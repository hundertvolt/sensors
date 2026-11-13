"""Every per-field result word comes from asy_config_manager's VALID/UNCHANGED/INVALID/FAILED (SPECIFICATION.md
G.2): a second spelling of one drifts from the wire contract unseen. The scan reads src/ and every device's generated
module; tests/ keeps its literals, which state the wire contract."""

import ast
import shutil
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES, device_toml

from buildgen.generate import generate_device

_REPO_ROOT = Path(__file__).resolve().parent.parent
_WORDS = {"VALID": "Valid", "UNCHANGED": "Unchanged", "INVALID": "Invalid", "FAILED": "Failed"}
_HOME = "asy_config_manager.py"
_VALIDITY_TYPE = "WriteValidity"


def _docstrings(tree: ast.Module) -> "set[int]":
    nodes: list[ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef] = [tree]
    nodes += [n for n in ast.walk(tree) if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))]
    return {id(n.body[0].value) for n in nodes if n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}


def _home_definitions(tree: ast.Module) -> "set[int]":
    # The module-level spelling of each word (`VALID: "Final" = "Valid"`) and WriteValidity's Literal members.
    found = {
        id(node.value) for node in tree.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and isinstance(node.value, ast.Constant) and _WORDS.get(node.target.id) == node.value.value
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == _VALIDITY_TYPE for t in node.targets):
            found |= {id(n) for n in ast.walk(node.value) if isinstance(n, ast.Constant) and n.value in _WORDS.values()}
    return found


def find_spellings(label: str, source: str, *, home: bool = False) -> "list[str]":
    # `label:line: "word"` for each string constant equal to a result word; docstrings are not code.
    tree = ast.parse(source)
    skipped = _docstrings(tree) | (_home_definitions(tree) if home else set())
    return [
        f"{label}:{node.lineno}: {node.value!r}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and node.value in _WORDS.values() and id(node) not in skipped
    ]


def scan_src(src_dir: Path) -> "list[str]":
    return sorted(
        line
        for path in sorted(src_dir.glob("*.py"))
        for line in find_spellings(f"src/{path.name}", path.read_text(encoding="utf-8"), home=path.name == _HOME)
    )


@pytest.fixture(scope="module")
def generated_modules() -> "list[tuple[str, str]]":
    # Generated fresh per device, as the other generated-module checks do, never read from a stale build/.
    return [
        (f"build/generated_src/sensortask_{device}.py", generate_device(device_toml(device), _REPO_ROOT / "src", _REPO_ROOT / "ext").module_source)
        for device in DEVICE_NAMES
    ]


def test_src_spells_no_result_word_outside_the_config_manager() -> None:
    found = scan_src(_REPO_ROOT / "src")
    assert not found, "a result word spelled outside asy_config_manager.py - use its VALID/UNCHANGED/INVALID/FAILED:\n" + "\n".join(f"  {line}" for line in found)


def test_no_generated_module_spells_a_result_word(generated_modules: "list[tuple[str, str]]") -> None:
    found = [line for label, source in generated_modules for line in find_spellings(label, source)]
    assert not found, "a generated module spells a result word - emit the config manager's constant:\n" + "\n".join(f"  {line}" for line in found)


def test_the_home_still_holds_each_word_once_and_the_validity_type() -> None:
    # The exemption follows the code: a renamed constant or type would leave it guarding nothing.
    tree = ast.parse((_REPO_ROOT / "src" / _HOME).read_text(encoding="utf-8"))
    exempt = _home_definitions(tree)
    words = [str(n.value) for n in ast.walk(tree) if isinstance(n, ast.Constant) and id(n) in exempt]
    assert sorted(words) == sorted([*_WORDS.values(), *_WORDS.values()]), words


@pytest.mark.parametrize("filename", ["asy_wifi_service.py", _HOME])
def test_a_planted_spelling_is_named_with_its_line(tmp_path: Path, filename: str) -> None:
    # Bite: one "Valid" in a setter, in a module and in the home outside its four definitions.
    src_dir = tmp_path / "src"
    shutil.copytree(_REPO_ROOT / "src", src_dir)
    before = scan_src(src_dir)
    lines = (src_dir / filename).read_text(encoding="utf-8").splitlines()
    lines += ["", "", "def _planted_setter(results: dict) -> None:", '    results["Key"] = "Valid"']
    (src_dir / filename).write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert sorted(set(scan_src(src_dir)) - set(before)) == [f"src/{filename}:{len(lines)}: 'Valid'"]


def test_a_docstring_equal_to_a_word_is_not_a_spelling() -> None:
    assert find_spellings("x.py", 'def f() -> None:\n    "Valid"\n') == []
    assert find_spellings("x.py", 'def f() -> str:\n    return "Valid"\n') == ["x.py:2: 'Valid'"]
