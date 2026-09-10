"""Shared "specially formatted comment near a schema" scanning infrastructure: the mechanism
behind `# @requires` today and the planned `# @web`/`# @web-group` tags tomorrow, and the standing
rule that a near-miss attempt at one must fail the build loud (BUILD_CHAIN_PLAN.md's quality bar)."""

import re
import tokenize
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from buildgen.errors import BuildError


# Every comment-tag family this generator recognizes. Each carries its own "does this comment even
# look like an attempt at me" predicate, because the families have genuinely different payload
# shapes - an operator for @requires, a snake_case field name for @wiring - and a single shared
# heuristic would go blind on whichever shape it wasn't written for, which is exactly the silent
# miss this whole module exists to prevent. Add a family here and give it its own strict-grammar
# module alongside requires_tag.py/wiring_tag.py; @web/@web-group (BACKLOG.md) lands the same way.
def _looks_like_requires_payload(text: str) -> bool:
    if _PAYLOAD_OPERATOR_RE.search(text):
        return True
    return bool(_PAYLOAD_DOTTED_RE.search(text) and _PAYLOAD_NUMBER_RE.search(text))


def _payload_words(text: str) -> "tuple[bool, list[str]]":
    """Whether the comment carried the "@" sigil, plus whatever follows its leading word."""
    stripped = text.lstrip("#").strip()
    at_sign = stripped.startswith("@")
    if at_sign:
        stripped = stripped[1:].lstrip()
    m = _LEADING_WORD_RE.match(stripped)
    return at_sign, (stripped[m.end():].split() if m else [])


def _looks_like_wiring_payload(text: str) -> bool:
    # Every element of a wiring tag is a bare word, so sentence punctuation rules a comment out
    # immediately. Past that the bar depends on the sigil, because the two paths carry very
    # different false-positive risk: nobody writes "@wiring" in prose, so with the sigil any bare-
    # word payload counts as an attempt (which is what lets a tag with an element *dropped* still
    # be caught). Without it, "wiring is handled by the generator" is ordinary English, so a real
    # name shape - a snake_case TOML field or a CamelCase producer class - has to be present too.
    at_sign, words = _payload_words(text)
    if not words or not all(_PAYLOAD_WORD_RE.match(w) for w in words):
        return False
    if at_sign:
        return True
    return any(_PAYLOAD_SNAKE_RE.match(w) or _PAYLOAD_CAMEL_RE.match(w) for w in words)


def _looks_like_limits_payload(text: str) -> bool:
    # A limits tag is a field name followed by a range or a choice set, so either the payload
    # carries that punctuation ("1..3600", "in {0x76, 0x77}") or it is the bare field name whose
    # domain got dropped. "@limits are checked elsewhere in this file" is neither.
    _, words = _payload_words(text)
    if not words:
        return False
    if not _PAYLOAD_WORD_RE.match(words[0]):
        # No field name at all - an attempt only if what's left is recognisably a domain, so the
        # tag whose *field* was dropped ("@limits 1..3600") is still caught.
        return bool(_PAYLOAD_DOMAIN_START_RE.match(words[0]) and _PAYLOAD_RANGE_OR_SET_RE.search(" ".join(words)))
    if len(words) == 1:
        return True  # the field name survived but its domain was dropped - still an attempt
    # Past the field name a real domain opens with a number, an unbounded "*", or the "in" of a
    # choice set. "@limits are described in the matrix doc, section 5.2" opens with "described",
    # which is how ordinary prose stays out of this.
    return bool(_PAYLOAD_DOMAIN_START_RE.match(words[1]))


def _looks_like_requires_attempt(text: str) -> bool:
    # An exact "@requires" is strong evidence by itself, so a bare number is payload enough for it
    # ("@requires timeout 200000" - both the "bus." prefix and the operator dropped). This
    # leniency is specific to this family's number-shaped payload: applied to @limits it would read
    # "@limits are described in section 5.2" as a broken tag, so it lives here, not in the shared
    # scan. The other families need no equivalent - their own strict predicates already recognise
    # every partial tag, because any bare-word payload is one.
    return _looks_like_requires_payload(text) or bool(_PAYLOAD_NUMBER_RE.search(text))


@dataclass(frozen=True)
class TagSpec:
    name: str
    looks_like_payload: "Callable[[str], bool]"  # strict: gates typo matching against this name
    looks_like_attempt: "Callable[[str], bool] | None" = None  # looser: gates an exact name match

    def is_attempt(self, text: str) -> bool:
        return self.looks_like_attempt(text) if self.looks_like_attempt is not None else self.looks_like_payload(text)


KNOWN_TAGS = (
    TagSpec("requires", _looks_like_requires_payload, _looks_like_requires_attempt),
    TagSpec("wiring", _looks_like_wiring_payload),
    TagSpec("value-wiring", _looks_like_wiring_payload),
    TagSpec("limits", _looks_like_limits_payload),
)
KNOWN_TAG_NAMES = tuple(spec.name for spec in KNOWN_TAGS)

# Generous enough to catch one missing/extra/swapped letter (e.g. "require", "requries",
# "reqiures"), scaled down for a short tag name: two edits away from a 3-4 letter name (the planned
# "@web") is most of the dictionary, so a short name only tolerates one.
def _max_typo_distance(tag_name: str) -> int:
    return 1 if len(tag_name) <= 4 else 2

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
_PAYLOAD_SNAKE_RE = re.compile(r"^_*[a-z][a-z0-9]*_[a-z0-9_]+$")
_PAYLOAD_CAMEL_RE = re.compile(r"^_*[A-Z][A-Za-z0-9]*[a-z][A-Za-z0-9]*$")
_PAYLOAD_WORD_RE = re.compile(r"^[A-Za-z_][\w.-]*$")  # a bare word - no sentence punctuation
_PAYLOAD_RANGE_OR_SET_RE = re.compile(r"\.\.|\{")
_PAYLOAD_DOMAIN_START_RE = re.compile(r"^(in$|[-+*0-9])")
_LEADING_WORD_RE = re.compile(r"[A-Za-z_][\w-]*")

# Tokens that carry no statement indentation of their own, so they never update the running
# "is the current statement indented" answer iter_comment_tokens() tracks.
_NON_STATEMENT_TOKENS = frozenset({tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENCODING, tokenize.ENDMARKER})


@dataclass(frozen=True)
class CommentToken:
    lineno: int
    col: int
    text: str
    inside_block: bool  # inside a class/function body, i.e. NOT module level. Deliberately not the
    # token's own column (a trailing comment on a module-level statement starts well past 0) nor
    # bare physical indentation (a comment on a bracketed continuation line of a module-level
    # statement is indented, but is still module level) - see iter_comment_tokens().


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
    grammar) is never mistaken for a real comment. Each token carries whether it sits inside a
    class/function body rather than at module level."""
    tokens = []
    # Bracket depth, plus whether the statement that opened the current bracketing was itself
    # indented: inside brackets a comment's own line is always indented by style, so its physical
    # indentation says nothing about whether it sits at module level - the enclosing statement's
    # does. Outside brackets the line's own indentation is the answer, and INDENT/DEDENT depth is
    # not: the tokenizer emits no DEDENT for a comment line, so a module-level comment following an
    # indented block still reads as depth 1 there.
    depth = 0
    stmt_indented = False
    try:
        with path.open("rb") as f:  # tokenize decodes it itself, honoring a PEP 263 cookie/BOM
            for tok in tokenize.tokenize(f.readline):
                if tok.type == tokenize.COMMENT:
                    # tok.line is the tokenizer's own physical source line. Re-deriving it by
                    # indexing a str.splitlines() list would misalign: splitlines() also breaks on
                    # \x0b/\x0c/\u2028/..., which Python's tokenizer treats as ordinary characters,
                    # so a single such character anywhere earlier in the file shifted every later
                    # line by one and made valid module-level tags fail as "not at module level".
                    inside_block = stmt_indented if depth else tok.line[:1].isspace()
                    tokens.append(CommentToken(tok.start[0], tok.start[1], tok.string, inside_block))
                elif tok.type == tokenize.OP and tok.string in "()[]{}":
                    depth += 1 if tok.string in "([{" else -1
                elif not depth and tok.type not in _NON_STATEMENT_TOKENS:
                    stmt_indented = tok.line[:1].isspace()
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


def looks_like_tag_payload(comment_text: str, spec: "TagSpec | None"=None) -> bool:
    """Whether a comment carries the rough payload shape of a real tag - the gate that keeps
    ordinary prose merely *mentioning* a tag name from being treated as a broken tag. Defaults to
    @requires' own shape when no family is named."""
    if spec is None:
        return _looks_like_requires_payload(comment_text)
    return spec.looks_like_payload(comment_text)


def check_for_near_miss_tags(tokens: "list[CommentToken]", path: Path, device: str, instance_label: str, exact_matches: "set[tuple[int, int]]", specs: "tuple[TagSpec, ...] | None"=None) -> None:
    """Raises BuildError for any comment that looks like a typo'd or malformed attempt at one of
    KNOWN_TAG_NAMES but isn't one of the already-successfully-parsed tags at `exact_matches`
    ((lineno, col) pairs of the real, well-formed tags each tag module's own parser already found).
    This is the "present, or close to present" half of the standing rule (module docstring above):
    a real driver signature change once silently broke two frozen device scripts for a full day,
    undetected purely because nothing validated the comment that would have caught it (see
    tests_hardware/device_scripts/sgp40_voc_algorithm_quality.py's git history) - the same failure
    mode applies here if a typo'd @requires tag is just silently treated as "no tag present".

    `specs` narrows which families are policed. Each grammar module passes its own, so a perfectly
    valid tag of a *different* family isn't reported as a malformed one of this family - every
    family is still policed on every file, because validate.py runs all of the parsers over it."""
    for tok in tokens:
        if (tok.lineno, tok.col) in exact_matches:
            continue
        word, at_sign = find_leading_word(tok.text)
        if word is None:
            continue
        lower = word.lower()
        for spec in (KNOWN_TAGS if specs is None else specs):
            known = spec.name
            structured = spec.looks_like_payload(tok.text)
            # An exact tag name gets whatever leniency its own family allows; a merely typo'd word
            # never does - it needs the family's full strict shape.
            exact_evidence = spec.is_attempt(tok.text)
            if lower == known:
                if not exact_evidence:
                    break  # prose merely naming this tag - and not a typo of any other one either
                if at_sign:
                    raise BuildError(device, f"{path}:{tok.lineno}: malformed @{known} tag (doesn't match the required grammar): {tok.text.strip()!r}", instance=instance_label)
                raise BuildError(device, f"{path}:{tok.lineno}: comment looks like an @{known} tag with its leading '@' missing: {tok.text.strip()!r}", instance=instance_label)
            # A typo'd word is only ever a near miss *with* the sigil: "required"/"require" are
            # within edit distance 2 of "requires" but are also ordinary English a prose comment can
            # legitimately open with, so demanding the "@" there is what keeps this false-positive free.
            if at_sign and structured and _levenshtein(lower, known) <= _max_typo_distance(known):
                raise BuildError(device, f"{path}:{tok.lineno}: comment looks like a misspelled @{known} tag: {tok.text.strip()!r}", instance=instance_label)
