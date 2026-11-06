"""Isolated-driver device script: the bench build's whole graph over its scratch config, its clock set as an NTP sync
leaves it (the client's own success handler), then the RTC stepped under it: BMP3XX stamps, an SGP40 backup's age past
a backward step, cettime() across the March switch, and Synced and LastSyncAge on the ticks across a year's steps."""

import asyncio
import errno
import os
import time

import _bench_device as device  # rendered: the bench device's generated module
import machine

from asy_base_classes import utc_now

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from _shared.facts import done, fact
    from _shared.watchdog import arm
    from bench_facts import BenchFacts

    from asy_sgp40_driver import SGP40_Reader

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

_SCRATCH_CFG_PATH = "hwtest-scratch/"
_POLL_MS = 100
_WAIT_MS = 20_000  # each wait below polls its state at most this long; the supervisor feeds meanwhile
_STEPS_S = (-3600, 86400)  # back an hour, then forward a day, as the twin steps
_DST_START = 1774746000  # 2026-03-29 01:00 UTC, the last Sunday of March: CET to CEST
_YEAR_S = 365 * 86400
_AGE_MIN_S = 2
_BACK_S = 7200  # the step back behind the backup, as the twin steps: its age reads -2 h
_MAX_AGE_MIN = 60  # a BackupMaxAge that refuses it; 0 accepts every age (asy_sgp40_driver.py's age check)


def _set(rtc: machine.RTC, epoch: int) -> None:
    t = time.gmtime(epoch)
    rtc.datetime((t[0], t[1], t[2], t[6], t[3], t[4], t[5], 0))


def _count_restores(sgp: "SGP40_Reader") -> "list[bool]":
    # Each restore the reader decides from here on, in order: True where it applied the backup.
    decisions: list[bool] = []
    original = sgp._run_restore

    async def run_restore(buf: object, *, deserialize: bool, cfg_values: "tuple[int, int, int] | None") -> bool:
        applied = await original(buf, deserialize=deserialize, cfg_values=cfg_values)  # type: ignore[arg-type]  # passed through
        if deserialize:
            decisions.append(applied)
        return applied

    sgp._run_restore = run_restore  # type: ignore[method-assign]  # observed from outside, as reset_code_stack_exhausted.py wraps
    return decisions


async def _until(check: "Callable[[], Awaitable[bool]]", what: str) -> None:
    waited = 0
    while not await check():
        if waited >= _WAIT_MS:
            raise RuntimeError(what + " within " + str(_WAIT_MS) + " ms")
        await asyncio.sleep_ms(_POLL_MS)
        waited += _POLL_MS


async def _backup_age_past_a_step_back(sgp: "SGP40_Reader", rtc: machine.RTC) -> "dict[str, object]":
    # One backup at the running clock, the clock stepped back behind it, then a restore under a max age and under none.
    async def settled() -> bool:  # initialised, a sample read and the boot's own restore attempt over
        return getattr(sgp._datastruct, "Raw", None) is not None and sgp._voc_init == 0

    await _until(settled, "the SGP40 never read and settled its boot restore")
    written = (await sgp.get_mem_status())[0]
    sgp._backup_counter = 59  # BackupPeriod's default of 1 min: the next cycle backs up, as the twin sets it

    async def backed_up() -> bool:
        return (await sgp.get_mem_status())[0] not in (None, written)

    await _until(backed_up, "no SGP40 backup written")
    stamp = (await sgp.get_mem_status())[0]
    _set(rtc, time.time() - _BACK_S)
    decisions = _count_restores(sgp)
    restores = []
    for max_age in (_MAX_AGE_MIN, 0):  # primed in RAM, as sgp40_fram_backup_restore.py primes its schema: no flash I/O
        sgp.cfgmgr._cache["BackupMaxAge"] = max_age
        asked = len(decisions)
        sgp._voc_init = 1  # a restore on the next cycle, as a fresh boot's init asks for one

        async def decided(asked: int = asked) -> bool:
            return len(decisions) > asked

        await _until(decided, "the SGP40 restore was never decided")
        log = (await sgp.get_error_counter())["SGP40"]
        newest = [[kind, num] for kind, num in zip(log["ErrType"], log["ErrNum"]) if kind != "N"][-1:]
        restores.append({"max_age": max_age, "restored": decisions[asked], "from": (await sgp.get_mem_status())[1], "newest": newest})
    return {"stamp": stamp, "restores": restores}


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
    rtc = machine.RTC()
    start, t0 = time.time(), time.ticks_ms()
    try:
        await device.build_system(watchdog=wdt, cfg_path=_SCRATCH_CFG_PATH, web_host="127.0.0.1", web_port=8080)
        sysfunct, ntp = device.sysfunct, getattr(device, "ntp", None)
        reader = next((getattr(device, name) for name in BENCH["instances"] if name.startswith("bmp3xx")), None)
        sgp = next((getattr(device, name) for name in BENCH["instances"] if name.startswith("sgp40")), None)
        if sysfunct is None or ntp is None or reader is None or sgp is None:
            raise RuntimeError("the generated build constructed no SystemService, NTP client, BMP3XX or SGP40 reader")
        await sysfunct.run_setups(device._collect_setups())
        await sysfunct.start_tasks(device._collect_task_starters(), task_names=device._collect_task_names())
        await sysfunct.start_timers(device._collect_trigger_starters(), device._collect_timer_starters())
        running.append(asyncio.create_task(sysfunct.supervise_tasks()))
        await ntp._handle_ntp_sync_success(time.gmtime())  # the clock as a sync leaves it, valid from here on
        synced_at = time.ticks_ms()
        stamps = []
        for step in _STEPS_S:
            _set(rtc, time.time() + step)
            before = reader._datastruct
            reader._read_event.set()  # the next cycle now, as its trigger would within a SampleInterval

            async def fresh(before: object = before) -> bool:
                return reader._datastruct is not before and reader._datastruct.TS is not None

            await _until(fresh, "no BMP3XX sample after the step")
            stamps.append([utc_now(), reader._datastruct.TS])
        fact("stamps", stamps)
        fact("backup", await _backup_age_past_a_step_back(sgp, rtc))
        fact("offsets", await ntp.cfgmgr.get_dict(["GMTOffset", "DSTOffset"]))
        local = []
        for at in (_DST_START - 60, _DST_START + 60, _DST_START - 60):
            _set(rtc, at)
            cet = await ntp.cettime()
            local.append([at, None if cet is None else list(cet[:6])])
        fact("local", local)
        _set(rtc, start + time.ticks_diff(time.ticks_ms(), t0) // 1000)
        _set(rtc, time.time() + _YEAR_S)
        _set(rtc, time.time() - 2 * _YEAR_S)

        async def aged() -> bool:
            age = (await ntp.get_data()).LastSyncAge
            return age is not None and age >= _AGE_MIN_S

        await _until(aged, "LastSyncAge never counted")
        data = await ntp.get_data()
        fact("sync", {"synced": data.Synced, "age": data.LastSyncAge, "ticks_s": time.ticks_diff(time.ticks_ms(), synced_at) // 1000})
    except Exception as e:  # a failure before the verdict: reported, then the cleanup below
        fact("failure", repr(e))
    finally:
        _set(rtc, start + time.ticks_diff(time.ticks_ms(), t0) // 1000)  # the RTC back on its own time
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
