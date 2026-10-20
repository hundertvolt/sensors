"""Every broad handler in src/ and the generated modules records a C-stack overflow first (SPECIFICATION.md F.1): its first
statement is report_if_fatal(<its name>), the asy_print_log primitive, unless it ends in a bare raise; so is the first statement
of each function Microdot hands an exception it caught: the one errorhandler(Exception) registers and its rebound print_exception."""

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
# PrintLog.report_unretrieved() keeps `except Exception: pass`: tests_scripts/test_exception_handler_contract.py pins that
# form, since nothing may escape into asyncio's loop from the handler asyncio itself calls for an unretrieved task.
_EXEMPT = frozenset({("src/asy_print_log.py", "PrintLog.report_unretrieved")})

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


def _records_its_parameter(fn: "Function | None", *, resolves: bool) -> bool:
    # The function's first statement records its last parameter, the exception Microdot hands it.
    params = [] if fn is None else [a.arg for a in fn.args.args]
    return fn is not None and bool(params) and resolves and bool(fn.body) and _records(fn.body[0], params[-1])


def findings(path: str, source: str) -> "list[str]":
    tree = ast.parse(source)
    resolves = _resolves(tree)
    owner = _qualified(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and _is_broad(node):
            qual = owner.get(node, "<module>")
            if (path, qual) in _EXEMPT or _ends_in_bare_raise(node):
                continue
            if not (resolves and _records(node.body[0], node.name)):
                out.append(f"{path}:{node.lineno} {qual}(): a broad handler whose first statement is not {_PRIMITIVE}({node.name or '<unbound>'})")
    functions = {n.name: n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for line, name in _registered_handlers(tree):
        if not _records_its_parameter(functions.get(name), resolves=resolves):
            out.append(f"{path}:{line} errorhandler(Exception) registers {name}(), which does not start with {_PRIMITIVE}(<its exception parameter>)")
    for line, name in _rebound_printers(tree):
        if not _records_its_parameter(functions.get(name), resolves=resolves):
            out.append(f"{path}:{line} print_exception is rebound to {name}(), which does not start with {_PRIMITIVE}(<its exception parameter>)")
    return out


def _all_findings(sources: "dict[str, str]") -> "list[str]":
    return [finding for path, source in sorted(sources.items()) for finding in findings(path, source)]


@pytest.fixture(scope="module")
def sources() -> "dict[str, str]":
    # src/ from disk, and each device's three generated modules in memory, under the paths they are written to.
    out = {f"src/{p.name}": p.read_text(encoding="utf-8") for p in sorted(SRC.glob("*.py"))}
    for device in DEVICE_NAMES:
        result = generate_device(REPO_ROOT / "devices" / f"{device}.toml", SRC, REPO_ROOT / "ext")
        out[f"build/generated_src/sensortask_{device}.py"] = result.module_source
        out[f"build/generated_src/sensortask_{device}_main.py"] = result.boot_entry_source
        out[f"build/generated_src/sensortask_{device}_main_noautostart.py"] = result.boot_entry_noautostart_source
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


_IMPORT = "from asy_print_log import report_if_fatal\n\n\n"


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("    try:\n        f()\n    except Exception as e:\n        report_if_fatal(e)\n        log(e)\n", 0),
        ("    try:\n        f()\n    except Exception as e:\n        log(e)\n", 1),
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


def test_the_rebound_exception_printer_must_record_its_parameter() -> None:
    head = _IMPORT + "import microdot\n\n\nclass W:\n    def __init__(self):\n        microdot.print_exception = self._print_exception\n\n"
    assert len(findings("src/x.py", head + "    def _print_exception(self, exc):\n        log(exc)\n")) == 1
    assert len(findings("src/x.py", head + "    def _print_exception(self, exc):\n        log(exc)\n        report_if_fatal(exc)\n")) == 1
    assert findings("src/x.py", head + "    def _print_exception(self, exc):\n        report_if_fatal(exc)\n        log(exc)\n") == []


def test_the_exempt_handler_is_exempt_only_where_it_is() -> None:
    source = "class PrintLog:\n    def report_unretrieved(self, loop, context):\n        try:\n            f()\n        except Exception:\n            pass\n"
    assert findings("src/asy_print_log.py", source) == []
    assert len(findings("src/other.py", source)) == 1
