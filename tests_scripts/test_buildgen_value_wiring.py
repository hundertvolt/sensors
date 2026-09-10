"""Tests for buildgen.value_wiring: parsing a driver's `_VALUE_WIRING` tuple straight from source
via AST (BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md §2.9/§10.6). Covers the real _VALUE_WIRING
declaration already in src/asy_sgp40_driver.py plus every malformed shape the parser must reject."""

from pathlib import Path

import pytest

from buildgen.errors import BuildError
from buildgen.value_wiring import ValueWiringField, parse_value_wiring


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


def test_parse_value_wiring_sgp40_temperature_and_humidity(src_dir: Path):
    fields = parse_value_wiring(src_dir / "asy_sgp40_driver.py", "dev", "sgp40")
    assert ValueWiringField("temperature_source", "temperature_source", "temperature_field", True) in fields
    assert ValueWiringField("humidity_source", "humidity_source", "humidity_field", True) in fields


def test_parse_value_wiring_no_value_wiring_declared_returns_empty(tmp_path: Path):
    path = tmp_path / "asy_plain_driver.py"
    path.write_text("class Plain_Reader:\n    pass\n")
    assert parse_value_wiring(path, "dev", "plain") == ()


def test_parse_value_wiring_not_a_tuple(tmp_path: Path):
    path = tmp_path / "asy_bad_driver.py"
    path.write_text('_VALUE_WIRING = "not a tuple"\n')
    with pytest.raises(BuildError, match="must be a literal tuple"):
        parse_value_wiring(path, "dev", "bad")


@pytest.mark.parametrize(
    "body,match",
    [
        ('_VALUE_WIRING = (("only_three", "x", "y"),)', "must be a 4-tuple"),
        ('_VALUE_WIRING = ((1, "x", "y", True),)', r"\[0\] \(toml_field\) must be a string literal"),
        ('_VALUE_WIRING = (("x", 1, "y", True),)', r"\[1\] \(source_kwarg\) must be a string literal"),
        ('_VALUE_WIRING = (("x", "y", 1, True),)', r"\[2\] \(field_kwarg\) must be a string literal"),
        ('_VALUE_WIRING = (("x", "y", "z", "yes"),)', r"\[3\] \(required\) must be a bool literal"),
    ],
)
def test_parse_value_wiring_malformed_tuple_shapes(tmp_path: Path, body: str, match: str):
    path = tmp_path / "asy_bad_driver.py"
    path.write_text(f"{body}\n")
    with pytest.raises(BuildError, match=match):
        parse_value_wiring(path, "dev", "bad")


def test_parse_value_wiring_syntax_error(tmp_path: Path):
    path = tmp_path / "asy_broken_driver.py"
    path.write_text("def f(:\n")
    with pytest.raises(BuildError, match="syntax error"):
        parse_value_wiring(path, "dev", "broken")
