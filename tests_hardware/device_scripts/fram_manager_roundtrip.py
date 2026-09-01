"""Isolated-driver device script, flash-tier gap fix: AsyFramManager/FRAM_SPI (asy_fram_manager.py/
asy_fram_driver.py) against the real MB85RS64V SPI FRAM chip - the "FRAM working at all" gap (no
automated real-hardware test of this chip existed before this file; the pre-existing reboot-
persistence tests in flash/test_reboot_persistence.py exercise config_manager's littlefs-backed
storage, a structurally different mechanism - see that file's own module docstring).

Exercises the real chain a production chunk owner (SystemService, BMP3xx_Reader, SCD30_Reader, ...)
actually goes through: fram.setup() (a real SPI RDID probe, verifying manufacturer/product ID
against the datasheet-documented values - see asy_fram_driver.py's _KNOWN_PRODUCT_IDS), get_chunk()
(the dual-copy/CRC allocator), chunk.write()/chunk.read() (real SPI read/write transactions, CRC8
add-then-check, dual-copy comparison). A deterministic non-trivial byte pattern (not all-zero/
all-0xFF) is used so a real round trip is actually being verified, not just "some bytes came back".

Uses the exact same spi0/cs construction sensortask_wozi.py's build_system() uses for the real FRAM
chip (SPI(0, 2, 3, 4), cs=1, max_size=0x2000).

Run via `mpremote run <this> soft-reset`."""

import asyncio

import asy_spi_driver
from asy_fram_manager import AsyFramManager
from crc_checks import CRC8

CHUNK_SIZE = 32
PATTERN = bytes((i * 7 + 3) % 256 for i in range(CHUNK_SIZE))  # non-trivial, not all-zero/all-0xFF


async def _main() -> None:
    spi0 = asy_spi_driver.SPI(0, 2, 3, 4)
    fram = AsyFramManager(spi0, 1, max_size=0x2000, debug=None)
    if not await fram.setup():
        print("RESULT: FAIL fram.setup() failed - real FRAM chip not responding on spi0/cs1 (RDID probe failed)")
        return

    chunk = fram.get_chunk(CHUNK_SIZE, crc=CRC8())
    if chunk is None:
        print("RESULT: FAIL get_chunk() returned None - allocator rejected a fresh chunk request")
        return

    if not await chunk.write(PATTERN):
        print("RESULT: FAIL chunk.write() returned False - real SPI write to FRAM failed")
        return

    read_back = await chunk.read()
    if read_back is None:
        print("RESULT: FAIL chunk.read() returned None after a successful write - real SPI read/CRC/dual-copy check failed")
        return

    if bytes(read_back) != PATTERN:
        print(f"RESULT: FAIL read-back data does not match written pattern - wrote {PATTERN.hex()}, read {bytes(read_back).hex()}")
        return

    print(f"RESULT: PASS wrote and read back {CHUNK_SIZE} bytes matching the pattern via the real FRAM chip")


asyncio.run(_main())
