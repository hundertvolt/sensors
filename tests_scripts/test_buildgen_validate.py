"""Tests for buildgen.validate, the full fail-loud validation pass. Every abort condition gets its
own test, driven by a deliberately malformed fixture built from _toml_fixtures.base_doc() - never
just incidentally exercised by the six real device TOMLs happening to be valid."""

import shutil
from pathlib import Path

import pytest
from _toml_fixtures import base_doc, write_doc, write_text

from buildgen.errors import BuildError
from buildgen.model import DeviceModel
from buildgen.validate import build_model


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


def _build(tmp_path: Path, src_dir: Path, doc: dict, name: str = "dev") -> "DeviceModel":
    return build_model(write_doc(tmp_path, name, doc), src_dir)


def test_base_doc_is_valid(tmp_path: Path, src_dir: Path) -> None:
    _build(tmp_path, src_dir, base_doc())  # no raise


def test_malformed_toml_syntax(tmp_path: Path, src_dir: Path) -> None:
    path = write_text(tmp_path, "dev", "this is not [valid toml\n")
    with pytest.raises(BuildError, match="not valid TOML"):
        build_model(path, src_dir)


def test_literal_duplicate_toml_key_in_one_table_rejected(tmp_path: Path, src_dir: Path) -> None:
    # §5.1 #1's first sub-case: tomllib itself rejects a repeated key in one table before buildgen
    # ever sees the parsed doc - load_device() wraps that TOMLDecodeError into the same BuildError
    # as any other malformed-syntax input. Not exercised by any existing test until now.
    path = write_text(tmp_path, "dev", '[device]\nname = "Test"\nname = "Test2"\n')
    with pytest.raises(BuildError, match="not valid TOML"):
        build_model(path, src_dir)


def test_missing_device_table(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    del doc["device"]
    with pytest.raises(BuildError, match=r"missing \[device\] table"):
        _build(tmp_path, src_dir, doc)


@pytest.mark.parametrize("field", ["name", "hostname", "hotspot_password", "conn_fail_to_hotspot", "hotspot_time_min"])
def test_missing_required_device_field(tmp_path: Path, src_dir: Path, field: str) -> None:
    doc = base_doc()
    del doc["device"][field]
    with pytest.raises(BuildError, match=f"missing required field {field!r}"):
        _build(tmp_path, src_dir, doc)


@pytest.mark.parametrize("value", [5, 12345678, True, ["12345678"], 1.5])
def test_device_hotspot_password_wrong_type_rejected(tmp_path: Path, src_dir: Path, value: object) -> None:
    # Every other [device] field was type-checked; this one had only the bare presence check, so a
    # misformatted value built clean - the one hole in "any misformatted field must fail the build".
    doc = base_doc()
    doc["device"]["hotspot_password"] = value
    with pytest.raises(BuildError, match="hotspot_password must be a string"):
        _build(tmp_path, src_dir, doc)


@pytest.mark.parametrize("value", ["", "short", "1234567"])
def test_device_hotspot_password_too_short_rejected(tmp_path: Path, src_dir: Path, value: str) -> None:
    # 8 characters is WPA2-PSK's own minimum - below it the CYW43 can't bring the hotspot up at all.
    doc = base_doc()
    doc["device"]["hotspot_password"] = value
    with pytest.raises(BuildError, match="at least 8"):
        _build(tmp_path, src_dir, doc)


def test_device_hotspot_password_at_the_minimum_length_is_accepted(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["device"]["hotspot_password"] = "12345678"
    assert _build(tmp_path, src_dir, doc).doc["device"]["hotspot_password"] == "12345678"


def test_single_bracket_instance_table_names_the_real_mistake(tmp_path: Path, src_dir: Path) -> None:
    # [instance] instead of [[instance]] parses to a dict, whose iteration yields its keys - which
    # used to surface as "entry #0 is missing a 'driver' field", pointing at the wrong mistake.
    path = write_text(tmp_path, "dev", '[device]\nname = "Test"\n\n[instance]\ndriver = "neopixel"\npin = 15\n')
    with pytest.raises(BuildError, match=r"double brackets"):
        build_model(path, src_dir)


def test_instance_table_of_the_wrong_type_entirely_is_rejected(tmp_path: Path, src_dir: Path) -> None:
    # Top-level key, deliberately written before the [device] header so it isn't swallowed into it.
    path = write_text(tmp_path, "dev", 'instance = 5\n\n[device]\nname = "Test"\n')
    with pytest.raises(BuildError, match=r"must be an array of tables"):
        build_model(path, src_dir)


def test_device_int_field_wrong_type(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["device"]["conn_fail_to_hotspot"] = "five"
    with pytest.raises(BuildError, match="must be an int"):
        _build(tmp_path, src_dir, doc)


def test_device_bool_rejected_for_int_field(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["device"]["hotspot_time_min"] = True
    with pytest.raises(BuildError, match="must be an int"):
        _build(tmp_path, src_dir, doc)


def test_hostname_mismatch(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["device"]["hostname"] = "WrongName"
    with pytest.raises(BuildError, match="expected 'SensorStationTest'"):
        _build(tmp_path, src_dir, doc)


@pytest.mark.parametrize("bad_name", [5, ""])
def test_device_name_invalid_rejected(tmp_path: Path, src_dir: Path, bad_name: object) -> None:
    # §7.1 #9: [device].name's own type/non-emptiness check, exercised only implicitly by every
    # other fixture supplying a valid name today.
    doc = base_doc()
    doc["device"]["name"] = bad_name
    with pytest.raises(BuildError, match="non-empty string"):
        _build(tmp_path, src_dir, doc)


def test_empty_bus_table_with_bus_attached_instances_still_fails(tmp_path: Path, src_dir: Path) -> None:
    # Phase 2 (§10.3): [bus.*] being empty/absent is no longer unconditionally rejected - but
    # base_doc()'s scd30/sgp40/fram instances still reference "i2c0"/"spi0", so this now fails
    # downstream via the ordinary undeclared-bus check instead of a blanket "no bus table" error.
    doc = base_doc()
    doc["bus"] = {}
    with pytest.raises(BuildError, match="undeclared bus"):
        _build(tmp_path, src_dir, doc)


def test_no_buses_and_no_instances_is_a_valid_minimal_device(tmp_path: Path, src_dir: Path) -> None:
    # §4.3 axis 10 / §7.1 items 1-2, unblocked by Phase 2: a device with zero bus-attached
    # instances (no sensors, no FRAM at all) is a logically valid, simplest-possible shape.
    doc = base_doc()
    doc["bus"] = {}
    doc["instance"] = []
    doc["device"]["wiring"] = {}
    _build(tmp_path, src_dir, doc)  # no raise


def test_fram_entirely_absent_with_single_i2c_bus_is_fine(tmp_path: Path, src_dir: Path) -> None:
    # §7.1 items 1-2, deferred from Phase 1 pending this same relaxation: FRAM absent means spi0
    # (its sole real consumer) is also absent, leaving a single shared I2C bus with no SPI at all.
    doc = base_doc()
    doc["instance"] = [i for i in doc["instance"] if i["driver"] != "fram"]
    for inst in doc["instance"]:
        inst.get("wiring", {}).pop("fram_target", None)
    doc["device"]["wiring"].pop("fram_target", None)
    del doc["bus"]["spi0"]
    _build(tmp_path, src_dir, doc)  # no raise


def test_bus_id_with_unrecognized_kind_prefix_rejected(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["bus"]["i2c9"] = doc["bus"].pop("i2c0")
    doc["instance"][0]["bus"] = "i2c9"
    doc["instance"][1]["bus"] = "i2c9"
    with pytest.raises(BuildError, match="not a real Pico W bus"):
        _build(tmp_path, src_dir, doc)


def test_bus_id_bare_kind_with_no_port_digit_rejected(tmp_path: Path, src_dir: Path) -> None:
    # §5.1 #7/§7.2(A): "i2c" alone still starts with the recognized "i2c" prefix - the old
    # startswith()-only check let this through; the fixed real-id table closes it.
    doc = base_doc()
    doc["bus"]["i2c"] = doc["bus"].pop("i2c0")
    doc["instance"][0]["bus"] = "i2c"
    doc["instance"][1]["bus"] = "i2c"
    with pytest.raises(BuildError, match="not a real Pico W bus"):
        _build(tmp_path, src_dir, doc)


def test_two_i2c_buses_legal_topology(tmp_path: Path, src_dir: Path) -> None:
    # §4.3 axis 10: one pair from the I2C0 set, one from the I2C1 set - the same shape every real
    # device already uses (e.g. devices/wozi.toml), driven directly at the validate level here.
    doc = base_doc()
    doc["bus"]["i2c1"] = {"scl_pin": 19, "sda_pin": 18, "frequency": 50000}
    doc["instance"][1]["bus"] = "i2c1"  # sgp40 moves off the shared i2c0 bus
    _build(tmp_path, src_dir, doc)  # no raise


def test_spi1_is_a_legal_peripheral_index(tmp_path: Path, src_dir: Path) -> None:
    # spi1 is logically legal but unexercised by any real devices/*.toml today (§4.3 axis 10) -
    # `fram` (the sole real SPI-attached driver, per asy_spi_driver.py's own docstring) is a forced
    # singleton, so there's no way to have two SPI buses simultaneously *used* by real drivers; this
    # instead proves spi1 itself resolves correctly by moving the one fram instance onto it.
    doc = base_doc()
    doc["instance"][0]["irq_pin"] = 21  # free up GP8 (block8-11's MISO pin) from scd30's default
    del doc["bus"]["spi0"]
    doc["bus"]["spi1"] = {"sck_pin": 10, "mosi_pin": 11, "miso_pin": 8}  # real spi1-block pins
    doc["instance"][2]["bus"] = "spi1"  # fram
    _build(tmp_path, src_dir, doc)  # no raise


def test_i2c_pin_belonging_to_the_other_i2c_index_rejected(tmp_path: Path, src_dir: Path) -> None:
    # GP2/GP3 are a real, legal I2C pair - just I2C1's, not I2C0's. Silicon-illegal for bus.i2c0.
    doc = base_doc()
    doc["bus"]["i2c0"]["scl_pin"] = 3
    doc["bus"]["i2c0"]["sda_pin"] = 2
    with pytest.raises(BuildError, match="is wired to i2c1, not i2c0"):
        _build(tmp_path, src_dir, doc)


def test_i2c_pin_role_transposed_rejected(tmp_path: Path, src_dir: Path) -> None:
    # §6.4: both pins are real, legal GP12/13 for i2c0 - just swapped (scl<->sda).
    doc = base_doc()
    doc["bus"]["i2c0"]["scl_pin"] = 12
    doc["bus"]["i2c0"]["sda_pin"] = 13
    with pytest.raises(BuildError, match="pins transposed"):
        _build(tmp_path, src_dir, doc)


def test_spi_pin_role_transposed_rejected(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["bus"]["spi0"]["sck_pin"] = 3  # real SPI0 pin, but MOSI's, not SCK's
    doc["bus"]["spi0"]["mosi_pin"] = 2  # SCK's
    with pytest.raises(BuildError, match="pins transposed"):
        _build(tmp_path, src_dir, doc)


def test_gpio_with_no_i2c_function_rejected(tmp_path: Path, src_dir: Path) -> None:
    # GP22 is a real, usable GPIO (not wireless-reserved) that simply has no I2C function.
    doc = base_doc()
    doc["bus"]["i2c0"]["scl_pin"] = 22
    with pytest.raises(BuildError, match="has no I2C function"):
        _build(tmp_path, src_dir, doc)


def test_gpio_with_no_spi_function_rejected(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["bus"]["spi0"]["sck_pin"] = 28  # ADC2-only, no SPI function
    with pytest.raises(BuildError, match="has no SPI function"):
        _build(tmp_path, src_dir, doc)


@pytest.mark.parametrize("field,value", [("irq_pin", 24), ("pin", 25), ("cs_pin", 23)])
def test_wireless_reserved_gpio_rejected_on_any_pin_field(tmp_path: Path, src_dir: Path, field: str, value: int) -> None:
    # GP23/24/25/29 - the scope note in §4.3: applies to every claimed pin device-wide, not just
    # bus wire pins (irq_pin/pin/cs_pin here have no peripheral role to check, only existence).
    doc = base_doc()
    if field == "irq_pin":
        doc["instance"][0][field] = value  # scd30
    elif field == "pin":
        doc["instance"][3][field] = value  # neopixel
    else:
        doc["instance"][2][field] = value  # fram
    with pytest.raises(BuildError, match="not a usable Pico W GPIO"):
        _build(tmp_path, src_dir, doc)


@pytest.mark.parametrize("value", [30, -1])
def test_nonexistent_gpio_number_rejected(tmp_path: Path, src_dir: Path, value: int) -> None:
    doc = base_doc()
    doc["instance"][3]["pin"] = value  # neopixel
    with pytest.raises(BuildError, match="not a usable Pico W GPIO"):
        _build(tmp_path, src_dir, doc)


def test_bus_missing_required_wire_pin(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    del doc["bus"]["i2c0"]["scl_pin"]
    with pytest.raises(BuildError, match="missing required field 'scl_pin'"):
        _build(tmp_path, src_dir, doc)


@pytest.mark.parametrize("field", ["sck_pin", "mosi_pin", "miso_pin"])
def test_spi_bus_missing_required_wire_pin(tmp_path: Path, src_dir: Path, field: str) -> None:
    # §7.1 #8: only i2c0's scl_pin was individually tested; asy_spi_driver.SPI's three required
    # wire pins go through the identical _BUS_WIRE_FIELDS loop but had no test of their own.
    doc = base_doc()
    del doc["bus"]["spi0"][field]
    with pytest.raises(BuildError, match=f"missing required field {field!r}"):
        _build(tmp_path, src_dir, doc)


def test_bus_cs_pin_on_shared_bus_rejected(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["bus"]["i2c0"]["cs_pin"] = 9
    with pytest.raises(BuildError, match="cs_pin"):
        _build(tmp_path, src_dir, doc)


def test_i2c_bus_missing_frequency(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    del doc["bus"]["i2c0"]["frequency"]
    with pytest.raises(BuildError, match="missing an int frequency"):
        _build(tmp_path, src_dir, doc)


def test_spi_bus_declares_frequency(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["bus"]["spi0"]["frequency"] = 50000
    with pytest.raises(BuildError, match="has no such parameter"):
        _build(tmp_path, src_dir, doc)


def test_unknown_driver(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["instance"][0]["driver"] = "not_a_real_chip"
    with pytest.raises(BuildError, match="unknown driver"):
        _build(tmp_path, src_dir, doc)


def test_driver_resolvable_but_missing_buildspec_entry_reports_the_real_cause(tmp_path: Path) -> None:
    # §6.3/§8.4/§10.5 item 1: a driver that resolves fine via driver_registry (a real
    # asy_<name>_driver.py with a SensorReader subclass) but has no buildspec.py entry at all -
    # must fail loud, naming the real cause, not report every one of its fields as "unrecognized".
    custom_src = tmp_path / "src"
    custom_src.mkdir()
    (custom_src / "asy_bogus2_driver.py").write_text('_NAME = "BOGUS2"\n\n\nclass Bogus2_Reader(SensorReader):\n    pass\n')
    doc = {
        "device": {"name": "Test", "hostname": "SensorStationTest", "hotspot_password": "12345678", "conn_fail_to_hotspot": 5, "hotspot_time_min": 8},
        "bus": {},
        "instance": [{"driver": "bogus2"}],
    }
    with pytest.raises(BuildError, match="has no entry in buildgen.buildspec"):
        _build(tmp_path, custom_src, doc, name="bogus2dev")


def test_instance_missing_required_field(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    del doc["instance"][0]["irq_pin"]
    with pytest.raises(BuildError, match="missing required field 'irq_pin'"):
        _build(tmp_path, src_dir, doc)


def test_instance_references_undeclared_bus(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["instance"][0]["bus"] = "i2c9"
    with pytest.raises(BuildError, match="undeclared bus"):
        _build(tmp_path, src_dir, doc)


def test_address_field_on_driver_without_address_select_pin(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["instance"][0]["address"] = 0x61  # scd30 has no real address-select pin
    with pytest.raises(BuildError, match="no address-select pin"):
        _build(tmp_path, src_dir, doc)


def test_instance_unknown_field_rejected(tmp_path: Path, src_dir: Path) -> None:
    # A copy-paste leftover (e.g. converting a scd30 block to sgp40 but forgetting to drop
    # irq_pin) must fail loud, not be silently dropped by codegen.
    doc = base_doc()
    doc["instance"][1]["irq_pin"] = 9  # sgp40 has no irq_pin field
    with pytest.raises(BuildError, match="unrecognized field"):
        _build(tmp_path, src_dir, doc)


def test_instance_optional_field_is_allowed(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["instance"][0]["trigger_sec"] = 7  # scd30's own optional field
    _build(tmp_path, src_dir, doc)  # no raise


def test_device_unknown_field_rejected(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["device"]["conn_fail_to_hotspot_typo"] = 5
    with pytest.raises(BuildError, match="unrecognized field"):
        _build(tmp_path, src_dir, doc)


def test_bus_unknown_field_rejected(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["bus"]["i2c0"]["baud_rate"] = 100000  # not a real asy_i2c_driver.I2C parameter
    with pytest.raises(BuildError, match="unrecognized field"):
        _build(tmp_path, src_dir, doc)


def test_bus_timeout_is_allowed_on_i2c(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["bus"]["i2c0"]["timeout"] = 300000
    _build(tmp_path, src_dir, doc)  # no raise - i2c's own optional field, no false positive


def test_bus_timeout_wrong_type_rejected(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["bus"]["i2c0"]["timeout"] = "200000"  # quoted-in-TOML string, not an int
    with pytest.raises(BuildError, match="timeout must be an int"):
        _build(tmp_path, src_dir, doc)


@pytest.mark.parametrize("bad_value", [True, 250000.0])
def test_bus_timeout_bool_or_float_rejected(tmp_path: Path, src_dir: Path, bad_value: object) -> None:
    # §5.3/§7.2(B): the isinstance(x, int) and not isinstance(x, bool) pattern is only exercised by
    # one device-level field (hotspot_time_min) today; this locks the same guard in on bus timeout.
    doc = base_doc()
    doc["bus"]["i2c0"]["timeout"] = bad_value
    with pytest.raises(BuildError, match="timeout must be an int"):
        _build(tmp_path, src_dir, doc)


@pytest.mark.parametrize("bad_value", [True, 50000.0])
def test_bus_frequency_bool_or_float_rejected(tmp_path: Path, src_dir: Path, bad_value: object) -> None:
    doc = base_doc()
    doc["bus"]["i2c0"]["frequency"] = bad_value
    with pytest.raises(BuildError, match="missing an int frequency"):
        _build(tmp_path, src_dir, doc)


def test_instance_bus_field_wrong_type_rejected(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["instance"][0]["bus"] = 0  # not a string - would otherwise raise a raw TypeError/mismatch
    with pytest.raises(BuildError, match="bus must be a string"):
        _build(tmp_path, src_dir, doc)


@pytest.mark.parametrize("field,bad_value", [("max_size", "8192"), ("trigger_sec", "3")])
def test_instance_int_field_wrong_type_rejected(tmp_path: Path, src_dir: Path, field: str, bad_value: str) -> None:
    doc = base_doc()
    if field == "max_size":
        doc["instance"][2][field] = bad_value  # fram
    else:
        doc["instance"][0][field] = bad_value  # scd30
    with pytest.raises(BuildError, match=f"{field} must be an int"):
        _build(tmp_path, src_dir, doc)


def test_instance_address_field_wrong_type_rejected(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["instance"].append({"driver": "bmp3xx", "bus": "i2c0", "address": "0x77"})  # bmp3xx is address-capable
    with pytest.raises(BuildError, match="address must be an int"):
        _build(tmp_path, src_dir, doc)


@pytest.mark.parametrize("field,bad_value", [("max_size", True), ("max_size", 8192.0), ("trigger_sec", True), ("trigger_sec", 3.0)])
def test_instance_int_field_bool_or_float_rejected(tmp_path: Path, src_dir: Path, field: str, bad_value: object) -> None:
    # §5.3/§7.2(B): the same isinstance guard as test_instance_int_field_wrong_type_rejected above,
    # but for bool/float (both plausible copy-paste mistakes) rather than a quoted string.
    doc = base_doc()
    if field == "max_size":
        doc["instance"][2][field] = bad_value  # fram
    else:
        doc["instance"][0][field] = bad_value  # scd30
    with pytest.raises(BuildError, match=f"{field} must be an int"):
        _build(tmp_path, src_dir, doc)


@pytest.mark.parametrize("bad_value", [True, 119.0])
def test_instance_address_field_bool_or_float_rejected(tmp_path: Path, src_dir: Path, bad_value: object) -> None:
    doc = base_doc()
    doc["instance"].append({"driver": "bmp3xx", "bus": "i2c0", "address": bad_value})
    with pytest.raises(BuildError, match="address must be an int"):
        _build(tmp_path, src_dir, doc)


def test_warn_signal_source_wrong_type_rejected(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["instance"][4]["wiring"]["warn_co2"]["source"] = 42
    with pytest.raises(BuildError, match="source/field must both be strings"):
        _build(tmp_path, src_dir, doc)


def test_warn_signal_field_wrong_type_rejected(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["instance"][4]["wiring"]["warn_co2"]["field"] = 42
    with pytest.raises(BuildError, match="source/field must both be strings"):
        _build(tmp_path, src_dir, doc)


def test_instance_driver_field_wrong_type_rejected(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["instance"][0]["driver"] = 42
    with pytest.raises(BuildError, match="'driver' field must be a non-empty string"):
        _build(tmp_path, src_dir, doc)


def test_instance_name_ext_wrong_type_rejected(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["instance"][0]["name_ext"] = 7
    with pytest.raises(BuildError, match="'name_ext' field must be a string"):
        _build(tmp_path, src_dir, doc)


def test_declared_bus_never_used(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["bus"]["i2c1"] = {"scl_pin": 20, "sda_pin": 21, "frequency": 50000}
    with pytest.raises(BuildError, match="declared but never referenced"):
        _build(tmp_path, src_dir, doc)


def test_duplicate_driver_name_ext_pair(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    dup = dict(doc["instance"][0])
    doc["instance"].append(dup)
    with pytest.raises(BuildError, match="duplicate \\[\\[instance\\]\\] entry"):
        _build(tmp_path, src_dir, doc)


def test_instance_name_collision_via_distinct_drivers_same_resolved_name(tmp_path: Path, src_dir: Path) -> None:
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


def test_instance_label_collision_synthetic(tmp_path: Path, src_dir: Path) -> None:
    # §7.2(C)/§10.5 item 2: instance_label() (the generated Python-variable identity) has no
    # uniqueness check of its own distinct from resolved_name's - unreachable via any real driver
    # name today (none contains an underscore that lines up with another driver+name_ext
    # combination), so this drives _check_instance_label_collisions() directly against a synthetic
    # model, the same style as the resolved_name-collision test above.
    from buildgen.model import DeviceModel, InstanceSpec
    from buildgen.validate import _check_instance_label_collisions

    model = DeviceModel("dev", tmp_path / "dev.toml", {})
    model.instances[("foo_bar", "")] = InstanceSpec("foo_bar", "", {}, {}, 0)
    model.instances[("foo", "bar")] = InstanceSpec("foo", "bar", {}, {}, 1)
    with pytest.raises(BuildError, match="instance_label collision"):
        _check_instance_label_collisions(model)


def test_gpio_collision_cs_pin_synthetic_two_instances(tmp_path: Path, src_dir: Path) -> None:
    # §5.1 #12: duplicate CS pins on SPI is already subsumed by _check_gpio_collisions()'s shared
    # claims dict, but today only `fram` has a cs_pin field and it's a forced singleton - no real
    # TOML can produce two cs_pin-bearing instances to collide. Drives the check directly against a
    # synthetic model instead, the same style as the resolved_name-collision test above.
    from buildgen.model import DeviceModel, InstanceSpec
    from buildgen.validate import _check_gpio_collisions

    model = DeviceModel("dev", tmp_path / "dev.toml", {})
    model.instances[("fram", "a")] = InstanceSpec("fram", "a", {"cs_pin": 9}, {}, 0)
    model.instances[("fram", "b")] = InstanceSpec("fram", "b", {"cs_pin": 9}, {}, 1)
    with pytest.raises(BuildError, match="claimed twice"):
        _check_gpio_collisions(model, {})


def test_singleton_service_declared_twice(tmp_path: Path, src_dir: Path) -> None:
    # A singleton service is always forced to name_ext="" (see the next test), so two declarations
    # of the same one always collide as an exact-duplicate [[instance]] entry - caught by
    # model.load_device()'s own (driver, name_ext) dedup before the singleton-specific check even
    # runs (SPECIFICATION.md Part C.14's "never more than one per device by construction").
    doc = base_doc()
    second_fram = {"driver": "fram", "bus": "spi0", "cs_pin": 22, "max_size": 1024}
    doc["instance"].append(second_fram)
    with pytest.raises(BuildError, match="duplicate \\[\\[instance\\]\\] entry"):
        _build(tmp_path, src_dir, doc)


def test_singleton_service_with_name_ext_rejected(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    for inst in doc["instance"]:
        if inst["driver"] == "fram":
            inst["name_ext"] = "extra"
    with pytest.raises(BuildError, match="must not declare name_ext"):
        _build(tmp_path, src_dir, doc)


def test_global_gpio_pin_collision_bus_vs_instance(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["instance"][3]["pin"] = doc["bus"]["i2c0"]["scl_pin"]  # neopixel pin == bus.i2c0.scl_pin
    with pytest.raises(BuildError, match="claimed twice"):
        _build(tmp_path, src_dir, doc)


def test_global_gpio_pin_collision_two_instances(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["instance"][0]["irq_pin"] = doc["instance"][3]["pin"]  # scd30.irq_pin == neopixel.pin
    with pytest.raises(BuildError, match="claimed twice"):
        _build(tmp_path, src_dir, doc)


def test_global_gpio_pin_collision_bus_vs_bus(tmp_path: Path, src_dir: Path) -> None:
    # §7.1 #7: _check_gpio_collisions() claims every bus-table wire pin into one shared dict, so a
    # bus-vs-bus collision (no instance involved) should already raise - only bus-vs-instance and
    # instance-vs-instance had a test until now. Both buses stay used by their real instances, so
    # this isolates the pin-collision path from the separate "declared but never used" check.
    # GP4 is individually legal for both roles claimed here (i2c0's SDA *and* spi0's MISO, per the
    # real Figure 2 table) - picked deliberately so Phase 2's pin-role check doesn't fire first and
    # mask the plain double-claim this test means to isolate.
    doc = base_doc()
    doc["bus"]["i2c0"]["sda_pin"] = doc["bus"]["spi0"]["miso_pin"]
    with pytest.raises(BuildError, match="claimed twice"):
        _build(tmp_path, src_dir, doc)


def test_per_bus_explicit_address_collision(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["instance"].append({"driver": "bmp3xx", "name_ext": "", "bus": "i2c0", "address": 0x77})
    doc["instance"].append({"driver": "bmp3xx", "name_ext": "other", "bus": "i2c0", "address": 0x77})
    with pytest.raises(BuildError, match="claimed by both"):
        _build(tmp_path, src_dir, doc)


def test_per_bus_address_reuse_on_different_bus_is_legitimate(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["bus"]["i2c1"] = {"scl_pin": 27, "sda_pin": 26, "frequency": 50000}  # real i2c1 SDA/SCL pair (Phase 2)
    doc["instance"].append({"driver": "bmp3xx", "name_ext": "a", "bus": "i2c0", "address": 0x77})
    doc["instance"].append({"driver": "bmp3xx", "name_ext": "b", "bus": "i2c1", "address": 0x77})
    _build(tmp_path, src_dir, doc)  # no raise - different buses, same address value is fine


def test_two_fixed_address_instances_same_driver_same_bus_collide(tmp_path: Path, src_dir: Path) -> None:
    # Neither declares an explicit address - both scd30's, hardware address is fixed, so they
    # can't be told apart on the same bus at all.
    doc = base_doc()
    doc["instance"].append({"driver": "scd30", "name_ext": "second", "bus": "i2c0", "irq_pin": 21, "trigger_sec": 3})
    with pytest.raises(BuildError, match="can't be told apart"):
        _build(tmp_path, src_dir, doc)


def test_two_fixed_address_different_drivers_same_bus_do_not_collide(tmp_path: Path, src_dir: Path) -> None:
    # scd30 and sgp40 already share bus i2c0 in base_doc() with no explicit address on either -
    # different chip types have different real fixed addresses, so this must NOT raise.
    doc = base_doc()
    _build(tmp_path, src_dir, doc)


@pytest.mark.parametrize("bad_address", [0x50, 0, 0x78])
def test_bmp3xx_address_outside_legal_set_rejected(tmp_path: Path, src_dir: Path, bad_address: int) -> None:
    # Phase 3 (§5.1 #11/§10.4): bmp3xx's address is well-typed and hardware-plausible but not one
    # of the two real SDO-pin-selected values - a datasheet-reading mistake, not a TOML mistake.
    doc = base_doc()
    doc["instance"].append({"driver": "bmp3xx", "bus": "i2c0", "address": bad_address})
    with pytest.raises(BuildError, match="not one of this driver's legal values"):
        _build(tmp_path, src_dir, doc)


@pytest.mark.parametrize("legal_address", [0x76, 0x77])
def test_bmp3xx_address_in_legal_set_is_fine(tmp_path: Path, src_dir: Path, legal_address: int) -> None:
    doc = base_doc()
    doc["instance"].append({"driver": "bmp3xx", "bus": "i2c0", "address": legal_address})
    _build(tmp_path, src_dir, doc)  # no raise


@pytest.mark.parametrize("bad_trigger", [0, 3601, -1])
def test_bmp3xx_trigger_sec_outside_legal_range_rejected(tmp_path: Path, src_dir: Path, bad_trigger: int) -> None:
    doc = base_doc()
    doc["instance"].append({"driver": "bmp3xx", "bus": "i2c0", "address": 0x77, "trigger_sec": bad_trigger})
    with pytest.raises(BuildError, match="outside this driver's legal range"):
        _build(tmp_path, src_dir, doc)


@pytest.mark.parametrize("legal_trigger", [1, 3600, 60])
def test_bmp3xx_trigger_sec_in_legal_range_is_fine(tmp_path: Path, src_dir: Path, legal_trigger: int) -> None:
    doc = base_doc()
    doc["instance"].append({"driver": "bmp3xx", "bus": "i2c0", "address": 0x77, "trigger_sec": legal_trigger})
    _build(tmp_path, src_dir, doc)  # no raise


def test_two_bmp3xx_same_bus_different_legal_addresses_is_fine(tmp_path: Path, src_dir: Path) -> None:
    # §7.1 #6: the actually-common real case ADDRESS_CAPABLE_DRIVERS exists for - two bmp3xx on one
    # bus, told apart by their two legal SDO-pin addresses - had no positive test until now (only
    # the same-address collision and different-bus reuse cases were covered).
    doc = base_doc()
    doc["instance"].append({"driver": "bmp3xx", "name_ext": "a", "bus": "i2c0", "address": 0x76})
    doc["instance"].append({"driver": "bmp3xx", "name_ext": "b", "bus": "i2c0", "address": 0x77})
    _build(tmp_path, src_dir, doc)  # no raise


def test_wiring_field_not_declared_by_driver(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["instance"][2]["wiring"] = {"comp_source": "scd30"}  # fram has no _WIRING entry named comp_source
    with pytest.raises(BuildError, match="no matching _WIRING entry"):
        _build(tmp_path, src_dir, doc)


def test_instance_wiring_bogus_key_rejected(tmp_path: Path, src_dir: Path) -> None:
    # §5.1 #5/§7.2(B): an entirely fabricated [instance.wiring] key with no _WIRING match and no
    # warn_ prefix - the `wf is None` branch should already catch this; no test exercised it
    # directly with a name that isn't just "the wrong driver's own real field" (the test above).
    doc = base_doc()
    doc["instance"][0]["wiring"]["frobnicate"] = "scd30"  # scd30 has no such field at all
    with pytest.raises(BuildError, match="no matching _WIRING entry"):
        _build(tmp_path, src_dir, doc)


def test_wiring_value_not_a_string(tmp_path: Path, src_dir: Path) -> None:
    # Exercises _check_wiring_reference()'s own type check via notification's signal_sink - the
    # required, producer-class-constrained _WIRING field base_doc() has now that sgp40's own
    # comp_source has been generalized away by §2.9 (see test_buildgen_value_wiring.py for that).
    doc = base_doc()
    doc["instance"][4]["wiring"]["signal_sink"] = 42
    with pytest.raises(BuildError, match="must be a string instance reference"):
        _build(tmp_path, src_dir, doc)


def test_wiring_reference_unresolved(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["instance"][4]["wiring"]["signal_sink"] = "does_not_exist"
    with pytest.raises(BuildError, match="does not resolve to any declared instance"):
        _build(tmp_path, src_dir, doc)


def test_wiring_reference_wrong_class(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["instance"][4]["wiring"]["signal_sink"] = "fram"  # fram is AsyFramManager, not NeopixelDriver
    with pytest.raises(BuildError, match="requires a NeopixelDriver"):
        _build(tmp_path, src_dir, doc)


def test_required_wiring_field_missing(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    del doc["instance"][4]["wiring"]["signal_sink"]
    with pytest.raises(BuildError, match="missing required wiring.signal_sink"):
        _build(tmp_path, src_dir, doc)


def test_signal_sink_default_opt_in_is_fine(tmp_path: Path, src_dir: Path) -> None:
    # §1's original motivating scenario: a notification setup that shouldn't blink any LED.
    doc = base_doc()
    doc["instance"][4]["wiring"]["signal_sink"] = {"default": True}
    _build(tmp_path, src_dir, doc)  # no raise


def test_signal_sink_default_with_unknown_key_rejected(tmp_path: Path, src_dir: Path) -> None:
    # _DefaultSignalSink takes zero constructor args - any extra key is unrecognized.
    doc = base_doc()
    doc["instance"][4]["wiring"]["signal_sink"] = {"default": True, "bogus_key": 5}
    with pytest.raises(BuildError, match="unrecognized key"):
        _build(tmp_path, src_dir, doc)


def test_temperature_source_default_opt_in_is_fine(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["instance"][1]["wiring"]["temperature_source"] = {"default": True, "temperature": 20}
    _build(tmp_path, src_dir, doc)  # no raise - humidity_source stays a real reference


def test_humidity_source_default_opt_in_is_fine(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["instance"][1]["wiring"]["humidity_source"] = {"default": True}
    _build(tmp_path, src_dir, doc)  # no raise - default's own temperature param keeps its own default


def test_temperature_source_default_with_unknown_key_rejected(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["instance"][1]["wiring"]["temperature_source"] = {"default": True, "bogus_key": 5}
    with pytest.raises(BuildError, match="unrecognized key"):
        _build(tmp_path, src_dir, doc)


def test_sgp40_without_any_scd30_using_both_defaults(tmp_path: Path, src_dir: Path) -> None:
    # §1's original motivating scenario: an SGP40 with genuinely no SCD30 at all, defaulting both
    # compensation values via explicit {default = true} opt-ins.
    doc = base_doc()
    doc["instance"] = [i for i in doc["instance"] if i["driver"] != "scd30"]
    doc["instance"][0]["wiring"] = {  # sgp40, now index 0
        "temperature_source": {"default": True, "temperature": 22},
        "humidity_source": {"default": True},
        "fram_target": "fram",
    }
    del doc["instance"][3]["wiring"]["warn_co2"]  # notification, now index 3 - referenced scd30
    _build(tmp_path, src_dir, doc)  # no raise


def test_optional_wiring_field_absent_is_fine(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    del doc["instance"][1]["wiring"]["fram_target"]
    _build(tmp_path, src_dir, doc)  # no raise


def test_notification_present_with_zero_warn_signals_is_fine(tmp_path: Path, src_dir: Path) -> None:
    # §7.1 #3: warn_co2/warn_voc/warn_hum are each individually optional - a notification instance
    # with signal_sink wired but no warn_* keys at all should build clean. base_doc() always wires
    # warn_co2, so this was never actually exercised.
    doc = base_doc()
    del doc["instance"][4]["wiring"]["warn_co2"]
    _build(tmp_path, src_dir, doc)  # no raise


def test_warn_signal_malformed_shape(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["instance"][4]["wiring"]["warn_co2"] = "not a table"
    with pytest.raises(BuildError, match="must be a"):
        _build(tmp_path, src_dir, doc)


def test_warn_signal_source_unresolved(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["instance"][4]["wiring"]["warn_co2"]["source"] = "does_not_exist"
    with pytest.raises(BuildError, match="does not resolve to any declared instance"):
        _build(tmp_path, src_dir, doc)


def test_device_wiring_unknown_field(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["device"]["wiring"]["bogus_target"] = "neopixel"
    with pytest.raises(BuildError, match="unknown field"):
        _build(tmp_path, src_dir, doc)


def test_device_wiring_reference_unresolved(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["device"]["wiring"]["led_target"] = "does_not_exist"
    with pytest.raises(BuildError, match="does not resolve to any declared instance"):
        _build(tmp_path, src_dir, doc)


def test_device_wiring_reference_wrong_class(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["device"]["wiring"]["led_target"] = "fram"  # fram is AsyFramManager, not NeopixelDriver
    with pytest.raises(BuildError, match="requires a NeopixelDriver"):
        _build(tmp_path, src_dir, doc)


def test_device_wiring_optional_field_absent_is_fine(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    del doc["device"]["wiring"]["led_target"]
    _build(tmp_path, src_dir, doc)  # no raise


def test_partial_instance_level_fram_wiring_is_fine(tmp_path: Path, src_dir: Path) -> None:
    # §4.3 axis 4's "partial" state: FRAM present, some fram-wirable instances wire fram_target,
    # others explicitly don't - every existing test either wires it uniformly (base_doc's own
    # default) or removes it from exactly one instance while testing something unrelated. This is
    # the first test asserting the genuinely-partial case on its own terms.
    doc = base_doc()
    del doc["instance"][0]["wiring"]["fram_target"]  # scd30 - unwired
    del doc["instance"][3]["wiring"]["fram_target"]  # neopixel - unwired
    # sgp40 (index 1) and notification (index 4) keep their fram_target wiring - genuinely partial.
    _build(tmp_path, src_dir, doc)  # no raise


def test_device_wiring_fram_target_left_unwired_is_fine(tmp_path: Path, src_dir: Path) -> None:
    # §7.1 #4: the mirror image of the led_target test above - FRAM is present, but nothing wires
    # [device.wiring].fram_target to it. No existing test removed just this field while keeping the
    # fram instance itself.
    doc = base_doc()
    del doc["device"]["wiring"]["fram_target"]
    _build(tmp_path, src_dir, doc)  # no raise


def test_device_wiring_required_field_missing_is_rejected(tmp_path: Path, src_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Both real [device.wiring] fields (led_target/fram_target) are optional today, so this drives
    # _check_device_wiring's required-field enforcement directly against a stand-in consumer table
    # pointing at a real driver file with a genuinely required _WIRING entry (notification's
    # signal_sink - sgp40's old comp_source, this test's original stand-in, no longer exists as a
    # _WIRING entry at all since §2.9 generalized it away) - the same "drive a validate.py internal
    # directly" approach test_instance_name_collision_via_distinct_drivers_same_resolved_name()
    # above already uses for a case none of the six real device TOMLs can exercise either.
    import buildgen.validate as validate_mod
    from buildgen.model import DeviceModel

    monkeypatch.setitem(validate_mod._DEVICE_WIRING_CONSUMERS, "signal_sink", ("asy_notification_service.py", "NotificationCoordinator", "signal_sink"))
    model = DeviceModel("dev", tmp_path / "dev.toml", {"device": {"wiring": {}}})
    with pytest.raises(BuildError, match="missing required field 'signal_sink'"):
        validate_mod._check_device_wiring(model, src_dir)


def test_requires_tag_violated(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["bus"]["i2c0"]["timeout"] = 50000  # scd30's own @requires bus.timeout>=200000
    with pytest.raises(BuildError, match="does not satisfy"):
        _build(tmp_path, src_dir, doc)


def test_requires_tag_missing_bus_field(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    del doc["bus"]["i2c0"]["timeout"]
    with pytest.raises(BuildError, match="is missing field"):
        _build(tmp_path, src_dir, doc)


def test_requires_tag_satisfied(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    doc["bus"]["i2c0"]["timeout"] = 250000
    _build(tmp_path, src_dir, doc)  # no raise


def _staged_src_with_scd30_tag(tmp_path: Path, src_dir: Path, replacement: str) -> Path:
    """A writable copy of src/ whose scd30 driver carries `replacement` in place of its real
    `# @requires` tag - the only way to exercise a broken tag end-to-end through build_model()."""
    staged = tmp_path / "staged_src"
    shutil.copytree(src_dir, staged)
    driver = staged / "asy_scd30_driver.py"
    driver.write_text(driver.read_text().replace("# @requires bus.timeout>=200000", replacement))
    return staged


@pytest.mark.parametrize(
    "replacement,match",
    [
        ("# @require bus.timeout>=200000", "misspelled @requires tag"),  # typo'd tag word
        ("# requires bus.timeout>=200000", "leading '@' missing"),  # sigil dropped
        ("# @requires bus.timeout 200000", "malformed @requires tag"),  # operator dropped
    ],
)
def test_requires_tag_near_miss_in_a_driver_aborts_the_whole_build(tmp_path: Path, src_dir: Path, replacement: str, match: str) -> None:
    # The near-miss detector has to be reachable from build_model(), not just from its own unit
    # tests: a tag that silently degrades to "no tag declared" is exactly the bug it exists to
    # prevent, and this driver's real tag is the one the base fixture's bus table is sized for.
    staged = _staged_src_with_scd30_tag(tmp_path, src_dir, replacement)
    with pytest.raises(BuildError, match=match):
        _build(tmp_path, staged, base_doc())


def test_requires_tag_scd30_max_i2c_frequency_violated(tmp_path: Path, src_dir: Path) -> None:
    # asy_scd30_driver.py's "@requires bus.frequency<=100000" (Interface Description p.2's hard
    # datasheet maximum). Before that tag existed, an over-clocked SCD30 bus built cleanly and only
    # misbehaved on real hardware.
    doc = base_doc()
    doc["bus"]["i2c0"]["frequency"] = 400000
    with pytest.raises(BuildError, match="does not satisfy"):
        _build(tmp_path, src_dir, doc)


def test_requires_tag_stricter_sensor_wins_on_a_shared_bus(tmp_path: Path, src_dir: Path) -> None:
    # scd30 and sgp40 share i2c0 in base_doc(). 200 kHz is legal for the sgp40 (400 kHz max) and
    # illegal for the scd30 (100 kHz) - the bus must be held to the stricter of the two, which is
    # the whole point of these being per-driver tags evaluated against the bus each one references.
    doc = base_doc()
    doc["bus"]["i2c0"]["frequency"] = 200000
    with pytest.raises(BuildError, match="scd30"):
        _build(tmp_path, src_dir, doc)


def test_requires_tag_sgp40_max_i2c_frequency_violated(tmp_path: Path, src_dir: Path) -> None:
    # The sgp40's own 400 kHz ceiling (datasheet Table 3), on a bus with no scd30 to mask it.
    doc = base_doc()
    doc["bus"]["i2c1"] = {"scl_pin": 27, "sda_pin": 26, "frequency": 1000000}
    doc["instance"][1]["bus"] = "i2c1"
    with pytest.raises(BuildError, match="sgp40"):
        _build(tmp_path, src_dir, doc)


def test_requires_tag_sgp40_within_its_own_ceiling_on_a_separate_bus_builds(tmp_path: Path, src_dir: Path) -> None:
    # The control: 400 kHz is fine for an sgp40 alone - so the rejection above is the tag firing,
    # not the split-bus topology itself being invalid.
    doc = base_doc()
    doc["bus"]["i2c1"] = {"scl_pin": 27, "sda_pin": 26, "frequency": 400000}
    doc["instance"][1]["bus"] = "i2c1"
    _build(tmp_path, src_dir, doc)  # no raise


def test_requires_tag_removed_entirely_still_builds(tmp_path: Path, src_dir: Path) -> None:
    # The control for the three cases above: with the tag genuinely absent (not typo'd), the same
    # build succeeds - so those aborts are the near-miss detector firing, not the staged copy.
    staged = _staged_src_with_scd30_tag(tmp_path, src_dir, "# no requirement declared")
    _build(tmp_path, staged, base_doc())  # no raise
