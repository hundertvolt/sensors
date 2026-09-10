"""Shared "specially formatted comment near a schema" scanning infrastructure - the general
mechanism behind buildgen/requires_tag.py's `# @requires ...` tags today, and the planned
`# @web`/`# @web-group` website-definition tags (BACKLOG.md's "Website definitions-file
autogeneration" sketch) tomorrow. Standing rule (project owner's explicit direction, not just for
`@requires`): a typo'd or misplaced attempt at one of these tags must never be silently invisible -
a comment that's present, or close to present, must be verified correct in every dimension (exact
wording, location, format, content) or fail the build loud - never silently treated as "no tag
here, nothing to check". See check_for_near_miss_tags()'s own docstring for the concrete incident
this generalizes from.
"""

import re
import tokenize
from dataclasses import dataclass
from pathlib import Path

from buildgen.errors import BuildError

# Every comment-tag name this generator currently recognizes, by its bare @-word (no leading "@").
# Extend this set - and give the new tag its own strict-grammar module alongside requires_tag.py -
# the day the @web/@web-group website-definition parser (BACKLOG.md) actually gets built.
KNOWN_TAG_NAMES = ("requires",)

# Generous enough to catch one missing/extra/swapped letter (e.g. "require", "requries",
# "reqiures"), not so wide it starts matching unrelated short @-words by coincidence.
_MAX_TYPO_DISTANCE = 2

# A (dotted-or-bare) identifier followed by a comparison-like operator and a value - the rough
# shape every real tag's payload has, loose enough to survive a missing dot or a bare "=" typo.
# Gates near-miss detection so an ordinary prose comment that happens to open with "@requires"
# (e.g. "@requires a bit more care here") is never mistaken for a malformed tag - see
# test_buildgen_tag_comments.py's false-positive coverage.
_TAG_PAYLOAD_SHAPE_RE = re.compile(r"\b[\w.]+\s*(>=|<=|==|!=|=|>|<)\s*\S+")


@dataclass(frozen=True)
class CommentToken:
    lineno: int
    col: int
    text: str
    line_indented: bool  # the physical source line's own leading whitespace - not just this
    # token's own column, so a trailing inline comment on a module-level statement (col > 0 but
    # the statement itself is unindented) doesn't get mistaken for "inside a class/function body".


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, start=1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
        prev = cur
    return prev[-1]


def iter_comment_tokens(path: Path, device: str, instance_label: str) -> "list[CommentToken]":
    """Every real COMMENT token in `path` - tokenize-based, not a naive per-line regex, so a "#"
    inside a string/docstring (e.g. this very module's own docstring, which quotes example tag
    grammar) is never mistaken for a real comment."""
    lines = path.read_text().splitlines()
    tokens = []
    try:
        with path.open("rb") as f:
            for tok in tokenize.tokenize(f.readline):
                if tok.type != tokenize.COMMENT:
                    continue
                lineno, col = tok.start
                line = lines[lineno - 1] if 0 < lineno <= len(lines) else ""
                indented = line[: len(line) - len(line.lstrip())] != ""
                tokens.append(CommentToken(lineno, col, tok.string, indented))
    except (tokenize.TokenError, SyntaxError, IndentationError) as e:
        raise BuildError(device, f"{path} has a syntax error: {e}", instance=instance_label) from e
    return tokens


def find_tag_word(comment_text: str) -> "str | None":
    """Extracts the bare @-word from a comment (e.g. "requires" from "# @requires bus.x>=1").
    Returns None if the comment doesn't open with an @-word at all - not a tag attempt, just an
    ordinary comment that happens to contain "@" somewhere in its prose."""
    stripped = comment_text.lstrip("#").strip()
    if not stripped.startswith("@"):
        return None
    word = stripped[1:].split(None, 1)[0] if len(stripped) > 1 else ""
    word = word.rstrip(":()[]{}")  # a stray "@requires:"/"@requires(" trailing punctuation
    return word or None


def check_for_near_miss_tags(tokens: "list[CommentToken]", path: Path, device: str, instance_label: str, exact_matches: "set[tuple[int, int]]") -> None:
    """Raises BuildError for any comment that looks like a typo'd or malformed attempt at one of
    KNOWN_TAG_NAMES but isn't one of the already-successfully-parsed tags at `exact_matches`
    ((lineno, col) pairs of the real, well-formed tags each tag module's own parser already found).
    This is the "present, or close to present" half of the standing rule (module docstring above):
    a real driver signature change once silently broke two frozen device scripts for a full day,
    undetected purely because nothing validated the comment that would have caught it (see
    tests_hardware/device_scripts/sgp40_voc_algorithm_quality.py's git history) - the same failure
    mode applies here if a typo'd @requires tag is just silently treated as "no tag present"."""
    for tok in tokens:
        if (tok.lineno, tok.col) in exact_matches:
            continue
        word = find_tag_word(tok.text)
        if word is None or not _TAG_PAYLOAD_SHAPE_RE.search(tok.text):
            continue
        lower = word.lower()
        for known in KNOWN_TAG_NAMES:
            if lower == known:
                raise BuildError(device, f"{path}:{tok.lineno}: malformed @{known} tag (doesn't match the required grammar): {tok.text.strip()!r}", instance=instance_label)
            if _levenshtein(lower, known) <= _MAX_TYPO_DISTANCE:
                raise BuildError(device, f"{path}:{tok.lineno}: comment looks like a misspelled @{known} tag: {tok.text.strip()!r}", instance=instance_label)
