"""Isolated-driver device script: one real SCD30 reading through SCD30_Reader after the post-reset settle (tau63 above
10 s), reported for the host to check against plausibility_bounds.py. With BENCH["mode"] == "frc_window" it instead
runs the reader's FRC readiness accumulation over a synthetic 3600 s window, sending no SCD30 command."""

import asyncio

import asy_i2c_driver
from asy_scd30_driver import SCD30_Reader

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    import machine
    from _shared.facts import done, fact
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# @tunable l3.scd30_plausibility_read_settle_s = 45.0
_SETTLE_S = 45.0  # the datasheet's response time (tau63 above 10 s) plus margin
# @tunable l3.scd30_plausibility_read_step_s = 0.5
_STEP_S = 0.5
# @tunable l3.scd30_plausibility_read_poll_tries = 30
_POLL_TRIES = 30
_TRIGGER_S = 3
# The synthetic FRC window: FRCWindow's 3600 s maximum at the 2 s minimum interval, CO2 a fixed integer pattern
# (exact in float32, so only the accumulation can lose precision) around a constant temperature.
_FRC_INTERVAL_S = 2  # source: the SCD30's minimum interval (Interface Description 1.4.3)
_FRC_SAMPLES = 1800
_FRC_TEMPERATURE_C = 22.0


def _frc_co2(i: int) -> float:
    return 800.0 + (i * 7) % 21 - 10  # host test: the same series, summed in double precision


def _frc_window(reader: SCD30_Reader, wdt: "machine.WDT") -> None:
    # The reader's own accumulation (_frc_add()) and close (_frc_close()), no chip: the float32 sums and verdict out.
    for i in range(_FRC_SAMPLES):
        reader._frc_add(_frc_co2(i), _FRC_TEMPERATURE_C)
        if i % 100 == 0:
            wdt.feed()
    fact("frc_samples", reader._frc_n)
    fact("frc_sums", {"d": reader._frc_sum_d, "d2": reader._frc_sum_d2, "id": reader._frc_sum_id})
    fact("frc_thresholds", {"noise": reader._frc_noise, "rate": reader._frc_rate})
    fact("frc_verdict", reader._frc_close(_FRC_INTERVAL_S))
    fact("frc_interval_s", _FRC_INTERVAL_S)


async def _read(reader: SCD30_Reader, wdt: "machine.WDT") -> None:
    reader.start_timer()  # the real GPIO IRQ and the self-healing poll timer
    tasks = (reader.start_asy_read(), reader.start_asy_irq())
    await fed_sleep_ms(wdt, int(_SETTLE_S * 1000))  # readings inside the settle window are discarded on purpose
    data = await reader.get_data()  # the SCD30 namedtuple: CO2, Temp, Hum, WetBulb, DewPoint, FRCState, FRCWait, TS
    polls = 0
    while data.CO2 is None and polls < _POLL_TRIES:
        await fed_sleep_ms(wdt, int(_STEP_S * 1000))
        data = await reader.get_data()
        polls += 1
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
    fact("co2", data.CO2)
    fact("humidity", data.Hum)
    fact("temperature", data.Temp)
    fact("polls", polls)
    fact("died", died)


async def _main() -> None:
    wdt = arm()
    chip = BENCH["instances"]["scd30"]
    bus = BENCH["bus"][chip["bus"]]
    i2c = asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"], frequency=bus["frequency"], timeout=bus.get("timeout"))
    reader = SCD30_Reader(i2c, chip["irq_pin"], trigger_s=_TRIGGER_S, max_module_error=999)
    if BENCH.get("mode") == "frc_window":
        _frc_window(reader, wdt)
    else:
        await _read(reader, wdt)
    done()


asyncio.run(_main())
