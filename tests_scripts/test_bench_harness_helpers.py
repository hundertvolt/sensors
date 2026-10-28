"""Covers tests_hardware/'s shared host helpers offline against fakes: serving restore and recovery, boot/crash line
observers, errcount oracles, script rendering and facts, mpremote/picotool wrappers, the bench's route set and the
thread-worker, join, reset and no-sync rules over every host module of the hardware tier."""

import ast
import functools
import inspect
import json
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
import tomllib
from _devices import DEVICE_NAMES, device_toml

from buildgen.schema_ast import extract_field_schemas
from buildgen.source_ast import parse_source
from buildgen.validate import device_max_connections

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests_hardware"))

import bench_facts
import error_log_helpers
import harness
import http_client
import kick_then_reset as kick_then_reset_cli
import website_identity

TESTS_HARDWARE = Path(__file__).resolve().parent.parent / "tests_hardware"
# Every host module of the hardware tier; the device scripts run on the board and have their own guards.
HOST_MODULES = sorted(p for p in TESTS_HARDWARE.rglob("*.py") if "device_scripts" not in p.parts)
# The bench modules that repair an aborted run's leftover config value, and the one pushing sensor fields.
PUSH_MODULE = TESTS_HARDWARE / "bench" / "test_sensor_config_push_over_real_hardware.py"
REPAIR_MODULES = [TESTS_HARDWARE / "bench" / "test_network_resilience.py", PUSH_MODULE]

# @tunable l0.bench_helpers_stop_wait_s = 2.0
_STOP_WAIT_S = 2.0  # how soon a set stop must end the script-server wait
# The handlers a fetch's failures need: a cut-off answer is an HTTPException, beside OSError's transport errors.
_CATCH_ALL = frozenset({"Exception", "BaseException"})
_HTTP_ERROR = frozenset({"http_client.HTTP_ERROR", "HTTP_ERROR"})


class _Answers:
    # http_client.fetch()'s stand-in: each call takes the next outcome, a status code or None for a cut-off answer,
    # the last repeating; `calls` counts them.
    def __init__(self, outcomes: "list[int | None]") -> None:
        self.calls = 0
        self._outcomes = outcomes

    def __call__(self, *_args: object, **_kwargs: object) -> http_client.HttpResponse:
        self.calls += 1
        outcome = self._outcomes.pop(0) if len(self._outcomes) > 1 else self._outcomes[0]
        if outcome is None:
            raise http_client.HTTP_ERROR("cut off")
        return http_client.HttpResponse(outcome, {}, b"{}")


class _Clock(threading.Event):
    # A fake clock that is also a stop event: the `clock` fixture patches time.monotonic()/time.sleep() onto it and a
    # wait advances it instead of blocking. Every wait is recorded, so a bound is asserted exactly rather than timed.
    def __init__(self) -> None:
        super().__init__()
        self.now = 0.0
        self.waits: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.waits.append(seconds)
        self.now += seconds

    def wait(self, timeout: "float | None" = None) -> bool:
        assert timeout is not None, "an unbounded wait"
        if not self.is_set():
            self.sleep(timeout)
        return self.is_set()


class _FetchResolver:
    # Which calls of one module can let a fetch's failure escape: a helper module's raiser (http_client.fetch() the
    # first), imported by name or called through its module, or a function of this module that raises, transitively.
    def __init__(self, tree: ast.Module, helpers: "dict[str, frozenset[str]]") -> None:
        self.names: set[str] = set()
        self.modules: dict[str, frozenset[str]] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module in helpers:
                self.names |= {alias.asname or alias.name for alias in node.names if alias.name in helpers[node.module]}
            elif isinstance(node, ast.Import):
                self.modules |= {alias.asname or alias.name: helpers[alias.name] for alias in node.names if alias.name in helpers}
        self.raisers: dict[str, int] = {}  # each raising function by name, with its first unguarded fetching call's line
        defs = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        calls = {id(fn): _unguarded_calls(fn) for fn in defs}
        grown = True
        while grown:
            grown = False
            for fn in defs:
                hit = None if fn.name in self.raisers else next((call for call in calls[id(fn)] if self.fetching(call)), None)
                if hit is not None:
                    self.raisers[fn.name] = hit.lineno
                    grown = True

    def fetching(self, call: ast.Call) -> bool:
        func = call.func
        if isinstance(func, ast.Name):
            return func.id in self.raisers or func.id in self.names
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            return func.attr in self.modules.get(func.value.id, ()) or (func.value.id in ("self", "cls") and func.attr in self.raisers)
        return False


class _HeldSocket:
    def __init__(self, outcome: bytes | type[OSError]) -> None:
        self._outcome = outcome

    def recv(self, _size: int) -> bytes:
        if isinstance(self._outcome, bytes):
            return self._outcome
        raise self._outcome

    def settimeout(self, _timeout: float) -> None:
        pass


class _LogBoard:
    # tail_log() hands out one prepared chunk per call (then nothing), each call lasting its duration as on a live board.
    def __init__(self, chunks: "list[list[str]]") -> None:
        self._chunks = chunks

    def tail_log(self, duration_s: float, baudrate: int = 115200) -> "list[str]":
        del baudrate
        time.sleep(duration_s)
        return self._chunks.pop(0) if self._chunks else []


class _PhasedBoard:
    # A board printing one line per phase of observe_during(): "before" until the action runs, "during" while it does,
    # "after" in the tail after it. Each is read once; a read finding nothing new waits, bounded, for the next phase.
    def __init__(self) -> None:
        self.phase = "before"
        self.read: list[str] = []
        self._changed = threading.Condition()

    def enter(self, phase: str) -> None:
        # Moves to `phase` and returns once the tail has read it: the test advances on events, never on a fixed sleep.
        with self._changed:
            self.phase = phase
            self._changed.notify_all()
            assert self._changed.wait_for(lambda: phase in self.read, timeout=_STOP_WAIT_S), f"the tail never read {phase!r}"

    def tail_log(self, duration_s: float, baudrate: int = 115200) -> "list[str]":
        del baudrate
        with self._changed:
            if not self._changed.wait_for(lambda: self.phase not in self.read, timeout=duration_s):
                return []
            self.read.append(self.phase)
            self._changed.notify_all()
            return [self.phase]


class _Recorder:
    # A fake board and bench in one: every call it sees, in order.
    def __init__(self, *, configured: bool = True) -> None:
        self.ap_conn = "bench-ap"
        self.calls: list[str] = []
        self.configured = configured
        self.recovery_events: list[str] = []

    def is_configured(self) -> bool:
        return self.configured

    def hard_reset(self) -> None:
        self.calls.append("hard_reset")

    def kick_all_stations(self) -> None:
        self.calls.append("kick_all_stations")



def _bare_resets(tree: ast.Module) -> "list[str]":
    # Every board.hard_reset() a bench module makes itself: a recovery must go through recover_by_reset() or
    # kick_then_reset(), so it is reported and never skips the kick.
    return [f"line {node.lineno}" for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "hard_reset"]


@functools.cache
def _bench_routes() -> "tuple[str, ...]":
    # harness.get_routes() as the bench device answers it: one live read the per-device cases share.
    return tuple(harness.get_routes())


def _call_name(call: ast.Call) -> str:
    # The callee's own name: `f` of f(...) and of x.y.f(...); "" for a call of a call or a subscript.
    func = call.func
    return func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""


def _catches(handler: ast.ExceptHandler) -> set[str]:
    kinds = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type] if handler.type else []
    return {ast.unparse(kind) for kind in kinds}


def _declared_default(src_file: str, field: str) -> object:
    # The default a src/ schema tuple declares, read apart from buildgen: the third element of the six-element
    # ("<field>", type, default, min, max, special) literal naming the field.
    for node in ast.walk(_module_tree(harness.SRC_DIR / src_file)):
        if isinstance(node, ast.Tuple) and len(node.elts) == 6 and isinstance(node.elts[0], ast.Constant) and node.elts[0].value == field:
            return ast.literal_eval(node.elts[2])
    raise AssertionError(f"src/{src_file} has no schema tuple for {field!r}")


def _entry(counter: int) -> "error_log_helpers.ErrcountEntry":
    return {"counter": counter, "history": []}


def _guards_fetch(node: "ast.Try | ast.TryStar") -> bool:
    caught: set[str] = set().union(*(_catches(handler) for handler in node.handlers))
    return bool(caught & _CATCH_ALL) or ("OSError" in caught and bool(caught & _HTTP_ERROR))


@functools.cache
def _helper_raisers() -> "dict[str, frozenset[str]]":
    # Each top-level tests_hardware/ helper module's raisers by name, http_client.fetch() itself the seed; recomputed
    # until stable, since one helper module calls another's.
    helpers: dict[str, frozenset[str]] = {"http_client": frozenset({"fetch"})}
    paths = sorted(TESTS_HARDWARE.glob("*.py"))
    while True:
        grown = {path.stem: helpers.get(path.stem, frozenset()) | frozenset(_FetchResolver(_module_tree(path), helpers).raisers) for path in paths}
        if all(helpers.get(stem) == names for stem, names in grown.items()):
            return helpers
        helpers.update(grown)


def _joins(call: ast.Call, joiners: "set[str]") -> bool:
    # A thread's join(): `<thread>.join(...)` (never str.join on a literal), or a call of a local function that joins.
    func = call.func
    return (isinstance(func, ast.Attribute) and func.attr == "join" and not isinstance(func.value, ast.Constant)) or _call_name(call) in joiners


@functools.cache
def _log_literals() -> "frozenset[str]":
    # Every string constant passed to a logger method call (self.pr.one(...), pr.err_s(...), ...) anywhere in src/.
    found = set()
    for path in sorted(harness.SRC_DIR.glob("*.py")):
        for node in ast.walk(_module_tree(path)):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and ast.unparse(node.func.value).endswith("pr"):
                found |= {arg.value for arg in ast.walk(node) if isinstance(arg, ast.Constant) and isinstance(arg.value, str)}
    return frozenset(found)


def _module_tree(path: Path) -> ast.Module:
    # One parse per file text, shared by every rule here and with buildgen's own reads of src/ (a read-only tree).
    return parse_source(path.read_text(encoding="utf-8"), str(path))


def _no_sync_offenders(tree: ast.Module) -> "list[str]":
    # Every ["uv", "run", ...] argument list lacking "--no-sync": a board call or runner step that may sync mid-run.
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.List) and len(node.elts) >= 2 and all(isinstance(e, ast.Constant) for e in node.elts[:2]):
            head = [e.value for e in node.elts[:2] if isinstance(e, ast.Constant)]
            if head == ["uv", "run"] and not any(isinstance(e, ast.Constant) and e.value == "--no-sync" for e in node.elts):
                found.append(f"line {node.lineno}: {ast.unparse(node)[:60]}")
    return found


def _own_nodes(nodes: "list[ast.stmt]") -> "list[ast.AST]":
    # Every node the statements hold outside a nested def or lambda, which runs only when called.
    found: list[ast.AST] = []

    def visit(node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            return
        found.append(node)
        for child in ast.iter_child_nodes(node):
            visit(child)

    for stmt in nodes:
        visit(stmt)
    return found


def _pushed_fields() -> "list[tuple[str, str]]":
    # (src file, field) for every sensor field the push module writes: the keys of each _<NAME>_TEST_VALUES dict, with
    # the src/ module whose _NAME is that sensor (a text match: collection parses no src/). No dict is a failing case.
    by_name = {}
    for path in sorted(harness.SRC_DIR.glob("*.py")):
        named = re.search(r'^_NAME = (?:const\()?"([^"]+)"', path.read_text(encoding="utf-8"), re.MULTILINE)
        if named:
            by_name[named.group(1)] = path.name
    pushed = []
    for node in _module_tree(PUSH_MODULE).body:
        target = ast.unparse(node.targets[0]) if isinstance(node, ast.Assign) else ""
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict) and target.startswith("_") and target.endswith("_TEST_VALUES"):
            src_file = by_name.get(target[1 : -len("_TEST_VALUES")], f"<no src/ module's _NAME matches {target}>")
            pushed += [(src_file, key.value) for key in node.value.keys if isinstance(key, ast.Constant) and isinstance(key.value, str)]
    return pushed or [(f"<no _<NAME>_TEST_VALUES dict in {PUSH_MODULE.name}>", "")]


def _thread_targets(tree: ast.Module) -> "list[ast.expr]":
    # Each Thread(...) call's target: its target= keyword, else its second positional argument (Thread(None, f)).
    targets = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _call_name(node) == "Thread":
            keyword = next((kw.value for kw in node.keywords if kw.arg == "target"), None)
            target = keyword if keyword is not None else node.args[1] if len(node.args) > 1 else None
            if target is not None:
                targets.append(target)
    return targets


def _unguarded_calls(fn: "ast.FunctionDef | ast.AsyncFunctionDef") -> "list[ast.Call]":
    # Every call fn's own body makes outside a try guarding a fetch's failures; a nested def or lambda runs only when
    # called, so it is read as a function of its own.
    found: list[ast.Call] = []

    def visit(node: ast.AST, *, guarded: bool) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            return
        if isinstance(node, (ast.Try, ast.TryStar)):
            for stmt in node.body:
                visit(stmt, guarded=guarded or _guards_fetch(node))
            for part in [*node.handlers, *node.orelse, *node.finalbody]:
                visit(part, guarded=guarded)
            return
        if isinstance(node, ast.Call) and not guarded:
            found.append(node)
        for child in ast.iter_child_nodes(node):
            visit(child, guarded=guarded)

    for stmt in fn.body:
        visit(stmt, guarded=False)
    return found


def _unguarded_fetches(tree: ast.Module, helpers: "dict[str, frozenset[str]]") -> "list[str]":
    # Every thread target a fetch's failure can escape from, which then kills the thread and silently stops its load.
    resolver = _FetchResolver(tree, helpers)
    found = []
    for call_target in _thread_targets(tree):
        target = call_target
        while isinstance(target, ast.Call) and target.args:  # functools.partial(worker, ...)
            target = target.args[0]
        if isinstance(target, ast.Lambda):
            hits = [node.lineno for node in _own_nodes([ast.Expr(target.body)]) if isinstance(node, ast.Call) and resolver.fetching(node)]
            name, line = "lambda", hits[0] if hits else None
        else:
            name = target.id if isinstance(target, ast.Name) else target.attr if isinstance(target, ast.Attribute) else ""
            line = resolver.raisers.get(name)
        if line is not None:
            found.append(f"{name} (line {line})")
    return found


def _unjoined_starts(tree: ast.Module) -> "list[str]":
    # Every function that starts a thread with no join() reachable from a finally, or after a fixture's yield: a failing
    # test would leave its load running into the next one. A join through a local function counts.
    defs = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    own = {id(fn): _own_nodes(fn.body) for fn in defs}
    calls = {id(fn): [node for node in own[id(fn)] if isinstance(node, ast.Call)] for fn in defs}
    joiners: set[str] = set()
    grown = True
    while grown:
        grown = False
        for fn in defs:
            if fn.name not in joiners and any(_joins(call, joiners) for call in calls[id(fn)]):
                joiners.add(fn.name)
                grown = True
    found = []
    for fn in defs:
        if not {"Thread", "start"} <= {_call_name(call) for call in calls[id(fn)]}:
            continue
        finals = [stmt for node in own[id(fn)] if isinstance(node, (ast.Try, ast.TryStar)) for stmt in node.finalbody]
        yields = [index for index, stmt in enumerate(fn.body) if isinstance(stmt, ast.Expr) and isinstance(stmt.value, (ast.Yield, ast.YieldFrom))]
        reachable = _own_nodes(finals + (fn.body[yields[0] + 1 :] if yields else []))
        if not any(_joins(node, joiners) for node in reachable if isinstance(node, ast.Call)):
            found.append(f"{fn.name} (line {fn.lineno})")
    return found


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> _Clock:
    fake = _Clock()
    monkeypatch.setattr(time, "monotonic", fake.monotonic)
    monkeypatch.setattr(time, "sleep", fake.sleep)
    return fake


def test_wait_for_script_server_ends_at_once_when_its_test_has_already_stopped(monkeypatch: pytest.MonkeyPatch, clock: _Clock) -> None:
    answers = _Answers([200])
    monkeypatch.setattr(http_client, "fetch", answers)
    clock.set()
    assert harness.wait_for_script_server("dut", clock) is False
    assert clock.waits == [] and answers.calls == 0


def test_wait_for_script_server_waits_out_main_pys_server_then_finds_the_scripts(monkeypatch: pytest.MonkeyPatch, clock: _Clock) -> None:
    # 200 from main.py's server, a gap while mpremote swaps it for the script, then the script's 200.
    answers = _Answers([200, None, 200])
    monkeypatch.setattr(http_client, "fetch", answers)
    assert harness.wait_for_script_server("dut", clock, timeout_s=5.0, handover_s=5.0) is True
    assert answers.calls == 3 and clock.waits == [harness._SCRIPT_SERVER_HANDOVER_POLL_S]


def test_wait_for_script_server_raises_when_main_pys_server_outlasts_the_handover(monkeypatch: pytest.MonkeyPatch, clock: _Clock) -> None:
    # Nothing ever went quiet, so a 200 cannot be told from the script's: never True, and the wait ends at its bound.
    monkeypatch.setattr(http_client, "fetch", _Answers([200]))
    with pytest.raises(harness.HardwareTestFailureError, match=r"main\.py's server still answers /status"):
        harness.wait_for_script_server("dut", clock, timeout_s=5.0, handover_s=2.2)
    assert sum(clock.waits) == pytest.approx(2.2) and max(clock.waits) <= harness._SCRIPT_SERVER_HANDOVER_POLL_S


def test_wait_for_script_server_gives_up_at_its_bound_when_nothing_ever_answers(monkeypatch: pytest.MonkeyPatch, clock: _Clock) -> None:
    monkeypatch.setattr(http_client, "fetch", _Answers([None]))
    assert harness.wait_for_script_server("dut", clock, timeout_s=2.5, handover_s=0.1) is False
    assert sum(clock.waits) == pytest.approx(2.5) and max(clock.waits) <= harness._SCRIPT_SERVER_POLL_S


def test_wait_for_script_server_stops_waiting_for_the_script_when_its_test_ends(monkeypatch: pytest.MonkeyPatch) -> None:
    # main.py's server already gone, the script's never arriving: a real stop set from another thread, not the 60 s
    # timeout, ends the wait.
    monkeypatch.setattr(http_client, "fetch", _Answers([None]))
    stop = threading.Event()
    timer = threading.Timer(0.02, stop.set)
    timer.start()
    started = time.monotonic()
    try:
        assert harness.wait_for_script_server("dut", stop, timeout_s=60.0, handover_s=0.0) is False
    finally:
        timer.join(_STOP_WAIT_S)
    assert time.monotonic() - started < _STOP_WAIT_S


def test_wait_until_ends_at_its_bound_and_checks_once_more_there(clock: _Clock) -> None:
    checks: list[float] = []

    def check() -> bool:
        checks.append(clock.now)
        return False

    with pytest.raises(TimeoutError, match="the thing"):
        harness.wait_until(check, 2.5, poll_interval_s=1.0, description="the thing")
    assert clock.waits == [1.0, 1.0, 0.5] and checks == [0.0, 1.0, 2.0, 2.5]


def test_restore_board_to_serving_goes_through_kick_then_reset_and_then_waits_for_http(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _Recorder()

    def kick_then_reset(board: object, bench: object) -> None:
        assert board is fake and bench is fake
        fake.calls += ["kick_then_reset", "kick_all_stations", "hard_reset"]

    def fetch(*_args: object, **_kwargs: object) -> http_client.HttpResponse:
        fake.calls.append("fetch")
        return http_client.HttpResponse(200, {}, b"{}")

    monkeypatch.setattr(harness, "kick_then_reset", kick_then_reset)
    monkeypatch.setattr(http_client, "fetch", fetch)
    harness.restore_board_to_serving(fake, fake, "dut")  # type: ignore[arg-type]
    assert fake.calls == ["kick_then_reset", "kick_all_stations", "hard_reset", "fetch"]


def test_kick_then_reset_kicks_the_stations_before_the_one_reset() -> None:
    fake = _Recorder()
    harness.kick_then_reset(fake, fake)  # type: ignore[arg-type]
    assert fake.calls == ["kick_all_stations", "hard_reset"]


def test_the_soak_reads_systems_log_first_only_after_a_hard_reset_and_a_fresh_boot() -> None:
    # Its calls in source order, no twin: without a bench the session's own reset leaves the board mid-boot, so the
    # first live read must follow a reset of the soak's own, the board back on USB and the boot line.
    tree = ast.parse((TESTS_HARDWARE / "flash" / "test_memory_stress.py").read_text(encoding="utf-8"))
    soak = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "test_single_core_timing_headroom_holds_under_normal_full_task_load")
    calls = sorted((node for node in ast.walk(soak) if isinstance(node, ast.Call)), key=lambda call: (call.lineno, call.col_offset))
    order = [_call_name(call) for call in calls if _call_name(call) in {"hard_reset", "wait_until", "wait_for_boot", "read_live_system_log"}]
    assert order[: order.index("read_live_system_log") + 1] == ["hard_reset", "wait_until", "wait_for_boot", "read_live_system_log"], order


def test_elf_symbols_drops_a_name_nm_lists_more_than_once(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # A canned `nm -S` listing, no toolchain run: two local `tab`s and a `helper` listed once unsized could each be the
    # one a caller means, so neither comes back; the unique sized `base` does, and the unsized `_start` never does.
    listing = "20000100 00000010 b tab\n20000200 00000020 b tab\n20000300 00000004 d base\n10000400 t helper\n10000500 00000008 t helper\n10000000 T _start\n"
    monkeypatch.setattr(shutil, "which", lambda *_args, **_kwargs: "/usr/bin/arm-none-eabi-nm")
    monkeypatch.setattr(subprocess, "run", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, stdout=listing, stderr=""))
    assert harness.elf_symbols(tmp_path / "firmware.elf") == {"base": (0x20000300, 4)}


def test_the_kick_then_reset_cli_kicks_before_the_one_reset_on_the_named_board(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _Recorder()
    boards: list[str | None] = []

    def board(device: "str | None" = None) -> _Recorder:
        boards.append(device)
        return fake

    monkeypatch.setattr(kick_then_reset_cli, "BenchBridge", lambda: fake)
    monkeypatch.setattr(harness, "Board", board)
    assert kick_then_reset_cli.main(["--device", "/dev/fake-board"]) == 0
    assert boards == ["/dev/fake-board"] and fake.calls == ["kick_all_stations", "hard_reset"]


def test_the_kick_then_reset_cli_exits_2_naming_the_bench_setup_when_no_bridge_is_configured(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    fake = _Recorder(configured=False)
    monkeypatch.setattr(kick_then_reset_cli, "BenchBridge", lambda: fake)
    monkeypatch.setattr(harness, "Board", lambda device=None: pytest.fail(f"a board was resolved ({device}) with no bridge"))
    assert kick_then_reset_cli.main([]) == 2
    assert "env --tier bench" in capsys.readouterr().err and fake.calls == []


@pytest.mark.parametrize(
    ("ready_after", "calls", "notes", "spent_s"),
    [
        ("never-needed", [], 0, 0.0),
        ("reset", ["kick_all_stations", "hard_reset"], 1, 30.0),
    ],
)
def test_recover_by_reset_resets_only_when_the_first_wait_times_out_and_reports_it(clock: _Clock, ready_after: str, calls: "list[str]", notes: int, spent_s: float) -> None:
    fake = _Recorder()
    recorded: list[tuple[str, bool]] = []

    def note(text: str, *, recovery: bool = False) -> None:
        recorded.append((text, recovery))

    def ready() -> bool:
        return ready_after == "never-needed" or "hard_reset" in fake.calls

    harness.recover_by_reset(fake, fake, ready, first_wait_s=30.0, retry_wait_s=60.0, skipped="the NTP resync check", note=note, description="the DUT rejoining")  # type: ignore[arg-type]
    assert fake.calls == calls
    assert len(recorded) == notes
    assert clock.now == pytest.approx(spent_s), "the reset came before the whole first wait, or the retry waited on a ready board"
    if notes:
        assert recorded[0][1] is True and "skipped: the NTP resync check" in recorded[0][0] and "the DUT rejoining" in recorded[0][0]


def test_recover_by_reset_raises_after_exactly_one_reset_when_never_ready(clock: _Clock) -> None:
    fake = _Recorder()
    with pytest.raises(TimeoutError, match="after one recovery"):
        harness.recover_by_reset(fake, fake, lambda: False, first_wait_s=30.0, retry_wait_s=60.0, skipped="x", note=lambda *_a, **_k: None, description="never")  # type: ignore[arg-type]
    assert fake.calls == ["kick_all_stations", "hard_reset"]
    assert clock.now == pytest.approx(90.0)


def test_the_bare_reset_rule_sees_a_direct_hard_reset() -> None:
    assert _bare_resets(ast.parse("def t(board):\n    board.hard_reset()\n")) == ["line 2"]
    assert _bare_resets(ast.parse("def t(board, bench):\n    harness.kick_then_reset(board, bench)\n")) == []


@pytest.mark.parametrize("module", sorted((TESTS_HARDWARE / "bench").glob("*.py")), ids=lambda p: p.name)
def test_no_bench_module_resets_the_board_outside_the_reported_helpers(module: Path) -> None:
    assert _bare_resets(_module_tree(module)) == [], f"{module.name}: call harness.recover_by_reset()/kick_then_reset() instead"


def test_a_logger_absent_before_and_present_now_is_a_shape_change(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(error_log_helpers, "get_errcount", lambda _ip: {"SGP40": _entry(1)})
    with pytest.raises(AssertionError, match=r"changed shape.*appeared \['SGP40'\]"):
        error_log_helpers.assert_no_module_logged_a_new_error("dut", {}, "burst")


def test_a_logger_present_before_and_absent_now_is_a_shape_change(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(error_log_helpers, "get_errcount", lambda _ip: {"SYSTEM": _entry(0)})
    with pytest.raises(AssertionError, match=r"vanished \['SGP40'\]"):
        error_log_helpers.assert_no_module_logged_a_new_error("dut", {"SGP40": _entry(0), "SYSTEM": _entry(0)}, "burst")


def test_a_grown_counter_is_a_new_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(error_log_helpers, "get_errcount", lambda _ip: {"SGP40": _entry(3)})
    with pytest.raises(AssertionError, match=r"'SGP40': \(2, 3\)"):
        error_log_helpers.assert_no_module_logged_a_new_error("dut", {"SGP40": _entry(2)}, "burst")


def test_an_unchanged_counter_is_no_new_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(error_log_helpers, "get_errcount", lambda _ip: {"SGP40": _entry(2), "SYSTEM": _entry(0)})
    error_log_helpers.assert_no_module_logged_a_new_error("dut", {"SGP40": _entry(2), "SYSTEM": _entry(0)}, "burst")


def test_a_missing_logger_fails_naming_it_and_the_names_present() -> None:
    with pytest.raises(AssertionError, match=r"'NOPE' is not in /status errcount \(\['SGP40', 'SYSTEM'\]\)"):
        error_log_helpers.errcount_entry({"SYSTEM": _entry(0), "SGP40": _entry(0)}, "NOPE")


@pytest.mark.parametrize("entry", [{"counter": 1}, {"history": []}, {"counter": "1", "history": []}, {"counter": True, "history": []}, {"counter": 1, "history": [1]}, 7])
def test_an_entry_without_an_int_counter_and_a_history_list_fails(entry: object) -> None:
    with pytest.raises(AssertionError, match="SGP40"):
        error_log_helpers.errcount_entry({"SGP40": entry}, "SGP40")


@pytest.mark.parametrize("oracle", ["assert_no_task_ended", "assert_module_error_log_empty"])
def test_the_log_oracles_fail_closed_on_a_missing_logger(monkeypatch: pytest.MonkeyPatch, oracle: str) -> None:
    monkeypatch.setattr(error_log_helpers, "get_errcount", lambda _ip: {"WIFI": _entry(0)})
    with pytest.raises(AssertionError, match="is not in /status errcount"):
        getattr(error_log_helpers, oracle)("dut", "SYSTEM")


@pytest.mark.parametrize("marker", [*harness.BOOT_COMPLETION_MARKERS, "RTC set to:"])
def test_every_pinned_log_line_is_one_src_actually_logs(marker: str) -> None:
    # A reworded log line fails here, not as a boot oracle that silently never matches; the logger's own name prefix
    # (FRAM's "FRAM ") is the one part a marker carries beyond the call's text.
    literals = _log_literals()
    assert any(marker in text or marker.partition(" ")[2] == text for text in literals), f"no logger call in src/ prints {marker!r}"


def test_boot_lines_need_a_completion_marker_never_a_bare_tag() -> None:
    lines = ["CFGMGR_SYSTEM config_SYSTEM.cfg - loading", "FRAM chunk 3 allocated", "CFGMGR_WIFI config_WIFI.cfg - config is ready, nothing to write"]
    assert harness.boot_lines(lines) == [lines[2]]


def test_crash_lines_take_a_traceback_and_both_allocation_spellings() -> None:
    lines = ["Traceback (most recent call last):", "SYSTEM memory allocation failed, allocating 512 bytes", "MemoryError:", "WIFI connected"]
    assert harness.crash_lines(lines) == lines[:3]


def test_observe_during_returns_the_lines_before_during_and_after_the_action(monkeypatch: pytest.MonkeyPatch) -> None:
    # "after" is printed only once observe_during() has entered its tail after the action, so reading it proves the
    # tail outlived the action; every phase change waits for the tail's read, never on a clock.
    monkeypatch.setattr(harness, "_OBSERVE_TAIL_STEP_S", 0.01)
    board = _PhasedBoard()

    def tail_after(seconds: float) -> None:
        assert seconds == harness._OBSERVE_TAIL_AFTER_S
        board.enter("after")

    def action() -> str:
        board.enter("before")
        board.enter("during")
        return "done"

    monkeypatch.setattr(time, "sleep", tail_after)
    result, lines = harness.observe_during(board, action)  # type: ignore[arg-type]
    assert result == "done" and lines == ["before", "during", "after"]


def test_observe_during_raises_when_its_log_tail_broke(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(harness, "_OBSERVE_TAIL_AFTER_S", 0.0)
    broke = threading.Event()

    class Broken:
        def tail_log(self, duration_s: float, baudrate: int = 115200) -> "list[str]":
            broke.set()
            raise harness.HardwareNotAvailableError("port gone")

    with pytest.raises(harness.HardwareTestFailureError, match="port gone"):
        harness.observe_during(Broken(), lambda: broke.wait(_STOP_WAIT_S))  # type: ignore[arg-type]


def test_wait_for_boot_returns_once_a_boot_line_arrived_and_names_the_debug_level_need_otherwise(clock: _Clock) -> None:
    lines = harness.wait_for_boot(_LogBoard([["boot"], ["FRAM SPI FRAM Driver Setup complete"]]), 60.0)  # type: ignore[arg-type]
    assert lines == ["boot", "FRAM SPI FRAM Driver Setup complete"]
    assert clock.now == pytest.approx(2 * harness._OBSERVE_TAIL_STEP_S), "it read on after the boot line"
    with pytest.raises(TimeoutError, match="DebugLevel >= 3"):
        harness.wait_for_boot(_LogBoard([["CFGMGR_SYSTEM loading"]]), 2.5)  # type: ignore[arg-type]
    assert clock.now == pytest.approx(2 * harness._OBSERVE_TAIL_STEP_S + 2.5), "the tail ran past its bound"


def test_retryable_picotool_exit_is_the_no_bootsel_device_status_only() -> None:
    assert harness._retryable_picotool_exit(249) is True
    assert [code for code in (0, 1, 248, 250, 255) if harness._retryable_picotool_exit(code)] == []


@pytest.mark.parametrize(("exits", "loads", "outcome"), [([249, 249, 0], 3, "flashed"), ([1], 1, "raises"), ([249, 2], 2, "raises"), ([249] * 5, 5, "raises")])
def test_reflash_retries_only_while_no_bootsel_device_is_enumerated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, exits: "list[int]", loads: int, outcome: str) -> None:
    calls: list[str] = []

    class Board:
        def __init__(self) -> None:
            self.recovery_events: list[str] = []

        def is_device_present(self) -> bool:
            return True

        def enter_bootloader(self) -> None:
            calls.append("bootloader")

    def run(argv: "list[str]", **_kwargs: object) -> object:
        calls.append(" ".join(argv[:3]))
        return type("Done", (), {"returncode": exits.pop(0), "stdout": "", "stderr": ""})()

    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(time, "sleep", lambda _s: None)
    monkeypatch.setattr(harness, "wait_for_boot", lambda _board, _timeout: ["config is ready"])
    board = Board()
    if outcome == "raises":
        with pytest.raises(harness.HardwareTestFailureError, match=r"picotool load .* failed"):
            harness.reflash(board, tmp_path / "image.uf2")  # type: ignore[arg-type]
    else:
        harness.reflash(board, tmp_path / "image.uf2")  # type: ignore[arg-type]
    assert calls == ["bootloader"] + ["sudo picotool load"] * loads
    assert len(board.recovery_events) == loads - 1, board.recovery_events


def test_the_no_sync_rule_sees_a_list_without_it() -> None:
    assert _no_sync_offenders(ast.parse('cmd = ["uv", "run", "mpremote"]\nok = ["uv", "run", "--no-sync", "x"]\n')) == ["line 1: ['uv', 'run', 'mpremote']"]


@pytest.mark.parametrize("module", HOST_MODULES, ids=lambda p: str(p.relative_to(TESTS_HARDWARE)))
def test_no_hardware_module_runs_uv_without_no_sync(module: Path) -> None:
    # Nothing inside a hardware run syncs, so a lock change or a third party's outage cannot read as a board fault.
    assert _no_sync_offenders(_module_tree(module)) == [], module.name


def test_parse_facts_reads_every_fact_and_needs_done() -> None:
    output = 'boot noise\nFACT count=3\nFACT values={"a": [1, 2.5], "b": null}\nDONE\n'
    assert harness.parse_facts(output) == {"count": 3, "values": {"a": [1, 2.5], "b": None}}
    with pytest.raises(harness.HardwareTestFailureError, match="no DONE line"):
        harness.parse_facts("FACT count=3\n")
    assert harness.parse_facts("FACT count=3\n", allow_missing_done=True) == {"count": 3}


@pytest.mark.parametrize("line", ["FACT count", "FACT =3", "FACT x=nan", "FACT x=1\nFACT x=2"])
def test_parse_facts_refuses_a_malformed_repeated_or_non_json_fact(line: str) -> None:
    with pytest.raises(harness.HardwareTestFailureError):
        harness.parse_facts(line + "\nDONE\n")


def test_render_inlines_facts_extras_includes_and_the_device_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(harness, "RENDERED_SCRIPTS_DIR", tmp_path / "out")
    script = tmp_path / "probe.py"
    script.write_text(
        "import json\n"
        "# @include _shared/facts.py\n"
        "# @include _shared/facts.py\n"
        "import _bench_device as device  # rendered: the bench device's generated module\n"
        'BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py\n'
        "fact('module', BENCH['device_module'])\n",
        encoding="utf-8",
    )
    rendered = harness.render_device_script(script, SEAM=3).read_text(encoding="utf-8")
    facts = bench_facts.build(harness.bench_device())
    assert f"import {facts['device_module']} as device  # rendered: the bench device's generated module\n" in rendered
    assert rendered.count("def fact(") == 1, "an include inlined twice"
    bench = next(line for line in rendered.splitlines() if line.startswith("BENCH"))
    assert ast.literal_eval(bench.split("=", 1)[1].split("  # rendered")[0].strip()) == {**facts, "SEAM": 3}
    assert "# @include" not in rendered and "_bench_device" not in rendered


def test_render_leaves_a_plain_script_alone_and_refuses_extras_it_cannot_receive(tmp_path: Path) -> None:
    script = tmp_path / "plain.py"
    script.write_text("print('hi')\n", encoding="utf-8")
    assert harness.render_device_script(script) == script
    with pytest.raises(ValueError, match="no BENCH line"):
        harness.render_device_script(script, SEAM=1)


def test_render_refuses_an_extra_shadowing_a_board_fact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(harness, "RENDERED_SCRIPTS_DIR", tmp_path / "out")
    script = tmp_path / "probe.py"
    script.write_text('BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py\n', encoding="utf-8")
    with pytest.raises(ValueError, match="shadow"):
        harness.render_device_script(script, depth=1)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_bench_facts_build_for_every_device_as_a_literal_the_board_reads_back(device: str) -> None:
    facts = bench_facts.build(device)
    assert ast.literal_eval(repr(facts)) == facts
    assert facts["device_module"] == f"sensortask_{device}"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_bench_route_set_is_the_rest_references_get_routes(monkeypatch: pytest.MonkeyPatch, repo_root: Path, device: str) -> None:
    reference = json.loads((repo_root / "build" / "generated_src" / "api" / f"{device}.json").read_text(encoding="utf-8"))
    expected = [route["path"] for route in reference["routes"] if route["method"] == "GET"]
    assert list(_bench_routes()) == expected and "/notification" in expected
    monkeypatch.setattr(harness, "_api_reference", lambda _device: reference)
    assert harness.get_routes() == expected


def test_get_routes_adds_the_page_and_filters_by_streaming(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    stub = {"routes": [{"method": "GET", "path": "/measurements"}, {"method": "GET", "path": "/status"}, {"method": "GET", "path": "/zz-extra"}, {"method": "PUT", "path": "/system"}]}
    (tmp_path / "ref.json").write_text(json.dumps(stub), encoding="utf-8")
    monkeypatch.setattr(harness, "_api_reference", lambda _device: json.loads((tmp_path / "ref.json").read_text(encoding="utf-8")))
    assert harness.get_routes() == ["/measurements", "/status", "/zz-extra"]
    assert harness.get_routes(json_only=False) == ["/measurements", "/status", "/zz-extra", "/"]
    assert harness.get_routes("PUT") == ["/system"]
    streaming = harness._streaming_paths("GET")
    assert {"/measurements", "/status"} <= streaming and "/zz-extra" not in streaming, streaming
    assert harness.get_routes(streams=True) == ["/measurements", "/status"]
    assert harness.get_routes(streams=False) == ["/zz-extra"]


def test_the_bench_toml_facts_come_from_the_toml_and_src(repo_root: Path) -> None:
    table = tomllib.loads(harness.device_toml().read_text(encoding="utf-8"))["device"]
    wifi = extract_field_schemas(repo_root / "src" / "asy_wifi_service.py")
    assert harness.hotspot_password() == table["hotspot_password"]
    assert harness.dut_hostname_candidates() == (table["hostname"], wifi["Hostname"][1])
    assert harness.configured_max_connections() == harness.configured_max_connections(harness.bench_device())


@pytest.mark.parametrize(("src_file", "field"), [("asy_ntp_client.py", "NTPHost"), *_pushed_fields()], ids=str)
def test_schema_default_is_the_default_each_src_tuple_declares(src_file: str, field: str) -> None:
    # The repair target of an aborted run's leftover: the NTP host the fault test garbles and every field the push tests
    # write, each against an ast read of its src/ tuple apart from buildgen's.
    assert not src_file.startswith("<"), src_file
    assert harness.schema_default(src_file, field) == _declared_default(src_file, field)


def test_schema_default_refuses_a_field_the_file_does_not_declare() -> None:
    with pytest.raises(harness.HardwareNotAvailableError, match=r"src/asy_ntp_client\.py declares no schema field 'NoSuchField'"):
        harness.schema_default("asy_ntp_client.py", "NoSuchField")


@pytest.mark.parametrize("module", REPAIR_MODULES, ids=lambda p: p.name)
def test_every_leftover_repair_reads_its_target_through_schema_default(module: Path) -> None:
    # A leftover is repaired to the product default as harness.schema_default() reads it (checked above against src/),
    # never to a literal of the test's own nor to a refusal to run.
    calls = [node for node in ast.walk(_module_tree(module)) if isinstance(node, ast.Call) and _call_name(node) == "schema_default"]
    assert calls, f"{module.name} repairs no leftover through harness.schema_default()"


def test_fram_backed_logger_names_are_buildgens_expected_facts(repo_root: Path) -> None:
    expected = json.loads((repo_root / "build" / "generated_src" / f"sensortask_{harness.bench_device()}_expected.json").read_text(encoding="utf-8"))
    assert harness.fram_backed_logger_names() == expected["fram_backed_loggers"]


@pytest.mark.parametrize(
    ("source", "found"),
    [
        ("import http_client\nimport threading\ndef worker():\n    try:\n        http_client.fetch('h', 80, 'GET', '/')\n    except OSError:\n        pass\nthreading.Thread(target=worker)\n", ["worker (line 5)"]),
        ("import http_client\nimport threading\ndef worker():\n    http_client.fetch('h', 80, 'GET', '/')\nthreading.Thread(target=worker)\n", ["worker (line 4)"]),
        ("import http_client\nimport threading\ndef get():\n    return http_client.fetch('h', 80, 'GET', '/')\ndef worker():\n    get()\nthreading.Thread(None, worker)\n", ["worker (line 6)"]),
        ("import http_client\nimport threading\nfrom error_log_helpers import get_errcount\ndef worker():\n    get_errcount('h')\nthreading.Thread(target=worker)\n", ["worker (line 5)"]),
        ("import http_client\nimport threading\ndef fetch():\n    return http_client.fetch('h', 80, 'GET', '/')\nthreading.Thread(target=lambda: fetch())\n", ["lambda (line 5)"]),
        ("import http_client\nimport threading\ndef worker():\n    try:\n        http_client.fetch('h', 80, 'GET', '/')\n    except (OSError, http_client.HTTP_ERROR):\n        pass\nthreading.Thread(target=worker)\n", []),
        ("import http_client\nimport threading\ndef get():\n    try:\n        return http_client.fetch('h', 80, 'GET', '/')\n    except Exception:\n        return None\nthreading.Thread(None, get)\n", []),
    ],
    ids=["catches-only-oserror", "try-less", "positional-target-via-helper", "helper-module-fetch", "lambda-target", "guarded", "guarded-helper"],
)
def test_the_worker_rule_sees_every_unguarded_fetch_a_thread_target_makes(source: str, found: "list[str]") -> None:
    assert _unguarded_fetches(ast.parse(source), _helper_raisers()) == found


@pytest.mark.parametrize("module", HOST_MODULES, ids=lambda p: str(p.relative_to(TESTS_HARDWARE)))
def test_every_hardware_thread_worker_survives_a_cut_off_answer(module: Path) -> None:
    assert _unguarded_fetches(_module_tree(module), _helper_raisers()) == [], f"{module.name}: catch (OSError, http_client.HTTP_ERROR) around the fetch and record the failure"


@pytest.mark.parametrize(
    ("source", "found"),
    [
        ("def test_x():\n    t = threading.Thread(target=f)\n    t.start()\n", ["test_x (line 1)"]),
        ("def test_x():\n    t = threading.Thread(target=f)\n    t.start()\n    t.join()\n", ["test_x (line 1)"]),
        ("def test_x():\n    t = threading.Thread(target=f)\n    try:\n        t.start()\n    finally:\n        stop.set()\n        t.join(5)\n", []),
        ("def end(ts):\n    for t in ts:\n        t.join(5)\ndef test_x():\n    ts = [threading.Thread(target=f)]\n    try:\n        ts[0].start()\n    finally:\n        end(ts)\n", []),
        ("@pytest.fixture\ndef load():\n    t = threading.Thread(target=f)\n    t.start()\n    yield t\n    t.join(5)\n", []),
    ],
    ids=["unjoined", "joined-only-on-success", "joined-in-finally", "joined-through-a-helper", "fixture-teardown"],
)
def test_the_join_rule_sees_a_started_thread_no_finally_joins(source: str, found: "list[str]") -> None:
    assert _unjoined_starts(ast.parse(source)) == found


@pytest.mark.parametrize("module", HOST_MODULES, ids=lambda p: str(p.relative_to(TESTS_HARDWARE)))
def test_every_started_hardware_thread_is_joined_on_every_path(module: Path) -> None:
    assert _unjoined_starts(_module_tree(module)) == [], f"{module.name}: stop and join the thread in a finally"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_website_check_reads_the_union_of_every_errcount_group(repo_root: Path, device: str) -> None:
    # Against the definitions the build wrote, read here apart from the check's own in-process derivation.
    built = json.loads((repo_root / "build" / "generated_src" / "definitions" / f"{device}.json").read_text(encoding="utf-8"))
    groups = [group for section in built["sections"] for group in section.get("groups", []) if group.get("kind") == "errcount"]
    union = list(dict.fromkeys(module["key"] for group in groups for module in group["modules"]))
    assert len(groups) >= 2 and website_identity._errcount_keys(device) == union


def test_the_website_check_names_its_device() -> None:
    # A required keyword: a page check that silently assumed one board would pass on the wrong board's build.
    parameter = inspect.signature(website_identity.assert_page_is_this_devices_build).parameters["device"]
    assert (parameter.kind, parameter.default) == (inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.empty)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_configured_max_connections_is_the_builds_own_ceiling_for_every_device(device: str) -> None:
    assert harness.configured_max_connections(device) == device_max_connections(device_toml(device), harness.REPO_ROOT / "src")


def test_a_probe_whose_connections_are_all_still_open_stands() -> None:
    harness._assert_probe_held([_HeldSocket(TimeoutError), _HeldSocket(TimeoutError)], time.monotonic())  # type: ignore[list-item]


@pytest.mark.parametrize(
    ("outcome", "shown"),
    [(b"", "b''"), (b"HTTP/1.0 408", "HTTP/1.0 408"), (ConnectionResetError, "<reset>")],
)
def test_a_probe_with_any_connection_closed_answered_or_reset_is_voided_by_index(outcome: bytes | type[OSError], shown: str) -> None:
    # A FIN, an answer or an RST each mean the connection was not held when the refusal landed.
    with pytest.raises(AssertionError, match=r"connection 1 was no longer held") as info:
        harness._assert_probe_held([_HeldSocket(TimeoutError), _HeldSocket(outcome)], time.monotonic())  # type: ignore[list-item]
    assert shown in str(info.value), info.value
