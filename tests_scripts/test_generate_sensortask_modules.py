"""Tests scripts/_generate_sensortask_modules.py (SPECIFICATION.md Part E.3's build/generated_src/
pre-generation step) - both its real-device happy path (module source, wiring-plan JSON, definitions,
their manifest and the REST API reference) and its BuildError-reporting failure path."""

import json
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
        expected_plan = compute_twin_wiring(expected.model)
        # "instances" is main()'s addition on top of compute_twin_wiring()'s shape, an
        # independent pre-construction driver-presence oracle - checked against the model
        # directly, then popped so the rest compares against that function's return unchanged.
        actual_plan = json.loads((out_dir / f"sensortask_{device}_wiring_plan.json").read_text())
        assert actual_plan.pop("instances") == sorted({spec.driver for spec in expected.model.instances.values()})
        assert actual_plan == expected_plan
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
        raise BuildError("broken", "simulated failure for broken.toml")

    monkeypatch.setattr(generate_sensortask_modules, "generate_device", fake_generate_device)

    exit_code = generate_sensortask_modules.main()
    assert exit_code == 1
    assert "simulated failure for broken.toml" in capsys.readouterr().err

    # Never left holding a half-written module, wiring plan, definitions or API reference for the device that failed.
    out_dir = tmp_path / "build" / "generated_src"
    assert not [*out_dir.glob("sensortask_broken*"), *out_dir.glob("definitions/broken*"), *out_dir.glob("api/broken*")]


@pytest.mark.parametrize("stage", ["generate_definitions", "generate_api_reference"])
def test_a_later_stage_build_error_is_reported_and_leaves_none_of_that_device(generate_sensortask_modules: ModuleType, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], stage: str) -> None:
    # A device's outputs are all computed before any is written, so a stage after the module's own
    # generation failing is the same one-line report and exit 1, with no file of that device behind.
    monkeypatch.setattr(generate_sensortask_modules, "REPO_ROOT", tmp_path)
    (tmp_path / "devices").mkdir()
    (tmp_path / "devices" / f"{DEVICE_NAMES[0]}.toml").symlink_to(repo_root / "devices" / f"{DEVICE_NAMES[0]}.toml")
    (tmp_path / "src").symlink_to(repo_root / "src")
    (tmp_path / "ext").symlink_to(repo_root / "ext")

    def failing_stage(*_args: object, **_kwargs: object) -> SimpleNamespace:
        raise BuildError(DEVICE_NAMES[0], f"simulated {stage} failure")

    monkeypatch.setattr(generate_sensortask_modules, stage, failing_stage)

    assert generate_sensortask_modules.main() == 1
    assert f"simulated {stage} failure" in capsys.readouterr().err
    out_dir = tmp_path / "build" / "generated_src"
    assert not [p for p in out_dir.rglob("*") if p.is_file()]
