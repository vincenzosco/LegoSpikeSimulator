"""Traccia di una simulazione: eventi, pose e diagnostica.

La traccia è il contratto fra il processo che esegue il programma utente
(`spikesim.runner`) e la GUI: il runner produce un documento JSON, la GUI lo
consuma. Tenere il formato in un unico posto evita che i due lati divergano.

Struttura JSON::

    {
      "program": "/percorso/programma.py",
      "duration_ms": 1500,          # tempo *simulato* trascorso
      "terminated": true,           # il programma è finito da solo
      "poses": [[t, x, y, heading], ...],
      "events": [{"t": 0, "type": "print", "data": {"text": "ciao"}}, ...],
      "diagnostics": [{"severity": "error", "code": "...", ...}]
    }
"""

from __future__ import annotations

import json
import traceback
from dataclasses import dataclass, field
from typing import Any, Iterable

#: Tipi di evento che la GUI sa disegnare. Un tipo sconosciuto è un errore di
#: versione fra runner e GUI, non un evento da ignorare in silenzio.
EVENT_TYPES = frozenset(
    {
        "print",  # {"text": str}
        "note",  # {"text": str, "level": str}
        "motor",  # {"port": int, "velocity": float, "status": int | None}
        "motor_pair",  # {"pair": int, "left": int, "right": int}
        "light_matrix",  # {"pixels": [25 x int]}
        "light_matrix_text",  # {"text": str}
        "hub_light",  # {"light": int, "color": int}
        "sound",  # {"freq": int, "duration": int}
    }
)

SEVERITIES = ("error", "warning", "info")


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """Un singolo messaggio per l'utente, con l'eventuale riga di codice."""

    severity: str
    code: str
    message: str
    line: int | None = None
    column: int | None = None
    detail: str = ""

    def __post_init__(self) -> None:
        if self.severity not in SEVERITIES:
            raise ValueError(f"severità non valida: {self.severity!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Diagnostic":
        return cls(
            severity=data["severity"],
            code=data["code"],
            message=data["message"],
            line=data.get("line"),
            column=data.get("column"),
            detail=data.get("detail", ""),
        )


@dataclass(frozen=True, slots=True)
class Event:
    """Qualcosa che è successo al tempo simulato ``t`` (millisecondi)."""

    t: int
    type: str
    data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.type not in EVENT_TYPES:
            raise ValueError(f"tipo di evento sconosciuto: {self.type!r}")

    def to_dict(self) -> dict[str, Any]:
        return {"t": self.t, "type": self.type, "data": self.data}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        return cls(t=int(data["t"]), type=data["type"], data=dict(data.get("data", {})))


@dataclass
class Trace:
    """Risultato completo di una simulazione."""

    program: str
    duration_ms: int
    terminated: bool
    poses: list[tuple[int, float, float, float]]
    events: list[Event]
    diagnostics: list[Diagnostic]

    # -- interrogazioni ----------------------------------------------------

    def count(self, severity: str) -> int:
        return sum(1 for d in self.diagnostics if d.severity == severity)

    @property
    def ok(self) -> bool:
        return self.count("error") == 0

    def pose_at(self, t_ms: float) -> tuple[float, float, float]:
        """Posizione interpolata al tempo ``t_ms`` (clampata agli estremi)."""
        if not self.poses:
            return (0.0, 0.0, 0.0)
        if t_ms <= self.poses[0][0]:
            return self.poses[0][1:]
        if t_ms >= self.poses[-1][0]:
            return self.poses[-1][1:]
        # Le pose sono poche migliaia: una scansione lineare è più che
        # sufficiente e non richiede struttura dati aggiuntiva.
        for previous, following in zip(self.poses, self.poses[1:]):
            if t_ms <= following[0]:
                span = following[0] - previous[0]
                alpha = 0.0 if span == 0 else (t_ms - previous[0]) / span
                return (
                    previous[1] + (following[1] - previous[1]) * alpha,
                    previous[2] + (following[2] - previous[2]) * alpha,
                    previous[3] + (following[3] - previous[3]) * alpha,
                )
        return self.poses[-1][1:]

    def events_until(self, t_ms: float, types: Iterable[str] | None = None) -> list[Event]:
        wanted = set(types) if types is not None else None
        return [
            event
            for event in self.events
            if event.t <= t_ms and (wanted is None or event.type in wanted)
        ]

    # -- serializzazione ----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "program": self.program,
            "duration_ms": self.duration_ms,
            "terminated": self.terminated,
            "poses": [list(pose) for pose in self.poses],
            "events": [event.to_dict() for event in self.events],
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Trace":
        return cls(
            program=data.get("program", ""),
            duration_ms=int(data.get("duration_ms", 0)),
            terminated=bool(data.get("terminated", False)),
            poses=[tuple(pose) for pose in data.get("poses", [])],
            events=[Event.from_dict(event) for event in data.get("events", [])],
            diagnostics=[Diagnostic.from_dict(d) for d in data.get("diagnostics", [])],
        )


def to_json(trace: Trace, *, indent: int | None = None) -> str:
    """Serializza la traccia in JSON.

    ``ensure_ascii=False`` mantiene leggibili i messaggi in italiano.
    """
    return json.dumps(trace.to_dict(), ensure_ascii=False, indent=indent)


def from_json(text: str) -> Trace:
    """Deserializza una traccia; solleva ``ValueError`` su eventi sconosciuti."""
    return Trace.from_dict(json.loads(text))


def user_line_from_exception(exc: BaseException, program_filename: str) -> int | None:
    """Riga del file dell'utente più interna coinvolta nell'eccezione.

    È la riga che l'utente deve correggere, non l'interno della libreria.
    """
    line: int | None = None
    for frame, lineno in traceback.walk_tb(exc.__traceback__):
        if frame.f_code.co_filename == program_filename:
            line = lineno
    return line


def format_exception(exc: BaseException) -> str:
    """Traceback completo, come testo."""
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).strip()


def diagnostics_from_exception(
    exc: BaseException, program_filename: str
) -> list[Diagnostic]:
    """Trasforma un'eccezione del programma utente in una diagnostica."""
    line = user_line_from_exception(exc, program_filename)
    detail = format_exception(exc)
    return [
        Diagnostic(
            severity="error",
            code="PYTHON",
            message=f"{type(exc).__name__}: {exc}",
            line=line,
            detail=detail.strip(),
        )
    ]
