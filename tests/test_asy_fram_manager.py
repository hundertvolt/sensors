import asyncio

from _fram_chip_fake import FakeMB85RS64V

import asy_fram_manager
import asy_spi_driver
from asy_fram_manager import AsyFramChunkBuffer, AsyFramManager
from asy_spi_driver import SPI
from crc_checks import CRC8, CRC_Pass

# Same one-process-per-test-file swap as test_asy_fram_driver.py - see its own comment.
asy_spi_driver._SPI = FakeMB85RS64V  # type: ignore[misc]

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")

# Real on-chip constant values (asy_fram_manager.py's own _STATUS_* are micropython.const() and
# compiled away - not importable - so these are hardcoded, matching test_asy_fram_driver.py's own
# convention of hardcoding raw wire-level values rather than importing driver internals).
_STATUS_UNINIT = 0x00
_STATUS_IDLE = 0x01
_STATUS_BUSY = 0x02


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


def make_bus() -> SPI:
    return SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)


def make_manager(max_size: int = 0x2000, history_length: int = 10) -> tuple[AsyFramManager, FakeMB85RS64V]:
    bus = make_bus()
    manager = AsyFramManager(bus, 1, max_size=max_size, history_length=history_length)
    chip = manager.fram._spidev.spi._spi
    assert isinstance(chip, FakeMB85RS64V)
    return manager, chip


async def setup_manager(manager: AsyFramManager) -> bool:
    return await manager.setup()


async def _synced() -> bool:
    return True


async def _not_synced() -> bool:
    return False


async def _raising_callback() -> bool:
    raise RuntimeError("ntp callback exploded")


# ---------------------------------------------------------------------------
# Allocator - bump-pointer offsets, the static-layout invariant the whole file relies on
# ---------------------------------------------------------------------------


def test_get_chunk_sequential_allocation_offsets_match_bump_pointer_math() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk1 = manager.get_chunk(4)  # default crc is CRC_Pass, length 0
    chunk2 = manager.get_chunk(8)
    assert chunk1 is not None and chunk2 is not None
    # block_addr[1] is where block 1 (the 2nd redundant copy) starts within the chunk, not the
    # end of the chunk's whole 2-block allocation - that end is base_addr + full_size (2*block).
    assert chunk1.block_addr == (0, 6)  # block 0 at [0,6), block 1 at [6,12) - 4 data+0 crc+2 status each
    assert chunk2.block_addr == (12, 22)  # starts at chunk1's full 2*(4+0+2)=12; block length 8+0+2=10


def test_allocation_order_not_chunk_size_determines_offsets() -> None:
    # The static-allocation invariant this whole file depends on: whichever get_chunk()/
    # get_timestamped_chunk() call happens first claims the lower offset, regardless of the
    # chunk's own size - this is why call order must stay identical across firmware versions for
    # a device's existing stored data to still decode correctly.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    small_first = manager.get_chunk(2)
    big_second = manager.get_chunk(50)
    assert small_first is not None and big_second is not None
    assert small_first.block_addr[0] < big_second.block_addr[0]
    # small_first's own full 2-block span ends at block_addr[1] + one block's length (block 1
    # starts at block_addr[1] and is the same length as block 0, i.e. block_addr[1]-block_addr[0]).
    small_first_end = small_first.block_addr[1] + (small_first.block_addr[1] - small_first.block_addr[0])
    assert big_second.block_addr[0] == small_first_end  # immediately follows, no gap


def test_get_chunk_returns_none_when_request_exceeds_remaining_capacity() -> None:
    manager, _chip = make_manager(max_size=16)
    run(setup_manager(manager))
    assert manager.get_chunk(100) is None


def test_get_timestamped_chunk_size_includes_the_8_byte_timestamp() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(4, _synced)
    assert chunk is not None
    assert chunk.block_addr == (0, 4 + 8 + 0 + 2)  # size(4) + ts(8) + crc(0) + status(2) = 14


# ---------------------------------------------------------------------------
# Basic write/read round trip and size-mismatch guards
# ---------------------------------------------------------------------------


def test_read_before_any_write_returns_none() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8())
    assert chunk is not None

    async def scenario() -> bytearray | None:
        return await chunk.read()

    assert run(scenario()) is None


def test_write_then_read_round_trip_no_crc() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(5, crc=CRC_Pass())
    assert chunk is not None

    async def scenario() -> bytearray | None:
        await chunk.write(b"hello")
        return await chunk.read()

    assert run(scenario()) == bytearray(b"hello")


def test_write_then_read_round_trip_with_crc8() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(5, crc=CRC8())
    assert chunk is not None

    async def scenario() -> bytearray | None:
        await chunk.write(b"world")
        return await chunk.read()

    assert run(scenario()) == bytearray(b"world")


def test_write_rejects_data_larger_than_chunk_size() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass())
    assert chunk is not None

    async def scenario() -> bool:
        return await chunk.write(b"toolong!")

    assert run(scenario()) is False


def test_write_into_rejects_a_buffer_of_the_wrong_size() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass())
    assert chunk is not None
    wrong_buf = AsyFramChunkBuffer(8, 0)  # this chunk expects 4 payload bytes, not 8

    async def scenario() -> bool:
        return await chunk.write_into(wrong_buf)

    assert run(scenario()) is False


def test_preallocated_buffer_write_into_read_into_round_trip() -> None:
    # The "ad hoc vs. preallocated" top-level interface: write_into()/read_into() let a caller
    # reuse one buffer across calls via get_buffer(), instead of write()/read()'s own
    # fresh-allocation-per-call convenience wrapper.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8())
    assert chunk is not None
    buf = chunk.get_buffer()
    databuf = buf.get_data_buf()
    assert databuf is not None
    databuf[:] = b"data"

    async def scenario() -> tuple[bool, bool, bytearray | None]:
        write_ok = await chunk.write_into(buf)
        read_buf = chunk.get_buffer()
        read_ok = await chunk.read_into(read_buf)
        data = read_buf.get_data_buf()
        return write_ok, read_ok, None if data is None else bytearray(data)

    write_ok, read_ok, data = run(scenario())
    assert write_ok is True
    assert read_ok is True
    assert data == bytearray(b"data")


# ---------------------------------------------------------------------------
# Dual-copy self-healing and torn-write detection - the actual data-loss-prevention machinery
# ---------------------------------------------------------------------------


def test_corrupted_block0_status_falls_back_to_block1_and_self_heals_block0() -> None:
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass())
    assert chunk is not None

    async def scenario() -> bytearray | None:
        await chunk.write(b"good")
        addr0, _addr1 = chunk.block_addr
        # Simulate power loss mid-write: block 0 left with status BUSY (never reached the final
        # "set IDLE" step) - the same on-chip state a real torn write leaves behind.
        chip.memory[addr0 + 4] = _STATUS_BUSY
        chip.memory[addr0 + 5] = _STATUS_BUSY
        return await chunk.read()

    result = run(scenario())
    assert result == bytearray(b"good")  # recovered from block 1
    addr0, _addr1 = chunk.block_addr
    assert chip.memory[addr0 + 4] == _STATUS_IDLE  # block 0 healed back to IDLE...
    assert bytes(chip.memory[addr0 : addr0 + 4]) == b"good"  # ...with the correct data


def test_corrupted_block1_status_leaves_block0_valid_and_self_heals_block1() -> None:
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass())
    assert chunk is not None

    async def scenario() -> bytearray | None:
        await chunk.write(b"good")
        _addr0, addr1 = chunk.block_addr
        chip.memory[addr1 + 4] = _STATUS_BUSY
        chip.memory[addr1 + 5] = _STATUS_BUSY
        return await chunk.read()

    result = run(scenario())
    assert result == bytearray(b"good")
    _addr0, addr1 = chunk.block_addr
    assert chip.memory[addr1 + 4] == _STATUS_IDLE
    assert bytes(chip.memory[addr1 : addr1 + 4]) == b"good"


def test_crc8_detects_corrupted_payload_byte_and_falls_back_to_other_block() -> None:
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8())
    assert chunk is not None

    async def scenario() -> bytearray | None:
        await chunk.write(b"good")
        addr0, _addr1 = chunk.block_addr
        # Flip a payload byte directly on the "chip", bypassing the driver entirely - raw SPI has
        # no way to detect this (see test_asy_fram_driver.py); this is exactly the corruption
        # class CRC8 + dual-copy redundancy exist to catch one layer up.
        chip.memory[addr0] ^= 0xFF
        return await chunk.read()

    assert run(scenario()) == bytearray(b"good")  # recovered from block 1, CRC caught block 0


def test_read_reports_failure_when_both_blocks_valid_but_hold_different_data() -> None:
    # Simulates a write torn between finishing block 0 and starting block 1: both blocks
    # independently look fine (CRC_Pass never checks payload content, status bytes are IDLE) but
    # hold different data - no generation counter can say which is "right", so this must fail
    # rather than guess (owner-confirmed intentional design, see asy_fram_manager.py's docstring).
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass())
    assert chunk is not None
    addr0, addr1 = chunk.block_addr
    chip.memory[addr0 : addr0 + 4] = b"AAAA"
    chip.memory[addr0 + 4] = _STATUS_IDLE
    chip.memory[addr0 + 5] = _STATUS_IDLE
    chip.memory[addr1 : addr1 + 4] = b"BBBB"
    chip.memory[addr1 + 4] = _STATUS_IDLE
    chip.memory[addr1 + 5] = _STATUS_IDLE

    async def scenario() -> bytearray | None:
        return await chunk.read()

    assert run(scenario()) is None


# ---------------------------------------------------------------------------
# verify - periodic write-back verification
# ---------------------------------------------------------------------------


def test_get_verify_set_verify_round_trip() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass())
    assert chunk is not None

    async def scenario() -> tuple[int, int]:
        before = await chunk.get_verify()
        await chunk.set_verify(3)
        after = await chunk.get_verify()
        return before, after

    before, after = run(scenario())
    assert before == 0
    assert after == 3


def test_write_with_verify_enabled_succeeds_for_correct_data() -> None:
    # Exercises the real _compare_with verification path (not just a getter/setter round trip):
    # with verify=1, every write re-reads and compares both blocks against what was just written.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8(), verify=1)
    assert chunk is not None

    async def scenario() -> bool:
        return await chunk.write(b"good")

    assert run(scenario()) is True


# ---------------------------------------------------------------------------
# pause / override_pause
# ---------------------------------------------------------------------------


def test_manager_pause_blocks_chunk_operations_without_override() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass())
    assert chunk is not None
    run(chunk.write(b"data"))
    manager.set_pause(True)

    async def scenario() -> tuple[bool, bytearray | None]:
        write_ok = await chunk.write(b"else")
        read_result = await chunk.read()
        return write_ok, read_result

    write_ok, read_result = run(scenario())
    assert write_ok is False
    assert read_result is None  # refused, not "no data" - but collapses to the same sentinel

    manager.set_pause(False)

    async def confirm() -> bytearray | None:
        return await chunk.read()

    assert run(confirm()) == bytearray(b"data")  # original data intact - "else" write was refused


def test_override_pause_bypasses_manager_pause() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass())
    assert chunk is not None
    manager.set_pause(True)

    async def scenario() -> tuple[bool, bytearray | None]:
        write_ok = await chunk.write(b"data", override_pause=True)
        read_result = await chunk.read(override_pause=True)
        return write_ok, read_result

    write_ok, read_result = run(scenario())
    assert write_ok is True
    assert read_result == bytearray(b"data")


# ---------------------------------------------------------------------------
# clear()
# ---------------------------------------------------------------------------


def test_clear_resets_chunk_to_reading_as_uninitialized() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass())
    assert chunk is not None
    run(chunk.write(b"data"))
    assert run(chunk.read()) == bytearray(b"data")

    async def scenario() -> tuple[bool, bytearray | None]:
        cleared = await chunk.clear()
        data = await chunk.read()
        return cleared, data

    cleared, data = run(scenario())
    assert cleared is True
    assert data is None


# ---------------------------------------------------------------------------
# Timestamped chunk - NTP gating and age computation
# ---------------------------------------------------------------------------


def test_timestamped_write_without_ntp_sync_stores_uninit_timestamp() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(4, _not_synced, crc=CRC_Pass())
    assert chunk is not None

    async def scenario() -> tuple[bool, int | None, bool, int | None, int | None, bytearray | None]:
        ntp_synced, utc, write_ok = await chunk.write(b"data")
        ts, age, data = await chunk.read()
        return ntp_synced, utc, write_ok, ts, age, data

    ntp_synced, _utc, write_ok, ts, age, data = run(scenario())
    assert ntp_synced is False
    assert write_ok is True
    assert ts is None
    assert age is None
    assert data == bytearray(b"data")


def test_timestamped_write_with_ntp_sync_stores_and_reads_back_valid_timestamp() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(4, _synced, crc=CRC_Pass())
    assert chunk is not None

    async def scenario() -> tuple[bool, int | None, int | None, int | None, bytearray | None]:
        ntp_synced, utc, write_ok = await chunk.write(b"data")
        assert write_ok is True
        ts, age, data = await chunk.read()
        return ntp_synced, utc, ts, age, data

    ntp_synced, utc, ts, age, data = run(scenario())
    assert ntp_synced is True
    assert utc is not None and utc != 0
    assert ts == utc
    assert age is not None and age >= 0
    assert data == bytearray(b"data")


def test_timestamped_read_skips_age_when_currently_not_synced() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    write_chunk = manager.get_timestamped_chunk(4, _synced, crc=CRC_Pass())
    assert write_chunk is not None
    run(write_chunk.write(b"data"))

    # A second handle onto the same chunk, synced at write time but not at read time.
    read_chunk = manager.get_timestamped_chunk(4, _not_synced, crc=CRC_Pass())
    assert read_chunk is not None
    read_chunk.block_addr = write_chunk.block_addr  # same on-chip storage, different callback

    async def scenario() -> tuple[int | None, int | None]:
        ts, age, _data = await read_chunk.read()
        return ts, age

    ts, age = run(scenario())
    assert ts is not None  # the timestamp itself was stored validly...
    assert age is None  # ...but age can't be computed without a currently-synced clock


def test_timestamped_write_require_ntp_refuses_when_not_synced_and_persists_nothing() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(4, _not_synced, crc=CRC_Pass())
    assert chunk is not None

    async def scenario() -> tuple[bool, int | None, bool, tuple[int | None, int | None, bytearray | None]]:
        ntp_synced, utc, write_ok = await chunk.write(b"data", require_ntp=True)
        read_result = await chunk.read()
        return ntp_synced, utc, write_ok, read_result

    ntp_synced, utc, write_ok, read_result = run(scenario())
    assert (ntp_synced, utc, write_ok) == (False, None, False)
    assert read_result == (None, None, None)


# ---------------------------------------------------------------------------
# Regression tests for bugs found and fixed during this file's src/ promotion
# ---------------------------------------------------------------------------


def test_ntp_callback_raising_degrades_to_not_synced_instead_of_propagating() -> None:
    # ntp_sync_callback is a caller-injected dependency (async_connect.py, not itself audited)
    # that could legitimately misbehave - was called unguarded before this promotion.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(4, _raising_callback, crc=CRC_Pass())
    assert chunk is not None

    async def scenario() -> tuple[bool, int | None, bool]:
        return await chunk.write(b"data")

    ntp_synced, _utc, write_ok = run(scenario())
    assert ntp_synced is False
    assert write_ok is True  # still writes, with the uninitialized timestamp sentinel


def test_mktime_overflow_degrades_to_uninit_timestamp_instead_of_propagating() -> None:
    # Confirmed against current MicroPython docs: mktime() genuinely raises OverflowError past
    # ~2037 on the rp2 port (32-bit signed epoch) - was called unguarded before this promotion, a
    # real crash risk for a device meant to run unattended for years.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(4, _synced, crc=CRC_Pass())
    assert chunk is not None

    class _OverflowingTime:
        # Patches the `time` name inside asy_fram_manager.py's own namespace, not the real
        # built-in `time` module (which doesn't support attribute assignment on this
        # interpreter) - the same "patch the name where it's looked up" technique already used
        # for asy_spi_driver._SPI above.
        @staticmethod
        def gmtime() -> tuple[int, ...]:
            return (2038, 1, 1, 0, 0, 0, 0, 1)

        @staticmethod
        def mktime(_t: tuple[int, ...]) -> int:
            raise OverflowError("simulated rp2 epoch overflow")

    original_time = asy_fram_manager.time
    asy_fram_manager.time = _OverflowingTime  # type: ignore[assignment]
    try:

        async def scenario() -> tuple[bool, int | None, bool]:
            return await chunk.write(b"data")

        ntp_synced, _utc, write_ok = run(scenario())
    finally:
        asy_fram_manager.time = original_time

    assert ntp_synced is False
    assert write_ok is True

    async def read_back() -> int | None:
        ts, _age, _data = await chunk.read()
        return ts

    assert run(read_back()) is None


def test_compare_with_huge_check_length_self_heals_instead_of_crashing() -> None:
    # _compare_with's `bytearray(self.check_length)` was unguarded against MemoryError/
    # OverflowError - check_length is a caller-supplied int, not hardware-bounded like the
    # allocation asy_fram_driver.py's own guard covers. Magnitude matches
    # tests/test_base_classes.py's own confirmed MemoryError boundary for bytearray(n).
    # The allocation failure makes _compare_with report block 1 as "not verifiably valid", which
    # _read() already treats like any other block-1 problem: heal it from block 0 rather than
    # failing the whole read - proving the fix integrates with existing self-healing, not just
    # that it avoids a crash.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass(), check_length=2**62)
    assert chunk is not None
    run(chunk.write(b"data"))

    async def scenario() -> bytearray | None:
        return await chunk.read()

    assert run(scenario()) == bytearray(b"data")  # no crash, and still recovers real data


def test_compare_with_zero_check_length_fails_cleanly_instead_of_hanging_forever() -> None:
    # Regression for a real bug found in review: _read_chunk's streaming loop computes
    # chunk_size = min(len(buf), total_size - position) - with check_length=0, len(buf) is
    # always 0, so chunk_size is always 0, position never advances, and the loop runs forever
    # (confirmed directly: it hung past a bounded wait before this fix). asyncio.wait_for here
    # means a real regression fails this test with a clear timeout, not a frozen test run.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass(), check_length=0)
    assert chunk is not None
    run(chunk.write(b"data"))

    async def scenario() -> bytearray | None:
        return await asyncio.wait_for(chunk.read(), timeout=5)

    assert run(scenario()) == bytearray(b"data")  # block 1 unverifiable -> healed from block 0


def test_compare_with_huge_check_length_during_write_verification_degrades_safely() -> None:
    # Same guard, exercised via _write()'s own verify path instead of _read()'s cross-check -
    # verify treats "couldn't verify" the same as "verification failed", so the write reports
    # False (real data was physically written, but that can't be confirmed) rather than crashing.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass(), check_length=2**62, verify=1)
    assert chunk is not None

    async def scenario() -> bool:
        return await chunk.write(b"data")

    assert run(scenario()) is False


def test_oversized_write_logs_errno_84_not_colliding_with_clears_errno_80() -> None:
    # AsyFramChunk.write's own "data too large" errno used to collide with
    # _AsyBaseFramChunk.clear()'s errno=80 - both log into the same shared PrintLogHistory
    # instance every chunk allocated from one manager shares, so the two failures were previously
    # indistinguishable in the error history.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass())
    assert chunk is not None

    async def scenario() -> dict:
        await chunk.write(b"toolong!")
        return await manager.get_error_counter()

    result = run(scenario())
    assert 84 in result["FRAM"]["ErrNum"]
    assert 80 not in result["FRAM"]["ErrNum"]


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
