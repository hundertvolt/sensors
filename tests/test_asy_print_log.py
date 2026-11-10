"""PrintLogHistory and its FRAM store: levels, the bounded history and its count cap, the one-slot repeat rule, the boot
window and persistence across a reboot."""

import struct
from collections import deque

import micropython
from _async_harness import run
from _error_codes import code
from _fram_builders import make_fram_manager
from _recording_print import record_prints
from _src_const import src_const
from _stack_overflow import stack_overflow

import asy_print_log as print_log_module
from asy_base_classes import RegionBuffer
from asy_fram_manager import FRAMChunk
from asy_print_log import DEFAULT_LOG, LogConfig, PrintLog, PrintLogHistory, PrintLogHistoryStore, fatal_reported, make_logger, report_if_fatal

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:

    from crc_checks import CRCBase


class _RaisingFramChunk:
    # Fails only by allocation, the one failure the real chunk documents (SPECIFICATION.md C.7); parameter names
    # stay exact so mypy checks the fake against asy_print_log's Protocols. `error` swaps in another class.
    def __init__(
        self, *, raise_on_write: bool = False, raise_on_read: bool = False, none_buffer: bool = False, error: "Exception | None" = None,
    ) -> None:
        self.raise_on_write = raise_on_write
        self.raise_on_read = raise_on_read
        self.none_buffer = none_buffer
        self.error = MemoryError("simulated allocation failure") if error is None else error

    def get_buffer(self) -> "RegionBuffer":
        buf = RegionBuffer(6, data_start=0, data_length=6)
        if self.none_buffer:
            buf._buf = None  # the shape a failed buffer allocation leaves
        return buf

    def write_into(self, buf: "RegionBuffer") -> bool:
        if self.raise_on_write:
            raise self.error
        return True

    def read_into(self, buf: "RegionBuffer") -> bool:
        if self.raise_on_read:
            raise self.error
        return True


class _RaisingFramManager:
    def __init__(self, chunk: "_RaisingFramChunk | None", *, raise_on_get_chunk: bool = False, error: "Exception | None" = None) -> None:
        self._chunk = chunk
        self.raise_on_get_chunk = raise_on_get_chunk
        self.error = MemoryError("simulated allocation failure") if error is None else error

    # Fails only by allocation, the one failure the real chunk documents (SPECIFICATION.md C.7); parameter names
    # stay exact so mypy checks the fake against asy_print_log's Protocols.
    def get_chunk(
        self, size: int, crc: "CRCBase | None" = None, verify: int = 0, *, owner: str,
    ) -> "_RaisingFramChunk | None":
        if self.raise_on_get_chunk:
            raise self.error
        return self._chunk

    def get_pause(self) -> bool:
        return False


class _CountingFramManager:
    def __init__(self, chunk: "_CountingFramChunk") -> None:
        self._chunk = chunk
        self.paused = False  # what get_pause() answers; the chunk's own write_result models the refusal

    # Parameter names kept exact for the structural _FramManager Protocol match (see _RaisingFramManager).
    def get_chunk(
        self, size: int, crc: "CRCBase | None" = None, verify: int = 0, *, owner: str,
    ) -> "_CountingFramChunk":
        return self._chunk

    def get_pause(self) -> bool:
        return self.paused


# ---------------------------------------------------------------------------
# PrintLog - levels 0 (off) .. 5 (all), clamped into that range
# ---------------------------------------------------------------------------


def test_set_level_none_is_off() -> None:
    assert PrintLog(None).level == 0


def test_set_level_clamps_below_off_and_above_all() -> None:
    assert PrintLog(-5).level == 0
    pr = PrintLog(2)
    pr.set_level(10)
    assert pr.level == 5


def test_set_level_valid_value_passes_through() -> None:
    pr = PrintLog(2)
    assert pr.level == 2


def test_each_level_prints_exactly_its_lines() -> None:
    expected = {0: [], 1: ["e"], 5: ["e", "w", "o", "v", "a"]}
    for level, lines in expected.items():
        pr = PrintLog(level)
        with record_prints() as rec:
            pr.err("e")
            pr.wrn("w")
            pr.one("o")
            pr.evt("v")
            pr.all("a", sep="-")
        assert [line[1] for line in rec.lines] == lines, level
    pr = PrintLog(5)
    with record_prints() as rec:
        pr.all("a", "b", sep="-", end="!")
    assert rec.kwargs == [{"sep": "-", "end": "!"}]  # the keywords reach print() as given


def test_set_level_exact_boundary_values_pass_through_unclamped() -> None:
    pr = PrintLog(0)
    assert pr.level == 0
    pr.set_level(5)
    assert pr.level == 5


def test_name_defaults_to_empty_string() -> None:
    pr = PrintLog()
    assert pr.name == ""


def test_name_is_stored_verbatim_when_given() -> None:
    pr = PrintLog(name="SGP40")
    assert pr.name == "SGP40"


# ---------------------------------------------------------------------------
# PrintLogHistory - bounded in-memory error/warning history
# ---------------------------------------------------------------------------


def test_initial_state_is_all_clear() -> None:
    hist = PrintLogHistory(history_length=4)
    assert hist._err_count == 0
    assert hist.initialized is False
    assert list(hist.history) == [0, 0, 0, 0]


def test_setup_marks_initialized() -> None:
    hist = PrintLogHistory()
    run(hist.setup())
    assert hist.initialized is True


def test_read_stub_always_true_on_the_in_memory_class() -> None:
    hist = PrintLogHistory()
    assert hist._read() is True  # no persistence to load in the pure in-memory case


def test_err_s_increments_count_and_records_history() -> None:
    hist = PrintLogHistory(history_length=4)
    hist.err_s("boom", errno=3)
    assert hist._err_count == 1
    assert list(hist.history)[-1] == 3  # _NO_ERR (0) + errno (3)


def test_wrn_s_records_in_the_warning_sub_range() -> None:
    hist = PrintLogHistory(history_length=4)
    hist.wrn_s("careful", wrnno=2)
    assert hist._err_count == 1
    assert list(hist.history)[-1] == 0x80 + 2  # _NO_WRN + wrnno


def test_err_s_default_errno_increments_count_but_not_history() -> None:
    # errno=0 (_NO_ERR, the default) still bumps the counter, but _store_err returns before
    # appending anything to history - a real, easy-to-miss asymmetry worth pinning down.
    hist = PrintLogHistory(history_length=4)
    hist.err_s("just counting")
    assert hist._err_count == 1
    assert list(hist.history) == [0, 0, 0, 0]


def test_history_is_bounded_and_drops_oldest() -> None:
    hist = PrintLogHistory(history_length=3)
    for errno in (1, 2, 3, 4):
        hist.err_s("e", errno=errno)
    assert list(hist.history) == [2, 3, 4]  # oldest (1) fell off the bounded deque


def test_err_count_saturates_at_max_and_never_wraps() -> None:
    hist = PrintLogHistory(history_length=2)
    hist._err_count = 0xFFFE  # one below _MAX_CNT - whitebox-set to avoid 65534 real calls
    hist.err_s("e", errno=1)
    assert hist._err_count == 0xFFFF  # reaches the cap exactly, a normal step
    hist.err_s("e", errno=2)  # a different code: the ring still takes it
    assert hist._err_count == 0xFFFF  # saturates, does not wrap to 0
    assert list(hist.history) == [1, 2]


def test_errno_beyond_its_sub_range_is_not_recorded() -> None:
    # errno=200 pushed past _MAX_ERR (0x7F) once _NO_ERR is added - out of the valid error
    # sub-range, so the count still increments but nothing is appended to history.
    hist = PrintLogHistory(history_length=2)
    hist.err_s("e", errno=200)
    assert hist._err_count == 1
    assert list(hist.history) == [0, 0]


def test_reset_clears_history_and_count() -> None:
    hist = PrintLogHistory(history_length=3)
    run(hist.setup())
    hist.err_s("e", errno=1)
    assert run(hist.reset()) is True
    assert hist._err_count == 0
    assert list(hist.history) == [0, 0, 0]


def test_a_ram_only_reset_allocates_nothing() -> None:
    # The clear works in place by deque item assignment (py/objdeque.c, v1.29.0): no list or tuple, whatever the ring's
    # length. The coroutine is built before the heap is locked, so the lock sees the reset's own body only.
    hist = PrintLogHistory(history_length=64)
    run(hist.setup())
    hist.err_s("e", errno=3)
    reset = hist.reset()
    outcome: list[object] = [None]
    micropython.heap_lock()
    try:
        reset.send(None)
    except StopIteration as stop:
        outcome[0] = stop.value
    except MemoryError:  # the locked heap's refusal, never printed: its text is what the memory gates match
        outcome[0] = "allocated"
    finally:
        micropython.heap_unlock()
    assert outcome[0] is True, outcome
    assert (hist._err_count, list(hist.history)) == (0, [0] * 64)


def test_get_log_classifies_error_warning_and_clear_entries() -> None:
    hist = PrintLogHistory(history_length=3, name="Sensor")
    hist.err_s("e", errno=5)  # oldest slot (still the initial _NO_ERR) falls off -> "E", 5
    hist.wrn_s("w", wrnno=2)  # -> "W", 2
    # remaining oldest slot is still the initial _NO_ERR -> "N", 0
    log = run(hist.get_log())
    assert log == {"Sensor": {"ErrCount": 2, "ErrNum": [0, 5, 2], "ErrType": ["N", "E", "W"]}}


class _DiagRecordingHistory(PrintLogHistory):
    # Records the internal-failure prints instead of gating them on a level, so a test can assert one fired.
    def __init__(self, history_length: int) -> None:
        super().__init__(history_length=history_length)
        self.diags: list[tuple[object, ...]] = []

    def _diag(self, *args: object) -> None:
        self.diags.append(args)


def test_a_negative_code_is_counted_diagnosed_and_takes_no_slot() -> None:
    hist = _DiagRecordingHistory(history_length=2)
    hist.err_s("e", errno=-3)
    hist.wrn_s("w", wrnno=-1)
    assert hist._err_count == 2
    assert list(hist.history) == [0, 0]
    assert [d[:3] for d in hist.diags if "is invalid!" in d] == [("PrintLog: Error number", -3, "is invalid!"), ("PrintLog: Error number", -1, "is invalid!")]


class _CountingFramChunk:
    # Counts the write-throughs a store makes and keeps the last payload; a read answers read_result (False: blank,
    # None: unreadable, True: `stored` copied into the buffer).
    def __init__(self, size: int, *, read_result: "bool | None" = False, stored: bytes = b"", write_result: bool = True) -> None:
        self.size = size
        self.writes = 0
        self.read_result = read_result
        self.stored = stored
        self.write_result = write_result
        self.last_payload: bytes | None = None

    # Parameter names kept exact for the structural _FramChunk Protocol match (see _RaisingFramChunk).
    def get_buffer(self) -> "RegionBuffer":
        return RegionBuffer(self.size, data_start=0, data_length=self.size)

    def write_into(self, buf: "RegionBuffer") -> bool:
        self.writes += 1
        dbuf = buf.get_data_buf()
        assert dbuf is not None
        self.last_payload = bytes(dbuf)
        return self.write_result

    def read_into(self, buf: "RegionBuffer") -> bool | None:
        if self.read_result:
            dbuf = buf.get_data_buf()
            assert dbuf is not None
            dbuf[: len(self.stored)] = self.stored
        return self.read_result


def _sustained_identical_code_spends_one_slot(hist: "PrintLogHistory", writes: "_CountingFramChunk | None") -> None:
    # Shared body of the per-history-type tests below: the newest-entry rule, SPECIFICATION.md Part C.7.1.
    run(hist.setup())
    writes_before = 0 if writes is None else writes.writes
    hist.err_s("earlier", errno=3)
    hist.wrn_s("earlier", wrnno=2)
    with record_prints() as rec:
        for _ in range(10):
            hist.err_s("sustained", errno=5)
    assert list(hist.history) == [0, 3, 0x80 + 2, 5]  # the earlier entries intact, one slot for the ten
    assert hist._err_count == 12
    assert [line for line in rec.lines if "sustained" in line] == [(hist.name, "sustained")] * 10  # console unfiltered
    if writes is not None:
        assert writes.writes - writes_before == 12  # one write-through per call, a repeat included
    hist.err_s("other", errno=6)  # a different code between spends a slot
    hist.err_s("again", errno=5)
    assert list(hist.history) == [0x80 + 2, 5, 6, 5]
    hist.err_s("recurring", errno=5)  # recovered (nothing logged), then the same code again: no new slot
    assert list(hist.history) == [0x80 + 2, 5, 6, 5]
    hist.wrn_s("same number as a warning", wrnno=5)  # the other kind is a different code
    assert list(hist.history) == [5, 6, 5, 0x80 + 5]
    assert hist._err_count == 16


def test_a_sustained_identical_code_spends_one_slot() -> None:
    _sustained_identical_code_spends_one_slot(PrintLogHistory(history_length=4, level=1, name="H"), None)


def test_a_sustained_identical_code_spends_one_slot_in_the_store() -> None:
    chunk = _CountingFramChunk(2 + 4)  # the store's "<H" header plus four history bytes
    store = PrintLogHistoryStore(_CountingFramManager(chunk), history_length=4, level=1, name="S")
    _sustained_identical_code_spends_one_slot(store, chunk)
    assert store.initialized is True


def test_get_log_reports_an_empty_warning_slot_as_no_entry() -> None:
    hist = PrintLogHistory(history_length=2, name="Sensor")
    hist.history.extend([0x80, 0x80 + 2])  # whitebox: the warning sentinel byte beside a real W2
    log = run(hist.get_log())
    assert log == {"Sensor": {"ErrCount": 0, "ErrNum": [0, 2], "ErrType": ["N", "W"]}}


def test_printloghistory_forwards_name_to_the_base_class() -> None:
    hist = PrintLogHistory(history_length=2, name="SGP40")
    assert hist.name == "SGP40"


def test_get_log_with_no_argument_and_no_name_set_falls_back_to_empty_string() -> None:
    hist = PrintLogHistory(history_length=1)
    log = run(hist.get_log())
    assert "" in log


def test_get_log_with_no_argument_uses_self_name() -> None:
    # Regression coverage for a real test-authoring mistake caught while trialing this design:
    # history_length=1 leaves no initial _NO_ERR slot to survive a single err_s() call, so this assertion
    # does not depend on the "leftover initial slot" shape the classification test above already covers.
    hist = PrintLogHistory(history_length=1, name="SGP40")
    hist.err_s("e", errno=1)
    log = run(hist.get_log())
    assert log == {"SGP40": {"ErrCount": 1, "ErrNum": [1], "ErrType": ["E"]}}


def test_get_log_takes_no_name_of_its_own() -> None:
    # The logger's own name is the one it reports under: no src/ caller ever passed another.
    hist = PrintLogHistory(history_length=1, name="SGP40")
    refused = False
    try:
        run(hist.get_log("Override"))  # type: ignore[call-arg]
    except TypeError:
        refused = True
    assert refused


def test_err_s_errno_at_exact_max_err_boundary_is_recorded() -> None:
    hist = PrintLogHistory(history_length=2)
    hist.err_s("e", errno=0x7F)  # _MAX_ERR itself - inclusive boundary
    assert list(hist.history)[-1] == 0x7F


def test_err_s_errno_one_past_max_err_boundary_is_not_recorded() -> None:
    hist = PrintLogHistory(history_length=2)
    hist.err_s("e", errno=0x80)  # one past _MAX_ERR - falls into the warning sub-range instead
    assert hist._err_count == 1
    assert list(hist.history) == [0, 0]


def test_wrn_s_wrnno_at_exact_max_boundary_is_recorded() -> None:
    hist = PrintLogHistory(history_length=2)
    hist.wrn_s("w", wrnno=0x7F)  # _NO_WRN + 0x7F == _MAX_WRN, inclusive boundary
    assert list(hist.history)[-1] == 0xFF


def test_wrn_s_wrnno_one_past_max_boundary_is_not_recorded() -> None:
    hist = PrintLogHistory(history_length=2)
    hist.wrn_s("w", wrnno=0x80)  # _NO_WRN + 0x80 == 0x100, past _MAX_WRN (0xFF)
    assert hist._err_count == 1
    assert list(hist.history) == [0, 0]


def test_history_length_zero_never_records_but_still_counts() -> None:
    # An unusual but typed-valid construction: a zero-length bounded deque. Empirically confirmed
    # under the real MicroPython interpreter that append()/extend() on it are silent no-ops, not
    # a crash.
    hist = PrintLogHistory(history_length=0)
    hist.err_s("e", errno=1)
    assert hist._err_count == 1
    assert list(hist.history) == []


def test_history_length_negative_is_clamped_to_zero_not_a_raise() -> None:
    # deque(maxlen=…) raises ValueError on a negative maxlen (pinned interpreter); the constructor clamps it to zero.
    hist = PrintLogHistory(history_length=-5)
    assert list(hist.history) == []
    hist.err_s("e", errno=1)
    assert hist._err_count == 1


def test_history_length_huge_is_capped_instead_of_crashing_the_interpreter() -> None:
    # A typed-valid but wildly unusual int input: confirmed against the pinned Unix-port interpreter that
    # `[x] * n`, what building this deque does internally, segfaults the whole process for some huge-but-
    # representable n, with no catchable exception at all.
    #
    # MemoryError only covers smaller sizes and OverflowError only n at or above the machine-word boundary,
    # leaving an uncatchable gap between. The fix caps the input before attempting the allocation, and this
    # pins that the cap holds, not just that construction does not raise.
    hist = PrintLogHistory(history_length=2**62)
    assert len(hist.history) <= 0xFFFF
    hist.err_s("e", errno=1)
    assert hist._err_count == 1


class _RaisingDeque:
    # PrintLogHistory.__init__()'s except MemoryError fallback cannot be forced deterministically through a
    # real allocation at any size small enough to be safe in a test, so it is faked by substituting
    # asy_print_log's own module-level `deque` name, as this project's other suites do for unreachable guards.
    #
    # Only the first, nonzero-maxlen call raises: the except block's own deque([], 0) fallback must still
    # succeed normally, matching what a memory-constrained device's tiny recovery allocation would do.
    def __call__(self, iterable: "list[int]", maxlen: int) -> "deque[int]":
        if maxlen == 0:
            return deque(iterable, maxlen)
        raise MemoryError("injected for the history ring")  # worded clear of the memory gates' markers


def test_a_failed_history_allocation_prints_its_text_and_keeps_a_zero_ring() -> None:
    original_deque = print_log_module.deque
    print_log_module.deque = _RaisingDeque()  # type: ignore[assignment, misc]
    try:
        with record_prints() as rec:
            hist = PrintLogHistory(history_length=10, level=1, name="H")
    finally:
        print_log_module.deque = original_deque  # type: ignore[misc]
    assert len(hist.history) == 0
    assert [line for line in rec.lines if any("injected for the history ring" in str(a) for a in line)] == [rec.lines[0]]
    assert len(rec.lines) == 1  # the one diagnostic line, carrying the failure's own text
    hist.err_s("e", errno=1)
    assert hist._err_count == 1  # counting still works even though history recording can't
    assert run(hist.get_log()) == {"H": {"ErrCount": 1, "ErrNum": [], "ErrType": []}}  # no slot reported


def test_a_failed_history_allocation_prints_nothing_with_logging_off() -> None:
    # DebugLevel 0 prints nothing, the logging layer's own caught allocation failure included.
    original_deque = print_log_module.deque
    print_log_module.deque = _RaisingDeque()  # type: ignore[assignment, misc]
    try:
        with record_prints() as rec:
            hist = PrintLogHistory(history_length=10, name="H")
    finally:
        print_log_module.deque = original_deque  # type: ignore[misc]
    assert (hist.level, len(hist.history), rec.lines) == (0, 0, [])


def test_err_s_before_setup_does_not_write_even_with_logging_off() -> None:
    # The "not initialized" guard's *return* must not depend on self.level - only the diagnostic
    # print does. PrintLogHistory's own _write() is a no-op either way, but this pins the contract
    # down at the base-class level too (PrintLogHistoryStore's own FRAM-visible version follows below).
    hist = PrintLogHistory(history_length=4, level=0)
    assert hist.initialized is False
    hist.err_s("e", errno=1)
    assert hist._err_count == 1  # counting still happens
    assert list(hist.history)[-1] == 1  # in-memory recording still happens


def test_reset_before_setup_still_clears_even_with_logging_off() -> None:
    # The in-memory base has nothing to persist, so reset() is unconditional here either way -
    # what this pins down is that it never depends on the logging level to do its job.
    hist = PrintLogHistory(history_length=3, level=0)
    hist.err_s("e", errno=1)
    assert hist.initialized is False
    assert run(hist.reset()) is True
    assert hist._err_count == 0
    assert list(hist.history) == [0, 0, 0]


# ---------------------------------------------------------------------------
# PrintLogHistoryStore - FRAM-backed persistence, against the real, now-promoted FRAMManager
# driven by tests/_fram_chip_fake.py's simulated MB85RS64V chip.
# ---------------------------------------------------------------------------


def test_printloghistorystore_allocates_a_chunk_from_the_fram_manager() -> None:
    manager, _chip = make_fram_manager()
    store = PrintLogHistoryStore(manager, history_length=4)
    assert store.fram is not None


def test_printloghistorystore_forwards_name_to_the_base_class() -> None:
    manager, _chip = make_fram_manager()
    store = PrintLogHistoryStore(manager, history_length=4, name="FRAM")
    assert store.name == "FRAM"


def test_printloghistorystore_out_of_memory_leaves_fram_none_and_never_raises() -> None:
    manager, _chip = make_fram_manager(max_size=1)  # too small for any real chunk
    store = PrintLogHistoryStore(manager, history_length=4)
    assert store.fram is None
    assert store._write() is False
    assert store._read() is None  # nothing was read


def test_printloghistorystore_read_before_any_write_fails_cleanly() -> None:
    manager, _chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=4)
    assert store._read() is False  # chunk allocated but never written yet - not "all zero"


def test_printloghistorystore_setup_first_time_falls_back_to_writing_defaults() -> None:
    manager, _chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=4)
    run(store.setup())
    assert store.initialized is True


def test_printloghistorystore_setup_with_no_fram_returns_without_initializing() -> None:
    manager, _chip = make_fram_manager(max_size=1)
    store = PrintLogHistoryStore(manager, history_length=4)
    assert store.fram is None
    run(store.setup())
    assert store.initialized is False
    assert store.initialized is False  # nothing to set up - allocation already failed in __init__


def test_printloghistorystore_setup_is_idempotent_once_initialized() -> None:
    manager, _chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=4)
    run(store.setup())
    assert store.initialized is True
    store.err_s("boom", errno=1)
    assert store._err_count == 1
    run(store.setup())  # second call must be a no-op, not re-read stale state over the live count
    assert store.initialized is True
    assert store._err_count == 1


def test_printloghistorystore_err_s_persists_and_survives_a_simulated_reboot() -> None:
    manager, chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=4)
    run(store.setup())
    store.err_s("boom", errno=3)
    assert store._err_count == 1

    # Simulate a reboot: a fresh manager/store pair attached to the SAME underlying chip memory,
    # replaying the same get_chunk() call sequence - genuinely round-trips through the real
    # dual-copy+CRC on-chip format, the same as a real chip's contents surviving a power cycle.
    manager2, _chip2 = make_fram_manager()
    manager2.fram._spidev.spi._spi = chip
    run(manager2.setup())
    rebooted_store = PrintLogHistoryStore(manager2, history_length=4)
    run(rebooted_store.setup())
    assert rebooted_store._err_count == 1
    assert list(rebooted_store.history)[-1] == 3


def test_a_reset_while_storage_is_paused_clears_nothing_and_the_history_survives_the_pause() -> None:
    # A paused manager refuses every chunk write (asy_fram_manager.py's _write()), so the store answers False, writes
    # nothing and keeps its ring and count; the first write after the pause then carries them all.
    chunk = _CountingFramChunk(2 + 4)  # the store's "<H" header plus four history bytes
    manager = _CountingFramManager(chunk)
    store = PrintLogHistoryStore(manager, history_length=4)
    run(store.setup())
    store.err_s("first", errno=3)
    store.err_s("second", errno=4)
    writes = chunk.writes
    manager.paused, chunk.write_result = True, False
    assert run(store.reset()) is False
    assert (chunk.writes, store._err_count) == (writes, 2)
    assert list(store.history)[-2:] == [3, 4]
    manager.paused, chunk.write_result = False, True
    store.err_s("after the pause", errno=5)
    assert chunk.last_payload == bytes((3, 0, 0, 3, 4, 5))  # count 3, then the ring with every entry


def test_a_reset_whose_write_the_chip_refuses_clears_ram_and_answers_false() -> None:
    # A failure other than the pause keeps the reset's effect in RAM: the entries go, it answers False with its own
    # diagnostic, and the logger stays as initialised as it was.
    manager, chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=3, level=1, name="S")
    with record_prints(store):
        store.err_s("e", errno=3)
    chip.drop_wren = True  # every write-enable latch stays clear: the chip refuses each write
    with record_prints(store) as rec:
        assert run(store.reset()) is False
    assert (store._err_count, list(store.history), store.initialized) == (0, [0, 0, 0], False)
    assert rec.lines == [("S", "PrintLog: History reset write failed!")], rec.lines


def test_the_written_image_packs_without_allocating() -> None:
    # Every write, a reset's cleared image included, packs byte by byte into the chunk's own buffer, no tuple of the ring
    # and no list: the count in the header, the slots oldest first.
    chunk = _CountingFramChunk(2 + 64)
    store = PrintLogHistoryStore(_CountingFramManager(chunk), history_length=64)
    run(store.setup())
    store.err_s("before", errno=3)
    store.err_s("since", errno=4)
    dbuf = chunk.get_buffer().get_data_buf()
    assert dbuf is not None
    allocated = [False]
    micropython.heap_lock()
    try:
        store._pack(dbuf)
    except MemoryError:  # the locked heap's refusal, never printed: its text is what the memory gates match
        allocated[0] = True
    finally:
        micropython.heap_unlock()
    assert allocated == [False]
    assert bytes(dbuf) == bytes((2, 0)) + bytes(62) + bytes((3, 4))


def test_setup_initialises_a_ram_only_history_but_no_unusable_chunk() -> None:
    manager, chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=4)
    chip.drop_wren = True  # blank and unwritable: setup() can neither read nor write it
    run(store.setup())
    assert store.initialized is False
    no_chunk = PrintLogHistoryStore(make_fram_manager(max_size=1)[0], history_length=4)
    run(no_chunk.setup())
    assert no_chunk.initialized is False
    ram = PrintLogHistory(history_length=4)
    run(ram.setup())
    assert ram.initialized is True


def test_a_restored_0x80_byte_reads_back_as_no_entry() -> None:
    # A 0x80 byte in the stored ring (the warning sentinel, or a foreign image) is an empty slot, never ErrNum 128.
    manager, chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=3, name="Sensor")
    run(store.setup())
    store.history.extend([0x80, 5, 0x80])
    assert store._write() is True
    manager2, _chip2 = make_fram_manager()
    manager2.fram._spidev.spi._spi = chip  # same chip image - models a reboot
    run(manager2.setup())
    rebooted = PrintLogHistoryStore(manager2, history_length=3, name="Sensor")
    run(rebooted.setup())
    log = run(rebooted.get_log())
    assert log == {"Sensor": {"ErrCount": 0, "ErrNum": [0, 5, 0], "ErrType": ["N", "E", "N"]}}


def test_printloghistorystore_err_s_before_setup_does_not_touch_fram() -> None:
    # Regression test for a real bug: _store_err()'s "not initialized" guard used to return early only when
    # self.level > _LOG_OFF, so with logging off - the common production case - calling err_s() before
    # setup() had loaded the persisted state fell through to _write() anyway.
    #
    # That overwrote real FRAM-persisted history with a freshly-constructed, not-yet-loaded default. Fixed
    # so the return no longer depends on self.level.
    manager, chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=4, level=None)  # level=None -> _LOG_OFF
    assert store.initialized is False
    store.err_s("boom", errno=3)
    assert store._err_count == 1  # in-memory state still updates
    assert chip.memory == bytearray(len(chip.memory))  # but nothing was ever written to FRAM


def test_printloghistorystore_reset_before_setup_persists_the_cleared_state_anyway() -> None:
    # SPECIFICATION.md Part C.7: reset() deliberately has no "uninitialized" guard. A cleared ring is not
    # stale state - it is precisely what the caller asked to persist - so it goes to FRAM straight
    # away, which is what stops a later setup() restoring the old history over the top.
    manager, chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=4, level=None)
    assert store.initialized is False
    assert run(store.reset()) is True
    assert chip.memory != bytearray(len(chip.memory)), "the cleared ring never reached the chip"
    assert store.initialized is True, "a successful reset write means this logger is initialized by definition"


def test_printloghistorystore_reset_during_the_boot_window_is_not_undone_by_the_later_setup() -> None:
    # The whole point of SPECIFICATION.md Part C.7's boot window: every FRAM-backed logger runs its own pr.setup() from
    # inside its task, so the webserver can answer a ResetErrors PUT before that has happened.
    # The reset must survive the setup() that follows it, not be silently rolled back.
    manager, chip = make_fram_manager()
    run(manager.setup())
    seeded = PrintLogHistoryStore(manager, history_length=3)
    run(seeded.setup())
    seeded.err_s("e", errno=7)
    assert list(seeded.history)[-1] == 7

    manager2, _chip2 = make_fram_manager()
    manager2.fram._spidev.spi._spi = chip  # same chip image - models a reboot, history still on it
    run(manager2.setup())
    rebooted = PrintLogHistoryStore(manager2, history_length=3)
    assert rebooted.initialized is False  # its task has not reached pr.setup() yet
    assert run(rebooted.reset()) is True  # the PUT lands in that window
    run(rebooted.setup())  # ... and only now does the task get there
    assert rebooted._err_count == 0
    assert list(rebooted.history) == [0, 0, 0], "setup() restored the old history over a reset that had already been persisted"


def test_printloghistorystore_reset_that_cannot_reach_the_chip_stays_uninitialized() -> None:
    # The safety half of dropping the guard: claiming initialization on a FAILED write would make
    # the later setup() return early, leaving a logger that believes it is persisted and is not.
    manager, chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=4)
    chip.drop_wren = True  # every chip write silently does nothing from here on
    assert run(store.reset()) is False  # ResetErrors then answers "Failed" for this logger
    assert store.initialized is False
    run(store.setup())  # the chip is blank and its write is dropped: RAM-only
    assert store.initialized is False
    chip.drop_wren = False
    run(store.setup())
    assert store.initialized is True


def test_printloghistorystore_zero_length_history_survives_write_and_read() -> None:
    # An unusual but typed-valid construction (struct format collapses to just "H") - confirmed
    # directly this doesn't crash get_buffer()/pack_into/unpack_from at either end.
    manager, _chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=0)
    run(store.setup())
    assert store.initialized is True
    store.err_s("e", errno=1)
    assert store._err_count == 1
    assert list(store.history) == []
    assert store._read() == (1, ())  # the stored count and its (empty) entries


def test_printloghistorystore_write_uses_explicit_little_endian_layout() -> None:
    # Pins the on-the-wire format explicitly now that asy_print_log.py uses "<H"/"B"*n instead of a bare one -
    # confirmed directly that MicroPython's struct defaults a no-prefix format to "@", native alignment and
    # padding, not "<", though it made no observable difference for this field order.
    manager, chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=2)
    store._err_count = 0x1234
    store.history.extend([5, 6])
    assert store._history_fmt == "<BB"  # explicit little-endian, like the header's "<H"
    store._write()
    assert isinstance(store.fram, FRAMChunk)  # whitebox: narrows to the real chunk's own block layout
    addr0 = store.fram._block_addr[0]
    raw = bytes(chip.memory[addr0 : addr0 + 4])
    assert list(raw) == [0x34, 0x12, 5, 6]  # little-endian u16, then 2 raw history bytes


def test_printloghistorystore_reset_persists_cleared_state_across_a_reboot() -> None:
    manager, chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=3)
    run(store.setup())
    store.err_s("e", errno=1)
    assert run(store.reset()) is True

    manager2, _chip2 = make_fram_manager()
    manager2.fram._spidev.spi._spi = chip
    run(manager2.setup())
    rebooted_store = PrintLogHistoryStore(manager2, history_length=3)
    run(rebooted_store.setup())
    assert rebooted_store._err_count == 0
    assert list(rebooted_store.history) == [0, 0, 0]


def test_read_answers_the_stored_entries_false_or_none_and_mutates_nothing() -> None:
    blank = PrintLogHistoryStore(_CountingFramManager(_CountingFramChunk(2 + 3)), history_length=3)
    assert blank._read() is False
    unreadable = PrintLogHistoryStore(_CountingFramManager(_CountingFramChunk(2 + 3, read_result=None)), history_length=3)
    assert unreadable._read() is None
    chunk = _CountingFramChunk(2 + 3, read_result=True, stored=b"\x05\x00\x01\x02\x03")
    stored = PrintLogHistoryStore(_CountingFramManager(chunk), history_length=3)
    stored.err_s("pre", errno=9)
    assert stored._read() == (5, (1, 2, 3))
    assert list(stored.history) == [0, 0, 9]  # the read itself applies nothing
    assert stored._err_count == 1


def test_a_clean_read_of_a_valid_store_sets_up_without_writing() -> None:
    # Nothing logged before setup(): the chunk already holds exactly this state, so setup() writes nothing back.
    chunk = _CountingFramChunk(2 + 3, read_result=True, stored=b"\x02\x00\x00\x03\x07")
    store = PrintLogHistoryStore(_CountingFramManager(chunk), history_length=3)
    run(store.setup())
    assert store.initialized is True
    assert store._err_count == 2
    assert chunk.writes == 0


def test_a_blank_store_is_reinitialised() -> None:
    chunk = _CountingFramChunk(2 + 3)
    store = PrintLogHistoryStore(_CountingFramManager(chunk), history_length=3)
    run(store.setup())
    assert store.initialized is True
    assert chunk.writes == 1
    assert chunk.last_payload == bytes(5)


def test_an_unreadable_store_keeps_its_bytes_and_stays_ram_only() -> None:
    chunk = _CountingFramChunk(2 + 3, read_result=None)
    store = PrintLogHistoryStore(_CountingFramManager(chunk), history_length=3, name="U")
    run(store.setup())
    assert store.initialized is False
    store.err_s("later", errno=4)
    assert chunk.writes == 0  # nothing ever reached the chunk: the stored history stays for the next boot
    assert list(store.history) == [0, code("E", "LOG_RAM_ONLY"), 4]
    assert store._err_count == 2


def test_only_an_unreadable_store_records_its_ram_only_entry() -> None:
    # An unreadable chunk at setup() keeps one counted LOG_RAM_ONLY entry in its own ring, its line printed at level 1. A
    # heap failure of the chunk, a refused setup write, an allocator refusal and a blank store record nothing.
    unreadable = _CountingFramChunk(2 + 3, read_result=None)
    store = PrintLogHistoryStore(_CountingFramManager(unreadable), history_length=3, level=1, name="B")
    with record_prints() as rec:
        run(store.setup())
    assert (store.initialized, run(store.get_log())["B"]) == (False, {"ErrCount": 1, "ErrNum": [0, 0, code("E", "LOG_RAM_ONLY")], "ErrType": ["N", "N", "E"]})
    assert ("B", "FRAM history unreadable - RAM-only until reboot") in rec.lines, rec.lines
    assert unreadable.writes == 0
    refusing = _CountingFramChunk(2 + 3, write_result=False)
    silent = (
        PrintLogHistoryStore(_RaisingFramManager(None, raise_on_get_chunk=True), history_length=3, name="A"),
        PrintLogHistoryStore(_CountingFramManager(refusing), history_length=3, name="C"),
        PrintLogHistoryStore(_RaisingFramManager(None), history_length=3, name="R"),  # the allocator had no room left
        PrintLogHistoryStore(_CountingFramManager(_CountingFramChunk(2 + 3)), history_length=3, name="Z"),
    )
    for quiet in silent:
        run(quiet.setup())
        run(quiet.setup())  # a second setup() adds no entry either
        assert (quiet._err_count, code("E", "LOG_RAM_ONLY") in quiet.history) == (0, False), quiet.name
    assert refusing.writes == 2  # the refused setup write, tried again by the second setup()


# ---------------------------------------------------------------------------
# PrintLogHistoryStore - real FRAM failure modes injected at the simulated-chip level (the fault-injection
# knobs in tests/_fram_chip_fake.py, covered in their own right by test_asy_fram_driver.py), plus the two
# Protocol-level defensive-contract proofs with no real-class equivalent.
# ---------------------------------------------------------------------------


def test_printloghistorystore_get_chunk_raising_leaves_fram_none() -> None:
    # An allocation failure while the chunk is built (the one failure the real get_chunk() can meet) leaves the
    # store RAM-only: no chunk, every write and read refused without raising.
    store = PrintLogHistoryStore(_RaisingFramManager(None, raise_on_get_chunk=True), history_length=4)
    assert store.fram is None
    assert store._write() is False
    assert store._read() is None


def test_printloghistorystore_read_into_raising_is_caught() -> None:
    chunk = _RaisingFramChunk(raise_on_read=True)
    store = PrintLogHistoryStore(_RaisingFramManager(chunk), history_length=4)
    assert store._read() is None  # unreadable, not blank: setup() must not overwrite the store


def test_a_none_data_buffer_fails_write_and_read_without_raising() -> None:
    chunk = _RaisingFramChunk(none_buffer=True)
    store = PrintLogHistoryStore(_RaisingFramManager(chunk), history_length=4)
    assert store._write() is False
    assert store._read() is None
    run(store.reset())
    store.err_s("e", errno=1)
    assert store._err_count == 1  # the entry still counts in RAM


def test_each_caught_chunk_allocation_failure_prints_its_text_at_level_1_and_nothing_at_level_0() -> None:
    # One line per occurrence from level 1 up, carrying the error's own text: the chunk's allocation, a read, a write.
    for level in (0, 1):
        err = MemoryError("injected for the chunk allocation")
        with record_prints() as rec:
            store = PrintLogHistoryStore(_RaisingFramManager(None, raise_on_get_chunk=True, error=err), history_length=4, level=level, name="A")
        assert store.fram is None
        assert rec.lines == [("A", "PrintLog: FRAM allocation failed:", err)] * level, (level, rec.lines)
        for kwargs, text in (({"raise_on_read": True}, "injected for the history read"), ({"raise_on_write": True}, "injected for the history write")):
            err = MemoryError(text)
            store = PrintLogHistoryStore(_RaisingFramManager(_RaisingFramChunk(error=err, **kwargs)), history_length=4, level=level, name="B")
            with record_prints() as rec:
                results = [store._read() if "raise_on_read" in kwargs else store._write() for _ in range(2)]
            assert results == ([None, None] if "raise_on_read" in kwargs else [False, False]), (text, results)
            what = "read" if "raise_on_read" in kwargs else "write"
            assert rec.lines == [("B", "PrintLog: FRAM history " + what + " failed:", err)] * 2 * level, (level, text, rec.lines)


def test_an_allocator_refusal_prints_only_its_gated_line() -> None:
    # A chunk the allocator refused is no heap failure: the gated line at a level, nothing with logging off.
    for level, lines in ((None, []), (1, [("R", "PrintLog: FRAM allocation failed!")])):
        with record_prints() as rec:
            PrintLogHistoryStore(_RaisingFramManager(None), history_length=4, level=level, name="R")
        assert rec.lines == lines, (level, rec.lines)
    with record_prints() as rec:  # a heap failure at a level prints its one ungated line, not the gated one too
        PrintLogHistoryStore(_RaisingFramManager(None, raise_on_get_chunk=True, error=MemoryError("injected for one line")), history_length=4, level=1, name="R")
    assert [line[:2] for line in rec.lines] == [("R", "PrintLog: FRAM allocation failed:")]


def test_a_non_allocation_failure_from_a_chunk_propagates() -> None:
    # The catch is allocation-only: any other exception is a defect that must surface, never read as a failed write.
    for kwargs in ({"raise_on_write": True}, {"raise_on_read": True}):
        chunk = _RaisingFramChunk(error=RuntimeError("not an allocation failure"), **kwargs)
        store = PrintLogHistoryStore(_RaisingFramManager(chunk), history_length=4)
        try:
            store._write() if "raise_on_write" in kwargs else store._read()
        except RuntimeError:
            continue
        raise AssertionError(f"a RuntimeError from the chunk was swallowed ({kwargs})")


class _RefusingFramChunk(_RaisingFramChunk):
    # A chunk whose every write reports failure, as the real one does for a chip it cannot reach.
    def write_into(self, buf: "RegionBuffer") -> bool:
        return False


def test_a_store_whose_reset_cannot_write_returns_false() -> None:
    store = PrintLogHistoryStore(_RaisingFramManager(_RefusingFramChunk()), history_length=4)
    store.err_s("e", errno=1)
    assert run(store.reset()) is False
    assert store._err_count == 0  # cleared in RAM; only the persisting failed
    assert store.initialized is False


def test_printloghistorystore_write_into_returns_false_is_surfaced() -> None:
    # A real hardware-reported failure (not a raise): WREN never latches, so every write the real
    # chunk attempts fails cleanly - write_into() already turns this into a clean False return,
    # without asy_print_log.py needing to catch anything.
    manager, chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=4)
    chip.drop_wren = True
    assert store._write() is False


def test_printloghistorystore_read_into_returns_false_is_surfaced() -> None:
    # A real double fault: both of the chunk's redundant blocks are corrupted, torn-write status left BUSY
    # on each, so the dual-copy self-healing has nothing left to recover from - a stronger proof than a flat
    # "read fails" flag, showing asy_print_log.py degrades cleanly even once that redundancy is exhausted.
    manager, chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=4)
    store._write()  # something real is persisted first
    assert isinstance(store.fram, FRAMChunk)  # whitebox: narrows to the real chunk's own block layout
    addr0, addr1 = store.fram._block_addr
    status_offset = 2 + len(store.history) + 1  # _HDR_SIZE("<H") + history bytes + CRC8's 1 byte
    for addr in (addr0, addr1):
        chip.memory[addr + status_offset] = 0x02  # _STATUS_BUSY, mirrors a torn write on both copies
        chip.memory[addr + status_offset + 1] = 0x02
    assert store._read() is False


def test_printloghistorystore_self_heals_from_a_single_corrupted_copy_across_a_reboot() -> None:
    # The genuine-bit-flip counterpart to the two torn-write tests above: a real persisted data byte of copy
    # 0 is flipped, so nothing about the block's status says anything is wrong and only CRC8, the checksum
    # PrintLogHistoryStore asks get_chunk() for, can notice.
    #
    # Mirrors tests/test_voc_algorithm.py's single-corrupted-copy test, which does this for a
    # CRC32-protected chunk, and additionally checks the surviving copy is written back over the corrupted
    # one rather than only being read around.
    manager, chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=4)
    run(store.setup())
    store.err_s("boom", errno=3)
    store.err_s("bang", errno=7)
    assert store._err_count == 2

    assert isinstance(store.fram, FRAMChunk)  # whitebox: narrows to the real chunk's own block layout
    addr0, _addr1 = store.fram._block_addr
    block_len = 2 + len(store.history) + 1  # _HDR_SIZE("<H") + history bytes + CRC8's 1 byte
    original_block0 = bytes(chip.memory[addr0 : addr0 + block_len])
    chip.memory[addr0 + 2] ^= 0xFF  # a single flipped history byte in copy 0 only - copy 1 is intact
    assert bytes(chip.memory[addr0 : addr0 + block_len]) != original_block0

    # Same simulated reboot as test_printloghistorystore_err_s_persists_and_survives_a_simulated_reboot:
    # a fresh manager/store pair over the SAME chip memory, with the corruption still in place.
    manager2, _chip2 = make_fram_manager()
    manager2.fram._spidev.spi._spi = chip
    run(manager2.setup())
    rebooted_store = PrintLogHistoryStore(manager2, history_length=4)
    run(rebooted_store.setup())
    assert rebooted_store.initialized is True
    assert rebooted_store._err_count == 2  # recovered from the surviving copy, not from the flipped one
    assert list(rebooted_store.history) == list(store.history) == [0, 0, 3, 7]
    # ...and the damaged copy was repaired on-chip in the process, not just read around.
    assert bytes(chip.memory[addr0 : addr0 + block_len]) == original_block0


def test_printloghistorystore_setup_fails_cleanly_when_both_read_and_write_fail() -> None:
    manager, chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=4)
    # Nothing written yet, so _read() naturally fails (chunk reads back as uninitialized); WREN
    # never latching makes the fallback _write() of defaults fail too.
    chip.drop_wren = True
    run(store.setup())
    assert store.initialized is False


def test_printloghistorystore_err_s_survives_a_write_failure_without_raising() -> None:
    # _store_err()'s failed-write path must not itself raise even though the underlying persist-write
    # now fails - in-memory state should still update.
    manager, chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=4)
    run(store.setup())
    chip.drop_wren = True
    store.err_s("boom", errno=3)
    assert store._err_count == 1  # the entry, kept in RAM; the failed write adds none
    assert list(store.history)[-1] == 3


def test_make_logger_builds_a_store_or_a_ram_history_by_config() -> None:
    manager, _ = make_fram_manager()
    run(manager.setup())
    store = make_logger(LogConfig(manager, 4, 2), "SGP40")
    assert isinstance(store, PrintLogHistoryStore)
    assert store.name == "SGP40"
    assert store.level == 2
    assert len(store.history) == 4
    assert isinstance(store.fram, FRAMChunk)
    ram = make_logger(DEFAULT_LOG, "X")
    assert type(ram) is PrintLogHistory
    assert ram.name == "X"
    assert ram.level == 0
    assert len(ram.history) == 10
    assert DEFAULT_LOG == (None, 10, None)


def test_the_stack_exhausted_text_is_the_interpreters_own_message() -> None:
    assert src_const("src/asy_print_log.py", "_STACK_EXHAUSTED") == str(stack_overflow())


def test_report_if_fatal_flags_only_a_stack_overflow() -> None:
    # Every other exception leaves the flag clear, the same text under another class included; the real overflow sets it,
    # last, so no case is checked from a set flag.
    text = str(stack_overflow())
    others = (RuntimeError("CRC check failed while reading data"), RuntimeError(), ValueError(text), OSError(5, text), MemoryError("injected for the fatal check"))
    for other in others:
        report_if_fatal(other)
        assert fatal_reported() is False, repr(other)
    report_if_fatal(stack_overflow())
    assert fatal_reported() is True
    print_log_module._fatal = False  # as at boot: microtest fails a test that leaves it set


def test_report_if_fatal_allocates_and_prints_nothing() -> None:
    # It may run with the C stack nearly spent: with the heap locked it neither raises nor prints, and the flag still sets.
    error = stack_overflow()
    raised = reported = False
    with record_prints() as recorder:
        micropython.heap_lock()
        try:
            report_if_fatal(error)
            reported = fatal_reported()
        except MemoryError:
            raised = True
        finally:
            micropython.heap_unlock()
    assert (raised, reported, recorder.lines) == (False, True, [])
    print_log_module._fatal = False  # as at boot: microtest fails a test that leaves it set


# ---------------------------------------------------------------------------
# DebugLevel 0 prints nothing, ever; a C-stack overflow handed to any entry point is recorded at every level
# ---------------------------------------------------------------------------

_ENTRIES = ("err", "wrn", "one", "evt", "all", "err_s", "wrn_s")  # every logging entry point


def _call(pr: PrintLogHistory, method: str, *args: object) -> None:
    getattr(pr, method)(*args)


def test_level_0_prints_nothing_for_a_caught_memory_error() -> None:
    err = MemoryError("injected at level 0")  # worded clear of the memory gates' markers
    for method in _ENTRIES:
        pr = PrintLogHistory(history_length=2, level=0, name="P")
        with record_prints() as rec:
            _call(pr, method, "context:", err)
        assert rec.lines == [], (method, rec.lines)


def test_level_1_prints_a_caught_memory_errors_text_under_the_loggers_name() -> None:
    err = MemoryError("injected at level 1")  # worded clear of the memory gates' markers
    pr = PrintLogHistory(history_length=2, level=1, name="P")
    run(pr.setup())
    with record_prints() as rec:
        pr.err("context:", err)
        pr.err_s("persisted:", err, errno=3)
        pr.wrn("below its level:", err)
    assert rec.lines == [("P", "context:", err), ("P", "persisted:", err)], rec.lines


def test_every_entry_point_records_a_stack_overflow_at_level_0() -> None:
    error = stack_overflow()
    for method in _ENTRIES:
        pr = PrintLogHistory(history_length=2, level=0, name="P")
        with record_prints() as rec:
            _call(pr, method, "handler caught:", error)
        assert (fatal_reported(), rec.lines) == (True, []), method
        print_log_module._fatal = False  # as at boot: microtest fails a test that leaves it set
    pr = PrintLogHistory(history_length=2, level=5, name="P")
    for method in _ENTRIES:
        for other in (RuntimeError("CRC check failed while reading data"), ValueError(str(error))):
            _call(pr, method, "no overflow:", other)
    assert fatal_reported() is False


class _FlagAtWriteChunk(_RaisingFramChunk):
    # Notes whether the C-stack record was already set when the store's write reached the chunk.
    def __init__(self) -> None:
        super().__init__()
        self.flag_at_write: list[bool] = []

    def write_into(self, buf: "RegionBuffer") -> bool:
        self.flag_at_write.append(fatal_reported())
        return True


def test_err_s_and_wrn_s_record_the_overflow_ahead_of_their_fram_write() -> None:
    error = stack_overflow()
    for method in ("err_s", "wrn_s"):
        chunk = _FlagAtWriteChunk()
        store = PrintLogHistoryStore(_RaisingFramManager(chunk), history_length=4, level=0, name="S")
        run(store.setup())
        chunk.flag_at_write.clear()
        store.err_s("handler caught:", error, errno=3) if method == "err_s" else store.wrn_s("handler caught:", error, wrnno=3)
        assert chunk.flag_at_write == [True], (method, chunk.flag_at_write)
        print_log_module._fatal = False  # as at boot: microtest fails a test that leaves it set


def test_a_log_call_records_prints_and_writes_its_entry_before_it_returns() -> None:
    # One form, a plain call that never suspends: the entry is counted, printed and on the chip when the call returns,
    # the persisted image the RAM state (SPECIFICATION.md C.7.1).
    chunk = _CountingFramChunk(2 + 4)
    store = PrintLogHistoryStore(_CountingFramManager(chunk), history_length=4, level=2, name="S")
    run(store.setup())
    before = chunk.writes
    with record_prints() as rec:
        store.err_s("first", errno=3)
        assert chunk.writes == before + 1 and rec.lines == [("S", "first")]
        store.wrn_s("second", wrnno=2)
    assert chunk.writes == before + 2
    assert chunk.last_payload == struct.pack("<H", 2) + bytes([0, 0, 3, 0x80 + 2])
    assert not hasattr(store, "err_q") and not hasattr(store, "wrn_q")


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
