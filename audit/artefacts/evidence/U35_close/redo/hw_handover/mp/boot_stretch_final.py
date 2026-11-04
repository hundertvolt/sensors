"""Final-image boot stretches: the shipped main() on the board's own config, its watchdog a recorder that stamps every
feed from the arming, as the boot entry orders it (WDT, imports, gc threshold, main), for RUN_S. main() writes
production FRAM chunks, so it refuses until CONFIRM is set (sed) once errcount and the raw FRAM are saved."""

import time

import machine

CONFIRM = False
DEVICE = "dev"
RUN_S = 30
SHOWN = 40  # stamps printed; the setup units' feeds come first, the supervisor's after

if not CONFIRM:
    print("SUM stretch refused: CONFIRM is False (save errcount and the raw FRAM first)")
    print("DONE=1")
    raise SystemExit

t0 = time.ticks_ms()
wdt = machine.WDT(timeout=8000)  # rp2 keeps one watchdog: this re-arms the boot entry's own
stamps = []


class Recorder:
    def feed(self) -> None:
        stamps.append(time.ticks_diff(time.ticks_ms(), t0))
        wdt.feed()


import gc  # after the arming, as in the boot entry

import micropython

micropython.alloc_emergency_exception_buf(100)
import asyncio

main = __import__("sensortask_" + DEVICE).main
gc.threshold(32768)


async def run() -> None:
    asyncio.create_task(main(watchdog=Recorder()))
    end = time.ticks_add(time.ticks_ms(), RUN_S * 1000)
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        await asyncio.sleep_ms(500)


asyncio.run(run())
gaps = [b - a for a, b in zip(stamps, stamps[1:])]
print("SUM stretch first_feed_ms=%s feeds=%d" % (stamps[0] if stamps else None, len(stamps)))
print("SUM stretch stamps_ms=%s" % stamps[:SHOWN])
print("SUM stretch gaps_ms=%s max_gap_ms=%s" % (gaps[: SHOWN - 1], max(gaps) if gaps else None))
print("DONE=1")
machine.reset()  # every raw-REPL session ends in a hard reset (tests_hardware/README.md); no record: 2 next boot
