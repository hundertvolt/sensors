"""Best-effort AST extraction of a driver's real `ConfigSchema`/`FieldSchema`-shaped module-level
constants (`config_manager.py`'s own `(name, type, default, min, max, special)` tuple, see
`src/config_manager.py`'s module docstring) - never imported, matching every other `buildgen`
driver-source scan (`buildgen.driver_registry`). This is real code the running firmware already
reads, not a comment tag: `buildgen.definitions` uses it to infer a website field's `kind`/`min`/
`max`/discrete-choice set automatically, so a `# @web` tag only needs to supply what the schema
tuple genuinely can't (label, unit, description, a discrete option's human-readable meaning)."""

import ast
from pathlib import Path

# One driver-declared field's (type, default, min, max, special) - the name itself is the dict key
# `extract_field_schemas()` returns it under.
FieldSchema = tuple[object, object, object, object, object]

# config_manager.py's own FieldSchema width: (name, type, default, min, max, special).
_FIELD_SCHEMA_LEN = 6


def _eval_literal(node: "ast.expr", consts: "dict[str, ast.expr]") -> object:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        operand = _eval_literal(node.operand, consts)
        if not isinstance(operand, (int, float)):
            raise TypeError(f"cannot negate non-numeric schema literal {operand!r}")
        return -operand
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "const" and len(node.args) == 1:
        return _eval_literal(node.args[0], consts)
    if isinstance(node, ast.Name):
        if node.id in consts:
            return _eval_literal(consts[node.id], consts)
        raise ValueError(f"cannot resolve name {node.id!r} in schema literal")
    if isinstance(node, (ast.Tuple, ast.List)):
        return tuple(_eval_literal(elt, consts) for elt in node.elts)
    raise ValueError(f"unsupported schema literal node {ast.dump(node)}")


def _field_schema_from_tuple(tup: "tuple[object, ...]") -> "tuple[str, FieldSchema] | None":
    # Both real shapes in src/ are a 6-tuple (name, type, default, min, max, special) whose first
    # two elements are always strings - config_manager.py's FieldSchema.
    if len(tup) == _FIELD_SCHEMA_LEN and isinstance(tup[0], str) and isinstance(tup[1], str):
        return tup[0], (tup[1], tup[2], tup[3], tup[4], tup[5])
    return None


def extract_field_schemas(source_path: Path) -> "dict[str, FieldSchema]":
    """Every module-level `NAME = const((("field", "type", default, min, max, special),))`
    (`ConfigSchema`-of-one, the project's own `_VAL_*` convention) or bare
    `NAME: "cm.FieldSchema" = ("field", "type", default, min, max, special)` assignment in
    `source_path`, keyed by the field's own name - not by the constant's Python name, which callers
    never need. Anything else (a driver's many other module-level constants) is silently skipped:
    this is a best-effort enrichment pass over real code the language itself already validated, not
    a comment tag subject to the tag family's own "near miss must fail loud" rule."""
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    consts: dict[str, ast.expr] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            consts[node.targets[0].id] = node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None and isinstance(node.target, ast.Name):
            consts[node.target.id] = node.value

    fields: dict[str, FieldSchema] = {}
    for value_node in consts.values():
        try:
            literal = _eval_literal(value_node, consts)
        except (ValueError, TypeError):
            continue
        if not isinstance(literal, tuple):
            continue
        direct = _field_schema_from_tuple(literal)
        if direct is not None:
            fields[direct[0]] = direct[1]
            continue
        if len(literal) == 1 and isinstance(literal[0], tuple):
            inner = _field_schema_from_tuple(literal[0])
            if inner is not None:
                fields[inner[0]] = inner[1]
    return fields
