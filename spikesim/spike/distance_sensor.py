"""``distance_sensor``: il sensore di distanza e i suoi 4 LED."""

from __future__ import annotations

from ..config import DISTANCE_SENSOR
from ..errors import PixelOutOfRangeError
from ..runtime import hardware

__all__ = ["distance", "clear", "get_pixel", "set_pixel", "show"]

_LEDS = 4
_STATE_KEY = "distance_leds"


def _port(port) -> int:
    hw = hardware()
    return hw.require_device(port, (DISTANCE_SENSOR,), "un sensore di distanza")


def _leds(port: int) -> list[int]:
    hw = hardware()
    return hw.device_state.setdefault((_STATE_KEY, port), [0] * _LEDS)


def _check(x: int, y: int) -> None:
    for name, value in (("x", x), ("y", y)):
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 3:
            raise PixelOutOfRangeError(
                f"{name} = {value!r} è fuori dai 4 LED del sensore di distanza (0-3)."
            )


def distance(port: int) -> int:
    """Distanza in millimetri, oppure -1 se non c'è una lettura valida."""
    hw = hardware()
    _port(port)
    return hw.config.sensors.distance


def clear(port: int) -> None:
    """Spegne i 4 LED del sensore."""
    port = _port(port)
    hardware().device_state[(_STATE_KEY, port)] = [0] * _LEDS


def set_pixel(port: int, x: int, y: int, intensity: int) -> None:
    """Cambia l'intensità di un LED (i LED sono disposti in una riga da 4)."""
    _check(x, y)
    port = _port(port)
    _leds(port)[x] = int(intensity)


def get_pixel(port: int, x: int, y: int) -> int:
    """Intensità di un LED."""
    _check(x, y)
    port = _port(port)
    return _leds(port)[x]


def show(port: int, pixels) -> None:
    """Accende i 4 LED con le intensità indicate."""
    port = _port(port)
    values = [int(value) for value in pixels]
    if len(values) != _LEDS:
        from ..errors import InvalidArgumentError

        raise InvalidArgumentError(
            f"show() richiede {_LEDS} valori, ricevuti {len(values)}."
        )
    hardware().device_state[(_STATE_KEY, port)] = values
