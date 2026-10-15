"""Isolated-driver device script: the BMP3xx same-device proof - an ongoing read against an incoming OSR write, then the
reset rung (soft reset and the stored OSR re-applied) while the reader runs (SPECIFICATION.md Part C.8). The OSR and
CONFIG registers are volatile, so this writes freely; reports facts, the host gives the verdict."""

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
    from _shared.bus_reader_loops import Record, Stop, read_loop, report_errors
    from _shared.facts import done, fact
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

_OSR_SETTINGS = (1, 2, 4, 8, 16, 32)  # the OSR encodings, datasheet sec 4.3.17
# @tunable l3.bmp3xx_same_device_rw_concurrency_read_iterations = 20
_READ_ITERATIONS = 20
# @tunable l3.bmp3xx_same_device_rw_concurrency_write_iterations = 6
_WRITE_ITERATIONS = 6
# @tunable l3.bmp3xx_same_device_rw_concurrency_write_spread_s = 0.05
_WRITE_SPREAD_S = 0.05
# @tunable l3.bmp3xx_same_device_rw_concurrency_run_bound_s = 60.0
_RUN_BOUND_S = 60.0
# The reset rung's reads run this long on each side of the reset.
# @tunable l3.bmp3xx_same_device_rw_concurrency_rung_margin_ms = 100
_RUNG_MARGIN_MS = 100
# The OSR the reset rung re-applies, distinct from the post-reset default x1 so a lost re-apply shows.
_CONFIGURED_OSR = 8


async def _main() -> None:
    wdt = arm()
    chip = BENCH["instances"]["bmp3xx"]
    bus = BENCH["bus"][chip["bus"]]
    i2c = asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"], frequency=bus["frequency"], timeout=bus.get("timeout"))
    bmp = BMP3XX_I2C(i2c, BENCH["addresses"]["bmp3xx"])
    await bmp.setup()
    p_low, p_high, _ = BENCH["bounds"]["pressure_hpa"]
    t_low, t_high, _ = BENCH["bounds"]["bmp3xx_temp_c"]
    clean_failures = [0]

    async def read_checked() -> "str | None":
        pressure, temperature = await bmp.get_pressure_and_temperature()
        if not (p_low <= pressure <= p_high and t_low <= temperature <= t_high):
            return f"wrong value: {pressure} hPa, {temperature} C"
        return None

    async def read_in_reset_window() -> "str | None":
        # A read the reset lands in may fail cleanly (counted); only a wrong value is a failure.
        try:
            return await read_checked()
        except (OSError, RuntimeError, ValueError):
            clean_failures[0] += 1
            return None

    reader_rec, write_rec = Record("bmp3xx_reader"), Record("bmp3xx_writer")

    async def writer() -> None:
        for i in range(_WRITE_ITERATIONS):
            await asyncio.sleep(_WRITE_SPREAD_S)  # spread the writes across the reader's run
            oversample = _OSR_SETTINGS[i % len(_OSR_SETTINGS)]
            try:
                await bmp.set_pressure_oversampling(oversample)
                readback = await bmp.get_pressure_oversampling()
            except (OSError, RuntimeError, ValueError) as e:
                write_rec.fail(f"write {i}: {e!r}")
                continue
            if readback == oversample:
                write_rec.reads += 1
            else:
                write_rec.fail(f"write {i}: wrote x{oversample}, read back x{readback} - a torn write")

    await asyncio.wait_for(asyncio.gather(read_loop(read_checked, _READ_ITERATIONS, 0, wdt, reader_rec, Stop()), writer()), _RUN_BOUND_S)
    fact("reads", reader_rec.reads)
    fact("reads_planned", _READ_ITERATIONS)
    fact("writes_ok", write_rec.reads)
    fact("writes_planned", _WRITE_ITERATIONS)

    # The reset rung: soft reset (all config back to defaults) and the stored OSR re-applied, among the reads.
    await bmp.set_pressure_oversampling(_CONFIGURED_OSR)
    reset_rec = Record("bmp3xx_reset_window")
    stop = Stop()

    async def reset_rung() -> None:
        await fed_sleep_ms(wdt, _RUNG_MARGIN_MS)
        try:
            await bmp.reset()
            await bmp.set_pressure_oversampling(_CONFIGURED_OSR)
        except (OSError, RuntimeError, ValueError) as e:
            reset_rec.fail(f"reset and re-apply: {e!r}")
        await fed_sleep_ms(wdt, _RUNG_MARGIN_MS)
        stop.is_set = True

    await asyncio.wait_for(asyncio.gather(read_loop(read_in_reset_window, None, 0, wdt, reset_rec, stop), reset_rung()), _RUN_BOUND_S)
    fact("reset_window_failures", clean_failures[0])
    fact("reset_window_reads", reset_rec.reads)
    post = Record("bmp3xx_after_reset")
    await read_loop(read_checked, 1, 0, wdt, post, Stop())
    fact("post_reset_valid", post.reads == 1)
    fact("osr_after", await bmp.get_pressure_oversampling())
    fact("osr_configured", _CONFIGURED_OSR)
    await bmp.set_pressure_oversampling(_OSR_SETTINGS[0])  # the post-reset default x1: volatile, but left clean
    report_errors([reader_rec, write_rec, reset_rec, post])
    done()


asyncio.run(_main())
