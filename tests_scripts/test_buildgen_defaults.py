"""Tests for buildgen.defaults: AST-discovering a driver's `_Default<Field>` classes (§2 of
BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md) - the wiring-defaults mechanism's own schema-by-
construction. Covers the three real default providers already in src/ plus every malformed shape."""

from pathlib import Path

import pytest

from buildgen.defaults import default_class_defines_attr, default_class_name, default_init_params, find_default_class
from buildgen.errors import BuildError


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


@pytest.mark.parametrize(
    "toml_field,expected_class",
    [
        ("temperature_source", "_DefaultTemperatureSource"),
        ("humidity_source", "_DefaultHumiditySource"),
        ("signal_sink", "_DefaultSignalSink"),
    ],
)
def test_default_class_name(toml_field: str, expected_class: str):
    assert default_class_name(toml_field) == expected_class


def test_find_default_class_sgp40_temperature_source(src_dir: Path):
    class_node = find_default_class(src_dir / "asy_sgp40_driver.py", "dev", "sgp40", "temperature_source")
    assert class_node is not None
    assert class_node.name == "_DefaultTemperatureSource"
    params = default_init_params(class_node, src_dir / "asy_sgp40_driver.py", "dev", "sgp40")
    assert any(p.name == "temperature" and p.has_default for p in params)


def test_find_default_class_sgp40_humidity_source(src_dir: Path):
    class_node = find_default_class(src_dir / "asy_sgp40_driver.py", "dev", "sgp40", "humidity_source")
    assert class_node is not None
    assert class_node.name == "_DefaultHumiditySource"
    params = default_init_params(class_node, src_dir / "asy_sgp40_driver.py", "dev", "sgp40")
    assert any(p.name == "relative_humidity" and p.has_default for p in params)


def test_find_default_class_notification_signal_sink(src_dir: Path):
    class_node = find_default_class(src_dir / "asy_notification_service.py", "dev", "notification", "signal_sink")
    assert class_node is not None
    assert class_node.name == "_DefaultSignalSink"
    assert default_class_defines_attr(class_node, "request_signal")
    assert not default_class_defines_attr(class_node, "not_a_real_method")


def test_find_default_class_not_declared_returns_none(src_dir: Path):
    # asy_scd30_driver.py has no _Default<Field> class for fram_target (it's not a defaultable
    # field per §2.7's scope - only the two original required=True fields need this mechanism).
    assert find_default_class(src_dir / "asy_scd30_driver.py", "dev", "scd30", "fram_target") is None


def test_default_init_params_required_and_optional(tmp_path: Path):
    path = tmp_path / "asy_fake_driver.py"
    path.write_text("class _DefaultFoo:\n    def __init__(self, required_one, optional_one=5):\n        pass\n")
    class_node = find_default_class(path, "dev", "fake", "foo")
    assert class_node is not None
    params = default_init_params(class_node, path, "dev", "fake")
    assert params[0].name == "required_one" and not params[0].has_default
    assert params[1].name == "optional_one" and params[1].has_default


def test_default_init_params_no_init_means_zero_params(tmp_path: Path):
    # A class with no explicit __init__ (e.g. _DefaultSignalSink) genuinely takes zero constructor
    # arguments - real, legal shape for {default = true} with no other keys at all.
    path = tmp_path / "asy_fake_driver.py"
    path.write_text("class _DefaultFoo:\n    pass\n")
    class_node = find_default_class(path, "dev", "fake", "foo")
    assert class_node is not None
    assert default_init_params(class_node, path, "dev", "fake") == ()


def test_find_default_class_syntax_error(tmp_path: Path):
    path = tmp_path / "asy_broken_driver.py"
    path.write_text("def f(:\n")
    with pytest.raises(BuildError, match="syntax error"):
        find_default_class(path, "dev", "broken", "foo")
