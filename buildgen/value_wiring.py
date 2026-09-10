"""AST-parses a driver module's `_VALUE_WIRING` tuple - `(toml_field, source_kwarg, field_kwarg,
required)` - the per-value measurement wiring that generalizes `warn_*`'s `{source, field}` shape to
any module consuming one scalar out of another's `get_data()` (matrix doc §2.9)."""

import ast
from dataclasses import dataclass
from pathlib import Path

from buildgen.errors import BuildError


@dataclass(frozen=True)
class ValueWiringField:
    toml_field: str
    source_kwarg: str
    field_kwarg: str
    required: bool


def _find_value_wiring(tree: ast.Module) -> ast.expr | None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id == "_VALUE_WIRING" for t in targets):
                return node.value
    return None


def parse_value_wiring(path: Path, device: str, driver: str) -> "tuple[ValueWiringField, ...]":
    try:
        tree = ast.parse(path.read_text(), filename=str(path))
    except SyntaxError as e:
        raise BuildError(device, f"{path} has a syntax error: {e}", instance=driver) from e

    value_node = _find_value_wiring(tree)
    if value_node is None:
        return ()
    if not isinstance(value_node, ast.Tuple):
        raise BuildError(device, f"{path}: _VALUE_WIRING must be a literal tuple", instance=driver)

    fields = []
    for i, elt in enumerate(value_node.elts):
        label = f"_VALUE_WIRING[{i}]"
        if not isinstance(elt, ast.Tuple) or len(elt.elts) != 4:
            raise BuildError(device, f"{path}: {label} must be a 4-tuple (toml_field, source_kwarg, field_kwarg, required)", instance=driver)
        f_field, f_source_kw, f_field_kw, f_required = elt.elts
        if not (isinstance(f_field, ast.Constant) and isinstance(f_field.value, str)):
            raise BuildError(device, f"{path}: {label}[0] (toml_field) must be a string literal", instance=driver)
        if not (isinstance(f_source_kw, ast.Constant) and isinstance(f_source_kw.value, str)):
            raise BuildError(device, f"{path}: {label}[1] (source_kwarg) must be a string literal", instance=driver)
        if not (isinstance(f_field_kw, ast.Constant) and isinstance(f_field_kw.value, str)):
            raise BuildError(device, f"{path}: {label}[2] (field_kwarg) must be a string literal", instance=driver)
        if not (isinstance(f_required, ast.Constant) and isinstance(f_required.value, bool)):
            raise BuildError(device, f"{path}: {label}[3] (required) must be a bool literal", instance=driver)
        fields.append(ValueWiringField(f_field.value, f_source_kw.value, f_field_kw.value, bool(f_required.value)))
    return tuple(fields)
