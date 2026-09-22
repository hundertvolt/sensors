"""SPECIFICATION.md Part I.4(e)'s bar is asserted by four separate gates - the unit tier, the twin
tier and the flash/bench hardware tiers - each with its own copy of the pattern. Three of the four
were blind to a caught degrade until 2026-09-22; this keeps them agreeing, and the suite's own
deliberate injections clear of the wording they grep for."""

import ast
from pathlib import Path
from types import ModuleType

import pytest
from _script_loader import load_script_module

# The interpreter's own MemoryError messages, from py/runtime.c:1692/1696 - the only two in the
# pinned source. src/ logs str(e), never the class, so the second marker is the one that sees a
# caught degrade; the class name appears only in an uncaught traceback.
_CANONICAL = ("MemoryError", "memory allocation failed")

_HARDWARE_TIER_FILES = (
    "tests_hardware/flash/test_memory_stress.py",
    "tests_hardware/bench/test_memory_stress_bench.py",
)


@pytest.fixture
def harness(repo_root: Path) -> ModuleType:
    return load_script_module(repo_root / "tests_hardware" / "harness.py", "harness")


def test_the_hardware_tier_holds_the_canonical_marker_set(harness: ModuleType) -> None:
    assert tuple(harness.MEMORY_ERROR_MARKERS) == _CANONICAL, f"tests_hardware/harness.py no longer carries {_CANONICAL} - all four gates have to move together"


def test_the_twin_tier_agrees_with_it(ci_suite: ModuleType, harness: ModuleType) -> None:
    assert tuple(ci_suite._MEMORY_ERROR_MARKERS) == tuple(harness.MEMORY_ERROR_MARKERS), f"the twin gate matches {ci_suite._MEMORY_ERROR_MARKERS} against the hardware tier's {harness.MEMORY_ERROR_MARKERS}"


def test_the_unit_tier_agrees_with_it(repo_root: Path, harness: ModuleType) -> None:
    # A grep pattern rather than a tuple, so this is the one gate that cannot simply be compared.
    pattern = "|".join(harness.MEMORY_ERROR_MARKERS)
    assert f'local pattern="{pattern}"' in (repo_root / "scripts" / "test.sh").read_text(), f"scripts/test.sh's MemoryError gate no longer greps for {pattern!r}"


@pytest.mark.parametrize("path", _HARDWARE_TIER_FILES)
def test_no_hardware_tier_gate_hardcodes_the_class_name_again(repo_root: Path, path: str) -> None:
    # The regression that would undo this: a new soak assertion written with a bare "MemoryError"
    # substring, which is green for every caught degrade. The shared constant is the only route.
    text = (repo_root / path).read_text()
    assert "MEMORY_ERROR_MARKERS" in text, f"{path} must reach the marker set through harness.MEMORY_ERROR_MARKERS"
    offenders = [n for n, line in enumerate(text.split("\n"), 1) if '"MemoryError"' in line and "MEMORY_ERROR_MARKERS" not in line]
    assert not offenders, f"{path} lines {offenders} test for the bare class name, which a caught-and-logged failure never prints"


# The other half of a substring gate: what the suite's own deliberate failures are allowed to say.
# Nothing pinned this, and one carelessly worded injection would fail every run of a healthy tree.
_INJECTION_SCOPES = ("tests", "digital_twin")


def _callee_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    return call.func.attr if isinstance(call.func, ast.Attribute) else None


def _injected_messages(repo_root: Path) -> list[tuple[str, int, str]]:
    # Two shapes: a MemoryError built anywhere (raised now, or queued for a fake to raise later),
    # and a raise through a variable class - tests/machine.py's Timer fake, whose injected class is
    # whichever one the test picked, so the name at the raise site is never a builtin's.
    found: list[tuple[str, int, str]] = []
    for scope in _INJECTION_SCOPES:
        # tests/_tmp is skipped, not parsed: it is per-test scratch that 85 concurrently running
        # test files create and delete under this tier's feet, so walking it would make this
        # assertion depend on what they happen to be holding.
        for path in sorted(q for q in (repo_root / scope).rglob("*.py") if "_tmp" not in q.parts):
            for node in ast.walk(ast.parse(path.read_text())):
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
