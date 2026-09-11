"""Unit tests for digital_twin/run_generic_integration.py: parse_args() (pure), _collect_chips()
(the generalized fault/hang chip lookup - BUILD_CHAIN_PLAN.md's Session 5 write-up, item 4), and one
real end-to-end smoke boot. The smoke test deliberately reuses the hand-written sensortask_wozi
module plus machine's own "wozi" legacy wiring plan (JSON-dumped to a temp file) rather than a real
buildgen-generated module - buildgen needs tomllib/CPython and can't run inside this MicroPython
process at all (see the module docstring this file's own subject re-states); proving a genuinely
*generated* module boots is tests_scripts/test_digital_twin_generated_boot.py's job instead. This
file only proves run_generic_integration.py's own generic machinery (dynamic --module import, JSON
wiring-plan loading, generalized chip lookup) works, using a well-understood module as the payload."""

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
# module -> asy_webserver_service -> microdot - same convention test_digital_twin_run_wozi_integration.py's
# own comment uses.
sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

import machine
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
    plan: "dict[str, Any]" = {"buses": {"i2c1": []}, "spi": {}}
    module = _FakeModule()
    assert _collect_chips(module, plan) == {}


# ---------------------------------------------------------------------------
# main() - one real, short, bounded end-to-end smoke test (same spirit as
# test_digital_twin_run_wozi_integration.py's own main() smoke test): boots the real hand-written
# sensortask_wozi object graph via the GENERIC entry point (not a static `import sensortask_wozi`),
# wired from a JSON-dumped copy of machine's own "wozi" legacy plan, with one real injected fault.
# Deliberately exactly one such test - see test_digital_twin_run_wozi_integration.py's own identical
# comment for why (the real object graph's orphaned background tasks after main_task.cancel()).
# ---------------------------------------------------------------------------


def test_main_boots_sensortask_wozi_through_the_generic_path_and_serves_real_http() -> None:
    import json
    import os

    try:
        os.mkdir("tests/_tmp")
    except OSError:
        pass
    plan_path = "tests/_tmp/generic_integration_wiring_plan.json"
    with open(plan_path, "w") as f:
        json.dump(machine._LEGACY_WIRING_PLANS["wozi"], f)

    config = RunConfig(
        "sensortask_wozi",
        plan_path,
        host="127.0.0.1",
        port=19099,
        fram_state_path=None,
        scd30_state_path=None,
        duration=0.0,
        faults=[("sgp40", "writeto", 2)],
    )
    try:
        summary = run_timed(main(config), timeout_s=30.0)
    finally:
        try:
            os.remove(plan_path)
        except OSError:
            pass
    assert summary["failures"] == []
