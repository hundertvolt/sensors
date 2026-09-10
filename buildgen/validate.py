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

import ast
from pathlib import Path

from buildgen.buildspec import ADDRESS_CAPABLE_DRIVERS, ALLOWED_INSTANCE_FIELDS, BUS_ATTACHED_DRIVERS, FIXED_ADDRESS_DRIVERS, REQUIRED_TOML_FIELDS
from buildgen.defaults import default_class_defines_attr, default_class_name, default_init_params, find_default_class
from buildgen.driver_registry import SERVICE_DRIVERS, parse_name_constant, resolve_driver
from buildgen.errors import BuildError
from buildgen.limits import parse_limits
from buildgen.model import DeviceModel, InstanceSpec, instance_label, load_device, resolve_instance_key
from buildgen.pico_gpio import I2C_ROLE, SPI_ROLE, gpio_exists
from buildgen.requires_tag import check_requires_tags, parse_requires_tags
from buildgen.value_wiring import ValueWiringField, parse_value_wiring
from buildgen.wiring import WiringField, parse_wiring

_BUS_WIRE_FIELDS = {
    "i2c": ("scl_pin", "sda_pin"),
    "spi": ("sck_pin", "mosi_pin", "miso_pin"),
}
# Real RP2040 bus identities - Pico W exposes exactly two I2C and two SPI peripheral indices, never
# an arbitrary digit (closes the "i2c2"/bare-"i2c" gap - _bus_kind() used to only check the prefix).
_VALID_BUS_IDS = {"i2c0": "i2c", "i2c1": "i2c", "spi0": "spi", "spi1": "spi"}
# bus-table field name -> (role table, the role that field must resolve to). Both fields of a kind
# always appear together in _BUS_WIRE_FIELDS/_BUS_ALLOWED_FIELDS, so a bus table never mixes kinds.
_BUS_PIN_ROLE: "dict[str, tuple[dict[int, tuple[str, str]], str]]" = {
    "scl_pin": (I2C_ROLE, "scl"),
    "sda_pin": (I2C_ROLE, "sda"),
    "sck_pin": (SPI_ROLE, "sck"),
    "mosi_pin": (SPI_ROLE, "mosi"),
    "miso_pin": (SPI_ROLE, "miso"),
}
# Every field a bus table of this kind may declare, in total - its own required wire pins plus
# "frequency" (both i2c/asy_i2c_driver.I2C's own required param, checked separately above for a
# more specific message) and, i2c-only, "timeout" (asy_i2c_driver.I2C's own optional param;
# asy_spi_driver.SPI has none) - itself optional at the bus-table-shape level, only actually
# required when an scd30 instance sits on this specific bus (enforced by that driver's own
# @requires tag, not here).
_BUS_ALLOWED_FIELDS = {
    "i2c": frozenset(_BUS_WIRE_FIELDS["i2c"]) | {"frequency", "timeout"},
    "spi": frozenset(_BUS_WIRE_FIELDS["spi"]),
}
_REQUIRED_DEVICE_FIELDS = ("name", "hostname", "hotspot_password", "conn_fail_to_hotspot", "hotspot_time_min")
_REQUIRED_DEVICE_INT_FIELDS = ("conn_fail_to_hotspot", "hotspot_time_min")
_ALLOWED_DEVICE_FIELDS = frozenset(_REQUIRED_DEVICE_FIELDS) | {"wiring"}

# [device.wiring] fields and which mandatory-infra consumer's own _WIRING they resolve against -
# both fixed and known ahead of time (BUILD_CHAIN_PLAN.md's schema section: exactly these two
# fields exist today), unlike [instance.wiring]'s fully generic per-driver resolution below.
_DEVICE_WIRING_CONSUMERS = {"led_target": ("asy_wifi_service.py", "AsyConnTime", "conn"), "fram_target": ("system_service.py", "SystemService", "sysfunct")}


def _bus_kind(bus_name: str, device: str) -> str:
    kind = _VALID_BUS_IDS.get(bus_name)
    if kind is None:
        raise BuildError(device, f"bus id {bus_name!r} is not a real Pico W bus - valid ids are {sorted(_VALID_BUS_IDS)}", field=bus_name)
    return kind


def _check_device_table(model: DeviceModel) -> None:
    # KNOWN GAP, discovered during this session's own review, pre-existing (not introduced here):
    # `name`/`hostname`/`hotspot_password` are validated below (presence, shape, the
    # SensorStation<name> derivation formula) but this generator never actually wires any of the
    # three into generated code - neither AsyConnTime.__init__ nor any hand-written
    # sensortask_*.py has a constructor-time injection point for them. Hostname/HotspotPW are
    # ConfigManager-persisted runtime values with a single hardcoded shared default
    # ("SensorNode"/"12345678" - asy_wifi_service.py's own _VAL_HOST/_VAL_HOTSPOT_PW), identical
    # across every device's frozen build; confirmed directly that src/sensortask_wozi.py doesn't
    # set them either. So today, every device (hand-written or generated) actually boots with
    # hostname "SensorNode", not "SensorStationWozi" etc., regardless of what devices/*.toml says.
    # Flagged in this session's PR rather than silently left implicit - fixing it needs either a
    # `src/` constructor-time override mechanism (out of this session's narrow-additive-only scope)
    # or a build-artifact-tree config-seeding step (Session 6's territory), not a buildgen/-only fix.
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
    unknown = set(dev) - _ALLOWED_DEVICE_FIELDS
    if unknown:
        raise BuildError(model.device, f"[device] declares unrecognized field(s) {sorted(unknown)} - typo, or copy-pasted from an unrelated table?", field=sorted(unknown)[0])


def _check_bus_tables(model: DeviceModel) -> "dict[str, dict]":
    # A device with zero bus-attached instances (no sensors, no FRAM) is a logically valid,
    # simplest-possible shape - [bus.*] is allowed to be absent/empty entirely. If any instance
    # *does* need a bus, _check_required_fields()'s "references undeclared bus" check catches that
    # downstream; this function only validates the shape of whatever bus tables are actually there.
    buses = model.doc.get("bus", {})
    if not isinstance(buses, dict):
        raise BuildError(model.device, f"[bus] must be a table of bus tables, got {buses!r}")
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
        if "timeout" in bus_table and not (isinstance(bus_table["timeout"], int) and not isinstance(bus_table["timeout"], bool)):
            raise BuildError(model.device, f"bus.{bus_name} ({kind}) timeout must be an int, got {bus_table['timeout']!r}", field="timeout")
        unknown = set(bus_table) - _BUS_ALLOWED_FIELDS[kind]
        if unknown:
            raise BuildError(model.device, f"bus.{bus_name} ({kind}) declares unrecognized field(s) {sorted(unknown)} - typo, or copy-pasted from an unrelated bus kind?", field=sorted(unknown)[0])
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
        spec.limits_schema = parse_limits(info.source_path, model.device, spec.label)
        spec.value_wiring_schema = parse_value_wiring(info.source_path, model.device, spec.label)
        spec.resolved_name = _instance_name(parse_name_constant(info.source_path, model.device, spec.label), spec.name_ext)

        if spec.driver in SERVICE_DRIVERS and spec.name_ext:
            raise BuildError(model.device, f"{spec.label}: singleton service driver {spec.driver!r} must not declare name_ext", instance=spec.label, field="name_ext")


def _instance_name(base_name: str, name_ext: str) -> str:
    return base_name if not name_ext else base_name + "_" + name_ext


def _check_required_fields(model: DeviceModel, buses: "dict[str, dict]") -> None:
    for spec in model.instances.values():
        # §6.3/§8.4/§10.5 item 1: a driver that resolves via driver_registry.resolve_driver() (it's
        # a real asy_<name>_driver.py with a SensorReader/SensorReaderConfig subclass, or a known
        # _OVERRIDES service) but has no entry in buildspec.py's own hand-maintained dicts would
        # otherwise fall through .get(spec.driver, ()) / .get(spec.driver, frozenset()) below and
        # have every one of its real fields flagged as "unrecognized" - technically fail-loud, but
        # with a message that looks like a TOML typo rather than what it actually is. Named
        # explicitly here so a driver-onboarding gap reports its real cause.
        if spec.driver not in REQUIRED_TOML_FIELDS:
            raise BuildError(
                model.device,
                f"{spec.label}: driver {spec.driver!r} resolves via buildgen.driver_registry but has no entry in buildgen.buildspec's REQUIRED_TOML_FIELDS/ALLOWED_INSTANCE_FIELDS - a new driver needs a buildspec.py entry added by hand (see buildspec.py's own module docstring)",
                instance=spec.label,
            )
        for f in REQUIRED_TOML_FIELDS.get(spec.driver, ()):
            if f not in spec.fields:
                raise BuildError(model.device, f"{spec.label} is missing required field {f!r}", instance=spec.label, field=f)
        if spec.driver in BUS_ATTACHED_DRIVERS:
            # A non-string "bus" (e.g. a stray TOML array) would otherwise crash the membership
            # check below with a raw "unhashable type" TypeError instead of a fail-loud BuildError.
            if not isinstance(spec.fields["bus"], str):
                raise BuildError(model.device, f"{spec.label}.bus must be a string, got {spec.fields['bus']!r}", instance=spec.label, field="bus")
            if spec.fields["bus"] not in buses:
                raise BuildError(model.device, f"{spec.label} references undeclared bus {spec.fields['bus']!r}", instance=spec.label, field="bus")
        if "address" in spec.fields and spec.driver not in ADDRESS_CAPABLE_DRIVERS:
            raise BuildError(model.device, f"{spec.label} declares an address field, but {spec.driver!r} has no address-select pin (see buildgen.buildspec.ADDRESS_CAPABLE_DRIVERS)", instance=spec.label, field="address")
        # These three all reach codegen.py's hex()/str() argument-building unvalidated otherwise -
        # a wrong type (e.g. a quoted "0x77" string for address) would raise a raw TypeError from
        # hex(), or - for trigger_sec, which only ever goes through str() - silently render as a
        # bare, unquoted Python identifier token that ast.parse() itself can't distinguish from a
        # real int literal (BuildError catches it here instead of producing subtly-broken output).
        for f in ("address", "max_size", "trigger_sec"):
            if f in spec.fields and not (isinstance(spec.fields[f], int) and not isinstance(spec.fields[f], bool)):
                raise BuildError(model.device, f"{spec.label}.{f} must be an int, got {spec.fields[f]!r}", instance=spec.label, field=f)
        # Catch-all: any field beyond "driver"/"name_ext" (structural, handled by model.py) and
        # this driver's own required+optional set is a copy-paste/typo error (BUILD_CHAIN_PLAN.md's
        # "plain wrong/missing/copy-pasted fields") - e.g. an "irq_pin" left over from copying a
        # scd30 block to make a new sgp40 instance, silently ignored by codegen otherwise since it
        # never appears in any driver's own _build_call() branch.
        unknown = set(spec.fields) - {"driver", "name_ext"} - ALLOWED_INSTANCE_FIELDS.get(spec.driver, frozenset())
        if unknown:
            raise BuildError(model.device, f"{spec.label} declares unrecognized field(s) {sorted(unknown)} for driver {spec.driver!r}", instance=spec.label, field=sorted(unknown)[0])


def _check_limits(model: DeviceModel) -> None:
    # A driver-declared _LIMITS field only ever names an already-type-checked int field
    # (_check_required_fields runs before this in build_model()'s pipeline) - no isinstance guard
    # needed here the way _check_gpio_collisions' claim() needs one for raw, unchecked TOML input.
    for spec in model.instances.values():
        for lf in spec.limits_schema:
            if lf.toml_field not in spec.fields:
                continue
            value = spec.fields[lf.toml_field]
            if lf.choices is not None:
                if value not in lf.choices:
                    raise BuildError(
                        model.device,
                        f"{spec.label}.{lf.toml_field}={value!r} is not one of this driver's legal values {sorted(lf.choices)}",
                        instance=spec.label,
                        field=lf.toml_field,
                    )
                continue
            if (lf.min is not None and value < lf.min) or (lf.max is not None and value > lf.max):
                raise BuildError(
                    model.device,
                    f"{spec.label}.{lf.toml_field}={value!r} is outside this driver's legal range ({lf.min}, {lf.max})",
                    instance=spec.label,
                    field=lf.toml_field,
                )


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


def _check_instance_label_collisions(model: DeviceModel) -> None:
    # §7.2(C)/§8.5/§10.5 item 2: instance_label() (the codegen-time Python-variable identity,
    # f"{driver}_{name_ext}" if name_ext else driver) is a different identity space from
    # resolved_name (the REST-key identity, already checked above) - unreachable with today's 6 real
    # driver names (none contains an underscore that could line up with another driver+name_ext
    # combination), but structurally latent for a future driver whose module name does.
    seen: dict[str, tuple[str, str]] = {}
    for key in model.instances:
        label = instance_label(key)
        existing = seen.get(label)
        if existing is not None:
            raise BuildError(
                model.device,
                f"instance_label collision: {key!r} and {existing!r} both resolve to the generated Python variable name {label!r} - rename one driver module or its name_ext",
                instance=instance_label(key),
            )
        seen[label] = key


def _check_gpio_collisions(model: DeviceModel, buses: "dict[str, dict]") -> None:
    claims: dict[int, str] = {}

    def claim(pin: object, owner: str, field: str) -> None:
        if pin is None:
            return
        if not (isinstance(pin, int) and not isinstance(pin, bool)):
            raise BuildError(model.device, f"{owner}.{field} value {pin!r} is not an int", instance=owner, field=field)
        # Applies to every claimed pin device-wide (bus wire pins and instance-exclusive
        # cs_pin/irq_pin/pin alike) - real GPIO number, not one of the wireless-reserved four.
        if not gpio_exists(pin):
            raise BuildError(
                model.device,
                f"{owner}.{field}=GP{pin} is not a usable Pico W GPIO - must be 0-29, excluding the wireless-reserved GP23/24/25/29",
                instance=owner,
                field=field,
            )
        existing = claims.get(pin)
        if existing is not None:
            raise BuildError(model.device, f"GPIO{pin} claimed twice - by {existing!r} and by {owner!r} ({field})", instance=owner, field=field)
        claims[pin] = owner

    for bus_name, bus_table in buses.items():
        for f in ("scl_pin", "sda_pin", "sck_pin", "mosi_pin", "miso_pin"):
            if f not in bus_table:
                continue
            pin = bus_table[f]
            claim(pin, f"bus.{bus_name}", f)
            # Bus-pin-only: this specific GPIO must be hardwired to *this* bus's own peripheral
            # index, in the *role* this field claims (SDA vs SCL, MISO vs SCK vs MOSI) - not just
            # any legal, unclaimed GPIO. cs_pin/irq_pin/neopixel's "pin" have no peripheral role to
            # check (see the claim() call below), so this half only runs for bus wire pins.
            role_table, expected_role = _BUS_PIN_ROLE[f]
            info = role_table.get(pin)
            if info is None:
                kind = "I2C" if role_table is I2C_ROLE else "SPI"
                raise BuildError(model.device, f"bus.{bus_name}.{f}=GP{pin} has no {kind} function on the Pico W", instance=f"bus.{bus_name}", field=f)
            actual_bus, actual_role = info
            if actual_bus != bus_name:
                raise BuildError(model.device, f"bus.{bus_name}.{f}=GP{pin} is wired to {actual_bus}, not {bus_name}", instance=f"bus.{bus_name}", field=f)
            if actual_role != expected_role:
                raise BuildError(
                    model.device,
                    f"bus.{bus_name}.{f}=GP{pin} is {bus_name}'s {actual_role.upper()} pin, not its {expected_role.upper()} pin - pins transposed?",
                    instance=f"bus.{bus_name}",
                    field=f,
                )
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


def _check_source_field_reference(model: DeviceModel, value: object, consumer_label: str, toml_field: str) -> None:
    # Shared by warn_*'s per-signal getters and _VALUE_WIRING's per-value measurement wiring (§2.9)
    # - both are the same generic {source, field} shape, resolved by attribute name alone rather
    # than a fixed producer_class.
    if not isinstance(value, dict) or "source" not in value or "field" not in value:
        raise BuildError(model.device, f"{consumer_label}'s wiring.{toml_field} must be a {{source, field}} table", instance=consumer_label, field=toml_field)
    # A non-string "source" would otherwise crash resolve_instance_key()'s `"_" in value` check
    # with a raw TypeError instead of a fail-loud BuildError.
    if not isinstance(value["source"], str) or not isinstance(value["field"], str):
        raise BuildError(model.device, f"{consumer_label}'s wiring.{toml_field}.source/field must both be strings", instance=consumer_label, field=toml_field)
    source_key = resolve_instance_key(model, value["source"])
    if source_key not in model.instances:
        raise BuildError(model.device, f"{consumer_label}'s wiring.{toml_field}.source={value['source']!r} does not resolve to any declared instance", instance=consumer_label, field=toml_field)


def _check_default_provider_params(model: DeviceModel, spec: InstanceSpec, toml_field: str, value: dict) -> ast.ClassDef:
    # Shared by _WIRING-based defaults (signal_sink) and _VALUE_WIRING-based defaults
    # (temperature_source/humidity_source) - §2.4's "the class definition IS the schema": a
    # `_Default<Field>`'s own `__init__` signature says what keys a `{default = true, ...}`
    # sub-table may/must carry, discovered via AST the same way _WIRING/_LIMITS already are.
    assert spec.driver_info is not None
    class_node = find_default_class(spec.driver_info.source_path, model.device, spec.label, toml_field)
    if class_node is None:
        raise BuildError(
            model.device,
            f"{spec.label}'s wiring.{toml_field} opts into the default, but {spec.driver_info.source_path.name} defines no {default_class_name(toml_field)} class",
            instance=spec.label,
            field=toml_field,
        )
    params = default_init_params(class_node, spec.driver_info.source_path, model.device, spec.label)
    allowed = {p.name for p in params}
    required = {p.name for p in params if not p.has_default}
    given = set(value) - {"default"}
    unknown = given - allowed
    if unknown:
        raise BuildError(model.device, f"{spec.label}'s wiring.{toml_field} default sub-table has unrecognized key(s) {sorted(unknown)} for {class_node.name}", instance=spec.label, field=toml_field)
    missing = required - given
    if missing:
        raise BuildError(model.device, f"{spec.label}'s wiring.{toml_field} default sub-table is missing required key(s) {sorted(missing)} for {class_node.name}", instance=spec.label, field=toml_field)
    return class_node


def _check_default_selection(model: DeviceModel, spec: InstanceSpec, wf: WiringField, toml_field: str, value: dict) -> None:
    class_node = _check_default_provider_params(model, spec, toml_field, value)
    # §2.8's second open question, resolved "yes" for attr-mode _WIRING fields only (signal_sink):
    # verify the default provider actually defines the target attribute/method - same
    # fail-loud-at-generation-time philosophy as every other buildgen/ check. The generalized
    # per-value mechanism (_VALUE_WIRING) needs no equivalent check - every _Default<Field> there
    # follows one fixed, hardcoded "get_data() returns an object with a .value attribute" contract
    # instead (see _check_default_value_selection below).
    if wf.mode == "attr" and not default_class_defines_attr(class_node, wf.target):
        raise BuildError(
            model.device,
            f"{spec.label}'s wiring.{toml_field} default provider {class_node.name} defines no {wf.target!r} attribute/method - required for 'attr' mode wiring",
            instance=spec.label,
            field=toml_field,
        )


def _check_default_value_selection(model: DeviceModel, spec: InstanceSpec, vwf: ValueWiringField) -> None:
    value = spec.wiring[vwf.toml_field]
    assert isinstance(value, dict)
    _check_default_provider_params(model, spec, vwf.toml_field, value)


def _check_instance_wiring(model: DeviceModel, src_dir: Path) -> None:
    for spec in model.instances.values():
        value_wiring_fields = {vwf.toml_field for vwf in spec.value_wiring_schema}
        for toml_field, value in spec.wiring.items():
            if toml_field.startswith("warn_"):
                continue  # per-signal getters (source/field pairs) - checked separately below
            if toml_field in value_wiring_fields:
                continue  # _VALUE_WIRING field (§2.9) - checked separately by _check_value_wiring()
            wf = _resolve_wiring_field(spec.wiring_schema, toml_field)
            if wf is None:
                raise BuildError(model.device, f"{spec.label} declares wiring.{toml_field}, but its driver has no matching _WIRING entry", instance=spec.label, field=toml_field)
            # §2's wiring-defaults mechanism: a {default = true, ...} sub-table opts out of
            # resolving a real instance reference entirely - branch at the very top, before any
            # string-only handling runs (§10.1 item 1's resolved branch-point decision).
            if isinstance(value, dict) and value.get("default") is True:
                _check_default_selection(model, spec, wf, toml_field, value)
                continue
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
            _check_source_field_reference(model, value, spec.label, toml_field)


def _check_value_wiring(model: DeviceModel) -> None:
    # §2.9's per-value measurement wiring: each field independently resolves to either a real
    # {source, field} reference (any producer, matched by attribute name) or an explicit
    # {default = true, ...} opt-in (§2) - never silently defaulted just because it's absent.
    for spec in model.instances.values():
        for vwf in spec.value_wiring_schema:
            value = spec.wiring.get(vwf.toml_field)
            if value is None:
                if vwf.required:
                    raise BuildError(model.device, f"{spec.label} is missing required wiring.{vwf.toml_field}", instance=spec.label, field=vwf.toml_field)
                continue
            if isinstance(value, dict) and value.get("default") is True:
                _check_default_value_selection(model, spec, vwf)
                continue
            _check_source_field_reference(model, value, spec.label, vwf.toml_field)


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

    # Required-field enforcement, mirroring _check_instance_wiring's own pass below - both known
    # device-wiring fields are optional today, so this was previously untested/untriggered dead
    # code potential; kept in sync so a future required _WIRING entry on conn/sysfunct can't
    # silently go unenforced the way [instance.wiring]'s required fields already are.
    for toml_field, (module_file, _class_name, consumer_label) in _DEVICE_WIRING_CONSUMERS.items():
        if toml_field in wiring:
            continue
        schema = parse_wiring(src_dir / module_file, model.device, consumer_label)
        wf = _resolve_wiring_field(schema, toml_field)
        if wf is not None and wf.required:
            raise BuildError(model.device, f"[device.wiring] is missing required field {toml_field!r}", field=toml_field)


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
    _check_limits(model)
    _check_all_buses_used(model, buses)
    _check_instance_name_collisions(model)
    _check_instance_label_collisions(model)
    _check_gpio_collisions(model, buses)
    _check_address_collisions(model)
    _check_instance_wiring(model, src_dir)
    _check_value_wiring(model)
    _check_device_wiring(model, src_dir)
    _check_requires_tags(model, buses)
    return model


__all__ = ["build_model", "instance_label", "InstanceSpec"]
