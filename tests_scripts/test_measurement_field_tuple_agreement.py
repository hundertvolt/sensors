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

_SRC = Path(__file__).resolve().parent.parent / "src"


def _literal_tuple(node: ast.AST) -> tuple[str, ...] | None:
    # const(("a", "b")) and a bare ("a", "b") both reduce to the same tuple; anything that is not a
    # tuple of plain string literals is not the declaration shape this guard understands.
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "const" and node.args:
        node = node.args[0]
    if not isinstance(node, ast.Tuple):
        return None
    if not all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in node.elts):
        return None
    return tuple(e.value for e in node.elts)  # type: ignore[attr-defined]


def _declarations(path: Path) -> tuple[dict[str, tuple[str, ...]], tuple[str, ...] | None]:
    """Every `X = namedtuple("X", (...))` in the module, plus its module-level `_FIELDS` if any."""
    tuples: dict[str, tuple[str, ...]] = {}
    fields: tuple[str, ...] | None = None
    for node in ast.parse(path.read_text()).body:
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


_MODULES_WITH_FIELDS = sorted(p.name for p in _SRC.glob("*.py") if _declarations(p)[1] is not None)


def test_the_guard_actually_found_the_modules_it_guards() -> None:
    # Without this the whole file passes vacuously the day the declaration shape changes - the same
    # guard-is-blind trap SPECIFICATION.md Part E.8 describes. Seven today; a new driver adds one.
    assert len(_MODULES_WITH_FIELDS) >= 7, f"expected every measurement-publishing src/ module to be found, got {_MODULES_WITH_FIELDS}"


@pytest.mark.parametrize("module", _MODULES_WITH_FIELDS)
def test_fields_tuple_matches_its_own_named_tuple(module: str) -> None:
    tuples, fields = _declarations(_SRC / module)
    assert fields is not None
    # The module's own measurement NamedTuple is the one whose fields _FIELDS claims to mirror -
    # matched by content, since a module may declare several (asy_ntp_client.py also has
    # GMTimeStruct, asy_sgp40_driver.py _ConstValue) and only one of them is the published shape.
    named = {name: decl for name, decl in tuples.items() if not name.startswith("_")}
    assert named, f"src/{module} declares _FIELDS but no public NamedTuple to agree with"
    matching = [name for name, decl in named.items() if decl == fields]
    assert matching, (
        f"src/{module}'s _FIELDS has drifted from every NamedTuple it declares.\n"
        f"  _FIELDS: {fields}\n"
        + "".join(f"  {name}: {decl}\n" for name, decl in sorted(named.items()))
        + "  make_dict() keys /measurements by _FIELDS, so this drift publishes wrong or missing keys."
    )
