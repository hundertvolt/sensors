"""Tests for buildgen.graph: topological construction ordering by _WIRING dependency
(SPECIFICATION.md Part C.14.2's "ordering hazard #1") and cycle rejection."""

from pathlib import Path

import pytest
from _toml_fixtures import base_doc, write_doc

from buildgen.errors import BuildError
from buildgen.generate import generate_device
from buildgen.graph import build_construction_order
from buildgen.validate import build_model


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


@pytest.fixture
def ext_dir(repo_root: Path) -> Path:
    return repo_root / "ext"


def test_wozi_construction_order_matches_reference_ordering_constraints(repo_root: Path, src_dir: Path, ext_dir: Path):
    result = generate_device(repo_root / "devices" / "wozi.toml", src_dir, ext_dir)
    order = [n if isinstance(n, str) else f"{n[0]}_{n[1]}" if n[1] else n[0] for n in result.model.construction_order]
    # src/sensortask_wozi.py's own real, hand-verified construction order (SPECIFICATION.md Part
    # A.7): conn/ntp before fram/sysfunct, fram before sysfunct (SystemService's own fram= kwarg),
    # scd30 before sgp40 (comp_source), every fram-wired instance after fram, notification last
    # (signal_sink -> neopixel, and every warn_* source already built).
    assert order.index("conn") < order.index("ntp") < order.index("sysfunct")
    assert order.index("fram") < order.index("sysfunct")
    assert order.index("scd30") < order.index("sgp40")
    assert order.index("neopixel") < order.index("notification")
    assert order.index("scd30") < order.index("notification")
    assert order.index("sgp40") < order.index("notification")


def test_novel_combo_sgp40_after_its_named_comp_source(repo_root: Path, src_dir: Path, ext_dir: Path):
    fixture = repo_root / "tests_scripts" / "buildgen_fixtures" / "novel_combo.toml"
    result = generate_device(fixture, src_dir, ext_dir)
    order = result.model.construction_order
    assert order.index(("scd30", "secondary")) < order.index(("sgp40", ""))
    # comp_source is scd30_secondary, not scd30_primary - construction order must not accidentally
    # depend on primary too (there's no wiring edge to it).
    assert ("scd30", "primary") in order


def test_cycle_detection_raises(tmp_path: Path, src_dir: Path):
    # asy_sgp40_driver.py's own comp_source _WIRING requires an SCD30_Reader - can't construct a
    # real cycle with the actual driver set (SGP40 requiring SCD30 which requires SGP40 back isn't
    # expressible in real _WIRING declarations), so this drives build_construction_order() directly
    # against a synthetic DeviceModel whose two instances depend on each other.
    from buildgen.wiring import WiringField

    doc = base_doc()
    model = build_model(write_doc(tmp_path, "dev", doc), src_dir)
    a = model.instances[("scd30", "")]  # sgp40 already depends on scd30 (comp_source, base_doc's own wiring)
    a.wiring_schema = (WiringField("comp_source", "SGP40_Reader", "comp_source", True, "kwarg"),)
    a.wiring["comp_source"] = "sgp40"
    with pytest.raises(BuildError, match="cycle"):
        build_construction_order(model)
