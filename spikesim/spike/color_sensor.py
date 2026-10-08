"""``color_sensor``: il sensore di colore.

Quando c'è un tappeto, il sensore legge la mattonella su cui si trova il
**centro** del robot — è la lettura che cambia mentre il robot avanza, ed è
su questa che si basa il programma segui-linea. Senza tappeto restituisce i
valori fissi impostati nella configurazione delle porte.
"""

from __future__ import annotations

from ..config import COLOR_SENSOR
from ..runtime import hardware

__all__ = ["color", "reflection", "rgbi"]


def _port(port) -> int:
    return hardware().require_device(port, (COLOR_SENSOR,), "un sensore di colore")


def color(port: int) -> int:
    """Colore riconosciuto: confrontalo con le costanti del modulo ``color``."""
    _port(port)
    return hardware().surface().color


def reflection(port: int) -> int:
    """Intensità della luce riflessa, da 0 a 100."""
    _port(port)
    return hardware().surface().reflection


def rgbi(port: int) -> tuple[int, int, int, int]:
    """(rosso, verde, blu, intensità) misurati dal sensore."""
    _port(port)
    reflection = hardware().surface().reflection
    value = reflection * 255 // 100
    return (value, value, value, reflection)
