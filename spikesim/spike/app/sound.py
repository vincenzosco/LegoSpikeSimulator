"""``app.sound``: i suoni riprodotti dall'app."""

from __future__ import annotations

from ...errors import InvalidArgumentError
from ...runtime import hardware

__all__ = ["play", "set_attributes", "stop"]


def play(sound_name: str, volume: int = 100, pitch: int = 0, pan: int = 0):
    """Riproduce un suono dell'app.

    Restituisce un'attesa: senza ``await`` il suono non viene riprodotto.
    """
    hw = hardware()
    if not isinstance(sound_name, str):
        raise InvalidArgumentError(
            f"nome del suono non valido: {sound_name!r}; usa una stringa."
        )
    if not 0 <= int(volume) <= 100:
        raise InvalidArgumentError(
            f"volume {volume!r} fuori intervallo: usa un valore da 0 a 100."
        )
    hw.emit("note", text=f"app.sound.play({sound_name!r})", level="info")
    label = f"app.sound.play({sound_name!r})"
    return hw.tracked(_play_impl(hw, label), label)


async def _play_impl(hw, label: str) -> None:
    await hw.awaitable(kind="note", label=label, ready_at=hw.t_ms)


def set_attributes(volume: int, pitch: int, pan: int) -> None:
    """Imposta volume, intonazione e pan del suono."""
    hardware().emit(
        "note",
        text=f"app.sound.set_attributes({volume}, {pitch}, {pan})",
        level="info",
    )


def stop() -> None:
    """Ferma i suoni dell'app."""
    hardware().emit("note", text="app.sound.stop()", level="info")
