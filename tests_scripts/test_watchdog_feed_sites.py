"""The watchdog is fed only at the pinned sites (SPECIFICATION.md G.2): `SystemService.feed_watchdog()`'s latched
`.feed()`, the supervisor loop's two calls (escalation, pass end), and the generated boot batch's call after each
`setup()` - never in a Timer/IRQ callback, in another loop, or anywhere else in src/ or a generated module."""

import ast
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES

from buildgen.generate import generate_device

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
_SERVICE = ("asy_system_service.py", "SystemService")
_LATCH = "_force_watchdog_starve"
_SUPERVISOR = "_supervise"
# Names the supervisor never reaches: its escalation resets through _reboot() directly, never a command path.
_SUPERVISOR_FORBIDDEN = ("reboot_system", "reboot_bootloader", "_request_shutdown")
_BOOT_BATCH = "build_system"
_CALLBACK_KEYWORDS = frozenset({"callback", "handler"})


@dataclass(frozen=True)
class Feed:
    file: str
    cls: str
    function: str
    kind: str  # "feed" or "feed_watchdog"
    line: int
    loops: tuple[str, ...]  # the enclosing loop kinds inside the function, outermost first
    in_lambda: bool
    node: ast.Call

    def where(self) -> str:
        return f"{self.file}:{self.line} {self.cls + '.' if self.cls else ''}{self.function}()"


def _feed_kind(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    name = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else None
    return name if name in ("feed", "feed_watchdog") else None


def feed_sites(file: str, tree: ast.Module) -> list[Feed]:
    sites: list[Feed] = []

    def visit(node: ast.AST, cls: str, function: str, loops: tuple[str, ...], *, in_lambda: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                visit(child, child.name, "", (), in_lambda=False)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                visit(child, cls, child.name, (), in_lambda=False)
            elif isinstance(child, ast.Lambda):
                visit(child, cls, function, loops, in_lambda=True)
            elif isinstance(child, (ast.While, ast.For, ast.AsyncFor)):
                visit(child, cls, function, (*loops, type(child).__name__), in_lambda=in_lambda)
            else:
                if isinstance(child, ast.Call) and (kind := _feed_kind(child)) is not None:
                    sites.append(Feed(file, cls, function, kind, child.lineno, loops, in_lambda, child))
                visit(child, cls, function, loops, in_lambda=in_lambda)

    visit(tree, "", "<module>", (), in_lambda=False)
    return sites


def callback_targets(tree: ast.Module) -> set[str]:
    # Names of the functions any callback=/handler= argument (Timer(), Timer.init(), Pin.irq()) or a
    # positional Pin.irq() handler is, or that its lambda calls.
    targets: set[str] = set()
    for call in (n for n in ast.walk(tree) if isinstance(n, ast.Call)):
        values = [kw.value for kw in call.keywords if kw.arg in _CALLBACK_KEYWORDS] + (call.args[:1] if ast.unparse(call.func).endswith(".irq") else [])
        for value in values:
            for node in ast.walk(value) if isinstance(value, ast.Lambda) else [value]:
                ref = node.func if isinstance(node, ast.Call) else node
                if isinstance(ref, ast.Attribute):
                    targets.add(ref.attr)
                elif isinstance(ref, ast.Name):
                    targets.add(ref.id)
    return targets


def _service_method(tree: ast.Module, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    service = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == _SERVICE[1]), None)
    return None if service is None else next((f for f in service.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and f.name == name), None)


def _guarded_by_latch(fn: ast.FunctionDef | ast.AsyncFunctionDef, call: ast.Call) -> bool:
    return any(isinstance(n, ast.If) and _LATCH in ast.unparse(n.test) and any(c is call for c in ast.walk(n)) for n in ast.walk(fn))


def src_findings(src: Path) -> list[str]:
    trees = {p.name: ast.parse(p.read_text(encoding="utf-8"), filename=p.name) for p in sorted(src.glob("*.py"))}
    findings: list[str] = []
    service = trees.get(_SERVICE[0])
    for file, tree in trees.items():
        reached = callback_targets(tree)
        for site in feed_sites(file, tree):
            if site.in_lambda or site.function in reached:
                findings.append(f"{site.where()}: a feed inside a Timer/IRQ callback")
            elif (site.file, site.cls) == _SERVICE and site.kind == "feed" and site.function == "feed_watchdog":
                fn = _service_method(tree, "feed_watchdog")
                if fn is None or not _guarded_by_latch(fn, site.node):
                    findings.append(f"{site.where()}: the latched feed no longer tests {_LATCH}")
            elif (site.file, site.cls) == _SERVICE and site.kind == "feed_watchdog" and site.function == _SUPERVISOR:
                if site.loops != ("While",):
                    findings.append(f"{site.where()}: the supervisor feeds at its pass end and in its escalation block - not inside {site.loops}")
            else:
                findings.append(f"{site.where()}: a watchdog feed outside the pinned set")
    sites = [s for file, tree in trees.items() for s in feed_sites(file, tree)]
    for kind, function, want in (("feed", "feed_watchdog", 1), ("feed_watchdog", _SUPERVISOR, 2)):
        count = sum(1 for s in sites if (s.file, s.cls) == _SERVICE and s.kind == kind and s.function == function)
        if count != want:
            findings.append(f"{_SERVICE[1]}.{function}(): {count} `{kind}(` calls where the pinned set has {want}")
    if service is None:
        findings.append(f"{_SERVICE[0]} is missing")
    else:
        findings.extend(supervisor_findings(service))
    return findings


def supervisor_findings(tree: ast.Module) -> list[str]:
    # The escalation resets through one _reboot( without fed=, and no command path is reachable from the loop.
    fn = _service_method(tree, _SUPERVISOR)
    if fn is None:
        return [f"{_SERVICE[1]}.{_SUPERVISOR}() is missing"]
    findings: list[str] = []
    names = {n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)} | {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
    findings.extend(f"{_SERVICE[1]}.{_SUPERVISOR}() references {name}" for name in _SUPERVISOR_FORBIDDEN if name in names)
    reboots = [n for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "_reboot"]
    if len(reboots) != 1 or any(kw.arg == "fed" for kw in reboots[0].keywords):
        findings.append(f"{_SERVICE[1]}.{_SUPERVISOR}(): {len(reboots)} `_reboot(` calls where the pinned set has one, without fed=")
    return findings


def generated_findings(device: str, source: str) -> list[str]:
    # The generated boot batch: every `await <x>.setup()` is followed by one sysfunct.feed_watchdog(),
    # outside any loop; no other generated feed.
    tree = ast.parse(source)
    findings: list[str] = []
    batch = next((n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == _BOOT_BATCH), None)
    after_setup: set[int] = set()
    if batch is None:
        findings.append(f"sensortask_{device}: no {_BOOT_BATCH}()")
    else:
        body = batch.body
        for i, stmt in enumerate(body):
            is_setup = isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Await) and isinstance(stmt.value.value, ast.Call) and isinstance(stmt.value.value.func, ast.Attribute) and stmt.value.value.func.attr == "setup"
            if not is_setup:
                continue
            following = body[i + 1] if i + 1 < len(body) else None
            if following is not None and isinstance(following, ast.Expr) and ast.unparse(following) == "sysfunct.feed_watchdog()":
                after_setup.add(id(following.value))
            else:
                findings.append(f"sensortask_{device}:{stmt.lineno} {_BOOT_BATCH}(): `{ast.unparse(stmt)}` is not followed by sysfunct.feed_watchdog()")
    findings.extend(f"{site.where()}: a generated feed outside the boot batch's per-setup() calls" for site in feed_sites(f"sensortask_{device}.py", tree) if id(site.node) not in after_setup)
    return findings


# The later stages of the pinned set: each holds while its form is absent; once it lands, its test fails
# so the landing change moves it into the checks above. (part, owner, still-pending predicate)
_PENDING: tuple[tuple[str, str, Callable[[str, ast.Module], bool]], ...] = (
    ("feed_watchdog() tests _feed_owned", "U20", lambda _text, tree: "_feed_owned" not in ast.unparse(_service_method(tree, "feed_watchdog") or ast.Pass())),
    ("run_setups(): the per-unit feed inside its bounded for; no generated feed", "U20", lambda _text, tree: _service_method(tree, "run_setups") is None),
    (("_own_feed(): referenced only by _shutdown_sequence(), by _reboot() once under `if fed:` right before self._reset_timer.init(, and as step_done of "
      "_flush_config_stores(close=True, ...) and self._storage.quiesce(...)"), "U20", lambda _text, tree: _service_method(tree, "_own_feed") is None),
    ("erase_chip(self._own_feed) in _shutdown_sequence()", "U26", lambda text, _tree: "erase_chip(" not in text),
)


def pending_findings(src: Path) -> list[str]:
    text = (src / _SERVICE[0]).read_text(encoding="utf-8")
    tree = ast.parse(text)
    return [f"pending part landed ({unit}): {part} - pin it in this check and drop it from _PENDING" for part, unit, pending in _PENDING if not pending(text, tree)]


@pytest.fixture(scope="module")
def modules() -> dict[str, str]:
    out: dict[str, str] = {}
    for device in DEVICE_NAMES:
        generated = generate_device(REPO_ROOT / "devices" / f"{device}.toml", SRC, REPO_ROOT / "ext")
        out[device] = generated.module_source
        out[f"boot_{device}"] = generated.boot_entry_source
    return out


@pytest.fixture
def src_copy(tmp_path: Path) -> Path:
    return Path(shutil.copytree(SRC, tmp_path / "src"))


def _edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, f"{path.name}: the anchor is not unique: {old!r}"
    path.write_text(text.replace(old, new), encoding="utf-8")


def test_src_feeds_only_at_the_pinned_sites() -> None:
    assert src_findings(SRC) == []


def test_generated_modules_feed_only_after_each_boot_setup(modules: dict[str, str]) -> None:
    findings: list[str] = []
    for device, source in sorted(modules.items()):
        if device.startswith("boot_"):
            findings += [f"{device}: {site.where()}: a feed in a generated boot entry" for site in feed_sites(device, ast.parse(source))]
        else:
            findings += generated_findings(device, source)
    assert findings == []
    assert all(sum(1 for s in feed_sites(d, ast.parse(src)) if s.kind == "feed_watchdog") >= 3 for d, src in modules.items() if not d.startswith("boot_"))


def test_the_later_stages_are_still_pending() -> None:
    assert pending_findings(SRC) == []


def test_a_fifth_feed_site_fails(src_copy: Path) -> None:
    _edit(src_copy / "asy_system_service.py", "    def pause_permanent_storage(self, duration: int) -> bool:\n", "    def pause_permanent_storage(self, duration: int) -> bool:\n        self._watchdog.feed()\n")
    findings = src_findings(src_copy)
    assert len(findings) == 1 and "SystemService.pause_permanent_storage(): a watchdog feed outside the pinned set" in findings[0], findings


def test_a_dropped_latch_test_fails(src_copy: Path) -> None:
    _edit(src_copy / "asy_system_service.py", "        if self._watchdog is not None and not self._force_watchdog_starve:\n            self._watchdog.feed()", "        if self._watchdog is not None:\n            self._watchdog.feed()")
    findings = src_findings(src_copy)
    assert len(findings) == 1 and "SystemService.feed_watchdog(): the latched feed no longer tests _force_watchdog_starve" in findings[0], findings


def test_a_feed_in_a_timer_callback_fails(src_copy: Path) -> None:
    _edit(src_copy / "asy_system_service.py", "callback=lambda _b: self._sequencer_flag.set())", "callback=lambda _b: self.feed_watchdog())")
    findings = src_findings(src_copy)
    # Both the lambda's own call and the latched feed it reaches.
    assert [f.split(" ", 1)[1] for f in findings] == [
        "SystemService.feed_watchdog(): a feed inside a Timer/IRQ callback",
        "SystemService.start_timers(): a feed inside a Timer/IRQ callback",
    ], findings


def test_a_function_a_timer_callback_reaches_must_not_feed(src_copy: Path) -> None:
    _edit(src_copy / "asy_system_service.py", "callback=lambda _b: self._sequencer_flag.set())", "callback=lambda _b: self.pause_permanent_storage(0))")
    _edit(src_copy / "asy_system_service.py", "    def pause_permanent_storage(self, duration: int) -> bool:\n", "    def pause_permanent_storage(self, duration: int) -> bool:\n        self.feed_watchdog()\n")
    findings = src_findings(src_copy)
    assert len(findings) == 1 and "SystemService.pause_permanent_storage(): a feed inside a Timer/IRQ callback" in findings[0], findings


def test_a_feed_inside_the_supervisor_scan_fails(src_copy: Path) -> None:
    _edit(src_copy / "asy_system_service.py", "                    no_fail = False\n", "                    no_fail = False\n                    self.feed_watchdog()\n")
    findings = src_findings(src_copy)
    assert findings[0].endswith("the supervisor feeds at its pass end and in its escalation block - not inside ('While', 'For')"), findings
    assert findings[1] == "SystemService._supervise(): 3 `feed_watchdog(` calls where the pinned set has 2", findings


def test_a_dropped_escalation_feed_fails(src_copy: Path) -> None:
    _edit(src_copy / "asy_system_service.py", "                self.feed_watchdog()\n                self._force_watchdog_starve = True\n", "                self._force_watchdog_starve = True\n")
    findings = src_findings(src_copy)
    assert findings == ["SystemService._supervise(): 1 `feed_watchdog(` calls where the pinned set has 2"], findings


def test_an_escalation_through_a_command_path_fails(src_copy: Path) -> None:
    _edit(src_copy / "asy_system_service.py", '                await self._reboot(_RR_TASK_BUDGET, "Reboot triggered", system_reset)\n', "                await self.reboot_system()\n")
    findings = src_findings(src_copy)
    assert findings == [
        "SystemService._supervise() references reboot_system",
        "SystemService._supervise(): 0 `_reboot(` calls where the pinned set has one, without fed=",
    ], findings


def test_a_fed_escalation_reset_fails(src_copy: Path) -> None:
    _edit(src_copy / "asy_system_service.py", 'await self._reboot(_RR_TASK_BUDGET, "Reboot triggered", system_reset)', 'await self._reboot(_RR_TASK_BUDGET, "Reboot triggered", system_reset, fed=True)')
    findings = src_findings(src_copy)
    assert findings == ["SystemService._supervise(): 1 `_reboot(` calls where the pinned set has one, without fed="], findings


def test_a_feed_in_another_loop_fails(src_copy: Path) -> None:
    _edit(src_copy / "asy_system_service.py", "        for n, starter in enumerate(timers):\n", "        for n, starter in enumerate(timers):\n            self.feed_watchdog()\n")
    findings = src_findings(src_copy)
    assert len(findings) == 1 and "SystemService.start_timers(): a watchdog feed outside the pinned set" in findings[0], findings


def test_a_generated_feed_off_the_per_setup_pattern_fails(modules: dict[str, str]) -> None:
    device = next(d for d in sorted(modules) if not d.startswith("boot_"))
    source = modules[device]
    setup = next(line for line in source.splitlines() if line.strip().startswith("await ") and line.strip().endswith(".setup()"))
    moved = source.replace(f"{setup}\n    sysfunct.feed_watchdog()\n", f"{setup}\n", 1).replace("    gc.collect()\n", "    gc.collect()\n    for _ in range(2):\n        sysfunct.feed_watchdog()\n", 1)
    assert moved != source
    findings = generated_findings(device, moved)
    assert len(findings) == 2, findings
    assert "is not followed by sysfunct.feed_watchdog()" in findings[0] and "a generated feed outside the boot batch's per-setup() calls" in findings[1], findings


def test_a_landed_later_stage_must_be_pinned(src_copy: Path) -> None:
    _edit(src_copy / "asy_system_service.py", "    def feed_watchdog(self) -> None:\n", "    def _own_feed(self) -> None:\n        pass\n\n    def feed_watchdog(self) -> None:\n")
    findings = pending_findings(src_copy)
    assert len(findings) == 1 and findings[0].startswith("pending part landed (U20): _own_feed():"), findings


def test_a_feed_in_a_timer_constructor_callback_fails(src_copy: Path) -> None:
    _edit(src_copy / "asy_system_service.py", "        self._reset_timer = Timer()\n", "        self._reset_timer = Timer(-1, period=10, callback=lambda _t: self.feed_watchdog())\n")
    findings = src_findings(src_copy)
    assert any("SystemService.__init__(): a feed inside a Timer/IRQ callback" in f for f in findings), findings
