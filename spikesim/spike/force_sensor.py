"""``force_sensor``: il sensore di forza."""

from __future__ import annotations

from ..config import FORCE_SENSOR
from ..runtime import hardware

__all__ = ["force", "pressed", "raw"]


def _port(port) -> int:
    hw = hardware()
    return hw.require_device(port, (FORCE_SENSOR,), "un sensore di forza")


def force(port: int) -> int:
    """Forza misurata in decinewton, da 0 a 100."""
    hw = hardware()
    _port(port)
    return hw.config.sensors.force


def pressed(port: int) -> bool:
    """``True`` se il pulsante del sensore è premuto."""
    hw = hardware()
    _port(port)
    return hw.config.sensors.pressed


def raw(port: int) -> int:
    """Valore grezzo, non calibrato, del sensore."""
    hw = hardware()
    _port(port)
    return hw.config.sensors.force * 10
