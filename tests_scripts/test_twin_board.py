"""tests_hardware/twin_board.py keeps harness.Board's shape (ast) and runs a device script under the real Unix-port twin
via digital_twin/run_device_script.py: output back, a raising or starving script or one it cannot intern failing, a
reset's output kept, both GC stages, twin layout and probe binary (micropypath.toml, _unix_port.sh), conformance."""

import ast
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests_hardware"))

import conformance
import harness
import twin_board

import scripts._twin_process as twin_process

TESTS_HARDWARE = Path(__file__).resolve().parent.parent / "tests_hardware"
_TWIN_LAYOUT = tomllib.loads((TESTS_HARDWARE.parent / "scripts" / "micropypath.toml").read_text(encoding="utf-8"))["twin"]
_LIMIT = twin_process._QSTR_MAX_BYTES
_REFUSED = f"- the Unix port interns each as a qstr of at most {_LIMIT} bytes and dies before the runner starts"


def _plant_binary(toolchain: Path, *, reports: str) -> Path:
    # A stand-in the shared probe asks for its build flavour: it answers with `reports`.
    binary = toolchain / "micropython" / "ports" / "unix" / "build-standard" / "micropython"
    binary.parent.mkdir(parents=True)
    binary.write_text(f"#!/bin/sh\necho {reports}\n", encoding="utf-8")
    binary.chmod(0o755)
    return binary


def _public_methods(path: Path, cls: str) -> "dict[str, list[tuple[str, str]]]":
    # Each public method's parameters as (name, kind), read from the class body by ast.
    tree = ast.parse(path.read_text(encoding="utf-8"))
    body = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == cls).body
    methods = {}
    for fn in body:
        if isinstance(fn, ast.FunctionDef) and not fn.name.startswith("_"):
            args = fn.args
            methods[fn.name] = [(a.arg, "positional") for a in args.args] + [(a.arg, "keyword") for a in args.kwonlyargs] + ([(args.kwarg.arg, "extras")] if args.kwarg else [])
    return methods


def _script(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "probe.py"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def twin(twin_env: None) -> "twin_board.TwinBoard":
    del twin_env
    return twin_board.TwinBoard()


@pytest.fixture
def twin_env(micropython_bin: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The built Unix port, and the rendered scripts and wiring plans under the test's own directory.
    monkeypatch.setenv("PICO_TOOLCHAIN_DIR", str(micropython_bin.parents[4]))
    monkeypatch.setattr(harness, "RENDERED_SCRIPTS_DIR", tmp_path / "rendered")
    monkeypatch.setattr(twin_board, "PLAN_DIR", tmp_path / "twin")


def test_twin_board_has_boards_public_methods_with_the_same_parameters() -> None:
    board, twin = _public_methods(TESTS_HARDWARE / "harness.py", "Board"), _public_methods(TESTS_HARDWARE / "twin_board.py", "TwinBoard")
    assert twin == board, f"TwinBoard differs from Board: {sorted(set(twin.items()) ^ set(board.items()))}"


def test_the_twin_runs_the_probes_binary_with_the_twins_one_micropypath(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, repo_root: Path) -> None:
    binary = _plant_binary(tmp_path, reports="standard")
    seen: list[tuple[list[str], dict[str, str]]] = []
    real_run = subprocess.run

    def run(argv: "list[str]", **kwargs: object) -> "subprocess.CompletedProcess[str]":
        if argv[0] == "/bin/bash":  # the shared probe itself runs for real
            return real_run(argv, **kwargs)  # type: ignore[call-overload, no-any-return]
        env = kwargs["env"]
        assert isinstance(env, dict)
        seen.append((argv, env))
        return subprocess.CompletedProcess(argv, 0, "ok\n", "")

    monkeypatch.setenv("PICO_TOOLCHAIN_DIR", str(tmp_path))
    monkeypatch.setattr(twin_board, "PLAN_DIR", tmp_path / "twin")
    monkeypatch.setattr(subprocess, "run", run)
    twin_board.TwinBoard().run_isolated(_script(tmp_path, "print('ok')\n"))
    argv, env = seen[0]
    assert argv[0] == str(binary) and twin_board.unix_port_binary() == binary
    assert env["MICROPYPATH"] == twin_board.twin_micropypath() and env["TZ"] == "UTC"
    assert [entry.removeprefix(f"{repo_root}/") for entry in env["MICROPYPATH"].split(":")] == _TWIN_LAYOUT.split(":")


@pytest.mark.parametrize("gc_threshold", [-1, 32768])
def test_a_script_runs_in_the_twin_and_returns_its_output(twin: "twin_board.TwinBoard", tmp_path: Path, gc_threshold: int) -> None:
    twin.gc_threshold = gc_threshold
    output = twin.run_isolated(_script(tmp_path, "import gc\nprint('twin-ok', gc.threshold())\n"))
    assert f"twin-ok {gc_threshold}" in output, output
    assert twin.tail_log(0.0) == output.splitlines() and twin.recovery_events == []
    assert twin.tail_log(0.0) == [], "a passive tail reads each line once"


def test_a_raising_script_fails_the_run_with_its_traceback(twin: "twin_board.TwinBoard", tmp_path: Path) -> None:
    with pytest.raises(harness.HardwareTestFailureError, match=r"failed \(exit 1\)(.|\n)*ValueError: boom"):
        twin.run_isolated(_script(tmp_path, "raise ValueError('boom')\n"))


def test_a_script_exit_status_is_the_runs(twin: "twin_board.TwinBoard", tmp_path: Path) -> None:
    twin.run_isolated(_script(tmp_path, "import sys\nsys.exit(0)\n"))
    with pytest.raises(harness.HardwareTestFailureError, match=r"exit 5"):
        twin.run_isolated(_script(tmp_path, "import sys\nsys.exit(5)\n"))


def test_a_reset_ends_an_expect_reset_run_with_the_output_before_it(twin: "twin_board.TwinBoard", tmp_path: Path) -> None:
    script = _script(tmp_path, "import machine\nprint('FACT seeded=true')\nmachine.reset()\nprint('never')\n")
    output = twin.run_isolated_expect_reset(script)
    assert "FACT seeded=true" in output and "never" not in output and "machine reset: kind=reset" in output
    assert harness.parse_facts(output, allow_missing_done=True) == {"seeded": True}
    with pytest.raises(harness.HardwareTestFailureError, match="exit 3"):
        twin.run_isolated(script)


def test_a_script_starving_the_watchdog_fails(twin: "twin_board.TwinBoard", tmp_path: Path) -> None:
    script = _script(tmp_path, "import asyncio, machine\nasync def idle():\n    await asyncio.sleep_ms(300)\nwdt = machine.WDT(timeout=100)\nasyncio.run(idle())\n")
    with pytest.raises(harness.HardwareTestFailureError, match="starved the watchdog"):
        twin.run_isolated(script)


def test_a_second_watchdog_construction_is_the_armed_one(twin: "twin_board.TwinBoard", tmp_path: Path) -> None:
    # rp2 keeps one watchdog: two constructions are one object, so feeding the second keeps the first from firing.
    script = _script(tmp_path, "import asyncio, machine\nfirst = machine.WDT(timeout=200)\nsecond = machine.WDT(timeout=200)\nasync def fed():\n    for _ in range(5):\n        await asyncio.sleep_ms(100)\n        second.feed()\nasyncio.run(fed())\nprint('same', first is second)\n")
    assert "same True" in twin.run_isolated(script)


def test_a_missing_unix_port_names_the_build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PICO_TOOLCHAIN_DIR", str(tmp_path / "no-toolchain"))
    monkeypatch.setattr(twin_board, "PLAN_DIR", tmp_path / "twin")
    with pytest.raises(FileNotFoundError, match=r"^error: no MicroPython Unix port at .*build-standard/micropython - build it with: uv run toolchain/setup_toolchain\.py setup$"):
        twin_board.TwinBoard().run_isolated(_script(tmp_path, "print(1)\n"))


def test_a_binary_of_another_build_flavour_is_refused_naming_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A settrace build would run every twin at 4-5x the allocations (SPECIFICATION.md E.5.2): the run refuses it.
    _plant_binary(tmp_path, reports="settrace")
    monkeypatch.setenv("PICO_TOOLCHAIN_DIR", str(tmp_path))
    monkeypatch.setattr(twin_board, "PLAN_DIR", tmp_path / "twin")
    with pytest.raises(FileNotFoundError, match=r"reports itself as the 'settrace' build flavour, not 'standard'"):
        twin_board.TwinBoard().run_isolated(_script(tmp_path, "print(1)\n"))


@pytest.mark.parametrize("case", ["wiring plan", "script", "multibyte state directory", "runner's directory", "micropypath entry"])
def test_a_string_the_interpreter_cannot_intern_fails_the_run_before_anything_starts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    # Each kills the interpreter before the runner's first line ("FATAL: uncaught NLR", exit 1): the run fails naming it,
    # its size in bytes (as the interpreter measures) and the limit, before the probe or the interpreter runs.
    calls: list[list[str]] = []

    def run(argv: "list[str]", **_kw: object) -> "subprocess.CompletedProcess[str]":
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, "ok\n", "")

    plan_dir, script_dir = tmp_path / ("p" * 250 if case == "wiring plan" else "twin"), tmp_path / ("s" * 250 if case == "script" else "scripts")
    script_dir.mkdir()
    if case == "multibyte state directory":
        (tmp_path / ("\u00e9" * 100)).mkdir()
        monkeypatch.setattr(tempfile, "tempdir", str(tmp_path / ("\u00e9" * 100)))
    elif case == "runner's directory":
        monkeypatch.setattr(twin_board, "RUNNER", f"{'r' * 250}/run_device_script.py")
    elif case == "micropypath entry":
        monkeypatch.setattr(twin_board, "_TWIN_LAYOUT", f"/{'m' * _LIMIT}:{_TWIN_LAYOUT}")
    monkeypatch.setattr(twin_board, "PLAN_DIR", plan_dir)
    monkeypatch.setattr(subprocess, "run", run)
    board, script = twin_board.TwinBoard(), _script(script_dir, "print('ok')\n")
    name, value = {
        "wiring plan": ("argument 1", plan_dir / f"{board.device}_plan.json"),
        "script": ("argument 2", script),
        "multibyte state directory": ("--state-dir's value", board._state.name),
        "runner's directory": ("the runner's directory", (harness.REPO_ROOT / twin_board.RUNNER).resolve().parent),
        "micropypath entry": ("MICROPYPATH entry 1", f"/{'m' * _LIMIT}"),
    }[case]
    with pytest.raises(harness.HardwareTestFailureError, match=r"^twin run of probe\.py was not started: ") as failed:
        board.run_isolated(script)
    assert f"{name} ({len(os.fsencode(str(value)))} bytes)" in str(failed.value) and str(failed.value).endswith(_REFUSED), failed.value
    assert calls == [], f"the twin probed or ran the interpreter before refusing: {calls}"


def test_the_refusal_is_the_twin_launchs_own_check() -> None:
    # One check for every Python launcher of the Unix port: twin_board keeps no copy of scripts/_twin_process.py's.
    assert vars(twin_board)["_uninternable"] is twin_process._uninternable


def test_a_string_at_the_limit_still_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The boundary's other side: a wiring plan path and a MICROPYPATH entry of 255 bytes each run.
    binary = _plant_binary(tmp_path, reports="standard")
    seen: list[list[str]] = []
    real_run = subprocess.run

    def run(argv: "list[str]", **kwargs: object) -> "subprocess.CompletedProcess[str]":
        if argv[0] == "/bin/bash":  # the shared probe itself runs for real
            return real_run(argv, **kwargs)  # type: ignore[call-overload, no-any-return]
        seen.append(argv)
        return subprocess.CompletedProcess(argv, 0, "ok\n", "")

    pad = _LIMIT - len(os.fsencode(str(tmp_path))) - len(f"//{harness.bench_device()}_plan.json")
    monkeypatch.setenv("PICO_TOOLCHAIN_DIR", str(tmp_path))
    monkeypatch.setattr(twin_board, "PLAN_DIR", tmp_path / ("p" * pad))
    monkeypatch.setattr(twin_board, "_TWIN_LAYOUT", f"/{'m' * (_LIMIT - 1)}:{_TWIN_LAYOUT}")
    monkeypatch.setattr(subprocess, "run", run)
    assert twin_board.TwinBoard().run_isolated(_script(tmp_path, "print('ok')\n")) == "ok\n"
    assert seen[0][0] == str(binary) and len(os.fsencode(seen[0][4])) == _LIMIT, seen


def test_the_runner_prints_its_usage_and_refuses_a_malformed_call(micropython_bin: Path, repo_root: Path) -> None:
    env = dict(os.environ, MICROPYPATH=_TWIN_LAYOUT, TZ="UTC")
    usage = subprocess.run([str(micropython_bin), twin_board.RUNNER, "--help"], cwd=repo_root, env=env, capture_output=True, text=True, timeout=60, check=False)
    bad = subprocess.run([str(micropython_bin), twin_board.RUNNER, "only-one"], cwd=repo_root, env=env, capture_output=True, text=True, timeout=60, check=False)
    assert (usage.returncode, bad.returncode) == (0, 2), (usage.stdout, bad.stdout)
    assert "usage:" in usage.stdout and "expected a wiring plan and a script" in bad.stdout


@pytest.mark.parametrize("gc_threshold", [-1, 32768])
def test_a_conformance_probe_runs_on_the_twin_and_returns_its_keys(twin_env: None, tmp_path: Path, gc_threshold: int) -> None:
    # A probe of the real ones' output form; the ISL29125 probe itself spends ~10 s per run in settle waits that model
    # the chip's conversion times, so its own twin runs are recorded at execution rather than repeated here.
    del twin_env
    probe = _script(tmp_path, "import gc\nprint('A01_id=0x7d')\nprint('GC=%d' % gc.threshold())\nprint('DONE=1')\n")
    assert conformance.run_probe_on_twin(probe, gc_threshold) == {"A01_id": "0x7d", "GC": str(gc_threshold), "DONE": "1"}


def test_a_conformance_probe_that_never_finished_fails_with_its_output(twin_env: None, tmp_path: Path) -> None:
    del twin_env
    with pytest.raises(AssertionError, match=r"did not run to completion(.|\n)*A01_id=0x7d"):
        conformance.run_probe_on_twin(_script(tmp_path, "print('A01_id=0x7d')\n"), -1)


def test_conformance_diffs_protocol_keys_verbatim_and_physical_keys_by_their_independent_form() -> None:
    physical = frozenset({"lux", "counts"})
    checks = {"counts": lambda value: 0 <= int(value) <= 65535}
    real = {"A01_id": "0x7d", "lux": "312", "counts": "70000", "B02_only_real": "1"}
    twin = {"A01_id": "0x7e", "lux": "18", "counts": "1200"}
    assert conformance.compare(real, twin, physical, checks) == [
        "A01_id: real chip '0x7d', twin '0x7e'",
        "B02_only_real: real chip '1', twin '<absent>'",
        "counts: real chip outside its independent form (real chip '70000', twin '1200')",
    ]
    assert conformance.compare({"lux": "5"}, {}, physical, checks) == ["lux: real chip '5', twin '<absent>'"]


def test_a_conformance_run_with_no_unix_port_skips_naming_the_build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PICO_TOOLCHAIN_DIR", str(tmp_path / "no-toolchain"))
    with pytest.raises(pytest.skip.Exception, match=r"not built at .* - run scripts/test\.sh once"):
        conformance.run_probe_on_twin(conformance.ISL29125.probe, -1)
