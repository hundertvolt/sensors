"""Isolated-driver device script: the UART link must keep completing transfers while every other
real subsystem on this board is busy - both I2C buses, the FRAM's SPI bus, and heavy allocation
churn all at once. The realistic worst case for a stop-and-wait link sharing one core."""
# Reads only: nothing here writes an I2C sensor's EEPROM or the RP2040's own flash filesystem, per
# C.8's write-safety constraints. FRAM reads are free; its writes are a separate tier's business.

import asyncio
import gc
import time

import machine

import asy_i2c_driver
import asy_spi_driver
import asy_uart_driver
from asy_fram_manager import AsyFramManager
from asy_scd30_driver import SCD30_I2C
from asy_sgp40_driver import SGP40_I2C
from asy_uart_comm import ROLE_INITIATOR, ROLE_RESPONDER, UART_Comm

BAUDRATE = 115200
PAYLOAD_SIZE = 48
TIMEOUT_MS = 1000
POLL_WAIT_MS = 2
POLL_IDLE_MS = 50
BUF_BYTES = 512
_CMD_BANNER = 0x01
_BANNER = b"loaded-link-ok"
RUN_MS = 6000
# A stop-and-wait round trip is a few ms; over this window even a heavily loaded board should land
# many. The floor is deliberately far below the unloaded rate - this asserts the link keeps making
# progress under load, not a throughput number.
_MIN_TRANSFERS = 20  # measured 58 unloaded-by-comparison; this is a floor, not a throughput target
# No transfer may come close to its own deadline: half the timeout still leaves the link visibly
# healthy rather than merely not-yet-failing. Measured worst case under this load is ~114ms.
_MAX_RTT_MS = TIMEOUT_MS // 2
_CHURN_BLOCK = 512  # bytes per allocation in the churn task - enough to fragment, far from the cap


def get_callback(cmd_id: int) -> "tuple[bool, bytes | None]":
    return (cmd_id == _CMD_BANNER), _BANNER


def set_callback(cmd_id: int) -> "tuple[bool, int | None]":
    return True, None


class Load:
    # Every concurrent pressure source, each counting its own progress so a starved one is visible
    # rather than merely absent.
    def __init__(self) -> None:
        self.i2c0_reads = 0
        self.i2c1_reads = 0
        self.spi_reads = 0
        self.churn_blocks = 0
        self.alloc_failures = 0
        self.stop = False


async def _sgp_load_loop(sgp: "SGP40_I2C", load: Load) -> None:
    # Real driver traffic through the real session lock, not a bus scan: scan() is synchronous and
    # blocks the event loop for the whole 128-address sweep, which models nothing production does.
    while not load.stop:
        try:
            await sgp.measure_raw()
            load.i2c1_reads += 1
        except Exception:  # a device fault is a different tier's subject
            pass
        await asyncio.sleep_ms(5)


async def _scd_load_loop(scd: SCD30_I2C, load: Load) -> None:
    # Read-only getters throughout: nothing here touches the SCD30's own EEPROM (CLAUDE.md).
    while not load.stop:
        try:
            await scd.get_measurement_interval()
            load.i2c0_reads += 1
        except Exception:
            pass
        await asyncio.sleep_ms(5)


async def _fram_read_loop(fram: AsyFramManager, load: Load) -> None:
    while not load.stop:
        if await fram.fram.verify_present():
            load.spi_reads += 1
        await asyncio.sleep_ms(10)


async def _memory_churn_loop(load: Load) -> None:
    # Pressure on the allocator, which is what turns a latent one-big-allocation design into a
    # failure (SPECIFICATION.md Part I). Held briefly, then dropped, so the heap keeps moving.
    held: list[bytearray] = []
    while not load.stop:
        try:
            held.append(bytearray(_CHURN_BLOCK))
            load.churn_blocks += 1
        except MemoryError:
            load.alloc_failures += 1
            held = []
            gc.collect()
        if len(held) > 24:
            held = held[12:]
        await asyncio.sleep_ms(2)


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)
    failures = []
    load = Load()

    uart0 = asy_uart_driver.UART(0, 0, 1, baudrate=BAUDRATE, rxbuf=BUF_BYTES, txbuf=BUF_BYTES, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_IDLE_MS)
    uart1 = asy_uart_driver.UART(1, 8, 9, baudrate=BAUDRATE, rxbuf=BUF_BYTES, txbuf=BUF_BYTES, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_IDLE_MS)
    initiator = UART_Comm(uart0, ROLE_INITIATOR, payload_size=PAYLOAD_SIZE, timeout=TIMEOUT_MS, name="UART_INIT")
    responder = UART_Comm(
        uart1, ROLE_RESPONDER, payload_size=PAYLOAD_SIZE, timeout=TIMEOUT_MS,
        get_callback=get_callback, set_callback=set_callback, name="UART_RESP",
    )
    await initiator.setup()
    await responder.setup()

    # dev_legacy/README.md's wiring: i2c0 (13, 12), i2c1 (15, 14), SPI0 (2, 3, 4) with FRAM CS=5.
    i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000, timeout=200000)
    spi0 = asy_spi_driver.SPI(0, 2, 3, 4)
    fram = AsyFramManager(spi0, 5, max_size=0x40000)
    await fram.setup()
    # SCD30 and SGP40 both sit on i2c1 on this bench; the SCD30 getters below are reads, so the
    # loop labelled i2c0 is really "the other device on the shared bus" - both contend for i2c1,
    # which is the harder case for the link anyway.
    scd = SCD30_I2C(i2c1)
    sgp = SGP40_I2C(i2c1)
    await sgp.setup()

    transfers = 0
    link_failures = 0
    worst_rtt_ms = 0
    tasks = [
        asyncio.create_task(responder._listen_loop()),
        asyncio.create_task(_scd_load_loop(scd, load)),
        asyncio.create_task(_sgp_load_loop(sgp, load)),
        asyncio.create_task(_fram_read_loop(fram, load)),
        asyncio.create_task(_memory_churn_loop(load)),
    ]
    try:
        deadline = time.ticks_add(time.ticks_ms(), RUN_MS)
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            wdt.feed()
            started = time.ticks_ms()
            answer = await initiator.uart_get(_CMD_BANNER)
            rtt = time.ticks_diff(time.ticks_ms(), started)
            if answer is not None and bytes(answer) == _BANNER:
                transfers += 1
                worst_rtt_ms = max(worst_rtt_ms, rtt)
            else:
                link_failures += 1
            await asyncio.sleep_ms(5)
    finally:
        load.stop = True
        for task in tasks:
            task.cancel()
        await asyncio.sleep_ms(50)
        wdt.feed()

    counts_i = await initiator.get_error_counter()
    counts_r = await responder.get_error_counter()
    uart0.deinit()
    uart1.deinit()

    if transfers < _MIN_TRANSFERS:
        failures.append(f"only {transfers} transfers completed under load, under the {_MIN_TRANSFERS} floor")
    if link_failures:
        failures.append(f"{link_failures} transfer(s) failed while the rest of the system was busy")
    if worst_rtt_ms > _MAX_RTT_MS:
        failures.append(f"worst round trip {worst_rtt_ms}ms under load, past the {_MAX_RTT_MS}ms bound (timeout is {TIMEOUT_MS}ms)")
    for name, counts in (("UART_INIT", counts_i), ("UART_RESP", counts_r)):
        if name in counts and counts[name]["ErrCount"]:
            failures.append(f"{name} logged {counts[name]['ErrCount']} errors under load: {counts[name]['ErrNum']}")
    # Every other subsystem must have kept running too: a link that stayed healthy by starving the
    # buses it shares a core with has not demonstrated anything.
    if not load.i2c0_reads or not load.i2c1_reads:
        failures.append(f"an I2C device was starved by the link: scd={load.i2c0_reads} sgp={load.i2c1_reads}")
    if not load.spi_reads:
        failures.append("the FRAM's SPI bus was starved by the link")
    if not load.churn_blocks:
        failures.append("the allocation churn task never ran")

    if failures:
        print("RESULT: FAIL " + "; ".join(failures))
    else:
        print(
            f"RESULT: PASS {transfers} transfers (worst RTT {worst_rtt_ms}ms) while scd={load.i2c0_reads} "
            f"sgp={load.i2c1_reads} spi={load.spi_reads} churn={load.churn_blocks} "
            f"allocfail={load.alloc_failures}",
        )


asyncio.run(_main())
