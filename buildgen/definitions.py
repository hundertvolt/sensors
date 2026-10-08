"""Generates a device's website `definitions.json` (SPECIFICATION.md Part H.5) from a validated
`DeviceModel` plus the `# @web`/`# @web-group` tags on the `src/` files that own each field/group
(`buildgen.web_tag`; design rationale: Part H.5.1). CLI at the bottom: manual use + `build_website.sh`."""

import argparse
import functools
import json
import sys
from pathlib import Path
from typing import Any

from buildgen.errors import BuildError
from buildgen.graph import build_construction_order
from buildgen.model import MAINTENANCE_NAMES, DeviceModel, InstanceSpec
from buildgen.schema_ast import FieldSchema, extract_field_schemas
from buildgen.validate import build_model
from buildgen.version import WEBSITE_VERSION
from buildgen.web_tag import SELF_GROUP, WebFieldTag, WebGroupTag, parse_web_group_tags, parse_web_tags

REPO_ROOT = Path(__file__).resolve().parent.parent
# The one code catalog (SPECIFICATION.md C.7.1): errno/wrnno texts and the status-code tables.
_CATALOG_PATH = Path(__file__).resolve().parent / "error_catalog.json"

# SCHEMA_VERSION is this file's wire-format shape version - can js/definitions.js understand what
# it was served. WEBSITE_VERSION is the product/build version, a different concept entirely;
# never conflate the two (Part L.7).
SCHEMA_VERSION = "1.0.0"

# The page's poll interval: the status section's own and the default every other polled section takes.
# @tunable web.poll_interval_ms = 3000
_POLL_INTERVAL_MS = 3000

# Fixed, generator-owned REST-endpoint skeleton (H.4: "Nav grouping: Mirrors the 6 REST endpoints
# 1:1") - never per-device data, so never tag-derived (SPECIFICATION.md Part H.5.1). "groups" is
# filled in per device below; "notification" is appended only when a `notification` instance exists.
_SECTION_SKELETON: "tuple[dict[str, Any], ...]" = (
    {"key": "measurements", "label": "Measurements", "description": "Live sensor readings, refreshed automatically.", "rest": {"get": "/measurements"}, "pollGroup": "live"},
    {"key": "sensors", "label": "Sensors", "description": "Per-sensor configuration. Each card applies independently.", "rest": {"get": "/sensors", "put": "/sensors"}, "pollGroup": "settings"},
    {"key": "networking", "label": "Networking", "description": "Wi-Fi credentials, identity, and NTP time sync. Live status (IP, RSSI, uptime, sync age) is on the Status page.", "rest": {"get": "/networking", "put": "/networking"}, "pollGroup": "settings"},
    {"key": "system", "label": "System", "rest": {"get": "/system", "put": "/system"}, "pollGroup": "settings"},
    {"key": "status", "label": "Status", "description": "Live system/network/error state. Error counts are always visible; click a module to see its history.", "rest": {"get": "/status", "put": "/status"}, "pollGroup": "live", "pollIntervalMs": _POLL_INTERVAL_MS},
)
_NOTIFICATION_SECTION_SKELETON: "dict[str, Any]" = {
    "key": "notification", "label": "Notification", "rest": {"get": "/notification", "put": "/notification"}, "pollGroup": "settings",
}

# Instances scanned per-device (their web-facing fields/groups vary by which TOML instance exists,
# and by name_ext when more than one instance of the same driver is present).
_SENSOR_DRIVERS = ("scd30", "sgp40", "bmp3xx", "isl29125")

# buildgen.codegen._KNOWN_SIGNALS' own parallel: label/unit UI metadata for the same three warn_*
# TOML wiring keys, keyed identically. Min/max match that catalog's own field-schema literals
# exactly (_FIELD_WARN_CO2/_FIELD_WARN_VOC/_FIELD_WARN_HUM).
_WARN_SIGNAL_WEB_CATALOG: "dict[str, dict[str, Any]]" = {
    "warn_co2": {"key": "WarnCO2", "label": "CO2 Warning Threshold", "unit": "ppm", "kind": "number", "min": 0, "max": 3000},
    "warn_voc": {"key": "WarnVOC", "label": "VOC Warning Threshold", "kind": "number", "min": 0, "max": 500},
    "warn_hum": {"key": "WarnHum", "label": "Humidity Warning Threshold", "unit": "%", "kind": "number", "min": 0.0, "max": 100.0, "float": True},
}

# Dispatch-only webserver-level fields: no per-device variation and no single owning driver file
# (Part H.5.1), each flagged dispatch so the never-"Unchanged" class reads from definitions alone.
# Sources in asy_webserver_service.py: _dispatch_notification_led(), _SYSTEM_CMDS, PauseTime's field.
_SYSTEM_COMMAND_GROUP: "dict[str, Any]" = {
    "key": "command", "label": "System Command", "submit": True,
    "fields": [{"key": "SystemCmd", "label": "Command", "kind": "enum", "dispatch": True, "options": [
        {"value": "reboot", "label": "Reboot"},
        {"value": "bootloader", "label": "Reboot into bootloader"},
        {"value": "mempause", "label": "Pause backups for 5 minutes"},
    ]}],
}
_NOTIFICATION_FLASH_GROUP: "dict[str, Any]" = {
    "key": "flash", "label": "Manual Flash Command", "submit": True, "submitLabel": "Flash LED",
    "fields": [{"key": "LightCmdLED", "label": "LED Flash", "kind": "composite", "dispatch": True, "subFields": [
        {"key": "R", "label": "Red", "kind": "number", "min": 0, "max": 255},
        {"key": "G", "label": "Green", "kind": "number", "min": 0, "max": 255},
        {"key": "B", "label": "Blue", "kind": "number", "min": 0, "max": 255},
        {"key": "T", "label": "Time (s)", "kind": "number", "min": 0.5, "max": 60.0, "float": True},
    ]}],
}
_NOTIFICATION_PAUSE_GROUP: "dict[str, Any]" = {
    "key": "pause", "label": "Pause Notifications", "submit": True,
    "fields": [{
        "key": "PauseTime", "label": "Pause Time", "unit": "s", "kind": "number", "min": 0, "max": 3600,
        "description": "Temporarily suppress automatic LED notifications. Current value is live (from Status).", "dispatch": True,
    }],
}
_RESET_ERRORS_GROUP: "dict[str, Any]" = {
    "key": "resetErrors", "label": "Reset Errors", "submit": True, "submitLabel": "Reset All Errors",
    "fields": [{
        "key": "ResetErrors", "label": "Confirm Reset", "kind": "toggle", "onLabel": "Yes, reset", "offLabel": "No",
        "description": "Resets every module's error counter and history in one call. Absent/No is a no-op.", "dispatch": True,
    }],
}

# GET /system's nested "build" entry (codegen's build_info), shown read-only through each field's path.
_BUILD_GROUP: "dict[str, Any]" = {
    "key": "build", "label": "Build",
    "fields": [
        {"key": "FirmwareVersion", "label": "Firmware Version", "kind": "readonly", "path": ["build", "FirmwareVersion"]},
        {"key": "WebsiteVersion", "label": "Website Version", "kind": "readonly", "path": ["build", "WebsiteVersion"]},
        {"key": "BuildDate", "label": "Build Date", "kind": "readonly", "path": ["build", "BuildDate"]},
    ],
}

# GET /status networking's MQTT fields, in asy_mqtt_client.get_link_status()'s order (Part A.11).
_MQTT_STATUS_FIELDS: "tuple[dict[str, Any], ...]" = (
    {"key": "MQTTState", "label": "MQTT State", "kind": "readonly", "description": "disabled, waiting (no network), connecting, connected, backoff, or no memory."},
    {"key": "MQTTConnected", "label": "MQTT Connected", "kind": "readonly"},
    {"key": "MQTTBroker", "label": "MQTT Broker IP", "kind": "readonly"},
    {"key": "MQTTUptime", "label": "MQTT Connection Uptime", "unit": "s", "kind": "readonly"},
    {"key": "MQTTConnects", "label": "MQTT Connects", "kind": "readonly"},
    {"key": "MQTTTeardowns", "label": "MQTT Connections Lost", "kind": "readonly"},
    {"key": "MQTTLastReason", "label": "MQTT Last End Reason", "kind": "readonly"},
    {"key": "MQTTTxMsgs", "label": "MQTT Messages Sent", "kind": "readonly"},
    {"key": "MQTTTxDropped", "label": "MQTT Messages Dropped", "kind": "readonly", "description": "Outbound messages not sent: queue full, refused, or QoS 1 given up."},
    {"key": "MQTTRxMsgs", "label": "MQTT Messages Received", "kind": "readonly"},
    {"key": "MQTTRxDropped", "label": "MQTT Messages Discarded", "kind": "readonly", "description": "Inbound packets too large to parse, or QoS 1 acknowledgements that found no room."},
    {"key": "MQTTPingTimeouts", "label": "MQTT Ping Timeouts", "kind": "readonly", "description": "Connections closed because the broker stopped answering while Wi-Fi was up."},
    {"key": "MQTTShortSessions", "label": "MQTT Short Sessions", "kind": "readonly", "description": "Sessions the broker ended right after they began - another client with this client ID?"},
    {"key": "MQTTLastRxTopic", "label": "MQTT Last Received Topic", "kind": "readonly"},
)

# Errcount module catalog (H.6): {have-key: (label, has_cfgmgr_companion)}. A have-key is an
# instance's own `driver` string, plus the five mandatory keys that are never [[instance]]
# entries. Generator-owned like the catalogs above: cosmetic labels, owned by no source file.
_MANDATORY_ERRCOUNT_KEYS = frozenset({"wifi", "dns", "ntp", "system", "webserver"})
_ERRCOUNT_CATALOG: "tuple[tuple[str, str, bool], ...]" = (
    ("wifi", "Wi-Fi", True),
    ("dns", "Captive DNS", False),
    ("ntp", "NTP Client", True),
    ("fram", "FRAM Storage", False),
    ("system", "System", True),
    ("scd30", "SCD30", True),  # (H.6) a CFGMGR_ companion for the three FRC settings
    ("sgp40", "SGP40", True),
    ("bmp3xx", "BMP388", True),
    ("isl29125", "ISL29125", True),
    ("neopixel", "Neopixel LED", False),
    ("notification", "Notification Service", True),
    ("uart_link", "UART Link", False),  # no CFGMGR_ companion: UARTComm has no config schema - its
    # parameters are an out-of-band two-implementation wire contract, never runtime-writable (Part J.6)
    ("mqtt", "MQTT Client", True),
    ("webserver", "Web Server", False),
)
# Display names for the name_ext values a multi-instance driver carries, where the raw suffix is an
# abbreviation. Anything absent renders as the raw name_ext, which is what a device author typed.
_NAME_EXT_LABEL: "dict[str, str]" = {"init": "Initiator", "resp": "Responder"}
_ERRCOUNT_NAME: "dict[str, str]" = {
    "wifi": "WIFI", "dns": "DNSSRV", "ntp": "NTP", "fram": "FRAM", "system": "SYSTEM",
    "scd30": "SCD30", "sgp40": "SGP40", "bmp3xx": "BMP3XX", "isl29125": "ISL29125", "neopixel": "NEOPIXEL",
    "notification": "NOTIFY", "mqtt": "MQTT", "webserver": "WEBSERVER",
}
_CFGMGR_LABEL: "dict[str, str]" = {
    "wifi": "Wi-Fi Config Store", "ntp": "NTP Config Store", "system": "System Config Store",
    "scd30": "SCD30 Config Store", "sgp40": "SGP40 Config Store", "bmp3xx": "BMP388 Config Store", "isl29125": "ISL29125 Config Store",
    "notification": "Notification Config Store", "mqtt": "MQTT Config Store",
}


@functools.cache
def _load_catalog() -> "dict[str, Any]":
    # Read once per process; every caller only reads it.
    catalog: dict[str, Any] = json.loads(_CATALOG_PATH.read_text())
    return catalog


def _status_codes(table: str, device: str, field: str) -> "dict[str, str]":
    # A readonly field's codes=<table>, inlined as {"<n>": "<text>"} from the catalog's status section.
    tables: dict[str, dict[str, dict[str, str]]] = _load_catalog().get("status", {})
    if table not in tables:
        raise BuildError(device, f"codes={table!r} names no status table in {_CATALOG_PATH.name} (tables: {sorted(tables)})", field=field)
    return {num: row["text"] for num, row in tables[table].items()}


def _errcount_codes(catalog: "dict[str, Any]") -> "dict[str, dict[str, str]]":
    # Every non-retired errno/wrnno: numbers are global, so one table serves every errcount row.
    return {kind: {num: row["text"] for num, row in catalog["codes"][kind].items() if not row.get("retired")} for kind in ("E", "W")}


class _DriverTags:
    # Parsed `@web`/`@web-group` tags plus real `ConfigSchema` literals for one source file,
    # cached so a file scanned by more than one instance (two SCD30s, or WiFi/NTP/System, which are
    # scanned once per device regardless of instance count) is only ever tokenized/AST-parsed once.

    def __init__(self, path: Path, device: str, instance_label: str) -> None:
        self.field_tags: tuple[WebFieldTag, ...] = parse_web_tags(path, device, instance_label)
        self.group_tags: tuple[WebGroupTag, ...] = parse_web_group_tags(path, device, instance_label)
        self.schemas: dict[str, FieldSchema] = extract_field_schemas(path)


def _load_driver_tags(cache: "dict[Path, _DriverTags]", path: Path, device: str, instance_label: str) -> _DriverTags:
    if path not in cache:
        cache[path] = _DriverTags(path, device, instance_label)
    return cache[path]


def _coerce_special_value(raw: str, field_type: "str | None") -> "int | float | str | None":
    if raw == "null":
        return None  # the one value-free special: "nothing yet", e.g. no backup since boot
    if field_type == "float":
        return float(raw)
    if field_type == "int":
        return int(raw)
    return raw


def _coerce_readonly_special(raw: str) -> "int | float | str | None":
    # A readonly field has no schema type: its special reads as null, an int, a float or a string.
    if raw == "null":
        return None
    for convert in (int, float):
        try:
            return convert(raw)
        except ValueError:
            continue
    return raw


def _infer_kind(tag: WebFieldTag, field_type: "str | None", special: object, device: str, path: Path) -> str:
    if tag.kind is not None:
        return tag.kind
    if field_type is None:
        raise BuildError(device, f"{path}: @web tag for {tag.field_name!r} has no matching ConfigSchema constant and no explicit kind= override", field=tag.field_name)
    if field_type == "bool":
        return "toggle"
    if field_type == "str":
        return "string"
    if isinstance(special, (tuple, list)) and special:
        return "enum"
    return "number"


def _toggle_field(tag: WebFieldTag) -> "dict[str, Any]":
    return {"onLabel": tag.on_label or "On", "offLabel": tag.off_label or "Off"}


def _unquoted(raw: str) -> "str | None":
    # A quoted special:"<text>" value's text; None for a bare token.
    return raw[1:-1] if len(raw) > 1 and raw[0] == raw[-1] == '"' else None


def _string_special(tag: WebFieldTag, special: object, device: str, path: Path) -> "list[dict[str, Any]]":
    # The schema's sentinel (PW's "" bypasses its length bounds), labelled by the tag: the page then
    # accepts exactly what the server accepts, so a tag may label no other value.
    labels: dict[str, str] = {}
    for raw, meaning in tag.special:
        text = _unquoted(raw)
        if text is None:
            raise BuildError(device, f'{path}: @web tag for {tag.field_name!r} has special:{raw}= but a string field\'s special: value is a quoted string, e.g. special:""="..."', field=tag.field_name)
        labels[text] = meaning
    extra = sorted(set(labels) - ({special} if isinstance(special, str) else set()))
    if extra:
        raise BuildError(device, f"{path}: @web tag for {tag.field_name!r} declares special: value(s) {extra} not in its ConfigSchema", field=tag.field_name)
    if not isinstance(special, str):
        return []
    if special not in labels:
        raise BuildError(device, f'{path}: @web tag for {tag.field_name!r} has a sentinel special value {special!r} but no matching special:"{special}"="..." label', field=tag.field_name)
    return [{"value": special, "meaning": labels[special]}]


def _string_field(tag: WebFieldTag, min_v: object, max_v: object, special: object, device: str, path: Path) -> "dict[str, Any]":
    out: dict[str, Any] = {}
    if min_v is not None:
        out["minLength"] = min_v
    if max_v is not None:
        out["maxLength"] = max_v
    if tag.mask:
        out["mask"] = True
    if tag.byte_length:
        out["byteLength"] = True
    if tag.shape is not None:
        out["shape"] = tag.shape
    special_values = _string_special(tag, special, device, path)
    if special_values:
        out["specialValues"] = special_values
    return out


def _check_string_keys(tag: WebFieldTag, kind: str, device: str, path: Path) -> None:
    # web_tag checks bytes=/shape= against an explicit kind=; an inferred kind is known only here.
    if kind != "string" and (tag.byte_length or tag.shape is not None):
        raise BuildError(device, f"{path}: @web tag for {tag.field_name!r} has bytes= or shape= but its kind is {kind!r}, not string", field=tag.field_name)
    if kind != "string" and any(_unquoted(raw) is not None for raw, _meaning in tag.special):
        raise BuildError(device, f"{path}: @web tag for {tag.field_name!r} has a quoted special: value but its kind is {kind!r}; a quoted special: value labels a string field only", field=tag.field_name)


def _enum_field(tag: WebFieldTag, special: object, device: str, path: Path) -> "dict[str, Any]":
    if not isinstance(special, (tuple, list)) or not special:
        raise BuildError(device, f"{path}: @web tag for {tag.field_name!r} has kind=enum but its ConfigSchema has no discrete choice set", field=tag.field_name)
    tag_meanings = dict(tag.special)
    options: list[dict[str, Any]] = []
    for value in special:
        meaning = tag_meanings.get(str(value))
        if meaning is None:
            raise BuildError(device, f'{path}: enum field {tag.field_name!r} option {value!r} has no matching special:{value}="..." label', field=tag.field_name)
        options.append({"value": value, "label": meaning})
    extra = set(tag_meanings) - {str(v) for v in special}
    if extra:
        raise BuildError(device, f"{path}: @web tag for {tag.field_name!r} declares special: option(s) {sorted(extra)} not present in its ConfigSchema", field=tag.field_name)
    return {"options": options}


def _number_field(tag: WebFieldTag, field_type: "str | None", min_v: object, max_v: object, special: object, device: str, path: Path) -> "dict[str, Any]":
    out: dict[str, Any] = {}
    if min_v is not None:
        out["min"] = min_v
    if max_v is not None:
        out["max"] = max_v
    if field_type == "float":
        out["float"] = True
    if special is not None and not isinstance(special, (tuple, list)):
        # A schema-declared sentinel bypass (e.g. AmbPres=0, outside the field's normal min/max
        # range) - the tag must document its meaning; nothing else may claim it.
        meaning = dict(tag.special).get(str(special))
        if meaning is None:
            raise BuildError(device, f'{path}: @web tag for {tag.field_name!r} has a sentinel special value {special!r} but no matching special:{special}="..." label', field=tag.field_name)
        out["specialValues"] = [{"value": special, "meaning": meaning}]
    elif tag.special:
        # No schema-declared sentinel, but the tag documents one or more values anyway (e.g.
        # ISL29125's AutoRangeDwell=0.0 - a perfectly ordinary in-range value that also has a special UI
        # meaning, never a bypass asy_config_manager.py's own validation needs to know about).
        out["specialValues"] = [{"value": _coerce_special_value(raw, field_type), "meaning": meaning} for raw, meaning in tag.special]
    return out


def _build_field_def(tag: WebFieldTag, schema: "FieldSchema | None", device: str, path: Path) -> "dict[str, Any]":
    out: dict[str, Any] = {"key": tag.field_name, "label": tag.label}
    if tag.unit:
        out["unit"] = tag.unit

    raw_type, _default, min_v, max_v, special = schema if schema is not None else (None, None, None, None, None)
    field_type = raw_type if isinstance(raw_type, str) else None
    kind = _infer_kind(tag, field_type, special, device, path)
    out["kind"] = kind
    _check_string_keys(tag, kind, device, path)

    if kind == "toggle":
        out.update(_toggle_field(tag))
    elif kind == "string":
        out.update(_string_field(tag, min_v, max_v, special, device, path))
    elif kind == "enum":
        out.update(_enum_field(tag, special, device, path))
    elif kind == "number":
        out.update(_number_field(tag, field_type, min_v, max_v, special, device, path))
    elif kind == "readonly" and tag.special:
        # A readonly value's documented specials (e.g. SGP40's BackupTS: null and 0), shown as text.
        out["specialValues"] = [{"value": _coerce_readonly_special(raw), "meaning": meaning} for raw, meaning in tag.special]

    if tag.description:
        out["description"] = tag.description
    if tag.dispatch:
        out["dispatch"] = True
    if tag.always_executed:
        out["alwaysExecuted"] = True
    if tag.default_value is not None:
        out["defaultValue"] = tag.default_value
    if tag.path is not None:
        out["path"] = list(tag.path)
    if tag.decimals is not None:
        out["decimals"] = tag.decimals
    if tag.format is not None:
        out["format"] = tag.format
    if tag.codes is not None:
        out["codes"] = _status_codes(tag.codes, device, tag.field_name)
    return out


def _fields_for(tags: _DriverTags, section: str, submit_group: str, device: str, path: Path) -> "list[dict[str, Any]]":
    return [
        _build_field_def(t, tags.schemas.get(t.field_name), device, path)
        for t in tags.field_tags
        if t.section == section and t.submit_group == submit_group
    ]


def _group_shell(group_tag: WebGroupTag, *, key: str, label: str) -> "dict[str, Any]":
    out: dict[str, Any] = {"key": key, "label": label}
    if group_tag.submit:
        out["submit"] = True
    if group_tag.submit_label:
        out["submitLabel"] = group_tag.submit_label
    return out


def _resolved_key(spec: InstanceSpec, device: str) -> str:
    if spec.resolved_name is None:
        raise BuildError(device, "internal: resolved_name unresolved before definitions generation", instance=spec.label)
    return spec.resolved_name


def _instance_group(spec: InstanceSpec, section: str, tags: _DriverTags, path: Path, device: str) -> "dict[str, Any] | None":
    group_tag = next((g for g in tags.group_tags if g.section == section and g.submit_group == SELF_GROUP), None)
    if group_tag is None:
        return None
    label = group_tag.label if not spec.name_ext else f"{group_tag.label} ({spec.name_ext})"
    out = _group_shell(group_tag, key=_resolved_key(spec, device), label=label)
    out["fields"] = _fields_for(tags, section, SELF_GROUP, device, path)
    return out


def _mandatory_group(section: str, submit_group: str, key: str, tags_list: "list[tuple[_DriverTags, Path]]", device: str) -> "dict[str, Any]":
    declaring = [t for t, _p in tags_list for g in t.group_tags if g.section == section and g.submit_group == submit_group]
    if len(declaring) == 0:
        raise BuildError(device, f"no @web-group tag declares section={section!r} submitGroup={submit_group!r} in any scanned file")
    if len(declaring) > 1:
        raise BuildError(device, f"more than one @web-group tag declares section={section!r} submitGroup={submit_group!r}")
    group_tag = next(g for g in declaring[0].group_tags if g.section == section and g.submit_group == submit_group)
    out = _group_shell(group_tag, key=key, label=group_tag.label)
    fields: list[dict[str, Any]] = []
    for t, p in tags_list:
        fields.extend(_fields_for(t, section, submit_group, device, p))
    if not fields:
        raise BuildError(device, f"section={section!r} submitGroup={submit_group!r} has an @web-group declaration but no @web field tags reference it")
    out["fields"] = fields
    return out


def _sensor_instance_specs(model: DeviceModel) -> "list[InstanceSpec]":
    # Cards follow the construction order (buildgen.graph); a model that skipped the graph fails here
    # rather than falling back to TOML order, so the CLI and the build can never disagree.
    order = {node: i for i, node in enumerate(model.construction_order)}
    specs = [spec for spec in model.instances.values() if spec.driver in _SENSOR_DRIVERS]
    for spec in specs:
        if spec.key not in order:
            raise BuildError(model.device, "internal: construction order unresolved before definitions generation", instance=spec.label)
    return sorted(specs, key=lambda spec: order[spec.key])


def _notification_spec(model: DeviceModel) -> "InstanceSpec | None":
    return next((spec for spec in model.instances.values() if spec.driver == "notification"), None)


def _measurements_and_sensors_sections(model: DeviceModel, cache: "dict[Path, _DriverTags]") -> "tuple[dict[str, Any], dict[str, Any]]":
    measurements = dict(_SECTION_SKELETON[0])
    sensors = dict(_SECTION_SKELETON[1])
    m_groups: list[dict[str, Any]] = []
    s_groups: list[dict[str, Any]] = []
    for spec in _sensor_instance_specs(model):
        if spec.driver_info is None:
            raise BuildError(model.device, "internal: driver_info unresolved before definitions generation", instance=spec.label)
        path = spec.driver_info.source_path
        tags = _load_driver_tags(cache, path, model.device, spec.label)
        m_group = _instance_group(spec, "measurements", tags, path, model.device)
        s_group = _instance_group(spec, "sensors", tags, path, model.device)
        if m_group is None:
            raise BuildError(model.device, f"{path}: no @web-group section=measurements submitGroup=self tag found", instance=spec.label)
        if s_group is None:
            raise BuildError(model.device, f"{path}: no @web-group section=sensors submitGroup=self tag found", instance=spec.label)
        m_groups.append(m_group)
        s_groups.append(s_group)
    measurements["groups"] = m_groups
    sensors["groups"] = s_groups
    return measurements, sensors


def _networking_section(src_dir: Path, device: str, cache: "dict[Path, _DriverTags]", have: "set[str]") -> "dict[str, Any]":
    wifi_path = src_dir / "asy_wifi_service.py"
    ntp_path = src_dir / "asy_ntp_client.py"
    wifi_tags = _load_driver_tags(cache, wifi_path, device, "wifi")
    ntp_tags = _load_driver_tags(cache, ntp_path, device, "ntp")
    section = dict(_SECTION_SKELETON[2])
    dns_label = next(label for key, label, _has_cfgmgr in _ERRCOUNT_CATALOG if key == "dns")
    groups = [
        _mandatory_group("networking", "identity", "identity", [(wifi_tags, wifi_path)], device),
        _mandatory_group("networking", "wifiLed", "wifiLed", [(wifi_tags, wifi_path)], device),
        _mandatory_group("networking", "ntp", "ntp", [(ntp_tags, ntp_path)], device),
        _mandatory_group("networking", "dns", "dns", [(ntp_tags, ntp_path)], device),
    ]
    if "mqtt" in have:  # a singleton service: its group key is the literal "mqtt"
        mqtt_path = src_dir / "asy_mqtt_client.py"
        groups.append(_mandatory_group("networking", "mqtt", "mqtt", [(_load_driver_tags(cache, mqtt_path, device, "mqtt"), mqtt_path)], device))
    # The captive DNS server's history is shown with the networking data (owner, 2026-09-26).
    groups.append(_errcount_shell("dnsErrors", "Captive DNS Error History", [{"key": _ERRCOUNT_NAME["dns"], "label": dns_label}], _load_catalog()))
    section["groups"] = groups
    return section


def _system_section(src_dir: Path, device: str, cache: "dict[Path, _DriverTags]") -> "dict[str, Any]":
    system_path = src_dir / "asy_system_service.py"
    ntp_path = src_dir / "asy_ntp_client.py"
    system_tags = _load_driver_tags(cache, system_path, device, "system")
    ntp_tags = _load_driver_tags(cache, ntp_path, device, "ntp")
    section = dict(_SECTION_SKELETON[3])
    section["groups"] = [
        _mandatory_group("system", "settings", "settings", [(system_tags, system_path), (ntp_tags, ntp_path)], device),
        dict(_SYSTEM_COMMAND_GROUP),
        dict(_BUILD_GROUP),
    ]
    return section


def _suffixed(label: str, name_ext: str) -> str:
    return label if not name_ext else f"{label} ({_NAME_EXT_LABEL.get(name_ext, name_ext)})"


def _errcount_shell(key: str, label: str, modules: "list[dict[str, str]]", catalog: "dict[str, Any]") -> "dict[str, Any]":
    # Every errcount group carries the same code-description block, so no two groups can differ.
    return {"key": key, "label": label, "kind": "errcount", "modules": modules, "codes": _errcount_codes(catalog)}


def _errcount_group(model: DeviceModel, catalog: "dict[str, Any]") -> "dict[str, Any]":
    # Keyed per logger INSTANCE, as the API publishes them: scd30_primary publishes
    # SCD30_primary and CFGMGR_SCD30_primary and needs a row under each. A kind-keyed catalog
    # drifts silently both ways - a missing source vanishes, a stale row renders a permanent 0.
    modules: list[dict[str, str]] = []
    by_driver: dict[str, list[InstanceSpec]] = {}
    for spec in model.instances.values():
        by_driver.setdefault(spec.driver, []).append(spec)
    # Catalog order is display order, each row keyed by resolved_name; the webserver's row is the
    # group's last entry (a UART row lands between notification and it), and dns is on Networking.
    for key, label, has_cfgmgr in _ERRCOUNT_CATALOG:
        if key in ("webserver", "dns"):
            continue
        if key in _MANDATORY_ERRCOUNT_KEYS:
            # wifi/dns/ntp/system are mandatory infrastructure, never [[instance]] - one logger each,
            # with a fixed name no device can vary.
            modules.append({"key": _ERRCOUNT_NAME[key], "label": label})
            if has_cfgmgr:
                modules.append({"key": f"CFGMGR_{_ERRCOUNT_NAME[key]}", "label": _CFGMGR_LABEL[key]})
            continue
        for spec in by_driver.get(key, []):  # TOML declaration order, so two instances read in the order written
            name = _resolved_key(spec, model.device)
            modules.append({"key": name, "label": _suffixed(label, spec.name_ext)})
            if has_cfgmgr:
                modules.append({"key": f"CFGMGR_{name}", "label": _suffixed(_CFGMGR_LABEL[key], spec.name_ext)})
    webserver_label = next(label for key, label, _has_cfgmgr in _ERRCOUNT_CATALOG if key == "webserver")
    modules.append({"key": _ERRCOUNT_NAME["webserver"], "label": webserver_label})
    return _errcount_shell("errcount", "Error Counts & History", modules, catalog)


def _sgp40_maintenance_fields(model: DeviceModel, cache: "dict[Path, _DriverTags]") -> "list[dict[str, Any]]":
    # Built from the SGP40 driver's own section=status tags, one set per instance in construction
    # order; keyed as GET /status flattens them (<resolved_name>_<field>), labelled like its card.
    out: list[dict[str, Any]] = []
    for spec in (s for s in _sensor_instance_specs(model) if s.driver == "sgp40"):
        if spec.driver_info is None:
            raise BuildError(model.device, "internal: driver_info unresolved before definitions generation", instance=spec.label)
        path = spec.driver_info.source_path
        tags = _load_driver_tags(cache, path, model.device, spec.label)
        fields = _fields_for(tags, "status", "maintenance", model.device, path)
        if not fields:
            raise BuildError(model.device, f"{path}: no @web section=status submitGroup=maintenance tag found", instance=spec.label)
        for field in fields:
            field["key"] = f"{_resolved_key(spec, model.device)}_{field['key']}"
            if spec.name_ext:
                field["label"] = f"{field['label']} ({spec.name_ext})"
        out += fields
    return out


def _status_section(model: DeviceModel, have: "set[str]", cache: "dict[Path, _DriverTags]") -> "dict[str, Any]":
    section = dict(_SECTION_SKELETON[4])
    networking_fields = [
        {"key": "Mode", "label": "Wi-Fi Mode", "kind": "readonly"},
        {"key": "Connected", "label": "Connected", "kind": "readonly", "description": "True while the Wi-Fi link is up, hotspot included."},
        {"key": "IPv4", "label": "IPv4 Address", "kind": "readonly"},
        {"key": "Subnet", "label": "Subnet Mask", "kind": "readonly"},
        {"key": "Gateway", "label": "Gateway", "kind": "readonly"},
        {"key": "DNS", "label": "Name Server", "kind": "readonly"},
        {"key": "RSSI", "label": "Wi-Fi RSSI", "unit": "dBm", "kind": "readonly"},
        {"key": "WifiUptime", "label": "Wi-Fi Uptime", "unit": "s", "kind": "readonly", "description": "Seconds the Wi-Fi link has been up, hotspot included; 0 while it is down."},
        {"key": "WifiTS", "label": "Wi-Fi Status Time", "kind": "readonly", "format": "epoch"},
        {"key": "NTPSynced", "label": "NTP Synced", "kind": "readonly"},
        {"key": "NTPLastSyncAge", "label": "NTP Last Sync Age", "unit": "s", "kind": "readonly"},
        {"key": "NTPLastSync", "label": "NTP Last Sync Time", "kind": "readonly", "format": "epoch", "description": "Unix timestamp of the last successful sync."},
        {"key": "HTTPDropped", "label": "Dropped Connections", "kind": "readonly", "description": "Web connections dropped in the last 24 hours, hourly resolution."},
    ]
    if "mqtt" in have:
        networking_fields += [dict(field) for field in _MQTT_STATUS_FIELDS]
    system_fields = [
        {"key": "SysUptime", "label": "System Uptime", "unit": "s", "kind": "readonly"},
        {
            "key": "BootSignature", "label": "Boot Signature", "kind": "readonly",
            "description": "Opaque value, stable for the running boot session; a different value on a later poll means the device rebooted. Not a human-readable code.",
        },
    ]
    if "fram" in have:
        system_fields.append({"key": "MemPaused", "label": "Backups Paused", "kind": "readonly"})
    system_fields += [
        {"key": "LocalTime", "label": "Local Time", "kind": "readonly", "format": "gmtimestruct"},
        {"key": "UTCTime", "label": "UTC Time", "kind": "readonly", "format": "gmtimestruct"},
    ]
    groups = [
        {"key": "networking", "label": "Networking Status", "fields": networking_fields},
        {"key": "system", "label": "System Status", "fields": system_fields},
    ]
    # "Sensor Maintenance": one group, its fields built additively from whichever maintenance-status
    # sources this device actually has (matches codegen._emit_webserver()'s own additive
    # maintenance_sensors= tuple) - never a per-driver group of its own, both here and there.
    maintenance_fields: list[dict[str, Any]] = []
    if "sgp40" in have:
        maintenance_fields += _sgp40_maintenance_fields(model, cache)
    if "uart_link" in have:
        uart = MAINTENANCE_NAMES["uart_link"]
        maintenance_fields += [
            {
                "key": f"{uart}_Transfers", "label": "UART Link Transfers", "kind": "readonly",
                "description": "Completed transfers across this bench rig's UART0<->UART1 crossover jumper since boot. Bench-only - a deployed unit has no such link.",
            },
            {
                "key": f"{uart}_Failures", "label": "UART Link Failures", "kind": "readonly",
                "description": "Transfers that did not complete across the crossover jumper since boot.",
            },
        ]
    if maintenance_fields:
        groups.append({"key": "sensors", "label": "Sensor Maintenance", "fields": maintenance_fields})
    if "notification" in have:
        groups.append({"key": "notification", "label": "Notification Status", "fields": [
            {"key": "Triggered", "label": "Currently Triggered", "kind": "readonly"},
            {"key": "TS", "label": "Last Trigger Timestamp", "kind": "readonly", "format": "epoch"},
            {"key": "PauseTime", "label": "Remaining Pause Time", "unit": "s", "kind": "readonly"},
        ]})
    groups.append(_errcount_group(model, _load_catalog()))
    groups.append(dict(_RESET_ERRORS_GROUP))
    section["groups"] = groups
    return section


def _notification_section(model: DeviceModel, cache: "dict[Path, _DriverTags]", have: "set[str]") -> "dict[str, Any] | None":
    spec = _notification_spec(model)
    if spec is None:
        return None
    if spec.driver_info is None:
        raise BuildError(model.device, "internal: driver_info unresolved before definitions generation", instance=spec.label)
    path = spec.driver_info.source_path
    tags = _load_driver_tags(cache, path, model.device, spec.label)
    # Literal "autoConfig" key, not spec.resolved_name: NotificationService is a singleton
    # service (driver_registry.SERVICE_DRIVERS), so there is no multi-instance disambiguation need
    # the way scd30/sgp40/bmp3xx have.
    auto_group = _mandatory_group("notification", "autoConfig", "autoConfig", [(tags, path)], model.device)
    # Catalog order is display order, never the TOML's own [instance.wiring] key order.
    warn_fields = [dict(_WARN_SIGNAL_WEB_CATALOG[key]) for key in _WARN_SIGNAL_WEB_CATALOG if key in spec.wiring]
    auto_group["fields"] = auto_group["fields"] + warn_fields

    groups = [auto_group]
    if "neopixel" in have:
        groups.append(dict(_NOTIFICATION_FLASH_GROUP))
    groups.append(dict(_NOTIFICATION_PAUSE_GROUP))
    section = dict(_NOTIFICATION_SECTION_SKELETON)
    section["groups"] = groups
    return section


def generate_definitions(model: DeviceModel, src_dir: Path) -> "dict[str, Any]":
    # The full `definitions.json`-shaped dict for `model` (already `buildgen.validate.build_model()`-
    # validated). Every scanned `@web`/`@web-group` tag is re-parsed once per distinct source path
    # (`_DriverTags` cache), regardless of how many instances/sections reference it.
    have = {spec.driver for spec in model.instances.values()}
    cache: dict[Path, _DriverTags] = {}

    measurements, sensors = _measurements_and_sensors_sections(model, cache)
    sections = [
        measurements,
        sensors,
        _networking_section(src_dir, model.device, cache, have),
        _system_section(src_dir, model.device, cache),
        _status_section(model, have, cache),
    ]
    notification = _notification_section(model, cache, have)
    if notification is not None:
        sections.append(notification)

    return {
        "schemaVersion": SCHEMA_VERSION,
        "websiteVersion": WEBSITE_VERSION,
        "device": {"id": model.device, "displayName": model.device},
        "landingSection": "measurements",
        "defaultPollIntervalMs": _POLL_INTERVAL_MS,
        "sections": sections,
    }


def definitions_for_toml(toml_path: Path, src_dir: Path) -> "dict[str, Any]":
    # The one entry point from a device TOML to its definitions: validated model, construction
    # order (`buildgen.graph`), then `generate_definitions()` - every caller gets the build's order.
    model = build_model(toml_path, src_dir)
    build_construction_order(model)
    return generate_definitions(model, src_dir)


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a device's website definitions.json from its device TOML.")
    parser.add_argument("device_toml", type=Path)
    parser.add_argument("--src-dir", type=Path, default=REPO_ROOT / "src")
    parser.add_argument("--out", type=Path, default=None, help="write definitions.json here instead of printing to stdout")
    args = parser.parse_args(argv)

    try:
        definitions = definitions_for_toml(args.device_toml, args.src_dir)
    except BuildError as e:
        print(f"buildgen: {e}", file=sys.stderr)
        return 1

    text = json.dumps(definitions, indent=2)
    if args.out is None:
        print(text)
    else:
        args.out.write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
