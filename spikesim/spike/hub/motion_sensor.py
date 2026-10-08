"""``hub.motion_sensor``: giroscopio, accelerometro e gesti del hub.

Nella simulazione imu e drive base sono la stessa cosa: lo yaw segue
l'orientamento del robot, così un programma che gira di 90 gradi leggendo
``tilt_angles()`` funziona davvero. Accelerometro, gesti e tocchi sono
fissi, perché il hub simulato è appoggiato e fermo.
"""

from __future__ import annotations

import math

from ...errors import InvalidArgumentError
from .. import _consts as K
from ...runtime import hardware

TAPPED = K.GESTURE_TAPPED
DOUBLE_TAPPED = K.GESTURE_DOUBLE_TAPPED
SHAKEN = K.GESTURE_SHAKEN
FALLING = K.GESTURE_FALLING
UNKNOWN = K.GESTURE_UNKNOWN

TOP = K.FACE_TOP
FRONT = K.FACE_FRONT
RIGHT = K.FACE_RIGHT
BOTTOM = K.FACE_BOTTOM
BACK = K.FACE_BACK
LEFT = K.FACE_LEFT

_FACES = (TOP, FRONT, RIGHT, BOTTOM, BACK, LEFT)
#: Accelerazione di gravità in milli-g, hub appoggiato sul lato con la matrice.
_GRAVITY_MG = 1000


def yaw() -> float:
    """Yaw corrente in decimi di grado (utile anche ai test)."""
    hw = hardware()
    return hw.pose.heading * 10.0 - hw.yaw_offset_decidegrees


def tilt_angles() -> tuple[int, int, int]:
    """(yaw, pitch, roll) in decimi di grado; pitch e roll sono 0."""
    value = yaw()
    return (int(round(value)), 0, 0)


def reset_yaw(angle: int) -> None:
    """Rende ``angle`` (decimi di grado) il nuovo valore di yaw."""
    hw = hardware()
    hw.yaw_offset_decidegrees = hw.pose.heading * 10.0 - float(angle)


def angular_velocity(raw_unfiltered: bool = False) -> tuple[int, int, int]:
    """Velocità angolare (x, y, z) in decimi di grado al secondo.

    L'asse z è quello verticale: ruota con il robot.
    """
    hw = hardware()
    left, right = hw.drive_velocities()
    if hw.config.track_width_mm <= 0:
        return (0, 0, 0)
    # Velocità lineari delle ruote -> velocità angolare del robot.
    mm_per_degree = math.pi * hw.config.wheel_diameter_mm / 360.0
    omega_deg_s = (right - left) * mm_per_degree / hw.config.track_width_mm
    return (0, 0, int(round(omega_deg_s * 10.0)))


def acceleration(raw_unfiltered: bool = False) -> tuple[int, int, int]:
    """Accelerazione (x, y, z) in milli-g: solo la gravità, hub fermo."""
    return (0, 0, _GRAVITY_MG)


def quaternion() -> tuple[float, float, float, float]:
    """Orientamento del hub come quaternione (w, x, y, z)."""
    half = math.radians(yaw() / 10.0) / 2.0
    return (math.cos(half), 0.0, 0.0, math.sin(half))


def stable() -> bool:
    """Il hub simulato è sempre appoggiato e fermo."""
    return True


def gesture() -> int:
    """Nessun gesto: il hub simulato non viene scosso né toccato."""
    return UNKNOWN


def tap_count() -> int:
    """Numero di tocchi riconosciuti: sempre 0 nella simulazione."""
    return 0


def reset_tap_count() -> None:
    """Azzera il contatore dei tocchi (no-op nella simulazione)."""
    return None


def up_face() -> int:
    """Faccia rivolta verso l'alto: il hub è appoggiato con la matrice in alto."""
    return TOP


def get_yaw_face() -> int:
    """Faccia rispetto a cui è misurato lo yaw."""
    hw = hardware()
    return hw.yaw_face


def set_yaw_face(up: int) -> bool:
    """Cambia la faccia rispetto a cui è misurato lo yaw."""
    hw = hardware()
    if up not in _FACES:
        raise InvalidArgumentError(
            f"faccia non valida: {up!r}; usa una costante TOP/FRONT/RIGHT/"
            "BOTTOM/BACK/LEFT di motion_sensor."
        )
    hw.yaw_face = up
    return True
