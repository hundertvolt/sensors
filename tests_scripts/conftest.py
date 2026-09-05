"""Shared fixtures for tests_scripts/ (SPECIFICATION.md Part B.11's build-chain verification).
See CLAUDE.md's "Code quality tooling" for why this suite runs under CPython/pytest rather than
the real MicroPython Unix-port interpreter tests/ uses (SPECIFICATION.md Part E.1)."""

import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def micropython_dir() -> Path:
    # Mirrors scripts/build_firmware.py's own main()'s --toolchain-dir default resolution exactly
    # (PICO_TOOLCHAIN_DIR env var, else ~/pico-toolchain) - scripts/test.sh/CI always provisions a
    # real checkout here before this suite runs (see build_stage_dir()'s own rp2.py copy).
    toolchain_dir = Path(os.environ.get("PICO_TOOLCHAIN_DIR", Path.home() / "pico-toolchain"))
    return toolchain_dir / "micropython"
