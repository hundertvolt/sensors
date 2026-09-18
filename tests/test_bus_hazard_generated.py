"""Mock-tier bus-hazard coverage assembled FROM the real TOML wiring (SPECIFICATION.md Part C.8),
not hand-paired like test_bus_hazard_multi_device.py. Every device's generated wiring plan and
every I2C bus on it, discovered from build/generated_src/ - a new device needs no edit here."""

import json
import os

from _bus_hazard_catalog import (
    build_bus_occupants,
    fake,
    make_i2c,
    scenario_a_write_does_not_disturb_concurrent_sibling_reads,
    scenario_all_occupants_concurrent_reads_stay_correct,
    scenario_each_occupant_never_touches_an_unexpected_address,
    scenario_general_call_does_not_disturb_concurrent_siblings,
    scenario_same_occupant_own_write_does_not_disturb_own_concurrent_read,
)

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, TypeVar

    from _bus_hazard_catalog import BusOccupant
    from machine import I2C as FakeI2C

    T = TypeVar("T")

import asyncio


def run(coro: "Coroutine[Any, Any, T]") -> "T":
    return asyncio.run(coro)


def _generated_src_dir() -> str:
    # tests/ runs as the Unix-port interpreter's cwd == repo root (scripts/test.sh's own
    # convention - every existing tests/test_*.py that reads build/generated_src/ already assumes
    # this), so a plain relative path matches every other file's own convention here.
    return "build/generated_src"


def _all_device_wiring_plans() -> "list[tuple[str, dict[str, Any]]]":
    """(device, plan) for every real devices/*.toml - discovered from whichever wiring-plan JSONs
    scripts/_generate_sensortask_modules.py already wrote, not a hand-kept device list, so a 7th
    device is picked up with zero edits here."""
    src_dir = _generated_src_dir()
    # os.listdir() + manual filtering, not glob - MicroPython's Unix-port test build has no glob
    # module (confirmed by grep: nothing under tests/ imports it, every existing directory scan
    # here uses os.listdir(), e.g. test_ticks_rollover.py's own _SRC_DIR sweep).
    filenames = sorted(f for f in os.listdir(src_dir) if f.startswith("sensortask_") and f.endswith("_wiring_plan.json"))
    plans = []
    for filename in filenames:
        # Plain "/".join(), not os.path.join() - MicroPython's os module has no .path submodule
        # (confirmed by grep: nothing anywhere in tests/ uses it), and this only ever runs on the
        # Unix port anyway (never a real device), so there's no Windows-separator concern to guard.
        with open(f"{src_dir}/{filename}") as f:
            plan = json.load(f)
        plans.append((plan["device"], plan))
    assert plans, f"no *_wiring_plan.json found under {_generated_src_dir()!r} - did scripts/_generate_sensortask_modules.py run first?"
    return plans


def _port_id_for_bus(bus_name: str) -> int:
    # Bus names are always the literal TOML field value ("i2c0"/"i2c1", ...) - see
    # buildgen.twin_wiring.compute_twin_wiring()'s own "buses" key, which is exactly this string -
    # so the trailing digit IS the real hardware port id, not a separate fact to hand-maintain.
    assert bus_name.startswith("i2c"), f"unexpected I2C bus key shape: {bus_name!r}"
    return int(bus_name[len("i2c") :])


def _make_build_fresh(bus_name: str, attachments: "list[dict[str, Any]]") -> "Callable[[], tuple[FakeI2C, list[BusOccupant]]]":
    port_id = _port_id_for_bus(bus_name)

    def build_fresh() -> "tuple[FakeI2C, list[BusOccupant]]":
        i2c = make_i2c(port_id)
        return fake(i2c), build_bus_occupants(i2c, attachments)

    return build_fresh


def _register_bus_tests(namespace: "dict[str, object]", device: str, bus_name: str, attachments: "list[dict[str, Any]]") -> None:
    prefix = f"test_{device}_{bus_name}"
    port_id = _port_id_for_bus(bus_name)

    def test_each_real_occupant_never_touches_an_unexpected_address() -> None:
        run(scenario_each_occupant_never_touches_an_unexpected_address(attachments))

    namespace[f"{prefix}_each_real_occupant_never_touches_an_unexpected_address"] = test_each_real_occupant_never_touches_an_unexpected_address

    def test_same_occupant_own_write_does_not_disturb_own_concurrent_read_across_timing_offsets() -> None:
        # A same-DEVICE hazard, not cross-occupant - applies even to a lone occupant on its own bus
        # (test_bus_hazard_multi_device.py's own byte-exact same-device proofs cover exactly this
        # shape for SCD30/ISL29125 alone on a bus), so this is generated unconditionally, unlike the
        # cross-occupant scenarios below which need >= 2 real occupants to mean anything.
        run(scenario_same_occupant_own_write_does_not_disturb_own_concurrent_read(_make_build_fresh(bus_name, attachments)))

    namespace[f"{prefix}_same_occupant_own_write_does_not_disturb_own_concurrent_read_across_timing_offsets"] = test_same_occupant_own_write_does_not_disturb_own_concurrent_read_across_timing_offsets

    if len(attachments) < 2:
        # Nothing to interleave - a lone occupant on its own bus has no cross-sensor hazard to
        # prove anything about (the original dev/i2c1-only >= 2 scoping, generalized to every
        # device/bus).
        return

    def test_bus_membership_matches_the_real_toml_group() -> None:
        drivers = {a["driver"] for a in attachments}
        assert len(attachments) >= 2, f"{device}'s own {bus_name} no longer has 2+ real occupants ({drivers}) - this generated test group's whole point (cross-sensor hazard coverage) no longer applies"

    namespace[f"{prefix}_bus_membership_matches_the_real_toml_group"] = test_bus_membership_matches_the_real_toml_group

    def test_all_real_occupants_concurrent_reads_stay_correct_and_genuinely_interleave() -> None:
        i2c = make_i2c(port_id)
        occupants = build_bus_occupants(i2c, attachments)
        run(scenario_all_occupants_concurrent_reads_stay_correct(fake(i2c), occupants))

    namespace[f"{prefix}_all_real_occupants_concurrent_reads_stay_correct_and_genuinely_interleave"] = test_all_real_occupants_concurrent_reads_stay_correct_and_genuinely_interleave

    def test_a_config_write_does_not_disturb_concurrent_sibling_reads_across_timing_offsets() -> None:
        run(scenario_a_write_does_not_disturb_concurrent_sibling_reads(_make_build_fresh(bus_name, attachments)))

    namespace[f"{prefix}_a_config_write_does_not_disturb_concurrent_sibling_reads_across_timing_offsets"] = test_a_config_write_does_not_disturb_concurrent_sibling_reads_across_timing_offsets

    def test_general_call_broadcast_does_not_disturb_concurrent_siblings_across_timing_offsets() -> None:
        run(scenario_general_call_does_not_disturb_concurrent_siblings(_make_build_fresh(bus_name, attachments)))

    namespace[f"{prefix}_general_call_broadcast_does_not_disturb_concurrent_siblings_across_timing_offsets"] = test_general_call_broadcast_does_not_disturb_concurrent_siblings_across_timing_offsets


for _device, _plan in _all_device_wiring_plans():
    for _bus_name, _attachments in _plan["buses"].items():
        _register_bus_tests(globals(), _device, _bus_name, _attachments)


# ---------------------------------------------------------------------------
# Fail-loud paths: a real occupant with no tests/_bus_hazard_catalog.py adapter yet must abort with
# a clear, actionable message, never silently skip that driver's own coverage (SPECIFICATION.md Part L.5's
# "tested to the same bar as src/ code: ... full error-handling-path coverage" bar, applied here).
# ---------------------------------------------------------------------------

_UNKNOWN_ATTACHMENT = {"driver": "not_a_real_driver", "name_ext": "", "address": 0x50}


def test_build_bus_occupants_fails_loud_for_a_driver_with_no_catalog_adapter() -> None:
    i2c = make_i2c(1)
    try:
        build_bus_occupants(i2c, [_UNKNOWN_ATTACHMENT])
    except KeyError as e:
        assert "not_a_real_driver" in str(e)
        return
    raise AssertionError("build_bus_occupants() must fail loud for a driver with no I2C_HAZARD_CATALOG adapter")


def test_address_sweep_scenario_fails_loud_for_a_driver_with_no_catalog_adapter() -> None:
    try:
        run(scenario_each_occupant_never_touches_an_unexpected_address([_UNKNOWN_ATTACHMENT]))
    except KeyError as e:
        assert "not_a_real_driver" in str(e)
        return
    raise AssertionError("scenario_each_occupant_never_touches_an_unexpected_address() must fail loud for a driver with no I2C_HAZARD_CATALOG adapter")


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
