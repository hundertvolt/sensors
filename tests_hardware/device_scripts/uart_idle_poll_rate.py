"""Isolated-driver device script: an idle responder must poll at poll_idle_ms, not poll_wait_ms
(SPECIFICATION.md Part F.5.9). Counts real ipoll() rounds rather than timing the loop - a count is
a property of the code, while throughput on this board moves with heap state (Part E.7)."""

import asyncio
import gc

import machine

import asy_uart_driver
from asy_uart_comm import ROLE_RESPONDER, ResponderCallbacks, UARTComm

BAUDRATE = 115200
# @tunable dev.uart_poll_wait_ms = 2
POLL_WAIT_MS = 2
# @tunable dev.uart_poll_idle_ms = 50
POLL_IDLE_MS = 50  # mirrors sensortask_dev.py's own pair
# @tunable l3.uart_idle_poll_rate_sample_ms = 3000
SAMPLE_MS = 3000
# Rounds expected over the sample window at each rate, and how far off is still acceptable. The
# ratio is what the finding is about, so the bound is deliberately loose on absolute counts.
_EXPECTED_IDLE_ROUNDS = SAMPLE_MS // POLL_IDLE_MS
# @tunable l3.uart_idle_poll_rate_min_ratio = 5
_MIN_RATIO = 5  # measured 20.6x; anything under 5x means the idle rate is not being selected
# @tunable l3.uart_idle_poll_rate_sample_step_ms = 250
_SAMPLE_STEP_MS = 250
# @tunable l3.uart_idle_poll_rate_stop_poll_ms = 10
_STOP_POLL_MS = 10
# @tunable l3.uart_idle_poll_rate_stop_poll_tries = 40
_STOP_POLL_TRIES = 40
# @tunable l3.uart_idle_poll_rate_expected_rounds_factor = 2
_EXPECTED_ROUNDS_FACTOR = 2


class CountingPoller:
    # Wraps the real select.poll the driver installed, counting ipoll() calls - one per ready()
    # round. Nothing in the driver is modified, so the shipped path is what gets measured.
    def __init__(self, inner: object) -> None:
        self._inner = inner
        self.rounds = 0

    def ipoll(self, timeout_ms: int) -> object:
        self.rounds += 1
        return self._inner.ipoll(timeout_ms)  # type: ignore[attr-defined]

    def unregister(self, obj: object) -> object:
        return self._inner.unregister(obj)  # type: ignore[attr-defined]

    def register(self, obj: object, mask: int) -> object:
        return self._inner.register(obj, mask)  # type: ignore[attr-defined]


def get_callback(cmd_id: int) -> "tuple[bool, bytes | None]":
    return True, b"v"


def set_callback(cmd_id: int) -> "tuple[bool, int | None]":
    return True, None


async def _count_rounds(wdt: "machine.WDT", idle_ms: int) -> int:
    # UART1 alone: nothing drives UART0, so the line is genuinely silent and the listener parks in
    # the one deadline-less wait this protocol issues.
    gc.collect()
    uart = asy_uart_driver.UART(
        1, 8, 9, baudrate=BAUDRATE, rxbuf=512, txbuf=512, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=idle_ms,
    )
    counter = CountingPoller(uart.poller)
    uart.poller = counter  # type: ignore[assignment]
    comm = UARTComm(
        uart, ROLE_RESPONDER, payload_size=48, timeout=1000,
        callbacks=ResponderCallbacks(get_callback, set_callback, None), name="UART_IDLE",
    )
    await comm.setup()
    listener = asyncio.create_task(comm.uart_listen())
    await asyncio.sleep_ms(100)  # let it reach the parked wait before counting
    counter.rounds = 0
    for _ in range(SAMPLE_MS // _SAMPLE_STEP_MS):
        wdt.feed()
        await asyncio.sleep_ms(_SAMPLE_STEP_MS)
    rounds = counter.rounds
    await comm.clear()
    for _ in range(_STOP_POLL_TRIES):
        if listener.done():
            break
        wdt.feed()
        await asyncio.sleep_ms(_STOP_POLL_MS)
    if not listener.done():
        listener.cancel()
        await asyncio.sleep_ms(20)
    uart.deinit()
    return rounds


async def _main() -> None:
    # @tunable wdt.timeout_ms = 8000
    wdt = machine.WDT(timeout=8000)
    failures = []
    # Interleaved: a single ordered pass cannot separate a real effect from drift (Part E.7).
    fast_a = await _count_rounds(wdt, POLL_WAIT_MS)
    idle_a = await _count_rounds(wdt, POLL_IDLE_MS)
    fast_b = await _count_rounds(wdt, POLL_WAIT_MS)
    idle_b = await _count_rounds(wdt, POLL_IDLE_MS)
    fast = min(fast_a, fast_b)
    idle = max(idle_a, idle_b)

    if not idle:
        failures.append("an idle listener performed no poll rounds at all - it is not waiting where this test thinks")
    elif fast // idle < _MIN_RATIO:
        failures.append(f"idle rate cut poll rounds only {fast // idle}x ({fast} -> {idle}), under the {_MIN_RATIO}x floor")
    # The absolute rate should track poll_idle_ms, not merely be smaller - a listener that stopped
    # polling entirely would also pass the ratio check but would never notice a frame.
    if idle > _EXPECTED_IDLE_ROUNDS * _EXPECTED_ROUNDS_FACTOR or idle < _EXPECTED_IDLE_ROUNDS // _EXPECTED_ROUNDS_FACTOR:
        failures.append(f"idle listener polled {idle} times in {SAMPLE_MS}ms, not near the expected {_EXPECTED_IDLE_ROUNDS}")

    if failures:
        print("RESULT: FAIL " + "; ".join(failures))
    else:
        print(f"RESULT: PASS idle poll rounds {fast_a}/{fast_b} at {POLL_WAIT_MS}ms vs {idle_a}/{idle_b} at {POLL_IDLE_MS}ms over {SAMPLE_MS}ms")


asyncio.run(_main())
