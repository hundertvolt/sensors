"""Full-stack integration tests: the real chain from tests/_fram_chip_fake.py's simulated MB85RS64V chip, through asy_spi_driver.py/asy_fram_driver.py/asy_fram_manager.py, up into asy_print_log.py/asy_base_classes.py's real consumers - mocked down to SPI bus interaction, not just FRAMManager's own boundary.
See SPECIFICATION.md Part E.4 for the mocking-boundary plan."""
# No bus-level fault here: rp2 SPI's only one, an RX overrun raising OSError(EIO) on a 32+ byte read (SPECIFICATION.md
# F.5.2), is modelled by tests/machine.py's rx_overrun and driven through this same stack in test_asy_fram_manager.py.

import asyncio
import gc
from collections import namedtuple

from _error_codes import code
from _fram_chip_fake import FakeMB85RS64V

import asy_spi_driver
from asy_base_classes import SensorReader
from asy_crc_checks import CRC32, CRCPass
from asy_fram_manager import FRAMChunk, FRAMManager
from asy_print_log import LogConfig, PrintLogHistoryStore
from asy_spi_driver import SPI

# Same one-process-per-test-file swap as the other asy_fram_* test files - see their own comments.
asy_spi_driver._SPI = FakeMB85RS64V  # type: ignore[misc]

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")
    from asy_print_log import ErrorLog

Meas = namedtuple("Meas", ["temp", "hum"])

# Real on-chip constant values (asy_fram_manager.py's own _STATUS_* are micropython.const() and
# compiled away - not importable - matching test_asy_fram_manager.py's own convention).
_STATUS_BUSY = 0x02


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


def make_manager(max_size: int = 0x2000) -> tuple[FRAMManager, FakeMB85RS64V]:
    bus = SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    manager = FRAMManager(bus, 1, max_size=max_size)
    chip = manager.fram._spidev.spi._spi
    assert isinstance(chip, FakeMB85RS64V)
    return manager, chip


async def _synced() -> bool:
    return True


# ---------------------------------------------------------------------------
# Real multi-consumer topology, matching the generated device modules' production shape: one FRAMManager
# backs both a driver's own PrintLogHistoryStore (error persistence, CRC8, allocated first by
# SensorReader.__init__) and a separate value-backup chunk (allocated second, CRC32, as _ts_storage is).
#
# Confirms the shared bump-pointer allocator gives both non-overlapping storage, and that both operate
# correctly and independently off the one manager.
# ---------------------------------------------------------------------------


def test_printloghistorystore_chunk_and_a_separate_value_chunk_share_one_manager_without_overlap() -> None:
    manager, _chip = make_manager()
    run(manager.setup())
    reader = SensorReader(Meas(20.0, 50), "", max_module_error=3, log=LogConfig(manager, 10, None))
    run(reader.setup())
    assert isinstance(reader.pr, PrintLogHistoryStore)
    assert isinstance(reader.pr.fram, FRAMChunk)
    value_chunk = manager.get_timestamped_chunk(8, _synced, crc=CRC32(), owner="VALUE")
    assert value_chunk is not None

    # The PrintLogHistoryStore chunk's full 2-block span must end exactly where the next
    # allocation starts - the same non-overlap invariant tests/test_asy_fram_manager.py's own
    # allocator tests check, now proven across two structurally different real chunk types.
    pr_block0, pr_block1 = reader.pr.fram._block_addr
    pr_full_end = pr_block1 + (pr_block1 - pr_block0)
    assert value_chunk._block_addr[0] == pr_full_end

    async def scenario() -> "tuple[ErrorLog, bool, bytearray | None]":
        await reader.pr.err_s("integration test error", errno=code("E", "CALLBACK"))
        log = await reader.pr.get_log("sensor")
        buf = value_chunk.get_buffer()
        dbuf = buf.get_data_buf()
        assert dbuf is not None
        dbuf[:] = b"12345678"
        write_ok, *_ = await value_chunk.write_into(buf)
        read_buf = value_chunk.get_buffer()
        _res, _ts2, _age = await value_chunk.read_into(read_buf)
        data = read_buf.get_data_buf()
        return log, write_ok, None if data is None else bytearray(data)

    log, write_ok, data = run(scenario())
    assert log["sensor"]["ErrNum"][-1] == code("E", "CALLBACK")  # the error persisted through the PrintLogHistoryStore chunk
    assert write_ok is True
    assert data == bytearray(b"12345678")  # the separate value chunk round-trips independently


# ---------------------------------------------------------------------------
# Real chip-level faults propagating through SensorReader's FRAM-backed error logging - one layer
# further than tests/test_asy_print_log.py's own PrintLogHistoryStore-focused fault tests, going
# through the full real SensorReader -> PrintLogHistoryStore -> FRAMChunk -> FRAM_SPI chain.
# ---------------------------------------------------------------------------


def test_real_chip_fault_degrades_fram_persistence_but_keeps_in_memory_error_tracking_correct() -> None:
    # A real chip.drop_wren fault, not a Protocol-level fake, breaks the underlying FRAM write - confirming
    # asy_print_log.py's "_err_count and history update in memory regardless of persistence success" contract
    # holds when the failure is genuinely hardware-level, not a hypothetical misbehaving _FramManager.
    manager, chip = make_manager()
    run(manager.setup())
    reader = SensorReader(Meas(20.0, 50), "", max_module_error=3, log=LogConfig(manager, 10, None))
    run(reader.setup())
    chip.drop_wren = True

    async def scenario() -> "tuple[int, ErrorLog]":
        await reader.pr.err_s("boom", errno=code("E", "UNEXPECTED"))
        log = await reader.pr.get_log("sensor")
        return reader.pr._err_count, log

    err_count, log = run(scenario())
    assert err_count == 2  # in-memory counting is unaffected by the underlying FRAM fault; the failed write adds LOG_RAM_ONLY
    assert log["sensor"]["ErrNum"][-2:] == [code("E", "UNEXPECTED"), code("E", "LOG_RAM_ONLY")]


def test_sensorreader_runs_in_degraded_mode_when_fram_setup_never_succeeded() -> None:
    # Models a chip dead or missing at boot (a real device-ID mismatch): setup() fails, but a driver's
    # SensorReader(log=LogConfig(manager, ...)) must still construct and run. get_chunk() needs no successful setup(), so
    # reader.pr.fram is a real but permanently unusable chunk, not None, and must degrade cleanly.
    manager, chip = make_manager()
    chip.rdid_response = bytes([0xFF, 0xFF, 0xFF, 0xFF])
    setup_ok = run(manager.setup())
    assert setup_ok is False
    before = bytes(chip.memory)
    reader = SensorReader(Meas(20.0, 50), "", max_module_error=3, log=LogConfig(manager, 10, None))
    run(reader.setup())
    assert isinstance(reader.pr, PrintLogHistoryStore)
    assert reader.pr.fram is not None  # allocated fine, just backed by a chip that never came up
    assert list(reader.pr.history).count(code("E", "LOG_RAM_ONLY")) == 1  # the store says it runs RAM-only

    async def scenario() -> int:
        await reader.pr.err_s("boom", errno=code("E", "BAD_ARG"))
        return reader.pr._err_count

    assert run(scenario()) == 2  # its RAM-only entry and this one, tracked in memory, no crash despite the dead chip
    assert bytes(chip.memory) == before


def test_after_a_chip_loss_ten_logger_writes_add_no_fram_log_entry_beyond_the_loss() -> None:
    # A chip gone silent mid-run is lost on the second latch anomaly: one FRAM_CHIP_LOST, then the chunk layer
    # stays off the chip, so no later persisted entry reaches the bus or adds to the FRAM manager's log.
    manager, chip = make_manager()
    run(manager.setup())
    reader = SensorReader(Meas(1.0, 1), "LOSS", max_module_error=3, log=LogConfig(manager, 10, None))
    run(reader.setup())
    chip.silent = 0x00
    for _ in range(2):  # each failed write stops at its first status-byte write: one latch anomaly apiece
        run(reader.pr.err_s("a write that finds the loss", errno=code("E", "READ")))
    assert manager.fram.lost.is_set()
    assert list(manager.pr.history).count(code("E", "FRAM_CHIP_LOST")) == 1
    fram_errors = manager.pr._err_count
    chip.opcodes = []

    async def ten_writes() -> None:
        for _ in range(10):
            await reader.pr.err_s("while lost", errno=code("E", "READ"))

    run(ten_writes())
    assert manager.pr._err_count == fram_errors
    assert list(manager.pr.history).count(code("E", "FRAM_CHIP_LOST")) == 1
    assert chip.opcodes == []  # nothing reached the bus
    assert reader.pr._err_count == 13  # every entry still counted in RAM, plus the failed-write run's one LOG_RAM_ONLY


# ---------------------------------------------------------------------------
# Long-running stability - matching src/asy_sgp40_driver.py's real periodic
# write_into/read_into cycle (a fresh scratch buffer fetched via get_buffer() each cycle, CRC32,
# dynamic verify), run across many iterations to catch any state leak a 1-2-cycle test wouldn't.
# ---------------------------------------------------------------------------


def test_many_write_read_cycles_with_crc32_and_verify_show_no_state_leak() -> None:
    # gc.collect() each cycle: without it this tight allocate-heavy loop exhausts the Unix-port binary's
    # heap after ~7 cycles with a plain MemoryError - a test-environment GC-timing artifact, diagnosed
    # directly, not an asy_fram_manager.py bug.
    #
    # The loop is the regression check for state leaking across cycles (stale CRC, _verify_counter or lock
    # state carrying over), not for the unrelated heap ceiling.
    manager, _chip = make_manager()
    run(manager.setup())
    chunk = manager.get_chunk(8, crc=CRC32(), verify=1, owner="CYCLES")
    assert chunk is not None

    async def run_cycle(i: int) -> tuple[bool, bytearray | None]:
        payload = f"cy{i:06d}".encode()
        write_ok = await chunk.write(payload)
        data = await chunk.read()
        return write_ok, data

    for i in range(40):
        gc.collect()
        write_ok, data = run(run_cycle(i))
        assert write_ok is True
        assert data == bytearray(f"cy{i:06d}".encode())


# ---------------------------------------------------------------------------
# Multiple independent consumers on one shared manager, and surviving a simulated reboot -
# the actual production topology (multiple sensor drivers, each with log=LogConfig(<one shared manager>, ...))
# and the static-allocation-order invariant the whole module exists to preserve.
# ---------------------------------------------------------------------------


def test_two_sensorreaders_sharing_one_manager_keep_independent_error_histories() -> None:
    # A shared physical chip does not mean shared bookkeeping - each SensorReader gets its own
    # PrintLogHistoryStore chunk at a distinct address, so one driver's errors must never show up
    # in another driver's own error log even though both ultimately hit the same FRAM chip.
    manager, _chip = make_manager()
    run(manager.setup())
    reader_a = SensorReader(Meas(1.0, 1), "A", max_module_error=3, log=LogConfig(manager, 10, None))  # one owner name per chunk
    reader_b = SensorReader(Meas(2.0, 2), "B", max_module_error=3, log=LogConfig(manager, 10, None))
    run(reader_a.setup())
    run(reader_b.setup())
    assert isinstance(reader_a.pr, PrintLogHistoryStore) and isinstance(reader_b.pr, PrintLogHistoryStore)
    assert isinstance(reader_a.pr.fram, FRAMChunk) and isinstance(reader_b.pr.fram, FRAMChunk)
    assert reader_a.pr.fram._block_addr != reader_b.pr.fram._block_addr

    async def scenario() -> "tuple[ErrorLog, ErrorLog]":
        await reader_a.pr.err_s("err in a", errno=code("E", "CALLBACK"))
        await reader_b.pr.wrn_s("wrn in b", wrnno=code("W", "STORED_DEFAULT"))
        log_a = await reader_a.pr.get_log("a")
        log_b = await reader_b.pr.get_log("b")
        return log_a, log_b

    log_a, log_b = run(scenario())
    assert log_a["a"]["ErrCount"] == 1
    assert log_a["a"]["ErrNum"][-1] == code("E", "CALLBACK")
    assert log_b["b"]["ErrCount"] == 1
    assert log_b["b"]["ErrNum"][-1] == code("W", "STORED_DEFAULT")  # reader_a's error never leaked into reader_b's history


def test_persisted_error_log_and_value_chunk_both_survive_a_simulated_reboot() -> None:
    # The central invariant this module exists for, proven across two structurally different chunk types at
    # once - a PrintLogHistoryStore's chunk and a separate CRC32 value chunk, not just one: reattaching
    # fresh manager and reader objects to the same chip, in the same instantiation order, must decode both.
    manager1, chip = make_manager()
    run(manager1.setup())
    reader1 = SensorReader(Meas(1.0, 1), "", max_module_error=3, log=LogConfig(manager1, 10, None))
    run(reader1.setup())
    value_chunk1 = manager1.get_timestamped_chunk(8, _synced, crc=CRC32(), owner="VALUE")
    assert value_chunk1 is not None

    async def before_reboot() -> None:
        await reader1.pr.err_s("persisted error", errno=code("E", "CONTRACT"))
        buf = value_chunk1.get_buffer()
        dbuf = buf.get_data_buf()
        assert dbuf is not None
        dbuf[:] = b"deadbeef"
        await value_chunk1.write_into(buf)

    run(before_reboot())

    manager2, _chip2 = make_manager()
    manager2.fram._spidev.spi._spi = chip  # same underlying chip, fresh manager/reader objects
    run(manager2.setup())
    reader2 = SensorReader(Meas(1.0, 1), "", max_module_error=3, log=LogConfig(manager2, 10, None))
    run(reader2.setup())
    value_chunk2 = manager2.get_timestamped_chunk(8, _synced, crc=CRC32(), owner="VALUE")  # the same owner reads its own chunk
    assert value_chunk2 is not None

    async def after_reboot() -> "tuple[ErrorLog, bytearray | None]":
        log = await reader2.pr.get_log("x")
        read_buf = value_chunk2.get_buffer()
        _res, _ts, _age = await value_chunk2.read_into(read_buf)
        data = read_buf.get_data_buf()
        return log, None if data is None else bytearray(data)

    log, data = run(after_reboot())
    assert log["x"]["ErrNum"][-1] == code("E", "CONTRACT")
    assert data == bytearray(b"deadbeef")


# ---------------------------------------------------------------------------
# Fault injection through the full real chain, not just at FRAMManager's boundary - each mirrors a
# failure mode already proven at the module level in tests/test_asy_fram_manager.py, now confirmed to hold
# when driven through the actual production consumer chain rather than calling chunk.write()/read().
# ---------------------------------------------------------------------------


def test_torn_write_on_printloghistorystore_chunk_self_heals_across_a_simulated_reboot() -> None:
    # Simulates power loss mid-write, one block left BUSY, on a production consumer's own persisted chunk,
    # then a fresh boot - proving self-heal holds through the actual SensorReader -> PrintLogHistoryStore ->
    # FRAMChunk -> FRAM_SPI chain, not just when a test pokes a directly-allocated chunk.
    manager1, chip = make_manager()
    run(manager1.setup())
    reader1 = SensorReader(Meas(1.0, 1), "", max_module_error=3, log=LogConfig(manager1, 10, None))
    run(reader1.setup())
    run(reader1.pr.err_s("before reboot", errno=code("E", "LOCK_TIMEOUT")))
    assert isinstance(reader1.pr, PrintLogHistoryStore)
    assert isinstance(reader1.pr.fram, FRAMChunk)
    addr0, _addr1 = reader1.pr.fram._block_addr
    status_addr = addr0 + reader1.pr.fram.size + reader1.pr.fram.crc.length()
    chip.memory[status_addr] = _STATUS_BUSY
    chip.memory[status_addr + 1] = _STATUS_BUSY

    manager2, _chip2 = make_manager()
    manager2.fram._spidev.spi._spi = chip  # same underlying chip, fresh manager/reader objects
    run(manager2.setup())
    reader2 = SensorReader(Meas(1.0, 1), "", max_module_error=3, log=LogConfig(manager2, 10, None))
    run(reader2.setup())

    async def scenario() -> "ErrorLog":
        return await reader2.pr.get_log("y")

    log = run(scenario())
    assert log["y"]["ErrNum"][-1] == code("E", "LOCK_TIMEOUT")  # recovered from block 1 despite block 0's torn-write marker


def test_torn_write_on_both_blocks_wipes_the_history_cleanly_rather_than_partially() -> None:
    # The other outcome of the same power-loss shape: an interrupted write can leave BOTH blocks marked
    # BUSY, the protocol marking both before touching either payload, leaving nothing to self-heal from.
    # setup()'s _read() fails, its _write() fallback stores the empty ring, and the history is gone.
    #
    # That loss is accepted behavior, not a defect (project owner, 2026-09-11): no recovery scheme is wanted
    # for a reboot that catches the chip mid-operation.
    #
    # What this pins is that the loss is all-or-nothing - a cleanly empty ring, never a partial or garbled
    # one, which is the dual-block plus CRC plus busy-flag protocol's actual job. Mirrored at the twin tier
    # (Run 5b) and on real silicon (tests_hardware/flash/test_fram_storage.py).
    manager1, chip = make_manager()
    run(manager1.setup())
    reader1 = SensorReader(Meas(1.0, 1), "", max_module_error=3, log=LogConfig(manager1, 10, None))
    run(reader1.setup())
    run(reader1.pr.err_s("before reboot", errno=code("E", "LOCK_TIMEOUT")))
    assert isinstance(reader1.pr, PrintLogHistoryStore)
    assert isinstance(reader1.pr.fram, FRAMChunk)
    addr0, addr1 = reader1.pr.fram._block_addr
    payload_len = reader1.pr.fram.size + reader1.pr.fram.crc.length()
    for base in (addr0, addr1):
        chip.memory[base + payload_len] = _STATUS_BUSY
        chip.memory[base + payload_len + 1] = _STATUS_BUSY

    manager2, _chip2 = make_manager()
    manager2.fram._spidev.spi._spi = chip  # same underlying chip, fresh manager/reader objects
    run(manager2.setup())
    reader2 = SensorReader(Meas(1.0, 1), "", max_module_error=3, log=LogConfig(manager2, 10, None))
    run(reader2.setup())

    async def scenario() -> "ErrorLog":
        return await reader2.pr.get_log("y")

    log = run(scenario())
    assert log["y"]["ErrCount"] == 0  # not a partially-restored count
    assert set(log["y"]["ErrType"]) == {"N"}  # cleanly empty, never a torn remnant of the planted entry
    assert code("E", "LOCK_TIMEOUT") not in log["y"]["ErrNum"]

    # And the chunk must still be usable afterwards - a wedged chunk that never takes a write again
    # would be a real defect even under the accepted-loss rule above.
    run(reader2.pr.err_s("after reboot", errno=code("E", "READ")))
    log_after = run(scenario())
    assert log_after["y"]["ErrNum"][-1] == code("E", "READ")
    assert log_after["y"]["ErrCount"] == 1


def test_value_chunk_crc_trailer_corruption_self_heals_through_the_full_chain() -> None:
    # A directly corrupted CRC trailer byte (not payload) on a real CRC32 value chunk, matching
    # asy_sgp40_driver.py's own _ts_storage shape - proves the checksum's own on-chip storage is
    # covered end to end, not just when tested via FRAMManager's own boundary.
    manager, chip = make_manager()
    run(manager.setup())
    value_chunk = manager.get_timestamped_chunk(8, _synced, crc=CRC32(), owner="VALUE")
    assert value_chunk is not None

    async def write_data() -> None:
        buf = value_chunk.get_buffer()
        dbuf = buf.get_data_buf()
        assert dbuf is not None
        dbuf[:] = b"12345678"
        await value_chunk.write_into(buf)

    run(write_data())
    addr0, _addr1 = value_chunk._block_addr
    crc_byte_addr = addr0 + value_chunk.size + value_chunk.crc.length() - 1
    chip.memory[crc_byte_addr] ^= 0xFF

    async def read_data() -> bytearray | None:
        read_buf = value_chunk.get_buffer()
        _res, _ts, _age = await value_chunk.read_into(read_buf)
        data = read_buf.get_data_buf()
        return None if data is None else bytearray(data)

    assert run(read_data()) == bytearray(b"12345678")  # self-healed from block 1


def test_value_chunk_timestamp_corruption_hard_fails_without_crc_through_the_full_chain() -> None:
    # Mirrors the same finding from tests/test_asy_fram_manager.py through the full chain: with
    # crc=CRCPass(), a corrupted timestamp byte isn't silently returned wrong - the independent
    # cross-block comparison still catches it as "both blocks valid but different data".
    manager, chip = make_manager()
    run(manager.setup())
    value_chunk = manager.get_timestamped_chunk(8, _synced, crc=CRCPass(), owner="VALUE")
    assert value_chunk is not None

    async def write_data() -> None:
        buf = value_chunk.get_buffer()
        dbuf = buf.get_data_buf()
        assert dbuf is not None
        dbuf[:] = b"12345678"
        await value_chunk.write_into(buf)

    run(write_data())
    addr0, _addr1 = value_chunk._block_addr
    chip.memory[addr0] ^= 0xFF  # first byte of the on-chip timestamp field itself

    async def read_data() -> tuple[int | None, int | None, bytearray | None]:
        return await value_chunk.read()

    assert run(read_data()) == (None, None, None)  # hard fail, not a silently wrong timestamp


def test_pause_blocks_persisted_write_but_in_memory_error_tracking_still_works() -> None:
    # asy_print_log.py's "in-memory count and history update regardless of persistence success" contract, proven
    # here for the pause fault mode specifically, previously only for a real drop_wren fault - and, unlike
    # that test, verified by confirming no byte anywhere on the simulated chip changed while paused.
    manager, chip = make_manager()
    run(manager.setup())
    reader = SensorReader(Meas(1.0, 1), "", max_module_error=3, log=LogConfig(manager, 10, None))
    run(reader.setup())
    before = bytes(chip.memory)
    manager.set_pause(value=True)

    async def scenario() -> int:
        await reader.pr.err_s("paused write", errno=code("E", "READ"))
        return reader.pr._err_count

    err_count = run(scenario())
    assert err_count == 2  # in-memory tracking unaffected by pause; the refused write adds one LOG_RAM_ONLY
    assert bytes(chip.memory) == before  # nothing was actually written to FRAM while paused


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
