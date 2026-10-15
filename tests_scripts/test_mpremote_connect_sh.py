"""scripts/mpremote_connect.sh with a stub `uv` on PATH: $MPREMOTE_DEVICE wins and no resolver runs, else the board
`toolchain/setup_toolchain.py board` prints is the one connected, and a resolver that finds none or several stops the run
with its own message before mpremote starts."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Logs each call as written; the resolver prints $STUB_BOARD, or fails with the resolver's own line when it is empty.
_STUB_UV = """#!{python}
import json, os, sys
with open(os.environ["STUB_CALLS"], "a") as calls:
    calls.write(json.dumps(sys.argv[1:]) + "\\n")
if sys.argv[1:] == ["run", "--no-sync", "toolchain/setup_toolchain.py", "board"]:
    board = os.environ.get("STUB_BOARD", "")
    if not board:
        sys.exit("setup_toolchain: no MicroPython board found (stub)")
    print(board)
sys.exit(0)
"""


def _run(repo_root: Path, tmp_path: Path, *args: str, **env_extra: str) -> "tuple[subprocess.CompletedProcess[str], list[list[str]]]":
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    stub = bin_dir / "uv"
    stub.write_text(_STUB_UV.format(python=sys.executable), encoding="utf-8")
    stub.chmod(0o755)
    calls = tmp_path / "calls.jsonl"
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "STUB_CALLS": str(calls)}
    for name in ("MPREMOTE_DEVICE", "STUB_BOARD"):
        env.pop(name, None)
    env.update(env_extra)
    result = subprocess.run(["/bin/bash", str(repo_root / "scripts" / "mpremote_connect.sh"), *args], capture_output=True, text=True, check=False, env=env, cwd=tmp_path, timeout=60)
    return result, [json.loads(line) for line in calls.read_text(encoding="utf-8").splitlines()] if calls.exists() else []


def test_mpremote_device_wins_and_no_resolver_runs(repo_root: Path, tmp_path: Path) -> None:
    result, calls = _run(repo_root, tmp_path, "exec", "print(1)", MPREMOTE_DEVICE="/dev/fixture-board", STUB_BOARD="/dev/fixture-other")
    assert result.returncode == 0, result.stderr
    assert calls == [["run", "--no-sync", "mpremote", "connect", "/dev/fixture-board", "exec", "print(1)"]]


def test_without_mpremote_device_the_resolvers_board_is_connected(repo_root: Path, tmp_path: Path) -> None:
    result, calls = _run(repo_root, tmp_path, "ls", STUB_BOARD="/dev/serial/by-id/fixture-board")
    assert result.returncode == 0, result.stderr
    assert calls == [["run", "--no-sync", "toolchain/setup_toolchain.py", "board"], ["run", "--no-sync", "mpremote", "connect", "/dev/serial/by-id/fixture-board", "ls"]]


def test_a_failed_resolution_exits_1_with_the_resolvers_message_and_no_mpremote(repo_root: Path, tmp_path: Path) -> None:
    result, calls = _run(repo_root, tmp_path, "ls")
    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stderr == "setup_toolchain: no MicroPython board found (stub)\n", "the resolver's own line reaches the user unchanged"
    assert calls == [["run", "--no-sync", "toolchain/setup_toolchain.py", "board"]]


@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help_names_the_resolver_and_runs_nothing(repo_root: Path, tmp_path: Path, flag: str) -> None:
    result, calls = _run(repo_root, tmp_path, flag)
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("Usage: scripts/mpremote_connect.sh"), result.stdout
    assert "MPREMOTE_DEVICE" in result.stdout and "toolchain/setup_toolchain.py board" in result.stdout, result.stdout
    assert calls == []
