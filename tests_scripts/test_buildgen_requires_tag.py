"""Tests for buildgen.requires_tag: the `# @requires bus.<field><op><value>` comment-tag parser
and enforcement (BUILD_CHAIN_PLAN.md's "Build/generator script quality bar"). Covers the real
SCD30 clock-stretch tag this session added plus every malformed/violated case."""

from pathlib import Path

import pytest

from buildgen.errors import BuildError
from buildgen.requires_tag import RequiresTag, check_requires_tags, parse_requires_tags


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


def test_parse_requires_tags_scd30_clock_stretch(src_dir: Path):
    tags = parse_requires_tags(src_dir / "asy_scd30_driver.py", "dev", "scd30")
    assert RequiresTag("timeout", ">=", 200000, "# @requires bus.timeout>=200000") in tags


def test_parse_requires_tags_none_declared(tmp_path: Path):
    path = tmp_path / "asy_plain_driver.py"
    path.write_text("class Plain_Reader:\n    pass\n")
    assert parse_requires_tags(path, "dev", "plain") == ()


@pytest.mark.parametrize("op,value", [(">=", "200000"), ("<=", "50000"), ("==", "100000"), ("!=", "0"), (">", "1"), ("<", "999999")])
def test_parse_requires_tags_every_operator(tmp_path: Path, op: str, value: str):
    path = tmp_path / "asy_x_driver.py"
    path.write_text(f"# @requires bus.timeout{op}{value}\n")
    tags = parse_requires_tags(path, "dev", "x")
    assert tags == (RequiresTag("timeout", op, int(value), f"# @requires bus.timeout{op}{value}"),)


def test_parse_requires_tags_float_value(tmp_path: Path):
    path = tmp_path / "asy_x_driver.py"
    path.write_text("# @requires bus.frequency>=50000.5\n")
    tags = parse_requires_tags(path, "dev", "x")
    assert tags[0].value == 50000.5


def test_parse_requires_tags_malformed_value(tmp_path: Path):
    path = tmp_path / "asy_x_driver.py"
    path.write_text("# @requires bus.timeout>=not_a_number\n")
    with pytest.raises(BuildError, match="malformed @requires value"):
        parse_requires_tags(path, "dev", "x")


def test_check_requires_tags_satisfied():
    tags = (RequiresTag("timeout", ">=", 200000, "@requires bus.timeout>=200000"),)
    check_requires_tags(tags, {"timeout": 200000}, "dev", "scd30", "i2c0")  # no raise


def test_check_requires_tags_violated():
    tags = (RequiresTag("timeout", ">=", 200000, "@requires bus.timeout>=200000"),)
    with pytest.raises(BuildError, match="does not satisfy"):
        check_requires_tags(tags, {"timeout": 50000}, "dev", "scd30", "i2c0")


def test_check_requires_tags_missing_bus_field():
    tags = (RequiresTag("timeout", ">=", 200000, "@requires bus.timeout>=200000"),)
    with pytest.raises(BuildError, match="is missing field"):
        check_requires_tags(tags, {}, "dev", "scd30", "i2c0")


def test_check_requires_tags_wrong_type_fails_loud_not_a_raw_traceback():
    # A malformed TOML value (e.g. "200ms" where an int is expected) must produce a clean
    # BuildError, not an uncaught TypeError from comparing str >= int.
    tags = (RequiresTag("timeout", ">=", 200000, "@requires bus.timeout>=200000"),)
    with pytest.raises(BuildError, match="not comparable"):
        check_requires_tags(tags, {"timeout": "200ms"}, "dev", "scd30", "i2c0")


# ---------------------------------------------------------------------------
# "Present, or close to present, with typos" - a typo'd/malformed/misplaced @requires attempt must
# fail the build loud, never be silently treated as "no tag declared" (buildgen/tag_comments.py's
# standing rule). Complements test_buildgen_tag_comments.py's own unit-level coverage of the shared
# mechanism with full parse_requires_tags() end-to-end coverage of the one real tag that uses it.
# ---------------------------------------------------------------------------


def test_parse_requires_tags_missing_s_typo_raises(tmp_path: Path):
    path = tmp_path / "asy_x_driver.py"
    path.write_text("# @require bus.timeout>=200000\n")
    with pytest.raises(BuildError, match="misspelled @requires tag"):
        parse_requires_tags(path, "dev", "x")


def test_parse_requires_tags_wrong_case_typo_raises(tmp_path: Path):
    path = tmp_path / "asy_x_driver.py"
    path.write_text("# @Requires bus.timeout>=200000\n")
    with pytest.raises(BuildError, match="malformed @requires tag"):
        parse_requires_tags(path, "dev", "x")


def test_parse_requires_tags_missing_bus_prefix_raises(tmp_path: Path):
    path = tmp_path / "asy_x_driver.py"
    path.write_text("# @requires timeout>=200000\n")
    with pytest.raises(BuildError, match="malformed @requires tag"):
        parse_requires_tags(path, "dev", "x")


def test_parse_requires_tags_single_equals_typo_raises(tmp_path: Path):
    path = tmp_path / "asy_x_driver.py"
    path.write_text("# @requires bus.timeout=200000\n")
    with pytest.raises(BuildError, match="malformed @requires tag"):
        parse_requires_tags(path, "dev", "x")


def test_parse_requires_tags_indented_inside_function_raises(tmp_path: Path):
    # Location dimension: a well-formed tag hidden inside a method body isn't "close to the
    # schema" the way module-level _WIRING/_VAL_* placement is - must fail, not silently parse.
    path = tmp_path / "asy_x_driver.py"
    path.write_text("class Foo:\n    def __init__(self):\n        # @requires bus.timeout>=200000\n        pass\n")
    with pytest.raises(BuildError, match="module level"):
        parse_requires_tags(path, "dev", "x")


def test_parse_requires_tags_prose_mentioning_the_tag_by_name_is_not_flagged(tmp_path: Path):
    # Regression guard for a real near-collision found in this repo: buildgen/validate.py has a
    # multi-line prose comment that happens to wrap so one line reads "# @requires tag, not
    # here)." - carries no field/operator/value payload, so it must never be mistaken for a
    # malformed tag attempt.
    path = tmp_path / "asy_x_driver.py"
    path.write_text("# explains something, only actually\n# required by that driver's own\n# @requires tag, not here).\nx = 1\n")
    assert parse_requires_tags(path, "dev", "x") == ()


def test_parse_requires_tags_unrelated_at_word_is_not_flagged(tmp_path: Path):
    path = tmp_path / "asy_x_driver.py"
    path.write_text("# @param bus.timeout>=200000\n")
    assert parse_requires_tags(path, "dev", "x") == ()
