"""Pins that every staged config write in tests_hardware/device_scripts/ is flushed on the manager
that actually holds it. write_config() only stages - an unflushed manager lets asyncio.run() discard
the flash write, and the file keeps setup()'s defaults (MEASUREMENTS archive 7O)."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

DEVICE_SCRIPTS = REPO_ROOT / "tests_hardware" / "device_scripts"

# A write reaches flash through the manager named here, which is what flush_pending() must be called
# on. write_config() IS the manager's own method, so it stages on the receiver; _set_dict_cfg() is
# SensorReaderConfig's, and stages on that object's `.cfgmgr` - pinned by the last test below.
_DELEGATES_TO_CFGMGR = "_set_dict_cfg"
_WRITES_DIRECTLY = "write_config"
_FLUSH = "flush_pending"

# A script whose staged write does NOT have to reach flash, with the reason it does not. Each entry
# is re-derived by the tests below rather than trusted, so a script that stops qualifying fails here.
_JUSTIFIED_UNFLUSHED = {
    "isl29125_mechanism_envelope.py": "awaits between pushes, so its flushes are scheduled, and nothing it writes has to survive a reset",
}


class _Sites(NamedTuple):
    write_targets: dict[str, int]  # manager holding a staged write -> line of the first write to it
    flush_targets: set[str]  # manager flush_pending() was called on
    unresolvable: list[tuple[str, int]]  # a write whose receiver this guard cannot name


def _dotted(node: ast.expr) -> str | None:
    # The receiver's source spelling ("mgr", "conn.cfgmgr"), or None for a shape with no stable name
    # (a call result, a subscript). None is reported as unresolvable, never skipped.
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return None if base is None else f"{base}.{node.attr}"
    return None


def _sites(tree: ast.Module) -> _Sites:
    writes: dict[str, int] = {}
    flushes: set[str] = set()
    unresolvable: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        attr, receiver = node.func.attr, _dotted(node.func.value)
        if attr == _FLUSH:
            if receiver is not None:
                flushes.add(receiver)
        elif attr in (_WRITES_DIRECTLY, _DELEGATES_TO_CFGMGR):
            if receiver is None:
                unresolvable.append((attr, node.lineno))
                continue
            target = receiver if attr == _WRITES_DIRECTLY else f"{receiver}.cfgmgr"
            writes.setdefault(target, node.lineno)
    return _Sites(writes, flushes, unresolvable)


def _writing_scripts() -> list[tuple[Path, ast.Module, _Sites]]:
    # Matching is file-scoped by source spelling, because a write can sit in a helper that takes the
    # object as a parameter while the flush sits in _main (wifi_service_reconnect_repro.py does
    # exactly that). So no call ORDER is asserted: across two functions there is no order to read.
    found = []
    for path in sorted(DEVICE_SCRIPTS.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        sites = _sites(tree)
        if sites.write_targets or sites.unresolvable:
            found.append((path, tree, sites))
    return found


def _has_await_between_writes(tree: ast.Module) -> bool:
    # The justification the allowlist claims: an `await asyncio.sleep*()` somewhere in the file is
    # what lets a staged flush actually get scheduled before the script ends.
    return any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr.startswith("sleep")
        for node in ast.walk(tree)
    )


def test_every_staged_write_is_flushed_on_the_manager_that_holds_it() -> None:
    offenders = []
    for path, _tree, sites in _writing_scripts():
        if path.name in _JUSTIFIED_UNFLUSHED:
            continue
        for target, line in sorted(sites.write_targets.items()):
            if target not in sites.flush_targets:
                offenders.append(f"{path.name}:{line} stages on `{target}`, never flushed")
    assert not offenders, (
        "these managers hold a staged config write that no flush_pending() call reaches, so "
        "asyncio.run() discards the flash write and the file keeps its defaults (MEASUREMENTS archive 7O). "
        f"A second manager in the same file being flushed does NOT cover these: {offenders}"
    )


def test_no_write_site_has_a_receiver_this_guard_cannot_name() -> None:
    # Without this, a write through a shape _dotted() cannot render would contribute no target and
    # the file would pass by silence. A new shape must fail here and be taught to the guard.
    unresolvable = [f"{path.name}:{line} ({attr})" for path, _tree, sites in _writing_scripts() for attr, line in sites.unresolvable]
    assert not unresolvable, f"these config writes have a receiver this guard cannot resolve to a manager name, so it cannot check them: {unresolvable}"


def test_the_allowlist_only_names_scripts_that_actually_write_config() -> None:
    writing = {path.name for path, _tree, _sites in _writing_scripts()}
    stale = sorted(set(_JUSTIFIED_UNFLUSHED) - writing)
    assert not stale, f"_JUSTIFIED_UNFLUSHED names {stale}, which no longer write config at all - drop the entry rather than carrying it"


def test_each_allowlisted_script_still_meets_the_reason_it_was_allowlisted() -> None:
    # Re-derives the claim instead of trusting the comment: an allowlisted script that loses its
    # awaits has lost the thing that made skipping the flush safe, and must fail here.
    for path, tree, _sites in _writing_scripts():
        if path.name not in _JUSTIFIED_UNFLUSHED:
            continue
        assert _has_await_between_writes(tree), (
            f"{path.name} is allowlisted because it {_JUSTIFIED_UNFLUSHED[path.name]}, but it no "
            "longer awaits anything that would let a staged flush run - it needs flush_pending() now"
        )


def test_the_cfgmgr_delegation_this_guard_assumes_is_still_what_src_does() -> None:
    # The `.cfgmgr` hop above is only correct while _set_mgr_cfg persists through that attribute. If
    # it is ever renamed, every _set_dict_cfg() target this guard derives is wrong, so pin it here.
    tree = ast.parse((REPO_ROOT / "src" / "base_classes.py").read_text(encoding="utf-8"))
    bodies = [node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef) and node.name == "_set_mgr_cfg"]
    assert len(bodies) == 1, f"expected exactly one _set_mgr_cfg in src/base_classes.py, found {len(bodies)}"
    targets = {_dotted(node.func.value) for node in ast.walk(bodies[0]) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == _WRITES_DIRECTLY}
    assert targets == {"self.cfgmgr"}, f"_set_mgr_cfg persists through {targets or 'no write_config() call at all'}, not self.cfgmgr - this guard's _set_dict_cfg target is now wrong"
