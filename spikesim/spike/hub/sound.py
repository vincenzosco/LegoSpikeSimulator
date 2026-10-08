"""``hub.sound``: il buzzer del hub."""

from __future__ import annotations

from ...errors import InvalidArgumentError
from .. import _consts as K
from ...runtime import hardware

ANY = K.SOUND_ANY
DEFAULT = K.SOUND_DEFAULT
WAVEFORM_SINE = K.WAVEFORM_SINE
WAVEFORM_SQUARE = K.WAVEFORM_SQUARE
WAVEFORM_SAWTOOTH = K.WAVEFORM_SAWTOOTH
WAVEFORM_TRIANGLE = K.WAVEFORM_TRIANGLE


def _volume(value) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise InvalidArgumentError(
            f"volume non valido: {value!r}; usa un intero da 0 a 100."
        ) from exc
    if not 0 <= number <= 100:
        hw = hardware()
        hw.note(
            "warning",
            "SPIKE032",
            f"volume {number} fuori dall'intervallo 0-100: limitato.",
            line=hw.caller_line(),
        )
        number = max(0, min(100, number))
    return number


def beep(
    freq: int = 440,
    duration: int = 500,
    volume: int = 100,
    *,
    attack: int = 0,
    decay: int = 0,
    sustain: int = 100,
    release: int = 0,
    transition: int = 10,
    waveform: int = WAVEFORM_SINE,
    channel: int = DEFAULT,
):
    """Fa suonare un beep di ``duration`` millisecondi.

    Restituisce un awaitable: il beep dura quanto il tempo simulato che
    trascorre, quindi senza ``await`` non si sente nulla.
    """
    hw = hardware()
    _volume(volume)
    if duration < 0:
        raise InvalidArgumentError(
            f"durata non valida: {duration!r}; usa un numero di millisecondi >= 0."
        )
    hw.sounds.append({"freq": int(freq), "duration": int(duration)})
    hw.emit("sound", freq=int(freq), duration=int(duration))
    label = f"hub.sound.beep(freq={freq}, duration={duration})"
    return hw.tracked(_beep_impl(hw, int(duration)), label)


async def _beep_impl(hw, duration: int) -> None:
    await hw.awaitable(
        kind="sleep",
        label="hub.sound.beep",
        ready_at=hw.t_ms + max(0, duration),
    )


def stop() -> None:
    """Ferma ogni suono."""
    hardware().sounds.clear()


def volume(volume: int) -> None:
    """Imposta il volume del hub (0-100)."""
    _volume(volume)
