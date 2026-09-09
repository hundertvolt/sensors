"""Isolated-driver device script, phase 1 of 2 (see verify_recovery.py for phase 2). Races a real
machine.reset() against an in-flight FRAM write, same yield-point technique as the CS-hijack script.
Run via `board.run_isolated_expect_reset()`, never run_isolated() - see tests_hardware/README.md's FRAM reset-race finding."""

import asyncio

import machine

import asy_spi_driver
from asy_fram_driver import FRAM_SPI
from print_log import PrintLogHistory

# Scratch addresses, disjoint from every other device script's own regions (CS-hijack uses
# 0x9000-0x93ff).
_GUARD_BEFORE_ADDR = 0xA000
_TARGET_ADDR = 0xA010
_GUARD_AFTER_ADDR = 0xA020

_GUARD_BEFORE_PATTERN = bytes(range(0x10, 0x20))
_ORIGINAL_TARGET_PATTERN = bytes(range(0x70, 0x80))
_NEW_TARGET_PATTERN = bytes((0xCC,) * 16)  # what the interrupted write attempts, must never land
_GUARD_AFTER_PATTERN = bytes(range(0x30, 0x40))


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)
    spi0 = asy_spi_driver.SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    fram = FRAM_SPI(spi0, 5, logger=PrintLogHistory(name="FRAMRESETRACE"), max_size=0x40000)
    await fram.setup()
    if not fram.initialized:
        print("RESULT: FAIL fram.setup() did not reach initialized=True - device not found?")
        return

    async with fram:
        ok = await fram.set_values(_GUARD_BEFORE_PATTERN, addr_start=_GUARD_BEFORE_ADDR)
    if not ok:
        print("RESULT: FAIL could not seed the guard-before region")
        return
    async with fram:
        ok = await fram.set_values(_ORIGINAL_TARGET_PATTERN, addr_start=_TARGET_ADDR)
    if not ok:
        print("RESULT: FAIL could not seed the target region's original content")
        return
    async with fram:
        ok = await fram.set_values(_GUARD_AFTER_PATTERN, addr_start=_GUARD_AFTER_ADDR)
    if not ok:
        print("RESULT: FAIL could not seed the guard-after region")
        return
    wdt.feed()

    async def victim_writer() -> None:
        async with fram:
            await fram.set_values(_NEW_TARGET_PATTERN, addr_start=_TARGET_ADDR)

    async def reset_yanker() -> None:
        # One await asyncio.sleep(0) before acting - next-in-line the instant victim_writer yields,
        # same scheduling-order dependency as the CS-hijack script's cs_yanker().
        await asyncio.sleep(0)
        machine.reset()  # never returns - real RP2040 hardware reset, immediate

    await asyncio.wait_for(asyncio.gather(reset_yanker(), victim_writer()), 30.0)  # type: ignore[arg-type]
    # Unreachable in the successful case (machine.reset() halts the runtime first). If this DOES
    # print, the race missed its window - the phase-2 verify script's guard-region check catches that.
    print("RESULT: FAIL reset_yanker() never actually fired before victim_writer() completed - race did not land, nothing was tested")


asyncio.run(_main())
