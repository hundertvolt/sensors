import asyncio
import asyncio.core as asyncio_core  # type: ignore[import-not-found]  # asyncio's own context dict, read back below
import gc
import os
import sys
import time

import machine
import micropython
from _error_codes import code
from _fram_chip_fake import FakeMB85RS64V
from _tmp_scratch import TmpScratch
from _write_counters import WriteCountingOpen
from machine import Timer

# Same one-process-per-test-file swap as test_asy_base_classes.py/test_asy_fram_manager.py.
import asy_base_classes
import asy_config_manager as cm
import asy_print_log
import asy_spi_driver
import asy_system_service
from asy_fram_manager import FRAMManager
from asy_print_log import DEFAULT_LOG, LogConfig, PrintLogHistory, PrintLogHistoryStore
from asy_spi_driver import SPI
from asy_system_service import BOOT_CONSTRUCTION, BOOT_DONE, BOOT_NTP, SystemService, begin_boot, write_reset_record

asy_spi_driver._SPI = FakeMB85RS64V  # type: ignore[misc]

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from asyncio.events import _Context, _ExceptionHandler
    from collections.abc import Callable, Coroutine
    from typing import Any, TypeVar

    from machine import WDT
    from typing_extensions import Self

    T = TypeVar("T")

# @tunable l1.system_service_run_bound_s = 5
_RUN_BOUND_S = 5
_SRC = "src/asy_system_service.py"
# The documented DebugLevel numbers (SPECIFICATION.md Part A.8): 0 off, 1 errors, 2 warnings, 3 once, 4 events, 5 all.
_ERR, _WARN, _EVENT, _ALL = 1, 2, 4, 5


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


def _src_const(name: str) -> int:
    # The shipped value, read from the source: a private const() is not a module attribute on MicroPython.
    with open(_SRC) as f:
        for line in f:
            if line.startswith(name + " = const("):
                return int(line.split("const(", 1)[1].split(")", 1)[0], 0)
    raise AssertionError(name + " not found in " + _SRC)


def make_ntp_stub(
    *, synced: bool = False, raise_exc: "Exception | None" = None,
) -> "tuple[Callable[[], Coroutine[Any, Any, bool]], list[int]]":
    calls = [0]

    async def _ntp() -> bool:
        calls[0] += 1
        if raise_exc is not None:
            raise raise_exc
        return synced

    return _ntp, calls


def make_service(  # keywords mirror SystemService.__init__()'s own
    ntp: "Callable[[], Coroutine[Any, Any, bool]] | None" = None,
    *,
    watchdog: "WDT | None" = None,
    storage: "FRAMManager | None" = None,
    log: "LogConfig" = DEFAULT_LOG,
    cfg_path: str = "",
    level_setters: "Callable[[], list[Callable[[int], bool]]] | None" = None,
    config_stores: "Callable[[], list[cm.ConfigManager]] | None" = None,
    reset_reason: int = 0,
) -> SystemService:
    if ntp is None:
        ntp, _calls = make_ntp_stub(synced=False)
    return SystemService(
        ntp, watchdog=watchdog, storage=storage, level_setters=level_setters, config_stores=config_stores,
        reset_reason=reset_reason, cfg_path=cfg_path, log=log,
    )


def make_fram_manager(max_size: int = 0x2000) -> "tuple[FRAMManager, FakeMB85RS64V]":
    bus = SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    manager = FRAMManager(bus, 1, max_size=max_size)
    chip = manager.fram._spidev.spi._spi
    assert isinstance(chip, FakeMB85RS64V)
    return manager, chip


def _same_chip_manager(chip: FakeMB85RS64V) -> FRAMManager:
    # A fresh manager over the same chip image: models a reboot, the allocation sequence replayed.
    manager, _chip = make_fram_manager()
    manager.fram._spidev.spi._spi = chip
    run(manager.setup())
    return manager


_TICKS_PERIOD = 1 << 30  # rp2's ticks_ms() wrap: py/mpconfig.h's MICROPY_PY_TIME_TICKS_PERIOD on a 32-bit small int


class _Clock:
    # A driven ticks_ms() source installed as `time` in the modules that read it; every other name reaches the real
    # module, unless `strict`, where the wall-clock reads raise (no RTC, time() or NTP value may be read).
    def __init__(self, *, strict: bool = False) -> None:
        self.now = 1000
        self._strict = strict
        self._saved = (asy_base_classes.time, asy_system_service.time)

    def ticks_ms(self) -> int:
        return self.now

    def ticks_add(self, a: int, b: int) -> int:
        return (a + b) & (_TICKS_PERIOD - 1)

    def ticks_diff(self, a: int, b: int) -> int:
        return ((a - b + _TICKS_PERIOD // 2) & (_TICKS_PERIOD - 1)) - _TICKS_PERIOD // 2

    def advance(self, ms: int) -> None:
        self.now = self.ticks_add(self.now, ms)

    def __getattr__(self, name: str) -> object:
        if self._strict and name in ("gmtime", "mktime", "time", "localtime"):
            raise AssertionError("the wall clock was read: time." + name)
        return getattr(time, name)

    def __enter__(self) -> "Self":
        asy_base_classes.time = self  # type: ignore[assignment]
        asy_system_service.time = self  # type: ignore[assignment]
        return self

    def __exit__(self, *exc_info: object) -> None:
        asy_base_classes.time, asy_system_service.time = self._saved


async def _pump(flag: "asyncio.ThreadSafeFlag", ticks: int, clock: "_Clock | None" = None, step_ms: int = 1000, settle: int = 5) -> None:
    # Drives a ThreadSafeFlag-gated loop forward `ticks` times, the driven clock advanced `step_ms` before each wake-up;
    # `settle` extra yields per tick let every await point of one loop iteration resolve before the next.
    for _ in range(ticks):
        if clock is not None:
            clock.advance(step_ms)
        flag.set()
        for _ in range(settle):
            await asyncio.sleep(0)


async def _cancel(task: "asyncio.Task[Any]") -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


class _FastAsyncSleep:
    # Makes asyncio.sleep()/sleep_ms() one yield each, so a supervisor pass or a fallback pass costs no real time;
    # with a clock, each sleep also advances it by the slept time. Restored however the block exits.
    def __init__(self, clock: "_Clock | None" = None) -> None:
        self._clock = clock

    def __enter__(self) -> "Self":
        self._real_sleep = asyncio.sleep
        self._real_sleep_ms = asyncio.sleep_ms
        clock = self._clock
        real_sleep = self._real_sleep

        async def _fast(seconds: float) -> None:
            if clock is not None:
                clock.advance(int(seconds * 1000))
            await real_sleep(0)

        async def _fast_ms(ms: int) -> None:
            if clock is not None:
                clock.advance(ms)
            await real_sleep(0)

        asyncio.sleep = _fast  # type: ignore[assignment]  # deliberate monkeypatch, not a real caller mismatch
        asyncio.sleep_ms = _fast_ms  # type: ignore[assignment]  # likewise, for the millisecond form
        return self

    def __exit__(self, *exc_info: object) -> None:
        asyncio.sleep = self._real_sleep
        asyncio.sleep_ms = self._real_sleep_ms


class _RaiseOnArm:
    # Toggles tests/machine.py's shared Timer.raise_on_arm for the `with` block, simulating real rp2 alarm-
    # pool exhaustion from Timer.init(); `exc` picks OSError(ENOMEM) or MemoryError, neither of which is
    # the other's subclass (Part F), so each guard is proven against both.
    def __init__(self, exc: "type[BaseException]" = OSError) -> None:
        self._exc = exc

    def __enter__(self) -> "Self":
        Timer.raise_on_arm_exc = self._exc
        Timer.raise_on_arm = True
        return self

    def __exit__(self, *exc_info: object) -> None:
        Timer.raise_on_arm = False
        Timer.raise_on_arm_exc = OSError


class _PrintRecorder:
    # Shadows print() inside asy_print_log only, where every logger line is printed.
    def __init__(self) -> None:
        self.lines: list[tuple[object, ...]] = []
        asy_print_log.print = self  # type: ignore[attr-defined]

    def __call__(self, *args: object, **_kwargs: object) -> None:
        self.lines.append(args)

    def restore(self) -> None:
        del asy_print_log.print  # type: ignore[attr-defined]


def _persisted(log_owner: "SystemService | PrintLogHistory") -> "list[int]":
    # A history's used slots, oldest first ("N" marks an unused one); warnings carry their W number.
    pr = log_owner.pr if isinstance(log_owner, SystemService) else log_owner
    log = run(pr.get_log())[pr.name]
    return [log["ErrNum"][i] for i in range(len(log["ErrNum"])) if log["ErrType"][i] != "N"]


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


def test_init_uses_in_memory_logging_when_fram_is_none() -> None:
    svc = make_service()
    assert isinstance(svc.pr, PrintLogHistory)
    assert svc._storage_pause is None
    assert svc.pr.name == "SYSTEM"  # baked in via make_logger(), not left empty


def test_init_uses_fram_backed_logging_and_wires_storage_pause_when_fram_given() -> None:
    manager, _chip = make_fram_manager()
    svc = make_service(storage=manager, log=LogConfig(manager, 10, None))
    assert isinstance(svc.pr, PrintLogHistoryStore)
    assert isinstance(svc.cfgmgr.pr, PrintLogHistoryStore)  # the settings store's logger shares the log config
    assert svc._storage_pause is not None
    assert svc.pr.name == "SYSTEM"
    # Bound-method identity isn't guaranteed (each attribute access can mint a fresh bound-method
    # object) - confirm by behavior instead: calling svc._storage_pause must reach manager's own state.
    svc._storage_pause(value=True)
    assert manager.get_pause() is True
    svc._storage_pause(value=False)
    assert manager.get_pause() is False


def test_init_debug_level_is_forwarded_to_the_logger() -> None:
    svc = make_service(log=LogConfig(None, 10, _ERR))
    assert svc.pr.level == _ERR
    assert svc.cfgmgr.pr.level == _ERR  # CFGMGR_SYSTEM takes the same config


def test_init_history_length_is_forwarded() -> None:
    svc = make_service(log=LogConfig(None, 3, None))
    assert len(svc.pr.history) == 3
    assert len(svc.cfgmgr.pr.history) == 3


def test_init_storage_without_a_fram_log_keeps_ram_logging_and_the_pause() -> None:
    # storage= is only the pause target; whether SYSTEM logs into FRAM is the log config's choice alone.
    manager, _chip = make_fram_manager()
    svc = make_service(storage=manager)
    assert type(svc.pr) is PrintLogHistory
    assert svc._storage_pause is not None
    svc._storage_pause(value=True)
    assert manager.get_pause() is True


def test_init_watchdog_is_stored() -> None:
    wdt = machine.WDT()
    svc = make_service(watchdog=wdt)
    assert svc._watchdog is wdt


def test_init_without_watchdog_defaults_to_none() -> None:
    svc = make_service()
    assert svc._watchdog is None


def test_init_keeps_the_reset_reason_it_is_given() -> None:
    assert make_service().get_reset_reason() == _src_const("_RR_UNKNOWN")
    assert make_service(reset_reason=12).get_reset_reason() == 12


def test_init_zero_history_length_is_accepted_in_memory() -> None:
    # Unusual-but-typing-valid content: 0 is a legal int, not just the documented default of 10.
    svc = make_service(log=LogConfig(None, 0, None))
    assert len(svc.pr.history) == 0
    run(svc.pr.setup())
    run(svc.pr.err_s("boom", errno=1))  # must not raise despite there being nowhere to store it
    assert svc.pr._err_count == 1


def test_init_negative_history_length_is_clamped_to_zero() -> None:
    # asy_print_log.py's own PrintLogHistory clamps this; asy_system_service.py passes it through unmodified.
    svc = make_service(log=LogConfig(None, -5, None))
    assert len(svc.pr.history) == 0


def test_init_all_constructor_params_combined_wire_correctly() -> None:
    # Cross-dependency: fram + watchdog + history_length + debug all set together, not just each in isolation.
    manager, _chip = make_fram_manager()
    wdt = machine.WDT()
    svc = make_service(storage=manager, watchdog=wdt, log=LogConfig(manager, 4, _ALL))
    assert isinstance(svc.pr, PrintLogHistoryStore)
    assert svc._storage_pause is not None
    assert svc._watchdog is wdt
    assert len(svc.pr.history) == 4
    assert svc.pr.level == _ALL


# ---------------------------------------------------------------------------
# feed_watchdog() - the one no-op-safe watchdog access point (SPECIFICATION.md Part G.2)
# ---------------------------------------------------------------------------


def test_feed_watchdog_feeds_a_real_watchdog() -> None:
    wdt = machine.WDT()
    svc = make_service(watchdog=wdt)
    svc.feed_watchdog()
    assert wdt.feed_count == 1
    svc.feed_watchdog()
    assert wdt.feed_count == 2


def test_feed_watchdog_is_a_silent_no_op_without_a_watchdog() -> None:
    # A watchdog-less build takes the identical code path, no special-casing at the call site.
    svc = make_service()
    assert svc._watchdog is None
    svc.feed_watchdog()  # must not raise


def test_feed_watchdog_stops_once_force_watchdog_starve_latches() -> None:
    # _force_watchdog_starve is the one-way "let the hardware watchdog do it" signal: set when a reset cannot be
    # armed or the supervisor escalates - feed_watchdog() honours it even with a real watchdog present.
    wdt = machine.WDT()
    svc = make_service(watchdog=wdt)
    svc._force_watchdog_starve = True
    svc.feed_watchdog()
    assert wdt.feed_count == 0


# ---------------------------------------------------------------------------
# Uptime and the boot signature: measured ticks, driven by the fake clock
# ---------------------------------------------------------------------------


def test_get_uptime_initial_value_is_zero_before_status_counter_runs() -> None:
    with _Clock():
        svc = make_service()
        assert run(svc.get_uptime()) == 0


def test_get_boot_signature_initial_value_before_status_counter_runs() -> None:
    svc = make_service()
    assert run(svc.get_boot_signature()) is None  # LockedValue(init_value=None)'s own default


def test_ntp_boot_signature_not_synced_returns_none() -> None:
    ntp, _calls = make_ntp_stub(synced=False)
    svc = make_service(ntp)
    assert run(svc._ntp_boot_signature()) is None
    assert svc.pr._err_count == 0


def test_ntp_boot_signature_synced_returns_a_real_utc_timestamp() -> None:
    ntp, _calls = make_ntp_stub(synced=True)
    svc = make_service(ntp)
    asy_base_classes.set_utc_valid()
    try:
        result = run(svc._ntp_boot_signature())
    finally:
        asy_base_classes.set_utc_valid(valid=False)
    assert isinstance(result, int)
    assert result > 1_700_000_000  # sanity bound: after 2023-11-14, not the pre-refactor's magic -1/1
    assert svc.pr._err_count == 0


def test_a_synced_signature_reads_utc_now() -> None:
    # The signature is the shared UTC primitive's value: None while the clock is not marked valid,
    # even with NTP reporting synced, and utc_now() itself once it is.
    ntp, _calls = make_ntp_stub(synced=True)
    svc = make_service(ntp)
    assert run(svc._ntp_boot_signature()) is None
    original = asy_base_classes.utc_now
    asy_system_service.utc_now = lambda: 1_790_000_000
    try:
        assert run(svc._ntp_boot_signature()) == 1_790_000_000
    finally:
        asy_system_service.utc_now = original
    assert svc.pr._err_count == 0


def test_a_32_bit_signature_round_trips() -> None:
    # The signature is an identifier, never stepped: a LockedValue, so no counter cap clamps it.
    svc = make_service()
    run(svc._boot_signature.set_value(1_790_000_000))
    assert run(svc.get_boot_signature()) == 1_790_000_000
    run(svc._boot_signature.set_value(0xFFFFFFFF))  # a random signature uses the full 32 bits
    assert run(svc.get_boot_signature()) == 0xFFFFFFFF


def test_ntp_boot_signature_callback_exception_returns_none_and_logs_once() -> None:
    ntp, calls = make_ntp_stub(raise_exc=RuntimeError("ntp callback exploded"))
    svc = make_service(ntp)
    assert run(svc._ntp_boot_signature()) is None
    assert calls[0] == 1
    assert svc.pr._err_count == 1
    assert _persisted(svc) == [code("E", "CALLBACK")]


def _run_status_loop(svc: SystemService, clock: _Clock, ticks: int) -> "tuple[bool, int | float | None, int]":
    # Runs the status loop over `ticks` driven seconds; answers (signature resolved, signature, uptime).
    async def scenario() -> "tuple[bool, int | float | None, int]":
        task = asyncio.create_task(svc._status_loop())
        await _pump(svc._uptime_event, ticks, clock)
        result = (svc._start_time_set, await svc.get_boot_signature(), await svc.get_uptime())
        await _cancel(task)
        return result

    return run(scenario())


def test_status_counter_reads_one_second_of_uptime_per_driven_second() -> None:
    with _Clock() as clock:
        svc = make_service()
        assert _run_status_loop(svc, clock, 5)[2] == 5  # five pumps of 1000 ms each


def test_status_counter_sets_boot_signature_via_ntp_once_synced() -> None:
    ntp, _calls = make_ntp_stub(synced=True)
    asy_base_classes.set_utc_valid()
    try:
        with _Clock() as clock:
            svc = make_service(ntp)
            start_time_set, signature, _uptime = _run_status_loop(svc, clock, 1)
    finally:
        asy_base_classes.set_utc_valid(valid=False)
    assert start_time_set is True
    assert signature is not None
    assert signature > 1_700_000_000


def test_status_counter_before_wait_time_never_synced_leaves_boot_signature_unresolved() -> None:
    with _Clock() as clock:
        svc = make_service()
        start_time_set, signature, _uptime = _run_status_loop(svc, clock, 5)  # well below _NTP_WAIT_TIME (120)
    assert start_time_set is False
    assert signature is None  # _status_loop's own "not yet resolved" sentinel


def test_status_counter_falls_back_to_random_after_wait_time_when_never_synced() -> None:
    with _Clock() as clock:
        svc = make_service()
        start_time_set, signature, uptime = _run_status_loop(svc, clock, _src_const("_NTP_WAIT_TIME"))  # exactly _NTP_WAIT_TIME - boundary is accepted, not rejected
    assert (start_time_set, uptime) == (True, 120)
    assert signature is not None


def test_status_counter_callback_exception_is_treated_as_not_synced_and_still_falls_back() -> None:
    ntp, calls = make_ntp_stub(raise_exc=RuntimeError("ntp callback exploded"))
    with _Clock() as clock:
        svc = make_service(ntp)
        start_time_set, signature, _uptime = _run_status_loop(svc, clock, 120)
    assert start_time_set is True
    assert signature is not None
    assert calls[0] == 120  # every tick retried the callback until the wait-time fallback resolved it
    assert svc.pr._err_count == 120  # every tick retried and was counted; the repeat spends one slot
    assert _persisted(svc) == [code("E", "CALLBACK")]


def test_status_counter_stops_checking_ntp_once_start_time_is_set() -> None:
    ntp, calls = make_ntp_stub(synced=True)
    asy_base_classes.set_utc_valid()
    try:
        with _Clock() as clock:
            _run_status_loop(make_service(ntp), clock, 4)
    finally:
        asy_base_classes.set_utc_valid(valid=False)
    assert calls[0] == 1  # resolved on tick 1, never rechecked on ticks 2-4


def test_status_counter_boot_signature_never_changes_again_once_resolved() -> None:
    # An outside observer watches get_boot_signature() for a change to detect a reboot, so the value stays
    # stable for the rest of this boot once resolved - never re-picked, never "upgraded".
    ntp, _calls = make_ntp_stub(synced=True)
    asy_base_classes.set_utc_valid()

    async def scenario(svc: SystemService, clock: _Clock) -> "list[int | float | None]":
        task = asyncio.create_task(svc._status_loop())
        await _pump(svc._uptime_event, 1, clock)
        seen = [await svc.get_boot_signature()]
        await _pump(svc._uptime_event, 10, clock)
        seen.append(await svc.get_boot_signature())
        await _cancel(task)
        return seen

    try:
        with _Clock() as clock:
            first, second = run(scenario(make_service(ntp), clock))
    finally:
        asy_base_classes.set_utc_valid(valid=False)
    assert first is not None
    assert first == second  # unchanged across 10 further ticks - no spurious "reboot" signal


def test_uptime_is_measured_not_counted() -> None:
    # Uptime follows ticks_ms() deltas, never the number of wake-ups, and reads no wall clock at all.
    async def wakes(svc: SystemService, clock: _Clock, gaps_ms: "list[int]") -> int:
        task = asyncio.create_task(svc._status_loop())
        for gap in gaps_ms:
            await _pump(svc._uptime_event, 1, clock, step_ms=gap)
        uptime = await svc.get_uptime()
        await _cancel(task)
        return uptime

    with _Clock() as clock:
        assert run(wakes(make_service(), clock, [2500, 2500, 2500])) == 7  # (a) three wake-ups over 7,500 ms
        svc = make_service()
        clock.advance(5000)  # (b) no wake-up for 5,000 ms, then one
        assert run(wakes(svc, clock, [0])) == 5
    with _Clock() as clock:  # (c) a dropped wake-up loses nothing: the next read carries the elapsed time
        svc = make_service()
        svc.start_uptime_timer()

        async def dropped() -> int:
            task = asyncio.create_task(svc._status_loop())
            clock.advance(1000)
            svc._uptime_timer.drop()
            clock.advance(1000)
            svc._uptime_timer.trigger()
            for _ in range(5):
                await asyncio.sleep(0)
            uptime = await svc.get_uptime()
            await _cancel(task)
            return uptime

        assert run(dropped()) == 2
    with _Clock(strict=True) as clock:  # (d) no RTC, time() or NTP value: the wall-clock reads raise here
        assert run(wakes(make_service(), clock, [1000, 1000, 1000])) == 3


def test_a_restarted_counter_keeps_the_signature() -> None:
    # A supervisor restart of the uptime task changes neither the signature nor uptime (both live outside it).
    async def restart(svc: SystemService, clock: _Clock, first_ticks: int) -> "tuple[int | float | None, int | float | None, int]":
        task = asyncio.create_task(svc._status_loop())
        await _pump(svc._uptime_event, first_ticks, clock)
        before = await svc.get_boot_signature()
        await _cancel(task)
        task = asyncio.create_task(svc._status_loop())
        await _pump(svc._uptime_event, 2, clock)
        after = await svc.get_boot_signature()
        uptime = await svc.get_uptime()
        await _cancel(task)
        return before, after, uptime

    ntp, _calls = make_ntp_stub(synced=True)
    asy_base_classes.set_utc_valid()
    try:
        with _Clock() as clock:
            before, after, uptime = run(restart(make_service(ntp), clock, 1))
    finally:
        asy_base_classes.set_utc_valid(valid=False)
    assert before is not None and before == after
    assert uptime == 3
    with _Clock() as clock:  # the random fallback: resolved at 120 s, kept across the restart
        before, after, uptime = run(restart(make_service(), clock, 120))
    assert before is not None and before == after
    assert uptime == 122


def test_a_dead_uptime_timer_falls_back_to_one_second_passes() -> None:
    with _Clock() as clock:
        svc = make_service()
        with _RaiseOnArm():
            svc.start_uptime_timer()
        assert svc._tick_failed is True
        assert svc._uptime_event.state  # set: wakes the loop into its fallback

        async def scenario() -> "tuple[int, int | float | None, int]":
            task = asyncio.create_task(svc._status_loop())
            with _RaiseOnArm(), _FastAsyncSleep(clock):
                for _ in range(130):
                    await asyncio.sleep(0)
            uptime = await svc.get_uptime()
            signature = await svc.get_boot_signature()
            entries = svc.pr._err_count
            await _cancel(task)
            return uptime, signature, entries

        uptime, signature, entries = run(scenario())
    assert uptime >= 120  # one driven second per pass, no tick needed
    assert signature is not None  # the random fallback resolved on the passes alone
    assert entries == 1 and _persisted(svc) == [code("E", "TIMER")]  # once per task run, however many passes
    assert svc._tick_failed is True

    with _Clock() as clock:  # once an arm succeeds the passes wait on the tick again
        svc = make_service()
        with _RaiseOnArm():
            svc.start_uptime_timer()

        async def rearm() -> int:
            task = asyncio.create_task(svc._status_loop())
            with _FastAsyncSleep(clock):
                for _ in range(5):
                    await asyncio.sleep(0)
            assert svc._tick_failed is False
            assert svc._uptime_timer.mode == Timer.PERIODIC and svc._uptime_timer.period == 1000
            settled = await svc.get_uptime()
            for _ in range(5):
                await asyncio.sleep(0)  # no tick and no fallback: the loop waits on the event
            clock.advance(3000)
            assert await svc.get_uptime() == settled + 3  # measured on the next read whenever it comes
            await _cancel(task)
            return settled

        assert run(rearm()) >= 1
    assert _persisted(svc) == [code("E", "TIMER")]


def test_a_dead_uptime_timer_reads_the_clock_every_second() -> None:
    # The structural form of "uptime is read inside ticks_diff()'s 2**29 ms horizon": with the timer dead, no two
    # consecutive TickSeconds reads are more than 1000 driven ms apart, and uptime equals the driven seconds.
    with _Clock() as clock:
        svc = make_service()
        reads: list[int] = []
        real_read = svc._uptime.read

        def recording_read() -> int:
            reads.append(clock.now)
            return real_read()

        svc._uptime.read = recording_read  # type: ignore[method-assign]
        with _RaiseOnArm():
            svc.start_uptime_timer()
        start = clock.now

        async def scenario() -> int:
            task = asyncio.create_task(svc._status_loop())
            with _RaiseOnArm(), _FastAsyncSleep(clock):
                while len(reads) < 50:
                    await asyncio.sleep(0)
            await _cancel(task)
            return await svc.get_uptime()

        uptime = run(scenario())
    assert max(reads[i + 1] - reads[i] for i in range(len(reads) - 1)) <= 1000, reads
    assert uptime == (clock.now - start) // 1000


# ---------------------------------------------------------------------------
# start_timers - the timer starters, then the read triggers staggered from one shared start
# ---------------------------------------------------------------------------


def test_start_timers_with_no_starters_arms_nothing() -> None:
    svc = make_service()
    before = list(Timer.all_timers)
    run(svc.start_timers([], []))
    assert Timer.all_timers == before
    assert svc._sequencer_timer.period == -1  # never armed


def test_a_single_trigger_starts_without_a_stagger_timer() -> None:
    svc = make_service()
    started: list[int] = []
    run(svc.start_timers([lambda: started.append(1)], []))
    assert started == [1]
    assert svc._sequencer_timer.period == -1  # slot 0 starts at the shared start itself


def test_triggers_start_in_order_on_the_one_preallocated_timer() -> None:
    svc = make_service()
    before = list(Timer.all_timers)
    started: list[str] = []
    timers = [lambda: started.append("t1"), lambda: started.append("t2")]
    triggers = [lambda: started.append("r1"), lambda: started.append("r2"), lambda: started.append("r3")]
    first_id = id(svc._sequencer_timer)

    async def scenario() -> None:
        task = asyncio.create_task(svc.start_timers(triggers, timers))
        for _ in range(5):
            await asyncio.sleep(0)
        assert started == ["t1", "t2", "r1"]  # the timer starters first, then trigger 0 at once
        for n in (2, 3):
            assert svc._sequencer_timer.mode == Timer.ONE_SHOT
            assert 0 < svc._sequencer_timer.period <= (n - 1) * 250  # trigger n-1 waits for its slot
            svc._sequencer_timer.trigger()
            for _ in range(5):
                await asyncio.sleep(0)
            assert started[-1] == "r" + str(n)
        await task

    run(scenario())
    assert started == ["t1", "t2", "r1", "r2", "r3"]
    assert id(svc._sequencer_timer) == first_id
    assert Timer.all_timers == before  # one preallocated Timer re-armed through init(), none constructed


def test_a_raising_starter_is_persisted_and_sequencing_continues() -> None:
    svc = make_service(log=LogConfig(None, 10, _ERR))
    started: list[int] = []

    def bad_starter() -> None:
        raise RuntimeError("boom")

    recorder = _PrintRecorder()
    try:
        with _FastAsyncSleep():
            run(svc.start_timers([lambda: started.append(1)], [bad_starter, lambda: started.append(2)]))
    finally:
        recorder.restore()
    assert started == [2, 1]
    assert svc.pr._err_count == 1
    assert _persisted(svc) == [code("E", "TASK_STARTER_RAISED")]
    assert [line[:3] for line in recorder.lines if line[1] == "Timer starter"] == [("SYSTEM", "Timer starter", 0)]


def _start_triggers_with_every_arm_failing(exc: "type[BaseException]") -> "tuple[SystemService, list[int]]":
    svc = make_service()
    started: list[int] = []
    triggers = [lambda: started.append(1), lambda: started.append(2), lambda: started.append(3)]
    with _FastAsyncSleep(), _RaiseOnArm(exc):
        run(svc.start_timers(triggers, []))
    return svc, started


def test_an_arm_failure_falls_back_to_a_sleep_and_still_starts_every_trigger() -> None:
    for exc in (OSError, MemoryError):
        svc, started = _start_triggers_with_every_arm_failing(exc)
        assert started == [1, 2, 3]  # degraded in place, never stopped early
        assert svc.pr._err_count == 2  # one entry per failed stagger arm (trigger 0 needs none)
        assert _persisted(svc) == [code("E", "TIMER")]


# ---------------------------------------------------------------------------
# The reset path: reboot_system()/reboot_bootloader() and _reboot() - record, flush, pause, arm
# ---------------------------------------------------------------------------


async def _fire(svc: SystemService) -> None:
    # The reset timer's one-shot fires; the woken reset task then runs the reset action.
    svc._reset_timer.trigger()
    for _ in range(50):
        await asyncio.sleep(0)
        if svc._reset_task is not None and svc._reset_task.done():
            return
    raise AssertionError("the reset task never ran")


class _Store:
    # A config store double: records the order of its calls against the reset record and the storage pause.
    def __init__(self, name: str, events: "list[str]", manager: "FRAMManager | None" = None, *, raise_on_flush: bool = False) -> None:
        self.name = name
        self.flushes = 0
        self.closed = False
        self._events = events
        self._manager = manager
        self._raise = raise_on_flush

    def close_writes(self) -> None:
        self.closed = True
        self._events.append(self.name + ".close")

    async def flush_pending(self) -> None:
        self.flushes += 1
        record = machine.mem_backup(0)[1]
        paused = None if self._manager is None else self._manager.get_pause()
        self._events.append(f"{self.name}.flush record={record} paused={paused}")
        if self._raise:
            raise OSError(5, "injected flush failure")


def test_reboot_system_arms_the_one_shot_and_the_trigger_runs_machine_reset() -> None:
    svc = make_service()
    machine.reset_count = 0

    async def scenario() -> None:
        await svc.reboot_system()
        assert svc._reset_timer.mode == Timer.ONE_SHOT
        assert svc._reset_timer.period == _src_const("_RESET_DELAY") * 1000
        assert machine.reset_count == 0  # not yet fired - a real Timer would still be counting down
        await _fire(svc)

    run(scenario())
    assert machine.reset_count == 1


def test_an_armed_reset_stops_every_feed_so_a_dropped_one_shot_still_resets() -> None:
    # A one-shot the scheduler drops never wakes the reset task; with nothing feeding, the watchdog resets instead.
    wdt = machine.WDT()
    svc = make_service(watchdog=wdt)

    async def scenario() -> None:
        svc.feed_watchdog()
        assert wdt.feed_count == 1
        await svc.reboot_system()
        svc.feed_watchdog()
        assert wdt.feed_count == 1, wdt.feed_count  # the callback never runs here: nothing fed since the arm
        await _cancel(svc._reset_task)  # type: ignore[arg-type]

    run(scenario())
    assert machine.mem_backup(0)[1] == _src_const("_RR_REBOOT")  # the watchdog reset still decodes as the command


def test_reboot_system_with_fram_pauses_storage_and_a_pending_unpause_never_reopens_it() -> None:
    manager, _chip = make_fram_manager()
    svc = make_service(storage=manager, log=LogConfig(manager, 10, None))
    machine.reset_count = 0
    with _Clock() as clock:

        async def scenario() -> None:
            assert svc.pause_permanent_storage(60) is True
            await svc.reboot_system()
            assert manager.get_pause() is True  # paused at once, before the reset timer ever fires
            loop = asyncio.create_task(svc._status_loop())
            await _pump(svc._uptime_event, 61, clock)  # the pending deadline passes inside the countdown
            await _fire(svc)
            await _cancel(loop)

        run(scenario())
    assert machine.reset_count == 1
    assert manager.get_pause() is True
    assert svc._unpause_at is None  # spent, refused


def test_reboot_bootloader_arms_the_one_shot_and_the_trigger_runs_machine_bootloader() -> None:
    manager, _chip = make_fram_manager()
    svc = make_service(storage=manager, log=LogConfig(manager, 10, None))
    machine.bootloader_count = 0

    async def scenario() -> None:
        await svc.reboot_bootloader()
        assert manager.get_pause() is True
        assert machine.bootloader_count == 0
        await _fire(svc)

    run(scenario())
    assert machine.bootloader_count == 1


def _arm_failure(exc: "type[BaseException]", *, bootloader: bool, with_fram: bool) -> "tuple[SystemService, FRAMManager | None]":
    manager = make_fram_manager()[0] if with_fram else None
    svc = make_service(storage=manager, log=LogConfig(manager, 10, None) if manager is not None else DEFAULT_LOG)
    code_ = _src_const("_RR_BOOTLOADER" if bootloader else "_RR_REBOOT")
    action = machine.bootloader if bootloader else machine.reset
    with _RaiseOnArm(exc):
        run(svc._reboot(code_, "Reboot triggered", action))  # must not raise despite the timer failing to arm
    return svc, manager


def test_an_arm_failure_starves_the_watchdog_and_records_code_6() -> None:
    # Real rp2 Timer.init() raises OSError(ENOMEM) on an exhausted alarm pool, a failed allocation MemoryError:
    # either way the reset falls back to the starved watchdog, and the record names it (code 6).
    machine.reset_count = 0
    for bootloader in (False, True):
        for exc in (OSError, MemoryError):
            for with_fram in (False, True):
                machine.power_on()
                svc, manager = _arm_failure(exc, bootloader=bootloader, with_fram=with_fram)
                assert svc._force_watchdog_starve is True
                assert machine.mem_backup(0)[1] == _src_const("_RR_STARVE_ARM_FAILED")
                assert svc._reset_task is not None and svc._reset_timer.period == -1  # created, then cancelled; never armed
                if manager is not None:
                    assert manager.get_pause() is True  # the pause happened before the failing init()
    assert machine.reset_count == 0  # never armed, so it can never fire on its own


def test_a_second_reboot_request_neither_deinits_nor_rearms() -> None:
    svc = make_service()

    async def scenario() -> None:
        await svc.reboot_system()
        callback = svc._reset_timer.callback
        await svc.reboot_bootloader()
        await svc._reboot(_src_const("_RR_TASK_BUDGET"), "Reboot triggered", machine.reset)
        assert len(svc._reset_timer.arms) == 1
        assert svc._reset_timer.callback is callback
        assert svc._reset_timer.deinit_called is False
        await _cancel(svc._reset_task)  # type: ignore[arg-type]

    run(scenario())
    assert machine.mem_backup(0)[1] == _src_const("_RR_REBOOT")  # the first request's record stands


def test_a_raising_flush_never_stops_the_other_stores_or_the_arm() -> None:
    events: list[str] = []
    stores = [_Store("A", events), _Store("B", events, raise_on_flush=True), _Store("C", events)]
    svc = make_service(config_stores=lambda: stores)  # type: ignore[arg-type, return-value]
    run(svc.setup())

    async def scenario() -> None:
        await svc.reboot_system()
        assert svc._reset_timer.period == _src_const("_RESET_DELAY") * 1000  # still armed
        await _cancel(svc._reset_task)  # type: ignore[arg-type]

    run(scenario())
    assert [s.flushes for s in stores] == [1, 1, 1]
    assert _persisted(svc) == [code("E", "CALLBACK")]


def test_the_record_precedes_the_flush_and_the_pause_follows_it() -> None:
    machine.power_on()
    manager, _chip = make_fram_manager()
    events: list[str] = []
    store = _Store("A", events, manager)
    svc = make_service(storage=manager, config_stores=lambda: [store])  # type: ignore[list-item]
    run(svc.setup())

    async def scenario() -> None:
        await svc.reboot_system()
        assert manager.get_pause() is True
        await _fire(svc)

    run(scenario())
    reboot = _src_const("_RR_REBOOT")
    # The record is written before the first flush, which runs unpaused; the stores close, then flush once more.
    assert events == [f"A.flush record={reboot} paused=False", "A.close", f"A.flush record={reboot} paused=True"]


def test_a_task_creation_failure_inside_reboot_starves_and_arms_nothing() -> None:
    machine.power_on()
    svc = make_service()
    real_create_task = asyncio.create_task

    def failing(_coro: object) -> None:
        _coro.close()  # type: ignore[attr-defined]
        raise MemoryError("injected: no room for the reset task")

    asyncio.create_task = failing  # type: ignore[assignment]
    try:
        run(svc.reboot_system())
    finally:
        asyncio.create_task = real_create_task
    assert svc._force_watchdog_starve is True
    assert svc._reset_task is None
    assert svc._reset_timer.arms == []
    assert machine.mem_backup(0)[1] == _src_const("_RR_STARVE_ARM_FAILED")


# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper.
_scratch = TmpScratch("sysservice")


def _tmp_cfg_dir() -> str:
    return _scratch.dir()


_VAL_COUNT: "cm.ConfigSchema" = (("Count", "int", 5, 0, 10, None),)


def _real_store(path: str) -> cm.ConfigManager:
    store = cm.ConfigManager(path + "config_RESETWIN.cfg", _VAL_COUNT, "RESETWIN")
    assert run(store.setup()) is True
    return store


def _file_count(path: str) -> int:
    with open(path + "config_RESETWIN.cfg") as f:
        return int(f.read().split(":")[1].strip(" }\n"))


def test_a_write_accepted_inside_the_countdown_is_on_flash_before_the_reset() -> None:
    path = _tmp_cfg_dir()
    store = _real_store(path)
    svc = make_service(config_stores=lambda: [store])
    run(svc.setup())
    machine.reset_count = 0

    async def scenario() -> "tuple[bool, cm.WriteValidity]":
        await svc.reboot_system()
        persisted, results = await store.write_config({"Count": 7})  # 3.9 s into the window: staged, flushed by the reset
        assert (persisted, results) == (True, {"Count": "Valid"})
        await _fire(svc)
        return await store.write_config({"Count": 8})  # after the trigger: the store is closed

    late = run(scenario())
    assert machine.reset_count == 1
    assert _file_count(path) == 7
    assert late == (False, {})


# ---------------------------------------------------------------------------
# pause_permanent_storage() - a deadline tested on the uptime pass, never a timer
# ---------------------------------------------------------------------------


def _paused_service() -> "tuple[SystemService, FRAMManager]":
    manager, _chip = make_fram_manager()
    return make_service(storage=manager, log=LogConfig(manager, 10, _EVENT)), manager


def test_pause_permanent_storage_without_fram_is_a_no_op_that_answers_true() -> None:
    svc = make_service()
    before = list(Timer.all_timers)
    assert svc.pause_permanent_storage(100) is True
    assert svc._unpause_at is None
    assert Timer.all_timers == before


def test_pause_permanent_storage_zero_and_negative_durations_unpause_at_once() -> None:
    for duration in (0, -5):
        svc, manager = _paused_service()
        svc.pause_permanent_storage(60)
        assert svc.pause_permanent_storage(duration) is True
        assert manager.get_pause() is False
        assert svc._unpause_at is None  # the pending deadline is cleared too


def test_pause_permanent_storage_clamps_to_the_max() -> None:
    with _Clock() as clock:
        for duration in (999_999, _src_const("_MAX_STORAGE_PAUSE")):
            svc, manager = _paused_service()
            assert svc.pause_permanent_storage(duration) is True
            assert manager.get_pause() is True
            assert svc._unpause_at is not None
            assert clock.ticks_diff(svc._unpause_at, clock.now) == _src_const("_MAX_STORAGE_PAUSE") * 1000  # type: ignore[arg-type]


def test_a_pause_arms_no_timer() -> None:
    svc, _manager = _paused_service()
    before = [(t, t.period, t.mode, len(t.arms)) for t in Timer.all_timers]
    svc.pause_permanent_storage(60)
    assert [(t, t.period, t.mode, len(t.arms)) for t in Timer.all_timers] == before


def _pending(svc: SystemService) -> bool:
    return svc._unpause_at is not None


def _auto_unpause_lines(recorder: _PrintRecorder) -> int:
    return sum(1 for line in recorder.lines if "Storage auto-unpaused." in line)


def test_the_first_pass_past_the_deadline_unpauses_and_logs_one_line() -> None:
    recorder = _PrintRecorder()
    try:
        with _Clock() as clock:
            svc, manager = _paused_service()

            async def scenario() -> None:
                task = asyncio.create_task(svc._status_loop())
                assert svc.pause_permanent_storage(60) is True
                await _pump(svc._uptime_event, 59, clock)
                await _pump(svc._uptime_event, 1, clock, step_ms=999)  # 1 ms before the deadline
                assert (manager.get_pause(), _pending(svc)) == (True, True)
                await _pump(svc._uptime_event, 1, clock, step_ms=1)  # the first pass at it
                assert (manager.get_pause(), _pending(svc)) == (False, False)
                await _pump(svc._uptime_event, 3, clock)
                await _cancel(task)

            run(scenario())
    finally:
        recorder.restore()
    assert _auto_unpause_lines(recorder) == 1


def test_a_second_pause_replaces_the_first_deadline() -> None:
    with _Clock() as clock:
        svc, manager = _paused_service()

        async def scenario() -> None:
            task = asyncio.create_task(svc._status_loop())
            svc.pause_permanent_storage(60)
            svc.pause_permanent_storage(120)
            await _pump(svc._uptime_event, 61, clock)
            assert manager.get_pause() is True  # the first deadline is gone
            await _pump(svc._uptime_event, 60, clock)
            assert manager.get_pause() is False
            await _cancel(task)

        run(scenario())


def test_a_dropped_tick_delays_the_unpause_by_one_pass() -> None:
    with _Clock() as clock:
        svc, manager = _paused_service()
        svc.start_uptime_timer()

        async def scenario() -> None:
            task = asyncio.create_task(svc._status_loop())
            svc.pause_permanent_storage(2)
            for drop in (False, True):
                clock.advance(1000)
                if drop:
                    svc._uptime_timer.drop()  # the crossing tick's callback lost to a full scheduler queue
                else:
                    svc._uptime_timer.trigger()
                for _ in range(5):
                    await asyncio.sleep(0)
            assert manager.get_pause() is True  # crossed at 2 s, but the pass never ran
            clock.advance(1000)
            svc._uptime_timer.trigger()
            for _ in range(5):
                await asyncio.sleep(0)
            assert manager.get_pause() is False  # the next pass unpauses
            await _cancel(task)

        run(scenario())


def test_mempause_answers_valid_with_every_timer_arm_failing() -> None:
    # A "Valid" pause always ends: with every Timer.init() failing it ends on the uptime loop's one-second fallback.
    with _Clock() as clock:
        svc, manager = _paused_service()
        with _RaiseOnArm():
            svc.start_uptime_timer()
            assert svc.pause_permanent_storage(5) is True
            assert manager.get_pause() is True

            async def scenario() -> None:
                task = asyncio.create_task(svc._status_loop())
                with _FastAsyncSleep(clock):
                    for _ in range(40):
                        await asyncio.sleep(0)
                await _cancel(task)

            run(scenario())
    assert manager.get_pause() is False


def test_a_deadline_crossed_after_a_reset_leaves_storage_paused() -> None:
    recorder = _PrintRecorder()
    try:
        with _Clock() as clock:
            svc, manager = _paused_service()

            async def scenario() -> None:
                task = asyncio.create_task(svc._status_loop())
                svc.pause_permanent_storage(10)
                await svc._reboot(_src_const("_RR_REBOOT"), "Reboot triggered", machine.reset)
                await _pump(svc._uptime_event, 12, clock)
                await _cancel(task)
                await _cancel(svc._reset_task)  # type: ignore[arg-type]

            run(scenario())
    finally:
        recorder.restore()
    assert manager.get_pause() is True
    assert svc._unpause_at is None
    assert _auto_unpause_lines(recorder) == 0


# ---------------------------------------------------------------------------
# get_task_starters / get_timer_starters
# ---------------------------------------------------------------------------


def test_get_task_starters_starter_returns_a_real_task() -> None:
    svc = make_service()

    async def scenario() -> None:
        starters = svc.get_task_starters()
        assert len(starters) == 1  # the uptime counter alone: the auto-unpause has no task
        await _cancel(starters[0]())

    run(scenario())


def test_get_timer_starters_starter_arms_the_uptime_timer() -> None:
    svc = make_service()
    starters = svc.get_timer_starters()
    assert len(starters) == 1
    starters[0]()
    assert svc._uptime_timer.mode == Timer.PERIODIC
    assert svc._uptime_timer.period == 1000
    assert svc._tick_failed is False


def test_start_uptime_timer_degrades_to_the_fallback_when_it_cannot_be_armed() -> None:
    # Owner-confirmed design (2026-07-18, `1df8bc4`): a failed arm degrades rather than reboots. Its persisted
    # TIMER entry comes from the uptime loop's fallback, once per task run, not from this call.
    for exc in (OSError, MemoryError):
        svc = make_service()
        with _RaiseOnArm(exc):
            svc.start_uptime_timer()  # must not raise despite the timer failing to arm
        assert svc._tick_failed is True
        assert svc.pr._err_count == 0
        assert svc._force_watchdog_starve is False  # graceful degradation, not a forced reboot
        assert svc._uptime_timer.period == -1  # never actually armed


# ---------------------------------------------------------------------------
# get_error_counter / reset_error_counter
# ---------------------------------------------------------------------------


def test_get_error_counter_reflects_logged_errors_and_reset_clears_them() -> None:
    # history_length=1: one err_s() fills the one slot, so the log reads exactly that entry.
    svc = make_service(log=LogConfig(None, 1, None))
    run(svc.pr.setup())
    run(svc.pr.err_s("boom", errno=code("E", "CALLBACK")))
    result = run(svc.get_error_counter())
    assert result == {"SYSTEM": {"ErrCount": 1, "ErrNum": [code("E", "CALLBACK")], "ErrType": ["E"]}}
    assert run(svc.reset_error_counter()) is True
    assert svc.pr._err_count == 0


def test_get_error_counter_and_reset_work_when_fram_backed() -> None:
    manager, _chip = make_fram_manager()
    run(manager.setup())
    svc = make_service(storage=manager, log=LogConfig(manager, 1, None))
    run(svc.pr.setup())
    run(svc.pr.err_s("boom", errno=code("E", "CALLBACK")))
    result = run(svc.get_error_counter())
    assert result == {"SYSTEM": {"ErrCount": 1, "ErrNum": [code("E", "CALLBACK")], "ErrType": ["E"]}}
    assert run(svc.reset_error_counter()) is True
    assert svc.pr._err_count == 0


def test_reset_error_counter_answers_false_when_the_history_write_fails() -> None:
    manager, chip = make_fram_manager()
    svc = make_service(storage=manager, log=LogConfig(manager, 4, None))
    run(manager.setup())
    run(svc.pr.setup())
    chip.drop_wren = True  # no WREN lands: the cleared ring cannot be written
    assert run(svc.reset_error_counter()) is False


# ---------------------------------------------------------------------------
# _start_task
# ---------------------------------------------------------------------------


def test_start_task_returns_the_real_task_on_success() -> None:
    svc = make_service()

    async def scenario() -> None:
        async def _coro() -> None:
            pass

        def starter() -> "asyncio.Task[None]":
            return asyncio.create_task(_coro())

        task = await svc._start_task(starter, 0)
        assert task is not None
        await task

    run(scenario())


def test_start_task_starter_exception_returns_none_and_logs_once() -> None:
    svc = make_service()

    def bad_starter() -> "asyncio.Task[None]":
        raise RuntimeError("boom")

    result = run(svc._start_task(bad_starter, 2))
    assert result is None
    assert svc.pr._err_count == 1
    assert _persisted(svc) == [code("E", "TASK_STARTER_RAISED")]


# ---------------------------------------------------------------------------
# start_and_check_tasks() - the start loop, then the supervisor as its own task
# ---------------------------------------------------------------------------


async def _yields(n: int) -> None:
    for _ in range(n):
        await asyncio.sleep(0)


def _long_lived_starter() -> "asyncio.Task[None]":
    async def _c() -> None:
        await asyncio.Event().wait()

    return asyncio.create_task(_c())


def test_start_and_check_tasks_empty_starters_never_fails() -> None:
    wdt = machine.WDT()
    svc = make_service(watchdog=wdt)

    async def scenario() -> None:
        task = asyncio.create_task(svc.start_and_check_tasks([]))
        await _yields(3)
        assert wdt.feed_count >= 1
        await _cancel(task)

    with _FastAsyncSleep():
        run(scenario())


def test_cancelling_start_and_check_tasks_cancels_its_supervisor() -> None:
    wdt = machine.WDT()
    svc = make_service(watchdog=wdt)

    async def scenario() -> None:
        task = asyncio.create_task(svc.start_and_check_tasks([_long_lived_starter]))
        await _yields(10)
        supervisor = svc._supervisor_task
        assert supervisor is not None and not supervisor.done()
        await _cancel(task)
        await _yields(3)
        assert supervisor.done()
        fed = wdt.feed_count
        await _yields(10)
        assert wdt.feed_count == fed  # nothing supervises, nothing feeds

    with _FastAsyncSleep():
        run(scenario())


class _CountingGc:
    # Stands in for the `gc` module so the boot collects can be counted - module-attribute
    # reassignment is this project's mocking mechanism (MicroPython has no unittest.mock).

    def __init__(self) -> None:
        self.collects = 0

    def collect(self) -> None:
        self.collects += 1


def _count_collects_during_supervision(starters: "list[Callable[[], asyncio.Task[Any]]]", iterations: int) -> "tuple[int, int]":
    # Returns (collects once every starter has been started, collects after `iterations` more
    # supervisor yields) - the second must equal the first: the supervisor is the run phase.
    counter = _CountingGc()
    original_gc = asy_system_service.gc
    asy_system_service.gc = counter  # type: ignore[assignment]
    svc = make_service(watchdog=machine.WDT())
    after_start = [0]

    async def scenario() -> None:
        task = asyncio.create_task(svc.start_and_check_tasks(starters))
        await _yields(4 * (len(starters) + 1))  # let the whole starter loop and its sleeps drain
        after_start[0] = counter.collects
        await _yields(iterations)
        await _cancel(task)

    try:
        with _FastAsyncSleep():
            run(scenario())
    finally:
        asy_system_service.gc = original_gc
    return after_start[0], counter.collects


def test_start_and_check_tasks_collects_once_per_starter_plus_one_and_never_in_the_supervisor() -> None:
    # The boot placement reset (SPECIFICATION.md I.4(f.1)): the starter list is the second of the two one-time
    # boot lists that get a collect between their units; the supervisor underneath is the run phase.
    starters = [_long_lived_starter, _long_lived_starter, _long_lived_starter]
    after_start, after_supervision = _count_collects_during_supervision(starters, 40)
    assert after_start == len(starters) + 1, f"expected {len(starters) + 1} boot collects, got {after_start}"
    assert after_supervision == after_start, f"the supervisor collected {after_supervision - after_start} time(s)"


def test_start_and_check_tasks_with_no_starters_still_does_the_start_of_list_collect() -> None:
    after_start, after_supervision = _count_collects_during_supervision([], 20)
    assert after_start == 1, f"expected exactly the start-of-list collect, got {after_start}"
    assert after_supervision == 1, "the supervisor loop must not collect even with no tasks to supervise"


def _supervised(svc: SystemService, starters: "list[Callable[[], asyncio.Task[Any]]]", passes: int = 20) -> None:
    # Drives the start loop and the supervisor through `passes` yields under the fast sleep, then cancels both.
    async def scenario() -> None:
        task = asyncio.create_task(svc.start_and_check_tasks(starters))
        await _yields(passes)
        await _cancel(task)

    with _FastAsyncSleep():
        run(scenario())


def test_start_and_check_tasks_feeds_the_watchdog_while_tasks_stay_alive() -> None:
    wdt = machine.WDT()
    _supervised(make_service(watchdog=wdt), [_long_lived_starter], 10)
    assert wdt.feed_count >= 1


def test_start_and_check_tasks_stops_feeding_the_watchdog_once_force_watchdog_starve_is_set() -> None:
    wdt = machine.WDT()
    svc = make_service(watchdog=wdt)
    svc._force_watchdog_starve = True
    _supervised(svc, [_long_lived_starter], 10)
    assert wdt.feed_count == 0  # never fed despite tasks staying alive and under the fail budget


def test_start_and_check_tasks_without_watchdog_does_not_raise() -> None:
    _supervised(make_service(watchdog=None), [_long_lived_starter], 10)  # must not raise


def test_the_supervisor_leaves_the_logger_setup_to_the_boot_batch() -> None:
    svc = make_service()
    _supervised(svc, [_long_lived_starter], 10)
    assert svc.pr.initialized is False


def _ending_then_parked(how: str, calls: "list[int]", parked: asyncio.Event) -> "Callable[[], asyncio.Task[None]]":
    # A starter whose first task ends `how` ("raise", "cancel" or "return") and whose later ones park on an
    # event; "starter" makes the second start itself raise. Parked, not slept: the fast sleep returns at once.
    def starter() -> "asyncio.Task[None]":
        calls[0] += 1
        attempt = calls[0]
        if how == "starter" and attempt == 2:
            raise RuntimeError("injected starter failure")

        async def _c() -> None:
            if attempt == 1:
                if how == "raise":
                    raise RuntimeError("injected task crash")
                if how == "cancel":
                    raise asyncio.CancelledError
                return
            await parked.wait()

        return asyncio.create_task(_c())

    return starter


def test_each_task_end_adds_exactly_one_entry() -> None:
    # One SYSTEM entry per task end, by how it ended; the restart line beside it is console-only.
    for how, name in (("raise", "TASK_RAISED"), ("cancel", "TASK_CANCELLED"), ("return", "TASK_RETURNED")):
        svc = make_service()
        calls = [0]
        _supervised(svc, [_ending_then_parked(how, calls, asyncio.Event())])
        assert calls[0] == 2, (how, calls)
        assert _persisted(svc) == [code("E", name)], (how, _persisted(svc))
        assert svc.pr._err_count == 1, how
    # A restart whose starter raises adds only its own TASK_STARTER_RAISED beside the task end's entry.
    svc = make_service()
    calls = [0]
    _supervised(svc, [_ending_then_parked("starter", calls, asyncio.Event())])
    assert calls[0] == 3, calls
    assert _persisted(svc) == [code("E", "TASK_RETURNED"), code("E", "TASK_STARTER_RAISED")], _persisted(svc)
    assert svc.pr._err_count == 2


def test_start_and_check_tasks_restarts_a_dead_task_and_logs_its_end() -> None:
    svc = make_service()
    calls = [0]
    _supervised(svc, [_ending_then_parked("return", calls, asyncio.Event())], 10)
    assert calls[0] >= 2  # started once at startup, restarted at least once after dying
    assert _persisted(svc)[0] == code("E", "TASK_RETURNED"), _persisted(svc)
    assert "W" not in run(svc.get_error_counter())["SYSTEM"]["ErrType"]  # the restart line is console-only


def test_start_and_check_tasks_logs_the_real_exception_of_a_crashed_task() -> None:
    # MicroPython's asyncio Task has no .exception()/.result(): _log_dead_task() awaits the ended task to learn why.
    svc = make_service()
    calls = [0]
    _supervised(svc, [_ending_then_parked("raise", calls, asyncio.Event())], 10)
    assert calls[0] >= 2
    assert code("E", "TASK_RAISED") in _persisted(svc)


def test_start_and_check_tasks_logs_a_self_cancelled_task_as_a_persisted_error() -> None:
    # Regression for the real "wrnno=10" bench bug: a task ending cancelled persists its own TASK_CANCELLED.
    svc = make_service()
    calls = [0]
    _supervised(svc, [_ending_then_parked("cancel", calls, asyncio.Event())], 10)
    assert calls[0] >= 2
    assert _persisted(svc) == [code("E", "TASK_CANCELLED")]  # exactly one entry, _log_dead_task's own


def _dead_starter(calls: "list[int]") -> "Callable[[], asyncio.Task[None]]":
    def starter() -> "asyncio.Task[None]":
        calls[0] += 1

        async def _c() -> None:
            return None

        return asyncio.create_task(_c())

    return starter


def test_the_supervisor_escalates_past_the_failure_budget() -> None:
    machine.power_on()
    machine.reset_count = 0
    svc = make_service()
    calls = [0]

    def always_raising_starter() -> "asyncio.Task[None]":
        calls[0] += 1
        raise RuntimeError("starter always fails")

    async def scenario() -> None:
        sup = asyncio.create_task(svc.start_and_check_tasks([always_raising_starter]))
        for _ in range(_RUN_BOUND_S * 100):
            await asyncio.sleep(0)
            if svc._reset_armed:
                break
        assert svc._reset_armed, "the supervisor never escalated"
        await _yields(10)
        assert not sup.done()  # it keeps running after the arm - main() never returns
        await _cancel(sup)
        await _fire(svc)

    with _FastAsyncSleep():
        run(scenario())
    assert machine.reset_count == 1
    assert _persisted(svc).count(code("E", "TASK_BUDGET_REBOOT")) == 1  # one escalation, however many passes follow
    assert calls[0] >= 4  # enough restart attempts to cross _TASK_FAIL_MAX (100 per attempt)


def test_a_pass_with_every_task_dead_escalates_at_the_first_end_past_the_budget() -> None:
    # 22 ended tasks in one pass: exactly four task-end entries, then the escalation's, fed once, three restarts.
    wdt = machine.WDT()
    svc = make_service(watchdog=wdt)
    calls = [0]
    starters = [_dead_starter(calls)] * 22
    seen: list[object] = []

    async def scenario() -> None:
        sup = asyncio.create_task(svc.start_and_check_tasks(starters))
        for _ in range(200):
            await asyncio.sleep(0)
            if svc._reset_armed:
                break
        # The escalating pass has armed the reset and sleeps: what it left is read before another pass runs.
        seen.extend((await svc.get_error_counter(), svc.pr._err_count, wdt.feed_count, calls[0]))
        await _cancel(sup)
        await _cancel(svc._reset_task)  # type: ignore[arg-type]

    with _FastAsyncSleep():
        run(scenario())
    log, entries, feeds, started = seen
    numbers, kinds = log["SYSTEM"]["ErrNum"], log["SYSTEM"]["ErrType"]  # type: ignore[index]
    used = [numbers[i] for i in range(len(numbers)) if kinds[i] != "N"]
    # Four task-end entries (one slot under the repeat rule, four counts), then the escalation's.
    assert used == [code("E", "TASK_RETURNED"), code("E", "TASK_BUDGET_REBOOT")], used
    assert entries == 5, entries
    assert feeds == 1, feeds  # the escalation's one feed; the pass end is starved
    assert started == 22 + 3, started  # restarts for the first three ends only


def test_an_escalating_pass_retires_the_dead_task_so_no_later_pass_awaits_it_again() -> None:
    # The escalating pass breaks before its restart: the dead task must still leave its slot, since a later pass
    # awaiting it again raises None where the first await raced asyncio's queued handler call (Part F.1).
    svc = make_service()
    calls = [0]
    first: list[object] = []  # the tasks themselves: a freed task's id() is reused once a collection runs
    again: list[object] = []
    real_log = svc._log_dead_task

    def starter() -> "asyncio.Task[None]":
        calls[0] += 1

        async def _c() -> None:
            raise RuntimeError("injected task crash")

        return asyncio.create_task(_c())

    async def recording_log(task: "asyncio.Task[Any]", n: int) -> None:
        # A repeat is recorded and never awaited, so the defect reads as a failure here rather than a segfault.
        if any(seen is task for seen in first):
            again.append(task)
            return
        first.append(task)
        await real_log(task, n)

    held: list[object] = []
    real_reboot = svc._reboot

    async def recording_reboot(code: int, message: str, action: "Callable[[], None]") -> None:
        held.append(svc._tasks[0])  # what the escalating pass left in the slot
        await real_reboot(code, message, action)

    svc._log_dead_task = recording_log  # type: ignore[method-assign]
    svc._reboot = recording_reboot  # type: ignore[method-assign]

    async def scenario() -> None:
        sup = asyncio.create_task(svc.start_and_check_tasks([starter]))
        for _ in range(400):
            await asyncio.sleep(0)
        await _cancel(sup)
        await _cancel(svc._reset_task)  # type: ignore[arg-type]

    with _FastAsyncSleep():
        run(scenario())
    assert svc._reset_armed, "the supervisor never escalated"
    assert again == [], f"{len(again)} later pass(es) awaited an already-logged dead task again"
    assert held == [None], held
    assert calls[0] > 4, calls  # later passes still restart, unfed


def test_three_deaths_stay_inside_the_budget_and_decay() -> None:
    svc = make_service(watchdog=machine.WDT())
    calls = [0]
    parked = asyncio.Event()

    def three_then_parked() -> "asyncio.Task[None]":
        calls[0] += 1
        attempt = calls[0]

        async def _c() -> None:
            if attempt <= 3:
                return
            await parked.wait()

        return asyncio.create_task(_c())

    _supervised(svc, [three_then_parked], 60)
    assert calls[0] == 4  # every end restarted
    assert svc._reset_armed is False
    assert _persisted(svc) == [code("E", "TASK_RETURNED")]  # three ends, one slot (the repeat rule)
    assert svc.pr._err_count == 3


def test_the_escalation_flushes_a_staged_write_and_stops_feeding_for_good() -> None:
    path = _tmp_cfg_dir()
    store = _real_store(path)
    wdt = machine.WDT()
    svc = make_service(watchdog=wdt, config_stores=lambda: [store])
    run(svc.setup())
    calls = [0]

    async def scenario() -> None:
        assert (await store.write_config({"Count": 9}))[0] is True
        sup = asyncio.create_task(svc.start_and_check_tasks([_dead_starter(calls)]))
        for _ in range(500):
            await asyncio.sleep(0)
            if svc._reset_armed:
                break
        assert svc._reset_armed
        assert _file_count(path) == 9  # flushed before the arm
        fed = wdt.feed_count
        await _yields(20)  # two more supervisor passes
        assert not sup.done()
        assert wdt.feed_count == fed
        svc.feed_watchdog()
        assert wdt.feed_count == fed  # one-way, whatever the budget does next
        await _cancel(sup)
        await _cancel(svc._reset_task)  # type: ignore[arg-type]

    with _FastAsyncSleep():
        run(scenario())


# ---------------------------------------------------------------------------
# The reset-reason record (region 0) and the boot phases (region 1)
# ---------------------------------------------------------------------------


def _watchdog_reset() -> None:
    # A starved or commanded watchdog reset: the regions survive, rp2 reports WDT_RESET.
    machine.reset_cause_value = machine.WDT_RESET


def test_every_intended_reset_path_decodes_to_its_code_and_is_cleared() -> None:
    def reboot(svc: SystemService) -> None:
        async def scenario() -> None:
            await svc.reboot_system()
            await _fire(svc)

        run(scenario())

    def bootloader(svc: SystemService) -> None:
        async def scenario() -> None:
            await svc.reboot_bootloader()
            await _fire(svc)

        run(scenario())

    def starve(svc: SystemService) -> None:
        with _RaiseOnArm():
            run(svc.reboot_system())
        _watchdog_reset()

    for path, name in ((reboot, "_RR_REBOOT"), (bootloader, "_RR_BOOTLOADER"), (starve, "_RR_STARVE_ARM_FAILED")):
        machine.power_on()
        begin_boot()
        path(make_service())
        assert begin_boot() == _src_const(name), name
        assert list(machine.mem_backup(0)) == [0, 0, 0, 0]
        make_service().boot_phase(BOOT_DONE)
        _watchdog_reset()
        assert begin_boot() == _src_const("_RR_WATCHDOG")  # cleared: the next reset after a full boot reads unrecorded


def test_the_supervisor_escalation_decodes_to_code_5() -> None:
    machine.power_on()
    begin_boot()
    svc = make_service()

    def always_raising_starter() -> "asyncio.Task[None]":
        raise RuntimeError("starter always fails")

    async def scenario() -> None:
        sup = asyncio.create_task(svc.start_and_check_tasks([always_raising_starter]))
        for _ in range(500):
            await asyncio.sleep(0)
            if svc._reset_armed:
                break
        await _cancel(sup)
        await _fire(svc)

    with _FastAsyncSleep():
        run(scenario())
    assert begin_boot() == _src_const("_RR_TASK_BUDGET")


def test_power_on_reads_1_even_with_a_stale_valid_record() -> None:
    machine.power_on()
    write_reset_record(_src_const("_RR_REBOOT"))
    machine.reset_cause_value = machine.PWRON_RESET
    assert begin_boot() == _src_const("_RR_POWER_ON")
    assert list(machine.mem_backup(0)) == [0, 0, 0, 0]


def test_no_record_after_a_complete_boot_reads_watchdog() -> None:
    machine.power_on()
    begin_boot()
    make_service().boot_phase(BOOT_DONE)
    _watchdog_reset()
    assert begin_boot() == _src_const("_RR_WATCHDOG")


def test_a_record_with_a_wrong_check_word_reads_unknown() -> None:
    machine.power_on()
    write_reset_record(_src_const("_RR_REBOOT"))
    machine.mem_backup(0)[2] ^= 1
    _watchdog_reset()
    assert begin_boot() == _src_const("_RR_UNKNOWN")


def test_a_crash_in_each_boot_phase_decodes_to_10_plus_the_phase() -> None:
    for p in range(BOOT_CONSTRUCTION, BOOT_NTP + 1):
        machine.power_on()
        begin_boot()  # marks phase 1
        svc = make_service()
        for q in range(BOOT_CONSTRUCTION, p + 1):
            svc.boot_phase(q)
        _watchdog_reset()
        assert begin_boot() == _src_const("_RR_BOOT_FAILURE") + p, p


def test_the_command_codes_decode_like_every_other_record() -> None:
    for name in ("_RR_CONFIG_RESET", "_RR_FRAM_ERASED", "_RR_COMMAND_INCOMPLETE"):
        machine.power_on()
        write_reset_record(_src_const(name))
        _watchdog_reset()
        assert begin_boot() == _src_const(name), name


def test_the_record_and_the_phase_marker_stay_small_ints() -> None:
    # Every stored word lies below 2**30, so a store never needs a heap int on the target.
    for name in ("_RR_MAGIC", "_BP_MAGIC", "_RR_CHECK"):
        assert 0 < _src_const(name) < 2**30, name
    assert (_src_const("_RR_MAGIC") ^ _src_const("_RR_CHECK")) < 2**30


def _plant_reset_flags(reason: int, chip: int) -> None:
    # What the chip's WATCHDOG REASON and VREG_AND_CHIP_RESET CHIP_RESET registers read at this boot.
    machine.watchdog_reason_value = reason
    machine.chip_reset_value = chip


def test_the_reset_flags_read_power_on_after_a_power_cycle() -> None:
    machine.power_on()
    assert begin_boot() == _src_const("_RR_POWER_ON")
    assert make_service().get_reset_bits() == 0x100  # HAD_POR


def test_the_reset_flags_after_a_reboot_read_force_with_had_por_kept() -> None:
    machine.power_on()
    begin_boot()
    svc = make_service()

    async def scenario() -> None:
        await svc.reboot_system()
        await _fire(svc)

    run(scenario())
    assert begin_boot() == _src_const("_RR_REBOOT")
    assert make_service().get_reset_bits() == 0x102  # FORCE, and HAD_POR survives a watchdog reset


def test_the_reset_flags_keep_only_their_named_bits() -> None:
    machine.power_on()
    _plant_reset_flags(1, 0x10000)  # a watchdog timeout after a RUN-pin reset
    begin_boot()
    assert make_service().get_reset_bits() == 0x10001
    _plant_reset_flags(0xFFFFFFFF, 0xFFFFFFFF)
    begin_boot()
    assert make_service().get_reset_bits() == 0x3 | 0x110100  # TIMER|FORCE, HAD_PSM_RESTART|HAD_RUN|HAD_POR


def test_the_reset_flags_are_taken_once_at_boot() -> None:
    machine.power_on()
    begin_boot()
    _plant_reset_flags(0x2, 0x10000)  # registers that change later never reach the reported value
    assert make_service().get_reset_bits() == 0x100


def test_the_reset_flags_never_change_the_decoded_reason() -> None:
    # Reported raw beside the decode, never folded into it: HAD_POR survives a watchdog reset, so a
    # decode reading it would need bench evidence first.
    def decoded(flags: "tuple[int, int]", prepare: "Callable[[], None]") -> int:
        machine.power_on()
        prepare()
        _plant_reset_flags(*flags)
        return begin_boot()

    def after_a_full_boot() -> None:
        begin_boot()
        make_service().boot_phase(BOOT_DONE)
        _watchdog_reset()

    def after_a_record() -> None:
        write_reset_record(_src_const("_RR_REBOOT"))
        _watchdog_reset()

    for prepare in (lambda: None, after_a_full_boot, after_a_record):
        assert decoded((0, 0), prepare) == decoded((0xFFFFFFFF, 0xFFFFFFFF), prepare) == decoded((1, 0x10000), prepare)


# ---------------------------------------------------------------------------
# System-settings store (config_SYSTEM.cfg) - DebugLevel through the SettingsGroup call, real file I/O
# ---------------------------------------------------------------------------


def _set_level(svc: SystemService, level: int) -> "cm.WriteValidity":
    return run(svc._set_dict_cfg({"DebugLevel": level}, svc.get_cfg_schema()))


def _recorder(calls: "list[int]") -> "Callable[[int], bool]":
    # A level setter that records each level it is given and accepts it, as PrintLog.set_level() does.
    def setter(value: int) -> bool:
        calls.append(value)
        return True

    return setter


def test_setup_resolves_cfgmgr_and_reads_the_default_level_on_first_boot() -> None:
    svc = make_service(cfg_path=_tmp_cfg_dir())
    assert run(svc.setup()) is True
    assert svc.cfgmgr.valid is True
    assert run(svc.get_dict_cfg()) == {"SYSTEM": {"DebugLevel": 0}}


def test_setup_sets_up_its_own_logger_first() -> None:
    svc = make_service(cfg_path=_tmp_cfg_dir())
    before = svc.pr.initialized  # __init__ never sets the logger up
    assert run(svc.setup()) is True
    assert (before, svc.pr.initialized, svc.cfgmgr.pr.initialized) == (False, True, True)


def test_setup_answers_false_for_an_unusable_store_and_still_sets_up_the_logger() -> None:
    cfg_path = _tmp_cfg_dir()
    os.mkdir(cfg_path + "config_SYSTEM.cfg")  # a directory where the settings file belongs
    try:
        svc = make_service(cfg_path=cfg_path)
        assert run(svc.setup()) is False
        assert svc.pr.initialized is True
        assert run(svc.get_dict_cfg()) == {"SYSTEM": {"error": "unavailable"}}
    finally:
        os.rmdir(cfg_path + "config_SYSTEM.cfg")


def test_get_dict_cfg_answers_the_nested_shape_or_the_unavailable_marker() -> None:
    svc = make_service(cfg_path=_tmp_cfg_dir())
    assert run(svc.get_dict_cfg()) == {"SYSTEM": {"error": "unavailable"}}  # before setup(): the store is not valid
    run(svc.setup())
    assert run(svc.get_dict_cfg()) == {"SYSTEM": {"DebugLevel": 0}}


def test_setup_pushes_the_persisted_value_out_through_every_registered_setter() -> None:
    calls: list[int] = []
    svc = make_service(cfg_path=_tmp_cfg_dir(), level_setters=lambda: [_recorder(calls)])
    run(svc.setup())
    # First boot writes and uses the schema default (0); the registry is still called once, unchanged default or not.
    assert calls == [0]


class _UnreadableOs:
    # Stands in for asy_config_manager's `os`: the config file exists but every stat() fails with EIO.
    def stat(self, _path: str) -> "tuple[int, ...]":
        raise OSError(5, "EIO")

    def __getattr__(self, name: str) -> object:
        return getattr(os, name)


def test_an_unreadable_store_keeps_the_constructed_level() -> None:
    calls: list[int] = []
    svc = make_service(cfg_path=_tmp_cfg_dir(), log=LogConfig(None, 10, 3), level_setters=lambda: [_recorder(calls)])
    original = cm.os
    cm.os = _UnreadableOs()  # type: ignore[assignment]
    try:
        run(svc.setup())
        assert svc.cfgmgr.writable is False
        dict_cfg = run(svc.get_dict_cfg())
    finally:
        cm.os = original
    assert calls == []  # nothing pushed: no value was read
    assert (svc.pr.level, svc.cfgmgr.pr.level) == (3, 3)
    assert dict_cfg == {"SYSTEM": {"error": "unavailable"}}  # never the defaults standing in for the unread file
    assert _persisted(svc.cfgmgr.pr) == [code("W", "CFG_FILE_UNREADABLE")]  # the store's one read-failure entry


def test_a_stored_level_wins_over_the_constructed_one() -> None:
    cfg_path = _tmp_cfg_dir()
    with open(cfg_path + "config_SYSTEM.cfg", "w") as f:
        f.write('{"DebugLevel": 4}')
    holder: list[SystemService] = []
    svc = make_service(
        cfg_path=cfg_path, log=LogConfig(None, 10, 2),
        level_setters=lambda: [pr.set_level for pr in holder[0].get_loggers()],
    )
    holder.append(svc)
    run(svc.setup())
    assert (svc.pr.level, svc.cfgmgr.pr.level) == (4, 4)  # CFGMGR_SYSTEM included


def test_set_dict_cfg_persists_and_calls_every_setter() -> None:
    calls_a: list[int] = []
    calls_b: list[int] = []
    svc = make_service(cfg_path=_tmp_cfg_dir(), level_setters=lambda: [_recorder(calls_a), _recorder(calls_b)])
    run(svc.setup())
    assert _set_level(svc, _ALL) == {"DebugLevel": "Valid"}
    assert calls_a == [0, _ALL]  # once from setup()'s own push, once from this call
    assert calls_b == [0, _ALL]
    assert run(svc.get_dict_cfg()) == {"SYSTEM": {"DebugLevel": _ALL}}


def test_an_out_of_range_level_is_invalid_and_never_reaches_the_registry() -> None:
    calls: list[int] = []
    svc = make_service(cfg_path=_tmp_cfg_dir(), level_setters=lambda: [_recorder(calls)])
    run(svc.setup())
    calls.clear()  # drop setup()'s own push of the default, isolate this call's own effect
    assert _set_level(svc, 99) == {"DebugLevel": "Invalid"}  # outside the schema's 0-5 range
    assert calls == []
    assert run(svc.get_dict_cfg()) == {"SYSTEM": {"DebugLevel": 0}}


def test_a_level_written_before_setup_fails_every_key() -> None:
    svc = make_service(cfg_path=_tmp_cfg_dir())
    assert _set_level(svc, _ALL) == {"DebugLevel": "Failed"}  # cfgmgr.valid is False before setup()


def test_a_level_without_any_registered_setters_still_persists() -> None:
    svc = make_service(cfg_path=_tmp_cfg_dir())
    run(svc.setup())
    assert _set_level(svc, _WARN) == {"DebugLevel": "Valid"}
    assert run(svc.get_dict_cfg()) == {"SYSTEM": {"DebugLevel": _WARN}}


def test_one_bad_setter_does_not_stop_the_rest_of_the_registry() -> None:
    calls: list[int] = []

    def _raising_setter(_value: int) -> bool:
        raise RuntimeError("simulated bad setter")

    svc = make_service(
        cfg_path=_tmp_cfg_dir(), level_setters=lambda: [_recorder(calls), _raising_setter, _recorder(calls)],
    )
    run(svc.setup())
    assert _set_level(svc, _WARN) == {"DebugLevel": "Valid"}  # persistence itself is unaffected
    assert calls == [0, 0, _WARN, _WARN]  # both good setters still ran, both times


def test_a_bad_setter_persists_one_callback_entry() -> None:
    def _raising_setter(_value: int) -> bool:
        raise RuntimeError("simulated bad setter")

    svc = make_service(cfg_path=_tmp_cfg_dir(), level_setters=lambda: [_raising_setter])
    run(svc.setup())
    _set_level(svc, _WARN)
    assert _persisted(svc)[-1] == code("E", "CALLBACK")


def test_the_debug_level_survives_a_simulated_reboot() -> None:
    cfg_path = _tmp_cfg_dir()
    svc = make_service(cfg_path=cfg_path)

    async def first_boot() -> None:
        await svc.setup()
        await svc._set_dict_cfg({"DebugLevel": _EVENT}, svc.get_cfg_schema())
        await svc.cfgmgr.flush_pending()

    run(first_boot())
    holder: list[SystemService] = []
    after = make_service(cfg_path=cfg_path, level_setters=lambda: [holder[0].pr.set_level])
    holder.append(after)
    run(after.setup())
    assert run(after.get_dict_cfg()) == {"SYSTEM": {"DebugLevel": _EVENT}}
    assert after.pr.level == _EVENT


def test_get_cfg_schema_returns_the_debug_level_field() -> None:
    assert make_service().get_cfg_schema()[0][0] == "DebugLevel"


def test_the_level_setters_provider_is_resolved_once_in_setup() -> None:
    # The provider is called once, in setup(): not at construction (the other modules' loggers
    # may not exist yet), and not again on a later level change.
    resolved = [0]
    calls: list[int] = []

    def provider() -> "list[Callable[[int], bool]]":
        resolved[0] += 1
        return [_recorder(calls)]

    svc = make_service(cfg_path=_tmp_cfg_dir(), level_setters=provider)
    assert resolved[0] == 0
    run(svc.setup())
    assert resolved[0] == 1
    assert calls == [0]
    _set_level(svc, _WARN)
    assert resolved[0] == 1
    assert calls == [0, _WARN]


def test_the_config_stores_provider_is_resolved_once_in_setup() -> None:
    resolved = [0]
    events: list[str] = []
    store = _Store("A", events)

    def provider() -> "list[cm.ConfigManager]":
        resolved[0] += 1
        return [store]  # type: ignore[list-item]

    svc = make_service(cfg_path=_tmp_cfg_dir(), config_stores=provider)
    assert resolved[0] == 0
    run(svc.setup())
    assert resolved[0] == 1

    async def scenario() -> None:
        await svc.reboot_system()
        await _cancel(svc._reset_task)  # type: ignore[arg-type]

    run(scenario())
    assert resolved[0] == 1
    assert store.flushes == 1


def test_pr_logger_reflects_the_live_debug_level_via_the_registry() -> None:
    # (exactly what every generated module's _collect_level_setters() does for every module, sysfunct's own included)
    holder: list[SystemService] = []
    svc = make_service(cfg_path=_tmp_cfg_dir(), level_setters=lambda: [holder[0].pr.set_level])
    holder.append(svc)
    run(svc.setup())
    _set_level(svc, _ERR)
    assert svc.pr.level == _ERR


# ---------------------------------------------------------------------------
# CONFIG_LOST: a missing settings file beside surviving FRAM history
# ---------------------------------------------------------------------------


def _history_chip() -> FakeMB85RS64V:
    # A chip whose SYSTEM chunk holds one entry, from an earlier boot.
    manager, chip = make_fram_manager()
    run(manager.setup())
    svc = make_service(storage=manager, log=LogConfig(manager, 10, None), cfg_path=_tmp_cfg_dir())
    run(svc.setup())
    run(svc.pr.err_s("an earlier boot's entry", errno=code("E", "CALLBACK")))
    return chip


def _config_lost_count(*, chip: "FakeMB85RS64V | None", file_present: bool, reset_reason: int) -> "tuple[int, SystemService, str]":
    cfg_path = _tmp_cfg_dir()
    if file_present:
        with open(cfg_path + "config_SYSTEM.cfg", "w") as f:
            f.write('{"DebugLevel": 0}')
    if chip is None:
        svc = make_service(cfg_path=cfg_path, reset_reason=reset_reason)
    else:
        manager = _same_chip_manager(chip)
        svc = make_service(storage=manager, log=LogConfig(manager, 10, None), cfg_path=cfg_path, reset_reason=reset_reason)
    run(svc.setup())
    return _persisted(svc).count(code("W", "CONFIG_LOST")), svc, cfg_path


def test_a_missing_settings_file_beside_restored_history_persists_config_lost() -> None:
    watchdog = _src_const("_RR_WATCHDOG")
    count, svc, cfg_path = _config_lost_count(chip=_history_chip(), file_present=False, reset_reason=watchdog)
    assert count == 1
    assert _persisted(svc)[-1] == code("W", "CONFIG_LOST")
    with open(cfg_path + "config_SYSTEM.cfg") as f:
        assert f.read().replace(" ", "") == '{"DebugLevel":0}'  # written with its defaults
    # Controls, none of which persists it: a first boot on a blank chip, the file present, a commanded config
    # reset (7) or an incomplete one (9), and a RAM-only logger.
    blank_manager, blank_chip = make_fram_manager()
    run(blank_manager.setup())
    assert _config_lost_count(chip=blank_chip, file_present=False, reset_reason=watchdog)[0] == 0
    assert _config_lost_count(chip=_history_chip(), file_present=True, reset_reason=watchdog)[0] == 0
    for commanded in ("_RR_CONFIG_RESET", "_RR_COMMAND_INCOMPLETE"):
        assert _config_lost_count(chip=_history_chip(), file_present=False, reset_reason=_src_const(commanded))[0] == 0
    assert _config_lost_count(chip=None, file_present=False, reset_reason=watchdog)[0] == 0


def test_a_fresh_filesystem_writes_the_settings_file_once() -> None:
    cfg_path = _tmp_cfg_dir()
    with WriteCountingOpen(cm) as counter:
        run(make_service(cfg_path=cfg_path).setup())
        run(make_service(cfg_path=cfg_path).setup())
    assert counter.writes == 1


# ---------------------------------------------------------------------------
# The unretrieved-task-exception report, SYSTEM's PrintLog.report_unretrieved() (SPECIFICATION.md Part F.1): asyncio
# calls it as handler(loop, context) with its own module dict; start_and_check_tasks() installs it only where none is set.
# ---------------------------------------------------------------------------

_UNRETRIEVED = "Task exception wasn't retrieved"  # asyncio's own message (extmod/asyncio/core.py:27 at v1.29.0)
_HAMMER_ROUNDS = 10
_HAMMER_TASKS = 100
_LARGE_LOCAL = 2048  # a dead task's frame holding this much is what a retained context would keep
_HAMMER_DRIFT_BYTES = _LARGE_LOCAL // 4  # below one large local, so a single retained dead task fails the bound
_SETTLE_YIELDS = 8  # every death and its re-queued handler call land within these yields


class _ExhaustionError(MemoryError):
    """A MemoryError printed under its own name, so a level-1 print of one stays clear of the memory gate's words."""


class _HandlerSlot:
    # Sets the loop's exception handler for the block and puts back whatever was set before (microtest's PC report).
    def __init__(self, handler: "_ExceptionHandler | None") -> None:
        self._handler = handler
        self._saved: _ExceptionHandler | None = None

    def __enter__(self) -> "Self":
        loop = asyncio.get_event_loop()
        self._saved = loop.get_exception_handler()
        loop.set_exception_handler(self._handler)
        return self

    def __exit__(self, *exc_info: object) -> None:
        asyncio.get_event_loop().set_exception_handler(self._saved)


class _ReportRecorder:
    # Shadows print() and sys inside asy_print_log, where the report lives, so its two outputs read back as calls;
    # `fail` makes the print raise instead.
    def __init__(self, fail: "Exception | None" = None) -> None:
        self.lines: list[tuple[object, ...]] = []
        self.tracebacks: list[object] = []
        self._fail = fail

    def __enter__(self) -> "Self":
        asy_print_log.print = self._print  # type: ignore[attr-defined]
        asy_print_log.sys = self  # type: ignore[assignment]
        return self

    def __exit__(self, *exc_info: object) -> None:
        del asy_print_log.print  # type: ignore[attr-defined]
        asy_print_log.sys = sys

    def _print(self, *args: object, **_kwargs: object) -> None:
        if self._fail is not None:
            raise self._fail
        self.lines.append(args)

    def print_exception(self, exc: object, *_file: object) -> None:
        self.tracebacks.append(exc)


def _raised(exc: BaseException) -> BaseException:
    # The exception as asyncio hands it over: raised once, so it carries a traceback.
    try:
        raise exc
    except BaseException as caught:
        return caught


def _genuine_memory_error() -> BaseException:
    # A real allocation failure under a locked heap, the death the report exists for.
    caught: BaseException | None = None
    micropython.heap_lock()
    try:
        bytearray(16)
    except MemoryError as e:
        caught = e
    finally:
        micropython.heap_unlock()
    assert caught is not None, "bytearray() allocated with the heap locked"
    return caught


def _context(exc: object) -> "_Context":
    return {"message": _UNRETRIEVED, "exception": exc, "future": object()}


def _call_cost() -> int:
    # What one empty two-argument Python call allocates on this binary: 0, except build-settrace's frame
    # object per call (Part E.5.2), so "allocates nothing" holds the report to exactly that cost.
    def empty(_loop: object, _context: object) -> None:
        pass

    empty(None, None)
    gc.collect()
    before = gc.mem_alloc()
    empty(None, None)
    return gc.mem_alloc() - before


def _call_locked(report: "Callable[[object, _Context], None]", context: "_Context") -> None:
    micropython.heap_lock()
    try:
        report(None, context)
    finally:
        micropython.heap_unlock()


def _settled_alloc() -> int:
    # Read in sync scope after asyncio.run() returned: the run's own main task, which can keep a stale
    # link to the last task queued under it (py/pairheap.c leaves child_last set), is gone by then.
    gc.collect()
    return gc.mem_alloc()


def test_start_and_check_tasks_installs_the_report_when_no_handler_is_set() -> None:
    svc = make_service()
    with _HandlerSlot(None):
        _supervised(svc, [_long_lived_starter], 5)
        installed = asyncio.get_event_loop().get_exception_handler()
    assert installed == svc.pr.report_unretrieved, installed
    context = _context(_raised(ValueError("probe")))
    assert installed is not None
    installed(None, context)
    assert context["exception"] is None and context["future"] is None


def test_start_and_check_tasks_never_replaces_an_installed_handler() -> None:
    def keep(_loop: object, _context: "_Context") -> None:
        pass

    with _HandlerSlot(keep):
        _supervised(make_service(), [_long_lived_starter], 5)
        assert asyncio.get_event_loop().get_exception_handler() is keep


def test_the_report_prints_nothing_at_level_0_and_releases_the_dead_task() -> None:
    svc = make_service()
    assert svc.pr.level == 0
    for exc in (_raised(ValueError("probe")), _genuine_memory_error()):
        context = _context(exc)
        with _ReportRecorder() as recorder:
            svc.pr.report_unretrieved(None, context)
        assert recorder.lines == [] and recorder.tracebacks == [], (recorder.lines, recorder.tracebacks)
        assert context == {"message": _UNRETRIEVED, "exception": None, "future": None}, context


def test_from_level_1_the_report_prints_one_line_and_the_traceback() -> None:
    for level in (_ERR, _WARN, _EVENT, _ALL):
        svc = make_service()
        assert svc.pr.set_level(level)
        exc = _raised(ValueError("probe"))
        context = _context(exc)
        with _ReportRecorder() as recorder:
            svc.pr.report_unretrieved(None, context)
        assert recorder.lines == [("SYSTEM", _UNRETRIEVED)], (level, recorder.lines)
        assert recorder.tracebacks == [exc], (level, recorder.tracebacks)
        assert context["exception"] is None and context["future"] is None, level


def test_the_report_returns_and_releases_the_task_with_the_heap_locked() -> None:
    # Level 1 prints for real here: both exceptions are worded clear of the memory gate's markers, and a
    # genuine allocation failure is taken at level 0 only, where nothing prints.
    cases = (
        (0, _raised(ValueError("probe"))),
        (0, _genuine_memory_error()),
        (0, _raised(_ExhaustionError("simulated allocation failure"))),
        (_ERR, _raised(ValueError("probe"))),
        (_ERR, _raised(_ExhaustionError("simulated allocation failure"))),
    )
    for level, exc in cases:
        svc = make_service()
        assert svc.pr.set_level(level)
        context = _context(exc)
        _call_locked(svc.pr.report_unretrieved, context)
        assert context["exception"] is None and context["future"] is None, (level, exc)


def test_the_reports_outputs_allocate_nothing() -> None:
    # The body's two calls under a locked heap with no handler to swallow a failure, then the whole
    # report with the heap open: nothing it does may leave an allocation behind.
    exc = _raised(ValueError("probe"))
    micropython.heap_lock()
    try:
        print("SYSTEM", _UNRETRIEVED)
        sys.print_exception(exc)
    finally:
        micropython.heap_unlock()
    for level in (0, _ERR):
        svc = make_service()
        assert svc.pr.set_level(level)
        context = _context(exc)
        cost = _call_cost()
        gc.collect()
        before = gc.mem_alloc()
        svc.pr.report_unretrieved(None, context)
        after = gc.mem_alloc()
        assert after - before == cost, (level, after - before, cost)


def test_a_report_that_cannot_print_still_releases_the_task_and_never_raises() -> None:
    svc = make_service()
    assert svc.pr.set_level(_ERR)
    context = _context(_raised(ValueError("probe")))
    with _ReportRecorder(fail=RuntimeError("console gone")):
        svc.pr.report_unretrieved(None, context)
    assert context["exception"] is None and context["future"] is None
    bare: _Context = {}
    svc.pr.report_unretrieved(None, bare)  # the missing "message" raises before anything prints
    assert bare == {"exception": None, "future": None}, bare
    for level in (0, _ERR):
        assert svc.pr.set_level(level)
        svc.pr.report_unretrieved(None, None)  # type: ignore[arg-type]  # not even a dict: the clearing raises too


async def _dies(n: int) -> None:
    # Every other death is a genuine allocation failure; every fourth holds a large local in its frame.
    if n % 2:
        micropython.heap_lock()
        try:
            bytearray(16)
        finally:
            micropython.heap_unlock()
    held = bytearray(_LARGE_LOCAL if n % 4 == 0 else 16)
    raise ValueError("probe", len(held))


def _deaths(n_tasks: int, *, first: int = 0) -> None:
    # Detached tasks that die with nobody awaiting them: each reaches the loop's exception handler.
    async def scenario() -> None:
        tasks = [asyncio.create_task(_dies(n)) for n in range(first, first + n_tasks)]  # held, never awaited
        for _ in range(_SETTLE_YIELDS):
            await asyncio.sleep(0)
        assert all(task.done() for task in tasks)

    run(scenario())


def test_a_thousand_unretrieved_deaths_through_the_real_loop_retain_nothing() -> None:
    # Level 0, the deployed default: silent, so the genuine allocation failures never reach the console.
    svc = make_service()
    with _HandlerSlot(None):
        _supervised(svc, [_long_lived_starter], 5)
        assert asyncio.get_event_loop().get_exception_handler() == svc.pr.report_unretrieved
        _deaths(_HAMMER_TASKS)  # first-use allocations land before the baseline
        drift = [0] * _HAMMER_ROUNDS  # sized before the baseline: a growing list would read as drift
        baseline = _settled_alloc()
        for i in range(_HAMMER_ROUNDS):
            _deaths(_HAMMER_TASKS)
            drift[i] = _settled_alloc() - baseline
        context = asyncio_core._exc_context
        assert context["exception"] is None and context["future"] is None, context
    assert max(drift) <= _HAMMER_DRIFT_BYTES, drift


def test_the_report_releases_the_dead_task_the_default_handler_keeps() -> None:
    svc = make_service()
    try:
        with _HandlerSlot(svc.pr.report_unretrieved):
            _deaths(1)  # warm-up, and leaves asyncio's context clear
            before = _settled_alloc()
            _deaths(1)
            released = _settled_alloc() - before
        with _HandlerSlot(None):  # asyncio's default handler, which prints this one probe
            before = _settled_alloc()
            _deaths(1)
            kept = _settled_alloc() - before
    finally:
        svc.pr.report_unretrieved(None, asyncio_core._exc_context)  # later tests start from a clear context
    assert kept >= _LARGE_LOCAL, kept
    assert released <= _HAMMER_DRIFT_BYTES, released


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
