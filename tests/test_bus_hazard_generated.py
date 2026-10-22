"""Mock-tier bus-hazard coverage assembled FROM the real TOML wiring (SPECIFICATION.md Part C.8),
not hand-paired like test_bus_hazard_multi_device.py. Every device's generated wiring plan and
every I2C bus on it, discovered from build/generated_src/ - a new device needs no edit here."""

import json
import os

from _async_harness import run
from _bus_hazard_catalog import (
    I2C_HAZARD_CATALOG,
    build_bus_occupants,
    fake,
    make_i2c,
    scenario_a_write_does_not_disturb_concurrent_sibling_reads,
    scenario_all_occupants_concurrent_reads_stay_correct,
    scenario_bus_recovery_does_not_disturb_concurrent_siblings,
    scenario_each_occupant_never_touches_an_unexpected_address,
    scenario_general_call_does_not_disturb_concurrent_siblings,
    scenario_same_occupant_own_write_does_not_disturb_own_concurrent_read,
    spi_adapter_for,
)
from _generated_tree import require_fresh

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable

    from _bus_hazard_catalog import BusOccupant
    from _twin_devices import I2CAttachment, SpiAttachment, TwinWiringPlan
    from machine import I2C as FakeI2C


def _generated_src_dir() -> str:
    # tests/ runs as the Unix-port interpreter's cwd == repo root (scripts/test.sh's own
    # convention - every existing tests/test_*.py that reads build/generated_src/ already assumes
    # this), so a plain relative path matches every other file's own convention here.
    return "build/generated_src"


def _all_device_wiring_plans() -> "list[tuple[str, TwinWiringPlan]]":
    # (device, plan) for every generated device: whichever wiring plans the generator wrote, never a hand-kept list.
    # os.listdir() and "/" joins: the Unix-port test build has no glob module and its os no os.path.
    require_fresh()
    src_dir = _generated_src_dir()
    filenames = sorted(f for f in os.listdir(src_dir) if f.startswith("sensortask_") and f.endswith("_wiring_plan.json"))
    plans = []
    for filename in filenames:
        with open(f"{src_dir}/{filename}") as f:
            plan = json.load(f)
        plans.append((plan["device"], plan))
    assert plans, f"no *_wiring_plan.json found under {_generated_src_dir()!r} - did scripts/_generate_sensortask_modules.py run first?"
    return plans


def _port_id_for_bus(bus_name: str) -> int:
    # Bus names are the TOML's own bus keys ("i2c0", "spi0", ... - buildgen.twin_wiring.compute_twin_wiring()'s
    # "buses" and "spi" keys), so the trailing digit IS the hardware port id, not a separate fact to keep.
    kind = bus_name.rstrip("0123456789")
    assert kind in ("i2c", "spi") and bus_name[len(kind) :].isdigit(), f"unexpected bus key shape: {bus_name!r} (expected i2c<n> or spi<n>)"
    return int(bus_name[len(kind) :])


def _make_build_fresh(bus_name: str, attachments: "list[I2CAttachment]") -> "Callable[[], tuple[FakeI2C, list[BusOccupant]]]":
    port_id = _port_id_for_bus(bus_name)

    def build_fresh() -> "tuple[FakeI2C, list[BusOccupant]]":
        i2c = make_i2c(port_id)
        return fake(i2c), build_bus_occupants(i2c, attachments)

    return build_fresh


def _writers(attachments: "list[I2CAttachment]") -> "list[str]":
    # Each occupant whose catalog adapter has a safe write; an occupant missing from the catalog fails in its test.
    writers = []
    for attachment in attachments:
        adapter = I2C_HAZARD_CATALOG.get(attachment["driver"])
        if adapter is not None and adapter.write_once is not None:
            writers.append(attachment["driver"])
    return writers


def _register_write_tests(namespace: "dict[str, object]", prefix: str, bus_name: str, attachments: "list[I2CAttachment]") -> None:
    # One test per writer; a bus with no writer gets the one test that reports SKIP with the catalog's reason.
    writers: list[str | None] = list(_writers(attachments))
    for writer in writers or [None]:

        def test_a_write_does_not_disturb_concurrent_sibling_reads_across_timing_offsets(writer: "str | None" = writer) -> None:
            run(scenario_a_write_does_not_disturb_concurrent_sibling_reads(_make_build_fresh(bus_name, attachments), writer=writer))

        name = "config" if writer is None else writer
        namespace[f"{prefix}_a_{name}_write_does_not_disturb_concurrent_sibling_reads_across_timing_offsets"] = test_a_write_does_not_disturb_concurrent_sibling_reads_across_timing_offsets


def _register_bus_tests(namespace: "dict[str, object]", device: str, bus_name: str, attachments: "list[I2CAttachment]") -> None:
    prefix = f"test_{device}_{bus_name}"
    port_id = _port_id_for_bus(bus_name)

    def test_each_real_occupant_never_touches_an_unexpected_address() -> None:
        run(scenario_each_occupant_never_touches_an_unexpected_address(attachments))

    namespace[f"{prefix}_each_real_occupant_never_touches_an_unexpected_address"] = test_each_real_occupant_never_touches_an_unexpected_address

    def test_same_occupant_own_write_does_not_disturb_own_concurrent_read_across_timing_offsets() -> None:
        # A same-DEVICE hazard, not cross-occupant, so it applies even to a lone occupant on its own bus,
        # the shape test_bus_hazard_multi_device.py's byte-exact proofs cover. Hence generated
        # unconditionally, unlike the cross-occupant scenarios below, which need two real occupants.
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

    _register_write_tests(namespace, prefix, bus_name, attachments)

    def test_general_call_broadcast_does_not_disturb_concurrent_siblings_across_timing_offsets() -> None:
        run(scenario_general_call_does_not_disturb_concurrent_siblings(_make_build_fresh(bus_name, attachments)))

    namespace[f"{prefix}_general_call_broadcast_does_not_disturb_concurrent_siblings_across_timing_offsets"] = test_general_call_broadcast_does_not_disturb_concurrent_siblings_across_timing_offsets

    def test_a_bus_recovery_does_not_disturb_concurrent_sibling_reads_across_timing_offsets() -> None:
        run(scenario_bus_recovery_does_not_disturb_concurrent_siblings(_make_build_fresh(bus_name, attachments)))

    namespace[f"{prefix}_a_bus_recovery_does_not_disturb_concurrent_sibling_reads_across_timing_offsets"] = test_a_bus_recovery_does_not_disturb_concurrent_sibling_reads_across_timing_offsets


def _register_spi_bus_tests(namespace: "dict[str, object]", device: str, bus_name: str, attachments: "list[SpiAttachment]") -> None:
    # A lone SPI occupant's same-device hazards live with its driver (test_asy_fram_driver.py); a shared SPI bus
    # needs every occupant in SPI_HAZARD_CATALOG first, and this test names the one missing.
    _port_id_for_bus(bus_name)
    if len(attachments) < 2:
        return

    def test_every_spi_occupant_has_a_hazard_adapter() -> None:
        for attachment in attachments:
            spi_adapter_for(attachment["driver"])

    namespace[f"test_{device}_{bus_name}_every_spi_occupant_has_a_hazard_adapter"] = test_every_spi_occupant_has_a_hazard_adapter


for _device, _plan in _all_device_wiring_plans():
    for _bus_name, _attachments in _plan["buses"].items():
        _register_bus_tests(globals(), _device, _bus_name, _attachments)
    _spi_buses: "dict[str, list[SpiAttachment]]" = {}
    for _bus_name, _attachment in _plan.get("spi", {}).items():
        _spi_buses.setdefault(_bus_name, []).append(_attachment)
    for _bus_name, _spi_attachments in _spi_buses.items():
        _register_spi_bus_tests(globals(), _device, _bus_name, _spi_attachments)


# ---------------------------------------------------------------------------
# Fail-loud paths: a real occupant with no tests/_bus_hazard_catalog.py adapter yet must abort with
# a clear, actionable message, never silently skip that driver's own coverage (SPECIFICATION.md Part L.5's
# "tested to the same bar as src/ code: ... full error-handling-path coverage" bar, applied here).
# ---------------------------------------------------------------------------

_UNKNOWN_ATTACHMENT: "I2CAttachment" = {"driver": "not_a_real_driver", "name_ext": "", "address": 0x50}


def test_build_bus_occupants_fails_loud_for_a_driver_with_no_catalog_adapter() -> None:
    i2c = make_i2c(1)
    try:
        build_bus_occupants(i2c, [_UNKNOWN_ATTACHMENT])
    except KeyError as e:
        assert "not_a_real_driver" in str(e)
        return
    raise AssertionError("build_bus_occupants() must fail loud for a driver with no I2C_HAZARD_CATALOG adapter")


def test_a_shared_spi_bus_fails_loud_for_a_driver_with_no_catalog_adapter() -> None:
    try:
        spi_adapter_for("not_a_real_driver")
    except KeyError as e:
        assert "not_a_real_driver" in str(e)
        return
    raise AssertionError("spi_adapter_for() must fail loud for a driver with no SPI_HAZARD_CATALOG adapter")


def test_a_bus_key_names_its_port_for_both_bus_kinds() -> None:
    assert (_port_id_for_bus("i2c1"), _port_id_for_bus("spi0")) == (1, 0)
    for bad in ("uart0", "i2c", "spix"):
        try:
            _port_id_for_bus(bad)
        except AssertionError:
            continue
        raise AssertionError(f"{bad!r} was taken for a bus key")


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
