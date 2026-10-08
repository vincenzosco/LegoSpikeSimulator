"""Fumo sulla GUI: caricamento, drag & drop, simulazione, disegno.

Girano in modalità ``offscreen`` (vedi ``tests/conftest.py``): non serve uno
schermo, ma la finestra viene davvero costruita, il programma davvero
eseguito e la vista davvero disegnata.
"""

from __future__ import annotations

import time

import pytest
from PyQt5.QtCore import QMimeData, QPoint, Qt, QUrl
from PyQt5.QtGui import QDragLeaveEvent, QDropEvent

from spikesim import templates
from spikesim.config import COLOR_SENSOR, DISTANCE_SENSOR, PORT_C, PORT_D

PROGRAM = """
import motor_pair, runloop
from hub import port

async def main():
    motor_pair.pair(motor_pair.PAIR_1, port.A, port.B)
    await motor_pair.move_for_degrees(motor_pair.PAIR_1, 720, 0, velocity=360)

runloop.run(main())
"""


@pytest.fixture
def window(qapp):
    from spikesim.gui.main_window import MainWindow

    main_window = MainWindow()
    yield main_window
    main_window.close()
    main_window.deleteLater()
    qapp.processEvents()


def _wait_for_simulation(window, qapp, timeout_s: float = 60.0) -> None:
    deadline = time.time() + timeout_s
    while window._thread is not None and window._thread.isRunning():  # noqa: SLF001
        qapp.processEvents()
        time.sleep(0.01)
        if time.time() > deadline:
            raise AssertionError("la simulazione non è terminata")
    # Le connessioni sono queued: servono un paio di giri di event loop.
    for _ in range(50):
        qapp.processEvents()
        time.sleep(0.002)


def _write(tmp_path, source: str, name: str = "programma.py"):
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def test_window_starts_on_the_first_template_with_nothing_simulated(window):
    """Aprendo il simulatore c'è già un percorso pronto da provare."""
    first = templates.all_templates()[0]
    assert window.code_panel.path == first.program_path
    assert window.mat_panel.template().key == first.key
    assert window.robot_view._trace is None  # noqa: SLF001
    assert not window.timeline.play_button.isEnabled()


def test_the_template_program_passes_the_checker(window):
    assert window.problems_panel.tree.topLevelItemCount() == 0


def test_path_field_loads_the_program(window, tmp_path):
    path = _write(tmp_path, PROGRAM)
    window.path_edit.setText(str(path))
    window._load_from_field()  # noqa: SLF001
    assert window.code_panel.path == str(path)
    assert "motor_pair" in window.code_panel.editor.toPlainText()
    assert window.problems_panel.tree.topLevelItemCount() == 0


def test_load_reports_missing_file(window, tmp_path):
    from PyQt5.QtWidgets import QMessageBox

    shown: list[tuple[str, str]] = []
    original = QMessageBox.warning
    QMessageBox.warning = staticmethod(  # type: ignore[assignment]
        lambda _parent, title, message, *args, **kwargs: shown.append((title, message))
    )
    try:
        assert window.load_program(str(tmp_path / "manca.py")) is False
    finally:
        QMessageBox.warning = original  # type: ignore[assignment]
    assert shown and shown[0][0] == "File non trovato"


def test_load_rejects_a_non_python_file(window, tmp_path):
    from PyQt5.QtWidgets import QMessageBox

    other = tmp_path / "note.txt"
    other.write_text("ciao", encoding="utf-8")
    before = window.code_panel.path
    original = QMessageBox.warning
    QMessageBox.warning = staticmethod(  # type: ignore[assignment]
        lambda _parent, title, message, *args, **kwargs: None
    )
    try:
        assert window.load_program(str(other)) is False
    finally:
        QMessageBox.warning = original  # type: ignore[assignment]
    assert window.code_panel.path == before


def test_syntax_error_file_loads_and_shows_the_problem(window, tmp_path):
    path = _write(tmp_path, "import motor\n\ndef rotto(:\n    pass\n")
    assert window.load_program(str(path)) is True
    tree = window.problems_panel.tree
    assert tree.topLevelItemCount() == 1
    assert tree.topLevelItem(0).text(1) == "SYN001"
    assert tree.topLevelItem(0).text(2) == "3"


def test_problem_activation_jumps_to_the_line(window, tmp_path):
    path = _write(tmp_path, "import motor\n\ndef rotto(:\n    pass\n")
    window.load_program(str(path))
    window.problems_panel.problemActivated.emit(3)
    assert window.code_panel.editor.textCursor().blockNumber() == 2


def test_drag_and_drop_loads_a_python_file(window, tmp_path):
    path = _write(tmp_path, PROGRAM)
    event = _drop_event([str(path)])
    window.dropEvent(event)
    assert window.code_panel.path == str(path)
    assert event.isAccepted()


def test_drag_and_drop_ignores_non_python_files(window, tmp_path):
    before = window.code_panel.path
    other = tmp_path / "immagine.png"
    other.write_bytes(b"\x89PNG")
    event = _drop_event([str(other)])
    window.dropEvent(event)
    assert window.code_panel.path == before


def test_drag_and_drop_ignores_a_directory(window, tmp_path):
    before = window.code_panel.path
    event = _drop_event([str(tmp_path)])
    window.dropEvent(event)
    assert window.code_panel.path == before


def test_drag_over_the_window_highlights_the_panel(window, tmp_path):
    path = _write(tmp_path, PROGRAM)
    event = _drop_event([str(path)])
    window.dragEnterEvent(event)
    assert window.code_panel.editor.property("active") == "true"
    window.dragLeaveEvent(QDragLeaveEvent())
    assert window.code_panel.editor.property("active") == "false"


def test_full_simulation_shows_a_moving_robot(window, qapp, tmp_path):
    path = _write(tmp_path, PROGRAM)
    window.load_program(str(path))
    window.simulate()
    _wait_for_simulation(window, qapp)

    trace = window._trace  # noqa: SLF001
    assert trace is not None, "la simulazione non ha prodotto una traccia"
    assert trace.ok, trace.diagnostics
    # 720 gradi di ruota = 2 giri di ruota da 56 mm.
    assert trace.poses[-1][1] == pytest.approx(2 * 3.141592653589793 * 56.0, rel=1e-6)
    assert window.timeline.play_button.isEnabled()

    # La vista disegna davvero, e cambia fra inizio e fine.
    window.timeline.pause()
    window.timeline.set_time(0.0)
    qapp.processEvents()
    start = window.robot_view.grab()
    window.timeline.set_time(trace.duration_ms)
    qapp.processEvents()
    end = window.robot_view.grab()
    assert not start.isNull() and start.width() > 0
    assert not end.isNull()
    assert start.toImage() != end.toImage(), "il disegno del robot non è cambiato"


def test_mat_panel_offers_the_templates_and_starts_on_the_line_follower(window):
    panel = window.mat_panel
    keys = [panel.template_combo.itemData(i) for i in range(panel.template_combo.count())]
    assert keys == [template.key for template in templates.all_templates()]
    assert "seguilinea" in keys
    assert panel.template().key == templates.all_templates()[0].key
    assert panel.mat().tiles, "il pannello deve avere subito una pista"
    assert panel.mat().tile_at(panel.mat().start_x, panel.mat().start_y).kind == "start"
    assert panel.ambient_light() == 100


def test_choosing_a_template_loads_its_program_and_its_ports(window, qapp):
    chosen = templates.get("seguilinea_lungo")
    assert window.mat_panel.set_template_by_key("seguilinea_lungo") is True
    qapp.processEvents()

    assert window.code_panel.path == chosen.program_path
    config = window.port_panel.config()
    for port, device in chosen.ports.items():
        assert config.device(port) == device


def test_rerolling_gives_a_different_track(window, qapp):
    before = window.mat_panel.mat().to_dict()
    for _ in range(30):
        window.mat_panel.reroll()
        if window.mat_panel.mat().to_dict() != before:
            break
    assert window.mat_panel.mat().to_dict() != before, "il sorteggio non ha cambiato la pista"


def test_the_same_seed_gives_the_same_track(window, qapp):
    window.mat_panel.seed_spin.setValue(12345)
    first = window.mat_panel.mat().to_dict()
    window.mat_panel.seed_spin.setValue(999)
    window.mat_panel.seed_spin.setValue(12345)
    assert window.mat_panel.mat().to_dict() == first


def test_the_light_slider_reaches_the_configuration(window, qapp):
    window.mat_panel.light_slider.setValue(30)
    qapp.processEvents()
    assert window.mat_panel.ambient_light() == 30
    config = window._current_config()  # noqa: SLF001
    assert config.ambient_light == 30
    assert config.mat is not None
    assert config.mat.to_dict() == window.mat_panel.mat().to_dict()


def test_the_robot_view_zooms_out_to_show_the_whole_track(window, qapp):
    board = window.mat_panel.mat()
    window.robot_view.set_mat(board)
    window.robot_view.set_trace(None)
    qapp.processEvents()
    left, bottom, right, top = window.robot_view._bounds  # noqa: SLF001
    board_left, board_bottom, board_right, board_top = board.bounds()
    assert left <= board_left and bottom <= board_bottom
    assert right >= board_right and top >= board_top


def test_the_window_draws_the_mat_without_a_trace(window, qapp):
    window.robot_view.set_trace(None)
    qapp.processEvents()
    assert window.robot_view._mat is not None  # noqa: SLF001
    pixmap = window.robot_view.grab()
    assert not pixmap.isNull() and pixmap.width() > 0


def test_the_mat_is_drawn_differently_from_an_empty_field(window, qapp):
    from spikesim.mat import Mat

    window.robot_view.set_mat(window.mat_panel.mat())
    qapp.processEvents()
    with_mat = window.robot_view.grab().toImage()
    window.robot_view.set_mat(Mat())
    qapp.processEvents()
    empty = window.robot_view.grab().toImage()
    assert with_mat != empty, "il tappeto non viene disegnato"


def test_simulating_a_template_from_the_gui_reaches_the_finish(window, qapp):
    window.mat_panel.set_template_by_key("seguilinea_facile")
    qapp.processEvents()
    window.simulate()
    _wait_for_simulation(window, qapp)

    trace = window._trace  # noqa: SLF001
    assert trace is not None and trace.ok, trace.diagnostics
    board = window.mat_panel.mat()
    finish = board.path_tiles()[-1]
    x, y = trace.poses[-1][1], trace.poses[-1][2]
    assert board.cell_at(x, y) == finish


def test_simulating_in_the_dark_stops_the_robot(window, qapp):
    window.mat_panel.set_template_by_key("seguilinea_facile")
    window.mat_panel.light_slider.setValue(5)
    qapp.processEvents()
    window.simulate()
    _wait_for_simulation(window, qapp)

    trace = window._trace  # noqa: SLF001
    assert trace.ok, trace.diagnostics
    assert trace.poses[-1][1:] == trace.poses[0][1:], "al buio il robot non deve muoversi"


def test_playback_keeps_running_by_itself(window, qapp):
    """Avviata la riproduzione, l'animazione deve procedere da sola."""
    window.timeline.set_duration(10000)
    window.timeline.play()
    assert window.timeline.is_playing()

    deadline = time.time() + 0.4
    while time.time() < deadline:
        qapp.processEvents()
        time.sleep(0.005)

    assert window.timeline.is_playing(), "la riproduzione si è fermata da sola"
    assert window.timeline.time_ms > 100.0, "il tempo non è avanzato"


def test_seeking_backwards_rebuilds_the_console(window, qapp, tmp_path):
    path = _write(
        tmp_path,
        "import runloop\n"
        "\n"
        "async def main():\n"
        "    print('primo')\n"
        "    await runloop.sleep_ms(500)\n"
        "    print('secondo')\n"
        "\n"
        "runloop.run(main())\n",
    )
    window.load_program(str(path))
    window.simulate()
    _wait_for_simulation(window, qapp)

    window.timeline.set_time(window._trace.duration_ms)  # noqa: SLF001
    qapp.processEvents()
    assert "secondo" in window.console_panel.view.toPlainText()

    window.timeline.set_time(0.0)
    qapp.processEvents()
    text = window.console_panel.view.toPlainText()
    assert "primo" in text
    assert "secondo" not in text, "riavvolgendo, i messaggi futuri devono sparire"

    # E riavanzando devono ricomparire, una volta sola.
    window.timeline.set_time(window._trace.duration_ms)  # noqa: SLF001
    qapp.processEvents()
    text = window.console_panel.view.toPlainText()
    assert text.count("primo") == 1
    assert "secondo" in text


def test_matrix_view_follows_the_events(window, qapp, tmp_path):
    path = _write(
        tmp_path,
        "from hub import light_matrix\n"
        "import runloop\n"
        "\n"
        "async def main():\n"
        "    light_matrix.show_image(light_matrix.IMAGE_HEART)\n"
        "    await runloop.sleep_ms(500)\n"
        "\n"
        "runloop.run(main())\n",
    )
    window.load_program(str(path))
    window.simulate()
    _wait_for_simulation(window, qapp)
    window.timeline.set_time(window._trace.duration_ms)  # noqa: SLF001
    qapp.processEvents()
    assert sum(window.hub_view._pixels) > 0  # noqa: SLF001


def test_console_shows_prints_as_time_advances(window, qapp, tmp_path):
    path = _write(
        tmp_path,
        "import runloop\n"
        "\n"
        "async def main():\n"
        "    print('primo')\n"
        "    await runloop.sleep_ms(500)\n"
        "    print('secondo')\n"
        "\n"
        "runloop.run(main())\n",
    )
    window.load_program(str(path))
    window.simulate()
    _wait_for_simulation(window, qapp)

    window.timeline.set_time(0.0)
    qapp.processEvents()
    early = window.console_panel.view.toPlainText()
    window.timeline.set_time(window._trace.duration_ms)  # noqa: SLF001
    qapp.processEvents()
    late = window.console_panel.view.toPlainText()
    assert "primo" in early
    assert "secondo" not in early
    assert "secondo" in late


def test_port_configuration_reaches_the_simulation(window, qapp, tmp_path):
    # Il sensore di distanza legge ancora il valore impostato a mano: è il
    # modo più diretto per verificare che il pannello delle porte arrivi fino
    # al processo che esegue il programma (il colore, col tappeto, legge il
    # tappeto).
    path = _write(
        tmp_path,
        "import distance_sensor\n"
        "from hub import port\n"
        "import runloop\n"
        "\n"
        "async def main():\n"
        "    print(distance_sensor.distance(port.D))\n"
        "    await runloop.sleep_ms(10)\n"
        "\n"
        "runloop.run(main())\n",
    )
    combo = window.port_panel._device_boxes[PORT_D]  # noqa: SLF001
    combo.setCurrentIndex(combo.findData(DISTANCE_SENSOR))
    window.load_program(str(path))
    window.simulate()
    _wait_for_simulation(window, qapp)
    trace = window._trace  # noqa: SLF001
    assert trace.ok, trace.diagnostics
    text = [e.data["text"] for e in trace.events if e.type == "print"]
    assert text == ["200"]


def test_a_missing_sensor_on_the_port_still_fails(window, qapp, tmp_path):
    """La configurazione delle porte continua a contare davvero."""
    path = _write(
        tmp_path,
        "import color_sensor\n"
        "from hub import port\n"
        "\n"
        "print(color_sensor.color(port.F))\n",
    )
    window.load_program(str(path))
    window.simulate()
    _wait_for_simulation(window, qapp)
    trace = window._trace  # noqa: SLF001
    assert not trace.ok
    assert any("SPIKE011" in d.code for d in trace.diagnostics), trace.diagnostics


def test_closing_during_a_simulation_is_safe(window, qapp, tmp_path):
    path = _write(tmp_path, "while True:\n    pass\n")
    window.load_program(str(path))
    window.simulate()
    qapp.processEvents()
    assert window._thread is not None and window._thread.isRunning()  # noqa: SLF001

    window.close()
    qapp.processEvents()

    assert window._thread is None, "il lavoratore deve essere stato fermato"


def test_diagnostics_are_rechecked_when_the_hardware_changes(window, tmp_path):
    path = _write(
        tmp_path,
        "import motor\n"
        "from hub import port\n"
        "\n"
        "motor.run(port.C, 500)\n",
    )
    window.load_program(str(path))
    assert window.problems_panel.tree.topLevelItemCount() == 1

    combo = window.port_panel._device_boxes[PORT_C]  # noqa: SLF001
    combo.setCurrentIndex(combo.findData("motor_medium"))
    assert window.problems_panel.tree.topLevelItemCount() == 0


#: In Qt reale il QMimeData di un evento è di proprietà di chi genera
#: l'evento; qui l'evento lo costruiamo a mano, quindi dobbiamo tenerlo vivo
#: noi, altrimenti l'oggetto Python viene raccolto e Qt legge memoria libera.
_MIME_KEEPALIVE: list[QMimeData] = []


def _drop_event(paths: list[str]) -> QDropEvent:
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(path) for path in paths])
    _MIME_KEEPALIVE.append(mime)
    return QDropEvent(
        QPoint(20, 20), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier
    )
