"""Costanti numeriche della libreria SPIKE 3.

Stanno in un modulo isolato (nessuna dipendenza interna) perché servono sia
ai moduli della libreria simulata sia al runtime. I nomi sono quelli della
documentazione SPIKE 3; le costanti che nella documentazione appartengono a
moduli diversi ma hanno lo stesso valore (``motor.READY`` e ``motor.COAST``
valgono entrambi 0) hanno qui un prefisso che ne indica il modulo.
"""

from __future__ import annotations

# --- motor: stato di un movimento ------------------------------------------
MOTOR_READY = 0
MOTOR_RUNNING = 1
MOTOR_STALLED = 2
MOTOR_CANCELLED = 3
MOTOR_ERROR = 4
MOTOR_DISCONNECTED = 5

# --- motor: comportamento allo stop ----------------------------------------
MOTOR_COAST = 0
MOTOR_BRAKE = 1
MOTOR_HOLD = 2
MOTOR_CONTINUE = 3
MOTOR_SMART_COAST = 4
MOTOR_SMART_BRAKE = 5

# --- motor: direzione ------------------------------------------------------
MOTOR_CLOCKWISE = 0
MOTOR_COUNTERCLOCKWISE = 1
MOTOR_SHORTEST_PATH = 2
MOTOR_LONGEST_PATH = 3

# --- motor_pair ------------------------------------------------------------
PAIR_1 = 0
PAIR_2 = 1
PAIR_3 = 2

# --- hub.button ------------------------------------------------------------
BUTTON_LEFT = 1
BUTTON_RIGHT = 2

# --- hub.light -------------------------------------------------------------
LIGHT_POWER = 0
LIGHT_CONNECT = 1

# --- hub.sound -------------------------------------------------------------
SOUND_ANY = -2
SOUND_DEFAULT = -1
WAVEFORM_SINE = 1
WAVEFORM_SQUARE = 2
WAVEFORM_SAWTOOTH = 3
# La documentazione SPIKE 3 assegna 1 sia a WAVEFORM_SINE sia a
# WAVEFORM_TRIANGLE: è un refuso della tabella, mantenuto identico per non
# inventare un valore che il firmware non usa.
WAVEFORM_TRIANGLE = 1

# --- hub.motion_sensor -----------------------------------------------------
GESTURE_TAPPED = 0
GESTURE_DOUBLE_TAPPED = 1
GESTURE_SHAKEN = 2
GESTURE_FALLING = 3
GESTURE_UNKNOWN = -1

FACE_TOP = 0
FACE_FRONT = 1
FACE_RIGHT = 2
FACE_BOTTOM = 3
FACE_BACK = 4
FACE_LEFT = 5

# --- orientation -----------------------------------------------------------
ORIENTATION_UP = 0
ORIENTATION_RIGHT = 1
ORIENTATION_DOWN = 2
ORIENTATION_LEFT = 3

# --- color -----------------------------------------------------------------
COLOR_BLACK = 0
COLOR_MAGENTA = 1
COLOR_PURPLE = 2
COLOR_BLUE = 3
COLOR_AZURE = 4
COLOR_TURQUOISE = 5
COLOR_GREEN = 6
COLOR_YELLOW = 7
COLOR_ORANGE = 8
COLOR_RED = 9
COLOR_WHITE = 10
COLOR_UNKNOWN = -1

#: Nomi dei colori nell'ordine degli indici 0..10, più ``UNKNOWN``.
COLOR_NAMES = (
    "BLACK", "MAGENTA", "PURPLE", "BLUE", "AZURE", "TURQUOISE",
    "GREEN", "YELLOW", "ORANGE", "RED", "WHITE",
)

#: Indice dell'immagine della Light Matrix -> nome della costante ``IMAGE_*``.
IMAGE_NAMES = (
    "HEART", "HEART_SMALL", "HAPPY", "SMILE", "SAD", "CONFUSED", "ANGRY",
    "ASLEEP", "SURPRISED", "SILLY", "FABULOUS", "MEH", "YES", "NO",
    "CLOCK12", "CLOCK1", "CLOCK2", "CLOCK3", "CLOCK4", "CLOCK5", "CLOCK6",
    "CLOCK7", "CLOCK8", "CLOCK9", "CLOCK10", "CLOCK11",
    "ARROW_N", "ARROW_NE", "ARROW_E", "ARROW_SE", "ARROW_S", "ARROW_SW",
    "ARROW_W", "ARROW_NW", "GO_RIGHT", "GO_LEFT", "GO_UP", "GO_DOWN",
    "TRIANGLE", "TRIANGLE_LEFT", "CHESSBOARD", "DIAMOND", "DIAMOND_SMALL",
    "SQUARE", "SQUARE_SMALL", "RABBIT", "COW", "MUSIC_CROTCHET",
    "MUSIC_QUAVER", "MUSIC_QUAVERS", "PITCHFORK", "XMAS", "PACMAN", "TARGET",
    "TSHIRT", "ROLLERSKATE", "DUCK", "HOUSE", "TORTOISE", "BUTTERFLY",
    "STICKFIGURE", "GHOST", "SWORD", "GIRAFFE", "SKULL", "UMBRELLA", "SNAKE",
)

#: Nome della costante ``IMAGE_*`` -> indice 1..67.
IMAGE_CONSTANTS = {name: index for index, name in enumerate(IMAGE_NAMES, start=1)}

#: Le stesse immagini della Light Matrix, usate da ``app.display`` (1..21).
APP_IMAGE_NAMES = (
    "ROBOT_1", "ROBOT_2", "ROBOT_3", "ROBOT_4", "ROBOT_5",
    "HUB_1", "HUB_2", "HUB_3", "HUB_4",
    "AMUSEMENT_PARK", "BEACH", "HAUNTED_HOUSE", "CARNIVAL", "BOOKSHELF",
    "PLAYGROUND", "MOON", "CAVE", "OCEAN", "POLAR_BEAR", "PARK", "RANDOM",
)
APP_IMAGE_CONSTANTS = {name: index for index, name in enumerate(APP_IMAGE_NAMES, start=1)}

#: ``app.music`` — strumenti MIDI (1..21).
INSTRUMENT_NAMES = (
    "PIANO", "ELECTRIC_PIANO", "ORGAN", "GUITAR", "ELECTRIC_GUITAR", "BASS",
    "PIZZICATO", "CELLO", "TROMBONE", "CLARINET", "SAXOPHONE", "FLUTE",
    "WOODEN_FLUTE", "BASSOON", "CHOIR", "VIBRAPHONE", "MUSIC_BOX",
    "STEEL_DRUM", "MARIMBA", "SYNTH_LEAD", "SYNTH_PAD",
)
INSTRUMENT_CONSTANTS = {name: index for index, name in enumerate(INSTRUMENT_NAMES, start=1)}

#: ``app.music`` — percussioni.
DRUM_NAMES = (
    "SNARE", "BASS", "SIDE_STICK", "CRASH_CYMBAL", "OPEN_HI_HAT",
    "CLOSED_HI_HAT", "TAMBOURINE", "HAND_CLAP", "CLAVES", "WOOD_BLOCK",
    "COWBELL", "TRIANGLE", "BONGO", "CONGA", "CABASA", "GUIRO",
    "VIBRASLAP", "CUICA",
)
DRUM_CONSTANTS = {name: index for index, name in enumerate(DRUM_NAMES, start=1)}
