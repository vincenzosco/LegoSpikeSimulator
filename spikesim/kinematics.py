"""Cinematica di un drive base a due ruote.

Funzioni pure, senza stato globale e senza dipendenze da Qt: sono il cuore
del modello fisico e vengono usate dallo scheduler per integrare il movimento
del robot nel tempo.

Convenzioni (valide in tutto il simulatore):

* lunghezze in millimetri, angoli in gradi, tempo in millisecondi;
* il campo è il piano matematico: ``+x`` verso est, ``+y`` verso nord;
* ``heading`` è la direzione puntata dal robot, ``0`` = est, crescente in
  senso antiorario (quindi ``90`` = nord).

Nel modello LEGO lo sterzo segue la convenzione dei blocchi Word di SPIKE:

* ``steering = 0``   → dritto (entrambe le ruote alla stessa velocità);
* ``steering = 100`` → sterzata a destra (ruota sinistra accelerata, destra ferma);
* ``steering = -100``→ sterzata a sinistra (ruota sinistra ferma, destra accelerata).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

#: Sotto questa velocità angolare il movimento è trattato come rettilineo,
#: per evitare di dividere per un ``omega`` che è solo rumore numerico.
_OMEGA_EPS = 1e-12


@dataclass(frozen=True, slots=True)
class Pose:
    """Posizione e orientamento del robot sul campo."""

    x: float = 0.0
    y: float = 0.0
    heading: float = 0.0

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.heading)


def motor_degrees_to_mm(degrees: float, wheel_diameter_mm: float) -> float:
    """Spazio percorso da una ruota che ruota di ``degrees`` gradi."""
    return math.pi * wheel_diameter_mm * degrees / 360.0


def motor_to_mm_s(velocity_deg_s: float, wheel_diameter_mm: float) -> float:
    """Velocità lineare della ruota (mm/s) da una velocità in gradi/s."""
    return motor_degrees_to_mm(velocity_deg_s, wheel_diameter_mm)


def steering_to_wheel_velocities(
    velocity: float, steering: float
) -> tuple[float, float]:
    """Velocità (sinistra, destra) in gradi/s da velocità e sterzo LEGO.

    ``steering`` è limitato a ``[-100, 100]``; i valori fuori intervallo
    vengono saturati come fa il firmware del hub.
    """
    s = max(-100.0, min(100.0, float(steering)))
    velocity = float(velocity)
    return (velocity * (1.0 + s / 100.0), velocity * (1.0 - s / 100.0))


def integrate(
    pose: Pose,
    left_mm_s: float,
    right_mm_s: float,
    dt_ms: float,
    track_width_mm: float,
) -> Pose:
    """Avanza ``pose`` di ``dt_ms`` con le due ruote a velocità costante.

    Usa la soluzione esatta del moto a curvatura costante (arco di cerchio),
    non un'approssimazione a passi: il risultato è preciso per qualunque
    ``dt`` e il percorso è esattamente un arco.
    """
    if dt_ms <= 0:
        return pose

    dt = dt_ms / 1000.0
    v = 0.5 * (left_mm_s + right_mm_s)
    omega = (right_mm_s - left_mm_s) / track_width_mm if track_width_mm > 0 else 0.0

    if abs(omega) < _OMEGA_EPS:
        if v == 0.0:
            return pose
        h = math.radians(pose.heading)
        return Pose(
            pose.x + v * math.cos(h) * dt,
            pose.y + v * math.sin(h) * dt,
            pose.heading,
        )

    radius = v / omega
    theta = omega * dt
    h0 = math.radians(pose.heading)
    h1 = h0 + theta
    return Pose(
        pose.x + radius * (math.sin(h1) - math.sin(h0)),
        pose.y - radius * (math.cos(h1) - math.cos(h0)),
        pose.heading + math.degrees(theta),
    )
