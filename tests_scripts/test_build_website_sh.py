"""Tests scripts/build_website.sh directly - structural checks (which paths get archived/renamed/
excluded) complementing tests/test_website_build_integration.py, which proves the served *content*
is correct. Same literal-path-string grep technique as test_build_frozen_html_sh.py."""

import subprocess


def _run_build_website(repo_root, device, output_path, check=True):
    return subprocess.run(
        ["scripts/build_website.sh", device, str(output_path)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=check,
    )


def test_wozi_device_stages_the_expected_files_renamed_and_flattened(repo_root, tmp_path):
    out_file = tmp_path / "frozen_website_wozi.py"
    _run_build_website(repo_root, "wozi", out_file)

    text = out_file.read_text()
    for expected in (
        "/index.html.gz",
        "/style.css.gz",
        "/definitions.json.gz",  # html/definitions/wozi.json, renamed+flattened - not nested under /definitions/
        "/js/app.js.gz",  # js/main.js, renamed at staging time - see scripts/build_website.sh's own comment
        "/js/definitions.js.gz",
        "/js/poll-manager.js.gz",
        "/js/render.js.gz",
        "/js/templates.js.gz",
        "/js/nav.js.gz",
    ):
        assert expected in text, expected


def test_prototype_only_files_are_never_staged(repo_root, tmp_path):
    out_file = tmp_path / "frozen_website_wozi.py"
    _run_build_website(repo_root, "wozi", out_file)

    text = out_file.read_text()
    for unexpected in ("/js/mock-server.js.gz", "/definitions/wozi.json.gz", "/definitions/dev.json.gz", "/dev.json.gz"):
        assert unexpected not in text, unexpected


def test_unknown_device_fails_with_no_matching_definitions_file(repo_root, tmp_path):
    out_file = tmp_path / "frozen_missing.py"
    result = _run_build_website(repo_root, "no-such-device", out_file, check=False)

    assert result.returncode != 0
    assert "no-such-device" in result.stderr
    assert not out_file.exists()


def test_output_path_argument_is_forwarded_to_build_frozen_html(repo_root, tmp_path):
    # A distinctive, non-default output path proves scripts/build_website.sh really forwards its
    # second argument through to scripts/build_frozen_html.sh rather than always writing to the
    # default frozen_modules/frozen_html.py location.
    out_file = tmp_path / "somewhere" / "custom_name.py"
    out_file.parent.mkdir()
    _run_build_website(repo_root, "wozi", out_file)

    assert out_file.is_file()
