"""Isolated-driver device script: PrintLogHistoryStore (asy_print_log.py), the FRAM-backed error history every
chunk-owning module uses, on the real part: one entry recorded, a fresh boot simulated by a new FRAMManager, the
history read back; the chunk is cleared after setup and again on the way out, so no seeded entry survives."""

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

_HISTORY_LENGTH = 5
E_TEST_SEED_A = 125  # the error catalog's test band, never a product code
_LOG_NAME = "TEST"


async def _main() -> None:
    arm()
    chip = next(instance for instance in BENCH["instances"].values() if instance["driver"] == "fram")
    bus = BENCH["bus"][chip["bus"]]
    spi = asy_spi_driver.SPI(bus["id"], sck_pin=bus["sck_pin"], mosi_pin=bus["mosi_pin"], miso_pin=bus["miso_pin"])
    fram_a = FRAMManager(spi, chip["cs_pin"], BENCH["fram_max_size"])
    fact("setup", await fram_a.setup())
    pr1 = make_logger(LogConfig(fram_a, _HISTORY_LENGTH, None), _LOG_NAME)
    await pr1.setup()
    fact("initialized", pr1.initialized)
    if not pr1.initialized:
        done()
        return
    # A fresh boot: a new FRAMManager over the same part allocates its first chunk at the address pr1's took.
    fram_b = FRAMManager(spi, chip["cs_pin"], BENCH["fram_max_size"])
    pr2 = make_logger(LogConfig(fram_b, _HISTORY_LENGTH, None), _LOG_NAME)
    try:
        fact("cleared_first", await pr1.reset())
        await pr1.err_s("test error for fram_error_log_roundtrip.py", errno=E_TEST_SEED_A)
        fact("rebooted_setup", await fram_b.setup())
        await pr2.setup()
        fact("restored", pr2.initialized)
        entry = (await pr2.get_log())[_LOG_NAME]  # ErrEntry types its three fields exactly
        fact("err_count", entry["ErrCount"])
        fact("err_num", entry["ErrNum"])
        fact("err_type", entry["ErrType"])
    finally:
        fact("cleared_last", await pr2.reset())
    fact("seed", E_TEST_SEED_A)
    done()


asyncio.run(_main())
