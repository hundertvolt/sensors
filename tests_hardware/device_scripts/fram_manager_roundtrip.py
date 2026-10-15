"""Isolated-driver device script: FRAMManager/FRAM_SPI against the real FRAM part - the chunk-owner chain (setup()'s
RDID probe, get_chunk()'s dual-copy/CRC allocator, chunk.write()/read()) with a non-trivial pattern, the part's RDID
reported; the chunk is cleared after setup and again on the way out, so no pattern survives the run."""

import asyncio
import binascii

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

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

CHUNK_SIZE = 32
PATTERN = bytes((i * 7 + 3) % 256 for i in range(CHUNK_SIZE))  # non-trivial, not all-zero/all-0xFF


async def _main() -> None:
    arm()
    chip = next(instance for instance in BENCH["instances"].values() if instance["driver"] == "fram")
    bus = BENCH["bus"][chip["bus"]]
    spi = asy_spi_driver.SPI(bus["id"], sck_pin=bus["sck_pin"], mosi_pin=bus["mosi_pin"], miso_pin=bus["miso_pin"])
    fram = FRAMManager(spi, chip["cs_pin"], BENCH["fram_max_size"])
    ready = await fram.setup()
    fact("setup", ready)
    fact("rdid", binascii.hexlify(bytes(fram.fram._id_buf)).decode())
    chunk = fram.get_chunk(CHUNK_SIZE, crc=CRC8(), owner="fram_manager_roundtrip") if ready else None
    fact("allocated", chunk is not None)
    if chunk is not None:
        try:
            fact("cleared_first", await chunk.clear())
            fact("written", await chunk.write(PATTERN))
            read_back = await chunk.read()
            fact("read_ok", read_back is not None)
            fact("matches", read_back is not None and bytes(read_back) == PATTERN)
        finally:
            fact("cleared_last", await chunk.clear())
    done()


asyncio.run(_main())
