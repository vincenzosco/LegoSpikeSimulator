"""``hub.light``: i LED di stato del hub."""

from __future__ import annotations

from ...errors import InvalidArgumentError
from .. import _consts as K
from ...runtime import hardware

POWER = K.LIGHT_POWER
CONNECT = K.LIGHT_CONNECT


def color(light: int, color: int) -> None:
    """Cambia il colore di un LED del hub."""
    hw = hardware()
    if light not in (POWER, CONNECT):
        raise InvalidArgumentError(
            f"LED non valido: {light!r}; usa light.POWER o light.CONNECT."
        )
    if not 0 <= color <= 10:
        raise InvalidArgumentError(
            f"colore non valido: {color!r}; usa una costante del modulo color."
        )
    hw.hub_lights[light] = color
    hw.emit("hub_light", light=light, color=color)
