"""Tests scripts/_digital_twin_ci_suite.py's pure helpers without a live twin: _error_type_count()'s type_char selection
(Run 8's "W" case), the fault matrix's instance selection, the shutdown line's parse and its feed-gap verdict, and the
events Runs 9 and 10 end their waits on - the same way test_digital_twin_ci_suite_soak.py does for Run 11's."""

import errno
import functools
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import TYPE_CHECKING

import pytest
import tomllib
from _devices import DEVICE_NAMES, device_toml

import scripts._twin_process as twin_process

if TYPE_CHECKING:
    from collections.abc import Callable


def _ctx(ci_suite: ModuleType, keys: "list[str]", logs_dir: Path = Path("/nonexistent")) -> object:
    # One RunContext over the named instance keys; a key "<driver>_<ext>" is an instance with that name_ext.
    instances = tuple(sorted(ci_suite.Instance(key, *(key.rsplit("_", 1) if key.startswith("uart_link_") else (key, ""))) for key in keys))
    return ci_suite.RunContext(micropython_bin="/nonexistent", logs_dir=logs_dir, device="fixture-device", module="sensortask_fixture", wiring_plan_path=Path("/nonexistent"), instances=instances, gc_threshold=-1, routes=("/status",))


# ---------------------------------------------------------------------------
# _error_type_count() - "counter" bumps on errors AND warnings alike, so a driver's own recovery
# notice inflates it without any new failure. Counting one type's history entries is what the
# suite's "did N of THIS kind of event happen" checks actually need.
# ---------------------------------------------------------------------------


def test_error_type_count_defaults_to_counting_errors_only(ci_suite: ModuleType) -> None:
    entry = _entry((18, "E"), (5, "W"), (18, "E"))
    assert ci_suite._error_type_count(entry) == 2


def test_error_type_count_selects_warnings_when_asked(ci_suite: ModuleType) -> None:
    # Run 8's real case: asy_wifi_service.py records a scripted connect failure via wrn_s(), so
    # WIFI's own history is "W"-typed and an "E"-only count would read every one of them as zero.
    entry = _entry((18, "E"), (5, "W"), (5, "W"), (5, "W"))
    assert ci_suite._error_type_count(entry, "W") == 3
    assert ci_suite._error_type_count(entry) == 1


def test_error_type_count_ignores_the_empty_ring_slots(ci_suite: ModuleType) -> None:
    # asy_print_log.py pre-fills the history deque with its own "nothing recorded" sentinel, published
    # as type "N" - a full ten-slot ring with one real entry must still count as one, never ten.
    entry = _entry(*([(0, "N")] * 9), (5, "W"))
    assert ci_suite._error_type_count(entry, "W") == 1
    assert ci_suite._error_type_count(entry) == 0


def test_error_type_count_survives_a_missing_or_malformed_history(ci_suite: ModuleType) -> None:
    # _errcount() returns {} for any /status read it couldn't parse, and the published history is
    # zipped from two independent lists - neither may turn a degraded read into a raised exception
    # inside a run function's own assertion.
    assert ci_suite._error_type_count({}) == 0
    assert ci_suite._error_type_count({"counter": 3}) == 0
    assert ci_suite._error_type_count({"history": ["not-a-dict", None, 7]}) == 0
    assert ci_suite._error_type_count({"history": [{"num": 1}]}) == 0


def test_error_type_count_is_never_satisfied_by_the_raw_counter(ci_suite: ModuleType) -> None:
    # The regression this function exists to prevent: a recovery notice bumping "counter" past the
    # target while no new error of the counted type was ever recorded.
    entry = _entry((18, "E"), (14, "W"), counter=9)
    assert ci_suite._error_type_count(entry) == 1


# ---------------------------------------------------------------------------
# _failure_events() - under asy_print_log.py's newest-entry rule a repeated code spends no slot, so a
# failure is an ErrCount step not backed by a warning slot.
# ---------------------------------------------------------------------------


def test_failure_events_counts_repeats_the_ring_folded_into_one_slot(ci_suite: ModuleType) -> None:
    assert ci_suite._failure_events(_entry((10, "E"), counter=3)) == 3


def test_failure_events_subtracts_each_warning_slot(ci_suite: ModuleType) -> None:
    assert ci_suite._failure_events(_entry((10, "E"), (15, "W"), (10, "E"), counter=4)) == 3


def test_failure_events_is_zero_for_an_empty_or_unreadable_entry(ci_suite: ModuleType) -> None:
    assert ci_suite._failure_events(_entry()) == 0
    assert ci_suite._failure_events({}) == -1, "an entry without a counter is no count at all, never zero failures"
    assert ci_suite._link_failures({}, {}) == -1


def test_link_failures_count_only_what_one_link_added(ci_suite: ModuleType) -> None:
    # Run 5c's real case: each earlier link's boot logged SGP40's no-backup warning, folded into one slot.
    before = _entry((65, "W"), counter=2)
    after = _entry((65, "W"), (10, "E"), (65, "W"), counter=6)
    assert ci_suite._failure_events(after) == 4
    assert ci_suite._link_failures(before, after) == 3


def test_a_restore_equal_to_the_ring_written_is_whole(ci_suite: ModuleType) -> None:
    written = _entry((10, "E"), (65, "W"), counter=4)
    assert ci_suite._restore_is_all_or_nothing(written, _entry((10, "E"), (65, "W"), counter=5))


def test_a_whole_ring_followed_by_this_boots_own_warning_is_whole(ci_suite: ModuleType) -> None:
    # A case CI meets on real devices: the restored ring, then the new boot's no-backup warning after it.
    written = _entry((10, "E"), counter=3)
    assert ci_suite._restore_is_all_or_nothing(written, _entry((10, "E"), (65, "W"), counter=4))
    assert not ci_suite._restore_is_all_or_nothing(written, _entry((10, "E"), (65, "W"), counter=2))


def test_a_lost_ring_holding_only_this_boots_warning_is_nothing(ci_suite: ModuleType) -> None:
    written = _entry((10, "E"), (65, "W"), counter=4)
    assert ci_suite._restore_is_all_or_nothing(written, _entry((65, "W"), counter=1))
    assert ci_suite._restore_is_all_or_nothing(written, _entry())


def test_a_partial_ring_or_a_lost_count_is_neither(ci_suite: ModuleType) -> None:
    written = _entry((11, "E"), (10, "E"), (65, "W"), counter=6)
    assert not ci_suite._restore_is_all_or_nothing(written, _entry((10, "E"), (65, "W"), counter=6))
    assert not ci_suite._restore_is_all_or_nothing(written, _entry((11, "E"), (10, "E"), (65, "W"), counter=2))
    assert not ci_suite._restore_is_all_or_nothing(written, _entry((10, "E"), (65, "W"), (11, "E"), counter=7))


# ---------------------------------------------------------------------------
# The per-device fault matrix: every instance the device's TOML wires, by its --fault key.
# ---------------------------------------------------------------------------


def _drive_timed_reset(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch, elapsed_s: float, status: int = 200, word: object = "Valid") -> "tuple[int, list[str], list[str]]":
    # Runs _put_reset_errors_timed() with a scripted elapsed time and answer word; returns (status, oks, failures).
    clock = iter([1000.0, 1000.0 + elapsed_s])
    monkeypatch.setattr(ci_suite.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(ci_suite, "_http", lambda *_a, **_k: (status, {"result": {"ResetErrors": word}}))
    oks: list[str] = []
    monkeypatch.setattr(ci_suite, "_check", lambda *, condition, msg: (oks if condition else failures).append(msg))
    failures: list[str] = []
    return ci_suite._put_reset_errors_timed("Run T"), oks, failures


def test_the_fault_instances_are_sorted_by_key_and_filtered_by_the_table(ci_suite: ModuleType) -> None:
    ctx = _ctx(ci_suite, ["sgp40", "fram", "scd30", "uart_link_init", "uart_link_resp"])
    assert [i.key for i in ci_suite._fault_instances(ctx, ci_suite._SUSTAINED_FAULT)] == ["fram", "scd30", "sgp40", "uart_link_init", "uart_link_resp"]
    assert [i.key for i in ci_suite._fault_instances(ctx, ci_suite._HANG_MATRIX)] == ["fram", "scd30", "sgp40"]


def test_an_instance_names_its_own_error_source(ci_suite: ModuleType) -> None:
    # instance_name(): an empty name_ext keeps the driver's _NAME, a non-empty one appends "_<name_ext>".
    assert ci_suite.Instance("sgp40", "sgp40", "").errcount_name == "SGP40"
    assert ci_suite.Instance("uart_link_init", "uart_link", "init").errcount_name == "UART_init"


def test_every_faultable_driver_has_both_an_op_and_an_errcount_name(ci_suite: ModuleType) -> None:
    # Run 3 looks a driver up in _SUSTAINED_FAULT and every run names its source through _DRIVER_ERRCOUNT_NAME; the
    # two tables are hand-kept separately, and a driver present in one but not the other raises mid-run.
    assert set(ci_suite._SUSTAINED_FAULT) == set(ci_suite._DRIVER_ERRCOUNT_NAME)
    assert set(ci_suite._DRIVER_ERRCOUNT_NAME) >= ci_suite._NO_PERSIST_WHEN_FRAM_FAULTED
    assert set(ci_suite._DRIVER_ERRCOUNT_NAME) >= ci_suite._MEASUREMENT_DRIVERS


def test_run_5c_faults_every_chip_instance_but_never_the_store_or_a_link(ci_suite: ModuleType) -> None:
    # Run 5c's premise is a HEALTHY store, so its chain is every chip instance: faulting the store voids it, and a
    # UART link has no bounded fault in the vocabulary. Checked as an identity, so a new chip driver joins both.
    ctx = _ctx(ci_suite, ["scd30", "sgp40", "bmp3xx", "isl29125", "fram", "uart_link_init"])
    assert [i.key for i in ci_suite._healthy_store_fault_instances(ctx)] == ["bmp3xx", "isl29125", "scd30", "sgp40"]
    assert set(ci_suite._BOUNDED_FAULT) == set(ci_suite._SUSTAINED_FAULT) - {"fram", "uart_link"}


def test_the_error_sources_exempt_from_run_5cs_loss_sweep_are_the_store_and_the_ram_only_config_log(ci_suite: ModuleType) -> None:
    # Everything else in errcount is FRAM-backed and must come back across a commanded reboot. FRAMManager
    # cannot persist its own history through the store that failed, and CFGMGR_SCD30 is RAM-only (owner,
    # 2026-09-29: 'no extra FRAM chunk'); _sensortask_scenarios.py pins the same set from the real object graph.
    assert sorted(ci_suite._IN_MEMORY_ONLY_ERROR_SOURCES) == ["CFGMGR_SCD30", "FRAM"]
    names = set(ci_suite._DRIVER_ERRCOUNT_NAME.values())
    assert ci_suite._IN_MEMORY_ONLY_ERROR_SOURCES.issubset(names | {f"CFGMGR_{name}" for name in names})


def test_every_i2c_or_spi_attached_driver_a_real_device_declares_is_faultable(ci_suite: ModuleType) -> None:
    # The three tables above are only checked against EACH OTHER, which let the ISL29125 be
    # absent from all of them and silently skipped from the day it shipped. This is the outward
    # check: the real device set decides who belongs.

    # Every bus a device declares an instance on - i2c, spi and the uart_link pair's - is faulted by Run 3.
    attached = set()
    for device in DEVICE_NAMES:
        doc = tomllib.loads(device_toml(device).read_text(encoding="utf-8"))
        attached |= {inst["driver"] for inst in doc.get("instance", []) if str(inst.get("bus", "")).startswith(("i2c", "spi", "uart"))}
    missing = sorted(attached - set(ci_suite._SUSTAINED_FAULT))
    assert not missing, f"bus-attached driver(s) {missing} are declared by a real device but absent from _SUSTAINED_FAULT, so Run 3 skips them without saying so"


# ---------------------------------------------------------------------------
# _errcount() / _errcount_required(), the tolerant/strict split that guards the vacuous-pass
# class: {} for an unreadable /status reads as counter 0 with an empty history, so an assertion
# expecting 0 would hold against a server that answered nothing - as Runs 4, 5c and 8 all did.
# ---------------------------------------------------------------------------


def _entry(*history: tuple[int, str], counter: int | None = None) -> dict[str, object]:
    # One GET /status errcount entry, in asy_webserver_service.py's own published shape.
    items = [{"num": num, "type": kind} for num, kind in history]
    return {"counter": len(items) if counter is None else counter, "history": items}


_READABLE = {"errcount": {"SGP40": {"counter": 0, "history": [{"num": 0, "type": "N"}]}}}


def test_errcount_is_tolerant_so_the_polling_helpers_can_retry(ci_suite: ModuleType, http_stub: "Callable[[int, object], None]") -> None:
    # The tolerance is deliberate and load-bearing: _wait_for_errcount_above()/
    # _wait_for_error_type_count() call this in a loop during boot, where a transient non-200 must
    # retry rather than abort the whole run.
    http_stub(503, None)
    assert ci_suite._errcount("SGP40") == {}


def test_errcount_is_also_tolerant_of_a_200_with_an_unusable_body(ci_suite: ModuleType, http_stub: "Callable[[int, object], None]") -> None:
    http_stub(200, "not-a-dict")
    assert ci_suite._errcount("SGP40") == {}
    http_stub(200, {"errcount": {"SGP40": "not-a-dict-either"}})
    assert ci_suite._errcount("SGP40") == {}


def test_errcount_required_raises_instead_of_answering_an_empty_entry(ci_suite: ModuleType, http_stub: "Callable[[int, object], None]") -> None:
    # THE regression test for the vacuous-pass class. Before the split, Run 4's `counter == 0`,
    # Run 5c's `_error_type_count(...) == 0` and Run 8's `restored in (0, N)` all held here.
    http_stub(503, None)
    with pytest.raises(RuntimeError, match="readable errcount entry"):
        ci_suite._errcount_required("SGP40")


def test_errcount_required_raises_for_a_source_missing_from_a_readable_status(ci_suite: ModuleType, http_stub: "Callable[[int, object], None]") -> None:
    # Every registered error source appears in errcount whether or not it ever logged, so a missing
    # entry is a real failure - never "this module simply has no errors".
    http_stub(200, {"errcount": {"SCD30": {"counter": 0, "history": []}}})
    with pytest.raises(RuntimeError, match="SGP40"):
        ci_suite._errcount_required("SGP40")


def test_errcount_required_returns_the_entry_when_status_is_genuinely_readable(ci_suite: ModuleType, http_stub: "Callable[[int, object], None]") -> None:
    http_stub(200, _READABLE)
    assert ci_suite._errcount_required("SGP40") == {"counter": 0, "history": [{"num": 0, "type": "N"}]}


def test_errcount_all_raises_rather_than_sweeping_an_unreadable_status(ci_suite: ModuleType, http_stub: "Callable[[int, object], None]") -> None:
    # Run 5c's device-wide sweep iterates whatever this returns, so a tolerant {} here would turn
    # "the server answered nothing" into "no source lost anything" - the same vacuous pass the
    # _errcount()/_errcount_required() split exists to prevent, one level up.
    http_stub(503, None)
    with pytest.raises(RuntimeError, match="readable body"):
        ci_suite._errcount_all()
    http_stub(200, "not-a-dict")
    with pytest.raises(RuntimeError, match="readable body"):
        ci_suite._errcount_all()


def test_errcount_all_raises_on_a_200_carrying_no_usable_table(ci_suite: ModuleType, http_stub: "Callable[[int, object], None]") -> None:
    bodies: list[object] = [{}, {"errcount": {}}, {"errcount": "not-a-dict"}]
    for body in bodies:
        http_stub(200, body)
        with pytest.raises(RuntimeError, match="no usable errcount table"):
            ci_suite._errcount_all()


def test_errcount_all_drops_only_the_rows_that_are_not_entries(ci_suite: ModuleType, http_stub: "Callable[[int, object], None]") -> None:
    http_stub(200, {"errcount": {"SGP40": {"counter": 1, "history": []}, "JUNK": "not-a-dict"}})
    assert ci_suite._errcount_all() == {"SGP40": {"counter": 1, "history": []}}


def test_error_counts_settle_only_once_consecutive_reads_agree(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    # Snapshotting mid-fault is the failure this guards: the reboot would then be compared against
    # entries that landed AFTER the snapshot, and a run that lost nothing would read as a loss.
    reads = iter([1, 2, 3, 3, 3])
    monkeypatch.setattr(ci_suite, "_errcount_all", lambda: {"SGP40": _entry(*[(10, "E")] * next(reads))})
    monkeypatch.setattr(ci_suite.time, "sleep", lambda _s: None)
    assert ci_suite._wait_for_error_counts_to_settle(["SGP40"], timeout_s=30.0) == {"SGP40": 3}


def test_error_counts_settle_on_the_counter_while_a_repeated_code_keeps_one_slot(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    # The newest-entry rule: three identical failures hold one slot, so only the counter shows them landing.
    reads = iter([1, 2, 3, 3, 3])
    monkeypatch.setattr(ci_suite, "_errcount_all", lambda: {"SGP40": _entry((10, "E"), counter=next(reads))})
    monkeypatch.setattr(ci_suite.time, "sleep", lambda _s: None)
    assert ci_suite._wait_for_error_counts_to_settle(["SGP40"], timeout_s=30.0) == {"SGP40": 3}


def test_error_counts_that_never_settle_raise_instead_of_returning_a_moving_target(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    toggle = [0]

    def _never_agrees() -> dict[str, dict[str, object]]:
        toggle[0] ^= 1
        return {"SGP40": _entry(*[(10, "E")] * (1 + toggle[0]))}

    monkeypatch.setattr(ci_suite, "_errcount_all", _never_agrees)
    monkeypatch.setattr(ci_suite.time, "sleep", lambda _s: None)
    with pytest.raises(RuntimeError, match="never settled"):
        ci_suite._wait_for_error_counts_to_settle(["SGP40"], timeout_s=0.2, interval_s=0.0)


def test_error_counts_settle_across_every_name_at_once_not_one_at_a_time(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    # A per-name settle would call SGP40 settled while SCD30 was still climbing, and snapshot both.
    pairs = iter([(3, 1), (3, 2), (3, 3), (3, 3), (3, 3)])
    def _table() -> dict[str, dict[str, object]]:
        sgp, scd = next(pairs)
        return {"SGP40": _entry(*[(10, "E")] * sgp), "SCD30": _entry(*[(10, "E")] * scd)}
    monkeypatch.setattr(ci_suite, "_errcount_all", _table)
    monkeypatch.setattr(ci_suite.time, "sleep", lambda _s: None)
    assert ci_suite._wait_for_error_counts_to_settle(["SGP40", "SCD30"], timeout_s=30.0) == {"SGP40": 3, "SCD30": 3}


def test_the_run_4_assertion_shape_fails_closed_on_an_empty_entry(ci_suite: ModuleType) -> None:
    # Run 4 keeps `entry.get("counter", -1) == 0` rather than a bare `== 0`. Pinned directly,
    # because the -1 looks like a typo and reverting it to 0 silently restores the old hole.
    unreadable: dict[str, int] = {}
    assert unreadable.get("counter", -1) != 0
    assert {"counter": 0}.get("counter", -1) == 0


# ---------------------------------------------------------------------------
# _put_reset_errors_timed() - the elapsed-time budget (SPECIFICATION.md C.7). A timeout only catches
# a call that never finished; the budget covers the band between a normal reset and the server's own cap.
# ---------------------------------------------------------------------------


def _failures_of(ci_suite: ModuleType, call: "Callable[[], object]") -> "list[str]":
    saved = list(ci_suite._FAILURES)
    ci_suite._FAILURES.clear()
    try:
        call()
        return list(ci_suite._FAILURES)
    finally:
        ci_suite._FAILURES[:] = saved


def test_a_sweep_inside_the_budget_passes_and_reports_its_share_of_the_cap(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    status, oks, failures = _drive_timed_reset(ci_suite, monkeypatch, elapsed_s=8.28)  # the worst real twin sample
    assert status == 200
    assert not failures
    assert "8.28s" in oks[0] and "55% of the server's own 15.0s cap" in oks[0]


def test_a_sweep_past_the_budget_fails_even_though_the_request_itself_succeeded(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    # The whole point: HTTP 200 and well under the client timeout, yet still a failure. A plain
    # timeout can never catch this case.
    status, oks, failures = _drive_timed_reset(ci_suite, monkeypatch, elapsed_s=13.0)
    assert status == 200, "the budget check must not change what the caller sees"
    assert not [m for m in oks if "budget" in m]
    assert len(failures) == 1 and "13.00s" in failures[0]


@pytest.mark.parametrize("word", ["Failed", "Invalid", None])
def test_a_reset_that_did_not_answer_valid_fails_inside_the_budget(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch, word: object) -> None:
    # "Failed" is a store whose cleared state was not written: HTTP 200 and fast, yet the history it should clear stays.
    status, _oks, failures = _drive_timed_reset(ci_suite, monkeypatch, elapsed_s=1.0, word=word)
    assert status == 200
    assert len(failures) == 1 and f"({word!r})" in failures[0]


def test_the_budget_boundary_is_exclusive(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    # Exactly at the budget is a failure, not a pass - pinned so a later `<=` refactor is caught.
    _status, oks, failures = _drive_timed_reset(ci_suite, monkeypatch, elapsed_s=ci_suite._RESET_ERRORS_BUDGET_S)
    assert not [m for m in oks if "budget" in m]
    assert len(failures) == 1


def test_the_budget_sits_between_the_observed_worst_case_and_the_servers_own_cap(ci_suite: ModuleType) -> None:
    # Sized from measurement, not taste: the twin's worst observed dev sweep is 8.91s and real
    # hardware is 6.32s idle / 11.58s under three concurrent readers. A budget at or below the
    # worst observed value flakes; at or above the cap it can never fire before the server aborts.
    assert 8.91 < ci_suite._RESET_ERRORS_BUDGET_S < ci_suite._SERVER_OUTER_CAP_S
    assert ci_suite._RESET_ERRORS_BUDGET_S < ci_suite._RESET_ERRORS_TIMEOUT_S, "the budget must trip before the client timeout, or it is unreachable"


def test_the_commanded_reset_deadline_follows_both_src_constants(ci_suite: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The deadline a reboot/bootloader/resetconfig run allows is _RESET_DELAY + _TASK_CHECK_TIME +
    # a margin, read from src. A copy with both changed must move the deadline by exactly their sum.
    src = tmp_path / "src"
    src.mkdir()
    original = (Path(ci_suite.SRC_DIR) / "asy_system_service.py").read_text(encoding="utf-8")
    modified = original.replace("_RESET_DELAY = const(4)", "_RESET_DELAY = const(9)").replace("_TASK_CHECK_TIME = const(2)", "_TASK_CHECK_TIME = const(5)")
    assert modified != original, "the src constants are no longer in the pinned form - update this case with them"
    (src / "asy_system_service.py").write_text(modified, encoding="utf-8")
    monkeypatch.setattr(ci_suite, "SRC_DIR", src)
    assert ci_suite._commanded_reset_deadline_s() == 9 + 5 + ci_suite._COMMANDED_RESET_MARGIN_S, "the deadline must follow both constants and its margin"


def test_every_reset_errors_call_in_the_suite_goes_through_the_timed_helper(ci_suite: ModuleType) -> None:
    # A budget helper that some call site bypasses measures nothing on that path. Checked against the
    # real source: a second raw _http("PUT", "/status", {"ResetErrors": ...}) is exactly how the gap
    # would reappear, and it would still pass every behavioural test above.
    source = Path(ci_suite.__file__ or "").read_text(encoding="utf-8")
    raw = [line.strip() for line in source.splitlines() if '"ResetErrors"' in line and "_http(" in line]
    assert len(raw) == 1, f"the ResetErrors PUT must be issued in exactly one place - _put_reset_errors_timed() - found {len(raw)}: {raw}"
    assert source.count("_put_reset_errors_timed(") >= 3, "both run functions that reset the error logs must call the timed helper (plus its own definition)"


def test_the_persisted_error_modules_are_real_errcount_sources_and_not_empty(ci_suite: ModuleType) -> None:
    # Run 5b/5c loop over this tuple. Empty, or carrying a name /status never publishes, and the
    # whole all-or-nothing restore check degrades into a no-op that still reports a pass - the same
    # vacuous-pass class the tolerant/strict split above closes, arriving through the table instead.
    assert ci_suite._PERSISTED_ERROR_MODULES, "Run 5b would iterate over nothing and still pass"
    published = set(ci_suite._DRIVER_ERRCOUNT_NAME.values())
    for name in ci_suite._PERSISTED_ERROR_MODULES:
        assert name in published, f"{name!r} is not an errcount source name - _errcount_required() would raise mid-run"


def test_the_sgp40_asymmetry_between_the_three_driver_sets_is_deliberate(ci_suite: ModuleType) -> None:
    # SGP40 is the one measurement driver outside the reset-to-0-with-FRAM-faulted set and the
    # one whose reboot persistence is actually proven - two halves of one decision. Adding it to
    # the first set, or dropping it from the second, would flip a real assertion unnoticed.
    assert "sgp40" in ci_suite._MEASUREMENT_DRIVERS
    assert "sgp40" not in ci_suite._NO_PERSIST_WHEN_FRAM_FAULTED, "SGP40's own history is deliberately not asserted to reset - see _PERSISTED_ERROR_MODULES' comment"
    assert ci_suite._DRIVER_ERRCOUNT_NAME["sgp40"] in ci_suite._PERSISTED_ERROR_MODULES
    assert ci_suite._NO_PERSIST_WHEN_FRAM_FAULTED < ci_suite._MEASUREMENT_DRIVERS, "the reset-to-0 set is a strict subset of the drivers that produce a reading"
# ---------------------------------------------------------------------------
# _check_no_memory_error_in_log() - Part I.4(e)'s twin half, which had no test of its own at all.
# ---------------------------------------------------------------------------


def test_a_caught_and_degraded_allocation_failure_is_caught_though_it_never_says_memoryerror(ci_suite: ModuleType, tmp_path: Path) -> None:
    # The real emitted form: src/'s handlers log str(e), and the interpreter's own message carries
    # no class name, so matching "MemoryError" alone only ever caught an uncaught traceback - the
    # exact opposite of "caught-and-logged counts as a failure too".
    assert _memory_error_verdict(ci_suite, tmp_path, "NTP Could not start NTP timer: memory allocation failed, allocating 512 bytes\n")


def test_an_uncaught_traceback_is_still_caught(ci_suite: ModuleType, tmp_path: Path) -> None:
    assert _memory_error_verdict(ci_suite, tmp_path, "Traceback (most recent call last):\nMemoryError: memory allocation failed\n")


def test_a_clean_run_log_records_no_failure(ci_suite: ModuleType, tmp_path: Path) -> None:
    assert _memory_error_verdict(ci_suite, tmp_path, "OK: served\nOK: clean shutdown\n") == []


@pytest.mark.parametrize("make", ["missing", "unreadable"])
def test_a_missing_or_unreadable_log_fails_the_check_and_names_the_path(ci_suite: ModuleType, tmp_path: Path, make: str) -> None:
    # Fails closed: a log the check cannot read is a run it cannot vouch for, never a clean one.
    log = tmp_path / "absent.log"
    if make == "unreadable":
        log.mkdir()  # reading a directory raises, as any unreadable log does
    saved = list(ci_suite._FAILURES)
    ci_suite._FAILURES.clear()
    try:
        ci_suite._check_no_memory_error_in_log(log, "Run 1")
        failures = list(ci_suite._FAILURES)
    finally:
        ci_suite._FAILURES[:] = saved
    assert len(failures) == 1, failures
    assert "Run 1" in failures[0] and str(log) in failures[0], failures


# ---------------------------------------------------------------------------
# Run 9's host that never answers: the request leaves this host and goes unanswered (NTP_NO_REPLY), or, with no
# route out (a network namespace holding only lo), the send itself fails (NTP_NOT_SENT). The route decides which.
# ---------------------------------------------------------------------------


def test_run_9_expects_no_reply_where_a_route_leaves_the_host(ci_suite: ModuleType) -> None:
    no_reply, not_sent = ci_suite.code("E", "NTP_NO_REPLY"), ci_suite.code("E", "NTP_NOT_SENT")
    ok, msg = ci_suite._ntp_unreachable_verdict([0, no_reply], route=True)
    assert ok, msg
    assert "NTP_NO_REPLY" in msg and "a route" in msg
    assert not ci_suite._ntp_unreachable_verdict([0, not_sent], route=True)[0]  # the other code is not this branch's
    assert not ci_suite._ntp_unreachable_verdict([0, not_sent, no_reply], route=True)[0]
    assert not ci_suite._ntp_unreachable_verdict([0], route=True)[0]


def test_run_9_expects_not_sent_where_no_route_leaves_the_host(ci_suite: ModuleType) -> None:
    no_reply, not_sent = ci_suite.code("E", "NTP_NO_REPLY"), ci_suite.code("E", "NTP_NOT_SENT")
    ok, msg = ci_suite._ntp_unreachable_verdict([not_sent], route=False)
    assert ok, msg
    assert "NTP_NOT_SENT" in msg and "no route" in msg
    assert not ci_suite._ntp_unreachable_verdict([no_reply], route=False)[0]
    assert not ci_suite._ntp_unreachable_verdict([], route=False)[0]


def test_the_route_probe_finds_the_loopback_route(ci_suite: ModuleType) -> None:
    assert ci_suite._route_leaves_host("127.0.0.1", 123) is True  # a UDP connect() sends nothing


class _NoRouteSocket:
    # A socket.socket stand-in whose connect() fails as a host with no route out does (ENETUNREACH).
    def __init__(self, *_args: object) -> None:
        self.closed = False

    def __enter__(self) -> "_NoRouteSocket":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.closed = True

    def connect(self, _addr: object) -> None:
        raise OSError(errno.ENETUNREACH, "Network is unreachable")


def test_the_route_probe_reports_a_host_with_no_route_out(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ci_suite.socket, "socket", _NoRouteSocket)
    assert ci_suite._route_leaves_host("192.0.2.1", 123) is False


# ---------------------------------------------------------------------------
# scripts/_twin_process.py's readers of the runner's own lines and exit codes, shared by the suite and the harness.
# ---------------------------------------------------------------------------

_PREFIX = "digital_twin/run_generic_integration.py [dev]"
_R0 = "0x00000000,0x00000000,0x00000000,0x00000000"
# The GC summary micropython.mem_info() prints right before the line: its max free sz is in heap blocks.
_GC_SUMMARY = " No. of 1-blocks: 14, 2-blocks: 4, max blk sz: 9, max free sz: 64730"
_SHUTDOWN = (
    f"{_GC_SUMMARY}\n{_PREFIX} shutdown: would_have_triggered_count=0 feed_count=41 largest_feed_gap_ms=812 wdt_timeout_ms=8000 "
    f"mem_backup: r0={_R0} public_destinations_refused=0 flash_stall_longest_ms=3 gc_block_bytes=32"
)


def test_the_shutdown_line_yields_every_field_and_one_uart_entry_per_instance() -> None:
    line = f"{_SHUTDOWN} uart=uart_link_initiator:transfers=12,failures=0,overruns=1 uart=uart_link_responder:transfers=11,failures=2,overruns=0"
    parsed = twin_process.parse_shutdown_line(f"boot\n{line}\nbye\n")
    assert parsed is not None
    assert (parsed.would_have_triggered_count, parsed.feed_count, parsed.largest_feed_gap_ms, parsed.wdt_timeout_ms) == (0, 41, 812, 8000)
    assert parsed.mem_backup_r0 == (0, 0, 0, 0)
    assert parsed.largest_free_block_bytes == 64730 * 32
    assert (parsed.public_destinations_refused, parsed.flash_stall_longest_ms) == (0, 3)
    assert parsed.uart == {"uart_link_initiator": twin_process.UartCounts(12, 0, 1), "uart_link_responder": twin_process.UartCounts(11, 2, 0)}
    assert parsed.uart["uart_link_initiator"].rx_laps_and_errors == 1


def test_a_shutdown_line_without_uart_links_has_an_empty_uart_table() -> None:
    parsed = twin_process.parse_shutdown_line(_SHUTDOWN)
    assert parsed is not None
    assert parsed.uart == {}
    words = twin_process.parse_shutdown_line(_SHUTDOWN.replace(f"r0={_R0}", "r0=0x00000001,0x2a5e0001,0x0,0x15a5a5a4"))
    assert words is not None
    assert words.mem_backup_r0 == (1, 0x2A5E0001, 0, 0x15A5A5A4)


def test_a_log_without_a_shutdown_line_reads_none() -> None:
    assert twin_process.parse_shutdown_line("boot\nTraceback (most recent call last):\n") is None


@pytest.mark.parametrize("field", ["would_have_triggered_count", "feed_count", "largest_feed_gap_ms", "wdt_timeout_ms", "public_destinations_refused", "flash_stall_longest_ms", "gc_block_bytes"])
def test_a_shutdown_line_missing_a_field_fails_naming_it(field: str) -> None:
    line = " ".join(token for token in _SHUTDOWN.split(" ") if not token.startswith(f"{field}="))
    with pytest.raises(ValueError, match=field):
        twin_process.parse_shutdown_line(line)


def test_a_shutdown_line_with_a_bad_r0_or_count_fails_naming_it() -> None:
    with pytest.raises(ValueError, match="mem_backup"):
        twin_process.parse_shutdown_line(_SHUTDOWN.replace(f"r0={_R0}", "r0=0x0,0x0,0x0"))
    with pytest.raises(ValueError, match="mem_backup"):
        twin_process.parse_shutdown_line(_SHUTDOWN.replace(f"mem_backup: r0={_R0} ", ""))
    with pytest.raises(ValueError, match="feed_count"):
        twin_process.parse_shutdown_line(_SHUTDOWN.replace("feed_count=41", "feed_count=4x"))


def test_a_shutdown_line_after_no_gc_summary_fails_naming_it() -> None:
    # The largest free block has no reader but mem_info()'s printout, so a line without it is a run that measured nothing.
    with pytest.raises(ValueError, match="max free sz"):
        twin_process.parse_shutdown_line(_SHUTDOWN.replace(f"{_GC_SUMMARY}\n", "booted\n"))


@pytest.mark.parametrize(("gap", "problem"), [(6000, False), (6300, True)])
def test_a_feed_gap_above_three_quarters_of_the_watchdog_timeout_is_a_near_reset(gap: int, *, problem: bool) -> None:
    line = twin_process.parse_shutdown_line(_SHUTDOWN.replace("largest_feed_gap_ms=812", f"largest_feed_gap_ms={gap}"))
    assert line is not None
    verdict = twin_process.feed_gap_verdict(line)
    assert (verdict is not None) == problem, verdict
    assert verdict is None or (f"{gap} ms" in verdict and "8000 ms" in verdict), verdict


@pytest.mark.parametrize("starves", [False, True])
def test_a_run_whose_feed_gap_came_near_the_watchdog_fails_unless_it_starves_it_by_design(ci_suite: ModuleType, tmp_path: Path, *, starves: bool) -> None:
    log = tmp_path / "twin.log"
    log.write_text(_SHUTDOWN.replace("largest_feed_gap_ms=812", "largest_feed_gap_ms=6300") + "\n", encoding="utf-8")
    run = twin_process.TwinRun(proc=None, log_path=log, log_file=log.open(encoding="utf-8"), device="fixture-device", state_dir=tmp_path)  # type: ignore[arg-type]
    failures = _failures_of(ci_suite, lambda: ci_suite._check_run_log(run, "Run 1", starves_watchdog=starves))
    gap_failures = [f for f in failures if "feed gap" in f]
    assert gap_failures == [] if starves else (len(gap_failures) == 1 and "6300 ms" in gap_failures[0]), failures


@pytest.mark.parametrize("token", ["uart=UART_init:transfers=1,failures=x,overruns=0", "uart=UART_init:transfers=1,failures=0", "uart=UART_init"])
def test_a_malformed_uart_entry_fails_naming_the_instance(token: str) -> None:
    with pytest.raises(ValueError, match="UART_init"):
        twin_process.parse_shutdown_line(f"{_SHUTDOWN} {token}")


def test_a_uart_instance_named_twice_fails() -> None:
    twice = f"{_SHUTDOWN} uart=a:transfers=1,failures=0,overruns=0 uart=a:transfers=2,failures=0,overruns=0"
    with pytest.raises(ValueError, match="twice"):
        twin_process.parse_shutdown_line(twice)


def test_the_machine_reset_line_names_its_kind_and_counts() -> None:
    log = f"{_PREFIX} machine reset: kind=bootloader reset_count=0 bootloader_count=1\n{_SHUTDOWN}\n"
    assert twin_process.parse_machine_reset_line(log) == twin_process.ResetLine("bootloader", 0, 1)
    assert twin_process.parse_machine_reset_line(_SHUTDOWN) is None


def test_the_shared_exit_codes_are_the_runners_own() -> None:
    source = (Path(__file__).resolve().parent.parent / "digital_twin" / "run_generic_integration.py").read_text(encoding="utf-8")
    for name in ("RESET", "BOOTLOADER", "POWER_LOSS"):
        found = re.search(rf"^_EXIT_SIMULATED_{name} = (\d+)$", source, re.MULTILINE)
        assert found is not None, f"the runner no longer defines _EXIT_SIMULATED_{name}"
        assert getattr(twin_process, f"EXIT_SIMULATED_{name}") == int(found.group(1))


def test_a_signal_death_is_named_as_a_crash_and_never_as_a_failed_check() -> None:
    assert twin_process.exit_reason(-11) == "the interpreter was killed by signal 11 (SIGSEGV) - a crash, not a failed check"
    assert "signal 9 (SIGKILL)" in twin_process.exit_reason(-9)  # a SIGKILL nobody here sent is a crash too


def test_the_callers_own_kill_and_timeout_are_named_as_theirs() -> None:
    assert twin_process.exit_reason(-9, killed=True) == "killed by the caller after it ignored SIGINT"
    assert twin_process.exit_reason(twin_process.EXIT_SUITE_TIMEOUT) == "no exit before the caller's deadline"
    assert twin_process.exit_reason(twin_process.EXIT_SIMULATED_RESET) == "a simulated reset"
    assert twin_process.exit_reason(1) == "exit code 1"


_SIGINT_CHILD = "import signal, sys, time; signal.pthread_sigmask(signal.SIG_BLOCK if sys.argv[1] == 'block' else signal.SIG_UNBLOCK, {signal.SIGINT}); print('ready', flush=True); time.sleep(60)"


@pytest.mark.parametrize(("mode", "expected"), [("block", r"pending, blocked in (\d+) of \1 threads, caught"), ("unblock", r"blocked in 0 of \d+ threads, caught")])
def test_the_ignored_sigint_diagnostic_names_where_the_kernel_holds_sigint(mode: str, expected: str) -> None:
    # A twin that ignores SIGINT is described before the kill: a signal the kernel still holds (blocked, pending) must read
    # apart from one it delivered to the handler, so the next such run says which half failed.
    child = subprocess.Popen([sys.executable, "-c", _SIGINT_CHILD, mode], stdout=subprocess.PIPE, text=True)
    try:
        assert child.stdout is not None and child.stdout.readline() == "ready\n"
        if mode == "block":
            child.send_signal(signal.SIGINT)
        fields = twin_process._proc_diagnostic_fields(child.pid)
        assert re.fullmatch(expected, fields.get("SIGINT", "")), fields
        assert {"SigPnd", "ShdPnd", "SigBlk", "SigIgn", "SigCgt", "Threads"} <= fields.keys(), fields
    finally:
        child.kill()
        child.wait(timeout=5)


# A twin that ignores its first SIGINT, as each outcome of the second one leaves it: the runtime's own exit 1 while the
# first is still pending, an interrupt absorbed and then honoured, and a SIGINT never handled at all.
_SECOND_SIGINT_CHILD = (
    "import os, signal, sys, time\n"
    "mode = sys.argv[1]\n"
    "seen = []\n"
    "def on_sigint(_n, _f):\n"
    "    seen.append(1)\n"
    "    if len(seen) == 2:\n"
    "        os._exit(1 if mode == 'pending' else 0)\n"
    "    print('handled', flush=True)\n"
    "signal.signal(signal.SIGINT, signal.SIG_IGN if mode == 'ignored' else on_sigint)\n"
    "print('ready', flush=True)\n"
    "time.sleep(60)\n"
)


class _FirstWaitExpires(subprocess.Popen[str]):
    # shutdown()'s first wait expires once the child has handled that SIGINT, at once when it ignores it: no timeout's
    # wall time, and the second SIGINT never merges with an unhandled first. Every later wait is the real one.
    handled_marker: "str | None" = None
    log_path = Path("/nonexistent")
    waited = False

    def wait(self, timeout: "float | None" = None) -> int:
        if self.waited:
            return super().wait(timeout)
        self.waited = True
        deadline = time.monotonic() + 10
        while self.handled_marker is not None and self.handled_marker not in self.log_path.read_text(encoding="utf-8") and time.monotonic() < deadline:
            time.sleep(0.01)
        raise subprocess.TimeoutExpired(self.args, timeout or 0.0)


@pytest.mark.parametrize(
    ("mode", "outcome"),
    [("pending", "exit 1 at once, nothing printed: the first was never consumed"), ("absorbed", "a clean exit: the first was raised and absorbed"), ("ignored", "still running: neither SIGINT was acted on")],
)
def test_a_twin_that_ignores_its_sigint_gets_a_second_one_whose_outcome_is_recorded(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, mode: str, outcome: str) -> None:
    # The verdict stays the first SIGINT's however the second ends the twin: the caller's kill, with its code. The second
    # wait binds only for the child that never exits.
    monkeypatch.setattr(twin_process, "_KBD_TRACEBACK_WAIT_S", 0.0)
    monkeypatch.setattr(twin_process, "_SECOND_SIGINT_WAIT_S", 0.05 if mode == "ignored" else 5.0)
    log_path = tmp_path / "twin.log"
    log_file = log_path.open("w", encoding="utf-8")
    proc = _FirstWaitExpires([sys.executable, "-I", "-S", "-c", _SECOND_SIGINT_CHILD, mode], stdin=subprocess.PIPE, stdout=log_file, stderr=subprocess.STDOUT, text=True)
    proc.log_path, proc.handled_marker = log_path, None if mode == "ignored" else "handled"
    run = twin_process.TwinRun(proc=proc, log_path=log_path, log_file=log_file, device="fixture-device", state_dir=tmp_path)
    deadline = time.monotonic() + 10
    while "ready" not in log_path.read_text(encoding="utf-8") and time.monotonic() < deadline:
        time.sleep(0.01)
    code = twin_process.shutdown(run, "fixture twin", timeout_s=0.5)
    printed = capsys.readouterr().out
    assert f"DIAG: fixture twin: a second SIGINT: {outcome}" in printed, printed
    assert (code, run.killed) == (-signal.SIGKILL, True)
    assert twin_process.exit_reason(code, killed=run.killed) == "killed by the caller after it ignored SIGINT"


def test_an_empty_log_gives_no_memory_verdict(ci_suite: ModuleType, tmp_path: Path) -> None:
    failures = _memory_error_verdict(ci_suite, tmp_path, "")
    assert len(failures) == 1 and "empty" in failures[0], failures


# ---------------------------------------------------------------------------
# The suite's own verdicts over the shared helpers: a signal death, a strict history read, a reading with no value.
# ---------------------------------------------------------------------------


def _memory_error_verdict(ci_suite: ModuleType, tmp_path: Path, log_text: str) -> "list[str]":
    # Runs the check over one captured run log and returns whatever failures it recorded.
    log = tmp_path / "run.log"
    log.write_text(log_text, encoding="utf-8")
    saved = list(ci_suite._FAILURES)  # module-level and session-shared: never left mutated
    ci_suite._FAILURES.clear()
    try:
        ci_suite._check_no_memory_error_in_log(log, "Run 1")
        return list(ci_suite._FAILURES)
    finally:
        ci_suite._FAILURES[:] = saved


def _run_stub(tmp_path: Path, *, killed: bool) -> object:
    # A TwinRun whose log holds two lines; only the fields _check_exit() reads.
    log = tmp_path / "twin.log"
    log.write_text("booting\nSegmentation fault\n", encoding="utf-8")
    return twin_process.TwinRun(proc=None, log_path=log, log_file=log.open(encoding="utf-8"), device="fixture-device", state_dir=tmp_path, killed=killed)  # type: ignore[arg-type]


def test_a_signal_death_the_suite_did_not_cause_fails_as_a_crash_with_the_log_tail(ci_suite: ModuleType, tmp_path: Path) -> None:
    failures = _failures_of(ci_suite, lambda: ci_suite._check_exit(_run_stub(tmp_path, killed=False), -11, "Run 5c-b"))
    assert len(failures) == 1, failures
    assert "killed by signal 11 (SIGSEGV) - a crash, not a failed check" in failures[0] and "Segmentation fault" in failures[0]


@pytest.mark.parametrize("ec", [-9, -256])
def test_the_suites_own_kill_or_timeout_is_left_to_the_callers_check(ci_suite: ModuleType, tmp_path: Path, ec: int) -> None:
    assert _failures_of(ci_suite, lambda: ci_suite._check_exit(_run_stub(tmp_path, killed=True), ec, "Run 10")) == []


def test_a_clean_or_reset_exit_is_no_crash(ci_suite: ModuleType, tmp_path: Path) -> None:
    for ec in (0, 1, 3, 4):
        assert _failures_of(ci_suite, functools.partial(ci_suite._check_exit, _run_stub(tmp_path, killed=False), ec, "Run 1")) == []


def test_an_all_null_measurement_block_is_no_reading(ci_suite: ModuleType) -> None:
    # The block a driver publishes before its first good read: truthy as a dict, empty as a reading.
    assert not ci_suite._real_reading({"TS": None, "Temp": None, "Pres": None})
    assert not ci_suite._real_reading({"TS": 1791954984})
    assert not ci_suite._real_reading(None)
    assert ci_suite._real_reading({"TS": None, "Temp": 21.5})


def test_the_strict_history_reader_raises_on_an_entry_without_one(ci_suite: ModuleType) -> None:
    assert ci_suite._error_codes(_entry((11, "E"), (14, "W"))) == [("E", 11), ("W", 14)]
    with pytest.raises(KeyError):
        ci_suite._error_codes({"counter": 3})


def _stub_status(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch, entries: "dict[str, dict[str, object]]") -> "list[str]":
    # Every run helper stubbed over one /status answer; returns the failures the run recorded.
    body = {"errcount": entries, "networking": {"NTPSynced": True}, "system": {"UTCTime": None, "LocalTime": None}}
    monkeypatch.setattr(ci_suite, "_http", lambda *_a, **_k: (200, body))
    monkeypatch.setattr(ci_suite, "_spawn", lambda *_a: object())
    monkeypatch.setattr(ci_suite, "_wait_until_serving", lambda _proc: None)
    monkeypatch.setattr(ci_suite, "_shutdown", lambda _proc, _label: 0)
    monkeypatch.setattr(ci_suite.time, "sleep", lambda _s: None)
    for wait in ("_NTP_UNREACHABLE_WATCH_S", "_ERROR_COUNT_WAIT_S", "_NTP_FIRST_SYNC_WAIT_S"):
        monkeypatch.setattr(ci_suite, wait, 0.0)
    monkeypatch.setattr(ci_suite, "_FAILURES", [])
    return ci_suite._FAILURES  # type: ignore[no-any-return]


@pytest.fixture
def http_stub(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> "Callable[[int, object], None]":
    def install(status: int, body: object) -> None:
        monkeypatch.setattr(ci_suite, "_http", lambda *_a, **_k: (status, body))
    return install


def test_run_9_fails_closed_on_a_system_entry_without_a_counter(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    # Two missing counters once compared equal (0 == 0) and passed "no task was restarted".
    failures = _stub_status(ci_suite, monkeypatch, {"SYSTEM": {"history": []}, "NTP": {"counter": 1, "history": [{"type": "E", "num": 72}]}})
    ci_suite._run_9_ntp_unreachable(_ctx(ci_suite, []))
    assert any("no task ended and was restarted" in f for f in failures), failures


@pytest.mark.parametrize(("failed", "bound"), [(3, 90.0), (2, 0.0)])
def test_run_9_ends_its_watch_once_ntp_failed_every_scheduled_attempt_never_after_a_fixed_wait(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch, failed: int, bound: float) -> None:
    # The watch ends on the failures, then one supervisor pass; at the bound with fewer, the run fails naming the count.
    expected = "NTP_NO_REPLY" if ci_suite._route_leaves_host(ci_suite._NTP_UNREACHABLE_HOST, ci_suite._NTP_PORT) else "NTP_NOT_SENT"
    failures = _stub_status(ci_suite, monkeypatch, {"SYSTEM": {"counter": 0, "history": []}, "NTP": {"counter": failed, "history": [{"type": "E", "num": ci_suite.code("E", expected)}]}})
    slept: list[float] = []
    monkeypatch.setattr(ci_suite.time, "sleep", slept.append)
    monkeypatch.setattr(ci_suite, "_NTP_UNREACHABLE_WATCH_S", bound)
    ci_suite._run_9_ntp_unreachable(_ctx(ci_suite, []))
    assert sum(slept) < ci_suite._NTP_UNREACHABLE_WATCH_S or bound == 0.0, slept
    assert 90.0 not in slept, slept
    counted = [f for f in failures if "NTP failed" in f]
    assert counted == [] if failed >= ci_suite._NTP_UNREACHABLE_FAILURES else (len(counted) == 1 and f"failed {failed} time(s)" in counted[0]), failures


def test_run_8_fails_closed_on_a_wifi_entry_without_a_counter(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    # A missing counter once read as 0, inside the all-or-nothing set (0, 6).
    failures = _stub_status(ci_suite, monkeypatch, {"WIFI": {"history": []}})
    ci_suite._run_8_wifi_persistence_and_configure_ntp(_ctx(ci_suite, []))
    assert any("the counter came back with it" in f for f in failures), failures


@pytest.mark.parametrize("engaged", [True, False])
def test_run_10_ends_each_hang_run_on_the_runners_line_and_otherwise_waits_out_its_duration(ci_suite: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, engaged: bool) -> None:
    # A hang run's feed gap is past the timeout on purpose, so its log skips the near-reset check.
    ended: list[str] = []
    line = _SHUTDOWN.replace("would_have_triggered_count=0", "would_have_triggered_count=1").replace("largest_feed_gap_ms=812", "largest_feed_gap_ms=12010")

    def spawn(_ctx: object, _args: object, log_path: Path) -> object:
        log_path.write_text(("WATCHDOG_WOULD_TRIGGER count=1\n" if engaged else "") + line + "\n", encoding="utf-8")
        return twin_process.TwinRun(proc=SimpleNamespace(poll=lambda: None), log_path=log_path, log_file=log_path.open(encoding="utf-8"), device="fixture-device", state_dir=tmp_path)  # type: ignore[arg-type]

    def interrupted(_run: object, _label: object, _timeout_s: object) -> int:
        ended.append("SIGINT")
        return 0

    def waited_out(_run: object, _timeout_s: object) -> int:
        ended.append("duration")
        return 0

    monkeypatch.setattr(ci_suite, "_archive_state", lambda _ctx, _label: None)
    monkeypatch.setattr(ci_suite, "_spawn", spawn)
    monkeypatch.setattr(ci_suite, "shutdown", interrupted)
    monkeypatch.setattr(ci_suite, "wait_exit", waited_out)
    monkeypatch.setattr(ci_suite, "_HANG_RUN_EXIT_WAIT_S", 0.02)
    monkeypatch.setattr(ci_suite, "_VERBOSE_POLL_S", 0.01)
    ctx = _ctx(ci_suite, ["sgp40"], tmp_path)
    failures = _failures_of(ci_suite, lambda: ci_suite._run_10_watchdog_hang_backstop(ctx))
    assert failures == [], failures
    assert ended == ["SIGINT" if engaged else "duration"], ended

