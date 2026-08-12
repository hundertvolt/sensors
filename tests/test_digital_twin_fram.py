"""Deterministic unit tests for digital_twin/_fram_chip.py's own SPI opcode protocol and JSON
persistence - independently reimplements the MB85RS64V opcode shapes tests/_fram_chip_fake.py
already establishes for unit tests (WREN/WRDI/RDSR/WRSR/READ/WRITE/RDID - confirmed directly against
src/asy_fram_driver.py's FRAM_SPI, the same source that fixture is built from), but as its own
independent module (FINAL_WIRING_PLAN.md's Step 3 - digital_twin/ never imports tests/machine.py or
tests/_fram_chip_fake.py), plus save_state()/load persistence the unit-test fixture doesn't need.
"""

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
