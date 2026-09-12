"""Isolated-driver device script: an idle responder must poll at poll_idle_ms, not poll_wait_ms
(SPECIFICATION.md Part F.5.9). Counts real ipoll() rounds rather than timing the loop - a count is
a property of the code, while throughput on this board moves with heap state (Part E.7)."""

import asyncio
import gc

import machine

import asy_uart_driver
from asy_uart_comm import ROLE_RESPONDER, UART_Comm

BAUDRATE = 115200
POLL_WAIT_MS = 2
POLL_IDLE_MS = 50  # mirrors sensortask_dev.py's own pair
SAMPLE_MS = 3000
# Rounds expected over the sample window at each rate, and how far off is still acceptable. The
# ratio is what the finding is about, so the bound is deliberately loose on absolute counts.
_EXPECTED_IDLE_ROUNDS = SAMPLE_MS // POLL_IDLE_MS
_MIN_RATIO = 5  # measured 20.6x; anything under 5x means the idle rate is not being selected


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
    comm = UART_Comm(
        uart, ROLE_RESPONDER, payload_size=48, timeout=1000,
        get_callback=get_callback, set_callback=set_callback, name="UART_IDLE",
    )
    await comm.setup()
    listener = asyncio.create_task(comm.uart_listen())
    await asyncio.sleep_ms(100)  # let it reach the parked wait before counting
    counter.rounds = 0
    for _ in range(SAMPLE_MS // 250):
        wdt.feed()
        await asyncio.sleep_ms(250)
    rounds = counter.rounds
    await comm.clear()
    for _ in range(40):
        if listener.done():
            break
        wdt.feed()
        await asyncio.sleep_ms(10)
    if not listener.done():
        listener.cancel()
        await asyncio.sleep_ms(20)
    uart.deinit()
    return rounds


async def _main() -> None:
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
    if idle > _EXPECTED_IDLE_ROUNDS * 2 or idle < _EXPECTED_IDLE_ROUNDS // 2:
        failures.append(f"idle listener polled {idle} times in {SAMPLE_MS}ms, not near the expected {_EXPECTED_IDLE_ROUNDS}")

    if failures:
        print("RESULT: FAIL " + "; ".join(failures))
    else:
        print(f"RESULT: PASS idle poll rounds {fast_a}/{fast_b} at {POLL_WAIT_MS}ms vs {idle_a}/{idle_b} at {POLL_IDLE_MS}ms over {SAMPLE_MS}ms")


asyncio.run(_main())
