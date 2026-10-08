"""Il tappeto a mattonelle: superfici, luce e generazione casuale."""

from __future__ import annotations

import pytest

from spikesim import mat as M
from spikesim.spike import color

SIZE = 100.0


# --- superfici --------------------------------------------------------------


def test_every_kind_has_a_colour_and_a_reflection():
    for kind in M.TILE_KINDS:
        assert kind in M.TILE_COLORS, kind
        assert kind in M.TILE_REFLECTION, kind
        assert 0 <= M.TILE_REFLECTION[kind] <= 100, kind


def test_turn_tiles_are_green_and_red():
    assert M.TILE_COLORS[M.TURN_LEFT] == color.GREEN
    assert M.TILE_COLORS[M.TURN_RIGHT] == color.RED


def test_the_line_tiles_are_dark_and_the_background_is_light():
    # La pista è scura (il "nastro") su un fondo chiaro: è ciò che rende
    # leggibile la riflessione.
    assert M.TILE_REFLECTION[M.STRAIGHT] < M.TILE_REFLECTION[M.EMPTY]
    assert M.TILE_REFLECTION[M.TURN_LEFT] < M.TILE_REFLECTION[M.EMPTY]


def test_tile_surface_is_the_kind_surface():
    surface = M.Tile(M.TURN_LEFT).surface()
    assert surface == M.Surface(color.GREEN, M.TILE_REFLECTION[M.TURN_LEFT])


# --- campionamento della superficie ----------------------------------------


def _two_tile_mat() -> M.Mat:
    return M.Mat(
        tile_size_mm=SIZE,
        tiles={
            (0, 0): M.Tile(M.START),
            (1, 0): M.Tile(M.TURN_LEFT),
        },
    )


def test_surface_at_returns_the_tile_the_point_is_standing_on():
    board = _two_tile_mat()
    assert board.tile_at(0.0, 0.0).kind == M.START
    assert board.tile_at(SIZE, 0.0).kind == M.TURN_LEFT
    # Un punto in un angolo della mattonella appartiene ancora alla mattonella.
    assert board.tile_at(SIZE - 1.0, 1.0).kind == M.TURN_LEFT
    assert board.surface_at(SIZE, 0.0).color == color.GREEN


def test_surface_outside_the_track_is_the_background():
    board = _two_tile_mat()
    assert board.tile_at(50.0 * SIZE, 0.0).kind == M.EMPTY
    assert board.surface_at(50.0 * SIZE, 0.0) == M.Tile(M.EMPTY).surface()


def test_bounds_cover_every_tile():
    board = _two_tile_mat()
    left, bottom, right, top = board.bounds()
    assert left <= -SIZE / 2 and right >= SIZE + SIZE / 2
    assert top - bottom >= SIZE


def test_negative_coordinates_are_handled():
    board = M.Mat(tile_size_mm=SIZE, tiles={(0, 0): M.Tile(M.START), (-1, -1): M.Tile(M.FINISH)})
    assert board.tile_at(-SIZE, -SIZE).kind == M.FINISH
    left, bottom, _right, _top = board.bounds()
    assert left < 0 and bottom < 0


# --- generazione ------------------------------------------------------------


def _walk(board: M.Mat) -> list[tuple[int, int]]:
    """Percorre la pista come farà il robot: legge la mattonella, poi avanza."""
    size = board.tile_size_mm
    heading = int(board.start_heading) % 360
    col = int(round(board.start_x / size))
    row = int(round(board.start_y / size))
    visited = [(col, row)]
    for _ in range(len(board.tiles) + 1):
        tile = board.tiles[(col, row)]
        if tile.kind == M.FINISH:
            return visited
        if tile.kind == M.TURN_LEFT:
            heading = (heading - 90) % 360
        elif tile.kind == M.TURN_RIGHT:
            heading = (heading + 90) % 360
        elif tile.kind not in (M.START, M.STRAIGHT):
            raise AssertionError(f"mattonella inattesa sul percorso: {tile.kind}")
        dc, dr = M.DIRECTIONS[heading]
        col, row = col + dc, row + dr
        if (col, row) not in board.tiles:
            raise AssertionError(f"il percorso si interrompe in {(col, row)}")
        visited.append((col, row))
    raise AssertionError("il percorso non arriva mai alla mattonella di arrivo")


@pytest.mark.parametrize("seed", [0, 1, 2, 7, 42, 1234])
def test_a_generated_track_is_connected(seed):
    board = M.generate_track(seed, straights=6, turns=4)
    path = _walk(board)
    assert len(path) == len(set(path)), "il percorso passa due volte sulla stessa mattonella"
    assert board.tiles[path[-1]].kind == M.FINISH
    assert board.tiles[path[0]].kind == M.START


@pytest.mark.parametrize("seed", [0, 1, 2, 7, 42, 1234])
def test_the_start_pose_sits_on_the_start_tile(seed):
    board = M.generate_track(seed, straights=6, turns=4)
    assert board.tile_at(board.start_x, board.start_y).kind == M.START


def test_generation_is_reproducible_with_the_same_seed():
    assert M.generate_track(11).to_dict() == M.generate_track(11).to_dict()


def test_different_seeds_give_different_tracks():
    shapes = {repr(M.generate_track(seed).to_dict()["tiles"]) for seed in range(12)}
    assert len(shapes) > 1


def test_a_track_can_have_no_turns():
    board = M.generate_track(3, straights=5, turns=0)
    kinds = {tile.kind for tile in board.tiles.values()}
    assert M.TURN_LEFT not in kinds and M.TURN_RIGHT not in kinds


def test_the_requested_turns_are_placed_when_there_is_room():
    for seed in range(6):
        board = M.generate_track(seed, straights=6, turns=4)
        turns = sum(
            1 for tile in board.tiles.values() if tile.kind in (M.TURN_LEFT, M.TURN_RIGHT)
        )
        assert turns == 4, f"seme {seed}: {turns} curve invece di 4"


def test_tile_size_is_configurable():
    board = M.generate_track(5, straights=3, turns=1, tile_size_mm=60.0)
    assert board.tile_size_mm == 60.0


# --- luce -------------------------------------------------------------------


def test_full_light_keeps_colour_and_reflection():
    surface = M.Surface(color.GREEN, 45)
    assert M.apply_light(surface, 100) == surface


def test_low_light_scales_the_reflection():
    assert M.apply_light(M.Surface(color.WHITE, 90), 50).reflection == 45
    assert M.apply_light(M.Surface(color.WHITE, 90), 0).reflection == 0


def test_below_the_threshold_colours_are_indistinguishable():
    dark = M.LIGHT_THRESHOLD - 1
    assert M.apply_light(M.Surface(color.GREEN, 45), dark).color == color.UNKNOWN
    assert M.apply_light(M.Surface(color.RED, 45), dark).color == color.UNKNOWN
    assert M.apply_light(M.Surface(color.GREEN, 45), M.LIGHT_THRESHOLD).color == color.GREEN


def test_light_is_clamped():
    assert M.apply_light(M.Surface(color.WHITE, 90), 500).reflection == 90
    assert M.apply_light(M.Surface(color.WHITE, 90), -10).reflection == 0


# --- serializzazione --------------------------------------------------------


def test_mat_round_trips_through_a_dict():
    board = M.generate_track(21, straights=4, turns=2)
    again = M.Mat.from_dict(board.to_dict())
    assert again.to_dict() == board.to_dict()
    assert again.tile_at(0.0, 0.0).kind == M.START
    assert again.start_heading == board.start_heading


def test_an_empty_mat_round_trips_too():
    assert M.Mat.from_dict(M.Mat().to_dict()).to_dict() == M.Mat().to_dict()
