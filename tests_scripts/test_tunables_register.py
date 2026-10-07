"""Pins every tuned value's tag to its SPECIFICATION.md Part N row: a malformed or near-miss tag, a
tag whose literal is not on the line below it, a tag without a row and a row without its tags all
fail, as do the watchdog, supervisor and page-load relations between the registered values (N.2)."""

import os
import re
from dataclasses import dataclass
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES, device_toml

from buildgen.errors import BuildError
from buildgen.tag_comments import _levenshtein, _max_typo_distance, iter_comment_tokens
from buildgen.validate import device_max_connections

_SCAN_DIRS = ("src", "buildgen", "digital_twin", "tests", "tests_scripts", "tests_hardware", "scripts", "toolchain", "js", "tests_js", "devices", ".github")
_SCAN_FILES = ("vitest.config.js",)
_SKIP_DIRS = frozenset({"__pycache__", "_tmp", "node_modules", ".pytest_cache", ".mypy_cache"})
_HASH_SUFFIXES = frozenset({".sh", ".yml", ".yaml", ".toml"})
_SLASH_SUFFIXES = frozenset({".js", ".mjs"})
# Comment-bearing types this check has no reader for: a tag in one would be skipped without a word.
_UNREAD_SUFFIXES = frozenset({".ini", ".cfg", ".ts", ".cjs"})

_NAME = "tunable"
_ID = r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*"
_TAG_RE = re.compile(rf"^@{_NAME} (?P<id>{_ID}) = (?P<literal>\S+)$")
_ID_RE = re.compile(rf"^{_ID}$")
_SIGIL_WORD_RE = re.compile(r"@([A-Za-z][\w-]*)")
_BEGIN, _END = "<!-- tunables:begin -->", "<!-- tunables:end -->"
_COLUMNS = ("id", "value", "sites", "dependants", "basis", "margin", "re-check trigger")
_EMPTY_CELLS = frozenset({"", "-", "\u2014", "\u2013"})  # empty, or a hyphen, em or en dash
_SITE_RE = re.compile(r"^(?P<path>[\w.][\w./-]*?)(?::[\d, -]+)?\s+[\u2014\u2013]\s+(?P<literal>\S+)")

# rp2's WDT refuses a longer timeout: ports/rp2/machine_wdt.c:32-38 (v1.29.0), a platform fact.
_RP2_WDT_MAX_MS = 8388
# "<<" in system_service.py, read as a factor of at least four (agent, 2026-09-29): the ratio the
# shipped values meet exactly; the real margin is the supervisor-scan budget in wdt.timeout_ms's row.
_TASK_CHECK_FACTOR = 4


@dataclass(frozen=True)
class Tag:
    path: str
    line: int
    id: str
    literal: str


@dataclass(frozen=True)
class Row:
    id: str
    kind: str
    cells: "dict[str, str]"
    line: int


def _comments(path: Path, lines: "list[str]") -> "list[tuple[int, str, bool]]":
    """Every comment as (line, text without its marker, whether the comment has its line to itself)."""
    if path.suffix == ".py":
        try:
            tokens = iter_comment_tokens(path, "tunables", str(path))
        except BuildError as e:
            raise AssertionError(str(e)) from e
        return [(t.lineno, t.text[1:].strip(), not lines[t.lineno - 1][: t.col].strip()) for t in tokens]
    marker = "#" if path.suffix in _HASH_SUFFIXES else "//"
    found: list[tuple[int, str, bool]] = []
    for number, raw in enumerate(lines, 1):
        stripped = raw.strip()
        if stripped.startswith(marker):
            found.append((number, stripped[len(marker) :].strip(), True))
            continue
        # A trailing comment counts only when it opens with a sigil: a marker inside a string or a
        # URL then never reads as a comment, while a tag placed after code still gets reported.
        at = max(raw.find(f"{marker} @"), raw.find(f"{marker}@"))
        if at != -1:
            found.append((number, raw[at + len(marker) :].strip(), False))
    return found


def _is_comment_line(path: Path, line: str) -> bool:
    return line.strip().startswith("#" if path.suffix in _HASH_SUFFIXES | {".py"} else "//")


def _near_miss(word: str) -> bool:
    return _levenshtein(word.lower(), _NAME) <= _max_typo_distance(_NAME)


def _scan_file(root: Path, path: Path, tags: "list[Tag]", problems: "list[str]") -> None:
    # Split on newlines only, as the tokenizer does: splitlines() also breaks on \x0c and friends.
    lines = path.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
    rel = path.relative_to(root).as_posix()
    for number, text, own_line in _comments(path, lines):
        words = [w for w in _SIGIL_WORD_RE.findall(text) if _near_miss(w)]
        if not words:
            continue
        where = f"{rel}:{number}"
        match = _TAG_RE.match(text)
        if match is None or words != [_NAME]:
            problems.append(f"{where}: malformed or near-miss tag (grammar: @{_NAME} <area>.<name> = <literal>): {text!r}")
            continue
        if not own_line:
            problems.append(f"{where}: a @{_NAME} tag sits on its own comment line above its literal, never after code: {text!r}")
            continue
        literal = match["literal"]
        following = next((ln for ln in lines[number:] if not _is_comment_line(path, ln)), "")
        if not re.search(rf"(?<![\w.]){re.escape(literal)}(?![\w.])", following):
            problems.append(f"{where}: {match['id']} = {literal}, but the next non-comment line does not carry {literal} as a whole token: {following.strip()!r}")
            continue
        tags.append(Tag(rel, number, match["id"], literal))


def collect_tags(root: Path) -> "tuple[list[Tag], list[str]]":
    """Every tag under the scanned scopes, plus every malformed, misplaced or literal-less one."""
    files = [root / name for name in _SCAN_FILES if (root / name).is_file()]
    for scope in _SCAN_DIRS:
        for directory, subdirs, names in os.walk(root / scope):
            subdirs[:] = sorted(d for d in subdirs if d not in _SKIP_DIRS)
            files += [Path(directory) / n for n in sorted(names) if Path(n).suffix in _HASH_SUFFIXES | _SLASH_SUFFIXES | _UNREAD_SUFFIXES | {".py"}]
    tags: list[Tag] = []
    problems: list[str] = []
    unread = [f for f in files if f.suffix in _UNREAD_SUFFIXES]
    problems += [f"{f.relative_to(root).as_posix()}: holds a @{_NAME} tag in a file type this check cannot read" for f in unread if f"@{_NAME}" in f.read_text(encoding="utf-8")]
    files = [f for f in files if f.suffix not in _UNREAD_SUFFIXES]
    for path in files:
        _scan_file(root, path, tags, problems)
    return tags, problems


def _cells(line: str) -> "list[str]":
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def parse_register(spec_text: str) -> "tuple[list[Row], list[str]]":
    """Part N's rows. A table under an N.4 heading, or one with a "Checked by" or rule-valued Kind
    column, holds rule rows; every other table between the markers holds tuned rows."""
    if spec_text.count(_BEGIN) != 1 or spec_text.count(_END) != 1 or spec_text.index(_BEGIN) > spec_text.index(_END):
        return [], [f"SPECIFICATION.md must hold Part N's register exactly once between {_BEGIN} and {_END}"]
    start = spec_text[: spec_text.index(_BEGIN)].count("\n") + 1
    body = spec_text[spec_text.index(_BEGIN) : spec_text.index(_END)].splitlines()
    rows: list[Row] = []
    problems: list[str] = []
    heading = ""
    header: list[str] | None = None
    for offset, raw in enumerate(body):
        line = raw.strip()
        if line.startswith("#"):
            heading, header = line, None
            continue
        if not line.startswith("|"):
            header = None
            continue
        cells = _cells(line)
        if header is None:
            header = [re.sub(r"\s*\(.*\)$", "", c).lower() for c in cells]
            continue
        if all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
            continue
        named = dict(zip(header, cells, strict=False))
        row_id = named.get("id", "").strip("`")
        kind_cell = named.get("kind", "").strip("`").lower()
        kind = "rule" if kind_cell == "rule" or "checked by" in header or "N.4" in heading else "tuned"
        if not _ID_RE.match(row_id):
            problems.append(f"SPECIFICATION.md:{start + offset}: row ID {row_id!r} does not match <area>.<name>")
            continue
        rows.append(Row(row_id, kind, named, start + offset))
    return rows, problems


def _sites(cell: str) -> "tuple[set[tuple[str, str]], list[str]]":
    sites: set[tuple[str, str]] = set()
    bad: list[str] = []
    for part in re.split(r";|<br\s*/?>", cell.replace("`", "")):
        if not part.strip():
            continue
        match = _SITE_RE.match(part.strip())
        if match is None:
            bad.append(part.strip())
            continue
        sites.add((match["path"], match["literal"].rstrip(",;)")))
    return sites, bad


def check_register(tags: "list[Tag]", rows: "list[Row]") -> "list[str]":
    """Tags and rows agree both ways, and every row carries what N.1 requires of it."""
    problems: list[str] = []
    by_id: dict[str, Row] = {}
    for row in rows:
        if row.id in by_id:
            problems.append(f"SPECIFICATION.md:{row.line}: {row.id} has a second row (first at line {by_id[row.id].line})")
        by_id.setdefault(row.id, row)
    tagged: dict[str, set[tuple[str, str]]] = {}
    for tag in tags:
        tagged.setdefault(tag.id, set()).add((tag.path, tag.literal))
        if tag.id not in by_id:
            problems.append(f"{tag.path}:{tag.line}: {tag.id} is tagged but has no SPECIFICATION.md Part N row")
    for row in by_id.values():
        where = f"SPECIFICATION.md:{row.line}: {row.id}"
        problems += [f"{where} has an empty {c.capitalize()}" for c in ("basis", "margin", "re-check trigger") if row.cells.get(c, "x") in _EMPTY_CELLS]
        basis = row.cells.get("basis", "")
        if basis.lower().startswith("estimated") and "measurement owed" not in basis.lower():
            problems.append(f'{where}: an estimated Basis names the measurement owed ("measurement owed: <how, level>")')
        if row.kind == "rule":
            if row.id in tagged:
                problems.append(f"{where} is a rule row, yet tagged at {sorted(tagged[row.id])} - a rule has no single code site")
            if not any("checked by" in k or "checked by" in v.lower() for k, v in row.cells.items() if v not in _EMPTY_CELLS):
                problems.append(f'{where} is a rule row naming no checking test or review ("Checked by ...")')
            continue
        missing = [c for c in _COLUMNS if c not in row.cells]
        if missing:
            problems.append(f"{where}: its table lacks the column(s) {missing}")
            continue
        listed, bad = _sites(row.cells["sites"])
        problems += [f"{where}: Sites entry {b!r} is not '<file> — <literal>'" for b in bad]
        found = tagged.get(row.id, set())
        if not found:
            problems.append(f"{where} is a tuned row, but no file carries its @{_NAME} tag")
        elif listed != found:
            problems.append(f"{where}: Sites list {sorted(listed)}, the tags say {sorted(found)}")
    return problems


def check_tree(root: Path) -> "list[str]":
    tags, problems = collect_tags(root)
    rows, register_problems = parse_register((root / "SPECIFICATION.md").read_text(encoding="utf-8"))
    return problems + register_problems + check_register(tags, rows)


@pytest.fixture(scope="module")
def real_tags(repo_root: Path) -> "list[Tag]":
    tags, problems = collect_tags(repo_root)
    assert not problems, "\n".join(problems)
    return tags


def _values(tags: "list[Tag]", tunable_id: str) -> "list[float]":
    literals = sorted({t.literal for t in tags if t.id == tunable_id})
    assert literals, f"{tunable_id} is tagged nowhere, so its relation cannot be checked"
    try:
        return [float(v) for v in literals]
    except ValueError as e:
        raise AssertionError(f"{tunable_id}'s literals {literals} are not numbers") from e


def test_every_tag_is_well_formed_and_sits_above_its_literal(repo_root: Path) -> None:
    _, problems = collect_tags(repo_root)
    assert not problems, "\n".join(problems)


def test_the_tags_and_the_part_n_rows_agree(repo_root: Path, real_tags: "list[Tag]") -> None:
    rows, problems = parse_register((repo_root / "SPECIFICATION.md").read_text(encoding="utf-8"))
    problems += check_register(real_tags, rows)
    assert not problems, "\n".join(problems)


def test_the_watchdog_timeout_stays_under_the_rp2_cap(real_tags: "list[Tag]") -> None:
    for value in _values(real_tags, "wdt.timeout_ms"):
        assert value <= _RP2_WDT_MAX_MS, f"wdt.timeout_ms {value:g} exceeds rp2's {_RP2_WDT_MAX_MS} ms WDT cap"


def test_the_reset_delay_ends_before_the_watchdog_would(real_tags: "list[Tag]") -> None:
    timeout_ms = min(_values(real_tags, "wdt.timeout_ms"))
    for delay_s in _values(real_tags, "system.reset_delay_s"):
        assert delay_s * 1000 < timeout_ms, f"system.reset_delay_s ({delay_s:g} s) must end before the {timeout_ms:g} ms watchdog does"


def test_the_supervisor_scan_fits_the_watchdog_several_times(real_tags: "list[Tag]") -> None:
    timeout_ms = min(_values(real_tags, "wdt.timeout_ms"))
    for check_s in _values(real_tags, "system.task_check_s"):
        assert check_s * 1000 * _TASK_CHECK_FACTOR <= timeout_ms, f"system.task_check_s ({check_s:g} s) x {_TASK_CHECK_FACTOR} must fit the {timeout_ms:g} ms watchdog"


def test_one_page_load_fits_the_largest_shipped_connection_ceiling(repo_root: Path, real_tags: "list[Tag]") -> None:
    ceiling = max(device_max_connections(device_toml(d), repo_root / "src") for d in DEVICE_NAMES)
    for per_load in _values(real_tags, "web.connections_per_page_load"):
        assert per_load <= ceiling, f"one page load opens {per_load:g} connections, above the largest shipped max_connections ({ceiling})"


# ---------------------------------------------------------------------------
# The check on a tmp tree: each planted defect is reported, and the clean tree reports nothing.
# ---------------------------------------------------------------------------

_ROW = "| `{id}` | {value} | `{sites}` | none | owner decision (owner, 2026-09-26) | 2x | any change |"
_HEAD = "| ID | Value | Sites (file — literal) | Dependants | Basis | Margin | Re-check trigger |\n|---|---|---|---|---|---|---|"


def _tree(tmp_path: Path, source: str, rows: "list[str]") -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "mod.py").write_text(source)
    (tmp_path / "SPECIFICATION.md").write_text(f"# Part N\n\n{_BEGIN}\n## N.3\n\n{_HEAD}\n" + "\n".join(rows) + f"\n{_END}\n")
    return tmp_path


def _tag(tunable_id: str, literal: str) -> str:
    return f"# @{_NAME} {tunable_id} = {literal}\n"


def test_a_clean_tree_reports_nothing(tmp_path: Path) -> None:
    root = _tree(tmp_path, _tag("x.wait_s", "5.0") + "WAIT_S = 5.0\n", [_ROW.format(id="x.wait_s", value="5.0 s", sites="src/mod.py — 5.0")])
    assert check_tree(root) == []


def test_a_row_without_a_tag_is_reported(tmp_path: Path) -> None:
    root = _tree(tmp_path, "WAIT_S = 5.0\n", [_ROW.format(id="x.wait_s", value="5.0 s", sites="src/mod.py — 5.0")])
    assert any("no file carries its" in p for p in check_tree(root)), check_tree(root)


def test_a_tag_without_a_row_is_reported(tmp_path: Path) -> None:
    root = _tree(tmp_path, _tag("x.wait_s", "5.0") + "WAIT_S = 5.0\n", [])
    assert any("has no SPECIFICATION.md Part N row" in p for p in check_tree(root)), check_tree(root)


def test_a_row_listing_another_literal_is_reported(tmp_path: Path) -> None:
    root = _tree(tmp_path, _tag("x.wait_s", "5.0") + "WAIT_S = 5.0\n", [_ROW.format(id="x.wait_s", value="6.0 s", sites="src/mod.py — 6.0")])
    assert any("Sites list" in p for p in check_tree(root)), check_tree(root)


def test_a_near_miss_tag_is_reported(tmp_path: Path) -> None:
    root = _tree(tmp_path, "# @tunabel x.wait_s = 5.0\nWAIT_S = 5.0\n", [])
    assert any("malformed or near-miss" in p for p in check_tree(root)), check_tree(root)


def test_a_tag_whose_literal_is_not_on_the_next_line_is_reported(tmp_path: Path) -> None:
    root = _tree(tmp_path, _tag("x.wait_s", "5.0") + "WAIT_S = 15.0\n", [_ROW.format(id="x.wait_s", value="5.0 s", sites="src/mod.py — 5.0")])
    assert any("does not carry 5.0 as a whole token" in p for p in check_tree(root)), check_tree(root)


def test_a_tag_in_a_file_type_the_check_cannot_read_is_reported(tmp_path: Path) -> None:
    root = _tree(tmp_path, "", [])
    (root / "src" / "mypy.ini").write_text(f"[mypy]\n# @{_NAME} x.wait_s = 5\nwait = 5\n")
    assert any("file type this check cannot read" in p for p in check_tree(root)), check_tree(root)


def test_a_trailing_tag_and_a_tag_in_a_string_are_told_apart(tmp_path: Path) -> None:
    source = f"WAIT_S = 5.0  # @{_NAME} x.wait_s = 5.0\nTEXT = '# @{_NAME} not a comment'\n"
    problems = check_tree(_tree(tmp_path, source, []))
    assert len(problems) == 1, problems
    assert "on its own comment line" in problems[0]


def test_an_estimated_basis_without_its_owed_measurement_and_a_rule_without_a_check_are_reported(tmp_path: Path) -> None:
    row = _ROW.format(id="x.wait_s", value="5.0 s", sites="src/mod.py — 5.0").replace("owner decision (owner, 2026-09-26)", "estimated (agent, abc1234)")
    rule = "\n## N.4\n\n| ID | Value | Dependants | Checked by |\n|---|---|---|---|\n| `x.bound_us` | sub-ms | every wait | — |"
    problems = check_tree(_tree(tmp_path, _tag("x.wait_s", "5.0") + "WAIT_S = 5.0\n", [row + rule]))
    assert any("measurement owed" in p for p in problems), problems
    assert any("naming no checking test or review" in p for p in problems), problems
