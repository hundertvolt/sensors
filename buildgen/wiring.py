"""AST-parses a driver module's `_WIRING` tuple, `(toml_field, producer_class, target, required,
mode)` - SPECIFICATION.md Part C.14.2 documents the shape and all three modes. Never imported: only
the literal shape is needed, never the class objects it references."""

import ast
from dataclasses import dataclass
from pathlib import Path

from buildgen.errors import BuildError

_VALID_MODES = {"kwarg", "attr", "setter"}


# mode decides how the resolved producer reaches its consumer (SPECIFICATION.md Part C.14.2):
# "kwarg" passes the instance as a constructor kwarg named `target`; "attr" passes the instance's
# `target` attribute/bound method instead (signal_sink wants `pixel.request_signal`, not `pixel`);
# "setter" calls `<consumer>.<target>(<producer>)` once, after both exist, so it gates nothing in
# construction order. Per-value measurement wiring is _VALUE_WIRING's, not _WIRING's (value_wiring.py).
@dataclass(frozen=True)
class WiringField:
    toml_field: str
    producer_class: str  # a plain class-name string (e.g. "SCD30_Reader") - never imported/resolved to a real type object
    target: str
    required: bool
    mode: str  # "kwarg" | "attr" | "setter"


def _class_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _find_wiring_value(tree: ast.Module) -> ast.expr | None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id == "_WIRING" for t in targets):
                return node.value
    return None


def parse_wiring(path: Path, device: str, driver: str) -> tuple[WiringField, ...]:
    try:
        tree = ast.parse(path.read_text(), filename=str(path))
    except SyntaxError as e:
        raise BuildError(device, f"{path} has a syntax error: {e}", instance=driver) from e

    value_node = _find_wiring_value(tree)
    if value_node is None:
        return ()
    if not isinstance(value_node, ast.Tuple):
        raise BuildError(device, f"{path}: _WIRING must be a literal tuple", instance=driver)

    fields = []
    for i, elt in enumerate(value_node.elts):
        label = f"_WIRING[{i}]"
        if not isinstance(elt, ast.Tuple) or len(elt.elts) != 5:
            raise BuildError(device, f"{path}: {label} must be a 5-tuple (toml_field, producer_class, target, required, mode)", instance=driver)
        f_field, f_class, f_target, f_required, f_mode = elt.elts
        if not (isinstance(f_field, ast.Constant) and isinstance(f_field.value, str)):
            raise BuildError(device, f"{path}: {label}[0] (toml_field) must be a string literal", instance=driver)
        class_name = _class_name(f_class)
        if class_name is None:
            raise BuildError(device, f"{path}: {label}[1] (producer_class) must be a plain class reference", instance=driver)
        if not (isinstance(f_target, ast.Constant) and isinstance(f_target.value, str)):
            raise BuildError(device, f"{path}: {label}[2] (target) must be a string literal", instance=driver)
        if not (isinstance(f_required, ast.Constant) and isinstance(f_required.value, bool)):
            raise BuildError(device, f"{path}: {label}[3] (required) must be a bool literal", instance=driver)
        if not (isinstance(f_mode, ast.Constant) and isinstance(f_mode.value, str) and f_mode.value in _VALID_MODES):
            raise BuildError(device, f"{path}: {label}[4] (mode) must be one of {sorted(_VALID_MODES)}", instance=driver)
        fields.append(WiringField(f_field.value, class_name, f_target.value, bool(f_required.value), f_mode.value))
    return tuple(fields)
