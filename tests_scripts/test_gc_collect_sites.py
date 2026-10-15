"""SPECIFICATION.md I.4(f.1)'s boot-confined placement reset, through scripts/_check_gc_collect_sites.py: `gc.collect()`
lives in exactly two functions, reached by any name bound to gc or to gc.collect, and a new site, a renamed allowed
one or a file that does not parse fails - the live tree included, generated modules in memory."""

import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
from _script_loader import load_script_module

_ALLOWED_SRC = "import gc\n\n\nclass SystemService:\n    async def run_setups(self) -> None:\n        gc.collect()\n\n    async def start_tasks(self) -> None:\n        gc.collect()\n"


@pytest.fixture(scope="module")
def checker(repo_root: Path) -> ModuleType:
    return load_script_module(repo_root / "scripts" / "_check_gc_collect_sites.py", "_check_gc_collect_sites")


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    # A stand-in repo holding only the allowed sites: every case adds one file, so the verdict is attributable to it.
    (tmp_path / "src").mkdir()
    (tmp_path / "buildgen").mkdir()
    (tmp_path / "devices").mkdir()
    (tmp_path / "src" / "asy_system_service.py").write_text(_ALLOWED_SRC, encoding="utf-8")
    (tmp_path / "buildgen" / "codegen.py").write_text('lines.append("    sysfunct.run_setups(_collect_setups())")\n', encoding="utf-8")
    return tmp_path


def test_the_allowed_sites_alone_are_clean(checker: ModuleType, tree: Path) -> None:
    assert checker.scan_tree(tree).findings == []


@pytest.mark.parametrize(
    ("source", "line"),
    [
        ("import gc\ngc.collect()\n", 2),
        ("import gc as g\n\ndef run():\n    g.collect()\n", 4),
        ("from gc import collect\n\ndef run():\n    collect()\n", 4),
        ("from gc import collect as c\nc()\n", 2),
        ("import gc\nsweep = gc.collect\nsweep()\n", 3),
    ],
    ids=["module-level", "module-alias", "imported-function", "function-alias", "assigned-alias"],
)
def test_a_collect_outside_the_table_is_reported_whatever_its_spelling(checker: ModuleType, tree: Path, source: str, line: int) -> None:
    (tree / "src" / "asy_other.py").write_text(source, encoding="utf-8")
    findings = checker.scan_tree(tree).findings
    assert len(findings) == 1 and findings[0].startswith(f"src/asy_other.py:{line}: gc.collect() in "), findings
    assert findings[0].endswith(" is not an allowed site (SPECIFICATION.md I.4(e)/(f.1))"), findings


def test_an_unrelated_collect_method_is_not_the_gc_call(checker: ModuleType, tree: Path) -> None:
    (tree / "src" / "asy_other.py").write_text("def f(bag):\n    bag.collect()\n    bag.gc.collect()\n", encoding="utf-8")
    assert checker.scan_tree(tree).findings == []


def test_a_site_in_another_function_of_the_allowed_file_is_reported_by_its_qualified_name(checker: ModuleType, tree: Path) -> None:
    (tree / "src" / "asy_system_service.py").write_text(_ALLOWED_SRC + "\n    def supervise(self) -> None:\n        gc.collect()\n", encoding="utf-8")
    assert checker.scan_tree(tree).findings == ["src/asy_system_service.py:12: gc.collect() in SystemService.supervise is not an allowed site (SPECIFICATION.md I.4(e)/(f.1))"]


def test_a_renamed_allowed_function_leaves_a_stale_row_that_is_reported(checker: ModuleType, tree: Path) -> None:
    (tree / "src" / "asy_system_service.py").write_text(_ALLOWED_SRC.replace("start_tasks", "start_all"), encoding="utf-8")
    findings = checker.scan_tree(tree).findings
    assert "src/asy_system_service.py: the allowed site SystemService.start_tasks holds no gc.collect() call - restore it or remove its row" in findings
    assert any("SystemService.start_all is not an allowed site" in f for f in findings), findings


@pytest.mark.parametrize("filename", ["codegen.py", "sub/leaf.py"])
def test_a_collect_anywhere_in_buildgen_s_text_is_reported(checker: ModuleType, tree: Path, filename: str) -> None:
    # The generator emits none: a collect in an emitted string is a violation like a call.
    (tree / "buildgen" / filename).parent.mkdir(exist_ok=True)
    (tree / "buildgen" / filename).write_text('lines.append("    gc.collect()")\n', encoding="utf-8")
    assert checker.scan_tree(tree).findings == [f"buildgen/{filename}:1: gc.collect( in buildgen/'s text - the generated modules carry none (SPECIFICATION.md I.4(f.1))"]


def test_a_subdirectory_of_src_is_searched_too(checker: ModuleType, tree: Path) -> None:
    (tree / "src" / "sub").mkdir()
    (tree / "src" / "sub" / "leaf.py").write_text("import gc\ngc.collect()\n", encoding="utf-8")
    assert [f.split(":")[0] for f in checker.scan_tree(tree).findings] == ["src/sub/leaf.py"]


def test_a_file_that_does_not_parse_is_an_error_never_a_skip(checker: ModuleType, tree: Path) -> None:
    (tree / "src" / "asy_broken.py").write_text("def (:\n", encoding="utf-8")
    result = checker.scan_tree(tree)
    assert result.errors and result.errors[0].startswith("src/asy_broken.py:1: cannot parse"), result.errors


def test_a_root_with_no_source_to_scan_cannot_look(checker: ModuleType, tmp_path: Path) -> None:
    # A --root naming the wrong directory finds nothing to check: an error, never a clean pass.
    result = checker.scan_tree(tmp_path)
    assert result.errors == ["src/: no Python file to scan - the gc.collect() check could not look"], result.errors


def test_the_scopes_with_no_rows_yet_are_named_as_unchecked(checker: ModuleType, tree: Path) -> None:
    assert checker.scan_tree(tree).unchecked == ("tests", "digital_twin", "tests_hardware")


def test_the_live_tree_passes_the_command_with_its_generated_modules(repo_root: Path) -> None:
    # The command lint.sh runs: exit 0 on the real tree, every derived device's module and boot entries checked.
    done = subprocess.run([sys.executable, str(repo_root / "scripts" / "_check_gc_collect_sites.py")], cwd=repo_root, capture_output=True, text=True, check=False, timeout=120)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "generated modules checked:" in done.stdout and "not checked yet: tests/, digital_twin/, tests_hardware/" in done.stdout, done.stdout


@pytest.mark.parametrize(("planted", "code"), [("import gc\ngc.collect()\n", 1), ("def (:\n", 2)], ids=["finding", "unparsable"])
def test_the_command_exits_1_on_a_finding_and_2_when_it_cannot_look(checker: ModuleType, tree: Path, planted: str, code: int, capsys: pytest.CaptureFixture[str]) -> None:
    (tree / "src" / "asy_other.py").write_text(planted, encoding="utf-8")
    assert checker.main(["--root", str(tree)]) == code
    assert "src/asy_other.py:" in capsys.readouterr().err
