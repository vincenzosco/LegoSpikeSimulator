#!/usr/bin/env python3
"""Genera gli screenshot del README, senza bisogno di uno schermo.

Costruisce la finestra vera in modalità ``offscreen``, ci fa girare dentro il
template del segui-linea e salva delle immagini PNG in ``docs/screenshots/``.

    python3 tools/make_screenshots.py

Le immagini sono quelle usate da ``README.md`` e ``README.it.md``: se cambi la
finestra, rilancia questo script invece di rifare gli screenshot a mano.
"""

from __future__ import annotations

import os
import sys
import time

# Deve essere deciso prima che esista una QApplication.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PyQt5.QtGui import QColor, QImage  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from spikesim.gui import theme  # noqa: E402
from spikesim.gui.main_window import MainWindow  # noqa: E402

OUTPUT_DIR = os.path.join(ROOT, "docs", "screenshots")
WINDOW_SIZE = (1440, 940)
#: Quanto aspettare (secondi reali) perché la simulazione finisca.
SIMULATION_TIMEOUT_S = 120.0


def _settle(app: QApplication, rounds: int = 30) -> None:
    for _ in range(rounds):
        app.processEvents()
        time.sleep(0.005)


def _simulate(window: MainWindow, app: QApplication) -> None:
    """Esegue la simulazione e aspetta che il processo figlio finisca."""
    window.simulate()
    deadline = time.time() + SIMULATION_TIMEOUT_S
    while window._thread is not None and window._thread.isRunning():  # noqa: SLF001
        app.processEvents()
        time.sleep(0.01)
        if time.time() > deadline:
            raise SystemExit("la simulazione non è terminata in tempo")
    _settle(app, rounds=80)


def _shoot(window: MainWindow, app: QApplication, name: str, fraction: float | None = None) -> str:
    """Salva la finestra in ``docs/screenshots/<name>.png``.

    ``fraction`` posiziona la barra del tempo (0 = partenza, 1 = fine).
    """
    window.timeline.pause()
    if fraction is not None and window._trace is not None:  # noqa: SLF001
        window.timeline.set_time(window._trace.duration_ms * fraction)  # noqa: SLF001
    _settle(app)

    path = os.path.join(OUTPUT_DIR, f"{name}.png")
    pixmap = window.grab()
    if pixmap.isNull() or not pixmap.save(path, "PNG"):
        raise SystemExit(f"non sono riuscito a salvare {path}")
    print(f"scritto {path} ({pixmap.width()}x{pixmap.height()})")
    return path


def _shoot_widget(widget, app: QApplication, name: str) -> str:
    _settle(app)
    path = os.path.join(OUTPUT_DIR, f"{name}.png")
    pixmap = widget.grab()
    if pixmap.isNull() or not pixmap.save(path, "PNG"):
        raise SystemExit(f"non sono riuscito a salvare {path}")
    print(f"scritto {path} ({pixmap.width()}x{pixmap.height()})")
    return path


def _require(condition: bool, message: str) -> None:
    """Uno screenshot che non mostra quello che dice la didascalia è un bug."""
    if not condition:
        raise SystemExit(f"screenshot non valido: {message}")


def _has_colour(path: str, hex_colour: str, tolerance: int = 40) -> bool:
    """L'immagine salvata contiene quel colore? (campionata a passi di 2 px)"""
    image = QImage(path)
    if image.isNull():
        return False
    target = QColor(hex_colour)
    for y in range(0, image.height(), 2):
        for x in range(0, image.width(), 2):
            colour = image.pixelColor(x, y)
            if (
                abs(colour.red() - target.red()) <= tolerance
                and abs(colour.green() - target.green()) <= tolerance
                and abs(colour.blue() - target.blue()) <= tolerance
            ):
                return True
    return False


def main() -> int:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    app = QApplication.instance() or QApplication(["screenshot"])
    app.setApplicationName("Simulatore SPIKE")
    app.setStyleSheet(theme.STYLESHEET)

    window = MainWindow()
    window.resize(*WINDOW_SIZE)
    window.show()
    _settle(app)

    # 1 — All'apertura: il template è già scelto, la pista è disegnata e non
    #     è ancora stata simulata niente.
    window.mat_panel.set_template_by_key("seguilinea")
    window.mat_panel.seed_spin.setValue(3)
    _settle(app)
    _shoot(window, app, "01-avvio")
    _require(window.code_panel.path is not None, "al primo screenshot manca il programma")
    _require(window._trace is None, "il primo screenshot non deve avere una traccia")  # noqa: SLF001

    # 2 — A metà percorso: il robot è sul nastro, la console racconta cosa vede.
    _simulate(window, app)
    _shoot(window, app, "02-seguilinea", 0.55)
    _shoot_widget(window.robot_view, app, "03-campo")
    trace = window._trace  # noqa: SLF001
    _require(trace is not None and trace.ok, "la simulazione del segui-linea è fallita")
    _require(trace.poses[-1][1] > 0.0, "il robot non si è mosso")

    # Il campo disegna davvero le mattonelle: verde per le curve, giallo per l'arrivo.
    field = os.path.join(OUTPUT_DIR, "03-campo.png")
    _require(_has_colour(field, theme.TILE_FILL["turn_left"]), "nel campo non si vede una curva")
    _require(_has_colour(field, theme.TILE_FILL["finish"]), "nel campo non si vede l'arrivo")

    # 3 — All'arrivo: il robot si è fermato sulla mattonella gialla.
    _shoot(window, app, "04-arrivo", 1.0)
    board = window.mat_panel.mat()
    finish = board.path_tiles()[-1]
    _require(
        board.cell_at(trace.poses[-1][1], trace.poses[-1][2]) == finish,
        "il robot non è arrivato sulla mattonella di arrivo",
    )

    # 4 — Al buio: il sensore non distingue più i colori e il robot resta fermo.
    window.mat_panel.set_ambient_light(5)
    _settle(app)
    _simulate(window, app)
    _shoot(window, app, "05-buio", 1.0)
    dark = window._trace  # noqa: SLF001
    _require(dark is not None and dark.poses[-1][1:] == dark.poses[0][1:], "al buio il robot si è mosso")
    _require("non vedo" in window.console_panel.view.toPlainText(), "manca il messaggio al buio")

    # 5 — Un percorso più lungo, per far vedere quanto si allarga il campo.
    window.mat_panel.set_ambient_light(100)
    window.mat_panel.set_template_by_key("seguilinea_lungo")
    window.mat_panel.seed_spin.setValue(11)
    _settle(app)
    _simulate(window, app)
    _shoot(window, app, "06-percorso-lungo", 0.5)
    long_trace = window._trace  # noqa: SLF001
    _require(long_trace is not None and long_trace.ok, "il percorso lungo è fallito")

    window.close()
    print("tutti gli screenshot sono stati verificati")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
