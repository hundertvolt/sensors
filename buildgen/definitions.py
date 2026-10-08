"""Generates a device's website `definitions.json` (SPECIFICATION.md Part H.5) from a validated
`DeviceModel` plus the `# @web`/`# @web-group` tags on the `src/` files that own each field/group
(`buildgen.web_tag`; design rationale: Part H.5.1). CLI at the bottom: manual use + `build_website.sh`."""

import argparse
import contextlib
import functools
import json
import os
import sys
from pathlib import Path
from typing import NotRequired, TypedDict

from buildgen.driver_registry import DriverInfo, parse_name_constant
from buildgen.errors import BuildError, BuildInternalError
from buildgen.graph import build_construction_order
from buildgen.jsontypes import JsonDict, JsonValue
from buildgen.model import MAINTENANCE_NAMES, DeviceModel, InstanceSpec
from buildgen.schema_ast import FieldSchema, extract_field_schemas
from buildgen.signals import WARN_SIGNALS, WarnSignal
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
_SECTION_SKELETON: "tuple[JsonDict, ...]" = (
    {"key": "measurements", "label": "Measurements", "description": "Live sensor readings, refreshed automatically.", "rest": {"get": "/measurements"}, "pollGroup": "live"},
    {"key": "sensors", "label": "Sensors", "description": "Per-sensor configuration. Each card applies independently.", "rest": {"get": "/sensors", "put": "/sensors"}, "pollGroup": "settings"},
    {"key": "networking", "label": "Networking", "description": "Wi-Fi credentials, identity, and NTP time sync. Live status (IP, RSSI, uptime, sync age) is on the Status page.", "rest": {"get": "/networking", "put": "/networking"}, "pollGroup": "settings"},
    {"key": "system", "label": "System", "rest": {"get": "/system", "put": "/system"}, "pollGroup": "settings"},
    {"key": "status", "label": "Status", "description": "Live system/network/error state. Error counts are always visible; click a module to see its history.", "rest": {"get": "/status", "put": "/status"}, "pollGroup": "live", "pollIntervalMs": _POLL_INTERVAL_MS},
)
_NOTIFICATION_SECTION_SKELETON: JsonDict = {
    "key": "notification", "label": "Notification", "rest": {"get": "/notification", "put": "/notification"}, "pollGroup": "settings",
}

# Dispatch-only webserver-level fields: no per-device variation and no single owning driver file
# (Part H.5.1), each flagged dispatch so the never-"Unchanged" class reads from definitions alone.
# Sources in asy_webserver_service.py: _dispatch_notification_led(), _SYSTEM_CMDS, PauseTime's field.
_SYSTEM_COMMAND_GROUP: JsonDict = {
    "key": "command", "label": "System Command", "submit": True,
    "fields": [{"key": "SystemCmd", "label": "Command", "kind": "enum", "dispatch": True, "options": [
        {"value": "reboot", "label": "Reboot"},
        {"value": "bootloader", "label": "Reboot into bootloader"},
        {"value": "mempause", "label": "Pause backups for 5 minutes"},
        {"value": "resetconfig", "label": "Reset to defaults"},
        {"value": "erasefram", "label": "Erase FRAM"},
    ]}],
}
_NOTIFICATION_FLASH_GROUP: JsonDict = {
    "key": "flash", "label": "Manual Flash Command", "submit": True, "submitLabel": "Flash LED",
    "fields": [{"key": "LightCmdLED", "label": "LED Flash", "kind": "composite", "dispatch": True, "subFields": [
        {"key": "R", "label": "Red", "kind": "number", "min": 0, "max": 255},
        {"key": "G", "label": "Green", "kind": "number", "min": 0, "max": 255},
        {"key": "B", "label": "Blue", "kind": "number", "min": 0, "max": 255},
        {"key": "T", "label": "Time (s)", "kind": "number", "min": 0.5, "max": 60.0, "float": True},
    ]}],
}
_NOTIFICATION_PAUSE_GROUP: JsonDict = {
    "key": "pause", "label": "Pause Notifications", "submit": True,
    "fields": [{
        "key": "PauseTime", "label": "Pause Time", "unit": "s", "kind": "number", "min": 0, "max": 3600,
        "description": "Temporarily suppress automatic LED notifications. Current value is live (from Status).", "dispatch": True,
    }],
}
_RESET_ERRORS_GROUP: JsonDict = {
    "key": "resetErrors", "label": "Reset Errors", "submit": True, "submitLabel": "Reset All Errors",
    "fields": [{
        "key": "ResetErrors", "label": "Confirm Reset", "kind": "toggle", "onLabel": "Yes, reset", "offLabel": "No",
        "description": "Resets every module's error counter and history in one call. Absent/No is a no-op.", "dispatch": True,
    }],
}

# GET /system's nested "build" entry (codegen's build_info), shown read-only through each field's path.
_BUILD_GROUP: JsonDict = {
    "key": "build", "label": "Build",
    "fields": [
        {"key": "FirmwareVersion", "label": "Firmware Version", "kind": "readonly", "path": ["build", "FirmwareVersion"]},
        {"key": "WebsiteVersion", "label": "Website Version", "kind": "readonly", "path": ["build", "WebsiteVersion"]},
        {"key": "BuildDate", "label": "Build Date", "kind": "readonly", "path": ["build", "BuildDate"]},
    ],
}

# Errcount module catalog (H.6): (have-key, label, has_cfgmgr_companion) rows. A have-key is an
# instance's own `driver` string, plus the five mandatory keys that are never [[instance]]
# entries. Generator-owned like the catalogs above: cosmetic labels, owned by no source file.
_ERRCOUNT_CATALOG: "tuple[tuple[str, str, bool], ...]" = (
    ("wifi", "Wi-Fi", True),
    ("dns", "Captive DNS", False),
    ("ntp", "NTP Client", True),
    ("fram", "FRAM Storage", False),
    ("system", "System", True),
    ("scd30", "SCD30", True),  # (H.6) a CFGMGR_ companion for the three FRC settings
    ("sgp40", "SGP40", True),
    ("bmp3xx", "BMP3xx", True),
    ("isl29125", "ISL29125", True),
    ("neopixel", "Neopixel LED", False),
    ("notification", "Notification Service", True),
    ("uart_link", "UART Link", False),  # no CFGMGR_ companion: UARTComm has no config schema - its
    # parameters are an out-of-band two-implementation wire contract, never runtime-writable (Part J.6)
    ("webserver", "Web Server", False),
)
# The mandatory modules' files: each one's logger name is its own `_NAME`, read from the file.
_MANDATORY_ERRCOUNT_FILES: "dict[str, str]" = {
    "wifi": "asy_wifi_service.py", "dns": "asy_captive_dns.py", "ntp": "asy_ntp_client.py",
    "system": "asy_system_service.py", "webserver": "asy_webserver_service.py",
}
# Display names for the name_ext values a multi-instance driver carries, where the raw suffix is an
# abbreviation. Anything absent renders as the raw name_ext, which is what a device author typed.
_NAME_EXT_LABEL: "dict[str, str]" = {"init": "Initiator", "resp": "Responder"}
_CFGMGR_LABEL: "dict[str, str]" = {
    "wifi": "Wi-Fi Config Store", "ntp": "NTP Config Store", "system": "System Config Store",
    "scd30": "SCD30 Config Store", "sgp40": "SGP40 Config Store", "bmp3xx": "BMP3xx Config Store", "isl29125": "ISL29125 Config Store",
    "notification": "Notification Config Store",
}


class _CodeRow(TypedDict):
    text: str
    retired: NotRequired[bool]


class _StatusRow(TypedDict):
    text: str


class _Catalog(TypedDict):
    # The two parts of the catalog the definitions inline; tests_scripts/test_error_catalog.py checks the whole file.
    codes: dict[str, dict[str, _CodeRow]]
    status: dict[str, dict[str, _StatusRow]]


@functools.cache
def _load_catalog() -> _Catalog:
    # Read once per process; every caller only reads it.
    catalog: _Catalog = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    return catalog


def _status_codes(table: str, device: str, field: str) -> JsonDict:
    # A readonly field's codes=<table>, inlined as {"<n>": "<text>"} from the catalog's status section.
    tables = _load_catalog().get("status", {})
    if table not in tables:
        raise BuildError(
            device, f"codes={table!r} names no status table in {_CATALOG_PATH.name} (tables: {sorted(tables)})", field=field,
            rule="web.codes-unknown-table", fix=f"name one of the catalog's status tables, or add a {table!r} table to buildgen/{_CATALOG_PATH.name}",
        )
    return {num: row["text"] for num, row in tables[table].items()}


def _errcount_codes(catalog: _Catalog) -> JsonDict:
    # Every non-retired errno/wrnno: numbers are global, so one table serves every errcount row.
    codes: JsonDict = {}
    for kind in ("E", "W"):
        texts: JsonDict = {num: row["text"] for num, row in catalog["codes"][kind].items() if not row.get("retired")}
        codes[kind] = texts
    return codes


class _DriverTags:
    # Parsed `@web`/`@web-group` tags plus real `ConfigSchema` literals for one source file, parsed once
    # per file however many instances scan it. Every schema field carries a @web tag, hidden= included.

    def __init__(self, path: Path, device: str, instance_label: str) -> None:
        self.field_tags: tuple[WebFieldTag, ...] = parse_web_tags(path, device, instance_label)
        self.group_tags: tuple[WebGroupTag, ...] = parse_web_group_tags(path, device, instance_label)
        self.schemas: dict[str, FieldSchema] = extract_field_schemas(path, device=device, instance_label=instance_label)
        untagged = sorted(set(self.schemas) - {tag.field_name for tag in self.field_tags})
        if untagged:
            raise BuildError(
                device, f"{path}: schema field(s) {untagged} have no @web tag", instance=instance_label, field=untagged[0],
                rule="web.schema-field-untagged", fix='add a # @web tag for each, or # @web <Field> hidden="<why>" to keep one off the website',
            )


def _load_driver_tags(cache: "dict[Path, _DriverTags]", path: Path, device: str, instance_label: str) -> _DriverTags:
    if path not in cache:
        cache[path] = _DriverTags(path, device, instance_label)
    return cache[path]


def _json_literal(value: object, device: str, path: Path, field: str) -> JsonValue:
    # A schema value as the JSON the page reads (a tuple as a list); one with no JSON form fails here,
    # rather than as a TypeError while the file is written.
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, tuple):
        return [_json_literal(item, device, path, field) for item in value]
    raise BuildError(
        device, f"{path}: the schema of {field!r} holds {value!r}, which has no JSON form", field=field,
        rule="schema.value-not-json", fix="write the schema's values as numbers, strings, booleans, None or tuples of them",
    )


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
        raise BuildError(
            device, f"{path}: @web tag for {tag.field_name!r} has no matching ConfigSchema constant and no explicit kind= override", field=tag.field_name,
            rule="web.kind-unresolved", fix="add kind=<readonly|number|string|enum|toggle> to the tag, or declare the field's schema constant",
        )
    if field_type == "bool":
        return "toggle"
    if field_type == "str":
        return "string"
    if isinstance(special, (tuple, list)) and special:
        return "enum"
    return "number"


def _toggle_field(tag: WebFieldTag) -> JsonDict:
    return {"onLabel": tag.on_label or "On", "offLabel": tag.off_label or "Off"}


def _unquoted(raw: str) -> "str | None":
    # A quoted special:"<text>" value's text; None for a bare token.
    return raw[1:-1] if len(raw) > 1 and raw[0] == raw[-1] == '"' else None


def _string_special(tag: WebFieldTag, special: object, device: str, path: Path) -> "list[JsonValue]":
    # The schema's sentinel (PW's "" bypasses its length bounds), labelled by the tag: the page then
    # accepts exactly what the server accepts, so a tag may label no other value.
    labels: dict[str, str] = {}
    for raw, meaning in tag.special:
        text = _unquoted(raw)
        if text is None:
            raise BuildError(
                device, f'{path}: @web tag for {tag.field_name!r} has special:{raw}= but a string field\'s special: value is a quoted string, e.g. special:""="..."', field=tag.field_name,
                rule="web.string-special-unquoted", fix=f'quote the value: special:"{raw}"="{meaning}"',
            )
        labels[text] = meaning
    extra = sorted(set(labels) - ({special} if isinstance(special, str) else set()))
    if extra:
        raise BuildError(
            device, f"{path}: @web tag for {tag.field_name!r} declares special: value(s) {extra} not in its ConfigSchema", field=tag.field_name,
            rule="web.special-not-in-schema", fix="remove the special: entries the field's schema does not declare",
        )
    if not isinstance(special, str):
        return []
    if special not in labels:
        raise BuildError(
            device, f'{path}: @web tag for {tag.field_name!r} has a sentinel special value {special!r} but no matching special:"{special}"="..." label', field=tag.field_name,
            rule="web.special-unlabelled", fix=f'add special:"{special}"="<meaning>" to the tag',
        )
    return [{"value": special, "meaning": labels[special]}]


def _string_field(tag: WebFieldTag, min_v: object, max_v: object, special: object, device: str, path: Path) -> JsonDict:
    out: JsonDict = {}
    if min_v is not None:
        out["minLength"] = _json_literal(min_v, device, path, tag.field_name)
    if max_v is not None:
        out["maxLength"] = _json_literal(max_v, device, path, tag.field_name)
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
        raise BuildError(
            device, f"{path}: @web tag for {tag.field_name!r} has bytes= or shape= but its kind is {kind!r}, not string", field=tag.field_name,
            rule="web.string-key-off-string", fix="drop bytes= and shape= from the tag, or make the field a string",
        )
    if kind != "string" and any(_unquoted(raw) is not None for raw, _meaning in tag.special):
        raise BuildError(
            device, f"{path}: @web tag for {tag.field_name!r} has a quoted special: value but its kind is {kind!r}; a quoted special: value labels a string field only", field=tag.field_name,
            rule="web.quoted-special-off-string", fix="write the special: value unquoted, in the field's own type",
        )


def _enum_field(tag: WebFieldTag, special: object, device: str, path: Path) -> JsonDict:
    if not isinstance(special, (tuple, list)) or not special:
        raise BuildError(
            device, f"{path}: @web tag for {tag.field_name!r} has kind=enum but its ConfigSchema has no discrete choice set", field=tag.field_name,
            rule="web.enum-without-choices", fix="give the field's schema a tuple of choices in its special slot, or drop kind=enum",
        )
    tag_meanings = dict(tag.special)
    options: list[JsonValue] = []
    for value in special:
        meaning = tag_meanings.get(str(value))
        if meaning is None:
            raise BuildError(
                device, f'{path}: enum field {tag.field_name!r} option {value!r} has no matching special:{value}="..." label', field=tag.field_name,
                rule="web.special-unlabelled", fix=f'add special:{value}="<label>" to the tag',
            )
        options.append({"value": _json_literal(value, device, path, tag.field_name), "label": meaning})
    extra = set(tag_meanings) - {str(v) for v in special}
    if extra:
        raise BuildError(
            device, f"{path}: @web tag for {tag.field_name!r} declares special: option(s) {sorted(extra)} not present in its ConfigSchema", field=tag.field_name,
            rule="web.special-not-in-schema", fix="remove the special: entries the field's schema does not declare",
        )
    return {"options": options}


def _number_field(tag: WebFieldTag, field_type: "str | None", min_v: object, max_v: object, special: object, device: str, path: Path) -> JsonDict:
    out: JsonDict = {}
    if min_v is not None:
        out["min"] = _json_literal(min_v, device, path, tag.field_name)
    if max_v is not None:
        out["max"] = _json_literal(max_v, device, path, tag.field_name)
    if field_type == "float":
        out["float"] = True
    if special is not None and not isinstance(special, (tuple, list)):
        # A schema-declared sentinel bypass (e.g. AmbPres=0, outside the field's normal min/max
        # range) - the tag must document its meaning; nothing else may claim it.
        meaning = dict(tag.special).get(str(special))
        if meaning is None:
            raise BuildError(
                device, f'{path}: @web tag for {tag.field_name!r} has a sentinel special value {special!r} but no matching special:{special}="..." label', field=tag.field_name,
                rule="web.special-unlabelled", fix=f'add special:{special}="<meaning>" to the tag',
            )
        out["specialValues"] = [{"value": _json_literal(special, device, path, tag.field_name), "meaning": meaning}]
    elif tag.special:
        # No schema-declared sentinel, but the tag documents one or more values anyway (e.g.
        # ISL29125's AutoRangeDwell=0.0 - a perfectly ordinary in-range value that also has a special UI
        # meaning, never a bypass asy_config_manager.py's own validation needs to know about).
        values: list[JsonValue] = [{"value": _coerce_special_value(raw, field_type), "meaning": meaning} for raw, meaning in tag.special]
        out["specialValues"] = values
    return out


def _build_field_def(tag: WebFieldTag, schema: "FieldSchema | None", device: str, path: Path) -> JsonDict:
    out: JsonDict = {"key": tag.field_name, "label": tag.label}
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
        values: list[JsonValue] = [{"value": _coerce_readonly_special(raw), "meaning": meaning} for raw, meaning in tag.special]
        out["specialValues"] = values

    if tag.description:
        out["description"] = tag.description
    if tag.dispatch:
        out["dispatch"] = True
    if tag.always_executed:
        out["alwaysExecuted"] = True
    if tag.default_value is not None:
        out["defaultValue"] = tag.default_value
    if tag.path is not None:
        path_keys: list[JsonValue] = list(tag.path)
        out["path"] = path_keys
    if tag.decimals is not None:
        out["decimals"] = tag.decimals
    if tag.format is not None:
        out["format"] = tag.format
    if tag.codes is not None:
        out["codes"] = _status_codes(tag.codes, device, tag.field_name)
    return out


def _fields_for(tags: _DriverTags, section: str, submit_group: str, device: str, path: Path) -> "list[JsonValue]":
    return [
        _build_field_def(t, tags.schemas.get(t.field_name), device, path)
        for t in tags.field_tags
        if t.hidden is None and t.section == section and t.submit_group == submit_group
    ]


def _group_shell(group_tag: WebGroupTag, *, key: str, label: str) -> JsonDict:
    out: JsonDict = {"key": key, "label": label}
    if group_tag.submit:
        out["submit"] = True
    if group_tag.submit_label:
        out["submitLabel"] = group_tag.submit_label
    return out


def _resolved_key(spec: InstanceSpec, device: str) -> str:
    if spec.resolved_name is None:
        raise BuildInternalError(f"[{device}/{spec.label}] resolved_name unresolved before definitions generation")
    return spec.resolved_name


def _instance_group(spec: InstanceSpec, section: str, tags: _DriverTags, path: Path, device: str) -> "JsonDict | None":
    group_tag = next((g for g in tags.group_tags if g.section == section and g.submit_group == SELF_GROUP), None)
    if group_tag is None:
        return None
    label = group_tag.label if not spec.name_ext else f"{group_tag.label} ({spec.name_ext})"
    out = _group_shell(group_tag, key=_resolved_key(spec, device), label=label)
    out["fields"] = _fields_for(tags, section, SELF_GROUP, device, path)
    return out


def _mandatory_group(section: str, submit_group: str, key: str, tags_list: "list[tuple[_DriverTags, Path]]", device: str, extra_fields: "tuple[JsonDict, ...]" = ()) -> JsonDict:
    # The group one scanned file declares, its fields from every file in tags_list, then extra_fields.
    declaring = [t for t, _p in tags_list for g in t.group_tags if g.section == section and g.submit_group == submit_group]
    if len(declaring) == 0:
        raise BuildError(
            device, f"no @web-group tag declares section={section!r} submitGroup={submit_group!r} in any scanned file",
            rule="web.group-undeclared", fix=f'add # @web-group section={section} submitGroup={submit_group} label="..." to the file that owns the group',
        )
    if len(declaring) > 1:
        raise BuildError(
            device, f"more than one @web-group tag declares section={section!r} submitGroup={submit_group!r}",
            rule="web.group-declared-twice", fix="keep one @web-group tag for this section and submitGroup",
        )
    group_tag = next(g for g in declaring[0].group_tags if g.section == section and g.submit_group == submit_group)
    out = _group_shell(group_tag, key=key, label=group_tag.label)
    fields: list[JsonValue] = []
    for t, p in tags_list:
        fields.extend(_fields_for(t, section, submit_group, device, p))
    if not fields:
        raise BuildError(
            device, f"section={section!r} submitGroup={submit_group!r} has an @web-group declaration but no @web field tags reference it",
            rule="web.group-without-fields", fix="tag a field with this section and submitGroup, or remove the @web-group tag",
        )
    fields.extend(extra_fields)
    out["fields"] = fields
    return out


def _sensor_instance_specs(model: DeviceModel) -> "list[tuple[InstanceSpec, DriverInfo]]":
    # The registry's sensor instances, as cards in construction order (buildgen.graph); a model that
    # skipped the graph fails here rather than falling back to TOML order, so the CLI and the build agree.
    order = {node: i for i, node in enumerate(model.construction_order)}
    sensors: list[tuple[InstanceSpec, DriverInfo]] = []
    for spec in model.instances.values():
        if spec.driver_info is None:
            raise BuildInternalError(f"[{model.device}/{spec.label}] driver_info unresolved before definitions generation")
        if spec.driver_info.kind != "sensor":
            continue
        if spec.key not in order:
            raise BuildInternalError(f"[{model.device}/{spec.label}] construction order unresolved before definitions generation")
        sensors.append((spec, spec.driver_info))
    return sorted(sensors, key=lambda pair: order[pair[0].key])


def _notification_spec(model: DeviceModel) -> "InstanceSpec | None":
    return next((spec for spec in model.instances.values() if spec.driver == "notification"), None)


def _measurements_and_sensors_sections(model: DeviceModel, cache: "dict[Path, _DriverTags]") -> "tuple[JsonDict, JsonDict]":
    measurements = dict(_SECTION_SKELETON[0])
    sensors = dict(_SECTION_SKELETON[1])
    m_groups: list[JsonValue] = []
    s_groups: list[JsonValue] = []
    for spec, info in _sensor_instance_specs(model):
        path = info.source_path
        tags = _load_driver_tags(cache, path, model.device, spec.label)
        m_group = _instance_group(spec, "measurements", tags, path, model.device)
        s_group = _instance_group(spec, "sensors", tags, path, model.device)
        if m_group is None or s_group is None:
            section = "measurements" if m_group is None else "sensors"
            raise BuildError(
                model.device, f"{path}: no @web-group section={section} submitGroup=self tag found", instance=spec.label,
                rule="web.instance-group-missing", fix=f'add # @web-group section={section} submitGroup=self label="..." to {path.name}',
            )
        m_groups.append(m_group)
        s_groups.append(s_group)
    measurements["groups"] = m_groups
    sensors["groups"] = s_groups
    return measurements, sensors


def _logger_name(src_dir: Path, key: str, device: str) -> str:
    # A mandatory module's logger name, read from its file's own `_NAME`.
    return parse_name_constant(src_dir / _MANDATORY_ERRCOUNT_FILES[key], device, key)


def _networking_section(src_dir: Path, device: str, cache: "dict[Path, _DriverTags]") -> JsonDict:
    wifi_path = src_dir / "asy_wifi_service.py"
    ntp_path = src_dir / "asy_ntp_client.py"
    wifi_tags = _load_driver_tags(cache, wifi_path, device, "wifi")
    ntp_tags = _load_driver_tags(cache, ntp_path, device, "ntp")
    section = dict(_SECTION_SKELETON[2])
    dns_label = next(label for key, label, _has_cfgmgr in _ERRCOUNT_CATALOG if key == "dns")
    groups: list[JsonValue] = [
        _mandatory_group("networking", "identity", "identity", [(wifi_tags, wifi_path)], device),
        _mandatory_group("networking", "wifiLed", "wifiLed", [(wifi_tags, wifi_path)], device),
        _mandatory_group("networking", "ntp", "ntp", [(ntp_tags, ntp_path)], device),
        _mandatory_group("networking", "dns", "dns", [(ntp_tags, ntp_path)], device),
        # The captive DNS server's history is shown with the networking data (owner, 2026-09-26).
        _errcount_shell("dnsErrors", "Captive DNS Error History", [{"key": _logger_name(src_dir, "dns", device), "label": dns_label}], _load_catalog()),
    ]
    section["groups"] = groups
    return section


def _system_section(src_dir: Path, device: str, cache: "dict[Path, _DriverTags]") -> JsonDict:
    system_path = src_dir / "asy_system_service.py"
    ntp_path = src_dir / "asy_ntp_client.py"
    system_tags = _load_driver_tags(cache, system_path, device, "system")
    ntp_tags = _load_driver_tags(cache, ntp_path, device, "ntp")
    section = dict(_SECTION_SKELETON[3])
    groups: list[JsonValue] = [
        _mandatory_group("system", "settings", "settings", [(system_tags, system_path), (ntp_tags, ntp_path)], device),
        dict(_SYSTEM_COMMAND_GROUP),
        dict(_BUILD_GROUP),
    ]
    section["groups"] = groups
    return section


def _suffixed(label: str, name_ext: str) -> str:
    return label if not name_ext else f"{label} ({_NAME_EXT_LABEL.get(name_ext, name_ext)})"


def _errcount_shell(key: str, label: str, modules: "list[JsonValue]", catalog: _Catalog) -> JsonDict:
    # Every errcount group carries the same code-description block, so no two groups can differ.
    return {"key": key, "label": label, "kind": "errcount", "modules": modules, "codes": _errcount_codes(catalog)}


def _errcount_group(model: DeviceModel, catalog: _Catalog, src_dir: Path) -> JsonDict:
    # Keyed per logger INSTANCE, as the API publishes them: scd30_primary publishes
    # SCD30_primary and CFGMGR_SCD30_primary and needs a row under each. A kind-keyed catalog
    # drifts silently both ways - a missing source vanishes, a stale row renders a permanent 0.
    modules: list[JsonValue] = []
    by_driver: dict[str, list[InstanceSpec]] = {}
    for spec in model.instances.values():
        by_driver.setdefault(spec.driver, []).append(spec)
    # Catalog order is display order, each row keyed by resolved_name; the webserver's row is the
    # group's last entry (a UART row lands between notification and it), and dns is on Networking.
    for key, label, has_cfgmgr in _ERRCOUNT_CATALOG:
        if key in ("webserver", "dns"):
            continue
        if key in _MANDATORY_ERRCOUNT_FILES:
            # wifi/ntp/system are mandatory infrastructure, never [[instance]] - one logger each,
            # named by its own file's _NAME.
            name = _logger_name(src_dir, key, model.device)
            modules.append({"key": name, "label": label})
            if has_cfgmgr:
                modules.append({"key": f"CFGMGR_{name}", "label": _CFGMGR_LABEL[key]})
            continue
        for spec in by_driver.get(key, []):  # TOML declaration order, so two instances read in the order written
            name = _resolved_key(spec, model.device)
            modules.append({"key": name, "label": _suffixed(label, spec.name_ext)})
            if has_cfgmgr:
                modules.append({"key": f"CFGMGR_{name}", "label": _suffixed(_CFGMGR_LABEL[key], spec.name_ext)})
    webserver_label = next(label for key, label, _has_cfgmgr in _ERRCOUNT_CATALOG if key == "webserver")
    modules.append({"key": _logger_name(src_dir, "webserver", model.device), "label": webserver_label})
    return _errcount_shell("errcount", "Error Counts & History", modules, catalog)


def _sgp40_maintenance_fields(model: DeviceModel, cache: "dict[Path, _DriverTags]") -> "list[JsonValue]":
    # Built from the SGP40 driver's own section=status tags, one set per instance in construction
    # order; keyed as GET /status flattens them (<resolved_name>_<field>), labelled like its card.
    out: list[JsonValue] = []
    for spec, info in _sensor_instance_specs(model):
        if spec.driver != "sgp40":
            continue
        path = info.source_path
        tags = _load_driver_tags(cache, path, model.device, spec.label)
        maintenance = [t for t in tags.field_tags if t.hidden is None and t.section == "status" and t.submit_group == "maintenance"]
        if not maintenance:
            raise BuildError(
                model.device, f"{path}: no @web section=status submitGroup=maintenance tag found", instance=spec.label,
                rule="web.maintenance-tag-missing", fix=f"tag {path.name}'s maintenance fields with section=status submitGroup=maintenance",
            )
        for tag in maintenance:
            field = _build_field_def(tag, tags.schemas.get(tag.field_name), model.device, path)
            field["key"] = f"{_resolved_key(spec, model.device)}_{tag.field_name}"
            if spec.name_ext:
                field["label"] = f"{tag.label} ({spec.name_ext})"
            out.append(field)
    return out


def _status_section(model: DeviceModel, have: "set[str]", cache: "dict[Path, _DriverTags]", src_dir: Path) -> JsonDict:
    section = dict(_SECTION_SKELETON[4])
    networking_fields: list[JsonValue] = [
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
    # The order GET /status publishes the system keys in (codegen's _system_status()).
    system_fields: list[JsonValue] = [
        {"key": "SysUptime", "label": "System Uptime", "unit": "s", "kind": "readonly"},
        {
            "key": "BootSignature", "label": "Boot Signature", "kind": "readonly",
            "description": "Opaque value, stable for the running boot session; a different value on a later poll means the device rebooted. Not a human-readable code.",
        },
        {
            "key": "ResetReason", "label": "Last Reset Reason", "kind": "readonly", "description": "Why the device last restarted, as a numeric code.",
            "codes": _status_codes("ResetReason", model.device, "ResetReason"),
        },
        {
            "key": "ResetBits", "label": "Reset Flags", "kind": "readonly",
            "description": "The chip's own reset flags at this boot, reported raw: 1 watchdog timer expired, 2 reset forced by software, 256 power-on or brown-out, 65536 RUN pin, 1048576 debug-port restart.",
        },
        {"key": "MemFree", "label": "Free Heap", "unit": "B", "kind": "readonly", "description": "gc.mem_free() when this poll was answered; the floor under load is the figure of interest."},
    ]
    if "fram" in have:
        system_fields.append({"key": "MemPaused", "label": "Backups Paused", "kind": "readonly"})
    system_fields += [
        {
            "key": "ConfigFaults", "label": "Config Faults", "kind": "readonly",
            "description": "Modules whose config file existed at this boot but could not be read or was damaged (a damaged file is repaired at boot); empty when none. Listed until the next boot.",
        },
        {
            "key": "ConfigUnpersisted", "label": "Config Unpersisted", "kind": "readonly",
            "description": "Modules whose last accepted config change could not be written to flash: it applies now but is lost at the next boot. Empty when none; cleared by the module's next successful write.",
        },
        {"key": "LocalTime", "label": "Local Time", "kind": "readonly", "format": "gmtimestruct"},
        {"key": "UTCTime", "label": "UTC Time", "kind": "readonly", "format": "gmtimestruct"},
    ]
    groups: list[JsonValue] = [
        {"key": "networking", "label": "Networking Status", "fields": networking_fields},
        {"key": "system", "label": "System Status", "fields": system_fields},
    ]
    # "Sensor Maintenance": one group, its fields built additively from whichever maintenance-status
    # sources this device actually has (matches codegen._emit_webserver()'s own additive
    # maintenance_sensors= tuple) - never a per-driver group of its own, both here and there.
    maintenance_fields: list[JsonValue] = []
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
    # Every field group, then the error counts and their reset command; the webserver's row is errcount's last.
    groups.append(_errcount_group(model, _load_catalog(), src_dir))
    groups.append(dict(_RESET_ERRORS_GROUP))
    section["groups"] = groups
    return section


def _warn_field(signal: WarnSignal) -> JsonDict:
    # A warn signal's threshold field, built from the one signal catalog (buildgen.signals).
    field: JsonDict = {"key": signal.name, "label": signal.label}
    if signal.unit is not None:
        field["unit"] = signal.unit
    field.update({"kind": "number", "min": signal.min, "max": signal.max})
    if signal.field_type == "float":
        field["float"] = True
    return field


def _notification_section(model: DeviceModel, cache: "dict[Path, _DriverTags]", have: "set[str]") -> "JsonDict | None":
    spec = _notification_spec(model)
    if spec is None:
        return None
    if spec.driver_info is None:
        raise BuildInternalError(f"[{model.device}/{spec.label}] driver_info unresolved before definitions generation")
    path = spec.driver_info.source_path
    tags = _load_driver_tags(cache, path, model.device, spec.label)
    # Catalog order is display order, never the TOML's own [instance.wiring] key order.
    warn_fields = tuple(_warn_field(signal) for key, signal in WARN_SIGNALS.items() if key in spec.wiring)
    # Literal "autoConfig" key, not spec.resolved_name: NotificationService is a singleton
    # service (driver_registry.SERVICE_DRIVERS), so there is no multi-instance disambiguation need
    # the way scd30/sgp40/bmp3xx have.
    groups: list[JsonValue] = [_mandatory_group("notification", "autoConfig", "autoConfig", [(tags, path)], model.device, warn_fields)]
    if "neopixel" in have:
        groups.append(dict(_NOTIFICATION_FLASH_GROUP))
    groups.append(dict(_NOTIFICATION_PAUSE_GROUP))
    section = dict(_NOTIFICATION_SECTION_SKELETON)
    section["groups"] = groups
    return section


def generate_definitions(model: DeviceModel, src_dir: Path) -> JsonDict:
    # The full `definitions.json`-shaped dict for `model` (already `buildgen.validate.build_model()`-
    # validated). Every scanned `@web`/`@web-group` tag is re-parsed once per distinct source path
    # (`_DriverTags` cache), regardless of how many instances/sections reference it.
    have = {spec.driver for spec in model.instances.values()}
    cache: dict[Path, _DriverTags] = {}

    measurements, sensors = _measurements_and_sensors_sections(model, cache)
    sections: list[JsonValue] = [
        measurements,
        sensors,
        _networking_section(src_dir, model.device, cache),
        _system_section(src_dir, model.device, cache),
        _status_section(model, have, cache, src_dir),
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


def definitions_for_toml(toml_path: Path, src_dir: Path) -> JsonDict:
    # The one entry point from a device TOML to its definitions: validated model, construction
    # order (`buildgen.graph`), then `generate_definitions()` - every caller gets the build's order.
    model = build_model(toml_path, src_dir)
    build_construction_order(model)
    return generate_definitions(model, src_dir)


def _write_replacing(path: Path, text: str) -> None:
    # Written beside the target, then renamed over it: a failed write leaves the old file or none, never part of one.
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        raise


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
    except OSError as e:
        print(f"buildgen: cannot read {e.filename}: {e.strerror} - fix: check that --src-dir names a complete src/ tree", file=sys.stderr)
        return 1

    text = json.dumps(definitions, indent=2)
    if args.out is None:
        print(text)
        return 0
    try:
        _write_replacing(args.out, text)
    except OSError as e:
        print(f"buildgen: cannot write {args.out}: {e.strerror} - fix: check that the output directory exists and is writable", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
