"""Tests for buildgen.validate: the full fail-loud validation pass (BUILD_CHAIN_PLAN.md's
"Build/generator script quality bar"). Every abort condition gets its own test, driven by a
deliberately malformed fixture built from _toml_fixtures.base_doc() - never just incidentally
exercised by the six real device TOMLs happening to be valid."""

from pathlib import Path

import pytest
from _toml_fixtures import base_doc, write_doc, write_text

from buildgen.errors import BuildError
from buildgen.validate import build_model


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


def _build(tmp_path: Path, src_dir: Path, doc: dict, name: str = "dev"):
    return build_model(write_doc(tmp_path, name, doc), src_dir)


def test_base_doc_is_valid(tmp_path: Path, src_dir: Path):
    _build(tmp_path, src_dir, base_doc())  # no raise


def test_malformed_toml_syntax(tmp_path: Path, src_dir: Path):
    path = write_text(tmp_path, "dev", "this is not [valid toml\n")
    with pytest.raises(BuildError, match="not valid TOML"):
        build_model(path, src_dir)


def test_missing_device_table(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    del doc["device"]
    with pytest.raises(BuildError, match=r"missing \[device\] table"):
        _build(tmp_path, src_dir, doc)


@pytest.mark.parametrize("field", ["name", "hostname", "hotspot_password", "conn_fail_to_hotspot", "hotspot_time_min"])
def test_missing_required_device_field(tmp_path: Path, src_dir: Path, field: str):
    doc = base_doc()
    del doc["device"][field]
    with pytest.raises(BuildError, match=f"missing required field {field!r}"):
        _build(tmp_path, src_dir, doc)


def test_device_int_field_wrong_type(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    doc["device"]["conn_fail_to_hotspot"] = "five"
    with pytest.raises(BuildError, match="must be an int"):
        _build(tmp_path, src_dir, doc)


def test_device_bool_rejected_for_int_field(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    doc["device"]["hotspot_time_min"] = True
    with pytest.raises(BuildError, match="must be an int"):
        _build(tmp_path, src_dir, doc)


def test_hostname_mismatch(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    doc["device"]["hostname"] = "WrongName"
    with pytest.raises(BuildError, match="expected 'SensorStationTest'"):
        _build(tmp_path, src_dir, doc)


def test_no_bus_table(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    doc["bus"] = {}
    with pytest.raises(BuildError, match=r"no \[bus\.\*\] table declared"):
        _build(tmp_path, src_dir, doc)


def test_bus_missing_required_wire_pin(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    del doc["bus"]["i2c0"]["scl_pin"]
    with pytest.raises(BuildError, match="missing required field 'scl_pin'"):
        _build(tmp_path, src_dir, doc)


def test_bus_cs_pin_on_shared_bus_rejected(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    doc["bus"]["i2c0"]["cs_pin"] = 9
    with pytest.raises(BuildError, match="cs_pin"):
        _build(tmp_path, src_dir, doc)


def test_i2c_bus_missing_frequency(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    del doc["bus"]["i2c0"]["frequency"]
    with pytest.raises(BuildError, match="missing an int frequency"):
        _build(tmp_path, src_dir, doc)


def test_spi_bus_declares_frequency(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    doc["bus"]["spi0"]["frequency"] = 50000
    with pytest.raises(BuildError, match="has no such parameter"):
        _build(tmp_path, src_dir, doc)


def test_unknown_driver(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    doc["instance"][0]["driver"] = "not_a_real_chip"
    with pytest.raises(BuildError, match="unknown driver"):
        _build(tmp_path, src_dir, doc)


def test_instance_missing_required_field(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    del doc["instance"][0]["irq_pin"]
    with pytest.raises(BuildError, match="missing required field 'irq_pin'"):
        _build(tmp_path, src_dir, doc)


def test_instance_references_undeclared_bus(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    doc["instance"][0]["bus"] = "i2c9"
    with pytest.raises(BuildError, match="undeclared bus"):
        _build(tmp_path, src_dir, doc)


def test_address_field_on_driver_without_address_select_pin(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    doc["instance"][0]["address"] = 0x61  # scd30 has no real address-select pin
    with pytest.raises(BuildError, match="no address-select pin"):
        _build(tmp_path, src_dir, doc)


def test_declared_bus_never_used(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    doc["bus"]["i2c1"] = {"scl_pin": 20, "sda_pin": 21, "frequency": 50000}
    with pytest.raises(BuildError, match="declared but never referenced"):
        _build(tmp_path, src_dir, doc)


def test_duplicate_driver_name_ext_pair(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    dup = dict(doc["instance"][0])
    doc["instance"].append(dup)
    with pytest.raises(BuildError, match="duplicate \\[\\[instance\\]\\] entry"):
        _build(tmp_path, src_dir, doc)


def test_instance_name_collision_via_distinct_drivers_same_resolved_name(tmp_path: Path, src_dir: Path):
    # Two genuinely different [[instance]] entries (different drivers, so the (driver, name_ext)
    # dedup in model.load_device() doesn't catch it) that still resolve to the same
    # instance_name() - real drivers' _NAME constants never collide this way today (each is a
    # distinct all-caps token), so this drives validate._check_instance_name_collisions() directly
    # against a synthetic model, the same way test_buildgen_graph.py's cycle test does.
    from buildgen.model import DeviceModel, InstanceSpec
    from buildgen.validate import _check_instance_name_collisions

    model = DeviceModel("dev", tmp_path / "dev.toml", {})
    model.instances[("a", "")] = InstanceSpec("a", "", {}, {}, 0, resolved_name="SAME")
    model.instances[("b", "")] = InstanceSpec("b", "", {}, {}, 1, resolved_name="SAME")
    with pytest.raises(BuildError, match="instance_name collision"):
        _check_instance_name_collisions(model)


def test_singleton_service_declared_twice(tmp_path: Path, src_dir: Path):
    # A singleton service is always forced to name_ext="" (see the next test), so two declarations
    # of the same one always collide as an exact-duplicate [[instance]] entry - caught by
    # model.load_device()'s own (driver, name_ext) dedup before the singleton-specific check even
    # runs (SPECIFICATION.md Part C.14's "never more than one per device by construction").
    doc = base_doc()
    second_fram = {"driver": "fram", "bus": "spi0", "cs_pin": 22, "max_size": 1024}
    doc["instance"].append(second_fram)
    with pytest.raises(BuildError, match="duplicate \\[\\[instance\\]\\] entry"):
        _build(tmp_path, src_dir, doc)


def test_singleton_service_with_name_ext_rejected(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    for inst in doc["instance"]:
        if inst["driver"] == "fram":
            inst["name_ext"] = "extra"
    with pytest.raises(BuildError, match="must not declare name_ext"):
        _build(tmp_path, src_dir, doc)


def test_global_gpio_pin_collision_bus_vs_instance(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    doc["instance"][3]["pin"] = doc["bus"]["i2c0"]["scl_pin"]  # neopixel pin == bus.i2c0.scl_pin
    with pytest.raises(BuildError, match="claimed twice"):
        _build(tmp_path, src_dir, doc)


def test_global_gpio_pin_collision_two_instances(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    doc["instance"][0]["irq_pin"] = doc["instance"][3]["pin"]  # scd30.irq_pin == neopixel.pin
    with pytest.raises(BuildError, match="claimed twice"):
        _build(tmp_path, src_dir, doc)


def test_per_bus_explicit_address_collision(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    doc["instance"].append({"driver": "bmp3xx", "name_ext": "", "bus": "i2c0", "address": 0x77})
    doc["instance"].append({"driver": "bmp3xx", "name_ext": "other", "bus": "i2c0", "address": 0x77})
    with pytest.raises(BuildError, match="claimed by both"):
        _build(tmp_path, src_dir, doc)


def test_per_bus_address_reuse_on_different_bus_is_legitimate(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    doc["bus"]["i2c1"] = {"scl_pin": 26, "sda_pin": 27, "frequency": 50000}
    doc["instance"].append({"driver": "bmp3xx", "name_ext": "a", "bus": "i2c0", "address": 0x77})
    doc["instance"].append({"driver": "bmp3xx", "name_ext": "b", "bus": "i2c1", "address": 0x77})
    _build(tmp_path, src_dir, doc)  # no raise - different buses, same address value is fine


def test_two_fixed_address_instances_same_driver_same_bus_collide(tmp_path: Path, src_dir: Path):
    # Neither declares an explicit address - both scd30's, hardware address is fixed, so they
    # can't be told apart on the same bus at all.
    doc = base_doc()
    doc["instance"].append({"driver": "scd30", "name_ext": "second", "bus": "i2c0", "irq_pin": 21, "trigger_sec": 3})
    with pytest.raises(BuildError, match="can't be told apart"):
        _build(tmp_path, src_dir, doc)


def test_two_fixed_address_different_drivers_same_bus_do_not_collide(tmp_path: Path, src_dir: Path):
    # scd30 and sgp40 already share bus i2c0 in base_doc() with no explicit address on either -
    # different chip types have different real fixed addresses, so this must NOT raise.
    doc = base_doc()
    _build(tmp_path, src_dir, doc)


def test_wiring_field_not_declared_by_driver(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    doc["instance"][2]["wiring"] = {"comp_source": "scd30"}  # fram has no _WIRING entry named comp_source
    with pytest.raises(BuildError, match="no matching _WIRING entry"):
        _build(tmp_path, src_dir, doc)


def test_wiring_value_not_a_string(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    doc["instance"][1]["wiring"]["comp_source"] = 42
    with pytest.raises(BuildError, match="must be a string instance reference"):
        _build(tmp_path, src_dir, doc)


def test_wiring_reference_unresolved(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    doc["instance"][1]["wiring"]["comp_source"] = "does_not_exist"
    with pytest.raises(BuildError, match="does not resolve to any declared instance"):
        _build(tmp_path, src_dir, doc)


def test_wiring_reference_wrong_class(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    doc["instance"][1]["wiring"]["comp_source"] = "fram"  # fram is AsyFramManager, not SCD30_Reader
    with pytest.raises(BuildError, match="requires a SCD30_Reader"):
        _build(tmp_path, src_dir, doc)


def test_required_wiring_field_missing(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    del doc["instance"][1]["wiring"]["comp_source"]
    with pytest.raises(BuildError, match="missing required wiring.comp_source"):
        _build(tmp_path, src_dir, doc)


def test_optional_wiring_field_absent_is_fine(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    del doc["instance"][1]["wiring"]["fram_target"]
    _build(tmp_path, src_dir, doc)  # no raise


def test_warn_signal_malformed_shape(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    doc["instance"][4]["wiring"]["warn_co2"] = "not a table"
    with pytest.raises(BuildError, match="must be a"):
        _build(tmp_path, src_dir, doc)


def test_warn_signal_source_unresolved(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    doc["instance"][4]["wiring"]["warn_co2"]["source"] = "does_not_exist"
    with pytest.raises(BuildError, match="does not resolve to any declared instance"):
        _build(tmp_path, src_dir, doc)


def test_device_wiring_unknown_field(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    doc["device"]["wiring"]["bogus_target"] = "neopixel"
    with pytest.raises(BuildError, match="unknown field"):
        _build(tmp_path, src_dir, doc)


def test_device_wiring_reference_unresolved(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    doc["device"]["wiring"]["led_target"] = "does_not_exist"
    with pytest.raises(BuildError, match="does not resolve to any declared instance"):
        _build(tmp_path, src_dir, doc)


def test_device_wiring_reference_wrong_class(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    doc["device"]["wiring"]["led_target"] = "fram"  # fram is AsyFramManager, not NeopixelDriver
    with pytest.raises(BuildError, match="requires a NeopixelDriver"):
        _build(tmp_path, src_dir, doc)


def test_device_wiring_optional_field_absent_is_fine(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    del doc["device"]["wiring"]["led_target"]
    _build(tmp_path, src_dir, doc)  # no raise


def test_requires_tag_violated(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    doc["bus"]["i2c0"]["timeout"] = 50000  # scd30's own @requires bus.timeout>=200000
    with pytest.raises(BuildError, match="does not satisfy"):
        _build(tmp_path, src_dir, doc)


def test_requires_tag_missing_bus_field(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    del doc["bus"]["i2c0"]["timeout"]
    with pytest.raises(BuildError, match="is missing field"):
        _build(tmp_path, src_dir, doc)


def test_requires_tag_satisfied(tmp_path: Path, src_dir: Path):
    doc = base_doc()
    doc["bus"]["i2c0"]["timeout"] = 250000
    _build(tmp_path, src_dir, doc)  # no raise
