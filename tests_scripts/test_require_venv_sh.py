"""scripts/_require_venv.sh's require_project_venv, the check scripts/lint.sh and scripts/typecheck.sh run first: no
venv, another venv, a venv uv.lock no longer matches and a tool resolving outside the venv each refuse with the fix,
before any check runs; the project venv with its tools passes. Run in a copy of the helper beside a fake .venv."""

import os
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_TOOLS = ("ruff", "mypy")


def _stub(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(0o755)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    # The helper in a stand-in repo whose .venv holds the tools, and a uv whose `sync --check` passes unless told not to.
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "_require_venv.sh").write_bytes((_REPO / "scripts" / "_require_venv.sh").read_bytes())
    for tool in _TOOLS:
        _stub(root / ".venv" / "bin" / tool, "exit 0")
    _stub(tmp_path / "uv_bin" / "uv", 'echo "uv $*" >> "$UV_CALLS"; [ -z "$UV_FAILS" ] || { echo "Would update foo" >&2; exit 1; }')
    return root


def _check(repo: Path, *, venv: "str | None", path_first: "Path | None" = None, uv_fails: bool = False) -> subprocess.CompletedProcess[str]:
    path = [str(p) for p in (path_first, repo / ".venv" / "bin", repo.parent / "uv_bin") if p is not None]
    env = {"PATH": ":".join([*path, "/usr/bin", "/bin"]), "UV_CALLS": str(repo.parent / "uv.calls"), "UV_FAILS": "1" if uv_fails else ""}
    if venv is not None:
        env["VIRTUAL_ENV"] = venv
    script = f'source scripts/_require_venv.sh && require_project_venv {" ".join(_TOOLS)} && echo "venv ok"'
    return subprocess.run(["/bin/bash", "-c", script], cwd=repo, env=env, capture_output=True, text=True, check=False, timeout=30)


def test_the_project_venv_with_its_tools_passes_and_checks_the_lock_offline(repo: Path) -> None:
    done = _check(repo, venv=str(repo / ".venv"))
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "venv ok"
    assert (repo.parent / "uv.calls").read_text(encoding="utf-8").split() == ["uv", "sync", "--locked", "--check", "--offline"]


@pytest.mark.parametrize("venv", [None, "elsewhere"], ids=["no-venv", "another-venv"])
def test_no_venv_or_another_venv_is_refused_naming_the_activation(repo: Path, tmp_path: Path, venv: "str | None") -> None:
    other = None if venv is None else str(tmp_path / venv)
    if other is not None:
        os.makedirs(other)
    done = _check(repo, venv=other)
    assert done.returncode == 1
    assert "error: activate the project venv first (uv sync && source .venv/bin/activate), or run through uv run" in done.stderr
    assert not (repo.parent / "uv.calls").exists(), "the lock was checked before the venv was"


def test_a_venv_the_lock_no_longer_matches_is_refused_naming_uv_sync(repo: Path) -> None:
    done = _check(repo, venv=str(repo / ".venv"), uv_fails=True)
    assert done.returncode == 1
    assert "error: the venv does not match uv.lock - run uv sync" in done.stderr
    assert "Would update foo" in done.stderr, "uv's own account of the mismatch is shown"


def test_a_tool_found_before_the_venv_on_path_is_refused_naming_it(repo: Path, tmp_path: Path) -> None:
    # A system ruff of another version earlier on PATH would otherwise run in place of the pinned one.
    _stub(tmp_path / "system_bin" / "ruff", "exit 0")
    done = _check(repo, venv=str(repo / ".venv"), path_first=tmp_path / "system_bin")
    assert done.returncode == 1
    assert f"error: ruff resolves to {tmp_path / 'system_bin' / 'ruff'}, not the project venv's {repo / '.venv' / 'bin' / 'ruff'}" in done.stderr


def test_run_as_a_command_it_refuses(repo: Path) -> None:
    done = subprocess.run(["/bin/bash", "scripts/_require_venv.sh"], cwd=repo, capture_output=True, text=True, check=False, timeout=30)
    assert done.returncode == 2
    assert "source scripts/_require_venv.sh" in done.stderr
