"""Isolated-driver device script, flash-tier: proves the SCD30 device-session lock
(SCD30_DeviceSession, src/asy_scd30_driver.py) actually serializes two concurrent multi-transaction
sequences against the SAME device, so they can't interleave and corrupt each other - the real-
hardware counterpart to SPECIFICATION.md Part C.8's documented model, closing the gap that the
mock-level tests (tests/test_asy_i2c_driver.py's "asyncio interlock" section) only ever exercise the
raw bus lock with a synthetic instrumented counter, never a real device's own CRC-8-protected wire
protocol under genuine concurrent access.

Two coroutines run concurrently against one SCD30_I2C instance for a fixed iteration count each:
  - reader: repeated read_measurement() (a 2-3 step sequence: data-ready poll, optionally a command
    write, optionally an 18-byte CRC-8 checked burst read - see asy_scd30_driver.py's own comments).
  - snapshotter: repeated get_config_snapshot() (5 separate CRC-8 checked register reads held under
    one device-session lock, per its own torn-read-closing docstring).
Both paths are CRC-8 protected (crc_checks.py) - if the device-session lock didn't actually
serialize these two sequences, an interleaved write/read from the other coroutine landing mid-
sequence would very likely scramble the register-address/response byte framing and trip a CRC
failure (RuntimeError) or a bus NAK (OSError), not silently succeed. Zero exceptions and every
reading staying within datasheet-plausible bounds (same bounds as scd30_plausibility_read.py) is the
proof of no corruption. Read-only throughout - no persisted config is mutated, no restore needed.

This bench unit wires SCD30 to I2C1 (scl=15, sda=14) - see scd30_plausibility_read.py's own
docstring for the real i2c.scan() confirmation this was checked against.

Run via `mpremote run <this> soft-reset`."""

import asyncio

import machine

import asy_i2c_driver
from asy_scd30_driver import SCD30_I2C

CO2_MIN_PPM, CO2_MAX_PPM = 200, 10_000
HUMIDITY_MIN_RH, HUMIDITY_MAX_RH = 0.0, 100.0
TEMP_MIN_C, TEMP_MAX_C = -40.0, 70.0

READER_ITERATIONS = 120
SNAPSHOTTER_ITERATIONS = 40


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)  # matches src/system_service.py's own production value
    i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000, timeout=200000)
    scd = SCD30_I2C(i2c1)
    await scd.setup()
    await scd.set_ambient_pressure(1013)  # 0x0010 doubles as "trigger continuous measurement"

    reader_errors = []
    reader_completed = 0
    snapshot_errors = []
    snapshot_completed = 0

    async def reader() -> None:
        nonlocal reader_completed
        for i in range(READER_ITERATIONS):
            try:
                await scd.read_measurement()
                co2 = await scd.get_CO2()
                hum = await scd.get_relative_humidity()
                temp = await scd.get_temperature()
                if co2 is not None and not (CO2_MIN_PPM <= co2 <= CO2_MAX_PPM):
                    reader_errors.append(f"iter {i}: CO2={co2!r} outside plausible bounds")
                if hum is not None and not (HUMIDITY_MIN_RH <= hum <= HUMIDITY_MAX_RH):
                    reader_errors.append(f"iter {i}: Hum={hum!r} outside plausible bounds")
                if temp is not None and not (TEMP_MIN_C <= temp <= TEMP_MAX_C):
                    reader_errors.append(f"iter {i}: Temp={temp!r} outside plausible bounds")
            except Exception as e:  # noqa: BLE001 - any exception here is itself the corruption signal this script exists to catch
                reader_errors.append(f"iter {i}: {type(e).__name__}: {e}")
            reader_completed += 1
            if i % 10 == 0:
                wdt.feed()

    async def snapshotter() -> None:
        nonlocal snapshot_completed
        for i in range(SNAPSHOTTER_ITERATIONS):
            try:
                temp_offset, meas_int, amb_pres, altitude, frc, self_cal = await scd.get_config_snapshot()
                if not (2 <= meas_int <= 1800):
                    snapshot_errors.append(f"iter {i}: MeasInt={meas_int!r} outside valid schema range")
                if not (400 <= frc <= 2000):
                    snapshot_errors.append(f"iter {i}: ForceCalRef={frc!r} outside valid schema range")
            except Exception as e:  # noqa: BLE001 - see reader()'s own comment
                snapshot_errors.append(f"iter {i}: {type(e).__name__}: {e}")
            snapshot_completed += 1
            if i % 5 == 0:
                wdt.feed()

    await asyncio.wait_for(asyncio.gather(reader(), snapshotter()), 90.0)

    failures = []
    if reader_completed != READER_ITERATIONS:
        failures.append(f"reader only completed {reader_completed}/{READER_ITERATIONS} iterations")
    if snapshot_completed != SNAPSHOTTER_ITERATIONS:
        failures.append(f"snapshotter only completed {snapshot_completed}/{SNAPSHOTTER_ITERATIONS} iterations")
    failures.extend(reader_errors)
    failures.extend(snapshot_errors)

    if failures:
        print(f"RESULT: FAIL {len(failures)} issue(s): {'; '.join(failures[:10])}")
    else:
        print(
            f"RESULT: PASS reader={reader_completed}/{READER_ITERATIONS} "
            f"snapshotter={snapshot_completed}/{SNAPSHOTTER_ITERATIONS} both clean, no CRC/bus faults"
        )


asyncio.run(_main())
