"""``motor``: controllo dei singoli motori.

Convenzione di verso usata dalla simulazione: il motore percorre
``degrees * sign(velocity)`` gradi, cioè il verso dipende dal segno di
``velocity``, come sull'hardware vero.
"""

from __future__ import annotations

import math

from ..errors import InvalidArgumentError
from ..runtime import MotorState, hardware
from . import _consts as K

READY = K.MOTOR_READY
RUNNING = K.MOTOR_RUNNING
STALLED = K.MOTOR_STALLED
CANCELLED = K.MOTOR_CANCELLED
#: La documentazione SPIKE 3 scrive sia ``CANCELED`` sia ``CANCELLED``.
CANCELED = K.MOTOR_CANCELLED
ERROR = K.MOTOR_ERROR
DISCONNECTED = K.MOTOR_DISCONNECTED

COAST = K.MOTOR_COAST
BRAKE = K.MOTOR_BRAKE
HOLD = K.MOTOR_HOLD
CONTINUE = K.MOTOR_CONTINUE
SMART_COAST = K.MOTOR_SMART_COAST
SMART_BRAKE = K.MOTOR_SMART_BRAKE

CLOCKWISE = K.MOTOR_CLOCKWISE
COUNTERCLOCKWISE = K.MOTOR_COUNTERCLOCKWISE
SHORTEST_PATH = K.MOTOR_SHORTEST_PATH
LONGEST_PATH = K.MOTOR_LONGEST_PATH

__all__ = [
    "run", "run_for_degrees", "run_for_time", "run_to_absolute_position",
    "run_to_relative_position", "stop", "set_duty_cycle", "get_duty_cycle",
    "absolute_position", "relative_position", "velocity", "reset_relative_position",
]


def _speed(value, hw, state: MotorState) -> float:
    """Velocità in gradi/s, limitata a quella massima del motore."""
    try:
        speed = float(value)
    except (TypeError, ValueError) as exc:
        raise InvalidArgumentError(
            f"velocità non valida: {value!r}; usa un intero in gradi al secondo."
        ) from exc
    limit = hw.config.velocity_limit(state.port)
    if limit and abs(speed) > limit:
        hw.note(
            "warning",
            "SPIKE033",
            f"velocità {speed:.0f} °/s fuori intervallo per questo motore "
            f"(-{limit}..{limit}): limitata a {limit}.",
            line=hw.caller_line(),
        )
        speed = math.copysign(limit, speed)
    return speed


def _degrees(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise InvalidArgumentError(
            f"angolo non valido: {value!r}; usa un numero di gradi."
        ) from exc


def _direction(degrees: float, velocity: float) -> float:
    """Verso effettivo del movimento (1 avanti, -1 indietro)."""
    return math.copysign(1.0, degrees * velocity) if velocity else math.copysign(1.0, degrees)


def run(port: int, velocity: int, *, acceleration: int = 1000) -> None:
    """Avvia il motore a velocità costante finché non arriva un altro comando."""
    hw = hardware()
    state = hw.motor(port)
    speed = _speed(velocity, hw, state)
    hw.cancel_move(state)
    state.velocity = speed
    state.status = K.MOTOR_RUNNING if speed else K.MOTOR_READY
    hw.motor_changed(state)


def stop(port: int, *, stop: int = BRAKE) -> None:
    """Ferma il motore."""
    hw = hardware()
    state = hw.motor(port)
    hw.cancel_move(state)
    state.status = K.MOTOR_READY
    state.finish(hw)


def run_for_degrees(
    port: int,
    degrees: int,
    velocity: int,
    *,
    stop: int = BRAKE,
    acceleration: int = 1000,
    deceleration: int = 1000,
):
    """Gira il motore di ``degrees`` gradi e restituisce un awaitable."""
    hw = hardware()
    state = hw.motor(port)
    speed = _speed(velocity, hw, state)
    travel = _degrees(degrees)
    if speed == 0:
        raise InvalidArgumentError(
            "run_for_degrees() richiede una velocità diversa da 0: con velocità 0 "
            "il motore non raggiungerebbe mai la posizione richiesta."
        )
    direction = _direction(travel, velocity)
    duration = abs(travel) / abs(speed) * 1000.0
    return hw.start_motor_move(
        state,
        velocity=math.copysign(abs(speed), direction),
        duration_ms=duration,
        target_position=state.position + direction * abs(travel),
        stop_behavior=stop,
        label=f"motor.run_for_degrees(porta {state.port}, {travel:g}, {speed:g})",
    )


def run_for_time(
    port: int,
    duration: int,
    velocity: int,
    *,
    stop: int = BRAKE,
    acceleration: int = 1000,
    deceleration: int = 1000,
):
    """Gira il motore per ``duration`` millisecondi e restituisce un awaitable."""
    hw = hardware()
    state = hw.motor(port)
    speed = _speed(velocity, hw, state)
    try:
        milliseconds = float(duration)
    except (TypeError, ValueError) as exc:
        raise InvalidArgumentError(
            f"durata non valida: {duration!r}; usa millisecondi."
        ) from exc
    if milliseconds < 0:
        raise InvalidArgumentError(
            f"durata negativa: {duration!r}."
        )
    return hw.start_motor_move(
        state,
        velocity=speed,
        duration_ms=milliseconds,
        stop_behavior=stop,
        label=f"motor.run_for_time(porta {state.port}, {milliseconds:g} ms)",
    )


def _absolute_target(current: float, position: float, direction: int) -> float:
    """Posizione assoluta da raggiungere (le posizioni si ripetono ogni 360°)."""
    candidates = [position - 360.0, position, position + 360.0]
    if direction == SHORTEST_PATH:
        return min(candidates, key=lambda value: abs(value - current))
    if direction == LONGEST_PATH:
        return max(candidates, key=lambda value: abs(value - current))
    if direction == CLOCKWISE:
        return min(
            (value for value in candidates if value >= current),
            key=lambda value: value,
            default=position + 360.0,
        )
    return max(
        (value for value in candidates if value <= current),
        key=lambda value: value,
        default=position - 360.0,
    )


def run_to_absolute_position(
    port: int,
    position: int,
    velocity: int,
    *,
    direction: int = SHORTEST_PATH,
    stop: int = BRAKE,
    acceleration: int = 1000,
    deceleration: int = 1000,
):
    """Porta il motore a una posizione assoluta e restituisce un awaitable."""
    hw = hardware()
    state = hw.motor(port)
    speed = _speed(velocity, hw, state)
    if speed == 0:
        raise InvalidArgumentError(
            "run_to_absolute_position() richiede una velocità diversa da 0."
        )
    if direction not in (CLOCKWISE, COUNTERCLOCKWISE, SHORTEST_PATH, LONGEST_PATH):
        raise InvalidArgumentError(
            f"direzione non valida: {direction!r}; usa motor.CLOCKWISE, "
            "COUNTERCLOCKWISE, SHORTEST_PATH o LONGEST_PATH."
        )
    target = _absolute_target(state.position, _degrees(position), direction)
    return hw.start_motor_move(
        state,
        velocity=math.copysign(abs(speed), target - state.position),
        duration_ms=abs(target - state.position) / abs(speed) * 1000.0,
        target_position=target,
        stop_behavior=stop,
        label=f"motor.run_to_absolute_position(porta {state.port}, {position:g})",
    )


def run_to_relative_position(
    port: int,
    position: int,
    velocity: int,
    *,
    stop: int = BRAKE,
    acceleration: int = 1000,
    deceleration: int = 1000,
):
    """Porta il motore a una posizione relativa e restituisce un awaitable."""
    hw = hardware()
    state = hw.motor(port)
    speed = _speed(velocity, hw, state)
    if speed == 0:
        raise InvalidArgumentError(
            "run_to_relative_position() richiede una velocità diversa da 0."
        )
    target = state.relative_offset + _degrees(position)
    return hw.start_motor_move(
        state,
        velocity=math.copysign(abs(speed), target - state.position),
        duration_ms=abs(target - state.position) / abs(speed) * 1000.0,
        target_position=target,
        stop_behavior=stop,
        label=f"motor.run_to_relative_position(porta {state.port}, {position:g})",
    )


def absolute_position(port: int) -> int:
    """Posizione assoluta del motore, in gradi."""
    return int(round(hardware().motor(port).position))


def relative_position(port: int) -> int:
    """Posizione del motore rispetto all'ultimo ``reset_relative_position``."""
    state = hardware().motor(port)
    return int(round(state.position - state.relative_offset))


def reset_relative_position(port: int, position: int) -> None:
    """Rende ``position`` la nuova posizione relativa del motore."""
    state = hardware().motor(port)
    state.relative_offset = state.position - _degrees(position)


def velocity(port: int) -> int:
    """Velocità corrente del motore in gradi al secondo."""
    return int(round(hardware().motor(port).velocity))


def get_duty_cycle(port: int) -> int:
    """Ciclo di lavoro (PWM) del motore, da 0 a 10000."""
    hw = hardware()
    state = hw.motor(port)
    limit = hw.config.velocity_limit(state.port)
    if not limit or state.velocity == 0:
        return 0
    return int(round(state.velocity / limit * 10000))


def set_duty_cycle(port: int, pwm: int) -> None:
    """Avvia il motore con un PWM da -10000 a 10000."""
    hw = hardware()
    state = hw.motor(port)
    try:
        value = int(pwm)
    except (TypeError, ValueError) as exc:
        raise InvalidArgumentError(
            f"PWM non valido: {pwm!r}; usa un intero da -10000 a 10000."
        ) from exc
    if not -10000 <= value <= 10000:
        raise InvalidArgumentError(
            f"PWM {value} fuori intervallo: usa un valore da -10000 a 10000."
        )
    limit = hw.config.velocity_limit(state.port)
    hw.cancel_move(state)
    state.duty_cycle = value
    state.velocity = value / 10000.0 * limit
    state.status = K.MOTOR_RUNNING if value else K.MOTOR_READY
    hw.motor_changed(state)
