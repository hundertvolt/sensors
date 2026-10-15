"""Tests scripts/build_firmware.py (SPECIFICATION.md Part B.11's real firmware.uf2 assembly
script) - its own logic (_MANIFEST_TEMPLATE, build_stage_dir()'s per-device boot-module selection,
CLI error paths) without the minutes-long ARM compile."""

# The one test that does run the real ARM build carries its own comment - see
# test_real_firmware_build_produces_a_valid_uf2.

import contextlib
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import pytest
import tomllib
from _devices import DEVICE_NAMES, device_toml, devices_with
from _script_loader import load_script_module

from buildgen.codegen import generate_boot_entry_source
from buildgen.frozen_modules import compute_frozen_modules
from buildgen.generate import generate_device
from buildgen.validate import device_max_connections
from buildgen.version import FIRMWARE_VERSION, WEBSITE_VERSION

if TYPE_CHECKING:
    from collections.abc import Iterator

# The faked generations below need only a device label; the CLI cases need a real device to name.
_FIXTURE_DEVICE = "fixture_device"
_A_DEVICE = DEVICE_NAMES[0]
_BUILD_DATE = "2026-09-12T10:00:00Z"

def _run_cli(repo_root: Path, args: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/build_firmware.py", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=check,
    )


@pytest.fixture(scope="session")
def build_firmware(repo_root: Path) -> ModuleType:
    # Imports scripts/build_firmware.py as a real module (it's a `uv run`-style standalone
    # script, not a package member) so build_stage_dir()/_MANIFEST_TEMPLATE can be checked
    # directly instead of only through subprocess/CLI behavior.
    return load_script_module(repo_root / "scripts" / "build_firmware.py", "build_firmware")


# Website builds run at most this many at a time: the stagings' one slow step, each a separate process.
_WEBSITE_BUILDS_AT_ONCE = 2


@pytest.fixture(scope="module")
def stagings(build_firmware: ModuleType, tmp_path_factory: pytest.TempPathFactory) -> "dict[str, Path]":
    # One staging per device, shared by the read-only checks below. The build date is passed in, as
    # main() does, so a reference generation embeds the identical timestamp (SPECIFICATION.md Part L.7).
    # The Python half stages in turn; the website commands it issues are collected and run after.
    website_builds: list[tuple[list[str], Path]] = []

    def collect(argv: "list[str]", *, cwd: Path, check: bool) -> None:
        assert check and Path(argv[0]).name == "build_website.sh", argv
        website_builds.append((argv, cwd))

    stages = {}
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(build_firmware.subprocess, "run", collect)
        for device in DEVICE_NAMES:
            stages[device] = tmp_path_factory.mktemp(f"stage_{device}")
            build_firmware.build_stage_dir(stages[device], device, build_date=_BUILD_DATE)
    assert len(website_builds) == len(DEVICE_NAMES), website_builds
    with ThreadPoolExecutor(max_workers=_WEBSITE_BUILDS_AT_ONCE) as pool:
        for done in pool.map(lambda job: subprocess.run(job[0], cwd=job[1], check=False, capture_output=True, text=True), website_builds):
            assert done.returncode == 0, f"{done.args} failed:\n{done.stdout}{done.stderr}"
    return stages


@pytest.fixture(params=DEVICE_NAMES)
def staged_device(request: pytest.FixtureRequest, stagings: "dict[str, Path]") -> "tuple[str, Path]":
    device = str(request.param)
    return device, stagings[device]


def test_build_stage_dir_rejects_a_device_with_no_matching_toml(build_firmware: ModuleType, tmp_path: Path) -> None:
    # Fail loud, before staging anything - build_stage_dir() converts buildgen's own BuildError
    # (no devices/no-such-device.toml to read) into a plain RuntimeError, matching this function's
    # contract of raising RuntimeError for every build-impossible condition.
    with pytest.raises(RuntimeError, match="no-such-device"):
        build_firmware.build_stage_dir(tmp_path, "no-such-device")


def test_build_stage_dir_rejects_a_frozen_module_resolving_to_neither_src_nor_ext(build_firmware: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A defensive check for a contract mismatch buildgen's guarantees should prevent, simulated
    # with a fake GeneratedDevice - a plain SimpleNamespace, build_stage_dir reading only four
    # attributes off it - whose frozen_modules names a module neither src/ nor ext/ has.
    from types import SimpleNamespace

    fake_generated = SimpleNamespace(
        model=SimpleNamespace(device=_FIXTURE_DEVICE),
        module_source="# fake module\n",
        boot_entry_source="# fake boot\n",
        frozen_modules=frozenset({"this_module_does_not_exist_anywhere"}),
    )
    monkeypatch.setattr(build_firmware, "generate_device", lambda *_args, **_kwargs: fake_generated)

    with pytest.raises(RuntimeError, match="this_module_does_not_exist_anywhere"):
        build_firmware.build_stage_dir(tmp_path, _FIXTURE_DEVICE)


def test_build_stage_dir_rejects_a_frozen_module_colliding_with_a_reserved_staging_name(build_firmware: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The other defensive check: a frozen module whose filename collides with a reserved name
    # must fail rather than overwrite the real entry or website content. No src/ file is called
    # "main.py" today, so REPO_ROOT is patched to a fake tree purely to reach the collision.
    from types import SimpleNamespace

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("# dummy colliding module\n")
    monkeypatch.setattr(build_firmware, "REPO_ROOT", tmp_path)

    fake_generated = SimpleNamespace(
        model=SimpleNamespace(device=_FIXTURE_DEVICE),
        module_source="# fake module\n",
        boot_entry_source="# fake boot\n",
        frozen_modules=frozenset({"main"}),
    )
    monkeypatch.setattr(build_firmware, "generate_device", lambda *_args, **_kwargs: fake_generated)

    stage_dir = tmp_path / "stage"
    stage_dir.mkdir()
    with pytest.raises(RuntimeError, match=r"main\.py"):
        build_firmware.build_stage_dir(stage_dir, _FIXTURE_DEVICE)


def test_manifest_template_includes_the_default_board_manifest_and_freezes_stage_dir(build_firmware: ModuleType, tmp_path: Path) -> None:
    # Each device's boot module is frozen as "main.py", so the default board manifest is reused
    # unchanged - unlike the old custom _boot.py, which had to skip that manifest to avoid a
    # colliding second freeze() and broke USB entirely (Part F.1).

    # str(), not the Path: the template interpolates {stage_dir!r} and the real call site passes
    # a str, so a Path here would render as PosixPath('...').
    stage_dir = str(tmp_path / "some-stage-dir")
    manifest = build_firmware._MANIFEST_TEMPLATE.format(board="RPI_PICO_W", stage_dir=stage_dir)
    assert 'include("$(PORT_DIR)/boards/RPI_PICO_W/manifest.py")' in manifest
    assert f"freeze('{stage_dir}')" in manifest


def test_build_stage_dir_stages_exactly_the_computed_frozen_modules(repo_root: Path, staged_device: "tuple[str, Path]") -> None:
    # No longer every src/*.py file: only this device's buildgen-computed dependency closure is
    # staged (Part L.2's dependency-driven selection), a genuinely smaller firmware than this
    # script produced before buildgen.
    device, stage_dir = staged_device
    generated = generate_device(repo_root / "devices" / f"{device}.toml", repo_root / "src", repo_root / "ext")
    expected_modules = compute_frozen_modules(generated.module_source, repo_root / "src", repo_root / "ext")
    assert expected_modules, "sanity: a real device should need at least one frozen module"

    staged = {p.name for p in stage_dir.iterdir()}
    assert {f"{m}.py" for m in expected_modules} <= staged

    for expected in ("microdot.py", "main.py", "frozen_html.py", f"sensortask_{device}.py"):
        assert expected in staged, expected

    # A module outside this device's closure must NOT be staged either, which is what proves
    # this is a real device-scoped subset rather than every src/*.py file passing the assertion
    # above by coincidence.

    # Not asserted non-empty: a device wiring every driver in src/ has an empty unrelated set, so
    # the check bites through the devices that leave a driver out, across the parametrization.
    all_src_modules = {p.stem for p in (repo_root / "src").glob("*.py")}
    unrelated_modules = all_src_modules - expected_modules
    assert not ({f"{m}.py" for m in unrelated_modules} & staged)

    assert (repo_root / "ext" / "microdot.py").read_text() == (stage_dir / "microdot.py").read_text()


def test_build_stage_dir_writes_the_generated_entry_module_and_boot_entry(build_firmware: ModuleType, repo_root: Path, staged_device: "tuple[str, Path]") -> None:
    # The generated device entry module and its boot entry: freshly generated text, never copied
    # from a retired boot_entry file, staged as "main.py" for the load-bearing reason
    # build_firmware.py's docstring gives.

    # Content-matched against buildgen's generator rather than checked for filename presence, so
    # each device really stages its own boot module instead of falling back to another device's.
    # The reference generation takes the staging's pinned build date.
    device, stage_dir = staged_device
    generated = generate_device(repo_root / "devices" / f"{device}.toml", repo_root / "src", repo_root / "ext", build_date=_BUILD_DATE)
    # The generated module carries src/'s own TYPE_CHECKING form, so it is staged stripped like every src/ module.
    staged = (stage_dir / f"sensortask_{device}.py").read_text()
    assert "TYPE_CHECKING" in generated.module_source
    assert "TYPE_CHECKING" not in staged
    assert staged == build_firmware.strip_type_checking_blocks(generated.module_source)
    assert (stage_dir / "main.py").read_text() == generated.boot_entry_source == generate_boot_entry_source(device)
    assert len(DEVICE_NAMES) >= 2, "the check below needs a second real device"
    other_device = next(d for d in DEVICE_NAMES if d != device)
    assert (stage_dir / "main.py").read_text() != generate_boot_entry_source(other_device)


def test_build_stage_dir_strips_type_checking_blocks_from_staged_src_files(repo_root: Path, staged_device: "tuple[str, Path]") -> None:
    # asy_config_manager.py is a known if TYPE_CHECKING: user, so its staged copy must have the
    # guard stripped while the real src/ file keeps it - CLAUDE.md's hard rule against editing
    # src/ for a build-only concern.
    _device, stage_dir = staged_device
    staged_text = (stage_dir / "asy_config_manager.py").read_text()
    assert "TYPE_CHECKING" not in staged_text
    assert "TYPE_CHECKING" in (repo_root / "src" / "asy_config_manager.py").read_text()


def test_build_stage_dir_frozen_html_contains_the_real_website(staged_device: "tuple[str, Path]") -> None:
    _device, stage_dir = staged_device
    frozen_html_text = (stage_dir / "frozen_html.py").read_text()
    assert "/index.html.gz" in frozen_html_text
    # /js/app.js.gz marks the real bundled website. No separate definitions or style check: both are
    # inlined into index.html at build time (Part H.7), never staged as their own files.
    assert "/js/app.js.gz" in frozen_html_text


def test_cli_missing_device_toml_fails_fast(repo_root: Path, tmp_path: Path) -> None:
    result = _run_cli(repo_root, ["no-such-device", "--output", str(tmp_path / "out.uf2")])
    assert result.returncode != 0
    assert "no-such-device" in result.stderr


def test_cli_missing_toolchain_dir_fails_before_attempting_a_build(repo_root: Path, tmp_path: Path) -> None:
    result = _run_cli(
        repo_root,
        [_A_DEVICE, "--output", str(tmp_path / "out.uf2"), "--toolchain-dir", str(tmp_path / "no-toolchain-here")],
    )
    assert result.returncode != 0
    assert "no-toolchain-here" in result.stderr or "toolchain" in result.stderr.lower()
    assert not (tmp_path / "out.uf2").exists()


def _fake_toolchain(root: Path) -> Path:
    # A toolchain directory that passes the checkout check: ports/rp2 present, nothing built.
    (root / "micropython" / "ports" / "rp2").mkdir(parents=True)
    return root


def test_cli_a_toolchain_without_its_record_is_refused_before_building(repo_root: Path, tmp_path: Path) -> None:
    # setup deletes the record first and writes it last, so a directory without one is an interrupted
    # setup or a toolchain built before the record existed: neither is built from.
    toolchain = _fake_toolchain(tmp_path / "toolchain")
    result = _run_cli(repo_root, [_A_DEVICE, "--output", str(tmp_path / "out.uf2"), "--toolchain-dir", str(toolchain)])
    assert result.returncode == 1, result.stdout + result.stderr
    assert f"the toolchain at {toolchain} is incomplete or predates the build record - run `uv run toolchain/setup_toolchain.py setup` first" in result.stderr
    assert "Traceback" not in result.stderr
    assert not (tmp_path / "out.uf2").exists()


def test_cli_a_toolchain_in_use_fails_at_once_naming_the_holder(build_firmware: ModuleType, repo_root: Path, tmp_path: Path) -> None:
    # A second build (or a setup) on one toolchain directory fails fast with the holder's pid rather than
    # wiping mpy-cross under the first; this process holds the real lock while the CLI runs.
    toolchain = _fake_toolchain(tmp_path / "toolchain")
    with build_firmware.st.toolchain_lock(toolchain):
        result = _run_cli(repo_root, [_A_DEVICE, "--output", str(tmp_path / "out.uf2"), "--toolchain-dir", str(toolchain)])
    assert result.returncode == 1, result.stdout + result.stderr
    assert f"another setup or firmware build (pid {os.getpid()}) is using {toolchain}" in result.stderr
    assert not (tmp_path / "out.uf2").exists()


# A record may carry no built ref (a `test` run with none to carry over); the line then says so, never "None".
@pytest.mark.parametrize(
    ("built_ref", "printed"),
    [("v1.29.0", "MicroPython v1.29.0 (0123abcd)"), (None, "MicroPython v1.29.0 as pinned (built by `test`, ref not recorded) (0123abcd)")],
)
def test_a_relative_toolchain_dir_reaches_the_build_resolved_and_the_lock_spans_it(build_firmware: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], built_ref: "str | None", printed: str) -> None:
    # One absolute path for the lock, the record and every path the build writes into generated files;
    # the lock is held from before the mpy-cross wipe until the image is copied out.
    monkeypatch.chdir(tmp_path)
    toolchain = _fake_toolchain(tmp_path / "rel" / "toolchain").resolve()
    stale_mpy_cross = toolchain / "micropython" / "mpy-cross" / "build" / "stale.o"
    stale_mpy_cross.parent.mkdir(parents=True)
    stale_mpy_cross.write_text("")
    output = tmp_path / "out.uf2"
    events: list[str] = []
    seen: dict[str, Path] = {}

    @contextlib.contextmanager
    def fake_lock(toolchain_dir: Path) -> "Iterator[None]":
        seen["lock"] = toolchain_dir
        events.append(f"lock (mpy-cross build present: {stale_mpy_cross.exists()})")
        yield
        events.append(f"unlock (image copied: {output.exists()}, record written: {output.with_suffix('.json').exists()})")

    def fake_build_firmware(micropython_dir: Path, _board: str, _jobs: int, *_args: object, toolchain_dir: Path, **_kwargs: object) -> Path:
        seen["build"] = toolchain_dir
        events.append("build_firmware")
        image = micropython_dir / "firmware.uf2"
        image.write_bytes(b"UF2\n")
        return image

    monkeypatch.setattr(build_firmware.st, "toolchain_lock", fake_lock)
    monkeypatch.setattr(build_firmware.st, "read_toolchain_record", lambda _d: {"pinned_ref": "v1.29.0", "built_ref": built_ref, "micropython_commit": "0123abcd"})
    monkeypatch.setattr(build_firmware.st, "build_mpy_cross", lambda *_a: events.append(f"build_mpy_cross (wiped: {not stale_mpy_cross.exists()})"))
    monkeypatch.setattr(build_firmware.st, "build_firmware", fake_build_firmware)
    monkeypatch.setattr(build_firmware, "build_stage_dir", lambda *_a, **_k: events.append("stage"))
    monkeypatch.setattr(build_firmware, "source_state", lambda _root: _SOURCE_STATE)
    _fake_readers(build_firmware, monkeypatch)
    monkeypatch.setattr(sys, "argv", ["build_firmware.py", _A_DEVICE, "--output", str(output), "--toolchain-dir", "rel/toolchain"])
    assert build_firmware.main() == 0
    assert seen == {"lock": toolchain, "build": toolchain}, seen
    assert events == ["lock (mpy-cross build present: True)", "stage", "build_mpy_cross (wiped: True)", "build_firmware", "unlock (image copied: True, record written: True)"], events
    toolchain_line = next(line for line in capsys.readouterr().out.splitlines() if line.startswith("== Toolchain: "))
    assert printed in toolchain_line, toolchain_line
    assert "None" not in toolchain_line, toolchain_line


# ---------------------------------------------------------------------------
# The image record beside every .uf2 and --device-toml: a run can tell which build a board carries.
# ---------------------------------------------------------------------------

_LWIP_READ = {"TCP_MSS": 1460, "MEMP_NUM_TCP_PCB": 9}
_SOURCE_STATE = ("0123456789abcdef0123456789abcdef01234567", True)  # source_state() itself: its own case below


def _fake_readers(build_firmware: ModuleType, monkeypatch: pytest.MonkeyPatch, *, modlwip_ok: bool = True) -> "list[tuple[str, Path]]":
    # The two post-build readers, faked: each logs the build dir it was given.
    seen: list[tuple[str, Path]] = []

    def read_lwip(build_dir: Path, macros: "dict[str, int]") -> "dict[str, int]":
        assert macros == build_firmware.st.load_lwip_macros(), "the readback asks for the pinned options"
        seen.append(("lwip", build_dir))
        return dict(_LWIP_READ)

    def verify_modlwip(build_dir: Path, _micropython_dir: Path, copy_path: Path) -> None:
        seen.append(("modlwip", build_dir))
        assert copy_path.parts[-2:] == (build_firmware.micropython_overrides.MODLWIP_OVERRIDE_DIR_NAME, build_firmware.micropython_overrides.MODLWIP_COPY_NAME), copy_path
        if not modlwip_ok:
            raise build_firmware.micropython_overrides.OverrideError("modlwip_eagain: the control image")

    monkeypatch.setattr(build_firmware.micropython_overrides, "read_lwip_macros_from_build", read_lwip)
    monkeypatch.setattr(build_firmware.micropython_overrides, "verify_modlwip_eagain_in_build", verify_modlwip)
    return seen


def _uart_crc(toml_path: Path) -> "dict[str, str]":
    # Each UART bus's CRC mode as the device TOML declares it (absent: "none").
    instances = tomllib.loads(toml_path.read_text(encoding="utf-8")).get("instance", [])
    return {i["bus"]: i.get("crc", "none") for i in instances if i.get("driver") == "uart_link"}


@dataclass
class _Built:
    # What main() did under _build_with_fakes(): its exit, what staging got, what the readers read.
    exit: int
    port_build: Path
    readers: "list[tuple[str, Path]]"
    staged: "dict[str, object]" = field(default_factory=dict)


def _build_with_fakes(build_firmware: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *argv: str, modlwip_ok: bool = True) -> _Built:
    # main() with the toolchain, staging and ARM build faked. The image lands in a fake port build
    # dir, never beside the output, so the readers' build dir can be told apart from the copy.
    toolchain = _fake_toolchain(tmp_path / "toolchain")
    port_build = toolchain / "micropython" / "ports" / "rp2" / "build-FAKE"
    built = _Built(exit=-1, port_build=port_build, readers=_fake_readers(build_firmware, monkeypatch, modlwip_ok=modlwip_ok))

    def fake_stage(_stage_dir: Path, device: str, *, device_toml: Path, build_date: str) -> None:
        built.staged.update(device=device, device_toml=device_toml, build_date=build_date)

    def fake_build(*_args: object, **_kwargs: object) -> Path:
        port_build.mkdir(parents=True, exist_ok=True)
        (port_build / "firmware.uf2").write_bytes(b"UF2\nnew image")
        return port_build / "firmware.uf2"

    monkeypatch.setattr(build_firmware.st, "read_toolchain_record", lambda _d: {"pinned_ref": "v1.29.0", "built_ref": "v1.29.0", "micropython_commit": "0123abcd"})
    monkeypatch.setattr(build_firmware, "source_state", lambda _root: _SOURCE_STATE)
    monkeypatch.setattr(build_firmware.st, "build_mpy_cross", lambda *_a: None)
    monkeypatch.setattr(build_firmware.st, "build_firmware", fake_build)
    monkeypatch.setattr(build_firmware, "build_stage_dir", fake_stage)
    monkeypatch.setattr(sys, "argv", ["build_firmware.py", *argv, "--toolchain-dir", str(toolchain)])
    built.exit = build_firmware.main()
    return built


@pytest.mark.parametrize("modlwip_ok", [True, False], ids=["override-compiled", "control-image"])
def test_main_writes_the_image_record_beside_the_image(build_firmware: ModuleType, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, modlwip_ok: bool) -> None:  # noqa: FBT001
    output = tmp_path / "out" / f"firmware-{_A_DEVICE}.uf2"
    built = _build_with_fakes(build_firmware, tmp_path, monkeypatch, _A_DEVICE, "--output", str(output), modlwip_ok=modlwip_ok)
    assert built.exit == 0
    record = json.loads(output.with_suffix(".json").read_text())
    toml = device_toml(_A_DEVICE)
    commit, dirty = _SOURCE_STATE
    assert record == {
        "BuildDate": built.staged["build_date"],
        "commit": commit,
        "device": _A_DEVICE,
        "deviceToml": f"devices/{_A_DEVICE}.toml",
        "dirty": dirty,
        "firmwareVersion": FIRMWARE_VERSION,
        "lwip": _LWIP_READ,
        "maxConnections": device_max_connections(toml, repo_root / "src"),
        "overrides": ["modlwip_eagain"] if modlwip_ok else [],
        "uartCrc": _uart_crc(toml),
        "websiteVersion": WEBSITE_VERSION,
    }
    assert list(record) == sorted(record), "the record's keys are written sorted"
    assert built.staged["device_toml"] == toml, "the default --device-toml is the device's own TOML"
    assert sorted(what for what, _dir in built.readers) == ["lwip", "modlwip"]
    assert {build_dir for _what, build_dir in built.readers} == {built.port_build}, "both readers read the port's build dir, never the copied output"


def test_the_image_and_its_record_are_never_paired_wrongly(build_firmware: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The old record goes first, the image moves in whole, the record comes last: a kill anywhere
    # leaves no record or a record beside the image it describes, never a truncated image.
    output = tmp_path / "firmware.uf2"
    output.write_bytes(b"UF2\nold image")
    output.with_suffix(".json").write_text('{"stale": true}')
    replaced: list[tuple[str, str, bool]] = []
    real_replace = os.replace

    def recording_replace(src: "str | os.PathLike[str]", dst: "str | os.PathLike[str]") -> None:
        replaced.append((Path(src).name, Path(dst).name, output.with_suffix(".json").exists()))
        real_replace(src, dst)

    monkeypatch.setattr(build_firmware.os, "replace", recording_replace)
    _build_with_fakes(build_firmware, tmp_path, monkeypatch, _A_DEVICE, "--output", str(output))
    assert [(src.endswith(".tmp"), dst, had) for src, dst, had in replaced] == [(True, "firmware.uf2", False), (True, "firmware.json", False)], replaced
    assert output.read_bytes() == b"UF2\nnew image"
    assert sorted(p.name for p in tmp_path.iterdir() if p.is_file()) == ["firmware.json", "firmware.uf2"], "no .tmp file is left"


def test_a_failed_image_move_leaves_no_record_and_the_old_image(build_firmware: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "firmware.uf2"
    output.write_bytes(b"UF2\nold image")
    output.with_suffix(".json").write_text('{"stale": true}')

    def failing_replace(*_args: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(build_firmware.os, "replace", failing_replace)
    with pytest.raises(OSError, match="disk full"):
        _build_with_fakes(build_firmware, tmp_path, monkeypatch, _A_DEVICE, "--output", str(output))
    assert output.read_bytes() == b"UF2\nold image"
    assert not output.with_suffix(".json").exists(), "a record must never stand beside an image it does not describe"


def test_source_state_names_the_commit_and_a_dirty_tree(build_firmware: ModuleType, tmp_path: Path) -> None:
    git = shutil.which("git") or "git"
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    (tmp_path / "f.txt").write_text("a\n")
    for argv in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "c"]):
        subprocess.run([git, *argv], cwd=tmp_path, env=env, check=True)
    head = subprocess.run([git, "rev-parse", "HEAD"], cwd=tmp_path, env=env, capture_output=True, text=True, check=True).stdout.strip()
    assert build_firmware.source_state(tmp_path) == (head, False)
    (tmp_path / "f.txt").write_text("b\n")
    assert build_firmware.source_state(tmp_path) == (head, True)
    assert build_firmware.source_state(tmp_path / "not-a-repo") == (None, None), "an unknown state is written as unknown, never as clean"


def _toml_with_hotspot_password(tmp_path: Path, device: str, password: str) -> Path:
    # A copy of a real device's TOML under its own stem with another hotspot password - a value that
    # reaches the generated module (the hostname cannot vary: buildgen pins it to the name).
    text = device_toml(device).read_text(encoding="utf-8")
    current = tomllib.loads(text)["device"]["hotspot_password"]
    copy = tmp_path / f"{device}.toml"
    copy.write_text(text.replace(f'hotspot_password = "{current}"', f'hotspot_password = "{password}"', 1), encoding="utf-8")
    return copy


def test_build_stage_dir_builds_from_the_given_device_toml(build_firmware: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml = _toml_with_hotspot_password(tmp_path, _A_DEVICE, "fixture-pw")
    stage = tmp_path / "stage"
    stage.mkdir()
    real_run = subprocess.run
    # The website build is not under test here, and it is the one slow step of a staging. Without a
    # build_date the generator stamps its own "now" (the default path, kept for other callers).
    monkeypatch.setattr(build_firmware.subprocess, "run", lambda argv, **kw: None if "build_website.sh" in str(argv[0]) else real_run(argv, **kw))
    monkeypatch.setattr("buildgen.generate.current_build_date", lambda: "2026-01-02T03:04:05Z")
    build_firmware.build_stage_dir(stage, _A_DEVICE, device_toml=toml)
    staged = (stage / f"sensortask_{_A_DEVICE}.py").read_text()
    assert "'fixture-pw'" in staged, "the staged module comes from the given TOML"
    assert "_BUILD_DATE = const('2026-01-02T03:04:05Z')" in staged


def _main_refusal(build_firmware: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], *argv: str) -> str:
    # main() on argv with staging and the toolchain record forbidden: the refusal must come first.
    def never(*_a: object, **_k: object) -> None:
        raise AssertionError("refused too late: staging or the toolchain was reached")

    monkeypatch.setattr(build_firmware, "build_stage_dir", never)
    monkeypatch.setattr(build_firmware.st, "read_toolchain_record", never)
    monkeypatch.setattr(sys, "argv", ["build_firmware.py", *argv])
    assert build_firmware.main() == 1
    return capsys.readouterr().err


def test_a_missing_device_toml_path_fails_before_staging(build_firmware: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / f"{_A_DEVICE}.toml"
    err = _main_refusal(build_firmware, monkeypatch, capsys, _A_DEVICE, "--device-toml", str(missing), "--output", str(tmp_path / "out.uf2"))
    assert str(missing) in err
    assert not (tmp_path / "out.uf2").exists()


def test_a_device_toml_of_another_device_is_refused(build_firmware: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    # buildgen names the image's modules after the TOML's file name, so a mismatch would ship an
    # image whose name and record claim one device and whose code is another.
    other = next(d for d in DEVICE_NAMES if d != _A_DEVICE)
    err = _main_refusal(build_firmware, monkeypatch, capsys, _A_DEVICE, "--device-toml", str(device_toml(other)), "--output", str(tmp_path / "out.uf2"))
    assert f"builds device {other!r}, not {_A_DEVICE!r}" in err


def test_a_device_toml_changing_the_website_is_refused(build_firmware: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    # The website is built from the repo's own TOML, so a copy that changes what it shows would put
    # a page on the board that does not match its image.
    device = next(d for d in DEVICE_NAMES if "notification" in {i.get("driver") for i in tomllib.loads(device_toml(d).read_text(encoding="utf-8"))["instance"]})
    text = device_toml(device).read_text(encoding="utf-8")
    copy = tmp_path / f"{device}.toml"
    copy.write_text(text[: text.index('[[instance]]\ndriver = "notification"')], encoding="utf-8")  # from the notification instance on: its warning thresholds leave the website
    err = _main_refusal(build_firmware, monkeypatch, capsys, device, "--device-toml", str(copy), "--output", str(tmp_path / "out.uf2"))
    assert "changes what the website shows" in err


def test_a_crc16_copy_of_the_link_device_builds_and_its_record_says_so(build_firmware: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The second CRC mode's bench image: the same device, its links switched to crc16 in a copy.
    linked = devices_with("uart_link")
    assert linked, "no device declares a uart_link - the CRC16 image has nothing to build"
    text = device_toml(linked[0]).read_text(encoding="utf-8")
    copy = tmp_path / "toml" / f"{linked[0]}.toml"
    copy.parent.mkdir()
    copy.write_text(text.replace('driver = "uart_link"\n', 'driver = "uart_link"\ncrc = "crc16"\n'), encoding="utf-8")
    built = _build_with_fakes(build_firmware, tmp_path, monkeypatch, linked[0], "--device-toml", str(copy), "--output", str(tmp_path / "crc16.uf2"))
    assert built.exit == 0
    record = json.loads((tmp_path / "crc16.json").read_text())
    assert record["uartCrc"] and set(record["uartCrc"].values()) == {"crc16"}, record["uartCrc"]
    assert record["deviceToml"] == str(copy.resolve())
    assert built.staged["device_toml"] == copy.resolve()


@pytest.mark.parametrize("device", DEVICE_NAMES)
@pytest.mark.skipif(
    os.environ.get("RUN_SLOW_FIRMWARE_BUILD") != "1",
    reason="real ARM firmware compile, several minutes - opt in with RUN_SLOW_FIRMWARE_BUILD=1 "
    "(see .github/workflows/ci.yml's firmware-build-verify job, which sets it)",
)
def test_real_firmware_build_produces_a_valid_uf2(repo_root: Path, tmp_path: Path, device: str) -> None:
    # The end-to-end proof Part B.11 asked for: a real firmware.uf2 from the same script and
    # manifest a device build uses, not just the staging logic above. Needs the toolchain already
    # installed, which test.sh and the unit-tests job both provision first.

    # Parametrized over every real device, each with its own boot entry that must compile and
    # freeze cleanly. CI runs them as a per-device matrix; locally `-k` selects one.
    output = tmp_path / f"firmware-{device}.uf2"
    result = _run_cli(repo_root, [device, "--output", str(output)])
    assert result.returncode == 0, result.stdout + result.stderr

    assert output.is_file()
    data = output.read_bytes()
    assert data[:4] == b"UF2\n"
    assert len(data) > 0 and len(data) % 512 == 0  # UF2 files are a sequence of fixed 512-byte blocks
