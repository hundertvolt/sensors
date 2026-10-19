"""Structural guard for every `src/` module that declares both a measurement NamedTuple and the
`_FIELDS` tuple `make_dict()` keys its output by (SPECIFICATION.md Part C.6): the two are written
out separately by hand, and until this test nothing checked that they still say the same thing."""

# Seven modules carry this duplication with nothing behind the "kept in sync" comment. It stays
# deliberately: mypy's namedtuple plugin infers field names only from a literal at the call site,
# so routing through `_FIELDS` would cost static typing on every field access.

# Drift here is silent and reaches the wire: `_FIELDS` is what make_dict() iterates to build the
# `/measurements` body, while the NamedTuple is what the read path fills, so a field renamed in one
# and not the other publishes a wrong or missing key while every driver test still passes.

import ast
from pathlib import Path

import pytest
import tomllib
from _devices import DEVICE_NAMES, device_toml

from buildgen.web_tag import parse_web_tags

_SRC = Path(__file__).resolve().parent.parent / "src"


def _literal_tuple(node: ast.AST) -> tuple[str, ...] | None:
    # const(("a", "b")) and a bare ("a", "b") both reduce to the same tuple; anything that is not a
    # tuple of plain string literals is not the declaration shape this guard understands.
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "const" and node.args:
        node = node.args[0]
    if not isinstance(node, ast.Tuple):
        return None
    names: list[str] = []
    for element in node.elts:
        if not (isinstance(element, ast.Constant) and isinstance(element.value, str)):
            return None
        names.append(element.value)
    return tuple(names)


def _declarations(path: Path) -> tuple[dict[str, tuple[str, ...]], tuple[str, ...] | None]:
    # Every `X = namedtuple("X", (...))` in the module, plus its module-level `_FIELDS` if any.
    tuples: dict[str, tuple[str, ...]] = {}
    fields: tuple[str, ...] | None = None
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        name = node.targets[0].id
        value = node.value
        if name == "_FIELDS":
            fields = _literal_tuple(value)
        elif isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "namedtuple" and len(value.args) == 2:
            declared = _literal_tuple(value.args[1])
            if declared is not None:
                tuples[name] = declared
    return tuples, fields


def _keyword_tuple(path: Path, function: str, keyword: str) -> "list[tuple[str, ...] | None]":
    # The literal tuple passed as `keyword=` to `function(...)`, once per call in the module.
    return [
        _literal_tuple(k.value) for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == function
        for k in node.keywords if k.arg == keyword
    ]


def _a_device_with(driver: str) -> str:
    # The device name only labels a parse error, so any device whose TOML wires the driver will do.
    return next(d for d in DEVICE_NAMES if any(i.get("driver") == driver for i in tomllib.loads(device_toml(d).read_text(encoding="utf-8")).get("instance", [])))


def test_scd30_always_written_keys_equal_its_always_executed_tags() -> None:
    # The firmware never reads @web tags, so its own always= tuple is pinned to them: ContMeas is a
    # dispatch-only key handled apart from compare_before_write().
    path = _SRC / "asy_scd30_driver.py"
    tagged = {t.field_name for t in parse_web_tags(path, _a_device_with("scd30"), "scd30") if t.always_executed} - {"ContMeas"}
    (always,) = _keyword_tuple(path, "compare_before_write", "always")
    assert always is not None and set(always) == tagged, f"always={always}, tagged alwaysExecuted={sorted(tagged)}"


_MODULES_WITH_FIELDS = sorted(p.name for p in _SRC.glob("*.py") if _declarations(p)[1] is not None)


def test_the_guard_actually_found_the_modules_it_guards() -> None:
    # Without this the whole file passes vacuously the day the declaration shape changes - the same
    # guard-is-blind trap SPECIFICATION.md Part E.8 describes. Seven today; a new driver adds one.
    assert len(_MODULES_WITH_FIELDS) >= 7, f"expected every measurement-publishing src/ module to be found, got {_MODULES_WITH_FIELDS}"


def _reader_tuple(path: Path, tuples: "dict[str, tuple[str, ...]]") -> "str | None":
    # The NamedTuple the module's reader passes as the first positional argument of its super().__init__().
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        func = node.func if isinstance(node, ast.Call) else None
        if isinstance(node, ast.Call) and isinstance(func, ast.Attribute) and func.attr == "__init__" and ast.unparse(func.value) == "super()" and node.args:
            first = node.args[0]
            if isinstance(first, ast.Call) and isinstance(first.func, ast.Name) and first.func.id in tuples:
                return first.func.id
    return None


def _field_problems(path: Path) -> "list[str]":
    # _FIELDS must equal the NamedTuple the reader fills, bound through its super().__init__() call - never
    # merely some NamedTuple of equal content (asy_ntp_client.py also declares GMTimeStruct, for one).
    tuples, fields = _declarations(path)
    assert fields is not None
    bound = _reader_tuple(path, tuples)
    if bound is None:
        return [f"src/{path.name}: its reader passes no NamedTuple of the module as super().__init__()'s first argument"]
    if tuples[bound] == fields:
        return []
    drift = f"src/{path.name}'s _FIELDS has drifted from {bound}, the NamedTuple its reader fills.\n  _FIELDS: {fields}\n  {bound}: {tuples[bound]}\n"
    return [drift + "  make_dict() keys /measurements by _FIELDS, so this drift publishes wrong or missing keys."]


@pytest.mark.parametrize("module", _MODULES_WITH_FIELDS)
def test_fields_tuple_matches_its_own_named_tuple(module: str) -> None:
    problems = _field_problems(_SRC / module)
    assert not problems, "\n".join(problems)


_TWIN = (
    '_FIELDS = const(("A", "B", "TS"))\nX = namedtuple("X", ("A", "C", "TS"))\nTWIN = namedtuple("TWIN", ("A", "B", "TS"))\n\n\n'
    "class X_Reader(SensorReader):\n    def __init__(self):\n        super().__init__(X(None, None, None), _NAME)\n"
)


def test_a_fields_tuple_equal_only_to_a_twin_of_the_readers_tuple_fails(tmp_path: Path) -> None:
    # The reader publishes X; a second NamedTuple that happens to equal _FIELDS proves nothing about it.
    (tmp_path / "asy_x_driver.py").write_text(_TWIN, encoding="utf-8")
    problems = _field_problems(tmp_path / "asy_x_driver.py")
    assert len(problems) == 1 and "X" in problems[0], problems


def test_a_reader_passing_no_named_tuple_fails_naming_its_module(tmp_path: Path) -> None:
    (tmp_path / "asy_x_driver.py").write_text(_TWIN.replace("X(None, None, None)", "None"), encoding="utf-8")
    assert _field_problems(tmp_path / "asy_x_driver.py") == ["src/asy_x_driver.py: its reader passes no NamedTuple of the module as super().__init__()'s first argument"]
