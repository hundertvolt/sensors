"""Isolated-driver device script, flash-tier: real-hardware regression test for the SGP40 general-
call reset hazard found while auditing SPECIFICATION.md Part C.8's locking model (see this session's
own bus-hazard report). SGP40_I2C._reset() (src/asy_sgp40_driver.py) sends `i2c.i2c.writeto(0x00,
b"\\x06")` - a genuine I2C general-call broadcast to the reserved address 0x00, which the SGP40
datasheet (datasheets/sgp40/Sensirion_Gas_Sensors_Datasheet_SGP40.pdf, Table 17, p.14) documents as
"resetting all devices connected to the same I2C bus". This fires on every SGP40 task-supervisor
restart during normal running operation (SGP40_Reader.read_loop() -> _init_sgp() -> setup() ->
initialize() -> _reset(), and system_service.py's start_and_check_tasks() restarts any task that
returns), not just at cold boot - so a sibling device on the same bus could in principle be disrupted
mid-transaction by a broadcast neither our software locking model nor the sibling's own firmware is
guaranteed to know about.

De-risking already done by reading the actual datasheets (not memory/web search, per CLAUDE.md):
neither the SCD30 Interface Description/Datasheet nor the BMP388/BMP384 datasheets document any
general-call/broadcast-address listening behavior - both sensors' only documented reset mechanisms
are addressed commands to their own I2C address. This script is the real-hardware confirmation of
that datasheet-based prediction, for the pairing this dev bench's own bench-tested wiring actually
puts on one shared bus: SCD30 + SGP40 on I2C1 (sensortask_dev.py's own wiring comment - NOT the same
pairing as production wozi, which puts SGP40 + BMP3xx together instead; see this session's Part 1
report for the full wiring-divergence finding and why both pairings independently check out against
their respective datasheets).

Mechanism: one coroutine continuously runs SCD30 read_measurement() cycles (CRC-8 protected -
corruption from an ill-timed broadcast landing mid-sequence would very likely trip a CRC failure or
bus NAK, not silently succeed) while a second coroutine repeatedly drives SGP40 through its real
production reset path (initialize(), which ends with _reset()'s own general-call broadcast) at the
same time. If SCD30 secretly does honor the general call (undocumented), continuous measurement
would be wiped mid-run and reads would start failing/going stale; if the broadcast's own bus-level
electrical transition corrupts an in-flight SCD30 transaction's timing, CRC failures or OSErrors
would surface directly. Zero errors and every reading staying within plausible bounds throughout
(including immediately after each broadcast) is the proof this hazard is not live on this bus.

Run via `mpremote run <this> soft-reset`."""

import asyncio

import machine

import asy_i2c_driver
from asy_scd30_driver import SCD30_I2C
from asy_sgp40_driver import SGP40_I2C

CO2_MIN_PPM, CO2_MAX_PPM = 200, 10_000
HUMIDITY_MIN_RH, HUMIDITY_MAX_RH = 0.0, 100.0
TEMP_MIN_C, TEMP_MAX_C = -40.0, 70.0

SGP40_RESET_CYCLES = 8


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)
    i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000, timeout=200000)
    scd = SCD30_I2C(i2c1)
    sgp = SGP40_I2C(i2c1)
    await scd.setup()
    # Deliberately never calls set_ambient_pressure() here - see
    # scd30_same_device_rw_concurrency.py's own docstring for the one NVM-persisted write this
    # whole test group makes, exactly once per session, via tests_hardware/flash/conftest.py's
    # scd30_continuous_measurement_triggered fixture (which this test depends on).
    await sgp.setup()

    scd_errors = []
    scd_completed = 0
    distinct_co2_values = set()
    stop = False

    async def scd_loop() -> None:
        nonlocal scd_completed
        i = 0
        while not stop:
            try:
                await scd.read_measurement()
                co2 = await scd.get_CO2()
                hum = await scd.get_relative_humidity()
                temp = await scd.get_temperature()
                if co2 is not None:
                    if not (CO2_MIN_PPM <= co2 <= CO2_MAX_PPM):
                        scd_errors.append(f"iter {i}: CO2={co2!r} outside plausible bounds")
                    distinct_co2_values.add(co2)
                if hum is not None and not (HUMIDITY_MIN_RH <= hum <= HUMIDITY_MAX_RH):
                    scd_errors.append(f"iter {i}: Hum={hum!r} outside plausible bounds")
                if temp is not None and not (TEMP_MIN_C <= temp <= TEMP_MAX_C):
                    scd_errors.append(f"iter {i}: Temp={temp!r} outside plausible bounds")
            except Exception as e:  # noqa: BLE001 - any exception is itself the corruption signal this script exists to catch
                scd_errors.append(f"iter {i}: {type(e).__name__}: {e}")
            scd_completed += 1
            i += 1
            if i % 10 == 0:
                wdt.feed()

    sgp_errors = []
    sgp_completed = 0

    async def sgp_reset_loop() -> None:
        nonlocal stop, sgp_completed
        for i in range(SGP40_RESET_CYCLES):
            try:
                await sgp.initialize()  # real production path: ends with _reset()'s general-call broadcast
                sgp_completed += 1
            except Exception as e:  # noqa: BLE001 - SGP40's own init failing is worth surfacing too, though not this script's main question
                sgp_errors.append(f"iter {i}: {type(e).__name__}: {e}")
            wdt.feed()
        stop = True

    await asyncio.wait_for(asyncio.gather(scd_loop(), sgp_reset_loop()), 90.0)

    failures = []
    if sgp_completed != SGP40_RESET_CYCLES:
        failures.append(f"SGP40 only completed {sgp_completed}/{SGP40_RESET_CYCLES} reset cycles: {'; '.join(sgp_errors[:5])}")
    if scd_completed == 0:
        failures.append("SCD30 completed zero read cycles during the whole run - loop never progressed")
    failures.extend(scd_errors[:10])
    # The run spans ~8 SGP40 reset cycles (~1.5s each, ~12s+ total) - several times the SCD30's own
    # ~2s default measurement interval, so continuous measurement genuinely advancing should produce
    # at least a couple of distinct CO2 values (real sensor noise alone almost guarantees more than
    # one even in a perfectly stable room). A single unchanging value for the whole run is the
    # concrete signal that continuous measurement silently stopped advancing - e.g. because the
    # general-call broadcast actually did reset SCD30's continuous-measurement state, undocumented -
    # not proven by a CRC failure (that only catches the broadcast corrupting a transaction already
    # in flight, not a clean-looking reset landing between transactions).
    if len(distinct_co2_values) < 2:
        failures.append(
            f"only {len(distinct_co2_values)} distinct CO2 value(s) seen across {scd_completed} reads over "
            f"{sgp_completed} SGP40 reset cycles - continuous measurement may have silently stopped advancing"
        )

    if failures:
        print(f"RESULT: FAIL {'; '.join(failures)}")
    else:
        print(
            f"RESULT: PASS scd30_reads={scd_completed} sgp40_reset_cycles={sgp_completed} "
            f"distinct_co2_values={len(distinct_co2_values)} - zero corruption/errors, measurement kept advancing"
        )


asyncio.run(_main())
