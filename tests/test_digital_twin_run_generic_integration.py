"""Unit tests for digital_twin/run_generic_integration.py: parse_args() (pure), _collect_chips() (the generalized fault/hang chip lookup), and one real end-to-end smoke boot. The soak/memory-trend-check machinery itself (formerly this file's own _soak() coverage) moved host-side (SPECIFICATION.md's "Driver/DUT process separation" Part, 2026-09-14) - see scripts/_digital_twin_ci_suite.py's own Run 11 and tests_scripts/test_digital_twin_ci_suite_soak.py instead.
The smoke test reuses the hand-written sensortask_wozi module plus wozi's own build/generated_src/sensortask_wozi_wiring_plan.json (buildgen-generated, same file machine.configure_i2c_wiring("wozi") itself loads), not a real buildgen-generated module - buildgen needs tomllib/CPython and can't run inside this MicroPython process at all; proving a genuinely *generated* module boots is tests_scripts/test_digital_twin_generated_boot.py's job instead. This file only proves run_generic_integration.py's own generic machinery works, using a well-understood module as the payload."""

import asyncio
import sys
import time

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")

sys.path.insert(0, "ext")  # run_generic_integration.py transitively imports a booted sensortask_*
# module -> asy_webserver_service -> microdot - reaches the real, vendored ext/microdot.py.
sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

import machine
import network
import run_generic_integration
from _tmp_scratch import TmpScratch
from _twin_common import Injections, StatePaths
from machine import I2C, SPI, Pin
from run_generic_integration import RunConfig, RunLimits, _apply_fault, _apply_hang, _collect_chips, _serve_until, main, parse_args

# @tunable l2.run_generic_integration_run_bound_s = 5.0
_RUN_BOUND_S = 5.0
# @tunable l2.run_generic_integration_main_run_bound_s = 15.0
_MAIN_RUN_BOUND_S = 15.0


_scratch = TmpScratch("rgi")


def run_timed(coro: "Coroutine[Any, Any, T]", timeout_s: float = _RUN_BOUND_S) -> "T":
    return asyncio.run(asyncio.wait_for(coro, timeout_s))


# ---------------------------------------------------------------------------
# parse_args() - CLI argument parsing
# ---------------------------------------------------------------------------


def test_parse_args_requires_module() -> None:
    try:
        parse_args(["--wiring-plan", "plan.json"])
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "--module" in str(e)


def test_parse_args_requires_wiring_plan() -> None:
    try:
        parse_args(["--module", "sensortask_wozi"])
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "--wiring-plan" in str(e)


def test_parse_args_minimal_valid_config() -> None:
    config = parse_args(["--module", "sensortask_novel_combo", "--wiring-plan", "plan.json"])
    assert config == RunConfig("sensortask_novel_combo", "plan.json")
    assert config.device == "sensortask_novel_combo"  # defaults to the module name, unset --device
    assert config.state == StatePaths(None, None)
    assert config.injections == Injections(None, [], [], [])
    # @tunable gc.threshold_bytes = 32768
    assert config.run == RunLimits(None, 32768, None, None)


def test_run_config_compares_and_prints_its_grouped_fields() -> None:
    faulted = RunConfig("m", "p.json", injections=Injections(None, [("sgp40", "writeto", 1)], [], []))
    assert faulted != RunConfig("m", "p.json")
    assert faulted == RunConfig("m", "p.json", injections=Injections(None, [("sgp40", "writeto", 1)], [], []))
    text = repr(faulted)
    assert "state=" in text and "injections=" in text and "run=" in text, text


def test_parse_args_device_label_overrides_the_module_name() -> None:
    config = parse_args(["--module", "sensortask_novel_combo", "--wiring-plan", "plan.json", "--device", "novel_combo"])
    assert config.device == "novel_combo"


def test_parse_args_host_and_port() -> None:
    config = parse_args(["--module", "m", "--wiring-plan", "p.json", "--host", "0.0.0.0", "--port", "9090"])
    assert config.host == "0.0.0.0"
    assert config.port == 9090


def test_parse_args_empty_fram_state_path_means_in_memory_only() -> None:
    config = parse_args(["--module", "m", "--wiring-plan", "p.json", "--fram-state-path", ""])
    assert config.state.fram is None


def test_parse_args_fault_hang_and_wifi_outcome_reuse_launchs_own_parsers() -> None:
    config = parse_args(
        [
            "--module", "m", "--wiring-plan", "p.json",
            "--fault", "sgp40:writeto:2",
            "--hang", "scd30:readfrom_into:0.5",
            "--wifi-outcome", "no_ap",
        ],
    )
    assert config.injections.faults == [("sgp40", "writeto", 2)]
    assert config.injections.hangs == [("scd30", "readfrom_into", 0.5, 1)]
    assert len(config.injections.wifi_outcomes) == 1


def test_parse_args_rejects_an_unrecognized_flag() -> None:
    try:
        parse_args(["--module", "m", "--wiring-plan", "p.json", "--bogus"])
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_parse_args_missing_value_for_a_flag_raises() -> None:
    # _pop_value()'s own guard.
    try:
        parse_args(["--module", "m", "--wiring-plan", "p.json", "--host"])
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_parse_args_gc_threshold_defaults_to_matching_real_firmware() -> None:
    # 32768 matches buildgen.codegen.generate_boot_entry_source()'s own real-firmware boot entry -
    # an ordinary twin run should model production's real memory-safety configuration by default,
    # not just its allocation code. See _GC_THRESHOLD_DEFAULT's own module-level comment.
    config = parse_args(["--module", "m", "--wiring-plan", "p.json"])
    # @tunable gc.threshold_bytes = 32768
    assert config.run.gc_threshold == 32768


def test_parse_args_gc_threshold_is_overridable() -> None:
    # scripts/_digital_twin_ci_suite.py's main() needs this to drive the whole suite at MicroPython's own
    # reactive-only default - Part I.4(e)'s standing rule that the suite must pass there before it is ever
    # run with a chosen threshold.
    config = parse_args(["--module", "m", "--wiring-plan", "p.json", "--gc-threshold", "-1"])
    assert config.run.gc_threshold == -1


def test_parse_args_mem_sample_interval_ms_defaults_to_disabled() -> None:
    # Unset by default - the background gc.mem_free() sampler (_mem_sampler()) only exists to feed
    # scripts/_digital_twin_ci_suite.py's own Run 11 soak-trend check; an ordinary twin run has no
    # reason to pay for it.
    config = parse_args(["--module", "m", "--wiring-plan", "p.json"])
    assert config.run.mem_sample_interval_ms is None


def test_parse_args_mem_sample_interval_ms_is_settable() -> None:
    config = parse_args(["--module", "m", "--wiring-plan", "p.json", "--mem-sample-interval-ms", "25"])
    assert config.run.mem_sample_interval_ms == 25


def test_parse_args_stop_file_is_settable_and_empty_means_none() -> None:
    assert parse_args(["--module", "m", "--wiring-plan", "p.json", "--stop-file", "s"]).run.stop_file == "s"
    assert parse_args(["--module", "m", "--wiring-plan", "p.json", "--stop-file", ""]).run.stop_file is None


# ---------------------------------------------------------------------------
# _serve_until() - the duration as an upper bound a caller done early ends with a file
# ---------------------------------------------------------------------------


def test_serving_ends_at_once_when_the_stop_file_already_exists() -> None:
    stop = _scratch.path("stop_present")
    with open(stop, "w"):
        pass
    start = time.ticks_ms()
    run_timed(_serve_until(30.0, stop))
    assert time.ticks_diff(time.ticks_ms(), start) < 1000  # a 30 s bound, left on the first look


def test_serving_ends_once_the_stop_file_appears() -> None:
    stop = _scratch.path("stop_later")

    async def scenario() -> int:
        async def write_later() -> None:
            await asyncio.sleep_ms(300)
            with open(stop, "w"):
                pass

        writer = asyncio.create_task(write_later())
        start = time.ticks_ms()
        await _serve_until(30.0, stop)
        await writer
        return time.ticks_diff(time.ticks_ms(), start)

    elapsed = run_timed(scenario())
    assert 300 <= elapsed < 3000, elapsed  # after the write, long before the 30 s bound


def test_serving_without_the_stop_file_lasts_the_whole_duration() -> None:
    for stop in (None, _scratch.path("stop_never")):
        start = time.ticks_ms()
        run_timed(_serve_until(0.4, stop))
        assert time.ticks_diff(time.ticks_ms(), start) >= 400, stop


# ---------------------------------------------------------------------------
# _collect_chips() - the generalized fault/hang lookup (replaces run_wozi_integration.py's/
# run_dev_integration.py's own hardcoded {"scd30": sensortask_wozi.i2c0._i2c.devices[0x61], ...})
# ---------------------------------------------------------------------------


class _FakeBusWrapper:
    # Stands in for asy_i2c_driver.I2C/asy_spi_driver.SPI's own real "_i2c"/"_spi" attribute
    # (the twin's real machine.I2C/machine.SPI object) - _collect_chips() only ever reads that one
    # attribute off whatever bus_var it's given, so this is the minimal double for it.
    def __init__(self, i2c: "I2C | None" = None, spi: "SPI | None" = None) -> None:
        self._i2c = i2c
        self._spi = spi


class _FakeModule:
    # Class-level attribute declarations defaulting to None, standing in for a generated module's globals that
    # build_system() has not assigned (_collect_chips() reads them with getattr()) - letting test functions
    # assign whichever subset a plan wires without mypy flagging the rest as undeclared.
    i2c0: "_FakeBusWrapper | None" = None
    i2c1: "_FakeBusWrapper | None" = None
    spi0: "_FakeBusWrapper | None" = None


def test_collect_chips_keys_a_single_instance_driver_by_its_plain_name() -> None:
    Pin.reset_registry()
    plan = {"buses": {"i2c0": [{"driver": "scd30", "name_ext": "", "address": 0x61, "irq_pin": 6}]}, "spi": {}}
    machine.configure_wiring(plan)
    module = _FakeModule()
    bus0 = _FakeBusWrapper(i2c=I2C(0, scl=Pin(13), sda=Pin(12), freq=50000))
    module.i2c0 = bus0
    chips = _collect_chips(module, plan)
    assert bus0._i2c is not None
    assert chips["scd30"] is bus0._i2c.devices[0x61]
    assert "scd30_" not in "".join(chips)  # no name_ext -> no qualified key emitted


def test_collect_chips_keys_a_multi_instance_driver_by_its_qualified_name_too() -> None:
    Pin.reset_registry()
    plan = {
        "buses": {
            "i2c0": [{"driver": "scd30", "name_ext": "primary", "address": 0x61, "irq_pin": 2}],
            "i2c1": [{"driver": "scd30", "name_ext": "secondary", "address": 0x61, "irq_pin": 8}],
        },
        "spi": {},
    }
    machine.configure_wiring(plan)
    module = _FakeModule()
    bus0 = _FakeBusWrapper(i2c=I2C(0, scl=Pin(13), sda=Pin(12), freq=50000))
    bus1 = _FakeBusWrapper(i2c=I2C(1, scl=Pin(19), sda=Pin(18), freq=50000))
    module.i2c0 = bus0
    module.i2c1 = bus1
    chips = _collect_chips(module, plan)
    assert bus0._i2c is not None and bus1._i2c is not None
    assert chips["scd30_primary"] is bus0._i2c.devices[0x61]
    assert chips["scd30_secondary"] is bus1._i2c.devices[0x61]
    # The plain "scd30" key still exists (first instance wins) - parse_fault_spec()'s own
    # vocabulary (launch.py) can only ever address a driver by its plain name, never per-instance.
    assert chips["scd30"] is bus0._i2c.devices[0x61]


def test_collect_chips_includes_fram_from_the_spi_bus() -> None:
    Pin.reset_registry()
    plan = {"buses": {}, "spi": {"spi0": {"driver": "fram", "name_ext": "", "max_size": 0x2000}}}
    machine.configure_wiring(plan)
    module = _FakeModule()
    bus0 = _FakeBusWrapper(spi=SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4)))
    module.spi0 = bus0
    chips = _collect_chips(module, plan)
    assert bus0._spi is not None
    assert chips["fram"] is bus0._spi.device


def test_collect_chips_skips_a_bus_var_the_module_never_constructed() -> None:
    # A generated device that has no i2c1 at all (e.g. every sensor lives on i2c0) must not crash
    # _collect_chips() just because plan["buses"] happens to be empty for i2c1 - getattr()'s own
    # default handles a bus name the module never set as an attribute in the first place too.
    plan: dict[str, Any] = {"buses": {"i2c1": []}, "spi": {}}
    module = _FakeModule()
    assert _collect_chips(module, plan) == {}


# ---------------------------------------------------------------------------
# main() - one real, short, bounded end-to-end smoke test: boots the real sensortask_wozi object graph via
# the GENERIC entry point rather than a static import, wired from a JSON-dumped copy of machine's "wozi"
# plan, with one real injected fault - the shape the retired run_wozi_integration.py's own test used.
#
# No soak driving here any more (SPECIFICATION.md's "Driver/DUT process separation" Part): that moved host-
# side to the CI suite's Run 11, which drives requests against a real boot at scale. This only proves main()
# itself boots, arms a fault and shuts down cleanly.
#
# Deliberately exactly one such test, not a boot-only one plus a separate fault-injection one: main()'s real
# supervisor leaves several background tasks running after main_task.cancel(), the orphaned-task memory-
# pressure problem the twin integration suite's docstring documents. launch.py's tests match this.
# ---------------------------------------------------------------------------


def test_main_boots_arms_a_fault_and_shuts_down_cleanly() -> None:
    config = RunConfig(
        "sensortask_wozi",
        "build/generated_src/sensortask_wozi_wiring_plan.json",  # buildgen-generated - see this file's own module docstring
        host="127.0.0.1",
        port=19099,
        state=StatePaths(None, None),
        injections=Injections(None, [("sgp40", "writeto", 2)], [], []),
        run=RunLimits(0.0, run_generic_integration._GC_THRESHOLD_DEFAULT, None, None),  # boot, arm the fault, then shut down immediately - no soak driving here any more
    )
    run_timed(main(config), timeout_s=_MAIN_RUN_BOUND_S)
    # The WDT the runner built and passed to the booted module's main(), read as _print_wdt_status()
    # reads it: an ordinary boot never starves it.
    watchdog = run_generic_integration._watchdog
    assert watchdog is not None
    assert watchdog.would_have_triggered_count == 0


# ---------------------------------------------------------------------------
# _apply_fault/_apply_hang - a name in the vocabulary is not a chip on THIS device
# ---------------------------------------------------------------------------


def test_a_fault_naming_a_driver_this_device_does_not_carry_is_refused_by_name() -> None:
    # The generic entry point boots whatever a device's own TOML declares, so the miss is routine
    # rather than exotic: bmp3xx is wozi/dev-only and isl29125 is dev-only, yet both parse on every
    # device. The refusal has to name the device asked for AND what is actually wired.
    try:
        _apply_fault("bmp3xx", "readfrom_mem", 1, {"scd30": object(), "fram": object()}, network.WLAN(network.STA_IF))
    except ValueError as e:
        assert "bmp3xx" in str(e), e
        assert "fram" in str(e) and "scd30" in str(e), "the message must list what this device did wire"
    else:
        raise AssertionError("an unwired driver must be refused, not KeyError from inside the plumbing")


def test_a_hang_naming_a_driver_this_device_does_not_carry_is_refused_the_same_way() -> None:
    try:
        _apply_hang("bmp3xx", "readfrom_mem", 0.1, 1, {})
    except ValueError as e:
        assert "bmp3xx" in str(e), e
    else:
        raise AssertionError("--hang must refuse an unwired driver too, not only --fault")


def test_a_wlan_fault_still_bypasses_the_wiring_check() -> None:
    # wlan never appears in `chips`, so the guard must sit after that branch - in front of it, every
    # --fault wlan:* run on every device would raise instead of arming the outcome.
    wlan = network.WLAN(network.STA_IF)
    _apply_fault("wlan", "connect", 1, {}, wlan)
    assert "connect" in wlan.raise_on


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
