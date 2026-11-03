"""Holds interrupts off with machine.disable_irq() and a busy-wait while the other UART of the crossover pair keeps
sending, to show the DMA receive ring loses no frame within its bound and reports an overrun beyond it - no flash
write. STATE selects the soft-reset, break and config-write cases; facts out, the host test judges."""

import asyncio
import errno
import gc
import os
import time

import machine
import rp2
from machine import UART, Pin

import asy_config_manager as cm
import asy_uart_driver
from asy_crc_checks import CRC16
from asy_uart_comm import DEFAULT_LIMITS, ROLE_INITIATOR, ROLE_RESPONDER, ResponderCallbacks, TransferLimits, UARTComm

# @include _shared/facts.py
# @include _shared/watchdog.py
# @include _shared/settle.py
# @include _shared/heap_probe.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact
    from _shared.heap_probe import largest_block
    from _shared.settle import settled
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts, BusFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# Explicit, never inherited: the ring's heap cost is read at MicroPython's own reactive default, the (e) stage,
# whatever threshold an earlier run left.
gc.threshold(-1)

PAYLOAD_SIZE = 48
TIMEOUT_MS = 1000
FRAME = 5 + PAYLOAD_SIZE  # one protocol frame's length (J.3); a stream frame is a sequence byte, then its pattern
_CMD = 0x02
_UART_BASES = (0x40034000, 0x40038000)  # UART0/UART1 register blocks; UARTDR at offset 0 (RP2040 datasheet 4.2.8)
_UARTRSR = 0x004  # receive status: bit 3 OE (Table 427)
_UARTDMACR = 0x048  # bit 0 RXDMAE (Table 439)
_RSR_OE = 0x08
_DMACR_RXDMAE = 0x01
_DREQ_UART_TX = (20, 22)  # DREQ_UART0_TX, DREQ_UART1_TX (RP2040 datasheet 2.5.3.1)
# The W25Q16JV's page program max (tPP 3 ms) and sector erase typical and max (tSE 45/400 ms), the longest
# interrupts-off stretches ports/rp2/rp2_flash.c runs (v1.29.0); a fourth window is the first 100 ms past the bound.
_FLASH_WINDOWS_US = (3000, 45000, 400000)
_OVER_BOUND_STEP_US = 100000
_STREAM_MARGIN_US = 50000  # the stream runs this long on each side of a window
_AFTER_FRAMES = 4  # sent once the drain is done: every frame after a resync arrives intact
# @tunable l3.uart_dma_ring_interrupts_off_quiet_ms = 50
_QUIET_MS = 50
# Long past the 32-byte FIFO's fill at line rate (2.8 ms at 115200 baud).
# @tunable l3.uart_dma_ring_interrupts_off_oe_bound_us = 20000
_OE_BOUND_US = 20000
_SENTINEL = 0xA5
# @tunable l3.uart_dma_ring_interrupts_off_untouched_ms = 1000
_UNTOUCHED_MS = 1000
# The stream the harness's trailing soft reset lands in: far longer than that reset takes to arrive.
# @tunable l3.uart_dma_ring_interrupts_off_reset_stream_ms = 2000
_RESET_STREAM_MS = 2000
_LINK_TRANSACTIONS = 5
_BREAK_AFTER_MS = 2  # inside the 4.6 ms a 53-byte frame takes at 115200 baud
_SCRATCH_FILE = "config_HWTEST_UART.cfg"
_SCRATCH_SCHEMA: "cm.ConfigSchema" = (("Value", "int", 0, 0, 1000, None),)


async def _after_soft_reset(wdt: "machine.WDT") -> None:
    # After the reset: the same DMA channels claimable, and a fresh buffer of the ring's allocation left untouched while
    # the sender streams - no channel from before the reset still writes into memory.
    send_bus, recv_bus = _bus("uart_link_init"), _bus("uart_link_resp")
    claimed = (rp2.DMA(), rp2.DMA())
    writer = _raw_uart(send_bus)
    sender = _Sender(send_bus, _UNTOUCHED_MS * 1000)
    await sender.build()
    fact("channels_free", [claimed[0].channel, claimed[1].channel, sender.dma.channel])
    probe = bytearray(2 * recv_bus["rx_ring"])  # the driver allocates twice its ring to align it
    for i in range(len(probe)):
        probe[i] = _SENTINEL
    sender.start(0, sender.frames)
    await fed_sleep_ms(wdt, _UNTOUCHED_MS)
    fact("streamed", await sender.finished(wdt))
    fact("ring_untouched", all(b == _SENTINEL for b in probe))
    sender.dma.close()
    for channel in claimed:
        channel.close()
    writer.deinit()


async def _break(wdt: "machine.WDT") -> None:
    # A break sent mid-frame on the initiator's line between two framed transactions: that transaction fails, the next
    # succeeds, and whether the responder's driver counted the UARTRSR error a DMA read leaves.
    initiator, responder, drivers = await _pair()
    listener = responder.start_asy_listen()
    first = await initiator.uart_set(_CMD, b"before")
    laps = drivers[1].rx_overruns
    task = asyncio.create_task(initiator.uart_set(_CMD, bytes(PAYLOAD_SIZE)))
    await asyncio.sleep_ms(_BREAK_AFTER_MS)
    line = drivers[0]._uart  # machine.UART itself: the driver offers no break of its own
    if line is not None:
        line.sendbreak()
    while not task.done():
        await settled(wdt, task)
    broken = await task
    nxt = await initiator.uart_set(_CMD, b"after")
    counted = drivers[1].rx_overruns - laps
    listener.cancel()
    await settled(wdt, listener)
    fact("break", {"first_ok": first, "break_frame_failed": broken is False, "next_frame_ok": nxt, "rsr_error_counted": counted})
    for driver in drivers:
        driver.deinit()


def _bus(label: str) -> "BusFacts":
    return BENCH["bus"][BENCH["instances"][label]["bus"]]


class _Sender:
    # Framed frames from one pre-built buffer, out through a DMA channel paced by the sending UART's TX DREQ, so the
    # stream keeps going while the receiving side holds interrupts off; the UART itself is whoever owns it.
    def __init__(self, bus: "BusFacts", window_us: int, extra: int = 0) -> None:
        crc = _crc()
        self.frame_bytes = FRAME + (0 if crc is None else crc.length())
        self.frames = _frames_for(window_us, bus, self.frame_bytes) + extra
        self.buf = bytearray(self.frames * self.frame_bytes)
        self.dr = _UART_BASES[bus["id"]]
        self.dreq = _DREQ_UART_TX[bus["id"]]
        self.byte_us = 10 * 1000000 // bus["baudrate"] + 1
        self.deadline = time.ticks_ms()
        self.dma = rp2.DMA()

    async def build(self) -> None:
        crc = _crc()
        frame = bytearray(FRAME)
        for i in range(self.frames):
            frame[0] = i & 0xFF
            for j in range(1, FRAME):
                frame[j] = (i + j) & 0xFF
            framed = frame if crc is None else await crc.add(frame)
            if framed is not None:
                self.buf[i * self.frame_bytes : (i + 1) * self.frame_bytes] = framed

    async def finished(self, wdt: "machine.WDT") -> bool:
        # The stream's own wire time bounds the wait: a channel still busy past it is a fact, never a hang.
        while self.dma.active() and time.ticks_diff(self.deadline, time.ticks_ms()) > 0:
            wdt.feed()
            await asyncio.sleep_ms(1)
        return not self.dma.active()

    def start(self, first: int, count: int) -> None:
        view = memoryview(self.buf)[first * self.frame_bytes : (first + count) * self.frame_bytes]
        ctrl = self.dma.pack_ctrl(size=0, inc_read=True, inc_write=False, treq_sel=self.dreq)
        self.dma.config(read=view, write=self.dr, count=len(view), ctrl=ctrl, trigger=True)
        self.deadline = time.ticks_add(time.ticks_ms(), len(view) * self.byte_us // 1000 + _QUIET_MS)


def _comm(driver: "asy_uart_driver.UART", role: str, bus: "BusFacts") -> UARTComm:
    limits = TransferLimits(PAYLOAD_SIZE, TIMEOUT_MS, DEFAULT_LIMITS.chunk_bytes, bus["max_transfer_bytes"])
    if role == ROLE_INITIATOR:
        return UARTComm(driver, ROLE_INITIATOR, limits=limits, name="UART_INIT")
    return UARTComm(driver, ROLE_RESPONDER, limits=limits, callbacks=ResponderCallbacks(lambda _c: (True, b"r"), lambda _c: (True, None), None), name="UART_RESP")


async def _config_write(wdt: "machine.WDT") -> None:
    # The stream while a scratch manager flushes one changed value: a real flash write's interrupts-off window.
    send_bus, recv_bus = _bus("uart_link_init"), _bus("uart_link_resp")
    writer = _raw_uart(send_bus)
    sender = _Sender(send_bus, _FLASH_WINDOWS_US[-1])
    await sender.build()
    driver = _driver(recv_bus)
    fact("setup", await _comm(driver, ROLE_RESPONDER, recv_bus).setup())
    _remove_scratch()
    try:
        sender.start(0, sender.frames)
        flush_us = await _flush_us(_scratch_manager(), 1)
        oe = _oe(recv_bus)
        streamed = await sender.finished(wdt)
        fact("config_write", {"flush_us": flush_us, "streamed": streamed, "frames_sent": sender.frames, "frames_intact": len(await _drain(driver)), "uartrsr_oe": oe})
    finally:
        _remove_scratch()
        sender.dma.close()
        writer.deinit()
        driver.deinit()


async def _config_write_link(wdt: "machine.WDT") -> None:
    # The pair exchanging frames longer than the 32-byte TX FIFO while each transaction meets one config flush.
    initiator, responder, drivers = await _pair()
    listener = responder.start_asy_listen()
    mgr = _scratch_manager()
    expected = bytearray(b"r")
    scratch = bytearray(1)
    ok = failed = wrong = 0
    flushes = []
    _remove_scratch()
    try:
        for n in range(_LINK_TRANSACTIONS):
            answer = asyncio.create_task(initiator.uart_get(_CMD))
            flushes.append(await _flush_us(mgr, n + 1))
            while not answer.done():
                await settled(wdt, answer)
            got = await answer
            if got is None:
                failed += 1
            elif len(got) == len(expected) and got.copy_into(scratch) and scratch == expected:
                ok += 1
            else:
                wrong += 1
    finally:
        _remove_scratch()
        listener.cancel()
        await settled(wdt, listener)
        for driver in drivers:
            driver.deinit()
    fact("config_write_link", {"transactions_ok": ok, "transactions_failed": failed, "wrong_payloads": wrong, "flush_us": flushes})


def _crc() -> "CRC16 | None":
    return CRC16() if BENCH.get("CRC_MODE", "none") == "crc16" else None


async def _drain(driver: "asy_uart_driver.UART") -> "list[int]":
    # Every frame read whole until the line is quiet: the sequence numbers of the intact ones.
    buf = bytearray(FRAME + driver.crc.length())
    intact: list[int] = []
    async with driver:
        while True:
            got = await driver.readinto_until_complete(buf, FRAME, start_timeout_ms=_QUIET_MS, timeout_ms=_QUIET_MS)
            if got is None and not driver._rx_level():
                break
            if got == FRAME and all(buf[j] == (buf[0] + j) & 0xFF for j in range(1, FRAME)):
                intact.append(buf[0])
            await asyncio.sleep_ms(0)
    return intact


def _driver(bus: "BusFacts") -> "asy_uart_driver.UART":
    return asy_uart_driver.UART(
        bus["id"], bus["tx_pin"], bus["rx_pin"], baudrate=bus["baudrate"], rxbuf=bus["rxbuf"], txbuf=bus["txbuf"], rx_ring=bus["rx_ring"],
        poll_wait_ms=bus["poll_wait_ms"], poll_idle_ms=bus["poll_idle_ms"], crc=_crc(),
    )


async def _flush_us(mgr: "cm.ConfigManager", value: int) -> int:
    # One changed value written and flushed: the flash driver's own interrupts-off window, timed.
    t0 = time.ticks_us()
    await mgr.write_config({"Value": value})
    await mgr.flush_pending()
    return time.ticks_diff(time.ticks_us(), t0)


def _frames_for(window_us: int, bus: "BusFacts", frame_bytes: int) -> int:
    return window_us * (bus["baudrate"] // 10) // (frame_bytes * 1000000) + 1


def _hold_irqs_off(window_us: int) -> None:
    # Interrupts off for the window, busy-waiting on the hardware timer, readable with interrupts off. The main mypy
    # pass reads machine as tests/machine.py, which models no IRQ state, hence the two ignores here and below.
    state = machine.disable_irq()  # type: ignore[attr-defined]
    start = time.ticks_us()
    while time.ticks_diff(time.ticks_us(), start) < window_us:
        pass
    machine.enable_irq(state)  # type: ignore[attr-defined]


def _oe(bus: "BusFacts") -> bool:
    return bool(machine.mem32[_UART_BASES[bus["id"]] + _UARTRSR] & _RSR_OE)


def _overrun_with_rxdmae_off(bus: "BusFacts") -> bool:
    # RXDMAE cleared with interrupts off, busy-waiting until UARTRSR sets OE or the bound passes; restored after.
    dmacr = _UART_BASES[bus["id"]] + _UARTDMACR
    state = machine.disable_irq()  # type: ignore[attr-defined]
    machine.mem32[dmacr] = machine.mem32[dmacr] & ~_DMACR_RXDMAE
    start = time.ticks_us()
    while not _oe(bus) and time.ticks_diff(time.ticks_us(), start) < _OE_BOUND_US:
        pass
    oe = _oe(bus)
    machine.mem32[dmacr] = machine.mem32[dmacr] | _DMACR_RXDMAE
    machine.enable_irq(state)  # type: ignore[attr-defined]
    return oe


async def _pair() -> "tuple[UARTComm, UARTComm, tuple[asy_uart_driver.UART, asy_uart_driver.UART]]":
    send_bus, recv_bus = _bus("uart_link_init"), _bus("uart_link_resp")
    drivers = (_driver(send_bus), _driver(recv_bus))
    initiator, responder = _comm(drivers[0], ROLE_INITIATOR, send_bus), _comm(drivers[1], ROLE_RESPONDER, recv_bus)
    fact("setup", {"initiator": await initiator.setup(), "responder": await responder.setup()})
    return initiator, responder, drivers


def _raw_uart(bus: "BusFacts") -> UART:
    return UART(bus["id"], baudrate=bus["baudrate"], tx=Pin(bus["tx_pin"]), rx=Pin(bus["rx_pin"]), rxbuf=bus["rxbuf"], txbuf=bus["txbuf"])


def _remove_scratch() -> None:
    try:
        os.remove(_SCRATCH_FILE)
    except OSError as e:  # no write reached flash: nothing to remove
        if e.errno != errno.ENOENT:
            fact("scratch_remove_errno", e.errno)


async def _rxdmae_window(wdt: "machine.WDT") -> None:
    # RXDMAE cleared with interrupts off until UARTRSR sets OE - the ring's error path - then a transaction fails on
    # the pending overrun and the next one succeeds.
    send_bus, recv_bus = _bus("uart_link_init"), _bus("uart_link_resp")
    drivers = (_driver(send_bus), _driver(recv_bus))
    initiator, responder = _comm(drivers[0], ROLE_INITIATOR, send_bus), _comm(drivers[1], ROLE_RESPONDER, recv_bus)
    fact("rxdmae_setup", {"initiator": await initiator.setup(), "responder": await responder.setup()})
    sender = _Sender(send_bus, _OE_BOUND_US)
    await sender.build()
    sender.start(0, sender.frames)
    oe = _overrun_with_rxdmae_off(recv_bus)
    wdt.feed()
    streamed = await sender.finished(wdt)
    first = await _transfer(wdt, initiator, responder)
    fact("rxdmae_window", {"streamed": streamed, "oe_set": oe, "first_failed": first is False, "next_ok": await _transfer(wdt, initiator, responder)})
    sender.dma.close()
    for driver in drivers:
        driver.deinit()


def _scratch_manager() -> "cm.ConfigManager":
    # Primed in RAM from its schema, no setup(): only the owned writes reach flash.
    mgr = cm.ConfigManager(_SCRATCH_FILE, _SCRATCH_SCHEMA, "HWTEST")
    mgr._cache = {field[0]: field[2] for field in _SCRATCH_SCHEMA}
    mgr.valid = True
    return mgr


async def _soft_reset() -> None:
    # Streams into the receiver's ring and returns at once: the harness's trailing soft reset lands while frames arrive.
    send_bus, recv_bus = _bus("uart_link_init"), _bus("uart_link_resp")
    _raw_uart(send_bus)
    sender = _Sender(send_bus, _RESET_STREAM_MS * 1000)
    await sender.build()
    driver = _driver(recv_bus)
    fact("setup", await _comm(driver, ROLE_RESPONDER, recv_bus).setup())
    rx = driver._rx_dma
    reload = driver._rx_reload
    fact("channels", [rx.channel, reload.channel, sender.dma.channel] if rx is not None and reload is not None else [])
    sender.start(0, sender.frames)
    print("RESET_NOW")


async def _sweep(wdt: "machine.WDT") -> None:
    send_bus, recv_bus = _bus("uart_link_init"), _bus("uart_link_resp")
    bound_us = recv_bus["rx_ring"] * 10 * 1000000 // recv_bus["baudrate"]  # a continuous sender fills the ring
    windows = _FLASH_WINDOWS_US + ((bound_us // _OVER_BOUND_STEP_US + 1) * _OVER_BOUND_STEP_US,)
    fact("ring_bound_us", bound_us)
    writer = _raw_uart(send_bus)
    sender = _Sender(send_bus, max(windows) + 2 * _STREAM_MARGIN_US, _AFTER_FRAMES)
    await sender.build()
    gc.collect()
    heap_before, largest_before = gc.mem_free(), largest_block()
    driver = _driver(recv_bus)
    fact("setup", await _comm(driver, ROLE_RESPONDER, recv_bus).setup())
    gc.collect()
    fact("heap", {"heap_before": heap_before, "heap_after": gc.mem_free(), "largest_before": largest_before, "largest_after": largest_block(), "ring_bytes": driver.rx_ring})
    try:
        records = []
        for window_us in windows:
            records.append(await _window(wdt, sender, driver, recv_bus, window_us))
        fact("windows", records)
    finally:
        sender.dma.close()
        writer.deinit()
        driver.deinit()


async def _transfer(wdt: "machine.WDT", initiator: UARTComm, responder: UARTComm) -> bool:
    listener = asyncio.create_task(responder.uart_listen())
    ok = await initiator.uart_set(_CMD, b"after")
    if not await settled(wdt, listener):
        await responder.clear()
        await settled(wdt, listener)
    return ok


async def _window(wdt: "machine.WDT", sender: _Sender, driver: "asy_uart_driver.UART", bus: "BusFacts", window_us: int) -> "dict[str, object]":
    frames = _frames_for(window_us + 2 * _STREAM_MARGIN_US, bus, sender.frame_bytes)
    laps = driver.rx_overruns
    gc.collect()  # before the window: no collection inside the record
    wdt.feed()
    # The reader drains while the stream runs, as the shipped listener does: only the window itself stops it, so the
    # ring has to hold the window's bytes alone (a reader started after the stream overran the ring at every window).
    reader = asyncio.create_task(_drain(driver))
    sender.start(0, frames)
    await asyncio.sleep_ms(_STREAM_MARGIN_US // 1000)
    _hold_irqs_off(window_us)
    oe = _oe(bus)
    wdt.feed()
    streamed = await sender.finished(wdt)
    intact = await reader
    sender.start(frames, _AFTER_FRAMES)
    streamed = await sender.finished(wdt) and streamed
    after = await _drain(driver)
    return {
        "window_us": window_us, "streamed": streamed, "frames_sent": frames, "frames_intact": len(intact),
        "overrun_detected": driver.rx_overruns - laps, "uartrsr_oe": oe, "after_sent": _AFTER_FRAMES, "after_intact": len(after),
    }


async def _main() -> None:
    wdt = arm()
    state = BENCH.get("STATE", "sweep")
    fact("crc_mode", BENCH.get("CRC_MODE", "none"))
    fact("state", state)
    fact("gc_threshold", gc.threshold())
    if state == "soft_reset":
        await _soft_reset()
    elif state == "after_soft_reset":
        await _after_soft_reset(wdt)
    elif state == "config_write":
        await _config_write(wdt)
    elif state == "break":
        await _break(wdt)
    elif state == "config_write_link":
        await _config_write_link(wdt)
    else:
        await _sweep(wdt)
        await _rxdmae_window(wdt)
    done()


asyncio.run(_main())
