"""Modello della traccia: eventi, diagnostica, serializzazione JSON."""

from __future__ import annotations

import json

import pytest

from spikesim.trace import (
    Diagnostic,
    Event,
    Trace,
    diagnostics_from_exception,
    from_json,
    to_json,
)


def _sample_trace() -> Trace:
    return Trace(
        program="/tmp/programma.py",
        duration_ms=1500,
        terminated=True,
        poses=[(0, 0.0, 0.0, 0.0), (500, 87.9, 0.0, 0.0), (1500, 263.8, 0.0, 0.0)],
        events=[
            Event(t=0, type="print", data={"text": "ciao"}),
            Event(t=0, type="motor", data={"port": 0, "velocity": 720.0}),
            Event(t=500, type="light_matrix", data={"pixels": [0] * 25}),
        ],
        diagnostics=[
            Diagnostic("warning", "SPIKE014", "velocità fuori intervallo", line=3),
            Diagnostic("error", "SPIKE013", "pair non creata", line=7, column=8),
        ],
    )


def test_json_round_trip_preserves_everything():
    trace = _sample_trace()
    assert from_json(to_json(trace)) == trace


def test_to_json_is_valid_json_and_utf8_safe():
    payload = json.loads(to_json(_sample_trace()))
    assert payload["program"] == "/tmp/programma.py"
    assert payload["poses"][1] == [500, 87.9, 0.0, 0.0]


def test_unknown_event_type_is_rejected_on_load():
    payload = json.loads(to_json(_sample_trace()))
    payload["events"].append({"t": 1, "type": "teleport", "data": {}})
    with pytest.raises(ValueError, match="teleport"):
        from_json(json.dumps(payload))


def test_empty_trace_round_trips():
    trace = Trace(program="x.py", duration_ms=0, terminated=False, poses=[], events=[], diagnostics=[])
    assert from_json(to_json(trace)) == trace


def test_counts_by_severity():
    trace = _sample_trace()
    assert trace.count("error") == 1
    assert trace.count("warning") == 1
    assert trace.count("info") == 0


def test_pose_lookup_interpolates_between_samples():
    trace = _sample_trace()
    assert trace.pose_at(-10) == (0.0, 0.0, 0.0)
    assert trace.pose_at(250) == pytest.approx((87.9 / 2, 0.0, 0.0))
    assert trace.pose_at(999999) == (263.8, 0.0, 0.0)


def test_diagnostic_from_exception_points_at_user_line(tmp_path):
    program = tmp_path / "rotto.py"
    program.write_text(
        "def livello1():\n"
        "    return 1 / 0\n"
        "\n"
        "livello1()\n",
        encoding="utf-8",
    )
    with pytest.raises(ZeroDivisionError) as info:
        exec(compile(program.read_text(), str(program), "exec"), {"__name__": "__main__"})

    diagnostics = diagnostics_from_exception(info.value, str(program))
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.severity == "error"
    assert diagnostic.line == 2, "la riga dell'utente che ha causato l'errore"
    assert "division by zero" in diagnostic.message
