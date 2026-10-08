import asyncio
from collections import deque

import micropython
from _error_codes import code
from _fram_chip_fake import FakeMB85RS64V

import asy_print_log as print_log_module
import asy_spi_driver
from asy_base_classes import RegionBuffer
from asy_fram_manager import FRAMChunk, FRAMManager
from asy_print_log import DEFAULT_LOG, LogConfig, PrintLog, PrintLogHistory, PrintLogHistoryStore, console, make_logger
from asy_spi_driver import SPI

# Same one-process-per-test-file swap as test_asy_fram_driver.py/test_asy_fram_manager.py.
asy_spi_driver._SPI = FakeMB85RS64V  # type: ignore[misc]

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    from asy_crc_checks import CRCBase

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


def make_fram_manager(max_size: int = 0x2000) -> "tuple[FRAMManager, FakeMB85RS64V]":
    bus = SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    manager = FRAMManager(bus, 1, max_size=max_size)
    chip = manager.fram._spidev.spi._spi
    assert isinstance(chip, FakeMB85RS64V)
    return manager, chip


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

    async def write_into(self, buf: "RegionBuffer") -> bool:
        if self.raise_on_write:
            raise self.error
        return True

    async def read_into(self, buf: "RegionBuffer") -> bool:
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
        self, size: int, crc: "CRCBase | None" = None, verify: int = 0, check_length: int = 8, *, owner: str,
    ) -> "_RaisingFramChunk | None":
        if self.raise_on_get_chunk:
            raise self.error
        return self._chunk


class _CountingFramManager:
    def __init__(self, chunk: "_CountingFramChunk") -> None:
        self._chunk = chunk

    # Parameter names kept exact for the structural _FramManager Protocol match (see _RaisingFramManager).
    def get_chunk(
        self, size: int, crc: "CRCBase | None" = None, verify: int = 0, check_length: int = 8, *, owner: str,
    ) -> "_CountingFramChunk":
        return self._chunk


# ---------------------------------------------------------------------------
# PrintLog - levels 0 (off) .. 5 (all), refused when invalid
# ---------------------------------------------------------------------------


def test_set_level_none_is_off() -> None:
    assert PrintLog(None).level == 0


def test_an_out_of_range_level_is_refused_not_clamped() -> None:
    assert PrintLog(-5).level == 0
    pr = PrintLog(2)
    assert pr.set_level(10) is False
    assert pr.level == 2


def test_set_level_valid_value_passes_through() -> None:
    pr = PrintLog(2)
    assert pr.level == 2


def test_set_level_refuses_non_int_and_out_of_range_values() -> None:
    pr = PrintLog(2, name="P")
    rec = _PrintRecorder()
    try:
        refused = [pr.set_level(v) for v in (True, 2.0, None, 6, -1)]  # type: ignore[arg-type]
    finally:
        rec.restore()
    assert refused == [False] * 5
    assert pr.level == 2
    assert [line[:2] for line in rec.lines] == [("P", "PrintLog: invalid level refused:")] * 5  # each one says so at level 2
    assert pr.set_level(3) is True
    assert pr.level == 3


def test_each_level_prints_exactly_its_lines() -> None:
    expected = {0: [], 1: ["e"], 5: ["e", "w", "o", "v", "a"]}
    for level, lines in expected.items():
        pr = PrintLog(level)
        rec = _PrintRecorder()
        try:
            pr.err("e")
            pr.wrn("w")
            pr.one("o")
            pr.evt("v")
            pr.all("a", sep="-")
        finally:
            rec.restore()
        assert [line[1] for line in rec.lines] == lines, level
    pr = PrintLog(5)
    rec = _PrintRecorder()
    try:
        pr.all("a", "b", sep="-", end="!")
    finally:
        rec.restore()
    assert rec.kwargs == [{"sep": "-", "end": "!"}]  # the keywords reach print() as given


def test_set_level_exact_boundary_values_pass_through_unclamped() -> None:
    pr = PrintLog(0)
    assert pr.level == 0
    assert pr.set_level(5) is True
    assert pr.level == 5


def test_name_defaults_to_empty_string() -> None:
    pr = PrintLog()
    assert pr.name == ""


def test_name_is_stored_verbatim_when_given() -> None:
    pr = PrintLog(name="SGP40")
    assert pr.name == "SGP40"


# ---------------------------------------------------------------------------
# console() - the one line of a layer with no logger: no level, no history
# ---------------------------------------------------------------------------


def test_console_prints_each_call_once_with_its_name_first() -> None:
    err = MemoryError("injected for the console line")  # worded clear of the memory gates' markers
    rec = _PrintRecorder()
    try:
        console("UDPSocket", err)
        console("RegionBuffer", "text", 3)
        console("Named", "what", None)  # no error: the two-argument line
    finally:
        rec.restore()
    assert rec.lines == [("UDPSocket", err), ("RegionBuffer", "text", 3), ("Named", "what")]
    assert str(rec.lines[0][1]) == "injected for the console line"  # print() writes the caught error's own text
    assert rec.kwargs == [{}, {}, {}]  # print()'s own separator and line end


_NO_ARG = object()
_LOCKED_LINE: list[object] = [None, None, None]  # what the heap-free print() stand-in last saw: name, what, err


def _locked_print(name: object, what: object, err: object = _NO_ARG) -> None:
    # A print() stand-in that allocates nothing: fixed arity, the arguments kept in preallocated slots.
    _LOCKED_LINE[0] = name
    _LOCKED_LINE[1] = what
    _LOCKED_LINE[2] = err


def test_console_allocates_nothing_in_either_arity() -> None:
    # console() runs inside MemoryError arms of methods that never raise: with the heap locked, neither arity may raise,
    # through the real print() or a recording stand-in, and the stand-in still sees the error's text.
    err = MemoryError("injected for the locked console line")  # worded clear of the memory gates' markers
    raised = [False, False, False]
    micropython.heap_lock()
    try:
        console("Console", "real print, heap locked:", err)
    except MemoryError:
        raised[0] = True
    finally:
        micropython.heap_unlock()
    print_log_module.print = _locked_print  # type: ignore[attr-defined]
    try:
        micropython.heap_lock()
        try:
            console("UDPSocket", err)
        except MemoryError:
            raised[1] = True
        finally:
            micropython.heap_unlock()
        two = tuple(_LOCKED_LINE)
        micropython.heap_lock()
        try:
            console("RegionBuffer", "buffer allocation failed:", err)
        except MemoryError:
            raised[2] = True
        finally:
            micropython.heap_unlock()
        three = tuple(_LOCKED_LINE)
    finally:
        del print_log_module.print  # type: ignore[attr-defined]
    assert raised == [False, False, False], ("console() allocated with the heap locked", raised)
    assert two == ("UDPSocket", err, _NO_ARG)  # the two-argument print(), no None appended
    assert three == ("RegionBuffer", "buffer allocation failed:", err)
    assert str(three[2]) == "injected for the locked console line"


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
    assert run(hist.setup()) is True
    assert hist.initialized is True


def test_entries_logged_before_setup_count_their_ram_slots() -> None:
    # The pre-setup slot count: appends made while not initialised, capped at the ring's length; a repeat
    # of the newest entry takes no slot; reset() clears it, and nothing counts once set up.
    hist = PrintLogHistory(history_length=3)
    assert hist._pre_setup_slots == 0
    run(hist.err_s("a", errno=1))
    run(hist.err_s("a", errno=1))  # the newest-entry rule: counted, no slot
    run(hist.wrn_s("b", wrnno=2))
    assert hist._pre_setup_slots == 2
    for errno in (3, 4, 5):
        run(hist.err_s("c", errno=errno))
    assert hist._pre_setup_slots == 3  # never above the ring's own length
    run(hist.reset())
    assert hist._pre_setup_slots == 0
    run(hist.err_s("d", errno=6))  # reset() initialised it: no longer pre-setup
    assert hist._pre_setup_slots == 0


def test_read_stub_always_true_on_the_in_memory_class() -> None:
    hist = PrintLogHistory()
    assert run(hist._read()) is True  # no persistence to load in the pure in-memory case


def test_err_s_increments_count_and_records_history() -> None:
    hist = PrintLogHistory(history_length=4)
    run(hist.err_s("boom", errno=3))
    assert hist._err_count == 1
    assert list(hist.history)[-1] == 3  # _NO_ERR (0) + errno (3)


def test_wrn_s_records_in_the_warning_sub_range() -> None:
    hist = PrintLogHistory(history_length=4)
    run(hist.wrn_s("careful", wrnno=2))
    assert hist._err_count == 1
    assert list(hist.history)[-1] == 0x80 + 2  # _NO_WRN + wrnno


def test_err_s_default_errno_increments_count_but_not_history() -> None:
    # errno=0 (_NO_ERR, the default) still bumps the counter, but _store_err returns before
    # appending anything to history - a real, easy-to-miss asymmetry worth pinning down.
    hist = PrintLogHistory(history_length=4)
    run(hist.err_s("just counting"))
    assert hist._err_count == 1
    assert list(hist.history) == [0, 0, 0, 0]


def test_history_is_bounded_and_drops_oldest() -> None:
    hist = PrintLogHistory(history_length=3)
    for errno in (1, 2, 3, 4):
        run(hist.err_s("e", errno=errno))
    assert list(hist.history) == [2, 3, 4]  # oldest (1) fell off the bounded deque


def test_err_count_saturates_at_max_and_never_wraps() -> None:
    hist = PrintLogHistory(history_length=2)
    hist._err_count = 0xFFFE  # one below _MAX_CNT - whitebox-set to avoid 65534 real calls
    run(hist.err_s("e", errno=1))
    assert hist._err_count == 0xFFFF  # reaches the cap exactly, a normal step
    run(hist.err_s("e", errno=2))  # a different code: the ring still takes it
    assert hist._err_count == 0xFFFF  # saturates, does not wrap to 0
    assert list(hist.history) == [1, 2]


def test_errno_beyond_its_sub_range_is_not_recorded() -> None:
    # errno=200 pushed past _MAX_ERR (0x7F) once _NO_ERR is added - out of the valid error
    # sub-range, so the count still increments but nothing is appended to history.
    hist = PrintLogHistory(history_length=2)
    run(hist.err_s("e", errno=200))
    assert hist._err_count == 1
    assert list(hist.history) == [0, 0]


def test_reset_clears_history_and_count() -> None:
    hist = PrintLogHistory(history_length=3)
    run(hist.setup())
    run(hist.err_s("e", errno=1))
    assert run(hist.reset()) is True
    assert hist._err_count == 0
    assert list(hist.history) == [0, 0, 0]


def test_get_log_classifies_error_warning_and_clear_entries() -> None:
    hist = PrintLogHistory(history_length=3)
    run(hist.err_s("e", errno=5))  # oldest slot (still the initial _NO_ERR) falls off -> "E", 5
    run(hist.wrn_s("w", wrnno=2))  # -> "W", 2
    # remaining oldest slot is still the initial _NO_ERR -> "N", 0
    log = run(hist.get_log("Sensor"))
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
    run(hist.err_s("e", errno=-3))
    run(hist.wrn_s("w", wrnno=-1))
    assert hist._err_count == 2
    assert list(hist.history) == [0, 0]
    assert [d[:3] for d in hist.diags if "is invalid!" in d] == [("PrintLog: Error number", -3, "is invalid!"), ("PrintLog: Error number", -1, "is invalid!")]


class _PrintRecorder:
    # Local stand-in for a shared print recorder: shadows print() inside asy_print_log only, so every
    # console line a logger emits is captured with its arguments; restore() removes the shadow.
    def __init__(self) -> None:
        self.lines: list[tuple[object, ...]] = []
        self.kwargs: list[dict[str, object]] = []
        print_log_module.print = self  # type: ignore[attr-defined]

    def __call__(self, *args: object, **kwargs: object) -> None:
        self.lines.append(args)
        self.kwargs.append(kwargs)

    def restore(self) -> None:
        del print_log_module.print  # type: ignore[attr-defined]


class _CountingFramChunk:
    # Counts the write-throughs a store makes and keeps the last payload; a read waits on read_gate when set, then
    # answers read_result (False: blank, None: unreadable, True: `stored` copied into the buffer).
    def __init__(self, size: int, *, read_result: "bool | None" = False, stored: bytes = b"", write_result: bool = True) -> None:
        self.size = size
        self.writes = 0
        self.read_result = read_result
        self.stored = stored
        self.write_result = write_result
        self.read_gate: asyncio.Event | None = None
        self.last_payload: bytes | None = None

    # Parameter names kept exact for the structural _FramChunk Protocol match (see _RaisingFramChunk).
    def get_buffer(self) -> "RegionBuffer":
        return RegionBuffer(self.size, data_start=0, data_length=self.size)

    async def write_into(self, buf: "RegionBuffer") -> bool:
        self.writes += 1
        dbuf = buf.get_data_buf()
        assert dbuf is not None
        self.last_payload = bytes(dbuf)
        return self.write_result

    async def read_into(self, buf: "RegionBuffer") -> bool | None:
        if self.read_gate is not None:
            await self.read_gate.wait()
        if self.read_result:
            dbuf = buf.get_data_buf()
            assert dbuf is not None
            dbuf[: len(self.stored)] = self.stored
        return self.read_result


def _sustained_identical_code_spends_one_slot(hist: "PrintLogHistory", writes: "_CountingFramChunk | None") -> None:
    # Shared body of the per-history-type tests below: the newest-entry rule, SPECIFICATION.md Part C.7.1.
    run(hist.setup())
    writes_before = 0 if writes is None else writes.writes
    run(hist.err_s("earlier", errno=3))
    run(hist.wrn_s("earlier", wrnno=2))
    rec = _PrintRecorder()
    try:
        for _ in range(10):
            run(hist.err_s("sustained", errno=5))
    finally:
        rec.restore()
    assert list(hist.history) == [0, 3, 0x80 + 2, 5]  # the earlier entries intact, one slot for the ten
    assert hist._err_count == 12
    assert [line for line in rec.lines if "sustained" in line] == [(hist.name, "sustained")] * 10  # console unfiltered
    if writes is not None:
        assert writes.writes - writes_before == 12  # one write-through per call, a repeat included
    run(hist.err_s("other", errno=6))  # a different code between spends a slot
    run(hist.err_s("again", errno=5))
    assert list(hist.history) == [0x80 + 2, 5, 6, 5]
    run(hist.err_s("recurring", errno=5))  # recovered (nothing logged), then the same code again: no new slot
    assert list(hist.history) == [0x80 + 2, 5, 6, 5]
    run(hist.wrn_s("same number as a warning", wrnno=5))  # the other kind is a different code
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
    hist = PrintLogHistory(history_length=2)
    hist.history.extend([0x80, 0x80 + 2])  # whitebox: the warning sentinel byte beside a real W2
    log = run(hist.get_log("Sensor"))
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
    run(hist.err_s("e", errno=1))
    log = run(hist.get_log())
    assert log == {"SGP40": {"ErrCount": 1, "ErrNum": [1], "ErrType": ["E"]}}


def test_get_log_explicit_name_still_overrides_self_name() -> None:
    hist = PrintLogHistory(history_length=1, name="SGP40")
    log = run(hist.get_log("Override"))
    assert "Override" in log
    assert "SGP40" not in log


def test_err_s_errno_at_exact_max_err_boundary_is_recorded() -> None:
    hist = PrintLogHistory(history_length=2)
    run(hist.err_s("e", errno=0x7F))  # _MAX_ERR itself - inclusive boundary
    assert list(hist.history)[-1] == 0x7F


def test_err_s_errno_one_past_max_err_boundary_is_not_recorded() -> None:
    hist = PrintLogHistory(history_length=2)
    run(hist.err_s("e", errno=0x80))  # one past _MAX_ERR - falls into the warning sub-range instead
    assert hist._err_count == 1
    assert list(hist.history) == [0, 0]


def test_wrn_s_wrnno_at_exact_max_boundary_is_recorded() -> None:
    hist = PrintLogHistory(history_length=2)
    run(hist.wrn_s("w", wrnno=0x7F))  # _NO_WRN + 0x7F == _MAX_WRN, inclusive boundary
    assert list(hist.history)[-1] == 0xFF


def test_wrn_s_wrnno_one_past_max_boundary_is_not_recorded() -> None:
    hist = PrintLogHistory(history_length=2)
    run(hist.wrn_s("w", wrnno=0x80))  # _NO_WRN + 0x80 == 0x100, past _MAX_WRN (0xFF)
    assert hist._err_count == 1
    assert list(hist.history) == [0, 0]


def test_history_length_zero_never_records_but_still_counts() -> None:
    # An unusual but typed-valid construction: a zero-length bounded deque. Empirically confirmed
    # under the real MicroPython interpreter that append()/extend() on it are silent no-ops, not
    # a crash.
    hist = PrintLogHistory(history_length=0)
    run(hist.err_s("e", errno=1))
    assert hist._err_count == 1
    assert list(hist.history) == []


def test_history_length_negative_is_clamped_to_zero_not_a_raise() -> None:
    # deque(maxlen=…) raises ValueError on a negative maxlen (pinned interpreter); the constructor clamps it to zero.
    hist = PrintLogHistory(history_length=-5)
    assert list(hist.history) == []
    run(hist.err_s("e", errno=1))
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
    run(hist.err_s("e", errno=1))
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
    print_log_module.deque = _RaisingDeque()  # type: ignore[assignment,misc]
    rec = _PrintRecorder()
    try:
        hist = PrintLogHistory(history_length=10, level=1, name="H")
    finally:
        rec.restore()
        print_log_module.deque = original_deque  # type: ignore[misc]
    assert len(hist.history) == 0
    assert [line for line in rec.lines if any("injected for the history ring" in str(a) for a in line)] == [rec.lines[0]]
    assert len(rec.lines) == 1  # the one diagnostic line, carrying the failure's own text
    run(hist.err_s("e", errno=1))
    assert hist._err_count == 1  # counting still works even though history recording can't
    assert run(hist.get_log()) == {"H": {"ErrCount": 1, "ErrNum": [], "ErrType": []}}  # no slot reported


def test_a_failed_history_allocation_prints_its_text_with_logging_off() -> None:
    # The logging layer cannot log into itself: its own caught allocation failure is an ungated console line.
    original_deque = print_log_module.deque
    print_log_module.deque = _RaisingDeque()  # type: ignore[assignment,misc]
    rec = _PrintRecorder()
    try:
        hist = PrintLogHistory(history_length=10, name="H")
    finally:
        rec.restore()
        print_log_module.deque = original_deque  # type: ignore[misc]
    assert hist.level == 0
    assert [(line[:2], str(line[2])) for line in rec.lines] == [(("H", "PrintLog: history allocation failed:"), "injected for the history ring")]


def test_err_s_before_setup_does_not_write_even_with_logging_off() -> None:
    # The "not initialized" guard's *return* must not depend on self.level - only the diagnostic
    # print does. PrintLogHistory's own _write() is a no-op either way, but this pins the contract
    # down at the base-class level too (PrintLogHistoryStore's own FRAM-visible version follows below).
    hist = PrintLogHistory(history_length=4, level=0)
    assert hist.initialized is False
    run(hist.err_s("e", errno=1))
    assert hist._err_count == 1  # counting still happens
    assert list(hist.history)[-1] == 1  # in-memory recording still happens


def test_reset_before_setup_still_clears_even_with_logging_off() -> None:
    # The in-memory base has nothing to persist, so reset() is unconditional here either way -
    # what this pins down is that it never depends on the logging level to do its job.
    hist = PrintLogHistory(history_length=3, level=0)
    run(hist.err_s("e", errno=1))
    assert hist.initialized is False
    assert run(hist.reset()) is True
    assert hist._err_count == 0
    assert list(hist.history) == [0, 0, 0]


# ---------------------------------------------------------------------------
# PrintLogHistoryStore - FRAM-backed persistence, against the real, now-promoted FRAMManager
# driven by tests/_fram_chip_fake.py's simulated MB85RS64V chip (see BACKLOG.md - tests/_fram_mock.py
# and its flat, non-redundant abstraction are retired now that asy_fram_manager.py itself is in src/).
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
    assert run(store._write()) is False
    assert run(store._read()) is None  # nothing was read


def test_printloghistorystore_read_before_any_write_fails_cleanly() -> None:
    manager, _chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=4)
    assert run(store._read()) is False  # chunk allocated but never written yet - not "all zero"


def test_printloghistorystore_setup_first_time_falls_back_to_writing_defaults() -> None:
    manager, _chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=4)
    assert run(store.setup()) is True
    assert store.initialized is True
    assert store.restored is False  # a blank chunk: nothing an earlier boot stored


def test_printloghistorystore_setup_with_no_fram_returns_without_initializing() -> None:
    manager, _chip = make_fram_manager(max_size=1)
    store = PrintLogHistoryStore(manager, history_length=4)
    assert store.fram is None
    assert run(store.setup()) is False
    assert store.initialized is False  # nothing to set up - allocation already failed in __init__


def test_printloghistorystore_setup_is_idempotent_once_initialized() -> None:
    manager, _chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=4)
    run(store.setup())
    assert store.initialized is True
    run(store.err_s("boom", errno=1))
    assert store._err_count == 1
    assert run(store.setup()) is True  # second call must be a no-op, not re-read stale state over the live count
    assert store.initialized is True
    assert store._err_count == 1


def test_printloghistorystore_err_s_persists_and_survives_a_simulated_reboot() -> None:
    manager, chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=4)
    run(store.setup())
    run(store.err_s("boom", errno=3))
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
    assert rebooted_store.restored is True


def test_restored_is_false_for_an_unreadable_chunk_and_a_ram_only_history() -> None:
    manager, chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=4)
    chip.drop_wren = True  # blank and unwritable: setup() can neither read nor write it
    assert run(store.setup()) is False
    assert store.restored is False
    no_chunk = PrintLogHistoryStore(make_fram_manager(max_size=1)[0], history_length=4)
    assert run(no_chunk.setup()) is False
    assert no_chunk.restored is False
    ram = PrintLogHistory(history_length=4)
    assert run(ram.setup()) is True
    assert ram.restored is False  # a RAM-only history never restores


def test_a_restored_0x80_byte_reads_back_as_no_entry() -> None:
    # A 0x80 byte in the stored ring (the warning sentinel, or a foreign image) is an empty slot, never ErrNum 128.
    manager, chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=3)
    run(store.setup())
    store.history.extend([0x80, 5, 0x80])
    assert run(store._write()) is True
    manager2, _chip2 = make_fram_manager()
    manager2.fram._spidev.spi._spi = chip  # same chip image - models a reboot
    run(manager2.setup())
    rebooted = PrintLogHistoryStore(manager2, history_length=3)
    run(rebooted.setup())
    log = run(rebooted.get_log("Sensor"))
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
    run(store.err_s("boom", errno=3))
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
    run(seeded.err_s("e", errno=7))
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
    assert run(store.setup()) is False  # the chip is blank and its write is dropped: RAM-only
    chip.drop_wren = False
    assert run(store.setup()) is True
    assert store.initialized is True


def test_printloghistorystore_zero_length_history_survives_write_and_read() -> None:
    # An unusual but typed-valid construction (struct format collapses to just "H") - confirmed
    # directly this doesn't crash get_buffer()/pack_into/unpack_from at either end.
    manager, _chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=0)
    run(store.setup())
    assert store.initialized is True
    run(store.err_s("e", errno=1))
    assert store._err_count == 1
    assert list(store.history) == []
    assert run(store._read()) == (1, ())  # the stored count and its (empty) entries


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
    run(store._write())
    assert isinstance(store.fram, FRAMChunk)  # whitebox: narrows to the real chunk's own block layout
    addr0 = store.fram._block_addr[0]
    raw = bytes(chip.memory[addr0 : addr0 + 4])
    assert list(raw) == [0x34, 0x12, 5, 6]  # little-endian u16, then 2 raw history bytes


def test_printloghistorystore_reset_persists_cleared_state_across_a_reboot() -> None:
    manager, chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=3)
    run(store.setup())
    run(store.err_s("e", errno=1))
    assert run(store.reset()) is True

    manager2, _chip2 = make_fram_manager()
    manager2.fram._spidev.spi._spi = chip
    run(manager2.setup())
    rebooted_store = PrintLogHistoryStore(manager2, history_length=3)
    run(rebooted_store.setup())
    assert rebooted_store._err_count == 0
    assert list(rebooted_store.history) == [0, 0, 0]


class _GatedFramChunk(_CountingFramChunk):
    # Holds every write_into() on a test-held gate, then records the payload it was handed; the write
    # numbered in failing_writes (counted from 1) reports failure.
    def __init__(self, size: int) -> None:
        super().__init__(size)
        self.gate = asyncio.Event()
        self.payloads: list[bytes] = []
        self.failing_writes: tuple[int, ...] = ()

    async def write_into(self, buf: "RegionBuffer") -> bool:
        await self.gate.wait()
        dbuf = buf.get_data_buf()
        assert dbuf is not None
        self.payloads.append(bytes(dbuf))
        self.writes += 1
        return len(self.payloads) not in self.failing_writes


class _ResultRecordingStore(PrintLogHistoryStore):
    # Records what each _write() call returned, in completion order.
    def __init__(self, fram: "_CountingFramManager", history_length: int) -> None:
        super().__init__(fram, history_length=history_length)
        self.results: list[bool] = []

    async def _write(self) -> bool:
        ok = await PrintLogHistoryStore._write(self)
        self.results.append(ok)
        return ok


def test_concurrent_writes_land_newest_last() -> None:
    chunk = _GatedFramChunk(2 + 3)  # the "<H" header plus three history bytes
    store = _ResultRecordingStore(_CountingFramManager(chunk), history_length=3)
    chunk.gate.set()
    assert run(store.setup()) is True  # a blank chunk: setup() writes the empty state through the open gate
    chunk.gate.clear()
    chunk.payloads.clear()
    store.results.clear()

    async def scenario() -> None:
        tasks = [asyncio.create_task(store.err_s("e", errno=n)) for n in (1, 2, 3)]
        for _ in range(5):  # every call stores its entry and reaches its write before the gate opens
            await asyncio.sleep(0)
        chunk.gate.set()
        await asyncio.gather(*tasks)

    run(scenario())
    # The first call's write and the newest one's; the middle call was superseded and skipped.
    assert chunk.payloads == [b"\x01\x00\x00\x00\x01", b"\x03\x00\x01\x02\x03"], chunk.payloads
    assert store.results == [True, True, True], store.results  # a superseded call reports success: a newer write carries its state


def test_a_cancelled_newest_write_leaves_no_entry_unwritten() -> None:
    # The newest caller's task is cancelled while it waits for the write (a connection's outer cap does
    # exactly this): the call queued before it must still write every entry, not skip on its account.
    chunk = _GatedFramChunk(2 + 3)
    store = _ResultRecordingStore(_CountingFramManager(chunk), history_length=3)
    chunk.gate.set()
    assert run(store.setup()) is True
    chunk.gate.clear()
    chunk.payloads.clear()
    store.results.clear()

    async def scenario() -> None:
        tasks = [asyncio.create_task(store.err_s("e", errno=n)) for n in (1, 2, 3)]
        for _ in range(5):
            await asyncio.sleep(0)
        tasks[2].cancel()
        for _ in range(5):
            await asyncio.sleep(0)
        chunk.gate.set()
        await asyncio.gather(tasks[0], tasks[1])
        try:
            await tasks[2]
        except asyncio.CancelledError:
            pass
        else:
            raise AssertionError("the cancelled call completed")

    run(scenario())
    assert chunk.payloads == [b"\x01\x00\x00\x00\x01", b"\x03\x00\x01\x02\x03"], chunk.payloads
    assert store.results == [True, True], store.results


def test_a_failed_write_leaves_the_next_queued_call_to_write() -> None:
    # The second write fails: the call queued behind it writes the same state again rather than skipping,
    # so a skipped call's True always means its entry landed.
    chunk = _GatedFramChunk(2 + 3)
    store = _ResultRecordingStore(_CountingFramManager(chunk), history_length=3)
    chunk.gate.set()
    assert run(store.setup()) is True
    chunk.gate.clear()
    chunk.payloads.clear()
    store.results.clear()
    chunk.failing_writes = (2,)

    async def scenario() -> None:
        tasks = [asyncio.create_task(store.err_s("e", errno=n)) for n in (1, 2, 3)]
        for _ in range(5):
            await asyncio.sleep(0)
        chunk.gate.set()
        await asyncio.gather(*tasks)

    run(scenario())
    # The third call writes the full state again, the failed write's LOG_RAM_ONLY entry now in it.
    after = bytes((4, 0, 2, 3, code("E", "LOG_RAM_ONLY")))
    assert chunk.payloads == [b"\x01\x00\x00\x00\x01", b"\x03\x00\x01\x02\x03", after], chunk.payloads
    assert store.results == [True, False, True], store.results


def test_a_failed_write_after_setup_keeps_one_ram_only_entry_until_a_write_lands() -> None:
    # The chunk stops taking writes after setup(): the run's first failure adds one counted LOG_RAM_ONLY entry in RAM with
    # no second attempt, later failures add none, the next write that lands persists it, and a later run records again.
    ram_only = code("E", "LOG_RAM_ONLY")
    chunk = _CountingFramChunk(2 + 4)
    store = PrintLogHistoryStore(_CountingFramManager(chunk), history_length=4, name="S")
    assert run(store.setup()) is True
    writes = chunk.writes
    chunk.write_result = False
    run(store.err_s("first", errno=3))
    run(store.err_s("second", errno=5))
    assert chunk.writes - writes == 2  # one attempt per call, none for the entry itself
    assert list(store.history) == [0, 3, ram_only, 5]
    assert store._err_count == 3
    chunk.write_result = True
    run(store.wrn_s("back", wrnno=2))
    assert chunk.last_payload == bytes((4, 0, 3, ram_only, 5, 0x80 + 2))  # the entry rode the write that landed
    chunk.write_result = False
    run(store.err_s("again", errno=6))
    assert list(store.history) == [5, 0x80 + 2, 6, ram_only]  # a new run, a new entry
    assert store._err_count == 6


def test_a_reset_inside_a_failed_write_run_records_nothing_itself_and_starts_a_new_run() -> None:
    ram_only = code("E", "LOG_RAM_ONLY")
    chunk = _CountingFramChunk(2 + 3)
    store = PrintLogHistoryStore(_CountingFramManager(chunk), history_length=3)
    assert run(store.setup()) is True
    chunk.write_result = False
    run(store.err_s("e", errno=3))
    assert run(store.reset()) is False  # its failure is ResetErrors' "Failed", not an entry in the ring it cleared
    assert list(store.history) == [0, 0, 0]
    assert store._err_count == 0
    run(store.err_s("e", errno=4))
    assert list(store.history) == [0, 4, ram_only]
    assert store._err_count == 2


def test_a_reset_whose_write_lands_after_a_failed_one_ends_the_run() -> None:
    # A write fails while a reset waits on the write lock: its entry lands in the cleared ring and the reset's write
    # persists it, so the run is over and the next failure starts a new one.
    ram_only = code("E", "LOG_RAM_ONLY")
    chunk = _GatedFramChunk(2 + 3)
    store = PrintLogHistoryStore(_CountingFramManager(chunk), history_length=3)
    chunk.gate.set()
    assert run(store.setup()) is True
    chunk.gate.clear()
    chunk.payloads.clear()
    chunk.failing_writes = (1, 3)

    async def scenario() -> bool:
        failing = asyncio.create_task(store.err_s("e", errno=3))
        await asyncio.sleep(0)  # its write now waits at the gate
        reset = asyncio.create_task(store.reset())
        await asyncio.sleep(0)  # the reset has cleared the ring and waits on the write lock
        chunk.gate.set()
        await failing
        return await reset

    assert run(scenario()) is True
    assert chunk.payloads[1] == bytes((1, 0, 0, 0, ram_only))
    run(store.err_s("e", errno=5))  # the third write fails: a new run
    assert list(store.history) == [ram_only, 5, ram_only]


def test_queued_calls_behind_a_failed_write_record_one_entry_and_the_next_write_lands_it() -> None:
    chunk = _GatedFramChunk(2 + 4)
    store = PrintLogHistoryStore(_CountingFramManager(chunk), history_length=4)
    chunk.gate.set()
    assert run(store.setup()) is True
    chunk.gate.clear()
    chunk.payloads.clear()
    chunk.failing_writes = (1,)

    async def scenario() -> None:
        tasks = [asyncio.create_task(store.err_s("e", errno=n)) for n in (1, 2, 3)]
        for _ in range(5):
            await asyncio.sleep(0)
        chunk.gate.set()
        await asyncio.gather(*tasks)

    run(scenario())
    # The failed first write, then one write of the newest state with the run's entry; the third call skips.
    assert chunk.payloads == [b"\x01\x00\x00\x00\x00\x01", bytes((4, 0, 1, 2, 3, code("E", "LOG_RAM_ONLY")))], chunk.payloads


def test_an_entry_logged_during_the_setup_write_keeps_a_ram_only_entry_when_its_write_fails() -> None:
    chunk = _GatedFramChunk(2 + 3)
    chunk.failing_writes = (2,)  # setup()'s own write lands, the one for the entry logged meanwhile fails
    store = PrintLogHistoryStore(_CountingFramManager(chunk), history_length=3)

    async def scenario() -> bool:
        setup = asyncio.create_task(store.setup())
        for _ in range(5):
            await asyncio.sleep(0)
        await store.err_s("during the setup write", errno=4)
        chunk.gate.set()
        return await setup

    assert run(scenario()) is True
    assert list(store.history) == [0, 4, code("E", "LOG_RAM_ONLY")]
    assert store._err_count == 2


def test_read_answers_the_stored_entries_false_or_none_and_mutates_nothing() -> None:
    blank = PrintLogHistoryStore(_CountingFramManager(_CountingFramChunk(2 + 3)), history_length=3)
    assert run(blank._read()) is False
    unreadable = PrintLogHistoryStore(_CountingFramManager(_CountingFramChunk(2 + 3, read_result=None)), history_length=3)
    assert run(unreadable._read()) is None
    chunk = _CountingFramChunk(2 + 3, read_result=True, stored=b"\x05\x00\x01\x02\x03")
    stored = PrintLogHistoryStore(_CountingFramManager(chunk), history_length=3)
    run(stored.err_s("pre", errno=9))
    assert run(stored._read()) == (5, (1, 2, 3))
    assert list(stored.history) == [0, 0, 9]  # the read itself applies nothing
    assert stored._err_count == 1


def test_setup_merges_entries_logged_before_it_after_the_stored_ones() -> None:
    # Two stored entries and one logged before setup(): the stored ring first, the earlier entry newest, counts
    # summed; a repeat of it before setup() is counted but takes no slot.
    earlier_chunk = _CountingFramChunk(2 + 4)
    earlier = PrintLogHistoryStore(_CountingFramManager(earlier_chunk), history_length=4)  # the earlier boot
    run(earlier.setup())
    run(earlier.err_s("stored", errno=3))
    run(earlier.err_s("stored", errno=7))
    assert earlier_chunk.last_payload is not None
    for repeats, count in ((1, 3), (2, 4)):
        chunk = _CountingFramChunk(2 + 4, read_result=True, stored=earlier_chunk.last_payload)
        store = PrintLogHistoryStore(_CountingFramManager(chunk), history_length=4)
        for _ in range(repeats):
            run(store.err_s("before setup", errno=5))
        assert chunk.writes == 0
        assert run(store.setup()) is True
        assert list(store.history) == [0, 3, 7, 5]
        assert store._err_count == count
        assert store._pre_setup_slots == 0
        assert store.restored is True
        assert chunk.writes == 1  # the merge changed the ring: written once
        assert chunk.last_payload == bytes((count, 0, 0, 3, 7, 5))


def test_a_clean_read_of_a_valid_store_sets_up_without_writing() -> None:
    # Nothing logged before setup(): the chunk already holds exactly this state, so setup() writes nothing back.
    chunk = _CountingFramChunk(2 + 3, read_result=True, stored=b"\x02\x00\x00\x03\x07")
    store = PrintLogHistoryStore(_CountingFramManager(chunk), history_length=3)
    assert run(store.setup()) is True
    assert store.initialized is True
    assert store.restored is True
    assert store._err_count == 2
    assert chunk.writes == 0


def test_a_merged_count_saturates_at_the_cap() -> None:
    chunk = _CountingFramChunk(2 + 2, read_result=True, stored=b"\xfe\xff\x00\x00")  # 0xFFFE stored
    store = PrintLogHistoryStore(_CountingFramManager(chunk), history_length=2)
    run(store.err_s("before setup", errno=1))
    run(store.err_s("before setup", errno=2))
    assert run(store.setup()) is True
    assert store._err_count == 0xFFFF  # the uint16 header's own maximum, never past it


def test_a_reset_landing_during_setups_read_leaves_ram_and_the_chunk_cleared() -> None:
    chunk = _CountingFramChunk(2 + 3, read_result=True, stored=b"\x02\x00\x00\x03\x07")
    gate = asyncio.Event()
    chunk.read_gate = gate
    store = PrintLogHistoryStore(_CountingFramManager(chunk), history_length=3)

    async def scenario() -> bool:
        setup = asyncio.create_task(store.setup())
        await asyncio.sleep(0)  # setup() now waits inside its read
        assert await store.reset() is True
        gate.set()
        return await setup

    assert run(scenario()) is True
    assert store._err_count == 0
    assert list(store.history) == [0, 0, 0]
    assert chunk.writes == 1  # the reset's write only: setup() applied and wrote nothing
    assert chunk.last_payload == bytes(5)
    assert store.restored is False


def test_an_entry_logged_during_the_setup_write_still_lands_on_the_chunk() -> None:
    # An entry arriving while setup()'s own write is in flight is neither in that write's payload nor written through
    # (the store is not initialised yet): setup() writes once more, so it survives a reboot.
    chunk = _GatedFramChunk(2 + 3)
    store = PrintLogHistoryStore(_CountingFramManager(chunk), history_length=3)

    async def scenario() -> bool:
        setup = asyncio.create_task(store.setup())
        for _ in range(5):  # setup() now waits inside its write
            await asyncio.sleep(0)
        await store.err_s("during the setup write", errno=4)
        chunk.gate.set()
        return await setup

    assert run(scenario()) is True
    assert chunk.payloads[-1] == b"\x01\x00\x00\x00\x04", chunk.payloads


def test_a_blank_store_is_reinitialised() -> None:
    chunk = _CountingFramChunk(2 + 3)
    store = PrintLogHistoryStore(_CountingFramManager(chunk), history_length=3)
    assert run(store.setup()) is True
    assert store.initialized is True
    assert store.restored is False
    assert chunk.writes == 1
    assert chunk.last_payload == bytes(5)


def test_an_unreadable_store_keeps_its_bytes_and_stays_ram_only() -> None:
    chunk = _CountingFramChunk(2 + 3, read_result=None)
    store = PrintLogHistoryStore(_CountingFramManager(chunk), history_length=3, name="U")
    assert run(store.setup()) is False
    assert store.initialized is False
    assert store.restored is False
    run(store.err_s("later", errno=4))
    assert chunk.writes == 0  # nothing ever reached the chunk: the stored history stays for the next boot
    assert list(store.history) == [0, code("E", "LOG_RAM_ONLY"), 4]
    assert store._err_count == 2


def test_each_ram_only_store_shows_one_entry_under_its_own_name() -> None:
    # The chunk's heap allocation raised, it read unreadable at setup(), or its first write failed: setup() is False and
    # the store's own ring holds one counted LOG_RAM_ONLY entry, the console line kept; nothing lands on the chunk.
    unreadable = _CountingFramChunk(2 + 3, read_result=None)
    refusing = _CountingFramChunk(2 + 3, write_result=False)
    cases = (
        (PrintLogHistoryStore(_RaisingFramManager(None, raise_on_get_chunk=True), history_length=3, level=1, name="A"), None, "FRAM history allocation failed - RAM-only until reboot"),
        (PrintLogHistoryStore(_CountingFramManager(unreadable), history_length=3, level=1, name="B"), unreadable, "FRAM history unreadable - RAM-only until reboot"),
        (PrintLogHistoryStore(_CountingFramManager(refusing), history_length=3, level=1, name="C"), refusing, "FRAM history setup write failed - RAM-only until reboot"),
    )
    for store, chunk, text in cases:
        writes_before = 0 if chunk is None else chunk.writes
        rec = _PrintRecorder()
        try:
            assert run(store.setup()) is False
        finally:
            rec.restore()
        log = run(store.get_log())[store.name]
        assert log["ErrCount"] == 1, (store.name, log)
        assert log["ErrNum"].count(code("E", "LOG_RAM_ONLY")) == 1, (store.name, log)
        assert (store.name, text) in rec.lines, (store.name, rec.lines)
        if chunk is not None:
            assert chunk.writes == writes_before + (1 if chunk is refusing else 0)  # only the refused setup write
    refused = PrintLogHistoryStore(_RaisingFramManager(None), history_length=3)  # the allocator had no room left
    assert run(refused.setup()) is False
    assert refused._err_count == 0  # an allocator refusal records nothing; the bench's capacity check finds it
    blank = PrintLogHistoryStore(_CountingFramManager(_CountingFramChunk(2 + 3)), history_length=3)
    assert run(blank.setup()) is True
    assert run(blank.setup()) is True  # an initialised store's second setup() adds no entry
    assert blank._err_count == 0
    assert code("E", "LOG_RAM_ONLY") not in blank.history


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
    assert run(store._write()) is False
    assert run(store._read()) is None


def test_printloghistorystore_read_into_raising_is_caught() -> None:
    chunk = _RaisingFramChunk(raise_on_read=True)
    store = PrintLogHistoryStore(_RaisingFramManager(chunk), history_length=4)
    assert run(store._read()) is None  # unreadable, not blank: setup() must not overwrite the store


def test_a_none_data_buffer_fails_write_and_read_without_raising() -> None:
    chunk = _RaisingFramChunk(none_buffer=True)
    store = PrintLogHistoryStore(_RaisingFramManager(chunk), history_length=4)
    assert run(store._write()) is False
    assert run(store._read()) is None
    run(store.reset())
    run(store.err_s("e", errno=1))
    assert store._err_count == 1  # the entry still counts in RAM


def test_each_caught_chunk_allocation_failure_prints_its_text_once_with_logging_off() -> None:
    # One ungated console line per occurrence, carrying the error's own text: the chunk's allocation, a read, a write.
    err = MemoryError("injected for the chunk allocation")
    rec = _PrintRecorder()
    try:
        store = PrintLogHistoryStore(_RaisingFramManager(None, raise_on_get_chunk=True, error=err), history_length=4, name="A")
    finally:
        rec.restore()
    assert store.fram is None
    assert rec.lines == [("A", "PrintLog: FRAM allocation failed:", err)]
    for kwargs, text in (({"raise_on_read": True}, "injected for the history read"), ({"raise_on_write": True}, "injected for the history write")):
        err = MemoryError(text)
        store = PrintLogHistoryStore(_RaisingFramManager(_RaisingFramChunk(error=err, **kwargs)), history_length=4, name="B")
        rec = _PrintRecorder()
        try:
            results = [run(store._read() if "raise_on_read" in kwargs else store._write()) for _ in range(2)]
        finally:
            rec.restore()
        assert results == ([None, None] if "raise_on_read" in kwargs else [False, False]), (text, results)
        what = "read" if "raise_on_read" in kwargs else "write"
        assert rec.lines == [("B", "PrintLog: FRAM history " + what + " failed:", err)] * 2, (text, rec.lines)


def test_an_allocator_refusal_prints_only_its_gated_line() -> None:
    # A chunk the allocator refused is no heap failure: the gated line at a level, nothing with logging off.
    for level, lines in ((None, []), (1, [("R", "PrintLog: FRAM allocation failed!")])):
        rec = _PrintRecorder()
        try:
            PrintLogHistoryStore(_RaisingFramManager(None), history_length=4, level=level, name="R")
        finally:
            rec.restore()
        assert rec.lines == lines, (level, rec.lines)
    rec = _PrintRecorder()
    try:  # a heap failure at a level prints its one ungated line, not the gated one too
        PrintLogHistoryStore(_RaisingFramManager(None, raise_on_get_chunk=True, error=MemoryError("injected for one line")), history_length=4, level=1, name="R")
    finally:
        rec.restore()
    assert [line[:2] for line in rec.lines] == [("R", "PrintLog: FRAM allocation failed:")]


def test_a_non_allocation_failure_from_a_chunk_propagates() -> None:
    # The catch is allocation-only: any other exception is a defect that must surface, never read as a failed write.
    for kwargs in ({"raise_on_write": True}, {"raise_on_read": True}):
        chunk = _RaisingFramChunk(error=RuntimeError("not an allocation failure"), **kwargs)
        store = PrintLogHistoryStore(_RaisingFramManager(chunk), history_length=4)
        try:
            run(store._write() if "raise_on_write" in kwargs else store._read())
        except RuntimeError:
            continue
        raise AssertionError(f"a RuntimeError from the chunk was swallowed ({kwargs})")


class _RefusingFramChunk(_RaisingFramChunk):
    # A chunk whose every write reports failure, as the real one does for a chip it cannot reach.
    async def write_into(self, buf: "RegionBuffer") -> bool:
        return False


def test_a_store_whose_reset_cannot_write_returns_false() -> None:
    store = PrintLogHistoryStore(_RaisingFramManager(_RefusingFramChunk()), history_length=4)
    run(store.err_s("e", errno=1))
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
    assert run(store._write()) is False


def test_printloghistorystore_read_into_returns_false_is_surfaced() -> None:
    # A real double fault: both of the chunk's redundant blocks are corrupted, torn-write status left BUSY
    # on each, so the dual-copy self-healing has nothing left to recover from - a stronger proof than a flat
    # "read fails" flag, showing asy_print_log.py degrades cleanly even once that redundancy is exhausted.
    manager, chip = make_fram_manager()
    run(manager.setup())
    store = PrintLogHistoryStore(manager, history_length=4)
    run(store._write())  # something real is persisted first
    assert isinstance(store.fram, FRAMChunk)  # whitebox: narrows to the real chunk's own block layout
    addr0, addr1 = store.fram._block_addr
    status_offset = 2 + len(store.history) + 1  # _HDR_SIZE("<H") + history bytes + CRC8's 1 byte
    for addr in (addr0, addr1):
        chip.memory[addr + status_offset] = 0x02  # _STATUS_BUSY, mirrors a torn write on both copies
        chip.memory[addr + status_offset + 1] = 0x02
    assert run(store._read()) is False


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
    run(store.err_s("boom", errno=3))
    run(store.err_s("bang", errno=7))
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
    run(store.err_s("boom", errno=3))
    assert store._err_count == 2  # the entry and the failed write's LOG_RAM_ONLY
    assert list(store.history)[-2:] == [3, code("E", "LOG_RAM_ONLY")]


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


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
