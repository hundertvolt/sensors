"""Tests for buildgen.limits: parsing a driver's `_LIMITS` tuple straight from source via AST
(BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md §5.2/§10.4). Covers the real _LIMITS declaration
already in src/asy_bmp3xx_driver.py plus every malformed shape the parser must reject."""

from pathlib import Path

import pytest

from buildgen.errors import BuildError
from buildgen.limits import LimitField, parse_limits


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


def test_parse_limits_bmp3xx_address_and_trigger_sec(src_dir: Path):
    fields = parse_limits(src_dir / "asy_bmp3xx_driver.py", "dev", "bmp3xx")
    assert LimitField("address", frozenset({0x76, 0x77})) in fields
    assert LimitField("trigger_sec", None, 1, 3600) in fields


def test_parse_limits_no_limits_declared_returns_empty(tmp_path: Path):
    path = tmp_path / "asy_plain_driver.py"
    path.write_text("class Plain_Reader:\n    pass\n")
    assert parse_limits(path, "dev", "plain") == ()


def test_parse_limits_not_a_tuple(tmp_path: Path):
    path = tmp_path / "asy_bad_driver.py"
    path.write_text('_LIMITS = "not a tuple"\n')
    with pytest.raises(BuildError, match="must be a literal tuple"):
        parse_limits(path, "dev", "bad")


def test_parse_limits_negative_bound(tmp_path: Path):
    path = tmp_path / "asy_neg_driver.py"
    path.write_text('_LIMITS = (("x", (-10, 10)),)\n')
    assert parse_limits(path, "dev", "neg") == (LimitField("x", None, -10, 10),)


def test_parse_limits_one_sided_bound(tmp_path: Path):
    path = tmp_path / "asy_one_sided_driver.py"
    path.write_text('_LIMITS = (("x", (0, None)),)\n')
    assert parse_limits(path, "dev", "one_sided") == (LimitField("x", None, 0, None),)


def test_parse_limits_float_bound(tmp_path: Path):
    path = tmp_path / "asy_float_driver.py"
    path.write_text('_LIMITS = (("x", (0.5, 99.5)),)\n')
    assert parse_limits(path, "dev", "float") == (LimitField("x", None, 0.5, 99.5),)


@pytest.mark.parametrize(
    "body,match",
    [
        ('_LIMITS = (("only_one",),)', "must be a 2-tuple"),
        ('_LIMITS = ((1, (0, 10)),)', r"\[0\] \(toml_field\) must be a string literal"),
        ('_LIMITS = (("x", "not a tuple or frozenset"),)', r"\[1\] \(constraint\) must be a"),
        ('_LIMITS = (("x", (0, "ten")),)', r"\(min, max\) entries must each be a number literal or None"),
        ('_LIMITS = (("x", (True, 10)),)', r"\(min, max\) entries must each be a number literal or None"),
        ('_LIMITS = (("x", frozenset({"a", "b"})),)', r"\[1\] \(constraint\) must be a"),
    ],
)
def test_parse_limits_malformed_tuple_shapes(tmp_path: Path, body: str, match: str):
    path = tmp_path / "asy_bad_driver.py"
    path.write_text(f"{body}\n")
    with pytest.raises(BuildError, match=match):
        parse_limits(path, "dev", "bad")


def test_parse_limits_syntax_error(tmp_path: Path):
    path = tmp_path / "asy_broken_driver.py"
    path.write_text("def f(:\n")
    with pytest.raises(BuildError, match="syntax error"):
        parse_limits(path, "dev", "broken")
