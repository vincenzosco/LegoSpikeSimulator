"""Analisi statica del programma utente, prima di eseguirlo.

I controlli statici servono a dire *prima* cosa non torna (nome sbagliato,
`await` dimenticato, porta vuota) così l'utente non deve dedurlo da un
movimento che non avviene.
"""

from __future__ import annotations

import textwrap

from spikesim.checker import check_source, check_text
from spikesim.config import COLOR_SENSOR, PORT_C, default_config


def check(source: str, config=None):
    return check_text(textwrap.dedent(source).lstrip("\n"), "programma.py", config)


def codes(diagnostics):
    return [d.code for d in diagnostics]


def test_correct_program_is_clean():
    diagnostics = check(
        """
        import motor, runloop
        from hub import port

        async def main():
            await motor.run_for_degrees(port.A, 360, 720)

        runloop.run(main())
        """
    )
    assert diagnostics == [], diagnostics


def test_syntax_error_is_reported_with_line_and_column():
    diagnostics = check(
        """
        import motor

        def rotto(:
            pass
        """
    )
    assert codes(diagnostics) == ["SYN001"]
    assert diagnostics[0].line == 3
    assert diagnostics[0].column is not None
    assert diagnostics[0].severity == "error"


def test_misspelled_module_suggests_the_right_one():
    diagnostics = check("import motr\n")
    assert codes(diagnostics) == ["SPIKE100"]
    assert "motor" in diagnostics[0].message
    assert diagnostics[0].line == 1


def test_ordinary_library_imports_are_not_flagged():
    assert check("import json\nimport math\nimport random\n") == []


def test_unknown_function_on_a_spike_module():
    diagnostics = check(
        """
        import motor
        from hub import port

        motor.runn(port.A, 500)
        """
    )
    assert codes(diagnostics) == ["SPIKE101"]
    assert "run_for_degrees" in diagnostics[0].message or "run" in diagnostics[0].message
    assert diagnostics[0].line == 4


def test_unknown_color_constant():
    diagnostics = check(
        """
        import color
        from hub import light

        light.color(light.POWER, color.PINK)
        """
    )
    assert codes(diagnostics) == ["SPIKE101"]
    assert diagnostics[0].line == 4


def test_unknown_port_constant():
    diagnostics = check("from hub import port\n\nmotor_port = port.G\n")
    assert codes(diagnostics) == ["SPIKE101"]


def test_awaitable_call_without_await_is_flagged():
    diagnostics = check(
        """
        import motor, runloop
        from hub import port

        async def main():
            motor.run_for_degrees(port.A, 360, 720)

        runloop.run(main())
        """
    )
    assert codes(diagnostics) == ["SPIKE102"]
    assert diagnostics[0].line == 5
    assert diagnostics[0].severity == "warning"


def test_awaited_call_is_not_flagged():
    diagnostics = check(
        """
        import motor, runloop
        from hub import port

        async def main():
            await motor.run_for_degrees(port.A, 360, 720)

        runloop.run(main())
        """
    )
    assert diagnostics == []


def test_runloop_run_without_call_parentheses():
    diagnostics = check(
        """
        import runloop

        async def main():
            await runloop.sleep_ms(100)

        runloop.run(main)
        """
    )
    assert "SPIKE103" in codes(diagnostics)
    assert diagnostics[0].line == 6


def test_async_function_defined_but_never_started():
    diagnostics = check(
        """
        import runloop

        async def main():
            await runloop.sleep_ms(100)
        """
    )
    assert codes(diagnostics) == ["SPIKE104"]
    assert "runloop.run" in diagnostics[0].message


def test_motor_pair_used_without_pairing():
    diagnostics = check(
        """
        import motor_pair, runloop

        async def main():
            await motor_pair.move_for_degrees(motor_pair.PAIR_1, 360, 0)

        runloop.run(main())
        """
    )
    assert codes(diagnostics) == ["SPIKE105"]
    assert diagnostics[0].line == 4


def test_pairing_first_removes_the_warning():
    diagnostics = check(
        """
        import motor_pair, runloop
        from hub import port

        async def main():
            motor_pair.pair(motor_pair.PAIR_1, port.A, port.B)
            await motor_pair.move_for_degrees(motor_pair.PAIR_1, 360, 0)

        runloop.run(main())
        """
    )
    assert diagnostics == []


def test_motor_command_on_a_port_with_no_motor():
    diagnostics = check(
        """
        import motor
        from hub import port

        motor.run(port.C, 500)
        """
    )
    assert codes(diagnostics) == ["SPIKE106"]
    assert "C" in diagnostics[0].message
    assert diagnostics[0].line == 4


def test_sensor_read_on_a_port_with_no_sensor():
    diagnostics = check(
        """
        import color_sensor
        from hub import port

        print(color_sensor.color(port.D))
        """
    )
    assert codes(diagnostics) == ["SPIKE106"]
    assert "D" in diagnostics[0].message


def test_port_check_uses_the_configured_hardware():
    config = default_config().with_port(PORT_C, COLOR_SENSOR)
    diagnostics = check(
        """
        import color_sensor
        from hub import port

        print(color_sensor.color(port.C))
        """,
        config,
    )
    assert diagnostics == []


def test_check_source_reads_a_file(tmp_path):
    program = tmp_path / "p.py"
    program.write_text("import motr\n", encoding="utf-8")
    diagnostics = check_source(str(program))
    assert codes(diagnostics) == ["SPIKE100"]


def test_check_source_on_a_missing_file_is_reported_not_raised(tmp_path):
    diagnostics = check_source(str(tmp_path / "non_esiste.py"))
    assert codes(diagnostics) == ["SYN002"]
