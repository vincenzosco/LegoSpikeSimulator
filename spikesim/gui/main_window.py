"""Finestra principale del simulatore."""

from __future__ import annotations

import os
import threading

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QAction,
    QDockWidget,
    QFileDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ..checker import check_source
from ..config import Config, default_config
from ..runner import RunResult, run_program
from ..trace import Trace
from .code_panel import CodePanel
from .console_panel import ConsolePanel
from .hub_view import HubView
from .port_config_panel import PortConfigPanel
from .problems_panel import ProblemsPanel
from .robot_view import RobotView
from .timeline import Timeline


class _RunnerThread(QThread):
    """Esegue il programma in un processo separato, senza bloccare la GUI."""

    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self, path: str, config: Config, timeout_s: float, cancel: threading.Event
    ) -> None:
        super().__init__()
        self._path = path
        self._config = config
        self._timeout = timeout_s
        self._cancel = cancel

    def run(self) -> None:  # noqa: D102 - metodo di QThread
        try:
            self.completed.emit(
                run_program(
                    self._path,
                    self._config,
                    timeout_s=self._timeout,
                    cancel=self._cancel,
                )
            )
        except Exception as exc:  # pragma: no cover - difensivo
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Simulatore LEGO SPIKE Prime")
        self.resize(1360, 900)
        self.setAcceptDrops(True)

        self._config = default_config()
        self._thread: _RunnerThread | None = None
        self._cancel: threading.Event | None = None
        self._trace: Trace | None = None

        self.code_panel = CodePanel()
        self.problems_panel = ProblemsPanel()
        self.robot_view = RobotView()
        self.hub_view = HubView()
        self.console_panel = ConsolePanel()
        self.timeline = Timeline()
        self.port_panel = PortConfigPanel()

        self._build_layout()
        self._build_toolbar()
        self._connect()
        self._set_status("Trascina un file .py nella finestra, oppure incolla il percorso.")

    # -- costruzione ---------------------------------------------------------

    def _build_layout(self) -> None:
        left = QSplitter(Qt.Vertical)
        left.addWidget(self.code_panel)
        left.addWidget(self.problems_panel)
        left.setStretchFactor(0, 3)
        left.setStretchFactor(1, 2)

        right = QSplitter(Qt.Vertical)
        right.addWidget(self.robot_view)
        right.addWidget(self.hub_view)
        right.setStretchFactor(0, 3)
        right.setStretchFactor(1, 1)

        centre = QSplitter(Qt.Horizontal)
        centre.addWidget(left)
        centre.addWidget(right)
        centre.setStretchFactor(0, 1)
        centre.setStretchFactor(1, 1)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addWidget(centre, 1)
        layout.addWidget(self.timeline)
        self.setCentralWidget(container)

        console_dock = QDockWidget("Console", self)
        console_dock.setWidget(self.console_panel)
        console_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.BottomDockWidgetArea, console_dock)
        self.console_dock = console_dock

        ports_dock = QDockWidget("Hardware", self)
        ports_dock.setWidget(self.port_panel)
        ports_dock.setMinimumWidth(280)
        ports_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.RightDockWidgetArea, ports_dock)
        self.ports_dock = ports_dock

        self.status = QLabel()
        self.statusBar().addWidget(self.status, 1)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Principale")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.open_action = QAction("Apri…", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.choose_file)
        toolbar.addAction(self.open_action)

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText(
            "Percorso del file .py da simulare (incollalo qui e premi Invio)"
        )
        self.path_edit.setMinimumWidth(360)
        self.path_edit.returnPressed.connect(self._load_from_field)
        toolbar.addWidget(self.path_edit)

        load_button = QPushButton("Apri")
        load_button.clicked.connect(self._load_from_field)
        toolbar.addWidget(load_button)

        toolbar.addSeparator()

        self.run_action = QAction("▶  Simula", self)
        self.run_action.setShortcut("F5")
        self.run_action.triggered.connect(self.simulate)
        toolbar.addAction(self.run_action)

        self.check_action = QAction("Controlla", self)
        self.check_action.setShortcut("F6")
        self.check_action.triggered.connect(self.recheck)
        toolbar.addAction(self.check_action)

    def _connect(self) -> None:
        self.problems_panel.problemActivated.connect(self.code_panel.goto_line)
        self.timeline.timeChanged.connect(self._on_time_changed)
        self.port_panel.configChanged.connect(self._on_config_changed)

    # -- apertura del programma ---------------------------------------------

    def choose_file(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(
            self, "Scegli il programma", "", "Programmi Python (*.py)"
        )
        if path:
            self.load_program(path)

    def _load_from_field(self) -> None:
        text = self.path_edit.text().strip().strip('"').strip("'")
        if text:
            self.load_program(os.path.expanduser(text))

    def load_program(self, path: str) -> bool:
        """Carica ``path``: usata sia dal campo di testo sia dal drag & drop."""
        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isfile(path):
            self._warn("File non trovato", f"«{path}» non esiste o non è un file.")
            return False
        if not path.lower().endswith(".py"):
            self._warn(
                "Formato non supportato",
                "Il simulatore esegue solo file Python (.py).",
            )
            return False
        try:
            with open(path, "r", encoding="utf-8") as handle:
                source = handle.read()
        except (OSError, UnicodeDecodeError) as exc:
            self._warn("File non leggibile", str(exc))
            return False

        self.code_panel.set_program(path, source)
        self.path_edit.setText(path)
        self._reset_simulation()
        self.recheck()
        self._set_status(f"Caricato {os.path.basename(path)} — premi Simula (F5).")
        return True

    def recheck(self) -> None:
        path = self.code_panel.path
        if not path:
            self.problems_panel.clear()
            return
        diagnostics = check_source(path, self.port_panel.config())
        self.problems_panel.set_diagnostics(diagnostics)

    # -- simulazione ---------------------------------------------------------

    def simulate(self) -> None:
        path = self.code_panel.path
        if not path:
            self._warn("Nessun programma", "Apri prima un file .py da simulare.")
            return
        if self._thread is not None and self._thread.isRunning():
            return

        config = self.port_panel.config()
        self.problems_panel.set_diagnostics(check_source(path, config))
        self._reset_simulation()
        self._set_busy(True)
        self._set_status("Simulazione in corso…")

        self._cancel = threading.Event()
        self._thread = _RunnerThread(path, config, 90.0, self._cancel)
        self._thread.completed.connect(self._on_result)
        self._thread.failed.connect(self._on_failure)
        self._thread.start()

    def _on_result(self, result: RunResult) -> None:
        self._set_busy(False)
        trace = result.trace
        self._trace = trace
        self.problems_panel.set_diagnostics(trace.diagnostics)
        self.console_panel.set_trace(trace, trace.diagnostics)
        self.robot_view.set_trace(trace)
        self.hub_view.set_trace(trace, self.port_panel.config())
        self.timeline.set_duration(trace.duration_ms)
        self._on_time_changed(0.0)

        errors = trace.count("error")
        warnings = trace.count("warning")
        state = "completato" if trace.terminated else "interrotto"
        self._set_status(
            f"Simulazione {state} — {trace.duration_ms / 1000:.2f} s simulati, "
            f"{errors} errori, {warnings} avvisi."
        )
        if trace.duration_ms > 0:
            self.timeline.play()
        if result.stderr.strip():
            self.console_panel.view.appendPlainText(
                "\n— messaggi del processo —\n" + result.stderr.strip()
            )

    def _on_failure(self, message: str) -> None:
        self._set_busy(False)
        self._set_status("Simulazione non riuscita.")
        self._warn("Errore di esecuzione", message)

    def _reset_simulation(self) -> None:
        self._trace = None
        self.robot_view.set_trace(None)
        self.hub_view.set_trace(None, self.port_panel.config())
        self.console_panel.clear()
        self.timeline.set_duration(0)

    def _on_time_changed(self, t_ms: float) -> None:
        self.robot_view.set_time(t_ms)
        self.hub_view.set_time(t_ms)
        self.console_panel.show_until(t_ms)
        if self._trace is not None:
            x, y, heading = self._trace.pose_at(t_ms)
            self.statusBar().showMessage(
                f"x={x:7.1f} mm   y={y:7.1f} mm   verso={heading:6.1f}°", 4000
            )

    # -- configurazione ------------------------------------------------------

    def _on_config_changed(self) -> None:
        self.recheck()

    # -- drag & drop ---------------------------------------------------------

    def dragEnterEvent(self, event) -> None:  # noqa: N802 - nome imposto da Qt
        if self._first_python_file(event) is not None:
            event.acceptProposedAction()
            self.code_panel.set_drop_active(True)
            self._set_status("Rilascia il file per caricarlo.")
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802 - nome imposto da Qt
        self.code_panel.set_drop_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:  # noqa: N802 - nome imposto da Qt
        self.code_panel.set_drop_active(False)
        path = self._first_python_file(event)
        if path is None:
            event.ignore()
            return
        event.acceptProposedAction()
        self.load_program(path)

    @staticmethod
    def _first_python_file(event) -> str | None:
        mime = event.mimeData()
        if not mime.hasUrls():
            return None
        for url in mime.urls():
            if not url.isLocalFile():
                continue
            path = url.toLocalFile()
            if os.path.isfile(path) and path.lower().endswith(".py"):
                return path
        return None

    # -- utilità -------------------------------------------------------------

    def closeEvent(self, event) -> None:  # noqa: N802 - nome imposto da Qt
        """Chiudendo la finestra non deve restare un programma in sottofondo."""
        self._stop_runner()
        super().closeEvent(event)

    def _stop_runner(self) -> None:
        thread, self._thread = self._thread, None
        if self._cancel is not None:
            self._cancel.set()
            self._cancel = None
        if thread is None:
            return
        # Scollegarsi prima: se il lavoratore finisse comunque mentre la
        # finestra se ne sta andando, non deve richiamare i suoi slot.
        for signal in (thread.completed, thread.failed):
            try:
                signal.disconnect()
            except TypeError:
                pass
        if thread.isRunning() and not thread.wait(3000):  # pragma: no cover - difensivo
            thread.terminate()
            thread.wait(1000)

    def _set_busy(self, busy: bool) -> None:
        self.run_action.setEnabled(not busy)
        self.open_action.setEnabled(not busy)
        self.run_action.setText("⏳  Simulazione…" if busy else "▶  Simula")

    def _set_status(self, text: str) -> None:
        self.status.setText(text)

    def _warn(self, title: str, message: str) -> None:
        QMessageBox.warning(self, title, message)
