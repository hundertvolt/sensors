import asyncio

import machine
from _fram_chip_fake import FakeMB85RS64V
from machine import Timer

# Same one-process-per-test-file swap as test_base_classes.py/test_asy_fram_manager.py.
import asy_spi_driver
import system_service
from asy_fram_manager import AsyFramManager
from asy_spi_driver import SPI
from print_log import PrintLog, PrintLogHistory, PrintLogHistoryStore
from system_service import SystemService

asy_spi_driver._SPI = FakeMB85RS64V  # type: ignore[misc]

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


def make_ntp_stub(
    synced: bool = False, raise_exc: "Exception | None" = None
) -> "tuple[Callable[[], Coroutine[Any, Any, bool]], list[int]]":
    calls = [0]

    async def _ntp() -> bool:
        calls[0] += 1
        if raise_exc is not None:
            raise raise_exc
        return synced

    return _ntp, calls


def make_service(ntp: "Callable[[], Coroutine[Any, Any, bool]] | None" = None, **kwargs: "Any") -> SystemService:
    if ntp is None:
        ntp, _calls = make_ntp_stub(synced=False)
    return SystemService(ntp, **kwargs)


def make_fram_manager(max_size: int = 0x2000) -> "tuple[AsyFramManager, FakeMB85RS64V]":
    bus = SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    manager = AsyFramManager(bus, 1, max_size=max_size)
    chip = manager.fram._spidev.spi._spi
    assert isinstance(chip, FakeMB85RS64V)
    return manager, chip


async def _pump(flag: "asyncio.ThreadSafeFlag", ticks: int, settle: int = 5) -> None:
    # Drives a ThreadSafeFlag-gated loop (status_counter) forward `ticks` times without relying on
    # real elapsed time - `settle` extra sleep(0) yields per tick let every await point in one loop
    # iteration resolve before the flag is set again (verified directly against the built
    # interpreter: a single sleep(0) isn't always enough to drain a multi-await iteration).
    for _ in range(ticks):
        flag.set()
        for _ in range(settle):
            await asyncio.sleep(0)


class _FastAsyncSleep:
    # start_and_check_tasks() staggers task startup by 1.0/len(task_starters) real seconds and
    # checks tasks every real _TASK_CHECK_TIME=2s - both far too slow for a test that just wants
    # to drive a handful of supervisor cycles. asyncio.sleep is a shared, process-wide function
    # (unlike the per-module `time` swap above, there's exactly one to patch); restored on
    # __exit__ regardless of how the `with` block exits.
    def __enter__(self) -> "_FastAsyncSleep":
        self._real_sleep = asyncio.sleep

        async def _fast(_seconds: float) -> None:
            await self._real_sleep(0)

        asyncio.sleep = _fast  # type: ignore[assignment]  # deliberate monkeypatch, not a real caller mismatch
        return self

    def __exit__(self, *exc_info: "Any") -> None:
        asyncio.sleep = self._real_sleep


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


def test_init_uses_in_memory_logging_when_fram_is_none() -> None:
    svc = make_service()
    assert isinstance(svc.pr, PrintLogHistory)
    assert svc.storage_pause is None


def test_init_uses_fram_backed_logging_and_wires_storage_pause_when_fram_given() -> None:
    manager, _chip = make_fram_manager()
    svc = make_service(fram=manager)
    assert isinstance(svc.pr, PrintLogHistoryStore)
    assert svc.storage_pause is not None
    # Bound-method identity isn't guaranteed (each attribute access can mint a fresh bound-method
    # object) - confirm by behavior instead: calling svc.storage_pause must reach manager's own state.
    svc.storage_pause(True)
    assert manager.get_pause() is True
    svc.storage_pause(False)
    assert manager.get_pause() is False


def test_init_debug_level_is_forwarded_to_the_logger() -> None:
    svc = make_service(debug=PrintLog.level_err())
    assert svc.pr.get_level() == PrintLog.level_err()


def test_init_history_length_is_forwarded() -> None:
    svc = make_service(history_length=3)
    assert len(svc.pr.history) == 3


def test_init_watchdog_is_stored() -> None:
    wdt = machine.WDT()
    svc = make_service(watchdog=wdt)
    assert svc.watchdog is wdt


def test_init_without_watchdog_defaults_to_none() -> None:
    svc = make_service()
    assert svc.watchdog is None


# ---------------------------------------------------------------------------
# get_uptime / get_boot_signature - before status_counter ever runs
# ---------------------------------------------------------------------------


def test_get_uptime_initial_value_is_zero_before_status_counter_runs() -> None:
    svc = make_service()
    assert run(svc.get_uptime()) == 0


def test_get_boot_signature_initial_value_before_status_counter_runs() -> None:
    svc = make_service()
    assert run(svc.get_boot_signature()) == 1  # LockedValue(1)'s own constructor default


# ---------------------------------------------------------------------------
# _ntp_boot_signature
# ---------------------------------------------------------------------------


def test_ntp_boot_signature_not_synced_returns_none() -> None:
    ntp, _calls = make_ntp_stub(synced=False)
    svc = make_service(ntp)
    assert run(svc._ntp_boot_signature()) is None
    assert svc.pr.err_count == 0


def test_ntp_boot_signature_synced_returns_a_real_utc_timestamp() -> None:
    ntp, _calls = make_ntp_stub(synced=True)
    svc = make_service(ntp)
    result = run(svc._ntp_boot_signature())
    assert isinstance(result, int)
    assert result > 1_700_000_000  # sanity bound: after 2023-11-14, not the pre-refactor's magic -1/1
    assert svc.pr.err_count == 0


def test_ntp_boot_signature_callback_exception_returns_none_and_logs_once() -> None:
    ntp, calls = make_ntp_stub(raise_exc=RuntimeError("ntp callback exploded"))
    svc = make_service(ntp)
    assert run(svc._ntp_boot_signature()) is None
    assert calls[0] == 1
    assert svc.pr.err_count == 1


class _OverflowingTime:
    # MicroPython's real `time` module is a read-only builtin (confirmed directly: assigning
    # time.mktime = ... raises AttributeError) - can't monkeypatch an attribute onto it, so this
    # replaces system_service's own module-level `time` name instead (a plain, mutable module
    # global, unlike the builtin module it points to).
    def gmtime(self) -> "Any":
        import time as _real_time

        return _real_time.gmtime()

    def mktime(self, _t: "Any") -> int:
        raise OverflowError("past rp2's ~2037 32-bit epoch range")


def test_ntp_boot_signature_mktime_overflow_returns_none_and_logs_once() -> None:
    ntp, _calls = make_ntp_stub(synced=True)
    svc = make_service(ntp)
    original_time = system_service.time
    system_service.time = _OverflowingTime()  # type: ignore[assignment]  # deliberate monkeypatch, not a real caller mismatch
    try:
        result = run(svc._ntp_boot_signature())
    finally:
        system_service.time = original_time
    assert result is None
    assert svc.pr.err_count == 1


# ---------------------------------------------------------------------------
# status_counter - full loop, driven via _pump() instead of real elapsed time
# ---------------------------------------------------------------------------


def test_status_counter_increments_uptime_every_tick() -> None:
    svc = make_service()

    async def scenario() -> int:
        task = asyncio.create_task(svc.status_counter())
        await _pump(svc.uptime_event, 5)
        uptime = await svc.get_uptime()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return uptime

    assert run(scenario()) == 5


def test_status_counter_sets_boot_signature_via_ntp_once_synced() -> None:
    ntp, _calls = make_ntp_stub(synced=True)
    svc = make_service(ntp)

    async def scenario() -> "tuple[bool, int]":
        task = asyncio.create_task(svc.status_counter())
        await _pump(svc.uptime_event, 1)
        signature = await svc.get_boot_signature()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return svc.start_time_set, signature

    start_time_set, signature = run(scenario())
    assert start_time_set is True
    assert signature > 1_700_000_000


def test_status_counter_before_wait_time_never_synced_leaves_boot_signature_unresolved() -> None:
    ntp, _calls = make_ntp_stub(synced=False)
    svc = make_service(ntp)

    async def scenario() -> "tuple[bool, int]":
        task = asyncio.create_task(svc.status_counter())
        await _pump(svc.uptime_event, 5)  # well below _NTP_WAIT_TIME (120)
        signature = await svc.get_boot_signature()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return svc.start_time_set, signature

    start_time_set, signature = run(scenario())
    assert start_time_set is False
    assert signature == -1  # status_counter's own "not yet resolved" sentinel


def test_status_counter_falls_back_to_random_after_wait_time_when_never_synced() -> None:
    ntp, _calls = make_ntp_stub(synced=False)
    svc = make_service(ntp)

    async def scenario() -> "tuple[bool, int]":
        task = asyncio.create_task(svc.status_counter())
        await _pump(svc.uptime_event, 120)  # exactly _NTP_WAIT_TIME - boundary is accepted, not rejected
        signature = await svc.get_boot_signature()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return svc.start_time_set, signature

    start_time_set, signature = run(scenario())
    assert start_time_set is True
    assert signature != -1


def test_status_counter_callback_exception_is_treated_as_not_synced_and_still_falls_back() -> None:
    ntp, calls = make_ntp_stub(raise_exc=RuntimeError("ntp callback exploded"))
    svc = make_service(ntp)

    async def scenario() -> "tuple[bool, int]":
        task = asyncio.create_task(svc.status_counter())
        await _pump(svc.uptime_event, 120)
        signature = await svc.get_boot_signature()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return svc.start_time_set, signature

    start_time_set, signature = run(scenario())
    assert start_time_set is True
    assert signature != -1
    assert calls[0] == 120  # every tick retried the callback until the wait-time fallback resolved it
    assert svc.pr.err_count == 120  # each retry logged its own failure - bounded by print_log.py's own history/count caps


def test_status_counter_stops_checking_ntp_once_start_time_is_set() -> None:
    ntp, calls = make_ntp_stub(synced=True)
    svc = make_service(ntp)

    async def scenario() -> int:
        task = asyncio.create_task(svc.status_counter())
        await _pump(svc.uptime_event, 4)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return calls[0]

    assert run(scenario()) == 1  # resolved on tick 1, never rechecked on ticks 2-4


# ---------------------------------------------------------------------------
# _timer_sequencer / start_timers
# ---------------------------------------------------------------------------


def test_start_timers_empty_list_sets_timers_running_without_crashing() -> None:
    svc = make_service()
    Timer.all_timers.clear()
    run(svc.start_timers([]))
    assert Timer.all_timers == []  # no chain timer ever created for an empty starter list


def test_start_timers_single_starter_needs_no_chain_timer() -> None:
    svc = make_service()
    Timer.all_timers.clear()
    started = []
    run(svc.start_timers([lambda: started.append(1)]))
    assert started == [1]
    assert Timer.all_timers == []


def test_start_timers_sequences_all_starters_in_order_and_sets_timers_running() -> None:
    svc = make_service()
    Timer.all_timers.clear()
    started: list[int] = []
    starters = [lambda: started.append(1), lambda: started.append(2), lambda: started.append(3)]

    async def scenario() -> bool:
        task = asyncio.create_task(svc.start_timers(starters))
        await asyncio.sleep(0)  # let start_timers begin: _timer_sequencer starts timer[0] synchronously
        assert started == [1]
        assert len(Timer.all_timers) == 1
        Timer.all_timers[-1].trigger()
        assert started == [1, 2]
        assert len(Timer.all_timers) == 2
        Timer.all_timers[-1].trigger()
        assert started == [1, 2, 3]
        await task  # completes now: timers_running was set by the last _timer_sequencer step
        return True

    assert run(scenario())


def test_timer_sequencer_starter_exception_is_logged_and_sequencing_continues() -> None:
    svc = make_service()
    Timer.all_timers.clear()
    started: list[int] = []

    def bad_starter() -> None:
        raise RuntimeError("boom")

    starters = [bad_starter, lambda: started.append(2)]

    async def scenario() -> bool:
        task = asyncio.create_task(svc.start_timers(starters))
        await asyncio.sleep(0)
        assert started == []  # bad_starter raised, never appended
        assert len(Timer.all_timers) == 1
        Timer.all_timers[-1].trigger()
        assert started == [2]  # sequencing continued to the next starter regardless
        await task
        return True

    assert run(scenario())  # must not raise despite bad_starter's exception


# ---------------------------------------------------------------------------
# reboot_system / reboot_bootloader / pause_permanent_storage
# ---------------------------------------------------------------------------


def test_reboot_system_without_fram_arms_reset_timer_and_fires_machine_reset() -> None:
    svc = make_service()
    machine.reset_count = 0
    svc.reboot_system()
    assert svc.reset_timer.mode == Timer.ONE_SHOT
    assert svc.reset_timer.period == 4 * 1000  # _RESET_DELAY: micropython.const(), compiled away, hardcoded per tests/README.md
    assert machine.reset_count == 0  # not yet fired - a real Timer would still be counting down
    svc.reset_timer.trigger()
    assert machine.reset_count == 1


def test_reboot_system_with_fram_pauses_storage_before_arming_the_reset() -> None:
    manager, _chip = make_fram_manager()
    svc = make_service(fram=manager)
    machine.reset_count = 0
    svc.reboot_system()
    assert manager.get_pause() is True  # paused immediately, before the reset timer ever fires
    svc.reset_timer.trigger()
    assert machine.reset_count == 1


def test_reboot_system_cancels_any_pending_storage_unpause_timer() -> None:
    manager, _chip = make_fram_manager()
    svc = make_service(fram=manager)
    svc.pause_permanent_storage(60)
    assert svc.storage_timer.deinit_called is False
    svc.reboot_system()
    assert svc.storage_timer.deinit_called is True


def test_reboot_bootloader_arms_reset_timer_and_fires_machine_bootloader() -> None:
    svc = make_service()
    machine.bootloader_count = 0
    svc.reboot_bootloader()
    assert machine.bootloader_count == 0
    svc.reset_timer.trigger()
    assert machine.bootloader_count == 1


def test_reboot_bootloader_with_fram_pauses_storage_before_arming_the_reset() -> None:
    manager, _chip = make_fram_manager()
    svc = make_service(fram=manager)
    machine.bootloader_count = 0
    svc.reboot_bootloader()
    assert manager.get_pause() is True  # paused immediately, before the reset timer ever fires
    svc.reset_timer.trigger()
    assert machine.bootloader_count == 1


def test_pause_permanent_storage_without_fram_is_a_no_op() -> None:
    svc = make_service()
    svc.pause_permanent_storage(100)
    assert svc.storage_timer.period == -1  # never armed


def test_pause_permanent_storage_zero_duration_immediately_unpauses() -> None:
    manager, _chip = make_fram_manager()
    svc = make_service(fram=manager)
    svc.pause_permanent_storage(0)
    assert manager.get_pause() is False


def test_pause_permanent_storage_negative_duration_is_clamped_to_zero_and_immediately_unpauses() -> None:
    manager, _chip = make_fram_manager()
    svc = make_service(fram=manager)
    svc.pause_permanent_storage(-5)
    assert manager.get_pause() is False


def test_pause_permanent_storage_clamps_to_the_max() -> None:
    manager, _chip = make_fram_manager()
    svc = make_service(fram=manager)
    svc.pause_permanent_storage(999_999)
    assert svc.storage_timer.period == 3600 * 1000  # _MAX_STORAGE_PAUSE: compiled away, hardcoded


def test_pause_permanent_storage_exact_max_boundary_is_accepted_not_clamped_further() -> None:
    manager, _chip = make_fram_manager()
    svc = make_service(fram=manager)
    svc.pause_permanent_storage(3600)
    assert svc.storage_timer.period == 3600 * 1000  # _MAX_STORAGE_PAUSE: compiled away, hardcoded


def test_pause_permanent_storage_valid_duration_pauses_then_auto_unpauses_when_timer_fires() -> None:
    manager, _chip = make_fram_manager()
    svc = make_service(fram=manager)
    svc.pause_permanent_storage(60)
    assert manager.get_pause() is True
    assert svc.storage_timer.period == 60 * 1000
    svc.storage_timer.trigger()
    assert manager.get_pause() is False


# ---------------------------------------------------------------------------
# get_task_starters / get_timer_starters
# ---------------------------------------------------------------------------


def test_stop_uptime_timer_deinits_the_timer() -> None:
    svc = make_service()
    svc.start_uptime_timer()
    assert svc.uptime_timer.deinit_called is False
    svc.stop_uptime_timer()
    assert svc.uptime_timer.deinit_called is True


def test_get_task_starters_starter_returns_a_real_task() -> None:
    svc = make_service()

    async def scenario() -> None:
        starters = svc.get_task_starters()
        assert len(starters) == 1
        task = starters[0]()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    run(scenario())


def test_get_timer_starters_starter_arms_the_uptime_timer() -> None:
    svc = make_service()
    starters = svc.get_timer_starters()
    assert len(starters) == 1
    starters[0]()
    assert svc.uptime_timer.mode == Timer.PERIODIC
    assert svc.uptime_timer.period == 1000


# ---------------------------------------------------------------------------
# get_error_counter / reset_error_counter
# ---------------------------------------------------------------------------


def test_get_error_counter_reflects_logged_errors_and_reset_clears_them() -> None:
    # history_length=1: get_log() always reports the full (fixed-length) history deque, not just
    # the entries actually written - a length-1 history is what makes "just one error" also
    # produce a length-1 ErrNum/ErrType, matching this test's single err_s() call exactly.
    svc = make_service(history_length=1)
    run(svc.pr.setup())
    run(svc.pr.err_s("boom", errno=1))
    result = run(svc.get_error_counter())
    assert result == {"Tasks": {"ErrCount": 1, "ErrNum": [1], "ErrType": ["E"]}}
    run(svc.reset_error_counter())
    assert svc.pr.err_count == 0


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
    assert svc.pr.err_count == 1


# ---------------------------------------------------------------------------
# start_and_check_tasks
# ---------------------------------------------------------------------------


def test_start_and_check_tasks_empty_starters_never_fails() -> None:
    svc = make_service(watchdog=machine.WDT())

    async def scenario() -> None:
        task = asyncio.create_task(svc.start_and_check_tasks([]))
        await asyncio.sleep(0)
        assert svc.watchdog is not None
        assert svc.watchdog.feed_count >= 1
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    with _FastAsyncSleep():
        run(scenario())


def test_start_and_check_tasks_feeds_the_watchdog_while_tasks_stay_alive() -> None:
    wdt = machine.WDT()
    svc = make_service(watchdog=wdt)

    def long_lived_starter() -> "asyncio.Task[None]":
        async def _c() -> None:
            await asyncio.sleep(3600)

        return asyncio.create_task(_c())

    async def scenario() -> None:
        task = asyncio.create_task(svc.start_and_check_tasks([long_lived_starter]))
        for _ in range(10):
            await asyncio.sleep(0)
        assert wdt.feed_count >= 1
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    with _FastAsyncSleep():
        run(scenario())


def test_start_and_check_tasks_without_watchdog_does_not_raise() -> None:
    svc = make_service(watchdog=None)

    def long_lived_starter() -> "asyncio.Task[None]":
        async def _c() -> None:
            await asyncio.sleep(3600)

        return asyncio.create_task(_c())

    async def scenario() -> None:
        task = asyncio.create_task(svc.start_and_check_tasks([long_lived_starter]))
        for _ in range(10):
            await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    with _FastAsyncSleep():
        run(scenario())  # must not raise despite watchdog being None


def test_start_and_check_tasks_restarts_a_dead_task_and_logs_a_warning() -> None:
    svc = make_service()
    call_count = [0]

    def quick_dying_starter() -> "asyncio.Task[None]":
        call_count[0] += 1

        async def _c() -> None:
            return None

        return asyncio.create_task(_c())

    async def scenario() -> None:
        task = asyncio.create_task(svc.start_and_check_tasks([quick_dying_starter]))
        for _ in range(10):
            await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    with _FastAsyncSleep():
        run(scenario())
    assert call_count[0] >= 2  # started once at startup, restarted at least once after dying
    assert svc.pr.err_count >= 1  # the "Task wurde beendet" warning persisted


def test_start_and_check_tasks_gives_up_and_reboots_past_the_failure_budget() -> None:
    # Reaching _TASK_FAIL_MAX (300, incrementing by 100 per restart) takes several real
    # _TASK_CHECK_TIME=2s cycles - both consts are micropython.const() and compiled away (see
    # tests/README.md), so they can't be monkeypatched, only asyncio.sleep itself can.
    svc = make_service()
    call_count = [0]

    def always_raising_starter() -> "asyncio.Task[None]":
        call_count[0] += 1
        raise RuntimeError("starter always fails")

    machine.reset_count = 0
    with _FastAsyncSleep():
        run(asyncio.wait_for(svc.start_and_check_tasks([always_raising_starter]), 5))

    assert call_count[0] >= 4  # enough restart attempts to cross _TASK_FAIL_MAX (100 per attempt)
    svc.reset_timer.trigger()
    assert machine.reset_count == 1


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
