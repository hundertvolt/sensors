"""Tests for buildgen.wiring: parsing a driver's `_WIRING` tuple straight from source via AST
(SPECIFICATION.md Part C.14.2, extended - see this session's PR description). Covers the real
_WIRING declarations already in src/ plus every malformed shape the parser must reject."""

from pathlib import Path

import pytest

from buildgen.errors import BuildError
from buildgen.wiring import WiringField, parse_wiring


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


def test_parse_wiring_sgp40_fram_target(src_dir: Path) -> None:
    # comp_source is no longer a _WIRING entry at all - §2.9 generalized it into independent
    # per-value fields, resolved by buildgen.value_wiring instead (see test_buildgen_value_wiring.py).
    fields = parse_wiring(src_dir / "asy_sgp40_driver.py", "dev", "sgp40")
    assert fields == (WiringField("fram_target", "AsyFramManager", "fram_storage", False, "kwarg"),)


def test_parse_wiring_notification_signal_sink_is_attr_mode(src_dir: Path) -> None:
    fields = parse_wiring(src_dir / "asy_notification_service.py", "dev", "notification")
    assert WiringField("signal_sink", "NeopixelDriver", "request_signal", True, "attr") in fields


def test_parse_wiring_wifi_led_target_is_setter_mode(src_dir: Path) -> None:
    fields = parse_wiring(src_dir / "asy_wifi_service.py", "dev", "conn")
    assert WiringField("led_target", "NeopixelDriver", "set_ext_led", False, "setter") in fields


def test_parse_wiring_no_wiring_declared_returns_empty(tmp_path: Path) -> None:
    path = tmp_path / "asy_plain_driver.py"
    path.write_text("class Plain_Reader:\n    pass\n")
    assert parse_wiring(path, "dev", "plain") == ()


def test_parse_wiring_not_a_tuple(tmp_path: Path) -> None:
    path = tmp_path / "asy_bad_driver.py"
    path.write_text('_WIRING = "not a tuple"\n')
    with pytest.raises(BuildError, match="must be a literal tuple"):
        parse_wiring(path, "dev", "bad")


@pytest.mark.parametrize(
    "body,match",
    [
        ('_WIRING = (("only_two", Foo),)', "must be a 5-tuple"),
        ('_WIRING = ((1, Foo, "x", True, "kwarg"),)', r"\[0\] \(toml_field\) must be a string literal"),
        ('_WIRING = (("x", "Foo", "x", True, "kwarg"),)', r"\[1\] \(producer_class\) must be a plain class reference"),
        ('_WIRING = (("x", Foo, 1, True, "kwarg"),)', r"\[2\] \(target\) must be a string literal"),
        ('_WIRING = (("x", Foo, "x", "yes", "kwarg"),)', r"\[3\] \(required\) must be a bool literal"),
        ('_WIRING = (("x", Foo, "x", True, "bogus"),)', r"\[4\] \(mode\) must be one of"),
    ],
)
def test_parse_wiring_malformed_tuple_shapes(tmp_path: Path, body: str, match: str) -> None:
    path = tmp_path / "asy_bad_driver.py"
    path.write_text(f"class Foo:\n    pass\n\n\n{body}\n")
    with pytest.raises(BuildError, match=match):
        parse_wiring(path, "dev", "bad")


def test_parse_wiring_syntax_error(tmp_path: Path) -> None:
    path = tmp_path / "asy_broken_driver.py"
    path.write_text("def f(:\n")
    with pytest.raises(BuildError, match="syntax error"):
        parse_wiring(path, "dev", "broken")


def test_parse_wiring_accepts_attribute_class_reference(tmp_path: Path) -> None:
    # producer_class may be a dotted attribute reference (module.Class), not just a bare Name.
    path = tmp_path / "asy_bad_driver.py"
    path.write_text('import other_module\n\n\n_WIRING = (("x", other_module.Foo, "x", True, "kwarg"),)\n')
    fields = parse_wiring(path, "dev", "bad")
    assert fields == (WiringField("x", "Foo", "x", True, "kwarg"),)
