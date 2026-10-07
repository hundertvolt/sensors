"""Tests for buildgen.driver_registry: driver -> class resolution (the naming convention plus its
documented fallback table), and the _NAME-constant parser instance-name collision detection relies
on. See SPECIFICATION.md Part L.1's acceptance criterion #1."""

from pathlib import Path

import pytest

from buildgen.driver_registry import SERVICE_DRIVERS, SINGLETON_SERVICE_DRIVERS, DriverInfo, class_has_read_triggers, parse_name_constant, resolve_driver
from buildgen.errors import BuildError


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


@pytest.mark.parametrize(
    "driver,module,class_name,kind,needs_setup",
    [
        ("scd30", "asy_scd30_driver", "SCD30_Reader", "sensor", True),
        ("sgp40", "asy_sgp40_driver", "SGP40_Reader", "sensor", True),
        ("bmp3xx", "asy_bmp3xx_driver", "BMP3XX_Reader", "sensor", True),
        ("isl29125", "asy_isl29125_driver", "ISL29125_Reader", "sensor", True),
        ("fram", "asy_fram_manager", "FRAMManager", "service", True),
        ("neopixel", "asy_neopixel_driver", "NeopixelDriver", "service", True),
        ("notification", "asy_notification_service", "NotificationService", "service", True),
        ("uart_link", "asy_uart_link_driver", "UARTLinkDriver", "service", True),
    ],
)
def test_resolve_driver_real_drivers(src_dir: Path, driver: str, module: str, class_name: str, kind: str, *, needs_setup: bool) -> None:
    info = resolve_driver(driver, src_dir, "dev")
    assert info == DriverInfo(driver, module, class_name, kind, src_dir / f"{module}.py", needs_setup)


def test_a_plain_sensor_reader_subclass_needs_setup(tmp_path: Path) -> None:
    # SensorReader.setup() sets the reader's own logger up, so every reader joins the boot batch.
    (tmp_path / "asy_plain_driver.py").write_text("class Plain_Reader(SensorReader):\n    pass\n")
    assert resolve_driver("plain", tmp_path, "dev").needs_setup is True


def test_read_triggers_are_declared_by_the_reader_class_itself(tmp_path: Path) -> None:
    (tmp_path / "asy_trig_driver.py").write_text("class Trig_Reader(SensorReader):\n    def get_trigger_starters(self):\n        return []\n")
    (tmp_path / "asy_tick_driver.py").write_text("class Tick_Reader(SensorReaderConfig):\n    def get_timer_starters(self):\n        return []\n")
    assert class_has_read_triggers(resolve_driver("trig", tmp_path, "dev")) is True
    assert class_has_read_triggers(resolve_driver("tick", tmp_path, "dev")) is False


def test_resolve_driver_unknown_driver_raises(src_dir: Path) -> None:
    with pytest.raises(BuildError, match="unknown driver"):
        resolve_driver("nonexistent_chip", src_dir, "dev")


def test_resolve_driver_reads_the_class_name_not_a_naive_uppercase(tmp_path: Path) -> None:
    # The whole point of AST-based resolution: every real driver's class now matches the naive
    # "<driver>".upper() + "_Reader", so a driver file whose class does not proves the AST read.
    (tmp_path / "asy_chipx_driver.py").write_text("class ChipX_Reader(SensorReader):\n    pass\n")
    info = resolve_driver("chipx", tmp_path, "dev")
    assert info.class_name == "ChipX_Reader"
    assert info.class_name != "chipx".upper() + "_Reader"


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
    assert {"fram", "neopixel", "notification", "uart_link"} == SERVICE_DRIVERS


def test_singleton_service_drivers_excludes_uart_link() -> None:
    # uart_link resolves via the same override table (not a SensorReader/SensorReaderConfig
    # subclass either) but isn't a singleton - a device wires exactly two instances
    # (initiator/responder), disambiguated by name_ext like any other multi-instance driver.
    assert {"fram", "neopixel", "notification"} == SINGLETON_SERVICE_DRIVERS
    assert "uart_link" not in SINGLETON_SERVICE_DRIVERS


@pytest.mark.parametrize(
    "driver,expected_name",
    [("scd30", "SCD30"), ("sgp40", "SGP40"), ("bmp3xx", "BMP3XX"), ("isl29125", "ISL29125"), ("fram", "FRAM"), ("neopixel", "NEOPIXEL"), ("notification", "NOTIFY"), ("uart_link", "UART")],
)
def test_parse_name_constant_real_drivers(src_dir: Path, driver: str, expected_name: str) -> None:
    info = resolve_driver(driver, src_dir, "dev")
    assert parse_name_constant(info.source_path, "dev", driver) == expected_name


def test_parse_name_constant_confirms_notify_is_not_notification(src_dir: Path) -> None:
    # SPECIFICATION.md Part L.3's confirmed-real bug case: NotificationService's _NAME is
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


def test_needs_setup_returns_false_when_the_class_is_absent_from_the_file(tmp_path: Path) -> None:
    # The scan walks the whole module looking for the named class; a file that simply doesn't
    # define it must answer "no setup needed" rather than raise.
    import ast

    from buildgen.driver_registry import _class_needs_setup

    tree = ast.parse("class SomethingElse:\n    pass\n")
    assert _class_needs_setup(tree, "X_Reader") is False
