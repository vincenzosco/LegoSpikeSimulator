"""ERRORE VOLUTO — la porta C non ha un motore.

Con la configurazione predefinita il drive base usa le porte A e B; la
porta C è vuota. Il programma si ferma con ``SPIKE012``, che è quello che
farebbe anche il hub vero.

Per farlo funzionare: collega un motore alla porta C nel pannello
«Hardware», oppure cambia la porta in ``port.A``.
"""

import motor
import runloop
from hub import port


async def main():
    await motor.run_for_degrees(port.C, 360, 720)


runloop.run(main())
