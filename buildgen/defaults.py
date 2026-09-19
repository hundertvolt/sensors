"""AST-discovers a driver module's `_Default<ToMLFieldInPascalCase>` classes - the wiring-defaults
mechanism's schema-by-construction, where the class's own `__init__` signature IS the schema for a
`{default = true, ...}` TOML sub-table (SPECIFICATION.md Part L.6.2)."""

import ast
from dataclasses import dataclass
from pathlib import Path

from buildgen.errors import BuildError


@dataclass(frozen=True)
class DefaultParam:
    name: str
    has_default: bool


def default_class_name(toml_field: str) -> str:
    # "temperature_source" -> "_DefaultTemperatureSource" (§2.3's fixed naming convention).
    return "_Default" + "".join(part.capitalize() for part in toml_field.split("_"))


def find_default_class(path: Path, device: str, driver: str, toml_field: str) -> "ast.ClassDef | None":
    try:
        tree = ast.parse(path.read_text(), filename=str(path))
    except SyntaxError as e:
        raise BuildError(device, f"{path} has a syntax error: {e}", instance=driver) from e
    class_name = default_class_name(toml_field)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    return None


def default_init_params(class_node: "ast.ClassDef", _path: Path, _device: str, _driver: str) -> "tuple[DefaultParam, ...]":
    # A class with no explicit __init__ takes zero constructor arguments, the legal shape for a
    # defaultable field with no constant at all - not an error. _path/_device/_driver are unused
    # while this has no error path, kept for the same context shape find_default_class() uses.
    for item in class_node.body:
        if isinstance(item, ast.FunctionDef) and item.name == "__init__":
            positional = (item.args.posonlyargs + item.args.args)[1:]  # drop "self"
            num_required = len(positional) - len(item.args.defaults)
            return tuple(DefaultParam(a.arg, i >= num_required) for i, a in enumerate(positional))
    return ()


def default_class_defines_attr(class_node: "ast.ClassDef", attr: str) -> bool:
    return any(isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == attr for item in class_node.body)
