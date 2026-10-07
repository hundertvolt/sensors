"""Every citation in the living text resolves (CLAUDE.md's decision-records rule 5): repo paths, SPEC
headings, BACKLOG items, no label of a deleted plan. Existing misses sit in _citation_allowlist.txt,
which only shrinks; `uv run python tests_scripts/test_citations.py --regenerate` prunes it."""

import re
import shutil
import subprocess
import sys
import warnings
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path

import _repo_scan
import pytest
from _repo_scan import REPO_ROOT, exit_on_new, git_ignored, git_lines, git_succeeds, is_plain, is_shared_excluded, prose_blocks, read_allowlist, read_text, regenerate_allowlist, repo_files
from test_legacy_paths import PRE_MOVE_ROOTS

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
# Top-level directories since deleted: a citation into one is checked (and misses) instead of being
# passed over as not a repo path. A directory joins here in the commit that deletes it; the legacy
# roots moved under legacy/ come from the check that keeps them gone.
_RETIRED_TOPS = frozenset({"improved-quality", *PRE_MOVE_ROOTS})
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
    # What a citation resolves against: the tree, SPEC's headings, BACKLOG's items, the row keys.

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


def _top_entries(files: list[str]) -> set[str]:
    return {p.split("/", 1)[0] for p in files} | _RETIRED_TOPS


def _datasheets_checked() -> bool:
    # A skip warns rather than prints: pytest shows a warning summary even under -q, never a passing test's output.
    status = git_lines("submodule", "status", "datasheets")
    if status and status[0].startswith("-"):
        warnings.warn("datasheets/ submodule not initialised - paths under it are not checked", stacklevel=2)
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
    # The unresolved paths a token cites. An `a.md/b.md` alternation is split at each known file, and
    # an unresolved name with no extension and no trailing slash is prose ("tests/mypy/ruff/CI").
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
    # 'ok' when the archive commit is an ancestor, 'shallow' when a shallow clone lacks it, else 'missing'.
    if git_succeeds("merge-base", "--is-ancestor", _ARCHIVE_COMMIT, "HEAD"):
        return "ok"
    if git_lines("rev-parse", "--is-shallow-repository") == ["true"]:
        warnings.warn(f"shallow clone without {_ARCHIVE_COMMIT} - 'archive §N' citations are not checked", stacklevel=2)
        return "shallow"
    return "missing"


def _prose_lines(path: str, text: str) -> list[str]:
    # Markdown and plain text whole; code and config by their comments and docstrings only, so a
    # synthetic path in a test's string literal is not mistaken for a citation.
    if is_plain(path):
        return text.splitlines()
    return [line for block in prose_blocks(path, text) for line in block.lines]


def _token_misses(path: str, token: str, ctx: _Context) -> set[str]:
    # A token under a directory beside the citing file resolves relative to it, else from the root;
    # it misses only when every reading misses, and is then reported as the first reading.
    first, here = token.split("/", 1)[0], path.rpartition("/")[0]
    readings = []
    if here and f"{here}/{first}" in ctx.known - ctx.files:
        readings.append(_path_misses(f"{here}/{token}", ctx))
    if first in ctx.top and first not in _UPSTREAM_ROOTS and (first != "datasheets" or ctx.datasheets):
        readings.append(_path_misses(token, ctx))
    return readings[0] if readings and all(readings) else set()


def _file_findings(path: str, lines: list[str], ctx: _Context) -> Counter[str]:
    # Each occurrence counts, so one allow-list line covers one occurrence.
    found: Counter[str] = Counter()
    text = "\n".join(lines)
    for match in _PATH_TOKEN.finditer(text):
        found.update(_token_misses(path, _clean_path(match.group(1)), ctx))
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


def collect_findings() -> Counter[tuple[str, str]]:
    files = repo_files()
    scanned = {path: text for path in _scanned_files() if (text := read_text(path)) is not None}
    ctx = _Context(
        files=set(files),
        top=_top_entries(files),
        known=_known_paths(files),
        md_names={Path(p).name for p in files if p.endswith(".md")},
        spec=_spec_ids(),
        backlog=_backlog_numbers(),
        rows={key for path, text in scanned.items() if path.endswith(".md") for key in _ROW_KEY.findall(text)},
        datasheets=_datasheets_checked(),
        archive=_archive_state(),
    )
    findings = Counter({(path, token): n for path, text in scanned.items() for token, n in _file_findings(path, _prose_lines(path, text), ctx).items()})
    ignored = git_ignored({token for _, token in findings if "/" in token or token.endswith(".md")})
    return Counter({key: n for key, n in findings.items() if key[1] not in ignored})


@pytest.fixture(scope="module")
def findings() -> Counter[tuple[str, str]]:
    return collect_findings()


def test_every_citation_resolves_or_is_allow_listed(findings: Counter[tuple[str, str]]) -> None:
    new = sorted((findings - read_allowlist(ALLOWLIST)).elements())
    assert not new, "unresolved citations (path, token) - point at what exists, or state the fact in place:\n" + "\n".join(f"  {p}: {t}" for p, t in new)


def test_the_allowlist_only_shrinks(findings: Counter[tuple[str, str]]) -> None:
    stale = sorted((read_allowlist(ALLOWLIST) - findings).elements())
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
    assert _file_findings("x.md", [text, "U26 and V07 but not `E21`, E21, D65 or B10"], _FIXTURE_CTX) == Counter([
        "src/gone.py", "GONE_PLAN.md", "Part B.2", "SPEC A.9", "BACKLOG item 7", "WP3", "OR12", "archive §4", "U26", "V07",
    ])


def test_a_label_the_file_itself_opens_is_defined() -> None:
    lines = ["## Step 1: build", "Then Step 1 again, and Step 2."]
    assert _file_findings("y.md", lines, replace(_FIXTURE_CTX, archive="ok")) == Counter(["Step 2"])


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
    assert _file_findings("z.py", _prose_lines("z.py", source), _FIXTURE_CTX) == Counter(["src/also_gone.py"])


def test_a_skipped_check_warns_so_a_quiet_run_still_shows_it(monkeypatch: pytest.MonkeyPatch) -> None:
    def lines(*args: str) -> list[str]:
        return ["true"] if args[0] == "rev-parse" else ["-0123456 datasheets"]

    this = sys.modules[__name__]
    monkeypatch.setattr(this, "git_succeeds", lambda *_: False)
    monkeypatch.setattr(this, "git_lines", lines)
    with pytest.warns(UserWarning, match="archive"):
        assert _archive_state() == "shallow"
    with pytest.warns(UserWarning, match="datasheets"):
        assert not _datasheets_checked()


def test_a_file_that_is_not_utf8_raises_rather_than_reading_as_no_prose(tmp_path: Path) -> None:
    (tmp_path / "latin1.md").write_bytes("caf\xe9 cites src/gone.py\n".encode("latin-1"))
    (tmp_path / "blob.bin").write_bytes(b"\x00\x01")
    with pytest.raises(UnicodeDecodeError):
        read_text(str(tmp_path / "latin1.md"))
    assert read_text(str(tmp_path / "blob.bin")) is None


def test_an_unlisted_file_type_raises_rather_than_reading_as_no_prose() -> None:
    for path in ("tools/probe.jsonc", "scripts/no_suffix", "src/extension.pyx"):
        with pytest.raises(ValueError, match="no prose reader"):
            prose_blocks(path, "# cites src/gone.py\n")
    assert [b.lines for b in prose_blocks("src/stub.pyi", "# cites src/gone.py\n")] == [b.lines for b in prose_blocks("src/stub.py", "# cites src/gone.py\n")] != []
    assert prose_blocks("package.json", "{}") == prose_blocks(".nvmrc", "24\n") == prose_blocks("ext/LICENSE-x", "MIT") == []


def test_every_scanned_text_file_has_a_prose_reader_or_is_listed_prose_free() -> None:
    for path in repo_files():
        if not is_shared_excluded(path) and read_text(path) is not None:
            prose_blocks(path, "")


def test_citations_into_a_retired_top_level_directory_are_checked() -> None:
    ctx = replace(_FIXTURE_CTX, top=_top_entries(sorted(_FIXTURE_CTX.files)))
    assert _file_findings("x.md", ["Moved out of improved-quality/old.py into src/real.py."], ctx) == Counter({"improved-quality/old.py": 1})


def test_a_path_under_a_directory_beside_the_citing_file_resolves_relative_to_it() -> None:
    files = ["SPECIFICATION.md", "hw/README.md", "hw/flash/t.py", "hw/src/x.py", "src/real.py"]
    ctx = replace(_FIXTURE_CTX, files=set(files), top=_top_entries(files), known=_known_paths(files))
    lines = ["flash/t.py, flash/gone.py, src/x.py, src/real.py, src/none.py"]
    assert _file_findings("hw/README.md", lines, ctx) == Counter({"hw/flash/gone.py": 1, "hw/src/none.py": 1})
    assert _file_findings("README.md", lines, ctx) == Counter({"src/x.py": 1, "src/none.py": 1})


def test_each_occurrence_counts_and_one_allow_list_line_covers_one(tmp_path: Path) -> None:
    assert _file_findings("x.md", ["See WP3, src/gone.py and WP3 again"], _FIXTURE_CTX) == Counter({"WP3": 2, "src/gone.py": 1})
    listed = tmp_path / "allow.txt"
    listed.write_text("# header\nx.md\tWP3\n", encoding="utf-8")
    assert Counter({("x.md", "WP3"): 2}) - read_allowlist(listed) == Counter({("x.md", "WP3"): 1})


def test_regenerate_only_shrinks_and_names_what_it_did_not_add(tmp_path: Path) -> None:
    listed, header = tmp_path / "allow.txt", ("h",)
    first = Counter([("a.md", "X"), ("a.md", "X"), ("b.md", "Y")])
    assert regenerate_allowlist(listed, header, first) == []
    assert read_allowlist(listed) == first
    assert regenerate_allowlist(listed, header, Counter([("a.md", "X"), ("c.md", "Z"), ("c.md", "Z")])) == [("c.md", "Z"), ("c.md", "Z")]
    assert read_allowlist(listed) == Counter([("a.md", "X")])
    before = listed.read_bytes()
    assert regenerate_allowlist(listed, header, Counter([("a.md", "X")])) == []
    assert listed.read_bytes() == before
    with pytest.raises(SystemExit, match=r"c\.md"):
        exit_on_new("allow.txt", [("c.md", "Z")])


def test_a_listing_without_specification_md_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    git = shutil.which("git") or "git"
    subprocess.run([git, "init", "-q", str(tmp_path)], check=True)
    copy = tmp_path / "copy"
    copy.mkdir()
    (copy / "SPECIFICATION.md").write_text("# an untracked copy nested in another repository\n")
    monkeypatch.setattr(_repo_scan, "REPO_ROOT", copy)
    with pytest.raises(RuntimeError, match=r"SPECIFICATION\.md"):
        repo_files()
    (copy / "other.txt").write_text("tracked by the outer repository\n")
    subprocess.run([git, "-C", str(tmp_path), "add", "copy/other.txt"], check=True)
    with pytest.raises(RuntimeError, match=r"SPECIFICATION\.md"):
        repo_files()


def _regenerate() -> None:
    new = regenerate_allowlist(ALLOWLIST, _ALLOWLIST_HEADER, collect_findings())
    exit_on_new(str(ALLOWLIST.relative_to(REPO_ROOT)), new)


if __name__ == "__main__":
    if sys.argv[1:] != ["--regenerate"]:
        sys.exit("usage: uv run python tests_scripts/test_citations.py --regenerate")
    _regenerate()
