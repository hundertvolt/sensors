import asyncio

from _fram_mock import MockAsyFramManager, _MockFramChunk

from print_log import PrintLog, PrintLogHistory, PrintLogHistoryStore

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# PrintLog - level clamping and the level_* constant accessors
# ---------------------------------------------------------------------------


def test_set_level_none_is_off() -> None:
    pr = PrintLog(None)
    assert pr.get_level() == PrintLog.level_off()


def test_set_level_clamps_below_off_and_above_all() -> None:
    pr = PrintLog(PrintLog.level_off() - 5)
    assert pr.get_level() == PrintLog.level_off()
    pr.set_level(PrintLog.level_info() + 5)
    assert pr.get_level() == PrintLog.level_info()


def test_set_level_valid_value_passes_through() -> None:
    pr = PrintLog(PrintLog.level_warn())
    assert pr.get_level() == PrintLog.level_warn()


def test_level_constants_are_ordered() -> None:
    levels = [
        PrintLog.level_off(),
        PrintLog.level_err(),
        PrintLog.level_warn(),
        PrintLog.level_once(),
        PrintLog.level_event(),
        PrintLog.level_info(),
    ]
    assert levels == sorted(levels)
    assert len(set(levels)) == len(levels)  # all distinct


def test_logging_methods_never_raise_at_any_level() -> None:
    for level in (PrintLog.level_off(), PrintLog.level_err(), PrintLog.level_info()):
        pr = PrintLog(level)
        pr.err("e")
        pr.wrn("w")
        pr.one("o")
        pr.evt("v")
        pr.all("a", sep="-")  # kwargs forwarded through to print() too


def test_set_level_exact_boundary_values_pass_through_unclamped() -> None:
    pr = PrintLog(PrintLog.level_off())
    assert pr.get_level() == PrintLog.level_off()
    pr.set_level(PrintLog.level_info())
    assert pr.get_level() == PrintLog.level_info()


# ---------------------------------------------------------------------------
# PrintLogHistory - bounded in-memory error/warning history
# ---------------------------------------------------------------------------


def test_initial_state_is_all_clear() -> None:
    hist = PrintLogHistory(history_length=4)
    assert hist.err_count == 0
    assert hist.initialized is False
    assert list(hist.history) == [0, 0, 0, 0]


def test_setup_marks_initialized() -> None:
    hist = PrintLogHistory()
    run(hist.setup())
    assert hist.initialized is True


def test_read_stub_always_true_on_the_in_memory_class() -> None:
    hist = PrintLogHistory()
    assert run(hist._read()) is True  # no persistence to load in the pure in-memory case


def test_err_s_increments_count_and_records_history() -> None:
    hist = PrintLogHistory(history_length=4)
    run(hist.err_s("boom", errno=3))
    assert hist.err_count == 1
    assert list(hist.history)[-1] == 3  # _NO_ERR (0) + errno (3)


def test_wrn_s_records_in_the_warning_sub_range() -> None:
    hist = PrintLogHistory(history_length=4)
    run(hist.wrn_s("careful", wrnno=2))
    assert hist.err_count == 1
    assert list(hist.history)[-1] == 0x80 + 2  # _NO_WRN + wrnno


def test_err_s_default_errno_increments_count_but_not_history() -> None:
    # errno=0 (_NO_ERR, the default) still bumps the counter, but _store_err returns before
    # appending anything to history - a real, easy-to-miss asymmetry worth pinning down.
    hist = PrintLogHistory(history_length=4)
    run(hist.err_s("just counting"))
    assert hist.err_count == 1
    assert list(hist.history) == [0, 0, 0, 0]


def test_history_is_bounded_and_drops_oldest() -> None:
    hist = PrintLogHistory(history_length=3)
    for errno in (1, 2, 3, 4):
        run(hist.err_s("e", errno=errno))
    assert list(hist.history) == [2, 3, 4]  # oldest (1) fell off the bounded deque


def test_err_count_saturates_at_max_and_never_wraps() -> None:
    hist = PrintLogHistory(history_length=2)
    hist.err_count = 0xFFFF  # _MAX_CNT - whitebox-set to avoid 65535 real calls
    run(hist.err_s("e", errno=1))
    assert hist.err_count == 0xFFFF  # saturates, does not wrap to 0


def test_errno_beyond_its_sub_range_is_not_recorded() -> None:
    # errno=200 pushed past _MAX_ERR (0x7F) once _NO_ERR is added - out of the valid error
    # sub-range, so the count still increments but nothing is appended to history.
    hist = PrintLogHistory(history_length=2)
    run(hist.err_s("e", errno=200))
    assert hist.err_count == 1
    assert list(hist.history) == [0, 0]


def test_reset_clears_history_and_count() -> None:
    hist = PrintLogHistory(history_length=3)
    run(hist.setup())
    run(hist.err_s("e", errno=1))
    run(hist.reset())
    assert hist.err_count == 0
    assert list(hist.history) == [0, 0, 0]


def test_get_log_classifies_error_warning_and_clear_entries() -> None:
    hist = PrintLogHistory(history_length=3)
    run(hist.err_s("e", errno=5))  # oldest slot (still the initial _NO_ERR) falls off -> "E", 5
    run(hist.wrn_s("w", wrnno=2))  # -> "W", 2
    # remaining oldest slot is still the initial _NO_ERR -> "N", 0
    log = run(hist.get_log("Sensor"))
    assert log == {"Sensor": {"ErrCount": 2, "ErrNum": [0, 5, 2], "ErrType": ["N", "E", "W"]}}


def test_err_s_errno_at_exact_max_err_boundary_is_recorded() -> None:
    hist = PrintLogHistory(history_length=2)
    run(hist.err_s("e", errno=0x7F))  # _MAX_ERR itself - inclusive boundary
    assert list(hist.history)[-1] == 0x7F


def test_err_s_errno_one_past_max_err_boundary_is_not_recorded() -> None:
    hist = PrintLogHistory(history_length=2)
    run(hist.err_s("e", errno=0x80))  # one past _MAX_ERR - falls into the warning sub-range instead
    assert hist.err_count == 1
    assert list(hist.history) == [0, 0]


def test_wrn_s_wrnno_at_exact_max_boundary_is_recorded() -> None:
    hist = PrintLogHistory(history_length=2)
    run(hist.wrn_s("w", wrnno=0x7F))  # _NO_WRN + 0x7F == _MAX_WRN, inclusive boundary
    assert list(hist.history)[-1] == 0xFF


def test_wrn_s_wrnno_one_past_max_boundary_is_not_recorded() -> None:
    hist = PrintLogHistory(history_length=2)
    run(hist.wrn_s("w", wrnno=0x80))  # _NO_WRN + 0x80 == 0x100, past _MAX_WRN (0xFF)
    assert hist.err_count == 1
    assert list(hist.history) == [0, 0]


def test_err_count_increments_normally_right_below_the_cap() -> None:
    hist = PrintLogHistory(history_length=2)
    hist.err_count = 0xFFFE  # one below _MAX_CNT
    run(hist.err_s("e", errno=1))
    assert hist.err_count == 0xFFFF  # reaches the cap exactly, still a normal increment


def test_history_length_zero_never_records_but_still_counts() -> None:
    # An unusual but typed-valid construction: a zero-length bounded deque. Empirically confirmed
    # under the real MicroPython interpreter that append()/extend() on it are silent no-ops, not
    # a crash (see the deque investigation in this session).
    hist = PrintLogHistory(history_length=0)
    run(hist.err_s("e", errno=1))
    assert hist.err_count == 1
    assert list(hist.history) == []


def test_history_length_negative_is_clamped_to_zero_not_a_raise() -> None:
    # deque(maxlen=...) raises ValueError on a negative maxlen (confirmed directly against the real
    # MicroPython interpreter) - a typed-valid but unusual int input the constructor must clamp
    # rather than propagate, matching set_level()'s own clamping convention.
    hist = PrintLogHistory(history_length=-5)
    assert list(hist.history) == []
    run(hist.err_s("e", errno=1))
    assert hist.err_count == 1


def test_history_length_huge_is_capped_instead_of_crashing_the_interpreter() -> None:
    # A typed-valid but wildly unusual int input: confirmed directly against the pinned Unix-port
    # interpreter that `[x] * n` (what building this deque does internally) segfaults the whole
    # process for some huge-but-representable n (no catchable exception at all - MemoryError only
    # covers smaller sizes, OverflowError only covers n at/above the machine-word boundary, and
    # there's an uncatchable gap in between). The fix caps the input before ever attempting the
    # allocation - this pins that the cap actually holds, not just that construction "doesn't raise".
    hist = PrintLogHistory(history_length=2**62)
    assert len(hist.history) <= 0xFFFF
    run(hist.err_s("e", errno=1))
    assert hist.err_count == 1


def test_err_s_before_setup_does_not_write_even_with_logging_off() -> None:
    # The "not initialized" guard's *return* must not depend on self.level - only the diagnostic
    # print does. PrintLogHistory's own _write() is a no-op either way, but this pins the contract
    # down at the base-class level too (PrintLogHistoryStore's own FRAM-visible version follows below).
    hist = PrintLogHistory(history_length=4, level=PrintLog.level_off())
    assert hist.initialized is False
    run(hist.err_s("e", errno=1))
    assert hist.err_count == 1  # counting still happens
    assert list(hist.history)[-1] == 1  # in-memory recording still happens


def test_reset_before_setup_does_not_write_even_with_logging_off() -> None:
    hist = PrintLogHistory(history_length=3, level=PrintLog.level_off())
    run(hist.err_s("e", errno=1))
    assert hist.initialized is False
    run(hist.reset())
    assert hist.err_count == 0
    assert list(hist.history) == [0, 0, 0]


# ---------------------------------------------------------------------------
# PrintLogHistoryStore - FRAM-backed persistence, against a mocked FRAM API
# (tests/_fram_mock.py - see BACKLOG.md for why the real asy_fram_manager.py isn't used here yet)
# ---------------------------------------------------------------------------


def test_printloghistorystore_allocates_a_chunk_from_the_fram_manager() -> None:
    store = PrintLogHistoryStore(MockAsyFramManager(), history_length=4)
    assert store.fram is not None


def test_printloghistorystore_out_of_memory_leaves_fram_none_and_never_raises() -> None:
    store = PrintLogHistoryStore(MockAsyFramManager(out_of_memory=True), history_length=4)
    assert store.fram is None
    assert run(store._write()) is False
    assert run(store._read()) is False


def test_printloghistorystore_read_before_any_write_fails_cleanly() -> None:
    store = PrintLogHistoryStore(MockAsyFramManager(), history_length=4)
    assert run(store._read()) is False  # chunk allocated but never written yet - not "all zero"


def test_printloghistorystore_setup_first_time_falls_back_to_writing_defaults() -> None:
    store = PrintLogHistoryStore(MockAsyFramManager(), history_length=4)
    run(store.setup())
    assert store.initialized is True


def test_printloghistorystore_setup_with_no_fram_returns_without_initializing() -> None:
    store = PrintLogHistoryStore(MockAsyFramManager(out_of_memory=True), history_length=4)
    assert store.fram is None
    run(store.setup())
    assert store.initialized is False  # nothing to set up - allocation already failed in __init__


def test_printloghistorystore_setup_is_idempotent_once_initialized() -> None:
    store = PrintLogHistoryStore(MockAsyFramManager(), history_length=4)
    run(store.setup())
    assert store.initialized is True
    run(store.err_s("boom", errno=1))
    assert store.err_count == 1
    run(store.setup())  # second call must be a no-op, not re-read stale state over the live count
    assert store.initialized is True
    assert store.err_count == 1


def test_printloghistorystore_err_s_persists_and_survives_a_simulated_reboot() -> None:
    manager = MockAsyFramManager()
    store = PrintLogHistoryStore(manager, history_length=4)
    run(store.setup())
    run(store.err_s("boom", errno=3))
    assert store.err_count == 1

    # Simulate a reboot: a fresh manager/store pair, replaying the same get_chunk() call, wrapping
    # the same backing bytes - same as a real chip's contents surviving a power cycle.
    rebooted_store = PrintLogHistoryStore(MockAsyFramManager(backing=manager.backing), history_length=4)
    run(rebooted_store.setup())
    assert rebooted_store.err_count == 1
    assert list(rebooted_store.history)[-1] == 3


def test_printloghistorystore_err_s_before_setup_does_not_touch_fram() -> None:
    # Regression test for a real bug: _store_err()'s "not initialized" guard used to only return
    # early when self.level > _LOG_OFF, so with logging off (the common production case) calling
    # err_s() before setup() had loaded (or established) the persisted state fell through to
    # _write() anyway - overwriting real FRAM-persisted history with a freshly-constructed,
    # not-yet-loaded default. Fixed so the return no longer depends on self.level.
    manager = MockAsyFramManager()
    store = PrintLogHistoryStore(manager, history_length=4, level=None)  # level=None -> _LOG_OFF
    assert store.initialized is False
    run(store.err_s("boom", errno=3))
    assert store.err_count == 1  # in-memory state still updates
    assert manager.backing._written_offsets == set()  # but nothing was ever written to FRAM


def test_printloghistorystore_reset_before_setup_does_not_touch_fram() -> None:
    manager = MockAsyFramManager()
    store = PrintLogHistoryStore(manager, history_length=4, level=None)
    assert store.initialized is False
    run(store.reset())
    assert manager.backing._written_offsets == set()


def test_printloghistorystore_zero_length_history_survives_write_and_read() -> None:
    # An unusual but typed-valid construction (struct format collapses to just "H") - confirmed
    # directly this doesn't crash get_buffer()/pack_into/unpack_from at either end.
    manager = MockAsyFramManager()
    store = PrintLogHistoryStore(manager, history_length=0)
    run(store.setup())
    assert store.initialized is True
    run(store.err_s("e", errno=1))
    assert store.err_count == 1
    assert list(store.history) == []
    assert run(store._read()) is True


def test_printloghistorystore_write_uses_explicit_little_endian_layout() -> None:
    # Pins down the on-the-wire format explicitly now that print_log.py uses "<H"/"B"*n instead of
    # a bare "H"/"B"*n format string - confirmed directly that MicroPython's struct defaults a
    # no-prefix format to "@" (native alignment/padding), not "<", though it made no observable
    # difference for this specific field order (see module docstring).
    manager = MockAsyFramManager()
    store = PrintLogHistoryStore(manager, history_length=2)
    store.err_count = 0x1234
    store.history.extend([5, 6])
    run(store._write())
    raw = manager.backing.read(0, 4)
    assert raw is not None
    assert list(raw) == [0x34, 0x12, 5, 6]  # little-endian u16, then 2 raw history bytes


def test_printloghistorystore_reset_persists_cleared_state_across_a_reboot() -> None:
    manager = MockAsyFramManager()
    store = PrintLogHistoryStore(manager, history_length=3)
    run(store.setup())
    run(store.err_s("e", errno=1))
    run(store.reset())

    rebooted_store = PrintLogHistoryStore(MockAsyFramManager(backing=manager.backing), history_length=3)
    run(rebooted_store.setup())
    assert rebooted_store.err_count == 0
    assert list(rebooted_store.history) == [0, 0, 0]


# ---------------------------------------------------------------------------
# PrintLogHistoryStore - every simulated FRAM failure mode (tests/_fram_mock.py's fault injection)
# ---------------------------------------------------------------------------


def test_printloghistorystore_get_chunk_raising_leaves_fram_none() -> None:
    store = PrintLogHistoryStore(MockAsyFramManager(raise_on_get_chunk=True), history_length=4)
    assert store.fram is None
    assert run(store._write()) is False
    assert run(store._read()) is False


def test_printloghistorystore_get_buffer_raising_is_caught_by_write() -> None:
    store = PrintLogHistoryStore(MockAsyFramManager(), history_length=4)
    assert isinstance(store.fram, _MockFramChunk)  # whitebox: narrows the type to reach the mock's fault flags
    store.fram.raise_on_get_buffer = True
    assert run(store._write()) is False


def test_printloghistorystore_get_buffer_raising_is_caught_by_read() -> None:
    store = PrintLogHistoryStore(MockAsyFramManager(), history_length=4)
    assert isinstance(store.fram, _MockFramChunk)
    store.fram.raise_on_get_buffer = True
    assert run(store._read()) is False


def test_printloghistorystore_broken_buffer_is_caught_by_write() -> None:
    # get_buffer() "succeeds" but returns a buffer whose get_data_buf() is None - struct.pack_into
    # on that None then raises TypeError, which the widened try/except must still catch (this is
    # the exact shape of bug this session's audit found and fixed: get_buffer()/get_data_buf() used
    # to sit outside the try block entirely).
    store = PrintLogHistoryStore(MockAsyFramManager(), history_length=4)
    assert isinstance(store.fram, _MockFramChunk)
    store.fram.broken_buffer = True
    assert run(store._write()) is False


def test_printloghistorystore_broken_buffer_is_caught_by_read() -> None:
    store = PrintLogHistoryStore(MockAsyFramManager(), history_length=4)
    assert isinstance(store.fram, _MockFramChunk)
    store.fram.broken_buffer = True
    assert run(store._read()) is False


def test_printloghistorystore_write_into_raising_is_caught() -> None:
    store = PrintLogHistoryStore(MockAsyFramManager(), history_length=4)
    assert isinstance(store.fram, _MockFramChunk)
    store.fram.raise_on_write = True
    assert run(store._write()) is False


def test_printloghistorystore_write_into_returns_false_is_surfaced() -> None:
    # Distinct from raising: a hardware-reported failure that write_into() itself already turns
    # into a clean False return, without print_log.py needing to catch anything.
    store = PrintLogHistoryStore(MockAsyFramManager(), history_length=4)
    assert isinstance(store.fram, _MockFramChunk)
    store.fram.write_returns_false = True
    assert run(store._write()) is False


def test_printloghistorystore_read_into_raising_is_caught() -> None:
    store = PrintLogHistoryStore(MockAsyFramManager(), history_length=4)
    assert isinstance(store.fram, _MockFramChunk)
    store.fram.raise_on_read = True
    assert run(store._read()) is False


def test_printloghistorystore_read_into_returns_false_is_surfaced() -> None:
    store = PrintLogHistoryStore(MockAsyFramManager(), history_length=4)
    assert isinstance(store.fram, _MockFramChunk)
    run(store._write())  # something real is persisted first
    store.fram.read_returns_false = True
    assert run(store._read()) is False


def test_printloghistorystore_setup_fails_cleanly_when_both_read_and_write_fail() -> None:
    store = PrintLogHistoryStore(MockAsyFramManager(), history_length=4)
    assert isinstance(store.fram, _MockFramChunk)
    store.fram.read_returns_false = True
    store.fram.write_returns_false = True
    run(store.setup())
    assert store.initialized is False


def test_printloghistorystore_err_s_survives_a_write_failure_without_raising() -> None:
    # _store_err()'s own "if not await self._write(): print(...)" fallback must not itself raise
    # even though the underlying write_into() does - in-memory state should still update.
    store = PrintLogHistoryStore(MockAsyFramManager(), history_length=4)
    assert isinstance(store.fram, _MockFramChunk)
    run(store.setup())
    store.fram.raise_on_write = True
    run(store.err_s("boom", errno=3))
    assert store.err_count == 1
    assert list(store.history)[-1] == 3


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
