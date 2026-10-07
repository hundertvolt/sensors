"""Bench-only UART crossover-link exerciser: wraps one role's `UARTComm` over an already-built
`asy_uart_driver.UART` bus, plus the banner/echo application logic and transfer/failure counters
that have no home in the standalone protocol module itself. See SPECIFICATION.md Part J.7/A.7."""
# Not a SensorReader/SensorReaderConfig subclass, like UARTComm (agent, 2026-09-11; Part J.9) -
# resolved via buildgen.driver_registry._OVERRIDES.

import asyncio

from micropython import const

from asy_config_manager import instance_name
from asy_print_log import DEFAULT_LOG
from asy_uart_comm import CMD_SET, ROLE_INITIATOR, ROLE_RESPONDER, ResponderCallbacks, UARTComm

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    import asyncio as _asyncio
    from collections.abc import Callable
    from typing import Any

    from asy_base_classes import ErrorSource, TimerStarter
    from asy_print_log import ErrorLog, LogConfig, PrintLogHistory
    from asy_uart_driver import UART

_NAME = const("UART")
# @wiring fram_target FRAMManager log optional kwarg

# The two bench-only command ids this exerciser answers/asks across the jumper - never protocol-
# level (UARTComm itself carries no application semantics, SPECIFICATION.md Part J.1). Bench-only:
# nothing about a deployed unit's real behavior depends on either.
_CMD_BANNER = const(0x01)
_CMD_ECHO = const(0x02)
_BANNER = const(b"dev-uart-crossover")
# How often the initiator drives one real transfer across the jumper - nothing else on a live
# system ever initiates one, so without this the link would sit idle and every claim about it
# coexisting with the webserver would be a claim about an idle link (SPECIFICATION.md Part A.7).
# @tunable uart.exercise_period_ms = 1000
_EXERCISE_PERIOD_MS = const(1000)


class UARTLinkDriver:
    def __init__(
        self,
        uart: "UART | None",
        role: str,
        payload_size: int = 48,
        timeout: int = 1000,
        name_ext: str = "",
        log: "LogConfig" = DEFAULT_LOG,
        logger: "PrintLogHistory | None" = None,
    ) -> None:
        self._role = role
        self.uart = uart  # public: the digital twin reaches the underlying machine fake through it
        # (attach_crossover_jumper() needs each side's own already-built ._uart/.poller, the same
        # way it already reaches every other bus-attached instance's own bus object - see
        # digital_twin/run_generic_integration.py's _wire_uart_crossover()).
        resolved_name = instance_name(_NAME, name_ext)
        # log=/logger= forwarded into UARTComm. The protocol carries no application semantics (Part J.1), but its
        # history is real diagnostic state, so it gets the same optional-FRAM treatment as every module's logger.
        callbacks = ResponderCallbacks(self._get_callback, self._set_callback, self._message_callback) if role == ROLE_RESPONDER else None
        self._comm = UARTComm(
            uart, role, payload_size=payload_size, timeout=timeout, callbacks=callbacks, name=resolved_name, log=log, logger=logger,
        )
        self.name = self._comm.name  # matches self.pr.name - the _ModuleLike registration shape
        self.pr = self._comm.pr
        self._last_echo: bytearray | None = None
        self.initialized = False  # True once the inner UARTComm's setup() succeeded
        self._transfers = 0
        self._failures = 0

    def _get_callback(self, cmd_id: int) -> tuple[bool, bytes | None]:
        # Answers a GET across the jumper. Returns (valid, payload); withholding validity is how
        # the responder signals "no such command", which the peer sees as a withheld answer.
        if cmd_id == _CMD_BANNER:
            return True, _BANNER
        if cmd_id == _CMD_ECHO:
            return True, bytes(self._last_echo or b"")
        return False, None

    def _set_callback(self, cmd_id: int) -> tuple[bool, int | None]:
        # Accepts a SET across the jumper. Returns (valid, expected_size); None means "don't
        # care", which is what a bench echo wants.
        return (cmd_id == _CMD_ECHO), None

    async def _exercise_loop(self) -> None:
        # Drives one real GET across the jumper per period, so the link carries traffic on a live
        # system instead of only under a device script. Never raises out: uart_get() is contracted
        # to return None rather than raise, and the counters are what a failure reports through.
        while True:
            answer = await self._comm.uart_get(_CMD_BANNER)
            if answer is not None and bytes(answer) == _BANNER:
                self._transfers += 1
            else:
                self._failures += 1
            await asyncio.sleep_ms(_EXERCISE_PERIOD_MS)

    def _message_callback(self, cmd_id: int, cmd: int, payload: bytearray | None) -> None:
        # The owned listen loop's delivery point - without it the received payload has nowhere to
        # go, and the ECHO command above could only ever answer empty. The cmd check matters: an
        # answered GET for the same id also lands here, carrying no payload, and would blank it.
        if cmd == CMD_SET and cmd_id == _CMD_ECHO:
            self._last_echo = payload

    # -- starters ----------------------------------------------------------

    def get_task_starters(self) -> "list[Callable[[], _asyncio.Task[Any]]]":
        # The role decides the task set, as in UARTComm's own get_task_starters(): both ends
        # initiating has no arbitration in this protocol (Part J.2; owner, 2026-09-11). The initiating half is this
        # class's job instead - UARTComm cannot know what a caller wants to ask its peer.
        starters = self._comm.get_task_starters()
        if self._role == ROLE_INITIATOR:
            starters = starters + [self.start_asy_exercise]
        return starters

    def get_timer_starters(self) -> "list[TimerStarter]":
        return self._comm.get_timer_starters()  # empty - no machine.Timer anywhere in this file either

    def start_asy_exercise(self) -> "_asyncio.Task[None]":
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._exercise_loop())

    # -- getters -----------------------------------------------------------

    async def get_error_counter(self) -> "ErrorLog":
        return await self._comm.get_error_counter()

    def get_error_sources(self) -> "list[ErrorSource]":
        # Fan-in primitive (SPECIFICATION.md Part C.14/G.2) - delegated entirely to the inner
        # UARTComm, which already satisfies the ErrorSource surface; this wrapper
        # holds no error state of its own.
        return [self._comm]

    async def get_link_status(self) -> "dict[str, Any]":
        # Registered as a maintenance sensor, not a new /status key - that list is variable-length
        # by design, so this bench-only link reports through it without touching the shared
        # webserver (matches asy_sgp40_driver.py's own maintenance-status precedent).
        return {"Transfers": self._transfers, "Failures": self._failures}

    def get_loggers(self) -> "list[PrintLogHistory]":
        return [self._comm.pr]

    # -- others ------------------------------------------------------------

    async def reset_error_counter(self) -> None:
        await self._comm.reset_error_counter()
        self._transfers = 0
        self._failures = 0

    async def setup(self) -> bool:
        if await self._comm.setup():
            self.initialized = True
        return self.initialized
