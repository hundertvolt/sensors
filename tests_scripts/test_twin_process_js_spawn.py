"""tests_js/_twin_process.js's spawnTwin(): a caller's TEST_TWIN_HOST never reaches the twin. Driven by Node on a copy
in a throwaway tree with a stub interpreter."""

import json
import os
import shlex
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_LAUNCH = "tests_js/_twin_process.js"
# The launch frame, the modules it imports and the files it reads or runs, copied into each throwaway tree.
_COPIED = (_LAUNCH, "tests_js/_micropypath.js", "tests_js/_port_lock.js", "tests_js/_twin_start_failure.js", "scripts/_unix_port.sh", "scripts/micropypath.toml", "scripts/memory_markers.json", "package.json")


def _spawn(tmp_path: Path, *, device: str = "fixture-device", config_dir: str = "", root_dir: str = "repo", layout: str = "", home: bool = True, caller_env: "dict[str, str] | None" = None) -> "tuple[dict[str, object], list[str]]":
    # One spawnTwin() in a fresh Node, waited out and stopped: what it threw or how the stub exited, and the stub's log,
    # one line per call (the probe's -c call as "probe"); the twin writes its TEST_TWIN_HOST to tmp_path/twin_host.
    # root_dir places the copy; layout's entries lead its twin line; caller_env goes over the caller's own environment.
    root = tmp_path / root_dir
    for rel in _COPIED:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / rel, root / rel)
    (root / "digital_twin").mkdir()
    (root / "digital_twin" / "run_generic_integration.py").write_text("", encoding="utf-8")  # the stub interpreter never reads it
    if layout:
        toml = root / "scripts" / "micropypath.toml"
        toml.write_text(toml.read_text(encoding="utf-8").replace('\ntwin = "', f'\ntwin = "{layout}:'), encoding="utf-8")
    log = tmp_path / "calls"
    interpreter = tmp_path / "toolchain" / "micropython" / "ports" / "unix" / "build-standard" / "micropython"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text(f'#!/usr/bin/env bash\nif [ "${{1:-}}" = -c ]; then echo probe >>{shlex.quote(str(log))}; echo standard; exit 0; fi\necho "${{TEST_TWIN_HOST-<unset>}}" >{shlex.quote(str(tmp_path / "twin_host"))}\necho "micropython $*" >>{shlex.quote(str(log))}\n', encoding="utf-8")
    interpreter.chmod(0o755)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    env = {name: value for name, value in os.environ.items() if not name.startswith("SENSORS_PORT_LOCK") and (home or name != "HOME")}
    env.update({"PICO_TOOLCHAIN_DIR": str(tmp_path / "toolchain"), "XDG_RUNTIME_DIR": str(runtime), **(caller_env or {})})
    twin = json.dumps({"device": device, "port": 20000, "configDir": config_dir or str(tmp_path / "config")})
    script = (
        f"import {{ spawnTwin, stopTwin }} from {json.dumps((root / _LAUNCH).as_uri())};\nlet outcome;\n"
        f"try {{\n    const proc = spawnTwin({twin});\n    await new Promise((resolve) => {{ proc.once('exit', resolve); }});\n"
        "    await stopTwin(proc);\n    outcome = { exited: proc.exitCode };\n} catch (err) {\n    outcome = { refused: err.message };\n}\n"
        "console.log(JSON.stringify(outcome));"
    )
    node = shutil.which("node")
    assert node is not None, "node is not on PATH - the live tier this launch serves cannot run without it either"
    done = subprocess.run([node, "--input-type=module", "-e", script], cwd=root, env=env, capture_output=True, text=True, check=False, timeout=60)
    assert done.returncode == 0, done.stderr
    flock = shutil.which("flock") or "/usr/bin/flock"
    assert all(subprocess.run([flock, "-n", str(lock), "true"], check=False).returncode == 0 for lock in runtime.glob("*.flock")), "the launch left a port lock held"
    outcome = json.loads(done.stdout.strip().splitlines()[-1])
    assert isinstance(outcome, dict), outcome
    return outcome, log.read_text(encoding="utf-8").splitlines() if log.exists() else []


def test_a_callers_twin_host_never_reaches_the_twin(tmp_path: Path) -> None:
    # TEST_TWIN_HOST is scripts/test.sh's address for each of its own jobs: a caller's would bind the twin's captive DNS
    # there, off the HOST every live test reaches the twin at and the 127.0.0.1 that port 53's lock assumes.
    outcome, calls = _spawn(tmp_path, caller_env={"TEST_TWIN_HOST": "127.0.0.77"})
    assert outcome == {"exited": 0} and len(calls) == 2, (outcome, calls)
    seen = (tmp_path / "twin_host").read_text(encoding="utf-8")
    assert seen == "<unset>\n", f"the caller's TEST_TWIN_HOST reached the twin's environment: {seen!r}"
