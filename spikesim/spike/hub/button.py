"""``hub.button``: i pulsanti sul hub.

Nella simulazione nessuno preme i pulsanti: ``pressed`` restituisce sempre
``0``. Un programma che aspetta un pulsante in un ciclo stretto non termina
mai, e viene fermato dal limite di passi con un messaggio esplicito.
"""

from __future__ import annotations

from ...errors import InvalidArgumentError
from .. import _consts as K
from ...runtime import hardware

LEFT = K.BUTTON_LEFT
RIGHT = K.BUTTON_RIGHT


def pressed(button: int) -> int:
    """``1`` se il pulsante è premuto, ``0`` altrimenti (sempre 0 qui).

    Sull'hardware vero il valore di ritorno è la durata della pressione in
    millisecondi.
    """
    if button not in (LEFT, RIGHT):
        raise InvalidArgumentError(
            f"pulsante non valido: {button!r}; usa button.LEFT o button.RIGHT."
        )
    hardware()  # verifica che una simulazione sia attiva
    return 0
