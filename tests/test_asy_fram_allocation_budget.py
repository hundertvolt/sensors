"""Allocation budget for the FRAM path's boot-time cost: one blank and one valid PrintLogHistoryStore.setup() priced in a collection-free window, against a ceiling set from a measured run.
This is the efficiency half of SPECIFICATION.md I.4(e) - it fails if a coroutine-per-CS-cycle, or any comparable per-call allocation, regresses back into the path."""
# Absolute figures are binary-dependent, not board figures: plain runs use build-standard; --coverage runs
# build-settrace, which inflates every figure 4-5x - one budget per binary (SPECIFICATION.md E.5.2).

import gc
import sys

from _async_harness import run
from _fram_builders import make_fram_manager

from asy_print_log import PrintLogHistoryStore

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from asy_fram_manager import FRAMManager

# Measured 2026-10-13, mock tier, median of five, 13-15% margin: build-settrace 263,232 B blank / 238,208 B valid;
# build-standard 26,496 / 20,128 - the pair whose ratios carry to the board. The coverage tracer's float per call adds
# 58,976 / 54,336 B to the settrace pair (2026-10-14, SPECIFICATION.md E.5.2), added with the headroom unchanged.
_SETTRACE_BUILD = hasattr(sys, "settrace")
_BUDGET_BLANK = 361_000 if _SETTRACE_BUILD else 30_000
_BUDGET_VALID = 325_000 if _SETTRACE_BUILD else 23_000


async def _priced(logger: PrintLogHistoryStore) -> "tuple[int, int]":
    # One setup() inside a collection-free window. The collect comes first so the window starts
    # from a known floor; both figures are read before anything else allocates.
    gc.collect()
    free_before = gc.mem_free()
    alloc_before = gc.mem_alloc()
    logger.initialized = False
    await logger.setup()
    alloc_after = gc.mem_alloc()
    free_after = gc.mem_free()
    return alloc_after - alloc_before, free_before - free_after


async def _rig() -> "tuple[FRAMManager, PrintLogHistoryStore]":
    manager, _chip = make_fram_manager()
    assert await manager.setup()
    return manager, PrintLogHistoryStore(manager, 10, None, name="BUDGET")


def test_blank_setup_stays_within_its_allocation_budget() -> None:
    # A blank chip: setup()'s _read() finds no valid copy, so _write() lays down both. 14 byte-level
    # commands over 54 CS cycles - the most expensive shape the boot batch ever asks for.
    async def scenario() -> "tuple[int, int]":
        _manager, logger = await _rig()
        return await _priced(logger)

    allocated, consumed = run(scenario())
    assert allocated == consumed, f"a collection ran inside the window: {allocated} allocated, {consumed} consumed"
    assert allocated <= _BUDGET_BLANK, f"blank setup allocated {allocated} B, budget {_BUDGET_BLANK} B"


def test_valid_setup_stays_within_its_allocation_budget() -> None:
    # The steady-state shape: a chip that already carries a valid pair, so _read() succeeds and
    # _write() never runs. 47 CS cycles.
    async def scenario() -> "tuple[int, int]":
        _manager, logger = await _rig()
        await logger.setup()  # first setup lays the valid pair down, outside the window
        return await _priced(logger)

    allocated, consumed = run(scenario())
    assert allocated == consumed, f"a collection ran inside the window: {allocated} allocated, {consumed} consumed"
    assert allocated <= _BUDGET_VALID, f"valid setup allocated {allocated} B, budget {_BUDGET_VALID} B"


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
