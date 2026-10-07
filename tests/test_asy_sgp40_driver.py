"""Mocks only the raw I2C bus transaction level (tests/machine.py's fake machine.I2C, extended with a read_queue for word-oriented protocols - see its own inline comment), matching SPECIFICATION.md Part E.4's mocking boundary: asy_sgp40_driver.py's own protocol/CRC/locking logic and voc_algorithm.py's real VOCAlgorithm run unmocked."""
# FRAM-backed backup/restore tests use the real FRAMManager against tests/_fram_chip_fake.py's
# simulated chip, matching tests/test_fram_integration.py's own pattern.

import asyncio
import json
from collections import namedtuple

from _error_codes import code
from _fram_chip_fake import FakeMB85RS64V
from _tmp_scratch import TmpScratch
from machine import I2C as FakeI2C
from machine import Timer

import asy_base_classes
import asy_sgp40_driver
import asy_spi_driver
from asy_base_classes import ValueRef
from asy_fram_manager import FRAMManager
from asy_i2c_driver import I2C
from asy_print_log import LogConfig, PrintLogHistoryStore
from asy_sgp40_driver import SGP40, SGP40_I2C, SGP40_Reader, SgpBackup
from asy_spi_driver import SPI

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, Literal, TypeVar

    from typing_extensions import Self

    from asy_print_log import ErrorLog

    T = TypeVar("T")

# Same one-process-per-test-file FRAM chip swap as tests/test_fram_integration.py.
asy_spi_driver._SPI = FakeMB85RS64V  # type: ignore[misc]

# Per-test config-file isolation via tests/_tmp_scratch.py - see that module's docstring for the
# mechanism. Most tests here share _SHARED_CFG_DIR: they only rely on schema defaults, so they
# never write conflicting values. _sgp_cfg_dir() below serves the ones that do write real values.
_scratch = TmpScratch("sgp40")
_SHARED_CFG_DIR = _scratch.dir()


class _UTCValid:
    # The NTP client's first clock set of the boot, as utc_now() sees it, undone on exit.
    def __enter__(self) -> "_UTCValid":
        asy_base_classes.set_utc_valid()
        return self

    def __exit__(self, *_exc: object) -> None:
        asy_base_classes.set_utc_valid(valid=False)

_CRC_POLY = 0x31  # datasheet Table 7
# @tunable l1.asy_sgp40_driver_event_wait_s = 1
_EVENT_WAIT_S = 1


def _crc8(data: bytes) -> int:
    # Independent CRC-8 reimplementation for building fixtures - not the driver's own
    # asy_crc_checks.CRC8, so a bug shared between the two couldn't hide behind a self-consistent test.
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ _CRC_POLY) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def _word(value: int) -> bytes:
    payload = bytes([(value >> 8) & 0xFF, value & 0xFF])
    return payload + bytes([_crc8(payload)])


def test_the_defaulted_compensation_sources_carry_the_datasheets_own_values() -> None:
    # What buildgen wires when no live temperature/humidity source exists (Part L.6). Only the
    # class NAMES were pinned, by AST in tests_scripts/test_buildgen_defaults.py - the 25 degC /
    # 50 %RH themselves are a datasheet claim (Table 9) that nothing asserted at runtime.
    temp = asy_sgp40_driver._DefaultTemperatureSource()
    hum = asy_sgp40_driver._DefaultHumiditySource()
    assert run(temp.get_data()).value == 25.0
    assert run(hum.get_data()).value == 50.0


def test_a_defaulted_compensation_source_honours_an_explicit_value_and_coerces_it() -> None:
    # The TOML form is `{default = true, temperature = 25}`, so the value is caller-supplied and
    # arrives as whatever TOML parsed - float() is what keeps an int from reaching measure_raw().
    temp = asy_sgp40_driver._DefaultTemperatureSource(temperature=10)
    hum = asy_sgp40_driver._DefaultHumiditySource(relative_humidity=80)
    assert run(temp.get_data()).value == 10.0
    assert run(hum.get_data()).value == 80.0
    assert isinstance(run(temp.get_data()).value, float)
    assert isinstance(run(hum.get_data()).value, float)


def test_a_defaulted_source_returns_the_same_object_every_call_rather_than_allocating() -> None:
    # Built once in __init__ and handed out, not rebuilt per read: this is on the measurement path
    # of every VOC sample, and a fresh namedtuple per call would be a per-sample allocation.
    temp = asy_sgp40_driver._DefaultTemperatureSource()
    assert run(temp.get_data()) is run(temp.get_data())


def test_crc8_helper_matches_datasheet_example() -> None:
    assert _crc8(b"\xbe\xef") == 0x92


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


def _last_err(counter: "ErrorLog", field: 'Literal["ErrNum", "ErrType"]') -> "int | str":
    # ErrNum/ErrType are list-shaped once _error_check()/err_s() has run at least once - same
    # helper as test_asy_wifi_service.py's/test_asy_ntp_client.py's own, scoped to "SGP40".
    value = counter["SGP40"][field]
    assert isinstance(value, list)
    return value[-1]


def make_i2c() -> I2C:
    return I2C(1, scl_pin=19, sda_pin=18, frequency=50000)


def bus(i2c: I2C) -> FakeI2C:
    return i2c._i2c  # type: ignore[return-value]


def queue_successful_init(fake_bus: FakeI2C) -> None:
    # serial number (word[0] must be 0) then self-test success, in the order initialize() reads them.
    fake_bus.read_queue.append(_word(0x0000) + _word(0x1234) + _word(0x5678))
    fake_bus.read_queue.append(_word(0xD400))


def make_sgp() -> SGP40_I2C:
    return SGP40_I2C(make_i2c())


# ---------------------------------------------------------------------------
# initialize() - serial number / self-test gates (feature-set check removed: not in datasheet Table 8; owner-confirmed, 2026-07-21)
# ---------------------------------------------------------------------------


def test_initialize_success_probes_serial_number_then_self_test_then_resets() -> None:
    sgp = make_sgp()
    fake_bus = bus(sgp._i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    run(sgp.initialize())
    writes = [entry for entry in fake_bus.log if entry[0] == "writeto"]
    assert writes[0][1:3] == (0x59, b"\x36\x82")  # get serial number
    assert writes[1][1:3] == (0x59, b"\x28\x0e")  # execute self-test
    assert writes[2] == ("writeto", 0x00, b"\x06", True)  # true general-call reset - the bug fix


def test_initialize_serial_number_mismatch_raises() -> None:
    sgp = make_sgp()
    fake_bus = bus(sgp._i2c_sgp40.i2c_device.i2c)
    fake_bus.read_queue.append(_word(0x0001) + _word(0x1234) + _word(0x5678))  # word[0] != 0
    try:
        run(sgp.initialize())
        raise AssertionError("expected RuntimeError")
    except RuntimeError as e:
        assert "serial number does not match" in str(e)


def test_initialize_self_test_failure_raises() -> None:
    sgp = make_sgp()
    fake_bus = bus(sgp._i2c_sgp40.i2c_device.i2c)
    fake_bus.read_queue.append(_word(0x0000) + _word(0x1234) + _word(0x5678))
    fake_bus.read_queue.append(_word(0x4B00))  # datasheet: one or more tests failed
    try:
        run(sgp.initialize())
        raise AssertionError("expected RuntimeError")
    except RuntimeError as e:
        assert "self test failed" in str(e)


def test_initialize_self_test_success_ignores_nonzero_low_byte() -> None:
    # Regression test: datasheet Table 13 documents 0xD4 0xXX as "all tests passed, ignore 0xXX" -
    # the low byte is not guaranteed to be 0x00. A prior version (inherited from the deployed
    # driver) checked the full word against 0xD400 and would have spuriously raised here.
    sgp = make_sgp()
    fake_bus = bus(sgp._i2c_sgp40.i2c_device.i2c)
    fake_bus.read_queue.append(_word(0x0000) + _word(0x1234) + _word(0x5678))
    fake_bus.read_queue.append(_word(0xD4FF))  # high byte 0xD4 = pass, non-zero low byte
    run(sgp.initialize())  # must not raise


def test_initialize_no_feature_set_check_is_issued() -> None:
    # Regression test for the dropped, undocumented 0x20 0x2F check (see BACKLOG.md).
    sgp = make_sgp()
    fake_bus = bus(sgp._i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    run(sgp.initialize())
    commands = [entry[2] for entry in fake_bus.log if entry[0] == "writeto"]
    assert b"\x20\x2f" not in commands


def test_initialize_bus_nak_propagates_as_oserror() -> None:
    # Real transaction failures are allowed to propagate uncaught from SGP40_I2C
    # (SPECIFICATION.md Part D.2's I2C carve-out) - SGP40_Reader._init_sgp() is what closes this gap.
    sgp = make_sgp()
    fake_bus = bus(sgp._i2c_sgp40.i2c_device.i2c)
    fake_bus.nak_addresses.add(0x59)
    try:
        run(sgp.initialize())
        raise AssertionError("expected OSError")
    except OSError:
        pass


def test_initialize_corrupted_response_raises_crc_error() -> None:
    sgp = make_sgp()
    fake_bus = bus(sgp._i2c_sgp40.i2c_device.i2c)
    good = _word(0x0000) + _word(0x1234) + _word(0x5678)
    corrupted = bytes([good[0] ^ 0xFF]) + good[1:]  # flip a payload byte, CRC no longer matches
    fake_bus.read_queue.append(corrupted)
    try:
        run(sgp.initialize())
        raise AssertionError("expected RuntimeError")
    except RuntimeError as e:
        assert "CRC" in str(e)


# ---------------------------------------------------------------------------
# _reset() - true I2C general call (the confirmed datasheet-vs-code bug, now fixed)
# ---------------------------------------------------------------------------


def test_reset_writes_single_byte_to_general_call_address_zero() -> None:
    sgp = make_sgp()
    fake_bus = bus(sgp._i2c_sgp40.i2c_device.i2c)
    run(sgp._reset())
    assert fake_bus.log[-1] == ("writeto", 0x00, b"\x06", True)
    # Not the SGP40's own address, and not the old two-byte [0x00, 0x06] payload sent to it.
    assert all(entry[1] != 0x59 for entry in fake_bus.log if entry[0] == "writeto")


def test_reset_tolerates_nak_at_general_call_address() -> None:
    sgp = make_sgp()
    fake_bus = bus(sgp._i2c_sgp40.i2c_device.i2c)
    fake_bus.nak_addresses.add(0x00)  # not every device on the bus needs to support a general call
    run(sgp._reset())  # must not raise


# ---------------------------------------------------------------------------
# temperature/humidity-to-ticks conversion (datasheet Table 10 worked examples)
# ---------------------------------------------------------------------------


def test_celsius_to_ticks_matches_datasheet_table_10() -> None:
    buf = bytearray(2)
    SGP40_I2C._celsius_to_ticks(25, buf)
    assert bytes(buf) == b"\x66\x66"
    SGP40_I2C._celsius_to_ticks(-45, buf)
    assert bytes(buf) == b"\x00\x00"
    SGP40_I2C._celsius_to_ticks(130, buf)
    assert bytes(buf) == b"\xff\xff"


def test_celsius_to_ticks_rounds_to_nearest_not_truncates() -> None:
    # 24C -> 25839.514285... ticks: truncation would give 25839 (0x64EF), rounding gives 25840
    # (0x64F0) - matches _relative_humidity_to_ticks()'s own round-to-nearest convention.
    buf = bytearray(2)
    SGP40_I2C._celsius_to_ticks(24, buf)
    assert bytes(buf) == b"\x64\xf0"


def test_relative_humidity_to_ticks_matches_datasheet_table_10() -> None:
    buf = bytearray(2)
    SGP40_I2C._relative_humidity_to_ticks(50, buf)
    assert bytes(buf) == b"\x80\x00"
    SGP40_I2C._relative_humidity_to_ticks(0, buf)
    assert bytes(buf) == b"\x00\x00"
    SGP40_I2C._relative_humidity_to_ticks(100, buf)
    assert bytes(buf) == b"\xff\xff"


# ---------------------------------------------------------------------------
# measure_raw / get_raw - compensated command construction and CRC-checked response parsing
# ---------------------------------------------------------------------------


def test_measure_raw_default_command_matches_datasheet_no_compensation() -> None:
    sgp = make_sgp()
    fake_bus = bus(sgp._i2c_sgp40.i2c_device.i2c)
    fake_bus.read_queue.append(_word(30000))
    raw = run(sgp.measure_raw())  # defaults: 25C, 50%RH
    assert raw == 30000
    writes = [entry for entry in fake_bus.log if entry[0] == "writeto"]
    assert writes[-1][2] == b"\x26\x0f\x80\x00\xa2\x66\x66\x93"  # datasheet Table 9's own example


def test_measure_raw_custom_compensation_encodes_correct_ticks_and_crc() -> None:
    sgp = make_sgp()
    fake_bus = bus(sgp._i2c_sgp40.i2c_device.i2c)
    fake_bus.read_queue.append(_word(12345))
    run(sgp.measure_raw(temperature=-45, relative_humidity=0))
    writes = [entry for entry in fake_bus.log if entry[0] == "writeto"]
    sent = writes[-1][2]
    assert sent[0:2] == b"\x26\x0f"
    assert sent[2:5] == b"\x00\x00\x81"  # 0% RH -> 0x0000, CRC 0x81 (Table 10)
    assert sent[5:8] == b"\x00\x00\x81"  # -45C -> 0x0000, CRC 0x81 (Table 10)


def test_get_raw_crc_mismatch_raises() -> None:
    sgp = make_sgp()
    fake_bus = bus(sgp._i2c_sgp40.i2c_device.i2c)
    good = _word(1000)
    fake_bus.read_queue.append(bytes([good[0] ^ 0xFF]) + good[1:])
    try:
        run(sgp.get_raw())
        raise AssertionError("expected RuntimeError")
    except RuntimeError as e:
        assert "CRC" in str(e)


# ---------------------------------------------------------------------------
# measure_index_and_raw - VOC algorithm wiring
# ---------------------------------------------------------------------------


def test_measure_index_and_raw_returns_voc_index_and_raw() -> None:
    sgp = make_sgp()
    fake_bus = bus(sgp._i2c_sgp40.i2c_device.i2c)
    fake_bus.read_queue.append(_word(30000))
    voc_index, raw, serialized, deserialized = run(sgp.measure_index_and_raw(temperature=25, relative_humidity=50))
    assert raw == 30000
    assert isinstance(voc_index, int)
    assert serialized is False
    assert deserialized is False


def test_measure_index_and_raw_reset_reinitializes_algorithm_state() -> None:
    sgp = make_sgp()
    fake_bus = bus(sgp._i2c_sgp40.i2c_device.i2c)
    for _ in range(5):
        fake_bus.read_queue.append(_word(30000))
        run(sgp.measure_index_and_raw())
    assert sgp._voc_algorithm is not None
    assert sgp._voc_algorithm.params.muptime > 0
    fake_bus.read_queue.append(_word(30000))
    run(sgp.measure_index_and_raw(reset=True))
    # vocalgorithm_reset() runs before this same call's own vocalgorithm_process(), which then
    # advances muptime by exactly one sample - proves the reset actually happened, not a no-op.
    assert sgp._voc_algorithm.params.muptime == 1 * 65536


# ---------------------------------------------------------------------------
# SGP40_Reader - err_cnt_internal regression, comp-data handling, error counting
# ---------------------------------------------------------------------------


_CompReading = namedtuple("_CompReading", ("Temp", "Hum"))


class _FakeCompSource:
    # Structural stand-in for a compensation producer (Part C.14, L.6.3): only get_data() is read,
    # through each ValueRef's field.
    def __init__(self, temp: "float | None" = 25.0, hum: "float | None" = 50.0, *, raise_exc: bool = False) -> None:
        self._temp = temp
        self._hum = hum
        self._raise = raise_exc

    async def get_data(self) -> "Any":
        if self._raise:
            raise RuntimeError("simulated compensation-source failure")
        return _CompReading(self._temp, self._hum)


def make_reader(**kwargs: "Any") -> SGP40_Reader:
    kwargs.setdefault("cfg_path", _SHARED_CFG_DIR)
    reader = SGP40_Reader(
        make_i2c(),
        ValueRef(_FakeCompSource(), "Temp"),
        ValueRef(_FakeCompSource(), "Hum"),
        max_module_error=2,
        **kwargs,
    )
    run(reader.setup())
    return reader


def test_init_sgp_resets_the_real_base_class_error_counter() -> None:
    # Regression test: _init_sgp() used to write self.err_cnt_internal (no underscore), a dead
    # attribute distinct from asy_base_classes.py's real self._err_cnt_internal (see BACKLOG.md).
    reader = make_reader()
    reader._err_cnt_internal = 7  # simulate a streak accumulated before a supervisor restart
    fake_bus = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    ok = run(reader._init_sgp())
    assert ok is True
    assert reader._err_cnt_internal == 0
    assert not hasattr(reader, "err_cnt_internal")  # the old, mistyped dead attribute must not exist


def test_read_sgp_without_compensation_data_returns_all_none() -> None:
    reader = SGP40_Reader(
        make_i2c(),
        ValueRef(_FakeCompSource(None, None), "Temp"),
        ValueRef(_FakeCompSource(None, None), "Hum"),
        max_module_error=2,
        cfg_path=_SHARED_CFG_DIR,
    )
    run(reader.setup())
    data, compensated, serialized = run(reader._read_sgp(None, serialize=False, deserialize=False))
    assert data == SGP40(None, None, None)
    assert compensated is False
    assert serialized is False


def test_read_sgp_without_compensation_data_yet_logs_nothing() -> None:
    # Regression test for the boot-race false error (SPECIFICATION.md Part C.14.2): a compensation
    # source whose field is legitimately still None (SCD30 has not finished its first post-boot
    # measurement) is startup jitter, not a fault, and must log no E/W entry at all.

    # The old code called float(getattr(...)) inside the try meant to catch a genuine read failure,
    # so a None field raised TypeError there and was misreported as "Compensation data read failed"
    # (SOURCE) plus a "No compensation data available!" warning. Neither may fire here now.
    reader = SGP40_Reader(
        make_i2c(),
        ValueRef(_FakeCompSource(None, None), "Temp"),
        ValueRef(_FakeCompSource(None, None), "Hum"),
        max_module_error=2,
        cfg_path=_SHARED_CFG_DIR,
    )
    run(reader.setup())
    data, compensated, serialized = run(reader._read_sgp(None, serialize=False, deserialize=False))
    assert data == SGP40(None, None, None)
    assert compensated is False
    assert serialized is False
    log = run(reader.get_error_counter())
    assert log["SGP40"]["ErrCount"] == 0, f"expected startup jitter must not log any E/W entry ({log!r})"


def test_read_sgp_with_one_of_two_compensation_fields_still_none_logs_nothing() -> None:
    # Same regression as above, but only one of the two wired fields is still None - the getattr()
    # default catches each field independently, so a partial startup race (e.g. temperature already
    # measured, humidity not yet) must be just as silent as both being None.
    reader = SGP40_Reader(
        make_i2c(),
        ValueRef(_FakeCompSource(25.0, None), "Temp"),
        ValueRef(_FakeCompSource(25.0, None), "Hum"),
        max_module_error=2,
        cfg_path=_SHARED_CFG_DIR,
    )
    run(reader.setup())
    data, compensated, serialized = run(reader._read_sgp(None, serialize=False, deserialize=False))
    assert data == SGP40(None, None, None)
    assert compensated is False
    assert serialized is False
    log = run(reader.get_error_counter())
    assert log["SGP40"]["ErrCount"] == 0


def test_read_sgp_with_compensation_data_stores_a_result() -> None:
    reader = make_reader()
    fake_bus = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
    fake_bus.read_queue.append(_word(31000))
    with _UTCValid():
        data, compensated, _serialized = run(reader._read_sgp(None, serialize=False, deserialize=False))
    assert compensated is True
    assert data.Raw == 31000
    assert isinstance(data.VOC, int)
    assert data.TS is not None


def test_a_pre_sync_read_publishes_ts_none_and_steps_no_streak() -> None:
    # utc_now() is None until the NTP client sets the clock: a good read returns TS None, and the
    # read loop's condition counts only a compensated cycle whose measured values are gone.
    reader = make_reader()
    fake_bus = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
    fake_bus.read_queue.append(_word(31000))
    data, compensated, _serialized = run(reader._read_sgp(None, serialize=False, deserialize=False))
    assert data.TS is None
    assert data.VOC is not None and data.Raw == 31000
    assert run(reader._error_check(data, condition=compensated and data[0] is None)) is True
    assert reader._err_cnt_internal == 0
    run(reader._store_sgp(data))
    assert run(reader.get_data()) == data


def test_a_failed_read_keeps_the_last_good_sample_and_its_timestamp() -> None:
    reader = make_reader()
    fake_bus = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
    fake_bus.read_queue.append(_word(31000))
    with _UTCValid():
        good, _compensated, _serialized = run(reader._read_sgp(None, serialize=False, deserialize=False))
        run(reader._store_sgp(good))
        fake_bus.nak_addresses.add(0x59)
        failed, _compensated, _serialized = run(reader._read_sgp(None, serialize=False, deserialize=False))
        run(reader._store_sgp(failed))
    assert good.TS is not None
    assert failed.VOC is None and failed.Raw is None
    assert run(reader.get_data()) == good  # the last good sample, its TS unchanged
    assert run(reader.get_error_counter())["SGP40"]["ErrNum"][-1] == code("E", "READ")  # only the read error


def test_store_sgp_ignores_partial_none_results() -> None:
    reader = make_reader()
    run(reader._store_sgp(SGP40(None, 100, 12345)))
    assert run(reader.get_data()) == SGP40(None, None, None)


def test_store_sgp_persists_a_complete_result() -> None:
    reader = make_reader()
    run(reader._store_sgp(SGP40(42, 31000, 12345)))
    assert run(reader.get_data()) == SGP40(42, 31000, 12345)


def test_store_sgp_accepts_a_result_without_a_timestamp() -> None:
    reader = make_reader()
    run(reader._store_sgp(SGP40(42, 31000, None)))  # a sample taken before the first NTP sync
    assert run(reader.get_data()) == SGP40(42, 31000, None)


def test_check_storage_without_fram_returns_no_buffer_and_resets_voc_timers() -> None:
    reader = make_reader()  # no backup -> _ts_storage is None
    reader._voc_init = 5
    reader._voc_write = 5
    buf, serialize, deserialize, cfg_values = run(reader._check_storage())
    assert (buf, serialize, deserialize, cfg_values) == (None, False, False, None)
    assert reader._voc_init == 0
    assert reader._voc_write == 0


def test_run_restore_without_deserialize_trigger_is_a_no_op() -> None:
    reader = make_reader()
    assert run(reader._run_restore(None, deserialize=False, cfg_values=None)) is False


def test_get_mem_status_reflects_last_backup_and_restored_from() -> None:
    reader = make_reader()
    assert run(reader.get_mem_status()) == (None, None)
    reader._last_backup = 111
    reader._restored_from = 222
    assert run(reader.get_mem_status()) == (111, 222)


def test_get_error_counter_reflects_logged_errors() -> None:
    reader = make_reader()
    run(reader.setup())
    empty = SGP40(None, None, None)
    run(reader._error_check(empty))
    run(reader._error_check(empty))
    run(reader._error_check(empty))  # exceeds max_module_error=2 -> logged as a real error
    log = run(reader.get_error_counter())
    err_count = log["SGP40"]["ErrCount"]
    assert isinstance(err_count, int)
    assert err_count >= 1


def test_start_asy_read_returns_a_real_task() -> None:
    reader = make_reader()
    fake_bus = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)

    async def scenario() -> bool:
        task = reader.start_asy_read()
        await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return True

    with _FastAsyncSleep():
        assert run(scenario()) is True


def test_start_timer_and_stop_timer_wire_the_trigger_event() -> None:
    reader = make_reader()
    reader.start_timer()
    assert reader._trigger_timer.callback is not None
    reader._trigger_timer.trigger()  # fake machine.Timer.trigger() - fires the callback synchronously
    assert run(asyncio.wait_for(reader._read_event.wait(), _EVENT_WAIT_S)) is None
    reader.stop_timer()
    assert reader._trigger_timer.deinit_called is True


class _RaiseOnArm:
    # Same technique as the _RaiseOnArm in the asy_system_service/wifi suites - toggles
    # tests/machine.py's shared Timer.raise_on_arm for the `with` block. `exc` picks which arm of
    # `except (OSError, MemoryError)` runs; MemoryError is no OSError subclass (Part F).
    def __init__(self, exc: "type[BaseException]" = OSError) -> None:
        self._exc = exc

    def __enter__(self) -> "Self":
        Timer.raise_on_arm_exc = self._exc
        Timer.raise_on_arm = True
        return self

    def __exit__(self, *exc_info: object) -> None:
        Timer.raise_on_arm = False
        Timer.raise_on_arm_exc = OSError


def test_start_timer_degrades_gracefully_when_alarm_pool_exhausted() -> None:
    # start_timer() runs as a trigger starter (get_trigger_starters()); a raise there would leave this
    # sensor untriggered, so an arm failure degrades instead.
    reader = make_reader()
    with _RaiseOnArm():
        reader.start_timer()  # must not raise despite the timer failing to arm
    assert reader._trigger_timer.period == -1  # never actually armed
    assert reader._trigger_timer.callback is None  # nor wired to the trigger event
    assert reader.pr._err_count == 0  # start_timer() logs via the non-persisting pr.err(), not err_s()


def test_start_timer_degrades_gracefully_on_a_memory_error() -> None:
    # Sibling of the OSError test above, for the other arm of start_timer()'s own
    # `except (OSError, MemoryError)` - same graceful degradation must hold either way.
    reader = make_reader()
    with _RaiseOnArm(MemoryError):
        reader.start_timer()  # must not raise despite the timer failing to arm
    assert reader._trigger_timer.period == -1  # never actually armed
    assert reader._trigger_timer.callback is None  # nor wired to the trigger event
    assert reader.pr._err_count == 0  # start_timer() logs via the non-persisting pr.err(), not err_s()


def test_error_check_gives_up_after_max_module_error_consecutive_failures() -> None:
    reader = make_reader()  # max_module_error=2
    empty = SGP40(None, None, None)
    assert run(reader._error_check(empty)) is True  # 1st failure
    assert run(reader._error_check(empty)) is True  # 2nd failure
    assert run(reader._error_check(empty)) is False  # 3rd failure exceeds max_module_error=2


def test_error_check_recovers_after_a_success() -> None:
    reader = make_reader()
    empty = SGP40(None, None, None)
    good = SGP40(1, 30000, 12345)
    run(reader._error_check(empty))
    run(reader._error_check(empty))
    assert run(reader._error_check(good)) is True
    assert reader._err_cnt_internal == 1  # decremented by the success, not reset to 0


def test_reset_voc_true_sets_the_reset_flag() -> None:
    reader = make_reader()
    assert reader._reset_pending is False
    assert run(reader.reset_voc(flag=True)) is True  # uniform setter return contract: True = applied
    assert reader._reset_pending is True


def test_reset_voc_false_is_a_no_op() -> None:
    reader = make_reader()
    reader._reset_pending = True
    assert run(reader.reset_voc(flag=False)) is False  # uniform setter return contract: False = no-op
    assert reader._reset_pending is True  # unchanged - reset_voc's own documented contract


def test_push_reset_voc_wrapper_delegates_to_reset_voc() -> None:
    reader = make_reader()
    assert run(reader._push_reset_voc(True)) is True
    assert reader._reset_pending is True


def test_push_reset_voc_wrapper_reports_success_even_when_flag_is_false() -> None:
    # reset_voc(flag=False) is a legitimate no-op, not a push failure - the wrapper must not
    # forward its False-means-no-op return as a False-means-push-failed result, or _set_dict_cfg
    # would misreport a valid `ResetVOC: false` as "Failed" and run the recovery chain.
    reader = make_reader()
    assert run(reader._push_reset_voc(False)) is True
    assert reader._reset_pending is False


def test_push_reset_voc_wrapper_rejects_a_non_bool_value_defensively() -> None:
    # _set_dict_cfg only ever invokes a push callback with an already schema-validated value (real
    # bool, by construction) - this guards the type for the checker and as defense-in-depth, not
    # because a real caller can reach it with the wrong type.
    reader = make_reader()
    assert run(reader._push_reset_voc("not a bool")) is False
    assert run(reader._push_reset_voc(1)) is False
    assert reader._reset_pending is False


def test_set_dict_cfg_reset_voc_triggers_the_reset_and_is_never_persisted() -> None:
    # The direct trigger mechanism replacing legacy's cmd_keys: ResetVOC goes through the same
    # generic _set_dict_cfg() path as any other field, but its special-alone shape (def=None,
    # special=True) means ConfigManager never stores it - write_config()'s "valid but not stored".
    cfg_dir = _sgp_cfg_dir("resetvoc_trigger")
    reader = SGP40_Reader(make_i2c(), ValueRef(_FakeCompSource(), "Temp"), ValueRef(_FakeCompSource(), "Hum"), max_module_error=2, cfg_path=cfg_dir)
    run(reader.setup())
    results = run(reader._set_dict_cfg({"ResetVOC": True}, reader.get_cfg_schema()))
    assert results == {"ResetVOC": "Valid"}
    assert reader._reset_pending is True
    with open(cfg_dir + _SGP_CFG_FILE) as f:
        assert "ResetVOC" not in f.read()  # never written to disk


def test_set_dict_cfg_reset_voc_re_fires_every_time_not_just_on_change() -> None:
    # Unlike an ordinary field, which only pushes on an actual change, a special-alone field has
    # no previous value to compare against, so write_config() always reports it "Valid" and the
    # same value twice re-triggers the push - the repeatable "reset now" semantic reset_voc() needs.
    cfg_dir = _sgp_cfg_dir("resetvoc_refire")
    reader = SGP40_Reader(make_i2c(), ValueRef(_FakeCompSource(), "Temp"), ValueRef(_FakeCompSource(), "Hum"), max_module_error=2, cfg_path=cfg_dir)
    run(reader.setup())
    first = run(reader._set_dict_cfg({"ResetVOC": True}, reader.get_cfg_schema()))
    reader._reset_pending = False  # simulate the reset having already completed and cleared by _read_loop()
    second = run(reader._set_dict_cfg({"ResetVOC": True}, reader.get_cfg_schema()))
    assert first == {"ResetVOC": "Valid"}
    assert second == {"ResetVOC": "Valid"}
    assert reader._reset_pending is True  # the second request re-armed it


def test_set_dict_cfg_reset_voc_false_reports_valid_not_failed() -> None:
    # End-to-end regression test for the _push_reset_voc fix above: `{"ResetVOC": false}` is a
    # legitimate no-op matching reset_voc(flag=False)'s contract and must surface as "Valid", not
    # "Failed" - without triggering the sensor read or leaving work for _recover_failed_push.
    cfg_dir = _sgp_cfg_dir("resetvoc_false")
    reader = SGP40_Reader(make_i2c(), ValueRef(_FakeCompSource(), "Temp"), ValueRef(_FakeCompSource(), "Hum"), max_module_error=2, cfg_path=cfg_dir)
    run(reader.setup())
    results = run(reader._set_dict_cfg({"ResetVOC": False}, reader.get_cfg_schema()))
    assert results == {"ResetVOC": "Valid"}
    assert reader._reset_pending is False


def test_get_dict_cfg_unaffected_by_the_command_only_reset_field_in_the_schema() -> None:
    # get_dict_cfg() deliberately passes its own BackupPeriod/BackupMaxAge/WaitTimeNTP schema
    # rather than get_cfg_schema() (which includes ResetVOC) - ConfigManager.get_dict() is
    # all-or-nothing on a key never in _cache (see asy_sgp40_driver.py's _VAL_RESET_VOC comment).
    reader = make_reader()
    result = run(reader.get_dict_cfg())
    assert result == {"SGP40": {"BackupPeriod": 1, "BackupMaxAge": 7200, "WaitTimeNTP": 30}}


def test_reset_never_drops_but_each_sub_part_completes_at_most_once() -> None:
    # Reset has two independently tracked sub-parts (_reset_fram_cleared/_reset_algo_applied):
    # self._reset_pending only clears once BOTH have succeeded, so a user's request is never silently
    # dropped, but neither part repeats once it succeeded while the other is still retrying.
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    reader = SGP40_Reader(
        make_i2c(),
        ValueRef(_FakeCompSource(None, None), "Temp"),
        ValueRef(_FakeCompSource(None, None), "Hum"),
        backup=SgpBackup(manager, _ntp_synced),
        log=LogConfig(manager, 10, None),
        max_module_error=5,
        cfg_path=_SHARED_CFG_DIR,
    )
    run(reader.setup())
    fake_bus = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    run(reader._init_sgp())
    run(reader.reset_voc(flag=True))
    reset_after_request = reader._reset_pending
    assert reset_after_request is True

    # Cycle 1: no compensation data yet, but the FRAM clear does not depend on it and succeeds
    # against the real chip this cycle. The algorithm-reset half has not run (measure_index_and_raw()
    # is never reached without compensation data), so the request as a whole stays pending.
    run(reader._read_sgp(None, serialize=False, deserialize=False))
    # Snapshotting into locals before each assert sidesteps a real mypy narrowing limitation: once
    # `reader._reset_pending is True` is asserted, mypy keeps that narrowing across the intervening run()
    # calls and flags a later `is False` as unreachable, though it does change at runtime.
    reset_mid = reader._reset_pending
    fram_cleared_mid = reader._reset_fram_cleared
    algo_applied_mid = reader._reset_algo_applied
    assert reset_mid is True
    assert fram_cleared_mid is True
    assert algo_applied_mid is False

    # Pause FRAM storage: if _read_sgp() incorrectly re-attempted the already-succeeded clear(), it
    # would now fail and leave self._reset_pending stuck True forever - proving it does NOT touch FRAM again.
    manager.set_pause(value=True)
    reader._temperature = ValueRef(_FakeCompSource(), "Temp")
    reader._humidity = ValueRef(_FakeCompSource(), "Hum")
    fake_bus.read_queue.append(_word(30000))
    run(reader._read_sgp(None, serialize=False, deserialize=False))
    manager.set_pause(value=False)
    reset_final = reader._reset_pending
    assert reset_final is False  # both parts satisfied - the clear was correctly not retried
    voc_algorithm = reader._sgp._voc_algorithm
    assert voc_algorithm is not None
    assert voc_algorithm.params.muptime == 1 * 65536  # vocalgorithm_reset() applied exactly once


def test_reset_retries_only_the_fram_half_once_the_algo_half_already_succeeded() -> None:
    # Mirror of the test above: the algorithm reset succeeds first (compensation data available
    # immediately), but the FRAM clear keeps failing (paused) - vocalgorithm_reset() must NOT run
    # again on a later cycle just because the FRAM half is still incomplete.
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    reader = SGP40_Reader(
        make_i2c(),
        ValueRef(_FakeCompSource(), "Temp"),
        ValueRef(_FakeCompSource(), "Hum"),
        backup=SgpBackup(manager, _ntp_synced),
        log=LogConfig(manager, 10, None),
        max_module_error=5,
        cfg_path=_SHARED_CFG_DIR,
    )
    run(reader.setup())
    fake_bus = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    run(reader._init_sgp())
    manager.set_pause(value=True)  # FRAM clear fails every attempt until unpaused below
    run(reader.reset_voc(flag=True))

    # Local-variable snapshots throughout (rather than repeated bare `reader._reset_pending`/
    # `reader._sgp._voc_algorithm` attribute access) sidestep a real mypy narrowing limitation - see
    # the matching comment in test_reset_never_drops_but_each_sub_part_completes_at_most_once above.
    fake_bus.read_queue.append(_word(30000))
    run(reader._read_sgp(None, serialize=False, deserialize=False))
    reset_after_cycle1 = reader._reset_pending
    algo_applied_after_cycle1 = reader._reset_algo_applied
    voc_algorithm = reader._sgp._voc_algorithm
    assert reset_after_cycle1 is True  # FRAM half still pending
    assert algo_applied_after_cycle1 is True  # algorithm reset already succeeded, first cycle
    assert voc_algorithm is not None
    assert voc_algorithm.params.muptime == 1 * 65536

    # Retry with the FRAM clear still failing - the algorithm reset must NOT run again (muptime
    # keeps advancing by one sample per call, never resetting back to 1 * 65536).
    fake_bus.read_queue.append(_word(30000))
    run(reader._read_sgp(None, serialize=False, deserialize=False))
    reset_after_cycle2 = reader._reset_pending
    assert reset_after_cycle2 is True
    assert voc_algorithm.params.muptime == 2 * 65536
    # The failed clear keeps SGP40's own entry beside the store's refusal (C.7: each layer logs).
    assert _last_err(run(reader.get_error_counter()), "ErrNum") == code("E", "SGP_BACKUP_CLEAR")
    assert code("W", "FRAM_PAUSED") in _warnings(run(manager.pr.get_log()))

    # FRAM finally recovers - the reset completes, still without ever re-applying the algo reset.
    manager.set_pause(value=False)
    fake_bus.read_queue.append(_word(30000))
    run(reader._read_sgp(None, serialize=False, deserialize=False))
    reset_after_cycle3 = reader._reset_pending
    assert reset_after_cycle3 is False
    assert voc_algorithm.params.muptime == 3 * 65536


def test_read_sgp_nan_compensation_temperature_is_caught_not_propagated() -> None:
    # _celsius_to_ticks()/_relative_humidity_to_ticks() call int() on a compensation value never
    # validated beyond "not None" - confirmed against the real interpreter that NaN raises
    # ValueError and Inf OverflowError. Structurally safe inside _read_sgp()'s try, but untested.
    reader = make_reader()
    reader._temperature = ValueRef(_FakeCompSource(float("nan"), 50.0), "Temp")
    reader._humidity = ValueRef(_FakeCompSource(float("nan"), 50.0), "Hum")
    run(reader.setup())
    data, compensated, serialized = run(reader._read_sgp(None, serialize=False, deserialize=False))
    assert data == SGP40(None, None, None)
    assert compensated is True  # comp data was "available" (not None) - the arithmetic itself failed
    assert serialized is False
    log = run(reader.get_error_counter())
    err_count = log["SGP40"]["ErrCount"]
    assert isinstance(err_count, int)
    assert err_count >= 1


def test_read_sgp_inf_compensation_humidity_is_caught_not_propagated() -> None:
    reader = make_reader()
    reader._temperature = ValueRef(_FakeCompSource(25.0, float("inf")), "Temp")
    reader._humidity = ValueRef(_FakeCompSource(25.0, float("inf")), "Hum")
    run(reader.setup())
    data, compensated, serialized = run(reader._read_sgp(None, serialize=False, deserialize=False))
    assert data == SGP40(None, None, None)
    assert compensated is True
    assert serialized is False
    log = run(reader.get_error_counter())
    err_count = log["SGP40"]["ErrCount"]
    assert isinstance(err_count, int)
    assert err_count >= 1


def test_read_sgp_comp_source_get_data_raising_is_caught_not_propagated() -> None:
    # Distinct from the NaN/Inf tests above, where get_data() succeeds but returns bad values:
    # here get_data() itself raises. Each source is caller-supplied and only structurally typed
    # (Part C.14), so this can't be ruled out statically even though SCD30_Reader never raises.
    reader = make_reader()
    reader._temperature = ValueRef(_FakeCompSource(raise_exc=True), "Temp")
    reader._humidity = ValueRef(_FakeCompSource(raise_exc=True), "Hum")
    run(reader.setup())
    data, compensated, serialized = run(reader._read_sgp(None, serialize=False, deserialize=False))
    assert data == SGP40(None, None, None)
    assert compensated is False  # temp_val/hum_val fell back to None, None before the availability check
    assert serialized is False
    log = run(reader.get_error_counter())
    # Exactly one entry (the real get_data() failure, SOURCE) - not also a second, redundant "no
    # compensation data available" warning for a condition the exception already explains
    # (SPECIFICATION.md Part C.14.2).
    assert log["SGP40"]["ErrCount"] == 1
    assert _last_err(log, "ErrNum") == code("E", "SOURCE")
    assert _last_err(log, "ErrType") == "E"


_BadCompReading = namedtuple("_BadCompReading", ("Temp", "Hum"))


class _FakeNonNumericCompSource:
    # A non-numeric-but-not-None field: never producible by a real *_Reader, whose measurement
    # fields are float|None, but the source is only structurally typed (Part C.14). Proves Part
    # D.2's "never raises, under any input" for the float() calls in _read_sgp()'s second try.
    async def get_data(self) -> "Any":
        return _BadCompReading("not-a-number", 50.0)


def test_read_sgp_non_numeric_compensation_value_is_caught_not_propagated() -> None:
    # Distinct from both tests above: get_data() succeeds and the field is not None, so it passes
    # the availability check, but float() on the value itself raises - this must be caught by the
    # existing second try/except (READ, "Read failed"), not escape _read_sgp() uncaught.
    reader = make_reader()
    bad_source = _FakeNonNumericCompSource()
    reader._temperature = ValueRef(bad_source, "Temp")
    reader._humidity = ValueRef(bad_source, "Hum")
    run(reader.setup())
    data, compensated, serialized = run(reader._read_sgp(None, serialize=False, deserialize=False))
    assert data == SGP40(None, None, None)
    assert compensated is True  # comp data was "available" (not None) - float() itself failed
    assert serialized is False
    log = run(reader.get_error_counter())
    assert log["SGP40"]["ErrCount"] == 1
    assert _last_err(log, "ErrNum") == code("E", "READ")
    assert _last_err(log, "ErrType") == "E"


def test_run_backup_genuine_fram_write_failure_is_logged_as_an_error() -> None:
    # Distinct from the "no NTP yet" deferral: here require_ntp is already satisfied but the FRAM
    # write itself fails - manager.set_pause(value=True) makes _mempause() return True, so _write()
    # bails out with a clean False without touching the chip, the shape a hardware fault takes.
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    reader = SGP40_Reader(
        make_i2c(),
        ValueRef(_FakeCompSource(), "Temp"),
        ValueRef(_FakeCompSource(), "Hum"),
        backup=SgpBackup(manager, _ntp_synced),
        log=LogConfig(manager, 10, None),
        max_module_error=5,
        cfg_path=_SHARED_CFG_DIR,
    )
    run(reader.setup())
    fake_bus = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    run(reader._init_sgp())
    reader._voc_write = 0  # require_ntp=False - isolates the "genuine write failure" branch
    buf, _serialize, _deserialize, cfg_values = run(reader._check_storage())
    manager.set_pause(value=True)
    run(reader._run_backup(buf, serialize=True, cfg_values=cfg_values))
    manager.set_pause(value=False)
    assert reader._last_backup is None
    log = run(reader.get_error_counter())
    err_count = log["SGP40"]["ErrCount"]
    assert isinstance(err_count, int)
    assert err_count >= 1
    # Each layer the failure reaches keeps its own entry: the store's refusal and SGP40's failed backup.
    assert _last_err(log, "ErrNum") == code("E", "SGP_BACKUP_WRITE")
    assert code("W", "FRAM_PAUSED") in _warnings(run(manager.pr.get_log()))


def _backup_rig(manager: FRAMManager) -> "tuple[SGP40_Reader, FakeI2C]":
    reader = SGP40_Reader(
        make_i2c(),
        ValueRef(_FakeCompSource(), "Temp"),
        ValueRef(_FakeCompSource(), "Hum"),
        backup=SgpBackup(manager, _ntp_synced),
        log=LogConfig(manager, 10, None),
        max_module_error=5,
        cfg_path=_SHARED_CFG_DIR,
    )
    run(reader.setup())
    fake_bus = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    assert run(reader._init_sgp()) is True
    return reader, fake_bus


def _restore_once(reader: SGP40_Reader) -> bool:
    reader._voc_init = 1  # the restore runs on this cycle
    buf, _serialize, deserialize, cfg_values = run(reader._check_storage())
    return run(reader._run_restore(buf, deserialize=deserialize, cfg_values=cfg_values))


# Each layer a backup failure reaches keeps one entry of its own, so the history shows how far it reached.


def test_crc_invalid_backup_logs_in_fram_and_in_sgp40() -> None:
    manager, chip, spi_bus = make_fram_manager()
    run(manager.setup())
    writer, fake_bus = _backup_rig(manager)
    writer._voc_write = 0
    run(_write_and_back_up(writer, fake_bus, 1))
    for addr in range(len(chip.memory)):  # every copy of every block fails its CRC now
        chip.memory[addr] ^= 0x5A
    manager2 = make_fram_manager_sharing(spi_bus)
    run(manager2.setup())
    reader, _bus2 = _backup_rig(manager2)
    assert _restore_once(reader) is False
    assert _warnings(run(reader.get_error_counter()))[-1] == code("W", "SGP_NO_BACKUP")
    fram_log = run(manager2.pr.get_log())
    assert "E" in next(iter(fram_log.values()))["ErrType"], f"the FRAM layer persisted nothing: {fram_log!r}"


def test_a_paused_store_logs_in_fram_and_in_sgp40() -> None:
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    reader, _bus = _backup_rig(manager)
    manager.set_pause(value=True)
    assert _restore_once(reader) is False
    manager.set_pause(value=False)
    assert _warnings(run(reader.get_error_counter()))[-1] == code("W", "SGP_NO_BACKUP")
    assert code("W", "FRAM_PAUSED") in _warnings(run(manager.pr.get_log()))


def test_a_failed_backup_write_logs_in_fram_and_in_sgp40() -> None:
    manager, chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    reader, fake_bus = _backup_rig(manager)
    reader._voc_write = 0  # require_ntp=False: the write itself is what fails
    chip.drop_wren = True  # the write-enable latch never sets, so nothing reaches the chip
    run(_write_and_back_up(reader, fake_bus, 1))
    chip.drop_wren = False
    assert reader._last_backup is None
    assert _last_err(run(reader.get_error_counter()), "ErrNum") == code("E", "SGP_BACKUP_WRITE")
    fram_log = next(iter(run(manager.pr.get_log()).values()))
    assert any(kind != "N" for kind in fram_log["ErrType"]), f"the FRAM layer persisted nothing: {fram_log!r}"


def test_run_restore_applies_backup_anyway_once_wait_time_ntp_budget_is_exhausted() -> None:
    # Escape hatch in _run_restore(): if a valid timestamped backup exists but NTP has not synced
    # when _voc_init's WaitTimeNTP countdown reaches 0, the restore is applied anyway without
    # checking BackupMaxAge - recovering a possibly-unverifiable-age baseline rather than losing it.
    manager, _chip, spi_bus = make_fram_manager()
    run(manager.setup())

    async def scenario() -> tuple[bool, int | None]:
        writer = SGP40_Reader(
            make_i2c(),
            ValueRef(_FakeCompSource(), "Temp"),
            ValueRef(_FakeCompSource(), "Hum"),
            backup=SgpBackup(manager, _ntp_synced),
            log=LogConfig(manager, 10, None),
            max_module_error=5,
            cfg_path=_SHARED_CFG_DIR,
        )
        await writer.setup()
        fake_bus = bus(writer._sgp._i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus)
        await writer._init_sgp()
        await _write_and_back_up(writer, fake_bus, 1)  # a real, valid, NTP-timestamped backup

        manager2 = make_fram_manager_sharing(spi_bus)
        await manager2.setup()
        reader = SGP40_Reader(
            make_i2c(),
            ValueRef(_FakeCompSource(), "Temp"),
            ValueRef(_FakeCompSource(), "Hum"),
            backup=SgpBackup(manager2, _ntp_not_synced),
            log=LogConfig(manager2, 10, None),  # the *reader's* own current time is never NTP-synced
            max_module_error=5,
            cfg_path=_SHARED_CFG_DIR,
        )
        await reader.setup()
        fake_bus2 = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus2)
        await reader._init_sgp()
        reader._voc_init = 1  # about to hit 0 on the next _check_storage() cycle
        buf2, _serialize2, deserialize2, cfg_values2 = await reader._check_storage()
        assert reader._voc_init == 0  # countdown just reached its end this same cycle
        return await reader._run_restore(buf2, deserialize=deserialize2, cfg_values=cfg_values2), reader._restored_from

    with _UTCValid():
        restored, restored_from = run(scenario())
    assert restored is True  # applied anyway, despite age being unknowable (no NTP)
    # A real write-time timestamp (the backup itself has one - only the *reader's* clock is
    # unsynced), not the ts=-1 "no timestamp at all" sentinel from the ts_is_None branch.
    assert restored_from is not None and restored_from > 0


def test_run_backup_writes_without_timestamp_once_wait_time_ntp_budget_is_exhausted() -> None:
    # Symmetric to the restore-side escape hatch above: once _voc_write's WaitTimeNTP countdown
    # reaches 0, require_ntp becomes False and the backup is written even though NTP has not
    # synced. The existing deferral test only covers the "still waiting" branch, not this one.
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())

    async def scenario() -> tuple[int | None, int]:
        writer = SGP40_Reader(
            make_i2c(),
            ValueRef(_FakeCompSource(), "Temp"),
            ValueRef(_FakeCompSource(), "Hum"),
            backup=SgpBackup(manager, _ntp_not_synced),
            log=LogConfig(manager, 10, None),
            max_module_error=5,
            cfg_path=_SHARED_CFG_DIR,
        )
        await writer.setup()
        fake_bus = bus(writer._sgp._i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus)
        await writer._init_sgp()
        writer._voc_write = 0  # budget already exhausted -> require_ntp will be False
        buf, _serialize, _deserialize, cfg_values = await writer._check_storage()
        fake_bus.read_queue.append(_word(30000))
        data, _compensated, _serialized = await writer._read_sgp(buf, serialize=True, deserialize=False)
        await writer._store_sgp(data)
        await writer._run_backup(buf, serialize=True, cfg_values=cfg_values)
        return writer._last_backup, writer._voc_write

    last_backup, voc_write_after = run(scenario())
    assert last_backup == 0  # written without a timestamp - the documented "backup exists, no TS" sentinel
    assert voc_write_after == 0  # require_ntp was False, so the "resynced" branch never re-arms it


def _warnings(log: "ErrorLog") -> "list[int]":
    entry = next(iter(log.values()))
    nums, kinds = entry["ErrNum"], entry["ErrType"]
    return [nums[i] for i in range(len(nums)) if kinds[i] == "W"]  # MicroPython's zip() takes no strict=


def _written_no_ts_slots(log: "ErrorLog") -> int:
    return _warnings(log).count(code("W", "SGP_WRITTEN_NO_TS"))


def _run_untimestamped_backups(plan: "list[bool | str]") -> tuple[int, int]:
    # One SGP40_Reader with a switchable clock; each plan step runs one backup: False = NTP absent,
    # True = synced, "defer" = synced-required write deferred, "fail" = the FRAM write itself fails.
    # Returns (SGP_WRITTEN_NO_TS slots in the history, err_count).
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    ntp = [False]

    async def ntp_cb() -> bool:
        return ntp[0]

    async def scenario() -> tuple[int, int]:
        writer = SGP40_Reader(
            make_i2c(),
            ValueRef(_FakeCompSource(), "Temp"),
            ValueRef(_FakeCompSource(), "Hum"),
            backup=SgpBackup(manager, ntp_cb),
            log=LogConfig(manager, 10, None),
            max_module_error=5,
            cfg_path=_SHARED_CFG_DIR,
        )
        await writer.setup()
        fake_bus = bus(writer._sgp._i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus)
        await writer._init_sgp()
        buf, _serialize, _deserialize, cfg_values = await writer._check_storage()
        fake_bus.read_queue.append(_word(30000))
        data, _compensated, _serialized = await writer._read_sgp(buf, serialize=True, deserialize=False)
        await writer._store_sgp(data)
        assert writer._ts_storage is not None
        real_write_into = writer._ts_storage.write_into
        for step in plan:
            writer._ts_storage.write_into = real_write_into  # type: ignore[method-assign]
            if step == "defer":
                ntp[0] = False
                writer._voc_write = 2  # budget left -> require_ntp True -> deferred, nothing written
            elif step == "fail":
                ntp[0] = False
                writer._voc_write = 0

                async def failing_write_into(*_a: object, **_k: object) -> tuple[bool, int | None, bool]:
                    return False, -1, False

                writer._ts_storage.write_into = failing_write_into  # type: ignore[method-assign]
            else:
                ntp[0] = bool(step)
                writer._voc_write = 0  # budget exhausted -> require_ntp False -> always writes
            await writer._run_backup(buf, serialize=True, cfg_values=cfg_values)
        return _written_no_ts_slots(await writer.pr.get_log()), writer.pr._err_count

    with _UTCValid():  # the clock a sync sets: the NTP callback alone decides timestamped or not
        return run(scenario())


def test_untimestamped_backups_spend_one_slot_per_run_not_one_per_backup() -> None:
    # Bench finding 2026-09-25: one slot per 1-min backup filled the ring after one hotspot episode.
    slots, count = _run_untimestamped_backups([False] * 9)
    assert slots == 1
    assert count == 9  # every backup still counts (C.7.1)


def test_a_timestamped_backup_between_two_outages_leaves_one_slot() -> None:
    # The timestamped backup logs nothing, so the next outage's warning repeats the newest entry.
    slots, count = _run_untimestamped_backups([False, False, True, False, False])
    assert slots == 1
    assert count == 4  # the timestamped backup logs nothing


def test_a_timestamped_backup_on_the_require_ntp_branch_also_leaves_one_slot() -> None:
    # _voc_write > 0 with NTP synced takes the "written with timestamp" branch, not "again".
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    ntp = [False]

    async def ntp_cb() -> bool:
        return ntp[0]

    async def scenario() -> int:
        writer = SGP40_Reader(
            make_i2c(),
            ValueRef(_FakeCompSource(), "Temp"),
            ValueRef(_FakeCompSource(), "Hum"),
            backup=SgpBackup(manager, ntp_cb),
            log=LogConfig(manager, 10, None),
            max_module_error=5,
            cfg_path=_SHARED_CFG_DIR,
        )
        await writer.setup()
        fake_bus = bus(writer._sgp._i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus)
        await writer._init_sgp()
        buf, _serialize, _deserialize, cfg_values = await writer._check_storage()
        fake_bus.read_queue.append(_word(30000))
        data, _compensated, _serialized = await writer._read_sgp(buf, serialize=True, deserialize=False)
        await writer._store_sgp(data)
        writer._voc_write = 0
        await writer._run_backup(buf, serialize=True, cfg_values=cfg_values)  # SGP_WRITTEN_NO_TS, first slot
        ntp[0] = True
        writer._voc_write = 3  # decremented to 2 -> require_ntp True, synced -> timestamped write
        await writer._run_backup(buf, serialize=True, cfg_values=cfg_values)
        assert writer._last_backup is not None and writer._last_backup > 0
        ntp[0] = False
        writer._voc_write = 0
        await writer._run_backup(buf, serialize=True, cfg_values=cfg_values)  # repeats the newest entry
        return _written_no_ts_slots(await writer.pr.get_log())

    with _UTCValid():
        assert run(scenario()) == 1


def test_a_deferral_spends_no_slot_and_a_failed_write_its_own() -> None:
    # A deferral writes and logs nothing; the failed write's SGP_BACKUP_WRITE entry is a different
    # code, so the untimestamped backup after it spends a slot again (the newest-entry rule).
    slots, count = _run_untimestamped_backups([False, "defer", False, "fail", False])
    assert slots == 2
    assert count == 4  # three untimestamped backups and the failed write


def test_check_storage_backup_counter_wraps_before_it_could_overflow() -> None:
    # The 100000 wraparound guard only matters when BackupPeriod is disabled (0): any nonzero
    # period resets _backup_counter long before 100000 for every value in the field's valid range
    # (max 60*1440 = 86400), so the guard is otherwise unreachable. Previously untested.
    cfg_dir = _sgp_cfg_dir("backupdisabled")
    _write_sgp_cfg(cfg_dir, {"BackupPeriod": 0, "BackupMaxAge": 7200, "WaitTimeNTP": 30})
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    reader = SGP40_Reader(
        make_i2c(),
        ValueRef(_FakeCompSource(), "Temp"),
        ValueRef(_FakeCompSource(), "Hum"),
        backup=SgpBackup(manager, _ntp_synced),
        log=LogConfig(manager, 10, None),
        max_module_error=5,
        cfg_path=cfg_dir,
    )
    run(reader.setup())
    fake_bus = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    run(reader._init_sgp())
    reader._backup_counter = 99999
    run(reader._check_storage())
    assert reader._backup_counter == 0  # wrapped, not left to grow past 100000


def test_init_sgp_sets_verify_to_the_documented_formula() -> None:
    # ceil((10 * _FRAM_VERIFY_MINS) / BackupPeriod) * 0.1 - roughly "verify once per
    # _FRAM_VERIFY_MINS (60min) worth of backups". Confirmed against the real
    # _ts_storage.get_verify(), not just that _init_sgp() succeeds.
    cfg_dir = _sgp_cfg_dir("verify")
    _write_sgp_cfg(cfg_dir, {"BackupPeriod": 5, "BackupMaxAge": 7200, "WaitTimeNTP": 30})
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    reader = SGP40_Reader(
        make_i2c(),
        ValueRef(_FakeCompSource(), "Temp"),
        ValueRef(_FakeCompSource(), "Hum"),
        backup=SgpBackup(manager, _ntp_synced),
        log=LogConfig(manager, 10, None),
        max_module_error=5,
        cfg_path=cfg_dir,
    )
    run(reader.setup())
    fake_bus = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    assert run(reader._init_sgp()) is True
    assert reader._ts_storage is not None
    # ceil(600/5)*0.1 = ceil(120.0)*0.1 = 120*0.1 = 12.0 -> int(12.0) = 12
    assert run(reader._ts_storage.get_verify()) == 12


def test_simultaneous_restore_and_backup_in_one_cycle_reads_then_rewrites_the_same_buffer() -> None:
    # _check_storage() can set both serialize and deserialize in one cycle (a restore pending AND
    # the backup period elapsing at the same tick), and both share the SAME buffer: the old state
    # is read in, unpacked, advanced by one sample, re-packed, and written back out.
    manager, _chip, spi_bus = make_fram_manager()
    run(manager.setup())

    async def scenario() -> tuple[bool, bool, int]:
        writer = SGP40_Reader(
            make_i2c(),
            ValueRef(_FakeCompSource(), "Temp"),
            ValueRef(_FakeCompSource(), "Hum"),
            backup=SgpBackup(manager, _ntp_synced),
            log=LogConfig(manager, 10, None),
            max_module_error=5,
            cfg_path=_SHARED_CFG_DIR,
        )
        await writer.setup()
        fake_bus = bus(writer._sgp._i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus)
        await writer._init_sgp()
        # Converge past the initial blackout so the restored state is distinguishable.
        # _write_and_back_up() threads buf through _read_sgp() on the final sample so pack_into()
        # populates it; buf=None would instead persist a freshly-allocated, all-zero buffer.
        await _write_and_back_up(writer, fake_bus, 60)

        manager2 = make_fram_manager_sharing(spi_bus)
        await manager2.setup()
        reader = SGP40_Reader(
            make_i2c(),
            ValueRef(_FakeCompSource(), "Temp"),
            ValueRef(_FakeCompSource(), "Hum"),
            backup=SgpBackup(manager2, _ntp_synced),
            log=LogConfig(manager2, 10, None),
            max_module_error=5,
            cfg_path=_SHARED_CFG_DIR,
        )
        await reader.setup()
        fake_bus2 = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus2)
        await reader._init_sgp()
        # Force both triggers to coincide on the very next _check_storage() cycle: WaitTimeNTP's
        # default (30) leaves _voc_init > 0 on a fresh reader already; _backup_counter is set one
        # short of BackupPeriod's default (1) * 60 trigger threshold.
        reader._backup_counter = 59
        buf2, serialize2, deserialize2, cfg_values2 = await reader._check_storage()
        assert serialize2 is True
        assert deserialize2 is True
        deserialize2 = await reader._run_restore(buf2, deserialize=deserialize2, cfg_values=cfg_values2)
        assert deserialize2 is True  # restore actually applied
        fake_bus2.read_queue.append(_word(31000))
        data, _compensated, serialized2 = await reader._read_sgp(buf2, serialize=serialize2, deserialize=deserialize2)
        await reader._store_sgp(data)
        assert reader._sgp._voc_algorithm is not None
        return serialized2, True, reader._sgp._voc_algorithm.params.muptime

    with _UTCValid():
        serialized, has_algo, muptime_after = run(scenario())
    assert serialized is True  # the same cycle both restored AND re-serialized successfully
    assert has_algo is True
    assert muptime_after > 45 * 65536  # restored state was already well past the initial blackout


def test_get_dict_data_and_get_dict_cfg_shape() -> None:
    reader = make_reader()
    run(reader._store_sgp(SGP40(42, 31000, 12345)))
    data = run(reader.get_dict_data())
    assert data["SGP40"]["VOC"] == 42
    assert data["SGP40"]["Raw"] == 31000
    cfg = run(reader.get_dict_cfg())
    assert set(cfg["SGP40"].keys()) == {"BackupPeriod", "BackupMaxAge", "WaitTimeNTP"}


def test_get_task_starters_and_timer_starters_are_bound_methods() -> None:
    reader = make_reader()
    assert reader.get_task_starters() == [reader.start_asy_read]
    assert reader.get_trigger_starters() == [reader.start_timer]
    assert reader.get_timer_starters() == []


# ---------------------------------------------------------------------------
# Config schema - every field's valid range/defaults, single- and multi-field invalid
# recombinations, read through the real driver + ConfigManager (not asy_config_manager.py's own
# generic validation machinery - see tests/test_asy_config_manager.py for that).
# ---------------------------------------------------------------------------

_SGP_CFG_FILE = "config_SGP40.cfg"

# Mirrors of asy_sgp40_driver.py's own _VAL_BACKUP_PERIOD/_VAL_BACKUP_MAX_AGE/_VAL_WAIT_TIME_NTP const() tuples - not importable
# once const()-folded (see this file's own module docstring on the mocking boundary and
# SPECIFICATION.md Part E.5.1's "Reading the numbers" for why), needed here for a live write_config() call.
_VAL_BACKUP_PERIOD = (("BackupPeriod", "int", 1, 0, 1440, None),)
_VAL_BACKUP_MAX_AGE = (("BackupMaxAge", "int", 7200, 0, 10080, None),)
_VAL_WAIT_TIME_NTP = (("WaitTimeNTP", "int", 30, 0, 600, None),)
_VAL_RESET_VOC = (("ResetVOC", "bool", None, None, None, True),)


def test_get_cfg_schema_matches_the_public_attribute() -> None:
    # get_cfg_schema() is inherited for free from asy_base_classes.py's SensorReaderConfig.
    reader = make_reader()
    assert reader.get_cfg_schema() == reader._cfg_schema
    assert reader.get_cfg_schema() == (_VAL_BACKUP_PERIOD + _VAL_BACKUP_MAX_AGE + _VAL_WAIT_TIME_NTP + _VAL_RESET_VOC)


def test_push_callbacks_registered_only_for_the_command_only_reset_field() -> None:
    # BackupPeriod/BackupMaxAge/WaitTimeNTP are persist-only: _check_storage()/_init_sgp() read
    # them fresh every cycle, so nothing needs a live push - the same shape as asy_ntp_client.py's
    # fields. ResetVOC is the one exception, a command-only trigger registered like any other.
    reader = make_reader()
    assert set(reader._push_callbacks) == {"ResetVOC"}


def test_set_dict_cfg_works_out_of_the_box_with_zero_driver_changes() -> None:
    # Isolated cfg dir (see _sgp_cfg_dir() below), not the shared make_reader() config path - this
    # test actually persists non-default values, and the shared path is only safe for tests that
    # never write, same reasoning as every other config-writing test in this file.
    cfg_dir = _sgp_cfg_dir("setdictzero")
    reader = SGP40_Reader(make_i2c(), ValueRef(_FakeCompSource(), "Temp"), ValueRef(_FakeCompSource(), "Hum"), max_module_error=2, cfg_path=cfg_dir)
    run(reader.setup())
    results = run(reader._set_dict_cfg({"BackupPeriod": 30, "WaitTimeNTP": 60}, reader.get_cfg_schema()))
    assert results == {"BackupPeriod": "Valid", "WaitTimeNTP": "Valid"}
    stored = run(reader.cfgmgr.get_dict(["BackupPeriod", "WaitTimeNTP"]))
    assert stored == {"BackupPeriod": 30, "WaitTimeNTP": 60}


def _sgp_cfg_dir(name: str) -> str:
    # A fresh subdirectory per test, not the _SHARED_CFG_DIR the rest of this file uses: those
    # tests only rely on schema defaults and never collide, while these write real config files.
    # _scratch.dir() is always brand new and empty, so no stale-leftover case needs guarding.
    return _scratch.dir(name)


def _write_sgp_cfg(cfg_dir: str, values: dict[str, object]) -> None:
    with open(cfg_dir + _SGP_CFG_FILE, "w") as f:
        json.dump(values, f)


def test_get_dict_cfg_reports_schema_defaults_when_no_config_file_exists() -> None:
    # Also locks the schema's documented bounds/defaults against silent drift: BackupPeriod
    # 0-1440min default 1, BackupMaxAge 0-10080min default 7200, WaitTimeNTP 0-600s default 30.
    # The _VAL_* tuples are const()-folded and not importable, so these read back through cfgmgr.
    cfg_dir = _sgp_cfg_dir("defaults")
    reader = SGP40_Reader(make_i2c(), ValueRef(_FakeCompSource(), "Temp"), ValueRef(_FakeCompSource(), "Hum"), max_module_error=2, cfg_path=cfg_dir)
    run(reader.setup())
    cfg = run(reader.get_dict_cfg())
    assert cfg["SGP40"] == {"BackupPeriod": 1, "BackupMaxAge": 7200, "WaitTimeNTP": 30}


def test_get_dict_cfg_reports_all_valid_minimum_boundary_values() -> None:
    cfg_dir = _sgp_cfg_dir("minbound")
    _write_sgp_cfg(cfg_dir, {"BackupPeriod": 0, "BackupMaxAge": 0, "WaitTimeNTP": 0})
    reader = SGP40_Reader(make_i2c(), ValueRef(_FakeCompSource(), "Temp"), ValueRef(_FakeCompSource(), "Hum"), max_module_error=2, cfg_path=cfg_dir)
    run(reader.setup())
    cfg = run(reader.get_dict_cfg())
    assert cfg["SGP40"] == {"BackupPeriod": 0, "BackupMaxAge": 0, "WaitTimeNTP": 0}


def test_get_dict_cfg_reports_all_valid_maximum_boundary_values() -> None:
    cfg_dir = _sgp_cfg_dir("maxbound")
    _write_sgp_cfg(cfg_dir, {"BackupPeriod": 1440, "BackupMaxAge": 10080, "WaitTimeNTP": 600})
    reader = SGP40_Reader(make_i2c(), ValueRef(_FakeCompSource(), "Temp"), ValueRef(_FakeCompSource(), "Hum"), max_module_error=2, cfg_path=cfg_dir)
    run(reader.setup())
    cfg = run(reader.get_dict_cfg())
    assert cfg["SGP40"] == {"BackupPeriod": 1440, "BackupMaxAge": 10080, "WaitTimeNTP": 600}


def test_get_dict_cfg_reports_a_typical_valid_custom_combination() -> None:
    cfg_dir = _sgp_cfg_dir("typical")
    _write_sgp_cfg(cfg_dir, {"BackupPeriod": 60, "BackupMaxAge": 1440, "WaitTimeNTP": 120})
    reader = SGP40_Reader(make_i2c(), ValueRef(_FakeCompSource(), "Temp"), ValueRef(_FakeCompSource(), "Hum"), max_module_error=2, cfg_path=cfg_dir)
    run(reader.setup())
    cfg = run(reader.get_dict_cfg())
    assert cfg["SGP40"] == {"BackupPeriod": 60, "BackupMaxAge": 1440, "WaitTimeNTP": 120}


def test_config_single_invalid_backup_period_defaults_only_that_field() -> None:
    cfg_dir = _sgp_cfg_dir("badbp")
    _write_sgp_cfg(cfg_dir, {"BackupPeriod": 1441, "BackupMaxAge": 1440, "WaitTimeNTP": 120})
    reader = SGP40_Reader(make_i2c(), ValueRef(_FakeCompSource(), "Temp"), ValueRef(_FakeCompSource(), "Hum"), max_module_error=2, cfg_path=cfg_dir)
    run(reader.setup())
    cfg = run(reader.get_dict_cfg())
    assert cfg["SGP40"] == {"BackupPeriod": 1, "BackupMaxAge": 1440, "WaitTimeNTP": 120}  # only BP reverted


def test_config_single_invalid_backup_max_age_defaults_only_that_field() -> None:
    cfg_dir = _sgp_cfg_dir("badbmax")
    _write_sgp_cfg(cfg_dir, {"BackupPeriod": 60, "BackupMaxAge": -1, "WaitTimeNTP": 120})
    reader = SGP40_Reader(make_i2c(), ValueRef(_FakeCompSource(), "Temp"), ValueRef(_FakeCompSource(), "Hum"), max_module_error=2, cfg_path=cfg_dir)
    run(reader.setup())
    cfg = run(reader.get_dict_cfg())
    assert cfg["SGP40"] == {"BackupPeriod": 60, "BackupMaxAge": 7200, "WaitTimeNTP": 120}


def test_config_single_invalid_wait_time_ntp_defaults_only_that_field() -> None:
    cfg_dir = _sgp_cfg_dir("badwt")
    _write_sgp_cfg(cfg_dir, {"BackupPeriod": 60, "BackupMaxAge": 1440, "WaitTimeNTP": 601})
    reader = SGP40_Reader(make_i2c(), ValueRef(_FakeCompSource(), "Temp"), ValueRef(_FakeCompSource(), "Hum"), max_module_error=2, cfg_path=cfg_dir)
    run(reader.setup())
    cfg = run(reader.get_dict_cfg())
    assert cfg["SGP40"] == {"BackupPeriod": 60, "BackupMaxAge": 1440, "WaitTimeNTP": 30}


def test_config_two_invalid_fields_each_independently_defaulted() -> None:
    cfg_dir = _sgp_cfg_dir("badtwo")
    _write_sgp_cfg(cfg_dir, {"BackupPeriod": -5, "BackupMaxAge": 1440, "WaitTimeNTP": 99999})
    reader = SGP40_Reader(make_i2c(), ValueRef(_FakeCompSource(), "Temp"), ValueRef(_FakeCompSource(), "Hum"), max_module_error=2, cfg_path=cfg_dir)
    run(reader.setup())
    cfg = run(reader.get_dict_cfg())
    assert cfg["SGP40"] == {"BackupPeriod": 1, "BackupMaxAge": 1440, "WaitTimeNTP": 30}


def test_config_all_three_fields_invalid_falls_back_to_full_defaults() -> None:
    cfg_dir = _sgp_cfg_dir("badall")
    _write_sgp_cfg(cfg_dir, {"BackupPeriod": -1, "BackupMaxAge": 999999, "WaitTimeNTP": -30})
    reader = SGP40_Reader(make_i2c(), ValueRef(_FakeCompSource(), "Temp"), ValueRef(_FakeCompSource(), "Hum"), max_module_error=2, cfg_path=cfg_dir)
    run(reader.setup())
    cfg = run(reader.get_dict_cfg())
    assert cfg["SGP40"] == {"BackupPeriod": 1, "BackupMaxAge": 7200, "WaitTimeNTP": 30}
    # driver must still init cleanly despite an all-invalid config file already on disk
    fake_bus = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    assert run(reader._init_sgp()) is True


def test_config_wrong_type_values_single_and_combined() -> None:
    cfg_dir = _sgp_cfg_dir("wrongtype")
    _write_sgp_cfg(cfg_dir, {"BackupPeriod": "sixty", "BackupMaxAge": 1440, "WaitTimeNTP": 12.5})
    reader = SGP40_Reader(make_i2c(), ValueRef(_FakeCompSource(), "Temp"), ValueRef(_FakeCompSource(), "Hum"), max_module_error=2, cfg_path=cfg_dir)
    run(reader.setup())
    cfg = run(reader.get_dict_cfg())
    assert cfg["SGP40"] == {"BackupPeriod": 1, "BackupMaxAge": 1440, "WaitTimeNTP": 30}


def test_config_missing_keys_use_defaults() -> None:
    cfg_dir = _sgp_cfg_dir("missing")
    _write_sgp_cfg(cfg_dir, {"BackupMaxAge": 1440})  # BackupPeriod, WaitTimeNTP both absent
    reader = SGP40_Reader(make_i2c(), ValueRef(_FakeCompSource(), "Temp"), ValueRef(_FakeCompSource(), "Hum"), max_module_error=2, cfg_path=cfg_dir)
    run(reader.setup())
    cfg = run(reader.get_dict_cfg())
    assert cfg["SGP40"] == {"BackupPeriod": 1, "BackupMaxAge": 1440, "WaitTimeNTP": 30}


def test_init_sgp_applies_custom_wait_time_ntp_from_valid_config() -> None:
    # _init_sgp() must actually thread a valid custom WaitTimeNTP into _voc_init/_voc_write, not just
    # report it via get_dict_cfg() - the two are separate ConfigManager reads internally.
    cfg_dir = _sgp_cfg_dir("applywt")
    _write_sgp_cfg(cfg_dir, {"BackupPeriod": 1, "BackupMaxAge": 7200, "WaitTimeNTP": 5})
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    reader = SGP40_Reader(
        make_i2c(),
        ValueRef(_FakeCompSource(), "Temp"),
        ValueRef(_FakeCompSource(), "Hum"),
        backup=SgpBackup(manager, _ntp_synced),
        log=LogConfig(manager, 10, None),
        max_module_error=2,
        cfg_path=cfg_dir,
    )
    run(reader.setup())
    fake_bus = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    assert run(reader._init_sgp()) is True
    assert reader._voc_init == 5
    assert reader._voc_write == 5


# ---------------------------------------------------------------------------
# _read_loop() - end-to-end wiring, driven via real trigger events and cancellation
# (matches asy_system_service.py's own test convention for a supervising while-True loop)
# ---------------------------------------------------------------------------


class _FastAsyncSleep:
    # _init_sgp()/initialize()/_reset() make several real asyncio.sleep() calls (_SERIAL_READ_WAIT_MS/
    # _SELF_TEST_WAIT_MS/_MEASURE_WAIT_MS command delays, plus _reset()'s _GENERAL_CALL_RESET_WAIT_S
    # settle) - too slow for a _read_loop() test; asyncio.sleep is process-wide, restored on any exit.
    def __enter__(self) -> "Self":
        self._real_sleep = asyncio.sleep

        async def _fast(_seconds: float) -> None:
            await self._real_sleep(0)

        asyncio.sleep = _fast  # type: ignore[assignment]  # deliberate monkeypatch, not a real caller mismatch
        return self

    def __exit__(self, *exc_info: object) -> None:
        asyncio.sleep = self._real_sleep


def test_read_loop_stores_a_result_after_one_trigger() -> None:
    reader = make_reader()
    fake_bus = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    fake_bus.read_queue.append(_word(31500))

    async def scenario() -> SGP40:
        task = asyncio.create_task(reader._read_loop())
        for _ in range(20):  # pump the loop until _init_sgp() (real sleeps, now fast) completes
            await asyncio.sleep(0)
        reader._read_event.set()
        for _ in range(20):  # pump the loop until the result is stored
            await asyncio.sleep(0)
            data = await reader.get_data()
            if data.Raw is not None:
                break
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return await reader.get_data()

    with _FastAsyncSleep():
        data = run(scenario())
    assert data.Raw == 31500


def test_read_loop_gives_up_and_returns_false_after_max_errors() -> None:
    # Missing compensation data does NOT count as an SGP40 error (_error_check's condition= gate
    # skips it). To drive the give-up path, keep real compensation data but fail the I2C
    # measurement itself with a CRC mismatch, which _read_sgp turns into a real counted failure.
    reader = make_reader()  # max_module_error=2
    fake_bus = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)

    async def scenario() -> bool:
        task = asyncio.create_task(reader._read_loop())
        for _ in range(20):
            await asyncio.sleep(0)
        for _ in range(4):  # each trigger with a corrupted measurement response counts as one failure
            bad = _word(30000)
            fake_bus.read_queue.append(bytes([bad[0] ^ 0xFF]) + bad[1:])
            reader._read_event.set()
            for _ in range(20):
                await asyncio.sleep(0)
                if task.done():
                    return await task
        raise AssertionError("_read_loop never gave up")

    with _FastAsyncSleep():
        assert run(scenario()) is False


# ---------------------------------------------------------------------------
# FRAM-backed backup/restore - real FRAMManager against tests/_fram_chip_fake.py
# ---------------------------------------------------------------------------


async def _ntp_synced() -> bool:
    return True


async def _ntp_not_synced() -> bool:
    return False


def make_fram_manager() -> tuple[FRAMManager, FakeMB85RS64V, SPI]:
    spi_bus = SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    manager = FRAMManager(spi_bus, 1, max_size=0x2000)
    chip = manager.fram._spidev.spi._spi
    assert isinstance(chip, FakeMB85RS64V)
    return manager, chip, spi_bus


def make_fram_manager_sharing(spi_bus: SPI) -> FRAMManager:
    # A second, independently-allocating FRAMManager sharing the first's spi_bus and so its
    # chip memory - simulating a reboot's fresh manager object replaying the identical get_chunk()
    # sequence against surviving data, matching tests/test_fram_integration.py's pattern.

    # Reusing the same instance would be wrong: its _allocated_size bump pointer keeps advancing, so
    # a second SGP40_Reader would land its chunks in a fresh, never-written region.
    return FRAMManager(spi_bus, 1, max_size=0x2000)


async def _write_and_back_up(writer: SGP40_Reader, fake_bus: FakeI2C, samples: int) -> tuple[SGP40, object]:
    buf, _serialize, _deserialize, cfg_values = await writer._check_storage()
    for i in range(samples):
        fake_bus.read_queue.append(_word(30000 + i * 17))
        is_last = i == samples - 1
        # serialize=True only on the final read - vocalgorithm_proc_ser_des() packs the current
        # state into buf as part of that same call, exactly like a real trigger cycle, where
        # _read_loop passes _check_storage()'s one serialize flag into the same-cycle _read_sgp().
        data, _compensated, _serialized = await writer._read_sgp(buf, serialize=is_last, deserialize=False)
        await writer._store_sgp(data)
    await writer._run_backup(buf, serialize=True, cfg_values=cfg_values)
    return data, buf


def test_fram_backup_writes_and_restore_recovers_full_algorithm_state() -> None:
    manager, _chip, spi_bus = make_fram_manager()
    run(manager.setup())

    async def scenario() -> tuple[SGP40, int]:
        writer = SGP40_Reader(
            make_i2c(),
            ValueRef(_FakeCompSource(), "Temp"),
            ValueRef(_FakeCompSource(), "Hum"),
            backup=SgpBackup(manager, _ntp_synced),
            log=LogConfig(manager, 10, None),
            max_module_error=5,
            cfg_path=_SHARED_CFG_DIR,
        )
        await writer.setup()
        fake_bus = bus(writer._sgp._i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus)
        assert await writer._init_sgp() is True
        await _write_and_back_up(writer, fake_bus, 60)  # converge state past the 46-sample initial blackout
        assert writer._last_backup is not None
        assert writer._sgp._voc_algorithm is not None  # lazily created by the first real read above

        # A second reader, sharing the same FRAM backing (a simulated reboot) - fresh VOCAlgorithm,
        # never processed a single sample, must recover the exact converged state via restore.
        manager2 = make_fram_manager_sharing(spi_bus)
        run_ok = await manager2.setup()
        assert run_ok is True
        reader = SGP40_Reader(
            make_i2c(),
            ValueRef(_FakeCompSource(), "Temp"),
            ValueRef(_FakeCompSource(), "Hum"),
            backup=SgpBackup(manager2, _ntp_synced),
            log=LogConfig(manager2, 10, None),
            max_module_error=5,
            cfg_path=_SHARED_CFG_DIR,
        )
        await reader.setup()
        fake_bus2 = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus2)
        assert await reader._init_sgp() is True
        buf2, _serialize2, deserialize2, cfg_values2 = await reader._check_storage()
        assert deserialize2 is True  # _voc_init starts at WaitTimeNTP>0 on a fresh reader -> restore triggers
        restored = await reader._run_restore(buf2, deserialize=deserialize2, cfg_values=cfg_values2)
        assert restored is True
        fake_bus2.read_queue.append(_word(30500))
        data2, _compensated2, _serialized2 = await reader._read_sgp(buf2, serialize=False, deserialize=True)
        assert reader._sgp._voc_algorithm is not None
        return data2, reader._sgp._voc_algorithm.params.muptime

    with _UTCValid():
        data, muptime_after_restore = run(scenario())
    assert data.VOC is not None
    # The restored uptime must already be well past the 45s initial blackout the writer converged
    # through - proving the *whole* state (not just mean/std) survived, per voc_algorithm.py's
    # module docstring on why this differs from Sensirion's own short-interruption-only API.
    assert muptime_after_restore > 45 * 65536


class _OldTime:
    # FRAMTimestampedChunk.write_into() stamps utc_now(), and poking the chip's stored timestamp bytes
    # only corrupts one redundant copy's CRC, which _read() then self-heals from the other copy.

    # So utc_now()'s own `time` (asy_base_classes') is replaced for the one write, giving an old but
    # valid, correctly CRC-covered timestamp.
    def gmtime(self, *args: object) -> object:
        import time as _real_time

        return _real_time.gmtime(*args)  # type: ignore[arg-type]

    def mktime(self, t: object) -> int:
        import time as _real_time

        return _real_time.mktime(t) - 999999  # type: ignore[arg-type]


def test_fram_restore_rejects_backup_older_than_backup_max_age() -> None:
    manager, _chip, spi_bus = make_fram_manager()
    run(manager.setup())

    async def scenario() -> bool:
        writer = SGP40_Reader(
            make_i2c(),
            ValueRef(_FakeCompSource(), "Temp"),
            ValueRef(_FakeCompSource(), "Hum"),
            backup=SgpBackup(manager, _ntp_synced),
            log=LogConfig(manager, 10, None),
            max_module_error=5,
            cfg_path=_SHARED_CFG_DIR,
        )
        await writer.setup()
        fake_bus = bus(writer._sgp._i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus)
        await writer._init_sgp()

        original_time = asy_base_classes.time
        asy_base_classes.time = _OldTime()  # type: ignore[assignment]  # deliberate monkeypatch, not a real caller mismatch
        try:
            await _write_and_back_up(writer, fake_bus, 1)  # backed up ~999999s (~11.6 days) in the "past"
        finally:
            asy_base_classes.time = original_time

        manager2 = make_fram_manager_sharing(spi_bus)
        await manager2.setup()
        reader = SGP40_Reader(
            make_i2c(),
            ValueRef(_FakeCompSource(), "Temp"),
            ValueRef(_FakeCompSource(), "Hum"),
            backup=SgpBackup(manager2, _ntp_synced),
            log=LogConfig(manager2, 10, None),
            max_module_error=5,
            cfg_path=_SHARED_CFG_DIR,
        )
        await reader.setup()
        fake_bus2 = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus2)
        await reader._init_sgp()
        buf2, _serialize2, deserialize2, cfg_values2 = await reader._check_storage()
        return await reader._run_restore(buf2, deserialize=deserialize2, cfg_values=cfg_values2)

    with _UTCValid():
        assert run(scenario()) is False  # too old - BackupMaxAge default is 7200 minutes


def test_fram_restore_finds_no_backup_on_a_never_written_chunk() -> None:
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())

    async def scenario() -> bool:
        reader = SGP40_Reader(
            make_i2c(),
            ValueRef(_FakeCompSource(), "Temp"),
            ValueRef(_FakeCompSource(), "Hum"),
            backup=SgpBackup(manager, _ntp_synced),
            log=LogConfig(manager, 10, None),
            max_module_error=5,
            cfg_path=_SHARED_CFG_DIR,
        )
        await reader.setup()
        fake_bus = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus)
        await reader._init_sgp()
        buf, _serialize, deserialize, cfg_values = await reader._check_storage()
        assert deserialize is True  # WaitTimeNTP>0 on a fresh reader -> restore is attempted
        return await reader._run_restore(buf, deserialize=deserialize, cfg_values=cfg_values)

    assert run(scenario()) is False  # never written - no backup to recover
    # this also means _run_restore's own error_check/log path (not the FRAM chip's, since read_into
    # itself never raises) was exercised for a real, hardware-shaped "no backup" case, not a
    # hand-constructed None input like test_run_restore_without_deserialize_trigger_is_a_no_op above.


def test_fram_backup_without_ntp_sync_is_deferred_not_lost() -> None:
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())

    async def scenario() -> tuple[bool, int]:
        writer = SGP40_Reader(
            make_i2c(),
            ValueRef(_FakeCompSource(), "Temp"),
            ValueRef(_FakeCompSource(), "Hum"),
            backup=SgpBackup(manager, _ntp_not_synced),
            log=LogConfig(manager, 10, None),
            max_module_error=5,
            cfg_path=_SHARED_CFG_DIR,
        )
        await writer.setup()
        fake_bus = bus(writer._sgp._i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus)
        await writer._init_sgp()
        assert writer._voc_write > 0  # WaitTimeNTP default (30) requires NTP before the first write counts
        buf, _serialize, _deserialize, cfg_values = await writer._check_storage()
        fake_bus.read_queue.append(_word(30000))
        data, _compensated, _serialized = await writer._read_sgp(buf, serialize=False, deserialize=False)
        await writer._store_sgp(data)
        await writer._run_backup(buf, serialize=True, cfg_values=cfg_values)
        return writer._last_backup is None, writer._backup_counter

    no_backup_yet, backup_counter = run(scenario())
    assert no_backup_yet is True  # no timestamped backup recorded without NTP while require_ntp holds
    assert backup_counter > 0  # retry is rescheduled, not silently dropped


# ---------------------------------------------------------------------------
# comp_callback / add_into fault-hardening (this review pass's own fixes)
# ---------------------------------------------------------------------------


def test_read_sgp_comp_callback_exception_is_caught_not_propagated() -> None:
    # Regression test: a compensation-source get_data() failure used to be called unwrapped, unlike
    # every other caller-supplied callback in this codebase (e.g. asy_fram_manager.py's ntp_sync_callback).
    reader = SGP40_Reader(
        make_i2c(),
        ValueRef(_FakeCompSource(raise_exc=True), "Temp"),
        ValueRef(_FakeCompSource(raise_exc=True), "Hum"),
        max_module_error=2,
        cfg_path=_SHARED_CFG_DIR,
    )
    run(reader.setup())
    data, compensated, serialized = run(reader._read_sgp(None, serialize=False, deserialize=False))
    assert data == SGP40(None, None, None)
    assert compensated is False
    assert serialized is False
    log = run(reader.get_error_counter())
    err_count = log["SGP40"]["ErrCount"]
    assert isinstance(err_count, int)
    assert err_count >= 1


class _AlwaysFailCRC:
    # Minimal fake matching CRCBase.add_into()'s contract just enough to force the "computation
    # failed" branch measure_raw() must handle; the real CRC8 cannot fail through its fixed buffer
    # shape. `start` keeps its unprefixed name: measure_raw() passes it by keyword.
    async def add_into(self, _buffer: bytearray, _size: int, start: int = 0, _init: int | None = None) -> int | None:
        return None


def test_measure_raw_add_into_failure_returns_none_not_raise() -> None:
    # Regression test: measure_raw()'s two crc.add_into() calls used to ignore the return value
    # entirely, unlike check_from()'s own calls a few lines away and asy_fram_manager.py's own
    # add_into() call site.
    sgp = make_sgp()
    sgp.crc = _AlwaysFailCRC()  # type: ignore[assignment]
    fake_bus = bus(sgp._i2c_sgp40.i2c_device.i2c)
    raw = run(sgp.measure_raw())
    assert raw is None
    assert fake_bus.log == []  # never even reached get_raw()'s own bus transaction


# ---------------------------------------------------------------------------
# I2C hardware-fault propagation - NAK/OSError specifically, distinct from the CRC-mismatch
# RuntimeError path above. Proves SGP40_I2C's documented "OSError allowed to propagate" carve-out
# (Part D.2) is absorbed by SGP40_Reader's wrapping try/except, up through _read_loop()'s give-up.
# ---------------------------------------------------------------------------


def test_read_sgp_i2c_nak_during_measurement_is_caught_and_counted() -> None:
    reader = make_reader()
    fake_bus = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
    fake_bus.nak_addresses.add(0x59)  # the sensor itself stops acking mid-measurement
    run(reader.setup())
    data, compensated, serialized = run(reader._read_sgp(None, serialize=False, deserialize=False))
    assert data == SGP40(None, None, None)
    assert compensated is True  # comp data itself was fine - the I2C transaction is what failed
    assert serialized is False
    log = run(reader.get_error_counter())
    err_count = log["SGP40"]["ErrCount"]
    assert isinstance(err_count, int)
    assert err_count >= 1


def test_read_loop_gives_up_via_real_i2c_nak_faults_not_just_crc_mismatch() -> None:
    reader = make_reader()  # max_module_error=2
    fake_bus = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)

    async def scenario() -> bool:
        task = asyncio.create_task(reader._read_loop())
        for _ in range(20):
            await asyncio.sleep(0)
        fake_bus.nak_addresses.add(0x59)  # sensor goes unresponsive after a successful init
        for _ in range(4):
            reader._read_event.set()
            for _ in range(20):
                await asyncio.sleep(0)
                if task.done():
                    return await task
        raise AssertionError("_read_loop never gave up")

    with _FastAsyncSleep():
        assert run(scenario()) is False


# ---------------------------------------------------------------------------
# asy_print_log / asy_base_classes FRAM-backed logging - SGP40's error log persists across a reboot,
# separate from _ts_storage's VOC-state chunk, which is allocated first because
# SensorReaderConfig -> SensorReader.__init__ runs before SGP40_Reader's own get_timestamped_chunk().
# ---------------------------------------------------------------------------


def test_reader_with_fram_storage_gets_a_fram_backed_print_log() -> None:
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    reader = SGP40_Reader(
        make_i2c(),
        ValueRef(_FakeCompSource(), "Temp"),
        ValueRef(_FakeCompSource(), "Hum"),
        backup=SgpBackup(manager, _ntp_synced),
        log=LogConfig(manager, 10, None),
        max_module_error=2,
        cfg_path=_SHARED_CFG_DIR,
    )
    run(reader.setup())
    assert isinstance(reader.pr, PrintLogHistoryStore)


def test_the_log_config_and_the_backup_are_independent() -> None:
    # The logger's FRAM store comes from log= alone, the VOC backup's from backup= alone.
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    backup_only = SGP40_Reader(make_i2c(), ValueRef(_FakeCompSource(), "Temp"), ValueRef(_FakeCompSource(), "Hum"), backup=SgpBackup(manager, _ntp_synced), cfg_path=_SHARED_CFG_DIR)
    assert not isinstance(backup_only.pr, PrintLogHistoryStore)
    assert backup_only._ts_storage is not None
    log_only = SGP40_Reader(make_i2c(), ValueRef(_FakeCompSource(), "Temp"), ValueRef(_FakeCompSource(), "Hum"), cfg_path=_SHARED_CFG_DIR, log=LogConfig(manager, 4, 1))
    assert isinstance(log_only.pr, PrintLogHistoryStore)
    assert len(log_only.pr.history) == 4
    assert log_only.pr.level == 1
    assert log_only._ts_storage is None


def test_reader_survives_get_timestamped_chunk_raising_instead_of_returning_none() -> None:
    # Regression test: __init__ used to call fram_storage.get_timestamped_chunk() unguarded,
    # trusting FRAMManager's "never raises" contract with no defense in depth. A raise here
    # happens at construction time, before any supervisor exists, so it must degrade to None.
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())

    def raising_get_timestamped_chunk(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("simulated allocation failure")

    manager.get_timestamped_chunk = raising_get_timestamped_chunk  # type: ignore[method-assign]

    reader = SGP40_Reader(
        make_i2c(),
        ValueRef(_FakeCompSource(), "Temp"),
        ValueRef(_FakeCompSource(), "Hum"),
        backup=SgpBackup(manager, _ntp_synced),
        log=LogConfig(manager, 10, None),
        max_module_error=2,
        cfg_path=_SHARED_CFG_DIR,
    )
    run(reader.setup())
    assert reader._ts_storage is None
    assert isinstance(reader.pr, PrintLogHistoryStore)  # print-log FRAM persistence is unaffected


def test_sgp40_error_log_survives_a_simulated_reboot_via_fram() -> None:
    manager, _chip, spi_bus = make_fram_manager()
    run(manager.setup())

    async def scenario() -> int:
        reader = SGP40_Reader(
            make_i2c(),
            ValueRef(_FakeCompSource(), "Temp"),
            ValueRef(_FakeCompSource(), "Hum"),
            backup=SgpBackup(manager, _ntp_synced),
            log=LogConfig(manager, 10, None),
            max_module_error=2,
            cfg_path=_SHARED_CFG_DIR,
        )
        await reader.setup()
        await reader.pr.err_s("SGP40", "simulated fault", errno=1)

        manager2 = make_fram_manager_sharing(spi_bus)
        assert await manager2.setup() is True
        reader2 = SGP40_Reader(
            make_i2c(),
            ValueRef(_FakeCompSource(), "Temp"),
            ValueRef(_FakeCompSource(), "Hum"),
            backup=SgpBackup(manager2, _ntp_synced),
            log=LogConfig(manager2, 10, None),
            max_module_error=2,
            cfg_path=_SHARED_CFG_DIR,
        )
        await reader2.setup()  # loads the persisted history back from FRAM
        log = await reader2.get_error_counter()
        err_count = log["SGP40"]["ErrCount"]
        assert isinstance(err_count, int)
        return err_count

    assert run(scenario()) == 1


# ---------------------------------------------------------------------------
# _init_sgp() - the initial-setup failure (INIT) and config-read failure (CFG_READ) paths, plus
# the stale-out-of-schema WaitTimeNTP cap, were never exercised by any test above.
# ---------------------------------------------------------------------------


def test_init_sgp_fails_and_logs_when_setup_raises() -> None:
    # No fake_bus.read_queue seeded at all - initialize()'s own serial-number read gets back an
    # all-zero reply, whose CRC check fails, raising RuntimeError before sgp.setup() ever reaches
    # _reset()'s own real _GENERAL_CALL_RESET_WAIT_S settle sleep.
    reader = make_reader()
    ok = run(reader._init_sgp())
    assert ok is False
    log = run(reader.get_error_counter())
    assert _last_err(log, "ErrNum") == code("E", "INIT")
    assert _last_err(log, "ErrType") == "E"


def test_init_sgp_fails_and_logs_when_config_data_unreadable() -> None:
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    reader = SGP40_Reader(
        make_i2c(),
        ValueRef(_FakeCompSource(), "Temp"),
        ValueRef(_FakeCompSource(), "Hum"),
        backup=SgpBackup(manager, _ntp_synced),
        log=LogConfig(manager, 10, None),
        max_module_error=5,
        cfg_path=_SHARED_CFG_DIR,
    )
    run(reader.setup())
    fake_bus = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    reader.cfgmgr.valid = False  # simulate an unreadable/corrupted per-sensor config file
    ok = run(reader._init_sgp())
    assert ok is False
    log = run(reader.get_error_counter())
    assert _last_err(log, "ErrNum") == code("E", "CFG_READ")
    assert _last_err(log, "ErrType") == "E"
    # Each layer keeps its own entry: SGP40's fallback here, the store's refusal there.
    assert run(reader.cfgmgr.pr.get_log())[reader.cfgmgr.name]["ErrNum"][-1] == code("E", "CFG_NOT_VALID")


def test_init_sgp_caps_a_stale_out_of_schema_wait_time_ntp() -> None:
    # The schema's own WaitTimeNTP max (600, matching _MAX_NTP_WAITTIME) already prevents a normal
    # write_config() from storing anything past the cap - reachable only via a stale value written
    # before this bound existed, same technique as test_asy_bmp3xx_driver.py's own analogous test.
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    reader = SGP40_Reader(
        make_i2c(),
        ValueRef(_FakeCompSource(), "Temp"),
        ValueRef(_FakeCompSource(), "Hum"),
        backup=SgpBackup(manager, _ntp_synced),
        log=LogConfig(manager, 10, None),
        max_module_error=5,
        cfg_path=_SHARED_CFG_DIR,
    )
    run(reader.setup())
    fake_bus = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    reader.cfgmgr._cache["WaitTimeNTP"] = 9999
    assert run(reader._init_sgp()) is True
    assert reader._voc_init == 600  # capped at _MAX_NTP_WAITTIME, not the stale stored value
    assert reader._voc_write == 600


def test_check_storage_fails_and_logs_when_config_data_unreadable() -> None:
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    reader = SGP40_Reader(
        make_i2c(),
        ValueRef(_FakeCompSource(), "Temp"),
        ValueRef(_FakeCompSource(), "Hum"),
        backup=SgpBackup(manager, _ntp_synced),
        log=LogConfig(manager, 10, None),
        max_module_error=5,
        cfg_path=_SHARED_CFG_DIR,
    )
    run(reader.setup())
    fake_bus = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    assert run(reader._init_sgp()) is True
    reader.cfgmgr.valid = False  # corrupt the config only after init already succeeded
    buf, serialize, deserialize, cfg_values = run(reader._check_storage())
    assert (buf, serialize, deserialize, cfg_values) == (None, False, False, None)
    log = run(reader.get_error_counter())
    assert _last_err(log, "ErrNum") == code("E", "CFG_READ")
    assert _last_err(log, "ErrType") == "E"
    assert run(reader.cfgmgr.pr.get_log())[reader.cfgmgr.name]["ErrNum"][-1] == code("E", "CFG_NOT_VALID")


# ---------------------------------------------------------------------------
# _run_restore() - only the no-buffer/no-trigger no-op and the two escape-hatch tests above were
# ever exercised; the "backup found but no timestamp" and "timestamp valid but age unknown" branches
# (asy_fram_manager.py's own read_into() contract) were not.
# ---------------------------------------------------------------------------


def test_run_restore_backup_without_timestamp_clears_voc_init_and_still_restores() -> None:
    manager, _chip, spi_bus = make_fram_manager()
    run(manager.setup())

    async def scenario() -> "tuple[bool, int, ErrorLog]":
        writer = SGP40_Reader(
            make_i2c(),
            ValueRef(_FakeCompSource(), "Temp"),
            ValueRef(_FakeCompSource(), "Hum"),
            backup=SgpBackup(manager, _ntp_not_synced),
            log=LogConfig(manager, 10, None),  # every write from here on lacks a timestamp
            max_module_error=5,
            cfg_path=_SHARED_CFG_DIR,
        )
        await writer.setup()
        fake_bus = bus(writer._sgp._i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus)
        await writer._init_sgp()
        writer._voc_write = 0  # budget exhausted -> require_ntp False -> writes anyway, sans timestamp
        await _write_and_back_up(writer, fake_bus, 1)

        manager2 = make_fram_manager_sharing(spi_bus)
        await manager2.setup()
        reader = SGP40_Reader(
            make_i2c(),
            ValueRef(_FakeCompSource(), "Temp"),
            ValueRef(_FakeCompSource(), "Hum"),
            backup=SgpBackup(manager2, _ntp_synced),
            log=LogConfig(manager2, 10, None),
            max_module_error=5,
            cfg_path=_SHARED_CFG_DIR,
        )
        await reader.setup()
        fake_bus2 = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus2)
        await reader._init_sgp()
        buf2, _serialize2, deserialize2, cfg_values2 = await reader._check_storage()
        restored = await reader._run_restore(buf2, deserialize=deserialize2, cfg_values=cfg_values2)
        return restored, reader._voc_init, await reader.get_error_counter()

    restored, voc_init_after, log = run(scenario())
    assert restored is True
    assert voc_init_after == 0  # SGP_RESTORED_NO_TS's own reset, not left counting down
    assert _warnings(log)[-1] == code("W", "SGP_RESTORED_NO_TS")


def test_run_restore_valid_timestamp_but_unknown_age_waits_for_ntp() -> None:
    # A real, validly-timestamped backup exists, but the reading reader's own NTP callback is not
    # synced yet, so read_into() reports (True, ts, age=None). With _voc_init still > 0, as a fresh
    # reader always starts, _run_restore() must not apply the backup yet, just keep waiting.
    manager, _chip, spi_bus = make_fram_manager()
    run(manager.setup())

    async def scenario() -> bool:
        writer = SGP40_Reader(
            make_i2c(),
            ValueRef(_FakeCompSource(), "Temp"),
            ValueRef(_FakeCompSource(), "Hum"),
            backup=SgpBackup(manager, _ntp_synced),
            log=LogConfig(manager, 10, None),
            max_module_error=5,
            cfg_path=_SHARED_CFG_DIR,
        )
        await writer.setup()
        fake_bus = bus(writer._sgp._i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus)
        await writer._init_sgp()
        await _write_and_back_up(writer, fake_bus, 1)

        manager2 = make_fram_manager_sharing(spi_bus)
        await manager2.setup()
        reader = SGP40_Reader(
            make_i2c(),
            ValueRef(_FakeCompSource(), "Temp"),
            ValueRef(_FakeCompSource(), "Hum"),
            backup=SgpBackup(manager2, _ntp_not_synced),
            log=LogConfig(manager2, 10, None),  # this reader's own clock isn't synced yet
            max_module_error=5,
            cfg_path=_SHARED_CFG_DIR,
        )
        await reader.setup()
        fake_bus2 = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus2)
        await reader._init_sgp()
        assert reader._voc_init > 0  # fresh reader, WaitTimeNTP default still counting down
        buf2, _serialize2, deserialize2, cfg_values2 = await reader._check_storage()
        return await reader._run_restore(buf2, deserialize=deserialize2, cfg_values=cfg_values2)

    assert run(scenario()) is False


# ---------------------------------------------------------------------------
# _run_backup() - the set_verify-divergence branch and the "resynced after a no-timestamp write"
# branch were never exercised.
# ---------------------------------------------------------------------------


def test_run_backup_updates_verify_when_backup_period_changes_after_init() -> None:
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    reader = SGP40_Reader(
        make_i2c(),
        ValueRef(_FakeCompSource(), "Temp"),
        ValueRef(_FakeCompSource(), "Hum"),
        backup=SgpBackup(manager, _ntp_synced),
        log=LogConfig(manager, 10, None),
        max_module_error=5,
        cfg_path=_sgp_cfg_dir("verify_change"),  # fresh, isolated config file - this test writes to it
    )
    run(reader.setup())
    fake_bus = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    run(reader._init_sgp())
    verify_at_init = run(reader._ts_storage.get_verify())  # type: ignore[union-attr]
    # Change BackupPeriod after init already computed/stored its own verify value against the old one.
    run(reader.cfgmgr.write_config({"BackupPeriod": 30}))
    reader._backup_counter = 1799  # one short of the *new* BackupPeriod=30's own 60*30 trigger threshold
    fake_bus.read_queue.append(_word(30000))
    buf, serialize, _deserialize, cfg_values = run(reader._check_storage())
    assert serialize is True
    run(reader._read_sgp(buf, serialize=serialize, deserialize=False))
    run(reader._run_backup(buf, serialize=serialize, cfg_values=cfg_values))
    verify_after = run(reader._ts_storage.get_verify())  # type: ignore[union-attr]
    assert verify_after != verify_at_init


def test_run_backup_resyncs_with_timestamp_once_ntp_available_again() -> None:
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    reader = SGP40_Reader(
        make_i2c(),
        ValueRef(_FakeCompSource(), "Temp"),
        ValueRef(_FakeCompSource(), "Hum"),
        backup=SgpBackup(manager, _ntp_synced),
        log=LogConfig(manager, 10, None),  # NTP is synced by the time _run_backup() actually writes
        max_module_error=5,
        cfg_path=_sgp_cfg_dir("resync_with_ts"),
    )
    run(reader.setup())
    fake_bus = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    run(reader._init_sgp())
    reader._voc_write = 0  # require_ntp already satisfied/exhausted from a prior cycle
    reader._backup_counter = 59  # one short of BackupPeriod=1's own 60-tick trigger threshold
    fake_bus.read_queue.append(_word(30000))
    buf, serialize, _deserialize, cfg_values = run(reader._check_storage())
    assert serialize is True
    run(reader._read_sgp(buf, serialize=serialize, deserialize=False))
    with _UTCValid():
        run(reader._run_backup(buf, serialize=serialize, cfg_values=cfg_values))
    assert reader._last_backup is not None  # written with a real timestamp, not the untimestamped-backup sentinel
    assert reader._voc_write == 30  # re-armed to the configured WaitTimeNTP default


# ---------------------------------------------------------------------------
# _read_sgp() - the reset-with-no-storage vacuous-satisfaction branch, the deserialize-retry-on-
# missing-compensation-data branch, the SGP_ALGO_STATE deserialize-failure branch, and completing a
# pending reset despite an I2C fault were never exercised.
# ---------------------------------------------------------------------------


def test_read_sgp_reset_without_fram_storage_completes_immediately() -> None:
    reader = make_reader()  # no backup -> _ts_storage is None
    run(reader.reset_voc(flag=True))
    run(reader._read_sgp(None, serialize=False, deserialize=False))
    assert reader._reset_fram_cleared is True  # nothing to clear - vacuously satisfied
    assert reader._reset_pending is False  # both sub-parts done (algo half applies unconditionally too)


def test_read_sgp_retries_deserialize_when_compensation_data_missing() -> None:
    reader = SGP40_Reader(
        make_i2c(),
        ValueRef(_FakeCompSource(None, None), "Temp"),
        ValueRef(_FakeCompSource(None, None), "Hum"),
        max_module_error=2,
        cfg_path=_SHARED_CFG_DIR,
    )
    run(reader.setup())
    reader._voc_init = 0
    run(reader._read_sgp(None, serialize=False, deserialize=True))  # deserialize=True, but no compensation data available
    assert reader._voc_init == 1  # retry scheduled for the next cycle
    assert reader._backup_counter == 0


class _TooSmallBuf:
    # A real FRAM-backed buffer is always exactly get_params_memsize() (256 bytes) and always
    # deserialized at offset 0, so struct.unpack_from("32q", ...) can never see a size mismatch
    # through normal use - this fake is the only way to force the too-small-backup branch.
    def get_data_buf(self) -> bytearray:
        return bytearray(8)  # far short of the 256 bytes "32q" needs


def test_read_sgp_logs_sgp_algo_state_when_deserialize_fails() -> None:
    reader = make_reader()
    fake_bus = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
    fake_bus.read_queue.append(_word(30000))
    run(reader.setup())
    run(reader._read_sgp(_TooSmallBuf(), serialize=False, deserialize=True))  # type: ignore[arg-type]
    log = run(reader.get_error_counter())
    assert _last_err(log, "ErrNum") == code("E", "SGP_ALGO_STATE")
    assert _last_err(log, "ErrType") == "E"


def test_read_sgp_completes_a_pending_reset_even_when_the_i2c_read_fails() -> None:
    reader = make_reader()
    run(reader.reset_voc(flag=True))
    fake_bus = bus(reader._sgp._i2c_sgp40.i2c_device.i2c)
    fake_bus.nak_addresses.add(0x59)  # every bus op on this address fails
    run(reader._read_sgp(None, serialize=False, deserialize=False))
    assert reader._reset_algo_applied is True  # vocalgorithm_reset() never raises - applies regardless
    assert reader._reset_pending is False  # both sub-parts satisfied despite the I2C fault


# ---------------------------------------------------------------------------
# _read_loop() - init failure must return False, matching every other *_Reader's own convention.
# ---------------------------------------------------------------------------


def test_read_loop_returns_false_when_init_fails() -> None:
    # No fake_bus.read_queue seeded - same fast-failing setup as test_init_sgp_fails_and_logs_when_setup_raises
    # above, so no real _GENERAL_CALL_RESET_WAIT_S _reset() sleep is ever reached and this doesn't need a
    # background task / cancellation dance at all.
    reader = make_reader()
    assert run(reader._read_loop()) is False


# ---------------------------------------------------------------------------
# The "no sensor response at all" guards in initialize()/get_raw()/measure_raw() and
# measure_index_and_raw() - as opposed to a NAK or CRC mismatch, both covered above - are reachable
# only by _read_word_from_command() returning None, which no real caller's readlen triggers.
# ---------------------------------------------------------------------------


class _NoneReadWord:
    async def __call__(self, *_args: object, **_kwargs: object) -> None:
        return None


def test_initialize_raises_when_serial_number_read_returns_none() -> None:
    sgp = make_sgp()
    sgp._read_word_from_command = _NoneReadWord()  # type: ignore[method-assign]
    try:
        run(sgp.initialize())
        raise AssertionError("expected RuntimeError")
    except RuntimeError as e:
        assert "no sensor response" in str(e)


def test_initialize_raises_when_self_test_read_returns_none() -> None:
    sgp = make_sgp()
    fake_bus = bus(sgp._i2c_sgp40.i2c_device.i2c)
    fake_bus.read_queue.append(_word(0x0000) + _word(0x1234) + _word(0x5678))  # serial number: OK
    real_read_word = sgp._read_word_from_command

    async def fake_read_word(sgp40: object, delay_ms: int = 10, readlen: "int | None" = 1) -> "list[int] | None":
        # @tunable sgp40.self_test_wait_ms = 500
        if delay_ms == 500:  # the self-test read's own distinguishing delay_ms
            return None
        return await real_read_word(sgp40, delay_ms=delay_ms, readlen=readlen)  # type: ignore[arg-type]

    sgp._read_word_from_command = fake_read_word  # type: ignore[method-assign]
    try:
        run(sgp.initialize())
        raise AssertionError("expected RuntimeError")
    except RuntimeError as e:
        assert "no sensor response" in str(e)


def test_get_raw_returns_none_when_read_word_from_command_returns_none() -> None:
    sgp = make_sgp()
    sgp._read_word_from_command = _NoneReadWord()  # type: ignore[method-assign]
    assert run(sgp.get_raw()) is None


class _FailSecondAddIntoCRC:
    # measure_raw()'s two crc.add_into() calls are distinguished by their start= argument (2 for
    # humidity, 5 for temperature). The add_into-failure test above covers the first; this covers
    # the second call's own separate None-check.
    async def add_into(self, _buffer: bytearray, size: int, start: int = 0, _init: int | None = None) -> int | None:
        return None if start == 5 else size


def test_measure_raw_second_add_into_failure_returns_none_not_raise() -> None:
    sgp = make_sgp()
    sgp.crc = _FailSecondAddIntoCRC()  # type: ignore[assignment]
    fake_bus = bus(sgp._i2c_sgp40.i2c_device.i2c)
    raw = run(sgp.measure_raw())
    assert raw is None
    assert fake_bus.log == []  # never even reached get_raw()'s own bus transaction


def test_measure_index_and_raw_returns_none_index_when_raw_measurement_fails() -> None:
    sgp = make_sgp()
    sgp.crc = _AlwaysFailCRC()  # type: ignore[assignment]
    voc_index, raw, serialized, deserialized = run(sgp.measure_index_and_raw())
    assert (voc_index, raw, serialized, deserialized) == (None, None, False, False)


# ---------------------------------------------------------------------------
# Bus-hazard coverage moved from tests/test_bus_hazard_multi_device.py (SPECIFICATION.md Part
# C.8): genuinely SGP40-specific (only this driver's own API and its own general-call exception),
# not a generic cross-sensor shape.
# ---------------------------------------------------------------------------

def test_touches_only_its_own_address_except_reset_which_touches_only_the_general_call_address() -> None:
    sgp = make_sgp()
    fake_bus = bus(sgp._i2c_sgp40.i2c_device.i2c)
    for _ in range(10):
        fake_bus.read_queue.append(_word(0x8000))
    queue_successful_init(fake_bus)

    async def exercise_non_reset() -> None:
        for call in (
            sgp.setup,  # includes one initialize() -> _reset() call - excluded from this half's assertion below
            sgp.get_raw,
            lambda: sgp.measure_raw(25, 50),
            lambda: sgp.measure_index_and_raw(25, 50),
        ):
            try:
                await call()
            except Exception:  # only the addresses touched matter for this sweep, not success
                pass

    with _FastAsyncSleep():
        run(exercise_non_reset())

    touched = {entry[1] for entry in fake_bus.log if entry[0] in ("writeto", "readfrom_into", "readfrom_mem", "writeto_mem")}
    # setup() calls initialize() -> _reset(), so 0x00 (the general call address) is expected here
    # too; this sweep's job is only to confirm no *third*, unexpected address shows up.
    assert touched <= {0x59, 0x00}, f"SGP40_I2C touched unexpected address(es): {touched - {0x59, 0x00}}"



def test_init_sgp_runs_on_the_defaults_when_its_config_file_cannot_be_written() -> None:
    # Regression (SPECIFICATION.md C.7.3): the failed write used to surface here as CFG_READ and a task
    # restart per boot; now init succeeds on the validated defaults and no read retries the write.
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    reader = SGP40_Reader(
        make_i2c(),
        ValueRef(_FakeCompSource(), "Temp"),
        ValueRef(_FakeCompSource(), "Hum"),
        backup=SgpBackup(manager, _ntp_synced),
        log=LogConfig(manager, 10, None),
        cfg_path=_SHARED_CFG_DIR + "missing_dir/",
    )
    run(reader.setup())
    assert reader.cfgmgr.valid is True
    queue_successful_init(bus(reader._sgp._i2c_sgp40.i2c_device.i2c))
    assert run(reader._init_sgp()) is True
    assert code("E", "CFG_READ") not in run(reader.get_error_counter())["SGP40"]["ErrNum"]
    assert run(reader.cfgmgr.pr.get_log())[reader.cfgmgr.name]["ErrNum"][-1] == code("E", "CFG_FILE_WRITE")


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
