"""Isolated-driver device script: the UART link must keep completing transfers - banner GETs and echo-checked
multi-chunk SETs - while every other real subsystem is busy: the shared I2C bus, the FRAM's SPI bus and allocation
churn at once. The realistic worst case for a stop-and-wait link sharing one core; facts out, the host judges."""
# Reads only on the sensors and the FRAM: nothing writes an I2C sensor's EEPROM or the RP2040's flash filesystem (C.8).

import asyncio
import gc
import time

import asy_i2c_driver
import asy_spi_driver
import asy_uart_driver
from asy_crc_checks import CRC16
from asy_fram_manager import FRAMManager
from asy_scd30_driver import SCD30_I2C
from asy_sgp40_driver import SGP40_I2C
from asy_uart_comm import DEFAULT_LIMITS, ROLE_INITIATOR, ROLE_RESPONDER, ResponderCallbacks, TransferLimits, UARTComm

# @include _shared/facts.py
# @include _shared/watchdog.py
# @include _shared/settle.py
# @include _shared/isl_error_log.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    import machine
    from _mpy_shed.time_mp import _TicksMs
    from _shared.facts import _ERRORS_KEPT, done, errors, fact
    from _shared.isl_error_log import log_record
    from _shared.settle import settled
    from _shared.watchdog import arm
    from bench_facts import BenchFacts, BusFacts

    from asy_base_classes import PieceBuffer

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

PAYLOAD_SIZE = 48  # the protocol's default frame, agreed out of band (J.6)
TIMEOUT_MS = 1000
_CMD_BANNER = 0x01
_CMD_ECHO = 0x02
_BANNER = b"loaded-link-ok"
_ECHO_BYTES = PAYLOAD_SIZE * 2 + 7  # three data chunks per echo SET
# @tunable l3.uart_link_under_concurrent_system_load_run_ms = 12000
_RUN_MS = 12000  # long enough for a second measurement window to mean something
# A floor far below the unloaded rate (measured 58): the link keeps making progress under load, no throughput target.
# @tunable l3.uart_link_under_concurrent_system_load_min_transfers = 20
_MIN_TRANSFERS = 20
# No transfer may come close to its own deadline: half the timeout leaves the link visibly healthy (measured ~114 ms).
# @tunable l3.uart_link_under_concurrent_system_load_max_rtt_fraction = 2
_MAX_RTT_FRACTION = 2
# @tunable l3.uart_link_under_concurrent_system_load_churn_block = 512
_CHURN_BLOCK = 512  # bytes per allocation in the churn task - enough to fragment, far from the cap
_CHURN_HELD_MAX = 24  # blocks held before half are dropped: at most 25 x 512 B live at once
# @tunable l3.uart_link_under_concurrent_system_load_sensor_load_step_ms = 5
_SENSOR_LOAD_STEP_MS = 5
# @tunable l3.uart_link_under_concurrent_system_load_spi_load_step_ms = 10
_SPI_LOAD_STEP_MS = 10
# @tunable l3.uart_link_under_concurrent_system_load_churn_step_ms = 2
_CHURN_STEP_MS = 2
# @tunable l3.uart_link_under_concurrent_system_load_heap_sample_step_ms = 8
_HEAP_SAMPLE_STEP_MS = 8
# @tunable l3.uart_link_under_concurrent_system_load_transfer_step_ms = 5
_TRANSFER_STEP_MS = 5
# @tunable l3.uart_link_under_concurrent_system_load_heap_floor_samples = 8
_HEAP_FLOOR_SAMPLES = 8
# @tunable l3.uart_link_under_concurrent_system_load_heap_growth_max_bytes = 2048
_HEAP_GROWTH_MAX_BYTES = 2048


class Load:
    # Every concurrent pressure source, each counting its own progress so a starved one is visible, not merely absent.
    def __init__(self) -> None:
        self.scd_reads = 0
        self.sgp_reads = 0
        self.i2c_errors = 0  # counted and reported, never silently dropped
        self.spi_reads = 0
        self.fram_absent = 0  # a verify_present() that found no FRAM: counted, the host fails on any
        self.churn_blocks = 0
        self.alloc_failures = 0
        self.stop = False


class _Echo:
    # The responder's callbacks: the banner, and the last echo SET's payload answered back by one copy-out.
    def __init__(self) -> None:
        self.last: PieceBuffer | None = None

    def get(self, cmd_id: int) -> "tuple[bool, bytes | bytearray | None]":
        if cmd_id == _CMD_BANNER:
            return True, _BANNER
        if cmd_id == _CMD_ECHO and self.last is not None:
            answer = bytearray(len(self.last))
            return self.last.copy_into(answer), answer
        return False, None

    def message(self, cmd_id: int, cmd: int, payload: "PieceBuffer | None") -> None:
        if cmd_id == _CMD_ECHO:
            self.last = payload

    def set(self, cmd_id: int) -> "tuple[bool, int | None]":
        return cmd_id == _CMD_ECHO, None


def _driver(bus: "BusFacts") -> "asy_uart_driver.UART":
    return asy_uart_driver.UART(
        bus["id"], bus["tx_pin"], bus["rx_pin"], baudrate=bus["baudrate"], rxbuf=bus["rxbuf"], txbuf=bus["txbuf"], rx_ring=bus["rx_ring"],
        poll_wait_ms=bus["poll_wait_ms"], poll_idle_ms=bus["poll_idle_ms"], crc=CRC16() if BENCH.get("CRC_MODE", "none") == "crc16" else None,
    )


async def _fram_read_loop(fram: FRAMManager, load: Load) -> None:
    while not load.stop:
        if await fram.fram.verify_present():
            load.spi_reads += 1
        else:
            load.fram_absent += 1
        await asyncio.sleep_ms(_SPI_LOAD_STEP_MS)


async def _heap_floor() -> int:
    # gc.mem_alloc() mid-run counts the churn's own held blocks, a swing of up to 6144 B: the minimum over more than
    # two churn cycles is the live floor, which is what "did the link retain" needs.
    floor = 0
    for _ in range(_HEAP_FLOOR_SAMPLES):
        gc.collect()
        sample = gc.mem_alloc()
        floor = sample if not floor else min(floor, sample)
        await asyncio.sleep_ms(_HEAP_SAMPLE_STEP_MS)
    return floor


async def _memory_churn_loop(load: Load) -> None:
    # Pressure on the allocator, which turns a latent one-big-allocation design into a failure (Part I). A failed
    # allocation is recorded, never collected around: the host fails the run on any (CLAUDE.md memory rule).
    held: list[bytearray] = []
    while not load.stop:
        try:
            held.append(bytearray(_CHURN_BLOCK))
            load.churn_blocks += 1
        except MemoryError:
            load.alloc_failures += 1
            held = []
        if len(held) > _CHURN_HELD_MAX:
            held = held[_CHURN_HELD_MAX // 2 :]
        await asyncio.sleep_ms(_CHURN_STEP_MS)


async def _round(initiator: UARTComm, link: "_Link", payload: bytearray, scratch: bytearray, banner: bytearray, seed: int) -> None:
    # One banner GET, one echo SET of a fresh pattern and the echo GET compared byte for byte against it.
    started = time.ticks_ms()
    answer = await initiator.uart_get(_CMD_BANNER)
    link.timed(started, ok=answer is not None and len(answer) == len(_BANNER) and answer.copy_into(banner) and banner == _BANNER)
    for i in range(len(payload)):
        payload[i] = (seed + i) & 0xFF
    started = time.ticks_ms()
    sent = await initiator.uart_set(_CMD_ECHO, payload)
    link.timed(started, ok=sent)
    link.set_total += 1
    started = time.ticks_ms()
    echo = await initiator.uart_get(_CMD_ECHO)
    link.timed(started, ok=echo is not None)
    if sent and echo is not None and len(echo) == len(payload) and echo.copy_into(scratch) and scratch == payload:
        link.echo_intact += 1
    else:
        link.mismatch(f"round {seed}: sent {sent}, echo {None if echo is None else len(echo)} bytes")


async def _run(wdt: "machine.WDT", initiator: UARTComm, link: "_Link") -> "tuple[int, int]":
    payload = bytearray(_ECHO_BYTES)
    scratch = bytearray(_ECHO_BYTES)  # each answer is a PieceBuffer (no buffer protocol): compared by one copy-out
    banner = bytearray(len(_BANNER))
    heap_at_third = 0
    started_ms = time.ticks_ms()
    seed = 0
    while time.ticks_diff(time.ticks_ms(), started_ms) < _RUN_MS:
        wdt.feed()
        if not heap_at_third and time.ticks_diff(time.ticks_ms(), started_ms) > _RUN_MS // 3:
            heap_at_third = await _heap_floor()  # after the first transactions' one-time cost
        await _round(initiator, link, payload, scratch, banner, seed)
        seed += 1
        await asyncio.sleep_ms(_TRANSFER_STEP_MS)
    return heap_at_third, await _heap_floor()  # the end sampled while the loads still run, as the third was


class _Link:
    # The initiator's running record: transfers and their worst round trip, echo SETs and their byte-for-byte check.
    def __init__(self) -> None:
        self.transfers = 0
        self.failures = 0
        self.worst_rtt_ms = 0
        self.set_total = 0
        self.echo_intact = 0
        self.mismatch_total = 0
        self.mismatches: list[str] = []

    def mismatch(self, text: str) -> None:
        self.mismatch_total += 1
        if len(self.mismatches) < _ERRORS_KEPT:
            self.mismatches.append(text)

    def timed(self, started: "_TicksMs", *, ok: bool) -> None:
        if ok:
            self.transfers += 1
            self.worst_rtt_ms = max(self.worst_rtt_ms, time.ticks_diff(time.ticks_ms(), started))
        else:
            self.failures += 1


async def _scd_load_loop(scd: SCD30_I2C, load: Load) -> None:
    # Read-only getters throughout: nothing here touches the SCD30's own NVM.
    while not load.stop:
        try:
            await scd.get_measurement_interval()
            load.scd_reads += 1
        except Exception:  # counted, as above
            load.i2c_errors += 1
        await asyncio.sleep_ms(_SENSOR_LOAD_STEP_MS)


async def _sgp_load_loop(sgp: SGP40_I2C, load: Load) -> None:
    # Real driver traffic through the real session lock, never a bus scan (synchronous, it would block the loop).
    while not load.stop:
        try:
            await sgp.measure_raw()
            load.sgp_reads += 1
        except Exception:  # a device fault is a different tier's subject; counted so it stays visible
            load.i2c_errors += 1
        await asyncio.sleep_ms(_SENSOR_LOAD_STEP_MS)


async def _main() -> None:
    wdt = arm()
    # The memory rule's first stage: MicroPython's own reactive default, no proactive collection (CLAUDE.md).
    gc.threshold(-1)
    fact("gc_threshold", gc.threshold())
    fact("crc_mode", BENCH.get("CRC_MODE", "none"))
    load = Load()
    link_bus = BENCH["bus"][BENCH["instances"]["uart_link_init"]["bus"]]
    limits = TransferLimits(PAYLOAD_SIZE, TIMEOUT_MS, DEFAULT_LIMITS.chunk_bytes, link_bus["max_transfer_bytes"])
    uart0, uart1 = _driver(link_bus), _driver(BENCH["bus"][BENCH["instances"]["uart_link_resp"]["bus"]])
    echo = _Echo()
    initiator = UARTComm(uart0, ROLE_INITIATOR, limits=limits, name="UART_INIT")
    responder = UARTComm(uart1, ROLE_RESPONDER, limits=limits, callbacks=ResponderCallbacks(echo.get, echo.set, echo.message), name="UART_RESP")
    sensor_bus = BENCH["bus"][BENCH["instances"]["scd30"]["bus"]]  # the SCD30 and the SGP40 share it on this bench
    i2c = asy_i2c_driver.I2C(sensor_bus["id"], sensor_bus["scl_pin"], sensor_bus["sda_pin"], frequency=sensor_bus["frequency"], timeout=sensor_bus.get("timeout"))
    fram_facts = BENCH["instances"]["fram"]
    spi_bus = BENCH["bus"][fram_facts["bus"]]
    fram = FRAMManager(asy_spi_driver.SPI(spi_bus["id"], spi_bus["sck_pin"], spi_bus["mosi_pin"], spi_bus["miso_pin"]), fram_facts["cs_pin"], max_size=BENCH["fram_max_size"])
    sgp = SGP40_I2C(i2c)
    setups = {"initiator": await initiator.setup(), "responder": await responder.setup(), "fram": await fram.setup(), "sgp40": await sgp.setup()}
    fact("setup", setups)
    link = _Link()
    heap = (0, 0)
    if all(setups.values()):
        tasks = [
            responder.start_asy_listen(),
            asyncio.create_task(_scd_load_loop(SCD30_I2C(i2c), load)),
            asyncio.create_task(_sgp_load_loop(sgp, load)),
            asyncio.create_task(_fram_read_loop(fram, load)),
            asyncio.create_task(_memory_churn_loop(load)),
        ]
        try:
            heap = await _run(wdt, initiator, link)
        finally:
            load.stop = True
            for task in tasks:
                task.cancel()
                await settled(wdt, task)
    fact("transfers", link.transfers)
    fact("link_failures", link.failures)
    fact("worst_rtt_ms", link.worst_rtt_ms)
    fact("timeout_ms", TIMEOUT_MS)
    fact("set_total", link.set_total)
    fact("echo_intact", link.echo_intact)
    errors("echo_mismatch", link.mismatch_total, link.mismatches)
    counts = {}
    for comm in (initiator, responder):  # no await inside a comprehension on MicroPython
        counts[comm.name] = log_record(await comm.get_error_counter(), comm.name)
    fact("error_counts", counts)
    fact("load", {"scd_reads": load.scd_reads, "sgp_reads": load.sgp_reads, "i2c_errors": load.i2c_errors, "spi_reads": load.spi_reads, "fram_absent": load.fram_absent, "churn_blocks": load.churn_blocks})
    errors("alloc_failures", load.alloc_failures, [f"churn allocation of {_CHURN_BLOCK} B failed while <= {_CHURN_HELD_MAX + 1} blocks were held"] if load.alloc_failures else [])
    fact("heap_at_third", heap[0])
    fact("heap_at_end", heap[1])
    fact("bounds", {"min_transfers": _MIN_TRANSFERS, "max_rtt_ms": TIMEOUT_MS // _MAX_RTT_FRACTION, "heap_growth_max_bytes": _HEAP_GROWTH_MAX_BYTES})
    uart0.deinit()
    uart1.deinit()
    done()


asyncio.run(_main())
