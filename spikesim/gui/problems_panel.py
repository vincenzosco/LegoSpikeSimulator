"""Pannello dei problemi trovati nell'ultimo programma."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import (
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..trace import Diagnostic
from . import theme

_SEVERITY_LABEL = {"error": "Errore", "warning": "Avviso", "info": "Info"}
_SEVERITY_COLOR = {"error": theme.ERROR, "warning": theme.WARNING, "info": theme.INFO}


class ProblemsPanel(QWidget):
    """Elenco dei problemi; doppio clic per andare alla riga."""

    problemActivated = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.title = QLabel("Problemi")
        self.title.setProperty("role", "section")

        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["", "Codice", "Riga", "Messaggio"])
        self.tree.setRootIsDecorated(False)
        self.tree.setUniformRowHeights(True)
        self.tree.setColumnWidth(0, 70)
        self.tree.setColumnWidth(1, 80)
        self.tree.setColumnWidth(2, 50)
        self.tree.itemDoubleClicked.connect(self._on_activated)
        self.tree.itemActivated.connect(self._on_activated)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(4)
        layout.addWidget(self.title)
        layout.addWidget(self.tree)

    # -- API ----------------------------------------------------------------

    def set_diagnostics(self, diagnostics: list[Diagnostic]) -> None:
        self.tree.clear()
        for diagnostic in diagnostics:
            item = QTreeWidgetItem(
                [
                    _SEVERITY_LABEL.get(diagnostic.severity, diagnostic.severity),
                    diagnostic.code,
                    "" if diagnostic.line is None else str(diagnostic.line),
                    diagnostic.message,
                ]
            )
            color = QColor(_SEVERITY_COLOR.get(diagnostic.severity, theme.TEXT))
            item.setForeground(0, QBrush(color))
            item.setForeground(3, QBrush(color))
            if diagnostic.detail:
                item.setToolTip(3, diagnostic.detail)
            item.setData(0, Qt.UserRole, diagnostic.line)
            self.tree.addTopLevelItem(item)
        self._refresh_title(diagnostics)

    def clear(self) -> None:
        self.tree.clear()
        self._refresh_title([])

    def _refresh_title(self, diagnostics: list[Diagnostic]) -> None:
        errors = sum(1 for d in diagnostics if d.severity == "error")
        warnings = sum(1 for d in diagnostics if d.severity == "warning")
        if not diagnostics:
            self.title.setText("Problemi — nessuno")
        else:
            self.title.setText(f"Problemi — {errors} errori, {warnings} avvisi")

    def _on_activated(self, item: QTreeWidgetItem, _column: int = 0) -> None:
        line = item.data(0, Qt.UserRole)
        if line:
            self.problemActivated.emit(int(line))
