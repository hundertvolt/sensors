"""AST-discovers a driver module's `_Default<ToMLFieldInPascalCase>` classes - the wiring-defaults
mechanism's schema-by-construction, where the class's own `__init__` signature IS the schema for a
`{default = true, ...}` TOML sub-table (SPECIFICATION.md Part L.6.2)."""

import ast
from dataclasses import dataclass
from pathlib import Path

from buildgen.driver_registry import parse_source_file


@dataclass(frozen=True)
class DefaultParam:
    name: str
    has_default: bool


def default_class_name(toml_field: str) -> str:
    # "temperature_source" -> "_DefaultTemperatureSource" (SPECIFICATION.md Part L.6.2's convention).
    return "_Default" + "".join(part.capitalize() for part in toml_field.split("_"))


def find_default_class(path: Path, device: str, driver: str, toml_field: str) -> "ast.ClassDef | None":
    _text, tree = parse_source_file(path, device, driver)
    class_name = default_class_name(toml_field)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    return None


def default_init_params(class_node: "ast.ClassDef") -> "tuple[DefaultParam, ...]":
    # A class with no explicit __init__ takes zero constructor arguments, the legal shape for a
    # defaultable field with no constant at all - not an error. Keyword-only parameters join the
    # positional ones: kw_defaults holds None for one without a default.
    for item in class_node.body:
        if isinstance(item, ast.FunctionDef) and item.name == "__init__":
            positional = (item.args.posonlyargs + item.args.args)[1:]  # drop "self"
            num_required = len(positional) - len(item.args.defaults)
            params = [DefaultParam(a.arg, i >= num_required) for i, a in enumerate(positional)]
            params += [DefaultParam(a.arg, d is not None) for a, d in zip(item.args.kwonlyargs, item.args.kw_defaults, strict=True)]
            return tuple(params)
    return ()


def default_class_defines_attr(class_node: "ast.ClassDef", attr: str) -> bool:
    return any(isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == attr for item in class_node.body)
