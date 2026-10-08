"""Colori e foglio di stile condivisi dalla GUI."""

from __future__ import annotations

BACKGROUND = "#12161f"
SURFACE = "#1b2130"
SURFACE_ALT = "#232b3d"
BORDER = "#2e3850"
TEXT = "#e6ebf5"
TEXT_MUTED = "#93a0b8"
ACCENT = "#2f8bff"
FIELD = "#0e1420"
GRID = "#1d2740"
GRID_MAJOR = "#27334f"
PATH = "#8fd0ff"
ROBOT = "#2f8bff"
ROBOT_DARK = "#1b5bb0"
ERROR = "#ff6b6b"
WARNING = "#ffc857"
INFO = "#7fd1a6"
MATRIX_ON = "#ff4d4d"

# --- tappeto a mattonelle ---------------------------------------------------

#: Il "tavolo" su cui è appoggiato il tappeto.
MAT_BACKGROUND = "#eef1f7"
MAT_GRID = "#c3ccdd"
#: Il nastro nero che unisce le mattonelle della pista.
MAT_LINE = "#101418"

#: Colore con cui si disegna ogni tipo di mattonella (chiavi di `spikesim.mat`).
TILE_FILL = {
    "empty": MAT_BACKGROUND,
    "start": "#2f6bff",
    "straight": "#151a24",
    "turn_left": "#3ddb5a",
    "turn_right": "#ff3b30",
    "cross": "#151a24",
    "finish": "#ffe14d",
}

#: Ordine dei colori SPIKE (0..10), usato per i LED dell'app.
SPIKE_COLORS = (
    "#000000", "#ff4dd2", "#8b4dff", "#2f6bff", "#37b6ff",
    "#2fd6c8", "#3ddb5a", "#ffe14d", "#ff9a3d", "#ff3b30",
    "#ffffff",
)

STYLESHEET = f"""
QWidget {{
    background: {BACKGROUND};
    color: {TEXT};
    font-size: 13px;
}}
QMainWindow::separator {{ background: {BORDER}; width: 1px; height: 1px; }}
QLabel[role="section"] {{
    color: {TEXT_MUTED};
    font-weight: 600;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 1px;
    padding: 2px 0;
}}
QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 6px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    color: {TEXT_MUTED};
}}
QPlainTextEdit, QTextEdit, QListWidget, QTreeWidget, QTableWidget {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    selection-background-color: {ACCENT};
}}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background: {SURFACE_ALT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 8px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 18px; }}
QPushButton {{
    background: {SURFACE_ALT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 14px;
}}
QPushButton:hover {{ background: #2b3550; }}
QPushButton:disabled {{ color: #5c6880; background: #1a2030; }}
QPushButton#primary {{
    background: {ACCENT};
    border-color: {ACCENT};
    color: white;
    font-weight: 600;
}}
QPushButton#primary:hover {{ background: #4a9dff; }}
QPushButton#primary:disabled {{ background: #2a3a55; border-color: #2a3a55; color: #6d7a92; }}
QToolBar {{ background: {SURFACE}; border-bottom: 1px solid {BORDER}; spacing: 6px; padding: 6px; }}
QStatusBar {{ background: {SURFACE}; border-top: 1px solid {BORDER}; }}
QHeaderView::section {{
    background: {SURFACE_ALT};
    border: none;
    border-right: 1px solid {BORDER};
    padding: 5px;
    color: {TEXT_MUTED};
}}
QSlider::groove:horizontal {{
    height: 4px; background: {BORDER}; border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT}; width: 12px; margin: -5px 0; border-radius: 6px;
}}
QScrollBar:vertical {{ background: {BACKGROUND}; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; min-height: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QPlainTextEdit#codeEditor {{
    border: 2px dashed {BORDER};
}}
QPlainTextEdit#codeEditor[active="true"] {{
    border: 2px solid {ACCENT};
    background: #1d2a44;
}}
"""
