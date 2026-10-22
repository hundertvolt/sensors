"""scripts/mpremote_connect.sh with a stub `uv` on PATH: one retried sync first, then $MPREMOTE_DEVICE wins and no
resolver runs, else the board `toolchain/setup_toolchain.py board` prints is the one connected, and a resolver that
finds none or several stops the run with its own message before mpremote starts."""

import os
import subprocess
from pathlib import Path

import pytest

_SYNC = ["sync", "--locked"]
# Logs each call as written (NUL-separated, its argument count first); the resolver prints $STUB_BOARD, or fails with
# the resolver's own line when it is empty. In bash, so a call starts no interpreter.
_STUB_UV = """#!/bin/bash
printf '%s\\0' "$#" "$@" >>"$STUB_CALLS"
if [ "$*" = "sync --locked" ]; then
    exit "${STUB_SYNC_EXIT:-0}"
fi
if [ "$*" = "run --no-sync toolchain/setup_toolchain.py board" ]; then
    [ -n "${STUB_BOARD:-}" ] || { echo "setup_toolchain: no MicroPython board found (stub)" >&2; exit 1; }
    echo "$STUB_BOARD"
fi
exit 0
"""


def _run(repo_root: Path, tmp_path: Path, *args: str, **env_extra: str) -> "tuple[subprocess.CompletedProcess[str], list[list[str]]]":
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    stub = bin_dir / "uv"
    stub.write_text(_STUB_UV, encoding="utf-8")
    # The retried sync's pauses are taken by a stub, never waited out.
    (bin_dir / "sleep").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    for written in (stub, bin_dir / "sleep"):
        written.chmod(0o755)
    calls = tmp_path / "calls"
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "STUB_CALLS": str(calls)}
    for name in ("MPREMOTE_DEVICE", "STUB_BOARD"):
        env.pop(name, None)
    env.update(env_extra)
    result = subprocess.run(["/bin/bash", str(repo_root / "scripts" / "mpremote_connect.sh"), *args], capture_output=True, text=True, check=False, env=env, cwd=tmp_path, timeout=60)
    fields = calls.read_text(encoding="utf-8").split("\0")[:-1] if calls.exists() else []
    logged, at = [], 0
    while at < len(fields):
        logged.append(fields[at + 1 : at + 1 + int(fields[at])])
        at += 1 + int(fields[at])
    return result, logged


def test_mpremote_device_wins_and_no_resolver_runs(repo_root: Path, tmp_path: Path) -> None:
    result, calls = _run(repo_root, tmp_path, "exec", "print(1)", MPREMOTE_DEVICE="/dev/fixture-board", STUB_BOARD="/dev/fixture-other")
    assert result.returncode == 0, result.stderr
    assert calls == [_SYNC, ["run", "--no-sync", "mpremote", "connect", "/dev/fixture-board", "exec", "print(1)"]]


def test_without_mpremote_device_the_resolvers_board_is_connected(repo_root: Path, tmp_path: Path) -> None:
    result, calls = _run(repo_root, tmp_path, "ls", STUB_BOARD="/dev/serial/by-id/fixture-board")
    assert result.returncode == 0, result.stderr
    assert calls == [_SYNC, ["run", "--no-sync", "toolchain/setup_toolchain.py", "board"], ["run", "--no-sync", "mpremote", "connect", "/dev/serial/by-id/fixture-board", "ls"]]


def test_a_failed_resolution_exits_1_with_the_resolvers_message_and_no_mpremote(repo_root: Path, tmp_path: Path) -> None:
    result, calls = _run(repo_root, tmp_path, "ls")
    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stderr == "setup_toolchain: no MicroPython board found (stub)\n", "the resolver's own line reaches the user unchanged"
    assert calls == [_SYNC, ["run", "--no-sync", "toolchain/setup_toolchain.py", "board"]]


def test_a_sync_failing_every_attempt_exits_1_before_any_board_call(repo_root: Path, tmp_path: Path) -> None:
    result, calls = _run(repo_root, tmp_path, "ls", MPREMOTE_DEVICE="/dev/fixture-board", STUB_SYNC_EXIT="2")
    assert result.returncode == 1, "a failed sync is a failed run (1), never uv's own 2, which reads as a usage error"
    assert calls == [_SYNC] * 3
    assert "error: the retried uv sync failed" in result.stderr, result.stderr


@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help_names_the_resolver_and_runs_nothing(repo_root: Path, tmp_path: Path, flag: str) -> None:
    result, calls = _run(repo_root, tmp_path, flag)
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("Usage: scripts/mpremote_connect.sh"), result.stdout
    assert "MPREMOTE_DEVICE" in result.stdout and "toolchain/setup_toolchain.py board" in result.stdout, result.stdout
    assert calls == []
