import asyncio

from _fram_chip_fake import FakeMB85RS64V

import asy_fram_manager
import asy_spi_driver
from asy_fram_manager import AsyFramChunkBuffer, AsyFramManager
from asy_spi_driver import SPI
from crc_checks import CRC8, CRC16, CRC32, CRC_Pass

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

    async def scenario() -> tuple[bytearray | None, dict]:
        await chunk.write(b"good")
        addr0, _addr1 = chunk.block_addr
        # Simulate power loss mid-write: block 0 left with status BUSY (never reached the final
        # "set IDLE" step) - the same on-chip state a real torn write leaves behind.
        chip.memory[addr0 + 4] = _STATUS_BUSY
        chip.memory[addr0 + 5] = _STATUS_BUSY
        result = await chunk.read()
        errs = await manager.get_error_counter()
        return result, errs

    result, errs = run(scenario())
    assert result == bytearray(b"good")  # recovered from block 1
    assert 31 in errs["FRAM"]["ErrNum"]  # _set_check_sb: "Read status byte is not IDLE but X" (err=30+1)
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


# ---------------------------------------------------------------------------
# Chip-level fault injection - real FRAM_SPI failures (not direct memory pokes), exercised through
# tests/_fram_chip_fake.py's fault-injection knobs, down to the actual mocked chip behaviour.
# ---------------------------------------------------------------------------


def test_write_fails_cleanly_when_chip_drops_wren_latch() -> None:
    # drop_wren makes every fram.set_values() fail at the driver layer (WREN latch never sets,
    # asy_fram_driver.py's own _enable_write() check fails) - the first real (not memory-poked)
    # FRAM-level failure this suite exercises through the manager.
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass())
    assert chunk is not None
    chip.drop_wren = True

    async def scenario() -> tuple[bool, dict]:
        write_ok = await chunk.write(b"data")
        result = await manager.get_error_counter()
        return write_ok, result

    write_ok, result = run(scenario())
    errnums = result["FRAM"]["ErrNum"]
    assert write_ok is False
    assert 12 in errnums  # _set_check_sb: "Write status byte failed!" (busy status, err=10+2)
    assert 61 in errnums  # _write: "Writing block 0 failed!"


def test_read_fails_cleanly_when_chip_drops_wren_latch() -> None:
    # Reading also needs a real chip write (BUSY status before the read, IDLE after) - drop_wren
    # breaks that step for both blocks, so read() reports total failure instead of stale/no data.
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass())
    assert chunk is not None
    run(chunk.write(b"good"))
    chip.drop_wren = True

    async def scenario() -> tuple[bytearray | None, dict]:
        result = await chunk.read()
        errs = await manager.get_error_counter()
        return result, errs

    result, errs = run(scenario())
    errnums = errs["FRAM"]["ErrNum"]
    assert result is None
    assert errnums.count(32) == 2  # both blocks fail the same way (err=30+2, the read's own busy-set write)
    assert 72 in errnums  # "Invalid data in block 1" - neither copy usable


def test_clear_fails_cleanly_when_chip_drops_wren_latch() -> None:
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass())
    assert chunk is not None
    run(chunk.write(b"good"))
    chip.drop_wren = True

    async def scenario() -> tuple[bool, dict]:
        cleared = await chunk.clear()
        errs = await manager.get_error_counter()
        return cleared, errs

    cleared, errs = run(scenario())
    errnums = errs["FRAM"]["ErrNum"]
    assert cleared is False
    assert 52 in errnums  # err=50+2
    assert 80 in errnums


def test_write_fails_cleanly_when_fram_is_write_protected() -> None:
    # Same failure shape as the WREN-drop test, but via the driver's own write-protect check
    # (asy_fram_driver.py's _write()'s first guard) - a real, commonly used failure mode (write
    # protection is a supported driver feature), not just a simulated bus glitch.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass())
    assert chunk is not None

    async def scenario() -> tuple[bool, bool, dict]:
        protect_ok = await manager.fram.set_write_protected(True)
        write_ok = await chunk.write(b"data")
        errs = await manager.get_error_counter()
        return protect_ok, write_ok, errs

    protect_ok, write_ok, errs = run(scenario())
    errnums = errs["FRAM"]["ErrNum"]
    assert protect_ok is True
    assert write_ok is False
    assert 12 in errnums
    assert 61 in errnums


def test_operations_fail_cleanly_once_fram_chip_goes_uninitialized_mid_run() -> None:
    # Models a chip that stopped responding after a successful setup() - every FRAM_SPI call
    # short-circuits on its own `uninitialized` guard before ever touching the bus. Distinct from
    # the WREN-drop case: reads fail at the *read* step (errno 30) here since get_values() itself
    # refuses immediately, not just the subsequent status write (errno 32 for WREN-drop).
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass())
    assert chunk is not None
    run(chunk.write(b"good"))
    manager.fram.uninitialized = True

    async def scenario() -> tuple[bool, bytearray | None, bool, dict]:
        write_ok = await chunk.write(b"data")
        read_result = await chunk.read()
        cleared = await chunk.clear()
        errs = await manager.get_error_counter()
        return write_ok, read_result, cleared, errs

    write_ok, read_result, cleared, errs = run(scenario())
    errnums = errs["FRAM"]["ErrNum"]
    assert write_ok is False
    assert read_result is None
    assert cleared is False
    assert 30 in errnums  # read's own status-byte *read* fails immediately (vs. 32 for WREN-drop)


# ---------------------------------------------------------------------------
# Both-blocks-invalid and self-heal-write-failure paths - the remaining _read() branches this
# suite hadn't exercised yet
# ---------------------------------------------------------------------------


def test_read_fails_when_both_blocks_have_crc_invalid_payloads() -> None:
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8())
    assert chunk is not None
    run(chunk.write(b"good"))
    addr0, addr1 = chunk.block_addr
    chip.memory[addr0] ^= 0xFF
    chip.memory[addr1] ^= 0xFF

    async def scenario() -> tuple[bytearray | None, dict]:
        result = await chunk.read()
        errs = await manager.get_error_counter()
        return result, errs

    result, errs = run(scenario())
    errnums = errs["FRAM"]["ErrNum"]
    assert result is None
    assert errnums.count(46) == 2  # CRC error in _read_chunk, both blocks
    assert 72 in errnums  # "Invalid data in block 1" - none of the copies usable


def test_block1_invalid_while_block0_valid_self_heals_block1() -> None:
    # Mirror of the existing block-0-corruption self-heal test - this file only ever corrupted
    # block 0's payload directly; block 1 being the one that's wrong (block 0 fine) is a distinct
    # code path (_compare_with's cross-check inside _read()'s "block 0 already valid" branch, not
    # the "block 0 invalid" branch).
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8())
    assert chunk is not None
    run(chunk.write(b"good"))
    _addr0, addr1 = chunk.block_addr
    chip.memory[addr1] ^= 0xFF

    async def scenario() -> bytearray | None:
        return await chunk.read()

    assert run(scenario()) == bytearray(b"good")
    _addr0, addr1 = chunk.block_addr
    assert bytes(chip.memory[addr1 : addr1 + 4]) == b"good"  # block 1 healed


def test_read_fails_when_self_heal_write_to_block0_fails() -> None:
    # block 0 is invalid and needs healing from block 1; if that heal write itself fails (a real
    # FRAM write can fail independently of the read that triggered it), read() must still report
    # failure rather than pretend the stale/invalid block 0 is now fine. _write_chunk is patched
    # per-address rather than using write-protect, since write-protect would also block the
    # BUSY-status write every read needs just to start, masking this specific failure.
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8())
    assert chunk is not None
    run(chunk.write(b"good"))
    addr0, _addr1 = chunk.block_addr
    chip.memory[addr0] ^= 0xFF
    original_write_chunk = chunk._write_chunk

    async def failing_write_chunk(buf: bytearray, addr: int) -> bool:
        if addr == addr0:
            return False
        return await original_write_chunk(buf, addr)

    chunk._write_chunk = failing_write_chunk  # type: ignore[method-assign]

    async def scenario() -> tuple[bytearray | None, dict]:
        result = await chunk.read()
        errs = await manager.get_error_counter()
        return result, errs

    result, errs = run(scenario())
    errnums = errs["FRAM"]["ErrNum"]
    assert result is None
    assert 71 in errnums  # "Writing block 0 failed!" - the heal write itself


def test_read_fails_when_self_heal_write_to_block1_fails() -> None:
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8())
    assert chunk is not None
    run(chunk.write(b"good"))
    _addr0, addr1 = chunk.block_addr
    chip.memory[addr1] ^= 0xFF
    original_write_chunk = chunk._write_chunk

    async def failing_write_chunk(buf: bytearray, addr: int) -> bool:
        if addr == addr1:
            return False
        return await original_write_chunk(buf, addr)

    chunk._write_chunk = failing_write_chunk  # type: ignore[method-assign]

    async def scenario() -> tuple[bytearray | None, dict]:
        result = await chunk.read()
        errs = await manager.get_error_counter()
        return result, errs

    result, errs = run(scenario())
    errnums = errs["FRAM"]["ErrNum"]
    assert result is None
    assert 72 in errnums  # "Writing block 1 failed!" - the heal write itself


def test_read_into_rejects_a_buffer_of_the_wrong_size() -> None:
    # Mirror of the existing write_into size-mismatch test - _read()'s own errno=70 guard.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass())
    assert chunk is not None
    wrong_buf = AsyFramChunkBuffer(8, 0)  # this chunk expects 4 payload bytes, not 8

    async def scenario() -> bool:
        return await chunk.read_into(wrong_buf)

    assert run(scenario()) is False


def test_clear_while_paused_is_refused_without_override() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass())
    assert chunk is not None
    run(chunk.write(b"data"))
    manager.set_pause(True)

    async def scenario() -> tuple[bool, bytearray | None]:
        cleared = await chunk.clear()
        data = await chunk.read(override_pause=True)
        return cleared, data

    cleared, data = run(scenario())
    assert cleared is False
    assert data == bytearray(b"data")  # refused, original data intact


def test_clear_override_pause_bypasses_manager_pause() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass())
    assert chunk is not None
    run(chunk.write(b"data"))
    manager.set_pause(True)

    async def scenario() -> tuple[bool, bytearray | None]:
        cleared = await chunk.clear(override_pause=True)
        data = await chunk.read(override_pause=True)
        return cleared, data

    cleared, data = run(scenario())
    assert cleared is True
    assert data is None


# ---------------------------------------------------------------------------
# CRC width, check_length, and verify-counter configuration variety (cross-dependency with
# crc_checks.py's other concrete CRC widths, only CRC8/CRC_Pass exercised above)
# ---------------------------------------------------------------------------


def test_write_then_read_round_trip_with_crc16() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(5, crc=CRC16())
    assert chunk is not None
    assert chunk.block_addr == (0, 9)  # 5 data + 2 crc + 2 status per block

    async def scenario() -> bytearray | None:
        await chunk.write(b"hello")
        return await chunk.read()

    assert run(scenario()) == bytearray(b"hello")


def test_write_then_read_round_trip_with_crc32() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(5, crc=CRC32())
    assert chunk is not None
    assert chunk.block_addr == (0, 11)  # 5 data + 4 crc + 2 status per block

    async def scenario() -> bytearray | None:
        await chunk.write(b"world")
        return await chunk.read()

    assert run(scenario()) == bytearray(b"world")


def test_check_length_of_1_still_verifies_the_whole_chunk_across_many_iterations() -> None:
    # check_length only bounds how much _compare_with pulls per streaming iteration - the loop
    # keeps iterating until the whole chunk is covered, so a tiny check_length must still produce
    # a correct, fully-verified result, not a partial one.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(10, crc=CRC_Pass(), check_length=1, verify=1)
    assert chunk is not None

    async def scenario() -> tuple[bool, bytearray | None]:
        write_ok = await chunk.write(b"0123456789")
        data = await chunk.read()
        return write_ok, data

    write_ok, data = run(scenario())
    assert write_ok is True
    assert data == bytearray(b"0123456789")


def test_verify_counter_only_triggers_every_nth_write() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass(), verify=2)
    assert chunk is not None

    run(chunk.write(b"one!"))
    assert chunk.verify_counter == 1  # below threshold, no verification ran yet
    run(chunk.write(b"two!"))
    assert chunk.verify_counter == 0  # threshold hit, verification ran and counter reset


def test_get_chunk_allocation_succeeds_at_exact_remaining_capacity_boundary() -> None:
    manager, _chip = make_manager(max_size=12)
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass())  # full_size = 2*(4+0+2) = 12, exact fit
    assert chunk is not None
    assert manager.get_chunk(1) is None  # nothing left at all


# ---------------------------------------------------------------------------
# AsyFramTimestampedChunk shares _AsyBaseFramChunk behavior (inheritance) - pause/clear/verify
# were only ever exercised through AsyFramChunk above; confirm the shared base actually behaves
# the same way through the timestamped subclass too, not just by inheritance on paper.
# ---------------------------------------------------------------------------


def test_timestamped_chunk_clear_resets_to_reading_as_uninitialized() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(4, _synced, crc=CRC_Pass())
    assert chunk is not None
    run(chunk.write(b"data"))
    _ts, _age, data = run(chunk.read())
    assert data == bytearray(b"data")

    async def scenario() -> tuple[bool, tuple[int | None, int | None, bytearray | None]]:
        cleared = await chunk.clear()
        result = await chunk.read()
        return cleared, result

    cleared, result = run(scenario())
    assert cleared is True
    assert result == (None, None, None)


def test_timestamped_chunk_respects_manager_pause_and_override() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(4, _synced, crc=CRC_Pass())
    assert chunk is not None
    manager.set_pause(True)

    async def scenario() -> tuple[bool, tuple[int | None, int | None, bytearray | None]]:
        _ntp_synced, _utc, write_ok = await chunk.write(b"data")
        read_result = await chunk.read()
        return write_ok, read_result

    write_ok, read_result = run(scenario())
    assert write_ok is False  # _write's own pause guard refuses, same as AsyFramChunk
    assert read_result == (None, None, None)

    manager.set_pause(False)

    async def with_override() -> tuple[bool, tuple[int | None, int | None, bytearray | None]]:
        _ntp_synced, _utc, write_ok = await chunk.write(b"data", override_pause=True)
        result = await chunk.read(override_pause=True)
        return write_ok, result

    write_ok, result = run(with_override())
    assert write_ok is True
    assert result[2] == bytearray(b"data")


def test_timestamped_chunk_write_with_verify_enabled_succeeds() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(4, _synced, crc=CRC_Pass(), verify=1)
    assert chunk is not None

    async def scenario() -> bool:
        _ntp_synced, _utc, write_ok = await chunk.write(b"data")
        return write_ok

    assert run(scenario()) is True


# ---------------------------------------------------------------------------
# Unusual content - edge cases in what's actually stored, not just failure injection
# ---------------------------------------------------------------------------


def test_zero_size_chunk_documents_the_flagged_spurious_crc_error_on_read() -> None:
    # Locks down a known, deliberately-not-fixed quirk (see BACKLOG.md): a 0-byte chunk's CRC
    # engine never receives a single run_inc() call (_read_chunk's streaming loop's `while
    # position < total_size` never executes when total_size is 0), so check_inc() reports
    # "invalid" even though nothing was ever actually wrong - write() succeeds but read() then
    # reports failure. Confirmed directly against the real interpreter; this test locks down that
    # documented, discussed behavior so it can't silently change, not a new bug being introduced.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(0, crc=CRC_Pass())
    assert chunk is not None

    async def scenario() -> tuple[bool, bytearray | None]:
        write_ok = await chunk.write(b"")
        data = await chunk.read()
        return write_ok, data

    write_ok, data = run(scenario())
    assert write_ok is True
    assert data is None  # spurious CRC "error" on read - see BACKLOG.md, not fixed here


def test_all_zero_and_all_0xff_payloads_round_trip_without_sentinel_collision() -> None:
    # Payload content lives in a separate address range from the status bytes (_STATUS_UNINIT is
    # 0x00, one of the exact byte values a real payload might legitimately need to store) -
    # confirms there's no accidental confusion between "chunk never written" and "chunk holds
    # all-zero data".
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8())
    assert chunk is not None

    async def scenario() -> tuple[bytearray | None, bytearray | None]:
        await chunk.write(b"\x00\x00\x00\x00")
        zeros = await chunk.read()
        await chunk.write(b"\xff\xff\xff\xff")
        ones = await chunk.read()
        return zeros, ones

    zeros, ones = run(scenario())
    assert zeros == bytearray(b"\x00\x00\x00\x00")
    assert ones == bytearray(b"\xff\xff\xff\xff")


def test_epoch_zero_timestamp_reads_back_as_uninitialized_sentinel_collision() -> None:
    # _TS_UNINIT (0) doubles as both "never written" and the literal Unix epoch - a real UTC
    # timestamp of exactly 0 is indistinguishable from "uninitialized" on read. Confirmed via a
    # direct interpreter test, not fixed here (inherited from the original deployed design, not
    # introduced by this promotion) - locks down the collision as real, documented behavior.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(4, _synced, crc=CRC_Pass())
    assert chunk is not None

    class _EpochZeroTime:
        @staticmethod
        def gmtime() -> tuple[int, ...]:
            return (1970, 1, 1, 0, 0, 0, 0, 1)

        @staticmethod
        def mktime(_t: tuple[int, ...]) -> int:
            return 0

    original_time = asy_fram_manager.time
    asy_fram_manager.time = _EpochZeroTime  # type: ignore[assignment]
    try:

        async def scenario() -> tuple[bool, int | None, bool]:
            return await chunk.write(b"data")

        ntp_synced, utc, write_ok = run(scenario())
    finally:
        asy_fram_manager.time = original_time

    assert ntp_synced is True
    assert utc == 0
    assert write_ok is True

    async def read_back() -> int | None:
        ts, _age, _data = await chunk.read()
        return ts

    assert run(read_back()) is None  # collides with the "never written" sentinel


# ---------------------------------------------------------------------------
# Deliberately-allowed exceptions propagating through this file's own composition points -
# confirms the "caught here" / "allowed to raise" boundary asy_fram_driver.py's own docstring
# documents actually holds one layer up, through AsyFramManager's public API, not just in
# asy_fram_driver.py's own already-thorough test suite in isolation.
# ---------------------------------------------------------------------------


def test_construction_raises_uncaught_valueerror_for_an_out_of_range_spi_cs() -> None:
    # AsyFramManager.__init__ constructs FRAM_SPI(...) with no try/except around it - a bad
    # spi_cs is a one-time, at-boot misconfiguration allowed to raise loudly rather than silently
    # produce a permanently nonfunctional manager (asy_fram_driver.py's own already-tested
    # carve-out, confirmed here to still hold through this file's own constructor).
    bus = make_bus()
    try:
        AsyFramManager(bus, 99, max_size=0x2000)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_setup_fails_cleanly_when_device_id_does_not_match() -> None:
    # Real device-not-found path (asy_fram_driver.py's FRAM_SPI.setup() raises OSError) - caught
    # by AsyFramManager.setup()'s own try/except, turned into a clean False + errno=83, not left
    # to propagate. A different, driver-owned RDID mismatch, not a caller misconfiguration.
    manager, chip = make_manager()
    chip.rdid_response = bytes([0xFF, 0xFF, 0xFF, 0xFF])

    async def scenario() -> tuple[bool, dict]:
        ok = await manager.setup()
        errs = await manager.get_error_counter()
        return ok, errs

    ok, errs = run(scenario())
    assert ok is False
    assert 83 in errs["FRAM"]["ErrNum"]


def test_chunk_operations_fail_cleanly_when_the_underlying_bus_is_deinitialized_mid_run() -> None:
    # asy_spi_driver.py's own contract says a mid-operation bus deinit raises an uncaught
    # RuntimeError at that layer (asy_fram_driver.py's own test suite already proves this in
    # isolation) - this confirms the *other* half of that same contract: one layer up, this
    # file's broad `except Exception` in _write_chunk/_read_chunk/_clear_chunk catches it cleanly,
    # rather than letting it propagate out of AsyFramChunk's own public write()/read()/clear().
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass())
    assert chunk is not None
    run(chunk.write(b"good"))
    manager.fram._spidev.spi.deinit()

    async def scenario() -> tuple[bool, bytearray | None, bool, dict]:
        write_ok = await chunk.write(b"data")
        read_result = await chunk.read()
        cleared = await chunk.clear()
        errs = await manager.get_error_counter()
        return write_ok, read_result, cleared, errs

    write_ok, read_result, cleared, errs = run(scenario())
    errnums = errs["FRAM"]["ErrNum"]
    assert write_ok is False
    assert read_result is None
    assert cleared is False
    assert 26 in errnums  # "General write error in _write_chunk:" - the caught RuntimeError
    assert 47 in errnums  # "General read error in _read_chunk:"
    assert 58 in errnums  # "General write error in _clear_chunk:"


# ---------------------------------------------------------------------------
# Configuration edge values - within-type but unusual/invalid inputs (negative, zero, huge),
# single and combined, staying inside every parameter's declared int type throughout.
# ---------------------------------------------------------------------------


def test_get_chunk_negative_size_degrades_to_an_unusable_but_non_crashing_chunk() -> None:
    # A negative size flows straight into AsyFramChunkBuffer/LockableBuffer, whose own guard
    # (base_classes.py) already turns any negative size into buf=None - confirmed here at this
    # file's own boundary that the degradation is clean end to end, not just at that lower layer.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(-4, crc=CRC_Pass())
    assert chunk is not None  # allocation bookkeeping itself doesn't reject a negative size

    async def scenario() -> tuple[bool, bytearray | None]:
        write_ok = await chunk.write(b"data")
        data = await chunk.read()
        return write_ok, data

    write_ok, data = run(scenario())
    assert write_ok is False
    assert data is None


def test_get_chunk_negative_verify_triggers_verification_on_every_single_write() -> None:
    # Surprising but harmless: verify_counter starts at 0 and is compared with `>=` against
    # `verify` *after* incrementing - a negative verify makes that comparison (1 >= negative) true
    # on the very first write, so verification runs (and the counter resets to 0) every time,
    # unlike verify=0 (never verifies) or verify=N>0 (every Nth write). Locked down as real,
    # non-crashing, if unusual, behavior - not something this pass changes.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass(), verify=-5)
    assert chunk is not None

    async def scenario() -> bool:
        return await chunk.write(b"data")

    assert run(scenario()) is True
    assert chunk.verify_counter == 0  # verification ran and reset the counter, not left at 1


def test_get_chunk_negative_check_length_self_heals_instead_of_crashing() -> None:
    # Same MemoryError-degrades-to-"not verifiably valid" guard as the huge-check_length
    # regression test, reached via a different input class: bytearray(negative_int) raises
    # MemoryError on this interpreter (confirmed directly - the negative count gets reinterpreted
    # as a huge unsigned allocation request), not a distinct crash mode of its own.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass(), check_length=-1)
    assert chunk is not None
    run(chunk.write(b"data"))

    async def scenario() -> bytearray | None:
        return await chunk.read()

    assert run(scenario()) == bytearray(b"data")


def test_manager_negative_max_size_degrades_to_always_out_of_memory() -> None:
    manager, _chip = make_manager(max_size=-100)
    assert manager.get_chunk(4) is None
    assert manager.get_timestamped_chunk(4, _synced) is None


def test_multiple_invalid_parameters_combined_still_degrade_safely() -> None:
    # negative size + negative verify + negative check_length together, all in one chunk - none
    # of these interact to produce anything worse than each one's own individual degradation.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(-4, crc=CRC_Pass(), verify=-1, check_length=-1)
    assert chunk is not None

    async def scenario() -> tuple[bool, bytearray | None]:
        write_ok = await chunk.write(b"data")
        data = await chunk.read()
        return write_ok, data

    write_ok, data = run(scenario())
    assert write_ok is False
    assert data is None


# ---------------------------------------------------------------------------
# Fresh-eyes re-audit: previously-unreached status-byte/verify branches, and a genuinely
# unplanned concurrency condition found by construction, not by inspection alone.
# ---------------------------------------------------------------------------


def test_disagreeing_status_bytes_within_one_block_are_treated_as_invalid_and_self_healed() -> None:
    # _handle_status_bytes checks its two status bytes' "uninit" results *agree* before trusting
    # either - status byte 1 = UNINIT and status byte 2 = IDLE are each individually a normal,
    # valid value on their own (neither triggers the "not idle, not uninit" errno=31 path), but
    # disagreeing with each other is its own distinct failure the base/errno=31 checks can't
    # catch - only reachable via _read_chunk's initial busy-set step (check_idle=True is the only
    # call site where the "uninit" flag isn't hardcoded False), confirmed empirically, previously
    # completely untested.
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass())
    assert chunk is not None
    run(chunk.write(b"good"))
    addr0, _addr1 = chunk.block_addr
    chip.memory[addr0 + 4] = _STATUS_UNINIT
    chip.memory[addr0 + 5] = _STATUS_IDLE

    async def scenario() -> tuple[bytearray | None, dict]:
        result = await chunk.read()
        errs = await manager.get_error_counter()
        return result, errs

    result, errs = run(scenario())
    assert result == bytearray(b"good")  # falls back to block 1 and self-heals, like any other invalid block 0
    assert 36 in errs["FRAM"]["ErrNum"]  # _handle_status_bytes: "Read status uninit bytes inconsistent!" (30+6)


def test_write_verify_reports_the_distinct_errno_when_only_block_1_fails_verification() -> None:
    # The verify loop's `errno=63+n` was only ever exercised for n=0 (block 0 failing first always
    # short-circuits the loop before n=1 is tried) - isolating block 1's own verification failure
    # needs a per-address patch, the same technique already used for the self-heal-write-failure
    # tests, since block 0 must genuinely succeed for the loop to ever reach n=1 at all.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass(), verify=1)
    assert chunk is not None
    _addr0, addr1 = chunk.block_addr
    original_compare_with = chunk._compare_with

    async def failing_compare_with(buf: bytearray, addr: int) -> tuple[bool, bool, bool]:
        if addr == addr1:
            return False, False, False
        return await original_compare_with(buf, addr)

    chunk._compare_with = failing_compare_with  # type: ignore[method-assign]

    async def scenario() -> tuple[bool, dict]:
        write_ok = await chunk.write(b"data")
        errs = await manager.get_error_counter()
        return write_ok, errs

    write_ok, errs = run(scenario())
    assert write_ok is False
    assert 64 in errs["FRAM"]["ErrNum"]  # "Block 1 write verification error!" (63+1), not 63


def test_concurrent_writes_to_the_same_chunk_never_produce_silently_corrupted_data() -> None:
    # A genuinely unplanned condition found by construction, not by inspection: _write() only
    # holds fram's lock separately for each block (_write_chunk acquires/releases it once per
    # block), not continuously across the whole logical write - so two tasks writing the same
    # chunk concurrently can interleave *between* blocks, each reporting success, while leaving
    # one task's data in block 0 and the other's in block 1. Deterministically forced here via an
    # asyncio.Event handshake (natural scheduling in a plain asyncio.gather() doesn't reliably
    # interleave at this exact boundary - confirmed directly, it usually just doesn't race) rather
    # than hoping a race manifests on its own. The point isn't that this is "fixed" - concurrent
    # writers to one chunk were never a designed-for use case - it's that the existing CRC/dual-copy
    # hard-fail safety net (the same "both blocks valid but different data" path already tested
    # for the single-writer torn-write case) catches the inconsistency cleanly: a subsequent read
    # never returns silently mixed/wrong bytes, only a clean payload or a safe None.
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8())
    assert chunk is not None
    addr0, addr1 = chunk.block_addr
    original_write_chunk = chunk._write_chunk

    block0_written = asyncio.Event()
    let_a_finish = asyncio.Event()

    async def a_patched_write_chunk(buf: bytearray, addr: int) -> bool:
        res = await original_write_chunk(buf, addr)
        if addr == addr0:
            block0_written.set()
            await let_a_finish.wait()  # pause task A right between its own block 0 and block 1 writes
        return res

    async def writer_a() -> bool:
        chunk._write_chunk = a_patched_write_chunk  # type: ignore[method-assign]
        return await chunk.write(b"AAAA")

    async def writer_b() -> bool:
        await block0_written.wait()  # let A finish block 0 first
        chunk._write_chunk = original_write_chunk  # type: ignore[method-assign]
        ok = await chunk.write(b"BBBB")  # B fully completes both of its own blocks
        let_a_finish.set()  # now let A resume and finish its own block 1 write, last
        return ok

    async def scenario() -> tuple[list[bool], bytearray | None]:
        results = await asyncio.gather(writer_a(), writer_b())
        read_result = await chunk.read()
        return results, read_result

    results, read_result = run(scenario())
    assert results == [True, True]  # neither individual write call can see the other's interference
    assert bytes(chip.memory[addr0 : addr0 + 4]) == b"BBBB"  # proves the interleave actually happened
    assert bytes(chip.memory[addr1 : addr1 + 4]) == b"AAAA"
    assert read_result is None  # the safety net refuses to guess, never returns a mixed/wrong payload


def test_manager_setup_is_idempotent_when_called_twice() -> None:
    manager, _chip = make_manager()
    ok1 = run(manager.setup())
    ok2 = run(manager.setup())
    assert ok1 is True
    assert ok2 is True
    chunk = manager.get_chunk(4, crc=CRC_Pass())
    assert chunk is not None

    async def scenario() -> tuple[bool, bytearray | None]:
        write_ok = await chunk.write(b"data")
        data = await chunk.read()
        return write_ok, data

    write_ok, data = run(scenario())
    assert write_ok is True
    assert data == bytearray(b"data")


def test_get_chunk_zero_size_still_needs_status_byte_overhead_at_the_capacity_boundary() -> None:
    # Even a 0-byte payload chunk needs 2*_NUM_STATUS_BYTES=4 bytes of real overhead - a manager
    # with genuinely zero bytes left must refuse a size=0 request too, not special-case it as free.
    manager, _chip = make_manager(max_size=12)
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC_Pass())  # exact fit, uses all 12 bytes
    assert chunk is not None
    assert manager.get_chunk(0, crc=CRC_Pass()) is None


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
