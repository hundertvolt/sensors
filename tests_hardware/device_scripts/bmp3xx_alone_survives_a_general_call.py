"""Isolated-driver device script: a lone BMP3xx keeps its state through I2C general-call resets - distinctive volatile
settings, then a range-checked reader racing a broadcaster that sends 0x06 to address 0x00 under the bus lock; the
configuration, chip ID, power-control bits and power-on flag compared before and after. Reports facts only."""

import asyncio

import asy_i2c_driver
from asy_bmp3xx_driver import BMP3XX_I2C

# @include _shared/facts.py
# @include _shared/watchdog.py
# @include _shared/bus_reader_loops.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.bus_reader_loops import Record, Stop, outside, read_loop, report_errors
    from _shared.facts import done, fact
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

_GENERAL_CALL = (0x00, b"\x06")  # I2C-bus specification 3.1.13: the general call and its reset second byte
_DISTINCT = (8, 2, 3)  # pressure OSR, temperature OSR, IIR coefficient: none of them a post-reset default
# @tunable l3.bmp3xx_alone_survives_a_general_call_broadcasts = 10
_BROADCASTS = 10
# @tunable l3.bmp3xx_alone_survives_a_general_call_broadcast_step_ms = 200
_BROADCAST_STEP_MS = 200
# @tunable l3.bmp3xx_alone_survives_a_general_call_run_bound_s = 60.0
_RUN_BOUND_S = 60.0


async def _state(bmp: BMP3XX_I2C) -> "dict[str, object]":
    # The configuration snapshot, the chip ID (datasheet sec 4.3.1, register 0x00) and PWR_CTRL (sec 4.3.16, 0x1B).
    return {"snapshot": list(await bmp.get_config_snapshot()), "chip_id": await bmp._read_byte(0x00), "pwr_ctrl": await bmp._read_byte(0x1B)}


async def _main() -> None:
    wdt = arm()
    bus = BENCH["bus"][BENCH["instances"]["bmp3xx"]["bus"]]
    i2c = asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"], frequency=bus["frequency"], timeout=bus.get("timeout"))
    fact("devices_on_bus", i2c.scan())
    bmp = BMP3XX_I2C(i2c, BENCH["addresses"]["bmp3xx"])
    await bmp.setup()
    try:
        await bmp.set_pressure_oversampling(_DISTINCT[0])
        await bmp.set_temperature_oversampling(_DISTINCT[1])
        await bmp.set_filter_coefficient(_DISTINCT[2])
        await bmp.take_por_detected()  # cleared: a later True is a reset this script did not make
        fact("before", await _state(bmp))

        async def read() -> "str | None":
            pressure, temperature = await bmp.get_pressure_and_temperature()
            return outside(BENCH["bounds"], "pressure_hpa", pressure) or outside(BENCH["bounds"], "bmp3xx_temp_c", temperature)

        reader_rec, stop = Record("bmp3xx"), Stop()
        general_call = asy_i2c_driver.I2CDevice(i2c, _GENERAL_CALL[0])
        sent = {"broadcasts": 0, "naks": 0}

        async def broadcaster() -> None:
            for _ in range(_BROADCASTS):
                sent["broadcasts"] += 1  # on the wire whether or not a device acknowledges it
                try:
                    async with general_call:
                        await general_call.write(_GENERAL_CALL[1])
                except OSError:  # nobody acknowledged the general call: counted, not a failure
                    sent["naks"] += 1
                await fed_sleep_ms(wdt, _BROADCAST_STEP_MS)
            stop.is_set = True

        await asyncio.wait_for(asyncio.gather(read_loop(read, None, 0, wdt, reader_rec, stop), broadcaster()), _RUN_BOUND_S)
        fact("broadcasts", sent["broadcasts"])
        fact("naks", sent["naks"])
        fact("broadcasts_planned", _BROADCASTS)
        fact("reads", reader_rec.reads)
        fact("after", await _state(bmp))
        fact("distinct", list(_DISTINCT))
        fact("por_after", await bmp.take_por_detected())
        report_errors([reader_rec])
    finally:
        # The soft reset leaves the post-reset defaults (OSR x1, x1, IIR 0), which are the driver schema's defaults.
        await bmp.reset()
    done()


asyncio.run(_main())
