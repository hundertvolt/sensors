"""scripts/uv_sync_retried.sh with stub `uv` and `sleep` as the whole PATH: a sync failing twice passes on the third
attempt after 10 s and 20 s pauses, three failures end with the last attempt's own exit code, and the attempts and
pause step equal toolchain/setup_toolchain.py's, so the script stays the one retry definition CI and the runners share."""

import inspect
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from _script_loader import load_script_module

_SCRIPT = Path("scripts") / "uv_sync_retried.sh"
_SYNC = "uv sync --locked"
# Fails its first $STUB_FAILS calls with exit 3 (any code but 1 shows the last attempt's own code is kept).
_STUB_UV = """#!/bin/bash
echo "uv $*" >>"$STUB_CALLS"
count=0
while IFS= read -r line; do
    [[ "$line" != uv\\ * ]] || count=$((count + 1))
done <"$STUB_CALLS"
[ "$count" -gt "$STUB_FAILS" ] || exit 3
"""


def _literal(repo_root: Path, tag: str) -> int:
    # The integer on the line under the script's tag line for `tag`, checked equal to the tag's own value.
    found = re.search(rf"^# @tunable {re.escape(tag)} = (\d+)\n\w+=(\d+)$", (repo_root / _SCRIPT).read_text(encoding="utf-8"), re.MULTILINE)
    assert found and found.group(1) == found.group(2), f"{_SCRIPT} has no `{tag}` tag over its literal"
    return int(found.group(2))


def _run(repo_root: Path, tmp_path: Path, fails: int, *args: str) -> "tuple[subprocess.CompletedProcess[str], list[str]]":
    # The stubs are the whole PATH: no real uv can run, and no real pause is taken.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "calls"
    calls.touch()
    (bin_dir / "uv").write_text(_STUB_UV, encoding="utf-8")
    (bin_dir / "sleep").write_text('#!/bin/bash\necho "sleep $*" >>"$STUB_CALLS"\n', encoding="utf-8")
    (bin_dir / "dirname").write_text(f'#!/bin/bash\nexec {shutil.which("dirname")} "$@"\n', encoding="utf-8")
    for stub in bin_dir.iterdir():
        stub.chmod(0o755)
    env = {"PATH": str(bin_dir), "HOME": str(tmp_path), "STUB_CALLS": str(calls), "STUB_FAILS": str(fails)}
    done = subprocess.run(["/bin/bash", str(repo_root / _SCRIPT), *args], capture_output=True, text=True, check=False, env=env, cwd=tmp_path, timeout=60)
    return done, calls.read_text(encoding="utf-8").splitlines()


def test_a_sync_failing_twice_passes_on_the_third_attempt_after_10_and_20_s(repo_root: Path, tmp_path: Path) -> None:
    done, calls = _run(repo_root, tmp_path, 2)
    assert done.returncode == 0, done.stderr
    assert calls == [_SYNC, "sleep 10", _SYNC, "sleep 20", _SYNC]
    assert "uv sync failed on attempt 2/3; retrying in 20s" in done.stderr, done.stderr


def test_three_failures_end_with_the_last_attempts_own_exit_code(repo_root: Path, tmp_path: Path) -> None:
    done, calls = _run(repo_root, tmp_path, 3)
    assert done.returncode == 3, "the last attempt's exit code is the script's"
    assert calls == [_SYNC, "sleep 10", _SYNC, "sleep 20", _SYNC]


def test_a_first_attempt_that_passes_pauses_nowhere_and_arguments_reach_uv(repo_root: Path, tmp_path: Path) -> None:
    done, calls = _run(repo_root, tmp_path, 0, "--no-dev")
    assert done.returncode == 0, done.stderr
    assert calls == [f"{_SYNC} --no-dev"]


def test_the_attempts_and_pause_step_equal_the_installers(repo_root: Path) -> None:
    setup_toolchain = load_script_module(repo_root / "toolchain" / "setup_toolchain.py", "setup_toolchain")
    assert _literal(repo_root, "tool.uv_sync_attempts") == setup_toolchain.NETWORK_ATTEMPTS
    assert _literal(repo_root, "tool.uv_sync_backoff_step_s") == inspect.signature(setup_toolchain.run_retried).parameters["backoff_s"].default


@pytest.mark.parametrize("path", [".github/workflows/ci.yml", ".github/actions/setup-micropython-toolchain/action.yml", ".github/actions/uv-sync/action.yml"])
def test_no_ci_file_carries_a_retry_loop_of_its_own(repo_root: Path, path: str) -> None:
    assert "for attempt in" not in (repo_root / path).read_text(encoding="utf-8"), f"{path}: call scripts/uv_sync_retried.sh (through the uv-sync action) instead"
