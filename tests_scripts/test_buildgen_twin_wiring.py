"""Tests for buildgen.twin_wiring: the digital twin's wiring-plan generator - proves digital_twin/machine.py's `configure_i2c_wiring("wozi"|"dev")` correctly loads and applies the real, freshly-generated plan (no hand-maintained literal exists anymore), plus shape/JSON-round-trip checks and the two synthetic fixtures (proving generality beyond the 6 real, hand-verified devices, same spirit as test_buildgen_definitions.py)."""

import json
import sys
from pathlib import Path
from typing import Any

import pytest
from _devices import DEVICE_NAMES

from buildgen import twin_wiring
from buildgen.model import DeviceModel, InstanceSpec
from buildgen.twin_wiring import FIXED_ADDRESSES, compute_twin_wiring
from buildgen.validate import build_model


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


@pytest.fixture
def fixtures_dir(repo_root: Path) -> Path:
    return repo_root / "tests_scripts" / "buildgen_fixtures"


@pytest.fixture
def digital_twin_machine(repo_root: Path) -> Any:
    # digital_twin/machine.py has no MicroPython-only import at module scope (only individual method
    # bodies do), so plain `import machine` under this suite's own CPython/pytest process works -
    # the same cross-check approach test_buildgen_definitions.py uses against html/definitions/*.json.
    digital_twin_dir = str(repo_root / "digital_twin")
    inserted = digital_twin_dir not in sys.path
    if inserted:
        sys.path.insert(0, digital_twin_dir)
    import machine  # type: ignore[import-not-found]  # only resolvable once digital_twin_dir is on sys.path, above

    yield machine
    if inserted:
        sys.path.remove(digital_twin_dir)


# ---------------------------------------------------------------------------
# configure_i2c_wiring() actually loads the real, generated plan - not a hand-typed literal
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("device", ["wozi", "dev"])
def test_configure_i2c_wiring_loads_the_real_generated_plan(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, repo_root: Path, src_dir: Path, digital_twin_machine: Any, device: str,
) -> None:
    # configure_i2c_wiring() reads the generated wiring plan relative to cwd, as every other twin
    # consumer of that file does. This proves the load-and-apply mechanism end to end against a
    # throwaway tree under a tmp cwd, so it needs no prior run and no hand-kept literal.
    model = build_model(repo_root / "devices" / f"{device}.toml", src_dir)
    expected = compute_twin_wiring(model)
    generated_dir = tmp_path / "build" / "generated_src"
    generated_dir.mkdir(parents=True)
    (generated_dir / f"sensortask_{device}_wiring_plan.json").write_text(json.dumps(expected))
    monkeypatch.chdir(tmp_path)
    digital_twin_machine.configure_i2c_wiring(device)
    assert digital_twin_machine._wiring_plan == expected


# ---------------------------------------------------------------------------
# Shape / JSON-round-trip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_generated_plan_is_json_round_trippable(repo_root: Path, src_dir: Path, device: str) -> None:
    model = build_model(repo_root / "devices" / f"{device}.toml", src_dir)
    plan = compute_twin_wiring(model)
    assert json.loads(json.dumps(plan)) == plan


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_real_device_wires_fram_on_its_own_declared_spi_bus(repo_root: Path, src_dir: Path, device: str) -> None:
    model = build_model(repo_root / "devices" / f"{device}.toml", src_dir)
    plan = compute_twin_wiring(model)
    assert set(plan["spi"]) == {"spi0"}
    assert plan["spi"]["spi0"]["driver"] == "fram"


def test_bmp3xx_address_is_read_from_the_toml_not_the_fixed_table(repo_root: Path, src_dir: Path) -> None:
    # bmp3xx is ADDRESS_CAPABLE, not FIXED_ADDRESS - proves compute_twin_wiring() actually reads
    # spec.fields["address"] for it rather than (incorrectly) falling back to FIXED_ADDRESSES.
    model = build_model(repo_root / "devices" / "wozi.toml", src_dir)
    plan = compute_twin_wiring(model)
    bmp_attachments = [a for attachments in plan["buses"].values() for a in attachments if a["driver"] == "bmp3xx"]
    assert len(bmp_attachments) == 1
    assert bmp_attachments[0]["address"] == 0x77


def test_fixed_addresses_table_matches_the_real_drivers_own_hardware_defaults() -> None:
    # src/asy_scd30_driver.py's own _SCD30_DEFAULT_ADDR, src/asy_sgp40_driver.py's own
    # address=0x59 default, and src/asy_isl29125_driver.py's own hard-wired 0x44 (no
    # address-select pin at all) - see buildgen/twin_wiring.py's own FIXED_ADDRESSES docstring.
    assert FIXED_ADDRESSES == {"scd30": 0x61, "sgp40": 0x59, "isl29125": 0x44}


def test_twin_machine_has_no_chip_fake_for_an_unknown_driver_fails_loud(digital_twin_machine: Any) -> None:
    # _build_i2c_chip()'s analogue of the no-address-rule test below: an attachment naming a
    # driver the twin has no fake for must fail loud, not produce a bus with a missing device.
    # Driven directly, since the two sides are hand-kept in sync for one fixed driver set.
    with pytest.raises(ValueError, match=r"digital twin has no I2C chip fake for driver 'not_a_real_driver'"):
        digital_twin_machine._build_i2c_chip({"driver": "not_a_real_driver"})


def test_bus_attached_driver_with_no_address_rule_fails_loud_not_silently_miswired(monkeypatch: pytest.MonkeyPatch) -> None:
    # Guards compute_twin_wiring()'s defensive fallback: a driver added to BUS_ATTACHED_DRIVERS
    # without a matching address rule here must fail loud, never silently mis-wire the twin.

    # Unreachable through any real TOML, buildspec.py's three classification sets partitioning
    # BUS_ATTACHED_DRIVERS exhaustively, so the gap is constructed by monkeypatch - the same
    # technique the missing-buildspec-entry test uses for its own unreachable branch.
    monkeypatch.setattr(twin_wiring, "BUS_ATTACHED_DRIVERS", frozenset({"fakebus"}))
    spec = InstanceSpec(driver="fakebus", name_ext="", fields={"bus": "i2c0"}, wiring={}, order_index=0)
    model = DeviceModel(device="test", path=Path("test.toml"), doc={}, instances={("fakebus", ""): spec})
    with pytest.raises(ValueError, match=r"no address rule for bus-attached driver 'fakebus'"):
        compute_twin_wiring(model)


# ---------------------------------------------------------------------------
# Mandatory synthetic fixtures - proving generality beyond the 6 real, hand-verified devices
# (mirrors test_buildgen_definitions.py's own fixture coverage)
# ---------------------------------------------------------------------------


def test_novel_combo_fixture_wires_two_scd30_instances_on_separate_buses(fixtures_dir: Path, src_dir: Path) -> None:
    model = build_model(fixtures_dir / "novel_combo.toml", src_dir)
    plan = compute_twin_wiring(model)
    i2c0_scd30 = next(a for a in plan["buses"]["i2c0"] if a["driver"] == "scd30")
    i2c1_scd30 = next(a for a in plan["buses"]["i2c1"] if a["driver"] == "scd30")
    assert i2c0_scd30 == {"driver": "scd30", "name_ext": "primary", "address": 0x61, "irq_pin": 2}
    assert i2c1_scd30 == {"driver": "scd30", "name_ext": "secondary", "address": 0x61, "irq_pin": 10}
    # Same fixed address on two different buses - never a collision (buildgen.validate's own
    # per-bus address-collision check only scopes within one bus).
    bmp3xx = next(a for a in plan["buses"]["i2c0"] if a["driver"] == "bmp3xx")
    assert bmp3xx["address"] == 0x76  # the alternate hardwired-address-select value
    assert plan["spi"]["spi0"]["max_size"] == 0x8000


def test_multi_instance_fixture_wires_three_devices_sharing_one_bus(fixtures_dir: Path, src_dir: Path) -> None:
    model = build_model(fixtures_dir / "multi_instance.toml", src_dir)
    plan = compute_twin_wiring(model)
    assert len(plan["buses"]["i2c0"]) == 3  # scd30_a + bmp3xx_only + sgp40_b, all distinct addresses
    addresses = {a["driver"]: a["address"] for a in plan["buses"]["i2c0"]}
    assert addresses == {"scd30": 0x61, "bmp3xx": 0x76, "sgp40": 0x59}
    i2c1_addresses = {a["driver"]: a["address"] for a in plan["buses"]["i2c1"]}
    assert i2c1_addresses == {"scd30": 0x61, "sgp40": 0x59}
    assert plan["spi"]["spi0"]["max_size"] == 0x4000
