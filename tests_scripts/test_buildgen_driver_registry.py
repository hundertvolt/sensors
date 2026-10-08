"""Tests for buildgen.driver_registry: driver -> class resolution (the naming convention plus its
documented fallback table), and the _NAME-constant parser instance-name collision detection relies
on. See SPECIFICATION.md Part L.1's acceptance criterion #1."""

import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from buildgen.driver_registry import SERVICE_DRIVERS, SINGLETON_SERVICE_DRIVERS, DriverInfo, class_has_read_triggers, data_fields, parse_name_constant, resolve_driver
from buildgen.errors import BuildError

if TYPE_CHECKING:
    from collections.abc import Callable


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
    with pytest.raises(BuildError, match="unknown driver") as raised:
        resolve_driver("nonexistent_chip", src_dir, "dev")
    assert raised.value.rule == "driver.unknown"


def test_resolve_driver_reads_the_class_name_not_a_naive_uppercase(tmp_path: Path) -> None:
    # The whole point of AST-based resolution: every real driver's class now matches the naive
    # "<driver>".upper() + "_Reader", so a driver file whose class does not proves the AST read.
    (tmp_path / "asy_chipx_driver.py").write_text("class ChipX_Reader(SensorReader):\n    pass\n")
    info = resolve_driver("chipx", tmp_path, "dev")
    assert info.class_name == "ChipX_Reader"
    assert info.class_name != "chipx".upper() + "_Reader"


def test_resolve_driver_file_with_no_reader_subclass(tmp_path: Path) -> None:
    (tmp_path / "asy_bogus_driver.py").write_text("class NotAReader:\n    pass\n")
    with pytest.raises(BuildError, match="no SensorReader/SensorReaderConfig subclass") as raised:
        resolve_driver("bogus", tmp_path, "dev")
    assert raised.value.rule == "driver.no-reader-class"


def test_resolve_driver_file_with_two_reader_subclasses_is_ambiguous(tmp_path: Path) -> None:
    (tmp_path / "asy_dual_driver.py").write_text("class Foo_Reader(SensorReader):\n    pass\n\n\nclass Bar_Reader(SensorReaderConfig):\n    pass\n")
    with pytest.raises(BuildError, match="ambiguous") as raised:
        resolve_driver("dual", tmp_path, "dev")
    assert raised.value.rule == "driver.ambiguous-reader-class"


def test_resolve_driver_syntax_error_in_driver_file(tmp_path: Path) -> None:
    (tmp_path / "asy_broken_driver.py").write_text("class Foo(:\n")
    with pytest.raises(BuildError, match="syntax error") as raised:
        resolve_driver("broken", tmp_path, "dev")
    assert raised.value.rule == "source.syntax-error"


def test_resolve_driver_override_table_missing_file(tmp_path: Path) -> None:
    with pytest.raises(BuildError, match="does not exist") as raised:
        resolve_driver("fram", tmp_path, "dev")
    assert raised.value.rule == "driver.module-missing"


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
    with pytest.raises(BuildError, match="no module-level _NAME") as raised:
        parse_name_constant(path, "dev", "foo")
    assert raised.value.rule == "source.name-missing"


def test_parse_name_constant_non_string(tmp_path: Path) -> None:
    path = tmp_path / "asy_foo_driver.py"
    path.write_text("_NAME = 42\n")
    with pytest.raises(BuildError, match="not a plain/const") as raised:
        parse_name_constant(path, "dev", "foo")
    assert raised.value.rule == "source.name-not-literal"


def test_needs_setup_returns_false_when_the_class_is_absent_from_the_file(tmp_path: Path) -> None:
    # The scan walks the whole module looking for the named class; a file that simply doesn't
    # define it must answer "no setup needed" rather than raise.
    import ast

    from buildgen.driver_registry import _class_needs_setup

    tree = ast.parse("class SomethingElse:\n    pass\n")
    assert _class_needs_setup(tree, "X_Reader") is False


_UNREADABLE_FIX = "declare get_data()'s result as a module-level namedtuple with a literal field tuple"


@pytest.mark.parametrize(
    "driver,wired_fields",
    [("scd30", {"CO2", "Temp", "Hum"}), ("bmp3xx", {"Temp"}), ("sgp40", {"VOC"})],
)
def test_data_fields_reads_every_wired_producers_namedtuple(src_dir: Path, driver: str, wired_fields: "set[str]") -> None:
    # The fields the device TOMLs reference through {source, field}; "TS" is every producer's.
    info = resolve_driver(driver, src_dir, "dev")
    fields = data_fields(info.source_path, info.class_name, "dev", driver)
    assert wired_fields | {"TS"} <= fields
    assert "value" not in fields  # asy_sgp40_driver.py's _ConstValue providers are other classes


def test_data_fields_accepts_the_string_form_of_the_annotation(tmp_path: Path) -> None:
    path = tmp_path / "asy_chip_driver.py"
    path.write_text('CHIP = namedtuple("CHIP", ("A", "B"))\n\n\nclass Chip_Reader(SensorReader):\n    async def get_data(self) -> "CHIP":\n        pass\n')
    assert data_fields(path, "Chip_Reader", "dev", "chip") == frozenset({"A", "B"})


def test_data_fields_follows_a_rewritten_file(tmp_path: Path) -> None:
    # The cache keys on the source text, so an edit at the same path is never answered stale.
    path = tmp_path / "asy_chip_driver.py"
    reader = "\n\n\nclass Chip_Reader(SensorReader):\n    async def get_data(self) -> CHIP:\n        pass\n"
    path.write_text('CHIP = namedtuple("CHIP", ("A",))' + reader)
    assert data_fields(path, "Chip_Reader", "dev", "chip") == frozenset({"A"})
    path.write_text('CHIP = namedtuple("CHIP", ("A", "C"))' + reader)
    assert data_fields(path, "Chip_Reader", "dev", "chip") == frozenset({"A", "C"})


@pytest.mark.parametrize(
    "source",
    [
        pytest.param("class Chip_Reader(SensorReader):\n    async def get_data(self) -> dict:\n        pass\n", id="not-a-namedtuple"),
        pytest.param('FIELDS = ("A",)\nCHIP = namedtuple("CHIP", FIELDS)\n\n\nclass Chip_Reader(SensorReader):\n    async def get_data(self) -> CHIP:\n        pass\n', id="field-tuple-not-literal"),
        pytest.param('CHIP = namedtuple("CHIP", ("A", 1))\n\n\nclass Chip_Reader(SensorReader):\n    async def get_data(self) -> CHIP:\n        pass\n', id="field-not-a-string"),
        pytest.param('if True:\n    CHIP = namedtuple("CHIP", ("A",))\n\n\nclass Chip_Reader(SensorReader):\n    async def get_data(self) -> CHIP:\n        pass\n', id="not-module-level"),
        pytest.param("class Chip_Reader(SensorReader):\n    async def get_data(self):\n        pass\n", id="no-annotation"),
        pytest.param("class Chip_Reader(SensorReader):\n    pass\n", id="no-get-data"),
        pytest.param("class Other_Reader(SensorReader):\n    async def get_data(self) -> dict:\n        pass\n", id="no-such-class"),
    ],
)
def test_data_fields_refuses_anything_but_a_literal_namedtuple(tmp_path: Path, source: str) -> None:
    path = tmp_path / "asy_chip_driver.py"
    path.write_text(source)
    with pytest.raises(BuildError) as excinfo:
        data_fields(path, "Chip_Reader", "dev", "chip_a")
    assert excinfo.value.rule == "source.fields-unreadable"
    assert excinfo.value.fix == _UNREADABLE_FIX
    assert (excinfo.value.instance, excinfo.value.field) == ("chip_a", None)
    assert str(excinfo.value).startswith(f"[dev/chip_a] {path}: ")
    assert str(excinfo.value).endswith(" - fix: " + _UNREADABLE_FIX)


@pytest.mark.parametrize(
    "call",
    [
        pytest.param(lambda path: data_fields(path, "Chip_Reader", "fixture", "chip"), id="data_fields"),
        pytest.param(lambda path: parse_name_constant(path, "fixture", "chip"), id="parse_name_constant"),
        pytest.param(lambda path: class_has_read_triggers(DriverInfo("chip", "asy_chip_driver", "Chip_Reader", "sensor", path, needs_setup=True)), id="class_has_read_triggers"),
    ],
)
def test_an_unreadable_driver_file_is_a_build_error_not_a_raw_oserror(tmp_path: Path, call: "Callable[[Path], object]") -> None:
    path = tmp_path / "asy_chip_driver.py"  # never written
    with pytest.raises(BuildError, match="cannot read") as raised:
        call(path)
    assert (raised.value.rule, raised.value.fix) == ("src.unreadable", "restore asy_chip_driver.py in the source directory")


def test_the_driver_files_read_the_same_under_any_locale(repo_root: Path) -> None:
    # Driver files hold non-ASCII text; read under an ASCII locale with UTF-8 mode off, they must still parse.
    probe = (
        "import sys; sys.path.insert(0, sys.argv[1]); from pathlib import Path; "
        "from buildgen.driver_registry import class_has_read_triggers, data_fields, parse_name_constant, resolve_driver; "
        "info = resolve_driver('scd30', Path(sys.argv[1]) / 'src', 'fixture'); "
        "print(info.class_name, class_has_read_triggers(info), parse_name_constant(info.source_path, 'fixture', 'scd30'), sorted(data_fields(info.source_path, info.class_name, 'fixture', 'scd30'))[0])"
    )
    env = {"PATH": os.environ.get("PATH", ""), "LC_ALL": "C", "LANG": "C"}
    done = subprocess.run([sys.executable, "-I", "-X", "utf8=0", "-c", probe, str(repo_root)], env=env, capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr
    assert done.stdout.split() == ["SCD30_Reader", "False", "SCD30", "CO2"]


def test_the_driver_facts_follow_a_file_rewritten_at_the_same_path(tmp_path: Path) -> None:
    # Every fact is cached by the file's text, not its path: a rewritten file is read again.
    path = tmp_path / "asy_chip_driver.py"
    path.write_text('_NAME = const("ONE")\n\n\nclass One_Reader(SensorReader):\n    pass\n')
    first = resolve_driver("chip", tmp_path, "fixture")
    assert (first.class_name, parse_name_constant(path, "fixture", "chip"), class_has_read_triggers(first)) == ("One_Reader", "ONE", False)
    path.write_text('_NAME = const("TWO")\n\n\nclass Two_Reader(SensorReader):\n    def get_trigger_starters(self):\n        return []\n')
    second = resolve_driver("chip", tmp_path, "fixture")
    assert (second.class_name, parse_name_constant(path, "fixture", "chip"), class_has_read_triggers(second)) == ("Two_Reader", "TWO", True)
