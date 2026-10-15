"""A long device script feeds the watchdog in short steps: no single sleep in a rendered script outlasts the shared
feed step (at most 2 s), and a script its host test allows more than one watchdog period arms the watchdog and feeds
it - the two starvation scripts excepted, whose subject is the reset."""

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests_hardware"))
import bench_facts
import harness

_TESTS_HARDWARE = Path(__file__).resolve().parents[1] / "tests_hardware"
_SCRIPTS = _TESTS_HARDWARE / "device_scripts"
_MAX_STEP_MS = 2000
_WATCHDOG_PERIOD_S = 8
# The scripts whose subject is the watchdog reset itself: they starve it on purpose.
_STARVATION_SCRIPTS = {"watchdog_starvation_reset.py", "reboot_fallback_starves_the_watchdog.py"}
_SLEEP_SCALE_MS = {"sleep": 1000.0, "sleep_ms": 1.0, "sleep_us": 0.001}
_FEEDS = frozenset({"feed", "fed_sleep_ms", "fed_wait_ms", "settled"})


def _call_name(node: ast.AST) -> str:
    if not isinstance(node, ast.Call):
        return ""
    return node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")


def _constants(tree: ast.Module) -> "dict[str, float]":
    # Module-level NAME = <number>, so a sleep through a named constant is read like a literal.
    found: dict[str, float] = {}
    for node in tree.body:
        value = node.value if isinstance(node, ast.Assign | ast.AnnAssign) else None
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        if isinstance(value, ast.Constant) and isinstance(value.value, int | float) and not isinstance(value.value, bool):
            found.update({t.id: float(value.value) for t in targets if isinstance(t, ast.Name)})
    return found


def _number(node: "ast.expr | None", constants: "dict[str, float]") -> "float | None":
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float) and not isinstance(node.value, bool):
        return float(node.value)
    if isinstance(node, ast.Name):
        return constants.get(node.id)
    return None


def _long_sleeps(source: str) -> "list[str]":
    # Each sleep()/sleep_ms()/sleep_us() whose literal or named-constant argument exceeds one feed step.
    tree = ast.parse(source)
    constants = _constants(tree)
    found: list[str] = []
    for node in ast.walk(tree):
        name = _call_name(node)
        if isinstance(node, ast.Call) and name in _SLEEP_SCALE_MS and node.args:
            value = _number(node.args[0], constants)
            if value is not None and value * _SLEEP_SCALE_MS[name] > _MAX_STEP_MS:
                found.append(f"line {node.lineno}: {name}({ast.unparse(node.args[0])})")
    return found


def _rendered_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> "dict[str, str]":
    monkeypatch.setattr(harness, "RENDERED_SCRIPTS_DIR", tmp_path)
    # A static check reads the includes a render inlines; no fact value enters it, so the render takes the device
    # module's name alone instead of a cold build of every fact.
    module = f"sensortask_{harness.bench_device()}"
    monkeypatch.setattr(bench_facts, "build", lambda _device: {"device_module": module})
    return {path.name: harness.render_device_script(path).read_text(encoding="utf-8") for path in sorted(_SCRIPTS.glob("*.py"))}


def test_the_shared_feed_step_is_at_most_two_seconds() -> None:
    step = _constants(ast.parse((_SCRIPTS / "_shared" / "watchdog.py").read_text(encoding="utf-8"))).get("_FEED_STEP_MS")
    assert step is not None and step <= _MAX_STEP_MS, f"_shared/watchdog.py's _FEED_STEP_MS is {step}"


def test_no_rendered_script_sleeps_longer_than_one_feed_step(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    found = {name: sleeps for name, source in _rendered_sources(tmp_path, monkeypatch).items() if (sleeps := _long_sleeps(source))}
    assert not found, f"a wait longer than {_MAX_STEP_MS} ms goes through fed_sleep_ms()/fed_wait_ms(): {found}"


def _long_runs(modules: "list[Path]", scripts: "set[str]") -> "dict[str, float]":
    # Script -> the longest timeout_s a host run_isolated() call gives it, read from literals and module constants.
    longest: dict[str, float] = {}
    for path in modules:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        constants = _constants(tree)
        named = {t.id: s for n in tree.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name) for s in scripts if s in ast.unparse(n.value)}
        for call in [n for n in ast.walk(tree) if isinstance(n, ast.Call) and _call_name(n) in {"run_isolated", "run_isolated_expect_reset"} and n.args]:
            timeout = _number(next((kw.value for kw in call.keywords if kw.arg == "timeout_s"), None), constants)
            ran = {s for s in scripts if s in ast.unparse(call.args[0])} | {named[n.id] for n in ast.walk(call.args[0]) if isinstance(n, ast.Name) and n.id in named}
            for script in ran if timeout is not None else set():
                longest[script] = max(longest.get(script, 0.0), timeout or 0.0)
    return longest


def _arms_and_feeds(source: str) -> bool:
    # Fed by the script itself, or by the product system it builds: build_system()/main() take the watchdog and feed it.
    calls = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call)]
    names = {_call_name(n) for n in calls}
    handed_over = any(_call_name(c) in {"build_system", "main"} and any(kw.arg == "watchdog" for kw in c.keywords) for c in calls)
    return bool(names & {"arm", "WDT"}) and (bool(names & _FEEDS) or handed_over)


def test_a_script_run_longer_than_one_watchdog_period_arms_and_feeds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rendered = _rendered_sources(tmp_path, monkeypatch)
    modules = sorted(p for p in _TESTS_HARDWARE.rglob("*.py") if "device_scripts" not in p.parts)
    runs = _long_runs(modules, set(rendered))
    assert runs, "no host run_isolated() call names a script with a timeout_s - the scan reads nothing"
    unfed = {name: timeout for name, timeout in runs.items() if timeout > _WATCHDOG_PERIOD_S and name not in _STARVATION_SCRIPTS and not _arms_and_feeds(rendered[name])}
    assert not unfed, f"allowed more than {_WATCHDOG_PERIOD_S} s yet never arms and feeds the watchdog (script: timeout_s): {unfed}"


def test_the_watchdog_checks_bite(tmp_path: Path) -> None:
    assert _long_sleeps("import time\n_WAIT_S = 5\ntime.sleep(_WAIT_S)\ntime.sleep_ms(1500)\nawait asyncio.sleep_ms(2500)\n") == ["line 3: sleep(_WAIT_S)", "line 5: sleep_ms(2500)"]
    host = tmp_path / "test_host.py"
    host.write_text("_LONG_S = 30.0\n\n\ndef test_a(board):\n    board.run_isolated(DEVICE_SCRIPTS / 'long.py', timeout_s=_LONG_S)\n    board.run_isolated(DEVICE_SCRIPTS / 'short.py', timeout_s=5)\n", encoding="utf-8")
    assert _long_runs([host], {"long.py", "short.py"}) == {"long.py": 30.0, "short.py": 5.0}
    assert not _arms_and_feeds("async def _main():\n    await work()\n")
    assert _arms_and_feeds("async def _main():\n    wdt = arm()\n    await fed_sleep_ms(wdt, 9000)\n")
    assert _arms_and_feeds("async def _main():\n    wdt = machine.WDT(timeout=8000)\n    await device.main(watchdog=wdt)\n")
