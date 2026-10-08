"""``color_matrix``: la matrice di LED 3x3 della SPIKE Prime."""

from __future__ import annotations

from ..config import COLOR_MATRIX
from ..errors import InvalidArgumentError, PixelOutOfRangeError
from ..runtime import hardware

__all__ = ["clear", "get_pixel", "set_pixel", "show"]

_PIXELS = 9
_STATE_KEY = "color_matrix"


def _port(port) -> int:
    hw = hardware()
    return hw.require_device(port, (COLOR_MATRIX,), "una matrice colori")


def _pixels(port: int) -> list[tuple[int, int]]:
    return hardware().device_state.setdefault((_STATE_KEY, port), [(0, 0)] * _PIXELS)


def _check(x: int, y: int) -> None:
    for name, value in (("x", x), ("y", y)):
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 2:
            raise PixelOutOfRangeError(
                f"{name} = {value!r} è fuori dalla matrice 3x3 (0-2)."
            )


def clear(port: int) -> None:
    """Spegne tutti i pixel."""
    port = _port(port)
    hardware().device_state[(_STATE_KEY, port)] = [(0, 0)] * _PIXELS


def get_pixel(port: int, x: int, y: int) -> tuple[int, int]:
    """(colore, intensità) di un pixel."""
    _check(x, y)
    port = _port(port)
    return _pixels(port)[y * 3 + x]


def set_pixel(port: int, x: int, y: int, pixel: tuple[int, int]) -> None:
    """Cambia colore e intensità di un pixel."""
    _check(x, y)
    port = _port(port)
    color, intensity = pixel
    _pixels(port)[y * 3 + x] = (int(color), int(intensity))


def show(port: int, pixels) -> None:
    """Accende tutti i 9 pixel con la lista (colore, intensità)."""
    port = _port(port)
    values = [(int(color), int(intensity)) for color, intensity in pixels]
    if len(values) != _PIXELS:
        raise InvalidArgumentError(
            f"show() richiede {_PIXELS} coppie (colore, intensità), ricevute {len(values)}."
        )
    hardware().device_state[(_STATE_KEY, port)] = values
