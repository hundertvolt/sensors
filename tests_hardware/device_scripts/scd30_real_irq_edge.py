"""Isolated-driver device script: a rising edge on the SCD30's RDY pin drives SCD30_Reader's read through its IRQ
path on real silicon. Software cannot fully tell the real IRQ from the self-healing fallback - a scope on the pin is
the only certain check (E.6.6 row scd30-rdy-irq-vs-fallback). Reports facts; the host gives the verdict."""

import asyncio
import time

import asy_i2c_driver
from asy_scd30_driver import SCD30_Reader

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# Above the SCD30's own ~2 s interval plus the IRQ latency, below the self-healing fallback's ~10 s (_TRIGGER_S).
# @tunable l3.scd30_real_irq_edge_fast_path_deadline_s = 5.0
_FAST_PATH_DEADLINE_S = 5.0
_TRIGGER_S = 10
# @tunable l3.scd30_real_irq_edge_poll_ms = 100
_POLL_MS = 100


async def _main() -> None:
    wdt = arm()
    chip = BENCH["instances"]["scd30"]
    bus = BENCH["bus"][chip["bus"]]
    i2c = asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"], frequency=bus["frequency"], timeout=bus.get("timeout"))
    reader = SCD30_Reader(i2c, chip["irq_pin"], trigger_s=_TRIGGER_S, max_module_error=999)
    reader.start_timer()  # the real GPIO IRQ (rising edge) and the self-healing poll timer
    tasks = (reader.start_asy_read(), reader.start_asy_irq())
    deadline_ms = int(_FAST_PATH_DEADLINE_S * 1000)
    start = time.ticks_ms()
    co2 = None
    elapsed_ms = None
    while co2 is None and time.ticks_diff(time.ticks_ms(), start) < deadline_ms:
        co2 = (await reader.get_data()).CO2
        if co2 is not None:
            elapsed_ms = time.ticks_diff(time.ticks_ms(), start)
        await fed_sleep_ms(wdt, _POLL_MS)
    died = []
    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception as e:  # a task that died on its own is a fact the host fails on
            died.append(repr(e))
        await asyncio.sleep(0)
    reader.stop_timer()
    fact("co2", co2)
    fact("elapsed_ms", elapsed_ms)
    fact("deadline_ms", deadline_ms)
    fact("trigger_s", _TRIGGER_S)
    fact("died", died)
    done()


asyncio.run(_main())
