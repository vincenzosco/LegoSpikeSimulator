"""ERRORE VOLUTO — manca ``await``.

La riga 10 chiama una funzione asincrona senza ``await``: non succede
nulla. Il simulatore lo segnala come ``SPIKE020`` (a runtime) e ``SPIKE102``
(controllo statico, prima ancora di eseguire), indicando la riga esatta.

Correzione: scrivi ``await motor.run_for_degrees(...)``.
"""

import motor
import runloop
from hub import port


async def main():
    motor.run_for_degrees(port.A, 360, 720)


runloop.run(main())
