"""scripts/lint.sh's three grep guards enforce rules mypy and ruff cannot express, and their own
failure mode is silent: a drifted pattern stops matching and the gate goes green on a real
violation. Each block is extracted from the live script and run against a fabricated tree."""

import re
import subprocess
from pathlib import Path

import pytest

_METHOD_ASSIGN = "method-assign"
_SRC_COLLECT = "gc.collect() in src/"
_BUILDGEN_COLLECT = "gc.collect() in buildgen/"


def _guard_block(repo_root: Path, needle: str) -> str:
    """The one `if grep ...; then ... fi` block of scripts/lint.sh whose message contains `needle`."""
    text = (repo_root / "scripts" / "lint.sh").read_text()
    blocks = [b for b in re.findall(r"^if grep .*?^fi$", text, re.MULTILINE | re.DOTALL) if needle in b]
    assert len(blocks) == 1, f"expected exactly one lint.sh guard mentioning {needle!r}, found {len(blocks)}"
    return str(blocks[0])


def _run_guard(repo_root: Path, tree: Path, needle: str, script_home: Path | None = None) -> subprocess.CompletedProcess[str]:
    # The probe script never lands in the tree it searches: the live-tree case below would otherwise
    # leave a guard.sh behind in the repo, the very leak scripts/test.sh has a sweep for.
    slug = re.sub(r"[^a-z]+", "_", needle.lower()).strip("_")
    script = (script_home or tree) / f"guard_{slug}.sh"
    # set -euo pipefail as the real script has it: without -o pipefail the piped gc.collect guards
    # would report the wrong command's status, which is exactly the kind of drift this checks.
    script.write_text(f'#!/usr/bin/env bash\nset -euo pipefail\nstatus=0\n{_guard_block(repo_root, needle)}\nexit "$status"\n')
    return subprocess.run(["/bin/bash", str(script)], cwd=tree, capture_output=True, text=True, check=False)


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """A minimal stand-in repo: both scopes present and both clean, so every case below adds
    exactly one file and the guard's verdict is attributable to it."""
    (tmp_path / "src").mkdir()
    (tmp_path / "buildgen").mkdir()
    (tmp_path / "src" / "system_service.py").write_text("import gc\n\n\nasync def start_and_check_tasks() -> None:\n    gc.collect()\n")
    (tmp_path / "src" / "asy_fram_driver.py").write_text("x = 1\n")
    (tmp_path / "buildgen" / "codegen.py").write_text('lines.append("    gc.collect()")\n')
    (tmp_path / "buildgen" / "driver_registry.py").write_text("y = 2\n")
    return tmp_path


@pytest.mark.parametrize("needle", [_METHOD_ASSIGN, _SRC_COLLECT, _BUILDGEN_COLLECT])
def test_each_guard_passes_a_tree_that_only_holds_its_allowed_sites(repo_root: Path, tree: Path, needle: str) -> None:
    result = _run_guard(repo_root, tree, needle)
    assert result.returncode == 0, f"the {needle!r} guard failed a clean tree: {result.stdout}{result.stderr}"


@pytest.mark.parametrize(
    "suppression",
    [
        "obj.meth = other  # type: ignore[method-assign]",
        "obj.meth = other  # type: ignore[assignment,method-assign]",
        "obj.meth = other  # type: ignore[method-assign,assignment]",
    ],
)
def test_a_method_assign_suppression_anywhere_in_src_fails_the_gate(repo_root: Path, tree: Path, suppression: str) -> None:
    # The combined forms are the ones a pattern without `[^]]*` would miss, and they are what a real
    # site looks like: a method reassignment usually trips `assignment` in the same breath.
    (tree / "src" / "asy_fram_driver.py").write_text(f"{suppression}\n")
    result = _run_guard(repo_root, tree, _METHOD_ASSIGN)
    assert result.returncode == 1, f"a {suppression!r} in src/ must fail the lint gate"
    assert "must never suppress method-assign" in result.stderr


def test_the_same_suppression_outside_src_is_left_alone(repo_root: Path, tree: Path) -> None:
    # tests/ and digital_twin/ carry ~157 of these deliberately - that IS the mocking mechanism.
    (tree / "tests").mkdir()
    (tree / "tests" / "machine.py").write_text("obj.meth = other  # type: ignore[method-assign]\n")
    assert _run_guard(repo_root, tree, _METHOD_ASSIGN).returncode == 0


@pytest.mark.parametrize(("scope", "filename", "needle"), [("src", "asy_fram_manager.py", _SRC_COLLECT), ("buildgen", "driver_registry.py", _BUILDGEN_COLLECT)])
def test_a_gc_collect_outside_its_one_allowed_file_fails_the_gate(repo_root: Path, tree: Path, scope: str, filename: str, needle: str) -> None:
    (tree / scope / filename).write_text("import gc\ngc.collect()\n")
    result = _run_guard(repo_root, tree, needle)
    assert result.returncode == 1, f"gc.collect() in {scope}/{filename} must fail the lint gate (SPECIFICATION.md Part I.4(f.1))"
    assert "I.4(f.1)" in result.stderr


@pytest.mark.parametrize(("scope", "filename", "needle"), [("src", "not_system_service.py", _SRC_COLLECT), ("src", "system_service_helper.py", _SRC_COLLECT), ("buildgen", "codegen_helpers.py", _BUILDGEN_COLLECT)])
def test_a_filename_that_merely_contains_the_allowed_one_is_not_excused(repo_root: Path, tree: Path, scope: str, filename: str, needle: str) -> None:
    # The bite: the exclusion is `grep -v "^src/system_service.py:"`, anchored and with the colon.
    # Unanchored, every one of these names would inherit the exception silently.
    (tree / scope / filename).write_text("import gc\ngc.collect()\n")
    assert _run_guard(repo_root, tree, needle).returncode == 1, f"{scope}/{filename} must not inherit {needle}'s single-file exception"


@pytest.mark.parametrize(("scope", "filename", "needle"), [("src", "system_service.py", _SRC_COLLECT), ("buildgen", "codegen.py", _BUILDGEN_COLLECT)])
def test_the_allowed_file_may_hold_several_collects(repo_root: Path, tree: Path, scope: str, filename: str, needle: str) -> None:
    # Both allowed sites genuinely hold two: one before the list and one per unit inside it.
    (tree / scope / filename).write_text("import gc\ngc.collect()\nfor _ in range(2):\n    gc.collect()\n")
    assert _run_guard(repo_root, tree, needle).returncode == 0


def test_a_subdirectory_of_an_allowed_scope_is_searched_too(repo_root: Path, tree: Path) -> None:
    # -r, not a flat glob: src/ is flat today, but a guard that stopped at the top level would go
    # green the day it is not.
    (tree / "src" / "sub").mkdir()
    (tree / "src" / "sub" / "leaf.py").write_text("import gc\ngc.collect()\n")
    assert _run_guard(repo_root, tree, _SRC_COLLECT).returncode == 1


def test_the_live_tree_satisfies_all_three_guards(repo_root: Path, tmp_path: Path) -> None:
    # Run against the real repo, so the pytest tier states the invariant independently of whether
    # anyone ran scripts/lint.sh - the same reason test_gc_collect_sites.py exists beside it.
    for needle in (_METHOD_ASSIGN, _SRC_COLLECT, _BUILDGEN_COLLECT):
        result = _run_guard(repo_root, repo_root, needle, script_home=tmp_path)
        assert result.returncode == 0, f"the live tree violates lint.sh's {needle!r} guard: {result.stdout}{result.stderr}"
