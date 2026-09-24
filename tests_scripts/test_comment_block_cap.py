"""CLAUDE.md's 3-line cap on every header and inline comment block, measured rather than swept by
hand. Python and shell only - JS/CSS keep their own syntax and stay review-enforced. The counting
convention this encodes is CLAUDE.md's; without it the same tree measures anywhere from 0 to 458."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCOPES = ("src", "buildgen", "digital_twin", "toolchain", "scripts", "tests", "tests_scripts", "tests_hardware")
CAP = 3

# Data, not commentary, so exempt - CLAUDE.md names the buildgen tags; PEP 723's inline script
# metadata is the same case, one machine-read line per field, read by `uv run` itself.
_TAGS = ("@web", "@web-group", "@wiring", "@value-wiring", "@limits", "@requires")
_PEP723 = re.compile(r"^#\s*(///|requires-python\s*=|dependencies\s*=)")
# Punctuation between paragraphs, not prose: a banner rule, a bare `#`, and a docstring's own lone
# delimiter line. Each is why a hand count and a naive line count disagree.
_DIVIDER = re.compile(r"^#\s*[-=~*#]{4,}\s*$")
_LONE_QUOTE = re.compile(r"^\s*(?:[rbfu]{1,2})?(\"\"\"|''')\s*$")


def _is_comment(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("#") and not stripped.startswith("#!")


def _is_punctuation(line: str) -> bool:
    stripped = line.strip()
    return stripped == "#" or bool(_DIVIDER.match(stripped)) or bool(_PEP723.match(stripped))


def _comment_blocks(lines: list[str]) -> list[tuple[int, int]]:
    """Over-cap runs of comment-ONLY lines. A trailing comment on a code line annotates that line,
    so it never starts a block - which is what keeps a column of annotated data entries from
    reading as one long block."""
    over: list[tuple[int, int]] = []
    run = start = 0
    for number, raw in enumerate(lines, 1):
        if _is_comment(raw) and _is_punctuation(raw):
            if run > CAP:
                over.append((start, run))
            run = 0
            continue
        if _is_comment(raw):
            if run == 0:
                start = number
            run += 1
            continue
        if run > CAP:
            over.append((start, run))
        run = 0
    if run > CAP:
        over.append((start, run))
    return [(s, n) for s, n in over if not any(tag in line for line in lines[s - 1 : s - 1 + n] for tag in _TAGS)]


def _docstrings(lines: list[str]) -> list[tuple[int, int]]:
    over: list[tuple[int, int]] = []
    for node in ast.walk(ast.parse("\n".join(lines))):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if ast.get_docstring(node, clean=False) is None:
            continue
        first = node.body[0]
        text = lines[first.lineno - 1 : (first.end_lineno or first.lineno)]
        while len(text) > 1 and _LONE_QUOTE.match(text[-1]):
            text = text[:-1]
        while len(text) > 1 and _LONE_QUOTE.match(text[0]):
            text = text[1:]
        if len(text) > CAP:
            over.append((first.lineno, len(text)))
    return over


def _findings(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    found = [(start, length, "comment") for start, length in _comment_blocks(lines)]
    if path.suffix == ".py":
        found += [(start, length, "docstring") for start, length in _docstrings(lines)]
    rel = path.relative_to(REPO_ROOT)
    return [f"{rel}:{start}: {length}-line {kind} block" for start, length, kind in sorted(found)]


def _sources() -> list[Path]:
    found: list[Path] = []
    for scope in SCOPES:
        for pattern in ("*.py", "*.sh", "**/*.py", "**/*.sh"):
            found.extend(p for p in (REPO_ROOT / scope).glob(pattern) if p.is_file())
    return sorted(set(found))


def test_the_scan_actually_reaches_every_scope_with_files_in_it() -> None:
    # Guards the detector: a glob that silently matched nothing would pass everything vacuously.
    by_scope = {scope: sum(1 for p in _sources() if p.is_relative_to(REPO_ROOT / scope)) for scope in SCOPES}
    assert all(count > 0 for count in by_scope.values()), by_scope
    assert sum(by_scope.values()) > 200, by_scope


@pytest.mark.parametrize("source", _sources(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_no_comment_or_docstring_block_exceeds_three_lines(source: Path) -> None:
    assert _findings(source) == [], f"CLAUDE.md caps every header and inline comment block at {CAP} lines: {_findings(source)}"


def test_a_block_of_four_prose_lines_is_caught() -> None:
    assert _comment_blocks(["# one", "# two", "# three", "# four", "x = 1"]) == [(1, 4)]


def test_three_lines_on_either_side_of_a_paragraph_break_are_two_blocks() -> None:
    # The convention that makes the difference between 0 and 458 findings on this tree.
    assert _comment_blocks(["# one", "# two", "# three", "#", "# four", "# five", "# six"]) == []


def test_a_banner_rule_and_pep_723_metadata_are_punctuation_not_prose() -> None:
    assert _comment_blocks(["# " + "-" * 8, "# one", "# two", "# three", "# " + "-" * 8]) == []
    assert _comment_blocks(["# /// script", "# requires-python = '>=3.11'", "# dependencies = []", "# ///"]) == []


def test_a_trailing_comment_does_not_start_a_block_but_its_continuation_lines_do() -> None:
    assert _comment_blocks(["x = 1  # a", "y = 2  # b", "z = 3  # c", "w = 4  # d"]) == []
    assert _comment_blocks(["x = 1  # a", "# b", "# c", "# d", "# e"]) == [(2, 4)]


def test_a_docstrings_lone_closing_delimiter_is_not_a_fourth_line() -> None:
    assert _docstrings(['"""one', "two", "three", '"""']) == []
    assert _docstrings(['"""one', "two", "three", "four", '"""']) == [(1, 4)]
