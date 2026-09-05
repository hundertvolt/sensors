"""Isolated-driver device script, flash-tier, phase 2 of 2 - runs after the board has come back up
from the real hardware reset fram_reset_race_during_write_seed_and_race.py's own reset_yanker()
triggered mid-write (see that script's own docstring for the full design and honest scope). Proves:
the raced write never landed (target region still shows the original, pre-race content), neither
guard region was disturbed (no wild corruption spread beyond the write in progress), a fresh
verify_present() succeeds (the chip's own SPI protocol state machine isn't left wedged - matching
fram_cs_hijack_fault_injection_and_recovery.py's own recovery proof), and a completely clean write
+read round trip at a separate address works normally afterward too - including proving the stray
SET WEL latch left behind by the interrupted session (see phase 1's own docstring) causes no
problem for this next real write.

Run via ordinary board.run_isolated(this_script) - a normal isolated-driver call, unlike phase 1."""

import asyncio

import machine

import asy_spi_driver
from asy_fram_driver import FRAM_SPI
from print_log import PrintLogHistory

_GUARD_BEFORE_ADDR = 0xA000
_TARGET_ADDR = 0xA010
_GUARD_AFTER_ADDR = 0xA020
_POST_RECOVERY_ADDR = 0xA030

_GUARD_BEFORE_PATTERN = bytes(range(0x10, 0x20))
_ORIGINAL_TARGET_PATTERN = bytes(range(0x70, 0x80))
_GUARD_AFTER_PATTERN = bytes(range(0x30, 0x40))
_POST_RECOVERY_PATTERN = bytes(range(0x50, 0x60))


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)
    spi0 = asy_spi_driver.SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    fram = FRAM_SPI(spi0, 5, logger=PrintLogHistory(name="FRAMRESETRACE"), max_size=0x40000)
    await fram.setup()
    if not fram.initialized:
        print("RESULT: FAIL fram.setup() did not reach initialized=True after the reset - device not found?")
        return

    failures = []

    async with fram:
        guard_before = bytearray(16)
        ok = await fram.get_values(guard_before, addr_start=_GUARD_BEFORE_ADDR)
    if not ok or bytes(guard_before) != _GUARD_BEFORE_PATTERN:
        failures.append(f"guard-before region disturbed: expected {_GUARD_BEFORE_PATTERN.hex()}, got {bytes(guard_before).hex()} (ok={ok})")
    wdt.feed()

    async with fram:
        target = bytearray(16)
        ok = await fram.get_values(target, addr_start=_TARGET_ADDR)
    # HARD requirement, same standing rule as the CS-hijack race: the raced write must never have
    # reached the chip - the target region must still show its real, original, pre-race content.
    if not ok or bytes(target) != _ORIGINAL_TARGET_PATTERN:
        failures.append(f"target region was NOT left at its original content: expected {_ORIGINAL_TARGET_PATTERN.hex()}, got {bytes(target).hex()} (ok={ok}) - the reset-raced write may have partially or fully landed")
    wdt.feed()

    async with fram:
        guard_after = bytearray(16)
        ok = await fram.get_values(guard_after, addr_start=_GUARD_AFTER_ADDR)
    if not ok or bytes(guard_after) != _GUARD_AFTER_PATTERN:
        failures.append(f"guard-after region disturbed: expected {_GUARD_AFTER_PATTERN.hex()}, got {bytes(guard_after).hex()} (ok={ok})")
    wdt.feed()

    # Recovery: verify_present() (not lock-wrapped - self-acquires internally, asyncio.Lock isn't
    # reentrant) must succeed cleanly, then a completely fresh write+read round trip must work
    # normally - including proving the stray SET WEL left over from the interrupted session (phase
    # 1's own docstring) doesn't wedge the very next real write.
    recovered = await fram.verify_present()
    wdt.feed()
    if not recovered:
        failures.append("verify_present() failed after the reset race - chip/driver did not recover")

    async with fram:
        clean_write_ok = await fram.set_values(_POST_RECOVERY_PATTERN, addr_start=_POST_RECOVERY_ADDR)
    async with fram:
        clean_readback = bytearray(len(_POST_RECOVERY_PATTERN))
        clean_read_ok = await fram.get_values(clean_readback, addr_start=_POST_RECOVERY_ADDR)
    if not clean_write_ok:
        failures.append("post-recovery set_values() failed outright")
    if not clean_read_ok or bytes(clean_readback) != _POST_RECOVERY_PATTERN:
        failures.append(f"post-recovery get_values() returned {bytes(clean_readback).hex()}, expected {_POST_RECOVERY_PATTERN.hex()}")

    if failures:
        print(f"RESULT: FAIL {len(failures)} issue(s): {'; '.join(failures)}")
    else:
        print("RESULT: PASS the reset-raced write never landed, both guard regions were untouched, and the driver fully recovered")


asyncio.run(_main())
