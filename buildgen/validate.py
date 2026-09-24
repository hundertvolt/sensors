"""The full validation pass (SPECIFICATION.md Part L.5): structural shape, every
global-resource-collision class, and wiring-reference resolution. `build_model()` either raises a
`BuildError` naming device/instance/field, or returns a fully-resolved, safe-to-generate model."""

import ast
import importlib.util
from pathlib import Path

import tomllib

from buildgen.buildspec import ADDRESS_CAPABLE_DRIVERS, ALLOWED_INSTANCE_FIELDS, BUS_ATTACHED_DRIVERS, BUS_KIND_BY_DRIVER, FIXED_ADDRESS_DRIVERS, REQUIRED_TOML_FIELDS
from buildgen.defaults import default_class_defines_attr, default_class_name, default_init_params, find_default_class
from buildgen.driver_registry import SINGLETON_SERVICE_DRIVERS, parse_name_constant, resolve_driver
from buildgen.errors import BuildError
from buildgen.limits import LimitField, parse_limits
from buildgen.model import DeviceModel, InstanceSpec, TomlDoc, instance_label, load_device, lwip_macros, resolve_instance_key
from buildgen.pico_gpio import I2C_ROLE, SPI_ROLE, UART_ROLE, gpio_exists
from buildgen.requires_tag import RequiresTag, check_requires_tags, parse_requires_tags
from buildgen.value_wiring import ValueWiringField, parse_value_wiring
from buildgen.wiring import WiringField, parse_wiring

# Cached per-driver-source-file parse results (_resolve_instances() below) - the fixed shape every
# one of buildgen's four comment-tag parsers returns for one driver file.
_ParsedDriverTags = tuple["tuple[WiringField, ...]", "tuple[RequiresTag, ...]", "tuple[LimitField, ...]", "tuple[ValueWiringField, ...]", str]

_BUS_WIRE_FIELDS = {
    "i2c": ("scl_pin", "sda_pin"),
    "spi": ("sck_pin", "mosi_pin", "miso_pin"),
    "uart": ("tx_pin", "rx_pin"),
}
# Real RP2040 bus identities - Pico W exposes exactly two I2C, two SPI and two UART peripheral
# indices, never an arbitrary digit (closes the "i2c2"/bare-"i2c" gap - _bus_kind() used to only
# check the prefix).
_VALID_BUS_IDS = {"i2c0": "i2c", "i2c1": "i2c", "spi0": "spi", "spi1": "spi", "uart0": "uart", "uart1": "uart"}
# bus-table field name -> (role table, the role that field must resolve to). Every field of a kind
# always appears together in _BUS_WIRE_FIELDS/_BUS_ALLOWED_FIELDS, so a bus table never mixes kinds.
_BUS_PIN_ROLE: "dict[str, tuple[dict[int, tuple[str, str]], str]]" = {
    "scl_pin": (I2C_ROLE, "scl"),
    "sda_pin": (I2C_ROLE, "sda"),
    "sck_pin": (SPI_ROLE, "sck"),
    "mosi_pin": (SPI_ROLE, "mosi"),
    "miso_pin": (SPI_ROLE, "miso"),
    "tx_pin": (UART_ROLE, "tx"),
    "rx_pin": (UART_ROLE, "rx"),
}
# Every field a bus table of this kind may declare: its required wire pins, plus "frequency"
# (checked separately above for a better message) and, i2c-only, "timeout" - optional at the
# table level, required only when an scd30 sits on this bus, which its @requires tag enforces.

# uart's optional fields mirror asy_uart_driver.UART's kwargs of the same name, present because
# dev's bench tuning (Part J) differs from that constructor's defaults. "baudrate" is required
# like i2c's "frequency"; codegen emits a kwarg only for whichever others the TOML declares.
_BUS_ALLOWED_FIELDS = {
    "i2c": frozenset(_BUS_WIRE_FIELDS["i2c"]) | {"frequency", "timeout"},
    "spi": frozenset(_BUS_WIRE_FIELDS["spi"]),
    "uart": frozenset(_BUS_WIRE_FIELDS["uart"]) | {"baudrate", "rxbuf", "txbuf", "poll_wait_ms", "poll_idle_ms"},
}
_UART_LINK_ROLES = frozenset({"initiator", "responder"})  # asy_uart_comm.ROLE_INITIATOR/ROLE_RESPONDER's
# own literal values, duplicated here rather than imported - buildgen never imports real src/
# modules (they can rely on MicroPython-only syntax/APIs the driver_registry.py docstring's own
# AST-only-parsing rule exists to avoid), so the two string literals are the contract instead.
_UART_OPTIONAL_INT_FIELDS = ("rxbuf", "txbuf", "poll_wait_ms", "poll_idle_ms")
_REQUIRED_DEVICE_FIELDS = ("name", "hostname", "hotspot_password", "conn_fail_to_hotspot", "hotspot_time_min")
_HOSTNAME_MAX_LEN = 32  # network.hostname()'s real cap; asy_wifi_service._VAL_HOST carries the same number
_REQUIRED_DEVICE_INT_FIELDS = ("conn_fail_to_hotspot", "hotspot_time_min")
# Optional: absent, each falls back to WebserverService.__init__'s own default, and the check below
# runs against that EFFECTIVE value - so no device can outrun its firmware by simply saying nothing.
_OPTIONAL_DEVICE_INT_FIELDS = ("max_connections", "backlog")
_ALLOWED_DEVICE_FIELDS = frozenset(_REQUIRED_DEVICE_FIELDS) | frozenset(_OPTIONAL_DEVICE_INT_FIELDS) | {"wiring"}
_MAX_CONNECTIONS_FLOOR = 1  # a webserver admitting no connection serves nothing
_WPA2_MIN_PASSWORD_LEN = 8  # WPA2-PSK's own minimum (IEEE 802.11i)
_WPA2_MAX_PASSWORD_LEN = 63  # its maximum too; asy_wifi_service._VAL_HOTSPOT_PW carries the same pair

# [device.wiring] fields and the mandatory-infra consumers whose _WIRING they resolve against,
# fixed ahead of time (Part L.3) unlike [instance.wiring]'s generic resolution. fram_target has
# several consumers, and each one's own tag is checked so a missing declaration is caught here.
_DEVICE_WIRING_CONSUMERS: "dict[str, tuple[tuple[str, str, str], ...]]" = {
    "led_target": (("asy_wifi_service.py", "AsyConnTime", "conn"),),
    "fram_target": (
        ("system_service.py", "SystemService", "sysfunct"),
        ("asy_wifi_service.py", "AsyConnTime", "conn"),
        ("asy_ntp_client.py", "AsyNtpClient", "ntp"),
        ("asy_webserver_service.py", "WebserverService", "webserver"),
    ),
}


def _bus_kind(bus_name: str, device: str) -> str:
    kind = _VALID_BUS_IDS.get(bus_name)
    if kind is None:
        raise BuildError(device, f"bus id {bus_name!r} is not a real Pico W bus - valid ids are {sorted(_VALID_BUS_IDS)}", field=bus_name)
    return kind


def _check_device_table(model: DeviceModel) -> None:
    # These three are validated here AND wired into generated code since 2026-09-18: codegen
    # passes hostname/hotspot_password to AsyConnTime, which uses them as the defaults of the two
    # persisted fields. Before that they were checked and reached nothing.
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
    # hotspot_password used to get only the bare presence check, so `= 5` or `= ""` built clean -
    # the one field outside the "any misformatted value fails the build" rule. The 8-character
    # floor is WPA2-PSK's own minimum: below it the CYW43 cannot bring the hotspot up at all.
    if not isinstance(dev["hotspot_password"], str):
        raise BuildError(model.device, f"[device].hotspot_password must be a string, got {dev['hotspot_password']!r}", field="hotspot_password")
    if not (_WPA2_MIN_PASSWORD_LEN <= len(dev["hotspot_password"]) <= _WPA2_MAX_PASSWORD_LEN):
        # Both ends, for the same reason the hostname cap below exists: the value is really injected
        # now, and one outside _VAL_HOTSPOT_PW's own bounds is dropped at boot back to the shared
        # default - which for this field is the password published in src/, on every device at once.
        raise BuildError(model.device, f"[device].hotspot_password is {len(dev['hotspot_password'])} characters - WPA2 allows {_WPA2_MIN_PASSWORD_LEN} to {_WPA2_MAX_PASSWORD_LEN}", field="hotspot_password")
    expected_hostname = "SensorStation" + dev["name"]
    if dev["hostname"] != expected_hostname:
        raise BuildError(model.device, f"[device].hostname is {dev['hostname']!r}, expected {expected_hostname!r} (SensorStation<name>)", field="hostname")
    # network.hostname()'s cap, mirrored from _VAL_HOST's upper bound. Now that the value really
    # is injected, an over-long one would be dropped back to "SensorNode" by _with_default() and
    # the device would quietly not answer to its own name. In practice a cap on [device].name.
    if len(dev["hostname"]) > _HOSTNAME_MAX_LEN:
        raise BuildError(model.device, f"[device].hostname is {len(dev['hostname'])} characters - network.hostname() caps at {_HOSTNAME_MAX_LEN}, so [device].name may be at most {_HOSTNAME_MAX_LEN - len('SensorStation')}", field="hostname")
    for f in _OPTIONAL_DEVICE_INT_FIELDS:
        if f in dev and not (isinstance(dev[f], int) and not isinstance(dev[f], bool)):
            raise BuildError(model.device, f"[device].{f} must be an int, got {dev[f]!r}", field=f)
    unknown = set(dev) - _ALLOWED_DEVICE_FIELDS
    if unknown:
        raise BuildError(model.device, f"[device] declares unrecognized field(s) {sorted(unknown)} - typo, or copy-pasted from an unrelated table?", field=min(unknown))


def webserver_init_default(src_dir: Path, name: str) -> int:
    """One `WebserverService.__init__` keyword default, read out of the real source. buildgen never
    imports src/ (it may use MicroPython-only syntax), so AST is the mechanism - the same one
    tests_scripts/test_request_body_cap_headroom.py uses for max_content_length."""
    path = src_dir / "asy_webserver_service.py"
    try:
        tree = ast.parse(path.read_text(), filename=str(path))
    except (OSError, SyntaxError) as e:
        raise BuildError("<src>", f"cannot read {path} to resolve WebserverService's own {name} default: {e}", field=name) from e
    for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == "WebserverService"):
        for fn in (n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"):
            # Keyword-only and positional defaults are walked as two pairings rather than one
            # concatenation: kw_defaults carries a None per argument that has no default, so the
            # two lists have different element types and only line up within their own group.
            positional = fn.args.args[len(fn.args.args) - len(fn.args.defaults):]
            pairs: list[tuple[ast.arg, ast.expr | None]] = list(zip(fn.args.kwonlyargs, fn.args.kw_defaults, strict=True))
            pairs += list(zip(positional, fn.args.defaults, strict=True))
            for arg, default in pairs:
                if arg.arg == name and isinstance(default, ast.Constant) and isinstance(default.value, int) and not isinstance(default.value, bool):
                    return default.value
    raise BuildError("<src>", f"WebserverService.__init__ no longer has a readable int default for {name!r} in {path} - the per-device key and the shipped default have to agree", field=name)


def device_max_connections(toml_path: Path, src_dir: Path) -> int:
    """The admission ceiling `toml_path` builds: its own [device].max_connections, else
    WebserverService's default. Host-side instruments size their load with this, never a literal."""
    with toml_path.open("rb") as f:
        ceiling = tomllib.load(f).get("device", {}).get("max_connections")
    return ceiling if isinstance(ceiling, int) else webserver_init_default(src_dir, "max_connections")


def _lwip_ensemble_problems(macros: "dict[str, int]", max_connections: int) -> "list[str]":
    """toolchain/micropython_overrides.py owns the relationships (they are lwIP's, not buildgen's).
    Loaded by path because buildgen is a package and toolchain/ is a flat script directory - the
    same bare-sibling shape tests_hardware/harness.py already uses for setup_toolchain."""
    spec = importlib.util.spec_from_file_location("micropython_overrides", Path(__file__).resolve().parent.parent / "toolchain" / "micropython_overrides.py")
    if spec is None or spec.loader is None:
        raise BuildError("<toolchain>", "cannot load toolchain/micropython_overrides.py, which owns lwIP's own option relationships", field="max_connections")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        problems: list[str] = module.check_lwip_ensemble(macros, max_connections)
    except KeyError as e:
        raise BuildError("<toolchain>", f"[lwip] in toolchain/versions.toml lacks {e} - it is what bounds every device's max_connections", field="max_connections") from e
    return problems


def _check_connection_ceiling(model: DeviceModel, src_dir: Path) -> None:
    """The device's EFFECTIVE admission ceiling against the firmware it ships in. Config that
    outruns its build refuses connections it says it admits, which reads as an application bug -
    so the PCB, segment and send-arena shares per connection (Part H.7) are build errors."""
    dev = model.doc["device"]
    max_connections = dev.get("max_connections", webserver_init_default(src_dir, "max_connections"))
    if max_connections < _MAX_CONNECTIONS_FLOOR:
        raise BuildError(model.device, f"[device].max_connections is {max_connections} - a webserver admitting no connection at all serves nothing, so the floor is {_MAX_CONNECTIONS_FLOOR}", field="max_connections")
    # lwIP's options are an ensemble and its own checks size the shared pools for ONE connection.
    # The N-connection half is checked here, where N is known.
    ensemble = _lwip_ensemble_problems(lwip_macros(), max_connections)
    if ensemble:
        raise BuildError(model.device, f"[device].max_connections is {max_connections}, which this firmware's lwIP settings cannot serve: " + "; ".join(ensemble) + ". Raise the matching [lwip] values in toolchain/versions.toml or lower max_connections", field="max_connections")
    backlog = dev.get("backlog")
    if backlog is not None and backlog < max_connections:
        # An accept queue shallower than the ceiling drops arrivals inside lwIP, where nothing in
        # src/ ever sees them - so the device silently serves fewer than its own config admits.
        raise BuildError(model.device, f"[device].backlog is {backlog}, below the {max_connections} connections [device].max_connections admits - the accept queue would drop arrivals the ceiling says it accepts", field="backlog")


def _check_bus_tables(model: DeviceModel) -> "dict[str, TomlDoc]":
    # A device with no bus-attached instances at all is a valid, simplest-possible shape, so
    # [bus.*] may be absent entirely. An instance that does need one is caught downstream by
    # _check_required_fields(); this only validates the shape of whatever tables are present.
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
        if kind in ("spi", "uart") and "frequency" in bus_table:
            raise BuildError(model.device, f"bus.{bus_name} ({kind}) declares frequency - its own driver has no such parameter", field="frequency")
        if kind == "uart" and not (isinstance(bus_table.get("baudrate"), int) and not isinstance(bus_table.get("baudrate"), bool)):
            raise BuildError(model.device, f"bus.{bus_name} (uart) is missing an int baudrate", field="baudrate")
        if "timeout" in bus_table and not (isinstance(bus_table["timeout"], int) and not isinstance(bus_table["timeout"], bool)):
            raise BuildError(model.device, f"bus.{bus_name} ({kind}) timeout must be an int, got {bus_table['timeout']!r}", field="timeout")
        if kind == "uart":
            for f in _UART_OPTIONAL_INT_FIELDS:
                if f in bus_table and not (isinstance(bus_table[f], int) and not isinstance(bus_table[f], bool)):
                    raise BuildError(model.device, f"bus.{bus_name} (uart) {f} must be an int, got {bus_table[f]!r}", field=f)
        unknown = set(bus_table) - _BUS_ALLOWED_FIELDS[kind]
        if unknown:
            raise BuildError(model.device, f"bus.{bus_name} ({kind}) declares unrecognized field(s) {sorted(unknown)} - typo, or copy-pasted from an unrelated bus kind?", field=min(unknown))
    return buses


def _resolve_instances(model: DeviceModel, src_dir: Path) -> None:
    # No "singleton declared twice" check is needed: a singleton is always forced to
    # name_ext="", so two of them share one (driver, name_ext) key and load_device() already
    # rejects that as a duplicate before this runs.

    # Every parse below re-reads the driver's source, so two instances of one driver did it
    # twice. Cached per source path for this build, the results being pure functions of the file.
    # A parse error still aborts on whichever instance hit it first, and either names it right.
    parsed: dict[Path, _ParsedDriverTags] = {}
    for spec in model.instances.values():
        info = resolve_driver(spec.driver, src_dir, model.device)
        spec.driver_info = info
        if info.source_path not in parsed:
            parsed[info.source_path] = (
                parse_wiring(info.source_path, model.device, spec.label),
                parse_requires_tags(info.source_path, model.device, spec.label),
                parse_limits(info.source_path, model.device, spec.label),
                parse_value_wiring(info.source_path, model.device, spec.label),
                parse_name_constant(info.source_path, model.device, spec.label),
            )
        spec.wiring_schema, spec.requires_tags, spec.limits_schema, spec.value_wiring_schema, base_name = parsed[info.source_path]
        spec.resolved_name = _instance_name(base_name, spec.name_ext)

        if spec.driver in SINGLETON_SERVICE_DRIVERS and spec.name_ext:
            raise BuildError(model.device, f"{spec.label}: singleton service driver {spec.driver!r} must not declare name_ext", instance=spec.label, field="name_ext")


def _instance_name(base_name: str, name_ext: str) -> str:
    return base_name if not name_ext else base_name + "_" + name_ext


def _check_required_fields(model: DeviceModel, buses: "dict[str, TomlDoc]") -> None:
    for spec in model.instances.values():
        # A driver resolving through driver_registry but absent from buildspec.py's tables would
        # fall through the .get() defaults below and have every real field flagged
        # "unrecognized" - fail-loud, but reading like a TOML typo. Named here instead (Part L.6).
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
            if spec.driver not in BUS_KIND_BY_DRIVER:
                raise BuildError(model.device, f"{spec.label}: driver {spec.driver!r} is in BUS_ATTACHED_DRIVERS but has no buildgen.buildspec.BUS_KIND_BY_DRIVER entry - add one", instance=spec.label)
            # A driver pointed at the wrong kind of bus used to build cleanly - the bus merely
            # had to exist - and failed only at boot, deep inside that driver's construction,
            # with a raw AttributeError instead of this error.
            actual_kind = _bus_kind(spec.fields["bus"], model.device)
            expected_kind = BUS_KIND_BY_DRIVER[spec.driver]
            if actual_kind != expected_kind:
                raise BuildError(
                    model.device,
                    f"{spec.label}.bus={spec.fields['bus']!r} is a {actual_kind} bus, but driver {spec.driver!r} needs a {expected_kind} bus",
                    instance=spec.label,
                    field="bus",
                )
        if "address" in spec.fields and spec.driver not in ADDRESS_CAPABLE_DRIVERS:
            raise BuildError(model.device, f"{spec.label} declares an address field, but {spec.driver!r} has no address-select pin (see buildgen.buildspec.ADDRESS_CAPABLE_DRIVERS)", instance=spec.label, field="address")
        if spec.driver == "uart_link" and spec.fields.get("role") not in _UART_LINK_ROLES:
            raise BuildError(model.device, f"{spec.label}.role must be one of {sorted(_UART_LINK_ROLES)}, got {spec.fields.get('role')!r}", instance=spec.label, field="role")
        # These three reach codegen's hex()/str() argument-building unvalidated otherwise: a
        # quoted "0x77" raises a raw TypeError from hex(), and trigger_sec, which only goes
        # through str(), renders as a bare identifier token ast.parse() cannot tell from an int.
        for f in ("address", "max_size", "trigger_sec"):
            if f in spec.fields and not (isinstance(spec.fields[f], int) and not isinstance(spec.fields[f], bool)):
                raise BuildError(model.device, f"{spec.label}.{f} must be an int, got {spec.fields[f]!r}", instance=spec.label, field=f)
        # Catch-all: any field beyond driver/name_ext and this driver's own set is a copy-paste
        # error (Part L.5) - an "irq_pin" left from cloning an scd30 block, say, which codegen
        # would otherwise ignore silently, never reaching any driver's _build_call() branch.
        unknown = set(spec.fields) - {"driver", "name_ext"} - ALLOWED_INSTANCE_FIELDS.get(spec.driver, frozenset())
        if unknown:
            raise BuildError(model.device, f"{spec.label} declares unrecognized field(s) {sorted(unknown)} for driver {spec.driver!r}", instance=spec.label, field=min(unknown))


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


def _check_all_buses_used(model: DeviceModel, buses: "dict[str, TomlDoc]") -> None:
    used = {spec.fields["bus"] for spec in model.instances.values() if "bus" in spec.fields}
    orphans = set(buses) - used
    if orphans:
        raise BuildError(model.device, f"bus(es) {sorted(orphans)} declared but never referenced by any instance")


def _check_instance_name_collisions(model: DeviceModel) -> None:
    seen: dict[str, str] = {}
    for spec in model.instances.values():
        if spec.resolved_name is None:
            raise BuildError(model.device, "internal: resolved_name unresolved by collision-check time", instance=spec.label)
        existing = seen.get(spec.resolved_name)
        if existing is not None:
            raise BuildError(
                model.device,
                f"instance_name collision: {spec.label!r} and {existing!r} both resolve to {spec.resolved_name!r} - give one a disambiguating name_ext",
                instance=spec.label,
            )
        seen[spec.resolved_name] = spec.label


def _check_instance_label_collisions(model: DeviceModel) -> None:
    # instance_label(), the codegen-time Python-variable identity, is a different space from
    # resolved_name's REST-key identity checked above. Unreachable with today's six driver names,
    # none of which carries an underscore that could line up, but latent for a future one.
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


def _check_gpio_collisions(model: DeviceModel, buses: "dict[str, TomlDoc]") -> None:
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
        for f in ("scl_pin", "sda_pin", "sck_pin", "mosi_pin", "miso_pin", "tx_pin", "rx_pin"):
            if f not in bus_table:
                continue
            pin = bus_table[f]
            claim(pin, f"bus.{bus_name}", f)
            # Bus pins only: the GPIO must be hardwired to THIS bus's peripheral index in the
            # role the field claims, not merely be legal and unclaimed. cs_pin/irq_pin/neopixel's
            # pin have no peripheral role, so this half runs for wire pins alone.
            role_table, expected_role = _BUS_PIN_ROLE[f]
            info = role_table.get(pin)
            if info is None:
                kind = "I2C" if role_table is I2C_ROLE else "SPI" if role_table is SPI_ROLE else "UART"
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


def _check_uart_link_roles(model: DeviceModel) -> None:
    # RP2040 has two UART peripherals, so a device wires at most one crossover pair. This is
    # what enforces the guarantee compute_twin_wiring()'s docstring already relies on.

    # Without it two initiators on uart0/uart1 built and booted silently, both looping on read
    # timeouts with nothing able to answer, while the twin's pairing loop kept the last one it
    # saw and left responder_var None - disabling crossover wiring with no error naming it.
    initiators = [spec.label for spec in model.instances.values() if spec.driver == "uart_link" and spec.fields.get("role") == "initiator"]
    responders = [spec.label for spec in model.instances.values() if spec.driver == "uart_link" and spec.fields.get("role") == "responder"]
    if not initiators and not responders:
        return
    if len(initiators) != 1 or len(responders) != 1:
        raise BuildError(
            model.device,
            f"a device wires exactly one uart_link initiator and one responder (RP2040 has only two UART peripherals) - found {len(initiators)} initiator(s) {sorted(initiators)} and {len(responders)} responder(s) {sorted(responders)}",
        )


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
    if target.driver_info is None:
        raise BuildError(model.device, "internal: target.driver_info unresolved by wiring-reference-check time", instance=consumer_label, field=toml_field)
    if target.driver_info.class_name != wf.producer_class:
        raise BuildError(
            model.device,
            f"{consumer_label}'s wiring.{toml_field}={target_key_str!r} resolves to a {target.driver_info.class_name}, but {wf.mode!r} wiring requires a {wf.producer_class}",
            instance=consumer_label,
            field=toml_field,
        )


def _check_source_field_reference(model: DeviceModel, value: object, consumer_label: str, toml_field: str) -> None:
    # Shared by warn_*'s getters and _VALUE_WIRING's per-value wiring (SPECIFICATION.md Part L.6.3)
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


def _check_default_provider_params(model: DeviceModel, spec: InstanceSpec, toml_field: str, value: "TomlDoc") -> ast.ClassDef:
    # Shared by _WIRING- and _VALUE_WIRING-based defaults, on the principle that the class
    # definition IS the schema: a `_Default<Field>`'s own __init__ signature says which keys a
    # `{default = true, ...}` sub-table may carry, read by AST like _WIRING and _LIMITS.
    if spec.driver_info is None:
        raise BuildError(model.device, "internal: driver_info unresolved by default-provider-check time", instance=spec.label, field=toml_field)
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


def _check_default_selection(model: DeviceModel, spec: InstanceSpec, wf: WiringField, toml_field: str, value: "TomlDoc") -> None:
    class_node = _check_default_provider_params(model, spec, toml_field, value)
    # For attr-mode _WIRING fields only: verify the default provider really defines the target
    # attribute, the same fail-at-generation-time rule every other check here follows.
    # _VALUE_WIRING needs no equivalent - its providers all follow one fixed get_data() contract.
    if wf.mode == "attr" and not default_class_defines_attr(class_node, wf.target):
        raise BuildError(
            model.device,
            f"{spec.label}'s wiring.{toml_field} default provider {class_node.name} defines no {wf.target!r} attribute/method - required for 'attr' mode wiring",
            instance=spec.label,
            field=toml_field,
        )


def _check_default_value_selection(model: DeviceModel, spec: InstanceSpec, vwf: ValueWiringField) -> None:
    value = spec.wiring[vwf.toml_field]
    if not isinstance(value, dict):
        raise BuildError(model.device, "internal: default-selection check reached with a non-table wiring value", instance=spec.label, field=vwf.toml_field)
    _check_default_provider_params(model, spec, vwf.toml_field, value)


def _check_instance_wiring(model: DeviceModel) -> None:
    for spec in model.instances.values():
        value_wiring_fields = {vwf.toml_field for vwf in spec.value_wiring_schema}
        for toml_field, value in spec.wiring.items():
            if toml_field.startswith("warn_"):
                continue  # per-signal getters (source/field pairs) - checked separately below
            if toml_field in value_wiring_fields:
                continue  # _VALUE_WIRING field (SPECIFICATION.md Part L.6.3) - checked by _check_value_wiring()
            wf = _resolve_wiring_field(spec.wiring_schema, toml_field)
            if wf is None:
                raise BuildError(model.device, f"{spec.label} declares wiring.{toml_field}, but its driver has no matching _WIRING entry", instance=spec.label, field=toml_field)
            # SPECIFICATION.md Part L.6.2's wiring-defaults mechanism: a {default = true, ...} sub-table
            # opts out of resolving a real instance reference entirely - branch at the very top,
            # before any string-only handling runs.
            if isinstance(value, dict) and value.get("default") is True:
                _check_default_selection(model, spec, wf, toml_field, value)
                continue
            if not isinstance(value, str):
                raise BuildError(model.device, f"{spec.label}'s wiring.{toml_field} must be a string instance reference, got {value!r}", instance=spec.label, field=toml_field)
            _check_wiring_reference(model, wf, value, spec.label, toml_field)
        for wf in spec.wiring_schema:
            if wf.required and wf.toml_field not in spec.wiring:
                raise BuildError(model.device, f"{spec.label} is missing required wiring.{wf.toml_field}", instance=spec.label, field=wf.toml_field)

        # Per-signal getters (notification's warn_co2/warn_voc/warn_hum): related to _WIRING but
        # separate (Part C.14.3). Each {source, field} sub-table is optional, and `source`
        # resolves against the same driver/name_ext space as every other wiring reference.
        for toml_field, value in spec.wiring.items():
            if not toml_field.startswith("warn_"):
                continue
            _check_source_field_reference(model, value, spec.label, toml_field)


def _check_value_wiring(model: DeviceModel) -> None:
    # SPECIFICATION.md Part L.6.3's per-value wiring: each field independently resolves to either a
    # real {source, field} reference (any producer, matched by attribute name) or an explicit
    # {default = true, ...} opt-in (L.6.2) - never silently defaulted just because it's absent.
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
        consumers = _DEVICE_WIRING_CONSUMERS.get(toml_field)
        if consumers is None:
            raise BuildError(model.device, f"[device.wiring] declares unknown field {toml_field!r}", field=toml_field)
        if not isinstance(value, str):
            raise BuildError(model.device, f"[device.wiring].{toml_field} must be a string instance reference, got {value!r}", field=toml_field)
        for module_file, _class_name, consumer_label in consumers:
            schema = parse_wiring(src_dir / module_file, model.device, consumer_label)
            wf = _resolve_wiring_field(schema, toml_field)
            if wf is None:
                raise BuildError(model.device, f"[device.wiring].{toml_field} declared, but {module_file} has no matching @wiring tag", field=toml_field)
            _check_wiring_reference(model, wf, value, "device.wiring", toml_field)

    # Required-field enforcement mirroring _check_instance_wiring's pass below. Both device-
    # wiring fields are optional today, so this never fires yet; kept in sync so a future
    # required entry cannot go unenforced. A field is required if ANY consumer's tag says so.
    for toml_field, consumers in _DEVICE_WIRING_CONSUMERS.items():
        if toml_field in wiring:
            continue
        for module_file, _class_name, consumer_label in consumers:
            schema = parse_wiring(src_dir / module_file, model.device, consumer_label)
            wf = _resolve_wiring_field(schema, toml_field)
            if wf is not None and wf.required:
                raise BuildError(model.device, f"[device.wiring] is missing required field {toml_field!r}", field=toml_field)


def _check_requires_tags(model: DeviceModel, buses: "dict[str, TomlDoc]") -> None:
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
    _check_uart_link_roles(model)
    _check_limits(model)
    _check_all_buses_used(model, buses)
    _check_instance_name_collisions(model)
    _check_instance_label_collisions(model)
    _check_gpio_collisions(model, buses)
    _check_address_collisions(model)
    _check_instance_wiring(model)
    _check_value_wiring(model)
    _check_device_wiring(model, src_dir)
    _check_requires_tags(model, buses)
    # Last, because it is a coherence check between this device's config and the firmware it will
    # ship in rather than a property of the TOML - anything genuinely wrong with the device should
    # report before it, and it is the only stage that reads toolchain/versions.toml at all.
    _check_connection_ceiling(model, src_dir)
    return model


__all__ = ["InstanceSpec", "build_model", "instance_label"]
