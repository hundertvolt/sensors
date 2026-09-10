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


def test_wozi_construction_order_matches_reference_ordering_constraints(repo_root: Path, src_dir: Path, ext_dir: Path) -> None:
    result = generate_device(repo_root / "devices" / "wozi.toml", src_dir, ext_dir)
    order = [n if isinstance(n, str) else f"{n[0]}_{n[1]}" if n[1] else n[0] for n in result.model.construction_order]
    # src/sensortask_wozi.py's own real, hand-verified construction order (SPECIFICATION.md Part
    # A.7): conn/ntp before fram/sysfunct, fram before sysfunct (SystemService's own fram= kwarg),
    # scd30 before sgp40 (temperature_source/humidity_source, §2.9), every fram-wired instance
    # after fram, notification last (signal_sink -> neopixel, and every warn_* source already built).
    assert order.index("conn") < order.index("ntp") < order.index("sysfunct")
    assert order.index("fram") < order.index("sysfunct")
    assert order.index("scd30") < order.index("sgp40")
    assert order.index("neopixel") < order.index("notification")
    assert order.index("scd30") < order.index("notification")
    assert order.index("sgp40") < order.index("notification")


def test_novel_combo_sgp40_after_both_its_independently_named_sources(repo_root: Path, src_dir: Path, ext_dir: Path) -> None:
    # §2.9: temperature_source=scd30_secondary and humidity_source=scd30_primary are two
    # independent wiring edges - sgp40 must be constructed after *both*, not just one.
    fixture = repo_root / "tests_scripts" / "buildgen_fixtures" / "novel_combo.toml"
    result = generate_device(fixture, src_dir, ext_dir)
    order = result.model.construction_order
    assert order.index(("scd30", "secondary")) < order.index(("sgp40", ""))
    assert order.index(("scd30", "primary")) < order.index(("sgp40", ""))


def test_multi_instance_fixture_respects_cross_driver_dependency(repo_root: Path, src_dir: Path, ext_dir: Path) -> None:
    # Axis 9's richest corner (§10.7 item 1): sgp40_b's temperature_source is bmp3xx, not scd30 -
    # construction order must respect *that* real dependency, not just "some scd30 before sgp40".
    fixture = repo_root / "tests_scripts" / "buildgen_fixtures" / "multi_instance.toml"
    result = generate_device(fixture, src_dir, ext_dir)
    order = result.model.construction_order
    assert order.index(("scd30", "b")) < order.index(("sgp40", "a"))
    assert order.index(("bmp3xx", "only")) < order.index(("sgp40", "b"))


def test_cycle_detection_raises(tmp_path: Path, src_dir: Path) -> None:
    # No real driver's _WIRING requires SGP40_Reader as a producer - can't construct a real cycle
    # with the actual driver set (SGP40 requiring SCD30, which would need to require SGP40 back,
    # isn't expressible in real _WIRING declarations), so this drives build_construction_order()
    # directly against a synthetic DeviceModel whose two instances depend on each other.
    from buildgen.wiring import WiringField

    doc = base_doc()
    model = build_model(write_doc(tmp_path, "dev", doc), src_dir)
    a = model.instances[("scd30", "")]  # sgp40 already depends on scd30 (temperature_source/humidity_source, base_doc's own wiring)
    a.wiring_schema = (WiringField("fake_dep", "SGP40_Reader", "fake_dep", True, "kwarg"),)
    a.wiring["fake_dep"] = "sgp40"
    with pytest.raises(BuildError, match="cycle"):
        build_construction_order(model)


def test_setter_mode_wiring_on_an_instance_gates_no_construction_order(tmp_path: Path, src_dir: Path) -> None:
    # "setter" wiring is a post-construction call, so it must never contribute a dependency edge -
    # otherwise a pair of instances wiring each other by setter would deadlock the sort. Only
    # AsyConnTime declares a setter tag today, and it is mandatory infra rather than an
    # [[instance]], so this drives the sort directly against a synthetic model.
    from buildgen.wiring import WiringField

    model = build_model(write_doc(tmp_path, "dev", base_doc()), src_dir)
    scd30 = model.instances[("scd30", "")]
    # A setter edge in the direction opposite to the real dependency: a real edge here would be a
    # cycle (sgp40 already depends on scd30 for both its values), so a clean sort proves it isn't one.
    scd30.wiring_schema = (WiringField("led_target", "SGP40_Reader", "set_something", False, "setter"),)
    scd30.wiring["led_target"] = "sgp40"
    order = build_construction_order(model)
    assert order.index(("scd30", "")) < order.index(("sgp40", ""))
