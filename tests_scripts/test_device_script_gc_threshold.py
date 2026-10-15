"""Pins that every device script measuring the heap sets gc.threshold itself and reports the gc_threshold fact first:
mpremote's soft reset keeps the boot entry's threshold, so a figure not naming its stage is void
(SPECIFICATION.md E.8). Read on the rendered scripts, so a measurement through an include counts."""

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests_hardware"))
import bench_facts
import harness

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "tests_hardware" / "device_scripts"

# What makes a script a heap measurement: it reads the heap's own figures or its block map.
_MEASURES = {("gc", "mem_free"), ("gc", "mem_alloc"), ("micropython", "mem_info")}
_FACT = "gc_threshold"


def _calls(tree: ast.Module) -> "list[tuple[str, str, ast.Call]]":
    # (module, function, call) for every call of a module function in any spelling: gc.f(), g.f() after `import gc as
    # g`, and f() or x() after `from gc import f [as x]`.
    modules = {alias.asname or alias.name: alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    functions = {alias.asname or alias.name: (node.module or "", alias.name) for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) for alias in node.names}
    found: list[tuple[str, str, ast.Call]] = []
    for node in [n for n in ast.walk(tree) if isinstance(n, ast.Call)]:
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            found.append((modules.get(node.func.value.id, node.func.value.id), node.func.attr, node))
        elif isinstance(node.func, ast.Name) and node.func.id in functions:
            found.append((*functions[node.func.id], node))
    return found


def _report_lines(tree: ast.Module) -> "list[int]":
    # Lines of every fact("gc_threshold", ...) call: the script's report of the stage it measured at.
    return [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "fact" and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == _FACT]


def _problems(source: str) -> "list[str]":
    tree = ast.parse(source)
    calls = _calls(tree)
    if not any((mod, fn) in _MEASURES for mod, fn, _ in calls):
        return []
    problems = []
    # The no-argument gc.threshold() reads the value back, never sets it.
    sets = [call.lineno for mod, fn, call in calls if (mod, fn) == ("gc", "threshold") and call.args]
    reports = _report_lines(tree)
    if not sets:
        problems.append("measures the heap but never sets gc.threshold - it runs under whatever main.py left")
    if not reports:
        problems.append(f'measures the heap but never reports fact("{_FACT}", ...) - its output cannot say what it was taken at')
    if sets and reports and min(reports) < min(sets):
        # A first arm run at whatever it inherited, made to look set by a later switch.
        problems.append(f"reports {_FACT} at line {min(reports)} before setting gc.threshold at line {min(sets)} - that first arm runs at whatever it inherited")
    return problems


def _rendered_measuring_scripts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> "dict[str, str]":
    monkeypatch.setattr(harness, "RENDERED_SCRIPTS_DIR", tmp_path)
    # A static check reads the includes a render inlines; no fact value enters it, so the render takes the device
    # module's name alone instead of a cold build of every fact.
    module = f"sensortask_{harness.bench_device()}"
    monkeypatch.setattr(bench_facts, "build", lambda _device: {"device_module": module})
    rendered = {p.name: harness.render_device_script(p).read_text(encoding="utf-8") for p in sorted(DEVICE_SCRIPTS.glob("*.py"))}
    return {name: source for name, source in rendered.items() if any((m, f) in _MEASURES for m, f, _ in _calls(ast.parse(source)))}


def test_every_heap_measuring_device_script_sets_and_reports_its_gc_threshold(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    measuring = _rendered_measuring_scripts(tmp_path, monkeypatch)
    # Guards the detector itself: an empty or shrunken set would pass everything below vacuously.
    assert {"serving_at_default_gc.py", "heap_under_connection_ceiling.py", "allocation_need_per_source.py", "heap_headroom_after_full_system_build.py", "heap_layout_after_full_boot_sequence.py"} <= set(measuring), sorted(measuring)
    found = {name: problems for name, source in measuring.items() if (problems := _problems(source))}
    assert not found, found


@pytest.mark.parametrize(
    "source",
    [
        "import gc as g\ng.threshold(-1)\nfact('gc_threshold', g.threshold())\ng.mem_free()\n",
        "from gc import mem_free as free, threshold as limit\nlimit(32768)\nfact('gc_threshold', 32768)\nfree()\n",
    ],
    ids=["module-alias", "from-import-alias"],
)
def test_every_spelling_of_the_set_and_the_measurement_counts(source: str) -> None:
    assert _problems(source) == []


def test_a_threshold_named_only_in_a_comment_or_read_back_does_not_count_as_set() -> None:
    # The value in prose, the call nowhere.
    source = "import gc\n# at gc.threshold(-1) that is the real state\nfact('gc_threshold', gc.threshold())\ngc.mem_free()\n"
    assert _problems(source) == ["measures the heap but never sets gc.threshold - it runs under whatever main.py left"]


def test_a_threshold_set_but_never_reported_is_caught() -> None:
    assert _problems("from gc import mem_free\nimport gc\ngc.threshold(-1)\nprint(mem_free())\n") == [f'measures the heap but never reports fact("{_FACT}", ...) - its output cannot say what it was taken at']


def test_a_threshold_set_only_after_the_first_reported_arm_is_caught() -> None:
    # A set anywhere in the file is not enough: a later switch would make an inherited first arm look chosen.
    # @tunable gc.threshold_bytes = 32768
    source = "import gc\nfact('gc_threshold', gc.threshold())\nprint(gc.mem_free())\ngc.threshold(32768)\nfact('gc_threshold', 32768)\n"
    assert _problems(source) == ["reports gc_threshold at line 2 before setting gc.threshold at line 4 - that first arm runs at whatever it inherited"]


def test_a_script_that_does_not_measure_the_heap_owes_nothing() -> None:
    assert _problems("import gc\ngc.collect()\nfact('ok', True)\n") == []
