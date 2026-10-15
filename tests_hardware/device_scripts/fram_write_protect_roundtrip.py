"""Isolated-driver device script: FRAM_SPI's real write-protect status-register round trip (WPEN|BP0|BP1) - does WP
gate a write AND a read, and can it be cleared again. Reads being gated too is intended (SPECIFICATION.md Part A.4's
FRAM entry). The finally clears protection, then zeroes the chunk, so neither outlives the run."""

import asyncio

import asy_spi_driver
from asy_crc_checks import CRC8
from asy_fram_manager import FRAMManager

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

    from asy_fram_manager import FRAMChunk

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

CHUNK_SIZE = 16
PATTERN_A = bytes((i * 3 + 1) % 256 for i in range(CHUNK_SIZE))
PATTERN_B = bytes((i * 5 + 2) % 256 for i in range(CHUNK_SIZE))


async def _after_clearing(fram: FRAMManager, chunk: "FRAMChunk") -> "str | None":
    if not await fram.fram.set_write_protected(value=False):
        return "set_write_protected(False) failed against the real chip"
    if await fram.fram.get_write_protected():
        return "get_write_protected() still reports True after set_write_protected(False)"

    # Verified only after clearing protection, for the reason asserted in _while_protected().
    # Clearing protection cannot alter stored bytes, so this still proves the write was blocked.
    readback = await chunk.read()
    fact("data_survived", readback is not None and bytes(readback) == PATTERN_A)
    if readback is None or bytes(readback) != PATTERN_A:
        return f"data changed despite write protection having been active - the chip itself did not refuse the guard-bypassed write: read {None if readback is None else bytes(readback).hex()}"
    if not await chunk.write(PATTERN_B):
        return "write failed after write protection was cleared again"
    readback = await chunk.read()
    if readback is None or bytes(readback) != PATTERN_B:
        return f"write after un-protecting did not take effect: read {None if readback is None else bytes(readback).hex()}"
    return None


async def _chip_itself_refuses(fram: FRAMManager, chunk: "FRAMChunk") -> None:
    # The checks above stop at FRAM_SPI._write()'s software guard, so they prove the DRIVER
    # refuses, not the silicon. Lying to the driver (_wp is only a cached status-register copy)
    # sends a real WREN+WRITE at a chip whose BP0|BP1 still protect the whole array.

    # No verdict of its own: whether chunk.write() reports success only says which side of the
    # periodic-verify counter this landed on. The claim is _after_clearing()'s readback - the
    # bytes must still be PATTERN_A.
    fram.fram._wp = False  # deliberately desynced from the chip, see above
    try:
        await chunk.write(PATTERN_B)
    finally:
        fram.fram._wp = True  # back in sync with the still-protected chip


async def _main() -> None:
    arm()
    chip = next(instance for instance in BENCH["instances"].values() if instance["driver"] == "fram")
    bus = BENCH["bus"][chip["bus"]]
    spi = asy_spi_driver.SPI(bus["id"], sck_pin=bus["sck_pin"], mosi_pin=bus["mosi_pin"], miso_pin=bus["miso_pin"])
    fram = FRAMManager(spi, chip["cs_pin"], BENCH["fram_max_size"])
    fact("setup", await fram.setup())
    chunk = fram.get_chunk(CHUNK_SIZE, crc=CRC8(), owner="fram_write_protect_roundtrip")
    fact("allocated", chunk is not None)
    if chunk is None:
        done()
        return
    # Always leave the real chip unprotected on exit, regardless of where a failure occurs -
    # a stuck-protected chip would silently break every other FRAM-owning module's writes.
    reason: str | None = "the run ended before its phases"
    try:
        if not await fram.fram.set_write_protected(value=False):  # a known starting state, whatever was set before
            reason = "could not clear write protection to establish a known starting state"
        elif not await chunk.write(PATTERN_A):
            reason = "baseline write (unprotected) failed - the real chip is not writable at all"
        else:
            reason = await _while_protected(fram, chunk)
            if reason is None:
                await _chip_itself_refuses(fram, chunk)
                reason = await _after_clearing(fram, chunk)
    finally:
        fact("left_protected", not await fram.fram.set_write_protected(value=False))
        fact("cleared_last", await chunk.clear())
    fact("failure", reason)
    done()


# Each phase returns a failure reason, or None on success - keeps the phases individually readable
# and _main() a plain sequence, rather than one function with a dozen early prints.
async def _while_protected(fram: FRAMManager, chunk: "FRAMChunk") -> "str | None":
    if not await fram.fram.set_write_protected(value=True):
        return "set_write_protected(True) failed against the real chip"
    if not await fram.fram.get_write_protected():
        return "get_write_protected() reports False right after set_write_protected(True)"

    # A real write while protected must be rejected (FRAM_SPI._write()'s own get_write_protected() gate).
    blocked_write = not await chunk.write(PATTERN_B)
    fact("blocked_write", blocked_write)
    if not blocked_write:
        return "chunk.write() succeeded while the real chip was write-protected"

    # And so must a read: _read_chunk() writes a transient busy marker before reading, so the same
    # gate stops it. Intended behavior, asserted here rather than only noted - the mock and twin
    # tiers assert the identical pair (SPECIFICATION.md Part A.4's FRAM entry).
    read_back = await chunk.read()
    fact("blocked_read", read_back is None)
    if read_back is not None:
        return f"chunk.read() returned data while the real chip was write-protected: {bytes(read_back).hex()}"
    return None


asyncio.run(_main())
