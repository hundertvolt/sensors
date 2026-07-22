"""Mocks only the raw I2C bus transaction level (tests/machine.py's fake machine.I2C, extended
with a read_queue for word-oriented protocols like this one - see its own module docstring),
matching tests/README.md's mocking boundary: asy_sgp40_driver.py's own protocol/CRC/locking logic
and voc_algorithm.py's real VOCAlgorithm run unmocked. FRAM-backed backup/restore tests use the
real AsyFramManager against tests/_fram_chip_fake.py's simulated chip, matching
tests/test_fram_integration.py's own pattern.
"""

import asyncio
import json
import os

from _fram_chip_fake import FakeMB85RS64V
from machine import I2C as FakeI2C

import asy_fram_manager
import asy_spi_driver
from asy_fram_manager import AsyFramManager
from asy_i2c_driver import I2C
from asy_sgp40_driver import SGP40, SGP40_I2C, SGP40_Reader
from asy_spi_driver import SPI
from print_log import PrintLogHistoryStore

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")

# Same one-process-per-test-file FRAM chip swap as tests/test_fram_integration.py.
asy_spi_driver._SPI = FakeMB85RS64V  # type: ignore[misc]

_TMP_DIR = "tests/_tmp"


def _tmp_path(name: str) -> str:
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass  # already exists
    return _TMP_DIR + "/" + name

_CRC_POLY = 0x31  # datasheet Table 7


def _crc8(data: bytes) -> int:
    # Independent CRC-8 reimplementation for building fixtures - not the driver's own
    # crc_checks.CRC8, so a bug shared between the two couldn't hide behind a self-consistent test.
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ _CRC_POLY) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def _word(value: int) -> bytes:
    payload = bytes([(value >> 8) & 0xFF, value & 0xFF])
    return payload + bytes([_crc8(payload)])


def test_crc8_helper_matches_datasheet_example() -> None:
    assert _crc8(b"\xbe\xef") == 0x92


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


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
# initialize() - serial number / self-test gates (feature-set check intentionally removed)
# ---------------------------------------------------------------------------


def test_initialize_success_probes_serial_number_then_self_test_then_resets() -> None:
    sgp = make_sgp()
    fake_bus = bus(sgp.i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    run(sgp.initialize())
    writes = [entry for entry in fake_bus.log if entry[0] == "writeto"]
    assert writes[0][1:3] == (0x59, b"\x36\x82")  # get serial number
    assert writes[1][1:3] == (0x59, b"\x28\x0e")  # execute self-test
    assert writes[2] == ("writeto", 0x00, b"\x06", True)  # true general-call reset - the bug fix


def test_initialize_serial_number_mismatch_raises() -> None:
    sgp = make_sgp()
    fake_bus = bus(sgp.i2c_sgp40.i2c_device.i2c)
    fake_bus.read_queue.append(_word(0x0001) + _word(0x1234) + _word(0x5678))  # word[0] != 0
    try:
        run(sgp.initialize())
        raise AssertionError("expected RuntimeError")
    except RuntimeError as e:
        assert "Serial number" in str(e)


def test_initialize_self_test_failure_raises() -> None:
    sgp = make_sgp()
    fake_bus = bus(sgp.i2c_sgp40.i2c_device.i2c)
    fake_bus.read_queue.append(_word(0x0000) + _word(0x1234) + _word(0x5678))
    fake_bus.read_queue.append(_word(0x4B00))  # datasheet: one or more tests failed
    try:
        run(sgp.initialize())
        raise AssertionError("expected RuntimeError")
    except RuntimeError as e:
        assert "Self test failed" in str(e)


def test_initialize_self_test_success_ignores_nonzero_low_byte() -> None:
    # Regression test: datasheet Table 13 documents 0xD4 0xXX as "all tests passed, ignore 0xXX" -
    # the low byte is not guaranteed to be 0x00. A prior version (inherited from the deployed
    # driver) checked the full word against 0xD400 and would have spuriously raised here.
    sgp = make_sgp()
    fake_bus = bus(sgp.i2c_sgp40.i2c_device.i2c)
    fake_bus.read_queue.append(_word(0x0000) + _word(0x1234) + _word(0x5678))
    fake_bus.read_queue.append(_word(0xD4FF))  # high byte 0xD4 = pass, non-zero low byte
    run(sgp.initialize())  # must not raise


def test_initialize_no_feature_set_check_is_issued() -> None:
    # Regression test for the dropped, undocumented 0x20 0x2F check (see BACKLOG.md).
    sgp = make_sgp()
    fake_bus = bus(sgp.i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    run(sgp.initialize())
    commands = [entry[2] for entry in fake_bus.log if entry[0] == "writeto"]
    assert b"\x20\x2f" not in commands


def test_initialize_bus_nak_propagates_as_oserror() -> None:
    # Real transaction failures are allowed to propagate uncaught from SGP40_I2C (src/README.md
    # section 2's I2C carve-out) - SGP40_Reader._init_sgp() is what closes this gap.
    sgp = make_sgp()
    fake_bus = bus(sgp.i2c_sgp40.i2c_device.i2c)
    fake_bus.nak_addresses.add(0x59)
    try:
        run(sgp.initialize())
        raise AssertionError("expected OSError")
    except OSError:
        pass


def test_initialize_corrupted_response_raises_crc_error() -> None:
    sgp = make_sgp()
    fake_bus = bus(sgp.i2c_sgp40.i2c_device.i2c)
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
    fake_bus = bus(sgp.i2c_sgp40.i2c_device.i2c)
    run(sgp._reset())
    assert fake_bus.log[-1] == ("writeto", 0x00, b"\x06", True)
    # Not the SGP40's own address, and not the old two-byte [0x00, 0x06] payload sent to it.
    assert all(entry[1] != 0x59 for entry in fake_bus.log if entry[0] == "writeto")


def test_reset_tolerates_nak_at_general_call_address() -> None:
    sgp = make_sgp()
    fake_bus = bus(sgp.i2c_sgp40.i2c_device.i2c)
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
    fake_bus = bus(sgp.i2c_sgp40.i2c_device.i2c)
    fake_bus.read_queue.append(_word(30000))
    raw = run(sgp.measure_raw())  # defaults: 25C, 50%RH
    assert raw == 30000
    writes = [entry for entry in fake_bus.log if entry[0] == "writeto"]
    assert writes[-1][2] == b"\x26\x0f\x80\x00\xa2\x66\x66\x93"  # datasheet Table 9's own example


def test_measure_raw_custom_compensation_encodes_correct_ticks_and_crc() -> None:
    sgp = make_sgp()
    fake_bus = bus(sgp.i2c_sgp40.i2c_device.i2c)
    fake_bus.read_queue.append(_word(12345))
    run(sgp.measure_raw(temperature=-45, relative_humidity=0))
    writes = [entry for entry in fake_bus.log if entry[0] == "writeto"]
    sent = writes[-1][2]
    assert sent[0:2] == b"\x26\x0f"
    assert sent[2:5] == b"\x00\x00\x81"  # 0% RH -> 0x0000, CRC 0x81 (Table 10)
    assert sent[5:8] == b"\x00\x00\x81"  # -45C -> 0x0000, CRC 0x81 (Table 10)


def test_get_raw_crc_mismatch_raises() -> None:
    sgp = make_sgp()
    fake_bus = bus(sgp.i2c_sgp40.i2c_device.i2c)
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
    fake_bus = bus(sgp.i2c_sgp40.i2c_device.i2c)
    fake_bus.read_queue.append(_word(30000))
    voc_index, raw, serialized, deserialized = run(sgp.measure_index_and_raw(temperature=25, relative_humidity=50))
    assert raw == 30000
    assert isinstance(voc_index, int)
    assert serialized is False
    assert deserialized is False


def test_measure_index_and_raw_reset_reinitializes_algorithm_state() -> None:
    sgp = make_sgp()
    fake_bus = bus(sgp.i2c_sgp40.i2c_device.i2c)
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


async def _no_comp_data() -> list[float | None]:
    return [None, None]


async def _comp_data() -> list[float | None]:
    return [25.0, 50.0]


def make_reader(**kwargs: object) -> SGP40_Reader:
    kwargs.setdefault("cfg_path", _tmp_path("") + "/")
    return SGP40_Reader(make_i2c(), _comp_data, max_i2c_err=2, **kwargs)  # type: ignore[arg-type]


def test_init_sgp_resets_the_real_base_class_error_counter() -> None:
    # Regression test: _init_sgp() used to write self.err_cnt_internal (no underscore), a dead
    # attribute distinct from base_classes.py's real self._err_cnt_internal (see BACKLOG.md).
    reader = make_reader()
    reader._err_cnt_internal = 7  # simulate a streak accumulated before a supervisor restart
    fake_bus = bus(reader.sgp.i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    ok = run(reader._init_sgp())
    assert ok is True
    assert reader._err_cnt_internal == 0
    assert not hasattr(reader, "err_cnt_internal")  # the old, mistyped dead attribute must not exist


def test_read_sgp_without_compensation_data_returns_all_none() -> None:
    reader = SGP40_Reader(make_i2c(), _no_comp_data, max_i2c_err=2, cfg_path=_tmp_path("") + "/")
    data, compensated, serialized = run(reader._read_sgp(None, False, False))
    assert data == SGP40(None, None, None)
    assert compensated is False
    assert serialized is False


def test_read_sgp_with_compensation_data_stores_a_result() -> None:
    reader = make_reader()
    fake_bus = bus(reader.sgp.i2c_sgp40.i2c_device.i2c)
    fake_bus.read_queue.append(_word(31000))
    data, compensated, _serialized = run(reader._read_sgp(None, False, False))
    assert compensated is True
    assert data.Raw == 31000
    assert isinstance(data.VOC, int)
    assert data.TS is not None


def test_store_sgp_ignores_partial_none_results() -> None:
    reader = make_reader()
    run(reader._store_sgp(SGP40(None, 100, 12345)))
    assert run(reader.get_data()) == SGP40(None, None, None)


def test_store_sgp_persists_a_complete_result() -> None:
    reader = make_reader()
    run(reader._store_sgp(SGP40(42, 31000, 12345)))
    assert run(reader.get_data()) == SGP40(42, 31000, 12345)


def test_check_storage_without_fram_returns_no_buffer_and_resets_voc_timers() -> None:
    reader = make_reader()  # no fram_storage -> ts_storage is None
    reader.voc_init = 5
    reader.voc_write = 5
    buf, serialize, deserialize, cfg_values = run(reader._check_storage())
    assert (buf, serialize, deserialize, cfg_values) == (None, False, False, None)
    assert reader.voc_init == 0
    assert reader.voc_write == 0


def test_run_restore_without_deserialize_trigger_is_a_no_op() -> None:
    reader = make_reader()
    assert run(reader._run_restore(None, False, None)) is False


def test_get_mem_status_reflects_last_backup_and_restored_from() -> None:
    reader = make_reader()
    assert run(reader.get_mem_status()) == (None, None)
    reader.last_backup = 111
    reader.restored_from = 222
    assert run(reader.get_mem_status()) == (111, 222)


def test_get_error_counter_reflects_logged_errors() -> None:
    reader = make_reader()
    run(reader.pr.setup())
    empty = SGP40(None, None, None)
    run(reader._error_check(empty, "SGP40"))
    run(reader._error_check(empty, "SGP40"))
    run(reader._error_check(empty, "SGP40"))  # exceeds max_i2c_err=2 -> logged as a real error
    log = run(reader.get_error_counter())
    err_count = log["SGP40"]["ErrCount"]
    assert isinstance(err_count, int)
    assert err_count >= 1


def test_start_asy_read_returns_a_real_task() -> None:
    reader = make_reader()
    fake_bus = bus(reader.sgp.i2c_sgp40.i2c_device.i2c)
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
    assert reader.trigger_timer.callback is not None
    reader.trigger_timer.trigger()  # fake machine.Timer.trigger() - fires the callback synchronously
    assert run(asyncio.wait_for(reader.trigger_event.wait(), 1)) is None
    reader.stop_timer()
    assert reader.trigger_timer.deinit_called is True


def test_error_check_gives_up_after_max_i2c_err_consecutive_failures() -> None:
    reader = make_reader()  # max_i2c_err=2
    empty = SGP40(None, None, None)
    assert run(reader._error_check(empty, "SGP40")) is True  # 1st failure
    assert run(reader._error_check(empty, "SGP40")) is True  # 2nd failure
    assert run(reader._error_check(empty, "SGP40")) is False  # 3rd failure exceeds max_i2c_err=2


def test_error_check_recovers_after_a_success() -> None:
    reader = make_reader()
    empty = SGP40(None, None, None)
    good = SGP40(1, 30000, 12345)
    run(reader._error_check(empty, "SGP40"))
    run(reader._error_check(empty, "SGP40"))
    assert run(reader._error_check(good, "SGP40")) is True
    assert reader._err_cnt_internal == 1  # decremented by the success, not reset to 0


def test_reset_voc_true_sets_the_reset_flag() -> None:
    reader = make_reader()
    assert reader.reset is False
    run(reader.reset_voc(True))
    assert reader.reset is True


def test_reset_voc_false_is_a_no_op() -> None:
    reader = make_reader()
    reader.reset = True
    run(reader.reset_voc(False))
    assert reader.reset is True  # unchanged - reset_voc's own documented contract


def test_reset_never_drops_but_each_sub_part_completes_at_most_once() -> None:
    # Reset has two independent sub-parts tracked separately (_reset_fram_cleared/
    # _reset_algo_applied): self.reset only clears once BOTH have succeeded (never silently drops
    # a user's reset request), but neither part repeats once it has already succeeded, even while
    # the other is still being retried.
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    reader = SGP40_Reader(
        make_i2c(),
        _no_comp_data,
        fram_storage=manager,
        fram_ntp_callback=_ntp_synced,
        max_i2c_err=5,
        cfg_path=_tmp_path("") + "/",
    )
    fake_bus = bus(reader.sgp.i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    run(reader._init_sgp())
    run(reader.reset_voc(True))
    assert reader.reset is True

    # Cycle 1: no compensation data yet, but the FRAM clear doesn't depend on it at all - it
    # succeeds this cycle against the real, working chip. The algorithm-reset half hasn't run yet
    # (measure_index_and_raw() is never reached without compensation data), so the request as a
    # whole is still pending.
    run(reader._read_sgp(None, False, False))
    assert reader.reset is True
    assert reader._reset_fram_cleared is True
    assert reader._reset_algo_applied is False

    # Pause FRAM storage: if _read_sgp() incorrectly re-attempted the already-succeeded clear(), it
    # would now fail and leave self.reset stuck True forever - proving it does NOT touch FRAM again.
    manager.set_pause(True)
    reader.comp_callback = _comp_data
    fake_bus.read_queue.append(_word(30000))
    run(reader._read_sgp(None, False, False))
    manager.set_pause(False)
    assert reader.reset is False  # both parts satisfied - the clear was correctly not retried
    assert reader.sgp._voc_algorithm is not None
    assert reader.sgp._voc_algorithm.params.muptime == 1 * 65536  # vocalgorithm_reset() applied exactly once


def test_reset_retries_only_the_fram_half_once_the_algo_half_already_succeeded() -> None:
    # Mirror of the test above: the algorithm reset succeeds first (compensation data available
    # immediately), but the FRAM clear keeps failing (paused) - vocalgorithm_reset() must NOT run
    # again on a later cycle just because the FRAM half is still incomplete.
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    reader = SGP40_Reader(
        make_i2c(),
        _comp_data,
        fram_storage=manager,
        fram_ntp_callback=_ntp_synced,
        max_i2c_err=5,
        cfg_path=_tmp_path("") + "/",
    )
    fake_bus = bus(reader.sgp.i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    run(reader._init_sgp())
    manager.set_pause(True)  # FRAM clear fails every attempt until unpaused below
    run(reader.reset_voc(True))

    fake_bus.read_queue.append(_word(30000))
    run(reader._read_sgp(None, False, False))
    assert reader.reset is True  # FRAM half still pending
    assert reader._reset_algo_applied is True  # algorithm reset already succeeded, first cycle
    assert reader.sgp._voc_algorithm is not None
    assert reader.sgp._voc_algorithm.params.muptime == 1 * 65536

    # Retry with the FRAM clear still failing - the algorithm reset must NOT run again (muptime
    # keeps advancing by one sample per call, never resetting back to 1 * 65536).
    fake_bus.read_queue.append(_word(30000))
    run(reader._read_sgp(None, False, False))
    assert reader.reset is True
    assert reader.sgp._voc_algorithm.params.muptime == 2 * 65536

    # FRAM finally recovers - the reset completes, still without ever re-applying the algo reset.
    manager.set_pause(False)
    fake_bus.read_queue.append(_word(30000))
    run(reader._read_sgp(None, False, False))
    assert reader.reset is False
    assert reader.sgp._voc_algorithm.params.muptime == 3 * 65536


async def _nan_comp_data() -> list[float | None]:
    return [float("nan"), 50.0]


async def _inf_comp_data() -> list[float | None]:
    return [25.0, float("inf")]


def test_read_sgp_nan_compensation_temperature_is_caught_not_propagated() -> None:
    # _celsius_to_ticks()/_relative_humidity_to_ticks() call int() on the compensation value, which
    # is never validated beyond "not None" before reaching there - confirmed directly against the
    # real interpreter that NaN raises ValueError (and Inf raises OverflowError, see the next test).
    # Already structurally safe (both calls happen inside _read_sgp()'s own wrapping
    # try/except Exception), but previously untested.
    reader = make_reader()
    reader.comp_callback = _nan_comp_data
    run(reader.pr.setup())
    data, compensated, serialized = run(reader._read_sgp(None, False, False))
    assert data == SGP40(None, None, None)
    assert compensated is True  # comp data was "available" (not None) - the arithmetic itself failed
    assert serialized is False
    log = run(reader.get_error_counter())
    err_count = log["SGP40"]["ErrCount"]
    assert isinstance(err_count, int)
    assert err_count >= 1


def test_read_sgp_inf_compensation_humidity_is_caught_not_propagated() -> None:
    reader = make_reader()
    reader.comp_callback = _inf_comp_data
    run(reader.pr.setup())
    data, compensated, serialized = run(reader._read_sgp(None, False, False))
    assert data == SGP40(None, None, None)
    assert compensated is True
    assert serialized is False
    log = run(reader.get_error_counter())
    err_count = log["SGP40"]["ErrCount"]
    assert isinstance(err_count, int)
    assert err_count >= 1


def test_run_backup_genuine_fram_write_failure_is_logged_as_an_error() -> None:
    # Distinct from the "no NTP yet" deferral path
    # (test_fram_backup_without_ntp_sync_is_deferred_not_lost): here NTP is synced and require_ntp
    # is already satisfied (voc_write forced to 0), but the underlying FRAM write itself genuinely
    # fails - manager.set_pause(True) makes _mempause() return True, so _write() bails out with a
    # clean False without ever touching the real chip, the same shape a genuine hardware fault
    # takes. Previously untested branch: "Schreibfehler beim Backup!" (errno=13).
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    reader = SGP40_Reader(
        make_i2c(),
        _comp_data,
        fram_storage=manager,
        fram_ntp_callback=_ntp_synced,
        max_i2c_err=5,
        cfg_path=_tmp_path("") + "/",
    )
    fake_bus = bus(reader.sgp.i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    run(reader._init_sgp())
    reader.voc_write = 0  # require_ntp=False - isolates the "genuine write failure" branch
    buf, _serialize, _deserialize, cfg_values = run(reader._check_storage())
    manager.set_pause(True)
    run(reader._run_backup(buf, True, cfg_values))
    manager.set_pause(False)
    assert reader.last_backup is None
    log = run(reader.get_error_counter())
    err_count = log["SGP40"]["ErrCount"]
    assert isinstance(err_count, int)
    assert err_count >= 1


def test_run_restore_applies_backup_anyway_once_wait_time_ntp_budget_is_exhausted() -> None:
    # Escape hatch in _run_restore(): if a valid, timestamped backup exists but NTP still hasn't
    # synced by the time voc_init's WaitTimeNTP countdown reaches 0, the restore is applied anyway
    # without ever checking BackupMaxAge - recovering a possibly-unverifiable-age baseline rather
    # than losing it entirely. Previously untested (existing FRAM restore tests all use _ntp_synced
    # throughout).
    manager, _chip, spi_bus = make_fram_manager()
    run(manager.setup())

    async def scenario() -> tuple[bool, int | None]:
        writer = SGP40_Reader(
            make_i2c(),
            _comp_data,
            fram_storage=manager,
            fram_ntp_callback=_ntp_synced,
            max_i2c_err=5,
            cfg_path=_tmp_path("") + "/",
        )
        fake_bus = bus(writer.sgp.i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus)
        await writer._init_sgp()
        await _write_and_back_up(writer, fake_bus, 1)  # a real, valid, NTP-timestamped backup

        manager2 = make_fram_manager_sharing(spi_bus)
        await manager2.setup()
        reader = SGP40_Reader(
            make_i2c(),
            _comp_data,
            fram_storage=manager2,
            fram_ntp_callback=_ntp_not_synced,  # the *reader's* own current time is never NTP-synced
            max_i2c_err=5,
            cfg_path=_tmp_path("") + "/",
        )
        fake_bus2 = bus(reader.sgp.i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus2)
        await reader._init_sgp()
        reader.voc_init = 1  # about to hit 0 on the next _check_storage() cycle
        buf2, _serialize2, deserialize2, cfg_values2 = await reader._check_storage()
        assert reader.voc_init == 0  # countdown just reached its end this same cycle
        return await reader._run_restore(buf2, deserialize2, cfg_values2), reader.restored_from

    restored, restored_from = run(scenario())
    assert restored is True  # applied anyway, despite age being unknowable (no NTP)
    # A real write-time timestamp (the backup itself has one - only the *reader's* clock is
    # unsynced), not the ts=-1 "no timestamp at all" sentinel from the ts_is_None branch.
    assert restored_from is not None and restored_from > 0


def test_run_backup_writes_without_timestamp_once_wait_time_ntp_budget_is_exhausted() -> None:
    # Symmetric to the restore-side escape hatch above: once voc_write's WaitTimeNTP countdown
    # reaches 0, require_ntp becomes False and the backup is written anyway even though NTP still
    # hasn't synced - the existing test_fram_backup_without_ntp_sync_is_deferred_not_lost only
    # covers the "still waiting" (require_ntp still True) branch, not this one.
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())

    async def scenario() -> tuple[int | None, int]:
        writer = SGP40_Reader(
            make_i2c(),
            _comp_data,
            fram_storage=manager,
            fram_ntp_callback=_ntp_not_synced,
            max_i2c_err=5,
            cfg_path=_tmp_path("") + "/",
        )
        fake_bus = bus(writer.sgp.i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus)
        await writer._init_sgp()
        writer.voc_write = 0  # budget already exhausted -> require_ntp will be False
        buf, _serialize, _deserialize, cfg_values = await writer._check_storage()
        fake_bus.read_queue.append(_word(30000))
        data, _compensated, _serialized = await writer._read_sgp(buf, True, False)
        await writer._store_sgp(data)
        await writer._run_backup(buf, True, cfg_values)
        return writer.last_backup, writer.voc_write

    last_backup, voc_write_after = run(scenario())
    assert last_backup == 0  # written without a timestamp - the documented "backup exists, no TS" sentinel
    assert voc_write_after == 0  # require_ntp was False, so the "resynced" branch never re-arms it


def test_check_storage_backup_counter_wraps_before_it_could_overflow() -> None:
    # The 100000 wraparound guard only ever matters when BackupPeriod is disabled (0) - any nonzero
    # period's own periodic-trigger reset (backup_counter=0 once the period elapses) already fires
    # long before 100000 for every value in that field's own valid range (max 60*1440 = 86400 <
    # 100000), so this specific guard is otherwise unreachable. Previously untested.
    cfg_dir = _sgp_cfg_dir("backupdisabled")
    _write_sgp_cfg(cfg_dir, {"BackupPeriod": 0, "BackupMaxAge": 7200, "WaitTimeNTP": 30})
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    reader = SGP40_Reader(
        make_i2c(),
        _comp_data,
        fram_storage=manager,
        fram_ntp_callback=_ntp_synced,
        max_i2c_err=5,
        cfg_path=cfg_dir,
    )
    fake_bus = bus(reader.sgp.i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    run(reader._init_sgp())
    reader.backup_counter = 99999
    run(reader._check_storage())
    assert reader.backup_counter == 0  # wrapped, not left to grow past 100000


def test_init_sgp_sets_verify_to_the_documented_formula() -> None:
    # ceil((10 * _FRAM_VERIFY_MINS) / BackupPeriod) * 0.1 - roughly "verify once per
    # _FRAM_VERIFY_MINS (60min) worth of backups". Confirmed against the real
    # ts_storage.get_verify(), not just that _init_sgp() succeeds.
    cfg_dir = _sgp_cfg_dir("verify")
    _write_sgp_cfg(cfg_dir, {"BackupPeriod": 5, "BackupMaxAge": 7200, "WaitTimeNTP": 30})
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    reader = SGP40_Reader(
        make_i2c(),
        _comp_data,
        fram_storage=manager,
        fram_ntp_callback=_ntp_synced,
        max_i2c_err=5,
        cfg_path=cfg_dir,
    )
    fake_bus = bus(reader.sgp.i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    assert run(reader._init_sgp()) is True
    assert reader.ts_storage is not None
    # ceil(600/5)*0.1 = ceil(120.0)*0.1 = 120*0.1 = 12.0 -> int(12.0) = 12
    assert run(reader.ts_storage.get_verify()) == 12


def test_simultaneous_restore_and_backup_in_one_cycle_reads_then_rewrites_the_same_buffer() -> None:
    # _check_storage() can independently set both serialize and deserialize True in the same cycle
    # (a restore still pending AND the periodic backup period elapsing at the same tick) - both then
    # share the SAME buffer: _run_restore() reads the old state into it first, then
    # vocalgorithm_proc_ser_des() unpacks it, processes one new sample, and re-packs the *updated*
    # state back into that same buffer, which _run_backup() then writes out. Never exercised by any
    # existing test (each of which only ever triggers one or the other, never both at once).
    manager, _chip, spi_bus = make_fram_manager()
    run(manager.setup())

    async def scenario() -> tuple[bool, bool, int]:
        writer = SGP40_Reader(
            make_i2c(),
            _comp_data,
            fram_storage=manager,
            fram_ntp_callback=_ntp_synced,
            max_i2c_err=5,
            cfg_path=_tmp_path("") + "/",
        )
        fake_bus = bus(writer.sgp.i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus)
        await writer._init_sgp()
        # Converge past the initial blackout so the restored state is meaningfully distinguishable
        # - _write_and_back_up() (used by the existing FRAM round-trip test) threads buf through
        # _read_sgp() on the final sample so pack_into() actually populates it before the backup
        # write; passing buf=None here (like the plain read_loop tests do) would instead persist a
        # freshly-allocated, all-zero buffer that was never populated at all.
        await _write_and_back_up(writer, fake_bus, 60)

        manager2 = make_fram_manager_sharing(spi_bus)
        await manager2.setup()
        reader = SGP40_Reader(
            make_i2c(),
            _comp_data,
            fram_storage=manager2,
            fram_ntp_callback=_ntp_synced,
            max_i2c_err=5,
            cfg_path=_tmp_path("") + "/",
        )
        fake_bus2 = bus(reader.sgp.i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus2)
        await reader._init_sgp()
        # Force both triggers to coincide on the very next _check_storage() cycle: WaitTimeNTP's
        # default (30) leaves voc_init > 0 on a fresh reader already; backup_counter is set one
        # short of BackupPeriod's default (1) * 60 trigger threshold.
        reader.backup_counter = 59
        buf2, serialize2, deserialize2, cfg_values2 = await reader._check_storage()
        assert serialize2 is True
        assert deserialize2 is True
        deserialize2 = await reader._run_restore(buf2, deserialize2, cfg_values2)
        assert deserialize2 is True  # restore actually applied
        fake_bus2.read_queue.append(_word(31000))
        data, _compensated, serialized2 = await reader._read_sgp(buf2, serialize2, deserialize2)
        await reader._store_sgp(data)
        assert reader.sgp._voc_algorithm is not None
        return serialized2, True, reader.sgp._voc_algorithm.params.muptime

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
    assert reader.get_timer_starters() == [reader.start_timer]


# ---------------------------------------------------------------------------
# Config schema - every field's valid range/defaults, single- and multi-field invalid
# recombinations, read through the real driver + ConfigManager (not config_manager.py's own
# generic validation machinery - see tests/test_config_manager.py for that).
# ---------------------------------------------------------------------------

_SGP_CFG_FILE = "config_SGP40.cfg"


def _sgp_cfg_dir(name: str) -> str:
    # A fresh subdirectory per test, not the shared _tmp_path("") every other test in this file
    # uses - those never write custom values, only ever rely on schema defaults, so they don't
    # collide; these tests write real per-test config files and must not see each other's state.
    # _tmp_path("") first: guarantees _TMP_DIR itself exists before nesting a subdirectory under
    # it - on a fresh checkout (no leftover tests/_tmp from a prior local run) this test file's own
    # first call could otherwise hit ENOENT (parent missing), which the bare `except OSError: pass`
    # below would silently swallow together with the real "already exists" case it's meant for,
    # leaving the directory never actually created (caught by CI, not by a local rerun that reused
    # an already-existing tests/_tmp from an earlier session).
    _tmp_path("")
    path = _TMP_DIR + "/sgpcfg_" + name
    try:
        os.mkdir(path)
    except OSError:
        pass  # already exists
    return path + "/"


def _write_sgp_cfg(cfg_dir: str, values: dict[str, object]) -> None:
    with open(cfg_dir + _SGP_CFG_FILE, "w") as f:
        json.dump(values, f)


def test_get_dict_cfg_reports_schema_defaults_when_no_config_file_exists() -> None:
    # Also locks in the schema's own documented bounds/defaults against silent drift: BackupPeriod
    # 0-1440min (24h) default 1, BackupMaxAge 0-10080min (7 days) default 7200, WaitTimeNTP 0-600s
    # (10min, matches _MAX_NTP_WAITTIME) default 30 - _VAL_BP/_VAL_BMAX/_VAL_WT themselves are
    # micropython.const()-folded at compile time and not importable (same as asy_fram_manager.py's
    # own _STATUS_* constants - see tests/test_asy_fram_manager.py's own convention), so this reads
    # them back through the real driver + ConfigManager instead of importing the tuples directly.
    cfg_dir = _sgp_cfg_dir("defaults")
    reader = SGP40_Reader(make_i2c(), _comp_data, max_i2c_err=2, cfg_path=cfg_dir)
    cfg = run(reader.get_dict_cfg())
    assert cfg["SGP40"] == {"BackupPeriod": 1, "BackupMaxAge": 7200, "WaitTimeNTP": 30}


def test_get_dict_cfg_reports_all_valid_minimum_boundary_values() -> None:
    cfg_dir = _sgp_cfg_dir("minbound")
    _write_sgp_cfg(cfg_dir, {"BackupPeriod": 0, "BackupMaxAge": 0, "WaitTimeNTP": 0})
    reader = SGP40_Reader(make_i2c(), _comp_data, max_i2c_err=2, cfg_path=cfg_dir)
    cfg = run(reader.get_dict_cfg())
    assert cfg["SGP40"] == {"BackupPeriod": 0, "BackupMaxAge": 0, "WaitTimeNTP": 0}


def test_get_dict_cfg_reports_all_valid_maximum_boundary_values() -> None:
    cfg_dir = _sgp_cfg_dir("maxbound")
    _write_sgp_cfg(cfg_dir, {"BackupPeriod": 1440, "BackupMaxAge": 10080, "WaitTimeNTP": 600})
    reader = SGP40_Reader(make_i2c(), _comp_data, max_i2c_err=2, cfg_path=cfg_dir)
    cfg = run(reader.get_dict_cfg())
    assert cfg["SGP40"] == {"BackupPeriod": 1440, "BackupMaxAge": 10080, "WaitTimeNTP": 600}


def test_get_dict_cfg_reports_a_typical_valid_custom_combination() -> None:
    cfg_dir = _sgp_cfg_dir("typical")
    _write_sgp_cfg(cfg_dir, {"BackupPeriod": 60, "BackupMaxAge": 1440, "WaitTimeNTP": 120})
    reader = SGP40_Reader(make_i2c(), _comp_data, max_i2c_err=2, cfg_path=cfg_dir)
    cfg = run(reader.get_dict_cfg())
    assert cfg["SGP40"] == {"BackupPeriod": 60, "BackupMaxAge": 1440, "WaitTimeNTP": 120}


def test_config_single_invalid_backup_period_defaults_only_that_field() -> None:
    cfg_dir = _sgp_cfg_dir("badbp")
    _write_sgp_cfg(cfg_dir, {"BackupPeriod": 1441, "BackupMaxAge": 1440, "WaitTimeNTP": 120})
    reader = SGP40_Reader(make_i2c(), _comp_data, max_i2c_err=2, cfg_path=cfg_dir)
    cfg = run(reader.get_dict_cfg())
    assert cfg["SGP40"] == {"BackupPeriod": 1, "BackupMaxAge": 1440, "WaitTimeNTP": 120}  # only BP reverted


def test_config_single_invalid_backup_max_age_defaults_only_that_field() -> None:
    cfg_dir = _sgp_cfg_dir("badbmax")
    _write_sgp_cfg(cfg_dir, {"BackupPeriod": 60, "BackupMaxAge": -1, "WaitTimeNTP": 120})
    reader = SGP40_Reader(make_i2c(), _comp_data, max_i2c_err=2, cfg_path=cfg_dir)
    cfg = run(reader.get_dict_cfg())
    assert cfg["SGP40"] == {"BackupPeriod": 60, "BackupMaxAge": 7200, "WaitTimeNTP": 120}


def test_config_single_invalid_wait_time_ntp_defaults_only_that_field() -> None:
    cfg_dir = _sgp_cfg_dir("badwt")
    _write_sgp_cfg(cfg_dir, {"BackupPeriod": 60, "BackupMaxAge": 1440, "WaitTimeNTP": 601})
    reader = SGP40_Reader(make_i2c(), _comp_data, max_i2c_err=2, cfg_path=cfg_dir)
    cfg = run(reader.get_dict_cfg())
    assert cfg["SGP40"] == {"BackupPeriod": 60, "BackupMaxAge": 1440, "WaitTimeNTP": 30}


def test_config_two_invalid_fields_each_independently_defaulted() -> None:
    cfg_dir = _sgp_cfg_dir("badtwo")
    _write_sgp_cfg(cfg_dir, {"BackupPeriod": -5, "BackupMaxAge": 1440, "WaitTimeNTP": 99999})
    reader = SGP40_Reader(make_i2c(), _comp_data, max_i2c_err=2, cfg_path=cfg_dir)
    cfg = run(reader.get_dict_cfg())
    assert cfg["SGP40"] == {"BackupPeriod": 1, "BackupMaxAge": 1440, "WaitTimeNTP": 30}


def test_config_all_three_fields_invalid_falls_back_to_full_defaults() -> None:
    cfg_dir = _sgp_cfg_dir("badall")
    _write_sgp_cfg(cfg_dir, {"BackupPeriod": -1, "BackupMaxAge": 999999, "WaitTimeNTP": -30})
    reader = SGP40_Reader(make_i2c(), _comp_data, max_i2c_err=2, cfg_path=cfg_dir)
    cfg = run(reader.get_dict_cfg())
    assert cfg["SGP40"] == {"BackupPeriod": 1, "BackupMaxAge": 7200, "WaitTimeNTP": 30}
    # driver must still init cleanly despite an all-invalid config file already on disk
    fake_bus = bus(reader.sgp.i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    assert run(reader._init_sgp()) is True


def test_config_wrong_type_values_single_and_combined() -> None:
    cfg_dir = _sgp_cfg_dir("wrongtype")
    _write_sgp_cfg(cfg_dir, {"BackupPeriod": "sixty", "BackupMaxAge": 1440, "WaitTimeNTP": 12.5})
    reader = SGP40_Reader(make_i2c(), _comp_data, max_i2c_err=2, cfg_path=cfg_dir)
    cfg = run(reader.get_dict_cfg())
    assert cfg["SGP40"] == {"BackupPeriod": 1, "BackupMaxAge": 1440, "WaitTimeNTP": 30}


def test_config_missing_keys_use_defaults() -> None:
    cfg_dir = _sgp_cfg_dir("missing")
    _write_sgp_cfg(cfg_dir, {"BackupMaxAge": 1440})  # BackupPeriod, WaitTimeNTP both absent
    reader = SGP40_Reader(make_i2c(), _comp_data, max_i2c_err=2, cfg_path=cfg_dir)
    cfg = run(reader.get_dict_cfg())
    assert cfg["SGP40"] == {"BackupPeriod": 1, "BackupMaxAge": 1440, "WaitTimeNTP": 30}


def test_init_sgp_applies_custom_wait_time_ntp_from_valid_config() -> None:
    # _init_sgp() must actually thread a valid custom WaitTimeNTP into voc_init/voc_write, not just
    # report it via get_dict_cfg() - the two are separate ConfigManager reads internally.
    cfg_dir = _sgp_cfg_dir("applywt")
    _write_sgp_cfg(cfg_dir, {"BackupPeriod": 1, "BackupMaxAge": 7200, "WaitTimeNTP": 5})
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    reader = SGP40_Reader(
        make_i2c(),
        _comp_data,
        fram_storage=manager,
        fram_ntp_callback=_ntp_synced,
        max_i2c_err=2,
        cfg_path=cfg_dir,
    )
    fake_bus = bus(reader.sgp.i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    assert run(reader._init_sgp()) is True
    assert reader.voc_init == 5
    assert reader.voc_write == 5


# ---------------------------------------------------------------------------
# read_loop() - end-to-end wiring, driven via real trigger events and cancellation
# (matches system_service.py's own test convention for a supervising while-True loop)
# ---------------------------------------------------------------------------


class _FastAsyncSleep:
    # _init_sgp()/initialize()/_reset() make several real asyncio.sleep() calls (3ms/500ms/100ms
    # command delays, plus _reset()'s 1s post-reset settle) - far too slow for a test driving
    # read_loop() through several full cycles. asyncio.sleep is a shared, process-wide function
    # (same technique as tests/test_system_service.py's own _FastAsyncSleep), restored on exit
    # regardless of how the `with` block exits.
    def __enter__(self) -> "_FastAsyncSleep":
        self._real_sleep = asyncio.sleep

        async def _fast(_seconds: float) -> None:
            await self._real_sleep(0)

        asyncio.sleep = _fast  # type: ignore[assignment]  # deliberate monkeypatch, not a real caller mismatch
        return self

    def __exit__(self, *exc_info: object) -> None:
        asyncio.sleep = self._real_sleep


def test_read_loop_stores_a_result_after_one_trigger() -> None:
    reader = make_reader()
    fake_bus = bus(reader.sgp.i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)
    fake_bus.read_queue.append(_word(31500))

    async def scenario() -> SGP40:
        task = asyncio.create_task(reader.read_loop())
        for _ in range(20):  # pump the loop until _init_sgp() (real sleeps, now fast) completes
            await asyncio.sleep(0)
        reader.trigger_event.set()
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
    # Missing compensation data does NOT count as an SGP40 error (_read_sgp returns
    # compensated=False, and _error_check's condition= gate skips counting it - see
    # BACKLOG.md's "SGP40 silently falling back... acceptable as-is"). To actually drive the
    # give-up path, keep real compensation data but fail the I2C measurement itself (CRC
    # mismatch), which _read_sgp's own except Exception turns into a real counted failure.
    reader = make_reader()  # max_i2c_err=2
    fake_bus = bus(reader.sgp.i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)

    async def scenario() -> bool:
        task = asyncio.create_task(reader.read_loop())
        for _ in range(20):
            await asyncio.sleep(0)
        for _ in range(4):  # each trigger with a corrupted measurement response counts as one failure
            bad = _word(30000)
            fake_bus.read_queue.append(bytes([bad[0] ^ 0xFF]) + bad[1:])
            reader.trigger_event.set()
            for _ in range(20):
                await asyncio.sleep(0)
                if task.done():
                    return await task
        raise AssertionError("read_loop never gave up")

    with _FastAsyncSleep():
        assert run(scenario()) is False


# ---------------------------------------------------------------------------
# FRAM-backed backup/restore - real AsyFramManager against tests/_fram_chip_fake.py
# ---------------------------------------------------------------------------


async def _ntp_synced() -> bool:
    return True


async def _ntp_not_synced() -> bool:
    return False


def make_fram_manager() -> tuple[AsyFramManager, FakeMB85RS64V, SPI]:
    spi_bus = SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    manager = AsyFramManager(spi_bus, 1, max_size=0x2000)
    chip = manager.fram._spidev.spi._spi
    assert isinstance(chip, FakeMB85RS64V)
    return manager, chip, spi_bus


def make_fram_manager_sharing(spi_bus: SPI) -> AsyFramManager:
    # A *second*, independently-allocating AsyFramManager sharing the first's underlying spi_bus
    # (and so its FakeMB85RS64V chip/memory) - simulates a real reboot's own fresh manager object
    # replaying the identical get_chunk()/get_timestamped_chunk() call sequence against surviving
    # on-chip data, matching tests/test_fram_integration.py's own pattern. Reusing the *same*
    # AsyFramManager instance for both "writer" and "reader" would be wrong: its own allocated_size
    # bump pointer keeps advancing, so a second SGP40_Reader construction would land its chunks in
    # a fresh, never-written region instead of the first one's.
    return AsyFramManager(spi_bus, 1, max_size=0x2000)


async def _write_and_back_up(writer: SGP40_Reader, fake_bus: FakeI2C, samples: int) -> tuple[SGP40, object]:
    buf, _serialize, _deserialize, cfg_values = await writer._check_storage()
    for i in range(samples):
        fake_bus.read_queue.append(_word(30000 + i * 17))
        is_last = i == samples - 1
        # serialize=True only on the final read - vocalgorithm_proc_ser_des() packs the algorithm's
        # *current* state into buf as part of that same call, exactly like a real trigger cycle
        # (SGP40_Reader.read_loop passes _check_storage()'s one serialize flag straight into the
        # same-cycle _read_sgp() call).
        data, _compensated, _serialized = await writer._read_sgp(buf, is_last, False)
        await writer._store_sgp(data)
    await writer._run_backup(buf, True, cfg_values)
    return data, buf


def test_fram_backup_writes_and_restore_recovers_full_algorithm_state() -> None:
    manager, _chip, spi_bus = make_fram_manager()
    run(manager.setup())

    async def scenario() -> tuple[SGP40, int]:
        writer = SGP40_Reader(
            make_i2c(),
            _comp_data,
            fram_storage=manager,
            fram_ntp_callback=_ntp_synced,
            max_i2c_err=5,
            cfg_path=_tmp_path("") + "/",
        )
        fake_bus = bus(writer.sgp.i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus)
        assert await writer._init_sgp() is True
        await _write_and_back_up(writer, fake_bus, 60)  # converge state past the 46-sample initial blackout
        assert writer.last_backup is not None
        assert writer.sgp._voc_algorithm is not None  # lazily created by the first real read above

        # A second reader, sharing the same FRAM backing (a simulated reboot) - fresh VOCAlgorithm,
        # never processed a single sample, must recover the exact converged state via restore.
        manager2 = make_fram_manager_sharing(spi_bus)
        run_ok = await manager2.setup()
        assert run_ok is True
        reader = SGP40_Reader(
            make_i2c(),
            _comp_data,
            fram_storage=manager2,
            fram_ntp_callback=_ntp_synced,
            max_i2c_err=5,
            cfg_path=_tmp_path("") + "/",
        )
        fake_bus2 = bus(reader.sgp.i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus2)
        assert await reader._init_sgp() is True
        buf2, _serialize2, deserialize2, cfg_values2 = await reader._check_storage()
        assert deserialize2 is True  # voc_init starts at WaitTimeNTP>0 on a fresh reader -> restore triggers
        restored = await reader._run_restore(buf2, deserialize2, cfg_values2)
        assert restored is True
        fake_bus2.read_queue.append(_word(30500))
        data2, _compensated2, _serialized2 = await reader._read_sgp(buf2, False, True)
        assert reader.sgp._voc_algorithm is not None
        return data2, reader.sgp._voc_algorithm.params.muptime

    data, muptime_after_restore = run(scenario())
    assert data.VOC is not None
    # The restored uptime must already be well past the 45s initial blackout the writer converged
    # through - proving the *whole* state (not just mean/std) survived, per voc_algorithm.py's
    # module docstring on why this differs from Sensirion's own short-interruption-only API.
    assert muptime_after_restore > 45 * 65536


class _OldTime:
    # asy_fram_manager.py's AsyFramTimestampedChunk.write_into() always stamps
    # time.mktime(time.gmtime()) (real current time - no way to inject an arbitrary past
    # timestamp through the public write API). Directly poking the chip's raw stored timestamp
    # bytes instead doesn't work: it only corrupts one of the two redundant copies' CRC, and
    # _AsyBaseFramChunk._read() then silently self-heals from the other, untouched (young) copy -
    # exactly the dual-copy-redundancy behavior asy_fram_manager.py is supposed to have. Instead,
    # monkeypatch asy_fram_manager's own `time` module reference (real `time` is a read-only
    # builtin - see BACKLOG.md/tests/test_system_service.py for the same technique) so *only* the
    # write during this test computes an artificially old, but otherwise completely valid and
    # correctly-CRC-covered, timestamp.
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
            _comp_data,
            fram_storage=manager,
            fram_ntp_callback=_ntp_synced,
            max_i2c_err=5,
            cfg_path=_tmp_path("") + "/",
        )
        fake_bus = bus(writer.sgp.i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus)
        await writer._init_sgp()

        original_time = asy_fram_manager.time
        asy_fram_manager.time = _OldTime()  # type: ignore[assignment]  # deliberate monkeypatch, not a real caller mismatch
        try:
            await _write_and_back_up(writer, fake_bus, 1)  # backed up ~999999s (~11.6 days) in the "past"
        finally:
            asy_fram_manager.time = original_time

        manager2 = make_fram_manager_sharing(spi_bus)
        await manager2.setup()
        reader = SGP40_Reader(
            make_i2c(),
            _comp_data,
            fram_storage=manager2,
            fram_ntp_callback=_ntp_synced,
            max_i2c_err=5,
            cfg_path=_tmp_path("") + "/",
        )
        fake_bus2 = bus(reader.sgp.i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus2)
        await reader._init_sgp()
        buf2, _serialize2, deserialize2, cfg_values2 = await reader._check_storage()
        return await reader._run_restore(buf2, deserialize2, cfg_values2)

    assert run(scenario()) is False  # too old - BackupMaxAge default is 7200 minutes


def test_fram_restore_finds_no_backup_on_a_never_written_chunk() -> None:
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())

    async def scenario() -> bool:
        reader = SGP40_Reader(
            make_i2c(),
            _comp_data,
            fram_storage=manager,
            fram_ntp_callback=_ntp_synced,
            max_i2c_err=5,
            cfg_path=_tmp_path("") + "/",
        )
        fake_bus = bus(reader.sgp.i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus)
        await reader._init_sgp()
        buf, _serialize, deserialize, cfg_values = await reader._check_storage()
        assert deserialize is True  # WaitTimeNTP>0 on a fresh reader -> restore is attempted
        return await reader._run_restore(buf, deserialize, cfg_values)

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
            _comp_data,
            fram_storage=manager,
            fram_ntp_callback=_ntp_not_synced,
            max_i2c_err=5,
            cfg_path=_tmp_path("") + "/",
        )
        fake_bus = bus(writer.sgp.i2c_sgp40.i2c_device.i2c)
        queue_successful_init(fake_bus)
        await writer._init_sgp()
        assert writer.voc_write > 0  # WaitTimeNTP default (30) requires NTP before the first write counts
        buf, _serialize, _deserialize, cfg_values = await writer._check_storage()
        fake_bus.read_queue.append(_word(30000))
        data, _compensated, _serialized = await writer._read_sgp(buf, False, False)
        await writer._store_sgp(data)
        await writer._run_backup(buf, True, cfg_values)
        return writer.last_backup is None, writer.backup_counter

    no_backup_yet, backup_counter = run(scenario())
    assert no_backup_yet is True  # no timestamped backup recorded without NTP while require_ntp holds
    assert backup_counter > 0  # retry is rescheduled, not silently dropped


# ---------------------------------------------------------------------------
# comp_callback / add_into fault-hardening (this review pass's own fixes)
# ---------------------------------------------------------------------------


async def _raising_comp_callback() -> list[float | None]:
    raise RuntimeError("compensation source blew up")


def test_read_sgp_comp_callback_exception_is_caught_not_propagated() -> None:
    # Regression test: comp_callback() used to be called unwrapped, unlike every other
    # caller-supplied callback in this codebase (e.g. asy_fram_manager.py's ntp_sync_callback).
    reader = SGP40_Reader(make_i2c(), _raising_comp_callback, max_i2c_err=2, cfg_path=_tmp_path("") + "/")
    run(reader.pr.setup())
    data, compensated, serialized = run(reader._read_sgp(None, False, False))
    assert data == SGP40(None, None, None)
    assert compensated is False
    assert serialized is False
    log = run(reader.get_error_counter())
    err_count = log["SGP40"]["ErrCount"]
    assert isinstance(err_count, int)
    assert err_count >= 1


class _AlwaysFailCRC:
    # Minimal fake matching CRC_Base.add_into()'s signature/contract just enough to force the
    # "computation failed" branch measure_raw() must now handle - crc_checks.py's own real CRC8
    # can't actually be made to fail add_into() through measure_raw()'s fixed, always-sufficient
    # buffer shape (see BACKLOG.md), so this is the only way to reach that path at all.
    async def add_into(self, buffer: bytearray, size: int, start: int = 0, init: int | None = None) -> int | None:
        return None


def test_measure_raw_add_into_failure_returns_none_not_raise() -> None:
    # Regression test: measure_raw()'s two crc.add_into() calls used to ignore the return value
    # entirely, unlike check_from()'s own calls a few lines away and asy_fram_manager.py's own
    # add_into() call site.
    sgp = make_sgp()
    sgp.crc = _AlwaysFailCRC()  # type: ignore[assignment]
    fake_bus = bus(sgp.i2c_sgp40.i2c_device.i2c)
    raw = run(sgp.measure_raw())
    assert raw is None
    assert fake_bus.log == []  # never even reached get_raw()'s own bus transaction


# ---------------------------------------------------------------------------
# I2C hardware-fault propagation - NAK/OSError specifically (distinct from the CRC-mismatch
# RuntimeError path already covered above). Proves SGP40_I2C's documented "OSError allowed to
# propagate" carve-out (src/README.md section 2) is actually absorbed by SGP40_Reader's own
# wrapping try/except, all the way up through read_loop()'s error-counting/give-up logic.
# ---------------------------------------------------------------------------


def test_read_sgp_i2c_nak_during_measurement_is_caught_and_counted() -> None:
    reader = make_reader()
    fake_bus = bus(reader.sgp.i2c_sgp40.i2c_device.i2c)
    fake_bus.nak_addresses.add(0x59)  # the sensor itself stops acking mid-measurement
    run(reader.pr.setup())
    data, compensated, serialized = run(reader._read_sgp(None, False, False))
    assert data == SGP40(None, None, None)
    assert compensated is True  # comp data itself was fine - the I2C transaction is what failed
    assert serialized is False
    log = run(reader.get_error_counter())
    err_count = log["SGP40"]["ErrCount"]
    assert isinstance(err_count, int)
    assert err_count >= 1


def test_read_loop_gives_up_via_real_i2c_nak_faults_not_just_crc_mismatch() -> None:
    reader = make_reader()  # max_i2c_err=2
    fake_bus = bus(reader.sgp.i2c_sgp40.i2c_device.i2c)
    queue_successful_init(fake_bus)

    async def scenario() -> bool:
        task = asyncio.create_task(reader.read_loop())
        for _ in range(20):
            await asyncio.sleep(0)
        fake_bus.nak_addresses.add(0x59)  # sensor goes unresponsive after a successful init
        for _ in range(4):
            reader.trigger_event.set()
            for _ in range(20):
                await asyncio.sleep(0)
                if task.done():
                    return await task
        raise AssertionError("read_loop never gave up")

    with _FastAsyncSleep():
        assert run(scenario()) is False


# ---------------------------------------------------------------------------
# print_log / base_classes FRAM-backed logging - SGP40's own error log persists across a reboot,
# separate from ts_storage's own VOC-state chunk (allocated first, in construction order - see
# base_classes.py's SensorReaderConfig -> SensorReader.__init__ running before this file's own
# fram_storage.get_timestamped_chunk() call in SGP40_Reader.__init__).
# ---------------------------------------------------------------------------


def test_reader_with_fram_storage_gets_a_fram_backed_print_log() -> None:
    manager, _chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    reader = SGP40_Reader(
        make_i2c(),
        _comp_data,
        fram_storage=manager,
        fram_ntp_callback=_ntp_synced,
        max_i2c_err=2,
        cfg_path=_tmp_path("") + "/",
    )
    assert isinstance(reader.pr, PrintLogHistoryStore)


def test_sgp40_error_log_survives_a_simulated_reboot_via_fram() -> None:
    manager, _chip, spi_bus = make_fram_manager()
    run(manager.setup())

    async def scenario() -> int:
        reader = SGP40_Reader(
            make_i2c(),
            _comp_data,
            fram_storage=manager,
            fram_ntp_callback=_ntp_synced,
            max_i2c_err=2,
            cfg_path=_tmp_path("") + "/",
        )
        await reader.pr.setup()
        await reader.pr.err_s("SGP40", "simulated fault", errno=1)

        manager2 = make_fram_manager_sharing(spi_bus)
        assert await manager2.setup() is True
        reader2 = SGP40_Reader(
            make_i2c(),
            _comp_data,
            fram_storage=manager2,
            fram_ntp_callback=_ntp_synced,
            max_i2c_err=2,
            cfg_path=_tmp_path("") + "/",
        )
        await reader2.pr.setup()  # loads the persisted history back from FRAM
        log = await reader2.get_error_counter()
        err_count = log["SGP40"]["ErrCount"]
        assert isinstance(err_count, int)
        return err_count

    assert run(scenario()) == 1


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
