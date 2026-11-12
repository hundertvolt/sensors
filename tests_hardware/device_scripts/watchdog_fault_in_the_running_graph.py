"""Isolated-driver device script: the product's main() over the bench build's scratch config, then one fault inside the
running system after the supervisor's first feed - "main_exit" cancels main() under the live loop, "supervisor_raise"
makes the dead-task report raise - and the loop runs on unfed until the watchdog resets."""

import asyncio
import errno
import os

import _bench_device as device  # rendered: the bench device's generated module
import machine

# @include _shared/facts.py
# @include _shared/watchdog.py
# @include _shared/unretrieved.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact
    from _shared.unretrieved import report_unretrieved
    from _shared.watchdog import _WDT_TIMEOUT_MS, arm
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

_SCRATCH_CFG_PATH = "hwtest-scratch/"
_MODES = ("main_exit", "supervisor_raise")
_POLL_MS = 100
_READY_WAIT_MS = 60_000  # the scratch boot's construction, setups and task start, fed by the product throughout
_ROUND_MS = 500
_UNFED_ROUNDS = 3 * _WDT_TIMEOUT_MS // _ROUND_MS  # well past the watchdog's period: the reset ends the run first


class _CountingWatchdog:
    # The real watchdog, fed only through this wrapper, so each feed the product makes is counted.
    def __init__(self, wdt: machine.WDT) -> None:
        self._wdt = wdt
        self.feeds = 0

    def feed(self) -> None:
        self.feeds += 1
        self._wdt.feed()


async def _raising_report(_task: object, _n: int) -> None:
    raise RuntimeError("the supervisor's dead-task report raised (a test-only watchdog fault)")


def _tasks_started() -> bool:
    tasks = getattr(getattr(device, "sysfunct", None), "_tasks", None)
    if not tasks:
        return False
    return None not in tasks


async def _main() -> None:
    report_unretrieved()
    watchdog = _CountingWatchdog(arm())
    mode = BENCH.get("mode", "main_exit")
    fact("mode", mode)
    try:  # an aborted run's leftover first (none: ENOENT)
        for name in os.listdir(_SCRATCH_CFG_PATH):
            os.remove(_SCRATCH_CFG_PATH + name)
        os.rmdir(_SCRATCH_CFG_PATH)
    except OSError as e:
        if e.errno != errno.ENOENT:
            fact("leftover_errno", e.errno)
    os.mkdir(_SCRATCH_CFG_PATH)
    main_task = None
    try:
        if mode not in _MODES:
            raise ValueError("unknown mode " + mode)
        main_task = asyncio.create_task(device.main(watchdog=watchdog, cfg_path=_SCRATCH_CFG_PATH, web_host="127.0.0.1", web_port=8080))  # type: ignore[arg-type]  # duck-typed: feed() alone
        waited = 0
        while not _tasks_started() and waited < _READY_WAIT_MS:
            await asyncio.sleep_ms(_POLL_MS)
            waited += _POLL_MS
        sysfunct = getattr(device, "sysfunct", None)  # a module global main() assigns as it constructs
        if sysfunct is None or not _tasks_started():
            raise RuntimeError("the scratch boot never started its tasks")
        fed = watchdog.feeds
        while watchdog.feeds == fed and waited < _READY_WAIT_MS:  # the supervisor's first feed once every task exists
            await asyncio.sleep_ms(_POLL_MS)
            waited += _POLL_MS
        if watchdog.feeds == fed:
            raise RuntimeError("the supervisor never fed once every task existed")
        fact("fed_at_fault", watchdog.feeds)
        if mode == "supervisor_raise":
            sysfunct._log_dead_task = _raising_report  # the fault, planted from outside
            next(task for task in sysfunct._tasks if task is not None).cancel()
        else:
            main_task.cancel()  # as if main() returned: the loop and its tasks run on
        for n in range(_UNFED_ROUNDS):  # each round proves the loop alive: the feeds so far, and what has ended
            await asyncio.sleep_ms(_ROUND_MS)
            supervisor = sysfunct._supervisor_task
            fact("round_" + str(n), {"feeds": watchdog.feeds, "main": main_task.done(), "supervisor": supervisor is not None and supervisor.done()})
        fact("no_reset_after_ms", _UNFED_ROUNDS * _ROUND_MS)
    except Exception as e:  # a failure before the fault: reported, then the cleanup below
        fact("failure", repr(e))
    finally:
        # Reached only without the reset: the graph stopped, the scratch directory and the boot-phase mark gone.
        if main_task is not None:
            main_task.cancel()
        for task in getattr(getattr(device, "sysfunct", None), "_tasks", None) or []:
            if task is not None:
                task.cancel()
        await asyncio.sleep_ms(_POLL_MS)
        pixel = getattr(device, "neopixel", None)  # the build constructs the rig's NeoPixel where the TOML wires one
        if pixel is not None:
            pixel.off()
        for name in os.listdir(_SCRATCH_CFG_PATH):
            os.remove(_SCRATCH_CFG_PATH + name)
        os.rmdir(_SCRATCH_CFG_PATH)
        phase = machine.mem_backup(1)
        for i in range(len(phase)):
            phase[i] = 0
        done()


asyncio.run(_main())
