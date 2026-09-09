"""The full validation pass (BUILD_CHAIN_PLAN.md's "Build/generator script quality bar"):
structural shape, every global-resource-collision class, and wiring-reference resolution. Builds
on `buildgen.model.load_device()`'s already-parsed `DeviceModel`, filling in each `InstanceSpec`'s
`driver_info`/`wiring_schema`/`requires_tags`/`resolved_name` along the way. Every check here
raises `buildgen.errors.BuildError` naming the device/instance/field responsible - never a bare
`assert` - so a caller (the CPython test suite, or a future real build script) gets one specific,
human-readable reason the build was aborted, not a generic failure.

`build_model()` is the single entry point: call it, and either it raises (details above) or it
returns a `DeviceModel` whose every instance is fully resolved and every collision/reference check
already passed - safe to hand straight to `buildgen.graph`/`buildgen.codegen`."""

from pathlib import Path

from buildgen.buildspec import ADDRESS_CAPABLE_DRIVERS, BUS_ATTACHED_DRIVERS, FIXED_ADDRESS_DRIVERS, REQUIRED_TOML_FIELDS
from buildgen.driver_registry import SERVICE_DRIVERS, parse_name_constant, resolve_driver
from buildgen.errors import BuildError
from buildgen.model import DeviceModel, InstanceSpec, instance_label, load_device, resolve_instance_key
from buildgen.requires_tag import check_requires_tags, parse_requires_tags
from buildgen.wiring import WiringField, parse_wiring

_BUS_WIRE_FIELDS = {
    "i2c": ("scl_pin", "sda_pin"),
    "spi": ("sck_pin", "mosi_pin", "miso_pin"),
}
_REQUIRED_DEVICE_FIELDS = ("name", "hostname", "hotspot_password", "conn_fail_to_hotspot", "hotspot_time_min")
_REQUIRED_DEVICE_INT_FIELDS = ("conn_fail_to_hotspot", "hotspot_time_min")

# [device.wiring] fields and which mandatory-infra consumer's own _WIRING they resolve against -
# both fixed and known ahead of time (BUILD_CHAIN_PLAN.md's schema section: exactly these two
# fields exist today), unlike [instance.wiring]'s fully generic per-driver resolution below.
_DEVICE_WIRING_CONSUMERS = {"led_target": ("asy_wifi_service.py", "AsyConnTime", "conn"), "fram_target": ("system_service.py", "SystemService", "sysfunct")}


def _bus_kind(bus_name: str, device: str) -> str:
    for kind in _BUS_WIRE_FIELDS:
        if bus_name.startswith(kind):
            return kind
    raise BuildError(device, f"bus id {bus_name!r} doesn't start with a recognized kind (i2c/spi)", field=bus_name)


def _check_device_table(model: DeviceModel) -> None:
    dev = model.doc.get("device")
    if not isinstance(dev, dict):
        raise BuildError(model.device, "missing [device] table")
    for f in _REQUIRED_DEVICE_FIELDS:
        if f not in dev:
            raise BuildError(model.device, f"[device] is missing required field {f!r}", field=f)
    for f in _REQUIRED_DEVICE_INT_FIELDS:
        if not (isinstance(dev[f], int) and not isinstance(dev[f], bool)):
            raise BuildError(model.device, f"[device].{f} must be an int, got {dev[f]!r}", field=f)
    if not (isinstance(dev["name"], str) and dev["name"]):
        raise BuildError(model.device, "[device].name must be a non-empty string", field="name")
    expected_hostname = "SensorStation" + dev["name"]
    if dev["hostname"] != expected_hostname:
        raise BuildError(model.device, f"[device].hostname is {dev['hostname']!r}, expected {expected_hostname!r} (SensorStation<name>)", field="hostname")


def _check_bus_tables(model: DeviceModel) -> "dict[str, dict]":
    buses = model.doc.get("bus")
    if not isinstance(buses, dict) or not buses:
        raise BuildError(model.device, "no [bus.*] table declared")
    for bus_name, bus_table in buses.items():
        if not isinstance(bus_table, dict):
            raise BuildError(model.device, f"bus.{bus_name} is not a table", field=bus_name)
        kind = _bus_kind(bus_name, model.device)
        for f in _BUS_WIRE_FIELDS[kind]:
            if f not in bus_table:
                raise BuildError(model.device, f"bus.{bus_name} ({kind}) is missing required field {f!r}", field=f)
        if "cs_pin" in bus_table:
            raise BuildError(model.device, f"bus.{bus_name} declares cs_pin - that's an instance-exclusive resource, not a shared bus field", field="cs_pin")
        if kind == "i2c" and not (isinstance(bus_table.get("frequency"), int) and not isinstance(bus_table.get("frequency"), bool)):
            raise BuildError(model.device, f"bus.{bus_name} (i2c) is missing an int frequency", field="frequency")
        if kind == "spi" and "frequency" in bus_table:
            raise BuildError(model.device, f"bus.{bus_name} (spi) declares frequency - asy_spi_driver.SPI has no such parameter", field="frequency")
    return buses


def _resolve_instances(model: DeviceModel, src_dir: Path) -> None:
    # No separate "singleton declared twice" check needed: a singleton service instance is always
    # forced to name_ext="" (below), so two of the same singleton driver always share the exact
    # same (driver, name_ext) key - model.load_device() already rejects that as a duplicate
    # [[instance]] entry before this function ever runs, making a second check here dead code.
    for spec in model.instances.values():
        info = resolve_driver(spec.driver, src_dir, model.device)
        spec.driver_info = info
        spec.wiring_schema = parse_wiring(info.source_path, model.device, spec.label)
        spec.requires_tags = parse_requires_tags(info.source_path, model.device, spec.label)
        spec.resolved_name = _instance_name(parse_name_constant(info.source_path, model.device, spec.label), spec.name_ext)

        if spec.driver in SERVICE_DRIVERS and spec.name_ext:
            raise BuildError(model.device, f"{spec.label}: singleton service driver {spec.driver!r} must not declare name_ext", instance=spec.label, field="name_ext")


def _instance_name(base_name: str, name_ext: str) -> str:
    return base_name if not name_ext else base_name + "_" + name_ext


def _check_required_fields(model: DeviceModel, buses: "dict[str, dict]") -> None:
    for spec in model.instances.values():
        for f in REQUIRED_TOML_FIELDS.get(spec.driver, ()):
            if f not in spec.fields:
                raise BuildError(model.device, f"{spec.label} is missing required field {f!r}", instance=spec.label, field=f)
        if spec.driver in BUS_ATTACHED_DRIVERS and spec.fields["bus"] not in buses:
            raise BuildError(model.device, f"{spec.label} references undeclared bus {spec.fields['bus']!r}", instance=spec.label, field="bus")
        if "address" in spec.fields and spec.driver not in ADDRESS_CAPABLE_DRIVERS:
            raise BuildError(model.device, f"{spec.label} declares an address field, but {spec.driver!r} has no address-select pin (see buildgen.buildspec.ADDRESS_CAPABLE_DRIVERS)", instance=spec.label, field="address")


def _check_all_buses_used(model: DeviceModel, buses: "dict[str, dict]") -> None:
    used = {spec.fields["bus"] for spec in model.instances.values() if "bus" in spec.fields}
    orphans = set(buses) - used
    if orphans:
        raise BuildError(model.device, f"bus(es) {sorted(orphans)} declared but never referenced by any instance")


def _check_instance_name_collisions(model: DeviceModel) -> None:
    seen: dict[str, str] = {}
    for spec in model.instances.values():
        assert spec.resolved_name is not None
        existing = seen.get(spec.resolved_name)
        if existing is not None:
            raise BuildError(
                model.device,
                f"instance_name collision: {spec.label!r} and {existing!r} both resolve to {spec.resolved_name!r} - give one a disambiguating name_ext",
                instance=spec.label,
            )
        seen[spec.resolved_name] = spec.label


def _check_gpio_collisions(model: DeviceModel, buses: "dict[str, dict]") -> None:
    claims: dict[int, str] = {}

    def claim(pin: object, owner: str, field: str) -> None:
        if pin is None:
            return
        if not (isinstance(pin, int) and not isinstance(pin, bool)):
            raise BuildError(model.device, f"{owner}.{field} value {pin!r} is not an int", instance=owner, field=field)
        existing = claims.get(pin)
        if existing is not None:
            raise BuildError(model.device, f"GPIO{pin} claimed twice - by {existing!r} and by {owner!r} ({field})", instance=owner, field=field)
        claims[pin] = owner

    for bus_name, bus_table in buses.items():
        for f in ("scl_pin", "sda_pin", "sck_pin", "mosi_pin", "miso_pin"):
            if f in bus_table:
                claim(bus_table[f], f"bus.{bus_name}", f)
    for spec in model.instances.values():
        for f in ("cs_pin", "irq_pin", "pin"):
            if f in spec.fields:
                claim(spec.fields[f], spec.label, f)


def _check_address_collisions(model: DeviceModel) -> None:
    per_bus_explicit: dict[str, dict[int, str]] = {}
    # Fixed-address collision is scoped to (bus, driver kind): two different fixed-address chip
    # types (e.g. scd30 + sgp40) on the same bus don't collide - each has its own distinct hardware
    # address - only two instances of the *same* fixed-address driver sharing a bus do.
    per_bus_driver_fixed: dict[tuple[str, str], list[str]] = {}
    for spec in model.instances.values():
        if "bus" not in spec.fields:
            continue
        bus = spec.fields["bus"]
        if "address" in spec.fields:
            claims = per_bus_explicit.setdefault(bus, {})
            existing = claims.get(spec.fields["address"])
            if existing is not None:
                raise BuildError(model.device, f"bus {bus!r}: address {spec.fields['address']:#x} claimed by both {existing!r} and {spec.label!r}", instance=spec.label, field="address")
            claims[spec.fields["address"]] = spec.label
        elif spec.driver in FIXED_ADDRESS_DRIVERS:
            per_bus_driver_fixed.setdefault((bus, spec.driver), []).append(spec.label)
    for (bus, driver), labels in per_bus_driver_fixed.items():
        if len(labels) > 1:
            raise BuildError(model.device, f"bus {bus!r}: {labels} are all {driver!r}-family instances with no address field - their hardware address is fixed, so they can't be told apart on the same bus", instance=labels[-1])


def _resolve_wiring_field(schema: "tuple[WiringField, ...]", toml_field: str) -> "WiringField | None":
    for wf in schema:
        if wf.toml_field == toml_field:
            return wf
    return None


def _check_wiring_reference(model: DeviceModel, wf: WiringField, target_key_str: str, consumer_label: str, toml_field: str) -> None:
    target_key = resolve_instance_key(model, target_key_str)
    target = model.instances.get(target_key)
    if target is None:
        raise BuildError(model.device, f"{consumer_label}'s wiring.{toml_field}={target_key_str!r} does not resolve to any declared instance", instance=consumer_label, field=toml_field)
    assert target.driver_info is not None
    if target.driver_info.class_name != wf.producer_class:
        raise BuildError(
            model.device,
            f"{consumer_label}'s wiring.{toml_field}={target_key_str!r} resolves to a {target.driver_info.class_name}, but {wf.mode!r} wiring requires a {wf.producer_class}",
            instance=consumer_label,
            field=toml_field,
        )


def _check_instance_wiring(model: DeviceModel, src_dir: Path) -> None:
    for spec in model.instances.values():
        for toml_field, value in spec.wiring.items():
            if toml_field.startswith("warn_"):
                continue  # per-signal getters (source/field pairs) - checked separately below
            wf = _resolve_wiring_field(spec.wiring_schema, toml_field)
            if wf is None:
                raise BuildError(model.device, f"{spec.label} declares wiring.{toml_field}, but its driver has no matching _WIRING entry", instance=spec.label, field=toml_field)
            if not isinstance(value, str):
                raise BuildError(model.device, f"{spec.label}'s wiring.{toml_field} must be a string instance reference, got {value!r}", instance=spec.label, field=toml_field)
            _check_wiring_reference(model, wf, value, spec.label, toml_field)
        for wf in spec.wiring_schema:
            if wf.required and wf.toml_field not in spec.wiring:
                raise BuildError(model.device, f"{spec.label} is missing required wiring.{wf.toml_field}", instance=spec.label, field=wf.toml_field)

        # Per-signal getters (notification's warn_co2/warn_voc/warn_hum): a related but separate
        # mechanism from _WIRING (SPECIFICATION.md Part C.14.3) - {source, field} sub-tables,
        # each individually optional; `source` still resolves against the same driver/name_ext
        # identity space as every other wiring reference.
        for toml_field, value in spec.wiring.items():
            if not toml_field.startswith("warn_"):
                continue
            if not isinstance(value, dict) or "source" not in value or "field" not in value:
                raise BuildError(model.device, f"{spec.label}'s wiring.{toml_field} must be a {{source, field}} table", instance=spec.label, field=toml_field)
            source_key = resolve_instance_key(model, value["source"])
            if source_key not in model.instances:
                raise BuildError(model.device, f"{spec.label}'s wiring.{toml_field}.source={value['source']!r} does not resolve to any declared instance", instance=spec.label, field=toml_field)


def _check_device_wiring(model: DeviceModel, src_dir: Path) -> None:
    wiring = model.doc.get("device", {}).get("wiring", {})
    for toml_field, value in wiring.items():
        consumer_info = _DEVICE_WIRING_CONSUMERS.get(toml_field)
        if consumer_info is None:
            raise BuildError(model.device, f"[device.wiring] declares unknown field {toml_field!r}", field=toml_field)
        module_file, _class_name, consumer_label = consumer_info
        schema = parse_wiring(src_dir / module_file, model.device, consumer_label)
        wf = _resolve_wiring_field(schema, toml_field)
        if wf is None:
            raise BuildError(model.device, f"[device.wiring].{toml_field} declared, but {module_file} has no matching _WIRING entry", field=toml_field)
        if not isinstance(value, str):
            raise BuildError(model.device, f"[device.wiring].{toml_field} must be a string instance reference, got {value!r}", field=toml_field)
        _check_wiring_reference(model, wf, value, "device.wiring", toml_field)


def _check_requires_tags(model: DeviceModel, buses: "dict[str, dict]") -> None:
    for spec in model.instances.values():
        if not spec.requires_tags:
            continue
        bus_name = spec.fields.get("bus")
        if bus_name is None:
            raise BuildError(model.device, f"{spec.label} declares @requires bus tags but has no 'bus' field", instance=spec.label)
        check_requires_tags(spec.requires_tags, buses[bus_name], model.device, spec.label, bus_name)


def build_model(toml_path: Path, src_dir: Path) -> DeviceModel:
    model = load_device(toml_path)
    _check_device_table(model)
    buses = _check_bus_tables(model)
    _resolve_instances(model, src_dir)
    _check_required_fields(model, buses)
    _check_all_buses_used(model, buses)
    _check_instance_name_collisions(model)
    _check_gpio_collisions(model, buses)
    _check_address_collisions(model)
    _check_instance_wiring(model, src_dir)
    _check_device_wiring(model, src_dir)
    _check_requires_tags(model, buses)
    return model


__all__ = ["build_model", "instance_label", "InstanceSpec"]
