"""scripts/_render_coverage.py reports only the files its anchor set names: a file missing from it
drops out of the report even when the raw dump recorded its lines. Pins the set to every .py file
under --src-dir, subdirectories included (digital_twin/unixport/ holds the UDP shim), and the XML-less render."""

import json
import sys
from pathlib import Path

import pytest
from _script_loader import load_script_module


def test_a_file_in_a_subdirectory_is_anchored(repo_root: Path, tmp_path: Path) -> None:
    render = load_script_module(repo_root / "scripts" / "_render_coverage.py", "_render_coverage_under_test")
    for rel in ("pkg/top.py", "pkg/sub/nested.py", "pkg/sub/notes.txt"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x = 1\n", encoding="utf-8")
    assert render.anchor_files(str(tmp_path), "pkg") == [str(tmp_path / "pkg" / "sub" / "nested.py"), str(tmp_path / "pkg" / "top.py")]


def test_a_render_given_no_xml_file_writes_html_and_markdown_only(repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The generated modules' render, as scripts/test.sh --coverage calls it: one dump line set, no XML.
    render = load_script_module(repo_root / "scripts" / "_render_coverage.py", "_render_coverage_under_test")
    module = tmp_path / "build" / "generated_src" / "sensortask_fixture_device.py"
    module.parent.mkdir(parents=True)
    module.write_text("x = 1\nif x:\n    y = 2\nelse:\n    y = 3\n", encoding="utf-8")
    (tmp_path / "raw").mkdir()
    (tmp_path / "raw" / "test_x.json").write_text(json.dumps({"build/generated_src/sensortask_fixture_device.py": [1, 2, 3]}), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    argv = ["--raw-dir", "raw", "--src-dir", "build/generated_src", "--html-dir", "htmlcov_generated", "--markdown-file", "coverage_summary_generated.md"]
    monkeypatch.setattr(sys, "argv", ["_render_coverage.py", *argv])
    assert render.main() == 0
    assert sorted(path.name for path in tmp_path.iterdir()) == [".coverage", "build", "coverage_summary_generated.md", "htmlcov_generated", "raw"]
    rows = [[cell.strip() for cell in line.strip("|").split("|")] for line in (tmp_path / "coverage_summary_generated.md").read_text(encoding="utf-8").splitlines()]
    assert [r"build/generated\_src/sensortask\_fixture\_device.py", "4", "1", "75%"] in rows, rows  # markdown escapes "_"
    assert (tmp_path / "htmlcov_generated" / "index.html").is_file()
