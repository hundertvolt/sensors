"""Setters answer `bool` (SPECIFICATION.md C.5.2): every push callback is registered in its class's `__init__`
and nowhere else, and returns `bool`, as does every `set_*` a push callback, a settings group or a generated
REST dispatcher reaches; `_set_dict_cfg`/`_set_mgr_cfg` answer the `WriteValidity` forms C.5.2 documents."""

import ast
import re
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES

from buildgen.generate import generate_device

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
_PUSH = "_push_callbacks"
_MUTATORS = frozenset({"update", "setdefault", "pop", "popitem", "clear", "__setitem__", "__delitem__"})
# C.5.2's documented answers for the settings-group entry point and the store extension point.
_DOCUMENTED = {"_set_dict_cfg": "WriteValidity", "_set_mgr_cfg": "tuple[bool, WriteValidity]"}
# Named out of the rule: chip-protocol classes answer the chip's own way, a Locked* setter only stores.
_CHIP_OR_LOCKED_RE = re.compile(r"^(?:\w+_I2C|FRAM_SPI|Locked\w*)$")
# Wiring setters, each by name: none is a settings write, so none answers applied/rejected.
_NAMED_OUT = {
    ("FRAMManager", "set_pause"): "wiring: the storage pause callable SystemService is constructed with",
    ("_FRAMBaseChunk", "set_verify"): "wiring: a chunk's verify mode, set by its owner after allocation",
}
# The RouteSources fields the generated module fills with a REST command dispatcher.
_DISPATCHER_FIELDS = frozenset({"system_cmd", "notification_led", "notification_pause"})


Assignment = ast.Assign | ast.AnnAssign | ast.AugAssign


def _targets(stmt: Assignment) -> list[ast.expr]:
    return stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]


class Classes:
    def __init__(self, src: Path) -> None:
        self.nodes: dict[str, ast.ClassDef] = {}
        self.file: dict[str, str] = {}
        for path in sorted(src.glob("*.py")):
            for node in ast.parse(path.read_text(encoding="utf-8"), filename=path.name).body:
                if isinstance(node, ast.ClassDef):
                    self.nodes[node.name] = node
                    self.file[node.name] = path.name

    def by_name(self, name: str) -> list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
        return [(cls, fn) for cls, node in self.nodes.items() for fn in node.body if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn.name == name]

    def method(self, cls: str, name: str) -> tuple[str, ast.FunctionDef | ast.AsyncFunctionDef] | None:
        for owner in self.mro(cls):
            for fn in self.nodes[owner].body:
                if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn.name == name:
                    return owner, fn
        return None

    def mro(self, name: str) -> list[str]:
        out, todo = [], [name]
        while todo:
            current = todo.pop(0)
            if current in self.nodes and current not in out:
                out.append(current)
                todo.extend(b.id for b in self.nodes[current].bases if isinstance(b, ast.Name))
        return out


def _returns(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    if fn.returns is None:
        return "<none>"
    node = fn.returns
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else ast.unparse(node)


def _named_out(cls: str, name: str) -> bool:
    return bool(_CHIP_OR_LOCKED_RE.match(cls)) or (cls, name) in _NAMED_OUT


def _is_self_push(node: ast.expr) -> bool:
    target = node.value if isinstance(node, ast.Subscript) else node
    return isinstance(target, ast.Attribute) and target.attr == _PUSH and isinstance(target.value, ast.Name) and target.value.id == "self"


def _calls_to_setters(body: ast.AST) -> list[ast.Call]:
    return [n for n in ast.walk(body) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr.startswith("set_")]


def _check_bool(classes: Classes, cls: str, fn: ast.FunctionDef | ast.AsyncFunctionDef, why: str, findings: list[str]) -> None:
    if not _named_out(cls, fn.name) and _returns(fn) != "bool":
        findings.append(f"{classes.file[cls]}:{fn.lineno} {cls}.{fn.name}() -> {_returns(fn)}: {why}, so it answers bool")


def _reached_by_name(classes: Classes, call: ast.Call, origin: str, findings: list[str]) -> None:
    candidates = classes.by_name(call.func.attr)  # type: ignore[attr-defined]
    if not candidates:
        findings.append(f"{origin}: `{ast.unparse(call.func)}` names no method in src/")
    for cls, fn in candidates:
        _check_bool(classes, cls, fn, f"reached by {origin}", findings)


def push_findings(classes: Classes) -> list[str]:
    findings: list[str] = []
    for cls, node in classes.nodes.items():
        for fn in (n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))):
            where = f"{classes.file[cls]} {cls}.{fn.name}()"
            for stmt in (s for s in ast.walk(fn) if isinstance(s, (ast.Assign, ast.AnnAssign, ast.AugAssign))):
                for target in (t for t in _targets(stmt) if _is_self_push(t)):
                    if fn.name != "__init__":
                        findings.append(f"{where}:{stmt.lineno}: _push_callbacks is assigned outside __init__")
                    if isinstance(target, ast.Subscript):
                        value = stmt.value
                        if value is None or not (isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name) and value.value.id == "self"):
                            findings.append(f"{where}:{stmt.lineno}: a push callback is registered as `{ast.unparse(value) if value is not None else 'nothing'}`, not a method of self")
                            continue
                        found = classes.method(cls, value.attr)
                        if found is None:
                            findings.append(f"{where}:{stmt.lineno}: the push callback self.{value.attr} is no method of {cls}")
                            continue
                        owner, method = found
                        _check_bool(classes, owner, method, "a push callback", findings)
                        for call in _calls_to_setters(method):
                            origin = f"the push callback {owner}.{method.name}()"
                            receiver = call.func.value  # type: ignore[attr-defined]
                            if isinstance(receiver, ast.Name) and receiver.id == "self" and (own := classes.method(cls, call.func.attr)):  # type: ignore[attr-defined]
                                _check_bool(classes, own[0], own[1], f"reached by {origin}", findings)
                            else:
                                _reached_by_name(classes, call, origin, findings)
            if fn.name != "__init__":
                findings.extend(
                    f"{where}:{n.lineno}: _push_callbacks.{n.func.attr}() outside __init__"
                    for n in ast.walk(fn)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in _MUTATORS and _is_self_push(n.func.value)
                )
    return findings


def documented_findings(classes: Classes) -> list[str]:
    return [
        f"{classes.file[cls]}:{fn.lineno} {cls}.{fn.name}() -> {_returns(fn)}: C.5.2 documents {answer}"
        for name, answer in _DOCUMENTED.items()
        for cls, fn in classes.by_name(name)
        if _returns(fn) != answer
    ]


def dispatcher_findings(classes: Classes, device: str, module_source: str) -> list[str]:
    # The generated REST dispatchers and settings-group hooks, and every set_* they call or hand over.
    tree = ast.parse(module_source)
    functions = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    findings: list[str] = []
    dispatchers = 0
    for call in (n for n in ast.walk(tree) if isinstance(n, ast.Call)):
        callee = call.func.id if isinstance(call.func, ast.Name) else ""
        if callee == "RouteSources":
            for kw in call.keywords:
                if kw.arg in _DISPATCHER_FIELDS and isinstance(kw.value, ast.Name) and kw.value.id in functions:
                    dispatchers += 1
                    for inner in _calls_to_setters(functions[kw.value.id]):
                        _reached_by_name(classes, inner, f"sensortask_{device}.{kw.value.id}()", findings)
        if callee in ("RouteSources", "SettingsGroup"):
            for value in [*call.args, *(kw.value for kw in call.keywords)]:
                if isinstance(value, ast.Attribute) and value.attr.startswith("set_"):
                    _reached_by_name(classes, ast.Call(func=value, args=[], keywords=[]), f"sensortask_{device} {callee}(...)", findings)
    assert dispatchers or "RouteSources(" not in module_source, f"sensortask_{device}: a RouteSources call with no dispatcher found - the scan would be vacuous"
    return findings


def all_findings(src: Path, modules: dict[str, str]) -> list[str]:
    classes = Classes(src)
    findings = push_findings(classes) + documented_findings(classes)
    findings += [f"named out of the rule, but {cls}.{name} is defined nowhere in src/ (stale)" for cls, name in _NAMED_OUT if classes.method(cls, name) is None]
    for device, source in sorted(modules.items()):
        for finding in dispatcher_findings(classes, device, source):
            if finding not in findings:
                findings.append(finding)
    return findings


@pytest.fixture(scope="module")
def modules() -> dict[str, str]:
    return {d: generate_device(REPO_ROOT / "devices" / f"{d}.toml", SRC, REPO_ROOT / "ext").module_source for d in DEVICE_NAMES}


def test_every_reached_setter_answers_bool_and_push_callbacks_register_once(modules: dict[str, str]) -> None:
    assert all_findings(SRC, modules) == []


def test_the_scan_reaches_push_callbacks_and_generated_dispatchers(modules: dict[str, str]) -> None:
    classes = Classes(SRC)
    registered = [stmt for node in classes.nodes.values() for stmt in ast.walk(node) if isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Subscript) and _is_self_push(t) for t in stmt.targets)]
    assert len(registered) >= 15, registered
    assert all("RouteSources(" in source for source in modules.values())
