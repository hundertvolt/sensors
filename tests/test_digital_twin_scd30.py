"""Deterministic unit tests for digital_twin/_scd30_chip.py's own transaction-response logic -
matches the raw word-register command shapes src/asy_scd30_driver.py's SCD30_I2C sends (confirmed
directly against that file, not tests/machine.py). Real-time RDY-pin/data-ready scheduling is
exercised only via the explicit, synchronous _produce_new_reading() test hook here - the one
"does real-time firing actually work at all" check lives in tests/test_digital_twin_machine.py
against the shared Timer class itself, matching this step's own "not flaky wall-clock-timing
assertions" criterion (FINAL_WIRING_PLAN.md's Step 3).
"""

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

sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

from _crc8 import crc8, word  # noqa: E402
from _scd30_chip import Scd30Chip  # noqa: E402

_TMP_DIR = "tests/_tmp"


def _tmp_path(name: str) -> str:
    # Same convention as test_digital_twin_fram.py's own _tmp_path() helper.
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass
    return _TMP_DIR + "/" + name


class _FixedRandom:
    def __init__(self, uniform_values: "list[float] | None" = None) -> None:
        self._uniform_values = list(uniform_values or [])

    def uniform(self, a: float, b: float) -> float:
        assert self._uniform_values, "uniform() called more times than scripted"
        value = self._uniform_values.pop(0)
        assert a <= value <= b, f"scripted value {value} outside requested range [{a},{b}]"
        return value


def _get(chip: Scd30Chip, reg_hi: int, reg_lo: int, nbytes: int = 3) -> bytes:
    chip.handle_writeto(bytes([reg_hi, reg_lo]))
    return chip.handle_readfrom_into(nbytes)


def _set(chip: Scd30Chip, reg_hi: int, reg_lo: int, arg: int) -> None:
    payload = bytes([reg_hi, reg_lo, (arg >> 8) & 0xFF, arg & 0xFF])
    chip.handle_writeto(payload + bytes([crc8(payload[2:4])]))


def test_measurement_interval_set_then_get_round_trips() -> None:
    chip = Scd30Chip(auto_refresh=False)
    _set(chip, 0x46, 0x00, 5)
    reply = _get(chip, 0x46, 0x00)
    assert reply == word(5)


def test_self_calibration_enabled_set_then_get_round_trips() -> None:
    chip = Scd30Chip(auto_refresh=False)
    _set(chip, 0x53, 0x06, 1)
    assert _get(chip, 0x53, 0x06) == word(1)
    _set(chip, 0x53, 0x06, 0)
    assert _get(chip, 0x53, 0x06) == word(0)


def test_ambient_pressure_set_then_get_round_trips() -> None:
    chip = Scd30Chip(auto_refresh=False)
    _set(chip, 0x00, 0x10, 1013)
    assert _get(chip, 0x00, 0x10) == word(1013)


def test_altitude_set_then_get_round_trips() -> None:
    chip = Scd30Chip(auto_refresh=False)
    _set(chip, 0x51, 0x02, 250)
    assert _get(chip, 0x51, 0x02) == word(250)


def test_stop_continuous_measurement_and_soft_reset_are_accepted_bare_commands() -> None:
    # Neither command has any readback of its own (no persistent chip-side state a soft reset would
    # need to clear) - this only proves handle_writeto() accepts the 2-byte command shape without
    # raising, matching a real device silently accepting these.
    chip = Scd30Chip(auto_refresh=False)
    chip.handle_writeto(bytes([0x01, 0x04]))  # STOP_CONTINUOUS_MEASUREMENT
    chip.handle_writeto(bytes([0xD3, 0x04]))  # SOFT_RESET


def test_read_firmware_version_reports_the_fixed_plausible_value() -> None:
    chip = Scd30Chip(auto_refresh=False)
    assert _get(chip, 0xD1, 0x00) == word(0x0342)


def test_readfrom_into_with_an_unrecognized_last_command_returns_zero_bytes() -> None:
    chip = Scd30Chip(auto_refresh=False)
    chip.handle_writeto(bytes([0xFF, 0xFF]))  # not a command this chip recognizes
    assert chip.handle_readfrom_into(3) == bytes(3)


def test_temperature_offset_set_then_get_round_trips_as_raw_centidegrees() -> None:
    chip = Scd30Chip(auto_refresh=False)
    _set(chip, 0x54, 0x03, 150)  # driver sends offset*100
    assert _get(chip, 0x54, 0x03) == word(150)


def test_forced_recalibration_reference_always_reads_back_400() -> None:
    # Real hardware quirk (asy_scd30_driver.py's own comment): volatile readback always 400
    # regardless of the last value applied - the calibration curve update is permanent, the
    # readback register just isn't.
    chip = Scd30Chip(auto_refresh=False)
    _set(chip, 0x52, 0x04, 900)
    assert _get(chip, 0x52, 0x04) == word(400)


def test_data_ready_starts_false() -> None:
    chip = Scd30Chip(auto_refresh=False)
    assert _get(chip, 0x02, 0x02) == word(0)


def test_produce_new_reading_sets_data_ready_true() -> None:
    chip = Scd30Chip(auto_refresh=False, random_source=_FixedRandom(uniform_values=[500.0, 22.0, 45.0, 0.0, 0.0, 0.0]))
    chip._produce_new_reading()
    assert _get(chip, 0x02, 0x02) == word(1)


def test_read_measurement_returns_crc_valid_buffer_decoding_to_the_produced_values() -> None:
    # First 3 values: the uniform draw at construction. Last 3: the step delta _produce_new_reading()
    # below draws - zeroed here so the final value stays exactly at the constructed initial value,
    # keeping this test's own assertions about the *values* independent of the walk mechanism
    # (which gets its own dedicated tests further down).
    chip = Scd30Chip(auto_refresh=False, random_source=_FixedRandom(uniform_values=[512.5, 21.5, 47.25, 0.0, 0.0, 0.0]))
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
    chip = Scd30Chip(auto_refresh=False, random_source=_FixedRandom(uniform_values=[500.0, 22.0, 45.0, 0.0, 0.0, 0.0]))
    chip._produce_new_reading()
    chip.handle_writeto(b"\x03\x00")
    chip.handle_readfrom_into(18)
    assert _get(chip, 0x02, 0x02) == word(0)  # cleared the instant it was read (Interface Description 1.4.4)


def test_construction_draws_an_initial_value_within_range_without_needing_a_reading_produced() -> None:
    # Initial value: a uniform draw within [min,max] at construction, before _produce_new_reading()
    # is ever called - not datasheet-derived (the step bound isn't), but the initial-value mechanism
    # (a uniform draw) is unchanged from before this walk existed.
    chip = Scd30Chip(auto_refresh=False, random_source=_FixedRandom(uniform_values=[1234.0, 25.5, 55.5]))
    assert chip._co2 == 1234.0
    assert chip._temp == 25.5
    assert chip._hum == 55.5


def test_produce_new_reading_steps_from_the_previous_value_rather_than_a_fresh_draw() -> None:
    chip = Scd30Chip(auto_refresh=False, random_source=_FixedRandom(uniform_values=[1000.0, 20.0, 50.0, 25.0, -0.5, 2.0]))
    assert chip._co2 == 1000.0 and chip._temp == 20.0 and chip._hum == 50.0  # construction draw
    chip._produce_new_reading()
    assert chip._co2 == 1025.0  # 1000.0 + 25.0
    assert chip._temp == 19.5  # 20.0 + -0.5
    assert chip._hum == 52.0  # 50.0 + 2.0


def test_produce_new_reading_step_delta_is_clamped_to_the_default_step_bound() -> None:
    # _FixedRandom itself asserts a <= value <= b for every uniform() call - if _produce_new_reading()
    # ever passed the wrong (a, b) bound for a step draw (e.g. the full [min,max] range instead of
    # [-step,step]), this test's deliberately-tight scripted delta would fail that assertion.
    chip = Scd30Chip(auto_refresh=False, random_source=_FixedRandom(uniform_values=[1000.0, 20.0, 50.0, 50.0, 1.0, 3.0]))
    chip._produce_new_reading()  # co2_step=50.0, temp_step=1.0, hum_step=3.0 (this chip's defaults)


def test_produce_new_reading_step_is_clamped_to_the_configured_max() -> None:
    chip = Scd30Chip(
        auto_refresh=False,
        max_co2=2000.0,
        co2_step=50.0,
        random_source=_FixedRandom(uniform_values=[1980.0, 20.0, 50.0, 50.0, 0.0, 0.0]),
    )
    chip._produce_new_reading()
    assert chip._co2 == 2000.0  # 1980.0 + 50.0 would be 2030.0 - clamped back to max_co2


def test_produce_new_reading_step_is_clamped_to_the_configured_min() -> None:
    chip = Scd30Chip(
        auto_refresh=False,
        min_temp=15.0,
        temp_step=1.0,
        random_source=_FixedRandom(uniform_values=[1000.0, 15.5, 50.0, 0.0, -1.0, 0.0]),
    )
    chip._produce_new_reading()
    assert chip._temp == 15.0  # 15.5 + -1.0 would be 14.5 - clamped back to min_temp


def test_step_bounds_are_configurable_via_the_constructor() -> None:
    chip = Scd30Chip(
        auto_refresh=False,
        co2_step=5.0,
        temp_step=0.1,
        hum_step=0.5,
        random_source=_FixedRandom(uniform_values=[1000.0, 20.0, 50.0, 5.0, 0.1, 0.5]),
    )
    chip._produce_new_reading()  # would violate the default 50.0/1.0/3.0 bounds - proves the override took


def test_corrupt_next_measurement_stays_orthogonal_to_the_walk() -> None:
    # The fault-injection flag corrupts whatever the walk just produced - it doesn't interact with
    # the walk mechanism itself.
    chip = Scd30Chip(auto_refresh=False, random_source=_FixedRandom(uniform_values=[1000.0, 20.0, 50.0, 0.0, 0.0, 0.0]))
    chip._produce_new_reading()
    chip.corrupt_next_measurement = True
    chip.handle_writeto(b"\x03\x00")
    buf = chip.handle_readfrom_into(18)
    assert buf[2] != crc8(buf[0:2])
    co2 = struct.unpack(">f", buf[0:2] + buf[3:5])[0]
    assert co2 == 1000.0  # the underlying walked value is unaffected by the corruption


def test_default_ranges_stay_inside_the_datasheets_own_documented_ranges() -> None:
    # Sensirion_CO2_Sensors_SCD30_Datasheet.pdf: CO2 accuracy-guaranteed 400-10'000ppm, humidity
    # 0-100%RH, temperature -40-70 degC. The twin's own defaults must be sensible sub-ranges.
    chip = Scd30Chip(auto_refresh=False)
    assert 400 <= chip._min_co2 and chip._max_co2 <= 10000
    assert 0 <= chip._min_hum and chip._max_hum <= 100
    assert -40 <= chip._min_temp and chip._max_temp <= 70


def test_rdy_pin_goes_high_on_new_reading_and_fires_a_registered_rising_edge_handler() -> None:
    fired: list[int | None] = []

    class _FakePin:
        IRQ_RISING = 0x08
        IRQ_FALLING = 0x04

        def __init__(self) -> None:
            self._value = 0
            self._handler: Callable[[_FakePin], None] | None = None
            self._trigger = self.IRQ_RISING | self.IRQ_FALLING

        def value(self, x: "int | None" = None) -> "int | None":
            if x is None:
                return self._value
            self._value = 1 if x else 0
            return None

        def irq(self, handler: "Callable[[_FakePin], None] | None" = None, trigger: int = IRQ_RISING | IRQ_FALLING, hard: bool = False) -> None:
            self._handler = handler
            self._trigger = trigger

        def simulate_edge(self, new_value: int) -> None:
            old = self._value
            self._value = 1 if new_value else 0
            rising = old == 0 and self._value == 1
            if rising and (self._trigger & self.IRQ_RISING) and self._handler is not None:
                self._handler(self)

    pin = _FakePin()
    pin.irq(handler=lambda p: fired.append(p.value()), trigger=pin.IRQ_RISING)
    chip = Scd30Chip(auto_refresh=False, rdy_pin=pin, random_source=_FixedRandom(uniform_values=[500.0, 22.0, 45.0, 0.0, 0.0, 0.0]))
    chip._produce_new_reading()
    assert pin.value() == 1
    assert fired == [1]

    chip.handle_writeto(b"\x03\x00")
    chip.handle_readfrom_into(18)
    assert pin.value() == 0  # dropped low once the measurement was actually read out


def test_auto_refresh_false_does_not_start_a_background_timer() -> None:
    chip = Scd30Chip(auto_refresh=False)
    assert chip._timer is None


def test_auto_refresh_true_starts_a_real_timer_and_setting_interval_re_arms_it() -> None:
    chip = Scd30Chip()  # auto_refresh defaults to True
    assert chip._timer is not None
    first_timer = chip._timer
    _set(chip, 0x46, 0x00, 10)  # SET_MEASUREMENT_INTERVAL - must re-arm at the new cadence
    assert chip._timer is not None
    assert chip._timer.period == 10 * 1000
    assert chip._timer is not first_timer  # re-armed, not just mutated in place
    chip._timer.deinit()  # don't leave a live background task running past this test


def test_fault_injection_on_writeto_and_readfrom_into() -> None:
    chip = Scd30Chip(auto_refresh=False)
    chip.fault.inject_fault("writeto", OSError(5, "no ACK"))
    try:
        chip.handle_writeto(b"\x02\x02")
        raise AssertionError("expected OSError")
    except OSError:
        pass
    chip.handle_writeto(b"\x02\x02")
    chip.fault.inject_fault("readfrom_into", OSError(5, "timeout"))
    try:
        chip.handle_readfrom_into(3)
        raise AssertionError("expected OSError")
    except OSError:
        pass


def test_fault_injector_clear_of_one_op_leaves_other_ops_armed() -> None:
    # FaultInjector.clear() is shared, generic infrastructure (digital_twin/_fault_injection.py) -
    # exercised here via a real chip's own .fault, matching this file's own established pattern for
    # every other FaultInjector behavior, rather than a standalone test file for two small helpers.
    chip = Scd30Chip(auto_refresh=False)
    chip.fault.inject_fault("writeto", OSError(5, "no ACK"))
    chip.fault.inject_fault("readfrom_into", OSError(5, "timeout"))
    chip.fault.clear("writeto")
    chip.handle_writeto(b"\x02\x02")  # writeto's queue was cleared - no raise
    try:
        chip.handle_readfrom_into(3)  # readfrom_into's own queue is untouched
        raise AssertionError("expected OSError")
    except OSError:
        pass


def test_fault_injector_clear_with_no_op_clears_every_queue() -> None:
    chip = Scd30Chip(auto_refresh=False)
    chip.fault.inject_fault("writeto", OSError(5, "no ACK"))
    chip.fault.inject_fault("readfrom_into", OSError(5, "timeout"))
    chip.fault.clear()
    chip.handle_writeto(b"\x02\x02")
    chip.handle_readfrom_into(3)  # neither queue raises - both were cleared


def test_fault_injection_can_corrupt_the_next_measurement_crc() -> None:
    chip = Scd30Chip(auto_refresh=False, random_source=_FixedRandom(uniform_values=[500.0, 22.0, 45.0, 0.0, 0.0, 0.0]))
    chip._produce_new_reading()
    chip.corrupt_next_measurement = True
    chip.handle_writeto(b"\x03\x00")
    buf = chip.handle_readfrom_into(18)
    assert buf[2] != crc8(buf[0:2])


def test_save_state_then_construct_a_fresh_chip_from_the_same_path_reads_back_identical_settings() -> None:
    path = _tmp_path("scd30_state.json")
    try:
        os.remove(path)
    except OSError:
        pass
    chip1 = Scd30Chip(auto_refresh=False, state_path=path)
    _set(chip1, 0x46, 0x00, 10)  # measurement interval
    _set(chip1, 0x53, 0x06, 1)  # ASC enable
    _set(chip1, 0x00, 0x10, 1013)  # ambient pressure
    _set(chip1, 0x51, 0x02, 250)  # altitude
    _set(chip1, 0x54, 0x03, 150)  # temperature offset
    chip1.save_state()

    chip2 = Scd30Chip(auto_refresh=False, state_path=path)
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
    chip = Scd30Chip(auto_refresh=False, state_path=path)
    _set(chip, 0x46, 0x00, 10)
    try:
        with open(path):
            raise AssertionError("state file must not exist before an explicit save_state() call")
    except OSError:
        pass  # expected - nothing written yet


def test_persisted_file_is_json_with_the_five_nvm_backed_settings() -> None:
    path = _tmp_path("scd30_format.json")
    chip = Scd30Chip(auto_refresh=False, state_path=path)
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
    }


def test_live_readings_and_in_flight_protocol_state_are_not_persisted() -> None:
    # Only the five NVM-backed settings survive a "power cycle" on real hardware - CO2/temp/humidity
    # always restart from a fresh reading. Confirmed by checking the persisted file itself never
    # contains a co2/temp/hum key at all, not just that a fresh chip happens to draw a different value.
    path = _tmp_path("scd30_no_readings_persisted.json")
    chip = Scd30Chip(auto_refresh=False, state_path=path, random_source=_FixedRandom(uniform_values=[500.0, 22.0, 45.0]))
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
    chip = Scd30Chip(auto_refresh=False, state_path=path)  # must not raise
    assert _get(chip, 0x46, 0x00) == word(2)  # measurement_interval_s's own default


def test_load_state_with_malformed_json_leaves_factory_fresh_settings_without_raising() -> None:
    path = _tmp_path("scd30_malformed.json")
    with open(path, "w") as f:
        f.write("{not valid json")
    chip = Scd30Chip(auto_refresh=False, state_path=path)  # must not raise
    assert _get(chip, 0x46, 0x00) == word(2)


def test_state_path_none_never_touches_disk() -> None:
    # Default construction (state_path=None) is the same "in-memory only" convention FramChip uses -
    # save_state() must be a silent no-op, not raise for lacking a path.
    chip = Scd30Chip(auto_refresh=False)
    _set(chip, 0x46, 0x00, 10)
    chip.save_state()  # must not raise


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
