"""Isolated-driver device script: FRAM's own same-device concurrency proof - "ongoing read, incoming
write" (SPECIFICATION.md Part C.8). FRAM has no NVM write-wear concern (10^13 ops/byte, datasheets/
fram/). get_values()/set_values() require the caller to already hold the outer Lockable lock."""

import asyncio

import machine

import asy_spi_driver
from asy_fram_driver import FRAM_SPI
from print_log import PrintLogHistory

READ_REGION = (0x0000, 32)  # never touched by the writer below
WRITE_REGION = (0x8000, 32)  # disjoint scratch region, well within the real 256KB chip's range
SEED_PATTERN = bytes(range(32))
WRITE_PATTERN = bytes((32 - i) & 0xFF for i in range(32))  # deliberately distinct from SEED_PATTERN

READ_ITERATIONS = 30


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)
    spi0 = asy_spi_driver.SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    fram = FRAM_SPI(spi0, 5, logger=PrintLogHistory(name="FRAMCONCUR"), max_size=0x40000)
    await fram.setup()
    if not fram.initialized:
        print("RESULT: FAIL fram.setup() did not reach initialized=True - device not found?")
        return

    async with fram:
        ok = await fram.set_values(SEED_PATTERN, addr_start=READ_REGION[0])
    if not ok:
        print("RESULT: FAIL could not seed the read region before starting the concurrency check")
        return

    read_mismatches = []
    reads_completed = 0
    write_completed = False

    async def reader() -> None:
        nonlocal reads_completed
        buf = bytearray(READ_REGION[1])
        for i in range(READ_ITERATIONS):
            async with fram:
                ok = await fram.get_values(buf, addr_start=READ_REGION[0])
            if not ok or bytes(buf) != SEED_PATTERN:
                read_mismatches.append(f"iter {i}: ok={ok} got={bytes(buf).hex()}")
            reads_completed += 1
            if i % 5 == 0:
                wdt.feed()

    async def writer() -> None:
        nonlocal write_completed
        await asyncio.sleep(0)  # let the reader get partway into its run first, matching the other same-device scripts' own pattern
        async with fram:
            ok = await fram.set_values(WRITE_PATTERN, addr_start=WRITE_REGION[0])
        if not ok:
            read_mismatches.append("write() returned False under concurrent read load")
        write_completed = True

    await asyncio.wait_for(asyncio.gather(reader(), writer()), 60.0)

    async with fram:
        write_readback = bytearray(WRITE_REGION[1])
        write_ok = await fram.get_values(write_readback, addr_start=WRITE_REGION[0])

    failures = []
    if reads_completed != READ_ITERATIONS:
        failures.append(f"reader only completed {reads_completed}/{READ_ITERATIONS} iterations")
    if not write_completed:
        failures.append("writer never completed")
    if not write_ok or bytes(write_readback) != WRITE_PATTERN:
        failures.append(f"write region shows {bytes(write_readback).hex()}, expected {WRITE_PATTERN.hex()} - torn/corrupted write")
    failures.extend(read_mismatches)

    if failures:
        print(f"RESULT: FAIL {len(failures)} issue(s): {'; '.join(failures[:10])}")
    else:
        print(f"RESULT: PASS reader={reads_completed}/{READ_ITERATIONS} writer completed, both regions clean, no corruption")


asyncio.run(_main())
