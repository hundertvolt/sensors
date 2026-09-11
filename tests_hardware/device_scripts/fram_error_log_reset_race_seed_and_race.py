"""Isolated-driver device script, phase 1 of 2 (see fram_error_log_reset_race_verify.py). Races a
real machine.reset() against an in-flight PrintLogHistoryStore chunk write - the CHUNK-level
counterpart to fram_reset_race_during_write_seed_and_race.py's raw-driver race.
Run via `board.run_isolated_expect_reset()`, never run_isolated()."""

import asyncio

import machine

import asy_spi_driver
from asy_fram_manager import AsyFramManager
from print_log import make_logger

HISTORY_LENGTH = 10
SEEDED_ERRNO = 5  # what the three settled, fully-written entries carry
RACED_ERRNO = 6  # the fourth entry, whose write is what the reset interrupts
LOG_NAME = "ERRRACE"
_WDT_TIMEOUT_MS = 8000


async def _main() -> None:
    wdt = machine.WDT(timeout=_WDT_TIMEOUT_MS)
    spi0 = asy_spi_driver.SPI(0, 2, 3, 4)
    fram = AsyFramManager(spi0, 5, max_size=0x40000, debug=None)
    if not await fram.setup():
        print("RESULT: FAIL fram.setup() failed - real FRAM chip not responding on spi0/cs5")
        return

    # First chunk allocated off a freshly-constructed manager, so it lands at allocation offset 0 -
    # the verify script constructs the same two objects in the same order and therefore addresses
    # the same chunk. Same convention fram_error_log_roundtrip.py already relies on.
    store = make_logger(fram, history_length=HISTORY_LENGTH, debug=None, name=LOG_NAME)
    await store.setup()
    if not store.initialized:
        print("RESULT: FAIL PrintLogHistoryStore.setup() did not initialize - no FRAM chunk")
        return

    # Clear first: this chunk is real, persistent on-chip storage, so setup() above just restored
    # whatever a previous run of this script left in it - without a reset the ring accumulates and
    # "exactly three settled entries" would be false on every run after the first.
    await store.reset()
    baseline = await store.get_log()
    if any(t != "N" for t in baseline[LOG_NAME]["ErrType"]) or baseline[LOG_NAME]["ErrCount"] != 0:
        print(f"RESULT: FAIL could not clear the chunk to a known baseline before seeding ({baseline[LOG_NAME]!r})")
        return

    for _ in range(3):
        await store.err_s("seeded", errno=SEEDED_ERRNO)
    log = await store.get_log()
    seeded = [n for n, t in zip(log[LOG_NAME]["ErrNum"], log[LOG_NAME]["ErrType"]) if t == "E"]  # noqa: B905 - MicroPython zip() rejects strict=
    if seeded != [SEEDED_ERRNO] * 3:
        print(f"RESULT: FAIL could not seed three settled entries before racing (got {seeded})")
        return
    wdt.feed()

    async def victim_writer() -> None:
        # err_s() is write-through (print_log.py's _store_err()), so this is a real chunk write:
        # both status bytes to _STATUS_BUSY, payload + CRC, then both back to _STATUS_IDLE.
        await store.err_s("raced", errno=RACED_ERRNO)

    async def reset_yanker() -> None:
        # One await asyncio.sleep(0) before acting - next-in-line the instant victim_writer yields,
        # same scheduling-order dependency as fram_reset_race_during_write_seed_and_race.py's own.
        await asyncio.sleep(0)
        machine.reset()  # never returns - real RP2040 hardware reset, immediate

    print("SEEDED: three settled entries written, racing a real reset against the fourth")
    await asyncio.gather(victim_writer(), reset_yanker())
    print("RESULT: FAIL machine.reset() returned - the race never happened")


asyncio.run(_main())
