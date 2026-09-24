"""Pins that every bench test running a device script puts the board back to serving afterwards.
run_isolated() leaves main.py stopped, and the one bench test that did not restore it failed every
network test after it in the same run (tests_hardware/README.md, "Holding a ceiling open")."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parent.parent / "tests_hardware" / "bench"
_RUNS = "run_isolated"
_RESTORES = "restore_board_to_serving"


def _called_names(node: ast.AST) -> set[str]:
    names = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            func = sub.func
            names.add(func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else "")
    return names


def _is_fixture(fn: ast.FunctionDef) -> bool:
    for dec in fn.decorator_list:
        target = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(target, ast.Attribute) and target.attr == "fixture":
            return True
    return False


def _restores_on_every_exit(fn: ast.FunctionDef) -> bool:
    # In a finally, or - for a fixture - anywhere after its yield, which pytest runs as teardown.
    finally_blocks = [stmt for node in ast.walk(fn) if isinstance(node, ast.Try) for stmt in node.finalbody]
    if any(_RESTORES in _called_names(stmt) for stmt in finally_blocks):
        return True
    if _is_fixture(fn):
        yields = [i for i, stmt in enumerate(fn.body) if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Yield)]
        return bool(yields) and any(_RESTORES in _called_names(stmt) for stmt in fn.body[yields[0] + 1 :])
    return False


def _problems(source: str) -> list[str]:
    functions = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef)]
    restoring_fixtures = {fn.name for fn in functions if _is_fixture(fn) and _restores_on_every_exit(fn)}
    problems = []
    for fn in functions:
        if _RUNS not in _called_names(fn) or _is_fixture(fn):
            continue
        via_fixture = {a.arg for a in fn.args.args} & restoring_fixtures
        if not via_fixture and not _restores_on_every_exit(fn):
            problems.append(f"{fn.name} calls {_RUNS}() but never reaches {_RESTORES}() in a finally or a fixture's teardown")
    return problems


def _runners() -> list[Path]:
    return sorted(p for p in BENCH.glob("test_*.py") if f".{_RUNS}(" in p.read_text())


def test_the_rule_sees_the_bench_tests_that_run_device_scripts() -> None:
    # Guards the detector: an empty set would pass the test below vacuously.
    assert {"test_heap_under_connection_ceiling.py", "test_serving_heap_at_default_gc.py"} <= {p.name for p in _runners()}


@pytest.mark.parametrize("module", _runners(), ids=lambda p: p.name)
def test_every_bench_test_running_a_device_script_restores_the_board_to_serving(module: Path) -> None:
    assert _problems(module.read_text()) == [], module.name


def test_a_restore_outside_a_finally_does_not_count() -> None:
    # A failing assertion before it skips the restore - exactly the run that then breaks the rest.
    source = "def test_x(board, bench, dut_ip):\n    board.run_isolated('s.py')\n    restore_board_to_serving(board, bench, dut_ip)\n"
    assert _problems(source) == ["test_x calls run_isolated() but never reaches restore_board_to_serving() in a finally or a fixture's teardown"]


def test_a_fixture_restoring_after_its_yield_covers_every_test_that_takes_it() -> None:
    source = (
        "import pytest\n@pytest.fixture(scope='module')\ndef isolated(board, bench, dut_ip):\n    yield board\n    restore_board_to_serving(board, bench, dut_ip)\n"
        "def test_x(isolated):\n    isolated.run_isolated('s.py')\n"
    )
    assert _problems(source) == []


def test_a_fixture_restoring_before_its_yield_does_not_count() -> None:
    source = (
        "import pytest\n@pytest.fixture\ndef isolated(board, bench, dut_ip):\n    restore_board_to_serving(board, bench, dut_ip)\n    yield board\n"
        "def test_x(isolated):\n    isolated.run_isolated('s.py')\n"
    )
    assert len(_problems(source)) == 1
