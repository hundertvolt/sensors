"""Strips `if TYPE_CHECKING:` blocks and their try/except ImportError header out of a module's
source before it's frozen/mpy-cross-compiled - `mpy-cross` doesn't dead-code-eliminate these
(SPECIFICATION.md Part B.11), so they'd otherwise survive into the .mpy bytecode as dead weight."""

from __future__ import annotations

import ast


def _is_bare_type_checking_test(test: ast.expr) -> bool:
    """Matches only a bare `TYPE_CHECKING` or `mod.TYPE_CHECKING` test - never a compound
    condition (`if TYPE_CHECKING and x:`), which is left untouched rather than guessed at, per
    BACKLOG.md's original prototype note."""
    if isinstance(test, ast.Name):
        return bool(test.id == "TYPE_CHECKING")
    if isinstance(test, ast.Attribute):
        return bool(test.attr == "TYPE_CHECKING")
    return False


def _is_type_checking_import_guard(node: ast.Try) -> bool:
    """Matches exactly this codebase's `try: from typing import TYPE_CHECKING / except
    ImportError: TYPE_CHECKING = False` convention - never a general try/except guarding
    something else, which is left alone."""
    if node.orelse or node.finalbody or len(node.body) != 1 or len(node.handlers) != 1:
        return False
    (stmt,) = node.body
    if not (isinstance(stmt, ast.ImportFrom) and stmt.module == "typing"):
        return False
    if not any(alias.name == "TYPE_CHECKING" for alias in stmt.names):
        return False
    (handler,) = node.handlers
    if not (isinstance(handler.type, ast.Name) and handler.type.id == "ImportError"):
        return False
    if len(handler.body) != 1:
        return False
    (assign,) = handler.body
    return (
        isinstance(assign, ast.Assign)
        and len(assign.targets) == 1
        and isinstance(assign.targets[0], ast.Name)
        and assign.targets[0].id == "TYPE_CHECKING"
        and isinstance(assign.value, ast.Constant)
        and assign.value.value is False
    )


class _TypeCheckingStripper(ast.NodeTransformer):
    def __init__(self) -> None:
        self.removed_anything = False

    def visit_If(self, node: ast.If) -> ast.If | None:
        if not node.orelse and _is_bare_type_checking_test(node.test):
            self.removed_anything = True
            return None
        self.generic_visit(node)
        return node

    def visit_Try(self, node: ast.Try) -> ast.Try | None:
        if _is_type_checking_import_guard(node):
            self.removed_anything = True
            return None
        self.generic_visit(node)
        return node


def strip_type_checking_blocks(source: str) -> str:
    """Returns `source` with every bare `if TYPE_CHECKING:` block (no `elif`/`else`) and its
    try/except ImportError header removed, re-parsing the output to fail loudly on a bad
    transform. Source with no such blocks is returned byte-for-byte unchanged."""
    tree = ast.parse(source)
    stripper = _TypeCheckingStripper()
    stripped_tree = stripper.visit(tree)
    if not stripper.removed_anything:
        return source
    ast.fix_missing_locations(stripped_tree)
    output: str = ast.unparse(stripped_tree)
    ast.parse(output)  # validity check: raises SyntaxError if the transform produced garbage
    return output
