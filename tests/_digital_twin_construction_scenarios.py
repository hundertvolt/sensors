"""Shared scenario library: twin-tier construction, wiring and boot across every generated device (SPECIFICATION.md Part
L.4), fast, no wall-clock waits. Not a test file: it exports register_for_device(), load_device() and DrivenWall, after
the caller's prewarm and UDP shim (tests/test_digital_twin_construction.py); Part E.2.1 has the per-device split."""

import asyncio
import json
import sys
import time

sys.path.insert(0, "ext")  # same convention as tests/_sensortask_scenarios.py's own comment
sys.path.insert(0, "digital_twin")  # see tests/test_digital_twin_sgp40.py's own comment for why

import _wall_clock
import machine
import microtest
import network
import run_generic_integration
from _async_harness import cancel, run_timed
from _boot_recorder import BootRecorder, expected_entries
from _fake_time import DrivenTime
from _generated_module import ERROR_LEVEL, boot_entry_watchdog, boot_generated, write_error_level_config
from _generated_tree import require_fresh
from _offline_ntp_config import write_offline_ntp_config  # _generated_module's import put its directory on the path
from _port_bands import PortAllocator
from _shared_rest_roundtrip import assert_named_modules_constructed
from _tmp_scratch import TmpScratch
from _twin_devices import generated_devices, wiring_plan

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType
    from typing import TypedDict, TypeVar, cast

    from launch import _Plan

    T = TypeVar("T")

    class _ExpectedFacts(TypedDict):
        # The part of buildgen's expected facts these scenarios read.
        boot_sequence: dict[str, list[str]]

else:

    def cast(_typ: object, val: "T") -> "T":  # no typing module on MicroPython: the identity at run time
        return val

require_fresh()  # every scenario boots a generated module and reads its plan

# @tunable l2.construction_scenarios_run_timeout_s = 10.0
_RUN_TIMEOUT_S = 10.0
# The product's own maintenance modules, which every generated build_system() constructs whatever its TOML declares.
_MAINTENANCE = ("conn", "ntp", "sysfunct", "webserver")
# Where each IRQ-wired driver keeps its line: (the reader's Pin attribute, its chip fake's Pin attribute).
_IRQ_ATTRIBUTES = {"scd30": ("_irq_pin", "_rdy_pin"), "isl29125": ("irq_pin", "_int_pin")}

_scratch: "TmpScratch | None" = None
_ports: "PortAllocator | None" = None
_PARAM_SCENARIOS: "list[tuple[str, Callable[[str], None]]]" = []


def _register_param(name: str) -> "Callable[[Callable[[str], None]], Callable[[str], None]]":
    def deco(fn: "Callable[[str], None]") -> "Callable[[str], None]":
        _PARAM_SCENARIOS.append((name, fn))
        return fn

    return deco


async def _boot_device(port: int, device: str) -> "ModuleType":
    module = _fresh_board(device)
    module, _watchdog = await boot_generated(module, device, cfg_path=_tmp_cfg_dir(), log_errors=True, web_host="127.0.0.1", web_port=port)
    return module


def _constructed_names(module: "ModuleType") -> "set[str]":
    # Every module global holding a constructed product module (it has setup() and loggers), as the boot recorder finds them.
    return {name for name in dir(module) if not name.startswith("_") and not isinstance(getattr(module, name), type) and hasattr(getattr(module, name), "setup") and hasattr(getattr(module, name), "get_loggers")}


def _expected_facts(device: str) -> "_ExpectedFacts":
    # What buildgen alone derives for the device (its boot sequence among them), written beside the module.
    with open(f"build/generated_src/sensortask_{device}_expected.json") as f:
        facts: _ExpectedFacts = json.load(f)
    return facts


def _fresh_board(device: str) -> "ModuleType":
    # A new board for each boot: no bus or interface of an earlier one, then the device's own plan, then its module.
    machine.reset_peripherals()
    network.reset_interfaces()
    machine.configure_wiring(wiring_plan(device))
    return load_device(device)


def _next_test_port() -> int:
    assert _ports is not None, "register_for_device() must run before any scenario calls _next_test_port()"
    return _ports.next()


@_register_param("boot_sequence_matches_the_generated_expectation")
def _scenario_boot_sequence(device: str) -> None:
    # The real main() up to the supervisor, every setup() doing its real chip I/O on the twin: exactly the sequence
    # buildgen derived, the first NTP sync after the timer starts, and the boot never near the watchdog's timeout.
    async def scenario() -> None:
        cfg_path = _tmp_cfg_dir()
        write_offline_ntp_config(cfg_path)
        write_error_level_config(cfg_path)
        module = _fresh_board(device)
        await module.build_system(watchdog=boot_entry_watchdog(module, device), cfg_path=cfg_path, debug=ERROR_LEVEL, web_host="127.0.0.1", web_port=0)
        recorder = BootRecorder(module)  # it names its classes from a built module
        module = _fresh_board(device)
        module.__dict__["webserver"] = None  # the global the runner's wait reads: this boot's, not the build's above
        watchdog = boot_entry_watchdog(module, device)
        main_task = asyncio.get_event_loop().create_task(module.main(watchdog=watchdog, cfg_path=cfg_path, debug=ERROR_LEVEL, web_host="127.0.0.1", web_port=_next_test_port()))
        try:
            # The runner's own steps between build_system() and the setups: a UART link's bounded pollers, as on CI.
            await run_generic_integration._wait_until_built(module)
            # The runner's _Plan and tests' TwinWiringPlan type the one wiring-plan JSON from each side (the twin
            # cannot import the tests' type), so the plan crosses that boundary by a cast.
            plan: _Plan = cast("_Plan", wiring_plan(device))
            run_generic_integration._wire_uart_crossover(module, plan)
            await main_task
        except Exception as e:
            if not recorder.stopped_by(e):
                raise
        else:
            raise AssertionError("main() returned")
        finally:
            recorder.restore()
            if not main_task.done():
                await cancel(main_task)
        entries = recorder.entries()
        assert entries == expected_entries(_expected_facts(device)["boot_sequence"]), entries
        assert entries.index(("call", "ntp_force_sync")) > entries.index(("return", "start_timers")), entries
        assert watchdog.would_have_triggered_count == 0

    run_timed(scenario(), timeout_s=_RUN_TIMEOUT_S)


@_register_param("build_system_boots_against_the_real_twin_buses_without_exception")
def _scenario_boots_against_real_twin_buses(device: str) -> None:
    # Every FRAM chunk (Part A.7) allocates against the twin's real chip fakes. The names come from the device's plan
    # (each bus it declares) and buildgen's construction list, and exactly those globals hold a constructed module.
    async def scenario() -> None:
        module = await _boot_device(_next_test_port(), device)
        plan = wiring_plan(device)
        construction = _expected_facts(device)["boot_sequence"]["construction"]
        unmatched = [driver for driver in plan["instances"] if not any(name == driver or name.startswith(driver + "_") for name in construction)]
        assert unmatched == [], f"plan instances {unmatched} have no construction in the expected facts"
        assert_named_modules_constructed(module, tuple(sorted(set(plan["pins"]) | set(construction) | set(_MAINTENANCE))))
        assert _constructed_names(module) == set(construction) | {"webserver"}, sorted(_constructed_names(module))

    run_timed(scenario(), timeout_s=_RUN_TIMEOUT_S)


@_register_param("irq_pins_are_shared_by_chip_fake_and_driver")
def _scenario_irq_pins_shared(device: str) -> None:
    # Each IRQ line the plan wires is one Pin object, held by the booted reader and driven by its chip fake; the
    # ISL29125 INT line idles high (open drain with a pull-up, datasheet p6).
    plan = wiring_plan(device)
    wired = [(bus, attachment) for bus, attachments in sorted(plan["buses"].items()) for attachment in attachments if "irq_pin" in attachment]
    if not wired:
        raise microtest.Skip(f"{device} declares no IRQ-wired chip")

    async def scenario() -> None:
        module = await _boot_device(_next_test_port(), device)
        for bus, attachment in wired:
            driver = attachment["driver"]
            assert driver in _IRQ_ATTRIBUTES, f"no IRQ attribute known for {driver}: add it to _IRQ_ATTRIBUTES"
            reader_attribute, chip_attribute = _IRQ_ATTRIBUTES[driver]
            reader = getattr(module, driver + ("_" + attachment["name_ext"] if attachment["name_ext"] else ""))
            line = machine.Pin(attachment["irq_pin"])
            assert getattr(reader, reader_attribute) is line, (driver, attachment)
            assert getattr(getattr(module, bus)._i2c.devices[attachment["address"]], chip_attribute) is line, (driver, attachment)
            if driver == "isl29125":
                assert line.value() == 1, f"{device}'s ISL29125 INT line reads {line.value()} at idle"

    run_timed(scenario(), timeout_s=_RUN_TIMEOUT_S)


@_register_param("load_device_returns_the_devices_own_generated_module")
def _scenario_load_device_returns_the_generated_module(device: str) -> None:
    # The one loader the twin files share: the device's generated module, and a device the generator never wrote refused.
    assert load_device(device).__name__ == f"sensortask_{device}"
    try:
        load_device(device + "-not-generated")
    except AssertionError as e:
        assert "is not a generated device" in str(e), e
    else:
        raise AssertionError("load_device() accepted a device the generator never wrote")


def _tmp_cfg_dir() -> str:
    assert _scratch is not None, "register_for_device() must run before any scenario calls _tmp_cfg_dir()"
    return _scratch.dir()


def _wall() -> "_wall_clock.WallClock | ModuleType":
    # The wall clock a module reads: the twin's once installed, else the built-in time.
    return _wall_clock.installed() or time


class DrivenWall(DrivenTime):
    # DrivenTime's ticks and sleeps; time(), gmtime() and localtime() as each module read them before it: the twin wall
    # clock once installed, its steps included, else the built-in (agent, 2026-10-27).
    def gmtime(self, *secs: int) -> "tuple[int, ...]":
        return tuple(_wall().gmtime(*secs))

    def localtime(self, *secs: int) -> "tuple[int, ...]":
        return tuple(_wall().localtime(*secs))

    def time(self) -> int:
        return int(_wall().time())


# ---------------------------------------------------------------------------
# Registration: one test_<scenario> per scenario, for whichever single device the caller names -
# microtest.py discovers every callable in globals() named test_*, the only parametrization mechanism
# available here (Part E.1).
#
# fn is bound as a default-argument value rather than read from the loop variable, or every generated test
# would share the same last-iteration fn.
# ---------------------------------------------------------------------------


def load_device(device: str) -> "ModuleType":
    # The one loader of a device's generated module the twin files share (its named import, SPECIFICATION.md F.1).
    devices = generated_devices()
    if device not in devices:
        raise AssertionError(f"{device!r} is not a generated device {devices!r}")
    return __import__(f"sensortask_{device}")


def register_for_device(device: str) -> "dict[str, Callable[[], None]]":
    global _scratch, _ports
    assert device in generated_devices(), f"{device!r} is not a generated device {generated_devices()!r}"
    defined = sorted(name for name in globals() if name.startswith("_scenario_"))
    assert len(defined) == len(_PARAM_SCENARIOS), f"{len(defined)} _scenario_* functions, {len(_PARAM_SCENARIOS)} registered: one lacks its @_register_param"
    _scratch = TmpScratch(f"dtcs_{device}")
    _ports = PortAllocator("_digital_twin_construction_scenarios", device)

    tests: dict[str, Callable[[], None]] = {}
    for scenario_name, scenario_fn in _PARAM_SCENARIOS:

        def _make_test(fn: "Callable[[str], None]" = scenario_fn) -> "Callable[[], None]":
            def test() -> None:
                fn(device)

            return test

        tests[f"test_{scenario_name}"] = _make_test()
    return tests
