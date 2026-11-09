"""Every broad handler in src/ and the generated device modules records a C-stack overflow (SPECIFICATION.md F.1):
it hands its exception to a logger entry, which records it, or starts with report_if_fatal(<its name>), unless it ends
in a bare raise; so do Microdot's errorhandler(Exception) function and its rebound print_exception."""

import ast
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES

from buildgen.generate import generate_device

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
_PRIMITIVE = "report_if_fatal"
_HOME = "asy_print_log"
# RuntimeError is broad too: the C-stack overflow is one (py/cstack.c, v1.29.0), so a handler naming it can catch it.
_BROAD = frozenset({"Exception", "BaseException", "RuntimeError"})
# PrintLog.report_unretrieved() keeps `except Exception: pass` (tests_scripts/test_exception_handler_contract.py); the
# shutdown's unbound `pass` handler awaits a stopped task once the supervisor, the record's one reader, has stopped.
_EXEMPT = frozenset({("src/asy_print_log.py", "PrintLog.report_unretrieved")})
_EXEMPT_PASS = frozenset({("src/asy_system_service.py", "SystemService._shutdown_sequence")})
# Each logger entry point, whose first step records an overflow among its arguments; `_err` is UARTComm's err_q() forwarder.
_LOGGER_METHODS = frozenset({"err", "err_s", "err_q", "wrn", "wrn_s", "wrn_q", "one", "evt", "all", "_err"})

Function = ast.FunctionDef | ast.AsyncFunctionDef


def _is_broad(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return True
    kinds = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    return any(isinstance(kind, ast.Name) and kind.id in _BROAD for kind in kinds)


def _resolves(tree: ast.Module) -> bool:
    # The name is the primitive itself: imported from its home module unrenamed, or defined at the top of that module.
    imported = any(
        isinstance(node, ast.ImportFrom) and node.module == _HOME and any(a.name == _PRIMITIVE and a.asname is None for a in node.names)
        for node in tree.body
    )
    return imported or any(isinstance(node, ast.FunctionDef) and node.name == _PRIMITIVE for node in tree.body)


def _records(stmt: ast.stmt, name: "str | None") -> bool:
    # `report_if_fatal(<name>)` as a bare statement, its one argument the exception's own binding.
    if name is None or not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Call):
        return False
    call = stmt.value
    return isinstance(call.func, ast.Name) and call.func.id == _PRIMITIVE and not call.keywords and len(call.args) == 1 and isinstance(call.args[0], ast.Name) and call.args[0].id == name


def _logs(stmt: ast.stmt, name: "str | None") -> bool:
    # `<logger>.<entry>(..., <name>, ...)` inside an expression statement of the handler's own body, awaited or passed on.
    if name is None or not isinstance(stmt, ast.Expr):
        return False
    calls = [n for n in ast.walk(stmt.value) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in _LOGGER_METHODS]
    return any(isinstance(a, ast.Name) and a.id == name for call in calls for a in call.args)


def _until_exit(body: "list[ast.stmt]") -> "list[ast.stmt]":
    # The statements that run on every path: those before the first that can leave the block (a return, raise, break or
    # continue anywhere inside it).
    out: list[ast.stmt] = []
    for stmt in body:
        if any(isinstance(n, (ast.Return, ast.Raise, ast.Break, ast.Continue)) for n in ast.walk(stmt)):
            break
        out.append(stmt)
    return out


def _is_exempt_pass(path: str, qual: str, handler: ast.ExceptHandler) -> bool:
    return (path, qual) in _EXEMPT_PASS and handler.name is None and len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass)


def _ends_in_bare_raise(handler: ast.ExceptHandler) -> bool:
    last = handler.body[-1]
    return isinstance(last, ast.Raise) and last.exc is None


def _qualified(tree: ast.Module) -> "dict[ast.AST, str]":
    # Each function's dotted name (Class.method), and every node inside it mapped to that name.
    owner: dict[ast.AST, str] = {}

    def visit(node: ast.AST, prefix: str, current: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = prefix + child.name
                inner = name if not isinstance(child, ast.ClassDef) else current
                owner[child] = name
                visit(child, name + ".", inner)
            else:
                owner[child] = current
                visit(child, prefix, current)

    visit(tree, "", "<module>")
    return owner


def _registered_handlers(tree: ast.Module) -> "list[tuple[int, str]]":
    # (line, function name) of each function given to errorhandler(Exception), called or used as a decorator.
    def is_registration(call: ast.expr) -> bool:
        return (
            isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr == "errorhandler"
            and len(call.args) == 1 and isinstance(call.args[0], ast.Name) and call.args[0].id == "Exception"
        )

    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and is_registration(node.func) and len(node.args) == 1:
            target = node.args[0]
            name = target.attr if isinstance(target, ast.Attribute) else target.id if isinstance(target, ast.Name) else ""
            found.append((node.lineno, name))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(is_registration(d) for d in node.decorator_list):
            found.append((node.lineno, node.name))
    return found


def _rebound_printers(tree: ast.Module) -> "list[tuple[int, str]]":
    # (line, function name) of each function assigned over a module's print_exception: Microdot's request-read catch calls
    # that alone (ext/microdot.py handle_request()), so it is the only place such an exception is seen.
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Attribute) and t.attr == "print_exception" for t in node.targets):
            value = node.value
            found.append((node.lineno, value.attr if isinstance(value, ast.Attribute) else value.id if isinstance(value, ast.Name) else ""))
    return found


def _records_its_parameter(fn: "Function | None", *, resolves: bool, logged: bool = False) -> bool:
    # The function's first statement records its last parameter, the exception Microdot hands it, or (logged) a statement
    # of its body hands that to a logger call.
    params = [] if fn is None else [a.arg for a in fn.args.args]
    if fn is None or not params or not fn.body:
        return False
    return (resolves and _records(fn.body[0], params[-1])) or (logged and any(_logs(s, params[-1]) for s in _until_exit(fn.body)))


def findings(path: str, source: str) -> "list[str]":
    tree = ast.parse(source)
    resolves = _resolves(tree)
    owner = _qualified(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and _is_broad(node):
            qual = owner.get(node, "<module>")
            if (path, qual) in _EXEMPT or _is_exempt_pass(path, qual, node) or _ends_in_bare_raise(node):
                continue
            if not ((resolves and _records(node.body[0], node.name)) or any(_logs(s, node.name) for s in _until_exit(node.body))):
                out.append(f"{path}:{node.lineno} {qual}(): a broad handler that neither logs {node.name or '<unbound>'} nor starts with {_PRIMITIVE}()")
    functions = {n.name: n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for line, name in _registered_handlers(tree):
        if not _records_its_parameter(functions.get(name), resolves=resolves, logged=True):
            out.append(f"{path}:{line} errorhandler(Exception) registers {name}(), which neither logs its exception parameter nor starts with {_PRIMITIVE}()")
    for line, name in _rebound_printers(tree):
        if not _records_its_parameter(functions.get(name), resolves=resolves, logged=True):
            out.append(f"{path}:{line} print_exception is rebound to {name}(), which neither logs its exception parameter nor starts with {_PRIMITIVE}()")
    return out


def _all_findings(sources: "dict[str, str]") -> "list[str]":
    return [finding for path, source in sorted(sources.items()) for finding in findings(path, source)]


@pytest.fixture(scope="module")
def sources() -> "dict[str, str]":
    # src/ from disk, and each generated device module in memory under its written path; the boot entries' handlers run
    # once the loop has ended, where nothing reads the record.
    out = {f"src/{p.name}": p.read_text(encoding="utf-8") for p in sorted(SRC.glob("*.py"))}
    for device in DEVICE_NAMES:
        result = generate_device(REPO_ROOT / "devices" / f"{device}.toml", SRC, REPO_ROOT / "ext")
        out[f"build/generated_src/sensortask_{device}.py"] = result.module_source
    return out


def test_every_broad_handler_records_a_stack_overflow_first(sources: "dict[str, str]") -> None:
    assert _all_findings(sources) == []


def test_the_walk_reaches_the_handlers_it_checks(sources: "dict[str, str]") -> None:
    # Not vacuous: src/ holds broad handlers, the one errorhandler(Exception) registration and the one rebound printer, and
    # the exempt handler still exists with its broad clause (a stale exemption would hide nothing and must go).
    trees = {path: ast.parse(source) for path, source in sources.items() if path.startswith("src/")}
    broad = [n for tree in trees.values() for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler) and _is_broad(n)]
    assert len(broad) >= 50, len(broad)
    assert sum(len(_registered_handlers(tree)) for tree in trees.values()) == 1
    assert sum(len(_rebound_printers(tree)) for tree in trees.values()) == 1
    for path, qual in _EXEMPT:
        owner = _qualified(trees[path])
        assert any(isinstance(n, ast.ExceptHandler) and _is_broad(n) and owner[n] == qual for n in ast.walk(trees[path])), (path, qual)
    for path, qual in _EXEMPT_PASS:
        owner = _qualified(trees[path])
        assert any(isinstance(n, ast.ExceptHandler) and _is_broad(n) and _is_exempt_pass(path, owner.get(n, ""), n) for n in ast.walk(trees[path])), (path, qual)


_IMPORT = "from asy_print_log import report_if_fatal\n\n\n"


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("    try:\n        f()\n    except Exception as e:\n        report_if_fatal(e)\n        log(e)\n", 0),
        ("    try:\n        f()\n    except Exception as e:\n        log(e)\n", 1),
        ("    try:\n        f()\n    except Exception as e:\n        x = 1\n        self.pr.err('failed:', e)\n", 0),
        ("    try:\n        f()\n    except Exception as e:\n        await self.pr.err_s('failed:', e, errno=3)\n", 0),
        ("    try:\n        f()\n    except Exception as e:\n        await self._err(3, 'failed:', e)\n", 0),
        ("    try:\n        f()\n    except Exception as e:\n        await self._trace(self.pr.err_s('failed:', e, errno=3))\n", 0),
        ("    try:\n        f()\n    except Exception as e:\n        self.pr.err('failed')\n", 1),
        ("    try:\n        f()\n    except Exception as e:\n        self.pr.err('failed:', other)\n", 1),
        ("    try:\n        f()\n    except Exception as e:\n        self.store.save(e)\n", 1),
        ("    try:\n        f()\n    except Exception as e:\n        if g():\n            self.pr.err('failed:', e)\n", 1),
        ("    try:\n        f()\n    except Exception as e:\n        return\n        self.pr.err('failed:', e)\n", 1),
        ("    try:\n        f()\n    except Exception as e:\n        if g():\n            return\n        self.pr.err('failed:', e)\n", 1),
        ("    for x in y:\n        try:\n            f()\n        except Exception as e:\n            if g():\n                continue\n            self.pr.err('failed:', e)\n", 1),
        ("    try:\n        f()\n    except Exception as e:\n        self.pr.err('failed:', e)\n        return None\n", 0),
        ("    try:\n        f()\n    except (OSError, Exception) as e:\n        log(e)\n", 1),
        ("    try:\n        f()\n    except BaseException:\n        pass\n", 1),
        ("    try:\n        f()\n    except:\n        pass\n", 1),
        ("    try:\n        f()\n    except Exception as e:\n        log(e)\n        report_if_fatal(e)\n", 1),
        ("    try:\n        f()\n    except Exception as e:\n        report_if_fatal(other)\n", 1),
        ("    try:\n        f()\n    except Exception:\n        log()\n        raise\n", 0),
        ("    try:\n        f()\n    except (OSError, ValueError) as e:\n        log(e)\n", 0),
        ("    try:\n        f()\n    except RuntimeError:\n        pass\n", 1),
        ("    try:\n        f()\n    except (OSError, RuntimeError) as e:\n        log(e)\n", 1),
        ("    try:\n        f()\n    except RuntimeError as e:\n        report_if_fatal(e)\n", 0),
        ("    try:\n        f()\n    except NotImplementedError:\n        pass\n", 0),
    ],
)
def test_a_fabricated_handler_is_judged_by_its_first_statement(body: str, expected: int) -> None:
    assert len(findings("src/x.py", _IMPORT + "def g():\n" + body)) == expected


def test_the_call_counts_only_as_the_asy_print_log_primitive() -> None:
    body = "def g():\n    try:\n        f()\n    except Exception as e:\n        report_if_fatal(e)\n"
    assert len(findings("src/x.py", body)) == 1  # not imported
    assert len(findings("src/x.py", "from other import report_if_fatal\n\n\n" + body)) == 1
    assert findings("src/x.py", _IMPORT + body) == []


def test_the_registered_exception_handler_must_record_its_parameter() -> None:
    head = _IMPORT + "class W:\n    def __init__(self, app):\n        app.errorhandler(Exception)(self.on_error)\n\n"
    assert len(findings("src/x.py", head + "    async def on_error(self, request, exc):\n        log(exc)\n")) == 1
    assert findings("src/x.py", head + "    async def on_error(self, request, exc):\n        report_if_fatal(exc)\n        log(exc)\n") == []
    assert findings("src/x.py", head + "    async def on_error(self, request, exc):\n        await self.pr.err_s('failed:', exc, errno=3)\n") == []


def test_the_rebound_exception_printer_must_record_its_parameter() -> None:
    head = _IMPORT + "import microdot\n\n\nclass W:\n    def __init__(self):\n        microdot.print_exception = self._print_exception\n\n"
    assert len(findings("src/x.py", head + "    def _print_exception(self, exc):\n        log(exc)\n")) == 1
    assert len(findings("src/x.py", head + "    def _print_exception(self, exc):\n        log(exc)\n        report_if_fatal(exc)\n")) == 1
    assert findings("src/x.py", head + "    def _print_exception(self, exc):\n        self.pr.err('caught:', exc)\n") == []  # the logger records first
    assert len(findings("src/x.py", head + "    def _print_exception(self, exc):\n        if g():\n            return\n        self.pr.err('caught:', exc)\n")) == 1
    assert findings("src/x.py", head + "    def _print_exception(self, exc):\n        report_if_fatal(exc)\n        log(exc)\n") == []


def test_the_exempt_handler_is_exempt_only_where_it_is() -> None:
    source = "class PrintLog:\n    def report_unretrieved(self, loop, context):\n        try:\n            f()\n        except Exception:\n            pass\n"
    assert findings("src/asy_print_log.py", source) == []
    assert len(findings("src/other.py", source)) == 1


def test_the_shutdown_exemption_covers_only_its_unbound_pass_handler() -> None:
    head = "class SystemService:\n    async def _shutdown_sequence(self):\n        try:\n            f()\n"
    assert findings("src/asy_system_service.py", head + "        except Exception:\n            pass\n") == []
    assert len(findings("src/asy_system_service.py", head + "        except Exception as e:\n            pass\n")) == 1
    assert len(findings("src/asy_system_service.py", head + "        except Exception as e:\n            await self.pr.err_s('failed:')\n")) == 1
    assert len(findings("src/other.py", head + "        except Exception:\n            pass\n")) == 1
