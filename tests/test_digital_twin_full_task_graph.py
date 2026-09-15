"""Real, full task-graph digital-twin tests - split into their own file/process (not part of
test_digital_twin_sensortask_integration.py) because driving every real task_starter concurrently
leaks enough real, un-cancellable-from-outside asyncio/socket state into this Unix-port process's
shared task queue to intermittently hang unrelated, later tests sharing that same process - see the
module docstring notes on both tests below for the full account and CLAUDE.md's own "Known hang
cause" entries for the general class of problem this is."""

import asyncio
import gc
import json
import os
import sys

sys.path.insert(0, "ext")  # same convention as test_sensortask.py's own comment - reaches the
# real, vendored ext/microdot.py that sensortask_wozi.py transitively imports.
sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port

# Must run before AsyUDPSocket is constructed (DNSServer, inside AsyConnTime.__init__ below): this
# Unix-port build rejects a plain (host, port) tuple in bind()/connect()/sendto() (SPECIFICATION.md
# Part A.10), a twin-side workaround since AsyUDPSocket's own addr is correct production code.
patch_asy_udp_socket_for_unix_port()

import machine  # noqa: E402
import sensortask_wozi  # noqa: E402

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, TypeVar

    from system_service import SystemService

    T = TypeVar("T")


def run_timed(coro: "Coroutine[Any, Any, T]", timeout_s: float) -> "T":
    return asyncio.run(asyncio.wait_for(coro, timeout_s))


# Same _tmp_cfg_dir()/_next_test_port() shape as test_digital_twin_sensortask_integration.py's own
# (and every other digital-twin test file's) - kept here rather than shared, since this file's own
# two tests are its only callers and the whole point of the split is zero shared runtime state.
_TMP_DIR = "tests/_tmp"
_next_dir = 0
_next_port = 19700  # a fixed, non-privileged test-only range, disjoint from every other digital-twin
# test file's own range (grep confirms no overlap) - a fresh port per test avoids TIME_WAIT reuse.


def _tmp_cfg_dir() -> str:
    global _next_dir
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass
    _next_dir += 1
    path = _TMP_DIR + "/dtftg_" + str(_next_dir)
    try:
        os.mkdir(path)
    except OSError:
        pass
    return path + "/"


def _next_test_port() -> int:
    global _next_port
    _next_port += 1
    return _next_port


def _wiring_plan(device: str) -> "dict[str, Any]":
    with open(f"build/generated_src/sensortask_{device}_wiring_plan.json") as f:
        plan: dict[str, Any] = json.load(f)
    return plan


async def _boot(port: int) -> None:
    machine.configure_wiring(_wiring_plan("wozi"))
    await sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=port)


async def _cancel(task: "asyncio.Task[Any]") -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def _wait_until(predicate: "Callable[[], bool]", timeout_s: float, interval_s: float = 0.25) -> bool:
    # Bounded polling helper - same shape as test_digital_twin_sensortask_integration.py's own.
    elapsed = 0.0
    while elapsed < timeout_s:
        if predicate():
            return True
        await asyncio.sleep(interval_s)
        elapsed += interval_s
    return predicate()


# ---------------------------------------------------------------------------
# Watchdog escalation - a short, real, fully-supervised run (owner decision 7: automated assertion
# *and* manually observable - the manual side lives in digital_twin/run_generic_integration.py
# (--module sensortask_wozi --wiring-plan ... --device wozi), this is the automated side).
#
# Deliberately does NOT drive this through sensortask_wozi.main()/start_and_check_tasks(): a real
# regression found while building this file - MicroPython's globals() does not preserve
# definition order (confirmed directly: this file's own test_* functions ran in a different order
# than written), so "the last test in the file" is not actually "the last test to run", and
# start_and_check_tasks() keeps its own started tasks in a local variable with no way for a caller
# to reach and cancel them - main_task.cancel() only ever cancelled the *outer* wrapper coroutine,
# leaving every real task it had started (webserver server, sensor timers, WDT countdown, ...)
# running in the background for the rest of this process. Across the other tests' own repeated
# build_system() calls (each allocating a fresh 8KB FramChip, fresh ConfigManagers, ...), those
# orphaned tasks' lingering references were enough to starve the Unix-port heap - a real
# MemoryError once, and a hard interpreter segfault once (with a `run()`-inside-`run()` bug of this
# file's own stacked on top - see git history for the full story). Fix: start exactly the same real
# task starters sensortask_wozi.main() itself would, but keep every one of them in a list this test
# owns and explicitly cancels in `finally`. Runs its own small watchdog-feed loop rather than
# start_and_check_tasks()'s own (already covered by tests/test_system_service.py) - this test's own
# job is only "does the real, twin-backed object graph's real concurrent tasks ever block the event
# loop long enough to starve a feed loop running alongside them", which needs the real tasks
# running for real but not that specific feed implementation.
#
# Split into this dedicated file (2026-09-15, alongside the task-supervisor-restart test below):
# even with every task this test itself starts cancelled in `finally`, running this test and its
# sibling below in the SAME process as test_digital_twin_sensortask_integration.py's other ~35
# lighter tests intermittently hung one of those later, unrelated tests - confirmed directly by
# bisection (disabling both real-full-task-graph tests made the other file pass 38/38 cleanly every
# time; running just these two alone, repeatedly, in their own process never hangs). The exact
# interpreter-level mechanism (something below the Python level - gc.collect() between every test
# does not prevent it) wasn't pinned down further; scripts/test.sh already runs one Unix-port
# process per tests/test_*.py file specifically to contain this class of problem (CLAUDE.md's
# "Known hang cause #2"), so giving these two their own file is the same fix already established
# for the general case, not a new mechanism.
# ---------------------------------------------------------------------------


async def _feed_watchdog_periodically(watchdog: "machine.WDT") -> None:
    while True:
        watchdog.feed()
        await asyncio.sleep(1.0)


def test_watchdog_is_never_starved_while_every_real_task_runs_concurrently() -> None:
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        assert sensortask_wozi.watchdog is not None and sensortask_wozi.sysfunct is not None
        await sensortask_wozi.sysfunct.start_timers(sensortask_wozi._collect_timer_starters())
        # Each starter already returns its own asyncio.Task (system_service.py's own _start_task()
        # calls them exactly this way - `return starter()`, no extra create_task() wrapping).
        tasks = [starter() for starter in sensortask_wozi._collect_task_starters()]
        tasks.append(asyncio.get_event_loop().create_task(_feed_watchdog_periodically(sensortask_wozi.watchdog)))
        try:
            await asyncio.sleep(9.0)  # just over the hardcoded 8000ms WDT timeout - long enough that
            # a real, unintended stall (not just this test's own feed loop existing) is what keeps
            # the count at 0, not merely "not enough wall-clock time has passed yet".
            assert sensortask_wozi.watchdog.would_have_triggered_count == 0
        finally:
            for task in tasks:
                await _cancel(task)
            # Defensive, same as the task-supervisor-restart test below: conn.start_asy_wlan_connect
            # (one of the real task_starters above) can independently reach real hotspot activation
            # and start its own real DNSServer task, spawned internally by AsyConnTime rather than
            # through the tracked `tasks` list.
            if sensortask_wozi.conn is not None and sensortask_wozi.conn.dns_server_task is not None:
                await _cancel(sensortask_wozi.conn.dns_server_task)
            gc.collect()

    run_timed(scenario(), timeout_s=15.0)


# ---------------------------------------------------------------------------
# Task-supervisor restart, end-to-end (BACKLOG.md "Whole-system integration test scope") - a real
# task drawn from the REAL, full _collect_task_starters() list (build_system()'s own real object
# graph, not a hand-built/synthetic task list) actually dying and being rediscovered/restarted by
# SystemService.start_and_check_tasks()'s own real supervisor loop, via the real get_task_starters()
# indirection - not a fake of the supervisor itself. The one test in this file that starts the real
# full task list through the real supervisor rather than a hand-picked subset.
# ---------------------------------------------------------------------------


def test_start_and_check_tasks_restarts_a_real_dead_task_from_the_real_full_task_list() -> None:
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        assert sensortask_wozi.sysfunct is not None and sensortask_wozi.bmp3xx is not None
        sysfunct = sensortask_wozi.sysfunct
        task_starters = sensortask_wozi._collect_task_starters()  # the REAL, full list - every
        # constructed module's own get_task_starters(), exactly what main() itself would use.

        started: dict[int, list[Any]] = {}  # values are asyncio.Task[Any] | None - real _start_task()'s own return type
        from system_service import SystemService

        real_start_task = SystemService._start_task

        async def _tracking_start_task(self: "SystemService", starter: "Callable[[], asyncio.Task[Any]]", n: "int") -> "asyncio.Task[Any] | None":
            # Observes the real supervisor's own real task-(re)start calls without changing its
            # behavior at all - the same non-invasive class-method-wrap convention
            # test_sensortask.py's own FRAM-chunk-order test already uses.
            task = await real_start_task(self, starter, n)
            started.setdefault(n, []).append(task)
            return task

        SystemService._start_task = _tracking_start_task  # type: ignore[method-assign]
        supervisor_task = asyncio.get_event_loop().create_task(sysfunct.start_and_check_tasks(task_starters))
        try:
            # bmp3xx.start_asy_trigger's own task (_base_trigger()) is just a real event-wait
            # loop with no I/O and no Timer armed in this test (start_timers() was never called) -
            # a real, side-effect-free task to kill and watch get restarted. The real restart logic
            # itself (start_and_check_tasks()) never inspects which task died or why, only
            # task.done(), so this pick is representative of any real task in the list.
            target_idx = task_starters.index(sensortask_wozi.bmp3xx.start_asy_trigger)
            assert await _wait_until(lambda: target_idx in started, timeout_s=5.0), (
                "the real task was never started by the real supervisor at all"
            )
            assert len(started[target_idx]) == 1
            first_task = started[target_idx][0]
            assert first_task is not None and not first_task.done()

            first_task.cancel()  # a real task genuinely ending - the same observable state
            # (task.done() == True) a real crash would leave behind; start_and_check_tasks() only
            # ever inspects .done(), never *why* a task ended.
            assert await _wait_until(lambda: len(started[target_idx]) == 2, timeout_s=6.0), (
                "start_and_check_tasks() never rediscovered and restarted the real dead task"
            )
            second_task = started[target_idx][1]
            assert second_task is not None
            assert second_task is not first_task
            assert not second_task.done()
        finally:
            SystemService._start_task = real_start_task  # type: ignore[method-assign]
            await _cancel(supervisor_task)  # only cancels the outer wrapper (see the watchdog
            # test's own module comment above) - every real started task is cancelled individually
            # below too.
            for tasks in started.values():
                for task in tasks:
                    if task is not None:
                        await _cancel(task)
            # Defensive: the real, unmodified wlan_connect task (started as part of the real full
            # list above) can independently reach real hotspot activation and start its own real
            # DNSServer task within this test's own window - not cancelled by the loop above since
            # it's spawned internally by AsyConnTime, not through _start_task().
            if sensortask_wozi.conn is not None and sensortask_wozi.conn.dns_server_task is not None:
                await _cancel(sensortask_wozi.conn.dns_server_task)
            gc.collect()

    run_timed(scenario(), timeout_s=20.0)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
