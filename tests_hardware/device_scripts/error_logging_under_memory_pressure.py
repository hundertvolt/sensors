"""Isolated-driver device script: the diagnostic path itself must survive a scarce heap. Records and
reads back FRAM-backed error history (print_log.py) while memory_pressure churns the allocator - if
logging degrades under pressure, the evidence of the pressure is what gets lost. Part I.6."""
# Writes FRAM only (no RP2040 flash, no sensor EEPROM), and its chunk 0 is production's chunk 0 -
# this run overwrites the board's real error-log history, per tests_hardware/README.md.

import asyncio
import gc
import time

import machine
import memory_pressure

import asy_spi_driver
from asy_fram_manager import AsyFramManager
from print_log import PrintLogHistory, make_logger

HISTORY_LENGTH = 5
TEST_ERRNO = 42
LOG_NAME = "TEST"
_ROUNDS = 40
# Tighter than the instrument's own default: this script has almost no resident object graph, so
# the default headroom would barely pressure anything. Still a floor, never exhaustion.
_HEADROOM = 8192


async def _main() -> None:
    if gc.threshold() != -1:
        print(f"RESULT: FAIL expected a reactive-GC build, but gc.threshold() is {gc.threshold()}")
        return

    # run_isolated() arms an 8s watchdog before every isolated script and nothing feeds it on our
    # behalf - under reactive-only GC each round pays a full sweep, so the loop below must feed
    # it like every other long-running device script does.
    wdt = machine.WDT(timeout=8000)
    failures = []
    spi0 = asy_spi_driver.SPI(0, 2, 3, 4)
    fram = AsyFramManager(spi0, 5, max_size=0x40000, debug=None)
    if not await fram.setup():
        print("RESULT: FAIL fram.setup() failed - real FRAM chip not responding on spi0/cs5")
        return

    pr = make_logger(fram, history_length=HISTORY_LENGTH, debug=None, name=LOG_NAME)
    await pr.setup()
    if not pr.initialized:
        print("RESULT: FAIL logger failed to initialize against the real FRAM chunk")
        return
    await pr.reset()

    churn = memory_pressure.start(headroom=_HEADROOM)
    await asyncio.sleep_ms(200)  # let the instrument reach its hold depth before anything is measured

    # A fresh PrintLogHistory per round: its deque([_NO_ERR] * n) allocation is the one print_log.py
    # guards with its own MemoryError fallback, and a degraded-to-zero history is a silent failure.
    degraded = 0
    started_ms = time.ticks_ms()
    for _ in range(_ROUNDS):
        wdt.feed()
        probe = PrintLogHistory(history_length=HISTORY_LENGTH, level=None, name="PROBE")
        if len(probe.history) != HISTORY_LENGTH:
            degraded += 1
        await pr.err_s("pressure round", errno=TEST_ERRNO)
        await asyncio.sleep_ms(5)
    elapsed_ms = time.ticks_diff(time.ticks_ms(), started_ms)

    churn.stop = True
    await asyncio.sleep_ms(50)
    wdt.feed()

    log = await pr.get_log()
    entry = log.get(LOG_NAME)
    if entry is None:
        failures.append(f"get_log() returned no entry for {LOG_NAME!r}: {log!r}")
    else:
        if entry["ErrCount"] != _ROUNDS:
            failures.append(f"ErrCount={entry['ErrCount']!r} after {_ROUNDS} recorded errors under pressure - entries were lost")
        matched = next((t for n, t in zip(entry["ErrNum"], entry["ErrType"]) if n == TEST_ERRNO), None)  # noqa: B905 - MicroPython zip() rejects strict=
        if matched != "E":
            failures.append(f"restored history lacks errno={TEST_ERRNO} as type 'E': ErrNum={entry['ErrNum']!r} ErrType={entry['ErrType']!r}")
    if degraded:
        failures.append(f"{degraded}/{_ROUNDS} PrintLogHistory allocations degraded to a zero-length history under pressure")
    if not churn.blocks:
        failures.append("the churn instrument never ran")
    if churn.alloc_failures:
        failures.append(f"the churn instrument itself hit {churn.alloc_failures} MemoryError(s) - headroom mis-calibrated, this run proves nothing")

    if failures:
        print("RESULT: FAIL " + "; ".join(failures))
    else:
        print(f"RESULT: PASS {_ROUNDS} errors recorded and read back in {elapsed_ms}ms under churn={churn.blocks} blocks drops={churn.drops}")


asyncio.run(_main())
