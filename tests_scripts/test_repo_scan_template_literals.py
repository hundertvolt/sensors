"""prose_blocks()'s reader of // and /* */ comments reads a template literal's `${...}` substitution as code, as at top
level, so a comment there is found and one written inside the template's own text is not; a "${" opens one only where
a template literal's text holds it unescaped."""

import pytest
from _repo_scan import prose_blocks


def _comments(text: str) -> list[tuple[int, tuple[str, ...]]]:
    return sorted((block.line, block.lines) for block in prose_blocks("x.js", text))


@pytest.mark.parametrize(
    "statement",
    [
        "const s = `a ${/** @type {string} */ (x)} b`;",
        "const s = `a ${f(x, /* found */ y)} b`;",
        "const s = `a ${f({ k: 1 }, /* found */ y)} b`;",
        'const s = `a ${f("}", /* found */ y)} b`;',
        "const s = `a ${f('}', /* found */ y)} b`;",
        "const s = `a ${s.replace(/[}]/g, /* found */ y)} b`;",
        "const s = `a ${s.replace(/}/g, /* found */ y)} b`;",
        "const s = `a ${f(`b`, /* found */ y)} b`;",
        "const s = `a ${f(`b ${c}`, /* found */ y)} b`;",
        "const s = `a ${f(`b ${g(`c`)}`, /* found */ y)} b`;",
        "const s = `a ${(() => { return 1; })() + /* found */ y} b`;",
        "const s = `a ${x} b ${/* found */ y} c`;",
    ],
)
def test_a_comment_inside_a_substitution_is_found(statement: str) -> None:
    inside = ("@type {string}",) if "@type" in statement else ("found",)
    assert _comments(f"{statement} // after\n") == sorted([(1, inside), (1, ("after",))])


def test_an_own_line_comment_in_a_substitution_spanning_lines_is_found_on_its_row() -> None:
    text = "const s = `a ${\n    // inside\n    /* also\n       inside */\n    x\n} b`;\n// after\n"
    assert _comments(text) == [(2, ("inside",)), (3, ("also", "inside")), (7, ("after",))]


@pytest.mark.parametrize(
    "statement",
    [
        "const s = `a ${`/* not a comment */`} b`;",
        "const s = `a ${f(`b ${c} /* not a comment */`)} b`;",
        "const s = `a ${x} /* not a comment */ ${y} b`;",
        "const s = `a ${f('}')} /* not a comment */ b`;",
        "const s = `a ${f({ k: '{' })} /* not a comment */ b`;",
    ],
)
def test_a_comment_in_the_text_of_a_template_around_a_substitution_is_not_one(statement: str) -> None:
    assert _comments(f"{statement}\n// after\n") == [(2, ("after",))]


@pytest.mark.parametrize(
    "statement",
    [
        "const s = `a ${x} it's`;",
        "const s = `a ${f(`b ${c} it's`)} it's`;",
        'const s = `a ${f("q")} say "x`;',
    ],
)
def test_a_quote_in_the_text_after_a_substitution_opens_no_string(statement: str) -> None:
    assert _comments(f"{statement} // after\n/* own */\n") == [(1, ("after",)), (2, ("own",))]


@pytest.mark.parametrize(
    "statement",
    [
        'const s = "${ /* not a comment */ }";',
        "const s = '${ /* not a comment */ }';",
        "const s = `\\${ /* not a comment */ }`;",
        "const s = `$x /* not a comment */ {y}`;",
        "const s = `$ { /* not a comment */ }`;",
        "const s = `$\\{ /* not a comment */ }`;",
    ],
)
def test_a_dollar_brace_opens_no_substitution_outside_a_template_text_or_escaped(statement: str) -> None:
    assert _comments(f"{statement}\n// after\n") == [(2, ("after",))]


def test_a_regex_may_open_a_substitution() -> None:
    # Right after "${" an expression starts, so a "/" there opens a regex literal and its quote opens no string; the tag
    # before the template is a value's end, after which a "/" would divide.
    assert _comments('const s = tag`${/"/.test(x) ? 1 : 2}`; // after\n') == [(1, ("after",))]
