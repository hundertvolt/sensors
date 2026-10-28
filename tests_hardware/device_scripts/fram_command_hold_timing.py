"""Times one FRAM command envelope and one block operation on the real chip, bus held: the host checks the longest
non-yielding stretch against one UART poll floor (SPECIFICATION.md J.6) and the block hold against its budget. Writes
only inside its declared scratch region, above every chunk; never calls get_chunk()."""

import asyncio
import time

import asy_spi_driver
from asy_fram_manager import FRAMManager

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

_SCRATCH_REGIONS = ((BENCH["fram_max_size"] - 0x100, 0x100),)  # the part's top 256 B, above every chunk
_SCRATCH_ADDR = _SCRATCH_REGIONS[0][0]
_UART_FLOOR_US = 80 * 10 * 1_000_000 // 115_200  # 80 B of 8N1 at 115200 baud (J.6): 6,944 us
# @tunable l3.fram_command_hold_block_budget_us = 25000
_BLOCK_HOLD_BUDGET_US = 25000  # SPECIFICATION.md F.3's hold.fram_block row: the measured 18,089-23,148 us (F.5.8) plus 8 %
_BLOCK_COMMANDS = 4  # a block operation's own command count


async def _main() -> None:
    arm()
    chip = next(instance for instance in BENCH["instances"].values() if instance["driver"] == "fram")
    bus = BENCH["bus"][chip["bus"]]
    spi = asy_spi_driver.SPI(bus["id"], sck_pin=bus["sck_pin"], mosi_pin=bus["mosi_pin"], miso_pin=bus["miso_pin"])
    fram = FRAMManager(spi, chip["cs_pin"], BENCH["fram_max_size"])
    fact("setup", await fram.setup())
    driver = fram.fram
    one = bytearray(1)
    eight = bytearray(8)
    # (a) the synchronous, non-yielding stretches, bus already held.
    async with driver:
        t0 = time.ticks_us()
        w_status = driver.set_values_sync(one, _SCRATCH_ADDR)
        t1 = time.ticks_us()
        r_status = driver.get_values_sync(eight, _SCRATCH_ADDR)
        t2 = time.ticks_us()
    fact("command_ok", await driver.report_set_values(w_status) and await driver.report_get_values(r_status))
    # (b) the bus-lock hold: entry to exit, yields inside it included; every status is judged.
    w_status = r_status = 0
    t3 = time.ticks_us()
    async with driver:
        for _ in range(_BLOCK_COMMANDS):
            w_status |= driver.set_values_sync(one, _SCRATCH_ADDR)
            await asyncio.sleep(0)
            r_status |= driver.get_values_sync(eight, _SCRATCH_ADDR)
            await asyncio.sleep(0)
    hold_us = time.ticks_diff(time.ticks_us(), t3)
    fact("block_ok", await driver.report_set_values(w_status) and await driver.report_get_values(r_status))
    fact("write_us", time.ticks_diff(t1, t0))
    fact("read_us", time.ticks_diff(t2, t1))
    fact("hold_us", hold_us)
    fact("uart_floor_us", _UART_FLOOR_US)
    fact("block_hold_budget_us", _BLOCK_HOLD_BUDGET_US)
    done()


asyncio.run(_main())
