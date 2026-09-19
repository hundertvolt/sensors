"""Tests scripts/build_website.sh directly - structural checks (which paths get archived/renamed/
excluded) complementing tests/test_website_build_integration.py, which proves the served *content*
is correct. Same literal-path-string grep technique as test_build_frozen_html_sh.py."""

import subprocess
from pathlib import Path


def _run_build_website(repo_root: Path, device: str, output_path: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(repo_root / "scripts" / "build_website.sh"), device, str(output_path)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=check,
    )


def test_wozi_device_stages_the_expected_files_renamed_and_flattened(repo_root: Path, tmp_path: Path) -> None:
    out_file = tmp_path / "frozen_website_wozi.py"
    _run_build_website(repo_root, "wozi", out_file)

    text = out_file.read_text()
    for expected in (
        "/index.html.gz",
        "/js/app.js.gz",  # the bundled production JS (field-format.js, poll-manager.js, templates.js,
        # definitions.js, render.js, nav.js, main.js concatenated - see scripts/build_website.sh's
        # own "Bundling" comment for why) - a single file now, not seven separate ones
        # (SPECIFICATION.md Part H.7).
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
    out_file = tmp_path / "frozen_website_wozi.py"
    _run_build_website(repo_root, "wozi", out_file)

    text = out_file.read_text()
    for unexpected in ("/js/mock-server.js.gz", "/definitions/wozi.json.gz", "/definitions/dev.json.gz", "/dev.json.gz"):
        assert unexpected not in text, unexpected


def test_unknown_device_fails_with_no_matching_definitions_file(repo_root: Path, tmp_path: Path) -> None:
    out_file = tmp_path / "frozen_missing.py"
    result = _run_build_website(repo_root, "no-such-device", out_file, check=False)

    assert result.returncode != 0
    # Both halves of the fallback's own failure message - it's genuinely missing both a
    # hand-written definitions file AND a devices/<device>.toml to generate one from.
    assert "html/definitions/no-such-device.json" in result.stderr
    assert "devices/no-such-device.toml" in result.stderr
    assert not out_file.exists()


def test_device_without_a_hand_written_definitions_file_generates_one_via_buildgen(repo_root: Path, tmp_path: Path) -> None:
    # Four devices have no hand-written definitions.json, so build_website.sh generates one on
    # the fly through buildgen rather than failing - which is what lets build_firmware.py build
    # them at all (Part L.4). "arzi" stands in for all four.
    definitions_file = repo_root / "html" / "definitions" / "arzi.json"
    assert not definitions_file.exists(), "sanity: this test's whole premise is that arzi has no hand-written definitions.json"

    out_file = tmp_path / "frozen_website_arzi.py"
    _run_build_website(repo_root, "arzi", out_file)

    text = out_file.read_text()
    assert "/index.html.gz" in text
    assert "/js/app.js.gz" in text
    # The generated definitions.json must be inlined like the hand-written ones, never staged as
    # its own frozen file. A regression guard: an earlier fallback wrote it into the served stage
    # directory rather than a scratch one, and it reappeared here as a stray /definitions.json.gz.
    assert "/definitions.json.gz" not in text


def test_device_toml_that_fails_buildgen_validation_fails_the_build_loud(repo_root: Path, tmp_path: Path) -> None:
    # The fallback's other failure surface: a devices/<device>.toml that exists but fails
    # buildgen's validation, as opposed to neither file existing at all.

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


def test_every_real_js_and_html_file_is_accounted_for_by_the_staging_script(repo_root: Path) -> None:
    # build_website.sh's cp lists are hand-kept, not derived from directory contents, so a new
    # html/ or js/ file would silently ship without it - or without a deliberate prototype-only
    # decision. Cross-checking the directories against the script's source makes that loud.
    script_text = (repo_root / "scripts" / "build_website.sh").read_text()

    html_root_files = {p.name for p in (repo_root / "html").iterdir() if p.is_file()}
    for name in html_root_files:
        assert name in script_text, f"html/{name} exists but isn't referenced by build_website.sh"

    js_files = {p.name for p in (repo_root / "js").glob("*.js")}
    # js/main.js is staged under a different name (see build_website.sh's own comment) - checked
    # for by content ("main.js" itself), not "js/app.js.gz" like the others.
    for name in js_files:
        assert name in script_text, f"js/{name} exists but isn't referenced by build_website.sh"


def test_output_path_argument_is_forwarded_to_build_frozen_html(repo_root: Path, tmp_path: Path) -> None:
    # A distinctive, non-default output path proves scripts/build_website.sh really forwards its
    # second argument through to scripts/build_frozen_html.sh rather than always writing to the
    # default frozen_modules/frozen_html.py location.
    out_file = tmp_path / "somewhere" / "custom_name.py"
    out_file.parent.mkdir()
    _run_build_website(repo_root, "wozi", out_file)

    assert out_file.is_file()
