"""Counters stay allocation-free (SPECIFICATION.md G.2): over src/ and every device's generated modules, no
min(x + n, cap) step, no cap or max_val above COUNTER_CAP (2**30 - 1, the largest small int), and every
integer += / -= on an attribute checks a bound before it steps, resets at a threshold, or is listed below."""

import ast
import re
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES
from _repo_scan import REPO_ROOT

from buildgen.generate import generate_device

_SMALL_INT_MAX = 0x3FFFFFFF
_CAP_NAME = re.compile(r".*_CAP|.*max_val.*|.*MAX.*")
_ORDERING = (ast.Lt, ast.LtE, ast.Gt, ast.GtE)

# (path, constant) -> why a value above COUNTER_CAP is no counter bound.
_LARGE_CONSTANTS: dict[tuple[str, str], str] = {
    ("src/asy_ntp_client.py", "_NTP_MAX_PLAUSIBLE_UNIX_TIME"): "a UTC plausibility bound, compared, never stepped",
    ("src/voc_algorithm.py", "_FIX16_MAXIMUM"): "the Sensirion port's C int32 fix16 limit, not a counter",
}
# (path, Class.attribute) -> why an unguarded integer step stays bounded.
_EXEMPT: dict[tuple[str, str], str] = {
    ("src/asy_base_classes.py", "SensorReader._err_cnt_internal"): "bounded by the give-up: past max_module_error each failed cycle ends the read loop, whose restarts are budgeted (C.7)",
    ("src/asy_isl29125_driver.py", "ISL29125_Reader._periodic_only_switches"): "returns below its warn threshold and resets to 0 at it",
    ("src/asy_ntp_client.py", "NTPClient._unsynced_wait_s"): "reset to 0 once it reaches the retry wait (through `due`)",
    ("src/asy_sgp40_driver.py", "SGP40_Reader._voc_init"): "restores the same call's decrement, so it never rises above its starting value",
}
# Unguarded steps whose bound is not written yet: each leaves when its counter saturates, wraps or is
# masked, and the stale-entry test then fails until the entry is deleted. The list only shrinks.
_PENDING: dict[tuple[str, str], str] = {
    ("src/asy_uart_comm.py", "UARTComm._blind_resyncs"): "saturates at the resync streak threshold",
    ("src/asy_uart_driver.py", "UART._cancel_req"): "becomes a conditionally wrapped sequence",
    ("src/asy_uart_driver.py", "UART.cancel_unacknowledged"): "becomes a conditionally wrapped sequence",
    ("src/asy_uart_link_driver.py", "UARTLinkDriver._failures"): "saturates at COUNTER_CAP",
    ("src/asy_uart_link_driver.py", "UARTLinkDriver._transfers"): "saturates at COUNTER_CAP",
}


def _all_steps(modules: list[tuple[str, ast.Module]]) -> dict[tuple[str, str], int]:
    steps: dict[tuple[str, str], int] = {}
    for path, tree in modules:
        steps.update(unbounded_steps(path, tree))
    return steps


def _int_constants(tree: ast.Module) -> dict[str, int]:
    # Module-level names bound to an int literal or const(<int literal>).
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            value = node.value.args[0] if isinstance(node.value, ast.Call) and ast.unparse(node.value.func) == "const" and node.value.args else node.value
            if isinstance(value, ast.Constant) and type(value.value) is int:
                found[node.targets[0].id] = value.value
    return found


def _mentions(test: ast.expr, attr: str, ops: tuple[type[ast.cmpop], ...]) -> bool:
    for node in ast.walk(test):
        if isinstance(node, ast.Compare) and any(isinstance(op, ops) for op in node.ops):
            operands = [node.left, *node.comparators]
            if any(isinstance(o, ast.Attribute) and ast.unparse(o) == f"self.{attr}" for o in operands):
                return True
    return False


def _resets_at_threshold(function: ast.AST, attr: str, parents: dict[ast.AST, ast.AST]) -> bool:
    for node in ast.walk(function):
        if isinstance(node, ast.Assign) and [ast.unparse(t) for t in node.targets] == [f"self.{attr}"] and isinstance(node.value, ast.Constant) and node.value.value == 0:
            parent = parents.get(node)
            while parent is not None and parent is not function:
                if isinstance(parent, ast.If) and _mentions(parent.test, attr, (*_ORDERING, ast.Eq)):
                    return True
                parent = parents.get(parent)
    return False


def large_caps(path: str, tree: ast.Module) -> list[tuple[str, str, int, int]]:
    # (2) every integer above COUNTER_CAP bound to a cap-shaped name or passed as max_val=: (path, name, line, value).
    found = []
    for node in ast.walk(tree):
        pairs: list[tuple[str, ast.expr | None]] = []
        if isinstance(node, ast.Assign):
            pairs = [(ast.unparse(t).rsplit(".", 1)[-1], node.value) for t in node.targets]
        elif isinstance(node, ast.AnnAssign):
            pairs = [(ast.unparse(node.target).rsplit(".", 1)[-1], node.value)]
        elif isinstance(node, ast.keyword) and node.arg is not None:
            pairs = [(node.arg, node.value)] if node.arg == "max_val" else []
        elif isinstance(node, ast.arguments):
            named = [*node.posonlyargs, *node.args]
            pairs = [(a.arg, d) for a, d in zip(named[len(named) - len(node.defaults) :], node.defaults, strict=True)]
            pairs += [(a.arg, d) for a, d in zip(node.kwonlyargs, node.kw_defaults, strict=True)]
        for name, value in pairs:
            literal = value.args[0] if isinstance(value, ast.Call) and ast.unparse(value.func) == "const" and value.args else value
            if isinstance(literal, ast.Constant) and type(literal.value) is int and literal.value > _SMALL_INT_MAX and _CAP_NAME.fullmatch(name):
                found.append((path, name, literal.lineno, literal.value))
    return found


def min_steps(path: str, tree: ast.Module) -> list[str]:
    # (1) min(<expr> + <n>, <cap>) and min(max(<x> + ...)) build the stepped value before the cap applies.
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and ast.unparse(node.func) == "min" and node.args:
            first = node.args[0]
            if isinstance(first, ast.Call) and ast.unparse(first.func) == "max" and first.args:
                first = first.args[0]
            if isinstance(first, ast.BinOp) and isinstance(first.op, ast.Add):
                found.append(f"{path}:{node.lineno}: {ast.unparse(node)}")
    return found


@pytest.fixture(scope="module")
def modules(tmp_path_factory: pytest.TempPathFactory) -> list[tuple[str, ast.Module]]:
    out = tmp_path_factory.mktemp("generated_src")
    found = [(f"src/{p.name}", ast.parse(p.read_text(encoding="utf-8"))) for p in sorted((REPO_ROOT / "src").glob("*.py"))]
    for device in DEVICE_NAMES:
        generated = generate_device(REPO_ROOT / "devices" / f"{device}.toml", REPO_ROOT / "src", REPO_ROOT / "ext")
        for name, source in ((f"sensortask_{device}", generated.module_source), (f"{device}_boot", generated.boot_entry_source)):
            (out / f"{name}.py").write_text(source, encoding="utf-8")
            found.append((f"build/generated_src/{name}.py", ast.parse((out / f"{name}.py").read_text(encoding="utf-8"))))
    return found


def unbounded_steps(path: str, tree: ast.Module) -> dict[tuple[str, str], int]:
    # (3) an integer `self.<attr> += n` / `-= n` with no guarding comparison of the attribute and no
    # reset to 0 under a test of it in the same function: {(path, Class.attr): line}.
    constants = _int_constants(tree)
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    found = {}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.AugAssign) and isinstance(node.op, (ast.Add, ast.Sub)) and isinstance(node.target, ast.Attribute) and ast.unparse(node.target.value) == "self"):
            continue
        step = node.value
        if not ((isinstance(step, ast.Constant) and type(step.value) is int) or (isinstance(step, ast.Name) and step.id in constants)):
            continue
        attr, chain, guarded = node.target.attr, [], False
        parent = parents.get(node)
        while parent is not None:
            chain.append(parent)
            guarded = guarded or (isinstance(parent, (ast.If, ast.While)) and _mentions(parent.test, attr, _ORDERING))
            parent = parents.get(parent)
        function = next((p for p in chain if isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef))), None)
        cls = next((p.name for p in chain if isinstance(p, ast.ClassDef)), "<module>")
        if guarded or (function is not None and _resets_at_threshold(function, attr, parents)):
            continue
        found[(path, f"{cls}.{attr}")] = node.lineno
    return found


def voc_uptime_limit(tree: ast.Module) -> int:
    # The VOC port's two uptime counters step by F16(1) up to this limit, read from the module's own const()s.
    constants = _int_constants(tree)
    return (constants["_VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__FIX16_MAX"] - constants["_VOCALGORITHM_SAMPLING_INTERVAL"]) * constants["_FIX16_ONE"]


def test_no_min_step(modules: list[tuple[str, ast.Module]]) -> None:
    found = [line for path, tree in modules for line in min_steps(path, tree)]
    assert not found, "check the bound before stepping, never min() after it:\n" + "\n".join(found)


def test_no_cap_above_the_small_int_range(modules: list[tuple[str, ast.Module]]) -> None:
    found = [f"{p}:{line}: {name} = {value:#x}" for path, tree in modules for p, name, line, value in large_caps(path, tree) if (p, name) not in _LARGE_CONSTANTS]
    assert not found, "a cap above COUNTER_CAP lets a counter leave the small-int range:\n" + "\n".join(found)


def test_every_large_constant_entry_is_still_above_the_range(modules: list[tuple[str, ast.Module]]) -> None:
    present = {(p, name) for path, tree in modules for p, name, _, _ in large_caps(path, tree)}
    assert set(_LARGE_CONSTANTS) <= present, f"no longer above COUNTER_CAP - delete the entry: {sorted(set(_LARGE_CONSTANTS) - present)}"


def test_every_integer_step_is_bounded(modules: list[tuple[str, ast.Module]]) -> None:
    found = {key: line for key, line in _all_steps(modules).items() if key not in _EXEMPT and key not in _PENDING}
    assert not found, "an unbounded counter step - guard it with a cap comparison, or reset it at a threshold:\n" + "\n".join(f"  {p}:{line} {name}" for (p, name), line in sorted(found.items()))


def test_every_exempt_and_pending_entry_is_still_an_unguarded_step(modules: list[tuple[str, ast.Module]]) -> None:
    stale = sorted((set(_EXEMPT) | set(_PENDING)) - set(_all_steps(modules)))
    assert not stale, f"no longer an unguarded step - delete the entry: {stale}"
    assert not set(_EXEMPT) & set(_PENDING)


def test_the_logger_s_capped_counter_is_not_flagged(modules: list[tuple[str, ast.Module]]) -> None:
    source = (REPO_ROOT / "src" / "asy_print_log.py").read_text(encoding="utf-8")
    assert re.search(r"if self\._err_count < \w+:\n\s+self\._err_count \+= 1", source), "the logger's capped step moved - re-point this test"
    assert ("src/asy_print_log.py", "PrintLogHistory._err_count") not in _all_steps(modules)


def test_the_voc_uptime_counters_stay_small_ints(modules: list[tuple[str, ast.Module]]) -> None:
    # uptime_gamma/uptime_gating are plain assignments on self.params, so this bound is asserted here, not scanned.
    tree = next(tree for path, tree in modules if path == "src/voc_algorithm.py")
    assert voc_uptime_limit(tree) <= _SMALL_INT_MAX


def test_a_planted_voc_uptime_limit_above_the_range_fails() -> None:
    tree = ast.parse("_VOCALGORITHM_SAMPLING_INTERVAL = const(1)\n_VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__FIX16_MAX = const(32767)\n_FIX16_ONE = const(0x00010000)\n")
    assert voc_uptime_limit(tree) == 32766 * 65536 > _SMALL_INT_MAX


def test_a_planted_violation_fails_each_rule(tmp_path: Path) -> None:
    copy = tmp_path / "asy_planted.py"
    copy.write_text(
        "_LIMIT = const(4)\n"
        "WRAP_CAP = const(0xFFFFFFFF)\n"
        "class C:\n"
        "    def step(self):\n"
        "        self.n = min(self.n + 1, _LIMIT)\n"
        "        self.free += 1\n"
        "        self.by_const -= _LIMIT\n"
        "        make(max_val=0x40000000)\n"
        "        if self.ok < _LIMIT:\n"
        "            self.ok += 1\n"
        "        self.mod += 1\n"
        "        if self.mod >= _LIMIT:\n"
        "            self.mod = 0\n"
        "    def args(self, max_val=0x7FFFFFFF):\n"
        "        self.text += 'x'\n",
        encoding="utf-8",
    )
    tree = ast.parse(copy.read_text(encoding="utf-8"))
    assert min_steps("src/asy_planted.py", tree) == ["src/asy_planted.py:5: min(self.n + 1, _LIMIT)"]
    assert sorted(large_caps("src/asy_planted.py", tree)) == [
        ("src/asy_planted.py", "WRAP_CAP", 2, 0xFFFFFFFF),
        ("src/asy_planted.py", "max_val", 8, 0x40000000),
        ("src/asy_planted.py", "max_val", 14, 0x7FFFFFFF),
    ]
    assert unbounded_steps("src/asy_planted.py", tree) == {("src/asy_planted.py", "C.free"): 6, ("src/asy_planted.py", "C.by_const"): 7}
