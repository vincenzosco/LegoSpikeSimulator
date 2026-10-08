"""Pannello console: ``print`` del programma e messaggi della simulazione."""

from __future__ import annotations

from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import QLabel, QPlainTextEdit, QVBoxLayout, QWidget

from ..trace import Diagnostic, Trace
from . import theme

_COLOR = {"error": theme.ERROR, "warning": theme.WARNING, "info": theme.TEXT_MUTED}


class ConsolePanel(QWidget):
    """Mostra i messaggi man mano che il tempo simulato avanza."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.title = QLabel("Console")
        self.title.setProperty("role", "section")

        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setFont(QFont("Menlo", 11))
        self.view.setMaximumBlockCount(5000)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(4)
        layout.addWidget(self.title)
        layout.addWidget(self.view)

        self._entries: list[tuple[int, str, str]] = []
        self._index = 0
        self._last_t = 0

    # -- API ----------------------------------------------------------------

    def set_trace(self, trace: Trace, diagnostics: list[Diagnostic]) -> None:
        self.view.clear()
        self._entries = [
            (event.t, event.type, str(event.data.get("text", "")))
            for event in trace.events
            if event.type in ("print", "note")
        ]
        self._index = 0
        self._last_t = 0

        self._append("— problemi —", theme.TEXT_MUTED)
        if not diagnostics:
            self._append("nessun problema rilevato", theme.INFO)
        else:
            for diagnostic in diagnostics:
                where = f" (riga {diagnostic.line})" if diagnostic.line else ""
                self._append(
                    f"[{diagnostic.code}]{where} {diagnostic.message}",
                    _COLOR.get(diagnostic.severity, theme.TEXT),
                )
        self._append("— esecuzione —", theme.TEXT_MUTED)

    def clear(self) -> None:
        self.view.clear()
        self._entries = []
        self._index = 0
        self._last_t = 0

    def show_until(self, t_ms: float) -> None:
        """Mostra tutti i messaggi fino al tempo simulato ``t_ms``."""
        if t_ms < self._last_t:
            self._rebuild(t_ms)
            return
        self._last_t = t_ms
        while self._index < len(self._entries) and self._entries[self._index][0] <= t_ms:
            time_ms, kind, text = self._entries[self._index]
            self._append(f"[{time_ms / 1000:6.2f} s] {text}",
                         theme.TEXT if kind == "print" else theme.TEXT_MUTED)
            self._index += 1

    # -- interni -------------------------------------------------------------

    def _rebuild(self, t_ms: float) -> None:
        """Ricostruisce la vista dopo un riavvolgimento."""
        head = self._entries
        self._entries = []
        self._index = 0
        self.view.clear()
        self._append("— esecuzione —", theme.TEXT_MUTED)
        self._entries = head
        self._last_t = -1
        while self._index < len(self._entries) and self._entries[self._index][0] <= t_ms:
            time_ms, kind, text = self._entries[self._index]
            self._append(f"[{time_ms / 1000:6.2f} s] {text}",
                         theme.TEXT if kind == "print" else theme.TEXT_MUTED)
            self._index += 1
        self._last_t = t_ms

    def _append(self, text: str, color: str) -> None:
        self.view.appendHtml(
            f'<span style="color:{color}; white-space:pre-wrap">{_escape(text)}</span>'
        )


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
