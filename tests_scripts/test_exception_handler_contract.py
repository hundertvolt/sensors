"""Whole-tree contract for asyncio's unretrieved-task-exception handler (SPECIFICATION.md Part F.1): only the firmware's
start_and_check_tasks() installs one, and only where none is set; both handler bodies are allocation-free and never
raise by construction; every PC entry point installs the always-printing PC report before the firmware starts."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from _devices import DEVICE_NAMES
from _script_loader import load_script_module

from buildgen.generate import generate_device

if TYPE_CHECKING:
    from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parent.parent

_FIRMWARE_FILE = "src/asy_system_service.py"  # the one install site
_INSTALLER = "start_and_check_tasks"
_HANDLER_FILE = "src/asy_print_log.py"  # print() lives only in the logger module (test_code_conventions.py)
_HANDLER_CLASS = "PrintLog"
_FIRMWARE_HANDLER = "report_unretrieved"
_PC_FILE = "digital_twin/unix_port_unretrieved_report.py"
_PC_MODULE = "unix_port_unretrieved_report"
_PC_HANDLER = "report_unretrieved"
_PC_INSTALL = "install"
_MICROTEST_FILE = "tests/microtest.py"
_MICROTEST_RUN = "run"
_ENTRY_DIRS = ("digital_twin", "tests")
_CLEARED_KEYS = frozenset({"exception", "future"})
# A display, a comprehension, a format or an operator allocates; a starred argument builds a tuple.
_ALLOCATING = (
    ast.JoinedStr, ast.FormattedValue, ast.BinOp, ast.List, ast.Tuple, ast.Dict, ast.Set, ast.ListComp, ast.SetComp,
    ast.DictComp, ast.GeneratorExp, ast.Starred, ast.Lambda, ast.Await, ast.Yield, ast.YieldFrom, ast.NamedExpr,
)
_OUTPUT_STATEMENTS = (ast.If, ast.Expr)


# ---------------------------------------------------------------------------
# (a) Who installs a handler
# ---------------------------------------------------------------------------


def _is_attr_call(node: ast.AST, attr: str) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == attr


def _is_unset_guard(test: ast.expr) -> bool:
    # `<loop>.get_exception_handler() is None`, nothing else.
    return (
        isinstance(test, ast.Compare)
        and _is_attr_call(test.left, "get_exception_handler")
        and len(test.ops) == 1
        and isinstance(test.ops[0], ast.Is)
        and isinstance(test.comparators[0], ast.Constant)
        and test.comparators[0].value is None
    )


def _install_sites(tree: ast.Module) -> list[tuple[int, str, bool]]:
    # (line, enclosing function, guarded) for each set_exception_handler() call; guarded means its statement sits
    # directly in the body of an `if <loop>.get_exception_handler() is None:`.
    sites: list[tuple[int, str, bool]] = []

    def visit(node: ast.AST, owner: str, *, guard: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                visit(child, child.name, guard=False)
                continue
            if isinstance(child, ast.If):
                visit(child.test, owner, guard=False)
                for stmt in child.body:
                    visit_stmt(stmt, owner, guard=_is_unset_guard(child.test))
                for stmt in child.orelse:
                    visit_stmt(stmt, owner, guard=False)
                continue
            if isinstance(child, ast.Call) and _is_attr_call(child, "set_exception_handler"):
                sites.append((child.lineno, owner, guard))
            visit(child, owner, guard=False)

    def visit_stmt(stmt: ast.stmt, owner: str, *, guard: bool) -> None:
        if isinstance(stmt, ast.Expr) and _is_attr_call(stmt.value, "set_exception_handler"):
            sites.append((stmt.lineno, owner, guard))
            visit(stmt.value, owner, guard=False)
            return
        visit(ast.Module(body=[stmt], type_ignores=[]), owner, guard=False)

    visit(tree, "<module>", guard=False)
    return sites


def install_site_findings(sources: dict[str, str]) -> list[str]:
    findings: list[str] = []
    guarded_in_installer = 0
    for label, text in sorted(sources.items()):
        for line, owner, guarded in _install_sites(ast.parse(text)):
            if label != _FIRMWARE_FILE or owner != _INSTALLER:
                findings.append(f"{label}:{line} calls set_exception_handler() in {owner}; only {_FIRMWARE_FILE}'s {_INSTALLER}() may")
            elif not guarded:
                findings.append(f"{label}:{line} installs a handler without `if <loop>.get_exception_handler() is None:` - it would replace the PC tiers' report")
            else:
                guarded_in_installer += 1
    if guarded_in_installer != 1:
        findings.append(f"{_FIRMWARE_FILE}'s {_INSTALLER}() installs the report {guarded_in_installer} time(s), expected exactly once")
    return findings


# ---------------------------------------------------------------------------
# (b) What a handler body may do
# ---------------------------------------------------------------------------


def _is_output_call(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id == "print"
    return isinstance(func, ast.Attribute) and func.attr == "print_exception" and isinstance(func.value, ast.Name) and func.value.id == "sys"


def _is_fixed_argument(node: ast.expr, context: str) -> bool:
    # A name, an attribute chain, a string constant or context["<key>"]: loads that allocate nothing.
    if isinstance(node, ast.Name):
        return True
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str)
    if isinstance(node, ast.Attribute):
        return _is_fixed_argument(node.value, context)
    return isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == context and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str)


def _clears(stmt: ast.stmt, context: str) -> str | None:
    # The key of a `context["<key>"] = None` statement, else None.
    if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.value, ast.Constant) and stmt.value.value is None):
        return None
    target = stmt.targets[0]
    if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name) and target.value.id == context and isinstance(target.slice, ast.Constant) and isinstance(target.slice.value, str):
        return target.slice.value
    return None


def _output_findings(label: str, statements: list[ast.stmt], context: str) -> list[str]:
    findings = [
        f"{label}:{stmt.lineno} {type(stmt).__name__} statement - the output block holds only `if` and the two output calls"
        for stmt in (n for top in statements for n in ast.walk(top) if isinstance(n, ast.stmt))
        if not isinstance(stmt, _OUTPUT_STATEMENTS)
    ]
    for node in (n for stmt in statements for n in ast.walk(stmt)):
        if isinstance(node, _ALLOCATING):
            findings.append(f"{label}:{node.lineno} {type(node).__name__} - allocates (a display, format, operator or starred argument)")
        elif isinstance(node, ast.Call):
            if not _is_output_call(node):
                findings.append(f"{label}:{node.lineno} calls {ast.unparse(node.func)}() - only print() and sys.print_exception() may run here, never a logger method")
            elif node.keywords:
                findings.append(f"{label}:{node.lineno} passes a keyword to {ast.unparse(node.func)}() - fixed positional arguments only")
            else:
                findings.extend(f"{label}:{node.lineno} argument {ast.unparse(arg)} is not a fixed load" for arg in node.args if not _is_fixed_argument(arg, context))
    return findings


def handler_body_findings(label: str, func: ast.FunctionDef) -> list[str]:
    # The one shape: try: [try: <output> finally: clear both keys] except Exception: pass. Clearing in the inner
    # finally runs whatever the output did; the outer except also holds a context the clearing cannot write to.
    if len(func.args.args) < 2:
        return [f"{label}:{func.lineno} {func.name}() does not take asyncio's (loop, context)"]
    context = func.args.args[-1].arg
    body = [s for s in func.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))]
    outer = body[0] if len(body) == 1 else None
    if not isinstance(outer, ast.Try) or outer.orelse or outer.finalbody or len(outer.handlers) != 1:
        return [f"{label}:{func.lineno} {func.name}() is not one `try: ... except Exception: pass` block"]
    handler = outer.handlers[0]
    findings: list[str] = []
    if not (isinstance(handler.type, ast.Name) and handler.type.id == "Exception" and handler.name is None and len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass)):
        findings.append(f"{label}:{handler.lineno} the outer handler is not `except Exception: pass` - something could escape into asyncio's loop")
    inner = outer.body[0] if len(outer.body) == 1 else None
    if not isinstance(inner, ast.Try) or inner.handlers or inner.orelse:
        return [*findings, f"{label}:{outer.lineno} the outer try does not hold exactly one `try: ... finally:` block"]
    cleared = [_clears(stmt, context) for stmt in inner.finalbody]
    if None in cleared or set(cleared) != _CLEARED_KEYS or len(cleared) != len(_CLEARED_KEYS):
        findings.append(f"{label}:{inner.lineno} the finally block must set exactly {context}[{sorted(_CLEARED_KEYS)}] to None, found {[ast.unparse(s) for s in inner.finalbody]}")
    return findings + _output_findings(label, inner.body, context)


def _function(tree: ast.Module, name: str, owner_class: str | None = None) -> ast.FunctionDef | None:
    scope: list[ast.stmt] = tree.body
    if owner_class is not None:
        classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == owner_class]
        if not classes:
            return None
        scope = classes[0].body
    found = [n for n in scope if isinstance(n, ast.FunctionDef) and n.name == name]
    return found[0] if found else None


# ---------------------------------------------------------------------------
# (c) Every PC entry point installs the PC report first
# ---------------------------------------------------------------------------


def _is_asyncio_run(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "run" and isinstance(node.func.value, ast.Name) and node.func.value.id == "asyncio"


def _driven_coroutines(tree: ast.Module) -> list[str]:
    # The names of the coroutine functions a module-level asyncio.run() drives, under `if __name__ ...` or bare.
    module_level = (top for top in tree.body if not isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)))
    return [
        node.args[0].func.id
        for top in module_level
        for node in ast.walk(top)
        if isinstance(node, ast.Call) and _is_asyncio_run(node) and node.args and isinstance(node.args[0], ast.Call) and isinstance(node.args[0].func, ast.Name)
    ]


def _install_names(tree: ast.Module) -> tuple[set[str], set[str]]:
    # (bare names bound to the PC module's install(), names bound to the PC module itself).
    bare: set[str] = set()
    modules: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == _PC_MODULE:
            bare.update(alias.asname or alias.name for alias in node.names if alias.name == _PC_INSTALL)
        elif isinstance(node, ast.Import):
            modules.update(alias.asname or alias.name for alias in node.names if alias.name == _PC_MODULE)
    return bare, modules


def _is_install_call(stmt: ast.stmt, bare: set[str], modules: set[str]) -> bool:
    if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call) and not stmt.value.args and not stmt.value.keywords):
        return False
    func = stmt.value.func
    if isinstance(func, ast.Name):
        return func.id in bare
    return isinstance(func, ast.Attribute) and func.attr == _PC_INSTALL and isinstance(func.value, ast.Name) and func.value.id in modules


def entry_findings(label: str, tree: ast.Module, entry: str) -> list[str]:
    funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == entry]
    if not funcs:
        return [f"{label}: the entry function {entry}() is not defined at module level"]
    body = [s for s in funcs[0].body if not isinstance(s, ast.Global) and not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
    bare, modules = _install_names(tree)
    if not body or not _is_install_call(body[0], bare, modules):
        return [f"{label}:{funcs[0].lineno} {entry}() does not open with the PC report's install() from {_PC_MODULE} - the firmware would then install its level-gated one"]
    return []


def _entry_points(root: Path) -> list[tuple[str, ast.Module, str]]:
    found: list[tuple[str, ast.Module, str]] = []
    for directory in _ENTRY_DIRS:
        for path in sorted((root / directory).glob("*.py")):
            label = path.relative_to(root).as_posix()
            tree = ast.parse(path.read_text(encoding="utf-8"))
            if label == _MICROTEST_FILE:
                found.append((label, tree, _MICROTEST_RUN))
            found.extend((label, tree, name) for name in _driven_coroutines(tree))
    return found


# ---------------------------------------------------------------------------
# The real tree
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def firmware_sources() -> dict[str, str]:
    sources = {f"src/{p.name}": p.read_text(encoding="utf-8") for p in sorted((REPO_ROOT / "src").glob("*.py"))}
    for device in DEVICE_NAMES:
        generated = generate_device(REPO_ROOT / "devices" / f"{device}.toml", REPO_ROOT / "src", REPO_ROOT / "ext")
        sources[f"build/generated_src/sensortask_{device}.py"] = generated.module_source
        sources[f"build/generated_src/{device}_boot.py"] = generated.boot_entry_source
    return sources


def test_only_start_and_check_tasks_installs_a_handler_and_only_where_none_is_set(firmware_sources: dict[str, str]) -> None:
    findings = install_site_findings(firmware_sources)
    assert not findings, "\n".join(findings)


@pytest.mark.parametrize(("path", "owner_class", "name"), [(_HANDLER_FILE, _HANDLER_CLASS, _FIRMWARE_HANDLER), (_PC_FILE, None, _PC_HANDLER)])
def test_each_handler_body_is_allocation_free_and_never_raises(path: str, owner_class: str | None, name: str) -> None:
    func = _function(ast.parse((REPO_ROOT / path).read_text(encoding="utf-8")), name, owner_class)
    assert func is not None, f"{path} defines no {name}()"
    findings = handler_body_findings(path, func)
    assert not findings, "\n".join(findings)


def test_every_pc_entry_point_installs_the_pc_report_before_the_firmware_starts() -> None:
    entries = _entry_points(REPO_ROOT)
    labels = {label for label, _tree, _entry in entries}
    # Discovery's own premise: the twin runner and the unit runner are found, or this checks nothing.
    assert {_MICROTEST_FILE, "digital_twin/run_generic_integration.py"} <= labels, sorted(labels)
    findings = [f for label, tree, entry in entries for f in entry_findings(label, tree, entry)]
    assert not findings, "\n".join(findings)


# ---------------------------------------------------------------------------
# Planted negatives: each rule fails on the shape it exists to stop
# ---------------------------------------------------------------------------

_GOOD_INSTALLER = (
    "async def start_and_check_tasks(self):\n"
    "    loop = asyncio.get_event_loop()\n"
    "    if loop.get_exception_handler() is None:\n"
    "        loop.set_exception_handler(self.pr.report_unretrieved)\n"
)


def test_a_clean_install_site_reports_nothing() -> None:
    assert install_site_findings({_FIRMWARE_FILE: _GOOD_INSTALLER}) == []


@pytest.mark.parametrize(
    ("sources", "needle"),
    [
        ({_FIRMWARE_FILE: _GOOD_INSTALLER, "src/other.py": "def f(loop):\n    loop.set_exception_handler(None)\n"}, "src/other.py:2"),
        ({_FIRMWARE_FILE: _GOOD_INSTALLER, "build/generated_src/sensortask_x.py": "loop.set_exception_handler(h)\n"}, "sensortask_x.py:1"),
        ({_FIRMWARE_FILE: _GOOD_INSTALLER.replace("start_and_check_tasks", "setup")}, "in setup"),
        ({_FIRMWARE_FILE: _GOOD_INSTALLER.replace("    if loop.get_exception_handler() is None:\n        ", "    ")}, "without `if"),
        ({_FIRMWARE_FILE: _GOOD_INSTALLER.replace("is None", "is not None")}, "without `if"),
        ({_FIRMWARE_FILE: _GOOD_INSTALLER.replace("is None:\n        loop.set", "is None:\n        pass\n    else:\n        loop.set")}, "without `if"),
        ({_FIRMWARE_FILE: "async def start_and_check_tasks(self):\n    pass\n"}, "0 time(s)"),
    ],
)
def test_a_planted_install_site_is_reported(sources: dict[str, str], needle: str) -> None:
    findings = install_site_findings(sources)
    assert any(needle in f for f in findings), findings


_GOOD_HANDLER = (
    "def report(self, _loop, context):\n"
    "    try:\n"
    "        try:\n"
    "            if self.pr.level >= LOG_ERR:\n"
    "                print(self.pr.name, context['message'])\n"
    "                sys.print_exception(context['exception'])\n"
    "        finally:\n"
    "            context['exception'] = None\n"
    "            context['future'] = None\n"
    "    except Exception:\n"
    "        pass\n"
)


def _body_findings(source: str) -> list[str]:
    func = ast.parse(source).body[0]
    assert isinstance(func, ast.FunctionDef)
    return handler_body_findings("planted.py", func)


def test_a_clean_handler_body_reports_nothing() -> None:
    assert _body_findings(_GOOD_HANDLER) == []


@pytest.mark.parametrize(
    ("old", "new", "needle"),
    [
        ("print(self.pr.name, context['message'])", "print(*context['message'])", "Starred"),
        ("print(self.pr.name, context['message'])", 'print(f"{self.pr.name}")', "JoinedStr"),
        ("print(self.pr.name, context['message'])", "print('%s' % self.pr.name)", "BinOp"),
        ("print(self.pr.name, context['message'])", "print(self.pr.name + context['message'])", "BinOp"),
        ("print(self.pr.name, context['message'])", "print([self.pr.name])", "List"),
        ("print(self.pr.name, context['message'])", "print((self.pr.name, 1))", "Tuple"),
        ("print(self.pr.name, context['message'])", "self.pr.err(context['message'])", "self.pr.err()"),
        ("print(self.pr.name, context['message'])", "print(self.pr.name, end='')", "keyword"),
        ("print(self.pr.name, context['message'])", "print(str(context['message']))", "str()"),
        ("print(self.pr.name, context['message'])", "print(context[self.pr.name])", "not a fixed load"),
        ("print(self.pr.name, context['message'])", "text = context['message']", "Assign statement"),
        ("            context['future'] = None\n", "", "must set exactly"),
        ("            context['future'] = None\n", "            context['future'] = 0\n", "must set exactly"),
        ("    except Exception:\n        pass\n", "    except ValueError:\n        pass\n", "not `except Exception: pass`"),
        ("    except Exception:\n        pass\n", "    except Exception:\n        raise\n", "not `except Exception: pass`"),
    ],
)
def test_a_planted_handler_body_is_reported(old: str, new: str, needle: str) -> None:
    source = _GOOD_HANDLER.replace(old, new)
    assert source != _GOOD_HANDLER
    findings = _body_findings(source)
    assert any(needle in f for f in findings), findings


def test_the_flat_form_whose_clearing_could_escape_is_reported() -> None:
    # try/except/finally at one level: a finally that cannot write to the context would raise into asyncio's loop.
    flat = (
        "def report(self, _loop, context):\n"
        "    try:\n"
        "        print(self.pr.name, context['message'])\n"
        "    except Exception:\n"
        "        pass\n"
        "    finally:\n"
        "        context['exception'] = None\n"
        "        context['future'] = None\n"
    )
    assert any("not one `try" in f for f in _body_findings(flat))


_GOOD_ENTRY = (
    "import asyncio\n"
    "from unix_port_unretrieved_report import install\n\n"
    "async def main():\n"
    "    global booted\n"
    "    install()\n"
    "    await boot()\n\n"
    "if __name__ == '__main__':\n"
    "    asyncio.run(main())\n"
)


def _planted_entries(tmp_path: Path, files: dict[str, str]) -> list[str]:
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text, encoding="utf-8")
    return [f for label, tree, entry in _entry_points(tmp_path) for f in entry_findings(label, tree, entry)]


def test_a_clean_entry_point_reports_nothing(tmp_path: Path) -> None:
    module_form = _GOOD_ENTRY.replace("from unix_port_unretrieved_report import install", "import unix_port_unretrieved_report").replace("    install()", "    unix_port_unretrieved_report.install()")
    microtest = "import unix_port_unretrieved_report\n\ndef run(namespace):\n    unix_port_unretrieved_report.install()\n"
    files = {"digital_twin/a.py": _GOOD_ENTRY, "digital_twin/b.py": module_form, "tests/microtest.py": microtest}
    assert _planted_entries(tmp_path, files) == []


@pytest.mark.parametrize(
    ("name", "text", "needle"),
    [
        ("digital_twin/a.py", _GOOD_ENTRY.replace("    install()\n", ""), "a.py:4 main()"),
        ("digital_twin/a.py", _GOOD_ENTRY.replace("    install()\n    await boot()\n", "    await boot()\n    install()\n"), "a.py:4 main()"),
        ("digital_twin/a.py", _GOOD_ENTRY.replace("from unix_port_unretrieved_report import install", "from elsewhere import install"), "a.py:4 main()"),
        ("tests/_probe.py", "import asyncio\n\nasync def _main():\n    pass\n\nasyncio.run(_main())\n", "_probe.py:3 _main()"),
        ("tests/microtest.py", "def run(namespace):\n    pass\n", "microtest.py:1 run()"),
        ("digital_twin/a.py", "import asyncio\n\nasyncio.run(main())\n", "main() is not defined"),
    ],
)
def test_a_planted_entry_point_is_reported(tmp_path: Path, name: str, text: str, needle: str) -> None:
    findings = _planted_entries(tmp_path, {name: text})
    assert any(needle in f for f in findings), findings


# ---------------------------------------------------------------------------
# (d) A device script running the real firmware's main() installs an always-printing report first: its host gate
# greps the board's output for memory markers, and the firmware's own report is silent at DebugLevel 0.
# ---------------------------------------------------------------------------

_DEVICE_SCRIPTS = "tests_hardware/device_scripts"
_FIRMWARE_MODULE_PREFIX = "sensortask_"


def _is_firmware_main_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "main"
        and isinstance(node.func.value, ast.Name) and node.func.value.id.startswith(_FIRMWARE_MODULE_PREFIX)
    )


def _installed_handler(stmt: ast.stmt) -> str | None:
    # The handler name of `asyncio.get_event_loop().set_exception_handler(<name>)`, else None.
    if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call) and _is_attr_call(stmt.value, "set_exception_handler")):
        return None
    call = stmt.value
    target = call.func.value if isinstance(call.func, ast.Attribute) else None
    if not (_is_attr_call(target, "get_event_loop") if target is not None else False) or len(call.args) != 1 or not isinstance(call.args[0], ast.Name):
        return None
    return call.args[0].id


def device_script_findings(label: str, tree: ast.Module) -> list[str]:
    findings: list[str] = []
    functions = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for func in functions.values():
        calls = [n for n in ast.walk(func) if _is_firmware_main_call(n)]
        if not calls:
            continue
        body = [s for s in func.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
        handler = _installed_handler(body[0]) if body else None
        if handler is None:
            findings.append(f"{label}:{func.lineno} {func.name}() runs the firmware's main() without first installing an always-printing report")
            continue
        report = functions.get(handler)
        if not isinstance(report, ast.FunctionDef):
            findings.append(f"{label}:{func.lineno} installs {handler}, which is no module-level function here")
            continue
        findings.extend(handler_body_findings(label, report))
        if any(isinstance(n, ast.If) for stmt in report.body for n in ast.walk(stmt)):
            findings.append(f"{label}:{report.lineno} {handler}() gates its output - the board-side report must print at every level")
    return findings


def test_every_device_script_running_the_firmware_installs_an_always_printing_report_first() -> None:
    scripts = sorted((REPO_ROOT / _DEVICE_SCRIPTS).glob("*.py"))
    trees = {p.relative_to(REPO_ROOT).as_posix(): ast.parse(p.read_text(encoding="utf-8")) for p in scripts}
    running = [label for label, tree in trees.items() if any(_is_firmware_main_call(n) for n in ast.walk(tree))]
    assert running, "no device script runs the firmware's main() - discovery has stopped seeing them"
    findings = [f for label in running for f in device_script_findings(label, trees[label])]
    assert not findings, "\n".join(findings)


_GOOD_SCRIPT = (
    "import asyncio\nimport sys\nimport sensortask_x\n\n\n"
    "def _report(_loop, context):\n"
    "    try:\n        try:\n            print('UNRETRIEVED TASK EXCEPTION:', context['message'])\n"
    "            sys.print_exception(context['exception'])\n"
    "        finally:\n            context['exception'] = None\n            context['future'] = None\n"
    "    except Exception:\n        pass\n\n\n"
    "async def _run():\n"
    "    asyncio.get_event_loop().set_exception_handler(_report)\n"
    "    task = asyncio.get_event_loop().create_task(sensortask_x.main())\n"
)


def test_a_clean_device_script_reports_nothing() -> None:
    assert device_script_findings("planted.py", ast.parse(_GOOD_SCRIPT)) == []


@pytest.mark.parametrize(
    ("old", "new", "needle"),
    [
        ("    asyncio.get_event_loop().set_exception_handler(_report)\n", "", "without first installing"),
        ("    asyncio.get_event_loop().set_exception_handler(_report)\n    task = asyncio.get_event_loop().create_task(sensortask_x.main())\n",
         "    task = asyncio.get_event_loop().create_task(sensortask_x.main())\n    asyncio.get_event_loop().set_exception_handler(_report)\n", "without first installing"),
        ("set_exception_handler(_report)", "set_exception_handler(_missing)", "no module-level function"),
        ("            print('UNRETRIEVED TASK EXCEPTION:', context['message'])\n", "            if LEVEL:\n                print('UNRETRIEVED TASK EXCEPTION:', context['message'])\n", "gates its output"),
        ("            print('UNRETRIEVED TASK EXCEPTION:', context['message'])\n", "            print(*context['message'])\n", "Starred"),
    ],
)
def test_a_planted_device_script_is_reported(old: str, new: str, needle: str) -> None:
    source = _GOOD_SCRIPT.replace(old, new)
    assert source != _GOOD_SCRIPT
    findings = device_script_findings("planted.py", ast.parse(source))
    assert any(needle in f for f in findings), findings


# ---------------------------------------------------------------------------
# (e) A console-tail memory gate also reads SYSTEM's task-end log: at DebugLevel 0 the board prints no unretrieved
# task exception, so a supervised task that died of an exhausted heap shows only as a new TASK_RAISED entry. A test
# that clears the error logs reads them first (CLAUDE.md: read the FRAM-backed logs before any ResetErrors).
# ---------------------------------------------------------------------------

_GATE_DIRS = ("tests_hardware/flash", "tests_hardware/bench")
_TAIL = "tail_log"
_MARKERS = "MEMORY_ERROR_MARKERS"
_TASK_END_CHECK = "assert_no_new_task_raised"
_LOG_READS = frozenset({"get_errcount", "read_live_system_log"})
_LOG_CLEAR = "reset_all_error_logs"


def _called_names(node: ast.AST) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            name = n.func.id if isinstance(n.func, ast.Name) else n.func.attr if isinstance(n.func, ast.Attribute) else None
            if name is not None:
                found.append((n.lineno, name))
    return sorted(found)


def gate_findings(label: str, tree: ast.Module) -> list[str]:
    # For a module holding a console-tail memory gate: every test that tails the log, itself or through a module-level
    # helper, checks the task-end log, and reads the error logs before its first clear.
    if not any(isinstance(n, ast.Name) and n.id == _MARKERS for n in ast.walk(tree)):
        return []
    helpers = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    tailing = {name for name, f in helpers.items() if any(c == _TAIL for _, c in _called_names(f))}
    reading = {name for name, f in helpers.items() if any(c in _LOG_READS for _, c in _called_names(f))}
    findings: list[str] = []
    for name, func in helpers.items():
        if not name.startswith("test_"):
            continue
        calls = _called_names(func)
        if not any(c == _TAIL or c in tailing for _, c in calls):
            continue
        if not any(c == _TASK_END_CHECK for _, c in calls):
            findings.append(f"{label}:{func.lineno} {name}() tails the console for memory markers but never calls {_TASK_END_CHECK}()")
        clears = [line for line, c in calls if c == _LOG_CLEAR]
        reads = [line for line, c in calls if c in _LOG_READS or c in reading]
        if clears and not (reads and reads[0] < clears[0]):
            findings.append(f"{label}:{clears[0]} {name}() clears the error logs before reading them")
    return findings


def test_every_console_tail_memory_gate_reads_the_task_end_log_and_reads_before_clearing() -> None:
    labels: list[str] = []
    findings: list[str] = []
    for directory in _GATE_DIRS:
        for path in sorted((REPO_ROOT / directory).glob("test_*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            if any(isinstance(n, ast.Name) and n.id == _MARKERS for n in ast.walk(tree)) and any(c == _TAIL for _, c in _called_names(tree)):
                labels.append(path.relative_to(REPO_ROOT).as_posix())
            findings.extend(gate_findings(path.relative_to(REPO_ROOT).as_posix(), tree))
    assert {"tests_hardware/flash/test_memory_stress.py", "tests_hardware/bench/test_memory_stress_bench.py"} <= set(labels), labels
    assert not findings, "\n".join(findings)


_GOOD_GATE = (
    "from harness import MEMORY_ERROR_MARKERS\n\n\n"
    "def _load(board):\n    return board.tail_log(duration_s=1)\n\n\n"
    "def _note(dut_ip):\n    print(dut_ip)\n\n\n"
    "def _read_first(dut_ip):\n    print(get_errcount(dut_ip))\n\n\n"
    "def test_soak(board, dut_ip):\n"
    "    before = get_errcount(dut_ip)\n"
    "    reset_all_error_logs(dut_ip)\n"
    "    lines = _load(board)\n"
    "    after = get_errcount(dut_ip)\n"
    "    assert not [ln for ln in lines if any(m in ln for m in MEMORY_ERROR_MARKERS)]\n"
    "    assert_no_new_task_raised({}, after, 'soak')\n"
)


def test_a_clean_gate_reports_nothing() -> None:
    assert gate_findings("planted.py", ast.parse(_GOOD_GATE)) == []
    through_a_helper = _GOOD_GATE.replace("    before = get_errcount(dut_ip)\n", "    _read_first(dut_ip)\n")
    assert gate_findings("planted.py", ast.parse(through_a_helper)) == []


@pytest.mark.parametrize(
    ("old", "new", "needle"),
    [
        ("    assert_no_new_task_raised({}, after, 'soak')\n", "", "never calls"),
        ("    before = get_errcount(dut_ip)\n", "", "before reading them"),
        # A read through a module-level helper counts; a helper that reads nothing does not.
        ("    before = get_errcount(dut_ip)\n", "    _note(dut_ip)\n", "before reading them"),
        ("    before = get_errcount(dut_ip)\n    reset_all_error_logs(dut_ip)\n", "    reset_all_error_logs(dut_ip)\n    before = get_errcount(dut_ip)\n", "before reading them"),
        # A direct tail_log() call is a gate too, not only one through a helper.
        ("    lines = _load(board)\n    after = get_errcount(dut_ip)\n    assert not [ln for ln in lines if any(m in ln for m in MEMORY_ERROR_MARKERS)]\n    assert_no_new_task_raised({}, after, 'soak')\n",
         "    lines = board.tail_log(duration_s=1)\n    assert not [ln for ln in lines if any(m in ln for m in MEMORY_ERROR_MARKERS)]\n", "never calls"),
    ],
)
def test_a_planted_gate_is_reported(old: str, new: str, needle: str) -> None:
    source = _GOOD_GATE.replace(old, new)
    assert source != _GOOD_GATE
    findings = gate_findings("planted.py", ast.parse(source))
    assert any(needle in f for f in findings), findings


# ---------------------------------------------------------------------------
# The task-end comparison itself
# ---------------------------------------------------------------------------


@pytest.fixture
def helpers(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(str(REPO_ROOT / "tests_hardware"))
    return load_script_module(REPO_ROOT / "tests_hardware" / "error_log_helpers.py", "error_log_helpers")


def _log(counter: int, *entries: tuple[str, int]) -> dict[str, object]:
    history = [{"num": 0, "type": "N"}] * (10 - len(entries)) + [{"num": n, "type": t} for t, n in entries]
    return {"SYSTEM": {"counter": counter, "history": history}}


@pytest.mark.parametrize(
    ("before", "after", "expected"),
    [
        (_log(0), _log(0), 0),
        (_log(0), _log(1, ("E", 42)), 1),
        (_log(1, ("E", 42)), _log(1, ("E", 42)), 0),  # an old entry, nothing new
        (_log(1, ("E", 42)), _log(2, ("E", 42)), 1),  # a repeat into the newest slot spends no slot but counts
        (_log(1, ("E", 42)), _log(2, ("E", 42), ("E", 43)), 0),  # a new cancelled end, the old raised one stays old
        (_log(5, ("E", 42)), _log(1, ("E", 42)), 1),  # cleared in between: what the log holds is new
        ({}, _log(2, ("E", 44), ("E", 42)), 1),
        (_log(0), _log(2, ("W", 42), ("E", 41)), 0),  # a warning with the same number is no task end
    ],
)
def test_new_task_raised_counts_only_the_entries_since_the_first_read(helpers: ModuleType, before: dict[str, object], after: dict[str, object], expected: int) -> None:
    assert helpers.new_task_raised(before, after) == expected
    if expected:
        with pytest.raises(AssertionError, match="TASK_RAISED"):
            helpers.assert_no_new_task_raised(before, after, "planted")
    else:
        helpers.assert_no_new_task_raised(before, after, "planted")
