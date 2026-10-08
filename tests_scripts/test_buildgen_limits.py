"""Tests for buildgen.limits: the `# @limits <field> <min>..<max>` / `# @limits <field> in {a, b}`
comment tag - a TOML field's own unconditional domain. Walks the same accept/reject dimensions as
test_buildgen_wiring.py; see that file's own dimension index."""

import ast
from pathlib import Path

import pytest

from buildgen.errors import BuildError
from buildgen.limits import LimitField, parse_limits


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


def _parse(tmp_path: Path, source: str) -> "tuple[LimitField, ...]":
    path = tmp_path / "asy_x_driver.py"
    path.write_text(source)
    return parse_limits(path, "dev", "x")


def _parse_expecting(tmp_path: Path, source: str, match: str) -> None:
    with pytest.raises(BuildError, match=match):
        _parse(tmp_path, source)


# --- accept side: the full range x number-shape cross product -----------------------------------


@pytest.mark.parametrize(
    "payload,low,high",
    [
        ("1..3600", 1, 3600),
        ("0..0", 0, 0),  # min == max is an exact-value requirement
        ("-40..85", -40, 85),
        ("1..*", 1, None),  # unbounded above
        ("*..100", None, 100),  # unbounded below
        ("0.5..99.5", 0.5, 99.5),
        ("-0.25..0", -0.25, 0),
        ("1..2e3", 1, 2000.0),
        ("0x10..0xff", 16, 255),
        ("1_000..2_000", 1000, 2000),
    ],
)
def test_parse_limits_accepts_every_range_shape(tmp_path: Path, payload: str, low: object, high: object) -> None:
    (field,) = _parse(tmp_path, f"# @limits trigger_s {payload}\n")
    assert (field.toml_field, field.choices, field.min, field.max) == ("trigger_s", None, low, high)


@pytest.mark.parametrize(
    "payload,expected",
    [
        ("in {0x76, 0x77}", {0x76, 0x77}),
        ("in {0x76,0x77}", {0x76, 0x77}),  # no space after the comma
        ("in {1}", {1}),  # a single legal value
        ("in { 1 , 2 , 3 }", {1, 2, 3}),  # generous inner spacing
        ("in {1, 1, 2}", {1, 2}),  # a repeated value collapses rather than erroring
        ("in {-5, 0, 5}", {-5, 0, 5}),
    ],
)
def test_parse_limits_accepts_every_choice_set_shape(tmp_path: Path, payload: str, expected: "set[int]") -> None:
    (field,) = _parse(tmp_path, f"# @limits address {payload}\n")
    assert (field.toml_field, field.choices, field.min, field.max) == ("address", frozenset(expected), None, None)


@pytest.mark.parametrize(
    "source",
    [
        "#@limits trigger_s 1..3600\n",
        "## @limits trigger_s 1..3600\n",
        "#   @limits   trigger_s   1..3600\n",
        "#\t@limits\ttrigger_s\t1..3600\n",
        "X = 1  # @limits trigger_s 1..3600\n",
        "_SCHEMA = (\n    # @limits trigger_s 1..3600\n)\n",
    ],
)
def test_parse_limits_accepts_every_legal_spacing_and_placement(tmp_path: Path, source: str) -> None:
    (field,) = _parse(tmp_path, source)
    assert (field.min, field.max) == (1, 3600)


# --- multiplicity -------------------------------------------------------------------------------


def test_parse_limits_no_tags_is_not_an_error(tmp_path: Path) -> None:
    assert _parse(tmp_path, "X = 1\n") == ()


def test_parse_limits_several_tags_keep_source_order(tmp_path: Path) -> None:
    fields = _parse(tmp_path, "# @limits address in {1, 2}\n# @limits trigger_s 1..3600\n")
    assert [f.toml_field for f in fields] == ["address", "trigger_s"]


def test_parse_limits_duplicate_field_rejected(tmp_path: Path) -> None:
    # One domain per field: two tags would silently let the second win.
    _parse_expecting(tmp_path, "# @limits trigger_s 1..10\n# @limits trigger_s 1..3600\n", "two @limits tags for 'trigger_s'")


# --- reject side: wording -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "source,match",
    [
        ("# @limts trigger_s 1..3600\n", "misspelled @limits tag"),  # deletion
        ("# @limiits trigger_s 1..3600\n", "misspelled @limits tag"),  # insertion
        ("# @limats trigger_s 1..3600\n", "misspelled @limits tag"),  # substitution
        ("# @limtis trigger_s 1..3600\n", "misspelled @limits tag"),  # transposition
        ("# @LIMITS trigger_s 1..3600\n", "malformed @limits tag"),  # mis-cased
        ("# limits trigger_s 1..3600\n", "leading '@' missing"),  # sigil dropped
    ],
)
def test_parse_limits_rejects_each_wording_mistake(tmp_path: Path, source: str, match: str) -> None:
    _parse_expecting(tmp_path, source, match)


# --- reject side: format, each element wrong then dropped ---------------------------------------


@pytest.mark.parametrize(
    "source,match",
    [
        ("# @limits trigger_s\n", "malformed @limits tag"),  # the whole domain dropped
        ("# @limits trigger_s 1..\n", "missing one of its bounds"),  # max dropped
        ("# @limits trigger_s ..3600\n", "missing one of its bounds"),  # min dropped
        ("# @limits trigger_s 1.3600\n", "malformed @limits tag"),  # the ".." itself dropped
        ("# @limits trigger_s *..*\n", "checks nothing"),  # both bounds unbounded
        ("# @limits trigger_s 3600..1\n", "inverted"),  # bounds swapped
        ("# @limits trigger_s x..3600\n", "min 'x' is not a number"),
        ("# @limits trigger_s 1..x\n", "max 'x' is not a number"),
        ("# @limits address in {}\n", "empty choice set"),  # the values dropped
        ("# @limits address in {0x76\n", "is neither a range"),  # the closing brace dropped
        ("# @limits address in 0x76, 0x77}\n", "is neither a range"),  # the opening brace dropped
        ("# @limits address in {1.5}\n", "must be an int, not a float"),
        ("# @limits address in {x}\n", "choice 'x' is not a number"),
    ],
)
def test_parse_limits_rejects_each_payload_mistake(tmp_path: Path, source: str, match: str) -> None:
    _parse_expecting(tmp_path, source, match)


def test_parse_limits_rejects_a_dropped_field_name(tmp_path: Path) -> None:
    # Only the domain left: it parses as field="1", payload="" - no domain at all.
    _parse_expecting(tmp_path, "# @limits 1..3600\n", "malformed @limits tag")


def test_parse_limits_bare_tag_name_with_no_payload_at_all_is_prose(tmp_path: Path) -> None:
    # Consistent with @requires/@wiring: the tag name alone carries nothing to tell an abandoned
    # tag from prose naming the mechanism.
    assert _parse(tmp_path, "# @limits\n") == ()


# --- reject side: location ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        "class Foo:\n    # @limits trigger_s 1..3600\n    X = 1\n",
        "def f():\n    # @limits trigger_s 1..3600\n    pass\n",
    ],
)
def test_parse_limits_rejects_locations_inside_a_body(tmp_path: Path, source: str) -> None:
    _parse_expecting(tmp_path, source, "module level")


# --- false positives ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        "# limits are checked elsewhere in this file\n",
        "# @limits are described in the matrix doc, section 5.2\n",
        'X = "# @limits trigger_s 1..3600"\n',
        '"""Doc.\n# @limits trigger_s 1..3600\n"""\nX = 1\n',
    ],
)
def test_parse_limits_leaves_non_tags_alone(tmp_path: Path, source: str) -> None:
    assert _parse(tmp_path, source) == ()


# --- the real declarations in src/ --------------------------------------------------------------


def test_parse_limits_real_bmp3xx_driver(src_dir: Path) -> None:
    assert parse_limits(src_dir / "asy_bmp3xx_driver.py", "dev", "bmp3xx") == (
        LimitField("address", frozenset({0x76, 0x77}), None, None),
        LimitField("trigger_s", None, 1, 3600),
    )


def test_parse_limits_real_isl29125_driver(src_dir: Path) -> None:
    # No "address" limit, unlike bmp3xx - 0x44 is hard-wired with no address-select pin at all, so
    # this driver has no TOML-configurable address field for a @limits tag to describe.
    assert parse_limits(src_dir / "asy_isl29125_driver.py", "dev", "isl29125") == (LimitField("trigger_s", None, 1, 3600),)


def test_parse_limits_real_scd30_driver(src_dir: Path) -> None:
    # 1 s up to the chip's longest measurement interval (Interface Description 1.4.3): the stuck-pin fallback's bounds.
    assert parse_limits(src_dir / "asy_scd30_driver.py", "dev", "scd30") == (LimitField("trigger_s", None, 1, 1800),)


def _known_fram_sizes(driver: Path) -> "frozenset[int]":
    # _KNOWN_PRODUCT_IDS' keys, read without importing the MicroPython-only driver.
    for node in ast.walk(ast.parse(driver.read_text())):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "_KNOWN_PRODUCT_IDS":
            assert isinstance(node.value, ast.Dict)
            return frozenset(ast.literal_eval(key) for key in node.value.keys if key is not None)
    raise AssertionError(f"{driver.name} declares no _KNOWN_PRODUCT_IDS")


def test_fram_max_size_limits_match_the_known_product_ids(src_dir: Path) -> None:
    # The build-time set and the boot-time RDID table are two copies of one fact; a size in one only builds-then-fails.
    (limit,) = parse_limits(src_dir / "asy_fram_manager.py", "dev", "fram")
    assert limit.toml_field == "max_size"
    assert limit.choices == _known_fram_sizes(src_dir / "asy_fram_driver.py")


def test_no_other_src_module_declares_an_unnoticed_limits_tag(src_dir: Path) -> None:
    tagged = {p.name for p in sorted(src_dir.glob("*.py")) if parse_limits(p, "dev", "x")}
    assert tagged == {"asy_bmp3xx_driver.py", "asy_fram_manager.py", "asy_isl29125_driver.py", "asy_scd30_driver.py"}
