"""Tests for buildgen.definitions (SPECIFICATION.md Part H.5/H.5.1): every tagged field lands once in its group,
every device's output passes the shared shape corpus, and the catalog-derived blocks equal their sources."""

import ast
import copy
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, TypeGuard

import pytest
from _devices import DEVICE_NAMES, device_toml

from buildgen.definitions import SCHEMA_VERSION, _build_field_def, _DriverTags, definitions_for_toml, generate_definitions, main
from buildgen.driver_registry import DriverInfo
from buildgen.errors import BuildError, BuildInternalError
from buildgen.generate import generate_device
from buildgen.graph import build_construction_order
from buildgen.jsontypes import JsonDict
from buildgen.model import DeviceModel, InstanceSpec
from buildgen.schema_ast import _eval_literal
from buildgen.signals import WARN_SIGNALS
from buildgen.validate import build_model
from buildgen.version import WEBSITE_VERSION
from buildgen.web_tag import _MAX_DECIMALS, SELF_GROUP, WebFieldTag, parse_web_tags

BMP3XX_DEVICES = {"dev", "wozi"}
ISL29125_DEVICES = {"dev"}

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CATALOG = json.loads((_REPO_ROOT / "buildgen" / "error_catalog.json").read_text())
_SHAPE_CASES = json.loads((_REPO_ROOT / "tests_scripts" / "definitions_shape_cases.json").read_text())
# The files every device's mandatory networking/system groups are tagged in; instance files come from
# the model (each instance's driver_info.source_path).
_MANDATORY_TAG_FILES = ("asy_wifi_service.py", "asy_ntp_client.py", "asy_system_service.py")


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


@pytest.fixture
def fixtures_dir(repo_root: Path) -> Path:
    return repo_root / "tests_scripts" / "buildgen_fixtures"


def _generate(repo_root: Path, src_dir: Path, device: str) -> "dict[str, Any]":
    return _read(definitions_for_toml(repo_root / "devices" / f"{device}.toml", src_dir))


def _read(definitions: JsonDict) -> "dict[str, Any]":
    # The generated definitions as the page reads them: through JSON, which every value must survive.
    parsed: dict[str, Any] = json.loads(json.dumps(definitions))
    return parsed


def _field_groups(definitions: "dict[str, Any]") -> "list[tuple[str, dict[str, Any]]]":
    # (section key, group) for every field group - errcount groups carry modules, not fields.
    return [(s["key"], g) for s in definitions["sections"] for g in s["groups"] if "fields" in g]


def _errcount_groups(definitions: "dict[str, Any]") -> "list[tuple[str, dict[str, Any]]]":
    return [(s["key"], g) for s in definitions["sections"] for g in s["groups"] if g.get("kind") == "errcount"]


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


def _hidden_problems(model: DeviceModel, src_dir: Path, definitions: "dict[str, Any]") -> "list[str]":
    # A hidden field shows in none of its file's groups: an instance's own cards and maintenance rows, or a mandatory file's sections.
    problems: list[str] = []
    for path, spec in _tag_sources(model, src_dir):
        hidden = {tag.field_name for tag in parse_web_tags(path, model.device, spec.label if spec is not None else path.stem) if tag.hidden is not None}
        for section in definitions["sections"]:
            for group in section["groups"]:
                own = group["key"] == spec.resolved_name if spec is not None else section["key"] in {"networking", "system"}
                keys = {f["key"] for f in group.get("fields", [])}
                shown = (keys & hidden if own else set()) | (keys & {f"{spec.resolved_name}_{name}" for name in hidden} if spec is not None else set())
                problems += [f"{path.name}: hidden {key} shown in {section['key']}/{group['key']}" for key in sorted(shown)]
    return problems


def _tag_placement_problems(expected: "Counter[tuple[str, str, str, str, str | None]]", definitions: "dict[str, Any]") -> "list[str]":
    # Every generated field whose key some tag of its section names, counted against where the tags put it.
    tagged = {(section, key) for section, _group, key, _label, _unit in expected}
    actual: Counter[tuple[str, str, str, str, str | None]] = Counter(
        (section, group["key"], f["key"], f["label"], f.get("unit"))
        for section, group in _field_groups(definitions)
        for f in group["fields"]
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
    _section, group = next((s, g) for s, g in _field_groups(dropped) if g["fields"] and g["key"] != "build")
    removed = group["fields"].pop(0)
    assert _tag_placement_problems(expected, dropped), f"dropping {removed['key']} went unnoticed"
    duplicated = copy.deepcopy(generated)
    _section, group = next((s, g) for s, g in _field_groups(duplicated) if g["fields"] and g["key"] != "build")
    group["fields"].append(dict(group["fields"][0]))
    assert _tag_placement_problems(expected, duplicated), "a duplicated field went unnoticed"


def test_the_hidden_oracle_bites(repo_root: Path, src_dir: Path) -> None:
    # A device with an instance whose file hides a field: that field planted in its card, or as its maintenance row, is found.
    for device in DEVICE_NAMES:
        model = build_model(device_toml(device), src_dir)
        spec = next((s for s in model.instances.values() if s.driver_info is not None and any(t.hidden for t in parse_web_tags(s.driver_info.source_path, device, s.label))), None)
        if spec is not None:
            break
    else:
        pytest.skip("no device has an instance with a hidden= field")
    assert spec.driver_info is not None
    name = next(t.field_name for t in parse_web_tags(spec.driver_info.source_path, device, spec.label) if t.hidden)
    generated = _generate(repo_root, src_dir, device)
    assert _hidden_problems(model, src_dir, generated) == []
    for key in (name, f"{spec.resolved_name}_{name}"):
        planted = copy.deepcopy(generated)
        _section, group = next((s, g) for s, g in _field_groups(planted) if g["key"] == (spec.resolved_name if key == name else "sensors"))
        group["fields"].append({"key": key, "label": key, "kind": "readonly"})
        assert _hidden_problems(model, src_dir, planted), f"a hidden {key} went unnoticed"


# ---------------------------------------------------------------------------
# Per-device structural variation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_bmp3xx_group_presence_matches_device_instance_set(repo_root: Path, src_dir: Path, device: str) -> None:
    generated = _generate(repo_root, src_dir, device)
    sensors_section = next(s for s in generated["sections"] if s["key"] == "sensors")
    group_keys = {g["key"] for g in sensors_section["groups"]}
    if device in BMP3XX_DEVICES:
        assert "BMP3XX" in group_keys
    else:
        assert "BMP3XX" not in group_keys


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_isl29125_group_presence_matches_device_instance_set(repo_root: Path, src_dir: Path, device: str) -> None:
    generated = _generate(repo_root, src_dir, device)
    sensors_section = next(s for s in generated["sections"] if s["key"] == "sensors")
    group_keys = {g["key"] for g in sensors_section["groups"]}
    if device in ISL29125_DEVICES:
        assert "ISL29125" in group_keys
    else:
        assert "ISL29125" not in group_keys


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_real_device_has_all_six_sections(repo_root: Path, src_dir: Path, device: str) -> None:
    generated = _generate(repo_root, src_dir, device)
    assert {s["key"] for s in generated["sections"]} == {"measurements", "sensors", "networking", "system", "status", "notification"}


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
    status = next(s for s in generated["sections"] if s["key"] == "status")
    system_group = next(g for g in status["groups"] if g["key"] == "system")
    assert not any(f["key"] == "FirmwareVersion" for f in system_group["fields"])


def _returned_keys(module_source: str, function: str) -> "list[str]":
    # The literal keys of the dict a generated status source returns.
    fn = next(n for n in ast.walk(ast.parse(module_source)) if isinstance(n, ast.AsyncFunctionDef) and n.name == function)
    returned = next(n.value for n in ast.walk(fn) if isinstance(n, ast.Return))
    assert isinstance(returned, ast.Dict), f"{function}() returns no dict literal"
    return [k.value for k in returned.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_each_status_group_lists_the_keys_its_generated_source_returns(repo_root: Path, src_dir: Path, device: str) -> None:
    source = generate_device(device_toml(device), src_dir, repo_root / "ext").module_source
    status = next(s for s in _generate(repo_root, src_dir, device)["sections"] if s["key"] == "status")
    groups = {g["key"]: g for g in status["groups"]}
    for key, function in (("networking", "_networking_status"), ("system", "_system_status"), ("notification", "_notification_status")):
        if key not in groups:
            assert f"async def {function}(" not in source, f"{function}() is generated but no status group lists it"
            continue
        assert sorted(f["key"] for f in groups[key]["fields"]) == sorted(_returned_keys(source, function)), key


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_networking_status_carries_the_address_once_and_says_what_the_link_counts(repo_root: Path, src_dir: Path, device: str) -> None:
    status = next(s for s in _generate(repo_root, src_dir, device)["sections"] if s["key"] == "status")
    fields = {f["key"]: f for f in next(g for g in status["groups"] if g["key"] == "networking")["fields"]}
    assert "IP" not in fields
    assert "IPv4" in fields
    assert fields["Connected"]["description"] == "True while the Wi-Fi link is up, hotspot included."
    assert fields["WifiUptime"]["description"] == "Seconds the Wi-Fi link has been up, hotspot included; 0 while it is down."


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_networking_status_lists_the_drop_window_and_the_wifi_snapshot_time(repo_root: Path, src_dir: Path, device: str) -> None:
    status = next(s for s in _generate(repo_root, src_dir, device)["sections"] if s["key"] == "status")
    fields = {f["key"]: f for f in next(g for g in status["groups"] if g["key"] == "networking")["fields"]}
    assert fields["HTTPDropped"] == {"key": "HTTPDropped", "label": "Dropped Connections", "kind": "readonly", "description": "Web connections dropped in the last 24 hours, hourly resolution."}
    assert fields["WifiTS"] == {"key": "WifiTS", "label": "Wi-Fi Status Time", "kind": "readonly", "format": "epoch"}


# GET /status's system keys in the order the generated _system_status() publishes them; MemPaused only with FRAM.
_SYSTEM_STATUS_KEYS = ("SysUptime", "BootSignature", "ResetReason", "ResetBits", "MemFree", "MemPaused", "ConfigFaults", "ConfigUnpersisted", "LocalTime", "UTCTime")


def _system_status_fields(repo_root: Path, src_dir: Path, device: str) -> "list[dict[str, Any]]":
    status = next(s for s in _generate(repo_root, src_dir, device)["sections"] if s["key"] == "status")
    fields: list[dict[str, Any]] = next(g for g in status["groups"] if g["key"] == "system")["fields"]
    return fields


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_system_status_lists_its_rows_in_the_published_order(repo_root: Path, src_dir: Path, device: str) -> None:
    has_fram = any(spec.driver == "fram" for spec in build_model(device_toml(device), src_dir).instances.values())
    expected = [key for key in _SYSTEM_STATUS_KEYS if has_fram or key != "MemPaused"]
    assert [f["key"] for f in _system_status_fields(repo_root, src_dir, device)] == expected


def test_the_reset_heap_and_config_rows_say_what_they_report(repo_root: Path, src_dir: Path) -> None:
    fields = {f["key"]: f for f in _system_status_fields(repo_root, src_dir, DEVICE_NAMES[0])}
    reset_codes = {num: row["text"] for num, row in _CATALOG["status"]["ResetReason"].items()}
    assert fields["ResetReason"] == {"key": "ResetReason", "label": "Last Reset Reason", "kind": "readonly", "description": "Why the device last restarted, as a numeric code.", "codes": reset_codes}
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


def test_the_system_command_offers_its_five_words_in_order(repo_root: Path, src_dir: Path) -> None:
    system = next(s for s in _generate(repo_root, src_dir, DEVICE_NAMES[0])["sections"] if s["key"] == "system")
    (field,) = next(g for g in system["groups"] if g["key"] == "command")["fields"]
    assert (field["key"], field["kind"], field["dispatch"]) == ("SystemCmd", "enum", True)
    assert field["options"] == [
        {"value": "reboot", "label": "Reboot"},
        {"value": "bootloader", "label": "Reboot into bootloader"},
        {"value": "mempause", "label": "Pause backups for 5 minutes"},
        {"value": "resetconfig", "label": "Reset to defaults"},
        {"value": "erasefram", "label": "Erase FRAM"},
    ]


# ---------------------------------------------------------------------------
# A string field's special value: the schema's sentinel, labelled by its tag's quoted special:
# ---------------------------------------------------------------------------

_PW_SCHEMA = ("str", "", 8, 63, "")  # the shape of asy_wifi_service.py's _VAL_PW: "" bypasses 8..63


def _string_tag(*special: "tuple[str, str]") -> WebFieldTag:
    return WebFieldTag(field_name="PW", section="networking", submit_group="identity", label="Wi-Fi Password", raw="# @web PW", special=special)


def test_a_string_fields_schema_special_is_emitted_with_its_tag_label() -> None:
    field = _build_field_def(_string_tag(('""', "Open network")), _PW_SCHEMA, "dev", Path("asy_wifi_service.py"))
    assert (field["kind"], field["minLength"], field["maxLength"]) == ("string", 8, 63)
    assert field["specialValues"] == [{"value": "", "meaning": "Open network"}]


def test_a_string_field_without_a_schema_special_emits_none() -> None:
    field = _build_field_def(_string_tag(), ("str", "x", 1, 32, None), "dev", Path("asy_x.py"))
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
        _build_field_def(_string_tag(*special), (schema[0], schema[1], schema[2], schema[3], schema[4]), "dev", Path("asy_wifi_service.py"))
    _assert_rule(caught.value, rule)


@pytest.mark.parametrize(("kind", "schema"), [("number", ("int", 0, 0, 10, None)), ("readonly", None)])
def test_a_quoted_special_off_a_string_field_fails_loud(kind: str, schema: "tuple[object, object, object, object, object] | None") -> None:
    tag = WebFieldTag(field_name="X", section="sensors", submit_group="self", label="X", raw="# @web X", kind=kind, special=(('"0"', "Zero"),))
    with pytest.raises(BuildError, match="a quoted special: value labels a string field only") as caught:
        _build_field_def(tag, schema, "dev", Path("asy_x.py"))
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
    keys = [m["key"] for _section, group in _errcount_groups(generated) for m in group["modules"]]
    scd30 = [k for k in keys if k.startswith("SCD30")]
    assert scd30, f"{device} lists no SCD30 errcount row - the check holds nothing"
    for name in scd30:
        assert keys.count(f"CFGMGR_{name}") == 1, name
    states = [f for _section, group in _field_groups(generated) for f in group["fields"] if f["key"] == "FRCState"]
    assert len(states) == len(scd30)
    for field in states:
        assert field["codes"] == {num: row["text"] for num, row in _CATALOG["status"]["FRCState"].items()}


def _tagged_code_tables(src_dir: Path) -> "dict[str, str]":
    # Field key -> the status table its `codes=` tag names, over every tagged src/ file.
    return {t.field_name: t.codes for p in sorted(src_dir.glob("*.py")) for t in parse_web_tags(p, "fixture", "x") if t.codes is not None}


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_field_codes_table_equals_its_catalog_status_table(repo_root: Path, src_dir: Path, device: str) -> None:
    # A catalog row (the Status page's own fields) names its table by its key; a tagged field by codes=.
    tables = _CATALOG.get("status", {})
    named = _tagged_code_tables(src_dir)
    for _section, group in _field_groups(_generate(repo_root, src_dir, device)):
        for f in group["fields"]:
            if "codes" in f:
                table = named.get(f["key"], f["key"])
                assert table in tables, f"{f['key']} carries codes but the catalog has no status table {table!r}"
                assert f["codes"] == {num: row["text"] for num, row in tables[table].items()}, f["key"]


def test_every_codes_tag_names_a_present_table(src_dir: Path) -> None:
    missing = {field: table for field, table in _tagged_code_tables(src_dir).items() if table not in _CATALOG.get("status", {})}
    assert not missing, f"codes= tags naming no table in buildgen/error_catalog.json's status section: {missing}"


def test_a_codes_hint_naming_no_table_fails_the_build() -> None:
    tag = WebFieldTag(field_name="X", section="status", submit_group="system", label="X", raw="# @web X", kind="readonly", codes="NoSuchTable")
    with pytest.raises(BuildError, match="codes='NoSuchTable' names no status table") as caught:
        _build_field_def(tag, None, "dev", Path("asy_x.py"))
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
    model = DeviceModel(device="dev", path=Path("dev.toml"), doc={"device": {"name": "dev"}}, instances={}, construction_order=[])
    keys = {section: [m["key"] for _s, g in _errcount_groups(_read(generate_definitions(model, patched_src))) if _s == section for m in g["modules"]] for section in ("networking", "status")}
    assert keys["networking"] == ["CAPDNS"]
    assert {"WLAN", "CFGMGR_WLAN"} <= set(keys["status"])
    assert not {"WIFI", "CFGMGR_WIFI", "DNSSRV"} & set(keys["status"])


def test_a_sensor_the_registry_resolves_gets_its_cards_whatever_its_driver_name(src_dir: Path) -> None:
    # The registry's own classification (kind "sensor") decides the cards; no list of driver names does.
    info = DriverInfo(driver="co2probe", module="asy_scd30_driver", class_name="SCD30_Reader", kind="sensor", source_path=src_dir / "asy_scd30_driver.py", needs_setup=True)
    spec = InstanceSpec(driver="co2probe", name_ext="", fields={}, wiring={}, order_index=0, driver_info=info, resolved_name="CO2PROBE")
    model = DeviceModel(device="dev", path=Path("dev.toml"), doc={"device": {"name": "dev"}}, instances={spec.key: spec}, construction_order=[spec.key])
    generated = _read(generate_definitions(model, src_dir))
    for section in ("measurements", "sensors"):
        assert [g["key"] for g in next(s for s in generated["sections"] if s["key"] == section)["groups"]] == ["CO2PROBE"], section


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_warn_fields_are_the_signal_catalogs(repo_root: Path, src_dir: Path, device: str) -> None:
    # Guard: each wired warn signal's threshold field carries buildgen.signals' values, in catalog order.
    model = build_model(device_toml(device), src_dir)
    notification = next((spec for spec in model.instances.values() if spec.driver == "notification"), None)
    if notification is None:
        pytest.skip(f"{device} has no notification instance")
    sections = {s["key"]: s for s in _generate(repo_root, src_dir, device)["sections"]}
    fields = [f for g in sections["notification"]["groups"] for f in g.get("fields", []) if f["key"].startswith("Warn")]
    expected = [
        {"key": s.name, "label": s.label, **({"unit": s.unit} if s.unit is not None else {}), "kind": "number", "min": s.min, "max": s.max, **({"float": True} if s.field_type == "float" else {})}
        for key, s in WARN_SIGNALS.items() if key in notification.wiring
    ]
    assert fields == expected


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_timestamp_is_an_epoch_with_no_unit(repo_root: Path, src_dir: Path, device: str) -> None:
    # An instant, not a duration: the page shows its age, so a seconds unit would mislabel it.
    stamps = [f for _section, group in _field_groups(_generate(repo_root, src_dir, device)) for f in group["fields"] if f["key"].endswith("TS") or f["key"] == "NTPLastSync"]
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
    status = next(s for s in _generate(repo_root, src_dir, device)["sections"] if s["key"] == "status")
    maintenance = [f for g in status["groups"] if g["key"] == "sensors" for f in g["fields"]]
    if not sgp40:
        assert not [f["key"] for f in maintenance if f["key"].startswith("SGP40")], f"{device} has no sgp40 but lists its maintenance rows"
        return
    prefix = f"{sgp40[0].resolved_name}_"
    fields = {f["key"].removeprefix(prefix): f for f in maintenance if f["key"].startswith(prefix)}
    assert set(fields) == _sgp_maintenance_keys(generate_device(device_toml(device), src_dir, repo_root / "ext").module_source)
    for name, f in fields.items():
        assert f["specialValues"] == [{"value": None, "meaning": "None since boot"}, {"value": 0, "meaning": "No timestamp"}], name


def test_each_sgp40_publishes_its_own_maintenance_rows_under_its_rest_identity(repo_root: Path, src_dir: Path, fixtures_dir: Path) -> None:
    # Two SGP40s: one adapter each, reading its own module-level instance (a bare `sgp40` names none,
    # so every /status read failed), and one row set each keyed <resolved_name>_<field>.
    toml_path = fixtures_dir / "multi_instance.toml"
    source = generate_device(toml_path, src_dir, repo_root / "ext").module_source
    entries = dict(re.findall(r'\("(SGP40\w*)", (_sgp_maintenance_status\w*)\)', source))
    assert entries == {"SGP40_a": "_sgp_maintenance_status_sgp40_a", "SGP40_b": "_sgp_maintenance_status_sgp40_b"}
    for adapter in entries.values():
        var = adapter.removeprefix("_sgp_maintenance_status_")
        body = source.split(f"async def {adapter}()", 1)[1].split("\n\n", 1)[0]
        assert re.search(rf"^{var}: ", source, re.MULTILINE), f"{adapter} reads {var}, which the module never declares"
        assert f"await {var}.get_mem_status()" in body, body
    status = next(s for s in _read(definitions_for_toml(toml_path, src_dir))["sections"] if s["key"] == "status")
    rows = [f for g in status["groups"] if g["key"] == "sensors" for f in g["fields"]]
    assert {f["key"] for f in rows} == {f"{name}_{key}" for name in entries for key in _sgp_maintenance_keys(source)}
    assert len({f["label"] for f in rows}) == len(rows), [f["label"] for f in rows]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_logger_has_one_errcount_row_and_dns_sits_on_networking(repo_root: Path, src_dir: Path, device: str) -> None:
    groups = _errcount_groups(_generate(repo_root, src_dir, device))
    rows = Counter(m["key"] for _section, g in groups for m in g["modules"])
    assert not [key for key, count in rows.items() if count > 1], f"loggers listed in more than one errcount row: {rows}"
    assert [section for section, g in groups if any(m["key"] == "DNSSRV" for m in g["modules"])] == ["networking"]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_identity_and_ntp_groups_carry_their_apply_labels(repo_root: Path, src_dir: Path, device: str) -> None:
    networking = next(s for s in _generate(repo_root, src_dir, device)["sections"] if s["key"] == "networking")
    labels = {g["key"]: g.get("submitLabel") for g in networking["groups"]}
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
_POLL_GROUPS = ("live", "settings", "none")
_FIELD_FORMATS = ("gmtimestruct", "epoch")
_STRING_SHAPES = ("hostLabel", "countryCode", "hostName", "ipv4List")


def _is_number(value: object) -> "TypeGuard[int | float]":
    return isinstance(value, int | float) and not isinstance(value, bool)


def _is_string_map(value: object) -> bool:
    return isinstance(value, dict) and all(isinstance(v, str) for v in value.values())


def _top_level_problems(defs: "dict[str, Any]") -> "list[str]":
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
    interval = defs.get("defaultPollIntervalMs")
    if not _is_number(interval) or not interval > 0:
        problems.append("defaultPollIntervalMs")
    return problems


def _field_hint_problems(f: object, where: str) -> "list[str]":
    if not isinstance(f, dict):
        return []  # validateFieldHints() leaves a non-object field to the group-level checks
    problems = []
    if "path" in f:
        path = f["path"]
        if not isinstance(path, list) or not path or not all(isinstance(step, str) and step for step in path):
            problems.append(f"{where}.path")
        elif f.get("kind") != "readonly":
            problems.append(f"{where}.path on a writable field")
    decimals = f.get("decimals")
    if "decimals" in f and not (_is_number(decimals) and float(decimals).is_integer() and 0 <= decimals <= _MAX_DECIMALS):
        problems.append(f"{where}.decimals")
    if "format" in f and (f["format"] not in _FIELD_FORMATS or f.get("kind") != "readonly"):
        problems.append(f"{where}.format")
    if "codes" in f and not _is_string_map(f["codes"]):
        problems.append(f"{where}.codes")
    if "alwaysExecuted" in f and not isinstance(f["alwaysExecuted"], bool):
        problems.append(f"{where}.alwaysExecuted")
    if "byteLength" in f and (not isinstance(f["byteLength"], bool) or f.get("kind") != "string"):
        problems.append(f"{where}.byteLength")
    if "shape" in f and (f["shape"] not in _STRING_SHAPES or f.get("kind") != "string"):
        problems.append(f"{where}.shape")
    return problems


def _group_problems(g: object, where: str) -> "list[str]":
    if not isinstance(g, dict):
        return [f"{where} is not an object"]  # validateDefinitions() throws on it: a rejection either way
    problems = []
    if not isinstance(g.get("key"), str) or not isinstance(g.get("label"), str):
        problems.append(f"{where} key/label")
    if g.get("kind") == "errcount":
        if not isinstance(g.get("modules"), list):
            problems.append(f"{where}.modules")
        codes = g.get("codes", {"E": {}, "W": {}})
        if not isinstance(codes, dict) or not _is_string_map(codes.get("E")) or not _is_string_map(codes.get("W")):
            problems.append(f"{where}.codes")
        return problems
    fields = g.get("fields")
    if not isinstance(fields, list):
        return [*problems, f"{where}.fields"]
    for index, f in enumerate(fields):
        problems += _field_hint_problems(f, f"{where}.fields[{index}]")
    return problems


def _section_problems(s: "dict[str, Any]", where: str) -> "list[str]":
    problems = [f"{where}.{key}" for key in ("key", "label") if not isinstance(s.get(key), str)]
    rest = s.get("rest")
    if not isinstance(rest, dict) or not isinstance(rest.get("get"), str):
        problems.append(f"{where}.rest.get")
    if s.get("pollGroup") not in _POLL_GROUPS:
        problems.append(f"{where}.pollGroup")
    if "pollIntervalMs" in s and (not _is_number(s["pollIntervalMs"]) or not s["pollIntervalMs"] > 0):
        problems.append(f"{where}.pollIntervalMs")
    groups = s.get("groups")
    if not isinstance(groups, list):
        return [*problems, f"{where}.groups"]
    for index, g in enumerate(groups):
        problems += _group_problems(g, f"{where}.groups[{index}]")
    return problems


def _shape_problems(defs: object) -> "list[str]":
    # js/definitions.js's validateDefinitions(), rule for rule: empty means the document loads.
    if not isinstance(defs, dict):
        return ["definitions.json is not a JSON object"]
    problems = _top_level_problems(defs)
    sections = defs.get("sections")
    if not isinstance(sections, list) or not sections:
        return [*problems, "sections"]
    section_keys = set()
    for index, s in enumerate(sections):
        if not isinstance(s, dict):
            problems.append(f"sections[{index}] is not an object")
            continue
        if isinstance(s.get("key"), str):
            section_keys.add(s["key"])
        problems += _section_problems(s, f"sections[{index}]")
    if "landingSection" in defs and defs["landingSection"] not in section_keys:
        problems.append("landingSection matches no section")
    return problems


@pytest.mark.parametrize("case", _SHAPE_CASES, ids=[c["name"] for c in _SHAPE_CASES])
def test_shape_corpus_agrees(case: "dict[str, Any]") -> None:
    # The same corpus tests_js/definitions-shape-corpus.test.js runs through the real validator.
    assert (_shape_problems(case["definitions"]) == []) == case["valid"], _shape_problems(case["definitions"])


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_generated_definitions_pass_shape_validation(repo_root: Path, src_dir: Path, device: str) -> None:
    assert _shape_problems(_generate(repo_root, src_dir, device)) == []


# ---------------------------------------------------------------------------
# Mandatory synthetic fixtures - proving generality beyond the 6 real, hand-verified devices
# ---------------------------------------------------------------------------


def test_novel_combo_fixture_generates_distinct_scd30_groups(fixtures_dir: Path, src_dir: Path) -> None:
    generated = _read(definitions_for_toml(fixtures_dir / "novel_combo.toml", src_dir))
    measurements = next(s for s in generated["sections"] if s["key"] == "measurements")
    scd30_group_keys = {g["key"] for g in measurements["groups"] if g["key"].startswith("SCD30")}
    assert scd30_group_keys == {"SCD30_primary", "SCD30_secondary"}
    labels = {g["key"]: g["label"] for g in measurements["groups"] if g["key"].startswith("SCD30")}
    assert labels["SCD30_primary"].endswith("(primary)")
    assert labels["SCD30_secondary"].endswith("(secondary)")


def test_novel_combo_fixture_only_wires_the_one_declared_warning_signal(fixtures_dir: Path, src_dir: Path) -> None:
    generated = _read(definitions_for_toml(fixtures_dir / "novel_combo.toml", src_dir))
    notification = next(s for s in generated["sections"] if s["key"] == "notification")
    auto_group = next(g for g in notification["groups"] if not g["key"].startswith(("flash", "pause")))
    warn_keys = {f["key"] for f in auto_group["fields"] if f["key"].startswith("Warn")}
    assert warn_keys == {"WarnCO2"}


def test_multi_instance_fixture_generates_successfully(fixtures_dir: Path, src_dir: Path) -> None:
    generated = _read(definitions_for_toml(fixtures_dir / "multi_instance.toml", src_dir))
    assert _shape_problems(generated) == []


@pytest.mark.parametrize("bound", [b"\x00", 1j])
def test_a_schema_value_with_no_json_form_fails_the_build(bound: object) -> None:
    tag = WebFieldTag(field_name="X", section="sensors", submit_group="self", label="X", raw="# @web X")
    with pytest.raises(BuildError, match="which has no JSON form") as caught:
        _build_field_def(tag, ("int", 0, bound, 10, None), "dev", Path("asy_x.py"))
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
    with pytest.raises(BuildError, match="has bytes= or shape= but its kind is 'number'") as caught:
        _build_field_def(tag, ("int", 0, 0, 10, None), "dev", Path("asy_x.py"))
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
    model = _single_scd30_model("dev", mutated)
    with pytest.raises(BuildError, match="no @web-group section=measurements") as caught:
        generate_definitions(model, src_dir)
    _assert_rule(caught.value, "web.instance-group-missing")


def test_a_schema_field_without_a_web_tag_fails_the_build(tmp_path: Path, src_dir: Path) -> None:
    mutated = _copy_driver_without(tmp_path, src_dir, "asy_scd30_driver.py", "# @web AmbPres section=sensors")
    model = _single_scd30_model("dev", mutated)
    with pytest.raises(BuildError, match=r"schema field\(s\) \['AmbPres'\] have no @web tag") as caught:
        generate_definitions(model, src_dir)
    _assert_rule(caught.value, "web.schema-field-untagged")


def test_an_unreadable_schema_names_its_device_and_instance(tmp_path: Path, src_dir: Path) -> None:
    mutated = tmp_path / "asy_scd30_driver.py"
    mutated.write_text((src_dir / "asy_scd30_driver.py").read_text(encoding="utf-8") + '_VAL_BROKEN = const((("X", "int", 0, 0, _NO_SUCH_BOUND, None),))\n', encoding="utf-8")
    with pytest.raises(BuildError, match="_VAL_BROKEN") as caught:
        generate_definitions(_single_scd30_model("dev", mutated), src_dir)
    assert (caught.value.device, caught.value.instance) == ("dev", "scd30")
    _assert_rule(caught.value, "schema.unreadable")


def test_a_hidden_schema_field_stays_off_the_website(tmp_path: Path, src_dir: Path) -> None:
    # A schema field tagged hidden= stays off the page; the rest of the card still shows.
    original = (src_dir / "asy_scd30_driver.py").read_text(encoding="utf-8")
    line = next(line for line in original.splitlines(keepends=True) if line.startswith("# @web AmbPres section=sensors"))
    mutated = tmp_path / "asy_scd30_driver.py"
    mutated.write_text(original.replace(line, '# @web AmbPres hidden="a test keeps it off"\n', 1), encoding="utf-8")
    generated = _read(generate_definitions(_single_scd30_model("dev", mutated), src_dir))
    sensors_fields = {f["key"] for g in next(s for s in generated["sections"] if s["key"] == "sensors")["groups"] for f in g["fields"]}
    assert "AmbPres" not in sensors_fields
    assert "MeasInterval" in sensors_fields


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
    model = DeviceModel(device="dev", path=Path("dev.toml"), doc={"device": {"name": "dev"}}, instances={("bmp3xx", ""): spec}, construction_order=[("bmp3xx", "")])
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
    model = DeviceModel(device="dev", path=Path("dev.toml"), doc={"device": {"name": "dev"}}, instances={}, construction_order=[])

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
    model = _single_scd30_model("dev", mutated)
    with pytest.raises(BuildError, match="no matching ConfigSchema constant and no explicit kind") as caught:
        generate_definitions(model, src_dir)
    _assert_rule(caught.value, "web.kind-unresolved")


def test_web_tag_kind_enum_with_no_discrete_schema_choice_set_fails_loud(tmp_path: Path, src_dir: Path) -> None:
    # Same freestanding ContMeas field, forced to kind=enum instead of dropped entirely - _enum_field()
    # needs a tuple/list `special` from the schema, and ContMeas's synthetic bool schema has none.
    mutated = _copy_driver_replacing(tmp_path, src_dir, "asy_scd30_driver.py", "kind=toggle", "kind=enum")
    model = _single_scd30_model("dev", mutated)
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
    model = DeviceModel(device="dev", path=Path("dev.toml"), doc={"device": {"name": "dev"}}, instances={("bmp3xx", ""): spec}, construction_order=[("bmp3xx", "")])
    with pytest.raises(BuildError, match=r"declares special: option\(s\) \['999'\] not present") as caught:
        generate_definitions(model, src_dir)
    _assert_rule(caught.value, "web.special-not-in-schema")


def test_web_tag_schema_sentinel_value_with_no_matching_special_label_fails_loud(tmp_path: Path, src_dir: Path) -> None:
    # AmbPres's ConfigSchema declares a scalar sentinel rather than a choice set, documented by
    # its own special:0= tag entry. Drop that one entry and the sentinel has nothing left to
    # explain it.
    mutated = _copy_driver_replacing(tmp_path, src_dir, "asy_scd30_driver.py", ' special:0="Compensation off / use Altitude"', "")
    model = _single_scd30_model("dev", mutated)
    with pytest.raises(BuildError, match=r"has a sentinel special value 0 but no matching special:0") as caught:
        generate_definitions(model, src_dir)
    _assert_rule(caught.value, "web.special-unlabelled")


def test_an_sgp40_without_maintenance_tags_fails_the_build(tmp_path: Path, src_dir: Path) -> None:
    mutated = _copy_driver_without(tmp_path, src_dir, "asy_sgp40_driver.py", "section=status submitGroup=maintenance")
    info = DriverInfo(driver="sgp40", module="asy_sgp40_driver", class_name="SGP40_Reader", kind="sensor", source_path=mutated, needs_setup=True)
    spec = InstanceSpec(driver="sgp40", name_ext="", fields={}, wiring={}, order_index=0, driver_info=info, resolved_name="SGP40")
    model = DeviceModel(device="dev", path=Path("dev.toml"), doc={"device": {"name": "dev"}}, instances={spec.key: spec}, construction_order=[spec.key])
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
    model = DeviceModel(device="dev", path=Path("dev.toml"), doc={"device": {"name": "dev"}}, instances={}, construction_order=[])
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
    model = DeviceModel(device="dev", path=Path("dev.toml"), doc={"device": {"name": "dev"}}, instances={("notification", ""): spec}, construction_order=[("notification", "")])
    with pytest.raises(BuildError, match=r"section='notification' submitGroup='autoConfig' has an @web-group declaration but no @web field tags reference it") as caught:
        generate_definitions(model, src_dir)
    _assert_rule(caught.value, "web.group-without-fields")


def test_resolved_key_fails_loud_if_resolved_name_still_unset() -> None:
    # _resolved_key()'s own invariant guard - buildgen.validate._resolve_instances()
    # always sets resolved_name before definitions generation ever runs on a real model.
    from buildgen.definitions import _resolved_key

    spec = InstanceSpec(driver="scd30", name_ext="", fields={}, wiring={}, order_index=0)  # resolved_name defaults to None
    with pytest.raises(BuildInternalError, match="resolved_name unresolved before definitions generation"):
        _resolved_key(spec, "dev")


def test_measurements_and_sensors_sections_fails_loud_if_driver_info_still_unset() -> None:
    # _measurements_and_sensors_sections()'s own invariant guard - same
    # always-resolved-by-validate.py reasoning as _resolved_key() above.
    from buildgen.definitions import _measurements_and_sensors_sections

    spec = InstanceSpec(driver="scd30", name_ext="", fields={}, wiring={}, order_index=0, resolved_name="SCD30")  # driver_info defaults to None
    model = DeviceModel(device="dev", path=Path("dev.toml"), doc={"device": {"name": "dev"}}, instances={("scd30", ""): spec}, construction_order=[("scd30", "")])
    with pytest.raises(BuildInternalError, match="driver_info unresolved before definitions generation"):
        _measurements_and_sensors_sections(model, {})


def test_notification_section_fails_loud_if_driver_info_still_unset() -> None:
    # _notification_section()'s own invariant guard, same reasoning as above.
    from buildgen.definitions import _notification_section

    spec = InstanceSpec(driver="notification", name_ext="", fields={}, wiring={}, order_index=0)  # driver_info defaults to None
    model = DeviceModel(device="dev", path=Path("dev.toml"), doc={"device": {"name": "dev"}}, instances={("notification", ""): spec}, construction_order=[("notification", "")])
    with pytest.raises(BuildInternalError, match="driver_info unresolved before definitions generation"):
        _notification_section(model, {}, {"notification"})


def test_no_notification_instance_omits_notification_section(src_dir: Path) -> None:
    model = DeviceModel(device="dev", path=Path("dev.toml"), doc={"device": {"name": "dev"}}, instances={}, construction_order=[])
    generated = _read(generate_definitions(model, src_dir))
    assert "notification" not in {s["key"] for s in generated["sections"]}
    assert {s["key"] for s in generated["sections"]} == {"measurements", "sensors", "networking", "system", "status"}


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
    assert json.loads(out_file.read_text()) == json.loads(json.dumps(generate_definitions(model, src_dir)))


def test_definitions_refuse_a_model_that_skipped_the_construction_order(src_dir: Path) -> None:
    # Falling back to TOML order would silently reorder the cards; a caller that skipped the graph fails.
    model = _single_scd30_model("fixture", src_dir / "asy_scd30_driver.py")
    model.construction_order = []
    with pytest.raises(BuildInternalError, match="construction order unresolved before definitions generation"):
        generate_definitions(model, src_dir)


def test_cli_prints_to_stdout_when_out_is_omitted(repo_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([str(repo_root / "devices" / "wozi.toml")])
    assert exit_code == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["device"]["id"] == "wozi"


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

    monkeypatch.setattr("buildgen.definitions.os.replace", refuse)
    assert main([str(device_toml(DEVICE_NAMES[0])), "--out", str(out)]) == 1
    assert "injected for the rename" in _one_line_error(capsys)
    assert out.read_text(encoding="utf-8") == "old"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["definitions.json"]
