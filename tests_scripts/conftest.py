"""Shared fixtures for tests_scripts/ (SPECIFICATION.md Part B.11's build-chain verification).
See CLAUDE.md's "Code quality tooling" for why this suite runs under CPython/pytest rather than
the real MicroPython Unix-port interpreter tests/ uses (SPECIFICATION.md Part E.1)."""

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType

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


def load_script_module(module_path: Path, name: str) -> ModuleType:
    """Imports a standalone `uv run`-style script (scripts/*.py, toolchain/*.py - not package
    members) as a real module, so its functions can be exercised directly rather than only through
    subprocess/CLI behavior. Fails loud: importlib returns None for both the spec and its loader
    rather than raising, and an unguarded attribute error on those reads as an unrelated bug."""
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"couldn't build an import spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
