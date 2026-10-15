"""Isolated-driver device script, phase 2 of 2: after the reset fram_error_log_reset_race_seed_and_race.py landed
mid-write, reports the restored history (the host accepts only empty, the seeded sequence, or it plus the raced entry),
writes one new entry, and clears the chunk on the way out so no seeded history survives the pair."""

import asyncio

import asy_spi_driver
from asy_fram_manager import FRAMManager
from asy_print_log import LogConfig, make_logger

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact
    from _shared.watchdog import arm
    from bench_facts import BenchFacts

    from asy_print_log import ErrEntry

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

_HISTORY_LENGTH = 10
_LOG_NAME = "ERRRACE"
E_TEST_SEED_C = 127  # the post-recovery entry, from the error catalog's test band


def _errors(entry: "ErrEntry") -> "list[int]":
    nums, types = entry["ErrNum"], entry["ErrType"]
    return [nums[i] for i in range(len(types)) if types[i] == "E"]


async def _main() -> None:
    arm()
    chip = next(instance for instance in BENCH["instances"].values() if instance["driver"] == "fram")
    bus = BENCH["bus"][chip["bus"]]
    spi = asy_spi_driver.SPI(bus["id"], sck_pin=bus["sck_pin"], mosi_pin=bus["mosi_pin"], miso_pin=bus["miso_pin"])
    # The seed phase's two objects in the same order, so this addresses the same chunk.
    fram = FRAMManager(spi, chip["cs_pin"], BENCH["fram_max_size"])
    fact("setup", await fram.setup())
    # Not cleared first: what the raced reset left behind is the thing under test; the chunk is cleared last instead.
    store = make_logger(LogConfig(fram, _HISTORY_LENGTH, None), _LOG_NAME)
    try:
        await store.setup()
        fact("initialized", store.initialized)
        entry = (await store.get_log())[_LOG_NAME]
        fact("recovered", _errors(entry))
        fact("warnings", len([t for t in entry["ErrType"] if t == "W"]))
        fact("err_count", entry["ErrCount"])
        # The chunk takes a fresh entry afterwards: a reset-wedged chunk unreadable for good would be a defect.
        await store.err_s("post-recovery", errno=E_TEST_SEED_C)
        fact("tail", _errors((await store.get_log())[_LOG_NAME]))
    finally:
        fact("cleared_last", await store.reset())
    done()


asyncio.run(_main())
