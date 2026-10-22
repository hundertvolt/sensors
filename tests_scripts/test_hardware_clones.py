"""No clone group in the hardware levels: two or more non-trivial functions in tests_hardware/ with the same body (by
normalised AST, docstring aside) fail naming each copy - the shared code belongs in one helper, or in a device-script
include under _shared/, which this scan leaves out."""

import ast
from pathlib import Path

_TESTS_HARDWARE = Path(__file__).resolve().parents[1] / "tests_hardware"
# Below this many AST nodes a body is a one-liner wrapper or a stub, whose repetition is no duplicated logic.
_MIN_NODES = 25


def _body_key(fn: "ast.FunctionDef | ast.AsyncFunctionDef") -> "str | None":
    body = fn.body[1:] if fn.body and isinstance(fn.body[0], ast.Expr) and isinstance(fn.body[0].value, ast.Constant) and isinstance(fn.body[0].value.value, str) else fn.body
    if sum(1 for stmt in body for _ in ast.walk(stmt)) < _MIN_NODES:
        return None
    return "\n".join(ast.dump(stmt, include_attributes=False) for stmt in body)


def clone_groups(root: Path) -> "list[list[str]]":
    groups: dict[str, list[str]] = {}
    for path in sorted(p for p in root.rglob("*.py") if "_shared" not in p.parts):
        for fn in [n for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]:
            key = _body_key(fn)
            if key is not None:
                groups.setdefault(key, []).append(f"{path.relative_to(root).as_posix()}::{fn.name}")
    return sorted(sorted(members) for members in groups.values() if len(members) > 1)


def test_no_function_body_is_copied_in_the_hardware_levels() -> None:
    groups = clone_groups(_TESTS_HARDWARE)
    assert not groups, "identical function bodies - one helper (or a device_scripts/_shared include) instead:\n  " + "\n  ".join(" = ".join(g) for g in groups)


def test_the_clone_scan_bites(tmp_path: Path) -> None:
    body = "    total = 0\n    for value in values:\n        if value > limit:\n            total += value * 2\n    return total\n"
    (tmp_path / "a.py").write_text(f"def first(values, limit):\n{body}", encoding="utf-8")
    (tmp_path / "b.py").write_text(f'def second(values, limit):\n    """Same logic, other name."""\n{body}\n\ndef small():\n    return 1\n', encoding="utf-8")
    (tmp_path / "_shared").mkdir()
    (tmp_path / "_shared" / "c.py").write_text(f"def included(values, limit):\n{body}", encoding="utf-8")
    assert clone_groups(tmp_path) == [["a.py::first", "b.py::second"]]
