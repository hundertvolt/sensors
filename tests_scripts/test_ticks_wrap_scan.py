"""Every tick value in src/, digital_twin/ and the generated device modules reaches arithmetic or an ordering only
through time.ticks_diff()/ticks_add(), and no literal ticks_add() delta reaches 2**29 (SPECIFICATION.md F.1): an ast
scan per function. Its known users are tests/test_ticks_rollover.py's _KNOWN_TICKS_USERS, the one list both tiers read."""

import ast
import operator
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from _devices import DEVICE_NAMES

from buildgen.generate import generate_device

if TYPE_CHECKING:
    from collections.abc import Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
_L1_FILE = REPO_ROOT / "tests" / "test_ticks_rollover.py"
_SCOPES = ("src", "digital_twin")
_PRODUCERS = frozenset({"ticks_add", "ticks_cpu", "ticks_ms", "ticks_us"})  # each returns a tick value
_READERS = _PRODUCERS | {"ticks_diff"}
_HORIZON = 1 << 29  # ticks_diff()'s range on rp2 is [-2**29, 2**29) (extmod/modtime.c:166-175, v1.29.0)
_ORDERING_OPS = (ast.Lt, ast.LtE, ast.Gt, ast.GtE)
_ORDERING_CALLS = frozenset({"max", "min", "sorted"})
_INT_OPS: "dict[type[ast.operator], Callable[[int, int], int]]" = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.FloorDiv: operator.floordiv, ast.LShift: operator.lshift, ast.Pow: operator.pow,
}
_SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)
_TRUTH = "tests a tick value's truth, false at the valid tick 0"
_UNLISTED = "src/zz_plant.py: reads ticks but is not in _KNOWN_TICKS_USERS"


def _is_tick(node: ast.expr, names: "set[str]", held: "set[str]") -> bool:
    if isinstance(node, ast.Call):
        return _call_name(node) in _PRODUCERS or _call_name(node) in held
    if isinstance(node, ast.Name):
        return node.id in names
    if isinstance(node, ast.Attribute):
        return node.attr in held
    if isinstance(node, ast.Subscript):
        return ast.unparse(node.value) in held
    if isinstance(node, ast.IfExp):
        return _is_tick(node.body, names, held) or _is_tick(node.orelse, names, held)
    if isinstance(node, ast.BoolOp):
        return any(_is_tick(v, names, held) for v in node.values)
    if isinstance(node, ast.NamedExpr):
        return _is_tick(node.value, names, held)
    return False


def _annotated_tick(annotation: "ast.expr | None") -> bool:
    # The stubs' opaque tick types (`_TicksMs`, `_TicksUs`, `_Ticks`), written bare or as a string.
    return annotation is not None and "_Ticks" in ast.unparse(annotation)


def _bindings(nodes: "list[ast.AST]") -> "list[tuple[ast.expr, ast.expr | None, bool]]":
    # (target, value, annotated as a tick) for each binding among a scope's own nodes; a tuple target pairs with a tuple value.
    out: list[tuple[ast.expr, ast.expr | None, bool]] = []
    for node in nodes:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Tuple) and isinstance(node.value, ast.Tuple) and len(target.elts) == len(node.value.elts):
                    out.extend((t, v, False) for t, v in zip(target.elts, node.value.elts, strict=True))
                else:
                    out.append((target, node.value, False))
        elif isinstance(node, ast.AnnAssign):
            out.append((node.target, node.value, _annotated_tick(node.annotation)))
        elif isinstance(node, ast.NamedExpr):
            out.append((node.target, node.value, False))
    return out


def _call_name(node: ast.AST) -> "str | None":
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    return func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else None


def _file_findings(path: str, tree: ast.Module, held: "set[str]") -> "tuple[list[tuple[int, int, str]], int]":
    # The file's findings as (line, column, text) and its own tick bindings. `held` - attributes, subscripted containers
    # and functions holding or returning a tick - is shared by every scanned file and grows here.
    consts = _module_ints(tree)
    scopes = _scopes(tree, None, "")
    names: dict[int, set[str]] = {id(scope): set() for scope, _parent, _qual in scopes}
    nodes = {id(scope): _own_nodes(scope) for scope, _parent, _qual in scopes}
    binds = {id(scope): _bindings(nodes[id(scope)]) for scope, _parent, _qual in scopes}
    functions: dict[str, list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, bool]]] = {}
    for scope, parent, _qual in scopes:
        if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.setdefault(scope.name, []).append((scope, isinstance(parent, ast.ClassDef)))
    passed: dict[int, set[str]] = {id(scope): set() for scope, _parent, _qual in scopes}  # parameters handed a tick
    bound: set[str] = set()
    while True:
        size = (sum(len(n) for n in names.values()), sum(len(n) for n in passed.values()), len(held))
        for scope, parent, qual in scopes:  # a parent precedes its children
            own = names[id(scope)]
            own |= names[id(parent)] if parent is not None else set()
            if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                params = [*scope.args.posonlyargs, *scope.args.args, *scope.args.kwonlyargs, scope.args.vararg, scope.args.kwarg]
                annotated = {a.arg for a in params if a is not None and _annotated_tick(a.annotation)} | passed[id(scope)]
                own |= annotated
                bound |= {f"{qual}:{a}" for a in annotated}
            for target, value, annotated_tick in binds[id(scope)]:
                if annotated_tick or (value is not None and _is_tick(value, own, held)):
                    key = target.id if isinstance(target, ast.Name) else target.attr if isinstance(target, ast.Attribute) else ast.unparse(target.value) if isinstance(target, ast.Subscript) else None
                    if isinstance(target, ast.Name):
                        own.add(target.id)
                        bound.add(f"{qual}:{key}")
                    elif key is not None:
                        held.add(key)
                        bound.add(key)
            for call in (n for n in nodes[id(scope)] if isinstance(n, ast.Call) and _call_name(n) in functions):
                for fn, is_method in functions[str(_call_name(call))]:
                    positional = [a.arg for a in (*fn.args.posonlyargs, *fn.args.args)][1 if is_method and isinstance(call.func, ast.Attribute) else 0 :]
                    passed[id(fn)] |= {p for p, a in zip(positional, call.args, strict=False) if _is_tick(a, own, held)}
                    passed[id(fn)] |= {k.arg for k in call.keywords if k.arg is not None and _is_tick(k.value, own, held)}
            if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(isinstance(n, ast.Return) and n.value is not None and _is_tick(n.value, own, held) for n in nodes[id(scope)]):
                held.add(scope.name)
                bound.add(f"{qual}()")
        if (sum(len(n) for n in names.values()), sum(len(n) for n in passed.values()), len(held)) == size:
            break
    found: list[tuple[int, int, str]] = []
    for scope, _parent, qual in scopes:
        own = names[id(scope)]
        for node in nodes[id(scope)]:
            reason = _rule(node, own, held, consts)
            if reason:
                assert isinstance(node, (ast.expr, ast.stmt)), node  # _rule() judges only expressions and statements
                shown = node.test if isinstance(node, (ast.If, ast.While, ast.Assert)) else node
                found.append((node.lineno, node.col_offset, f"{path}:{node.lineno} {qual}(): `{ast.unparse(shown)}` {reason}"))
    return found, len(bound)


def _findings(sources: "dict[str, str]", known: "tuple[str, ...]") -> "list[str]":
    # Every rule finding in path order, then each tick user missing from the known list and each listed file reading none.
    # A tick attribute or helper one file binds is followed in every other, so the shared set is grown to a fixed point first.
    trees = {path: ast.parse(sources[path], filename=path) for path in sorted(sources)}
    held: set[str] = set()
    while True:
        size = len(held)
        for path, tree in trees.items():
            _file_findings(path, tree, held)
        if len(held) == size:
            break
    out: list[str] = []
    users: set[str] = set()
    for path, tree in trees.items():
        found, bindings = _file_findings(path, tree, held)
        out.extend(text for _line, _col, text in sorted(found))
        if any(_call_name(n) in _READERS for n in ast.walk(tree)):
            users.add(path)
            if path in known and bindings == 0:
                out.append(f"{path}: reads ticks but binds no tick value - the scan judges nothing there")
    out.extend(f"{path}: reads ticks but is not in _KNOWN_TICKS_USERS" for path in sorted(users - set(known)))
    out.extend(f"{path}: listed in _KNOWN_TICKS_USERS but reads no ticks" for path in sorted(set(known) - users))
    return out


def _int_value(node: ast.expr, consts: "dict[str, int]") -> "int | None":
    # A compile-time integer: a literal, a module constant, or +, -, *, //, <<, ** over them.
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return node.value
    if isinstance(node, ast.Name):
        return consts.get(node.id)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        operand = _int_value(node.operand, consts)
        return None if operand is None else -operand if isinstance(node.op, ast.USub) else operand
    if isinstance(node, ast.BinOp) and type(node.op) in _INT_OPS:
        left, right = _int_value(node.left, consts), _int_value(node.right, consts)
        if left is None or right is None or (isinstance(node.op, (ast.Pow, ast.LShift)) and not 0 <= right < 64):
            return None
        return _INT_OPS[type(node.op)](left, right)
    return None


def _known_users() -> "tuple[str, ...]":
    tree = ast.parse(_L1_FILE.read_text(encoding="utf-8"))
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and [ast.unparse(t) for t in stmt.targets] == ["_KNOWN_TICKS_USERS"]:
            return tuple(ast.literal_eval(stmt.value))
    msg = f"{_L1_FILE.name} defines no _KNOWN_TICKS_USERS"
    raise AssertionError(msg)


def _module_ints(tree: ast.Module) -> "dict[str, int]":
    # Module-level integer constants, `const()` or plain, in definition order.
    consts: dict[str, int] = {}
    for stmt in tree.body:
        target, value = (stmt.targets[0], stmt.value) if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 else (stmt.target, stmt.value) if isinstance(stmt, ast.AnnAssign) else (None, None)
        if isinstance(target, ast.Name) and value is not None:
            if _call_name(value) == "const" and isinstance(value, ast.Call) and len(value.args) == 1:
                value = value.args[0]
            number = _int_value(value, consts)
            if number is not None:
                consts[target.id] = number
    return consts


def _own_nodes(scope: ast.AST) -> "list[ast.AST]":
    # The nodes a scope evaluates itself, not those of a function, lambda or class nested in it.
    out: list[ast.AST] = []
    stack = list(ast.iter_child_nodes(scope))
    while stack:
        node = stack.pop()
        if isinstance(node, _SCOPE_NODES):
            continue
        out.append(node)
        stack.extend(ast.iter_child_nodes(node))
    return out


def _plant(root: Path, rel: str, source: str) -> "dict[str, str]":
    (root / rel).write_text(source, encoding="utf-8")
    return _read_scopes(root)


def _read_scopes(root: Path) -> "dict[str, str]":
    return {f"{scope}/{p.name}": p.read_text(encoding="utf-8") for scope in _SCOPES for p in sorted((root / scope).glob("*.py"))}


def _rule(node: ast.AST, names: "set[str]", held: "set[str]", consts: "dict[str, int]") -> "str | None":
    # What makes this node a wrap hazard, or None: arithmetic, an ordering or a truth test on a tick operand, or a
    # ticks_add() delta that is a tick value or a constant at or past the horizon.
    def tick(n: ast.expr) -> bool:
        return _is_tick(n, names, held)

    if isinstance(node, ast.BinOp) and not (isinstance(node.op, ast.Mod) and isinstance(node.left, ast.Constant) and isinstance(node.left.value, str)):
        return "is arithmetic on a tick value" if tick(node.left) or tick(node.right) else None
    if isinstance(node, ast.AugAssign):
        return "is arithmetic on a tick value" if tick(node.target) or tick(node.value) else None
    if isinstance(node, ast.UnaryOp):
        return None if not tick(node.operand) else _TRUTH if isinstance(node.op, ast.Not) else "is arithmetic on a tick value"
    if isinstance(node, (ast.If, ast.While, ast.IfExp, ast.Assert)):
        return _TRUTH if tick(node.test) else None
    if isinstance(node, ast.BoolOp):
        return _TRUTH if any(tick(v) for v in node.values[:-1]) else None
    if isinstance(node, ast.Compare):
        operands = [node.left, *node.comparators]
        hit = any(isinstance(op, _ORDERING_OPS) and (tick(operands[i]) or tick(operands[i + 1])) for i, op in enumerate(node.ops))
        return "orders a tick value" if hit else None
    if _call_name(node) in _ORDERING_CALLS and isinstance(node, ast.Call):
        return "orders a tick value" if any(tick(a) for a in node.args) else None
    if _call_name(node) == "ticks_add" and isinstance(node, ast.Call) and len(node.args) == 2:
        if tick(node.args[1]):
            return "takes a tick value as its delta"
        delta = _int_value(node.args[1], consts)
        if delta is not None and abs(delta) >= _HORIZON:
            return f"adds a delta of {delta} ms, at or past ticks_diff()'s 2**29 horizon"
    return None


def _scopes(node: ast.AST, parent: "ast.AST | None", qual: str) -> "list[tuple[ast.AST, ast.AST | None, str]]":
    # (scope, enclosing scope, qualified name) for the module and every function, lambda and class in it, outermost first.
    out: list[tuple[ast.AST, ast.AST | None, str]] = [(node, parent, qual or "<module>")]
    stack = list(ast.iter_child_nodes(node))
    while stack:
        child = stack.pop(0)
        if isinstance(child, _SCOPE_NODES):
            name = "<lambda>" if isinstance(child, ast.Lambda) else child.name
            out.extend(_scopes(child, node, f"{qual}.{name}" if qual else name))
        else:
            stack.extend(ast.iter_child_nodes(child))
    return out


@pytest.fixture(scope="module")
def generated() -> "dict[str, str]":
    out: dict[str, str] = {}
    for device in DEVICE_NAMES:
        result = generate_device(REPO_ROOT / "devices" / f"{device}.toml", REPO_ROOT / "src", REPO_ROOT / "ext")
        out[f"generated:sensortask_{device}.py"] = result.module_source
        out[f"generated:{device}/main.py"] = result.boot_entry_source
    return out


@pytest.fixture
def tree_copy(tmp_path: Path) -> Path:
    for scope in _SCOPES:
        shutil.copytree(REPO_ROOT / scope, tmp_path / scope, ignore=shutil.ignore_patterns("__pycache__"))
    return tmp_path


def test_the_tree_passes(generated: "dict[str, str]") -> None:
    sources = _read_scopes(REPO_ROOT) | generated
    assert len(generated) == 2 * len(DEVICE_NAMES) > 0
    assert _findings(sources, _known_users()) == []


def test_a_two_line_subtraction_fails(tree_copy: Path, generated: "dict[str, str]") -> None:
    plant = "import time\n\n\ndef elapsed(t0):\n    now = time.ticks_ms()\n    return now - t0\n"
    findings = _findings(_plant(tree_copy, "src/zz_plant.py", plant) | generated, _known_users())
    assert findings == ["src/zz_plant.py:6 elapsed(): `now - t0` is arithmetic on a tick value", _UNLISTED], findings


def test_a_stored_attribute_compared_in_another_method_fails(tree_copy: Path, generated: "dict[str, str]") -> None:
    plant = (
        "import time\n\n\nclass Gate:\n    def arm(self):\n        self._deadline = time.ticks_add(time.ticks_ms(), 100)\n\n"
        "    def expired(self):\n        return time.ticks_ms() >= self._deadline\n"
    )
    findings = _findings(_plant(tree_copy, "src/zz_plant.py", plant) | generated, _known_users())
    assert findings == ["src/zz_plant.py:9 Gate.expired(): `time.ticks_ms() >= self._deadline` orders a tick value", _UNLISTED], findings


def test_an_added_deadline_and_a_name_chain_fail(tree_copy: Path, generated: "dict[str, str]") -> None:
    plant = "import time\n\n\ndef wait(limit):\n    t0 = time.ticks_ms()\n    start = t0\n    deadline = start + 100\n    return start < limit\n"
    findings = _findings(_plant(tree_copy, "src/zz_plant.py", plant) | generated, _known_users())
    assert findings == [
        "src/zz_plant.py:7 wait(): `start + 100` is arithmetic on a tick value",
        "src/zz_plant.py:8 wait(): `start < limit` orders a tick value",
        _UNLISTED,
    ], findings


def test_an_annotated_parameter_an_augmented_step_and_min_fail(tree_copy: Path, generated: "dict[str, str]") -> None:
    plant = (
        "import time\n\n\ndef late(t0: '_TicksMs', t1: '_TicksMs'):\n    t0 += 5\n    first = min(t0, t1)\n    return -t1\n\n\n"
        "def now():\n    return time.ticks_ms()\n"
    )
    findings = _findings(_plant(tree_copy, "src/zz_plant.py", plant) | generated, _known_users())
    assert findings == [
        "src/zz_plant.py:5 late(): `t0 += 5` is arithmetic on a tick value",
        "src/zz_plant.py:6 late(): `min(t0, t1)` orders a tick value",
        "src/zz_plant.py:7 late(): `-t1` is arithmetic on a tick value",
        _UNLISTED,
    ], findings


def test_a_tick_returned_by_a_helper_or_stored_in_a_container_is_followed(tree_copy: Path, generated: "dict[str, str]") -> None:
    plant = (
        "import time\n\n\ndef _now():\n    return time.ticks_ms()\n\n\n"
        "def check(stamps, limit):\n    stamps[0] = _now()\n    t = _now()\n    return (stamps[0] > limit, t - limit)\n"
    )
    findings = _findings(_plant(tree_copy, "src/zz_plant.py", plant) | generated, _known_users())
    assert findings == [
        "src/zz_plant.py:11 check(): `stamps[0] > limit` orders a tick value",
        "src/zz_plant.py:11 check(): `t - limit` is arithmetic on a tick value",
        _UNLISTED,
    ], findings


def test_a_tick_attribute_is_followed_into_another_file(tree_copy: Path, generated: "dict[str, str]") -> None:
    _plant(tree_copy, "src/zz_plant.py", "import time\n\n\nclass Stamp:\n    def mark(self):\n        self._zz_stamp = time.ticks_ms()\n")
    sources = _plant(tree_copy, "digital_twin/zz_reader.py", "def stale(stamp, limit):\n    return stamp._zz_stamp >= limit\n")
    findings = _findings(sources | generated, _known_users())
    assert findings == ["digital_twin/zz_reader.py:2 stale(): `stamp._zz_stamp >= limit` orders a tick value", _UNLISTED], findings


def test_a_tick_handed_to_a_function_of_the_same_file_is_followed(tree_copy: Path, generated: "dict[str, str]") -> None:
    plant = (
        "import time\n\n\ndef _age(t0, limit):\n    return t0 > limit\n\n\nclass Gate:\n    def _late(self, t1, *, t2=None):\n"
        "        return t1 - t2\n\n    def check(self):\n        return _age(time.ticks_ms(), 5), self._late(1, t2=time.ticks_ms())\n"
    )
    findings = _findings(_plant(tree_copy, "src/zz_plant.py", plant) | generated, _known_users())
    assert findings == [
        "src/zz_plant.py:5 _age(): `t0 > limit` orders a tick value",
        "src/zz_plant.py:10 Gate._late(): `t1 - t2` is arithmetic on a tick value",
        _UNLISTED,
    ], findings


def test_a_closure_reads_its_enclosing_ticks(tree_copy: Path, generated: "dict[str, str]") -> None:
    plant = "import time\n\n\ndef outer():\n    t0 = time.ticks_ms()\n\n    def inner():\n        return t0 * 2\n\n    return inner\n"
    findings = _findings(_plant(tree_copy, "src/zz_plant.py", plant) | generated, _known_users())
    assert findings == ["src/zz_plant.py:8 outer.inner(): `t0 * 2` is arithmetic on a tick value", _UNLISTED], findings


def test_a_ticks_add_delta_at_the_horizon_fails(tree_copy: Path, generated: "dict[str, str]") -> None:
    plant = (
        "import time\n\nfrom micropython import const\n\n_WAIT_MS = const(600_000_000)\n_OK_MS = const((1 << 29) - 1)\n\n\n"
        "def arm(t, d):\n    a = time.ticks_add(t, 1 << 29)\n    b = time.ticks_add(t, _WAIT_MS)\n    c = time.ticks_add(t, -(2**29))\n"
        "    e = time.ticks_add(t, time.ticks_ms())\n    return time.ticks_add(t, _OK_MS), time.ticks_add(t, d)\n"
    )
    findings = _findings(_plant(tree_copy, "src/zz_plant.py", plant) | generated, _known_users())
    assert findings == [
        "src/zz_plant.py:10 arm(): `time.ticks_add(t, 1 << 29)` adds a delta of 536870912 ms, at or past ticks_diff()'s 2**29 horizon",
        "src/zz_plant.py:11 arm(): `time.ticks_add(t, _WAIT_MS)` adds a delta of 600000000 ms, at or past ticks_diff()'s 2**29 horizon",
        "src/zz_plant.py:12 arm(): `time.ticks_add(t, -2 ** 29)` adds a delta of -536870912 ms, at or past ticks_diff()'s 2**29 horizon",
        "src/zz_plant.py:13 arm(): `time.ticks_add(t, time.ticks_ms())` takes a tick value as its delta",
        _UNLISTED,
    ], findings


def test_a_truth_test_on_a_tick_fails(tree_copy: Path, generated: "dict[str, str]") -> None:
    plant = (
        "import time\n\n\nclass Gate:\n    def check(self):\n        if self._t0:\n            return not self._t0\n"
        "        return self._t0 or 1\n\n    def arm(self):\n        self._t0 = time.ticks_ms()\n"
    )
    findings = _findings(_plant(tree_copy, "src/zz_plant.py", plant) | generated, _known_users())
    assert findings == [
        "src/zz_plant.py:6 Gate.check(): `self._t0` tests a tick value's truth, false at the valid tick 0",
        "src/zz_plant.py:7 Gate.check(): `not self._t0` tests a tick value's truth, false at the valid tick 0",
        "src/zz_plant.py:8 Gate.check(): `self._t0 or 1` tests a tick value's truth, false at the valid tick 0",
        _UNLISTED,
    ], findings


def test_the_correct_forms_pass(tree_copy: Path, generated: "dict[str, str]") -> None:
    # The negative control: deltas, sentinels and equality are not tick arithmetic.
    plant = (
        "import time\n\n\nclass Gate:\n    def __init__(self):\n        self._t0 = None\n\n    def check(self, timeout):\n"
        "        now = time.ticks_ms()\n        if self._t0 is None or self._t0 == now:\n            self._t0 = now\n"
        "        late = time.ticks_diff(now, self._t0) >= timeout\n        left = time.ticks_diff(self._t0, now) + 5\n"
        "        return late, left, time.ticks_add(now, (1 << 29) - 1), time.ticks_add(now, -((1 << 29) - 1))\n"
    )
    findings = _findings(_plant(tree_copy, "src/zz_plant.py", plant) | generated, _known_users())
    assert findings == [_UNLISTED], findings


def test_a_twin_plant_fails(tree_copy: Path, generated: "dict[str, str]") -> None:
    plant = "import time\n\n\ndef stamp(t0):\n    now = time.ticks_us()\n    return now > t0\n"
    findings = _findings(_plant(tree_copy, "digital_twin/zz_plant.py", plant) | generated, _known_users())
    assert findings == [
        "digital_twin/zz_plant.py:6 stamp(): `now > t0` orders a tick value",
        "digital_twin/zz_plant.py: reads ticks but is not in _KNOWN_TICKS_USERS",
    ], findings


def test_a_generated_module_plant_fails(generated: "dict[str, str]") -> None:
    # The generated modules are scanned in memory, as the generator returns them.
    device = DEVICE_NAMES[0]
    key = f"generated:sensortask_{device}.py"
    sources = _read_scopes(REPO_ROOT) | generated
    sources[key] += "\n\ndef zz_plant(t0):\n    return time.ticks_ms() - t0\n"
    line = sources[key].count("\n")
    findings = _findings(sources, _known_users())
    assert findings == [f"{key}:{line} zz_plant(): `time.ticks_ms() - t0` is arithmetic on a tick value", f"{key}: reads ticks but is not in _KNOWN_TICKS_USERS"], findings


def test_a_listed_user_that_reads_no_ticks_fails(tree_copy: Path, generated: "dict[str, str]") -> None:
    known = _known_users()
    gone = next(k for k in known if k.startswith("src/"))
    findings = _findings(_plant(tree_copy, gone, '"""Emptied."""\n') | generated, known)
    assert findings == [f"{gone}: listed in _KNOWN_TICKS_USERS but reads no ticks"], findings


def test_a_listed_user_binding_no_tick_fails(tree_copy: Path, generated: "dict[str, str]") -> None:
    # A listed user whose ticks the scan cannot follow is judged on nothing: that fails rather than passing empty.
    known = _known_users()
    blind = next(k for k in known if k.startswith("src/"))
    findings = _findings(_plant(tree_copy, blind, "import time\n\n\ndef late(a, b):\n    return time.ticks_diff(a, b)\n") | generated, known)
    assert findings == [f"{blind}: reads ticks but binds no tick value - the scan judges nothing there"], findings
