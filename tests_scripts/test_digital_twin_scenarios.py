"""scripts/_digital_twin_scenarios.py's frame without booting a twin: the registry (a goal per scenario, known driver
filters, nothing from tests/), the selection's named skips and deselections, which scenarios share a boot and in what
order, the idle check between them, the port band, a held port 53, the refusals, the run record and each boot's end."""

import ast
import inspect
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
import tomllib
from _devices import DEVICE_NAMES, device_toml
from _script_loader import load_script_module

from buildgen.buildspec import BUS_ATTACHED_DRIVERS
from buildgen.model import load_device
from buildgen.validate import _WDT_TIMEOUT_MS, init_int_default, module_int_const, smallest_hard_consumer

_REPO_ROOT = Path(__file__).resolve().parent.parent
_HARNESS = _REPO_ROOT / "scripts" / "_digital_twin_scenarios.py"


def _boot_once(harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, log: str, exited: "int | None", shutdown_code: int = 0, claim: bool = False, starves: bool = False) -> "list[str]":
    # One Context.boot() over a stub twin: `exited` is its exit code if it ended on its own, else it runs until shut down.
    log_path = tmp_path / "twin.log"
    log_path.write_text(log, encoding="utf-8")
    run = SimpleNamespace(proc=SimpleNamespace(poll=lambda: exited, returncode=exited), log_path=log_path, killed=False, state_dir=tmp_path)
    monkeypatch.setattr(harness, "spawn", lambda _launch, **_kw: run)
    monkeypatch.setattr(harness, "wait_until_serving", lambda *_a: None)
    monkeypatch.setattr(harness, "shutdown", lambda _run, _label: shutdown_code)
    monkeypatch.setattr(harness, "wait_exit", lambda _run, _timeout: exited)
    ctx = harness.Context("fixture-device", "/nonexistent", -1, tmp_path, (), iter([20000]), "fixture")
    with ctx.boot() as twin:
        twin.exit_claimed = claim
        twin.starves_watchdog = starves
    return [str(failure) for failure in ctx.failures]


def _clocked_stub(harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, first_move_s: float) -> "tuple[list[float], list[float]]":
    # _shared_stub's twins on a fake clock (the first list, advanced by the test; the second, each spawn's time), each
    # reading SGP40 as a fresh hotspot boot does: its untimestamped-backup warning once the twin is first_move_s old.
    clock = [0.0]
    spawned: list[float] = []
    log_path = tmp_path / "twin.log"
    log_path.write_text(_SHUTDOWN_LINE + "\n", encoding="utf-8")

    def spawn(_launch: object, **_kw: object) -> object:
        spawned.append(clock[0])
        return SimpleNamespace(proc=SimpleNamespace(poll=lambda: None, returncode=None), log_path=log_path, killed=False, state_dir=tmp_path)

    def error_table(_port: int) -> "dict[str, dict[str, object]]":
        moved = clock[0] - spawned[-1] >= first_move_s
        return {"SGP40": {"counter": int(moved), "history": [{"type": "W", "num": 35}] if moved else []}}

    monkeypatch.setattr(harness, "time", SimpleNamespace(monotonic=lambda: clock[0], sleep=lambda _s: None))
    monkeypatch.setattr(harness, "spawn", spawn)
    monkeypatch.setattr(harness, "wait_until_serving", lambda *_a: None)
    monkeypatch.setattr(harness, "shutdown", lambda _run, _label: 0)
    monkeypatch.setattr(harness, "_error_table", error_table)
    monkeypatch.setattr(harness, "_accept_queue", lambda _port: 0)
    monkeypatch.setattr(harness.Twin, "drained", lambda _self, _timeout_s=0: True)
    return clock, spawned


def _harness(*args: str, env: "dict[str, str] | None" = None) -> "subprocess.CompletedProcess[str]":
    return subprocess.run([sys.executable, str(_HARNESS), *args], capture_output=True, text=True, check=False, cwd=_REPO_ROOT, timeout=60, env=env)


def _item(harness: ModuleType, name: str, *, shared: bool = True, moves: "tuple[str, ...]" = ()) -> object:
    return harness.Scenario(name, lambda _ctx: None, "A goal.", "fixture", (), False, False, shared, moves)


def _lag_run(harness: ModuleType, device: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], windows: "list[int]", after: "tuple[int | tuple[int, int], ...]" = (2000, 900, 900)) -> "tuple[list[str], str, str]":
    # The loop-lag scenario on a stub twin on a fake clock: its load prints one LOOP_LAG line per figure of `windows`, the
    # first closing the window open when it began, after a line printed before it; then `after`'s lines print a report
    # window apart, the first 1 s after the stop. Returns the failures, the printed line and the evidence.
    links = sorted(harness._link_roles(device))
    log_path = tmp_path / "twin.log"
    report_s = module_int_const(harness.REPO_ROOT / "digital_twin", "run_generic_integration.py", "_LOOP_LAG_REPORT_MS") / 1000
    clock = [0.0]

    def line(index: int, us: "int | tuple[int, int]") -> str:
        max_us, p99_us = us if isinstance(us, tuple) else (us, us)
        return f"LOOP_LAG max_us={max_us} p99_us={p99_us} samples=500" + "".join(f" {key}={index}" for key in links)

    due = [(1.0 + report_s * i, line(len(windows) + i, us)) for i, us in enumerate(after)]

    def emit(*lines: str) -> None:
        with log_path.open("a", encoding="utf-8") as log:
            log.writelines(f"{text}\n" for text in lines)

    def sleep(seconds: float) -> None:
        clock[0] += seconds
        while due and due[0][0] <= clock[0]:
            emit(due.pop(0)[1])

    def load(_ctx: object, _twin: object) -> "dict[str, int]":
        emit(*(line(i, us) for i, us in enumerate(windows)))
        return dict.fromkeys(harness._get_routes(), 1)

    def shut_down(_run: object, _label: str) -> int:
        emit(_SHUTDOWN_LINE)
        return 0

    emit("LOOP_LAG max_us=400000 p99_us=400000 samples=100")
    run = SimpleNamespace(proc=SimpleNamespace(poll=lambda: None, returncode=None), log_path=log_path, killed=False, state_dir=tmp_path)
    monkeypatch.setattr(harness, "time", SimpleNamespace(monotonic=lambda: clock[0], sleep=sleep))
    monkeypatch.setattr(harness, "spawn", lambda _launch, **_kw: run)
    monkeypatch.setattr(harness, "wait_until_serving", lambda *_a: None)
    monkeypatch.setattr(harness, "shutdown", shut_down)
    monkeypatch.setattr(harness, "_lag_load", load)
    ctx = harness.Context(device, "/nonexistent", -1, tmp_path, (), iter([20000]), "fixture")
    try:
        harness.SCENARIOS["loop_lag_under_combined_load"].body(ctx)
    except AssertionError as failure:
        ctx.failures.insert(0, str(failure))
    evidence = tmp_path / "loop_lag.txt"
    return ctx.failures, capsys.readouterr().out, evidence.read_text(encoding="utf-8") if evidence.exists() else ""


def _plant_held_lock(runtime: Path, port: int) -> "subprocess.Popen[bytes]":
    # Another runner's live lock on `port`, as scripts/_port_lock.sh leaves it: its pid alive, outside this chain.
    holder = subprocess.Popen(["sleep", "60"])  # coreutils sleep, the stand-in holder's process
    lock = runtime / f"sensors-port-{port}.lock"
    lock.mkdir(parents=True)
    (lock / "runner").write_text("another suite\n", encoding="utf-8")
    (lock / "pid").write_text(f"{holder.pid}\n", encoding="utf-8")
    return holder


def _sgp40_default(tree: ast.Module, name: str) -> int:
    # The default of one `NAME = const(((field, type, default, ...),))` schema of src/asy_sgp40_driver.py.
    node = next(n for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == name)
    assert isinstance(node.value, ast.Call) and isinstance(node.value.args[0], ast.Tuple), ast.unparse(node)
    field = node.value.args[0].elts[0]
    assert isinstance(field, ast.Tuple) and isinstance(field.elts[2], ast.Constant) and isinstance(field.elts[2].value, int), ast.unparse(field)
    return field.elts[2].value


def _shared_stub(harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, counters: "list[dict[str, int]]") -> "list[object]":
    # Stub twins for a SharedBoot, each spawn recorded in the list returned: every slot reads free, and each GET /status
    # read takes the next of `counters`, each source's history one warning.
    spawned: list[object] = []
    log_path = tmp_path / "twin.log"
    log_path.write_text(_SHUTDOWN_LINE + "\n", encoding="utf-8")

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


def _spawned_boot(harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **boot: object) -> "tuple[list[str], str | None]":
    # One Context.boot() over a stub twin: the runner arguments spawn() was handed and the stored SYSTEM settings its
    # state held at that moment (None: no file).
    seen: list[tuple[list[str], str | None]] = []
    tmp_path.mkdir(parents=True, exist_ok=True)
    log_path = tmp_path / "twin.log"
    log_path.write_text(_SHUTDOWN_LINE + "\n", encoding="utf-8")

    def spawn(_launch: object, *, state_dir: Path, args: "tuple[str, ...]", **_kw: object) -> object:
        stored = state_dir / "config" / "config_SYSTEM.cfg"
        seen.append((list(args), stored.read_text(encoding="utf-8") if stored.exists() else None))
        return SimpleNamespace(proc=SimpleNamespace(poll=lambda: None, returncode=None), log_path=log_path, killed=False, state_dir=state_dir)

    monkeypatch.setattr(harness, "spawn", spawn)
    monkeypatch.setattr(harness, "wait_until_serving", lambda *_a: None)
    monkeypatch.setattr(harness, "shutdown", lambda _run, _label: 0)
    ctx = harness.Context("fixture-device", "/nonexistent", -1, tmp_path, (), iter([20000]), "fixture")
    with ctx.boot("--test-flash-stall-max", **boot):
        pass
    assert ctx.failures == [] and len(seen) == 1, (ctx.failures, seen)
    return seen[0]


def _toml_keys(node: object) -> "set[str]":
    # Every key at any depth of a parsed TOML document.
    if isinstance(node, dict):
        return set(node) | {k for v in node.values() for k in _toml_keys(v)}
    return {k for v in node for k in _toml_keys(v)} if isinstance(node, list) else set()


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
    tree = ast.parse(_HARNESS.read_text(encoding="utf-8"))
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


def test_a_device_independent_scenario_runs_on_its_first_device_with_the_property_only(harness: ModuleType) -> None:
    firsts = [item for item in harness.SCENARIOS.values() if item.first_device]
    assert {item.first_device for item in firsts} == set(harness._DEVICE_PROPERTIES), firsts  # each property in use
    for item in firsts:
        having = [d for d in harness.generated_devices() if harness._has_property(d, item.first_device)]
        assert having, f"{item.name}: no generated device has {item.first_device}"
        runs = {d: {s.name: why for s, why in harness.select(d, None, exclusive_port_53=True)}[item.name] for d in harness.generated_devices()}
        assert runs[having[0]] is None and all(why == f"skipped: a device-independent mechanism, run on {having[0]} only (SPECIFICATION.md E.2.1)" for d, why in runs.items() if d != having[0]), runs


def test_the_lag_bound_is_each_devices_smallest_hard_consumer_from_one_source(harness: ModuleType) -> None:
    # The watchdog's room beside one supervisor sleep, and each uart_link's reply slack (SPECIFICATION.md F.3), read
    # here from the sources; the build rule, the twin scenario and the bench lag test all call buildgen's one export.
    src = harness.REPO_ROOT / "src"
    task_check_s, reply_ms, gc_pause = module_int_const(src, "asy_system_service.py", "_TASK_CHECK_TIME"), module_int_const(src, "asy_uart_comm.py", "_DEFAULT_TIMEOUT_MS"), module_int_const(src, "asy_uart_comm.py", "_GC_PAUSE_WORST_MS")
    linked = []
    for device in DEVICE_NAMES:
        doc = tomllib.loads(device_toml(device).read_text(encoding="utf-8"))
        links = [doc["bus"][inst["bus"]] for inst in doc.get("instance", []) if inst.get("driver") == "uart_link"]
        expected = min([_WDT_TIMEOUT_MS - task_check_s * 1000] + [reply_ms - (2 * bus["poll_wait_ms"] + bus["poll_idle_ms"] + gc_pause) for bus in links])
        assert smallest_hard_consumer(load_device(device_toml(device)), src).ms == expected, device
        linked += [device] if links else []
    assert linked, "no device wires a uart_link, so the reply-slack consumer is never read"
    for reader in (harness.REPO_ROOT / "scripts" / "_digital_twin_scenarios.py", harness.REPO_ROOT / "tests_hardware" / "flash" / "test_memory_stress.py"):
        text = reader.read_text(encoding="utf-8")
        assert re.search(r"^from buildgen\.validate import .*\bsmallest_hard_consumer\b", text, re.MULTILINE), f"{reader.name} does not import the export"
        assert "_GC_PAUSE_WORST_MS" not in text and "def smallest_hard_consumer" not in text, f"{reader.name} computes its own consumer"


def test_the_loop_lag_load_spans_the_storm_at_the_longest_read_trigger_and_one_whole_window(harness: ModuleType) -> None:
    # Each storm fault lands on one read, at most the device's longest read trigger apart (each reader's trigger_s, the
    # SGP40's fixed 1 s); a link exercises once a period; one whole LOOP_LAG window inside the load prints by its end.
    src = harness.REPO_ROOT / "src"
    report_s = module_int_const(harness.REPO_ROOT / "digital_twin", "run_generic_integration.py", "_LOOP_LAG_REPORT_MS") / 1000
    link_s = module_int_const(src, "asy_uart_link_driver.py", "_EXERCISE_PERIOD_MS") / 1000
    faults = module_int_const(harness.REPO_ROOT / "buildgen", "codegen.py", "_MAX_MODULE_ERROR")  # the generated module's give-up streak
    readers = {"scd30": ("asy_scd30_driver.py", "SCD30_Reader"), "bmp3xx": ("asy_bmp3xx_driver.py", "BMP3XX_Reader"), "isl29125": ("asy_isl29125_driver.py", "ISL29125_Reader")}
    spans = []
    for device in DEVICE_NAMES:
        instances = load_device(device_toml(device)).instances.values()
        triggers = [1] + [int(str(s.fields.get("trigger_s", init_int_default(src, *readers[s.driver], "trigger_s")))) for s in instances if s.driver in readers]
        spans.append(max([faults * max(triggers)] + [link_s for s in instances if s.driver == "uart_link"]) + report_s)
    assert max(spans) == harness._LOOP_LAG_LOAD_S, spans


@pytest.mark.parametrize("device", DEVICE_NAMES)  # each device's own bound and link roles
def test_the_lag_under_load_is_over_the_windows_begun_after_its_start_and_the_boot_window_is_reported_apart(harness: ModuleType, device: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    # The first LOOP_LAG line after the load's start closes the window open then, which holds the end of boot: its
    # figure is reported beside the load's, never as it, and a line printed before the load counts in neither.
    failures, printed, evidence = _lag_run(harness, device, tmp_path, monkeypatch, capsys, [240000, 3000, 2500, 2800])
    assert failures == [], failures
    assert "max 3000 us over 4 windows" in printed and "max 240000 us" in printed and "400000" not in printed, printed
    assert evidence.splitlines()[0].split()[1:5] == ["load_max_us=3000", "boot_window_max_us=240000", "straddler_max_us=2000", "settled_max_us=900"], evidence


@pytest.mark.parametrize("device", DEVICE_NAMES)
@pytest.mark.parametrize(("over", "expected"), [(0, "in the window open when the load began"), (2, "under load"), (4, "under load")], ids=["the boot window", "a load window", "the window straddling the stop"])
def test_every_window_the_load_spans_is_held_to_the_bound_the_boot_one_included(harness: ModuleType, device: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], over: int, expected: str) -> None:
    # The window open when the readers stop closes on the next LOOP_LAG line: it holds load, so it is bound as a load window.
    bound_us = smallest_hard_consumer(load_device(device_toml(device)), harness.SRC_DIR).ms * 1000
    figures = [240000, 3000, 2500, 2800, 2000]
    figures[over] = bound_us + 1
    failures, _printed, _evidence = _lag_run(harness, device, tmp_path, monkeypatch, capsys, figures[:4], (figures[4], 900, 900))
    assert any(f"lagged {bound_us + 1} us {expected}" in f for f in failures), failures


@pytest.mark.parametrize("device", DEVICE_NAMES)
@pytest.mark.parametrize(("after", "settles"), [((60000, -1, 60000), True), ((2000, 0, 900), False)], ids=["the window after the straddling one", "one LED frame of lag"])
def test_the_settle_window_begins_after_the_stop_and_drops_no_led_frame(harness: ModuleType, device: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], *, after: "tuple[int, int, int]", settles: bool) -> None:
    # The line after the straddling one closes a window begun after the stop: it settles under one LED frame (the
    # neopixel driver's frame period), and neither the straddling window nor a later one stands in for it.
    frame_us = 1000 // module_int_const(harness.SRC_DIR, "asy_neopixel_driver.py", "_NEOPIXEL_FREQ_HZ") * 1000
    failures, _printed, _evidence = _lag_run(harness, device, tmp_path, monkeypatch, capsys, [240000, 3000, 2500, 2800], (after[0], frame_us + after[1], after[2]))
    assert (failures == []) if settles else any("did not settle" in f for f in failures), failures


@pytest.mark.parametrize("device", DEVICE_NAMES)
@pytest.mark.parametrize(("settle", "expected"), [((70000, 900), None), ((None, 900), "in the window after the load"), ((60000, 50000), "did not settle")], ids=["one host stall", "past one DNS query", "a slowed loop"])
def test_the_settle_window_is_held_at_its_p99_and_its_maximum_to_the_bound(harness: ModuleType, device: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], settle: "tuple[int | None, int]", expected: "str | None") -> None:
    # One late wake past a frame is the host's and passes; one past a DNS query (and so past every hard bound), or a
    # loop slowed at its p99, fails.
    rest_max_us = module_int_const(harness.REPO_ROOT / "buildgen", "codegen.py", "_DNS_TIMEOUT_MS") * 1000
    figure = (rest_max_us + 1 if settle[0] is None else settle[0], settle[1])
    failures, _printed, _evidence = _lag_run(harness, device, tmp_path, monkeypatch, capsys, [240000, 3000, 2500, 2800], (2000, figure, 900))
    assert (failures == []) if expected is None else any(expected in f for f in failures), failures


def test_a_stagger_wait_is_the_second_read_trigger_and_an_unknown_property_is_refused(harness: ModuleType) -> None:
    for device in harness.generated_devices():
        text = (harness.GENERATED_SRC_DIR / f"sensortask_{device}.py").read_text(encoding="utf-8")
        starter = text[text.index("def _collect_trigger_starters") :].split("\n\n", 1)[0]
        modules = re.search(r"for module in \(([^)]*)\)", starter)
        assert modules is not None, device
        assert harness._stagger_waits(device) == (len([m for m in modules.group(1).split(",") if m.strip()]) > 1), (device, modules.group(1))
    def body(_ctx: object) -> None:
        """A body asking for a property no device is read for."""

    with pytest.raises(ValueError, match="no known property"):
        harness.scenario("zz_unknown_property", family="fixture", first_device="fixture-property")(body)
    assert "zz_unknown_property" not in harness.SCENARIOS


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


@pytest.mark.usefixtures("own_lock_root")
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
    outcomes = {row["name"]: (row["outcome"], row["reason"]) for row in json.loads(record.read_text(encoding="utf-8"))}
    assert outcomes["ok"][0] == "passed"
    assert outcomes["broken"][0] == "failed" and "planted" in outcomes["broken"][1]
    assert outcomes["needs_isl"] == ("skipped", "device wires no isl29125")


def test_a_scenario_whose_premise_this_host_cannot_give_skips_with_its_reason(harness: ModuleType, tmp_path: Path) -> None:
    def no_premise(_ctx: object) -> None:
        """Skips."""
        raise harness.UnmetPremiseError("file modes do not bind here")

    item = harness.Scenario("no_premise", no_premise, "Skips.", "fixture")
    ctx = harness.Context(DEVICE_NAMES[0], "micropython", -1, tmp_path, (), iter(()), "host")
    assert harness._run_one(item, ctx) == harness.Outcome("no_premise", "skipped", "file modes do not bind here")
    ctx.failures.append("twin 1: the SIGINT shutdown ended killed")  # a boot's own failure still fails it
    assert harness._run_one(item, ctx).outcome == "failed"


@pytest.mark.usefixtures("own_lock_root")
def test_a_run_that_passed_nothing_is_no_pass(harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def ok(_ctx: object) -> None:
        """Passes."""

    monkeypatch.setattr(harness, "SCENARIOS", {"needs_isl": harness.Scenario("needs_isl", ok, "Passes.", "fixture", ("isl29125",))})
    device = next(d for d in DEVICE_NAMES if "isl29125" not in {driver for _k, driver, _e in harness._instances(d)})
    assert harness.main(["--device", device, "--logs-dir", str(tmp_path / "logs")]) == 1


_SHUTDOWN_LINE = (
    " No. of 1-blocks: 14, 2-blocks: 4, max blk sz: 9, max free sz: 64730\n"
    "digital_twin/run_generic_integration.py [fixture_device] shutdown: would_have_triggered_count=0 feed_count=1 largest_feed_gap_ms=1 "
    "wdt_timeout_ms=8000 mem_backup: r0=0x00000000,0x00000000,0x00000000,0x00000000 public_destinations_refused=0 flash_stall_longest_ms=0 "
    "gc_block_bytes=32 fram_writes=0 fram_writes_by=- fram_silent_writes=0 fram_silent_wrens=0"
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


@pytest.mark.parametrize("starves", [False, True])
def test_a_boot_whose_feed_gap_came_near_the_watchdog_fails_unless_it_starves_it_by_design(harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, starves: bool) -> None:
    near = _SHUTDOWN_LINE.replace("largest_feed_gap_ms=1 ", "largest_feed_gap_ms=6300 ")
    failures = _boot_once(harness, tmp_path, monkeypatch, log=near, exited=None, starves=starves)
    assert failures == [] if starves else (len(failures) == 1 and "6300 ms" in failures[0] and "8000 ms" in failures[0]), failures


@pytest.fixture
def own_lock_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # main() takes port 53's lock: a lock root of the test's own and no inherited chain, so no other suite's lock counts.
    for name in ("SENSORS_PORT_LOCKS_HELD", "SENSORS_PORT_LOCK_OWNER"):
        monkeypatch.delenv(name, raising=False)
    root = tmp_path / "runtime"
    root.mkdir()
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(root))
    return root


def test_a_held_port_53_fails_the_run_at_once_naming_it_and_boots_nothing(harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], own_lock_root: Path) -> None:
    ran: list[str] = []

    def body(_ctx: object) -> None:
        """Records that it ran."""
        ran.append("ran")

    monkeypatch.setattr(harness, "SCENARIOS", {"records": harness.Scenario("records", body, "Records that it ran.", "fixture")})
    holder = _plant_held_lock(own_lock_root, 53)
    try:
        code = harness.main(["--device", DEVICE_NAMES[0], "--logs-dir", str(tmp_path / "logs")])
    finally:
        holder.kill()
        holder.wait()
    err = capsys.readouterr().err
    assert (code, ran) == (1, []), (code, ran, err)
    assert "port 53 is held by another suite" in err, err


def test_every_boot_logs_at_error_level_from_its_build_and_its_stored_level(harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Built at error level by the runner's flag and kept there by a stored DebugLevel planted before the spawn, so a
    # caught allocation failure's line reaches the memory gate; the scenario's own arguments follow unchanged.
    level = module_int_const(_REPO_ROOT / "src", "asy_print_log.py", "_LOG_ERR")
    args, stored = _spawned_boot(harness, tmp_path, monkeypatch)
    assert args == ["--debug-level", str(level), "--test-kbd-traceback", "--test-flash-stall-max"], args
    assert stored is not None and json.loads(stored) == {"DebugLevel": level}, stored


def test_a_stored_level_is_kept_and_a_boot_not_logged_plants_nothing(harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "state_01" / "config"
    config.mkdir(parents=True)
    (config / "config_SYSTEM.cfg").write_text('{"DebugLevel": 4}', encoding="utf-8")  # an earlier boot's own
    assert _spawned_boot(harness, tmp_path, monkeypatch)[1] == '{"DebugLevel": 4}'
    args, stored = _spawned_boot(harness, tmp_path / "unlogged", monkeypatch, logged=False)
    assert (args, stored) == (["--test-kbd-traceback", "--test-flash-stall-max"], None)


def test_only_the_scenario_reading_the_device_defaults_boots_unlogged(harness: ModuleType) -> None:
    # GET /system's DebugLevel is the device's default only on a boot that planted nothing: that scenario's own boot.
    unlogged = sorted(item.name for item in harness.SCENARIOS.values() if "logged=False" in inspect.getsource(item.body))
    assert unlogged == ["every_get_endpoint_is_reachable_over_real_http_and_shaped_correctly"], unlogged
    assert not harness.SCENARIOS[unlogged[0]].shared


@pytest.mark.parametrize(
    ("word", "counters", "expected"),
    [("Failed", {"SGP40": 2, "SYSTEM": 0}, None), ("Valid", {"SGP40": 2, "SYSTEM": 0}, "answered 200 'Valid'"), ("Failed", {"SGP40": 0, "SYSTEM": 0}, "'SGP40': (2, 0)")],
    ids=["refused, nothing cleared", "accepted", "a count lowered"],
)
def test_a_reset_errors_under_a_held_reset_must_answer_failed_and_lower_nothing(harness: ModuleType, monkeypatch: pytest.MonkeyPatch, word: str, counters: "dict[str, int]", expected: "str | None") -> None:
    answer = harness.Answer(200, {}, json.dumps({"result": {"ResetErrors": word}}).encode())
    monkeypatch.setattr(harness, "_request", lambda *_a, **_kw: answer)
    monkeypatch.setattr(harness, "_error_table", lambda _port: {name: {"counter": value} for name, value in counters.items()})
    before = {"SGP40": {"counter": 2}, "SYSTEM": {"counter": 0}}
    if expected is None:
        harness._refused_reset_errors(20000, before, "while held")
        return
    with pytest.raises(AssertionError, match=re.escape(expected)):
        harness._refused_reset_errors(20000, before, "while held")


def test_the_routes_come_from_the_service_table(harness: ModuleType) -> None:
    routes = harness._get_routes()
    assert {"/measurements", "/sensors", "/status", "/system", "/networking", "/notification"} <= set(routes), routes
    assert "/" not in routes


def test_the_reset_takes_the_largest_body_and_skips_when_none_outgrows_both_buffers(harness: ModuleType) -> None:
    sizes = {"/status": 900, "/js/app.js": 28782, "/index.html": 16797}
    assert harness._largest_past(sizes, 6912) == "/js/app.js"
    with pytest.raises(harness.UnmetPremiseError, match=re.escape("no GET body exceeds the 28782 B the two pinned buffers hold (largest: /js/app.js, 28782 B)")):
        harness._largest_past(sizes, 28782)


def test_the_site_paths_are_the_staged_modules_files_as_a_client_requests_them(harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "fixture-device").mkdir()
    (tmp_path / "fixture-device" / "frozen_html.py").write_text("# /index.html.gz size=10\n_f0 = const(b'# /x.gz size=1')\n# /js/app.js.gz size=20\n", encoding="utf-8")
    monkeypatch.setattr(harness, "SITES_DIR", tmp_path)
    assert harness._site_paths("fixture-device") == ["/index.html", "/js/app.js"]
    (tmp_path / "fixture-device" / "frozen_html.py").write_text("_f0 = const(b'')\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="lists no file"):  # a changed module format, never a site with nothing to send
        harness._site_paths("fixture-device")


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


def test_a_group_reaching_the_sgp40_backup_deadline_goes_on_on_a_fresh_boot(harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Three 40 s scenarios on a twin whose own background moves SGP40 at 94 s, as dev's measured: the twin is retired
    # before its deadline, so no scenario's window holds that move and every idle check passes.
    clock, spawned = _clocked_stub(harness, tmp_path, monkeypatch, first_move_s=94.0)
    shared = harness.SharedBoot(harness.Context("fixture-device", "/nonexistent", -1, tmp_path, (), iter(range(20000, 20010)), "fixture"))
    results = []
    for name, last in (("a", False), ("b", False), ("c", True)):
        with harness.Context("fixture-device", "/nonexistent", -1, tmp_path, (), iter([]), "fixture", shared=shared).boot():
            clock[0] += 40.0
        results.append(shared.release(_item(harness, name), failed=False, last=last))
    assert results == [[], [], []], results
    assert len(spawned) >= 2 and all(later - earlier < 89.0 for earlier, later in zip(spawned, [*spawned[1:], clock[0]], strict=True)), spawned


@pytest.mark.parametrize("age_s", [90.0, 100.0], ids=["before the twin's first move", "after it"])
def test_a_count_moved_past_the_sgp40_backup_deadline_fails_as_the_boots_overrun(harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, age_s: float) -> None:
    # One scenario longer than the deadline: a count its window saw move fails naming the overrun, never blaming the
    # scenario for the background's move; with nothing moved yet there is nothing to tell apart, so it passes.
    clock, _spawned = _clocked_stub(harness, tmp_path, monkeypatch, first_move_s=94.0)
    shared = harness.SharedBoot(harness.Context("fixture-device", "/nonexistent", -1, tmp_path, (), iter(range(20000, 20010)), "fixture"))
    with harness.Context("fixture-device", "/nonexistent", -1, tmp_path, (), iter([]), "fixture", shared=shared).boot():
        clock[0] += age_s
    problems = shared.release(_item(harness, "slow"), failed=False, last=True)
    if age_s < 94.0:
        assert problems == [], problems
        return
    assert len(problems) == 1 and problems[0].startswith(f"idle check after slow: the shared boot outlived its SGP40 backup deadline ({age_s:.1f} s > 89 s)"), problems
    assert "SGP40" in problems[0] and "does not state" not in problems[0], problems


def test_the_shared_boot_deadline_is_sgp40s_first_untimestamped_backup(harness: ModuleType) -> None:
    # 60 x BackupPeriod read cycles to the first backup, then WaitTimeNTP - 1 retries waiting for NTP, each one read
    # period (asy_sgp40_driver.py _check_storage()/_run_backup()); no device overrides either default.
    tree = ast.parse((_REPO_ROOT / "src" / "asy_sgp40_driver.py").read_text(encoding="utf-8"))
    period = _sgp40_default(tree, "_VAL_BACKUP_PERIOD")
    wait = min(_sgp40_default(tree, "_VAL_WAIT_TIME_NTP"), module_int_const(_REPO_ROOT / "src", "asy_sgp40_driver.py", "_MAX_NTP_WAITTIME"))
    starter = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "start_timer")
    read_ms = [k.value.value for c in ast.walk(starter) if isinstance(c, ast.Call) for k in c.keywords if k.arg == "period" and isinstance(k.value, ast.Constant) and isinstance(k.value.value, int)]
    assert len(read_ms) == 1, read_ms
    assert (60 * period + max(wait - 1, 0)) * read_ms[0] / 1000 == harness._SHARED_BOOT_DEADLINE_S, (period, wait, read_ms)
    overrides = {device: sorted(_toml_keys(tomllib.loads(device_toml(device).read_text(encoding="utf-8"))) & {"BackupPeriod", "WaitTimeNTP"}) for device in DEVICE_NAMES}
    assert overrides and not any(overrides.values()), overrides


def test_the_accept_queue_is_read_from_the_listening_row(harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    table = tmp_path / "tcp"
    header = "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n"
    table.write_text(header + "   0: 0100007F:4E20 00000000:0000 0A 00000000:00000003 00:00000000 00000000     0        0 1\n   1: 0100007F:4E20 0100007F:9C40 01 00000000:00000000 00:00000000 00000000     0        0 2\n", encoding="utf-8")
    monkeypatch.setattr(harness, "Path", lambda name: table if name == "/proc/net/tcp" else tmp_path / "absent")
    assert harness._accept_queue(0x4E20) == 3
    assert harness._accept_queue(0x4E21) is None


def test_every_scenario_names_its_family_as_a_literal() -> None:
    # The level-containment check reads each decorator's family= keyword by AST, so it is a string literal everywhere.
    tree = ast.parse(_HARNESS.read_text(encoding="utf-8"))
    decorators = [d for n in tree.body if isinstance(n, ast.FunctionDef) for d in n.decorator_list if isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "scenario"]
    families = [next((k.value for k in d.keywords if k.arg == "family"), None) for d in decorators]
    assert decorators and all(isinstance(f, ast.Constant) and isinstance(f.value, str) and f.value.isidentifier() for f in families), [ast.unparse(d) for d, f in zip(decorators, families, strict=True) if not isinstance(f, ast.Constant)]


def test_a_scenario_without_a_family_is_refused_at_registration(harness: ModuleType) -> None:
    def body(_ctx: object) -> None:
        """Names no family."""

    with pytest.raises(ValueError, match="names no family"):
        harness.scenario("zz_no_family", family="")(body)
    assert "zz_no_family" not in harness.SCENARIOS
