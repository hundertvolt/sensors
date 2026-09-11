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

    # The seven production modules must NOT be individually staged any more - only the bundle
    # above. style.css and definitions.json (html/definitions/wozi.json) must NOT be staged as
    # separate files either any more - both are now inlined directly into index.html at build time
    # (see build_website.sh's own "Inlining" comment) - test_website_build_integration.py's own
    # test_inlined_definitions_and_stylesheet_replace_the_two_separately_staged_files proves the
    # inlined content itself is correct; this file only checks staging, not content.
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
    # arzi/klkizi/grkizi/schlafzi have no html/definitions/<device>.json at all (only wozi/dev do) -
    # scripts/build_website.sh falls back to generating one on the fly via buildgen instead of
    # failing, which is what actually lets scripts/build_firmware.py build these 4 devices at all
    # (BUILD_CHAIN_PLAN.md's Session 6 account). Picks "arzi" as a concrete stand-in for all four.
    definitions_file = repo_root / "html" / "definitions" / "arzi.json"
    assert not definitions_file.exists(), "sanity: this test's whole premise is that arzi has no hand-written definitions.json"

    out_file = tmp_path / "frozen_website_arzi.py"
    _run_build_website(repo_root, "arzi", out_file)

    text = out_file.read_text()
    assert "/index.html.gz" in text
    assert "/js/app.js.gz" in text
    # The generated definitions.json must be inlined into index.html, exactly like the two
    # hand-written ones - never staged as its own separate frozen file. Regression guard: an
    # earlier version of this fallback wrote the generated file directly into the served stage
    # directory instead of a separate scratch directory, and it reappeared here as a stray
    # /definitions.json.gz (scripts/build_website.sh's own "scratch_dir" comment).
    assert "/definitions.json.gz" not in text


def test_every_real_js_and_html_file_is_accounted_for_by_the_staging_script(repo_root: Path) -> None:
    # scripts/build_website.sh's cp lists (html root files, production js/ modules) are hand-kept,
    # not derived from directory contents - a new html/*.html or js/*.js file added later would
    # silently ship without it (or without a deliberate "stays prototype-only" decision) with no
    # test catching the drift. Cross-checks the real directories against the script's own source,
    # so a mismatch fails loudly instead of silently under-shipping the built website.
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
