"""Shape/collision smoke tests for devices/*.toml against BUILD_CHAIN_PLAN.md's schema (optional
modules only in [[instance]]; wifi/ntp/system are mandatory infra, tuned via [device] instead).
Hand-implements the collision checks until Session 3's generator/validator exists."""

import copy
from pathlib import Path

import pytest
import tomllib

DEVICE_NAMES = ["dev", "wozi", "arzi", "klkizi", "grkizi", "schlafzi"]

# Optional-module driver kinds every device declares, plus scd30/sgp40 (every device has both).
# bmp3xx is present only on wozi/dev. wifi/ntp/system are mandatory infra, never [[instance]].
_ALWAYS_PRESENT_DRIVERS = {"scd30", "sgp40", "fram", "neopixel", "notification"}
_DEVICES_WITH_BMP3XX = {"wozi", "dev"}
# Driver kinds that can have more than one instance per device.
_MULTI_INSTANCE_CAPABLE_DRIVERS = {"scd30", "sgp40", "bmp3xx"}
_SINGLETON_DRIVERS = {"fram", "neopixel", "notification"}
# Mandatory infrastructure - present on every device, never modeled as [[instance]]; tuned via
# required fields directly in [device].
_MANDATORY_INFRA_DRIVERS = {"wifi", "ntp", "system"}
_REQUIRED_DEVICE_INFRA_FIELDS = ("conn_fail_to_hotspot", "hotspot_time_min")
# Driver/service kinds whose fram=/fram_storage= wiring is individually optional.
_FRAM_WIRABLE_INSTANCE_DRIVERS = {"scd30", "sgp40", "bmp3xx", "neopixel", "notification"}
# Mandatory-infra-side mirror of [instance.wiring], under [device.wiring] - both fields optional.
_DEVICE_WIRING = {"led_target": "neopixel", "fram_target": "fram"}

_REQUIRED_BUS_PIN_FIELDS = {
    "i2c": {"scl_pin", "sda_pin"},
    "spi": {"sck_pin", "mosi_pin", "miso_pin"},
}


@pytest.fixture(scope="session")
def devices_dir(repo_root: Path) -> Path:
    return repo_root / "devices"


def _load(devices_dir: Path, name: str) -> dict:
    with open(devices_dir / f"{name}.toml", "rb") as f:
        return tomllib.load(f)


def _bus_kind(bus_name: str) -> str:
    for kind in _REQUIRED_BUS_PIN_FIELDS:
        if bus_name.startswith(kind):
            return kind
    raise AssertionError(f"unrecognized bus id {bus_name!r} - not an i2c*/spi* bus")


# --- reusable collision/shape checks (each raises AssertionError on the first violation found) --
# Standalone functions so the negative-path tests below can exercise the same logic on synthetic docs.


def check_bus_tables_declare_their_required_wire_pins(doc: dict, label: str) -> None:
    buses = doc["bus"]
    assert buses, f"{label}: no bus declared"
    for bus_name, bus_table in buses.items():
        kind = _bus_kind(bus_name)
        required = _REQUIRED_BUS_PIN_FIELDS[kind]
        missing = required - bus_table.keys()
        assert not missing, f"{label}: bus.{bus_name} is missing required field(s) {missing}"
        if kind == "i2c":
            # asy_i2c_driver.I2C takes a frequency param; asy_spi_driver.SPI has none.
            assert isinstance(bus_table.get("frequency"), int), f"{label}: bus.{bus_name} (i2c) is missing an int frequency"
        else:
            assert "frequency" not in bus_table, f"{label}: bus.{bus_name} (spi) declares frequency - asy_spi_driver.SPI has no such parameter"
        # cs_pin is an instance-exclusive resource, never a bus-shared field.
        assert "cs_pin" not in bus_table, f"{label}: bus.{bus_name} declares cs_pin - that belongs on the owning instance, not the shared bus"


def check_every_instance_referencing_a_bus_uses_a_declared_bus(doc: dict, label: str) -> None:
    bus_ids = set(doc["bus"].keys())
    for inst in doc["instance"]:
        if "bus" in inst:
            assert inst["bus"] in bus_ids, f"{label}: instance {inst['driver']!r} references undeclared bus {inst['bus']!r}"


def check_every_declared_bus_is_used_by_some_instance(doc: dict, label: str) -> None:
    used = {inst["bus"] for inst in doc["instance"] if "bus" in inst}
    orphans = set(doc["bus"].keys()) - used
    assert not orphans, f"{label}: bus(es) {orphans} declared but never referenced by any instance"


def check_singleton_drivers_never_declare_name_ext(doc: dict, label: str) -> None:
    for inst in doc["instance"]:
        if inst["driver"] in _SINGLETON_DRIVERS:
            assert "name_ext" not in inst, f"{label}: singleton driver {inst['driver']!r} declares name_ext - singleton service kinds never do"


# sgp40's per-value measurement wiring (BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md §2.9):
# temperature_source/humidity_source are independent {source, field} references, generalized from
# the old single whole-object comp_source field - every real device today sources both off scd30.
_SGP40_VALUE_WIRING = {"temperature_source": "Temp", "humidity_source": "Hum"}


def check_sgp40_wiring_resolves_to_real_sources(doc: dict, label: str) -> None:
    instances = {(inst["driver"], inst.get("name_ext", "")): inst for inst in doc["instance"]}
    sgp40_key = ("sgp40", "")
    assert sgp40_key in instances, f"{label}: no unextended sgp40 instance found"
    wiring = instances[sgp40_key].get("wiring")
    assert wiring is not None, f"{label}: sgp40 instance has no [instance.wiring] table"
    for key, expected_field in _SGP40_VALUE_WIRING.items():
        sig = wiring.get(key)
        assert sig is not None, f"{label}: sgp40 instance has no wiring.{key}"
        assert sig.get("field") == expected_field, f"{label}: [instance.wiring.{key}].field is {sig.get('field')!r}, expected {expected_field!r}"
        assert (sig.get("source"), "") in instances, f"{label}: sgp40's {key} references {sig.get('source')!r} but no such instance exists"


def check_no_global_gpio_pin_collision(doc: dict, label: str) -> None:
    # One flat GPIO namespace per device; `address` excluded - it's per-bus logical, not physical.
    claims: dict[int, str] = {}

    def claim(pin: object, owner: str) -> None:
        if pin is None:
            return
        assert isinstance(pin, int) and not isinstance(pin, bool), f"{label}: {owner}'s pin value {pin!r} is not an int"
        existing = claims.get(pin)
        assert existing is None, f"{label}: GPIO{pin} claimed twice - by {existing!r} and by {owner!r}"
        claims[pin] = owner

    for bus_name, bus_table in doc["bus"].items():
        for field in ("scl_pin", "sda_pin", "sck_pin", "mosi_pin", "miso_pin"):
            if field in bus_table:
                claim(bus_table[field], f"bus.{bus_name}.{field}")

    for inst in doc["instance"]:
        inst_label = inst["driver"] + (f"_{inst['name_ext']}" if inst.get("name_ext") else "")
        for field in ("cs_pin", "irq_pin", "pin"):
            if field in inst:
                claim(inst[field], f"instance[{inst_label}].{field}")


def check_no_per_bus_address_collision(doc: dict, label: str) -> None:
    per_bus: dict[str, dict[int, str]] = {}
    for inst in doc["instance"]:
        if "address" not in inst or "bus" not in inst:
            continue
        bus_claims = per_bus.setdefault(inst["bus"], {})
        existing = bus_claims.get(inst["address"])
        assert existing is None, f"{label}: bus {inst['bus']!r} address {inst['address']:#x} claimed by both {existing!r} and {inst['driver']!r}"
        bus_claims[inst["address"]] = inst["driver"]


def check_no_instance_name_collision(doc: dict, label: str) -> None:
    # instance_name(driver, name_ext) collision (SPECIFICATION.md Part C.14.1).
    names = [inst["driver"] + (f"_{inst['name_ext']}" if inst.get("name_ext") else "") for inst in doc["instance"]]
    assert len(names) == len(set(names)), f"{label}: instance name collision in {names}"


def check_notification_wiring_resolves_to_a_real_neopixel_instance(doc: dict, label: str) -> None:
    # signal_sink is a required, TOML-visible reference to the neopixel instance.
    instances = {(inst["driver"], inst.get("name_ext", "")): inst for inst in doc["instance"]}
    notif_key = ("notification", "")
    assert notif_key in instances, f"{label}: no notification instance found"
    wiring = instances[notif_key].get("wiring")
    assert wiring is not None, f"{label}: notification instance has no [instance.wiring] table"
    assert wiring.get("signal_sink") == "neopixel", f"{label}: notification's wiring.signal_sink is {wiring.get('signal_sink')!r}, expected 'neopixel'"
    assert ("neopixel", "") in instances, f"{label}: notification's signal_sink references 'neopixel' but no such instance exists"


_NOTIFICATION_SIGNAL_WIRING = {
    "warn_co2": ("scd30", "CO2"),
    "warn_voc": ("sgp40", "VOC"),
    "warn_hum": ("scd30", "Hum"),
}


def check_notification_signal_wiring_resolves_if_present(doc: dict, label: str) -> None:
    # Each per-signal getter is optional; absence disables that warning signal rather than erroring.
    instances = {(inst["driver"], inst.get("name_ext", "")): inst for inst in doc["instance"]}
    notif = next((inst for inst in doc["instance"] if inst["driver"] == "notification"), None)
    assert notif is not None, f"{label}: no notification instance found"
    wiring = notif.get("wiring", {})
    for key, (expected_driver, expected_field) in _NOTIFICATION_SIGNAL_WIRING.items():
        sig = wiring.get(key)
        if sig is None:
            continue  # optional - absent disables this signal on this device, not an error
        assert sig.get("source") == expected_driver, f"{label}: [instance.wiring.{key}].source is {sig.get('source')!r}, expected {expected_driver!r}"
        assert sig.get("field") == expected_field, f"{label}: [instance.wiring.{key}].field is {sig.get('field')!r}, expected {expected_field!r}"
        assert (sig["source"], "") in instances, f"{label}: notification's {key}.source references {sig['source']!r} but no such instance exists"


def check_fram_wiring_resolves_if_present(doc: dict, label: str) -> None:
    # fram_target is optional per instance; when present it must resolve to a real fram instance.
    instances = {(inst["driver"], inst.get("name_ext", "")): inst for inst in doc["instance"]}
    for inst in doc["instance"]:
        if inst["driver"] not in _FRAM_WIRABLE_INSTANCE_DRIVERS:
            continue
        wiring = inst.get("wiring", {})
        if "fram_target" not in wiring:
            continue  # optional - absent is allowed
        target = wiring["fram_target"]
        assert target == "fram", f"{label}: {inst['driver']}'s wiring.fram_target is {target!r}, expected 'fram'"
        assert ("fram", "") in instances, f"{label}: {inst['driver']}'s fram_target references 'fram' but no such instance exists"


def check_device_wiring_resolves_if_present(doc: dict, label: str) -> None:
    # Mandatory-infra-to-optional-instance links, under [device.wiring]; both fields optional.
    instances = {(inst["driver"], inst.get("name_ext", "")): inst for inst in doc["instance"]}
    wiring = doc.get("device", {}).get("wiring", {})
    for field, expected_driver in _DEVICE_WIRING.items():
        if field not in wiring:
            continue  # optional - absent disables the feature, not an error
        target = wiring[field]
        assert target == expected_driver, f"{label}: device.wiring.{field} is {target!r}, expected {expected_driver!r}"
        assert (target, "") in instances, f"{label}: device.wiring.{field} references {target!r} but no such instance exists"


def check_no_mandatory_infra_modeled_as_instance(doc: dict, label: str) -> None:
    # wifi/ntp/system must never appear as [[instance]] entries.
    drivers = {inst["driver"] for inst in doc["instance"]}
    leaked = drivers & _MANDATORY_INFRA_DRIVERS
    assert not leaked, f"{label}: {sorted(leaked)} modeled as [[instance]] - mandatory infrastructure belongs in [device], never as an instance"


def check_device_infra_fields_present_and_valid(doc: dict, label: str) -> None:
    # Required, not defaulted - a missing or wrong-typed field is a build-time error.
    cfg = doc.get("device")
    assert cfg is not None, f"{label}: no [device] table"
    for field in _REQUIRED_DEVICE_INFRA_FIELDS:
        assert field in cfg, f"{label}: [device] is missing required field {field!r}"
        assert isinstance(cfg[field], int) and not isinstance(cfg[field], bool), f"{label}: [device].{field} must be an int, got {cfg[field]!r}"


# --- shape/parse tests, run against the 6 real files --------------------------------------------


def test_all_six_device_files_exist(devices_dir: Path):
    found = {p.stem for p in devices_dir.glob("*.toml")}
    assert found == set(DEVICE_NAMES), f"devices/ should hold exactly the 6 real device TOML files, found {found}"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_parses_as_valid_toml(devices_dir: Path, device: str):
    _load(devices_dir, device)  # raises tomllib.TOMLDecodeError on malformed TOML


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_device_table_shape(devices_dir: Path, device: str):
    doc = _load(devices_dir, device)
    dev_table = doc["device"]
    assert isinstance(dev_table["name"], str) and dev_table["name"]
    assert isinstance(dev_table["hostname"], str) and dev_table["hostname"] == f"SensorStation{dev_table['name']}"
    assert isinstance(dev_table["hotspot_password"], str) and dev_table["hotspot_password"]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_bus_tables_declare_their_required_wire_pins(devices_dir: Path, device: str):
    check_bus_tables_declare_their_required_wire_pins(_load(devices_dir, device), device)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_instance_list_has_the_expected_driver_kinds(devices_dir: Path, device: str):
    doc = _load(devices_dir, device)
    drivers = [inst["driver"] for inst in doc["instance"]]
    expected = set(_ALWAYS_PRESENT_DRIVERS)
    if device in _DEVICES_WITH_BMP3XX:
        expected.add("bmp3xx")
    assert set(drivers) == expected, f"{device}: instance driver set {sorted(set(drivers))} != expected {sorted(expected)}"
    assert len(drivers) == len(set(drivers)), f"{device}: duplicate driver kind in instance list"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_multi_instance_capable_drivers_declare_name_ext(devices_dir: Path, device: str):
    doc = _load(devices_dir, device)
    for inst in doc["instance"]:
        if inst["driver"] in _MULTI_INSTANCE_CAPABLE_DRIVERS:
            assert "name_ext" in inst, f"{device}: {inst['driver']!r} instance is missing name_ext"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_singleton_drivers_never_declare_name_ext(devices_dir: Path, device: str):
    check_singleton_drivers_never_declare_name_ext(_load(devices_dir, device), device)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_instance_referencing_a_bus_uses_a_declared_bus(devices_dir: Path, device: str):
    check_every_instance_referencing_a_bus_uses_a_declared_bus(_load(devices_dir, device), device)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_declared_bus_is_used_by_some_instance(devices_dir: Path, device: str):
    check_every_declared_bus_is_used_by_some_instance(_load(devices_dir, device), device)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_sgp40_wiring_resolves_to_a_real_scd30_instance(devices_dir: Path, device: str):
    check_sgp40_wiring_resolves_to_real_sources(_load(devices_dir, device), device)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_notification_wiring_resolves_to_a_real_neopixel_instance(devices_dir: Path, device: str):
    check_notification_wiring_resolves_to_a_real_neopixel_instance(_load(devices_dir, device), device)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_notification_signal_wiring_resolves_if_present(devices_dir: Path, device: str):
    check_notification_signal_wiring_resolves_if_present(_load(devices_dir, device), device)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_fram_wiring_resolves_if_present(devices_dir: Path, device: str):
    check_fram_wiring_resolves_if_present(_load(devices_dir, device), device)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_device_wiring_resolves_if_present(devices_dir: Path, device: str):
    check_device_wiring_resolves_if_present(_load(devices_dir, device), device)


def test_every_real_device_declares_fram_wiring_on_every_wirable_instance(devices_dir: Path):
    # Fact about the 6 real devices, not a schema requirement - fram_target is individually optional.
    for device in DEVICE_NAMES:
        doc = _load(devices_dir, device)
        for inst in doc["instance"]:
            if inst["driver"] in _FRAM_WIRABLE_INSTANCE_DRIVERS:
                assert inst.get("wiring", {}).get("fram_target") == "fram", f"{device}: {inst['driver']} is missing fram_target"
        assert doc["device"]["wiring"] == _DEVICE_WIRING, f"{device}: unexpected device.wiring"


def test_every_real_device_declares_all_three_notification_signals(devices_dir: Path):
    # Fact about the 6 real devices, not a schema requirement - each signal is individually optional.
    for device in DEVICE_NAMES:
        doc = _load(devices_dir, device)
        notif = next(inst for inst in doc["instance"] if inst["driver"] == "notification")
        assert set(notif["wiring"]) == {"signal_sink", "fram_target", *_NOTIFICATION_SIGNAL_WIRING}, f"{device}: unexpected notification wiring keys"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_no_global_gpio_pin_collision(devices_dir: Path, device: str):
    check_no_global_gpio_pin_collision(_load(devices_dir, device), device)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_no_per_bus_address_collision(devices_dir: Path, device: str):
    check_no_per_bus_address_collision(_load(devices_dir, device), device)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_no_instance_name_collision(devices_dir: Path, device: str):
    check_no_instance_name_collision(_load(devices_dir, device), device)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_no_mandatory_infra_modeled_as_instance(devices_dir: Path, device: str):
    check_no_mandatory_infra_modeled_as_instance(_load(devices_dir, device), device)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_device_infra_fields_present_and_valid(devices_dir: Path, device: str):
    check_device_infra_fields_present_and_valid(_load(devices_dir, device), device)


def test_bmp3xx_only_present_on_wozi_and_dev(devices_dir: Path):
    for device in DEVICE_NAMES:
        doc = _load(devices_dir, device)
        drivers = {inst["driver"] for inst in doc["instance"]}
        assert ("bmp3xx" in drivers) == (device in _DEVICES_WITH_BMP3XX)


def test_klkizi_grkizi_schlafzi_share_identical_wiring(devices_dir: Path):
    # Only device identity (name/hostname) may differ; everything else must be byte-for-byte identical.
    docs = {name: _load(devices_dir, name) for name in ("klkizi", "grkizi", "schlafzi")}
    for doc in docs.values():
        del doc["device"]["name"]
        del doc["device"]["hostname"]
    bodies = list(docs.values())
    assert bodies[0] == bodies[1] == bodies[2]


# --- error-handling tests: each check above must actually fire on bad input ----------------------

# A minimal, otherwise-valid single-device doc; each negative test mutates it to trigger one violation.
_BASE_DOC: dict = {
    "device": {
        "name": "Test",
        "hostname": "SensorStationTest",
        "hotspot_password": "x",
        "conn_fail_to_hotspot": 5,
        "hotspot_time_min": 8,
        "wiring": {"led_target": "neopixel", "fram_target": "fram"},
    },
    "bus": {
        "i2c0": {"scl_pin": 13, "sda_pin": 12, "frequency": 50000, "timeout": 200000},
        "i2c1": {"scl_pin": 19, "sda_pin": 18, "frequency": 50000},
        "spi0": {"sck_pin": 2, "mosi_pin": 3, "miso_pin": 4},
    },
    "instance": [
        {"driver": "scd30", "name_ext": "", "bus": "i2c0", "irq_pin": 8, "trigger_sec": 3, "wiring": {"fram_target": "fram"}},
        {
            "driver": "sgp40",
            "name_ext": "",
            "bus": "i2c1",
            "wiring": {
                "temperature_source": {"source": "scd30", "field": "Temp"},
                "humidity_source": {"source": "scd30", "field": "Hum"},
                "fram_target": "fram",
            },
        },
        {"driver": "fram", "bus": "spi0", "cs_pin": 1, "max_size": 0x2000},
        {"driver": "neopixel", "pin": 15, "wiring": {"fram_target": "fram"}},
        {
            "driver": "notification",
            "wiring": {
                "signal_sink": "neopixel",
                "fram_target": "fram",
                "warn_co2": {"source": "scd30", "field": "CO2"},
                "warn_voc": {"source": "sgp40", "field": "VOC"},
                "warn_hum": {"source": "scd30", "field": "Hum"},
            },
        },
    ],
}


def _base_doc() -> dict:
    return copy.deepcopy(_BASE_DOC)


def test_base_doc_fixture_itself_passes_every_check():
    # Guards the negative tests below against a broken fixture.
    doc = _base_doc()
    check_bus_tables_declare_their_required_wire_pins(doc, "base")
    check_every_instance_referencing_a_bus_uses_a_declared_bus(doc, "base")
    check_every_declared_bus_is_used_by_some_instance(doc, "base")
    check_sgp40_wiring_resolves_to_real_sources(doc, "base")
    check_notification_wiring_resolves_to_a_real_neopixel_instance(doc, "base")
    check_notification_signal_wiring_resolves_if_present(doc, "base")
    check_fram_wiring_resolves_if_present(doc, "base")
    check_device_wiring_resolves_if_present(doc, "base")
    check_no_global_gpio_pin_collision(doc, "base")
    check_no_per_bus_address_collision(doc, "base")
    check_no_instance_name_collision(doc, "base")
    check_no_mandatory_infra_modeled_as_instance(doc, "base")
    check_device_infra_fields_present_and_valid(doc, "base")


def test_detects_missing_bus_wire_pin():
    doc = _base_doc()
    del doc["bus"]["i2c0"]["sda_pin"]
    with pytest.raises(AssertionError, match="missing required field"):
        check_bus_tables_declare_their_required_wire_pins(doc, "base")


def test_detects_i2c_bus_missing_frequency():
    doc = _base_doc()
    del doc["bus"]["i2c0"]["frequency"]
    with pytest.raises(AssertionError, match="frequency"):
        check_bus_tables_declare_their_required_wire_pins(doc, "base")


def test_detects_spi_bus_with_a_frequency_field():
    doc = _base_doc()
    doc["bus"]["spi0"]["frequency"] = 1000000
    with pytest.raises(AssertionError, match="has no such parameter"):
        check_bus_tables_declare_their_required_wire_pins(doc, "base")


def test_detects_cs_pin_on_a_bus_table():
    doc = _base_doc()
    doc["bus"]["spi0"]["cs_pin"] = 1
    with pytest.raises(AssertionError, match="cs_pin"):
        check_bus_tables_declare_their_required_wire_pins(doc, "base")


def test_detects_no_bus_declared_at_all():
    doc = _base_doc()
    doc["bus"] = {}
    with pytest.raises(AssertionError, match="no bus declared"):
        check_bus_tables_declare_their_required_wire_pins(doc, "base")


def test_bus_kind_rejects_an_unrecognized_bus_id():
    with pytest.raises(AssertionError, match="unrecognized bus id"):
        _bus_kind("uart0")


def test_detects_instance_referencing_an_undeclared_bus():
    doc = _base_doc()
    doc["instance"][0]["bus"] = "i2c9"
    with pytest.raises(AssertionError, match="undeclared bus"):
        check_every_instance_referencing_a_bus_uses_a_declared_bus(doc, "base")


def test_detects_an_orphan_declared_bus():
    doc = _base_doc()
    doc["bus"]["i2c2"] = {"scl_pin": 20, "sda_pin": 21, "frequency": 50000}
    with pytest.raises(AssertionError, match="never referenced"):
        check_every_declared_bus_is_used_by_some_instance(doc, "base")


def test_detects_a_singleton_driver_wrongly_declaring_name_ext():
    doc = _base_doc()
    doc["instance"][2]["name_ext"] = ""  # fram is a singleton driver kind
    with pytest.raises(AssertionError, match="name_ext"):
        check_singleton_drivers_never_declare_name_ext(doc, "base")


def test_detects_sgp40_missing_its_wiring_table():
    doc = _base_doc()
    del doc["instance"][1]["wiring"]
    with pytest.raises(AssertionError, match="no \\[instance.wiring\\] table"):
        check_sgp40_wiring_resolves_to_real_sources(doc, "base")


def test_detects_sgp40_wiring_with_the_wrong_field_name():
    # §2.9: any source exposing a matching attribute name is structurally valid (no fixed producer
    # class to check against) - this smoke suite instead checks the real devices' own convention
    # (temperature_source always reads "Temp"), so a field-name typo is what it can actually catch.
    doc = _base_doc()
    doc["instance"][1]["wiring"]["temperature_source"]["field"] = "Temperature"
    with pytest.raises(AssertionError, match="expected 'Temp'"):
        check_sgp40_wiring_resolves_to_real_sources(doc, "base")


def test_detects_sgp40_wiring_referencing_a_nonexistent_instance():
    doc = _base_doc()
    doc["instance"] = [i for i in doc["instance"] if i["driver"] != "scd30"]
    with pytest.raises(AssertionError, match="no such instance exists"):
        check_sgp40_wiring_resolves_to_real_sources(doc, "base")


def test_detects_sgp40_instance_missing_entirely():
    doc = _base_doc()
    doc["instance"] = [i for i in doc["instance"] if i["driver"] != "sgp40"]
    with pytest.raises(AssertionError, match="no unextended sgp40 instance found"):
        check_sgp40_wiring_resolves_to_real_sources(doc, "base")


def test_detects_notification_missing_its_wiring_table():
    doc = _base_doc()
    del doc["instance"][4]["wiring"]
    with pytest.raises(AssertionError, match=r"no \[instance.wiring\] table"):
        check_notification_wiring_resolves_to_a_real_neopixel_instance(doc, "base")


def test_detects_notification_wiring_pointing_at_the_wrong_driver():
    doc = _base_doc()
    doc["instance"][4]["wiring"]["signal_sink"] = "fram"
    with pytest.raises(AssertionError, match="expected 'neopixel'"):
        check_notification_wiring_resolves_to_a_real_neopixel_instance(doc, "base")


def test_detects_notification_wiring_referencing_a_nonexistent_instance():
    doc = _base_doc()
    doc["instance"] = [i for i in doc["instance"] if i["driver"] != "neopixel"]
    with pytest.raises(AssertionError, match="no such instance exists"):
        check_notification_wiring_resolves_to_a_real_neopixel_instance(doc, "base")


def test_detects_notification_instance_missing_entirely():
    doc = _base_doc()
    doc["instance"] = [i for i in doc["instance"] if i["driver"] != "notification"]
    with pytest.raises(AssertionError, match="no notification instance found"):
        check_notification_wiring_resolves_to_a_real_neopixel_instance(doc, "base")


def test_detects_notification_instance_missing_entirely_for_signal_wiring():
    doc = _base_doc()
    doc["instance"] = [i for i in doc["instance"] if i["driver"] != "notification"]
    with pytest.raises(AssertionError, match="no notification instance found"):
        check_notification_signal_wiring_resolves_if_present(doc, "base")


def test_allows_a_notification_signal_getter_to_be_entirely_absent():
    doc = _base_doc()
    del doc["instance"][4]["wiring"]["warn_hum"]
    check_notification_signal_wiring_resolves_if_present(doc, "base")  # must not raise


def test_detects_notification_signal_wiring_wrong_source():
    doc = _base_doc()
    doc["instance"][4]["wiring"]["warn_voc"]["source"] = "scd30"
    with pytest.raises(AssertionError, match="expected 'sgp40'"):
        check_notification_signal_wiring_resolves_if_present(doc, "base")


def test_detects_notification_signal_wiring_wrong_field():
    doc = _base_doc()
    doc["instance"][4]["wiring"]["warn_co2"]["field"] = "Hum"
    with pytest.raises(AssertionError, match="expected 'CO2'"):
        check_notification_signal_wiring_resolves_if_present(doc, "base")


def test_detects_notification_signal_wiring_referencing_a_nonexistent_instance():
    doc = _base_doc()
    doc["instance"] = [i for i in doc["instance"] if i["driver"] != "scd30"]
    with pytest.raises(AssertionError, match="no such instance exists"):
        check_notification_signal_wiring_resolves_if_present(doc, "base")


def test_detects_a_non_int_pin_value():
    doc = _base_doc()
    doc["bus"]["i2c0"]["scl_pin"] = "13"
    with pytest.raises(AssertionError, match="is not an int"):
        check_no_global_gpio_pin_collision(doc, "base")


def test_detects_a_bool_pin_value():
    doc = _base_doc()
    doc["instance"][3]["pin"] = True  # bool is an int subclass in Python - must still be rejected
    with pytest.raises(AssertionError, match="is not an int"):
        check_no_global_gpio_pin_collision(doc, "base")


def test_detects_a_bus_wire_pin_reused_by_another_bus():
    doc = _base_doc()
    doc["bus"]["i2c1"]["scl_pin"] = 13  # collides with i2c0's own scl_pin
    with pytest.raises(AssertionError, match="claimed twice"):
        check_no_global_gpio_pin_collision(doc, "base")


def test_detects_an_instance_cs_pin_reusing_a_bus_wire_pin():
    doc = _base_doc()
    doc["instance"][2]["cs_pin"] = 13  # collides with i2c0's own scl_pin
    with pytest.raises(AssertionError, match="claimed twice"):
        check_no_global_gpio_pin_collision(doc, "base")


def test_detects_two_instances_claiming_the_same_pin():
    doc = _base_doc()
    doc["instance"][3]["pin"] = 1  # neopixel's pin collides with fram's own cs_pin
    with pytest.raises(AssertionError, match="claimed twice"):
        check_no_global_gpio_pin_collision(doc, "base")


def test_detects_two_instances_sharing_an_address_on_the_same_bus():
    doc = _base_doc()
    doc["instance"].append({"driver": "bmp3xx", "name_ext": "", "bus": "i2c1", "address": 0x77})
    doc["instance"].append({"driver": "bmp3xx", "name_ext": "second", "bus": "i2c1", "address": 0x77})
    with pytest.raises(AssertionError, match="claimed by both"):
        check_no_per_bus_address_collision(doc, "base")


def test_allows_the_same_address_on_two_different_buses():
    # Per-bus address exclusivity is scoped, not global.
    doc = _base_doc()
    doc["instance"].append({"driver": "bmp3xx", "name_ext": "", "bus": "i2c1", "address": 0x77})
    doc["instance"].append({"driver": "bmp3xx", "name_ext": "second", "bus": "i2c0", "address": 0x77})
    check_no_per_bus_address_collision(doc, "base")  # must not raise


def test_detects_two_instances_resolving_to_the_same_name():
    doc = _base_doc()
    doc["instance"].append({"driver": "scd30", "name_ext": "", "bus": "i2c1", "irq_pin": 9, "trigger_sec": 3})
    with pytest.raises(AssertionError, match="instance name collision"):
        check_no_instance_name_collision(doc, "base")


def test_allows_two_same_driver_instances_disambiguated_by_name_ext():
    doc = _base_doc()
    doc["instance"].append({"driver": "scd30", "name_ext": "fan_pressure", "bus": "i2c1", "irq_pin": 9, "trigger_sec": 3})
    check_no_instance_name_collision(doc, "base")  # must not raise


@pytest.mark.parametrize("mandatory_driver", sorted(_MANDATORY_INFRA_DRIVERS))
def test_detects_mandatory_infra_modeled_as_instance(mandatory_driver: str):
    doc = _base_doc()
    doc["instance"].append({"driver": mandatory_driver})
    with pytest.raises(AssertionError, match="mandatory infrastructure"):
        check_no_mandatory_infra_modeled_as_instance(doc, "base")


def test_detects_device_table_missing_entirely():
    doc = _base_doc()
    del doc["device"]
    with pytest.raises(AssertionError, match=r"no \[device\] table"):
        check_device_infra_fields_present_and_valid(doc, "base")


def test_detects_device_missing_conn_fail_to_hotspot():
    doc = _base_doc()
    del doc["device"]["conn_fail_to_hotspot"]
    with pytest.raises(AssertionError, match="missing required field 'conn_fail_to_hotspot'"):
        check_device_infra_fields_present_and_valid(doc, "base")


def test_detects_device_missing_hotspot_time_min():
    doc = _base_doc()
    del doc["device"]["hotspot_time_min"]
    with pytest.raises(AssertionError, match="missing required field 'hotspot_time_min'"):
        check_device_infra_fields_present_and_valid(doc, "base")


def test_detects_device_infra_field_wrong_type():
    doc = _base_doc()
    doc["device"]["hotspot_time_min"] = "eight"
    with pytest.raises(AssertionError, match="must be an int"):
        check_device_infra_fields_present_and_valid(doc, "base")


def test_allows_fram_wiring_to_be_entirely_absent_on_any_instance():
    # Some instances may be wired to FRAM and others not, on the same device.
    doc = _base_doc()
    del doc["instance"][0]["wiring"]["fram_target"]  # scd30
    del doc["instance"][3]["wiring"]["fram_target"]  # neopixel
    check_fram_wiring_resolves_if_present(doc, "base")  # must not raise


def test_detects_fram_wiring_pointing_at_the_wrong_driver():
    doc = _base_doc()
    doc["instance"][0]["wiring"]["fram_target"] = "neopixel"
    with pytest.raises(AssertionError, match="expected 'fram'"):
        check_fram_wiring_resolves_if_present(doc, "base")


def test_detects_fram_wiring_referencing_a_nonexistent_instance():
    doc = _base_doc()
    doc["instance"] = [i for i in doc["instance"] if i["driver"] != "fram"]
    with pytest.raises(AssertionError, match="no such instance exists"):
        check_fram_wiring_resolves_if_present(doc, "base")


def test_allows_device_wiring_to_be_entirely_absent():
    doc = _base_doc()
    del doc["device"]["wiring"]
    check_device_wiring_resolves_if_present(doc, "base")  # must not raise


def test_allows_only_one_of_led_target_or_fram_target_to_be_present():
    doc = _base_doc()
    del doc["device"]["wiring"]["fram_target"]
    check_device_wiring_resolves_if_present(doc, "base")  # must not raise


def test_detects_device_wiring_pointing_at_the_wrong_driver():
    doc = _base_doc()
    doc["device"]["wiring"]["led_target"] = "fram"
    with pytest.raises(AssertionError, match="expected 'neopixel'"):
        check_device_wiring_resolves_if_present(doc, "base")


def test_detects_device_wiring_referencing_a_nonexistent_instance():
    doc = _base_doc()
    doc["instance"] = [i for i in doc["instance"] if i["driver"] != "neopixel"]
    with pytest.raises(AssertionError, match="no such instance exists"):
        check_device_wiring_resolves_if_present(doc, "base")
