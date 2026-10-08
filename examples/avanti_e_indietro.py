"""Movimenti di base con ``motor_pair``, con i messaggi di avanzamento."""

import motor_pair
import runloop
from hub import port


async def main():
    motor_pair.pair(motor_pair.PAIR_1, port.A, port.B)

    print("avanti")
    await motor_pair.move_for_degrees(motor_pair.PAIR_1, 360, 0, velocity=720)

    print("indietro")
    await motor_pair.move_for_degrees(motor_pair.PAIR_1, 360, 0, velocity=-720)

    print("curva a destra")
    await motor_pair.move_for_degrees(motor_pair.PAIR_1, 720, 50, velocity=500)

    print("fine")


runloop.run(main())
