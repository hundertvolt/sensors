"""The full validation pass (SPECIFICATION.md Part L.5): structural shape, every
global-resource-collision class, and wiring-reference resolution. `build_model()` either raises a
`BuildError` naming device/instance/field, or returns a fully-resolved, safe-to-generate model."""

import ast
import functools
import importlib.util
import math
from pathlib import Path
from typing import TypeGuard, TypeVar

import tomllib

from buildgen.buildspec import (
    ADDRESS_CAPABLE_DRIVERS,
    ALLOWED_INSTANCE_FIELDS,
    BUS_ATTACHED_DRIVERS,
    BUS_KIND_BY_DRIVER,
    FIXED_ADDRESS_DRIVERS,
    REQUIRED_TOML_FIELDS,
    UART_CRC_MODES,
)
from buildgen.defaults import default_class_defines_attr, default_class_name, default_init_params, find_default_class
from buildgen.driver_registry import SINGLETON_SERVICE_DRIVERS, data_fields, parse_name_constant, resolve_driver
from buildgen.errors import BuildError, BuildInternalError
from buildgen.limits import LimitField, parse_limits
from buildgen.model import DeviceModel, InstanceSpec, TomlDoc, TomlValue, instance_label, load_device, lwip_macros, resolve_instance_key
from buildgen.pico_gpio import I2C_ROLE, SPI_ROLE, UART_ROLE, gpio_exists
from buildgen.requires_tag import RequiresTag, check_requires_tags, parse_requires_tags
from buildgen.schema_ast import extract_field_schemas
from buildgen.signals import WARN_SIGNALS
from buildgen.source_ast import parse_source
from buildgen.value_wiring import ValueWiringField, parse_value_wiring
from buildgen.wiring import WiringField, parse_wiring

# Cached per-driver-source-file parse results (_resolve_instances() below) - the fixed shape every
# one of buildgen's four comment-tag parsers returns for one driver file.
_ParsedDriverTags = tuple["tuple[WiringField, ...]", "tuple[RequiresTag, ...]", "tuple[LimitField, ...]", "tuple[ValueWiringField, ...]", str]
_ConstT = TypeVar("_ConstT", int, float, str)

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
# Every field a bus table of this kind may declare: its wire pins, plus i2c's required "frequency" and
# optional "timeout" (required only where an scd30 sits on the bus, which its @requires tag enforces).
#
# uart's optional fields mirror asy_uart_driver.UART's kwargs of the same name, for a device whose link
# needs other buffers or poll rates than the constructor's defaults (Part J.6).
_BUS_ALLOWED_FIELDS = {
    "i2c": frozenset(_BUS_WIRE_FIELDS["i2c"]) | {"frequency", "timeout"},
    "spi": frozenset(_BUS_WIRE_FIELDS["spi"]),
    "uart": frozenset(_BUS_WIRE_FIELDS["uart"]) | {"baudrate", "rxbuf", "txbuf", "rx_ring", "poll_wait_ms", "poll_idle_ms"},
}
_UART_OPTIONAL_INT_FIELDS = ("rxbuf", "txbuf", "rx_ring", "poll_wait_ms", "poll_idle_ms")
_REQUIRED_DEVICE_FIELDS = ("name", "hostname", "hotspot_password", "conn_fail_to_hotspot", "hotspot_time_min")
_REQUIRED_DEVICE_INT_FIELDS = ("conn_fail_to_hotspot", "hotspot_time_min")
# Optional: absent, each falls back to its class's own __init__ default, and the checks below run
# against that EFFECTIVE value - so no device can outrun its firmware by simply saying nothing.
_OPTIONAL_DEVICE_INT_FIELDS = ("max_connections", "backlog", "ntp_retry_s", "ntp_retry_max_s")
_ALLOWED_DEVICE_FIELDS = frozenset(_REQUIRED_DEVICE_FIELDS) | frozenset(_OPTIONAL_DEVICE_INT_FIELDS) | {"wiring", "hardware_family"}
_MAX_CONNECTIONS_FLOOR = 1  # a webserver admitting no connection serves nothing
_HOSTNAME_PREFIX = "SensorStation"
# Bounds of values the build hands to the silicon or the port, each with its source.
_HOTSPOT_TIME_MIN_MAX = (2**31 - 1) // 60000  # Timer.init(period=60000 x minutes) is a signed machine int: ports/rp2/machine_timer.c:79
_SMALL_INT_MAX = 2**30 - 1  # rp2's small ints are 31-bit (py/smallint.h:39, :62 at v1.29.0); a doubled value past it allocates
_I2C_FREQUENCY_MAX_HZ = 1000000  # RP2040 datasheet 4.3.3 (printed p.442): fast mode plus, up to 1000 kbps
_UART_BAUDRATE_MAX = 7812500  # RP2040 datasheet 4.2.1 (printed p.418): UARTCLK / 16, 7.8 Mbaud at 125 MHz
_UART_BUFFER_MIN = 32  # ports/rp2/machine_uart.c:67, :372-375 (v1.29.0): a smaller rxbuf/txbuf is raised to it silently
_UART_BUFFER_MAX = 32766  # ports/rp2/machine_uart.c:68, :376-377: a larger one raises ValueError at boot
# The boot bus clear runs unfed after WDT() (Part A.7, stretch 1): per I2C bus up to _CLEAR_PULSES + 2 SCL
# waits (lead-in, pulses, STOP) of one timeout each. Bound (agent, 2026-10-07): the largest timeout any
# device declares, the SCD30's own floor; 2 buses x 11 waits x 200 ms = 4400 ms fit the budget below.
# @tunable i2c.timeout_max_us = 200000
_I2C_TIMEOUT_MAX_US = 200000
# @tunable wdt.timeout_ms = 8000
_WDT_TIMEOUT_MS = 8000  # codegen's generated WDT(timeout=...), the one the boot clear runs under
# Three quarters of the watchdog (agent, 2026-10-07): 2000 ms stay for the rest of stretch 1 (~0.17 s measured).
_BOOT_CLEAR_BUDGET_MS = _WDT_TIMEOUT_MS * 3 // 4

# [device.wiring] fields and the mandatory-infra consumers whose @wiring tags they resolve against, as
# (module file, the consumer's generated name) pairs fixed ahead of time (Part L.3). fram_target has
# several consumers, and each one's own tag is checked so a missing declaration is caught here.
_DEVICE_WIRING_CONSUMERS: "dict[str, tuple[tuple[str, str], ...]]" = {
    "led_target": (("asy_wifi_service.py", "conn"),),
    "fram_target": (
        ("asy_system_service.py", "sysfunct"),
        ("asy_wifi_service.py", "conn"),
        ("asy_ntp_client.py", "ntp"),
        ("asy_webserver_service.py", "webserver"),
    ),
}
# The mandatory modules every device builds, never [[instance]] entries: each one's _NAME is a logger
# name no instance may take, and so is CFGMGR_<name> for the ones owning a config store.
_MANDATORY_MODULE_FILES = ("asy_wifi_service.py", "asy_captive_dns.py", "asy_ntp_client.py", "asy_system_service.py", "asy_webserver_service.py")

# The settings groups the generated webserver serves, in order: (section, module variable, fields, hook), the hook
# written as SettingsGroup's own keyword and callable, or None. Codegen renders the rows and the build checks them for
# a repeated key; notification's group comes from its schema at boot, so it is no row.
SETTINGS_GROUPS: "tuple[tuple[str, str, tuple[str, ...], str | None], ...]" = (
    ("networking", "conn", ("SSID", "PW", "Country", "Hostname", "HotspotPW"), "post_fct=conn.reconnect_wifi"),
    ("networking", "conn", ("LEDWifiOn",), None),
    ("networking", "ntp", ("NTPHost", "NTPOffset", "NTPInterval"), "post_asy_fct=ntp.ntp_force_sync"),
    ("networking", "ntp", ("DNSFallback",), None),  # no hook: the next NTP attempt reads the fallback list
    ("system", "sysfunct", ("DebugLevel",), None),
    ("system", "ntp", ("GMTOffset", "DSTOffset"), None),
)


def _is_int(value: object) -> "TypeGuard[int]":
    # A TOML integer: bool is an int subclass in Python, never one here.
    return isinstance(value, int) and not isinstance(value, bool)


def _checked_int(value: "TomlValue") -> int:
    # A value an earlier check of this pass has proven an int.
    if not _is_int(value):
        raise BuildInternalError(f"internal: {value!r} reached a later check as an int unchecked")
    return value


def _checked_str(value: "TomlValue") -> str:
    # A value an earlier check of this pass has proven a string.
    if not isinstance(value, str):
        raise BuildInternalError(f"internal: {value!r} reached a later check as a string unchecked")
    return value


def _device_table(model: DeviceModel) -> "TomlDoc":
    # The [device] table _check_device_table() has proven a table.
    table = model.doc.get("device")
    if not isinstance(table, dict):
        raise BuildInternalError(f"internal: {model.device}'s [device] reached a later check unchecked")
    return table


def _bus_kind(bus_name: str, device: str) -> str:
    kind = _VALID_BUS_IDS.get(bus_name)
    if kind is None:
        raise BuildError(
            device,
            f"bus id {bus_name!r} is not a real Pico W bus - valid ids are {sorted(_VALID_BUS_IDS)}",
            rule="bus.unknown-id",
            fix=f"name the bus one of {sorted(_VALID_BUS_IDS)}",
            field=bus_name,
        )
    return kind


def _host_label_ok(label: str) -> bool:
    # RFC 1123 SS2.1 host label, re-stated from src/asy_wifi_service.py's own check (buildgen never
    # imports src/): letters, digits and '-', never at either end. DHCP and mDNS announce it as is.
    return bool(label) and label[0] != "-" and label[-1] != "-" and all(ch.isascii() and (ch.isalnum() or ch == "-") for ch in label)


def _wifi_schema_bounds(src_dir: Path, field: str) -> "tuple[int, int]":
    # One WifiService config field's (min, max), read from its schema: the device's own value is injected as that
    # field's default, so the build refuses what the schema would drop at boot to the shared default.
    path = src_dir / "asy_wifi_service.py"
    schemas = extract_field_schemas(path, field=field)  # a file it cannot read or parse fails there, placed at this field
    schema = schemas.get(field)
    low, high = (None, None) if schema is None else (schema[2], schema[3])
    if not (_is_int(low) and _is_int(high)):
        raise BuildError("<src>", f"{path} no longer declares a {field} schema with int bounds", rule="src.schema-missing", fix=f"give {field}'s schema in {path.name} int min and max bounds", field=field)
    return low, high


def _uart_link_roles(src_dir: Path) -> "tuple[str, str]":
    # asy_uart_comm's ROLE_INITIATOR/ROLE_RESPONDER, the two role strings a uart_link instance may state.
    return module_str_const(src_dir, "asy_uart_comm.py", "ROLE_INITIATOR"), module_str_const(src_dir, "asy_uart_comm.py", "ROLE_RESPONDER")


def _owns_config_store(path: Path) -> bool:
    # Whether the module builds a ConfigManager: a SensorReaderConfig subclass gets one from its base, any
    # other class constructs it. The store logs as CFGMGR_<name>, beside the module's own logger.
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as e:
        raise BuildError("<src>", f"cannot read {path} to find its config store: {e}", rule="src.unreadable", fix=f"restore {path.name} in the source directory", field=path.name) from e
    return _declares_config_store(source, str(path))


@functools.lru_cache(maxsize=64)
def _declares_config_store(source: str, filename: str) -> bool:
    # Keyed on the source text like source_ast's parse cache, so an edited file is never answered stale.
    for node in ast.walk(parse_source(source, filename)):
        if isinstance(node, ast.ClassDef) and any(isinstance(b, ast.Name) and b.id == "SensorReaderConfig" for b in node.bases):
            return True
        if isinstance(node, ast.Call) and ((isinstance(node.func, ast.Name) and node.func.id == "ConfigManager") or (isinstance(node.func, ast.Attribute) and node.func.attr == "ConfigManager")):
            return True
    return False


def _check_device_table(model: DeviceModel, src_dir: Path) -> None:
    # hostname and hotspot_password reach generated code as WifiService's defaults of its two persisted fields,
    # so each is held to the bounds its schema (_VAL_HOSTNAME, _VAL_HOTSPOT_PW) refuses at boot.
    table = model.doc.get("device")
    if not isinstance(table, dict):
        what = "missing [device] table" if table is None else f"[device] must be a table, got {table!r}"
        raise BuildError(model.device, what, rule="device.table-missing", fix="add a [device] table naming the device and its hotspot settings")
    for f in _REQUIRED_DEVICE_FIELDS:
        if f not in table:
            raise BuildError(model.device, f"[device] is missing required field {f!r}", rule="device.field-missing", fix=f"add {f} to [device]", field=f)
    for f in _REQUIRED_DEVICE_INT_FIELDS + _OPTIONAL_DEVICE_INT_FIELDS:
        if f in table and not _is_int(table[f]):
            raise BuildError(model.device, f"[device].{f} must be an int, got {table[f]!r}", rule="device.field-type", fix=f"write {f} as a whole number", field=f)
    name = table["name"]
    if not (isinstance(name, str) and name):
        raise BuildError(model.device, "[device].name must be a non-empty string", rule="device.field-type", fix="write name as a non-empty quoted string", field="name")
    _check_device_identity(model, table, name, src_dir)
    family = table.get("hardware_family")
    if family is not None and not (isinstance(family, str) and family):
        raise BuildError(model.device, f"[device].hardware_family must be a non-empty string, got {family!r}", rule="device.field-type", fix="write hardware_family as a non-empty quoted label", field="hardware_family")
    wiring = table.get("wiring", {})
    if not isinstance(wiring, dict):
        raise BuildError(model.device, f"[device].wiring must be a table, got {wiring!r}", rule="device.wiring-not-table", fix="write it as a [device.wiring] table", field="wiring")
    _check_device_ranges(model, table)
    unknown = set(table) - _ALLOWED_DEVICE_FIELDS
    if unknown:
        raise BuildError(
            model.device,
            f"[device] declares unrecognized field(s) {sorted(unknown)} - typo, or copy-pasted from an unrelated table?",
            rule="device.field-unknown",
            fix=f"remove or correct {sorted(unknown)}",
            field=min(unknown),
        )


def _check_device_identity(model: DeviceModel, table: "TomlDoc", name: str, src_dir: Path) -> None:
    # The hotspot password and the hostname, each against the bounds of the WifiService field it becomes.
    password = table["hotspot_password"]
    if not isinstance(password, str):
        raise BuildError(model.device, f"[device].hotspot_password must be a string, got {password!r}", rule="device.field-type", fix="write hotspot_password as a quoted string", field="hotspot_password")
    pw_min, pw_max = _wifi_schema_bounds(src_dir, "HotspotPW")
    if not pw_min <= len(password) <= pw_max:
        # One outside _VAL_HOTSPOT_PW's bounds would be dropped at boot back to the password published in src/.
        raise BuildError(
            model.device,
            f"[device].hotspot_password is {len(password)} characters - WPA2 allows {pw_min} to {pw_max}",
            rule="device.hotspot-password-length",
            fix=f"use a password of {pw_min} to {pw_max} characters",
            field="hotspot_password",
        )
    expected = _HOSTNAME_PREFIX + name
    if table["hostname"] != expected:
        raise BuildError(model.device, f"[device].hostname is {table['hostname']!r}, expected {expected!r} (SensorStation<name>)", rule="device.hostname-convention", fix=f"set hostname = {expected!r}", field="hostname")
    if not _host_label_ok(expected):
        raise BuildError(
            model.device,
            f"[device].hostname {expected!r} is not a host label (letters, digits, '-'; not starting or ending with '-'), so [device].name may use only those characters",
            rule="device.hostname-label",
            fix="use only letters, digits and '-' in [device].name",
            field="hostname",
        )
    # network.hostname()'s cap, as _VAL_HOSTNAME's max: an over-long name would be dropped back to the
    # shared default and the device would quietly not answer to its own name.
    host_max = _wifi_schema_bounds(src_dir, "Hostname")[1]
    if len(expected) > host_max:
        raise BuildError(
            model.device,
            f"[device].hostname is {len(expected)} characters - network.hostname() caps at {host_max}, so [device].name may be at most {host_max - len(_HOSTNAME_PREFIX)}",
            rule="device.hostname-length",
            fix=f"shorten [device].name to at most {host_max - len(_HOSTNAME_PREFIX)} characters",
            field="hostname",
        )


def _check_device_ranges(model: DeviceModel, table: "TomlDoc") -> None:
    # The two required timing ints, each against what its consumer accepts (Part C.7.2).
    minutes = _checked_int(table["hotspot_time_min"])
    if not 1 <= minutes <= _HOTSPOT_TIME_MIN_MAX:
        raise BuildError(
            model.device,
            f"[device].hotspot_time_min is {minutes} - the hotspot Timer's period, 60000 x minutes, must be a positive signed machine int",
            rule="device.hotspot-time-min-range",
            fix=f"set hotspot_time_min within 1..{_HOTSPOT_TIME_MIN_MAX}",
            field="hotspot_time_min",
        )
    failures = _checked_int(table["conn_fail_to_hotspot"])
    if failures < 1:
        raise BuildError(
            model.device,
            f"[device].conn_fail_to_hotspot is {failures} - below 1 the hotspot opens on the first failed connect",
            rule="device.conn-fail-to-hotspot-range",
            fix="set conn_fail_to_hotspot to 1 or more",
            field="conn_fail_to_hotspot",
        )


def init_int_default(src_dir: Path, filename: str, class_name: str, name: str) -> int:
    # One `<class_name>.__init__` int keyword default, read out of the real source. buildgen never
    # imports src/ (it may use MicroPython-only syntax), so AST is the mechanism - the same one
    # tests_scripts/test_request_body_cap_headroom.py uses for max_content_length.
    path = src_dir / filename
    try:
        tree = parse_source(path.read_text(encoding="utf-8"), str(path))
    except (OSError, SyntaxError) as e:
        raise BuildError("<src>", f"cannot read {path} to resolve {class_name}'s own {name} default: {e}", rule="src.unreadable", fix=f"restore {filename} in the source directory", field=name) from e
    for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == class_name):
        for fn in (n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"):
            # Keyword-only and positional defaults are walked as two pairings rather than one
            # concatenation: kw_defaults carries a None per argument that has no default, so the
            # two lists have different element types and only line up within their own group.
            positional = fn.args.args[len(fn.args.args) - len(fn.args.defaults):]
            pairs: list[tuple[ast.arg, ast.expr | None]] = list(zip(fn.args.kwonlyargs, fn.args.kw_defaults, strict=True))
            pairs += list(zip(positional, fn.args.defaults, strict=True))
            for arg, default in pairs:
                if arg.arg == name and isinstance(default, ast.Constant) and _is_int(default.value):
                    return default.value
    raise BuildError(
        "<src>",
        f"{class_name}.__init__ no longer has a readable int default for {name!r} in {path} - the per-device key and the shipped default have to agree",
        rule="src.default-missing",
        fix=f"give {class_name}.__init__'s {name} an int literal default",
        field=name,
    )


def _module_const(src_dir: Path, filename: str, name: str, kind: "type[_ConstT]") -> "_ConstT":
    # One module-level `NAME = const(<literal>)` (or a bare literal) of a src/ file, by AST: buildgen
    # never imports src/. `kind` is the literal's type, matched exactly, so a bool never counts as an int.
    path = src_dir / filename
    try:
        tree = parse_source(path.read_text(encoding="utf-8"), str(path))
    except (OSError, SyntaxError) as e:
        raise BuildError("<src>", f"cannot read {path} to resolve its {name}: {e}", rule="src.unreadable", fix=f"restore {filename} in the source directory", field=name) from e
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            value = node.value
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "const" and len(value.args) == 1:
                value = value.args[0]
            if isinstance(value, ast.Constant) and type(value.value) is kind and isinstance(value.value, kind):
                return value.value
    raise BuildError(
        "<src>",
        f"{path} no longer has a readable {kind.__name__} {name} - the build-time check mirroring it has to follow",
        rule="src.const-missing",
        fix=f"declare {name} = const(<{kind.__name__} literal>) at module level in {filename}",
        field=name,
    )


def module_int_const(src_dir: Path, filename: str, name: str) -> int:
    # One module-level `NAME = const(<int>)` of a src/ file, by AST like init_int_default().
    return _module_const(src_dir, filename, name, int)


def module_float_const(src_dir: Path, filename: str, name: str) -> float:
    # module_int_const()'s float sibling: `NAME = const(<float>)`.
    return _module_const(src_dir, filename, name, float)


def module_str_const(src_dir: Path, filename: str, name: str) -> str:
    # module_int_const()'s str sibling: `NAME = const("<str>")`.
    return _module_const(src_dir, filename, name, str)


def webserver_init_default(src_dir: Path, name: str) -> int:
    # One shipped ServingLimits default: asy_webserver_service.py's `_DEFAULT_<NAME>` constant.
    return module_int_const(src_dir, "asy_webserver_service.py", "_DEFAULT_" + name.upper())


def device_max_connections(toml_path: Path, src_dir: Path) -> int:
    # The admission ceiling `toml_path` builds: its own [device].max_connections, else
    # WebserverService's default. Host-side instruments size their load with this, never a literal.
    with toml_path.open("rb") as f:
        device_table = tomllib.load(f).get("device", {})
    ceiling = device_table.get("max_connections") if isinstance(device_table, dict) else None
    return ceiling if _is_int(ceiling) else webserver_init_default(src_dir, "max_connections")


def _lwip_ensemble_problems(macros: "dict[str, int]", max_connections: int) -> "list[str]":
    # toolchain/micropython_overrides.py owns the relationships (they are lwIP's, not buildgen's).
    # Loaded by path because buildgen is a package and toolchain/ is a flat script directory - the
    # same bare-sibling shape tests_hardware/harness.py already uses for setup_toolchain.
    spec = importlib.util.spec_from_file_location("micropython_overrides", Path(__file__).resolve().parent.parent / "toolchain" / "micropython_overrides.py")
    if spec is None or spec.loader is None:
        raise BuildError(
            "<toolchain>",
            "cannot load toolchain/micropython_overrides.py, which owns lwIP's own option relationships",
            rule="toolchain.overrides-unloadable",
            fix="restore toolchain/micropython_overrides.py",
            field="max_connections",
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:  # the toolchain's own shape check first, so a bad table is named rather than a traceback
        module.validate_lwip_macros(macros)
    except module.OverrideError as e:
        raise BuildError("<toolchain>", f"{e} - it is what bounds every device's max_connections", rule="toolchain.lwip-table", fix="correct the [lwip] table in toolchain/versions.toml", field="max_connections") from e
    problems: list[str] = module.check_lwip_ensemble(macros, max_connections)
    return problems


def _check_connection_ceiling(model: DeviceModel, src_dir: Path) -> None:
    # The device's EFFECTIVE admission ceiling against the firmware it ships in. Config that
    # outruns its build refuses connections it says it admits, which reads as an application bug -
    # so the PCB, segment and send-arena shares per connection (Part H.7) are build errors.
    table = _device_table(model)
    max_connections = _checked_int(table["max_connections"]) if "max_connections" in table else webserver_init_default(src_dir, "max_connections")
    if max_connections < _MAX_CONNECTIONS_FLOOR:
        raise BuildError(
            model.device,
            f"[device].max_connections is {max_connections} - a webserver admitting no connection at all serves nothing, so the floor is {_MAX_CONNECTIONS_FLOOR}",
            rule="device.max-connections-range",
            fix=f"set max_connections to {_MAX_CONNECTIONS_FLOOR} or more",
            field="max_connections",
        )
    # lwIP's options are an ensemble and its own checks size the shared pools for ONE connection.
    # The N-connection half is checked here, where N is known.
    ensemble = _lwip_ensemble_problems(lwip_macros(), max_connections)
    if ensemble:
        raise BuildError(
            model.device,
            f"[device].max_connections is {max_connections}, which this firmware's lwIP settings cannot serve: " + "; ".join(ensemble),
            rule="device.max-connections-lwip",
            fix="raise the matching [lwip] values in toolchain/versions.toml or lower max_connections",
            field="max_connections",
        )
    backlog = _checked_int(table["backlog"]) if "backlog" in table else None
    if backlog is not None and backlog < max_connections:
        # backlog is how many arrivals can land while the event loop is busy elsewhere; past it lwIP
        # resets them, where nothing in src/ sees it - so a burst the ceiling admits is cut short.
        raise BuildError(
            model.device,
            f"[device].backlog is {backlog}, below the {max_connections} connections [device].max_connections admits - the accept queue would drop arrivals of one burst the ceiling says it accepts",
            rule="device.backlog-below-ceiling",
            fix=f"set backlog to at least {max_connections}, or leave it out",
            field="backlog",
        )
    if backlog is not None and backlog > max_connections + 1:
        # Every queued arrival holds a pcb, and every one past a full ceiling plus one is refused by
        # _serve() anyway, so a deeper queue buys nothing but pcbs held for arrivals it turns away.
        raise BuildError(
            model.device,
            f"[device].backlog is {backlog}, above max_connections + 1 ({max_connections + 1}) - each extra queued arrival holds a pcb only to be refused",
            rule="device.backlog-above-ceiling",
            fix=f"set backlog to at most {max_connections + 1}, or leave it out",
            field="backlog",
        )


def ntp_backoff(device_table: "TomlDoc", src_dir: Path) -> "tuple[int, int]":
    # The effective (retry_s, retry_max_s) pair: [device]'s stated keys, else asy_ntp_client.py's
    # _DEFAULT_RETRY_S/_DEFAULT_RETRY_MAX_S - what the generated NtpTiming carries.
    retry_s = _checked_int(device_table["ntp_retry_s"]) if "ntp_retry_s" in device_table else module_int_const(src_dir, "asy_ntp_client.py", "_DEFAULT_RETRY_S")
    retry_max_s = _checked_int(device_table["ntp_retry_max_s"]) if "ntp_retry_max_s" in device_table else module_int_const(src_dir, "asy_ntp_client.py", "_DEFAULT_RETRY_MAX_S")
    return retry_s, retry_max_s


def _check_ntp_backoff(model: DeviceModel, src_dir: Path) -> None:
    # The unsynced NTP retry backoff (Part C.7.2), checked as the effective pair: NTPClient would quietly clamp
    # an interval below its check tick or a cap below the interval, and its doubling must stay a small int.
    table = _device_table(model)
    if "ntp_retry_s" not in table and "ntp_retry_max_s" not in table:
        return  # the shipped defaults, pinned coherent by tests_scripts/test_buildgen_validate.py
    retry_s, retry_max_s = ntp_backoff(table, src_dir)
    tick = module_int_const(src_dir, "asy_ntp_client.py", "_NTP_CHECK_INTERV")
    if retry_s < tick:
        raise BuildError(
            model.device,
            f"[device].ntp_retry_s is {retry_s} - NTP checks its sync state every {tick}s, so no shorter retry interval exists",
            rule="device.ntp-retry-below-tick",
            fix=f"set ntp_retry_s to {tick} or more",
            field="ntp_retry_s",
        )
    if retry_max_s < retry_s:
        raise BuildError(
            model.device,
            f"[device].ntp_retry_max_s is {retry_max_s}, below the {retry_s}s first retry interval it caps",
            rule="device.ntp-retry-max-below-retry",
            fix=f"set ntp_retry_max_s to at least {retry_s}",
            field="ntp_retry_max_s",
        )
    bound = _SMALL_INT_MAX // module_int_const(src_dir, "asy_ntp_client.py", "_NTP_BACKOFF_MULT")
    if retry_max_s > bound:
        raise BuildError(
            model.device,
            f"[device].ntp_retry_max_s is {retry_max_s} - the retry wait doubles up to it, and past {bound} that leaves rp2's small ints",
            rule="device.ntp-retry-max-range",
            fix=f"set ntp_retry_max_s to at most {bound}",
            field="ntp_retry_max_s",
        )


def _uart_bus_value(src_dir: Path, table: "TomlDoc", name: str) -> int:
    # A bus table's stated value, else asy_uart_driver.UART's own default, read from source.
    if name in table:
        return _checked_int(table[name])
    return init_int_default(src_dir, "asy_uart_driver.py", "UART", name)


def _uart_links(model: DeviceModel) -> "list[InstanceSpec]":
    return [spec for spec in model.instances.values() if spec.driver == "uart_link"]


def _uart_crc_width(spec: InstanceSpec) -> int:
    # The trailer bytes the link's crc mode adds to every frame (absent: "none", 0 bytes).
    return UART_CRC_MODES[_checked_str(spec.fields.get("crc", "none"))][1]


def _check_uart_link_buses(model: DeviceModel, buses: "dict[str, TomlDoc]", src_dir: Path) -> None:
    # Refuses the timeout, rxbuf and poll-rate values the protocol would refuse at boot - a config mismatch out of
    # runtime scope (owner, 2026-09-24, Part C.7.2); the build refuses it instead (agent, 2026-09-24). Generated
    # code wires no framing (adds 0); the CRC adds the width of the link's crc mode.
    for spec in _uart_links(model):
        bus_name = _checked_str(spec.fields["bus"])
        _check_uart_link_timing(model, spec, bus_name, buses[bus_name], src_dir)
        _check_uart_link_receive(model, spec, bus_name, buses[bus_name], src_dir)


def _check_uart_link_timing(model: DeviceModel, spec: InstanceSpec, bus_name: str, table: "TomlDoc", src_dir: Path) -> None:
    # The poll rates and the reply timeout against each other, at the values that boot (UARTComm's own bounds).
    comm = "asy_uart_comm.py"
    gc_pause, timeout, poll_max, horizon = (module_int_const(src_dir, comm, n) for n in ("_GC_PAUSE_WORST_MS", "_DEFAULT_TIMEOUT_MS", "_POLL_WAIT_MAX_MS", "_TICKS_HORIZON_MS"))
    num, den, mult = (module_int_const(src_dir, comm, n) for n in ("_RESYNC_NUM", "_RESYNC_DEN", "_DRAIN_BOUND_MULT"))
    poll_wait, poll_idle = (_uart_bus_value(src_dir, table, n) for n in ("poll_wait_ms", "poll_idle_ms"))
    if not 1 <= poll_wait <= poll_max:
        raise BuildError(
            model.device,
            f"bus.{bus_name}: poll_wait_ms {poll_wait} is outside 1 … {poll_max} - a UART transaction polls at single-digit milliseconds or poll latency dominates every exchange (Part J.6)",
            rule="bus.uart-poll-wait-range",
            fix=f"set poll_wait_ms within 1..{poll_max}",
            field="poll_wait_ms",
            instance=spec.label,
        )
    if not poll_wait <= poll_idle <= horizon:
        # The idle poll is the slower rate (Part F.5.9), and a delay ticks_add() takes (extmod/modtime.c:178-196).
        raise BuildError(
            model.device,
            f"bus.{bus_name}: poll_idle_ms {poll_idle} is outside {poll_wait} … {horizon} - the idle poll is never faster than the transaction poll and stays a valid ticks delay",
            rule="bus.uart-poll-idle-range",
            fix=f"set poll_idle_ms within {poll_wait}..{horizon}",
            field="poll_idle_ms",
            instance=spec.label,
        )
    max_timeout = horizon * den // (num * mult)
    if timeout > max_timeout:
        raise BuildError(
            model.device,
            f"{spec.label}'s {timeout}ms reply timeout is above {max_timeout}ms - its drain bound, {num}/{den} x {mult} x the timeout, would leave rp2's 2**29 ms ticks range (Part J.6)",
            rule="instance.uart-timeout-max",
            fix=f"lower asy_uart_comm's _DEFAULT_TIMEOUT_MS to {max_timeout} or less",
            instance=spec.label,
        )
    min_timeout = 2 * poll_wait + poll_idle + gc_pause
    if timeout < min_timeout:
        raise BuildError(
            model.device,
            f"bus.{bus_name}: {spec.label}'s {timeout}ms reply timeout is below the {min_timeout}ms its polls need (2 x poll_wait_ms {poll_wait} + poll_idle_ms {poll_idle} + {gc_pause}ms GC pause) - every request would time out on a sound link (Part J.6)",
            rule="bus.uart-timeout-floor",
            fix=f"lower poll_wait_ms or poll_idle_ms until 2 x poll_wait_ms + poll_idle_ms + {gc_pause} is at most {timeout}",
            field="poll_idle_ms",
            instance=spec.label,
        )


def _check_uart_link_receive(model: DeviceModel, spec: InstanceSpec, bus_name: str, table: "TomlDoc", src_dir: Path) -> None:
    # rxbuf, the DMA receive ring and the receive cap: one framed frame or one poll's arrivals for rxbuf, and the
    # ring also the stop-and-wait peer's frames during one config flush's hold (asy_uart_comm._min_rx_ring()).
    comm = "asy_uart_comm.py"
    header, jitter, payload, timeout, hold = (module_int_const(src_dir, comm, n) for n in ("_HEADER_LEN", "_POLL_JITTER_MS", "_DEFAULT_PAYLOAD_SIZE", "_DEFAULT_TIMEOUT_MS", "_FLASH_HOLD_MAX_MS"))
    poll_wait, rxbuf, ring = (_uart_bus_value(src_dir, table, n) for n in ("poll_wait_ms", "rxbuf", "rx_ring"))
    baudrate = _checked_int(table["baudrate"])
    frame = header + payload + _uart_crc_width(spec)
    min_rxbuf = max(frame, (baudrate // 10) * (poll_wait + jitter) // 1000)
    if rxbuf < min_rxbuf:
        raise BuildError(
            model.device,
            f"bus.{bus_name}: rxbuf {rxbuf} is below the {min_rxbuf} bytes {spec.label} needs (one {frame}-byte frame, or baudrate {baudrate} over poll_wait_ms {poll_wait} + {jitter}ms jitter, whichever is larger)",
            rule="bus.uart-rxbuf-floor",
            fix=f"set rxbuf to {min_rxbuf} or more",
            field="rxbuf",
            instance=spec.label,
        )
    ring_min, ring_max = (module_int_const(src_dir, "asy_uart_driver.py", n) for n in ("_RX_RING_MIN", "_RX_RING_MAX"))
    if not ring_min <= ring <= ring_max:
        raise BuildError(model.device, f"bus.{bus_name}: rx_ring {ring} is outside {ring_min} … {ring_max} - the ring sizes the DMA can wrap", rule="bus.uart-rx-ring", fix=f"set rx_ring within {ring_min}..{ring_max}", field="rx_ring", instance=spec.label)
    if ring & (ring - 1):
        raise BuildError(
            model.device,
            f"bus.{bus_name}: rx_ring {ring} is not a power of two - the DMA wraps its write address on a power-of-two boundary (RP2040 datasheet 2.5.7, CH0_CTRL_TRIG.RING_SIZE)",
            rule="bus.uart-rx-ring",
            fix="set rx_ring to a power of two",
            field="rx_ring",
            instance=spec.label,
        )
    # One unacknowledged frame plus one per re-initiation, 4 x timeout apart, during the hold (J.6).
    frames = 1 + hold // (4 * timeout)
    floor = 1 << (max(min_rxbuf, frame * frames) - 1).bit_length()
    if ring < floor:
        raise BuildError(
            model.device,
            f"bus.{bus_name}: rx_ring {ring} is below the {floor}-byte floor {spec.label} needs (rxbuf's {min_rxbuf} bytes, or {frames} {frame}-byte frame(s) a stop-and-wait peer sends during a {hold} ms flash hold, rounded up to a power of two)",
            rule="bus.uart-rx-ring",
            fix=f"set rx_ring to {floor} or more",
            field="rx_ring",
            instance=spec.label,
        )
    chunks_max = module_int_const(src_dir, comm, "_CHUNKS_MAX")
    cap = _checked_int(spec.fields["max_transfer_bytes"]) if "max_transfer_bytes" in spec.fields else module_int_const(src_dir, comm, "_DEFAULT_MAX_TRANSFER_BYTES")
    largest = (chunks_max - 1) * payload
    if not payload <= cap <= largest:
        raise BuildError(
            model.device,
            f"{spec.label}.max_transfer_bytes {cap} is outside {payload} … {largest} - at least one payload, at most the protocol's largest train ({chunks_max - 1} chunks)",
            rule="instance.uart-transfer-cap",
            fix=f"set max_transfer_bytes within {payload}..{largest}",
            field="max_transfer_bytes",
            instance=spec.label,
        )


def _check_bus_tables(model: DeviceModel) -> "dict[str, TomlDoc]":
    # A device with no bus-attached instances at all is a valid, simplest-possible shape, so
    # [bus.*] may be absent entirely. An instance that does need one is caught downstream by
    # _check_required_fields(); this only validates the shape of whatever tables are present.
    buses = model.doc.get("bus", {})
    if not isinstance(buses, dict):
        raise BuildError(model.device, f"[bus] must be a table of bus tables, got {buses!r}", rule="bus.not-a-table", fix="declare each bus as its own [bus.<id>] table")
    tables: dict[str, TomlDoc] = {}
    for bus_name, bus_table in buses.items():
        if not isinstance(bus_table, dict):
            raise BuildError(model.device, f"bus.{bus_name} is not a table", rule="bus.not-a-table", fix=f"write it as a [bus.{bus_name}] table", field=bus_name)
        kind = _bus_kind(bus_name, model.device)
        for f in _BUS_WIRE_FIELDS[kind]:
            if f not in bus_table:
                raise BuildError(model.device, f"bus.{bus_name} ({kind}) is missing required field {f!r}", rule="bus.field-missing", fix=f"add {f} to [bus.{bus_name}]", field=f)
        if "cs_pin" in bus_table:
            raise BuildError(model.device, f"bus.{bus_name} declares cs_pin - that's an instance-exclusive resource, not a shared bus field", rule="bus.field-unknown", fix="move cs_pin to the instance that owns the chip select", field="cs_pin")
        if kind != "i2c" and "frequency" in bus_table:
            raise BuildError(model.device, f"bus.{bus_name} ({kind}) declares frequency - its own driver has no such parameter", rule="bus.field-unknown", fix=f"remove frequency from [bus.{bus_name}]", field="frequency")
        if kind == "i2c":
            _check_i2c_bus(model, bus_name, bus_table)
        if kind == "uart":
            _check_uart_bus(model, bus_name, bus_table)
        unknown = set(bus_table) - _BUS_ALLOWED_FIELDS[kind]
        if unknown:
            raise BuildError(
                model.device,
                f"bus.{bus_name} ({kind}) declares unrecognized field(s) {sorted(unknown)} - typo, or copy-pasted from an unrelated bus kind?",
                rule="bus.field-unknown",
                fix=f"remove or correct {sorted(unknown)}",
                field=min(unknown),
            )
        tables[bus_name] = bus_table
    return tables


def _check_i2c_bus(model: DeviceModel, bus_name: str, table: "TomlDoc") -> None:
    frequency = table.get("frequency")
    if not _is_int(frequency):
        raise BuildError(model.device, f"bus.{bus_name} (i2c) is missing an int frequency", rule="bus.field-missing", fix=f"add frequency = <Hz> to [bus.{bus_name}] as a whole number", field="frequency")
    if not 1 <= frequency <= _I2C_FREQUENCY_MAX_HZ:
        # 0 also divides by zero in the port's own clock setup (ports/rp2/machine_i2c.c:131).
        raise BuildError(
            model.device,
            f"bus.{bus_name} (i2c) frequency {frequency} Hz is outside 1 … {_I2C_FREQUENCY_MAX_HZ} - RP2040's I2C runs up to fast mode plus",
            rule="bus.i2c-frequency-range",
            fix=f"set frequency within 1..{_I2C_FREQUENCY_MAX_HZ}",
            field="frequency",
        )
    if "timeout" not in table:
        return
    timeout = table["timeout"]
    if not _is_int(timeout):
        raise BuildError(model.device, f"bus.{bus_name} (i2c) timeout must be an int, got {timeout!r}", rule="bus.field-type", fix="write timeout as a whole number of microseconds", field="timeout")
    if timeout < 1:
        raise BuildError(
            model.device,
            f"bus.{bus_name} (i2c) timeout {timeout} us is not positive - every SCL wait would end before it began",
            rule="bus.i2c-timeout-range",
            fix=f"set timeout within 1..{_I2C_TIMEOUT_MAX_US}",
            field="timeout",
        )
    if timeout > _I2C_TIMEOUT_MAX_US:
        raise BuildError(
            model.device,
            f"bus.{bus_name} (i2c) timeout {timeout} us is above the {_I2C_TIMEOUT_MAX_US} us bound - the boot bus clear waits up to one timeout per SCL edge, unfed, under the {_WDT_TIMEOUT_MS} ms watchdog",
            rule="bus.i2c-timeout-max",
            fix=f"set timeout to at most {_I2C_TIMEOUT_MAX_US}",
            field="timeout",
        )


def _check_uart_bus(model: DeviceModel, bus_name: str, table: "TomlDoc") -> None:
    baudrate = table.get("baudrate")
    if not _is_int(baudrate):
        raise BuildError(model.device, f"bus.{bus_name} (uart) is missing an int baudrate", rule="bus.field-missing", fix=f"add baudrate to [bus.{bus_name}] as a whole number", field="baudrate")
    if not 1 <= baudrate <= _UART_BAUDRATE_MAX:
        # The port keeps its own default for 0 or less without a word (ports/rp2/machine_uart.c:285-287).
        raise BuildError(
            model.device,
            f"bus.{bus_name} (uart) baudrate {baudrate} is outside 1 … {_UART_BAUDRATE_MAX} - RP2040's UART tops out at UARTCLK / 16",
            rule="bus.uart-baudrate-range",
            fix=f"set baudrate within 1..{_UART_BAUDRATE_MAX}",
            field="baudrate",
        )
    for f in _UART_OPTIONAL_INT_FIELDS:
        if f in table and not _is_int(table[f]):
            raise BuildError(model.device, f"bus.{bus_name} (uart) {f} must be an int, got {table[f]!r}", rule="bus.field-type", fix=f"write {f} as a whole number", field=f)
    rxbuf, txbuf = table.get("rxbuf"), table.get("txbuf")
    if _is_int(rxbuf) and not _UART_BUFFER_MIN <= rxbuf <= _UART_BUFFER_MAX:
        raise BuildError(
            model.device,
            f"bus.{bus_name} (uart) rxbuf {rxbuf} is outside {_UART_BUFFER_MIN} … {_UART_BUFFER_MAX} - the port raises a smaller one silently and refuses a larger one at boot",
            rule="bus.uart-rxbuf-range",
            fix=f"set rxbuf within {_UART_BUFFER_MIN}..{_UART_BUFFER_MAX}",
            field="rxbuf",
        )
    if _is_int(txbuf) and not _UART_BUFFER_MIN <= txbuf <= _UART_BUFFER_MAX:
        raise BuildError(
            model.device,
            f"bus.{bus_name} (uart) txbuf {txbuf} is outside {_UART_BUFFER_MIN} … {_UART_BUFFER_MAX} - the port raises a smaller one silently and refuses a larger one at boot",
            rule="bus.uart-txbuf-range",
            fix=f"set txbuf within {_UART_BUFFER_MIN}..{_UART_BUFFER_MAX}",
            field="txbuf",
        )


def _check_boot_clear_budget(model: DeviceModel, buses: "dict[str, TomlDoc]", src_dir: Path) -> None:
    # Every I2C bus's boot clear at its worst: each SCL wait runs to its timeout, plus the clock's half periods.
    tables = [t for name, t in buses.items() if _bus_kind(name, model.device) == "i2c"]
    if not tables:
        return
    drv = "asy_i2c_driver.py"
    pulses, half_us, default_us = (module_int_const(src_dir, drv, n) for n in ("_CLEAR_PULSES", "_CLEAR_HALF_PERIOD_US", "_DEFAULT_TIMEOUT_US"))
    timeouts = [_checked_int(t["timeout"]) if "timeout" in t else default_us for t in tables]
    worst_us = sum((pulses + 2) * t + 2 * (pulses + 1) * half_us for t in timeouts)
    if worst_us > _BOOT_CLEAR_BUDGET_MS * 1000:
        raise BuildError(
            model.device,
            f"the boot bus clear can run {worst_us // 1000} ms unfed over {len(timeouts)} I2C bus(es) ({pulses + 2} SCL waits of one timeout each per bus), above its {_BOOT_CLEAR_BUDGET_MS} ms budget (three quarters of the {_WDT_TIMEOUT_MS} ms watchdog)",
            rule="bus.boot-clear-budget",
            fix="lower a bus timeout",
            field="timeout",
        )


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
            raise BuildError(
                model.device,
                f"{spec.label}: singleton service driver {spec.driver!r} must not declare name_ext",
                rule="instance.name-ext-singleton",
                fix="remove name_ext: a singleton service has none",
                instance=spec.label,
                field="name_ext",
            )


def _instance_name(base_name: str, name_ext: str) -> str:
    return base_name if not name_ext else base_name + "_" + name_ext


def _check_required_fields(model: DeviceModel, buses: "dict[str, TomlDoc]", src_dir: Path) -> None:
    for spec in model.instances.values():
        # A driver resolving through driver_registry but absent from buildspec.py's tables would
        # fall through the .get() defaults below and have every real field flagged
        # "unrecognized" - fail-loud, but reading like a TOML typo. Named here instead.
        if spec.driver not in REQUIRED_TOML_FIELDS:
            raise BuildError(
                model.device,
                f"{spec.label}: driver {spec.driver!r} resolves via buildgen.driver_registry but has no entry in buildgen.buildspec's REQUIRED_TOML_FIELDS/ALLOWED_INSTANCE_FIELDS - a new driver needs a buildspec.py entry added by hand (SPECIFICATION.md L.6.6)",
                rule="instance.no-buildspec-row",
                fix=f"add a {spec.driver!r} row to buildgen/buildspec.py's REQUIRED_TOML_FIELDS and OPTIONAL_TOML_FIELDS",
                instance=spec.label,
            )
        if spec.driver not in SINGLETON_SERVICE_DRIVERS and "name_ext" not in spec.fields:
            raise BuildError(
                model.device,
                f"{spec.label} states no name_ext - a driver that may repeat names every instance explicitly, so a second one never renames the first",
                rule="instance.name-ext-missing",
                fix='add name_ext = "" (or a suffix) to this [[instance]]',
                instance=spec.label,
                field="name_ext",
            )
        for f in REQUIRED_TOML_FIELDS.get(spec.driver, ()):
            if f not in spec.fields:
                raise BuildError(model.device, f"{spec.label} is missing required field {f!r}", rule="instance.field-missing", fix=f"add {f} to this [[instance]]", instance=spec.label, field=f)
        if spec.driver in BUS_ATTACHED_DRIVERS:
            _check_instance_bus(model, spec, buses)
        if "address" in spec.fields and spec.driver not in ADDRESS_CAPABLE_DRIVERS:
            raise BuildError(
                model.device,
                f"{spec.label} declares an address field, but {spec.driver!r} has no address-select pin (see buildgen.buildspec.ADDRESS_CAPABLE_DRIVERS)",
                rule="instance.address-not-selectable",
                fix="remove the address field: this chip's address is fixed",
                instance=spec.label,
                field="address",
            )
        if spec.driver == "uart_link":
            _check_uart_link_fields(model, spec, src_dir)
        _check_instance_field_types(model, spec)


def _check_instance_bus(model: DeviceModel, spec: InstanceSpec, buses: "dict[str, TomlDoc]") -> None:
    # A non-string "bus" (e.g. a stray TOML array) would otherwise crash the membership check below
    # with a raw "unhashable type" TypeError instead of a fail-loud BuildError.
    bus = spec.fields["bus"]
    if not isinstance(bus, str):
        raise BuildError(model.device, f"{spec.label}.bus must be a string, got {bus!r}", rule="instance.field-type", fix='write bus as a quoted bus id, e.g. "i2c0"', instance=spec.label, field="bus")
    if bus not in buses:
        raise BuildError(model.device, f"{spec.label} references undeclared bus {bus!r}", rule="instance.bus-undeclared", fix=f"declare a [bus.{bus}] table or point bus at a declared one", instance=spec.label, field="bus")
    if spec.driver not in BUS_KIND_BY_DRIVER:
        raise BuildError(
            model.device,
            f"{spec.label}: driver {spec.driver!r} is in BUS_ATTACHED_DRIVERS but has no buildgen.buildspec.BUS_KIND_BY_DRIVER entry",
            rule="instance.no-bus-kind-row",
            fix=f"add a {spec.driver!r} row to buildgen/buildspec.py's BUS_KIND_BY_DRIVER",
            instance=spec.label,
        )
    # A driver pointed at the wrong kind of bus used to build cleanly - the bus merely had to exist - and
    # failed only at boot, deep inside that driver's construction, with a raw AttributeError.
    actual_kind = _bus_kind(bus, model.device)
    expected_kind = BUS_KIND_BY_DRIVER[spec.driver]
    if actual_kind != expected_kind:
        raise BuildError(
            model.device,
            f"{spec.label}.bus={bus!r} is a {actual_kind} bus, but driver {spec.driver!r} needs a {expected_kind} bus",
            rule="instance.bus-kind",
            fix=f"point bus at a {expected_kind} bus",
            instance=spec.label,
            field="bus",
        )


def _check_uart_link_fields(model: DeviceModel, spec: InstanceSpec, src_dir: Path) -> None:
    # The role strings are asy_uart_comm's own constants; crc must name a mode of buildspec's table. Comparing with
    # == (never `in` a set) keeps an array or inline table value a BuildError instead of an unhashable TypeError.
    roles = _uart_link_roles(src_dir)
    role = spec.fields.get("role")
    if not any(role == r for r in roles):
        raise BuildError(
            model.device,
            f"{spec.label}.role must be one of {sorted(roles)}, got {role!r}",
            rule="instance.uart-role",
            fix=f"set role to {roles[0]!r} or {roles[1]!r}",
            instance=spec.label,
            field="role",
        )
    crc = spec.fields.get("crc", "none")
    if not (isinstance(crc, str) and crc in UART_CRC_MODES):
        raise BuildError(
            model.device,
            f"{spec.label}.crc must be one of {sorted(UART_CRC_MODES)}, got {crc!r}",
            rule="instance.uart-crc-mode",
            fix=f"set crc to one of {sorted(UART_CRC_MODES)}, or leave it out for none",
            instance=spec.label,
            field="crc",
        )


def _check_instance_field_types(model: DeviceModel, spec: InstanceSpec) -> None:
    # These reach codegen's hex()/str() argument-building unvalidated otherwise: a quoted "0x77" raises a raw
    # TypeError from hex(), and a str()-rendered string reads in the generated module as a bare name.
    for f in ("address", "max_size", "trigger_s", "max_transfer_bytes"):
        if f in spec.fields and not _is_int(spec.fields[f]):
            raise BuildError(model.device, f"{spec.label}.{f} must be an int, got {spec.fields[f]!r}", rule="instance.field-type", fix=f"write {f} as a whole number", instance=spec.label, field=f)
    if "irq_pull_up" in spec.fields and not isinstance(spec.fields["irq_pull_up"], bool):
        raise BuildError(
            model.device,
            f"{spec.label}.irq_pull_up must be true or false, got {spec.fields['irq_pull_up']!r}",
            rule="instance.irq-pull-up-type",
            fix="write true or false",
            instance=spec.label,
            field="irq_pull_up",
        )
    # Catch-all: any field beyond driver/name_ext and this driver's own set is a copy-paste
    # error (Part L.5) - an "irq_pin" left from cloning an scd30 block, say, which codegen
    # would otherwise ignore silently, never reaching any driver's _build_call() branch.
    unknown = set(spec.fields) - {"driver", "name_ext"} - ALLOWED_INSTANCE_FIELDS.get(spec.driver, frozenset())
    if unknown:
        raise BuildError(
            model.device,
            f"{spec.label} declares unrecognized field(s) {sorted(unknown)} for driver {spec.driver!r}",
            rule="instance.field-unknown",
            fix=f"remove or correct {sorted(unknown)}",
            instance=spec.label,
            field=min(unknown),
        )


def _check_limits(model: DeviceModel) -> None:
    # A driver-declared @limits field is checked at the value the TOML states; a value of the wrong
    # type is named here too, since no other check need have looked at that field first.
    for spec in model.instances.values():
        for lf in spec.limits_schema:
            if lf.toml_field not in spec.fields:
                continue
            value = spec.fields[lf.toml_field]
            if lf.choices is not None:
                if not (_is_int(value) and value in lf.choices):
                    raise BuildError(
                        model.device,
                        f"{spec.label}.{lf.toml_field}={value!r} is not one of this driver's legal values {sorted(lf.choices)}",
                        rule="instance.field-not-in-set",
                        fix=f"set {lf.toml_field} to one of {sorted(lf.choices)}",
                        instance=spec.label,
                        field=lf.toml_field,
                    )
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise BuildError(model.device, f"{spec.label}.{lf.toml_field} must be a number, got {value!r}", rule="instance.field-type", fix=f"write {lf.toml_field} as a number", instance=spec.label, field=lf.toml_field)
            legal = f"{'*' if lf.min is None else lf.min}..{'*' if lf.max is None else lf.max}"
            if not math.isfinite(value):
                # TOML writes nan and inf as floats: nan compares False against both bounds, so it is refused first.
                raise BuildError(
                    model.device,
                    f"{spec.label}.{lf.toml_field}={value!r} is not a finite number",
                    rule="instance.field-not-finite",
                    fix=f"set {lf.toml_field} within {legal}",
                    instance=spec.label,
                    field=lf.toml_field,
                )
            if (lf.min is not None and value < lf.min) or (lf.max is not None and value > lf.max):
                raise BuildError(
                    model.device,
                    f"{spec.label}.{lf.toml_field}={value!r} is outside this driver's legal range ({lf.min}, {lf.max})",
                    rule="instance.field-out-of-range",
                    fix=f"set {lf.toml_field} within {legal}",
                    instance=spec.label,
                    field=lf.toml_field,
                )


def _check_all_buses_used(model: DeviceModel, buses: "dict[str, TomlDoc]") -> None:
    used = {_checked_str(spec.fields["bus"]) for spec in model.instances.values() if "bus" in spec.fields}
    orphans = set(buses) - used
    if orphans:
        raise BuildError(
            model.device,
            f"bus(es) {sorted(orphans)} declared but never referenced by any instance",
            rule="bus.unused",
            fix=f"remove {sorted(orphans)} or point an instance at them",
            field=min(orphans),
        )


def _check_uart_bus_single_owner(model: DeviceModel) -> None:
    # A UART is point-to-point: one instance per UART bus whatever its driver, so a future UART driver is held to it
    # too. The uart_link pair count runs first, so its own messages are unchanged.
    owners: dict[str, str] = {}
    for spec in model.instances.values():
        bus = spec.fields.get("bus")
        if not (isinstance(bus, str) and _VALID_BUS_IDS.get(bus) == "uart"):
            continue
        existing = owners.get(bus)
        if existing is not None:
            raise BuildError(
                model.device,
                f"bus.{bus} is claimed by both {existing!r} and {spec.label!r} - a UART is point-to-point, one instance per UART bus",
                rule="bus.uart-shared",
                fix="put one of them on the other uart bus",
                instance=spec.label,
                field="bus",
            )
        owners[bus] = spec.label


def _check_instance_name_collisions(model: DeviceModel, src_dir: Path) -> None:
    # Every logger lands in /status errcount under its name, the last registration winning there (owner, 2026-08-12),
    # so a second claim would hide the first: the mandatory modules claim first, then each instance its name and
    # its config store's. Last-wins stays the webserver's rule within one module; the build keeps two modules apart.
    wanted: list[tuple[str, str, str | None]] = []  # (logger name, its owner as the message names it, instance)
    for filename in _MANDATORY_MODULE_FILES:
        owns_store = _owns_config_store(src_dir / filename)  # first: it names a missing file as a build error
        name = parse_name_constant(src_dir / filename, model.device, filename)
        wanted.append((name, f"the mandatory {name} module", None))
        if owns_store:
            wanted.append(("CFGMGR_" + name, f"the mandatory {name} module's config store", None))
    for spec in model.instances.values():
        if spec.resolved_name is None:
            raise BuildInternalError(f"internal: resolved_name unresolved by collision-check time ({spec.label})")
        if spec.driver_info is None:
            raise BuildInternalError(f"internal: driver_info unresolved by collision-check time ({spec.label})")
        wanted.append((spec.resolved_name, repr(spec.label), spec.label))
        if _owns_config_store(spec.driver_info.source_path):
            wanted.append(("CFGMGR_" + spec.resolved_name, f"{spec.label}'s config store", spec.label))
    claims: dict[str, str] = {}
    for name, owner, label in wanted:
        existing = claims.get(name)
        if existing is not None:
            raise BuildError(
                model.device,
                f"instance_name collision: {owner} and {existing} both claim the logger name {name!r}",
                rule="names.logger-collision",
                fix="give one a disambiguating name_ext",
                instance=label,
            )
        claims[name] = owner


def _check_settings_key_collisions(model: DeviceModel) -> None:
    # /networking and /system each merge several modules' groups into one object, so a key two groups served
    # would answer from one of them only; notification's computed group is a section of its own.
    served: dict[tuple[str, str], str] = {}
    for section, module_var, fields, _hook in SETTINGS_GROUPS:
        for key in fields:
            existing = served.get((section, key))
            if existing is not None:
                raise BuildError(
                    model.device,
                    f"settings key {key!r} is served twice in /{section}: by {existing} and by {module_var}",
                    rule="names.settings-key-collision",
                    fix=f"drop {key!r} from one of the two groups in buildgen/validate.py's SETTINGS_GROUPS",
                    field=key,
                )
            served[(section, key)] = module_var


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
                f"instance_label collision: {key!r} and {existing!r} both resolve to the generated Python variable name {label!r}",
                rule="names.label-collision",
                fix="rename one driver module or its name_ext",
                instance=instance_label(key),
            )
        seen[label] = key


def _check_gpio_collisions(model: DeviceModel, buses: "dict[str, TomlDoc]") -> None:
    claims: dict[int, str] = {}

    def claim(pin: "TomlValue | None", owner: str, field: str) -> None:
        if pin is None:
            return
        if not _is_int(pin):
            raise BuildError(model.device, f"{owner}.{field} value {pin!r} is not an int", rule="gpio.type", fix=f"write {field} as a GPIO number", instance=owner, field=field)
        # Applies to every claimed pin device-wide (bus wire pins and instance-exclusive
        # cs_pin/irq_pin/pin alike) - real GPIO number, not one of the wireless-reserved four.
        if not gpio_exists(pin):
            raise BuildError(
                model.device,
                f"{owner}.{field}=GP{pin} is not a usable Pico W GPIO - must be 0-29, excluding the wireless-reserved GP23/24/25/29",
                rule="gpio.not-usable",
                fix=f"set {field} to a GPIO in 0-29 other than 23, 24, 25 and 29",
                instance=owner,
                field=field,
            )
        existing = claims.get(pin)
        if existing is not None:
            raise BuildError(model.device, f"GPIO{pin} claimed twice - by {existing!r} and by {owner!r} ({field})", rule="gpio.claimed-twice", fix="give one of them a free GPIO", instance=owner, field=field)
        claims[pin] = owner

    for bus_name, bus_table in buses.items():
        for f in ("scl_pin", "sda_pin", "sck_pin", "mosi_pin", "miso_pin", "tx_pin", "rx_pin"):
            if f not in bus_table:
                continue
            pin = bus_table[f]
            claim(pin, f"bus.{bus_name}", f)
            _check_bus_pin_role(model, bus_name, f, _checked_int(pin))
    for spec in model.instances.values():
        for f in ("cs_pin", "irq_pin", "pin"):
            if f in spec.fields:
                claim(spec.fields[f], spec.label, f)


def _check_bus_pin_role(model: DeviceModel, bus_name: str, field: str, pin: int) -> None:
    # Bus pins only: the GPIO must be hardwired to THIS bus's peripheral index in the role the field
    # claims (RP2040 datasheet Table 279), not merely be legal and unclaimed.
    role_table, expected_role = _BUS_PIN_ROLE[field]
    info = role_table.get(pin)
    if info is None:
        kind = "I2C" if role_table is I2C_ROLE else "SPI" if role_table is SPI_ROLE else "UART"
        raise BuildError(
            model.device,
            f"bus.{bus_name}.{field}=GP{pin} has no {kind} bus-wire function (RP2040 datasheet Table 279)",
            rule="gpio.no-function",
            fix=f"use a GPIO Table 279 gives {bus_name}'s {expected_role.upper()}",
            instance=f"bus.{bus_name}",
            field=field,
        )
    actual_bus, actual_role = info
    if actual_bus != bus_name:
        raise BuildError(
            model.device,
            f"bus.{bus_name}.{field}=GP{pin} is wired to {actual_bus}, not {bus_name}",
            rule="gpio.wrong-bus",
            fix=f"use a GPIO Table 279 gives {bus_name}'s {expected_role.upper()}, or move the bus to {actual_bus}",
            instance=f"bus.{bus_name}",
            field=field,
        )
    if actual_role != expected_role:
        raise BuildError(
            model.device,
            f"bus.{bus_name}.{field}=GP{pin} is {bus_name}'s {actual_role.upper()} pin, not its {expected_role.upper()} pin - pins transposed?",
            rule="gpio.wrong-role",
            fix=f"swap the pins so {field} names {bus_name}'s {expected_role.upper()} GPIO",
            instance=f"bus.{bus_name}",
            field=field,
        )


def _check_address_collisions(model: DeviceModel) -> None:
    per_bus_explicit: dict[str, dict[int, str]] = {}
    # Fixed-address collision is scoped to (bus, driver kind): two different fixed-address chip
    # types (e.g. scd30 + sgp40) on the same bus don't collide - each has its own distinct hardware
    # address - only two instances of the *same* fixed-address driver sharing a bus do.
    per_bus_driver_fixed: dict[tuple[str, str], list[str]] = {}
    for spec in model.instances.values():
        if "bus" not in spec.fields:
            continue
        bus = _checked_str(spec.fields["bus"])
        if "address" in spec.fields:
            address = _checked_int(spec.fields["address"])
            claims = per_bus_explicit.setdefault(bus, {})
            existing = claims.get(address)
            if existing is not None:
                raise BuildError(
                    model.device,
                    f"bus {bus!r}: address {address:#x} claimed by both {existing!r} and {spec.label!r}",
                    rule="bus.address-collision",
                    fix="give one of them its other legal address, or put it on another bus",
                    instance=spec.label,
                    field="address",
                )
            claims[address] = spec.label
        elif spec.driver in FIXED_ADDRESS_DRIVERS:
            per_bus_driver_fixed.setdefault((bus, spec.driver), []).append(spec.label)
    for (bus, driver), labels in per_bus_driver_fixed.items():
        if len(labels) > 1:
            raise BuildError(
                model.device,
                f"bus {bus!r}: {labels} are all {driver!r}-family instances with no address field - their hardware address is fixed, so they can't be told apart on the same bus",
                rule="bus.fixed-address-collision",
                fix="put each of them on its own bus",
                instance=labels[-1],
            )


def _check_uart_link_roles(model: DeviceModel, buses: "dict[str, TomlDoc]", src_dir: Path) -> None:
    # RP2040 has two UART peripherals, so a device wires at most one crossover pair, each end on its own
    # UART - which compute_twin_wiring() relies on. Without it two initiators built and booted silently,
    # both looping on read timeouts, while the twin's pairing loop left responder_bus None.
    links = _uart_links(model)
    if not links:
        return
    initiator_role, responder_role = _uart_link_roles(src_dir)
    initiators = [spec for spec in links if spec.fields.get("role") == initiator_role]
    responders = [spec for spec in links if spec.fields.get("role") == responder_role]
    if len(initiators) != 1 or len(responders) != 1:
        raise BuildError(
            model.device,
            f"a device wires exactly one uart_link initiator and one responder (RP2040 has only two UART peripherals) - found {len(initiators)} initiator(s) {sorted(s.label for s in initiators)} and {len(responders)} responder(s) {sorted(s.label for s in responders)}",
            rule="instance.uart-link-pair",
            fix="declare exactly one initiator and one responder uart_link",
        )
    initiator, responder = initiators[0], responders[0]
    a, b = _checked_str(initiator.fields["bus"]), _checked_str(responder.fields["bus"])
    x, y = _checked_int(buses[a]["baudrate"]), _checked_int(buses[b]["baudrate"])
    if x != y:
        raise BuildError(
            model.device,
            f"uart_link pair: bus.{a} runs at {x} baud and bus.{b} at {y} - both ends of a link must agree (Part J.6: agreed out of band, never negotiated)",
            rule="instance.uart-baud-mismatch",
            fix="state one baudrate on both buses",
            field="baudrate",
            instance=responder.label,
        )
    crc_a, crc_b = initiator.fields.get("crc", "none"), responder.fields.get("crc", "none")
    if crc_a != crc_b:
        raise BuildError(
            model.device,
            f"uart_link pair: {initiator.label} uses crc {crc_a!r} and {responder.label} uses {crc_b!r} - both ends of a link must agree (Part J.6: agreed out of band, never negotiated)",
            rule="instance.uart-crc-mismatch",
            fix="state one crc mode on both ends",
            field="crc",
            instance=responder.label,
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
        raise BuildError(
            model.device,
            f"{consumer_label}'s wiring.{toml_field}={target_key_str!r} does not resolve to any declared instance",
            rule="wiring.target-unresolved",
            fix='point it at a declared instance, written "<driver>" or "<driver>_<name_ext>"',
            instance=consumer_label,
            field=toml_field,
        )
    if target.driver_info is None:
        raise BuildInternalError("internal: target.driver_info unresolved by wiring-reference-check time")
    if target.driver_info.class_name != wf.producer_class:
        raise BuildError(
            model.device,
            f"{consumer_label}'s wiring.{toml_field}={target_key_str!r} resolves to a {target.driver_info.class_name}, but {wf.mode!r} wiring requires a {wf.producer_class}",
            rule="wiring.target-class",
            fix=f"point it at an instance whose driver is a {wf.producer_class}",
            instance=consumer_label,
            field=toml_field,
        )


def _check_source_field_reference(model: DeviceModel, value: "TomlValue", consumer_label: str, toml_field: str) -> None:
    # Shared by warn_*'s getters and _VALUE_WIRING's per-value wiring (SPECIFICATION.md Part L.6.3): the generic
    # {source, field} shape, resolved against any producer, the field set read from its get_data() namedtuple.
    if not isinstance(value, dict) or "source" not in value or "field" not in value:
        raise BuildError(
            model.device,
            f"{consumer_label}'s wiring.{toml_field} must be a {{source, field}} table",
            rule="wiring.source-shape",
            fix='write it as a table with source = "<instance>" and field = "<get_data() field>"',
            instance=consumer_label,
            field=toml_field,
        )
    source, field_name = value["source"], value["field"]
    # A non-string "source" would otherwise crash resolve_instance_key()'s `"_" in value` check
    # with a raw TypeError instead of a fail-loud BuildError.
    if not isinstance(source, str) or not isinstance(field_name, str):
        raise BuildError(model.device, f"{consumer_label}'s wiring.{toml_field}.source/field must both be strings", rule="wiring.source-shape", fix="quote both source and field", instance=consumer_label, field=toml_field)
    producer = model.instances.get(resolve_instance_key(model, source))
    if producer is None:
        raise BuildError(
            model.device,
            f"{consumer_label}'s wiring.{toml_field}.source={source!r} does not resolve to any declared instance",
            rule="wiring.source-unresolved",
            fix='point source at a declared instance, written "<driver>" or "<driver>_<name_ext>"',
            instance=consumer_label,
            field=toml_field,
        )
    if producer.driver_info is None:
        raise BuildInternalError("internal: source.driver_info unresolved by source-field-check time")
    fields = data_fields(producer.driver_info.source_path, producer.driver_info.class_name, model.device, producer.label)
    if field_name not in fields:
        raise BuildError(
            model.device,
            f"{consumer_label}'s wiring.{toml_field}.field={field_name!r} names no field of {source}'s get_data() result",
            rule="source.field-unknown",
            fix=f"use one of {sorted(fields)}",
            instance=consumer_label,
            field=toml_field,
        )


def _check_default_provider_params(model: DeviceModel, spec: InstanceSpec, toml_field: str, value: "TomlDoc") -> ast.ClassDef:
    # Shared by _WIRING- and _VALUE_WIRING-based defaults, on the principle that the class
    # definition IS the schema: a `_Default<Field>`'s own __init__ signature says which keys a
    # `{default = true, ...}` sub-table may carry, read by AST like _WIRING and _LIMITS.
    if spec.driver_info is None:
        raise BuildInternalError("internal: driver_info unresolved by default-provider-check time")
    class_node = find_default_class(spec.driver_info.source_path, model.device, spec.label, toml_field)
    if class_node is None:
        raise BuildError(
            model.device,
            f"{spec.label}'s wiring.{toml_field} opts into the default, but {spec.driver_info.source_path.name} defines no {default_class_name(toml_field)} class",
            rule="wiring.default-class-missing",
            fix=f"wire {toml_field} to a real instance, or define {default_class_name(toml_field)} in {spec.driver_info.source_path.name}",
            instance=spec.label,
            field=toml_field,
        )
    params = default_init_params(class_node)
    allowed = {p.name for p in params}
    required = {p.name for p in params if not p.has_default}
    given = set(value) - {"default"}
    unknown = given - allowed
    if unknown:
        raise BuildError(
            model.device,
            f"{spec.label}'s wiring.{toml_field} default sub-table has unrecognized key(s) {sorted(unknown)} for {class_node.name}",
            rule="wiring.default-key-unknown",
            fix=f"use only {sorted(allowed)} beside default" if allowed else "leave only default = true in the sub-table",
            instance=spec.label,
            field=toml_field,
        )
    missing = required - given
    if missing:
        raise BuildError(
            model.device,
            f"{spec.label}'s wiring.{toml_field} default sub-table is missing required key(s) {sorted(missing)} for {class_node.name}",
            rule="wiring.default-key-missing",
            fix=f"add {sorted(missing)} to the default sub-table",
            instance=spec.label,
            field=toml_field,
        )
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
            rule="wiring.default-attr-missing",
            fix=f"define {wf.target} on {class_node.name}",
            instance=spec.label,
            field=toml_field,
        )


def _check_default_value_selection(model: DeviceModel, spec: InstanceSpec, vwf: ValueWiringField) -> None:
    value = spec.wiring[vwf.toml_field]
    if not isinstance(value, dict):
        raise BuildInternalError("internal: default-selection check reached with a non-table wiring value")
    _check_default_provider_params(model, spec, vwf.toml_field, value)


def _check_warn_signals(model: DeviceModel, spec: InstanceSpec) -> None:
    # The notification's per-signal getters (Part C.14.3), named from the generator's one catalog: a warn_*
    # key and its {source} edge are legal only there (agent, 2026-09-09), and each one stays optional.
    for toml_field, value in spec.wiring.items():
        if not toml_field.startswith("warn_"):
            continue
        if spec.driver != "notification":
            raise BuildError(
                model.device,
                f"{spec.label} declares wiring.{toml_field}, but warn signals belong to the notification instance",
                rule="wiring.warn-outside-notification",
                fix=f"move {toml_field} under the notification instance's [instance.wiring]",
                instance=spec.label,
                field=toml_field,
            )
        if toml_field not in WARN_SIGNALS:
            raise BuildError(
                model.device,
                f"{spec.label} declares wiring.{toml_field}, but the signal catalog knows only {sorted(WARN_SIGNALS)}",
                rule="wiring.warn-unknown",
                fix=f"use one of {sorted(WARN_SIGNALS)}, or add the signal to buildgen/signals.py's WARN_SIGNALS",
                instance=spec.label,
                field=toml_field,
            )
        _check_source_field_reference(model, value, spec.label, toml_field)


def _check_instance_wiring(model: DeviceModel) -> None:
    for spec in model.instances.values():
        _check_warn_signals(model, spec)
        value_wiring_fields = {vwf.toml_field for vwf in spec.value_wiring_schema}
        for toml_field, value in spec.wiring.items():
            if toml_field.startswith("warn_") or toml_field in value_wiring_fields:
                continue  # checked by _check_warn_signals() / _check_value_wiring() (Part L.6.3)
            wf = _resolve_wiring_field(spec.wiring_schema, toml_field)
            if wf is None:
                raise BuildError(
                    model.device,
                    f"{spec.label} declares wiring.{toml_field}, but its driver has no matching _WIRING entry",
                    rule="wiring.field-unknown",
                    fix=f"remove wiring.{toml_field} or correct its name",
                    instance=spec.label,
                    field=toml_field,
                )
            # SPECIFICATION.md Part L.6.2's wiring-defaults mechanism: a {default = true, ...} sub-table opts
            # out of resolving a real instance reference, so it branches before any string-only handling.
            if isinstance(value, dict) and value.get("default") is True:
                _check_default_selection(model, spec, wf, toml_field, value)
                continue
            if not isinstance(value, str):
                raise BuildError(
                    model.device,
                    f"{spec.label}'s wiring.{toml_field} must be a string instance reference, got {value!r}",
                    rule="wiring.target-type",
                    fix="write it as a quoted instance name, or as a {default = true} table",
                    instance=spec.label,
                    field=toml_field,
                )
            _check_wiring_reference(model, wf, value, spec.label, toml_field)
        for wf in spec.wiring_schema:
            if wf.required and wf.toml_field not in spec.wiring:
                raise BuildError(model.device, f"{spec.label} is missing required wiring.{wf.toml_field}", rule="wiring.field-missing", fix=f"add {wf.toml_field} to this instance's [instance.wiring]", instance=spec.label, field=wf.toml_field)


def _check_value_wiring(model: DeviceModel) -> None:
    # SPECIFICATION.md Part L.6.3's per-value wiring: each field independently resolves to either a
    # real {source, field} reference (any producer, matched by attribute name) or an explicit
    # {default = true, ...} opt-in (L.6.2) - never silently defaulted just because it's absent.
    for spec in model.instances.values():
        for vwf in spec.value_wiring_schema:
            value = spec.wiring.get(vwf.toml_field)
            if value is None:
                if vwf.required:
                    raise BuildError(
                        model.device,
                        f"{spec.label} is missing required wiring.{vwf.toml_field}",
                        rule="wiring.field-missing",
                        fix=f"add {vwf.toml_field} to this instance's [instance.wiring]",
                        instance=spec.label,
                        field=vwf.toml_field,
                    )
                continue
            if isinstance(value, dict) and value.get("default") is True:
                _check_default_value_selection(model, spec, vwf)
                continue
            _check_source_field_reference(model, value, spec.label, vwf.toml_field)


def _check_device_wiring(model: DeviceModel, src_dir: Path) -> None:
    # Each declared field against every consumer's own @wiring tag, recorded on the model per consumer so
    # codegen renders each consumer's own target (Part L.3).
    wiring = _device_table(model).get("wiring", {})
    if not isinstance(wiring, dict):
        raise BuildInternalError(f"internal: {model.device}'s [device].wiring reached the wiring check unchecked")
    schemas = {(f, label): parse_wiring(src_dir / f, model.device, label) for consumers in _DEVICE_WIRING_CONSUMERS.values() for f, label in consumers}
    for toml_field, value in wiring.items():
        consumers = _DEVICE_WIRING_CONSUMERS.get(toml_field)
        if consumers is None:
            raise BuildError(model.device, f"[device.wiring] declares unknown field {toml_field!r}", rule="device.wiring-field-unknown", fix=f"use one of {sorted(_DEVICE_WIRING_CONSUMERS)}", field=toml_field)
        if not isinstance(value, str):
            raise BuildError(model.device, f"[device.wiring].{toml_field} must be a string instance reference, got {value!r}", rule="wiring.target-type", fix="write it as a quoted instance name", field=toml_field)
        for module_file, consumer_label in consumers:
            wf = _resolve_wiring_field(schemas[(module_file, consumer_label)], toml_field)
            if wf is None:
                raise BuildError(
                    model.device,
                    f"[device.wiring].{toml_field} declared, but {module_file} has no matching @wiring tag",
                    rule="device.wiring-no-tag",
                    fix=f"add a # @wiring {toml_field} tag to {module_file}, or drop the field",
                    field=toml_field,
                )
            _check_wiring_reference(model, wf, value, "device.wiring", toml_field)
            model.device_wiring.setdefault(consumer_label, {})[toml_field] = wf

    # Required-field enforcement mirroring _check_instance_wiring's. Both device-wiring fields are optional
    # today, so this never fires yet; a field is required if ANY consumer's tag says so.
    for toml_field, consumers in _DEVICE_WIRING_CONSUMERS.items():
        if toml_field in wiring:
            continue
        for module_file, consumer_label in consumers:
            wf = _resolve_wiring_field(schemas[(module_file, consumer_label)], toml_field)
            if wf is not None and wf.required:
                raise BuildError(model.device, f"[device.wiring] is missing required field {toml_field!r}", rule="device.wiring-field-missing", fix=f"add {toml_field} to [device.wiring]", field=toml_field)


def _check_requires_tags(model: DeviceModel, buses: "dict[str, TomlDoc]") -> None:
    for spec in model.instances.values():
        if not spec.requires_tags:
            continue
        bus_name = spec.fields.get("bus")
        if bus_name is None:
            raise BuildError(
                model.device,
                f"{spec.label} declares @requires bus tags but has no 'bus' field",
                rule="instance.requires-without-bus",
                fix="drop the driver's @requires bus tags, or give it a bus",
                instance=spec.label,
            )
        check_requires_tags(spec.requires_tags, buses[_checked_str(bus_name)], model.device, spec.label, _checked_str(bus_name))


def build_model(toml_path: Path, src_dir: Path) -> DeviceModel:
    model = load_device(toml_path)
    _check_device_table(model, src_dir)
    buses = _check_bus_tables(model)
    _check_boot_clear_budget(model, buses, src_dir)
    _resolve_instances(model, src_dir)
    _check_required_fields(model, buses, src_dir)
    _check_uart_link_roles(model, buses, src_dir)
    _check_limits(model)
    _check_all_buses_used(model, buses)
    _check_uart_bus_single_owner(model)
    _check_instance_name_collisions(model, src_dir)
    _check_settings_key_collisions(model)
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
    _check_ntp_backoff(model, src_dir)
    _check_uart_link_buses(model, buses, src_dir)
    return model


__all__ = ["InstanceSpec", "build_model", "instance_label"]
