"""Deterministic tests for run_dev_integration.py's own parse_args()/_soak()/main() - each an
independently duplicated copy rather than a shared import, so a bug in this one would not be caught
by test_digital_twin_run_wozi_integration.py. Shared _http_client.py parsing is covered there."""

import asyncio
import sys

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")

sys.path.insert(0, "ext")  # run_dev_integration.py transitively imports sensortask_dev ->
# asy_webserver_service -> microdot - same convention test_sensortask_dev.py's own comment uses.
sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

from run_dev_integration import RunConfig, _soak, main, parse_args

import sensortask_dev


def run_timed(coro: "Coroutine[Any, Any, T]", timeout_s: float = 5.0) -> "T":
    return asyncio.run(asyncio.wait_for(coro, timeout_s))


# ---------------------------------------------------------------------------
# _soak() resilience: a connection closed with zero bytes written (the max_connections reject path)
# must be recorded as one soak failure, never raise out of _soak() and end the diagnostic run. This
# is the dev copy of _soak(), so the wozi-side test passing implies nothing about it.
# ---------------------------------------------------------------------------


async def _reset_immediately_server(_reader: "asyncio.StreamReader", writer: "asyncio.StreamWriter") -> None:
    writer.close()
    await writer.wait_closed()


def test_soak_records_a_connection_reset_as_a_failure_instead_of_crashing() -> None:
    async def scenario() -> None:
        server = await asyncio.start_server(_reset_immediately_server, "127.0.0.1", 18198)
        try:
            failures = await _soak("127.0.0.1", 18198, cycles=1)  # must not raise
        finally:
            server.close()
            await server.wait_closed()
        assert failures
        assert any("warmup" in f for f in failures)
        assert any("cycle 0" in f for f in failures)

    run_timed(scenario(), timeout_s=15.0)


# ---------------------------------------------------------------------------
# main() - one real, short, bounded end-to-end smoke test, deliberately exactly one (the wozi file's
# own comment has the full reasoning). The only test exercising main()'s `chips` dict, dev's own
# address wiring: a wrong address there is caught nowhere else in this suite.
# ---------------------------------------------------------------------------


def test_main_runs_a_tiny_bounded_soak_with_an_injected_fault_and_returns_a_clean_summary() -> None:
    config = RunConfig(
        host="127.0.0.1",
        port=19197,
        fram_state_path=None,
        scd30_state_path=None,
        soak=True,
        soak_cycles=2,
        duration=0.0,
        faults=[("sgp40", "writeto", 3)],
    )
    # 120s, not the wozi sibling's 60s: this run's wall clock is set by where GC collections land,
    # measured at 44.1-61.5s across variants of a module it never executes a changed line of (Part
    # E.7). A liveness backstop belongs above the whole observed range, not near it.
    summary = run_timed(main(config), timeout_s=120.0)
    non_memory_failures = [f for f in summary["failures"] if "gc.mem_free()" not in f]
    assert non_memory_failures == []
    assert summary["would_have_triggered_count"] == 0

    # The bench tier's claim in the twin tier, on this same run: building the dev graph twice
    # in one file exhausts the Unix port's 8MB test heap. The jumper and its exerciser ran through
    # the whole soak, so an idle-link reading cannot pass this.
    assert sensortask_dev.uart_transfers > 0, "the link never completed a transfer during the soak"
    # Counted, never timed: a transfer count is a property of the code, unlike this run's wall
    # clock (Part E.7). Every attempt must succeed - the jumper is attached and nothing else
    # contends for those two peripherals.
    assert sensortask_dev.uart_failures == 0, f"{sensortask_dev.uart_failures} link failures under concurrent HTTP load"



# ---------------------------------------------------------------------------
# parse_args() - the dev copy of the flag parsing the wozi test file covers for its own. Full parity
# coverage rather than a subset: catching a copy-paste divergence in either file's defaults is
# exactly what two separate, non-shared test files are for.
# ---------------------------------------------------------------------------


def test_parse_args_defaults() -> None:
    config = parse_args([])
    assert config == RunConfig(
        host="localhost",
        port=8080,
        fram_state_path="digital_twin/fram_state.json",
        scd30_state_path="digital_twin/scd30_state.json",
        seed=None,
        faults=[],
        wifi_outcomes=[],
        soak=False,
        soak_cycles=20,
        duration=None,
    )


def test_parse_args_host_and_port() -> None:
    config = parse_args(["--host", "0.0.0.0", "--port", "9091"])
    assert config.host == "0.0.0.0"
    assert config.port == 9091


def test_parse_args_empty_fram_state_path_means_in_memory_only() -> None:
    config = parse_args(["--fram-state-path", ""])
    assert config.fram_state_path is None


def test_parse_args_custom_fram_state_path() -> None:
    config = parse_args(["--fram-state-path", "scratch/fram_dev.json"])
    assert config.fram_state_path == "scratch/fram_dev.json"


def test_parse_args_empty_scd30_state_path_means_in_memory_only() -> None:
    config = parse_args(["--scd30-state-path", ""])
    assert config.scd30_state_path is None


def test_parse_args_custom_scd30_state_path() -> None:
    config = parse_args(["--scd30-state-path", "scratch/scd30_dev.json"])
    assert config.scd30_state_path == "scratch/scd30_dev.json"


def test_parse_args_seed_and_soak_cycles_and_duration() -> None:
    config = parse_args(["--seed", "7", "--soak-cycles", "5", "--duration", "0"])
    assert config.seed == 7
    assert config.soak_cycles == 5
    assert config.duration == 0.0


def test_parse_args_duration_omitted_stays_none() -> None:
    assert parse_args([]).duration is None


def test_parse_args_soak_flag_enables_soak_with_the_default_cycle_count() -> None:
    config = parse_args(["--soak"])
    assert config.soak is True
    assert config.soak_cycles == 20


def test_parse_args_soak_cycles_implies_soak() -> None:
    config = parse_args(["--soak-cycles", "5"])
    assert config.soak is True
    assert config.soak_cycles == 5


def test_parse_args_accumulates_repeated_fault_flags() -> None:
    config = parse_args(["--fault", "sgp40:writeto", "--fault", "fram:readinto:3"])
    assert config.faults == [("sgp40", "writeto", 1), ("fram", "readinto", 3)]


def test_parse_args_accumulates_repeated_hang_flags() -> None:
    # Not covered by the wozi-side test file (which never exercises --hang at all) - this file's
    # own parse_args() forwards to the same launch.py parse_hang_spec(), but the accumulation
    # (`hangs.append(...)`) is this copy's own code, same class of risk as --fault above.
    config = parse_args(["--hang", "fram:write:0.5", "--hang", "scd30:readfrom_into:1.0:2"])
    assert config.hangs == [("fram", "write", 0.5, 1), ("scd30", "readfrom_into", 1.0, 2)]


def test_parse_args_accumulates_repeated_wifi_outcome_flags() -> None:
    import network

    config = parse_args(["--wifi-outcome", "success", "--wifi-outcome", "no_ap"])
    assert config.wifi_outcomes == [network.STAT_GOT_IP, network.STAT_NO_AP_FOUND]


def test_parse_args_rejects_an_unrecognized_flag() -> None:
    try:
        parse_args(["--bogus"])
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_parse_args_missing_value_for_a_flag_raises() -> None:
    # _pop_value()'s own guard - this file's own copy, not exercised by the wozi-side test file.
    try:
        parse_args(["--host"])
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
