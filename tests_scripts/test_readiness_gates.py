"""A readiness flag exists exactly where product code reads it (SPECIFICATION.md C.13): a class assigning
`self.initialized` sets it False in `__init__` and True in `setup()`, or inherits both, and src/ reads it;
a teardown method on a class with no logger of its own answers `bool`. Its MicroPython half: tests/."""

import ast
import re
import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
_FLAG = "initialized"
# The classes product code never gates on carry no flag (SensorReader with every subclass).
_CARRY_NONE = ("SystemService", "SensorReader", "WebserverService", "NeopixelDriver", "NotificationService")
_TEARDOWN_RE = re.compile(r"^(?:deinit|close|disconnect|stop_\w+|cleanup)$")
_CHIP_CLASS_RE = re.compile(r"^\w+_I2C$")  # a stop_* there is a chip command, not a teardown
_MIRRORS = frozenset({("_TimeoutStreamProxy", "close")})  # the asyncio stream's own close(), mirrored
# Teardowns that answer None until their rework lands; an entry that answers bool fails. Empty: the list only shrinks.
_PENDING_TEARDOWNS: dict[tuple[str, str], str] = {}

Method = ast.FunctionDef | ast.AsyncFunctionDef


class Classes:
    def __init__(self, src: Path) -> None:
        self.nodes: dict[str, ast.ClassDef] = {}
        self.file: dict[str, str] = {}
        self.trees: dict[str, ast.Module] = {}
        for path in sorted(src.glob("*.py")):
            self.trees[path.name] = ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
            for node in self.trees[path.name].body:
                if isinstance(node, ast.ClassDef):
                    self.nodes[node.name] = node
                    self.file[node.name] = path.name

    def bases(self, name: str) -> list[str]:
        return [b.id for b in self.nodes[name].bases if isinstance(b, ast.Name) and b.id in self.nodes]

    def mro(self, name: str) -> list[str]:
        out, todo = [], [name]
        while todo:
            current = todo.pop(0)
            if current not in out:
                out.append(current)
                todo.extend(self.bases(current))
        return out

    def subclasses(self, name: str) -> list[str]:
        return [c for c in self.nodes if name in self.mro(c)]

    def method(self, cls: str, name: str) -> Method | None:
        return next((f for f in self.nodes[cls].body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and f.name == name), None)


def _self_flag(node: ast.AST, ctx: type[ast.expr_context]) -> list[ast.Attribute]:
    return [n for n in ast.walk(node) if isinstance(n, ast.Attribute) and n.attr == _FLAG and isinstance(n.ctx, ctx) and isinstance(n.value, ast.Name) and n.value.id == "self"]


def _sets(fn: Method | None, *, value: bool) -> bool:
    return fn is not None and any(
        isinstance(s, ast.Assign) and any(t in _self_flag(s, ast.Store) for t in s.targets) and isinstance(s.value, ast.Constant) and s.value.value is value
        for s in ast.walk(fn)
    )


def _awaits_super(fn: Method, name: str) -> bool:
    return any(
        isinstance(n, ast.Await) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == name
        and isinstance(n.value.func.value, ast.Call) and isinstance(n.value.func.value.func, ast.Name) and n.value.func.value.func.id == "super"
        for n in ast.walk(fn)
    )


def _calls_super_init(fn: Method) -> bool:
    return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "__init__" and isinstance(n.func.value, ast.Call)
               and isinstance(n.func.value.func, ast.Name) and n.func.value.func.id == "super" for n in ast.walk(fn))


def _initial_false(classes: Classes, cls: str) -> bool:
    init = classes.method(cls, "__init__")
    if _sets(init, value=False):
        return True
    inherits = init is None or _calls_super_init(init)
    return inherits and any(_initial_false(classes, base) for base in classes.bases(cls))


def _set_true_by_setup(classes: Classes, cls: str) -> bool:
    setup = classes.method(cls, "setup")
    if _sets(setup, value=True):
        return True
    inherits = setup is None or _awaits_super(setup, "setup")
    return inherits and any(_set_true_by_setup(classes, base) for base in classes.bases(cls))


def flag_findings(classes: Classes) -> list[str]:
    findings: list[str] = []
    stray = [f"{file}:{n.lineno} `{ast.unparse(n)}`" for file, tree in classes.trees.items() for n in ast.walk(tree)
             if isinstance(n, ast.Attribute) and n.attr == _FLAG and not (isinstance(n.value, ast.Name) and n.value.id == "self")]
    findings += [f"{site}: a readiness flag read through another object - this check cannot name its class" for site in stray]
    flagged = [cls for cls, node in classes.nodes.items() if _self_flag(node, ast.Store)]
    for cls in flagged:
        where = f"{classes.file[cls]} {cls}"
        if not _initial_false(classes, cls):
            findings.append(f"{where}: sets self.{_FLAG} but not False in __init__ (nor inherits it from a base's)")
        if not _set_true_by_setup(classes, cls):
            findings.append(f"{where}: sets self.{_FLAG} but not True in setup() (nor through an awaited super().setup())")
        if not any(_self_flag(classes.nodes[owner], ast.Load) for owner in classes.mro(cls)):
            findings.append(f"{where}: self.{_FLAG} is never read in src/ - a flag only a test reads is not product state")
    for name in _CARRY_NONE:
        findings += [f"{classes.file[cls]} {cls}: carries self.{_FLAG}, but product code never gates on this class" for cls in classes.subclasses(name) if cls in flagged]
    init = classes.method("ConfigManager", "__init__") if "ConfigManager" in classes.nodes else None
    if init is None or "ConfigManager" in flagged or "self.valid = False" not in (ast.unparse(s) for s in ast.walk(init)):
        findings.append("ConfigManager: gates on its own `valid` (False in __init__), never on a readiness flag")
    return findings


def teardown_findings(classes: Classes) -> list[str]:
    findings: list[str] = []
    seen: set[tuple[str, str]] = set()
    for cls, node in classes.nodes.items():
        has_logger = any(isinstance(n, ast.Attribute) and n.attr == "pr" and isinstance(n.ctx, ast.Store) for owner in classes.mro(cls) for n in ast.walk(classes.nodes[owner]))
        for fn in (f for f in node.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and _TEARDOWN_RE.match(f.name)):
            if has_logger or (cls, fn.name) in _MIRRORS or (fn.name.startswith("stop_") and _CHIP_CLASS_RE.match(cls)):
                continue
            answer = ast.unparse(fn.returns).strip("'\"") if fn.returns is not None else "<none>"
            if (cls, fn.name) in _PENDING_TEARDOWNS:
                seen.add((cls, fn.name))
                if answer == "bool":
                    findings.append(f"{classes.file[cls]}:{fn.lineno} {cls}.{fn.name}() answers bool now: drop it from the pending teardowns")
            elif answer != "bool":
                findings.append(f"{classes.file[cls]}:{fn.lineno} {cls}.{fn.name}() -> {answer}: a teardown on a class with no logger answers bool")
    findings += [f"pending teardown {cls}.{name}() ({unit}) exists nowhere in src/: drop it" for (cls, name), unit in _PENDING_TEARDOWNS.items() if (cls, name) not in seen]
    return findings


def all_findings(src: Path) -> list[str]:
    classes = Classes(src)
    return flag_findings(classes) + teardown_findings(classes)


@pytest.fixture
def src_copy(tmp_path: Path) -> Path:
    return Path(shutil.copytree(SRC, tmp_path / "src"))


def _edit(src: Path, name: str, old: str, new: str) -> None:
    path = src / name
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, f"{name}: the anchor is not unique: {old!r}"
    path.write_text(text.replace(old, new), encoding="utf-8")


def test_every_readiness_flag_is_set_up_and_read_and_every_teardown_answers_bool() -> None:
    assert all_findings(SRC) == []


def test_the_flagged_classes_are_the_fram_spi_uart_and_logging_ones() -> None:
    classes = Classes(SRC)
    flagged = {cls for cls, node in classes.nodes.items() if _self_flag(node, ast.Store)}
    assert {"FRAM_SPI", "SPIDevice", "UARTComm", "PrintLogHistory", "PrintLogHistoryStore"} <= flagged, flagged
    assert not flagged & {c for name in _CARRY_NONE for c in classes.subclasses(name)}, flagged


def test_an_unread_flag_on_a_class_that_carries_none_fails(src_copy: Path) -> None:
    _edit(src_copy, "asy_neopixel_driver.py", "        self._overlay_bri = led_overl_bri\n", "        self._overlay_bri = led_overl_bri\n        self.initialized = False\n")
    _edit(src_copy, "asy_neopixel_driver.py", "        await self.pr.setup()\n", "        self.initialized = True\n        await self.pr.setup()\n")
    assert all_findings(src_copy) == [
        "asy_neopixel_driver.py NeopixelDriver: self.initialized is never read in src/ - a flag only a test reads is not product state",
        "asy_neopixel_driver.py NeopixelDriver: carries self.initialized, but product code never gates on this class",
    ]


def test_a_flag_never_false_in_init_fails(src_copy: Path) -> None:
    _edit(src_copy, "asy_spi_driver.py", "        self.initialized = False  # _cs_pin isn't configured as an output until setup() runs\n", "")
    assert all_findings(src_copy) == ["asy_spi_driver.py SPIDevice: sets self.initialized but not False in __init__ (nor inherits it from a base's)"]


def test_a_flag_never_true_in_setup_fails(src_copy: Path) -> None:
    _edit(src_copy, "asy_uart_comm.py", '        self.initialized = True\n        self.pr.one("UART link ready as", self._role)\n', '        self.pr.one("UART link ready as", self._role)\n')
    assert all_findings(src_copy) == ["asy_uart_comm.py UARTComm: sets self.initialized but not True in setup() (nor through an awaited super().setup())"]


def test_a_teardown_not_answering_bool_fails(src_copy: Path) -> None:
    _edit(src_copy, "asy_uart_driver.py", "    def deinit(self) -> bool:", "    def deinit(self) -> None:")
    findings = all_findings(src_copy)
    assert len(findings) == 1 and findings[0].startswith("asy_uart_driver.py:") and "UART.deinit() -> None: a teardown on a class with no logger answers bool" in findings[0], findings


def test_a_pending_teardown_that_answers_bool_must_leave_the_list(src_copy: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(_PENDING_TEARDOWNS, ("I2C", "deinit"), "a later unit")
    findings = all_findings(src_copy)
    assert len(findings) == 1 and "I2C.deinit() answers bool now: drop it from the pending teardowns" in findings[0], findings


def test_config_manager_gating_on_anything_but_valid_fails(src_copy: Path) -> None:
    _edit(src_copy, "asy_config_manager.py", "        self.valid = False\n", "        self.initialized = False\n")
    findings = all_findings(src_copy)
    assert "ConfigManager: gates on its own `valid` (False in __init__), never on a readiness flag" in findings, findings
