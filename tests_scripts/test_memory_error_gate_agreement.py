"""SPECIFICATION.md Part I.4(e)'s bar is asserted by separate gates - unit, twin, flash, bench, heap map, the
tests_scripts twin boots and the JS live twins and smoke - each reading the pattern from scripts/memory_markers.json.
This keeps it their one source, and the suite's own injections clear of the wording they grep for."""

import ast
import json
import re
from pathlib import Path
from types import ModuleType

import pytest
from _repo_scan import python_files
from _script_loader import load_script_module

# The interpreter's own MemoryError wordings (py/runtime.c:1692/1696, v1.29.0). The message is placed only while an
# emergency exception buffer exists, which the boot entry reserves - without one it is empty. src/ logs str(e), so
# the second marker sees a caught degrade; the class name appears only in an uncaught traceback.
_CANONICAL = ("MemoryError", "memory allocation failed")

_HARDWARE_TIER_FILES = (
    "tests_hardware/flash/test_memory_stress.py",
    "tests_hardware/bench/test_memory_stress_bench.py",
    "tests_hardware/heap_map.py",
)


def _callee_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    return call.func.attr if isinstance(call.func, ast.Attribute) else None


_GATE_FILES = ("scripts/_twin_process.py", "scripts/test.sh", "tests_hardware/harness.py", "tests_js/_twin_process.js", "tests_js/_memory_markers.js")


def test_the_one_definition_holds_the_canonical_pair_and_every_gate_reads_it(repo_root: Path, harness: ModuleType) -> None:
    # One data file: the Python gates import it through scripts/_twin_process.py, test.sh and the Node frame read it.
    assert tuple(json.loads((repo_root / "scripts" / "memory_markers.json").read_text(encoding="utf-8"))) == _CANONICAL
    assert tuple(harness.MEMORY_ERROR_MARKERS) == _CANONICAL
    copies = [path for path in _GATE_FILES if any(f'"{marker}"' in (repo_root / path).read_text(encoding="utf-8") for marker in _CANONICAL)]
    assert copies == [], f"{copies} spell a marker literally - read scripts/memory_markers.json instead"


# Each JS runner that boots a twin scans its output through the shared module, never a copy.
_JS_GATE_IMPORTERS = ("scripts/cross_browser_smoke.mjs", "tests_js/_live_twin_command.js", "tests_js/_live_matrix_command.js")


@pytest.mark.parametrize("path", _JS_GATE_IMPORTERS)
def test_every_js_twin_runner_imports_the_shared_markers(repo_root: Path, path: str) -> None:
    text = (repo_root / path).read_text(encoding="utf-8")
    assert re.search(r"""from\s+["'][^"']*_memory_markers\.js["']""", text), f"{path} must import the marker set from tests_js/_memory_markers.js"


@pytest.mark.parametrize("path", ["tests_scripts/test_digital_twin_generated_boot.py", "tests_scripts/test_digital_twin_boot_contiguity.py"])
def test_every_tests_scripts_twin_boot_gates_on_the_markers(repo_root: Path, path: str) -> None:
    assert "MEMORY_ERROR_MARKERS" in (repo_root / path).read_text(encoding="utf-8"), f"{path} boots a twin and must scan its output for harness.MEMORY_ERROR_MARKERS"


@pytest.mark.parametrize("path", _HARDWARE_TIER_FILES)
def test_no_hardware_tier_gate_hardcodes_the_class_name_again(repo_root: Path, path: str) -> None:
    # The regression that would undo this: a new soak assertion written with a bare "MemoryError"
    # substring, which is green for every caught degrade. The shared constant is the only route.
    text = (repo_root / path).read_text(encoding="utf-8")
    assert "MEMORY_ERROR_MARKERS" in text, f"{path} must reach the marker set through harness.MEMORY_ERROR_MARKERS"
    offenders = [n for n, line in enumerate(text.split("\n"), 1) if '"MemoryError"' in line and "MEMORY_ERROR_MARKERS" not in line]
    assert not offenders, f"{path} lines {offenders} test for the bare class name, which a caught-and-logged failure never prints"


# The other half of a substring gate: what the suite's own deliberate failures are allowed to say.
# Nothing pinned this, and one carelessly worded injection would fail every run of a healthy tree.
_INJECTION_SCOPES = ("tests", "digital_twin")


def _injected_messages(repo_root: Path) -> list[tuple[str, int, str]]:
    # Two shapes: a MemoryError built anywhere (raised now, or queued for a fake to raise later),
    # and a raise through a variable class - tests/machine.py's Timer fake, whose injected class is
    # whichever one the test picked, so the name at the raise site is never a builtin's.
    found: list[tuple[str, int, str]] = []
    for scope in _INJECTION_SCOPES:
        for path in python_files(repo_root, scope):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                calls: list[ast.Call] = []
                if isinstance(node, ast.Call) and _callee_name(node) == "MemoryError":
                    calls.append(node)
                if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
                    name = _callee_name(node.exc)
                    if name is not None and not name.endswith(("Error", "Exception")):
                        calls.append(node.exc)
                for call in calls:
                    found += [(str(path.relative_to(repo_root)), call.lineno, arg.value) for arg in call.args if isinstance(arg, ast.Constant) and isinstance(arg.value, str)]
    return found


@pytest.fixture
def harness(repo_root: Path) -> ModuleType:
    return load_script_module(repo_root / "tests_hardware" / "harness.py", "harness_for_gate_agreement")


def test_the_suites_own_injections_never_spell_the_interpreters_wording(repo_root: Path) -> None:
    # A deliberate injection reads "simulated allocation failure" for exactly this reason: src/'s
    # handler logs whatever it is given, the gate greps that log, and a message borrowing the
    # interpreter's own words would fail every file it runs in on a tree with nothing wrong.
    messages = _injected_messages(repo_root)
    assert len(messages) >= 12, f"only {len(messages)} injected exception messages found across {_INJECTION_SCOPES} - this scan has stopped seeing them"
    offenders = [(path, line, text) for path, line, text in messages if any(marker in text for marker in _CANONICAL)]
    assert not offenders, f"these injected messages contain a gate marker and would fail their own file: {offenders}"


def test_the_marker_free_wording_is_actually_in_use(repo_root: Path) -> None:
    # Guards the assertion above against passing because the scan found nothing meaningful: the
    # known wording has to be among what it collected, not merely absent from it.
    texts = {text for _, _, text in _injected_messages(repo_root)}
    assert "simulated allocation failure" in texts, f"no injection uses the established wording any more - found {sorted(texts)[:10]}"
