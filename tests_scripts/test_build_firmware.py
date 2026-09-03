"""Tests scripts/build_firmware.py (SPECIFICATION.md Part B.11's real firmware.uf2 assembly
script). Fast tests cover its own logic (_boot_py()/_MANIFEST_TEMPLATE content, build_stage_dir()'s
file assembly - including its per-device boot-module selection, DEV_HARDWARE_BASELINE_PLAN.md
decision 2 - CLI error paths) without the real, minutes-long ARM compile - see
test_real_firmware_build_produces_a_valid_uf2's own comment for the one test that does that."""

import importlib.util
import os
import subprocess
import sys

import pytest


@pytest.fixture(scope="session")
def build_firmware(repo_root):
    """Imports scripts/build_firmware.py as a real module (it's a `uv run`-style standalone
    script, not a package member) so build_stage_dir()/_boot_py()/_MANIFEST_TEMPLATE can be checked
    directly instead of only through subprocess/CLI behavior."""
    module_path = repo_root / "scripts" / "build_firmware.py"
    spec = importlib.util.spec_from_file_location("build_firmware", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("device", ["wozi", "dev"])
def test_boot_py_imports_the_matching_device_boot_and_never_the_repos_own_modules_boot(build_firmware, device):
    # See scripts/build_firmware.py's own module docstring: _boot_py(device) is the port's stock
    # ports/rp2/modules/_boot.py content plus one added `import <device>_boot` line - CLAUDE.md's
    # hard rule against touching/deriving from this repo's own modules/_boot.py (its
    # still-unresolved literal "import sensortask.py" mechanism, see BACKLOG.md #1) must never leak
    # into this new, from-scratch boot file. Parametrized over both real devices - the exact
    # regression this covers (DEV_HARDWARE_BASELINE_PLAN.md decision 2) is that this must pick the
    # *correct*, distinct boot module per device, not just always resolve to wozi's.
    boot_py = build_firmware._boot_py(device)
    assert f"import {device}_boot" in boot_py
    other_device = "dev" if device == "wozi" else "wozi"
    assert f"import {other_device}_boot" not in boot_py
    assert "sensortask" not in boot_py
    assert "vfs.mount(fs, \"/\")" in boot_py
    assert "rp2.Flash()" in boot_py


def test_build_stage_dir_rejects_a_device_with_no_boot_entry_file(build_firmware, micropython_dir, tmp_path):
    # DEV_HARDWARE_BASELINE_PLAN.md decision 2's own explicit requirement: fail loud, before
    # staging anything, rather than silently falling back to some other device's boot module.
    with pytest.raises(RuntimeError, match="no-such-device"):
        build_firmware.build_stage_dir(tmp_path, "no-such-device", micropython_dir)


def test_manifest_template_states_every_required_module_and_no_default_board_manifest(build_firmware):
    manifest = build_firmware._MANIFEST_TEMPLATE.format(stage_dir="/tmp/some-stage-dir")
    for expected in (
        'include("$(MPY_DIR)/extmod/asyncio")',
        'require("onewire")',
        'require("ds18x20")',
        'require("dht")',
        'require("neopixel")',
        'require("bundle-networking")',
        'require("aioble")',
        "freeze('/tmp/some-stage-dir')",
    ):
        assert expected in manifest, expected
    # The board's own default manifest (boards/RPI_PICO_W/manifest.py -> boards/manifest.py) must
    # never be included here - its own freeze("$(PORT_DIR)/modules") would freeze a second,
    # different _boot.py under the same frozen name, silently shadowing (or colliding with) the
    # one this script builds. See the module docstring for the full collision mechanics.
    assert "boards/RPI_PICO_W/manifest.py" not in manifest
    assert "$(PORT_DIR)/modules" not in manifest


@pytest.mark.parametrize("device", ["wozi", "dev"])
def test_build_stage_dir_assembles_every_expected_file(build_firmware, repo_root, micropython_dir, tmp_path, device):
    build_firmware.build_stage_dir(tmp_path, device, micropython_dir)

    staged = {p.name for p in tmp_path.iterdir()}
    src_files = {p.name for p in (repo_root / "src").glob("*.py")}
    assert src_files, "sanity: src/ should contain at least one .py file"
    assert src_files <= staged

    boot_module_file = f"{device}_boot.py"
    for expected in ("microdot.py", boot_module_file, "_boot.py", "frozen_html.py", "rp2.py"):
        assert expected in staged, expected

    assert (tmp_path / "_boot.py").read_text() == build_firmware._boot_py(device)
    # boot_entry/<device>_boot.py is copied verbatim, not modules/_boot.py (the protected file) -
    # confirmed by content match against the real source, not just filename presence. This is also
    # the regression coverage DEV_HARDWARE_BASELINE_PLAN.md decision 2 asked for: each device's own
    # staged _boot.py imports its own, distinct boot module - not silently falling back to wozi's.
    assert (tmp_path / boot_module_file).read_text() == (repo_root / "boot_entry" / boot_module_file).read_text()
    assert f"import {device}_boot" in (tmp_path / "_boot.py").read_text()
    other_device = "dev" if device == "wozi" else "wozi"
    assert f"import {other_device}_boot" not in (tmp_path / "_boot.py").read_text()
    assert (tmp_path / "microdot.py").read_text() == (repo_root / "ext" / "microdot.py").read_text()


@pytest.mark.parametrize("device", ["wozi", "dev"])
def test_build_stage_dir_strips_type_checking_blocks_from_staged_src_files(
    build_firmware, repo_root, micropython_dir, tmp_path, device
):
    # config_manager.py is a real, known if TYPE_CHECKING: user (BACKLOG.md's measured baseline
    # for this saving) - its staged copy must have the guard stripped even though the real src/
    # file (never touched by this build) keeps it, per CLAUDE.md's hard rule against editing src/
    # itself for a build-only concern.
    build_firmware.build_stage_dir(tmp_path, device, micropython_dir)
    staged_text = (tmp_path / "config_manager.py").read_text()
    assert "TYPE_CHECKING" not in staged_text
    assert "TYPE_CHECKING" in (repo_root / "src" / "config_manager.py").read_text()


@pytest.mark.parametrize("device", ["wozi", "dev"])
def test_build_stage_dir_frozen_html_contains_the_real_website_not_the_stub(build_firmware, micropython_dir, tmp_path, device):
    build_firmware.build_stage_dir(tmp_path, device, micropython_dir)
    frozen_html_text = (tmp_path / "frozen_html.py").read_text()
    assert "/index.html.gz" in frozen_html_text
    # /js/app.js.gz alone already distinguishes this from html_stub's own frozen build (which has
    # no js/ directory at all - see test_build_frozen_html_sh.py's own stub-side coverage). No
    # separate /definitions.json.gz or /style.css.gz check any more - both are inlined directly
    # into index.html at build time now (scripts/build_website.sh's own "Inlining" comment,
    # SPECIFICATION.md Part H.7), never staged as their own files.
    assert "/js/app.js.gz" in frozen_html_text


def _run_cli(repo_root, args, check=False):
    return subprocess.run(
        [sys.executable, "scripts/build_firmware.py", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=check,
    )


def test_cli_missing_definitions_file_fails_fast(repo_root, tmp_path):
    result = _run_cli(repo_root, ["no-such-device", "--output", str(tmp_path / "out.uf2")])
    assert result.returncode != 0
    assert "no-such-device" in result.stderr


def test_cli_missing_toolchain_dir_fails_before_attempting_a_build(repo_root, tmp_path):
    result = _run_cli(
        repo_root,
        ["wozi", "--output", str(tmp_path / "out.uf2"), "--toolchain-dir", str(tmp_path / "no-toolchain-here")],
    )
    assert result.returncode != 0
    assert "no-toolchain-here" in result.stderr or "toolchain" in result.stderr.lower()
    assert not (tmp_path / "out.uf2").exists()


@pytest.mark.skipif(
    os.environ.get("RUN_SLOW_FIRMWARE_BUILD") != "1",
    reason="real ARM firmware compile, several minutes - opt in with RUN_SLOW_FIRMWARE_BUILD=1 "
    "(see .github/workflows/ci.yml's firmware-build-verify job, which sets it)",
)
def test_real_firmware_build_produces_a_valid_uf2(repo_root, tmp_path):
    # The actual end-to-end proof SPECIFICATION.md Part B.11 asked for: a real src/-based
    # firmware.uf2, built by the exact same script/manifest a device build would use, not just its
    # staging logic checked in isolation above. Needs the real toolchain already installed
    # (uv run toolchain/setup_toolchain.py setup) - scripts/test.sh and CI's unit-tests job both
    # already provision it before this suite runs.
    output = tmp_path / "firmware-wozi.uf2"
    result = _run_cli(repo_root, ["wozi", "--output", str(output)])
    assert result.returncode == 0, result.stdout + result.stderr

    assert output.is_file()
    data = output.read_bytes()
    assert data[:4] == b"UF2\n"
    assert len(data) > 0 and len(data) % 512 == 0  # UF2 files are a sequence of fixed 512-byte blocks
