"""Isolated-driver device script: one supervised reader's read coroutine rebound, over the bench build's scratch config,
to recurse until MicroPython's stack check raises; the recorded overflow makes the supervisor reboot with its code, or,
modes "entry_held" and "escape" (no handler records it), SYSTEM's FRAM lock held leaves that code to the watchdog."""

import asyncio
import errno
import os

import _bench_device as device  # rendered: the bench device's generated module
import machine

from asy_print_log import report_if_fatal

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable

    from _shared.facts import done, fact
    from _shared.watchdog import _WDT_TIMEOUT_MS, arm
    from bench_facts import BenchFacts

    from asy_system_service import SystemService

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

_SCRATCH_CFG_PATH = "hwtest-scratch/"
_MODES = ("reboot", "entry_held", "escape")
_WAIT_STEP_MS = 100
_RESET_WAIT_MS = 4 * _WDT_TIMEOUT_MS  # the death, the supervisor's next pass, then the reset delay


def _deep(depth: "list[int]", n: int) -> int:
    depth[0] = n
    return _deep(depth, n + 1) + 1


def _exhaust(reader: object, deaths: "list[int]", *, recorded: bool) -> None:
    # From outside: the reader's read loop becomes a recursion that ends only in the stack check's RuntimeError, which
    # its handler records before the raise, as a reader's broad handler does (src/asy_print_log.py report_if_fatal()).
    async def read_loop() -> None:
        depth = [0]
        try:
            _deep(depth, 0)
        except RuntimeError as e:
            deaths.append(depth[0])
            if recorded:  # "escape": unrecorded, the error ends the task and the supervisor's dead-task entry meets it
                report_if_fatal(e)
            raise

    reader._read_loop = read_loop  # type: ignore[attr-defined]


async def _main() -> None:
    wdt = arm()
    mode = BENCH.get("mode", "reboot")
    fact("mode", mode)
    try:  # an aborted run's leftover first (none: ENOENT)
        for name in os.listdir(_SCRATCH_CFG_PATH):
            os.remove(_SCRATCH_CFG_PATH + name)
        os.rmdir(_SCRATCH_CFG_PATH)
    except OSError as e:
        if e.errno != errno.ENOENT:
            fact("leftover_errno", e.errno)
    os.mkdir(_SCRATCH_CFG_PATH)
    running: list[asyncio.Task[None]] = []  # stopped on any exit without the reset
    deaths: list[int] = []
    try:
        if mode not in _MODES:
            raise ValueError("unknown mode " + mode)
        await device.build_system(watchdog=wdt, cfg_path=_SCRATCH_CFG_PATH, web_host="127.0.0.1", web_port=8080)
        sysfunct = device.sysfunct
        if sysfunct is None:
            raise RuntimeError("the generated build constructed no SystemService")
        await sysfunct.run_setups(device._collect_setups())
        if mode != "reboot":
            chunk = getattr(sysfunct.pr, "fram", None)
            if chunk is None:
                raise RuntimeError("SYSTEM's logger has no FRAM chunk, so no entry write of its can be held")
            await chunk._op_lock.acquire()  # never released: the escalation's or dead-task entry write waits on it for good
            fact("held", True)
        label = next(name for name in BENCH["instances"] if hasattr(getattr(device, name, None), "_read_loop"))
        fact("reader", label)
        _exhaust(getattr(device, label), deaths, recorded=mode != "escape")
        _wrap_reboot(sysfunct, deaths)
        await sysfunct.start_tasks(device._collect_task_starters(), task_names=device._collect_task_names())
        running.append(asyncio.create_task(sysfunct.supervise_tasks()))
        for _ in range(_RESET_WAIT_MS // _WAIT_STEP_MS):  # the supervisor feeds until its escalation starves the watchdog
            await asyncio.sleep_ms(_WAIT_STEP_MS)
        fact("no_reset_after_ms", _RESET_WAIT_MS)
    except Exception as e:  # a pre-reset failure: reported, then the cleanup below
        fact("failure", repr(e))
    finally:
        for task in running:
            task.cancel()
        # Reached only without the reset: the scratch directory and build_system()'s boot-phase mark go, the rig dark.
        fact("deaths", deaths)
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


def _wrap_reboot(sysfunct: "SystemService", deaths: "list[int]") -> None:
    original = sysfunct._reboot

    async def reboot(code: int, message: str, action: "Callable[[], None]", *, fed: bool = False) -> None:
        await original(code, message, action, fed=fed)
        fact("reset", {"code": code, "deaths": deaths})

    sysfunct._reboot = reboot  # type: ignore[method-assign]


asyncio.run(_main())
