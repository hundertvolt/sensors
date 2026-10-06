"""scripts/typecheck.sh ends every run with the summary block (SPECIFICATION.md E.10): each pass is a
counted check, and a step that aborts the run is named by its stage. Driven on a copy of the script
in a stand-in repo, with mypy, uv and python3 stubbed, so nothing is installed or generated."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _run(tmp_path: Path, *args: str, mypy_fails_on: str = "", uv_install_fails: bool = False) -> subprocess.CompletedProcess[str]:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    for name in ("typecheck.sh", "_summary_block.sh"):
        shutil.copy(REPO_ROOT / "scripts" / name, root / "scripts" / name)
    stub_bin = tmp_path / "stub_bin"
    stub_bin.mkdir()
    stubs = {
        # Fails only the pass whose arguments contain mypy_fails_on (empty: none fails).
        "mypy": f'#!/usr/bin/env bash\nif [ -n "{mypy_fails_on}" ] && [[ "$*" == *"{mypy_fails_on}"* ]]; then echo "error: planted"; exit 1; fi\nexit 0\n',
        "uv": f'#!/usr/bin/env bash\nif [ "$1" = "pip" ]; then exit {1 if uv_install_fails else 0}; fi\nexit 0\n',
        "python3": "#!/usr/bin/env bash\ncat >/dev/null\necho 1.29.0\n",
    }
    for name, body in stubs.items():
        (stub_bin / name).write_text(body)
        (stub_bin / name).chmod(0o755)
    env = {**os.environ, "PATH": f"{stub_bin}:{os.environ['PATH']}", "GIT_CEILING_DIRECTORIES": str(tmp_path)}
    return subprocess.run(["/bin/bash", str(root / "scripts" / "typecheck.sh"), *args], env=env, capture_output=True, text=True, check=False, timeout=60)


def _block(out: str) -> str:
    return out[out.index("== Summary: scripts/typecheck.sh ==") :]


def test_a_clean_run_counts_every_step_and_exits_0(tmp_path: Path) -> None:
    done = _run(tmp_path)
    assert done.returncode == 0, done.stdout + done.stderr
    block = _block(done.stdout)
    assert "\nCounts (checks): passed 7 · failed 0 ·" in block
    assert block.endswith("Result: PASS\nExit code: 0\n")


def test_a_failing_twin_pass_is_named_and_fails_the_run(tmp_path: Path) -> None:
    done = _run(tmp_path, mypy_fails_on="digital_twin/typecheck.ini")
    assert done.returncode == 1
    block = _block(done.stdout)
    assert "\nCounts (checks): passed 6 · failed 1 ·" in block
    assert "Failed:\n  - twin pass: digital_twin/typecheck.ini\n" in block
    assert block.endswith("Result: FAIL\nExit code: 1\n")


def test_every_pass_runs_even_after_one_fails(tmp_path: Path) -> None:
    done = _run(tmp_path, mypy_fails_on="host_typecheck.ini")
    assert done.returncode == 1
    assert "Failed:\n  - host pass: host_typecheck.ini\n" in _block(done.stdout)


def test_a_failing_stub_install_aborts_naming_its_stage(tmp_path: Path) -> None:
    done = _run(tmp_path, uv_install_fails=True)
    assert done.returncode == 1
    block = _block(done.stdout)
    assert "Failed:\n  - stub install: exited 1\n" in block
    assert "\nCounts (checks): passed 1 · failed 1 ·" in block


@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help_prints_the_usage_and_runs_nothing(tmp_path: Path, flag: str) -> None:
    done = _run(tmp_path, flag, uv_install_fails=True)
    assert done.returncode == 0, done.stderr
    assert done.stdout.startswith("Usage: scripts/typecheck.sh [PATH ...]")
    assert "== Summary" not in done.stdout
