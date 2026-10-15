"""Isolated-driver device script: an "erasefram" whose second erase unit raises OSError(EIO), over the bench build's
scratch config. The shutdown step dies unfed, so the watchdog resets the board and the next boot must read code 9, the
record written as the command passed the gate; FRAM only, no flash write beyond the scratch setups, the facts first."""

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
    from _shared.facts import done, fact
    from _shared.watchdog import _WDT_TIMEOUT_MS, arm
    from bench_facts import BenchFacts

    from asy_fram_driver import FRAM_SPI

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

_SCRATCH_CFG_PATH = "hwtest-scratch/"
# asy_fram_manager.py's _ERASE_UNIT: a const() whose name starts with "_" is no module global on MicroPython, so it
# cannot be imported and is restated here.
_ERASE_UNIT = 256
_FAILING_UNIT = 2
_WAIT_STEP_MS = 100
_RESET_WAIT_MS = 2 * _WDT_TIMEOUT_MS  # unfed: past the watchdog, which must end the run first


def _fail_unit(driver: "FRAM_SPI") -> None:
    # From outside: the erase's per-unit write raises as a dying SPI transfer would, at the second unit only.
    original = driver.set_values_sync
    units = [0]

    def write(buf: "bytes | bytearray | memoryview", addr_start: int) -> int:
        if len(buf) == _ERASE_UNIT and not any(buf):
            units[0] += 1
            if units[0] == _FAILING_UNIT:
                fact("raised_at", addr_start)
                raise OSError(errno.EIO)
        return original(buf, addr_start)

    driver.set_values_sync = write  # type: ignore[method-assign]


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
    running: list[asyncio.Task[None]] = []  # stopped on any exit without the reset
    try:
        await device.build_system(watchdog=wdt, cfg_path=_SCRATCH_CFG_PATH, web_host="127.0.0.1", web_port=8080)
        sysfunct, webserver, fram = device.sysfunct, device.webserver, device.fram
        if sysfunct is None or webserver is None or fram is None:
            raise RuntimeError("the generated build constructed no SystemService, webserver or FRAM")
        await sysfunct.run_setups(device._collect_setups())
        _fail_unit(fram.fram)
        await sysfunct.start_tasks(device._collect_task_starters())
        running.append(asyncio.create_task(sysfunct.supervise_tasks()))  # the shutdown's first step waits for it to park
        answer = await webserver._dispatch_system_cmd("erasefram")
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
