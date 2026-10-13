"""Never-imported AST extraction of a driver's `ConfigSchema`/`FieldSchema` constants - the same
never-import policy as `buildgen.driver_registry`. Schema constants must evaluate; other constants
are skipped. Used by `buildgen.definitions`; design rationale: SPECIFICATION.md Part H.5.1."""

import ast
import functools
from pathlib import Path

from buildgen.driver_registry import parse_source_file
from buildgen.errors import BuildError
from buildgen.source_ast import parse_source

# One driver-declared field's (type, default, min, max, special) - the name itself is the dict key
# `extract_field_schemas()` returns it under.
FieldSchema = tuple[object, object, object, object, object]

# asy_config_manager.py's own FieldSchema width: (name, type, default, min, max, special).
_FIELD_SCHEMA_LEN = 6
_FIELD_TYPES = ("int", "float", "str", "bool")  # asy_config_manager.py's type_or_range_error() branches
_SCHEMA_ANNOTATIONS = ("ConfigSchema", "FieldSchema")  # the last dotted part of a schema constant's annotation


def _eval_literal(node: "ast.expr", consts: "dict[str, ast.expr]", resolving: "frozenset[str]" = frozenset()) -> object:
    # `resolving` holds the names being resolved, so `_A = _B; _B = _A` reads as unresolvable
    # instead of recursing until Python's own limit.
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        operand = _eval_literal(node.operand, consts, resolving)
        if not isinstance(operand, (int, float)):
            raise TypeError(f"cannot negate non-numeric schema literal {operand!r}")
        return -operand
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "const" and len(node.args) == 1:
        return _eval_literal(node.args[0], consts, resolving)
    if isinstance(node, ast.Name):
        if node.id in resolving:
            raise ValueError(f"circular reference to {node.id!r} in schema literal")
        if node.id in consts:
            return _eval_literal(consts[node.id], consts, resolving | {node.id})
        raise ValueError(f"cannot resolve name {node.id!r} in schema literal")
    if isinstance(node, (ast.Tuple, ast.List)):
        return tuple(_eval_literal(elt, consts, resolving) for elt in node.elts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):  # a schema concatenation, `_VAL_A + _VAL_B`
        left, right = _eval_literal(node.left, consts, resolving), _eval_literal(node.right, consts, resolving)
        if not (isinstance(left, tuple) and isinstance(right, tuple)):
            raise TypeError(f"cannot concatenate non-tuple schema literals {left!r} + {right!r}")
        return left + right
    raise ValueError(f"unsupported schema literal node {ast.dump(node)}")


def _field_schema_from_tuple(tup: "tuple[object, ...]") -> "tuple[str, FieldSchema] | None":
    # Both real shapes in src/ are a 6-tuple (name, type, default, min, max, special): a string name
    # and one of asy_config_manager.py's four type names, so a tuple of six key names is not one.
    if len(tup) == _FIELD_SCHEMA_LEN and isinstance(tup[0], str) and tup[1] in _FIELD_TYPES:
        return tup[0], (tup[1], tup[2], tup[3], tup[4], tup[5])
    return None


def _is_schema_annotation(annotation: "ast.expr") -> bool:
    # `ConfigSchema`, `cm.FieldSchema`, `tuple[cm.FieldSchema, ...]` or the string form of any: the last
    # dotted part of the name, or of a tuple's element type, names it.
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        try:
            annotation = ast.parse(annotation.value, mode="eval").body
        except SyntaxError:
            return False
    if isinstance(annotation, ast.Subscript) and isinstance(annotation.value, ast.Name) and annotation.value.id == "tuple":
        element = annotation.slice.elts[0] if isinstance(annotation.slice, ast.Tuple) and annotation.slice.elts else annotation.slice
        return _is_schema_annotation(element)
    if isinstance(annotation, (ast.Name, ast.Attribute)):
        return ast.unparse(annotation).rsplit(".", 1)[-1] in _SCHEMA_ANNOTATIONS
    return False


def _record_problem(record: "tuple[object, ...]") -> str:
    # Why a record _field_schema_from_tuple() refused is not (name, type, default, min, max, special).
    if len(record) != _FIELD_SCHEMA_LEN:
        return f"record {record!r} has {len(record)} items, not {_FIELD_SCHEMA_LEN}"
    if not isinstance(record[0], str):
        return f"record {record!r} has a non-str name"
    return f"record {record!r} has type {record[1]!r}, none of {list(_FIELD_TYPES)}"


def _schema_fields(literal: object) -> "list[tuple[str, FieldSchema]] | str":
    # A schema constant's fields - one bare FieldSchema or a tuple of them - or why it is neither.
    if not isinstance(literal, tuple):
        return f"its value {literal!r} is not a tuple"
    records = (literal,) if literal and not isinstance(literal[0], tuple) else literal
    fields = []
    for record in records:
        if not isinstance(record, tuple):
            return f"record {record!r} is not a tuple"
        field = _field_schema_from_tuple(record)
        if field is None:
            return _record_problem(record)
        fields.append(field)
    return fields


def extract_field_schemas(source_path: Path, *, device: str = "<src>", instance_label: "str | None" = None, field: "str | None" = None) -> "dict[str, FieldSchema]":
    # Every field of every schema constant in `source_path` (named _VAL_* or annotated ConfigSchema/
    # FieldSchema), keyed by field name. A schema constant that cannot be read fails the build; any
    # other constant counts only as a one-field schema, best-effort, and is skipped otherwise.
    text, _tree = parse_source_file(source_path, device, instance_label, field=field)
    fields, problem = _scan_schemas(text, str(source_path))
    if problem is None:
        return dict(fields)  # a fresh dict: the cached scan stays as it was
    rule, name, lineno, detail = problem
    if rule == "schema.unreadable":
        raise BuildError(
            device,
            f"{source_path}:{lineno}: schema constant {name} cannot be read at build time: {detail}",
            rule="schema.unreadable",
            fix="keep schema constants literal (numbers, strings, tuples, const(), names of other literal constants)",
            instance=instance_label,
            field=field,
        )
    raise BuildError(
        device,
        f"{source_path}:{lineno}: schema constant {name} is malformed: {detail}",
        rule="schema.malformed",
        fix="write each record as (name, type, default, min, max, special): a str name and one of int, float, str, bool",
        instance=instance_label,
        field=field,
    )


@functools.lru_cache(maxsize=256)
def _scan_schemas(text: str, filename: str) -> "tuple[tuple[tuple[str, FieldSchema], ...], tuple[str, str, int, str] | None]":
    # The file's fields in order, or the first schema constant's problem as (rule, name, line, detail).
    # Cached by the text, not the path, and immutable: a rewritten file is scanned again.
    tree = parse_source(text, filename)
    consts: dict[str, ast.expr] = {}
    schema_lines: dict[str, int] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name, is_schema = node.targets[0].id, node.targets[0].id.startswith("_VAL_")
            consts[name] = node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None and isinstance(node.target, ast.Name):
            name, is_schema = node.target.id, node.target.id.startswith("_VAL_") or _is_schema_annotation(node.annotation)
            consts[name] = node.value
        else:
            continue
        if is_schema:
            schema_lines[name] = node.lineno
        else:
            schema_lines.pop(name, None)  # the last assignment decides, as it does for the value

    fields: dict[str, FieldSchema] = {}
    for name, value_node in consts.items():
        if name in schema_lines:
            checked = _checked_schema(value_node, consts)
            if isinstance(checked, tuple):
                return (), (checked[0], name, schema_lines[name], checked[1])
            fields.update(checked)
            continue
        try:
            literal = _eval_literal(value_node, consts)
        except (TypeError, ValueError):
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
    return tuple(fields.items()), None


def _checked_schema(value_node: "ast.expr", consts: "dict[str, ast.expr]") -> "list[tuple[str, FieldSchema]] | tuple[str, str]":
    # A schema constant's fields, or (rule, detail) for why it cannot be one.
    try:
        literal = _eval_literal(value_node, consts)
    except (TypeError, ValueError) as e:
        return "schema.unreadable", str(e)
    fields = _schema_fields(literal)
    return ("schema.malformed", fields) if isinstance(fields, str) else fields
