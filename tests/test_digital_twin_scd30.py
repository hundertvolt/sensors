"""Deterministic unit tests for digital_twin/_scd30_chip.py's transaction-response logic - matches the raw word-register
commands src/asy_scd30_driver.py's SCD30_I2C sends. Real-time RDY-pin scheduling is exercised only via the synchronous
_produce_new_reading() hook here; the real-time-firing check itself lives in test_digital_twin_machine.py."""

import asyncio
import errno
import json
import os
import struct
import sys

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable

    from asy_config_manager import CfgValue

sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

import _scd30_chip
import machine
import microtest
from _async_harness import cancel, run
from _crc8 import crc8, word
from _error_codes import code
from _fast_sleep import FastAsyncSleep
from _scd30_chip import SCD30Chip, SCD30Nvm
from _tmp_scratch import TmpScratch
from _twin_common import Walk
from _twin_devices import device_with, wiring_plan
from _twin_random import FixedRandom
from _write_counters import WriteCountingOpen

import asy_config_manager
import asy_i2c_driver
from asy_scd30_driver import SCD30_Reader

# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that module's
# own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage.
_scratch = TmpScratch("digital_twin_scd30")
microtest.after_each(machine.reset_test_state)
_SCD30_ADDRESS = 0x61  # Interface Description 1.1.1


def _get(chip: SCD30Chip, reg_hi: int, reg_lo: int, nbytes: int = 3) -> bytes:
    chip.handle_writeto(bytes([reg_hi, reg_lo]))
    return chip.handle_readfrom_into(nbytes)


def _reader_on_the_twin_bus(cfg_path: str) -> "tuple[SCD30_Reader, SCD30Chip]":
    # The real reader on the bus a generated device wires its SCD30 on, built as that device's plan describes it; the
    # chip's own measurement Timer is stopped, so each test produces the measurements it reads.
    plan = wiring_plan(device_with("scd30"))
    machine.reset_peripherals()
    machine.configure_wiring(plan)
    bus, attachment = next((name, a) for name, attached in plan["buses"].items() for a in attached if a["driver"] == "scd30")
    pins = plan["pins"][bus]
    scl, sda = pins.get("scl"), pins.get("sda")
    assert isinstance(scl, int)
    assert isinstance(sda, int)
    i2c = asy_i2c_driver.I2C(int(bus[3:]), scl_pin=scl, sda_pin=sda, frequency=50000)
    reader = SCD30_Reader(i2c, irq_pin=attachment["irq_pin"], cfg_path=cfg_path)
    found = machine.peripheral(bus)
    assert isinstance(found, machine.I2C)
    chip = found.devices[_SCD30_ADDRESS]
    assert isinstance(chip, SCD30Chip)
    assert chip._timer is not None
    chip._timer.deinit()
    chip._timer = None  # an interval write must not re-arm it
    return reader, chip


def _reported_temperature(chip: SCD30Chip) -> float:
    # The temperature word of the measurement the driver reads (its own unpack of bytes 6-11).
    chip.handle_writeto(b"\x03\x00")
    raw = chip.handle_readfrom_into(18)
    return float(struct.unpack(">f", raw[6:8] + raw[9:11])[0])


def _set(chip: SCD30Chip, reg_hi: int, reg_lo: int, arg: int) -> None:
    payload = bytes([reg_hi, reg_lo, (arg >> 8) & 0xFF, arg & 0xFF])
    chip.handle_writeto(payload + bytes([crc8(payload[2:4])]))


def _tmp_path(name: str) -> str:
    return _scratch.path(name)


class _LevelPin:
    # Stand-in for machine.py's Pin: only simulate_edge() is called on the RDY pin; `edges` records each level change.
    def __init__(self) -> None:
        self.level = 0
        self.edges: list[int] = []

    def simulate_edge(self, new_value: int) -> None:
        level = 1 if new_value else 0
        if level != self.level:
            self.edges.append(level)
        self.level = level


class _RecordingTimer:
    # Stand-in for the simulation Timer a timer_factory builds: records the period of every init().
    PERIODIC = 1

    def __init__(self, periods: "list[int]") -> None:
        self._periods = periods

    def init(self, *, period: int, mode: int, callback: object) -> None:
        assert mode == self.PERIODIC
        assert callable(callback)
        self._periods.append(period)


class _PrintRecorder:
    # Shadows print() inside _scd30_chip only, recording each line's arguments; leaving the block removes the shadow.
    def __enter__(self) -> "list[tuple[object, ...]]":
        lines: list[tuple[object, ...]] = []
        _scd30_chip.print = lambda *args: lines.append(args)  # type: ignore[attr-defined]  # a module-global shadow of the builtin
        return lines

    def __exit__(self, *_exc_info: object) -> None:
        del _scd30_chip.print  # type: ignore[attr-defined]


def test_measurement_interval_set_then_get_round_trips() -> None:
    chip = SCD30Chip()
    _set(chip, 0x46, 0x00, 5)
    reply = _get(chip, 0x46, 0x00)
    assert reply == word(5)


def test_self_calibration_enabled_set_then_get_round_trips() -> None:
    chip = SCD30Chip()
    _set(chip, 0x53, 0x06, 1)
    assert _get(chip, 0x53, 0x06) == word(1)
    _set(chip, 0x53, 0x06, 0)
    assert _get(chip, 0x53, 0x06) == word(0)


def test_ambient_pressure_set_then_get_round_trips() -> None:
    chip = SCD30Chip()
    _set(chip, 0x00, 0x10, 1013)
    assert _get(chip, 0x00, 0x10) == word(1013)


def test_altitude_set_then_get_round_trips() -> None:
    chip = SCD30Chip()
    _set(chip, 0x51, 0x02, 250)
    assert _get(chip, 0x51, 0x02) == word(250)


def test_a_soft_reset_drops_the_unread_measurement_and_the_frc_reference() -> None:
    # "the same state as after powering up" (Interface Description 1.4.10): data-ready 0, FRC back at 400.
    chip = SCD30Chip(random_source=FixedRandom())
    _set(chip, 0x52, 0x04, 900)
    chip._produce_new_reading()
    chip.handle_writeto(bytes([0xD3, 0x04]))  # SOFT_RESET
    assert _get(chip, 0x02, 0x02) == word(0)
    assert _get(chip, 0x52, 0x04) == word(400)


def test_read_firmware_version_reports_the_fixed_plausible_value() -> None:
    chip = SCD30Chip()
    assert _get(chip, 0xD1, 0x00) == word(0x0342)


def test_readfrom_into_with_an_unrecognized_last_command_returns_zero_bytes() -> None:
    chip = SCD30Chip()
    chip.handle_writeto(bytes([0xFF, 0xFF]))  # not a command this chip recognizes
    assert chip.handle_readfrom_into(3) == bytes(3)


def test_temperature_offset_set_then_get_round_trips_as_raw_centidegrees() -> None:
    chip = SCD30Chip()
    _set(chip, 0x54, 0x03, 150)  # driver sends offset*100
    assert _get(chip, 0x54, 0x03) == word(150)


def test_a_reading_reports_the_sensors_temperature_less_the_offset() -> None:
    for offset_raw in (0, 150, 65535):
        chip = SCD30Chip(random_source=FixedRandom(uniform_values=[500.0, 22.0, 45.0, 0.0, 0.0, 0.0]))
        _set(chip, 0x54, 0x03, offset_raw)
        chip._produce_new_reading()
        assert abs(_reported_temperature(chip) - (22.0 - offset_raw / 100)) < 1e-3, offset_raw


def test_the_forced_recalibration_reference_reads_back_the_last_one_until_a_power_up() -> None:
    # "The most recently used reference value is retained in volatile memory ... After repowering the sensor, the
    # command will return the standard reference value of 400 ppm" (Interface Description 1.4.6).
    path = _tmp_path("scd30_frc.json")
    chip = SCD30Chip(state_path=path)
    assert _get(chip, 0x52, 0x04) == word(400)
    _set(chip, 0x52, 0x04, 900)
    assert _get(chip, 0x52, 0x04) == word(900)
    chip.save_state()
    assert _get(SCD30Chip(state_path=path), 0x52, 0x04) == word(400)  # a new chip from the same state file
    chip.handle_writeto(bytes([0xD3, 0x04]))  # soft reset: as after powering up (1.4.10)
    assert _get(chip, 0x52, 0x04) == word(400)


def test_a_forced_recalibration_reference_outside_400_to_2000_is_ignored() -> None:
    chip = SCD30Chip()
    for ppm in (399, 2001):
        _set(chip, 0x52, 0x04, ppm)
        assert _get(chip, 0x52, 0x04) == word(400), ppm
    assert chip.nvm_writes == 0


def test_a_measurement_interval_outside_2_to_1800_is_ignored_and_arms_no_timer() -> None:
    built: list[int] = []
    chip = SCD30Chip(timer_factory=lambda: _RecordingTimer(built))  # type: ignore[arg-type, return-value]  # a recording stand-in
    for seconds in (0, 1, 1801):
        _set(chip, 0x46, 0x00, seconds)
        assert _get(chip, 0x46, 0x00) == word(2), seconds
    assert built == [2000]  # the power-up arm only: no 0 ms (or 1801 s) periodic Timer
    for seconds in (2, 1800):
        _set(chip, 0x46, 0x00, seconds)
        assert _get(chip, 0x46, 0x00) == word(seconds)
    assert built == [2000, 2000, 1800000]


def test_an_argument_with_a_wrong_crc_changes_nothing_and_is_counted() -> None:
    chip = SCD30Chip()
    payload = bytes([0x51, 0x02, 0x00, 0xFA])
    chip.handle_writeto(payload + bytes([crc8(payload[2:4]) ^ 0xFF]))
    assert _get(chip, 0x51, 0x02) == word(0)
    assert chip.bad_crc_commands == 1
    assert chip.nvm_writes == 0


def test_stop_ends_the_measurements_and_a_start_resumes_them() -> None:
    pin = _LevelPin()
    chip = SCD30Chip(rdy_pin=pin, random_source=FixedRandom())
    chip.handle_writeto(bytes([0x01, 0x04]))  # stop continuous measurement (1.4.2)
    for _ in range(3):  # three intervals: no measurement, no RDY edge
        chip._produce_new_reading()
        assert pin.edges == []
    assert _get(chip, 0x02, 0x02) == word(0)
    _set(chip, 0x00, 0x10, 0)  # start continuous measurement, no pressure compensation (1.4.1)
    chip._produce_new_reading()
    assert pin.edges == [1]
    assert _get(chip, 0x02, 0x02) == word(1)


def test_an_unprovisioned_chip_measures_nothing_until_started() -> None:
    chip = SCD30Chip(nvm=SCD30Nvm(2, False), random_source=FixedRandom())
    chip._produce_new_reading()
    assert _get(chip, 0x02, 0x02) == word(0)
    _set(chip, 0x00, 0x10, 0)
    chip._produce_new_reading()
    assert _get(chip, 0x02, 0x02) == word(1)


def test_data_ready_starts_false() -> None:
    chip = SCD30Chip()
    assert _get(chip, 0x02, 0x02) == word(0)


def test_produce_new_reading_sets_data_ready_true() -> None:
    chip = SCD30Chip(random_source=FixedRandom(uniform_values=[500.0, 22.0, 45.0, 0.0, 0.0, 0.0]))
    chip._produce_new_reading()
    assert _get(chip, 0x02, 0x02) == word(1)


def test_read_measurement_returns_crc_valid_buffer_decoding_to_the_produced_values() -> None:
    # First 3 values: the uniform draw at construction. Last 3: the step delta _produce_new_reading() draws,
    # zeroed here so the final value stays exactly at the constructed initial value, keeping this test's
    # assertions about the values independent of the walk mechanism, which has its own tests below.
    chip = SCD30Chip(random_source=FixedRandom(uniform_values=[512.5, 21.5, 47.25, 0.0, 0.0, 0.0]))
    chip._produce_new_reading()
    chip.handle_writeto(b"\x03\x00")  # READ_MEASUREMENT - bare command, no args
    buf = chip.handle_readfrom_into(18)
    assert len(buf) == 18
    for i in range(0, 18, 3):
        assert buf[i + 2] == crc8(buf[i : i + 2])
    co2 = struct.unpack(">f", buf[0:2] + buf[3:5])[0]
    temp = struct.unpack(">f", buf[6:8] + buf[9:11])[0]
    hum = struct.unpack(">f", buf[12:14] + buf[15:17])[0]
    assert co2 == 512.5
    assert temp == 21.5
    assert hum == 47.25


def test_read_measurement_clears_data_ready() -> None:
    chip = SCD30Chip(random_source=FixedRandom(uniform_values=[500.0, 22.0, 45.0, 0.0, 0.0, 0.0]))
    chip._produce_new_reading()
    chip.handle_writeto(b"\x03\x00")
    chip.handle_readfrom_into(18)
    assert _get(chip, 0x02, 0x02) == word(0)  # cleared the instant it was read (Interface Description 1.4.4)


def test_construction_draws_an_initial_value_within_range_without_needing_a_reading_produced() -> None:
    # Initial value: a uniform draw within [min,max] at construction, before _produce_new_reading()
    # is ever called - not datasheet-derived (the step bound isn't), but the initial-value mechanism
    # (a uniform draw) is unchanged from before this walk existed.
    chip = SCD30Chip(random_source=FixedRandom(uniform_values=[1234.0, 25.5, 55.5]))
    assert chip._co2 == 1234.0
    assert chip._temp == 25.5
    assert chip._hum == 55.5


def test_produce_new_reading_steps_from_the_previous_value_rather_than_a_fresh_draw() -> None:
    chip = SCD30Chip(random_source=FixedRandom(uniform_values=[1000.0, 20.0, 50.0, 25.0, -0.5, 2.0]))
    assert chip._co2 == 1000.0 and chip._temp == 20.0 and chip._hum == 50.0  # construction draw
    chip._produce_new_reading()
    assert chip._co2 == 1025.0  # 1000.0 + 25.0
    assert chip._temp == 19.5  # 20.0 + -0.5
    assert chip._hum == 52.0  # 50.0 + 2.0


def test_produce_new_reading_step_delta_is_clamped_to_the_default_step_bound() -> None:
    # _FixedRandom itself asserts a <= value <= b for every uniform() call - if _produce_new_reading()
    # ever passed the wrong (a, b) bound for a step draw (e.g. the full [min,max] range instead of
    # [-step,step]), this test's deliberately-tight scripted delta would fail that assertion.
    chip = SCD30Chip(random_source=FixedRandom(uniform_values=[1000.0, 20.0, 50.0, 50.0, 1.0, 3.0]))
    chip._produce_new_reading()  # walk steps co2 50.0, temp 1.0, hum 3.0 (this chip's defaults)


def test_produce_new_reading_step_is_clamped_to_the_configured_max() -> None:
    chip = SCD30Chip(
        co2=Walk(400.0, 2000.0, 50.0),
        random_source=FixedRandom(uniform_values=[1980.0, 20.0, 50.0, 50.0, 0.0, 0.0]),
    )
    chip._produce_new_reading()
    assert chip._co2 == 2000.0  # 1980.0 + 50.0 would be 2030.0 - clamped back to the co2 walk's hi


def test_produce_new_reading_step_is_clamped_to_the_configured_min() -> None:
    chip = SCD30Chip(
        temp=Walk(15.0, 30.0, 1.0),
        random_source=FixedRandom(uniform_values=[1000.0, 15.5, 50.0, 0.0, -1.0, 0.0]),
    )
    chip._produce_new_reading()
    assert chip._temp == 15.0  # 15.5 + -1.0 would be 14.5 - clamped back to the temp walk's lo


def test_step_bounds_are_configurable_via_the_constructor() -> None:
    random = FixedRandom(uniform_values=[1000.0, 20.0, 50.0, 5.0, 0.1, 0.5])
    chip = SCD30Chip(co2=Walk(400.0, 2000.0, 5.0), temp=Walk(15.0, 30.0, 0.1), hum=Walk(20.0, 70.0, 0.5), random_source=random)
    chip._produce_new_reading()
    assert random.calls[3:6] == [(-5.0, 5.0), (-0.1, 0.1), (-0.5, 0.5)], random.calls  # the step draws take the walks' own steps


def test_corrupt_next_stays_orthogonal_to_the_walk() -> None:
    # The fault-injection flag corrupts whatever the walk just produced - it doesn't interact with
    # the walk mechanism itself.
    chip = SCD30Chip(random_source=FixedRandom(uniform_values=[1000.0, 20.0, 50.0, 0.0, 0.0, 0.0]))
    chip._produce_new_reading()
    chip.corrupt_next()
    chip.handle_writeto(b"\x03\x00")
    buf = chip.handle_readfrom_into(18)
    assert buf[2] != crc8(buf[0:2])
    co2 = struct.unpack(">f", buf[0:2] + buf[3:5])[0]
    assert co2 == 1000.0  # the underlying walked value is unaffected by the corruption


def test_default_ranges_stay_inside_the_datasheets_own_documented_ranges() -> None:
    # 400-10 000 ppm, 0-100 %RH, -40-70 C (SCD30 datasheet Tables 1-3): the walks are sub-ranges.
    chip = SCD30Chip()
    assert chip.co2.lo >= 400 and chip.co2.hi <= 10000
    assert chip.hum.lo >= 0 and chip.hum.hi <= 100
    assert chip.temp.lo >= -40 and chip.temp.hi <= 70


def test_rdy_pin_goes_high_on_new_reading_and_fires_a_registered_rising_edge_handler() -> None:
    fired: list[int | None] = []

    class _FakePin:
        IRQ_RISING = 0x08
        IRQ_FALLING = 0x04

        def __init__(self) -> None:
            self._value = 0
            self._handler: Callable[[_FakePin], None] | None = None
            self._trigger = self.IRQ_RISING | self.IRQ_FALLING

        def irq(self, handler: "Callable[[_FakePin], None] | None" = None, trigger: int = IRQ_RISING | IRQ_FALLING, *, _hard: bool = False) -> None:
            self._handler = handler
            self._trigger = trigger

        def simulate_edge(self, new_value: int) -> None:
            old = self._value
            self._value = 1 if new_value else 0
            rising = old == 0 and self._value == 1
            if rising and (self._trigger & self.IRQ_RISING) and self._handler is not None:
                self._handler(self)

        def value(self, x: "int | None" = None) -> "int | None":
            if x is None:
                return self._value
            self._value = 1 if x else 0
            return None

    pin = _FakePin()
    pin.irq(handler=lambda p: fired.append(p.value()), trigger=pin.IRQ_RISING)
    chip = SCD30Chip(rdy_pin=pin, random_source=FixedRandom(uniform_values=[500.0, 22.0, 45.0, 0.0, 0.0, 0.0]))
    chip._produce_new_reading()
    assert pin.value() == 1
    assert fired == [1]

    chip.handle_writeto(b"\x03\x00")
    chip.handle_readfrom_into(18)
    assert pin.value() == 0  # dropped low once the measurement was actually read out


def test_without_a_timer_factory_the_chip_starts_no_timer() -> None:
    chip = SCD30Chip()
    assert chip._timer is None


def test_a_timer_factory_builds_one_timer_that_setting_the_interval_re_arms() -> None:
    # One coroutine: the twin Timer runs as a task, which the harness ends with the run.
    built: list[machine.Timer] = []

    def factory() -> machine.Timer:
        built.append(machine._simulation_timer())
        return built[-1]

    async def scenario() -> None:
        chip = SCD30Chip(timer_factory=factory)
        assert chip._timer is not None
        assert chip._timer.period == 2 * 1000
        _set(chip, 0x46, 0x00, 10)  # SET_MEASUREMENT_INTERVAL - must re-arm at the new cadence
        assert chip._timer.period == 10 * 1000
        assert built == [chip._timer]  # re-armed in place: init() replaces the schedule
        chip._timer.deinit()

    run(scenario())


def test_two_raises_of_one_queued_fault_are_distinct_fresh_exceptions() -> None:
    chip = SCD30Chip()
    chip.fault.inject_fault("readfrom_into", OSError, errno.EIO, "planted", times=2)
    raised = []
    for _ in range(2):
        try:
            chip.handle_readfrom_into(3)
        except OSError as e:
            raised.append(e)
        assert chip.fault.pending("readfrom_into") == 2 - len(raised)
    assert len(raised) == 2
    assert raised[0] is not raised[1]
    assert raised[0].args == raised[1].args == (errno.EIO, "planted")


def test_a_fault_matched_to_the_read_out_spares_a_data_ready_read_and_hits_the_next_read_out() -> None:
    chip = SCD30Chip(random_source=FixedRandom(uniform_values=[500.0, 22.0, 45.0, 0.0, 0.0, 0.0]))
    chip._produce_new_reading()
    chip.fault.inject_fault("readfrom_into", OSError, errno.EIO, "read-out", match=0x0300)
    assert _get(chip, 0x02, 0x02) == word(1)  # data-ready, not the matched command
    assert chip.fault.pending("readfrom_into") == 1
    chip.handle_writeto(b"\x03\x00")
    try:
        chip.handle_readfrom_into(18)
        raise AssertionError("expected the matched fault on the read-out")
    except OSError as e:
        assert e.errno == errno.EIO
    assert chip.fault.pending("readfrom_into") == 0
    assert len(chip.handle_readfrom_into(18)) == 18


def test_a_write_fault_keyed_to_a_command_word_spares_the_other_commands() -> None:
    chip = SCD30Chip()
    chip.fault.inject_fault("writeto", OSError, errno.EIO, "stop", match=0x0104)
    chip.handle_writeto(b"\x02\x02")
    try:
        chip.handle_writeto(b"\x01\x04")
        raise AssertionError("expected the keyed fault on the stop command")
    except OSError:
        pass
    assert chip.fault.pending("writeto") == 0


def test_the_oldest_fault_a_key_matches_fires_first_and_an_unmatched_one_stays_queued() -> None:
    chip = SCD30Chip()
    chip.fault.inject_fault("writeto", OSError, errno.EIO, "for the read-out", match=0x0300)
    chip.fault.inject_fault("writeto", OSError, errno.ETIMEDOUT, "for anything")
    try:
        chip.handle_writeto(b"\x02\x02")
        raise AssertionError("expected the unkeyed fault")
    except OSError as e:
        assert e.errno == errno.ETIMEDOUT  # the older entry does not match 0x0202, so the newer one fires
    assert chip.fault.pending("writeto") == 1
    chip.handle_writeto(b"\x02\x02")  # only the 0x0300 entry is left, and it spares this command
    try:
        chip.handle_writeto(b"\x03\x00")
        raise AssertionError("expected the keyed fault")
    except OSError as e:
        assert e.errno == errno.EIO


def test_a_fault_for_zero_times_is_refused() -> None:
    chip = SCD30Chip()
    try:
        chip.fault.inject_fault("writeto", OSError, errno.EIO, times=0)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    assert chip.fault.pending("writeto") == 0


def test_power_cycle_drops_the_unread_measurement_and_keeps_the_nvm_interval() -> None:
    pin = _LevelPin()
    chip = SCD30Chip(rdy_pin=pin, random_source=FixedRandom(uniform_values=[500.0, 22.0, 45.0, 0.0, 0.0, 0.0]))
    _set(chip, 0x46, 0x00, 5)
    chip._produce_new_reading()
    assert pin.level == 1
    chip.power_cycle()
    assert pin.level == 0
    assert _get(chip, 0x02, 0x02) == word(0)
    chip.handle_writeto(b"\x03\x00")
    assert chip.handle_readfrom_into(18) == bytes(18)
    assert _get(chip, 0x46, 0x00) == word(5)


def test_rdy_stuck_high_holds_the_line_high_while_no_new_measurement_arrives() -> None:
    pin = _LevelPin()
    chip = SCD30Chip(rdy_pin=pin, random_source=FixedRandom(uniform_values=[500.0, 22.0, 45.0, 0.0, 0.0, 0.0]))
    chip.rdy_stuck_high = True
    chip._produce_new_reading()
    assert pin.level == 1
    assert _get(chip, 0x02, 0x02) == word(0)
    chip.handle_writeto(b"\x03\x00")
    chip.handle_readfrom_into(18)
    assert pin.level == 1  # the read-out does not drop a stuck line
    chip.rdy_stuck_high = False
    chip._produce_new_reading()
    assert _get(chip, 0x02, 0x02) == word(1)
    chip.handle_writeto(b"\x03\x00")
    chip.handle_readfrom_into(18)
    assert pin.level == 0


def test_nvm_writes_counts_each_accepted_nvm_command_and_nothing_else() -> None:
    # The six NVM-writing argument commands and the bare stop (Interface Description 1.4.1-1.4.3,
    # 1.4.6-1.4.8); register reads, data-ready, read-out, firmware version and soft reset write none.
    chip = SCD30Chip()
    assert chip.nvm_writes == 0
    for reg_hi, reg_lo, arg in ((0x00, 0x10, 1013), (0x46, 0x00, 5), (0x51, 0x02, 250), (0x52, 0x04, 900), (0x53, 0x06, 1), (0x54, 0x03, 150)):
        _get(chip, reg_hi, reg_lo)  # the register read of the same word is not a write
        before = chip.nvm_writes
        _set(chip, reg_hi, reg_lo, arg)
        assert chip.nvm_writes == before + 1
    chip.handle_writeto(bytes([0x01, 0x04]))  # stop continuous measurement: its status lives in NVM
    assert chip.nvm_writes == 7
    for reg_hi, reg_lo in ((0x02, 0x02), (0x03, 0x00), (0xD1, 0x00), (0xD3, 0x04)):
        _get(chip, reg_hi, reg_lo)
    assert chip.nvm_writes == 7


def test_two_identical_puts_write_the_chip_nvm_only_for_the_always_sent_commands() -> None:
    # The real SCD30_Reader over the twin's bus, driven through _set_dict_cfg() (the config-apply path
    # the PUT route calls): the second identical body writes NVM only for AmbPres and ForceCalRef.
    reader, chip = _reader_on_the_twin_bus(cfg_path=_scratch.dir())
    body: dict[str, CfgValue] = {"TempOffset": 1.5, "MeasInterval": 10, "AmbPres": 1000, "Altitude": 200, "ForceCalRef": 450, "SelfCal": True}
    with FastAsyncSleep():  # the driver's command waits cost no real time
        assert run(reader._set_dict_cfg(body, reader.get_cfg_schema())) == dict.fromkeys(body, "Valid")
        assert chip.nvm_writes == 6
        second = run(reader._set_dict_cfg(body, reader.get_cfg_schema()))
    assert second == {"TempOffset": "Unchanged", "MeasInterval": "Unchanged", "AmbPres": "Valid", "Altitude": "Unchanged", "ForceCalRef": "Valid", "SelfCal": "Unchanged"}
    assert chip.nvm_writes == 8


def test_a_failed_deferred_flush_is_healed_by_the_next_accepted_put() -> None:
    # One PUT's config-file write fails: its value stays in effect and the store runs unpersisted, one E CFG_FILE_WRITE;
    # the next accepted PUT writes the file once, holding both values, and the store is persisted again.
    cfg_path = _scratch.dir()
    reader, _chip = _reader_on_the_twin_bus(cfg_path=cfg_path)
    store = reader.cfgmgr

    async def put(body: "dict[str, CfgValue]") -> "dict[str, str]":
        results = await reader._set_dict_cfg(body, reader.get_cfg_schema())
        await store.flush_pending()  # the deferred write the PUT committed, landed or failed
        return dict(results)

    with FastAsyncSleep():  # the driver's command waits cost no real time
        assert run(reader.setup()) is True  # the store loaded, as at boot
        with WriteCountingOpen(asy_config_manager, fail_writes=True) as failing:
            first = run(put({"FRCNoise": 25.0}))  # a file-held setting: the chip's own ones live in its NVM
        unpersisted = store.unpersisted
        with WriteCountingOpen(asy_config_manager) as counting:
            second = run(put({"FRCWindow": 120}))
    assert (first, second) == ({"FRCNoise": "Valid"}, {"FRCWindow": "Valid"}), (first, second)
    assert (failing.writes, unpersisted) == (1, True), f"the failing PUT wrote {failing.writes} time(s), unpersisted={unpersisted}"
    assert (counting.writes, store.unpersisted) == (1, False), f"the healing PUT wrote {counting.writes} time(s), unpersisted={store.unpersisted}"
    with open(asy_config_manager.config_filename(cfg_path, reader.name)) as f:
        saved = json.load(f)
    assert (saved["FRCNoise"], saved["FRCWindow"]) == (25.0, 120), f"the healed file holds {saved}"
    (log,) = run(store.pr.get_log()).values()
    failures = [i for i in range(len(log["ErrNum"])) if log["ErrType"][i] == "E" and log["ErrNum"][i] == code("E", "CFG_FILE_WRITE")]
    assert len(failures) == 1, f"the store logged {log}"


def test_the_real_reader_accepts_a_reading_at_the_largest_temperature_offset() -> None:
    # The driver's range gate adds the offset back to the reported temperature: at the largest offset the twin's
    # reading still passes, and the reader reports the sensor's own temperature less 655.35 degC.
    reader, chip = _reader_on_the_twin_bus(cfg_path=_scratch.dir())

    async def scenario() -> "tuple[float | None, bool, float, int]":
        assert await reader.setup() is True
        body: dict[str, CfgValue] = {"TempOffset": 655.35}
        assert await reader._set_dict_cfg(body, reader.get_cfg_schema()) == {"TempOffset": "Valid"}
        chip._produce_new_reading()
        results, new_data = await reader._read_scd()
        return results[1], new_data, chip._temp, (await reader.get_error_counter())["SCD30"]["ErrCount"]

    with FastAsyncSleep():  # the driver's command waits cost no real time
        temperature, new_data, sensed, errors = run(scenario())
    assert new_data is True
    assert errors == 0  # no "Reading rejected"
    assert temperature is not None and abs(temperature - (sensed - 655.35)) < 0.01


def test_a_booted_reader_on_a_constant_co2_twin_reaches_frc_ready_and_keeps_its_frc_settings() -> None:
    # The real SCD30_Reader over the twin's bus, set up and initialised as at boot; the read cycles are driven
    # in-process, one chip measurement each, with the walks held still (CO2 and temperature step 0).
    reader, chip = _reader_on_the_twin_bus(cfg_path=_scratch.dir())
    chip.co2 = Walk(800.0, 800.0, 0.0)  # a twin-only knob: a constant CO2
    chip.temp = Walk(chip.temp.lo, chip.temp.hi, 0.0)  # and a steady temperature

    async def scenario() -> "tuple[list[int | None], dict[str, CfgValue]]":
        assert await reader.setup() is True
        assert await reader._init_scd() is True  # the chip answers its interval: 2 s, so 180 samples settle
        states = []
        for _ in range(180):
            chip._produce_new_reading()
            results, new_data = await reader._read_scd()
            assert await reader._error_check(results, condition=results[0] is None)
            await reader._store_scd(results, new_data)
            states.append((await reader.get_data()).FRCState)
        body: dict[str, CfgValue] = {"FRCNoise": 25.0, "FRCRate": 5.0, "FRCWindow": 90}
        assert await reader._set_dict_cfg(body, reader.get_cfg_schema()) == dict.fromkeys(body, "Valid")
        return states, (await reader.get_dict_cfg())["SCD30"]

    with FastAsyncSleep():
        states, cfg = run(scenario())
    assert states[:-1] == [1] * 179
    assert states[-1] == 4
    assert (cfg["FRCNoise"], cfg["FRCRate"], cfg["FRCWindow"]) == (25.0, 5.0, 90)
    assert chip.nvm_writes == 0  # the FRC settings never reach the chip


def test_a_stuck_high_rdy_line_warns_once_after_five_empty_reads_and_new_data_ends_it() -> None:
    reader, chip = _reader_on_the_twin_bus(cfg_path=_scratch.dir())

    async def warnings() -> int:
        log = (await reader.get_error_counter())["SCD30"]
        return sum(1 for kind, number in zip(log["ErrType"], log["ErrNum"]) if (kind, number) == ("W", code("W", "SCD_NOT_READY")))

    async def scenario() -> "tuple[list[int], int]":
        assert await reader.setup() is True
        chip.rdy_stuck_high = True
        seen = []
        for _ in range(5):
            chip._produce_new_reading()  # the line reads high, but no measurement completes
            _results, new_data = await reader._read_scd()
            assert new_data is False
            seen.append(await warnings())
        chip.rdy_stuck_high = False
        for _ in range(3):
            chip._produce_new_reading()
            _results, new_data = await reader._read_scd()
            assert new_data is True
        return seen, await warnings()

    with FastAsyncSleep():
        seen, after = run(scenario())
    assert seen == [0, 0, 0, 0, 1]
    assert after == 1  # new data ended the episode: no further entry


def test_a_silent_scd30_publishes_not_measuring_and_runs_no_cycle_streak_or_entry() -> None:
    # Data-ready never rises after three readings (the helper stops the chip's own measurement Timer): the irq
    # loop's base ticks find the line low, FRCState drops to 0 after two intervals, and nothing is retried or logged.
    reader, chip = _reader_on_the_twin_bus(cfg_path=_scratch.dir())

    async def scenario() -> "tuple[int | None, int | None, bool, int, int, int]":
        assert await reader.setup() is True
        assert await reader._init_scd() is True  # the chip answers its interval: 2 s, four 500 ms ticks
        for _ in range(3):
            chip._produce_new_reading()
            results, new_data = await reader._read_scd()
            assert await reader._error_check(results, condition=results[0] is None)
            await reader._store_scd(results, new_data)
        settling = (await reader.get_data()).FRCState
        chip._measuring = False  # the chip falls silent: its restarted measurement Timer completes nothing more
        chip._data_ready = False
        chip._drive_rdy(0)
        errors = (await reader.get_error_counter())["SCD30"]["ErrCount"]
        reader._read_event.clear()  # the three readings' own RDY edges, which no read loop consumed here
        loop = asyncio.get_event_loop().create_task(reader._irq_loop())
        for _ in range(8):  # two intervals of base ticks, the line low throughout
            reader._base_trigger_event.set()
            for _turn in range(3):
                await asyncio.sleep(0)
        await cancel(loop)
        after = (await reader.get_error_counter())["SCD30"]["ErrCount"]
        return settling, (await reader.get_data()).FRCState, bool(reader._read_event.state), reader._err_cnt_internal, errors, after

    with FastAsyncSleep():
        settling, silent, triggered, streak, errors, after = run(scenario())
    assert (settling, silent) == (1, 0), f"FRCState went {settling} -> {silent}, expected settling (1) then not measuring (0)"
    assert not triggered, "a low data-ready line re-triggered a read"
    assert (streak, after) == (0, errors), f"silence stepped the streak to {streak} or logged {after - errors} entr(ies)"


def test_fault_injection_on_writeto_and_readfrom_into() -> None:
    chip = SCD30Chip()
    chip.fault.inject_fault("writeto", OSError, errno.EIO, "no ACK")
    try:
        chip.handle_writeto(b"\x02\x02")
        raise AssertionError("expected OSError")
    except OSError:
        pass
    chip.handle_writeto(b"\x02\x02")
    chip.fault.inject_fault("readfrom_into", OSError, errno.ETIMEDOUT, "timeout")
    try:
        chip.handle_readfrom_into(3)
        raise AssertionError("expected OSError")
    except OSError:
        pass


def test_fault_injector_clear_of_one_op_leaves_other_ops_armed() -> None:
    # FaultInjector.clear() is shared, generic infrastructure (digital_twin/_fault_injection.py) -
    # exercised here via a real chip's own .fault, matching this file's own established pattern for
    # every other FaultInjector behavior, rather than a standalone test file for two small helpers.
    chip = SCD30Chip()
    chip.fault.inject_fault("writeto", OSError, errno.EIO, "no ACK")
    chip.fault.inject_fault("readfrom_into", OSError, errno.ETIMEDOUT, "timeout")
    chip.fault.clear("writeto")
    chip.handle_writeto(b"\x02\x02")  # writeto's queue was cleared - no raise
    try:
        chip.handle_readfrom_into(3)  # readfrom_into's own queue is untouched
        raise AssertionError("expected OSError")
    except OSError:
        pass


def test_fault_injector_clear_with_no_op_clears_every_queue() -> None:
    chip = SCD30Chip()
    chip.fault.inject_fault("writeto", OSError, errno.EIO, "no ACK")
    chip.fault.inject_fault("readfrom_into", OSError, errno.ETIMEDOUT, "timeout")
    chip.fault.clear()
    chip.handle_writeto(b"\x02\x02")
    assert chip.handle_readfrom_into(3) == word(0)  # neither queue raises - both were cleared, and the reply is the chip's


def test_a_hang_for_zero_times_is_refused() -> None:
    chip = SCD30Chip()
    try:
        chip.fault.inject_hang("writeto", 0.01, times=0)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_fault_injection_can_corrupt_the_next_measurement_crc() -> None:
    chip = SCD30Chip(random_source=FixedRandom(uniform_values=[500.0, 22.0, 45.0, 0.0, 0.0, 0.0]))
    chip._produce_new_reading()
    chip.corrupt_next()
    chip.handle_writeto(b"\x03\x00")
    buf = chip.handle_readfrom_into(18)
    assert buf[2] != crc8(buf[0:2])


def test_save_state_then_construct_a_fresh_chip_from_the_same_path_reads_back_identical_settings() -> None:
    path = _tmp_path("scd30_state.json")
    try:
        os.remove(path)
    except OSError:
        pass
    chip1 = SCD30Chip(state_path=path)
    _set(chip1, 0x46, 0x00, 10)  # measurement interval
    _set(chip1, 0x53, 0x06, 1)  # ASC enable
    _set(chip1, 0x00, 0x10, 1013)  # ambient pressure
    _set(chip1, 0x51, 0x02, 250)  # altitude
    _set(chip1, 0x54, 0x03, 150)  # temperature offset
    chip1.save_state()

    chip2 = SCD30Chip(state_path=path)
    assert _get(chip2, 0x46, 0x00) == word(10)
    assert _get(chip2, 0x53, 0x06) == word(1)
    assert _get(chip2, 0x00, 0x10) == word(1013)
    assert _get(chip2, 0x51, 0x02) == word(250)
    assert _get(chip2, 0x54, 0x03) == word(150)


def test_state_is_not_written_until_save_state_is_called() -> None:
    path = _tmp_path("scd30_no_autosave.json")
    try:
        os.remove(path)
    except OSError:
        pass
    chip = SCD30Chip(state_path=path)
    _set(chip, 0x46, 0x00, 10)
    try:
        with open(path):
            raise AssertionError("state file must not exist before an explicit save_state() call")
    except OSError:
        pass  # expected - nothing written yet


def test_persisted_file_is_json_with_the_five_nvm_backed_settings_and_the_measuring_status() -> None:
    path = _tmp_path("scd30_format.json")
    chip = SCD30Chip(state_path=path)
    _set(chip, 0x46, 0x00, 7)
    chip.save_state()
    with open(path) as f:
        data = json.load(f)
    assert data == {
        "measurement_interval_s": 7,
        "ambient_pressure": 0,
        "altitude": 0,
        "temp_offset_raw": 0,
        "asc_enabled": 0,
        "measuring": True,
    }
    try:
        os.stat(path + ".tmp")
        raise AssertionError("save_state() left its temporary file behind")
    except OSError:
        pass


def test_the_measuring_status_round_trips_through_the_state_file() -> None:
    path = _tmp_path("scd30_measuring.json")
    chip = SCD30Chip(state_path=path)
    chip.handle_writeto(bytes([0x01, 0x04]))  # stop
    chip.save_state()
    restarted = SCD30Chip(state_path=path, random_source=FixedRandom())
    restarted._produce_new_reading()
    assert _get(restarted, 0x02, 0x02) == word(0)  # still stopped after the power-up (1.4.1: the status is NVM)


def test_live_readings_and_in_flight_protocol_state_are_not_persisted() -> None:
    # Only the five NVM-backed settings survive a "power cycle" on real hardware - CO2/temp/humidity
    # always restart from a fresh reading. Confirmed by checking the persisted file itself never
    # contains a co2/temp/hum key at all, not just that a fresh chip happens to draw a different value.
    path = _tmp_path("scd30_no_readings_persisted.json")
    chip = SCD30Chip(state_path=path, random_source=FixedRandom(uniform_values=[500.0, 22.0, 45.0]))
    chip.save_state()
    with open(path) as f:
        data = json.load(f)
    assert "co2" not in data and "temp" not in data and "hum" not in data


def test_missing_state_file_starts_from_factory_fresh_settings_without_raising() -> None:
    path = _tmp_path("scd30_does_not_exist.json")
    try:
        os.remove(path)
    except OSError:
        pass
    with _PrintRecorder() as lines:
        chip = SCD30Chip(state_path=path)  # must not raise
    assert lines == []  # a first launch has no file: nothing to report
    assert _get(chip, 0x46, 0x00) == word(2)  # measurement_interval_s's own default


def test_an_unloadable_state_file_says_why_and_leaves_factory_fresh_settings() -> None:
    for name, text, reason in (
        ("scd30_malformed.json", "{not valid json", "json"),
        ("scd30_list.json", "[1, 2]", "shape"),
        ("scd30_mistyped.json", '{"altitude": "x", "measurement_interval_s": 9}', "type"),
        ("scd30_measuring_int.json", '{"measuring": 1}', "type"),
    ):
        path = _tmp_path(name)
        with open(path, "w") as f:
            f.write(text)
        with _PrintRecorder() as lines:
            chip = SCD30Chip(state_path=path)  # must not raise
        assert lines == [("SCD30 state", path, f"not loaded ({reason}): starting from factory-fresh settings")], (name, lines)
        assert _get(chip, 0x46, 0x00) == word(2), name
        assert _get(chip, 0x51, 0x02) == word(0), name


def test_state_path_none_never_touches_disk() -> None:
    # Default construction (state_path=None) is the same "in-memory only" convention FRAMChip uses -
    # save_state() must be a silent no-op, not raise for lacking a path.
    before = set(os.listdir("."))
    chip = SCD30Chip()
    _set(chip, 0x46, 0x00, 10)
    chip.save_state()  # must not raise
    assert set(os.listdir(".")) == before  # no file created in the working directory


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
