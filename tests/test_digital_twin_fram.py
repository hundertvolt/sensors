"""Deterministic unit tests for digital_twin/_fram_chip.py's own SPI opcode protocol (WREN/WRDI/RDSR/WRSR/READ/WRITE/RDID) and JSON persistence - independently reimplemented, not sharing tests/_fram_chip_fake.py.
Also the chunk layer's tri-state read (asy_fram_manager.py) over that chip on the twin's own SPI bus."""

import asyncio
import errno
import json
import os
import sys

sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why
sys.path.insert(0, "digital_twin/unixport")  # the UDP shim's directory (digital_twin/README.md "_unix_port_udp_addr_shim.py")

from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from unix_port_poll_prewarm import prewarm_poll_set

prewarm_poll_set()  # before any poll object is registered: one test boots a whole device (digital_twin/README.md "Known gaps")
patch_asy_udp_socket_for_unix_port()  # before any UDPSocket is constructed (digital_twin/README.md "_unix_port_udp_addr_shim.py")

import _fram_chip  # noqa: E402 - imported after the prewarm and the UDP shim
import machine  # noqa: E402 - imported after the prewarm and the UDP shim
import microtest  # noqa: E402 - imported after the prewarm and the UDP shim
import network  # noqa: E402 - imported after the prewarm and the UDP shim
from _async_harness import cancel, run  # noqa: E402 - imported after the prewarm and the UDP shim
from _digital_twin_construction_scenarios import load_device  # noqa: E402 - imported after the prewarm and the UDP shim
from _error_codes import code  # noqa: E402 - imported after the prewarm and the UDP shim
from _fast_sleep import FastAsyncSleep  # noqa: E402 - imported after the prewarm and the UDP shim
from _fram_chip import _PAGE_SIZE, FRAMChip  # noqa: E402 - imported after the prewarm and the UDP shim
from _generated_module import boot_generated  # noqa: E402 - imported after the prewarm and the UDP shim
from _src_const import src_const  # noqa: E402 - imported after the prewarm and the UDP shim
from _task_names import task_name  # noqa: E402 - imported after the prewarm and the UDP shim
from _tmp_scratch import TmpScratch  # noqa: E402 - imported after the prewarm and the UDP shim
from _twin_devices import device_with, wiring_plan  # noqa: E402 - imported after the prewarm and the UDP shim

import asy_base_classes  # noqa: E402 - imported after the prewarm and the UDP shim
import asy_fram_driver  # noqa: E402 - imported after the prewarm and the UDP shim
from asy_crc_checks import CRC8  # noqa: E402 - imported after the prewarm and the UDP shim
from asy_fram_manager import FRAMManager  # noqa: E402 - imported after the prewarm and the UDP shim
from asy_print_log import LogConfig, PrintLogHistoryStore  # noqa: E402 - imported after the prewarm and the UDP shim
from asy_spi_driver import SPI  # noqa: E402 - imported after the prewarm and the UDP shim

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import TypeVar

    from asy_fram_driver import FRAM_SPI
    from asy_fram_manager import FRAMChunk, FRAMTimestampedChunk

    T = TypeVar("T")

_OPCODE_WREN = 0x06
_OPCODE_WRDI = 0x04
_OPCODE_RDSR = 0x05
_OPCODE_WRSR = 0x01
_OPCODE_READ = 0x03
_OPCODE_WRITE = 0x02
_OPCODE_RDID = 0x9F
_MB85RS64V_RDID = bytes([0x04, 0x7F, 0x03, 0x02])  # MB85RS64V datasheet p.10
_MB85RS2MTA_RDID = bytes([0x04, 0x7F, 0x48, 0x03])  # Fujitsu, continuation code, product ID 0x4803 (DS501-00032-3v0-E p10)

_STATUS_IDLE = src_const("src/asy_fram_manager.py", "_STATUS_IDLE")
_STATUS_BUSY = src_const("src/asy_fram_manager.py", "_STATUS_BUSY")
_PAYLOAD = bytes(range(40))  # 41 bytes with its CRC8 byte: over the twin bus's 32-byte RX-overrun threshold
_FAULT_TIMES = 64  # more chip reads than one chunk read makes: the fault lasts until cleared
# @tunable l2.fram_booted_until_yields = 2000
_UNTIL_YIELDS = 2000

# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that module's
# own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage.
_scratch = TmpScratch("digital_twin_fram")
microtest.after_each(machine.reset_test_state)
microtest.after_each(network.reset_test_state)


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


def _chunks(manager: FRAMManager) -> "tuple[FRAMChunk, FRAMTimestampedChunk]":
    chunk = manager.get_chunk(len(_PAYLOAD), crc=CRC8(), owner="T1")
    ts_chunk = manager.get_timestamped_chunk(len(_PAYLOAD), _synced, crc=CRC8(), owner="T2")
    assert chunk is not None
    assert ts_chunk is not None
    return chunk, ts_chunk


def _errnums(manager: FRAMManager) -> list[int]:
    return run(manager.get_error_counter())["FRAM"]["ErrNum"]


async def _lose(fram: "FRAM_SPI", chip: FRAMChip) -> None:
    # The chip goes silent; two refused writes in a row make the driver probe its RDID and find the loss.
    chip.silent = True
    for _ in range(2):
        async with fram:
            assert await fram.set_values(b"\x01\x02", chip.size - 2) is False
    assert fram.lost.is_set()


def _rdid(chip: FRAMChip) -> bytes:
    chip.write(bytes([_OPCODE_RDID]))
    buf = bytearray(4)
    chip.readinto(buf)
    return bytes(buf)


def _rdsr(chip: FRAMChip) -> int:
    chip.write(bytes([_OPCODE_RDSR]))
    buf = bytearray(1)
    chip.readinto(buf)
    return buf[0]


def _read_mem(chip: FRAMChip, addr: int, nbytes: int) -> bytes:
    chip.write(bytes([_OPCODE_READ, (addr >> 8) & 0xFF, addr & 0xFF]))
    buf = bytearray(nbytes)
    chip.readinto(buf)
    return bytes(buf)


def _read_mem24(chip: FRAMChip, addr: int, nbytes: int) -> bytes:
    chip.write(bytes([_OPCODE_READ, (addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF]))
    buf = bytearray(nbytes)
    chip.readinto(buf)
    return bytes(buf)


def _status_bytes(chip: FRAMChip, chunk: "FRAMChunk | FRAMTimestampedChunk") -> list[int]:
    # Both status bytes of both copies; the layout is [data][crc][status 1][status 2] per copy.
    out = []
    for addr in chunk._block_addr:
        status = addr + chunk.size + chunk.crc.length()
        out += [chip.memory[status], chip.memory[status + 1]]
    return out


async def _synced() -> bool:
    return True


def _tmp_path(name: str) -> str:
    return _scratch.path(name)


def _twin_manager(status: int = 0x00) -> "tuple[FRAMManager, machine.SPI, FRAMChip]":
    # The chip's status register is set before the manager's setup() reads it.
    machine.reset_peripherals()
    machine.configure_wiring(_a_plan_with_an_8kb_fram_on_spi0())
    manager = FRAMManager(SPI(0, 2, 3, 4), 1, max_size=0x2000, log=LogConfig(None, 10, None))
    bus = manager.fram._spidev.spi._spi
    assert bus is not None
    assert bus.device is not None
    bus.device.status = status
    assert run(manager.setup()) is True
    return manager, bus, bus.device


async def _until(what: str, condition: "Callable[[], bool]") -> None:
    # Polls on scheduler yields (the sleeps are fast), bounded by a tagged number of them.
    for _ in range(_UNTIL_YIELDS):
        if condition():
            return
        await asyncio.sleep(0)
    raise AssertionError(f"{what}: not within {_UNTIL_YIELDS} scheduler yields")


def _wren(chip: FRAMChip) -> None:
    chip.write(bytes([_OPCODE_WREN]))


def _write_mem(chip: FRAMChip, addr: int, data: bytes) -> None:
    chip.write(bytes([_OPCODE_WRITE, (addr >> 8) & 0xFF, addr & 0xFF]))
    chip.write(data)


# 24-bit-address variants of _write_mem()/_read_mem() above, matching src/asy_fram_driver.py's own
# _setup_addr_buffer() for a chip whose max_size exceeds _ADDR_16BIT_MAX (dev's 256KB MB85RS2MTA) -
# a 3-byte address (4-byte opcode+address header) instead of the 8KB chip's 2-byte address.
def _write_mem24(chip: FRAMChip, addr: int, data: bytes) -> None:
    chip.write(bytes([_OPCODE_WRITE, (addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF]))
    chip.write(data)


class _PrintRecorder:
    # Shadows print() inside _fram_chip only, recording each line's arguments; leaving the block removes the shadow.
    def __enter__(self) -> "list[tuple[object, ...]]":
        lines: list[tuple[object, ...]] = []
        _fram_chip.print = lambda *args: lines.append(args)  # type: ignore[attr-defined]  # a module-global shadow of the builtin
        return lines

    def __exit__(self, *_exc_info: object) -> None:
        del _fram_chip.print  # type: ignore[attr-defined]


class _RenameFailsOs:
    # Stands in for os inside _fram_chip: the rename that publishes a save fails, as a process killed there would.
    def rename(self, _old: str, _new: str) -> None:
        raise OSError(errno.EIO, "planted rename failure")


def test_rdid_reports_the_id_it_was_built_with() -> None:
    assert _rdid(FRAMChip(0x2000, _MB85RS64V_RDID)) == _MB85RS64V_RDID
    assert _rdid(FRAMChip(0x40000, _MB85RS2MTA_RDID)) == _MB85RS2MTA_RDID


def test_a_chip_needs_its_rdid_given() -> None:
    try:
        FRAMChip(0x2000)  # type: ignore[call-arg]
        raise AssertionError("expected TypeError: rdid_response has no default")
    except TypeError:
        pass


def test_rdid_once_answers_the_next_rdid_only() -> None:
    chip = FRAMChip(0x2000, _MB85RS64V_RDID)
    chip.rdid_once = bytes(4)
    assert _rdid(chip) == bytes(4)
    assert _rdid(chip) == _MB85RS64V_RDID


def test_drop_next_wren_drops_that_many_wrens_and_no_more() -> None:
    chip = FRAMChip(0x2000, _MB85RS64V_RDID)
    chip.drop_next_wren = 1
    _wren(chip)
    assert not _rdsr(chip) & 0x02
    _write_mem(chip, 0x0010, b"\xaa")
    assert _read_mem(chip, 0x0010, 1) == b"\x00"
    assert chip.drop_next_wren == 0
    _wren(chip)
    assert _rdsr(chip) & 0x02
    _write_mem(chip, 0x0010, b"\xaa")
    assert _read_mem(chip, 0x0010, 1) == b"\xaa"


def test_a_silent_chip_reads_zeros_and_ignores_every_write() -> None:
    chip = FRAMChip(0x2000, _MB85RS64V_RDID)
    _wren(chip)
    _write_mem(chip, 0x0020, b"\x5a\x5b")
    chip.silent = True
    assert _rdid(chip) == bytes(4)
    assert _read_mem(chip, 0x0020, 2) == bytes(2)
    _wren(chip)
    _write_mem(chip, 0x0020, b"\x01\x02")
    chip.silent = False
    assert not _rdsr(chip) & 0x02  # the WREN sent while silent never reached the chip
    assert _read_mem(chip, 0x0020, 2) == b"\x5a\x5b"


def test_write_fault_injection_is_refused() -> None:
    # rp2 SPI writes never raise (ports/rp2/machine_spi.c:312-315).
    chip = FRAMChip(0x2000, _MB85RS64V_RDID)
    try:
        chip.fault.inject_fault("write", OSError, errno.EIO, "planted")
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert str(e).startswith("'write' cannot raise on this bus (rp2) - "), str(e)
    assert chip.fault.pending("write") == 0


def test_readinto_with_no_recognized_pending_op_zero_fills_the_buffer() -> None:
    # A readinto() with nothing recognized pending (never read/rdsr/rdid'd, or right after an
    # opcode like WREN/WRDI/WRSR/WRITE that doesn't itself arm a subsequent readinto()) still
    # behaves like a real bus transaction rather than raising - zero-filled, not garbage/untouched.
    chip = FRAMChip(0x2000, _MB85RS64V_RDID)
    buf = bytearray([0xAA, 0xAA, 0xAA])
    chip.readinto(buf)
    assert bytes(buf) == bytes(3)
    _wren(chip)
    buf2 = bytearray([0xBB, 0xBB])
    chip.readinto(buf2)
    assert bytes(buf2) == bytes(2)


def test_write_requires_wren_first() -> None:
    chip = FRAMChip(0x2000, _MB85RS64V_RDID)
    _write_mem(chip, 0x0000, b"\x11\x22")
    assert _read_mem(chip, 0x0000, 2) == b"\x00\x00"  # untouched - WEL was never set


def test_write_after_wren_persists_to_memory() -> None:
    chip = FRAMChip(0x2000, _MB85RS64V_RDID)
    _wren(chip)
    _write_mem(chip, 0x0010, b"\xaa\xbb\xcc")
    assert _read_mem(chip, 0x0010, 3) == b"\xaa\xbb\xcc"


def test_wel_autoclears_after_a_write_so_a_second_write_needs_a_fresh_wren() -> None:
    chip = FRAMChip(0x2000, _MB85RS64V_RDID)
    _wren(chip)
    _write_mem(chip, 0x0000, b"\x01")
    _write_mem(chip, 0x0001, b"\x02")  # no WREN in between
    assert _read_mem(chip, 0x0000, 2) == b"\x01\x00"


def test_wrdi_clears_wel() -> None:
    chip = FRAMChip(0x2000, _MB85RS64V_RDID)
    _wren(chip)
    chip.write(bytes([_OPCODE_WRDI]))
    _write_mem(chip, 0x0000, b"\xff")
    assert _read_mem(chip, 0x0000, 1) == b"\x00"


def test_rdsr_reflects_wel_bit() -> None:
    chip = FRAMChip(0x2000, _MB85RS64V_RDID)
    assert _rdsr(chip) & 0x02 == 0
    _wren(chip)
    assert _rdsr(chip) & 0x02 == 0x02


def test_read_returns_zero_bytes_for_untouched_memory() -> None:
    chip = FRAMChip(0x2000, _MB85RS64V_RDID)
    assert _read_mem(chip, 0x1000, 4) == bytes(4)


def test_wrsr_requires_wel_and_preserves_the_wel_bit_itself() -> None:
    chip = FRAMChip(0x2000, _MB85RS64V_RDID)
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
    chip1 = FRAMChip(0x2000, _MB85RS64V_RDID, state_path=path)
    _wren(chip1)
    _write_mem(chip1, 0x0042, b"\xde\xad\xbe\xef")
    chip1.save_state()

    chip2 = FRAMChip(0x2000, _MB85RS64V_RDID, state_path=path)
    assert _read_mem(chip2, 0x0042, 4) == b"\xde\xad\xbe\xef"


def test_state_is_not_written_until_save_state_is_called() -> None:
    path = _tmp_path("fram_no_autosave.json")
    try:
        os.remove(path)
    except OSError:
        pass
    chip = FRAMChip(0x2000, _MB85RS64V_RDID, state_path=path)
    _wren(chip)
    _write_mem(chip, 0x0000, b"\x01")
    try:
        with open(path):
            raise AssertionError("state file must not exist before an explicit save_state() call")
    except OSError:
        pass  # expected - nothing written yet


def test_persisted_file_is_json_with_hex_encoded_memory() -> None:
    path = _tmp_path("fram_format.json")
    chip = FRAMChip(0x10, _MB85RS64V_RDID, state_path=path)
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
    path = _tmp_path("fram_chunk_boundary.json")
    size = _fram_chip._SAVE_CHUNK_SIZE * 3 + 7  # spans multiple chunks, last one partial
    chip1 = FRAMChip(size, _MB85RS64V_RDID, state_path=path)
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

    chip2 = FRAMChip(size, _MB85RS64V_RDID, state_path=path)
    for i, addr in enumerate(boundaries):
        assert _read_mem(chip2, addr, 1) == bytes([(i + 1) & 0xFF])
    assert chip2.memory == chip1.memory


def test_load_state_with_no_memory_hex_marker_says_so_and_leaves_a_blank_chip() -> None:
    # _load_state() hand-parses this project's own fixed file shape (save_state()'s comment says why).
    path = _tmp_path("fram_no_marker.json")
    with open(path, "w") as f:
        f.write('{"unexpected": "shape"}')
    with _PrintRecorder() as lines:
        chip = FRAMChip(0x10, _MB85RS64V_RDID, state_path=path)  # must not raise
    assert lines == [("FRAM state", path, "not loaded (marker): starting from a factory-fresh chip")], lines
    assert _read_mem(chip, 0x0000, 4) == bytes(4)


def test_a_truncated_state_file_says_so_and_keeps_none_of_its_partial_bytes() -> None:
    path = _tmp_path("fram_truncated.json")
    with open(path, "w") as f:
        f.write('{"size": 16, "memory_hex": "deadbeef"}')  # only 4 bytes' worth for a 16-byte chip
    with _PrintRecorder() as lines:
        chip = FRAMChip(16, _MB85RS64V_RDID, state_path=path)  # must not raise
    assert lines == [("FRAM state", path, "not loaded (truncated): starting from a factory-fresh chip")], lines
    assert _read_mem(chip, 0x0000, 16) == bytes(16)


def test_a_state_file_of_the_other_chip_size_says_so_and_loads_blank() -> None:
    path = _tmp_path("fram_other_size.json")
    small = FRAMChip(0x2000, _MB85RS64V_RDID, state_path=path)
    _wren(small)
    _write_mem(small, 0x0000, b"\x11\x22")
    small.save_state()
    with _PrintRecorder() as lines:
        big = FRAMChip(0x40000, _MB85RS2MTA_RDID, state_path=path)
    assert lines == [("FRAM state", path, "not loaded (size): starting from a factory-fresh chip")], lines
    assert _read_mem24(big, 0x0000, 2) == bytes(2)


def test_a_save_leaves_no_temporary_file_and_a_cut_save_keeps_the_previous_image() -> None:
    path = _tmp_path("fram_atomic.json")
    chip = FRAMChip(0x10, _MB85RS64V_RDID, state_path=path)
    _wren(chip)
    _write_mem(chip, 0x0000, b"\x5a")
    chip.save_state()
    try:
        os.stat(path + ".tmp")
        raise AssertionError("save_state() left its temporary file behind")
    except OSError:
        pass
    with open(path) as f:
        before = f.read()
    _wren(chip)
    _write_mem(chip, 0x0000, b"\xa5")
    real_os = _fram_chip.os  # type: ignore[attr-defined]  # the module's own os import, patched below
    _fram_chip.os = _RenameFailsOs()  # type: ignore[assignment, attr-defined]  # the process dies between the stream and the rename
    try:
        chip.save_state()
        raise AssertionError("expected the planted rename failure")
    except OSError:
        pass
    finally:
        _fram_chip.os = real_os  # type: ignore[attr-defined]
    with open(path) as f:
        assert f.read() == before


def test_load_state_handles_a_hex_byte_pair_straddling_a_chunk_boundary() -> None:
    # Regression test for the read-side chunked parse itself, _load_state()'s pending/piece stitching
    # mirroring save_state()'s fix on the read path: a hex byte pair split across two f.read() calls must
    # still decode to the right byte, not be silently dropped or misaligned.
    #
    # _LOAD_CHUNK_CHARS defaults to 1024, far larger than any size this test can afford to construct by
    # hand, so it is temporarily shrunk to 1 to force a straddle on almost every byte without a huge
    # fixture.
    path = _tmp_path("fram_chunk_straddle.json")
    data = bytes(range(32))  # 32 distinct, order-sensitive bytes - any dropped/misaligned nibble
    # would show up as a mismatch somewhere in the full comparison below.
    with open(path, "w") as f:
        f.write('{"size": 32, "memory_hex": "' + data.hex() + '"}')

    original = _fram_chip._LOAD_CHUNK_CHARS
    _fram_chip._LOAD_CHUNK_CHARS = 1
    try:
        chip = FRAMChip(32, _MB85RS64V_RDID, state_path=path)
    finally:
        _fram_chip._LOAD_CHUNK_CHARS = original
    assert _read_mem(chip, 0x0000, 32) == data


def test_missing_state_file_starts_from_a_blank_chip_without_a_line() -> None:
    path = _tmp_path("fram_does_not_exist.json")
    try:
        os.remove(path)
    except OSError:
        pass
    with _PrintRecorder() as lines:
        chip = FRAMChip(0x2000, _MB85RS64V_RDID, state_path=path)  # must not raise
    assert lines == []  # a first launch has no file: nothing to report
    assert _read_mem(chip, 0x0000, 4) == bytes(4)


def test_a_readinto_fault_keyed_to_the_read_opcode_spares_a_long_rdid_read() -> None:
    chip = FRAMChip(0x2000, _MB85RS64V_RDID)
    chip.fault.inject_fault("readinto", OSError, errno.EIO, "read", match=_OPCODE_READ)
    chip.write(bytes([_OPCODE_RDID]))
    chip.readinto(bytearray(32))
    assert chip.fault.pending("readinto") == 1
    try:
        _read_mem(chip, 0x0000, 32)
        raise AssertionError("expected OSError")
    except OSError as e:
        assert e.errno == errno.EIO
    assert chip.fault.pending("readinto") == 0


def test_24_bit_address_write_and_read_round_trip_correctly_on_a_256kb_chip() -> None:
    # A 256KB chip (dev's real MB85RS2MTA) sends a 3-byte address, so a 4-byte header, instead of the 8KB
    # chip's 2-byte one - being over _ADDR_16BIT_MAX, it exercises that path. A basic correctness check; the
    # next test shows why a single-address round trip alone cannot catch an aliasing bug.
    chip = FRAMChip(0x40000, _MB85RS2MTA_RDID)
    _wren(chip)
    _write_mem24(chip, 0x0100, b"\xaa\xbb\xcc")
    assert _read_mem24(chip, 0x0100, 3) == b"\xaa\xbb\xcc"


def test_24_bit_address_low_byte_is_not_dropped_so_aliasing_addresses_stay_distinct() -> None:
    # The low address byte must survive: 0x0000FF and 0x000000 are distinct cells of a 256 KB chip, so a write
    # to one never lands on the other (a 3-byte address, asy_fram_driver.py's _setup_addr_buffer()).
    chip = FRAMChip(0x40000, _MB85RS2MTA_RDID)
    _wren(chip)
    _write_mem24(chip, 0x0000, b"\x11")
    _wren(chip)
    _write_mem24(chip, 0x00FF, b"\x22")
    assert _read_mem24(chip, 0x0000, 1) == b"\x11"
    assert _read_mem24(chip, 0x00FF, 1) == b"\x22"


def test_16_bit_address_chip_is_unaffected_by_the_24_bit_address_path() -> None:
    # The size threshold (_ADDR_16BIT_MAX) must keep every existing 8KB-chip caller on the original
    # 2-byte decode - a regression here would silently break every non-dev device.
    chip = FRAMChip(0x2000, _MB85RS64V_RDID)
    _wren(chip)
    _write_mem(chip, 0x0100, b"\xdd")
    assert _read_mem(chip, 0x0100, 1) == b"\xdd"


def test_a_256kb_chip_holds_its_memory_in_pages_never_one_large_block() -> None:
    # One 256KB bytearray needs a contiguous run a fragmented test heap may not have, even with most of
    # it free (a coverage run failed so with 15MB free). No page may exceed one page's size.
    chip = FRAMChip(0x40000, _MB85RS2MTA_RDID)
    pages = chip.memory._pages
    assert len(pages) > 1, f"a 256KB chip still holds {len(pages)} block"
    assert all(len(page) <= _PAGE_SIZE for page in pages), [len(page) for page in pages if len(page) > _PAGE_SIZE]
    assert sum(len(page) for page in pages) == 0x40000


def test_paged_memory_reads_and_writes_like_the_bytearray_it_replaces() -> None:
    # Every access shape the twin and the tests use, across page boundaries, against a plain bytearray.
    size = 3 * _PAGE_SIZE + 17
    chip = FRAMChip(size, _MB85RS64V_RDID)
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
    other = FRAMChip(size, _MB85RS64V_RDID)
    other.memory[0:size] = ref
    assert chip.memory == other.memory


def test_a_write_past_the_chip_end_is_refused_not_grown() -> None:
    # A bytearray slice assignment past its end would grow the chip; the paged memory refuses instead.
    chip = FRAMChip(_PAGE_SIZE, _MB85RS64V_RDID)
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
    for _ in range(2):  # a second read of a never-written chunk still finds it uninitialised
        assert run(chunk.read_into(chunk.get_buffer())) is False
        assert run(ts_chunk.read_into(ts_chunk.get_buffer())) == (False, None, None)
    assert bytes(chip.memory) == bytes(len(chip.memory)), "a blank read wrote to the chip"
    assert run(manager.get_error_counter())["FRAM"]["ErrCount"] == 0


def test_a_persistent_chip_read_fault_reads_none_then_the_leftover_busy_markers_read_false() -> None:
    # rp2 raises only on a read of 32+ bytes: the status bytes still read, the payload read fails after its busy
    # marker landed - the same outcome as the bus overrun below, the payload kept and False until the next write.
    manager, _bus, chip = _twin_manager()
    chunk, _ts_chunk = _chunks(manager)
    assert run(chunk.write(_PAYLOAD)) is True
    chip.fault.inject_fault("readinto", OSError, errno.EIO, "chip read fault", times=_FAULT_TIMES)
    assert run(chunk.read_into(chunk.get_buffer())) is None
    chip.fault.clear()
    assert _status_bytes(chip, chunk) == [_STATUS_BUSY] * 4
    for addr in chunk._block_addr:
        assert bytes(chip.memory[addr : addr + len(_PAYLOAD)]) == _PAYLOAD
    assert code("E", "UNEXPECTED") in _errnums(manager)
    assert run(chunk.read_into(chunk.get_buffer())) is False
    assert run(chunk.write(_PAYLOAD)) is True
    buf = chunk.get_buffer()
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
        chip.fault.inject_fault("readinto", OSError, errno.EIO, "chip read fault", times=_FAULT_TIMES)
        assert run(ts_chunk.read_into(ts_chunk.get_buffer())) == (None, None, None)
        chip.fault.clear()
        assert run(ts_chunk.read_into(ts_chunk.get_buffer())) == (False, None, None)  # the busy markers it left
        assert run(ts_chunk.write(_PAYLOAD))[0] is True
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


def test_readinto_fault_fires_only_on_a_long_read() -> None:
    chip = FRAMChip(0x2000, _MB85RS64V_RDID)
    chip.fault.inject_fault("readinto", OSError, errno.EIO, "overrun")
    assert _read_mem(chip, 0x0000, 4) == bytes(4)  # under rp2's DMA threshold: no overrun is possible
    assert chip.fault.pending("readinto") == 1
    try:
        _read_mem(chip, 0x0000, 32)
        raise AssertionError("expected the queued fault on the 32-byte read")
    except OSError:
        pass
    assert chip.fault.pending("readinto") == 0


def test_the_long_read_threshold_is_the_twin_buses_dma_threshold() -> None:
    assert _fram_chip._OVERRUN_MIN_READ == machine._SPI_DMA_MIN_SIZE


def test_a_write_across_the_last_address_wraps_to_address_zero() -> None:
    chip = FRAMChip(0x2000, _MB85RS64V_RDID)
    _wren(chip)
    _write_mem(chip, 0x1FFE, b"\x01\x02\x03\x04")
    assert len(chip.memory) == 0x2000
    assert _read_mem(chip, 0x1FFE, 2) == b"\x01\x02"
    assert _read_mem(chip, 0x0000, 2) == b"\x03\x04"


def test_a_read_past_the_end_wraps_to_address_zero() -> None:
    chip = FRAMChip(0x2000, _MB85RS64V_RDID)
    _wren(chip)
    _write_mem(chip, 0x0000, b"\xaa\xbb")
    _wren(chip)
    _write_mem(chip, 0x1FFF, b"\xcc")
    assert _read_mem(chip, 0x1FFF, 3) == b"\xcc\xaa\xbb"


def test_opcode_address_and_data_in_one_write_are_refused() -> None:
    chip = FRAMChip(0x2000, _MB85RS64V_RDID)
    _wren(chip)
    try:
        chip.write(bytes([_OPCODE_WRITE, 0x00, 0x10, 0xAA]))
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "one write()" in str(e), e
    assert _read_mem(chip, 0x0010, 1) == b"\x00"


def test_an_rdid_into_an_8_byte_buffer_keeps_8_bytes_and_holds_the_last_bit() -> None:
    # "SO holds the output state of the last bit in 32-bit Device ID until CS is risen" (both datasheets, p.10).
    for size, rdid, tail in ((0x2000, _MB85RS64V_RDID, 0x00), (0x40000, _MB85RS2MTA_RDID, 0xFF)):
        chip = FRAMChip(size, rdid)
        chip.write(bytes([_OPCODE_RDID]))
        buf = bytearray(8)
        chip.readinto(buf)
        assert bytes(buf) == rdid + bytes([tail] * 4), (size, bytes(buf))


def test_fram_rdid_table_matches_the_driver() -> None:
    # Every product ID asy_fram_driver.py knows has the twin's RDID, and no other size has one.
    known = asy_fram_driver._KNOWN_PRODUCT_IDS
    assert set(known) == set(machine._FRAM_RDID_BY_MAX_SIZE)
    for size, pid in known.items():
        assert machine._FRAM_RDID_BY_MAX_SIZE[size] == bytes([0x04, 0x7F, pid >> 8, pid & 0xFF]), size


def test_payload_writes_are_counted_by_address() -> None:
    chip = FRAMChip(0x2000, _MB85RS64V_RDID)
    _wren(chip)
    _write_mem(chip, 0x0100, b"\x01\x02")
    assert (chip.write_count, chip.writes_at) == (1, {0x0100: 1})
    _wren(chip)
    _write_mem(chip, 0x0200, b"\x01")  # a one-byte status write
    _write_mem(chip, 0x0300, b"\x01\x02")  # no WREN
    chip.silent = True
    _wren(chip)
    _write_mem(chip, 0x0400, b"\x01\x02")
    chip.silent = False
    chip.drop_next_wren = 1
    _wren(chip)
    _write_mem(chip, 0x0500, b"\x01\x02")
    assert (chip.write_count, chip.writes_at, chip.writes_at_dropped) == (1, {0x0100: 1}, 0)
    for addr in range(_fram_chip._WRITES_AT_MAX_KEYS):
        chip.writes_at[0x1000 + addr] = 1  # fill the address table to its cap without 2048 real writes
    del chip.writes_at[0x0100]
    _wren(chip)
    _write_mem(chip, 0x0100, b"\x01\x02")
    assert chip.writes_at_dropped == 1
    assert len(chip.writes_at) == _fram_chip._WRITES_AT_MAX_KEYS


def test_a_chunk_write_survives_one_dropped_wren() -> None:
    manager, _bus, chip = _twin_manager()
    chunk, _ts_chunk = _chunks(manager)
    chip.drop_next_wren = 1
    assert run(chunk.write(_PAYLOAD)) is True  # the driver's one WREN retry sets the latch
    assert chip.drop_next_wren == 0
    buf = chunk.get_buffer()
    assert run(chunk.read_into(buf)) is True
    assert bytes(buf.get_data_buf() or b"") == _PAYLOAD


def test_a_logger_over_its_written_chunk_on_a_protected_chip_stays_uninitialised_and_writes_nothing() -> None:
    # A chip an earlier session left write-protected (SR 0x8C) holds the logger's written chunk: the read cannot mark
    # the copy busy, so it reads as unreadable, the logger stays uninitialised and the chunk bytes stay as they were.
    path = _tmp_path("fram_protected.json")
    manager, _bus, chip = _twin_manager()
    first = PrintLogHistoryStore(manager, name="T3")
    assert run(first.setup()) is True
    run(first.err_s("planted", errno=code("E", "UNEXPECTED")))
    chip.state_path = path
    chip.save_state()
    machine.reset_test_state()
    machine.configure_fram_state_path(path)
    manager, _bus, chip = _twin_manager(status=0x8C)
    stored = bytes(chip.memory)
    second = PrintLogHistoryStore(manager, name="T3")
    run(second.setup())
    assert second.initialized is False
    assert bytes(chip.memory) == stored


def test_a_booted_device_whose_fram_goes_silent_restarts_its_task_and_recovers_or_arms_the_reset() -> None:
    # Silent after boot: two refused writes find the loss and the chip watch task ends; the supervisor restarts it, the
    # restart sets the answering chip up again and a logger write lands; kept silent, the restart budget arms the reset.
    device = device_with("fram")
    module = load_device(device)
    machine.reset_peripherals()
    network.reset_interfaces()
    machine.configure_wiring(wiring_plan(device))

    async def scenario() -> None:
        await boot_generated(module, device, cfg_path=_scratch.dir(), log_errors=True)
        (spi_name,) = wiring_plan(device)["spi"]
        bus = machine.peripheral(spi_name)
        assert isinstance(bus, machine.SPI)
        chip = bus.device
        assert isinstance(chip, FRAMChip)
        fram, sysfunct = module.fram.fram, module.sysfunct
        with FastAsyncSleep():
            await sysfunct.start_tasks([module.fram.start_asy_watch_chip], task_names=[task_name(module.fram, module.fram.start_asy_watch_chip)])
            first = sysfunct._tasks[0]
            supervisor = asyncio.create_task(sysfunct.supervise_tasks())
            await _lose(fram, chip)
            chip.silent = False
            await _until("the watch task restarted and set the chip up", lambda: sysfunct._tasks[0] not in (None, first) and not fram.lost.is_set())
            before = chip.write_count
            await sysfunct.pr.err_s("planted", errno=code("E", "UNEXPECTED"))
            assert chip.write_count > before, "the logger write after the recovery did not reach the chip"
            await _lose(fram, chip)
            await _until("the restart budget armed the reset", lambda: sysfunct._reset_armed)
            sysfunct._reset_timer.deinit()  # asserted at the armed point: the in-process graph never takes the reset
            await cancel(supervisor)

    run(scenario())


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
