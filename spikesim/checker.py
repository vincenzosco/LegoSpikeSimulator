"""Analisi statica di un programma SPIKE, con diagnostica in italiano.

Il programma viene letto senza essere eseguito e confrontato con la libreria
SPIKE e con la configurazione delle porte. Serve a dire subito le cose che
altrimenti si vedrebbero solo come "il robot non si muove":

* un modulo o un nome scritto male (``import motr``, ``motor.runn``);
* una funzione chiamata senza ``await`` (non fa *nulla*);
* ``runloop.run(main)`` senza le parentesi;
* una funzione ``async`` definita e mai avviata;
* una coppia motori usata prima di essere creata;
* un motore o un sensore usato su una porta dove non c'è.

Il checker non è un analizzatore completo: lavora sui nomi che il programma
importa dalla libreria SPIKE e tace su tutto il resto.
"""

from __future__ import annotations

import ast
import difflib
import os

from .config import (
    COLOR_MATRIX,
    COLOR_SENSOR,
    DEVICE_LABELS,
    DISTANCE_SENSOR,
    FORCE_SENSOR,
    MOTOR_KINDS,
    PORT_NAMES,
    Config,
    default_config,
)
from .spike_api import AWAIT_REQUIRED, MODULE_MAP, load
from .trace import Diagnostic

#: Funzione -> tipo di dispositivo richiesto sulla porta (primo parametro).
_PORT_FUNCTIONS: dict[str, dict[str, str]] = {
    "motor": {
        name: "motor"
        for name in (
            "run", "run_for_degrees", "run_for_time", "run_to_absolute_position",
            "run_to_relative_position", "stop", "set_duty_cycle", "get_duty_cycle",
            "absolute_position", "relative_position", "velocity",
            "reset_relative_position",
        )
    },
    "color_sensor": {name: "color_sensor" for name in ("color", "reflection", "rgbi")},
    "distance_sensor": {
        name: "distance_sensor"
        for name in ("clear", "distance", "get_pixel", "set_pixel", "show")
    },
    "force_sensor": {name: "force_sensor" for name in ("force", "pressed", "raw")},
    "color_matrix": {
        name: "color_matrix"
        for name in ("clear", "get_pixel", "set_pixel", "show")
    },
}

_REQUIRED_DEVICES: dict[str, frozenset[str]] = {
    "motor": MOTOR_KINDS,
    "color_sensor": frozenset({COLOR_SENSOR}),
    "distance_sensor": frozenset({DISTANCE_SENSOR}),
    "force_sensor": frozenset({FORCE_SENSOR}),
    "color_matrix": frozenset({COLOR_MATRIX}),
}

_PAIR_MOVE_FUNCTIONS = frozenset(
    {"move", "move_for_degrees", "move_for_time", "move_tank",
     "move_tank_for_degrees", "move_tank_for_time", "stop"}
)

_SIMILARITY = 0.8


def check_source(path: str, config: Config | None = None) -> list[Diagnostic]:
    """Controlla il file ``path``; un file illeggibile diventa una diagnostica."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            source = handle.read()
    except OSError as exc:
        return [
            Diagnostic(
                "error",
                "SYN002",
                f"non riesco a leggere {path}: {exc.strerror or exc}.",
            )
        ]
    return check_text(source, os.path.basename(path), config)


def check_text(
    source: str, filename: str = "programma.py", config: Config | None = None
) -> list[Diagnostic]:
    """Controlla il testo del programma e restituisce le diagnostiche trovate."""
    config = config or default_config()
    try:
        tree = ast.parse(source, filename)
    except SyntaxError as exc:
        return [
            Diagnostic(
                "error",
                "SYN001",
                f"errore di sintassi: {exc.msg}.",
                line=exc.lineno,
                column=exc.offset,
            )
        ]
    return _Checker(filename, config).run(tree)


class _Checker:
    def __init__(self, filename: str, config: Config) -> None:
        self.filename = filename
        self.config = config
        self.diagnostics: list[Diagnostic] = []
        #: nome locale -> percorso del modulo/sottomodulo SPIKE
        self.bindings: dict[str, str] = {}
        #: nomi delle funzioni ``async def`` definite nel programma
        self.async_functions: set[str] = set()
        self.uses_runloop_run = False
        self.pairs_created = False
        self.first_pair_move: ast.AST | None = None

    # -- utilità -------------------------------------------------------------

    def report(
        self,
        node: ast.AST | None,
        severity: str,
        code: str,
        message: str,
        *,
        column: int | None = None,
    ) -> None:
        line = getattr(node, "lineno", None) if node is not None else None
        if column is None and node is not None:
            column = getattr(node, "col_offset", None)
            column = column + 1 if column is not None else None
        self.diagnostics.append(Diagnostic(severity, code, message, line=line, column=column))

    def _suggest(self, name: str, module_path: str) -> str:
        try:
            options = [item for item in dir(load(module_path)) if not item.startswith("_")]
        except Exception:  # pragma: no cover - modulo SPIKE sempre importabile
            return ""
        matches = difflib.get_close_matches(name, options, n=1, cutoff=_SIMILARITY)
        return f" Intendevi «{matches[0]}»?" if matches else ""

    # -- passata principale --------------------------------------------------

    def run(self, tree: ast.AST) -> list[Diagnostic]:
        self._collect(tree)
        self._check(tree)
        self.diagnostics.sort(key=lambda d: (d.line if d.line is not None else 10**9, d.code))
        return self.diagnostics

    def _collect(self, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                self.async_functions.add(node.name)
            elif isinstance(node, ast.Import):
                self._collect_import(node)
            elif isinstance(node, ast.ImportFrom):
                self._collect_import_from(node)

    def _collect_import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name in MODULE_MAP:
                self.bindings[alias.asname or alias.name] = alias.name
                continue
            matches = difflib.get_close_matches(
                alias.name, sorted(MODULE_MAP), n=1, cutoff=_SIMILARITY
            )
            if matches:
                self.report(
                    node,
                    "error",
                    "SPIKE100",
                    f"il modulo «{alias.name}» non esiste nella libreria SPIKE: "
                    f"intendevi «{matches[0]}»?",
                )

    def _collect_import_from(self, node: ast.ImportFrom) -> None:
        if node.module not in MODULE_MAP:
            return
        for alias in node.names:
            target = f"{node.module}.{alias.name}"
            if target in MODULE_MAP:
                self.bindings[alias.asname or alias.name] = target
                continue
            self.report(
                node,
                "error",
                "SPIKE101",
                f"«{node.module}» non ha «{alias.name}»."
                + self._suggest(alias.name, node.module),
            )

    def _check(self, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                self._check_attribute(node)
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                self._check_bare_call(node)
            elif isinstance(node, ast.Call):
                self._check_call(node)
        self._check_async_usage()

    # -- controlli -----------------------------------------------------------

    def _module_chain(self, node: ast.Attribute) -> tuple[str, str] | None:
        """(modulo, attributo finale) se ``node`` parte da un modulo SPIKE."""
        parts: list[str] = []
        current: ast.AST = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if not isinstance(current, ast.Name) or current.id not in self.bindings:
            return None
        parts.reverse()
        module_path = self.bindings[current.id]
        index = 0
        while index < len(parts) - 1 and f"{module_path}.{parts[index]}" in MODULE_MAP:
            module_path = f"{module_path}.{parts[index]}"
            index += 1
        return module_path, parts[index]

    def _check_attribute(self, node: ast.Attribute) -> None:
        chain = self._module_chain(node)
        if chain is None:
            return
        module_path, attribute = chain
        if attribute.startswith("__"):
            return
        module = load(module_path)
        if hasattr(module, attribute):
            return
        self.report(
            node,
            "error",
            "SPIKE101",
            f"«{module_path}» non ha «{attribute}»."
            + self._suggest(attribute, module_path),
        )

    def _spike_call_path(self, call: ast.Call) -> str | None:
        """Percorso SPIKE completo della funzione chiamata, se riconoscibile."""
        function = call.func
        if isinstance(function, ast.Attribute):
            chain = self._module_chain(function)
            if chain is None:
                return None
            return f"{chain[0]}.{chain[1]}"
        if isinstance(function, ast.Name) and function.id in self.bindings:
            # from hub import light_matrix -> light_matrix.write(...)
            return self.bindings[function.id]
        return None

    def _check_bare_call(self, statement: ast.Expr) -> None:
        """Chiamata usata come istruzione: se serve un await, è un errore."""
        call = statement.value
        path = self._spike_call_path(call)
        if path is None:
            return
        module_path, _, name = path.rpartition(".")
        if name in AWAIT_REQUIRED.get(module_path, frozenset()):
            self.report(
                call,
                "warning",
                "SPIKE102",
                f"«{path}» è asincrona e qui non ha «await»: non avrà alcun "
                "effetto. Scrivi «await " + path + "(...)» dentro una funzione "
                "async avviata con runloop.run().",
            )

    def _check_call(self, call: ast.Call) -> None:
        path = self._spike_call_path(call)
        if path is None:
            return
        module_path, _, name = path.rpartition(".")

        if path == "motor_pair.pair":
            self.pairs_created = True
        elif module_path == "motor_pair" and name in _PAIR_MOVE_FUNCTIONS:
            if self.first_pair_move is None:
                self.first_pair_move = call

        if path == "runloop.run":
            self.uses_runloop_run = True
            for argument in call.args:
                if isinstance(argument, ast.Name) and argument.id in self.async_functions:
                    self.report(
                        argument,
                        "warning",
                        "SPIKE103",
                        f"«runloop.run({argument.id})» ha ricevuto la funzione senza "
                        f"parentesi: usa «runloop.run({argument.id}())».",
                    )

        self._check_port_argument(call, module_path, name)

    def _check_port_argument(self, call: ast.Call, module_path: str, name: str) -> None:
        what = _PORT_FUNCTIONS.get(module_path, {}).get(name)
        if what is None or not call.args:
            return
        port = self._literal_port(call.args[0])
        if port is None:
            return
        if self.config.device(port) in _REQUIRED_DEVICES[what]:
            return
        connected = DEVICE_LABELS.get(self.config.device(port), "?").lower()
        self.report(
            call.args[0],
            "warning",
            "SPIKE106",
            f"sulla porta {PORT_NAMES[port]} non c'è un {what.replace('_', ' ')} "
            f"(collegato: {connected}): il comando non avrà effetto.",
        )

    def _literal_port(self, node: ast.AST) -> int | None:
        """Valore della porta se è scritto in modo riconoscibile (``port.C``, ``2``)."""
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return node.value if 0 <= node.value <= 5 else None
        if isinstance(node, ast.Attribute):
            chain = self._module_chain(node)
            if chain == ("hub.port", node.attr):
                value = getattr(load("hub.port"), node.attr, None)
                return value if isinstance(value, int) else None
        return None

    def _check_async_usage(self) -> None:
        if self.async_functions and not self.uses_runloop_run:
            self.report(
                None,
                "warning",
                "SPIKE104",
                "il programma definisce «async def "
                f"{sorted(self.async_functions)[0]}()» ma non chiama mai "
                "runloop.run(): le funzioni async non verranno eseguite.",
            )
        if self.first_pair_move is not None and not self.pairs_created:
            self.report(
                self.first_pair_move,
                "warning",
                "SPIKE105",
                "la Motor Pair viene usata senza essere stata creata: chiama prima "
                "motor_pair.pair(motor_pair.PAIR_1, <motore sinistro>, <motore destro>).",
            )
