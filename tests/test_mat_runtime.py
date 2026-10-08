"""Il tappeto e la luce arrivano fino ai sensori del programma utente."""

from __future__ import annotations

import math
from dataclasses import replace

import pytest

from spikesim import mat as M
from spikesim.config import COLOR_SENSOR, PORT_C, Config, default_config
from spikesim.spike import color

TILE = 100.0
#: Gradi di ruota per avanzare di una mattonella (ruota da 56 mm).
TILE_IN_DEGREES = 205


def _board(start_x: float = 0.0, start_y: float = 0.0, start_heading: float = 0.0) -> M.Mat:
    return M.Mat(
        tile_size_mm=TILE,
        tiles={
            (0, 0): M.Tile(M.START),
            (1, 0): M.Tile(M.TURN_LEFT),
            (2, 0): M.Tile(M.FINISH),
        },
        start_x=start_x,
        start_y=start_y,
        start_heading=start_heading,
    )


def _config(mat: M.Mat | None, ambient: int = 100, **sensors) -> Config:
    config = default_config().with_port(PORT_C, COLOR_SENSOR)
    config = replace(config, mat=mat, ambient_light=ambient)
    return config.with_sensors(**sensors) if sensors else config


def _prints(trace) -> list[str]:
    return [event.data.get("text", "") for event in trace.events if event.type == "print"]


READ_SOURCE = """
import color_sensor
import runloop
from hub import port

async def main():
    print("colore", color_sensor.color(port.C))
    print("riflessione", color_sensor.reflection(port.C))

runloop.run(main())
"""

MOVE_SOURCE = """
import color_sensor
import motor_pair
import runloop
from hub import port

async def main():
    motor_pair.pair(motor_pair.PAIR_1, port.A, port.B)
    print("prima", color_sensor.color(port.C))
    await motor_pair.move_for_degrees(motor_pair.PAIR_1, 205, 0, velocity=360)
    print("dopo", color_sensor.color(port.C))

runloop.run(main())
"""


# --- configurazione ---------------------------------------------------------


def test_config_round_trips_the_mat_and_the_light():
    board = M.generate_track(4, straights=4, turns=2)
    config = _config(board, ambient=40)
    again = Config.from_dict(config.to_dict())
    assert again.ambient_light == 40
    assert again.mat is not None
    assert again.mat.to_dict() == board.to_dict()
    assert again.to_dict() == config.to_dict()


def test_config_without_a_mat_still_round_trips():
    config = _config(None)
    again = Config.from_dict(config.to_dict())
    assert again.mat is None
    assert again.to_dict() == config.to_dict()


# --- lettura della mattonella ----------------------------------------------


def test_the_sensor_reads_the_tile_the_robot_stands_on(run_source):
    result = run_source(READ_SOURCE, _config(_board()))
    assert result.trace.count("error") == 0
    assert _prints(result.trace) == [
        f"colore {color.BLUE}",
        f"riflessione {M.TILE_REFLECTION[M.START]}",
    ]


def test_moving_onto_the_next_tile_changes_the_reading(run_source):
    result = run_source(MOVE_SOURCE, _config(_board()))
    assert result.trace.count("error") == 0
    assert _prints(result.trace) == [f"prima {color.BLUE}", f"dopo {color.GREEN}"]


def test_the_robot_starts_where_the_mat_says(run_source):
    board = _board(start_x=150.0, start_y=-50.0, start_heading=90.0)
    result = run_source(READ_SOURCE, _config(board))
    t, x, y, heading = result.trace.poses[0]
    assert (x, y, heading) == (150.0, -50.0, 90.0)


def test_outside_the_track_the_robot_reads_the_background(run_source):
    board = _board(start_x=1000.0)  # molto fuori dalla pista
    result = run_source(READ_SOURCE, _config(board))
    assert _prints(result.trace)[0] == f"colore {color.WHITE}"


# --- luce -------------------------------------------------------------------


def test_low_light_halves_the_reflection_and_blanks_the_colour(run_source):
    bright = run_source(READ_SOURCE, _config(_board(), ambient=100)).trace
    dim = run_source(READ_SOURCE, _config(_board(), ambient=50)).trace
    dark = run_source(READ_SOURCE, _config(_board(), ambient=10)).trace

    assert _prints(bright)[1] == f"riflessione {M.TILE_REFLECTION[M.START]}"
    assert _prints(dim)[1] == f"riflessione {round(M.TILE_REFLECTION[M.START] * 0.5)}"
    assert _prints(dark)[0] == f"colore {color.UNKNOWN}"


def test_a_green_tile_stops_looking_green_in_the_dark(run_source):
    bright = run_source(MOVE_SOURCE, _config(_board(), ambient=100)).trace
    dark = run_source(MOVE_SOURCE, _config(_board(), ambient=5)).trace
    assert _prints(bright)[1] == f"dopo {color.GREEN}"
    assert _prints(dark)[1] == f"dopo {color.UNKNOWN}"


# --- retrocompatibilità -----------------------------------------------------


def test_without_a_mat_the_fixed_sensor_values_still_come_back(run_source):
    config = _config(None, color=color.RED, reflection=73)
    result = run_source(READ_SOURCE, config)
    assert _prints(result.trace) == ["colore 9", "riflessione 73"]


def test_default_config_has_no_mat_and_full_light():
    config = default_config()
    assert config.mat is None
    assert config.ambient_light == 100


def test_a_tile_size_becomes_millimetres_of_travel(run_source):
    """Una mattonella da 100 mm si percorre con ~205 gradi di ruota."""
    expected = TILE / (math.pi * 56.0) * 360.0
    assert abs(expected - TILE_IN_DEGREES) < 1.5
    result = run_source(MOVE_SOURCE, _config(_board()))
    x = result.trace.poses[-1][1]
    assert 50.0 <= x <= 150.0, "il robot deve fermarsi dentro la mattonella successiva"
