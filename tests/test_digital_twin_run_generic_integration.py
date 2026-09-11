"""Unit tests for digital_twin/run_generic_integration.py: parse_args() (pure), _collect_chips() (the generalized fault/hang chip lookup), _soak() resilience, and one real end-to-end smoke boot (now exercising --soak too, ported from run_wozi_integration.py's own equivalent test - BUILD_CHAIN_PLAN.md's Session 6.2 retired that file and run_dev_integration.py outright in favor of this one, now-fully-capable generic entry point).
The smoke test reuses the hand-written sensortask_wozi module plus machine's own "wozi" legacy plan (JSON-dumped to a temp file), not a real buildgen-generated module - buildgen needs tomllib/CPython and can't run inside this MicroPython process at all; proving a genuinely *generated* module boots is tests_scripts/test_digital_twin_generated_boot.py's job instead. This file only proves run_generic_integration.py's own generic machinery works, using a well-understood module as the payload."""

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
from run_generic_integration import RunConfig, _collect_chips, _soak, main, parse_args


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


def test_parse_args_soak_defaults_to_disabled() -> None:
    # A bare, no-flags run is the plain "launch the twin and serve forever" path - soak only opts
    # in via --soak/--soak-cycles below. Ported from run_wozi_integration.py's own identical test
    # (BUILD_CHAIN_PLAN.md's Session 6.2 - that file and run_dev_integration.py are both retired now
    # that this generic entry point carries their own soak machinery too).
    config = parse_args(["--module", "m", "--wiring-plan", "p.json"])
    assert config.soak is False
    assert config.soak_cycles == 20


def test_parse_args_soak_flag_enables_soak_with_the_default_cycle_count() -> None:
    config = parse_args(["--module", "m", "--wiring-plan", "p.json", "--soak"])
    assert config.soak is True
    assert config.soak_cycles == 20


def test_parse_args_soak_cycles_implies_soak() -> None:
    # Passing a cycle count is itself opting into running the soak - no need to also pass --soak.
    config = parse_args(["--module", "m", "--wiring-plan", "p.json", "--soak-cycles", "5"])
    assert config.soak is True
    assert config.soak_cycles == 5


# ---------------------------------------------------------------------------
# _soak() resilience - regression coverage for a real crash found via a real user report running
# this exact soak against the real assembled system, ported verbatim from
# run_wozi_integration.py's own identical test (BUILD_CHAIN_PLAN.md's Session 6.2): src/
# asy_webserver_service.py's own max_connections=4 reject-when-full path
# (WebserverService._serve()) closes a rejected connection immediately with zero response ever
# written, by design (BACKLOG.md's own "reject-when-full" decision) - a real client hitting it sees
# an ECONNRESET (or an EOF-before-any-bytes, depending on the OS/kernel's own close-with-unread-data
# semantics) with no HTTP-level response at all. The real server already tolerates this kind of
# failure gracefully; _soak() must record it as one soak failure among many, never raise and crash
# the whole diagnostic run.
# ---------------------------------------------------------------------------


async def _reset_immediately_server(_reader: "asyncio.StreamReader", writer: "asyncio.StreamWriter") -> None:
    # Never reads the request, never writes a response, closes immediately - the same "closed with
    # nothing written at all" shape WebserverService._serve()'s own reject-when-full path produces
    # (its own _close_writer() helper: writer.close() then await writer.wait_closed()).
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
        assert failures  # every single request (warmup and main cycle alike) failed - some
        # failure must have been recorded, not silently dropped
        assert any("warmup" in f for f in failures)
        assert any("cycle 0" in f for f in failures)

    run_timed(scenario(), timeout_s=15.0)


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
# wired from a JSON-dumped copy of machine's own "wozi" legacy plan, running a tiny bounded soak
# with one real injected fault - the same combined shape run_wozi_integration.py's own now-retired
# main() smoke test used (BUILD_CHAIN_PLAN.md's Session 6.2: that file and run_dev_integration.py
# are both gone now that this generic entry point carries their own soak machinery too).
# Deliberately exactly one such test, not two (a soak-only one plus a separate fault-injection
# one): main()'s own real supervisor (sensortask_wozi.main()/start_and_check_tasks()) leaves
# several real background tasks running after main()'s own main_task.cancel() - the same orphaned-
# task memory-pressure bug tests/test_digital_twin_sensortask_integration.py's own module docstring
# already documents in full. digital_twin/launch.py's own test file has exactly one such smoke test
# for the identical reason - matched here, not reinvented.
# ---------------------------------------------------------------------------


def test_main_runs_a_tiny_bounded_soak_with_an_injected_fault_and_returns_a_clean_summary() -> None:
    # soak_cycles is deliberately tiny, unlike a real soak run (run_generic_integration.py's own
    # default is 20) - this is a smoke test, not a real soak, and the memory-flat check's fixed
    # tolerance needs far more real cycles than fit a fast smoke test to reliably average out
    # ordinary per-connection allocator noise (confirmed directly against the now-retired
    # run_wozi_integration.py's own identical test: a real run at this small cycle count produced a
    # false-positive-shaped gc.mem_free() dip). The endpoint-reachability and watchdog signals are
    # meaningful even at this tiny scale, so this only excludes that one specific, scale-sensitive
    # failure message.
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
        soak=True,
        soak_cycles=2,
        duration=0.0,
        faults=[("sgp40", "writeto", 2)],
    )
    try:
        # _SOAK_WARMUP_CYCLES (40) adds real HTTP round trips ahead of this test's own tiny
        # soak_cycles - 30s wasn't enough once that warm-up landed (same finding
        # run_wozi_integration.py's own now-retired identical test already made).
        summary = run_timed(main(config), timeout_s=60.0)
    finally:
        try:
            os.remove(plan_path)
        except OSError:
            pass
    non_memory_failures = [f for f in summary["failures"] if "gc.mem_free()" not in f]
    assert non_memory_failures == []
    assert summary["would_have_triggered_count"] == 0


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
