"""``device``: informazioni sui dispositivi collegati alle porte.

Gli identificativi dei dispositivi non sono pubblicati nella documentazione
SPIKE 3: quelli qui sotto sono stabili e coerenti fra loro, ma non
pretendono di essere i valori esatti del firmware.
"""

from __future__ import annotations

from ..config import (
    COLOR_MATRIX,
    COLOR_SENSOR,
    DISTANCE_SENSOR,
    EMPTY,
    FORCE_SENSOR,
    MOTOR_LARGE,
    MOTOR_KINDS,
    MOTOR_MEDIUM,
    MOTOR_SMALL,
)
from ..errors import InvalidArgumentError, NoDeviceError
from ..runtime import hardware
from . import motor

__all__ = ["data", "id", "get_duty_cycle", "ready", "set_duty_cycle"]

_DEVICE_IDS = {
    MOTOR_LARGE: 46,
    MOTOR_MEDIUM: 48,
    MOTOR_SMALL: 49,
    COLOR_SENSOR: 61,
    DISTANCE_SENSOR: 62,
    FORCE_SENSOR: 63,
    COLOR_MATRIX: 64,
}

#: Lunghezza dei dati LPF-2 restituiti (non modellati nel dettaglio).
_DATA_LENGTH = 8


def _device_kind(port) -> tuple[int, str]:
    hw = hardware()
    index = hw.port_index(port)
    kind = hw.config.device(index)
    if kind == EMPTY:
        from ..config import DEVICE_LABELS, PORT_NAMES

        raise NoDeviceError(
            f"sulla porta {PORT_NAMES[index]} non c'è nessun dispositivo collegato "
            f"({DEVICE_LABELS[EMPTY]})."
        )
    return index, kind


def id(port: int) -> int:
    """Identificativo del dispositivo collegato alla porta."""
    _index, kind = _device_kind(port)
    return _DEVICE_IDS[kind]


def ready(port: int) -> bool:
    """``True`` se il dispositivo collegato è pronto a ricevere comandi."""
    try:
        _device_kind(port)
    except NoDeviceError:
        return False
    return True


def data(port: int) -> tuple[int, ...]:
    """Dati LPF-2 grezzi del dispositivo (non modellati: tutti zeri)."""
    _device_kind(port)
    return tuple(0 for _ in range(_DATA_LENGTH))


def get_duty_cycle(port: int) -> int:
    """Ciclo di lavoro del dispositivo, da 0 a 10000."""
    _index, kind = _device_kind(port)
    if kind in MOTOR_KINDS:
        return motor.get_duty_cycle(port)
    return 0


def set_duty_cycle(port: int, duty_cycle: int) -> None:
    """Imposta il ciclo di lavoro del dispositivo (solo per i motori)."""
    _index, kind = _device_kind(port)
    if kind not in MOTOR_KINDS:
        raise InvalidArgumentError(
            "set_duty_cycle() funziona solo con i motori: usa motor.set_duty_cycle()."
        )
    motor.set_duty_cycle(port, duty_cycle)
