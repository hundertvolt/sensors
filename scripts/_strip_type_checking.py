"""Blanks `TYPE_CHECKING` blocks and their import guard in a staged copy, line for line (SPECIFICATION.md Part B.11)."""

import ast

_NAME = "TYPE_CHECKING"


class StripError(Exception):
    # A staged copy that would still read TYPE_CHECKING, or a source that does not parse: path and line named.
    pass


def _is_read(node: ast.AST) -> bool:
    # A load of the bare name or of `<module>.TYPE_CHECKING`.
    if isinstance(node, ast.Name):
        return node.id == _NAME and isinstance(node.ctx, ast.Load)
    if isinstance(node, ast.Attribute):
        return node.attr == _NAME and isinstance(node.ctx, ast.Load)
    return False


def _is_type_checking_import_guard(node: ast.Try) -> bool:
    # Exactly this codebase's `try: from typing import TYPE_CHECKING / except ImportError:
    # TYPE_CHECKING = False` convention - never a general try/except guarding something else.
    if node.orelse or node.finalbody or len(node.body) != 1 or len(node.handlers) != 1:
        return False
    (stmt,) = node.body
    if not (isinstance(stmt, ast.ImportFrom) and stmt.module == "typing"):
        return False
    if not any(alias.name == _NAME for alias in stmt.names):
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
        and assign.targets[0].id == _NAME
        and isinstance(assign.value, ast.Constant)
        and assign.value.value is False
    )


def _child_suites(node: ast.stmt) -> "list[list[ast.stmt]]":
    # Every statement list directly under a compound statement: bodies, else/finally and handler/case bodies.
    suites: list[list[ast.stmt]] = []
    for _field, value in ast.iter_fields(node):
        if isinstance(value, list) and value and isinstance(value[0], ast.stmt):
            suites.append(value)
        elif isinstance(value, list):
            suites.extend(item.body for item in value if isinstance(item, (ast.ExceptHandler, ast.match_case)))
    return suites


def _span(node: "ast.stmt | ast.expr") -> "range":
    return range(node.lineno, (node.end_lineno or node.lineno) + 1)


class _Plan:
    # The edits one source needs, read off its AST: whole lines blanked, the `pass` lines that keep an
    # emptied suite valid, and each remaining read's one-line span, which becomes False.
    def __init__(self, lines: "list[bytes]") -> None:
        self.lines = lines
        self.blank: set[int] = set()
        self.passes: dict[int, int] = {}

    def _removable(self, stmt: ast.stmt) -> bool:
        # A bare `if TYPE_CHECKING:` with no elif/else (and not itself an elif), or the import guard.
        if isinstance(stmt, ast.Try):
            return _is_type_checking_import_guard(stmt)
        if not (isinstance(stmt, ast.If) and not stmt.orelse and _is_read(stmt.test)):
            return False
        return not self.lines[stmt.lineno - 1][stmt.col_offset :].startswith(b"elif")

    def walk(self, suite: "list[ast.stmt]", *, needs_pass: bool) -> None:
        kept = 0
        for stmt in suite:
            if self._removable(stmt):
                self.blank.update(_span(stmt))
                continue
            kept += 1
            for child in _child_suites(stmt):
                self.walk(child, needs_pass=True)
        if needs_pass and not kept:
            self.passes[suite[0].lineno] = suite[0].col_offset

    def spans(self, reads: "list[ast.expr]") -> "list[tuple[int, int, int]]":
        # (line, start, end) byte columns of each read outside a blanked statement, outermost only; a read
        # spanning lines has no in-place form and is left for the re-parse check to refuse.
        spans = [(node.lineno, node.col_offset, node.end_col_offset or 0) for node in reads if node.lineno == node.end_lineno and node.lineno not in self.blank]
        return [s for s in spans if not any(o != s and o[0] == s[0] and o[1] <= s[1] and s[2] <= o[2] for o in spans)]


def _reads(tree: ast.Module) -> "list[ast.expr]":
    return [node for node in ast.walk(tree) if isinstance(node, ast.expr) and _is_read(node)]


def _edited(line: bytes, replacement: bytes) -> bytes:
    # The line's content replaced, its \r (a CRLF file) kept.
    return replacement + (b"\r" if line.endswith(b"\r") else b"")


def strip_type_checking_blocks(source: str, path: str = "<source>") -> str:
    # Every line keeps its number (comments included; mpy-cross drops them), so a field traceback's line
    # numbers equal the source's; the result depends only on the text, never on the host CPython.
    # Source with nothing to strip is returned unchanged.
    try:
        tree = ast.parse(source, path)
    except SyntaxError as e:
        raise StripError(f"{path}:{e.lineno}: {e.msg}") from e
    original = [line.encode("utf-8") for line in source.split("\n")]
    plan = _Plan(original)
    plan.walk(tree.body, needs_pass=False)
    reads = _reads(tree)
    if not plan.blank and not reads:
        return source
    lines = list(original)
    for number, start, end in sorted(plan.spans(reads), reverse=True):
        lines[number - 1] = lines[number - 1][:start] + b"False" + lines[number - 1][end:]
    for number in plan.blank:
        lines[number - 1] = _edited(original[number - 1], b"")
    for number, indent in plan.passes.items():
        lines[number - 1] = original[number - 1][:indent] + _edited(original[number - 1], b"pass")
    output = "\n".join(line.decode("utf-8") for line in lines)
    try:
        residue = sorted(node.lineno for node in _reads(ast.parse(output, path)))
    except SyntaxError as e:
        raise StripError(f"{path}:{e.lineno}: the stripped copy does not parse ({e.msg})") from e
    if residue:
        raise StripError(f"{path}:{residue[0]}: TYPE_CHECKING still read after stripping")
    return output
