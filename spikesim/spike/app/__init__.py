"""Modulo ``app``: la comunicazione fra hub e applicazione.

Nella simulazione non c'è un'app: le funzioni producono eventi che la GUI
mostra nel pannello della console, così si vede comunque *cosa* il
programma avrebbe mandato allo schermo.
"""

from __future__ import annotations

from . import bargraph, display, linegraph, music, sound

__all__ = ["bargraph", "display", "linegraph", "music", "sound"]
