"""Isolated-driver device script: the ISL29125's same-device "ongoing read, incoming write" proof (SPECIFICATION.md
Part C.8). Its config registers are volatile (FN8424 p.7), so this writes freely; the sharper hazard is the destructive
0x08 status read, which a config write landing mid-cycle must not tear. Reports facts; the host gives the verdict."""

import asyncio

import asy_i2c_driver
from asy_isl29125_driver import ISL29125_I2C

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

# @tunable l3.isl29125_same_device_rw_concurrency_read_iterations = 20
_READ_ITERATIONS = 20
# @tunable l3.isl29125_same_device_rw_concurrency_write_iterations = 6
_WRITE_ITERATIONS = 6
# @tunable l3.isl29125_same_device_rw_concurrency_read_step_ms = 50
_READ_STEP_MS = 50
# @tunable l3.isl29125_same_device_rw_concurrency_write_step_ms = 90
_WRITE_STEP_MS = 90
# The writer starts once the reader completed its first read, at most this long after (a deadline, not a head start).
# @tunable l3.isl29125_same_device_rw_concurrency_writer_delay_ms = 120
_WRITER_DELAY_MS = 120
# @tunable l3.isl29125_same_device_rw_concurrency_writer_poll_ms = 10
_WRITER_POLL_MS = 10
_IR_ADJUST_VALUES = (0, 16, 32, 40, 48, 63)  # every one legal per FN8424 p.10's 0-63 field
_STATUS_RESERVED_MASK = 0xC8  # B7:B6 and B3 read zero on a working part (FN8424 p.12, Table 15)
_IR_ADJUST_MASK = 0x3F  # source: CONFIG2's IR Comp Adjust bits B[5:0] (FN8424 p.10)


async def _main() -> None:
    wdt = arm()
    # The protocol layer directly, never ISL29125_Reader (Part C.8): nothing here touches the RP2040's flash, and the
    # part has no NVM, so rewriting its configuration costs nothing.
    bus = BENCH["bus"][BENCH["instances"]["isl29125"]["bus"]]
    i2c = asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"], frequency=bus["frequency"], timeout=bus.get("timeout"))
    isl = ISL29125_I2C(i2c)
    await isl.setup()
    torn = [0]

    async def read() -> "str | None":
        status = await isl.read_status()
        counts = await isl.read_counts()
        if status & _STATUS_RESERVED_MASK or not all(0 <= c <= 0xFFFF for c in counts):
            torn[0] += 1
            return f"status={status:#04x} counts={counts}: a reserved status bit or a count outside 16 bits - a torn read"
        return None

    reader_rec, write_rec = Record("isl29125_reader"), Record("isl29125_writer")

    async def writer() -> None:
        waited_ms = 0
        while reader_rec.reads + reader_rec.total == 0 and waited_ms < _WRITER_DELAY_MS:
            await fed_sleep_ms(wdt, _WRITER_POLL_MS)
            waited_ms += _WRITER_POLL_MS
        for i in range(_WRITE_ITERATIONS):
            wanted = _IR_ADJUST_VALUES[i % len(_IR_ADJUST_VALUES)]
            try:
                # IR compensation only: a 2-byte burst at 0x02 that does not restart the conversion.
                await isl.configure(ir_adjust=wanted)
                readback = (await isl.get_config_snapshot())[1] & _IR_ADJUST_MASK
            except (OSError, RuntimeError, ValueError) as e:
                write_rec.fail(f"write {i}: {e!r}")
            else:
                if readback == wanted:
                    write_rec.reads += 1
                else:
                    write_rec.fail(f"write {i}: wrote IRCompAdjust={wanted}, read back {readback}")
            await fed_sleep_ms(wdt, _WRITE_STEP_MS)

    await asyncio.gather(read_loop(read, _READ_ITERATIONS, _READ_STEP_MS, wdt, reader_rec, Stop()), writer())
    fact("reads", reader_rec.reads)
    fact("reads_planned", _READ_ITERATIONS)
    fact("torn_reads", torn[0])
    fact("writes_ok", write_rec.reads)
    fact("writes_planned", _WRITE_ITERATIONS)
    report_errors([reader_rec, write_rec])
    done()


asyncio.run(_main())
