"""scripts/run_unix_port_integration.sh boots the device it is told to and no other: without --device, with an empty one
or with a name no devices/*.toml carries, it exits 2 naming the devices it can boot and runs nothing. Driven on a copy
in a throwaway tree whose build steps, setcap and interpreter are stubs that log what they were handed."""

import hashlib
import json
import os
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
_RUNNER = "scripts/run_unix_port_integration.sh"
_USAGE = "Usage: scripts/run_unix_port_integration.sh --device <name> [flags forwarded to the twin]"
_VALID = "valid devices: fixture_device_a fixture_device_b"
# The real files the runner sources, and the toolchain files its probe hashes against the record.
_COPIED = (_RUNNER, "scripts/_devices.sh", "scripts/_port_lock.sh", "scripts/_unix_port.sh", "scripts/micropypath.toml")
_INPUTS = ("versions.toml", "setup_toolchain.py", "micropython_overrides.py")


def _launch(tmp_path: Path, *args: str) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    # Runs the copy beside its libraries and a toolchain whose probe answers standard with a current record; returns the
    # run and the stubs' log, one "<stub> <args>" line per call (the probe's -c call is answered, not logged).
    root = tmp_path / "repo"
    for rel in (*_COPIED, *(f"toolchain/{name}" for name in _INPUTS)):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / rel, root / rel)
    hashes = {name: hashlib.sha256((root / "toolchain" / name).read_bytes()).hexdigest() for name in _INPUTS}
    (tmp_path / "toolchain").mkdir()
    (tmp_path / "toolchain" / "toolchain-record.json").write_text(json.dumps({"input_sha256": hashes, "unix_binaries": ["build-standard"]}, indent=2) + "\n", encoding="utf-8")
    (root / "devices").mkdir()
    for name in ("fixture_device_b", "fixture_device_a", "zz_test_leaked"):
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
    env.update({"PATH": f"{stub_bin}:{os.environ['PATH']}", "HOME": str(tmp_path), "PICO_TOOLCHAIN_DIR": str(tmp_path / "toolchain"), "XDG_RUNTIME_DIR": str(runtime)})
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
