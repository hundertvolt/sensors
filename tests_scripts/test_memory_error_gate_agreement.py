"""SPECIFICATION.md Part I.4(e)'s bar is asserted by four separate gates - the unit tier, the twin
tier and the flash/bench hardware tiers - and each had its own copy of the pattern. Three of the
four were blind to a caught-and-logged failure until 2026-09-22; this keeps them agreeing."""

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
