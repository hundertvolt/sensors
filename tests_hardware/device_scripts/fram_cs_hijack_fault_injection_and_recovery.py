"""Isolated-driver device script: real-hardware GPIO-level fault injection against FRAM's CS pin -
races CS deassertion against an in-flight write/read (no external fault hardware needed - the
RP2040 already owns CS as a software-toggled Pin). See tests_hardware/README.md's FRAM CS-hijack finding."""

import asyncio

import machine

import asy_spi_driver
from asy_fram_driver import FRAM_SPI
from print_log import PrintLogHistory

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Awaitable

_WRITE_RACE_ADDR = 0x9000  # scratch addresses, disjoint from every other device script's own regions
_READ_RACE_ADDR = 0x9100
_POST_RECOVERY_ADDR_WRITE_HIJACK = 0x9200
_POST_RECOVERY_ADDR_READ_HIJACK = 0x9300

_ORIGINAL_PATTERN = bytes(range(16))
_HIJACKED_WRITE_PATTERN = bytes((0xAA,) * 16)  # deliberately distinct from _ORIGINAL_PATTERN
_READ_SEED_PATTERN = bytes(range(0x60, 0x70))  # deliberately distinct from every other pattern above
_POST_RECOVERY_PATTERN = bytes(range(0x40, 0x50))


async def _cs_yank_race(fram: FRAM_SPI, victim: "Awaitable[None]") -> bool:
    """Shared race harness for both scenarios below. Returns whether the yanker actually ran before
    the victim's own __aenter__ sleep elapsed - necessary but not sufficient; each caller's own
    outcome-based assertion afterward is the real proof."""
    cs_forced_high_early = False

    async def cs_yanker() -> None:
        nonlocal cs_forced_high_early
        await asyncio.sleep(0)
        fram._spidev.cs_pin.value(not fram._spidev.cs_active_value)  # deassert
        cs_forced_high_early = True

    await asyncio.wait_for(asyncio.gather(cs_yanker(), victim), 30.0)
    return cs_forced_high_early


async def _assert_recovery(fram: FRAM_SPI, addr: int, wdt: machine.WDT) -> list[str]:
    failures = []
    recovered = await fram.verify_present()  # not wrapped in `async with fram:` - self-acquires the same outer lock internally (asyncio.Lock isn't reentrant)
    wdt.feed()
    if not recovered:
        failures.append("verify_present() failed after the CS-hijack race - chip/driver did not recover")

    async with fram:
        clean_write_ok = await fram.set_values(_POST_RECOVERY_PATTERN, addr_start=addr)
    async with fram:
        clean_readback = bytearray(len(_POST_RECOVERY_PATTERN))
        clean_read_ok = await fram.get_values(clean_readback, addr_start=addr)

    if not clean_write_ok:
        failures.append("post-recovery set_values() failed outright")
    if not clean_read_ok or bytes(clean_readback) != _POST_RECOVERY_PATTERN:
        failures.append(f"post-recovery get_values() returned {bytes(clean_readback).hex()}, expected {_POST_RECOVERY_PATTERN.hex()}")
    return failures


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)
    spi0 = asy_spi_driver.SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    fram = FRAM_SPI(spi0, 5, logger=PrintLogHistory(name="FRAMCSHIJACK"), max_size=0x40000)
    await fram.setup()
    if not fram.initialized:
        print("RESULT: FAIL fram.setup() did not reach initialized=True - device not found?")
        return

    failures = []

    # --- Scenario 1: write hijack ---------------------------------------------------------------
    async with fram:
        ok = await fram.set_values(_ORIGINAL_PATTERN, addr_start=_WRITE_RACE_ADDR)
    if not ok:
        print("RESULT: FAIL could not seed the write-race region before starting the hijack")
        return
    wdt.feed()

    write_raised: BaseException | None = None

    async def victim_writer() -> None:
        nonlocal write_raised
        try:
            async with fram:
                await fram.set_values(_HIJACKED_WRITE_PATTERN, addr_start=_WRITE_RACE_ADDR)
        except Exception as e:
            write_raised = e

    yanker_ran = await _cs_yank_race(fram, victim_writer())
    if not yanker_ran:
        failures.append("write hijack: cs_yanker() never actually ran before victim_writer() completed - race did not land, nothing was tested")
    else:
        async with fram:
            write_readback = bytearray(16)
            write_readback_ok = await fram.get_values(write_readback, addr_start=_WRITE_RACE_ADDR)
        # Hard requirement: the hijacked write must never have reached the chip - anything else
        # means the race missed its window and this script tested nothing real.
        if not write_readback_ok or bytes(write_readback) != _ORIGINAL_PATTERN:
            failures.append(
                f"write hijack: expected original data {_ORIGINAL_PATTERN.hex()} untouched (write_raised={write_raised!r}), "
                f"got {bytes(write_readback).hex()} - the hijacked write was not reliably blocked",
            )
    wdt.feed()
    failures.extend(await _assert_recovery(fram, _POST_RECOVERY_ADDR_WRITE_HIJACK, wdt))

    # --- Scenario 2: read hijack -------------------------------------------------------------
    async with fram:
        ok = await fram.set_values(_READ_SEED_PATTERN, addr_start=_READ_RACE_ADDR)
    if not ok:
        failures.append("read hijack: could not seed the read-race region before starting the hijack")
    else:
        wdt.feed()
        read_raised: BaseException | None = None
        hijacked_read_buf = bytearray(16)

        async def victim_reader() -> None:
            nonlocal read_raised
            try:
                async with fram:
                    await fram.get_values(hijacked_read_buf, addr_start=_READ_RACE_ADDR)
            except Exception as e:
                read_raised = e

        yanker_ran = await _cs_yank_race(fram, victim_reader())
        if not yanker_ran:
            failures.append("read hijack: cs_yanker() never actually ran before victim_reader() completed - race did not land, nothing was tested")
        # Hard requirement: a hijacked read must never return the real, correct data - a
        # "sensible" result here would mean the race missed its window. Not asserted against a
        # specific wrong value (a different unit could float differently on a deselected MISO).
        elif read_raised is None and bytes(hijacked_read_buf) == _READ_SEED_PATTERN:
            failures.append(f"read hijack: got back the real seeded data {_READ_SEED_PATTERN.hex()} with no exception - the race did not reliably intercept the read")
        wdt.feed()
        failures.extend(await _assert_recovery(fram, _POST_RECOVERY_ADDR_READ_HIJACK, wdt))

    if failures:
        print(f"RESULT: FAIL {len(failures)} issue(s): {'; '.join(failures)}")
    else:
        print("RESULT: PASS both write-hijack and read-hijack races landed as required, driver fully recovered from each")


asyncio.run(_main())
