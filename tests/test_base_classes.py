import asyncio
import os
from collections import namedtuple

from _fram_mock import MockAsyFramManager, _MockFramChunk

import config_manager as cm
from base_classes import (
    Lockable,
    LockableBuffer,
    LockedCounter,
    LockedFlag,
    LockedValue,
    SensorReader,
    SensorReaderConfig,
)
from print_log import PrintLog, PrintLogHistory, PrintLogHistStore

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


Meas = namedtuple("Meas", ["temp", "hum"])

_TMP_DIR = "tests/_tmp"
_VAL_SI: "cm.ConfigSchema" = (("SampleInterv", "int", 2, 1, 3600, None),)


def _tmp_path(name: str) -> str:
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass  # already exists
    return _TMP_DIR + "/" + name


def _remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass  # already gone


# ---------------------------------------------------------------------------
# Lockable / LockableBuffer
# ---------------------------------------------------------------------------


def test_lockable_context_manager_acquires_and_releases() -> None:
    lock = Lockable()

    async def scenario() -> bool:
        async with lock as ctx:
            locked_inside = lock.asy_lock.locked()
            same_object = ctx is lock
        return locked_inside and same_object and not lock.asy_lock.locked()

    assert run(scenario())


def test_lockable_accepts_a_preexisting_lock() -> None:
    shared = asyncio.Lock()
    lock = Lockable(shared)
    assert lock.asy_lock is shared


def test_lockable_aexit_swallows_already_released_lock() -> None:
    lock = Lockable()

    async def scenario() -> None:
        async with lock:
            lock.asy_lock.release()  # released early, out from under the context manager

    run(scenario())  # must not raise despite the double release
    assert not lock.asy_lock.locked()


def test_lockable_aexit_never_suppresses_the_real_exception() -> None:
    lock = Lockable()

    async def scenario() -> None:
        async with lock:
            raise ValueError("boom")

    try:
        run(scenario())
        raised = False
    except ValueError:
        raised = True
    assert raised
    assert not lock.asy_lock.locked()  # still released despite the exception


def test_lockable_serializes_concurrent_access() -> None:
    lock = Lockable()
    max_concurrent = 0
    current = 0

    async def critical_section() -> None:
        nonlocal max_concurrent, current
        async with lock:
            current += 1
            max_concurrent = max(max_concurrent, current)
            await asyncio.sleep(0)
            current -= 1

    async def scenario() -> None:
        await asyncio.gather(*(critical_section() for _ in range(5)))

    run(scenario())
    assert max_concurrent == 1


def test_lockablebuffer_default_data_length_spans_remainder() -> None:
    buf = LockableBuffer(10, data_start=2)
    raw = buf.get_buf()
    data = buf.get_data_buf()
    assert raw is not None
    assert data is not None
    assert len(raw) == 10
    assert len(data) == 8  # 10 - 2


def test_lockablebuffer_explicit_data_length_and_offset() -> None:
    buf = LockableBuffer(10, data_start=2, data_length=3)
    raw = buf.get_buf()
    data = buf.get_data_buf()
    assert raw is not None
    assert data is not None
    assert len(data) == 3
    raw[2:5] = b"\x01\x02\x03"
    assert bytes(data) == b"\x01\x02\x03"


def test_lockablebuffer_oversized_region_yields_none() -> None:
    buf = LockableBuffer(4, data_start=2, data_length=10)  # data_end (12) > size (4)
    assert buf.get_buf() is None
    assert buf.get_data_buf() is None


def test_lockablebuffer_negative_size_yields_none() -> None:
    buf = LockableBuffer(-1)  # bytearray(-1) would raise MemoryError on real MicroPython if unguarded
    assert buf.get_buf() is None
    assert buf.get_data_buf() is None


def test_lockablebuffer_negative_data_start_yields_none() -> None:
    buf = LockableBuffer(10, data_start=-3)  # would otherwise silently wrap to a wrong-offset slice
    assert buf.get_buf() is None
    assert buf.get_data_buf() is None


def test_lockablebuffer_negative_data_length_yields_none() -> None:
    buf = LockableBuffer(10, data_start=2, data_length=-5)  # data_end (-3) doesn't trip data_end > size alone
    assert buf.get_buf() is None
    assert buf.get_data_buf() is None


def test_lockablebuffer_huge_size_yields_none_not_memoryerror() -> None:
    # A valid, non-negative size can still exhaust the heap - confirmed directly against the real
    # MicroPython interpreter that bytearray(2**62) raises MemoryError, not a negative-input error.
    buf = LockableBuffer(2**62)
    assert buf.get_buf() is None
    assert buf.get_data_buf() is None


def test_lockablebuffer_astronomical_size_yields_none_not_overflowerror() -> None:
    # A second, distinct failure mode above the first: confirmed directly that bytearray(n) raises
    # OverflowError instead of MemoryError once n hits the signed-64-bit machine-word boundary
    # (2**63) - both must degrade the same way, not just the smaller-magnitude one.
    buf = LockableBuffer(2**63)
    assert buf.get_buf() is None
    assert buf.get_data_buf() is None


def test_lockablebuffer_zero_length_data_region_is_valid() -> None:
    # data_start == size is a legitimate boundary, not an oversized region: data_length defaults to
    # 0, so data_end (== size) is not > size.
    buf = LockableBuffer(4, data_start=4)
    raw = buf.get_buf()
    data = buf.get_data_buf()
    assert raw is not None
    assert len(raw) == 4
    assert data is not None
    assert len(data) == 0


def test_lockablebuffer_is_still_lockable() -> None:
    buf = LockableBuffer(4)

    async def scenario() -> bool:
        locked_inside = False
        async with buf:
            locked_inside = buf.asy_lock.locked()
        return locked_inside

    assert run(scenario())


def test_lockablebuffer_is_a_lockable_instance() -> None:
    assert isinstance(LockableBuffer(4), Lockable)


# ---------------------------------------------------------------------------
# LockedCounter / LockedFlag / LockedValue
# ---------------------------------------------------------------------------


def test_lockedcounter_defaults() -> None:
    counter = LockedCounter()
    assert run(counter.get_value()) == 0
    assert counter.max_val == 0xFF


def test_lockedcounter_increment_saturates_at_max() -> None:
    counter = LockedCounter(init_value=0, max_val=2)
    assert run(counter.increment()) == 1
    assert run(counter.increment()) == 2
    assert run(counter.increment()) == 2  # saturated, does not wrap


def test_lockedcounter_decrement_floors_at_zero() -> None:
    counter = LockedCounter(init_value=1, max_val=5)
    assert run(counter.decrement()) == 0
    assert run(counter.decrement()) == 0  # floored, does not go negative


def test_lockedcounter_set_value_clamps_to_max() -> None:
    counter = LockedCounter(max_val=10)
    run(counter.set_value(999))
    assert run(counter.get_value()) == 10
    run(counter.set_value(3))
    assert run(counter.get_value()) == 3


def test_lockedcounter_set_value_clamps_negative_to_zero() -> None:
    counter = LockedCounter(max_val=10)
    run(counter.set_value(-7))
    assert run(counter.get_value()) == 0


def test_lockedcounter_init_value_is_clamped_same_as_set_value() -> None:
    counter = LockedCounter(init_value=999, max_val=10)
    assert run(counter.get_value()) == 10
    counter = LockedCounter(init_value=-7, max_val=10)
    assert run(counter.get_value()) == 0


def test_lockedcounter_none_is_a_distinct_never_happened_sentinel() -> None:
    counter = LockedCounter(init_value=None, max_val=10)
    assert run(counter.get_value()) is None
    run(counter.set_value(None))
    assert run(counter.get_value()) is None


def test_lockedcounter_increment_from_none_starts_at_one() -> None:
    counter = LockedCounter(init_value=None, max_val=10)
    assert run(counter.increment()) == 1


def test_lockedcounter_decrement_from_none_stays_at_zero() -> None:
    counter = LockedCounter(init_value=None, max_val=10)
    assert run(counter.decrement()) == 0


def test_lockedcounter_max_val_zero_stays_clamped_to_zero() -> None:
    # An unusual but typed-valid config: a counter that can never hold a nonzero value.
    counter = LockedCounter(init_value=5, max_val=0)
    assert run(counter.get_value()) == 0
    assert run(counter.increment()) == 0
    assert run(counter.decrement()) == 0


def test_lockedcounter_concurrent_increments_are_not_lost() -> None:
    counter = LockedCounter(init_value=0, max_val=1000)

    async def scenario() -> None:
        await asyncio.gather(*(counter.increment() for _ in range(50)))

    run(scenario())
    assert run(counter.get_value()) == 50


def test_lockedflag_transitions() -> None:
    flag = LockedFlag()
    assert run(flag.get_value()) is False
    run(flag.set_true())
    assert run(flag.get_value()) is True
    run(flag.set_false())
    assert run(flag.get_value()) is False


def test_lockedflag_init_value() -> None:
    flag = LockedFlag(init_value=True)
    assert run(flag.get_value()) is True


def test_lockedvalue_roundtrip_int_and_float() -> None:
    value = LockedValue(0)
    run(value.set_value(42))
    assert run(value.get_value()) == 42
    run(value.set_value(3.5))
    assert run(value.get_value()) == 3.5


def test_lockedvalue_roundtrip_inf_and_nan() -> None:
    # Unusual but typed-valid float content: LockedValue does no range clamping (unlike
    # LockedCounter), so these must simply round-trip untouched.
    value = LockedValue(0.0)
    run(value.set_value(float("inf")))
    assert run(value.get_value()) == float("inf")
    run(value.set_value(float("nan")))
    assert run(value.get_value()) != run(value.get_value())  # nan != nan is the only valid check


# ---------------------------------------------------------------------------
# SensorReader - fram=None (in-memory logging) path
# ---------------------------------------------------------------------------


def test_sensorreader_uses_in_memory_logging_when_fram_is_none() -> None:
    reader = SensorReader(Meas(20.0, 50), max_i2c_err=3)
    assert isinstance(reader.pr, PrintLogHistory)


def test_sensorreader_debug_level_is_forwarded_to_the_logger() -> None:
    reader = SensorReader(Meas(20.0, 50), max_i2c_err=3, debug=PrintLog.level_err())
    assert reader.pr.get_level() == PrintLog.level_err()


def test_sensorreader_debug_none_leaves_logger_at_off() -> None:
    reader = SensorReader(Meas(20.0, 50), max_i2c_err=3, debug=None)
    assert reader.pr.get_level() == PrintLog.level_off()


def test_sensorreader_history_length_zero_is_forwarded_and_never_raises() -> None:
    reader = SensorReader(Meas(None, 50), max_i2c_err=3, history_length=0)
    assert run(reader._error_check(Meas(None, 50), "temp")) is True
    assert reader.pr.err_count == 1
    assert list(reader.pr.history) == []  # nothing to hold, but the count still tracked


def test_error_check_max_i2c_err_zero_gives_up_on_first_failure() -> None:
    # Zero tolerance is a legitimate, if unusual, config value - not a caller mistake to guard
    # against like a negative max_i2c_err would be (see BACKLOG.md's structural-pass note).
    reader = SensorReader(Meas(None, 50), max_i2c_err=0)
    assert run(reader._error_check(Meas(None, 50), "temp")) is False


def test_get_dict_cfg_duplicate_schema_names_collapse_to_one_key() -> None:
    # schema_names() documents "duplicates preserved" - _get_dict_cfg's own dict comprehension must
    # still behave sanely (last write wins, no raise) rather than assuming names are unique.
    dup_schema: cm.ConfigSchema = (
        ("SampleInterv", "int", 2, 1, 3600, None),
        ("SampleInterv", "int", 9, 1, 3600, None),
    )
    reader = SensorReader(Meas(20.0, 50), max_i2c_err=3)
    result = run(reader._get_dict_cfg("Sensor", dup_schema))
    assert result == {"Sensor": {"SampleInterv": None}}


def test_sensorreader_meas_data_roundtrip() -> None:
    reader = SensorReader(Meas(20.0, 50), max_i2c_err=3)
    assert run(reader._get_meas_data()) == Meas(20.0, 50)
    run(reader._set_meas_data(Meas(21.0, 60)))
    assert run(reader._get_meas_data()) == Meas(21.0, 60)


def test_sensorreader_reset_error_counter_clears_history() -> None:
    reader = SensorReader(Meas(20.0, 50), max_i2c_err=3)
    run(reader.pr.setup())
    run(reader.pr.err_s("boom", errno=1))
    assert reader.pr.err_count == 1
    run(reader.reset_error_counter())
    assert reader.pr.err_count == 0


def test_error_check_no_failure_keeps_going_and_decays_counter() -> None:
    reader = SensorReader(Meas(20.0, 50), max_i2c_err=2)
    reader._err_cnt_internal = 1
    assert run(reader._error_check(Meas(20.0, 50), "temp")) is True
    assert reader._err_cnt_internal == 0  # decayed back down since this call had no failure


def test_error_check_failure_increments_until_giving_up() -> None:
    reader = SensorReader(Meas(None, 50), max_i2c_err=2)
    assert run(reader._error_check(Meas(None, 50), "temp")) is True  # 1 <= max
    assert run(reader._error_check(Meas(None, 50), "temp")) is True  # 2 <= max
    assert run(reader._error_check(Meas(None, 50), "temp")) is False  # 3 > max - give up


def test_error_check_condition_false_ignores_none_results() -> None:
    reader = SensorReader(Meas(None, 50), max_i2c_err=0)
    assert run(reader._error_check(Meas(None, 50), "temp", condition=False)) is True
    assert reader._err_cnt_internal == 0


def test_get_dict_cfg_default_returns_all_none() -> None:
    reader = SensorReader(Meas(20.0, 50), max_i2c_err=3)
    result = run(reader._get_dict_cfg("Sensor", _VAL_SI))
    assert result == {"Sensor": {"SampleInterv": None}}


def test_get_dict_cfg_merges_callback_result() -> None:
    reader = SensorReader(Meas(20.0, 50), max_i2c_err=3)

    async def callback() -> "dict[str, int | float | str | None]":
        return {"SampleInterv": 5}

    result = run(reader._get_dict_cfg("Sensor", _VAL_SI, callback=callback))
    assert result == {"Sensor": {"SampleInterv": 5}}


def test_get_dict_cfg_callback_exception_is_caught() -> None:
    reader = SensorReader(Meas(20.0, 50), max_i2c_err=3)

    async def bad_callback() -> "dict[str, int | float | str | None]":
        raise RuntimeError("sensor read failed")

    result = run(reader._get_dict_cfg("Sensor", _VAL_SI, callback=bad_callback))
    assert result == {"Sensor": {"SampleInterv": None}}  # falls back to defaults, doesn't raise


def test_get_dict_cfg_callback_extra_key_is_still_merged() -> None:
    reader = SensorReader(Meas(20.0, 50), max_i2c_err=3)

    async def callback() -> "dict[str, int | float | str | None]":
        return {"SampleInterv": 5, "Unexpected": 1}

    result = run(reader._get_dict_cfg("Sensor", _VAL_SI, callback=callback))
    assert result == {"Sensor": {"SampleInterv": 5, "Unexpected": 1}}


def test_get_dict_cfg_mgr_cfg_update_exception_is_caught() -> None:
    # _get_mgr_cfg is an override point (dict[...] | None per its type contract, but that's not
    # statically enforced on a runtime-misbehaving subclass) - a value that isn't actually
    # dict-like must not let ret[name].update(sensor_conf) raise out of _get_dict_cfg.
    class BadMgrCfgReader(SensorReader):
        async def _get_mgr_cfg(self, cfg: "list[str]") -> "dict[str, int | float | str | None] | None":
            return 42  # type: ignore[return-value]

    reader = BadMgrCfgReader(Meas(20.0, 50), max_i2c_err=3)
    result = run(reader._get_dict_cfg("Sensor", _VAL_SI))
    assert result == {"Sensor": {"SampleInterv": None}}  # update(42) raised TypeError - falls back to all-None


# ---------------------------------------------------------------------------
# SensorReader - fram given (FRAM-backed PrintLogHistStore logging), using the
# same tests/_fram_mock.py boundary print_log.py's own tests use. Integration
# coverage across base_classes.py + print_log.py + the FRAM mock together.
# ---------------------------------------------------------------------------


def test_sensorreader_uses_fram_backed_logging_when_fram_is_given() -> None:
    reader = SensorReader(Meas(20.0, 50), max_i2c_err=3, fram=MockAsyFramManager())
    assert isinstance(reader.pr, PrintLogHistStore)


def test_sensorreader_fram_backed_error_check_persists_and_survives_reboot() -> None:
    manager = MockAsyFramManager()
    reader = SensorReader(Meas(None, 50), max_i2c_err=5, fram=manager)
    run(reader.pr.setup())
    assert run(reader._error_check(Meas(None, 50), "temp")) is True
    assert run(reader._error_check(Meas(None, 50), "temp")) is True
    assert reader.pr.err_count == 2

    # Simulate a reboot: a fresh SensorReader/manager pair sharing the same backing bytes, same
    # as print_log.py's own test_printloghiststore_err_s_persists_and_survives_a_simulated_reboot.
    rebooted = SensorReader(Meas(None, 50), max_i2c_err=5, fram=MockAsyFramManager(backing=manager.backing))
    run(rebooted.pr.setup())
    assert rebooted.pr.err_count == 2


def test_sensorreader_fram_backed_error_check_without_setup_never_raises() -> None:
    # Real drivers call `await self.pr.setup()` themselves as part of their own async init (e.g.
    # asy_bmp3xx_driver.py's _init_bmp) - SensorReader.__init__ can't do this itself since it's
    # sync. Skipping setup() must degrade cleanly (in-memory count/history still update per
    # print_log.py's own contract; only the FRAM write is skipped), never raise.
    reader = SensorReader(Meas(None, 50), max_i2c_err=5, fram=MockAsyFramManager())
    assert reader.pr.initialized is False
    assert run(reader._error_check(Meas(None, 50), "temp")) is True
    assert reader.pr.err_count == 1


def test_sensorreader_fram_allocation_failure_still_logs_in_memory_without_raising() -> None:
    reader = SensorReader(Meas(None, 50), max_i2c_err=5, fram=MockAsyFramManager(out_of_memory=True))
    assert isinstance(reader.pr, PrintLogHistStore)
    assert reader.pr.fram is None
    run(reader.pr.setup())  # no-op: nothing allocated, must not raise
    assert run(reader._error_check(Meas(None, 50), "temp")) is True
    assert reader.pr.err_count == 1  # in-memory count still tracked despite FRAM being unavailable


# ---------------------------------------------------------------------------
# SensorReader - every simulated FRAM failure mode (tests/_fram_mock.py's fault injection),
# driven through SensorReader's own API (_error_check/reset_error_counter/setup) rather than
# print_log.py's methods directly - test_print_log.py already covers each mode exhaustively at
# that level; this confirms the same fault matrix still degrades cleanly through this file's wiring.
# ---------------------------------------------------------------------------


def test_sensorreader_fram_raise_on_get_chunk_never_raises_at_construction() -> None:
    reader = SensorReader(Meas(None, 50), max_i2c_err=5, fram=MockAsyFramManager(raise_on_get_chunk=True))
    assert isinstance(reader.pr, PrintLogHistStore)
    assert reader.pr.fram is None
    assert run(reader._error_check(Meas(None, 50), "temp")) is True
    assert reader.pr.err_count == 1


def test_sensorreader_fram_get_buffer_raising_is_caught_during_error_check() -> None:
    reader = SensorReader(Meas(None, 50), max_i2c_err=5, fram=MockAsyFramManager())
    assert isinstance(reader.pr, PrintLogHistStore)  # narrows reader.pr's type so .fram is visible
    assert isinstance(reader.pr.fram, _MockFramChunk)  # whitebox: narrows further to reach the mock's fault flags
    run(reader.pr.setup())
    reader.pr.fram.raise_on_get_buffer = True
    assert run(reader._error_check(Meas(None, 50), "temp")) is True
    assert reader.pr.err_count == 1  # FRAM write failed silently; in-memory count still tracked


def test_sensorreader_fram_broken_buffer_is_caught_during_error_check() -> None:
    reader = SensorReader(Meas(None, 50), max_i2c_err=5, fram=MockAsyFramManager())
    assert isinstance(reader.pr, PrintLogHistStore)
    assert isinstance(reader.pr.fram, _MockFramChunk)
    run(reader.pr.setup())
    reader.pr.fram.broken_buffer = True
    assert run(reader._error_check(Meas(None, 50), "temp")) is True
    assert reader.pr.err_count == 1


def test_sensorreader_fram_raise_on_write_is_caught_during_error_check() -> None:
    reader = SensorReader(Meas(None, 50), max_i2c_err=5, fram=MockAsyFramManager())
    assert isinstance(reader.pr, PrintLogHistStore)
    assert isinstance(reader.pr.fram, _MockFramChunk)
    run(reader.pr.setup())
    reader.pr.fram.raise_on_write = True
    assert run(reader._error_check(Meas(None, 50), "temp")) is True
    assert reader.pr.err_count == 1


def test_sensorreader_fram_write_returns_false_is_surfaced_during_error_check() -> None:
    reader = SensorReader(Meas(None, 50), max_i2c_err=5, fram=MockAsyFramManager())
    assert isinstance(reader.pr, PrintLogHistStore)
    assert isinstance(reader.pr.fram, _MockFramChunk)
    run(reader.pr.setup())
    reader.pr.fram.write_returns_false = True
    assert run(reader._error_check(Meas(None, 50), "temp")) is True
    assert reader.pr.err_count == 1


def test_sensorreader_fram_raise_on_read_falls_back_to_write_during_setup() -> None:
    reader = SensorReader(Meas(None, 50), max_i2c_err=5, fram=MockAsyFramManager())
    assert isinstance(reader.pr, PrintLogHistStore)
    assert isinstance(reader.pr.fram, _MockFramChunk)
    reader.pr.fram.raise_on_read = True
    run(reader.pr.setup())  # first-time setup: _read() fails, falls back to _write() succeeding
    assert reader.pr.initialized is True


def test_sensorreader_fram_setup_fails_cleanly_when_both_read_and_write_fail() -> None:
    reader = SensorReader(Meas(None, 50), max_i2c_err=5, fram=MockAsyFramManager())
    assert isinstance(reader.pr, PrintLogHistStore)
    assert isinstance(reader.pr.fram, _MockFramChunk)
    reader.pr.fram.read_returns_false = True
    reader.pr.fram.write_returns_false = True
    run(reader.pr.setup())
    assert reader.pr.initialized is False
    assert run(reader._error_check(Meas(None, 50), "temp")) is True  # still tracks in-memory
    assert reader.pr.err_count == 1


# ---------------------------------------------------------------------------
# SensorReaderConfig - real ConfigManager/file I/O, no mocking
# ---------------------------------------------------------------------------


def test_sensorreaderconfig_wires_a_real_configmanager() -> None:
    path_prefix = _tmp_path("") + "/"
    _remove(path_prefix + "config_temp.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), 3, "temp", _VAL_SI, cfg_path=path_prefix)
        assert reader.cfgmgr.config_file == path_prefix + "config_temp.cfg"
        assert reader.cfgmgr.valid is True
    finally:
        _remove(path_prefix + "config_temp.cfg")


def test_sensorreaderconfig_is_a_sensorreader_with_a_real_mgr_cfg_override() -> None:
    # Inheritance-level check: SensorReaderConfig IS-A SensorReader, and _get_mgr_cfg's override
    # actually replaces the base class's always-{} stub rather than just adding cfgmgr alongside it.
    path_prefix = _tmp_path("") + "/"
    _remove(path_prefix + "config_isa.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), 3, "isa", _VAL_SI, cfg_path=path_prefix)
        assert isinstance(reader, SensorReader)
        assert run(reader._get_mgr_cfg(["SampleInterv"])) == {"SampleInterv": 2}
    finally:
        _remove(path_prefix + "config_isa.cfg")


def test_sensorreaderconfig_shares_the_same_logger_instance_with_its_configmanager() -> None:
    # Cross-dependency check: SensorReaderConfig.__init__ passes self.pr into ConfigManager - it must
    # be the exact same object, not an equal-but-separate one, or sensor errors and config
    # errors/warnings would silently split across two independent histories.
    path_prefix = _tmp_path("") + "/"
    _remove(path_prefix + "config_shared.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), 3, "shared", _VAL_SI, cfg_path=path_prefix)
        assert reader.cfgmgr.pr is reader.pr
    finally:
        _remove(path_prefix + "config_shared.cfg")


def test_sensorreaderconfig_get_dict_cfg_reads_real_config_file() -> None:
    path_prefix = _tmp_path("") + "/"
    _remove(path_prefix + "config_temp2.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), 3, "temp2", _VAL_SI, cfg_path=path_prefix)
        result = run(reader._get_dict_cfg("Sensor", _VAL_SI))
        assert result == {"Sensor": {"SampleInterv": 2}}  # the schema's own default
    finally:
        _remove(path_prefix + "config_temp2.cfg")


def test_sensorreaderconfig_malformed_schema_propagates_none_through_get_dict_cfg() -> None:
    # An empty default_vals schema makes ConfigManager itself invalid (see config_manager.py's
    # own "Defaults are empty" check) - confirms that invalidity propagates cleanly all the way up
    # through SensorReaderConfig's own public surface, not just when calling ConfigManager directly.
    path_prefix = _tmp_path("") + "/"
    _remove(path_prefix + "config_badschema.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), 3, "badschema", (), cfg_path=path_prefix)
        assert reader.cfgmgr.valid is False
        result = run(reader._get_dict_cfg("Sensor", ()))
        assert result == {"Sensor": {}}
    finally:
        _remove(path_prefix + "config_badschema.cfg")


# ---------------------------------------------------------------------------
# SensorReaderConfig - integration across all three files at once: real
# ConfigManager file I/O (config_manager.py), FRAM-backed logging via the
# tests/_fram_mock.py boundary (print_log.py), and base_classes.py's own
# wiring between the two.
# ---------------------------------------------------------------------------


def test_sensorreaderconfig_fram_backed_logging_with_real_config_file() -> None:
    path_prefix = _tmp_path("") + "/"
    _remove(path_prefix + "config_fram1.cfg")
    try:
        reader = SensorReaderConfig(
            Meas(20.0, 50), 3, "fram1", _VAL_SI, cfg_path=path_prefix, fram=MockAsyFramManager()
        )
        assert isinstance(reader.pr, PrintLogHistStore)
        assert reader.cfgmgr.valid is True
        result = run(reader._get_dict_cfg("Sensor", _VAL_SI))
        assert result == {"Sensor": {"SampleInterv": 2}}
    finally:
        _remove(path_prefix + "config_fram1.cfg")


def test_sensorreaderconfig_malformed_config_file_repairs_cleanly_with_fram_backed_logger() -> None:
    # ConfigManager logs repair warnings via the plain (non-persisting) pr.wrn()/pr.err(), never
    # wrn_s()/err_s() - confirms a FRAM-backed logger's transient methods work under a real repair
    # path without raising, and that nothing is persisted to FRAM by this (err_count stays 0).
    path_prefix = _tmp_path("") + "/"
    path = path_prefix + "config_fram2.cfg"
    _remove(path)
    with open(path, "w") as f:
        f.write("{not valid json")
    try:
        reader = SensorReaderConfig(
            Meas(20.0, 50), 3, "fram2", _VAL_SI, cfg_path=path_prefix, fram=MockAsyFramManager()
        )
        assert reader.cfgmgr.valid is True  # malformed file was repaired, not left invalid
        assert reader.pr.err_count == 0  # repair warnings use pr.wrn()/pr.err(), never the _s() persisting variants
        result = run(reader._get_dict_cfg("Sensor", _VAL_SI))
        assert result == {"Sensor": {"SampleInterv": 2}}
    finally:
        _remove(path)


def test_sensorreaderconfig_fram_allocation_failure_and_missing_config_file_together() -> None:
    # Two independent subsystems degrading at once: FRAM allocation fails (pr.fram stays None) while
    # the config file doesn't exist yet either (gets created with defaults) - neither failure may
    # raise, nor may one derail the other.
    path_prefix = _tmp_path("") + "/"
    _remove(path_prefix + "config_fram3.cfg")
    try:
        reader = SensorReaderConfig(
            Meas(20.0, 50),
            3,
            "fram3",
            _VAL_SI,
            cfg_path=path_prefix,
            fram=MockAsyFramManager(out_of_memory=True),
        )
        assert isinstance(reader.pr, PrintLogHistStore)
        assert reader.pr.fram is None
        assert reader.cfgmgr.valid is True
        result = run(reader._get_dict_cfg("Sensor", _VAL_SI))
        assert result == {"Sensor": {"SampleInterv": 2}}
    finally:
        _remove(path_prefix + "config_fram3.cfg")


def test_sensorreaderconfig_write_config_is_reflected_by_get_dict_cfg() -> None:
    # Closes the loop on the read-only integration tests above: a write through the wired
    # ConfigManager (config_manager.py) must be visible through SensorReaderConfig's own public
    # surface (base_classes.py), with no error logged through the real PrintLogHistory (print_log.py).
    path_prefix = _tmp_path("") + "/"
    _remove(path_prefix + "config_writeback.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), 3, "writeback", _VAL_SI, cfg_path=path_prefix)
        ok, results = run(reader.cfgmgr.write_config({"SampleInterv": 42}, _VAL_SI))
        assert ok is True
        assert results == {"SampleInterv": "Valid"}
        assert reader.pr.err_count == 0
        result = run(reader._get_dict_cfg("Sensor", _VAL_SI))
        assert result == {"Sensor": {"SampleInterv": 42}}
    finally:
        _remove(path_prefix + "config_writeback.cfg")


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
