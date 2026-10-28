"""The board on the bench is named by data: exactly one device TOML sets [device] bench = true, and both readers
of that rule (tests_hardware/harness.py, tests_scripts/_devices.py) find it, refuse none or several naming the
files, and take $BENCH_DEVICE only when it names a real device TOML."""

import shutil
import sys
from pathlib import Path

import _devices
import pytest
import tomllib
from _devices import DEVICE_NAMES, device_toml

from buildgen.errors import BuildError
from buildgen.validate import build_model

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests_hardware"))

import harness


def _flagged() -> "list[str]":
    return [d for d in DEVICE_NAMES if tomllib.loads(device_toml(d).read_text(encoding="utf-8"))["device"].get("bench") is True]


def _write(directory: Path, name: str, *, bench: "bool | None") -> None:
    flag = "" if bench is None else f"bench = {str(bench).lower()}\n"
    (directory / f"{name}.toml").write_text(f'[device]\nname = "{name}"\n{flag}', encoding="utf-8")


def test_exactly_one_device_toml_names_the_bench_board() -> None:
    assert len(_flagged()) == 1, f"[device] bench = true is set in {_flagged()} - exactly one board is on the bench"


def test_both_readers_name_the_flagged_device(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BENCH_DEVICE", raising=False)
    assert harness.bench_device() == _devices.bench_device() == _flagged()[0]


@pytest.mark.parametrize("flags", [(False, None), (True, True)], ids=["none", "two"])
def test_none_or_several_flagged_tomls_are_refused_naming_the_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, flags: "tuple[bool, bool | None]") -> None:
    for index, flag in enumerate(flags):
        _write(tmp_path, f"fixture{index}", bench=flag)
    _write(tmp_path, "zz_test_leak", bench=True)  # a leaked live-tree fixture never counts
    monkeypatch.delenv("BENCH_DEVICE", raising=False)
    monkeypatch.setattr(harness, "DEVICES_DIR", tmp_path)
    named = "fixture0.toml" if flags[1] else "bench = true"
    with pytest.raises(harness.HardwareNotAvailableError, match=named):
        harness.bench_device()
    with pytest.raises(AssertionError, match=named):
        _devices.bench_device(tmp_path)


def test_the_environment_override_names_an_existing_device_or_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write(tmp_path, "fixture0", bench=True)
    _write(tmp_path, "fixture1", bench=None)
    monkeypatch.setattr(harness, "DEVICES_DIR", tmp_path)
    monkeypatch.setenv("BENCH_DEVICE", "fixture1")
    assert harness.bench_device() == "fixture1"
    monkeypatch.setenv("BENCH_DEVICE", "fixture-absent")
    with pytest.raises(harness.HardwareNotAvailableError, match=r"fixture-absent\.toml"):
        harness.bench_device()


def test_the_build_refuses_a_bench_flag_that_is_no_bool(tmp_path: Path, repo_root: Path) -> None:
    source = device_toml(_flagged()[0])
    target = tmp_path / source.name
    shutil.copy(source, target)
    target.write_text(target.read_text(encoding="utf-8").replace("bench = true", "bench = 1"), encoding="utf-8")
    with pytest.raises(BuildError, match=r"\[device\]\.bench must be true or false"):
        build_model(target, repo_root / "src")
