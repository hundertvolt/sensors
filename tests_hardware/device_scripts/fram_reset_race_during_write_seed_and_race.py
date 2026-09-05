"""Isolated-driver device script, flash-tier, phase 1 of 2 (see the sibling
fram_reset_race_during_write_verify_recovery.py for phase 2 - this script's own real hardware
reset means it can never itself print a RESULT line or return control to the caller).

Recombination test (2026-09-04, project owner's own explicit request): the CS-hijack script
(fram_cs_hijack_fault_injection_and_recovery.py) already proves a controlled CS deselect mid-write
leaves the chip untouched. This script instead races a genuine RP2040 *hardware reset*
(machine.reset(), the closest software-triggered equivalent to a real power cycle this harness can
achieve deterministically) against the same in-flight write, at the identical deterministic
yield-point technique that script's own module docstring documents in full (the one real `await`
inside SPIDevice.__aenter__() - no other point in the whole write path can ever be interleaved by
MicroPython's cooperative scheduler). A real reset is a genuinely different fault than a CS
deselect: unlike a clean CS deassert (which is the SPI protocol's own built-in deselect mechanism,
per the chip's own datasheet), a reset happens on the RP2040 side only - the FRAM chip itself has
no idea the host rebooted, so anything the chip's own internal state machine was mid-way through
(specifically: the WEL write-enable latch, already SET by _enable_write()'s own prior, already-
completed WREN session before this race's own WRITE session even begins - see
asy_fram_driver.py's own _write()) is left exactly as it was, not cleanly unwound.

Because SPIDevice.write()/readinto() have no internal yield point at all (same finding the CS-hijack
script already confirmed), the only reachable race position is the same one that script uses: CS
already asserted, but before the WRITE opcode/address/data bytes are clocked out at all - so this
cannot prove a genuinely *torn* (partially-written) transfer, only that a real hardware reset
landing right as a write session begins (with WEL already left SET from the immediately-preceding,
already-completed WREN handshake) leaves the target region untouched and the driver/chip fully
recoverable afterward, including that the stray SET WEL causes no problem for the very next real
operation. A true mid-byte-transfer power loss is architecturally unreachable via any
interpreter-level race (the real SPI transfer is a single, uninterruptible synchronous
machine.SPI.write() call - the same reason a wedged I2C/SPI bus can't be timeout-wrapped either, see
SPECIFICATION.md Part F.2) - only a genuinely asynchronous, uncontrolled-by-the-interpreter event
(a real external power cycle, or a real host-triggered mid-transfer interrupt this harness cannot
achieve without risking concurrent access to the same serial port from two processes) could ever
reach that point; see BACKLOG.md's own account of this test for the full reasoning on why this is
the honest, safely-buildable scope, not the exhaustive one.

This bench unit wires FRAM to SPI0 (sck=2, mosi=3, miso=4), CS=GPIO5, a 256KB MB85RS2MTA chip.

Run via `board.run_isolated_expect_reset(this_script)` - NEVER run_isolated()/`mpremote run ...
soft-reset`, since this script's own machine.reset() call means the mpremote subprocess driving it
will see the device disappear mid-session, which run_isolated()'s own raise-on-nonzero-exit
behavior would otherwise treat as a hard failure."""

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
        # Exactly one await asyncio.sleep(0) before acting - guarantees it's next-in-line the
        # instant victim_writer yields inside __aenter__, same proven scheduling-order dependency
        # fram_cs_hijack_fault_injection_and_recovery.py's own cs_yanker() uses (5/5 reliable there).
        await asyncio.sleep(0)
        machine.reset()  # never returns - real RP2040 hardware reset, immediate

    await asyncio.wait_for(asyncio.gather(reset_yanker(), victim_writer()), 30.0)  # type: ignore[arg-type]
    # Unreachable in the real, successful case - reset_yanker()'s machine.reset() halts the whole
    # runtime before this line can ever run. If this DOES print, the race missed its window
    # entirely (reset_yanker never got scheduled in time) - the phase-2 verify script's own guard-
    # region check will catch that as a real failure (a race that silently missed must fail loudly,
    # same standing rule fram_cs_hijack_fault_injection_and_recovery.py's own module docstring
    # states), not this line.
    print("RESULT: FAIL reset_yanker() never actually fired before victim_writer() completed - race did not land, nothing was tested")


asyncio.run(_main())
