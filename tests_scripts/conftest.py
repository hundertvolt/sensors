"""Shared fixtures for tests_scripts/ (SPECIFICATION.md Part B.11's build-chain verification).
See CLAUDE.md's "Code quality tooling" for why this suite runs under CPython/pytest rather than
the real MicroPython Unix-port interpreter tests/ uses (SPECIFICATION.md Part E.1)."""

import os
import sys
from pathlib import Path
from types import ModuleType

import pytest
from _script_loader import load_script_module

REPO_ROOT = Path(__file__).resolve().parent.parent

# buildgen/ (SPECIFICATION.md Part L.4) is a real top-level package, unlike scripts/
# (loaded per-file via importlib.util elsewhere in this suite) - pytest's own rootless import mode
# only ever puts tests_scripts/ itself on sys.path, never the repo root, so its tests need this to
# resolve `import buildgen`.
sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture(scope="session", autouse=True)
def _reclaim_leaked_device_fixtures() -> None:
    """Reclaims any `devices/zz_test_*.toml` a KILLED earlier run left behind, once, before any test
    runs - race-free by construction, since nothing has created one yet at session start (a test
    globbing the live tree could only tell leak from legitimate fixture by racing it)."""
    for stale in sorted((REPO_ROOT / "devices").glob("zz_test_*.toml")):
        stale.unlink()
        print(f"reclaimed leaked live-tree device fixture: {stale.name}")


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def ci_suite(repo_root: Path) -> ModuleType:
    """scripts/_digital_twin_ci_suite.py as a real module - a standalone `uv run`-style script, not a
    package member, so its pure helpers are only reachable through the loader. Session-scoped and
    shared, so the three test files exercising it execute the module once between them, not once each."""
    return load_script_module(repo_root / "scripts" / "_digital_twin_ci_suite.py", "_digital_twin_ci_suite")


@pytest.fixture(scope="session")
def micropython_dir() -> Path:
    # Mirrors scripts/build_firmware.py's own main()'s --toolchain-dir default resolution exactly
    # (PICO_TOOLCHAIN_DIR env var, else ~/pico-toolchain) - scripts/test.sh/CI always provisions a
    # real checkout here before this suite runs (see build_stage_dir()'s own rp2.py copy).
    toolchain_dir = Path(os.environ.get("PICO_TOOLCHAIN_DIR", Path.home() / "pico-toolchain"))
    return toolchain_dir / "micropython"


@pytest.fixture(scope="session")
def micropython_bin(micropython_dir: Path) -> Path:
    # Same path scripts/run_digital_twin_ci.sh's own $micropython_bin resolves to. A test that needs
    # to actually spawn it (e.g. test_digital_twin_generated_boot.py) skips itself when it isn't
    # built yet, rather than failing the whole suite - building it is scripts/test.sh's/CI's job.
    path = micropython_dir / "ports" / "unix" / "build-standard" / "micropython"
    if not path.is_file():
        pytest.skip(f"MicroPython Unix port not built at {path} - run toolchain/setup_toolchain.py setup first")
    return path
