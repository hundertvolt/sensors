"""Resolves a device TOML's `driver = "<name>"` to its real `src/` class via the existing
`asy_<name>_driver.py` -> `<Name>_Reader` convention (SPECIFICATION.md Part C.2/C.5), AST-parsed -
SPECIFICATION.md Part L.1's acceptance criterion #1. An explicit table covers the named exceptions."""

import ast
import functools
from dataclasses import dataclass
from pathlib import Path

from buildgen.errors import BuildError
from buildgen.source_ast import parse_source

_READER_BASES = {"SensorReader", "SensorReaderConfig"}

# Drivers that cannot follow the asy_<name>_driver.py/*_Reader convention (Part L.1's criterion
# 1): none defines a SensorReader/SensorReaderConfig subclass. The naming convention alone was
# never sufficient either - asy_uart_link_driver.py fits it and still needs the override.
_OVERRIDES: dict[str, tuple[str, str]] = {
    "fram": ("asy_fram_manager", "FRAMManager"),
    "neopixel": ("asy_neopixel_driver", "NeopixelDriver"),
    "notification": ("asy_notification_service", "NotificationService"),
    "uart_link": ("asy_uart_link_driver", "UARTLinkDriver"),
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


def read_source_text(path: Path, device: str, label: "str | None", *, field: "str | None" = None) -> str:
    # A src/ file's text, UTF-8 whatever the host's locale; an unreadable file is a build error placed at the
    # instance (label) or field the caller reads it for.
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise BuildError(device, f"{path} is not UTF-8 text: {e}", rule="source.syntax-error", fix="fix the file so Python can parse it", instance=label, field=field) from e
    except OSError as e:
        raise BuildError(device, f"cannot read {path}: {e}", rule="src.unreadable", fix=f"restore {path.name} in the source directory", instance=label, field=field) from e


def parse_source_file(path: Path, device: str, label: "str | None", *, field: "str | None" = None) -> "tuple[str, ast.Module]":
    # The file's text and its shared tree (source_ast caches it by the text, never the path).
    text = read_source_text(path, device, label, field=field)
    try:
        return text, parse_source(text, str(path))
    except SyntaxError as e:
        raise BuildError(device, f"{path} has a syntax error: {e}", rule="source.syntax-error", fix="fix the file so Python can parse it", instance=label, field=field) from e


def _find_reader_classes(tree: ast.Module) -> "list[str]":
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            base_names = {b.id for b in node.bases if isinstance(b, ast.Name)}
            if base_names & _READER_BASES:
                found.append(node.name)
    return found


def _class_needs_setup(tree: ast.Module, class_name: str) -> bool:
    # Every SensorReader/SensorReaderConfig subclass needs it: its setup() sets its own logger up first
    # (SPECIFICATION.md Part A.7). A service override needs it when it defines an `async def setup` itself.
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            bases = {b.id for b in node.bases if isinstance(b, ast.Name)}
            if bases & _READER_BASES:
                return True
            return any(isinstance(item, ast.AsyncFunctionDef) and item.name == "setup" for item in node.body)
    return False


def class_has_read_triggers(info: DriverInfo) -> bool:
    # Whether the class declares get_trigger_starters() itself, overriding SensorReader's empty default:
    # its read triggers then join the system service's stagger (SPECIFICATION.md Part C.9.1).
    text, _tree = parse_source_file(info.source_path, "", info.driver)
    return _declares_read_triggers(text, str(info.source_path), info.class_name)


# The facts below are cached by the file's text (each caller has parsed it first), not by its
# path: a file rewritten in place is read again. Each returns an immutable value.
@functools.lru_cache(maxsize=256)
def _declares_read_triggers(text: str, filename: str, class_name: str) -> bool:
    for node in ast.walk(parse_source(text, filename)):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return any(isinstance(item, ast.FunctionDef) and item.name == "get_trigger_starters" for item in node.body)
    return False


@functools.lru_cache(maxsize=256)
def _reader_classes(text: str, filename: str) -> "tuple[str, ...]":
    return tuple(_find_reader_classes(parse_source(text, filename)))


@functools.lru_cache(maxsize=256)
def _needs_setup(text: str, filename: str, class_name: str) -> bool:
    return _class_needs_setup(parse_source(text, filename), class_name)


def resolve_driver(driver: str, src_dir: Path, device: str) -> DriverInfo:
    if driver in _OVERRIDES:
        module, class_name = _OVERRIDES[driver]
        path = src_dir / f"{module}.py"
        if not path.is_file():
            raise BuildError(
                device,
                f"driver {driver!r} maps to {module}.py via the fallback table, but that file does not exist in {src_dir}",
                rule="driver.module-missing",
                fix=f"restore src/{module}.py, or correct its row in buildgen.driver_registry._OVERRIDES",
                instance=driver,
            )
        text, _tree = parse_source_file(path, device, driver)
        return DriverInfo(driver, module, class_name, "service", path, _needs_setup(text, str(path), class_name))

    module = f"asy_{driver}_driver"
    path = src_dir / f"{module}.py"
    if not path.is_file():
        raise BuildError(
            device,
            f"unknown driver {driver!r}: no {path.name} in {src_dir} and no buildgen.driver_registry._OVERRIDES entry",
            rule="driver.unknown",
            fix=f"correct the driver name, or add src/{path.name} defining its reader class",
            instance=driver,
        )
    text, _tree = parse_source_file(path, device, driver)
    found = _reader_classes(text, str(path))
    if not found:
        raise BuildError(
            device,
            f"{path} defines no SensorReader/SensorReaderConfig subclass",
            rule="driver.no-reader-class",
            fix=f"add one, or add {driver!r} to buildgen.driver_registry._OVERRIDES if it genuinely can't follow that convention",
            instance=driver,
        )
    if len(found) > 1:
        raise BuildError(
            device,
            f"{path} defines more than one SensorReader/SensorReaderConfig subclass ({sorted(found)}) - ambiguous",
            rule="driver.ambiguous-reader-class",
            fix=f"add {driver!r} to buildgen.driver_registry._OVERRIDES to pick one explicitly",
            instance=driver,
        )
    found_class_name = found[0]
    return DriverInfo(driver, module, found_class_name, "sensor", path, _needs_setup(text, str(path), found_class_name))


def parse_name_constant(path: Path, device: str, driver: str) -> str:
    # `_NAME = const("SCD30")` (or a plain `_NAME = "SCD30"`) - the instance_name()/REST-key
    # identity space (SPECIFICATION.md Part C.14.1), deliberately distinct from the TOML
    # driver/name_ext identity space wiring resolves against (see buildgen.wiring's own docstring).
    text, _tree = parse_source_file(path, device, driver)
    found, name = _name_constant(text, str(path))
    if name is not None:
        return name
    if found:
        raise BuildError(
            device,
            f"{path}: _NAME is not a plain/const()-wrapped string literal",
            rule="source.name-not-literal",
            fix='write it as _NAME = const("<NAME>") with a string literal',
            instance=driver,
        )
    raise BuildError(device, f"{path} declares no module-level _NAME constant", rule="source.name-missing", fix='declare a module-level _NAME = const("<NAME>")', instance=driver)


@functools.lru_cache(maxsize=256)
def _name_constant(text: str, filename: str) -> "tuple[bool, str | None]":
    # (whether a _NAME assignment exists, its string literal or None).
    for node in ast.walk(parse_source(text, filename)):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_NAME" for t in node.targets):
            value = node.value
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "const" and value.args:
                value = value.args[0]
            return True, value.value if isinstance(value, ast.Constant) and isinstance(value.value, str) else None
    return False, None


def data_fields(path: Path, class_name: str, device: str, label: str) -> frozenset[str]:
    # The fields of class_name's get_data() result, which a {source, field} reference names: its
    # return annotation must be a module-level `X = namedtuple("X", (<str literals>))`.
    text, _tree = parse_source_file(path, device, label)
    fields = _data_fields(text, str(path), class_name)
    if fields is None:
        raise BuildError(
            device,
            f"{path}: cannot read the fields of {class_name}.get_data()'s result",
            rule="source.fields-unreadable",
            fix="declare get_data()'s result as a module-level namedtuple with a literal field tuple",
            instance=label,
        )
    return fields


@functools.lru_cache(maxsize=64)
def _data_fields(source: str, filename: str, class_name: str) -> "frozenset[str] | None":
    # Keyed on the source text like the facts above, so an edited file is never answered stale.
    tree = parse_source(source, filename)
    result_name = _get_data_result_name(tree, class_name)
    return None if result_name is None else _namedtuple_fields(tree, result_name)


def _get_data_result_name(tree: ast.Module, class_name: str) -> "str | None":
    # The class's own `async def get_data(self) -> X` (or `-> "X"`): the name X, else None.
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.AsyncFunctionDef) and item.name == "get_data":
                    returns = item.returns
                    if isinstance(returns, ast.Name):
                        return returns.id
                    if isinstance(returns, ast.Constant) and isinstance(returns.value, str):
                        return returns.value
    return None


def _namedtuple_fields(tree: ast.Module, name: str) -> "frozenset[str] | None":
    # The module-level `name = namedtuple("name", (<str literals>))`: its field names, else None.
    for stmt in tree.body:
        if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name) and stmt.targets[0].id == name):
            continue
        call = stmt.value
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "namedtuple" and len(call.args) > 1):
            return None
        field_tuple = call.args[1]
        if not isinstance(field_tuple, ast.Tuple):
            return None
        names = [e.value for e in field_tuple.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
        return frozenset(names) if len(names) == len(field_tuple.elts) else None
    return None
