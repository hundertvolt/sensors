"""Isolated-driver device script: AsyFramManager/FRAM_SPI against the real MB85RS2MTA SPI FRAM chip
- exercises the real chunk-owner chain (fram.setup()'s RDID probe, get_chunk()'s dual-copy/CRC
allocator, chunk.write()/read()) with a deterministic non-trivial byte pattern."""

import asyncio

import asy_spi_driver
from asy_fram_manager import AsyFramManager
from crc_checks import CRC8

CHUNK_SIZE = 32
PATTERN = bytes((i * 7 + 3) % 256 for i in range(CHUNK_SIZE))  # non-trivial, not all-zero/all-0xFF


async def _main() -> None:
    spi0 = asy_spi_driver.SPI(0, 2, 3, 4)
    fram = AsyFramManager(spi0, 5, max_size=0x40000, debug=None)
    if not await fram.setup():
        print("RESULT: FAIL fram.setup() failed - real FRAM chip not responding on spi0/cs5 (RDID probe failed)")
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
