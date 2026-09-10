"""Tests for buildgen.tag_comments: the shared "specially formatted comment near a schema"
scanning infrastructure behind buildgen/requires_tag.py's `# @requires ...` tag (and, later, the
planned `# @web`/`# @web-group` website-definition tags - BACKLOG.md). Standing rule under test: a
typo'd or misplaced tag attempt must fail loud, never be silently treated as "no tag here"."""

from pathlib import Path

import pytest

from buildgen.errors import BuildError
from buildgen.tag_comments import CommentToken, check_for_near_miss_tags, find_tag_word, iter_comment_tokens


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


def test_iter_comment_tokens_marks_indented_comment(tmp_path: Path):
    path = tmp_path / "asy_x_driver.py"
    path.write_text("class Foo:\n    def bar(self):\n        # indented comment\n        pass\n")
    tokens = iter_comment_tokens(path, "dev", "x")
    assert len(tokens) == 1
    assert tokens[0].line_indented is True


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


def test_iter_comment_tokens_syntax_error_raises_build_error_not_raw_traceback(tmp_path: Path):
    path = tmp_path / "asy_x_driver.py"
    path.write_text("x = ('unterminated\n")
    with pytest.raises(BuildError, match="syntax error"):
        iter_comment_tokens(path, "dev", "x")


@pytest.mark.parametrize(
    "text,expected",
    [
        ("# @requires bus.timeout>=200000", "requires"),
        ("# @Requires bus.timeout>=200000", "Requires"),
        ("# @requires: bus.timeout>=200000", "requires"),
        ("# just a note", None),
        ("# see the @requires tag above", None),  # doesn't *open* with @ - mid-sentence mention
        ("#", None),
        ("# @", None),
    ],
)
def test_find_tag_word(text: str, expected: "str | None"):
    assert find_tag_word(text) == expected


def test_check_for_near_miss_tags_ignores_prose_without_payload_shape():
    # Mirrors a real near-collision found in this repo (buildgen/validate.py's own comment: "...
    # required by that driver's own @requires tag, not here)." wrapped across #-lines) - a comment
    # that opens with "@requires" but carries no field/operator/value shape at all must never be
    # flagged, or ordinary prose mentioning the tag by name would break every build.
    tok = CommentToken(1, 0, "# @requires tag, not here).", False)
    check_for_near_miss_tags([tok], Path("x.py"), "dev", "x", set())  # no raise


def test_check_for_near_miss_tags_flags_exact_keyword_bad_structure():
    tok = CommentToken(1, 0, "# @requires timeout>=200000", False)  # missing "bus." prefix
    with pytest.raises(BuildError, match="malformed @requires tag"):
        check_for_near_miss_tags([tok], Path("x.py"), "dev", "x", set())


def test_check_for_near_miss_tags_flags_typo_within_distance():
    tok = CommentToken(1, 0, "# @require bus.timeout>=200000", False)  # missing "s"
    with pytest.raises(BuildError, match="misspelled @requires tag"):
        check_for_near_miss_tags([tok], Path("x.py"), "dev", "x", set())


def test_check_for_near_miss_tags_ignores_unrelated_at_word():
    tok = CommentToken(1, 0, "# @param bus.timeout>=200000", False)  # not close to "requires"
    check_for_near_miss_tags([tok], Path("x.py"), "dev", "x", set())  # no raise


def test_check_for_near_miss_tags_skips_already_exact_matched_tokens():
    tok = CommentToken(1, 0, "# @requires bus.timeout>=200000", False)
    check_for_near_miss_tags([tok], Path("x.py"), "dev", "x", {(1, 0)})  # no raise - already counted
