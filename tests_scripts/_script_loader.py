"""Shared helper for importing a standalone `uv run`-style script (scripts/*.py, toolchain/*.py)
as a real module. Split out of conftest.py so this bare import cannot collide with
tests_hardware/'s own bare "conftest" - mypy resolves one bare name to one file per run."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_script_module(module_path: Path, name: str) -> ModuleType:
    """Imports a standalone `uv run`-style script so its functions can be exercised directly, not
    only through subprocess/CLI behavior. Fails loud, because importlib returns None for the spec
    and its loader rather than raising, and an attribute error on those reads as another bug."""
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"couldn't build an import spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    # Registered in sys.modules BEFORE exec_module(): a @dataclass under `from __future__ import
    # annotations` resolves its string annotations through sys.modules[cls.__module__] while the
    # class body still runs, and raises AttributeError otherwise.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
