"""Isolated-driver device script: FRAM_SPI's real write-protect status-register round trip
(WPEN|BP0|BP1) against the real chip - does WP gate a write AND a read, and can it be cleared again.
Reads being gated too is intended, accepted behavior - SPECIFICATION.md Part A.4's FRAM entry."""

import asyncio

import asy_spi_driver
from asy_fram_manager import AsyFramManager
from crc_checks import CRC8

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from asy_fram_manager import AsyFramChunk

CHUNK_SIZE = 16
PATTERN_A = bytes((i * 3 + 1) % 256 for i in range(CHUNK_SIZE))
PATTERN_B = bytes((i * 5 + 2) % 256 for i in range(CHUNK_SIZE))


# Each phase returns a failure reason, or None on success - keeps the phases individually readable
# and _main() a plain sequence, rather than one function with a dozen early prints.
async def _while_protected(fram: AsyFramManager, chunk: "AsyFramChunk") -> "str | None":
    if not await fram.fram.set_write_protected(value=True):
        return "set_write_protected(True) failed against the real chip"
    if not await fram.fram.get_write_protected():
        return "get_write_protected() reports False right after set_write_protected(True)"

    # A real write while protected must be rejected (FRAM_SPI._write()'s own get_write_protected() gate).
    if await chunk.write(PATTERN_B):
        return "chunk.write() succeeded while the real chip was write-protected"

    # And so must a read: _read_chunk() writes a transient busy marker before reading, so the same
    # gate stops it. Intended behavior, asserted here rather than only noted - the mock and twin
    # tiers assert the identical pair (SPECIFICATION.md Part A.4's FRAM entry).
    blocked_read = await chunk.read()
    if blocked_read is not None:
        return f"chunk.read() returned data while the real chip was write-protected: {bytes(blocked_read).hex()}"
    if await chunk.read(override_pause=True) is not None:
        return "override_pause bypassed the real chip's write protection - it only ever bypasses the manager's own pause flag"
    return None


async def _chip_itself_refuses(fram: AsyFramManager, chunk: "AsyFramChunk") -> None:
    # The checks above all stop at FRAM_SPI._write()'s own software guard, so on their own they
    # prove the DRIVER refuses, not that the silicon does. Only real hardware can answer that, so
    # the bench tier asks it directly: lie to the driver (_wp is just the cached copy of the status
    # register, and there is no WP pin on this rig) so it sends a real WREN+WRITE at a chip whose
    # BP0|BP1 still protect the whole array.
    # Deliberately returns no verdict of its own. Whether chunk.write() reports success is not the
    # claim - the driver gets no readback unless its periodic verify happens to land on this write -
    # and asserting either way would only test which side of that counter we are on. The real claim
    # is the readback in _after_clearing(): the bytes must still be PATTERN_A.
    fram.fram._wp = False  # deliberately desynced from the chip, see above
    try:
        await chunk.write(PATTERN_B)
    finally:
        fram.fram._wp = True  # back in sync with the still-protected chip


async def _after_clearing(fram: AsyFramManager, chunk: "AsyFramChunk") -> "str | None":
    if not await fram.fram.set_write_protected(value=False):
        return "set_write_protected(False) failed against the real chip"
    if await fram.fram.get_write_protected():
        return "get_write_protected() still reports True after set_write_protected(False)"

    # Verified only after clearing protection, for the reason asserted in _while_protected().
    # Clearing protection cannot alter stored bytes, so this still proves the write was blocked.
    readback = await chunk.read()
    if readback is None or bytes(readback) != PATTERN_A:
        return f"data changed despite write protection having been active - the chip itself did not refuse the guard-bypassed write: read {None if readback is None else bytes(readback).hex()}"
    if not await chunk.write(PATTERN_B):
        return "write failed after write protection was cleared again"
    readback = await chunk.read()
    if readback is None or bytes(readback) != PATTERN_B:
        return f"write after un-protecting did not take effect: read {None if readback is None else bytes(readback).hex()}"
    return None


async def _main() -> None:
    spi0 = asy_spi_driver.SPI(0, 2, 3, 4)
    fram = AsyFramManager(spi0, 5, max_size=0x40000, debug=None)
    if not await fram.setup():
        print("RESULT: FAIL fram.setup() failed - real FRAM chip not responding on spi0/cs5")
        return

    chunk = fram.get_chunk(CHUNK_SIZE, crc=CRC8())
    if chunk is None:
        print("RESULT: FAIL get_chunk() returned None")
        return

    # Always leave the real chip unprotected on exit, regardless of where a failure occurs -
    # a stuck-protected chip would silently break every other FRAM-owning module's writes.
    try:
        if not await fram.fram.set_write_protected(value=False):  # known starting state, ignore whatever was set before
            print("RESULT: FAIL could not clear write protection to establish a known starting state")
            return
        if not await chunk.write(PATTERN_A):
            print("RESULT: FAIL baseline write (unprotected) failed - real chip not writable at all")
            return
        reason = await _while_protected(fram, chunk)
        if reason is None:
            await _chip_itself_refuses(fram, chunk)
            reason = await _after_clearing(fram, chunk)
    finally:
        await fram.fram.set_write_protected(value=False)

    if reason is not None:
        print(f"RESULT: FAIL {reason}")
        return
    print("RESULT: PASS real write protection blocked a write, a read and a guard-bypassed write, and the data survived all three")


asyncio.run(_main())
