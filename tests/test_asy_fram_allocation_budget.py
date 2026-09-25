"""Allocation budget for the FRAM path's boot-time cost: one blank and one valid PrintLogHistoryStore.setup() priced in a collection-free window, against a ceiling set from a measured run.
This is the efficiency half of SPECIFICATION.md I.4(e) - it fails if a coroutine-per-CS-cycle, or any comparable per-call allocation, regresses back into the path."""
# The absolute byte figures are binary-dependent and NOT board figures: a MICROPY_PY_SYS_SETTRACE=1
# build (which scripts/test.sh's interpreter is) inflates every number here 4-5x and non-uniformly
# - HEAP_FRAGMENTATION_MEASUREMENTS.md M3.7 and archive 3A. Both budgets are measured, one per build.

import asyncio
import gc
import sys

from _fram_chip_fake import FakeMB85RS64V

import asy_spi_driver
from asy_fram_manager import AsyFramManager
from asy_spi_driver import SPI
from print_log import PrintLogHistoryStore

# Same one-process-per-test-file swap as the other asy_fram_* test files - see their own comments.
asy_spi_driver._SPI = FakeMB85RS64V  # type: ignore[misc]

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")

# Measured 2026-09-18, mock tier, median of five, ~15% margin. Settrace build: 296,448 B blank /
# 234,592 B valid (was 820,096 / 564,960). Settrace-free: 28,864 / 20,512 (was 137,088 / 89,408)
# - that pair is the one whose ratios carry to the board.
_SETTRACE_BUILD = hasattr(sys, "settrace")
_BUDGET_BLANK = 344_000 if _SETTRACE_BUILD else 34_000
_BUDGET_VALID = 270_000 if _SETTRACE_BUILD else 24_000


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


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


async def _rig() -> "tuple[AsyFramManager, PrintLogHistoryStore]":
    bus = SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    manager = AsyFramManager(bus, 1, max_size=0x2000, debug=None)
    assert await manager.setup()
    return manager, PrintLogHistoryStore(manager, 10, None, name="BUDGET")


def test_blank_setup_stays_within_its_allocation_budget() -> None:
    # A blank chip: setup()'s _read() finds no valid copy, so _write() lays down both. 18 byte-level
    # commands over 74 CS cycles - the most expensive shape the boot batch ever asks for.
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


def test_the_budgets_are_not_trivially_satisfied() -> None:
    # A budget nothing could ever exceed would pass forever. These are set ~15% above a measured
    # run, so the pre-restructure cost (2.8x the blank budget, 2.4x the valid one) would fail them.
    assert (820_096 if _SETTRACE_BUILD else 137_088) > _BUDGET_BLANK
    assert (564_960 if _SETTRACE_BUILD else 89_408) > _BUDGET_VALID


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
