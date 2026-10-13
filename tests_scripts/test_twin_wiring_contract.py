"""The twin wiring plan's one stated shape (SPECIFICATION.md Part L.4): every device's and fixture's plan
matches `buildgen.twin_wiring.TwinWiringPlan`, every key a consumer reads off a plan is a declared one, the
UART pair names buses its device declares, and the twin runner calls the generated `main()` as it is."""

import ast
import json
import types
from pathlib import Path
from typing import Union, get_args, get_origin, get_type_hints, is_typeddict

import pytest
import tomllib
from _devices import DEVICE_NAMES

from buildgen.generate import generate_device
from buildgen.twin_wiring import I2CAttachment, SpiAttachment, TwinWiringPlan, UartPair, compute_twin_wiring
from buildgen.validate import build_model

_REPO = Path(__file__).resolve().parent.parent
_TOMLS = [*(f"devices/{d}.toml" for d in DEVICE_NAMES), "tests_scripts/buildgen_fixtures/multi_instance.toml", "tests_scripts/buildgen_fixtures/novel_combo.toml"]
_CONSUMER_ROOTS = ("digital_twin", "tests", "tests_scripts", "scripts")
_DECLARED = {name: set(get_type_hints(cls)) for name, cls in (("TwinWiringPlan", TwinWiringPlan), ("UartPair", UartPair), ("I2CAttachment", I2CAttachment), ("SpiAttachment", SpiAttachment))}


def _consumers() -> "list[Path]":
    # Derived, never listed: every file in the consumer roots that names a wiring plan at all.
    return sorted(p for root in _CONSUMER_ROOTS for p in (_REPO / root).rglob("*.py") if "wiring_plan" in p.read_text(encoding="utf-8"))


def _main_keywords_passed(tree: ast.Module) -> "set[str]":
    # The keyword names of every `<x>.main(...)`/`main(...)` call that passes any, in one file.
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and n.keywords and ((isinstance(n.func, ast.Attribute) and n.func.attr == "main") or (isinstance(n.func, ast.Name) and n.func.id == "main"))]
    return {kw.arg for call in calls for kw in call.keywords if kw.arg is not None}


def _mismatches(value: object, hint: object, where: str) -> "list[str]":
    # Where `value` (a plan read back from JSON) departs from `hint`, recursively; [] when it conforms.
    if hint is type(None):
        return [] if value is None else [f"{where}: {value!r} is not None"]
    if get_origin(hint) in (Union, types.UnionType):
        return [] if any(not _mismatches(value, arg, where) for arg in get_args(hint)) else [f"{where}: {value!r} matches none of {hint}"]
    if is_typeddict(hint):
        if not isinstance(value, dict):
            return [f"{where}: {value!r} is not a table"]
        fields = get_type_hints(hint)
        found = [f"{where}: missing {key!r}" for key in sorted(getattr(hint, "__required_keys__", frozenset()) - value.keys())]
        found += [f"{where}: undeclared {key!r}" for key in sorted(value.keys() - fields.keys())]
        return found + [m for key in sorted(value.keys() & fields.keys()) for m in _mismatches(value[key], fields[key], f"{where}.{key}")]
    if get_origin(hint) is dict:
        if not isinstance(value, dict):
            return [f"{where}: {value!r} is not a table"]
        return [m for key, item in value.items() for m in (_mismatches(key, str, f"{where} key") + _mismatches(item, get_args(hint)[1], f"{where}[{key!r}]"))]
    if get_origin(hint) is list:
        if not isinstance(value, list):
            return [f"{where}: {value!r} is not a list"]
        return [m for i, item in enumerate(value) for m in _mismatches(item, get_args(hint)[0], f"{where}[{i}]")]
    if hint is int:
        return [] if isinstance(value, int) and not isinstance(value, bool) else [f"{where}: {value!r} is not an int"]
    return [] if isinstance(value, str) else [f"{where}: {value!r} is not a str"]


def _plan_key_reads(tree: ast.Module) -> "list[tuple[int, str, str]]":
    # Each function sees the module's names, plus what this file's own calls pass its positional parameters.
    module = _PlanKeyReads(_scope_nodes(tree), {})
    module.run()
    functions = {n.name: n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    passed: dict[str, dict[str, object]] = {name: {} for name in functions}
    reads: list[tuple[int, str, str]] = []
    for _ in range(3):  # a parameter bound in one round can feed a call in the next
        reads = list(module.reads)
        scopes = [module, *(_PlanKeyReads(_scope_nodes(fn), {**module.env, **passed[name]}) for name, fn in functions.items())]
        for scope in scopes[1:]:
            reads += scope.run()
        for scope in scopes:
            for call in scope.nodes:
                if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id in functions):
                    continue
                for arg, param in zip(call.args, functions[call.func.id].args.args, strict=False):
                    if (value := scope.type_of(arg)) is not None:
                        passed[call.func.id][param.arg] = value
            reads += scope.reads
    return sorted(set(reads))


def _scope_nodes(scope: ast.AST) -> "list[ast.AST]":
    # Every node of one scope, a nested function's body left to its own scope.
    found: list[ast.AST] = []
    pending = list(ast.iter_child_nodes(scope))
    while pending:
        node = pending.pop()
        found.append(node)
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            pending.extend(ast.iter_child_nodes(node))
    return found


def _strip_none(hint: object) -> object:
    if get_origin(hint) in (Union, types.UnionType):
        rest = [arg for arg in get_args(hint) if arg is not type(None)]
        return rest[0] if len(rest) == 1 else hint
    return hint


@pytest.mark.parametrize("toml_path", _TOMLS)
def test_every_plan_matches_the_declared_shape(toml_path: str) -> None:
    plan = json.loads(json.dumps(compute_twin_wiring(build_model(_REPO / toml_path, _REPO / "src"))))
    assert _mismatches(plan, TwinWiringPlan, "plan") == []


@pytest.mark.parametrize("toml_path", _TOMLS)
def test_the_uart_pair_names_two_uart_buses_the_device_declares(toml_path: str) -> None:
    plan = compute_twin_wiring(build_model(_REPO / toml_path, _REPO / "src"))
    with (_REPO / toml_path).open("rb") as f:
        buses = set(tomllib.load(f).get("bus", {}))
    if plan["uart"] is not None:
        pair = [plan["uart"]["initiator_bus"], plan["uart"]["responder_bus"]]
        assert all(bus in buses and bus.startswith("uart") for bus in pair), (pair, sorted(buses))
        assert pair[0] != pair[1]


class _PlanKeyReads:
    # A typed taint over one scope: what each name holds of a plan (by the declared hints), so a string key
    # read off a plan table is checked against its own TypedDict, and a bus-id key off a mapping is not.
    def __init__(self, nodes: "list[ast.AST]", outer: "dict[str, object]") -> None:
        self.nodes = nodes
        self.env: dict[str, object] = dict(outer)
        self.reads: list[tuple[int, str, str]] = []  # (line, TypedDict name, key)

    def _bind(self, target: ast.expr, value: object) -> None:
        if isinstance(target, ast.Name) and value is not None:
            self.env[target.id] = value
        elif isinstance(target, ast.Tuple) and isinstance(value, tuple) and value[0] == "pair":
            self._bind(target.elts[-1], value[1])
        elif isinstance(target, ast.Tuple) and isinstance(value, tuple) and value[0] == "values" and len(target.elts) == 1:
            self._bind(target.elts[0], value[1])

    def _call(self, node: ast.Call) -> object:
        if self._root(node.func):
            return TwinWiringPlan
        if isinstance(node.func, ast.Name) and node.func.id in ("sorted", "list", "tuple", "set", "iter", "reversed") and node.args:
            return self.type_of(node.args[0])
        if not isinstance(node.func, ast.Attribute):
            return None
        owner = _strip_none(self.type_of(node.func.value))
        if node.func.attr == "get" and node.args:
            key = node.args[0].value if isinstance(node.args[0], ast.Constant) else None
            return self._field(owner, key, node.lineno)
        if get_origin(owner) is dict and node.func.attr in ("items", "values"):
            return (node.func.attr, get_args(owner)[1])
        return None

    def _field(self, owner: object, key: object, line: int) -> object:
        owner = _strip_none(owner)
        if is_typeddict(owner) and isinstance(key, str):
            self.reads.append((line, getattr(owner, "__name__", str(owner)), key))
            return get_type_hints(owner).get(key)
        if get_origin(owner) in (dict, list):
            return get_args(owner)[-1]
        return None

    def _iterated(self, value: object) -> object:
        if isinstance(value, tuple):
            return ("pair", value[1]) if value[0] == "items" else value[1]
        return get_args(value)[0] if get_origin(value) is list else None

    def _root(self, node: ast.expr) -> bool:
        name = node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute) else ""
        return "wiring_plan" in name

    def run(self) -> "list[tuple[int, str, str]]":
        for _ in range(5):  # a fixpoint: a name may be bound below the line that reads it
            before = dict(self.env)
            for node in self.nodes:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        self._bind(target, self.type_of(node.value))
                elif isinstance(node, ast.AnnAssign) and node.value is not None:
                    self._bind(node.target, self.type_of(node.value))
                elif isinstance(node, (ast.For, ast.comprehension)):
                    self._bind(node.target, self._iterated(self.type_of(node.iter)))
            if self.env == before:
                break
        self.reads = []
        for node in self.nodes:
            if isinstance(node, (ast.Subscript, ast.Call)):
                self.type_of(node)
        return self.reads

    def type_of(self, node: ast.expr) -> object:
        if isinstance(node, ast.Name):
            if node.id in self.env:
                return self.env[node.id]
            return TwinWiringPlan if "plan" in node.id.lower() else None
        if isinstance(node, ast.Subscript):
            key = node.slice.value if isinstance(node.slice, ast.Constant) else None
            return self._field(self.type_of(node.value), key, node.lineno)
        if isinstance(node, ast.IfExp):
            return self.type_of(node.body) or self.type_of(node.orelse)
        if isinstance(node, ast.Call):
            return self._call(node)
        return None


def test_every_key_a_consumer_reads_off_a_plan_is_declared() -> None:
    reads = {path.relative_to(_REPO).as_posix(): _plan_key_reads(ast.parse(path.read_text(encoding="utf-8"))) for path in _consumers()}
    undeclared = [f"{path}:{line}: {owner}[{key!r}]" for path, found in reads.items() for line, owner, key in found if key not in _DECLARED[owner]]
    assert undeclared == []
    # Not vacuous: the twin's own two readers are found reading the plan.
    assert reads.get("digital_twin/machine.py") and reads.get("digital_twin/run_generic_integration.py"), sorted(reads)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_runner_and_the_boot_entry_call_the_generated_main_as_declared(device: str) -> None:
    generated = generate_device(_REPO / "devices" / f"{device}.toml", _REPO / "src", _REPO / "ext", build_date="2026-01-01T00:00:00Z")
    (main,) = [n for n in ast.parse(generated.module_source).body if isinstance(n, ast.AsyncFunctionDef) and n.name == "main"]
    accepted = {a.arg for a in main.args.kwonlyargs}
    required = {a.arg for a, default in zip(main.args.kwonlyargs, main.args.kw_defaults, strict=True) if default is None}
    assert not main.args.args and accepted == {"watchdog", "cfg_path", "debug", "web_host", "web_port"}
    for caller, source in (("digital_twin/run_generic_integration.py", (_REPO / "digital_twin" / "run_generic_integration.py").read_text()), ("the boot entry", generated.boot_entry_source)):
        passed = _main_keywords_passed(ast.parse(source))
        assert required <= passed <= accepted, (caller, sorted(passed))
