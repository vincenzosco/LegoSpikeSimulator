"""Segui-linea: il robot legge la mattonella sotto di sé e obbedisce.

È il programma di un segui-linea da tappeto didattico. Il robot avanza di una
mattonella per volta, legge il colore della mattonella su cui si trova e
reagisce come farebbe un robot vero:

* mattonella dritta (nera) o di partenza (blu) -> avanti di una mattonella;
* mattonella **verde** -> curva di 90 gradi a sinistra;
* mattonella **rossa** -> curva di 90 gradi a destra;
* mattonella gialla (arrivo) -> si ferma;
* buio, o colore che non riconosce -> si ferma e lo dice nella console.

La curva è una rotazione *sul posto*: il robot non si sposta dal centro della
mattonella, quindi resta allineato alla griglia e la mattonella successiva è
sempre esattamente davanti a lui.

Come si usa dalla GUI: apri «Tappeto e luce», scegli un template e premi
Simula. Nella console compare la cronaca di quello che il robot vede.
"""

import color
import color_sensor
import motor_pair
import runloop
from hub import motion_sensor, port

#: Il sensore di colore guarda in basso, verso il tappeto.
PORTA_SENSORE = port.C

VELOCITA = 400  # gradi al secondo mentre va dritto
VELOCITA_GIRATA = 300  # gradi al secondo durante una curva sul posto

#: Una mattonella è larga 100 mm. Con la ruota da 56 mm del drive base:
#:   100 mm * 360 / (pi * 56 mm) = 204.63 gradi di ruota.
#: Se cambi il lato delle mattonelle, ricalcola questo numero.
GRADI_PER_MATTONELLA = 204.63

NOVANTA_GRADI = 900  # il giroscopio conta in decimi di grado
MASSIMO_PASSI = 100  # rete di sicurezza: non restare mai in ciclo infinito

#: Nomi leggibili, per la cronaca nella console.
NOMI = {
    color.BLACK: "dritto",
    color.BLUE: "partenza",
    color.GREEN: "curva a sinistra",
    color.RED: "curva a destra",
    color.YELLOW: "arrivo",
    color.WHITE: "fuori pista",
    color.UNKNOWN: "buio",
}


async def avanza():
    """Percorre una mattonella, dritto davanti a sé."""
    await motor_pair.move_for_degrees(
        motor_pair.PAIR_1, GRADI_PER_MATTONELLA, 0, velocity=VELOCITA
    )


async def gira(a_sinistra):
    """Ruota di 90 gradi sul posto, restando al centro della mattonella."""
    motion_sensor.reset_yaw(0)
    if a_sinistra:
        # Ruota sinistra indietro, destra avanti: il robot gira a sinistra
        # attorno al proprio centro, senza spostarsi.
        motor_pair.move_tank(motor_pair.PAIR_1, -VELOCITA_GIRATA, VELOCITA_GIRATA)
    else:
        motor_pair.move_tank(motor_pair.PAIR_1, VELOCITA_GIRATA, -VELOCITA_GIRATA)
    await runloop.until(lambda: abs(motion_sensor.tilt_angles()[0]) >= NOVANTA_GRADI)
    motor_pair.stop(motor_pair.PAIR_1)


async def main():
    motor_pair.pair(motor_pair.PAIR_1, port.A, port.B)
    print("seguilinea: parto")

    for passo in range(MASSIMO_PASSI):
        visto = color_sensor.color(PORTA_SENSORE)
        riflessione = color_sensor.reflection(PORTA_SENSORE)
        print(
            "passo", passo, "->", NOMI.get(visto, "sconosciuta"),
            "- riflessione", riflessione,
        )

        if visto == color.YELLOW:
            print("arrivato!")
            break

        if visto == color.GREEN:
            print("curva a sinistra")
            await gira(True)
        elif visto == color.RED:
            print("curva a destra")
            await gira(False)
        elif visto != color.BLACK and visto != color.BLUE:
            # UNKNOWN: troppo buio per vedere i colori. WHITE: fuori pista.
            print("non vedo più la pista: mi fermo")
            break

        # Girato (o dritto): lascia la mattonella appena letta.
        await avanza()

    motor_pair.stop(motor_pair.PAIR_1)
    print("seguilinea: fine")


runloop.run(main())
