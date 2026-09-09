"""End-to-end tests: buildgen.generate.generate_device() against all 6 real devices/*.toml plus
the mandatory synthetic "novel combination" fixture (BUILD_CHAIN_PLAN.md's acceptance criteria
#2) - proving the full pipeline (validate -> topological sort -> code generation) succeeds from
one TOML file with zero code changes elsewhere. Correctness proof scope (documented in this
session's PR description): generated output is syntactically valid Python matching the documented
construction-order/wiring shape, checked via ast.parse() and structural inspection - not executed
under a real interpreter (Session 5's digital-twin generalization is what actually boots a
generated module)."""

import ast
from pathlib import Path

import pytest
from _toml_fixtures import base_doc, write_doc

from buildgen.errors import BuildError
from buildgen.generate import generate_device

DEVICE_NAMES = ["dev", "wozi", "arzi", "klkizi", "grkizi", "schlafzi"]


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


@pytest.fixture
def ext_dir(repo_root: Path) -> Path:
    return repo_root / "ext"


@pytest.fixture
def fixtures_dir(repo_root: Path) -> Path:
    return repo_root / "tests_scripts" / "buildgen_fixtures"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_generates_syntactically_valid_module(repo_root: Path, src_dir: Path, ext_dir: Path, device: str):
    result = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir)
    tree = ast.parse(result.module_source, filename=f"sensortask_{device}.py")
    assert any(isinstance(n, ast.AsyncFunctionDef) and n.name == "build_system" for n in tree.body)
    assert any(isinstance(n, ast.AsyncFunctionDef) and n.name == "main" for n in tree.body)
    ast.parse(result.boot_entry_source, filename=f"{device}_boot.py")


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_boot_entry_imports_the_right_module(repo_root: Path, src_dir: Path, ext_dir: Path, device: str):
    result = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir)
    assert f"from sensortask_{device} import main" in result.boot_entry_source


def test_novel_combo_fixture_generates_successfully(fixtures_dir: Path, src_dir: Path, ext_dir: Path):
    # The mandatory synthetic "novel combination" fixture (BUILD_CHAIN_PLAN.md's acceptance
    # criteria #2): existing drivers mixed in a layout none of the 6 real devices use (two SCD30s,
    # SGP40 compensated from the second one, BMP3xx at the alternate address, a partial
    # notification signal set) - proving the generator's generality, not just the 6 hand-verified
    # real files.
    result = generate_device(fixtures_dir / "novel_combo.toml", src_dir, ext_dir)
    ast.parse(result.module_source)
    ast.parse(result.boot_entry_source)
    assert "scd30_primary" in result.module_source
    assert "scd30_secondary" in result.module_source
    assert "SGP40_Reader(i2c1, scd30_secondary" in result.module_source
    # Only warn_co2 is wired - warn_voc/warn_hum must not appear at all.
    assert "WarnCO2" in result.module_source
    assert "WarnVOC" not in result.module_source
    assert "WarnHum" not in result.module_source


def test_novel_combo_construction_order_is_topologically_valid(fixtures_dir: Path, src_dir: Path, ext_dir: Path):
    result = generate_device(fixtures_dir / "novel_combo.toml", src_dir, ext_dir)
    order = result.model.construction_order
    assert order.index(("scd30", "secondary")) < order.index(("sgp40", ""))
    assert order.index(("fram", "")) < order.index(("scd30", "primary"))
    assert order.index(("neopixel", "")) < order.index(("notification", ""))


def test_device_without_notification_or_neopixel_omits_their_wiring(tmp_path: Path, src_dir: Path, ext_dir: Path):
    doc = base_doc()
    doc["instance"] = [i for i in doc["instance"] if i["driver"] not in ("neopixel", "notification")]
    del doc["device"]["wiring"]["led_target"]
    result = generate_device(write_doc(tmp_path, "minimal", doc), src_dir, ext_dir)
    ast.parse(result.module_source)
    assert "notification_led=" not in result.module_source
    assert "notification_pause=" not in result.module_source
    assert '"notification":' not in result.module_source.split("status_sources=")[1].split("\n")[0] if "status_sources=" in result.module_source else True


def test_device_without_sgp40_omits_maintenance_sensors(tmp_path: Path, src_dir: Path, ext_dir: Path):
    doc = base_doc()
    doc["instance"] = [i for i in doc["instance"] if i["driver"] != "sgp40"]
    del doc["instance"][0]["wiring"]  # nothing else references sgp40's comp_source now
    result = generate_device(write_doc(tmp_path, "nosgp40", doc), src_dir, ext_dir)
    ast.parse(result.module_source)
    assert "maintenance_sensors=" not in result.module_source


def test_build_error_reports_device_and_field(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    del doc["device"]["hotspot_time_min"]
    path = write_doc(tmp_path, "broken_device", doc)
    with pytest.raises(BuildError) as exc_info:
        generate_device(path, src_dir)
    assert "broken_device" in str(exc_info.value)
    assert "hotspot_time_min" in str(exc_info.value)
