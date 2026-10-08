"""Esecuzione di un programma SPIKE scritto dall'utente.

Due modalità:

``run_in_process(path, config)``
    esegue il programma qui, nello stesso processo: è quella usata dai test
    e dal processo figlio;
``run_program(path, config)``
    avvia un processo separato (``python -m spikesim.runner``) e ne legge la
    traccia JSON. È quella usata dalla GUI: un programma che non termina
    (``while True: pass``) può essere ucciso senza portarsi dietro l'editor.

Il programma dell'utente non viene modificato: la libreria SPIKE viene
registrata in ``sys.modules`` con i suoi nomi (``import motor``,
``from hub import port``) e il modulo ``time`` riceve le funzioni
MicroPython (``sleep_ms``, ``ticks_ms``, ...).
"""

from __future__ import annotations

import argparse
import io
import json
import os
import signal
import subprocess
import sys
import threading
import warnings
from dataclasses import dataclass

from .config import Config, default_config
from .errors import ProgramLimitError, SpikeError
from .runtime import Hardware, Scheduler, set_hardware
from .spike_api import install, install_time_shim
from .trace import (
    Diagnostic,
    Trace,
    diagnostics_from_exception,
    format_exception,
    to_json,
    user_line_from_exception,
)

#: Cartella che contiene il pacchetto: serve per il ``PYTHONPATH`` del figlio.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Ragioni per cui la simulazione si è fermata senza che il programma finisse.
_STOPPED_REASONS = {"time_limit", "step_limit", "blocked"}


@dataclass
class RunResult:
    """Traccia prodotta più l'output di errore del processo figlio."""

    trace: Trace
    stderr: str = ""


class _PrintRouter(io.TextIOBase):
    """Sostituisce ``sys.stdout``: i ``print`` diventano eventi della traccia."""

    def __init__(self, hardware: Hardware) -> None:
        self.hardware = hardware
        self._buffer = ""

    @property
    def encoding(self) -> str:  # usato da print/file=...
        return "utf-8"

    def writable(self) -> bool:
        return True

    def write(self, text) -> int:  # type: ignore[override]
        if not isinstance(text, str):
            text = str(text)
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self.hardware.emit("print", text=line)
        if len(self._buffer) > 4096:
            self.hardware.emit("print", text=self._buffer)
            self._buffer = ""
        return len(text)

    def flush(self) -> None:
        if self._buffer:
            self.hardware.emit("print", text=self._buffer)
            self._buffer = ""


class _Watchdog:
    """Interrompe un programma che non cede mai il controllo.

    Un ciclo puramente Python (``while True: pass``) non passa mai dallo
    scheduler, che quindi non può accorgersene: serve un timer reale.
    """

    def __init__(self, seconds: float) -> None:
        self.seconds = float(seconds)
        self._previous = None
        self._armed = False

    def start(self) -> None:
        if self.seconds <= 0 or not hasattr(signal, "SIGALRM"):
            return
        if threading.current_thread() is not threading.main_thread():
            return
        try:
            self._previous = signal.signal(signal.SIGALRM, self._fire)
            signal.setitimer(signal.ITIMER_REAL, self.seconds)
            self._armed = True
        except (ValueError, OSError):  # pragma: no cover - ambiente senza timer
            self._armed = False

    def _fire(self, _signum, _frame):  # pragma: no cover - arriva dal segnale
        raise ProgramLimitError(
            f"il programma ha superato {self.seconds:.0f} secondi reali di "
            "esecuzione senza terminare: interrotto."
        )

    def stop(self) -> None:
        if not self._armed:
            return
        try:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, self._previous)
        except (ValueError, OSError):  # pragma: no cover
            pass
        self._armed = False


# ---------------------------------------------------------------------------
# Esecuzione nello stesso processo
# ---------------------------------------------------------------------------


def run_in_process(path: str, config: Config | None = None) -> RunResult:
    """Esegue ``path`` contro il hub simulato e restituisce la traccia."""
    program = os.path.abspath(path)
    config = config or default_config()
    hardware = Hardware(config, program=program)
    Scheduler(hardware)
    set_hardware(hardware)

    restore_modules = install()
    restore_time = install_time_shim()
    router = _PrintRouter(hardware)
    previous_stdout = sys.stdout
    sys.stdout = router
    watchdog = _Watchdog(config.max_wall_seconds)
    terminated = True

    # Le coroutine create e mai attese (per esempio ``main()`` senza
    # ``runloop.run``) vengono intercettate qui: CPython emette un
    # RuntimeWarning nel momento in cui l'oggetto viene raccolto, ed è
    # informazione troppo utile per lasciarla sparire.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            watchdog.start()
            with open(program, "r", encoding="utf-8") as handle:
                source = handle.read()
            code = compile(source, program, "exec")
            namespace = {
                "__name__": "__main__",
                "__file__": program,
                "__builtins__": __builtins__,
            }
            exec(code, namespace)  # noqa: S102 - è il compito di questo modulo
        except SyntaxError as exc:
            terminated = False
            hardware.note(
                "error",
                "PYTHON",
                f"SyntaxError: {exc.msg}",
                line=exc.lineno,
                column=exc.offset,
                detail=format_exception(exc),
            )
        except SystemExit:
            # sys.exit() nel programma utente: terminazione voluta.
            terminated = True
        except SpikeError as exc:
            terminated = False
            hardware.note(
                "error",
                exc.code,
                exc.message,
                line=user_line_from_exception(exc, program),
                detail=format_exception(exc),
            )
        except BaseException as exc:  # noqa: BLE001 - qualunque errore dell'utente
            terminated = False
            hardware.diagnostics.extend(diagnostics_from_exception(exc, program))
        finally:
            watchdog.stop()
            router.flush()
            sys.stdout = previous_stdout
            restore_time()
            restore_modules()

    _absorb_warnings(hardware, caught)
    hardware.stop_all_motors()
    if hardware.stop_reason in _STOPPED_REASONS:
        terminated = False
    trace = hardware.finish(terminated=terminated)
    set_hardware(None)
    return RunResult(trace=trace)


# ---------------------------------------------------------------------------
# Esecuzione in un processo separato
# ---------------------------------------------------------------------------


def _absorb_warnings(hardware: Hardware, caught) -> None:
    """Trasforma i warning di CPython in diagnostica della traccia."""
    reported = 0
    for entry in caught:
        text = str(entry.message)
        if "never awaited" in text:
            if reported < 10:
                hardware.note(
                    "warning",
                    "SPIKE020",
                    f"{text}: senza await e senza runloop.run() non ha alcun "
                    "effetto. Racchiudi il codice in una funzione async e "
                    "avviala con runloop.run().",
                )
            reported += 1
        else:
            # Un warning qualsiasi del programma: non lo nascondiamo.
            print(
                f"{entry.filename}:{entry.lineno}: {entry.category.__name__}: {text}",
                file=sys.stderr,
            )
    if reported > 10:
        hardware.note(
            "warning", "SPIKE020", f"e altre {reported - 10} coroutine mai attese."
        )


def _timeout_trace(path: str, seconds: float) -> Trace:
    """Traccia prodotta quando il processo figlio viene ucciso per timeout."""
    return Trace(
        program=os.path.abspath(path),
        duration_ms=0,
        terminated=False,
        poses=[],
        events=[],
        diagnostics=[
            Diagnostic(
                "error",
                "TIMEOUT",
                f"il programma non ha risposto entro {seconds:.0f} secondi ed è "
                "stato interrotto.",
            )
        ],
    )


def run_program(
    path: str, config: Config | None = None, *, timeout_s: float = 90.0
) -> RunResult:
    """Esegue ``path`` in un processo separato e legge la traccia JSON."""
    config = config or default_config()
    command = [
        sys.executable,
        "-m",
        "spikesim.runner",
        "--file",
        os.path.abspath(path),
        "--config",
        json.dumps(config.to_dict()),
    ]
    environment = dict(os.environ)
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = REPO_ROOT + (os.pathsep + existing if existing else "")
    environment.setdefault("PYTHONIOENCODING", "utf-8")

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout_s,
            env=environment,
            cwd=REPO_ROOT,
        )
    except subprocess.TimeoutExpired as expired:
        stderr = expired.stderr or ""
        if isinstance(stderr, bytes):  # pragma: no cover - dipende da text=
            stderr = stderr.decode("utf-8", "replace")
        return RunResult(trace=_timeout_trace(path, timeout_s), stderr=stderr)

    stderr = completed.stderr or ""
    try:
        trace = Trace.from_dict(json.loads(completed.stdout))
    except (ValueError, TypeError) as exc:
        return RunResult(
            trace=Trace(
                program=os.path.abspath(path),
                duration_ms=0,
                terminated=False,
                poses=[],
                events=[],
                diagnostics=[
                    Diagnostic(
                        "error",
                        "RUNNER",
                        "il processo che esegue il programma non ha prodotto una "
                        f"traccia valida ({exc}).",
                        detail=stderr.strip() or completed.stdout[-2000:],
                    )
                ],
            ),
            stderr=stderr,
        )
    return RunResult(trace=trace, stderr=stderr)


# ---------------------------------------------------------------------------
# Entry point del processo figlio
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spikesim.runner",
        description="Esegue un programma SPIKE e stampa la traccia JSON su stdout.",
    )
    parser.add_argument("--file", required=True, help="programma Python da simulare")
    parser.add_argument("--config", default=None, help="configurazione delle porte in JSON")
    parser.add_argument("--out", default=None, help="scrive la traccia in questo file")
    arguments = parser.parse_args(argv)

    config = (
        Config.from_dict(json.loads(arguments.config))
        if arguments.config
        else default_config()
    )
    result = run_in_process(arguments.file, config)
    payload = to_json(result.trace)
    if arguments.out:
        with open(arguments.out, "w", encoding="utf-8") as handle:
            handle.write(payload)
    else:
        sys.stdout.write(payload)
        sys.stdout.write("\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":  # pragma: no cover - avvio da riga di comando
    raise SystemExit(main())
