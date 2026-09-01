"""Isolated-driver device script, bottom-level hardware-function gap fix: FRAM_SPI's real
write-protect status-register round trip (asy_fram_driver.py's set_write_protected()/
get_write_protected(), the WPEN|BP0|BP1 bits - datasheet MB85RS64V-DS501-00015 status register
table) against the real MB85RS64V chip - not just "can a chunk be written", but "does the real
WP hardware mechanism actually gate a real write, and can it be turned back off again".

Run via `mpremote run <this> soft-reset`."""

import asyncio

import asy_spi_driver
from asy_fram_manager import AsyFramManager
from crc_checks import CRC8

CHUNK_SIZE = 16
PATTERN_A = bytes((i * 3 + 1) % 256 for i in range(CHUNK_SIZE))
PATTERN_B = bytes((i * 5 + 2) % 256 for i in range(CHUNK_SIZE))


async def _main() -> None:
    spi0 = asy_spi_driver.SPI(0, 2, 3, 4)
    fram = AsyFramManager(spi0, 1, max_size=0x2000, debug=None)
    if not await fram.setup():
        print("RESULT: FAIL fram.setup() failed - real FRAM chip not responding on spi0/cs1")
        return

    chunk = fram.get_chunk(CHUNK_SIZE, crc=CRC8())
    if chunk is None:
        print("RESULT: FAIL get_chunk() returned None")
        return

    # Always leave the real chip unprotected on exit, regardless of where a failure occurs -
    # a stuck-protected chip would silently break every other FRAM-owning module's writes.
    try:
        if not await fram.fram.set_write_protected(False):  # known starting state, ignore whatever was set before
            print("RESULT: FAIL could not clear write protection to establish a known starting state")
            return

        if not await chunk.write(PATTERN_A):
            print("RESULT: FAIL baseline write (unprotected) failed - real chip not writable at all")
            return

        if not await fram.fram.set_write_protected(True):
            print("RESULT: FAIL set_write_protected(True) failed against the real chip")
            return
        if not await fram.fram.get_write_protected():
            print("RESULT: FAIL get_write_protected() reports False right after set_write_protected(True)")
            return

        # A real write while protected must be rejected (FRAM_SPI._write()'s own get_write_protected() gate).
        blocked = await chunk.write(PATTERN_B)
        if blocked:
            print("RESULT: FAIL chunk.write() succeeded while the real chip was write-protected")
            return
        readback = await chunk.read()
        if readback is None or bytes(readback) != PATTERN_A:
            print(f"RESULT: FAIL data changed despite write protection being active: read {None if readback is None else bytes(readback).hex()}")
            return

        if not await fram.fram.set_write_protected(False):
            print("RESULT: FAIL set_write_protected(False) failed against the real chip")
            return
        if await fram.fram.get_write_protected():
            print("RESULT: FAIL get_write_protected() still reports True after set_write_protected(False)")
            return
        if not await chunk.write(PATTERN_B):
            print("RESULT: FAIL write failed after write protection was cleared again")
            return
        readback = await chunk.read()
        if readback is None or bytes(readback) != PATTERN_B:
            print(f"RESULT: FAIL write after un-protecting did not take effect: read {None if readback is None else bytes(readback).hex()}")
            return
    finally:
        await fram.fram.set_write_protected(False)

    print("RESULT: PASS real write protection blocked a write while active and allowed one once cleared")


asyncio.run(_main())
