"""Tests scripts/build_website.sh directly - structural checks (which paths get archived/renamed/
excluded) complementing tests/test_website_build_integration.py, which proves the served *content*
is correct. Same literal-path-string grep technique as test_build_frozen_html_sh.py."""

import json
import re
import subprocess
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES


def _run_build_website(repo_root: Path, device: str, output_path: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(repo_root / "scripts" / "build_website.sh"), device, str(output_path)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=check,
    )


def test_a_device_stages_the_expected_files_renamed_and_flattened(repo_root: Path, tmp_path: Path) -> None:
    out_file = tmp_path / "frozen_website.py"
    _run_build_website(repo_root, DEVICE_NAMES[0], out_file)

    text = out_file.read_text()
    for expected in (
        "/index.html.gz",
        "/js/app.js.gz",  # the one production bundle: js/main.js's import closure, concatenated by
        # scripts/_stage_website.py (SPECIFICATION.md Part H.7), not one file per module.
    ):
        assert expected in text, expected

    # The seven production modules must NOT be staged individually any more, only the bundle
    # above, and style.css and definitions.json must not be staged at all - both are inlined into
    # index.html at build time. This file checks staging; the integration test checks content.
    for not_staged in (
        "/js/definitions.js.gz",
        "/js/poll-manager.js.gz",
        "/js/render.js.gz",
        "/js/templates.js.gz",
        "/js/nav.js.gz",
        "/js/field-format.js.gz",
        "/style.css.gz",
        "/definitions.json.gz",
    ):
        assert not_staged not in text, not_staged


def test_prototype_only_files_are_never_staged(repo_root: Path, tmp_path: Path) -> None:
    out_file = tmp_path / "frozen_website.py"
    _run_build_website(repo_root, DEVICE_NAMES[0], out_file)

    text = out_file.read_text()
    unexpected_paths = (
        "/js/mock-server.js.gz",
        "/definitions.json.gz",
        *(f"/definitions/{d}.json.gz" for d in DEVICE_NAMES),
        *(f"/{d}.json.gz" for d in DEVICE_NAMES),
    )
    for unexpected in unexpected_paths:
        assert unexpected not in text, unexpected


def test_unknown_device_fails_naming_its_missing_toml(repo_root: Path, tmp_path: Path) -> None:
    out_file = tmp_path / "frozen_missing.py"
    result = _run_build_website(repo_root, "no-such-device", out_file, check=False)

    assert result.returncode != 0
    # The device TOML is the one source the buildgen generation step reads; nothing else is looked for.
    assert "devices/no-such-device.toml" in result.stderr
    assert "html/definitions" not in result.stderr
    assert not out_file.exists()


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_device_inlines_generated_definitions_and_never_stages_them(repo_root: Path, tmp_path: Path, device: str) -> None:
    # Every device's definitions come from the buildgen generation step and are inlined into
    # index.html, never staged as their own frozen file: a scratch-directory mix-up once froze
    # one as a stray /definitions.json.gz.
    out_file = tmp_path / "frozen_website.py"
    _run_build_website(repo_root, device, out_file)

    text = out_file.read_text()
    assert "/index.html.gz" in text
    assert "/js/app.js.gz" in text
    assert "/definitions.json.gz" not in text


def test_device_toml_that_fails_buildgen_validation_fails_the_build_loud(repo_root: Path, tmp_path: Path) -> None:
    # The buildgen generation step's other failure surface: a devices/<device>.toml that exists
    # but fails buildgen's validation, as opposed to no TOML at all.

    # build_website.sh always cd's to the repo root, so this needs a real file on disk: the
    # fixture lives in buildgen_fixtures/ and is copied into devices/ under a test-only name,
    # removed again in `finally` even when an assertion fails.
    device = "zz_test_malformed_buildgen_fixture"
    device_toml = repo_root / "devices" / f"{device}.toml"
    assert not device_toml.exists(), "sanity: this test-only device name must not collide with a real device"
    fixture = (repo_root / "tests_scripts" / "buildgen_fixtures" / "malformed_missing_device_table.toml").read_text()

    device_toml.write_text(fixture)
    try:
        out_file = tmp_path / f"frozen_website_{device}.py"
        result = _run_build_website(repo_root, device, out_file, check=False)

        assert result.returncode != 0
        assert "missing [device] table" in result.stderr
        assert not out_file.exists()
    finally:
        device_toml.unlink()


def test_output_path_argument_is_forwarded_to_build_frozen_html(repo_root: Path, tmp_path: Path) -> None:
    # A distinctive, non-default output path proves scripts/build_website.sh really forwards its
    # second argument through to scripts/build_frozen_html.sh rather than always writing to the
    # default frozen_modules/frozen_html.py location.
    out_file = tmp_path / "somewhere" / "custom_name.py"
    out_file.parent.mkdir()
    _run_build_website(repo_root, DEVICE_NAMES[0], out_file)

    assert out_file.is_file()


def test_stage_only_fills_the_given_directory_and_freezes_nothing(repo_root: Path, tmp_path: Path) -> None:
    # The staged page html-validate lints: the stager's output in a directory created for it, and no
    # build_frozen_html.sh run (its "Wrote" line) and no frozen module anywhere.
    stage = tmp_path / "nested" / "stage"
    result = subprocess.run([str(repo_root / "scripts" / "build_website.sh"), "--stage-only", DEVICE_NAMES[0], str(stage)], cwd=repo_root, capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr
    assert sorted(p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file()) == ["index.html", "js/app.js"]
    assert "Wrote " not in result.stdout
    assert not list(tmp_path.rglob("*.py"))
    inlined = re.search(r'<script type="application/json" id="inlined-definitions">(.*?)</script>', (stage / "index.html").read_text(), re.DOTALL)
    assert inlined is not None
    assert json.loads(inlined.group(1))["device"]["id"] == DEVICE_NAMES[0]


def test_stage_only_without_a_stage_directory_is_a_usage_error(repo_root: Path) -> None:
    result = subprocess.run([str(repo_root / "scripts" / "build_website.sh"), "--stage-only", DEVICE_NAMES[0]], cwd=repo_root, capture_output=True, text=True, check=False)
    assert result.returncode == 2, (result.returncode, result.stderr)
    assert "Usage: scripts/build_website.sh [--stage-only] <device> [output]" in result.stderr
