"""Pins that every tests_hardware/device_scripts/ file which writes config also awaits
flush_pending(). write_config() only stages - a script that returns without flushing lets
asyncio.run() discard the flash write, and the file keeps setup()'s defaults (MEASUREMENTS 7O)."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

DEVICE_SCRIPTS = REPO_ROOT / "tests_hardware" / "device_scripts"

# Calls whose persist leg is a real write_config(), by name - _set_dict_cfg() reaches it through
# SensorReaderConfig rather than calling it directly.
_WRITING_CALLS = frozenset({"write_config", "_set_dict_cfg"})

# A script whose staged write does NOT have to reach flash, with the reason it does not. Each entry
# is re-derived by the test below rather than trusted, so a script that stops qualifying fails here.
_JUSTIFIED_UNFLUSHED = {
    "isl29125_mechanism_envelope.py": "awaits between pushes, so its flushes are scheduled, and nothing it writes has to survive a reset",
}


def _called_names(tree: ast.Module) -> set[str]:
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                names.add(func.attr)
            elif isinstance(func, ast.Name):
                names.add(func.id)
    return names


def _has_await_between_writes(tree: ast.Module) -> bool:
    # The justification the allowlist claims: an `await asyncio.sleep*()` somewhere in the file is
    # what lets a staged flush actually get scheduled before the script ends.
    return any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr.startswith("sleep")
        for node in ast.walk(tree)
    )


def _writing_scripts() -> list[tuple[Path, ast.Module]]:
    found = []
    for path in sorted(DEVICE_SCRIPTS.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if _WRITING_CALLS & _called_names(tree):
            found.append((path, tree))
    return found


def test_every_config_writing_device_script_flushes_or_is_justified() -> None:
    offenders = []
    for path, tree in _writing_scripts():
        if "flush_pending" in _called_names(tree) or path.name in _JUSTIFIED_UNFLUSHED:
            continue
        offenders.append(path.name)
    assert not offenders, (
        "these device scripts stage a config write and never await flush_pending(), so asyncio.run() "
        f"discards the flash write and the file keeps its defaults (MEASUREMENTS 7O): {offenders}"
    )


def test_the_allowlist_only_names_scripts_that_actually_write_config() -> None:
    writing = {path.name for path, _tree in _writing_scripts()}
    stale = sorted(set(_JUSTIFIED_UNFLUSHED) - writing)
    assert not stale, f"_JUSTIFIED_UNFLUSHED names {stale}, which no longer write config at all - drop the entry rather than carrying it"


def test_each_allowlisted_script_still_meets_the_reason_it_was_allowlisted() -> None:
    # Re-derives the claim instead of trusting the comment: an allowlisted script that loses its
    # awaits has lost the thing that made skipping the flush safe, and must fail here.
    for path, tree in _writing_scripts():
        if path.name not in _JUSTIFIED_UNFLUSHED:
            continue
        assert _has_await_between_writes(tree), (
            f"{path.name} is allowlisted because it {_JUSTIFIED_UNFLUSHED[path.name]}, but it no "
            "longer awaits anything that would let a staged flush run - it needs flush_pending() now"
        )
