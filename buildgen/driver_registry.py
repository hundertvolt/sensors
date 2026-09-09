"""Resolves a device TOML's `driver = "<name>"` string to its real `src/` Python class -
BUILD_CHAIN_PLAN.md's acceptance criteria #1: "one small, explicit fact... nothing else". Primary
rule: the existing `asy_<name>_driver.py` -> `<Name>_Reader` naming convention (SPECIFICATION.md
Part C.2/C.5), discovered by AST-parsing the file - never imported (`src/` modules import
`machine`/`neopixel`/`asyncio.ThreadSafeFlag`, real MicroPython-only names this host-side CPython
tool can't import), and never by guessing the class name's casing (`BMP3xx_Reader` isn't
`"bmp3xx".upper() + "_Reader"`). Falls back to an explicit table only for a driver that genuinely
can't follow the file-naming pattern (singleton services with no `asy_<name>_driver.py` file, or
whose class isn't a `SensorReader`/`SensorReaderConfig` subclass at all)."""

import ast
from dataclasses import dataclass
from pathlib import Path

from buildgen.errors import BuildError

_READER_BASES = {"SensorReader", "SensorReaderConfig"}

# Singleton services genuinely can't follow asy_<name>_driver.py/*_Reader (BUILD_CHAIN_PLAN.md's
# "Acceptance criteria" #1's own named exception): fram/notification's own files aren't named
# "_driver.py", and none of the three defines a SensorReader/SensorReaderConfig subclass at all.
_OVERRIDES: dict[str, tuple[str, str]] = {
    "fram": ("asy_fram_manager", "AsyFramManager"),
    "neopixel": ("asy_neopixel_driver", "NeopixelDriver"),
    "notification": ("asy_notification_service", "NotificationCoordinator"),
}

# Singleton services: never more than one per device (SPECIFICATION.md Part C.14's own scoping).
SERVICE_DRIVERS = frozenset(_OVERRIDES)


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


def _find_reader_class(tree: ast.Module) -> str | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            base_names = {b.id for b in node.bases if isinstance(b, ast.Name)}
            if base_names & _READER_BASES:
                return node.name
    return None


def _class_needs_setup(tree: ast.Module, class_name: str) -> bool:
    # SensorReaderConfig subclasses always need it (base_classes.py's own async setup(), which
    # reads the on-flash ConfigManager); bare SensorReader subclasses never do (no ConfigManager -
    # e.g. SCD30_Reader). Neither base applies to a "service" override (AsyFramManager/
    # NeopixelDriver/NotificationCoordinator's own __init__ superclass differs per class) - fall
    # back to whether the class defines its own `async def setup` at all (true for AsyFramManager,
    # false for NeopixelDriver; NotificationCoordinator hits the SensorReaderConfig branch above
    # directly, since it does extend it).
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
    found_class_name = _find_reader_class(tree)
    if found_class_name is None:
        raise BuildError(
            device,
            f"{path} defines no SensorReader/SensorReaderConfig subclass - add one, or add {driver!r} to buildgen.driver_registry._OVERRIDES if it genuinely can't follow that convention",
            instance=driver,
        )
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
