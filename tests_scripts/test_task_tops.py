"""Every create_task() in src/ outside the task starters, and every start_server() callback, runs a coroutine ending in
a top of its own (its shape: _is_top() and ends_in_a_top() below); earlier statements are unchecked (SPECIFICATION.md
C.9). No generated module calls either."""

import ast
import functools
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES

from buildgen.generate import generate_device
from buildgen.source_ast import parse_source

Function = ast.FunctionDef | ast.AsyncFunctionDef
Classes = dict[str, tuple[str, ast.ClassDef]]
Module = tuple[str, str, ast.Module]  # file name, text, tree
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"


def _is_self(node: ast.expr) -> bool:
    return isinstance(node, ast.Name) and node.id == "self"


def _is_top(stmt: ast.stmt) -> bool:
    # A top: a `try` with no else/finally whose `except Exception as e:` calls self.pr.err_s() with e, raising nothing
    # (the logger's entry records a C-stack overflow, SPECIFICATION.md F.1).
    if not isinstance(stmt, ast.Try) or stmt.orelse or stmt.finalbody:  # either arm runs outside the handler
        return False
    for handler in stmt.handlers:
        raises = any(isinstance(node, ast.Raise) for s in handler.body for node in ast.walk(s))
        if isinstance(handler.type, ast.Name) and handler.type.id == "Exception" and handler.name:
            name = handler.name
            return not raises and any(_logs(s, name) for s in handler.body)
        if raises and not (isinstance(handler.type, ast.Attribute) and handler.type.attr == "CancelledError"):
            return False  # an earlier arm re-raising lets its exception past the top; only a cancellation may pass
    return False


@functools.cache
def _bound_class(cls: ast.ClassDef, attr: str) -> str | None:
    # The one class a `self.<attr> = Class(...)` in the class's own methods binds; None when none or several do.
    bound = {
        node.value.func.id
        for node in ast.walk(cls)
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
        and any(isinstance(t, ast.Attribute) and _is_self(t.value) and t.attr == attr for t in node.targets)
    }
    return bound.pop() if len(bound) == 1 else None


def _calls(node: ast.AST, name: str) -> bool:
    # `<anything>.<name>(...)` or a bare `<name>(...)`.
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return (isinstance(func, ast.Attribute) and func.attr == name) or (isinstance(func, ast.Name) and func.id == name)


def _check_target(classes: Classes, cls: str, ref: "ast.expr | None", site: str, what: str) -> "tuple[str | None, str | None]":
    # (the target checked as "Class.method()", the finding): a reference resolved to a method that ends in no top fails.
    target = _resolve(classes, cls, ref)
    if target is None:
        return None, f"{site}: {what} this check cannot resolve to a method"
    t_file, t_cls, t_fn = target
    name = f"{t_cls}.{t_fn.name}()"
    if not isinstance(t_fn, ast.AsyncFunctionDef) or not ends_in_a_top(t_fn):
        return name, f"{site}: its task {name} ({t_file}:{t_fn.lineno}) ends in no top"
    return name, None


@functools.cache
def _class_calls(cls: ast.ClassDef) -> "list[tuple[Function, ast.Call]]":
    # Each create_task()/start_server() call in the class's own methods, with its method, in walk order; cached on the
    # read-only trees parse_source() shares, so a plant re-walks only the file it changed.
    return [
        (fn, node)
        for fn in cls.body
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
        for node in ast.walk(fn)
        if isinstance(node, ast.Call) and (_calls(node, "create_task") or _calls(node, "start_server"))
    ]


def _classes(modules: "list[Module]") -> Classes:
    found: Classes = {}
    for name, _text, tree in modules:
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                found[node.name] = (name, node)
    return found


def _logs(stmt: ast.stmt, name: str) -> bool:
    # `self.pr.err_s(..., <name>, ...)` (or a logger's own `self.err_s(...)`) as a statement of its own.
    if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)):
        return False
    call = stmt.value
    func = call.func
    if not (isinstance(func, ast.Attribute) and func.attr == "err_s"):
        return False
    owner = func.value
    logger = _is_self(owner) or (isinstance(owner, ast.Attribute) and owner.attr == "pr" and _is_self(owner.value))
    return logger and any(isinstance(a, ast.Name) and a.id == name for a in call.args)


def _method(classes: Classes, name: str, method: str) -> "tuple[str, str, Function] | None":
    # (file, class, method) as attribute lookup finds it: the class first, then its bases in order.
    todo = [name]
    while todo:
        entry = classes.get(todo.pop(0))
        if entry is None:
            continue
        for fn in entry[1].body:
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn.name == method:
                return entry[0], entry[1].name, fn
        todo.extend(b.id for b in entry[1].bases if isinstance(b, ast.Name))
    return None


def _modules(src: Path) -> "list[Module]":
    found: list[Module] = []
    for path in sorted(src.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        found.append((path.name, text, parse_source(text, path.name)))  # buildgen's read-only trees: one parse per text
    return found


def _resolve(classes: Classes, cls: str, ref: "ast.expr | None") -> "tuple[str, str, Function] | None":
    # The method a `self.<m>` or `self.<attr>.<m>` reference names; any other expression is unresolved.
    if not isinstance(ref, ast.Attribute):
        return None
    owner = ref.value
    if _is_self(owner):
        return _method(classes, cls, ref.attr)
    if isinstance(owner, ast.Attribute) and _is_self(owner.value) and cls in classes:
        bound = _bound_class(classes[cls][1], owner.attr)
        return None if bound is None else _method(classes, bound, ref.attr)
    return None


def _server_calls(modules: "list[Module]") -> "list[tuple[str, int, int]]":
    # Every start_server() call in src/ as (file, line, column), wherever it stands; a call names it in its text.
    return [(name, line, col) for name, text, tree in modules if "start_server" in text for line, col in _server_sites(tree)]


@functools.cache
def _server_sites(tree: ast.Module) -> "tuple[tuple[int, int], ...]":
    return tuple((node.lineno, node.col_offset) for node in ast.walk(tree) if isinstance(node, ast.Call) and _calls(node, "start_server"))  # per read-only tree


def _starters(classes: "dict[str, ast.ClassDef]", name: str) -> "set[str]":
    # The methods a class's (or a base's) get_task_starters() returns, as `self.<method>` references; start_timers()
    # discards a timer starter's result (asy_system_service.py), so no supervisor watches a task created there.
    found: set[str] = set()
    todo = [name]
    while todo:
        node = classes.get(todo.pop())
        if node is None:
            continue
        todo.extend(b.id for b in node.bases if isinstance(b, ast.Name))
        for fn in node.body:
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn.name == "get_task_starters":
                found.update(n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "self")
    return found


def ends_in_a_top(fn: Function) -> bool:
    # The last statement is a top, or a `while True:` whose whole body is one, either in a cleanup-only `try`.
    last = fn.body[-1]
    while isinstance(last, ast.Try) and not last.handlers and not last.orelse:
        last = last.body[-1]  # a cleanup-only try: what it wraps is the task's end
    if isinstance(last, ast.While) and isinstance(last.test, ast.Constant) and last.test.value is True and not last.orelse:
        return len(last.body) == 1 and _is_top(last.body[0])
    return _is_top(last)


@pytest.fixture(scope="module")
def generated() -> "dict[str, str]":
    # Each device's generated module in memory, under the path it is written to, as test_fatal_report_sites.py builds it.
    return {f"build/generated_src/sensortask_{d}.py": generate_device(REPO_ROOT / "devices" / f"{d}.toml", SRC, REPO_ROOT / "ext").module_source for d in DEVICE_NAMES}


def generated_task_calls(sources: "dict[str, str]") -> "list[str]":
    # A generated module's tasks are its modules' task starters, which main() hands to start_tasks(): a call of its own is unwatched.
    return [
        f"{path}:{node.lineno}: a generated module calls {name}(), whose task no supervisor watches"
        for path, source in sorted(sources.items())
        for node in ast.walk(parse_source(source, path))
        if isinstance(node, ast.Call)
        for name in ("create_task", "start_server")
        if _calls(node, name)
    ]


def task_tops(src: Path) -> "tuple[list[str], list[str]]":
    # (findings, the targets checked): one per create_task() outside the starters and one per start_server(), whose
    # connection tasks no supervisor watches wherever it is called; one outside a class method is unresolved.
    modules = _modules(src)
    classes = _classes(modules)
    nodes = {name: entry[1] for name, entry in classes.items()}
    findings: list[str] = []
    checked: list[str] = []
    resolved: set[tuple[str, int, int]] = set()
    calling = {name for name, text, _parsed in modules if "create_task" in text or "start_server" in text}  # a call names its callee
    for file, cls in sorted(classes.values(), key=lambda entry: (entry[0], entry[1].lineno)):
        if file not in calling:
            continue
        starters = _starters(nodes, cls.name)
        for fn, node in _class_calls(cls):
            site = f"{file}:{node.lineno} {cls.name}.{fn.name}()"
            if _calls(node, "start_server"):
                resolved.add((file, node.lineno, node.col_offset))
                name, finding = _check_target(classes, cls.name, node.args[0] if node.args else None, site, "start_server() runs a callback")
            elif fn.name not in starters:  # a create_task()
                coro = node.args[0] if node.args else None
                name, finding = _check_target(classes, cls.name, coro.func if isinstance(coro, ast.Call) else None, site, "create_task() runs a coroutine")
            else:
                continue
            checked.extend([name] if name else [])
            findings.extend([finding] if finding else [])
    findings.extend(f"{file}:{line}: start_server() outside a class method, which this check cannot resolve" for file, line, col in _server_calls(modules) if (file, line, col) not in resolved)
    return findings, checked


def test_every_task_outside_the_starters_ends_in_its_own_top() -> None:
    findings, checked = task_tops(SRC)
    assert findings == []
    # No form is vacuous: a plain top, a forever loop's per-pass one and a connection callback's are all among the checked.
    assert {"SystemService._reset_when_due()", "CaptiveDNS.run()", "WebserverService._serve()"} <= set(checked), checked


def test_no_generated_module_creates_a_task(generated: "dict[str, str]") -> None:
    assert generated_task_calls(generated) == []
    # Not vacuous: every device's module is read, and each starts its tasks through start_tasks().
    assert len(generated) == len(DEVICE_NAMES) > 0
    assert all(any(_calls(node, "start_tasks") for node in ast.walk(parse_source(source, path))) for path, source in generated.items())


@pytest.mark.parametrize(("name", "call"), [("create_task", "asyncio.create_task(_plant())"), ("start_server", "await asyncio.start_server(_plant, '', 80)")], ids=["create_task", "start_server"])
def test_a_generated_module_that_creates_a_task_fails(generated: "dict[str, str]", name: str, call: str) -> None:
    anchor = "    await sysfunct.start_tasks("
    assert all(source.count(anchor) == 1 for source in generated.values()), "main()'s start_tasks() line moved"
    findings = generated_task_calls({path: source.replace(anchor, f"    {call}\n{anchor}") for path, source in generated.items()})
    assert [f.split(":", 1)[0] for f in findings] == sorted(generated), findings  # one per device
    assert all(f.endswith(f": a generated module calls {name}(), whose task no supervisor watches") for f in findings), findings
