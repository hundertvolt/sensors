"""Tests for buildgen.requires_tag: the `# @requires bus.<field><op><value>` comment-tag parser
and enforcement (BUILD_CHAIN_PLAN.md's "Build/generator script quality bar"). Covers the real
SCD30 clock-stretch tag this session added plus every malformed/violated case."""

# Matrix dimensions for the one real tag built on buildgen/tag_comments.py's shared mechanism
# (whose own unit-level coverage is test_buildgen_tag_comments.py). The accept side is covered as a
# full cross-product where dimensions genuinely interact, since a build that silently accepts the
# wrong thing is the failure mode the whole tag exists to prevent; the reject side covers each
# dimension once rather than recombining - a build that aborts, aborts.
#   D1 operator     >= <= == != > <
#   D2 value        int / zero / negative / underscored / float / negative float / exponent
#   D3 format       spacing around "#", the tag word, the dot and the operator; "##" section style
#   D4 location     top of file, after a docstring, among imports, trailing inline on a module-level
#                   statement, last line with no trailing newline, next to _WIRING
#   D5 multiplicity none, one, several (distinct fields, repeated field, exact duplicates), mixed in
#                   with ordinary comments and strings that merely contain tag-shaped text
#   D6 field name   plain, underscored, digit-bearing
#   D7 enforcement  each operator satisfied and violated against a real bus table, plus missing
#                   field, falsy-but-present value, and non-comparable types

from pathlib import Path

import pytest

from buildgen.errors import BuildError
from buildgen.requires_tag import RequiresTag, check_requires_tags, parse_requires_tags

_OPS = [">=", "<=", "==", "!=", ">", "<"]

_VALUES = [
    ("200000", 200000, int),
    ("0", 0, int),
    ("-5", -5, int),
    ("1_000", 1000, int),  # Python's own numeric-literal underscore grouping, via int()
    ("50000.5", 50000.5, float),
    ("-0.25", -0.25, float),
    ("2e5", 200000.0, float),
]


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


def _parse(tmp_path: Path, source: str) -> "tuple[RequiresTag, ...]":
    path = tmp_path / "asy_x_driver.py"
    path.write_text(source)
    return parse_requires_tags(path, "dev", "x")


def _parse_expecting(tmp_path: Path, source: str, match: str) -> None:
    with pytest.raises(BuildError, match=match):
        _parse(tmp_path, source)


# ---------------------------------------------------------------------------
# D1 x D2: every operator against every value shape. These two genuinely interact - the operator
# alternation and the value pattern share a boundary, and a naive value pattern re-splits
# "bus.x>=-5" into op ">" / value "=-5" or swallows the "=" of ">=" - so this one is a full cross.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("op", _OPS)
@pytest.mark.parametrize("raw,expected,expected_type", _VALUES)
def test_parse_requires_tags_operator_value_cross_product(tmp_path: Path, op: str, raw: str, expected: "int | float", expected_type: type) -> None:
    (tag,) = _parse(tmp_path, f"# @requires bus.timeout{op}{raw}\n")
    assert (tag.field, tag.op, tag.value) == ("timeout", op, expected)
    assert type(tag.value) is expected_type  # int stays int - "0" must not silently become 0.0
    assert tag.raw == f"# @requires bus.timeout{op}{raw}"


# ---------------------------------------------------------------------------
# D3: format/spacing variants that must all parse to the identical tag
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        "# @requires bus.timeout>=200000\n",  # canonical
        "#@requires bus.timeout>=200000\n",  # no space after the hash
        "#   @requires   bus.timeout>=200000\n",  # wide gap after the hash and the tag word
        "# @requires bus.timeout >= 200000\n",  # spaces around the operator
        "# @requires bus.timeout  >=  200000\n",  # wide spaces around the operator
        "## @requires bus.timeout>=200000\n",  # section-style double hash
        "# @requires bus.timeout>=200000   \n",  # trailing whitespace
        "#\t@requires bus.timeout>=200000\n",  # tab instead of a space
    ],
)
def test_parse_requires_tags_format_variants(tmp_path: Path, source: str) -> None:
    (tag,) = _parse(tmp_path, source)
    assert (tag.field, tag.op, tag.value) == ("timeout", ">=", 200000)


# ---------------------------------------------------------------------------
# D4: every legal placement of a well-formed tag
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        "# @requires bus.timeout>=200000\nx = 1\n",  # very first line
        '"""Driver docstring."""\n\n# @requires bus.timeout>=200000\nx = 1\n',  # after the module docstring
        "import time\n\n# @requires bus.timeout>=200000\nimport struct\n",  # among the imports
        "_WIRING = (('bus', 'i2c'),)  # @requires bus.timeout>=200000\n",  # trailing inline, next to _WIRING
        "_WIRING = ()\n# @requires bus.timeout>=200000\n_VAL_TEMP = ()\n",  # between the schema tuples
        "x = 1\n# @requires bus.timeout>=200000",  # last line, no trailing newline
        "def f():\n    pass\n\n\n# @requires bus.timeout>=200000\n",  # after a function body, back at column 0
    ],
)
def test_parse_requires_tags_valid_locations(tmp_path: Path, source: str) -> None:
    (tag,) = _parse(tmp_path, source)
    assert (tag.field, tag.op, tag.value) == ("timeout", ">=", 200000)


# ---------------------------------------------------------------------------
# D5: multiplicity, and coexistence with ordinary comments/strings
# ---------------------------------------------------------------------------


def test_parse_requires_tags_none_declared(tmp_path: Path) -> None:
    assert _parse(tmp_path, "class Plain_Reader:\n    pass\n") == ()


def test_parse_requires_tags_two_distinct_fields_in_source_order(tmp_path: Path) -> None:
    tags = _parse(tmp_path, "# @requires bus.timeout>=200000\n# @requires bus.frequency<=100000\n")
    assert [(t.field, t.op, t.value) for t in tags] == [("timeout", ">=", 200000), ("frequency", "<=", 100000)]


def test_parse_requires_tags_same_field_bounded_from_both_sides(tmp_path: Path) -> None:
    # A range is expressed as two tags on the same field - both must survive, not collapse.
    tags = _parse(tmp_path, "# @requires bus.frequency>=50000\n# @requires bus.frequency<=400000\n")
    assert [(t.op, t.value) for t in tags] == [(">=", 50000), ("<=", 400000)]


def test_parse_requires_tags_exact_duplicates_are_both_kept(tmp_path: Path) -> None:
    # Redundant, but harmless and self-consistent: the checker just evaluates the same thing twice.
    tags = _parse(tmp_path, "# @requires bus.timeout>=200000\n# @requires bus.timeout>=200000\n")
    assert len(tags) == 2


def test_parse_requires_tags_a_valid_tag_does_not_excuse_a_near_miss_beside_it(tmp_path: Path) -> None:
    # The exact-match bookkeeping parse_requires_tags() hands the near-miss detector is per comment
    # position, not "this file already had a valid tag" - a half-migrated driver still fails.
    _parse_expecting(tmp_path, "# @requires bus.timeout>=200000\n# @require bus.frequency>=100000\n", "misspelled @requires tag")


def test_parse_requires_tags_line_break_lookalike_does_not_fake_an_indented_tag(tmp_path: Path) -> None:
    # Regression guard, end to end: a \x0b anywhere earlier in the file used to shift the scan's
    # idea of every later line, rejecting this perfectly valid module-level tag as "not at module
    # level". See test_buildgen_tag_comments.py for the mechanism.
    path = tmp_path / "asy_x_driver.py"
    path.write_bytes(b"X = 'a\x0bb'\ndef f():\n    pass\n# @requires bus.timeout>=200000\n")
    (tag,) = parse_requires_tags(path, "dev", "x")
    assert (tag.field, tag.op, tag.value) == ("timeout", ">=", 200000)


def test_parse_requires_tags_among_ordinary_comments_and_tag_shaped_strings(tmp_path: Path) -> None:
    source = (
        '"""Docstring mentioning # @requires bus.frequency>=999999 as an example."""\n'
        "# an ordinary comment\n"
        "# @requires bus.timeout>=200000\n"
        'ERR = "see # @requires bus.frequency>=888888"\n'
        "x = 1  # another ordinary comment\n"
    )
    tags = _parse(tmp_path, source)
    assert [(t.field, t.value) for t in tags] == [("timeout", 200000)]


# ---------------------------------------------------------------------------
# D6: field-name shapes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field", ["timeout", "clock_stretch_us", "pin0", "_reserved"])
def test_parse_requires_tags_field_name_shapes(tmp_path: Path, field: str) -> None:
    (tag,) = _parse(tmp_path, f"# @requires bus.{field}>=1\n")
    assert tag.field == field


@pytest.mark.parametrize(
    "driver,instance,expected",
    [
        # Every real tag any src/ driver declares today, each traced to its own datasheet citation
        # in the driver file itself. A driver gaining or losing one is a deliberate change that has
        # to show up here too.
        ("asy_scd30_driver.py", "scd30", (RequiresTag("timeout", ">=", 200000, "# @requires bus.timeout>=200000"), RequiresTag("frequency", "<=", 100000, "# @requires bus.frequency<=100000"))),
        ("asy_sgp40_driver.py", "sgp40", (RequiresTag("frequency", "<=", 400000, "# @requires bus.frequency<=400000"),)),
    ],
)
def test_parse_requires_tags_real_drivers(src_dir: Path, driver: str, instance: str, expected: "tuple[RequiresTag, ...]") -> None:
    assert parse_requires_tags(src_dir / driver, "dev", instance) == expected


def test_no_other_src_driver_declares_an_unnoticed_tag(src_dir: Path) -> None:
    # The near-miss detector only fires on comments that *look* like tags; this is the other half -
    # a tag added to some other driver without a test here would otherwise go unrecorded.
    tagged = {p.name for p in sorted(src_dir.glob("*.py")) if parse_requires_tags(p, "dev", "x")}
    assert tagged == {"asy_scd30_driver.py", "asy_sgp40_driver.py"}


# ---------------------------------------------------------------------------
# "Present, or close to present, with typos" - a typo'd/malformed/misplaced @requires attempt must
# fail the build loud, never be silently treated as "no tag declared" (buildgen/tag_comments.py's
# standing rule). One case per dimension: an abort is an abort, so these don't recombine.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source,match",
    [
        # D2 wording
        ("# @require bus.timeout>=200000\n", "misspelled @requires tag"),
        ("# @Requires bus.timeout>=200000\n", "malformed @requires tag"),
        ("# requires bus.timeout>=200000\n", "leading '@' missing"),
        # D3 format
        ("# @requires timeout>=200000\n", "malformed @requires tag"),  # "bus." prefix dropped
        ("# @requires bus.timeout=200000\n", "malformed @requires tag"),  # single "=" typo
        ("# @requires bus.timeout 200000\n", "malformed @requires tag"),  # operator dropped
        ("# @requires bus.timeout>=\n", "malformed @requires tag"),  # value dropped
        ("# @requires bus . timeout>=200000\n", "malformed @requires tag"),  # spaces around the dot
        ("# @requires bus.timeout>=200000 ms\n", "malformed @requires tag"),  # trailing junk
        ("# @requires timeout 200000\n", "malformed @requires tag"),  # prefix *and* operator dropped
        # D2 content
        ("# @requires bus.timeout>=not_a_number\n", "malformed @requires value"),
        ("# @requires bus.timeout>=1.2.3\n", "malformed @requires value"),
    ],
)
def test_parse_requires_tags_rejects_every_broken_shape(tmp_path: Path, source: str, match: str) -> None:
    _parse_expecting(tmp_path, source, match)


@pytest.mark.parametrize(
    "source",
    [
        "class Foo:\n    def __init__(self):\n        # @requires bus.timeout>=200000\n        pass\n",  # in a method body
        "class Foo:\n    # @requires bus.timeout>=200000\n    X = 1\n",  # in a class body
        "def f():\n    x = (\n        # @requires bus.timeout>=200000\n    )\n",  # bracketed, but inside a body
    ],
)
def test_parse_requires_tags_rejects_locations_inside_a_body(tmp_path: Path, source: str) -> None:
    # Location dimension: a well-formed tag hidden inside a body isn't "close to the schema" the way
    # module-level _WIRING/_VAL_* placement is - it must fail, not silently parse.
    _parse_expecting(tmp_path, source, "module level")


@pytest.mark.parametrize(
    "source",
    [
        "_WIRING = (\n    # @requires bus.timeout>=200000\n)\n",
        "_WIRING = (\n    ('fram_target', X, 'fram', False, 'kwarg'),\n    # @requires bus.timeout>=200000\n)\n",
        "_LIMITS = [\n    # @requires bus.timeout>=200000\n]\n",
        "_D = {\n    # @requires bus.timeout>=200000\n}\n",
        "_WIRING = (\n    # @requires bus.timeout>=200000\n    (1, (2,\n        3)),\n)\n",  # nested brackets
    ],
)
def test_parse_requires_tags_accepts_a_bracketed_continuation_line_at_module_level(tmp_path: Path, source: str) -> None:
    # A tag written inside a module-level statement's own brackets is physically indented but is
    # still module level, and sitting *inside* _WIRING's parens is about as close to the schema as
    # a comment can get. Placement is judged by the enclosing statement, not by leading whitespace.
    (tag,) = _parse(tmp_path, source)
    assert (tag.field, tag.op, tag.value) == ("timeout", ">=", 200000)


@pytest.mark.parametrize(
    "source",
    [
        # Prose that merely names the tag - mirrors the real near-collision in buildgen/validate.py,
        # whose multi-line comment wraps so one line reads "# @requires tag, not here).".
        "# explains something, only actually\n# required by that driver's own\n# @requires tag, not here).\nx = 1\n",
        "# @param bus.timeout>=200000\n",  # an unrelated @-word
        "# @requi bus.timeout>=200000\n",  # edit distance 3 - outside the typo tolerance
        "# required for correct clock stretching\n",  # sigil-less English prose, no payload
        '"""# @requires bus.timeout>=200000"""\nx = 1\n',  # inside a docstring, not a comment
        'X = "# @requires bus.timeout>=200000"\n',  # inside a string literal
    ],
)
def test_parse_requires_tags_leaves_non_tags_alone(tmp_path: Path, source: str) -> None:
    assert _parse(tmp_path, source) == ()


# ---------------------------------------------------------------------------
# D7: enforcement against a real bus table
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "op,actual,value,satisfied",
    [
        (">=", 100, 50, True), (">=", 100, 100, True), (">=", 100, 200, False),
        ("<=", 100, 200, True), ("<=", 100, 100, True), ("<=", 100, 50, False),
        ("==", 100, 100, True), ("==", 100, 50, False),
        ("!=", 100, 50, True), ("!=", 100, 100, False),
        (">", 100, 50, True), (">", 100, 100, False),
        ("<", 100, 200, True), ("<", 100, 100, False),
    ],
)
def test_check_requires_tags_every_operator_both_ways(op: str, actual: int, value: int, *, satisfied: bool) -> None:
    tags = (RequiresTag("timeout", op, value, f"@requires bus.timeout{op}{value}"),)
    if satisfied:
        check_requires_tags(tags, {"timeout": actual}, "dev", "scd30", "i2c0")  # no raise
    else:
        with pytest.raises(BuildError, match="does not satisfy"):
            check_requires_tags(tags, {"timeout": actual}, "dev", "scd30", "i2c0")


@pytest.mark.parametrize("actual,value", [(100, 99.5), (100.5, 100), (100.0, 100)])
def test_check_requires_tags_mixed_int_float_comparison(actual: "int | float", value: "int | float") -> None:
    tags = (RequiresTag("frequency", ">=", value, "@requires bus.frequency>=x"),)
    check_requires_tags(tags, {"frequency": actual}, "dev", "scd30", "i2c0")  # no raise


def test_check_requires_tags_zero_is_a_present_value_not_a_missing_field() -> None:
    # bus_table.get() returning a falsy 0 must go down the comparison path, not the "missing field"
    # path - a `if not actual` bug here would report the wrong error for a perfectly valid table.
    check_requires_tags((RequiresTag("offset", "==", 0, "@requires bus.offset==0"),), {"offset": 0}, "dev", "scd30", "i2c0")
    with pytest.raises(BuildError, match="does not satisfy"):
        check_requires_tags((RequiresTag("offset", "!=", 0, "@requires bus.offset!=0"),), {"offset": 0}, "dev", "scd30", "i2c0")


def test_check_requires_tags_missing_bus_field() -> None:
    tags = (RequiresTag("timeout", ">=", 200000, "@requires bus.timeout>=200000"),)
    with pytest.raises(BuildError, match="is missing field"):
        check_requires_tags(tags, {}, "dev", "scd30", "i2c0")


@pytest.mark.parametrize("actual", ["200ms", [200000], {"us": 200000}, None])
def test_check_requires_tags_wrong_type_fails_loud_not_a_raw_traceback(actual: object) -> None:
    # A malformed TOML value (e.g. "200ms" where an int is expected) must produce a clean
    # BuildError, not an uncaught TypeError from comparing str >= int. A None value is
    # indistinguishable from an absent key here, and reports as the missing field it effectively is.
    tags = (RequiresTag("timeout", ">=", 200000, "@requires bus.timeout>=200000"),)
    expected = "is missing field" if actual is None else "not comparable"
    with pytest.raises(BuildError, match=expected):
        check_requires_tags(tags, {"timeout": actual}, "dev", "scd30", "i2c0")


def test_check_requires_tags_reports_the_first_violated_tag_of_several() -> None:
    tags = (
        RequiresTag("timeout", ">=", 200000, "@requires bus.timeout>=200000"),
        RequiresTag("frequency", "<=", 100000, "@requires bus.frequency<=100000"),
    )
    with pytest.raises(BuildError, match="frequency"):
        check_requires_tags(tags, {"timeout": 250000, "frequency": 400000}, "dev", "scd30", "i2c0")


def test_check_requires_tags_all_satisfied() -> None:
    tags = (
        RequiresTag("timeout", ">=", 200000, "@requires bus.timeout>=200000"),
        RequiresTag("frequency", "<=", 400000, "@requires bus.frequency<=400000"),
    )
    check_requires_tags(tags, {"timeout": 250000, "frequency": 100000}, "dev", "scd30", "i2c0")  # no raise
