"""Times one FRAM command and one log entry's whole chunk write, as its commands, on the real chip: the host checks the
command against one UART poll floor (SPECIFICATION.md J.6) and records the entry (F.3). Writes only inside its
declared scratch region, above every chunk; never calls get_chunk()."""

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
_ENTRY_PAYLOAD = 13  # a ten-slot history's block: its "<H" count, ten slots and CRC8; the status pair follows it


async def _main() -> None:
    arm()
    chip = next(instance for instance in BENCH["instances"].values() if instance["driver"] == "fram")
    bus = BENCH["bus"][chip["bus"]]
    spi = asy_spi_driver.SPI(bus["id"], sck_pin=bus["sck_pin"], mosi_pin=bus["mosi_pin"], miso_pin=bus["miso_pin"])
    fram = FRAMManager(spi, chip["cs_pin"], BENCH["fram_max_size"])
    await fram.setup()
    fact("setup", fram.initialized)
    driver = fram.fram
    one = bytearray(1)
    eight = bytearray(8)
    # (a) one command each, a plain call that never suspends.
    t0 = time.ticks_us()
    w_ok = driver.set_values(one, _SCRATCH_ADDR)
    t1 = time.ticks_us()
    r_ok = driver.get_values(eight, _SCRATCH_ADDR)
    t2 = time.ticks_us()
    fact("command_ok", w_ok and r_ok)
    # (b) a log entry's chunk write as its 51 commands: block 1's status pair read, then per block each status byte, the
    # payload, each status byte again.
    pair, payload = bytearray(2), bytearray(_ENTRY_PAYLOAD)
    second = _SCRATCH_ADDR + _ENTRY_PAYLOAD + len(pair)
    t3 = time.ticks_us()
    ok = driver.get_values(pair, second + _ENTRY_PAYLOAD)
    for base in (_SCRATCH_ADDR, second):
        status = base + _ENTRY_PAYLOAD
        ok = driver.set_values(one, status) and driver.set_values(one, status + 1) and driver.set_values(payload, base) and ok
        ok = driver.set_values(one, status) and driver.set_values(one, status + 1) and ok
    entry_us = time.ticks_diff(time.ticks_us(), t3)
    fact("entry_ok", ok)
    fact("write_us", time.ticks_diff(t1, t0))
    fact("read_us", time.ticks_diff(t2, t1))
    fact("entry_us", entry_us)
    fact("uart_floor_us", _UART_FLOOR_US)
    done()


asyncio.run(_main())
