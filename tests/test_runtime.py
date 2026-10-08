"""Orologio virtuale, fisica e diagnostica dei programmi eseguiti.

Qui si eseguono programmi SPIKE veri e si controlla *cosa succede*: dove
arriva il robot, quanto tempo simulato passa, quali problemi vengono
segnalati e su quale riga.
"""

from __future__ import annotations

import math
from dataclasses import replace

import pytest

from spikesim.config import COLOR_SENSOR, PORT_C, default_config
from spikesim.runtime import PHYSICS_STEP_MS

WHEEL_MM_PER_TURN = math.pi * 56.0  # ruota da 56 mm di diametro


def _codes(result):
    return [diagnostic.code for diagnostic in result.trace.diagnostics]


def _lines(result, code):
    return [
        diagnostic.line
        for diagnostic in result.trace.diagnostics
        if diagnostic.code == code
    ]


def _messages(result):
    return " | ".join(d.message for d in result.trace.diagnostics)


# --- movimento -------------------------------------------------------------


def test_move_for_degrees_drives_the_base_straight(run_source):
    result = run_source(
        """
        import motor_pair
        from hub import port
        import runloop

        async def main():
            motor_pair.pair(motor_pair.PAIR_1, port.A, port.B)
            await motor_pair.move_for_degrees(motor_pair.PAIR_1, 360, 0, velocity=360)

        runloop.run(main())
        """
    )
    trace = result.trace
    assert trace.ok, _messages(result)
    # 360 gradi di ruota = una circonferenza completa della ruota.
    assert trace.poses[-1][1] == pytest.approx(WHEEL_MM_PER_TURN, rel=1e-6)
    assert trace.poses[-1][2] == pytest.approx(0.0, abs=1e-6)
    assert trace.poses[-1][3] == pytest.approx(0.0, abs=1e-6)
    assert trace.duration_ms == pytest.approx(1000, abs=5)


def test_single_motor_on_a_drive_wheel_pivots_the_robot(run_source):
    """Il motore A è la ruota sinistra del drive base: girando, il robot ruota."""
    result = run_source(
        """
        import motor
        from hub import port
        import runloop

        async def main():
            await motor.run_for_degrees(port.A, 360, 720)

        runloop.run(main())
        """
    )
    trace = result.trace
    assert trace.ok, _messages(result)
    # Ruota sinistra a 351.86 mm/s, destra ferma: omega = -pi rad/s per 0.5 s.
    assert trace.poses[-1][3] == pytest.approx(-90.0, abs=0.01)


def test_motor_on_a_non_drive_port_does_not_move_the_robot(run_source):
    config = default_config().with_port(PORT_C, "motor_medium")
    result = run_source(
        """
        import motor
        from hub import port
        import runloop

        async def main():
            await motor.run_for_degrees(port.C, 360, 720)

        runloop.run(main())
        """,
        config,
    )
    trace = result.trace
    assert trace.ok, _messages(result)
    assert trace.poses[-1][1] == pytest.approx(0.0, abs=1e-9)
    assert trace.poses[-1][3] == pytest.approx(0.0, abs=1e-9)


def test_tank_move_for_degrees_spins_in_place(run_source):
    result = run_source(
        """
        import motor_pair
        from hub import port
        import runloop

        async def main():
            motor_pair.pair(motor_pair.PAIR_1, port.A, port.B)
            await motor_pair.move_tank_for_degrees(motor_pair.PAIR_1, 360, 500, -500)

        runloop.run(main())
        """,
    )
    trace = result.trace
    assert trace.ok, _messages(result)
    # Ruote opposte: il centro non si sposta, l'orientamento sì.
    assert trace.poses[-1][1] == pytest.approx(0.0, abs=1e-6)
    assert abs(trace.poses[-1][3]) > 90.0


def test_top_level_sleep_advances_the_robot(run_source):
    """Senza runloop: ``time.sleep_ms`` fa avanzare il tempo simulato."""
    result = run_source(
        """
        import motor
        import time
        from hub import port

        motor.run(port.A, 360)
        time.sleep_ms(1000)
        motor.stop(port.A)
        """
    )
    trace = result.trace
    assert trace.ok, _messages(result)
    assert trace.duration_ms == pytest.approx(1000, abs=5)
    assert trace.poses[-1][3] == pytest.approx(-90.0, abs=0.01)


def test_full_lock_steering_is_not_reported_as_a_stall(run_source):
    """Con sterzo 100 la ruota destra è ferma per progetto, non bloccata."""
    result = run_source(
        """
        import motor_pair, runloop
        from hub import port

        async def main():
            motor_pair.pair(motor_pair.PAIR_1, port.A, port.B)
            await motor_pair.move_for_degrees(motor_pair.PAIR_1, 360, 100)

        runloop.run(main())
        """
    )
    trace = result.trace
    assert "SPIKE019" not in _codes(result), _messages(result)
    assert trace.ok, _messages(result)
    # Ruota destra ferma e sinistra al doppio: il robot ruota attorno alla
    # ruota destra, quindi il *centro* percorre un arco di raggio pari a metà
    # carreggiata (56 mm) e chiude a -90 gradi.
    assert trace.poses[-1][3] == pytest.approx(-90.0, abs=0.5)
    assert trace.poses[-1][1] == pytest.approx(56.0, abs=1.0)
    assert trace.poses[-1][2] == pytest.approx(-56.0, abs=1.0)


def test_zero_degree_move_is_not_reported_as_a_stall(run_source):
    result = run_source(
        """
        import motor, runloop
        from hub import port

        async def main():
            await motor.run_for_degrees(port.A, 0, 720)

        runloop.run(main())
        """
    )
    assert "SPIKE019" not in _codes(result), _messages(result)
    assert result.trace.poses[-1][3] == pytest.approx(0.0, abs=1e-9)


def test_pose_samples_are_dense_enough_for_animation(run_source):
    result = run_source(
        """
        import motor, time
        from hub import port

        motor.run(port.A, 360)
        time.sleep_ms(500)
        """
    )
    samples = result.trace.poses
    assert len(samples) >= 500 / (default_config().sample_interval_ms + 1)
    assert samples[0][0] == 0
    gaps = [b[0] - a[0] for a, b in zip(samples, samples[1:])]
    assert max(gaps) <= default_config().sample_interval_ms + PHYSICS_STEP_MS


# --- scheduler -------------------------------------------------------------


def test_parallel_tasks_interleave_and_wait_for_the_longest(run_source):
    result = run_source(
        """
        import runloop

        async def breve():
            await runloop.sleep_ms(400)
            print("breve")

        async def lunga():
            await runloop.sleep_ms(1000)
            print("lunga")

        runloop.run(breve(), lunga())
        """
    )
    trace = result.trace
    assert trace.ok, _messages(result)
    assert trace.duration_ms == pytest.approx(1000, abs=1)
    prints = [event for event in trace.events if event.type == "print"]
    assert [event.data["text"] for event in prints] == ["breve", "lunga"]
    assert prints[0].t == pytest.approx(400, abs=1)
    assert prints[1].t == pytest.approx(1000, abs=1)


def test_until_waits_for_the_predicate(run_source):
    result = run_source(
        """
        import motor, runloop
        import motor_pair
        from hub import port, motion_sensor

        async def main():
            motor_pair.pair(motor_pair.PAIR_1, port.A, port.B)
            motor_pair.move(motor_pair.PAIR_1, 100, velocity=360)
            await runloop.until(lambda: abs(motion_sensor.tilt_angles()[0]) >= 900)
            motor_pair.stop(motor_pair.PAIR_1)

        runloop.run(main())
        """
    )
    trace = result.trace
    assert trace.ok, _messages(result)
    assert abs(trace.poses[-1][3]) >= 89.0


def test_until_timeout_gives_control_back(run_source):
    result = run_source(
        """
        import runloop

        async def main():
            await runloop.until(lambda: False, timeout=300)
            print("scaduto")

        runloop.run(main())
        """
    )
    trace = result.trace
    assert trace.ok, _messages(result)
    assert trace.duration_ms == pytest.approx(300, abs=15)


# --- diagnostica -----------------------------------------------------------


def test_unawaited_motor_command_is_reported_with_its_line(run_source):
    result = run_source(
        """
        import motor, runloop
        from hub import port

        async def main():
            motor.run_for_degrees(port.A, 360, 720)

        runloop.run(main())
        """
    )
    trace = result.trace
    assert "SPIKE020" in _codes(result)
    assert _lines(result, "SPIKE020") == [5]
    # Senza await il motore non si è mai mosso.
    assert trace.poses[-1][3] == pytest.approx(0.0, abs=1e-9)


def test_motor_on_an_empty_port_is_an_error_with_its_line(run_source):
    result = run_source(
        """
        import motor, runloop
        from hub import port

        async def main():
            await motor.run_for_degrees(port.C, 360, 720)

        runloop.run(main())
        """
    )
    trace = result.trace
    assert not trace.ok
    assert "SPIKE012" in _codes(result)
    assert _lines(result, "SPIKE012") == [5]
    assert not trace.terminated


def test_velocity_out_of_range_is_clamped_with_a_warning(run_source):
    result = run_source(
        """
        import motor
        from hub import port

        motor.run(port.A, 5000)
        motor.stop(port.A)
        """
    )
    assert "SPIKE033" in _codes(result)
    assert _lines(result, "SPIKE033") == [4]


def test_using_a_motor_pair_without_pairing_is_an_error(run_source):
    result = run_source(
        """
        import motor_pair, runloop

        async def main():
            motor_pair.move(motor_pair.PAIR_1, 0)

        runloop.run(main())
        """
    )
    assert "SPIKE013" in _codes(result)
    assert _lines(result, "SPIKE013") == [4]


def test_sensor_read_on_a_port_without_the_sensor_is_an_error(run_source):
    result = run_source(
        """
        import color_sensor
        from hub import port

        print(color_sensor.color(port.C))
        """
    )
    assert "SPIKE011" in _codes(result)
    assert _lines(result, "SPIKE011") == [4]


def test_configured_sensor_values_are_returned(run_source):
    config = default_config().with_port(PORT_C, COLOR_SENSOR)
    config = config.with_sensors(color=9, reflection=42)
    result = run_source(
        """
        import color_sensor, color
        from hub import port

        print(color_sensor.color(port.C) == color.RED)
        print(color_sensor.reflection(port.C))
        """,
        config,
    )
    assert result.trace.ok, _messages(result)
    text = [event.data["text"] for event in result.trace.events if event.type == "print"]
    assert text == ["True", "42"]


def test_python_exception_is_reported_with_the_user_line(run_source):
    result = run_source(
        """
        import runloop

        async def main():
            valori = [1, 2]
            print(valori[5])

        runloop.run(main())
        """
    )
    trace = result.trace
    assert not trace.ok
    assert not trace.terminated
    error = [d for d in trace.diagnostics if d.severity == "error"][0]
    assert error.line == 5
    assert "IndexError" in error.message


def test_syntax_error_is_reported_with_line_and_column(run_source):
    result = run_source(
        """
        import motor

        def rotto(:
            pass
        """
    )
    trace = result.trace
    assert not trace.ok
    error = trace.diagnostics[0]
    assert "SyntaxError" in error.message
    assert error.line == 3
    assert error.column is not None


# --- limiti ----------------------------------------------------------------


def test_endless_runloop_is_stopped_at_the_time_limit(run_source):
    result = run_source(
        """
        import runloop

        async def main():
            while True:
                await runloop.sleep_ms(500)

        runloop.run(main())
        """,
        replace(default_config(), max_sim_time_ms=2000),
    )
    trace = result.trace
    assert "SPIKE016" in _codes(result)
    assert not trace.terminated
    assert trace.duration_ms >= 1


def test_endless_python_loop_is_stopped_by_the_watchdog(run_source):
    result = run_source(
        """
        while True:
            pass
        """,
        replace(default_config(), max_wall_seconds=0.4),
    )
    trace = result.trace
    assert not trace.terminated
    assert trace.diagnostics, "il watchdog deve lasciare una diagnostica"
    assert "secondi reali" in trace.diagnostics[0].message


def test_program_that_forgets_runloop_still_reports_missing_await(run_source):
    result = run_source(
        """
        import motor
        from hub import port

        async def main():
            await motor.run_for_degrees(port.A, 360, 720)

        main()
        """
    )
    trace = result.trace
    # main() è una coroutine creata e mai avviata: il programma non ha fatto nulla.
    assert trace.duration_ms == 0
    assert "SPIKE020" in _codes(result)


def test_light_matrix_write_scrolls_and_takes_time(run_source):
    result = run_source(
        """
        import runloop
        from hub import light_matrix

        async def main():
            await light_matrix.write("CIAO", time_per_character=100)

        runloop.run(main())
        """
    )
    trace = result.trace
    assert trace.ok, _messages(result)
    assert trace.duration_ms > 0
    frames = [event for event in trace.events if event.type == "light_matrix"]
    assert len(frames) > 5
    assert any(sum(frame.data["pixels"]) > 0 for frame in frames)
