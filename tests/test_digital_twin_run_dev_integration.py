"""Deterministic unit tests for digital_twin/run_dev_integration.py's own parse_args()/_soak()/
main() - the dev-variant sibling of test_digital_twin_run_wozi_integration.py. Needed because this
file's own module docstring says it "mirrors run_wozi_integration.py exactly" but its parse_args(),
_soak(), _apply_fault()/_apply_hang(), and main() are each an independently-duplicated copy, not a
shared import from launch.py - a bug introduced only in this copy (wrong default, wrong chip
address in main()'s own `chips` dict, a soak-loop regression) would not be caught by the wozi test
file, which only imports run_wozi_integration. _http_client.py's own parsing is shared and already
fully covered there, so it isn't repeated here."""

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


def run_timed(coro: "Coroutine[Any, Any, T]", timeout_s: float = 5.0) -> "T":
    return asyncio.run(asyncio.wait_for(coro, timeout_s))


# ---------------------------------------------------------------------------
# _soak() resilience - same regression this file's own module docstring and
# test_digital_twin_run_wozi_integration.py's own identical test document: a connection closed with
# zero bytes written (WebserverService._serve()'s own max_connections reject-when-full path) must
# be recorded as one soak failure, never raise out of _soak() and crash the whole diagnostic run.
# This is this file's own independently-duplicated _soak() copy, not a shared one - not implied by
# the wozi-side test passing.
# ---------------------------------------------------------------------------


async def _reset_immediately_server(reader: "Any", writer: "Any") -> None:
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
# run_dev_integration.main() - one real, short, bounded end-to-end smoke test, same spirit and same
# "deliberately exactly one" reasoning as test_digital_twin_run_wozi_integration.py's own identical
# test (see that file's own comment for the full account of why one, not two). This is the one test
# that actually exercises main()'s own `chips` dict (dev's own i2c0/i2c1/spi0 address wiring, wired
# independently of wozi's) - a wrong address there would raise a KeyError applying the fault below,
# or silently fault the wrong device, either way not caught anywhere else in this suite.
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
    summary = run_timed(main(config), timeout_s=60.0)
    non_memory_failures = [f for f in summary["failures"] if "gc.mem_free()" not in f]
    assert non_memory_failures == []
    assert summary["would_have_triggered_count"] == 0


# ---------------------------------------------------------------------------
# run_dev_integration.parse_args() - this file's own independently-duplicated copy of the same
# flag-parsing logic test_digital_twin_run_wozi_integration.py already covers for
# run_wozi_integration's copy. Full parity coverage, not a subset - a copy-paste divergence in
# either file's own defaults/flags is exactly what two separate, non-shared test files are for.
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
