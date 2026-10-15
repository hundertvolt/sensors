"""The twin runners with every tool stubbed: run_digital_twin_ci.sh archives the device's previous logs before any build
(three runs kept), runs the suite and the harness at each GC stage, the CRC16 rerun only for a uart_link device, passes
--only/--repeat on and exits with the worst result; both refuse a held port 53 before any tool runs."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES, devices_with

REPO_ROOT = Path(__file__).resolve().parent.parent
_RUNNER = "scripts/run_digital_twin_ci.sh"
# @tunable l0.run_digital_twin_ci_sh_timeout_s = 60
_TIMEOUT_S = 60
# The real files the runner sources or runs, and the toolchain files its probe hashes against the record.
_COPIED = ("scripts/run_digital_twin_ci.sh", "scripts/run_unix_port_integration.sh", "scripts/_devices.sh", "scripts/_port_lock.sh", "scripts/_unix_port.sh", "scripts/_archive_evidence.py", "scripts/micropypath.toml")
_INPUTS = ("versions.toml", "setup_toolchain.py", "micropython_overrides.py")
_SUITE, _HARNESS, _ARCHIVE = "scripts/_digital_twin_ci_suite.py", "scripts/_digital_twin_scenarios.py", "scripts/_archive_evidence.py"
# uv as the runner meets it: the archive helper runs for real, every other script is recorded and exits STUB_EXIT_<stem>.
_STUB_UV = """#!{python} -I
import json, os, subprocess, sys
args = sys.argv[1:]
script = next(a for a in args if a.endswith(".py"))
with open(os.environ["STUB_CALLS"], "a", encoding="utf-8") as f:
    f.write(json.dumps(["uv", *args]) + "\\n")
if script == {archive!r}:
    sys.exit(subprocess.run([sys.executable, *args[args.index(script):]], check=False).returncode)
sys.exit(int(os.environ.get("STUB_EXIT_" + os.path.basename(script).removesuffix(".py").lstrip("_").upper(), "0")))
"""
_STUB_RECORDER = """#!{python} -I
import json, os, sys
with open(os.environ["STUB_CALLS"], "a", encoding="utf-8") as f:
    f.write(json.dumps([os.path.basename(sys.argv[0]), *sys.argv[1:]]) + "\\n")
"""
_STUB_BINARY = "#!/bin/sh\necho standard\n"  # the probe's answer of a standard-flavour Unix port


def _calls(sandbox: Path) -> "list[list[str]]":
    path = sandbox / "stub.calls"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def _run(sandbox: Path, *args: str, runner: str = _RUNNER, **exits: int) -> "tuple[subprocess.CompletedProcess[str], list[list[str]]]":
    # One run of a runner in the sandbox, its calls recorded from scratch; `exits` sets a stubbed script's exit code.
    (sandbox / "stub.calls").unlink(missing_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("SENSORS_PORT_LOCK", "STUB_"))}
    env |= {"PATH": f"{sandbox / '.stub_bin'}:{os.environ['PATH']}", "HOME": str(sandbox / "home"), "PICO_TOOLCHAIN_DIR": str(sandbox / "toolchain")}
    env |= {"XDG_RUNTIME_DIR": str(sandbox / "runtime"), "STUB_CALLS": str(sandbox / "stub.calls"), **{f"STUB_EXIT_{k.upper()}": str(v) for k, v in exits.items()}}
    done = subprocess.run(["/bin/bash", str(sandbox / runner), *args], cwd=sandbox, env=env, capture_output=True, text=True, check=False, timeout=_TIMEOUT_S)
    return done, _calls(sandbox)


def _scripts(calls: "list[list[str]]", script: str) -> "list[list[str]]":
    # The uv calls of one script, each from the script's own path on.
    return [call[call.index(script) :] for call in calls if call[0] == "uv" and script in call]


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    # A tree of the runner, its libraries and devices/, a toolchain whose probe answers standard with a current record,
    # and stubs for uv, setcap and the website build that record each call.
    root = tmp_path / "repo"
    for rel in _COPIED:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / rel, root / rel)
    shutil.copytree(REPO_ROOT / "devices", root / "devices", ignore=shutil.ignore_patterns("zz_test_*"))
    (root / "toolchain").mkdir()
    hashes = {}
    for name in _INPUTS:
        shutil.copy2(REPO_ROOT / "toolchain" / name, root / "toolchain" / name)
        hashes[name] = hashlib.sha256((root / "toolchain" / name).read_bytes()).hexdigest()
    binary = root / "toolchain" / "micropython" / "ports" / "unix" / "build-standard" / "micropython"
    stubs = {binary: _STUB_BINARY, root / "scripts" / "build_website.sh": _STUB_RECORDER.format(python=sys.executable)}
    stubs |= {root / ".stub_bin" / "uv": _STUB_UV.format(python=sys.executable, archive=_ARCHIVE), root / ".stub_bin" / "setcap": _STUB_RECORDER.format(python=sys.executable)}
    for path, body in stubs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)
    record = {"input_sha256": hashes, "unix_binaries": ["build-standard"]}
    (root / "toolchain" / "toolchain-record.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    (root / "runtime").mkdir()
    return root


_LINKED = devices_with("uart_link")
_UNLINKED = [d for d in DEVICE_NAMES if d not in _LINKED]


def test_the_devices_previous_logs_are_archived_before_any_build_and_three_runs_kept(sandbox: Path) -> None:
    device, other = DEVICE_NAMES[0], DEVICE_NAMES[1]
    (sandbox / "digital_twin_ci_logs" / other).mkdir(parents=True)
    (sandbox / "digital_twin_ci_logs" / other / "kept.log").write_text("another device's run\n", encoding="utf-8")
    for run in range(4):
        (sandbox / "digital_twin_ci_logs" / device).mkdir(parents=True, exist_ok=True)
        (sandbox / "digital_twin_ci_logs" / device / f"run{run}.log").write_text(f"run {run}\n", encoding="utf-8")
        done, calls = _run(sandbox, device, "--part", "harness")
        assert done.returncode == 0, done.stderr
        archive = next(i for i, call in enumerate(calls) if _ARCHIVE in call)
        built = next(i for i, call in enumerate(calls) if call[0] == "build_website.sh")
        assert archive < built, calls
        assert not (sandbox / "digital_twin_ci_logs" / device / f"run{run}.log").exists()
    runs = sorted((sandbox / "build" / "archive" / f"digital_twin_ci_{device}").iterdir())
    assert [sorted(p.name for p in (run / device).iterdir()) for run in runs] == [["run1.log"], ["run2.log"], ["run3.log"]], runs
    assert (sandbox / "digital_twin_ci_logs" / other / "kept.log").read_text(encoding="utf-8") == "another device's run\n"


@pytest.mark.parametrize(("args", "suite_stage", "harness_stages"), [((), [], ["-1", "32768"]), (("--gc-threshold", "32768"), ["--gc-threshold", "32768"], ["32768"])])
def test_the_suite_and_the_harness_run_at_both_gc_stages_or_the_one_given(sandbox: Path, args: "tuple[str, ...]", suite_stage: "list[str]", harness_stages: "list[str]") -> None:
    # The suite runs both stages itself unless one is named; the harness once per stage, into the device's own logs.
    device = _UNLINKED[0]
    done, calls = _run(sandbox, device, *args)
    assert done.returncode == 0, done.stderr
    (suite,) = _scripts(calls, _SUITE)
    assert suite[suite.index("--logs-dir") + 1] == f"digital_twin_ci_logs/{device}" and suite[suite.index("--logs-dir") + 2 :] == suite_stage, suite
    harness = _scripts(calls, _HARNESS)
    assert [call[call.index("--gc-threshold") + 1] for call in harness] == harness_stages, harness
    assert [call[call.index("--logs-dir") + 1] for call in harness] == [f"digital_twin_ci_logs/{device}/scenarios/gc_threshold_{s.replace('-', 'neg')}" for s in harness_stages]


def test_only_and_repeat_reach_the_suite_alone(sandbox: Path) -> None:
    done, calls = _run(sandbox, _UNLINKED[0], "--only", "9", "--repeat", "2")
    assert done.returncode == 0, done.stderr
    (suite,) = _scripts(calls, _SUITE)
    assert suite[-4:] == ["--only", "9", "--repeat", "2"], suite
    assert all("--only" not in call and "--repeat" not in call for call in _scripts(calls, _HARNESS)), calls


@pytest.mark.parametrize("device", [_LINKED[0], _UNLINKED[0]])
def test_the_crc16_rerun_runs_only_for_a_device_wiring_a_uart_link_pair(sandbox: Path, device: str) -> None:
    done, calls = _run(sandbox, device, "--part", "suite")
    assert done.returncode == 0, done.stderr
    reruns = [call for call in _scripts(calls, _SUITE) if "--device-toml" in call]
    if device not in _LINKED:
        assert reruns == [], reruns
        return
    derived = f"digital_twin_ci_logs/{device}/crc16/{device}.toml"
    assert reruns == [[_SUITE, "--micropython-bin", str(sandbox / "toolchain" / "micropython" / "ports" / "unix" / "build-standard" / "micropython"), "--device", device, "--device-toml", derived, "--only", "3", "--logs-dir", f"digital_twin_ci_logs/{device}/crc16"]], reruns
    text = (sandbox / derived).read_text(encoding="utf-8")
    assert text.count('crc = "crc16"\n') == text.count('driver = "uart_link"\n') > 0, text


@pytest.mark.parametrize(("suite", "harness", "worst"), [(0, 0, 0), (1, 0, 1), (0, 1, 1), (0, 3, 3)])
def test_the_exit_is_the_worst_of_the_runs(sandbox: Path, suite: int, harness: int, worst: int) -> None:
    done, calls = _run(sandbox, _UNLINKED[0], digital_twin_ci_suite=suite, digital_twin_scenarios=harness)
    assert done.returncode == worst, done.stderr
    assert len(_scripts(calls, _HARNESS)) == 2, calls  # a failed suite never skips the harness


@pytest.mark.parametrize("args", [(), ("--part",), ("--part", "neither")], ids=["no-device", "no-value", "bad-value"])
def test_a_missing_device_or_a_bad_option_exits_2_before_any_tool_runs(sandbox: Path, args: "tuple[str, ...]") -> None:
    done, calls = _run(sandbox, *((DEVICE_NAMES[0], *args) if args else ()))
    assert (done.returncode, calls) == (2, []), (done.stderr, calls)
    assert "Usage: scripts/run_digital_twin_ci.sh" in done.stderr, done.stderr


@pytest.mark.parametrize(("args", "parts"), [((), ("suite", "harness")), (("--part", "suite"), ("suite",)), (("--part", "harness"), ("harness",))])
def test_the_ci_runner_builds_the_site_each_part_boots_from(sandbox: Path, args: "tuple[str, ...]", parts: "tuple[str, ...]") -> None:
    # The suite boots frozen_modules/, the harness the device's own site under build/generated_html/: each part builds its own.
    device = _UNLINKED[0]
    done, calls = _run(sandbox, device, *args)
    assert done.returncode == 0, done.stderr
    want = {"suite": ["build_website.sh", device], "harness": ["build_website.sh", device, f"build/generated_html/{device}/frozen_html.py"]}
    assert [call for call in calls if call[0] == "build_website.sh"] == [want[part] for part in parts]


@pytest.mark.parametrize(("runner", "args"), [(_RUNNER, (DEVICE_NAMES[0],)), ("scripts/run_unix_port_integration.sh", ("--device", DEVICE_NAMES[0]))])
def test_a_held_port_53_fails_a_twin_runner_at_once_naming_it_before_any_tool_runs(sandbox: Path, runner: str, args: "tuple[str, ...]") -> None:
    holder = subprocess.Popen(["sleep", "60"])  # noqa: S607 - coreutils sleep, the stand-in holder's process
    lock = sandbox / "runtime" / "sensors-port-53.lock"
    lock.mkdir()
    (lock / "runner").write_text("another suite\n", encoding="utf-8")
    (lock / "pid").write_text(f"{holder.pid}\n", encoding="utf-8")
    try:
        done, calls = _run(sandbox, *args, runner=runner)
    finally:
        holder.kill()
        holder.wait()
    assert (done.returncode, calls) == (1, []), (done.stderr, calls)
    assert "port 53 is held by another suite" in done.stderr, done.stderr
