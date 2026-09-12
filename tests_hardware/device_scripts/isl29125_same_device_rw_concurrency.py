"""Isolated-driver device script: the ISL29125's same-device concurrency proof - "ongoing read,
incoming write" (SPECIFICATION.md Part C.8). Its config registers are volatile (FN8424 p7 calls
them volatile memory outright), so this writes freely; the sharper hazard is the DESTRUCTIVE 0x08
status read, which a config write landing mid-cycle must not tear."""

import asyncio

import machine

import asy_i2c_driver
from asy_isl29125_driver import ISL29125_I2C

READ_ITERATIONS = 20
WRITE_ITERATIONS = 6
_IR_ADJUST_VALUES = (0, 16, 32, 40, 48, 63)  # every one legal per p10's own 0-63 ALSCC field
_STATUS_RESERVED_MASK = 0xC8  # B7:B6 and B3 read zero on a working part (p12, Table 15)


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)
    # Constructs the PROTOCOL layer directly, never ISL29125_Reader: Part C.8's standing rule for
    # a concurrency script that exercises persisted config, so nothing here can touch the
    # RP2040's own flash filesystem. The ISL has no on-chip NVM at all, so rewriting its config
    # costs nothing either - this is the first promoted sensor where that is true.
    i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000, timeout=200000)
    isl = ISL29125_I2C(i2c1)
    await isl.setup()

    read_errors = []
    read_completed = 0
    write_errors = []
    write_completed = 0

    async def reader() -> None:
        nonlocal read_completed
        for i in range(READ_ITERATIONS):
            try:
                status = await isl.read_status()
                if status & _STATUS_RESERVED_MASK:
                    read_errors.append(f"iter {i}: status={status:#04x} has a reserved bit set - the read was torn or the part is faulty")
                green, red, blue = await isl.read_counts()
                if not all(0 <= channel <= 0xFFFF for channel in (green, red, blue)):
                    read_errors.append(f"iter {i}: counts=({green}, {red}, {blue}) outside the 16-bit range")
                if green == red == blue == 0xFFFF and status & _STATUS_RESERVED_MASK:
                    read_errors.append(f"iter {i}: all-ones counts with an implausible status - the bus looks dead, not saturated")
            except Exception as e:
                read_errors.append(f"iter {i}: read raised {e!r}")
            else:
                read_completed += 1
            wdt.feed()
            await asyncio.sleep_ms(50)

    async def writer() -> None:
        nonlocal write_completed
        await asyncio.sleep_ms(120)  # let the reader get well into its run first
        for i in range(WRITE_ITERATIONS):
            wanted = _IR_ADJUST_VALUES[i % len(_IR_ADJUST_VALUES)]
            try:
                # An IR-compensation-only change: a 2-byte burst at 0x02, which deliberately does
                # NOT restart the conversion, so a concurrent read keeps producing real data.
                await isl.configure(ir_adjust=wanted)
                snapshot = await isl.get_config_snapshot()
                readback = snapshot[1] & 0x3F
                if readback != wanted:
                    write_errors.append(f"iter {i}: wrote IrCompAdjust={wanted}, read back {readback}")
            except Exception as e:
                write_errors.append(f"iter {i}: write raised {e!r}")
            else:
                write_completed += 1
            wdt.feed()
            await asyncio.sleep_ms(90)

    await asyncio.gather(reader(), writer())

    failures = []
    if read_completed != READ_ITERATIONS:
        failures.append(f"only {read_completed}/{READ_ITERATIONS} reads completed")
    if write_completed != WRITE_ITERATIONS:
        failures.append(f"only {write_completed}/{WRITE_ITERATIONS} writes completed")
    failures.extend(read_errors)
    failures.extend(write_errors)

    if failures:
        print(f"RESULT: FAIL {'; '.join(failures)}")
    else:
        print(f"RESULT: PASS {read_completed} reads and {write_completed} config writes interleaved with no torn value")


asyncio.run(_main())
