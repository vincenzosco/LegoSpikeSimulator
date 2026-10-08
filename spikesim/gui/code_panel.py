"""Pannello con il codice del programma caricato."""

from __future__ import annotations

import os

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QTextCharFormat, QTextCursor
from PyQt5.QtWidgets import (
    QLabel,
    QPlainTextEdit,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import theme


class _CodeEditor(QPlainTextEdit):
    """Editor in sola lettura con i numeri di riga."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setFont(QFont("Menlo", 12))
        self.line_area = _LineNumberArea(self)
        self.blockCountChanged.connect(lambda _count: self._update_margin())
        self.updateRequest.connect(self._on_update_request)
        self._update_margin()

    def _update_margin(self) -> None:
        digits = max(3, len(str(max(1, self.blockCount()))))
        width = 14 + digits * 8
        self.setViewportMargins(width, 0, 0, 0)
        self.line_area.setFixedWidth(width)

    def _on_update_request(self, rect: QRect, dy: int) -> None:
        if dy:
            self.line_area.scroll(0, dy)
        else:
            self.line_area.update(0, rect.y(), self.line_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_margin()

    def resizeEvent(self, event) -> None:  # noqa: N802 - nome imposto da Qt
        super().resizeEvent(event)
        contents = self.contentsRect()
        self.line_area.setGeometry(
            QRect(contents.left(), contents.top(), self.line_area.width(), contents.height())
        )


class _LineNumberArea(QWidget):
    def __init__(self, editor: _CodeEditor) -> None:
        super().__init__(editor)
        self._editor = editor

    def paintEvent(self, event) -> None:  # noqa: N802 - nome imposto da Qt
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor(theme.SURFACE_ALT))
        painter.setPen(QColor(theme.TEXT_MUTED))

        block = self._editor.firstVisibleBlock()
        number = block.blockNumber()
        offset = self._editor.contentOffset()
        top = self._editor.blockBoundingGeometry(block).translated(offset).top()
        height = self._editor.fontMetrics().height()
        bottom = top + self._editor.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(
                    0, int(top), self.width() - 8, height, Qt.AlignRight, str(number + 1)
                )
            block = block.next()
            top = bottom
            bottom = top + self._editor.blockBoundingRect(block).height()
            number += 1


class CodePanel(QWidget):
    """Mostra il file caricato, senza modificarlo."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._path: str | None = None

        self.title = QLabel("Nessun programma caricato")
        self.title.setProperty("role", "section")
        # Un percorso lungo non deve allargare il pannello: il percorso intero
        # resta nel suggerimento, l'etichetta mostra solo il nome del file.
        self.title.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.title.setMinimumWidth(0)

        self.editor = _CodeEditor()
        self.editor.setObjectName("codeEditor")
        self.editor.setPlaceholderText(
            "Trascina qui un file .py, oppure incolla il suo percorso e premi Apri."
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(4)
        layout.addWidget(self.title)
        layout.addWidget(self.editor)

    @property
    def path(self) -> str | None:
        return self._path

    def set_program(self, path: str, source: str) -> None:
        self._path = path
        self.title.setText(os.path.basename(path))
        self.title.setToolTip(path)
        self.editor.setPlainText(source)
        self.editor.setExtraSelections([])

    def clear(self) -> None:
        self._path = None
        self.title.setText("Nessun programma caricato")
        self.title.setToolTip("")
        self.editor.clear()
        self.editor.setExtraSelections([])

    def set_drop_active(self, active: bool) -> None:
        """Evidenzia il pannello mentre si trascina un file sopra la finestra."""
        self.editor.setProperty("active", "true" if active else "false")
        self.editor.style().unpolish(self.editor)
        self.editor.style().polish(self.editor)

    def goto_line(self, line: int) -> None:
        """Porta il cursore su ``line`` (1-based) e la evidenzia."""
        block = self.editor.document().findBlockByNumber(max(0, line - 1))
        if not block.isValid():
            return
        self.editor.setTextCursor(QTextCursor(block))
        self.editor.centerCursor()

        selection = QTextEdit.ExtraSelection()
        selection.cursor = QTextCursor(block)
        selection.format = QTextCharFormat()
        selection.format.setBackground(QColor("#3a2b2b"))
        selection.format.setProperty(QTextCharFormat.FullWidthSelection, True)
        self.editor.setExtraSelections([selection])
