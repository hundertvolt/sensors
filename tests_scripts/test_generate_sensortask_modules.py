"""Tests scripts/_generate_sensortask_modules.py (SPECIFICATION.md Part E.3's build/generated_src/
pre-generation step): every real device's written outputs equal its in-memory generation, every file
reaches its name by rename, and a BuildError or a failed write is one reported line, nothing half-written."""

import builtins
import errno
import io
import json
import os
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from _devices import DEVICE_NAMES
from _script_loader import load_script_module

from buildgen.api_reference import api_reference_json, generate_api_reference
from buildgen.definitions import definitions_for_toml
from buildgen.errors import BuildError
from buildgen.generate import generate_device
from buildgen.twin_wiring import compute_twin_wiring


@pytest.fixture
def generate_sensortask_modules(repo_root: Path) -> ModuleType:
    return load_script_module(repo_root / "scripts" / "_generate_sensortask_modules.py", "_generate_sensortask_modules")


def test_main_generates_every_real_device_matching_generate_device_directly(generate_sensortask_modules: ModuleType, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(generate_sensortask_modules, "REPO_ROOT", tmp_path)
    (tmp_path / "devices").symlink_to(repo_root / "devices")
    (tmp_path / "src").symlink_to(repo_root / "src")
    (tmp_path / "ext").symlink_to(repo_root / "ext")
    # Pins the one build_date main() computes for its whole batch, so this test's own separate
    # reference generate_device() calls below embed the exact same timestamp instead of racing a
    # real wall clock against main()'s already-completed run (SPECIFICATION.md Part L.7).
    monkeypatch.setattr(generate_sensortask_modules, "current_build_date", lambda: "2026-09-12T10:00:00Z")

    exit_code = generate_sensortask_modules.main()
    assert exit_code == 0

    out_dir = tmp_path / "build" / "generated_src"
    for device in DEVICE_NAMES:
        expected = generate_device(repo_root / "devices" / f"{device}.toml", repo_root / "src", repo_root / "ext", build_date="2026-09-12T10:00:00Z")
        assert (out_dir / f"sensortask_{device}.py").read_text() == expected.module_source
        assert (out_dir / f"sensortask_{device}_main.py").read_text() == expected.boot_entry_source
        assert (out_dir / f"sensortask_{device}_main_noautostart.py").read_text() == expected.boot_entry_noautostart_source
        assert json.loads((out_dir / f"sensortask_{device}_expected.json").read_text()) == expected.expected_facts
        # compute_twin_wiring() is the plan's one producer, "instances" included: the file is its output unchanged.
        assert json.loads((out_dir / f"sensortask_{device}_wiring_plan.json").read_text()) == compute_twin_wiring(expected.model)
        written = json.loads((out_dir / "definitions" / f"{device}.json").read_text())
        assert written == definitions_for_toml(repo_root / "devices" / f"{device}.toml", repo_root / "src")
        assert (out_dir / "api" / f"{device}.json").read_text() == api_reference_json(generate_api_reference(expected.model, repo_root / "src"))
    assert json.loads((out_dir / "definitions" / "index.json").read_text()) == {"devices": sorted(DEVICE_NAMES)}


def test_main_reports_a_build_error_and_exits_nonzero_without_crashing(generate_sensortask_modules: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    # A malformed devices/*.toml is a reachable failure, so the loop's except BuildError must
    # report it and return 1 rather than let a traceback escape or leave a half-generated tree.
    # generate_device is monkeypatched: only this script's reporting contract is under test.
    (tmp_path / "devices").mkdir()
    (tmp_path / "devices" / "broken.toml").write_text("# not a real device\n")
    monkeypatch.setattr(generate_sensortask_modules, "REPO_ROOT", tmp_path)

    def fake_generate_device(*_args: object, **_kwargs: object) -> SimpleNamespace:
        raise BuildError("broken", "simulated failure for broken.toml", rule="test.simulated-failure", fix="repair the fixture")

    monkeypatch.setattr(generate_sensortask_modules, "generate_device", fake_generate_device)

    exit_code = generate_sensortask_modules.main()
    assert exit_code == 1
    err = capsys.readouterr().err
    assert "simulated failure for broken.toml - fix: repair the fixture" in err
    assert "Traceback" not in err

    # Never left holding a half-written module, wiring plan, definitions or API reference for the device that failed.
    out_dir = tmp_path / "build" / "generated_src"
    assert not [*out_dir.glob("sensortask_broken*"), *out_dir.glob("definitions/broken*"), *out_dir.glob("api/broken*")]


@pytest.mark.parametrize("stage", ["generate_definitions", "generate_api_reference", "compute_twin_wiring"])
def test_a_later_stage_build_error_is_reported_and_leaves_none_of_that_device(generate_sensortask_modules: ModuleType, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], stage: str) -> None:
    # A device's outputs are all computed before any is written, so a stage after the module's own
    # generation failing is the same one-line report and exit 1, with no file of that device behind.
    monkeypatch.setattr(generate_sensortask_modules, "REPO_ROOT", tmp_path)
    (tmp_path / "devices").mkdir()
    (tmp_path / "devices" / f"{DEVICE_NAMES[0]}.toml").symlink_to(repo_root / "devices" / f"{DEVICE_NAMES[0]}.toml")
    (tmp_path / "src").symlink_to(repo_root / "src")
    (tmp_path / "ext").symlink_to(repo_root / "ext")

    def failing_stage(*_args: object, **_kwargs: object) -> SimpleNamespace:
        raise BuildError(DEVICE_NAMES[0], f"simulated {stage} failure", rule="test.simulated-failure", fix="repair the fixture")

    monkeypatch.setattr(generate_sensortask_modules, stage, failing_stage)

    assert generate_sensortask_modules.main() == 1
    assert f"simulated {stage} failure" in capsys.readouterr().err
    out_dir = tmp_path / "build" / "generated_src"
    assert not [p for p in out_dir.rglob("*") if p.is_file()]


def _one_device_tree(repo_root: Path, tmp_path: Path) -> Path:
    # A stand-in repo root holding one real device, its src/ and ext/; returns the output directory.
    (tmp_path / "devices").mkdir()
    (tmp_path / "devices" / f"{DEVICE_NAMES[0]}.toml").symlink_to(repo_root / "devices" / f"{DEVICE_NAMES[0]}.toml")
    (tmp_path / "src").symlink_to(repo_root / "src")
    (tmp_path / "ext").symlink_to(repo_root / "ext")
    return tmp_path / "build" / "generated_src"


def test_no_output_is_ever_opened_for_writing_under_its_final_name(generate_sensortask_modules: ModuleType, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A typecheck or test run reading build/generated_src/ while it is regenerated must meet the old file
    # or the new one, never a truncated one: every write goes to <name>.tmp and reaches <name> by os.replace.
    monkeypatch.setattr(generate_sensortask_modules, "REPO_ROOT", tmp_path)
    out_dir = _one_device_tree(repo_root, tmp_path)
    opened: list[Path] = []
    renamed: list[tuple[Path, Path]] = []
    real_open, real_replace = io.open, os.replace

    def recording_open(file: object, mode: str = "r", *args: object, **kwargs: object) -> object:
        if isinstance(file, (str, Path)) and any(flag in mode for flag in "wax+") and Path(file).is_relative_to(out_dir):
            opened.append(Path(file))
        return real_open(file, mode, *args, **kwargs)  # type: ignore[call-overload]

    def recording_replace(src: "str | Path", dst: "str | Path") -> None:
        renamed.append((Path(src), Path(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(io, "open", recording_open)
    monkeypatch.setattr(builtins, "open", recording_open)
    monkeypatch.setattr(os, "replace", recording_replace)
    assert generate_sensortask_modules.main() == 0

    finals = sorted(p for p in out_dir.rglob("*") if p.is_file())
    assert finals, "the run wrote nothing - the check below would hold vacuously"
    assert not [p for p in finals if p.name.endswith(".tmp")], "a .tmp file was left behind"
    assert sorted(opened) == sorted(p.with_name(f"{p.name}.tmp") for p in finals), f"a file was opened under its final name: {sorted(set(opened) - {p.with_name(f'{p.name}.tmp') for p in finals})}"
    assert sorted(renamed) == sorted((p.with_name(f"{p.name}.tmp"), p) for p in finals), "every output must reach its name by one rename of its own .tmp"


def test_a_failed_write_is_one_reported_line_and_leaves_no_temporary_file(generate_sensortask_modules: ModuleType, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    # A full disk on the device's third file, raised by the write itself and so naming no file: exit 1
    # with the file named anyway, no traceback, the .tmp files already written removed, no output in place.
    monkeypatch.setattr(generate_sensortask_modules, "REPO_ROOT", tmp_path)
    out_dir = _one_device_tree(repo_root, tmp_path)
    real_write_text = Path.write_text
    writes: list[Path] = []

    def filling_write_text(self: Path, data: str, *args: object, **kwargs: object) -> int:
        writes.append(self)
        if len(writes) == 3:
            raise OSError(errno.ENOSPC, "No space left on device")
        return real_write_text(self, data, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "write_text", filling_write_text)
    assert generate_sensortask_modules.main() == 1
    err = capsys.readouterr().err
    assert f"error: cannot write {writes[2]}: No space left on device" in err
    assert "Traceback" not in err
    assert not [p for p in out_dir.rglob("*") if p.is_file()], "a failed write left files behind"
