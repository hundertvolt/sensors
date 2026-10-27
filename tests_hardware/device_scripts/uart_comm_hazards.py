"""Isolated-driver device script: the UART link's comm hazards across the bench board's crossover jumper - two
initiations on one instance (H1a), clear()/cancel_read_timeout() racing a transaction (H1b), both ends transmitting
(H2), first-chunk field boundaries (H3) and a stalled TX - each reported as facts for the host test to judge."""
# The injector object is the only fault source, as in uart_crossover_recovery.py; the UART fault catalog itself is
# mock-only (no injection hardware will be bought, owner, 2026-09-22). BENCH["part"] "h1h2" runs the bench subset.

import asyncio
import time

import asy_uart_driver
from asy_crc_checks import CRC16
from asy_uart_comm import CMD_SET, DEFAULT_LIMITS, ROLE_INITIATOR, ROLE_RESPONDER, ResponderCallbacks, TransferLimits, UARTComm

# @include _shared/facts.py
# @include _shared/watchdog.py
# @include _shared/settle.py
# @include _shared/isl_error_log.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine

    import machine
    from _shared.facts import done, fact
    from _shared.isl_error_log import log_record
    from _shared.settle import settled
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts, BusFacts

    from asy_uart_comm import ListenResult

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# A short-timeout pair polling at 2 ms both ways, so the timeout's 30 ms floor (J.6) holds with margin.
PAYLOAD_SIZE = 48
TIMEOUT_MS = 100
_POLL_MS = 2
_CMD_ECHO = 0x02
_CMD_ID = 0x07  # the command id the raw first chunks carry
_FRAME = 5 + PAYLOAD_SIZE  # header and payload (J.3)
_GET = 0x02  # the wire's GET command byte (J.3)
_ACK = 0x01  # the wire's ACK command byte (J.3)
_TRAIN_BYTES = PAYLOAD_SIZE * 2 + 7  # three data chunks: room for a mid-train race
# A rejected frame is answered by silence: each verdict waits the responder's timeout and its resync window past it.
# @tunable l3.uart_comm_hazards_quiet_window_ms = 300
_QUIET_WINDOW_MS = 300
# The fields of a first-chunk SET and the boundary values each is swept over: the L2 field sweep's CRC arm set.
_H3_FIELDS = (
    ("cmd", 1, (0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0xFF)),
    ("size", 2, (0, 1, 2, 8, 9, 255)),
    ("chunks", 3, (0, 1, 2, 255)),
    ("cur_chunk", 4, (0, 1, 2, 255)),
    ("uid", 0, (0x00, 0xFE, 0xFF)),
)
# @tunable l3.uart_comm_hazards_recovery_attempts = 2
_RECOVERY_ATTEMPTS = 2  # after H2 or the stalled TX, both ends recover within this many attempts
# The stalled TX: the initiator's line re-initialised this slow, so a filler is still draining when the frame is due.
_STALL_BAUD = 300
_STALL_FILLER_BYTES = 32
# After the stall the slow bytes already on the wire reach the responder: the line is let go quiet before the next one.
_STALL_SETTLE_MS = (_STALL_FILLER_BYTES + _FRAME) * 10 * 1000 // _STALL_BAUD + _QUIET_WINDOW_MS


class _Recorder:
    # Wraps the responder driver's frame read and keeps what each call returned: a frame read whole, or not.
    def __init__(self, driver: "asy_uart_driver.UART") -> None:
        self._read = driver.readinto_until_complete
        self.seen = 0
        self.whole = 0

    async def __call__(self, buf: bytearray, nbytes: int, start_timeout_ms: int = -1, timeout_ms: int = -1) -> "int | None":
        got = await self._read(buf, nbytes, start_timeout_ms=start_timeout_ms, timeout_ms=timeout_ms)
        if got is not None:
            self.seen += 1
            if got == _FRAME and buf[1] in (_GET, CMD_SET) and 1 <= buf[4] <= buf[3]:
                self.whole += 1
        return got


class _Pair:
    # The two instances on the crossover jumper, and the faults made with their own peripherals.
    def __init__(self) -> None:
        crc = BENCH.get("CRC_MODE", "none") == "crc16"
        self.buses: list[BusFacts] = [BENCH["bus"][BENCH["instances"][label]["bus"]] for label in ("uart_link_init", "uart_link_resp")]
        self.drivers = [self._driver(bus, crc=crc) for bus in self.buses]
        limits = TransferLimits(PAYLOAD_SIZE, TIMEOUT_MS, DEFAULT_LIMITS.chunk_bytes, DEFAULT_LIMITS.max_transfer_bytes)
        self.initiator = UARTComm(self.drivers[0], ROLE_INITIATOR, limits=limits, name="UART_INIT")
        self.responder = UARTComm(self.drivers[1], ROLE_RESPONDER, limits=limits, callbacks=ResponderCallbacks(lambda _c: (True, b"h"), lambda _c: (True, None), None), name="UART_RESP")
        self.recorder = _Recorder(self.drivers[1])
        self.drivers[1].readinto_until_complete = self.recorder  # type: ignore[method-assign]

    @staticmethod
    def _driver(bus: "BusFacts", *, crc: bool) -> "asy_uart_driver.UART":
        return asy_uart_driver.UART(
            bus["id"], bus["tx_pin"], bus["rx_pin"], baudrate=bus["baudrate"], rxbuf=bus["rxbuf"], txbuf=bus["txbuf"], rx_ring=bus["rx_ring"],
            poll_wait_ms=_POLL_MS, poll_idle_ms=_POLL_MS, crc=CRC16() if crc else None,
        )

    async def ack_seen(self) -> bool:
        # The initiator's raw driver: an ACK frame back within the quiet window, or silence.
        driver = self.drivers[0]
        buf = bytearray(_FRAME + driver.crc.length())
        async with driver:
            got = await driver.readinto_until_complete(buf, _FRAME, start_timeout_ms=_QUIET_WINDOW_MS, timeout_ms=TIMEOUT_MS)
        return got == _FRAME and buf[1] == _ACK

    def reinit_initiator(self, baudrate: int) -> None:
        bus = self.buses[0]
        self.drivers[0].init(bus["id"], bus["tx_pin"], bus["rx_pin"], baudrate=baudrate, rxbuf=bus["rxbuf"], txbuf=bus["txbuf"], rx_ring=bus["rx_ring"])

    async def write_raw(self, side: int, frame: bytearray) -> bool:
        driver = self.drivers[side]
        async with driver:
            return await driver.write(frame, timeout_ms=TIMEOUT_MS)


async def _clean(wdt: "machine.WDT", pair: _Pair) -> bool:
    return (await _listened(wdt, pair, pair.initiator.uart_set(_CMD_ECHO, b"ok")))[0]


async def _h1a(wdt: "machine.WDT", pair: _Pair) -> None:
    # Two initiations at once on one instance: one completes, the other is refused as re-entrant; whole frames only.
    await pair.initiator.reset_error_counter()
    seen, whole = pair.recorder.seen, pair.recorder.whole
    listener = pair.responder.start_asy_listen()
    first = asyncio.create_task(pair.initiator.uart_set(_CMD_ECHO, bytes(_TRAIN_BYTES)))
    second = asyncio.create_task(pair.initiator.uart_set(_CMD_ECHO, b"second"))
    while not (first.done() and second.done()):
        await settled(wdt, first)
        await settled(wdt, second)
    listener.cancel()
    await settled(wdt, listener)
    fact("h1a", {
        "results": [await first, await second], "log": log_record(await pair.initiator.get_error_counter(), pair.initiator.name),
        "frames_seen": pair.recorder.seen - seen, "frames_whole": pair.recorder.whole - whole,
    })


async def _h1b(wdt: "machine.WDT", pair: _Pair) -> None:
    races = []
    for point in ("clear_before_first_frame", "clear_mid_train", "clear_after_last_ack", "cancel_read_timeout_mid_train"):
        races.append(await _race(wdt, pair, point))
    fact("h1b", races)


async def _h2(wdt: "machine.WDT", pair: _Pair) -> None:
    # The responder writes a raw GET while the initiator awaits its ACK: logged as peer-initiated, then both recover.
    await pair.initiator.reset_error_counter()
    task = asyncio.create_task(pair.initiator.uart_set(_CMD_ECHO, b"crossing"))
    responder_bus = pair.drivers[1]
    deadline = time.ticks_add(time.ticks_ms(), TIMEOUT_MS)
    while not responder_bus._rx_level() and time.ticks_diff(deadline, time.ticks_ms()) > 0:
        await asyncio.sleep_ms(0)  # the initiator's frame has reached the responder's ring: its ACK is due
    get = bytearray(_FRAME)
    get[0], get[1], get[2], get[3], get[4], get[5] = 0, _GET, 1, 1, 1, _CMD_ID
    wrote = await pair.write_raw(1, get)
    while not task.done():
        await settled(wdt, task)
    failed = await task is False
    attempts, recovered = await _recover(wdt, pair)
    fact("h2", {"raw_get_written": wrote, "failed": failed, "log": log_record(await pair.initiator.get_error_counter(), pair.initiator.name), "attempts": attempts, "recovered": recovered})


async def _h3(wdt: "machine.WDT", pair: _Pair) -> None:
    # Each boundary value in a legal first-chunk SET, from the initiator's raw driver to a listening responder:
    # whether an ACK came back, and one clean exchange after each field's sweep.
    sweeps = []
    for name, offset, values in _H3_FIELDS:
        verdicts = []
        for value in values:
            frame = bytearray(_FRAME)
            frame[0], frame[1], frame[2], frame[3], frame[4], frame[5] = 1, CMD_SET, 1, 2, 1, _CMD_ID
            frame[offset] = value
            listener = asyncio.create_task(pair.responder.uart_listen())
            await asyncio.sleep_ms(_POLL_MS)
            written = await pair.write_raw(0, frame)
            verdicts.append([value, written and await pair.ack_seen()])
            if not await settled(wdt, listener):
                await pair.responder.clear()
                await settled(wdt, listener)
        sweeps.append({"field": name, "verdicts": verdicts, "clean_after": await _clean(wdt, pair)})
    fact("h3", sweeps)


async def _listened(wdt: "machine.WDT", pair: _Pair, work: "Coroutine[object, object, bool]") -> "tuple[bool, ListenResult | None]":
    # One transaction against a listener started for it; the listener joined with clear(), the documented unstick
    # (SPECIFICATION.md Part J.5), or cancelled. Returns the transaction's result and what the listener returned.
    listener = asyncio.create_task(pair.responder.uart_listen())
    task = asyncio.create_task(work)
    while not task.done():
        await settled(wdt, task)
    if not await settled(wdt, listener):
        await pair.responder.clear()
    if not await settled(wdt, listener):
        listener.cancel()
        await settled(wdt, listener)
        return await task, None
    return await task, await listener


async def _race(wdt: "machine.WDT", pair: _Pair, point: str) -> "dict[str, object]":
    # One racing call at one point of a three-chunk SET; the transaction completes or fails cleanly, the next succeeds.
    listener = asyncio.create_task(pair.responder.uart_listen())
    if point == "clear_before_first_frame":
        await pair.responder.clear()
    task = asyncio.create_task(pair.initiator.uart_set(_CMD_ECHO, bytes(_TRAIN_BYTES)))
    if point in ("clear_mid_train", "cancel_read_timeout_mid_train"):
        seen = pair.recorder.seen
        deadline = time.ticks_add(time.ticks_ms(), TIMEOUT_MS)
        while pair.recorder.seen == seen and time.ticks_diff(deadline, time.ticks_ms()) > 0:
            await asyncio.sleep_ms(_POLL_MS)
        if point == "clear_mid_train":
            await pair.responder.clear()
        else:
            await pair.drivers[1].cancel_read_timeout()
    while not task.done():
        await settled(wdt, task)
    if point == "clear_after_last_ack":
        await pair.responder.clear()
    if not await settled(wdt, listener):
        await pair.responder.clear()
        await settled(wdt, listener)
    return {"point": point, "result": await task, "next_ok": await _clean(wdt, pair)}


async def _recover(wdt: "machine.WDT", pair: _Pair) -> "tuple[int, bool]":
    # A clean exchange after a fault, the responder cleared before each try: how many tries it took, within the bound.
    attempts = 0
    recovered = False
    while attempts < _RECOVERY_ATTEMPTS and not recovered:
        attempts += 1
        await pair.responder.clear()
        recovered = await _clean(wdt, pair)
    return attempts, recovered


async def _stalled_tx(wdt: "machine.WDT", pair: _Pair) -> None:
    # A TX that cannot drain: the initiator's line slowed so a filler is still going out when its frame is due.
    await pair.initiator.reset_error_counter()
    pair.reinit_initiator(_STALL_BAUD)
    filled = await pair.write_raw(0, bytearray(_STALL_FILLER_BYTES))
    failed = (await _listened(wdt, pair, pair.initiator.uart_set(_CMD_ECHO, b"stalled")))[0] is False
    log = log_record(await pair.initiator.get_error_counter(), pair.initiator.name)
    pair.reinit_initiator(pair.buses[0]["baudrate"])
    await fed_sleep_ms(wdt, _STALL_SETTLE_MS)
    attempts, recovered = await _recover(wdt, pair)
    fact("stalled_tx", {"filled": filled, "failed": failed, "log": log, "attempts": attempts, "recovered": recovered})


async def _main() -> None:
    wdt = arm()
    part = BENCH.get("part", "all")
    fact("crc_mode", BENCH.get("CRC_MODE", "none"))
    fact("part", part)
    pair = _Pair()
    setups = {"initiator": await pair.initiator.setup(), "responder": await pair.responder.setup()}
    fact("setup", setups)
    try:
        if all(setups.values()):
            await _h1a(wdt, pair)
            await _h1b(wdt, pair)
            await _h2(wdt, pair)
            if part == "all":
                await _h3(wdt, pair)
                await _stalled_tx(wdt, pair)
    finally:
        for driver in pair.drivers:
            driver.deinit()
    done()


asyncio.run(_main())
