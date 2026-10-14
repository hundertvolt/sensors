"""Tests scripts/_digital_twin_scenarios.py's frame without booting a twin: the registry (a goal per scenario, known
driver filters, nothing from tests/), the selection's named skips and deselections, which scenarios share a boot and in
what order, the idle check between them, the port band, the command line's refusals, the run record and each boot's end."""

import ast
import inspect
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from _devices import DEVICE_NAMES
from _script_loader import load_script_module

from buildgen.buildspec import BUS_ATTACHED_DRIVERS

_REPO_ROOT = Path(__file__).resolve().parent.parent
_HARNESS = _REPO_ROOT / "scripts" / "_digital_twin_scenarios.py"


def _boot_once(harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, log: str, exited: "int | None", shutdown_code: int = 0, claim: bool = False) -> "list[str]":
    # One Context.boot() over a stub twin: `exited` is its exit code if it ended on its own, else it runs until shut down.
    log_path = tmp_path / "twin.log"
    log_path.write_text(log)
    run = SimpleNamespace(proc=SimpleNamespace(poll=lambda: exited, returncode=exited), log_path=log_path, killed=False, state_dir=tmp_path)
    monkeypatch.setattr(harness, "spawn", lambda _launch, **_kw: run)
    monkeypatch.setattr(harness, "wait_until_serving", lambda *_a: None)
    monkeypatch.setattr(harness, "shutdown", lambda _run, _label: shutdown_code)
    monkeypatch.setattr(harness, "wait_exit", lambda _run, _timeout: exited)
    ctx = harness.Context("fixture-device", "/nonexistent", -1, tmp_path, (), iter([20000]), "fixture")
    with ctx.boot() as twin:
        twin.exit_claimed = claim
    return [str(failure) for failure in ctx.failures]


def _harness(*args: str, env: "dict[str, str] | None" = None) -> "subprocess.CompletedProcess[str]":
    return subprocess.run([sys.executable, str(_HARNESS), *args], capture_output=True, text=True, check=False, cwd=_REPO_ROOT, timeout=60, env=env)


def _item(harness: ModuleType, name: str, *, shared: bool = True, moves: "tuple[str, ...]" = ()) -> object:
    return harness.Scenario(name, lambda _ctx: None, "A goal.", "fixture", (), False, False, shared, moves)


def _shared_stub(harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, counters: "list[dict[str, int]]") -> "list[object]":
    # Stub twins for a SharedBoot, each spawn recorded in the list returned: every slot reads free, and each GET /status
    # read takes the next of `counters`, each source's history one warning.
    spawned: list[object] = []
    log_path = tmp_path / "twin.log"
    log_path.write_text(_SHUTDOWN_LINE + "\n")

    def spawn(_launch: object, **_kw: object) -> object:
        run = SimpleNamespace(proc=SimpleNamespace(poll=lambda: None, returncode=None), log_path=log_path, killed=False, state_dir=tmp_path)
        spawned.append(run)
        return run

    reads = iter([{name: {"counter": value, "history": [{"type": "W", "num": 48}]} for name, value in read.items()} for read in counters])
    monkeypatch.setattr(harness, "spawn", spawn)
    monkeypatch.setattr(harness, "wait_until_serving", lambda *_a: None)
    monkeypatch.setattr(harness, "shutdown", lambda _run, _label: 0)
    monkeypatch.setattr(harness, "_error_table", lambda _port: next(reads))
    monkeypatch.setattr(harness, "_accept_queue", lambda _port: 0)
    monkeypatch.setattr(harness.Twin, "drained", lambda _self, _timeout_s=0: True)
    return spawned


def test_every_scenario_states_its_goal_and_a_known_device_filter(harness: ModuleType) -> None:
    assert harness.SCENARIOS, "the registry is empty - nothing would run"
    for item in harness.SCENARIOS.values():
        assert item.goal and item.goal[0].isupper() and item.goal.endswith("."), f"{item.name}: goal {item.goal!r}"
        assert set(item.drivers) <= BUS_ATTACHED_DRIVERS, f"{item.name} filters on {item.drivers}, not bus-attached drivers"


def test_a_scenario_without_a_goal_is_refused_at_registration(harness: ModuleType) -> None:
    with pytest.raises(ValueError, match="no goal docstring"):
        harness.scenario("zz_no_goal", family="fixture")(lambda _ctx: None)
    assert "zz_no_goal" not in harness.SCENARIOS


def test_a_name_registered_twice_is_refused(harness: ModuleType) -> None:
    name = next(iter(harness.SCENARIOS))

    def body(_ctx: object) -> None:
        """A second body under a taken name."""

    with pytest.raises(ValueError, match="registered twice"):
        harness.scenario(name, family="fixture")(body)


def test_the_harness_imports_nothing_from_tests() -> None:
    tree = ast.parse(_HARNESS.read_text())
    imported = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module] + [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    assert not [m for m in imported if m == "tests" or m.startswith("tests.")], imported


def test_a_shared_port_53_deselects_the_dns_scenarios_by_reason(harness: ModuleType) -> None:
    exclusive = sorted(s.name for s in harness.SCENARIOS.values() if s.needs_exclusive_port_53)
    assert exclusive, "no scenario needs port 53 alone - the deselection rule has nothing to hold"
    chosen = {item.name: why for item, why in harness.select(DEVICE_NAMES[0], None, exclusive_port_53=False)}
    assert all(chosen[name] == "deselected: needs exclusive port 53 - run_digital_twin_ci.sh runs it" for name in exclusive), chosen
    assert all(why is None for item, why in harness.select(DEVICE_NAMES[0], None, exclusive_port_53=True) if item.needs_exclusive_port_53)


def test_a_device_without_a_scenarios_driver_skips_it_by_name(harness: ModuleType) -> None:
    device = next(d for d in DEVICE_NAMES if "isl29125" not in {driver for _k, driver, _e in harness._instances(d)})
    chosen = {item.name: why for item, why in harness.select(device, None, exclusive_port_53=True)}
    assert chosen["isl29125_config_put_during_get_loops"] == "skipped: device wires no isl29125", chosen


def test_only_selects_by_name_and_refuses_an_unknown_one(harness: ModuleType) -> None:
    name = next(iter(harness.SCENARIOS))
    assert [item.name for item, _why in harness.select(DEVICE_NAMES[0], frozenset({name}), exclusive_port_53=True)] == [name]
    done = _harness("--device", DEVICE_NAMES[0], "--only", "zz_not_a_scenario")
    assert done.returncode == 2 and "unknown scenario" in done.stderr, (done.returncode, done.stderr)


def test_an_unknown_device_is_a_usage_error() -> None:
    done = _harness("--device", "fixture-device")
    assert done.returncode == 2 and "not a generated device" in done.stderr, done.stderr


def test_exclusive_port_53_needs_the_callers_lock() -> None:
    env = {k: v for k, v in os.environ.items() if k != "SENSORS_PORT_LOCKS_HELD"}
    done = _harness("--device", DEVICE_NAMES[0], "--exclusive-port-53", env=env)
    assert done.returncode == 2 and "port 53's lock" in done.stderr, done.stderr


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_each_device_draws_from_its_own_block_of_the_harness_band(harness: ModuleType, port_bands: ModuleType, device: str) -> None:
    assert harness._band(device) == port_bands.band_for_device("_digital_twin_scenarios", device)


def test_the_run_record_names_each_scenarios_outcome(harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def ok(_ctx: object) -> None:
        """Passes."""

    def broken(_ctx: object) -> None:
        """Fails."""
        raise AssertionError("planted")

    registry = {name: harness.Scenario(name, body, (body.__doc__ or "").strip(), "fixture", drivers) for name, body, drivers in (("ok", ok, ()), ("broken", broken, ()), ("needs_isl", ok, ("isl29125",)))}
    monkeypatch.setattr(harness, "SCENARIOS", registry)
    device = next(d for d in DEVICE_NAMES if "isl29125" not in {driver for _k, driver, _e in harness._instances(d)})
    record = tmp_path / "record.json"
    assert harness.main(["--device", device, "--logs-dir", str(tmp_path / "logs"), "--run-record", str(record)]) == 1
    outcomes = {row["name"]: (row["outcome"], row["reason"]) for row in json.loads(record.read_text())}
    assert outcomes["ok"][0] == "passed"
    assert outcomes["broken"][0] == "failed" and "planted" in outcomes["broken"][1]
    assert outcomes["needs_isl"] == ("skipped", "device wires no isl29125")


def test_a_run_that_passed_nothing_is_no_pass(harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def ok(_ctx: object) -> None:
        """Passes."""

    monkeypatch.setattr(harness, "SCENARIOS", {"needs_isl": harness.Scenario("needs_isl", ok, "Passes.", "fixture", ("isl29125",))})
    device = next(d for d in DEVICE_NAMES if "isl29125" not in {driver for _k, driver, _e in harness._instances(d)})
    assert harness.main(["--device", device, "--logs-dir", str(tmp_path / "logs")]) == 1


_SHUTDOWN_LINE = (
    "digital_twin/run_generic_integration.py [fixture_device] shutdown: would_have_triggered_count=0 feed_count=1 largest_feed_gap_ms=1 "
    "mem_backup: r0=0x00000000,0x00000000,0x00000000,0x00000000 public_destinations_refused=0 flash_stall_longest_ms=0"
)


@pytest.fixture(scope="module")
def harness() -> ModuleType:
    return load_script_module(_HARNESS, "_digital_twin_scenarios")


@pytest.mark.parametrize(
    ("log", "exited", "shutdown_code", "claim", "expected"),
    [
        (_SHUTDOWN_LINE, None, 0, False, None),
        (_SHUTDOWN_LINE, None, 1, False, "the SIGINT shutdown ended"),
        ("booted\n", None, 0, False, "printed no shutdown line"),
        (_SHUTDOWN_LINE, 3, 0, False, "ended on its own mid-scenario"),
        (_SHUTDOWN_LINE, 3, 0, True, None),
    ],
    ids=["clean", "unclean shutdown", "no shutdown line", "unclaimed exit", "claimed exit"],
)
def test_every_boot_ends_cleanly_or_by_a_claimed_exit(harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, log: str, exited: "int | None", shutdown_code: int, claim: bool, expected: "str | None") -> None:
    failures = _boot_once(harness, tmp_path, monkeypatch, log=log, exited=exited, shutdown_code=shutdown_code, claim=claim)
    assert (failures == []) if expected is None else (len(failures) == 1 and expected in failures[0]), failures


def test_the_routes_come_from_the_service_table(harness: ModuleType) -> None:
    routes = harness._get_routes()
    assert {"/measurements", "/sensors", "/status", "/system", "/networking", "/notification"} <= set(routes), routes
    assert "/" not in routes


@pytest.fixture(scope="module")
def port_bands() -> ModuleType:
    sys.path.insert(0, str(_REPO_ROOT / "tests"))
    return load_script_module(_REPO_ROOT / "tests" / "_port_bands.py", "_port_bands")


def test_the_sharing_scenarios_that_run_go_first_each_part_in_registry_order(harness: ModuleType) -> None:
    chosen = [(_item(harness, "a", shared=False), None), (_item(harness, "b"), None), (_item(harness, "c"), "skipped: device wires no x"), (_item(harness, "d", shared=False), None), (_item(harness, "e"), None)]
    assert [item.name for item, _why in harness.run_order(chosen)] == ["b", "e", "a", "c", "d"]


def test_consecutive_sharing_scenarios_that_run_form_one_group(harness: ModuleType) -> None:
    ordered = [(_item(harness, "a"), None), (_item(harness, "b"), "skipped: device wires no x"), (_item(harness, "c"), None), (_item(harness, "d", shared=False), None), (_item(harness, "e"), None)]
    assert harness.shared_groups(ordered) == [["a", "c"], ["e"]]
    assert harness.shared_groups(harness.run_order(ordered)) == [["a", "c", "e"]]


def test_a_sharing_scenario_boots_once_with_no_arguments_but_the_slot_lines(harness: ModuleType) -> None:
    # The selection rule read off each body: one boot, nothing passed but *_CONN, no system command, no PUT but an empty
    # one, no planted state; any other body boots its own twin.
    forbidden = {"_system_cmd", "_config_write", "_two_at_once", "_save_fram_evidence", "_exits_with", "_reason_after"}
    problems = []
    for item in harness.SCENARIOS.values():
        if not item.shared:
            continue
        tree = ast.parse(inspect.getsource(item.body))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
        boots = [c for c in calls if isinstance(c.func, ast.Attribute) and c.func.attr == "boot"]
        args_ok = all(not b.keywords and (not b.args or ast.unparse(b) == "ctx.boot(*_CONN)") for b in boots)
        used = {c.func.id for c in calls if isinstance(c.func, ast.Name)} & forbidden
        puts = [ast.unparse(c) for c in calls if isinstance(c.func, ast.Name) and c.func.id == "_request" and any(isinstance(a, ast.Constant) and a.value == "PUT" for a in c.args) and not (len(c.args) > 3 and isinstance(c.args[3], ast.Dict) and not c.args[3].keys)]
        if len(boots) != 1 or not args_ok or used or puts:
            problems.append(f"{item.name}: boots {[ast.unparse(b) for b in boots]}, calls {sorted(used)}, PUTs {puts}")
        logging = {c.func.id for c in calls if isinstance(c.func, ast.Name)} & {"_still_serving", "_flaky"}  # a refusal or a hang-up each logs
        if logging and "WEBSERVER" not in item.moves:
            problems.append(f"{item.name}: calls {sorted(logging)} but does not state the WEBSERVER entries they log")
    assert not problems, problems
    assert sum(item.shared for item in harness.SCENARIOS.values()) >= 1, "no scenario shares a boot - the rule has nothing to hold"


def test_moved_error_sources_on_an_own_boot_are_refused_at_registration(harness: ModuleType) -> None:
    def body(_ctx: object) -> None:
        """Moves an error count on its own boot."""

    with pytest.raises(ValueError, match="runs on its own boot"):
        harness.scenario("zz_moves_alone", family="fixture", moves=("WEBSERVER",))(body)
    assert "zz_moves_alone" not in harness.SCENARIOS


def test_sharing_scenarios_run_on_one_twin_until_the_group_ends(harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spawned = _shared_stub(harness, tmp_path, monkeypatch, [{"WEBSERVER": 0}, {"WEBSERVER": 2}, {"WEBSERVER": 2}])
    shared = harness.SharedBoot(harness.Context("fixture-device", "/nonexistent", -1, tmp_path, (), iter(range(20000, 20010)), "fixture"))
    for name, moves, last in (("a", ("WEBSERVER",), False), ("b", (), True)):
        ctx = harness.Context("fixture-device", "/nonexistent", -1, tmp_path, (), iter([]), "fixture", shared=shared)
        with ctx.boot() as twin:
            assert twin is shared.twin
        assert shared.release(_item(harness, name, moves=moves), failed=False, last=last) == []
    assert len(spawned) == 1 and shared.twin is None


def test_an_idle_check_failure_names_the_scenario_and_the_next_boots_fresh(harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spawned = _shared_stub(harness, tmp_path, monkeypatch, [{"WEBSERVER": 0}, {"WEBSERVER": 1}, {"WEBSERVER": 0}])
    shared = harness.SharedBoot(harness.Context("fixture-device", "/nonexistent", -1, tmp_path, (), iter(range(20000, 20010)), "fixture"))
    with harness.Context("fixture-device", "/nonexistent", -1, tmp_path, (), iter([]), "fixture", shared=shared).boot():
        pass
    problems = shared.release(_item(harness, "moves_unstated"), failed=False, last=False)
    assert len(problems) == 1 and "idle check after moves_unstated" in problems[0] and "'WEBSERVER': (0, 1, [['W', 48]])" in problems[0], problems
    assert shared.twin is None
    with harness.Context("fixture-device", "/nonexistent", -1, tmp_path, (), iter([]), "fixture", shared=shared).boot() as twin:
        assert twin is shared.twin
    assert len(spawned) == 2


def test_a_held_slot_or_a_queued_connection_fails_the_idle_check(harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _shared_stub(harness, tmp_path, monkeypatch, [{}, {}])
    shared = harness.SharedBoot(harness.Context("fixture-device", "/nonexistent", -1, tmp_path, (), iter(range(20000, 20010)), "fixture"))
    monkeypatch.setattr(harness, "_DRAIN_WAIT_S", 0.0)
    monkeypatch.setattr(harness.Twin, "drained", lambda _self, _timeout_s=0: False)
    monkeypatch.setattr(harness, "_accept_queue", lambda _port: 1)
    with harness.Context("fixture-device", "/nonexistent", -1, tmp_path, (), iter([]), "fixture", shared=shared).boot():
        pass
    problems = shared.release(_item(harness, "holds"), failed=False, last=False)
    assert any("slot was still held" in p for p in problems) and any("1 connection(s) still in the accept queue" in p for p in problems), problems
    assert all(p.startswith("idle check after holds") for p in problems), problems


def test_a_sharing_scenario_asking_for_its_own_arguments_is_refused(harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spawned = _shared_stub(harness, tmp_path, monkeypatch, [{}])
    shared = harness.SharedBoot(harness.Context("fixture-device", "/nonexistent", -1, tmp_path, (), iter(range(20000, 20010)), "fixture"))
    ctx = harness.Context("fixture-device", "/nonexistent", -1, tmp_path, (), iter([]), "fixture", shared=shared)
    with pytest.raises(RuntimeError, match="boots once"), ctx.boot("--test-hold-closing-slot"):
        pass
    assert spawned == []


def test_the_accept_queue_is_read_from_the_listening_row(harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    table = tmp_path / "tcp"
    header = "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n"
    table.write_text(header + "   0: 0100007F:4E20 00000000:0000 0A 00000000:00000003 00:00000000 00000000     0        0 1\n   1: 0100007F:4E20 0100007F:9C40 01 00000000:00000000 00:00000000 00000000     0        0 2\n")
    monkeypatch.setattr(harness, "Path", lambda name: table if name == "/proc/net/tcp" else tmp_path / "absent")
    assert harness._accept_queue(0x4E20) == 3
    assert harness._accept_queue(0x4E21) is None


def test_every_scenario_names_its_family_as_a_literal() -> None:
    # The level-containment check reads each decorator's family= keyword by AST, so it is a string literal everywhere.
    tree = ast.parse(_HARNESS.read_text())
    decorators = [d for n in tree.body if isinstance(n, ast.FunctionDef) for d in n.decorator_list if isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "scenario"]
    families = [next((k.value for k in d.keywords if k.arg == "family"), None) for d in decorators]
    assert decorators and all(isinstance(f, ast.Constant) and isinstance(f.value, str) and f.value.isidentifier() for f in families), [ast.unparse(d) for d, f in zip(decorators, families, strict=True) if not isinstance(f, ast.Constant)]


def test_a_scenario_without_a_family_is_refused_at_registration(harness: ModuleType) -> None:
    def body(_ctx: object) -> None:
        """Names no family."""

    with pytest.raises(ValueError, match="names no family"):
        harness.scenario("zz_no_family", family="")(body)
    assert "zz_no_family" not in harness.SCENARIOS


def _runner_builds(tmp_path: Path, *args: str) -> "list[str]":
    # scripts/run_digital_twin_ci.sh run in a throwaway tree whose website build, uv and setcap only log their calls;
    # returns the build_website.sh argument lists, one line each.
    root, stub_bin, calls = tmp_path / "repo", tmp_path / "stub_bin", tmp_path / "calls"
    for rel in ("scripts/run_digital_twin_ci.sh", "scripts/_port_lock.sh"):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes((_REPO_ROOT / rel).read_bytes())
    (root / "devices").mkdir()
    (root / "devices" / "fixture-device.toml").write_text("# fixture\n", encoding="utf-8")
    binary = tmp_path / "toolchain" / "micropython" / "ports" / "unix" / "build-standard" / "micropython"
    stubs = {root / "scripts" / "build_website.sh": f'echo "$*" >> {calls}', binary: "", **{stub_bin / name: "" for name in ("uv", "setcap")}, stub_bin / "sudo": '"$@"'}
    for path, body in stubs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"#!/usr/bin/env bash\n{body}\n", encoding="utf-8")
        path.chmod(0o755)
    (tmp_path / "runtime").mkdir()
    env = {k: v for k, v in os.environ.items() if not k.startswith("SENSORS_PORT_LOCK")}
    env |= {"PATH": f"{stub_bin}:{os.environ['PATH']}", "PICO_TOOLCHAIN_DIR": str(tmp_path / "toolchain"), "XDG_RUNTIME_DIR": str(tmp_path / "runtime")}
    done = subprocess.run(["/bin/bash", str(root / "scripts" / "run_digital_twin_ci.sh"), "fixture-device", *args], cwd=root, env=env, capture_output=True, text=True, check=False, timeout=60)
    assert done.returncode == 0, done.stderr
    return calls.read_text(encoding="utf-8").splitlines() if calls.exists() else []


@pytest.mark.parametrize(("args", "parts"), [((), ("suite", "harness")), (("--part", "suite"), ("suite",)), (("--part", "harness"), ("harness",))])
def test_the_ci_runner_builds_the_site_each_part_boots_from(harness: ModuleType, tmp_path: Path, args: "tuple[str, ...]", parts: "tuple[str, ...]") -> None:
    # The suite boots frozen_modules/, the harness the device's own site under SITES_DIR: each part builds its own.
    site = (harness.SITES_DIR / "fixture-device" / "frozen_html.py").relative_to(_REPO_ROOT)
    want = {"suite": "fixture-device", "harness": f"fixture-device {site}"}
    assert _runner_builds(tmp_path, *args) == [want[part] for part in parts]
