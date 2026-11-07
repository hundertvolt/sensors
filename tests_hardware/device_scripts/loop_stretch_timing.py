"""Times the product's routine no-yield stretches on the real chip: a collection over the bench build's full object
graph, one VOC-algorithm step, one CRC32 over a 256-byte chunk. The host holds each under the worst-case collection
pause the UART reply floor budgets (SPECIFICATION.md Part F.3); construction only, no task and no bus I/O."""

import asyncio
import errno
import gc
import os
import time

import _bench_device as device  # rendered: the bench device's generated module
import machine

from asy_crc_checks import CRC32
from voc_algorithm import VOCAlgorithm

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact
    from _shared.watchdog import arm
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# Explicit, never inherited: mpremote's soft reset keeps whatever threshold main.py left.
gc.threshold(-1)
# A scratch directory: construction writes nothing, and every config store points into it, never at a production file.
_SCRATCH_CFG_PATH = "hwtest-scratch/"
_ROUTINE_STALL_US = 21 * 1000  # the J.6 GC term, Part N's uart.gc_pause_worst_ms: the pause the UART reply floor budgets
_GC_RUNS = 5
_VOC_STEPS = 60
_VOC_TIMED = 20  # the last steps, past the algorithm's start-up blackout: the full path
_VOC_RAW = (26000, 26100, 25950, 26050)  # a fixed raw series, no sensor: the pure step
_CRC_BYTES = 256


async def _main() -> None:
    wdt = arm()
    fact("gc_threshold", gc.threshold())
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
        wdt.feed()  # between the measurements, never inside a timed stretch
        gc_max = 0
        for _ in range(_GC_RUNS):
            t0 = time.ticks_us()
            gc.collect()
            gc_max = max(gc_max, time.ticks_diff(time.ticks_us(), t0))
        fact("gc_max_us", gc_max)
        wdt.feed()
        voc = VOCAlgorithm()
        voc_max = 0
        for step in range(_VOC_STEPS):
            t0 = time.ticks_us()
            voc.vocalgorithm_process(_VOC_RAW[step % len(_VOC_RAW)])
            if step >= _VOC_STEPS - _VOC_TIMED:
                voc_max = max(voc_max, time.ticks_diff(time.ticks_us(), t0))
        fact("voc_max_us", voc_max)
        wdt.feed()
        gaps = [0]
        probing = [True]

        async def probe() -> None:
            # Wakes at every yield the CRC loop gives: the largest gap between two wake-ups is its longest stretch.
            last = time.ticks_us()
            while probing[0]:
                await asyncio.sleep_ms(0)
                now = time.ticks_us()
                gaps[0] = max(gaps[0], time.ticks_diff(now, last))
                last = now

        waker = asyncio.create_task(probe())
        await asyncio.sleep_ms(0)
        t0 = time.ticks_us()
        await CRC32().check_from(bytearray(_CRC_BYTES))  # the verdict is irrelevant here: the bytes are all walked either way
        fact("crc_total_us", time.ticks_diff(time.ticks_us(), t0))
        probing[0] = False
        await waker
        fact("crc_gap_max_us", gaps[0])
        fact("routine_stall_us", _ROUTINE_STALL_US)
    finally:
        pixel = getattr(device, "neopixel", None)  # the build constructs the rig's NeoPixel where the TOML wires one
        if pixel is not None:
            pixel.off()
        for name in os.listdir(_SCRATCH_CFG_PATH):
            os.remove(_SCRATCH_CFG_PATH + name)
        os.rmdir(_SCRATCH_CFG_PATH)
        # The boot-phase mark build_system() left: cleared, so the next reset does not read as a boot failure.
        phase = machine.mem_backup(1)
        for i in range(len(phase)):
            phase[i] = 0
    done()


asyncio.run(_main())
