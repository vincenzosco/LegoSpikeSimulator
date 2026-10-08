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

from spikesim.config import PORT_C, COLOR_SENSOR

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


def test_window_starts_empty(window):
    assert window.code_panel.path is None
    assert window.robot_view._trace is None  # noqa: SLF001
    assert not window.timeline.play_button.isEnabled()


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
    original = QMessageBox.warning
    QMessageBox.warning = staticmethod(  # type: ignore[assignment]
        lambda _parent, title, message, *args, **kwargs: None
    )
    try:
        assert window.load_program(str(other)) is False
    finally:
        QMessageBox.warning = original  # type: ignore[assignment]
    assert window.code_panel.path is None


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
    other = tmp_path / "immagine.png"
    other.write_bytes(b"\x89PNG")
    event = _drop_event([str(other)])
    window.dropEvent(event)
    assert window.code_panel.path is None


def test_drag_and_drop_ignores_a_directory(window, tmp_path):
    event = _drop_event([str(tmp_path)])
    window.dropEvent(event)
    assert window.code_panel.path is None


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
    path = _write(
        tmp_path,
        "import color_sensor\n"
        "from hub import port\n"
        "import runloop\n"
        "\n"
        "async def main():\n"
        "    print(color_sensor.color(port.C))\n"
        "    await runloop.sleep_ms(10)\n"
        "\n"
        "runloop.run(main())\n",
    )
    window.port_panel._device_boxes[PORT_C].setCurrentIndex(  # noqa: SLF001
        window.port_panel._device_boxes[PORT_C].findData(COLOR_SENSOR)  # noqa: SLF001
    )
    window.load_program(str(path))
    window.simulate()
    _wait_for_simulation(window, qapp)
    trace = window._trace  # noqa: SLF001
    assert trace.ok, trace.diagnostics
    text = [e.data["text"] for e in trace.events if e.type == "print"]
    assert text == ["9"]


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
