"""``app.display``: immagini e testo sullo schermo dell'app."""

from __future__ import annotations

from ...errors import InvalidArgumentError
from .. import _consts as K
from ...runtime import hardware

#: Le 21 costanti ``IMAGE_*`` di app.display.
globals().update({f"IMAGE_{name}": value for name, value in K.APP_IMAGE_CONSTANTS.items()})

__all__ = ["show", "hide", "image", "text"] + [
    f"IMAGE_{name}" for name in K.APP_IMAGE_NAMES
]


def show(fullscreen: bool = False) -> None:
    """Mostra sull'app la schermata corrente."""
    hw = hardware()
    hw.emit("note", text="app.display.show()", level="info")


def hide() -> None:
    """Nasconde la schermata dell'app."""
    hw = hardware()
    hw.emit("note", text="app.display.hide()", level="info")


def image(image: int) -> None:
    """Mostra una delle 21 immagini dell'app (``IMAGE_ROBOT_1`` ... ``IMAGE_RANDOM``)."""
    hw = hardware()
    if image not in K.APP_IMAGE_CONSTANTS.values():
        raise InvalidArgumentError(
            f"immagine non valida: {image!r}; l'intervallo valido è 1-21 "
            "(usa una costante IMAGE_* di app.display)."
        )
    hw.emit("note", text=f"app.display.image({image})", level="info")


def text(text: str) -> None:
    """Mostra una scritta sullo schermo dell'app."""
    hw = hardware()
    hw.emit("note", text=f"app.display.text({text!r})", level="info")
