"""Tests for digital_twin/launch.py: the shared --fault/--hang vocabulary and parsers, parse_args(), the shared chip
lookup and fault plumbing (pure, synchronous), and short end-to-end runs of main() over a fixture plan - a
"does it work at all" check, not a precise-behaviour assertion."""

import asyncio
import errno
import sys

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import ParamSpec, TypeVar

    from launch import _Plan

    T = TypeVar("T")
    P = ParamSpec("P")

sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

import launch
import machine
import microtest
import network
from _async_harness import run
from _src_const import src_const
from _twin_common import Injections, StatePaths
from _twin_devices import device_with

microtest.after_each(machine.reset_test_state)
microtest.after_each(network.reset_test_state)

# @tunable l2.launch_short_duration_s = 0.5
_SHORT_DURATION_S = 0.5
# @tunable l2.launch_main_bound_s = 10
_MAIN_BOUND_S = 10
# @tunable l2.launch_fault_duration_s = 2.5
_FAULT_DURATION_S = 2.5
# @tunable l2.launch_long_duration_s = 4.5
_LONG_DURATION_S = 4.5
# @tunable l2.launch_long_main_bound_s = 15
_LONG_MAIN_BOUND_S = 15
# @tunable l2.launch_long_min_readings = 5
_LONG_MIN_READINGS = 5

# A generated device that wires the BMP3xx, so every read the launcher makes has its chip.
_DEVICE = device_with("bmp3xx")
_PLAN_PATH = f"build/generated_src/sensortask_{_DEVICE}_wiring_plan.json"


def _chips(**chips: "_FakeChip") -> "dict[str, object]":
    wired: dict[str, object] = {}
    wired.update(chips)  # a recording double in each chip fake's place
    return wired


def _config(seed: int, faults: "list[launch.FaultSpec]", wifi: "list[int]", *, no_wdt_feed: bool, duration: float) -> "launch.LaunchConfig":
    return launch.LaunchConfig(_in_memory(), Injections(seed, faults, [], wifi), wiring_plan_path=_PLAN_PATH, no_wdt_feed=no_wdt_feed, duration=duration)


def _in_memory() -> "StatePaths":
    return StatePaths(None, None, None)  # no chip persists: every main() run here starts fresh


# ---------------------------------------------------------------------------
# parse_fault_spec / parse_hang_spec - the shared vocabulary
# ---------------------------------------------------------------------------


def test_parse_fault_spec_defaults_times_to_one_with_no_match() -> None:
    assert launch.parse_fault_spec("scd30:writeto") == ("scd30", "writeto", 1, None, "oserror")


def test_parse_fault_spec_honors_an_explicit_times_and_a_hex_match() -> None:
    assert launch.parse_fault_spec("sgp40:readfrom_into:3") == ("sgp40", "readfrom_into", 3, None, "oserror")
    assert launch.parse_fault_spec("scd30:readfrom_into:3:0x0300") == ("scd30", "readfrom_into", 3, 0x300, "oserror")
    assert launch.parse_fault_spec("bmp3xx:readfrom_mem:2:f7") == ("bmp3xx", "readfrom_mem", 2, 0xF7, "oserror")


def test_parse_fault_spec_and_parse_hang_spec_accept_every_op_of_their_tables() -> None:
    for device, ops in launch._FAULT_DEVICE_OPS.items():
        for op in ops:
            assert launch.parse_fault_spec(f"{device}:{op}") == (device, op, 1, None, "oserror"), (device, op)
    for device, ops in launch._HANG_DEVICE_OPS.items():
        for op in ops:
            assert launch.parse_hang_spec(f"{device}:{op}:0.5") == (device, op, 0.5, 1), (device, op)


def test_parse_fault_spec_addresses_an_instance_by_its_instance_key() -> None:
    assert launch._driver_of("uart_link_init") == "uart_link"  # the longest driver wins over a shorter prefix
    assert launch._driver_of("scd30_primary") == "scd30"
    assert launch.parse_fault_spec("scd30_x:writeto") == ("scd30_x", "writeto", 1, None, "oserror")
    assert launch._driver_of("scd3") is None
    assert launch.parse_fault_spec("uart_link_resp:silent") == ("uart_link_resp", "silent", 1, None, "oserror")
    assert launch.parse_hang_spec("scd30_primary:writeto:0.5") == ("scd30_primary", "writeto", 0.5, 1)


def test_parse_fault_spec_accepts_times_for_wlan_and_refuses_its_match() -> None:
    assert launch.parse_fault_spec("wlan:status:2") == ("wlan", "status", 2, None, "oserror")
    assert "MATCH" in _refused(launch.parse_fault_spec, "wlan:status:2:1")


def test_parse_fault_spec_refuses_times_and_match_for_a_persistent_mode() -> None:
    for spec in ("fram:silent:2", "isl29125:int_stuck_high:0x08", "uart_link:silent:1:2"):
        assert "mode" in _refused(launch.parse_fault_spec, spec), spec


def test_parse_fault_spec_has_no_fram_write_fault() -> None:
    # rp2's SPI write never raises, so the vocabulary offers no fault there; a hang still stalls it.
    _refused(launch.parse_fault_spec, "fram:write")
    assert launch.parse_hang_spec("fram:write:0.1") == ("fram", "write", 0.1, 1)


def test_parse_fault_spec_stack_queues_one_stack_exhaustion_on_a_queued_fault_only() -> None:
    assert launch.parse_fault_spec("sgp40:readfrom_into:stack") == ("sgp40", "readfrom_into", 1, None, "stack")
    for spec in ("wlan:status:stack", "fram:wren:stack", "sgp40:readfrom_into:stack:0x260F", "fram:silent:stack"):
        _refused(launch.parse_fault_spec, spec)


def test_parse_fault_spec_refuses_a_bad_device_op_shape_times_or_match() -> None:
    for spec in ("bogus:writeto", "scd30:readfrom_mem", "scd30", "scd30:writeto:2:59:extra", "", "scd30:writeto:x", "scd30:writeto:0", "scd30:writeto:1:zz"):
        _refused(launch.parse_fault_spec, spec)


def test_parse_hang_spec_covers_each_bus_write_op_and_refuses_wlan() -> None:
    assert launch.parse_hang_spec("bmp3xx:writeto:0.5:2") == ("bmp3xx", "writeto", 0.5, 2)
    assert launch.parse_hang_spec("isl29125:writeto:0.5") == ("isl29125", "writeto", 0.5, 1)
    for spec in ("wlan:connect:1", "scd30:writeto:0", "scd30:writeto:1:0", "scd30:writeto"):
        _refused(launch.parse_hang_spec, spec)


# ---------------------------------------------------------------------------
# parse_args
# ---------------------------------------------------------------------------


def test_parse_args_requires_a_wiring_plan() -> None:
    assert "--wiring-plan" in _refused(launch.parse_args, [])


def test_parse_args_defaults_persist_and_an_empty_path_means_in_memory() -> None:
    config = launch.parse_args(["--wiring-plan", "p.json"])
    assert config.wiring_plan_path == "p.json"
    assert config.state == StatePaths("digital_twin/fram_state.json", "digital_twin/scd30_state.json", "digital_twin/mem_backup_state.json")
    assert config.injections == Injections(None, [], [], [])
    assert config.no_wdt_feed is False
    assert config.duration is None
    flags = ["--fram-state-path", "", "--scd30-state-path", "", "--mem-backup-state-path", ""]
    assert launch.parse_args(["--wiring-plan", "p.json"] + flags).state == _in_memory()


def test_parse_args_rejects_an_unrecognized_flag_a_missing_value_or_an_unknown_wifi_outcome() -> None:
    for argv in (["--wiring-plan", "p", "--not-a-real-flag"], ["--wiring-plan", "p", "--seed"], ["--wiring-plan", "p", "--wifi-outcome", "bogus"]):
        _refused(launch.parse_args, argv)


def test_parse_args_help_exits_zero_before_parsing_anything_else() -> None:
    # --help answers before any other flag is read, so a typo next to it cannot turn the usage
    # request into a ValueError, and nothing after parse_args() (the chip fakes, the WDT) runs.
    for argv in (["--help"], ["-h"], ["--seed", "not-a-number", "--help"]):
        try:
            launch.parse_args(argv)
            raise AssertionError(f"expected SystemExit(0) for {argv}")
        except SystemExit as e:
            assert e.args == (0,), f"{argv}: --help must exit 0, got {e.args}"


def test_parse_args_combines_every_flag_together() -> None:
    config = launch.parse_args(
        [
            "--wiring-plan", "p.json",
            "--seed", "7",
            "--fram-state-path", "tests/_tmp/launch_fram.bin",
            "--scd30-state-path", "tests/_tmp/launch_scd30.json",
            "--mem-backup-state-path", "tests/_tmp/launch_mem.json",
            "--fault", "bmp3xx:readfrom_mem:3",
            "--fault", "wlan:connect",
            "--hang", "scd30:readfrom_into:0.5",
            "--wifi-outcome", "connect_fail",
            "--no-wdt-feed",
            "--duration", "1.5",
        ],
    )
    assert config.state == StatePaths("tests/_tmp/launch_fram.bin", "tests/_tmp/launch_scd30.json", "tests/_tmp/launch_mem.json")
    faults: list[launch.FaultSpec] = [("bmp3xx", "readfrom_mem", 3, None, "oserror"), ("wlan", "connect", 1, None, "oserror")]
    assert config.injections == Injections(7, faults, [("scd30", "readfrom_into", 0.5, 1)], [network.STAT_CONNECT_FAIL])
    assert config.no_wdt_feed is True
    assert config.duration == 1.5


# ---------------------------------------------------------------------------
# _collect_chips / _apply_fault / _apply_hang - the one implementation both runners use
# ---------------------------------------------------------------------------


class _RecordingInjector:
    # Records each call in the FaultInjector shape (inject_fault(op, exc_type, *args, times=, match=)).
    def __init__(self) -> None:
        self.faults: list[tuple[object, ...]] = []
        self.hangs: list[tuple[str, float, int]] = []

    def inject_fault(self, op: str, exc_type: "type[BaseException]", *args: object, times: int = 1, match: "int | None" = None) -> None:
        self.faults.append((op, exc_type, args, times, match))

    def inject_hang(self, op: str, seconds: float, times: int = 1) -> None:
        self.hangs.append((op, seconds, times))


class _FakeChip:
    def __init__(self) -> None:
        self.fault = _RecordingInjector()
        self.silent = False
        self.drop_next_wren = 0
        self.modes: list[str] = []

    def configure_fault(self, op: str) -> None:
        self.modes.append(op)


def test_collect_chips_keys_each_wired_chip_by_its_instance_key_through_peripheral() -> None:
    plan: _Plan = {
        "device": "fixture-device",
        "buses": {
            "i2c0": [{"driver": "scd30", "name_ext": "primary", "address": 0x61, "irq_pin": 2}],
            "i2c1": [{"driver": "sgp40", "name_ext": "", "address": 0x59}],
        },
        "spi": {"spi0": {"driver": "fram", "name_ext": "", "max_size": 0x2000}},
        "uart": None,
        "pins": {},
    }
    machine.configure_wiring(plan)

    async def scenario() -> None:  # one run: the twin SCD30's refresh timer is a task, ended with the run
        i2c0 = machine.I2C(0, scl=machine.Pin(13), sda=machine.Pin(12))
        spi0 = machine.SPI(0, sck=machine.Pin(2), mosi=machine.Pin(3), miso=machine.Pin(4))
        chips = launch._collect_chips(plan)  # i2c1 never constructed: skipped, not an error
        assert sorted(chips) == ["fram", "scd30_primary"], sorted(chips)
        assert chips["scd30_primary"] is i2c0.devices[0x61]
        assert chips["fram"] is spi0.device

    run(scenario())


def test_apply_fault_queues_a_fresh_oserror_with_times_and_match() -> None:
    chip = _FakeChip()
    launch._apply_fault(("sgp40", "writeto", 2, 0x59, "oserror"), _chips(sgp40=chip), network.WLAN(network.STA_IF))
    assert chip.fault.faults == [("writeto", OSError, (errno.EIO, "digital_twin/launch.py --fault sgp40:writeto"), 2, 0x59)]


def test_apply_fault_sets_each_mode_and_counted_knob() -> None:
    isl, fram, link = _FakeChip(), _FakeChip(), _FakeChip()
    chips = _chips(isl29125=isl, fram=fram, uart_link_init=link)
    wlan = network.WLAN(network.STA_IF)
    for spec in ("isl29125:int_stuck_high", "fram:silent", "fram:wren:3", "uart_link_init:silent"):
        launch._apply_fault(launch.parse_fault_spec(spec), chips, wlan)
    assert isl.modes == ["isl29125:int_stuck_high"]
    assert fram.silent and fram.drop_next_wren == 3 and link.silent
    assert fram.fault.faults == [] and link.fault.faults == []


def _refused(fn: "Callable[P, object]", *args: "P.args", **kwargs: "P.kwargs") -> str:
    try:
        fn(*args, **kwargs)
    except ValueError as e:
        return str(e)
    raise AssertionError(f"expected ValueError for {args!r}")


def test_a_stack_fault_raises_one_stack_exhaustion_on_the_chips_next_read() -> None:
    plan: _Plan = {"device": "fixture-device", "buses": {"i2c0": [{"driver": "sgp40", "name_ext": "", "address": 0x59}]}, "spi": {}, "uart": None, "pins": {}}
    machine.configure_wiring(plan)
    bus = machine.I2C(0, scl=machine.Pin(13), sda=machine.Pin(12))
    launch._apply_fault(launch.parse_fault_spec("sgp40:readfrom_into:stack"), launch._collect_chips(plan), network.WLAN(network.STA_IF))
    buf = bytearray(3)
    try:
        bus.readfrom_into(0x59, buf)
    except RuntimeError as e:
        assert str(e) == src_const("src/asy_print_log.py", "_STACK_EXHAUSTED"), e  # test_asy_print_log.py pins it to the real text
    else:
        raise AssertionError("the queued stack fault never raised")
    bus.readfrom_into(0x59, buf)  # one fault, spent


def test_apply_fault_arms_wlan_with_its_times_and_bypasses_the_wiring_check() -> None:
    # wlan is no chip in `chips`, so the guard sits after that branch: in front of it, every --fault wlan:* would raise.
    wlan = network.WLAN(network.STA_IF)
    launch._apply_fault(("wlan", "connect", 2, None, "oserror"), {}, wlan)
    assert wlan.raise_on["connect"] == (OSError, (errno.EIO, "digital_twin/launch.py --fault wlan:connect"), 2), wlan.raise_on


def test_a_fault_or_hang_naming_a_chip_this_run_never_wired_is_refused_by_name() -> None:
    # The name parses (it is in the vocabulary) but this run wired no such chip: the refusal names the
    # asked-for device, what is wired, and which entry point refused it.
    message = _refused(launch._apply_fault, ("isl29125", "readfrom_mem", 1, None, "oserror"), _chips(scd30=_FakeChip()), network.WLAN(network.STA_IF))
    assert "isl29125" in message and "scd30" in message and "digital_twin/launch.py" in message, message
    assert "uart_link_init" in _refused(launch._apply_fault, ("uart_link_init", "silent", 1, None, "oserror"), {}, network.WLAN(network.STA_IF))
    assert "isl29125" in _refused(launch._apply_hang, ("isl29125", "readfrom_mem", 0.1, 1), {})
    chip = _FakeChip()
    launch._apply_hang(("scd30", "writeto", 0.1, 2), _chips(scd30=chip))
    assert chip.fault.hangs == [("writeto", 0.1, 2)]


def test_require_wired_names_the_entry_point_it_was_given() -> None:
    try:
        launch._require_wired("bmp3xx", {}, source="run_generic_integration.py")
    except ValueError as e:
        assert "digital_twin/run_generic_integration.py" in str(e), e
    else:
        raise AssertionError("an unwired device must be refused")


# ---------------------------------------------------------------------------
# main() - short end-to-end runs over the fixture plan
# ---------------------------------------------------------------------------


def test_main_runs_end_to_end_and_returns_a_summary() -> None:
    summary = run(asyncio.wait_for(launch.main(_config(1234, [], [], no_wdt_feed=True, duration=_SHORT_DURATION_S)), _MAIN_BOUND_S))
    readings = summary["readings"]
    assert readings is not None and readings >= 1  # at least one real bus-level read happened
    assert summary["wifi_status"] is not None
    assert summary["would_have_triggered_count"] == 0  # only 0.5s, well under wdt.timeout_ms (8000 ms)


def test_main_with_scripted_faults_and_wifi_outcome_still_completes() -> None:
    # The duration clears network.py's connect delay for the scripted outcome to settle, and one poll interval past
    # the first round: both one-shot faults fire on that first round, which then yields no reading at all.
    faults: list[launch.FaultSpec] = [("sgp40", "writeto", 1, None, "oserror"), ("bmp3xx", "readfrom_mem", 1, None, "oserror")]
    summary = run(asyncio.wait_for(launch.main(_config(99, faults, [network.STAT_NO_AP_FOUND], no_wdt_feed=True, duration=_FAULT_DURATION_S)), _MAIN_BOUND_S))
    assert summary["wifi_status"] == network.STAT_NO_AP_FOUND
    readings = summary["readings"]
    assert readings is not None and readings >= 1  # the second round's readings, after both faults were spent


def test_main_a_wlan_fault_is_isolated_and_still_returns_a_summary() -> None:
    # WLAN.active()/connect() at startup and WLAN.status() in the cleanup and the watcher are each isolated, so a
    # --fault wlan:... leaves the feed and read loops running.
    config = _config(7, [("wlan", "connect", 1, None, "oserror")], [], no_wdt_feed=True, duration=_SHORT_DURATION_S)
    summary = run(asyncio.wait_for(launch.main(config), _MAIN_BOUND_S))
    readings = summary["readings"]
    assert readings is not None and readings >= 1  # sensor loop still ran despite the WLAN fault


def test_main_long_enough_duration_reaches_a_real_wdt_feed_and_scd30s_timer_driven_reading() -> None:
    # _SENSOR_POLL_INTERVAL_S and SCD30's default measurement interval are both 2.0s, so only a longer run lets the
    # SCD30's Timer produce a ready reading; no_wdt_feed=False exercises a real watchdog.feed() too.
    summary = run(asyncio.wait_for(launch.main(_config(55, [], [], no_wdt_feed=False, duration=_LONG_DURATION_S)), _LONG_MAIN_BOUND_S))
    readings = summary["readings"]
    assert readings is not None and readings >= _LONG_MIN_READINGS  # several rounds across 4.5s, past SCD30's 2s cadence
    assert summary["would_have_triggered_count"] == 0  # fed for real, well under wdt.timeout_ms (8000 ms)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
