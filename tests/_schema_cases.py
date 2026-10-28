"""The domain edges of every config field a src/ driver declares (SPECIFICATION.md C.5), read from its source text:
each bound from below, at it and from above, a set's edges and gap, both bools, None, and NaN/+-inf for a float field.
in_domain() answers from the declared row alone, so a check that drifts from its declaration fails the caller."""

import math

from _src_const import py_value
from _src_schema import src_schema

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from asy_config_manager import CfgValue, FieldSchema

_INF = float("inf")
_FIELD_MARK = ': "FieldSchema" = ('


def _float_step(bound: float) -> float:
    # About one part in a million of the bound: inside the rp2's single-precision float and the Unix port's double alike.
    magnitude, step = abs(bound) or 1.0, 1e-6
    while magnitude >= 10.0:
        magnitude, step = magnitude / 10.0, step * 10.0
    return step


def declared_fields(path: str) -> "list[FieldSchema]":
    # Every schema row of `path`: each `_VAL_*` const() schema, then each module-level FieldSchema literal, in source order.
    rows: list[FieldSchema] = []
    with open(path) as f:
        for line in f:
            head = line.split(" ", 1)[0]
            if head.startswith("_VAL_") and " = const((" in line:
                rows += list(src_schema(path, head))
            elif line.startswith("_") and _FIELD_MARK in line:
                rows.append(py_value(path, head.split(":", 1)[0]))  # type: ignore[arg-type]
    return rows


def domain_cases(field: "FieldSchema") -> "list[tuple[str, CfgValue, bool]]":
    # (label, value, inside the declared domain): the cases a PUT of this field must take or refuse.
    _name, kind, _default, low, high, special = field
    cases: list[tuple[str, CfgValue]] = []
    if kind == "bool":
        cases = [("True", True), ("False", False), ("the int 1", 1)]
    elif kind not in ("int", "float"):
        raise ValueError(f"{field[0]}: no domain cases for a {kind} field")
    elif isinstance(special, tuple) and low is None and high is None:
        members = sorted(v for v in special if isinstance(v, (int, float)))
        if len(members) != len(special):
            raise ValueError(f"{field[0]}: a {kind} set with a member that is no number")
        first, last = members[0], members[-1]
        below = first - 1 if kind == "int" else first - _float_step(first)
        above = last + 1 if kind == "int" else last + _float_step(last)
        cases = [("below the set's smallest", below), ("the set's smallest", first), ("the set's largest", last), ("above the set's largest", above)]
        for gap in range(int(first), int(last)) if kind == "int" else ():  # the first non-member, never a list of the span
            if gap not in members:
                cases.append(("a non-member inside the set's span", gap))
                break
    elif low is not None and high is not None:
        below = low - 1 if kind == "int" else low - _float_step(low)
        above = high + 1 if kind == "int" else high + _float_step(high)
        cases = [("below the minimum", below), ("the minimum", low), ("the maximum", high), ("above the maximum", above)]
        if special is not None and not isinstance(special, (tuple, list)):
            cases.append(("the special value", special))
    else:
        raise ValueError(f"{field[0]}: a {kind} field with neither a range nor a set")
    cases.append(("None", None))
    if kind == "float":
        cases += [("NaN", float("nan")), ("+inf", _INF), ("-inf", -_INF)]
    return [(label, value, in_domain(value, field)) for label, value in cases]


def in_domain(value: object, field: "FieldSchema") -> bool:
    _name, kind, _default, low, high, special = field
    if value is None:
        return False
    if kind == "bool":
        return type(value) is bool
    if kind == "int" and type(value) is not int:
        return False
    if kind == "float" and (type(value) not in (int, float) or not math.isfinite(value)):  # type: ignore[arg-type]
        return False
    if (type(special) is tuple and value in special) or (special is not None and type(special) is not tuple and value == special):
        return True
    return low is not None and high is not None and low <= value <= high  # type: ignore[operator]


def special_alone(field: "FieldSchema") -> bool:
    # A command field (default None, one scalar special): validated, never stored (C.5.2.1).
    return field[2] is None and field[5] is not None and type(field[5]) is not tuple
