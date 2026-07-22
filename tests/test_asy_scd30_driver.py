"""Unit + integration tests for asy_scd30_driver.py (src/).

Module-level tests exercise SCD30_I2C alone against tests/machine.py's fake I2C/Pin, cross-checked
byte-for-byte against the Interface Description's own worked examples (datasheets/scd30/) rather
than only against this file's own CRC8 computation. Integration-level tests exercise SCD30_Reader
wired to the real src/asy_i2c_driver.py, src/base_classes.py and src/print_log.py - no mocking above
the raw I2C bus - covering how a real OSError (bus fault) or RuntimeError (CRC mismatch) propagates
up through the Reader's never-raises wrapper contract and into the real error counter/log.
"""

import asyncio
import struct

from machine import I2C as FakeI2C
from machine import Pin as FakePin
from machine import Timer as FakeTimer

from asy_i2c_driver import I2C
from asy_scd30_driver import SCD30, SCD30_I2C, SCD30_Reader
from crc_checks import CRC8

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


_ADDR = 0x61  # _SCD30_DEFAULT_ADDR


def make_i2c() -> I2C:
    return I2C(0, scl_pin=1, sda_pin=0, frequency=100000)


def fake(i2c: I2C) -> FakeI2C:
    return i2c._i2c  # type: ignore[return-value]


def make_scd() -> "tuple[SCD30_I2C, FakeI2C]":
    i2c = make_i2c()
    scd = SCD30_I2C(i2c)
    return scd, fake(i2c)


def make_reader(trigger_sec: int = 3, max_i2c_err: int = 5) -> SCD30_Reader:
    return SCD30_Reader(make_i2c(), irq_pin=5, trigger_sec=trigger_sec, max_i2c_err=max_i2c_err)


def reader_fake_i2c(reader: SCD30_Reader) -> FakeI2C:
    return reader.scd.i2c_scd30.i2c_device.i2c._i2c  # type: ignore[return-value]


def crc8_byte(data: bytes) -> int:
    added = run(CRC8().add(bytearray(data)))
    assert added is not None
    return added[-1]


def register_frame(value: int) -> bytes:
    # 2 data bytes (big-endian, matching >H) + 1 CRC byte over those two - every SCD30 register
    # read reply (Interface Description 1.2, Table 1).
    payload = struct.pack(">H", value)
    return payload + bytes([crc8_byte(payload)])


def data_frame(co2: float, temperature: float, humidity: float) -> bytes:
    # 3 x (word0 + crc0 + word1 + crc1) = 18 bytes, matching read_measurement()'s own layout and
    # Interface Description Table 2's read-out order (CO2, Temperature, Humidity).
    frame = bytearray()
    for value in (co2, temperature, humidity):
        raw = struct.pack(">f", value)
        msw, lsw = raw[0:2], raw[2:4]
        frame += msw + bytes([crc8_byte(msw)]) + lsw + bytes([crc8_byte(lsw)])
    return bytes(frame)


async def _settle(n: int = 5) -> None:
    for _ in range(n):
        await asyncio.sleep(0)


# ---------------------------------------------------------------------------
# Module level: wire format cross-checked against the Interface Description's own worked examples
# (datasheets/scd30/Sensirion_CO2_Sensors_SCD30_Interface_Description.pdf) - hardcoded bytes from
# the PDF, not this file's own crc8_byte() helper, so a latent bug in that helper couldn't mask a
# real mismatch.
# ---------------------------------------------------------------------------


def test_stop_continuous_measurement_matches_datasheet_example() -> None:
    # Section 1.4.2: START 0xC2 0x01 0x04 STOP
    scd, i2c = make_scd()
    run(scd.stop_continuous_measurement())
    assert i2c.log[-1] == ("writeto", _ADDR, bytes([0x01, 0x04]), True)


def test_trigger_continuous_measurement_zero_pressure_matches_datasheet_example() -> None:
    # Section 1.4.1: START 0xC2 0x00 0x10 0x00 0x00 0x81 STOP
    scd, i2c = make_scd()
    run(scd.set_ambient_pressure(0))
    assert i2c.log[-1] == ("writeto", _ADDR, bytes([0x00, 0x10, 0x00, 0x00, 0x81]), True)


def test_set_measurement_interval_matches_datasheet_example() -> None:
    # Section 1.4.3: START 0xC2 0x46 0x00 0x00 0x02 0xE3 STOP (set interval to 2s)
    scd, i2c = make_scd()
    run(scd.set_measurement_interval(2))
    assert i2c.log[-1] == ("writeto", _ADDR, bytes([0x46, 0x00, 0x00, 0x02, 0xE3]), True)


def test_get_data_ready_command_matches_datasheet_example() -> None:
    # Section 1.4.4: START 0xC2 0x02 0x02 STOP. Queues "not ready" (0) so read_measurement() stops
    # right after this command instead of also needing a full 18-byte measurement frame queued.
    scd, i2c = make_scd()
    i2c.read_queue.append(register_frame(0))
    run(scd.read_measurement())
    assert i2c.log[0] == ("writeto", _ADDR, bytes([0x02, 0x02]), True)


def test_read_measurement_command_matches_datasheet_example() -> None:
    # Section 1.4.5: write command 0xC2 0x03 0x00 STOP
    scd, i2c = make_scd()
    i2c.read_queue.append(register_frame(1))
    i2c.read_queue.append(data_frame(400.0, 20.0, 50.0))
    run(scd.read_measurement())
    ops = [entry for entry in i2c.log if entry[0] == "writeto"]
    assert ops[-1] == ("writeto", _ADDR, bytes([0x03, 0x00]), True)


def test_read_measurement_data_matches_datasheet_worked_example() -> None:
    # Section 1.4.5/1.5 worked example: 439 PPM, 48.8% RH, 27.2 degC, exact bytes from the PDF's
    # own oscilloscope capture (CRC bytes included, verbatim, not recomputed).
    scd, i2c = make_scd()
    i2c.read_queue.append(register_frame(1))
    i2c.read_queue.append(
        bytes(
            [
                0x43, 0xDB, 0xCB, 0x8C, 0x2E, 0x8F,  # CO2
                0x41, 0xD9, 0x70, 0xE7, 0xFF, 0xF5,  # Temperature
                0x42, 0x43, 0xBF, 0x3A, 0x1B, 0x74,  # Humidity
            ]
        )
    )
    run(scd.read_measurement())
    assert abs((scd._co2 or 0) - 439.09) < 0.01
    assert abs((scd._temperature or 0) - 27.2) < 0.05
    assert abs((scd._relative_humidity or 0) - 48.8) < 0.05


def test_asc_deactivate_matches_datasheet_example() -> None:
    # Section 1.4.6: START 0xC2 0x53 0x06 0x00 0x00 0x81 STOP
    scd, i2c = make_scd()
    run(scd.set_self_calibration_enabled(False))
    assert i2c.log[-1] == ("writeto", _ADDR, bytes([0x53, 0x06, 0x00, 0x00, 0x81]), True)


def test_frc_matches_datasheet_example() -> None:
    # Section 1.4.4(FRC): START 0xC2 0x52 0x04 0x01 0xC2 0x50 STOP (reference = 450 ppm)
    scd, i2c = make_scd()
    run(scd.set_forced_recalibration_reference(450))
    assert i2c.log[-1] == ("writeto", _ADDR, bytes([0x52, 0x04, 0x01, 0xC2, 0x50]), True)


def test_temperature_offset_matches_datasheet_example() -> None:
    # Section 1.4.7: START 0xC2 0x54 0x03 0x01 0xF4 0x33 STOP (offset = 5.00 degC = 500 centidegrees)
    scd, i2c = make_scd()
    run(scd.set_temperature_offset(5.0))
    assert i2c.log[-1] == ("writeto", _ADDR, bytes([0x54, 0x03, 0x01, 0xF4, 0x33]), True)


def test_altitude_matches_datasheet_example() -> None:
    # Section 1.4.8: START 0xC2 0x51 0x02 0x03 0xE8 0xD4 STOP (altitude = 1000m)
    scd, i2c = make_scd()
    run(scd.set_altitude(1000))
    assert i2c.log[-1] == ("writeto", _ADDR, bytes([0x51, 0x02, 0x03, 0xE8, 0xD4]), True)


def test_read_firmware_version_command_matches_datasheet_example() -> None:
    # Section 1.4.9: write 0xC2 0xD1 0x00 STOP
    scd, i2c = make_scd()
    i2c.read_queue.append(register_frame(0x0342))  # major=3, minor=0x42, per the PDF's own example
    run(scd._read_register(0xD100))
    assert i2c.log[0] == ("writeto", _ADDR, bytes([0xD1, 0x00]), True)


def test_soft_reset_command_matches_datasheet_example() -> None:
    # Section 1.4.10: START 0xC2 0xD3 0x04 STOP
    scd, i2c = make_scd()
    run(scd.reset())
    assert i2c.log[-1] == ("writeto", _ADDR, bytes([0xD3, 0x04]), True)


def test_get_temperature_offset_matches_datasheet_example() -> None:
    # Section 1.4.7 readback: 0x01 0xF4 (500) -> 5.00 degC
    scd, i2c = make_scd()
    i2c.read_queue.append(bytes([0x01, 0xF4, 0x33]))
    assert run(scd.get_temperature_offset()) == 5.0


# ---------------------------------------------------------------------------
# Module level: range validation - every boundary, both sides, for every persistent setter
# ---------------------------------------------------------------------------


def _raises_attribute_error(coro: "Coroutine[Any, Any, None]") -> bool:
    try:
        run(coro)
    except AttributeError:
        return True
    return False


def test_set_measurement_interval_boundaries() -> None:
    scd, _ = make_scd()
    assert _raises_attribute_error(scd.set_measurement_interval(1))
    assert _raises_attribute_error(scd.set_measurement_interval(1801))
    assert not _raises_attribute_error(scd.set_measurement_interval(2))
    assert not _raises_attribute_error(scd.set_measurement_interval(1800))
    assert not _raises_attribute_error(scd.set_measurement_interval(900))


def test_set_ambient_pressure_boundaries() -> None:
    scd, _ = make_scd()
    assert _raises_attribute_error(scd.set_ambient_pressure(699))
    assert _raises_attribute_error(scd.set_ambient_pressure(1401))
    assert not _raises_attribute_error(scd.set_ambient_pressure(0))  # special "disable" value
    assert not _raises_attribute_error(scd.set_ambient_pressure(700))
    assert not _raises_attribute_error(scd.set_ambient_pressure(1400))
    assert not _raises_attribute_error(scd.set_ambient_pressure(1013))


def test_set_ambient_pressure_rejects_values_just_inside_the_dead_zone_around_zero() -> None:
    # 0 is the one special value below 700 that's valid - 1 through 699 must all still raise.
    scd, _ = make_scd()
    assert _raises_attribute_error(scd.set_ambient_pressure(1))
    assert _raises_attribute_error(scd.set_ambient_pressure(699))


def test_set_ambient_pressure_rejects_fractional_values_that_would_truncate_to_the_special_zero() -> None:
    # Regression test for a real bug found during re-review: validating against pressure_mbar
    # *after* int()-truncating it let any value in the open interval (-1, 0) - e.g. -0.5 - silently
    # through as the special "disable" value 0, instead of being rejected, since int(-0.5) == 0
    # (Python/MicroPython int() truncates toward zero, it doesn't round). Confirmed directly
    # against the real interpreter before fixing: set_ambient_pressure(-0.5) used to send a real
    # "disable ambient pressure" command to the sensor with no error raised at all.
    scd, i2c = make_scd()
    for bad in (-0.5, -0.01, -0.999):
        assert _raises_attribute_error(scd.set_ambient_pressure(bad)), f"{bad} should have raised"
    assert len(i2c.log) == 0  # none of the rejected calls should have reached the bus


def test_set_altitude_boundaries() -> None:
    scd, _ = make_scd()
    assert _raises_attribute_error(scd.set_altitude(-1))
    assert _raises_attribute_error(scd.set_altitude(65536))
    assert not _raises_attribute_error(scd.set_altitude(0))
    assert not _raises_attribute_error(scd.set_altitude(65535))
    assert not _raises_attribute_error(scd.set_altitude(1000))


def test_set_altitude_rejects_fractional_values_that_would_truncate_to_zero() -> None:
    # Same class of bug as set_ambient_pressure's own regression test above: int(-0.5) == 0, which
    # is itself a valid altitude (sea level) - so truncating before validating would have silently
    # accepted a negative altitude as "0m" instead of rejecting it. altitude's signature only
    # advertises int (unlike pressure_mbar's explicit int | float), but nothing stops a caller from
    # passing a float anyway - defensive test, deliberately outside the declared type.
    scd, i2c = make_scd()
    for bad in (-0.5, -0.01, -0.999):
        assert _raises_attribute_error(scd.set_altitude(bad)), f"{bad} should have raised"  # type: ignore[arg-type]
    assert len(i2c.log) == 0


def test_set_temperature_offset_boundaries() -> None:
    scd, _ = make_scd()
    assert _raises_attribute_error(scd.set_temperature_offset(-0.01))
    assert _raises_attribute_error(scd.set_temperature_offset(655.36))
    assert not _raises_attribute_error(scd.set_temperature_offset(0.0))
    assert not _raises_attribute_error(scd.set_temperature_offset(655.35))
    assert not _raises_attribute_error(scd.set_temperature_offset(5.0))


def test_set_forced_recalibration_reference_boundaries() -> None:
    scd, _ = make_scd()
    assert _raises_attribute_error(scd.set_forced_recalibration_reference(399))
    assert _raises_attribute_error(scd.set_forced_recalibration_reference(2001))
    assert not _raises_attribute_error(scd.set_forced_recalibration_reference(400))
    assert not _raises_attribute_error(scd.set_forced_recalibration_reference(2000))
    assert not _raises_attribute_error(scd.set_forced_recalibration_reference(450))


def test_invalid_setter_call_does_not_corrupt_state_for_a_later_valid_call() -> None:
    # Multiple invalid-parameter recombinations in sequence, on one shared instance/buffer, then a
    # real valid call afterwards - the shared self._buffer must not be left in a state that
    # corrupts a subsequent, unrelated, valid command.
    scd, i2c = make_scd()
    assert _raises_attribute_error(scd.set_altitude(-1))
    assert _raises_attribute_error(scd.set_temperature_offset(-1.0))
    assert _raises_attribute_error(scd.set_forced_recalibration_reference(100))
    assert _raises_attribute_error(scd.set_measurement_interval(0))
    assert _raises_attribute_error(scd.set_ambient_pressure(1))
    # None of the above should have reached the bus at all (raised before _send_command).
    assert len(i2c.log) == 0
    run(scd.set_altitude(500))
    assert i2c.log[-1] == ("writeto", _ADDR, bytes([0x51, 0x02, 0x01, 0xF4, crc8_byte(bytes([0x01, 0xF4]))]), True)


def test_range_checks_raise_before_touching_the_bus() -> None:
    # An invalid argument must never reach _send_command at all (no partial/garbage I2C traffic).
    scd, i2c = make_scd()
    for bad_call in (
        scd.set_measurement_interval(1),
        scd.set_ambient_pressure(1),
        scd.set_altitude(-1),
        scd.set_temperature_offset(-1.0),
        scd.set_forced_recalibration_reference(1),
    ):
        assert _raises_attribute_error(bad_call)
    assert len(i2c.log) == 0


# ---------------------------------------------------------------------------
# Module level: CRC - register reads and full measurement reads, matching Sensirion's documented
# CRC-8 (poly 0x31, init 0xFF) exactly - reuses the already-verified real CRC8 class rather than
# reimplementing the algorithm in this test file.
# ---------------------------------------------------------------------------


def test_read_register_raises_on_crc_mismatch() -> None:
    scd, i2c = make_scd()
    corrupted = bytearray(register_frame(1234))
    corrupted[-1] ^= 0xFF
    i2c.read_queue.append(bytes(corrupted))
    try:
        run(scd._read_register(0xBEEF))
        raised = False
    except RuntimeError:
        raised = True
    assert raised


def test_read_measurement_raises_on_crc_mismatch_in_any_of_the_six_words() -> None:
    # Corrupt each of the 6 CRC bytes (positions 2,5,8,11,14,17) independently - every one must be
    # caught, not just the first.
    for crc_pos in (2, 5, 8, 11, 14, 17):
        scd, i2c = make_scd()
        i2c.read_queue.append(register_frame(1))
        corrupted = bytearray(data_frame(400.0, 20.0, 50.0))
        corrupted[crc_pos] ^= 0xFF
        i2c.read_queue.append(bytes(corrupted))
        try:
            run(scd.read_measurement())
            raised = False
        except RuntimeError:
            raised = True
        assert raised, f"CRC corruption at byte {crc_pos} was not detected"


def test_read_measurement_not_ready_clears_cached_values_and_issues_no_measurement_read() -> None:
    scd, i2c = make_scd()
    # Assigned through a float | None-typed local rather than bare literals - mypy narrows a direct
    # `scd._co2 = 1.0` to non-Optional float and never widens it back across the run() call below,
    # which would make every `assert ... is None` after the first look statically unreachable.
    stale: float | None = 1.0
    scd._co2, scd._temperature, scd._relative_humidity = stale, stale, stale
    i2c.read_queue.append(register_frame(0))
    run(scd.read_measurement())
    assert scd._co2 is None
    assert scd._temperature is None
    assert scd._relative_humidity is None
    ops = [entry[0] for entry in i2c.log]
    assert ops == ["writeto", "readfrom_into"]  # only the data-ready probe, no measurement read


def test_get_co2_temperature_humidity_all_reflect_one_read_measurement_call() -> None:
    # Regression test for a real bug found during re-review: get_CO2()/get_temperature()/
    # get_relative_humidity() used to each independently call the data-ready-checking fetch, and
    # the SCD30's data-ready flag clears the instant the measurement is actually read - so only the
    # first of the three ever saw "ready", and the second/third would see "not ready" and wipe the
    # first call's own fresh result back to None. Modeled here with a single register_frame(1) +
    # data_frame() pair queued - exactly one real sensor read - not three, which is what let the bug
    # go unnoticed: three independently-queued "ready" replies don't match how the real hardware
    # actually behaves across one read_measurement() + three getter calls.
    scd, i2c = make_scd()
    i2c.read_queue.append(register_frame(1))
    i2c.read_queue.append(data_frame(412.5, 23.4, 45.6))
    run(scd.read_measurement())
    co2 = run(scd.get_CO2())
    temperature = run(scd.get_temperature())
    humidity = run(scd.get_relative_humidity())
    assert co2 is not None and abs(co2 - 412.5) < 0.01
    assert temperature is not None and abs(temperature - 23.4) < 0.01
    assert humidity is not None and abs(humidity - 45.6) < 0.01
    # The three getters must be pure cache reads - no further I2C traffic beyond the one
    # read_measurement() call above.
    assert len(i2c.log) == 4  # data-ready probe (write+read) + measurement read (write+read)


def test_getters_never_touch_the_bus_on_their_own() -> None:
    scd, i2c = make_scd()
    co2 = run(scd.get_CO2())
    temperature = run(scd.get_temperature())
    humidity = run(scd.get_relative_humidity())
    assert co2 is None  # nothing fetched yet - initial cache state, not a bus error
    assert temperature is None
    assert humidity is None
    assert len(i2c.log) == 0


def test_get_self_calibration_enabled_decodes_1_and_0() -> None:
    scd, i2c = make_scd()
    i2c.read_queue.append(register_frame(1))
    assert run(scd.get_self_calibration_enabled()) is True
    i2c.read_queue.append(register_frame(0))
    assert run(scd.get_self_calibration_enabled()) is False


# ---------------------------------------------------------------------------
# Module level: real bus faults (OSError) propagate uncaught - SCD30_I2C is the documented
# "allowed to raise" layer (src/README.md's raw-bus-call carve-out).
# ---------------------------------------------------------------------------


def test_nak_propagates_as_oserror_from_every_write_based_command() -> None:
    scd, i2c = make_scd()
    i2c.nak_addresses.add(_ADDR)
    for bad_call in (
        scd.set_measurement_interval(10),
        scd.set_ambient_pressure(1000),
        scd.set_altitude(100),
        scd.set_temperature_offset(1.0),
        scd.set_forced_recalibration_reference(500),
        scd.set_self_calibration_enabled(True),
        scd.stop_continuous_measurement(),
        scd.reset(),
    ):
        try:
            run(bad_call)
            raised = False
        except OSError:
            raised = True
        assert raised


def test_nak_propagates_as_oserror_from_every_register_read() -> None:
    scd, i2c = make_scd()
    i2c.nak_addresses.add(_ADDR)
    for bad_call in (
        scd.get_measurement_interval(),
        scd.get_ambient_pressure(),
        scd.get_altitude(),
        scd.get_temperature_offset(),
        scd.get_forced_recalibration_reference(),
        scd.get_self_calibration_enabled(),
        scd.read_measurement(),
    ):
        try:
            run(bad_call)
            raised = False
        except OSError:
            raised = True
        assert raised


def test_nak_never_reaches_get_co2_temperature_humidity_pure_cache_reads() -> None:
    # Unlike every other getter above, get_CO2()/get_temperature()/get_relative_humidity() never
    # touch the bus themselves (see their own comments) - a NAK'd bus must not make them raise,
    # it should just mean they keep returning whatever's cached (None here, nothing fetched yet).
    scd, i2c = make_scd()
    i2c.nak_addresses.add(_ADDR)
    assert run(scd.get_CO2()) is None
    assert run(scd.get_temperature()) is None
    assert run(scd.get_relative_humidity()) is None


def test_bus_busy_timeout_propagates_as_oserror() -> None:
    scd, i2c = make_scd()
    i2c.busy = True
    try:
        run(scd.get_measurement_interval())
        raised = False
    except OSError:
        raised = True
    assert raised


def test_fault_injected_read_half_failure_after_a_successful_write_half() -> None:
    # Models a transfer interrupted partway through: the write leg (command bytes) succeeds, then
    # the read leg (response) fails - a real bus condition (e.g. a device reset mid-transaction).
    scd, i2c = make_scd()
    i2c.inject_fault("readfrom_into", OSError(5, "read half failed"))
    try:
        run(scd.get_measurement_interval())
        raised = False
    except OSError:
        raised = True
    assert raised
    assert i2c.log[0][0] == "writeto"  # the write half really did complete first


# ---------------------------------------------------------------------------
# Module level: setup()/reset() - identity check, then soft reset with the real ~2.5s documented
# delay. Kept to two tests (the delay is real elapsed time, not simulated) rather than exercised
# from every angle at this layer.
# ---------------------------------------------------------------------------


def test_setup_probes_reads_firmware_version_then_soft_resets() -> None:
    scd, i2c = make_scd()
    i2c.read_queue.append(register_frame(0x0301))
    run(scd.setup())
    ops = [entry[0] for entry in i2c.log]
    assert ops == ["writeto", "writeto", "readfrom_into", "writeto"]
    assert i2c.log[0][2] == b""  # I2CDevice.setup()'s device-presence probe
    assert i2c.log[1][2] == bytes([0xD1, 0x00])  # _CMD_READ_FIRMWARE_VERSION
    assert i2c.log[-1][2] == bytes([0xD3, 0x04])  # _CMD_SOFT_RESET


def test_setup_probe_failure_never_reaches_firmware_read_or_reset() -> None:
    scd, i2c = make_scd()
    i2c.nak_addresses.add(_ADDR)
    try:
        run(scd.setup())
        raised = False
    except (OSError, ValueError, RuntimeError):
        raised = True
    assert raised
    assert len(i2c.log) == 0  # probe failed before any command bytes were even written


# ===========================================================================
# Integration level: SCD30_Reader wired to the real asy_i2c_driver.I2C/I2CDevice,
# base_classes.SensorReader, and print_log.PrintLogHistory - only the raw I2C bus is mocked.
# ===========================================================================


def test_reader_init_constructs_a_real_input_pin_and_leaves_timer_unarmed() -> None:
    reader = make_reader()
    assert reader.irq_pin.mode == FakePin.IN
    assert reader.start_trigger_timer.deinit_called is False


def test_reader_start_timer_arms_periodic_timer_and_pin_irq() -> None:
    FakeTimer.all_timers.clear()
    reader = make_reader()
    reader.start_timer()
    assert reader.start_trigger_timer.period == 500
    assert reader.start_trigger_timer.mode == FakeTimer.PERIODIC
    assert reader.irq_pin._irq_trigger == FakePin.IRQ_RISING

    reader.start_trigger_timer.trigger()
    reader.irq_pin.trigger_irq()

    async def scenario() -> None:
        await asyncio.wait_for(reader.start_trigger_event.wait(), 1)
        await asyncio.wait_for(reader.irq_trigger_event.wait(), 1)

    run(scenario())
    FakeTimer.all_timers.clear()


def test_reader_stop_timer_deinits_the_periodic_timer_only() -> None:
    FakeTimer.all_timers.clear()
    reader = make_reader()
    reader.start_timer()
    reader.stop_timer()
    assert reader.start_trigger_timer.deinit_called is True
    FakeTimer.all_timers.clear()


def test_reader_get_task_starters_and_timer_starters_shape() -> None:
    reader = make_reader()
    task_starters = reader.get_task_starters()
    timer_starters = reader.get_timer_starters()
    assert task_starters == [reader.start_asy_read, reader.start_asy_init]
    assert timer_starters == [reader.start_timer]


def test_scd_init_irq_sets_irq_trigger_after_enough_consecutive_stuck_ticks() -> None:
    reader = make_reader(trigger_sec=3)  # trigger_half_sec = 2*3 = 6
    reader.irq_pin.value(1)  # IRQ pin stuck HIGH - sensor never actually got read

    async def scenario() -> "tuple[bool, bool]":
        task = asyncio.create_task(reader.scd_init_irq())
        for _ in range(5):
            reader.start_trigger_event.set()
            await _settle(3)
        not_yet = True
        try:
            await asyncio.wait_for(reader.irq_trigger_event.wait(), 0)
            not_yet = False
        except asyncio.TimeoutError:
            pass
        reader.start_trigger_event.set()
        await _settle(3)
        triggered = False
        try:
            await asyncio.wait_for(reader.irq_trigger_event.wait(), 1)
            triggered = True
        except asyncio.TimeoutError:
            pass
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return not_yet, triggered

    not_yet, triggered = run(scenario())
    assert not_yet is True
    assert triggered is True


def test_scd_init_irq_never_triggers_while_pin_reads_low() -> None:
    reader = make_reader(trigger_sec=1)  # trigger_half_sec = 2
    reader.irq_pin.value(0)  # sensor is being read normally - pin never stuck high

    async def scenario() -> bool:
        task = asyncio.create_task(reader.scd_init_irq())
        for _ in range(10):
            reader.start_trigger_event.set()
            await _settle(3)
        triggered = True
        try:
            await asyncio.wait_for(reader.irq_trigger_event.wait(), 0)
        except asyncio.TimeoutError:
            triggered = False
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return triggered

    assert run(scenario()) is False


# ---------------------------------------------------------------------------
# Integration: every public getter/setter, real fault propagation through print_log/base_classes -
# an OSError (bus NAK), a RuntimeError (CRC), and an AttributeError (bad range) must all surface as
# None (getters) / False (setters), never leak past the Reader.
# ---------------------------------------------------------------------------


def test_reader_getters_return_none_on_bus_nak() -> None:
    reader = make_reader()
    reader_fake_i2c(reader).nak_addresses.add(_ADDR)

    async def scenario() -> "tuple[Any, ...]":
        return (
            await reader.get_measurement_interval(),
            await reader.get_self_calibration_enabled(),
            await reader.get_ambient_pressure(),
            await reader.get_altitude(),
            await reader.get_temperature_offset(),
            await reader.get_forced_recalibration_reference(),
        )

    assert run(scenario()) == (None, None, None, None, None, None)


def test_reader_setters_return_false_on_bus_nak() -> None:
    reader = make_reader()
    reader_fake_i2c(reader).nak_addresses.add(_ADDR)

    async def scenario() -> "tuple[bool, ...]":
        return (
            await reader.set_measurement_interval(10),
            await reader.set_self_calibration_enabled(True),
            await reader.set_ambient_pressure(1000),
            await reader.set_altitude(100),
            await reader.set_temperature_offset(1.0),
            await reader.set_forced_recalibration_reference(500),
        )

    assert run(scenario()) == (False, False, False, False, False, False)


def test_reader_setters_return_false_on_invalid_range_not_just_bus_faults() -> None:
    # The AttributeError SCD30_I2C raises for an out-of-range argument must be absorbed exactly
    # like a bus fault - same False return, no special-casing.
    reader = make_reader()

    async def scenario() -> "tuple[bool, ...]":
        return (
            await reader.set_measurement_interval(1),
            await reader.set_ambient_pressure(1),
            await reader.set_altitude(-1),
            await reader.set_temperature_offset(-1.0),
            await reader.set_forced_recalibration_reference(1),
        )

    assert run(scenario()) == (False, False, False, False, False)


def test_reader_getters_return_none_on_crc_mismatch() -> None:
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    corrupted = bytearray(register_frame(999))
    corrupted[-1] ^= 0xFF
    for _ in range(6):
        i2c.read_queue.append(bytes(corrupted))

    async def scenario() -> "tuple[Any, ...]":
        return (
            await reader.get_measurement_interval(),
            await reader.get_self_calibration_enabled(),
            await reader.get_ambient_pressure(),
            await reader.get_altitude(),
            await reader.get_temperature_offset(),
            await reader.get_forced_recalibration_reference(),
        )

    assert run(scenario()) == (None, None, None, None, None, None)


def test_reader_set_then_get_altitude_round_trips_through_real_i2c_frames() -> None:
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    # Queued upfront, not from inside scenario(): register_frame() calls run()/asyncio.run()
    # itself (via crc8_byte()), and nesting that inside a coroutine already driven by an outer
    # run(scenario()) segfaults the MicroPython Unix port instead of raising cleanly - a real
    # difference from CPython's asyncio.run(), which just raises RuntimeError for the same misuse.
    i2c.read_queue.append(register_frame(321))

    async def scenario() -> "tuple[bool, int | None]":
        ok = await reader.set_altitude(321)
        value = await reader.get_altitude()
        return ok, value

    ok, value = run(scenario())
    assert ok is True
    assert value == 321


def test_reader_stop_continuous_measurement_true_is_a_pure_noop() -> None:
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    assert run(reader.stop_continuous_measurement(True)) is False
    assert len(i2c.log) == 0


def test_reader_stop_continuous_measurement_false_sends_the_real_stop_command() -> None:
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    assert run(reader.stop_continuous_measurement(False)) is True
    assert i2c.log[-1] == ("writeto", _ADDR, bytes([0x01, 0x04]), True)


def test_reader_stop_continuous_measurement_false_returns_false_on_bus_fault() -> None:
    reader = make_reader()
    reader_fake_i2c(reader).nak_addresses.add(_ADDR)
    assert run(reader.stop_continuous_measurement(False)) is False


# ---------------------------------------------------------------------------
# Integration: get_dict_cfg()/get_dict_data() through the real config_manager.make_dict/name_cfg
# ---------------------------------------------------------------------------


def test_get_dict_cfg_reports_every_schema_field_by_name() -> None:
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    i2c.read_queue.append(register_frame(450))  # TempOffs
    i2c.read_queue.append(register_frame(10))  # MeasInt
    i2c.read_queue.append(register_frame(1000))  # AmbPres
    i2c.read_queue.append(register_frame(200))  # Altitude
    i2c.read_queue.append(register_frame(400))  # ForceCalRef
    i2c.read_queue.append(register_frame(1))  # SelfCal

    result = run(reader.get_dict_cfg())
    fields = result["SCD30"]
    assert fields["TempOffs"] == 4.5
    assert fields["MeasInt"] == 10
    assert fields["AmbPres"] == 1000
    assert fields["Altitude"] == 200
    assert fields["ForceCalRef"] == 400
    assert fields["SelfCal"] is True


def test_get_dict_cfg_degrades_to_none_per_field_on_bus_fault_not_a_crash() -> None:
    reader = make_reader()
    reader_fake_i2c(reader).nak_addresses.add(_ADDR)
    result = run(reader.get_dict_cfg())
    fields = result["SCD30"]
    assert fields == {
        "TempOffs": None,
        "MeasInt": None,
        "AmbPres": None,
        "Altitude": None,
        "ForceCalRef": None,
        "SelfCal": None,
    }


def test_get_dict_data_reports_measured_values_by_name() -> None:
    reader = make_reader()
    data = SCD30(400.0, 20.0, 50.0, 15.2, 9.3, 123456)
    run(reader._set_meas_data(data))
    result = run(reader.get_dict_data())
    assert result["SCD30"]["CO2"] == 400.0
    assert result["SCD30"]["Temp"] == 20.0
    assert result["SCD30"]["Hum"] == 50.0
    assert result["SCD30"]["TS"] == 123456


def test_get_error_counter_forwards_to_the_real_print_log() -> None:
    reader = make_reader()
    log = run(reader.get_error_counter())
    assert log["SCD30"]["ErrCount"] == 0


# ---------------------------------------------------------------------------
# Integration: _init_scd() / read_loop() - real base_classes.SensorReader + print_log wiring.
# scd.setup()'s own I2C behavior is independently covered above; here it's monkeypatched to a fast
# no-op so these tests focus on read_loop()'s own orchestration (IRQ-driven trigger, error
# counting, data storage) without re-paying its real ~2.5s reset delay each time.
# ---------------------------------------------------------------------------


async def _fake_setup() -> None:
    return None


def test_init_scd_returns_false_immediately_when_probe_fails_no_reset_reached() -> None:
    reader = make_reader()
    reader_fake_i2c(reader).nak_addresses.add(_ADDR)
    assert run(reader._init_scd()) is False


def test_read_loop_full_iteration_stores_measured_data_and_derived_values() -> None:
    reader = make_reader(max_i2c_err=1)
    reader.scd.setup = _fake_setup  # type: ignore[method-assign]
    # read_measurement() is the one call that can raise post-fix; get_CO2()/get_temperature()/
    # get_relative_humidity() are pure cache reads (see src/asy_scd30_driver.py's own comment on
    # why they must never independently re-check data-ready) - faked as a no-op success plus fixed
    # cache values, matching that real shape instead of the pre-fix "each getter fetches" one.
    reader.scd.read_measurement = _fake_setup  # type: ignore[method-assign]

    async def fake_co2() -> float:
        return 500.0

    async def fake_temp() -> float:
        return 21.0

    async def fake_hum() -> float:
        return 40.0

    reader.scd.get_CO2 = fake_co2  # type: ignore[method-assign]
    reader.scd.get_temperature = fake_temp  # type: ignore[method-assign]
    reader.scd.get_relative_humidity = fake_hum  # type: ignore[method-assign]

    async def scenario() -> SCD30:
        task = asyncio.create_task(reader.read_loop())
        await _settle(5)
        reader.irq_trigger_event.set()
        await _settle(5)
        data = await reader.get_data()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return data

    data = run(scenario())
    assert data.CO2 == 500.0
    assert data.Temp == 21.0
    assert data.Hum == 40.0
    assert data.TS is not None
    assert data.WetBulb is not None
    assert data.DewPoint is not None


def test_read_loop_gives_up_after_max_i2c_err_consecutive_failures_and_logs_via_real_print_log() -> None:
    reader = make_reader(max_i2c_err=1)
    reader.scd.setup = _fake_setup  # type: ignore[method-assign]

    async def fake_fail() -> None:
        raise OSError(5, "nak")

    # Faked on read_measurement() itself, the real single fault point post-fix - the getters are
    # never reached once it raises, so they're left as the real (pure cache-read) implementation;
    # read_measurement()'s own protocol-level fault handling is covered separately above.
    reader.scd.read_measurement = fake_fail  # type: ignore[method-assign]

    async def scenario() -> bool:
        task = asyncio.create_task(reader.read_loop())
        await _settle(5)
        for _ in range(4):
            if task.done():
                break
            reader.irq_trigger_event.set()
            await _settle(5)
        return await task

    result = run(scenario())
    assert result is False
    log = run(reader.get_error_counter())
    err_count = log["SCD30"]["ErrCount"]
    assert isinstance(err_count, int)
    assert err_count >= 2  # two consecutive failures exceed max_i2c_err=1


def test_read_loop_recovers_error_counter_after_a_good_read_following_failures() -> None:
    reader = make_reader(max_i2c_err=5)
    reader.scd.setup = _fake_setup  # type: ignore[method-assign]
    fail_next = [True, True, False]

    async def flaky_read_measurement() -> None:
        if fail_next.pop(0):
            raise OSError(5, "nak")

    reader.scd.read_measurement = flaky_read_measurement  # type: ignore[method-assign]

    async def fake_co2() -> float:
        return 500.0

    async def fake_ok() -> float:
        return 1.0

    reader.scd.get_CO2 = fake_co2  # type: ignore[method-assign]
    reader.scd.get_temperature = fake_ok  # type: ignore[method-assign]
    reader.scd.get_relative_humidity = fake_ok  # type: ignore[method-assign]

    async def scenario() -> "SCD30 | None":
        task = asyncio.create_task(reader.read_loop())
        await _settle(5)
        for _ in range(3):
            reader.irq_trigger_event.set()
            await _settle(5)
        data = await reader.get_data()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return data

    data = run(scenario())
    assert data is not None
    assert data.CO2 == 500.0  # the third, successful read is what ends up stored


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
