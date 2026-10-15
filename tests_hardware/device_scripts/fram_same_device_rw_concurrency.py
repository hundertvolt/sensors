"""Isolated-driver device script: FRAM's same-device "ongoing read, incoming write" proof (SPECIFICATION.md Part C.8):
repeated reads of production bytes (an evidence region, read only) while a write lands in a scratch region. FRAM has
no write wear (10^13 operations per byte, datasheets/); reports facts, the host gives the verdict."""

import asyncio

import asy_spi_driver
from asy_fram_driver import FRAM_SPI
from asy_print_log import PrintLogHistory

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import _ERRORS_KEPT, done, errors, fact
    from _shared.watchdog import arm
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# Read only, after the session saved the raw FRAM; the write lands in a scratch region the guard keeps disjoint.
_EVIDENCE_REGIONS = ((0x0000, 32),)
_SCRATCH_REGIONS = ((0x8000, 32),)
_READ_REGION = _EVIDENCE_REGIONS[0]
_WRITE_REGION = _SCRATCH_REGIONS[0]
_WRITE_PATTERN = bytes((32 - i) & 0xFF for i in range(_WRITE_REGION[1]))

# @tunable l3.fram_same_device_rw_concurrency_read_iterations = 30
_READ_ITERATIONS = 30
# @tunable l3.fram_same_device_rw_concurrency_run_bound_s = 60.0
_RUN_BOUND_S = 60.0


async def _main() -> None:
    wdt = arm()
    chip = BENCH["instances"]["fram"]
    bus = BENCH["bus"][chip["bus"]]
    spi = asy_spi_driver.SPI(bus["id"], sck_pin=bus["sck_pin"], mosi_pin=bus["mosi_pin"], miso_pin=bus["miso_pin"])
    fram = FRAM_SPI(spi, chip["cs_pin"], logger=PrintLogHistory(name="FRAMCONCUR"), max_size=BENCH["fram_max_size"])
    await fram.setup()
    fact("initialized", fram.initialized)
    if not fram.initialized:
        done()
        return
    baseline = bytearray(_READ_REGION[1])
    async with fram:
        fact("baseline_read", await fram.get_values(baseline, addr_start=_READ_REGION[0]))
    failures: list[str] = []
    counts = {"reads_ok": 0, "reads_torn": 0}

    async def reader() -> None:
        buf = bytearray(_READ_REGION[1])
        for i in range(_READ_ITERATIONS):
            async with fram:
                ok = await fram.get_values(buf, addr_start=_READ_REGION[0])
            if ok and buf == baseline:
                counts["reads_ok"] += 1
            else:
                counts["reads_torn"] += 1
                if len(failures) < _ERRORS_KEPT:
                    failures.append(f"read {i}: ok={ok} got={bytes(buf).hex()}")
            wdt.feed()
            await asyncio.sleep(0)

    async def writer() -> None:
        await asyncio.sleep(0)  # the reader takes the first turn
        async with fram:
            fact("write_ok", await fram.set_values(_WRITE_PATTERN, addr_start=_WRITE_REGION[0]))

    await asyncio.wait_for(asyncio.gather(reader(), writer()), _RUN_BOUND_S)
    readback = bytearray(_WRITE_REGION[1])
    async with fram:
        ok = await fram.get_values(readback, addr_start=_WRITE_REGION[0])
    fact("write_readback_ok", ok and readback == _WRITE_PATTERN)
    fact("reads_ok", counts["reads_ok"])
    fact("reads_torn", counts["reads_torn"])
    fact("reads_planned", _READ_ITERATIONS)
    errors("errors", counts["reads_torn"], failures)
    done()


asyncio.run(_main())
