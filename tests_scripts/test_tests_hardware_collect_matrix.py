"""The hardware levels collect under every option with nothing attached: one subprocess with no
hardware tool on PATH loops pytest.main() over the option combinations and reports each exit code
and item count; a fixture that needs hardware may skip, collection itself never fails."""

import ast
import itertools
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from _devices import DEVICE_NAMES
from _script_loader import load_script_module

# The tools a fixture would reach for; none may be on PATH, so collection proves it calls none.
_HARDWARE_TOOLS = ("mpremote", "nmcli", "iw", "tc", "iptables", "picotool")
_BOOLEANS = (
    "--allow-flash-cycle",
    "--allow-multi-day-rollover",
    "--allow-neopixel-sweep",
    "--allow-persistence-write",
    "--allow-scd30-extra-write",
    "--allow-toolchain-reverify",
    "--repair-standard-state",
    "--twin",
)
# The only options read while collecting (the wear gates' deselection); every other is a fixture's, read at run time.
_READ_AT_COLLECTION = {"--allow-persistence-write", "--allow-scd30-extra-write"}
_COLLECTION_HOOKS = {"pytest_collection", "pytest_collection_modifyitems", "pytest_collect_file", "pytest_pycollect_makeitem", "pytest_generate_tests", "pytest_itemcollected", "pytest_collection_finish", "pytest_ignore_collect"}

_LOOP = """
import contextlib, io, json, sys
import pytest

class _Count:
    def __init__(self):
        self.items = 0
    def pytest_collection_finish(self, session):
        self.items = len(session.items)

results = []
for combo in json.loads(sys.argv[1]):
    counter = _Count()
    with contextlib.redirect_stdout(io.StringIO()):
        code = pytest.main(["tests_hardware", "--collect-only", "-q", "-p", "no:cacheprovider", *combo], plugins=[counter])
    results.append({"combo": combo, "code": int(code), "items": counter.items})
print(json.dumps(results))
"""


def _bare_path() -> str:
    # PATH without any directory holding a hardware tool; the interpreter runs by its absolute path, so its own
    # directory (which holds the venv's mpremote) stays off too.
    keep = [d for d in os.environ.get("PATH", "").split(os.pathsep) if d and not any((Path(d) / tool).exists() for tool in _HARDWARE_TOOLS)]
    bare = os.pathsep.join(keep)
    assert not [tool for tool in _HARDWARE_TOOLS if shutil.which(tool, path=bare)], "a hardware tool is still on the stripped PATH"
    return bare


def _collect_all(repo_root: Path, combos: "list[list[str]]") -> "list[dict[str, object]]":
    env = dict(os.environ, PATH=_bare_path())
    ran = subprocess.run([sys.executable, "-c", _LOOP, json.dumps(combos)], capture_output=True, text=True, check=False, cwd=repo_root, env=env, timeout=600)
    assert ran.returncode == 0, ran.stdout + ran.stderr
    results: list[dict[str, object]] = json.loads(ran.stdout.strip().splitlines()[-1])
    assert [r["combo"] for r in results] == combos, "the loop skipped a combination"
    return results


def _soak_durations(repo_root: Path) -> "list[str]":
    return sorted(load_script_module(repo_root / "tests_hardware" / "soak_durations.py", "soak_durations_for_collect_matrix").SOAK_DURATION_SECONDS)


def test_every_option_combination_collects_with_nothing_attached(repo_root: Path, tmp_path: Path) -> None:
    durations = _soak_durations(repo_root)
    assert durations == ["long", "mid", "short"], durations
    soaks = [["--soak-duration", d] for d in durations]
    # Every subset of the two flags collection reads; each soak value and each other flag alone, then all on with each
    # soak value (the full 2^8 x 4 product measured 139 s; the read scan below proves no other option is read while collecting).
    read = sorted(_READ_AT_COLLECTION)
    combos = [list(flags) for n in range(len(read) + 1) for flags in itertools.combinations(read, n)]
    combos += soaks + [[flag] for flag in _BOOLEANS if flag not in _READ_AT_COLLECTION]
    combos += [[*_BOOLEANS, *soak] for soak in [[], *soaks]]
    absent = str(tmp_path / "absent")  # a path nothing has written: collection must not read it
    valued = [["--bench-device", name] for name in DEVICE_NAMES]
    valued += [["--image-record", absent], ["--device", "/dev/no-such-board"], ["--dut-ip", "192.0.2.1"], ["--lwip-control-image", absent], ["--rollover-image", absent]]
    combos += [[*_BOOLEANS, *option] for option in valued]
    failed = [r for r in _collect_all(repo_root, combos) if r["code"] != 0 or not r["items"]]
    assert not failed, f"collection failed or found nothing under these options: {failed[:5]} ({len(failed)} in all)"
    assert sorted(p.name for p in tmp_path.iterdir()) == [], "collection wrote a file"


def _read_of(node: ast.AST) -> "str | None":
    # A getoption("<name>") call as its name (a computed one as "?"), a `.option.<dest>` read as "option.<dest>".
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "getoption":
        arg = node.args[0] if node.args else None
        return arg.value if isinstance(arg, ast.Constant) and isinstance(arg.value, str) else "?"
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute) and node.value.attr == "option":
        return f"option.{node.attr}"
    return None


def _collection_and_import_reads(source: str) -> "tuple[list[str], list[str]]":
    # (reads inside a collection hook, reads that run when the module is imported: outside every function and lambda
    # body, decorators and defaults included).
    tree = ast.parse(source)
    hooks = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name in _COLLECTION_HOOKS]
    in_hooks = [read for hook in hooks for sub in ast.walk(hook) if (read := _read_of(sub)) is not None]
    at_import: list[str] = []
    pending: list[ast.AST] = [tree]
    while pending:
        node = pending.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            decorators = node.decorator_list if not isinstance(node, ast.Lambda) else []
            pending += [*decorators, *node.args.defaults, *(d for d in node.args.kw_defaults if d is not None)]
            continue
        read = _read_of(node)
        if read is not None:
            at_import.append(read)
        pending += ast.iter_child_nodes(node)
    return in_hooks, at_import


def test_only_the_wear_gates_are_read_at_collection_and_nothing_at_import(repo_root: Path) -> None:
    hooks, _ = _collection_and_import_reads((repo_root / "tests_hardware" / "conftest.py").read_text(encoding="utf-8"))
    assert set(hooks) == _READ_AT_COLLECTION, f"the conftest's collection hook reads {sorted(set(hooks))} - the scan below would see nothing"
    offenders: list[str] = []
    for path in sorted((repo_root / "tests_hardware").rglob("*.py")):
        if "device_scripts" in path.parts:
            continue
        in_hooks, at_import = _collection_and_import_reads(path.read_text(encoding="utf-8"))
        rel = path.relative_to(repo_root).as_posix()
        offenders += [f"{rel}: {read} read at collection" for read in in_hooks if read not in _READ_AT_COLLECTION]
        offenders += [f"{rel}: {read} read at import" for read in at_import]
    assert not offenders, offenders


def test_the_read_scan_sees_a_collection_hook_and_a_module_level_read() -> None:
    planted = 'X = config.getoption("--twin")\n\ndef pytest_collection_modifyitems(config, items):\n    config.getoption("--device")\n'
    assert _collection_and_import_reads(planted) == (["--device"], ["--twin"])
