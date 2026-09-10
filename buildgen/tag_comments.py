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

# The rough shape every real tag's payload has, in two alternative forms - an identifier followed
# by a comparison-like operator (value deliberately optional, so a truncated "bus.timeout>=" still
# counts as an attempt), or a dotted reference plus a number (so a tag whose operator was dropped
# entirely, "bus.timeout 200000", isn't silently invisible either). Gates near-miss detection so an
# ordinary prose comment that happens to open with "@requires" (e.g. "@requires a bit more care
# here") is never mistaken for a malformed tag - see test_buildgen_tag_comments.py's
# false-positive coverage.
_PAYLOAD_OPERATOR_RE = re.compile(r"\b[\w.]+\s*(>=|<=|==|!=|=|>|<)")
_PAYLOAD_DOTTED_RE = re.compile(r"\b\w+\.\w+")
_PAYLOAD_NUMBER_RE = re.compile(r"(?<![\w.])[-+]?\d")

# A tag name is a word, optionally hyphenated (the planned "@web-group" shape) - anything after the
# first non-word character is payload, not part of the name.
_LEADING_WORD_RE = re.compile(r"[A-Za-z_][\w-]*")


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
    try:
        with tokenize.open(path) as src:  # honors a PEP 263 coding cookie/BOM, unlike read_text()
            lines = src.read().splitlines()
    except (UnicodeDecodeError, LookupError, SyntaxError) as e:
        raise BuildError(device, f"{path} has an unreadable text encoding: {e}", instance=instance_label) from e
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


def find_leading_word(comment_text: str) -> "tuple[str | None, bool]":
    """The comment's opening word plus whether it carried the "@" sigil - "@" itself is one of the
    dimensions a typo can drop, so the two are reported separately rather than the sigil being a
    precondition for seeing the word at all."""
    stripped = comment_text.lstrip("#").strip()
    at_sign = stripped.startswith("@")
    if at_sign:
        stripped = stripped[1:].lstrip()
    # The word stops at the first non-word character, so "@requires:"/"@requires(bus.x>=1)" still
    # read as "requires" rather than as some unrecognizable near-word.
    m = _LEADING_WORD_RE.match(stripped)
    return (m.group(0) if m else None, at_sign)


def find_tag_word(comment_text: str) -> "str | None":
    """Extracts the bare @-word from a comment (e.g. "requires" from "# @requires bus.x>=1").
    Returns None if the comment doesn't open with an @-word at all - not a tag attempt, just an
    ordinary comment that happens to contain "@" somewhere in its prose."""
    word, at_sign = find_leading_word(comment_text)
    return word if at_sign else None


def looks_like_tag_payload(comment_text: str) -> bool:
    """Whether a comment carries the rough field/operator/value shape of a real tag - the gate that
    keeps ordinary prose merely *mentioning* a tag name from being treated as a broken tag."""
    if _PAYLOAD_OPERATOR_RE.search(comment_text):
        return True
    return bool(_PAYLOAD_DOTTED_RE.search(comment_text) and _PAYLOAD_NUMBER_RE.search(comment_text))


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
        word, at_sign = find_leading_word(tok.text)
        if word is None:
            continue
        structured = looks_like_tag_payload(tok.text)
        # An exact tag name is strong evidence on its own, so a bare number is enough of a payload
        # for it ("@requires timeout 200000" - both the "bus." prefix and the operator dropped).
        # A merely typo'd word gets no such leniency: it needs the full structured shape.
        exact_evidence = structured or bool(_PAYLOAD_NUMBER_RE.search(tok.text))
        lower = word.lower()
        for known in KNOWN_TAG_NAMES:
            if lower == known:
                if not exact_evidence:
                    continue
                if at_sign:
                    raise BuildError(device, f"{path}:{tok.lineno}: malformed @{known} tag (doesn't match the required grammar): {tok.text.strip()!r}", instance=instance_label)
                raise BuildError(device, f"{path}:{tok.lineno}: comment looks like an @{known} tag with its leading '@' missing: {tok.text.strip()!r}", instance=instance_label)
            # A typo'd word is only ever a near miss *with* the sigil: "required"/"require" are
            # within edit distance 2 of "requires" but are also ordinary English a prose comment can
            # legitimately open with, so demanding the "@" there is what keeps this false-positive free.
            if at_sign and structured and _levenshtein(lower, known) <= _MAX_TYPO_DISTANCE:
                raise BuildError(device, f"{path}:{tok.lineno}: comment looks like a misspelled @{known} tag: {tok.text.strip()!r}", instance=instance_label)
