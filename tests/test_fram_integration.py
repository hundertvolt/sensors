"""Full-stack integration tests: the real chain from tests/_fram_chip_fake.py's simulated
MB85RS64V chip, through asy_spi_driver.py/asy_fram_driver.py/asy_fram_manager.py, up into
print_log.py/base_classes.py's real consumers (SensorReader) - nothing faked above the chip-fake
level (which itself subclasses tests/machine.py's raw fake machine.SPI, so this is genuinely mocked
down to SPI bus interaction, not just to AsyFramManager's own boundary as tests/test_asy_fram_manager.py
mostly does). See tests/README.md's mocking-boundary plan and BACKLOG.md's "asy_fram_manager.py -> src/"
sections for why each individual module is trusted rather than re-mocked here.

Deliberately not modeled: a raw-SPI-bus-level fault (a real electrical disturbance corrupting a
transfer) - confirmed via tests/machine.py's and asy_spi_driver.py's own docstrings that real RP2040
SPI write()/readinto() genuinely cannot raise or report a fault at all once constructed (unlike I2C,
which has a NAK/timeout errno surface tests/machine.py's I2C fake does model) - so there is no lower
fault-injection seam to add here; tests/_fram_chip_fake.py's own opcode/latch/identity-level knobs
already are the lowest layer where an actual failure can be observed, matching asy_fram_driver.py's
own module docstring on this exact point.
"""

import asyncio
import gc
from collections import namedtuple

from _fram_chip_fake import FakeMB85RS64V

import asy_spi_driver
from asy_fram_manager import AsyFramChunk, AsyFramManager
from asy_spi_driver import SPI
from base_classes import SensorReader
from crc_checks import CRC32, CRC_Pass
from print_log import PrintLogHistoryStore

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

Meas = namedtuple("Meas", ["temp", "hum"])

# Real on-chip constant values (asy_fram_manager.py's own _STATUS_* are micropython.const() and
# compiled away - not importable - matching test_asy_fram_manager.py's own convention).
_STATUS_BUSY = 0x02


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


def make_manager(max_size: int = 0x2000) -> tuple[AsyFramManager, FakeMB85RS64V]:
    bus = SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    manager = AsyFramManager(bus, 1, max_size=max_size)
    chip = manager.fram._spidev.spi._spi
    assert isinstance(chip, FakeMB85RS64V)
    return manager, chip


async def _synced() -> bool:
    return True


# ---------------------------------------------------------------------------
# Real multi-consumer topology - matching improved-quality/sensortask-wozi.py's actual production
# shape: one AsyFramManager backs both a driver's own PrintLogHistoryStore (error persistence,
# CRC8, allocated first via SensorReader's own __init__) and a separate value-backup chunk
# (allocated second, a caller's own choice of CRC - CRC32, matching asy_sgp40_driver.py's real
# ts_storage) - confirming the shared bump-pointer allocator gives both non-overlapping storage
# and that both operate correctly and independently off the one manager.
# ---------------------------------------------------------------------------


def test_printloghistorystore_chunk_and_a_separate_value_chunk_share_one_manager_without_overlap() -> None:
    manager, _chip = make_manager()
    run(manager.setup())
    reader = SensorReader(Meas(20.0, 50), 3, fram=manager)
    run(reader.pr.setup())
    assert isinstance(reader.pr, PrintLogHistoryStore)
    assert isinstance(reader.pr.fram, AsyFramChunk)
    value_chunk = manager.get_timestamped_chunk(8, _synced, crc=CRC32())
    assert value_chunk is not None

    # The PrintLogHistoryStore chunk's full 2-block span must end exactly where the next
    # allocation starts - the same non-overlap invariant tests/test_asy_fram_manager.py's own
    # allocator tests check, now proven across two structurally different real chunk types.
    pr_block0, pr_block1 = reader.pr.fram.block_addr
    pr_full_end = pr_block1 + (pr_block1 - pr_block0)
    assert value_chunk.block_addr[0] == pr_full_end

    async def scenario() -> tuple[dict, bool, bytearray | None]:
        await reader.pr.err_s("integration test error", errno=1)
        log = await reader.pr.get_log("sensor")
        buf = value_chunk.get_buffer()
        dbuf = buf.get_data_buf()
        assert dbuf is not None
        dbuf[:] = b"12345678"
        _ntp_synced, _ts, write_ok = await value_chunk.write_into(buf)
        read_buf = value_chunk.get_buffer()
        _res, _ts2, _age = await value_chunk.read_into(read_buf)
        data = read_buf.get_data_buf()
        return log, write_ok, None if data is None else bytearray(data)

    log, write_ok, data = run(scenario())
    assert log["sensor"]["ErrNum"][-1] == 1  # the error persisted through the PrintLogHistoryStore chunk
    assert write_ok is True
    assert data == bytearray(b"12345678")  # the separate value chunk round-trips independently


# ---------------------------------------------------------------------------
# Real chip-level faults propagating through SensorReader's FRAM-backed error logging - one layer
# further than tests/test_print_log.py's own PrintLogHistoryStore-focused fault tests, going
# through the full real SensorReader -> PrintLogHistoryStore -> AsyFramChunk -> FRAM_SPI chain.
# ---------------------------------------------------------------------------


def test_real_chip_fault_degrades_fram_persistence_but_keeps_in_memory_error_tracking_correct() -> None:
    # A real chip.drop_wren fault (not a Protocol-level fake) breaks the underlying FRAM write -
    # confirms print_log.py's own "err_count/history update in memory regardless of persistence
    # success" contract holds when the failure is a genuine hardware-level one, not a hypothetical
    # misbehaving _FramManager.
    manager, chip = make_manager()
    run(manager.setup())
    reader = SensorReader(Meas(20.0, 50), 3, fram=manager)
    run(reader.pr.setup())
    chip.drop_wren = True

    async def scenario() -> tuple[int, dict]:
        await reader.pr.err_s("boom", errno=5)
        log = await reader.pr.get_log("sensor")
        return reader.pr.err_count, log

    err_count, log = run(scenario())
    assert err_count == 1  # in-memory counting is unaffected by the underlying FRAM fault
    assert log["sensor"]["ErrNum"][-1] == 5


def test_sensorreader_runs_in_degraded_mode_when_fram_setup_never_succeeded() -> None:
    # Models a chip that's dead/missing at boot (real device-ID mismatch): manager.setup() fails,
    # but a driver's own SensorReader(fram=manager) must still construct and run - get_chunk()'s
    # own bookkeeping doesn't require setup() to have succeeded, so reader.pr.fram is a real
    # (but permanently hardware-unusable) chunk, not None - every operation through it must still
    # degrade cleanly rather than raise or silently corrupt the in-memory error count.
    manager, chip = make_manager()
    chip.rdid_response = bytes([0xFF, 0xFF, 0xFF, 0xFF])
    setup_ok = run(manager.setup())
    assert setup_ok is False
    reader = SensorReader(Meas(20.0, 50), 3, fram=manager)
    run(reader.pr.setup())
    assert isinstance(reader.pr, PrintLogHistoryStore)
    assert reader.pr.fram is not None  # allocated fine, just backed by a chip that never came up

    async def scenario() -> int:
        await reader.pr.err_s("boom", errno=7)
        return reader.pr.err_count

    assert run(scenario()) == 1  # still tracked in memory, no crash despite the dead chip


# ---------------------------------------------------------------------------
# Long-running stability - matching improved-quality/asy_sgp40_driver.py's real periodic
# write_into/read_into cycle (a fresh scratch buffer fetched via get_buffer() each cycle, CRC32,
# dynamic verify), run across many iterations to catch any state leak a 1-2-cycle test wouldn't.
# ---------------------------------------------------------------------------


def test_many_write_read_cycles_with_crc32_and_verify_show_no_state_leak() -> None:
    # gc.collect() each cycle: confirmed directly that without it, this tight allocate-heavy loop
    # exhausts the MicroPython Unix-port test binary's heap after ~7 cycles with a plain
    # MemoryError (a test-environment GC-timing artifact reproduced and diagnosed directly, not an
    # asy_fram_manager.py bug - real firmware's own GC runs the same way real MicroPython drivers
    # already rely on). This loop is the actual regression check for state leaking across cycles
    # (stale CRC/verify_counter/lock state carrying over), not for the unrelated heap ceiling.
    manager, _chip = make_manager()
    run(manager.setup())
    chunk = manager.get_chunk(8, crc=CRC32(), verify=1)
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
# the actual production topology (multiple sensor drivers, each with fram=<one shared manager>)
# and the static-allocation-order invariant the whole module exists to preserve.
# ---------------------------------------------------------------------------


def test_two_sensorreaders_sharing_one_manager_keep_independent_error_histories() -> None:
    # A shared physical chip does not mean shared bookkeeping - each SensorReader gets its own
    # PrintLogHistoryStore chunk at a distinct address, so one driver's errors must never show up
    # in another driver's own error log even though both ultimately hit the same FRAM chip.
    manager, _chip = make_manager()
    run(manager.setup())
    reader_a = SensorReader(Meas(1.0, 1), 3, fram=manager)
    reader_b = SensorReader(Meas(2.0, 2), 3, fram=manager)
    run(reader_a.pr.setup())
    run(reader_b.pr.setup())
    assert isinstance(reader_a.pr, PrintLogHistoryStore) and isinstance(reader_b.pr, PrintLogHistoryStore)
    assert isinstance(reader_a.pr.fram, AsyFramChunk) and isinstance(reader_b.pr.fram, AsyFramChunk)
    assert reader_a.pr.fram.block_addr != reader_b.pr.fram.block_addr

    async def scenario() -> tuple[dict, dict]:
        await reader_a.pr.err_s("err in a", errno=1)
        await reader_b.pr.wrn_s("wrn in b", wrnno=2)
        log_a = await reader_a.pr.get_log("a")
        log_b = await reader_b.pr.get_log("b")
        return log_a, log_b

    log_a, log_b = run(scenario())
    assert log_a["a"]["ErrCount"] == 1
    assert log_a["a"]["ErrNum"][-1] == 1
    assert log_b["b"]["ErrCount"] == 1
    assert log_b["b"]["ErrNum"][-1] == 2  # reader_a's error never leaked into reader_b's history


def test_persisted_error_log_and_value_chunk_both_survive_a_simulated_reboot() -> None:
    # The central invariant this module exists for, proven across two structurally different
    # chunk types at once (a PrintLogHistoryStore's own chunk and a separate CRC32 value chunk),
    # not just one - reattaching fresh manager/reader objects to the same underlying chip, in the
    # same instantiation order, must decode both correctly.
    manager1, chip = make_manager()
    run(manager1.setup())
    reader1 = SensorReader(Meas(1.0, 1), 3, fram=manager1)
    run(reader1.pr.setup())
    value_chunk1 = manager1.get_timestamped_chunk(8, _synced, crc=CRC32())
    assert value_chunk1 is not None

    async def before_reboot() -> None:
        await reader1.pr.err_s("persisted error", errno=3)
        buf = value_chunk1.get_buffer()
        dbuf = buf.get_data_buf()
        assert dbuf is not None
        dbuf[:] = b"deadbeef"
        await value_chunk1.write_into(buf)

    run(before_reboot())

    manager2, _chip2 = make_manager()
    manager2.fram._spidev.spi._spi = chip  # same underlying chip, fresh manager/reader objects
    run(manager2.setup())
    reader2 = SensorReader(Meas(1.0, 1), 3, fram=manager2)
    run(reader2.pr.setup())
    value_chunk2 = manager2.get_timestamped_chunk(8, _synced, crc=CRC32())
    assert value_chunk2 is not None

    async def after_reboot() -> tuple[dict, bytearray | None]:
        log = await reader2.pr.get_log("x")
        read_buf = value_chunk2.get_buffer()
        _res, _ts, _age = await value_chunk2.read_into(read_buf)
        data = read_buf.get_data_buf()
        return log, None if data is None else bytearray(data)

    log, data = run(after_reboot())
    assert log["x"]["ErrNum"][-1] == 3
    assert data == bytearray(b"deadbeef")


# ---------------------------------------------------------------------------
# Fault injection through the full real chain, not just at AsyFramManager's own boundary - each
# mirrors a failure mode already proven at the module level in tests/test_asy_fram_manager.py, now
# confirmed to hold when driven through the actual production consumer chain instead of calling
# chunk.write()/read() directly.
# ---------------------------------------------------------------------------


def test_torn_write_on_printloghistorystore_chunk_self_heals_across_a_simulated_reboot() -> None:
    # Simulates power loss mid-write (one block left BUSY) on a real production consumer's own
    # persisted chunk, then a fresh boot - proving self-heal holds through the actual
    # SensorReader -> PrintLogHistoryStore -> AsyFramChunk -> FRAM_SPI chain, not just when a test
    # pokes a directly-allocated chunk.
    manager1, chip = make_manager()
    run(manager1.setup())
    reader1 = SensorReader(Meas(1.0, 1), 3, fram=manager1)
    run(reader1.pr.setup())
    run(reader1.pr.err_s("before reboot", errno=9))
    assert isinstance(reader1.pr, PrintLogHistoryStore)
    assert isinstance(reader1.pr.fram, AsyFramChunk)
    addr0, _addr1 = reader1.pr.fram.block_addr
    status_addr = addr0 + reader1.pr.fram.size + reader1.pr.fram.crc.length()
    chip.memory[status_addr] = _STATUS_BUSY
    chip.memory[status_addr + 1] = _STATUS_BUSY

    manager2, _chip2 = make_manager()
    manager2.fram._spidev.spi._spi = chip  # same underlying chip, fresh manager/reader objects
    run(manager2.setup())
    reader2 = SensorReader(Meas(1.0, 1), 3, fram=manager2)
    run(reader2.pr.setup())

    async def scenario() -> dict:
        return await reader2.pr.get_log("y")

    log = run(scenario())
    assert log["y"]["ErrNum"][-1] == 9  # recovered from block 1 despite block 0's torn-write marker


def test_value_chunk_crc_trailer_corruption_self_heals_through_the_full_chain() -> None:
    # A directly corrupted CRC trailer byte (not payload) on a real CRC32 value chunk, matching
    # asy_sgp40_driver.py's own ts_storage shape - proves the checksum's own on-chip storage is
    # covered end to end, not just when tested via AsyFramManager's own boundary.
    manager, chip = make_manager()
    run(manager.setup())
    value_chunk = manager.get_timestamped_chunk(8, _synced, crc=CRC32())
    assert value_chunk is not None

    async def write_data() -> None:
        buf = value_chunk.get_buffer()
        dbuf = buf.get_data_buf()
        assert dbuf is not None
        dbuf[:] = b"12345678"
        await value_chunk.write_into(buf)

    run(write_data())
    addr0, _addr1 = value_chunk.block_addr
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
    # crc=CRC_Pass(), a corrupted timestamp byte isn't silently returned wrong - the independent
    # cross-block comparison still catches it as "both blocks valid but different data".
    manager, chip = make_manager()
    run(manager.setup())
    value_chunk = manager.get_timestamped_chunk(8, _synced, crc=CRC_Pass())
    assert value_chunk is not None

    async def write_data() -> None:
        buf = value_chunk.get_buffer()
        dbuf = buf.get_data_buf()
        assert dbuf is not None
        dbuf[:] = b"12345678"
        await value_chunk.write_into(buf)

    run(write_data())
    addr0, _addr1 = value_chunk.block_addr
    chip.memory[addr0] ^= 0xFF  # first byte of the on-chip timestamp field itself

    async def read_data() -> tuple[int | None, int | None, bytearray | None]:
        return await value_chunk.read()

    assert run(read_data()) == (None, None, None)  # hard fail, not a silently wrong timestamp


def test_pause_blocks_persisted_write_but_in_memory_error_tracking_still_works() -> None:
    # print_log.py's own "in-memory count/history updates regardless of persistence success"
    # contract, proven here for the pause fault mode specifically (previously only proven for a
    # real chip.drop_wren fault) - and, unlike that test, verified by directly confirming no byte
    # anywhere on the simulated chip changed while paused, not just that the read-back matched.
    manager, chip = make_manager()
    run(manager.setup())
    reader = SensorReader(Meas(1.0, 1), 3, fram=manager)
    run(reader.pr.setup())
    before = bytes(chip.memory)
    manager.set_pause(True)

    async def scenario() -> int:
        await reader.pr.err_s("paused write", errno=11)
        return reader.pr.err_count

    err_count = run(scenario())
    assert err_count == 1  # in-memory tracking unaffected by pause
    assert bytes(chip.memory) == before  # nothing was actually written to FRAM while paused


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
