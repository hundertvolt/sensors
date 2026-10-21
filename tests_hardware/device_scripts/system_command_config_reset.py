"""Isolated-driver device script: "resetconfig" through the webserver's dispatch into the generated callback, over the
bench build's scratch config directory, one store's file damaged first. The product's controlled shutdown deletes every
file and its reset ends the run; the host reads the facts printed before it and lists the directory after."""

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

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# A scratch directory: every setup() finds its file absent here and writes its defaults once, never a production file.
_SCRATCH_CFG_PATH = "hwtest-scratch/"
_DAMAGE = b"\x00{not json"  # what a cut write leaves: the delete must remove it without reading it
_STATES = ("idle", "mempause")
_WAIT_STEP_MS = 100
_RESET_WAIT_MS = 2 * _WDT_TIMEOUT_MS  # unfed: past the command's own reset and any watchdog takeover


async def _main() -> None:
    wdt = arm()
    state = BENCH.get("STATE", "idle")
    fact("state", state)
    try:  # an aborted run's leftover first (none: ENOENT)
        for name in os.listdir(_SCRATCH_CFG_PATH):
            os.remove(_SCRATCH_CFG_PATH + name)
        os.rmdir(_SCRATCH_CFG_PATH)
    except OSError as e:
        if e.errno != errno.ENOENT:
            fact("leftover_errno", e.errno)
    os.mkdir(_SCRATCH_CFG_PATH)
    running: list[asyncio.Task[None]] = []  # stopped on any exit without the reset
    answer = ""
    try:
        if state not in _STATES:
            raise ValueError("unknown STATE " + state)
        await device.build_system(watchdog=wdt, cfg_path=_SCRATCH_CFG_PATH, web_host="127.0.0.1", web_port=8080)
        sysfunct, webserver = device.sysfunct, device.webserver
        if sysfunct is None or webserver is None:
            raise RuntimeError("the generated build constructed no SystemService or webserver")
        await sysfunct.run_setups(device._collect_setups())
        files = sorted(os.listdir(_SCRATCH_CFG_PATH))
        fact("scratch_files", files)
        with open(_SCRATCH_CFG_PATH + files[0], "wb") as f:  # the one owned write: a damaged store file
            f.write(_DAMAGE)
        fact("damaged", files[0])
        await sysfunct.start_tasks(device._collect_task_starters(), task_names=device._collect_task_names())
        running.append(asyncio.create_task(sysfunct.supervise_tasks()))  # the shutdown's first step waits for it to park
        if state == "mempause":
            fact("mempause", await webserver._dispatch_system_cmd("mempause"))
        answer = await webserver._dispatch_system_cmd("resetconfig")
        fact("answer", answer)
        if answer == "Valid":
            print("RESETCONFIG ACCEPTED")
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
