"""``app.linegraph``: grafici a linee mostrati dall'app."""

from __future__ import annotations

from ...errors import InvalidArgumentError
from ...runtime import hardware

__all__ = [
    "clear", "clear_all", "get_average", "get_last", "get_max", "get_min",
    "hide", "plot", "show",
]

_points: dict[int, list[float]] = {}


def _color(color: int) -> int:
    if not 0 <= int(color) <= 10:
        raise InvalidArgumentError(
            f"colore non valido: {color!r}; usa una costante del modulo color."
        )
    return int(color)


def plot(color: int, x: float, y: float) -> None:
    """Aggiunge un punto al grafico del colore indicato."""
    hw = hardware()
    key = _color(color)
    _points.setdefault(key, []).append(float(y))
    hw.emit("note", text=f"app.linegraph.plot({color}, {x}, {y})", level="info")


def clear(color: int) -> None:
    """Azzera una linea."""
    _points.pop(_color(color), None)


def clear_all() -> None:
    """Azzera tutte le linee."""
    _points.clear()


def show(fullscreen: bool = False) -> None:
    hardware().emit("note", text="app.linegraph.show()", level="info")


def hide() -> None:
    hardware().emit("note", text="app.linegraph.hide()", level="info")


def get_last(color: int):
    label = f"app.linegraph.get_last({color})"
    return _make(label)


def get_average(color: int):
    return _make(f"app.linegraph.get_average({color})")


def get_max(color: int):
    return _make(f"app.linegraph.get_max({color})")


def get_min(color: int):
    return _make(f"app.linegraph.get_min({color})")


def _make(label: str):
    hw = hardware()
    return hw.tracked(_value_impl(hw, label), label)


async def _value_impl(hw, label: str) -> None:
    await hw.awaitable(kind="note", label=label, ready_at=hw.t_ms)
