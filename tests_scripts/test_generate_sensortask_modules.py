"""Tests scripts/_generate_sensortask_modules.py (SPECIFICATION.md Part E.3's build/generated_src/
pre-generation step): every real device's written outputs equal its in-memory generation, every file
reaches its name by rename, both freshness stamps land last, and a failure is one line, nothing half-written."""

import builtins
import errno
import hashlib
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


def _one_device_tree(repo_root: Path, tmp_path: Path) -> Path:
    # A stand-in repo root holding one real device, its src/ and ext/; returns the output directory.
    (tmp_path / "devices").mkdir()
    (tmp_path / "devices" / f"{DEVICE_NAMES[0]}.toml").symlink_to(repo_root / "devices" / f"{DEVICE_NAMES[0]}.toml")
    (tmp_path / "src").symlink_to(repo_root / "src")
    (tmp_path / "ext").symlink_to(repo_root / "ext")
    return tmp_path / "build" / "generated_src"


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


def _single_device_run(generate_sensortask_modules: ModuleType, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *argv: str) -> "tuple[int, Path, Path]":
    # One TOML outside devices/ generated into its own directory, the stand-in repo's build/ left alone; (exit, out, root).
    root = tmp_path / "repo"
    root.mkdir()
    _one_device_tree(repo_root, root)
    toml = tmp_path / "fixture_device.toml"
    toml.write_text((repo_root / "devices" / f"{DEVICE_NAMES[0]}.toml").read_text())
    monkeypatch.setattr(generate_sensortask_modules, "REPO_ROOT", root)
    monkeypatch.setattr(generate_sensortask_modules, "current_build_date", lambda: "2026-09-12T10:00:00Z")
    out = tmp_path / "out"
    return generate_sensortask_modules.main(["--device-toml", str(toml), "--out-dir", str(out), *argv]), out, root


def test_the_single_device_mode_writes_that_toml_s_outputs_into_its_directory_only(generate_sensortask_modules: ModuleType, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    code, out, root = _single_device_run(generate_sensortask_modules, repo_root, tmp_path, monkeypatch)
    assert code == 0
    expected = generate_device(tmp_path / "fixture_device.toml", repo_root / "src", repo_root / "ext", build_date="2026-09-12T10:00:00Z")
    files = {p.relative_to(out).as_posix(): p.read_text() for p in out.rglob("*") if p.is_file()}
    assert sorted(files) == sorted([
        "sensortask_fixture_device.py", "sensortask_fixture_device_main.py", "sensortask_fixture_device_main_noautostart.py",
        "sensortask_fixture_device_expected.json", "sensortask_fixture_device_wiring_plan.json",
        "definitions/fixture_device.json", "definitions/index.json", "api/fixture_device.json",
    ])
    assert files["sensortask_fixture_device.py"] == expected.module_source
    assert json.loads(files["sensortask_fixture_device_wiring_plan.json"]) == compute_twin_wiring(expected.model)
    assert json.loads(files["definitions/index.json"]) == {"devices": ["fixture_device"]}
    assert not (root / "build").exists(), "the single-device mode wrote into the repo's tree"


def test_the_single_device_mode_writes_nothing_on_a_build_error(generate_sensortask_modules: ModuleType, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def failing(*_args: object, **_kwargs: object) -> None:
        raise BuildError("fixture_device", "planted", rule="toml.syntax", fix="none")

    monkeypatch.setattr(generate_sensortask_modules, "compute_twin_wiring", failing)
    code, out, _root = _single_device_run(generate_sensortask_modules, repo_root, tmp_path, monkeypatch)
    assert code == 1
    assert "error: [fixture_device] planted" in capsys.readouterr().err
    assert not out.exists() or not any(p.is_file() for p in out.rglob("*"))


@pytest.mark.parametrize("argv", [["--device-toml", "x.toml"], ["--out-dir", "out"], ["--device"]])
def test_an_incomplete_single_device_request_is_a_usage_error(generate_sensortask_modules: ModuleType, argv: "list[str]") -> None:
    with pytest.raises(SystemExit) as caught:
        generate_sensortask_modules.main(argv)
    assert caught.value.code == 2


@pytest.fixture
def generate_sensortask_modules(repo_root: Path) -> ModuleType:
    return load_script_module(repo_root / "scripts" / "_generate_sensortask_modules.py", "_generate_sensortask_modules")


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


def test_a_removed_devices_outputs_leave_the_tree_and_nothing_outside_it_is_touched(generate_sensortask_modules: ModuleType, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Two devices generated, one TOML removed, generated again: no file of the removed device stays behind for a
    # consumer to read as a device, the remaining one's outputs all do, and only build/generated_src/ is swept.
    monkeypatch.setattr(generate_sensortask_modules, "REPO_ROOT", tmp_path)
    out_dir = _one_device_tree(repo_root, tmp_path)
    kept, removed = DEVICE_NAMES[0], DEVICE_NAMES[1]
    (tmp_path / "devices" / f"{removed}.toml").symlink_to(repo_root / "devices" / f"{removed}.toml")
    assert generate_sensortask_modules.main() == 0
    assert [p for p in out_dir.rglob(f"*{removed}*") if p.is_file()], "the removed device was never generated - the sweep below would hold vacuously"
    beside = tmp_path / "build" / "generated_html" / removed / "index.html"
    beside.parent.mkdir(parents=True)
    beside.write_text("another builder's output\n")
    in_flight = out_dir / f"sensortask_{removed}.py.tmp"
    in_flight.write_text("a concurrent run's file before its rename\n")
    (tmp_path / "devices" / f"{removed}.toml").unlink()
    assert generate_sensortask_modules.main() == 0

    left = sorted(p.relative_to(out_dir).as_posix() for p in out_dir.rglob("*") if p.is_file() and not p.name.endswith(".tmp"))
    assert not [name for name in left if removed in name], left
    assert {f"sensortask_{kept}.py", f"definitions/{kept}.json", f"api/{kept}.json"} <= set(left), left
    assert beside.is_file() and in_flight.is_file(), "the sweep reached past the generator's own finished outputs"
    assert json.loads((out_dir / ".inputs_stamp.json").read_text())["outputs"] == left, "the stamp must list exactly the tree's files"


def test_both_freshness_stamps_hash_every_input_and_land_after_every_other_output(generate_sensortask_modules: ModuleType, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Every file a generation reads, hashed for tests/_generated_tree.py with every file it leaves, and each TOML's hash for
    # the JS loader; renamed in last.
    monkeypatch.setattr(generate_sensortask_modules, "REPO_ROOT", tmp_path)
    out_dir = _one_device_tree(repo_root, tmp_path)
    for shared in ("buildgen", "toolchain"):
        (tmp_path / shared).symlink_to(repo_root / shared)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "_generate_sensortask_modules.py").write_bytes((repo_root / "scripts" / "_generate_sensortask_modules.py").read_bytes())
    (tmp_path / "devices" / "zz_test_fixture.toml").write_text("# a concurrent test's fixture, never an input\n")
    renamed: list[Path] = []
    real_replace = os.replace

    def recording_replace(src: "str | Path", dst: "str | Path") -> None:
        renamed.append(Path(dst))
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", recording_replace)
    assert generate_sensortask_modules.main() == 0

    stamps = [out_dir / ".inputs_stamp.json", out_dir / "definitions" / "inputs_stamp.json"]
    assert sorted(renamed[-2:]) == sorted(stamps), renamed[-4:]
    tomls = sorted(p for p in (tmp_path / "devices").glob("*.toml") if not p.stem.startswith("zz_test_"))
    named = ["buildgen/error_catalog.json", "toolchain/versions.toml", "toolchain/micropython_overrides.py", "scripts/_generate_sensortask_modules.py"]
    inputs = [*tomls, *(tmp_path / name for name in named)] + [p for pattern in ("buildgen/*.py", "src/*.py", "ext/*.py") for p in tmp_path.glob(pattern)]
    expected = {str(p.relative_to(tmp_path)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    assert "ext/microdot.py" in expected  # the frozen-module closure reads it (buildgen/frozen_modules.py)
    outputs = sorted(p.relative_to(out_dir).as_posix() for p in out_dir.rglob("*") if p.is_file())
    assert json.loads(stamps[0].read_text()) == {"inputs": expected, "outputs": outputs}
    assert json.loads(stamps[1].read_text()) == {"tomls": {DEVICE_NAMES[0]: expected[f"devices/{DEVICE_NAMES[0]}.toml"]}}
