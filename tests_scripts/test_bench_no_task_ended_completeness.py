"""Every hardware test that injects a fault also asserts no task ended under it - "no Traceback" alone passed the NTP
give-up that restarted a task a minute and rebooted every four (SPECIFICATION.md C.7.2). The scan follows methods,
helpers and fixtures and covers the flash tier's fault scripts; plus the helper's own contract on a faked /status."""

import ast
import sys
from functools import cache
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests_hardware"))
import error_log_helpers

_TESTS_HARDWARE = Path(__file__).resolve().parents[1] / "tests_hardware"
# BenchBridge calls that put a real fault on the DUT's network. kick_all_stations() is absent on
# purpose: it is the reconnect nudge every hard_reset() test uses, not a fault.
_FAULT_INJECTORS = frozenset({"ap_down", "inject_network_degradation", "block_udp_ports", "redirect_udp_port_to_local", "start_udp_source_capture"})
# Calls that satisfy the check: the helper itself, or a helper that runs it before a reset. recover_by_reset() is not
# one: it resets without asserting first.
_CHECKERS = frozenset({"assert_no_task_ended", "_restore_ssid_over"})
_EXEMPT: "dict[str, str]" = {}
# Helpers whose injector call is join mechanics, so reaching them is no fault: the session's stale-credential recovery
# downs the AP only to scan for and join the DUT's own hotspot (agent, 2026-10-14).
_JOIN_MECHANICS = {"_recover_stale_dut_credentials": "ap_down() frees the single radio to scan for the DUT's hotspot"}
# The flash tier's fault-making device scripts: a test running one reaches no production SYSTEM log (an isolated
# script), so the script reports its own SYSTEM logger as a fact (a key naming "system") for the host to assert, unless
# the script and its includes start no task at all (none can end then; a task starter added later re-arms the check).
_FLASH_FAULT_SCRIPTS = {
    "fram_cs_hijack_fault_injection_and_recovery.py": "drives the FRAM chip-select from a second pin mid-transfer",
    "uart_crossover_recovery.py": "silences and desyncs the UART link",
    "fram_reset_race_during_write_seed_and_race.py": "resets the board in the middle of a FRAM write",
    "fram_error_log_reset_race_seed_and_race.py": "resets the board in the middle of an error-log write",
}

Fn = ast.FunctionDef | ast.AsyncFunctionDef


# Node -> the names it calls, walked once (the scan asks again for every module and fixed-point round); the entry keeps
# its node alive, so an id is never reused while it is cached.
_CALLED: "dict[int, tuple[ast.AST, frozenset[str]]]" = {}


def _called(fn: ast.AST) -> "frozenset[str]":
    if id(fn) not in _CALLED:
        _CALLED[id(fn)] = (fn, frozenset(n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "") for n in ast.walk(fn) if isinstance(n, ast.Call)))
    return _CALLED[id(fn)][1]


def _is_fixture(fn: Fn) -> bool:
    return any("fixture" in ast.unparse(d) for d in fn.decorator_list)


def _functions(tree: ast.Module) -> "list[Fn]":
    # Module-level functions and the methods of Test* classes.
    found: list[Fn] = [n for n in tree.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]
    for cls in [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name.startswith("Test")]:
        found += [n for n in cls.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]
    return found


def _injecting(functions: "dict[str, Fn]") -> "set[str]":
    # Names whose body calls an injector, directly or through another named function (to a fixed point).
    injecting = {name for name, fn in functions.items() if _called(fn) & _FAULT_INJECTORS and name not in _JOIN_MECHANICS}
    while True:
        more = {name for name, fn in functions.items() if name not in injecting and name not in _JOIN_MECHANICS and _called(fn) & injecting}
        if not more:
            return injecting
        injecting |= more


def _asserts_after_yield(fn: Fn) -> bool:
    # A fixture's teardown (after its yield) that asserts no task ended.
    yields = [n.lineno for n in ast.walk(fn) if isinstance(n, ast.Yield | ast.YieldFrom)]
    return bool(yields) and any(isinstance(n, ast.Call) and n.lineno > min(yields) and (getattr(n.func, "attr", None) or getattr(n.func, "id", "")) in _CHECKERS for n in ast.walk(fn))


def _injector_sites(nodes: "list[ast.AST]", path: Path) -> "set[tuple[str, int]]":
    return {(path.name, n.lineno) for node in nodes for n in ast.walk(node) if isinstance(n, ast.Call) and getattr(n.func, "attr", None) in _FAULT_INJECTORS}


def bench_findings(root: Path) -> "tuple[list[tuple[str, str, bool]], set[tuple[str, int]]]":
    # (each fault test with whether it checks, the injector call sites outside every function the scan sees).
    # bench_control.py defines the injectors, so its own calls between them are no test's fault.
    modules = {path: ast.parse(path.read_text(encoding="utf-8")) for path in [*sorted(root.glob("*.py")), *sorted((root / "bench").glob("*.py"))] if path.name != "bench_control.py"}
    shared = {fn.name: fn for path, tree in modules.items() if path.parent == root for fn in _functions(tree)}
    found: list[tuple[str, str, bool]] = []
    unseen: set[tuple[str, int]] = set()
    for path, tree in modules.items():
        local = _functions(tree)
        unseen |= _injector_sites([tree], path) - _injector_sites(list(local), path)
        if path.parent == root or not path.name.startswith("test_"):
            continue
        functions = {**shared, **{fn.name: fn for fn in local}}
        injecting = _injecting(functions)
        fixtures = {name for name in injecting if _is_fixture(functions[name]) and not _asserts_after_yield(functions[name])}
        tests = [f for f in local if f.name.startswith("test_") and (f.name in injecting or {a.arg for a in f.args.args} & fixtures)]
        found.extend((path.name, fn.name, bool(_called(fn) & _CHECKERS)) for fn in tests)
    return found, unseen


@cache
def _tier() -> "tuple[list[tuple[str, str, bool]], set[tuple[str, int]], list[tuple[str, str, bool]]]":
    # The real tier's findings, read once for the three tests below.
    found, unseen = bench_findings(_TESTS_HARDWARE)
    return found, unseen, flash_findings(_TESTS_HARDWARE)


def flash_findings(root: Path) -> "list[tuple[str, str, bool]]":
    # Each flash test running a fault script, with whether the script reports its SYSTEM logger as a fact.
    reports = {name: _reports_system(root / "device_scripts" / name) for name in _FLASH_FAULT_SCRIPTS if (root / "device_scripts" / name).is_file()}
    found: list[tuple[str, str, bool]] = []
    for path in sorted((root / "flash").glob("test_*.py")):
        for fn in [f for f in _functions(ast.parse(path.read_text(encoding="utf-8"))) if f.name.startswith("test_")]:
            texts = {n.value for n in ast.walk(fn) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
            ran = [name for name in reports if any(t.endswith(name) for t in texts)]
            if ran:
                found.append((path.name, fn.name, all(reports[name] for name in ran)))
    return found


_TASK_STARTERS = frozenset({"create_task", "gather", "build_system", "start_tasks", "run_setups", "main"})


def _reports_system(script: Path) -> bool:
    source = script.read_text(encoding="utf-8")
    calls = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "fact"]
    if any(c.args and isinstance(c.args[0], ast.Constant) and "system" in str(c.args[0].value).lower() for c in calls):
        return True
    included = [script.parent / line.split()[-1] for line in source.splitlines() if line.startswith("# @include ")]
    trees = [ast.parse(path.read_text(encoding="utf-8")) for path in [script, *included]]
    return not any(isinstance(n, ast.Call) and (getattr(n.func, "id", "") or getattr(n.func, "attr", "")) in _TASK_STARTERS for tree in trees for n in ast.walk(tree))


def test_the_scan_reaches_every_injector_call_site() -> None:
    # Derived, not a floor: every injector call in the tier sits in a test, a helper a test reaches, or a fixture.
    found, unseen, _ = _tier()
    names = {name for _file, name, _ok in found}
    assert "test_real_wifi_outage_and_recovery_while_in_normal_sta_mode" in names
    assert not unseen, f"injector calls outside every function the scan reads (file, line): {sorted(unseen)}"


def test_every_fault_injecting_test_asserts_no_task_ended() -> None:
    found, _, flash = _tier()
    missing = [f"bench/{file}::{name}" for file, name, ok in found if not ok and name not in _EXEMPT]
    missing += [f"flash/{file}::{name}" for file, name, ok in flash if not ok and name not in _EXEMPT]
    assert not missing, "these tests inject a fault but check no task ended (bench: assert_no_task_ended(); flash: the script's SYSTEM fact): " + ", ".join(missing)


def test_every_exemption_still_names_a_real_fault_test() -> None:
    found, _, flash = _tier()
    names = {name for _file, name, _ok in found + flash}
    assert set(_EXEMPT) <= names, f"stale exemptions: {sorted(set(_EXEMPT) - names)}"
    scripts = {p.name for p in (_TESTS_HARDWARE / "device_scripts").glob("*.py")}
    assert set(_FLASH_FAULT_SCRIPTS) <= scripts, f"_FLASH_FAULT_SCRIPTS names a script that is gone: {sorted(set(_FLASH_FAULT_SCRIPTS) - scripts)}"


def test_a_fault_script_passes_by_its_system_fact_or_by_starting_no_task(tmp_path: Path) -> None:
    (tmp_path / "_shared").mkdir()
    (tmp_path / "_shared" / "spawn.py").write_text("def go(loop):\n    loop.create_task(None)\n", encoding="utf-8")
    cases = {"fact('system_entries', [])\nasyncio.create_task(x())\n": True, "asyncio.run(_main())\n": True, "asyncio.create_task(x())\n": False, "# @include _shared/spawn.py\nasyncio.run(_main())\n": False}
    for index, (source, passes) in enumerate(cases.items()):
        (tmp_path / f"s{index}.py").write_text(source, encoding="utf-8")
        assert _reports_system(tmp_path / f"s{index}.py") is passes, source


def test_the_scan_follows_methods_helpers_and_fixtures(tmp_path: Path) -> None:
    (tmp_path / "bench").mkdir()
    (tmp_path / "shared.py").write_text("def outage(bench):\n    bench.ap_down()\n", encoding="utf-8")
    (tmp_path / "bench" / "test_bite.py").write_text(
        "import pytest\n\n\n@pytest.fixture\ndef degraded(bench):\n    bench.inject_network_degradation()\n    yield\n\n\n"
        "class TestGroup:\n    def test_method(self, bench):\n        outage(bench)\n\n\n"
        "def test_fixture_user(degraded):\n    pass\n\n\ndef test_checked(bench, dut_ip):\n    bench.block_udp_ports()\n    assert_no_task_ended(dut_ip, 'x')\n",
        encoding="utf-8",
    )
    found, unseen = bench_findings(tmp_path)
    assert sorted(found) == [("test_bite.py", "test_checked", True), ("test_bite.py", "test_fixture_user", False), ("test_bite.py", "test_method", False)]
    assert unseen == set()
    (tmp_path / "bench" / "test_hidden.py").write_text("class Helper:\n    def go(self, bench):\n        bench.ap_down()\n", encoding="utf-8")
    assert bench_findings(tmp_path)[1] == {("test_hidden.py", 3)}


@pytest.mark.parametrize(
    ("system_entry", "passes"),
    [
        ({"counter": 0, "history": []}, True),
        (None, False),  # a missing SYSTEM entry is a changed /status shape: it fails closed
        ({"counter": 1, "history": [{"num": error_log_helpers.code("E", "TASK_RETURNED"), "type": "E"}]}, False),  # a task returned
        ({"counter": 1, "history": [{"num": error_log_helpers.code("E", "TASK_RAISED"), "type": "E"}]}, False),  # a task ended with an exception
        ({"counter": 1, "history": [{"num": error_log_helpers.code("E", "TASK_BUDGET_REBOOT"), "type": "E"}]}, False),  # the budget rebooted the board
    ],
)
def test_assert_no_task_ended_reads_the_system_log(monkeypatch: pytest.MonkeyPatch, system_entry: "dict[str, object] | None", *, passes: bool) -> None:
    errcount = {"NTP": {"counter": 3, "history": []}}  # other modules' failures are not this check's business
    if system_entry is not None:
        errcount["SYSTEM"] = system_entry
    monkeypatch.setattr(error_log_helpers, "get_errcount", lambda _ip: errcount)
    if passes:
        error_log_helpers.assert_no_task_ended("10.0.0.2", "ctx")
    else:
        with pytest.raises(AssertionError, match="ctx: a task ended" if system_entry is not None else "'SYSTEM' is not in /status errcount"):
            error_log_helpers.assert_no_task_ended("10.0.0.2", "ctx")
