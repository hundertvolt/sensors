"""python_files() never lists a directory under the scratch the MicroPython tier and the twins delete while this tier
runs beside them: a directory deleted mid-walk raises from inside the walk, so filtering its results comes too late."""

import os
from pathlib import Path

import pytest
from _repo_scan import CONCURRENT_SCRATCH, python_files

_TREE = ("tests/a.py", "tests/sub/c.py", "tests/_tmp/key/b.py", "tests/_tmp/top.py", "digital_twin/e.py", "digital_twin/config/d.py", "digital_twin/notes.txt")


def _plant(root: Path) -> None:
    for name in _TREE:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text("x = 1\n")


def test_the_walk_lists_no_directory_under_concurrent_scratch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _plant(tmp_path)
    listed: list[str] = []
    real = os.scandir

    def recording(path: "str | os.PathLike[str]") -> "os._ScandirIterator[str]":
        listed.append(Path(path).relative_to(tmp_path).as_posix())
        return real(path)

    monkeypatch.setattr(os, "scandir", recording)
    found = [p.relative_to(tmp_path).as_posix() for scope in ("tests", "digital_twin") for p in python_files(tmp_path, scope)]
    assert found == ["tests/a.py", "tests/sub/c.py", "digital_twin/e.py"]
    assert listed == ["tests", "tests/sub", "digital_twin"], "the recorder saw a different walk than the one asserted on"
    assert not [d for d in listed if any(d == s or d.startswith(f"{s}/") for s in CONCURRENT_SCRATCH)]


def test_a_directory_lost_outside_scratch_raises_rather_than_reading_as_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _plant(tmp_path)
    real = os.scandir

    def losing(path: "str | os.PathLike[str]") -> "os._ScandirIterator[str]":
        if Path(path).name == "sub":
            raise FileNotFoundError(path)
        return real(path)

    monkeypatch.setattr(os, "scandir", losing)
    with pytest.raises(FileNotFoundError):
        python_files(tmp_path, "tests")


def test_a_scope_that_does_not_exist_holds_no_files(tmp_path: Path) -> None:
    assert python_files(tmp_path, "tests") == []
