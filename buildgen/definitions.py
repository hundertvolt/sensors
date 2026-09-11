"""Generates a device's website `definitions.json` (SPECIFICATION.md Part H.5) from a validated
`DeviceModel` plus the `# @web`/`# @web-group` tags on the `src/` files that own each field/group
(`buildgen.web_tag`; design rationale: Part H.5.1). CLI at the bottom: manual use + `build_website.sh`."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from buildgen.errors import BuildError
from buildgen.model import DeviceModel, InstanceSpec
from buildgen.schema_ast import FieldSchema, extract_field_schemas
from buildgen.validate import build_model
from buildgen.web_tag import SELF_GROUP, WebFieldTag, WebGroupTag, parse_web_group_tags, parse_web_tags

REPO_ROOT = Path(__file__).resolve().parent.parent

SCHEMA_VERSION = "1.0.0"

# Fixed, generator-owned REST-endpoint skeleton (H.4: "Nav grouping: Mirrors the 6 REST endpoints
# 1:1") - never per-device data, so never tag-derived (SPECIFICATION.md Part H.5.1). "groups" is
# filled in per device below; "notification" is appended only when a `notification` instance exists.
_SECTION_SKELETON: "tuple[dict[str, Any], ...]" = (
    {"key": "measurements", "label": "Measurements", "description": "Live sensor readings, refreshed automatically.", "rest": {"get": "/measurements"}, "pollGroup": "live"},
    {"key": "sensors", "label": "Sensors", "description": "Per-sensor configuration. Each card applies independently.", "rest": {"get": "/sensors", "put": "/sensors"}, "pollGroup": "settings"},
    {"key": "networking", "label": "Networking", "description": "Wi-Fi credentials, identity, and NTP time sync. Live status (IP, RSSI, uptime, sync age) is on the Status page.", "rest": {"get": "/networking", "put": "/networking"}, "pollGroup": "settings"},
    {"key": "system", "label": "System", "rest": {"get": "/system", "put": "/system"}, "pollGroup": "settings"},
    {"key": "status", "label": "Status", "description": "Live system/network/error state. Error counts are always visible; click a module to see its history.", "rest": {"get": "/status", "put": "/status"}, "pollGroup": "live", "pollIntervalMs": 3000},
)
_NOTIFICATION_SECTION_SKELETON: "dict[str, Any]" = {
    "key": "notification", "label": "Notification", "rest": {"get": "/notification", "put": "/notification"}, "pollGroup": "settings",
}

# Instances scanned per-device (their web-facing fields/groups vary by which TOML instance exists,
# and by name_ext when more than one instance of the same driver is present).
_SENSOR_DRIVERS = ("scd30", "sgp40", "bmp3xx")

# buildgen.codegen._KNOWN_SIGNALS' own parallel: label/unit UI metadata for the same three warn_*
# TOML wiring keys, keyed identically. Min/max match that catalog's own field-schema literals
# exactly (_FIELD_WARN_CO2/_FIELD_WARN_VOC/_FIELD_WARN_HUM).
_WARN_SIGNAL_WEB_CATALOG: "dict[str, dict[str, Any]]" = {
    "warn_co2": {"key": "WarnCO2", "label": "CO2 Warning Threshold", "unit": "ppm", "kind": "number", "min": 0, "max": 3000},
    "warn_voc": {"key": "WarnVOC", "label": "VOC Warning Threshold", "kind": "number", "min": 0, "max": 500},
    "warn_hum": {"key": "WarnHum", "label": "Humidity Warning Threshold", "unit": "%", "kind": "number", "min": 0.0, "max": 100.0, "float": True},
}

# Dispatch-only, webserver-level fields with no real per-device variation and no single owning
# driver file (SPECIFICATION.md Part H.5.1). `lightCmdLED`'s own bounds
# mirror asy_webserver_service.py's `_dispatch_notification_led()`/sensortask_wozi.py's
# `_FIELD_LED_R/G/B/T` (universal across every device); `SystemCmd` mirrors
# asy_webserver_service.py's `_SYSTEM_CMDS`; `PauseTime` mirrors its own `_PAUSE_TIME_FIELD`.
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
    "fields": [{"key": "lightCmdLED", "label": "LED Flash", "kind": "composite", "subFields": [
        {"key": "r", "label": "Red", "kind": "number", "min": 0, "max": 255},
        {"key": "g", "label": "Green", "kind": "number", "min": 0, "max": 255},
        {"key": "b", "label": "Blue", "kind": "number", "min": 0, "max": 255},
        {"key": "t", "label": "Time (s)", "kind": "number", "min": 0.5, "max": 60.0, "float": True},
    ]}],
}
_NOTIFICATION_PAUSE_GROUP: "dict[str, Any]" = {
    "key": "pause", "label": "Pause Notifications", "submit": True,
    "fields": [{
        "key": "PauseTime", "label": "Pause Time", "unit": "s", "kind": "number", "min": 0, "max": 3600,
        "description": "Temporarily suppress automatic LED notifications. Current value is live (from Status).",
    }],
}
_RESET_ERRORS_GROUP: "dict[str, Any]" = {
    "key": "resetErrors", "label": "Reset Errors", "submit": True, "submitLabel": "Reset All Errors",
    "fields": [{
        "key": "ResetErrors", "label": "Confirm Reset", "kind": "toggle", "onLabel": "Yes, reset", "offLabel": "No",
        "description": "Resets every module's error counter and history in one call. Absent/No is a no-op.", "dispatch": True,
    }],
}

# Errcount module catalog (H.6): {have-key: (label, has_cfgmgr_companion)}. "have-key" is the same
# vocabulary as an instance's own `driver` TOML string for optional modules, plus the five
# mandatory-infrastructure/fixed keys that are never `[[instance]]` entries. Fixed/generator-owned
# for the same reason as the dispatch-only catalogs above: these are cosmetic UI labels, not a
# per-driver fact any one source file is the sole owner of.
_MANDATORY_ERRCOUNT_KEYS = frozenset({"wifi", "dns", "ntp", "system", "webserver"})
_ERRCOUNT_CATALOG: "tuple[tuple[str, str, bool], ...]" = (
    ("wifi", "Wi-Fi", True),
    ("dns", "Captive DNS", False),
    ("ntp", "NTP Client", True),
    ("fram", "FRAM Storage", False),
    ("system", "System", True),
    ("scd30", "SCD30", False),  # NVM-backed - no local ConfigManager, so no CFGMGR_ companion (H.6)
    ("sgp40", "SGP40", True),
    ("bmp3xx", "BMP388", True),
    ("neopixel", "Neopixel LED", False),
    ("notification", "Notification Service", True),
    ("webserver", "Web Server", False),
)
_ERRCOUNT_NAME: "dict[str, str]" = {
    "wifi": "WIFI", "dns": "DNSSRV", "ntp": "NTP", "fram": "FRAM", "system": "SYSTEM",
    "scd30": "SCD30", "sgp40": "SGP40", "bmp3xx": "BMP3XX", "neopixel": "NEOPIXEL",
    "notification": "NOTIFY", "webserver": "WEBSERVER",
}
_CFGMGR_LABEL: "dict[str, str]" = {
    "wifi": "Wi-Fi Config Store", "ntp": "NTP Config Store", "system": "System Config Store",
    "sgp40": "SGP40 Config Store", "bmp3xx": "BMP388 Config Store", "notification": "Notification Config Store",
}


class _DriverTags:
    """Parsed `@web`/`@web-group` tags plus real `ConfigSchema` literals for one source file,
    cached so a file scanned by more than one instance (two SCD30s, or WiFi/NTP/System, which are
    scanned once per device regardless of instance count) is only ever tokenized/AST-parsed once."""

    def __init__(self, path: Path, device: str, instance_label: str) -> None:
        self.field_tags: tuple[WebFieldTag, ...] = parse_web_tags(path, device, instance_label)
        self.group_tags: tuple[WebGroupTag, ...] = parse_web_group_tags(path, device, instance_label)
        self.schemas: dict[str, FieldSchema] = extract_field_schemas(path)


def _load_driver_tags(cache: "dict[Path, _DriverTags]", path: Path, device: str, instance_label: str) -> _DriverTags:
    if path not in cache:
        cache[path] = _DriverTags(path, device, instance_label)
    return cache[path]


def _coerce_special_value(raw: str, field_type: "str | None") -> "int | float | str":
    if field_type == "float":
        return float(raw)
    if field_type == "int":
        return int(raw)
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


def _string_field(tag: WebFieldTag, min_v: object, max_v: object) -> "dict[str, Any]":
    out: dict[str, Any] = {}
    if min_v is not None:
        out["minLength"] = min_v
    if max_v is not None:
        out["maxLength"] = max_v
    if tag.mask:
        out["mask"] = True
    return out


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
        # SGP40's BackupPeriod=0 - a perfectly ordinary in-range value that also has a special UI
        # meaning, never a bypass config_manager.py's own validation needs to know about).
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

    if kind == "toggle":
        out.update(_toggle_field(tag))
    elif kind == "string":
        out.update(_string_field(tag, min_v, max_v))
    elif kind == "enum":
        out.update(_enum_field(tag, special, device, path))
    elif kind == "number":
        out.update(_number_field(tag, field_type, min_v, max_v, special, device, path))

    if tag.description:
        out["description"] = tag.description
    if tag.dispatch:
        out["dispatch"] = True
    if tag.default_value is not None:
        out["defaultValue"] = tag.default_value
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
    order = {node: i for i, node in enumerate(model.construction_order)}
    return sorted(
        (spec for spec in model.instances.values() if spec.driver in _SENSOR_DRIVERS),
        key=lambda spec: order.get(spec.key, spec.order_index),
    )


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


def _networking_section(src_dir: Path, device: str, cache: "dict[Path, _DriverTags]") -> "dict[str, Any]":
    wifi_path = src_dir / "asy_wifi_service.py"
    ntp_path = src_dir / "asy_ntp_client.py"
    wifi_tags = _load_driver_tags(cache, wifi_path, device, "wifi")
    ntp_tags = _load_driver_tags(cache, ntp_path, device, "ntp")
    section = dict(_SECTION_SKELETON[2])
    section["groups"] = [
        _mandatory_group("networking", "identity", "identity", [(wifi_tags, wifi_path)], device),
        _mandatory_group("networking", "wifiLed", "wifiLed", [(wifi_tags, wifi_path)], device),
        _mandatory_group("networking", "ntp", "ntp", [(ntp_tags, ntp_path)], device),
    ]
    return section


def _system_section(src_dir: Path, device: str, cache: "dict[Path, _DriverTags]") -> "dict[str, Any]":
    system_path = src_dir / "system_service.py"
    ntp_path = src_dir / "asy_ntp_client.py"
    system_tags = _load_driver_tags(cache, system_path, device, "system")
    ntp_tags = _load_driver_tags(cache, ntp_path, device, "ntp")
    section = dict(_SECTION_SKELETON[3])
    section["groups"] = [
        _mandatory_group("system", "settings", "settings", [(system_tags, system_path), (ntp_tags, ntp_path)], device),
        dict(_SYSTEM_COMMAND_GROUP),
    ]
    return section


def _errcount_group(have: "set[str]") -> "dict[str, Any]":
    modules: list[dict[str, str]] = []
    for key, label, has_cfgmgr in _ERRCOUNT_CATALOG:
        if key not in _MANDATORY_ERRCOUNT_KEYS and key not in have:
            continue
        modules.append({"key": _ERRCOUNT_NAME[key], "label": label})
        if has_cfgmgr:
            modules.append({"key": f"CFGMGR_{_ERRCOUNT_NAME[key]}", "label": _CFGMGR_LABEL[key]})
    return {"key": "errcount", "label": "Error Counts & History", "kind": "errcount", "modules": modules}


def _status_section(have: "set[str]") -> "dict[str, Any]":
    section = dict(_SECTION_SKELETON[4])
    networking_fields = [
        {"key": "Mode", "label": "Wi-Fi Mode", "kind": "readonly"},
        {"key": "Connected", "label": "Connected", "kind": "readonly"},
        {"key": "IP", "label": "IP Address", "kind": "readonly"},
        {"key": "IPv4", "label": "IPv4 Address", "kind": "readonly"},
        {"key": "Subnet", "label": "Subnet Mask", "kind": "readonly"},
        {"key": "Gateway", "label": "Gateway", "kind": "readonly"},
        {"key": "DNS", "label": "Name Server", "kind": "readonly"},
        {"key": "Rssi", "label": "Wi-Fi RSSI", "unit": "dBm", "kind": "readonly"},
        {"key": "WifiUptime", "label": "Wi-Fi Uptime", "unit": "s", "kind": "readonly"},
        {"key": "NtpSynced", "label": "NTP Synced", "kind": "readonly"},
        {"key": "NtpLastSyncAge", "label": "NTP Last Sync Age", "unit": "s", "kind": "readonly"},
        {"key": "NtpLastSync", "label": "NTP Last Sync Time", "unit": "s", "kind": "readonly", "description": "Unix timestamp of the last successful sync."},
    ]
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
        {"key": "UtcTime", "label": "UTC Time", "kind": "readonly", "format": "gmtimestruct"},
    ]
    groups = [
        {"key": "networking", "label": "Networking Status", "fields": networking_fields},
        {"key": "system", "label": "System Status", "fields": system_fields},
    ]
    if "sgp40" in have:
        groups.append({"key": "sensors", "label": "Sensor Maintenance", "fields": [
            {"key": "SGP40_BackupTS", "label": "SGP40 Last Backup", "kind": "readonly"},
            {"key": "SGP40_RestoreTS", "label": "SGP40 Restore Timestamp", "kind": "readonly"},
        ]})
    if "notification" in have:
        groups.append({"key": "notification", "label": "Notification Status", "fields": [
            {"key": "Triggered", "label": "Currently Triggered", "kind": "readonly"},
            {"key": "TS", "label": "Last Trigger Timestamp", "kind": "readonly"},
            {"key": "PauseTime", "label": "Remaining Pause Time", "unit": "s", "kind": "readonly"},
        ]})
    groups.append(_errcount_group(have))
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
    # Literal "autoConfig" key, not spec.resolved_name: NotificationCoordinator is a singleton
    # service (driver_registry.SERVICE_DRIVERS), so there is no multi-instance disambiguation need
    # the way scd30/sgp40/bmp3xx have - matches the hand-written definitions files' own key.
    auto_group = _mandatory_group("notification", "autoConfig", "autoConfig", [(tags, path)], model.device)
    # Preserve the fixed catalog's own declaration order (matches the hand-written definitions
    # files) rather than the TOML's own [instance.wiring] key order.
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
    """The full `definitions.json`-shaped dict for `model` (already `buildgen.validate.build_model()`-
    validated). Every scanned `@web`/`@web-group` tag is re-parsed once per distinct source path
    (`_DriverTags` cache), regardless of how many instances/sections reference it."""
    have = {spec.driver for spec in model.instances.values()}
    cache: dict[Path, _DriverTags] = {}

    measurements, sensors = _measurements_and_sensors_sections(model, cache)
    sections = [
        measurements,
        sensors,
        _networking_section(src_dir, model.device, cache),
        _system_section(src_dir, model.device, cache),
        _status_section(have),
    ]
    notification = _notification_section(model, cache, have)
    if notification is not None:
        sections.append(notification)

    return {
        "schemaVersion": SCHEMA_VERSION,
        "device": {"id": model.device, "displayName": model.device},
        "landingSection": "measurements",
        "defaultPollIntervalMs": 3000,
        "sections": sections,
    }


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a device's website definitions.json from its device TOML.")
    parser.add_argument("device_toml", type=Path)
    parser.add_argument("--src-dir", type=Path, default=REPO_ROOT / "src")
    parser.add_argument("--out", type=Path, default=None, help="write definitions.json here instead of printing to stdout")
    args = parser.parse_args(argv)

    try:
        model = build_model(args.device_toml, args.src_dir)
        definitions = generate_definitions(model, args.src_dir)
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
