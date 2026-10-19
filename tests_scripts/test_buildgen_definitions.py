"""Tests for buildgen.definitions (SPECIFICATION.md Part H.5/H.5.1): every tagged field lands once in its group,
every device's output passes the shared shape corpus, and the catalog-derived blocks equal their sources."""

import ast
import copy
import functools
import json
import math
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import TypeGuard

import pytest
import tomllib
from _devices import DEVICE_NAMES, device_toml, devices_with

from buildgen.definitions import SCHEMA_VERSION, _build_field_def, _DriverTags, definitions_for_toml, generate_definitions, main
from buildgen.driver_registry import DriverInfo
from buildgen.errors import BuildError, BuildInternalError
from buildgen.generate import generate_device
from buildgen.graph import build_construction_order
from buildgen.jsontypes import JsonDict, JsonValue
from buildgen.model import DeviceModel, InstanceSpec
from buildgen.schema_ast import _eval_literal, extract_field_schemas
from buildgen.signals import WARN_SIGNALS
from buildgen.validate import build_model
from buildgen.version import WEBSITE_VERSION
from buildgen.web_tag import _MAX_DECIMALS, SELF_GROUP, WebFieldTag, parse_web_tags, resolution_decimals

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CATALOG = json.loads((_REPO_ROOT / "buildgen" / "error_catalog.json").read_text(encoding="utf-8"))
_SHAPE_CASES = json.loads((_REPO_ROOT / "tests_scripts" / "definitions_shape_cases.json").read_text(encoding="utf-8"))
# The files every device's mandatory networking/system groups are tagged in; instance files come from
# the model (each instance's driver_info.source_path).
_MANDATORY_TAG_FILES = ("asy_wifi_service.py", "asy_ntp_client.py", "asy_system_service.py")


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


@pytest.fixture
def fixtures_dir(repo_root: Path) -> Path:
    return repo_root / "tests_scripts" / "buildgen_fixtures"


@functools.cache
def _definitions_text(toml_path: Path, src_dir: Path) -> str:
    # One generation per device file and source tree, kept as JSON text so every caller parses its own copy.
    return json.dumps(definitions_for_toml(toml_path, src_dir))


@functools.cache
def _module_source(toml_path: Path, src_dir: Path, ext_dir: Path) -> str:
    return generate_device(toml_path, src_dir, ext_dir).module_source


def _generate(repo_root: Path, src_dir: Path, device: str) -> "JsonDict":
    parsed: JsonDict = json.loads(_definitions_text(repo_root / "devices" / f"{device}.toml", src_dir))
    return parsed


def _read(definitions: JsonDict) -> "JsonDict":
    # The generated definitions as the page reads them: through JSON, which every value must survive.
    parsed: JsonDict = json.loads(json.dumps(definitions))
    return parsed


def _str(value: "JsonValue") -> str:
    assert isinstance(value, str), value
    return value


def _opt_str(value: "JsonValue") -> "str | None":
    assert value is None or isinstance(value, str), value
    return value


def _int(value: "JsonValue") -> int:
    assert isinstance(value, int) and not isinstance(value, bool), value
    return value


def _strs(value: "JsonValue") -> "list[str]":
    assert isinstance(value, list), value
    return [_str(v) for v in value]


def _obj(value: "JsonValue") -> "JsonDict":
    assert isinstance(value, dict), value
    return value


def _is_objs(value: "list[JsonValue]") -> "TypeGuard[list[JsonDict]]":
    return all(isinstance(v, dict) for v in value)


def _objs(value: "JsonValue") -> "list[JsonDict]":
    # A JSON array of objects, as the same list, so a test's in-place edit reaches the document.
    assert isinstance(value, list) and _is_objs(value), value
    return value


def _sections(definitions: "JsonDict") -> "list[JsonDict]":
    return _objs(definitions["sections"])


def _section(definitions: "JsonDict", key: str) -> "JsonDict":
    return next(s for s in _sections(definitions) if s["key"] == key)


def _groups(section: "JsonDict") -> "list[JsonDict]":
    return _objs(section["groups"])


def _group(section: "JsonDict", key: str) -> "JsonDict":
    return next(g for g in _groups(section) if g["key"] == key)


def _fields(group: "JsonDict") -> "list[JsonDict]":
    # An errcount group carries modules, not fields: it reads as an empty field list.
    return _objs(group.get("fields", []))


def _field_groups(definitions: "JsonDict") -> "list[tuple[str, JsonDict]]":
    # (section key, group) for every field group - errcount groups carry modules, not fields.
    return [(_str(s["key"]), g) for s in _sections(definitions) for g in _groups(s) if "fields" in g]


def _errcount_groups(definitions: "JsonDict") -> "list[tuple[str, JsonDict]]":
    return [(_str(s["key"]), g) for s in _sections(definitions) for g in _groups(s) if g.get("kind") == "errcount"]


def _assert_rule(error: BuildError, rule: str) -> None:
    # Every build error names the rule it broke and carries its fix in the message (SPECIFICATION.md L.5).
    assert error.rule == rule, error.rule
    assert error.fix and str(error).endswith(f" - fix: {error.fix}"), str(error)


# ---------------------------------------------------------------------------
# The tag oracle: every @web tag a device's files carry lands exactly once, in the group it names
# ---------------------------------------------------------------------------


def _tag_place(tag: WebFieldTag, spec: "InstanceSpec | None") -> "tuple[str, str, str]":
    # (section, group key, field key) a tag must land at: an instance's own card for `self`, the
    # Status page's Sensor Maintenance group keyed `<instance>_<field>` for a status tag, else its group.
    if spec is not None and tag.submit_group == SELF_GROUP:
        assert spec.resolved_name is not None
        return tag.section, spec.resolved_name, tag.field_name
    if spec is not None and tag.section == "status":
        assert spec.resolved_name is not None
        return "status", "sensors", f"{spec.resolved_name}_{tag.field_name}"
    return tag.section, tag.submit_group, tag.field_name


def _tag_sources(model: DeviceModel, src_dir: Path) -> "list[tuple[Path, InstanceSpec | None]]":
    sources: list[tuple[Path, InstanceSpec | None]] = [(src_dir / name, None) for name in _MANDATORY_TAG_FILES]
    return sources + [(spec.driver_info.source_path, spec) for spec in model.instances.values() if spec.driver_info is not None]


def _expected_tagged_fields(model: DeviceModel, src_dir: Path) -> "Counter[tuple[str, str, str, str, str | None]]":
    # A hidden= tag places nothing: _hidden_problems() checks that its field stays off the page.
    expected: Counter[tuple[str, str, str, str, str | None]] = Counter()
    for path, spec in _tag_sources(model, src_dir):
        for tag in parse_web_tags(path, model.device, spec.label if spec is not None else path.stem):
            if tag.hidden is None:
                section, group, key = _tag_place(tag, spec)
                expected[(section, group, key, tag.label, tag.unit)] += 1
    return expected


def _hidden_problems(model: DeviceModel, src_dir: Path, definitions: "JsonDict") -> "list[str]":
    # A hidden field shows in none of its file's groups: an instance's own cards and maintenance rows, or a mandatory file's sections.
    problems: list[str] = []
    for path, spec in _tag_sources(model, src_dir):
        hidden = {tag.field_name for tag in parse_web_tags(path, model.device, spec.label if spec is not None else path.stem) if tag.hidden is not None}
        for section in _sections(definitions):
            for group in _groups(section):
                own = group["key"] == spec.resolved_name if spec is not None else section["key"] in {"networking", "system"}
                keys = {_str(f["key"]) for f in _fields(group)}
                shown = (keys & hidden if own else set()) | (keys & {f"{spec.resolved_name}_{name}" for name in hidden} if spec is not None else set())
                problems += [f"{path.name}: hidden {key} shown in {section['key']}/{group['key']}" for key in sorted(shown)]
    return problems


def _tag_placement_problems(expected: "Counter[tuple[str, str, str, str, str | None]]", definitions: "JsonDict") -> "list[str]":
    # Every generated field whose key some tag of its section names, counted against where the tags put it.
    tagged = {(section, key) for section, _group, key, _label, _unit in expected}
    actual: Counter[tuple[str, str, str, str, str | None]] = Counter(
        (section, _str(group["key"]), _str(f["key"]), _str(f["label"]), _opt_str(f.get("unit")))
        for section, group in _field_groups(definitions)
        for f in _fields(group)
        if (section, f["key"]) in tagged
    )
    missing, extra = expected - actual, actual - expected
    return [f"tagged but not generated there: {sorted(missing)}"] * bool(missing) + [f"generated with no matching tag there: {sorted(extra)}"] * bool(extra)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_tagged_field_lands_once_in_its_group(repo_root: Path, src_dir: Path, device: str) -> None:
    # The independent oracle: tags read straight from the files, never through the generator, so a
    # field dropped, duplicated or landing in another instance's card fails here.
    model = build_model(device_toml(device), src_dir)
    generated = _generate(repo_root, src_dir, device)
    assert _tag_placement_problems(_expected_tagged_fields(model, src_dir), generated) == []
    assert _hidden_problems(model, src_dir, generated) == []


def test_the_tag_oracle_bites(repo_root: Path, src_dir: Path) -> None:
    device = DEVICE_NAMES[0]
    model = build_model(device_toml(device), src_dir)
    expected = _expected_tagged_fields(model, src_dir)
    generated = _generate(repo_root, src_dir, device)
    dropped = copy.deepcopy(generated)
    _section, group = next((s, g) for s, g in _field_groups(dropped) if _fields(g) and g["key"] != "build")
    removed = _fields(group).pop(0)
    assert _tag_placement_problems(expected, dropped), f"dropping {removed['key']} went unnoticed"
    duplicated = copy.deepcopy(generated)
    _section, group = next((s, g) for s, g in _field_groups(duplicated) if _fields(g) and g["key"] != "build")
    _fields(group).append(dict(_fields(group)[0]))
    assert _tag_placement_problems(expected, duplicated), "a duplicated field went unnoticed"


def test_the_hidden_oracle_bites(repo_root: Path, src_dir: Path) -> None:
    # A device with an instance whose file hides a field: that field planted in its card, or as its maintenance row, is found.
    for device in DEVICE_NAMES:
        model = build_model(device_toml(device), src_dir)
        spec = next((s for s in model.instances.values() if s.driver_info is not None and any(t.hidden for t in parse_web_tags(s.driver_info.source_path, device, s.label))), None)
        if spec is not None:
            break
    else:
        pytest.fail("no device has an instance with a hidden= field, so the oracle below bites on nothing")
    assert spec.driver_info is not None
    name = next(t.field_name for t in parse_web_tags(spec.driver_info.source_path, device, spec.label) if t.hidden)
    generated = _generate(repo_root, src_dir, device)
    assert _hidden_problems(model, src_dir, generated) == []
    for key in (name, f"{spec.resolved_name}_{name}"):
        planted = copy.deepcopy(generated)
        _section, group = next((s, g) for s, g in _field_groups(planted) if g["key"] == (spec.resolved_name if key == name else "sensors"))
        _fields(group).append({"key": key, "label": key, "kind": "readonly"})
        assert _hidden_problems(model, src_dir, planted), f"a hidden {key} went unnoticed"


# ---------------------------------------------------------------------------
# Per-device structural variation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_bmp3xx_group_presence_matches_device_instance_set(repo_root: Path, src_dir: Path, device: str) -> None:
    generated = _generate(repo_root, src_dir, device)
    group_keys = {_str(g["key"]) for g in _groups(_section(generated, "sensors"))}
    if device in devices_with("bmp3xx"):
        assert "BMP3XX" in group_keys
    else:
        assert "BMP3XX" not in group_keys


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_isl29125_group_presence_matches_device_instance_set(repo_root: Path, src_dir: Path, device: str) -> None:
    generated = _generate(repo_root, src_dir, device)
    group_keys = {_str(g["key"]) for g in _groups(_section(generated, "sensors"))}
    if device in devices_with("isl29125"):
        assert "ISL29125" in group_keys
    else:
        assert "ISL29125" not in group_keys


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_real_device_has_all_six_sections(repo_root: Path, src_dir: Path, device: str) -> None:
    generated = _generate(repo_root, src_dir, device)
    assert {_str(s["key"]) for s in _sections(generated)} == {"measurements", "sensors", "networking", "system", "status", "notification"}


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_real_device_stamps_the_website_version(repo_root: Path, src_dir: Path, device: str) -> None:
    # SPECIFICATION.md Part L.7: buildgen.version.WEBSITE_VERSION is a build-provenance-only
    # stamp, independent of schemaVersion (the wire-format shape version) - a genuinely different
    # concept, so the two must never collide on the same key.
    generated = _generate(repo_root, src_dir, device)
    assert generated["websiteVersion"] == WEBSITE_VERSION
    assert generated["websiteVersion"] != generated["schemaVersion"]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_status_pages_system_group_does_not_declare_a_firmware_version_field(repo_root: Path, src_dir: Path, device: str) -> None:
    # Regression guard against an earlier, corrected design: the firmware version
    # lives on GET /system's "build" sub-entry (src/asy_webserver_service.py's build_info=), not on
    # GET /status's "system" section - definitions.json's Status page never declares it.
    generated = _generate(repo_root, src_dir, device)
    system_group = _group(_section(generated, "status"), "system")
    assert not any(f["key"] == "FirmwareVersion" for f in _fields(system_group))


def _returned_keys(module_source: str, function: str) -> "list[str]":
    # The literal keys of the dict a generated status source returns.
    fn = next(n for n in ast.walk(ast.parse(module_source)) if isinstance(n, ast.AsyncFunctionDef) and n.name == function)
    returned = next(n.value for n in ast.walk(fn) if isinstance(n, ast.Return))
    assert isinstance(returned, ast.Dict), f"{function}() returns no dict literal"
    return [k.value for k in returned.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_each_status_group_lists_the_keys_its_generated_source_returns(repo_root: Path, src_dir: Path, device: str) -> None:
    source = _module_source(device_toml(device), src_dir, repo_root / "ext")
    groups = {_str(g["key"]): g for g in _groups(_section(_generate(repo_root, src_dir, device), "status"))}
    for key, function in (("networking", "_networking_status"), ("system", "_system_status"), ("notification", "_notification_status")):
        if key not in groups:
            assert f"async def {function}(" not in source, f"{function}() is generated but no status group lists it"
            continue
        assert sorted(_str(f["key"]) for f in _fields(groups[key])) == sorted(_returned_keys(source, function)), key


# The devices whose TOML declares a notification: the notification checks below run on each of them.
_NOTIFICATION_DEVICES = devices_with("notification")


def _wired_warn_signals(device: str) -> "list[str]":
    # The warn signals a device's notification wires, read from its TOML.
    instances = tomllib.loads(device_toml(device).read_text(encoding="utf-8")).get("instance", [])
    notifications = [i for i in instances if isinstance(i, dict) and i.get("driver") == "notification"]
    return [key for i in notifications if isinstance(i.get("wiring"), dict) for key in i["wiring"] if key in WARN_SIGNALS]


def test_a_real_device_wires_a_notification_and_a_warn_signal() -> None:
    # The floor of the per-device notification checks: none of them may pass by running on no device.
    assert _NOTIFICATION_DEVICES, "no device declares a notification, so the notification checks below run on nothing"
    assert any(_wired_warn_signals(device) for device in _NOTIFICATION_DEVICES), "no notification wires a warn signal, so the warn-field check compares two empty lists"


@pytest.mark.parametrize("device", _NOTIFICATION_DEVICES)
def test_the_notification_status_publishes_why_its_signals_were_not_evaluated(repo_root: Path, src_dir: Path, device: str) -> None:
    # State rides beside Triggered in the published order, its codes the catalog's NotifyState table (SPECIFICATION.md A.4).
    source = _module_source(device_toml(device), src_dir, repo_root / "ext")
    status = _section(_generate(repo_root, src_dir, device), "status")
    group = next((g for g in _groups(status) if g["key"] == "notification"), None)
    assert group is not None, f"{device} declares a notification, yet its status lists no notification group"
    assert [f["key"] for f in _fields(group)] == _returned_keys(source, "_notification_status") == ["Triggered", "State", "TS", "PauseTime"]
    assert _fields(group)[1] == {
        "key": "State", "label": "Evaluation State", "kind": "readonly",
        "description": "Whether the last notification cycle evaluated every signal, and why not, as a numeric code.",
        "codes": {num: row["text"] for num, row in _CATALOG["status"]["NotifyState"].items()},
    }


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_networking_status_carries_the_address_once_and_says_what_the_link_counts(repo_root: Path, src_dir: Path, device: str) -> None:
    fields = {_str(f["key"]): f for f in _fields(_group(_section(_generate(repo_root, src_dir, device), "status"), "networking"))}
    assert "IP" not in fields
    assert "IPv4" in fields
    assert fields["Connected"]["description"] == "True while the Wi-Fi link is up, hotspot included."
    assert fields["WifiUptime"]["description"] == "Seconds the Wi-Fi link has been up, hotspot included; 0 while it is down."


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_networking_status_lists_the_drop_window_and_the_wifi_snapshot_time(repo_root: Path, src_dir: Path, device: str) -> None:
    fields = {_str(f["key"]): f for f in _fields(_group(_section(_generate(repo_root, src_dir, device), "status"), "networking"))}
    assert fields["HTTPDropped"] == {"key": "HTTPDropped", "label": "Dropped Connections", "kind": "readonly", "description": "Web connections dropped in the last 24 hours, hourly resolution."}
    assert fields["WifiTS"] == {"key": "WifiTS", "label": "Wi-Fi Status Time", "kind": "readonly", "format": "epoch"}


# GET /status's system keys in the order the generated _system_status() publishes them; MemPaused only with FRAM.
_SYSTEM_STATUS_KEYS = ("SysUptime", "BootSignature", "ResetReason", "ResetBits", "MemFree", "MemPaused", "ConfigFaults", "ConfigUnpersisted", "LocalTime", "UTCTime", "UnixTime")


def _system_status_fields(repo_root: Path, src_dir: Path, device: str) -> "list[JsonDict]":
    return _fields(_group(_section(_generate(repo_root, src_dir, device), "status"), "system"))


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_system_status_lists_its_rows_in_the_published_order(repo_root: Path, src_dir: Path, device: str) -> None:
    has_fram = any(spec.driver == "fram" for spec in build_model(device_toml(device), src_dir).instances.values())
    expected = [key for key in _SYSTEM_STATUS_KEYS if has_fram or key != "MemPaused"]
    assert [f["key"] for f in _system_status_fields(repo_root, src_dir, device)] == expected


def test_the_reset_heap_and_config_rows_say_what_they_report(repo_root: Path, src_dir: Path) -> None:
    fields = {_str(f["key"]): f for f in _system_status_fields(repo_root, src_dir, DEVICE_NAMES[0])}
    reset_codes = {num: row["text"] for num, row in _CATALOG["status"]["ResetReason"].items()}
    assert fields["ResetReason"] == {
        "key": "ResetReason", "label": "Last Reset Reason", "kind": "readonly", "description": "Why the device last restarted, as a numeric code; click it for its meaning.", "codes": reset_codes,
    }
    assert fields["ResetBits"] == {
        "key": "ResetBits", "label": "Reset Flags", "kind": "readonly",
        "description": "The chip's own reset flags at this boot, reported raw: 1 watchdog timer expired, 2 reset forced by software, 256 power-on or brown-out, 65536 RUN pin, 1048576 debug-port restart.",
    }
    assert fields["MemFree"] == {"key": "MemFree", "label": "Free Heap", "unit": "B", "kind": "readonly", "description": "gc.mem_free() when this poll was answered; the floor under load is the figure of interest."}
    assert fields["ConfigFaults"] == {
        "key": "ConfigFaults", "label": "Config Faults", "kind": "readonly",
        "description": "Modules whose config file existed at this boot but could not be read or was damaged (a damaged file is repaired at boot); empty when none. Listed until the next boot.",
    }
    assert fields["ConfigUnpersisted"] == {
        "key": "ConfigUnpersisted", "label": "Config Unpersisted", "kind": "readonly",
        "description": "Modules whose last accepted config change could not be written to flash: it applies now but is lost at the next boot. Empty when none; cleared by the module's next successful write.",
    }


# The label the page shows for each service word.
_SYSTEM_CMD_LABELS = {"reboot": "Reboot", "bootloader": "Reboot into bootloader", "mempause": "Pause backups for 5 minutes", "resetconfig": "Reset to defaults", "erasefram": "Erase FRAM"}


def _system_cmd_problems(definitions: "JsonDict", src_dir: Path) -> "list[str]":
    (field,) = _fields(_group(_section(definitions, "system"), "command"))
    problems = [] if (field["key"], field["kind"], field["dispatch"]) == ("SystemCmd", "enum", True) else [f"the command field is {field['key']}/{field['kind']}"]
    words, options = _system_cmd_words(src_dir), _objs(field["options"])
    if [o["value"] for o in options] != words:
        return [*problems, f"SystemCmd offers {[o['value'] for o in options]}, the service accepts {words} (_SYSTEM_CMDS)"]
    return problems + [f"{o['value']} is labelled {o['label']!r}" for o in options if o["label"] != _SYSTEM_CMD_LABELS.get(_str(o["value"]))]


def _system_cmd_words(src_dir: Path) -> "list[str]":
    # The service's own words, in its order: `_SYSTEM_CMDS = const((...))` read by ast, a folded const() no import reaches.
    tree = ast.parse((src_dir / "asy_webserver_service.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and [ast.unparse(t) for t in node.targets] == ["_SYSTEM_CMDS"] and isinstance(node.value, ast.Call):
            words = ast.literal_eval(node.value.args[0])
            assert isinstance(words, tuple) and all(isinstance(w, str) for w in words), words
            return list(words)
    raise AssertionError("src/asy_webserver_service.py declares no _SYSTEM_CMDS = const((...))")


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_system_command_offers_every_service_word_in_order(repo_root: Path, src_dir: Path, device: str) -> None:
    problems = _system_cmd_problems(_generate(repo_root, src_dir, device), src_dir)
    assert not problems, problems


def test_a_service_word_the_command_does_not_offer_fails(tmp_path: Path, src_dir: Path) -> None:
    # The service gains a sixth word the definitions never offer: the page could not send it.
    src = Path(shutil.copytree(src_dir, tmp_path / "src"))
    service = src / "asy_webserver_service.py"
    text = service.read_text(encoding="utf-8")
    anchor = '_SYSTEM_CMDS = const(("reboot", "bootloader", "mempause", "resetconfig", "erasefram"))'
    assert text.count(anchor) == 1
    service.write_text(text.replace(anchor, anchor.replace('"erasefram"))', '"erasefram", "selftest"))')), encoding="utf-8")
    definitions = json.loads(json.dumps(definitions_for_toml(device_toml(DEVICE_NAMES[0]), src)))
    assert _system_cmd_problems(definitions, src), "a word _SYSTEM_CMDS gained passed unoffered"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_device_clock_follows_utc_time(repo_root: Path, src_dir: Path, device: str) -> None:
    fields = {f["key"]: f for f in _system_status_fields(repo_root, src_dir, device)}
    assert fields["UnixTime"] == {
        "key": "UnixTime", "label": "Device Clock", "unit": "s", "kind": "readonly",
        "description": "Unix time (UTC) when this poll was answered; every age on this site is computed against it.",
    }


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_command_and_the_error_reset_ask_before_they_are_sent(repo_root: Path, src_dir: Path, device: str) -> None:
    # The page asks before either, the API stays one command (owner, 2026-10-01: 'The API stays single command.').
    asking = [(section, group["key"], f["key"]) for section, group in _field_groups(_generate(repo_root, src_dir, device)) for f in _fields(group) if "confirm" in f]
    assert asking == [("system", "command", "SystemCmd"), ("status", "resetErrors", "ResetErrors")]
    assert all(f["confirm"] is True for _s, g in _field_groups(_generate(repo_root, src_dir, device)) for f in _fields(g) if "confirm" in f)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_site_default_decimals_follows_the_poll_interval(repo_root: Path, src_dir: Path, device: str) -> None:
    generated = _generate(repo_root, src_dir, device)
    keys = list(generated)
    # @tunable web.default_decimals = 2
    assert generated["defaultDecimals"] == 2
    assert keys.index("defaultDecimals") == keys.index("defaultPollIntervalMs") + 1


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_no_field_carries_a_stand_in_value(repo_root: Path, src_dir: Path, device: str) -> None:
    # A toggle whose state the GET cannot report renders unset; the definitions hold no default for it.
    assert '"defaultValue"' not in json.dumps(_generate(repo_root, src_dir, device))


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_maintenance_field_reads_its_instance_and_field_by_path(repo_root: Path, src_dir: Path, device: str) -> None:
    # GET /status nests each source's fields under its name; the key stays the flat, unique wire name.
    status = _section(_generate(repo_root, src_dir, device), "status")
    fields = [f for g in _groups(status) if g["key"] == "sensors" for f in _fields(g)]
    for f in fields:
        path = _strs(f.get("path", []))
        assert len(path) == 2 and "_".join(path) == f["key"], f
    sources = {_strs(f["path"])[0] for f in fields}
    model = build_model(device_toml(device), src_dir)
    expected = {spec.resolved_name for spec in model.instances.values() if spec.driver == "sgp40"} | ({"UARTLINK"} if any(spec.driver == "uart_link" for spec in model.instances.values()) else set())
    assert sources == expected


@pytest.mark.parametrize("device", _NOTIFICATION_DEVICES)
def test_the_notification_status_time_is_the_last_cycles_and_pause_time_reads_from_status(repo_root: Path, src_dir: Path, device: str) -> None:
    sections = {_str(s["key"]): s for s in _sections(_generate(repo_root, src_dir, device))}
    assert "notification" in sections, f"{device} declares a notification, yet its definitions have no notification section"
    status_fields = {_str(f["key"]): f for g in _groups(sections["status"]) if g["key"] == "notification" for f in _fields(g)}
    assert status_fields["TS"] == {
        "key": "TS", "label": "Last Cycle Time", "kind": "readonly", "format": "epoch",
        "description": "When the last notification cycle ran, whether or not it evaluated a signal (see Evaluation State).",
    }
    (pause,) = [f for g in _groups(sections["notification"]) if g["key"] == "pause" for f in _fields(g)]
    assert (pause["key"], pause["kind"], pause["statusPath"]) == ("PauseTime", "number", ["notification", "PauseTime"])


def _fields_by_key(definitions: "JsonDict") -> "dict[str, list[JsonDict]]":
    found: dict[str, list[JsonDict]] = {}
    for _section, group in _field_groups(definitions):
        for f in _fields(group):
            found.setdefault(_str(f["key"]), []).append(f)
    return found


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_page_keys_land_on_the_fields_their_tags_name(repo_root: Path, src_dir: Path, device: str) -> None:
    fields = _fields_by_key(_generate(repo_root, src_dir, device))
    assert [f["key"] for fs in fields.values() for f in fs if f.get("clearable")] == ["DNSFallback"]
    assert {f["key"]: f["ignoredWhenSet"] for fs in fields.values() for f in fs if "ignoredWhenSet" in f} == ({"Altitude": "AmbPres"} if "Altitude" in fields else {})
    for f in fields.get("TempOffset", []):
        if f.get("unit") == "K" and "resolution" in f:  # SCD30's, read in the chip's 0.01 degC tick
            assert (f["resolution"], f["decimals"]) == (0.01, 2)
    assert len([f for fs in fields.values() for f in fs if "resolution" in f]) == len([s for s in build_model(device_toml(device), src_dir).instances.values() if s.driver == "scd30"])


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_scd30_measurements_carry_their_datasheet_decimals(repo_root: Path, src_dir: Path, device: str) -> None:
    # CO2 repeats to 10 ppm, humidity to 0.1 %RH and temperature to 0.1 degC (SCD30 datasheet, Tables 1-3).
    for group in _groups(_section(_generate(repo_root, src_dir, device), "measurements")):
        if not _str(group["key"]).startswith("SCD30"):
            continue
        decimals = {_str(f["key"]): f.get("decimals") for f in _fields(group)}
        assert {key: decimals[key] for key in ("CO2", "Temp", "Hum", "WetBulb", "DewPoint")} == {"CO2": 0, "Temp": 1, "Hum": 1, "WetBulb": 1, "DewPoint": 1}


def _page_key_tag(*, resolution: "float | None" = None, decimals: "int | None" = None, clearable: bool = False) -> WebFieldTag:
    return WebFieldTag(field_name="X", section="sensors", submit_group="self", label="X", raw="# @web X", resolution=resolution, decimals=decimals, clearable=clearable)


@pytest.mark.parametrize(("resolution", "tag_decimals", "decimals"), [(0.1, None, 1), (0.01, None, 2), (5.0, None, 0), (0.01, 3, 3), (None, None, None)])
def test_a_number_fields_decimals_are_its_tags_else_its_resolutions(resolution: "float | None", tag_decimals: "int | None", decimals: "int | None") -> None:
    field = _build_field_def(_page_key_tag(resolution=resolution, decimals=tag_decimals), ("float", None, 0.0, 10.0, None), "fixture", Path("asy_x.py"))
    assert field.get("decimals") == decimals
    assert field.get("resolution") == resolution


@pytest.mark.parametrize(
    ("tag", "schema", "match", "rule"),
    [
        (_page_key_tag(clearable=True), ("int", 0, 0, 10, None), "but its kind is 'number', not string", "web.string-key-off-string"),
        (_page_key_tag(resolution=0.01), ("str", "x", 1, 32, None), "has resolution= but its kind is 'string', not number", "web.key-needs-number"),
        (_page_key_tag(resolution=0.01), ("bool", None, None, None, None), "has resolution= but its kind is 'toggle', not number", "web.key-needs-number"),
    ],
    ids=["clearable-on-a-number", "resolution-on-a-string", "resolution-on-a-toggle"],
)
def test_a_page_key_off_its_inferred_kind_fails_the_build(tag: WebFieldTag, schema: "tuple[object, object, object, object, object]", match: str, rule: str) -> None:
    with pytest.raises(BuildError, match=match) as caught:
        _build_field_def(tag, schema, "fixture", Path("asy_x.py"))
    _assert_rule(caught.value, rule)


def test_a_code_table_without_tones_carries_no_code_tones() -> None:
    tag = WebFieldTag(field_name="X", section="measurements", submit_group="self", label="X", raw="# @web X", kind="readonly", codes="FRCState")
    field = _build_field_def(tag, None, "fixture", Path("asy_x.py"))
    assert "codes" in field and "codeTones" not in field


# ---------------------------------------------------------------------------
# A string field's special value: the schema's sentinel, labelled by its tag's quoted special:
# ---------------------------------------------------------------------------

_PW_SCHEMA = ("str", "", 8, 63, "")  # the shape of asy_wifi_service.py's _VAL_PW: "" bypasses 8..63


def _string_tag(*special: "tuple[str, str]") -> WebFieldTag:
    return WebFieldTag(field_name="PW", section="networking", submit_group="identity", label="Wi-Fi Password", raw="# @web PW", special=special)


def test_a_string_fields_schema_special_is_emitted_with_its_tag_label() -> None:
    field = _build_field_def(_string_tag(('""', "Open network")), _PW_SCHEMA, "fixture", Path("asy_wifi_service.py"))
    assert (field["kind"], field["minLength"], field["maxLength"]) == ("string", 8, 63)
    assert field["specialValues"] == [{"value": "", "meaning": "Open network"}]


def test_a_string_field_without_a_schema_special_emits_none() -> None:
    field = _build_field_def(_string_tag(), ("str", "x", 1, 32, None), "fixture", Path("asy_x.py"))
    assert "specialValues" not in field


@pytest.mark.parametrize(
    ("special", "schema", "match", "rule"),
    [
        ((), _PW_SCHEMA, r"has a sentinel special value '' but no matching special:\"\"=", "web.special-unlabelled"),
        ((('""', "Open network"), ('"guest"', "Guest")), _PW_SCHEMA, r"declares special: value\(s\) \['guest'\] not in its ConfigSchema", "web.special-not-in-schema"),
        ((('""', "Open network"),), ("str", "x", 1, 32, None), r"declares special: value\(s\) \[''\] not in its ConfigSchema", "web.special-not-in-schema"),
        ((("open", "Open network"),), _PW_SCHEMA, "a string field's special: value is a quoted string", "web.string-special-unquoted"),
    ],
)
def test_a_string_fields_special_must_label_exactly_its_schema_sentinel(special: "tuple[tuple[str, str], ...]", schema: "tuple[object, ...]", match: str, rule: str) -> None:
    with pytest.raises(BuildError, match=match) as caught:
        _build_field_def(_string_tag(*special), (schema[0], schema[1], schema[2], schema[3], schema[4]), "fixture", Path("asy_wifi_service.py"))
    _assert_rule(caught.value, rule)


@pytest.mark.parametrize(("kind", "schema"), [("number", ("int", 0, 0, 10, None)), ("readonly", None)])
def test_a_quoted_special_off_a_string_field_fails_loud(kind: str, schema: "tuple[object, object, object, object, object] | None") -> None:
    tag = WebFieldTag(field_name="X", section="sensors", submit_group="self", label="X", raw="# @web X", kind=kind, special=(('"0"', "Zero"),))
    with pytest.raises(BuildError, match="a quoted special: value labels a string field only") as caught:
        _build_field_def(tag, schema, "fixture", Path("asy_x.py"))
    _assert_rule(caught.value, "web.quoted-special-off-string")


# ---------------------------------------------------------------------------
# Catalog-derived blocks equal their sources
# ---------------------------------------------------------------------------


def _live_codes(kind: str) -> "dict[str, str]":
    return {num: row["text"] for num, row in _CATALOG["codes"][kind].items() if not row.get("retired")}


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_errcount_codes_block_equals_the_catalogs_live_codes(repo_root: Path, src_dir: Path, device: str) -> None:
    groups = _errcount_groups(_generate(repo_root, src_dir, device))
    assert groups, f"{device} has no errcount group"
    for _section, group in groups:
        assert group["codes"] == {"E": _live_codes("E"), "W": _live_codes("W")}, group["key"]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_scd30_errcount_and_readiness_rows_match_the_catalog(repo_root: Path, src_dir: Path, device: str) -> None:
    # Each SCD30 lists its config store's logger beside its own, and FRCState names the catalog's readiness table.
    generated = _generate(repo_root, src_dir, device)
    keys = [_str(m["key"]) for _section, group in _errcount_groups(generated) for m in _objs(group["modules"])]
    scd30 = [k for k in keys if k.startswith("SCD30")]
    assert scd30, f"{device} lists no SCD30 errcount row - the check holds nothing"
    for name in scd30:
        assert keys.count(f"CFGMGR_{name}") == 1, name
    states = [f for _section, group in _field_groups(generated) for f in _fields(group) if f["key"] == "FRCState"]
    assert len(states) == len(scd30)
    for field in states:
        assert field["codes"] == {num: row["text"] for num, row in _CATALOG["status"]["FRCState"].items()}


def _tagged_code_tables(src_dir: Path) -> "dict[str, str]":
    # Field key -> the status table its `codes=` tag names, over every tagged src/ file.
    return {t.field_name: t.codes for p in sorted(src_dir.glob("*.py")) for t in parse_web_tags(p, "fixture", "x") if t.codes is not None}


# The Status page's own rows whose key is not their table's name; every other catalog row names its table by its key.
_STATUS_ROW_TABLES = {"State": "NotifyState"}


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_field_codes_table_equals_its_catalog_status_table(repo_root: Path, src_dir: Path, device: str) -> None:
    # A catalog row (the Status page's own fields) names its table by its key; a tagged field by codes=.
    tables = _CATALOG.get("status", {})
    named = _tagged_code_tables(src_dir)
    for _section, group in _field_groups(_generate(repo_root, src_dir, device)):
        for f in _fields(group):
            if "codes" in f:
                key = _str(f["key"])
                table = named.get(key, _STATUS_ROW_TABLES.get(key, key))
                assert table in tables, f"{f['key']} carries codes but the catalog has no status table {table!r}"
                assert f["codes"] == {num: row["text"] for num, row in tables[table].items()}, f["key"]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_code_tone_block_equals_its_catalog_tables_tones(repo_root: Path, src_dir: Path, device: str) -> None:
    # The page colours a code only where the catalog gives its table tones; text stays the cue either way.
    tables = _CATALOG.get("status", {})
    named = _tagged_code_tables(src_dir)
    for _section, group in _field_groups(_generate(repo_root, src_dir, device)):
        for f in _fields(group):
            key = _str(f["key"])
            table = named.get(key, _STATUS_ROW_TABLES.get(key, key)) if "codes" in f else None
            tones = {num: row["tone"] for num, row in tables[table].items() if "tone" in row} if table is not None else {}
            assert f.get("codeTones", {}) == tones, f["key"]


def test_every_codes_tag_names_a_present_table(src_dir: Path) -> None:
    missing = {field: table for field, table in _tagged_code_tables(src_dir).items() if table not in _CATALOG.get("status", {})}
    assert not missing, f"codes= tags naming no table in buildgen/error_catalog.json's status section: {missing}"


def test_a_codes_hint_naming_no_table_fails_the_build() -> None:
    tag = WebFieldTag(field_name="X", section="status", submit_group="system", label="X", raw="# @web X", kind="readonly", codes="NoSuchTable")
    with pytest.raises(BuildError, match="codes='NoSuchTable' names no status table") as caught:
        _build_field_def(tag, None, "fixture", Path("asy_x.py"))
    _assert_rule(caught.value, "web.codes-unknown-table")


def test_the_catalog_reads_the_same_under_any_locale(repo_root: Path) -> None:
    # The catalog holds non-ASCII text; read under an ASCII locale with UTF-8 mode off, it must still load.
    probe = "import sys; sys.path.insert(0, sys.argv[1]); from buildgen.definitions import _load_catalog; print(sorted(_load_catalog()['status']))"
    env = {"PATH": os.environ.get("PATH", ""), "LC_ALL": "C", "LANG": "C"}
    done = subprocess.run([sys.executable, "-I", "-X", "utf8=0", "-c", probe, str(repo_root)], env=env, capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr
    assert "ResetReason" in done.stdout


def test_the_mandatory_logger_names_are_read_from_their_files(tmp_path: Path, src_dir: Path) -> None:
    # Renaming a mandatory module's _NAME renames its errcount rows: the definitions keep no copy of it.
    patched_src = tmp_path / "src"
    shutil.copytree(src_dir, patched_src)
    for filename, old, new in (("asy_wifi_service.py", '_NAME = const("WIFI")', '_NAME = const("WLAN")'), ("asy_captive_dns.py", '_NAME = const("DNSSRV")', '_NAME = const("CAPDNS")')):
        text = (patched_src / filename).read_text(encoding="utf-8")
        assert old in text, f"{filename} no longer holds {old!r}"
        (patched_src / filename).write_text(text.replace(old, new, 1), encoding="utf-8")
    model = DeviceModel(device="fixture", path=Path("fixture.toml"), doc={"device": {"name": "fixture"}}, instances={}, construction_order=[])
    keys = {section: [m["key"] for _s, g in _errcount_groups(_read(generate_definitions(model, patched_src))) if _s == section for m in _objs(g["modules"])] for section in ("networking", "status")}
    assert keys["networking"] == ["CAPDNS"]
    assert {"WLAN", "CFGMGR_WLAN"} <= set(keys["status"])
    assert not {"WIFI", "CFGMGR_WIFI", "DNSSRV"} & set(keys["status"])


def test_a_sensor_the_registry_resolves_gets_its_cards_whatever_its_driver_name(src_dir: Path) -> None:
    # The registry's own classification (kind "sensor") decides the cards; no list of driver names does.
    info = DriverInfo(driver="co2probe", module="asy_scd30_driver", class_name="SCD30_Reader", kind="sensor", source_path=src_dir / "asy_scd30_driver.py", needs_setup=True)
    spec = InstanceSpec(driver="co2probe", name_ext="", fields={}, wiring={}, order_index=0, driver_info=info, resolved_name="CO2PROBE")
    model = DeviceModel(device="fixture", path=Path("fixture.toml"), doc={"device": {"name": "fixture"}}, instances={spec.key: spec}, construction_order=[spec.key])
    generated = _read(generate_definitions(model, src_dir))
    for section in ("measurements", "sensors"):
        assert [g["key"] for g in _groups(_section(generated, section))] == ["CO2PROBE"], section


@pytest.mark.parametrize("device", _NOTIFICATION_DEVICES)
def test_the_warn_fields_are_the_signal_catalogs(repo_root: Path, src_dir: Path, device: str) -> None:
    # Guard: each wired warn signal's threshold field carries buildgen.signals' values, in catalog order.
    model = build_model(device_toml(device), src_dir)
    notification = next((spec for spec in model.instances.values() if spec.driver == "notification"), None)
    assert notification is not None, f"{device} declares a notification the model does not build"
    fields = [f for g in _groups(_section(_generate(repo_root, src_dir, device), "notification")) for f in _fields(g) if _str(f["key"]).startswith("Warn")]
    expected = [
        {"key": s.name, "label": s.label, **({"unit": s.unit} if s.unit is not None else {}), "kind": "number", "min": s.min, "max": s.max, **({"float": True} if s.field_type == "float" else {})}
        for key, s in WARN_SIGNALS.items() if key in notification.wiring
    ]
    assert fields == expected


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_timestamp_is_an_epoch_with_no_unit(repo_root: Path, src_dir: Path, device: str) -> None:
    # An instant, not a duration: the page shows its age, so a seconds unit would mislabel it.
    stamps = [f for _section, group in _field_groups(_generate(repo_root, src_dir, device)) for f in _fields(group) if _str(f["key"]).endswith("TS") or f["key"] == "NTPLastSync"]
    assert stamps, f"{device} carries no timestamp field - the check found nothing to hold"
    wrong = [f["key"] for f in stamps if f.get("format") != "epoch" or "unit" in f]
    assert not wrong, f"timestamps without format epoch, or with a unit: {wrong}"


def _sgp_maintenance_keys(module_source: str) -> "set[str]":
    # The keys the generated module's SGP40 maintenance adapter(s) return.
    bodies = re.findall(r"async def _sgp_maintenance_status\w*\(\)[^\n]*\n((?:    .*\n)+)", module_source)
    assert bodies, "the generated module defines no _sgp_maintenance_status adapter - re-point this check"
    return {key for body in bodies for key in re.findall(r'"(\w+)":', body)}


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_sgp40_maintenance_fields_carry_both_special_values_and_the_adapters_keys(repo_root: Path, src_dir: Path, device: str) -> None:
    model = build_model(device_toml(device), src_dir)
    sgp40 = [spec for spec in model.instances.values() if spec.driver == "sgp40"]
    maintenance = [f for g in _groups(_section(_generate(repo_root, src_dir, device), "status")) if g["key"] == "sensors" for f in _fields(g)]
    if not sgp40:
        assert not [f["key"] for f in maintenance if _str(f["key"]).startswith("SGP40")], f"{device} has no sgp40 but lists its maintenance rows"
        return
    prefix = f"{sgp40[0].resolved_name}_"
    fields = {_str(f["key"]).removeprefix(prefix): f for f in maintenance if _str(f["key"]).startswith(prefix)}
    assert set(fields) == _sgp_maintenance_keys(_module_source(device_toml(device), src_dir, repo_root / "ext"))
    for name, f in fields.items():
        assert f["specialValues"] == [{"value": None, "meaning": "None since boot"}, {"value": 0, "meaning": "No timestamp"}], name


def test_each_sgp40_publishes_its_own_maintenance_rows_under_its_rest_identity(repo_root: Path, src_dir: Path, fixtures_dir: Path) -> None:
    # Two SGP40s: one adapter each, reading its own module-level instance (a bare `sgp40` names none,
    # so every /status read failed), and one row set each keyed <resolved_name>_<field>.
    toml_path = fixtures_dir / "multi_instance.toml"
    source = _module_source(toml_path, src_dir, repo_root / "ext")
    entries = dict(re.findall(r'\("(SGP40\w*)", (_sgp_maintenance_status\w*)\)', source))
    assert entries == {"SGP40_a": "_sgp_maintenance_status_sgp40_a", "SGP40_b": "_sgp_maintenance_status_sgp40_b"}
    for adapter in entries.values():
        var = adapter.removeprefix("_sgp_maintenance_status_")
        body = source.split(f"async def {adapter}()", 1)[1].split("\n\n", 1)[0]
        assert re.search(rf"^{var}: ", source, re.MULTILINE), f"{adapter} reads {var}, which the module never declares"
        assert f"await {var}.get_mem_status()" in body, body
    rows = [f for g in _groups(_section(_read(definitions_for_toml(toml_path, src_dir)), "status")) if g["key"] == "sensors" for f in _fields(g)]
    assert {_str(f["key"]) for f in rows} == {f"{name}_{key}" for name in entries for key in _sgp_maintenance_keys(source)}
    assert len({_str(f["label"]) for f in rows}) == len(rows), [f["label"] for f in rows]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_logger_has_one_errcount_row_and_dns_sits_on_networking(repo_root: Path, src_dir: Path, device: str) -> None:
    groups = _errcount_groups(_generate(repo_root, src_dir, device))
    rows = Counter(_str(m["key"]) for _section, g in groups for m in _objs(g["modules"]))
    assert not [key for key, count in rows.items() if count > 1], f"loggers listed in more than one errcount row: {rows}"
    assert [section for section, g in groups if any(m["key"] == "DNSSRV" for m in _objs(g["modules"]))] == ["networking"]


# The status sources the generated module registers, by the key GET /status publishes each under.
_STATUS_SOURCES = {"networking": "_networking_status", "system": "_system_status", "notification": "_notification_status"}


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_status_path_resolves_in_the_generated_status_source(repo_root: Path, src_dir: Path, device: str) -> None:
    # A field another route answers (PauseTime's live value) is read where GET /status publishes it.
    source = _module_source(device_toml(device), src_dir, repo_root / "ext")
    paths = [_strs(f["statusPath"]) for _section, group in _field_groups(_generate(repo_root, src_dir, device)) for f in _fields(group) if "statusPath" in f]
    for path in paths:
        assert len(path) == 2 and path[0] in _STATUS_SOURCES, path
        assert path[1] in _returned_keys(source, _STATUS_SOURCES[path[0]]), path
    has_notification = any(spec.driver == "notification" for spec in build_model(device_toml(device), src_dir).instances.values())
    assert paths == ([["notification", "PauseTime"]] if has_notification else [])


def _placed_fields(definitions: "JsonDict") -> "dict[tuple[str, str, str], JsonDict]":
    return {(section, _str(group["key"]), _str(f["key"])): f for section, group in _field_groups(definitions) for f in _fields(group)}


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_a_number_field_is_float_exactly_where_its_schema_is(repo_root: Path, src_dir: Path, device: str) -> None:
    # The client sends a fraction only where the server's schema takes one (C.16's int/float policy).
    model = build_model(device_toml(device), src_dir)
    placed = _placed_fields(_generate(repo_root, src_dir, device))
    checked = 0
    for path, spec in _tag_sources(model, src_dir):
        label = spec.label if spec is not None else path.stem
        schemas = extract_field_schemas(path, device=device, instance_label=label)
        for tag in parse_web_tags(path, device, label):
            f = placed.get(_tag_place(tag, spec)) if tag.hidden is None and tag.field_name in schemas else None
            if f is not None and f["kind"] == "number":
                assert (f.get("float") is True) == (schemas[tag.field_name][0] == "float"), f["key"]
                checked += 1
    assert checked, f"{device}: no schema-backed number field found - the check held nothing"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_field_shows_the_decimals_its_source_states(repo_root: Path, src_dir: Path, device: str) -> None:
    # The tag's decimals, else the digits its resolution needs, else the site default; a derived or default count
    # lies in 0..3, a tag's own is its source's decision (owner, 2026-10-02: 'derived or defined from the value
    # sourcing modules'). The API values stay unrounded: nothing here reaches the server.
    model = build_model(device_toml(device), src_dir)
    generated = _generate(repo_root, src_dir, device)
    default = _int(generated["defaultDecimals"])
    assert 0 <= default <= 3
    placed = _placed_fields(generated)
    tagged: set[tuple[str, str, str]] = set()
    for path, spec in _tag_sources(model, src_dir):
        for tag in parse_web_tags(path, device, spec.label if spec is not None else path.stem):
            place = _tag_place(tag, spec)
            if tag.hidden is not None or place not in placed:
                continue
            tagged.add(place)
            derived = resolution_decimals(tag.resolution) if tag.resolution is not None else None
            assert placed[place].get("decimals") == (tag.decimals if tag.decimals is not None else derived), place
            if tag.decimals is None:
                assert 0 <= _int(placed[place].get("decimals", default)) <= 3, place
    assert not [place for place, f in placed.items() if "decimals" in f and place not in tagged]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_identity_and_ntp_groups_carry_their_apply_labels(repo_root: Path, src_dir: Path, device: str) -> None:
    labels = {_str(g["key"]): g.get("submitLabel") for g in _groups(_section(_generate(repo_root, src_dir, device), "networking"))}
    assert (labels["identity"], labels["ntp"]) == ("Apply & Reconnect", "Apply & Resync")


def _radio_fields(src_dir: Path) -> "set[str]":
    # asy_wifi_service.py's `_RADIO_FIELDS = schema_names(<schemas>)`, the schemas resolved as buildgen.schema_ast reads them.
    tree = ast.parse((src_dir / "asy_wifi_service.py").read_text(encoding="utf-8"))
    consts = {n.targets[0].id: n.value for n in tree.body if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)}
    call = consts["_RADIO_FIELDS"]
    assert isinstance(call, ast.Call) and ast.unparse(call.func) == "schema_names", ast.unparse(call)
    schemas = _eval_literal(call.args[0], consts)
    assert isinstance(schemas, tuple)
    return {str(field[0]) for field in schemas if isinstance(field, tuple)}


def test_the_byte_bounded_fields_are_exactly_the_radio_fields(src_dir: Path) -> None:
    # The page counts UTF-8 bytes exactly where the server's radio check does (C.7.4): HotspotPW included.
    tags = parse_web_tags(src_dir / "asy_wifi_service.py", "fixture", "wifi")
    radio = _radio_fields(src_dir)
    assert "HotspotPW" in radio
    assert {t.field_name for t in tags if t.byte_length} == radio


# ---------------------------------------------------------------------------
# Shape validation - mirrors js/definitions.js's validateDefinitions() rule for rule, so a generated
# file is known to load without a Node round trip. Both read tests_scripts/definitions_shape_cases.json.
# ---------------------------------------------------------------------------

# validateDefinitions()'s own patterns and value sets (js/definitions.js): JS's \d is ASCII-only and
# its $ never matches before a trailing newline, hence [0-9] and fullmatch.
_SEMVER = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
_SUPPORTED_SCHEMA_MAJOR = int(SCHEMA_VERSION.split(".")[0])  # js/definitions.js's, pinned by test_definitions_js_mirrors.py
_MAX_POLL_INTERVAL_MS = 2**31 - 1  # setTimeout's ceiling; js/definitions.js's copy is pinned by test_definitions_js_mirrors.py
_POLL_GROUPS = ("live", "settings", "none")
_FIELD_KINDS = ("readonly", "number", "string", "enum", "toggle", "composite")
_FIELD_FORMATS = ("gmtimestruct", "epoch")
_STRING_SHAPES = ("hostLabel", "countryCode", "hostName", "ipv4List")
_CODE_TONES = ("good", "neutral", "warn")


def _is_number(value: object) -> "TypeGuard[int | float]":
    return isinstance(value, int | float) and not isinstance(value, bool)


def _is_string_map(value: object) -> bool:
    return isinstance(value, dict) and all(isinstance(v, str) for v in value.values())


def _is_poll_interval(value: object) -> bool:
    return _is_number(value) and 0 < value <= _MAX_POLL_INTERVAL_MS


def _is_decimals(value: object) -> bool:
    return _is_number(value) and float(value).is_integer() and 0 <= value <= _MAX_DECIMALS


def _is_step_list(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(step, str) and step for step in value)


def _duplicate(seen: "dict[str, int]", key: object, index: int, where: str) -> "list[str]":
    # A repeated key names both indices, as validateDefinitions()'s noteDuplicate() does.
    if not isinstance(key, str):
        return []
    if key in seen:
        return [f"{where}.key {key!r} duplicates [{seen[key]}]"]
    seen[key] = index
    return []


def _top_level_problems(defs: "JsonDict") -> "list[str]":
    problems = []
    version = defs.get("schemaVersion")
    if not isinstance(version, str) or not _SEMVER.fullmatch(version):
        problems.append("schemaVersion")
    elif int(version.split(".")[0]) != _SUPPORTED_SCHEMA_MAJOR:
        problems.append("schemaVersion major")
    device = defs.get("device")
    if not isinstance(device, dict) or not isinstance(device.get("id"), str):
        problems.append("device.id")
    if not isinstance(defs.get("landingSection"), str):
        problems.append("landingSection")
    if not _is_poll_interval(defs.get("defaultPollIntervalMs")):
        problems.append("defaultPollIntervalMs")
    if "defaultDecimals" in defs and not _is_decimals(defs["defaultDecimals"]):
        problems.append("defaultDecimals")
    return problems


def _code_hint_problems(f: "JsonDict", where: str) -> "list[str]":
    problems = []
    if "format" in f and (f["format"] not in _FIELD_FORMATS or f.get("kind") != "readonly"):
        problems.append(f"{where}.format")
    if "codes" in f and not _is_string_map(f["codes"]):
        problems.append(f"{where}.codes")
    if "codeTones" in f:
        codes = given if isinstance(given := f.get("codes"), dict) else {}
        tones = f["codeTones"]
        if not isinstance(tones, dict) or not all(code in codes and tone in _CODE_TONES for code, tone in tones.items()):
            problems.append(f"{where}.codeTones")
    special = f.get("specialValues")
    if "specialValues" in f and not (isinstance(special, list) and all(isinstance(s, dict) and "value" in s and isinstance(s.get("meaning"), str) for s in special)):
        problems.append(f"{where}.specialValues")
    return problems


def _value_hint_problems(f: "JsonDict", where: str, sibling_keys: "list[JsonValue]") -> "list[str]":
    problems = []
    kind = f.get("kind")
    if "path" in f:
        if not _is_step_list(f["path"]):
            problems.append(f"{where}.path")
        elif kind != "readonly":
            problems.append(f"{where}.path on a writable field")
    if "statusPath" in f and (not _is_step_list(f["statusPath"]) or kind not in ("readonly", "number")):
        problems.append(f"{where}.statusPath")
    if "decimals" in f and not _is_decimals(f["decimals"]):
        problems.append(f"{where}.decimals")
    resolution = f.get("resolution")
    if "resolution" in f and not (_is_number(resolution) and math.isfinite(resolution) and resolution > 0 and kind == "number"):
        problems.append(f"{where}.resolution")
    problems.extend(f"{where}.{key}" for key in ("byteLength", "clearable") if key in f and (not isinstance(f[key], bool) or kind != "string"))
    if "shape" in f and (f["shape"] not in _STRING_SHAPES or kind != "string"):
        problems.append(f"{where}.shape")
    if "alwaysExecuted" in f and not isinstance(f["alwaysExecuted"], bool):
        problems.append(f"{where}.alwaysExecuted")
    if "confirm" in f and (not isinstance(f["confirm"], bool) or kind not in ("enum", "toggle")):
        problems.append(f"{where}.confirm")
    sibling = f.get("ignoredWhenSet")
    if "ignoredWhenSet" in f and (not isinstance(sibling, str) or sibling == f.get("key") or sibling not in sibling_keys):
        problems.append(f"{where}.ignoredWhenSet")
    return problems


def _field_problems(f: "JsonDict", where: str, sibling_keys: "list[JsonValue]") -> "list[str]":
    problems = [f"{where}.{key}" for key in ("key", "label") if not isinstance(f.get(key), str)]
    if f.get("kind") not in _FIELD_KINDS:
        problems.append(f"{where}.kind")
    if f.get("kind") == "composite":
        sub_fields = f.get("subFields")
        problems += _fields_problems(sub_fields, f"{where}.subFields") if isinstance(sub_fields, list) else [f"{where}.subFields"]
    return problems + _code_hint_problems(f, where) + _value_hint_problems(f, where, sibling_keys)


def _fields_problems(fields: "list[JsonValue]", where: str) -> "list[str]":
    # A group's fields or a composite's sub-fields: each an object, each key once.
    problems: list[str] = []
    seen: dict[str, int] = {}
    keys = [f.get("key") if isinstance(f, dict) else None for f in fields]
    for index, f in enumerate(fields):
        if not isinstance(f, dict):
            problems.append(f"{where}[{index}] is not an object")
            continue
        problems += _duplicate(seen, f.get("key"), index, f"{where}[{index}]")
        problems += _field_problems(f, f"{where}[{index}]", keys)
    return problems


def _group_problems(g: "JsonDict", where: str, section: "JsonDict") -> "list[str]":
    problems = []
    if not isinstance(g.get("key"), str) or not isinstance(g.get("label"), str):
        problems.append(f"{where} key/label")
    if g.get("kind") == "errcount":
        modules = g.get("modules")
        if not isinstance(modules, list):
            problems.append(f"{where}.modules")
        else:
            problems += [f"{where}.modules[{i}]" for i, m in enumerate(modules) if not (isinstance(m, dict) and isinstance(m.get("key"), str) and isinstance(m.get("label"), str))]
        codes = g.get("codes", {"E": {}, "W": {}})
        if not isinstance(codes, dict) or not _is_string_map(codes.get("E")) or not _is_string_map(codes.get("W")):
            problems.append(f"{where}.codes")
        return problems
    fields = g.get("fields")
    if not isinstance(fields, list):
        return [*problems, f"{where}.fields"]
    rest = section.get("rest")
    if g.get("submit") is True and not (isinstance(rest, dict) and isinstance(rest.get("put"), str)):
        problems.append(f"{where} is writable but its section has no rest.put")
    return problems + _fields_problems(fields, f"{where}.fields")


def _section_problems(s: "JsonDict", where: str) -> "list[str]":
    problems = [f"{where}.{key}" for key in ("key", "label") if not isinstance(s.get(key), str)]
    rest = s.get("rest")
    if not isinstance(rest, dict) or not isinstance(rest.get("get"), str):
        problems.append(f"{where}.rest.get")
    if s.get("pollGroup") not in _POLL_GROUPS:
        problems.append(f"{where}.pollGroup")
    if "pollIntervalMs" in s and not _is_poll_interval(s["pollIntervalMs"]):
        problems.append(f"{where}.pollIntervalMs")
    groups = s.get("groups")
    if not isinstance(groups, list):
        return [*problems, f"{where}.groups"]
    seen: dict[str, int] = {}
    for index, g in enumerate(groups):
        if not isinstance(g, dict):
            problems.append(f"{where}.groups[{index}] is not an object")
            continue
        problems += _duplicate(seen, g.get("key"), index, f"{where}.groups[{index}]")
        problems += _group_problems(g, f"{where}.groups[{index}]", s)
    return problems


def _shape_problems(defs: object) -> "list[str]":
    # js/definitions.js's validateDefinitions(), rule for rule: empty means the document loads.
    if not isinstance(defs, dict):
        return ["definitions.json is not a JSON object"]
    problems = _top_level_problems(defs)
    sections = defs.get("sections")
    if not isinstance(sections, list) or not sections:
        return [*problems, "sections"]
    seen: dict[str, int] = {}
    for index, s in enumerate(sections):
        if not isinstance(s, dict):
            problems.append(f"sections[{index}] is not an object")
            continue
        problems += _duplicate(seen, s.get("key"), index, f"sections[{index}]")
        problems += _section_problems(s, f"sections[{index}]")
    if "landingSection" in defs and defs["landingSection"] not in seen:
        problems.append("landingSection matches no section")
    return problems


@pytest.mark.parametrize("case", _SHAPE_CASES, ids=[c["name"] for c in _SHAPE_CASES])
def test_shape_corpus_agrees(case: "JsonDict") -> None:
    # The same corpus tests_js/definitions-shape-corpus.test.js runs through the real validator.
    assert (_shape_problems(case["definitions"]) == []) == case["valid"], _shape_problems(case["definitions"])


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_generated_definitions_pass_shape_validation(repo_root: Path, src_dir: Path, device: str) -> None:
    assert _shape_problems(_generate(repo_root, src_dir, device)) == []


# ---------------------------------------------------------------------------
# Mandatory synthetic fixtures - proving generality beyond the real, hand-verified devices
# ---------------------------------------------------------------------------


def test_novel_combo_fixture_generates_distinct_scd30_groups(fixtures_dir: Path, src_dir: Path) -> None:
    generated = _read(definitions_for_toml(fixtures_dir / "novel_combo.toml", src_dir))
    scd30_groups = [g for g in _groups(_section(generated, "measurements")) if _str(g["key"]).startswith("SCD30")]
    assert {_str(g["key"]) for g in scd30_groups} == {"SCD30_primary", "SCD30_secondary"}
    labels = {_str(g["key"]): _str(g["label"]) for g in scd30_groups}
    assert labels["SCD30_primary"].endswith("(primary)")
    assert labels["SCD30_secondary"].endswith("(secondary)")


def test_novel_combo_fixture_only_wires_the_one_declared_warning_signal(fixtures_dir: Path, src_dir: Path) -> None:
    generated = _read(definitions_for_toml(fixtures_dir / "novel_combo.toml", src_dir))
    auto_group = next(g for g in _groups(_section(generated, "notification")) if not _str(g["key"]).startswith(("flash", "pause")))
    warn_keys = {_str(f["key"]) for f in _fields(auto_group) if _str(f["key"]).startswith("Warn")}
    assert warn_keys == {"WarnCO2"}


def test_multi_instance_fixture_generates_successfully(fixtures_dir: Path, src_dir: Path) -> None:
    generated = _read(definitions_for_toml(fixtures_dir / "multi_instance.toml", src_dir))
    assert _shape_problems(generated) == []


@pytest.mark.parametrize("bound", [b"\x00", 1j])
def test_a_schema_value_with_no_json_form_fails_the_build(bound: object) -> None:
    tag = WebFieldTag(field_name="X", section="sensors", submit_group="self", label="X", raw="# @web X")
    with pytest.raises(BuildError, match="which has no JSON form") as caught:
        _build_field_def(tag, ("int", 0, bound, 10, None), "fixture", Path("asy_x.py"))
    _assert_rule(caught.value, "schema.value-not-json")


@pytest.mark.parametrize(
    "tag",
    [
        WebFieldTag(field_name="X", section="sensors", submit_group="self", label="X", raw="# @web X", shape="hostLabel"),
        WebFieldTag(field_name="X", section="sensors", submit_group="self", label="X", raw="# @web X", byte_length=True),
    ],
    ids=["shape", "bytes"],
)
def test_a_string_key_off_a_string_field_fails_the_build(tag: WebFieldTag) -> None:
    with pytest.raises(BuildError, match="has bytes=, shape= or clearable= but its kind is 'number'") as caught:
        _build_field_def(tag, ("int", 0, 0, 10, None), "fixture", Path("asy_x.py"))
    _assert_rule(caught.value, "web.string-key-off-string")


# ---------------------------------------------------------------------------
# Failure paths: a minimal DeviceModel pointed at a deliberately mutated copy of one driver file,
# everything else from the real src/ tree - the project's malformed-fixture convention applied to
# a source file rather than a TOML document, since that is what this generator scans.
# ---------------------------------------------------------------------------


def _copy_driver_without(tmp_path: Path, src_dir: Path, filename: str, remove_line_containing: str) -> Path:
    original = (src_dir / filename).read_text(encoding="utf-8")
    lines = [line for line in original.splitlines(keepends=True) if remove_line_containing not in line]
    mutated = tmp_path / filename
    mutated.write_text("".join(lines), encoding="utf-8")
    return mutated


def _copy_driver_replacing(tmp_path: Path, src_dir: Path, filename: str, old: str, new: str) -> Path:
    original = (src_dir / filename).read_text(encoding="utf-8")
    assert old in original, f"{old!r} not found in {filename}"
    mutated = tmp_path / filename
    mutated.write_text(original.replace(old, new, 1), encoding="utf-8")
    return mutated


def _single_scd30_model(device: str, source_path: Path) -> DeviceModel:
    spec = InstanceSpec(
        driver="scd30", name_ext="", fields={}, wiring={}, order_index=0,
        driver_info=DriverInfo(driver="scd30", module="asy_scd30_driver", class_name="SCD30_Reader", kind="sensor", source_path=source_path, needs_setup=True),
        resolved_name="SCD30",
    )
    return DeviceModel(device=device, path=Path(f"{device}.toml"), doc={"device": {"name": device}}, instances={("scd30", ""): spec}, construction_order=[("scd30", "")])


def test_missing_web_group_tag_fails_loud(tmp_path: Path, src_dir: Path) -> None:
    mutated = _copy_driver_without(tmp_path, src_dir, "asy_scd30_driver.py", '# @web-group section=measurements submitGroup=self label="SCD30')
    model = _single_scd30_model("fixture", mutated)
    with pytest.raises(BuildError, match="no @web-group section=measurements") as caught:
        generate_definitions(model, src_dir)
    _assert_rule(caught.value, "web.instance-group-missing")


def test_a_schema_field_without_a_web_tag_fails_the_build(tmp_path: Path, src_dir: Path) -> None:
    mutated = _copy_driver_without(tmp_path, src_dir, "asy_scd30_driver.py", "# @web AmbPres section=sensors")
    model = _single_scd30_model("fixture", mutated)
    with pytest.raises(BuildError, match=r"schema field\(s\) \['AmbPres'\] have no @web tag") as caught:
        generate_definitions(model, src_dir)
    _assert_rule(caught.value, "web.schema-field-untagged")


def test_an_unreadable_schema_names_its_device_and_instance(tmp_path: Path, src_dir: Path) -> None:
    mutated = tmp_path / "asy_scd30_driver.py"
    mutated.write_text((src_dir / "asy_scd30_driver.py").read_text(encoding="utf-8") + '_VAL_BROKEN = const((("X", "int", 0, 0, _NO_SUCH_BOUND, None),))\n', encoding="utf-8")
    with pytest.raises(BuildError, match="_VAL_BROKEN") as caught:
        generate_definitions(_single_scd30_model("fixture", mutated), src_dir)
    assert (caught.value.device, caught.value.instance) == ("fixture", "scd30")
    _assert_rule(caught.value, "schema.unreadable")


def test_a_hidden_schema_field_stays_off_the_website(tmp_path: Path, src_dir: Path) -> None:
    # A schema field tagged hidden= stays off the page; the rest of the card still shows.
    original = (src_dir / "asy_scd30_driver.py").read_text(encoding="utf-8")
    line = next(line for line in original.splitlines(keepends=True) if line.startswith("# @web FRCWindow section=sensors"))
    mutated = tmp_path / "asy_scd30_driver.py"
    mutated.write_text(original.replace(line, '# @web FRCWindow hidden="a test keeps it off"\n', 1), encoding="utf-8")
    generated = _read(generate_definitions(_single_scd30_model("fixture", mutated), src_dir))
    sensors_fields = {_str(f["key"]) for g in _groups(_section(generated, "sensors")) for f in _fields(g)}
    assert "FRCWindow" not in sensors_fields
    assert "MeasInterval" in sensors_fields


def test_a_field_ignored_while_a_hidden_or_absent_sibling_is_set_fails_the_build(tmp_path: Path, src_dir: Path) -> None:
    # The page warns from the sibling's value, so the sibling must be on the page beside it.
    original = (src_dir / "asy_scd30_driver.py").read_text(encoding="utf-8")
    line = next(line for line in original.splitlines(keepends=True) if line.startswith("# @web AmbPres section=sensors"))
    for replacement in ('# @web AmbPres hidden="a test keeps it off"\n', line.replace("section=sensors", "section=measurements kind=readonly")):
        mutated = tmp_path / "asy_scd30_driver.py"
        mutated.write_text(original.replace(line, replacement, 1), encoding="utf-8")
        with pytest.raises(BuildError, match="ignoredWhenSet='AmbPres', which names no other field of its group") as caught:
            generate_definitions(_single_scd30_model("fixture", mutated), src_dir)
        _assert_rule(caught.value, "web.ignored-when-set-unknown")


def test_every_src_schema_field_is_tagged_or_hidden(src_dir: Path) -> None:
    # Every src/ file, a module no device includes too: each schema field has a @web tag, hidden= included.
    problems: list[str] = []
    for path in sorted(src_dir.glob("*.py")):
        try:
            _DriverTags(path, "scan", path.stem)
        except BuildError as e:
            problems.append(str(e))
    assert not problems, "\n".join(problems)


def test_missing_special_label_for_an_enum_schema_value_fails_loud(tmp_path: Path, src_dir: Path) -> None:
    mutated = _copy_driver_replacing(tmp_path, src_dir, "asy_bmp3xx_driver.py", ' special:127="127"', "")
    spec = InstanceSpec(
        driver="bmp3xx", name_ext="", fields={}, wiring={}, order_index=0,
        driver_info=DriverInfo(driver="bmp3xx", module="asy_bmp3xx_driver", class_name="BMP3XX_Reader", kind="sensor", source_path=mutated, needs_setup=True),
        resolved_name="BMP3XX",
    )
    model = DeviceModel(device="fixture", path=Path("fixture.toml"), doc={"device": {"name": "fixture"}}, instances={("bmp3xx", ""): spec}, construction_order=[("bmp3xx", "")])
    with pytest.raises(BuildError, match="no matching special:127") as caught:
        generate_definitions(model, src_dir)
    _assert_rule(caught.value, "web.special-unlabelled")


def test_duplicate_mandatory_group_across_two_files_fails_loud(tmp_path: Path, src_dir: Path) -> None:
    # asy_ntp_client.py deliberately never declares its own @web-group for section=system
    # submitGroup=settings (asy_system_service.py is the sole owner) - inject a second declaration to
    # prove the cross-file collision check actually runs.
    ntp_original = (src_dir / "asy_ntp_client.py").read_text(encoding="utf-8")
    mutated_ntp = tmp_path / "asy_ntp_client.py"
    mutated_ntp.write_text(
        ntp_original.replace(
            "# @web GMTOffset section=system submitGroup=settings",
            '# @web-group section=system submitGroup=settings label="Duplicate"\n# @web GMTOffset section=system submitGroup=settings',
            1,
        ),
        encoding="utf-8",
    )
    model = DeviceModel(device="fixture", path=Path("fixture.toml"), doc={"device": {"name": "fixture"}}, instances={}, construction_order=[])

    def _generate_with_patched_ntp() -> JsonDict:
        # _system_section() resolves asy_ntp_client.py by a fixed path under src_dir - point it at
        # a src_dir where only that one file differs, mirroring every other file from the real tree.
        patched_src = tmp_path / "src"
        patched_src.mkdir()
        for existing in src_dir.glob("*.py"):
            (patched_src / existing.name).write_bytes(existing.read_bytes())
        (patched_src / "asy_ntp_client.py").write_bytes(mutated_ntp.read_bytes())
        return generate_definitions(model, patched_src)

    with pytest.raises(BuildError, match="more than one @web-group") as caught:
        _generate_with_patched_ntp()
    _assert_rule(caught.value, "web.group-declared-twice")


def test_web_tag_with_no_schema_and_no_kind_override_fails_loud(tmp_path: Path, src_dir: Path) -> None:
    # ContMeas has no _VAL_* entry; drop its synthetic FieldSchema and its kind=toggle override too, and
    # it has neither a schema-derived field_type nor an explicit kind to fall back on.
    without_schema = _copy_driver_without(tmp_path, src_dir, "asy_scd30_driver.py", "_CONT_MEAS_FIELD: ")
    mutated = _copy_driver_replacing(tmp_path, tmp_path, "asy_scd30_driver.py", " kind=toggle", "")
    assert without_schema == mutated
    model = _single_scd30_model("fixture", mutated)
    with pytest.raises(BuildError, match="no matching ConfigSchema constant and no explicit kind") as caught:
        generate_definitions(model, src_dir)
    _assert_rule(caught.value, "web.kind-unresolved")


def test_web_tag_kind_enum_with_no_discrete_schema_choice_set_fails_loud(tmp_path: Path, src_dir: Path) -> None:
    # Same freestanding ContMeas field, forced to kind=enum instead of dropped entirely - _enum_field()
    # needs a tuple/list `special` from the schema, and ContMeas's synthetic bool schema has none.
    mutated = _copy_driver_replacing(tmp_path, src_dir, "asy_scd30_driver.py", "kind=toggle", "kind=enum")
    model = _single_scd30_model("fixture", mutated)
    with pytest.raises(BuildError, match="kind=enum but its ConfigSchema has no discrete choice set") as caught:
        generate_definitions(model, src_dir)
    _assert_rule(caught.value, "web.enum-without-choices")


def test_web_tag_declares_extra_special_label_not_in_schema_choice_set_fails_loud(tmp_path: Path, src_dir: Path) -> None:
    # The reverse of the missing-label test: every schema choice already has a matching special:
    # label, so adding one for a value the choice set does not contain is the only way to reach
    # the "declares special: option(s) ... not present" branch.
    mutated = _copy_driver_replacing(tmp_path, src_dir, "asy_bmp3xx_driver.py", ' special:127="127"', ' special:127="127" special:999="Extra"')
    spec = InstanceSpec(
        driver="bmp3xx", name_ext="", fields={}, wiring={}, order_index=0,
        driver_info=DriverInfo(driver="bmp3xx", module="asy_bmp3xx_driver", class_name="BMP3XX_Reader", kind="sensor", source_path=mutated, needs_setup=True),
        resolved_name="BMP3XX",
    )
    model = DeviceModel(device="fixture", path=Path("fixture.toml"), doc={"device": {"name": "fixture"}}, instances={("bmp3xx", ""): spec}, construction_order=[("bmp3xx", "")])
    with pytest.raises(BuildError, match=r"declares special: option\(s\) \['999'\] not present") as caught:
        generate_definitions(model, src_dir)
    _assert_rule(caught.value, "web.special-not-in-schema")


def test_web_tag_schema_sentinel_value_with_no_matching_special_label_fails_loud(tmp_path: Path, src_dir: Path) -> None:
    # AmbPres's ConfigSchema declares a scalar sentinel rather than a choice set, documented by
    # its own special:0= tag entry. Drop that one entry and the sentinel has nothing left to
    # explain it.
    mutated = _copy_driver_replacing(tmp_path, src_dir, "asy_scd30_driver.py", ' special:0="Compensation off / use Altitude"', "")
    model = _single_scd30_model("fixture", mutated)
    with pytest.raises(BuildError, match=r"has a sentinel special value 0 but no matching special:0") as caught:
        generate_definitions(model, src_dir)
    _assert_rule(caught.value, "web.special-unlabelled")


def test_an_sgp40_without_maintenance_tags_fails_the_build(tmp_path: Path, src_dir: Path) -> None:
    mutated = _copy_driver_without(tmp_path, src_dir, "asy_sgp40_driver.py", "section=status submitGroup=maintenance")
    info = DriverInfo(driver="sgp40", module="asy_sgp40_driver", class_name="SGP40_Reader", kind="sensor", source_path=mutated, needs_setup=True)
    spec = InstanceSpec(driver="sgp40", name_ext="", fields={}, wiring={}, order_index=0, driver_info=info, resolved_name="SGP40")
    model = DeviceModel(device="fixture", path=Path("fixture.toml"), doc={"device": {"name": "fixture"}}, instances={spec.key: spec}, construction_order=[spec.key])
    with pytest.raises(BuildError, match="no @web section=status submitGroup=maintenance tag found") as caught:
        generate_definitions(model, src_dir)
    _assert_rule(caught.value, "web.maintenance-tag-missing")


def test_mandatory_group_never_declared_anywhere_fails_loud(tmp_path: Path, src_dir: Path) -> None:
    # _mandatory_group()'s "none declaring" branch, distinct from the "declared twice" one above.
    # asy_system_service.py is the sole owner of that group, so dropping it rather than duplicating
    # it leaves no scanned file declaring the mandatory group at all.
    patched_src = tmp_path / "src"
    patched_src.mkdir()
    for existing in src_dir.glob("*.py"):
        (patched_src / existing.name).write_bytes(existing.read_bytes())
    mutated = _copy_driver_without(tmp_path, src_dir, "asy_system_service.py", '# @web-group section=system submitGroup=settings label="System Settings"')
    (patched_src / "asy_system_service.py").write_bytes(mutated.read_bytes())
    model = DeviceModel(device="fixture", path=Path("fixture.toml"), doc={"device": {"name": "fixture"}}, instances={}, construction_order=[])
    with pytest.raises(BuildError, match=r"no @web-group tag declares section='system' submitGroup='settings' in any scanned file") as caught:
        generate_definitions(model, patched_src)
    _assert_rule(caught.value, "web.group-undeclared")


def test_mandatory_group_declared_but_no_fields_reference_it_fails_loud(tmp_path: Path, src_dir: Path) -> None:
    # _mandatory_group()'s "declared but empty" branch: the @web-group tag survives while every field tag
    # turns hidden=, so no field references notification/autoConfig and each schema field stays tagged.
    # A synthetic notification instance: only a model with one reaches that group.
    original = (src_dir / "asy_notification_service.py").read_text(encoding="utf-8")
    lines = [re.sub(r"^# @web (\w+) .*$", r'# @web \1 hidden="test"', line) for line in original.splitlines(keepends=True)]
    mutated = tmp_path / "asy_notification_service.py"
    mutated.write_text("".join(lines), encoding="utf-8")
    spec = InstanceSpec(
        driver="notification", name_ext="", fields={}, wiring={}, order_index=0, resolved_name="NOTIFY",  # errcount rows are per instance now, so this must be filled as validate.py always fills it
        driver_info=DriverInfo(driver="notification", module="asy_notification_service", class_name="NotificationService", kind="service", source_path=mutated, needs_setup=True),
    )
    model = DeviceModel(device="fixture", path=Path("fixture.toml"), doc={"device": {"name": "fixture"}}, instances={("notification", ""): spec}, construction_order=[("notification", "")])
    with pytest.raises(BuildError, match=r"section='notification' submitGroup='autoConfig' has an @web-group declaration but no @web field tags reference it") as caught:
        generate_definitions(model, src_dir)
    _assert_rule(caught.value, "web.group-without-fields")


def test_resolved_key_fails_loud_if_resolved_name_still_unset() -> None:
    # _resolved_key()'s own invariant guard - buildgen.validate._resolve_instances()
    # always sets resolved_name before definitions generation ever runs on a real model.
    from buildgen.definitions import _resolved_key

    spec = InstanceSpec(driver="scd30", name_ext="", fields={}, wiring={}, order_index=0)  # resolved_name defaults to None
    with pytest.raises(BuildInternalError, match="resolved_name unresolved before definitions generation"):
        _resolved_key(spec, "fixture")


def test_measurements_and_sensors_sections_fails_loud_if_driver_info_still_unset() -> None:
    # _measurements_and_sensors_sections()'s own invariant guard - same
    # always-resolved-by-validate.py reasoning as _resolved_key() above.
    from buildgen.definitions import _measurements_and_sensors_sections

    spec = InstanceSpec(driver="scd30", name_ext="", fields={}, wiring={}, order_index=0, resolved_name="SCD30")  # driver_info defaults to None
    model = DeviceModel(device="fixture", path=Path("fixture.toml"), doc={"device": {"name": "fixture"}}, instances={("scd30", ""): spec}, construction_order=[("scd30", "")])
    with pytest.raises(BuildInternalError, match="driver_info unresolved before definitions generation"):
        _measurements_and_sensors_sections(model, {})


def test_notification_section_fails_loud_if_driver_info_still_unset() -> None:
    # _notification_section()'s own invariant guard, same reasoning as above.
    from buildgen.definitions import _notification_section

    spec = InstanceSpec(driver="notification", name_ext="", fields={}, wiring={}, order_index=0)  # driver_info defaults to None
    model = DeviceModel(device="fixture", path=Path("fixture.toml"), doc={"device": {"name": "fixture"}}, instances={("notification", ""): spec}, construction_order=[("notification", "")])
    with pytest.raises(BuildInternalError, match="driver_info unresolved before definitions generation"):
        _notification_section(model, {}, {"notification"})


def test_no_notification_instance_omits_notification_section(src_dir: Path) -> None:
    model = DeviceModel(device="fixture", path=Path("fixture.toml"), doc={"device": {"name": "fixture"}}, instances={}, construction_order=[])
    generated = _read(generate_definitions(model, src_dir))
    assert "notification" not in {_str(s["key"]) for s in _sections(generated)}
    assert {_str(s["key"]) for s in _sections(generated)} == {"measurements", "sensors", "networking", "system", "status"}


# ---------------------------------------------------------------------------
# CLI (scripts/build_website.sh's own build-time invocation, and manual use) -
# mirrors test_buildgen_generate.py's own CLI coverage.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("toml", [*DEVICE_NAMES, "multi_instance"])
def test_cli_output_equals_the_graph_ordered_build(repo_root: Path, src_dir: Path, fixtures_dir: Path, tmp_path: Path, toml: str) -> None:
    # The CLI and the build agree on group order: both order sensor cards by the construction graph,
    # which the multi-instance fixture is the one input to make visible.
    toml_path = device_toml(toml) if toml in DEVICE_NAMES else fixtures_dir / f"{toml}.toml"
    out_file = tmp_path / "definitions.json"
    assert main([str(toml_path), "--out", str(out_file)]) == 0
    model = build_model(toml_path, src_dir)
    build_construction_order(model)
    assert json.loads(out_file.read_text(encoding="utf-8")) == json.loads(json.dumps(generate_definitions(model, src_dir)))


def test_definitions_refuse_a_model_that_skipped_the_construction_order(src_dir: Path) -> None:
    # Falling back to TOML order would silently reorder the cards; a caller that skipped the graph fails.
    model = _single_scd30_model("fixture", src_dir / "asy_scd30_driver.py")
    model.construction_order = []
    with pytest.raises(BuildInternalError, match="construction order unresolved before definitions generation"):
        generate_definitions(model, src_dir)


def test_cli_prints_to_stdout_when_out_is_omitted(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([str(device_toml(DEVICE_NAMES[0]))])
    assert exit_code == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["device"]["id"] == DEVICE_NAMES[0]


def _one_line_error(capsys: pytest.CaptureFixture[str]) -> str:
    # A user error prints one line - what, where, the fix - and no traceback (SPECIFICATION.md L.5).
    err = capsys.readouterr().err
    assert "Traceback" not in err, err
    assert err.count("\n") == 1 and err.startswith("buildgen: "), err
    assert " - fix: " in err, err
    return err


def test_cli_reports_a_build_error_and_exits_nonzero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(tmp_path / "no-such-device.toml")]) == 1
    assert _one_line_error(capsys).startswith("buildgen: [no-such-device] ")


def test_cli_reports_a_definitions_error_in_one_line(tmp_path: Path, src_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    patched_src = tmp_path / "src"
    shutil.copytree(src_dir, patched_src)
    system = patched_src / "asy_system_service.py"
    text = system.read_text(encoding="utf-8")
    line = next(line for line in text.splitlines(keepends=True) if line.startswith("# @web-group section=system submitGroup=settings "))
    system.write_text(text.replace(line, "", 1), encoding="utf-8")
    assert main([str(device_toml(DEVICE_NAMES[0])), "--src-dir", str(patched_src)]) == 1
    assert "no @web-group tag declares section='system'" in _one_line_error(capsys)


def test_cli_reports_an_unwritable_output_in_one_line(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "no-such-dir" / "definitions.json"
    assert main([str(device_toml(DEVICE_NAMES[0])), "--out", str(out)]) == 1
    assert f"cannot write {out}" in _one_line_error(capsys)
    assert not out.parent.exists()


def test_cli_never_leaves_a_partial_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    # The file is written beside the target and renamed over it: a failed rename keeps the old file and no temporary.
    out = tmp_path / "definitions.json"
    out.write_text("old", encoding="utf-8")

    def refuse(_src: object, _dst: object) -> None:
        raise PermissionError(13, "injected for the rename")

    monkeypatch.setattr("os.replace", refuse)
    assert main([str(device_toml(DEVICE_NAMES[0])), "--out", str(out)]) == 1
    assert "injected for the rename" in _one_line_error(capsys)
    assert out.read_text(encoding="utf-8") == "old"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["definitions.json"]
