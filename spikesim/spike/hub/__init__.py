"""Modulo ``hub`` della libreria SPIKE 3.

Raccoglie i sottomoduli del hub (``port``, ``button``, ``light``,
``light_matrix``, ``motion_sensor``, ``sound``) e le funzioni che
descrivono il hub stesso.
"""

from __future__ import annotations

from ...runtime import hardware
from . import button, light, light_matrix, motion_sensor, port, sound

__all__ = [
    "button", "light", "light_matrix", "motion_sensor", "port", "sound",
    "device_uuid", "hardware_id", "power_off", "temperature",
]


def device_uuid() -> str:
    """Identificativo del dispositivo: costante nella simulazione."""
    return "sim-hub-0001"


def hardware_id() -> str:
    """Identificativo hardware: costante nella simulazione."""
    return "spike-prime-sim"


def temperature() -> int:
    """Temperatura del hub in decimi di grado celsius."""
    return 210


def power_off() -> int:
    """Spegne il hub: nella simulazione interrompe il programma."""
    hw = hardware()
    hw.note(
        "info",
        "SPIKE030",
        "hub.power_off() chiamato: il hub simulato si spegne e il programma termina.",
        line=hw.caller_line(),
    )
    hw.stop_all_motors()
    hw.stop_reason = "power_off"
    return 0
