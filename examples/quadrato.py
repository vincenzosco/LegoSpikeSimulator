"""Percorso quadrato: quattro lati e quattro curve da 90 gradi.

Mostra l'uso combinato di ``motor_pair`` (per avanzare) e di
``motion_sensor`` (per misurare l'angolo di sterzata): è il programma che
si scrive per primo quando si vuole un robot che si orienta da solo.

Con le impostazioni predefinite (ruota da 56 mm, distanza fra le ruote di
112 mm) 740 gradi di ruota sono circa 36 cm di avanzamento.
"""

import motor_pair
import runloop
from hub import motion_sensor, port

LATO_IN_GRADI = 740
NOVANTA_GRADI = 900  # il giroscopio conta in decimi di grado

VELOCITA = 500
VELOCITA_STERZATA = 300


async def lato():
    """Avanza dritto per un lato del quadrato."""
    await motor_pair.move_for_degrees(motor_pair.PAIR_1, LATO_IN_GRADI, 0, velocity=VELOCITA)


async def curva():
    """Ruota sul posto finché il giroscopio non ha misurato 90 gradi."""
    motor_pair.move_tank(motor_pair.PAIR_1, VELOCITA_STERZATA, -VELOCITA_STERZATA)
    await runloop.until(lambda: abs(motion_sensor.tilt_angles()[0]) >= NOVANTA_GRADI)
    motor_pair.stop(motor_pair.PAIR_1)


async def main():
    motor_pair.pair(motor_pair.PAIR_1, port.A, port.B)

    for numero in range(1, 5):
        print("lato", numero)
        await lato()
        motion_sensor.reset_yaw(0)
        await curva()

    print("quadrato completato")


runloop.run(main())
