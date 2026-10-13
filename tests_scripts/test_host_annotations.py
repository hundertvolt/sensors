"""Host code evaluates its annotations natively (pyproject.toml's requires-python >= 3.11): no host file imports
`annotations` from `__future__`, and no annotation evaluated at runtime names a TYPE_CHECKING-only import or a class
defined after it, unquoted - either raises NameError at import or call time (SPECIFICATION.md Part L.5)."""

import ast
from typing import TypeGuard

import pytest
from _repo_scan import REPO_ROOT, repo_files

HOST_SCOPES = ("buildgen/", "scripts/", "toolchain/", "tests_scripts/", "tests_hardware/")
# MicroPython code pushed to the board, checked with src/ (SPECIFICATION.md Part B.15), not host code.
_NOT_HOST = ("tests_hardware/device_scripts/",)


def _bound_names(stmts: list[ast.stmt]) -> set[str]:
    # Every name these statements bind in their own scope: imports, defs, classes and store targets, never
    # a nested function's or class's body. A TYPE_CHECKING block's body binds nothing at runtime; its else does.
    found: set[str] = set()
    for stmt in stmts:
        if _is_type_checking_guard(stmt):
            found |= _bound_names(stmt.orelse)
            continue
        stack: list[ast.AST] = [stmt]
        while stack:
            node = stack.pop()
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                found |= {(alias.asname or alias.name).split(".")[0] for alias in node.names}
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                found.add(node.name)
                continue
            elif isinstance(node, ast.Lambda):
                continue
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                found.add(node.id)
            stack.extend(ast.iter_child_nodes(node))
    return found


def _is_type_checking_guard(stmt: ast.AST) -> TypeGuard[ast.If]:
    if not isinstance(stmt, ast.If):
        return False
    test = stmt.test
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING")


def _runtime_annotations(tree: ast.Module) -> list[tuple[ast.expr | None, int | None]]:
    # (annotation, index of the module-level statement during which it is evaluated) for every annotation Python
    # evaluates: every def's signature at any depth, and a module or class body's annotated assignment - never a
    # function body's, and nothing inside a TYPE_CHECKING block. The index is None where evaluation waits for a call.
    found: list[tuple[ast.expr | None, int | None]] = []

    def visit(node: ast.AST, when: int | None, *, in_function: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if _is_type_checking_guard(child):
                for stmt in child.orelse:
                    visit_stmt(stmt, when, in_function=in_function)
                continue
            visit_stmt(child, when, in_function=in_function)

    def visit_stmt(child: ast.AST, when: int | None, *, in_function: bool) -> None:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found.extend((annotation, when) for annotation in _signature_annotations(child))
            visit(child, None, in_function=True)
        elif isinstance(child, ast.ClassDef):
            visit(child, when, in_function=False)  # a class body evaluates its annotations, even inside a function
        elif isinstance(child, ast.AnnAssign):
            if not in_function:
                found.append((child.annotation, when))
        elif isinstance(child, ast.Lambda):
            return
        else:
            visit(child, when, in_function=in_function)

    for index, stmt in enumerate(tree.body):
        if _is_type_checking_guard(stmt):
            for inner in stmt.orelse:
                visit_stmt(inner, index, in_function=False)
            continue
        visit_stmt(stmt, index, in_function=False)
    return found


def _signature_annotations(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.expr | None]:
    args = func.args
    every = [*args.posonlyargs, *args.args, *args.kwonlyargs, *(a for a in (args.vararg, args.kwarg) if a is not None)]
    return [*(a.annotation for a in every), func.returns]


def _unquoted_names(annotation: ast.expr | None) -> list[ast.Name]:
    # The bare names an annotation evaluates; a string constant (a quoted part) evaluates nothing.
    if annotation is None:
        return []
    return [node for node in ast.walk(annotation) if isinstance(node, ast.Name)]


def annotation_findings(label: str, source: str) -> list[str]:
    tree = ast.parse(source, filename=label)
    findings = [
        f"{label}:{node.lineno}: imports annotations from __future__ - host code evaluates its annotations natively"
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "__future__" and any(alias.name == "annotations" for alias in node.names)
    ]
    guarded = type_checking_only_names(tree)
    first_bound: dict[str, int] = {}
    for index, stmt in enumerate(tree.body):
        for bound in _bound_names([stmt]):
            first_bound.setdefault(bound, index)
    for annotation, when in _runtime_annotations(tree):
        for name in _unquoted_names(annotation):
            if name.id in guarded:
                findings.append(f"{label}:{name.lineno}: `{name.id}` is imported under TYPE_CHECKING only - quote it in this annotation")
            elif when is not None and first_bound.get(name.id, -1) >= when:
                findings.append(f"{label}:{name.lineno}: `{name.id}` is not defined yet when this annotation is evaluated - quote it")
    return findings


def host_files() -> list[str]:
    return [p for p in repo_files() if p.endswith(".py") and p.startswith(HOST_SCOPES) and not p.startswith(_NOT_HOST)]


def type_checking_only_names(tree: ast.Module) -> set[str]:
    # Names a module-level `if TYPE_CHECKING:` body binds and nothing else at module level binds at runtime.
    guarded: set[str] = set()
    for stmt in tree.body:
        if _is_type_checking_guard(stmt):
            guarded |= _bound_names(stmt.body)
    return guarded - _bound_names(tree.body)


def test_no_host_file_imports_future_annotations_or_evaluates_an_unbound_name() -> None:
    findings = [f for path in host_files() for f in annotation_findings(path, (REPO_ROOT / path).read_text(encoding="utf-8"))]
    assert not findings, "\n".join(findings)


def test_the_scan_reaches_every_host_scope() -> None:
    # A scope that lists no file is a scan that silently stopped looking there.
    files = host_files()
    empty = [scope for scope in HOST_SCOPES if not any(p.startswith(scope) for p in files)]
    assert not empty, f"no Python file found under {empty}"
    assert not [p for p in files if p.startswith(_NOT_HOST)]


_CLEAN = (
    "import asyncio\n"
    "from typing import TYPE_CHECKING\n\n"
    "if TYPE_CHECKING:\n"
    "    from harness import Board\n"
    "else:\n"
    "    from fallback import Spare\n\n\n"
    'def run(board: "Board", spare: Spare, loop: asyncio.AbstractEventLoop) -> "list[Board]":\n'
    "    local: Board = board\n"
    '    def inner(b: "Board") -> None: ...\n'
    "    return [local]\n\n\n"
    "class Later:\n"
    '    def clone(self) -> "Later": ...\n'
)


def test_a_clean_module_reports_nothing() -> None:
    # A guard on the checker: quoted names, a runtime else-branch import and a function-local annotation all pass.
    assert annotation_findings("m.py", _CLEAN) == []


@pytest.mark.parametrize(
    ("source", "needle"),
    [
        ("from __future__ import annotations\n", "m.py:1: imports annotations from __future__"),
        ("from __future__ import division, annotations\n", "m.py:1: imports annotations from __future__"),
        (_CLEAN.replace('board: "Board"', "board: Board"), "m.py:10: `Board` is imported under TYPE_CHECKING only"),
        (_CLEAN.replace('-> "list[Board]"', "-> list[Board]"), "`Board` is imported under TYPE_CHECKING only"),
        (_CLEAN.replace('def inner(b: "Board")', "def inner(b: Board)"), "m.py:12: `Board` is imported under TYPE_CHECKING only"),
        (_CLEAN.replace('-> "Later"', "-> Later"), "m.py:17: `Later` is not defined yet"),
        (_CLEAN + "\n\ndef early(x: Laterer) -> None: ...\n\n\nclass Laterer: ...\n", "`Laterer` is not defined yet"),
        (_CLEAN + "\n\nclass Row:\n    owner: Board\n", "`Board` is imported under TYPE_CHECKING only"),
        (_CLEAN + "\n\ndef build() -> None:\n    class Local:\n        owner: Board\n", "`Board` is imported under TYPE_CHECKING only"),
    ],
)
def test_a_planted_unbound_annotation_is_reported(source: str, needle: str) -> None:
    findings = annotation_findings("m.py", source)
    assert any(needle in f for f in findings), findings
