"""Isolated-driver device script: "erasefram" through the webserver's dispatch over the bench build's scratch config,
every FRAM-backed logger seeded with a test-band ring first; a recording proxy in SystemService's watchdog slot times
each feed. STATE picks the in-flight loads, a mempause, the refusals, or a reset armed mid-erase; facts stream first."""

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

    from asy_fram_manager import FRAMManager
    from asy_i2c_driver import I2C
    from asy_system_service import SystemService
    from asy_webserver_service import WebserverService

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

E_TEST_SEED_A = 125
E_TEST_SEED_B = 126
E_TEST_SEED_C = 127
_SEED = (E_TEST_SEED_A, E_TEST_SEED_B, E_TEST_SEED_C)  # distinct codes: a ring cut short shows as a shorter run
_SCRATCH_CFG_PATH = "hwtest-scratch/"
_STATES = ("idle", "loads", "mempause", "refusals")
_RESET_AFTER = "reset_after_"  # STATE prefix: the erase is cut by a reset this many ms after it starts
# Whole-string equality is the dispatch's one check: each of these is one edit away from a command word.
_NEAR_MISSES = ("Reboot", "reboot ", "REBOOT", "erase", "erasefram!", "eraseFRAM", "resetConfig", "boot", "", "mempause1", 1, None)
_REFUSAL_WAIT_MS = 10000  # unfed, past the watchdog: a refused command never stops the supervisor's feed
_LOAD_STEP_MS = 20
_WAIT_STEP_MS = 100
_RESET_WAIT_MS = 2 * _WDT_TIMEOUT_MS  # unfed: past the command's own reset and any watchdog takeover


class _RecordingWatchdog:
    """Forwards every feed to the armed watchdog; keeps the largest gap between feeds, overall and inside the erase."""

    def __init__(self, wdt: machine.WDT) -> None:
        self._wdt = wdt
        self.last = time.ticks_ms()
        self.feeds = 0
        self.max_gap_ms = 0
        self.erase_max_gap_ms = 0
        self.erasing = False

    def feed(self) -> None:
        now = time.ticks_ms()
        gap = time.ticks_diff(now, self.last)
        self.max_gap_ms = max(self.max_gap_ms, gap)
        if self.erasing:
            self.erase_max_gap_ms = max(self.erase_max_gap_ms, gap)
        self.last = now
        self.feeds += 1
        self._wdt.feed()


async def _loads(sysfunct: "SystemService", counts: "list[int]", stop: "list[bool]") -> None:
    # In flight through the shutdown, never fed: per round one SYSTEM chunk write (two test-band codes in turn, equal ones
    # would collapse) and a one-byte read of the first addressed I2C instance under its bus lock; counts writes, reads, faults.
    target = next(i for i in BENCH["instances"].values() if "address" in i and i["bus"].startswith("i2c"))
    bus: I2C = getattr(device, target["bus"])
    buf = bytearray(1)
    while not stop[0]:  # set once the reset is armed: the paused chunk layer refuses every write after it
        await sysfunct.pr.err_s("load", errno=_SEED[counts[0] % 2])
        counts[0] += 1
        try:
            async with bus.bus_lock:
                bus.readfrom_into(target["address"], buf)
            counts[1] += 1
        except OSError:
            counts[2] += 1
        await asyncio.sleep_ms(_LOAD_STEP_MS)


async def _main() -> None:
    wdt = arm()
    state = BENCH.get("STATE", "idle")
    fact("state", state)
    reset_after = int(state[len(_RESET_AFTER) :]) if state.startswith(_RESET_AFTER) else None
    try:  # an aborted run's leftover first (none: ENOENT)
        for name in os.listdir(_SCRATCH_CFG_PATH):
            os.remove(_SCRATCH_CFG_PATH + name)
        os.rmdir(_SCRATCH_CFG_PATH)
    except OSError as e:
        if e.errno != errno.ENOENT:
            fact("leftover_errno", e.errno)
    os.mkdir(_SCRATCH_CFG_PATH)
    running: list[asyncio.Task[None]] = []  # stopped on any exit without the reset
    loads = [0, 0, 0]  # load writes, bus reads, bus faults
    stop = [False]
    try:
        if state not in _STATES and reset_after is None:
            raise ValueError("unknown STATE " + state)
        await device.build_system(watchdog=wdt, cfg_path=_SCRATCH_CFG_PATH, web_host="127.0.0.1", web_port=8080)
        sysfunct, webserver, fram = device.sysfunct, device.webserver, device.fram
        if sysfunct is None or webserver is None or fram is None:
            raise RuntimeError("the generated build constructed no SystemService, webserver or FRAM")
        await sysfunct.run_setups(device._collect_setups())
        fact("layout", {"allocated": fram._allocated_size, "size": fram.size})
        if state != "refusals":  # a refused erase blanks nothing, so nothing is seeded that would stay behind
            await _seed(sysfunct)
        proxy = _RecordingWatchdog(wdt)
        sysfunct._watchdog = proxy  # type: ignore[assignment]  # a recording stand-in: every feed still reaches the WDT
        _wrap(sysfunct, fram, proxy, reset_after, loads, stop)
        await sysfunct.start_tasks(device._collect_task_starters(), task_names=device._collect_task_names())
        running.append(asyncio.create_task(sysfunct.supervise_tasks()))  # the shutdown's first step waits for it to park
        if state == "refusals":
            await _refusals(webserver, fram)
            return
        if state == "loads":
            running.append(asyncio.create_task(_loads(sysfunct, loads, stop)))
            await asyncio.sleep_ms(10 * _LOAD_STEP_MS)
        if state == "mempause":
            fact("mempause", await webserver._dispatch_system_cmd("mempause"))
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
        fact("loads", loads)
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


async def _refusals(webserver: "WebserverService", fram: "FRAMManager") -> None:
    # The near misses answer "Invalid"; an erase of a write-protected chip "Failed"; neither stops the feed.
    answers = []
    for word in _NEAR_MISSES:  # one at a time: MicroPython has no await inside a comprehension
        answers.append([repr(word), await webserver._dispatch_system_cmd(word)])
    fact("near_misses", answers)
    fact("protect", await fram.fram.set_write_protected(value=True))
    try:
        fact("protected_answer", await webserver._dispatch_system_cmd("erasefram"))
        for _ in range(_REFUSAL_WAIT_MS // _WAIT_STEP_MS):  # unfed by the script: the supervisor's feed carries it
            await asyncio.sleep_ms(_WAIT_STEP_MS)
        fact("survived_unfed_ms", _REFUSAL_WAIT_MS)
    finally:
        fact("unprotect", await fram.fram.set_write_protected(value=False))


async def _seed(sysfunct: "SystemService") -> None:
    # The test-band ring into every FRAM-backed logger, so the host can tell an erased chunk from a kept one.
    loggers = [logger for label in BENCH["fram_wired"] for logger in getattr(device, label).get_loggers() if getattr(logger, "fram", None) is not None]
    for logger in loggers:
        await logger.err_s("seed", errno=E_TEST_SEED_A)
        await logger.err_s("seed", errno=E_TEST_SEED_B)
        await logger.err_s("seed", errno=E_TEST_SEED_C)
    fact("seeded", sorted(logger.name for logger in loggers))
    fact("seeded_system", (await sysfunct.get_error_counter())["SYSTEM"])


def _wrap(sysfunct: "SystemService", fram: "FRAMManager", proxy: _RecordingWatchdog, reset_after: "int | None", loads: "list[int]", stop: "list[bool]") -> None:
    # From outside: the erase prints its start and its figures, an armed reset cuts it, the arm reports feeds and loads.
    original_erase, original_reboot = fram.erase_chip, sysfunct._reboot
    cut = machine.Timer()

    async def erase(step_done: "Callable[[], None]") -> bool:
        print("ERASE START")
        proxy.erasing = True
        started = time.ticks_ms()
        if reset_after is not None:
            cut.init(period=reset_after, mode=machine.Timer.ONE_SHOT, callback=lambda _t: machine.reset(), hard=True)
        ok = await original_erase(step_done)
        proxy.erasing = False
        fact("erase", {"ok": ok, "ms": time.ticks_diff(time.ticks_ms(), started), "max_gap_ms": proxy.erase_max_gap_ms})
        return ok

    async def reboot(code: int, message: str, action: "Callable[[], None]", *, fed: bool = False) -> None:
        await original_reboot(code, message, action, fed=fed)
        stop[0] = True
        fact("reset", {"code": code, "feeds": proxy.feeds, "max_gap_ms": proxy.max_gap_ms, "loads": loads})

    fram.erase_chip = erase  # type: ignore[method-assign]
    sysfunct._reboot = reboot  # type: ignore[method-assign]


asyncio.run(_main())
