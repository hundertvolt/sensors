import asyncio

from _error_codes import code
from _fram_chip_fake import FakeMB85RS64V

import asy_base_classes
import asy_fram_manager
import asy_spi_driver
from asy_crc_checks import CRC8, CRC16, CRC32, CRCPass
from asy_fram_manager import FRAMChunk, FRAMChunkBuffer, FRAMChunkTimestampedBuffer, FRAMManager
from asy_print_log import LogConfig, PrintLogHistory, PrintLogHistoryStore
from asy_spi_driver import SPI

# Same one-process-per-test-file swap as test_asy_fram_driver.py - see its own comment.
asy_spi_driver._SPI = FakeMB85RS64V  # type: ignore[misc]

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine
    from typing import Any, TypeVar

    from asy_crc_checks import CRCBase

    T = TypeVar("T")
    from asy_print_log import ErrorLog

# Real on-chip constant values (asy_fram_manager.py's own _STATUS_* are micropython.const() and
# compiled away - not importable - so these are hardcoded, matching test_asy_fram_driver.py's own
# convention of hardcoding raw wire-level values rather than importing driver internals).
_STATUS_UNINIT = 0x00
_STATUS_IDLE = 0x01
_STATUS_BUSY = 0x02

# A status bit no real set_values_sync()/get_values_sync() return uses, so an injected failure
# is distinguishable from every genuine one - see fail_set_values_at() below.
_INJECTED_FAILURE = 1 << 20


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


# @tunable l1.asy_fram_manager_read_wait_s = 5
_READ_WAIT_S = 5


def make_bus() -> SPI:
    return SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)


def make_manager(max_size: int = 0x2000, history_length: int = 10) -> tuple[FRAMManager, FakeMB85RS64V]:
    bus = make_bus()
    manager = FRAMManager(bus, 1, max_size=max_size, log=LogConfig(None, history_length, None))
    chip = manager.fram._spidev.spi._spi
    assert isinstance(chip, FakeMB85RS64V)
    return manager, chip


async def setup_manager(manager: FRAMManager) -> bool:
    return await manager.setup()


async def _synced() -> bool:
    return True


async def _not_synced() -> bool:
    return False


async def _raising_callback() -> bool:
    raise RuntimeError("ntp callback exploded")


class _UTCValid:
    # The NTP client's first clock set of the boot, as utc_now() sees it, undone on exit.
    def __enter__(self) -> "_UTCValid":
        asy_base_classes.set_utc_valid()
        return self

    def __exit__(self, *_exc: object) -> None:
        asy_base_classes.set_utc_valid(valid=False)


# ---------------------------------------------------------------------------
# Construction - the manager's own RAM-only log, and chunks bound to their manager
# ---------------------------------------------------------------------------


def test_the_manager_logs_ram_only_whatever_its_log_config_names() -> None:
    # The one module that never logs into FRAM is the FRAM module itself: log.fram is ignored,
    # its length and level are taken.
    other, _chip = make_manager()
    manager = FRAMManager(make_bus(), 1, max_size=0x2000, log=LogConfig(other, 4, 2))
    assert type(manager.pr) is PrintLogHistory
    assert manager.pr.name == "FRAM"
    assert len(manager.pr.history) == 4
    assert manager.pr.level == 2


def test_a_chunk_takes_its_fram_logger_and_pause_from_its_manager() -> None:
    manager, _chip = make_manager()
    chunk = manager.get_chunk(4, owner="T1")
    ts_chunk = manager.get_timestamped_chunk(4, _synced, owner="T2")
    assert chunk is not None
    assert ts_chunk is not None
    for c in (chunk, ts_chunk):
        assert c.fram is manager.fram
        assert c.pr is manager.pr
        assert c._mempause() is False
    manager.set_pause(value=True)
    assert chunk._mempause() is True
    assert ts_chunk._mempause() is True


def test_every_chunk_and_the_driver_log_into_the_managers_ram_history() -> None:
    # Guard: a FRAM-backed history here would write through FRAM from inside the driver lock the chunk
    # layer holds, and deadlock on it; so the chunks and the driver share the manager's RAM history.
    manager, _chip = make_manager()
    chunk = manager.get_chunk(4, owner="T1")
    ts_chunk = manager.get_timestamped_chunk(4, _synced, owner="T2")
    assert chunk is not None and ts_chunk is not None
    assert type(manager.pr) is PrintLogHistory
    assert manager.fram.pr is manager.pr
    assert chunk.pr is manager.pr
    assert ts_chunk.pr is manager.pr


# ---------------------------------------------------------------------------
# Allocator - bump-pointer offsets, the static-layout invariant the whole file relies on
# ---------------------------------------------------------------------------


def test_get_chunk_sequential_allocation_offsets_match_bump_pointer_math() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk1 = manager.get_chunk(4, owner="T1")  # default crc is CRCPass, length 0
    chunk2 = manager.get_chunk(8, owner="T2")
    assert chunk1 is not None and chunk2 is not None
    # _block_addr[1] is where block 1 (the 2nd redundant copy) starts within the chunk, not the
    # end of the chunk's whole 2-block allocation - that end is base_addr + full_size (2*block).
    assert chunk1._block_addr == (0, 6)  # block 0 at [0,6), block 1 at [6,12) - 4 data+0 crc+2 status each
    assert chunk2._block_addr == (12, 22)  # starts at chunk1's full 2*(4+0+2)=12; block length 8+0+2=10


def test_allocation_order_not_chunk_size_determines_offsets() -> None:
    # Whichever get_chunk()/get_timestamped_chunk() call happens first claims the lower offset regardless of
    # size, which is why call order must be fixed within one build.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    small_first = manager.get_chunk(2, owner="T1")
    big_second = manager.get_chunk(50, owner="T2")
    assert small_first is not None and big_second is not None
    assert small_first._block_addr[0] < big_second._block_addr[0]
    # small_first's own full 2-block span ends at _block_addr[1] + one block's length (block 1
    # starts at _block_addr[1] and is the same length as block 0, i.e. _block_addr[1]-_block_addr[0]).
    small_first_end = small_first._block_addr[1] + (small_first._block_addr[1] - small_first._block_addr[0])
    assert big_second._block_addr[0] == small_first_end  # immediately follows, no gap


def test_get_chunk_returns_none_when_request_exceeds_remaining_capacity() -> None:
    manager, _chip = make_manager(max_size=16)
    run(setup_manager(manager))
    assert manager.get_chunk(100, owner="T1") is None


def test_get_timestamped_chunk_size_includes_the_8_byte_timestamp() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(4, _synced, owner="T1")
    assert chunk is not None
    assert chunk._block_addr == (0, 4 + 8 + 0 + 2)  # size(4) + ts(8) + crc(0) + status(2) = 14


def test_owner_seeds_are_nonzero_and_differ_by_owner() -> None:
    for crc, all_set in ((CRC8(), 0xFF), (CRC16(), 0xFFFF), (CRC32(), 0xFFFF)):
        first = asy_fram_manager._owner_seed("SYSTEM", crc)
        second = asy_fram_manager._owner_seed("NTP", crc)
        assert first != second
        for seed in (first, second):
            assert 0 < seed < all_set  # never zero, never the unseeded all-ones register


def _owner_layout(chip: FakeMB85RS64V, owners: "list[str]", crc_class: "Callable[[], CRCBase]") -> "list[FRAMChunk]":
    # One build's layout: equal-size chunks in owner order on a fresh manager over a copy of chip's bytes.
    manager, fresh = make_manager()
    fresh.memory[:] = chip.memory
    run(setup_manager(manager))
    chunks = [manager.get_chunk(6, crc=crc_class(), owner=owner) for owner in owners]
    assert all(chunk is not None for chunk in chunks)
    return [chunk for chunk in chunks if chunk is not None]


def test_a_chunk_written_by_another_owner_reads_blank() -> None:
    # A reflash that drops the first owner shifts every later chunk by exactly one chunk span onto its
    # neighbour's bytes: each must fail its owner-seeded CRC, never load the neighbour's history.
    owners = ["WIFI", "NTP", "SYSTEM"]
    for crc_class in (CRC8, CRC16):
        seeds = [asy_fram_manager._owner_seed(owner, crc_class()) for owner in owners]
        assert len(set(seeds)) == len(owners)
        _manager, chip = make_manager()
        first = _owner_layout(chip, owners, crc_class)
        image = first[0].fram._spidev.spi._spi
        assert isinstance(image, FakeMB85RS64V)
        for n, chunk in enumerate(first):
            assert run(chunk.write(bytes([0x41 + n]) * 6)) is True
        shifted = _owner_layout(image, owners[1:], crc_class)
        for chunk in shifted:
            assert run(chunk.read_into(chunk.get_buffer())) is False
            assert run(chunk.write(b"fresh!")) is True
            assert run(chunk.read()) == bytearray(b"fresh!")
        control = _owner_layout(image, owners, crc_class)
        for n, chunk in enumerate(control):
            assert run(chunk.read()) == bytearray(bytes([0x41 + n]) * 6)


# ---------------------------------------------------------------------------
# Basic write/read round trip and size-mismatch guards
# ---------------------------------------------------------------------------


def test_read_before_any_write_returns_none() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8(), owner="T1")
    assert chunk is not None

    async def scenario() -> bytearray | None:
        return await chunk.read()

    assert run(scenario()) is None


def test_write_then_read_round_trip_no_crc() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(5, crc=CRCPass(), owner="T1")
    assert chunk is not None

    async def scenario() -> bytearray | None:
        await chunk.write(b"hello")
        return await chunk.read()

    assert run(scenario()) == bytearray(b"hello")


def test_write_then_read_round_trip_with_crc8() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(5, crc=CRC8(), owner="T1")
    assert chunk is not None

    async def scenario() -> bytearray | None:
        await chunk.write(b"world")
        return await chunk.read()

    assert run(scenario()) == bytearray(b"world")


def test_write_rejects_data_larger_than_chunk_size() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None

    async def scenario() -> bool:
        return await chunk.write(b"toolong!")

    assert run(scenario()) is False


def test_write_into_rejects_a_buffer_of_the_wrong_size() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None
    wrong_buf = FRAMChunkBuffer(8, 0)  # this chunk expects 4 payload bytes, not 8

    async def scenario() -> bool:
        return await chunk.write_into(wrong_buf)

    assert run(scenario()) is False


def test_preallocated_buffer_write_into_read_into_round_trip() -> None:
    # The "ad hoc vs. preallocated" top-level interface: write_into()/read_into() let a caller
    # reuse one buffer across calls via get_buffer(), instead of write()/read()'s own
    # fresh-allocation-per-call convenience wrapper.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8(), owner="T1")
    assert chunk is not None
    buf = chunk.get_buffer()
    databuf = buf.get_data_buf()
    assert databuf is not None
    databuf[:] = b"data"

    async def scenario() -> tuple[bool, bool | None, bytearray | None]:
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
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None

    async def scenario() -> "tuple[bytearray | None, ErrorLog]":
        await chunk.write(b"good")
        addr0, _addr1 = chunk._block_addr
        # Simulate power loss mid-write: block 0 left with status BUSY (never reached the final
        # "set IDLE" step) - the same on-chip state a real torn write leaves behind.
        chip.memory[addr0 + 4] = _STATUS_BUSY
        chip.memory[addr0 + 5] = _STATUS_BUSY
        result = await chunk.read()
        errs = await manager.get_error_counter()
        return result, errs

    result, errs = run(scenario())
    assert result == bytearray(b"good")  # recovered from block 1
    assert code("E", "FRAM_STATUS_BYTE") in errs["FRAM"]["ErrNum"]  # _set_check_sb: "Read status byte is not IDLE but X"
    addr0, _addr1 = chunk._block_addr
    assert chip.memory[addr0 + 4] == _STATUS_IDLE  # block 0 healed back to IDLE...
    assert bytes(chip.memory[addr0 : addr0 + 4]) == b"good"  # ...with the correct data


def test_corrupted_block1_status_leaves_block0_valid_and_self_heals_block1() -> None:
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None

    async def scenario() -> bytearray | None:
        await chunk.write(b"good")
        _addr0, addr1 = chunk._block_addr
        chip.memory[addr1 + 4] = _STATUS_BUSY
        chip.memory[addr1 + 5] = _STATUS_BUSY
        return await chunk.read()

    result = run(scenario())
    assert result == bytearray(b"good")
    _addr0, addr1 = chunk._block_addr
    assert chip.memory[addr1 + 4] == _STATUS_IDLE
    assert bytes(chip.memory[addr1 : addr1 + 4]) == b"good"


def test_status_byte_holding_an_unrecognized_garbage_value_is_treated_the_same_as_busy() -> None:
    # _set_check_sb's read-side check is only ever `!= IDLE` then `!= UNINIT` (_STATUS_BUSY is
    # written, never compared on read), so an arbitrary corrupted byte must take the same
    # "invalid, self-heal" path as a real torn-write BUSY rather than a separate failure mode.
    garbage = 0x7A  # deliberately not _STATUS_UNINIT/_STATUS_IDLE/_STATUS_BUSY
    assert garbage not in (_STATUS_UNINIT, _STATUS_IDLE, _STATUS_BUSY)
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None
    run(chunk.write(b"good"))
    addr0, _addr1 = chunk._block_addr
    chip.memory[addr0 + 4] = garbage
    chip.memory[addr0 + 5] = garbage

    async def scenario() -> "tuple[bytearray | None, ErrorLog]":
        result = await chunk.read()
        errs = await manager.get_error_counter()
        return result, errs

    result, errs = run(scenario())
    assert result == bytearray(b"good")  # recovered from block 1, same as the BUSY case
    assert code("E", "FRAM_STATUS_BYTE") in errs["FRAM"]["ErrNum"]  # same code the BUSY case produces - no special-casing
    assert chip.memory[addr0 + 4] == _STATUS_IDLE  # healed back to a real, recognized state


def test_crc8_detects_corrupted_payload_byte_and_falls_back_to_other_block() -> None:
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8(), owner="T1")
    assert chunk is not None

    async def scenario() -> bytearray | None:
        await chunk.write(b"good")
        addr0, _addr1 = chunk._block_addr
        # Flip a payload byte directly on the "chip", bypassing the driver entirely - raw SPI has
        # no way to detect this (see test_asy_fram_driver.py); this is exactly the corruption
        # class CRC8 + dual-copy redundancy exist to catch one layer up.
        chip.memory[addr0] ^= 0xFF
        return await chunk.read()

    assert run(scenario()) == bytearray(b"good")  # recovered from block 1, CRC caught block 0


def test_crc8_detects_corrupted_trailer_byte_itself_not_just_payload() -> None:
    # Every other CRC fault-injection test flips a payload byte - this flips the CRC's own on-chip
    # trailer byte (stored right after the payload, before the status bytes) instead, to prove the
    # checksum genuinely covers its own storage, not only the data it protects.
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8(), owner="T1")
    assert chunk is not None
    run(chunk.write(b"good"))
    addr0, _addr1 = chunk._block_addr
    crc_byte_addr = addr0 + chunk.size + chunk.crc.length() - 1  # the trailer byte itself
    chip.memory[crc_byte_addr] ^= 0xFF

    async def scenario() -> "tuple[bytearray | None, ErrorLog]":
        result = await chunk.read()
        errs = await manager.get_error_counter()
        return result, errs

    result, errs = run(scenario())
    assert result == bytearray(b"good")  # recovered from block 1
    assert code("E", "FRAM_DATA_CRC") in errs["FRAM"]["ErrNum"]  # _read_chunk: "CRC error in _read_chunk!" - same path as payload corruption


def test_read_reports_failure_when_both_blocks_valid_but_hold_different_data() -> None:
    # A write torn between block 0 and block 1: both blocks valid (CRC_Pass, both status bytes IDLE) but
    # different, and no generation counter says which is right, so the read fails rather than guesses
    # (owner, 2026-07-18).
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None
    addr0, addr1 = chunk._block_addr
    chip.memory[addr0 : addr0 + 4] = b"AAAA"
    chip.memory[addr0 + 4] = _STATUS_IDLE
    chip.memory[addr0 + 5] = _STATUS_IDLE
    chip.memory[addr1 : addr1 + 4] = b"BBBB"
    chip.memory[addr1 + 4] = _STATUS_IDLE
    chip.memory[addr1 + 5] = _STATUS_IDLE

    async def scenario() -> "tuple[bool | None, ErrorLog]":
        result = await chunk.read_into(chunk.get_buffer())
        return result, await manager.get_error_counter()

    result, errs = run(scenario())
    assert result is False  # read, and no copy usable
    assert _entries(errs) == [(code("E", "FRAM_COPIES_DIFFER"), "E")]


def test_a_never_written_chunk_read_twice_reports_uninitialised_both_times() -> None:
    # A blank block is never read, so it takes no busy marker and stays blank: the second read finds the
    # same blank chunk as the first, and so does a read after clear().
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8(), owner="T1")
    assert chunk is not None
    status = [addr + chunk.size + chunk.crc.length() for addr in chunk._block_addr]

    def blank_twice() -> None:
        for _read in range(2):
            assert run(chunk.read_into(chunk.get_buffer())) is False
            for addr in status:
                assert bytes(chip.memory[addr : addr + 2]) == b"\x00\x00"
        assert run(manager.get_error_counter())["FRAM"]["ErrCount"] == 0

    blank_twice()
    assert run(chunk.write(b"data")) is True
    assert run(chunk.clear()) is True
    blank_twice()


def test_read_into_is_tri_state() -> None:
    # True: valid data. False: read, and no copy usable (blank, or both invalid). None: not read (a fault
    # on a block with no valid copy beside it, or a failed repair write); the stored bytes are left as they are.
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None
    addr0, addr1 = chunk._block_addr

    def read() -> bool | None:
        return run(chunk.read_into(chunk.get_buffer()))

    assert read() is False  # blank
    assert run(chunk.write(b"good")) is True
    assert read() is True
    chip.memory[addr0 + 4] = 0x7F  # a status byte neither idle nor blank, on both blocks
    chip.memory[addr1 + 4] = 0x7F
    assert read() is False
    assert run(chunk.write(b"good")) is True
    chip.memory[addr0 + 4] = _STATUS_BUSY  # block 0 invalid, and its repair write fails
    fail_set_values_at(chunk, addr0 + 4)
    assert read() is None
    manager.fram.initialized = False  # the driver refuses every transfer: both blocks fault
    assert read() is None
    manager.fram.initialized = True
    assert bytes(chip.memory[addr1 : addr1 + 4]) == b"good"


def test_a_planted_fault_leaves_an_entry_at_every_layer_it_reaches() -> None:
    # One operation per fault: the detecting layer's entry first, then each layer it propagates
    # through adds its own, so the history shows how far the fault reached (owner, 2026-10-02).
    def entries_after(plant: "Callable[[FRAMManager, FakeMB85RS64V, FRAMChunk], None]", operation: str, crc: "CRCBase") -> "list[tuple[int, str]]":
        manager, chip = make_manager()
        run(setup_manager(manager))
        chunk = manager.get_chunk(4, crc=crc, owner="T1")
        assert chunk is not None
        assert run(chunk.write(b"good")) is True
        plant(manager, chip, chunk)
        if operation == "write":
            run(chunk.write(b"else"))
        else:
            run(chunk.read())
        return _entries(run(manager.get_error_counter()))

    def not_initialised(manager: FRAMManager, _chip: FakeMB85RS64V, _chunk: FRAMChunk) -> None:
        manager.fram.initialized = False

    def wel_not_set(_manager: FRAMManager, chip: FakeMB85RS64V, _chunk: FRAMChunk) -> None:
        chip.drop_wren = True

    def busy_block_0(_manager: FRAMManager, chip: FakeMB85RS64V, chunk: FRAMChunk) -> None:
        status = chunk._block_addr[0] + chunk.size + chunk.crc.length()
        chip.memory[status] = _STATUS_BUSY
        chip.memory[status + 1] = _STATUS_BUSY

    def crc_block_0(_manager: FRAMManager, chip: FakeMB85RS64V, chunk: FRAMChunk) -> None:
        chip.memory[chunk._block_addr[0]] ^= 0xFF

    def crc_both(_manager: FRAMManager, chip: FakeMB85RS64V, chunk: FRAMChunk) -> None:
        for addr in chunk._block_addr:
            chip.memory[addr] ^= 0xFF

    def e_(name: str) -> "tuple[int, str]":
        return code("E", name), "E"

    invalid = (code("W", "FRAM_BLOCK_INVALID"), "W")
    assert entries_after(not_initialised, "write", CRCPass()) == [e_("NOT_INIT"), e_("FRAM_STATUS_WRITE"), e_("FRAM_BLOCK_WRITE")]
    assert entries_after(wel_not_set, "write", CRCPass()) == [(code("W", "FRAM_WEL_NOT_SET"), "W"), e_("FRAM_STATUS_WRITE"), e_("FRAM_BLOCK_WRITE")]
    assert entries_after(busy_block_0, "read", CRCPass()) == [e_("FRAM_STATUS_BYTE"), invalid]
    assert entries_after(crc_block_0, "read", CRC8()) == [e_("FRAM_DATA_CRC"), invalid]
    assert entries_after(crc_both, "read", CRC8()) == [e_("FRAM_DATA_CRC"), invalid, e_("FRAM_DATA_CRC"), invalid]


def _land_altered_payload(chunk: "FRAMChunk") -> None:
    # The verify pass's subject: block 0's payload lands with its first byte flipped, the status bytes intact.
    original_sync = chunk.fram.set_values_sync
    payload_addr = chunk._block_addr[0]

    def altering(buf: bytes | bytearray | memoryview, addr_start: int) -> int:
        if addr_start == payload_addr:
            altered = bytearray(buf)
            altered[0] ^= 0xFF
            return original_sync(altered, addr_start)
        return original_sync(buf, addr_start)

    chunk.fram.set_values_sync = altering  # type: ignore[method-assign]


def test_a_verify_pass_that_finds_a_mismatch_logs_fram_verify() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), verify=1, owner="T1")
    assert chunk is not None
    _land_altered_payload(chunk)
    assert run(chunk.write(b"good")) is False
    assert _entries(run(manager.get_error_counter())) == [(code("E", "FRAM_VERIFY"), "E")]


def test_a_verify_pass_whose_block_read_fails_the_crc_logs_fram_data_crc() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8(), verify=1, owner="T1")
    assert chunk is not None
    _land_altered_payload(chunk)
    assert run(chunk.write(b"good")) is False
    assert _entries(run(manager.get_error_counter())) == [(code("E", "FRAM_DATA_CRC"), "E"), (code("E", "FRAM_VERIFY"), "E")]


def test_an_unallocatable_check_length_logs_alloc_on_read_and_write() -> None:
    # The cross-check's scratch could not be allocated: the read cannot verify block 1 (an ALLOC entry, then
    # the block's own warning and its rewrite) and a verified write cannot verify at all.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), check_length=-1, owner="T1")
    assert chunk is not None
    assert run(chunk.write(b"data")) is True
    assert run(chunk.read()) == bytearray(b"data")
    assert _entries(run(manager.get_error_counter())) == [(code("E", "ALLOC"), "E"), (code("W", "FRAM_BLOCK_INVALID"), "W")]
    verified, _chip = make_manager()
    run(setup_manager(verified))
    vchunk = verified.get_chunk(4, crc=CRCPass(), check_length=-1, verify=1, owner="T1")
    assert vchunk is not None
    assert run(vchunk.write(b"data")) is False
    assert _entries(run(verified.get_error_counter())) == [(code("E", "ALLOC"), "E"), (code("E", "FRAM_VERIFY"), "E")]


# ---------------------------------------------------------------------------
# verify - periodic write-back verification
# ---------------------------------------------------------------------------


def test_get_verify_set_verify_round_trip() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
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
    chunk = manager.get_chunk(4, crc=CRC8(), verify=1, owner="T1")
    assert chunk is not None

    async def scenario() -> bool:
        return await chunk.write(b"good")

    assert run(scenario()) is True


# ---------------------------------------------------------------------------
# pause
# ---------------------------------------------------------------------------


def test_manager_get_pause_reflects_set_pause_directly() -> None:
    # The plain getter itself, not just its effect on chunk operations. Real callers: a deliberate
    # reboot pauses storage right before resetting so no write is left mid-flight, and an
    # operator-triggered REST "mempause" pauses writes for a bounded maintenance window.
    manager, _chip = make_manager()
    assert manager.get_pause() is False
    manager.set_pause(value=True)
    assert manager.get_pause() is True
    manager.set_pause(value=False)
    assert manager.get_pause() is False


def test_manager_pause_blocks_chunk_operations() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None
    run(chunk.write(b"data"))
    manager.set_pause(value=True)

    async def scenario() -> tuple[bool, bytearray | None]:
        write_ok = await chunk.write(b"else")
        read_result = await chunk.read()
        return write_ok, read_result

    write_ok, read_result = run(scenario())
    assert write_ok is False
    assert read_result is None  # refused, not "no data" - but collapses to the same sentinel

    manager.set_pause(value=False)

    async def confirm() -> bytearray | None:
        return await chunk.read()

    assert run(confirm()) == bytearray(b"data")  # original data intact - "else" write was refused


def test_pause_short_circuits_before_the_bus_so_an_injected_fault_survives_untouched() -> None:
    # The ORDERING claim the test above cannot make: _read()/_write() consult _mempause()
    # BEFORE any SPI access, so a paused operation never drives the bus at all. Discriminated by a
    # queued one-shot readinto fault, which a paused read would have consumed.

    # A READ fault deliberately - machine.SPI's fake makes write() non-injectable on purpose,
    # matching the real rp2 write-only path's own inability to fail (Part F.5.2).
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None
    run(chunk.write(b"good"))
    chip.inject_fault("readinto", OSError(5, "SPI RX overrun"), times=1)
    manager.set_pause(value=True)

    async def while_paused() -> "tuple[bytearray | None, ErrorLog]":
        result = await chunk.read()
        return result, await manager.get_error_counter()

    paused_result, paused_errs = run(while_paused())
    assert paused_result is None  # refused by the gate
    # The refusal is logged as a WARNING (_read()'s FRAM_PAUSED), never an error, and no error
    # appears at all since nothing reached the bus. Asserting on ErrType rather than ErrCount is
    # deliberate: ErrCount counts "W" entries too, so it cannot tell "refused" from "tried".
    assert "E" not in paused_errs["FRAM"]["ErrType"]
    assert (code("W", "FRAM_PAUSED"), "W") in _entries(paused_errs)  # _read()'s own "FRAM communication paused" warning

    manager.set_pause(value=False)

    async def after_unpause() -> "tuple[bytearray | None, ErrorLog]":
        result = await chunk.read()
        return result, await manager.get_error_counter()

    result, errs = run(after_unpause())
    # The fault was still queued: it fires now, on the first read that genuinely reaches the bus.
    # The read still returns data - a single transient overrun is absorbed by the dual-copy
    # fallback (Part F.5.2) - but the error counter is what proves the bus was actually touched.
    assert result == bytearray(b"good")
    assert "E" in errs["FRAM"]["ErrType"]  # an error only appears once the bus is genuinely driven


def test_unpausing_restores_a_genuinely_working_bus_not_just_a_cleared_flag() -> None:
    # The other half of the pause lifecycle: after unpausing, a real write/read round trip must
    # land new bytes on the chip. A distinct second pattern makes a stale read impossible to
    # mistake for a fresh one.
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None
    run(chunk.write(b"aaaa"))
    manager.set_pause(value=True)
    assert run(chunk.write(b"bbbb")) is False
    addr0, _addr1 = chunk._block_addr
    assert bytes(chip.memory[addr0 : addr0 + 4]) == b"aaaa"  # the refused write never reached the chip

    manager.set_pause(value=False)
    assert run(chunk.write(b"bbbb")) is True
    assert run(chunk.read()) == bytearray(b"bbbb")
    assert bytes(chip.memory[addr0 : addr0 + 4]) == b"bbbb"  # ...and the real chip bytes changed


def test_a_commanded_mempause_spends_one_slot_across_chunks() -> None:
    # Every chunk logs into the manager's one history, so a pause refusing operations on several
    # chunks is still one repeated code: one slot, with ErrCount counting every refusal.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk_a = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    chunk_b = manager.get_chunk(4, crc=CRC8(), owner="T2")
    assert chunk_a is not None and chunk_b is not None
    manager.set_pause(value=True)

    async def scenario() -> "ErrorLog":
        for chunk in (chunk_a, chunk_b):
            assert await chunk.write(b"data") is False
            assert await chunk.read() is None
            assert await chunk.clear() is False
        return await manager.get_error_counter()

    errs = run(scenario())
    assert _entries(errs) == [(code("W", "FRAM_PAUSED"), "W")]
    assert errs["FRAM"]["ErrCount"] == 6


def test_every_allocated_chunk_is_recorded_once_and_a_refused_one_never() -> None:
    manager, _chip = make_manager(max_size=64)
    plain = manager.get_chunk(4, owner="T1")
    stamped = manager.get_timestamped_chunk(4, _synced, owner="T2")
    assert plain is not None and stamped is not None
    assert manager.get_chunk(0, owner="T3") is None  # a zero-size request is refused
    assert manager.get_chunk(64, owner="T4") is None  # out of memory
    assert manager.get_timestamped_chunk(64, _synced, owner="T5") is None
    assert manager._chunks == [plain, stamped]


def test_wait_idle_returns_at_once_on_an_idle_chunk_and_after_the_operation_in_flight() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, owner="T1")
    assert chunk is not None

    async def scenario() -> "list[str]":
        order: list[str] = []
        await chunk.wait_idle()  # nothing in flight
        order.append("idle at once")
        await chunk._op_lock.acquire()  # an operation in flight

        async def waiter() -> None:
            await chunk.wait_idle()
            order.append("idle")

        task = asyncio.create_task(waiter())
        for _ in range(3):
            await asyncio.sleep(0)
        order.append("released")
        chunk._op_lock.release()
        await task
        return order

    assert run(scenario()) == ["idle at once", "released", "idle"]


def test_quiesce_pauses_first_then_waits_out_each_chunk_and_reports_each_step() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    first = manager.get_chunk(4, owner="T1")
    second = manager.get_timestamped_chunk(4, _synced, owner="T2")
    assert first is not None and second is not None
    steps: list[bool] = []

    async def scenario() -> "tuple[bool, list[bool], bool]":
        await second._op_lock.acquire()  # the second chunk's operation is in flight
        task = asyncio.create_task(manager.quiesce(lambda: steps.append(manager.get_pause())))
        for _ in range(3):
            await asyncio.sleep(0)
        held = (task.done(), list(steps))
        second._op_lock.release()
        await task
        assert held == (False, [True])  # paused before the first step; still waiting on the busy chunk
        return task.done(), list(steps), await first.write(b"ab")

    done, all_steps, written = run(scenario())
    assert done is True
    assert all_steps == [True, True]  # one step per chunk, the pause set before the first
    assert written is False  # a new operation meets the pause


# ---------------------------------------------------------------------------
# clear - zeroing both copies of a chunk
# ---------------------------------------------------------------------------


def test_clear_resets_chunk_to_reading_as_uninitialized() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
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
    chunk = manager.get_timestamped_chunk(4, _not_synced, crc=CRCPass(), owner="T1")
    assert chunk is not None

    async def scenario() -> tuple[bool, bool, int | None, int | None, int | None, bytearray | None]:
        write_ok, ntp_synced, utc = await chunk.write(b"data")
        ts, age, data = await chunk.read()
        return write_ok, ntp_synced, utc, ts, age, data

    write_ok, ntp_synced, _utc, ts, age, data = run(scenario())
    assert ntp_synced is False
    assert write_ok is True
    assert ts is None
    assert age is None
    assert data == bytearray(b"data")


def test_timestamped_write_with_ntp_sync_stores_and_reads_back_valid_timestamp() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(4, _synced, crc=CRCPass(), owner="T1")
    assert chunk is not None

    async def scenario() -> tuple[bool, int | None, int | None, int | None, bytearray | None]:
        write_ok, ntp_synced, utc = await chunk.write(b"data")
        assert write_ok is True
        ts, age, data = await chunk.read()
        return ntp_synced, utc, ts, age, data

    with _UTCValid():
        ntp_synced, utc, ts, age, data = run(scenario())
    assert ntp_synced is True
    assert utc is not None and utc != 0
    assert ts == utc
    assert age is not None and age >= 0
    assert data == bytearray(b"data")


def test_timestamped_corrupted_timestamp_byte_self_heals_when_crc_protected() -> None:
    # The CRC covers the whole buffer, including the embedded 8-byte timestamp prefix, not just
    # the user payload - corrupting a timestamp byte directly (not the data, not tested elsewhere)
    # must be caught the same way any other corruption in the block is.
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(4, _synced, crc=CRC8(), owner="T1")
    assert chunk is not None
    with _UTCValid():
        run(chunk.write(b"data"))
    addr0, _addr1 = chunk._block_addr
    chip.memory[addr0] ^= 0xFF  # first byte of the on-chip timestamp field itself

    async def scenario() -> "tuple[int | None, bytearray | None, ErrorLog]":
        ts, _age, data = await chunk.read()
        errs = await manager.get_error_counter()
        return ts, data, errs

    ts, data, errs = run(scenario())
    assert ts is not None and data == bytearray(b"data")  # recovered from block 1
    assert code("E", "FRAM_DATA_CRC") in errs["FRAM"]["ErrNum"]  # _read_chunk: "CRC error in _read_chunk!" - same path as payload corruption


def test_timestamped_corrupted_timestamp_byte_hard_fails_without_crc() -> None:
    # With crc=CRCPass() (no checksum at all), a single corrupted copy is still caught - not by
    # any CRC but by the cross-block byte comparison every read() does: block 0 looks fine alone
    # yet disagrees with block 1, the same "which is right?" hard failure, not a silent answer.
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(4, _synced, crc=CRCPass(), owner="T1")
    assert chunk is not None
    run(chunk.write(b"data"))
    addr0, _addr1 = chunk._block_addr
    chip.memory[addr0] ^= 0xFF

    async def scenario() -> "tuple[int | None, int | None, bytearray | None, ErrorLog]":
        ts, age, data = await chunk.read()
        errs = await manager.get_error_counter()
        return ts, age, data, errs

    ts, age, data, errs = run(scenario())
    assert (ts, age, data) == (None, None, None)  # hard fail, not a silently wrong timestamp
    assert code("E", "FRAM_COPIES_DIFFER") in errs["FRAM"]["ErrNum"]  # _read(): "Both blocks valid but different data"


def test_timestamped_read_skips_age_when_currently_not_synced() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    write_chunk = manager.get_timestamped_chunk(4, _synced, crc=CRCPass(), owner="T1")
    assert write_chunk is not None
    with _UTCValid():
        run(write_chunk.write(b"data"))

    # A second handle onto the same chunk, synced at write time but not at read time.
    read_chunk = manager.get_timestamped_chunk(4, _not_synced, crc=CRCPass(), owner="T2")
    assert read_chunk is not None
    read_chunk._block_addr = write_chunk._block_addr  # same on-chip storage, different callback

    async def scenario() -> tuple[int | None, int | None]:
        ts, age, _data = await read_chunk.read()
        return ts, age

    ts, age = run(scenario())
    assert ts is not None  # the timestamp itself was stored validly...
    assert age is None  # ...but age can't be computed without a currently-synced clock


def test_timestamped_write_require_ntp_refuses_when_not_synced_and_persists_nothing() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(4, _not_synced, crc=CRCPass(), owner="T1")
    assert chunk is not None

    async def scenario() -> tuple[bool, bool, int | None, tuple[int | None, int | None, bytearray | None]]:
        write_ok, ntp_synced, utc = await chunk.write(b"data", require_ntp=True)
        read_result = await chunk.read()
        return write_ok, ntp_synced, utc, read_result

    write_ok, ntp_synced, utc, read_result = run(scenario())
    assert (write_ok, ntp_synced, utc) == (False, False, None)
    assert read_result == (None, None, None)


def test_a_synced_write_before_the_first_clock_set_stores_no_timestamp() -> None:
    # The NTP callback answers synced, but utc_now() is None until the NTP client sets the clock:
    # the write takes the not-synced path, and a write that requires NTP is refused.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(4, _synced, crc=CRCPass(), owner="T1")
    assert chunk is not None

    async def scenario() -> tuple[tuple[bool, bool, int | None], tuple[bool, bool, int | None], int | None]:
        refused = await chunk.write(b"data", require_ntp=True)
        written = await chunk.write(b"data")
        ts, _age, _data = await chunk.read()
        return refused, written, ts

    refused, written, ts = run(scenario())
    assert refused == (False, False, None)
    assert written[0] is True and written[1] is False
    assert ts is None
    assert run(manager.get_error_counter())["FRAM"]["ErrCount"] == 0  # no clock is no fault


def test_a_read_before_the_first_clock_set_reports_no_age() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(4, _synced, crc=CRCPass(), owner="T1")
    assert chunk is not None
    with _UTCValid():
        run(chunk.write(b"data"))
    ts, age, data = run(chunk.read())
    assert ts is not None  # stored while the clock was valid...
    assert age is None  # ...but no age without a valid clock now
    assert data == bytearray(b"data")


# ---------------------------------------------------------------------------
# Regression tests for bugs found and fixed during this file's src/ promotion
# ---------------------------------------------------------------------------


def test_ntp_callback_raising_degrades_to_not_synced_instead_of_propagating() -> None:
    # ntp_sync_callback is a caller-injected dependency whose generic Callable type does not
    # statically rule out misbehaving, and it was called unguarded before this promotion. See
    # tests/test_ntp_fram_system_integration.py for the same guard against the real object.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(4, _raising_callback, crc=CRCPass(), owner="T1")
    assert chunk is not None

    async def scenario() -> tuple[bool, bool, int | None]:
        return await chunk.write(b"data")

    write_ok, ntp_synced, _utc = run(scenario())
    assert ntp_synced is False
    assert write_ok is True  # still writes, with the uninitialized timestamp sentinel
    assert _entries(run(manager.get_error_counter())) == [(code("E", "CALLBACK"), "E")]  # its console line names the write path


def test_compare_with_huge_check_length_self_heals_instead_of_crashing() -> None:
    # _compare_with's `bytearray(self.check_length)` was unguarded against MemoryError/
    # OverflowError - check_length is caller-supplied, not hardware-bounded like the allocation
    # asy_fram_driver.py guards. Magnitude matches test_asy_base_classes.py's confirmed boundary.

    # The allocation failure makes _compare_with report block 1 "not verifiably valid", which
    # _read() heals from block 0 like any other block-1 problem - so the fix integrates with the
    # existing self-healing rather than merely avoiding a crash.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), check_length=2**62, owner="T1")
    assert chunk is not None
    run(chunk.write(b"data"))

    async def scenario() -> bytearray | None:
        return await chunk.read()

    assert run(scenario()) == bytearray(b"data")  # no crash, and still recovers real data


def test_compare_with_zero_check_length_fails_cleanly_instead_of_hanging_forever() -> None:
    # Regression for a real bug found in review: _read_chunk's streaming loop computes
    # chunk_size = min(len(buf), total_size - position), so with check_length=0 it is always 0,
    # position never advances and the loop runs forever. wait_for turns that into a clear timeout.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), check_length=0, owner="T1")
    assert chunk is not None
    run(chunk.write(b"data"))

    async def scenario() -> bytearray | None:
        return await asyncio.wait_for(chunk.read(), timeout=_READ_WAIT_S)

    assert run(scenario()) == bytearray(b"data")  # block 1 unverifiable -> healed from block 0
    # Pinned, not just "some error": a bench session reads these codes out of the FRAM log to
    # tell this apart from a real read failure (FRAM_READ), which degrades identically from outside.
    assert code("E", "BAD_ARG") in run(manager.get_error_counter())["FRAM"]["ErrNum"]


def test_compare_with_huge_check_length_during_write_verification_degrades_safely() -> None:
    # Same guard, exercised via _write()'s own verify path instead of _read()'s cross-check -
    # verify treats "couldn't verify" the same as "verification failed", so the write reports
    # False (real data was physically written, but that can't be confirmed) rather than crashing.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), check_length=2**62, verify=1, owner="T1")
    assert chunk is not None

    async def scenario() -> bool:
        return await chunk.write(b"data")

    assert run(scenario()) is False


def test_oversized_write_persists_a_bad_arg_entry() -> None:
    # FRAMChunk.write's "data too large" refusal and _FRAMBaseChunk.clear()'s failure log into the one
    # PrintLogHistory every chunk of a manager shares, so they carry two different catalog codes.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None

    async def scenario() -> "ErrorLog":
        await chunk.write(b"toolong!")
        return await manager.get_error_counter()

    result = run(scenario())
    assert code("E", "BAD_ARG") in result["FRAM"]["ErrNum"]
    assert code("E", "FRAM_CLEAR") not in result["FRAM"]["ErrNum"]


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
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None
    chip.drop_wren = True

    async def scenario() -> "tuple[bool, ErrorLog]":
        write_ok = await chunk.write(b"data")
        result = await manager.get_error_counter()
        return write_ok, result

    write_ok, result = run(scenario())
    errnums = result["FRAM"]["ErrNum"]
    assert write_ok is False
    assert code("E", "FRAM_STATUS_WRITE") in errnums  # _set_check_sb: "Write status byte failed!" (the busy mark)
    assert code("E", "FRAM_BLOCK_WRITE") in errnums  # _write: "Writing block 0 failed!"


def test_read_fails_cleanly_when_chip_drops_wren_latch() -> None:
    # Reading also needs a real chip write (BUSY status before the read, IDLE after) - drop_wren
    # breaks that step for both blocks, so read() reports total failure instead of stale/no data.
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None
    run(chunk.write(b"good"))
    chip.drop_wren = True

    async def scenario() -> "tuple[bytearray | None, ErrorLog]":
        result = await chunk.read()
        errs = await manager.get_error_counter()
        return result, errs

    result, errs = run(scenario())
    errnums = errs["FRAM"]["ErrNum"]
    assert result is None
    assert errnums.count(code("E", "FRAM_STATUS_WRITE")) == 2  # both blocks fail the same way (the read's own busy-set write)
    assert (code("W", "FRAM_BLOCK_INVALID"), "W") in _entries(errs)  # "Invalid data in block 1" - neither copy usable


def test_clear_fails_cleanly_when_chip_drops_wren_latch() -> None:
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None
    run(chunk.write(b"good"))
    chip.drop_wren = True

    async def scenario() -> "tuple[bool, ErrorLog]":
        cleared = await chunk.clear()
        errs = await manager.get_error_counter()
        return cleared, errs

    cleared, errs = run(scenario())
    errnums = errs["FRAM"]["ErrNum"]
    assert cleared is False
    assert code("E", "FRAM_STATUS_WRITE") in errnums  # the status-byte write, then clear()'s own entry
    assert code("E", "FRAM_CLEAR") in errnums


def test_write_fails_cleanly_when_fram_is_write_protected() -> None:
    # Same failure shape as the WREN-drop test, but via the driver's own write-protect check
    # (asy_fram_driver.py's _write()'s first guard) - a real, commonly used failure mode (write
    # protection is a supported driver feature), not just a simulated bus glitch.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None

    async def scenario() -> "tuple[bool, bool, ErrorLog]":
        protect_ok = await manager.fram.set_write_protected(value=True)
        write_ok = await chunk.write(b"data")
        errs = await manager.get_error_counter()
        return protect_ok, write_ok, errs

    protect_ok, write_ok, errs = run(scenario())
    errnums = errs["FRAM"]["ErrNum"]
    assert protect_ok is True
    assert write_ok is False
    assert code("E", "FRAM_STATUS_WRITE") in errnums
    assert code("E", "FRAM_BLOCK_WRITE") in errnums


def test_read_is_also_blocked_while_write_protected_and_the_data_survives_it() -> None:
    # Intended, accepted behaviour, not a defect (owner, 2026-09-11; SPEC A.4):
    # _read_chunk() must WRITE a transient busy marker before it reads, so write protection gates
    # read() as it gates write() - yet the stored bytes come back intact once protection clears.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None

    async def scenario() -> "tuple[bytearray | None, bytearray | None, ErrorLog]":
        assert await chunk.write(b"keep")
        assert await manager.fram.set_write_protected(value=True)
        blocked = await chunk.read()
        errs = await manager.get_error_counter()
        assert await manager.fram.set_write_protected(value=False)
        restored = await chunk.read()
        return blocked, restored, errs

    blocked, restored, errs = run(scenario())
    errnums = errs["FRAM"]["ErrNum"]
    assert blocked is None
    assert bytes(restored or b"") == b"keep"
    # Identical error signature to the WREN-drop read above: the busy-status write is what fails,
    # for both blocks, and neither copy is then usable.
    assert errnums.count(code("E", "FRAM_STATUS_WRITE")) == 2
    assert (code("W", "FRAM_BLOCK_INVALID"), "W") in _entries(errs)


def test_write_protect_gate_still_reaches_the_bus_unlike_the_pause_gate() -> None:
    # The two refusals look identical from outside (both hand back None) but differ where it
    # matters: set_pause() short-circuits before SPI, write protection does not - its guard sits
    # inside FRAM_SPI._write(), after _set_check_sb() already clocked the status byte off the chip.
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None
    reads = 0
    real_readinto = chip.readinto

    # Parameter name must match FakeMB85RS64V.readinto()'s own (_write_value) - mypy compares the
    # full signature on a method reassignment, and a renamed parameter is an `assignment` error
    # that `type: ignore[method-assign]` deliberately does not cover.
    def counting_readinto(buf: "bytearray | memoryview", _write_value: int = 0x00) -> None:
        nonlocal reads
        reads += 1
        real_readinto(buf, _write_value)

    async def scenario() -> "tuple[int, int]":
        assert await chunk.write(b"keep")
        assert await manager.fram.set_write_protected(value=True)
        chip.readinto = counting_readinto  # type: ignore[method-assign]
        assert await chunk.read() is None
        protected_reads = reads
        assert await manager.fram.set_write_protected(value=False)
        manager.set_pause(value=True)
        reads_before_pause = reads
        assert await chunk.read() is None
        paused_reads = reads - reads_before_pause
        manager.set_pause(value=False)
        return protected_reads, paused_reads

    protected_reads, paused_reads = run(scenario())
    chip.readinto = real_readinto  # type: ignore[method-assign]
    assert paused_reads == 0, "the paused read reached the chip - the pause gate is supposed to short-circuit first"
    assert protected_reads > 0, "the write-protected read never reached the chip - it is supposed to fail at the chip, not before it"


def test_operations_fail_cleanly_once_fram_chip_goes_uninitialized_mid_run() -> None:
    # Models a chip that stopped responding after a successful setup() - every FRAM_SPI call
    # short-circuits on its own `initialized` guard before touching the bus. Distinct from the
    # WREN-drop case: reads fail at the status-byte read, not the later status write.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None
    run(chunk.write(b"good"))
    manager.fram.initialized = False

    async def scenario() -> "tuple[bool, bytearray | None, bool, ErrorLog]":
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
    assert code("E", "FRAM_STATUS_READ") in errnums  # read's own status-byte *read* fails immediately (vs. the write for WREN-drop)
    assert code("E", "NOT_INIT") in errnums  # the driver guard's own entry
    assert code("E", "FRAM_BLOCK_WRITE") in errnums  # write's chunk-layer entry
    assert code("E", "FRAM_CLEAR") in errnums  # clear's chunk-layer entry


# ---------------------------------------------------------------------------
# Both-blocks-invalid and self-heal-write-failure paths - the remaining _read() branches this
# suite hadn't exercised yet
# ---------------------------------------------------------------------------


def test_read_fails_when_both_blocks_have_crc_invalid_payloads() -> None:
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8(), owner="T1")
    assert chunk is not None
    run(chunk.write(b"good"))
    addr0, addr1 = chunk._block_addr
    chip.memory[addr0] ^= 0xFF
    chip.memory[addr1] ^= 0xFF

    async def scenario() -> "tuple[bytearray | None, ErrorLog]":
        result = await chunk.read()
        errs = await manager.get_error_counter()
        return result, errs

    result, errs = run(scenario())
    errnums = errs["FRAM"]["ErrNum"]
    assert result is None
    assert errnums.count(code("E", "FRAM_DATA_CRC")) == 2  # CRC error in _read_chunk, both blocks
    assert (code("W", "FRAM_BLOCK_INVALID"), "W") in _entries(errs)  # "Invalid data in block 1" - none of the copies usable


def test_block1_invalid_while_block0_valid_self_heals_block1() -> None:
    # Mirror of the block-0-corruption self-heal test - this file only ever corrupted block 0's
    # payload, and block 1 being the wrong one is a distinct code path (_compare_with's cross-check
    # inside _read()'s "block 0 already valid" branch, not the "block 0 invalid" branch).
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8(), owner="T1")
    assert chunk is not None
    run(chunk.write(b"good"))
    _addr0, addr1 = chunk._block_addr
    chip.memory[addr1] ^= 0xFF

    async def scenario() -> bytearray | None:
        return await chunk.read()

    assert run(scenario()) == bytearray(b"good")
    _addr0, addr1 = chunk._block_addr
    assert bytes(chip.memory[addr1 : addr1 + 4]) == b"good"  # block 1 healed


def test_read_fails_when_self_heal_write_to_block0_fails() -> None:
    # Block 0 is invalid and needs healing from block 1; if that heal write fails, read() must
    # still report failure, not pretend block 0 is fine. _write_chunk is patched per-address
    # rather than write-protected, which would also block the BUSY write every read needs.
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8(), owner="T1")
    assert chunk is not None
    run(chunk.write(b"good"))
    addr0, _addr1 = chunk._block_addr
    chip.memory[addr0] ^= 0xFF
    original_write_chunk = chunk._write_chunk

    async def failing_write_chunk(buf: bytearray, addr: int) -> bool:
        if addr == addr0:
            return False
        return await original_write_chunk(buf, addr)

    chunk._write_chunk = failing_write_chunk  # type: ignore[method-assign]

    async def scenario() -> "tuple[bytearray | None, ErrorLog]":
        result = await chunk.read()
        errs = await manager.get_error_counter()
        return result, errs

    result, errs = run(scenario())
    errnums = errs["FRAM"]["ErrNum"]
    assert result is None
    assert code("E", "FRAM_BLOCK_WRITE") in errnums  # "Writing block 0 failed!" - the heal write itself


def test_read_fails_when_self_heal_write_to_block1_fails() -> None:
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8(), owner="T1")
    assert chunk is not None
    run(chunk.write(b"good"))
    _addr0, addr1 = chunk._block_addr
    chip.memory[addr1] ^= 0xFF
    original_write_chunk = chunk._write_chunk

    async def failing_write_chunk(buf: bytearray, addr: int) -> bool:
        if addr == addr1:
            return False
        return await original_write_chunk(buf, addr)

    chunk._write_chunk = failing_write_chunk  # type: ignore[method-assign]

    async def scenario() -> "tuple[bytearray | None, ErrorLog]":
        result = await chunk.read()
        errs = await manager.get_error_counter()
        return result, errs

    result, errs = run(scenario())
    errnums = errs["FRAM"]["ErrNum"]
    assert result is None
    assert code("E", "FRAM_BLOCK_WRITE") in errnums  # "Writing block 1 failed!" - the heal write itself


def test_read_into_rejects_a_buffer_of_the_wrong_size() -> None:
    # Mirror of the existing write_into size-mismatch test - _read()'s own BAD_ARG guard.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None
    wrong_buf = FRAMChunkBuffer(8, 0)  # this chunk expects 4 payload bytes, not 8

    async def scenario() -> bool | None:
        return await chunk.read_into(wrong_buf)

    assert run(scenario()) is None  # not read, as opposed to read and found blank or invalid


def test_clear_while_paused_is_refused() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None
    run(chunk.write(b"data"))
    manager.set_pause(value=True)

    async def scenario() -> tuple[bool, bytearray | None]:
        cleared = await chunk.clear()
        manager.set_pause(value=False)
        data = await chunk.read()
        return cleared, data

    cleared, data = run(scenario())
    assert cleared is False
    assert data == bytearray(b"data")  # refused, original data intact


# ---------------------------------------------------------------------------
# CRC width, check_length, and verify-counter configuration variety (cross-dependency with
# asy_crc_checks.py's other concrete CRC widths, only CRC8/CRCPass exercised above)
# ---------------------------------------------------------------------------


def test_write_then_read_round_trip_with_crc16() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(5, crc=CRC16(), owner="T1")
    assert chunk is not None
    assert chunk._block_addr == (0, 9)  # 5 data + 2 crc + 2 status per block

    async def scenario() -> bytearray | None:
        await chunk.write(b"hello")
        return await chunk.read()

    assert run(scenario()) == bytearray(b"hello")


def test_write_then_read_round_trip_with_crc32() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(5, crc=CRC32(), owner="T1")
    assert chunk is not None
    assert chunk._block_addr == (0, 11)  # 5 data + 4 crc + 2 status per block

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
    chunk = manager.get_chunk(10, crc=CRCPass(), check_length=1, verify=1, owner="T1")
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
    chunk = manager.get_chunk(4, crc=CRCPass(), verify=2, owner="T1")
    assert chunk is not None

    run(chunk.write(b"one!"))
    assert chunk._verify_counter == 1  # below threshold, no verification ran yet
    run(chunk.write(b"two!"))
    assert chunk._verify_counter == 0  # threshold hit, verification ran and counter reset


def test_get_chunk_allocation_succeeds_at_exact_remaining_capacity_boundary() -> None:
    manager, _chip = make_manager(max_size=12)
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")  # full_size = 2*(4+0+2) = 12, exact fit
    assert chunk is not None
    assert manager.get_chunk(1, owner="T2") is None  # nothing left at all


# ---------------------------------------------------------------------------
# FRAMTimestampedChunk shares _FRAMBaseChunk behavior (inheritance) - pause/clear/verify
# were only ever exercised through FRAMChunk above; confirm the shared base actually behaves
# the same way through the timestamped subclass too, not just by inheritance on paper.
# ---------------------------------------------------------------------------


def test_timestamped_chunk_clear_resets_to_reading_as_uninitialized() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(4, _synced, crc=CRCPass(), owner="T1")
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


def test_timestamped_chunk_respects_manager_pause() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(4, _synced, crc=CRCPass(), owner="T1")
    assert chunk is not None
    manager.set_pause(value=True)

    async def scenario() -> tuple[bool, tuple[int | None, int | None, bytearray | None]]:
        write_ok, _ntp_synced, _utc = await chunk.write(b"data")
        read_result = await chunk.read()
        return write_ok, read_result

    write_ok, read_result = run(scenario())
    assert write_ok is False  # _write's own pause guard refuses, same as FRAMChunk
    assert read_result == (None, None, None)

    manager.set_pause(value=False)

    async def unpaused() -> tuple[bool, tuple[int | None, int | None, bytearray | None]]:
        write_ok, _ntp_synced, _utc = await chunk.write(b"data")
        result = await chunk.read()
        return write_ok, result

    write_ok, result = run(unpaused())
    assert write_ok is True
    assert result[2] == bytearray(b"data")


def test_timestamped_chunk_write_with_verify_enabled_succeeds() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(4, _synced, crc=CRCPass(), verify=1, owner="T1")
    assert chunk is not None

    async def scenario() -> bool:
        write_ok, _ntp_synced, _utc = await chunk.write(b"data")
        return write_ok

    assert run(scenario()) is True


# ---------------------------------------------------------------------------
# Unusual content - edge cases in what's actually stored, not just failure injection
# ---------------------------------------------------------------------------


def test_get_chunk_rejects_zero_size_regardless_of_crc() -> None:
    # A chunk storing nothing is never a sensible request - rejected unconditionally at the top of
    # get_chunk(), before any CRC/capacity logic, not just for the CRCPass() case that used to
    # reproduce the old spurious-CRC-error-on-read quirk (now gone, replaced by this rejection).
    manager, _chip = make_manager()
    run(setup_manager(manager))
    assert manager.get_chunk(0, crc=CRCPass(), owner="T1") is None
    assert manager.get_chunk(0, crc=CRC8(), owner="T2") is None
    assert manager.get_chunk(0, owner="T3") is None  # default crc


def test_get_timestamped_chunk_rejects_zero_size_regardless_of_crc() -> None:
    # Mirrors get_chunk()'s rejection. The timestamped variant never reproduced the old quirk
    # itself - the 8-byte timestamp header keeps total_size > 0 whatever the payload size - but a
    # zero-payload request is just as senseless, so it is rejected the same way for consistency.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    assert manager.get_timestamped_chunk(0, _synced, crc=CRCPass(), owner="T1") is None
    assert manager.get_timestamped_chunk(0, _synced, crc=CRC8(), owner="T2") is None
    assert manager.get_timestamped_chunk(0, _synced, owner="T3") is None  # default crc


def test_get_chunk_rejects_zero_size_even_with_abundant_remaining_capacity() -> None:
    # Confirms the rejection isn't a side effect of the capacity check (e.g. some accidental
    # zero-cost-allocation math) - it happens unconditionally, even on a freshly constructed
    # manager with its entire 8KB untouched, and doesn't disturb the allocator's own bookkeeping.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    assert manager.get_chunk(0, crc=CRCPass(), owner="T1") is None
    assert manager._allocated_size == 0  # rejected before touching the bump pointer


def test_all_zero_and_all_0xff_payloads_round_trip_without_sentinel_collision() -> None:
    # Payload content lives in a separate address range from the status bytes, and _STATUS_UNINIT
    # is 0x00 - one of the exact byte values a real payload might legitimately store. Confirms
    # there is no confusion between "chunk never written" and "chunk holds all-zero data".
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8(), owner="T1")
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
    # _TS_UNINIT (0) doubles as both "never written" and the literal Unix epoch, so a real UTC
    # timestamp of exactly 0 is indistinguishable from uninitialized on read. Inherited from the
    # deployed design, not introduced here - locked down as real, documented behavior.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(4, _synced, crc=CRCPass(), owner="T1")
    assert chunk is not None

    class _EpochZeroTime:
        @staticmethod
        def gmtime() -> tuple[int, ...]:
            return (1970, 1, 1, 0, 0, 0, 0, 1)

        @staticmethod
        def mktime(_t: tuple[int, ...]) -> int:
            return 0

    original_time = asy_base_classes.time
    asy_base_classes.time = _EpochZeroTime  # type: ignore[assignment]
    try:

        async def scenario() -> tuple[bool, bool, int | None]:
            return await chunk.write(b"data")

        with _UTCValid():
            write_ok, ntp_synced, utc = run(scenario())
    finally:
        asy_base_classes.time = original_time

    assert ntp_synced is True
    assert utc == 0
    assert write_ok is True

    async def read_back() -> int | None:
        ts, _age, _data = await chunk.read()
        return ts

    assert run(read_back()) is None  # collides with the "never written" sentinel


# ---------------------------------------------------------------------------
# Deliberately-allowed exceptions propagating through this file's own composition points -
# confirms the "caught here" / "allowed to raise" boundary asy_fram_driver.py's docstring
# documents holds one layer up too, through FRAMManager's public API.
# ---------------------------------------------------------------------------


def test_construction_raises_uncaught_valueerror_for_an_out_of_range_spi_cs() -> None:
    # FRAMManager.__init__ constructs FRAM_SPI(...) with no try/except - a bad spi_cs is a
    # one-time at-boot misconfiguration allowed to raise loudly rather than silently produce a
    # permanently nonfunctional manager, and that carve-out must still hold through __init__.
    bus = make_bus()
    try:
        FRAMManager(bus, 99, max_size=0x2000)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_setup_fails_cleanly_when_device_id_does_not_match() -> None:
    # Real device-not-found path (asy_fram_driver.py's FRAM_SPI.setup() raises OSError) - caught
    # by FRAMManager.setup()'s own try/except, turned into a clean False + an INIT entry, not left
    # to propagate. A different, driver-owned RDID mismatch, not a caller misconfiguration.
    manager, chip = make_manager()
    chip.rdid_response = bytes([0xFF, 0xFF, 0xFF, 0xFF])

    async def scenario() -> "tuple[bool, ErrorLog]":
        ok = await manager.setup()
        errs = await manager.get_error_counter()
        return ok, errs

    ok, errs = run(scenario())
    assert ok is False
    assert code("E", "INIT") in errs["FRAM"]["ErrNum"]


def test_chunk_operations_fail_cleanly_when_the_bus_is_deinitialized_mid_run() -> None:
    # A deinitialised bus is reported by the driver as bus-down; the chunk layer fails the operation
    # and logs its own entry.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None
    run(chunk.write(b"good"))
    manager.fram._spidev.spi.deinit()

    async def scenario() -> "tuple[bool, bytearray | None, bool, ErrorLog]":
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
    assert code("E", "FRAM_BUS_DOWN") in errnums  # the driver's status, no raise
    assert code("E", "UNEXPECTED") not in errnums
    assert code("E", "FRAM_BLOCK_WRITE") in errnums
    assert code("E", "FRAM_STATUS_READ") in errnums
    assert code("E", "FRAM_CLEAR") in errnums


# ---------------------------------------------------------------------------
# Configuration edge values - within-type but unusual/invalid inputs (negative, zero, huge),
# single and combined, staying inside every parameter's declared int type throughout.
# ---------------------------------------------------------------------------


def test_get_chunk_negative_size_degrades_to_an_unusable_but_non_crashing_chunk() -> None:
    # A negative size flows straight into FRAMChunkBuffer/RegionBuffer, whose own guard
    # (asy_base_classes.py) already turns any negative size into buf=None - confirmed here at this
    # file's own boundary that the degradation is clean end to end, not just at that lower layer.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(-4, crc=CRCPass(), owner="T1")
    assert chunk is not None  # allocation bookkeeping itself doesn't reject a negative size

    async def scenario() -> tuple[bool, bytearray | None]:
        write_ok = await chunk.write(b"data")
        data = await chunk.read()
        return write_ok, data

    write_ok, data = run(scenario())
    assert write_ok is False
    assert data is None


def test_get_chunk_negative_verify_triggers_verification_on_every_single_write() -> None:
    # Surprising but harmless: _verify_counter starts at 0 and is compared with `>=` against
    # `verify` after incrementing, so a negative verify makes (1 >= negative) true on the first
    # write and verification runs every time. Locked down as real, non-crashing behavior.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), verify=-5, owner="T1")
    assert chunk is not None

    async def scenario() -> bool:
        return await chunk.write(b"data")

    assert run(scenario()) is True
    assert chunk._verify_counter == 0  # verification ran and reset the counter, not left at 1


def test_get_chunk_negative_check_length_self_heals_instead_of_crashing() -> None:
    # The same MemoryError-degrades-to-"not verifiably valid" guard as the huge-check_length
    # regression test, reached from a different input class: bytearray(negative_int) raises
    # MemoryError here too, the negative count being reinterpreted as a huge unsigned request.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), check_length=-1, owner="T1")
    assert chunk is not None
    run(chunk.write(b"data"))

    async def scenario() -> bytearray | None:
        return await chunk.read()

    assert run(scenario()) == bytearray(b"data")


def test_manager_negative_max_size_degrades_to_always_out_of_memory() -> None:
    manager, _chip = make_manager(max_size=-100)
    assert manager.get_chunk(4, owner="T1") is None
    assert manager.get_timestamped_chunk(4, _synced, owner="T2") is None


def test_multiple_invalid_parameters_combined_still_degrade_safely() -> None:
    # negative size + negative verify + negative check_length together, all in one chunk - none
    # of these interact to produce anything worse than each one's own individual degradation.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(-4, crc=CRCPass(), verify=-1, check_length=-1, owner="T1")
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
    # _handle_status_bytes checks that its two status bytes' "uninit" results agree before
    # trusting either: byte 1 = UNINIT with byte 2 = IDLE are each individually valid (neither
    # trips the FRAM_STATUS_BYTE path), but disagreeing is its own failure the base checks cannot catch.

    # Only reachable via _read_chunk's initial busy-set step, the one call site where the "uninit"
    # flag is not hardcoded False. Previously untested.
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None
    run(chunk.write(b"good"))
    addr0, _addr1 = chunk._block_addr
    chip.memory[addr0 + 4] = _STATUS_UNINIT
    chip.memory[addr0 + 5] = _STATUS_IDLE

    async def scenario() -> "tuple[bytearray | None, ErrorLog]":
        result = await chunk.read()
        errs = await manager.get_error_counter()
        return result, errs

    result, errs = run(scenario())
    assert result == bytearray(b"good")  # falls back to block 1 and self-heals, like any other invalid block 0
    assert code("E", "FRAM_STATUS_DISAGREE") in errs["FRAM"]["ErrNum"]  # _handle_status_bytes: "Read status uninit bytes inconsistent!"


def test_a_mixed_status_pair_fails_the_check_and_keeps_its_busy_marker() -> None:
    # A blank status byte beside an idle one, on both blocks: the blank byte is left unmarked, the idle one
    # takes its busy marker, the pair disagrees, and the block stays invalid - one entry per block.
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None
    run(chunk.write(b"good"))
    for addr in chunk._block_addr:
        chip.memory[addr + 4] = _STATUS_UNINIT
        chip.memory[addr + 5] = _STATUS_IDLE
    assert run(chunk.read_into(chunk.get_buffer())) is False
    for addr in chunk._block_addr:
        assert (chip.memory[addr + 4], chip.memory[addr + 5]) == (_STATUS_UNINIT, _STATUS_BUSY)
    errnums = run(manager.get_error_counter())["FRAM"]["ErrNum"]
    assert errnums.count(code("E", "FRAM_STATUS_DISAGREE")) == 2


def test_write_verify_fails_when_only_block_1_fails_verification() -> None:
    # The verify loop's block-1 failure was never exercised, since block 0 failing first
    # short-circuits before n=1. Isolating block 1's own verification failure needs a per-address
    # patch, the same technique as the self-heal-write-failure tests, so block 0 genuinely passes.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), verify=1, owner="T1")
    assert chunk is not None
    _addr0, addr1 = chunk._block_addr
    original_compare_with = chunk._compare_with

    async def failing_compare_with(buf: bytearray, addr: int) -> tuple[bool, bool, bool, bool]:
        if addr == addr1:
            return False, False, False, False
        return await original_compare_with(buf, addr)

    chunk._compare_with = failing_compare_with  # type: ignore[method-assign]

    async def scenario() -> "tuple[bool, ErrorLog]":
        write_ok = await chunk.write(b"data")
        errs = await manager.get_error_counter()
        return write_ok, errs

    write_ok, errs = run(scenario())
    assert write_ok is False
    assert code("E", "FRAM_VERIFY") in errs["FRAM"]["ErrNum"]  # "Block 1 write verification error!"


def test_op_lock_prevents_concurrent_writes_from_interleaving_between_blocks() -> None:
    # Found by construction, not inspection: _write() used to hold fram's lock only per block, so
    # two tasks writing one chunk could interleave between blocks, each reporting success while
    # leaving one task's data in block 0 and the other's in block 1.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8(), owner="T1")
    assert chunk is not None
    events: list[str] = []
    original_write_chunk = chunk._write_chunk

    async def instrumented_write_chunk(buf: bytearray, addr: int) -> bool:
        events.append("enter")
        result = await original_write_chunk(buf, addr)
        events.append("exit")
        return result

    chunk._write_chunk = instrumented_write_chunk  # type: ignore[method-assign]

    async def scenario() -> list[bool]:
        # The stub types 2-arg gather() as returning tuple[bool, bool], mirroring CPython
        # typeshed's precise-arity overloads, but MicroPython's asyncio.gather() always returns a
        # list (extmod/asyncio/funcs.py) - so the annotation stays honest to runtime behavior.
        return await asyncio.gather(chunk.write(b"AAAA"), chunk.write(b"BBBB"))  # type: ignore[return-value]

    results = run(scenario())
    assert results == [True, True]
    # Each write() calls _write_chunk twice (block 0, block 1) - full serialization means the
    # pattern is enter,exit,enter,exit,enter,exit,enter,exit (one writer's whole 2-block sequence
    # completes before the other's even starts), never two "enter"s without an "exit" between them.
    assert events == ["enter", "exit"] * 4
    read_result = run(chunk.read())
    assert read_result in (bytearray(b"AAAA"), bytearray(b"BBBB"))  # always a clean, single payload


def test_manager_setup_is_idempotent_when_called_twice() -> None:
    manager, _chip = make_manager()
    ok1 = run(manager.setup())
    ok2 = run(manager.setup())
    assert ok1 is True
    assert ok2 is True
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None

    async def scenario() -> tuple[bool, bytearray | None]:
        write_ok = await chunk.write(b"data")
        data = await chunk.read()
        return write_ok, data

    write_ok, data = run(scenario())
    assert write_ok is True
    assert data == bytearray(b"data")


def test_get_chunk_size_1_still_needs_status_byte_overhead_at_the_capacity_boundary() -> None:
    # The smallest valid (nonzero) payload still needs 2*_NUM_STATUS_BYTES=4 bytes of real
    # overhead on top of it - a manager with no room left must refuse even the smallest request.
    manager, _chip = make_manager(max_size=6)
    run(setup_manager(manager))
    chunk = manager.get_chunk(1, crc=CRCPass(), owner="T1")  # full_size = 2*(1+0+2) = 6, exact fit
    assert chunk is not None
    assert manager.get_chunk(1, crc=CRCPass(), owner="T2") is None  # no room left, even for another tiny chunk


# ---------------------------------------------------------------------------
# Remaining reachable coverage gaps - each isolates one specific untested branch
# ---------------------------------------------------------------------------


def test_write_fails_cleanly_when_block_1s_write_itself_fails() -> None:
    # _write()'s own block-1-write-failure path, distinct from block 0's (its own console line) -
    # isolated the same way the self-heal write-failure tests are, by patching _write_chunk
    # per-address so only block 1's own write call fails.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8(), owner="T1")
    assert chunk is not None
    _addr0, addr1 = chunk._block_addr
    original_write_chunk = chunk._write_chunk

    async def failing_write_chunk(buf: bytearray, addr: int) -> bool:
        if addr == addr1:
            return False
        return await original_write_chunk(buf, addr)

    chunk._write_chunk = failing_write_chunk  # type: ignore[method-assign]

    async def scenario() -> "tuple[bool, ErrorLog]":
        ok = await chunk.write(b"data")
        errs = await manager.get_error_counter()
        return ok, errs

    ok, errs = run(scenario())
    assert ok is False
    assert code("E", "FRAM_BLOCK_WRITE") in errs["FRAM"]["ErrNum"]  # _write(): "Writing block 1 failed!"


def test_read_self_heals_block_1_when_it_reads_back_as_uninitialized() -> None:
    # Mirrors the corrupted-block-1 self-heal tests, but for the "never written" case (both status
    # bytes UNINIT, not corrupted) rather than invalid data - a distinct branch (_read()'s own
    # uninit=True path) previously unexercised.
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None
    run(chunk.write(b"good"))
    _addr0, addr1 = chunk._block_addr
    chip.memory[addr1 + 4] = _STATUS_UNINIT
    chip.memory[addr1 + 5] = _STATUS_UNINIT

    async def scenario() -> bytearray | None:
        return await chunk.read()

    result = run(scenario())
    assert result == bytearray(b"good")  # block 0 stays authoritative
    assert bytes(chip.memory[addr1 : addr1 + 4]) == b"good"  # block 1 healed from it
    assert chip.memory[addr1 + 4] == _STATUS_IDLE  # healed to IDLE, not left UNINIT


def test_handle_status_bytes_fails_cleanly_when_only_the_second_byte_write_fails() -> None:
    # _set_check_sb's two calls (status byte 1, then byte 2) were previously only ever exercised
    # failing on byte 1 - byte 2 failing on its own needs an address-selective patch on
    # set_values() itself, since both bytes normally succeed or fail together under drop_wren.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None
    addr0, _addr1 = chunk._block_addr
    byte2_addr = addr0 + chunk.size + chunk.crc.length() + 1
    fail_set_values_at(chunk, byte2_addr)

    async def scenario() -> "tuple[bool, ErrorLog]":
        ok = await chunk.write(b"data")
        errs = await manager.get_error_counter()
        return ok, errs

    ok, errs = run(scenario())
    assert ok is False
    assert code("E", "FRAM_STATUS_WRITE") in errs["FRAM"]["ErrNum"]  # _set_check_sb: "Write status byte failed!" for byte 2


def test_write_chunk_fails_cleanly_when_crc_computation_itself_fails() -> None:
    # add_into() returning None (a real, if rare, CRC-computation failure) - the CRC objects in
    # normal use never fail on a well-formed buffer, so this patches the chunk's own crc instance
    # directly rather than contriving a real failing computation.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8(), owner="T1")
    assert chunk is not None

    async def failing_add_into(buffer: bytearray, size: int, start: int = 0, init: int | None = None) -> int | None:
        return None

    chunk.crc.add_into = failing_add_into  # type: ignore[method-assign]

    async def scenario() -> "tuple[bool, ErrorLog]":
        ok = await chunk.write(b"data")
        errs = await manager.get_error_counter()
        return ok, errs

    ok, errs = run(scenario())
    assert ok is False
    assert code("E", "FRAM_CRC_FAILED") in errs["FRAM"]["ErrNum"]  # _write_chunk: "CRC computation failed!"


def test_write_chunk_fails_cleanly_when_the_payload_write_itself_fails() -> None:
    # The payload set_values() call sits at a different address than the status-byte writes
    # around it - forcing it to fail in isolation needed its own address-selective patch.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8(), owner="T1")
    assert chunk is not None
    addr0, _addr1 = chunk._block_addr
    fail_set_values_at(chunk, addr0)

    async def scenario() -> "tuple[bool, ErrorLog]":
        ok = await chunk.write(b"data")
        errs = await manager.get_error_counter()
        return ok, errs

    ok, errs = run(scenario())
    assert ok is False
    assert code("E", "FRAM_PAYLOAD_WRITE") in errs["FRAM"]["ErrNum"]  # _write_chunk: "_write_chunk failed!" (the payload write)


def test_read_chunk_self_heals_from_block_1_when_block_0s_payload_read_itself_fails() -> None:
    # A genuine FRAM communication failure on the payload read (distinct from status-byte or
    # CRC-level corruption) needed its own address-selective patch on get_values() to isolate,
    # since block 0's status-byte reads use a different address entirely.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8(), owner="T1")
    assert chunk is not None
    run(chunk.write(b"good"))
    addr0, _addr1 = chunk._block_addr
    fail_get_values_at(chunk, addr0)

    async def scenario() -> "tuple[bytearray | None, ErrorLog]":
        result = await chunk.read()
        errs = await manager.get_error_counter()
        return result, errs

    result, errs = run(scenario())
    assert result == bytearray(b"good")  # self-heals from block 1
    assert code("E", "FRAM_READ") in errs["FRAM"]["ErrNum"]  # _read_chunk: "FRAM read error in _read_chunk!"


def test_read_chunk_fails_cleanly_when_incremental_crc_update_itself_fails() -> None:
    # run_inc() returning False mid-stream (distinct from the final check_inc() CRC-mismatch case)
    # was never exercised - patches the chunk's own crc instance the same way as the add_into test.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8(), owner="T1")
    assert chunk is not None
    run(chunk.write(b"good"))

    async def failing_run_inc(bytearr: bytearray | memoryview, init: int | None = None) -> bool:
        return False

    chunk.crc.run_inc = failing_run_inc  # type: ignore[method-assign]

    async def scenario() -> "tuple[bytearray | None, ErrorLog]":
        result = await chunk.read()
        errs = await manager.get_error_counter()
        return result, errs

    result, errs = run(scenario())
    assert result is None  # both blocks share the same patched crc, so neither can self-heal
    assert code("E", "FRAM_CRC_FAILED") in errs["FRAM"]["ErrNum"]  # _read_chunk: "Incremental CRC failed in _read_chunk!"


def test_read_chunk_fails_cleanly_when_the_final_idle_status_write_itself_fails() -> None:
    # The read-idle-set step, after a successful streaming read, has its own "write status byte
    # failed" branch. Reaching it rather than the busy-set at the start of the same read, which
    # writes the same address, needs a call counter: 1st write busy-set, 2nd the idle-set.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8(), owner="T1")
    assert chunk is not None
    run(chunk.write(b"good"))
    addr0, _addr1 = chunk._block_addr
    status_byte1_addr = addr0 + chunk.size + chunk.crc.length()
    fail_set_values_at(chunk, status_byte1_addr, on_call=2)

    async def scenario() -> "tuple[bytearray | None, ErrorLog]":
        result = await chunk.read()
        errs = await manager.get_error_counter()
        return result, errs

    result, errs = run(scenario())
    assert result == bytearray(b"good")  # self-heals from block 1 (block 0's own heal-write succeeds too)
    assert code("E", "FRAM_STATUS_WRITE") in errs["FRAM"]["ErrNum"]  # _read_chunk: read-idle-set "write status byte failed"


def test_clear_chunk_fails_cleanly_when_the_data_wipe_write_itself_fails() -> None:
    # The data-wipe set_values() call is distinct from clear()'s own status-byte write around it.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8(), owner="T1")
    assert chunk is not None
    run(chunk.write(b"good"))
    addr0, _addr1 = chunk._block_addr
    fail_set_values_at(chunk, addr0)

    async def scenario() -> "tuple[bool, ErrorLog]":
        ok = await chunk.clear()
        errs = await manager.get_error_counter()
        return ok, errs

    ok, errs = run(scenario())
    assert ok is False
    assert code("E", "FRAM_CLEAR_WRITE") in errs["FRAM"]["ErrNum"]  # _clear_chunk: "FRAM write failed in _clear_chunk!"


def test_write_into_called_directly_with_an_unallocated_buffer_returns_false() -> None:
    # write_into()'s own guard, only reachable when called directly (bypassing write()'s own
    # pre-check) - the real production call shape asy_print_log.py's PrintLogHistoryStore actually uses.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(-4, crc=CRCPass(), owner="T1")  # negative size - buffer allocation fails
    assert chunk is not None
    buf = chunk.get_buffer()

    async def scenario() -> bool:
        return await chunk.write_into(buf)

    assert run(scenario()) is False


def test_timestamped_write_returns_false_tuple_for_a_negative_size_chunk() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(-4, _synced, crc=CRCPass(), owner="T1")
    assert chunk is not None

    async def scenario() -> tuple[bool, bool, int | None]:
        return await chunk.write(b"data")

    assert run(scenario()) == (False, False, None)


def test_timestamped_write_data_larger_than_buffer_fails_with_bad_arg() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(2, _synced, crc=CRCPass(), owner="T1")
    assert chunk is not None

    async def scenario() -> "tuple[tuple[bool, bool, int | None], ErrorLog]":
        result = await chunk.write(b"toolong")
        errs = await manager.get_error_counter()
        return result, errs

    result, errs = run(scenario())
    assert result == (False, False, None)
    assert code("E", "BAD_ARG") in errs["FRAM"]["ErrNum"]


def test_timestamped_write_into_called_directly_with_an_unallocated_buffer_returns_false() -> None:
    # Same direct-call shape as the plain chunk's own write_into() test above, for the timestamped
    # variant's tbuf-None guard (also exercises get_ts_buf()'s own None-check as a side effect).
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(-4, _synced, crc=CRCPass(), owner="T1")
    assert chunk is not None
    buf = chunk.get_buffer()

    async def scenario() -> tuple[bool, bool, int | None]:
        return await chunk.write_into(buf)

    assert run(scenario()) == (False, False, None)


def test_timestamped_read_returns_none_tuple_for_a_negative_size_chunk() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(-4, _synced, crc=CRCPass(), owner="T1")
    assert chunk is not None

    async def scenario() -> tuple[int | None, int | None, bytearray | None]:
        return await chunk.read()

    assert run(scenario()) == (None, None, None)


def test_timestamped_read_ntp_callback_failure_during_age_computation_is_caught() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(4, _synced, crc=CRCPass(), owner="T1")
    assert chunk is not None
    with _UTCValid():
        run(chunk.write(b"data"))
    chunk._ntp_sync_callback = _raising_callback  # swap for the read-side NTP check only

    async def scenario() -> tuple[int | None, int | None, bytearray | None]:
        return await chunk.read()

    ts, age, data = run(scenario())
    assert ts is not None  # timestamp itself decoded fine
    assert age is None  # NTP check failed, so age can't be computed
    assert data == bytearray(b"data")
    assert code("E", "CALLBACK") in run(manager.get_error_counter())["FRAM"]["ErrNum"]


def test_manager_reset_error_counter_clears_history() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None

    async def scenario() -> "tuple[ErrorLog, ErrorLog]":
        await chunk.write(b"toolongdata")  # BAD_ARG, oversized - just to populate some history
        before = await manager.get_error_counter()
        assert await manager.reset_error_counter() is True  # the RAM-only history's reset always lands
        after = await manager.get_error_counter()
        return before, after

    before, after = run(scenario())
    assert before["FRAM"]["ErrCount"] > 0
    assert after["FRAM"]["ErrCount"] == 0


# ---------------------------------------------------------------------------
# The buffers' remaining accessors and both chunks' entry points on a buffer whose allocation FAILED. That is
# RegionBuffer's documented MemoryError degrade (asy_base_classes.py sets buf=None), so these are
# the branches a real allocation failure reaches - they must degrade, never raise.
# ---------------------------------------------------------------------------


def _degraded_buffer() -> FRAMChunkBuffer:
    # A negative size takes the same buf=None path bytearray(size) raising MemoryError takes, with
    # no injection needed - asy_base_classes.py guards both together for exactly that reason.
    buf = FRAMChunkBuffer(-1, 0)
    assert buf.get_buf() is None, "the fixture no longer produces an unallocated buffer"
    return buf


def _degraded_timestamped_buffer() -> FRAMChunkTimestampedBuffer:
    buf = FRAMChunkTimestampedBuffer(-1, 0, 0)
    assert buf.get_buf() is None, "the fixture no longer produces an unallocated buffer"
    return buf


def test_every_accessor_on_an_unallocated_chunk_buffer_returns_none() -> None:
    buf = _degraded_buffer()
    assert buf.get_data_buf() is None


def test_every_accessor_on_an_unallocated_timestamped_buffer_returns_none() -> None:
    # get_ts_buf() slices around data_start, so an unguarded one would raise TypeError on None rather
    # than returning it.
    buf = _degraded_timestamped_buffer()
    assert buf.get_ts_buf() is None
    assert buf.get_data_buf() is None


def test_the_timestamped_entry_points_degrade_on_a_foreign_unallocated_buffer() -> None:
    # Distinct from the negative-size-chunk tests above, which degrade a chunk's OWN buffer: here
    # a healthy chunk is handed someone else's failed allocation, the shape asy_print_log.py's store
    # really uses. Documented tuples, not just falsy - each caller unpacks three values.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(4, _synced, crc=CRC8(), owner="T1")
    assert chunk is not None
    assert run(chunk.write_into(_degraded_timestamped_buffer())) == (False, False, None)
    assert run(chunk.read_into(_degraded_timestamped_buffer())) == (None, None, None)


def test_an_unallocated_buffer_never_reaches_the_chip_at_all() -> None:
    # The property behind the two above: a degraded buffer is rejected before any SPI traffic, so a
    # failed allocation cannot leave a half-written chunk - not even the WREN that opens the envelope.
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8(), owner="T1")
    assert chunk is not None
    sent: list[bytes] = []
    real_write = chip.write

    def counting_write(buf: object) -> None:
        sent.append(bytes(buf))  # type: ignore[call-overload]
        real_write(buf)

    chip.write = counting_write  # type: ignore[method-assign]  # deliberate monkeypatch
    try:
        assert run(chunk.write_into(_degraded_buffer())) is False
    finally:
        chip.write = real_write  # type: ignore[method-assign]
    assert sent == [], f"a write from an unallocated buffer still drove the bus: {sent!r}"


def test_a_missing_chunk_buffer_logs_alloc() -> None:
    # Every chunk entry point that meets an unallocated buffer persists one ALLOC entry of its own:
    # an own buffer that failed (negative size) and a foreign one handed in, on both chunk classes.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    plain = manager.get_chunk(4, crc=CRC8(), owner="T1")
    stamped = manager.get_timestamped_chunk(4, _synced, crc=CRC8(), owner="T2")
    plain_unalloc = manager.get_chunk(-4, crc=CRCPass(), owner="T3")  # allocated last: a negative size moves the bump pointer back
    stamped_unalloc = manager.get_timestamped_chunk(-4, _synced, crc=CRCPass(), owner="T4")
    assert plain is not None and plain_unalloc is not None
    assert stamped is not None and stamped_unalloc is not None
    calls: tuple[Callable[[], Awaitable[object]], ...] = (
        lambda: plain_unalloc.write(b"data"),
        plain_unalloc.read,
        lambda: plain.write_into(_degraded_buffer()),
        lambda: plain.read_into(_degraded_buffer()),
        lambda: stamped_unalloc.write(b"data"),
        stamped_unalloc.read,
        lambda: stamped.write_into(_degraded_timestamped_buffer()),
        lambda: stamped.read_into(_degraded_timestamped_buffer()),
    )

    async def scenario() -> "list[int]":
        counts = []
        for call in calls:
            await call()
            log = await manager.get_error_counter()
            assert log["FRAM"]["ErrNum"][-1] == code("E", "ALLOC")
            counts.append(log["FRAM"]["ErrCount"])
        return counts

    assert run(scenario()) == list(range(1, len(calls) + 1)), "each call adds exactly one entry"
    assert _entries(run(manager.get_error_counter())) == [(code("E", "ALLOC"), "E")]  # one repeated code, one slot


# ---------------------------------------------------------------------------
# The rp2 SPI RX-overrun raise site (v1.29.0; SPECIFICATION.md F.5.2), driven through the live path: the
# fault is injected at the machine.SPI boundary and travels asy_spi_driver -> asy_fram_driver.get_values()
# -> _read_chunk's loop, so these pin down the stack's behaviour, not one layer's contract.
# ---------------------------------------------------------------------------


def test_rx_overrun_on_block_0s_payload_read_is_absorbed_by_the_dual_copy_recovery() -> None:
    # The headline live-path result: one transient overrun costs nothing. _read_chunk's blanket
    # except catches the OSError, _read falls through to block 1, and the caller gets its data.
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(40, crc=CRC8(), owner="T1")  # 41 bytes with CRC - over the 32-byte DMA threshold
    assert chunk is not None
    payload = bytes(range(40))
    run(chunk.write(payload))
    chip.rx_overrun_remaining = 1  # exactly one DMA-path read raises, then the bus recovers
    warnings = _recorded_warnings(manager)
    writes = _recorded_payload_writes(chunk)
    buf = chunk.get_buffer()

    async def scenario() -> "tuple[bool | None, ErrorLog]":
        result = await chunk.read_into(buf)
        return result, await manager.get_error_counter()

    result, errs = run(scenario())
    assert result is True
    assert bytes(buf.get_data_buf() or b"") == payload  # correct data, from block 1
    assert chip.rx_overrun_remaining == 0  # the overrun really did fire
    assert code("E", "UNEXPECTED") in errs["FRAM"]["ErrNum"]  # _read_chunk's "General read error", not an escaped raise
    assert chunk._block_addr[0] in writes  # block 0 rewritten from block 1
    assert not [w for w in warnings if w.startswith("Invalid data in block 0")]  # a fault, not corruption


def test_rx_overrun_on_every_payload_read_fails_cleanly_instead_of_killing_the_caller() -> None:
    # Both copies unreadable is the genuinely unrecoverable case - it must still degrade to a
    # None result rather than propagate, since an escaping OSError would take the reader task
    # down and leave asy_system_service.py's supervisor to restart it.
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(40, crc=CRC8(), owner="T1")
    assert chunk is not None
    run(chunk.write(bytes(range(40))))
    chip.rx_overrun = True  # sticky: every DMA-path read raises, both blocks
    before = bytearray(chip.memory)

    async def scenario() -> "tuple[bool | None, ErrorLog]":
        result = await chunk.read_into(chunk.get_buffer())  # must not raise
        return result, await manager.get_error_counter()

    result, errs = run(scenario())
    assert result is None  # not read: the stored history is kept, never re-initialised
    assert code("E", "UNEXPECTED") in errs["FRAM"]["ErrNum"]
    status = {addr + 41 + offset for addr in chunk._block_addr for offset in (0, 1)}
    changed = {addr for addr in range(len(before)) if before[addr] != chip.memory[addr]}
    assert changed <= status, f"the read path wrote more than the status bytes: {sorted(changed)}"


def test_a_sub_threshold_chunk_is_immune_to_a_bus_wide_overrun() -> None:
    # The 32-byte DMA threshold is a property of the live path too, not just the fake: a small
    # chunk's payload read and every 1-byte status-register read stay on the software path, so a
    # bus-wide overrun cannot touch them. This is why the fault needs a big chunk to reproduce.
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8(), owner="T1")  # 5 bytes total - under the threshold
    assert chunk is not None
    run(chunk.write(b"good"))
    chip.rx_overrun = True

    async def scenario() -> "tuple[bytearray | None, ErrorLog]":
        result = await chunk.read()
        return result, await manager.get_error_counter()

    result, errs = run(scenario())
    assert result == bytearray(b"good")
    assert code("E", "UNEXPECTED") not in errs["FRAM"]["ErrNum"]  # nothing raised at all


def test_an_overrun_leaves_the_spi_bus_itself_reusable_rather_than_wedged() -> None:
    # The failure path runs through two `async with` blocks (the manager's chunk lock and
    # SPIDevice's CS/bus lock). If either leaked, one overrun would wedge the shared SPI bus for
    # every other device on it. It does not: a second chunk reads normally once the bus recovers.
    manager, chip = make_manager()
    run(setup_manager(manager))
    broken = manager.get_chunk(40, crc=CRC8(), owner="T1")
    other = manager.get_chunk(40, crc=CRC8(), owner="T2")
    assert broken is not None and other is not None
    payload = bytes(range(40))
    run(broken.write(payload))
    run(other.write(payload))
    spidev = broken.fram._spidev
    chip.rx_overrun = True

    async def scenario() -> "tuple[bytearray | None, bool, bool, bytearray | None]":
        failed = await broken.read()
        cs_released = bool(spidev._cs_pin.value()) == (not spidev._cs_active_value)
        lock_released = not spidev.session_lock.locked()
        chip.rx_overrun = False  # bus recovers
        return failed, cs_released, lock_released, await other.read()

    failed, cs_released, lock_released, untouched = run(scenario())
    assert failed is None
    assert cs_released  # CS deasserted by SPIDevice.__aexit__ despite the exception
    assert lock_released
    assert untouched == bytearray(payload)  # the bus itself is fine


def test_an_overrun_mid_read_leaves_the_chunk_unreadable_until_it_is_rewritten() -> None:
    # Intended behavior, not a defect (Part A.4): _read_chunk marks a block BUSY before reading
    # and restores IDLE only on the way out, so an interruption leaves both copies marked.
    # MB85RS64V reads are destructive internally, so an interrupted read is an interrupted restore.
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(40, crc=CRC8(), owner="T1")
    assert chunk is not None
    payload = bytes(range(40))
    run(chunk.write(payload))
    addr0, addr1 = chunk._block_addr
    status0 = addr0 + 41  # layout is [data][crc][status 1][status 2]; 40 payload + 1 CRC8 byte
    status1 = addr1 + 41
    assert (chip.memory[status0], chip.memory[status1]) == (_STATUS_IDLE, _STATUS_IDLE)
    chip.rx_overrun = True

    async def scenario() -> "tuple[bytearray | None, tuple[int, int], bytes, bytearray | None, ErrorLog, bool]":
        failed = await chunk.read()
        # Sampled here, before the repairing write below puts the status bytes back to IDLE.
        left_as = (chip.memory[status0], chip.memory[status1])
        data_on_chip = bytes(chip.memory[addr0 : addr0 + 40])
        chip.rx_overrun = False  # the bus recovers completely
        still_failing = await chunk.read()
        errs = await manager.get_error_counter()
        repaired = await chunk.write(payload) and (await chunk.read()) == bytearray(payload)
        return failed, left_as, data_on_chip, still_failing, errs, repaired

    failed, left_as, data_on_chip, still_failing, errs, repaired = run(scenario())
    assert failed is None
    assert left_as == (_STATUS_BUSY, _STATUS_BUSY)
    assert data_on_chip == payload  # the data itself was never damaged
    assert still_failing is None  # ...and is refused anyway, deliberately
    assert code("E", "FRAM_STATUS_BYTE") in errs["FRAM"]["ErrNum"]  # "Read status byte is not 1 but 2"
    assert repaired  # a write is the only thing that clears it


# Status-byte failures, branch by branch: one code per condition (Part C.7.1); each layer the
# failure reaches keeps its own entry (owner, 2026-10-02).


def status_byte_addrs(chunk: "FRAMChunk") -> tuple[int, int]:
    base = chunk._block_addr[0] + chunk.size + chunk.crc.length()
    return base, base + 1


def fail_set_values_at(chunk: "FRAMChunk", addr: int, *, on_call: int = 1) -> None:
    # Address- and occurrence-selective: the same status byte is written once for the BUSY mark and
    # once for the IDLE mark, so the BUSY and IDLE marks need different occurrences. Injected at
    # set_values_sync(), the seam the chunk layer actually calls; the sentinel is an unused status bit.
    original_sync = chunk.fram.set_values_sync
    original_report = chunk.fram.report_set_values
    seen = [0]

    def failing(buf: bytes | bytearray | memoryview, addr_start: int) -> int:
        if addr_start == addr:
            seen[0] += 1
            if seen[0] == on_call:
                return _INJECTED_FAILURE
        return original_sync(buf, addr_start)

    async def reporting(status: int) -> bool:
        if status == _INJECTED_FAILURE:
            return False
        return await original_report(status)

    chunk.fram.set_values_sync = failing  # type: ignore[method-assign]
    chunk.fram.report_set_values = reporting  # type: ignore[method-assign]


def fail_get_values_at(chunk: "FRAMChunk", addr: int, *, on_call: int = 1) -> None:
    # The read-side mirror of fail_set_values_at above; same seam, same sentinel.
    original_sync = chunk.fram.get_values_sync
    original_report = chunk.fram.report_get_values
    seen = [0]

    def failing(buf: bytearray | memoryview, addr_start: int = 0) -> int:
        if addr_start == addr:
            seen[0] += 1
            if seen[0] == on_call:
                return _INJECTED_FAILURE
        return original_sync(buf, addr_start)

    async def reporting(status: int) -> bool:
        if status == _INJECTED_FAILURE:
            return False
        return await original_report(status)

    chunk.fram.get_values_sync = failing  # type: ignore[method-assign]
    chunk.fram.report_get_values = reporting  # type: ignore[method-assign]


def _recorded_warnings(manager: FRAMManager) -> list[str]:
    # Every warning text the chunk layer logs: the chunks share the manager's history instance.
    seen: list[str] = []
    real = manager.pr.wrn_s

    async def recording(*args: object, wrnno: int = 0, sep: str = " ", end: str = "\n") -> None:
        seen.append(sep.join(str(arg) for arg in args))
        await real(*args, wrnno=wrnno, sep=sep, end=end)

    manager.pr.wrn_s = recording  # type: ignore[method-assign]
    return seen


def _recorded_payload_writes(chunk: "FRAMChunk") -> list[int]:
    # The start address of every multi-byte write the chunk's driver makes (a payload, never a status byte).
    addrs: list[int] = []
    original_sync = chunk.fram.set_values_sync

    def recording(buf: bytes | bytearray | memoryview, addr_start: int) -> int:
        if len(buf) > 1:
            addrs.append(addr_start)
        return original_sync(buf, addr_start)

    chunk.fram.set_values_sync = recording  # type: ignore[method-assign]
    return addrs


def make_written_chunk(check_length: int = 8) -> "tuple[FRAMManager, FakeMB85RS64V, FRAMChunk]":
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), check_length=check_length, owner="T1")
    assert chunk is not None
    assert run(chunk.write(b"data")) is True
    return manager, chip, chunk


def errnums(manager: FRAMManager) -> list[int]:
    async def scenario() -> "ErrorLog":
        return await manager.get_error_counter()

    return run(scenario())["FRAM"]["ErrNum"]


def test_write_chunk_idle_mark_failing_on_status_byte_1_logs_the_status_byte_write_failure() -> None:
    manager, _chip, chunk = make_written_chunk()
    byte1, _byte2 = status_byte_addrs(chunk)
    fail_set_values_at(chunk, byte1, on_call=2)  # the IDLE mark, after the BUSY mark succeeded
    assert run(chunk.write(b"more")) is False
    assert code("E", "FRAM_STATUS_WRITE") in errnums(manager)  # byte 1's IDLE mark


def test_write_chunk_idle_mark_failing_on_status_byte_2_logs_the_status_byte_write_failure() -> None:
    manager, _chip, chunk = make_written_chunk()
    _byte1, byte2 = status_byte_addrs(chunk)
    fail_set_values_at(chunk, byte2, on_call=2)
    assert run(chunk.write(b"more")) is False
    assert code("E", "FRAM_STATUS_WRITE") in errnums(manager)  # byte 2's IDLE mark


def test_read_chunk_busy_mark_status_byte_2_read_failure_logs_the_status_byte_read_failure() -> None:
    manager, _chip, chunk = make_written_chunk()
    _byte1, byte2 = status_byte_addrs(chunk)
    fail_get_values_at(chunk, byte2)

    async def scenario() -> bytearray | None:
        return await chunk.read()

    run(scenario())
    assert code("E", "FRAM_STATUS_READ") in errnums(manager)  # byte 2's own "Read status byte failed!"


def test_read_chunk_busy_mark_status_byte_2_not_idle_logs_fram_status_byte() -> None:
    manager, chip, chunk = make_written_chunk()
    _byte1, byte2 = status_byte_addrs(chunk)
    chip.memory[byte2] = 0x7F  # neither IDLE nor UNINIT: a torn or corrupted status byte

    async def scenario() -> bytearray | None:
        return await chunk.read()

    run(scenario())
    assert code("E", "FRAM_STATUS_BYTE") in errnums(manager)


def test_read_chunk_busy_mark_status_byte_2_write_failure_logs_the_status_byte_write_failure() -> None:
    manager, _chip, chunk = make_written_chunk()
    _byte1, byte2 = status_byte_addrs(chunk)
    fail_set_values_at(chunk, byte2)  # the read's own BUSY mark; the write above already finished

    async def scenario() -> bytearray | None:
        return await chunk.read()

    run(scenario())
    assert code("E", "FRAM_STATUS_WRITE") in errnums(manager)  # the read's BUSY mark on byte 2


def test_clear_chunk_status_byte_2_failure_logs_the_status_byte_write_failure_and_clears_own() -> None:
    manager, _chip, chunk = make_written_chunk()
    _byte1, byte2 = status_byte_addrs(chunk)
    fail_set_values_at(chunk, byte2)

    async def scenario() -> bool:
        return await chunk.clear()

    assert run(scenario()) is False
    assert code("E", "FRAM_STATUS_WRITE") in errnums(manager)  # byte 2's UNINIT mark
    assert code("E", "FRAM_CLEAR") in errnums(manager)  # clear()'s own entry


# A block operation is not an opaque unit, and its scratch buffers belong to the chunk rather
# than to each call.


def test_a_concurrent_task_observes_a_block_operation_in_progress() -> None:
    # The per-command yields mean a block operation stays interleaved with the rest of the loop:
    # another task runs between its two status-byte pairs and can see the block marked BUSY, then
    # IDLE again. A block operation that never yielded would show only one of the two.
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None
    byte1, _byte2 = status_byte_addrs(chunk)
    seen: set[int] = set()

    async def observer() -> None:
        while True:
            seen.add(chip.memory[byte1])
            await asyncio.sleep(0)

    async def scenario() -> bool:
        watcher = asyncio.create_task(observer())
        await asyncio.sleep(0)
        ok = await chunk.write(b"data")
        watcher.cancel()
        try:
            await watcher
        except asyncio.CancelledError:
            pass
        return ok

    assert run(scenario()) is True
    assert _STATUS_BUSY in seen
    assert _STATUS_IDLE in seen


def test_every_block_operation_yields_even_when_it_returns_early() -> None:
    # A blank chip's whole read is two status-byte reads per block that find UNINIT and return, so the
    # yield after that pair must come before those early returns.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None
    passes = [0]

    async def competitor() -> None:
        while True:
            passes[0] += 1
            await asyncio.sleep(0)

    async def count(coro: "Coroutine[Any, Any, Any]") -> int:
        other = asyncio.create_task(competitor())
        await asyncio.sleep(0)
        before = passes[0]
        await coro
        during = passes[0] - before
        other.cancel()
        try:
            await other
        except asyncio.CancelledError:
            pass
        return during

    async def scenario() -> "tuple[int, int, int, int]":
        blank_read = await count(chunk.read())  # both blocks uninitialized: the early-return path
        wrote = await count(chunk.write(b"data"))
        valid_read = await count(chunk.read())
        cleared = await count(chunk.clear())
        return blank_read, wrote, valid_read, cleared

    blank_read, wrote, valid_read, cleared = run(scenario())
    assert blank_read >= 2, f"a blank read gave a competing task {blank_read} turns"  # one per block
    assert wrote >= 2
    assert valid_read >= 2
    assert cleared >= 2


def test_the_compare_with_scratch_buffer_belongs_to_the_chunk_not_the_call() -> None:
    # Was a bytearray(check_length) plus two memoryviews on every _compare_with() call - and
    # _compare_with() runs on every read and on every verified write. The size is fixed for the
    # chunk's whole life, so the buffer is allocated once, at construction.
    _manager, _chip, chunk = make_written_chunk()
    assert chunk._check_buf is not None
    assert len(chunk._check_buf) == 8
    before = id(chunk._check_buf)

    async def scenario() -> None:
        await chunk.read()
        await chunk.read()

    run(scenario())
    assert id(chunk._check_buf) == before


def test_a_chunk_whose_scratch_buffer_cannot_be_allocated_still_reads() -> None:
    # The (MemoryError, OverflowError) guard moves to construction with the allocation, but the
    # degradation must not change: _compare_with() reports "not verifiably valid", so a read
    # rewrites block 1 from block 0 and still returns the data (the self-heals test pins it).
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), check_length=-1, owner="T1")
    assert chunk is not None
    assert chunk._check_buf is None  # the allocation failed at construction, once, not per call
    run(chunk.write(b"data"))

    async def scenario() -> bytearray | None:
        return await chunk.read()

    assert run(scenario()) == bytearray(b"data")


# ---------------------------------------------------------------------------
# The central newest-entry rule (asy_print_log.py, SPECIFICATION.md C.7.1): a repeated identical code spends no
# new slot; ErrCount counts every event.
# ---------------------------------------------------------------------------


def _entries(errs: "ErrorLog") -> list[tuple[int, str]]:
    nums, types = errs["FRAM"]["ErrNum"], errs["FRAM"]["ErrType"]
    assert isinstance(nums, list)
    assert isinstance(types, list)
    # (number, type) pairs of the occupied slots; zip(strict=) has no MicroPython equivalent
    return [(num, types[index]) for index, num in enumerate(nums) if types[index] != "N"]


def test_a_block_0_that_keeps_failing_keeps_each_layers_entry_on_every_read() -> None:
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8(), owner="T1")
    assert chunk is not None

    async def scenario() -> "ErrorLog":
        await chunk.write(b"good")
        addr0, _addr1 = chunk._block_addr
        for _read in range(5):
            # Re-corrupted each time: _read() heals block 0 from block 1, so one flip is one event.
            chip.memory[addr0] ^= 0xFF
            assert await chunk.read() == bytearray(b"good")
        return await manager.get_error_counter()

    errs = run(scenario())
    # Each read meets the fault at two layers (the CRC check, then the block warning), so the two codes
    # alternate and each spends a slot: alternation is outside the newest-entry rule.
    crc_entry, block_entry = (code("E", "FRAM_DATA_CRC"), "E"), (code("W", "FRAM_BLOCK_INVALID"), "W")
    assert _entries(errs) == [crc_entry, block_entry] * 5
    assert errs["FRAM"]["ErrCount"] == 10


def test_a_recurrence_after_recovery_stays_one_slot() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None

    async def scenario() -> "ErrorLog":
        manager.set_pause(value=True)
        assert await chunk.write(b"data") is False  # FRAM_PAUSED
        manager.set_pause(value=False)
        assert await chunk.write(b"data") is True  # recovered: nothing logged
        assert await chunk.read() == bytearray(b"data")
        manager.set_pause(value=True)
        assert await chunk.write(b"else") is False  # the same code again, after the recovery
        return await manager.get_error_counter()

    errs = run(scenario())
    assert _entries(errs) == [(code("W", "FRAM_PAUSED"), "W")]
    assert errs["FRAM"]["ErrCount"] == 2


def test_a_held_mempause_spends_one_slot_for_paused_writes_and_reads() -> None:
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRCPass(), owner="T1")
    assert chunk is not None
    run(chunk.write(b"data"))
    manager.set_pause(value=True)

    async def scenario() -> "ErrorLog":
        for _cycle in range(4):
            await chunk.write(b"else")  # FRAM_PAUSED
            await chunk.read()  # FRAM_PAUSED
        return await manager.get_error_counter()

    errs = run(scenario())
    # A paused write and a paused read are one condition, one code.
    assert _entries(errs) == [(code("W", "FRAM_PAUSED"), "W")]
    assert errs["FRAM"]["ErrCount"] == 8


# ---------------------------------------------------------------------------
# A lost chip, a stepped clock, the erase and the chip-watch task
# ---------------------------------------------------------------------------


def test_every_chunk_operation_stays_silent_while_the_chip_is_lost() -> None:
    # The loss is the driver's one FRAM_CHIP_LOST entry: while it stands, no chunk operation reaches the bus
    # or logs, so the loggers' writes add nothing to the manager's history.
    manager, chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_chunk(4, crc=CRC8(), owner="T1")
    ts_chunk = manager.get_timestamped_chunk(4, _synced, crc=CRC8(), owner="T2")
    assert chunk is not None and ts_chunk is not None
    assert run(chunk.write(b"data")) is True
    stored = bytearray(chip.memory)
    chip.opcodes = []
    manager.fram.lost.set()
    assert run(chunk.write(b"else")) is False
    assert run(chunk.read_into(chunk.get_buffer())) is None
    assert run(chunk.clear()) is False
    assert run(chunk.invalidate()) is False
    assert run(ts_chunk.write(b"else"))[0] is False
    assert run(ts_chunk.read_into(ts_chunk.get_buffer())) == (None, None, None)
    assert chip.opcodes == []
    assert chip.memory == stored
    assert run(manager.get_error_counter())["FRAM"]["ErrCount"] == 0


class _SteppedTime:
    # A wall clock a test sets: utc_now() reads time.mktime(time.gmtime()), so mktime returns the setting.
    now = 1_000_000

    @staticmethod
    def gmtime() -> tuple[int, ...]:
        return (2001, 1, 1, 0, 0, 0, 0, 1)

    @staticmethod
    def mktime(_t: tuple[int, ...]) -> int:
        return _SteppedTime.now


def test_a_read_after_the_rtc_stepped_back_returns_a_negative_age() -> None:
    # Guard: the age is signed, so a clock set back after the write reads as negative (the caller treats
    # that as expired; SGP40's decision), and a forward step reads as the full span.
    manager, _chip = make_manager()
    run(setup_manager(manager))
    chunk = manager.get_timestamped_chunk(4, _synced, crc=CRC8(), owner="T1")
    assert chunk is not None
    original_time = asy_base_classes.time
    asy_base_classes.time = _SteppedTime  # type: ignore[assignment]
    try:
        with _UTCValid():
            _SteppedTime.now = 1_000_000
            assert run(chunk.write(b"data")) == (True, True, 1_000_000)
            _SteppedTime.now = 1_000_000 - 60
            back = run(chunk.read())
            _SteppedTime.now = 1_000_000 + 60
            forward = run(chunk.read())
    finally:
        asy_base_classes.time = original_time
    assert back == (1_000_000, -60, bytearray(b"data"))
    assert forward == (1_000_000, 60, bytearray(b"data"))


class _FakeMB85RS2MTA(FakeMB85RS64V):
    # dev's 256 KB part (MB85RS2MTA DS501-00032 p.10): its size and its identification.
    SIZE = 0x40000
    RDID = bytes([0x04, 0x7F, 0x48, 0x03])


class _PowerCut(BaseException):
    pass


class _CuttingChip(FakeMB85RS64V):
    # Test-local stand-in for the fake's cut_after_bytes knob: the power fails once that many data bytes have
    # landed; the write in progress keeps its leading part, then nothing more reaches the chip.
    cut_after: "int | None" = None

    def write(self, buf: object) -> None:
        data = bytes(buf)  # type: ignore[call-overload]
        if self.cut_after is not None and self._pending_op == 0x02 and self._pending_addr is not None:
            if len(data) > self.cut_after:
                if self.wel:
                    self.memory[self._pending_addr : self._pending_addr + self.cut_after] = data[: self.cut_after]
                self.cut_after = None
                raise _PowerCut
            self.cut_after -= len(data)
        super().write(buf)


def _manager_on(chip_class: "type[FakeMB85RS64V]") -> "tuple[FRAMManager, FakeMB85RS64V]":
    asy_spi_driver._SPI = chip_class  # type: ignore[misc]
    try:
        return make_manager(max_size=chip_class.SIZE)
    finally:
        asy_spi_driver._SPI = FakeMB85RS64V  # type: ignore[misc]


_LOGGERS = ("WIFI", "NTP", "SYSTEM")


def _logged_system(chip_class: "type[FakeMB85RS64V]", image: "bytearray | None" = None) -> "tuple[FRAMManager, FakeMB85RS64V, list[PrintLogHistoryStore]]":
    # A manager and three FRAM-backed loggers set up as the boot batch does them, over a copy of image.
    manager, chip = _manager_on(chip_class)
    if image is not None:
        chip.memory[:] = image
    stores = [PrintLogHistoryStore(manager, 10, None, name=name) for name in _LOGGERS]
    assert run(setup_manager(manager)) is True
    for store in stores:
        run(store.setup())
    return manager, chip, stores


def _filled_system(chip_class: "type[FakeMB85RS64V]") -> "tuple[FRAMManager, FakeMB85RS64V, list[PrintLogHistoryStore]]":
    manager, chip, stores = _logged_system(chip_class)
    for n, store in enumerate(stores):
        run(store.err_s("planted", errno=n + 1))
    chip.memory[manager._allocated_size :] = bytes([0xA5]) * (len(chip.memory) - manager._allocated_size)
    return manager, chip, stores


def _erase_and_record(chip_class: "type[FakeMB85RS64V]") -> "tuple[FakeMB85RS64V, list[int], int]":
    # One erase of a filled chip: the chip, the write summary [writes, next unit address, units in order (1/0),
    # last 1-byte write's index, first 256-byte write's index], and the step count. Fixed-size, so a 256 KB
    # chip's thousand writes never grow one list block (the coverage build's fragmented heap refused 16 KB).
    manager, chip, _stores = _filled_system(chip_class)
    summary = [0, 0, 1, -1, -1]
    steps = [0]
    original_sync = manager.fram.set_values_sync

    def recording(buf: bytes | bytearray | memoryview, addr_start: int) -> int:
        if len(buf) == 256:
            summary[2] &= int(addr_start == summary[1])
            summary[1] += 256
            if summary[4] < 0:
                summary[4] = summary[0]
        elif len(buf) == 1:
            summary[3] = summary[0]
        summary[0] += 1
        return original_sync(buf, addr_start)

    def step() -> None:
        steps[0] += 1

    manager.fram.set_values_sync = recording  # type: ignore[method-assign]
    assert run(manager.erase_chip(step)) is True
    return chip, summary, steps[0]


def test_erase_chip_zeroes_every_byte_in_ascending_units() -> None:
    for chip_class in (FakeMB85RS64V, _FakeMB85RS2MTA):
        chip, summary, steps = _erase_and_record(chip_class)
        _writes, next_unit, in_order, last_status, first_unit = summary
        zero = bytes(256)  # compared a unit at a time: a whole-chip zero buffer is one 256 KB block
        assert all(chip.memory[unit : unit + 256] == zero for unit in range(0, chip_class.SIZE, 256))
        assert (in_order, next_unit) == (1, chip_class.SIZE)  # 256-byte units from 0 upward, every one of them
        assert 0 <= last_status < first_unit  # every chunk blanked before the first byte is zeroed
        assert steps == len(_LOGGERS) + chip_class.SIZE // 256


def test_an_erased_chip_boots_like_a_new_one() -> None:
    manager, chip, _stores = _filled_system(FakeMB85RS64V)
    assert run(manager.erase_chip(lambda: None)) is True
    fresh, _chip, stores = _logged_system(FakeMB85RS64V, chip.memory)
    for store in stores:
        assert store.initialized is True
        assert store.restored is False
        assert run(store.get_log())[store.name]["ErrCount"] == 0
    assert "E" not in run(fresh.get_error_counter())["FRAM"]["ErrType"]


def test_an_all_zero_block_never_validates_even_with_an_idle_status() -> None:
    # What the erase leaves, with a status byte flipped to idle: an owner-seeded CRC is never zero over zeros.
    for crc in (CRC8(), CRC16(), CRC32()):
        manager, chip = make_manager()
        run(setup_manager(manager))
        chunk = manager.get_chunk(12, crc=crc, owner="SYSTEM")
        assert chunk is not None
        for addr in chunk._block_addr:
            status = addr + chunk.size + chunk.crc.length()
            chip.memory[addr:status] = bytes(status - addr)
            chip.memory[status] = _STATUS_IDLE
            chip.memory[status + 1] = _STATUS_IDLE
        assert run(chunk.read_into(chunk.get_buffer())) is not True


def test_erase_refuses_a_write_protected_or_uninitialised_chip() -> None:
    never_up, chip = make_manager()
    chip.memory[:] = bytes([0xA5]) * len(chip.memory)
    assert run(never_up.erase_ready()) is False
    assert run(never_up.erase_chip(lambda: None)) is False
    assert chip.memory == bytearray(bytes([0xA5]) * len(chip.memory))
    manager, chip, _stores = _filled_system(FakeMB85RS64V)
    stored = bytearray(chip.memory)
    assert run(manager.fram.set_write_protected(value=True)) is True
    assert run(manager.erase_ready()) is False
    assert run(manager.erase_chip(lambda: None)) is False
    assert chip.memory == stored
    assert run(manager.fram.set_write_protected(value=False)) is True
    manager.fram.lost.set()
    assert run(manager.erase_ready()) is False
    manager.fram.lost.clear()
    assert run(manager.erase_ready()) is True


def test_a_failed_invalidate_stops_before_pass_2() -> None:
    manager, chip, stores = _filled_system(FakeMB85RS64V)
    victim = stores[1].fram
    assert isinstance(victim, FRAMChunk)
    fail_set_values_at(victim, victim._block_addr[0] + victim.size + victim.crc.length())
    before = bytearray(chip.memory)
    assert run(manager.erase_chip(lambda: None)) is False
    assert chip.memory[manager._allocated_size :] == before[manager._allocated_size :]  # nothing zeroed


def _erase_cut_after(landed: int) -> "tuple[list[list[int]], bytearray]":
    # One erase whose power fails after `landed` data bytes; returns each logger's ring before and the image after.
    manager, chip, stores = _filled_system(_CuttingChip)
    assert isinstance(chip, _CuttingChip)
    rings = [list(store.history) for store in stores]
    chip.cut_after = landed

    async def erase() -> bool:
        try:
            await manager.erase_chip(lambda: None)
        except _PowerCut:
            return True
        return False

    assert run(erase()) is True, f"the power cut after {landed} bytes never came"
    return rings, bytearray(chip.memory)


def test_an_erase_cut_at_any_point_leaves_a_bootable_chip() -> None:
    # Pass 1 writes four status bytes per chunk; pass 2's first unit covers every allocated block. Each cut
    # boots into each ring exactly as it was or blank, with nothing but content findings in FRAM's log.
    probe, _chip, _stores = _filled_system(FakeMB85RS64V)
    pass_1 = 4 * len(_LOGGERS)
    assert probe._allocated_size <= 256
    cuts = list(range(pass_1)) + [pass_1, pass_1 + 128, pass_1 + 255]
    content = {code("E", "FRAM_STATUS_DISAGREE"), code("W", "FRAM_BLOCK_INVALID")}
    for landed in cuts:
        rings, image = _erase_cut_after(landed)
        manager, _chip, stores = _logged_system(FakeMB85RS64V, image)
        for n, store in enumerate(stores):
            assert store.initialized is True
            if store.restored:
                assert list(store.history) == rings[n], f"cut after {landed}: {store.name} restored a different ring"
            else:
                assert run(store.get_log())[store.name]["ErrCount"] == 0, f"cut after {landed}: {store.name}"
            run(store.err_s("after", errno=9))
            chunk = store.fram
            assert chunk is not None
            assert run(chunk.read_into(chunk.get_buffer())) is True, f"cut after {landed}: the next write did not land"
        logged = {num for num, _kind in _entries(run(manager.get_error_counter()))}
        assert logged <= content, f"cut after {landed}: {logged}"


def test_the_erase_blanks_every_chunk_before_it_zeroes_a_byte() -> None:
    manager, chip, stores = _filled_system(FakeMB85RS64V)
    seen: list[bytes] = []

    def after_each_step() -> None:
        if len(seen) < len(stores):
            statuses = b""
            for store in stores:
                chunk = store.fram
                assert isinstance(chunk, FRAMChunk)
                for addr in chunk._block_addr:
                    status = addr + chunk.size + chunk.crc.length()
                    statuses += bytes(chip.memory[status : status + 2])
            seen.append(statuses)

    assert run(manager.erase_chip(after_each_step)) is True
    assert seen[-1] == bytes(4 * len(stores))  # after pass 1, every block reads blank


def test_the_watch_task_waits_while_healthy_and_ends_on_a_loss() -> None:
    manager, chip = make_manager()
    assert manager.get_task_starters() == [manager.start_asy_watch_chip]  # always one, whatever the chip does
    assert manager.get_timer_starters() == []
    assert run(manager.setup()) is True

    async def turns(task: "asyncio.Task[None]") -> bool:
        for _ in range(5):
            await asyncio.sleep(0)
        return task.done()

    async def scenario() -> "tuple[bool, bool, bool, bool]":
        task = manager.start_asy_watch_chip()
        healthy = await turns(task)
        manager.fram.lost.set()
        ended = await turns(task)
        restarted = manager.start_asy_watch_chip()  # the chip answers again: set up anew, then waiting
        waiting = not await turns(restarted) and not manager.fram.lost.is_set()
        chip.rdid_response = bytes(4)  # lost for good: the next restart's setup fails and the task ends
        manager.fram.lost.set()
        gone = await turns(restarted)
        failed = await turns(manager.start_asy_watch_chip())
        return healthy, ended, waiting, gone and failed

    healthy, ended, waiting, gone = run(scenario())
    assert healthy is False  # still running while the chip is up
    assert ended is True
    assert waiting is True
    assert gone is True


def test_the_watch_task_ends_at_once_for_a_chip_never_set_up() -> None:
    # A declared chip that failed its boot setup escalates like any declared chip: its task ends at once.
    manager, chip = make_manager()
    chip.rdid_response = bytes([0xFF, 0xFF, 0xFF, 0xFF])
    assert run(manager.setup()) is False

    async def scenario() -> bool:
        task = manager.start_asy_watch_chip()
        for _ in range(3):
            await asyncio.sleep(0)
        return task.done()

    assert run(scenario()) is True


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
