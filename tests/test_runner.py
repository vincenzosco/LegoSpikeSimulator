"""Il processo separato che esegue il programma utente.

La GUI usa ``run_program`` (processo figlio) e non ``run_in_process``:
serve che un programma che non termina non si porti dietro l'interfaccia.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from spikesim.config import default_config
from spikesim.runner import REPO_ROOT, run_program

PROGRAM = """
import motor, time
from hub import port

motor.run(port.A, 360)
time.sleep_ms(500)
motor.stop(port.A)
"""


def _write(tmp_path, source: str, name: str = "programma.py"):
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def test_subprocess_produces_the_same_kind_of_trace(tmp_path):
    path = _write(tmp_path, PROGRAM)
    result = run_program(str(path), default_config(), timeout_s=60)
    trace = result.trace
    assert trace.ok, trace.diagnostics
    assert trace.terminated
    assert trace.program.endswith("programma.py")
    assert trace.duration_ms == 500
    # Ruota sinistra a 360 °/s (175.93 mm/s) e destra ferma per mezzo secondo:
    # omega = -175.93/112 = -pi/2 rad/s, quindi -45 gradi in 500 ms.
    assert trace.poses[-1][3] == pytest.approx(-45.0, abs=0.01)
    assert any(event.type == "motor" for event in trace.events)


def test_subprocess_reports_a_runtime_error_with_the_line(tmp_path):
    path = _write(
        tmp_path,
        "import runloop\n"
        "\n"
        "async def main():\n"
        "    raise ValueError('rotto')\n"
        "\n"
        "runloop.run(main())\n",
    )
    result = run_program(str(path), timeout_s=60)
    trace = result.trace
    assert not trace.ok
    assert not trace.terminated
    error = [d for d in trace.diagnostics if d.severity == "error"][0]
    assert error.line == 4
    assert "rotto" in error.message
    assert "ValueError" in error.detail


def test_runaway_program_is_killed_and_reported(tmp_path):
    path = _write(tmp_path, "while True:\n    pass\n")
    result = run_program(str(path), timeout_s=1.5)
    trace = result.trace
    assert not trace.terminated
    assert [d.code for d in trace.diagnostics] == ["TIMEOUT"]
    assert trace.poses == []


def test_stdout_is_pure_json_so_the_gui_can_parse_it(tmp_path):
    path = _write(tmp_path, "print('ciao')\nprint('mondo')\n")
    command = [
        sys.executable,
        "-m",
        "spikesim.runner",
        "--file",
        str(path),
    ]
    completed = subprocess.run(
        command, capture_output=True, text=True, cwd=REPO_ROOT, timeout=60
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    messages = [
        event["data"]["text"]
        for event in payload["events"]
        if event["type"] == "print"
    ]
    assert messages == ["ciao", "mondo"]


def test_cli_can_write_the_trace_to_a_file(tmp_path):
    path = _write(tmp_path, PROGRAM)
    output = tmp_path / "traccia.json"
    command = [
        sys.executable,
        "-m",
        "spikesim.runner",
        "--file",
        str(path),
        "--out",
        str(output),
    ]
    completed = subprocess.run(
        command, capture_output=True, text=True, cwd=REPO_ROOT, timeout=60
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["duration_ms"] == 500


def test_config_is_passed_to_the_child_process(tmp_path):
    path = _write(
        tmp_path,
        "import color_sensor\n"
        "from hub import port\n"
        "print(color_sensor.reflection(port.C))\n",
    )
    config = default_config().with_port(2, "color_sensor").with_sensors(reflection=77)
    result = run_program(str(path), config, timeout_s=60)
    assert result.trace.ok, result.trace.diagnostics
    text = [e.data["text"] for e in result.trace.events if e.type == "print"]
    assert text == ["77"]
