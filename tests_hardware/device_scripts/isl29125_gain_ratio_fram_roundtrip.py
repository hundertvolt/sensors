"""Isolated-driver device script: the ISL29125's gain-ratio FRAM chunk against the real MB85RS2MTA -
the persist/restore round trip, the plausibility gate on load, and ISLResetCal's real clear. A second
reader at the same FRAM address stands in for a fresh boot, as sgp40_fram_backup_restore.py does."""

import asyncio

import machine

import asy_i2c_driver
import asy_spi_driver
from asy_fram_manager import AsyFramManager
from asy_isl29125_driver import ISL29125_Reader

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from print_log import ErrorLog

# 24.5 is inside the driver's own 20.0-34.0 plausibility band AND exactly representable as a
# single-precision float (49/2), so a mismatch below is a real round-trip fault and never a
# rounding artefact - the chunk stores "<f", not "<d" (MicroPython's float is 4 bytes on rp2).
GOOD_RATIO = 24.5
IMPLAUSIBLE_RATIO = 99.0  # outside the band, so a loader that skips the gate would adopt it
NOMINAL = 10000 / 375

failures: "list[str]" = []
notes: "list[str]" = []


def check(condition: object, message: str) -> None:
    # `condition: object`, not `bool` - same reason isl29125_mechanism_envelope.py's own check() gives.
    if not condition:
        failures.append(message)


async def _always_synced() -> bool:
    return True  # stands in for the real ntp.ntp_issynced - no NTP subsystem in an isolated script


async def _fresh_reader(spi0: "asy_spi_driver.SPI", i2c1: "asy_i2c_driver.I2C") -> "ISL29125_Reader | None":
    """A brand-new AsyFramManager plus reader, allocating the same chunks at the same physical
    addresses the previous pair did - the allocator is deterministic, which is what makes this a
    genuine stand-in for a reboot rather than a second handle on the same objects."""
    fram = AsyFramManager(spi0, 5, max_size=0x40000, debug=None)
    if not await fram.setup():
        return None
    reader = ISL29125_Reader(i2c1, 6, max_module_error=999, fram=fram, fram_ntp_callback=_always_synced, debug=None)
    await reader.pr.setup()  # _load_gain_ratio()'s warnings go through it, and _init_isl is not run here
    # The logger is FRAM-backed, so it comes up carrying whatever the LAST run of this script left
    # behind - without this, phase 1's "a clean restore logged nothing" would pass on a virgin chip
    # and fail on every run after it. Clearing here scopes each phase's assertions to its own
    # warnings. It also clears one real error-log chunk, the documented isolated-driver side effect
    # tests_hardware/README.md describes; isl29125_mechanism_envelope.py does the same for the same reason.
    await reader.reset_error_counter()
    return reader


def _warnings(counters: "ErrorLog") -> "list[int]":
    """The wrnno values in ISL29125's own history - same ErrorLog shape (SPECIFICATION.md Part G.2)
    isl29125_mechanism_envelope.py's _log_entries() reads, narrowed to warnings."""
    entry = counters.get("ISL29125")
    if entry is None:
        return []
    types, nums = entry["ErrType"], entry["ErrNum"]
    return [nums[i] for i in range(min(len(types), len(nums))) if types[i] == "W"]  # no zip(strict=) on MicroPython


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)
    i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000, timeout=200000)
    spi0 = asy_spi_driver.SPI(0, 2, 3, 4)

    writer = await _fresh_reader(spi0, i2c1)
    if writer is None or writer.ts_storage is None:
        print("RESULT: FAIL could not allocate the gain-ratio chunk on the real FRAM chip")
        return

    # 1. A real, non-nominal ratio goes to the real chip and comes back off it.
    writer._gain_ratio = GOOD_RATIO
    await writer._persist_gain_ratio()
    check(writer._gain_ratio_ts is not None, "persisting a ratio produced no timestamp even with NTP reported synced")
    wdt.feed()

    restored = await _fresh_reader(spi0, i2c1)
    if restored is None:
        print("RESULT: FAIL the simulated fresh boot could not reach the real FRAM chip")
        return
    await restored._load_gain_ratio()
    ratio, cal_ts = await restored.get_mem_status()
    notes.append(f"restored ratio={ratio} ts={cal_ts}")
    check(ratio == GOOD_RATIO, f"a real FRAM round trip changed the ratio: wrote {GOOD_RATIO}, read back {ratio}")
    check(cal_ts is not None, "the ratio came back without the timestamp that was stored beside it")
    check(not _warnings(await restored.get_error_counter()), "a clean restore still logged a warning")
    wdt.feed()

    # 2. The plausibility gate is on LOAD, which is the boundary an untrusted value crosses - a
    #    corrupted chunk must degrade to nominal, never be adopted as the live scale factor.
    writer._gain_ratio = IMPLAUSIBLE_RATIO
    await writer._persist_gain_ratio()
    poisoned = await _fresh_reader(spi0, i2c1)
    if poisoned is None:
        print("RESULT: FAIL the second simulated fresh boot could not reach the real FRAM chip")
        return
    await poisoned._load_gain_ratio()
    ratio, _ts = await poisoned.get_mem_status()
    check(ratio == NOMINAL, f"an implausible stored ratio was adopted instead of rejected: got {ratio}")
    check(13 in _warnings(await poisoned.get_error_counter()), "rejecting an implausible stored ratio logged no wrnno=13")
    wdt.feed()

    # 3. ISLResetCal really clears the chip, so the next boot finds nothing rather than the old value.
    check(await poisoned.reset_gain_calibration(flag=True), "reset_gain_calibration() reported failure against the real chip")
    cleared = await _fresh_reader(spi0, i2c1)
    if cleared is None:
        print("RESULT: FAIL the third simulated fresh boot could not reach the real FRAM chip")
        return
    await cleared._load_gain_ratio()
    ratio, cal_ts = await cleared.get_mem_status()
    check(ratio == NOMINAL, f"a cleared calibration still restored a ratio: {ratio}")
    check(cal_ts is None, f"a cleared calibration still restored a timestamp: {cal_ts}")
    check(11 in _warnings(await cleared.get_error_counter()), "a cleared chunk did not report wrnno=11 (no backup found)")

    if failures:
        print("RESULT: FAIL " + " | ".join(failures) + " || " + " ; ".join(notes))
    else:
        print("RESULT: PASS " + " ; ".join(notes))


asyncio.run(_main())
