"""Tests for buildgen.driver_registry: driver -> class resolution (the naming convention plus its
documented fallback table), and the _NAME-constant parser instance-name collision detection relies
on. See BUILD_CHAIN_PLAN.md's acceptance criteria #1."""

from pathlib import Path

import pytest

from buildgen.driver_registry import SERVICE_DRIVERS, DriverInfo, parse_name_constant, resolve_driver
from buildgen.errors import BuildError


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


@pytest.mark.parametrize(
    "driver,module,class_name,kind,needs_setup",
    [
        ("scd30", "asy_scd30_driver", "SCD30_Reader", "sensor", False),
        ("sgp40", "asy_sgp40_driver", "SGP40_Reader", "sensor", True),
        ("bmp3xx", "asy_bmp3xx_driver", "BMP3xx_Reader", "sensor", True),
        ("fram", "asy_fram_manager", "AsyFramManager", "service", True),
        ("neopixel", "asy_neopixel_driver", "NeopixelDriver", "service", False),
        ("notification", "asy_notification_service", "NotificationCoordinator", "service", True),
    ],
)
def test_resolve_driver_real_drivers(src_dir: Path, driver: str, module: str, class_name: str, kind: str, needs_setup: bool) -> None:
    info = resolve_driver(driver, src_dir, "dev")
    assert info == DriverInfo(driver, module, class_name, kind, src_dir / f"{module}.py", needs_setup)


def test_resolve_driver_unknown_driver_raises(src_dir: Path) -> None:
    with pytest.raises(BuildError, match="unknown driver"):
        resolve_driver("nonexistent_chip", src_dir, "dev")


def test_resolve_driver_bmp3xx_naming_convention_is_not_a_naive_uppercase(src_dir: Path) -> None:
    # The whole point of AST-based resolution: BMP3xx_Reader isn't "bmp3xx".upper() + "_Reader"
    # ("BMP3XX_Reader") - a naive string-transform resolver would get this wrong.
    info = resolve_driver("bmp3xx", src_dir, "dev")
    assert info.class_name == "BMP3xx_Reader"
    assert info.class_name != "bmp3xx".upper() + "_Reader"


def test_resolve_driver_file_with_no_reader_subclass(tmp_path: Path) -> None:
    (tmp_path / "asy_bogus_driver.py").write_text("class NotAReader:\n    pass\n")
    with pytest.raises(BuildError, match="no SensorReader/SensorReaderConfig subclass"):
        resolve_driver("bogus", tmp_path, "dev")


def test_resolve_driver_file_with_two_reader_subclasses_is_ambiguous(tmp_path: Path) -> None:
    (tmp_path / "asy_dual_driver.py").write_text("class Foo_Reader(SensorReader):\n    pass\n\n\nclass Bar_Reader(SensorReaderConfig):\n    pass\n")
    with pytest.raises(BuildError, match="ambiguous"):
        resolve_driver("dual", tmp_path, "dev")


def test_resolve_driver_syntax_error_in_driver_file(tmp_path: Path) -> None:
    (tmp_path / "asy_broken_driver.py").write_text("class Foo(:\n")
    with pytest.raises(BuildError, match="syntax error"):
        resolve_driver("broken", tmp_path, "dev")


def test_resolve_driver_override_table_missing_file(tmp_path: Path) -> None:
    with pytest.raises(BuildError, match="does not exist"):
        resolve_driver("fram", tmp_path, "dev")


def test_service_drivers_frozenset_matches_override_table() -> None:
    assert SERVICE_DRIVERS == {"fram", "neopixel", "notification"}


@pytest.mark.parametrize(
    "driver,expected_name",
    [("scd30", "SCD30"), ("sgp40", "SGP40"), ("bmp3xx", "BMP3XX"), ("fram", "FRAM"), ("neopixel", "NEOPIXEL"), ("notification", "NOTIFY")],
)
def test_parse_name_constant_real_drivers(src_dir: Path, driver: str, expected_name: str) -> None:
    info = resolve_driver(driver, src_dir, "dev")
    assert parse_name_constant(info.source_path, "dev", driver) == expected_name


def test_parse_name_constant_confirms_notify_is_not_notification(src_dir: Path) -> None:
    # BUILD_CHAIN_PLAN.md's own confirmed-real bug case: NotificationCoordinator's _NAME is
    # "NOTIFY", not "NOTIFICATION" - instance_name()/_NAME is a different naming space than the
    # TOML driver identity ("notification") wiring resolves against.
    info = resolve_driver("notification", src_dir, "dev")
    name = parse_name_constant(info.source_path, "dev", "notification")
    assert name == "NOTIFY"
    assert name != "notification".upper()


def test_parse_name_constant_missing(tmp_path: Path) -> None:
    path = tmp_path / "asy_foo_driver.py"
    path.write_text("class Foo_Reader(SensorReader):\n    pass\n")
    with pytest.raises(BuildError, match="no module-level _NAME"):
        parse_name_constant(path, "dev", "foo")


def test_parse_name_constant_non_string(tmp_path: Path) -> None:
    path = tmp_path / "asy_foo_driver.py"
    path.write_text("_NAME = 42\n")
    with pytest.raises(BuildError, match="not a plain/const"):
        parse_name_constant(path, "dev", "foo")
