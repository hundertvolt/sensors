"""Isolated-driver device script: the bench build's whole graph over its scratch config, its tasks and timers started
with the RP2040's alarm pool emptied: each failed arm is handled in place and none resets, the uptime ticks on, and
mempause still answers. Facts first; no flash write but the scratch build's own."""

import asyncio
import errno
import os

import _bench_device as device  # rendered: the bench device's generated module
import machine

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable

    from _shared.facts import done, fact
    from _shared.watchdog import arm

_SCRATCH_CFG_PATH = "hwtest-scratch/"
_POOL_BOUND = 64  # an upper bound only: the pool holds 16 alarms (pico-sdk pico/time.h), fewer are free
_POLL_MS = 100
_WAIT_MS = 20_000  # each wait below polls its state at most this long; the supervisor feeds meanwhile


def _empty_pool() -> "list[machine.Timer]":
    # Timers armed until the pool refuses one with ENOMEM (timer_alarm_pool_exhaustion.py); the hogs, released later.
    hogs: list[machine.Timer] = []
    try:
        for _ in range(_POOL_BOUND):
            t = machine.Timer()
            t.init(period=600_000, callback=lambda _t: None)  # 10 min: never fires while held
            hogs.append(t)
    except OSError as exc:
        if exc.args and exc.args[0] == errno.ENOMEM:
            return hogs
        raise
    raise RuntimeError("the alarm pool never ran out")


async def _until(check: "Callable[[], bool]", what: str) -> None:
    # Polls `check()` every _POLL_MS until it holds or _WAIT_MS passes; the outcome as a fact.
    waited = 0
    while not check() and waited < _WAIT_MS:
        await asyncio.sleep_ms(_POLL_MS)
        waited += _POLL_MS
    fact(what, check())


async def _main() -> None:
    wdt = arm()
    try:  # an aborted run's leftover first (none: ENOENT)
        for name in os.listdir(_SCRATCH_CFG_PATH):
            os.remove(_SCRATCH_CFG_PATH + name)
        os.rmdir(_SCRATCH_CFG_PATH)
    except OSError as e:
        if e.errno != errno.ENOENT:
            fact("leftover_errno", e.errno)
    os.mkdir(_SCRATCH_CFG_PATH)
    running: list[asyncio.Task[None]] = []
    hogs: list[machine.Timer] = []
    try:
        await device.build_system(watchdog=wdt, cfg_path=_SCRATCH_CFG_PATH, web_host="127.0.0.1", web_port=8080)
        sysfunct = device.sysfunct
        if sysfunct is None:
            raise RuntimeError("the generated build constructed no SystemService")
        await sysfunct.run_setups(device._collect_setups())
        before = (await sysfunct.get_error_counter())["SYSTEM"]["ErrCount"]
        hogs = _empty_pool()
        fact("pool_free", len(hogs))
        await sysfunct.start_tasks(device._collect_task_starters(), task_names=device._collect_task_names())
        await sysfunct.start_timers(device._collect_trigger_starters(), device._collect_timer_starters())
        fact("timers_started", True)  # start_timers() returned: every starter ran
        running.append(asyncio.create_task(sysfunct.supervise_tasks()))
        counter = sysfunct._uptime
        uptime = counter.read()
        await _until(lambda: counter.read() > uptime, "uptime_rose")
        fact("mempause", await device._system_cmd_callback("mempause"))
        fram = device.fram
        fact("paused", None if fram is None else fram.get_pause())
        system = (await sysfunct.get_error_counter())["SYSTEM"]
        fact("system_gained", system["ErrCount"] - before)
        fact("system", system)
        for t in hogs:
            t.deinit()
        hogs = []
        fact("tasks_alive", all(task is not None and not task.done() for task in sysfunct._tasks))
        fact("reset_armed", sysfunct._phase >= 3)  # _PHASE_ARMED
    except Exception as e:  # a failure before the verdict: reported, then the cleanup below
        fact("failure", repr(e))
    finally:
        for t in hogs:
            t.deinit()
        for task in running:
            task.cancel()
        for task in getattr(getattr(device, "sysfunct", None), "_tasks", None) or []:
            if task is not None:
                task.cancel()
        await asyncio.sleep_ms(_POLL_MS)  # the cancelled tasks end before the scratch directory goes
        pixel = getattr(device, "neopixel", None)  # the build constructs the rig's NeoPixel where the TOML wires one
        if pixel is not None:
            pixel.off()
        for name in os.listdir(_SCRATCH_CFG_PATH):
            os.remove(_SCRATCH_CFG_PATH + name)
        os.rmdir(_SCRATCH_CFG_PATH)
        phase = machine.mem_backup(1)  # build_system()'s boot-phase mark: the next boot must not read a boot failure
        for i in range(len(phase)):
            phase[i] = 0
        done()


asyncio.run(_main())
