"""Mock-tier bus-hazard coverage assembled FROM the real TOML wiring
(BUS_HAZARD_TEST_GENERATION_REQUIREMENTS.md), not hand-paired like test_bus_hazard_multi_device.py.
Phase 1 scope only: dev's real i2c1 three-way group - see this file's own comments for the boundary."""

import json

from _bus_hazard_catalog import (
    build_bus_occupants,
    fake,
    make_i2c,
    scenario_a_write_does_not_disturb_concurrent_sibling_reads,
    scenario_all_occupants_concurrent_reads_stay_correct,
    scenario_each_occupant_never_touches_an_unexpected_address,
    scenario_general_call_does_not_disturb_concurrent_siblings,
)

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")

import asyncio

# Deliberately hardcoded to one real device/bus for this first landing, not a loop over every
# devices/*.toml - BUS_HAZARD_TEST_GENERATION_REQUIREMENTS.md Section 6 scopes phase 1 to dev's real
# i2c1 three-way group (SCD30+SGP40+ISL29125, the only real three-way I2C sharing in any device TOML
# today) and asks to stop before extending to any other device/bus. Generalizing this into a loop
# that dynamically defines one test_<device>_<bus>_... function per real bus (reading every
# build/generated_src/sensortask_<device>_wiring_plan.json instead of just dev's) is exactly the
# named follow-on work, not done here.
_DEVICE = "dev"
_BUS = "i2c1"


def run(coro: "Coroutine[Any, Any, T]") -> "T":
    return asyncio.run(coro)


def _dev_i2c1_attachments() -> "list[dict[str, Any]]":
    # The same generated artifact tests/test_digital_twin_bus_hazard_concurrency.py's
    # machine.configure_i2c_wiring("dev") already loads for the twin tier - reading it again here
    # is deliberate reuse of one already-computed fact (buildgen.twin_wiring.compute_twin_wiring()),
    # never a second hand-maintained copy of dev's own wiring.
    with open(f"build/generated_src/sensortask_{_DEVICE}_wiring_plan.json") as f:
        plan = json.load(f)
    attachments: list[dict[str, Any]] = plan["buses"][_BUS]
    return attachments


def test_dev_i2c1_bus_membership_matches_the_real_toml_three_way_group() -> None:
    # A guard, not a duplicate of the scenarios below: if a future devices/dev.toml edit ever drops
    # this bus back to fewer than 2 real occupants, the scenarios below would silently stop proving
    # anything cross-sensor at all - fail loud here instead of letting that happen quietly.
    attachments = _dev_i2c1_attachments()
    drivers = {a["driver"] for a in attachments}
    assert len(attachments) >= 2, f"dev's own i2c1 no longer has 2+ real occupants ({drivers}) - this file's whole point (cross-sensor hazard coverage) no longer applies; see BUS_HAZARD_TEST_GENERATION_REQUIREMENTS.md"


def test_dev_i2c1_all_real_occupants_concurrent_reads_stay_correct_and_genuinely_interleave() -> None:
    i2c = make_i2c(1)  # matches dev's real i2c1 port id
    occupants = build_bus_occupants(i2c, _dev_i2c1_attachments())
    run(scenario_all_occupants_concurrent_reads_stay_correct(fake(i2c), occupants))


def test_dev_i2c1_a_config_write_does_not_disturb_concurrent_sibling_reads() -> None:
    i2c = make_i2c(1)
    occupants = build_bus_occupants(i2c, _dev_i2c1_attachments())
    run(scenario_a_write_does_not_disturb_concurrent_sibling_reads(fake(i2c), occupants))


def test_dev_i2c1_general_call_broadcast_does_not_disturb_concurrent_siblings() -> None:
    i2c = make_i2c(1)
    occupants = build_bus_occupants(i2c, _dev_i2c1_attachments())
    run(scenario_general_call_does_not_disturb_concurrent_siblings(fake(i2c), occupants))


def test_dev_i2c1_each_real_occupant_never_touches_an_unexpected_address() -> None:
    run(scenario_each_occupant_never_touches_an_unexpected_address(_dev_i2c1_attachments()))


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
