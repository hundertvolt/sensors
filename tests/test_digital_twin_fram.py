"""Deterministic unit tests for digital_twin/_fram_chip.py's own SPI opcode protocol (WREN/WRDI/RDSR/WRSR/READ/WRITE/RDID) and JSON persistence - independently reimplemented, not sharing tests/_fram_chip_fake.py.
Also the chunk layer's tri-state read (asy_fram_manager.py) over that chip on the twin's own SPI bus."""

import asyncio
import json
import os
import sys

sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

import machine
from _error_codes import code
from _fram_chip import _PAGE_SIZE, FramChip
from _tmp_scratch import TmpScratch

import asy_base_classes
from asy_crc_checks import CRC8
from asy_fram_manager import FRAMManager
from asy_print_log import LogConfig
from asy_spi_driver import SPI

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import TypeVar

    from asy_fram_manager import FRAMChunk, FRAMTimestampedChunk

    T = TypeVar("T")

_OPCODE_WREN = 0x06
_OPCODE_WRDI = 0x04
_OPCODE_RDSR = 0x05
_OPCODE_WRSR = 0x01
_OPCODE_READ = 0x03
_OPCODE_WRITE = 0x02
_OPCODE_RDID = 0x9F

# The chunk layer's status-byte values (const() in asy_fram_manager.py, so not importable there).
_STATUS_IDLE = 0x01
_STATUS_BUSY = 0x02
_PAYLOAD = bytes(range(40))  # 41 bytes with its CRC8 byte: over the twin bus's 32-byte RX-overrun threshold
_FAULT_TIMES = 64  # more chip reads than one chunk read makes: the fault lasts until cleared

# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that module's
# own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage.
_scratch = TmpScratch("digital_twin_fram")


def _tmp_path(name: str) -> str:
    return _scratch.path(name)


def _rdsr(chip: FramChip) -> int:
    chip.write(bytes([_OPCODE_RDSR]))
    buf = bytearray(1)
    chip.readinto(buf)
    return buf[0]


def _rdid(chip: FramChip) -> bytes:
    chip.write(bytes([_OPCODE_RDID]))
    buf = bytearray(4)
    chip.readinto(buf)
    return bytes(buf)


def _wren(chip: FramChip) -> None:
    chip.write(bytes([_OPCODE_WREN]))


def _write_mem(chip: FramChip, addr: int, data: bytes) -> None:
    chip.write(bytes([_OPCODE_WRITE, (addr >> 8) & 0xFF, addr & 0xFF]))
    chip.write(data)


def _read_mem(chip: FramChip, addr: int, nbytes: int) -> bytes:
    chip.write(bytes([_OPCODE_READ, (addr >> 8) & 0xFF, addr & 0xFF]))
    buf = bytearray(nbytes)
    chip.readinto(buf)
    return bytes(buf)


# 24-bit-address variants of _write_mem()/_read_mem() above, matching src/asy_fram_driver.py's own
# _setup_addr_buffer() for a chip whose max_size exceeds _ADDR_16BIT_MAX (dev's 256KB MB85RS2MTA) -
# a 3-byte address (4-byte opcode+address header) instead of the 8KB chip's 2-byte address.
def _write_mem24(chip: FramChip, addr: int, data: bytes) -> None:
    chip.write(bytes([_OPCODE_WRITE, (addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF]))
    chip.write(data)


def _read_mem24(chip: FramChip, addr: int, nbytes: int) -> bytes:
    chip.write(bytes([_OPCODE_READ, (addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF]))
    buf = bytearray(nbytes)
    chip.readinto(buf)
    return bytes(buf)


def run(coro: "Coroutine[object, object, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


async def _synced() -> bool:
    return True


def _a_plan_with_an_8kb_fram_on_spi0() -> "dict[str, object]":
    # The device comes from the generated wiring plans, chosen by its FRAM, never by name: the twin wires
    # its chip by bus id, so spi0's pins 2/3/4 and CS 1 below drive it on any such device.
    for name in sorted(os.listdir("build/generated_src")):
        if name.endswith("_wiring_plan.json"):
            with open("build/generated_src/" + name) as f:
                raw = json.load(f)
            if not isinstance(raw, dict):
                continue
            plan: dict[str, object] = raw
            spi = plan.get("spi")
            fram = spi.get("spi0") if isinstance(spi, dict) else None
            if isinstance(fram, dict) and fram.get("driver") == "fram" and fram.get("max_size") == 0x2000:
                return plan
    raise AssertionError("no generated device declares an 8KB FRAM on spi0")


def _twin_manager() -> "tuple[FRAMManager, machine.SPI, FramChip]":
    machine.configure_wiring(_a_plan_with_an_8kb_fram_on_spi0())
    manager = FRAMManager(SPI(0, 2, 3, 4), 1, max_size=0x2000, log=LogConfig(None, 10, None))
    bus = manager.fram._spidev.spi._spi
    assert bus is not None
    assert bus.device is not None
    assert run(manager.setup()) is True
    return manager, bus, bus.device


def _chunks(manager: FRAMManager) -> "tuple[FRAMChunk, FRAMTimestampedChunk]":
    chunk = manager.get_chunk(len(_PAYLOAD), crc=CRC8(), owner="T1")
    ts_chunk = manager.get_timestamped_chunk(len(_PAYLOAD), _synced, crc=CRC8(), owner="T2")
    assert chunk is not None
    assert ts_chunk is not None
    return chunk, ts_chunk


def _status_bytes(chip: FramChip, chunk: "FRAMChunk | FRAMTimestampedChunk") -> list[int]:
    # Both status bytes of both copies; the layout is [data][crc][status 1][status 2] per copy.
    out = []
    for addr in chunk._block_addr:
        status = addr + chunk.size + chunk.crc.length()
        out += [chip.memory[status], chip.memory[status + 1]]
    return out


def _errnums(manager: FRAMManager) -> list[int]:
    return run(manager.get_error_counter())["FRAM"]["ErrNum"]


def test_rdid_reports_the_real_mb85rs64v_id_by_default() -> None:
    chip = FramChip(size=0x2000)
    assert _rdid(chip) == bytes([0x04, 0x7F, 0x03, 0x02])


def test_readinto_with_no_recognized_pending_op_zero_fills_the_buffer() -> None:
    # A readinto() with nothing recognized pending (never read/rdsr/rdid'd, or right after an
    # opcode like WREN/WRDI/WRSR/WRITE that doesn't itself arm a subsequent readinto()) still
    # behaves like a real bus transaction rather than raising - zero-filled, not garbage/untouched.
    chip = FramChip(size=0x2000)
    buf = bytearray([0xAA, 0xAA, 0xAA])
    chip.readinto(buf)
    assert bytes(buf) == bytes(3)
    _wren(chip)
    buf2 = bytearray([0xBB, 0xBB])
    chip.readinto(buf2)
    assert bytes(buf2) == bytes(2)


def test_write_requires_wren_first() -> None:
    chip = FramChip(size=0x2000)
    _write_mem(chip, 0x0000, b"\x11\x22")
    assert _read_mem(chip, 0x0000, 2) == b"\x00\x00"  # untouched - WEL was never set


def test_write_after_wren_persists_to_memory() -> None:
    chip = FramChip(size=0x2000)
    _wren(chip)
    _write_mem(chip, 0x0010, b"\xaa\xbb\xcc")
    assert _read_mem(chip, 0x0010, 3) == b"\xaa\xbb\xcc"


def test_wel_autoclears_after_a_write_so_a_second_write_needs_a_fresh_wren() -> None:
    chip = FramChip(size=0x2000)
    _wren(chip)
    _write_mem(chip, 0x0000, b"\x01")
    _write_mem(chip, 0x0001, b"\x02")  # no WREN in between
    assert _read_mem(chip, 0x0000, 2) == b"\x01\x00"


def test_wrdi_clears_wel() -> None:
    chip = FramChip(size=0x2000)
    _wren(chip)
    chip.write(bytes([_OPCODE_WRDI]))
    _write_mem(chip, 0x0000, b"\xff")
    assert _read_mem(chip, 0x0000, 1) == b"\x00"


def test_rdsr_reflects_wel_bit() -> None:
    chip = FramChip(size=0x2000)
    assert _rdsr(chip) & 0x02 == 0
    _wren(chip)
    assert _rdsr(chip) & 0x02 == 0x02


def test_read_returns_zero_bytes_for_untouched_memory() -> None:
    chip = FramChip(size=0x2000)
    assert _read_mem(chip, 0x1000, 4) == bytes(4)


def test_wrsr_requires_wel_and_preserves_the_wel_bit_itself() -> None:
    chip = FramChip(size=0x2000)
    chip.write(bytes([_OPCODE_WRSR, 0x08]))  # no WREN first - must be rejected
    assert _rdsr(chip) & 0x08 == 0
    _wren(chip)
    chip.write(bytes([_OPCODE_WRSR, 0x08]))
    status = _rdsr(chip)
    assert status & 0x08 == 0x08  # the new bit was written
    assert status & 0x02 == 0  # WEL auto-clears after WRSR recognition, same as after WRITE


def test_save_state_then_construct_a_fresh_chip_from_the_same_path_reads_back_identical_data() -> None:
    path = _tmp_path("fram_state.json")
    try:
        os.remove(path)
    except OSError:
        pass
    chip1 = FramChip(size=0x2000, state_path=path)
    _wren(chip1)
    _write_mem(chip1, 0x0042, b"\xde\xad\xbe\xef")
    chip1.save_state()

    chip2 = FramChip(size=0x2000, state_path=path)
    assert _read_mem(chip2, 0x0042, 4) == b"\xde\xad\xbe\xef"


def test_state_is_not_written_until_save_state_is_called() -> None:
    path = _tmp_path("fram_no_autosave.json")
    try:
        os.remove(path)
    except OSError:
        pass
    chip = FramChip(size=0x2000, state_path=path)
    _wren(chip)
    _write_mem(chip, 0x0000, b"\x01")
    try:
        with open(path):
            raise AssertionError("state file must not exist before an explicit save_state() call")
    except OSError:
        pass  # expected - nothing written yet


def test_persisted_file_is_json_with_hex_encoded_memory() -> None:
    path = _tmp_path("fram_format.json")
    chip = FramChip(size=0x10, state_path=path)
    _wren(chip)
    _write_mem(chip, 0x0000, b"\x99")
    chip.save_state()
    with open(path) as f:
        data = json.load(f)
    assert "memory_hex" in data
    assert bytes.fromhex(data["memory_hex"])[0] == 0x99


def test_save_state_round_trips_correctly_across_chunk_boundaries() -> None:
    # Regression test from baseline verification: save_state() used to build the whole memory image as one
    # giant hex string in a single allocation, which failed with a real MemoryError once the heap was
    # fragmented by a live system's churn - reproduced deterministically against this twin.
    #
    # The fix streams the write out in _SAVE_CHUNK_SIZE pieces. This test is not about fragmentation, which
    # no unit test reproduces deterministically, but about chunk-boundary correctness: every byte around and
    # across a boundary must still round-trip exactly.
    import _fram_chip

    path = _tmp_path("fram_chunk_boundary.json")
    size = _fram_chip._SAVE_CHUNK_SIZE * 3 + 7  # spans multiple chunks, last one partial
    chip1 = FramChip(size=size, state_path=path)
    _wren(chip1)
    # Distinct data at every chunk boundary (start/end of each _SAVE_CHUNK_SIZE-sized chunk) plus the
    # very first and very last byte of the whole buffer.
    boundaries = [0, size - 1]
    for n in range(1, 3):
        boundaries += [_fram_chip._SAVE_CHUNK_SIZE * n - 1, _fram_chip._SAVE_CHUNK_SIZE * n]
    for i, addr in enumerate(boundaries):
        _wren(chip1)  # WEL auto-clears after every write's data phase - must re-arm before each one
        _write_mem(chip1, addr, bytes([(i + 1) & 0xFF]))
    chip1.save_state()

    chip2 = FramChip(size=size, state_path=path)
    for i, addr in enumerate(boundaries):
        assert _read_mem(chip2, addr, 1) == bytes([(i + 1) & 0xFF])
    assert chip2.memory == chip1.memory


def test_load_state_with_no_memory_hex_marker_leaves_a_blank_chip_without_raising() -> None:
    # _load_state() hand-parses this project's own fixed file shape rather than using json.load()
    # (see save_state()'s own comment for why) - a malformed/unrecognized file (no "memory_hex": "
    # marker at all) must degrade to a blank chip, not raise.
    path = _tmp_path("fram_no_marker.json")
    with open(path, "w") as f:
        f.write('{"unexpected": "shape"}')
    chip = FramChip(size=0x10, state_path=path)  # must not raise
    assert _read_mem(chip, 0x0000, 4) == bytes(4)


def test_load_state_handles_a_truncated_file_without_raising() -> None:
    # Fewer hex digits than the chip's own size (a truncated/corrupted file) must leave the rest of
    # memory at its blank default rather than raising or reading past the available data.
    path = _tmp_path("fram_truncated.json")
    with open(path, "w") as f:
        f.write('{"size": 16, "memory_hex": "deadbeef"}')  # only 4 bytes' worth for a 16-byte chip
    chip = FramChip(size=16, state_path=path)  # must not raise
    assert _read_mem(chip, 0x0000, 4) == bytes.fromhex("deadbeef")
    assert _read_mem(chip, 0x0004, 4) == bytes(4)  # never-written tail stays blank


def test_load_state_handles_a_hex_byte_pair_straddling_a_chunk_boundary() -> None:
    # Regression test for the read-side chunked parse itself, _load_state()'s pending/piece stitching
    # mirroring save_state()'s fix on the read path: a hex byte pair split across two f.read() calls must
    # still decode to the right byte, not be silently dropped or misaligned.
    #
    # _LOAD_CHUNK_CHARS defaults to 1024, far larger than any size this test can afford to construct by
    # hand, so it is temporarily shrunk to 1 to force a straddle on almost every byte without a huge
    # fixture.
    import _fram_chip

    path = _tmp_path("fram_chunk_straddle.json")
    data = bytes(range(32))  # 32 distinct, order-sensitive bytes - any dropped/misaligned nibble
    # would show up as a mismatch somewhere in the full comparison below.
    with open(path, "w") as f:
        f.write('{"size": 32, "memory_hex": "' + data.hex() + '"}')

    original = _fram_chip._LOAD_CHUNK_CHARS
    _fram_chip._LOAD_CHUNK_CHARS = 1
    try:
        chip = FramChip(size=32, state_path=path)
    finally:
        _fram_chip._LOAD_CHUNK_CHARS = original
    assert _read_mem(chip, 0x0000, 32) == data


def test_missing_state_file_starts_from_a_blank_chip_without_raising() -> None:
    path = _tmp_path("fram_does_not_exist.json")
    try:
        os.remove(path)
    except OSError:
        pass
    chip = FramChip(size=0x2000, state_path=path)  # must not raise
    assert _read_mem(chip, 0x0000, 4) == bytes(4)


def test_fault_injection_on_write_and_readinto() -> None:
    chip = FramChip(size=0x2000)
    chip.fault.inject_fault("write", OSError(5, "no ACK"))
    try:
        _wren(chip)
        raise AssertionError("expected OSError")
    except OSError:
        pass
    _wren(chip)  # fault only fired once
    chip.fault.inject_fault("readinto", OSError(5, "timeout"))
    try:
        _read_mem(chip, 0x0000, 1)
        raise AssertionError("expected OSError")
    except OSError:
        pass


def test_24_bit_address_write_and_read_round_trip_correctly_on_a_256kb_chip() -> None:
    # A 256KB chip (dev's real MB85RS2MTA) sends a 3-byte address, so a 4-byte header, instead of the 8KB
    # chip's 2-byte one - being over _ADDR_16BIT_MAX, it exercises that path. A basic correctness check; the
    # next test shows why a single-address round trip alone cannot catch an aliasing bug.
    chip = FramChip(size=0x40000)
    _wren(chip)
    _write_mem24(chip, 0x0100, b"\xaa\xbb\xcc")
    assert _read_mem24(chip, 0x0100, 3) == b"\xaa\xbb\xcc"


def test_24_bit_address_low_byte_is_not_dropped_so_aliasing_addresses_stay_distinct() -> None:
    # SPECIFICATION.md Part L.4: _decode_addr() used to always read exactly 2 address bytes, silently
    # dropping the 256KB chip's true low-order byte, so a real address aliased to (addr >> 8) & 0xFF.
    #
    # Any two addresses sharing a high byte then collapsed onto one decoded address and a write to either
    # clobbered the other, corrupting unrelated FRAM chunks - discovered via a real digital-twin CI failure
    # against dev. This proves they now stay distinct.
    chip = FramChip(size=0x40000)
    _wren(chip)
    _write_mem24(chip, 0x0000, b"\x11")
    _wren(chip)
    _write_mem24(chip, 0x00FF, b"\x22")
    assert _read_mem24(chip, 0x0000, 1) == b"\x11"
    assert _read_mem24(chip, 0x00FF, 1) == b"\x22"


def test_16_bit_address_chip_is_unaffected_by_the_24_bit_address_path() -> None:
    # The size threshold (_ADDR_16BIT_MAX) must keep every existing 8KB-chip caller on the original
    # 2-byte decode - a regression here would silently break every non-dev device.
    chip = FramChip(size=0x2000)
    _wren(chip)
    _write_mem(chip, 0x0100, b"\xdd")
    assert _read_mem(chip, 0x0100, 1) == b"\xdd"


def test_a_256kb_chip_holds_its_memory_in_pages_never_one_large_block() -> None:
    # One 256KB bytearray needs a contiguous run a fragmented test heap may not have, even with most of
    # it free (a coverage run failed so with 15MB free). No page may exceed one page's size.
    chip = FramChip(size=0x40000)
    pages = chip.memory._pages
    assert len(pages) > 1, f"a 256KB chip still holds {len(pages)} block"
    assert all(len(page) <= _PAGE_SIZE for page in pages), [len(page) for page in pages if len(page) > _PAGE_SIZE]
    assert sum(len(page) for page in pages) == 0x40000


def test_paged_memory_reads_and_writes_like_the_bytearray_it_replaces() -> None:
    # Every access shape the twin and the tests use, across page boundaries, against a plain bytearray.
    size = 3 * _PAGE_SIZE + 17
    chip = FramChip(size=size)
    ref = bytearray(size)
    for start, data in ((0, b"\x01\x02"), (_PAGE_SIZE - 3, bytes(range(1, 9))), (2 * _PAGE_SIZE - 1, bytes(_PAGE_SIZE + 5)), (size - 4, b"\xfe\xfd\xfc\xfb")):
        chip.memory[start : start + len(data)] = data
        ref[start : start + len(data)] = data
    chip.memory[_PAGE_SIZE] ^= 0xFF
    ref[_PAGE_SIZE] ^= 0xFF
    assert len(chip.memory) == size
    assert chip.memory[_PAGE_SIZE] == ref[_PAGE_SIZE] == 4 ^ 0xFF  # byte 4 of range(1, 9), flipped
    assert chip.memory[_PAGE_SIZE - 5 : 2 * _PAGE_SIZE + 9] == ref[_PAGE_SIZE - 5 : 2 * _PAGE_SIZE + 9]
    assert chip.memory[size - 2 :] == ref[size - 2 :]
    assert bytes(chip.memory) == bytes(ref)
    other = FramChip(size=size)
    other.memory[0:size] = ref
    assert chip.memory == other.memory


def test_a_write_past_the_chip_end_is_refused_not_grown() -> None:
    # A bytearray slice assignment past its end would grow the chip; the paged memory refuses instead.
    chip = FramChip(size=_PAGE_SIZE)
    try:
        chip.memory[_PAGE_SIZE - 1 : _PAGE_SIZE + 1] = b"\x01\x02"
        raise AssertionError("expected IndexError")
    except IndexError:
        pass
    assert len(chip.memory) == _PAGE_SIZE


def test_a_chunk_on_the_twin_chip_reads_true_with_the_bytes_it_wrote() -> None:
    # True: valid data, in the caller's buffer. A read marks each copy busy and back idle, so it leaves the chip as it was.
    manager, _bus, chip = _twin_manager()
    chunk, _ts_chunk = _chunks(manager)
    assert run(chunk.write(_PAYLOAD)) is True
    stored = bytes(chip.memory)
    buf = chunk.get_buffer()
    assert run(chunk.read_into(buf)) is True
    assert bytes(buf.get_data_buf() or b"") == _PAYLOAD
    assert bytes(chip.memory) == stored
    assert _status_bytes(chip, chunk) == [_STATUS_IDLE] * 4


def test_a_blank_chunk_reads_false_and_takes_no_busy_marker() -> None:
    # False: nothing valid stored. A blank copy is never read, so the read marks nothing and logs nothing.
    manager, _bus, chip = _twin_manager()
    chunk, ts_chunk = _chunks(manager)
    assert run(chunk.read_into(chunk.get_buffer())) is False
    assert run(ts_chunk.read_into(ts_chunk.get_buffer())) == (False, None, None)
    assert bytes(chip.memory) == bytes(len(chip.memory)), "a blank read wrote to the chip"
    assert run(manager.get_error_counter())["FRAM"]["ErrCount"] == 0


def test_a_persistent_chip_read_fault_reads_none_and_leaves_the_chip_untouched() -> None:
    # None: nothing could be read. Every read clocked out of the chip fails, its status bytes included, so no
    # copy is marked or repaired, and the stored bytes read back whole once the fault clears.
    manager, _bus, chip = _twin_manager()
    chunk, _ts_chunk = _chunks(manager)
    assert run(chunk.write(_PAYLOAD)) is True
    stored = bytes(chip.memory)
    chip.fault.inject_fault("readinto", OSError(5, "chip read fault"), times=_FAULT_TIMES)
    buf = chunk.get_buffer()
    assert run(chunk.read_into(buf)) is None
    chip.fault.clear()
    assert bytes(chip.memory) == stored, "a faulted read changed the chip"
    assert code("E", "UNEXPECTED") in _errnums(manager)
    assert run(chunk.read_into(buf)) is True
    assert bytes(buf.get_data_buf() or b"") == _PAYLOAD


def test_a_persistent_overrun_reads_none_then_the_leftover_busy_markers_read_false() -> None:
    # The overrun fails each payload read after its busy marker landed: None, payload kept. Once the bus
    # recovers, both copies still carry the marker, so nothing valid is stored: False, writing nothing, until a write.
    manager, bus, chip = _twin_manager()
    chunk, _ts_chunk = _chunks(manager)
    assert run(chunk.write(_PAYLOAD)) is True
    bus.rx_overrun = True
    assert run(chunk.read_into(chunk.get_buffer())) is None
    bus.rx_overrun = False
    assert _status_bytes(chip, chunk) == [_STATUS_BUSY] * 4
    for addr in chunk._block_addr:
        assert bytes(chip.memory[addr : addr + len(_PAYLOAD)]) == _PAYLOAD
    left = bytes(chip.memory)
    assert run(chunk.read_into(chunk.get_buffer())) is False
    assert bytes(chip.memory) == left, "reading a leftover busy marker changed the chip"
    assert code("E", "FRAM_STATUS_BYTE") in _errnums(manager)
    assert run(chunk.write(_PAYLOAD)) is True
    buf = chunk.get_buffer()
    assert run(chunk.read_into(buf)) is True
    assert bytes(buf.get_data_buf() or b"") == _PAYLOAD


def test_the_timestamped_chunk_read_carries_the_same_tri_state() -> None:
    # The first element is the plain read's tri-state; the timestamp and its age come only with True.
    manager, bus, chip = _twin_manager()
    _chunk, ts_chunk = _chunks(manager)
    asy_base_classes.set_utc_valid()
    try:
        ok, synced, written_ts = run(ts_chunk.write(_PAYLOAD))
        assert ok is True
        assert synced is True
        buf = ts_chunk.get_buffer()
        valid, ts, age = run(ts_chunk.read_into(buf))
        assert valid is True
        assert ts == written_ts
        assert age is not None
        assert age >= 0
        assert bytes(buf.get_data_buf() or b"") == _PAYLOAD
        stored = bytes(chip.memory)
        chip.fault.inject_fault("readinto", OSError(5, "chip read fault"), times=_FAULT_TIMES)
        assert run(ts_chunk.read_into(ts_chunk.get_buffer())) == (None, None, None)
        chip.fault.clear()
        assert bytes(chip.memory) == stored, "a faulted read changed the chip"
        bus.rx_overrun = True
        assert run(ts_chunk.read_into(ts_chunk.get_buffer())) == (None, None, None)
        bus.rx_overrun = False
        assert run(ts_chunk.read_into(ts_chunk.get_buffer())) == (False, None, None)
    finally:
        asy_base_classes.set_utc_valid(valid=False)


def test_every_chunk_operation_stays_silent_on_the_twin_while_the_chip_is_lost() -> None:
    # While the driver's loss flag stands, no chunk operation reaches the bus, the chip or the log.
    manager, bus, chip = _twin_manager()
    chunk, ts_chunk = _chunks(manager)
    assert run(chunk.write(_PAYLOAD)) is True
    stored = bytes(chip.memory)
    traffic = list(bus.log)
    manager.fram.lost.set()
    assert run(chunk.write(b"else")) is False
    assert run(chunk.read_into(chunk.get_buffer())) is None
    assert run(chunk.clear()) is False
    assert run(chunk.invalidate()) is False
    assert run(ts_chunk.write(b"else"))[0] is False
    assert run(ts_chunk.read_into(ts_chunk.get_buffer())) == (None, None, None)
    assert list(bus.log) == traffic, "a chunk operation reached the bus while the chip was lost"
    assert bytes(chip.memory) == stored
    assert run(manager.get_error_counter())["FRAM"]["ErrCount"] == 0


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
