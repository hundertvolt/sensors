"""scripts/run_unix_port_integration.sh boots only the device it is told to (without one, or one no devices/*.toml
carries, it exits 2 naming those it can boot) and nothing the Unix port cannot intern: it exits 1 naming the string, its
bytes and the limit. Driven on a copy in a throwaway tree, its build steps, setcap and interpreter stubbed."""

import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

import scripts._twin_process as twin_process

REPO_ROOT = Path(__file__).resolve().parent.parent
_RUNNER = "scripts/run_unix_port_integration.sh"
_USAGE = "Usage: scripts/run_unix_port_integration.sh --device <name> [flags forwarded to the twin]"
_VALID = "valid devices: fixture_device_a fixture_device_b"
# The real files the runner sources, and the toolchain files its probe hashes against the record.
_COPIED = (_RUNNER, "scripts/_devices.sh", "scripts/_port_lock.sh", "scripts/_unix_port.sh", "scripts/micropypath.toml")
_INPUTS = ("versions.toml", "setup_toolchain.py", "micropython_overrides.py")
_LIMIT = twin_process._QSTR_MAX_BYTES
_OVER = "x" * (_LIMIT + 1)


def _launch(tmp_path: Path, *args: str, root_dir: str = "repo", device: str = "", layout: str = "", home: bool = True) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    # Runs the copy (under root_dir, with device's toml too and layout's entries first in the twin line) beside its
    # libraries and a probe answering standard with a current record; returns the run and the stubs' log, one
    # "<stub> <args>" per call.
    root = tmp_path / root_dir
    for rel in (*_COPIED, *(f"toolchain/{name}" for name in _INPUTS)):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / rel, root / rel)
    (root / "digital_twin").mkdir()
    (root / "digital_twin" / "run_generic_integration.py").write_text("", encoding="utf-8")  # the stub interpreter never reads it
    if layout:
        toml = root / "scripts" / "micropypath.toml"
        toml.write_text(toml.read_text(encoding="utf-8").replace('\ntwin = "', f'\ntwin = "{layout}:'), encoding="utf-8")
    hashes = {name: hashlib.sha256((root / "toolchain" / name).read_bytes()).hexdigest() for name in _INPUTS}
    (tmp_path / "toolchain").mkdir()
    (tmp_path / "toolchain" / "toolchain-record.json").write_text(json.dumps({"input_sha256": hashes, "unix_binaries": ["build-standard"]}, indent=2) + "\n", encoding="utf-8")
    (root / "devices").mkdir()
    for name in sorted({"fixture_device_b", "fixture_device_a", "zz_test_leaked", device} - {""}):
        (root / "devices" / f"{name}.toml").write_text("# fixture\n", encoding="utf-8")
    log = tmp_path / "calls"
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    interpreter = tmp_path / "toolchain" / "micropython" / "ports" / "unix" / "build-standard" / "micropython"
    stub_bin = tmp_path / "stub_bin"
    stubs = {
        stub_bin / "uv": "uv",
        stub_bin / "setcap": "setcap",
        stub_bin / "sudo": "sudo",
        root / "scripts" / "build_website.sh": "build_website.sh",
        # The interpreter also logs whether port 53's lock is held while it runs.
        interpreter: 'micropython held=$(test -d "$XDG_RUNTIME_DIR/sensors-port-53.lock" && echo 53)',
    }
    for path, line in stubs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        probe = 'if [ "${1:-}" = -c ]; then echo standard; exit 0; fi\n' if path == interpreter else ""
        path.write_text(f'#!/usr/bin/env bash\n{probe}echo "{line} $*" >>{shlex.quote(str(log))}\n', encoding="utf-8")
        path.chmod(0o755)
    env = {name: value for name, value in os.environ.items() if not name.startswith("SENSORS_PORT_LOCK")}
    env.update({"PATH": f"{stub_bin}:{os.environ['PATH']}", "HOME": str(tmp_path), "PICO_TOOLCHAIN_DIR": str(tmp_path / "toolchain"), "XDG_RUNTIME_DIR": str(runtime), "LC_ALL": "C.UTF-8"})
    if not home:
        del env["HOME"]
    done = subprocess.run(["/bin/bash", str(root / _RUNNER), *args], cwd=root, env=env, capture_output=True, text=True, check=False, timeout=60)
    assert list(runtime.iterdir()) == [], "the runner's exit left a port lock behind"
    return done, log.read_text(encoding="utf-8").splitlines() if log.exists() else []


@pytest.mark.parametrize(
    ("args", "stderr"),
    [
        ((), ["error: --device is required", _USAGE, _VALID]),
        (("--port", "9000"), ["error: --device is required", _USAGE, _VALID]),
        (("--device",), ["error: --device needs a device name", _USAGE, _VALID]),
        (("--device", ""), [f"error: no devices/.toml - {_VALID}"]),
        (("--device", "no_such_device"), [f"error: no devices/no_such_device.toml - {_VALID}"]),
        (("--device", "zz_test_leaked"), [f"error: no devices/zz_test_leaked.toml - {_VALID}"]),
    ],
    ids=["none", "only-forwarded-flags", "flag-without-value", "empty-value", "unknown", "reserved-fixture"],
)
def test_a_missing_or_unknown_device_exits_2_naming_the_valid_ones_and_runs_nothing(tmp_path: Path, args: tuple[str, ...], stderr: list[str]) -> None:
    done, calls = _launch(tmp_path, *args)
    assert (done.returncode, done.stderr.splitlines(), done.stdout) == (2, stderr, ""), done.stderr
    assert calls == [], f"the runner went on with no valid device: {calls}"


def test_the_named_device_is_built_generated_and_booted_with_the_other_flags_forwarded(tmp_path: Path) -> None:
    done, calls = _launch(tmp_path, "--port", "9000", "--device", "fixture_device_b", "--fault", "sgp40:writeto")
    assert done.returncode == 0, done.stderr
    assert not [call for call in calls if "setup_toolchain.py" in call], f"a current toolchain was set up again: {calls}"
    module = "sensortask_fixture_device_b"
    plan = f"build/generated_src/{module}_wiring_plan.json"
    assert calls[-3:] == [
        "build_website.sh fixture_device_b build/generated_html/fixture_device_b/frozen_html.py",
        "uv run --no-sync scripts/_generate_sensortask_modules.py",
        f"micropython held=53 digital_twin/run_generic_integration.py --module {module} --wiring-plan {plan} --device fixture_device_b --port 9000 --fault sgp40:writeto",
    ], calls


@pytest.mark.parametrize(
    ("case", "named"),
    [
        ("long device", "--wiring-plan's value (278 bytes)"),
        ("forwarded value", "--fault's value (256 bytes)"),
        ("multibyte forwarded value", "--fault's value (256 bytes)"),
        ("forwarded argument", "argument 7 (256 bytes)"),
        ("micropypath entry", "MICROPYPATH entry 1 (256 bytes)"),
        ("home-relative entry without HOME", "MICROPYPATH entry 1 (258 bytes)"),
        ("runner's directory", "the runner's directory"),
    ],
)
def test_a_string_the_interpreter_cannot_intern_exits_1_naming_it_before_anything_runs(tmp_path: Path, case: str, named: str) -> None:
    # Each kills the interpreter before the runner's first line ("FATAL: uncaught NLR", exit 1), after the lock, the builds
    # and setcap: refused before all of them, in bytes as the interpreter measures, under a UTF-8 locale.
    device, layout, root_dir, home = "fixture_device_b", "", "repo", True
    args: tuple[str, ...] = ()
    if case == "long device":
        device = "d" * 230
    elif case == "forwarded value":
        args = ("--fault", _OVER)
    elif case == "multibyte forwarded value":
        args = ("--fault", "\u00e9" * ((_LIMIT + 1) // 2))
    elif case == "forwarded argument":
        args = (_OVER,)
    elif case == "micropypath entry":
        layout = _OVER
    elif case == "home-relative entry without HOME":
        layout, home = f"~/{_OVER}", False
    else:
        root_dir = f"{'r' * 200}/repo"
        named += f" ({len(os.fsencode(os.path.realpath(tmp_path / root_dir / 'digital_twin')))} bytes)"
    done, calls = _launch(tmp_path, "--device", device, *args, root_dir=root_dir, device=device, layout=layout, home=home)
    assert (done.returncode, done.stdout, calls) == (1, "", []), (done.stderr, calls)
    assert done.stderr.startswith("error: the twin was not started: ") and named in done.stderr, done.stderr
    assert f"- the Unix port interns each as a qstr of at most {_LIMIT} bytes and dies before the runner starts\n" in done.stderr, done.stderr


def test_a_string_at_the_limit_or_one_the_interpreter_expands_still_boots(tmp_path: Path) -> None:
    # The boundary's other side: 255 bytes everywhere, and a ~/ entry the interpreter builds from $HOME, never interns.
    at_limit = "x" * _LIMIT
    done, calls = _launch(tmp_path, "--device", "fixture_device_b", "--fault", at_limit, layout=f"{at_limit}:~/{_OVER}")
    assert done.returncode == 0, done.stderr
    assert calls[-1].endswith(f"--device fixture_device_b --fault {at_limit}"), calls


def test_the_runners_limit_is_the_twin_launchs_own() -> None:
    # The runner's copy of the qstr limit is scripts/_twin_process.py's, which is checked against the interpreter itself.
    copies = re.findall(r"^qstr_max_bytes=(\d+)$", (REPO_ROOT / _RUNNER).read_text(encoding="utf-8"), re.MULTILINE)
    assert copies == [str(_LIMIT)], f"{_RUNNER} holds the qstr limit {copies}, scripts/_twin_process.py {_LIMIT}"
