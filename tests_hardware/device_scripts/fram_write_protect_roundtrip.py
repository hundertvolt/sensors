"""Isolated-driver device script, bottom-level hardware-function gap fix: FRAM_SPI's real
write-protect status-register round trip (asy_fram_driver.py's set_write_protected()/
get_write_protected(), the WPEN|BP0|BP1 bits - same status-register mechanism datasheeted for both
Fujitsu FRAM chips this project uses) against the real MB85RS2MTA chip this bench unit carries
(CS=GPIO5, not the deployed wozi unit's MB85RS64V at CS=GPIO1 - dev_legacy/README.md's own wiring
table, confirmed directly against this bench's live main.py and a real RDID probe) - not just "can
a chunk be written", but "does the real WP hardware mechanism actually gate a real write, and can
it be turned back off again".

No error-log check for the blocked write itself (unlike bench/test_network_resilience.py's fault-
injection tests): flash tier has no network, so there is no /status to check against at all here;
separately, FRAM_SPI._write()'s own write-protected rejection calls the plain self.pr.wrn() (not
wrn_s()), confirmed directly - never persisted to the history this device script's own chunk shares
with fram_error_log_roundtrip.py, so nothing would show up there either way.

REAL FINDING, flagged not fixed (a real src/ interaction, not a test bug once found): a chunk
read() cannot be performed while the chip is write-protected - _AsyBaseFramChunk._read_chunk()'s
own busy/idle status-byte protocol needs to WRITE a transient busy marker before it reads data
(asy_fram_manager.py's _handle_status_bytes()/_set_check_sb(), gated the same as any other write by
FRAM_SPI._write()'s get_write_protected() check), so a real write-protected chip makes chunk.read()
return None too, not just chunk.write(). Confirmed directly against real hardware (an earlier draft
of this script tried to read the chunk immediately after the blocked write, still under
protection, and got None every time - not a script bug in the read/compare logic itself). This
script therefore only reads back the data *after* clearing write protection again - clearing
protection is a status-register-only operation that cannot itself alter the stored bytes, so this
still fully verifies "the blocked write left the data unchanged," just not literally
mid-protection. Whether "reads also blocked while write-protected" is the intended, accepted
behavior of the busy-flag protocol is a project-owner call, not decided here.

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

        if not await fram.fram.set_write_protected(False):
            print("RESULT: FAIL set_write_protected(False) failed against the real chip")
            return
        if await fram.fram.get_write_protected():
            print("RESULT: FAIL get_write_protected() still reports True after set_write_protected(False)")
            return

        # Verified only now, after clearing protection - see this file's own module docstring:
        # chunk.read() itself needs write access (a transient busy-status byte) and would return
        # None while still protected, regardless of whether the data was actually left unchanged.
        # Clearing protection can't itself alter the stored bytes, so this still proves the blocked
        # write above left the data untouched.
        readback = await chunk.read()
        if readback is None or bytes(readback) != PATTERN_A:
            print(f"RESULT: FAIL data changed despite write protection having been active: read {None if readback is None else bytes(readback).hex()}")
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
