"""Resolves a device TOML's `driver = "<name>"` to its real `src/` class via the existing
`asy_<name>_driver.py` -> `<Name>_Reader` convention (SPECIFICATION.md Part C.2/C.5), AST-parsed -
SPECIFICATION.md Part L.1's acceptance criterion #1. An explicit table covers the named exceptions."""

import ast
from dataclasses import dataclass
from pathlib import Path

from buildgen.errors import BuildError

_READER_BASES = {"SensorReader", "SensorReaderConfig"}

# Drivers that cannot follow the asy_<name>_driver.py/*_Reader convention (Part L.1's criterion
# 1): none defines a SensorReader/SensorReaderConfig subclass. The naming convention alone was
# never sufficient either - asy_uart_link_driver.py fits it and still needs the override.
_OVERRIDES: dict[str, tuple[str, str]] = {
    "fram": ("asy_fram_manager", "AsyFramManager"),
    "neopixel": ("asy_neopixel_driver", "NeopixelDriver"),
    "notification": ("asy_notification_service", "NotificationCoordinator"),
    "uart_link": ("asy_uart_link_driver", "UartLinkExerciser"),
}

# Every driver resolved through the override table, singleton or not: "needs an override" and
# "is a singleton" are independent facts that merely coincided for the first three entries. The
# actual singleton restriction lives in SINGLETON_SERVICE_DRIVERS below.
SERVICE_DRIVERS = frozenset(_OVERRIDES)

# Singleton services: never more than one per device (Part C.14). uart_link is excluded on
# purpose - it needs the same override, but a device wires two instances (initiator/responder)
# disambiguated by name_ext, rather than being forced to name_ext="" like the other three.
SINGLETON_SERVICE_DRIVERS = SERVICE_DRIVERS - {"uart_link"}


@dataclass(frozen=True)
class DriverInfo:
    driver: str  # the TOML `driver = "..."` string, e.g. "scd30"
    module: str  # src/ module name, e.g. "asy_scd30_driver"
    class_name: str  # e.g. "SCD30_Reader"
    kind: str  # "sensor" (SensorReader/SensorReaderConfig subclass) or "service"
    source_path: Path
    needs_setup: bool  # whether build_system() must await <instance>.setup() - see _class_needs_setup()


def _parse(path: Path, device: str, driver: str) -> ast.Module:
    try:
        return ast.parse(path.read_text(), filename=str(path))
    except SyntaxError as e:
        raise BuildError(device, f"{path} has a syntax error: {e}", instance=driver) from e


def _find_reader_classes(tree: ast.Module) -> "list[str]":
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            base_names = {b.id for b in node.bases if isinstance(b, ast.Name)}
            if base_names & _READER_BASES:
                found.append(node.name)
    return found


def _class_needs_setup(tree: ast.Module, class_name: str) -> bool:
    # SensorReaderConfig subclasses always need it (their async setup() reads ConfigManager);
    # bare SensorReader subclasses never do. Neither base applies to a service override, so those
    # fall back to whether the class defines an `async def setup` of its own at all.
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            bases = {b.id for b in node.bases if isinstance(b, ast.Name)}
            if "SensorReaderConfig" in bases:
                return True
            if "SensorReader" in bases:
                return False
            return any(isinstance(item, ast.AsyncFunctionDef) and item.name == "setup" for item in node.body)
    return False


def resolve_driver(driver: str, src_dir: Path, device: str) -> DriverInfo:
    if driver in _OVERRIDES:
        module, class_name = _OVERRIDES[driver]
        path = src_dir / f"{module}.py"
        if not path.is_file():
            raise BuildError(device, f"driver {driver!r} maps to {module}.py via the fallback table, but that file does not exist in {src_dir}", instance=driver)
        tree = _parse(path, device, driver)
        return DriverInfo(driver, module, class_name, "service", path, _class_needs_setup(tree, class_name))

    module = f"asy_{driver}_driver"
    path = src_dir / f"{module}.py"
    if not path.is_file():
        raise BuildError(device, f"unknown driver {driver!r}: no {path.name} in {src_dir} and no buildgen.driver_registry._OVERRIDES entry", instance=driver)
    tree = _parse(path, device, driver)
    found = _find_reader_classes(tree)
    if not found:
        raise BuildError(
            device,
            f"{path} defines no SensorReader/SensorReaderConfig subclass - add one, or add {driver!r} to buildgen.driver_registry._OVERRIDES if it genuinely can't follow that convention",
            instance=driver,
        )
    if len(found) > 1:
        raise BuildError(
            device,
            f"{path} defines more than one SensorReader/SensorReaderConfig subclass ({sorted(found)}) - ambiguous, add {driver!r} to buildgen.driver_registry._OVERRIDES to pick one explicitly",
            instance=driver,
        )
    found_class_name = found[0]
    return DriverInfo(driver, module, found_class_name, "sensor", path, _class_needs_setup(tree, found_class_name))


def parse_name_constant(path: Path, device: str, driver: str) -> str:
    # `_NAME = const("SCD30")` (or a plain `_NAME = "SCD30"`) - the instance_name()/REST-key
    # identity space (SPECIFICATION.md Part C.14.1), deliberately distinct from the TOML
    # driver/name_ext identity space wiring resolves against (see buildgen.wiring's own docstring).
    tree = _parse(path, device, driver)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_NAME" for t in node.targets):
            value = node.value
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "const" and value.args:
                value = value.args[0]
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                return value.value
            raise BuildError(device, f"{path}: _NAME is not a plain/const()-wrapped string literal", instance=driver)
    raise BuildError(device, f"{path} declares no module-level _NAME constant", instance=driver)
