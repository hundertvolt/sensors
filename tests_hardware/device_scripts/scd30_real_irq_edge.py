"""Isolated-driver device script for flash-tier candidate A.4: confirms a genuine real-hardware
rising edge on the SCD30's own RDY pin drives `SCD30_Reader`'s real IRQ-pin self-healing mechanism
end to end - the exact same code path `test_digital_twin_scd30.py`'s own
`test_rdy_pin_goes_high_on_new_reading_and_fires_a_registered_rising_edge_handler` exercises in
simulation, now on real silicon.

Correction, not a new finding (see this session's own conversation history): an earlier pass wrongly
concluded the real driver never wires a GPIO to the SCD30's own RDY pin, based on grepping for the
literal string "rdy" and finding nothing - the real mechanism is named `irq_pin`/`IRQ` throughout
`src/asy_scd30_driver.py`, not "rdy" (its own module docstring says so directly: "SCD30_Reader runs
the read loop plus an IRQ-pin self-healing trigger"), and a narrower-than-necessary grep, followed by
not reading the rest of the file, missed it entirely. The project owner caught this and pointed at
the real mechanism directly. Re-read in full this time: `SCD30_Reader.__init__`'s own `irq_pin: int`
constructor parameter (wired in production as `SCD30_Reader(i2c0, 8, ...)` - sensortask_wozi.py,
GPIO 8; this bench unit instead wires SCD30 to I2C1 with IRQ on GPIO11 - see the wiring note
below), `start_timer()`'s real `self.irq_pin.irq(trigger=IRQ_RISING, handler=...)`, and
`scd_init_irq()`'s own staged self-healing fallback (a 500ms software poll that manually fires the
same trigger event if the pin has been stuck HIGH for `trigger_half_sec` consecutive intervals - i.e.
if the real hardware IRQ was somehow missed) - both paths feed the exact same `irq_trigger_event`
that `read_loop()` waits on.

Design: constructs the reader with a deliberately generous `trigger_sec` (10s, so the self-healing
fallback's own worst-case latency is ~10s) and asserts a real reading arrives (via get_data(), not by
also awaiting irq_trigger_event directly - a second, competing waiter on the same ThreadSafeFlag
alongside read_loop()'s own would race for which task actually gets woken by set(), per
MicroPython's ThreadSafeFlag being a single-waiter primitive, not a broadcast event; observing the
real *effect* - a stored reading - sidesteps that race entirely) well inside that window (5s). The
SCD30's own real ~2s default measurement interval means a genuine hardware IRQ should fire long
before the software fallback ever would, so a fast observed response is strong evidence the real IRQ
path (not the fallback) actually drove it. This can't fully disambiguate the two paths from software
alone (both set the same event) - a scope on the IRQ pin itself would be the only fully certain
confirmation, out of this script's own reach; the timing margin here is the practical proxy.

Wiring note: this bench unit puts SCD30 on I2C1 (scl=15, sda=14) with IRQ/RDY on GPIO11, not
I2C0/GPIO8 as production wozi does (dev_legacy/README.md's own wiring table) - confirmed directly
against this bench's live main.py and a real i2c.scan(). An earlier version of this script used the
production pins and would have silently probed an empty bus on this specific unit.

Run via `mpremote run <this> soft-reset`. Prints "RESULT: PASS ..." or "RESULT: FAIL <reason>"."""

import asyncio
import time

import asy_i2c_driver
from asy_scd30_driver import SCD30_Reader

FAST_PATH_DEADLINE_S = 5.0  # comfortably above the SCD30's own ~2s natural interval + IRQ latency,
# comfortably below the self-healing fallback's own ~10s worst case (TRIGGER_SEC below).
TRIGGER_SEC = 10


async def _main() -> None:
    i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000, timeout=200000)
    reader = SCD30_Reader(i2c1, 11, trigger_sec=TRIGGER_SEC, max_module_error=999, fram=None, debug=None)
    reader.start_timer()  # wires the real GPIO IRQ (rising edge) + the 500ms self-healing poll timer

    read_task = asyncio.create_task(reader.read_loop())
    init_irq_task = asyncio.create_task(reader.scd_init_irq())

    start = time.ticks_ms()
    data = None
    deadline_ms = int(FAST_PATH_DEADLINE_S * 1000)
    while time.ticks_diff(time.ticks_ms(), start) < deadline_ms:
        data = await reader.get_data()
        if data.CO2 is not None:
            break
        await asyncio.sleep_ms(100)

    read_task.cancel()
    init_irq_task.cancel()
    for task in (read_task, init_irq_task):
        try:
            await task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001 - CancelledError (real hardware confirmed: MicroPython's, like CPython's, subclasses BaseException, not Exception - SPECIFICATION.md Part F.2) or whatever the loop itself raised, not this script's concern once we have our own answer above
            pass

    if data is not None and data.CO2 is not None:
        elapsed_s = time.ticks_diff(time.ticks_ms(), start) / 1000.0
        print(f"RESULT: PASS real reading arrived after {elapsed_s:.2f}s (self-heal fallback threshold was ~{TRIGGER_SEC}s)")
    else:
        print(f"RESULT: FAIL no reading arrived within {FAST_PATH_DEADLINE_S}s - neither the real IRQ nor the self-healing fallback appears to have driven a read")


asyncio.run(_main())
