"""Tests for buildgen.twin_wiring: the digital twin's wiring-plan generator - cross-checks the two real devices' generated plans against digital_twin/machine.py's own hand-maintained `_LEGACY_WIRING_PLANS` (so the two can never silently drift apart), plus shape/JSON-round-trip checks and the two synthetic fixtures (proving generality beyond the 6 real, hand-verified devices, same spirit as test_buildgen_definitions.py)."""

import json
import sys
from pathlib import Path
from typing import Any

import pytest

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


def _sort_attachments(plan: "dict[str, Any]") -> "dict[str, Any]":
    """Normalizes a wiring plan's own bus attachment lists by address, so a real content
    difference still fails comparison but a cosmetic declaration-order difference does not."""
    return {
        "buses": {bus: sorted(attachments, key=lambda a: a["address"]) for bus, attachments in plan["buses"].items()},
        "spi": plan["spi"],
    }


# ---------------------------------------------------------------------------
# Cross-check against digital_twin/machine.py's own hand-maintained legacy plans
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("device", ["wozi", "dev"])
def test_generated_plan_matches_machines_own_legacy_plan(repo_root: Path, src_dir: Path, digital_twin_machine: Any, device: str) -> None:
    model = build_model(repo_root / "devices" / f"{device}.toml", src_dir)
    generated = compute_twin_wiring(model)
    legacy = digital_twin_machine._LEGACY_WIRING_PLANS[device]
    assert _sort_attachments(generated) == _sort_attachments(legacy)


# ---------------------------------------------------------------------------
# Shape / JSON-round-trip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("device", ["dev", "wozi", "arzi", "klkizi", "grkizi", "schlafzi"])
def test_generated_plan_is_json_round_trippable(repo_root: Path, src_dir: Path, device: str) -> None:
    model = build_model(repo_root / "devices" / f"{device}.toml", src_dir)
    plan = compute_twin_wiring(model)
    assert json.loads(json.dumps(plan)) == plan


@pytest.mark.parametrize("device", ["dev", "wozi", "arzi", "klkizi", "grkizi", "schlafzi"])
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
    # src/asy_scd30_driver.py's own _SCD30_DEFAULT_ADDR and src/asy_sgp40_driver.py's own
    # address=0x59 default - see buildgen/twin_wiring.py's own FIXED_ADDRESSES docstring.
    assert FIXED_ADDRESSES == {"scd30": 0x61, "sgp40": 0x59}


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
    assert i2c1_scd30 == {"driver": "scd30", "name_ext": "secondary", "address": 0x61, "irq_pin": 8}
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
