"""Tests for buildgen.tag_comments: the shared "specially formatted comment near a schema"
scanning infrastructure behind buildgen/requires_tag.py's `# @requires ...` tag (and, later, the
planned `# @web`/`# @web-group` website-definition tags - BACKLOG.md). Standing rule under test: a
typo'd or misplaced tag attempt must fail loud, never be silently treated as "no tag here"."""

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

from buildgen.errors import BuildError
from buildgen.tag_comments import (
    CommentToken,
    _levenshtein,
    check_for_near_miss_tags,
    find_leading_word,
    find_tag_word,
    iter_comment_tokens,
    looks_like_tag_payload,
)


def _tok(text: str, lineno: int = 1, col: int = 0, indented: bool = False) -> CommentToken:
    return CommentToken(lineno, col, text, indented)


def _check(tokens: "list[CommentToken]", exact: "set[tuple[int, int]] | None" = None) -> None:
    check_for_near_miss_tags(tokens, Path("x.py"), "dev", "x", exact or set())


# ---------------------------------------------------------------------------
# D1: comment scanning - what is a comment, where is it, and how does a bad file fail
# ---------------------------------------------------------------------------


def test_iter_comment_tokens_finds_a_real_comment(tmp_path: Path):
    path = tmp_path / "asy_x_driver.py"
    path.write_text("# a real comment\nx = 1\n")
    tokens = iter_comment_tokens(path, "dev", "x")
    assert len(tokens) == 1
    assert tokens[0] == CommentToken(1, 0, "# a real comment", False)


def test_iter_comment_tokens_ignores_hash_inside_string_literal(tmp_path: Path):
    # A naive per-line regex would mistake this for a comment - tokenize-based scanning knows it's
    # inside a string literal and correctly finds zero real comments.
    path = tmp_path / "asy_x_driver.py"
    path.write_text('x = "value # @requires bus.timeout>=200000"\n')
    assert iter_comment_tokens(path, "dev", "x") == []


def test_iter_comment_tokens_ignores_hash_inside_docstring(tmp_path: Path):
    # The multi-line sibling of the case above - this module's own docstring quotes tag grammar.
    path = tmp_path / "asy_x_driver.py"
    path.write_text('"""Doc.\n# @requires bus.timeout>=200000\n"""\nx = 1\n')
    assert iter_comment_tokens(path, "dev", "x") == []


def test_iter_comment_tokens_marks_indented_comment(tmp_path: Path):
    path = tmp_path / "asy_x_driver.py"
    path.write_text("class Foo:\n    def bar(self):\n        # indented comment\n        pass\n")
    tokens = iter_comment_tokens(path, "dev", "x")
    assert len(tokens) == 1
    assert tokens[0].line_indented is True


def test_iter_comment_tokens_marks_tab_indented_comment(tmp_path: Path):
    # Indentation is "the line has leading whitespace", not "the line starts with spaces".
    path = tmp_path / "asy_x_driver.py"
    path.write_text("def f():\n\t# tab-indented comment\n\tpass\n")
    assert iter_comment_tokens(path, "dev", "x")[0].line_indented is True


def test_iter_comment_tokens_trailing_inline_comment_on_module_level_statement_is_not_indented(tmp_path: Path):
    # The comment token's own column is > 0 (it starts after the code on the line), but the
    # statement itself is unindented - line_indented must reflect the *line's* own indentation, not
    # the token's column, or a legitimate trailing "_WIRING = (...)  # @requires ..." placement
    # would be wrongly rejected as "inside a class/function body".
    path = tmp_path / "asy_x_driver.py"
    path.write_text("_WIRING = ()  # trailing comment\n")
    tokens = iter_comment_tokens(path, "dev", "x")
    assert len(tokens) == 1
    assert tokens[0].col > 0
    assert tokens[0].line_indented is False


def test_iter_comment_tokens_reports_every_comment_in_source_order(tmp_path: Path):
    path = tmp_path / "asy_x_driver.py"
    path.write_text("#!/usr/bin/env python3\nx = 1  # first\n\n# second\ndef f():\n    # third\n    pass\n")
    tokens = iter_comment_tokens(path, "dev", "x")
    assert [(t.lineno, t.text, t.line_indented) for t in tokens] == [
        (1, "#!/usr/bin/env python3", False),
        (2, "# first", False),
        (4, "# second", False),
        (6, "# third", True),
    ]


def test_iter_comment_tokens_last_line_without_trailing_newline(tmp_path: Path):
    path = tmp_path / "asy_x_driver.py"
    path.write_text("x = 1\n# @requires bus.timeout>=200000")
    assert iter_comment_tokens(path, "dev", "x")[0].lineno == 2


def test_iter_comment_tokens_empty_file(tmp_path: Path):
    path = tmp_path / "asy_x_driver.py"
    path.write_text("")
    assert iter_comment_tokens(path, "dev", "x") == []


def test_iter_comment_tokens_handles_utf8_bom(tmp_path: Path):
    path = tmp_path / "asy_x_driver.py"
    path.write_bytes(b"\xef\xbb\xbf# @requires bus.timeout>=200000\nx = 1\n")
    assert iter_comment_tokens(path, "dev", "x")[0].text == "# @requires bus.timeout>=200000"


def test_iter_comment_tokens_honors_a_pep263_coding_cookie(tmp_path: Path):
    # Perfectly valid Python that a plain read_text() can't decode - the scan reads source the way
    # the interpreter does (cookie/BOM aware), so a legal driver file is never rejected for it.
    path = tmp_path / "asy_x_driver.py"
    path.write_bytes(b"# -*- coding: latin-1 -*-\n# caf\xe9\n# @requires bus.timeout>=200000\n")
    assert [t.text for t in iter_comment_tokens(path, "dev", "x")][1:] == ["# caf\xe9", "# @requires bus.timeout>=200000"]


def test_iter_comment_tokens_undecodable_source_fails_loud_not_a_raw_traceback(tmp_path: Path):
    # Non-UTF-8 bytes with no cookie declaring them: an abort either way, but it must surface as a
    # BuildError like every other one, not a raw UnicodeDecodeError traceback out of the generator.
    path = tmp_path / "asy_x_driver.py"
    path.write_bytes(b"# caf\xe9\nx = 1\n")
    with pytest.raises(BuildError, match="unreadable text encoding"):
        iter_comment_tokens(path, "dev", "x")


@pytest.mark.parametrize("source", ["x = ('unterminated\n", "x = (1,\n"])
def test_iter_comment_tokens_syntax_error_raises_build_error_not_raw_traceback(tmp_path: Path, source: str):
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
def test_find_leading_word(text: str, expected: "tuple[str | None, bool]"):
    assert find_leading_word(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("# @requires bus.timeout>=200000", "requires"),
        ("# @Requires bus.timeout>=200000", "Requires"),
        ("# @requires: bus.timeout>=200000", "requires"),
        ("# just a note", None),
        ("# see the @requires tag above", None),  # doesn't *open* with @ - mid-sentence mention
        ("# requires bus.timeout>=200000", None),  # no sigil - find_tag_word is the @-only view
        ("#", None),
        ("# @", None),
    ],
)
def test_find_tag_word(text: str, expected: "str | None"):
    assert find_tag_word(text) == expected


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
def test_levenshtein(a: str, b: str, expected: int):
    assert _levenshtein(a, b) == expected
    assert _levenshtein(b, a) == expected  # symmetric


# ---------------------------------------------------------------------------
# D3: payload shape - what separates a broken tag from prose that merely names one
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("op", [">=", "<=", "==", "!=", "=", ">", "<"])
def test_looks_like_tag_payload_every_operator(op: str):
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
def test_looks_like_tag_payload(text: str, expected: bool):
    assert looks_like_tag_payload(text) is expected


# ---------------------------------------------------------------------------
# D4: verdicts - which near-miss error fires, and what must stay silent
# ---------------------------------------------------------------------------


def test_check_for_near_miss_tags_flags_exact_keyword_bad_structure():
    with pytest.raises(BuildError, match="malformed @requires tag"):
        _check([_tok("# @requires timeout>=200000")])  # missing "bus." prefix


@pytest.mark.parametrize(
    "word",
    ["require", "requiress", "requirez", "requries", "requir"],  # delete/insert/substitute/transpose/distance-2
)
def test_check_for_near_miss_tags_flags_every_typo_shape(word: str):
    with pytest.raises(BuildError, match="misspelled @requires tag"):
        _check([_tok(f"# @{word} bus.timeout>=200000")])


def test_check_for_near_miss_tags_flags_wrong_case_as_the_exact_tag():
    # Case is folded before matching, so "@REQUIRES" is the exact tag spelled wrong, not a typo.
    with pytest.raises(BuildError, match="malformed @requires tag"):
        _check([_tok("# @REQUIRES bus.timeout>=200000")])


def test_check_for_near_miss_tags_flags_missing_at_sigil():
    with pytest.raises(BuildError, match="leading '@' missing"):
        _check([_tok("# requires bus.timeout>=200000")])


def test_check_for_near_miss_tags_flags_exact_keyword_with_only_a_number():
    # Both the "bus." prefix and the operator dropped - an exact tag name is strong enough evidence
    # on its own that a bare number counts as payload, or this would be silently invisible.
    with pytest.raises(BuildError, match="malformed @requires tag"):
        _check([_tok("# @requires timeout 200000")])


def test_check_for_near_miss_tags_flags_an_indented_near_miss_too():
    # Wrong location *and* wrong spelling still has to fail on the spelling - the location check
    # lives in each tag's own parser and only ever sees well-formed tags.
    with pytest.raises(BuildError, match="misspelled @requires tag"):
        _check([_tok("# @require bus.timeout>=200000", lineno=3, col=8, indented=True)])


def test_check_for_near_miss_tags_reports_the_offending_line_number():
    with pytest.raises(BuildError, match=r"x\.py:7:"):
        _check([_tok("# ordinary"), _tok("# @require bus.timeout>=200000", lineno=7)])


def test_check_for_near_miss_tags_ignores_prose_without_payload_shape():
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
def test_check_for_near_miss_tags_stays_silent(text: str):
    _check([_tok(text)])  # no raise


def test_check_for_near_miss_tags_skips_already_exact_matched_tokens():
    _check([_tok("# @requires bus.timeout>=200000")], exact={(1, 0)})  # no raise - already counted


def test_check_for_near_miss_tags_still_flags_a_second_bad_tag_beside_a_good_one():
    # The exact-match skip is per (lineno, col), not "this file already had a valid tag".
    tokens = [_tok("# @requires bus.timeout>=200000", lineno=1), _tok("# @require bus.frequency>=100000", lineno=2)]
    with pytest.raises(BuildError, match="misspelled @requires tag"):
        _check(tokens, exact={(1, 0)})


def test_check_for_near_miss_tags_empty_token_list():
    _check([])  # no raise
