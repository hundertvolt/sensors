"""Decision vocabulary carries its actor (CLAUDE.md's decision-records rule 1): a sentence calling a thing
accepted, settled, decided or deliberate names who and when, or cites its source. Existing misses sit in
_decision_vocab_allowlist.txt, which only shrinks; `test_decision_vocabulary.py --regenerate` prunes it."""

import re
import sys
from collections import Counter
from pathlib import Path

import pytest
from _repo_scan import REPO_ROOT, Block, exit_on_new, is_shared_excluded, prose_blocks, read_allowlist, read_text, regenerate_allowlist, repo_files

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
    # Split at ". " and "; " outside parentheses, so a tag's own "(owner, date; source)" stays whole.
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


def block_findings(block: Block) -> list[str]:
    # One entry per hit sentence, so a repeat counts against the allow-list again.
    if block.path == _LICENCE_FILE and block.lines[0].startswith((">", "```")):
        return []
    head_tagged = _carries_actor(block.lines[0])
    return [_prefix(s) for s in _sentences(block) if _is_hit(s) and not head_tagged and not _carries_actor(s)]


def collect_findings() -> Counter[tuple[str, str]]:
    findings: Counter[tuple[str, str]] = Counter()
    for path in repo_files():
        if _in_scope(path) and (text := read_text(path)) is not None:
            findings.update((path, prefix) for block in prose_blocks(path, text) for prefix in block_findings(block))
    return findings


@pytest.fixture(scope="module")
def findings() -> Counter[tuple[str, str]]:
    return collect_findings()


def test_decision_vocabulary_names_its_actor_or_is_allow_listed(findings: Counter[tuple[str, str]]) -> None:
    new = sorted((findings - read_allowlist(ALLOWLIST)).elements())
    assert not new, "decision vocabulary with no '(owner|agent, YYYY-MM-DD)' tag or source - tag the sentence:\n" + "\n".join(f"  {p}: {s}" for p, s in new)


def test_the_allowlist_only_shrinks(findings: Counter[tuple[str, str]]) -> None:
    stale = sorted((read_allowlist(ALLOWLIST) - findings).elements())
    assert not stale, "allow-list entries that no longer occur - delete these lines (or --regenerate):\n" + "\n".join(f"  {p}\t{s}" for p, s in stale)


def test_untagged_vocabulary_is_caught_and_tagged_vocabulary_passes() -> None:
    def hits(*lines: str) -> list[str]:
        return block_findings(Block("x.md", 1, lines))

    assert hits("This is settled. Nothing else.") == ["This is settled."]
    assert hits("This is settled (owner, 2026-09-26).") == []
    assert hits("This is deliberately slow (agent, 2026-09-10; see below).") == []
    assert hits("Accepted permanently (owner, 2026-09-26; see above) - a copy of an accepted risk.") == []
    assert hits("Kept on purpose (owner, 2026-09-18):", "it is deliberate.") == []
    assert hits("Do not re-raise this.") == ["Do not re-raise this."]
    assert hits("A value that must never be raised.") == ["A value that must never be raised."]
    assert hits("Fixed at the source in `3986be9`, by design.") == []
    assert hits("The datasheet's Table 8 makes this deliberate.") == []


def test_narrowings_keep_plain_usage_out() -> None:
    def hits(line: str) -> list[str]:
        return block_findings(Block("x.md", 1, (line,)))

    assert hits("An accepted PUT persists the value.") == []
    assert hits("Connections accepted by the server are counted.") == []
    assert hits("The timer never fires twice.") == []
    assert hits("The value was accepted, and the log says so.") == ["The value was accepted, and the log says so."]


def test_each_hit_sentence_counts_once_per_occurrence() -> None:
    assert block_findings(Block("x.md", 1, ("This is settled. This is settled.",))) == ["This is settled.", "This is settled."]


def test_regenerate_refuses_a_new_finding_and_keeps_only_old_ones(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    listed = tmp_path / "allow.txt"
    listed.write_text("x.md\tOld and settled.\nx.md\tGone and settled.\n", encoding="utf-8")
    this = sys.modules[__name__]
    monkeypatch.setattr(this, "ALLOWLIST", listed)
    monkeypatch.setattr(this, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(this, "collect_findings", lambda: Counter([("x.md", "Old and settled."), ("x.md", "New and settled.")]))
    with pytest.raises(SystemExit, match="New and settled"):
        _regenerate()
    assert listed.read_text(encoding="utf-8").splitlines()[-1:] == ["x.md\tOld and settled."]


def _regenerate() -> None:
    new = regenerate_allowlist(ALLOWLIST, _ALLOWLIST_HEADER, collect_findings())
    exit_on_new(str(ALLOWLIST.relative_to(REPO_ROOT)), new)


if __name__ == "__main__":
    if sys.argv[1:] != ["--regenerate"]:
        sys.exit("usage: uv run python tests_scripts/test_decision_vocabulary.py --regenerate")
    _regenerate()
