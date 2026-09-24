"""Pins that every device script measuring the heap sets gc.threshold itself and prints GC_THRESHOLD=.
mpremote interrupts main.py without resetting the interpreter, so an unset threshold is the boot
entry's, inherited silently - a result line that does not name its threshold is void (MEASUREMENTS §10)."""

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


def _prints_marker(tree: ast.Module) -> bool:
    # A print whose argument's literal text starts with the marker - an f-string's first piece included.
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print" and node.args:
            arg = node.args[0]
            head = arg.values[0] if isinstance(arg, ast.JoinedStr) and arg.values else arg
            if isinstance(head, ast.Constant) and isinstance(head.value, str) and head.value.startswith(_MARKER):
                return True
    return False


def _problems(source: str) -> list[str]:
    tree = ast.parse(source)
    calls = _calls(tree)
    if not any((mod, fn) in _MEASURES for mod, fn, _n in calls):
        return []
    problems = []
    if not any(mod == "gc" and fn == "threshold" and n >= 1 for mod, fn, n in calls):
        problems.append("measures the heap but never sets gc.threshold - it runs under whatever main.py left")
    if not _prints_marker(tree):
        problems.append(f"measures the heap but never prints {_MARKER} - its output cannot say what it was taken at")
    return problems


def _measuring_scripts() -> list[Path]:
    return sorted(p for p in DEVICE_SCRIPTS.glob("*.py") if any((m, f) in _MEASURES for m, f, _n in _calls(ast.parse(p.read_text()))))


def test_the_rule_covers_every_heap_measuring_script_there_is() -> None:
    # Guards the detector itself: an empty or shrunken set would pass everything below vacuously.
    names = {p.name for p in _measuring_scripts()}
    assert {"serving_at_default_gc.py", "heap_under_connection_ceiling.py", "allocation_need_per_source.py"} <= names, names


@pytest.mark.parametrize("script", _measuring_scripts(), ids=lambda p: p.name)
def test_every_heap_measuring_device_script_sets_and_reports_its_gc_threshold(script: Path) -> None:
    assert _problems(script.read_text()) == [], script.name


def test_a_threshold_named_only_in_a_comment_or_read_back_does_not_count_as_set() -> None:
    # The shape heap_under_connection_ceiling.py had: the value in prose, the call nowhere.
    source = 'import gc\n# at gc.threshold(-1) that is the real state\nprint(f"GC_THRESHOLD={gc.threshold()}")\ngc.mem_free()\n'
    assert _problems(source) == ["measures the heap but never sets gc.threshold - it runs under whatever main.py left"]


def test_a_threshold_set_but_never_reported_is_caught() -> None:
    assert _problems("import gc\ngc.threshold(-1)\nprint(gc.mem_free())\n") == [f"measures the heap but never prints {_MARKER} - its output cannot say what it was taken at"]


def test_a_script_that_does_not_measure_the_heap_owes_nothing() -> None:
    assert _problems("import gc\ngc.collect()\nprint('RESULT: PASS')\n") == []
