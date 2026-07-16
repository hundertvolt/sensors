import asyncio
import os
from collections import namedtuple

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
from print_log import PrintLogHistory

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


def test_lockablebuffer_is_still_lockable() -> None:
    buf = LockableBuffer(4)

    async def scenario() -> bool:
        locked_inside = False
        async with buf:
            locked_inside = buf.asy_lock.locked()
        return locked_inside

    assert run(scenario())


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


# ---------------------------------------------------------------------------
# SensorReader - fram=None path only (FRAM-backed PrintLogHistStore path is an
# untested backlog item pending asy_fram_manager.py's own src/ promotion)
# ---------------------------------------------------------------------------


def test_sensorreader_uses_in_memory_logging_when_fram_is_none() -> None:
    reader = SensorReader(Meas(20.0, 50), max_i2c_err=3)
    assert isinstance(reader.pr, PrintLogHistory)


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


def test_sensorreaderconfig_get_dict_cfg_reads_real_config_file() -> None:
    path_prefix = _tmp_path("") + "/"
    _remove(path_prefix + "config_temp2.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), 3, "temp2", _VAL_SI, cfg_path=path_prefix)
        result = run(reader._get_dict_cfg("Sensor", _VAL_SI))
        assert result == {"Sensor": {"SampleInterv": 2}}  # the schema's own default
    finally:
        _remove(path_prefix + "config_temp2.cfg")


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
