"""Parses a driver module's `_WIRING` tuple (SPECIFICATION.md Part C.14.2) directly from its
source via AST - never imported (see driver_registry.py's own module docstring for why). `_WIRING`
is a real, live tuple at runtime (unlike the TYPE_CHECKING-only `WiringSchema`/`WiringField` alias
it's annotated with in config_manager.py) but this generator only ever needs its literal shape,
never the actual class objects it references.

Extends C.14.2's original 2-element `(toml_field, producer_class)` shape to 5 elements -
`(toml_field, producer_class, target, required, mode)` - resolving BUILD_CHAIN_PLAN.md's two open
`_WIRING`-coverage questions (see this session's PR description for the full rationale):
  - mode="kwarg": the resolved producer instance is passed as a constructor kwarg named `target`
    (covers every `fram=`/`fram_storage=` case).
  - mode="attr": the resolved producer instance's `target` attribute/bound method is passed as the
    value instead of the instance itself (NotificationCoordinator's `request_signal_cb` wants
    `pixel.request_signal`, not `pixel` itself - this is `signal_sink`'s resolution).
  - mode="setter": `<consumer>.<target>(<resolved producer>)` is called once, after both already
    exist (AsyConnTime's `set_ext_led()` - `[device.wiring].led_target`).
`_WIRING` no longer covers per-value measurement wiring (SGP40's old whole-object `comp_source`) -
BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md §2.9 generalized that into independent
`temperature_source`/`humidity_source` fields, resolved generically by attribute name via
`buildgen.value_wiring`'s own `_VALUE_WIRING` tuple instead, the same shape `warn_*` already used."""

import ast
from dataclasses import dataclass
from pathlib import Path

from buildgen.errors import BuildError

_VALID_MODES = {"kwarg", "attr", "setter"}


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
