"""Bench-only UART crossover-link exerciser: wraps one role's `UARTComm` over an already-built
`asy_uart_driver.UART` bus, plus the banner/echo application logic and transfer/failure counters
that have no home in the standalone protocol module itself. See SPECIFICATION.md Part J.7/A.7."""
# Not a SensorReader/SensorReaderConfig subclass, like UARTComm (agent, 2026-09-11; Part J.9) -
# resolved via buildgen.driver_registry._OVERRIDES.

import asyncio

from micropython import const

from asy_base_classes import COUNTER_CAP
from asy_config_manager import instance_name
from asy_print_log import DEFAULT_LOG, report_if_fatal
from asy_uart_comm import CMD_SET, DEFAULT_LIMITS, ROLE_INITIATOR, ROLE_RESPONDER, ResponderCallbacks, UARTComm

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from asy_base_classes import ErrorSource, JsonDict, JsonValue, PieceBuffer, TaskStarter, TimerStarter
    from asy_print_log import ErrorLog, LogConfig, PrintLogHistory
    from asy_uart_comm import TransferLimits
    from asy_uart_driver import UART

_NAME = const("UART")
_ERR_UNEXPECTED = const(23)  # the catalog's shared code: an exception reached a task's top
# @wiring fram_target FRAMManager log optional kwarg

# The two bench-only command ids this exerciser answers/asks across the jumper - never protocol-
# level (UARTComm itself carries no application semantics, SPECIFICATION.md Part J.1). Bench-only:
# nothing about a deployed unit's real behavior depends on either.
_CMD_BANNER = const(0x01)
_CMD_ECHO = const(0x02)
_BANNER = const(b"uart-crossover")  # names the jumper it crosses, never a board variant
# How often the initiator drives one real transfer across the jumper - nothing else on a live
# system ever initiates one, so without this the link would sit idle and every claim about it
# coexisting with the webserver would be a claim about an idle link (SPECIFICATION.md Part A.7).
# @tunable uart.exercise_period_ms = 1000
_EXERCISE_PERIOD_MS = const(1000)
# Hazard mode (owner, 2026-10-21, asked "Leave the UART hazards under API load untested?": "b - system shall be proven
# stable unter max load allover"). Its form (agent, 2026-10-21): a dispatch-only request runs the bench hazard script's
# set once from this end via the protocol's own API, then the echo resumes; never persisted, so no boot starts in it.
_WIRE_ACK = const(0x01)  # the wire's ACK and GET command bytes (J.3), for the raw first chunks below
_WIRE_GET = const(0x02)
_HAZARD_CMD_ID = const(0x07)  # the command id the raw first chunks carry
_HEADER_BYTES = const(5)  # uid, cmd, size, chunks, cur_chunk (J.3)
# In reply budgets: an answered frame's wait, past the peer's train timeout and resync window (2.5, J.6), as the bench
# script's; and the ACK window and pre-recovery wait, past its longest listen backoff too (5 more, J.5).
# @tunable uart.hazard_quiet_timeouts = 3
_QUIET_TIMEOUTS = const(3)
# @tunable uart.hazard_window_timeouts = 8
_WINDOW_TIMEOUTS = const(8)
# @tunable uart.hazard_recovery_attempts = 2
_HAZARD_RECOVERY_ATTEMPTS = const(2)  # after a hazard, a clean exchange within this many tries
# Each field of a legal first-chunk SET and the boundary values it is swept over: the bench hazard script's set.
_HAZARD_FIELDS = (
    ("cmd", 1, (0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0xFF)),
    ("size", 2, (0, 1, 2, 8, 9, 255)),
    ("chunks", 3, (0, 1, 2, 255)),
    ("cur_chunk", 4, (0, 1, 2, 255)),
    ("uid", 0, (0x00, 0xFE, 0xFF)),
)


class UARTLinkDriver:
    def __init__(
        self,
        uart: "UART | None",
        role: str,
        limits: "TransferLimits" = DEFAULT_LIMITS,
        name_ext: str = "",
        log: "LogConfig" = DEFAULT_LOG,
        logger: "PrintLogHistory | None" = None,
    ) -> None:
        self._role = role
        resolved_name = instance_name(_NAME, name_ext)
        # log=/logger= forwarded into UARTComm. The protocol carries no application semantics (Part J.1), but its
        # history is real diagnostic state, so it gets the same optional-FRAM treatment as every module's logger.
        callbacks = ResponderCallbacks(self._get_callback, self._set_callback, self._message_callback) if role == ROLE_RESPONDER else None
        self._comm = UARTComm(
            uart, role, limits=limits, callbacks=callbacks, name=resolved_name, log=log, logger=logger,
        )
        self._uart = uart  # the hazard run's raw frames go out on the comm's own bus, under its own lock
        self._frame = _HEADER_BYTES + limits.payload_size
        self._timeout = limits.timeout
        self._quiet_ms = _QUIET_TIMEOUTS * limits.timeout
        self._window_ms = _WINDOW_TIMEOUTS * limits.timeout
        self._train = limits.payload_size * 2 + 7  # three data chunks, the bench hazard script's train
        self._hazard_pending = False
        self._hazard_runs = 0
        self._hazard_facts: JsonDict | None = None
        self.name = self._comm.name  # matches self.pr.name - the _ModuleLike registration shape
        self.pr = self._comm.pr
        self._last_echo: PieceBuffer | None = None
        self._banner_check = bytearray(len(_BANNER))  # the exercise loop's comparison scratch, allocated once
        self.initialized = False  # True once the inner UARTComm's setup() succeeded
        self._transfers = 0
        self._failures = 0

    def _get_callback(self, cmd_id: int) -> tuple[bool, bytes | bytearray | None]:
        # Answers a GET across the jumper. Returns (valid, payload); withholding validity is how
        # the responder signals "no such command", which the peer sees as a withheld answer.
        if cmd_id == _CMD_BANNER:
            return True, _BANNER
        if cmd_id == _CMD_ECHO:
            stored = self._last_echo
            if stored is None:
                return True, b""
            # The stored echo is a PieceBuffer (no buffer protocol): one copy-out, bounded by the receive cap,
            # answers the GET.
            echo = bytearray(len(stored))
            return stored.copy_into(echo), echo
        return False, None

    def _set_callback(self, cmd_id: int) -> tuple[bool, int | None]:
        # Accepts a SET across the jumper. Returns (valid, expected_size); None means "don't
        # care", which is what a bench echo wants.
        return (cmd_id == _CMD_ECHO), None

    async def _cross_both_ends(self, frame: bytearray) -> "list[JsonValue]":
        # Both ends transmitting (out of contract, J.2): a raw GET, uid 0, and at once a SET, whose ACK slot gets the GET's ACK.
        # The SET must fail: no ACK for a stale uid, or peer-initiated at the peer's answer when its uid is 0 too; then recover.
        frame[0], frame[1], frame[2], frame[3], frame[4], frame[5] = 0, _WIRE_GET, 1, 1, 1, _CMD_BANNER
        wrote = await self._write_raw(frame)
        crossed = await self._comm.uart_set(_CMD_ECHO, b"crossing")
        attempts, recovered = await self._recover()
        return [wrote, crossed, attempts, recovered]

    async def _exercise_loop(self) -> None:
        # Drives one real GET across the jumper per period, so the link carries traffic on a live system instead of only
        # under a device script. Never raises out (uart_get() answers None); ends, like the responder's listen loop, when
        # setup() failed: the supervisor's restart escalation is the path to a reboot for a link that cannot come up (C.7.2).
        while self.initialized:
            if self._hazard_pending:
                await self._run_hazards()  # one bounded run in place of a round, then the echo resumes at once
            answer = await self._comm.uart_get(_CMD_BANNER)
            if answer is not None and len(answer) == len(_BANNER) and answer.copy_into(self._banner_check) and self._banner_check == _BANNER:
                if self._transfers < COUNTER_CAP:
                    self._transfers += 1
            elif self._failures < COUNTER_CAP:
                self._failures += 1
            await asyncio.sleep_ms(_EXERCISE_PERIOD_MS)

    async def _initiate(self, payload: bytes) -> bool | None:
        # One of the two initiations at once, as its own task: its top logs a raise, and the verdict reads None for it.
        try:
            return await self._comm.uart_set(_CMD_ECHO, payload)
        except Exception as e:  # an unsupervised task's top: never raises, so the run goes on to its next hazard
            report_if_fatal(e)
            await self.pr.err_s("Hazard initiation failed:", e, errno=_ERR_UNEXPECTED)
            return None

    def _message_callback(self, cmd_id: int, cmd: int, payload: "PieceBuffer | None") -> None:
        # The owned listen loop's delivery point - without it the received payload has nowhere to
        # go, and the ECHO command above could only ever answer empty. The cmd check matters: an
        # answered GET for the same id also lands here, carrying no payload, and would blank it.
        if cmd == CMD_SET and cmd_id == _CMD_ECHO:
            self._last_echo = payload

    async def _read_raw(self, buf: bytearray) -> int | None:
        # One frame back within the window, or None for silence: a frame that waited out the peer's backoff is still read.
        bus = self._uart  # the comm's own bus and lock (C.8); _run_hazards() runs nothing without one
        if bus is None:
            return None
        async with bus as device:
            return await device.readinto_until_complete(buf, self._frame, start_timeout_ms=self._window_ms, timeout_ms=self._timeout)

    async def _recover(self) -> tuple[int, bool]:
        # A clean exchange after a hazard, the peer's backoff, timeout and resync let pass before each try.
        attempts = 0
        recovered = False
        while attempts < _HAZARD_RECOVERY_ATTEMPTS and not recovered:
            attempts += 1
            await asyncio.sleep_ms(self._window_ms)
            recovered = await self._comm.uart_set(_CMD_ECHO, b"ok")
        return attempts, recovered

    async def _run_hazards(self) -> None:
        # One run in the bench script's order. Its facts replace the last run's and are judged by the reader, as the bench
        # host judges the script's (J.7); the link counters stay the echo's own.
        bus = self._uart
        try:
            if bus is None:
                return
            frame = bytearray(self._frame)
            ack = bytearray(self._frame + bus.crc.length())
            two = await self._two_initiations()
            crossed = await self._cross_both_ends(frame)
            sweep = await self._sweep_fields(frame, ack)
            self._hazard_facts = {"TwoInitiations": two, "Crossed": crossed, "FieldSweep": sweep}
            if self._hazard_runs < COUNTER_CAP:
                self._hazard_runs += 1
        finally:
            self._hazard_pending = False

    async def _sweep_fields(self, frame: bytearray, ack: bytearray) -> "list[JsonValue]":
        # Each boundary value in a legal first-chunk SET, raw from this end to the listening peer: whether an ACK came
        # back, None where the raw write failed (no verdict on the value, so the judges count it), and one clean exchange
        # after each field's sweep.
        sweep: list[JsonValue] = []
        for name, offset, values in _HAZARD_FIELDS:
            acked: list[JsonValue] = []
            for value in values:
                frame[0], frame[1], frame[2], frame[3], frame[4], frame[5] = 1, CMD_SET, 1, 2, 1, _HAZARD_CMD_ID
                frame[offset] = value
                if not await self._write_raw(frame):
                    acked.append(None)
                    continue
                got = await self._read_raw(ack)
                acked.append(got == self._frame and ack[1] == _WIRE_ACK)
                if got is not None:
                    await asyncio.sleep_ms(self._quiet_ms)  # the peer answered: its own timeout and resync pass first
            sweep.append([name, acked, (await self._recover())[1]])
        return sweep

    async def _two_initiations(self) -> "list[JsonValue]":
        # Two initiations at once on this end: one completes, the other is refused as re-entrant (J.2).
        loop = asyncio.get_event_loop()
        first = loop.create_task(self._initiate(bytes(self._train)))
        second = loop.create_task(self._initiate(b"second"))
        try:
            return [await first, await second]
        finally:
            for task in (first, second):
                if not task.done():
                    task.cancel()  # a cancelled run leaves no transaction of its own behind

    async def _write_raw(self, frame: bytearray) -> bool:
        bus = self._uart  # as _read_raw()
        if bus is None:
            return False
        async with bus as device:
            return await device.write(frame, timeout_ms=self._timeout)

    # -- starters ----------------------------------------------------------

    def get_task_starters(self) -> "list[TaskStarter]":
        # The role decides the task set, as in UARTComm's own get_task_starters(): both ends
        # initiating has no arbitration in this protocol (Part J.2; owner, 2026-09-11). The initiating half is this
        # class's job instead - UARTComm cannot know what a caller wants to ask its peer.
        starters = self._comm.get_task_starters()
        if self._role == ROLE_INITIATOR:
            starters = starters + [self.start_asy_exercise]
        return starters

    def get_timer_starters(self) -> "list[TimerStarter]":
        return self._comm.get_timer_starters()  # empty - no machine.Timer anywhere in this file either

    def start_asy_exercise(self) -> asyncio.Task[None]:
        return asyncio.get_event_loop().create_task(self._exercise_loop())

    # -- getters -----------------------------------------------------------

    async def get_error_counter(self) -> "ErrorLog":
        return await self._comm.get_error_counter()

    def get_error_sources(self) -> "list[ErrorSource]":
        # Fan-in primitive (SPECIFICATION.md Part C.14/G.2) - delegated entirely to the inner
        # UARTComm, which already satisfies the ErrorSource surface; this wrapper
        # holds no error state of its own.
        return [self._comm]

    async def get_hazard_report(self) -> "JsonDict":
        # The last run's facts (None before any), for a reader to judge; Pending holds from the request to the run's end.
        return {"Runs": self._hazard_runs, "Pending": self._hazard_pending, "Last": self._hazard_facts}

    async def get_link_status(self) -> "JsonDict":
        # Registered as a maintenance sensor, not a new /status key - that list is variable-length
        # by design, so this bench-only link reports through it without touching the shared
        # webserver (matches asy_sgp40_driver.py's own maintenance-status precedent).
        return {"Transfers": self._transfers, "Failures": self._failures}

    def get_loggers(self) -> "list[PrintLogHistory]":
        return [self._comm.pr]

    # -- others ------------------------------------------------------------

    def request_hazard_run(self) -> bool:
        # The dispatch-only command: refused on the responder, before setup() and while a run is pending. The exercise
        # loop runs it in place of its next round; nothing is stored, so a reboot always starts in the echo.
        if self._role != ROLE_INITIATOR or not self.initialized or self._hazard_pending:
            return False
        self._hazard_pending = True
        return True

    async def reset_error_counter(self) -> bool:
        return await self._comm.reset_error_counter()  # the link's history is the comm's; the counts are since boot

    async def setup(self) -> bool:
        if await self._comm.setup():
            self.initialized = True
        return self.initialized
