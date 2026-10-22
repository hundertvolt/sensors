"""Isolated-driver device script: "reboot" or "bootloader" (COMMAND) through the webserver's dispatch over the bench
build's scratch config at DebugLevel 4, so the shutdown's step lines print, with a logger-write loop and an I2C read
loop in flight and a recording proxy in SystemService's watchdog slot; the product reset ends the run, the facts first.
"""

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
    from collections.abc import Callable

    from _shared.facts import done, fact
    from _shared.watchdog import _WDT_TIMEOUT_MS, arm
    from bench_facts import BenchFacts

    from asy_i2c_driver import I2C
    from asy_system_service import SystemService

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

E_TEST_SEED_A = 125
E_TEST_SEED_B = 126
_SCRATCH_CFG_PATH = "hwtest-scratch/"
_COMMANDS = ("reboot", "bootloader")
_STATES = ("idle", "mempause")
_DEBUG = 4  # the shutdown's step lines are event lines
_WRITTEN_KEPT = 32  # the newest written entries reported: a ring holds far fewer
_LOAD_STEP_MS = 20
_WAIT_STEP_MS = 100
_RESET_WAIT_MS = 2 * _WDT_TIMEOUT_MS  # unfed: past the command's own reset and any watchdog takeover


class _FeedRecorder:
    """Forwards every feed to the armed watchdog; keeps the count, the largest gap and when the last feed came."""

    def __init__(self, wdt: machine.WDT) -> None:
        self._wdt = wdt
        self.last = time.ticks_ms()
        self.count = 0
        self.max_gap_ms = 0

    def feed(self) -> None:
        now = time.ticks_ms()
        self.max_gap_ms = max(self.max_gap_ms, time.ticks_diff(now, self.last))
        self.last = now
        self.count += 1
        self._wdt.feed()


async def _loads(sysfunct: "SystemService", written: "list[int]", bus_counts: "list[int]", stop: "list[bool]") -> None:
    # In flight through the shutdown, never fed: per round one SYSTEM chunk write, its code recorded once the call returned,
    # and a one-byte read of the first addressed I2C instance under its bus lock (reads and faults counted).
    target = next(i for i in BENCH["instances"].values() if "address" in i and i["bus"].startswith("i2c"))
    bus: I2C = getattr(device, target["bus"])
    buf = bytearray(1)
    n = 0
    while not stop[0]:  # set once the reset is armed: the paused chunk layer refuses every write after it
        code = E_TEST_SEED_A if n % 2 else E_TEST_SEED_B
        await sysfunct.pr.err_s("load", errno=code)
        written.append(code)
        if len(written) > _WRITTEN_KEPT:
            written.pop(0)
        try:
            async with bus.bus_lock:
                bus.readfrom_into(target["address"], buf)
            bus_counts[0] += 1
        except OSError:
            bus_counts[1] += 1
        n += 1
        await asyncio.sleep_ms(_LOAD_STEP_MS)


async def _main() -> None:
    wdt = arm()
    command, state = BENCH.get("COMMAND", "reboot"), BENCH.get("STATE", "idle")
    fact("command", command)
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
    try:
        if command not in _COMMANDS or state not in _STATES:
            raise ValueError("unknown COMMAND or STATE " + command + " " + state)
        await device.build_system(watchdog=wdt, cfg_path=_SCRATCH_CFG_PATH, debug=_DEBUG, web_host="127.0.0.1", web_port=8080)
        sysfunct, webserver = device.sysfunct, device.webserver
        if sysfunct is None or webserver is None:
            raise RuntimeError("the generated build constructed no SystemService or webserver")
        await sysfunct.run_setups(device._collect_setups())
        for set_level in sysfunct._level_setters:  # the scratch store's default level won at setup: raised again, unwritten
            set_level(_DEBUG)
        recorder = _FeedRecorder(wdt)
        sysfunct._watchdog = recorder  # type: ignore[assignment]  # a recording stand-in: every feed still reaches the WDT
        written: list[int] = []
        bus_counts = [0, 0]  # reads, faults
        stop = [False]
        _wrap_reboot(sysfunct, recorder, written, bus_counts, stop)
        await sysfunct.start_tasks(device._collect_task_starters(), task_names=device._collect_task_names())
        running.append(asyncio.create_task(sysfunct.supervise_tasks()))  # the shutdown's first step waits for it to park
        running.append(asyncio.create_task(_loads(sysfunct, written, bus_counts, stop)))
        await asyncio.sleep_ms(10 * _LOAD_STEP_MS)
        if state == "mempause":
            fact("mempause", await webserver._dispatch_system_cmd("mempause"))
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


def _wrap_reboot(sysfunct: "SystemService", recorder: _FeedRecorder, written: "list[int]", bus_counts: "list[int]", stop: "list[bool]") -> None:
    # From outside: once the reset is armed (its last feed included), the feeds and the loads are reported.
    original = sysfunct._reboot

    async def reboot(code: int, message: str, action: "Callable[[], None]", *, fed: bool = False) -> None:
        await original(code, message, action, fed=fed)
        stop[0] = True
        fact("reset", {"code": code, "feeds": recorder.count, "max_gap_ms": recorder.max_gap_ms, "bus": bus_counts})
        fact("written", {"SYSTEM": written})

    sysfunct._reboot = reboot  # type: ignore[method-assign]


asyncio.run(_main())
