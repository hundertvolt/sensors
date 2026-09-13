"""Tests for buildgen.definitions: the website `definitions.json` generator (SPECIFICATION.md Part
H.5/H.5.1) - golden-file comparison against the hand-written `html/definitions/*.json`, plus a
`js/definitions.js`-`validateDefinitions()`-equivalent shape check for every real device."""

import json
from pathlib import Path
from typing import Any

import pytest

from buildgen.definitions import generate_definitions
from buildgen.driver_registry import DriverInfo
from buildgen.errors import BuildError
from buildgen.model import DeviceModel, InstanceSpec
from buildgen.validate import build_model
from buildgen.version import WEBSITE_VERSION

DEVICE_NAMES = ["dev", "wozi", "arzi", "klkizi", "grkizi", "schlafzi"]
BMP3XX_DEVICES = {"dev", "wozi"}


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


@pytest.fixture
def definitions_dir(repo_root: Path) -> Path:
    return repo_root / "html" / "definitions"


@pytest.fixture
def fixtures_dir(repo_root: Path) -> Path:
    return repo_root / "tests_scripts" / "buildgen_fixtures"


def _normalize(obj: object) -> object:
    """Sorts every list of key-bearing dicts by "key" (falling back to "value" for enum/special
    option lists) so comparison is insensitive to this generator's own field/group declaration
    order - a real content difference still fails, a cosmetic reordering does not."""
    if isinstance(obj, dict):
        return {k: _normalize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        normalized = [_normalize(item) for item in obj]
        dicts: list[dict[str, object]] = [item for item in normalized if isinstance(item, dict)]
        if len(dicts) == len(normalized) and dicts:
            sort_key = "key" if "key" in dicts[0] else "value"
            if all(sort_key in item for item in dicts):
                return sorted(dicts, key=lambda item: str(item[sort_key]))
        return normalized
    return obj


def _generate(repo_root: Path, src_dir: Path, device: str) -> "dict[str, Any]":
    model = build_model(repo_root / "devices" / f"{device}.toml", src_dir)
    return generate_definitions(model, src_dir)


# ---------------------------------------------------------------------------
# Golden-file comparison against the two hand-written references
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("device", ["wozi", "dev"])
def test_generated_definitions_match_hand_written_reference(repo_root: Path, src_dir: Path, definitions_dir: Path, device: str) -> None:
    generated = _generate(repo_root, src_dir, device)
    hand_written = json.loads((definitions_dir / f"{device}.json").read_text(encoding="utf-8"))
    assert _normalize(generated) == _normalize(hand_written)


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
def test_every_real_device_has_all_six_sections(repo_root: Path, src_dir: Path, device: str) -> None:
    generated = _generate(repo_root, src_dir, device)
    assert {s["key"] for s in generated["sections"]} == {"measurements", "sensors", "networking", "system", "status", "notification"}


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_real_device_stamps_the_website_version(repo_root: Path, src_dir: Path, device: str) -> None:
    # BUILD_CHAIN_PLAN.md Session 7: buildgen.version.WEBSITE_VERSION is a build-provenance-only
    # stamp, independent of schemaVersion (the wire-format shape version) - a genuinely different
    # concept, so the two must never collide on the same key.
    generated = _generate(repo_root, src_dir, device)
    assert generated["websiteVersion"] == WEBSITE_VERSION
    assert generated["websiteVersion"] != generated["schemaVersion"]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_status_pages_system_group_does_not_declare_a_firmware_version_field(repo_root: Path, src_dir: Path, device: str) -> None:
    # Regression guard against this session's own earlier, corrected design: the firmware version
    # lives on GET /system's "build" sub-entry (src/asy_webserver_service.py's build_info=), not on
    # GET /status's "system" section - definitions.json's Status page never declares it.
    generated = _generate(repo_root, src_dir, device)
    status = next(s for s in generated["sections"] if s["key"] == "status")
    system_group = next(g for g in status["groups"] if g["key"] == "system")
    assert not any(f["key"] == "FirmwareVersion" for f in system_group["fields"])


# ---------------------------------------------------------------------------
# Shape validation - mirrors js/definitions.js's validateDefinitions() closely enough to prove a
# generated file would load, without needing a Node round trip from a Python test suite.
# ---------------------------------------------------------------------------


def _shape_problems(defs: "dict[str, Any]") -> "list[str]":
    problems: list[str] = []
    if not isinstance(defs.get("schemaVersion"), str):
        problems.append("schemaVersion")
    if not isinstance(defs.get("device"), dict) or not isinstance(defs["device"].get("id"), str):
        problems.append("device.id")
    if not isinstance(defs.get("defaultPollIntervalMs"), (int, float)) or defs["defaultPollIntervalMs"] <= 0:
        problems.append("defaultPollIntervalMs")
    sections = defs.get("sections")
    if not isinstance(sections, list) or not sections:
        problems.append("sections")
        return problems
    section_keys = set()
    for section in sections:
        if not isinstance(section.get("key"), str) or not isinstance(section.get("label"), str):
            problems.append(f"section {section!r} key/label")
        section_keys.add(section.get("key"))
        rest = section.get("rest")
        if not isinstance(rest, dict) or not isinstance(rest.get("get"), str):
            problems.append(f"section {section.get('key')!r} rest.get")
        if section.get("pollGroup") not in ("live", "settings", "none"):
            problems.append(f"section {section.get('key')!r} pollGroup")
        groups = section.get("groups")
        if not isinstance(groups, list):
            problems.append(f"section {section.get('key')!r} groups")
            continue
        for group in groups:
            if not isinstance(group.get("key"), str) or not isinstance(group.get("label"), str):
                problems.append(f"group {group!r} key/label")
            if group.get("kind") == "errcount":
                if not isinstance(group.get("modules"), list):
                    problems.append(f"errcount group {group.get('key')!r} modules")
                continue
            if not isinstance(group.get("fields"), list):
                problems.append(f"group {group.get('key')!r} fields")
    if defs.get("landingSection") not in section_keys:
        problems.append("landingSection")
    return problems


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_generated_definitions_pass_shape_validation(repo_root: Path, src_dir: Path, device: str) -> None:
    assert _shape_problems(_generate(repo_root, src_dir, device)) == []


# ---------------------------------------------------------------------------
# Mandatory synthetic fixtures - proving generality beyond the 6 real, hand-verified devices
# ---------------------------------------------------------------------------


def test_novel_combo_fixture_generates_distinct_scd30_groups(fixtures_dir: Path, src_dir: Path) -> None:
    model = build_model(fixtures_dir / "novel_combo.toml", src_dir)
    generated = generate_definitions(model, src_dir)
    measurements = next(s for s in generated["sections"] if s["key"] == "measurements")
    scd30_group_keys = {g["key"] for g in measurements["groups"] if g["key"].startswith("SCD30")}
    assert scd30_group_keys == {"SCD30_primary", "SCD30_secondary"}
    labels = {g["key"]: g["label"] for g in measurements["groups"] if g["key"].startswith("SCD30")}
    assert labels["SCD30_primary"].endswith("(primary)")
    assert labels["SCD30_secondary"].endswith("(secondary)")


def test_novel_combo_fixture_only_wires_the_one_declared_warning_signal(fixtures_dir: Path, src_dir: Path) -> None:
    model = build_model(fixtures_dir / "novel_combo.toml", src_dir)
    generated = generate_definitions(model, src_dir)
    notification = next(s for s in generated["sections"] if s["key"] == "notification")
    auto_group = next(g for g in notification["groups"] if not g["key"].startswith(("flash", "pause")))
    warn_keys = {f["key"] for f in auto_group["fields"] if f["key"].startswith("Warn")}
    assert warn_keys == {"WarnCO2"}


def test_multi_instance_fixture_generates_successfully(fixtures_dir: Path, src_dir: Path) -> None:
    model = build_model(fixtures_dir / "multi_instance.toml", src_dir)
    generated = generate_definitions(model, src_dir)
    assert _shape_problems(generated) == []


# ---------------------------------------------------------------------------
# Failure paths - a hand-built minimal DeviceModel pointed at a deliberately mutated copy of one
# driver file, everything else read from the real src/ tree (mirrors the project's established
# "deliberately malformed fixture" testing convention, applied here to a source file rather than a
# TOML document since that's what this generator actually scans).
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
    assert "MeasInt" in sensors_fields


def test_missing_special_label_for_an_enum_schema_value_fails_loud(tmp_path: Path, src_dir: Path) -> None:
    mutated = _copy_driver_replacing(tmp_path, src_dir, "asy_bmp3xx_driver.py", ' special:127="127"', "")
    spec = InstanceSpec(
        driver="bmp3xx", name_ext="", fields={}, wiring={}, order_index=0,
        driver_info=DriverInfo(driver="bmp3xx", module="asy_bmp3xx_driver", class_name="BMP3xx_Reader", kind="sensor", source_path=mutated, needs_setup=True),
        resolved_name="BMP3XX",
    )
    model = DeviceModel(device="dev", path=Path("dev.toml"), doc={"device": {"name": "dev"}}, instances={("bmp3xx", ""): spec}, construction_order=[("bmp3xx", "")])
    with pytest.raises(BuildError, match="no matching special:127"):
        generate_definitions(model, src_dir)


def test_duplicate_mandatory_group_across_two_files_fails_loud(tmp_path: Path, src_dir: Path) -> None:
    # asy_ntp_client.py deliberately never declares its own @web-group for section=system
    # submitGroup=settings (system_service.py is the sole owner) - inject a second declaration to
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


def test_no_notification_instance_omits_notification_section(src_dir: Path) -> None:
    model = DeviceModel(device="dev", path=Path("dev.toml"), doc={"device": {"name": "dev"}}, instances={}, construction_order=[])
    generated = generate_definitions(model, src_dir)
    assert "notification" not in {s["key"] for s in generated["sections"]}
    assert {s["key"] for s in generated["sections"]} == {"measurements", "sensors", "networking", "system", "status"}


# ---------------------------------------------------------------------------
# CLI (scripts/build_website.sh's own build-time invocation, and manual use) -
# mirrors test_buildgen_generate.py's own CLI coverage.
# ---------------------------------------------------------------------------


def test_cli_writes_definitions_json_to_out(repo_root: Path, tmp_path: Path) -> None:
    from buildgen.definitions import main

    out_file = tmp_path / "wozi.json"
    exit_code = main([str(repo_root / "devices" / "wozi.toml"), "--out", str(out_file)])
    assert exit_code == 0
    written = json.loads(out_file.read_text())
    assert written["device"]["id"] == "wozi"
    assert written == generate_definitions(build_model(repo_root / "devices" / "wozi.toml", repo_root / "src"), repo_root / "src")


def test_cli_prints_to_stdout_when_out_is_omitted(repo_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from buildgen.definitions import main

    exit_code = main([str(repo_root / "devices" / "wozi.toml")])
    assert exit_code == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["device"]["id"] == "wozi"


def test_cli_reports_a_build_error_and_exits_nonzero(repo_root: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from buildgen.definitions import main

    missing_toml = tmp_path / "no-such-device.toml"
    exit_code = main([str(missing_toml)])
    assert exit_code == 1
    assert "buildgen:" in capsys.readouterr().err
