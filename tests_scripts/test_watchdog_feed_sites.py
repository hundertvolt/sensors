"""The watchdog is fed only at the pinned sites (SPECIFICATION.md G.2): `feed_watchdog()`'s and `_own_feed()`'s latched
`.feed()`, the supervisor loop's two calls, `run_setups()`'s one per unit, and `_own_feed()`'s shutdown-sequence callers -
never in a Timer/IRQ callback, in another loop, or anywhere else in src/; a generated module or boot entry feeds nowhere."""

import ast
import shutil
from dataclasses import dataclass
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES

from buildgen.generate import generate_device

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
_SERVICE = ("asy_system_service.py", "SystemService")
_LATCH = "_force_watchdog_starve"
_OWNED = "_feed_owned"
_SUPERVISOR = "_supervise"
_SETUP_RUNNER = "run_setups"
_OWN_FEED = "_own_feed"
_SEQUENCE = "_shutdown_sequence"
# Names the supervisor never reaches: its escalation resets through _reboot() directly, never a command path.
_SUPERVISOR_FORBIDDEN = ("reboot_system", "reboot_bootloader", "reset_to_defaults", "erase_fram", "_request_shutdown")
# Each latched .feed() and the conditions its guard tests; each feed_watchdog() caller and its loop nesting and count.
_LATCHED_FEEDS = {"feed_watchdog": (_LATCH, _OWNED), _OWN_FEED: (_LATCH,)}
_FEED_CALLERS = {_SUPERVISOR: (("While",), 2), _SETUP_RUNNER: (("For",), 1)}
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


def _guard_tests(fn: ast.FunctionDef | ast.AsyncFunctionDef, call: ast.Call) -> str:
    # The conditions of every `if` enclosing the call, as text.
    return " ".join(ast.unparse(n.test) for n in ast.walk(fn) if isinstance(n, ast.If) and any(c is call for c in ast.walk(n)))


def _site_finding(tree: ast.Module, site: Feed) -> str | None:
    # None for a pinned site in its pinned shape, else what is wrong with it.
    if (site.file, site.cls) != _SERVICE:
        return "a watchdog feed outside the pinned set"
    if site.kind == "feed" and site.function in _LATCHED_FEEDS:
        fn = _service_method(tree, site.function)
        tests = "" if fn is None else _guard_tests(fn, site.node)
        missing = [name for name in _LATCHED_FEEDS[site.function] if name not in tests]
        return f"the latched feed no longer tests {', '.join(missing)}" if missing else None
    if site.kind == "feed_watchdog" and site.function in _FEED_CALLERS:
        loops = _FEED_CALLERS[site.function][0]
        return None if site.loops == loops else f"feeds inside {site.loops}, where the pinned site sits inside {loops}"
    return "a watchdog feed outside the pinned set"


def src_findings(src: Path) -> list[str]:
    trees = {p.name: ast.parse(p.read_text(encoding="utf-8"), filename=p.name) for p in sorted(src.glob("*.py"))}
    findings: list[str] = []
    service = trees.get(_SERVICE[0])
    for file, tree in trees.items():
        reached = callback_targets(tree)
        for site in feed_sites(file, tree):
            if site.in_lambda or site.function in reached:
                findings.append(f"{site.where()}: a feed inside a Timer/IRQ callback")
            elif (problem := _site_finding(tree, site)) is not None:
                findings.append(f"{site.where()}: {problem}")
    sites = [s for file, tree in trees.items() for s in feed_sites(file, tree)]
    pinned = [("feed", name, 1) for name in _LATCHED_FEEDS] + [("feed_watchdog", name, want) for name, (_loops, want) in _FEED_CALLERS.items()]
    for kind, function, want in pinned:
        count = sum(1 for s in sites if (s.file, s.cls) == _SERVICE and s.kind == kind and s.function == function)
        if count != want:
            findings.append(f"{_SERVICE[1]}.{function}(): {count} `{kind}(` calls where the pinned set has {want}")
    if service is None:
        findings.append(f"{_SERVICE[0]} is missing")
    else:
        findings.extend(supervisor_findings(service))
        findings.extend(own_feed_findings(service))
    return findings


def _own_feed_use(fn: ast.FunctionDef | ast.AsyncFunctionDef, ref: ast.Attribute) -> bool:
    # A pinned use of self._own_feed inside fn: the sequence's statement call or a step_done handed to its flush, quiesce
    # or erase; _reboot()'s one call under `if fed:`, directly followed by the arm.
    parents = {child: node for node in ast.walk(fn) for child in ast.iter_child_nodes(node)}
    parent = parents.get(ref)
    if fn.name == _SEQUENCE:
        if isinstance(parent, ast.Call) and parent.func is ref:
            return isinstance(parents.get(parent), ast.Expr)
        holder = parents.get(parent) if isinstance(parent, ast.keyword) else parent
        if not isinstance(holder, ast.Call):
            return False
        callee = ast.unparse(holder.func)
        if isinstance(parent, ast.keyword):
            return parent.arg == "step_done" and callee == "self._flush_config_stores" and "close=True" in ast.unparse(holder)
        return callee in ("self._storage.quiesce", "self._storage.erase_chip")
    if fn.name == "_reboot" and isinstance(parent, ast.Call) and parent.func is ref:
        statement = parents.get(parent)
        guard = parents.get(statement) if statement is not None else None
        if not (isinstance(guard, ast.If) and ast.unparse(guard.test) == "fed" and len(guard.body) == 1):
            return False
        body = parents.get(guard)
        siblings = getattr(body, "body", [])
        following = siblings[siblings.index(guard) + 1] if guard in siblings and siblings.index(guard) + 1 < len(siblings) else None
        return following is not None and ast.unparse(following).startswith("self._reset_timer.init(")
    return False


def own_feed_findings(tree: ast.Module) -> list[str]:
    # _own_feed() is referenced only by the shutdown sequence and once by _reboot(); the sequence hands it to its flush,
    # quiesce and erase as each step's feed (a hung step is never fed).
    service = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == _SERVICE[1]), None)
    findings: list[str] = []
    reboot_calls = 0
    for fn in (f for f in getattr(service, "body", []) if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))):
        for ref in (n for n in ast.walk(fn) if isinstance(n, ast.Attribute) and n.attr == _OWN_FEED and fn.name != _OWN_FEED):
            if not _own_feed_use(fn, ref):
                findings.append(f"{_SERVICE[1]}.{fn.name}():{ref.lineno} uses {_OWN_FEED} outside the pinned set")
            elif fn.name == "_reboot":
                reboot_calls += 1
    if reboot_calls != 1:
        findings.append(f"{_SERVICE[1]}._reboot(): {reboot_calls} `{_OWN_FEED}()` calls under `if fed:` before the arm, where the pinned set has one")
    sequence = _service_method(tree, _SEQUENCE)
    if sequence is None or "self._storage.erase_chip(self._own_feed)" not in ast.unparse(sequence):
        findings.append(f"{_SERVICE[1]}.{_SEQUENCE}(): the erase no longer feeds through {_OWN_FEED} per unit")
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


def generated_findings(name: str, source: str) -> list[str]:
    # A generated module or boot entry feeds nowhere: run_setups() feeds the boot batch, the sequence and the supervisor
    # the rest, all inside SystemService.
    return [f"{site.where()}: a feed in generated code" for site in feed_sites(name, ast.parse(source))]


@pytest.fixture(scope="module")
def modules() -> dict[str, str]:
    out: dict[str, str] = {}
    for device in DEVICE_NAMES:
        generated = generate_device(REPO_ROOT / "devices" / f"{device}.toml", SRC, REPO_ROOT / "ext")
        out[f"sensortask_{device}.py"] = generated.module_source
        out[f"sensortask_{device}_main.py"] = generated.boot_entry_source
        out[f"sensortask_{device}_main_noautostart.py"] = generated.boot_entry_noautostart_source
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


def test_generated_modules_and_boot_entries_never_feed(modules: dict[str, str]) -> None:
    assert len(modules) == 3 * len(DEVICE_NAMES)
    assert [f for name, source in sorted(modules.items()) for f in generated_findings(name, source)] == []


def test_a_fifth_feed_site_fails(src_copy: Path) -> None:
    _edit(src_copy / "asy_system_service.py", "    def pause_permanent_storage(self, duration: int) -> bool:\n", "    def pause_permanent_storage(self, duration: int) -> bool:\n        self._watchdog.feed()\n")
    findings = src_findings(src_copy)
    assert len(findings) == 1 and "SystemService.pause_permanent_storage(): a watchdog feed outside the pinned set" in findings[0], findings


def test_a_dropped_latch_test_fails(src_copy: Path) -> None:
    _edit(src_copy / "asy_system_service.py", "        if self._watchdog is not None and not self._force_watchdog_starve and not self._feed_owned:\n", "        if self._watchdog is not None and not self._feed_owned:\n")
    findings = src_findings(src_copy)
    assert len(findings) == 1 and "SystemService.feed_watchdog(): the latched feed no longer tests _force_watchdog_starve" in findings[0], findings


def test_a_dropped_ownership_test_fails(src_copy: Path) -> None:
    _edit(src_copy / "asy_system_service.py", "        if self._watchdog is not None and not self._force_watchdog_starve and not self._feed_owned:\n", "        if self._watchdog is not None and not self._force_watchdog_starve:\n")
    findings = src_findings(src_copy)
    assert len(findings) == 1 and "SystemService.feed_watchdog(): the latched feed no longer tests _feed_owned" in findings[0], findings


def test_an_own_feed_without_the_starve_latch_fails(src_copy: Path) -> None:
    _edit(src_copy / "asy_system_service.py", "        if self._watchdog is not None and not self._force_watchdog_starve:\n            self._watchdog.feed()", "        if self._watchdog is not None:\n            self._watchdog.feed()")
    findings = src_findings(src_copy)
    assert len(findings) == 1 and "SystemService._own_feed(): the latched feed no longer tests _force_watchdog_starve" in findings[0], findings


def test_an_own_feed_outside_the_sequence_fails(src_copy: Path) -> None:
    _edit(src_copy / "asy_system_service.py", "                    no_fail = False\n", "                    no_fail = False\n                    self._own_feed()\n")
    findings = src_findings(src_copy)
    assert len(findings) == 1 and findings[0].startswith("SystemService._supervise():") and "uses _own_feed outside the pinned set" in findings[0], findings


def test_a_reboot_feed_after_the_arm_fails(src_copy: Path) -> None:
    text = (src_copy / "asy_system_service.py").read_text(encoding="utf-8")
    arm = next(line for line in text.splitlines() if line.strip().startswith("self._reset_timer.init(")) + "\n"
    _edit(src_copy / "asy_system_service.py", "            if fed:\n                self._own_feed()  # a system command's last feed, right before the arm\n" + arm, arm + "            if fed:\n                self._own_feed()\n")
    findings = src_findings(src_copy)
    assert any("SystemService._reboot():" in f and "outside the pinned set" in f for f in findings), findings
    assert "SystemService._reboot(): 0 `_own_feed()` calls under `if fed:` before the arm, where the pinned set has one" in findings, findings


def test_an_unfed_erase_fails(src_copy: Path) -> None:
    _edit(src_copy / "asy_system_service.py", "self._storage.erase_chip(self._own_feed)", "self._storage.erase_chip(lambda: None)")
    findings = src_findings(src_copy)
    assert findings == ["SystemService._shutdown_sequence(): the erase no longer feeds through _own_feed per unit"], findings


def test_a_setup_feed_moved_out_of_its_loop_fails(src_copy: Path) -> None:
    _edit(src_copy / "asy_system_service.py", "            await setup()\n            self.feed_watchdog()\n", "            await setup()\n")
    _edit(src_copy / "asy_system_service.py", "        self._config_faults = [", "        self.feed_watchdog()\n        self._config_faults = [")
    findings = src_findings(src_copy)
    assert len(findings) == 1 and "SystemService.run_setups(): feeds inside (), where the pinned site sits inside ('For',)" in findings[0], findings


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
    assert findings[0].endswith("feeds inside ('While', 'For'), where the pinned site sits inside ('While',)"), findings
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


def test_a_generated_feed_fails(modules: dict[str, str]) -> None:
    name = next(n for n in sorted(modules) if n.endswith("_main.py"))
    source = modules[name]
    fed = source.replace("\nasync def ", "\nasync def _fed() -> None:\n    sysfunct.feed_watchdog()\n\nasync def ", 1) if "\nasync def " in source else source + "\nsysfunct.feed_watchdog()\n"
    assert fed != source
    findings = generated_findings(name, fed)
    assert len(findings) == 1 and findings[0].endswith("a feed in generated code"), findings


def test_a_feed_in_a_timer_constructor_callback_fails(src_copy: Path) -> None:
    _edit(src_copy / "asy_system_service.py", "        self._reset_timer = Timer()\n", "        self._reset_timer = Timer(-1, period=10, callback=lambda _t: self.feed_watchdog())\n")
    findings = src_findings(src_copy)
    assert any("SystemService.__init__(): a feed inside a Timer/IRQ callback" in f for f in findings), findings
