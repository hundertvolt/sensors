"""The machine-checkable code conventions (SPECIFICATION.md C.2, C.9, C.14.1, D.6, D.15) over src/ and every device's
generated modules: the asy_ module marker, _NAME equal to the measurement type, starter and task names, the errno=/wrnno=
keyword, no print() or assert, config file names from one helper, D.15 member order and quoting only TYPE_CHECKING names."""

import ast
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import TypeGuard

import pytest
from _devices import DEVICE_NAMES
from _repo_scan import REPO_ROOT

from buildgen.generate import generate_device

# A literal port keeps upstream's names, casing and order (SPECIFICATION.md C.2, D.15).
_LITERAL_PORT = "src/voc_algorithm.py"
_COLLECTOR_NAMES = {
    "get_task_starters": re.compile(r"start_asy_\w+"),
    "get_timer_starters": re.compile(r"start_timer|start_\w+_timer"),
    # Trigger starters arm a timer, so they take the timer starters' names (agent, 2026-10-07).
    "get_trigger_starters": re.compile(r"start_timer|start_\w+_timer"),
}
_TASK_COROUTINE = re.compile(r"_\w+_loop")
_NUMBER_NAME = re.compile(r"_?(?:ERR|WRN)_\w+")
_CONFIG_NAME_HOME = "src/asy_config_manager.py"  # config_filename() there builds every config file name
# The no-autostart boot entry's one module-level print(): its REPL start line (agent, 2026-09-28).
_START_LINE_ENTRY = "_main_noautostart.py"


@dataclass(frozen=True)
class Module:
    path: str
    tree: ast.Module

    @property
    def generated(self) -> bool:
        return not self.path.startswith("src/")


Rule = Callable[[Module], list[str]]


def _parse(path: str, source: str) -> Module:
    return Module(path, ast.parse(source, filename=path))


def _defs(body: list[ast.stmt]) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [node for node in body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]


def _is_type_checking(test: ast.expr) -> bool:
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING")


def asy_marker(module: Module) -> list[str]:
    # (1) a module with an async def in its public API carries asy_, and only such a module (so
    # math_helpers and voc_algorithm stay unprefixed); the generated sensortask_<device> keep L.2's name.
    name = Path(module.path).stem
    if module.generated and name.startswith("sensortask_"):
        return []
    public = [d for d in _defs(module.tree.body) if not d.name.startswith("_")]
    for cls in module.tree.body:
        if isinstance(cls, ast.ClassDef) and not cls.name.startswith("_"):
            public.extend(d for d in _defs(cls.body) if not d.name.startswith("_"))
    has_async = any(isinstance(d, ast.AsyncFunctionDef) for d in public)
    if has_async and not name.startswith("asy_"):
        return [f"{module.path}: an async def in its public API, but no asy_ prefix"]
    if name.startswith("asy_") and not has_async:
        return [f"{module.path}: asy_ prefix, but no async def in its public API"]
    return []


def _namedtuple_types(module: Module) -> dict[str, str]:
    types = {}
    for node in ast.walk(module.tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            value = node.value
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "namedtuple" and value.args and isinstance(value.args[0], ast.Constant):
                types[node.targets[0].id] = str(value.args[0].value)
    return types


def measurement_name(module: Module) -> list[str]:
    # (2) _NAME = const("<X>") and the namedtuple passed as the measurement type are both <X>.
    name = next((
        node.value.args[0].value for node in module.tree.body
        if isinstance(node, ast.Assign) and [ast.unparse(t) for t in node.targets] == ["_NAME"]
        and isinstance(node.value, ast.Call) and ast.unparse(node.value.func) == "const" and isinstance(node.value.args[0], ast.Constant)
    ), None)
    types = _namedtuple_types(module)
    found = []
    for node in ast.walk(module.tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr == "__init__" and ast.unparse(node.func.value) == "super()":
            data = node.args[0] if node.args else next((k.value for k in node.keywords if k.arg == "init_data"), None)
        elif node.func.attr == "_set_meas_data" and node.args:
            data = node.args[0]
        else:
            continue
        if isinstance(data, ast.Call) and isinstance(data.func, ast.Name) and data.func.id in types and types[data.func.id] != name:
            found.append(f"{module.path}:{node.lineno}: measurement type {types[data.func.id]!r}, _NAME {name!r}")
    return found


def _collected_methods(cls: ast.ClassDef, collector: ast.FunctionDef | ast.AsyncFunctionDef) -> Iterator[str]:
    methods = {d.name for d in _defs(cls.body)}
    for node in ast.walk(collector):
        if isinstance(node, ast.List):
            for item in node.elts:
                if isinstance(item, ast.Attribute) and ast.unparse(item.value) == "self" and item.attr in methods:
                    yield item.attr


def starter_names(module: Module) -> list[str]:
    # (3) task starters are start_asy_*, timer starters start_timer/start_*_timer, and the coroutine
    # a task starter hands create_task() is _*_loop (SPECIFICATION.md C.9).
    found = []
    for cls in (node for node in ast.walk(module.tree) if isinstance(node, ast.ClassDef)):
        methods = {d.name: d for d in _defs(cls.body)}
        for collector, pattern in _COLLECTOR_NAMES.items():
            if collector not in methods:
                continue
            for starter in _collected_methods(cls, methods[collector]):
                if not pattern.fullmatch(starter):
                    found.append(f"{module.path}: {cls.name}.{collector}() returns {starter}")
                if collector != "get_task_starters":
                    continue
                for call in ast.walk(methods[starter]):
                    if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr == "create_task" and call.args:
                        coro = call.args[0]
                        coro_name = coro.func.attr if isinstance(coro, ast.Call) and isinstance(coro.func, ast.Attribute) else ast.unparse(coro)
                        if not _TASK_COROUTINE.fullmatch(coro_name):
                            found.append(f"{module.path}:{call.lineno}: {cls.name}.{starter}() starts {coro_name}, not a _*_loop coroutine")
    return found


def log_keywords(module: Module) -> list[str]:
    # (4) err_s()/wrn_s() take their number as errno=/wrnno=, never positionally.
    found = []
    for node in ast.walk(module.tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"err_s", "wrn_s"}:
            keyword = "errno" if node.func.attr == "err_s" else "wrnno"
            numbers = [a for a in node.args if (isinstance(a, ast.Constant) and type(a.value) is int) or _NUMBER_NAME.fullmatch(ast.unparse(a).rsplit(".", 1)[-1])]
            if keyword not in {k.arg for k in node.keywords} or numbers:
                found.append(f"{module.path}:{node.lineno}: {node.func.attr}() needs its number as {keyword}=")
    return found


def _is_print(node: ast.AST) -> TypeGuard[ast.Call]:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print"


def no_print(module: Module) -> list[str]:
    # (5) print() only inside the logger, and the no-autostart boot entry's first module-level start line.
    if module.path == "src/asy_print_log.py":
        return []
    calls = [n for n in ast.walk(module.tree) if _is_print(n)]
    if module.generated and module.path.endswith(_START_LINE_ENTRY):
        start_line = next((s.value for s in module.tree.body if isinstance(s, ast.Expr) and _is_print(s.value)), None)
        calls = [n for n in calls if n is not start_line]
    return [f"{module.path}:{n.lineno}: print()" for n in calls]


def _names_a_config_file(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str) and "config_" in node.value


def config_file_names(module: Module) -> list[str]:
    # (9) a "config_" literal is never concatenated (+, %, an f-string, .format()) in src/ outside the one
    # builder, asy_config_manager.config_filename() (SPECIFICATION.md C.14.1).
    if module.generated or module.path == _CONFIG_NAME_HOME:
        return []
    found = []
    for node in ast.walk(module.tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
            parts = [node.left, node.right]
        elif isinstance(node, ast.JoinedStr):
            parts = list(node.values)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format":
            parts = [node.func.value]
        else:
            continue
        if any(_names_a_config_file(part) for part in parts):
            found.append(f"{module.path}:{node.lineno}: a config file name built by hand, not by config_filename()")
    return found


# A src assert whose removal a later unit's change owns, keyed by file and enclosing function; an
# entry whose assert has gone fails (test_every_pending_assert_is_still_there).
_PENDING_ASSERTS: "dict[tuple[str, str], str]" = {}


def _asserts_by_function(module: Module) -> list[tuple[str, ast.Assert]]:
    return [
        (f.name, n) for f in ast.walk(module.tree) if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))
        for n in ast.walk(f) if isinstance(n, ast.Assert)
    ]


def no_assert(module: Module) -> list[str]:
    # (6) no assert in shipped code.
    pending = {func for (path, func) in _PENDING_ASSERTS if path == module.path}
    in_pending = {id(n) for func, n in _asserts_by_function(module) if func in pending}
    return [
        f"{module.path}:{n.lineno}: assert" for n in ast.walk(module.tree)
        if isinstance(n, ast.Assert) and id(n) not in in_pending
    ]


def _starter_role(cls: ast.ClassDef) -> set[str]:
    # D.15's Starter role: the get_*_starters() collections, what they return, and each stop_* pairing a start_*.
    methods = {d.name: d for d in _defs(cls.body)}
    starters = {name for name in methods if re.fullmatch(r"get_\w+_starters", name)}
    for collector in list(starters):
        starters.update(_collected_methods(cls, methods[collector]))
    started = {name.lstrip("_") for name in starters}
    return starters | {name for name in methods if name.lstrip("_").startswith("stop_") and "start_" + name.lstrip("_")[5:] in started}


def d15_key(name: str, starters: set[str]) -> tuple[int, int, int, str]:
    if name.startswith("__") and name.endswith("__"):
        return (0, 0 if name == "__init__" else 1, 0, name)
    base = name.lstrip("_")
    role = 0 if name in starters else 1 if base.startswith(("get_", "is_")) else 2 if base.startswith("set_") else 3
    return (1, 0 if name.startswith("_") else 1, role, base)


def _import_time_names(module: Module) -> set[str]:
    # A definition an import-time statement needs (a decorator, a default, a module or class-body
    # statement) is D.15's one allowed exception, so these functions are left out of the order.
    roots: list[ast.AST] = []
    for node in module.tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            roots.extend([*node.decorator_list, *node.args.defaults, *(d for d in node.args.kw_defaults if d is not None)])
        elif isinstance(node, ast.ClassDef):
            roots.extend([*node.decorator_list, *node.bases, *(s for s in node.body if not isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)))])
        else:
            roots.append(node)
    return {n.id for root in roots for n in ast.walk(root) if isinstance(n, ast.Name)}


def _out_of_order(where: str, names: list[str], starters: set[str]) -> list[str]:
    expected = sorted(names, key=lambda name: d15_key(name, starters))
    if names == expected:
        return []
    first = next(i for i, (got, want) in enumerate(zip(names, expected, strict=True)) if got != want)
    return [f"{where}: {names[first]} sits where D.15 puts {expected[first]}"]


def member_order(module: Module) -> list[str]:
    # (7) D.15 order in every src/ class and the module-level function list.
    if module.generated or module.path == _LITERAL_PORT:
        return []
    found = []
    for cls in (node for node in ast.walk(module.tree) if isinstance(node, ast.ClassDef)):
        found.extend(_out_of_order(f"{module.path} class {cls.name}", [d.name for d in _defs(cls.body)], _starter_role(cls)))
    needed = _import_time_names(module)
    functions = [d.name for d in _defs(module.tree.body) if d.name not in needed]
    found.extend(_out_of_order(f"{module.path} module functions", functions, set()))
    return found


def _type_checking_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.If) and _is_type_checking(node.test):
            for stmt in node.body:
                if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                    names.update((a.asname or a.name).split(".")[0] for a in stmt.names)
                elif isinstance(stmt, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    names.add(stmt.name)
                elif isinstance(stmt, ast.Assign):
                    names.update(t.id for t in stmt.targets if isinstance(t, ast.Name))
                elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    names.add(stmt.target.id)
    return names


def _annotations(tree: ast.Module) -> Iterator[ast.expr]:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            yield from (a.annotation for a in [*args.posonlyargs, *args.args, *args.kwonlyargs, args.vararg, args.kwarg] if a is not None and a.annotation is not None)
            if node.returns is not None:
                yield node.returns
        elif isinstance(node, ast.AnnAssign):
            yield node.annotation


def quoted_annotations(module: Module, project: dict[str, set[str]]) -> list[str]:
    # (8) an annotation is quoted only when it names a TYPE_CHECKING symbol - its own module's, or
    # through `<alias>.<name>` another project module's - or a class bound later than it (D.6).
    own = _type_checking_names(module.tree)
    aliases = {a.asname or a.name: a.name for n in module.tree.body if isinstance(n, ast.Import) for a in n.names}
    classes = {n.name: n.end_lineno or n.lineno for n in module.tree.body if isinstance(n, ast.ClassDef)}
    found = []
    for ann in _annotations(module.tree):
        if not (isinstance(ann, ast.Constant) and isinstance(ann.value, str)):
            continue
        expr = ast.parse(ann.value, mode="eval")
        names = {n.id for n in ast.walk(expr) if isinstance(n, ast.Name)}
        through = {a.attr for a in ast.walk(expr) if isinstance(a, ast.Attribute) and isinstance(a.value, ast.Name) and a.attr in project.get(aliases.get(a.value.id, ""), set())}
        later = {n for n in names if classes.get(n, 0) >= ann.lineno}
        if not (names & own or through or later):
            found.append(f"{module.path}:{ann.lineno}: quoted annotation {ann.value!r} names no TYPE_CHECKING symbol")
    return found


def _tc_table(modules: list[Module]) -> dict[str, set[str]]:
    return {Path(m.path).stem: _type_checking_names(m.tree) for m in modules}


RULES: dict[str, Rule] = {
    "asy_marker": asy_marker,
    "measurement_name": measurement_name,
    "starter_names": starter_names,
    "log_keywords": log_keywords,
    "no_print": no_print,
    "no_assert": no_assert,
    "config_file_names": config_file_names,
    "member_order": member_order,
}


@pytest.fixture(scope="module")
def modules(tmp_path_factory: pytest.TempPathFactory) -> list[Module]:
    out = tmp_path_factory.mktemp("generated_src")
    found = [_parse(f"src/{p.name}", p.read_text(encoding="utf-8")) for p in sorted((REPO_ROOT / "src").glob("*.py"))]
    for device in DEVICE_NAMES:
        generated = generate_device(REPO_ROOT / "devices" / f"{device}.toml", REPO_ROOT / "src", REPO_ROOT / "ext")
        sources = ((f"sensortask_{device}", generated.module_source), (f"sensortask_{device}_main", generated.boot_entry_source), (f"sensortask_{device}_main_noautostart", generated.boot_entry_noautostart_source))
        for name, source in sources:
            (out / f"{name}.py").write_text(source, encoding="utf-8")
            found.append(_parse(f"build/generated_src/{name}.py", (out / f"{name}.py").read_text(encoding="utf-8")))
    return found


@pytest.mark.parametrize("rule", sorted(RULES))
def test_the_tree_follows_each_convention(modules: list[Module], rule: str) -> None:
    found = [line for module in modules for line in RULES[rule](module)]
    assert not found, f"{rule}:\n" + "\n".join(f"  {line}" for line in found)


def test_quoted_annotations_name_a_type_checking_symbol(modules: list[Module]) -> None:
    table = _tc_table(modules)
    found = [line for module in modules for line in quoted_annotations(module, table)]
    assert not found, "\n".join(found)


def test_every_pending_assert_is_still_there(modules: list[Module]) -> None:
    by_path = {m.path: m for m in modules}
    gone = [key for key in _PENDING_ASSERTS if key[1] not in {func for func, _n in _asserts_by_function(by_path[key[0]])}]
    assert not gone, f"pending asserts no longer present - delete them from _PENDING_ASSERTS: {gone}"


def test_the_scan_sees_every_device_module(modules: list[Module]) -> None:
    assert {m.path for m in modules if m.generated} == {f"build/generated_src/{n}.py" for d in DEVICE_NAMES for n in (f"sensortask_{d}", f"sensortask_{d}_main", f"sensortask_{d}_main_noautostart")}


_NEGATIVE = {
    "asy_marker": ("src/helpers.py", "class Helper:\n    async def run(self):\n        pass\n", "src/helpers.py: an async def"),
    "measurement_name": (
        "src/asy_x_driver.py",
        "_NAME = const('XCHIP')\nX = namedtuple('X', ('TS',))\nclass X_Reader(SensorReader):\n    def __init__(self):\n        super().__init__(X(None), _NAME)\n",
        "src/asy_x_driver.py:5: measurement type 'X'",
    ),
    "starter_names": (
        "src/asy_x.py",
        "class Svc:\n    def get_task_starters(self):\n        return [self.start_asy_poll]\n    def start_asy_poll(self):\n        return loop.create_task(self.poll())\n    async def poll(self):\n        pass\n",
        "src/asy_x.py:5: Svc.start_asy_poll() starts poll",
    ),
    "log_keywords": ("src/asy_x.py", "async def f(pr):\n    await pr.err_s('bad', _ERR_BAD)\n", "src/asy_x.py:2: err_s() needs its number as errno="),
    "no_print": ("src/asy_x.py", "async def f():\n    print('x')\n", "src/asy_x.py:2: print()"),
    "no_assert": ("build/generated_src/sensortask_x.py", "def f(a):\n    assert a is not None\n    assert a > 0\n", "build/generated_src/sensortask_x.py:2: assert"),
    "member_order": ("src/asy_x.py", "class C:\n    async def setup(self):\n        pass\n    def reset(self):\n        pass\n", "src/asy_x.py class C: setup sits where D.15 puts reset"),
    "config_file_names": ("src/asy_x.py", "def f(p, n):\n    return p + 'config_' + n + '.cfg'\n", "src/asy_x.py:2: a config file name built by hand"),
}


@pytest.mark.parametrize("rule", sorted(_NEGATIVE))
def test_a_planted_violation_fails_its_rule(tmp_path: Path, rule: str) -> None:
    path, source, expected = _NEGATIVE[rule]
    copy = tmp_path / Path(path).name
    copy.write_text(source, encoding="utf-8")
    found = RULES[rule](_parse(path, copy.read_text(encoding="utf-8")))
    assert any(line.startswith(expected) for line in found), found


def test_the_no_autostart_entry_prints_its_start_line_and_nothing_else() -> None:
    # The named exception covers one module-level print() in that one generated file, never a second or a nested one.
    source = 'import sys\nprint("start line")\nprint("second")\ndef f():\n    print("nested")\n'
    assert no_print(_parse("build/generated_src/sensortask_x_main_noautostart.py", source)) == [
        "build/generated_src/sensortask_x_main_noautostart.py:3: print()",
        "build/generated_src/sensortask_x_main_noautostart.py:5: print()",
    ]
    assert len(no_print(_parse("build/generated_src/sensortask_x_main.py", source))) == 3


def test_a_planted_quoted_annotation_fails(tmp_path: Path) -> None:
    copy = tmp_path / "asy_x.py"
    copy.write_text("from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from typing import Any\ndef f(a: 'int', b: 'Any', c: 'Later') -> 'int | None':\n    pass\nclass Later:\n    pass\n", encoding="utf-8")
    module = _parse("src/asy_x.py", copy.read_text(encoding="utf-8"))
    assert quoted_annotations(module, {}) == [
        "src/asy_x.py:4: quoted annotation 'int' names no TYPE_CHECKING symbol",
        "src/asy_x.py:4: quoted annotation 'int | None' names no TYPE_CHECKING symbol",
    ]


def test_d15_orders_dunders_private_public_then_role_then_name() -> None:
    names = ["start_asy_read", "_read_loop", "get_task_starters", "stop_timer", "start_timer", "setup", "reset", "set_level", "get_level", "is_ready", "_get_x", "__repr__", "__init__"]
    starters = {"get_task_starters", "start_asy_read", "start_timer", "stop_timer"}
    assert sorted(names, key=lambda n: d15_key(n, starters)) == [
        "__init__", "__repr__", "_get_x", "_read_loop",
        "get_task_starters", "start_asy_read", "start_timer", "stop_timer", "get_level", "is_ready", "set_level", "reset", "setup",
    ]


def test_an_import_time_definition_is_left_out_of_the_order() -> None:
    module = _parse("src/asy_x.py", "def _make():\n    return 1\nX = _make()\ndef b():\n    pass\ndef _a():\n    pass\n")
    assert member_order(module) == ["src/asy_x.py module functions: b sits where D.15 puts _a"]
    module = _parse("src/asy_x.py", "def b():\n    pass\nX = b()\ndef _a():\n    pass\n")
    assert member_order(module) == []
