"""Tests for buildgen.definitions (SPECIFICATION.md Part H.5/H.5.1): every tagged field lands once in its group,
every device's output passes the shared shape corpus, and the catalog-derived blocks equal their sources."""

import copy
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, TypeGuard

import pytest
from _devices import DEVICE_NAMES, device_toml

from buildgen.definitions import SCHEMA_VERSION, definitions_for_toml, generate_definitions, main
from buildgen.driver_registry import DriverInfo
from buildgen.errors import BuildError
from buildgen.generate import generate_device
from buildgen.graph import build_construction_order
from buildgen.model import DeviceModel, InstanceSpec
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
    return definitions_for_toml(repo_root / "devices" / f"{device}.toml", src_dir)


def _field_groups(definitions: "dict[str, Any]") -> "list[tuple[str, dict[str, Any]]]":
    # (section key, group) for every field group - errcount groups carry modules, not fields.
    return [(s["key"], g) for s in definitions["sections"] for g in s["groups"] if "fields" in g]


def _errcount_groups(definitions: "dict[str, Any]") -> "list[tuple[str, dict[str, Any]]]":
    return [(s["key"], g) for s in definitions["sections"] for g in s["groups"] if g.get("kind") == "errcount"]


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


def _expected_tagged_fields(model: DeviceModel, src_dir: Path) -> "Counter[tuple[str, str, str, str, str | None]]":
    sources: list[tuple[Path, InstanceSpec | None]] = [(src_dir / name, None) for name in _MANDATORY_TAG_FILES]
    sources += [(spec.driver_info.source_path, spec) for spec in model.instances.values() if spec.driver_info is not None]
    expected: Counter[tuple[str, str, str, str, str | None]] = Counter()
    for path, spec in sources:
        for tag in parse_web_tags(path, model.device, spec.label if spec is not None else path.stem):
            section, group, key = _tag_place(tag, spec)
            expected[(section, group, key, tag.label, tag.unit)] += 1
    return expected


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
    assert _tag_placement_problems(_expected_tagged_fields(model, src_dir), _generate(repo_root, src_dir, device)) == []


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
    status = next(s for s in definitions_for_toml(toml_path, src_dir)["sections"] if s["key"] == "status")
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
_STRING_SHAPES = ("hostLabel", "countryCode")


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
    generated = definitions_for_toml(fixtures_dir / "novel_combo.toml", src_dir)
    measurements = next(s for s in generated["sections"] if s["key"] == "measurements")
    scd30_group_keys = {g["key"] for g in measurements["groups"] if g["key"].startswith("SCD30")}
    assert scd30_group_keys == {"SCD30_primary", "SCD30_secondary"}
    labels = {g["key"]: g["label"] for g in measurements["groups"] if g["key"].startswith("SCD30")}
    assert labels["SCD30_primary"].endswith("(primary)")
    assert labels["SCD30_secondary"].endswith("(secondary)")


def test_novel_combo_fixture_only_wires_the_one_declared_warning_signal(fixtures_dir: Path, src_dir: Path) -> None:
    generated = definitions_for_toml(fixtures_dir / "novel_combo.toml", src_dir)
    notification = next(s for s in generated["sections"] if s["key"] == "notification")
    auto_group = next(g for g in notification["groups"] if not g["key"].startswith(("flash", "pause")))
    warn_keys = {f["key"] for f in auto_group["fields"] if f["key"].startswith("Warn")}
    assert warn_keys == {"WarnCO2"}


def test_multi_instance_fixture_generates_successfully(fixtures_dir: Path, src_dir: Path) -> None:
    generated = definitions_for_toml(fixtures_dir / "multi_instance.toml", src_dir)
    assert _shape_problems(generated) == []


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
    with pytest.raises(BuildError, match="no @web-group section=measurements"):
        generate_definitions(model, src_dir)


def test_missing_web_field_tag_for_a_schema_field_is_tolerated_but_field_is_absent(tmp_path: Path, src_dir: Path) -> None:
    # Dropping one @web tag doesn't break the build - it just means that field never reaches the
    # website (the generator has no way to know it "should" exist; that's the tag's whole job).
    mutated = _copy_driver_without(tmp_path, src_dir, "asy_scd30_driver.py", "# @web AmbPres section=sensors")
    model = _single_scd30_model("dev", mutated)
    generated = generate_definitions(model, src_dir)
    sensors_fields = {f["key"] for g in next(s for s in generated["sections"] if s["key"] == "sensors")["groups"] for f in g["fields"]}
    assert "AmbPres" not in sensors_fields
    assert "MeasInterval" in sensors_fields


def test_missing_special_label_for_an_enum_schema_value_fails_loud(tmp_path: Path, src_dir: Path) -> None:
    mutated = _copy_driver_replacing(tmp_path, src_dir, "asy_bmp3xx_driver.py", ' special:127="127"', "")
    spec = InstanceSpec(
        driver="bmp3xx", name_ext="", fields={}, wiring={}, order_index=0,
        driver_info=DriverInfo(driver="bmp3xx", module="asy_bmp3xx_driver", class_name="BMP3XX_Reader", kind="sensor", source_path=mutated, needs_setup=True),
        resolved_name="BMP3XX",
    )
    model = DeviceModel(device="dev", path=Path("dev.toml"), doc={"device": {"name": "dev"}}, instances={("bmp3xx", ""): spec}, construction_order=[("bmp3xx", "")])
    with pytest.raises(BuildError, match="no matching special:127"):
        generate_definitions(model, src_dir)


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

    def _generate_with_patched_ntp() -> "dict[str, Any]":
        # _system_section() resolves asy_ntp_client.py by a fixed path under src_dir - point it at
        # a src_dir where only that one file differs, mirroring every other file from the real tree.
        patched_src = tmp_path / "src"
        patched_src.mkdir()
        for existing in src_dir.glob("*.py"):
            (patched_src / existing.name).write_bytes(existing.read_bytes())
        (patched_src / "asy_ntp_client.py").write_bytes(mutated_ntp.read_bytes())
        return generate_definitions(model, patched_src)

    with pytest.raises(BuildError, match="more than one @web-group"):
        _generate_with_patched_ntp()


def test_web_tag_with_no_schema_and_no_kind_override_fails_loud(tmp_path: Path, src_dir: Path) -> None:
    # ContMeas is freestanding, with no _VAL_* ConfigSchema constant at all, so its kind=toggle
    # override is the only thing letting _infer_kind() resolve it. Drop that and it has neither a
    # schema-derived field_type nor an explicit kind to fall back on.
    mutated = _copy_driver_replacing(tmp_path, src_dir, "asy_scd30_driver.py", " kind=toggle", "")
    model = _single_scd30_model("dev", mutated)
    with pytest.raises(BuildError, match="no matching ConfigSchema constant and no explicit kind"):
        generate_definitions(model, src_dir)


def test_web_tag_kind_enum_with_no_discrete_schema_choice_set_fails_loud(tmp_path: Path, src_dir: Path) -> None:
    # Same freestanding ContMeas field, forced to kind=enum instead of dropped entirely - _enum_field()
    # needs a tuple/list `special` from the schema, and ContMeas has no schema at all.
    mutated = _copy_driver_replacing(tmp_path, src_dir, "asy_scd30_driver.py", "kind=toggle", "kind=enum")
    model = _single_scd30_model("dev", mutated)
    with pytest.raises(BuildError, match="kind=enum but its ConfigSchema has no discrete choice set"):
        generate_definitions(model, src_dir)


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
    with pytest.raises(BuildError, match=r"declares special: option\(s\) \['999'\] not present"):
        generate_definitions(model, src_dir)


def test_web_tag_schema_sentinel_value_with_no_matching_special_label_fails_loud(tmp_path: Path, src_dir: Path) -> None:
    # AmbPres's ConfigSchema declares a scalar sentinel rather than a choice set, documented by
    # its own special:0= tag entry. Drop that one entry and the sentinel has nothing left to
    # explain it.
    mutated = _copy_driver_replacing(tmp_path, src_dir, "asy_scd30_driver.py", ' special:0="Compensation off / use Altitude"', "")
    model = _single_scd30_model("dev", mutated)
    with pytest.raises(BuildError, match=r"has a sentinel special value 0 but no matching special:0"):
        generate_definitions(model, src_dir)


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
    with pytest.raises(BuildError, match=r"no @web-group tag declares section='system' submitGroup='settings' in any scanned file"):
        generate_definitions(model, patched_src)


def test_mandatory_group_declared_but_no_fields_reference_it_fails_loud(tmp_path: Path, src_dir: Path) -> None:
    # _mandatory_group()'s own "declared but empty" branch: the @web-group tag survives, but every
    # @web field tag that would normally reference notification/autoConfig is stripped, so the
    # group has nothing to show. Uses a synthetic notification instance (driver_registry.py's own
    # NotificationService mapping) since _mandatory_group("notification", "autoConfig", ...) is
    # only reached when the model actually has one.
    original = (src_dir / "asy_notification_service.py").read_text(encoding="utf-8")
    lines = [line for line in original.splitlines(keepends=True) if not line.lstrip().startswith("# @web ")]
    mutated = tmp_path / "asy_notification_service.py"
    mutated.write_text("".join(lines), encoding="utf-8")
    spec = InstanceSpec(
        driver="notification", name_ext="", fields={}, wiring={}, order_index=0, resolved_name="NOTIFY",  # errcount rows are per instance now, so this must be filled as validate.py always fills it
        driver_info=DriverInfo(driver="notification", module="asy_notification_service", class_name="NotificationService", kind="service", source_path=mutated, needs_setup=True),
    )
    model = DeviceModel(device="dev", path=Path("dev.toml"), doc={"device": {"name": "dev"}}, instances={("notification", ""): spec}, construction_order=[("notification", "")])
    with pytest.raises(BuildError, match=r"section='notification' submitGroup='autoConfig' has an @web-group declaration but no @web field tags reference it"):
        generate_definitions(model, src_dir)


def test_resolved_key_fails_loud_if_resolved_name_still_unset() -> None:
    # _resolved_key()'s own "internal:" invariant guard - buildgen.validate._resolve_instances()
    # always sets resolved_name before definitions generation ever runs on a real model.
    from buildgen.definitions import _resolved_key

    spec = InstanceSpec(driver="scd30", name_ext="", fields={}, wiring={}, order_index=0)  # resolved_name defaults to None
    with pytest.raises(BuildError, match="internal: resolved_name unresolved before definitions generation"):
        _resolved_key(spec, "dev")


def test_measurements_and_sensors_sections_fails_loud_if_driver_info_still_unset() -> None:
    # _measurements_and_sensors_sections()'s own "internal:" invariant guard - same
    # always-resolved-by-validate.py reasoning as _resolved_key() above.
    from buildgen.definitions import _measurements_and_sensors_sections

    spec = InstanceSpec(driver="scd30", name_ext="", fields={}, wiring={}, order_index=0, resolved_name="SCD30")  # driver_info defaults to None
    model = DeviceModel(device="dev", path=Path("dev.toml"), doc={"device": {"name": "dev"}}, instances={("scd30", ""): spec}, construction_order=[("scd30", "")])
    with pytest.raises(BuildError, match="internal: driver_info unresolved before definitions generation"):
        _measurements_and_sensors_sections(model, {})


def test_notification_section_fails_loud_if_driver_info_still_unset() -> None:
    # _notification_section()'s own "internal:" invariant guard, same reasoning as above.
    from buildgen.definitions import _notification_section

    spec = InstanceSpec(driver="notification", name_ext="", fields={}, wiring={}, order_index=0)  # driver_info defaults to None
    model = DeviceModel(device="dev", path=Path("dev.toml"), doc={"device": {"name": "dev"}}, instances={("notification", ""): spec}, construction_order=[("notification", "")])
    with pytest.raises(BuildError, match="internal: driver_info unresolved before definitions generation"):
        _notification_section(model, {}, {"notification"})


def test_no_notification_instance_omits_notification_section(src_dir: Path) -> None:
    model = DeviceModel(device="dev", path=Path("dev.toml"), doc={"device": {"name": "dev"}}, instances={}, construction_order=[])
    generated = generate_definitions(model, src_dir)
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
    with pytest.raises(BuildError, match="internal: construction order unresolved before definitions generation"):
        generate_definitions(model, src_dir)


def test_cli_prints_to_stdout_when_out_is_omitted(repo_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([str(repo_root / "devices" / "wozi.toml")])
    assert exit_code == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["device"]["id"] == "wozi"


def test_cli_reports_a_build_error_and_exits_nonzero(repo_root: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing_toml = tmp_path / "no-such-device.toml"
    exit_code = main([str(missing_toml)])
    assert exit_code == 1
    assert "buildgen:" in capsys.readouterr().err
