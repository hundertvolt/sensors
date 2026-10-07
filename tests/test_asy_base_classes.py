import asyncio
import json
import os
import time
from collections import namedtuple

import machine
from _error_codes import code
from _fram_chip_fake import FakeMB85RS64V
from _tmp_scratch import TmpScratch
from _write_counters import WriteCountingOpen

import asy_base_classes
import asy_config_manager
import asy_print_log
import asy_spi_driver
from asy_base_classes import (
    COUNTER_CAP,
    Lockable,
    LockableBuffer,
    LockedCounter,
    LockedFlag,
    LockedValue,
    SensorReader,
    SensorReaderConfig,
    TickSeconds,
    arm_tick_timer,
    set_utc_valid,
    utc_now,
)
from asy_config_manager import schema_dict
from asy_fram_manager import FRAMManager
from asy_print_log import LogConfig, PrintLogHistory, PrintLogHistoryStore
from asy_spi_driver import SPI

# Same one-process-per-test-file swap as test_asy_fram_driver.py/test_asy_fram_manager.py.
asy_spi_driver._SPI = FakeMB85RS64V  # type: ignore[misc]

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    import asy_config_manager as cm
    from asy_base_classes import JsonMapping
    from asy_base_classes import LockableBuffer as _LockableBufferType
    from asy_crc_checks import CRCBase

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


def make_fram_manager(max_size: int = 0x2000) -> "tuple[FRAMManager, FakeMB85RS64V]":
    bus = SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    manager = FRAMManager(bus, 1, max_size=max_size)
    chip = manager.fram._spidev.spi._spi
    assert isinstance(chip, FakeMB85RS64V)
    return manager, chip


class _RaisingFramChunk:
    # Fails only by allocation, the one failure the real chunk documents (SPECIFICATION.md C.7), mirroring
    # tests/test_asy_print_log.py's: SensorReader's FRAM-backed path degrades to RAM-only on it.
    def __init__(self, *, raise_on_write: bool = False, raise_on_read: bool = False) -> None:
        self.raise_on_write = raise_on_write
        self.raise_on_read = raise_on_read

    # Every parameter below keeps its exact name (and stays unused): both doubles implement asy_print_log.py's
    # _FramChunk/_FramManager Protocols, which mypy matches structurally by parameter name, and asy_print_log.py
    # calls get_chunk(size, crc=CRC8()) by keyword on top of that.
    def get_buffer(self) -> "_LockableBufferType":
        from asy_base_classes import LockableBuffer as _LB

        return _LB(6, data_start=0, data_length=6)

    async def write_into(self, buf: "_LockableBufferType", *, override_pause: bool = False) -> bool:
        if self.raise_on_write:
            raise MemoryError("simulated allocation failure")
        return True

    async def read_into(self, buf: "_LockableBufferType", *, override_pause: bool = False) -> bool:
        if self.raise_on_read:
            raise MemoryError("simulated allocation failure")
        return True


class _RaisingFramManager:
    def __init__(self, chunk: "_RaisingFramChunk | None", *, raise_on_get_chunk: bool = False) -> None:
        self._chunk = chunk
        self.raise_on_get_chunk = raise_on_get_chunk

    # Every parameter below keeps its exact name (and stays unused): both doubles implement asy_print_log.py's
    # _FramChunk/_FramManager Protocols, which mypy matches structurally by parameter name, and asy_print_log.py
    # calls get_chunk(size, crc=CRC8()) by keyword on top of that.
    def get_chunk(
        self, size: int, crc: "CRCBase | None" = None, verify: int = 0, check_length: int = 8,
    ) -> "_RaisingFramChunk | None":
        if self.raise_on_get_chunk:
            raise MemoryError("simulated allocation failure")
        return self._chunk


Meas = namedtuple("Meas", ["temp", "hum"])

# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that module's
# own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage. Every test
# below writes its own uniquely-named config file, so they can safely share this one directory.
_scratch = TmpScratch("asy_base_classes")
_SHARED_CFG_DIR = _scratch.dir()
_VAL_SI: "cm.ConfigSchema" = (("SampleInterval", "int", 2, 1, 3600, None),)
_VAL_BOOL: "cm.ConfigSchema" = (("SelfCal", "bool", False, None, None, None),)
_VAL_SPECIAL: "cm.ConfigSchema" = (("Trigger", "bool", None, None, None, True),)  # special-alone, mirrors asy_sgp40_driver.py's ResetVOC


async def _put_flushed(reader: "SensorReaderConfig", data: "dict[str, int | float | str | bool | None]") -> "cm.WriteValidity":
    # One PUT and the flush it released, in one coroutine: deferred work never outlives a run() call.
    results = await reader._set_dict_cfg(data, reader.get_cfg_schema())
    await reader.cfgmgr.flush_pending()
    return results


async def _write_flushed(mgr: "cm.ConfigManager", data: "dict[str, int | float | str | bool | None]") -> "tuple[bool, cm.WriteValidity]":
    # One write and its flush in one coroutine: deferred work never outlives a run() call.
    result = await mgr.write_config(data)
    await mgr.flush_pending()
    return result


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
            locked_inside = lock.session_lock.locked()
            same_object = ctx is lock
        return locked_inside and same_object and not lock.session_lock.locked()

    assert run(scenario())


def test_lockable_accepts_a_preexisting_lock() -> None:
    shared = asyncio.Lock()
    lock = Lockable(shared)
    assert lock.session_lock is shared


def test_lockable_aexit_swallows_already_released_lock() -> None:
    lock = Lockable()

    async def scenario() -> None:
        async with lock:
            lock.session_lock.release()  # released early, out from under the context manager

    run(scenario())  # must not raise despite the double release
    assert not lock.session_lock.locked()


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
    assert not lock.session_lock.locked()  # still released despite the exception


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

    async def scenario() -> None:
        async with buf:
            assert buf.session_lock.locked()  # held for the whole block, same as a plain Lockable

    run(scenario())


def test_lockablebuffer_is_a_lockable_instance() -> None:
    assert isinstance(LockableBuffer(4), Lockable)


# ---------------------------------------------------------------------------
# LockedCounter / LockedFlag / LockedValue
# ---------------------------------------------------------------------------


def test_lockedcounter_defaults() -> None:
    counter = LockedCounter()
    assert run(counter.get_value()) == 0
    assert counter._max_val == COUNTER_CAP


def test_a_max_val_above_the_cap_is_clamped_to_it() -> None:
    assert COUNTER_CAP == 2**30 - 1
    assert LockedCounter(max_val=COUNTER_CAP + 5)._max_val == COUNTER_CAP


def test_increment_near_the_cap_stays_there() -> None:
    counter = LockedCounter(init_value=COUNTER_CAP - 1)
    assert run(counter.increment()) == COUNTER_CAP
    assert run(counter.increment()) == COUNTER_CAP  # checked before the step: no intermediate above the cap


def test_the_shared_scalars_hold_no_lock() -> None:
    # No method awaits, so no other task runs between a read and its write: the lock attribute is gone.
    for scalar in (LockedCounter(), LockedFlag(), LockedValue(init_value=None)):
        assert not hasattr(scalar, "value_lock")
        assert not hasattr(scalar, "_value_lock")


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


def test_lockedcounter_negative_max_val_is_clamped_to_zero_at_construction() -> None:
    # A negative max_val is a dev-time-typo risk, never a runtime-computed value. Clamped to 0 in __init__
    # so the counter's [0, max_val] invariant holds throughout: without it, _clamp's min(max(value, 0),
    # max_val) would collapse every value to the negative max_val.
    counter = LockedCounter(init_value=3, max_val=-5)
    assert counter._max_val == 0
    assert run(counter.get_value()) == 0
    assert run(counter.increment()) == 0
    assert run(counter.decrement()) == 0
    run(counter.set_value(-7))
    assert run(counter.get_value()) == 0


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
    value = LockedValue(init_value=0)
    run(value.set_value(42))
    assert run(value.get_value()) == 42
    run(value.set_value(3.5))
    assert run(value.get_value()) == 3.5


def test_lockedvalue_roundtrip_inf_and_nan() -> None:
    # Unusual but typed-valid float content: LockedValue does no range clamping (unlike
    # LockedCounter), so these must simply round-trip untouched.
    value = LockedValue(init_value=0.0)
    run(value.set_value(float("inf")))
    assert run(value.get_value()) == float("inf")
    run(value.set_value(float("nan")))
    assert run(value.get_value()) != run(value.get_value())  # nan != nan is the only valid check


def test_lockedvalue_round_trips_none_and_a_32_bit_value() -> None:
    value = LockedValue(init_value=None)
    assert run(value.get_value()) is None
    run(value.set_value(0xFFFFFFFF))  # a boot signature: an identifier, never stepped, never clamped
    assert run(value.get_value()) == 0xFFFFFFFF
    run(value.set_value(None))
    assert run(value.get_value()) is None


# ---------------------------------------------------------------------------
# TickSeconds / arm_tick_timer / utc_now
# ---------------------------------------------------------------------------

_TICKS_PERIOD = 2**30  # rp2's ticks_ms() period (TICKS_PERIOD in extmod/modtime.c)


class _FakeTicks:
    # Stands in for asy_base_classes.time: a settable millisecond clock wrapping at 2**30, with
    # ticks_diff()'s signed modular arithmetic, plus a settable wall clock for utc_now().
    def __init__(self, start_ms: int = 0) -> None:
        self.now_ms = start_ms
        self.wall_s = 1_790_000_000

    def advance(self, ms: int) -> None:
        self.now_ms += ms

    def ticks_ms(self) -> int:
        return self.now_ms % _TICKS_PERIOD

    def ticks_add(self, ticks: int, delta: int) -> int:
        return (ticks + delta) % _TICKS_PERIOD

    def ticks_diff(self, new: int, old: int) -> int:
        half = _TICKS_PERIOD // 2
        return ((new - old + half) % _TICKS_PERIOD) - half

    def gmtime(self, secs: "int | None" = None) -> "tuple[int, ...]":
        return (self.wall_s, 0, 0, 0, 0, 0, 0, 0) if secs is None else (secs, 0, 0, 0, 0, 0, 0, 0)

    def mktime(self, t: "tuple[int, ...]") -> int:
        return t[0]


def _with_fake_ticks(start_ms: int = 0) -> "_FakeTicks":
    fake = _FakeTicks(start_ms)
    asy_base_classes.time = fake  # type: ignore[assignment]
    return fake


def _restore_time() -> None:
    asy_base_classes.time = time


def test_tickseconds_counts_up_in_whole_seconds_keeping_the_remainder() -> None:
    fake = _with_fake_ticks()
    try:
        ticks = TickSeconds()
        fake.advance(999)
        assert ticks.read() == 0
        fake.advance(1)
        assert ticks.read() == 1
        for _ in range(3):
            fake.advance(700)
        assert ticks.read() == 3  # 1 s + 2100 ms: two more seconds, 100 ms kept
        fake.advance(900)
        assert ticks.read() == 4  # the kept 100 ms plus 900 ms make the next whole second
    finally:
        _restore_time()


def test_tickseconds_counts_down_to_zero_and_stays() -> None:
    fake = _with_fake_ticks()
    try:
        ticks = TickSeconds(count_down=True)
        ticks.restart(3)
        fake.advance(2500)
        assert ticks.read() == 1
        fake.advance(600)
        assert ticks.read() == 0
        fake.advance(5000)
        assert ticks.read() == 0
    finally:
        _restore_time()


def test_tickseconds_saturates_at_the_cap() -> None:
    fake = _with_fake_ticks()
    try:
        ticks = TickSeconds()
        ticks.restart(COUNTER_CAP - 1)
        fake.advance(5000)
        assert ticks.read() == COUNTER_CAP
        fake.advance(5000)
        assert ticks.read() == COUNTER_CAP
        ticks.restart(COUNTER_CAP + 7)  # a restart value is clamped into [0, COUNTER_CAP] too
        assert ticks.read() == COUNTER_CAP
        ticks.restart(-4)
        assert ticks.read() == 0
    finally:
        _restore_time()


def test_tickseconds_counts_across_the_ticks_wrap() -> None:
    fake = _with_fake_ticks(start_ms=_TICKS_PERIOD - 1500)
    try:
        ticks = TickSeconds()
        fake.advance(1000)
        assert ticks.read() == 1
        fake.advance(2000)  # crosses ticks_ms()'s 2**30 wrap: the delta stays the true elapsed time
        assert fake.ticks_ms() == 1500
        assert ticks.read() == 3
    finally:
        _restore_time()


def test_tickseconds_ignores_a_zero_or_negative_delta() -> None:
    fake = _with_fake_ticks(start_ms=10_000)
    try:
        ticks = TickSeconds()
        assert ticks.read() == 0
        fake.now_ms -= 3000  # a clock that ran backwards (never on target): nothing changes
        assert ticks.read() == 0
        fake.advance(999)
        assert ticks.read() == 0
        fake.advance(1)
        assert ticks.read() == 1
    finally:
        _restore_time()


class _PrintRecorder:
    # Shadows print() inside asy_print_log only, where every logger line is printed.
    def __init__(self) -> None:
        self.lines: list[tuple[object, ...]] = []
        asy_print_log.print = self  # type: ignore[attr-defined]

    def __call__(self, *args: object, **_kwargs: object) -> None:
        self.lines.append(args)

    def restore(self) -> None:
        del asy_print_log.print  # type: ignore[attr-defined]


def test_arm_tick_timer_arms_a_periodic_one_second_timer() -> None:
    timer = machine.Timer()
    flag = asyncio.ThreadSafeFlag()
    pr = PrintLogHistory(level=1, name="T")
    assert arm_tick_timer(timer, flag, pr, "test") is True
    assert (timer.period, timer.mode) == (1000, machine.Timer.PERIODIC)

    async def fired() -> bool:
        timer.trigger()
        await asyncio.wait_for_ms(flag.wait(), 100)
        return True

    assert run(fired()) is True


def test_arm_tick_timer_reports_a_failed_arm_with_one_line() -> None:
    for exc in (OSError, MemoryError):
        machine.Timer.raise_on_arm = True
        machine.Timer.raise_on_arm_exc = exc
        recorder = _PrintRecorder()
        try:
            timer = machine.Timer()
            pr = PrintLogHistory(level=1, name="T")
            assert arm_tick_timer(timer, asyncio.ThreadSafeFlag(), pr, "test") is False
            assert len(recorder.lines) == 1
            assert recorder.lines[0][:3] == ("T", "Could not arm", "test")
            assert timer.period == -1  # never armed
        finally:
            recorder.restore()
            machine.Timer.raise_on_arm = False
            machine.Timer.raise_on_arm_exc = OSError


def test_utc_now_is_none_until_the_clock_is_marked_valid() -> None:
    fake = _with_fake_ticks()
    try:
        assert utc_now() is None
        set_utc_valid()
        assert utc_now() == fake.wall_s
        fake.wall_s += 60
        assert utc_now() == fake.wall_s
    finally:
        set_utc_valid(valid=False)
        _restore_time()


def test_set_utc_valid_with_valid_false_takes_the_clock_back_to_unavailable() -> None:
    _with_fake_ticks()
    try:
        set_utc_valid()
        assert utc_now() is not None
        set_utc_valid(valid=False)
        assert utc_now() is None
    finally:
        set_utc_valid(valid=False)
        _restore_time()


# ---------------------------------------------------------------------------
# SensorReader - log.fram None (in-memory logging) path
# ---------------------------------------------------------------------------


def test_sensorreader_uses_in_memory_logging_when_fram_is_none() -> None:
    reader = SensorReader(Meas(20.0, 50), "", max_module_error=3)
    assert isinstance(reader.pr, PrintLogHistory)


def test_sensorreader_setup_sets_up_its_logger_and_answers_true() -> None:
    reader = SensorReader(Meas(20.0, 50), "", max_module_error=3)
    assert reader.pr.initialized is False  # __init__ never sets the logger up
    assert run(reader.setup()) is True
    assert reader.pr.initialized is True


def test_sensorreader_has_no_read_triggers_of_its_own() -> None:
    reader = SensorReader(Meas(20.0, 50), "", max_module_error=3)
    assert reader.get_trigger_starters() == []


def test_sensorreader_debug_level_is_forwarded_to_the_logger() -> None:
    reader = SensorReader(Meas(20.0, 50), "", max_module_error=3, log=LogConfig(None, 10, 1))
    assert reader.pr.level == 1


def test_sensorreader_debug_none_leaves_logger_at_off() -> None:
    reader = SensorReader(Meas(20.0, 50), "", max_module_error=3, log=LogConfig(None, 10, None))
    assert reader.pr.level == 0


def test_sensorreader_name_is_baked_into_a_freshly_constructed_logger() -> None:
    reader = SensorReader(Meas(20.0, 50), "TESTNAME", max_module_error=3)
    assert reader.pr.name == "TESTNAME"


def test_sensorreader_empty_name_reaches_the_logger_unchanged() -> None:
    reader = SensorReader(Meas(20.0, 50), "", max_module_error=3)
    assert reader.pr.name == ""


def test_sensorreader_empty_name_ext_reproduces_the_base_name_unchanged() -> None:
    # instance_name()'s single-instance-device no-op guarantee (SPECIFICATION.md Part C.14) -
    # name_ext="" (the default, every module today) must leave self.name/self.pr.name identical to
    # pre-name_ext behavior.
    reader = SensorReader(Meas(20.0, 50), "SCD30", max_module_error=3, name_ext="")
    assert reader.name == "SCD30"
    assert reader.pr.name == "SCD30"


def test_sensorreader_non_empty_name_ext_disambiguates_a_second_instance() -> None:
    reader = SensorReader(Meas(20.0, 50), "SCD30", max_module_error=3, name_ext="fan_pressure")
    assert reader.name == "SCD30_fan_pressure"
    assert reader.pr.name == "SCD30_fan_pressure"


def test_sensorreader_get_error_sources_returns_just_itself() -> None:
    reader = SensorReader(Meas(20.0, 50), "", max_module_error=3)
    assert reader.get_error_sources() == [reader]


def test_sensorreader_get_loggers_returns_just_its_own_logger() -> None:
    reader = SensorReader(Meas(20.0, 50), "", max_module_error=3)
    assert reader.get_loggers() == [reader.pr]


def test_sensorreader_history_length_zero_is_forwarded_and_never_raises() -> None:
    reader = SensorReader(Meas(None, 50), "", max_module_error=3, log=LogConfig(None, 0, None))
    assert run(reader._error_check(Meas(None, 50))) is True
    assert reader.pr._err_count == 1
    assert list(reader.pr.history) == []  # nothing to hold, but the count still tracked


def _newest(reader: "SensorReader") -> "tuple[int, str]":
    log = run(reader.pr.get_log())[reader.pr.name]
    return log["ErrNum"][-1], log["ErrType"][-1]


def test_error_check_max_module_error_zero_gives_up_on_first_failure() -> None:
    # Zero tolerance is a legitimate, if unusual, config value - not a caller mistake to guard
    # against like a negative max_module_error would be (see BACKLOG.md's structural-pass note).
    reader = SensorReader(Meas(None, 50), "", max_module_error=0)
    assert run(reader._error_check(Meas(None, 50))) is False
    assert _newest(reader) == (code("E", "GIVE_UP"), "E")


def test_a_failing_cycle_keeps_the_drivers_and_the_streaks_entries() -> None:
    # Each layer that meets the fault keeps its own entry: the driver's read failure, then the streak's;
    # the give-up adds its own. Alternating codes each take a slot under the newest-entry rule (C.7.1).
    reader = SensorReader(Meas(None, 50), "", max_module_error=1)
    assert run(reader.setup()) is True
    for _ in range(2):
        run(reader.pr.err_s("read failed", errno=code("E", "READ")))  # the driver's own entry
        run(reader._error_check(Meas(None, 50)))
    log = run(reader.pr.get_log())[reader.pr.name]
    used = [log["ErrNum"][i] for i in range(len(log["ErrNum"])) if log["ErrType"][i] != "N"]
    assert used == [code("E", "READ"), code("E", "STREAK"), code("E", "READ"), code("E", "STREAK"), code("E", "GIVE_UP")], used
    assert log["ErrCount"] == 5


def test_get_dict_cfg_duplicate_schema_names_collapse_to_one_key() -> None:
    # schema_names() documents "duplicates preserved" - _get_dict_cfg's own dict comprehension must
    # still behave sanely (last write wins, no raise) rather than assuming names are unique.
    dup_schema: cm.ConfigSchema = (
        ("SampleInterval", "int", 2, 1, 3600, None),
        ("SampleInterval", "int", 9, 1, 3600, None),
    )
    reader = SensorReader(Meas(20.0, 50), "", max_module_error=3)
    result = run(reader._get_dict_cfg("Sensor", dup_schema))
    assert result == {"Sensor": {"SampleInterval": None}}


def test_sensorreader_meas_data_roundtrip() -> None:
    reader = SensorReader(Meas(20.0, 50), "", max_module_error=3)
    assert run(reader._get_meas_data()) == Meas(20.0, 50)
    run(reader._set_meas_data(Meas(21.0, 60)))
    assert run(reader._get_meas_data()) == Meas(21.0, 60)


def test_sensorreader_reset_error_counter_clears_history() -> None:
    reader = SensorReader(Meas(20.0, 50), "", max_module_error=3)
    assert run(reader.setup()) is True
    run(reader.pr.err_s("boom", errno=code("E", "STREAK")))
    assert reader.pr._err_count == 1
    assert run(reader.reset_error_counter()) is True
    assert reader.pr._err_count == 0


def test_sensorreader_reset_error_counter_also_clears_the_consecutive_failure_streak() -> None:
    # reset_error_counter() must reset both counters this file tracks, not just pr's persisted
    # history/_err_count: a caller resetting "the" error counter after a task reset shouldn't have
    # the next run start partway toward giving up again via the untouched internal streak.
    reader = SensorReader(Meas(None, 50), "", max_module_error=5)
    run(reader._error_check(Meas(None, 50)))
    run(reader._error_check(Meas(None, 50)))
    assert reader._err_cnt_internal == 2
    run(reader.reset_error_counter())
    assert reader._err_cnt_internal == 0


def test_error_check_no_failure_keeps_going_and_decays_counter() -> None:
    reader = SensorReader(Meas(20.0, 50), "", max_module_error=2)
    reader._err_cnt_internal = 1
    assert run(reader._error_check(Meas(20.0, 50))) is True
    assert reader._err_cnt_internal == 0  # decayed back down since this call had no failure


def test_error_check_failure_increments_until_giving_up() -> None:
    reader = SensorReader(Meas(None, 50), "", max_module_error=2)
    assert run(reader._error_check(Meas(None, 50))) is True  # 1 <= max
    assert run(reader._error_check(Meas(None, 50))) is True  # 2 <= max
    assert run(reader._error_check(Meas(None, 50))) is False  # 3 > max - give up


def test_error_check_condition_false_ignores_none_results() -> None:
    reader = SensorReader(Meas(None, 50), "", max_module_error=0)
    assert run(reader._error_check(Meas(None, 50), condition=False)) is True
    assert reader._err_cnt_internal == 0


def test_get_dict_cfg_default_returns_all_none() -> None:
    reader = SensorReader(Meas(20.0, 50), "", max_module_error=3)
    result = run(reader._get_dict_cfg("Sensor", _VAL_SI))
    assert result == {"Sensor": {"SampleInterval": None}}


def test_get_dict_cfg_merges_callback_result() -> None:
    reader = SensorReader(Meas(20.0, 50), "", max_module_error=3)

    async def callback() -> "dict[str, int | float | str | None]":
        return {"SampleInterval": 5}

    result = run(reader._get_dict_cfg("Sensor", _VAL_SI, callback=callback))
    assert result == {"Sensor": {"SampleInterval": 5}}


def test_get_dict_cfg_callback_exception_is_caught() -> None:
    reader = SensorReader(Meas(20.0, 50), "", max_module_error=3)

    async def bad_callback() -> "dict[str, int | float | str | None]":
        raise RuntimeError("sensor read failed")

    result = run(reader._get_dict_cfg("Sensor", _VAL_SI, callback=bad_callback))
    assert result == {"Sensor": {"SampleInterval": None}}  # falls back to defaults, doesn't raise


def test_get_dict_cfg_callback_extra_key_is_still_merged() -> None:
    reader = SensorReader(Meas(20.0, 50), "", max_module_error=3)

    async def callback() -> "dict[str, int | float | str | None]":
        return {"SampleInterval": 5, "Unexpected": 1}

    result = run(reader._get_dict_cfg("Sensor", _VAL_SI, callback=callback))
    assert result == {"Sensor": {"SampleInterval": 5, "Unexpected": 1}}
    assert reader.pr._err_count == 1  # the "unknown keys" path goes through wrn_s(), not silently
    assert _newest(reader) == (code("W", "CALLBACK_KEYS"), "W")


def test_get_dict_cfg_mgr_cfg_extra_key_is_still_merged_and_warned() -> None:
    # Mirrors test_get_dict_cfg_callback_extra_key_is_still_merged: _get_mgr_cfg is the same kind of
    # overridable extension point as callback, so an override returning unrequested keys must be
    # merged-and-warned the same way, not silently swallowed just because it's the other code path.
    class ExtraKeyMgrCfgReader(SensorReader):
        async def _get_mgr_cfg(self, _cfg: "list[str]") -> "dict[str, int | float | str | None] | None":
            return {"SampleInterval": 5, "Unexpected": 1}

    reader = ExtraKeyMgrCfgReader(Meas(20.0, 50), "", max_module_error=3)
    result = run(reader._get_dict_cfg("Sensor", _VAL_SI))
    assert result == {"Sensor": {"SampleInterval": 5, "Unexpected": 1}}
    assert reader.pr._err_count == 1
    assert _newest(reader) == (code("W", "CFG_KEYS"), "W")


def test_get_dict_cfg_mgr_cfg_expected_keys_only_do_not_warn() -> None:
    # Negative case for the above: an override that only ever returns requested keys (the real
    # SensorReaderConfig._get_mgr_cfg's actual shape) must not trip the new warning path.
    reader = SensorReader(Meas(20.0, 50), "", max_module_error=3)
    result = run(reader._get_dict_cfg("Sensor", _VAL_SI))
    assert result == {"Sensor": {"SampleInterval": None}}
    assert reader.pr._err_count == 0


def test_get_dict_cfg_mgr_cfg_update_exception_is_caught() -> None:
    # _get_mgr_cfg is an override point (dict[...] | None per its type contract, but that's not
    # statically enforced on a runtime-misbehaving subclass) - a value that isn't actually
    # dict-like must not let ret[name].update(sensor_conf) raise out of _get_dict_cfg.
    class BadMgrCfgReader(SensorReader):
        async def _get_mgr_cfg(self, _cfg: "list[str]") -> "dict[str, int | float | str | None] | None":
            return 42  # type: ignore[return-value]

    reader = BadMgrCfgReader(Meas(20.0, 50), "", max_module_error=3)
    result = run(reader._get_dict_cfg("Sensor", _VAL_SI))
    assert result == {"Sensor": {"SampleInterval": None}}  # update(42) raised TypeError - falls back to all-None


# ---------------------------------------------------------------------------
# SensorReader - fram given (FRAM-backed PrintLogHistoryStore logging), using the real,
# now-promoted FRAMManager driven by tests/_fram_chip_fake.py's simulated MB85RS64V chip.
# Integration coverage across asy_base_classes.py + asy_print_log.py + asy_fram_manager.py together.
# ---------------------------------------------------------------------------


def test_sensorreader_uses_fram_backed_logging_when_fram_is_given() -> None:
    manager, _chip = make_fram_manager()
    reader = SensorReader(Meas(20.0, 50), "", max_module_error=3, log=LogConfig(manager, 10, None))
    assert isinstance(reader.pr, PrintLogHistoryStore)


def test_sensorreader_fram_backed_error_check_persists_and_survives_reboot() -> None:
    manager, chip = make_fram_manager()
    run(manager.setup())
    reader = SensorReader(Meas(None, 50), "", max_module_error=5, log=LogConfig(manager, 10, None))
    assert run(reader.setup()) is True
    assert run(reader._error_check(Meas(None, 50))) is True
    assert run(reader._error_check(Meas(None, 50))) is True
    assert reader.pr._err_count == 2

    # Simulate a reboot: a fresh SensorReader/manager pair attached to the same underlying chip,
    # same as asy_print_log.py's own test_printloghistorystore_err_s_persists_and_survives_a_simulated_reboot.
    manager2, _chip2 = make_fram_manager()
    manager2.fram._spidev.spi._spi = chip
    run(manager2.setup())
    rebooted = SensorReader(Meas(None, 50), "", max_module_error=5, log=LogConfig(manager2, 10, None))
    assert run(rebooted.setup()) is True
    assert rebooted.pr._err_count == 2
    nums = run(rebooted.pr.get_log())[rebooted.pr.name]["ErrNum"]
    assert nums[-1] == code("E", "STREAK") and nums.count(code("E", "STREAK")) == 1  # the streak's entry; its repeat spent no slot


def test_sensorreader_fram_backed_error_check_without_setup_never_raises() -> None:
    # The boot batch's reader.setup() sets the logger up, since SensorReader.__init__ is sync.
    # Skipping setup() must degrade cleanly - in-memory count and history still update per asy_print_log.py's
    # contract, only the FRAM write is skipped - and never raise.
    manager, _chip = make_fram_manager()
    reader = SensorReader(Meas(None, 50), "", max_module_error=5, log=LogConfig(manager, 10, None))
    assert reader.pr.initialized is False
    assert run(reader._error_check(Meas(None, 50))) is True
    assert reader.pr._err_count == 1


def test_sensorreader_fram_allocation_failure_still_logs_in_memory_without_raising() -> None:
    manager, _chip = make_fram_manager(max_size=1)  # too small for any real chunk
    reader = SensorReader(Meas(None, 50), "", max_module_error=5, log=LogConfig(manager, 10, None))
    assert isinstance(reader.pr, PrintLogHistoryStore)
    assert reader.pr.fram is None
    assert run(reader.setup()) is True  # nothing allocated: the logger runs in RAM, never raises
    assert run(reader._error_check(Meas(None, 50))) is True
    assert reader.pr._err_count == 1  # in-memory count still tracked despite FRAM being unavailable


# ---------------------------------------------------------------------------
# SensorReader - real FRAM failure modes injected at the simulated-chip level, plus the two Protocol-level
# defensive-contract proofs with no real-class equivalent, driven through SensorReader's own API rather than
# asy_print_log.py's methods.
#
# test_asy_print_log.py already covers each mode exhaustively at that level; this confirms the same fault matrix
# still degrades cleanly through asy_base_classes.py's own wiring.
# ---------------------------------------------------------------------------


def test_sensorreader_fram_raise_on_get_chunk_never_raises_at_construction() -> None:
    # An allocation failure while the chunk is built leaves SensorReader's logger RAM-only, never raising.
    fake_manager = _RaisingFramManager(None, raise_on_get_chunk=True)
    reader = SensorReader(Meas(None, 50), "", max_module_error=5, log=LogConfig(fake_manager, 10, None))
    assert isinstance(reader.pr, PrintLogHistoryStore)
    assert reader.pr.fram is None
    assert run(reader._error_check(Meas(None, 50))) is True
    assert reader.pr._err_count == 1


def test_sensorreader_fram_write_into_raising_is_caught_during_error_check() -> None:
    # A chunk write failing by allocation, the one way it can, degrades the same way through SensorReader.
    chunk = _RaisingFramChunk(raise_on_write=True)
    fake_manager = _RaisingFramManager(chunk)
    # history_length=4 matches _RaisingFramChunk.get_buffer()'s hardcoded 6-byte buffer (2-byte
    # header + 4 history bytes) - a mismatch here makes struct.pack_into/unpack_from fail on
    # buffer size instead of exercising the intended raise_on_write path.
    reader = SensorReader(Meas(None, 50), "", max_module_error=5, log=LogConfig(fake_manager, 4, None))
    assert isinstance(reader.pr, PrintLogHistoryStore)
    assert run(reader.setup()) is True
    assert run(reader._error_check(Meas(None, 50))) is True
    assert reader.pr._err_count == 1  # FRAM write failed silently; in-memory count still tracked


def test_sensorreader_fram_write_returns_false_is_surfaced_during_error_check() -> None:
    # A real hardware-reported failure (not a raise): WREN never latches, so every write the real
    # chunk attempts fails cleanly.
    manager, chip = make_fram_manager()
    run(manager.setup())
    reader = SensorReader(Meas(None, 50), "", max_module_error=5, log=LogConfig(manager, 10, None))
    assert run(reader.setup()) is True
    chip.drop_wren = True
    assert run(reader._error_check(Meas(None, 50))) is True
    assert reader.pr._err_count == 1


def test_sensorreader_fram_read_into_raising_falls_back_to_write_during_setup() -> None:
    chunk = _RaisingFramChunk(raise_on_read=True)
    fake_manager = _RaisingFramManager(chunk)
    reader = SensorReader(Meas(None, 50), "", max_module_error=5, log=LogConfig(fake_manager, 4, None))
    assert run(reader.setup()) is True  # first-time setup: _read() fails, falls back to _write() succeeding
    assert reader.pr.initialized is True


def test_sensorreader_fram_setup_fails_cleanly_when_both_read_and_write_fail() -> None:
    manager, chip = make_fram_manager()
    run(manager.setup())
    reader = SensorReader(Meas(None, 50), "", max_module_error=5, log=LogConfig(manager, 10, None))
    # Nothing written yet, so _read() naturally fails (chunk reads back as uninitialized); WREN
    # never latching makes the fallback _write() of defaults fail too.
    chip.drop_wren = True
    assert run(reader.setup()) is True  # the reader is ready; its logger runs in RAM
    assert reader.pr.initialized is False
    assert run(reader._error_check(Meas(None, 50))) is True  # still tracks in-memory
    assert reader.pr._err_count == 1


# ---------------------------------------------------------------------------
# SensorReaderConfig - real ConfigManager/file I/O, no mocking
# ---------------------------------------------------------------------------


def test_sensorreaderconfig_wires_a_real_configmanager() -> None:
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_temp.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "temp", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        assert reader.cfgmgr._config_file == path_prefix + "config_temp.cfg"
        assert reader.cfgmgr.valid is True
    finally:
        _remove(path_prefix + "config_temp.cfg")


def test_sensorreaderconfig_forwards_its_name_to_the_base_class_logger() -> None:
    # SensorReaderConfig.__init__ already took name to build the config filename - it must also
    # forward it to super().__init__() so reader.pr's own identity matches, not just cfgmgr's.
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_namefwd.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "namefwd", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        assert reader.pr.name == "namefwd"
    finally:
        _remove(path_prefix + "config_namefwd.cfg")


def test_sensorreaderconfig_name_ext_threads_into_filename_and_both_loggers() -> None:
    # name_ext (SPECIFICATION.md Part C.14) must resolve once in super().__init__() and then be used
    # consistently everywhere self.name is: the on-flash config filename, this object's logger, and the
    # nested ConfigManager's "CFGMGR_<name>" logger - not just the raw `name` positional.
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_SCD30_fan_pressure.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "SCD30", _VAL_SI, max_module_error=3, name_ext="fan_pressure", cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        assert reader.name == "SCD30_fan_pressure"
        assert reader.pr.name == "SCD30_fan_pressure"
        assert reader.cfgmgr._config_file == path_prefix + "config_SCD30_fan_pressure.cfg"
        assert reader.cfgmgr.pr.name == "CFGMGR_SCD30_fan_pressure"
    finally:
        _remove(path_prefix + "config_SCD30_fan_pressure.cfg")


def test_sensorreaderconfig_get_error_sources_includes_its_cfgmgr() -> None:
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_errsrc.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "errsrc", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        assert reader.get_error_sources() == [reader, reader.cfgmgr]
    finally:
        _remove(path_prefix + "config_errsrc.cfg")


def test_sensorreaderconfig_get_loggers_includes_its_cfgmgrs_logger() -> None:
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_loggers.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "loggers", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        assert reader.get_loggers() == [reader.pr, reader.cfgmgr.pr]
    finally:
        _remove(path_prefix + "config_loggers.cfg")


def test_sensorreaderconfig_setup_awaits_cfgmgr_setup() -> None:
    # SensorReaderConfig's own async def setup() extends ConfigManager's sync-__init__/
    # async-setup() readiness-gate pattern one level up (SPECIFICATION.md C.13) - awaiting
    # it must leave cfgmgr exactly as ready as calling cfgmgr.setup() directly would.
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_ownsetup.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "ownsetup", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        valid_before = reader.cfgmgr.valid
        assert valid_before is False  # not set up yet - __init__ is stash-only
        assert run(reader.setup()) is True
        valid_after = reader.cfgmgr.valid
        assert valid_after is True
        assert reader.pr.initialized is True  # the reader's own logger first, then the store's
        assert reader.cfgmgr.pr.initialized is True
        result = run(reader._get_dict_cfg("Sensor", _VAL_SI))
        assert result == {"Sensor": {"SampleInterval": 2}}
    finally:
        _remove(path_prefix + "config_ownsetup.cfg")


def test_sensorreaderconfig_setup_answers_false_for_an_unusable_store() -> None:
    path_prefix = _SHARED_CFG_DIR
    os.mkdir(path_prefix + "config_dirsetup.cfg")  # a directory where the config file belongs
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "dirsetup", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        assert run(reader.setup()) is False
        assert reader.cfgmgr.valid is False
        assert reader.pr.initialized is True  # the logger is set up even when the store is not
    finally:
        os.rmdir(path_prefix + "config_dirsetup.cfg")


def test_sensorreaderconfig_get_cfg_schema_returns_the_schema_it_was_built_with() -> None:
    # Base-class-owned getter, mirroring _get_mgr_cfg/_get_dict_cfg's "define once, inherit everywhere"
    # shape: every SensorReaderConfig subclass gets this free from the schema it already passes to
    # super().__init__(), held in the private self._cfg_schema.
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_getschema.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "getschema", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        assert reader.get_cfg_schema() == _VAL_SI
        assert reader._cfg_schema == _VAL_SI
    finally:
        _remove(path_prefix + "config_getschema.cfg")


def test_sensorreaderconfig_get_cfg_schema_is_a_plain_sync_call() -> None:
    # Deliberately sync, unlike _get_mgr_cfg/_get_dict_cfg: the schema is static, fixed at
    # construction, no I/O or locking involved - calling it directly (no run()/await) is the point.
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_syncschema.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "syncschema", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        result = reader.get_cfg_schema()
        assert result == _VAL_SI
    finally:
        _remove(path_prefix + "config_syncschema.cfg")


def test_sensorreaderconfig_get_cfg_schema_reflects_a_concatenated_multi_field_schema() -> None:
    # Every real driver passes a concatenated multi-tuple schema (e.g. asy_bmp3xx_driver.py's
    # _VAL_SAMPLE_INTERVAL + _VAL_PRES_OVERS + ...), not a single-field one - confirms the getter returns the exact
    # concatenated object, not just a single-field happy path.
    combined = _VAL_SI + _VAL_BOOL
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_combinedschema.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "combinedschema", combined, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        assert reader.get_cfg_schema() == combined
    finally:
        _remove(path_prefix + "config_combinedschema.cfg")


def test_sensorreaderconfig_is_a_sensorreader_with_a_real_mgr_cfg_override() -> None:
    # Inheritance-level check: SensorReaderConfig IS-A SensorReader, and _get_mgr_cfg's override
    # actually replaces the base class's always-{} stub rather than just adding cfgmgr alongside it.
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_isa.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "isa", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        assert isinstance(reader, SensorReader)
        assert run(reader._get_mgr_cfg(["SampleInterval"])) == {"SampleInterval": 2}
    finally:
        _remove(path_prefix + "config_isa.cfg")


def test_get_mgr_cfg_logs_a_cross_reference_line_before_calling_into_cfgmgr() -> None:
    # A line via the owner's self.pr whenever _get_mgr_cfg actually calls into self.cfgmgr, pairing
    # with ConfigManager's own "CFGMGR_"-identified log line for a human/future-rsyslog reader.
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_crossrefget.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "crossrefget", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        evt_calls: list[tuple[Any, ...]] = []
        reader.pr.evt = lambda *args, **_kwargs: evt_calls.append(args)  # type: ignore[method-assign]
        run(reader._get_mgr_cfg(["SampleInterval"]))
        assert len(evt_calls) == 1
    finally:
        _remove(path_prefix + "config_crossrefget.cfg")


def test_sensorreaderconfig_get_dict_cfg_round_trips_a_real_bool_field() -> None:
    # asy_scd30_driver.py's SelfCal is a real "bool"-schema field flowing through this exact path -
    # confirms the dict actually carries a bool (not a stringified/int-coerced stand-in).
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_boolfield.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "boolfield", _VAL_BOOL, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        result = run(reader._get_dict_cfg("Sensor", _VAL_BOOL))
        assert result == {"Sensor": {"SelfCal": False}}
        assert type(result["Sensor"]["SelfCal"]) is bool
    finally:
        _remove(path_prefix + "config_boolfield.cfg")


def test_sensorreaderconfig_configmanager_has_its_own_separate_logger_instance() -> None:
    # ConfigManager builds its own "CFGMGR_"-prefixed PrintLogHistory instead of reusing its owner's self.pr
    # - reusing the owner's logger would mislabel every config-related line as coming from the owner itself.
    # Deliberately the inverse of what this test asserted under the old shared-instance design.
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_shared.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "shared", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        assert reader.cfgmgr.pr is not reader.pr
    finally:
        _remove(path_prefix + "config_shared.cfg")


def test_sensorreaderconfig_get_dict_cfg_reads_real_config_file() -> None:
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_temp2.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "temp2", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        result = run(reader._get_dict_cfg("Sensor", _VAL_SI))
        assert result == {"Sensor": {"SampleInterval": 2}}  # the schema's own default
    finally:
        _remove(path_prefix + "config_temp2.cfg")


def test_sensorreaderconfig_malformed_schema_propagates_none_through_get_dict_cfg() -> None:
    # An empty default_vals schema makes ConfigManager itself invalid (see asy_config_manager.py's
    # own "Defaults are empty" check) - confirms that invalidity propagates cleanly all the way up
    # through SensorReaderConfig's own public surface, not just when calling ConfigManager directly.
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_badschema.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "badschema", (), max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        assert reader.cfgmgr.valid is False
        result = run(reader._get_dict_cfg("Sensor", ()))
        assert result == {"Sensor": {}}
    finally:
        _remove(path_prefix + "config_badschema.cfg")


# ---------------------------------------------------------------------------
# SensorReaderConfig - integration across all three files at once: real ConfigManager file I/O
# (asy_config_manager.py), FRAM-backed logging via the real FRAMManager (asy_print_log.py +
# asy_fram_manager.py), and asy_base_classes.py's own wiring between the two.
# ---------------------------------------------------------------------------


def test_sensorreaderconfig_fram_backed_logging_with_real_config_file() -> None:
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_fram1.cfg")
    try:
        manager, _chip = make_fram_manager()
        reader = SensorReaderConfig(Meas(20.0, 50), "fram1", _VAL_SI, max_module_error=3, cfg_path=path_prefix, log=LogConfig(manager, 10, None))
        run(reader.cfgmgr.setup())
        assert isinstance(reader.pr, PrintLogHistoryStore)
        assert reader.cfgmgr.valid is True
        result = run(reader._get_dict_cfg("Sensor", _VAL_SI))
        assert result == {"Sensor": {"SampleInterval": 2}}
    finally:
        _remove(path_prefix + "config_fram1.cfg")


def test_sensorreaderconfig_cfgmgr_inherits_fram_from_its_owning_module() -> None:
    # The implicit FRAM-wiring rule (SPECIFICATION.md A.7): SensorReaderConfig forwards its own in-scope
    # log config into the ConfigManager it owns, in its own chunk, separate from reader.pr's.
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_fram_cfgmgr.cfg")
    try:
        manager, _chip = make_fram_manager()
        reader = SensorReaderConfig(Meas(20.0, 50), "fram_cfgmgr", _VAL_SI, max_module_error=3, cfg_path=path_prefix, log=LogConfig(manager, 10, None))
        run(reader.cfgmgr.setup())
        assert isinstance(reader.cfgmgr.pr, PrintLogHistoryStore)
        assert isinstance(reader.pr, PrintLogHistoryStore)
        assert reader.cfgmgr.pr.fram is not None
        assert reader.cfgmgr.pr.fram is not reader.pr.fram  # each draws its own separate chunk
    finally:
        _remove(path_prefix + "config_fram_cfgmgr.cfg")


def test_sensorreaderconfig_cfgmgr_write_failure_errno_persists_across_a_simulated_reboot() -> None:
    # A real write_config() refusal (BAD_ARG, an unknown key) must survive a reboot through cfgmgr's own
    # FRAM-backed logger, exactly like reader.pr's own error history already does
    # (test_sensorreader_fram_backed_error_check_persists_and_survives_reboot).
    path_prefix = _SHARED_CFG_DIR
    path = path_prefix + "config_fram_reboot.cfg"
    _remove(path)
    try:
        manager, chip = make_fram_manager()
        run(manager.setup())
        reader = SensorReaderConfig(Meas(20.0, 50), "fram_reboot", _VAL_SI, max_module_error=3, cfg_path=path_prefix, log=LogConfig(manager, 10, None))
        run(reader.cfgmgr.setup())
        # A first boot's absent file is written with its defaults and persists no entry (a console line only).
        baseline_err_count = reader.cfgmgr.pr._err_count
        assert baseline_err_count == 0
        ok, results = run(reader.cfgmgr.write_config({"NotARealKey": 1}))
        # An unrecognized key alone never sets changed=True, so write_config's own "nothing to
        # write" path returns (True, ...) - "ok" means "no exception", not "every field valid";
        # the per-field "Invalid" result plus the persisted errno are what this test is really about.
        assert ok is True
        assert results == {"NotARealKey": "Invalid"}
        assert reader.cfgmgr.pr._err_count == baseline_err_count + 1

        # Simulate a reboot: a fresh manager/reader pair attached to the same underlying chip (same
        # pattern as test_sensorreader_fram_backed_error_check_persists_and_survives_reboot); the config
        # file the first setup() wrote is read back, recording nothing further.
        manager2, _chip2 = make_fram_manager()
        manager2.fram._spidev.spi._spi = chip
        run(manager2.setup())
        rebooted = SensorReaderConfig(Meas(20.0, 50), "fram_reboot", _VAL_SI, max_module_error=3, cfg_path=path_prefix, log=LogConfig(manager2, 10, None))
        run(rebooted.cfgmgr.setup())
        assert rebooted.cfgmgr.pr._err_count == baseline_err_count + 1
    finally:
        _remove(path)


def test_one_log_config_reaches_both_loggers_with_its_store_length_and_level() -> None:
    # The owner's one logging config object: the reader's logger and its config store's logger
    # each carry log's FRAM store (their own chunks), its history length and its level.
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_logcfg.cfg")
    try:
        manager, _chip = make_fram_manager()
        run(manager.setup())
        log = LogConfig(manager, 4, 1)
        reader = SensorReaderConfig(Meas(20.0, 50), "logcfg", _VAL_SI, max_module_error=3, cfg_path=path_prefix, log=log)
        for pr in (reader.pr, reader.cfgmgr.pr):
            assert isinstance(pr, PrintLogHistoryStore)
            assert pr.fram is not None
            assert len(pr.history) == 4  # padded to its fixed length
            assert pr.level == 1
        own, store = reader.pr, reader.cfgmgr.pr
        assert isinstance(own, PrintLogHistoryStore) and isinstance(store, PrintLogHistoryStore)
        assert own.fram is not store.fram
    finally:
        _remove(path_prefix + "config_logcfg.cfg")


def test_sensorreaderconfig_cfgmgr_stays_ram_only_when_fram_is_none() -> None:
    # With no FRAM in log at all the store's logger stays exactly RAM-only, not just "still works" - same
    # shape as test_sensorreader_uses_in_memory_logging_when_fram_is_none.
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_no_fram_cfgmgr.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "no_fram_cfgmgr", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        assert isinstance(reader.cfgmgr.pr, PrintLogHistory)
        assert not isinstance(reader.cfgmgr.pr, PrintLogHistoryStore)
    finally:
        _remove(path_prefix + "config_no_fram_cfgmgr.cfg")


def test_sensorreaderconfig_malformed_config_file_repairs_cleanly_with_fram_backed_logger() -> None:
    # ConfigManager's repair warning goes through its own separate "CFGMGR_" logger (FRAM-backed too, in its
    # own chunk), never reader.pr, so reader.pr._err_count stays 0 regardless of the repair.
    path_prefix = _SHARED_CFG_DIR
    path = path_prefix + "config_fram2.cfg"
    _remove(path)
    with open(path, "w") as f:
        f.write("{not valid json")
    try:
        manager, _chip = make_fram_manager()
        reader = SensorReaderConfig(Meas(20.0, 50), "fram2", _VAL_SI, max_module_error=3, cfg_path=path_prefix, log=LogConfig(manager, 10, None))
        run(reader.cfgmgr.setup())
        assert reader.cfgmgr.valid is True  # malformed file was repaired, not left invalid
        assert reader.cfgmgr.faulted is True  # a damaged file stays listed after its repair
        assert reader.cfgmgr.pr._err_count == 1  # the store's own warning, not the reader's
        assert reader.pr._err_count == 0
        result = run(reader._get_dict_cfg("Sensor", _VAL_SI))
        assert result == {"Sensor": {"SampleInterval": 2}}
    finally:
        _remove(path)


def test_sensorreaderconfig_fram_allocation_failure_and_missing_config_file_together() -> None:
    # Two independent subsystems degrading at once: FRAM allocation fails (pr.fram stays None) while the
    # config file does not exist yet either. Neither failure may raise, nor derail the other.
    #
    # Also WP4/Topic 6's negative case: it proves the per-device "every FRAM-chunk-holding module has a non-
    # None chunk" check can genuinely fail. _allocated_size can never exceed size by construction, so that
    # comparison alone is a tautology; a None chunk reference is the real signal capacity was insufficient.
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_fram3.cfg")
    try:
        manager, _chip = make_fram_manager(max_size=1)  # too small for any real chunk
        reader = SensorReaderConfig(
            Meas(20.0, 50),
            "fram3",
            _VAL_SI,
            max_module_error=3,
            cfg_path=path_prefix,
            log=LogConfig(manager, 10, None),
        )
        run(reader.cfgmgr.setup())
        assert isinstance(reader.pr, PrintLogHistoryStore)
        assert reader.pr.fram is None
        assert isinstance(reader.cfgmgr.pr, PrintLogHistoryStore)
        assert reader.cfgmgr.pr.fram is None
        assert reader.cfgmgr.valid is True
        result = run(reader._get_dict_cfg("Sensor", _VAL_SI))
        assert result == {"Sensor": {"SampleInterval": 2}}
    finally:
        _remove(path_prefix + "config_fram3.cfg")


def test_sensorreaderconfig_write_config_is_reflected_by_get_dict_cfg() -> None:
    # Closes the loop on the read-only integration tests above: a write through the wired
    # ConfigManager (asy_config_manager.py) must be visible through SensorReaderConfig's own public
    # surface (asy_base_classes.py), with no error logged through the real PrintLogHistory (asy_print_log.py).
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_writeback.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "writeback", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        ok, results = run(_write_flushed(reader.cfgmgr, {"SampleInterval": 42}))
        assert ok is True
        assert results == {"SampleInterval": "Valid"}
        assert reader.pr._err_count == 0
        result = run(reader._get_dict_cfg("Sensor", _VAL_SI))
        assert result == {"Sensor": {"SampleInterval": 42}}
    finally:
        _remove(path_prefix + "config_writeback.cfg")


# ---------------------------------------------------------------------------
# The write orchestration lives on SensorReader; SensorReaderConfig adds the file store (SCD30's AmbPres uses
# this path as an always key). Persist first, then push (owner, 2026-09-26), so whatever reached the hardware is
# still stored after an unplanned reset; push fires only for an actual change ("Valid"), never for "Unchanged".
# ---------------------------------------------------------------------------


def test_a_plain_sensorreader_answers_every_key_failed() -> None:
    # The default store is none: _set_mgr_cfg() persists nothing, so nothing is pushed either.
    reader = SensorReader(Meas(20.0, 50), "", max_module_error=3)
    pushed: list[int | float | str | bool | None] = []

    async def push(value: "int | float | str | bool | None") -> bool:
        pushed.append(value)
        return True

    reader._push_callbacks["SampleInterval"] = push
    assert run(reader._set_mgr_cfg({"SampleInterval": 42}, _VAL_SI)) == (False, {})
    results = run(reader._set_dict_cfg({"SampleInterval": 42, "Ghost": 1}, _VAL_SI))
    assert results == {"SampleInterval": "Failed", "Ghost": "Failed"}
    assert pushed == []
    assert reader.pr._err_count == 0  # no store is not a fault of the request


def test_a_key_without_a_push_callback_triggers_no_pre_write_read() -> None:
    # The pre-write snapshot serves only _recover_failed_push(), which runs only for a pushed key: a store
    # without push callbacks (SCD30's chip) pays no second read, and a pushed key still gets its snapshot.
    class CountingReader(SensorReaderConfig):
        reads: "list[list[str]]"

        async def _get_mgr_cfg(self, cfg: "list[str]") -> "dict[str, int | float | str | bool | None] | None":
            self.reads.append(cfg)
            return await super()._get_mgr_cfg(cfg)

    combined = _VAL_SI + _VAL_BOOL
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_nosnapshot.cfg")
    try:
        reader = CountingReader(Meas(20.0, 50), "nosnapshot", combined, max_module_error=3, cfg_path=path_prefix)
        reader.reads = []
        run(reader.cfgmgr.setup())
        assert run(reader._set_dict_cfg({"SampleInterval": 42, "SelfCal": True}, combined)) == {"SampleInterval": "Valid", "SelfCal": "Valid"}
        assert reader.reads == []

        async def push_ok(_value: "int | float | str | bool | None") -> bool:
            return True

        reader._push_callbacks["SelfCal"] = push_ok
        assert run(reader._set_dict_cfg({"SampleInterval": 43, "SelfCal": False}, combined)) == {"SampleInterval": "Valid", "SelfCal": "Valid"}
        assert reader.reads == [["SelfCal"]]
    finally:
        _remove(path_prefix + "config_nosnapshot.cfg")


def test_set_mgr_cfg_delegates_to_the_real_configmanager() -> None:
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_setmgr.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "setmgr", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())

        async def scenario() -> "tuple[tuple[bool, cm.WriteValidity], int, int]":
            with WriteCountingOpen(asy_config_manager) as counter:
                result = await reader._set_mgr_cfg({"SampleInterval": 42}, _VAL_SI)
                for _ in range(3):
                    await asyncio.sleep(0)
                held = counter.writes  # deferred: nothing written before the commit
                reader._commit_mgr_cfg()
                await reader.cfgmgr.flush_pending()
            return result, held, counter.writes

        (ok, results), held, written = run(scenario())
        assert ok is True
        assert results == {"SampleInterval": "Valid"}
        assert (held, written) == (0, 1)
        assert run(reader._get_dict_cfg("Sensor", _VAL_SI)) == {"Sensor": {"SampleInterval": 42}}
    finally:
        _remove(path_prefix + "config_setmgr.cfg")


def test_set_mgr_cfg_logs_a_cross_reference_line_before_calling_into_cfgmgr() -> None:
    # Setter mirror of test_get_mgr_cfg_logs_a_cross_reference_line_before_calling_into_cfgmgr.
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_crossrefset.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "crossrefset", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        evt_calls: list[tuple[Any, ...]] = []
        reader.pr.evt = lambda *args, **_kwargs: evt_calls.append(args)  # type: ignore[method-assign]
        run(reader._set_mgr_cfg({"SampleInterval": 42}, _VAL_SI))
        reader._commit_mgr_cfg()
        run(reader.cfgmgr.flush_pending())
        assert len(evt_calls) == 1
    finally:
        _remove(path_prefix + "config_crossrefset.cfg")


def test_set_dict_cfg_persist_only_field_with_no_push_callback_registered() -> None:
    # Matches asy_ntp_client.py's real shape today: every field is persist-only, zero setter
    # methods, self._push_callbacks stays the empty dict SensorReaderConfig.__init__ defaults it to.
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_persistonly.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "persistonly", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        results = run(reader._set_dict_cfg({"SampleInterval": 42}, _VAL_SI))
        assert results == {"SampleInterval": "Valid"}
        assert run(reader._get_dict_cfg("Sensor", _VAL_SI)) == {"Sensor": {"SampleInterval": 42}}
    finally:
        _remove(path_prefix + "config_persistonly.cfg")


def test_set_dict_cfg_registered_push_callback_is_invoked_with_the_new_value() -> None:
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_pushed.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "pushed", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        seen: list[int | float | str | bool | None] = []

        async def push(value: "int | float | str | bool | None") -> bool:
            seen.append(value)
            return True

        reader._push_callbacks["SampleInterval"] = push
        results = run(reader._set_dict_cfg({"SampleInterval": 42}, _VAL_SI))
        assert results == {"SampleInterval": "Valid"}
        assert seen == [42]
    finally:
        _remove(path_prefix + "config_pushed.cfg")


def test_set_dict_cfg_push_callback_returning_false_marks_the_field_failed() -> None:
    # Uniform bool setter-return contract: False means the hardware push was rejected. Persist-first still
    # writes the requested value first, but a failed push triggers _recover_failed_push, which corrects the
    # persisted value back to what it was immediately before the request.
    #
    # No getter is registered here, so the pre-write snapshot wins over the schema default; only the
    # underlying persisted value changes, and the reported status stays "Failed" either way.
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_pushfail.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "pushfail", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())

        async def push_ok(_value: "int | float | str | bool | None") -> bool:
            return True

        async def push_fail(_value: "int | float | str | bool | None") -> bool:
            return False

        # Establish a stored value (5) distinct from both the incoming request (42) and the schema
        # default (2), so the assertion below can only pass if the pre-write snapshot rung of the
        # fallback chain is the one actually used.
        reader._push_callbacks["SampleInterval"] = push_ok
        run(_put_flushed(reader, {"SampleInterval": 5}))

        reader._push_callbacks["SampleInterval"] = push_fail
        with WriteCountingOpen(asy_config_manager) as counter:
            results = run(_put_flushed(reader, {"SampleInterval": 42}))
        assert results == {"SampleInterval": "Failed"}
        assert counter.writes == 0  # the recovery restored what the file holds: nothing to write
        assert run(reader._get_dict_cfg("Sensor", _VAL_SI)) == {"Sensor": {"SampleInterval": 5}}
    finally:
        _remove(path_prefix + "config_pushfail.cfg")


def _file_value(path: str) -> object:
    with open(path) as f:
        return json.load(f)


def test_concurrent_puts_keep_the_later_value() -> None:
    # The first PUT's push is held, then fails; a second PUT arrives meanwhile. One PUT per module at a time:
    # the second waits, so the first's recovery can never overwrite the value the second stored.
    path_prefix = _SHARED_CFG_DIR
    path = path_prefix + "config_concurrentputs.cfg"
    _remove(path)
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "concurrentputs", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        gate = asyncio.Event()

        async def push(value: "int | float | str | bool | None") -> bool:
            if value == 42:
                await gate.wait()
                return False
            return True

        reader._push_callbacks["SampleInterval"] = push

        async def scenario() -> "tuple[cm.WriteValidity, cm.WriteValidity]":
            first = asyncio.create_task(reader._set_dict_cfg({"SampleInterval": 42}, _VAL_SI))
            for _ in range(3):
                await asyncio.sleep(0)
            second = asyncio.create_task(reader._set_dict_cfg({"SampleInterval": 77}, _VAL_SI))
            for _ in range(3):
                await asyncio.sleep(0)
            gate.set()
            results = await first, await second
            await reader.cfgmgr.flush_pending()
            return results

        assert run(scenario()) == ({"SampleInterval": "Failed"}, {"SampleInterval": "Valid"})
        assert run(reader.cfgmgr.get_dict(["SampleInterval"])) == {"SampleInterval": 77}
        assert _file_value(path) == {"SampleInterval": 77}
    finally:
        _remove(path)


def test_a_recovery_write_answering_false_prints_and_persists_nothing_of_its_own() -> None:
    # The store that refused the recovery persisted its own entry; the reader only says so on the console.
    class RefusingRecoveryReader(SensorReaderConfig):
        _write_calls = 0

        async def _set_mgr_cfg(self, data: "JsonMapping", cfg_vals: "cm.ConfigSchema") -> "tuple[bool, cm.WriteValidity]":
            self._write_calls += 1
            if self._write_calls == 1:
                return await super()._set_mgr_cfg(data, cfg_vals)
            return False, {}

    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_refusedrecovery.cfg")
    try:
        reader = RefusingRecoveryReader(Meas(20.0, 50), "refusedrecovery", _VAL_SI, max_module_error=3, cfg_path=path_prefix, log=LogConfig(None, 10, 1))
        run(reader.cfgmgr.setup())

        async def push_fail(_value: "int | float | str | bool | None") -> bool:
            return False

        reader._push_callbacks["SampleInterval"] = push_fail
        recorder = _PrintRecorder()
        try:
            results = run(_put_flushed(reader, {"SampleInterval": 42}))
        finally:
            recorder.restore()
        assert results == {"SampleInterval": "Failed"}
        assert reader._write_calls == 2
        assert [line[1:3] for line in recorder.lines if line[0] == "refusedrecovery"] == [("Recovery of", "SampleInterval")]
        assert reader.pr._err_count == 0  # nothing persisted by the reader itself
    finally:
        _remove(path_prefix + "config_refusedrecovery.cfg")


def test_a_successful_push_writes_once_after_it_returned() -> None:
    path_prefix = _SHARED_CFG_DIR
    path = path_prefix + "config_pushthenwrite.cfg"
    _remove(path)
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "pushthenwrite", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        seen: list[int] = []
        with WriteCountingOpen(asy_config_manager) as counter:

            async def push(_value: "int | float | str | bool | None") -> bool:
                for _ in range(3):
                    await asyncio.sleep(0)  # a flush released early would land here
                seen.append(counter.writes)
                return True

            reader._push_callbacks["SampleInterval"] = push
            assert run(_put_flushed(reader, {"SampleInterval": 42})) == {"SampleInterval": "Valid"}
        assert seen == [0]  # nothing written while the push ran
        assert counter.writes == 1
        assert _file_value(path) == {"SampleInterval": 42}
    finally:
        _remove(path)


def test_a_push_that_fails_and_recovers_writes_nothing() -> None:
    path_prefix = _SHARED_CFG_DIR
    path = path_prefix + "config_failrecovernowrite.cfg"
    _remove(path)
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "failrecovernowrite", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())

        async def push_fail(_value: "int | float | str | bool | None") -> bool:
            return False

        reader._push_callbacks["SampleInterval"] = push_fail
        with WriteCountingOpen(asy_config_manager) as counter:
            assert run(_put_flushed(reader, {"SampleInterval": 42})) == {"SampleInterval": "Failed"}
        assert counter.writes == 0  # restored to the schema default the file already holds
        assert _file_value(path) == {"SampleInterval": 2}
    finally:
        _remove(path)


def test_a_put_cancelled_mid_push_still_flushes_its_staged_value() -> None:
    path_prefix = _SHARED_CFG_DIR
    path = path_prefix + "config_cancelledput.cfg"
    _remove(path)
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "cancelledput", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        never = asyncio.Event()

        async def push(_value: "int | float | str | bool | None") -> bool:
            await never.wait()
            return True

        reader._push_callbacks["SampleInterval"] = push

        async def scenario() -> bool:
            put = asyncio.create_task(reader._set_dict_cfg({"SampleInterval": 42}, _VAL_SI))
            for _ in range(3):
                await asyncio.sleep(0)
            put.cancel()
            try:
                await put
            except asyncio.CancelledError:
                pass
            await reader.cfgmgr.flush_pending()
            return reader._set_lock.locked()

        assert run(scenario()) is False  # the cancelled PUT released its lock
        assert _file_value(path) == {"SampleInterval": 42}
    finally:
        _remove(path)


def test_set_dict_cfg_push_callback_raising_marks_the_field_failed_and_logs() -> None:
    # callback is caller-supplied (each module's own bound method) - its runtime behavior isn't
    # statically known, same reasoning as _get_dict_cfg's own callback handling.
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_pushraise.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "pushraise", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())

        async def push(_value: "int | float | str | bool | None") -> bool:
            raise RuntimeError("sensor push failed")

        reader._push_callbacks["SampleInterval"] = push
        run(reader.pr.setup())
        results = run(reader._set_dict_cfg({"SampleInterval": 42}, _VAL_SI))
        assert results == {"SampleInterval": "Failed"}
        assert reader.pr._err_count == 1
    finally:
        _remove(path_prefix + "config_pushraise.cfg")


def test_set_dict_cfg_failed_push_recovers_via_getter_when_registered() -> None:
    # The getter rung (self._get_callbacks) is authoritative when present - it wins over both the
    # pre-write snapshot and the schema default, since it reflects what the sensor actually has
    # right now, the most trustworthy source of truth for what the persisted value should become.
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_pushfailgetter.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "pushfailgetter", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())

        async def push_ok(_value: "int | float | str | bool | None") -> bool:
            return True

        async def push_fail(_value: "int | float | str | bool | None") -> bool:
            return False

        async def getter() -> "int | float | str | bool | None":
            return 99  # distinct from both the pre-write value (5) and the request (42)

        reader._push_callbacks["SampleInterval"] = push_ok
        run(reader._set_dict_cfg({"SampleInterval": 5}, _VAL_SI))

        reader._push_callbacks["SampleInterval"] = push_fail
        reader._get_callbacks["SampleInterval"] = getter
        results = run(reader._set_dict_cfg({"SampleInterval": 42}, _VAL_SI))
        assert results == {"SampleInterval": "Failed"}
        assert run(reader._get_dict_cfg("Sensor", _VAL_SI)) == {"Sensor": {"SampleInterval": 99}}
    finally:
        _remove(path_prefix + "config_pushfailgetter.cfg")


def test_set_dict_cfg_failed_push_falls_back_to_old_value_when_getter_raises() -> None:
    # getter is caller-supplied, same as a push callback - a raising getter must not crash the
    # recovery attempt, just fall through to the next rung (the pre-write snapshot).
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_pushfailgetterraise.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "pushfailgetterraise", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())

        async def push_ok(_value: "int | float | str | bool | None") -> bool:
            return True

        async def push_fail(_value: "int | float | str | bool | None") -> bool:
            return False

        async def bad_getter() -> "int | float | str | bool | None":
            raise RuntimeError("sensor unreadable")

        reader._push_callbacks["SampleInterval"] = push_ok
        run(reader._set_dict_cfg({"SampleInterval": 5}, _VAL_SI))

        reader._push_callbacks["SampleInterval"] = push_fail
        reader._get_callbacks["SampleInterval"] = bad_getter
        results = run(reader._set_dict_cfg({"SampleInterval": 42}, _VAL_SI))
        assert results == {"SampleInterval": "Failed"}
        assert run(reader._get_dict_cfg("Sensor", _VAL_SI)) == {"Sensor": {"SampleInterval": 5}}
    finally:
        _remove(path_prefix + "config_pushfailgetterraise.cfg")


def test_set_dict_cfg_failed_push_getter_returning_out_of_schema_value_falls_through() -> None:
    # A getter reads live, possibly-adversarial hardware state, so its return value is not statically known
    # to satisfy the field's schema. That must be treated like the getter raising: fall through to the next
    # rung, the pre-write snapshot, not persist a value _set_mgr_cfg would itself reject as "Invalid".
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_pushfailgetteroor.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "pushfailgetteroor", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())

        async def push_ok(_value: "int | float | str | bool | None") -> bool:
            return True

        async def push_fail(_value: "int | float | str | bool | None") -> bool:
            return False

        async def oor_getter() -> "int | float | str | bool | None":
            return 99999  # outside _VAL_SI's 1-3600 range - not a valid SampleInterval value

        reader._push_callbacks["SampleInterval"] = push_ok
        run(reader._set_dict_cfg({"SampleInterval": 5}, _VAL_SI))

        reader._push_callbacks["SampleInterval"] = push_fail
        reader._get_callbacks["SampleInterval"] = oor_getter
        results = run(reader._set_dict_cfg({"SampleInterval": 42}, _VAL_SI))
        assert results == {"SampleInterval": "Failed"}
        assert run(reader._get_dict_cfg("Sensor", _VAL_SI)) == {"Sensor": {"SampleInterval": 5}}
    finally:
        _remove(path_prefix + "config_pushfailgetteroor.cfg")


def test_set_dict_cfg_failed_push_getter_returning_coercible_value_is_coerced_before_persisting() -> None:
    # A getter reading real hardware can plausibly hand back an integral float for an int-typed field, so
    # _recover_failed_push's own type_or_range_error() call must coerce it like any other entry point rather
    # than accepting or rejecting on type alone. The coerced int, not the raw float, must be persisted.
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_pushfailgettercoerce.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "pushfailgettercoerce", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())

        async def push_ok(_value: "int | float | str | bool | None") -> bool:
            return True

        async def push_fail(_value: "int | float | str | bool | None") -> bool:
            return False

        async def coercible_getter() -> "int | float | str | bool | None":
            return 99.0  # integral float - not the int SampleInterval's schema declares, but coercible

        reader._push_callbacks["SampleInterval"] = push_ok
        run(reader._set_dict_cfg({"SampleInterval": 5}, _VAL_SI))

        reader._push_callbacks["SampleInterval"] = push_fail
        reader._get_callbacks["SampleInterval"] = coercible_getter
        results = run(reader._set_dict_cfg({"SampleInterval": 42}, _VAL_SI))
        assert results == {"SampleInterval": "Failed"}
        recovered = run(reader._get_dict_cfg("Sensor", _VAL_SI))
        assert recovered == {"Sensor": {"SampleInterval": 99}}
        assert type(recovered["Sensor"]["SampleInterval"]) is int
    finally:
        _remove(path_prefix + "config_pushfailgettercoerce.cfg")


def test_set_dict_cfg_failed_push_on_first_ever_request_recovers_to_schema_default() -> None:
    # No prior successful write and no getter registered - the pre-write snapshot itself is just
    # the freshly-created config's own default, so the fallback chain's last rung (the schema
    # default) is what actually ends up (re)persisted.
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_pushfailfirst.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "pushfailfirst", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())

        async def push_fail(_value: "int | float | str | bool | None") -> bool:
            return False

        reader._push_callbacks["SampleInterval"] = push_fail
        results = run(reader._set_dict_cfg({"SampleInterval": 42}, _VAL_SI))
        assert results == {"SampleInterval": "Failed"}
        assert run(reader._get_dict_cfg("Sensor", _VAL_SI)) == {"Sensor": {"SampleInterval": 2}}
    finally:
        _remove(path_prefix + "config_pushfailfirst.cfg")


def test_set_dict_cfg_failed_push_on_special_alone_field_skips_recovery_entirely() -> None:
    # Mirrors legacy's cmd_keys exclusion from the getter/config/default fallback chain: a command-only
    # field has nothing to persist-correct, never being in ConfigManager's _cache. A getter that raises if
    # called proves the recovery path returns immediately without reaching it.
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_pushfailtrigger.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "pushfailtrigger", _VAL_SPECIAL, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())

        async def push_fail(_value: "int | float | str | bool | None") -> bool:
            return False

        async def must_not_be_called() -> "int | float | str | bool | None":
            raise AssertionError("getter must never be called for a special-alone field")

        reader._push_callbacks["Trigger"] = push_fail
        reader._get_callbacks["Trigger"] = must_not_be_called
        results = run(reader._set_dict_cfg({"Trigger": True}, _VAL_SPECIAL))
        assert results == {"Trigger": "Failed"}
    finally:
        _remove(path_prefix + "config_pushfailtrigger.cfg")


def test_set_dict_cfg_special_alone_field_write_never_logs_a_spurious_config_read_error() -> None:
    # Real finding (2026-09-08, real bench hardware): a command-only/special-alone field is never in
    # ConfigManager's _cache, since setup() skips it as "not used for storage".
    #
    # _set_dict_cfg()'s pre-write old-value snapshot used to fetch it anyway, hitting get_dict()'s KeyError
    # path and logging one spurious CFGMGR_<name> errno=8 on every single write to such a field -
    # deterministic, one new entry per isolated PUT, not the race it was first mistaken for.
    #
    # Wasted work too: _recover_failed_push(), the only consumer of old_values, already skips a special-
    # alone field. Fixed by filtering the snapshot fetch to genuinely persisted keys, with the same schema-
    # derived check _recover_failed_push() applies at the point of use.
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_specialnospuriouserr.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "specialnospuriouserr", _VAL_SPECIAL, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())

        async def push_ok(_value: "int | float | str | bool | None") -> bool:
            return True

        reader._push_callbacks["Trigger"] = push_ok
        # A fresh special-alone-only schema's setup() persists nothing: no file is written, a console line says why.
        err_count_before = reader.cfgmgr.pr._err_count
        assert err_count_before == 0
        results = run(reader._set_dict_cfg({"Trigger": True}, _VAL_SPECIAL))
        assert results == {"Trigger": "Valid"}
        assert reader.cfgmgr.pr._err_count == err_count_before  # the real bug: this used to increase by 1 on every single call
    finally:
        _remove(path_prefix + "config_specialnospuriouserr.cfg")


def test_set_dict_cfg_mixed_persisted_and_special_alone_fields_in_one_request() -> None:
    # Coverage gap in the fix above: a request combining a genuinely persisted field with a special-alone
    # one must filter per field, not treat the whole request as one shape.
    #
    # Proves in one call what the dedicated special-alone test and the SampleInterval-only old-value tests
    # each only prove in isolation: the special-alone field still logs no spurious error, and the persisted
    # field's old-value snapshot is still fetched and used for real push-failure recovery.
    combined = _VAL_SI + _VAL_SPECIAL
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_mixedpersistedspecial.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "mixedpersistedspecial", combined, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())

        async def push_ok(_value: "int | float | str | bool | None") -> bool:
            return True

        async def push_fail(_value: "int | float | str | bool | None") -> bool:
            return False

        # Establish a known old value (5) for SampleInterval via one successful write first.
        reader._push_callbacks["SampleInterval"] = push_ok
        reader._push_callbacks["Trigger"] = push_ok
        run(reader._set_dict_cfg({"SampleInterval": 5}, combined))
        err_count_before = reader.cfgmgr.pr._err_count

        # Now both fields fail their push in the same request - SampleInterval must recover to its
        # real old value (5, not the new 42), Trigger must just report "Failed" with no recovery
        # attempt and no spurious config-read error logged for either field.
        reader._push_callbacks["SampleInterval"] = push_fail
        reader._push_callbacks["Trigger"] = push_fail
        results = run(reader._set_dict_cfg({"SampleInterval": 42, "Trigger": True}, combined))
        assert results == {"SampleInterval": "Failed", "Trigger": "Failed"}
        # Read back with _VAL_SI alone, matching real usage, where get_dict_cfg() excludes a special-alone
        # field from the schema it reads with. _get_dict_cfg() does no filtering of its own, so including
        # Trigger would exercise a separate, pre-existing characteristic.
        assert run(reader._get_dict_cfg("Sensor", _VAL_SI)) == {"Sensor": {"SampleInterval": 5}}
        assert reader.cfgmgr.pr._err_count == err_count_before
    finally:
        _remove(path_prefix + "config_mixedpersistedspecial.cfg")


def test_set_dict_cfg_old_value_snapshot_read_exception_falls_back_to_default() -> None:
    # _get_mgr_cfg is the same overridable extension point _get_dict_cfg already defends against -
    # _set_dict_cfg's own pre-write snapshot read gets identical defense: a raising override must
    # not crash the whole call, just degrade the fallback chain straight to the schema default.
    class RaisingGetMgrCfgReader(SensorReaderConfig):
        async def _get_mgr_cfg(self, _cfg: "list[str]") -> "dict[str, int | float | str | bool | None] | None":
            raise RuntimeError("simulated read failure")

    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_pushfailsnapraise.cfg")
    try:
        reader = RaisingGetMgrCfgReader(Meas(20.0, 50), "pushfailsnapraise", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())

        async def push_fail(_value: "int | float | str | bool | None") -> bool:
            return False

        reader._push_callbacks["SampleInterval"] = push_fail
        results = run(reader._set_dict_cfg({"SampleInterval": 42}, _VAL_SI))
        assert results == {"SampleInterval": "Failed"}
        assert reader.pr._err_count >= 1  # the snapshot-read failure was logged, not silently swallowed
        # _get_dict_cfg would hit the same raising override, so verify directly against the real
        # ConfigManager instead of through the reader's own (overridden) getter path.
        assert run(reader.cfgmgr.get_dict(["SampleInterval"])) == {"SampleInterval": 2}
    finally:
        _remove(path_prefix + "config_pushfailsnapraise.cfg")


def test_recover_failed_push_unknown_key_is_a_defensive_noop() -> None:
    # Unreachable via _set_dict_cfg's normal flow, where a key only reaches _recover_failed_push after being
    # validated present in cfg_vals, but exercised directly like this file's other "shouldn't happen"
    # branches - proving the defensive early return holds, not just that it is never hit in practice.
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_recoverunknown.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "recoverunknown", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        run(reader._recover_failed_push("NoSuchField", {}, _VAL_SI, fields=schema_dict(_VAL_SI)))  # must not raise
    finally:
        _remove(path_prefix + "config_recoverunknown.cfg")


def test_set_dict_cfg_recover_failed_push_correction_write_exception_is_caught() -> None:
    # _set_mgr_cfg is the same overridable extension point _set_dict_cfg's initial persist call already
    # defends against, and the correction write inside _recover_failed_push needs the same defense: a second
    # call that raises, where the initial persist succeeded, must not crash the whole request.
    class FlakyOnSecondWriteReader(SensorReaderConfig):
        # Class attribute instead of an __init__ override that only forwards *args/**kwargs to
        # super(): the first `+= 1` below rebinds it per instance, so the counter behaves
        # identically without a signature this file would have to restate (and mistype) verbatim.
        _write_calls = 0

        async def _set_mgr_cfg(
            self, data: "JsonMapping", cfg_vals: "cm.ConfigSchema",
        ) -> "tuple[bool, cm.WriteValidity]":
            self._write_calls += 1
            if self._write_calls == 1:
                return await super()._set_mgr_cfg(data, cfg_vals)
            raise RuntimeError("simulated correction-write failure")

    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_pushfailcorrectionraise.cfg")
    try:
        reader = FlakyOnSecondWriteReader(Meas(20.0, 50), "pushfailcorrectionraise", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())

        async def push_fail(_value: "int | float | str | bool | None") -> bool:
            return False

        reader._push_callbacks["SampleInterval"] = push_fail
        results = run(reader._set_dict_cfg({"SampleInterval": 42}, _VAL_SI))
        assert results == {"SampleInterval": "Failed"}
        assert reader.pr._err_count >= 1
    finally:
        _remove(path_prefix + "config_pushfailcorrectionraise.cfg")


def test_set_dict_cfg_multiple_fields_recover_independently_via_different_rungs() -> None:
    # Two fields in one request, both pushes failing, each resolving through a different fallback rung - so
    # the recovery chain is genuinely per-field independent, not merely correct for one isolated failure.
    # This file's "multiple invalid fields" shape, applied to recovery rather than validation.
    combined = _VAL_SI + _VAL_BOOL
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_pushfailmulti.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "pushfailmulti", combined, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())

        async def push_ok(_value: "int | float | str | bool | None") -> bool:
            return True

        async def push_fail(_value: "int | float | str | bool | None") -> bool:
            return False

        async def getter() -> "int | float | str | bool | None":
            return 77  # distinct from both the pre-write value (5) and the request (99)

        # Establish distinct pre-write values for both fields.
        reader._push_callbacks["SampleInterval"] = push_ok
        reader._push_callbacks["SelfCal"] = push_ok
        run(reader._set_dict_cfg({"SampleInterval": 5, "SelfCal": True}, combined))

        # SampleInterval has a getter registered (wins); SelfCal doesn't (falls to the pre-write
        # snapshot, True).
        reader._push_callbacks["SampleInterval"] = push_fail
        reader._push_callbacks["SelfCal"] = push_fail
        reader._get_callbacks["SampleInterval"] = getter
        results = run(reader._set_dict_cfg({"SampleInterval": 99, "SelfCal": False}, combined))
        assert results == {"SampleInterval": "Failed", "SelfCal": "Failed"}
        assert run(reader._get_dict_cfg("Sensor", combined)) == {
            "Sensor": {"SampleInterval": 77, "SelfCal": True},
        }
    finally:
        _remove(path_prefix + "config_pushfailmulti.cfg")


def test_set_dict_cfg_invalid_value_is_reported_and_never_pushed() -> None:
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_invalidnopush.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "invalidnopush", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        called = False

        async def push(_value: "int | float | str | bool | None") -> bool:
            nonlocal called
            called = True
            return True

        reader._push_callbacks["SampleInterval"] = push
        results = run(reader._set_dict_cfg({"SampleInterval": 9999}, _VAL_SI))  # out of [1, 3600]
        assert results == {"SampleInterval": "Invalid"}
        assert called is False
        assert run(reader._get_dict_cfg("Sensor", _VAL_SI)) == {"Sensor": {"SampleInterval": 2}}  # untouched default
    finally:
        _remove(path_prefix + "config_invalidnopush.cfg")


def test_set_dict_cfg_unchanged_value_is_reported_and_never_pushed() -> None:
    # No generic force-resend semantics: an unchanged value is a no-op for the hardware, matching
    # the legacy pipeline's own default (set_sensor_value only pushes on prev_updated or force=True).
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_unchangednopush.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "unchangednopush", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        called = False

        async def push(_value: "int | float | str | bool | None") -> bool:
            nonlocal called
            called = True
            return True

        reader._push_callbacks["SampleInterval"] = push
        results = run(reader._set_dict_cfg({"SampleInterval": 2}, _VAL_SI))  # 2 is the schema default already
        assert results == {"SampleInterval": "Unchanged"}
        assert called is False
    finally:
        _remove(path_prefix + "config_unchangednopush.cfg")


def test_set_dict_cfg_unknown_key_is_reported_invalid_individually_not_whole_request() -> None:
    # (owner, 2026-09-26): an unrecognized key is just another per-field "Invalid" outcome
    # (matching ConfigManager.write_config's own existing per-key tolerance) - it does not
    # invalidate the rest of a multi-field request.
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_unknownkey.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "unknownkey", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        results = run(reader._set_dict_cfg({"SampleInterval": 42, "NoSuchField": 1}, _VAL_SI))
        assert results == {"SampleInterval": "Valid", "NoSuchField": "Invalid"}
        assert run(reader._get_dict_cfg("Sensor", _VAL_SI)) == {"Sensor": {"SampleInterval": 42}}
    finally:
        _remove(path_prefix + "config_unknownkey.cfg")


def test_set_dict_cfg_multi_field_request_reports_each_field_independently() -> None:
    combined = _VAL_SI + _VAL_BOOL
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_multifield.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "multifield", combined, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        pushed: list[str] = []

        async def push_bool(_value: "int | float | str | bool | None") -> bool:
            pushed.append("SelfCal")
            return True

        reader._push_callbacks["SelfCal"] = push_bool
        results = run(reader._set_dict_cfg({"SampleInterval": 9999, "SelfCal": True}, combined))
        assert results == {"SampleInterval": "Invalid", "SelfCal": "Valid"}
        assert pushed == ["SelfCal"]
    finally:
        _remove(path_prefix + "config_multifield.cfg")


def test_set_dict_cfg_multiple_invalid_fields_neither_pushed() -> None:
    # Multiple simultaneously-invalid fields, each with its own registered push callback: confirms per-field
    # independence holds through the push layer too, not only the persist layer test_asy_config_manager.py
    # covers. Neither invalid field's callback fires, and both are left at their untouched defaults.
    combined = _VAL_SI + _VAL_BOOL
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_multiinvalid.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "multiinvalid", combined, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        pushed: list[str] = []

        async def push_int(_value: "int | float | str | bool | None") -> bool:
            pushed.append("SampleInterval")
            return True

        async def push_bool(_value: "int | float | str | bool | None") -> bool:
            pushed.append("SelfCal")
            return True

        reader._push_callbacks["SampleInterval"] = push_int
        reader._push_callbacks["SelfCal"] = push_bool
        results = run(reader._set_dict_cfg({"SampleInterval": 9999, "SelfCal": "not a bool"}, combined))
        assert results == {"SampleInterval": "Invalid", "SelfCal": "Invalid"}
        assert pushed == []
        assert run(reader._get_dict_cfg("Sensor", combined)) == {"Sensor": {"SampleInterval": 2, "SelfCal": False}}
    finally:
        _remove(path_prefix + "config_multiinvalid.cfg")


def test_set_dict_cfg_whole_persist_failure_marks_every_field_failed() -> None:
    # A genuinely invalid ConfigManager (e.g. malformed schema) makes write_config() itself return
    # (False, {}) - every key in the request comes back "Failed", not silently dropped or "Invalid"
    # (which would misleadingly suggest the values themselves were the problem).
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_wholefail.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "wholefail", (), max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        assert reader.cfgmgr.valid is False
        results = run(reader._set_dict_cfg({"SampleInterval": 42, "Other": 1}, ()))
        assert results == {"SampleInterval": "Failed", "Other": "Failed"}
    finally:
        _remove(path_prefix + "config_wholefail.cfg")


def test_set_dict_cfg_set_mgr_cfg_override_raising_marks_every_field_failed() -> None:
    # _set_mgr_cfg is an overridable extension point (mirrors _get_mgr_cfg) - the call itself,
    # not just its result, could misbehave on a misbehaving subclass override.
    class RaisingSetMgrCfgReader(SensorReaderConfig):
        async def _set_mgr_cfg(
            self, _data: "JsonMapping", _cfg_vals: "cm.ConfigSchema",
        ) -> "tuple[bool, cm.WriteValidity]":
            raise RuntimeError("simulated persistence failure")

    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_raisingmgr.cfg")
    try:
        reader = RaisingSetMgrCfgReader(Meas(20.0, 50), "raisingmgr", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        results = run(reader._set_dict_cfg({"SampleInterval": 42}, _VAL_SI))
        assert results == {"SampleInterval": "Failed"}
        assert reader.pr._err_count == 1
    finally:
        _remove(path_prefix + "config_raisingmgr.cfg")


def test_set_dict_cfg_set_mgr_cfg_override_malformed_result_marks_every_field_failed() -> None:
    # Same defensive posture as the raising-override test above, for the other way a misbehaving override
    # can fail: returning successfully but with a "results" that is not the WriteValidity dict the rest of
    # _set_dict_cfg assumes - results.get(key) would otherwise raise AttributeError, uncaught.
    class MalformedSetMgrCfgReader(SensorReaderConfig):
        async def _set_mgr_cfg(
            self, _data: "JsonMapping", _cfg_vals: "cm.ConfigSchema",
        ) -> "tuple[bool, cm.WriteValidity]":
            return True, "not a dict"  # type: ignore[return-value]  # deliberately malformed, simulating a misbehaving override

    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_malformedmgr.cfg")
    try:
        reader = MalformedSetMgrCfgReader(Meas(20.0, 50), "malformedmgr", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        results = run(reader._set_dict_cfg({"SampleInterval": 42}, _VAL_SI))
        assert results == {"SampleInterval": "Failed"}
        assert reader.pr._err_count == 1
    finally:
        _remove(path_prefix + "config_malformedmgr.cfg")


def test_set_dict_cfg_set_mgr_cfg_override_missing_key_marks_it_failed() -> None:
    # A third malformed-override shape, after raising and returning a non-dict: the override reports
    # persisted=True with a real dict that is simply missing a key the caller asked about. The real
    # ConfigManager-backed _set_mgr_cfg never does this, but a subclass override could.
    #
    # Without a fallback that key would silently vanish from the returned dict instead of being reported,
    # breaking the "every field reported independently" contract.
    class MissingKeySetMgrCfgReader(SensorReaderConfig):
        async def _set_mgr_cfg(
            self, _data: "JsonMapping", _cfg_vals: "cm.ConfigSchema",
        ) -> "tuple[bool, cm.WriteValidity]":
            return True, {}  # reports success but never mentions any of the requested keys

    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_missingkeymgr.cfg")
    try:
        reader = MissingKeySetMgrCfgReader(Meas(20.0, 50), "missingkeymgr", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        results = run(reader._set_dict_cfg({"SampleInterval": 42}, _VAL_SI))
        assert results == {"SampleInterval": "Failed"}
    finally:
        _remove(path_prefix + "config_missingkeymgr.cfg")


def test_set_dict_cfg_empty_data_returns_empty_result() -> None:
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_emptyset.cfg")
    try:
        reader = SensorReaderConfig(Meas(20.0, 50), "emptyset", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader.cfgmgr.setup())
        assert run(reader._set_dict_cfg({}, _VAL_SI)) == {}
    finally:
        _remove(path_prefix + "config_emptyset.cfg")


def test_set_dict_cfg_push_callbacks_default_to_empty_and_are_per_instance() -> None:
    # Registered once per instance at construction time (agent, 2026-08-03), never shared/leaked
    # across two separate instances of the same class.
    path_prefix = _SHARED_CFG_DIR
    _remove(path_prefix + "config_percallback1.cfg")
    _remove(path_prefix + "config_percallback2.cfg")
    try:
        reader1 = SensorReaderConfig(Meas(20.0, 50), "percallback1", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader1.cfgmgr.setup())
        reader2 = SensorReaderConfig(Meas(20.0, 50), "percallback2", _VAL_SI, max_module_error=3, cfg_path=path_prefix)
        run(reader2.cfgmgr.setup())
        assert reader1._push_callbacks == {}
        assert reader1._push_callbacks is not reader2._push_callbacks
        plain = SensorReader(Meas(20.0, 50), "", max_module_error=3)  # the dicts live on the base class
        assert (plain._push_callbacks, plain._get_callbacks) == ({}, {})

        async def push(_value: "int | float | str | bool | None") -> bool:
            return True

        reader1._push_callbacks["SampleInterval"] = push
        assert reader2._push_callbacks == {}
    finally:
        _remove(path_prefix + "config_percallback1.cfg")
        _remove(path_prefix + "config_percallback2.cfg")


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
