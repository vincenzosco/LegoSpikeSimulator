"""Catalogo dei template pronti all'uso.

Un *template* è una coppia: la pista da generare e il programma SPIKE che la
percorre. È il modo più veloce per vedere qualcosa muoversi: si sceglie
«Seguilinea», il simulatore sorteggia un tappeto e carica il segui-linea.

I programmi stanno in ``templates/`` e sono normalissimi programmi SPIKE: si
possono aprire, leggere e modificare come qualunque altro esempio.
"""

from __future__ import annotations

from dataclasses import replace

from .config import COLOR_SENSOR, MOTOR_MEDIUM, PORT_A, PORT_B, PORT_C, Config, default_config
from .mat import Mat, TrackTemplate, generate_track, register_template

#: Il drive base SPIKE standard più il sensore di colore che legge il tappeto.
STANDARD_PORTS = {
    PORT_A: MOTOR_MEDIUM,
    PORT_B: MOTOR_MEDIUM,
    PORT_C: COLOR_SENSOR,
}


def _register(template: TrackTemplate) -> TrackTemplate:
    ports = dict(STANDARD_PORTS)
    ports.update(template.ports)
    return register_template(replace(template, ports=ports))


_register(
    TrackTemplate(
        key="seguilinea_facile",
        name="Seguilinea facile",
        program="seguilinea.py",
        description="Pista corta con due curve: il primo percorso da provare.",
        straights=4,
        turns=2,
    )
)

_register(
    TrackTemplate(
        key="seguilinea",
        name="Seguilinea",
        program="seguilinea.py",
        description="Pista media: il segui-linea legge la mattonella e gira di 90°.",
        straights=6,
        turns=4,
    )
)

_register(
    TrackTemplate(
        key="seguilinea_lungo",
        name="Seguilinea lungo",
        program="seguilinea.py",
        description="Pista lunga con molte curve: serve pazienza e una buona luce.",
        straights=12,
        turns=8,
    )
)


def all_templates() -> list[TrackTemplate]:
    """I template in ordine di presentazione."""
    from .mat import TRACK_TEMPLATES

    return list(TRACK_TEMPLATES.values())


def get(key: str) -> TrackTemplate:
    """Il template con questa chiave; ``KeyError`` se non esiste."""
    from .mat import TRACK_TEMPLATES

    return TRACK_TEMPLATES[key]


def build_config(
    template: TrackTemplate, seed: int, *, ambient: int = 100, base: Config | None = None
) -> tuple[Config, Mat]:
    """(configurazione, tappeto) pronti per eseguire il template.

    La pista viene sorteggiata *qui*, una volta sola: la stessa ``Config``
    porta tappeto e luce fino al processo che esegue il programma, così il
    robot percorre esattamente il tappeto che l'utente vede.
    """
    start = base or default_config()
    for port, device in template.ports.items():
        start = start.with_port(port, device)
    board = generate_track(
        seed,
        straights=template.straights,
        turns=template.turns,
        tile_size_mm=template.tile_size_mm,
    )
    return replace(start, mat=board, ambient_light=int(ambient)), board
