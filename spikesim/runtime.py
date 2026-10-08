"""Orologio virtuale, hardware simulato e scheduler cooperativo.

Il tempo della simulazione avanza solo quando *tutte* le attività sono in
attesa: `sleep_ms(1000)` costa qualche millisecondo reale, non un secondo.
È questo che rende la simulazione istantanea e riproducibile.

Modello fisico adottato (documentato anche nel README):

* solo i motori collegati alle due porte del drive base fanno muovere il
  robot; un motore su un'altra porta gira ma non sposta il robot (è un
  braccio o un meccanismo);
* la rotazione del motore si converte in spazio percorso dalla ruota
  conoscendo il diametro della ruota;
* non sono modellati attrito, inerzia e rampe di accelerazione: la velocità
  è costante per tutta la durata del comando.
"""

from __future__ import annotations

import heapq
import inspect
import itertools
import math
import sys
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from .config import (
    DEVICE_LABELS,
    PORT_NAMES,
    PORTS,
    Config,
    default_config,
)
from .errors import (
    InvalidArgumentError,
    NoDeviceError,
    NotAMotorError,
    PortOutOfRangeError,
    ProgramLimitError,
)
from .kinematics import Pose, integrate, motor_to_mm_s
from .mat import Surface, apply_light
from .spike import _consts as K
from .trace import Diagnostic, Event, Trace

#: Passo con cui viene integrata la fisica fra due eventi.
PHYSICS_STEP_MS = 5.0
#: Ogni quanto viene ricontrollata la condizione di ``runloop.until``.
POLL_INTERVAL_MS = 10.0
#: Tetto al numero di eventi registrati: protegge la memoria su cicli lunghi.
MAX_EVENTS = 20_000
#: Tetto al numero di diagnostiche registrate a runtime.
MAX_DIAGNOSTICS = 500
#: Quante "attese mai awaited" elencare prima di riassumere.
MAX_UNAWAITED_REPORTED = 10


# ---------------------------------------------------------------------------
# Sorgenti di attesa
# ---------------------------------------------------------------------------


class SpikeAwaitable:
    """Valore restituito dalle operazioni ``async`` della libreria SPIKE.

    Non è una coroutine: è un *biglietto* che lo scheduler risolve quando è
    il momento giusto. ``await`` su di esso restituisce il controllo allo
    scheduler, che riprende la coroutine quando ``ready_at`` è raggiunto
    (oppure quando ``predicate`` diventa vero, per ``runloop.until``).

    Un oggetto creato e mai atteso non fa *nulla*: è l'errore più comune di
    chi inizia, e `Hardware.finish` lo segnala esplicitamente.
    """

    __slots__ = (
        "kind", "ready_at", "result", "predicate", "deadline",
        "awaited", "resolved", "label", "line",
    )

    def __init__(
        self,
        *,
        kind: str,
        label: str = "",
        line: int | None = None,
        ready_at: float | None = None,
        result: Any = None,
        predicate: Callable[[], bool] | None = None,
        deadline: float | None = None,
    ) -> None:
        self.kind = kind
        self.label = label or kind
        self.line = line
        self.ready_at = ready_at
        self.result = result
        self.predicate = predicate
        self.deadline = deadline
        self.awaited = False
        self.resolved = False

    def __await__(self):  # pragma: no cover - il corpo gira nello scheduler
        self.awaited = True
        return (yield self)

    def __repr__(self) -> str:  # pragma: no cover - solo per il debug
        return f"<{self.label} awaitable t={self.ready_at}>"


@dataclass(slots=True)
class _Move:
    """Movimento in corso di un motore."""

    target_position: float | None = None
    end_ms: float | None = None
    stalled_reported: bool = False
    awaitable: SpikeAwaitable | None = None


@dataclass(slots=True)
class MotorState:
    """Stato di un motore collegato a una porta."""

    port: int
    kind: str
    velocity: float = 0.0  # gradi/s
    position: float = 0.0  # gradi, posizione assoluta del codificatore
    relative_offset: float = 0.0
    duty_cycle: int = 0
    status: int = K.MOTOR_READY
    stop_behavior: int = K.MOTOR_BRAKE
    move: _Move | None = None

    def step(self, dt_ms: float, hardware: "Hardware") -> None:
        """Avanza la posizione di ``dt_ms``; gestisce la fine del movimento."""
        move = self.move
        if move is None:
            self.position += self.velocity * dt_ms / 1000.0
            return

        if move.end_ms is not None and hardware.t_ms + dt_ms >= move.end_ms - 1e-9:
            self.position += self.velocity * dt_ms / 1000.0
            self.finish(hardware)
            return

        if move.target_position is None:
            self.position += self.velocity * dt_ms / 1000.0
            return

        delta = self.velocity * dt_ms / 1000.0
        remaining = move.target_position - self.position
        if remaining == 0.0:
            # Già a destinazione: succede quando il movimento richiesto è di 0
            # gradi, o alla ruota ferma di uno sterzo a fondo corsa. Non è uno
            # stallo: la posizione richiesta *è* quella raggiunta.
            self.position = move.target_position
            self.finish(hardware)
            return
        if delta != 0.0 and remaining * delta > 0 and abs(remaining) <= abs(delta):
            self.position = move.target_position
            self.finish(hardware)
            return
        if delta == 0.0:
            if not move.stalled_reported:
                move.stalled_reported = True
                hardware.note(
                    "warning",
                    "SPIKE019",
                    f"il motore sulla porta {PORT_NAMES[self.port]} non si muove "
                    "(velocità 0): la posizione richiesta non sarà raggiunta.",
                    line=hardware.caller_line(),
                )
            return
        self.position += delta

    def finish(self, hardware: "Hardware") -> None:
        self.velocity = 0.0
        self.duty_cycle = 0
        self.status = K.MOTOR_READY
        self.move = None
        hardware.motor_changed(self)


# ---------------------------------------------------------------------------
# Hardware
# ---------------------------------------------------------------------------


class Hardware:
    """Stato completo del hub simulato, più la registrazione della traccia."""

    def __init__(self, config: Config | None = None, *, program: str = "<programma>") -> None:
        self.config = config or default_config()
        self.program = program
        self.t_ms = 0.0
        self.pose = self._start_pose()
        self.motors: dict[int, MotorState] = {
            port: MotorState(port, self.config.device(port))
            for port in PORTS
            if self.config.is_motor(port)
        }
        self.pairs: dict[int, tuple[int, int]] = {}
        self.light_matrix: list[int] = [0] * 25
        self.matrix_orientation: int = K.ORIENTATION_UP
        #: Offset dello yaw, in decimi di grado (usato da motion_sensor.reset_yaw).
        self.yaw_offset_decidegrees: float = 0.0
        #: Faccia rispetto a cui è misurato lo yaw.
        self.yaw_face: int = K.FACE_TOP
        self.hub_lights: dict[int, int] = {K.LIGHT_POWER: 0, K.LIGHT_CONNECT: 0}
        #: Stato generico dei dispositivi (LED dei sensori, pixel delle matrici).
        self.device_state: dict[tuple[str, int], Any] = {}
        self.sounds: list[dict[str, Any]] = []
        self.events: list[Event] = []
        self.poses: list[tuple[int, float, float, float]] = []
        self.diagnostics: list[Diagnostic] = []
        self.pending: list[tuple[Any, str, int | None]] = []
        self.scheduler: "Scheduler | None" = None
        self.truncated = False
        self.stop_reason = ""
        self._last_sample_ms = -1e18
        self._motor_events: dict[int, tuple[float, int]] = {}
        self._sample(force=True)

    # -- sensori ------------------------------------------------------------

    def _start_pose(self) -> Pose:
        """La posa di partenza: quella del tappeto, se c'è un tappeto."""
        mat = self.config.mat
        if mat is None:
            return Pose()
        return Pose(mat.start_x, mat.start_y, mat.start_heading)

    def surface(self) -> Surface:
        """Superficie sotto il robot, con la luce ambientale già applicata.

        Senza tappeto restituisce i valori fissi dei sensori, così i
        programmi scritti prima dell'arrivo del tappeto continuano a
        funzionare.
        """
        mat = self.config.mat
        if mat is None:
            return Surface(self.config.sensors.color, self.config.sensors.reflection)
        return apply_light(mat.surface_at(self.pose.x, self.pose.y), self.config.ambient_light)

    # -- validazione degli argomenti ---------------------------------------

    def port_index(self, value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value not in PORTS:
            raise PortOutOfRangeError(
                f"porta non valida: {value!r}; usa port.A ... port.F (0-5)."
            )
        return value

    def motor(self, value: Any) -> MotorState:
        port = self.port_index(value)
        state = self.motors.get(port)
        if state is None:
            raise NotAMotorError(
                f"sulla porta {PORT_NAMES[port]} non c'è un motore "
                f"(collegato: {DEVICE_LABELS.get(self.config.device(port), '?').lower()})."
            )
        return state

    def require_device(self, value: Any, kinds: Iterable[str], what: str) -> int:
        port = self.port_index(value)
        if self.config.device(port) not in kinds:
            raise NoDeviceError(
                f"sulla porta {PORT_NAMES[port]} non c'è {what} "
                f"(collegato: {DEVICE_LABELS.get(self.config.device(port), '?').lower()})."
            )
        return port

    # -- registrazione ------------------------------------------------------

    def emit(self, type_: str, **data: Any) -> None:
        if len(self.events) >= MAX_EVENTS:
            if not self.truncated:
                self.truncated = True
                self.diagnostics.append(
                    Diagnostic(
                        "warning",
                        "SPIKE018",
                        f"la traccia è stata troncata a {MAX_EVENTS} eventi "
                        "(programma troppo lungo o ciclo infinito).",
                    )
                )
            return
        self.events.append(Event(t=int(self.t_ms), type=type_, data=data))

    def note(
        self,
        severity: str,
        code: str,
        message: str,
        line: int | None = None,
        column: int | None = None,
        detail: str = "",
    ) -> None:
        if len(self.diagnostics) >= MAX_DIAGNOSTICS:
            return
        self.diagnostics.append(
            Diagnostic(severity, code, message, line=line, column=column, detail=detail)
        )

    def motor_changed(self, state: MotorState) -> None:
        key = (round(state.velocity, 3), state.status)
        if self._motor_events.get(state.port) == key:
            return
        self._motor_events[state.port] = key
        self.emit("motor", port=state.port, velocity=state.velocity, status=state.status)

    def caller_line(self) -> int | None:
        """Riga del programma utente che ha chiamato la libreria."""
        frame = sys._getframe(1)
        while frame is not None:
            if frame.f_code.co_filename == self.program:
                return frame.f_lineno
            frame = frame.f_back
        return None

    def track(self, obj: Any, label: str) -> Any:
        """Registra un awaitable/coroutine per il controllo "mai atteso"."""
        if len(self.pending) < 10_000:
            self.pending.append((obj, label, self.caller_line()))
        return obj

    def awaitable(self, *, kind: str, label: str, **kwargs: Any) -> SpikeAwaitable:
        """Crea un'attesa già tracciata, con la riga del programma utente."""
        awaitable = SpikeAwaitable(kind=kind, label=label, line=self.caller_line(), **kwargs)
        self.track(awaitable, label)
        return awaitable

    def tracked(self, coro: Any, label: str) -> Any:
        """Traccia una coroutine di libreria creata per il programma utente."""
        return self.track(coro, label)

    def stop_all_motors(self) -> None:
        """Arresta ogni motore (fine del programma, come sull'hardware vero)."""
        for state in self.motors.values():
            if state.velocity != 0.0 or state.move is not None:
                self.cancel_move(state)
                state.finish(self)

    def cancel_move(self, state: MotorState, status: int = K.MOTOR_CANCELLED) -> None:
        """Annulla il movimento in corso e risolve la sua attesa."""
        move = state.move
        state.move = None
        if move is not None and move.awaitable is not None:
            awaitable = move.awaitable
            move.awaitable = None
            if not awaitable.resolved and self.scheduler is not None:
                self.scheduler.resolve(awaitable, status)

    def start_motor_move(
        self,
        state: MotorState,
        *,
        velocity: float,
        duration_ms: float,
        target_position: float | None = None,
        stop_behavior: int = K.MOTOR_BRAKE,
        label: str = "",
        awaitable: SpikeAwaitable | None = None,
    ) -> SpikeAwaitable:
        """Avvia un movimento a durata nota e restituisce l'attesa associata.

        Con ``target_position`` il motore si ferma esattamente alla posizione
        richiesta; senza, si ferma allo scadere di ``duration_ms``.
        """
        self.cancel_move(state)
        move = _Move()
        if target_position is not None:
            move.target_position = float(target_position)
        else:
            move.end_ms = self.t_ms + float(duration_ms)
        state.move = move
        state.velocity = float(velocity)
        state.stop_behavior = stop_behavior
        state.status = K.MOTOR_RUNNING if velocity else K.MOTOR_READY
        if awaitable is None:
            awaitable = self.awaitable(
                kind="motor",
                label=label or "movimento motore",
                ready_at=self.t_ms + math.ceil(duration_ms),
                result=K.MOTOR_READY,
            )
        move.awaitable = awaitable
        self.motor_changed(state)
        return awaitable

    # -- fisica -------------------------------------------------------------

    def drive_velocities(self) -> tuple[float, float]:
        """Velocità (sinistra, destra) dei motori che muovono il robot."""
        left_port = self.config.drive_left_port
        right_port = self.config.drive_right_port
        left = self.motors[left_port].velocity if left_port in self.motors else 0.0
        right = self.motors[right_port].velocity if right_port in self.motors else 0.0
        if self.config.is_reversed(left_port):
            left = -left
        if self.config.is_reversed(right_port):
            right = -right
        return left, right

    def advance_to(self, target_ms: float) -> None:
        """Porta il tempo simulato a ``target_ms`` integrando la fisica."""
        target = min(float(target_ms), float(self.config.max_sim_time_ms))
        while self.t_ms < target - 1e-9:
            dt = min(PHYSICS_STEP_MS, target - self.t_ms)
            left, right = self.drive_velocities()
            for state in self.motors.values():
                state.step(dt, self)
            self.pose = integrate(
                self.pose,
                motor_to_mm_s(left, self.config.wheel_diameter_mm),
                motor_to_mm_s(right, self.config.wheel_diameter_mm),
                dt,
                self.config.track_width_mm,
            )
            self.t_ms += dt
            self._sample()

    def _sample(self, force: bool = False) -> None:
        if not force and (self.t_ms - self._last_sample_ms) < self.config.sample_interval_ms:
            return
        self._last_sample_ms = self.t_ms
        self.poses.append((int(self.t_ms), self.pose.x, self.pose.y, self.pose.heading))

    # -- conclusione --------------------------------------------------------

    def finish(self, *, terminated: bool) -> Trace:
        self._sample(force=True)
        self._report_unawaited()
        return Trace(
            program=self.program,
            duration_ms=int(self.t_ms),
            terminated=terminated,
            poses=self.poses,
            events=self.events,
            diagnostics=self.diagnostics,
        )

    def _report_unawaited(self) -> None:
        unawaited: list[tuple[Any, str, int | None]] = []
        for obj, label, line in self.pending:
            if isinstance(obj, SpikeAwaitable):
                # Conta solo l'essere stato atteso: un comando mai awaited può
                # comunque risultare "risolto" perché la fine del programma
                # ferma i motori, e non deve per questo sparire dalla diagnosi.
                if not obj.awaited:
                    unawaited.append((obj, label, line))
            elif inspect.iscoroutine(obj):
                try:
                    if inspect.getcoroutinestate(obj) == inspect.CORO_CREATED:
                        unawaited.append((obj, label, line))
                except Exception:  # pragma: no cover - coroutine già chiusa
                    pass
        if not unawaited:
            return
        shown = unawaited[:MAX_UNAWAITED_REPORTED]
        for _obj, label, line in shown:
            self.note(
                "warning",
                "SPIKE020",
                f"«{label}» è stato chiamato ma non è mai stato atteso con await: "
                "non ha alcun effetto. Racchiudi il codice in una funzione async "
                "e avviala con runloop.run().",
                line=line,
            )
        if len(unawaited) > len(shown):
            self.note(
                "warning",
                "SPIKE020",
                f"e altre {len(unawaited) - len(shown)} chiamate mai attese.",
            )


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

_READY = "ready"
_WAITING = "waiting"
_DONE = "done"


class _Task:
    __slots__ = ("coro", "state", "value", "awaitable", "name")

    def __init__(self, coro, name: str = "") -> None:
        self.coro = coro
        self.state = _READY
        self.value: Any = None
        self.awaitable: SpikeAwaitable | None = None
        self.name = name


class Scheduler:
    """Esegue le coroutine cooperativamente su un orologio virtuale."""

    def __init__(self, hardware: Hardware) -> None:
        self.hw = hardware
        hardware.scheduler = self
        self._tasks: list[_Task] = []
        self._wake: list[tuple[float, int, SpikeAwaitable, _Task]] = []
        self._waiting: dict[int, _Task] = {}
        self._seq = itertools.count()
        self.steps = 0
        self._running = False

    # -- API ----------------------------------------------------------------

    def run(self, coroutines: Iterable[Any], *, names: Iterable[str] | None = None) -> None:
        if self._running:
            raise InvalidArgumentError(
                "runloop.run() non può essere chiamato mentre il programma è già "
                "in esecuzione: avvia tutte le attività con un'unica chiamata."
            )
        names = list(names or [])
        coroutines = list(coroutines)
        if not coroutines:
            return
        self._running = True
        try:
            for index, coro in enumerate(coroutines):
                name = names[index] if index < len(names) else f"attività {index + 1}"
                self._tasks.append(_Task(coro, name))
            self._loop()
        finally:
            self._running = False
            self._cleanup()

    def resolve(self, awaitable: SpikeAwaitable, value: Any = None) -> None:
        """Risolve subito un'attesa già in corso (usato dalle cancellazioni)."""
        awaitable.result = value
        task = self._waiting.get(id(awaitable))
        if task is None or task.state != _WAITING or task.awaitable is not awaitable:
            awaitable.resolved = True
            return
        heapq.heappush(self._wake, (self.hw.t_ms, next(self._seq), awaitable, task))

    # -- nucleo -------------------------------------------------------------

    def _loop(self) -> None:
        limit_ms = self.hw.config.max_sim_time_ms
        while True:
            ready = [task for task in self._tasks if task.state == _READY]
            if ready:
                for task in ready:
                    self._step(task)
                    self.steps += 1
                    if self.steps > self.hw.config.max_steps:
                        self.hw.stop_reason = "step_limit"
                        raise ProgramLimitError(
                            "il programma ha eseguito troppi passi senza avanzare "
                            "nel tempo simulato (possibile ciclo infinito)."
                        )
                continue

            if not any(task.state == _WAITING for task in self._tasks):
                break

            if not self._wake:
                self.hw.stop_reason = "blocked"
                self.hw.note(
                    "error",
                    "SPIKE021",
                    "tutte le attività sono in attesa di un'operazione che il "
                    "simulatore non sa pianificare.",
                )
                break

            next_wake = self._wake[0][0]
            if next_wake > limit_ms:
                self.hw.stop_reason = "time_limit"
                self.hw.note(
                    "warning",
                    "SPIKE016",
                    f"il programma è ancora in esecuzione dopo {limit_ms / 1000:.0f} "
                    "secondi simulati: simulazione interrotta.",
                )
                break
            self.hw.advance_to(next_wake)
            self._wake_due()

    def _step(self, task: _Task) -> None:
        try:
            yielded = task.coro.send(task.value)
        except StopIteration:
            task.state = _DONE
            task.value = None
            return
        except BaseException:
            task.state = _DONE
            task.value = None
            raise

        task.value = None

        if isinstance(yielded, SpikeAwaitable):
            self._schedule(task, yielded)
            return

        self.hw.note(
            "error",
            "SPIKE022",
            f"il programma attende qualcosa che non è un'operazione SPIKE "
            f"({type(yielded).__name__}): usa runloop.sleep_ms() al posto di "
            "asyncio o di altre librerie con await.",
            line=self.hw.caller_line(),
        )
        task.state = _DONE

    def _schedule(self, task: _Task, awaitable: SpikeAwaitable) -> None:
        if awaitable.predicate is not None and awaitable.predicate():
            awaitable.resolved = True
            task.state = _READY
            task.value = awaitable.result
            return
        when = awaitable.ready_at if awaitable.ready_at is not None else self.hw.t_ms
        task.state = _WAITING
        task.awaitable = awaitable
        self._waiting[id(awaitable)] = task
        heapq.heappush(self._wake, (float(when), next(self._seq), awaitable, task))

    def _wake_due(self) -> None:
        now = self.hw.t_ms
        while self._wake and self._wake[0][0] <= now + 1e-9:
            _when, _seq, awaitable, task = heapq.heappop(self._wake)
            if task.state != _WAITING or task.awaitable is not awaitable:
                continue
            if awaitable.predicate is not None and not awaitable.predicate():
                if awaitable.deadline is not None and now >= awaitable.deadline:
                    awaitable.resolved = True
                    self._finish_wait(task, awaitable, awaitable.result)
                else:
                    heapq.heappush(
                        self._wake,
                        (now + POLL_INTERVAL_MS, next(self._seq), awaitable, task),
                    )
                continue
            awaitable.resolved = True
            self._finish_wait(task, awaitable, awaitable.result)

    def _finish_wait(self, task: _Task, awaitable: SpikeAwaitable, value: Any) -> None:
        self._waiting.pop(id(awaitable), None)
        task.awaitable = None
        task.state = _READY
        task.value = value

    def _cleanup(self) -> None:
        for task in self._tasks:
            if task.state != _DONE:
                try:
                    task.coro.close()
                except Exception:  # pragma: no cover - coroutine già conclusa
                    pass
        self._tasks.clear()
        self._wake.clear()
        self._waiting.clear()


# ---------------------------------------------------------------------------
# Runtime attivo
# ---------------------------------------------------------------------------

_active: Hardware | None = None


def set_hardware(hardware: Hardware | None) -> None:
    """Rende ``hardware`` il hub corrente per i moduli della libreria."""
    global _active
    _active = hardware


def hardware() -> Hardware:
    """Il hub simulato attivo; errore chiaro se non c'è una simulazione."""
    if _active is None:
        raise RuntimeError(
            "nessun hub simulato attivo: esegui il programma con "
            "spikesim.runner oppure crea un Hardware nei test."
        )
    return _active
