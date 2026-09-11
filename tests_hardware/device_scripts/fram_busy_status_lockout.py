"""Isolated-driver device script: the real-hardware half of the SPI RX-overrun story (BACKLOG.md).
An overrun itself is a DMA timing condition nothing in Python can induce, but its CONSEQUENCE is
inducible - both blocks left _STATUS_BUSY must lock the chunk unreadable until rewritten, which on
a destructive-readout part is intended behaviour, not a defect (SPECIFICATION.md Part A.4)."""

import asyncio

import asy_spi_driver
from asy_fram_manager import AsyFramManager
from crc_checks import CRC8

CHUNK_SIZE = 32
PATTERN_A = bytes((i * 7 + 3) % 256 for i in range(CHUNK_SIZE))
PATTERN_B = bytes((i * 11 + 29) % 256 for i in range(CHUNK_SIZE))
# Wire-level values, hardcoded rather than imported: asy_fram_manager.py's own _STATUS_*/_ADDR_*
# are micropython.const() and compiled away, the same convention the mock tier's tests follow.
_STATUS_BUSY = 0x02
_STATUS_LEN = 2
failures: list[str] = []


def check(msg: str, *, condition: bool) -> None:
    if not condition:
        failures.append(msg)


async def _force_both_blocks_busy(fram: AsyFramManager, chunk_size: int, crc_len: int, block_addr: "tuple[int, int]") -> bool:
    """Writes _STATUS_BUSY into both status bytes of both blocks, through the real driver - the
    state a read interrupted mid-transfer genuinely leaves behind."""
    async with fram.fram as dev:
        for base in block_addr:
            st_addr = base + chunk_size + crc_len
            for offset in range(_STATUS_LEN):
                if not await dev.set_values(bytearray([_STATUS_BUSY]), st_addr + offset):
                    return False
    return True


async def _main() -> None:
    spi0 = asy_spi_driver.SPI(0, 2, 3, 4)
    fram = AsyFramManager(spi0, 5, max_size=0x40000, debug=None)
    if not await fram.setup():
        print("RESULT: FAIL fram.setup() failed - real FRAM chip not responding on spi0/cs5")
        return

    crc = CRC8()
    chunk = fram.get_chunk(CHUNK_SIZE, crc=crc)
    if chunk is None:
        print("RESULT: FAIL get_chunk() returned None")
        return

    check("baseline write failed", condition=await chunk.write(PATTERN_A) is True)
    check("baseline read did not return the written pattern", condition=bytes(await chunk.read() or b"") == PATTERN_A)

    if not await _force_both_blocks_busy(fram, CHUNK_SIZE, crc.length(), chunk.block_addr):
        print("RESULT: FAIL could not write the BUSY status bytes through the real driver")
        return

    # Both copies busy: the read must refuse rather than hand back bytes it cannot vouch for.
    check("a chunk with both blocks left BUSY still returned data - the lockout did not engage", condition=await chunk.read() is None)
    errs = await fram.get_error_counter()
    check("the refused read logged no error at all", condition="E" in errs["FRAM"]["ErrType"])

    # A write is what clears it - proving the lockout is recoverable, not a permanently dead chunk.
    check("a write did not clear the stuck BUSY status", condition=await chunk.write(PATTERN_B) is True)
    check("the chunk did not read back correctly after the recovering write", condition=bytes(await chunk.read() or b"") == PATTERN_B)

    if failures:
        print(f"RESULT: FAIL {len(failures)} issue(s): {'; '.join(failures[:6])}")
    else:
        print("RESULT: PASS both-blocks-BUSY locks the real chunk unreadable and a rewrite recovers it")


asyncio.run(_main())
