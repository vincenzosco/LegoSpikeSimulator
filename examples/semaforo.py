"""Aspetta un colore e poi accende una spia.

Prima di eseguirlo ricordati di dire al simulatore che sulla porta C c'è un
sensore di colore: nel pannello «Hardware» scegli *Sensore di colore* per la
porta C. Senza quella impostazione il programma si ferma con un errore
(``SPIKE011``), esattamente come farebbe il hub con la porta vuota.
"""

import color
import color_sensor
import runloop
from hub import light, port

PORTA_SENSORE = port.C
TIMEOUT_MS = 5000


def vede_rosso():
    return color_sensor.color(PORTA_SENSORE) is color.RED


async def main():
    light.color(light.POWER, color.RED)
    print("in attesa del rosso…")

    await runloop.until(vede_rosso, timeout=TIMEOUT_MS)

    light.color(light.POWER, color.GREEN)
    print("verde: via!")


runloop.run(main())
