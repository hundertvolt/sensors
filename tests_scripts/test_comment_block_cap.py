"""CLAUDE.md's 3-line cap on every header and inline comment block, measured rather than swept by hand, and every file's
header present. Python and shell blocks are counted (the generated device modules too); JS, CSS, HTML and config files
are checked for a header, their content cap review-enforced (_REVIEW_ENFORCED). This file defines CLAUDE.md's counting."""

import ast
import io
import json
import math
import re
import subprocess
import sys
import tokenize
from collections.abc import Iterator
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES
from _repo_scan import REPO_ROOT, is_shared_excluded, repo_files

SCOPES = ("src", "buildgen", "digital_twin", "toolchain", "scripts", "tests", "tests_scripts", "tests_hardware")
CAP = 3
# Once set, a line counts ceil(len / _WRAP_WIDTH) lines (110, the hand-wrap width), so a paragraph packed onto one long
# line counts by its length; off, every line counts one (agent, 2026-10-15). The one switch for the length rule.
_WRAP_WIDTH: int | None = None

# Data, not commentary: a tag line leaves the count, its block's other lines count. CLAUDE.md names the buildgen tags;
# the last is the tunable register's (tests_scripts/test_tunables_register.py). The list grows only on the owner's word.
_TAGS = ("web", "web-group", "wiring", "value-wiring", "limits", "requires", "tunable")
_TAG_LINE = re.compile(r"^#+\s*@(?:" + "|".join(re.escape(tag) for tag in _TAGS) + r")(?:\s|$)")
# PEP 723 inline script metadata is uv's input: punctuation only between its own opening and closing lines.
_PEP723_OPEN, _PEP723_CLOSE = "# /// script", "# ///"
# Punctuation between paragraphs: a bare `#`, a `# ----` rule and a docstring's lone delimiter line. A rule of any other
# character is prose, and no comment line is one (CLAUDE.md: section dividers take the one `-` form).
_DIVIDER = re.compile(r"^#\s*-{4,}\s*$")
_OTHER_RULE = re.compile(r"^#\s*[=~*#]{4,}\s*$")
_LONE_QUOTE = re.compile(r"^\s*(?:[rbfu]{1,2})?(\"\"\"|''')\s*$")

# Header presence beyond Python and shell: a leading comment, after a shebang where there is one.
_SLASH_HEADED = (".js", ".mjs", ".ts", ".css")
_HASH_HEADED = (".yml", ".toml", ".ini")
_PAGE = "html/index.html"  # its header is an HTML comment directly after the doctype
# Config files whose header is still to be written; a row goes once its file has one (the pending test fails on it).
_HEADER_PENDING: frozenset[str] = frozenset()
_COUNTED = (".py", ".sh")
# The generator runs in a child interpreter: its caches (every src/ module's tree) never join this heap, where each
# collection the per-file parses set off would walk them again. It prints {path: source} for every device it is given.
_GENERATE = """import json, sys
from pathlib import Path
from buildgen.generate import generate_device
root, out = Path.cwd(), {}
for device in sys.argv[1:]:
    built = generate_device(root / "devices" / f"{device}.toml", root / "src", root / "ext")
    for suffix, source in (("", built.module_source), ("_main", built.boot_entry_source), ("_main_noautostart", built.boot_entry_noautostart_source)):
        out[f"build/generated_src/sensortask_{device}{suffix}.py"] = source
print(json.dumps(out))
"""
_PARSER_NEEDED = "the content cap needs a parser for this syntax (JSDoc tags are data, not prose); the header is checked"
# Every other tracked kind, with what stays review-enforced and why; a kind on neither list fails the kinds test.
_REVIEW_ENFORCED = {
    ".js": _PARSER_NEEDED,
    ".mjs": _PARSER_NEEDED,
    ".ts": _PARSER_NEEDED,
    ".css": _PARSER_NEEDED,
    ".html": "the page's inline comments; its header is checked, the cap counted on it",
    ".yml": "config: the content cap until a parser lands (CLAUDE.md); the header is checked",
    ".toml": "config: the content cap until a parser lands (CLAUDE.md); the header is checked",
    ".ini": "config: the content cap until a parser lands (CLAUDE.md); the header is checked",
    ".json": "JSON has no comments; the JSONC tsconfig files' headers until a parser lands",
    ".pyi": "type-check-only stubs mypy reads and nothing runs: their leading # header and its cap",
    ".md": "documentation: prose throughout, no header block",
    ".txt": "data: the allow-lists their checks read",
    ".ico": "binary",
    ".nvmrc": "one version string the Node tooling reads",
    ".gitignore": "ignore patterns: their comments",
    ".gitmodules": "the submodule's path and URL as git writes them: their comments",
    "LICENSE": "license text, verbatim",
}


def _block_weight(line: str) -> int:
    return 1 if _WRAP_WIDTH is None else max(1, math.ceil(len(line.strip()) / _WRAP_WIDTH))


def _comment_blocks(lines: list[str]) -> list[tuple[int, int]]:
    # Over-cap runs of comment-ONLY lines. A trailing comment on a code line annotates that line, so it never starts
    # a block - which keeps a column of annotated data entries from reading as one long block.
    over: list[tuple[int, int]] = []
    run = start = 0
    in_pep723 = False
    for number, raw in enumerate(lines, 1):
        stripped = raw.strip()
        if not _is_comment(stripped):
            if run > CAP:
                over.append((start, run))
            run = 0
            continue
        if stripped == _PEP723_OPEN or in_pep723:
            in_pep723 = stripped != _PEP723_CLOSE
        elif _TAG_LINE.match(stripped):
            continue  # neither counts nor ends the block
        elif not _is_punctuation(stripped):
            start = number if run == 0 else start
            run += _block_weight(stripped)
            continue
        if run > CAP:
            over.append((start, run))
        run = 0
    if run > CAP:
        over.append((start, run))
    return over


def _docstrings(lines: list[str]) -> list[tuple[int, int]]:
    over: list[tuple[int, int]] = []
    tree = ast.parse("\n".join(lines))
    for node in [tree, *_statements(tree)]:
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
        # A blank line separates a docstring's paragraphs, the way a bare `#` does a comment's.
        run = 0
        for line in [*text, ""]:
            if line.strip():
                run += _block_weight(line)
                continue
            if run > CAP:
                over.append((first.lineno, run))
                break
            run = 0
    return over


def _findings(rel: str, text: str) -> list[str]:
    lines = text.splitlines()
    found = [(start, length, "comment") for start, length in _comment_blocks(lines)]
    if rel.endswith(".py"):
        found += [(start, length, "docstring") for start, length in _docstrings(lines)]
    return [f"{rel}:{start}: {length}-line {kind} block" for start, length, kind in sorted(found)]


def _generated() -> dict[str, str]:
    # Every device's three generated modules, built in memory: the tests_scripts tier never reads build/generated_src/.
    done = subprocess.run([sys.executable, "-c", _GENERATE, *DEVICE_NAMES], cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr
    modules: dict[str, str] = json.loads(done.stdout)
    return modules


def _has_header(rel: str, text: str) -> bool:
    # A module docstring for Python (a file with no statement has nothing to head), else the file's first comment.
    if rel.endswith(".py"):
        return _opens_with_docstring(text)
    lines = text.splitlines()
    if rel == _PAGE:
        return len(lines) > 1 and lines[0].strip().lower() == "<!doctype html>" and lines[1].strip().startswith("<!--")
    body = lines[1:] if lines and lines[0].startswith("#!") else lines
    first = body[0].strip() if body else ""
    return first.startswith(("/*", "//")) if rel.endswith(_SLASH_HEADED) else first.startswith(("#", ";")) and not first.startswith("#!")


def _headed_files() -> list[str]:
    # The tracked files outside the counted scopes whose header this gate checks: JS, CSS, the page and the config.
    return [p for p in repo_files() if not is_shared_excluded(p) and (p.endswith(_SLASH_HEADED + _HASH_HEADED) or p == _PAGE)]


def _is_comment(stripped: str) -> bool:
    return stripped.startswith("#") and not stripped.startswith("#!")


def _is_punctuation(stripped: str) -> bool:
    return stripped == "#" or bool(_DIVIDER.match(stripped))


def _kind(rel: str) -> str:
    name = Path(rel).name
    return "LICENSE" if name.startswith("LICENSE") else Path(rel).suffix or name


def _opens_with_docstring(text: str) -> bool:
    # ast.get_docstring()'s test - the first statement a lone str literal - read from the first tokens alone, since a
    # second parse of every file would double the gate's cost. No statement at all also passes: nothing to head.
    tokens = (t for t in tokenize.generate_tokens(io.StringIO(text).readline) if t.type not in (tokenize.COMMENT, tokenize.NL))
    first = next(tokens)
    if first.type == tokenize.ENDMARKER:
        return True
    if first.type != tokenize.STRING or first.string.lstrip("rRuU")[:1] not in ("'", '"'):
        return False  # code, or a bytes or f-string, which is no docstring
    after = next(tokens)
    return after.type in (tokenize.NEWLINE, tokenize.ENDMARKER) or after.string == ";"


def _page_header_lines(text: str) -> int:
    # The prose lines of the page's leading <!-- ... --> comment, its delimiters left out where they stand alone.
    lines = text.splitlines()[1:]
    end = next(i for i, line in enumerate(lines) if "-->" in line)
    return sum(1 for line in lines[: end + 1] if line.strip() not in ("<!--", "-->"))


def _statements(node: ast.AST) -> Iterator[ast.stmt]:
    # Every statement under node: a docstring's owner is one, so no expression node needs visiting.
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.stmt):
            yield child
            yield from _statements(child)


def _sources() -> list[Path]:
    found: list[Path] = []
    for scope in SCOPES:
        for pattern in ("*.py", "*.sh", "**/*.py", "**/*.sh"):
            found.extend(p for p in (REPO_ROOT / scope).glob(pattern) if p.is_file())
    return sorted(set(found))


@pytest.fixture(scope="module")
def generated() -> dict[str, str]:
    return _generated()


def test_the_scan_actually_reaches_every_scope_with_files_in_it(generated: dict[str, str]) -> None:
    # Guards each detector: a glob or listing that silently matched nothing would pass everything vacuously.
    sources = _sources()
    by_scope = {scope: sum(1 for p in sources if p.is_relative_to(REPO_ROOT / scope)) for scope in SCOPES}
    headed = _headed_files()
    by_scope |= {top: sum(1 for p in headed if p.startswith(top + "/")) for top in ("js", "tests_js", "html")}
    by_scope |= {"build/generated_src": len(generated), "config": sum(1 for p in headed if p.endswith(_HASH_HEADED))}
    assert all(count > 0 for count in by_scope.values()), by_scope
    assert sum(by_scope.values()) > 200, by_scope
    assert len(generated) == 3 * len(DEVICE_NAMES) > 0, sorted(generated)


@pytest.mark.parametrize("source", _sources(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_no_comment_or_docstring_block_exceeds_three_lines(source: Path) -> None:
    found = _findings(str(source.relative_to(REPO_ROOT)), source.read_text(encoding="utf-8"))
    assert found == [], f"CLAUDE.md caps every header and inline comment block at {CAP} lines: {found}"


def test_every_generated_module_keeps_the_cap_and_opens_with_a_header(generated: dict[str, str]) -> None:
    found = [line for rel, text in generated.items() for line in _findings(rel, text)]
    found += [f"{rel}: no module docstring" for rel, text in generated.items() if not _has_header(rel, text)]
    assert found == [], found


def test_every_python_and_shell_file_opens_with_a_header() -> None:
    sources = _sources()
    assert sources, "the scan found no Python or shell file"
    found = [str(p.relative_to(REPO_ROOT)) for p in sources if not _has_header(str(p.relative_to(REPO_ROOT)), p.read_text(encoding="utf-8"))]
    assert found == [], f"CLAUDE.md: every module opens with one header block (a docstring in Python, a comment after the shebang in shell): {found}"


def test_every_js_css_page_and_config_file_opens_with_a_header() -> None:
    headed = _headed_files()
    assert headed, "the listing found no JS, CSS, page or config file"
    found = [p for p in headed if p not in _HEADER_PENDING and not _has_header(p, (REPO_ROOT / p).read_text(encoding="utf-8"))]
    assert found == [], f"CLAUDE.md: every file opens with one header block (a leading comment): {found}"


def test_the_page_header_follows_the_doctype_within_the_cap() -> None:
    text = (REPO_ROOT / _PAGE).read_text(encoding="utf-8")
    assert _has_header(_PAGE, text), f"{_PAGE}: no <!-- ... --> header directly after the doctype"
    assert _page_header_lines(text) <= CAP, f"{_PAGE}: a {_page_header_lines(text)}-line header"


def test_each_pending_header_is_still_missing() -> None:
    # The pending set only shrinks: a file that has gained its header leaves it.
    gained = sorted(p for p in _HEADER_PENDING if _has_header(p, (REPO_ROOT / p).read_text(encoding="utf-8")))
    assert gained == [], f"these now open with a header - delete their _HEADER_PENDING rows: {gained}"


def test_no_comment_line_is_a_rule_of_any_character_but_dashes(generated: dict[str, str]) -> None:
    texts = {str(p.relative_to(REPO_ROOT)): p.read_text(encoding="utf-8") for p in _sources()} | generated
    assert texts, "the scan found no file"
    found = [f"{rel}:{n}" for rel, text in texts.items() for n, line in enumerate(text.splitlines(), 1) if _OTHER_RULE.match(line.strip())]
    assert found == [], f"a section divider is a `# ----` rule (CLAUDE.md): {found}"


def test_every_tracked_kind_is_counted_or_review_enforced() -> None:
    tracked = [p for p in repo_files() if not is_shared_excluded(p)]
    assert tracked, "the listing found no tracked file"
    unlisted = sorted({_kind(p) for p in tracked} - set(_COUNTED) - set(_REVIEW_ENFORCED))
    assert unlisted == [], f"a tracked kind this gate neither counts nor names in _REVIEW_ENFORCED with its reason: {unlisted}"
    outside = sorted(p for p in tracked if p.endswith(_COUNTED) and p.split("/", 1)[0] not in SCOPES)
    assert outside == [], f"Python or shell outside the counted scopes: {outside}"


def test_a_block_of_four_prose_lines_is_caught() -> None:
    assert _comment_blocks(["# one", "# two", "# three", "# four", "x = 1"]) == [(1, 4)]


def test_three_lines_on_either_side_of_a_paragraph_break_are_two_blocks() -> None:
    # The convention that makes the difference between 0 and 458 findings on this tree.
    assert _comment_blocks(["# one", "# two", "# three", "#", "# four", "# five", "# six"]) == []


def test_a_dash_rule_and_pep_723_metadata_inside_its_block_are_punctuation() -> None:
    assert _comment_blocks(["# " + "-" * 8, "# one", "# two", "# three", "# " + "-" * 8]) == []
    assert _comment_blocks(["# /// script", "# requires-python = '>=3.11'", "# dependencies = []", "# ///", "# one", "# two", "# three"]) == []


def test_pep_723_keys_outside_their_block_are_prose() -> None:
    assert _comment_blocks(["# requires-python = '>=3.11'", "# dependencies = []", "# one", "# two"]) == [(1, 4)]


def test_a_rule_of_another_character_is_prose() -> None:
    for rule in ("# " + "=" * 8, "# " + "~" * 8, "# " + "*" * 8, "#" * 9):
        assert _comment_blocks([rule, "# one", "# two", "# three"]) == [(1, 4)], rule
        assert _OTHER_RULE.match(rule), rule
    assert not _OTHER_RULE.match("# " + "-" * 8)


def test_a_tag_line_leaves_the_count_and_its_block_still_counts() -> None:
    assert _comment_blocks(["# one", "# @requires bus.timeout>=200000", "# two", "# three", "# @wiring a b", "# four"]) == [(1, 4)]
    assert _comment_blocks(["# one", "# @web A section=x", "# @web-group B", "# two", "# three"]) == []
    assert _comment_blocks(["# a prose line naming @requires mid-sentence", "# two", "# three", "# four"]) == [(1, 4)]


def test_a_long_line_counts_by_its_length_once_the_wrap_width_is_set(monkeypatch: pytest.MonkeyPatch) -> None:
    long_line = "# " + "x" * 228  # 230 characters: three lines at 110
    assert _comment_blocks([long_line, "# two"]) == []
    monkeypatch.setitem(globals(), "_WRAP_WIDTH", 110)
    assert _comment_blocks([long_line, "# two"]) == [(1, 4)]
    assert _docstrings(['"""' + "y" * 400 + '"""']) == [(1, 4)]  # 406 characters: four lines


def test_a_trailing_comment_does_not_start_a_block_but_its_continuation_lines_do() -> None:
    assert _comment_blocks(["x = 1  # a", "y = 2  # b", "z = 3  # c", "w = 4  # d"]) == []
    assert _comment_blocks(["x = 1  # a", "# b", "# c", "# d", "# e"]) == [(2, 4)]


def test_a_docstrings_lone_closing_delimiter_is_not_a_fourth_line() -> None:
    assert _docstrings(['"""one', "two", "three", '"""']) == []
    assert _docstrings(['"""one', "two", "three", "four", '"""']) == [(1, 4)]


def test_a_blank_line_inside_a_docstring_separates_two_paragraphs() -> None:
    # CLAUDE.md's stated convention; without this the guard would be stricter than the rule it pins.
    assert _docstrings(['"""one', "two", "three", "", "four", "five", "six", '"""']) == []
    assert _docstrings(['"""one', "", "two", "three", "four", "five", '"""']) == [(1, 4)]


def test_each_kind_of_header_is_recognised() -> None:
    assert _has_header("a.py", '"""Head."""\nx = 1\n') and _has_header("a.py", "") and not _has_header("a.py", "# Head.\nx = 1\n")
    assert _has_header("a.py", '# coding note\nr"""Head."""\n') and _has_header("a.py", "# only a comment\n")
    for no_docstring in ('b"""Bytes."""\n', 'f"""F {x}."""\n', '"""Head.""" + x\n', "import os\n"):
        assert not _has_header("a.py", no_docstring), no_docstring
        assert ast.get_docstring(ast.parse(no_docstring)) is None, no_docstring  # the definition the token read follows
    assert _has_header("a.sh", "#!/bin/bash\n# Head.\nset -e\n") and not _has_header("a.sh", "#!/bin/bash\nset -e\n")
    assert _has_header("a.js", "// Head.\nexport {};\n") and _has_header("a.mjs", "#!/usr/bin/env node\n/** Head. */\n")
    assert not _has_header("a.js", "import x from 'y';\n") and not _has_header("a.css", "body {}\n")
    assert _has_header("a.toml", "# Head.\n[x]\n") and not _has_header("a.yml", "name: x\n")
    assert _has_header(_PAGE, "<!DOCTYPE html>\n<!-- Head. -->\n<html>\n") and not _has_header(_PAGE, "<!DOCTYPE html>\n<html>\n")
