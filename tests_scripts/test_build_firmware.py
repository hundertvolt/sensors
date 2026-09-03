"""Tests scripts/build_firmware.py (SPECIFICATION.md Part B.11's real firmware.uf2 assembly
script). Fast tests cover its own logic (_MANIFEST_TEMPLATE content, build_stage_dir()'s file
assembly - including its per-device boot-module selection, DEV_HARDWARE_BASELINE_PLAN.md
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
    script, not a package member) so build_stage_dir()/_MANIFEST_TEMPLATE can be checked
    directly instead of only through subprocess/CLI behavior."""
    module_path = repo_root / "scripts" / "build_firmware.py"
    spec = importlib.util.spec_from_file_location("build_firmware", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_stage_dir_rejects_a_device_with_no_boot_entry_file(build_firmware, tmp_path):
    # DEV_HARDWARE_BASELINE_PLAN.md decision 2's own explicit requirement: fail loud, before
    # staging anything, rather than silently falling back to some other device's boot module.
    with pytest.raises(RuntimeError, match="no-such-device"):
        build_firmware.build_stage_dir(tmp_path, "no-such-device")


def test_manifest_template_includes_the_default_board_manifest_and_freezes_stage_dir(build_firmware):
    # Unlike this script's own previous approach (a custom _boot.py, which meant skipping the
    # default board manifest entirely to avoid a colliding second freeze() of "_boot.py" - see
    # SPECIFICATION.md Part F.1 for why that broke USB entirely), each device's boot module is now
    # frozen under "main.py" instead, so the default manifest (asyncio/neopixel/bundle-networking/
    # ... plus the stock, always-returns _boot.py + rp2.py) is reused unchanged.
    manifest = build_firmware._MANIFEST_TEMPLATE.format(board="RPI_PICO_W", stage_dir="/tmp/some-stage-dir")
    assert 'include("$(PORT_DIR)/boards/RPI_PICO_W/manifest.py")' in manifest
    assert "freeze('/tmp/some-stage-dir')" in manifest


@pytest.mark.parametrize("device", ["wozi", "dev"])
def test_build_stage_dir_assembles_every_expected_file(build_firmware, repo_root, tmp_path, device):
    build_firmware.build_stage_dir(tmp_path, device)

    staged = {p.name for p in tmp_path.iterdir()}
    src_files = {p.name for p in (repo_root / "src").glob("*.py")}
    assert src_files, "sanity: src/ should contain at least one .py file"
    assert src_files <= staged

    for expected in ("microdot.py", "main.py", "frozen_html.py"):
        assert expected in staged, expected

    # boot_entry/<device>_boot.py is staged under the name "main.py" (see
    # scripts/build_firmware.py's own docstring for why this is load-bearing, not cosmetic), copied
    # verbatim content-wise, not modules/_boot.py (the protected file) - confirmed by content match
    # against the real source, not just filename presence. This is also the regression coverage
    # DEV_HARDWARE_BASELINE_PLAN.md decision 2 asked for: each device stages its own, distinct boot
    # module content - not silently falling back to wozi's.
    boot_entry_file = repo_root / "boot_entry" / f"{device}_boot.py"
    assert (tmp_path / "main.py").read_text() == boot_entry_file.read_text()
    other_device = "dev" if device == "wozi" else "wozi"
    other_boot_entry_file = repo_root / "boot_entry" / f"{other_device}_boot.py"
    assert (tmp_path / "main.py").read_text() != other_boot_entry_file.read_text()
    assert (tmp_path / "microdot.py").read_text() == (repo_root / "ext" / "microdot.py").read_text()


@pytest.mark.parametrize("device", ["wozi", "dev"])
def test_build_stage_dir_strips_type_checking_blocks_from_staged_src_files(build_firmware, repo_root, tmp_path, device):
    # config_manager.py is a real, known if TYPE_CHECKING: user (BACKLOG.md's measured baseline
    # for this saving) - its staged copy must have the guard stripped even though the real src/
    # file (never touched by this build) keeps it, per CLAUDE.md's hard rule against editing src/
    # itself for a build-only concern.
    build_firmware.build_stage_dir(tmp_path, device)
    staged_text = (tmp_path / "config_manager.py").read_text()
    assert "TYPE_CHECKING" not in staged_text
    assert "TYPE_CHECKING" in (repo_root / "src" / "config_manager.py").read_text()


@pytest.mark.parametrize("device", ["wozi", "dev"])
def test_build_stage_dir_frozen_html_contains_the_real_website_not_the_stub(build_firmware, tmp_path, device):
    build_firmware.build_stage_dir(tmp_path, device)
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


@pytest.mark.parametrize("device", ["wozi", "dev"])
@pytest.mark.skipif(
    os.environ.get("RUN_SLOW_FIRMWARE_BUILD") != "1",
    reason="real ARM firmware compile, several minutes - opt in with RUN_SLOW_FIRMWARE_BUILD=1 "
    "(see .github/workflows/ci.yml's firmware-build-verify job, which sets it)",
)
def test_real_firmware_build_produces_a_valid_uf2(repo_root, tmp_path, device):
    # The actual end-to-end proof SPECIFICATION.md Part B.11 asked for: a real src/-based
    # firmware.uf2, built by the exact same script/manifest a device build would use, not just its
    # staging logic checked in isolation above. Needs the real toolchain already installed
    # (uv run toolchain/setup_toolchain.py setup) - scripts/test.sh and CI's unit-tests job both
    # already provision it before this suite runs. Parametrized over both real devices - each has
    # its own distinct boot_entry/<device>_boot.py that must actually compile and freeze cleanly.
    output = tmp_path / f"firmware-{device}.uf2"
    result = _run_cli(repo_root, [device, "--output", str(output)])
    assert result.returncode == 0, result.stdout + result.stderr

    assert output.is_file()
    data = output.read_bytes()
    assert data[:4] == b"UF2\n"
    assert len(data) > 0 and len(data) % 512 == 0  # UF2 files are a sequence of fixed 512-byte blocks
