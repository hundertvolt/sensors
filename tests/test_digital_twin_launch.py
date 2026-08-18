"""Deterministic unit tests for digital_twin/launch.py's parse_args()/parse_fault_spec() (pure,
synchronous - the bulk of this file), plus one short-duration/fixed-seed end-to-end smoke test of
main() itself - same "does the mechanism work at all" spirit as
test_digital_twin_machine.py's own Timer/WDT live-timing tests and
test_digital_twin_network_neopixel.py's own WLAN connect-timing test, not a precise-behavior
assertion.
"""

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

sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

import machine  # noqa: E402
import network  # noqa: E402
from launch import LaunchConfig, main, parse_args, parse_fault_spec  # noqa: E402


def run(coro: "Coroutine[Any, Any, T]") -> "T":
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# parse_fault_spec()
# ---------------------------------------------------------------------------


def test_parse_fault_spec_defaults_times_to_one() -> None:
    assert parse_fault_spec("scd30:writeto") == ("scd30", "writeto", 1)


def test_parse_fault_spec_honors_an_explicit_times() -> None:
    assert parse_fault_spec("sgp40:readfrom_into:3") == ("sgp40", "readfrom_into", 3)


def test_parse_fault_spec_accepts_every_documented_device_and_op() -> None:
    assert parse_fault_spec("scd30:writeto") == ("scd30", "writeto", 1)
    assert parse_fault_spec("scd30:readfrom_into") == ("scd30", "readfrom_into", 1)
    assert parse_fault_spec("sgp40:writeto") == ("sgp40", "writeto", 1)
    assert parse_fault_spec("sgp40:readfrom_into") == ("sgp40", "readfrom_into", 1)
    assert parse_fault_spec("bmp3xx:readfrom_mem") == ("bmp3xx", "readfrom_mem", 1)
    assert parse_fault_spec("bmp3xx:writeto_mem") == ("bmp3xx", "writeto_mem", 1)
    assert parse_fault_spec("fram:write") == ("fram", "write", 1)
    assert parse_fault_spec("fram:readinto") == ("fram", "readinto", 1)
    assert parse_fault_spec("wlan:connect") == ("wlan", "connect", 1)


def test_parse_fault_spec_rejects_an_unrecognized_device() -> None:
    try:
        parse_fault_spec("bogus:writeto")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_parse_fault_spec_rejects_an_op_not_valid_for_the_device() -> None:
    try:
        parse_fault_spec("scd30:readfrom_mem")  # readfrom_mem is a bmp3xx op, not scd30's
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_parse_fault_spec_rejects_a_malformed_shape() -> None:
    for spec in ("scd30", "scd30:writeto:2:extra", ""):
        try:
            parse_fault_spec(spec)
            raise AssertionError(f"expected ValueError for {spec!r}")
        except ValueError:
            pass


def test_parse_fault_spec_rejects_a_non_integer_times() -> None:
    try:
        parse_fault_spec("scd30:writeto:not-a-number")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_parse_fault_spec_rejects_a_times_below_one() -> None:
    try:
        parse_fault_spec("scd30:writeto:0")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_parse_fault_spec_rejects_times_for_wlan() -> None:
    # network.WLAN.raise_on has no repeat-limit concept of its own - see launch.py's own comment.
    try:
        parse_fault_spec("wlan:connect:2")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# parse_args()
# ---------------------------------------------------------------------------


def test_parse_args_with_no_flags_returns_all_defaults() -> None:
    config = parse_args([])
    assert config.seed is None
    assert config.fram_state_path is None
    assert config.scd30_state_path is None
    assert config.faults == []
    assert config.wifi_outcomes == []
    assert config.no_wdt_feed is False
    assert config.duration is None


def test_parse_args_seed_is_parsed_as_int() -> None:
    config = parse_args(["--seed", "42"])
    assert config.seed == 42


def test_parse_args_fram_state_path_is_passed_through() -> None:
    config = parse_args(["--fram-state-path", "tests/_tmp/launch_fram.bin"])
    assert config.fram_state_path == "tests/_tmp/launch_fram.bin"


def test_parse_args_scd30_state_path_is_passed_through() -> None:
    config = parse_args(["--scd30-state-path", "tests/_tmp/launch_scd30.json"])
    assert config.scd30_state_path == "tests/_tmp/launch_scd30.json"


def test_parse_args_no_wdt_feed_is_a_bare_flag() -> None:
    config = parse_args(["--no-wdt-feed"])
    assert config.no_wdt_feed is True


def test_parse_args_duration_is_parsed_as_float() -> None:
    config = parse_args(["--duration", "2.5"])
    assert config.duration == 2.5


def test_parse_args_fault_is_repeatable_and_accumulates_in_order() -> None:
    config = parse_args(["--fault", "scd30:writeto:2", "--fault", "wlan:connect"])
    assert config.faults == [("scd30", "writeto", 2), ("wlan", "connect", 1)]


def test_parse_args_wifi_outcome_is_repeatable_and_resolves_to_real_network_constants() -> None:
    config = parse_args(["--wifi-outcome", "no_ap", "--wifi-outcome", "success"])
    assert config.wifi_outcomes == [network.STAT_NO_AP_FOUND, network.STAT_GOT_IP]


def test_parse_args_rejects_an_unrecognized_wifi_outcome() -> None:
    try:
        parse_args(["--wifi-outcome", "bogus"])
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_parse_args_rejects_an_unrecognized_flag() -> None:
    try:
        parse_args(["--not-a-real-flag"])
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_parse_args_rejects_a_flag_missing_its_value() -> None:
    try:
        parse_args(["--seed"])
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_parse_args_combines_every_flag_together() -> None:
    config = parse_args(
        [
            "--seed",
            "7",
            "--fram-state-path",
            "tests/_tmp/launch_fram.bin",
            "--scd30-state-path",
            "tests/_tmp/launch_scd30.json",
            "--fault",
            "bmp3xx:readfrom_mem:3",
            "--wifi-outcome",
            "connect_fail",
            "--no-wdt-feed",
            "--duration",
            "1.5",
        ]
    )
    assert config.seed == 7
    assert config.fram_state_path == "tests/_tmp/launch_fram.bin"
    assert config.scd30_state_path == "tests/_tmp/launch_scd30.json"
    assert config.faults == [("bmp3xx", "readfrom_mem", 3)]
    assert config.wifi_outcomes == [network.STAT_CONNECT_FAIL]
    assert config.no_wdt_feed is True
    assert config.duration == 1.5


# ---------------------------------------------------------------------------
# main() - one short-duration/fixed-seed end-to-end smoke test.
# ---------------------------------------------------------------------------


def test_main_runs_end_to_end_and_returns_a_summary() -> None:
    machine.Pin.reset_registry()  # isolate from any earlier test file's own Pin(8)/etc. wiring
    config = LaunchConfig(seed=1234, no_wdt_feed=True, duration=0.5)
    summary = run(asyncio.wait_for(main(config), 10))
    assert summary["readings"] >= 1  # at least one real bus-level read happened
    assert summary["wifi_status"] is not None
    assert summary["would_have_triggered_count"] == 0  # only 0.5s, well under the 8000ms WDT timeout


def test_main_with_scripted_faults_and_wifi_outcome_still_completes() -> None:
    # duration must clear both network.py's own _CONNECT_DELAY_S (0.7s), for the scripted outcome
    # to actually settle, and _sensor_loop()'s own 2.0s poll interval at least once past the first
    # iteration - both one-shot faults fire on that very first read (t=0), so a duration that only
    # covers one iteration would leave every sensor faulted/not-yet-ready and no reading produced at
    # all (SCD30 isn't ready that early either - see the dedicated longer-duration test below for
    # its own timer-driven path).
    machine.Pin.reset_registry()
    config = LaunchConfig(
        seed=99,
        no_wdt_feed=True,
        duration=2.5,
        faults=[("sgp40", "writeto", 1), ("bmp3xx", "readfrom_mem", 1)],
        wifi_outcomes=[network.STAT_NO_AP_FOUND],
    )
    summary = run(asyncio.wait_for(main(config), 10))
    assert summary["wifi_status"] == network.STAT_NO_AP_FOUND
    # Both one-shot faults (sgp40/bmp3xx) are isolated to their own read and spent after the first
    # iteration - the second iteration's real readings must still have been produced.
    assert summary["readings"] >= 1


def test_main_a_wlan_fault_is_isolated_and_still_returns_a_summary() -> None:
    # WLAN.active()/connect() at main()'s own startup, and WLAN.status() in its cleanup and in
    # _wifi_watcher()'s own loop, all used to be unguarded - a --fault wlan:... crashed main()
    # outright before it ever reached the WDT-feed/sensor-read loops. Now isolated the same way
    # _sensor_loop() isolates each sensor's own read.
    machine.Pin.reset_registry()
    config = LaunchConfig(seed=7, no_wdt_feed=True, duration=0.5, faults=[("wlan", "connect", 1)])
    summary = run(asyncio.wait_for(main(config), 10))
    assert summary["readings"] >= 1  # sensor loop still ran despite the WLAN fault


def test_main_long_enough_duration_reaches_a_real_wdt_feed_and_scd30s_timer_driven_reading() -> None:
    # _SENSOR_POLL_INTERVAL_S/SCD30's own default measurement_interval_s are both 2.0s - a duration
    # shorter than that (every other main() test here uses <=1.5s) never lets SCD30's internal Timer
    # produce a ready reading at all, so _read_scd30()'s own "ready" branch (as opposed to its
    # not-yet-ready None early-return) never actually runs. no_wdt_feed=False here also exercises a
    # real watchdog.feed() call, unlike every other main() test's no_wdt_feed=True.
    machine.Pin.reset_registry()
    config = LaunchConfig(seed=55, no_wdt_feed=False, duration=4.5)
    summary = run(asyncio.wait_for(main(config), 15))
    assert summary["readings"] >= 5  # several rounds across 4.5s, well past SCD30's 2s cadence
    assert summary["would_have_triggered_count"] == 0  # fed for real, well under the 8000ms timeout


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
