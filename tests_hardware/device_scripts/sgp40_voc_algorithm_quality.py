"""Isolated-driver device script: real SGP40 raw readings driven through the real voc_algorithm.py end to end, sampled
after the algorithm's blackout - VOC, raw and the largest single-step jump reported for the host to check against
plausibility_bounds.py and a stability bound. A sanity check, not an accuracy claim."""

import asyncio

import asy_i2c_driver
from asy_base_classes import ValueRef
from asy_sgp40_driver import SGP40_Reader

# @include _shared/facts.py
# @include _shared/watchdog.py
# @include _shared/fixed_source.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact
    from _shared.fixed_source import FixedSource
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# The 45 s documented blackout plus margin for the real 1 s read loop to catch up.
# @tunable l3.sgp40_voc_algorithm_quality_blackout_wait_s = 60.0
_BLACKOUT_WAIT_S = 60.0
_N_QUALITY_SAMPLES = 8
# @tunable l3.sgp40_voc_algorithm_quality_sample_interval_s = 2.0
_SAMPLE_INTERVAL_S = 2.0
# Generous against the algorithm's own adaptive low-pass smoothing.
# @tunable l3.sgp40_voc_algorithm_quality_max_single_step_jump = 300
_MAX_SINGLE_STEP_JUMP = 300
# The compensation the datasheet's Table 10 defaults to: fixed, not sensor-derived (SPECIFICATION.md Part L.6.3).
_COMPENSATION = (25.0, 50.0)


async def _main() -> None:
    wdt = arm()
    bus = BENCH["bus"][BENCH["instances"]["sgp40"]["bus"]]
    i2c = asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"], frequency=bus["frequency"], timeout=bus.get("timeout"))
    temperature, humidity = (ValueRef(FixedSource(value), "value") for value in _COMPENSATION)
    reader = SGP40_Reader(i2c, temperature, humidity, max_module_error=999)
    reader.start_timer()  # the algorithm's own fixed 1 s sampling period
    read_task = reader.start_asy_read()
    await fed_sleep_ms(wdt, int(_BLACKOUT_WAIT_S * 1000))
    samples = []
    for _ in range(_N_QUALITY_SAMPLES):
        data = await reader.get_data()
        samples.append([data.VOC, data.Raw])
        await fed_sleep_ms(wdt, int(_SAMPLE_INTERVAL_S * 1000))
    read_task.cancel()
    died = None
    try:
        await read_task
    except asyncio.CancelledError:
        pass
    except Exception as e:  # a read task that died on its own is a fact the host fails on
        died = repr(e)
    reader.stop_timer()
    voc = [v for v, _raw in samples if v is not None]
    fact("samples", samples)
    fact("max_step_jump", max((abs(b - a) for a, b in zip(voc, voc[1:])), default=0))  # noqa: B905 - MicroPython zip() takes no strict=
    fact("max_step_jump_bound", _MAX_SINGLE_STEP_JUMP)
    fact("blackout_s", _BLACKOUT_WAIT_S)
    fact("died", died)
    done()


asyncio.run(_main())
