"""scripts/_render_coverage.py reports only the files its anchor set names: a file missing from it
drops out of the report even when the raw dump recorded its lines. Pins the set to every .py file
under --src-dir, subdirectories included (digital_twin/unixport/ holds the UDP shim)."""

import sys
from pathlib import Path
from types import ModuleType

import pytest
from _script_loader import load_script_module


def test_a_file_in_a_subdirectory_is_anchored(repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # coverage.py is the script's own `uv run` dependency, not this tier's; the anchor set never touches it.
    monkeypatch.setitem(sys.modules, "coverage", ModuleType("coverage"))
    render = load_script_module(repo_root / "scripts" / "_render_coverage.py", "_render_coverage_under_test")
    for rel in ("pkg/top.py", "pkg/sub/nested.py", "pkg/sub/notes.txt"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x = 1\n")
    assert render.anchor_files(str(tmp_path), "pkg") == [str(tmp_path / "pkg" / "sub" / "nested.py"), str(tmp_path / "pkg" / "top.py")]
