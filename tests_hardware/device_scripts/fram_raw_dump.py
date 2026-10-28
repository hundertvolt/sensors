"""Isolated-driver device script, read-only: the whole FRAM part as address-tagged hex lines through the
driver's raw get_values in 256 B pieces (an all-zero piece is skipped, so an absent address reads zero), then the
status register, write protection and RDID as facts - the board half of harness.save_fram_raw(); it never writes."""

import asyncio
import binascii

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

_PIECE_BYTES = 256  # one get_values() read, one printed line
_EVIDENCE_REGIONS = ((0, BENCH["fram_max_size"]),)  # the whole production part, read only: the session saves it before any write


async def _main() -> None:
    wdt = arm()
    chip = next(instance for instance in BENCH["instances"].values() if instance["driver"] == "fram")
    bus = BENCH["bus"][chip["bus"]]
    spi = asy_spi_driver.SPI(bus["id"], sck_pin=bus["sck_pin"], mosi_pin=bus["mosi_pin"], miso_pin=bus["miso_pin"])
    fram = FRAM_SPI(spi, chip["cs_pin"], logger=PrintLogHistory(name="FRAMDUMP"), max_size=BENCH["fram_max_size"])
    await fram.setup()  # identifies the chip (RDID) and reads its status register; no write
    piece = bytearray(_PIECE_BYTES)
    skipped, failed_at = 0, None
    async with fram:  # the driver and bus locks the synchronous read requires, held for the whole dump
        for start, length in _EVIDENCE_REGIONS:
            for address in range(start, start + length, _PIECE_BYTES):
                view = memoryview(piece)[: min(_PIECE_BYTES, start + length - address)]
                if fram.get_values_sync(view, address) != 0:
                    failed_at = address
                    break
                if any(view):
                    print(f"FRAM {address:06x} {binascii.hexlify(bytes(view)).decode()}")
                else:
                    skipped += 1
                wdt.feed()
            if failed_at is not None:
                break
        status = fram._read_status()
    fact("dump_size", sum(length for _start, length in _EVIDENCE_REGIONS))
    fact("zero_pieces", skipped)
    fact("read_failed_at", failed_at)
    fact("status_register", status)
    fact("write_protected", await fram.get_write_protected())
    fact("rdid", binascii.hexlify(bytes(fram._id_buf)).decode())
    done()


asyncio.run(_main())
