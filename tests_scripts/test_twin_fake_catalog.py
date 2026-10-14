"""Every bus-attached driver buildgen knows has its twin fake, its dispatch and its twin test, and the L2 suite's
per-driver tables cover exactly that set, each error-source name pinned to the driver's own _NAME. Reads source by
ast and the file tree; imports nothing from digital_twin/."""

import ast
from pathlib import Path
from types import ModuleType

import pytest

from buildgen.buildspec import BUS_ATTACHED_DRIVERS
from buildgen.driver_registry import parse_name_constant, resolve_driver

_REPO_ROOT = Path(__file__).resolve().parent.parent
_MACHINE = _REPO_ROOT / "digital_twin" / "machine.py"
_I2C_DRIVERS = frozenset(BUS_ATTACHED_DRIVERS - {"fram", "uart_link"})


def _errcount_name(driver: str) -> str:
    info = resolve_driver(driver, _REPO_ROOT / "src", "fixture-device")
    return parse_name_constant(info.source_path, "fixture-device", driver)


def _function(name: str) -> ast.FunctionDef:
    for node in ast.parse(_MACHINE.read_text()).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"digital_twin/machine.py no longer defines {name}()")


def _i2c_branches() -> "set[str]":
    # The driver strings _build_i2c_chip() compares against: `driver == "<name>"`.
    found: set[str] = set()
    for node in ast.walk(_function("_build_i2c_chip")):
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and node.left.id == "driver":
            found |= {c.value for c in node.comparators if isinstance(c, ast.Constant) and isinstance(c.value, str)}
    return found


def test_the_bus_attached_set_is_the_one_this_catalog_expects() -> None:
    # The premise: an I2C chip set, the SPI store and the UART pair. A new kind of bus needs its own row here.
    assert {"fram", "uart_link"} <= BUS_ATTACHED_DRIVERS
    assert _I2C_DRIVERS, "no I2C driver left to check"


def test_every_i2c_driver_has_its_chip_fake_and_its_dispatch_branch() -> None:
    missing_fakes = sorted(d for d in _I2C_DRIVERS if not (_REPO_ROOT / "digital_twin" / f"_{d}_chip.py").is_file())
    assert not missing_fakes, f"no digital_twin/_<driver>_chip.py for {missing_fakes}"
    assert _i2c_branches() == _I2C_DRIVERS, f"_build_i2c_chip() dispatches {sorted(_i2c_branches())}, buildgen's I2C drivers are {sorted(_I2C_DRIVERS)}"


def test_the_store_and_the_link_are_wired_by_their_own_seams() -> None:
    source = _MACHINE.read_text()
    assert "FRAMChip(" in ast.unparse(_function("_wire_spi_device")), "_wire_spi_device() no longer builds the FRAM fake"
    assert (_REPO_ROOT / "digital_twin" / "_fram_chip.py").is_file()
    assert "class UARTLink" in source and "def attach_crossover_jumper(" in source, "the UART pair's crossover is gone"


@pytest.mark.parametrize("driver", sorted(BUS_ATTACHED_DRIVERS))
def test_every_bus_attached_driver_has_its_twin_test(driver: str) -> None:
    assert (_REPO_ROOT / "tests" / f"test_digital_twin_{driver}.py").is_file(), f"no tests/test_digital_twin_{driver}.py"


def test_the_suites_per_driver_tables_cover_the_same_set(ci_suite: ModuleType) -> None:
    assert set(ci_suite._SUSTAINED_FAULT) == BUS_ATTACHED_DRIVERS
    assert set(ci_suite._DRIVER_ERRCOUNT_NAME) == BUS_ATTACHED_DRIVERS
    sensors = {d for d in BUS_ATTACHED_DRIVERS if resolve_driver(d, _REPO_ROOT / "src", "fixture-device").kind == "sensor"}
    assert sensors == ci_suite._MEASUREMENT_DRIVERS, "_MEASUREMENT_DRIVERS is every sensor-kind bus driver, the ones /measurements reports"


@pytest.mark.parametrize("driver", sorted(BUS_ATTACHED_DRIVERS))
def test_each_error_source_name_is_the_drivers_own(ci_suite: ModuleType, driver: str) -> None:
    # A hand table, so each row is pinned to the driver source's _NAME rather than trusted.
    assert ci_suite._DRIVER_ERRCOUNT_NAME[driver] == _errcount_name(driver)
