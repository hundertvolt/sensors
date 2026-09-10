"""Isolated-driver device script: confirms a genuine rising edge on the SCD30's RDY pin drives
SCD30_Reader's IRQ-pin self-healing mechanism, on real silicon. Can't fully disambiguate a real IRQ
from the software fallback purely from software (a scope on the pin is the only certain check)."""

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
        except (asyncio.CancelledError, Exception):
            pass

    if data is not None and data.CO2 is not None:
        elapsed_s = time.ticks_diff(time.ticks_ms(), start) / 1000.0
        print(f"RESULT: PASS real reading arrived after {elapsed_s:.2f}s (self-heal fallback threshold was ~{TRIGGER_SEC}s)")
    else:
        print(f"RESULT: FAIL no reading arrived within {FAST_PATH_DEADLINE_S}s - neither the real IRQ nor the self-healing fallback appears to have driven a read")


asyncio.run(_main())
