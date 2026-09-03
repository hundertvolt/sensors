"""Isolated-driver device script, flash-tier: BMP3xx's own same-device concurrency proof - "ongoing
read, incoming write" (SPECIFICATION.md Part C.8's device-session lock model). Unlike SCD30, BMP3xx's
own OSR/CONFIG registers are volatile (SRAM-backed, reset on power loss - confirmed against
datasheets/bmp3xx/bst-bmp388-ds001.pdf sec 4.3.16-4.3.20, no NVM/EEPROM config store documented
anywhere in this chip), so repeated real writes here carry none of SCD30's real NVM-wear concern -
this script writes freely, many times, unlike scd30_same_device_rw_concurrency.py's own
exactly-once budget.

Two coroutines run concurrently against one BMP3XX_I2C instance: a burst of full forced-mode reads
(get_pressure_and_temperature(), each its own multi-step device-session-locked trigger/poll/burst-
read sequence), and a burst of real oversampling/filter-coefficient writes. Neither this chip's
protocol nor this test has CRC framing (unlike SCD30/SGP40) - correctness is proven by BMP3XX_I2C's
own datasheet-range rejection (_read() raises ValueError outside sec 1 Table 2's operating range) and
by confirming every write is actually readable back afterward, unmixed with a concurrently-in-flight
read's own register access.

Uses the raw BMP3XX_I2C protocol class directly, never BMP3xx_Reader - see
scd30_same_device_rw_concurrency.py's own docstring for why (no ConfigManager/RP2040 flash I/O
anywhere in this script - the project owner's real-hardware caveat).

This bench unit wires BMP3xx to I2C0 (scl=13, sda=12) - see bmp3xx_plausibility_read.py's own
docstring for the real i2c.scan() confirmation this was checked against.

Run via `mpremote run <this> soft-reset`."""

import asyncio

import machine

import asy_i2c_driver
from asy_bmp3xx_driver import BMP3XX_I2C

PRESSURE_MIN_HPA, PRESSURE_MAX_HPA = 300.0, 1250.0
TEMP_MIN_C, TEMP_MAX_C = -40.0, 85.0
_OSR_SETTINGS = (1, 2, 4, 8, 16, 32)

READ_ITERATIONS = 20
WRITE_ITERATIONS = 6


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)
    i2c0 = asy_i2c_driver.I2C(0, 13, 12, frequency=50000)
    bmp = BMP3XX_I2C(i2c0)
    await bmp.setup()

    read_errors = []
    read_completed = 0
    write_errors = []
    write_completed = 0

    async def reader() -> None:
        nonlocal read_completed
        for i in range(READ_ITERATIONS):
            try:
                pressure, temperature = await bmp.get_pressure_and_temperature()
                if not (PRESSURE_MIN_HPA <= pressure <= PRESSURE_MAX_HPA):
                    read_errors.append(f"iter {i}: Pres={pressure!r} outside plausible bounds")
                if not (TEMP_MIN_C <= temperature <= TEMP_MAX_C):
                    read_errors.append(f"iter {i}: Temp={temperature!r} outside plausible bounds")
            except Exception as e:  # noqa: BLE001 - any exception is itself the corruption signal this script exists to catch
                read_errors.append(f"iter {i}: {type(e).__name__}: {e}")
            read_completed += 1
            if i % 5 == 0:
                wdt.feed()

    async def writer() -> None:
        nonlocal write_completed
        for i in range(WRITE_ITERATIONS):
            await asyncio.sleep(0.05)  # spread writes out across the reader's whole run
            oversample = _OSR_SETTINGS[i % len(_OSR_SETTINGS)]
            try:
                await bmp.set_pressure_oversampling(oversample)
                readback = await bmp.get_pressure_oversampling()
                if readback != oversample:
                    write_errors.append(f"iter {i}: wrote PressOvers={oversample}, read back {readback} - torn/corrupted write")
            except Exception as e:  # noqa: BLE001 - see reader()'s own comment
                write_errors.append(f"iter {i}: {type(e).__name__}: {e}")
            write_completed += 1

    await asyncio.wait_for(asyncio.gather(reader(), writer()), 60.0)

    # Restore the datasheet/production default (x1, see asy_bmp3xx_driver.py's own _init_bmp()
    # default schema) - this register is volatile anyway (see module docstring), but leaving it
    # deliberately clean avoids surprising a later, unrelated real-hardware session.
    try:
        await bmp.set_pressure_oversampling(1)
    except Exception:  # noqa: BLE001 - best-effort cleanup only, not this script's own pass/fail signal
        pass

    failures = []
    if read_completed != READ_ITERATIONS:
        failures.append(f"reader only completed {read_completed}/{READ_ITERATIONS} iterations")
    if write_completed != WRITE_ITERATIONS:
        failures.append(f"writer only completed {write_completed}/{WRITE_ITERATIONS} iterations")
    failures.extend(read_errors)
    failures.extend(write_errors)

    if failures:
        print(f"RESULT: FAIL {len(failures)} issue(s): {'; '.join(failures[:10])}")
    else:
        print(f"RESULT: PASS reader={read_completed}/{READ_ITERATIONS} writer={write_completed}/{WRITE_ITERATIONS} both clean, no corruption")


asyncio.run(_main())
