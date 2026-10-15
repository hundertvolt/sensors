"""Isolated-driver device script: a shutdown step that never returns, over the bench build's scratch config. One store's
delete_file ("resetconfig") or flush_pending ("reboot") is replaced from outside by a coroutine that never ends; the
watchdog, fed by the shutdown alone, must reset the board - the host reads the HANG line and the reset code after."""

import asyncio
import errno
import os
import time

import _bench_device as device  # rendered: the bench device's generated module
import machine

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact
    from _shared.watchdog import _WDT_TIMEOUT_MS, arm
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

_SCRATCH_CFG_PATH = "hwtest-scratch/"
_COMMANDS = ("resetconfig", "reboot")
_WAIT_STEP_MS = 100
_RESET_WAIT_MS = 2 * _WDT_TIMEOUT_MS  # unfed: past the watchdog, which must end the run first
_started = time.ticks_ms()


async def _hang() -> bool:
    # The replaced step: entered after the shutdown's last own feed, so the watchdog's period starts about here.
    print("HANG", time.ticks_diff(time.ticks_ms(), _started))
    await asyncio.Event().wait()
    return False


async def _main() -> None:
    wdt = arm()
    command = BENCH.get("COMMAND", "resetconfig")
    fact("command", command)
    try:  # an aborted run's leftover first (none: ENOENT)
        for name in os.listdir(_SCRATCH_CFG_PATH):
            os.remove(_SCRATCH_CFG_PATH + name)
        os.rmdir(_SCRATCH_CFG_PATH)
    except OSError as e:
        if e.errno != errno.ENOENT:
            fact("leftover_errno", e.errno)
    os.mkdir(_SCRATCH_CFG_PATH)
    running: list[asyncio.Task[None]] = []  # stopped on any exit without the reset
    try:
        if command not in _COMMANDS:
            raise ValueError("unknown COMMAND " + command)
        await device.build_system(watchdog=wdt, cfg_path=_SCRATCH_CFG_PATH, web_host="127.0.0.1", web_port=8080)
        sysfunct, webserver = device.sysfunct, device.webserver
        if sysfunct is None or webserver is None:
            raise RuntimeError("the generated build constructed no SystemService or webserver")
        await sysfunct.run_setups(device._collect_setups())
        store = sysfunct._config_stores[0]
        fact("hung_store", store.name)
        if command == "resetconfig":
            store.delete_file = _hang  # type: ignore[method-assign]  # the step the shutdown runs fifth
        else:
            store.flush_pending = _hang  # type: ignore[method-assign, assignment]  # the step the shutdown runs second
        await sysfunct.start_tasks(device._collect_task_starters())
        running.append(asyncio.create_task(sysfunct.supervise_tasks()))  # the shutdown's first step waits for it to park
        answer = await webserver._dispatch_system_cmd(command)
        fact("answer", answer)
        if answer == "Valid":
            for _ in range(_RESET_WAIT_MS // _WAIT_STEP_MS):  # the product owns the feed from here: never fed
                await asyncio.sleep_ms(_WAIT_STEP_MS)
            fact("no_reset_after_ms", _RESET_WAIT_MS)
    except Exception as e:  # a pre-reset failure: reported, then the cleanup below
        fact("failure", repr(e))
    finally:
        for task in running:
            task.cancel()
        # Reached only without the reset: the scratch directory and build_system()'s boot-phase mark go, the rig dark.
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
