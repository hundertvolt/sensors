"""Every config schema is checked statically (SPECIFICATION.md C.5): each `_VAL_*` or `ConfigSchema`/`FieldSchema`
constant of src/ and of every generated device module is a run of well-formed 6-field records whose default passes
the store's own validator, float bounds within 2**24 and each field name declared once per module."""

import ast
import re
import shutil
import sys
import types
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

import pytest
from _devices import DEVICE_NAMES
from _repo_scan import REPO_ROOT
from _script_loader import load_script_module

from buildgen import schema_ast
from buildgen.generate import generate_device

_SRC = REPO_ROOT / "src"
_FIXTURE_TOMLS = ("multi_instance.toml", "novel_combo.toml")
# A ConfigSchema spelled out as its alias's own tuple[FieldSchema, ...] (the LED command fields).
_SPELLED_OUT_SCHEMA = re.compile(r"tuple\[(?:\w+\.)?FieldSchema, \.\.\.\]")
_TYPES: dict[str, type] = {"int": int, "float": float, "str": str, "bool": bool}
# rp2 builds single-precision floats (ports/rp2/mpconfigport.h, MICROPY_FLOAT_IMPL_FLOAT at v1.29.0): every
# integer up to 2**24 is exact, so a float field's bounds stay inside it and a field needing more is an int.
_FLOAT_LIMIT = 2**24



class Validator(Protocol):
    # asy_config_manager.type_or_range_error()'s shape.
    def __call__(self, check_val: object, field: "tuple[object, ...]", *, check_special: bool = True) -> "tuple[bool, object]": ...


def _annotation(node: ast.expr | None) -> str:
    if node is None:
        return ""
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else ast.unparse(node)


def _schema_kind(annotation: str) -> str:
    # "record" for a FieldSchema, "schema" for a ConfigSchema, "" for anything else: an annotation
    # names one by its last dotted part (cm.ConfigSchema is the generated modules' form).
    if _SPELLED_OUT_SCHEMA.fullmatch(annotation):
        return "schema"
    return {"FieldSchema": "record", "ConfigSchema": "schema"}.get(annotation.rsplit(".", 1)[-1], "")


def _is_aggregate(value: ast.expr) -> bool:
    # Built from other constants by name (`_VAL_A + _VAL_B`, or a bare `_VAL_A`): its records are theirs.
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "const" and len(value.args) == 1:
        return _is_aggregate(value.args[0])
    if isinstance(value, ast.BinOp) and isinstance(value.op, ast.Add):
        return _is_aggregate(value.left) and _is_aggregate(value.right)
    return isinstance(value, ast.Name)


def schema_constants(source: str) -> Iterator[tuple[str, int, list[object] | str, bool]]:
    # (name, line, its records or why they cannot be read, whether it aggregates other constants)
    # for each selected module-level constant.
    tree = ast.parse(source)
    consts: dict[str, ast.expr] = {}
    selected: list[tuple[str, ast.expr, int, bool]] = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name, value, kind = node.targets[0].id, node.value, ""
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            name, value, kind = node.target.id, node.value, _schema_kind(_annotation(node.annotation))
        else:
            continue
        consts[name] = value
        if name.startswith("_VAL_") or kind:
            selected.append((name, value, node.lineno, kind == "record"))
    for name, value, line, one_field in selected:
        try:
            literal = schema_ast._eval_literal(value, consts)
        except (TypeError, ValueError) as e:
            yield name, line, f"cannot be evaluated ({e})", False
            continue
        if one_field:
            yield name, line, [literal], False
        elif isinstance(literal, tuple):
            yield name, line, list(literal), _is_aggregate(value)
        else:
            yield name, line, f"is {literal!r}, not a tuple of field records", False


def duplicate_name_findings(path: str, source: str) -> list[str]:
    # Each field name once over a module's leaf schemas; an aggregate repeats its parts' names, so it is skipped.
    owner: dict[str, str] = {}
    found = []
    for name, line, records, aggregate in schema_constants(source):
        if aggregate or isinstance(records, str):
            continue
        for record in records:
            if not (isinstance(record, tuple) and record and isinstance(record[0], str)):
                continue  # record_findings() reports the shape
            if record[0] in owner:
                found.append(f"{path}:{line} field {record[0]!r} is declared by both {owner[record[0]]} and {name}")
            else:
                owner[record[0]] = name
    return found


def record_findings(record: object, validator: Validator) -> list[str]:
    if not (isinstance(record, tuple) and len(record) == 6 and isinstance(record[0], str) and isinstance(record[1], str)):
        return [f"{record!r} is not a 6-tuple (name, type, default, min, max, special) with a str name and type"]
    name, kind, default, lo, hi, special = record
    if kind not in _TYPES:
        return [f"{name}: type {kind!r} is none of {sorted(_TYPES)}"]
    found = []
    bound_type = None if kind == "bool" else float if kind == "float" else int
    for label, bound in (("min", lo), ("max", hi)):
        if bound is not None and type(bound) is not bound_type:
            found.append(f"{name}: {label} {bound!r} is not {'None' if bound_type is None else bound_type.__name__ + ' or None'}")
        elif kind == "float" and bound is not None and abs(bound) > _FLOAT_LIMIT:
            found.append(f"{name}: {label} {bound!r} lies outside +-2**24, where single precision stops being exact")
    if type(lo) is bound_type and type(hi) is bound_type and lo > hi:
        found.append(f"{name}: min {lo!r} > max {hi!r}")
    specials = special if isinstance(special, tuple) else () if special is None else (special,)
    if any(type(s) is not _TYPES[kind] for s in specials):
        found.append(f"{name}: special {special!r} is not of the field's type {kind}")
    # A record with neither default nor special stores none (a chip-held or dispatch-only field); a file store
    # serving one refuses it at setup() (CFG_BAD_DEFAULT). A special set has no one value to stand alone.
    value = special if default is None else default
    if default is None and isinstance(special, tuple):
        found.append(f"{name}: no default, and a special set cannot stand alone")
    elif value is not None and validator(value, record, check_special=True)[0]:
        found.append(f"{name}: default {default!r} (special {special!r}) fails the field's own validator")
    return found


def module_findings(path: str, source: str, validator: Validator) -> list[str]:
    found = []
    for name, line, records, _aggregate in schema_constants(source):
        if isinstance(records, str):
            found.append(f"{path}:{line} {name} {records}")
            continue
        found.extend(f"{path}:{line} {name}: {finding}" for record in records for finding in record_findings(record, validator))
    return found + duplicate_name_findings(path, source)


@pytest.fixture(scope="module")
def validator() -> Validator:
    # asy_config_manager.py loaded as a plain module under CPython, its two MicroPython-only imports stubbed.
    stubs = {"micropython": types.ModuleType("micropython"), "asy_print_log": types.ModuleType("asy_print_log")}
    stubs["micropython"].const = lambda value: value  # type: ignore[attr-defined]
    stubs["asy_print_log"].DEFAULT_LOG = None  # type: ignore[attr-defined]
    stubs["asy_print_log"].make_logger = None  # type: ignore[attr-defined]
    saved = {name: sys.modules.get(name) for name in stubs}
    sys.modules.update(stubs)
    try:
        module = load_script_module(_SRC / "asy_config_manager.py", "_config_manager_under_check")
    finally:
        for name, previous in saved.items():
            if previous is None:
                del sys.modules[name]
            else:
                sys.modules[name] = previous
    check: Validator = module.type_or_range_error
    return check


@pytest.fixture(scope="module")
def modules(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    out = tmp_path_factory.mktemp("generated_schemas")
    found = {f"src/{p.name}": p.read_text(encoding="utf-8") for p in sorted(_SRC.glob("*.py"))}
    tomls = [REPO_ROOT / "devices" / f"{d}.toml" for d in DEVICE_NAMES]
    tomls += [REPO_ROOT / "tests_scripts" / "buildgen_fixtures" / name for name in _FIXTURE_TOMLS]
    for toml in tomls:
        generated = out / f"sensortask_{toml.stem}.py"
        generated.write_text(generate_device(toml, _SRC, REPO_ROOT / "ext").module_source, encoding="utf-8")
        found[f"generated/{generated.name}"] = generated.read_text(encoding="utf-8")
    return found


def test_every_schema_in_src_and_the_generated_modules_is_well_formed(modules: dict[str, str], validator: Validator) -> None:
    found = [line for path, source in modules.items() for line in module_findings(path, source, validator)]
    assert not found, "\n".join(found)


def test_the_scan_reads_every_device_and_concatenated_schemas(modules: dict[str, str]) -> None:
    assert sum(path.startswith("generated/") for path in modules) == len(DEVICE_NAMES) + len(_FIXTURE_TOMLS)
    read = {name: (records, aggregate) for name, _line, records, aggregate in schema_constants(modules["src/asy_notification_service.py"])}
    own, aggregate = read["_VAL_OWN_SCHEMA"]  # three concatenations deep
    assert isinstance(own, list)
    assert aggregate
    assert [r[0] for r in own if isinstance(r, tuple)] == ["OnH", "OnM", "OffH", "OffM", "FlashBri", "FlashInterval", "FlashDur", "AutoOn"]
    records = sum(len(r) for path, source in modules.items() for _n, _l, r, _a in schema_constants(source) if not isinstance(r, str))
    assert records > 50, records  # every driver's fields, not a vacuous scan


def test_the_scan_reads_the_generated_warn_schemas_and_the_led_command_fields(modules: dict[str, str]) -> None:
    # The generated modules annotate their warn-signal schemas cm.ConfigSchema; the LED command
    # fields spell the alias out as tuple[cm.FieldSchema, ...]. Both are schemas the lint must read.
    warn = {name for path, source in modules.items() if path.startswith("generated/") for name, _l, _r, _a in schema_constants(source)}
    assert {"_FIELD_WARN_CO2", "_FIELD_WARN_VOC", "_FIELD_WARN_HUM"} <= warn
    webserver = {name: records for name, _l, records, _a in schema_constants(modules["src/asy_webserver_service.py"])}
    led = webserver["_LIGHT_CMD_FIELDS"]
    assert isinstance(led, list)
    assert [r[0] for r in led if isinstance(r, tuple)] == ["R", "G", "B", "T"]


def test_the_evaluator_concatenates_tuples_and_refuses_anything_else() -> None:
    consts = {"_A": ast.parse("(('A', 'int', 1, 0, 2, None),)", mode="eval").body}
    assert schema_ast._eval_literal(ast.parse("_A + _A", mode="eval").body, consts) == (("A", "int", 1, 0, 2, None),) * 2
    for text in ("1 + 2", "_A + 1"):
        with pytest.raises(TypeError):
            schema_ast._eval_literal(ast.parse(text, mode="eval").body, consts)


_BITES = (
    ('("PresOffset", "float", 0.0, -500.0, 500.0, None)', '("PresOffset", "float", 0.0, -500.0, 16777217.0, None)', "PresOffset: max 16777217.0 lies outside"),
    ('("PresOffset", "float", 0.0, -500.0, 500.0, None)', '("PresOffset", "float", 0.0, -500, 500.0, None)', "PresOffset: min -500 is not float or None"),
    ('("MeanAtmTemp", "float", 15.0, -40.0, 50.0, None)', '("MeanAtmTemp", "float", 15.0, -40.0, 50.0)', "is not a 6-tuple"),
    ('("TempOffset", "float", 0.0, -10.0, 10.0, None)', '("TempOffset", "float", 0.0, 10.0, -10.0, None)', "TempOffset: min 10.0 > max -10.0"),
    ('("TempOffset", "float", 0.0, -10.0, 10.0, None)', '("PresOffset", "float", 0.0, -10.0, 10.0, None)', "field 'PresOffset' is declared by both _VAL_PRES_OFFSET and _VAL_TEMP_OFFSET"),
    ('("MeanAtmTemp", "float", 15.0, -40.0, 50.0, None)', '("MeanAtmTemp", "float", 99.0, -40.0, 50.0, None)', "MeanAtmTemp: default 99.0 (special None) fails"),
)


@pytest.mark.parametrize(("old", "new", "expected"), _BITES)
def test_a_planted_malformed_bmp3xx_record_fails(tmp_path: Path, validator: Validator, old: str, new: str, expected: str) -> None:
    copy = Path(shutil.copy(_SRC / "asy_bmp3xx_driver.py", tmp_path))
    source = copy.read_text(encoding="utf-8")
    assert source.count(old) == 1, old
    found = module_findings("asy_bmp3xx_driver.py", source.replace(old, new), validator)
    assert any(expected in line for line in found), found


def test_a_tuple_special_on_a_special_alone_field_fails(tmp_path: Path, validator: Validator) -> None:
    copy = Path(shutil.copy(_SRC / "asy_isl29125_driver.py", tmp_path))
    old = '("Calibrate", "bool", None, None, None, True)'
    source = copy.read_text(encoding="utf-8")
    assert source.count(old) == 1
    found = module_findings("asy_isl29125_driver.py", source.replace(old, '("Calibrate", "bool", None, None, None, (True,))'), validator)
    assert found == [f"asy_isl29125_driver.py:{_line_of(source, old)} _VAL_CALIBRATE: Calibrate: no default, and a special set cannot stand alone"], found


def test_an_unreadable_schema_constant_fails() -> None:
    found = module_findings("x.py", "_VAL_X = const(((_UNDEFINED, 'int', 1, 0, 2, None),))\n", lambda *_a, **_k: (False, None))
    assert len(found) == 1 and "cannot be evaluated" in found[0], found


def _line_of(source: str, text: str) -> int:
    return source[: source.index(text)].count("\n") + 1
