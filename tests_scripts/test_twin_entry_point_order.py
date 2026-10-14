"""Every twin entry point that boots a device prewarms the poll set, then applies the UDP shim, before anything else
runs: a booting tests/test_digital_twin_*.py at module level, a booting digital_twin/ main() as its first statements
(after the exception report's install()); and the prewarm's ceiling clears 3 x the largest max_connections."""

import ast
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES, device_toml

from buildgen.validate import device_max_connections

REPO_ROOT = Path(__file__).resolve().parent.parent
_PREWARM = "prewarm_poll_set"
_SHIM = "patch_asy_udp_socket_for_unix_port"
_ORDER = [_PREWARM, _SHIM]
_REPORT = "install"  # unix_port_unretrieved_report's: the one call allowed ahead of the two (no poll object, no socket)
_RUNNER = "run_generic_integration"


def _is_path_edit(node: ast.stmt) -> bool:
    return isinstance(node, ast.Expr) and ast.unparse(node).startswith("sys.path.")


def _booting(tests_dir: Path) -> "list[Path]":
    # The test files that boot a device, directly or through a tests/_*.py scenario library that does.
    libraries = {path.stem for path in tests_dir.glob("_*.py") if _loads_a_device_itself(ast.parse(path.read_text(encoding="utf-8")))}
    found = []
    for path in sorted(tests_dir.glob("test_digital_twin_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if _loads_a_device_itself(tree) or _imported(tree) & libraries:
            found.append(path)
    return found


def _call_name(node: ast.AST) -> "str | None":
    if isinstance(node, ast.Expr):
        node = node.value
    if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
        node = node.value
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    return func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""


def _imported(tree: ast.Module) -> "set[str]":
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def _loads_a_device_itself(tree: ast.Module) -> bool:
    # A static load of a generated module or the runner, or an __import__() of a sensortask_ name.
    for node in ast.walk(tree):
        names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""] if isinstance(node, ast.ImportFrom) else []
        if any(name.startswith("sensortask_") or name == _RUNNER for name in names):
            return True
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "__import__" and node.args and "sensortask_" in ast.unparse(node.args[0]):
            return True
    return False


def _module_events(path: Path) -> "list[str]":
    # The module-level calls in order, sys.path edits aside; an import of a scenario library (a tests/_*.py that loads a
    # device) contributes that library's own calls at that point, since its module level runs there.
    events: list[str] = []
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        modules = [node.module] if isinstance(node, ast.ImportFrom) and node.module else [a.name for a in node.names] if isinstance(node, ast.Import) else []
        for module in modules:
            library = path.parent / f"{module}.py"
            if module.startswith("_") and library.is_file() and _loads_a_device_itself(ast.parse(library.read_text(encoding="utf-8"))):
                events.extend(_module_events(library))
        if not _is_path_edit(node) and (name := _call_name(node)) is not None:
            events.append(name)
    return events


def main_order_problems(path: Path) -> "list[str]":
    # A booting digital_twin/ main(): its first statements (global declarations aside) are the prewarm and the shim,
    # with the exception report's install() allowed ahead of them.
    tree = ast.parse(path.read_text(encoding="utf-8"))
    if not _loads_a_device_itself(tree) and "__import__(" not in ast.unparse(tree):
        return []
    problems = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "main":
            calls = [_call_name(stmt) for stmt in node.body if not isinstance(stmt, ast.Global)]
            if calls[:1] == [_REPORT]:
                calls = calls[1:]
            if calls[:2] != _ORDER:
                problems.append(f"{path.name}: main() starts {calls[:2]}, not {_ORDER}")
    return problems


def module_order_problems(path: Path) -> "list[str]":
    # The prewarm is the first module-level call (sys.path edits aside) and the shim follows it at module level.
    events = _module_events(path)
    if events[:1] != [_PREWARM] or _SHIM not in events:
        return [f"{path.name}: module-level calls start {events[:2]} with the shim {'present' if _SHIM in events else 'absent'}, not {_ORDER}"]
    return []


def test_every_booting_twin_test_file_prewarms_then_shims_first() -> None:
    booting = _booting(REPO_ROOT / "tests")
    assert len(booting) >= 10, [p.name for p in booting]  # not vacuous: the construction, concurrency and boot files
    problems = [problem for path in booting for problem in module_order_problems(path)]
    assert problems == [], problems


def test_every_booting_twin_main_prewarms_then_shims_first() -> None:
    mains = [path for path in sorted((REPO_ROOT / "digital_twin").rglob("*.py")) if "def main(" in path.read_text(encoding="utf-8")]
    assert any(path.name == f"{_RUNNER}.py" for path in mains), mains
    problems = [problem for path in mains for problem in main_order_problems(path)]
    assert problems == [], problems


def test_the_prewarm_ceiling_clears_three_times_the_largest_connection_ceiling() -> None:
    tree = ast.parse((REPO_ROOT / "digital_twin" / "unix_port_poll_prewarm.py").read_text(encoding="utf-8"))
    (ceiling,) = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and ast.unparse(n.targets[0]) == "_DEFAULT_CEILING"]
    largest = max(device_max_connections(device_toml(device), REPO_ROOT / "src") for device in DEVICE_NAMES)
    assert 3 * largest < ceiling, (largest, ceiling)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("import sys\nsys.path.insert(0, 'x')\nprewarm_poll_set()\npatch_asy_udp_socket_for_unix_port()\nimport sensortask_x\n", []),
        ("import sensortask_x\nrequire_fresh()\nprewarm_poll_set()\npatch_asy_udp_socket_for_unix_port()\n", ["module-level calls start"]),
        ("import run_generic_integration\npatch_asy_udp_socket_for_unix_port()\nprewarm_poll_set()\n", ["module-level calls start"]),
        ("prewarm_poll_set()\nimport sensortask_x\n_scratch = TmpScratch('x')\n", ["shim absent"]),
    ],
)
def test_a_planted_order_is_caught(tmp_path: Path, source: str, expected: "list[str]") -> None:
    path = tmp_path / "test_digital_twin_planted.py"
    path.write_text(source, encoding="utf-8")
    found = module_order_problems(path)
    assert len(found) == len(expected) and all(e in f for f, e in zip(found, expected, strict=True)), found


def test_a_planted_main_order_is_caught(tmp_path: Path) -> None:
    path = tmp_path / "planted_runner.py"
    path.write_text("import sensortask_x\nasync def main():\n    global x\n    install()\n    patch_asy_udp_socket_for_unix_port()\n    prewarm_poll_set()\n", encoding="utf-8")
    assert main_order_problems(path) != []
    path.write_text("import sensortask_x\nasync def main():\n    install()\n    prewarm_poll_set()\n    patch_asy_udp_socket_for_unix_port()\n", encoding="utf-8")
    assert main_order_problems(path) == []
