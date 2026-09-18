"""Structural guard for SPECIFICATION.md I.4(f.1)'s boot-confined placement reset: `gc.collect()`
lives in exactly two places, and a new call or a rename of either fails here - attributed to its
enclosing function, so this catches what a path-based grep would miss."""

import ast
from pathlib import Path

# The whole allowance, spelled out. src/ is checked structurally (a real call node, attributed to
# its enclosing function); buildgen/ is checked textually because there the call only ever exists
# inside codegen.py's emitted-source strings, where no Call node can be found. scripts/lint.sh
# greps for the same rule as a fast path; this test is the precise one - it attributes each call to
# its enclosing function, so it also catches a rename of the allowed site.
_ALLOWED_SRC_SITES = {("system_service.py", "start_and_check_tasks")}
_ALLOWED_BUILDGEN_FILES = {"codegen.py"}


def _is_gc_collect(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "collect"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "gc"
    )


def _collect_call_sites(tree: ast.Module) -> "list[str]":
    """Every `gc.collect(...)` call in this module, each labelled with the nearest enclosing
    function - "<module>" for one at import time, which would run on every boot. Explicit descent
    rather than ast.walk(): a walk from the module reaches calls inside functions too, and would
    attribute them twice."""
    sites: list[str] = []

    def visit(node: ast.AST, owner: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                visit(child, child.name)
                continue
            if _is_gc_collect(child):
                sites.append(owner)
            visit(child, owner)

    visit(tree, "<module>")
    return sites


def test_src_calls_gc_collect_only_in_the_task_starter_list(repo_root: Path) -> None:
    found = set()
    for path in sorted((repo_root / "src").glob("*.py")):
        for owner in _collect_call_sites(ast.parse(path.read_text())):
            found.add((path.name, owner))
    assert found == _ALLOWED_SRC_SITES, (
        f"gc.collect() sites in src/ are {sorted(found)}, expected exactly {sorted(_ALLOWED_SRC_SITES)}. "
        "I.4(f) confines it to the two one-time boot lists; anything else is the run phase."
    )


def test_buildgen_emits_gc_collect_only_from_codegen(repo_root: Path) -> None:
    found = {path.name for path in sorted((repo_root / "buildgen").rglob("*.py")) if "gc.collect(" in path.read_text()}
    assert found == _ALLOWED_BUILDGEN_FILES, (
        f"buildgen/ files containing 'gc.collect(' are {sorted(found)}, expected exactly {sorted(_ALLOWED_BUILDGEN_FILES)}"
    )


def test_the_guard_would_notice_a_new_site(tmp_path: Path) -> None:
    # A test for the guard: the walker must attribute a call to the function holding it, and must
    # see one added at module level too - the case that would run on every import.
    (tmp_path / "m.py").write_text(
        "import gc\n\n\ndef boot() -> None:\n    gc.collect()\n\n\ngc.collect()\n",
    )
    assert sorted(_collect_call_sites(ast.parse((tmp_path / "m.py").read_text()))) == ["<module>", "boot"]


def test_the_guard_ignores_an_unrelated_collect_method(tmp_path: Path) -> None:
    # `something_else.collect()` is not the gc call, and must not be reported as one.
    (tmp_path / "m.py").write_text("def f(bag) -> None:\n    bag.collect()\n")
    assert _collect_call_sites(ast.parse((tmp_path / "m.py").read_text())) == []
