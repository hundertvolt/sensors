"""Isolated-driver device script, phase 1 of 2 (fram_error_log_reset_race_verify.py is phase 2): seeds a
nonce-chosen test-band history, then lands a real machine.reset() right after transfer SEAM of the next entry's chunk
write. Run through board.run_isolated_expect_reset(); it ends in the reset, so the verify phase clears the chunk."""

import asyncio

import machine

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
_LOG_NAME = "ERRRACE"
E_TEST_SEED_A = 125  # the first of the error catalog's test band 125-127; the nonce picks one of its 27 sequences
_SEED = [E_TEST_SEED_A + (BENCH["NONCE"] // 3**i) % 3 for i in range(3)]
_RACED = E_TEST_SEED_A + BENCH["NONCE"] % 3  # the fourth entry, whose chunk write the reset interrupts


async def _main() -> None:
    wdt = arm()
    chip = next(instance for instance in BENCH["instances"].values() if instance["driver"] == "fram")
    bus = BENCH["bus"][chip["bus"]]
    spi = asy_spi_driver.SPI(bus["id"], sck_pin=bus["sck_pin"], mosi_pin=bus["mosi_pin"], miso_pin=bus["miso_pin"])
    # The verify phase builds the same two objects in the same order, so both address the manager's first chunk.
    fram = FRAMManager(spi, chip["cs_pin"], BENCH["fram_max_size"])
    fact("setup", await fram.setup())
    store = make_logger(LogConfig(fram, _HISTORY_LENGTH, None), _LOG_NAME)
    await store.setup()
    fact("initialized", store.initialized)
    if not store.initialized:
        done()
        return
    # Cleared first: the chunk is the part's real storage, so setup() just restored whatever a previous run left.
    await store.reset()
    fact("baseline", (await store.get_log())[_LOG_NAME])
    for seed in _SEED:
        await store.err_s("seeded", errno=seed)
    fact("seeded", (await store.get_log())[_LOG_NAME])
    wdt.feed()
    transfers = [0]
    driver = fram.fram
    write_sync = driver.set_values_sync

    def counting(buf: "bytes | bytearray | memoryview", addr_start: int) -> int:
        # The chunk write's own transfers, counted on this script's driver instance: the reset lands right after SEAM.
        status = write_sync(buf, addr_start)
        transfers[0] += 1
        if transfers[0] == BENCH["SEAM"]:
            print("LANDED seam=" + str(BENCH["SEAM"]))
            machine.reset()
        return status

    driver.set_values_sync = counting  # type: ignore[method-assign]  # an instance attribute of this script's driver
    print("SEEDED")
    await store.err_s("raced", errno=_RACED)
    fact("not_reset_after_transfers", transfers[0])
    done()


asyncio.run(_main())
