"""Tests scripts/_generate_sensortask_modules.py (SPECIFICATION.md Part E.3's build/generated_src/
pre-generation step) - both its real-device happy path (module source + wiring-plan JSON) and its
BuildError-reporting failure path."""

import json
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from _script_loader import load_script_module

from buildgen.errors import BuildError
from buildgen.generate import generate_device
from buildgen.twin_wiring import compute_twin_wiring

DEVICE_NAMES = ["dev", "wozi", "arzi", "klkizi", "grkizi", "schlafzi"]


@pytest.fixture
def generate_sensortask_modules(repo_root: Path) -> ModuleType:
    return load_script_module(repo_root / "scripts" / "_generate_sensortask_modules.py", "_generate_sensortask_modules")


def test_main_generates_every_real_device_matching_generate_device_directly(generate_sensortask_modules: ModuleType, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(generate_sensortask_modules, "REPO_ROOT", tmp_path)
    (tmp_path / "devices").symlink_to(repo_root / "devices")
    (tmp_path / "src").symlink_to(repo_root / "src")
    (tmp_path / "ext").symlink_to(repo_root / "ext")

    exit_code = generate_sensortask_modules.main()
    assert exit_code == 0

    out_dir = tmp_path / "build" / "generated_src"
    for device in DEVICE_NAMES:
        expected = generate_device(repo_root / "devices" / f"{device}.toml", repo_root / "src", repo_root / "ext")
        assert (out_dir / f"sensortask_{device}.py").read_text() == expected.module_source
        expected_plan = compute_twin_wiring(expected.model)
        # "instances" is main()'s own addition on top of compute_twin_wiring()'s documented shape
        # (an independent, pre-construction driver-presence oracle for tests/test_sensortask.py -
        # see main()'s own comment) - checked separately against the model directly, then popped
        # before comparing the rest of the plan against compute_twin_wiring()'s own return value
        # unchanged.
        actual_plan = json.loads((out_dir / f"sensortask_{device}_wiring_plan.json").read_text())
        assert actual_plan.pop("instances") == sorted({spec.driver for spec in expected.model.instances.values()})
        assert actual_plan == expected_plan


def test_main_reports_a_build_error_and_exits_nonzero_without_crashing(generate_sensortask_modules: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    # A malformed devices/*.toml is a real, reachable failure (a hand-edited TOML, a bad merge) -
    # the loop's own `except BuildError` must report it and return 1, not let a traceback escape or
    # silently leave a partially-generated build/generated_src/ with no explanation. Real generation
    # logic is bypassed (generate_device monkeypatched) so this test doesn't need a genuinely
    # malformed TOML fixture to trigger buildgen's own validation - only this script's own reporting
    # contract is under test here.
    (tmp_path / "devices").mkdir()
    (tmp_path / "devices" / "broken.toml").write_text("# not a real device\n")
    monkeypatch.setattr(generate_sensortask_modules, "REPO_ROOT", tmp_path)

    def fake_generate_device(*_args: object, **_kwargs: object) -> SimpleNamespace:
        raise BuildError("broken", "simulated failure for broken.toml")

    monkeypatch.setattr(generate_sensortask_modules, "generate_device", fake_generate_device)

    exit_code = generate_sensortask_modules.main()
    assert exit_code == 1
    assert "simulated failure for broken.toml" in capsys.readouterr().err

    # Never left holding a half-written module (or wiring plan) for the device that failed.
    assert not list((tmp_path / "build" / "generated_src").glob("sensortask_broken*"))
