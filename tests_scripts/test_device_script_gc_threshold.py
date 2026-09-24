"""Pins that every device script measuring the heap sets gc.threshold itself and prints GC_THRESHOLD=.
mpremote's raw-REPL soft reset keeps the boot entry's threshold (rp2 runs gc_init() once, outside that
loop), so an unset one is inherited silently - a result not naming its threshold is void (MEASUREMENTS §10)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "tests_hardware" / "device_scripts"

# What makes a script a heap measurement: it reads the heap's own figures or its block map.
_MEASURES = {("gc", "mem_free"), ("gc", "mem_alloc"), ("micropython", "mem_info")}
_MARKER = "GC_THRESHOLD="


def _calls(tree: ast.Module) -> list[tuple[str, str, int]]:
    # (module, function, argument count) for every plain `module.function(...)` call.
    return [
        (node.func.value.id, node.func.attr, len(node.args))
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
    ]


def _marker_print_lines(tree: ast.Module) -> list[int]:
    # Lines of every print whose argument's literal text starts with the marker - an f-string's
    # first piece included. Empty means the script never reports the threshold it ran at.
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print" and node.args:
            arg = node.args[0]
            head = arg.values[0] if isinstance(arg, ast.JoinedStr) and arg.values else arg
            if isinstance(head, ast.Constant) and isinstance(head.value, str) and head.value.startswith(_MARKER):
                lines.append(node.lineno)
    return lines


def _set_lines(tree: ast.Module) -> list[int]:
    # Lines of every gc.threshold(<value>) call - the no-argument form reads it back, never sets it.
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "gc" and node.func.attr == "threshold" and node.args
    ]


def _problems(source: str) -> list[str]:
    tree = ast.parse(source)
    calls = _calls(tree)
    if not any((mod, fn) in _MEASURES for mod, fn, _n in calls):
        return []
    problems = []
    sets, reports = _set_lines(tree), _marker_print_lines(tree)
    if not sets:
        problems.append("measures the heap but never sets gc.threshold - it runs under whatever main.py left")
    if not reports:
        problems.append(f"measures the heap but never prints {_MARKER} - its output cannot say what it was taken at")
    if sets and reports and min(reports) < min(sets):
        # The shape both flash-tier scripts had until 2026-09-24: a first arm run at whatever it
        # inherited, made to look set by a later switch (MEASUREMENTS 0B.7).
        problems.append(f"reports {_MARKER} at line {min(reports)} before setting gc.threshold at line {min(sets)} - that first arm runs at whatever it inherited")
    return problems


def _measuring_scripts() -> list[Path]:
    return sorted(p for p in DEVICE_SCRIPTS.glob("*.py") if any((m, f) in _MEASURES for m, f, _n in _calls(ast.parse(p.read_text()))))


def test_the_rule_covers_every_heap_measuring_script_there_is() -> None:
    # Guards the detector itself: an empty or shrunken set would pass everything below vacuously.
    names = {p.name for p in _measuring_scripts()}
    assert {"serving_at_default_gc.py", "heap_under_connection_ceiling.py", "allocation_need_per_source.py", "heap_headroom_after_full_system_build.py", "heap_layout_after_full_boot_sequence.py"} <= names, names


@pytest.mark.parametrize("script", _measuring_scripts(), ids=lambda p: p.name)
def test_every_heap_measuring_device_script_sets_and_reports_its_gc_threshold(script: Path) -> None:
    assert _problems(script.read_text()) == [], script.name


def test_a_threshold_named_only_in_a_comment_or_read_back_does_not_count_as_set() -> None:
    # The shape heap_under_connection_ceiling.py had: the value in prose, the call nowhere.
    source = 'import gc\n# at gc.threshold(-1) that is the real state\nprint(f"GC_THRESHOLD={gc.threshold()}")\ngc.mem_free()\n'
    assert _problems(source) == ["measures the heap but never sets gc.threshold - it runs under whatever main.py left"]


def test_a_threshold_set_but_never_reported_is_caught() -> None:
    assert _problems("import gc\ngc.threshold(-1)\nprint(gc.mem_free())\n") == [f"measures the heap but never prints {_MARKER} - its output cannot say what it was taken at"]


def test_a_threshold_set_only_after_the_first_reported_arm_is_caught() -> None:
    # A call anywhere used to satisfy the rule, so a later switch made an inherited first arm look
    # chosen - the shape two flash-tier scripts had, whose first arm's threshold is now unknowable.
    source = 'import gc\nprint(f"GC_THRESHOLD={gc.threshold()}")\nprint(gc.mem_free())\ngc.threshold(32768)\nprint(f"GC_THRESHOLD={gc.threshold()}")\n'
    assert _problems(source) == ["reports GC_THRESHOLD= at line 2 before setting gc.threshold at line 4 - that first arm runs at whatever it inherited"]


def test_a_script_that_does_not_measure_the_heap_owes_nothing() -> None:
    assert _problems("import gc\ngc.collect()\nprint('RESULT: PASS')\n") == []
