"""Smoke/shape/collision checks for devices/*.toml (BUILD_CHAIN_PLAN.md Session 2's own
deliverable - the 6 real device config files). This is deliberately NOT the full generator
validation pass (misconfigured/malformed-TOML abort paths, driver-class resolution, topological
sort) - that's Session 3's own build-tooling quality bar, run against a generator that doesn't
exist yet. This suite only proves the 6 real files parse as valid TOML, match the documented shape
(BUILD_CHAIN_PLAN.md's "Device TOML schema"), and are free of the resource collisions a human
author could introduce (global GPIO-pin exclusivity, per-bus address exclusivity, instance-name
collision) - checked by hand here since no automated validator exists yet (this initiative's own
"Global-resource-collision awareness" priming note)."""

import tomllib
from pathlib import Path

import pytest

DEVICE_NAMES = ["dev", "wozi", "arzi", "klkizi", "grkizi", "schlafzi"]

# Every device is expected to declare exactly these singleton-service driver kinds, plus scd30 and
# sgp40 (every real device has both - BUILD_CHAIN_PLAN.md's priming note). bmp3xx is present only
# on wozi/dev (see DEVICE_BMP3XX below) - the one real per-device sensor-set difference today.
_ALWAYS_PRESENT_DRIVERS = {"scd30", "sgp40", "fram", "neopixel", "wifi", "ntp", "system", "notification"}
_DEVICES_WITH_BMP3XX = {"wozi", "dev"}

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
    doc = _load(devices_dir, device)
    buses = doc["bus"]
    assert buses, "every device declares at least one bus"
    for bus_name, bus_table in buses.items():
        kind = _bus_kind(bus_name)
        required = _REQUIRED_BUS_PIN_FIELDS[kind]
        missing = required - bus_table.keys()
        assert not missing, f"{device}: bus.{bus_name} is missing required field(s) {missing}"
        if kind == "i2c":
            # asy_i2c_driver.I2C takes a real frequency param; asy_spi_driver.SPI has no
            # frequency parameter at all (confirmed directly against src/asy_spi_driver.py's own
            # SPI.__init__/init() - real RP2040 SPI here has no configurable clock rate exposed by
            # this driver), so spi buses never carry this field.
            assert isinstance(bus_table.get("frequency"), int)
        else:
            assert "frequency" not in bus_table, f"{device}: bus.{bus_name} (spi) declares frequency - asy_spi_driver.SPI has no such parameter"
        # cs_pin is an instance-exclusive resource (its own instance's CS pin), never a bus-shared
        # field - BUILD_CHAIN_PLAN.md's own "Build/generator script quality bar" schema-shape
        # requirement; kept out of every bus table here even though the plan's own illustrative
        # example inconsistently duplicates it there too (flagged in this PR's description).
        assert "cs_pin" not in bus_table, f"{device}: bus.{bus_name} declares cs_pin - that belongs on the owning instance, not the shared bus"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_instance_list_has_the_expected_driver_kinds(devices_dir: Path, device: str):
    doc = _load(devices_dir, device)
    drivers = [inst["driver"] for inst in doc["instance"]]
    expected = set(_ALWAYS_PRESENT_DRIVERS)
    if device in _DEVICES_WITH_BMP3XX:
        expected.add("bmp3xx")
    assert set(drivers) == expected, f"{device}: instance driver set {sorted(set(drivers))} != expected {sorted(expected)}"
    # No duplicate driver kind anywhere - none of the 6 real devices has two instances of the same
    # driver type today (BUILD_CHAIN_PLAN.md priming note).
    assert len(drivers) == len(set(drivers)), f"{device}: duplicate driver kind in instance list"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_instance_referencing_a_bus_uses_a_declared_bus(devices_dir: Path, device: str):
    doc = _load(devices_dir, device)
    bus_ids = set(doc["bus"].keys())
    for inst in doc["instance"]:
        if "bus" in inst:
            assert inst["bus"] in bus_ids, f"{device}: instance {inst['driver']!r} references undeclared bus {inst['bus']!r}"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_sgp40_wiring_resolves_to_a_real_scd30_instance(devices_dir: Path, device: str):
    doc = _load(devices_dir, device)
    instances = {(inst["driver"], inst.get("name_ext", "")): inst for inst in doc["instance"]}
    sgp40 = instances[("sgp40", "")]
    wiring = sgp40["wiring"]
    assert wiring["comp_source"] == "scd30"
    assert ("scd30", "") in instances, f"{device}: sgp40's comp_source references 'scd30' but no such instance exists"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_no_global_gpio_pin_collision(devices_dir: Path, device: str):
    # One flat namespace per device (BUILD_CHAIN_PLAN.md's "Global-resource-collision awareness"):
    # every bus's own wire pins, plus every instance's exclusive cs_pin/irq_pin/pin. `address` is
    # deliberately excluded - it's a per-bus logical address, not a physical GPIO pin.
    doc = _load(devices_dir, device)
    claims: dict[int, str] = {}

    def claim(pin: object, owner: str) -> None:
        if pin is None:
            return
        assert isinstance(pin, int), f"{device}: {owner}'s pin value {pin!r} is not an int"
        existing = claims.get(pin)
        assert existing is None, f"{device}: GPIO{pin} claimed twice - by {existing!r} and by {owner!r}"
        claims[pin] = owner

    for bus_name, bus_table in doc["bus"].items():
        for field in ("scl_pin", "sda_pin", "sck_pin", "mosi_pin", "miso_pin"):
            if field in bus_table:
                claim(bus_table[field], f"bus.{bus_name}.{field}")

    for inst in doc["instance"]:
        label = inst["driver"] + (f"_{inst['name_ext']}" if inst.get("name_ext") else "")
        for field in ("cs_pin", "irq_pin", "pin"):
            if field in inst:
                claim(inst[field], f"instance[{label}].{field}")


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_no_per_bus_address_collision(devices_dir: Path, device: str):
    doc = _load(devices_dir, device)
    per_bus: dict[str, dict[int, str]] = {}
    for inst in doc["instance"]:
        if "address" not in inst or "bus" not in inst:
            continue
        bus_claims = per_bus.setdefault(inst["bus"], {})
        existing = bus_claims.get(inst["address"])
        assert existing is None, f"{device}: bus {inst['bus']!r} address {inst['address']:#x} claimed by both {existing!r} and {inst['driver']!r}"
        bus_claims[inst["address"]] = inst["driver"]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_no_instance_name_collision(devices_dir: Path, device: str):
    # instance_name(driver, name_ext) collision (SPECIFICATION.md Part C.14.1) - not reachable by
    # any of the 6 real devices today (none has two instances of the same driver kind, checked by
    # test_instance_list_has_the_expected_driver_kinds above), but checked directly here per this
    # category's own standing rule rather than assumed.
    doc = _load(devices_dir, device)
    names = [inst["driver"] + (f"_{inst['name_ext']}" if inst.get("name_ext") else "") for inst in doc["instance"]]
    assert len(names) == len(set(names)), f"{device}: instance name collision in {names}"


def test_bmp3xx_only_present_on_wozi_and_dev(devices_dir: Path):
    # arzi/klkizi/grkizi/schlafzi have no BMP3xx at all (confirmed directly against
    # modules/sensortask-arzi.py / modules/sensortask-neu.py - neither imports/constructs one).
    for device in DEVICE_NAMES:
        doc = _load(devices_dir, device)
        drivers = {inst["driver"] for inst in doc["instance"]}
        assert ("bmp3xx" in drivers) == (device in _DEVICES_WITH_BMP3XX)


def test_klkizi_grkizi_schlafzi_share_identical_wiring():
    # Currently identical hardware to each other (README.md/BUILD_CHAIN_PLAN.md) - only device
    # identity (name/hostname) may differ between the three, everything else (buses, instances)
    # must be byte-for-byte identical.
    repo_root = Path(__file__).resolve().parent.parent
    devices_dir = repo_root / "devices"
    docs = {name: _load(devices_dir, name) for name in ("klkizi", "grkizi", "schlafzi")}
    for name, doc in docs.items():
        del doc["device"]["name"]
        del doc["device"]["hostname"]
    bodies = list(docs.values())
    assert bodies[0] == bodies[1] == bodies[2]
