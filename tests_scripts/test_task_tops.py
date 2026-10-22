"""Every create_task() in src/ outside the task starters, and every start_server() callback, runs a coroutine ending in
a top of its own (its shape: _is_top() and ends_in_a_top() below); earlier statements are unchecked (SPECIFICATION.md
C.9). No generated module calls either."""

import ast
import functools
import shutil
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES
from test_task_inventory import REPO_ROOT, SRC, _starters

from buildgen.generate import generate_device
from buildgen.source_ast import parse_source

Function = ast.FunctionDef | ast.AsyncFunctionDef
Classes = dict[str, tuple[str, ast.ClassDef]]
Module = tuple[str, str, ast.Module]  # file name, text, tree


def _is_self(node: ast.expr) -> bool:
    return isinstance(node, ast.Name) and node.id == "self"


def _is_top(stmt: ast.stmt) -> bool:
    # A top: a `try` with no else/finally whose `except Exception as e:` calls report_if_fatal(e) and awaits
    # self.pr.err_s() with e, raising nothing.
    if not isinstance(stmt, ast.Try) or stmt.orelse or stmt.finalbody:  # either arm runs outside the handler
        return False
    for handler in stmt.handlers:
        raises = any(isinstance(node, ast.Raise) for s in handler.body for node in ast.walk(s))
        if isinstance(handler.type, ast.Name) and handler.type.id == "Exception" and handler.name:
            name = handler.name
            return not raises and any(_reports(s, name) for s in handler.body) and any(_logs(s, name) for s in handler.body)
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


def _edit(src: Path, name: str, old: str, new: str) -> None:
    path = src / name
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, f"{name}: the anchor is not unique: {old!r}"
    path.write_text(text.replace(old, new), encoding="utf-8")


def _logs(stmt: ast.stmt, name: str) -> bool:
    # `await self.pr.err_s(..., <name>, ...)` as a statement of its own.
    if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Await) and isinstance(stmt.value.value, ast.Call)):
        return False
    call = stmt.value.value
    func = call.func
    logger = isinstance(func, ast.Attribute) and func.attr == "err_s" and isinstance(func.value, ast.Attribute) and func.value.attr == "pr" and _is_self(func.value.value)
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


def _reports(stmt: ast.stmt, name: str) -> bool:
    if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)):
        return False
    call = stmt.value
    arg = call.args[0] if len(call.args) == 1 else None
    return isinstance(call.func, ast.Name) and call.func.id == "report_if_fatal" and isinstance(arg, ast.Name) and arg.id == name


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


@pytest.fixture
def src_copy(tmp_path: Path) -> Path:
    return Path(shutil.copytree(SRC, tmp_path / "src"))


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


@pytest.mark.parametrize(
    ("name", "cls", "method", "loop"),
    [("asy_neopixel_driver.py", "NeopixelDriver", "toggle", "_signal_loop"), ("asy_ntp_client.py", "NTPClient", "start_check_timer", "_sync_loop")],
    ids=["in-a-plain-method", "in-a-timer-starter"],  # start_timers() discards a timer starter's result: no supervisor watches its task
)
def test_a_supervised_loop_started_outside_its_starter_fails(src_copy: Path, name: str, cls: str, method: str, loop: str) -> None:
    _edit(src_copy, name, f"    def {method}(self) -> None:\n", f"    def {method}(self) -> None:\n        asyncio.create_task(self.{loop}())\n")
    findings = task_tops(src_copy)[0]
    assert len(findings) == 1 and f"{cls}.{method}(): its task {cls}.{loop}() ({name}:" in findings[0], findings


@pytest.mark.parametrize(
    ("name", "old", "new"),
    [
        ("asy_config_manager.py", "        except Exception as e:  # an unsupervised task's top", "        except OSError as e:  # an unsupervised task's top"),
        ("asy_config_manager.py", '"- flush task failed:", e, errno=', '"- flush task failed:", errno='),
        ("asy_config_manager.py", "            report_if_fatal(e)\n            self.unpersisted = True  # the finally", "            self.unpersisted = True  # the finally"),
        ("asy_wifi_service.py", '"LED flash task failed:", e, errno=_ERR_UNEXPECTED)\n', '"LED flash task failed:", e, errno=_ERR_UNEXPECTED)\n        self._led_off()\n'),
        ("asy_wifi_service.py", '"LED flash task failed:", e, errno=_ERR_UNEXPECTED)\n', '"LED flash task failed:", e, errno=_ERR_UNEXPECTED)\n        else:\n            self._led_off()\n'),
        ("asy_wifi_service.py", '"LED flash task failed:", e, errno=_ERR_UNEXPECTED)\n', '"LED flash task failed:", e, errno=_ERR_UNEXPECTED)\n        finally:\n            self._led_off()\n'),
        ("asy_wifi_service.py", '"LED flash task failed:", e, errno=_ERR_UNEXPECTED)\n', '"LED flash task failed:", e, errno=_ERR_UNEXPECTED)\n            raise\n'),
        ("asy_wifi_service.py", "        except Exception as e:  # unsupervised task's top", "        except OSError:\n            raise\n        except Exception as e:  # unsupervised task's top"),
        ("asy_captive_dns.py", "            while True:\n                try:\n", "            while True:\n                await asyncio.sleep(0)\n                try:\n"),
        ("asy_webserver_service.py", '                report_if_fatal(e)\n                await self.pr.err_s("Connection task failed:", e, errno=_ERR_UNEXPECTED)\n', '                await self.pr.err_s("Connection task failed:", e, errno=_ERR_UNEXPECTED)\n'),
    ],
    ids=["narrowed", "cause-not-logged", "fatal-not-reported", "work-after-the-top", "work-in-its-else", "work-in-its-finally", "raised-after-the-log", "an-earlier-arm-re-raises", "loop-pass-outside-the-top", "callback-fatal-not-reported"],
)
def test_a_top_that_does_not_cover_its_task_fails(src_copy: Path, name: str, old: str, new: str) -> None:
    _edit(src_copy, name, old, new)
    findings = task_tops(src_copy)[0]
    assert len(findings) == 1 and f" ({name}:" in findings[0] and findings[0].endswith(") ends in no top"), findings  # the task's own file


def test_a_connection_callback_whose_top_is_removed_fails(src_copy: Path) -> None:
    top = (
        "            except Exception as e:  # the connection task's top: its creator logs what escaped the request (the count, a\n"
        "                # proxy, a release, a trace); the task raises out only via a failing logging call (SPECIFICATION.md A.5, G.2)\n"
        "                # or the finally's own calls on an exhausted heap: _close_writer() catches every Exception, decrement() cannot raise\n"
        "                report_if_fatal(e)\n"
        '                await self.pr.err_s("Connection task failed:", e, errno=_ERR_UNEXPECTED)\n'
    )
    _edit(src_copy, "asy_webserver_service.py", top, "")  # only the cancellation arm is left
    findings = task_tops(src_copy)[0]
    assert len(findings) == 1 and "WebserverService._serve_loop(): its task WebserverService._serve() (asy_webserver_service.py:" in findings[0], findings


def test_an_unresolvable_coroutine_fails(src_copy: Path) -> None:
    _edit(src_copy, "asy_wifi_service.py", "create_task(self._flash_led(on_ms, off_ms))", "create_task(_flash(on_ms, off_ms))")
    findings = task_tops(src_copy)[0]
    assert len(findings) == 1 and "WifiService._run_led_pattern(): create_task() runs a coroutine this check cannot resolve" in findings[0], findings


def test_an_unresolvable_or_unowned_server_callback_fails(src_copy: Path) -> None:
    _edit(src_copy, "asy_webserver_service.py", "start_server(self._serve, ", "start_server(_serve, ")
    findings = task_tops(src_copy)[0]
    assert len(findings) == 1 and "WebserverService._serve_loop(): start_server() runs a callback this check cannot resolve" in findings[0], findings
    path = src_copy / "asy_captive_dns.py"
    path.write_text(path.read_text(encoding="utf-8") + "\n\nasync def _plant() -> None:\n    await asyncio.start_server(_plant, '', 80)\n", encoding="utf-8")
    findings = task_tops(src_copy)[0]
    assert len(findings) == 2 and "asy_captive_dns.py:" in findings[1] and findings[1].endswith(": start_server() outside a class method, which this check cannot resolve"), findings
