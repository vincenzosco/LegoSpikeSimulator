"""ERRORE VOLUTO — ciclo infinito.

Il programma non termina mai: la simulazione si ferma dopo il tempo massimo
simulato e lo segnala con ``SPIKE016``, invece di restare appesa. Se il
ciclo non cedesse mai il controllo (``while True: pass``) interverrebbe il
limite di tempo reale.

Nota: sull'hardware vero questo programma è *legittimo* — un robot che non
si ferma mai è normale. Nel simulatore la traccia viene troncata, ma il
movimento resta visibile fino all'interruzione.
"""

import runloop
from hub import light_matrix


async def main():
    while True:
        light_matrix.show_image(light_matrix.IMAGE_HAPPY)
        await runloop.sleep_ms(500)
        light_matrix.show_image(light_matrix.IMAGE_SAD)
        await runloop.sleep_ms(500)


runloop.run(main())
