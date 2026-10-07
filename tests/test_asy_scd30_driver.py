"""Unit + integration tests for asy_scd30_driver.py (src/).
Module-level tests exercise SCD30_I2C against tests/machine.py's fake I2C/Pin, cross-checked byte-for-byte against the Interface Description's own worked examples (datasheets/scd30/).
Integration-level tests wire SCD30_Reader to the real asy_i2c_driver.py/asy_base_classes.py/asy_print_log.py - no mocking above the raw I2C bus.
"""
# Integration tests cover how a real OSError (bus fault) or RuntimeError (CRC mismatch) propagates
# up through the Reader's never-raises wrapper contract and into the real error counter/log.

import asyncio
import json
import struct

from _error_codes import code
from _tmp_scratch import TmpScratch
from _write_counters import WriteCountingOpen, scd30_nvm_writes
from machine import I2C as FakeI2C
from machine import Pin as FakePin
from machine import Timer as FakeTimer

import asy_base_classes
import asy_config_manager as cm
import asy_scd30_driver
from asy_crc_checks import CRC8
from asy_i2c_driver import I2C
from asy_print_log import LogConfig, PrintLogHistory
from asy_scd30_driver import SCD30, SCD30_I2C, SCD30_Reader

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine, Sequence
    from typing import Any, TypeVar

    T = TypeVar("T")
    from asy_config_manager import CfgValue, WriteValidity
    from asy_print_log import ErrorLog


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


_ADDR = 0x61  # Interface Description 1.1.1: the address is fixed
# @tunable scd30.start_trigger_period_ms = 500
_START_TRIGGER_PERIOD_MS = 500
# @tunable l1.asy_scd30_driver_event_wait_s = 1
_EVENT_WAIT_S = 1


def make_i2c() -> I2C:
    # A fresh static bus 0 (this tier has no per-test reset), its construction entry dropped so the
    # log holds only the test's own traffic.
    FakeI2C.reset_id(0)
    i2c = I2C(0, scl_pin=1, sda_pin=0, frequency=100000)
    fake(i2c).log.clear()
    return i2c


def fake(i2c: I2C) -> FakeI2C:
    return i2c._i2c  # type: ignore[return-value]


def make_scd() -> "tuple[SCD30_I2C, FakeI2C]":
    i2c = make_i2c()
    scd = SCD30_I2C(i2c)
    return scd, fake(i2c)


_scratch = TmpScratch("scd30")


def make_reader(trigger_s: int = 3, max_module_error: int = 5) -> SCD30_Reader:
    # The reader owns config_SCD30.cfg for its three FRC settings: a scratch directory, set up as at boot.
    reader = SCD30_Reader(make_i2c(), irq_pin=5, trigger_s=trigger_s, max_module_error=max_module_error, cfg_path=_scratch.dir())
    run(reader.setup())
    return reader


def reader_fake_i2c(reader: SCD30_Reader) -> FakeI2C:
    return reader._scd._i2c_scd30.i2c_device.i2c._i2c  # type: ignore[return-value]


def crc8_byte(data: bytes) -> int:
    added = run(CRC8().add(bytearray(data)))
    assert added is not None
    return added[-1]


def register_frame(value: int) -> bytes:
    # 2 data bytes (big-endian, matching >H) + 1 CRC byte over those two - every SCD30 register
    # read reply (Interface Description 1.2, Table 1).
    payload = struct.pack(">H", value)
    return payload + bytes([crc8_byte(payload)])


def _queue_snapshot(i2c: FakeI2C, temp_offset: int = 0, interval: int = 2, pressure: int = 0, altitude: int = 0, frc: int = 400, asc: int = 0) -> None:
    # The six register replies get_config_snapshot() reads, in its order; temp_offset is the raw tick word.
    for value in (temp_offset, interval, pressure, altitude, frc, asc):
        i2c.read_queue.append(register_frame(value))


def _arg_words(i2c: FakeI2C) -> "list[int]":
    # The command word of every 5-byte (command + argument) frame on the bus log, in order.
    return [(entry[2][0] << 8) | entry[2][1] for entry in i2c.log if entry[0] == "writeto" and len(entry[2]) == 5]


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


class _UTCValid:
    # The NTP client's first clock set of the boot, as utc_now() sees it, undone on exit.
    def __enter__(self) -> "_UTCValid":
        asy_base_classes.set_utc_valid()
        return self

    def __exit__(self, *_exc: object) -> None:
        asy_base_classes.set_utc_valid(valid=False)


class _FastAsyncSleep:
    # _read_dev_register()/_send_dev_command() each make a real asyncio.sleep(_CMD_RESPONSE_WAIT_S) - fine for a
    # directly awaited coroutine, far too slow for a test driving get_config_snapshot() through a bounded
    # sleep(0) pump. asyncio.sleep is process-wide, restored however the block exits.
    def __enter__(self) -> "_FastAsyncSleep":
        self._real_sleep = asyncio.sleep

        async def _fast(_seconds: float) -> None:
            await self._real_sleep(0)

        asyncio.sleep = _fast  # type: ignore[assignment]  # deliberate monkeypatch, not a real caller mismatch
        return self

    def __exit__(self, *exc_info: object) -> None:
        asyncio.sleep = self._real_sleep


class _RaiseOnArm:
    # Same technique as the _RaiseOnArm in the asy_system_service/wifi suites - toggles tests/machine.py's
    # shared Timer.raise_on_arm for the `with` block, simulating an rp2 Timer.init() that cannot arm. `exc`
    # picks which of start_timer()'s guarded arms runs: the OSError(ENOMEM) alarm-pool one, or MemoryError.
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
# (datasheets/scd30/Sensirion_CO2_Sensors_SCD30_Interface_Description.pdf) - hardcoded bytes from the PDF,
# not this file's crc8_byte() helper, so a latent bug in that helper cannot mask a real mismatch.
# ---------------------------------------------------------------------------


def test_the_reader_logger_follows_its_log_config() -> None:
    reader = SCD30_Reader(make_i2c(), irq_pin=5, log=LogConfig(None, 3, 2))
    assert type(reader.pr) is PrintLogHistory
    assert reader.pr.name == "SCD30"
    assert len(reader.pr.history) == 3
    assert reader.pr.level == 2


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
    assert run(scd.read_measurement()) is False
    assert i2c.log[0] == ("writeto", _ADDR, bytes([0x02, 0x02]), True)


def test_read_measurement_command_matches_datasheet_example() -> None:
    # Section 1.4.5: write command 0xC2 0x03 0x00 STOP
    scd, i2c = make_scd()
    i2c.read_queue.append(register_frame(1))
    i2c.read_queue.append(data_frame(400.0, 20.0, 50.0))
    assert run(scd.read_measurement()) is True
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
            ],
        ),
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


def test_temperature_offset_rounds_to_the_nearest_tick() -> None:
    # 0.29 * 100 is 28.999999999999996 in double: truncation sends 28, the nearest tick is 29.
    scd, i2c = make_scd()
    run(scd.set_temperature_offset(0.29))
    assert i2c.log[-1][2][:4] == bytes([0x54, 0x03, 0x00, 29])


def test_every_two_decimal_temperature_offset_is_sent_as_typed() -> None:
    # Double-precision proof of the rounding rule over the whole range. The float32 inputs that truncation stored one
    # tick low (0.53, 1.05, ...) cannot be produced on this port; the rule, not those inputs, covers them.
    scd, i2c = make_scd()

    async def sweep() -> int:
        for n in range(65536):  # 0.00-655.35, the schema range, as type_or_range_error() hands each value over
            await scd.set_temperature_offset(n / 100)
            frame = i2c.log[-1][2]
            if (frame[2] << 8 | frame[3]) != n or scd._temp_offset_ticks != n:
                return n
        return -1

    with _FastAsyncSleep():
        assert run(sweep()) == -1


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
    # Regression test for a real bug found during re-review: validating against pressure_mbar AFTER
    # int()-truncating it let any value in the open interval (-1, 0) through as the special "disable" value
    # 0, since int() truncates toward zero rather than rounding.
    #
    # Confirmed against the real interpreter before fixing: set_ambient_pressure(-0.5) sent a real "disable
    # ambient pressure" command to the sensor with no error raised at all.
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
    # Same class of bug as the set_ambient_pressure regression above: int(-0.5) == 0, itself a valid
    # altitude (sea level), so truncating before validating would silently accept a negative altitude as
    # "0m". altitude's signature only advertises int, but nothing stops a caller passing a float anyway.
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


def test_read_measurement_rejects_a_non_finite_word_in_any_position_and_keeps_the_cache() -> None:
    # CRC-valid NaN/inf still decodes, and json.dumps() would ship it as bare nan/inf (Part F.1).
    # Every position and every non-finite kind: one gate per word, not one per frame, is the claim.
    for bad in (float("nan"), float("inf"), float("-inf")):
        for position in range(3):
            values = [412.5, 23.4, 45.6]
            values[position] = bad
            scd, i2c = make_scd()
            scd._co2, scd._temperature, scd._relative_humidity = 1.0, 2.0, 3.0
            i2c.read_queue.append(register_frame(1))
            i2c.read_queue.append(data_frame(values[0], values[1], values[2]))
            try:
                run(scd.read_measurement())
                raised = False
            except ValueError as e:
                raised = "non-finite" in str(e)
            assert raised, f"{bad} in word {position} was accepted"
            assert (scd._co2, scd._temperature, scd._relative_humidity) == (1.0, 2.0, 3.0)


def _rejected_cycle(reader: SCD30_Reader) -> "tuple[tuple[object, ...], bool, SCD30, ErrorLog, int]":
    # One read cycle of a frame the gate rejects: what _read_scd() returns, what is published, the log, the streak.
    async def scenario() -> "tuple[tuple[object, ...], bool, SCD30, ErrorLog, int]":
        results, new_data = await reader._read_scd()
        await reader._error_check(results, condition=results[0] is None)
        await reader._store_scd(results, new_data)
        return results, new_data, await reader.get_data(), await reader.get_error_counter(), reader._err_cnt_internal

    return run(scenario())


def test_reader_turns_a_non_finite_measurement_into_a_logged_failed_read_and_stores_nothing() -> None:
    # Caller side of the gate above: _read_scd() logs the rejected value apart from a bus fault and
    # _store_scd() discards the all-None result, so the published data never carries the value.
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    i2c.read_queue.append(register_frame(1))
    i2c.read_queue.append(data_frame(float("nan"), 23.4, 45.6))
    results, new_data, data, log, streak = _rejected_cycle(reader)
    assert results[:3] == (None, None, None)
    assert new_data is False
    assert data.CO2 is None and data.Temp is None and data.Hum is None
    entries = [n for n, t in zip(log["SCD30"]["ErrNum"], log["SCD30"]["ErrType"]) if t == "E"]  # noqa: B905 - MicroPython zip() rejects strict=
    assert code("E", "READ_RANGE") in entries and code("E", "READ") not in entries
    assert streak == 1


def test_read_measurement_accepts_each_range_boundary_and_rejects_just_outside() -> None:
    # SCD30 Datasheet Tables 1-3: 0-40000 ppm, -40-70 degC, 0-100 %RH; the gate raises before the cache moves.
    accepted = ((0.0, 20.0, 50.0), (40000.0, 20.0, 50.0), (400.0, -40.0, 50.0), (400.0, 70.0, 50.0), (400.0, 20.0, 0.0), (400.0, 20.0, 100.0))
    rejected = ((-1.0, 20.0, 50.0), (40001.0, 20.0, 50.0), (400.0, -40.5, 50.0), (400.0, 70.5, 50.0), (400.0, 20.0, -0.5), (400.0, 20.0, 100.5))
    frames = [data_frame(*values) for values in accepted + rejected]
    for values, frame in zip(accepted, frames[: len(accepted)]):  # noqa: B905 - MicroPython zip() rejects strict=
        scd, i2c = make_scd()
        i2c.read_queue.append(register_frame(1))
        i2c.read_queue.append(frame)
        assert run(scd.read_measurement()) is True, values
        assert (scd._co2, scd._temperature, scd._relative_humidity) == values
    for values, frame in zip(rejected, frames[len(accepted) :]):  # noqa: B905 - MicroPython zip() rejects strict=
        scd, i2c = make_scd()
        scd._co2, scd._temperature, scd._relative_humidity = 1.0, 2.0, 3.0
        i2c.read_queue.append(register_frame(1))
        i2c.read_queue.append(frame)
        try:
            run(scd.read_measurement())
            message = ""
        except ValueError as e:
            message = str(e)
        assert "outside measurement range" in message, values
        assert (scd._co2, scd._temperature, scd._relative_humidity) == (1.0, 2.0, 3.0)


def test_the_reader_logs_an_out_of_range_frame_as_a_failed_read_and_stores_nothing() -> None:
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    i2c.read_queue.append(register_frame(1))
    i2c.read_queue.append(data_frame(40001.0, 23.4, 45.6))
    results, new_data, data, log, streak = _rejected_cycle(reader)
    assert results[:3] == (None, None, None)
    assert new_data is False
    assert data.CO2 is None
    entries = [n for n, t in zip(log["SCD30"]["ErrNum"], log["SCD30"]["ErrType"]) if t == "E"]  # noqa: B905 - MicroPython zip() rejects strict=
    assert code("E", "READ_RANGE") in entries and code("E", "READ") not in entries
    assert streak == 1


def test_the_temperature_gate_applies_the_cached_offset() -> None:
    # The chip reports its reading minus the offset (Interface Description 1.4.7): with 10 degC cached, a
    # decoded -45 degC is a sensor reading of -35 degC (in range), a decoded -51 degC one of -41 degC.
    for reported, accepted in ((-45.0, True), (-51.0, False)):
        scd, i2c = make_scd()
        scd._temp_offset_ticks = 1000
        i2c.read_queue.append(register_frame(1))
        i2c.read_queue.append(data_frame(400.0, reported, 50.0))
        try:
            ok = run(scd.read_measurement())
        except ValueError:
            ok = False
        assert ok is accepted, reported


def test_read_measurement_not_ready_leaves_cached_values_untouched_and_issues_no_measurement_read() -> None:
    # Matches the legacy driver's proven behaviour: a not-ready read neither raises nor clears the cache (owner, 2026-07-22,
    # `110f3db`; SPECIFICATION.md A.4).
    scd, i2c = make_scd()
    scd._co2, scd._temperature, scd._relative_humidity = 1.0, 2.0, 3.0
    i2c.read_queue.append(register_frame(0))
    assert run(scd.read_measurement()) is False
    assert scd._co2 == 1.0
    assert scd._temperature == 2.0
    assert scd._relative_humidity == 3.0
    ops = [entry[0] for entry in i2c.log]
    assert ops == ["writeto", "readfrom_into"]  # only the data-ready probe, no measurement read


def test_a_deinitialised_bus_fails_the_read_without_checking_a_stale_buffer() -> None:
    # A no-op transfer would leave the previous frame in the buffer, whose CRCs pass: the bus result
    # is tested before any CRC, so the stale frame is never decoded as a fresh reading.
    scd, i2c = make_scd()
    i2c.read_queue.append(register_frame(1))
    i2c.read_queue.append(data_frame(400.0, 20.0, 50.0))
    run(scd.read_measurement())
    assert (scd._co2, scd._temperature, scd._relative_humidity) == (400.0, 20.0, 50.0)
    scd._buffer[:] = data_frame(800.0, 25.0, 60.0)  # a valid frame left behind, first word non-zero
    scd._i2c_scd30.i2c_device.i2c.deinit()
    try:
        run(scd.read_measurement())
        message = ""
    except OSError as e:
        message = str(e)
    assert message == "I2C bus not initialized"
    assert (scd._co2, scd._temperature, scd._relative_humidity) == (400.0, 20.0, 50.0)


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
    # Regression test for a real bug found during re-review: the three getters used to each independently
    # call the data-ready-checking fetch, and the SCD30's data-ready flag clears the instant the measurement
    # is read - so only the first saw "ready" and the other two wiped its fresh result back to None.
    #
    # Modeled with a single register_frame(1) + data_frame() pair queued, exactly one real sensor read.
    # Three independently-queued "ready" replies is what let the bug go unnoticed, since that is not how the
    # real hardware behaves across one read_measurement() plus three getter calls.
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
# Module level: setup()/reset() - identity check, then soft reset with the real _SOFT_RESET_WAIT_S
# delay. Kept to two tests (the delay is real elapsed time, not simulated) rather than exercised
# from every angle at this layer.
# ---------------------------------------------------------------------------


def test_setup_probes_reads_firmware_version_then_soft_resets_and_reads_the_temperature_offset() -> None:
    scd, i2c = make_scd()
    i2c.read_queue.append(register_frame(0x0301))
    i2c.read_queue.append(register_frame(450))
    assert run(scd.setup()) is True
    ops = [entry[0] for entry in i2c.log]
    assert ops == ["writeto", "writeto", "readfrom_into", "writeto", "writeto", "readfrom_into"]
    assert i2c.log[0][2] == b""  # I2CDevice.setup()'s device-presence probe
    assert i2c.log[1][2] == bytes([0xD1, 0x00])  # _CMD_READ_FIRMWARE_VERSION
    assert i2c.log[3][2] == bytes([0xD3, 0x04])  # _CMD_SOFT_RESET
    assert i2c.log[4][2] == bytes([0x54, 0x03])  # the temperature offset the range gate adds back
    assert scd._temp_offset_ticks == 450


def test_setup_probe_failure_never_reaches_firmware_read_or_reset() -> None:
    scd, i2c = make_scd()
    i2c.nak_addresses.add(_ADDR)
    try:
        run(scd.setup())
        raised = False
    except (OSError, RuntimeError, ValueError):
        raised = True
    assert raised
    assert len(i2c.log) == 0  # probe failed before any command bytes were even written


# ===========================================================================
# Integration level: SCD30_Reader wired to the real asy_i2c_driver.I2C/I2CDevice,
# asy_base_classes.SensorReader, and asy_print_log.PrintLogHistory - only the raw I2C bus is mocked.
# ===========================================================================


def test_reader_init_constructs_a_real_input_pin_and_leaves_timer_unarmed() -> None:
    reader = make_reader()
    assert reader._irq_pin.mode == FakePin.IN
    assert reader._start_trigger_timer.deinit_called is False


def test_reader_start_timer_arms_periodic_timer_and_pin_irq() -> None:
    FakeTimer.all_timers.clear()
    reader = make_reader()
    reader.start_timer()
    assert reader._start_trigger_timer.period == _START_TRIGGER_PERIOD_MS
    assert reader._start_trigger_timer.mode == FakeTimer.PERIODIC
    assert reader._irq_pin._irq_trigger == FakePin.IRQ_RISING

    reader._start_trigger_timer.trigger()
    reader._irq_pin.trigger_irq()

    async def scenario() -> None:
        await asyncio.wait_for(reader._base_trigger_event.wait(), _EVENT_WAIT_S)
        await asyncio.wait_for(reader._read_event.wait(), _EVENT_WAIT_S)

    run(scenario())
    FakeTimer.all_timers.clear()


def test_reader_start_timer_degrades_gracefully_when_the_trigger_timer_cannot_be_armed() -> None:
    # Real rp2 Timer.init() raises OSError(ENOMEM) when the alarm pool is exhausted (ports/rp2/machine_timer.c);
    # start_timer() runs inside SystemService's timer start and must not raise into it.
    FakeTimer.all_timers.clear()
    reader = make_reader()
    with _RaiseOnArm():
        reader.start_timer()  # must not raise despite the timer failing to arm
    assert reader._start_trigger_timer.period == -1  # never actually armed
    assert reader._start_trigger_timer.callback is None  # nothing wired to _base_trigger_event
    # start_timer() is synchronous and persists nothing itself; the waiting _irq_loop() records the TIMER
    # error and ends (see the test below).
    assert run(reader.get_error_counter())["SCD30"]["ErrCount"] == 0
    assert reader._base_trigger_event.state  # the waiter is woken

    # The pin IRQ is wired after the guarded try/except, so a timer that failed to arm must not
    # cost the sensor its data-ready interrupt as well - that IRQ, not the timer, is what actually
    # triggers a measurement read (the timer only drives _irq_loop()'s stuck-pin watchdog).
    assert reader._irq_pin._irq_trigger == FakePin.IRQ_RISING
    reader._irq_pin.trigger_irq()

    async def scenario() -> None:
        await asyncio.wait_for(reader._read_event.wait(), _EVENT_WAIT_S)

    run(scenario())
    FakeTimer.all_timers.clear()


def test_reader_start_timer_degrades_gracefully_on_a_memory_error_while_arming() -> None:
    # MemoryError is not an OSError subclass (SPECIFICATION.md Part F), so start_timer()'s `except (OSError,
    # MemoryError)` needs that second arm spelled out - without it a heap-exhausted arming attempt
    # propagates straight out of this synchronous starter, pin IRQ included.
    FakeTimer.all_timers.clear()
    reader = make_reader()
    with _RaiseOnArm(MemoryError):
        reader.start_timer()  # must not raise despite the timer failing to arm
    assert reader._start_trigger_timer.period == -1  # never actually armed
    assert reader._start_trigger_timer.callback is None
    assert reader._irq_pin._irq_trigger == FakePin.IRQ_RISING
    assert reader._base_trigger_event.state  # the waiter is woken
    FakeTimer.all_timers.clear()


def _arm_failure_then_restart(exc: "type[BaseException]") -> None:
    FakeTimer.all_timers.clear()
    reader = make_reader(trigger_s=1)  # two ticks with the pin high force a read
    reader._irq_pin.value(1)

    async def first_run() -> bool:
        task = asyncio.create_task(reader._irq_loop())
        await _settle(3)
        with _RaiseOnArm(exc):
            reader.start_timer()
        await _settle(5)
        if not task.done():
            task.cancel()
            return False
        await task  # ended on its own: a return, not a raise
        return True

    assert run(first_run()) is True, exc
    log = run(reader.get_error_counter())["SCD30"]
    assert log["ErrCount"] == 1 and log["ErrNum"][-1] == code("E", "TIMER"), exc

    async def restart() -> bool:
        task = asyncio.create_task(reader._irq_loop())
        await _settle(3)
        for _ in range(2):
            reader._start_trigger_timer.trigger()
            await _settle(3)
        fired = reader._read_event.state
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return bool(fired)

    assert run(restart()) is True, exc
    assert [arm[1] for arm in reader._start_trigger_timer.arms] == [_START_TRIGGER_PERIOD_MS]
    assert run(reader.get_error_counter())["SCD30"]["ErrCount"] == 1
    FakeTimer.all_timers.clear()


def test_a_failed_trigger_arm_ends_the_irq_task_with_one_timer_entry_and_a_restart_rearms() -> None:
    # The arm fails after the task started (tasks start before timers at boot): the woken task persists one
    # TIMER entry and ends; its restart re-arms first, and a tick then drives the stuck-pin read.
    for exc in (OSError, MemoryError):
        _arm_failure_then_restart(exc)


def test_reader_stop_timer_deinits_the_periodic_timer_only() -> None:
    FakeTimer.all_timers.clear()
    reader = make_reader()
    reader.start_timer()
    reader.stop_timer()
    assert reader._start_trigger_timer.deinit_called is True
    FakeTimer.all_timers.clear()


def test_reader_get_task_starters_and_timer_starters_shape() -> None:
    reader = make_reader()
    task_starters = reader.get_task_starters()
    timer_starters = reader.get_timer_starters()
    assert task_starters == [reader.start_asy_read, reader.start_asy_irq]
    assert timer_starters == [reader.start_timer]
    assert reader.get_trigger_starters() == []  # reads on its own data-ready edge: nothing to stagger


def test_scd_init_irq_sets_irq_trigger_after_enough_consecutive_stuck_ticks() -> None:
    reader = make_reader(trigger_s=3)  # _trigger_half_ticks = 2*3 = 6
    reader._irq_pin.value(1)  # IRQ pin stuck HIGH - sensor never actually got read

    async def scenario() -> "tuple[bool, bool]":
        task = asyncio.create_task(reader._irq_loop())
        for _ in range(5):
            reader._base_trigger_event.set()
            await _settle(3)
        not_yet = True
        try:
            await asyncio.wait_for(reader._read_event.wait(), 0)
            not_yet = False
        except asyncio.TimeoutError:
            pass
        reader._base_trigger_event.set()
        await _settle(3)
        triggered = False
        try:
            await asyncio.wait_for(reader._read_event.wait(), _EVENT_WAIT_S)
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


def _drive_irq_ticks(reader: SCD30_Reader, pins: "list[int]") -> bool:
    # One base tick per entry, the pin at that level, nothing consuming the read event: whether it fired.
    async def scenario() -> bool:
        task = asyncio.create_task(reader._irq_loop())
        await _settle(3)
        for level in pins:
            reader._irq_pin.value(level)
            reader._base_trigger_event.set()
            await _settle(3)
        fired = bool(reader._read_event.state)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return fired

    return run(scenario())


def test_the_stuck_pin_count_saturates_at_the_threshold() -> None:
    reader = make_reader(trigger_s=3)  # _trigger_half_ticks = 6
    assert _drive_irq_ticks(reader, [1] * (3 * reader._trigger_half_ticks)) is True
    assert reader._scd_timer_triggers == reader._trigger_half_ticks


def test_stuck_pin_ticks_accumulate_across_a_low_gap() -> None:
    # The count is of ticks with the pin high since the last read, not of consecutive ones.
    reader = make_reader(trigger_s=3)
    assert _drive_irq_ticks(reader, [1] * 2 + [0] * 10 + [1] * 3) is False
    assert reader._scd_timer_triggers == 5
    reader = make_reader(trigger_s=3)
    assert _drive_irq_ticks(reader, [1] * 2 + [0] * 10 + [1] * 4) is True


def test_scd_init_irq_never_triggers_while_pin_reads_low() -> None:
    reader = make_reader(trigger_s=1)  # _trigger_half_ticks = 2
    reader._irq_pin.value(0)  # sensor is being read normally - pin never stuck high

    async def scenario() -> bool:
        task = asyncio.create_task(reader._irq_loop())
        for _ in range(10):
            reader._base_trigger_event.set()
            await _settle(3)
        triggered = True
        try:
            await asyncio.wait_for(reader._read_event.wait(), 0)
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
# Integration: every public getter/setter, real fault propagation through asy_print_log/asy_base_classes -
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


def test_reader_getters_log_chip_get_on_bus_nak() -> None:
    # Every forward logs its failure (SPECIFICATION.md C.7): one CHIP_GET class for all six; the
    # console line names the field.
    reader = make_reader()
    reader_fake_i2c(reader).nak_addresses.add(_ADDR)

    async def scenario() -> "ErrorLog":
        await reader.get_measurement_interval()
        await reader.get_self_calibration_enabled()
        await reader.get_ambient_pressure()
        await reader.get_altitude()
        await reader.get_temperature_offset()
        await reader.get_forced_recalibration_reference()
        return await reader.get_error_counter()

    log = run(scenario())["SCD30"]
    # Six counts, one slot: a repeat of the newest entry spends none (SPECIFICATION.md C.7.1).
    assert log["ErrCount"] == 6
    assert log["ErrNum"][-2:] == [0, code("E", "CHIP_GET")]
    assert log["ErrType"][-2:] == ["N", "E"]


def test_reader_setters_log_chip_set_on_bus_nak() -> None:
    reader = make_reader()
    reader_fake_i2c(reader).nak_addresses.add(_ADDR)

    async def scenario() -> "ErrorLog":
        await reader.set_measurement_interval(10)
        await reader.set_self_calibration_enabled(True)
        await reader.set_ambient_pressure(1000)
        await reader.set_altitude(100)
        await reader.set_temperature_offset(1.0)
        await reader.set_forced_recalibration_reference(500)
        return await reader.get_error_counter()

    log = run(scenario())["SCD30"]
    assert log["ErrCount"] == 6
    assert log["ErrNum"][-2:] == [0, code("E", "CHIP_SET")]
    assert log["ErrType"][-2:] == ["N", "E"]


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
    # Queued upfront, not from inside scenario(): register_frame() calls run()/asyncio.run() itself via
    # crc8_byte(), and nesting that inside a coroutine already driven by an outer run() segfaults the
    # MicroPython Unix port instead of raising cleanly, unlike CPython's RuntimeError for the same misuse.
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
    assert run(reader.stop_continuous_measurement(value=True)) is False
    assert len(i2c.log) == 0


def test_reader_stop_continuous_measurement_false_sends_the_real_stop_command() -> None:
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    assert run(reader.stop_continuous_measurement(value=False)) is True
    assert i2c.log[-1] == ("writeto", _ADDR, bytes([0x01, 0x04]), True)


def test_reader_stop_continuous_measurement_false_returns_false_on_bus_fault() -> None:
    reader = make_reader()
    reader_fake_i2c(reader).nak_addresses.add(_ADDR)

    async def scenario() -> "tuple[bool, ErrorLog]":
        ok = await reader.stop_continuous_measurement(value=False)
        return ok, await reader.get_error_counter()

    ok, log = run(scenario())
    assert ok is False
    assert log["SCD30"]["ErrNum"][-1] == code("E", "CHIP_SET")


def test_set_dict_cfg_reports_contmeas_true_as_valid_not_failed() -> None:
    # Regression test: stop_continuous_measurement(value=True) returns False for its no-op case, and a first
    # version of the ContMeas dispatch forwarded that into the generic "Valid"/"Failed" mapping - reporting
    # a client's ContMeas=True, the field's own default, as "Failed" though nothing failed.
    #
    # Never caught by any prior test, since nothing exercised _set_dict_cfg's ContMeas branch specifically.
    reader = make_reader()
    _queue_snapshot(reader_fake_i2c(reader))
    result = run(reader._set_dict_cfg({"ContMeas": True}, reader.get_cfg_schema()))
    assert result == {"ContMeas": "Valid"}


def test_set_dict_cfg_reports_contmeas_false_as_valid_when_the_real_stop_succeeds() -> None:
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    _queue_snapshot(i2c)
    result = run(reader._set_dict_cfg({"ContMeas": False}, reader.get_cfg_schema()))
    assert result == {"ContMeas": "Valid"}
    assert i2c.log[-1] == ("writeto", _ADDR, bytes([0x01, 0x04]), True)


def test_set_dict_cfg_reports_contmeas_false_as_failed_on_bus_fault() -> None:
    # The NAK fails the snapshot first: the body is refused whole, nothing is sent.
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    i2c.nak_addresses.add(_ADDR)

    async def scenario() -> "tuple[WriteValidity, ErrorLog]":
        result = await reader._set_dict_cfg({"ContMeas": False}, reader.get_cfg_schema())
        return result, await reader.get_error_counter()

    result, log = run(scenario())
    assert result == {"ContMeas": "Failed"}
    assert scd30_nvm_writes(i2c) == {}
    assert log["SCD30"]["ErrCount"] == 1
    assert log["SCD30"]["ErrNum"][-1] == code("E", "CHIP_GET")


def test_set_dict_cfg_reports_contmeas_non_bool_as_invalid() -> None:
    reader = make_reader()
    _queue_snapshot(reader_fake_i2c(reader))
    result = run(reader._set_dict_cfg({"ContMeas": "yes"}, reader.get_cfg_schema()))
    assert result == {"ContMeas": "Invalid"}


def _contmeas_put(body: "CfgValue") -> "tuple[WriteValidity, ErrorLog, FakeI2C]":
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    _queue_snapshot(i2c)

    async def scenario() -> "tuple[WriteValidity, ErrorLog]":
        result = await reader._set_dict_cfg({"ContMeas": body}, reader.get_cfg_schema())
        return result, await reader.get_error_counter()

    result, log = run(scenario())
    return result, log, i2c


def test_contmeas_rejects_an_int_and_a_string() -> None:
    # A bool field never takes an int or a string: the synthetic FieldSchema refuses both, nothing is sent.
    body: CfgValue
    for body in (1, "false"):
        result, log, i2c = _contmeas_put(body)
        assert result == {"ContMeas": "Invalid"}, body
        assert scd30_nvm_writes(i2c) == {} and _arg_words(i2c) == []
        assert log["SCD30"]["ErrNum"][-1] == code("E", "BAD_ARG")


def _stored_file(reader: SCD30_Reader) -> "dict[str, object]":
    # The config file as the flash holds it, after the deferred flush ran.
    run(reader.cfgmgr.flush_pending())
    with open(reader.cfgmgr._config_file) as f:
        stored: dict[str, object] = json.load(f)
    return stored


def test_frc_keys_stay_in_the_file_and_chip_keys_on_the_chip() -> None:
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    _queue_snapshot(i2c)
    body: dict[str, CfgValue] = {"FRCNoise": 30.0, "TempOffset": 4.5, "FRCWindow": 120}
    with WriteCountingOpen(cm) as opened:
        result = run(reader._set_dict_cfg(body, reader.get_cfg_schema()))
        stored = _stored_file(reader)
    assert result == dict.fromkeys(body, "Valid")
    assert scd30_nvm_writes(i2c) == {0x5403: 1}  # only the chip key reached the chip
    assert opened.writes == 1
    assert stored == {"FRCNoise": 30.0, "FRCRate": 10.0, "FRCWindow": 120}  # no chip key in the file
    # An FRC-only body takes no snapshot: the bus stays silent.
    i2c.log.clear()
    assert run(reader._set_dict_cfg({"FRCRate": 5.0}, reader.get_cfg_schema())) == {"FRCRate": "Valid"}
    assert len(i2c.log) == 0
    assert _stored_file(reader)["FRCRate"] == 5.0


# ---------------------------------------------------------------------------
# _set_dict_cfg through SCD30's chip store: snapshot, compare, validate, write in a fixed order (SPECIFICATION.md C.4.3).
# ---------------------------------------------------------------------------


def test_set_dict_cfg_dispatches_a_valid_value_to_the_real_setter_and_reports_valid() -> None:
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    _queue_snapshot(i2c)
    result = run(reader._set_dict_cfg({"TempOffset": 4.5}, reader.get_cfg_schema()))
    assert result == {"TempOffset": "Valid"}
    assert scd30_nvm_writes(i2c) == {0x5403: 1}


def test_set_dict_cfg_int_value_for_the_float_typed_tempoffs_field_is_coerced_before_dispatch() -> None:
    # TempOffset is float-typed, so a plain int PUT value must be coerced to float by type_or_range_error()
    # before reaching set_temperature_offset(). Both are structurally acceptable to the setter's int|float
    # signature, so only inspecting the actual argument received, via this spy, proves coercion really ran.
    reader = make_reader()
    reader_fake_i2c(reader)
    received = []

    async def spy(offset: "int | float") -> bool:
        received.append(offset)
        return True

    reader.set_temperature_offset = spy  # type: ignore[method-assign]
    _queue_snapshot(reader_fake_i2c(reader))
    result = run(reader._set_dict_cfg({"TempOffset": 5}, reader.get_cfg_schema()))
    assert result == {"TempOffset": "Valid"}
    assert received == [5.0]
    assert type(received[0]) is float


def test_set_dict_cfg_integral_float_value_for_the_int_typed_measint_field_is_coerced_before_dispatch() -> None:
    # Mirror of the test above, in the other direction: MeasInterval is int-typed - an integral float PUT
    # value must be coerced to int before reaching set_measurement_interval().
    reader = make_reader()
    reader_fake_i2c(reader)
    received = []

    async def spy(value: int) -> bool:
        received.append(value)
        return True

    reader.set_measurement_interval = spy  # type: ignore[method-assign]
    _queue_snapshot(reader_fake_i2c(reader))
    result = run(reader._set_dict_cfg({"MeasInterval": 10.0}, reader.get_cfg_schema()))
    assert result == {"MeasInterval": "Valid"}
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
    _queue_snapshot(reader_fake_i2c(reader))
    result = run(reader._set_dict_cfg({"MeasInterval": 10.5}, reader.get_cfg_schema()))
    assert result == {"MeasInterval": "Invalid"}
    assert received == []  # never dispatched - rejected before the setter is ever called


def test_set_dict_cfg_out_of_range_value_rejected_before_dispatch() -> None:
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    _queue_snapshot(i2c)

    async def scenario() -> "tuple[WriteValidity, ErrorLog]":
        result = await reader._set_dict_cfg({"TempOffset": 9999.0}, reader.get_cfg_schema())
        return result, await reader.get_error_counter()

    result, log = run(scenario())
    assert result == {"TempOffset": "Invalid"}
    assert scd30_nvm_writes(i2c) == {}
    assert log["SCD30"]["ErrNum"][-1] == code("E", "BAD_ARG")


def test_set_dict_cfg_wrong_type_value_rejected_before_dispatch() -> None:
    reader = make_reader()
    _queue_snapshot(reader_fake_i2c(reader))
    result = run(reader._set_dict_cfg({"TempOffset": "not a number"}, reader.get_cfg_schema()))
    assert result == {"TempOffset": "Invalid"}


def test_set_dict_cfg_unknown_key_reported_invalid_without_dispatch() -> None:
    # A body with no chip key reads no snapshot: the bus stays silent.
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    result = run(reader._set_dict_cfg({"NoSuchField": 5}, reader.get_cfg_schema()))
    assert result == {"NoSuchField": "Invalid"}
    assert len(i2c.log) == 0


def test_set_dict_cfg_setter_reports_failed_on_bus_fault() -> None:
    # The snapshot answers (stubbed); the bus then NAKs, so the write itself fails.
    reader = make_reader()

    async def stored() -> "tuple[float, int, int, int, int, bool]":
        return 0.0, 2, 0, 0, 400, False

    reader._scd.get_config_snapshot = stored  # type: ignore[method-assign]
    reader_fake_i2c(reader).nak_addresses.add(_ADDR)

    async def scenario() -> "tuple[WriteValidity, ErrorLog]":
        result = await reader._set_dict_cfg({"TempOffset": 4.5}, reader.get_cfg_schema())
        return result, await reader.get_error_counter()

    result, log = run(scenario())
    assert result == {"TempOffset": "Failed"}
    assert log["SCD30"]["ErrNum"][-1] == code("E", "CHIP_SET")


def test_set_dict_cfg_multiple_fields_in_one_call_including_ambpres_special_sentinel() -> None:
    # Exercises several dispatch fields together (not just TempOffset in isolation), including
    # AmbPres's own special-value sentinel (0 - deactivate ambient pressure compensation).
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    _queue_snapshot(i2c)
    result = run(reader._set_dict_cfg({"TempOffset": 5, "AmbPres": 0, "SelfCal": True}, reader.get_cfg_schema()))
    assert result == {"TempOffset": "Valid", "AmbPres": "Valid", "SelfCal": "Valid"}
    assert _arg_words(i2c) == [0x5403, 0x0010, 0x5306]  # _APPLY_ORDER: TempOffset, AmbPres, SelfCal


def test_a_repeated_put_of_a_stored_chip_value_is_unchanged_and_writes_nothing() -> None:
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    body: dict[str, CfgValue] = {"TempOffset": 4.5, "MeasInterval": 10, "Altitude": 200, "SelfCal": True}
    _queue_snapshot(i2c)
    first = run(reader._set_dict_cfg(body, reader.get_cfg_schema()))
    assert first == dict.fromkeys(body, "Valid")
    written = scd30_nvm_writes(i2c)
    _queue_snapshot(i2c, temp_offset=450, interval=10, altitude=200, asc=1)  # the chip now holds the body
    second = run(reader._set_dict_cfg(body, reader.get_cfg_schema()))
    assert second == dict.fromkeys(body, "Unchanged")
    assert scd30_nvm_writes(i2c) == written


def test_ambpres_and_forcecalref_always_write() -> None:
    # Both are commands to the chip, not compared: an equal value is sent once more and answers "Valid".
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    body: dict[str, CfgValue] = {"AmbPres": 1000, "ForceCalRef": 450}
    for attempt in (1, 2):
        _queue_snapshot(i2c, pressure=1000, frc=450)
        assert run(reader._set_dict_cfg(body, reader.get_cfg_schema())) == {"AmbPres": "Valid", "ForceCalRef": "Valid"}
        assert scd30_nvm_writes(i2c) == {0x0010: attempt, 0x5204: attempt}


def test_a_reversed_body_writes_in_the_fixed_order() -> None:
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    _queue_snapshot(i2c)
    body: dict[str, CfgValue] = {"SelfCal": True, "ForceCalRef": 450, "Altitude": 200, "AmbPres": 1000, "MeasInterval": 10, "TempOffset": 4.5}
    result = run(reader._set_dict_cfg(body, reader.get_cfg_schema()))
    assert result == dict.fromkeys(body, "Valid")
    assert _arg_words(i2c) == [0x5403, 0x4600, 0x0010, 0x5102, 0x5204, 0x5306]


def test_ambpres_with_contmeas_false_ends_stopped_in_either_key_order() -> None:
    # AmbPres (0x0010) starts continuous measurement; the stop (0x0104) is sent after it either way.
    bodies: list[dict[str, CfgValue]] = [{"AmbPres": 1000, "ContMeas": False}, {"ContMeas": False, "AmbPres": 1000}]
    for body in bodies:
        reader = make_reader()
        i2c = reader_fake_i2c(reader)
        _queue_snapshot(i2c)
        assert run(reader._set_dict_cfg(body, reader.get_cfg_schema())) == {"AmbPres": "Valid", "ContMeas": "Valid"}
        commands = [entry[2][:2] for entry in i2c.log if entry[0] == "writeto" and (len(entry[2]) == 5 or entry[2] == b"\x01\x04")]
        assert commands == [b"\x00\x10", b"\x01\x04"]


def test_a_failing_snapshot_fails_every_key_and_writes_nothing() -> None:
    # Nothing queued: the first register reply reads as zeros with a wrong CRC, so the snapshot fails on a live bus.
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    body: dict[str, CfgValue] = {"TempOffset": 4.5, "MeasInterval": 10, "AmbPres": 1000, "ContMeas": False, "NoSuchField": 1, "FRCNoise": 30.0}

    async def scenario() -> "tuple[WriteValidity, ErrorLog]":
        result = await reader._set_dict_cfg(body, reader.get_cfg_schema())
        await reader.cfgmgr.flush_pending()
        return result, await reader.get_error_counter()

    with WriteCountingOpen(cm) as opened:
        result, log = run(scenario())
    assert result == dict.fromkeys(body, "Failed")
    assert opened.writes == 0  # the FRC key is refused with the body: nothing reaches the file either
    assert scd30_nvm_writes(i2c) == {}
    assert _arg_words(i2c) == []
    assert log["SCD30"]["ErrCount"] == 1
    assert log["SCD30"]["ErrNum"][-1] == code("E", "CHIP_GET")


def test_tempoffset_compares_at_tick_resolution() -> None:
    # 12.345 rounds to tick 1235, the chip's stored word: equal at the chip's resolution.
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    _queue_snapshot(i2c, temp_offset=1235)
    assert run(reader._set_dict_cfg({"TempOffset": 12.345}, reader.get_cfg_schema())) == {"TempOffset": "Unchanged"}
    assert scd30_nvm_writes(i2c) == {}


# ---------------------------------------------------------------------------
# Integration: get_dict_cfg()/get_dict_data() through the real asy_config_manager.make_dict/name_cfg
# ---------------------------------------------------------------------------


def test_get_dict_cfg_reports_every_schema_field_by_name() -> None:
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    i2c.read_queue.append(register_frame(450))  # TempOffset
    i2c.read_queue.append(register_frame(10))  # MeasInterval
    i2c.read_queue.append(register_frame(1000))  # AmbPres
    i2c.read_queue.append(register_frame(200))  # Altitude
    i2c.read_queue.append(register_frame(400))  # ForceCalRef
    i2c.read_queue.append(register_frame(1))  # SelfCal

    result = run(reader.get_dict_cfg())
    fields = result["SCD30"]
    assert fields["TempOffset"] == 4.5
    assert fields["MeasInterval"] == 10
    assert fields["AmbPres"] == 1000
    assert fields["Altitude"] == 200
    assert fields["ForceCalRef"] == 400
    assert fields["SelfCal"] is True
    assert (fields["FRCNoise"], fields["FRCRate"], fields["FRCWindow"]) == (20.0, 10.0, 60)  # the file's defaults


def test_get_cfg_schema_returns_every_settable_field_by_name() -> None:
    # _put_sensors() calls get_cfg_schema() on every sensor; SCD30's covers six chip keys and three file keys.
    reader = make_reader()
    names = cm.schema_names(reader.get_cfg_schema())
    assert set(names) == {"TempOffset", "MeasInterval", "AmbPres", "Altitude", "ForceCalRef", "SelfCal", "FRCNoise", "FRCRate", "FRCWindow"}


def test_get_dict_cfg_degrades_to_none_per_field_on_bus_fault_not_a_crash() -> None:
    reader = make_reader()
    reader_fake_i2c(reader).nak_addresses.add(_ADDR)

    async def scenario() -> "tuple[dict[str, dict[str, int | float | str | bool | None]], ErrorLog]":
        result = await reader.get_dict_cfg()
        return result, await reader.get_error_counter()

    result, log = run(scenario())
    assert log["SCD30"]["ErrCount"] == 1
    assert log["SCD30"]["ErrNum"][-1] == code("E", "CHIP_GET")
    fields = result["SCD30"]
    assert fields == {
        "TempOffset": None,
        "MeasInterval": None,
        "AmbPres": None,
        "Altitude": None,
        "ForceCalRef": None,
        "SelfCal": None,
        "FRCNoise": 20.0,
        "FRCRate": 10.0,
        "FRCWindow": 60,
    }


def test_get_dict_cfg_after_a_failing_snapshot_shows_none_and_one_entry() -> None:
    # A CRC-failing snapshot on a live bus (nothing queued), beside the NAK case above.
    reader = make_reader()

    async def scenario() -> "tuple[dict[str, dict[str, int | float | str | bool | None]], ErrorLog]":
        result = await reader.get_dict_cfg()
        return result, await reader.get_error_counter()

    result, log = run(scenario())
    expected: dict[str, int | float | str | bool | None] = dict.fromkeys(("TempOffset", "MeasInterval", "AmbPres", "Altitude", "ForceCalRef", "SelfCal"))
    expected.update({"FRCNoise": 20.0, "FRCRate": 10.0, "FRCWindow": 60})  # the file still answers
    assert result == {"SCD30": expected}
    assert log["SCD30"]["ErrCount"] == 1
    assert log["SCD30"]["ErrNum"][-1] == code("E", "CHIP_GET")


def test_get_dict_cfg_snapshot_is_atomic_against_a_concurrent_config_write() -> None:
    # get_config_snapshot() holds the device session for all six reads: a concurrent offset write lands only
    # after them (two log entries per register).
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    for value in (450, 10, 1000, 200, 400, 1):  # TempOffset, MeasInterval, AmbPres, Altitude, ForceCalRef, SelfCal
        i2c.read_queue.append(register_frame(value))

    async def scenario() -> "tuple[dict[str, dict[str, int | float | str | bool | None]], list[tuple[Any, ...]]]":
        with _FastAsyncSleep():
            read_task = asyncio.create_task(reader.get_dict_cfg())
            await _settle(3)  # let the read task acquire the lock and begin its first register read
            assert not read_task.done()

            write_task = asyncio.create_task(reader._scd.set_temperature_offset(9.99))
            await _settle(3)  # give the write every chance to run if it weren't blocked by the lock
            assert not write_task.done()  # still blocked - proves the lock is held for the whole batch

            result = await read_task
            await write_task
        return result, list(i2c.log)

    result, log = run(scenario())
    fields = result["SCD30"]
    assert fields["TempOffset"] == 4.5  # the pre-write value, not the concurrent write's 9.99
    read_ops = 12  # 6 registers x (writeto register address, readfrom_into reply)
    # The write's command frame is 5 bytes (2-byte command, 2-byte data, 1-byte CRC), distinct from the
    # read's 2-byte register-address probe for the same command code - TempOffset is read first in the batch,
    # so a length-agnostic match would find that probe at index 0 instead.
    write_index = next(
        i for i, entry in enumerate(log) if entry[0] == "writeto" and entry[2][:2] == bytes([0x54, 0x03]) and len(entry[2]) == 5
    )
    assert write_index >= read_ops  # the write's own bus traffic never interleaved with the read's


def test_get_dict_data_reports_measured_values_by_name() -> None:
    reader = make_reader()
    data = SCD30(400.0, 20.0, 50.0, 15.2, 9.3, 1, 0, 123456)
    run(reader._set_meas_data(data))
    result = run(reader.get_dict_data())
    assert result["SCD30"]["CO2"] == 400.0
    assert result["SCD30"]["Temp"] == 20.0
    assert result["SCD30"]["Hum"] == 50.0
    assert (result["SCD30"]["FRCState"], result["SCD30"]["FRCWait"]) == (1, 0)
    assert result["SCD30"]["TS"] == 123456


def test_get_error_counter_forwards_to_the_real_print_log() -> None:
    reader = make_reader()
    log = run(reader.get_error_counter())
    assert log["SCD30"]["ErrCount"] == 0


# ---------------------------------------------------------------------------
# Integration: _init_scd() / _read_loop() - real asy_base_classes.SensorReader plus asy_print_log wiring.
# scd.setup() and the interval read are faked by _fake_init() so these focus on _read_loop()'s orchestration
# without re-paying the real _SOFT_RESET_WAIT_S reset delay each time.
# ---------------------------------------------------------------------------


async def _fake_new_data() -> bool:
    return True


async def _fake_chip_setup() -> bool:
    return True


async def _fake_interval() -> int:
    return 2


def _fake_init(reader: SCD30_Reader) -> None:
    reader._scd.setup = _fake_chip_setup  # type: ignore[method-assign]
    reader._scd.get_measurement_interval = _fake_interval  # type: ignore[method-assign]


def _entries(reader: SCD30_Reader) -> "list[tuple[str, int]]":
    # The module's persisted history, oldest first, as (kind, code) without the empty slots.
    log = run(reader.get_error_counter())["SCD30"]
    return [(t, n) for t, n in zip(log["ErrType"], log["ErrNum"]) if t != "N"]  # noqa: B905 - MicroPython zip() rejects strict=


def test_init_scd_returns_false_immediately_when_probe_fails_no_reset_reached() -> None:
    reader = make_reader()
    reader_fake_i2c(reader).nak_addresses.add(_ADDR)
    assert run(reader._init_scd()) is False
    # A failed chip setup runs the controller rung at once (C.7): the setup error, then the bus recovery.
    assert _entries(reader) == [("E", code("E", "INIT")), ("W", code("W", "BUS_RECOVERY"))]


def test_read_loop_full_iteration_stores_measured_data_and_derived_values() -> None:
    reader = make_reader(max_module_error=1)
    _fake_init(reader)
    # read_measurement() is the one call that can raise post-fix; the three getters are pure cache reads
    # (see src/asy_scd30_driver.py on why they must never re-check data-ready) - faked as a new-data success
    # plus fixed cache values, matching that shape, not the pre-fix "each getter fetches" one.
    reader._scd.read_measurement = _fake_new_data  # type: ignore[method-assign]

    async def fake_co2() -> float:
        return 500.0

    async def fake_temp() -> float:
        return 21.0

    async def fake_hum() -> float:
        return 40.0

    reader._scd.get_CO2 = fake_co2  # type: ignore[method-assign]
    reader._scd.get_temperature = fake_temp  # type: ignore[method-assign]
    reader._scd.get_relative_humidity = fake_hum  # type: ignore[method-assign]

    async def scenario() -> SCD30:
        task = asyncio.create_task(reader._read_loop())
        await _settle(5)
        reader._read_event.set()
        await _settle(5)
        data = await reader.get_data()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return data

    with _UTCValid():
        data = run(scenario())
    assert data.CO2 == 500.0
    assert data.Temp == 21.0
    assert data.Hum == 40.0
    assert data.TS is not None
    assert data.WetBulb is not None
    assert data.DewPoint is not None


def test_a_read_before_the_first_sync_publishes_with_ts_none_and_steps_no_streak() -> None:
    # utc_now() is None until the NTP client sets the clock: the sample is published with TS None,
    # and the read loop's condition counts only a cycle whose measured values are gone.
    reader = make_reader(max_module_error=1)
    _fake_init(reader)
    reader._scd.read_measurement = _fake_new_data  # type: ignore[method-assign]

    async def fake_value() -> float:
        return 21.0

    reader._scd.get_CO2 = fake_value  # type: ignore[method-assign]
    reader._scd.get_temperature = fake_value  # type: ignore[method-assign]
    reader._scd.get_relative_humidity = fake_value  # type: ignore[method-assign]

    async def scenario() -> "tuple[SCD30, bool]":
        task = asyncio.create_task(reader._read_loop())
        await _settle(5)
        for _ in range(3):  # three good cycles: past max_module_error had TS counted as a failure
            reader._read_event.set()
            await _settle(5)
        running = not task.done()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return await reader.get_data(), running

    data, running = run(scenario())
    assert running is True
    assert data.CO2 == 21.0
    assert data.TS is None
    assert reader._err_cnt_internal == 0


def test_a_failed_read_keeps_the_last_good_sample_and_its_timestamp() -> None:
    reader = make_reader()
    fail = [False]

    async def read_measurement() -> bool:
        if fail[0]:
            raise OSError(5, "nak")
        return True

    async def fake_value() -> float:
        return 21.0

    reader._scd.read_measurement = read_measurement  # type: ignore[method-assign]
    reader._scd.get_CO2 = fake_value  # type: ignore[method-assign]
    reader._scd.get_temperature = fake_value  # type: ignore[method-assign]
    reader._scd.get_relative_humidity = fake_value  # type: ignore[method-assign]
    with _UTCValid():
        run(reader._store_scd(*run(reader._read_scd())))
        good = run(reader.get_data())
        fail[0] = True
        failed, new_data = run(reader._read_scd())
        run(reader._store_scd(failed, new_data))
    assert good.TS is not None
    assert failed[:3] == (None, None, None)
    assert run(reader.get_data()) == good  # the last good sample, its TS unchanged
    assert run(reader.get_error_counter())["SCD30"]["ErrNum"][-1] == code("E", "READ")  # only the read error


def test_read_loop_gives_up_after_max_module_error_consecutive_failures_and_logs_via_real_print_log() -> None:
    reader = make_reader(max_module_error=1)
    _fake_init(reader)

    async def fake_fail() -> bool:
        raise OSError(5, "nak")

    # Faked on read_measurement() itself, the real single fault point post-fix - the getters are
    # never reached once it raises, so they're left as the real (pure cache-read) implementation;
    # read_measurement()'s own protocol-level fault handling is covered separately above.
    reader._scd.read_measurement = fake_fail  # type: ignore[method-assign]

    async def scenario() -> None:
        task = asyncio.create_task(reader._read_loop())
        await _settle(5)
        for _ in range(4):
            if task.done():
                break
            reader._read_event.set()
            await _settle(5)
        return await task

    assert run(scenario()) is None
    # Each failed cycle: the read's own entry, then the streak's; the second cycle exceeds max_module_error=1.
    read, streak, give_up = ("E", code("E", "READ")), ("E", code("E", "STREAK")), ("E", code("E", "GIVE_UP"))
    assert _entries(reader) == [read, streak, read, streak, give_up]
    assert run(reader.get_error_counter())["SCD30"]["ErrCount"] == 5


def test_read_loop_recovers_error_counter_after_a_good_read_following_failures() -> None:
    reader = make_reader(max_module_error=5)
    _fake_init(reader)
    fail_next = [True, True, False]
    resets = []

    async def flaky_read_measurement() -> bool:
        if fail_next.pop(0):
            raise OSError(5, "nak")
        return True

    async def fake_reset() -> None:  # the participant rung at the second failure, without its real 2.5 s wait
        resets.append(1)

    reader._scd.reset = fake_reset  # type: ignore[method-assign]

    reader._scd.read_measurement = flaky_read_measurement  # type: ignore[method-assign]

    async def fake_co2() -> float:
        return 500.0

    async def fake_ok() -> float:
        return 1.0

    reader._scd.get_CO2 = fake_co2  # type: ignore[method-assign]
    reader._scd.get_temperature = fake_ok  # type: ignore[method-assign]
    reader._scd.get_relative_humidity = fake_ok  # type: ignore[method-assign]

    async def scenario() -> "SCD30 | None":
        task = asyncio.create_task(reader._read_loop())
        await _settle(5)
        for _ in range(3):
            reader._read_event.set()
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
    assert resets == [1]
    assert [e for e in _entries(reader) if e[0] == "W"] == [("W", code("W", "DEVICE_RECOVERY"))]


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
        task = reader.start_asy_irq()
        await asyncio.sleep(0)
        is_task = isinstance(task, asyncio.Task)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return is_task

    assert run(scenario()) is True


def test_read_loop_ends_when_init_fails() -> None:
    reader = make_reader()
    reader_fake_i2c(reader).nak_addresses.add(_ADDR)
    assert run(reader._read_loop()) is None


# ---------------------------------------------------------------------------
# The recovery ladder's SCD30 rungs, the not-ready rules and the forced-recalibration readiness code
# (SPECIFICATION.md C.7 and M.2).
# ---------------------------------------------------------------------------


async def _no_reset() -> None:
    return None


def test_a_raising_reset_logs_one_chip_set_and_no_recovery_warning() -> None:
    reader = make_reader()

    async def failing_reset() -> None:
        raise OSError(5, "nak")

    reader._scd.reset = failing_reset  # type: ignore[method-assign]
    reader._err_cnt_internal = 2  # the second failed cycle: the participant rung's turn
    run(reader._climb_ladder())
    assert _entries(reader) == [("E", code("E", "CHIP_SET"))]


def test_the_third_failure_clears_the_bus_and_the_fourth_reinitialises_the_controller() -> None:
    reader = make_reader()
    reader._scd.reset = _no_reset  # type: ignore[method-assign]
    bus = reader._recovery_bus
    assert bus is not None
    marks = []
    for _ in range(4):
        run(reader._error_check((None, None, None, None)))
        marks.append(bus.recoveries)
    warnings = [e for e in _entries(reader) if e[0] == "W"]
    assert marks[1] < marks[2] < marks[3]  # one bus clear at the third failure, one controller rebuild at the fourth
    assert warnings == [("W", code("W", "DEVICE_RECOVERY")), ("W", code("W", "BUS_RECOVERY")), ("W", code("W", "BUS_RECOVERY"))]


def test_a_held_boot_bus_is_reported_once_at_setup() -> None:
    reader = make_reader()
    _fake_init(reader)
    statuses = [3, 0]
    bus = reader._recovery_bus
    assert bus is not None

    def take() -> int:
        return statuses.pop(0)

    bus.take_boot_clear_status = take  # type: ignore[method-assign]
    assert run(reader._init_scd()) is True
    assert run(reader._init_scd()) is True
    assert _entries(reader) == [("W", code("W", "BUS_RECOVERY"))]


def test_a_put_during_the_recovery_completes_after_it() -> None:
    # The rung holds the setter lock across the soft reset, so a PUT never meets a restarting chip.
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    _queue_snapshot(i2c)
    release = asyncio.Event()
    order = []

    async def slow_reset() -> None:
        order.append("reset")
        await release.wait()
        order.append("reset done")

    reader._scd.reset = slow_reset  # type: ignore[method-assign]

    async def scenario() -> "WriteValidity":
        with _FastAsyncSleep():
            rung = asyncio.create_task(reader._recover_device())
            await _settle(3)
            put = asyncio.create_task(reader._set_dict_cfg({"Altitude": 200}, reader.get_cfg_schema()))
            await _settle(5)
            assert not put.done()
            assert _arg_words(i2c) == []
            release.set()
            assert await rung is True
            return await put

    assert run(scenario()) == {"Altitude": "Valid"}
    assert order == ["reset", "reset done"]
    assert _arg_words(i2c) == [0x5102]


def test_a_not_ready_cycle_republishes_the_cached_reading_with_a_fresh_ts_and_no_error() -> None:
    # The owner's named exception to the staleness rule (owner, 2026-07-22, `110f3db`; SPECIFICATION.md A.4).
    reader = make_reader()
    i2c = reader_fake_i2c(reader)
    i2c.read_queue.append(register_frame(1))
    i2c.read_queue.append(data_frame(800.0, 21.0, 45.0))
    i2c.read_queue.append(register_frame(0))
    stamps = [1000, 2000]
    real_utc_now = asy_scd30_driver.utc_now
    asy_scd30_driver.utc_now = lambda: stamps.pop(0)
    try:
        with _FastAsyncSleep():
            run(reader._store_scd(*run(reader._read_scd())))
            first = run(reader.get_data())
            results, new_data = run(reader._read_scd())
            run(reader._store_scd(results, new_data))
    finally:
        asy_scd30_driver.utc_now = real_utc_now
    second = run(reader.get_data())
    assert new_data is False
    assert (second.CO2, second.Temp, second.Hum) == (first.CO2, first.Temp, first.Hum) == (800.0, 21.0, 45.0)
    assert (first.TS, second.TS) == (1000, 2000)
    assert (second.FRCState, second.FRCWait) == (first.FRCState, first.FRCWait)  # the state it already carries
    assert run(reader.get_error_counter())["SCD30"]["ErrCount"] == 0


def test_five_not_ready_reads_warn_once_and_new_data_clears() -> None:
    reader = make_reader()
    outcome: list[bool | None] = [False]

    async def read_measurement() -> bool:
        if outcome[0] is None:
            raise OSError(5, "nak")
        return outcome[0]

    async def fake_value() -> float:
        return 21.0

    reader._scd.read_measurement = read_measurement  # type: ignore[method-assign]
    reader._scd.get_CO2 = fake_value  # type: ignore[method-assign]
    reader._scd.get_temperature = fake_value  # type: ignore[method-assign]
    reader._scd.get_relative_humidity = fake_value  # type: ignore[method-assign]

    def cycles(*outcomes: "bool | None") -> "list[int]":
        warned = []
        for value in outcomes:
            outcome[0] = value
            run(reader._read_scd())
            warned.append(sum(1 for e in _entries(reader) if e == ("W", code("W", "SCD_NOT_READY"))))
        return warned

    assert cycles(False, False, False, False, False, False) == [0, 0, 0, 0, 1, 1]
    assert reader._not_ready_reads == 5  # held at the threshold
    assert cycles(True) == [1] and reader._not_ready_reads == 0
    cycles(False, False, False, False, False)
    log = run(reader.get_error_counter())["SCD30"]
    assert log["ErrCount"] == 2 and log["ErrNum"].count(code("W", "SCD_NOT_READY")) == 1  # one slot, newest-entry rule
    reader = make_reader()
    reader._scd.read_measurement = read_measurement  # type: ignore[method-assign]
    reader._scd.get_CO2 = fake_value  # type: ignore[method-assign]
    reader._scd.get_temperature = fake_value  # type: ignore[method-assign]
    reader._scd.get_relative_humidity = fake_value  # type: ignore[method-assign]
    assert cycles(False, False, False, None, False)[-1] == 0  # a raised read counts nothing toward it
    assert reader._not_ready_reads == 4
    _fake_init(reader)
    assert run(reader._init_scd()) is True
    assert reader._not_ready_reads == 0


def _frc_reader(interval: int = 2) -> SCD30_Reader:
    reader = make_reader()
    reader._frc_interval_s = interval
    return reader


async def _frc_feed(reader: SCD30_Reader, samples: "list[tuple[float, float]]") -> "list[tuple[int | None, int | None]]":
    # Each (CO2, temperature) as one new measurement through _store_scd(): the published (FRCState, FRCWait) after it.
    seen = []
    for co2, temperature in samples:
        await reader._store_scd((co2, temperature, 50.0, 1000), True)
        data = await reader.get_data()
        seen.append((data.FRCState, data.FRCWait))
    return seen


def test_frc_readiness_reaches_ready_after_the_settle_count_and_one_closed_window() -> None:
    # Interval 2 s: max(ceil(360 / 2), 5) = 180 samples (Low Power Mode note), FRCWindow 60 s = 30-sample windows.
    reader = _frc_reader()
    seen = run(_frc_feed(reader, [(800.0, 21.0)] * 180))
    assert seen[-1] == (4, None)
    assert [state for state, _wait in seen[:-1]] == [1] * 179
    assert [wait for _state, wait in seen[:-1]] == [(180 - k) * 2 for k in range(1, 180)]  # falls one interval per sample


def test_frc_readiness_names_drift_noise_and_a_temperature_step() -> None:
    drifting = [(800.0 + i, 21.0) for i in range(180)]  # 1 ppm per 2 s sample: 30 ppm/min over FRCRate 10
    noisy = [(800.0 + (30.0 if i % 2 else -30.0), 21.0) for i in range(180)]  # a residual near 31 ppm over FRCNoise 20
    stepped = [(800.0, 20.0 if i < 165 else 30.0) for i in range(180)]  # 10 degC x 2.5 ppm/degC over FRCNoise 20
    for samples, expected in ((drifting, 2), (noisy, 3), (stepped, 2)):
        assert run(_frc_feed(_frc_reader(), samples))[-1] == (expected, None), expected


def test_frc_readiness_restarts_on_a_gap_an_interval_change_a_pressure_write_and_a_stop() -> None:
    reader = _frc_reader()
    run(_frc_feed(reader, [(800.0, 21.0)] * 180))
    reader._frc_idle_ticks = 7  # 3.5 s since the last measurement: more than 1.5 intervals
    assert run(_frc_feed(reader, [(800.0, 21.0)]))[-1][0] == 1
    assert reader._frc_count == 1
    i2c = reader_fake_i2c(reader)
    for body in ({"MeasInterval": 4}, {"AmbPres": 1000}):
        run(_frc_feed(reader, [(800.0, 21.0)] * 10))
        _queue_snapshot(i2c)
        assert run(reader._set_dict_cfg(body, reader.get_cfg_schema())) == dict.fromkeys(body, "Valid")
        assert reader._frc_count == 0, body
    assert reader._frc_interval_s == 4
    assert reader._frc_measuring is True
    before = run(reader.get_data())
    _queue_snapshot(i2c)
    assert run(reader._set_dict_cfg({"ContMeas": False}, reader.get_cfg_schema())) == {"ContMeas": "Valid"}
    after = run(reader.get_data())
    assert (after.FRCState, after.FRCWait, after.TS, after.CO2) == (0, None, before.TS, before.CO2)
    assert reader._frc_measuring is False


def test_frc_readiness_publishes_not_measuring_after_two_intervals_without_data() -> None:
    reader = _frc_reader()
    run(_frc_feed(reader, [(800.0, 21.0)] * 3))
    _drive_irq_ticks(reader, [0] * 7)
    assert run(reader.get_data()).FRCState == 1
    _drive_irq_ticks(reader, [0])  # the eighth 500 ms tick: 4 x interval
    data = run(reader.get_data())
    assert (data.FRCState, data.FRCWait, data.TS) == (0, None, 1000)


def test_frc_counters_saturate_at_their_targets() -> None:
    reader = _frc_reader()
    run(_frc_feed(reader, [(800.0, 21.0)] * 400))
    assert reader._frc_count == 180
    assert reader._frc_n < 30
    _drive_irq_ticks(reader, [0] * 50)
    assert reader._frc_idle_ticks == 4 * 2 + 2


def test_a_forced_recalibration_while_settling_is_still_carried_out() -> None:
    reader = _frc_reader()
    run(_frc_feed(reader, [(800.0, 21.0)] * 3))
    assert run(reader.get_data()).FRCState == 1
    i2c = reader_fake_i2c(reader)
    _queue_snapshot(i2c)
    assert run(reader._set_dict_cfg({"ForceCalRef": 450}, reader.get_cfg_schema())) == {"ForceCalRef": "Valid"}
    assert scd30_nvm_writes(i2c) == {0x5204: 1}


def test_a_store_interleaved_with_a_republish_keeps_the_fresh_sample() -> None:
    reader = _frc_reader()
    run(_frc_feed(reader, [(800.0, 21.0)]))
    real_get = reader._get_meas_data

    async def yielding_get() -> object:
        await asyncio.sleep(0)  # a read-then-write republish would interleave here
        return await real_get()

    reader._get_meas_data = yielding_get  # type: ignore[method-assign, assignment]
    _queue_snapshot(reader_fake_i2c(reader))

    async def scenario() -> None:
        with _FastAsyncSleep():
            await asyncio.gather(reader._set_dict_cfg({"ContMeas": False}, reader.get_cfg_schema()), reader._store_scd((900.0, 22.0, 40.0, 2000), True))

    run(scenario())
    data = run(reader.get_data())
    assert (data.CO2, data.TS) == (900.0, 2000)


def test_a_full_length_frc_window_keeps_every_stored_sum_a_small_float() -> None:
    reader = _frc_reader()
    reader._frc_window_s = 3600  # 1800 samples at 2 s, the longest window
    run(_frc_feed(reader, [(800.0 + (i % 7), 21.0 + (i % 3) / 10) for i in range(1799)]))
    assert reader._frc_n == 1799
    for name in ("_frc_sum_d", "_frc_sum_d2", "_frc_sum_id", "_frc_co2_first", "_frc_t_first", "_frc_t_last"):
        value = getattr(reader, name)
        assert type(value) is float and abs(value) < 2**30, name


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
# SCD30_I2C._send_dev_command()'s CRC-generation guard - a real CRC8 object cannot fail add_into() through
# any command this driver sends (always a fixed 2-byte argument), so scd.crc is monkeypatched with a minimal
# fake, the same technique the SGP40 and UART driver suites use for their unreachable branches.
# ---------------------------------------------------------------------------


class _WrongLengthCRC:
    def length(self) -> int:
        return 1

    async def add_into(self, _buffer: bytearray, _size: int, start: int = 0, _init: "int | None" = None) -> int:  # start stays named: SCD30_I2C passes start=2
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


# ---------------------------------------------------------------------------
# Bus-hazard coverage moved from tests/test_bus_hazard_multi_device.py (SPECIFICATION.md Part
# C.8): genuinely SCD30-specific (decodes this driver's own wire protocol/API), not a generic
# cross-sensor shape, so it belongs here instead.
# ---------------------------------------------------------------------------


async def _gather(a: "Coroutine[Any, Any, Any]", b: "Coroutine[Any, Any, Any]") -> None:
    # asyncio.gather() itself returns a Future, not a Coroutine - mypy rejects passing it straight
    # to run() (same call-shape convention test_asy_i2c_driver.py's own scenario() wrapping uses).
    await asyncio.gather(a, b)


_CMD_GET_DATA_READY = b"\x02\x02"
_CMD_READ_MEASUREMENT = b"\x03\x00"
_CMD_SET_TEMPERATURE_OFFSET = b"\x54\x03"


def _parse_scd30_log(log: "Sequence[tuple[Any, ...]]", read_iterations: int) -> None:
    # Command-byte-based proof that same-device ops never interleave on the wire: parses the log into non-
    # overlapping runs and fails on any stray entry. A before/after log-length "span" check was rejected - a
    # coroutine blocked on the lock overlaps the holder's span, which is correct serialization.
    reads_parsed = 0
    writes_parsed = 0
    i = 0
    while i < len(log):
        entry = log[i]
        if entry[0] == "writeto" and bytes(entry[2][:2]) == _CMD_GET_DATA_READY:
            assert i + 3 < len(log), f"truncated read_measurement() sequence at log index {i}: {log[i:]}"
            assert log[i + 1][0] == "readfrom_into", f"expected readfrom_into at index {i + 1}, got {log[i + 1]}"
            assert log[i + 2][0] == "writeto" and bytes(log[i + 2][2][:2]) == _CMD_READ_MEASUREMENT, f"expected writeto(READ_MEASUREMENT) at index {i + 2}, got {log[i + 2]}"
            assert log[i + 3][0] == "readfrom_into", f"expected readfrom_into at index {i + 3}, got {log[i + 3]}"
            reads_parsed += 1
            i += 4
        elif entry[0] == "writeto" and bytes(entry[2][:2]) == _CMD_SET_TEMPERATURE_OFFSET:
            writes_parsed += 1
            i += 1
        else:
            raise AssertionError(f"unexpected/misplaced log entry at index {i} (interleaving corruption): {entry}")
    assert reads_parsed == read_iterations, f"parsed {reads_parsed} read cycles, expected {read_iterations}"
    assert writes_parsed == 1, f"parsed {writes_parsed} write(s), expected exactly 1"


def test_concurrent_read_and_write_never_interleave_on_the_wire_byte_exact() -> None:
    scd, i2c = make_scd()
    read_iterations = 6

    for _ in range(read_iterations):
        i2c.read_queue.append(register_frame(1))  # data-ready
        i2c.read_queue.append(data_frame(412.5, 23.4, 45.6))

    reads_completed = 0
    write_completed = False

    async def reader() -> None:
        nonlocal reads_completed
        for _ in range(read_iterations):
            await scd.read_measurement()
            reads_completed += 1

    async def writer() -> None:
        nonlocal write_completed
        await asyncio.sleep(0)  # let the reader get partway into its first cycle first
        await scd.set_temperature_offset(12.34)
        write_completed = True

    with _FastAsyncSleep():
        run(_gather(reader(), writer()))

    assert reads_completed == read_iterations
    assert write_completed
    _parse_scd30_log(list(i2c.log), read_iterations)  # a snapshot of the ring log, oldest first


def test_never_touches_any_address_but_its_own() -> None:
    scd, i2c = make_scd()
    for _ in range(40):  # generous - some methods issue more than one read
        i2c.read_queue.append(register_frame(1))
        i2c.read_queue.append(data_frame(400.0, 20.0, 50.0))

    async def exercise() -> None:
        for call in (
            scd.setup,
            scd.reset,
            scd.get_measurement_interval,
            scd.get_self_calibration_enabled,
            scd.get_ambient_pressure,
            scd.get_altitude,
            scd.get_temperature_offset,
            scd.get_forced_recalibration_reference,
            scd.get_config_snapshot,
            scd.read_measurement,
            scd.stop_continuous_measurement,
            lambda: scd.set_measurement_interval(5),
            lambda: scd.set_self_calibration_enabled(True),
            lambda: scd.set_ambient_pressure(1013),
            lambda: scd.set_altitude(100),
            lambda: scd.set_temperature_offset(1.0),
            lambda: scd.set_forced_recalibration_reference(500),
        ):
            try:
                await call()
            except Exception:  # only the addresses *touched* matter for this sweep, not success
                pass

    with _FastAsyncSleep():
        run(exercise())

    touched = {entry[1] for entry in i2c.log if entry[0] in ("writeto", "readfrom_into", "readfrom_mem", "writeto_mem")}
    assert touched == {_ADDR}, f"SCD30_I2C touched unexpected address(es): {touched - {_ADDR}}"


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
