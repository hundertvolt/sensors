import asyncio
import select

from machine import UART as FakeUART

from asy_uart_driver import UART
from crc_checks import CRC16, CRC_Pass

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


def make_uart(**kwargs: "Any") -> UART:
    return UART(0, tx_pin=0, rx_pin=1, **kwargs)


def fake(uart: UART) -> FakeUART:
    return uart._uart  # type: ignore[return-value]


class _StepPoller:
    # Stands in for uart.poller in tests that need genuine control over ready()'s per-call
    # readiness. Confirmed directly against this project's MicroPython Unix-port test build: its
    # select.poll() doesn't re-check a plain Python stream object's ioctl() per call the way real
    # hardware does (register()'d readiness never changes afterward, regardless of the object's
    # actual state) - so it can't exercise a genuine not-ready -> ready transition. This bypasses
    # select.poll entirely: each ipoll() call consumes the next `steps` entry (an event bitmask, or
    # a zero-arg callable returning one - useful for feeding data as a side effect of "becoming
    # ready"), repeating the last entry once exhausted.
    def __init__(self, steps: "list[int | Any]") -> None:
        self._steps = list(steps)

    def ipoll(self, timeout_ms: int) -> "list[tuple[None, int]]":
        step = self._steps.pop(0) if len(self._steps) > 1 else self._steps[-1]
        event = step() if callable(step) else step
        return [(None, event)] if event else []

    def unregister(self, obj: "object") -> None:  # lets a step trigger deinit() without crashing on this stand-in
        pass


# ---------------------------------------------------------------------------
# init / deinit - real hardware deinit(), not just dropping the reference
# ---------------------------------------------------------------------------


def test_deinit_calls_real_hardware_deinit_and_clears_poller() -> None:
    uart = make_uart()
    fk = fake(uart)
    uart.deinit()
    assert fk.deinit_called is True
    assert uart._uart is None
    assert uart.poller is None


def test_double_deinit_is_idempotent() -> None:
    uart = make_uart()
    fk = fake(uart)
    uart.deinit()
    uart.deinit()  # must not touch the (already gone) bus a second time
    assert fk.deinit_count == 1


def test_reinit_deinits_the_previous_bus_first() -> None:
    uart = make_uart()
    first = fake(uart)
    uart.init(0, tx_pin=0, rx_pin=1)
    assert first.deinit_called is True
    assert fake(uart) is not first


def test_operations_outside_async_with_return_none_or_false() -> None:
    uart = make_uart()  # initialized, but never entered via `async with`

    async def scenario() -> None:
        assert await uart.read() is None
        assert await uart.readinto(bytearray(4)) is None
        assert await uart.readline() is None
        assert await uart.write(bytearray(b"x")) is False

    run(scenario())


def test_operations_after_deinit_return_none_or_false() -> None:
    uart = make_uart()
    uart.deinit()

    async def scenario() -> None:
        assert await uart.read() is None
        assert await uart.read_until_complete(4) is None
        assert await uart.readinto(bytearray(4)) is None
        assert await uart.readinto_until_complete(bytearray(4), 4) is None
        assert await uart.readline() is None
        assert await uart.readline_until_complete() is None
        assert await uart.write(bytearray(b"x")) is False
        assert await uart.writefrom(bytearray(b"x"), 1) is False
        assert await uart.ready(select.POLLIN) is False

    run(scenario())


# ---------------------------------------------------------------------------
# async context manager - lock acquire/release
# ---------------------------------------------------------------------------


def test_async_with_acquires_and_releases_lock() -> None:
    uart = make_uart()
    assert uart.asy_lock.locked() is False

    async def scenario() -> None:
        async with uart:
            assert uart.asy_lock.locked() is True
        assert uart.asy_lock.locked() is False

    run(scenario())


# ---------------------------------------------------------------------------
# ready() / cancel_read_timeout()
# ---------------------------------------------------------------------------


def test_ready_returns_true_once_data_is_available() -> None:
    uart = make_uart()
    uart.poller = _StepPoller([select.POLLIN])  # type: ignore[assignment]
    assert run(uart.ready(select.POLLIN, timeout_ms=200)) is True


def test_ready_times_out_when_nothing_arrives() -> None:
    uart = make_uart()
    uart.poller = _StepPoller([0])  # type: ignore[assignment]  # never ready - see _StepPoller's own docstring
    assert run(uart.ready(select.POLLIN, timeout_ms=20)) is False


def test_ready_survives_a_concurrent_deinit_mid_loop() -> None:
    # Regression test: ready() used to check self._uart/self.poller for None only once, at entry,
    # then loop indefinitely calling self.poller.ipoll(0) - a concurrent deinit() mid-loop nulled
    # self.poller and crashed the next iteration with AttributeError. Fixed to re-check every
    # iteration, matching asy_udp_socket.py's own ready() (see BACKLOG.md).
    uart = make_uart()

    def deinit_mid_loop() -> int:
        uart.deinit()
        return 0

    uart.poller = _StepPoller([0, deinit_mid_loop])  # type: ignore[assignment]

    async def scenario() -> bool:
        async with uart:
            result = await uart.ready(select.POLLIN, timeout_ms=200)
        return result

    assert run(scenario()) is False  # must not raise


def test_cancel_read_timeout_returns_false_if_not_locked() -> None:
    uart = make_uart()
    assert run(uart.cancel_read_timeout()) is False


def test_cancel_read_timeout_unblocks_a_pending_wait() -> None:
    uart = make_uart()
    uart.poller = _StepPoller([0])  # type: ignore[assignment]  # never ready on its own - see _StepPoller's own docstring

    async def waiter() -> bytes | None:
        async with uart:
            result = await uart.read(timeout_ms=-1)  # waits forever unless cancelled
        return result

    async def scenario() -> tuple[bytes | None, bool]:
        task = asyncio.create_task(waiter())
        await asyncio.sleep_ms(5)  # let waiter enter ready()'s poll loop, holding the lock
        cancelled = await uart.cancel_read_timeout()
        result = await asyncio.wait_for(task, 2)
        return result, cancelled

    result, cancelled = run(scenario())
    assert result is None
    assert cancelled is True


# ---------------------------------------------------------------------------
# read / readinto / readline - single-round
# ---------------------------------------------------------------------------


def test_read_returns_bytes_once_ready() -> None:
    uart = make_uart()
    fake(uart).feed_rx(b"hello")

    async def scenario() -> bytes | None:
        async with uart:
            result = await uart.read()
        return result

    assert run(scenario()) == b"hello"


def test_read_returns_none_on_timeout() -> None:
    uart = make_uart()
    uart.poller = _StepPoller([0])  # type: ignore[assignment]  # never ready - see _StepPoller's own docstring

    async def scenario() -> bytes | None:
        async with uart:
            result = await uart.read(timeout_ms=20)
        return result

    assert run(scenario()) is None


def test_readinto_fills_buffer_and_returns_count() -> None:
    uart = make_uart()
    fake(uart).feed_rx(b"hi")
    buf = bytearray(4)

    async def scenario() -> int | None:
        async with uart:
            result = await uart.readinto(buf)
        return result

    assert run(scenario()) == 2
    assert bytes(buf[:2]) == b"hi"


def test_readline_returns_bytes_once_ready() -> None:
    uart = make_uart()
    fake(uart).feed_rx(b"line\n")

    async def scenario() -> bytes | None:
        async with uart:
            result = await uart.readline()
        return result

    assert run(scenario()) == b"line\n"


# ---------------------------------------------------------------------------
# read_until_complete / readinto_until_complete - multi-round assembly, CRC
# ---------------------------------------------------------------------------


def test_read_until_complete_zero_nbytes_returns_empty_immediately() -> None:
    uart = make_uart()

    async def scenario() -> bytearray | None:
        async with uart:
            result = await uart.read_until_complete(0)
        return result

    assert run(scenario()) == bytearray()


def test_read_until_complete_assembles_across_multiple_rounds() -> None:
    uart = make_uart()
    fk = fake(uart)
    fk.feed_rx(b"ab")  # round 1 sees only this

    def feed_rest_and_ready() -> int:  # round 2: more data "arrives" exactly as ready() reports it
        fk.feed_rx(b"cde")
        return select.POLLIN

    uart.poller = _StepPoller([select.POLLIN, feed_rest_and_ready])  # type: ignore[assignment]

    async def scenario() -> bytearray | None:
        async with uart:
            result = await uart.read_until_complete(5, start_timeout_ms=200, timeout_ms=200)
        return result

    assert run(scenario()) == bytearray(b"abcde")


def test_read_until_complete_default_crc_is_pass_through() -> None:
    uart = make_uart()
    assert isinstance(uart.crc, CRC_Pass)
    fake(uart).feed_rx(b"raw")

    async def scenario() -> bytearray | None:
        async with uart:
            result = await uart.read_until_complete(3)
        return result

    assert run(scenario()) == bytearray(b"raw")


def test_read_until_complete_strips_and_verifies_real_crc() -> None:
    uart = make_uart(crc=CRC16())
    framed = run(CRC16().add(bytearray(b"hello")))
    assert framed is not None
    fake(uart).feed_rx(bytes(framed))

    async def scenario() -> bytearray | None:
        async with uart:
            result = await uart.read_until_complete(5)
        return result

    assert run(scenario()) == bytearray(b"hello")


def test_read_until_complete_bad_crc_returns_none() -> None:
    uart = make_uart(crc=CRC16())
    framed = run(CRC16().add(bytearray(b"hello")))
    assert framed is not None
    framed[-1] ^= 0xFF  # corrupt the trailing CRC byte
    fake(uart).feed_rx(bytes(framed))

    async def scenario() -> bytearray | None:
        async with uart:
            result = await uart.read_until_complete(5)
        return result

    assert run(scenario()) is None


def test_readinto_until_complete_nbytes_too_large_for_buffer_returns_none() -> None:
    uart = make_uart()
    buf = bytearray(2)

    async def scenario() -> int | None:
        async with uart:
            result = await uart.readinto_until_complete(buf, 5)
        return result

    assert run(scenario()) is None


def test_readinto_until_complete_fills_buffer_and_strips_crc() -> None:
    uart = make_uart(crc=CRC16())
    framed = run(CRC16().add(bytearray(b"world")))
    assert framed is not None
    fake(uart).feed_rx(bytes(framed))
    buf = bytearray(16)

    async def scenario() -> int | None:
        async with uart:
            result = await uart.readinto_until_complete(buf, 5)
        return result

    size = run(scenario())
    assert size == 5
    assert bytes(buf[:5]) == b"world"


# ---------------------------------------------------------------------------
# readline_until_complete
# ---------------------------------------------------------------------------


def test_readline_until_complete_assembles_multi_part_line() -> None:
    uart = make_uart()
    fk = fake(uart)
    fk.feed_rx(b"partial-")  # round 1 sees only this - no \n yet

    def feed_rest_and_ready() -> int:  # round 2: the rest of the line "arrives" exactly as ready() reports it
        fk.feed_rx(b"line\n")
        return select.POLLIN

    uart.poller = _StepPoller([select.POLLIN, feed_rest_and_ready])  # type: ignore[assignment]

    async def scenario() -> bytearray | None:
        async with uart:
            result = await uart.readline_until_complete(start_timeout_ms=200, timeout_ms=200)
        return result

    assert run(scenario()) == bytearray(b"partial-line\n")


def test_readline_until_complete_survives_an_empty_readline_without_crashing() -> None:
    # Regression test for a fixed latent IndexError: `msg[-1]` on a still-empty bytearray if
    # readline() ever returns b"" while ready() still reports POLLIN. Monkeypatched directly since
    # the fake's own queue-driven readline() can't otherwise be made to return b"" while data is
    # still pending.
    uart = make_uart()
    fk = fake(uart)
    fk.feed_rx(b"ok\n")
    real_readline = fk.readline
    state = {"first": True}

    def patched_readline() -> bytes | None:
        if state["first"]:
            state["first"] = False
            return b""
        return real_readline()

    fk.readline = patched_readline  # type: ignore[method-assign]

    async def scenario() -> bytearray | None:
        async with uart:
            result = await uart.readline_until_complete(start_timeout_ms=200, timeout_ms=200)
        return result

    assert run(scenario()) == bytearray(b"ok\n")


# ---------------------------------------------------------------------------
# write / writefrom
# ---------------------------------------------------------------------------


def test_write_default_crc_is_pass_through() -> None:
    uart = make_uart()

    async def scenario() -> bool:
        async with uart:
            result = await uart.write(bytearray(b"raw"))
        return result

    assert run(scenario()) is True
    assert fake(uart).log[-1] == ("write", b"raw")


def test_write_frames_with_configured_crc() -> None:
    uart = make_uart(crc=CRC16())

    async def scenario() -> bool:
        async with uart:
            result = await uart.write(bytearray(b"hello"))
        return result

    assert run(scenario()) is True
    op, framed = fake(uart).log[-1]
    assert op == "write"
    assert framed[:5] == b"hello"
    assert len(framed) == 5 + CRC16().length()
    assert run(CRC16().check(bytearray(framed))) == bytearray(b"hello")


def test_write_waits_until_tx_becomes_writable() -> None:
    uart = make_uart()
    calls = {"n": 0}

    def not_ready_once_then_ready() -> int:
        calls["n"] += 1
        return select.POLLOUT if calls["n"] >= 2 else 0

    uart.poller = _StepPoller([not_ready_once_then_ready])  # type: ignore[assignment]

    async def scenario() -> bool:
        async with uart:
            result = await uart.write(bytearray(b"x"))
        return result

    assert run(scenario()) is True
    assert calls["n"] >= 2  # genuinely waited through at least one not-ready round, not a lucky first check


def test_writefrom_frames_with_crc_in_place() -> None:
    uart = make_uart(crc=CRC16())
    buf = bytearray(b"hello" + b"\x00" * 10)  # extra room for the trailing CRC

    async def scenario() -> bool:
        async with uart:
            result = await uart.writefrom(buf, 5)
        return result

    assert run(scenario()) is True
    op, written = fake(uart).log[-1]
    assert op == "write"
    assert written[:5] == b"hello"
    assert len(written) == 5 + CRC16().length()


def test_writefrom_buffer_too_small_for_crc_returns_false() -> None:
    uart = make_uart(crc=CRC16())
    buf = bytearray(b"hello")  # no room for the trailing CRC

    async def scenario() -> bool:
        async with uart:
            result = await uart.writefrom(buf, 5)
        return result

    assert run(scenario()) is False
    assert fake(uart).log == []  # rejected before ever touching the bus


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
