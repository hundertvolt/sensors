"""tests_js/_twin_process.js's spawnTwin(): a string the Unix port interns before the runner starts and cannot (an
argument, the runner's directory, a MICROPYPATH entry) is refused before anything is probed, locked or started, naming
it and the limit (scripts/_twin_process.py's). Driven by Node on a copy in a throwaway tree with a stub interpreter."""

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
_LAUNCH = "tests_js/_twin_process.js"
# The launch frame, the modules it imports and the files it reads or runs, copied into each throwaway tree.
_COPIED = (_LAUNCH, "tests_js/_micropypath.js", "tests_js/_port_lock.js", "tests_js/_twin_start_failure.js", "scripts/_unix_port.sh", "scripts/micropypath.toml", "package.json")
_LIMIT = twin_process._QSTR_MAX_BYTES
_OVER = "x" * (_LIMIT + 1)


def _spawn(tmp_path: Path, *, device: str = "fixture-device", config_dir: str = "", root_dir: str = "repo", layout: str = "", home: bool = True) -> "tuple[dict[str, object], list[str]]":
    # One spawnTwin() in a fresh Node, waited out and stopped: what it threw or how the stub exited, and the stub's log,
    # one line per call (the probe's -c call as "probe"). root_dir places the copy; layout's entries lead its twin line.
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
    interpreter.write_text(f'#!/usr/bin/env bash\nif [ "${{1:-}}" = -c ]; then echo probe >>{shlex.quote(str(log))}; echo standard; exit 0; fi\necho "micropython $*" >>{shlex.quote(str(log))}\n', encoding="utf-8")
    interpreter.chmod(0o755)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    env = {name: value for name, value in os.environ.items() if not name.startswith("SENSORS_PORT_LOCK") and (home or name != "HOME")}
    env.update({"PICO_TOOLCHAIN_DIR": str(tmp_path / "toolchain"), "XDG_RUNTIME_DIR": str(runtime)})
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
    assert list(runtime.iterdir()) == [], "the launch left a port lock behind"
    outcome = json.loads(done.stdout.strip().splitlines()[-1])
    assert isinstance(outcome, dict), outcome
    return outcome, log.read_text(encoding="utf-8").splitlines() if log.exists() else []


@pytest.mark.parametrize(
    ("case", "named"),
    [
        ("device", "--device's value (256 bytes)"),
        ("multibyte device", "--device's value (256 bytes)"),
        ("config directory", "--config-dir's value"),
        ("micropypath entry", "MICROPYPATH entry 1 (256 bytes)"),
        ("home-relative entry without HOME", "MICROPYPATH entry 1 (258 bytes)"),
        ("runner's directory", "the runner's directory"),
    ],
)
def test_a_string_the_interpreter_cannot_intern_is_refused_before_anything_starts(tmp_path: Path, case: str, named: str) -> None:
    # Each kills the interpreter before the runner's first line ("FATAL: uncaught NLR", exit 1), which read as a twin that
    # "exited before ever serving"; a byte count, not characters, is what the interpreter measures.
    device, config_dir, layout, root_dir, home = "fixture-device", "", "", "repo", True
    if case == "device":
        device = _OVER
    elif case == "multibyte device":
        device = "é" * ((_LIMIT + 1) // 2)
    elif case == "config directory":
        config_dir = str(tmp_path / ("c" * 250))
        named += f" ({len(os.fsencode(config_dir))} bytes)"
    elif case == "micropypath entry":
        layout = _OVER
    elif case == "home-relative entry without HOME":
        layout, home = f"~/{_OVER}", False
    else:
        root_dir = f"{'r' * 200}/repo"
        named += f" ({len(os.fsencode(os.path.realpath(tmp_path / root_dir / 'digital_twin')))} bytes)"
    outcome, calls = _spawn(tmp_path, device=device, config_dir=config_dir, root_dir=root_dir, layout=layout, home=home)
    refused = str(outcome.get("refused", outcome))
    assert refused.startswith("the twin was not started: ") and named in refused, refused
    assert refused.endswith(f"- the Unix port interns each as a qstr of at most {_LIMIT} bytes and dies before the runner starts"), refused
    assert calls == [], f"spawnTwin() probed or started the interpreter before refusing: {calls}"


def test_a_string_at_the_limit_or_one_the_interpreter_expands_still_starts(tmp_path: Path) -> None:
    # The boundary's other side: 255 bytes everywhere, and a ~/ entry the interpreter builds from $HOME, never interns.
    at_limit = "x" * _LIMIT
    config_dir = str(tmp_path / ("c" * (_LIMIT - len(os.fsencode(str(tmp_path))) - 1)))
    outcome, calls = _spawn(tmp_path, config_dir=config_dir, layout=f"{at_limit}:~/{_OVER}")
    assert outcome == {"exited": 0} and len(os.fsencode(config_dir)) == _LIMIT, outcome
    assert calls[0] == "probe" and calls[1].endswith(f"--config-dir {config_dir}") and len(calls) == 2, calls


def test_the_launchs_limit_is_the_python_launchs_own() -> None:
    # The JS copy of the qstr limit is scripts/_twin_process.py's, which is checked against the interpreter itself.
    copies = re.findall(r"^const QSTR_MAX_BYTES = (\d+);", (REPO_ROOT / _LAUNCH).read_text(encoding="utf-8"), re.MULTILINE)
    assert copies == [str(_LIMIT)], f"{_LAUNCH} holds the qstr limit {copies}, scripts/_twin_process.py {_LIMIT}"
