"""Unit tests for digital_twin/run_generic_integration.py: parse_args() (pure), _collect_chips() (the generalized fault/hang chip lookup), and one real end-to-end smoke boot. The soak/memory-trend-check machinery itself (formerly this file's own _soak() coverage) moved host-side (SPECIFICATION.md's "Driver/DUT process separation" Part, 2026-09-14) - see scripts/_digital_twin_ci_suite.py's own Run 11 and tests_scripts/test_digital_twin_ci_suite_soak.py instead.
The smoke test reuses the hand-written sensortask_wozi module plus wozi's own build/generated_src/sensortask_wozi_wiring_plan.json (buildgen-generated, same file machine.configure_i2c_wiring("wozi") itself loads), not a real buildgen-generated module - buildgen needs tomllib/CPython and can't run inside this MicroPython process at all; proving a genuinely *generated* module boots is tests_scripts/test_digital_twin_generated_boot.py's job instead. This file only proves run_generic_integration.py's own generic machinery works, using a well-understood module as the payload."""

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

sys.path.insert(0, "ext")  # run_generic_integration.py transitively imports a booted sensortask_*
# module -> asy_webserver_service -> microdot - reaches the real, vendored ext/microdot.py.
sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

import machine
import run_generic_integration
from machine import I2C, SPI, Pin
from run_generic_integration import RunConfig, _collect_chips, main, parse_args


def run_timed(coro: "Coroutine[Any, Any, T]", timeout_s: float = 5.0) -> "T":
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


def test_parse_args_device_label_overrides_the_module_name() -> None:
    config = parse_args(["--module", "sensortask_novel_combo", "--wiring-plan", "plan.json", "--device", "novel_combo"])
    assert config.device == "novel_combo"


def test_parse_args_host_and_port() -> None:
    config = parse_args(["--module", "m", "--wiring-plan", "p.json", "--host", "0.0.0.0", "--port", "9090"])
    assert config.host == "0.0.0.0"
    assert config.port == 9090


def test_parse_args_empty_fram_state_path_means_in_memory_only() -> None:
    config = parse_args(["--module", "m", "--wiring-plan", "p.json", "--fram-state-path", ""])
    assert config.fram_state_path is None


def test_parse_args_fault_hang_and_wifi_outcome_reuse_launchs_own_parsers() -> None:
    config = parse_args(
        [
            "--module", "m", "--wiring-plan", "p.json",
            "--fault", "sgp40:writeto:2",
            "--hang", "scd30:readfrom_into:0.5",
            "--wifi-outcome", "no_ap",
        ],
    )
    assert config.faults == [("sgp40", "writeto", 2)]
    assert config.hangs == [("scd30", "readfrom_into", 0.5, 1)]
    assert len(config.wifi_outcomes) == 1


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
    assert config.gc_threshold == 32768


def test_parse_args_gc_threshold_is_overridable() -> None:
    # scripts/_digital_twin_ci_suite.py's own main() needs this to drive the whole suite at
    # MicroPython's own real reactive-only default (CLAUDE.md's/SPECIFICATION.md Part I.4(e)'s
    # standing rule that the whole suite must pass there *before* it's ever run with a chosen
    # threshold).
    config = parse_args(["--module", "m", "--wiring-plan", "p.json", "--gc-threshold", "-1"])
    assert config.gc_threshold == -1


def test_parse_args_mem_sample_interval_ms_defaults_to_disabled() -> None:
    # Unset by default - the background gc.mem_free() sampler (_mem_sampler()) only exists to feed
    # scripts/_digital_twin_ci_suite.py's own Run 11 soak-trend check; an ordinary twin run has no
    # reason to pay for it.
    config = parse_args(["--module", "m", "--wiring-plan", "p.json"])
    assert config.mem_sample_interval_ms is None


def test_parse_args_mem_sample_interval_ms_is_settable() -> None:
    config = parse_args(["--module", "m", "--wiring-plan", "p.json", "--mem-sample-interval-ms", "25"])
    assert config.mem_sample_interval_ms == 25


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
    # Class-level attribute declarations, defaulting to None - the same shape a real generated
    # module's own globals take before build_system() assigns them (buildgen/codegen.py's own
    # _emit_globals(): `i2c0: "Any | None" = None`) - lets test functions below assign whichever
    # subset a given plan actually wires, without mypy flagging the rest as undeclared.
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
# main() - one real, short, bounded end-to-end smoke test: boots the real hand-written
# sensortask_wozi object graph via the GENERIC entry point (not a static `import sensortask_wozi`),
# wired from a JSON-dumped copy of machine's own "wozi" legacy plan, with one real injected fault -
# the same combined shape run_wozi_integration.py's own now-retired main() smoke test used
# (SPECIFICATION.md Part L.4). No soak driving here any more (SPECIFICATION.md's "Driver/
# DUT process separation" Part, 2026-09-14) - that moved host-side to scripts/
# _digital_twin_ci_suite.py's own Run 11, which is what actually exercises request-driving against
# a real boot at scale; this test only proves main() itself boots/arms a fault/shuts down cleanly.
# Deliberately exactly one such test, not two (a boot-only one plus a separate fault-injection one):
# main()'s own real supervisor (sensortask_wozi.main()/start_and_check_tasks()) leaves several real
# background tasks running after main()'s own main_task.cancel() - the same orphaned-task
# memory-pressure bug tests/test_digital_twin_sensortask_integration.py's own module docstring
# already documents in full. digital_twin/launch.py's own test file has exactly one such smoke test
# for the identical reason - matched here, not reinvented.
# ---------------------------------------------------------------------------


def test_main_boots_arms_a_fault_and_shuts_down_cleanly() -> None:
    config = RunConfig(
        "sensortask_wozi",
        "build/generated_src/sensortask_wozi_wiring_plan.json",  # buildgen-generated - see this file's own module docstring
        host="127.0.0.1",
        port=19099,
        fram_state_path=None,
        scd30_state_path=None,
        duration=0.0,  # boot, arm the fault, then shut down immediately - no soak driving here any more
        faults=[("sgp40", "writeto", 2)],
    )
    run_timed(main(config), timeout_s=15.0)
    # _booted_module is set by main() itself and read the same way _print_wdt_status()'s own two
    # call sites do - the real watchdog must never have starved just from this ordinary boot.
    booted = run_generic_integration._booted_module
    assert booted is not None
    assert booted.watchdog.would_have_triggered_count == 0


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
