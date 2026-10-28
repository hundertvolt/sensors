"""Isolated-driver device script: a ResetErrors landing before a FRAM-backed logger's own setup() has run still sticks
on the real part - the reset is persisted and the later setup() does not restore the old history over it
(SPECIFICATION.md Part C.7); the chunk is cleared after setup and again on the way out."""

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

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

_HISTORY_LENGTH = 10
# The error catalog's test band: alternating codes keep three slots, and no product code is ever seeded.
E_TEST_SEED_A = 125
E_TEST_SEED_B = 126
_SEEDS = [E_TEST_SEED_A, E_TEST_SEED_B, E_TEST_SEED_A]
_LOG_NAME = "ERRBOOT"


async def _main() -> None:
    arm()
    chip = next(instance for instance in BENCH["instances"].values() if instance["driver"] == "fram")
    bus = BENCH["bus"][chip["bus"]]
    spi = asy_spi_driver.SPI(bus["id"], sck_pin=bus["sck_pin"], mosi_pin=bus["mosi_pin"], miso_pin=bus["miso_pin"])
    fram = FRAMManager(spi, chip["cs_pin"], BENCH["fram_max_size"])
    fact("setup", await fram.setup())
    store = make_logger(LogConfig(fram, _HISTORY_LENGTH, None), _LOG_NAME)
    await store.setup()
    fact("initialized", store.initialized)
    if not store.initialized:
        done()
        return
    try:
        # Cleared at the start (a previous run's ring) and in the finally below (nothing seeded survives).
        await store.reset()
        for seed in _SEEDS:
            await store.err_s("seeded", errno=seed)
        fact("seeded_count", (await store.get_log())[_LOG_NAME]["ErrType"].count("E"))
        # The boot window: a fresh logger over the same chunk, its setup() not run yet, as the boot batch leaves it before
        # the server answers; make_logger() hands it back uninitialized, which is exactly that state.
        rebooted = make_logger(LogConfig(fram, _HISTORY_LENGTH, None), _LOG_NAME)
        await rebooted.reset()  # the PUT lands here
        fact("reset_persisted", rebooted.initialized)
        await rebooted.setup()  # ... and only now does its setup run
        fact("after", (await rebooted.get_log())[_LOG_NAME])
        # A third logger, no reset: the cleared state is what the part holds, not what the second object keeps in RAM.
        verify = make_logger(LogConfig(fram, _HISTORY_LENGTH, None), _LOG_NAME)
        await verify.setup()
        fact("persisted", (await verify.get_log())[_LOG_NAME])
    finally:
        fact("cleared_last", await store.reset())
    done()


asyncio.run(_main())
