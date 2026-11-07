"""Every src/ file derived from third-party code opens with its three-line attribution header, and
THIRD_PARTY_LICENSES.md holds exactly one entry for it that agrees with that header (licence, holder, year):
read both ways from the files themselves, so a header or an entry changed alone fails here."""

import ast
import re
from pathlib import Path

_LICENCE_FILE = "THIRD_PARTY_LICENSES.md"
_COPYRIGHT_TAG = "# SPDX-FileCopyrightText: "
_LICENSE_TAG = "# SPDX-License-Identifier: "
# The one attributed file with no licence to name: its author offered the code in a public discussion. That whole
# section is its entry, so the section's mention of another src/ file is not that file's entry.
_NO_LICENSE_FILE = "src/asy_udp_socket.py"
_NO_LICENSE_MARKS = ("karfas", "github.com/orgs/micropython/discussions/12967", _LICENCE_FILE)
_NO_LICENSE_SECTION = "## Author-permitted, no formal license"
_CODE_SPAN = re.compile(r"`([^`]+)`")
_SCOPE_SENTENCE = re.compile(r"SPDX header reads `([^`]+)`")
_YEARS_AND_HOLDER = re.compile(r"^(?:Copyright )?(?:\(c\) )?(\d{4}(?:, \d{4})*) (.+)$")
_OPERATORS = frozenset({"AND", "OR", "WITH"})


def _attributed(root: Path) -> list[str]:
    spdx = [f"src/{p.name}" for p in sorted((root / "src").glob("*.py")) if p.read_text(encoding="utf-8").startswith(_COPYRIGHT_TAG)]
    return [*spdx, _NO_LICENSE_FILE]


def _docstring_follows(root: Path, rel: str) -> bool:
    # The module docstring is the first statement, with nothing but blank lines between it and the header.
    tree = ast.parse((root / rel).read_text(encoding="utf-8"))
    first = tree.body[0] if tree.body else None
    if not (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str)):
        return False
    return all(not line.strip() for line in _lines(root, rel)[3 : first.lineno - 1])


def _entries(root: Path) -> dict[str, list[str]]:
    # {subject: [text, ...]} of each top-level bullet: a `- ` line at column 0 and its indented continuation lines.
    found: list[tuple[str, list[str]]] = []
    section, current = "", None
    for line in _lines(root, _LICENCE_FILE):
        if line.startswith("## "):
            section, current = line, None
        elif line.startswith("- "):
            current = [line]
            found.append((section, current))
        elif current is not None and line.startswith("  "):
            current.append(line)
        else:
            current = None
    entries: dict[str, list[str]] = {}
    for heading, parts in found:
        text = " ".join(part.strip() for part in parts)
        entries.setdefault(_subject(heading, text), []).append(text)
    return entries


def _header_problems(root: Path, rel: str) -> list[str]:
    head = _lines(root, rel)[:3]
    if rel == _NO_LICENSE_FILE:
        shaped = len(head) == 3 and all(line.startswith("# ") and "SPDX-" not in line for line in head)
        missing = [mark for mark in _NO_LICENSE_MARKS if mark not in " ".join(head)]
        problems = [] if shaped and not missing else [f"{rel}: not three comment lines with no SPDX tag naming {_NO_LICENSE_MARKS} (missing {missing})"]
    else:
        shaped = len(head) == 3 and head[1].startswith(_LICENSE_TAG) and head[1][len(_LICENSE_TAG) :].strip() != ""
        shaped = shaped and head[2].startswith("# ") and _LICENCE_FILE in head[2] and "SPDX-" not in head[2]
        problems = [] if shaped else [f"{rel}: lines 2-3 are not `{_LICENSE_TAG}<expr>` then a comment naming {_LICENCE_FILE}: {head[1:]}"]
    return problems if _docstring_follows(root, rel) else [*problems, f"{rel}: the module docstring does not follow the header"]


def _holder(head: list[str]) -> tuple[str, str]:
    # (years, holder name) of a copyright line: "Copyright (c) 2020 Bryan Siepert for ..." gives ("2020", "Bryan ...").
    match = _YEARS_AND_HOLDER.match(head[0][len(_COPYRIGHT_TAG) :])
    return ("", "") if match is None else (match.group(1), re.split(r" \(|, ", match.group(2))[0])


def _lines(root: Path, rel: str) -> list[str]:
    return (root / rel).read_text(encoding="utf-8").splitlines()


def _subject(heading: str, text: str) -> str:
    if heading.startswith(_NO_LICENSE_SECTION) and f"`{_NO_LICENSE_FILE}`" in text:
        return _NO_LICENSE_FILE
    first = _CODE_SPAN.search(text)
    return first.group(1) if first else ""


def test_every_attributed_file_opens_with_its_header(repo_root: Path) -> None:
    attributed = _attributed(repo_root)
    problems = [problem for rel in attributed for problem in _header_problems(repo_root, rel)]
    # An SPDX tag anywhere else in src/ is a header in another order, or one the shape check cannot see.
    for path in sorted((repo_root / "src").glob("*.py")):
        rel = f"src/{path.name}"
        problems += [f"{rel}:{n}: SPDX tag outside a header's lines 1-2" for n, line in enumerate(_lines(repo_root, rel), 1) if "SPDX-" in line and (n > 2 or rel not in attributed)]
    assert not problems, "\n".join(problems)


def test_each_attributed_file_has_exactly_one_entry(repo_root: Path) -> None:
    entries = _entries(repo_root)
    wrong = {rel: len(entries.get(rel, [])) for rel in _attributed(repo_root) if len(entries.get(rel, [])) != 1}
    assert not wrong, f"each attributed src/ file needs exactly one {_LICENCE_FILE} entry whose first code span is its path: {wrong}"


def test_every_src_path_the_licence_file_names_exists_with_a_header(repo_root: Path) -> None:
    named = {span for span in _CODE_SPAN.findall(" ".join(_lines(repo_root, _LICENCE_FILE))) if span.startswith("src/")}
    named |= {subject for subject in _entries(repo_root) if subject.startswith("src/")}
    missing = sorted(span for span in named if not (repo_root / span).exists())
    headerless = sorted(span for span in named if span.endswith(".py") and span not in _attributed(repo_root))
    assert not missing and not headerless, f"{_LICENCE_FILE} names src/ paths that do not exist {missing} or carry no attribution header {headerless}"


def test_each_header_agrees_with_its_entry_on_licence_holder_and_year(repo_root: Path) -> None:
    entries, problems = _entries(repo_root), []
    # A file the shape or one-entry test names is skipped here: its header or its entry cannot be read as one.
    checked = [rel for rel in _attributed(repo_root) if rel != _NO_LICENSE_FILE and len(entries.get(rel, [])) == 1 and not _header_problems(repo_root, rel)]
    for rel in checked:
        head, entry = _lines(repo_root, rel)[:3], entries[rel][0]
        expression = head[1][len(_LICENSE_TAG) :].strip()
        ids = [token for token in re.split(r"[\s()]+", expression) if token and token not in _OPERATORS]
        problems += [f"{rel}: its entry does not name {token}" for token in ids if not re.search(rf"(?<![\w.-]){re.escape(token)}(?![\w-]|\.\w)", entry)]
        # A file under more than one licence has its entry state the expression, and any such statement matches.
        stated = _SCOPE_SENTENCE.findall(entry)
        if stated != [expression] and (stated or len(ids) > 1):
            problems.append(f"{rel}: the header reads `{expression}`, its entry states the SPDX header reads {stated}")
        years, holder = _holder(head)
        if not years or years not in entry or holder not in entry:
            problems.append(f"{rel}: its entry does not name the header's year {years!r} and holder {holder!r}")
        copyright_line = head[0][len(_COPYRIGHT_TAG) :]
        for licence in sorted({span for span in _CODE_SPAN.findall(entry) if span.startswith("src/LICENSE-")}):
            if copyright_line not in (line.strip() for line in _lines(repo_root, licence)):
                problems.append(f"{licence}: no line reads `{copyright_line}`, the holder line of {rel}'s header")
    assert not problems, "\n".join(problems)
