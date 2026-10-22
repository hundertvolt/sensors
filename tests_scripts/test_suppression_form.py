"""Every suppression is coded, ordered and reasoned (SPECIFICATION.md D.6): no bare `type: ignore` or `noqa`, codes
ascending and ", "-separated, an inline `noqa: CODES - <reason>`, and in src/ no `noqa` at all and a reason beside or
directly above each `type: ignore[...]`. Comments are tokenised, so text inside a string never counts."""

import io
import re
import tokenize
from dataclasses import dataclass
from functools import cache

import pytest
from _repo_scan import REPO_ROOT, repo_files

_SCOPES = ("src/", "tests/", "digital_twin/", "buildgen/", "toolchain/", "scripts/", "tests_scripts/", "tests_hardware/")
# The directive spellings the tools themselves read: ruff's is case-insensitive, mypy's is not.
_NOQA = re.compile(r"#\s*noqa(?=$|[\s:])", re.IGNORECASE)
_TYPE_IGNORE = re.compile(r"#\s*type:\s*ignore(?=$|[\s\[])")
_NOQA_FORM = re.compile(r"# noqa: (?P<codes>[A-Z]+[0-9]+(?:, [A-Z]+[0-9]+)*) - \S")
_NOQA_CODES = re.compile(r"#\s*noqa\s*:\s*(?P<codes>[A-Z]+[0-9]+(?:[\s,]+[A-Z]+[0-9]+)*)", re.IGNORECASE)
_IGNORE_FORM = re.compile(r"# type: ignore\[(?P<codes>[a-z][a-z-]*(?:, [a-z][a-z-]*)*)\](?P<rest>.*)")
_IGNORE_CODES = re.compile(r"#\s*type:\s*ignore\[(?P<codes>[^\]]*)\]")


@dataclass(frozen=True)
class _Finding:
    rule: str
    where: str
    detail: str


@cache
def _all_findings() -> "tuple[_Finding, ...]":
    return tuple(f for path in _scoped_python_files() for f in _file_findings(path))


def _code_list_finding(where: str, kind: str, codes: str) -> "_Finding | None":
    listed = [c for c in re.split(r"[\s,]+", codes.strip()) if c]
    expected = ", ".join(sorted(listed))
    if codes.strip() != expected:
        return _Finding("order", where, f"{kind} codes {codes.strip()!r} - expected {expected!r} (ascending, comma-space separated)")
    return None


def _file_findings(path: str) -> "list[_Finding]":
    text = (REPO_ROOT / path).read_text(encoding="utf-8")
    lines = text.splitlines()
    found: list[_Finding] = []
    # A file the tokeniser cannot read raises here rather than reading as one with no suppression.
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type == tokenize.COMMENT:
            row = tok.start[0]
            found += _noqa_findings(path, row, tok.string)
            found += _ignore_findings(path, row, tok.string, lines[row - 2] if row >= 2 else "")
    return found


def _ignore_findings(path: str, row: int, comment: str, line_above: str) -> "list[_Finding]":
    where = f"{path}:{row}"
    found: list[_Finding] = []
    for match in _TYPE_IGNORE.finditer(comment):
        directive = comment[match.start() :]
        codes = _IGNORE_CODES.match(directive)
        if codes is None:
            found.append(_Finding("bare", where, f"{directive!r} names no error code - expected `# type: ignore[code]`"))
            continue
        if order := _code_list_finding(where, "type: ignore", codes.group("codes")):
            found.append(order)
        form = _IGNORE_FORM.match(directive)
        reasoned = (form is not None and re.match(r"\s+#\s*\S", form.group("rest")) is not None) or line_above.lstrip().startswith("#")
        if path.startswith("src/") and not reasoned:
            found.append(_Finding("src-reason", where, f"{directive!r} - src/ gives each its reason: a trailing `  # <reason>` or a comment line directly above"))
    return found


def _noqa_findings(path: str, row: int, comment: str) -> "list[_Finding]":
    where = f"{path}:{row}"
    found: list[_Finding] = []
    for match in _NOQA.finditer(comment):
        directive = comment[match.start() :]
        if path.startswith("src/"):
            found.append(_Finding("src-noqa", where, f"{directive!r} - src/ takes no inline noqa; its exemption lives in pyproject.toml"))
        codes = _NOQA_CODES.match(directive)
        if codes is None:
            found.append(_Finding("bare", where, f"{directive!r} names no code - expected `# noqa: CODE - <reason>`"))
            continue
        if order := _code_list_finding(where, "noqa", codes.group("codes")):
            found.append(order)
        if _NOQA_FORM.match(directive) is None:
            found.append(_Finding("reason", where, f"{directive!r} - expected `# noqa: CODES - <why the code stays>`"))
    return found


def _of(rule: str) -> "list[str]":
    return [f"{f.where}: {f.detail}" for f in _all_findings() if f.rule == rule]


def _scoped_python_files() -> list[str]:
    return [p for p in repo_files() if p.endswith(".py") and p.startswith(_SCOPES)]


def test_the_scan_reads_every_scope_and_finds_both_directive_kinds() -> None:
    files = _scoped_python_files()
    assert {scope for scope in _SCOPES if any(p.startswith(scope) for p in files)} == set(_SCOPES), "a lint scope lists no tracked .py file"
    comments = [tok.string for path in ("tests/test_asy_uart_comm.py", "scripts/build_firmware.py") for tok in tokenize.generate_tokens(io.StringIO((REPO_ROOT / path).read_text(encoding="utf-8")).readline) if tok.type == tokenize.COMMENT]
    assert any(_TYPE_IGNORE.search(c) for c in comments), "no type: ignore found where one is known to sit - the reader misses them"
    assert any(_NOQA.search(c) for c in comments), "no noqa found where one is known to sit - the reader misses them"


@pytest.mark.parametrize(
    ("comment", "rules"),
    [
        ("# noqa", {"bare"}),
        ("# noqa: E402", {"reason"}),
        ("# noqa: S607, S603 - argv from constants", {"order"}),
        ("# noqa: S603,S607 - argv from constants", {"order", "reason"}),
        ("# noqa: E402 - the sys.path line above makes it importable", set()),
        ("# type: ignore", {"bare"}),
        ("# type: ignore[method-assign, assignment]", {"order"}),
        ("# type: ignore[assignment,arg-type]  # a test double", {"order"}),
        ("# type: ignore[arg-type, assignment]", set()),
        ("# a comment only, mentioning noqa and type ignore in prose", set()),
    ],
)
def test_the_rules_read_each_spelling_as_the_tools_do(comment: str, rules: "set[str]") -> None:
    found = {f.rule for f in _noqa_findings("tests/x.py", 1, comment) + _ignore_findings("tests/x.py", 1, comment, "")}
    assert found == rules


@pytest.mark.parametrize(
    ("comment", "line_above", "rules"),
    [
        ("# noqa: E402 - the reason", "", {"src-noqa"}),
        ("# type: ignore[misc]", "    x = 1", {"src-reason"}),
        ("# type: ignore[misc]", "    # why the stub disagrees", set()),
        ("# type: ignore[misc]  # why the stub disagrees", "", set()),
    ],
)
def test_src_takes_no_noqa_and_a_reason_for_each_type_ignore(comment: str, line_above: str, rules: "set[str]") -> None:
    found = {f.rule for f in _noqa_findings("src/x.py", 2, comment) + _ignore_findings("src/x.py", 2, comment, line_above)}
    assert found == rules


def test_no_suppression_is_bare() -> None:
    assert not _of("bare"), "\n".join(_of("bare"))


def test_every_code_list_is_ascending_and_comma_space_separated() -> None:
    assert not _of("order"), "\n".join(_of("order"))


def test_every_inline_noqa_states_its_reason() -> None:
    assert not _of("reason"), "\n".join(_of("reason"))


def test_src_carries_no_noqa() -> None:
    assert not _of("src-noqa"), "\n".join(_of("src-noqa"))


def test_every_src_type_ignore_states_its_reason_beside_or_directly_above() -> None:
    assert not _of("src-reason"), "\n".join(_of("src-reason"))
