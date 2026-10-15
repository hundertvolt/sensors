"""Every sensor driver module keeps one shape (SPECIFICATION.md C.2): _NAME = const("<NAME>"), each namedtuple bound to its
own type name, REST keys from self.name never _NAME, no per-driver session class (DeviceSession is the shared one), and
the module order constants, _VAL_* schema tuples, _N_* counts, _NAME and the namedtuple, default helpers, reader, bus class."""

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest
from _repo_scan import REPO_ROOT

_READER_BASES = {"SensorReader", "SensorReaderConfig"}
# The module order: each top-level definition's rank is at least every earlier one's.
_RANKS = ("constant", "_VAL_* schema tuple", "_N_* count", "_NAME/namedtuple", "_Default*/_ConstValue helper", "*_Reader class", "*_I2C/*_SPI class")


@dataclass(frozen=True)
class Driver:
    path: str
    tree: ast.Module


def _parse(path: str, source: str) -> Driver:
    return Driver(path, ast.parse(source, filename=path))


def _is_reader_module(tree: ast.Module) -> bool:
    return any(isinstance(n, ast.ClassDef) and any(isinstance(b, ast.Name) and b.id in _READER_BASES for b in n.bases) for n in tree.body)


def _target(node: ast.stmt) -> str | None:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    return None


def _is_namedtuple_call(value: ast.expr | None) -> bool:
    return isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "namedtuple"


def _rank(node: ast.stmt) -> int | None:
    # Imports, TYPE_CHECKING blocks and module functions take no rank: D.15 orders the functions.
    if isinstance(node, ast.ClassDef):
        if node.name.startswith(("_Default", "_ConstValue")):
            return 4
        if node.name.endswith("_Reader"):
            return 5
        if node.name.endswith(("_I2C", "_SPI")):
            return 6
        return None
    name = _target(node)
    if name is None:
        return None
    if name.startswith(("_Default", "_ConstValue")):
        return 4
    if name in {"_NAME", "_FIELDS"} or _is_namedtuple_call(getattr(node, "value", None)):
        return 3
    if name.startswith("_N_"):
        return 2
    if name.startswith("_VAL_"):
        return 1
    return 0 if name.startswith("_") and name[1:].isupper() else None


def _is_str_const(value: ast.expr | None) -> bool:
    # const("<NAME>"): one string literal through micropython.const()
    return (
        isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "const"
        and len(value.args) == 1 and isinstance(value.args[0], ast.Constant) and isinstance(value.args[0].value, str)
    )


def name_const(driver: Driver) -> list[str]:
    found = [n for n in driver.tree.body if isinstance(n, ast.Assign) and _target(n) == "_NAME" and _is_str_const(n.value)]
    return [] if len(found) == 1 else [f'{driver.path}: {len(found)} module-level _NAME = const("<NAME>") bindings, expected one']


def namedtuple_names(driver: Driver) -> list[str]:
    found = []
    for node in ast.walk(driver.tree):
        if isinstance(node, ast.Assign) and _is_namedtuple_call(node.value):
            call = node.value
            assert isinstance(call, ast.Call)
            typename = call.args[0].value if call.args and isinstance(call.args[0], ast.Constant) else None
            target = _target(node)
            if target != typename:
                found.append(f"{driver.path}:{node.lineno}: namedtuple {typename!r} bound to {target!r}")
    return found


def _is_name(node: ast.expr | None) -> bool:
    return isinstance(node, ast.Name) and node.id == "_NAME"


def rest_keys(driver: Driver) -> list[str]:
    # The REST key is self.name (the instance's resolved name), never the type's _NAME.
    found = []
    for node in ast.walk(driver.tree):
        if isinstance(node, ast.Call):
            func = node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id if isinstance(node.func, ast.Name) else ""
            if func == "make_dict" and (any(_is_name(k.value) for k in node.keywords if k.arg == "name") or any(_is_name(a) for a in node.args[2:])):
                found.append(f"{driver.path}:{node.lineno}: make_dict() keyed by _NAME")
            if func == "_get_dict_cfg" and node.args and _is_name(node.args[0]):
                found.append(f"{driver.path}:{node.lineno}: _get_dict_cfg() keyed by _NAME")
        elif isinstance(node, ast.Dict) and any(_is_name(k) for k in node.keys):
            found.append(f"{driver.path}:{node.lineno}: a dict keyed by _NAME")
    return found


def no_session_subclass(driver: Driver) -> list[str]:
    return [f"{driver.path}:{n.lineno}: class {n.name}: the shared DeviceSession replaces it" for n in ast.walk(driver.tree) if isinstance(n, ast.ClassDef) and n.name.endswith("_DeviceSession")]


def module_order(driver: Driver) -> list[str]:
    found = []
    highest, where = -1, ""
    for node in driver.tree.body:
        rank = _rank(node)
        if rank is None:
            continue
        label = getattr(node, "name", None) or _target(node)
        if rank < highest:
            found.append(f"{driver.path}:{node.lineno}: {label} ({_RANKS[rank]}) after {where} ({_RANKS[highest]})")
        else:
            highest, where = rank, str(label)
    return found


RULES = {
    "name_const": name_const,
    "namedtuple_names": namedtuple_names,
    "rest_keys": rest_keys,
    "no_session_subclass": no_session_subclass,
    "module_order": module_order,
}


@pytest.fixture(scope="module")
def drivers() -> list[Driver]:
    found = [_parse(f"src/{p.name}", p.read_text(encoding="utf-8")) for p in sorted((REPO_ROOT / "src").glob("asy_*_driver.py"))]
    return [d for d in found if _is_reader_module(d.tree)]


def test_the_scan_sees_the_four_sensor_drivers(drivers: list[Driver]) -> None:
    assert {d.path for d in drivers} >= {f"src/asy_{chip}_driver.py" for chip in ("bmp3xx", "isl29125", "scd30", "sgp40")}


@pytest.mark.parametrize("rule", sorted(RULES))
def test_every_sensor_driver_keeps_the_shape(drivers: list[Driver], rule: str) -> None:
    found = [line for driver in drivers for line in RULES[rule](driver)]
    assert not found, f"{rule}:\n" + "\n".join(f"  {line}" for line in found)


_NEGATIVE = {
    "name_const": ("_NAME = 'XCHIP'\n", "src/asy_x_driver.py: 0 module-level"),
    "namedtuple_names": ("X = namedtuple('Y', ('TS',))\n", "src/asy_x_driver.py:1: namedtuple 'Y' bound to 'X'"),
    "rest_keys": ("def f(d):\n    return make_dict(d, _FIELDS, name=_NAME)\n", "src/asy_x_driver.py:2: make_dict() keyed by _NAME"),
    "no_session_subclass": ("class X_DeviceSession(Lockable):\n    pass\n", "src/asy_x_driver.py:1: class X_DeviceSession"),
    "module_order": ("_VAL_A = const(1)\n_LIMIT = const(2)\n", "src/asy_x_driver.py:2: _LIMIT (constant) after _VAL_A"),
}


@pytest.mark.parametrize("rule", sorted(_NEGATIVE))
def test_a_planted_violation_fails_its_rule(tmp_path: Path, rule: str) -> None:
    source, expected = _NEGATIVE[rule]
    copy = tmp_path / "asy_x_driver.py"
    copy.write_text(source, encoding="utf-8")
    found = RULES[rule](_parse("src/asy_x_driver.py", copy.read_text(encoding="utf-8")))
    assert any(line.startswith(expected) for line in found), found


def test_the_full_order_passes_in_sequence() -> None:
    source = (
        "_ERR_X = const(10)\n_VAL_A = const(1)\n_N_A = const(1)\n_NAME = const('X')\nX = namedtuple('X', ('TS',))\n"
        "_FIELDS = const(('TS',))\nclass _DefaultSource:\n    pass\nclass X_Reader(SensorReader):\n    pass\nclass X_I2C:\n    pass\n"
    )
    driver = _parse("src/asy_x_driver.py", source)
    assert [line for rule in RULES.values() for line in rule(driver)] == []
