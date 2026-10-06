"""Decision vocabulary carries its actor (CLAUDE.md's decision-records rule 1): a sentence calling a thing
accepted, settled, decided or deliberate names who and when, or cites its source. Existing misses sit in
_decision_vocab_allowlist.txt, which only shrinks; `test_decision_vocabulary.py --regenerate` rebuilds it."""

import re
import sys
from pathlib import Path

import pytest
from _repo_scan import REPO_ROOT, Block, is_shared_excluded, prose_blocks, read_allowlist, read_text, repo_files, write_allowlist

ALLOWLIST = Path(__file__).resolve().parent / "_decision_vocab_allowlist.txt"
_ALLOWLIST_HEADER = (
    "path<TAB>sentence prefix: actorless decision vocabulary present when the check landed. Only shrinks:",
    "the sentence, then rerun `uv run python tests_scripts/test_decision_vocabulary.py --regenerate`.",
)
_SELF = frozenset({"tests_scripts/test_decision_vocabulary.py", "tests_scripts/_decision_vocab_allowlist.txt", "tests_scripts/_citation_allowlist.txt"})
_PREFIX_CHARS = 80

# The vocabulary. "never" counts only in its rule sense; the other words count wherever they occur.
_VOCABULARY = re.compile(
    r"\b(?:accepted|settled|decided|by design|deliberate(?:ly)?|(?:don't|do not)\s+re-(?:propose|raise)|must never|and never will|never be|never\b.{0,80}?\bagain)\b",
    re.IGNORECASE,
)
# Narrowing: "accepted" qualifying a request, value or connection is the protocol's outcome, not a decision.
_ACCEPTED_OBJECT = re.compile(r"\baccepted\s+(?:PUTs?|writes?|values?|connections?|by the server)\b", re.IGNORECASE)
# Narrowing: a blockquote or fence in THIRD_PARTY_LICENSES.md is quoted licence text, not this project's.
_LICENCE_FILE = "THIRD_PARTY_LICENSES.md"

# What makes a hit pass: an actor tag, or a source - a datasheet, an upstream source path, a commit SHA.
_ACTOR_TAG = re.compile(r"\((?:owner|agent)[^)]*\d{4}-\d{2}-\d{2}")
_SOURCE = re.compile(
    r"datasheets/|-ds\d{3}\b|\bdatasheet\b[^.]*?(?:§|Table|p\.\s*\d|page|section)|\b(?:py|ports|extmod|lib|shared|drivers)/[\w/.-]+\.[ch]\b|`[0-9a-f]{7,40}`",
    re.IGNORECASE,
)


def _in_scope(path: str) -> bool:
    return not is_shared_excluded(path) and path not in _SELF and not path.endswith(".txt")


def _sentences(block: Block) -> list[str]:
    """Split at ". " and "; " outside parentheses, so a tag's own "(owner, date; source)" stays whole."""
    text, sentences, start, depth = " ".join(block.lines), [], 0, 0
    for i, ch in enumerate(text):
        depth += (ch == "(") - (ch == ")")
        if ch in ".;" and depth <= 0 and text[i + 1 : i + 2] == " ":
            sentences.append(text[start : i + 1].strip())
            start = i + 1
    return [s for s in [*sentences, text[start:].strip()] if s]


def _is_hit(sentence: str) -> bool:
    return any(not _ACCEPTED_OBJECT.match(sentence, m.start()) for m in _VOCABULARY.finditer(sentence))


def _carries_actor(text: str) -> bool:
    return bool(_ACTOR_TAG.search(text) or _SOURCE.search(text))


def _prefix(sentence: str) -> str:
    return " ".join(sentence.split())[:_PREFIX_CHARS].rstrip()


def block_findings(block: Block) -> set[str]:
    if block.path == _LICENCE_FILE and block.lines[0].startswith((">", "```")):
        return set()
    head_tagged = _carries_actor(block.lines[0])
    return {_prefix(s) for s in _sentences(block) if _is_hit(s) and not head_tagged and not _carries_actor(s)}


def collect_findings() -> set[tuple[str, str]]:
    findings: set[tuple[str, str]] = set()
    for path in repo_files():
        if _in_scope(path) and (text := read_text(path)) is not None:
            findings.update((path, prefix) for block in prose_blocks(path, text) for prefix in block_findings(block))
    return findings


@pytest.fixture(scope="module")
def findings() -> set[tuple[str, str]]:
    return collect_findings()


def test_decision_vocabulary_names_its_actor_or_is_allow_listed(findings: set[tuple[str, str]]) -> None:
    new = sorted(findings - read_allowlist(ALLOWLIST))
    assert not new, "decision vocabulary with no '(owner|agent, YYYY-MM-DD)' tag or source - tag the sentence:\n" + "\n".join(f"  {p}: {s}" for p, s in new)


def test_the_allowlist_only_shrinks(findings: set[tuple[str, str]]) -> None:
    stale = sorted(read_allowlist(ALLOWLIST) - findings)
    assert not stale, "allow-list entries that no longer occur - delete these lines (or --regenerate):\n" + "\n".join(f"  {p}\t{s}" for p, s in stale)


def test_untagged_vocabulary_is_caught_and_tagged_vocabulary_passes() -> None:
    def hits(*lines: str) -> set[str]:
        return block_findings(Block("x.md", 1, lines))

    assert hits("This is settled. Nothing else.") == {"This is settled."}
    assert hits("This is settled (owner, 2026-09-26).") == set()
    assert hits("This is deliberately slow (agent, 2026-09-10; see below).") == set()
    assert hits("Accepted permanently (owner, 2026-09-26; see above) - a copy of an accepted risk.") == set()
    assert hits("Kept on purpose (owner, 2026-09-18):", "it is deliberate.") == set()
    assert hits("Do not re-raise this.") == {"Do not re-raise this."}
    assert hits("A value that must never be raised.") == {"A value that must never be raised."}
    assert hits("Fixed at the source in `3986be9`, by design.") == set()
    assert hits("The datasheet's Table 8 makes this deliberate.") == set()


def test_narrowings_keep_plain_usage_out() -> None:
    def hits(line: str) -> set[str]:
        return block_findings(Block("x.md", 1, (line,)))

    assert hits("An accepted PUT persists the value.") == set()
    assert hits("Connections accepted by the server are counted.") == set()
    assert hits("The timer never fires twice.") == set()
    assert hits("The value was accepted, and the log says so.") == {"The value was accepted, and the log says so."}


def _regenerate() -> None:
    write_allowlist(ALLOWLIST, _ALLOWLIST_HEADER, collect_findings())
    print(f"wrote {ALLOWLIST.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    if sys.argv[1:] != ["--regenerate"]:
        sys.exit("usage: uv run python tests_scripts/test_decision_vocabulary.py --regenerate")
    _regenerate()
