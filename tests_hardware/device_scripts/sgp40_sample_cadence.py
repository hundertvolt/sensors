"""Isolated-driver device script: SGP40 read cycles counted over ten minutes of the bench device's real task graph,
booted over a scratch config directory, so a merged soft-timer tick shows as a lost algorithm sample (SPECIFICATION.md
M.3). Report only, no threshold; the device's own FRAM chunks are written (the session saved them first)."""

import asyncio
import errno
import os
import time
from array import array

import _bench_device as device  # rendered: the bench device's generated module
import machine

from asy_system_service import BOOT_SETUP, BOOT_TASKS, BOOT_TIMERS

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact
    from _shared.watchdog import arm, fed_sleep_ms

# @tunable l3.sgp40_sample_cadence_window_s = 600
_WINDOW_S = 600
# Two slots per expected cycle: a run that somehow reads faster than 1 Hz still never grows the array.
# @tunable l3.sgp40_sample_cadence_slots = 1200
_SLOTS = 1200
# A gap this long means at least one 1 s tick was merged into the next one.
# @tunable l3.sgp40_sample_cadence_gap_ms = 1500
_GAP_MS = 1500
# start_timers() waits on its stagger timers with no timeout of its own: a task here, polled in fed steps.
# @tunable l3.sgp40_sample_cadence_timers_timeout_s = 15
_TIMERS_TIMEOUT_S = 15
# @tunable l3.sgp40_sample_cadence_timers_poll_ms = 100
_TIMERS_POLL_MS = 100
# A scratch directory: every setup() finds its file absent here and writes its defaults once, never a production file.
_SCRATCH_CFG_PATH = "hwtest-scratch/"


async def _main() -> None:
    stamps = array("I", range(_SLOTS))  # ms since base, sized once from the range's length; a record allocates nothing
    count = [0]
    wdt = arm()
    try:  # an aborted run's leftover first (none: ENOENT)
        for name in os.listdir(_SCRATCH_CFG_PATH):
            os.remove(_SCRATCH_CFG_PATH + name)
        os.rmdir(_SCRATCH_CFG_PATH)
    except OSError as e:
        if e.errno != errno.ENOENT:
            fact("leftover_errno", e.errno)
    os.mkdir(_SCRATCH_CFG_PATH)
    try:
        await device.build_system(watchdog=wdt, cfg_path=_SCRATCH_CFG_PATH, web_host="127.0.0.1", web_port=8080)
        sgp40, sysfunct = device.sgp40, device.sysfunct
        fact("built", sgp40 is not None and sysfunct is not None)
        if sgp40 is None or sysfunct is None:
            return
        sysfunct.boot_phase(BOOT_SETUP)
        await sysfunct.run_setups(device._collect_setups())
        # FRAM backup at BackupPeriod 1, set on the reader in RAM: the scratch store's default, never a config write.
        sgp40.cfgmgr._cache["BackupPeriod"] = 1
        fact("backup_period_min", sgp40.cfgmgr._cache["BackupPeriod"])
        base = time.ticks_ms()
        inner_read = sgp40._read_sgp

        async def counting_read(*args: object, **kwargs: object) -> object:
            if count[0] < _SLOTS:
                stamps[count[0]] = time.ticks_diff(time.ticks_ms(), base)  # well inside ticks_diff()'s horizon
                count[0] += 1
            return await inner_read(*args, **kwargs)  # type: ignore[arg-type]

        sgp40._read_sgp = counting_read  # type: ignore[assignment, method-assign]
        sysfunct.boot_phase(BOOT_TASKS)
        await sysfunct.start_tasks(device._collect_task_starters())
        sysfunct.boot_phase(BOOT_TIMERS)
        timers = asyncio.create_task(sysfunct.start_timers(device._collect_trigger_starters(), device._collect_timer_starters()))
        waited_ms = 0
        while not timers.done() and waited_ms < _TIMERS_TIMEOUT_S * 1000:
            await fed_sleep_ms(wdt, _TIMERS_POLL_MS)
            waited_ms += _TIMERS_POLL_MS
        fact("timers_started", timers.done())
        if not timers.done():
            timers.cancel()
            return
        supervisor = asyncio.create_task(sysfunct.supervise_tasks())
        start = time.ticks_ms()
        await fed_sleep_ms(wdt, _WINDOW_S * 1000)
        elapsed = time.ticks_diff(time.ticks_ms(), start)
        supervisor.cancel()
        cycles = count[0]
        gaps = [stamps[i] - stamps[i - 1] for i in range(1, cycles)]
        # No pass threshold: the owner rejected mitigating a dropped soft-timer tick (SPECIFICATION.md M.3).
        fact("cycles", cycles)
        fact("elapsed_ms", elapsed)
        fact("lost", round(elapsed / 1000) - cycles)
        fact("max_gap_ms", max(gaps, default=0))
        fact("gaps_over_1500", sum(1 for gap in gaps if gap > _GAP_MS))
    finally:
        pixel = getattr(device, "neopixel", None)  # the build constructs the rig's NeoPixel where the TOML wires one
        if pixel is not None:
            pixel.off()
        for name in os.listdir(_SCRATCH_CFG_PATH):
            os.remove(_SCRATCH_CFG_PATH + name)
        os.rmdir(_SCRATCH_CFG_PATH)
        # The boot-phase mark the build left: cleared, so the next reset does not read as a boot failure.
        phase = machine.mem_backup(1)
        for i in range(len(phase)):
            phase[i] = 0
    done()


asyncio.run(_main())
