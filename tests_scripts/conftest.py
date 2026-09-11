"""Shared fixtures for tests_scripts/ (SPECIFICATION.md Part B.11's build-chain verification).
See CLAUDE.md's "Code quality tooling" for why this suite runs under CPython/pytest rather than
the real MicroPython Unix-port interpreter tests/ uses (SPECIFICATION.md Part E.1)."""

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# buildgen/ (Session 3 of BUILD_CHAIN_PLAN.md) is a real top-level package, unlike scripts/
# (loaded per-file via importlib.util elsewhere in this suite) - pytest's own rootless import mode
# only ever puts tests_scripts/ itself on sys.path, never the repo root, so its tests need this to
# resolve `import buildgen`.
sys.path.insert(0, str(REPO_ROOT))


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


@pytest.fixture(scope="session")
def micropython_bin(micropython_dir: Path) -> Path:
    # Same path scripts/run_digital_twin_ci.sh's own $micropython_bin resolves to. Tests that need
    # to actually spawn the real Unix-port interpreter (e.g. test_digital_twin_generated_boot.py)
    # skip themselves when it isn't built yet, rather than failing the whole suite - building it is
    # scripts/test.sh's/CI's own job (toolchain/setup_toolchain.py setup), not this fixture's.
    path = micropython_dir / "ports" / "unix" / "build-standard" / "micropython"
    if not path.is_file():
        pytest.skip(f"MicroPython Unix port not built at {path} - run toolchain/setup_toolchain.py setup first")
    return path
