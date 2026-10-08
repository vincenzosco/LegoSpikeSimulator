"""Avvio dell'applicazione PyQt5."""

from __future__ import annotations

import argparse
import sys
import traceback

from PyQt5.QtWidgets import QApplication, QMessageBox

from . import theme
from .main_window import MainWindow


def _install_exception_hook() -> None:
    """Un'eccezione in uno slot PyQt5 altrimenti abortirebbe il processo.

    Meglio: mostrare il messaggio e lasciare l'applicazione viva.
    """

    def hook(exc_type, exc_value, exc_traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        detail = "".join(
            traceback.format_exception(exc_type, exc_value, exc_traceback)
        )
        sys.stderr.write(detail)
        QMessageBox.critical(
            None,
            "Errore inatteso",
            f"{exc_type.__name__}: {exc_value}\n\nDettagli sulla console.",
        )

    sys.excepthook = hook


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spikesim",
        description="Simulatore di programmi Python per LEGO SPIKE Prime.",
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="programma .py da caricare all'avvio",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv if argv is not None else sys.argv[1:])

    application = QApplication.instance() or QApplication(sys.argv[:1])
    application.setApplicationName("Simulatore SPIKE")
    application.setStyleSheet(theme.STYLESHEET)
    _install_exception_hook()

    window = MainWindow()
    if arguments.file:
        window.load_program(arguments.file)
    window.show()
    return application.exec_()
