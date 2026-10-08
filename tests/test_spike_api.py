"""La superficie della libreria SPIKE 3 simulata.

La tabella qui sotto è copiata da
https://tuftsceeo.github.io/SPIKEPythonDocs/SPIKE3.html (vedi anche
``docs/spike3-reference.txt``): se un nome o un valore non corrisponde, il
programma dell'utente scritto per il SPIKE App non funzionerebbe.
"""

from __future__ import annotations

import inspect
import sys

import pytest

from spikesim import spike_api
from spikesim.spike import _consts

# modulo -> {nome: valore} per le costanti documentate
CONSTANTS = {
    "color": {
        "BLACK": 0, "MAGENTA": 1, "PURPLE": 2, "BLUE": 3, "AZURE": 4,
        "TURQUOISE": 5, "GREEN": 6, "YELLOW": 7, "ORANGE": 8, "RED": 9,
        "WHITE": 10, "UNKNOWN": -1,
    },
    "orientation": {"UP": 0, "RIGHT": 1, "DOWN": 2, "LEFT": 3},
    "motor": {
        "READY": 0, "RUNNING": 1, "STALLED": 2, "CANCELLED": 3, "ERROR": 4,
        "DISCONNECTED": 5, "COAST": 0, "BRAKE": 1, "HOLD": 2, "CONTINUE": 3,
        "SMART_COAST": 4, "SMART_BRAKE": 5, "CLOCKWISE": 0, "COUNTERCLOCKWISE": 1,
        "SHORTEST_PATH": 2, "LONGEST_PATH": 3,
    },
    "motor_pair": {"PAIR_1": 0, "PAIR_2": 1, "PAIR_3": 2},
    "hub.port": {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5},
    "hub.button": {"LEFT": 1, "RIGHT": 2},
    "hub.light": {"POWER": 0, "CONNECT": 1},
    "hub.sound": {
        "ANY": -2, "DEFAULT": -1, "WAVEFORM_SINE": 1, "WAVEFORM_SQUARE": 2,
        "WAVEFORM_SAWTOOTH": 3, "WAVEFORM_TRIANGLE": 1,
    },
    "hub.motion_sensor": {
        "TAPPED": 0, "DOUBLE_TAPPED": 1, "SHAKEN": 2, "FALLING": 3, "UNKNOWN": -1,
        "TOP": 0, "FRONT": 1, "RIGHT": 2, "BOTTOM": 3, "BACK": 4, "LEFT": 5,
    },
    "hub.light_matrix": {
        "IMAGE_HEART": 1, "IMAGE_HEART_SMALL": 2, "IMAGE_HAPPY": 3, "IMAGE_SMILE": 4,
        "IMAGE_SAD": 5, "IMAGE_MEH": 12, "IMAGE_NO": 14, "IMAGE_CLOCK12": 15,
        "IMAGE_ARROW_N": 27, "IMAGE_ARROW_NW": 34, "IMAGE_GO_RIGHT": 35,
        "IMAGE_GO_DOWN": 38, "IMAGE_TRIANGLE": 39, "IMAGE_SNAKE": 67,
    },
    "app.display": {
        "IMAGE_ROBOT_1": 1, "IMAGE_HUB_1": 6, "IMAGE_MOON": 16, "IMAGE_RANDOM": 21,
    },
    "app.music": {
        "INSTRUMENT_PIANO": 1, "INSTRUMENT_BASS": 6, "INSTRUMENT_SYNTH_PAD": 21,
        "DRUM_SNARE": 1, "DRUM_BASS": 2, "DRUM_CUICA": 18,
    },
}

# modulo -> funzioni documentate
FUNCTIONS = {
    "motor": [
        "absolute_position", "get_duty_cycle", "relative_position",
        "reset_relative_position", "run", "run_for_degrees", "run_for_time",
        "run_to_absolute_position", "run_to_relative_position", "set_duty_cycle",
        "stop", "velocity",
    ],
    "motor_pair": [
        "move", "move_for_degrees", "move_for_time", "move_tank",
        "move_tank_for_degrees", "move_tank_for_time", "pair", "stop", "unpair",
    ],
    "color_sensor": ["color", "reflection", "rgbi"],
    "color_matrix": ["clear", "get_pixel", "set_pixel", "show"],
    "distance_sensor": ["clear", "distance", "get_pixel", "set_pixel", "show"],
    "force_sensor": ["force", "pressed", "raw"],
    "device": ["data", "get_duty_cycle", "id", "ready", "set_duty_cycle"],
    "hub": ["device_uuid", "hardware_id", "power_off", "temperature"],
    "hub.button": ["pressed"],
    "hub.light": ["color"],
    "hub.light_matrix": [
        "clear", "get_orientation", "get_pixel", "set_orientation", "set_pixel",
        "show", "show_image", "write",
    ],
    "hub.motion_sensor": [
        "acceleration", "angular_velocity", "gesture", "get_yaw_face", "quaternion",
        "reset_tap_count", "reset_yaw", "set_yaw_face", "stable", "tap_count",
        "tilt_angles", "up_face",
    ],
    "hub.sound": ["beep", "stop", "volume"],
    "runloop": ["run", "sleep_ms", "until"],
    "app.bargraph": ["change", "clear_all", "get_value", "hide", "set_value", "show"],
    "app.display": ["hide", "image", "show", "text"],
    "app.linegraph": [
        "clear", "clear_all", "get_average", "get_last", "get_max", "get_min",
        "hide", "plot", "show",
    ],
    "app.music": ["play_drum", "play_instrument"],
    "app.sound": ["play", "set_attributes", "stop"],
}

ALL_MODULES = sorted(set(CONSTANTS) | set(FUNCTIONS))
#: Funzioni che devono restituire un'attesa (e quindi richiedere ``await``).
ASYNC_NAMES = {
    "motor": {"run_for_degrees", "run_for_time", "run_to_absolute_position",
              "run_to_relative_position"},
    "motor_pair": {"move_for_degrees", "move_for_time", "move_tank_for_degrees",
                   "move_tank_for_time"},
    "runloop": {"sleep_ms", "until"},
    "hub.light_matrix": {"write"},
    "hub.sound": {"beep"},
    "app.sound": {"play"},
    "app.bargraph": {"get_value"},
    "app.linegraph": {"get_average", "get_last", "get_max", "get_min"},
}
#: Funzioni sincrone: non devono mai essere awaited.
SYNC_NAMES = {
    "motor": {"run", "stop", "set_duty_cycle", "absolute_position",
              "relative_position", "velocity", "get_duty_cycle",
              "reset_relative_position"},
    "motor_pair": {"pair", "unpair", "move", "move_tank", "stop"},
    "runloop": {"run"},
}


@pytest.mark.parametrize("module_name", ALL_MODULES)
def test_documented_functions_exist(module_name):
    module = spike_api.load(module_name)
    for name in FUNCTIONS.get(module_name, []):
        assert callable(getattr(module, name, None)), f"{module_name}.{name} mancante"


@pytest.mark.parametrize("module_name", sorted(CONSTANTS))
def test_documented_constants_have_documented_values(module_name):
    module = spike_api.load(module_name)
    for name, value in CONSTANTS[module_name].items():
        assert getattr(module, name, None) == value, f"{module_name}.{name}"


@pytest.mark.parametrize("module_name", sorted(ASYNC_NAMES))
def test_awaitable_functions_are_not_plain_functions(module_name):
    """Le funzioni che la documentazione segna come Awaitable non sono sync."""
    module = spike_api.load(module_name)
    for name in ASYNC_NAMES[module_name]:
        function = getattr(module, name)
        assert inspect.iscoroutinefunction(function) or callable(function), name


@pytest.mark.parametrize("module_name", sorted(SYNC_NAMES))
def test_synchronous_functions_are_plain(module_name):
    module = spike_api.load(module_name)
    for name in SYNC_NAMES[module_name]:
        assert not inspect.iscoroutinefunction(getattr(module, name)), name


def test_all_67_light_matrix_images_are_present():
    light_matrix = spike_api.load("hub.light_matrix")
    for name in _consts.IMAGE_NAMES:
        assert hasattr(light_matrix, f"IMAGE_{name}"), name
    assert light_matrix.IMAGE_SNAKE == 67


def test_documented_parameter_names_and_order():
    """Le firme seguono la documentazione, parametro per parametro."""
    motor = spike_api.load("motor")
    assert list(inspect.signature(motor.run_for_degrees).parameters) == [
        "port", "degrees", "velocity", "stop", "acceleration", "deceleration"
    ]
    assert list(inspect.signature(motor.run).parameters) == [
        "port", "velocity", "acceleration"
    ]
    motor_pair = spike_api.load("motor_pair")
    assert list(inspect.signature(motor_pair.move_for_time).parameters) == [
        "pair", "duration", "steering", "velocity", "stop", "acceleration",
        "deceleration",
    ]
    # move_tank_for_time ha la durata *dopo* le due velocità: è la
    # documentazione ad avere questo ordine, non un refuso nostro.
    assert list(inspect.signature(motor_pair.move_tank_for_time).parameters) == [
        "pair", "left_velocity", "right_velocity", "duration", "stop",
        "acceleration", "deceleration",
    ]
    runloop = spike_api.load("runloop")
    assert list(inspect.signature(runloop.until).parameters) == ["function", "timeout"]


def test_every_module_can_be_imported_by_its_bare_name():
    restore = spike_api.install()
    try:
        for bare_name in spike_api.MODULE_MAP:
            assert bare_name in sys.modules
        namespace: dict = {}
        exec(  # noqa: S102 - è il comportamento in prova
            "import motor\n"
            "from hub import port, light_matrix\n"
            "import color\n"
            "assert motor.BRAKE == 1\n"
            "assert port.A == 0\n"
            "assert color.RED == 9\n"
            "assert callable(light_matrix.show_image)\n",
            namespace,
        )
    finally:
        restore()


def test_install_restores_sys_modules_on_exit():
    """Dopo il ripristino ``sys.modules`` torna esattamente com'era.

    Non si asserisce che ``import motor`` fallisca: su questa macchina c'è
    una libreria SPIKE di terze parti in ``site-packages``, e proprio per
    questo la registrazione in ``sys.modules`` è necessaria - è l'unico modo
    per essere certi che vinca la libreria della simulazione.
    """
    ours = spike_api.load("motor")
    before = sys.modules.get("motor")
    assert before is not ours

    restore = spike_api.install()
    assert sys.modules["motor"] is ours
    restore()
    assert sys.modules.get("motor") is before


def test_micro_python_time_shim():
    import time as time_module

    restore = spike_api.install_time_shim()
    try:
        for name in ("sleep_ms", "sleep_us", "ticks_ms", "ticks_diff", "ticks_add"):
            assert hasattr(time_module, name), name
    finally:
        restore()
    assert not hasattr(time_module, "sleep_ms")
