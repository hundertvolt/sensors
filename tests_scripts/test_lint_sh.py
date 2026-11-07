"""scripts/lint.sh: its method-assign guard (a rule mypy and ruff cannot express) extracted as the grep_guard call that
names it and run on fabricated trees - failing closed when grep cannot look - and the whole script in a sandbox with
its tools stubbed: help, arguments, the venv check, and a summary block naming every check."""

import re
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_CHECKS = ("generation", "ruff", "shellcheck", "actionlint", "zizmor", "method-assign guard", "gc sites")
_TOOLS = ("ruff", "shellcheck", "actionlint", "zizmor")
# What scripts/_check_gc_collect_sites.py reads besides src/, buildgen/ and ext/: its scopes, the devices it generates, and
# the generator's stamped tree with the stamp's own inputs.
_GC_CHECK_READS = ("devices", "tests", "digital_twin", "tests_hardware", "build", "toolchain")


def _guard(repo_root: Path) -> str:
    # lint.sh's grep_guard function and its one call naming method-assign, as one runnable block.
    text = (repo_root / "scripts" / "lint.sh").read_text(encoding="utf-8")
    function = re.search(r"^grep_guard\(\) \{\n.*?^\}$", text, re.MULTILINE | re.DOTALL)
    calls = [line for line in text.splitlines() if line.startswith("grep_guard method-assign ")]
    assert function is not None and len(calls) == 1, "expected lint.sh's grep_guard function and one method-assign call"
    return f"{function.group(0)}\n{calls[0]}"


def _run_guard(repo_root: Path, tree: Path, script_home: Path) -> subprocess.CompletedProcess[str]:
    # The probe never lands in the tree it searches: the live-tree case would otherwise leave it in the repo.
    script = script_home / "guard.sh"
    script.write_text(f'#!/usr/bin/env bash\nset -euo pipefail\nstatus=0\n{_guard(repo_root)}\nexit "$status"\n', encoding="utf-8")
    return subprocess.run(["/bin/bash", str(script)], cwd=tree, capture_output=True, text=True, check=False, timeout=30)


def _run_lint(repo_root: Path, tmp_path: Path, *args: str, failing_tool: "str | None" = None, env_change: "dict[str, str] | None" = None, gc_check: bool = False) -> subprocess.CompletedProcess[str]:
    root, env = _sandbox(repo_root, tmp_path, failing_tool, gc_check=gc_check)
    env.update(env_change or {})
    return subprocess.run(["/bin/bash", str(root / "scripts" / "lint.sh"), *args], cwd=root, env=env, capture_output=True, text=True, check=False, timeout=120)


def _sandbox(repo_root: Path, tmp_path: Path, failing_tool: "str | None", *, gc_check: bool) -> "tuple[Path, dict[str, str]]":
    # scripts/ copied and the trees the checks read linked - every one the gc checker reads with gc_check, else the
    # checker a passing stub like the tools - a .venv of stub tools (one may fail) and the real interpreter; uv records.
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    for path in (repo_root / "scripts").iterdir():
        if path.is_file():
            (root / "scripts" / path.name).write_bytes(path.read_bytes())
    for name in ("src", "buildgen", "ext", *(_GC_CHECK_READS if gc_check else ())):
        (root / name).symlink_to(repo_root / name)
    if not gc_check:
        (root / "scripts" / "_check_gc_collect_sites.py").write_text('import os\nwith open(os.environ["TOOL_CALLS"], "a") as f:\n    f.write("gc sites\\n")\n', encoding="utf-8")
    venv_bin = root / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    for tool in _TOOLS:
        (venv_bin / tool).write_text(f'#!/bin/sh\necho "{tool} $*" >> "$TOOL_CALLS"\nexit {1 if tool == failing_tool else 0}\n', encoding="utf-8")
        (venv_bin / tool).chmod(0o755)
    (venv_bin / "python3").symlink_to(sys.executable)
    uv_bin = tmp_path / "uv_bin"
    uv_bin.mkdir()
    (uv_bin / "uv").write_text('#!/bin/sh\necho "uv $*" >> "$TOOL_CALLS"\nexit 0\n', encoding="utf-8")
    (uv_bin / "uv").chmod(0o755)
    env = {"PATH": f"{venv_bin}:{uv_bin}:/usr/bin:/bin", "VIRTUAL_ENV": str(root / ".venv"), "TOOL_CALLS": str(tmp_path / "calls"), "HOME": str(tmp_path)}
    return root, env


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    root = tmp_path / "tree"
    (root / "src").mkdir(parents=True)
    (root / "src" / "asy_fram_driver.py").write_text("x = 1\n", encoding="utf-8")
    return root


def test_the_guard_passes_a_clean_tree(repo_root: Path, tree: Path, tmp_path: Path) -> None:
    assert _run_guard(repo_root, tree, tmp_path).returncode == 0


@pytest.mark.parametrize(
    "suppression",
    [
        "obj.meth = other  # type: ignore[method-assign]",
        "obj.meth = other  # type: ignore[assignment,method-assign]",
        "obj.meth = other  # type: ignore[method-assign,assignment]",
    ],
)
def test_a_method_assign_suppression_anywhere_in_src_fails_the_gate(repo_root: Path, tree: Path, tmp_path: Path, suppression: str) -> None:
    # The combined forms are the ones a pattern without `[^]]*` would miss, and they are what a real
    # site looks like: a method reassignment usually trips `assignment` in the same breath.
    (tree / "src" / "sub").mkdir()
    (tree / "src" / "sub" / "leaf.py").write_text(f"{suppression}\n", encoding="utf-8")
    result = _run_guard(repo_root, tree, tmp_path)
    assert result.returncode == 1, f"a {suppression!r} in src/ must fail the lint gate"
    assert "must never suppress method-assign" in result.stderr
    assert "src/sub/leaf.py:1:" in result.stdout, "the guard prints the site it found"


def test_the_same_suppression_outside_src_is_left_alone(repo_root: Path, tree: Path, tmp_path: Path) -> None:
    # tests/ and digital_twin/ mock by reassigning methods, so they carry these: that IS the mocking mechanism.
    (tree / "tests").mkdir()
    (tree / "tests" / "machine.py").write_text("obj.meth = other  # type: ignore[method-assign]\n", encoding="utf-8")
    assert _run_guard(repo_root, tree, tmp_path).returncode == 0


def test_a_guard_that_cannot_look_fails_closed(repo_root: Path, tree: Path, tmp_path: Path) -> None:
    # grep exit 2 (here: no src/ to search) is an error, never "no match", so a guard that could not look fails.
    (tree / "src" / "asy_fram_driver.py").unlink()
    (tree / "src").rmdir()
    result = _run_guard(repo_root, tree, tmp_path)
    assert result.returncode == 1
    assert "error: lint.sh could not search (-rn type: ignore\\[[^]]*method-assign src/, grep exit 2) - the method-assign guard did not look" in result.stderr


def test_the_live_tree_satisfies_the_guard(repo_root: Path, tmp_path: Path) -> None:
    result = _run_guard(repo_root, repo_root, tmp_path)
    assert result.returncode == 0, f"the live tree violates lint.sh's method-assign guard: {result.stdout}{result.stderr}"


def test_help_prints_the_usage_and_exits_0(repo_root: Path, tmp_path: Path) -> None:
    for flag in ("-h", "--help"):
        result = _run_lint(repo_root, tmp_path / flag, flag, failing_tool="ruff")
        assert result.returncode == 0, result.stderr
        assert result.stdout.startswith("Usage: scripts/lint.sh - no arguments"), result.stdout
        assert "== Summary" not in result.stdout, "--help runs no check"


def test_any_other_argument_is_a_usage_error_naming_it(repo_root: Path, tmp_path: Path) -> None:
    result = _run_lint(repo_root, tmp_path, "src/")
    assert result.returncode == 2
    assert "error: unknown argument src/" in result.stderr and "Usage: scripts/lint.sh" in result.stderr
    assert result.stdout == ""
    assert not (tmp_path / "calls").exists(), "a refused run ran a tool"


def test_outside_the_project_venv_nothing_runs(repo_root: Path, tmp_path: Path) -> None:
    result = _run_lint(repo_root, tmp_path, env_change={"VIRTUAL_ENV": str(tmp_path / "elsewhere")})
    assert result.returncode == 1
    assert "error: activate the project venv first" in result.stderr
    assert not (tmp_path / "calls").exists(), "a check ran outside the venv"


def test_a_clean_run_generates_first_then_ends_with_the_block_counting_every_check(repo_root: Path, tmp_path: Path) -> None:
    result = _run_lint(repo_root, tmp_path, gc_check=True)
    assert result.returncode == 0, result.stdout + result.stderr
    calls = (tmp_path / "calls").read_text(encoding="utf-8").splitlines()
    assert calls[:2] == ["uv sync --locked --check --offline", "uv run --no-sync scripts/_generate_sensortask_modules.py"], calls
    assert calls[2].startswith("ruff check ") and calls[2].endswith(" build/generated_src"), calls
    block = result.stdout[result.stdout.index("== Summary: scripts/lint.sh ==") :]
    assert f"\nCounts (checks): passed {len(_CHECKS)} · failed 0 ·" in block
    assert block.endswith("Result: PASS\nExit code: 0\n")


@pytest.mark.parametrize("tool", _TOOLS)
def test_a_failing_check_is_named_in_the_block_and_fails_the_run(repo_root: Path, tmp_path: Path, tool: str) -> None:
    result = _run_lint(repo_root, tmp_path, failing_tool=tool)
    assert result.returncode == 1
    block = result.stdout[result.stdout.index("== Summary: scripts/lint.sh ==") :]
    assert f"\nCounts (checks): passed {len(_CHECKS) - 1} · failed 1 ·" in block
    assert f"Failed:\n  - {tool}\n" in block
    assert block.endswith("Result: FAIL\nExit code: 1\n")

