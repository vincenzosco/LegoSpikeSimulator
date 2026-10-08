"""Interfaccia PyQt5 del simulatore.

Tutto ciò che dipende da Qt vive qui dentro: `spikesim.runner`,
`spikesim.checker` e `spikesim.runtime` restano usabili (e testabili) senza
una QApplication.
"""

from __future__ import annotations

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    """Avvia la GUI (import ritardato: serve una QApplication già pronta)."""
    from .app import main as _main

    return _main(argv)
