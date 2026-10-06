"""Every citation in the living text resolves (CLAUDE.md's decision-records rule 5): repo paths, SPEC
headings, BACKLOG items, no label of a deleted plan. Existing misses sit in _citation_allowlist.txt,
which only shrinks; `uv run python tests_scripts/test_citations.py --regenerate` rebuilds it."""

import re
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import pytest
from _repo_scan import REPO_ROOT, git_ignored, git_lines, git_succeeds, is_plain, is_shared_excluded, prose_blocks, read_allowlist, read_text, repo_files, write_allowlist

ALLOWLIST = Path(__file__).resolve().parent / "_citation_allowlist.txt"
_ALLOWLIST_HEADER = (
    "path<TAB>token: citations that did not resolve when the check landed. Only shrinks: fix the citing",
    "text, then rerun `uv run python tests_scripts/test_citations.py --regenerate`.",
)
# The check's own files and the two allow-lists hold the patterns and the misses themselves.
_SELF = frozenset({"tests_scripts/test_citations.py", "tests_scripts/_citation_allowlist.txt", "tests_scripts/_decision_vocab_allowlist.txt"})

# (a) Repo paths: a token starting with a top-level repo entry, or a bare *.md name. Upstream
# MicroPython roots are skipped by name, and the lookbehind refuses absolute, $VAR and URL paths.
_PATH_TOKEN = re.compile(r"(?<![\w/$~@.:\\-])((?:\./)?\.?[A-Za-z0-9_][\w.\-]*/[^\s`'\"()\[\],;:|=]*)")
_MD_NAME = re.compile(r"(?<![\w/$~@.:\\-])([A-Za-z0-9_][\w.\-]*\.md)\b")
_UPSTREAM_ROOTS = frozenset({"py", "ports", "extmod", "lib", "shared", "tools", "docs", "drivers"})
_PLACEHOLDER = re.compile(r"[<>{}$\\^+|…]|\.\.\.")
_GLOB = re.compile(r"[*?]")
# A file name with a hyphenated suffix glued on ("machine.py-backed") cites the file before it.
_HYPHEN_SUFFIX = re.compile(r"^(.+\.\w+)-[\w-]+$")

# (b) SPECIFICATION.md Part/section citations, each checked against a heading's own ID. "Part X" is
# the literal placeholder CLAUDE.md's "Moved to SPECIFICATION.md Part X" pattern uses.
_SPEC_PART = re.compile(r"\bParts?\s+([A-Z](?:\.\d+)*)(?![\w.]*\w)((?:\s*(?:,|and|&|/)\s*[A-Z](?:\.\d+)+)*)")
_SPEC_PART_TAIL = re.compile(r"[A-Z](?:\.\d+)+")
_SPEC_SECTION = re.compile(r"\bSPEC(?:IFICATION(?:\.md)?)?(?:'s)?\s+§?([A-Z]\.\d+(?:\.\d+)*)")
_SPEC_HEADING = re.compile(r"^#{1,6}\s+(?:Part\s+([A-Z])\b|([A-Z](?:\.\d+)+)\b)")
_PART_PLACEHOLDER = "X"

# (c) BACKLOG.md item citations, against its numbered items.
_BACKLOG_ITEM = re.compile(r"\bBACKLOG(?:\.md)?(?:'s)?\s+(?:#|(?:open\s+)?question\s+#?|item\s+#?)(\d+)\b")
_BACKLOG_NUMBERED = re.compile(r"^(\d+)\.\s")

# (d) Labels of deleted plans: defined only where the same file opens a heading, bullet or line with one.
_PLAN_LABELS = re.compile(r"\b(?:Session\s+\d+|Step\s+\d+|WP[1-8]|Topic\s+\d+|[Dd]ecision\s+#?\d+|measure\s+[AB]|Phase\s+\d+)\b")
_LINE_HEAD = re.compile(r"^[\s#>*\-/|]*(?:\d+\.\s*)?(?:\*\*)?")
# The audit's own IDs never belong in permanent text; unit names and list IDs are checked in prose
# only, outside code spans (a backticked `E21` is a literal), and a table row's own key defines one.
_AUDIT_IDS = re.compile(r"\b(?:OR\d+(?:\.[a-z])?|PQ\d+|LEAD/R\d+|HR\d+|[Hh]armonization\s+\d+|RF\d{3})\b")
_PROSE_IDS = re.compile(r"\b(?:U\d{1,2}|[ABCDEVL]\d\d|A2-0\d)\b")
_CODE_SPAN = re.compile(r"`[^`]*`")
_ROW_KEY = re.compile(r"^\|\s*([A-Z]\d\d)\s*\|", re.MULTILINE)
# Not list IDs: E10 and up is an error-catalog code (SPECIFICATION.md C.7.1), D65 the CIE standard
# illuminant, a Galaxy A54 the bench's Android phone.
_PROSE_ID_TERMS = re.compile(r"\bE[1-9]\d\b|\bD65\b|\bGalaxy A\d\d\b")

# (e) Archive-section citations hold while the archive commit is in history.
_ARCHIVE_CITE = re.compile(r"\barchive\s+§\s*\d+")
_ARCHIVE_COMMIT = "12640c2"


@dataclass(frozen=True)
class _Context:
    """What a citation resolves against: the tree, SPEC's headings, BACKLOG's items, the row keys."""

    files: set[str]
    top: set[str]
    known: set[str]
    md_names: set[str]
    spec: set[str]
    backlog: set[str]
    rows: set[str]
    datasheets: bool
    archive: str


def _scanned_files() -> list[str]:
    return [p for p in repo_files() if not is_shared_excluded(p) and p not in _SELF]


def _known_paths(files: list[str]) -> set[str]:
    known = set(files)
    for path in files:
        parts = path.split("/")
        known.update("/".join(parts[:i]) for i in range(1, len(parts)))
    return known


def _datasheets_checked() -> bool:
    status = git_lines("submodule", "status", "datasheets")
    if status and status[0].startswith("-"):
        print("notice: datasheets/ submodule not initialised - paths under it are not checked")
        return False
    return True


def _glob_regex(pattern: str) -> re.Pattern[str]:
    parts = re.split(r"(\*\*/|\*|\?)", pattern)
    table = {"**/": "(?:[^/]*/)*", "*": "[^/]*", "?": "[^/]"}
    return re.compile("".join(table.get(p, re.escape(p)) for p in parts) + "/?")


def _clean_path(token: str) -> str:
    token = token.split("#", 1)[0].removeprefix("./").rstrip(".!?'\"\\")
    while token.endswith("*") and not token.endswith("/*"):
        token = token[:-1]
    return token.rstrip(".")


def _path_resolves(token: str, known: set[str]) -> bool:
    segments = token.split("/")
    for i, seg in enumerate(segments):
        if _PLACEHOLDER.search(seg):
            return i == 0 or "/".join(segments[:i]) in known
    if _GLOB.search(token):
        pattern = _glob_regex(token.rstrip("/"))
        return any(pattern.fullmatch(path) for path in known)
    return token.rstrip("/") in known


def _path_misses(token: str, ctx: _Context) -> set[str]:
    """The unresolved paths a token cites. An `a.md/b.md` alternation is split at each known file, and
    an unresolved name with no extension and no trailing slash is prose ("tests/mypy/ruff/CI")."""
    if "//" in token:
        return set().union(*(_path_misses(part, ctx) for part in token.split("//") if part))
    segments = token.split("/")
    for i in range(1, len(segments)):
        if "/".join(segments[:i]) in ctx.files:
            rest = "/".join(segments[i:])
            return _path_misses(rest, ctx) if "/" in rest else ({rest} if rest.endswith(".md") and rest not in ctx.md_names else set())
    if _path_resolves(token, ctx.known):
        return set()
    if (hyphen := _HYPHEN_SUFFIX.match(token)) and _path_resolves(hyphen.group(1), ctx.known):
        return set()
    if not token.endswith("/") and "." not in segments[-1] and not _GLOB.search(segments[-1]):
        return set()
    return {token}


def _spec_ids() -> set[str]:
    ids, fenced = {_PART_PLACEHOLDER}, False
    for line in (REPO_ROOT / "SPECIFICATION.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and (match := _SPEC_HEADING.match(line)):
            ids.add(match.group(1) or match.group(2))
    return ids


def _backlog_numbers() -> set[str]:
    text = (REPO_ROOT / "BACKLOG.md").read_text(encoding="utf-8")
    return {m.group(1) for line in text.splitlines() if (m := _BACKLOG_NUMBERED.match(line))}


def _defined_labels(lines: list[str]) -> set[str]:
    return {" ".join(m.group(0).split()) for line in lines if (m := _PLAN_LABELS.match(_LINE_HEAD.sub("", line, count=1)))}


def _archive_state() -> str:
    """'ok' when the archive commit is an ancestor, 'shallow' when a shallow clone lacks it, else 'missing'."""
    if git_succeeds("merge-base", "--is-ancestor", _ARCHIVE_COMMIT, "HEAD"):
        return "ok"
    if git_lines("rev-parse", "--is-shallow-repository") == ["true"]:
        print(f"notice: shallow clone without {_ARCHIVE_COMMIT} - 'archive §N' citations are not checked")
        return "shallow"
    return "missing"


def _prose_lines(path: str, text: str) -> list[str]:
    """Markdown and plain text whole; code and config by their comments and docstrings only, so a
    synthetic path in a test's string literal is not mistaken for a citation."""
    if is_plain(path):
        return text.splitlines()
    return [line for block in prose_blocks(path, text) for line in block.lines]


def _file_findings(path: str, lines: list[str], ctx: _Context) -> set[str]:
    found: set[str] = set()
    text = "\n".join(lines)
    for match in _PATH_TOKEN.finditer(text):
        token = _clean_path(match.group(1))
        first = token.split("/", 1)[0]
        if first in ctx.top and first not in _UPSTREAM_ROOTS and (first != "datasheets" or ctx.datasheets):
            found.update(_path_misses(token, ctx))
    found.update(m.group(1) for m in _MD_NAME.finditer(text) if m.group(1) not in ctx.md_names)
    for match in _SPEC_PART.finditer(text):
        found.update(f"Part {ident}" for ident in [match.group(1), *_SPEC_PART_TAIL.findall(match.group(2))] if ident not in ctx.spec)
    found.update(f"SPEC {m.group(1)}" for m in _SPEC_SECTION.finditer(text) if m.group(1) not in ctx.spec)
    found.update(f"BACKLOG item {m.group(1)}" for m in _BACKLOG_ITEM.finditer(text) if m.group(1) not in ctx.backlog)
    defined = _defined_labels(lines)
    found.update(label for m in _PLAN_LABELS.finditer(text) if (label := " ".join(m.group(0).split())) not in defined)
    found.update(" ".join(m.group(0).split()) for m in _AUDIT_IDS.finditer(text))
    for line in lines:
        prose = _PROSE_ID_TERMS.sub("", _CODE_SPAN.sub("", line))
        found.update(ident for m in _PROSE_IDS.finditer(prose) if (ident := m.group(0)) not in ctx.rows)
    if ctx.archive == "missing":
        found.update(" ".join(m.group(0).split()) for m in _ARCHIVE_CITE.finditer(text))
    return found


def collect_findings() -> set[tuple[str, str]]:
    files = repo_files()
    scanned = {path: text for path in _scanned_files() if (text := read_text(path)) is not None}
    ctx = _Context(
        files=set(files),
        top={p.split("/", 1)[0] for p in files},
        known=_known_paths(files),
        md_names={Path(p).name for p in files if p.endswith(".md")},
        spec=_spec_ids(),
        backlog=_backlog_numbers(),
        rows={key for path, text in scanned.items() if path.endswith(".md") for key in _ROW_KEY.findall(text)},
        datasheets=_datasheets_checked(),
        archive=_archive_state(),
    )
    findings = {(path, token) for path, text in scanned.items() for token in _file_findings(path, _prose_lines(path, text), ctx)}
    ignored = git_ignored({token for _, token in findings if "/" in token or token.endswith(".md")})
    return {(path, token) for path, token in findings if token not in ignored}


@pytest.fixture(scope="module")
def findings() -> set[tuple[str, str]]:
    return collect_findings()


def test_every_citation_resolves_or_is_allow_listed(findings: set[tuple[str, str]]) -> None:
    new = sorted(findings - read_allowlist(ALLOWLIST))
    assert not new, "unresolved citations (path, token) - point at what exists, or state the fact in place:\n" + "\n".join(f"  {p}: {t}" for p, t in new)


def test_the_allowlist_only_shrinks(findings: set[tuple[str, str]]) -> None:
    stale = sorted(read_allowlist(ALLOWLIST) - findings)
    assert not stale, "allow-list entries that no longer occur - delete these lines (or --regenerate):\n" + "\n".join(f"  {p}\t{t}" for p, t in stale)


_FIXTURE_CTX = _Context(
    files={"src/real.py", "SPECIFICATION.md"},
    top={"src", "SPECIFICATION.md"},
    known={"src", "src/real.py", "SPECIFICATION.md"},
    md_names={"SPECIFICATION.md"},
    spec={"X", "A", "A.1"},
    backlog={"1"},
    rows={"B10"},
    datasheets=True,
    archive="missing",
)


def test_each_kind_of_miss_is_caught() -> None:
    text = "See src/gone.py, src/real.py, GONE_PLAN.md, Part A.1, Part B.2, SPEC A.9, BACKLOG item 7, BACKLOG #1, WP3, OR12, archive §4."
    assert _file_findings("x.md", [text, "U26 and V07 but not `E21`, E21, D65 or B10"], _FIXTURE_CTX) == {
        "src/gone.py", "GONE_PLAN.md", "Part B.2", "SPEC A.9", "BACKLOG item 7", "WP3", "OR12", "archive §4", "U26", "V07",
    }


def test_a_label_the_file_itself_opens_is_defined() -> None:
    lines = ["## Step 1: build", "Then Step 1 again, and Step 2."]
    assert _file_findings("y.md", lines, replace(_FIXTURE_CTX, archive="ok")) == {"Step 2"}


def test_paths_resolve_through_placeholders_globs_and_alternations() -> None:
    assert _path_misses("src/<name>.py", _FIXTURE_CTX) == set()
    assert _path_misses("src/*.py", _FIXTURE_CTX) == set()
    assert _path_misses("src/**/*.py", _FIXTURE_CTX) == set()
    assert _path_misses("src/*.c", _FIXTURE_CTX) == {"src/*.c"}
    assert _path_misses("src/real.py/GONE.md", _FIXTURE_CTX) == {"GONE.md"}
    assert _path_misses("src/real.py-backed", _FIXTURE_CTX) == set()
    assert _path_misses("src/mypy/ruff/CI", _FIXTURE_CTX) == set()
    assert _path_misses("src/gone/", _FIXTURE_CTX) == {"src/gone/"}


def test_code_files_are_read_by_their_comments_only() -> None:
    source = 'PATH = "src/gone.py"  # cites src/also_gone.py\n'
    assert _file_findings("z.py", _prose_lines("z.py", source), _FIXTURE_CTX) == {"src/also_gone.py"}


def _regenerate() -> None:
    write_allowlist(ALLOWLIST, _ALLOWLIST_HEADER, collect_findings())
    print(f"wrote {ALLOWLIST.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    if sys.argv[1:] != ["--regenerate"]:
        sys.exit("usage: uv run python tests_scripts/test_citations.py --regenerate")
    _regenerate()
