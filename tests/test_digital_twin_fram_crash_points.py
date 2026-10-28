"""Crash consistency on the twin chip, power lost after every SPI transaction of one chunk write and of the FRAM erase:
"After an abrupt reset a FRAM-backed history restores completely or not at all, never partially or garbled, and the
chunk accepts writes afterwards" (owner, 2026-09-26). One write per boot; mid-byte loss is the bench's (L3)."""

import sys

sys.path.insert(0, "digital_twin")  # the twin's machine ahead of tests/'s own (test_digital_twin_machine.py says why)

import machine
import microtest
from _async_harness import run
from _error_codes import code
from _twin_devices import generated_devices, wiring_plan

from asy_crc_checks import CRC32
from asy_fram_manager import FRAMManager
from asy_print_log import LogConfig, PrintLogHistoryStore
from asy_spi_driver import SPI
from voc_algorithm import VOCAlgorithm

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from _fram_chip import _PagedMemory
    from _twin_devices import TwinWiringPlan

    from asy_fram_manager import FRAMTimestampedChunk

_IMAGE_PAGE = 4096  # bytes per piece of a kept chip image
_ARMED_FOREVER = 1 << 30  # a dry run's countdown: never reached, so what is left of it counts the transactions made
_LOGGER = "CRASH"  # the logger store's owner name: its chunk's CRC seed
_STORES = ("CRASH_A", "CRASH_B", "CRASH_C")  # the erase case's rings, allocated in this order on every boot
_COPIES_DIFFER = ("E", code("E", "FRAM_COPIES_DIFFER"))
# What a torn block may leave behind when the chunk layer repairs or refuses it (asy_fram_manager.py's read path).
_TORN_TRACES = {
    ("E", code("E", "FRAM_STATUS_BYTE")),
    ("E", code("E", "FRAM_STATUS_DISAGREE")),
    ("E", code("E", "FRAM_DATA_CRC")),
    ("E", code("E", "FRAM_COPIES_DIFFER")),
    ("W", code("W", "FRAM_BLOCK_INVALID")),
}

microtest.after_each(machine.reset_test_state)


class _Board:
    # One power-up of the plan's FRAM bus: a fresh chip holding `image` (kept pages, or the chip just powered off's own
    # memory, adopted rather than copied), a fresh manager over it, set up.
    def __init__(self, plan: "TwinWiringPlan", image: "list[bytes] | _PagedMemory | None") -> None:
        (bus_name,) = plan["spi"]
        pins = plan["pins"][bus_name]
        size = plan["spi"][bus_name]["max_size"]
        machine.reset_peripherals()  # a power cycle: buses and chips rebuilt, the plan kept
        self.manager = FRAMManager(SPI(int(bus_name[3:]), pins["sck"], pins["mosi"], pins["miso"]), 1, max_size=size, log=LogConfig(None, 16, None))  # type: ignore[typeddict-item]  # an SPI bus's pins
        bus = machine.peripheral(bus_name)
        assert isinstance(bus, machine.SPI) and bus.device is not None
        self.bus, self.chip = bus, bus.device
        if isinstance(image, list):  # page by page: a 256 KB image is never one contiguous allocation
            start = 0
            for page in image:
                self.chip.memory[start : start + len(page)] = memoryview(page)
                start += len(page)
        elif image is not None:
            self.chip.memory = image
        assert run(self.manager.setup()) is True

    def cut_after(self, k: int, work: "Callable[[], Coroutine[object, object, object]]") -> bool:
        # Runs `work` with power lost after k transactions; True when the loss struck before it finished.
        self.bus.lose_power_after(k)
        try:
            run(work())
        except machine.SimulatedPowerLoss:
            return True
        finally:
            self.bus._power_left = None  # the board is powered off either way; nothing more runs on it
        return False

    def image(self) -> "list[bytes]":
        size = len(self.chip.memory)
        return [bytes(self.chip.memory[start : start + _IMAGE_PAGE]) for start in range(0, size, _IMAGE_PAGE)]

    def traces(self) -> "set[tuple[str, int]]":
        log = run(self.manager.get_error_counter())[self.manager.pr.name]
        return {(log["ErrType"][i], log["ErrNum"][i]) for i in range(len(log["ErrNum"])) if log["ErrType"][i] != "N"}

    def transactions(self, work: "Callable[[], Coroutine[object, object, object]]") -> int:
        # A dry run of `work`: the SPI transactions it makes.
        self.bus.lose_power_after(_ARMED_FOREVER)
        run(work())
        left = self.bus._power_left
        self.bus._power_left = None
        assert left is not None
        return _ARMED_FOREVER - left


def _backup(board: _Board) -> "FRAMTimestampedChunk":
    async def unsynced() -> bool:
        return False

    chunk = board.manager.get_timestamped_chunk(VOCAlgorithm.get_params_memsize(), unsynced, crc=CRC32(), owner="SGP40_VOC")
    assert chunk is not None
    return chunk


async def _backup_write(chunk: "FRAMTimestampedChunk", data: "bytes | bytearray") -> None:
    ok, _synced, _ts = await chunk.write(data)
    assert ok


def _backup_writer(chunk: "FRAMTimestampedChunk", data: bytearray) -> "Callable[[], Coroutine[object, object, None]]":
    # The work a cut interrupts: one backup write of `data`.
    def work() -> "Coroutine[object, object, None]":
        return _backup_write(chunk, data)

    return work


def _blank(store: PrintLogHistoryStore) -> "tuple[int, tuple[int, ...]]":
    # The state a logger sets up over a chunk with no usable history: no entries, a zero count.
    return 0, (0,) * len(store.history)


def _configure(plan: "TwinWiringPlan") -> None:
    machine.reset_peripherals()
    machine.configure_wiring(plan)


def _erase(board: _Board, marks: "list[int] | None" = None) -> "Callable[[], Coroutine[object, object, object]]":
    # The product's erase; `marks` records the transaction count at each of its feed points (a dry run's).
    def step_done() -> None:
        if marks is not None and board.bus._power_left is not None:
            marks.append(_ARMED_FOREVER - board.bus._power_left)

    async def erase() -> None:
        assert await board.manager.erase_chip(step_done) is True

    return erase


def _logger_state(store: PrintLogHistoryStore) -> "tuple[int, tuple[int, ...]] | bool | None":
    return run(store._read())


def test_a_logger_write_cut_after_every_transaction_restores_the_old_or_the_new_history() -> None:
    for plan in _plans_by_size():
        _configure(plan)
        board = _Board(plan, None)
        store = PrintLogHistoryStore(board.manager, name=_LOGGER)
        assert run(store.setup()) is True
        run(store.err_s("history A", errno=code("E", "TEST_SEED_A")))
        old_image, old = board.image(), _logger_state(store)

        count = board.transactions(_logger_write(store, "history B", "TEST_SEED_B"))
        new = _logger_state(store)
        assert old != new and isinstance(old, tuple) and isinstance(new, tuple), (old, new)
        kept: list[bytes] = []
        for k in range(count + 1):
            board = _Board(plan, old_image)
            store = PrintLogHistoryStore(board.manager, name=_LOGGER)
            run(store.setup())
            cut = board.cut_after(k, _logger_write(store, "history B", "TEST_SEED_B"))
            assert cut or k == count, f"size {plan['spi']}: the cut after {k} of {count} transactions never struck"
            if _unchanged(board.chip.memory, kept):
                continue  # the last checked cut's image, byte for byte: its restore already checked
            kept = [bytes(page) for page in board.chip.memory._pages]
            board = _Board(plan, board.chip.memory)
            store = PrintLogHistoryStore(board.manager, name=_LOGGER)
            assert run(store.setup()) is True, f"cut after {k}: the restored logger did not set up"
            restored, traces = _logger_state(store), board.traces()
            # Not at all is allowed only with its trace: two valid but differing copies are never guessed between.
            assert restored in (old, new) or (restored == _blank(store) and _COPIES_DIFFER in traces), f"cut after {k} of {count}: restored {restored} with {traces}, neither the old {old} nor the new {new}"
            assert traces <= _TORN_TRACES, f"cut after {k}: setup logged {traces - _TORN_TRACES}"
            run(store.err_s("history C", errno=code("E", "TEST_SEED_C")))
            written = _logger_state(store)
            assert written == (store._err_count, tuple(store.history)) != restored, f"cut after {k}: the next write read back {written}"


def _logger_write(store: PrintLogHistoryStore, text: str, seed: str) -> "Callable[[], Coroutine[object, object, None]]":
    # The work a cut interrupts: one logged error, which writes the store's chunk.
    def work() -> "Coroutine[object, object, None]":
        return store.err_s(text, errno=code("E", seed))

    return work


def test_a_backup_write_cut_after_every_transaction_restores_the_old_or_the_new_backup() -> None:
    size = VOCAlgorithm.get_params_memsize()
    old_data, new_data, last_data = bytearray([0x11] * size), bytearray([0x22] * size), bytearray([0x33] * size)
    for plan in _plans_by_size():
        _configure(plan)
        board = _Board(plan, None)
        chunk = _backup(board)
        run(_backup_write(chunk, old_data))
        old_image = board.image()
        count = board.transactions(_backup_writer(chunk, new_data))
        kept: list[bytes] = []
        for k in range(count + 1):
            board = _Board(plan, old_image)
            chunk = _backup(board)
            cut = board.cut_after(k, _backup_writer(chunk, new_data))
            assert cut or k == count, f"the cut after {k} of {count} transactions never struck"
            if _unchanged(board.chip.memory, kept):
                continue  # the last checked cut's image, byte for byte: its restore already checked
            kept = [bytes(page) for page in board.chip.memory._pages]
            board = _Board(plan, board.chip.memory)
            chunk = _backup(board)
            _ts, _age, restored = run(chunk.read())
            traces = board.traces()
            assert restored in (old_data, new_data) or (restored is None and _COPIES_DIFFER in traces), f"cut after {k} of {count}: restored {restored} with {traces}"
            assert traces <= _TORN_TRACES, f"cut after {k}: the read logged {traces - _TORN_TRACES}"
            run(_backup_write(chunk, last_data))
            assert run(chunk.read())[2] == last_data, f"cut after {k}: the next backup did not read back"


def _plans_by_size() -> "list[TwinWiringPlan]":
    # One generated plan per FRAM size the devices declare, the first device of each size.
    found: dict[int, TwinWiringPlan] = {}
    for device in generated_devices():
        plan = wiring_plan(device)
        for attachment in plan["spi"].values():
            found.setdefault(attachment["max_size"], plan)
    assert found, "no generated device wires a FRAM"
    return [found[size] for size in sorted(found)]


def _rings(board: _Board) -> "list[PrintLogHistoryStore]":
    stores = [PrintLogHistoryStore(board.manager, name=name) for name in _STORES]
    for store in stores:
        run(store.setup())
    return stores


def _unchanged(memory: "_PagedMemory", kept: "list[bytes]") -> bool:
    # Whether a cut left exactly the image `kept` holds, compared page by page.
    return len(kept) == len(memory._pages) and all(memory._pages[i] == kept[i] for i in range(len(kept)))


def test_an_erase_cut_inside_its_blanking_pass_or_its_first_and_last_units_restores_each_ring_or_blanks_it() -> None:
    # The largest generated FRAM: every cut inside pass 1 (each chunk marked blank), then every cut inside the first and
    # the last pass-2 unit over each allocated chunk; a fresh boot reads each ring exactly as written, or blank.
    plan = _plans_by_size()[-1]
    _configure(plan)
    board = _Board(plan, None)
    stores = _rings(board)
    for i, store in enumerate(stores):
        run(store.err_s("ring", i, errno=code("E", ("TEST_SEED_A", "TEST_SEED_B", "TEST_SEED_C")[i])))
    written = [_logger_state(store) for store in stores]
    old_image = board.image()
    unit = 256  # asy_fram_manager.py's _ERASE_UNIT
    spans = [(chunk._block_addr[0], 2 * chunk._block_addr[1] - chunk._block_addr[0]) for chunk in board.manager._chunks]
    marks: list[int] = []
    board.transactions(_erase(board, marks))
    pass1_end = marks[len(board.manager._chunks) - 1]
    cuts = set(range(pass1_end + 1))
    for first, last in spans:
        for u in (first // unit, (last - 1) // unit):
            mark = len(board.manager._chunks) + u  # the feed after unit u
            cuts.update(range(marks[mark - 1], marks[mark] + 1))
    blank = _blank(stores[0])
    kept: list[bytes] = []
    for k in sorted(cuts):
        board = _Board(plan, old_image)
        _rings(board)
        assert board.cut_after(k, _erase(board)), f"the erase finished before the cut after {k} transactions"
        if _unchanged(board.chip.memory, kept):
            continue  # the last checked cut's image, byte for byte: its restore already checked
        kept = [bytes(page) for page in board.chip.memory._pages]
        board = _Board(plan, board.chip.memory)
        restored = [_logger_state(store) for store in _rings(board)]
        for i, state in enumerate(restored):
            assert state in (written[i], blank), f"cut after {k}: ring {_STORES[i]} restored {state}, not {written[i]} or blank"
        assert board.traces() <= _TORN_TRACES, f"cut after {k}: the boot logged {board.traces() - _TORN_TRACES}"


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
