"""Configurazione dell'hardware simulato.

Descrive cosa è collegato a ogni porta del hub e i parametri fisici del
drive base. È l'unica fonte di verità condivisa fra GUI, checker e runtime:
viene serializzata in JSON per essere passata al processo che esegue il
programma utente (`spikesim.runner`).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .mat import Mat

# --- Porte -----------------------------------------------------------------

PORT_A = 0
PORT_B = 1
PORT_C = 2
PORT_D = 3
PORT_E = 4
PORT_F = 5
PORTS = (PORT_A, PORT_B, PORT_C, PORT_D, PORT_E, PORT_F)
PORT_NAMES = {PORT_A: "A", PORT_B: "B", PORT_C: "C", PORT_D: "D", PORT_E: "E", PORT_F: "F"}

# --- Tipi di dispositivo ---------------------------------------------------

EMPTY = "empty"
MOTOR_SMALL = "motor_small"
MOTOR_MEDIUM = "motor_medium"
MOTOR_LARGE = "motor_large"
COLOR_SENSOR = "color_sensor"
DISTANCE_SENSOR = "distance_sensor"
FORCE_SENSOR = "force_sensor"
COLOR_MATRIX = "color_matrix"

MOTOR_KINDS = frozenset({MOTOR_SMALL, MOTOR_MEDIUM, MOTOR_LARGE})

#: Etichette italiane per la GUI.
DEVICE_LABELS = {
    EMPTY: "Nessuno",
    MOTOR_SMALL: "Motore piccolo (essential)",
    MOTOR_MEDIUM: "Motore medio",
    MOTOR_LARGE: "Motore grande",
    COLOR_SENSOR: "Sensore di colore",
    DISTANCE_SENSOR: "Sensore di distanza",
    FORCE_SENSOR: "Sensore di forza",
    COLOR_MATRIX: "Matrice colori 3x3",
}

#: Velocità massima (gradi/s) per tipo di motore, dalla documentazione SPIKE 3.
MOTOR_VELOCITY_LIMITS = {
    MOTOR_SMALL: 660,
    MOTOR_MEDIUM: 1110,
    MOTOR_LARGE: 1050,
}

#: Diametro della ruota del drive base SPIKE Prime (mm).
DEFAULT_WHEEL_DIAMETER_MM = 56.0

#: Distanza fra i centri delle due ruote motrici del drive base (mm).
DEFAULT_TRACK_WIDTH_MM = 112.0


@dataclass(frozen=True, slots=True)
class PortConfig:
    """Cosa è collegato a una porta."""

    device: str = EMPTY
    reversed: bool = False


@dataclass(frozen=True, slots=True)
class SensorValues:
    """Valori restituiti dai sensori simulati (impostabili dall'utente)."""

    color: int = 9  # color.RED
    reflection: int = 50  # percentuale
    distance: int = 200  # millimetri
    force: int = 0  # decinewton
    pressed: bool = False


@dataclass(frozen=True, slots=True)
class Config:
    """Configurazione completa della simulazione."""

    ports: dict[int, PortConfig] = field(default_factory=dict)
    wheel_diameter_mm: float = DEFAULT_WHEEL_DIAMETER_MM
    track_width_mm: float = DEFAULT_TRACK_WIDTH_MM
    #: Porte che reggono le ruote motrici del drive base: solo questi due
    #: motori fanno muovere il robot, gli altri muovono bracci o meccanismi.
    drive_left_port: int = PORT_A
    drive_right_port: int = PORT_B
    max_sim_time_ms: int = 120_000
    max_steps: int = 2_000_000
    sample_interval_ms: int = 20
    #: Limite di tempo *reale*: un programma che non cede mai il controllo
    #: (per esempio ``while True: pass``) viene interrotto dal watchdog.
    max_wall_seconds: float = 15.0
    sensors: SensorValues = field(default_factory=SensorValues)
    #: Il tappeto a mattonelle su cui si muove il robot. Senza tappeto il
    #: campo è vuoto e i sensori leggono i valori fissi qui sopra.
    mat: Mat | None = None
    #: Luce ambientale in percentuale: 100 è una stanza ben illuminata,
    #: sotto ``spikesim.mat.LIGHT_THRESHOLD`` il sensore non distingue più i
    #: colori.
    ambient_light: int = 100

    # -- interrogazioni ----------------------------------------------------

    def device(self, port: int) -> str:
        """Tipo di dispositivo sulla porta (``EMPTY`` se la porta è libera)."""
        spec = self.ports.get(port)
        return spec.device if spec else EMPTY

    def is_motor(self, port: int) -> bool:
        return self.device(port) in MOTOR_KINDS

    def velocity_limit(self, port: int) -> int:
        """Velocità massima consentita dal motore sulla porta."""
        return MOTOR_VELOCITY_LIMITS.get(self.device(port), 0)

    def is_drive_wheel(self, port: int) -> bool:
        return port in (self.drive_left_port, self.drive_right_port)

    def is_reversed(self, port: int) -> bool:
        spec = self.ports.get(port)
        return spec.reversed if spec else False

    def with_port(self, port: int, device: str, reversed_: bool = False) -> "Config":
        ports = dict(self.ports)
        ports[port] = PortConfig(device, reversed_)
        return replace(self, ports=ports)

    def with_sensors(self, **kwargs: object) -> "Config":
        return replace(self, sensors=replace(self.sensors, **kwargs))

    # -- serializzazione (verso il processo figlio) -------------------------

    def to_dict(self) -> dict:
        return {
            "ports": {
                str(port): {"device": spec.device, "reversed": spec.reversed}
                for port, spec in self.ports.items()
            },
            "wheel_diameter_mm": self.wheel_diameter_mm,
            "track_width_mm": self.track_width_mm,
            "drive_left_port": self.drive_left_port,
            "drive_right_port": self.drive_right_port,
            "max_sim_time_ms": self.max_sim_time_ms,
            "max_steps": self.max_steps,
            "sample_interval_ms": self.sample_interval_ms,
            "max_wall_seconds": self.max_wall_seconds,
            "ambient_light": self.ambient_light,
            "mat": self.mat.to_dict() if self.mat is not None else None,
            "sensors": {
                "color": self.sensors.color,
                "reflection": self.sensors.reflection,
                "distance": self.sensors.distance,
                "force": self.sensors.force,
                "pressed": self.sensors.pressed,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        ports = {
            int(port): PortConfig(spec.get("device", EMPTY), bool(spec.get("reversed", False)))
            for port, spec in data.get("ports", {}).items()
        }
        sensors = data.get("sensors", {})
        return cls(
            ports=ports,
            wheel_diameter_mm=float(data.get("wheel_diameter_mm", DEFAULT_WHEEL_DIAMETER_MM)),
            track_width_mm=float(data.get("track_width_mm", DEFAULT_TRACK_WIDTH_MM)),
            drive_left_port=int(data.get("drive_left_port", PORT_A)),
            drive_right_port=int(data.get("drive_right_port", PORT_B)),
            max_sim_time_ms=int(data.get("max_sim_time_ms", 120_000)),
            max_steps=int(data.get("max_steps", 2_000_000)),
            sample_interval_ms=int(data.get("sample_interval_ms", 20)),
            max_wall_seconds=float(data.get("max_wall_seconds", 15.0)),
            ambient_light=int(data.get("ambient_light", 100)),
            mat=Mat.from_dict(data["mat"]) if data.get("mat") else None,
            sensors=SensorValues(
                color=int(sensors.get("color", 9)),
                reflection=int(sensors.get("reflection", 50)),
                distance=int(sensors.get("distance", 200)),
                force=int(sensors.get("force", 0)),
                pressed=bool(sensors.get("pressed", False)),
            ),
        )


def default_config() -> Config:
    """Drive base SPIKE Prime standard: due motori medi sulle porte A e B."""
    return Config(
        ports={
            PORT_A: PortConfig(MOTOR_MEDIUM),
            PORT_B: PortConfig(MOTOR_MEDIUM),
            PORT_C: PortConfig(EMPTY),
            PORT_D: PortConfig(EMPTY),
            PORT_E: PortConfig(EMPTY),
            PORT_F: PortConfig(EMPTY),
        }
    )
