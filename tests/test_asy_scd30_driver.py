"""Unit + integration tests for asy_scd30_driver.py (src/).
Module-level tests exercise SCD30_I2C against tests/machine.py's fake I2C/Pin, cross-checked byte-for-byte against the Interface Description's own worked examples (datasheets/scd30/).
Integration-level tests wire SCD30_Reader to the real asy_i2c_driver.py/base_classes.py/print_log.py - no mocking above the raw I2C bus.
"""
# Integration tests cover how a real OSError (bus fault) or RuntimeError (CRC mismatch) propagates
# up through the Reader's never-raises wrapper contract and into the real error counter/log.

import asyncio
import struct

from machine import I2C as FakeI2C
from machine import Pin as FakePin
from machine import Timer as FakeTimer

import config_manager as cm
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


def make_reader(trigger_sec: int = 3, max_module_error: int = 5) -> SCD30_Reader:
    return SCD30_Reader(make_i2c(), irq_pin=5, trigger_sec=trigger_sec, max_module_error=max_module_error)


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


class _FastAsyncSleep:
    # _read_dev_register()/_send_dev_command() each make real 0.05s asyncio.sleep() calls - fine for
    # a directly-`run()`-awaited coroutine, but far too slow for a test driving get_config_snapshot()
    # as a background task through a bounded sleep(0) pump loop (same technique as
    # test_asy_bmp3xx_driver.py's own _FastAsyncSleep). asyncio.sleep is a shared, process-wide
    # function, restored on exit regardless of how the `with` block exits.
    def __enter__(self) -> "_FastAsyncSleep":
        self._real_sleep = asyncio.sleep

        async def _fast(_seconds: float) -> None:
            await self._real_sleep(0)

        asyncio.sleep = _fast  # type: ignore[assignment]  # deliberate monkeypatch, not a real caller mismatch
        return self

    def __exit__(self, *exc_info: object) -> None:
        asyncio.sleep = self._real_sleep


class _RaiseOnArm:
    # Same technique as test_system_service.py's/test_asy_wifi_service.py's own _RaiseOnArm -
    # toggles tests/machine.py's Timer.raise_on_arm (a shared class attribute, not per-instance)
    # for the duration of the `with` block, simulating a real rp2 Timer.init() that can't arm.
    # `exc` picks which of start_timer()'s two guarded arms gets exercised: the default
    # OSError(ENOMEM) alarm-pool-exhaustion one, or the MemoryError one a failed allocation raises
    # instead (see tests/machine.py's Timer.raise_on_arm_exc). Both class attributes are restored
    # on exit regardless of how the block exits.
    def __init__(self, exc: "type[BaseException]" = OSError) -> None:
        self._exc = exc

    def __enter__(self) -> "_RaiseOnArm":
        FakeTimer.raise_on_arm_exc = self._exc
        FakeTimer.raise_on_arm = True
        return self

    def __exit__(self, *exc_info: object) -> None:
        FakeTimer.raise_on_arm = False
        FakeTimer.raise_on_arm_exc = OSError


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


def _raises_value_error(coro: "Coroutine[Any, Any, None]") -> bool:
    try:
        run(coro)
    except ValueError:
        return True
    return False


def test_set_measurement_interval_boundaries() -> None:
    scd, _ = make_scd()
    assert _raises_value_error(scd.set_measurement_interval(1))
    assert _raises_value_error(scd.set_measurement_interval(1801))
    assert not _raises_value_error(scd.set_measurement_interval(2))
    assert not _raises_value_error(scd.set_measurement_interval(1800))
    assert not _raises_value_error(scd.set_measurement_interval(900))


def test_set_ambient_pressure_boundaries() -> None:
    scd, _ = make_scd()
    assert _raises_value_error(scd.set_ambient_pressure(699))
    assert _raises_value_error(scd.set_ambient_pressure(1401))
    assert not _raises_value_error(scd.set_ambient_pressure(0))  # special "disable" value
    assert not _raises_value_error(scd.set_ambient_pressure(700))
    assert not _raises_value_error(scd.set_ambient_pressure(1400))
    assert not _raises_value_error(scd.set_ambient_pressure(1013))


def test_set_ambient_pressure_rejects_values_just_inside_the_dead_zone_around_zero() -> None:
    # 0 is the one special value below 700 that's valid - 1 through 699 must all still raise.
    scd, _ = make_scd()
    assert _raises_value_error(scd.set_ambient_pressure(1))
    assert _raises_value_error(scd.set_ambient_pressure(699))


def test_set_ambient_pressure_rejects_fractional_values_that_would_truncate_to_the_special_zero() -> None:
    # Regression test for a real bug found during re-review: validating against pressure_mbar
    # *after* int()-truncating it let any value in the open interval (-1, 0) - e.g. -0.5 - silently
    # through as the special "disable" value 0, instead of being rejected, since int(-0.5) == 0
    # (Python/MicroPython int() truncates toward zero, it doesn't round). Confirmed directly
    # against the real interpreter before fixing: set_ambient_pressure(-0.5) used to send a real
    # "disable ambient pressure" command to the sensor with no error raised at all.
    scd, i2c = make_scd()
    for bad in (-0.5, -0.01, -0.999):
        assert _raises_value_error(scd.set_ambient_pressure(bad)), f"{bad} should have raised"
    assert len(i2c.log) == 0  # none of the rejected calls should have reached the bus


def test_set_ambient_pressure_rejects_nan() -> None:
    # NaN compares False against every bound in the range check (never > or < anything), so
    # without an explicit check it would silently reach int(pressure_mbar) instead of being
    # rejected by the guard clause itself - see asy_scd30_driver.py's own comment.
    scd, i2c = make_scd()
    assert _raises_value_error(scd.set_ambient_pressure(float("nan")))
    assert len(i2c.log) == 0


def test_set_altitude_boundaries() -> None:
    scd, _ = make_scd()
    assert _raises_value_error(scd.set_altitude(-1))
    assert _raises_value_error(scd.set_altitude(65536))
    assert not _raises_value_error(scd.set_altitude(0))
    assert not _raises_value_error(scd.set_altitude(65535))
    assert not _raises_value_error(scd.set_altitude(1000))


def test_set_altitude_rejects_fractional_values_that_would_truncate_to_zero() -> None:
    # Same class of bug as set_ambient_pressure's own regression test above: int(-0.5) == 0, which
    # is itself a valid altitude (sea level) - so truncating before validating would have silently
    # accepted a negative altitude as "0m" instead of rejecting it. altitude's signature only
    # advertises int (unlike pressure_mbar's explicit int | float), but nothing stops a caller from
    # passing a float anyway - defensive test, deliberately outside the declared type.
    scd, i2c = make_scd()
    for bad in (-0.5, -0.01, -0.999):
        assert _raises_value_error(scd.set_altitude(bad)), f"{bad} should have raised"  # type: ignore[arg-type]
    assert len(i2c.log) == 0


def test_set_temperature_offset_boundaries() -> None:
    scd, _ = make_scd()
    assert _raises_value_error(scd.set_temperature_offset(-0.01))
    assert _raises_value_error(scd.set_temperature_offset(655.36))
    assert not _raises_value_error(scd.set_temperature_offset(0.0))
    assert not _raises_value_error(scd.set_temperature_offset(655.35))
    assert not _raises_value_error(scd.set_temperature_offset(5.0))


def test_set_temperature_offset_rejects_nan() -> None:
    # Same NaN gap as set_ambient_pressure's own regression test above.
    scd, i2c = make_scd()
    assert _raises_value_error(scd.set_temperature_offset(float("nan")))
    assert len(i2c.log) == 0


def test_set_forced_recalibration_reference_boundaries() -> None:
    scd, _ = make_scd()
    assert _raises_value_error(scd.set_forced_recalibration_reference(399))
    assert _raises_value_error(scd.set_forced_recalibration_reference(2001))
    assert not _raises_value_error(scd.set_forced_recalibration_reference(400))
    assert not _raises_value_error(scd.set_forced_recalibration_reference(2000))
    assert not _raises_value_error(scd.set_forced_recalibration_reference(450))


def test_invalid_setter_call_does_not_corrupt_state_for_a_later_valid_call() -> None:
    # Multiple invalid-parameter recombinations in sequence, on one shared instance/buffer, then a
    # real valid call afterwards - the shared self._buffer must not be left in a state that
    # corrupts a subsequent, unrelated, valid command.
    scd, i2c = make_scd()
    assert _raises_value_error(scd.set_altitude(-1))
    assert _raises_value_error(scd.set_temperature_offset(-1.0))
    assert _raises_value_error(scd.set_forced_recalibration_reference(100))
    assert _raises_value_error(scd.set_measurement_interval(0))
    assert _raises_value_error(scd.set_ambient_pressure(1))
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
        assert _raises_value_error(bad_call)
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


def test_read_measurement_not_ready_leaves_cached_values_untouched_and_issues_no_measurement_read() -> None:
    # Matches the legacy driver's own proven behavior: a not-ready read_measurement() call must
    # neither raise nor clear the cache - it just leaves whatever was last read in place. Reverted
    # from an earlier "clear to None" version per project-owner direction; see BACKLOG.md.
    scd, i2c = make_scd()
    scd._co2, scd._temperature, scd._relative_humidity = 1.0, 2.0, 3.0
    i2c.read_queue.append(register_frame(0))
    run(scd.read_measurement())
    assert scd._co2 == 1.0
    assert scd._temperature == 2.0
    assert scd._relative_humidity == 3.0
    ops = [entry[0] for entry in i2c.log]
    assert ops == ["writeto", "readfrom_into"]  # only the data-ready probe, no measurement read


def test_read_measurement_never_ran_yet_leaves_getters_at_their_initial_none() -> None:
    # The untouched-on-not-ready behavior must not be confused with "always returns stale data" -
    # before the first successful read_measurement() ever runs, the cache is still None (__init__'s
    # own default), not some leftover garbage value.
    scd, i2c = make_scd()
    i2c.read_queue.append(register_frame(0))
    run(scd.read_measurement())
    assert scd._co2 is None
    assert scd._temperature is None
    assert scd._relative_humidity is None


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
# "allowed to raise" layer (SPECIFICATION.md Part D.2's raw-bus-call carve-out).
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


def test_reader_start_timer_degrades_gracefully_when_the_trigger_timer_cannot_be_armed() -> None:
    # Real rp2 Timer.init() raises OSError(ENOMEM) when the alarm pool is exhausted (confirmed
    # against ports/rp2/machine_timer.c) - start_timer() must log via self.pr.err() and return
    # normally, since its caller is system_service.py's synchronous start_timers() sequencer:
    # raising here would take down the whole timer-start chain over one sensor's 500ms tick.
    FakeTimer.all_timers.clear()
    reader = make_reader()
    with _RaiseOnArm():
        reader.start_timer()  # must not raise despite the timer failing to arm
    assert reader.start_trigger_timer.period == -1  # never actually armed
    assert reader.start_trigger_timer.callback is None  # nothing wired to start_trigger_event
    # start_timer() is synchronous, so it logs via the plain, non-counting pr.err() rather than
    # awaiting pr.err_s() - this failure prints but is deliberately never recorded as a numbered
    # error in the counter, unlike every err_s() call site in this driver.
    assert run(reader.get_error_counter())["SCD30"]["ErrCount"] == 0

    # The pin IRQ is wired after the guarded try/except, so a timer that failed to arm must not
    # cost the sensor its data-ready interrupt as well - that IRQ, not the timer, is what actually
    # triggers a measurement read (the timer only drives scd_init_irq()'s stuck-pin watchdog).
    assert reader.irq_pin._irq_trigger == FakePin.IRQ_RISING
    reader.irq_pin.trigger_irq()

    async def scenario() -> None:
        await asyncio.wait_for(reader.irq_trigger_event.wait(), 1)

    run(scenario())
    FakeTimer.all_timers.clear()


def test_reader_start_timer_degrades_gracefully_on_a_memory_error_while_arming() -> None:
    # MemoryError is not an OSError subclass (see SPECIFICATION.md Part F), so start_timer()'s
    # `except (OSError, MemoryError)` needs that second arm spelled out explicitly - without it, a
    # heap-exhausted arming attempt would propagate straight out of this synchronous starter
    # instead of degrading the same way the ENOMEM case above does (pin IRQ included).
    FakeTimer.all_timers.clear()
    reader = make_reader()
    with _RaiseOnArm(MemoryError):
        reader.start_timer()  # must not raise despite the timer failing to arm
    assert reader.start_trigger_timer.period == -1  # never actually armed
    assert reader.start_trigger_timer.callback is None
    assert reader.irq_pin._irq_trigger == FakePin.IRQ_RISING
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
# an OSError (bus NAK), a RuntimeError (CRC), and a ValueError (bad range) must all surface as
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


def test_reader_getters_log_the_correct_errno_on_bus_nak() -> None:
    # Regression test for the getter forwards' own pr.err_s() logging (added alongside the
    # setters' below) - errno values per asy_scd30_driver.py's own forward-logging block, matching
    # SPECIFICATION.md Part C.7's documented convention that every forward logs, not just returns a sentinel.
    reader = make_reader()
    reader_fake_i2c(reader).nak_addresses.add(_ADDR)

    async def scenario() -> dict:
        await reader.get_measurement_interval()
        await reader.get_self_calibration_enabled()
        await reader.get_ambient_pressure()
        await reader.get_altitude()
        await reader.get_temperature_offset()
        await reader.get_forced_recalibration_reference()
        return await reader.get_error_counter()

    log = run(scenario())["SCD30"]
    # History is a fixed-length deque (default history_length=10), left-padded with "no error"
    # sentinels until it fills - only the trailing entries are this scenario's own 6 calls.
    assert log["ErrNum"][-6:] == [14, 16, 18, 20, 22, 24]
    assert log["ErrType"][-6:] == ["E", "E", "E", "E", "E", "E"]


def test_reader_setters_log_the_correct_errno_on_bus_nak() -> None:
    reader = make_reader()
    reader_fake_i2c(reader).nak_addresses.add(_ADDR)

    async def scenario() -> dict:
        await reader.set_measurement_interval(10)
        await reader.set_self_calibration_enabled(True)
        await reader.set_ambient_pressure(1000)
        await reader.set_altitude(100)
        await reader.set_temperature_offset(1.0)
        await reader.set_forced_recalibration_reference(500)
        return await reader.get_error_counter()

    log = run(scenario())["SCD30"]
    assert log["ErrNum"][-6:] == [15, 17, 19, 21, 23, 25]
    assert log["ErrType"][-6:] == ["E", "E", "E", "E", "E", "E"]


def test_reader_setters_return_false_on_invalid_range_not_just_bus_faults() -> None:
    # The ValueError SCD30_I2C raises for an out-of-range argument must be absorbed exactly
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

    async def scenario() -> "tuple[bool, dict]":
        ok = await reader.stop_continuous_measurement(False)
        return ok, await reader.get_error_counter()

    ok, log = run(scenario())
    assert ok is False
    assert log["SCD30"]["ErrNum"][-1] == 13


def test_set_dict_cfg_reports_contmeas_true_as_valid_not_failed() -> None:
    # Regression test: stop_continuous_measurement(True)'s own contract returns False for its
    # pure-no-op case (see test_reader_stop_continuous_measurement_true_is_a_pure_noop above), and
    # a first version of this method's ContMeas dispatch forwarded that return value straight into
    # the generic "Valid"/"Failed" mapping, unlike improved-quality/sensortask-wozi.py's own removed
    # _push_cont_meas wrapper - reporting a real client's ContMeas=True (the field's own default,
    # "keep measuring") as "Failed" even though nothing failed. Never caught by any prior test since
    # nothing exercised _set_dict_cfg's own ContMeas branch specifically.
    reader = make_reader()
    reader_fake_i2c(reader)
    result = run(reader._set_dict_cfg({"ContMeas": True}, reader.get_cfg_schema()))
    assert result == {"ContMeas": "Valid"}


def test_set_dict_cfg_reports_contmeas_false_as_valid_when_the_real_stop_succeeds() -> None:
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    result = run(reader._set_dict_cfg({"ContMeas": False}, reader.get_cfg_schema()))
    assert result == {"ContMeas": "Valid"}
    assert i2c.log[-1] == ("writeto", _ADDR, bytes([0x01, 0x04]), True)


def test_set_dict_cfg_reports_contmeas_false_as_failed_on_bus_fault() -> None:
    reader = make_reader()
    reader_fake_i2c(reader).nak_addresses.add(_ADDR)
    result = run(reader._set_dict_cfg({"ContMeas": False}, reader.get_cfg_schema()))
    assert result == {"ContMeas": "Failed"}


def test_set_dict_cfg_reports_contmeas_non_bool_as_invalid() -> None:
    reader = make_reader()
    reader_fake_i2c(reader)
    result = run(reader._set_dict_cfg({"ContMeas": "yes"}, reader.get_cfg_schema()))
    assert result == {"ContMeas": "Invalid"}


# ---------------------------------------------------------------------------
# _set_dict_cfg - schema-driven int/float dispatch loop (TempOffs/MeasInt/AmbPres/Altitude/
# ForceCalRef/SelfCal), distinct from the ContMeas special-case tests above: this is the branch
# that calls config_manager.py's type_or_range_error() (coercion included, SPECIFICATION.md Part
# A.8) before dispatching to each field's own real setter. Never exercised at all before this.
# ---------------------------------------------------------------------------


def test_set_dict_cfg_dispatches_a_valid_value_to_the_real_setter_and_reports_valid() -> None:
    reader = make_reader()
    reader_fake_i2c(reader)
    result = run(reader._set_dict_cfg({"TempOffs": 4.5}, reader.get_cfg_schema()))
    assert result == {"TempOffs": "Valid"}


def test_set_dict_cfg_int_value_for_the_float_typed_tempoffs_field_is_coerced_before_dispatch() -> None:
    # TempOffs is float-typed - a plain int PUT value must be coerced to float by
    # type_or_range_error() before ever reaching set_temperature_offset(), not passed through as
    # the raw int (both are structurally acceptable to the setter's own int|float signature, so
    # only inspecting the actual argument received - via this spy - proves coercion really ran).
    reader = make_reader()
    reader_fake_i2c(reader)
    received = []

    async def spy(offset: "int | float") -> bool:
        received.append(offset)
        return True

    reader.set_temperature_offset = spy  # type: ignore[method-assign]
    result = run(reader._set_dict_cfg({"TempOffs": 5}, reader.get_cfg_schema()))
    assert result == {"TempOffs": "Valid"}
    assert received == [5.0]
    assert type(received[0]) is float


def test_set_dict_cfg_integral_float_value_for_the_int_typed_measint_field_is_coerced_before_dispatch() -> None:
    # Mirror of the test above, in the other direction: MeasInt is int-typed - an integral float PUT
    # value must be coerced to int before reaching set_measurement_interval().
    reader = make_reader()
    reader_fake_i2c(reader)
    received = []

    async def spy(value: int) -> bool:
        received.append(value)
        return True

    reader.set_measurement_interval = spy  # type: ignore[method-assign]
    result = run(reader._set_dict_cfg({"MeasInt": 10.0}, reader.get_cfg_schema()))
    assert result == {"MeasInt": "Valid"}
    assert received == [10]
    assert type(received[0]) is int


def test_set_dict_cfg_fractional_value_for_an_int_typed_field_rejected_before_dispatch() -> None:
    reader = make_reader()
    reader_fake_i2c(reader)
    received = []

    async def spy(value: int) -> bool:
        received.append(value)
        return True

    reader.set_measurement_interval = spy  # type: ignore[method-assign]
    result = run(reader._set_dict_cfg({"MeasInt": 10.5}, reader.get_cfg_schema()))
    assert result == {"MeasInt": "Invalid"}
    assert received == []  # never dispatched - rejected before the setter is ever called


def test_set_dict_cfg_out_of_range_value_rejected_before_dispatch() -> None:
    reader = make_reader()
    reader_fake_i2c(reader)
    result = run(reader._set_dict_cfg({"TempOffs": 9999.0}, reader.get_cfg_schema()))
    assert result == {"TempOffs": "Invalid"}


def test_set_dict_cfg_wrong_type_value_rejected_before_dispatch() -> None:
    reader = make_reader()
    reader_fake_i2c(reader)
    result = run(reader._set_dict_cfg({"TempOffs": "not a number"}, reader.get_cfg_schema()))
    assert result == {"TempOffs": "Invalid"}


def test_set_dict_cfg_unknown_key_reported_invalid_without_dispatch() -> None:
    reader = make_reader()
    reader_fake_i2c(reader)
    result = run(reader._set_dict_cfg({"NoSuchField": 5}, reader.get_cfg_schema()))
    assert result == {"NoSuchField": "Invalid"}


def test_set_dict_cfg_setter_reports_failed_on_bus_fault() -> None:
    reader = make_reader()
    reader_fake_i2c(reader).nak_addresses.add(_ADDR)
    result = run(reader._set_dict_cfg({"TempOffs": 4.5}, reader.get_cfg_schema()))
    assert result == {"TempOffs": "Failed"}


def test_set_dict_cfg_multiple_fields_in_one_call_including_ambpres_special_sentinel() -> None:
    # Exercises several dispatch fields together (not just TempOffs in isolation), including
    # AmbPres's own special-value sentinel (0 - deactivate ambient pressure compensation).
    reader = make_reader()
    reader_fake_i2c(reader)
    result = run(reader._set_dict_cfg({"TempOffs": 5, "AmbPres": 0, "SelfCal": True}, reader.get_cfg_schema()))
    assert result == {"TempOffs": "Valid", "AmbPres": "Valid", "SelfCal": "Valid"}


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


def test_get_cfg_schema_returns_every_settable_field_by_name() -> None:
    # Regression test from baseline verification:
    # SCD30_Reader(SensorReader) - unlike every other reader in this codebase (SensorReaderConfig
    # subclasses) - never inherited a get_cfg_schema() method, even though
    # asy_webserver_service.py's _put_sensors() route calls module.get_cfg_schema() uniformly for
    # every registered sensor (this file's own _set_dict_cfg() docstring already documented that
    # exact expectation). Missing it meant a real PUT /sensors touching SCD30 crashed with a 500
    # (AttributeError) - reproduced directly, never caught by any existing test since
    # tests/test_asy_webserver_service.py's own _put_sensors tests use a fake module that already
    # has get_cfg_schema() defined.
    reader = make_reader()
    names = cm.schema_names(reader.get_cfg_schema())
    assert set(names) == {"TempOffs", "MeasInt", "AmbPres", "Altitude", "ForceCalRef", "SelfCal"}


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


def test_get_dict_cfg_snapshot_is_atomic_against_a_concurrent_config_write() -> None:
    # Regression test for BACKLOG.md's torn-read entry: get_dict_cfg()'s six config fields used to
    # be six independently-locked register reads, so a concurrent write (also i2c_scd30-locked)
    # could land between any two of them and produce a dict mixing pre-/post-write values.
    # get_config_snapshot() now holds the device-session lock for the whole batch, so a concurrent
    # write can't even start its own I2C traffic until the whole read has finished - proven here by
    # checking the concurrent write's own writeto() log entry only appears after all 6 of the read's
    # own log entries (2 ops/register: one writeto for the register address, one readfrom_into for
    # the reply).
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    for value in (450, 10, 1000, 200, 400, 1):  # TempOffs, MeasInt, AmbPres, Altitude, ForceCalRef, SelfCal
        i2c.read_queue.append(register_frame(value))

    async def scenario() -> "tuple[dict, list]":
        with _FastAsyncSleep():
            read_task = asyncio.create_task(reader.get_dict_cfg())
            await _settle(3)  # let the read task acquire the lock and begin its first register read
            assert not read_task.done()

            write_task = asyncio.create_task(reader.scd.set_temperature_offset(9.99))
            await _settle(3)  # give the write every chance to run if it weren't blocked by the lock
            assert not write_task.done()  # still blocked - proves the lock is held for the whole batch

            result = await read_task
            await write_task
        return result, list(i2c.log)

    result, log = run(scenario())
    fields = result["SCD30"]
    assert fields["TempOffs"] == 4.5  # the pre-write value, not the concurrent write's 9.99
    read_ops = 12  # 6 registers x (writeto register address, readfrom_into reply)
    # The write's own command frame is 5 bytes (2-byte command + 2-byte data + 1-byte CRC) -
    # distinct from the read's 2-byte register-address probe for the same command code (TempOffs
    # happens to be read first in the batch, so a length-agnostic match would find that probe
    # instead at index 0).
    write_index = next(
        i for i, entry in enumerate(log) if entry[0] == "writeto" and entry[2][:2] == bytes([0x54, 0x03]) and len(entry[2]) == 5
    )
    assert write_index >= read_ops  # the write's own bus traffic never interleaved with the read's


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
    reader = make_reader(max_module_error=1)
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


def test_read_loop_gives_up_after_max_module_error_consecutive_failures_and_logs_via_real_print_log() -> None:
    reader = make_reader(max_module_error=1)
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
    assert err_count >= 2  # two consecutive failures exceed max_module_error=1


def test_read_loop_recovers_error_counter_after_a_good_read_following_failures() -> None:
    reader = make_reader(max_module_error=5)
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


# ---------------------------------------------------------------------------
# Task starters (SPECIFICATION.md Part C.9) - get_task_starters()'s own shape is already checked
# above; neither starter method it returns was ever actually called.
# ---------------------------------------------------------------------------


def test_start_asy_read_returns_a_real_task() -> None:
    reader = make_reader()

    async def scenario() -> bool:
        task = reader.start_asy_read()
        await asyncio.sleep(0)
        is_task = isinstance(task, asyncio.Task)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return is_task

    assert run(scenario()) is True


def test_start_asy_init_returns_a_real_task() -> None:
    reader = make_reader()

    async def scenario() -> bool:
        task = reader.start_asy_init()
        await asyncio.sleep(0)
        is_task = isinstance(task, asyncio.Task)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return is_task

    assert run(scenario()) is True


def test_read_loop_returns_false_when_init_fails() -> None:
    reader = make_reader()
    reader_fake_i2c(reader).nak_addresses.add(_ADDR)
    assert run(reader.read_loop()) is False


# ---------------------------------------------------------------------------
# Reader-level setters' success paths - test_reader_setters_return_false_on_bus_nak/
# _on_invalid_range above only ever exercise the failure branches; only set_altitude has its own
# success-path round-trip test.
# ---------------------------------------------------------------------------


def test_reader_setters_return_true_on_success() -> None:
    reader = make_reader()

    async def scenario() -> "tuple[bool, ...]":
        return (
            await reader.set_measurement_interval(10),
            await reader.set_self_calibration_enabled(True),
            await reader.set_ambient_pressure(1000),
            await reader.set_temperature_offset(1.0),
            await reader.set_forced_recalibration_reference(500),
        )

    assert run(scenario()) == (True, True, True, True, True)


# ---------------------------------------------------------------------------
# SCD30_I2C._send_dev_command()'s CRC-generation guard - a real CRC8 object can't actually fail
# add_into() through any real command this driver sends (always a fixed 2-byte argument, always
# succeeds), so this monkeypatches scd.crc with a minimal fake, the same technique
# test_asy_sgp40_driver.py's own _AlwaysFailCRC/test_asy_uart_driver.py's own _NoneCRC use for their
# own otherwise-unreachable branches.
# ---------------------------------------------------------------------------


class _WrongLengthCRC:
    def length(self) -> int:
        return 1

    async def add_into(self, buffer: bytearray, size: int, start: int = 0, init: "int | None" = None) -> int:
        return 0  # never matches the expected size+crc_length total


def test_send_dev_command_raises_when_crc_generation_produces_the_wrong_length() -> None:
    scd, _i2c = make_scd()
    scd.crc = _WrongLengthCRC()  # type: ignore[assignment]
    try:
        run(scd.set_altitude(100))
        raised = False
    except RuntimeError as e:
        raised = "CRC generation failed" in str(e)
    assert raised


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
