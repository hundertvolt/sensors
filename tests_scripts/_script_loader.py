"""Shared helper for importing a standalone `uv run`-style script (scripts/*.py, toolchain/*.py -
not package members) as a real module - split out of conftest.py so this bare import doesn't
collide with tests_hardware/'s own bare "conftest" (both directories need mypy_path bare-name
resolution for their own sibling imports; mypy resolves one bare name to exactly one file per run,
same constraint digital_twin/typecheck.ini's own split exists for)."""

import importlib.util
from pathlib import Path
from types import ModuleType


def load_script_module(module_path: Path, name: str) -> ModuleType:
    """Imports a standalone `uv run`-style script so its functions can be exercised directly
    rather than only through subprocess/CLI behavior. Fails loud: importlib returns None for both
    the spec and its loader rather than raising, and an unguarded attribute error on those reads as
    an unrelated bug."""
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"couldn't build an import spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
