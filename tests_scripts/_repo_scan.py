"""Shared walk for the whole-repo checks (citations, decision vocabulary, import placement): the tracked
files, the prose each holds (Markdown text; comments and docstrings in code and config), and the
allow-list reader/writer behind each check's --regenerate mode."""

import ast
import fnmatch
import io
import re
import shutil
import subprocess
import sys
import tokenize
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_GIT = shutil.which("git") or "git"

# The legacy tree is reference-only (CLAUDE.md legacy rule) and stays out of every check. The audit
# working set is excluded until its close deletes it; arduino/ and ext/ are not this project's text.
LEGACY_PREFIXES = ("python/", "modules/", "html_raw/", "dev_legacy/")
LEGACY_ROOT_GLOBS = ("build-*.sh", "update_and_install.txt")
SHARED_EXCLUDED_PREFIXES = (*LEGACY_PREFIXES, "arduino/", "ext/", "audit/", "datasheets/", "node_modules/")
SHARED_EXCLUDED_FILES = frozenset({"PROJECT_AUDIT_PLAN.md", "uv.lock", "package-lock.json"})

_HASH_SUFFIXES = frozenset({".sh", ".toml", ".yml", ".yaml", ".ini", ".cfg", ".mk", ".gitignore"})
_SLASH_SUFFIXES = frozenset({".js", ".mjs", ".cjs", ".ts", ".css"})
_PLAIN_SUFFIXES = frozenset({".md", ".txt"})
# Types with no comment syntax to read (tsconfig*.json aside); any other unread type raises in
# prose_blocks(), so a new one cannot drop out of the checks unseen.
_NO_PROSE_SUFFIXES = frozenset({".json", ".nvmrc"})
_NO_PROSE_NAMES = ("LICENSE*",)
_TRAILING_HASH = re.compile(r"\s#(?:\s|$)")
_RULE_LINE = re.compile(r"^\s*[-=~*#]{4,}\s*$")


@dataclass(frozen=True)
class Block:
    """One run of prose: a comment block, a docstring or a Markdown paragraph, from its first line."""

    path: str
    line: int
    lines: tuple[str, ...]


def git_lines(*args: str) -> list[str]:
    result = subprocess.run([_GIT, *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    return result.stdout.splitlines()


def git_succeeds(*args: str) -> bool:
    return subprocess.run([_GIT, *args], cwd=REPO_ROOT, capture_output=True, check=False).returncode == 0


def git_ignored(paths: set[str]) -> set[str]:
    """The subset of `paths` git would ignore - a runtime artifact's name, not a stale citation."""
    if not paths:
        return set()
    result = subprocess.run([_GIT, "check-ignore", "--stdin"], cwd=REPO_ROOT, input="\n".join(sorted(paths)) + "\n", capture_output=True, text=True, check=False)
    return set(result.stdout.splitlines())


def repo_files() -> list[str]:
    """The tracked files; a listing without SPECIFICATION.md (a copy nested untracked in another
    repository lists nothing) raises, since every check would otherwise pass on an empty scan."""
    listed = subprocess.run([_GIT, "ls-files", "-z"], cwd=REPO_ROOT, capture_output=True, check=True).stdout
    files = sorted({p for p in listed.decode().split("\0") if p and (REPO_ROOT / p).is_file()})
    if "SPECIFICATION.md" not in files:
        msg = f"git ls-files in {REPO_ROOT} lists no SPECIFICATION.md - not this repository's own checkout"
        raise RuntimeError(msg)
    return files


def is_shared_excluded(path: str) -> bool:
    if path in SHARED_EXCLUDED_FILES or path.startswith(SHARED_EXCLUDED_PREFIXES):
        return True
    return "/" not in path and any(fnmatch.fnmatch(path, glob) for glob in LEGACY_ROOT_GLOBS)


def read_text(path: str) -> str | None:
    """The file's text, or None for a binary file (a NUL byte). A text file that is not UTF-8 raises,
    as import placement's own read does, rather than reading as a file with no prose."""
    raw = (REPO_ROOT / path).read_bytes()
    if b"\0" in raw[:8192]:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        exc.add_note(f"while reading {path}")
        raise


def _suffix(path: str) -> str:
    name = Path(path).name
    return name if name.startswith(".") and name.count(".") == 1 else Path(path).suffix.lower()


def is_plain(path: str) -> bool:
    return _suffix(path) in _PLAIN_SUFFIXES


def _grouped(path: str, own_line: list[tuple[int, str]], single: list[tuple[int, str]]) -> list[Block]:
    """Consecutive own-line comments form one block, a bare marker line splitting it; a trailing
    comment is a block of its own."""
    blocks: list[Block] = []
    run: list[tuple[int, str]] = []
    for row, raw in [*own_line, (-2, "")]:
        body = "" if _RULE_LINE.match(raw) else raw.strip()
        if run and (row != run[-1][0] + 1 or not body):
            blocks.append(Block(path, run[0][0], tuple(b for _, b in run)))
            run = []
        if body:
            run.append((row, body))
    blocks.extend(Block(path, row, (body.strip(),)) for row, body in single if body.strip())
    return blocks


def _python_blocks(path: str, text: str) -> list[Block]:
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
        tree = ast.parse(text)
    except (SyntaxError, tokenize.TokenError):
        return _hash_blocks(path, text)
    own: list[tuple[int, str]] = []
    single: list[tuple[int, str]] = []
    for tok in tokens:
        if tok.type == tokenize.COMMENT and not tok.string.startswith("#!"):
            body = tok.string[1:]
            (own if not tok.line[: tok.start[1]].strip() else single).append((tok.start[0], body))
    blocks = _grouped(path, own, single)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                lines = tuple(ln.strip() for ln in first.value.value.splitlines() if ln.strip())
                if lines:
                    blocks.append(Block(path, first.lineno, lines))
    return blocks


def _outside_quotes(line: str, index: int) -> bool:
    head = line[:index]
    return head.count('"') % 2 == 0 and head.count("'") % 2 == 0


def _hash_blocks(path: str, text: str) -> list[Block]:
    own: list[tuple[int, str]] = []
    single: list[tuple[int, str]] = []
    for row, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            if not stripped.startswith("#!"):
                own.append((row, stripped[1:]))
        elif (match := _TRAILING_HASH.search(line)) and _outside_quotes(line, match.start()):
            single.append((row, line[match.start() + 2 :]))
    return _grouped(path, own, single)


def _slash_blocks(path: str, text: str) -> list[Block]:
    """// and /* */ comments, string literals skipped (a regex literal is not, and needs none here)."""
    own: list[tuple[int, str]] = []
    single: list[tuple[int, str]] = []
    blocks: list[Block] = []
    i, row, quote, line_start = 0, 1, "", 0
    while i < len(text):
        ch = text[i]
        if ch == "\n":
            row, line_start = row + 1, i + 1
        if quote:
            if ch == "\\":
                i += 1
            elif ch == quote:
                quote = ""
        elif ch in "'\"`" and not path.endswith(".css"):
            quote = ch
        elif text.startswith("//", i) and not path.endswith(".css"):
            end = text.find("\n", i)
            end = len(text) if end < 0 else end
            (own if not text[line_start:i].strip() else single).append((row, text[i + 2 : end]))
            i = end
            continue
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            end = len(text) if end < 0 else end
            body = text[i + 2 : end]
            lines = tuple(s for ln in body.splitlines() if (s := ln.strip().lstrip("*").strip()))
            if lines:
                blocks.append(Block(path, row, lines))
            row += body.count("\n")
            i = end + 2
            continue
        i += 1
    return blocks + _grouped(path, own, single)


def _html_blocks(path: str, text: str) -> list[Block]:
    blocks = []
    for match in re.finditer(r"<!--(.*?)-->", text, re.DOTALL):
        lines = tuple(s for ln in match.group(1).splitlines() if (s := ln.strip()))
        if lines:
            blocks.append(Block(path, text.count("\n", 0, match.start()) + 1, lines))
    return blocks


def _markdown_blocks(path: str, text: str) -> list[Block]:
    """A paragraph, bullet, table row or heading is one unit; a fenced block's lines are prose too."""
    blocks: list[Block] = []
    run: list[tuple[int, str]] = []
    for row, line in [*enumerate(text.splitlines(), 1), (-2, "")]:
        stripped = line.strip()
        starts_unit = re.match(r"^(?:[-*+]\s|\d+\.\s|#{1,6}\s|\||```|>)", stripped) is not None
        if run and (not stripped or starts_unit):
            blocks.append(Block(path, run[0][0], tuple(b for _, b in run)))
            run = []
        if stripped:
            run.append((row, stripped))
    return blocks


def prose_blocks(path: str, text: str) -> list[Block]:
    suffix = _suffix(path)
    if suffix in _PLAIN_SUFFIXES:
        return _markdown_blocks(path, text)
    if suffix == ".py":
        return _python_blocks(path, text)
    if suffix in _HASH_SUFFIXES:
        return _hash_blocks(path, text)
    if suffix in _SLASH_SUFFIXES or (suffix == ".json" and Path(path).name.startswith("tsconfig")):
        return _slash_blocks(path, text)
    if suffix == ".html":
        return _html_blocks(path, text)
    if suffix in _NO_PROSE_SUFFIXES or any(fnmatch.fnmatch(Path(path).name, glob) for glob in _NO_PROSE_NAMES):
        return []
    msg = f"{path}: no prose reader for this file type - add one to _repo_scan.py, or list the type as prose-free there"
    raise ValueError(msg)


def read_allowlist(path: Path) -> Counter[tuple[str, str]]:
    """One line covers one occurrence: a miss repeated in a file is listed as often as it occurs."""
    entries: Counter[tuple[str, str]] = Counter()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            file_path, _, token = line.partition("\t")
            entries[(file_path, token)] += 1
    return entries


def write_allowlist(path: Path, header: tuple[str, ...], entries: Counter[tuple[str, str]]) -> None:
    """Sorted and newline-terminated, so a rerun over an unchanged tree rewrites the same bytes."""
    lines = [f"# {line}" for line in header] + [f"{file_path}\t{token}" for file_path, token in sorted(entries.elements())]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def regenerate_allowlist(path: Path, header: tuple[str, ...], current: Counter[tuple[str, str]]) -> list[tuple[str, str]]:
    """Writes previous & current, so the list only shrinks, and returns the new findings it left out;
    with no list yet (a check's own landing) it writes the whole current set."""
    previous = read_allowlist(path) if path.exists() else current
    write_allowlist(path, header, previous & current)
    return sorted((current - previous).elements())


def exit_on_new(written: str, new: Sequence[tuple[str, ...]]) -> None:
    """A --regenerate's last step: exit 1 naming each finding it refused to list."""
    print(f"wrote {written}")
    if new:
        sys.exit("not listed - the list only shrinks; fix these in the text:\n" + "\n".join("  " + "\t".join(entry) for entry in new))
