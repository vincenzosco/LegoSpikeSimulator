"""``motor_pair``: due motori sincronizzati, cioè il drive base.

Il numero di gradi richiesto è la rotazione della ruota più veloce: le
ruote seguono la proporzione dello sterzo. Con ``steering = 0`` entrambe le
ruote compiono esattamente ``degrees`` gradi; con ``steering = 100`` la ruota
sinistra compie tutti i gradi e la destra resta ferma (il robot ruota sul
posto attorno alla ruota destra).
"""

from __future__ import annotations

import math

from ..errors import InvalidArgumentError, NotPairedError
from ..kinematics import steering_to_wheel_velocities
from ..runtime import MotorState, hardware
from . import _consts as K
from . import motor

PAIR_1 = K.PAIR_1
PAIR_2 = K.PAIR_2
PAIR_3 = K.PAIR_3

_PAIRS = (PAIR_1, PAIR_2, PAIR_3)

__all__ = [
    "pair", "unpair", "move", "move_for_degrees", "move_for_time", "move_tank",
    "move_tank_for_degrees", "move_tank_for_time", "stop",
]


def _check_pair_number(pair: int) -> int:
    if pair not in _PAIRS:
        raise InvalidArgumentError(
            f"coppia non valida: {pair!r}; usa motor_pair.PAIR_1, PAIR_2 o PAIR_3."
        )
    return pair


def _motors(pair: int) -> tuple[MotorState, MotorState]:
    hw = hardware()
    _check_pair_number(pair)
    if pair not in hw.pairs:
        raise NotPairedError(
            f"la coppia {pair} non esiste: chiama prima "
            f"motor_pair.pair(motor_pair.PAIR_{pair + 1}, <motore sinistro>, "
            "<motore destro>)."
        )
    left_port, right_port = hw.pairs[pair]
    return hw.motors[left_port], hw.motors[right_port]


def _check_steering(hw, steering) -> float:
    try:
        value = float(steering)
    except (TypeError, ValueError) as exc:
        raise InvalidArgumentError(
            f"sterzo non valido: {steering!r}; usa un intero da -100 a 100."
        ) from exc
    if not -100 <= value <= 100:
        hw.note(
            "warning",
            "SPIKE034",
            f"sterzo {value:g} fuori dall'intervallo -100..100: limitato.",
            line=hw.caller_line(),
        )
        value = max(-100.0, min(100.0, value))
    return value


def _speeds(velocity) -> tuple[float, float]:
    try:
        value = float(velocity)
    except (TypeError, ValueError) as exc:
        raise InvalidArgumentError(
            f"velocità non valida: {velocity!r}; usa la velocità in gradi al secondo."
        ) from exc
    if value == 0:
        raise InvalidArgumentError(
            "la velocità non può essere 0: il movimento non avrebbe durata."
        )
    return (value, value)


def pair(pair: int, left_motor: int, right_motor: int) -> None:
    """Associa due motori a una coppia."""
    hw = hardware()
    _check_pair_number(pair)
    left = hw.motor(left_motor)
    right = hw.motor(right_motor)
    if left.port == right.port:
        raise InvalidArgumentError(
            "i due motori di una coppia devono essere su porte diverse."
        )
    hw.pairs[pair] = (left.port, right.port)
    from .hub.port import A, B, C, D, E, F

    names = {A: "A", B: "B", C: "C", D: "D", E: "E", F: "F"}
    hw.emit(
        "note",
        text=f"coppia {pair} creata: sinistra={names[left.port]}, destra={names[right.port]}",
        level="info",
    )


def unpair(pair: int) -> None:
    """Scioglie una coppia."""
    hw = hardware()
    _check_pair_number(pair)
    hw.pairs.pop(pair, None)


def stop(pair: int, *, stop: int = motor.BRAKE) -> None:
    """Ferma entrambi i motori della coppia."""
    hw = hardware()
    left, right = _motors(pair)
    for state in (left, right):
        hw.cancel_move(state)
        state.status = K.MOTOR_READY
        state.finish(hw)


def _start_pair_move(
    hw,
    pair: int,
    velocities: tuple[float, float],
    *,
    degrees: float | None,
    duration_ms: float | None,
    stop_behavior: int,
    label: str,
):
    """Avvia entrambi i motori con un'unica attesa condivisa."""
    left, right = _motors(pair)
    scale = max(abs(velocities[0]), abs(velocities[1]))
    if scale == 0:
        raise InvalidArgumentError(
            "le due ruote sono ferme: il movimento non avrebbe durata."
        )
    if degrees is not None:
        travel = [degrees * (value / scale) for value in velocities]
        duration = abs(degrees) / scale * 1000.0
        awaitable = hw.awaitable(
            kind="motor_pair",
            label=label,
            ready_at=hw.t_ms + math.ceil(duration),
            result=K.MOTOR_READY,
        )
        for state, value, distance in zip((left, right), velocities, travel):
            hw.start_motor_move(
                state,
                velocity=math.copysign(abs(value), distance) if distance else 0.0,
                duration_ms=duration,
                target_position=state.position + distance,
                stop_behavior=stop_behavior,
                label=label,
                awaitable=awaitable,
            )
        return awaitable

    duration = float(duration_ms or 0)
    awaitable = hw.awaitable(
        kind="motor_pair",
        label=label,
        ready_at=hw.t_ms + math.ceil(duration),
        result=K.MOTOR_READY,
    )
    for state, value in zip((left, right), velocities):
        hw.start_motor_move(
            state,
            velocity=value,
            duration_ms=duration,
            stop_behavior=stop_behavior,
            label=label,
            awaitable=awaitable,
        )
    return awaitable


def move(pair: int, steering: int, *, velocity: int = 360, acceleration: int = 1000) -> None:
    """Avanza curva alla velocità costante finché non arriva un altro comando."""
    hw = hardware()
    steering = _check_steering(hw, steering)
    left, right = _motors(pair)
    left_speed, right_speed = steering_to_wheel_velocities(float(velocity), steering)
    for state, value in ((left, left_speed), (right, right_speed)):
        hw.cancel_move(state)
        state.velocity = value
        state.status = K.MOTOR_RUNNING if value else K.MOTOR_READY
        hw.motor_changed(state)
    hw.emit("motor_pair", pair=pair, left=left_speed, right=right_speed)


def move_for_degrees(
    pair: int,
    degrees: int,
    steering: int,
    *,
    velocity: int = 360,
    stop: int = motor.BRAKE,
    acceleration: int = 1000,
    deceleration: int = 1000,
):
    """Avanza curva per ``degrees`` gradi e restituisce un awaitable."""
    hw = hardware()
    _speeds(velocity)
    steering = _check_steering(hw, steering)
    speeds = steering_to_wheel_velocities(float(velocity), steering)
    return _start_pair_move(
        hw,
        pair,
        speeds,
        degrees=float(degrees),
        duration_ms=None,
        stop_behavior=stop,
        label=f"motor_pair.move_for_degrees(coppia {pair}, {degrees:g}, sterzo {steering:g})",
    )


def move_for_time(
    pair: int,
    duration: int,
    steering: int,
    *,
    velocity: int = 360,
    stop: int = motor.BRAKE,
    acceleration: int = 1000,
    deceleration: int = 1000,
):
    """Avanza curva per ``duration`` millisecondi e restituisce un awaitable."""
    hw = hardware()
    _speeds(velocity)
    steering = _check_steering(hw, steering)
    speeds = steering_to_wheel_velocities(float(velocity), steering)
    return _start_pair_move(
        hw,
        pair,
        speeds,
        degrees=None,
        duration_ms=float(duration),
        stop_behavior=stop,
        label=f"motor_pair.move_for_time(coppia {pair}, {duration:g} ms, sterzo {steering:g})",
    )


def move_tank(
    pair: int, left_velocity: int, right_velocity: int, *, acceleration: int = 1000
) -> None:
    """Avanza con le due ruote a velocità indipendenti, senza fermarsi."""
    hw = hardware()
    left, right = _motors(pair)
    for state, value in ((left, float(left_velocity)), (right, float(right_velocity))):
        hw.cancel_move(state)
        state.velocity = value
        state.status = K.MOTOR_RUNNING if value else K.MOTOR_READY
        hw.motor_changed(state)
    hw.emit("motor_pair", pair=pair, left=float(left_velocity), right=float(right_velocity))


def move_tank_for_degrees(
    pair: int,
    degrees: int,
    left_velocity: int,
    right_velocity: int,
    *,
    stop: int = motor.BRAKE,
    acceleration: int = 1000,
    deceleration: int = 1000,
):
    """Combinazione tank per ``degrees`` gradi; restituisce un awaitable."""
    hw = hardware()
    return _start_pair_move(
        hw,
        pair,
        (float(left_velocity), float(right_velocity)),
        degrees=float(degrees),
        duration_ms=None,
        stop_behavior=stop,
        label=f"motor_pair.move_tank_for_degrees(coppia {pair}, {degrees:g})",
    )


def move_tank_for_time(
    pair: int,
    left_velocity: int,
    right_velocity: int,
    duration: int,
    *,
    stop: int = motor.BRAKE,
    acceleration: int = 1000,
    deceleration: int = 1000,
):
    """Combinazione tank per ``duration`` millisecondi; restituisce un awaitable."""
    hw = hardware()
    return _start_pair_move(
        hw,
        pair,
        (float(left_velocity), float(right_velocity)),
        degrees=None,
        duration_ms=float(duration),
        stop_behavior=stop,
        label=f"motor_pair.move_tank_for_time(coppia {pair}, {duration:g} ms)",
    )
