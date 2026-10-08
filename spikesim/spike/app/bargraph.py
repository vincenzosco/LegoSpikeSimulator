"""``app.bargraph``: grafici a barre mostrati dall'app."""

from __future__ import annotations

from ...errors import InvalidArgumentError
from ...runtime import hardware

__all__ = ["change", "clear_all", "get_value", "hide", "set_value", "show"]

_values: dict[int, float] = {}


def _color(color: int) -> int:
    if not 0 <= int(color) <= 10:
        raise InvalidArgumentError(
            f"colore non valido: {color!r}; usa una costante del modulo color."
        )
    return int(color)


def change(color: int, value: float) -> None:
    """Aggiunge ``value`` alla barra del colore indicato."""
    hw = hardware()
    key = _color(color)
    _values[key] = _values.get(key, 0.0) + float(value)
    hw.emit("note", text=f"app.bargraph.change({color}, {value})", level="info")


def set_value(color: int, value: float) -> None:
    """Imposta la barra del colore indicato."""
    hw = hardware()
    key = _color(color)
    _values[key] = float(value)
    hw.emit("note", text=f"app.bargraph.set_value({color}, {value})", level="info")


def clear_all() -> None:
    """Azzera tutte le barre."""
    hardware().emit("note", text="app.bargraph.clear_all()", level="info")
    _values.clear()


def show(fullscreen: bool = False) -> None:
    """Mostra il grafico a barre."""
    hardware().emit("note", text="app.bargraph.show()", level="info")


def hide() -> None:
    """Nasconde il grafico a barre."""
    hardware().emit("note", text="app.bargraph.hide()", level="info")


def get_value(color: int):
    """Legge il valore della barra (attesa: completa subito)."""
    hw = hardware()
    key = _color(color)
    label = f"app.bargraph.get_value({color})"
    return hw.tracked(_value_impl(hw, label), label)


async def _value_impl(hw, label: str) -> None:
    await hw.awaitable(kind="note", label=label, ready_at=hw.t_ms)
