"""Tests scripts/_digital_twin_ci_suite.py's own pure error-log helpers - _error_type_count()'s
type_char selection (Run 8's "W" case) and _bus_fault_drivers()'s filtering - without a live twin
subprocess/HTTP server, the same way test_digital_twin_ci_suite_soak.py does for Run 11's."""

from pathlib import Path
from types import ModuleType

import pytest
from _script_loader import load_script_module


@pytest.fixture(scope="session")
def ci_suite(repo_root: Path) -> ModuleType:
    return load_script_module(repo_root / "scripts" / "_digital_twin_ci_suite.py", "_digital_twin_ci_suite")


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
    assert ci_suite._bus_fault_drivers(_ctx(ci_suite, {"scd30", "isl29125", "neopixel"})) == ["scd30"]


def test_every_faultable_driver_has_both_an_op_and_an_errcount_name(ci_suite: ModuleType) -> None:
    # Run 3 looks a driver up in _BUS_FAULT_OPS and Run 4 in _DRIVER_ERRCOUNT_NAME; the two tables
    # are hand-kept separately, and a driver present in one but not the other raises mid-run.
    assert set(ci_suite._BUS_FAULT_OPS) == set(ci_suite._DRIVER_ERRCOUNT_NAME)
    assert set(ci_suite._DRIVER_ERRCOUNT_NAME) >= ci_suite._NO_PERSIST_WHEN_FRAM_FAULTED
    assert set(ci_suite._DRIVER_ERRCOUNT_NAME) >= ci_suite._MEASUREMENT_DRIVERS
