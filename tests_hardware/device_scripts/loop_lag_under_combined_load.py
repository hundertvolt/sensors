"""Event-loop lag of the bench build's shipped main() under in-process load: a 10 ms lag probe beside an
allocation-churn task and FRAM block writes inside this script's own scratch region; the firmware's tasks run as
shipped. Facts only: the host holds the lag to the device's smallest hard consumer (SPECIFICATION.md Part F.3)."""

import asyncio
import errno
import os
import time

import _bench_device as device  # rendered: the bench device's generated module
import machine

from asy_print_log import PrintLog

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py
# The product's own unretrieved-task report at the error level, so it prints whatever level the board's config holds.
_REPORT = PrintLog(level=1, name="UNRETRIEVED TASK EXCEPTION:")

# The part's second-highest 256 B, above every chunk and apart from the command-hold script's top 256 B.
_SCRATCH_REGIONS = ((BENCH["fram_max_size"] - 0x200, 0x100),)
# A scratch directory: every setup() finds its file absent here and writes its defaults once, never a production file.
_SCRATCH_CFG_PATH = "hwtest-scratch/"
# @tunable l3.loop_lag_window_s = 30
_WINDOW_S = 30
_PROBE_MS = 10
_BUCKETS = 64  # 1 ms lag buckets for the p99, the last one open-ended
_CHURN_BYTES = 512
_CHURN_MS = 5
_FRAM_WRITE_MS = 50
running = [True]


async def _churn() -> None:
    # Allocation churn that forces collections; nothing it allocates survives a round.
    while running[0]:
        garbage = bytearray(_CHURN_BYTES)
        garbage[0] = 1
        await asyncio.sleep_ms(_CHURN_MS)


async def _fram_writes(counts: "list[int]") -> None:
    # Block writes through the FRAM driver itself under its own locks, once main()'s setup batch has set the chip up,
    # only inside the declared scratch region: counts holds [written, failed].
    fram = device.fram
    if fram is None:
        return
    start, length = _SCRATCH_REGIONS[0]
    block = bytearray(length)
    while running[0]:
        if fram.fram.initialized:
            async with fram.fram as driver:
                ok = await driver.set_values(block, start)
            counts[0 if ok else 1] += 1
        await asyncio.sleep_ms(_FRAM_WRITE_MS)


async def _main() -> None:
    asyncio.get_event_loop().set_exception_handler(_REPORT.report_unretrieved)  # before main(): the firmware keeps it
    wdt = arm()
    try:  # an aborted run's leftover first (none: ENOENT)
        for name in os.listdir(_SCRATCH_CFG_PATH):
            os.remove(_SCRATCH_CFG_PATH + name)
        os.rmdir(_SCRATCH_CFG_PATH)
    except OSError as e:
        if e.errno != errno.ENOENT:
            fact("leftover_errno", e.errno)
    os.mkdir(_SCRATCH_CFG_PATH)
    buckets = [0] * _BUCKETS
    lag_max = [0]
    fram_writes = [0, 0]

    async def probe() -> None:
        # Sleeps _PROBE_MS at a time and records each overshoot of its due time.
        while running[0]:
            due = time.ticks_add(time.ticks_us(), _PROBE_MS * 1000)
            await asyncio.sleep_ms(_PROBE_MS)
            lag = max(time.ticks_diff(time.ticks_us(), due), 0)
            lag_max[0] = max(lag_max[0], lag)
            buckets[min(lag // 1000, _BUCKETS - 1)] += 1

    shipped = asyncio.create_task(device.main(watchdog=wdt, cfg_path=_SCRATCH_CFG_PATH, web_host="127.0.0.1", web_port=8080))
    loads = [asyncio.create_task(probe()), asyncio.create_task(_churn()), asyncio.create_task(_fram_writes(fram_writes))]
    try:
        await fed_sleep_ms(wdt, _WINDOW_S * 1000)
        fact("main_running", not shipped.done())
    finally:
        running[0] = False
        shipped.cancel()
        for task in loads:
            task.cancel()
        pixel = getattr(device, "neopixel", None)  # the build constructs the rig's NeoPixel where the TOML wires one
        if pixel is not None:
            pixel.off()
        for name in os.listdir(_SCRATCH_CFG_PATH):
            os.remove(_SCRATCH_CFG_PATH + name)
        os.rmdir(_SCRATCH_CFG_PATH)
        # The boot-phase mark main() left: cleared, so the next reset does not read as a boot failure.
        phase = machine.mem_backup(1)
        for i in range(len(phase)):
            phase[i] = 0
    samples = sum(buckets)
    seen, p99 = 0, _BUCKETS - 1
    for ms in range(_BUCKETS):
        seen += buckets[ms]
        if seen * 100 >= samples * 99:
            p99 = ms
            break
    fact("samples", samples)
    fact("lag_max_us", lag_max[0])
    fact("lag_p99_us", (p99 + 1) * 1000)  # the upper edge of the bucket holding the 99th percentile
    fact("fram_writes", fram_writes[0])
    fact("fram_write_failures", fram_writes[1])
    done()


asyncio.run(_main())
