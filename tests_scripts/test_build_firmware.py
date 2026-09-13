"""Tests scripts/build_firmware.py (SPECIFICATION.md Part B.11's real firmware.uf2 assembly
script) - its own logic (_MANIFEST_TEMPLATE, build_stage_dir()'s per-device boot-module selection,
CLI error paths) without the minutes-long ARM compile."""

# The one test that does run the real ARM build carries its own comment - see
# test_real_firmware_build_produces_a_valid_uf2.

import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
from _script_loader import load_script_module


@pytest.fixture(scope="session")
def build_firmware(repo_root: Path) -> ModuleType:
    """Imports scripts/build_firmware.py as a real module (it's a `uv run`-style standalone
    script, not a package member) so build_stage_dir()/_MANIFEST_TEMPLATE can be checked
    directly instead of only through subprocess/CLI behavior."""
    return load_script_module(repo_root / "scripts" / "build_firmware.py", "build_firmware")


def test_build_stage_dir_rejects_a_device_with_no_matching_toml(build_firmware: ModuleType, tmp_path: Path) -> None:
    # Fail loud, before staging anything - build_stage_dir() converts buildgen's own BuildError
    # (no devices/no-such-device.toml to read) into a plain RuntimeError, matching this function's
    # contract of raising RuntimeError for every build-impossible condition.
    with pytest.raises(RuntimeError, match="no-such-device"):
        build_firmware.build_stage_dir(tmp_path, "no-such-device")


def test_build_stage_dir_rejects_a_frozen_module_resolving_to_neither_src_nor_ext(build_firmware: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Defensive check for a buildgen/build_firmware.py contract mismatch that should never happen
    # given buildgen's own current guarantees - simulated by injecting a fake GeneratedDevice (a
    # plain SimpleNamespace, since build_stage_dir only ever reads .model.device/.module_source/
    # .boot_entry_source/.frozen_modules off it) whose frozen_modules set names a module neither
    # src/ nor ext/ actually has.
    from types import SimpleNamespace

    fake_generated = SimpleNamespace(
        model=SimpleNamespace(device="wozi"),
        module_source="# fake module\n",
        boot_entry_source="# fake boot\n",
        frozen_modules=frozenset({"this_module_does_not_exist_anywhere"}),
    )
    monkeypatch.setattr(build_firmware, "generate_device", lambda *_args, **_kwargs: fake_generated)

    with pytest.raises(RuntimeError, match="this_module_does_not_exist_anywhere"):
        build_firmware.build_stage_dir(tmp_path, "wozi")


def test_build_stage_dir_rejects_a_frozen_module_colliding_with_a_reserved_staging_name(build_firmware: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The other defensive check: a resolved frozen module whose own filename collides with one of
    # this build's own reserved names (main.py/frozen_html.py/sensortask_<device>.py) must fail
    # loud rather than silently overwrite (or be overwritten by) the real entry/website content.
    # No real src/ file is named "main.py" today, so REPO_ROOT is patched to a fake tree that has
    # one, purely to make the collision reachable.
    from types import SimpleNamespace

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("# dummy colliding module\n")
    monkeypatch.setattr(build_firmware, "REPO_ROOT", tmp_path)

    fake_generated = SimpleNamespace(
        model=SimpleNamespace(device="wozi"),
        module_source="# fake module\n",
        boot_entry_source="# fake boot\n",
        frozen_modules=frozenset({"main"}),
    )
    monkeypatch.setattr(build_firmware, "generate_device", lambda *_args, **_kwargs: fake_generated)

    stage_dir = tmp_path / "stage"
    stage_dir.mkdir()
    with pytest.raises(RuntimeError, match=r"main\.py"):
        build_firmware.build_stage_dir(stage_dir, "wozi")


def test_manifest_template_includes_the_default_board_manifest_and_freezes_stage_dir(build_firmware: ModuleType, tmp_path: Path) -> None:
    # Unlike this script's own previous approach (a custom _boot.py, which meant skipping the
    # default board manifest entirely to avoid a colliding second freeze() of "_boot.py" - see
    # SPECIFICATION.md Part F.1 for why that broke USB entirely), each device's boot module is now
    # frozen under "main.py" instead, so the default manifest (asyncio/neopixel/bundle-networking/
    # ... plus the stock, always-returns _boot.py + rp2.py) is reused unchanged.
    # str(), not the Path itself: the template interpolates {stage_dir!r} and build_firmware.py's
    # own call site passes str(stage_dir), so a Path here would render as PosixPath('...').
    stage_dir = str(tmp_path / "some-stage-dir")
    manifest = build_firmware._MANIFEST_TEMPLATE.format(board="RPI_PICO_W", stage_dir=stage_dir)
    assert 'include("$(PORT_DIR)/boards/RPI_PICO_W/manifest.py")' in manifest
    assert f"freeze('{stage_dir}')" in manifest


@pytest.mark.parametrize("device", ["wozi", "dev"])
def test_build_stage_dir_stages_exactly_the_computed_frozen_modules(build_firmware: ModuleType, repo_root: Path, tmp_path: Path, device: str) -> None:
    # No longer "every src/*.py file unconditionally" - only this device's own buildgen-computed
    # dependency closure (BUILD_CHAIN_PLAN.md's "Frozen-module selection is dependency-driven",
    # wired into this script by this session) gets staged, a real, smaller-firmware behavior change
    # from this script's own pre-buildgen shape.
    from buildgen.frozen_modules import compute_frozen_modules
    from buildgen.validate import build_model

    build_firmware.build_stage_dir(tmp_path, device)

    model = build_model(repo_root / "devices" / f"{device}.toml", repo_root / "src")
    expected_modules = compute_frozen_modules(model, repo_root / "src", repo_root / "ext")
    assert expected_modules, "sanity: a real device should need at least one frozen module"

    staged = {p.name for p in tmp_path.iterdir()}
    assert {f"{m}.py" for m in expected_modules} <= staged

    for expected in ("microdot.py", "main.py", "frozen_html.py", f"sensortask_{device}.py"):
        assert expected in staged, expected

    # A src/ module outside this device's own computed dependency closure (e.g. a driver no real
    # device today wires in) must NOT be staged either - proves this is a real, device-scoped
    # subset, not "every src/*.py file" still happening to pass the assertion above.
    all_src_modules = {p.stem for p in (repo_root / "src").glob("*.py")}
    unrelated_modules = all_src_modules - expected_modules
    assert unrelated_modules, "sanity: src/ should contain at least one module outside every real device's own dependency closure"
    assert not ({f"{m}.py" for m in unrelated_modules} & staged)

    assert (repo_root / "ext" / "microdot.py").read_text() == (tmp_path / "microdot.py").read_text()


@pytest.mark.parametrize("device", ["wozi", "dev"])
def test_build_stage_dir_writes_the_generated_entry_module_and_boot_entry(build_firmware: ModuleType, repo_root: Path, tmp_path: Path, device: str, monkeypatch: pytest.MonkeyPatch) -> None:
    # The generated device entry module (sensortask_<device>.py-equivalent) and its boot entry -
    # freshly generated text, never copied from boot_entry/<device>_boot.py (retired, this session -
    # see buildgen.codegen.generate_boot_entry_source()) - staged under "main.py" (see
    # scripts/build_firmware.py's own docstring for why this is load-bearing, not cosmetic).
    # Content-matched against buildgen's own generator directly, not just filename presence: each
    # device stages its own, distinct boot module content, not silently falling back to wozi's.
    from buildgen.codegen import generate_boot_entry_source
    from buildgen.generate import generate_device

    # Pins generate_device()'s own default build_date so build_stage_dir()'s internal call and this
    # test's separate reference call below embed the identical timestamp, rather than racing a real
    # wall clock against each other (BUILD_CHAIN_PLAN.md Session 7).
    monkeypatch.setattr("buildgen.generate.current_build_date", lambda: "2026-09-12T10:00:00Z")

    build_firmware.build_stage_dir(tmp_path, device)

    generated = generate_device(repo_root / "devices" / f"{device}.toml", repo_root / "src", repo_root / "ext")
    assert (tmp_path / f"sensortask_{device}.py").read_text() == generated.module_source
    assert (tmp_path / "main.py").read_text() == generate_boot_entry_source(device)
    other_device = "dev" if device == "wozi" else "wozi"
    assert (tmp_path / "main.py").read_text() != generate_boot_entry_source(other_device)


@pytest.mark.parametrize("device", ["wozi", "dev"])
def test_build_stage_dir_strips_type_checking_blocks_from_staged_src_files(build_firmware: ModuleType, repo_root: Path, tmp_path: Path, device: str) -> None:
    # config_manager.py is a real, known if TYPE_CHECKING: user (BACKLOG.md's measured baseline
    # for this saving) - its staged copy must have the guard stripped even though the real src/
    # file (never touched by this build) keeps it, per CLAUDE.md's hard rule against editing src/
    # itself for a build-only concern.
    build_firmware.build_stage_dir(tmp_path, device)
    staged_text = (tmp_path / "config_manager.py").read_text()
    assert "TYPE_CHECKING" not in staged_text
    assert "TYPE_CHECKING" in (repo_root / "src" / "config_manager.py").read_text()


@pytest.mark.parametrize("device", ["wozi", "dev"])
def test_build_stage_dir_frozen_html_contains_the_real_website_not_the_stub(build_firmware: ModuleType, tmp_path: Path, device: str) -> None:
    build_firmware.build_stage_dir(tmp_path, device)
    frozen_html_text = (tmp_path / "frozen_html.py").read_text()
    assert "/index.html.gz" in frozen_html_text
    # /js/app.js.gz alone already distinguishes this from html_stub's own frozen build (which has
    # no js/ directory at all - see test_build_frozen_html_sh.py's own stub-side coverage). No
    # separate /definitions.json.gz or /style.css.gz check any more - both are inlined directly
    # into index.html at build time now (scripts/build_website.sh's own "Inlining" comment,
    # SPECIFICATION.md Part H.7), never staged as their own files.
    assert "/js/app.js.gz" in frozen_html_text


def _run_cli(repo_root: Path, args: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/build_firmware.py", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=check,
    )


def test_cli_missing_device_toml_fails_fast(repo_root: Path, tmp_path: Path) -> None:
    result = _run_cli(repo_root, ["no-such-device", "--output", str(tmp_path / "out.uf2")])
    assert result.returncode != 0
    assert "no-such-device" in result.stderr


def test_cli_missing_toolchain_dir_fails_before_attempting_a_build(repo_root: Path, tmp_path: Path) -> None:
    result = _run_cli(
        repo_root,
        ["wozi", "--output", str(tmp_path / "out.uf2"), "--toolchain-dir", str(tmp_path / "no-toolchain-here")],
    )
    assert result.returncode != 0
    assert "no-toolchain-here" in result.stderr or "toolchain" in result.stderr.lower()
    assert not (tmp_path / "out.uf2").exists()


@pytest.mark.parametrize("device", ["wozi", "dev", "arzi", "klkizi", "grkizi", "schlafzi"])
@pytest.mark.skipif(
    os.environ.get("RUN_SLOW_FIRMWARE_BUILD") != "1",
    reason="real ARM firmware compile, several minutes - opt in with RUN_SLOW_FIRMWARE_BUILD=1 "
    "(see .github/workflows/ci.yml's firmware-build-verify job, which sets it)",
)
def test_real_firmware_build_produces_a_valid_uf2(repo_root: Path, tmp_path: Path, device: str) -> None:
    # The actual end-to-end proof SPECIFICATION.md Part B.11 asked for: a real src/-based
    # firmware.uf2, built by the exact same script/manifest a device build would use, not just its
    # staging logic checked in isolation above. Needs the real toolchain already installed
    # (uv run toolchain/setup_toolchain.py setup) - scripts/test.sh and CI's unit-tests job both
    # already provision it before this suite runs. Parametrized over all 6 real devices - each has
    # its own distinct buildgen-generated boot entry that must actually compile and freeze cleanly
    # (CI runs these as a per-device matrix, .github/workflows/ci.yml's firmware-build-verify job -
    # not all 6 in one slow local run, though `-k` can select just one for fast local iteration).
    output = tmp_path / f"firmware-{device}.uf2"
    result = _run_cli(repo_root, [device, "--output", str(output)])
    assert result.returncode == 0, result.stdout + result.stderr

    assert output.is_file()
    data = output.read_bytes()
    assert data[:4] == b"UF2\n"
    assert len(data) > 0 and len(data) % 512 == 0  # UF2 files are a sequence of fixed 512-byte blocks
