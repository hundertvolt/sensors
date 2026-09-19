"""Tests scripts/_digital_twin_ci_suite.py's own pure error-log helpers - _error_type_count()'s
type_char selection (Run 8's "W" case) and _bus_fault_drivers()'s filtering - without a live twin
subprocess/HTTP server, the same way test_digital_twin_ci_suite_soak.py does for Run 11's."""

from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import pytest
import tomllib
from _devices import DEVICE_NAMES, device_toml

if TYPE_CHECKING:
    from collections.abc import Callable


def _entry(*history: tuple[int, str], counter: int | None = None) -> dict[str, object]:
    """One GET /status errcount entry, in asy_webserver_service.py's own published shape."""
    items = [{"num": num, "type": kind} for num, kind in history]
    return {"counter": len(items) if counter is None else counter, "history": items}


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
    # print_log.py pre-fills the history deque with its own "nothing recorded" sentinel, published
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
# _bus_fault_drivers() - the per-device fault matrix, derived from that device's own wiring plan.
# ---------------------------------------------------------------------------


def _ctx(ci_suite: ModuleType, drivers: set[str]) -> object:
    return ci_suite.RunContext(
        micropython_bin="/nonexistent",
        logs_dir=Path("/nonexistent"),
        device="test",
        module="sensortask_test",
        wiring_plan_path=Path("/nonexistent"),
        drivers=frozenset(drivers),
        gc_threshold=-1,
    )


def test_bus_fault_drivers_is_sorted_and_deterministic(ci_suite: ModuleType) -> None:
    assert ci_suite._bus_fault_drivers(_ctx(ci_suite, {"sgp40", "fram", "scd30"})) == ["fram", "scd30", "sgp40"]


def test_bus_fault_drivers_skips_a_driver_the_suite_cannot_fault(ci_suite: ModuleType) -> None:
    # The filter's whole purpose: a future bus-attached driver with no _BUS_FAULT_OPS entry is
    # skipped here rather than KeyError-ing partway through Run 3/4.
    #
    # The stand-in is a name no device will ever declare. This once used "isl29125", accurate
    # when written, which silently became the record of a REAL gap once that driver shipped with
    # its own fault-capable fake - and closing the gap then looked like a regression.
    assert ci_suite._bus_fault_drivers(_ctx(ci_suite, {"scd30", "not_a_real_driver", "neopixel"})) == ["scd30"]


def test_every_faultable_driver_has_both_an_op_and_an_errcount_name(ci_suite: ModuleType) -> None:
    # Run 3 looks a driver up in _BUS_FAULT_OPS and Run 4 in _DRIVER_ERRCOUNT_NAME; the two tables
    # are hand-kept separately, and a driver present in one but not the other raises mid-run.
    assert set(ci_suite._BUS_FAULT_OPS) == set(ci_suite._DRIVER_ERRCOUNT_NAME)
    assert set(ci_suite._DRIVER_ERRCOUNT_NAME) >= ci_suite._NO_PERSIST_WHEN_FRAM_FAULTED
    assert set(ci_suite._DRIVER_ERRCOUNT_NAME) >= ci_suite._MEASUREMENT_DRIVERS


def test_run_5c_faults_every_bus_attached_driver_but_never_the_store_itself(ci_suite: ModuleType) -> None:
    # Run 5c's premise is a HEALTHY chip, so its sweep set is _bus_fault_drivers() minus "fram" -
    # faulting the store is the one thing that voids it, and is what makes Run 3/4's own sweep a
    # weaker claim. Checked as an identity, not a literal list, so a new bus driver joins both.
    ctx = _ctx(ci_suite, {"scd30", "sgp40", "bmp3xx", "isl29125", "fram"})
    assert ci_suite._healthy_store_fault_drivers(ctx) == ["bmp3xx", "isl29125", "scd30", "sgp40"]
    assert set(ci_suite._healthy_store_fault_drivers(ctx)) == set(ci_suite._bus_fault_drivers(ctx)) - {"fram"}


def test_the_only_error_source_exempt_from_run_5cs_loss_sweep_is_the_store_itself(ci_suite: ModuleType) -> None:
    # Everything else in errcount is FRAM-backed and must come back across a commanded reboot.
    # AsyFramManager cannot persist its own history through the store that failed, the one
    # legitimate exemption, which _sensortask_scenarios.py pins from the real object graph too.
    assert sorted(ci_suite._IN_MEMORY_ONLY_ERROR_SOURCES) == ["FRAM"]
    assert set(ci_suite._DRIVER_ERRCOUNT_NAME.values()) >= ci_suite._IN_MEMORY_ONLY_ERROR_SOURCES


def test_every_i2c_or_spi_attached_driver_a_real_device_declares_is_faultable(ci_suite: ModuleType) -> None:
    # The three tables above are only checked against EACH OTHER, which let the ISL29125 be
    # absent from all of them and silently skipped from the day it shipped. This is the outward
    # check: the real device set decides who belongs.

    # Scoped to i2c/spi, the buses the twin's chip fakes can fault. uart_link's peer is a second
    # UART_Comm rather than a faultable fake, so it is out by mechanism, not by an allowlist.
    attached = set()
    for device in DEVICE_NAMES:
        doc = tomllib.loads(device_toml(device).read_text())
        attached |= {inst["driver"] for inst in doc.get("instance", []) if str(inst.get("bus", "")).startswith(("i2c", "spi"))}
    missing = sorted(attached - set(ci_suite._BUS_FAULT_OPS))
    assert not missing, f"bus-attached driver(s) {missing} are declared by a real device but absent from _BUS_FAULT_OPS, so Run 3/4 skip them without saying so"


# ---------------------------------------------------------------------------
# _errcount() / _errcount_required(), the tolerant/strict split that guards the vacuous-pass
# class: {} for an unreadable /status reads as counter 0 with an empty history, so an assertion
# expecting 0 would hold against a server that answered nothing - as Runs 4, 5c and 8 all did.
# ---------------------------------------------------------------------------


@pytest.fixture
def _http_stub(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> "Callable[[int, object], None]":
    def install(status: int, body: object) -> None:
        monkeypatch.setattr(ci_suite, "_http", lambda *_a, **_k: (status, body))
    return install


_READABLE = {"errcount": {"SGP40": {"counter": 0, "history": [{"num": 0, "type": "N"}]}}}


def test_errcount_is_tolerant_so_the_polling_helpers_can_retry(ci_suite: ModuleType, _http_stub: "Callable[[int, object], None]") -> None:
    # The tolerance is deliberate and load-bearing: _wait_for_errcount_above()/
    # _wait_for_error_type_count() call this in a loop during boot, where a transient non-200 must
    # retry rather than abort the whole run.
    _http_stub(503, None)
    assert ci_suite._errcount("SGP40") == {}


def test_errcount_is_also_tolerant_of_a_200_with_an_unusable_body(ci_suite: ModuleType, _http_stub: "Callable[[int, object], None]") -> None:
    _http_stub(200, "not-a-dict")
    assert ci_suite._errcount("SGP40") == {}
    _http_stub(200, {"errcount": {"SGP40": "not-a-dict-either"}})
    assert ci_suite._errcount("SGP40") == {}


def test_errcount_required_raises_instead_of_answering_an_empty_entry(ci_suite: ModuleType, _http_stub: "Callable[[int, object], None]") -> None:
    # THE regression test for the vacuous-pass class. Before the split, Run 4's `counter == 0`,
    # Run 5c's `_error_type_count(...) == 0` and Run 8's `restored in (0, N)` all held here.
    _http_stub(503, None)
    with pytest.raises(RuntimeError, match="readable errcount entry"):
        ci_suite._errcount_required("SGP40")


def test_errcount_required_raises_for_a_source_missing_from_a_readable_status(ci_suite: ModuleType, _http_stub: "Callable[[int, object], None]") -> None:
    # Every registered error source appears in errcount whether or not it ever logged, so a missing
    # entry is a real failure - never "this module simply has no errors".
    _http_stub(200, {"errcount": {"SCD30": {"counter": 0, "history": []}}})
    with pytest.raises(RuntimeError, match="SGP40"):
        ci_suite._errcount_required("SGP40")


def test_errcount_required_returns_the_entry_when_status_is_genuinely_readable(ci_suite: ModuleType, _http_stub: "Callable[[int, object], None]") -> None:
    _http_stub(200, _READABLE)
    assert ci_suite._errcount_required("SGP40") == {"counter": 0, "history": [{"num": 0, "type": "N"}]}


def test_errcount_all_raises_rather_than_sweeping_an_unreadable_status(ci_suite: ModuleType, _http_stub: "Callable[[int, object], None]") -> None:
    # Run 5c's device-wide sweep iterates whatever this returns, so a tolerant {} here would turn
    # "the server answered nothing" into "no source lost anything" - the same vacuous pass the
    # _errcount()/_errcount_required() split exists to prevent, one level up.
    _http_stub(503, None)
    with pytest.raises(RuntimeError, match="readable body"):
        ci_suite._errcount_all()
    _http_stub(200, "not-a-dict")
    with pytest.raises(RuntimeError, match="readable body"):
        ci_suite._errcount_all()


def test_errcount_all_raises_on_a_200_carrying_no_usable_table(ci_suite: ModuleType, _http_stub: "Callable[[int, object], None]") -> None:
    bodies: list[object] = [{}, {"errcount": {}}, {"errcount": "not-a-dict"}]
    for body in bodies:
        _http_stub(200, body)
        with pytest.raises(RuntimeError, match="no usable errcount table"):
            ci_suite._errcount_all()


def test_errcount_all_drops_only_the_rows_that_are_not_entries(ci_suite: ModuleType, _http_stub: "Callable[[int, object], None]") -> None:
    _http_stub(200, {"errcount": {"SGP40": {"counter": 1, "history": []}, "JUNK": "not-a-dict"}})
    assert ci_suite._errcount_all() == {"SGP40": {"counter": 1, "history": []}}


def test_error_counts_settle_only_once_consecutive_reads_agree(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    # Snapshotting mid-fault is the failure this guards: the reboot would then be compared against
    # entries that landed AFTER the snapshot, and a run that lost nothing would read as a loss.
    reads = iter([1, 2, 3, 3, 3])
    monkeypatch.setattr(ci_suite, "_errcount_all", lambda: {"SGP40": _entry(*[(10, "E")] * next(reads))})
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
# _put_reset_errors_timed() - the elapsed-time budget (BACKLOG item 24). A timeout only catches a
# call that never finished; without this the suite was blind to the whole band between "normal" and
# the server's own cap.
# ---------------------------------------------------------------------------


def _drive_timed_reset(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch, elapsed_s: float, status: int = 200) -> "tuple[int, list[str], list[str]]":
    """Runs _put_reset_errors_timed() with a scripted elapsed time; returns (status, oks, failures)."""
    clock = iter([1000.0, 1000.0 + elapsed_s])
    monkeypatch.setattr(ci_suite.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(ci_suite, "_http", lambda *_a, **_k: (status, None))
    oks: list[str] = []
    monkeypatch.setattr(ci_suite, "_check", lambda *, condition, msg: (oks if condition else failures).append(msg))
    failures: list[str] = []
    return ci_suite._put_reset_errors_timed("Run T"), oks, failures


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
    assert not oks
    assert len(failures) == 1 and "13.00s" in failures[0]


def test_the_budget_boundary_is_exclusive(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    # Exactly at the budget is a failure, not a pass - pinned so a later `<=` refactor is caught.
    _status, oks, failures = _drive_timed_reset(ci_suite, monkeypatch, elapsed_s=ci_suite._RESET_ERRORS_BUDGET_S)
    assert not oks
    assert len(failures) == 1


def test_the_budget_sits_between_the_observed_worst_case_and_the_servers_own_cap(ci_suite: ModuleType) -> None:
    # Sized from measurement, not taste: the twin's worst observed dev sweep is 8.91s and real
    # hardware is 6.32s idle / 11.58s under three concurrent readers. A budget at or below the
    # worst observed value flakes; at or above the cap it can never fire before the server aborts.
    assert 8.91 < ci_suite._RESET_ERRORS_BUDGET_S < ci_suite._SERVER_OUTER_CAP_S
    assert ci_suite._RESET_ERRORS_BUDGET_S < ci_suite._RESET_ERRORS_TIMEOUT_S, "the budget must trip before the client timeout, or it is unreachable"


def test_every_reset_errors_call_in_the_suite_goes_through_the_timed_helper(ci_suite: ModuleType) -> None:
    # A budget helper that some call site bypasses measures nothing on that path. Checked against the
    # real source: a second raw _http("PUT", "/status", {"ResetErrors": ...}) is exactly how the gap
    # would reappear, and it would still pass every behavioural test above.
    source = Path(ci_suite.__file__ or "").read_text()
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
