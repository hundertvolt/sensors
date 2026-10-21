"""Pins that every staged config write in tests_hardware/device_scripts/ is flushed on the manager
that actually holds it. write_config() only stages - an unflushed manager lets asyncio.run() discard
the flash write, and the file keeps setup()'s defaults (MEASUREMENTS archive 7O)."""

import ast
import re
import sys
from functools import cache
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
_JUSTIFIED_UNFLUSHED: dict[str, str] = {}


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


@cache
def _writing_scripts() -> list[tuple[Path, ast.Module, _Sites]]:
    # Matching is file-scoped by source spelling, because a write can sit in a helper that takes the
    # object as a parameter while the flush sits in _main. So no call ORDER is asserted: across two
    # functions there is no order to read.
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
    writing = {path.name: sites for path, _tree, sites in _writing_scripts()}
    stale = sorted(set(_JUSTIFIED_UNFLUSHED) - set(writing))
    assert not stale, f"_JUSTIFIED_UNFLUSHED names {stale}, which no longer write config at all - drop the entry rather than carrying it"
    # An entry whose script now flushes every manager is stale too: the explicit flush is what the main check wants.
    flushed = sorted(name for name in _JUSTIFIED_UNFLUSHED if set(writing[name].write_targets) <= writing[name].flush_targets)
    assert not flushed, f"_JUSTIFIED_UNFLUSHED names {flushed}, which flush every staged write now - drop the entry"


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
    # SensorReader's default store writes nothing; SensorReaderConfig's is the one persisting override.
    tree = ast.parse((REPO_ROOT / "src" / "asy_base_classes.py").read_text(encoding="utf-8"))
    by_class = {cls.name: [n for n in cls.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "_set_mgr_cfg"] for cls in tree.body if isinstance(cls, ast.ClassDef)}
    owners = sorted(name for name, bodies in by_class.items() if bodies)
    assert owners == ["SensorReader", "SensorReaderConfig"], f"_set_mgr_cfg is defined on {owners}, not SensorReader (no store) and SensorReaderConfig (cfgmgr)"
    assert all(len(bodies) <= 1 for bodies in by_class.values()), "a class defines _set_mgr_cfg more than once"

    def _write_targets(body: ast.AsyncFunctionDef) -> set[str | None]:
        return {_dotted(node.func.value) for node in ast.walk(body) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == _WRITES_DIRECTLY}

    assert _write_targets(by_class["SensorReader"][0]) == set(), "SensorReader's default _set_mgr_cfg writes config - it has no store"
    targets = _write_targets(by_class["SensorReaderConfig"][0])
    assert targets == {"self.cfgmgr"}, f"_set_mgr_cfg persists through {targets or 'no write_config() call at all'}, not self.cfgmgr - this guard's _set_dict_cfg target is now wrong"


# A test's scratch store: config_HWTEST_* files and the directory a scratch build writes its stores into.
_SCRATCH_FILE = re.compile(r"config_HWTEST_\w*\.\w+")
_SCRATCH_DIR_NAME = "_SCRATCH_CFG_PATH"
_TESTS_HARDWARE = REPO_ROOT / "tests_hardware"


def _call_name(node: ast.AST) -> str:
    if not isinstance(node, ast.Call):
        return ""
    return node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")


def _strings(node: ast.AST, consts: "dict[str, str]") -> "set[str]":
    # Every string under `node`, a module-level name bound to one read as its value.
    found = {n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    return found | {consts[n.id] for n in ast.walk(node) if isinstance(n, ast.Name) and n.id in consts}


def _string_consts(tree: ast.Module) -> "dict[str, str]":
    return {t.id: n.value.value for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str) for t in n.targets if isinstance(t, ast.Name)}


def _removed_in_finally(tree: ast.Module) -> "dict[str, set[str]]":
    # Per remove/rmdir: the strings a `finally` passes to it, directly or through a module function it calls (by name).
    consts = _string_consts(tree)
    fns = {fn.name: fn for fn in tree.body if isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef)}
    found: dict[str, set[str]] = {"remove": set(), "rmdir": set()}

    def through(node: ast.AST, seen: "frozenset[str]") -> None:
        for call in [n for n in ast.walk(node) if isinstance(n, ast.Call)]:
            name = _call_name(call)
            if name in found:
                found[name] |= {s for arg in call.args for s in _strings(arg, consts)}
            elif name in fns and name not in seen:
                through(fns[name], seen | {name})

    for node in [n for n in ast.walk(tree) if isinstance(n, ast.Try)]:
        for stmt in node.finalbody:
            through(stmt, frozenset())
    return found


def _scratch_files(tree: ast.Module) -> "set[str]":
    return {m.group(0) for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) for m in [_SCRATCH_FILE.search(n.value)] if m}


def _builds_over_scratch(tree: ast.Module) -> bool:
    return any(_call_name(c) in {"build_system", "main"} and any(kw.arg == "cfg_path" and isinstance(kw.value, ast.Name) and kw.value.id == _SCRATCH_DIR_NAME for kw in c.keywords) for c in ast.walk(tree) if isinstance(c, ast.Call))


def _host_runs(host_modules: "list[Path]", scripts: "set[str]") -> "list[tuple[set[str], set[str]]]":
    # Per host function: (the scripts it names, the strings its own `finally` blocks carry - its cleanup).
    found: list[tuple[set[str], set[str]]] = []
    for path in host_modules:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        consts = _string_consts(tree)
        named_by = {t.id: {s for s in scripts if s in text} for n in tree.body if isinstance(n, ast.Assign) for text in [ast.unparse(n.value)] for t in n.targets if isinstance(t, ast.Name)}
        # Module functions and class methods: a nested def is walked with the function around it.
        outer = [n for n in tree.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]
        outer += [m for c in tree.body if isinstance(c, ast.ClassDef) for m in c.body if isinstance(m, ast.FunctionDef | ast.AsyncFunctionDef)]
        for fn in outer:
            nodes = list(ast.walk(fn))
            texts = {n.value for n in nodes if isinstance(n, ast.Constant) and isinstance(n.value, str)}
            names = {s for s in scripts for text in texts if text.endswith(s)}
            names |= {s for n in nodes if isinstance(n, ast.Name) for s in named_by.get(n.id, set())}
            cleanup = {s for t in ast.walk(fn) if isinstance(t, ast.Try) for stmt in t.finalbody for s in _strings(stmt, consts)}
            if names:
                found.append((names, cleanup))
    return found


def scratch_findings(scripts_dir: Path, host_modules: "list[Path]") -> "list[str]":
    trees = {path.name: ast.parse(path.read_text(encoding="utf-8")) for path in sorted(scripts_dir.glob("*.py"))}
    finals = {name: _removed_in_finally(tree) for name, tree in trees.items()}
    removed, rmdirs = {name: f["remove"] for name, f in finals.items()}, {name: f["rmdir"] for name, f in finals.items()}
    runs = _host_runs(host_modules, set(trees))
    found: list[str] = []
    for name, tree in trees.items():
        peers = [(scripts, cleanup) for scripts, cleanup in runs if name in scripts]
        for scratch in sorted(_scratch_files(tree)):
            by_script = scratch in removed[name] or any(scratch in removed[peer] for scripts, _ in peers for peer in scripts)
            by_host = any(any(scratch in text for text in cleanup) for _, cleanup in peers)
            if not (by_script or by_host):
                found.append(f"{name}: {scratch} is removed in no finally of its own or of a script its host test runs")
        if _builds_over_scratch(tree):
            directory = _string_consts(tree).get(_SCRATCH_DIR_NAME, "")
            own = bool(removed[name]) and directory in rmdirs[name]
            by_host = any(any(directory and directory in text for text in cleanup) for _, cleanup in peers)
            if not (own or by_host):
                found.append(f"{name}: builds over {_SCRATCH_DIR_NAME} ({directory!r}) and removes neither its files nor the directory in a finally")
    return found


def test_every_scratch_config_file_is_removed() -> None:
    hosts = sorted(p for p in _TESTS_HARDWARE.rglob("*.py") if "device_scripts" not in p.parts)
    assert _host_runs(hosts, {p.name for p in DEVICE_SCRIPTS.glob("*.py")}), "no host function names a device script - the scan reads nothing"
    found = scratch_findings(DEVICE_SCRIPTS, hosts)
    assert not found, "scratch config left on the board's flash after a run:\n  " + "\n  ".join(found)


def test_the_scratch_check_bites(tmp_path: Path) -> None:
    scripts, host = tmp_path / "device_scripts", tmp_path / "test_host.py"
    scripts.mkdir()
    (scripts / "keeps.py").write_text('_PATH = "config_HWTEST_A.cfg"\nmgr = ConfigManager(_PATH, S, "HWTEST")\n', encoding="utf-8")
    (scripts / "cleans.py").write_text('import os\n_PATH = "config_HWTEST_B.cfg"\n\n\ndef _rm():\n    os.remove(_PATH)\n\n\ntry:\n    run()\nfinally:\n    _rm()\n', encoding="utf-8")
    (scripts / "scratch_build.py").write_text('_SCRATCH_CFG_PATH = "hwtest-scratch/"\nawait device.build_system(watchdog=w, cfg_path=_SCRATCH_CFG_PATH)\n', encoding="utf-8")
    host.write_text("def test_a(board):\n    board.run_isolated(D / 'keeps.py')\n    board.run_isolated(D / 'cleans.py')\n    board.run_isolated(D / 'scratch_build.py')\n", encoding="utf-8")
    assert [f.split(":", 1)[0] for f in scratch_findings(scripts, [host])] == ["keeps.py", "scratch_build.py"]
    host.write_text("def test_a(board):\n    try:\n        board.run_isolated(D / 'keeps.py')\n        board.run_isolated(D / 'scratch_build.py')\n    finally:\n        board.exec(\"import os; os.remove('config_HWTEST_A.cfg'); rmtree('hwtest-scratch/')\")\n", encoding="utf-8")
    assert scratch_findings(scripts, [host]) == []
