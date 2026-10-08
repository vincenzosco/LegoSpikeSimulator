# Plan — Simulatore di codice LEGO SPIKE Prime (Python + PyQt5)

## Spec (authority)

User request:
> Crea un simulatore di codice LEGO SPIKE, consistente di un progetto Python, con Qt4/5, in cui
> si può drag and drop, o incollare il percorso del file Python, per vedere il movimento del
> robot, gli errori ed altre cose se nel codice non sono scritte correttamente. Per le librerie
> implementale da https://tuftsceeo.github.io/SPIKEPythonDocs/SPIKE3.html

Derived acceptance criteria:

1. A Python project (installable package + launcher script) that depends on PyQt5.
2. A GUI where the user can (a) drag & drop a `.py` file onto the window, **or** (b) paste/type
   a file path and load it. Both paths must end in the same "program loaded" state.
3. The simulator executes the loaded Python program against a re-implementation of the SPIKE 3
   API, and shows **the robot moving** on a 2D field.
4. It reports **errors and diagnostics** when the program is not written correctly: syntax
   errors, runtime exceptions with line numbers, and SPIKE-specific mistakes (unknown
   module/constant, wrong port, out-of-range velocity, un-awaited motor command, unpaired
   motor pair, non-terminating program).
5. The library surface follows the SPIKE 3 documentation (module/function/constant names and
   signatures) — not an invented API.

## Global Constraints

- Python 3.14, PyQt5 5.15 (already installed on the machine). No other runtime dependency.
- Tests: `pytest` (9.1.1) with `unittest` style is fine; run with `python3 -m pytest -q`.
- All simulator logic must be importable and testable **without a QApplication** (GUI imports
  are lazy/isolated in `spikesim.gui`).
- The unit of the robot model is the millimetre; angles in degrees; time in milliseconds.
- User programs are executed in a **subprocess** (`spikesim.runner`) so that a runaway program
  (e.g. `while True: pass`) can be killed, and so the MicroPython `time` shim cannot leak into
  the GUI process.
- The subprocess emits exactly one JSON document (the *Trace*) on stdout; human text/logs go to
  stderr. GUI reads stdout only.
- Italian UI strings, English identifiers/comments in code (matching the docs vocabulary).

## Interfaces (contracts between tasks)

- `spikesim/config.py` → `Config` (ports, wheel diameter, track width, velocity limits,
  sim limits). Consumed by T3, T4, T6, T8.
- `spikesim/kinematics.py` → `Pose`, `integrate(pose, left_mm_s, right_mm_s, dt_ms, cfg) -> Pose`,
  `motor_to_mm_s(velocity_deg_s, wheel_diameter_mm) -> float`, `steering_to_wheel_velocities(...)`.
  Consumed by T4, T8.
- `spikesim/trace.py` → `Trace`, `Event`, `Diagnostic`, `Severity`, `to_json/from_json`.
  Consumed by T4, T6, T7, T8.
- `spikesim/spike/` → the executable library (`motor`, `motor_pair`, `hub`, `color`, …), driven by
  `spikesim/runtime.py` (`Hardware`, `Scheduler`). Consumed by T6 only.
- `spikesim/checker.py` → `check_source(path) -> list[Diagnostic]`. Consumed by T7.
- `spikesim/runner.py` → `run_program(path, cfg) -> Trace` (in-process API used by tests) and
  `python -m spikesim.runner --file F` (subprocess entry). Consumed by T7, T8.
- GUI: `spikesim/gui/main_window.py::MainWindow` with `load_program(path)` and `run_program()`.

## Tasks

### T1 — Foundation: config, errors, kinematics
Steps:
1. Write `tests/test_kinematics.py` covering: straight drive distance, pivot in place,
   curve sign conventions, mm/deg conversion. Run → expected FAIL (module missing).
2. Implement `spikesim/config.py`, `spikesim/errors.py`, `spikesim/kinematics.py`.
3. Run `python3 -m pytest -q tests/test_kinematics.py` → expected: pass.
4. Commit.

### T2 — Trace model
Steps:
1. `tests/test_trace.py`: build a Trace with events + diagnostics, round-trip through JSON,
   assert equality and that unknown event types are rejected. → FAIL.
2. Implement `spikesim/trace.py`.
3. `pytest -q tests/test_trace.py` → pass. Commit.

### T3 — SPIKE 3 library surface
Steps:
1. `tests/test_spike_api.py`: import every documented module through the loader; assert all
   documented public names exist with the documented constant values (table copied from the
   Tufts SPIKE3 page); assert `from hub import port` / `import motor` resolve. → FAIL.
2. Implement `spikesim/spike/**` + `spikesim/runtime.py` (Hardware state, awaitable type).
3. `pytest -q tests/test_spike_api.py` → pass. Commit.

### T4 — Virtual clock, physics integration, runloop
Steps:
1. `tests/test_scheduler.py`: a program using `runloop.run` + `await motor.run_for_degrees`
   produces a straight-line pose sample set of the expected length; `sleep_ms` advances virtual
   time without real waiting; two parallel coroutines interleave; the step/time limits stop a
   runaway loop and emit a diagnostic. → FAIL.
2. Implement the scheduler in `spikesim/runtime.py` (`Scheduler`, physics stepping).
3. `pytest -q tests/test_scheduler.py` → pass. Commit.

### T5 — Static checker
Steps:
1. `tests/test_checker.py`: unknown module, unknown attribute (with "did you mean"), wrong
   constant, un-awaited async call, syntax error line/col, known-good file → clean. → FAIL.
2. Implement `spikesim/checker.py`.
3. `pytest -q tests/test_checker.py` → pass. Commit.

### T6 — Runner + end-to-end
Steps:
1. `tests/test_runner.py`: run 6 sample programs end-to-end and assert on the produced Trace
   (movement, prints, runtime error with line number, unpaired pair error, out-of-range
   warning, non-terminating stop). → FAIL.
2. Implement `spikesim/runner.py`.
3. `pytest -q tests/test_runner.py` → pass. Commit.

### T7 — GUI shell
Steps:
1. Implement `spikesim/gui/app.py`, `main_window.py`, `code_panel.py`, `problems_panel.py`,
   `port_config_panel.py`; `run_simulator.py`.
2. Smoke test: `QT_QPA_PLATFORM=offscreen python3 -c "..."` constructing the window, loading a
   file via `load_program()` and via a simulated drop event, and running a program. Expected:
   no exception, diagnostics populated. Commit.

### T8 — Simulation view
Steps:
1. Implement `spikesim/gui/robot_view.py` (field + robot + trail), `hub_view.py` (5×5 light
   matrix), `timeline.py` (play/pause/seek/speed).
2. Offscreen smoke test that renders the trace headlessly (`grab()` a QPixmap) at t=0 and
   t=end. Expected: non-null pixmaps, pose corresponds to the trace. Commit.

### T9 — Examples, README, launcher
Steps:
1. Add `examples/*.py` (correct programs + deliberately broken ones).
2. Write `README.md` (install, run, features, documented simplifications).
3. Full `pytest -q` → all green. Commit.

## Review Focus

Inputs the tests above do not exercise, to be checked deliberately at review:
- A program that never calls `runloop.run` but uses `time.sleep_ms` at top level.
- A program whose `main()` is not `async` but is passed to `runloop.run`.
- Sensor reads on a port configured as "empty".
- Very long programs near the simulated-time limit (trace size / GUI responsiveness).
- Drag & drop of a non-`.py` file, of a directory, and of a file with a syntax error.
