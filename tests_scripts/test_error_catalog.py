"""buildgen/error_catalog.json against every logging call in src/ and the generated modules, and every
test-side mirror of it: one number per meaning, passed by keyword through a named constant, and no test
or mock history holding a code the catalog does not give (SPECIFICATION.md C.7.1). Each check bites a plant."""

import ast
import json
import re
from collections import Counter
from dataclasses import dataclass
from functools import cache
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from _devices import DEVICE_NAMES

from buildgen.generate import generate_device

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

_REPO = Path(__file__).resolve().parent.parent
_CATALOG_PATH = _REPO / "buildgen" / "error_catalog.json"
_MOCK_SAMPLES = "mockdata/samples.json"
_TEST_SCOPES = ("tests", "tests_hardware", "tests_scripts", "digital_twin", "scripts")

_METHOD_KIND = {"err_s": "E", "wrn_s": "W"}
_KEYWORD = {"E": "errno", "W": "wrnno"}
_PREFIX = {"E": "_ERR_", "W": "_WRN_"}
_CODE_PARAMS = frozenset(_KEYWORD.values())
_COPY_NAME = re.compile(r"^_(?:ERR|WRN)_|_ERRNO|_WRNNO")
_SCRIPT_BINDING = re.compile(r"^([EW])_([A-Z0-9_]+)$")
_CODE_STRING = re.compile(r"^[EWN]\d+$")
# Text of an expression that reads a logged code back, after ast.unparse() normalised its quotes.
_LOGGED_MARKERS = ("ErrNum", "['num']", ".get('num')", ".history", "persisted(", "errnums(", "_warnings(", "errnos(", "last_errno(", "_log_entries(")
_CODE_ARGUMENT = {"assert_module_error_log_contains": (2, "num"), "_ntp_error_log_contains": (1, "errno")}
_ALLOWED_KEYWORDS = frozenset({"allowed_errors", "allowed_warnings"})
_COUNT_CALLS = frozenset({"len", "sum"})
_COUNT_METHODS = frozenset({"count", "index"})

# Seed scripts whose seeds still carry product numbers rather than the catalog's test band; each entry
# leaves with its script's rewrite, and an entry the scan no longer flags fails the pending test.
_SEED_NAMES_PENDING = frozenset({
    ("tests_hardware/device_scripts/fram_error_log_roundtrip.py", "TEST_ERRNO"),
})


@dataclass(frozen=True)
class _Module:
    path: str
    tree: ast.Module


def _module(path: str, source: str) -> _Module:
    return _Module(path, ast.parse(source, filename=path))


@cache
def _catalog() -> "dict[str, Any]":
    result: dict[str, Any] = json.loads(_CATALOG_PATH.read_text())
    return result


def _rows(catalog: "dict[str, Any]", kind: str) -> "dict[int, dict[str, Any]]":
    return {int(num): row for num, row in catalog["codes"].get(kind, {}).items()}


def _live_numbers(catalog: "dict[str, Any]", kind: str) -> "dict[str, int]":
    return {row["name"]: num for num, row in _rows(catalog, kind).items() if not row.get("retired")}


def _owners_of(catalog: "dict[str, Any]", path: str) -> "set[str]":
    return {
        owner for owner, spec in catalog["owners"].items()
        if any(path == f or (f.endswith("/") and path.startswith(f)) for f in spec["files"])
    }


def _repo_modules(directory: str) -> "list[_Module]":
    return [_module(p.relative_to(_REPO).as_posix(), p.read_text()) for p in sorted((_REPO / directory).rglob("*.py"))]


@cache
def _src() -> "tuple[_Module, ...]":
    return tuple(_repo_modules("src"))


@cache
def _generated() -> "tuple[_Module, ...]":
    modules = []
    for device in DEVICE_NAMES:
        result = generate_device(_REPO / "devices" / f"{device}.toml", _REPO / "src", _REPO / "ext")
        modules.append(_module(f"build/generated_src/sensortask_{device}.py", result.module_source))
    return tuple(modules)


@cache
def _test_side() -> "tuple[_Module, ...]":
    return tuple(m for scope in _TEST_SCOPES for m in _repo_modules(scope) if "/_tmp/" not in m.path)


def _functions(tree: ast.AST) -> "Iterator[ast.FunctionDef | ast.AsyncFunctionDef]":
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def _log_calls(tree: ast.AST) -> "Iterator[tuple[str, ast.Call]]":
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in _METHOD_KIND:
            yield _METHOD_KIND[node.func.attr], node


def _keyword(call: ast.Call, name: str) -> "ast.expr | None":
    return next((k.value for k in call.keywords if k.arg == name), None)


def _int_value(node: "ast.expr | None") -> "int | None":
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "const" and len(node.args) == 1:
        node = node.args[0]
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return node.value
    return None


def _binding(stmt: ast.stmt) -> "tuple[ast.expr | None, ast.expr | None]":
    # (target, value) of a single-target assignment; (None, None) for any other statement.
    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
        return stmt.targets[0], stmt.value
    if isinstance(stmt, ast.AnnAssign):
        return stmt.target, stmt.value
    return None, None


def _code_constants(tree: ast.Module) -> "Iterator[tuple[str, str, int | None, int]]":
    # (kind, name, value, line) of every module-level _ERR_/_WRN_ binding; value None when not a literal int.
    for stmt in tree.body:
        target, value = _binding(stmt)
        if isinstance(target, ast.Name):
            for kind, prefix in _PREFIX.items():
                if target.id.startswith(prefix):
                    yield kind, target.id, _int_value(value), stmt.lineno


def _loaded_names(tree: ast.AST) -> "set[str]":
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}


# ---- (1) catalog shape ----------------------------------------------------------------------------


def _band_problems(catalog: "dict[str, Any]", kind: str) -> "list[str]":
    problems: list[str] = []
    spans: list[tuple[int, int, str]] = []
    for owner, spec in catalog["owners"].items():
        spans.extend((lo, hi, owner) for lo, hi in spec["bands"].get(kind) or [])
    spans.sort()
    problems.extend(f"{kind}: bands of {a[2]} and {b[2]} overlap" for a, b in pairwise(spans) if b[0] <= a[1])
    for num, row in _rows(catalog, kind).items():
        bands = (catalog["owners"].get(row["owner"]) or {}).get("bands", {}).get(kind) or []
        if not any(lo <= num <= hi for lo, hi in bands):
            problems.append(f"{kind}{num} {row['name']} lies outside {row['owner']}'s {kind} band")
    return problems


def _shape_problems(catalog: "dict[str, Any]") -> "list[str]":
    low, high = catalog["range"]
    problems: list[str] = []
    for kind in ("E", "W"):
        rows = catalog["codes"].get(kind, {})
        problems.extend(f"{kind}{num} is not an int in {low}-{high}" for num in rows if not (num.isdigit() and low <= int(num) <= high))
        if not all(num.isdigit() for num in rows):
            continue
        problems.extend(_band_problems(catalog, kind))
        for field in ("name", "text"):
            seen = Counter(row[field] for row in rows.values())
            problems.extend(f"{kind}: {field} {value!r} is used {n} times" for value, n in seen.items() if n > 1)
    return problems


def _retired_live_sites(catalog: "dict[str, Any]", modules: "tuple[_Module, ...]") -> "list[str]":
    retired = {_PREFIX[kind] + row["name"] for kind in ("E", "W") for row in _rows(catalog, kind).values() if row.get("retired")}
    return [f"{m.path}: retired {name} is still used" for m in modules for name in sorted(retired & _loaded_names(m.tree))]


def test_catalog_shape() -> None:
    problems = _shape_problems(_catalog())
    assert not problems, "buildgen/error_catalog.json:\n" + "\n".join(problems)


def test_a_retired_code_has_no_live_site() -> None:
    problems = _retired_live_sites(_catalog(), _src())
    assert not problems, "\n".join(problems)


# ---- (2) every logging call passes its code by keyword --------------------------------------------


def _keyword_problems(modules: "tuple[_Module, ...]") -> "tuple[list[str], Counter[str]]":
    problems = []
    seen: Counter[str] = Counter()
    for m in modules:
        for kind, call in _log_calls(m.tree):
            seen[kind] += 1
            if _keyword(call, _KEYWORD[kind]) is None:
                problems.append(f"{m.path}:{call.lineno} passes no {_KEYWORD[kind]}=")
    return problems, seen


def test_every_logging_call_passes_its_code_by_keyword() -> None:
    problems, seen = _keyword_problems(_src())
    assert seen["E"] >= 1 and seen["W"] >= 1, f"the scan matched no err_s() or no wrn_s() call in src/ ({dict(seen)}) - a shape change emptied it"
    assert not problems, "\n".join(problems)


# ---- (3) code expressions and the carriers that feed them -----------------------------------------


@dataclass(frozen=True)
class _Scope:
    module: _Module
    function: "ast.FunctionDef | ast.AsyncFunctionDef"
    defs: "dict[str, ast.FunctionDef | ast.AsyncFunctionDef]"


def _params(fn: "ast.FunctionDef | ast.AsyncFunctionDef") -> "list[str]":
    return [a.arg for a in (*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs)]


def _assignments(tree: ast.AST, matches: "Callable[[ast.expr], bool]") -> "Iterator[tuple[ast.expr | None, int | None]]":
    # (value, tuple index) for every binding whose target `matches`; value None for a binding it cannot follow.
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if matches(target):
                    yield node.value, None
                elif isinstance(target, ast.Tuple):
                    yield from ((node.value, i) for i, elt in enumerate(target.elts) if matches(elt))
        elif isinstance(node, (ast.AnnAssign, ast.NamedExpr)) and matches(node.target):
            yield node.value, None
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            # Iterating a container feeds the target like popping from it does.
            taken = ast.Call(func=ast.Attribute(value=node.iter, attr="pop", ctx=ast.Load()), args=[], keywords=[])
            if matches(node.target):
                yield taken, None
            elif isinstance(node.target, ast.Tuple):
                yield from ((taken, i) for i, elt in enumerate(node.target.elts) if matches(elt))
        elif isinstance(node, ast.AugAssign) and matches(node.target):
            yield None, None


def _returns(fn: "ast.FunctionDef | ast.AsyncFunctionDef") -> "Iterator[ast.expr | None]":
    stack: list[ast.AST] = list(fn.body)
    while stack:
        node = stack.pop()
        if isinstance(node, ast.Return):
            yield node.value
        elif not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            stack.extend(ast.iter_child_nodes(node))


def _feeder_ok(scope: _Scope, node: "ast.expr | None", index: "int | None", seen: "set[str]") -> bool:
    # A carrier's source: a catalog name, 0, or a call/attribute whose own sources are those (transitively).
    if index is not None:
        if isinstance(node, ast.Tuple):
            return index < len(node.elts) and _feeder_ok(scope, node.elts[index], None, seen)
        return isinstance(node, ast.Call) and _call_feeds(scope, node, index, seen)
    if isinstance(node, ast.Constant):
        return node.value == 0 and type(node.value) is int
    if isinstance(node, ast.Name):
        return node.id.startswith(tuple(_PREFIX.values())) or node.id in _params(scope.function) or _local_ok(scope, node.id, seen)
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
        return all(_feeder_ok(scope, v, None, seen) for v in node.values)
    if isinstance(node, ast.IfExp):
        return _feeder_ok(scope, node.body, None, seen) and _feeder_ok(scope, node.orelse, None, seen)
    if isinstance(node, ast.Attribute):
        return _attribute_ok(scope, node.attr, seen)
    return isinstance(node, ast.Call) and _call_feeds(scope, node, None, seen)


def _call_feeds(scope: _Scope, call: ast.Call, index: "int | None", seen: "set[str]") -> bool:
    if isinstance(call.func, ast.Attribute) and call.func.attr == "pop" and isinstance(call.func.value, ast.Attribute):
        return _container_ok(scope, call.func.value.attr, index, seen)
    name = call.func.attr if isinstance(call.func, ast.Attribute) else getattr(call.func, "id", "")
    callee = scope.defs.get(name)
    if callee is None or f"def:{name}:{index}" in seen:
        return callee is not None
    seen.add(f"def:{name}:{index}")
    inner = _Scope(scope.module, callee, scope.defs)
    return all(_feeder_ok(inner, value, index, seen) for value in _returns(callee))


def _container_ok(scope: _Scope, attr: str, index: "int | None", seen: "set[str]") -> bool:
    # A container attribute feeds through every item appended to it or written into its initial literal.
    key = f"items:{attr}:{index}"
    if key in seen:
        return True
    seen.add(key)
    for fn in _functions(scope.module.tree):
        inner = _Scope(scope.module, fn, scope.defs)
        for node in ast.walk(fn):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("append", "insert")):
                continue
            if getattr(node.func.value, "attr", None) == attr and not _feeder_ok(inner, node.args[-1] if node.args else None, index, seen):
                return False
        for value, _ in _assignments(fn, lambda t: isinstance(t, ast.Attribute) and t.attr == attr):
            if not isinstance(value, (ast.List, ast.Tuple)) or not all(_feeder_ok(inner, e, index, seen) for e in value.elts):
                return False
    return True


def _local_ok(scope: _Scope, name: str, seen: "set[str]") -> bool:
    key = f"local:{scope.function.name}:{name}"
    if key in seen:
        return True
    seen.add(key)
    sources = list(_assignments(scope.function, lambda t: isinstance(t, ast.Name) and t.id == name))
    return bool(sources) and all(_feeder_ok(scope, value, index, seen) for value, index in sources)


def _attribute_ok(scope: _Scope, attr: str, seen: "set[str]") -> bool:
    key = f"attr:{attr}"
    if key in seen:
        return True
    seen.add(key)
    for fn in _functions(scope.module.tree):
        inner = _Scope(scope.module, fn, scope.defs)
        for value, index in _assignments(fn, lambda t: isinstance(t, ast.Attribute) and t.attr == attr):
            if not _feeder_ok(inner, value, index, seen):
                return False
    return True


def _expression_ok(scope: _Scope, node: ast.expr, kind: str) -> bool:
    # The shape of a code argument: catalog names, parameters, locals, attributes, `or` - no literal or arithmetic.
    if isinstance(node, ast.Name):
        if node.id.startswith(tuple(_PREFIX.values())):
            return node.id.startswith(_PREFIX[kind])
        return _feeder_ok(scope, node, None, set())
    if isinstance(node, ast.Attribute):
        return _feeder_ok(scope, node, None, set())
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
        return all(_expression_ok(scope, v, kind) for v in node.values)
    if isinstance(node, ast.IfExp):  # the test picks between two names; it is not part of the value
        return _expression_ok(scope, node.body, kind) and _expression_ok(scope, node.orelse, kind)
    return False


def _code_arguments(scope: _Scope) -> "Iterator[tuple[ast.Call, str, ast.expr]]":
    # Every argument in this function bound to a code: an err_s/wrn_s keyword, or a helper's errno/wrnno parameter.
    for node in ast.walk(scope.function):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute) and node.func.attr in _METHOD_KIND:
            kind = _METHOD_KIND[node.func.attr]
            value = _keyword(node, _KEYWORD[kind])
            if value is not None:
                yield node, kind, value
            continue
        name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
        helper = scope.defs.get(name)
        if helper is None:
            continue
        params = _params(helper)
        offset = 1 if params[:1] == ["self"] and isinstance(node.func, ast.Attribute) else 0
        for position, param in enumerate(params):
            if param in _CODE_PARAMS:
                kind = "E" if param == "errno" else "W"
                value = _keyword(node, param)
                if value is None and position - offset < len(node.args) and position >= offset:
                    value = node.args[position - offset]
                if value is not None and not isinstance(value, ast.Starred):
                    yield node, kind, value


def _expression_problems(modules: "tuple[_Module, ...]") -> "list[str]":
    problems = []
    for m in modules:
        defs = {fn.name: fn for fn in _functions(m.tree)}
        for fn in _functions(m.tree):
            scope = _Scope(m, fn, defs)
            for call, kind, value in _code_arguments(scope):
                if not _expression_ok(scope, value, kind):
                    problems.append(f"{m.path}:{call.lineno} {fn.name}(): code {ast.unparse(value)!r} is not built from {_PREFIX[kind]} names")
    return problems


def test_every_code_argument_is_built_from_catalog_names() -> None:
    problems = _expression_problems(_src())
    assert not problems, "\n".join(problems)


# ---- (4)/(6) constants equal their catalog entry and stay in their file's bands --------------------


def _constant_problems(catalog: "dict[str, Any]", modules: "tuple[_Module, ...]") -> "list[str]":
    problems = []
    for m in modules:
        owners = _owners_of(catalog, m.path) | {"base", "shared"}
        for kind, name, value, line in _code_constants(m.tree):
            rows = _rows(catalog, kind)
            expected = _live_numbers(catalog, kind).get(name[len(_PREFIX[kind]):])
            if value is None or value != expected:
                problems.append(f"{m.path}:{line} {name} = {value}, the catalog gives {expected}")
            elif rows[value]["owner"] not in owners:
                problems.append(f"{m.path}:{line} {name} belongs to {rows[value]['owner']}, not to this file's owners {sorted(owners)}")
    return problems


def _non_catalog_problems(catalog: "dict[str, Any]", modules: "tuple[_Module, ...]") -> "list[str]":
    problems = []
    for m in modules:
        for kind, name, value, line in _code_constants(m.tree):
            if value not in set(_live_numbers(catalog, kind).values()):
                problems.append(f"{m.path}:{line} {name} = {value} is not a live catalog {kind} code; a non-code constant takes no {_PREFIX[kind]} prefix")
    return problems


def test_every_code_constant_equals_its_catalog_entry_and_owner() -> None:
    problems = _constant_problems(_catalog(), _src())
    assert not problems, "\n".join(problems)


def test_no_code_constant_holds_a_non_catalog_value() -> None:
    problems = _non_catalog_problems(_catalog(), _src())
    assert not problems, "\n".join(problems)


# ---- (5) every live code is logged somewhere -------------------------------------------------------


def _unused_code_problems(catalog: "dict[str, Any]", modules: "tuple[_Module, ...]") -> "list[str]":
    used = set()
    for m in modules:
        declared = {name for _kind, name, _value, _line in _code_constants(m.tree)}
        used |= declared & _loaded_names(m.tree)
    return [
        f"{kind}{num} {row['name']} has no live site ({_PREFIX[kind]}{row['name']} declared and used in src/)"
        for kind in ("E", "W") for num, row in sorted(_rows(catalog, kind).items())
        if not row.get("retired") and row["owner"] != "test" and _PREFIX[kind] + row["name"] not in used
    ]


def test_every_live_code_has_a_live_site() -> None:
    problems = _unused_code_problems(_catalog(), _src())
    assert not problems, "\n".join(problems)


# ---- (7) the generated modules -------------------------------------------------------------------------


def test_generated_modules_follow_the_catalog() -> None:
    modules = _generated()
    assert len(modules) == len(DEVICE_NAMES)
    problems = _keyword_problems(modules)[0] + _expression_problems(modules) + _constant_problems(_catalog(), modules)
    assert not problems, "\n".join(problems)


# ---- (8) no test-side copy of a code ---------------------------------------------------------------------


def _seed_only(tree: ast.AST, name: str) -> bool:
    seed_values = {id(k.value) for _kind, call in _log_calls(tree) for k in call.keywords if k.arg in _CODE_PARAMS}
    loads = [n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, ast.Load)]
    return bool(loads) and all(id(n) in seed_values for n in loads)


def _copy_bindings(m: _Module) -> "Iterator[tuple[str, int]]":
    for node in ast.walk(m.tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            target, value = _binding(node)
            if isinstance(target, ast.Name) and _COPY_NAME.search(target.id) and _int_value(value) is not None and not _seed_only(m.tree, target.id):
                yield target.id, node.lineno


def _literal_codes(node: ast.AST) -> "set[int]":
    # Literals a code could be: ints and "E21"-style strings in the catalog's range; a list repeat count is not one.
    low, high = _catalog()["range"]
    counts = {id(n.right) for n in ast.walk(node) if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mult)}
    found = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and type(sub.value) is int and id(sub) not in counts:
            found.add(sub.value)
        elif isinstance(sub, ast.Constant) and isinstance(sub.value, str) and _CODE_STRING.match(sub.value):
            found.add(int(sub.value[1:]))
    return {n for n in found if low <= n <= high}


def _reads_logged_code(node: ast.expr) -> bool:
    if isinstance(node, ast.Call) and (getattr(node.func, "id", None) in _COUNT_CALLS or getattr(node.func, "attr", None) in _COUNT_METHODS):
        return False  # a count of logged codes, not a code
    text = ast.unparse(node)
    return any(marker in text for marker in _LOGGED_MARKERS)


def _seeded(fn: ast.AST) -> "set[int]":
    # Codes an err_s()/wrn_s() call in this function writes itself, directly or from a literal loop.
    loops = {t.id: n.iter for n in ast.walk(fn) if isinstance(n, (ast.For, ast.AsyncFor)) and isinstance(t := n.target, ast.Name)}
    seeds = set()
    for _kind, call in _log_calls(fn):
        for k in call.keywords:
            if k.arg in _CODE_PARAMS:
                value = _int_value(k.value)
                if value is not None:
                    seeds.add(value)
                elif isinstance(k.value, ast.Name) and k.value.id in loops:
                    seeds |= {v for e in ast.walk(loops[k.value.id]) if (v := _int_value(e if isinstance(e, ast.expr) else None)) is not None}
    return seeds


def _assert_literals(fn: ast.AST) -> "Iterator[tuple[int, set[int]]]":
    for node in ast.walk(fn):
        if not isinstance(node, ast.Assert):
            continue
        for cmp in (n for n in ast.walk(node.test) if isinstance(n, ast.Compare)):
            sides = [cmp.left, *cmp.comparators]
            for a, b in pairwise(sides):
                for logged, other in ((a, b), (b, a)):
                    if _reads_logged_code(logged) and not _reads_logged_code(other) and _literal_codes(other):
                        yield node.lineno, _literal_codes(other)
        for call in (n for n in ast.walk(node.test) if isinstance(n, ast.Call) and getattr(n.func, "attr", None) in _COUNT_METHODS):
            receiver = call.func.value if isinstance(call.func, ast.Attribute) else call.func
            if _reads_logged_code(receiver) and any(_literal_codes(a) for a in call.args):
                yield node.lineno, set().union(*(_literal_codes(a) for a in call.args))


def _call_literals(fn: ast.AST) -> "Iterator[tuple[int, set[int]]]":
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
        values: list[ast.expr | None] = [k.value for k in node.keywords if k.arg in _ALLOWED_KEYWORDS]
        if name in _CODE_ARGUMENT:
            position, keyword = _CODE_ARGUMENT[name]
            values.append(node.args[position] if position < len(node.args) else _keyword(node, keyword))
        for value in values:
            if value is not None and _literal_codes(value) and not isinstance(value, ast.Name):
                yield node.lineno, _literal_codes(value)


def _copy_problems(modules: "tuple[_Module, ...]") -> "list[str]":
    problems = [f"{m.path}:{line} binds {name} to an int - read it with code() from tests/_error_codes.py" for m in modules for name, line in _copy_bindings(m) if (m.path, name) not in _SEED_NAMES_PENDING]
    for m in modules:
        for fn in _functions(m.tree):
            seeded = _seeded(fn)
            for line, codes in (*_assert_literals(fn), *_call_literals(fn)):
                if codes - seeded:
                    problems.append(f"{m.path}:{line} {fn.name}() compares a logged code with the literal(s) {sorted(codes - seeded)} - use code()")
    return sorted(set(problems))


def test_no_test_tier_keeps_its_own_copy_of_a_code() -> None:
    problems = _copy_problems(_test_side())
    assert not problems, "\n".join(problems)


def test_every_pending_seed_name_is_still_flagged() -> None:
    flagged = {(m.path, name) for m in _test_side() for name, _line in _copy_bindings(m)}
    assert flagged >= _SEED_NAMES_PENDING, f"no longer a pending seed copy, drop from _SEED_NAMES_PENDING: {sorted(_SEED_NAMES_PENDING - flagged)}"


# ---- (9) device-script bindings ------------------------------------------------------------------------


def _script_binding_problems(catalog: "dict[str, Any]", modules: "tuple[_Module, ...]") -> "list[str]":
    problems = []
    for m in modules:
        for stmt in m.tree.body:
            target, value = _binding(stmt)
            match = _SCRIPT_BINDING.match(target.id) if isinstance(target, ast.Name) else None
            if match is not None:
                kind, name = match.groups()
                expected = _live_numbers(catalog, kind).get(name)
                if _int_value(value) != expected:
                    problems.append(f"{m.path}:{stmt.lineno} {match.group(0)} = {_int_value(value)}, the catalog gives {expected}")
    return problems


def test_device_script_bindings_equal_the_catalog() -> None:
    problems = _script_binding_problems(_catalog(), tuple(_repo_modules("tests_hardware/device_scripts")))
    assert not problems, "\n".join(problems)


# ---- (10) mock histories ---------------------------------------------------------------------------


def _logger_owners(catalog: "dict[str, Any]", logger: str) -> "set[str]":
    names = {logger, logger.split("_", 1)[0]}
    return {owner for owner, spec in catalog["owners"].items() if names & set(spec["loggers"])} | {"base", "shared"}


def _history_problems(catalog: "dict[str, Any]", source: str, errcount: "dict[str, Any]") -> "list[str]":
    problems = []
    for logger, entry in errcount.items():
        owners = _logger_owners(catalog, logger)
        slots = [(h["type"], h["num"]) for h in entry["history"] if h["type"] != "N"]
        for kind, num in slots:
            row = _rows(catalog, kind).get(num)
            if row is None or row.get("retired") or row["owner"] not in owners:
                problems.append(f"{source} {logger}: {kind}{num} is not a live catalog code of this logger")
        problems.extend(f"{source} {logger}: two adjacent {a[0]}{a[1]} entries - the newest-entry rule never writes a repeat into a new slot" for a, b in pairwise(slots) if a == b)
        if entry["counter"] < len(slots):
            problems.append(f"{source} {logger}: counter {entry['counter']} is below its {len(slots)} recorded slots")
    return problems


def test_mock_histories_hold_only_their_loggers_catalog_codes() -> None:
    # The one driver-keyed sample table every device's mock data is composed from (js/mock-server.js).
    errcount = json.loads((_REPO / _MOCK_SAMPLES).read_text())["errcount"]
    assert errcount, f"{_MOCK_SAMPLES} carries no errcount samples - the check would hold nothing"
    problems = _history_problems(_catalog(), _MOCK_SAMPLES, errcount)
    assert not problems, "\n".join(problems)


# ---- planted violations: each check above bites ---------------------------------------------------


_PLANT_CATALOG: "dict[str, Any]" = {
    "range": [1, 127],
    "owners": {
        "base": {"files": [], "loggers": [], "bands": {"E": [[1, 9]], "W": None}},
        "shared": {"files": [], "loggers": [], "bands": {"E": [[10, 19]], "W": [[10, 19]]}},
        "net": {"files": ["src/net.py"], "loggers": ["NET"], "bands": {"E": [[20, 29]], "W": [[20, 29]]}},
        "fan": {"files": ["src/fan.py"], "loggers": ["FAN"], "bands": {"E": [[30, 39]], "W": None}},
    },
    "codes": {
        "E": {
            "1": {"owner": "base", "name": "STREAK", "text": "streak"},
            "10": {"owner": "shared", "name": "INIT", "text": "init"},
            "20": {"owner": "net", "name": "NET_NO_ACK", "text": "no ack"},
            "30": {"owner": "fan", "name": "FAN_STALL", "text": "stall"},
            "31": {"owner": "fan", "name": "FAN_OLD", "text": "old", "retired": True},
        },
        "W": {"20": {"owner": "net", "name": "NET_SLOW", "text": "slow"}},
    },
}

_PLANT_NET = """
_ERR_NET_NO_ACK = const(20)
_WRN_NET_SLOW = const(20)
class Net:
    async def run(self):
        await self.pr.err_s("x", errno=_ERR_NET_NO_ACK)
        await self.pr.wrn_s("y", wrnno=_WRN_NET_SLOW)
"""


def _planted(source: str, path: str = "src/net.py") -> "tuple[_Module, ...]":
    return (_module(path, source),)


def _plant_catalog(**changes: object) -> "dict[str, Any]":
    catalog: dict[str, Any] = json.loads(json.dumps(_PLANT_CATALOG))
    for key, value in changes.items():
        kind, num, field = key.split("__")
        catalog["codes"][kind].setdefault(num, {"owner": "net", "name": f"N{num}", "text": f"t{num}"})[field] = value
    return catalog


def test_the_plants_start_clean() -> None:
    # Every bite below changes one thing from this baseline, so a bite cannot pass on a second fault.
    modules = _planted(_PLANT_NET)
    assert not _shape_problems(_PLANT_CATALOG)
    assert not _keyword_problems(modules)[0] + _expression_problems(modules) + _constant_problems(_PLANT_CATALOG, modules)
    assert not _non_catalog_problems(_PLANT_CATALOG, modules) + _retired_live_sites(_PLANT_CATALOG, modules)


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"E__126__owner": "net"}, "outside net's E band"),  # a code outside its owner's band
        ({"E__21__name": "NET_NO_ACK"}, "name 'NET_NO_ACK' is used 2 times"),
        ({"W__21__text": "slow"}, "text 'slow' is used 2 times"),
        ({"E__200__owner": "net"}, "is not an int in 1-127"),
    ],
)
def test_the_shape_check_bites(changes: "dict[str, Any]", expected: str) -> None:
    assert any(expected in p for p in _shape_problems(_plant_catalog(**changes)))


def test_the_band_overlap_check_bites() -> None:
    catalog = _plant_catalog()
    catalog["owners"]["fan"]["bands"]["E"] = [[29, 39]]
    assert any("overlap" in p for p in _shape_problems(catalog))


def test_the_retired_check_bites() -> None:
    planted = _planted("_ERR_FAN_OLD = const(31)\nasync def f(pr):\n    await pr.err_s('x', errno=_ERR_FAN_OLD)\n", "src/fan.py")
    assert _retired_live_sites(_PLANT_CATALOG, planted)


def test_the_keyword_check_bites() -> None:
    problems, seen = _keyword_problems(_planted("async def f(pr):\n    await pr.err_s('x', 20)\n"))
    assert seen["E"] == 1 and problems


@pytest.mark.parametrize(
    "argument",
    ["errno=20", "errno=_ERR_NET_NO_ACK + 1", "errno=_WRN_NET_SLOW", "errno=_LIMIT", "errno=self._last"],
)
def test_the_expression_check_bites(argument: str) -> None:
    source = f"_LIMIT = 5\nclass N:\n    def __init__(self):\n        self._last = 7\n    async def f(self):\n        await self.pr.err_s('x', {argument})\n"
    assert _expression_problems(_planted(source))


def test_the_expression_check_follows_helpers_and_feeders() -> None:
    clean = "class N:\n    def _check(self, b):\n        return _ERR_NET_NO_ACK if b else 0\n    async def _err(self, errno):\n        await self.pr.err_s('x', errno=errno)\n    async def f(self, b):\n        err = self._check(b)\n        await self._err(err)\n"
    assert not _expression_problems(_planted(clean))
    assert _expression_problems(_planted(clean.replace("else 0", "else 3")))  # a feeder returning a literal
    assert _expression_problems(_planted(clean.replace("self._err(err)", "self._err(4)")))  # a helper's errno argument


def test_the_constant_checks_bite() -> None:
    assert _constant_problems(_PLANT_CATALOG, _planted("_ERR_NET_NO_ACK = const(21)\n"))  # wrong number
    assert _constant_problems(_PLANT_CATALOG, _planted("_ERR_FAN_STALL = const(30)\n"))  # another owner's code
    assert _non_catalog_problems(_PLANT_CATALOG, _planted("_ERR_CMD = const(0xB6)\n"))  # not a code at all


def test_the_unused_code_check_bites() -> None:
    assert any("FAN_STALL" in p for p in _unused_code_problems(_PLANT_CATALOG, _planted(_PLANT_NET)))


def test_the_copy_check_bites() -> None:
    copy = _planted("_ERR_NO_ACK = 20\n", "tests/test_x.py")
    assert _copy_problems(copy)
    asserted = _planted("def test_x(c):\n    assert persisted(c) == ['E99']\n", "tests/test_x.py")
    assert _copy_problems(asserted)
    seeded = _planted("def test_x(pr, c):\n    run(pr.err_s('s', errno=99))\n    assert persisted(c) == ['E99']\n", "tests/test_x.py")
    assert not _copy_problems(seeded)
    seed_only = _planted("SEED_ERRNO = 99\nasync def f(pr):\n    await pr.err_s('s', errno=SEED_ERRNO)\n", "tests/test_x.py")
    assert not _copy_problems(seed_only)
    helper = _planted("def test_x(ip):\n    assert_module_error_log_contains(ip, 'NTP', 12, 'E')\n", "tests_hardware/test_x.py")
    assert _copy_problems(helper)


def test_the_script_binding_check_bites() -> None:
    assert _script_binding_problems(_PLANT_CATALOG, _planted("E_NET_NO_ACK = 21\n", "tests_hardware/device_scripts/x.py"))
    assert not _script_binding_problems(_PLANT_CATALOG, _planted("E_NET_NO_ACK = 20\n", "tests_hardware/device_scripts/x.py"))


def test_the_history_check_bites() -> None:
    def entry(*slots: "tuple[str, int]", counter: int = 9) -> "dict[str, Any]":
        return {"counter": counter, "history": [{"type": t, "num": n} for t, n in slots]}
    assert not _history_problems(_PLANT_CATALOG, "plant", {"NET": entry(("E", 20), ("W", 20), ("E", 10))})
    assert _history_problems(_PLANT_CATALOG, "plant", {"NET": entry(("E", 30))})  # another logger's code
    assert _history_problems(_PLANT_CATALOG, "plant", {"NET": entry(("E", 20), ("E", 20))})  # an adjacent repeat
    assert _history_problems(_PLANT_CATALOG, "plant", {"NET": entry(("E", 20), counter=0)})  # counter below its slots
