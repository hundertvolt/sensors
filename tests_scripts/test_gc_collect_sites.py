"""Structural guard for SPECIFICATION.md I.4(f.1)'s boot-confined placement reset: `gc.collect()`
lives in exactly two places, and a new call or a rename of either fails here - attributed to its
enclosing function, so this catches what a path-based grep would miss."""

import ast
from pathlib import Path

# The whole allowance. src/ is checked structurally (a real call node attributed to its enclosing
# function, so a rename of an allowed site fails too); buildgen/ textually, since the generator emits
# none. scripts/lint.sh greps the same rule as a fast path.
_ALLOWED_SRC_SITES = {("asy_system_service.py", "run_setups"), ("asy_system_service.py", "start_tasks")}


def _is_gc_collect(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "collect"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "gc"
    )


def _collect_call_sites(tree: ast.Module) -> "list[str]":
    # Every `gc.collect(...)` call in this module, labelled with the nearest enclosing function -
    # "<module>" for one at import time, which would run on every boot. Explicit descent, not
    # ast.walk(): a walk from the module reaches calls inside functions too and would double-count.
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


def test_src_calls_gc_collect_only_in_the_two_boot_lists(repo_root: Path) -> None:
    found = set()
    for path in sorted((repo_root / "src").glob("*.py")):
        for owner in _collect_call_sites(ast.parse(path.read_text())):
            found.add((path.name, owner))
    assert found == _ALLOWED_SRC_SITES, (
        f"gc.collect() sites in src/ are {sorted(found)}, expected exactly {sorted(_ALLOWED_SRC_SITES)}. "
        "I.4(f) confines it to the two one-time boot lists; anything else is the run phase."
    )


def test_buildgen_emits_no_gc_collect(repo_root: Path) -> None:
    # The boot lists run inside SystemService, so no generated module carries a collect of its own.
    found = sorted(str(path.relative_to(repo_root)) for path in (repo_root / "buildgen").rglob("*.py") if "gc.collect(" in path.read_text())
    assert not found, f"buildgen/ files containing 'gc.collect(' are {found}; the generator emits none (SPECIFICATION.md Part I.4(f.1))"


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
