"""Parses a driver module's `_LIMITS` tuple directly via AST - never imported (same never-import
design as every other buildgen/ discovery module; see driver_registry.py's own docstring for why).
Each entry is `(toml_field, constraint)`, where `constraint` is either a `(min, max)` 2-tuple (each
a number literal or `None`, meaning that side is unchecked - `min == max` expresses an exact-value
requirement) or `frozenset({...})` of exact legal int values, for a driver-declared, real,
already-documented-in-code domain a TOML field's value must satisfy (e.g. BMP388/390's
address-select pin: exactly 0x76 or 0x77).

Scope (BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md §5.2/§10.1 item 3): only fields with a genuine,
already-documented constraint get a `_LIMITS` entry - never an invented bound. `@requires` tags
(requires_tag.py) already cover the separate, conditional/cross-object case (a bus needs a stricter
setting only because a specific driver is attached to it); `_LIMITS` is for a field's own
unconditional domain."""

import ast
from dataclasses import dataclass
from pathlib import Path

from buildgen.errors import BuildError


@dataclass(frozen=True)
class LimitField:
    toml_field: str
    choices: "frozenset[int] | None"  # enumerated legal values, if that shape was used - min/max are both None when this is set
    min: "int | float | None" = None
    max: "int | float | None" = None


class _NotNumeric:
    pass


_NOT_NUMERIC = _NotNumeric()


def _find_limits_value(tree: ast.Module) -> ast.expr | None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id == "_LIMITS" for t in targets):
                return node.value
    return None


def _parse_bound(node: ast.expr) -> "int | float | None | _NotNumeric":
    if isinstance(node, ast.Constant):
        if node.value is None:
            return None
        if isinstance(node.value, bool):
            return _NOT_NUMERIC
        if isinstance(node.value, (int, float)):
            return node.value
        return _NOT_NUMERIC
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        inner = _parse_bound(node.operand)
        if isinstance(inner, (int, float)):
            return -inner
        return _NOT_NUMERIC
    return _NOT_NUMERIC


def _parse_choices(node: ast.expr) -> "frozenset[int] | None":
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "frozenset" and len(node.args) == 1):
        return None
    container = node.args[0]
    if not isinstance(container, (ast.Set, ast.List, ast.Tuple)):
        return None
    values: list[int] = []
    for elt in container.elts:
        bound = _parse_bound(elt)
        if not isinstance(bound, int):
            return None
        values.append(bound)
    return frozenset(values)


def parse_limits(path: Path, device: str, driver: str) -> "tuple[LimitField, ...]":
    try:
        tree = ast.parse(path.read_text(), filename=str(path))
    except SyntaxError as e:
        raise BuildError(device, f"{path} has a syntax error: {e}", instance=driver) from e

    value_node = _find_limits_value(tree)
    if value_node is None:
        return ()
    if not isinstance(value_node, ast.Tuple):
        raise BuildError(device, f"{path}: _LIMITS must be a literal tuple", instance=driver)

    fields = []
    for i, elt in enumerate(value_node.elts):
        label = f"_LIMITS[{i}]"
        if not isinstance(elt, ast.Tuple) or len(elt.elts) != 2:
            raise BuildError(device, f"{path}: {label} must be a 2-tuple (toml_field, constraint)", instance=driver)
        f_field, f_constraint = elt.elts
        if not (isinstance(f_field, ast.Constant) and isinstance(f_field.value, str)):
            raise BuildError(device, f"{path}: {label}[0] (toml_field) must be a string literal", instance=driver)

        choices = _parse_choices(f_constraint)
        if choices is not None:
            fields.append(LimitField(f_field.value, choices))
            continue

        if not (isinstance(f_constraint, ast.Tuple) and len(f_constraint.elts) == 2):
            raise BuildError(device, f"{path}: {label}[1] (constraint) must be a (min, max) 2-tuple or frozenset({{...}}) of ints", instance=driver)
        min_node, max_node = f_constraint.elts
        min_val = _parse_bound(min_node)
        max_val = _parse_bound(max_node)
        if isinstance(min_val, _NotNumeric) or isinstance(max_val, _NotNumeric):
            raise BuildError(device, f"{path}: {label}[1]'s (min, max) entries must each be a number literal or None", instance=driver)
        fields.append(LimitField(f_field.value, None, min_val, max_val))
    return tuple(fields)
