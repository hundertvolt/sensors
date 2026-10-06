"""Every runner and user-facing tool answers --help: exit 0, a usage block on stdout, and nothing in
the tree created, changed or removed - so asking a tool how to run it can never start it."""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Every runner and user-facing tool, by its path from the repo root; how each one is started follows
# from its suffix (and digital_twin/ runs under the Unix port).
TOOLS: tuple[str, ...] = (
    "scripts/test.sh",
    "scripts/lint.sh",
    "scripts/typecheck.sh",
    "scripts/run_digital_twin_ci.sh",
    "scripts/run_unix_port_integration.sh",
    "scripts/run_flash_hardware_suite.sh",
    "scripts/run_bench_hardware_suite.sh",
    "scripts/run_bench_soak_tests.sh",
    "scripts/run_manual_hardware_tests.sh",
    "scripts/mpremote_connect.sh",
    "scripts/setup_cross_browser_toolchain.sh",
    "scripts/cross_browser_smoke.mjs",
    "scripts/build_firmware.py",
    "scripts/build_website.sh",
    "scripts/build_device_websites.sh",
    "scripts/build_frozen_html.sh",
    "toolchain/setup_toolchain.py",
    "digital_twin/launch.py",
)

# The only commands on the PATH a tool sees here: one that stopped answering --help first fails on
# a missing uv, mpremote or nmcli instead of reaching a board or the bench network (real hardware
# needs the owner's go-ahead, CLAUDE.md). python3 is this suite's own interpreter.
_SAFE_COMMANDS = ("bash", "sh", "env", "dirname", "basename", "cat", "sed", "grep", "awk", "head", "tail", "tr", "cut", "sort", "wc", "printf", "realpath", "readlink", "uname", "id", "date", "ls", "git", "node")

# Written by the suites that may run beside this one (scripts/test.sh's concurrent MicroPython tier,
# its twins' config) and by any interpreter's bytecode cache: never a tool's --help side effect.
_CONCURRENT_SCRATCH = {Path(".git"), Path("node_modules"), Path(".venv"), Path("tests/_tmp"), Path("digital_twin/config")}
_CACHE_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}

_TIMEOUT_S = 60
_USAGE_LINE = re.compile(r"^usage:", re.IGNORECASE | re.MULTILINE)


@pytest.fixture(scope="module")
def safe_path(tmp_path_factory: pytest.TempPathFactory) -> str:
    bin_dir = tmp_path_factory.mktemp("safe_bin")
    targets = {name: shutil.which(name) for name in _SAFE_COMMANDS}
    targets["python3"] = sys.executable
    for name, target in targets.items():
        if target is not None:
            # A wrapper, not a symlink: a venv's python finds its packages only through its own path.
            wrapper = bin_dir / name
            wrapper.write_text(f'#!/bin/sh\nexec "{target}" "$@"\n')
            wrapper.chmod(0o755)
    return str(bin_dir)


def _tree_listing() -> set[str]:
    listing: set[str] = set()
    for root, dirs, files in os.walk(REPO_ROOT):
        here = Path(root).relative_to(REPO_ROOT)
        dirs[:] = [d for d in dirs if d not in _CACHE_DIRS and here / d not in _CONCURRENT_SCRATCH]
        listing.update(str(here / name) for name in dirs + files)
    return listing


def _tree_state() -> dict[str, tuple[int, int]]:
    state: dict[str, tuple[int, int]] = {}
    for name in _tree_listing():
        try:
            stat = (REPO_ROOT / name).lstat()
        except FileNotFoundError:
            continue
        state[name] = (stat.st_size, stat.st_mtime_ns)
    return state


def _command(tool: str, micropython_bin: Path) -> list[str]:
    if tool.startswith("digital_twin/"):
        return [str(micropython_bin), tool, "--help"]
    interpreter = {".sh": "bash", ".mjs": "node", ".py": sys.executable}[Path(tool).suffix]
    return [interpreter, tool, "--help"]


def test_every_listed_tool_exists() -> None:
    missing = [tool for tool in TOOLS if not (REPO_ROOT / tool).is_file()]
    assert not missing, f"TOOLS names files that are gone: {missing} - update the list with the tree"


@pytest.mark.parametrize("tool", TOOLS)
def test_help_answers_with_usage_and_touches_nothing(tool: str, safe_path: str, micropython_bin: Path) -> None:
    command = _command(tool, micropython_bin)
    if command[0] == "node" and shutil.which("node") is None:
        pytest.fail("node is a hard prerequisite of the host tier, and is not on PATH")
    env = {**os.environ, "PATH": safe_path, "MICROPYPATH": "digital_twin:src:.frozen"}
    if command[0] in ("bash", "node"):
        command[0] = str(shutil.which(command[0]))
    before = _tree_state()
    done = subprocess.run(command, cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=_TIMEOUT_S, check=False)
    after = _tree_state()
    assert done.returncode == 0, f"{tool} --help exited {done.returncode}:\n{done.stdout}\n{done.stderr}"
    # argparse spells its own block "usage:"; either spelling opens the synopsis.
    assert _USAGE_LINE.search(done.stdout), f"{tool} --help printed no usage block on stdout:\n{done.stdout}\n{done.stderr}"
    created, removed = sorted(after.keys() - before.keys()), sorted(before.keys() - after.keys())
    changed = sorted(name for name in after.keys() & before.keys() if after[name] != before[name] and not (REPO_ROOT / name).is_dir())
    assert not (created or removed or changed), f"{tool} --help touched the tree: created {created}, removed {removed}, changed {changed}"
