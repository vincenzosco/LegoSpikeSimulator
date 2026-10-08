"""Tappeto a mattonelle: superfici leggibili dai sensori, luce e percorsi.

Il tappeto è il *mondo* sotto il robot. È fatto di mattonelle quadrate
disposte su una griglia; ogni mattonella ha un tipo, e dal tipo discendono il
colore e la riflessione che il sensore di colore misura quando il robot ci
passa sopra.

Due scelte di modello, entrambe volute:

* il sensore legge la mattonella sotto il **centro** del robot — è
  letteralmente "quando passa sopra una mattonella". Così una rotazione sul
  posto non cambia la lettura, e il programma può girare *e poi* avanzare
  restando sempre allineato alla griglia;
* la pista è generata **una volta sola**, nella GUI, e poi viaggia dentro la
  `Config` fino al processo che esegue il programma. Se il sorteggio
  avvenisse nel processo figlio, il robot non seguirebbe il tappeto che
  l'utente vede.

La codifica delle mattonelle è quella dei tappeti didattici: le mattonelle
dritte sono nere (il "nastro"), quelle di curva sono colorate, perché il
programma debba *leggere* dove girarà.
"""

from __future__ import annotations

import math
import os
import random
from dataclasses import dataclass, field
from typing import Any

from .spike import color

#: Cartella dei programmi-template (``templates/seguilinea.py``, ...).
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(REPO_ROOT, "templates")

#: Lato di una mattonella (mm). Un percorso di sei mattonelle è lungo 60 cm.
DEFAULT_TILE_SIZE_MM = 100.0

# --- tipi di mattonella -----------------------------------------------------

EMPTY = "empty"
START = "start"
STRAIGHT = "straight"
TURN_LEFT = "turn_left"
TURN_RIGHT = "turn_right"
CROSS = "cross"
FINISH = "finish"

TILE_KINDS = (START, STRAIGHT, TURN_LEFT, TURN_RIGHT, CROSS, FINISH, EMPTY)

#: Tipi che il robot può incontrare *standoci sopra* mentre percorre la pista.
PATH_KINDS = (START, STRAIGHT, TURN_LEFT, TURN_RIGHT, CROSS, FINISH)

#: Colore che il sensore legge su ogni tipo di mattonella.
TILE_COLORS = {
    EMPTY: color.WHITE,
    START: color.BLUE,
    STRAIGHT: color.BLACK,
    TURN_LEFT: color.GREEN,
    TURN_RIGHT: color.RED,
    CROSS: color.BLACK,
    FINISH: color.YELLOW,
}

#: Riflessione (0-100) che il sensore misura su ogni tipo di mattonella,
#: a luce piena. Il nastro è scuro, il fondo chiaro: è questa differenza che
#: rende leggibile la pista.
TILE_REFLECTION = {
    EMPTY: 92,
    START: 55,
    STRAIGHT: 6,
    TURN_LEFT: 45,
    TURN_RIGHT: 45,
    CROSS: 6,
    FINISH: 70,
}

#: Titolo italiano di ogni tipo, per l'interfaccia.
TILE_LABELS = {
    EMPTY: "vuoto",
    START: "partenza",
    STRAIGHT: "dritto",
    TURN_LEFT: "curva a sinistra",
    TURN_RIGHT: "curva a destra",
    CROSS: "incrocio",
    FINISH: "arrivo",
}

#: Direzione di avanzamento (colonna, riga) per ogni verso in gradi.
DIRECTIONS = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}

#: Sotto questa percentuale di luce ambientale il sensore non distingue più i
#: colori: vede tutto uguale. È il modo in cui "si spegne la luce".
LIGHT_THRESHOLD = 25

#: Quante disposizioni provare prima di accontentarsi di una pista più corta.
_GENERATION_ATTEMPTS = 32

#: Marcatore interno: una mattonella su cui il robot deve girare.
_TURN = "turn"


# --- superfici --------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Surface:
    """Ciò che il sensore di colore misura in un punto del tappeto."""

    color: int = color.WHITE
    reflection: int = 92


@dataclass(frozen=True, slots=True)
class Tile:
    """Una mattonella: tipo e verso di *entrata* (per disegnarla)."""

    kind: str = EMPTY
    rotation: int = 0

    def __post_init__(self) -> None:
        if self.kind not in TILE_KINDS:
            raise ValueError(f"tipo di mattonella sconosciuto: {self.kind!r}")

    def surface(self) -> Surface:
        return Surface(TILE_COLORS[self.kind], TILE_REFLECTION[self.kind])

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "rotation": self.rotation}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Tile":
        return cls(kind=str(data.get("kind", EMPTY)), rotation=int(data.get("rotation", 0)))


def apply_light(surface: Surface, ambient: int) -> Surface:
    """La superficie *vista* dal sensore con ``ambient`` percento di luce.

    La riflessione è proporzionale alla luce: al buio non torna indietro
    niente. Sotto la soglia il sensore non distingue più i colori e riporta
    ``color.UNKNOWN`` — è il comportamento che fa "perdere la pista" al
    programma di esempio quando si abbassa la luce.
    """
    level = max(0, min(100, int(ambient)))
    reflection = int(round(surface.reflection * level / 100.0))
    if level < LIGHT_THRESHOLD:
        return Surface(color.UNKNOWN, reflection)
    return Surface(surface.color, reflection)


# --- tappeto ----------------------------------------------------------------


@dataclass(slots=True)
class Mat:
    """Griglia di mattonelle, più la posa da cui parte il robot."""

    tile_size_mm: float = DEFAULT_TILE_SIZE_MM
    tiles: dict[tuple[int, int], Tile] = field(default_factory=dict)
    start_x: float = 0.0
    start_y: float = 0.0
    start_heading: float = 0.0
    seed: int = 0

    # -- interrogazioni ----------------------------------------------------

    def cell_at(self, x_mm: float, y_mm: float) -> tuple[int, int]:
        """Cella della griglia che contiene il punto (mm)."""
        size = self.tile_size_mm or DEFAULT_TILE_SIZE_MM
        return (math.floor(x_mm / size + 0.5), math.floor(y_mm / size + 0.5))

    def centre_of(self, col: int, row: int) -> tuple[float, float]:
        size = self.tile_size_mm or DEFAULT_TILE_SIZE_MM
        return (col * size, row * size)

    def tile_at(self, x_mm: float, y_mm: float) -> Tile:
        """La mattonella sotto il punto; ``EMPTY`` fuori dalla pista."""
        return self.tiles.get(self.cell_at(x_mm, y_mm), Tile(EMPTY))

    def surface_at(self, x_mm: float, y_mm: float) -> Surface:
        """Superficie (non illuminata) nel punto."""
        return self.tile_at(x_mm, y_mm).surface()

    def bounds(self) -> tuple[float, float, float, float]:
        """(sinistra, basso, destra, alto) in mm, mattonelle comprese."""
        if not self.tiles:
            half = (self.tile_size_mm or DEFAULT_TILE_SIZE_MM) * 2
            return (self.start_x - half, self.start_y - half, self.start_x + half, self.start_y + half)
        half = (self.tile_size_mm or DEFAULT_TILE_SIZE_MM) / 2.0
        cols = [col for col, _row in self.tiles]
        rows = [row for _col, row in self.tiles]
        return (
            min(cols) * self.tile_size_mm - half,
            min(rows) * self.tile_size_mm - half,
            max(cols) * self.tile_size_mm + half,
            max(rows) * self.tile_size_mm + half,
        )

    def path_tiles(self) -> list[tuple[int, int]]:
        """Celle della pista in ordine di percorrenza (partenza -> arrivo)."""
        order: list[tuple[int, int]] = []
        cell = self.cell_at(self.start_x, self.start_y)
        heading = int(self.start_heading) % 360
        seen: set[tuple[int, int]] = set()
        while cell not in seen:
            seen.add(cell)
            order.append(cell)
            tile = self.tiles.get(cell)
            if tile is None or tile.kind == FINISH:
                break
            if tile.kind == TURN_LEFT:
                heading = (heading + 90) % 360
            elif tile.kind == TURN_RIGHT:
                heading = (heading - 90) % 360
            dc, dr = DIRECTIONS[heading]
            cell = (cell[0] + dc, cell[1] + dr)
        return order

    # -- serializzazione ----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "tile_size_mm": self.tile_size_mm,
            "start_x": self.start_x,
            "start_y": self.start_y,
            "start_heading": self.start_heading,
            "seed": self.seed,
            "tiles": [
                {"col": col, "row": row, **tile.to_dict()}
                for (col, row), tile in sorted(self.tiles.items())
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Mat":
        tiles = {
            (int(entry["col"]), int(entry["row"])): Tile.from_dict(entry)
            for entry in data.get("tiles", [])
        }
        return cls(
            tile_size_mm=float(data.get("tile_size_mm", DEFAULT_TILE_SIZE_MM)),
            tiles=tiles,
            start_x=float(data.get("start_x", 0.0)),
            start_y=float(data.get("start_y", 0.0)),
            start_heading=float(data.get("start_heading", 0.0)),
            seed=int(data.get("seed", 0)),
        )


# --- generazione casuale ----------------------------------------------------


def _attempt(
    rng: random.Random, straights: int, turns: int
) -> dict[tuple[int, int], Tile] | None:
    """Un tentativo di pista; ``None`` se il sorteggio si chiude in un vicolo.

    La pista è una passeggiata su una griglia: si parte dalla cella (0, 0)
    guardando a est e a ogni passo si decide se tirare dritto o girare,
    senza mai ripassare su una cella già occupata.
    """
    actions = [_TURN if move else "straight" for move in [False] * (straights - 1) + [True] * turns]
    rng.shuffle(actions)
    # La prima mattonella non può girare: il robot ci nasce sopra.
    actions.insert(0, "straight")

    tiles: dict[tuple[int, int], Tile] = {(0, 0): Tile(START, 0)}
    visited = {(0, 0)}
    col = row = 0
    heading = 0

    for index, action in enumerate(actions):
        previous = (col, row)
        if index == 0:
            # Dalla partenza si va sempre dritto, verso est.
            col, row = previous[0] + 1, previous[1]
            if (col, row) in visited:
                return None
            visited.add((col, row))
            continue

        if action == "straight":
            dc, dr = DIRECTIONS[heading]
            col, row = previous[0] + dc, previous[1] + dr
            if (col, row) in visited:
                return None
            tiles[previous] = Tile(STRAIGHT, heading)
        else:
            # ``heading`` cresce in senso antiorario (0 = est): girare a
            # sinistra *aumenta* il verso, come lo sterzo -100 dei motori.
            choices = [
                (TURN_LEFT, (heading + 90) % 360),
                (TURN_RIGHT, (heading - 90) % 360),
            ]
            rng.shuffle(choices)
            picked = None
            for kind, new_heading in choices:
                dc, dr = DIRECTIONS[new_heading]
                if (previous[0] + dc, previous[1] + dr) not in visited:
                    picked = (kind, new_heading, previous[0] + dc, previous[1] + dr)
                    break
            if picked is None:
                return None
            kind, new_heading, col, row = picked
            tiles[previous] = Tile(kind, heading)
            heading = new_heading
        visited.add((col, row))

    tiles[(col, row)] = Tile(FINISH, heading)
    return tiles


def generate_track(
    seed: int,
    *,
    straights: int = 6,
    turns: int = 4,
    tile_size_mm: float = DEFAULT_TILE_SIZE_MM,
) -> Mat:
    """Costruisce una pista casuale ma riproducibile dal seme ``seed``.

    Con lo stesso seme si ottiene sempre la stessa pista: l'utente vede un
    tappeto "nuovo" premendo *Nuovo percorso*, ma una simulazione resta
    ripetibile.
    """
    straights = max(1, int(straights))
    turns = max(0, int(turns))
    rng = random.Random(seed)
    for _attempt_index in range(_GENERATION_ATTEMPTS):
        tiles = _attempt(rng, straights, turns)
        if tiles is not None:
            return Mat(
                tile_size_mm=float(tile_size_mm),
                tiles=tiles,
                start_x=0.0,
                start_y=0.0,
                start_heading=0.0,
                seed=seed,
            )
    # Irraggiungibile in pratica: il primo tentativo riesce quasi sempre e i
    # tentativi hanno tutti lo stesso seme, quindi o riescono o falliscono
    # insieme solo in casi degeneri.
    return Mat(tile_size_mm=float(tile_size_mm), tiles={(0, 0): Tile(START, 0), (1, 0): Tile(FINISH, 0)}, seed=seed)


# --- template ---------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TrackTemplate:
    """Un percorso pronto all'uso: che pista generare e che programma caricare.

    ``ports`` è la configurazione consigliata per il programma del template:
    senza un sensore di colore collegato il segui-linea non avrebbe niente da
    leggere.
    """

    key: str
    name: str
    program: str
    description: str = ""
    straights: int = 6
    turns: int = 4
    tile_size_mm: float = DEFAULT_TILE_SIZE_MM
    ports: dict[int, str] = field(default_factory=dict)

    @property
    def program_path(self) -> str:
        """Percorso assoluto del programma del template."""
        return os.path.join(TEMPLATES_DIR, self.program)


#: I template disponibili, in ordine di presentazione. Riempito in
#: `spikesim.templates` (e dai test) con `register_template`.
TRACK_TEMPLATES: dict[str, TrackTemplate] = {}


def register_template(template: TrackTemplate) -> TrackTemplate:
    """Aggiunge ``template`` al catalogo e lo restituisce."""
    TRACK_TEMPLATES[template.key] = template
    return template


def template_build(template: TrackTemplate, seed: int) -> Mat:
    """Genera la pista di ``template`` con il seme dato."""
    return generate_track(
        seed,
        straights=template.straights,
        turns=template.turns,
        tile_size_mm=template.tile_size_mm,
    )
