"""Tests for buildgen.tag_comments, the shared "specially formatted comment near a schema"
scanner behind `# @requires` (and the planned `# @web`/`# @web-group` tags). Standing rule under
test: a typo'd or misplaced attempt must fail loud, never read as "no tag here"."""

# Matrix dimensions covered in this file (the shared mechanism, unit level - the full end-to-end
# grammar cross-product for the one real tag built on it lives in test_buildgen_requires_tag.py):
#   D1 scan     what counts as a real comment token at all (vs. a "#" inside a string/docstring),
#               where it sits (line, column, physical-line indentation), and how an unreadable or
#               unparseable source file fails.
#   D2 wording  the comment's leading word and its "@" sigil: exact, wrong case, each typo shape
#               (insert/delete/substitute/transpose), sigil missing, edit-distance boundary,
#               unrelated @-word, punctuation-suffixed word.
#   D3 payload  whether the rest of the comment carries a tag-shaped field/operator/value payload -
#               the gate that keeps ordinary prose merely mentioning a tag name from failing a build.
#   D4 verdict  which near-miss error each (wording x payload x sigil) combination raises, and every
#               combination that must stay silent.

from pathlib import Path

import pytest

from buildgen import tag_comments
from buildgen.errors import BuildError
from buildgen.tag_comments import CommentToken, _levenshtein, check_for_near_miss_tags, find_leading_word, iter_comment_tokens, looks_like_tag_payload


def _tok(text: str, lineno: int = 1, col: int = 0, *, indented: bool = False) -> CommentToken:
    return CommentToken(lineno, col, text, indented)


def _check(tokens: "list[CommentToken]", exact: "set[tuple[int, int]] | None" = None) -> None:
    check_for_near_miss_tags(tokens, Path("x.py"), "dev", "x", exact or set())


# ---------------------------------------------------------------------------
# D1: comment scanning - what is a comment, where is it, and how does a bad file fail
# ---------------------------------------------------------------------------


def test_iter_comment_tokens_finds_a_real_comment(tmp_path: Path) -> None:
    path = tmp_path / "asy_x_driver.py"
    path.write_text("# a real comment\nx = 1\n")
    tokens = iter_comment_tokens(path, "dev", "x")
    assert len(tokens) == 1
    assert tokens[0] == CommentToken(1, 0, "# a real comment", False)


def test_iter_comment_tokens_ignores_hash_inside_string_literal(tmp_path: Path) -> None:
    # A naive per-line regex would mistake this for a comment - tokenize-based scanning knows it's
    # inside a string literal and correctly finds zero real comments.
    path = tmp_path / "asy_x_driver.py"
    path.write_text('x = "value # @requires bus.timeout>=200000"\n')
    assert iter_comment_tokens(path, "dev", "x") == []


def test_iter_comment_tokens_ignores_hash_inside_docstring(tmp_path: Path) -> None:
    # The multi-line sibling of the case above - this module's own docstring quotes tag grammar.
    path = tmp_path / "asy_x_driver.py"
    path.write_text('"""Doc.\n# @requires bus.timeout>=200000\n"""\nx = 1\n')
    assert iter_comment_tokens(path, "dev", "x") == []


def test_iter_comment_tokens_marks_indented_comment(tmp_path: Path) -> None:
    path = tmp_path / "asy_x_driver.py"
    path.write_text("class Foo:\n    def bar(self):\n        # indented comment\n        pass\n")
    tokens = iter_comment_tokens(path, "dev", "x")
    assert len(tokens) == 1
    assert tokens[0].inside_block is True


def test_iter_comment_tokens_marks_tab_indented_comment(tmp_path: Path) -> None:
    # Indentation is "the line has leading whitespace", not "the line starts with spaces".
    path = tmp_path / "asy_x_driver.py"
    path.write_text("def f():\n\t# tab-indented comment\n\tpass\n")
    assert iter_comment_tokens(path, "dev", "x")[0].inside_block is True


def test_iter_comment_tokens_trailing_inline_comment_on_module_level_statement_is_not_indented(tmp_path: Path) -> None:
    # The comment token's own column is > 0 (it starts after the code on the line), but the
    # statement itself is unindented - inside_block must not be the token's column, or a legitimate
    # trailing "_WIRING = (...)  # @requires ..." placement would be wrongly rejected as "inside a
    # class/function body".
    path = tmp_path / "asy_x_driver.py"
    path.write_text("_WIRING = ()  # trailing comment\n")
    tokens = iter_comment_tokens(path, "dev", "x")
    assert len(tokens) == 1
    assert tokens[0].col > 0
    assert tokens[0].inside_block is False


def test_iter_comment_tokens_bracketed_continuation_line_at_module_level_is_not_inside_a_block(tmp_path: Path) -> None:
    # Inside a module-level statement's brackets the comment's own line is indented by style, but
    # the statement it belongs to is not - so physical indentation is the wrong question to ask.
    path = tmp_path / "asy_x_driver.py"
    path.write_text("_WIRING = (\n    # @requires bus.timeout>=200000\n)\n")
    (tok,) = iter_comment_tokens(path, "dev", "x")
    assert (tok.lineno, tok.inside_block) == (2, False)


def test_iter_comment_tokens_bracketed_continuation_line_inside_a_body_is_inside_a_block(tmp_path: Path) -> None:
    # The mirror image: same bracketed shape, but the enclosing statement is itself in a body.
    path = tmp_path / "asy_x_driver.py"
    path.write_text("def f():\n    x = (\n        # @requires bus.timeout>=200000\n    )\n")
    (tok,) = iter_comment_tokens(path, "dev", "x")
    assert (tok.lineno, tok.inside_block) == (3, True)


def test_iter_comment_tokens_module_level_comment_after_an_indented_block_is_not_inside_a_block(tmp_path: Path) -> None:
    # Guards the reason block depth can't simply be counted from INDENT/DEDENT: the tokenizer emits
    # no DEDENT for a comment line, so this comment is still "inside" the function by that measure.
    path = tmp_path / "asy_x_driver.py"
    path.write_text("def f():\n    pass\n# @requires bus.timeout>=200000\nx = 1\n")
    (tok,) = iter_comment_tokens(path, "dev", "x")
    assert (tok.lineno, tok.inside_block) == (3, False)


def test_iter_comment_tokens_statement_indentation_resets_after_brackets_close(tmp_path: Path) -> None:
    # The bracket-depth bookkeeping must unwind cleanly, or every comment after the first bracketed
    # module-level statement would inherit a stale answer.
    path = tmp_path / "asy_x_driver.py"
    path.write_text("_A = (\n    1,\n)\ndef f():\n    # inner\n    pass\n# outer\n")
    tokens = iter_comment_tokens(path, "dev", "x")
    assert [(t.text, t.inside_block) for t in tokens] == [("# inner", True), ("# outer", False)]


def test_iter_comment_tokens_reports_every_comment_in_source_order(tmp_path: Path) -> None:
    path = tmp_path / "asy_x_driver.py"
    path.write_text("#!/usr/bin/env python3\nx = 1  # first\n\n# second\ndef f():\n    # third\n    pass\n")
    tokens = iter_comment_tokens(path, "dev", "x")
    assert [(t.lineno, t.text, t.inside_block) for t in tokens] == [
        (1, "#!/usr/bin/env python3", False),
        (2, "# first", False),
        (4, "# second", False),
        (6, "# third", True),
    ]


def test_iter_comment_tokens_last_line_without_trailing_newline(tmp_path: Path) -> None:
    path = tmp_path / "asy_x_driver.py"
    path.write_text("x = 1\n# @requires bus.timeout>=200000")
    assert iter_comment_tokens(path, "dev", "x")[0].lineno == 2


def test_iter_comment_tokens_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "asy_x_driver.py"
    path.write_text("")
    assert iter_comment_tokens(path, "dev", "x") == []


def test_iter_comment_tokens_handles_utf8_bom(tmp_path: Path) -> None:
    path = tmp_path / "asy_x_driver.py"
    path.write_bytes(b"\xef\xbb\xbf# @requires bus.timeout>=200000\nx = 1\n")
    assert iter_comment_tokens(path, "dev", "x")[0].text == "# @requires bus.timeout>=200000"


def test_iter_comment_tokens_honors_a_pep263_coding_cookie(tmp_path: Path) -> None:
    # Perfectly valid Python that a plain read_text() can't decode - the scan reads source the way
    # the interpreter does (cookie/BOM aware), so a legal driver file is never rejected for it.
    path = tmp_path / "asy_x_driver.py"
    path.write_bytes(b"# -*- coding: latin-1 -*-\n# caf\xe9\n# @requires bus.timeout>=200000\n")
    assert [t.text for t in iter_comment_tokens(path, "dev", "x")][1:] == ["# caf\xe9", "# @requires bus.timeout>=200000"]


def test_iter_comment_tokens_undecodable_source_fails_loud_not_a_raw_traceback(tmp_path: Path) -> None:
    # Non-UTF-8 bytes with no cookie declaring them - Python's own tokenizer calls this a missing
    # encoding declaration. An abort either way, but it must surface as a BuildError like every
    # other one, not a raw decoding traceback out of the middle of the generator.
    path = tmp_path / "asy_x_driver.py"
    path.write_bytes(b"# caf\xe9\nx = 1\n")
    with pytest.raises(BuildError, match="encoding declaration"):
        iter_comment_tokens(path, "dev", "x")


def test_iter_comment_tokens_line_break_lookalike_does_not_shift_later_lines(tmp_path: Path) -> None:
    # Regression guard: str.splitlines() also breaks on \x0b/\x0c/\u2028/\u2029/\x85, which
    # Python's tokenizer treats as ordinary characters. Deriving each comment's physical line by
    # indexing a splitlines() list therefore shifted every line after one of those characters,
    # reporting an unindented module-level tag as indented - a valid driver rejected outright.
    path = tmp_path / "asy_x_driver.py"
    path.write_bytes(b"X = 'a\x0bb'\ndef f():\n    pass\n# @requires bus.timeout>=200000\n")
    (tok,) = iter_comment_tokens(path, "dev", "x")
    assert (tok.lineno, tok.inside_block) == (4, False)


@pytest.mark.parametrize("source", ["x = ('unterminated\n", "x = (1,\n"])
def test_iter_comment_tokens_syntax_error_raises_build_error_not_raw_traceback(tmp_path: Path, source: str) -> None:
    path = tmp_path / "asy_x_driver.py"
    path.write_text(source)
    with pytest.raises(BuildError, match="syntax error"):
        iter_comment_tokens(path, "dev", "x")


# ---------------------------------------------------------------------------
# D2: wording - the leading word and its "@" sigil
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("# @requires bus.timeout>=200000", ("requires", True)),
        ("#@requires bus.timeout>=200000", ("requires", True)),  # no space after the "#"
        ("#   @requires bus.timeout>=200000", ("requires", True)),  # wide gap after the "#"
        ("## @requires bus.timeout>=200000", ("requires", True)),  # section-style double hash
        ("# @ requires bus.timeout>=200000", ("requires", True)),  # sigil split off the word
        ("# @requires: bus.timeout>=200000", ("requires", True)),
        ("# @requires(bus.timeout>=200000)", ("requires", True)),  # word ends at the first non-word char
        ("# @Requires bus.timeout>=200000", ("Requires", True)),  # case preserved, not folded here
        ("# @web-group name=x", ("web-group", True)),  # hyphenated future tag shape
        ("# requires bus.timeout>=200000", ("requires", False)),  # sigil dropped entirely
        ("# just a note", ("just", False)),
        ("# see the @requires tag above", ("see", False)),
        ("#", (None, False)),
        ("# @", (None, True)),
        ("# 200000 is the floor", (None, False)),  # a digit doesn't open a tag name
    ],
)
def test_find_leading_word(text: str, expected: "tuple[str | None, bool]") -> None:
    assert find_leading_word(text) == expected


@pytest.mark.parametrize(
    "a,b,expected",
    [
        ("requires", "requires", 0),
        ("", "requires", 8),
        ("requires", "", 8),
        ("require", "requires", 1),  # deletion
        ("requiress", "requires", 1),  # insertion
        ("requirez", "requires", 1),  # substitution
        ("requries", "requires", 2),  # transposition (two single-char edits)
        ("requir", "requires", 2),  # two deletions - the tolerance boundary
        ("requi", "requires", 3),  # three deletions - just outside it
        ("param", "requires", 7),
    ],
)
def test_levenshtein(a: str, b: str, expected: int) -> None:
    assert _levenshtein(a, b) == expected
    assert _levenshtein(b, a) == expected  # symmetric


# ---------------------------------------------------------------------------
# D3: payload shape - what separates a broken tag from prose that merely names one
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("op", [">=", "<=", "==", "!=", "=", ">", "<"])
def test_looks_like_tag_payload_every_operator(op: str) -> None:
    assert looks_like_tag_payload(f"# @requires bus.timeout{op}200000") is True


@pytest.mark.parametrize(
    "text,expected",
    [
        ("# @requires bus.timeout >= 200000", True),  # spaced operator
        ("# @requires bus.timeout>=", True),  # operator present, value truncated away
        ("# @requires timeout>=200000", True),  # "bus." prefix dropped, operator still there
        ("# @requires bus.timeout 200000", True),  # operator dropped, dotted ref + number remain
        ("# @requires bus.timeout", False),  # dotted ref alone - no operator, no value
        ("# @requires 200000", False),  # number alone - nothing that names a field
        ("# @requires tag, not here).", False),  # the real prose collision in buildgen/validate.py
        ("# @requires a bit more care here", False),
    ],
)
def test_looks_like_tag_payload(text: str, *, expected: bool) -> None:
    assert looks_like_tag_payload(text) is expected


# ---------------------------------------------------------------------------
# D4: verdicts - which near-miss error fires, and what must stay silent
# ---------------------------------------------------------------------------


def test_check_for_near_miss_tags_flags_exact_keyword_bad_structure() -> None:
    with pytest.raises(BuildError, match="malformed @requires tag"):
        _check([_tok("# @requires timeout>=200000")])  # missing "bus." prefix


@pytest.mark.parametrize(
    "word",
    ["require", "requiress", "requirez", "requries", "requir"],  # delete/insert/substitute/transpose/distance-2
)
def test_check_for_near_miss_tags_flags_every_typo_shape(word: str) -> None:
    with pytest.raises(BuildError, match="misspelled @requires tag"):
        _check([_tok(f"# @{word} bus.timeout>=200000")])


def test_check_for_near_miss_tags_flags_wrong_case_as_the_exact_tag() -> None:
    # Case is folded before matching, so "@REQUIRES" is the exact tag spelled wrong, not a typo.
    with pytest.raises(BuildError, match="malformed @requires tag"):
        _check([_tok("# @REQUIRES bus.timeout>=200000")])


def test_check_for_near_miss_tags_flags_missing_at_sigil() -> None:
    with pytest.raises(BuildError, match="leading '@' missing"):
        _check([_tok("# requires bus.timeout>=200000")])


def test_check_for_near_miss_tags_flags_exact_keyword_with_only_a_number() -> None:
    # Both the "bus." prefix and the operator dropped - an exact tag name is strong enough evidence
    # on its own that a bare number counts as payload, or this would be silently invisible.
    with pytest.raises(BuildError, match="malformed @requires tag"):
        _check([_tok("# @requires timeout 200000")])


def test_check_for_near_miss_tags_flags_an_indented_near_miss_too() -> None:
    # Wrong location *and* wrong spelling still has to fail on the spelling - the location check
    # lives in each tag's own parser and only ever sees well-formed tags.
    with pytest.raises(BuildError, match="misspelled @requires tag"):
        _check([_tok("# @require bus.timeout>=200000", lineno=3, col=8, indented=True)])


def test_check_for_near_miss_tags_reports_the_offending_line_number() -> None:
    with pytest.raises(BuildError, match=r"x\.py:7:"):
        _check([_tok("# ordinary"), _tok("# @require bus.timeout>=200000", lineno=7)])


def test_check_for_near_miss_tags_ignores_prose_without_payload_shape() -> None:
    # Mirrors a real near-collision found in this repo (buildgen/validate.py's own comment: "...
    # required by that driver's own @requires tag, not here)." wrapped across #-lines) - a comment
    # that opens with "@requires" but carries no field/operator/value shape at all must never be
    # flagged, or ordinary prose mentioning the tag by name would break every build.
    _check([_tok("# @requires tag, not here).")])  # no raise


@pytest.mark.parametrize(
    "text",
    [
        "# @param bus.timeout>=200000",  # unrelated @-word, distance 8 from "requires"
        "# @requi bus.timeout>=200000",  # distance 3 - just outside the typo tolerance
        "# required bus.timeout>=200000",  # typo'd *and* sigil-less: ordinary English prose
        "# require bus.timeout>=200000",  # same - a typo alone is only a near miss with the sigil
        "# @requires",  # bare word, no payload at all
        "#",
    ],
)
def test_check_for_near_miss_tags_stays_silent(text: str) -> None:
    _check([_tok(text)])  # no raise


def test_check_for_near_miss_tags_skips_already_exact_matched_tokens() -> None:
    _check([_tok("# @requires bus.timeout>=200000")], exact={(1, 0)})  # no raise - already counted


def test_check_for_near_miss_tags_still_flags_a_second_bad_tag_beside_a_good_one() -> None:
    # The exact-match skip is per (lineno, col), not "this file already had a valid tag".
    tokens = [_tok("# @requires bus.timeout>=200000", lineno=1), _tok("# @require bus.frequency>=100000", lineno=2)]
    with pytest.raises(BuildError, match="misspelled @requires tag"):
        _check(tokens, exact={(1, 0)})


def test_check_for_near_miss_tags_empty_token_list() -> None:
    _check([])  # no raise


def test_check_for_near_miss_tags_typo_tolerance_narrows_for_a_short_tag_name(monkeypatch: pytest.MonkeyPatch) -> None:
    # Two edits away from a 3-letter name is most of the dictionary, so a short tag name (the
    # planned "@web") tolerates only one - otherwise adding it to the registry would start failing
    # builds over unrelated @-words. "wet" is one edit from "web"; "wed"/"we" would be too.
    web = tag_comments.TagSpec("web", tag_comments.looks_like_tag_payload)
    monkeypatch.setattr(tag_comments, "KNOWN_TAGS", (web,))
    with pytest.raises(BuildError, match="misspelled @web tag"):
        _check([_tok("# @wet name=x")])
    _check([_tok("# @net name=x")])  # two edits away - no raise


def test_known_tag_names_mirrors_the_registry() -> None:
    # KNOWN_TAG_NAMES is the convenience view; KNOWN_TAGS is the real registry the scan walks.
    assert tuple(spec.name for spec in tag_comments.KNOWN_TAGS) == tag_comments.KNOWN_TAG_NAMES


@pytest.mark.parametrize(
    "text,family,expected",
    [
        ("# @wiring fram_target AsyFramManager fram optional kwarg", "wiring", True),
        # With the sigil, any bare-word payload counts - that is what catches a tag whose elements
        # were dropped, at the accepted cost of flagging the prose nobody writes ("@wiring is what
        # this module needs"). Sentence punctuation still rules a comment out immediately.
        ("# @wiring is what this module needs, more of it", "wiring", False),
        ("# wiring is what this module needs more of", "wiring", False),
        ("# @value-wiring temperature_source temperature_source temperature_field required", "value-wiring", True),
        ("# @limits trigger_sec 1..3600", "limits", True),
        ("# @limits address in {0x76, 0x77}", "limits", True),
        ("# @limits are checked elsewhere in this file", "limits", False),
        ("# @requires bus.timeout>=200000", "requires", True),
        ("# @requires a bit more care here", "requires", False),
    ],
)
def test_each_family_recognizes_its_own_payload_shape_and_not_prose(text: str, family: str, *, expected: bool) -> None:
    # A single shared heuristic would go blind on whichever shape it wasn't written for - the exact
    # silent miss the near-miss detector exists to prevent - so each family gates on its own shape.
    (spec,) = [s for s in tag_comments.KNOWN_TAGS if s.name == family]
    assert spec.looks_like_payload(text) is expected


def test_looks_like_tag_payload_accepts_an_explicit_family(tmp_path: Path) -> None:
    # The helper defaults to @requires' own shape; passing a family switches it to that family's
    # predicate, which is how each grammar module gates its own near-miss detection.
    (wiring,) = [s for s in tag_comments.KNOWN_TAGS if s.name == "wiring"]
    text = "# @wiring fram_target AsyFramManager fram optional kwarg"
    assert tag_comments.looks_like_tag_payload(text, wiring) is True
    assert tag_comments.looks_like_tag_payload(text) is False  # no operator - not @requires-shaped
