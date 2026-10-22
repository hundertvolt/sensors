"""Every src/ sleep takes whole milliseconds (SPECIFICATION.md D.4): asyncio.sleep() an int literal or a module
`const(<int>)` name, every timeout wait_for_ms(), no float literal, float constant or true division in a sleep_ms() or
wait_for_ms() delay, a synchronous time.sleep*() only at Part N's `loop.sync_wait_max_us` named waits, each in place."""

import ast
import shutil
from dataclasses import dataclass
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
_MODULE_KINDS = {"asyncio": "asyncio", "uasyncio": "asyncio", "time": "time", "utime": "time"}
_SLEEPS = {"asyncio": frozenset({"sleep", "sleep_ms", "wait_for", "wait_for_ms"}), "time": frozenset({"sleep", "sleep_ms", "sleep_us"})}
# The named synchronous waits as (file, enclosing function, delay): the SPI chip-select settle and the I2C bus clear's
# 5 us half periods, at boot and in its awaited runtime twin, whose SCL waits yield (C.3).
_SYNC_WAITS = frozenset(
    {
        ("asy_i2c_driver.py", "_clear_bus", "_CLEAR_HALF_PERIOD_US"),
        ("asy_i2c_driver.py", "_clear_bus_awaiting", "_CLEAR_HALF_PERIOD_US"),
        ("asy_spi_driver.py", "session_begin", "_CS_SETTLE_US"),
        ("asy_spi_driver.py", "session_end", "_CS_SETTLE_US"),
    },
)


@dataclass(frozen=True)
class Sleep:
    file: str
    line: int
    function: str
    module: str  # "asyncio" or "time", whatever name the module was imported under
    name: str
    delay: ast.expr | None

    def key(self) -> tuple[str, str, str]:
        return self.file, self.function, ast.unparse(self.delay) if self.delay is not None else ""

    def where(self) -> str:
        return f"{self.file}:{self.line} {self.module}.{self.name}({self.key()[2]}) in {self.function}()"


def _aliases(tree: ast.Module) -> tuple[dict[str, str], dict[str, tuple[str, str]]]:
    # The names bound to the asyncio/time modules and to their functions, by every import form anywhere in the file.
    modules: dict[str, str] = {}
    functions: dict[str, tuple[str, str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update({a.asname or a.name: _MODULE_KINDS[a.name] for a in node.names if a.name in _MODULE_KINDS})
        elif isinstance(node, ast.ImportFrom) and node.module in _MODULE_KINDS:
            functions.update({a.asname or a.name: (_MODULE_KINDS[node.module], a.name) for a in node.names})
    return modules, functions


def _delay(call: ast.Call, name: str) -> ast.expr | None:
    # wait_for(aw, timeout) and wait_for_ms(aw, timeout) take the delay second, every sleep first.
    index = 1 if name.startswith("wait_for") else 0
    if len(call.args) > index:
        return call.args[index]
    return next((k.value for k in call.keywords if k.arg == "timeout" or (index == 0 and k.arg is not None)), None)


def _module(tmp_path: Path, source: str, name: str = "mod.py") -> Path:
    (tmp_path / name).write_text(source, encoding="utf-8")
    return tmp_path


def _module_values(tree: ast.Module) -> dict[str, tuple[bool, object]]:
    # Each module-level name bound to a literal: (whether it is const()-wrapped, the literal's value).
    values: dict[str, tuple[bool, object]] = {}
    for node in tree.body:
        target = node.targets[0] if isinstance(node, ast.Assign) and len(node.targets) == 1 else node.target if isinstance(node, ast.AnnAssign) else None
        value = node.value if isinstance(node, (ast.Assign, ast.AnnAssign)) else None
        if not isinstance(target, ast.Name) or value is None:
            continue
        wrapped = isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "const" and len(value.args) == 1
        literal = value.args[0] if isinstance(value, ast.Call) and wrapped else value
        if isinstance(literal, ast.Constant):
            values[target.id] = (wrapped, literal.value)
    return values


def _refusal(sleep: Sleep, values: dict[str, tuple[bool, object]]) -> str | None:
    delay = sleep.delay
    if sleep.module == "time":
        return None if sleep.key() in _SYNC_WAITS else "a synchronous wait outside the named ones"
    if sleep.name == "wait_for":
        return "every timeout goes through asyncio.wait_for_ms()"
    if sleep.name == "sleep":
        if isinstance(delay, ast.Constant) and type(delay.value) is int:
            return None
        named = values.get(delay.id) if isinstance(delay, ast.Name) else None
        return None if named is not None and named[0] and type(named[1]) is int else "asyncio.sleep() takes an int literal or a module const(<int>) name"
    nodes = list(ast.walk(delay)) if delay is not None else []
    floats = any(isinstance(n, ast.Constant) and type(n.value) is float for n in nodes)
    floats = floats or any(isinstance(n, ast.Name) and type(values.get(n.id, (False, None))[1]) is float for n in nodes)
    if delay is None or floats or any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div) for n in nodes):
        return "a millisecond delay holds no float literal or float constant and no true division"
    return None


def _sleeps_in(file: str, tree: ast.Module) -> list[Sleep]:
    modules, functions = _aliases(tree)
    found: list[Sleep] = []

    def visit(node: ast.AST, function: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.Call) and (target := _target(child.func, modules, functions)) is not None:
                found.append(Sleep(file, child.lineno, function, target[0], target[1], _delay(child, target[1])))
            visit(child, child.name if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) else function)

    visit(tree, "<module>")
    return found


def _src_copy(tmp_path: Path, name: str, old: str, new: str) -> Path:
    # src/ copied with one edit to one file, the edit's anchor once in it.
    for path in SRC.glob("*.py"):
        shutil.copy(path, tmp_path / path.name)
    text = (tmp_path / name).read_text(encoding="utf-8")
    assert text.count(old) == 1, f"the bite's anchor {old!r} must occur once in {name}"
    (tmp_path / name).write_text(text.replace(old, new), encoding="utf-8")
    return tmp_path


def _target(func: ast.expr, modules: dict[str, str], functions: dict[str, tuple[str, str]]) -> tuple[str, str] | None:
    # (module kind, function name) of a sleep or wait_for call, through any alias; None for every other call.
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id in modules:
        target: tuple[str, str] | None = (modules[func.value.id], func.attr)
    else:
        target = functions.get(func.id) if isinstance(func, ast.Name) else None
    return target if target is not None and target[1] in _SLEEPS[target[0]] else None


def named_wait_problems(src_dir: Path) -> list[str]:
    # A named wait that matches no call is a stale waiver; an asyncio-blind scan would pass everything.
    sleeps, _ = scan(src_dir)
    problems = [f"stale waiver: no {f}:{fn}() time.sleep*({d}) left" for f, fn, d in sorted(_SYNC_WAITS - {s.key() for s in sleeps if s.module == "time"})]
    return problems + ([] if any(s.module == "asyncio" for s in sleeps) else ["the scan found no asyncio sleep - it reads nothing"])


def scan(src_dir: Path) -> tuple[list[Sleep], list[str]]:
    # Every sleep and wait_for call in src_dir/*.py, and each one that breaks the form, with its reason.
    sleeps: list[Sleep] = []
    refused: list[str] = []
    for path in sorted(src_dir.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        values = _module_values(tree)
        found = _sleeps_in(path.name, tree)
        sleeps += found
        refused += [f"{s.where()}: {reason}" for s in found if (reason := _refusal(s, values)) is not None]
    return sleeps, refused


def test_every_src_sleep_takes_whole_milliseconds() -> None:
    _, refused = scan(SRC)
    assert not refused, f"{len(refused)} src/ sleep site(s) break the form:\n" + "\n".join(refused)


def test_every_named_synchronous_wait_is_still_in_place() -> None:
    assert named_wait_problems(SRC) == []


def test_a_removed_named_wait_is_a_stale_waiver(tmp_path: Path) -> None:
    src = _src_copy(tmp_path, "asy_spi_driver.py", "self._cs_pin.value(not self._cs_active_value)\n        time.sleep_us(_CS_SETTLE_US)\n", "self._cs_pin.value(not self._cs_active_value)\n")
    assert named_wait_problems(src) == ["stale waiver: no asy_spi_driver.py:session_end() time.sleep*(_CS_SETTLE_US) left"]


def test_an_asyncio_blind_scan_bites(tmp_path: Path) -> None:
    for path in SRC.glob("*.py"):  # every asyncio import renamed: the scan sees no asyncio module, so no asyncio sleep
        (tmp_path / path.name).write_text(path.read_text(encoding="utf-8").replace("import asyncio", "import aio_unread"), encoding="utf-8")
    assert "the scan found no asyncio sleep - it reads nothing" in named_wait_problems(tmp_path)


@pytest.mark.parametrize(
    ("name", "source"),
    [
        ("mod.py", "import asyncio\n\n\nasync def f():\n    await asyncio.sleep(0.05)\n"),
        ("mod.py", "import time\n\n\ndef f():\n    time.sleep_ms(1)\n"),
        ("mod.py", "import time as _t\n\n\ndef f():\n    _t.sleep_us(2)\n"),
        ("mod.py", "from utime import sleep\n\n\ndef f():\n    sleep(1)\n"),
        ("mod.py", "from asyncio import sleep as nap\n\n\nasync def f(t):\n    await nap(t)\n"),
        ("mod.py", "import asyncio\n\n\nasync def f(aw):\n    await asyncio.wait_for(aw, 5)\n"),
        ("mod.py", "import asyncio\n\n\nasync def f(t):\n    await asyncio.sleep_ms(t / 2)\n"),
        ("mod.py", "import asyncio\n\n\nasync def f(aw):\n    await asyncio.wait_for_ms(aw, 1.5 * 1000)\n"),
        ("mod.py", "import asyncio\n\n_F = 0.5\n\n\nasync def f():\n    await asyncio.sleep_ms(_F)\n"),
        ("mod.py", "import asyncio\nfrom micropython import const\n\n_HALF = const(0.5)\n\n\nasync def f():\n    await asyncio.sleep(_HALF)\n"),
        ("mod.py", "import asyncio\n\n_N = 2\n\n\nasync def f():\n    await asyncio.sleep(_N)\n"),
        ("asy_spi_driver.py", "import time\n\n\ndef session_begin():\n    time.sleep_us(3)\n"),
    ],
)
def test_a_refused_form_is_named(tmp_path: Path, name: str, source: str) -> None:
    sleeps, refused = scan(_module(tmp_path, source, name))
    assert len(sleeps) == 1, sleeps
    assert len(refused) == 1, refused
    assert refused[0].startswith(f"{name}:{sleeps[0].line} "), refused


@pytest.mark.parametrize(
    ("name", "source"),
    [
        ("mod.py", "import asyncio\n\n\nasync def f():\n    await asyncio.sleep(2)\n"),
        ("mod.py", "import asyncio\nfrom micropython import const\n\n_N = const(2)\n\n\nasync def f():\n    await asyncio.sleep(_N)\n"),
        ("mod.py", "import asyncio\n\n\nasync def f(t):\n    await asyncio.sleep_ms(t // 2)\n"),
        ("mod.py", "import asyncio\n\n\nasync def f(aw):\n    await asyncio.wait_for_ms(aw, 500)\n"),
        ("mod.py", "import asyncio\n\n\nclass C:\n    async def f(self):\n        await asyncio.sleep_ms(self._period_ms)\n"),
        ("asy_spi_driver.py", "import time\n\n\ndef session_begin():\n    time.sleep_us(_CS_SETTLE_US)\n"),
    ],
)
def test_an_accepted_form_passes(tmp_path: Path, name: str, source: str) -> None:
    sleeps, refused = scan(_module(tmp_path, source, name))
    assert len(sleeps) == 1, sleeps
    assert refused == []
