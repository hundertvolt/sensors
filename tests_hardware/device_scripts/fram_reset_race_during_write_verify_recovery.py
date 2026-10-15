"""Isolated-driver device script, phase 2 of 2: after the real reset phase 1 fired inside a write, the target holds its
original bytes or a prefix of the new ones (MB85RS2MTA p.9: each byte is written as it is clocked in), both guards are
untouched and the driver recovers. Restores the seed state in a finally; reports facts, the host gives the verdict."""

import asyncio

import asy_spi_driver
from asy_fram_driver import FRAM_SPI
from asy_print_log import PrintLogHistory

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact
    from _shared.watchdog import arm
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# Phase 1's region (one host test runs both phases).
_SCRATCH_REGIONS = ((0xA000, 0x40),)
_GUARD_BEFORE_ADDR = _SCRATCH_REGIONS[0][0]
_TARGET_ADDR = _GUARD_BEFORE_ADDR + 0x10
_GUARD_AFTER_ADDR = _GUARD_BEFORE_ADDR + 0x20
_POST_RECOVERY_ADDR = _GUARD_BEFORE_ADDR + 0x30

_GUARD_BEFORE_PATTERN = bytes(range(0x10, 0x20))
_ORIGINAL_TARGET_PATTERN = bytes(range(0x70, 0x80))
_NEW_TARGET_PATTERN = bytes((0xCC,) * 16)
_GUARD_AFTER_PATTERN = bytes(range(0x30, 0x40))
_POST_RECOVERY_PATTERN = bytes(range(0x50, 0x60))


async def _read(fram: FRAM_SPI, addr: int) -> "bytes | None":
    buf = bytearray(16)
    async with fram:
        ok = await fram.get_values(buf, addr_start=addr)
    return bytes(buf) if ok else None


def _target_state(target: bytes) -> str:
    # "original", "prefix:<n>" (the first n new bytes, then the original rest), or "other".
    for n in range(len(target) + 1):
        if target == _NEW_TARGET_PATTERN[:n] + _ORIGINAL_TARGET_PATTERN[n:]:
            return "original" if n == 0 else f"prefix:{n}"
    return "other"


async def _main() -> None:
    wdt = arm()
    chip = BENCH["instances"]["fram"]
    bus = BENCH["bus"][chip["bus"]]
    spi = asy_spi_driver.SPI(bus["id"], sck_pin=bus["sck_pin"], mosi_pin=bus["mosi_pin"], miso_pin=bus["miso_pin"])
    fram = FRAM_SPI(spi, chip["cs_pin"], logger=PrintLogHistory(name="FRAMRESETRACE"), max_size=BENCH["fram_max_size"])
    await fram.setup()
    fact("initialized", fram.initialized)
    if not fram.initialized:
        done()
        return
    try:
        fact("guard_before_ok", await _read(fram, _GUARD_BEFORE_ADDR) == _GUARD_BEFORE_PATTERN)
        target = await _read(fram, _TARGET_ADDR)
        fact("target_state", None if target is None else _target_state(target))
        fact("guard_after_ok", await _read(fram, _GUARD_AFTER_ADDR) == _GUARD_AFTER_PATTERN)
        wdt.feed()
        present = await fram.verify_present()  # takes the outer lock itself (asyncio.Lock is not reentrant)
        async with fram:
            wrote = await fram.set_values(_POST_RECOVERY_PATTERN, addr_start=_POST_RECOVERY_ADDR)
        fact("recovered", present and wrote and await _read(fram, _POST_RECOVERY_ADDR) == _POST_RECOVERY_PATTERN)
    finally:
        # Scratch, but the next run's assertion must not meet stale torn bytes: the seed state goes back.
        restored = []
        for addr, pattern in ((_GUARD_BEFORE_ADDR, _GUARD_BEFORE_PATTERN), (_TARGET_ADDR, _ORIGINAL_TARGET_PATTERN), (_GUARD_AFTER_ADDR, _GUARD_AFTER_PATTERN)):
            async with fram:
                restored.append(await fram.set_values(pattern, addr_start=addr))
        fact("seed_restored", all(restored))
    done()


asyncio.run(_main())
