"""Deterministic unit tests for digital_twin/_fram_chip.py's own SPI opcode protocol (WREN/WRDI/RDSR/WRSR/READ/WRITE/RDID) and JSON persistence - independently reimplemented, not sharing tests/_fram_chip_fake.py."""

import json
import os
import sys

sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

from _fram_chip import FramChip  # noqa: E402

_OPCODE_WREN = 0x06
_OPCODE_WRDI = 0x04
_OPCODE_RDSR = 0x05
_OPCODE_WRSR = 0x01
_OPCODE_READ = 0x03
_OPCODE_WRITE = 0x02
_OPCODE_RDID = 0x9F

_TMP_DIR = "tests/_tmp"


def _tmp_path(name: str) -> str:
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass
    return _TMP_DIR + "/" + name


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
    # Regression test from baseline verification: save_state()
    # used to build the whole memory image as one giant bytes(self.memory).hex() string in a single
    # allocation, which failed with a real MemoryError once the heap got fragmented by a live
    # system's normal churn (reproduced deterministically running the real assembled system against
    # this twin - see _fram_chip.py's own _SAVE_CHUNK_SIZE comment). The fix streams the write out in
    # _SAVE_CHUNK_SIZE-byte pieces instead; this test isn't about fragmentation itself (not
    # reproducible deterministically in a unit test), it's about chunk-boundary correctness - every
    # byte around and across a chunk boundary must still round-trip exactly, not just the bulk data.
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
    # Regression test for the read-side chunked parse itself (_load_state()'s own pending/piece
    # stitching, mirroring save_state()'s _SAVE_CHUNK_SIZE fix on the read path) - a hex byte pair
    # split across two f.read() calls must still decode to the right byte, not get silently
    # dropped or misaligned. _LOAD_CHUNK_CHARS defaults to 1024, far larger than any size this
    # test can afford to construct by hand - temporarily shrunk to 1 to force a straddle on
    # (almost) every single byte, deterministically, without needing a huge fixture.
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


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
