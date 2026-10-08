"""``color_sensor``: il sensore di colore.

I valori restituiti sono quelli impostati dall'utente nella configurazione
delle porte (colore, riflessione); non c'è un vero sensore da leggere.
"""

from __future__ import annotations

from ..config import COLOR_SENSOR
from ..runtime import hardware

__all__ = ["color", "reflection", "rgbi"]


def _port(port):
    hw = hardware()
    return hw.require_device(port, (COLOR_SENSOR,), "un sensore di colore")


def color(port: int) -> int:
    """Colore riconosciuto: confrontalo con le costanti del modulo ``color``."""
    hardware()
    _port(port)
    return hardware().config.sensors.color


def reflection(port: int) -> int:
    """Intensità della luce riflessa, da 0 a 100."""
    hardware()
    _port(port)
    return hardware().config.sensors.reflection


def rgbi(port: int) -> tuple[int, int, int, int]:
    """(rosso, verde, blu, intensità) misurati dal sensore."""
    hw = hardware()
    _port(port)
    value = hw.config.sensors.reflection * 255 // 100
    return (value, value, value, hw.config.sensors.reflection)
