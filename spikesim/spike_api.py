"""Registrazione della libreria SPIKE simulata in ``sys.modules``.

Il programma dell'utente scrive ``import motor`` e ``from hub import port``,
esattamente come nel SPIKE App. Perché funzioni senza toccare il codice
dell'utente, i moduli di `spikesim.spike` vengono registrati in
``sys.modules`` con il loro nome "nudo": ``import`` consulta ``sys.modules``
prima di cercare su disco, quindi non serve mettere `spikesim/spike` nel
``sys.path`` (che creerebbe due copie degli stessi moduli).

Lo stesso vale per il modulo ``time`` di MicroPython: qui non si può
sostituire ``time`` (è un modulo builtin e vincerebbe comunque), quindi se
ne arricchiscono le funzioni con ``sleep_ms``, ``ticks_ms`` e compagne.
"""

from __future__ import annotations

import importlib
import sys
import time
from typing import Callable

from .runtime import hardware

#: Nome visibile al programma utente -> modulo di `spikesim.spike`.
MODULE_MAP = {
    "motor": "spikesim.spike.motor",
    "motor_pair": "spikesim.spike.motor_pair",
    "color": "spikesim.spike.color",
    "orientation": "spikesim.spike.orientation",
    "runloop": "spikesim.spike.runloop",
    "device": "spikesim.spike.device",
    "color_sensor": "spikesim.spike.color_sensor",
    "distance_sensor": "spikesim.spike.distance_sensor",
    "force_sensor": "spikesim.spike.force_sensor",
    "color_matrix": "spikesim.spike.color_matrix",
    "hub": "spikesim.spike.hub",
    "hub.port": "spikesim.spike.hub.port",
    "hub.button": "spikesim.spike.hub.button",
    "hub.light": "spikesim.spike.hub.light",
    "hub.light_matrix": "spikesim.spike.hub.light_matrix",
    "hub.motion_sensor": "spikesim.spike.hub.motion_sensor",
    "hub.sound": "spikesim.spike.hub.sound",
    "app": "spikesim.spike.app",
    "app.bargraph": "spikesim.spike.app.bargraph",
    "app.display": "spikesim.spike.app.display",
    "app.linegraph": "spikesim.spike.app.linegraph",
    "app.music": "spikesim.spike.app.music",
    "app.sound": "spikesim.spike.app.sound",
}

#: I moduli che il checker riconosce come "libreria SPIKE".
SPIKE_MODULE_NAMES = frozenset(MODULE_MAP)

#: Funzioni che la documentazione dichiara ``Awaitable``: se vengono chiamate
#: senza ``await`` non fanno nulla. Il checker le usa per avvisare *prima* di
#: eseguire il programma.
AWAIT_REQUIRED: dict[str, frozenset[str]] = {
    "motor": frozenset(
        {
            "run_for_degrees",
            "run_for_time",
            "run_to_absolute_position",
            "run_to_relative_position",
        }
    ),
    "motor_pair": frozenset(
        {"move_for_degrees", "move_for_time", "move_tank_for_degrees", "move_tank_for_time"}
    ),
    "runloop": frozenset({"sleep_ms", "until"}),
    "hub.light_matrix": frozenset({"write"}),
    "hub.sound": frozenset({"beep"}),
    "app.sound": frozenset({"play"}),
    "app.bargraph": frozenset({"get_value"}),
    "app.linegraph": frozenset({"get_average", "get_last", "get_max", "get_min"}),
}


def load(name: str):
    """Importa il modulo SPIKE corrispondente a ``name``."""
    return importlib.import_module(MODULE_MAP[name])


def install() -> Callable[[], None]:
    """Registra i moduli SPIKE; restituisce la funzione di ripristino."""
    previous: dict[str, object] = {}
    for bare_name, dotted in MODULE_MAP.items():
        previous[bare_name] = sys.modules.get(bare_name)
        sys.modules[bare_name] = importlib.import_module(dotted)

    def restore() -> None:
        for bare_name, old in previous.items():
            if old is None:
                sys.modules.pop(bare_name, None)
            else:
                sys.modules[bare_name] = old

    return restore


_MISSING = object()
_SHIM_NAMES = (
    "sleep_ms", "sleep_us", "ticks_ms", "ticks_us", "ticks_diff", "ticks_add", "sleep",
)


def install_time_shim() -> Callable[[], None]:
    """Aggiunge a ``time`` le funzioni MicroPython usate da SPIKE."""
    saved: dict[str, object] = {}
    for name in _SHIM_NAMES:
        saved[name] = getattr(time, name, _MISSING)

    def sleep_ms(milliseconds: int) -> None:
        _advance(milliseconds)

    def sleep_us(microseconds: int) -> None:
        _advance(float(microseconds) / 1000.0)

    def sleep(seconds: float) -> None:
        _advance(float(seconds) * 1000.0)

    def ticks_ms() -> int:
        return int(hardware().t_ms)

    ticks_us = ticks_ms
    ticks_diff = lambda a, b: int(a) - int(b)  # noqa: E731 - come in MicroPython
    ticks_add = lambda a, b: int(a) + int(b)  # noqa: E731

    time.sleep_ms = sleep_ms  # type: ignore[attr-defined]
    time.sleep_us = sleep_us  # type: ignore[attr-defined]
    time.sleep = sleep  # type: ignore[assignment]
    time.ticks_ms = ticks_ms  # type: ignore[attr-defined]
    time.ticks_us = ticks_us  # type: ignore[attr-defined]
    time.ticks_diff = ticks_diff  # type: ignore[attr-defined]
    time.ticks_add = ticks_add  # type: ignore[attr-defined]

    def restore() -> None:
        for name, old in saved.items():
            if old is _MISSING:
                try:
                    delattr(time, name)
                except AttributeError:
                    pass
            else:
                setattr(time, name, old)

    return restore


def _advance(milliseconds: float) -> None:
    """Avanza il tempo simulato (un ``sleep`` di MicroPython)."""
    hw = hardware()
    if milliseconds < 0:
        from .errors import InvalidArgumentError

        raise InvalidArgumentError(f"durata negativa: {milliseconds}")
    hw.advance_to(hw.t_ms + float(milliseconds))
