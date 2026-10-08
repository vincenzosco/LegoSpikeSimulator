"""``app.music``: strumenti e percussioni riprodotti dall'app."""

from __future__ import annotations

from ...errors import InvalidArgumentError
from .. import _consts as K
from ...runtime import hardware

globals().update({f"INSTRUMENT_{name}": value for name, value in K.INSTRUMENT_CONSTANTS.items()})
globals().update({f"DRUM_{name}": value for name, value in K.DRUM_CONSTANTS.items()})

__all__ = ["play_instrument", "play_drum"] + [
    f"INSTRUMENT_{name}" for name in K.INSTRUMENT_NAMES
] + [f"DRUM_{name}" for name in K.DRUM_NAMES]


def play_instrument(instrument: int, note: int, duration: int) -> None:
    """Suona una nota con uno strumento MIDI."""
    hw = hardware()
    if instrument not in K.INSTRUMENT_CONSTANTS.values():
        raise InvalidArgumentError(
            f"strumento non valido: {instrument!r}; usa una costante INSTRUMENT_*."
        )
    if not 0 <= int(note) <= 130:
        raise InvalidArgumentError(
            f"nota MIDI {note!r} fuori intervallo: usa un valore da 0 a 130."
        )
    hw.emit("note", text=f"app.music.play_instrument({instrument}, {note}, {duration})",
            level="info")


def play_drum(drum: int) -> None:
    """Suona una percussione."""
    hw = hardware()
    if drum not in K.DRUM_CONSTANTS.values():
        raise InvalidArgumentError(
            f"percussione non valida: {drum!r}; usa una costante DRUM_*."
        )
    hw.emit("note", text=f"app.music.play_drum({drum})", level="info")
