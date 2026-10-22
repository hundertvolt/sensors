"""Isolated-driver device script: an idle responder must poll at poll_idle_ms, not poll_wait_ms (SPECIFICATION.md
Part F.5.9). Counts the driver's real readiness rounds rather than timing the loop - a count is a property of the
code, while throughput on this board moves with heap state (Part E.7). Facts out; the host test judges."""

import asyncio
import gc
import time

import asy_uart_driver
from asy_uart_comm import ROLE_RESPONDER, ResponderCallbacks, UARTComm

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable

    import machine
    from _shared.facts import done, fact
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts, BusFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# @tunable l3.uart_idle_poll_rate_sample_ms = 3000
_SAMPLE_MS = 3000
# @tunable l3.uart_idle_poll_rate_min_ratio = 5
_MIN_RATIO = 5  # measured 20.6x; anything under 5x means the idle rate is not being selected
# @tunable l3.uart_idle_poll_rate_expected_rounds_factor = 2
_EXPECTED_ROUNDS_FACTOR = 2
# The listener has reached its parked wait once its round counter moved: a deadline, not a fixed settle.
# @tunable l3.uart_idle_poll_rate_park_settle_ms = 500
_PARK_SETTLE_MS = 500
# @tunable l3.uart_idle_poll_rate_cancel_settle_ms = 400
_CANCEL_SETTLE_MS = 400
# @tunable l3.uart_idle_poll_rate_stop_poll_ms = 10
_STOP_POLL_MS = 10


class _CountingLevel:
    # Stands in for the driver's ring-level read, which every readiness round makes once: one call, one round.
    def __init__(self, inner: "Callable[[], int]") -> None:
        self._inner = inner
        self.rounds = 0

    def __call__(self) -> int:
        self.rounds += 1
        return self._inner()


async def _count_rounds(wdt: "machine.WDT", bus: "BusFacts", idle_ms: int) -> "tuple[bool, int, bool]":
    # The responder's UART alone: nothing drives the other end, so the line is genuinely silent and the listener
    # parks in the one deadline-less wait this protocol issues. The third value: the listener outlived clear()'s resync.
    gc.collect()
    uart = asy_uart_driver.UART(
        bus["id"], bus["tx_pin"], bus["rx_pin"], baudrate=bus["baudrate"], rxbuf=bus["rxbuf"], txbuf=bus["txbuf"], rx_ring=bus["rx_ring"],
        poll_wait_ms=bus["poll_wait_ms"], poll_idle_ms=idle_ms,
    )
    comm = UARTComm(uart, ROLE_RESPONDER, callbacks=ResponderCallbacks(get_callback, set_callback, None), name="UART_IDLE")
    ready = await comm.setup()
    counter = _CountingLevel(uart._rx_level)
    uart._rx_level = counter  # type: ignore[method-assign]
    listener = asyncio.create_task(comm.uart_listen())
    await _until(wdt, lambda: counter.rounds > 0, _PARK_SETTLE_MS)
    counter.rounds = 0
    await fed_sleep_ms(wdt, _SAMPLE_MS)
    rounds = counter.rounds
    await comm.clear()
    # The cancelled listen resyncs (J.5: drain until quiet), so it ends one quiet window after clear(), not at once.
    outlived = not await _until(wdt, listener.done, comm._resync_window_ms() + _CANCEL_SETTLE_MS)
    if outlived:
        listener.cancel()
        await _until(wdt, listener.done, _CANCEL_SETTLE_MS)
    uart.deinit()
    return ready, rounds, outlived


async def _until(wdt: "machine.WDT", check: "Callable[[], bool]", bound_ms: int) -> bool:
    deadline = time.ticks_add(time.ticks_ms(), bound_ms)
    while not check() and time.ticks_diff(deadline, time.ticks_ms()) > 0:
        wdt.feed()
        await asyncio.sleep_ms(_STOP_POLL_MS)
    return check()


def get_callback(cmd_id: int) -> "tuple[bool, bytes | None]":
    return True, b"v"


def set_callback(cmd_id: int) -> "tuple[bool, int | None]":
    return True, None


async def _main() -> None:
    wdt = arm()
    bus = BENCH["bus"][BENCH["instances"]["uart_link_resp"]["bus"]]
    # Interleaved: a single ordered pass cannot separate a real effect from drift (Part E.7). The fast arm states
    # idle = wait explicitly, the idle arm the TOML's own pair.
    fast_a = await _count_rounds(wdt, bus, bus["poll_wait_ms"])
    idle_a = await _count_rounds(wdt, bus, bus["poll_idle_ms"])
    fast_b = await _count_rounds(wdt, bus, bus["poll_wait_ms"])
    idle_b = await _count_rounds(wdt, bus, bus["poll_idle_ms"])
    fact("setup", [arm_result[0] for arm_result in (fast_a, idle_a, fast_b, idle_b)])
    fact("fast_rounds", [fast_a[1], fast_b[1]])
    fact("idle_rounds", [idle_a[1], idle_b[1]])
    fact("listener_cancelled", [arm_result[2] for arm_result in (fast_a, idle_a, fast_b, idle_b)])
    fact("sample_ms", _SAMPLE_MS)
    fact("expected_idle_rounds", _SAMPLE_MS // bus["poll_idle_ms"])
    fact("expected_rounds_factor", _EXPECTED_ROUNDS_FACTOR)
    fact("min_ratio", _MIN_RATIO)
    done()


asyncio.run(_main())
