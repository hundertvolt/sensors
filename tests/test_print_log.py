import asyncio

from _fram_mock import MockAsyFramManager, _MockFramChunk

from print_log import PrintLog, PrintLogHistory, PrintLogHistStore

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


# ---------------------------------------------------------------------------
# PrintLogHistStore - FRAM-backed persistence, against a mocked FRAM API
# (tests/_fram_mock.py - see BACKLOG.md for why the real asy_fram_manager.py isn't used here yet)
# ---------------------------------------------------------------------------


def test_printloghiststore_allocates_a_chunk_from_the_fram_manager() -> None:
    store = PrintLogHistStore(MockAsyFramManager(), history_length=4)
    assert store.fram is not None


def test_printloghiststore_out_of_memory_leaves_fram_none_and_never_raises() -> None:
    store = PrintLogHistStore(MockAsyFramManager(out_of_memory=True), history_length=4)
    assert store.fram is None
    assert run(store._write()) is False
    assert run(store._read()) is False


def test_printloghiststore_read_before_any_write_fails_cleanly() -> None:
    store = PrintLogHistStore(MockAsyFramManager(), history_length=4)
    assert run(store._read()) is False  # chunk allocated but never written yet - not "all zero"


def test_printloghiststore_setup_first_time_falls_back_to_writing_defaults() -> None:
    store = PrintLogHistStore(MockAsyFramManager(), history_length=4)
    run(store.setup())
    assert store.initialized is True


def test_printloghiststore_err_s_persists_and_survives_a_simulated_reboot() -> None:
    manager = MockAsyFramManager()
    store = PrintLogHistStore(manager, history_length=4)
    run(store.setup())
    run(store.err_s("boom", errno=3))
    assert store.err_count == 1

    # Simulate a reboot: a fresh manager/store pair, replaying the same get_chunk() call, wrapping
    # the same backing bytes - same as a real chip's contents surviving a power cycle.
    rebooted_store = PrintLogHistStore(MockAsyFramManager(backing=manager.backing), history_length=4)
    run(rebooted_store.setup())
    assert rebooted_store.err_count == 1
    assert list(rebooted_store.history)[-1] == 3


def test_printloghiststore_reset_persists_cleared_state_across_a_reboot() -> None:
    manager = MockAsyFramManager()
    store = PrintLogHistStore(manager, history_length=3)
    run(store.setup())
    run(store.err_s("e", errno=1))
    run(store.reset())

    rebooted_store = PrintLogHistStore(MockAsyFramManager(backing=manager.backing), history_length=3)
    run(rebooted_store.setup())
    assert rebooted_store.err_count == 0
    assert list(rebooted_store.history) == [0, 0, 0]


# ---------------------------------------------------------------------------
# PrintLogHistStore - every simulated FRAM failure mode (tests/_fram_mock.py's fault injection)
# ---------------------------------------------------------------------------


def test_printloghiststore_get_chunk_raising_leaves_fram_none() -> None:
    store = PrintLogHistStore(MockAsyFramManager(raise_on_get_chunk=True), history_length=4)
    assert store.fram is None
    assert run(store._write()) is False
    assert run(store._read()) is False


def test_printloghiststore_get_buffer_raising_is_caught_by_write() -> None:
    store = PrintLogHistStore(MockAsyFramManager(), history_length=4)
    assert isinstance(store.fram, _MockFramChunk)  # whitebox: narrows the type to reach the mock's fault flags
    store.fram.raise_on_get_buffer = True
    assert run(store._write()) is False


def test_printloghiststore_get_buffer_raising_is_caught_by_read() -> None:
    store = PrintLogHistStore(MockAsyFramManager(), history_length=4)
    assert isinstance(store.fram, _MockFramChunk)
    store.fram.raise_on_get_buffer = True
    assert run(store._read()) is False


def test_printloghiststore_broken_buffer_is_caught_by_write() -> None:
    # get_buffer() "succeeds" but returns a buffer whose get_data_buf() is None - struct.pack_into
    # on that None then raises TypeError, which the widened try/except must still catch (this is
    # the exact shape of bug this session's audit found and fixed: get_buffer()/get_data_buf() used
    # to sit outside the try block entirely).
    store = PrintLogHistStore(MockAsyFramManager(), history_length=4)
    assert isinstance(store.fram, _MockFramChunk)
    store.fram.broken_buffer = True
    assert run(store._write()) is False


def test_printloghiststore_broken_buffer_is_caught_by_read() -> None:
    store = PrintLogHistStore(MockAsyFramManager(), history_length=4)
    assert isinstance(store.fram, _MockFramChunk)
    store.fram.broken_buffer = True
    assert run(store._read()) is False


def test_printloghiststore_write_into_raising_is_caught() -> None:
    store = PrintLogHistStore(MockAsyFramManager(), history_length=4)
    assert isinstance(store.fram, _MockFramChunk)
    store.fram.raise_on_write = True
    assert run(store._write()) is False


def test_printloghiststore_write_into_returns_false_is_surfaced() -> None:
    # Distinct from raising: a hardware-reported failure that write_into() itself already turns
    # into a clean False return, without print_log.py needing to catch anything.
    store = PrintLogHistStore(MockAsyFramManager(), history_length=4)
    assert isinstance(store.fram, _MockFramChunk)
    store.fram.write_returns_false = True
    assert run(store._write()) is False


def test_printloghiststore_read_into_raising_is_caught() -> None:
    store = PrintLogHistStore(MockAsyFramManager(), history_length=4)
    assert isinstance(store.fram, _MockFramChunk)
    store.fram.raise_on_read = True
    assert run(store._read()) is False


def test_printloghiststore_read_into_returns_false_is_surfaced() -> None:
    store = PrintLogHistStore(MockAsyFramManager(), history_length=4)
    assert isinstance(store.fram, _MockFramChunk)
    run(store._write())  # something real is persisted first
    store.fram.read_returns_false = True
    assert run(store._read()) is False


def test_printloghiststore_setup_fails_cleanly_when_both_read_and_write_fail() -> None:
    store = PrintLogHistStore(MockAsyFramManager(), history_length=4)
    assert isinstance(store.fram, _MockFramChunk)
    store.fram.read_returns_false = True
    store.fram.write_returns_false = True
    run(store.setup())
    assert store.initialized is False


def test_printloghiststore_err_s_survives_a_write_failure_without_raising() -> None:
    # _store_err()'s own "if not await self._write(): print(...)" fallback must not itself raise
    # even though the underlying write_into() does - in-memory state should still update.
    store = PrintLogHistStore(MockAsyFramManager(), history_length=4)
    assert isinstance(store.fram, _MockFramChunk)
    run(store.setup())
    store.fram.raise_on_write = True
    run(store.err_s("boom", errno=3))
    assert store.err_count == 1
    assert list(store.history)[-1] == 3


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
