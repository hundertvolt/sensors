"""Isolated-driver device script: the real-hardware half of the SPI RX-overrun story. The overrun is a DMA timing
condition Python cannot induce; its consequence is - both blocks left _STATUS_BUSY lock the chunk unreadable until
rewritten, intended on a destructive-readout part (Part A.4). The chunk is rewritten with zeros on the way out."""

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
    from _shared.facts import done, errors, fact
    from _shared.watchdog import arm
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

CHUNK_SIZE = 32
PATTERN_A = bytes((i * 7 + 3) % 256 for i in range(CHUNK_SIZE))
PATTERN_B = bytes((i * 11 + 29) % 256 for i in range(CHUNK_SIZE))
# Wire-level values, hardcoded rather than imported: asy_fram_manager.py's own _STATUS_*/_ADDR_*
# are micropython.const() and compiled away, the same convention the mock tier's tests follow.
_STATUS_BUSY = 0x02
_STATUS_LEN = 2
failures: list[str] = []


async def _force_both_blocks_busy(fram: FRAMManager, chunk_size: int, crc_len: int, block_addr: "tuple[int, int]") -> bool:
    # Writes _STATUS_BUSY into both status bytes of both blocks, through the real driver - the
    # state a read interrupted mid-transfer genuinely leaves behind.
    async with fram.fram as dev:
        for base in block_addr:
            st_addr = base + chunk_size + crc_len
            for offset in range(_STATUS_LEN):
                if not await dev.set_values(bytearray([_STATUS_BUSY]), st_addr + offset):
                    return False
    return True


async def _main() -> None:
    arm()
    chip = next(instance for instance in BENCH["instances"].values() if instance["driver"] == "fram")
    bus = BENCH["bus"][chip["bus"]]
    spi = asy_spi_driver.SPI(bus["id"], sck_pin=bus["sck_pin"], mosi_pin=bus["mosi_pin"], miso_pin=bus["miso_pin"])
    fram = FRAMManager(spi, chip["cs_pin"], BENCH["fram_max_size"])
    fact("setup", await fram.setup())
    crc = CRC8()
    chunk = fram.get_chunk(CHUNK_SIZE, crc=crc, owner="fram_busy_status_lockout")
    fact("allocated", chunk is not None)
    if chunk is None:
        done()
        return
    try:
        fact("cleared_first", await chunk.clear())
        fact("baseline_ok", check("baseline write or read did not round-trip", condition=await chunk.write(PATTERN_A) is True and bytes(await chunk.read() or b"") == PATTERN_A))
        forced = await _force_both_blocks_busy(fram, CHUNK_SIZE, crc.length(), chunk._block_addr)
        fact("forced_busy", check("could not write the BUSY status bytes through the real driver", condition=forced))
        if forced:
            # Both copies busy: the read must refuse rather than hand back bytes it cannot vouch for.
            fact("locked_read_none", check("a chunk with both blocks BUSY still returned data", condition=await chunk.read() is None))
            fact("error_logged", check("the refused read logged no error", condition="E" in (await fram.get_error_counter())["FRAM"]["ErrType"]))
            # A write is what clears it: the lockout is recoverable, not a permanently dead chunk.
            recovered = await chunk.write(PATTERN_B) is True and bytes(await chunk.read() or b"") == PATTERN_B
            fact("recovered", check("a rewrite did not clear the stuck BUSY status", condition=recovered))
    finally:
        fact("cleared_last", await chunk.write(bytes(CHUNK_SIZE)))
    errors("failures", len(failures), failures)
    done()


def check(msg: str, *, condition: bool) -> bool:
    if not condition:
        failures.append(msg)
    return condition


asyncio.run(_main())
