"""``hub.light_matrix``: la matrice di 25 LED del hub."""

from __future__ import annotations

from ...errors import InvalidArgumentError, PixelOutOfRangeError
from .. import _consts as K
from .._images import glyph, image_pixels
from ...runtime import hardware

#: Le 67 costanti ``IMAGE_*`` della documentazione SPIKE 3. Sono generate
#: dalla tabella di `spikesim.spike._consts` per non ricopiarle a mano.
globals().update({f"IMAGE_{name}": value for name, value in K.IMAGE_CONSTANTS.items()})

__all__ = [
    "clear", "get_orientation", "get_pixel", "set_orientation", "set_pixel",
    "show", "show_image", "write",
] + [f"IMAGE_{name}" for name in K.IMAGE_NAMES]


def _check_pixel(x: int, y: int) -> None:
    for name, value in (("x", x), ("y", y)):
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 4:
            raise PixelOutOfRangeError(
                f"{name} = {value!r} è fuori dalla matrice 5x5: usa un valore da 0 a 4."
            )


def _intensity(value) -> int:
    """Intensità valida 0..100, con avviso se il programma esce dall'intervallo."""
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise InvalidArgumentError(
            f"intensità non valida: {value!r}; usa un intero da 0 a 100."
        ) from exc
    if not 0 <= number <= 100:
        hw = hardware()
        hw.note(
            "warning",
            "SPIKE031",
            f"intensità {number} fuori dall'intervallo 0-100: limitata.",
            line=hw.caller_line(),
        )
        number = max(0, min(100, number))
    return number


def _pixels_from(bits: list[int] | tuple[int, ...], intensity: int) -> list[int]:
    return [intensity if bit else 0 for bit in bits]


def clear() -> None:
    """Spegne tutti i pixel."""
    hw = hardware()
    hw.light_matrix = [0] * 25
    hw.emit("light_matrix", pixels=list(hw.light_matrix))


def show(pixels) -> None:
    """Accende i 25 pixel con le intensità indicate."""
    hw = hardware()
    values = [_intensity(value) for value in pixels]
    if len(values) != 25:
        raise InvalidArgumentError(
            f"show() richiede esattamente 25 valori, ricevuti {len(values)}."
        )
    hw.light_matrix = values
    hw.emit("light_matrix", pixels=values)


def set_pixel(x: int, y: int, intensity: int) -> None:
    """Imposta l'intensità di un pixel (x, y), entrambi da 0 a 4."""
    _check_pixel(x, y)
    hw = hardware()
    hw.light_matrix[y * 5 + x] = _intensity(intensity)
    hw.emit("light_matrix", pixels=list(hw.light_matrix))


def get_pixel(x: int, y: int) -> int:
    """Intensità del pixel (x, y)."""
    _check_pixel(x, y)
    return hardware().light_matrix[y * 5 + x]


def show_image(image: int) -> None:
    """Mostra una delle 67 immagini predefinite (``IMAGE_HEART`` ... ``IMAGE_SNAKE``)."""
    hw = hardware()
    pixels = image_pixels(image, 100)
    if pixels is None:
        raise InvalidArgumentError(
            f"immagine non valida: {image!r}; l'intervallo valido è 1-67 "
            "(usa una costante IMAGE_* di light_matrix)."
        )
    hw.light_matrix = pixels
    hw.emit("light_matrix", pixels=pixels)


def get_orientation() -> int:
    """Orientamento corrente della matrice (costanti del modulo orientation)."""
    return hardware().matrix_orientation


def set_orientation(top: int) -> int:
    """Ruota la matrice: ``top`` è il lato del hub usato come alto."""
    hw = hardware()
    if top not in (
        K.ORIENTATION_UP, K.ORIENTATION_RIGHT, K.ORIENTATION_DOWN, K.ORIENTATION_LEFT
    ):
        raise InvalidArgumentError(
            f"orientamento non valido: {top!r}; usa orientation.UP/RIGHT/DOWN/LEFT."
        )
    hw.matrix_orientation = top
    return top


def write(text: str, intensity: int = 100, time_per_character: int = 500):
    """Scrive ``text`` scorrendo i caratteri da destra verso sinistra.

    Restituisce un awaitable: senza ``await`` il testo non viene mostrato e
    il runtime lo segnala.
    """
    hw = hardware()
    label = f'light_matrix.write("{text}")'
    return hw.tracked(_write_impl(hw, str(text), _intensity(intensity), int(time_per_character)), label)


def _text_columns(text: str) -> list[list[int]]:
    """Colonne del testo: 5 righe per colonna, con una colonna vuota fra i caratteri."""
    columns: list[list[int]] = []
    for character in text:
        rows = glyph(character) or glyph("?")
        for x in range(5):
            columns.append([1 if rows[y][x] == "#" else 0 for y in range(5)])
        columns.append([0] * 5)
    return columns


async def _write_impl(hw, text: str, intensity: int, time_per_character: int) -> None:
    columns = _text_columns(text)
    if not columns:
        clear()
        return
    step_ms = max(1, time_per_character // 5)
    frames = max(1, len(columns) - 4)
    for start in range(frames):
        window = columns[start:start + 5]
        while len(window) < 5:
            window.append([0] * 5)
        pixels = [
            intensity if window[x][y] else 0
            for y in range(5)
            for x in range(5)
        ]
        hw.light_matrix = pixels
        hw.emit("light_matrix", pixels=pixels)
        await hw.awaitable(
            kind="sleep",
            label="light_matrix.write",
            ready_at=hw.t_ms + step_ms,
        )
