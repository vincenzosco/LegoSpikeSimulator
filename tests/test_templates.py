"""I template pronti all'uso e il segui-linea che li percorre davvero."""

from __future__ import annotations

import os

import pytest

from spikesim import mat as M
from spikesim import templates
from spikesim.runner import run_in_process

SEEDS = (0, 1, 2, 3, 4, 5)
KEYS = tuple(template.key for template in templates.all_templates())


def _turns(board: M.Mat) -> tuple[int, int]:
    left = sum(1 for tile in board.tiles.values() if tile.kind == M.TURN_LEFT)
    right = sum(1 for tile in board.tiles.values() if tile.kind == M.TURN_RIGHT)
    return left, right


def _expected_heading(board: M.Mat) -> int:
    heading = int(board.start_heading) % 360
    for cell in board.path_tiles():
        kind = board.tiles[cell].kind
        if kind == M.TURN_LEFT:
            heading = (heading + 90) % 360
        elif kind == M.TURN_RIGHT:
            heading = (heading - 90) % 360
    return heading


def _prints(trace) -> list[str]:
    return [event.data.get("text", "") for event in trace.events if event.type == "print"]


# --- catalogo ---------------------------------------------------------------


def test_the_catalogue_offers_several_templates_with_real_programs():
    catalog = templates.all_templates()
    assert len(catalog) >= 3, "servono alcune template fra cui scegliere"
    keys = [template.key for template in catalog]
    assert "seguilinea" in keys
    for template in catalog:
        assert os.path.isfile(template.program_path), template.program_path
        assert template.ports, template.key
        assert template.name and template.description


def test_build_config_installs_the_ports_the_program_needs():
    template = templates.get("seguilinea")
    config, board = templates.build_config(template, seed=0)
    assert config.mat is not None
    assert config.ambient_light == 100
    for port, device in template.ports.items():
        assert config.device(port) == device
    assert board.tile_at(board.start_x, board.start_y).kind == M.START


def test_build_config_keeps_the_light_it_is_given():
    config, _board = templates.build_config(templates.get("seguilinea"), seed=0, ambient=33)
    assert config.ambient_light == 33


def test_the_same_seed_rebuilds_the_same_track():
    _config, first = templates.build_config(templates.get("seguilinea"), seed=9)
    _config, second = templates.build_config(templates.get("seguilinea"), seed=9)
    assert first.to_dict() == second.to_dict()


# --- il segui-linea percorre la pista --------------------------------------


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("seed", SEEDS)
def test_every_template_reaches_the_finish_tile(key, seed):
    template = templates.get(key)
    config, board = templates.build_config(template, seed)
    trace = run_in_process(template.program_path, config).trace

    assert trace.count("error") == 0, [d.message for d in trace.diagnostics]
    assert trace.terminated, "il programma deve finire da solo"

    path = board.path_tiles()
    finish = path[-1]
    assert board.tiles[finish].kind == M.FINISH

    x, y, heading = trace.poses[-1][1:]
    size = board.tile_size_mm
    assert board.cell_at(x, y) == finish, (
        f"il robot è finito in {board.cell_at(x, y)}, la pista finisce in {finish}"
    )
    assert abs(x - finish[0] * size) <= 3.0, f"x={x} fuori dal centro della mattonella"
    assert abs(y - finish[1] * size) <= 3.0, f"y={y} fuori dal centro della mattonella"

    expected = _expected_heading(board)
    delta = (heading - expected + 180) % 360 - 180
    assert abs(delta) < 0.6, f"verso finale {heading:g}°, atteso {expected}°"


@pytest.mark.parametrize("seed", SEEDS)
def test_the_robot_turns_once_per_turn_tile(seed):
    template = templates.get("seguilinea")
    config, board = templates.build_config(template, seed)
    trace = run_in_process(template.program_path, config).trace

    left, right = _turns(board)
    assert left + right >= 1, "la pista deve avere almeno una curva"
    texts = _prints(trace)
    assert texts.count("curva a sinistra") == left
    assert texts.count("curva a destra") == right


def test_the_robot_stops_on_the_finish_tile_even_on_a_track_full_of_turns():
    template = templates.get("seguilinea")
    config, board = templates.build_config(template, seed=1)
    assert _turns(board)[0] + _turns(board)[1] >= 2
    trace = run_in_process(template.program_path, config).trace
    assert "arrivato!" in _prints(trace)


# --- la luce cambia il comportamento ---------------------------------------


def test_in_the_dark_the_line_follower_refuses_to_move():
    template = templates.get("seguilinea")
    config, board = templates.build_config(template, seed=2, ambient=5)
    trace = run_in_process(template.program_path, config).trace

    assert trace.count("error") == 0
    assert trace.poses[-1][1:] == trace.poses[0][1:], "al buio il robot non si muove"
    assert board.tiles[board.cell_at(trace.poses[0][1], trace.poses[0][2])].kind == M.START
    assert any("non vedo" in text for text in _prints(trace))
    assert "arrivato!" not in _prints(trace)


def test_with_enough_light_the_very_same_run_moves():
    template = templates.get("seguilinea")
    config, _board = templates.build_config(template, seed=2, ambient=100)
    trace = run_in_process(template.program_path, config).trace
    assert trace.poses[-1][1] != trace.poses[0][1] or trace.poses[-1][2] != trace.poses[0][2]
    assert "arrivato!" in _prints(trace)
