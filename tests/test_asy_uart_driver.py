import asyncio
import select

from machine import UART as FakeUART

from asy_uart_driver import UART
from crc_checks import CRC16, CRC_Base, CRC_Pass

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
# __init__ / init() - valid parameter configurations
# ---------------------------------------------------------------------------
# Real mp_machine_uart_init_helper()/make_new() constants (see tests/machine.py's own docstring
# for the source citations - not guessed).


def test_valid_default_construction_succeeds() -> None:
    uart = make_uart()
    assert fake(uart).id == 0
    assert fake(uart).baudrate == 9600


def test_valid_construction_on_both_real_uart_ports() -> None:
    for port_id in (0, 1):  # RP2040 has exactly two UART peripherals
        uart = UART(port_id, tx_pin=0, rx_pin=1)
        assert fake(uart).id == port_id


def test_valid_buffer_size_boundaries() -> None:
    uart = make_uart(rxbuf=32, txbuf=32766)  # MIN_BUFFER_SIZE / MAX_BUFFER_SIZE, both inclusive
    assert fake(uart).rxbuf == 32
    assert fake(uart).txbuf == 32766


def test_valid_invert_mask_every_combination() -> None:
    for invert in (0, 1, 2, 3):  # every real UART_INVERT_TX | UART_INVERT_RX combination
        uart = make_uart(invert=invert)
        assert fake(uart).invert == invert


def test_valid_bits_parity_stop_pass_through_unvalidated() -> None:
    # Real mp_machine_uart_init_helper() has no raising validation at all for bits/parity/stop -
    # confirmed directly against the source (see tests/machine.py's docstring); documents that
    # asy_uart_driver.py doesn't add its own validation on top either.
    uart = make_uart(bits=9, parity=1, stop=2)
    assert fake(uart).bits == 9
    assert fake(uart).parity == 1
    assert fake(uart).stop == 2


def test_non_positive_baudrate_does_not_raise() -> None:
    # Real hardware silently ignores a non-positive baudrate (keeps the previous/default value)
    # instead of raising - confirmed directly, not guessed (see tests/machine.py's docstring). The
    # raise/no-raise contract is what this test actually checks; it doesn't claim the fake models
    # the silent-ignore/clamp behavior itself.
    uart = make_uart(baudrate=0)
    assert fake(uart).id == 0  # construction completed, nothing raised


def test_valid_crc_configurations() -> None:
    default = make_uart()
    assert isinstance(default.crc, CRC_Pass)
    explicit_pass = CRC_Pass()
    with_pass = make_uart(crc=explicit_pass)
    assert with_pass.crc is explicit_pass
    explicit_crc16 = CRC16()
    with_crc16 = make_uart(crc=explicit_crc16)
    assert with_crc16.crc is explicit_crc16


# ---------------------------------------------------------------------------
# __init__ / init() - single invalid parameter
# ---------------------------------------------------------------------------


def test_invalid_port_id_raises_value_error() -> None:
    for port_id in (-1, 2, 99):
        try:
            UART(port_id, tx_pin=0, rx_pin=1)
            raised = False
        except ValueError:
            raised = True
        assert raised


def test_invalid_tx_pin_raises_value_error() -> None:
    try:
        UART(0, tx_pin=29, rx_pin=1)  # outside the real GPIO0-28 range
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_invalid_rx_pin_raises_value_error() -> None:
    try:
        UART(0, tx_pin=0, rx_pin=-1)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_non_int_pin_raises_type_error() -> None:
    try:
        UART(0, tx_pin="0", rx_pin=1)  # type: ignore[arg-type]
        raised = False
    except TypeError:
        raised = True
    assert raised


def test_rxbuf_too_large_raises_value_error() -> None:
    try:
        make_uart(rxbuf=32767)  # one past MAX_BUFFER_SIZE
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_txbuf_too_large_raises_value_error() -> None:
    try:
        make_uart(txbuf=40000)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_bad_invert_mask_raises_value_error() -> None:
    for invert in (4, -1, 255):  # outside UART_INVERT_MASK's real 0-3 range
        try:
            make_uart(invert=invert)
            raised = False
        except ValueError:
            raised = True
        assert raised


# ---------------------------------------------------------------------------
# __init__ / init() - multiple simultaneously-invalid parameters: which
# exception surfaces first, matching real evaluation/check order
# ---------------------------------------------------------------------------


def test_bad_tx_pin_wins_over_bad_port_id() -> None:
    # asy_uart_driver.py's own init() constructs Pin(tx_pin) as a call *argument* to _UART(...),
    # so a bad tx_pin always raises before _UART()'s own body (and therefore its port_id check)
    # ever runs - a consequence of how this driver is structured, not something to assume matches
    # mp_machine_uart_make_new()'s own internal check order in isolation.
    try:
        UART(99, tx_pin=29, rx_pin=1)
        message = ""
    except ValueError as e:
        message = str(e)
    assert "pin" in message.lower()


def test_bad_port_id_wins_over_bad_rxbuf_and_invert() -> None:
    # Once inside _UART()'s own body (both pins valid), id is checked before invert/rxbuf/txbuf -
    # matches mp_machine_uart_make_new() fully checking uart_id before init_helper() ever runs.
    try:
        UART(99, tx_pin=0, rx_pin=1, rxbuf=99999, invert=255)
        message = ""
    except ValueError as e:
        message = str(e)
    assert "UART(99)" in message


def test_bad_invert_wins_over_bad_rxbuf_and_txbuf() -> None:
    # invert is checked before rxbuf/txbuf in mp_machine_uart_init_helper()'s own body.
    try:
        make_uart(invert=255, rxbuf=99999, txbuf=99999)
        message = ""
    except ValueError as e:
        message = str(e)
    assert "inversion" in message.lower()


def test_bad_rxbuf_wins_over_bad_txbuf() -> None:
    # rxbuf is checked before txbuf in mp_machine_uart_init_helper()'s own body.
    try:
        make_uart(rxbuf=99999, txbuf=99999)
        message = ""
    except ValueError as e:
        message = str(e)
    assert "rxbuf" in message.lower()


def test_multiple_invalid_pins_still_raises_cleanly() -> None:
    try:
        UART(0, tx_pin=29, rx_pin=-1)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_failed_reinit_leaves_the_bus_deinitialized_not_reverted() -> None:
    # init() always deinit()s the previous bus first (see its own comment), so a failing re-init
    # can't roll back to the previous working bus - the instance is left deinitialized until a
    # caller successfully re-inits with valid parameters. Same shape as asy_i2c_driver.py's/
    # asy_spi_driver.py's own init(), not unique to UART.
    uart = make_uart()
    try:
        uart.init(99, tx_pin=0, rx_pin=1)  # bad port_id
        raised = False
    except ValueError:
        raised = True
    assert raised
    assert uart._uart is None
    assert uart.poller is None


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


# ---------------------------------------------------------------------------
# base_classes.Lockable integration - real inheritance (UART(Lockable)), not
# mocked - mirrors test_asy_i2c_driver.py's own Lockable integration coverage
# ---------------------------------------------------------------------------


def test_exception_inside_session_still_releases_the_lock() -> None:
    uart = make_uart()

    async def scenario() -> None:
        try:
            async with uart:
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        assert not uart.asy_lock.locked()
        async with uart:  # must still be acquirable - not left stuck locked
            pass

    run(scenario())


def test_context_manager_does_not_suppress_exceptions() -> None:
    uart = make_uart()

    async def scenario() -> None:
        async with uart:
            raise ValueError("boom")

    try:
        run(scenario())
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_aexit_tolerates_a_lock_already_released_inside_the_block() -> None:
    uart = make_uart()

    async def scenario() -> None:
        async with uart:
            uart.asy_lock.release()  # released early by hand
        # __aexit__'s own release() must swallow the resulting RuntimeError, not propagate it

    run(scenario())  # must not raise
    assert not uart.asy_lock.locked()


def test_task_cancellation_while_holding_the_lock_still_releases_it() -> None:
    # Interrupts a session via real asyncio cancellation (not just an exception raised by our own
    # code) - MicroPython's asyncio still runs __aexit__ via CancelledError propagating through
    # `async with`, same as CPython (confirmed directly for I2CDevice; UART(Lockable) shares the
    # exact same __aenter__/__aexit__ implementation, not a reimplementation).
    uart = make_uart()
    started = False

    async def holder() -> None:
        nonlocal started
        async with uart:
            started = True
            await asyncio.sleep(10)

    async def scenario() -> None:
        task = asyncio.create_task(holder())
        while not started:
            await asyncio.sleep(0)
        assert uart.asy_lock.locked()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert not uart.asy_lock.locked()

    run(scenario())


def test_two_tasks_sharing_one_uart_never_run_concurrently() -> None:
    uart = make_uart()
    concurrent = 0
    max_concurrent = 0

    async def worker() -> None:
        nonlocal concurrent, max_concurrent
        async with uart:
            concurrent += 1
            max_concurrent = max(max_concurrent, concurrent)
            await asyncio.sleep(0)  # yield - if the lock didn't serialize, the other task runs here
            concurrent -= 1

    async def scenario() -> None:
        await asyncio.gather(worker(), worker())

    run(scenario())
    assert max_concurrent == 1


def test_aenter_returns_the_uart_itself() -> None:
    uart = make_uart()

    async def scenario() -> None:
        async with uart as entered:
            assert entered is uart

    run(scenario())


def test_reentrant_acquisition_deadlocks_and_cleans_up() -> None:
    # Not reentrant by design (a plain asyncio.Lock, same as I2CDevice/SPIDevice's shared bus
    # lock) - bounded by wait_for so the test itself can't hang.
    uart = make_uart()

    async def reentrant() -> None:
        async with uart:
            async with uart:
                pass

    async def scenario() -> bool:
        try:
            await asyncio.wait_for(reentrant(), 0.2)
            return False
        except asyncio.TimeoutError:
            return True

    assert run(scenario())
    assert not uart.asy_lock.locked()


# ---------------------------------------------------------------------------
# crc_checks.py integration - real CRC_Base subclasses (not mocked), plus
# MemoryError fault injection at the guarded call sites (module docstring's
# "MemoryError guarding" section)
# ---------------------------------------------------------------------------


class _MemoryErrorCRC:
    # Wraps a real CRC_Base so length() (needed by read_until_complete()'s own nbytes += ... call)
    # keeps working, while add()/check() raise MemoryError instead of doing real work - same
    # technique as test_asy_udp_socket.py's own _MemoryErrorSocketWrapper, proving
    # asy_uart_driver.py's try/except MemoryError around these two calls actually catches it.
    def __init__(self, real: "CRC_Base") -> None:
        self._real = real

    def length(self) -> int:
        return self._real.length()

    async def add(self, bytearr: bytearray, init: "int | None" = None) -> bytearray | None:
        raise MemoryError("simulated allocation failure")

    async def check(self, bytearr: bytearray, init: "int | None" = None) -> bytearray | None:
        raise MemoryError("simulated allocation failure")


def test_write_returns_false_on_crc_add_memoryerror() -> None:
    uart = make_uart(crc=CRC16())
    uart.crc = _MemoryErrorCRC(CRC16())  # type: ignore[assignment]

    async def scenario() -> bool:
        async with uart:
            result = await uart.write(bytearray(b"x"))
        return result

    assert run(scenario()) is False
    assert fake(uart).log == []  # rejected before ever touching the bus


def test_read_until_complete_returns_none_on_crc_check_memoryerror() -> None:
    uart = make_uart(crc=CRC16())
    framed = run(CRC16().add(bytearray(b"hello")))
    assert framed is not None
    fake(uart).feed_rx(bytes(framed))
    uart.crc = _MemoryErrorCRC(CRC16())  # type: ignore[assignment]

    async def scenario() -> bytearray | None:
        async with uart:
            result = await uart.read_until_complete(5)
        return result

    assert run(scenario()) is None


# `msg += add`'s own MemoryError guard in read_until_complete()/readline_until_complete() (see the
# module docstring's "MemoryError guarding" section) is deliberately NOT fault-injected here the
# same way: unlike self.crc, `msg` is a plain bytearray built and grown entirely inside those
# methods - there's no substitutable object to wrap/monkeypatch the way _MemoryErrorCRC does above,
# and bytearray.__iadd__ has no Python-level hook to force MemoryError deterministically without
# either a constrained interpreter heap (not controllable from within a running test - see
# tests/README.md) or genuinely exhausting memory (flaky/unsafe for CI). Same category of
# documented, deliberate testing gap as test_print_log.py's own
# test_history_length_huge_is_capped_instead_of_crashing_the_interpreter comment. The surrounding
# behavior is still covered: test_read_until_complete_assembles_across_multiple_rounds and
# test_readline_until_complete_assembles_multi_part_line already exercise this exact line
# successfully across multiple rounds, proving the guard doesn't break normal accumulation.


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
