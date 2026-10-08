#!/usr/bin/env python3
"""Avvia il simulatore LEGO SPIKE Prime.

Esempi::

    python3 run_simulator.py
    python3 run_simulator.py examples/quadrato.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spikesim.gui.app import main  # noqa: E402 - dopo l'aggiunta del percorso

if __name__ == "__main__":
    raise SystemExit(main())
