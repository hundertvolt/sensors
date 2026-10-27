"""prose_blocks()'s reader of // and /* */ comments skips a JS regex literal as it skips a string, so a quote inside one
hides none of the comments after it; a "/" where a value ends (a division) is never taken for one."""

import pytest
from _repo_scan import prose_blocks


def _comments(path: str, text: str) -> list[tuple[int, tuple[str, ...]]]:
    return sorted((block.line, block.lines) for block in prose_blocks(path, text))


@pytest.mark.parametrize(
    "statement",
    [
        'const quoted = /"(\\w+)/u;',
        "const either = /['\"]/g;",
        'const slash = /a\\/"b/;',
        'const inClass = /[/"]/;',
        'call(/"/, 1);',
        'const pick = flag ? /"/ : /x/;',
        'const list = [/"/];',
        'const map = { key: /"/ };',
        'if (!/"/.test(s)) {}',
        'const both = a && /"/.test(s);',
        'function f(s) { return /"/.test(s); }',
        '/"/.test(s);',
        'if (s) {} /"/.test(s);',
    ],
)
def test_a_regex_holding_a_quote_hides_no_comment_after_it(statement: str) -> None:
    text = f"{statement} // same line\n/* own block */\n// own line\n"
    assert _comments("x.js", text) == [(1, ("same line",)), (2, ("own block",)), (3, ("own line",))]


@pytest.mark.parametrize(
    "statement",
    [
        "const half = total / 2;",
        "const mean = (a + b) / 2;",
        "const part = list[0] / 2;",
        "const next = n++ / 2;",
        "const ratio = a / b / c;",
        "const scaled = 3 / 2;",
        "const typed = /** @type {number} */ (x) / 2;",
    ],
)
def test_a_division_is_not_taken_for_a_regex(statement: str) -> None:
    # Read as a regex, the "/" would run to the comment's own first "/" and swallow it.
    text = f"{statement} // after the division\n"
    assert [lines for _, lines in _comments("x.js", text) if lines != ("@type {number}",)] == [("after the division",)]


def test_a_slash_that_opens_no_regex_closing_on_its_line_is_a_plain_character() -> None:
    # A regex literal never spans a line break, so a "/" read as one that is still open at its line's end was not one.
    assert _comments("x.ts", 'const odd = {} / 2; const s = "a";\n// kept\n') == [(2, ("kept",))]


def test_a_stylesheet_has_no_regex_literal() -> None:
    assert _comments("x.css", 'a { background: url("x/y"); } /* kept */\n') == [(1, ("kept",))]
