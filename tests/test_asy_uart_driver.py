import asyncio
import select
import time

from machine import UART as FakeUART

from asy_uart_driver import UART
from crc_checks import CRC16, CRC_Base, CRC_Pass
from framing_codecs import COBS_DELIMITER, Framing_COBS, Framing_Pass

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":
    # Bounded via wait_for(), not a bare asyncio.run(coro): several tests below feed data via
    # feed_rx() and then call uart.read()/write() with no explicit timeout_ms, which hits
    # asy_uart_driver.py's ready()'s timeout_ms=-1 (wait forever) branch and depends entirely on
    # the real select.poll() detecting readiness via tests/machine.py's fake UART's ioctl() - the
    # one mechanism in this file not exercised through the bounded _StepPoller test double. Investigated
    # as the leading suspect for a real, reproducible CI-only hang (always this file, never locally -
    # see CLAUDE.md's "CI hang investigation" note) that 20/20 recent CI runs hit regardless of
    # per-file timeout/retry/stdbuf mitigations already in scripts/test.sh. 5s is generous next to
    # the tightest existing inner bound already in this file (wait_for(task, 2)) while guaranteeing
    # this test file itself can never hang the whole suite even if that poll path genuinely misbehaves
    # again - a TimeoutError here surfaces as a normal, fast FAIL through microtest's own exception
    # handling, not a silent stall.
    return asyncio.run(asyncio.wait_for(coro, 5))


def make_uart(**kwargs: "Any") -> UART:
    uart = UART(0, tx_pin=0, rx_pin=1, **kwargs)
    # Replaces the real select.poll() init() installs, for every UART in this file: the Unix port
    # never re-checks a Python object's ioctl() after registration, so readiness waits hang on CI
    # (CLAUDE.md). Always-ready here; tests needing a schedule reassign their own _StepPoller.
    uart.poller = _StepPoller([select.POLLIN | select.POLLOUT])  # type: ignore[assignment]
    return uart


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

    def ipoll(self, _timeout_ms: int) -> "list[tuple[None, int]]":  # asy_uart_driver.py calls ipoll(0) positionally
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
    ok = uart.deinit()
    assert fk.deinit_called is True
    assert uart._uart is None
    assert uart.poller is None
    assert ok is True


class _RaisingUnregisterPoller:
    def unregister(self, _obj: "object") -> None:  # asy_uart_driver.py calls unregister() positionally
        raise OSError("simulated poller unregister failure")


def test_deinit_swallows_poller_unregister_failure() -> None:
    uart = make_uart()
    uart.poller = _RaisingUnregisterPoller()  # type: ignore[assignment]
    ok = uart.deinit()  # must not raise despite the poller's own unregister() failing
    assert uart._uart is None
    assert uart.poller is None
    # Step 6 (silent-failure-masking finding): a failed unregister() must be reported via the
    # return value, not just silently swallowed - see asy_udp_socket.py's disconnect() for the
    # identical pattern applied to its own logger-less class.
    assert ok is False


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
# ready / cancel_read_timeout
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
            return await uart.ready(select.POLLIN, timeout_ms=200)

    assert run(scenario()) is False  # must not raise


def test_ready_returns_false_on_a_malformed_mask() -> None:
    # A non-int mask makes `event & mask` inside ready()'s own loop raise TypeError - not caught by
    # any caller's own except clause (those only wrap the real UART call, not this await) - so
    # ready() must catch it itself and degrade to False rather than propagating.
    uart = make_uart()
    uart.poller = _StepPoller([select.POLLIN])  # type: ignore[assignment]
    assert run(uart.ready("not-a-mask")) is False  # type: ignore[arg-type]


def test_cancel_read_timeout_returns_false_if_not_locked() -> None:
    uart = make_uart()
    assert run(uart.cancel_read_timeout()) is False


def test_cancel_read_timeout_unblocks_a_pending_wait() -> None:
    uart = make_uart()
    uart.poller = _StepPoller([0])  # type: ignore[assignment]  # never ready on its own - see _StepPoller's own docstring

    async def waiter() -> bytes | None:
        async with uart:
            return await uart.read(timeout_ms=-1)  # waits forever unless cancelled

    async def scenario() -> tuple[bytes | None, bool]:
        task = asyncio.create_task(waiter())
        await asyncio.sleep_ms(5)  # let waiter enter ready()'s poll loop, holding the lock
        cancelled = await uart.cancel_read_timeout()
        result = await asyncio.wait_for(task, 2)
        return result, cancelled

    result, cancelled = run(scenario())
    assert result is None
    assert cancelled is True


def test_rxbuf_and_baudrate_are_readable_back() -> None:
    # A protocol layer above has to size frames against the real receive buffer and baud rate,
    # and machine.UART exposes neither - so this driver remembers what it was constructed with.
    uart = make_uart(rxbuf=512, baudrate=115200)
    assert uart.rxbuf == 512
    assert uart.baudrate == 115200
    uart.init(0, 0, 1, rxbuf=1024, baudrate=9600)
    assert uart.rxbuf == 1024
    assert uart.baudrate == 9600


def test_no_uart_built_here_polls_through_a_real_select_poll() -> None:
    # CLAUDE.md's standing rule, asserted rather than left to review: a real select.poll() behind
    # uart.poller is the known CI-only hang, since _write_all()'s ready(POLLOUT) wait then blocks
    # forever on a runner. That is how it escaped review once - six tests green locally, red in CI.
    real_poll_type = type(select.poll()).__name__
    assert type(make_uart().poller).__name__ != real_poll_type
    assert type(cobs_uart().poller).__name__ != real_poll_type


# ---------------------------------------------------------------------------
# B3 - optional-buffer gaps and caller-buffer validation
# ---------------------------------------------------------------------------


def test_a_complete_write_reslices_nothing() -> None:
    # B3.1: the re-slice happens only after a short write has actually occurred, so the normal
    # path costs no memoryview allocation. Asserted on what the fake actually received.
    uart = make_uart()
    payload = bytearray(b"0123456789")
    assert run(locked_write(uart, payload)) is True
    writes = [entry[1] for entry in fake(uart).log if entry[0] == "write"]
    assert writes == [b"0123456789"]  # exactly one round, so no slice was ever needed


def test_a_short_write_still_completes_across_rounds() -> None:
    uart = make_uart()
    fake(uart).write_limit = 4
    payload = bytearray(b"0123456789")
    assert run(locked_write(uart, payload)) is True
    writes = [entry[1] for entry in fake(uart).log if entry[0] == "write"]
    assert b"".join(writes) == b"0123456789"
    assert len(writes) == 3  # 4 + 4 + 2, the re-slicing path this time


def test_writefrom_rejects_a_size_longer_than_the_buffer() -> None:
    # B3.2: silent truncation, or an out-of-range write, would both be worse than the sentinel.
    uart = make_uart()
    assert run(locked_writefrom(uart, bytearray(4), 8)) is False
    assert run(locked_writefrom(uart, bytearray(4), -1)) is False


def test_writefrom_rejects_a_buffer_with_no_room_for_the_crc() -> None:
    uart = make_uart(crc=CRC16())
    assert run(locked_writefrom(uart, bytearray(4), 4)) is False  # 4 payload + 2 CRC > 4
    assert run(locked_writefrom(uart, bytearray(6), 4)) is True


def test_into_methods_move_the_same_bytes_as_their_allocating_siblings() -> None:
    # B3.3: the zero-allocation path exists for the whole related set, not half of it.
    allocating = make_uart()
    into = make_uart()
    payload = bytearray(b"\x01\x02\x03\x04")
    assert run(locked_write(allocating, bytearray(payload))) is True
    assert run(locked_writefrom(into, bytearray(payload), len(payload))) is True
    assert written(allocating) == written(into)

    reader_alloc = make_uart()
    reader_alloc.poller = _StepPoller([select.POLLIN])  # type: ignore[assignment]
    fake(reader_alloc).feed_rx(bytes(payload))
    reader_into = make_uart()
    reader_into.poller = _StepPoller([select.POLLIN])  # type: ignore[assignment]
    fake(reader_into).feed_rx(bytes(payload))
    got = run(locked_read_until_complete(reader_alloc, 4, start_timeout_ms=200, timeout_ms=200))
    buf = bytearray(4)
    size = run(locked_readinto_until_complete(reader_into, buf, 4, start_timeout_ms=200, timeout_ms=200))
    assert got is not None
    assert size == 4
    assert bytes(got) == bytes(buf)


# ---------------------------------------------------------------------------
# B2 - the pluggable framing codec
# ---------------------------------------------------------------------------


def cobs_uart(max_frame: int = 64, **kwargs: "Any") -> UART:
    return make_uart(framing=Framing_COBS(max_frame), **kwargs)


async def locked_write(uart: UART, msg: bytearray) -> bool:
    async with uart:
        return await uart.write(msg)


async def locked_writefrom(uart: UART, buf: bytearray, size: int) -> bool:
    async with uart:
        return await uart.writefrom(buf, size)


async def locked_readinto_until_complete(uart: UART, buf: bytearray, nbytes: int, **kwargs: "Any") -> int | None:
    async with uart:
        return await uart.readinto_until_complete(buf, nbytes, **kwargs)


async def locked_read_until_complete(uart: UART, nbytes: int, **kwargs: "Any") -> bytearray | None:
    async with uart:
        return await uart.read_until_complete(nbytes, **kwargs)


def written(uart: UART) -> bytes:
    return b"".join(entry[1] for entry in fake(uart).log if entry[0] == "write")


def test_pass_through_codec_emits_exactly_what_it_always_did() -> None:
    # The regression that proves the default changed nothing: identical bytes, with and without
    # the codec named explicitly.
    default_uart = make_uart()
    explicit = make_uart(framing=Framing_Pass())
    assert run(locked_write(default_uart, bytearray(b"\x01\x00\x02"))) is True
    assert run(locked_write(explicit, bytearray(b"\x01\x00\x02"))) is True
    assert written(default_uart) == b"\x01\x00\x02"
    assert written(explicit) == written(default_uart)


def test_cobs_write_emits_a_delimited_frame_with_no_inner_zero() -> None:
    uart = cobs_uart()
    assert run(locked_write(uart, bytearray(b"\x01\x00\x02"))) is True
    out = written(uart)
    assert out[-1] == COBS_DELIMITER
    assert COBS_DELIMITER not in out[:-1]


def test_writefrom_is_framed_exactly_like_write() -> None:
    # B2.6: a half-codec'd API, where write() frames and writefrom() does not, is the defect.
    via_write = cobs_uart()
    via_writefrom = cobs_uart()
    payload = bytearray(b"\x01\x00\x02\x03")
    assert run(locked_write(via_write, bytearray(payload))) is True
    buf = bytearray(payload) + bytearray(8)
    assert run(locked_writefrom(via_writefrom, buf, len(payload))) is True
    assert written(via_write) == written(via_writefrom)


def test_cobs_round_trips_through_the_driver() -> None:
    sender = cobs_uart()
    payload = bytearray(b"\x05\x00\x00\x07")
    assert run(locked_write(sender, bytearray(payload))) is True
    receiver = cobs_uart()
    receiver.poller = _StepPoller([select.POLLIN])  # type: ignore[assignment]
    fake(receiver).feed_rx(written(sender))
    buf = bytearray(64)
    size = run(locked_readinto_until_complete(receiver, buf, len(payload), start_timeout_ms=200, timeout_ms=200))
    assert size == len(payload)
    assert bytes(buf[:size]) == bytes(payload)


def test_cobs_round_trips_through_the_allocating_read() -> None:
    # B2.6 again, on the read half: read_until_complete() and readinto_until_complete() move
    # together or not at all.
    sender = cobs_uart()
    payload = bytearray(b"\x09\x00\x0a")
    assert run(locked_write(sender, bytearray(payload))) is True
    receiver = cobs_uart()
    receiver.poller = _StepPoller([select.POLLIN])  # type: ignore[assignment]
    fake(receiver).feed_rx(written(sender))
    got = run(locked_read_until_complete(receiver, len(payload), start_timeout_ms=200, timeout_ms=200))
    assert got is not None
    assert bytes(got) == bytes(payload)


def test_cobs_round_trips_with_a_crc_underneath_it() -> None:
    # The ordering claim itself: build -> CRC -> encode on write, the exact reverse on read.
    sender = make_uart(crc=CRC16(), framing=Framing_COBS(64))
    payload = bytearray(b"\x01\x02\x00\x03")
    assert run(locked_write(sender, bytearray(payload))) is True
    receiver = make_uart(crc=CRC16(), framing=Framing_COBS(64))
    receiver.poller = _StepPoller([select.POLLIN])  # type: ignore[assignment]
    fake(receiver).feed_rx(written(sender))
    buf = bytearray(64)
    size = run(locked_readinto_until_complete(receiver, buf, len(payload), start_timeout_ms=200, timeout_ms=200))
    assert size == len(payload)
    assert bytes(buf[:size]) == bytes(payload)


def test_a_peer_that_never_sends_a_delimiter_fails_the_read_rather_than_blocking() -> None:
    # B2.1: a delimited read is length-unknown, so only the codec's own worst-case bound stops a
    # silent peer from owning the read loop forever.
    uart = cobs_uart(max_frame=16)
    uart.poller = _StepPoller([0])  # type: ignore[assignment]  # never becomes ready again
    fake(uart).feed_rx(b"\x01" * 200)  # plenty of bytes, not one delimiter
    buf = bytearray(64)
    assert run(locked_readinto_until_complete(uart, buf, 8, start_timeout_ms=100, timeout_ms=100)) is None


def test_the_fragment_after_a_resync_is_discarded_never_decoded() -> None:
    # B2.2: a delimiter means "end of something"; only the *next* one bounds a whole frame.
    sender = cobs_uart()
    assert run(locked_write(sender, bytearray(b"\x41\x42\x43"))) is True
    whole_frame = written(sender)
    # A resync lands somewhere inside a frame, so the stream starts with that frame's tail,
    # then its delimiter, then the next whole frame.
    tail = b"\x77\x88" + bytes([COBS_DELIMITER])

    receiver = cobs_uart()
    receiver.poller = _StepPoller([select.POLLIN])  # type: ignore[assignment]
    fake(receiver).feed_rx(tail + whole_frame)
    receiver.resync_framing()
    buf = bytearray(64)
    size = run(locked_readinto_until_complete(receiver, buf, 3, start_timeout_ms=200, timeout_ms=200))
    assert size == 3
    assert bytes(buf[:size]) == b"\x41\x42\x43"

    # Without the resync the same stream decodes the fragment instead - which is exactly the
    # garbage B2.2 exists to keep out, so the flag has to be what makes the difference.
    naive = cobs_uart()
    naive.poller = _StepPoller([select.POLLIN])  # type: ignore[assignment]
    fake(naive).feed_rx(tail + whole_frame)
    assert run(locked_readinto_until_complete(naive, bytearray(64), 3, start_timeout_ms=200, timeout_ms=200)) is None


def test_empty_frames_are_skipped_at_the_codec_layer() -> None:
    # B2.3: two consecutive delimiters must never surface as a zero-length frame to index into.
    sender = cobs_uart()
    assert run(locked_write(sender, bytearray(b"\x31\x32"))) is True
    receiver = cobs_uart()
    receiver.poller = _StepPoller([select.POLLIN])  # type: ignore[assignment]
    fake(receiver).feed_rx(bytes([COBS_DELIMITER, COBS_DELIMITER]) + written(sender))
    buf = bytearray(64)
    size = run(locked_readinto_until_complete(receiver, buf, 2, start_timeout_ms=200, timeout_ms=200))
    assert size == 2
    assert bytes(buf[:size]) == b"\x31\x32"


def test_a_corrupt_code_byte_is_a_decode_failure_not_an_overrun() -> None:
    # B2.4, through the driver: the sentinel, never a walk off the end of the buffer.
    uart = cobs_uart()
    uart.poller = _StepPoller([select.POLLIN])  # type: ignore[assignment]
    fake(uart).feed_rx(b"\x40\x01\x02" + bytes([COBS_DELIMITER]))  # code 0x40 runs past the frame
    buf = bytearray(64)
    assert run(locked_readinto_until_complete(uart, buf, 3, start_timeout_ms=200, timeout_ms=200)) is None


def test_a_caller_buffer_too_small_for_the_encoded_frame_is_refused() -> None:
    # B2.5: silent truncation or a per-frame allocation are both worse than the sentinel.
    uart = cobs_uart()
    assert run(locked_readinto_until_complete(uart, bytearray(4), 8, start_timeout_ms=50, timeout_ms=50)) is None


def test_a_codec_whose_allocation_failed_degrades_every_framed_call() -> None:
    # B2.8: a driver that looks constructed but cannot frame must say so on every framed path.
    uart = make_uart(framing=Framing_COBS(-1))
    assert uart.framing.ready() is False
    assert run(locked_write(uart, bytearray(b"abc"))) is False
    assert run(locked_writefrom(uart, bytearray(b"abcd"), 4)) is False


def test_resync_framing_is_inert_for_the_pass_through_codec() -> None:
    uart = make_uart()
    uart.resync_framing()
    assert uart._skip_to_delimiter is False


# ---------------------------------------------------------------------------
# B1 - the cancel handshake: latched, bounded, broadcast
# ---------------------------------------------------------------------------


def test_cancel_during_a_completing_read_still_terminates() -> None:
    # B1.1: the cancel arrives while the lock is held but no ready() is in flight (here, during the
    # post-read CRC yield) and the read then completes normally. Before the fix nothing ever
    # acknowledged it and cancel_read_timeout() awaited forever - a wedge in the anti-wedge.
    uart = make_uart()
    uart.poller = _StepPoller([select.POLLIN])  # type: ignore[assignment]
    fake(uart).feed_rx(b"abcd")

    async def reader() -> bytes | None:
        async with uart:
            data = await uart.read(4)
            await asyncio.sleep_ms(30)  # stands in for crc.check()'s own per-byte yields
            return data

    async def scenario() -> tuple[bytes | None, bool]:
        task = asyncio.create_task(reader())
        await asyncio.sleep_ms(5)  # the read has completed; the lock is still held
        cancelled = await asyncio.wait_for(uart.cancel_read_timeout(), 2)
        return await asyncio.wait_for(task, 2), cancelled

    result, cancelled = run(scenario())
    assert result == b"abcd"  # the read was already done, so it is not disturbed
    assert cancelled is True  # and the canceller still returns instead of hanging


def test_cancel_between_two_reads_is_not_lost() -> None:
    # B1.2: ready() used to begin with `self.cancel = False`, erasing a request that arrived
    # between two reads - the canceller then blocked on an acknowledgement that never came.
    uart = make_uart()
    uart.poller = _StepPoller([select.POLLIN, select.POLLIN, 0])  # type: ignore[assignment]
    fake(uart).feed_rx(b"xy")

    async def reader() -> "list[object]":
        async with uart:
            first = await uart.read(2)
            await asyncio.sleep_ms(30)  # cancel lands in here, with no ready() in flight
            second = await uart.read(2, timeout_ms=-1)
            return [first, second]

    async def scenario() -> "tuple[list[object], bool]":
        task = asyncio.create_task(reader())
        await asyncio.sleep_ms(5)
        cancelled = await asyncio.wait_for(uart.cancel_read_timeout(), 2)
        return await asyncio.wait_for(task, 2), cancelled

    results, cancelled = run(scenario())
    assert cancelled is True
    assert results[0] == b"xy"
    assert results[1] is None  # the latched cancel aborts the *next* read rather than vanishing


def test_two_concurrent_cancellers_both_return() -> None:
    # B1.3: the acknowledgement is broadcast - one canceller consuming it must not strand another.
    uart = make_uart()
    uart.poller = _StepPoller([0])  # type: ignore[assignment]

    async def waiter() -> bytes | None:
        async with uart:
            return await uart.read(timeout_ms=-1)

    async def scenario() -> "tuple[bool, bool]":
        task = asyncio.create_task(waiter())
        await asyncio.sleep_ms(5)
        first = asyncio.create_task(uart.cancel_read_timeout())
        second = asyncio.create_task(uart.cancel_read_timeout())
        results = (await asyncio.wait_for(first, 2), await asyncio.wait_for(second, 2))
        await asyncio.wait_for(task, 2)
        return results

    first_result, second_result = run(scenario())
    assert first_result is True
    assert second_result is True


def test_no_read_happens_after_the_cancel_is_acknowledged() -> None:
    # B1.5: acknowledgement means "the read path has left the loop", not "it is about to".
    uart = make_uart()
    uart.poller = _StepPoller([0])  # type: ignore[assignment]

    async def waiter() -> bytes | None:
        async with uart:
            return await uart.read(timeout_ms=-1)

    async def scenario() -> "tuple[int, int]":
        task = asyncio.create_task(waiter())
        await asyncio.sleep_ms(5)
        await asyncio.wait_for(uart.cancel_read_timeout(), 2)
        reads_at_ack = len([entry for entry in fake(uart).log if entry[0] == "read"])
        await asyncio.wait_for(task, 2)
        return reads_at_ack, len([entry for entry in fake(uart).log if entry[0] == "read"])

    at_ack, after = run(scenario())
    assert at_ack == 0
    assert after == 0


def test_cancel_with_a_wedged_holder_is_bounded_and_counted() -> None:
    # B1.1's "provably terminating" half: a lock holder that never calls ready() again and never
    # exits cannot make cancel_read_timeout() block forever. It returns True (a cancel is
    # outstanding, so clear() must not then take the lock) and records the un-acknowledged case.
    uart = make_uart()

    async def wedged() -> None:
        async with uart:
            await asyncio.sleep_ms(400)  # never touches the bus again

    async def scenario() -> "tuple[bool, int]":
        task = asyncio.create_task(wedged())
        await asyncio.sleep_ms(5)
        result = await asyncio.wait_for(uart.cancel_read_timeout(timeout_ms=50), 2)
        unacked = uart.cancel_unacknowledged
        await asyncio.wait_for(task, 2)
        return result, unacked

    result, unacked = run(scenario())
    assert result is True
    assert unacked == 1


def test_leaving_the_locked_region_acknowledges_a_latched_cancel() -> None:
    # The other half of B1.1's required handling: the request is acknowledged on every exit from
    # the locked region, not only from inside ready()'s loop.
    uart = make_uart()

    async def holder() -> None:
        async with uart:
            await asyncio.sleep_ms(20)

    async def scenario() -> "tuple[bool, int]":
        task = asyncio.create_task(holder())
        await asyncio.sleep_ms(5)
        result = await asyncio.wait_for(uart.cancel_read_timeout(timeout_ms=500), 2)
        await asyncio.wait_for(task, 2)
        return result, uart.cancel_unacknowledged

    result, unacked = run(scenario())
    assert result is True
    assert unacked == 0  # acknowledged by the __aexit__, well inside the bound


def test_a_new_ready_call_does_not_clear_an_unrelated_cancel() -> None:
    # B1.2 at the unit level: entering ready() must not consume a request it did not serve.
    uart = make_uart()
    uart.poller = _StepPoller([select.POLLIN])  # type: ignore[assignment]
    uart.cancel = True
    assert run(one_shot_ready(uart)) is False  # the latched cancel wins over readiness
    assert uart.cancel is False  # and is consumed exactly once


async def one_shot_ready(uart: UART) -> bool:
    async with uart:
        return await uart.ready(select.POLLIN, timeout_ms=100)


# ---------------------------------------------------------------------------
# read / readinto / readline - single-round
# ---------------------------------------------------------------------------


def test_read_returns_bytes_once_ready() -> None:
    uart = make_uart()
    fake(uart).feed_rx(b"hello")
    # _StepPoller, not the real select.poll() init() registers by default: the real poll/ioctl
    # dispatch against tests/machine.py's pure-Python fake proved unreliable specifically on GitHub
    # Actions runners (never locally) - see CLAUDE.md's "CI hang investigation" note. This and every
    # other test below that used to rely on that path now use the same bounded test double already
    # used elsewhere in this file - they're testing read/write/CRC assembly logic, not the poll/
    # ioctl integration itself.
    uart.poller = _StepPoller([select.POLLIN])  # type: ignore[assignment]

    async def scenario() -> bytes | None:
        async with uart:
            return await uart.read()

    assert run(scenario()) == b"hello"


def test_read_returns_none_on_timeout() -> None:
    uart = make_uart()
    uart.poller = _StepPoller([0])  # type: ignore[assignment]  # never ready - see _StepPoller's own docstring

    async def scenario() -> bytes | None:
        async with uart:
            return await uart.read(timeout_ms=20)

    assert run(scenario()) is None


def test_read_with_explicit_nbytes_reads_exactly_that_many_bytes() -> None:
    uart = make_uart()
    fake(uart).feed_rx(b"hello world")
    uart.poller = _StepPoller([select.POLLIN])  # type: ignore[assignment]  # see test_read_returns_bytes_once_ready's comment

    async def scenario() -> bytes | None:
        async with uart:
            return await uart.read(5)

    assert run(scenario()) == b"hello"


def test_readinto_fills_buffer_and_returns_count() -> None:
    uart = make_uart()
    fake(uart).feed_rx(b"hi")
    uart.poller = _StepPoller([select.POLLIN])  # type: ignore[assignment]  # see test_read_returns_bytes_once_ready's comment
    buf = bytearray(4)

    async def scenario() -> int | None:
        async with uart:
            return await uart.readinto(buf)

    assert run(scenario()) == 2
    assert bytes(buf[:2]) == b"hi"


def test_readinto_with_explicit_nbytes_reads_exactly_that_many_bytes() -> None:
    uart = make_uart()
    fake(uart).feed_rx(b"hello world")
    uart.poller = _StepPoller([select.POLLIN])  # type: ignore[assignment]  # see test_read_returns_bytes_once_ready's comment
    buf = bytearray(11)

    async def scenario() -> int | None:
        async with uart:
            return await uart.readinto(buf, 5)

    assert run(scenario()) == 5
    assert bytes(buf[:5]) == b"hello"


def test_readline_returns_bytes_once_ready() -> None:
    uart = make_uart()
    fake(uart).feed_rx(b"line\n")
    uart.poller = _StepPoller([select.POLLIN])  # type: ignore[assignment]  # see test_read_returns_bytes_once_ready's comment

    async def scenario() -> bytes | None:
        async with uart:
            return await uart.readline()

    assert run(scenario()) == b"line\n"


# ---------------------------------------------------------------------------
# read_until_complete / readinto_until_complete - multi-round assembly, CRC
# ---------------------------------------------------------------------------


def test_read_until_complete_zero_nbytes_returns_empty_immediately() -> None:
    uart = make_uart()

    async def scenario() -> bytearray | None:
        async with uart:
            return await uart.read_until_complete(0)

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
            return await uart.read_until_complete(5, start_timeout_ms=200, timeout_ms=200)

    assert run(scenario()) == bytearray(b"abcde")


def test_read_until_complete_default_crc_is_pass_through() -> None:
    uart = make_uart()
    assert isinstance(uart.crc, CRC_Pass)
    fake(uart).feed_rx(b"raw")
    uart.poller = _StepPoller([select.POLLIN])  # type: ignore[assignment]  # see test_read_returns_bytes_once_ready's comment

    async def scenario() -> bytearray | None:
        async with uart:
            return await uart.read_until_complete(3)

    assert run(scenario()) == bytearray(b"raw")


def test_read_until_complete_strips_and_verifies_real_crc() -> None:
    uart = make_uart(crc=CRC16())
    framed = run(CRC16().add(bytearray(b"hello")))
    assert framed is not None
    fake(uart).feed_rx(bytes(framed))
    uart.poller = _StepPoller([select.POLLIN])  # type: ignore[assignment]  # see test_read_returns_bytes_once_ready's comment

    async def scenario() -> bytearray | None:
        async with uart:
            return await uart.read_until_complete(5)

    assert run(scenario()) == bytearray(b"hello")


def test_read_until_complete_bad_crc_returns_none() -> None:
    uart = make_uart(crc=CRC16())
    framed = run(CRC16().add(bytearray(b"hello")))
    assert framed is not None
    framed[-1] ^= 0xFF  # corrupt the trailing CRC byte
    fake(uart).feed_rx(bytes(framed))
    uart.poller = _StepPoller([select.POLLIN])  # type: ignore[assignment]  # see test_read_returns_bytes_once_ready's comment

    async def scenario() -> bytearray | None:
        async with uart:
            return await uart.read_until_complete(5)

    assert run(scenario()) is None


def test_readinto_until_complete_nbytes_too_large_for_buffer_returns_none() -> None:
    uart = make_uart()
    buf = bytearray(2)

    async def scenario() -> int | None:
        async with uart:
            return await uart.readinto_until_complete(buf, 5)

    assert run(scenario()) is None


def test_readinto_until_complete_fills_buffer_and_strips_crc() -> None:
    uart = make_uart(crc=CRC16())
    framed = run(CRC16().add(bytearray(b"world")))
    assert framed is not None
    fake(uart).feed_rx(bytes(framed))
    uart.poller = _StepPoller([select.POLLIN])  # type: ignore[assignment]  # see test_read_returns_bytes_once_ready's comment
    buf = bytearray(16)

    async def scenario() -> int | None:
        async with uart:
            return await uart.readinto_until_complete(buf, 5)

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
            return await uart.readline_until_complete(start_timeout_ms=200, timeout_ms=200)

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
    uart.poller = _StepPoller([select.POLLIN])  # type: ignore[assignment]  # see test_read_returns_bytes_once_ready's comment

    async def scenario() -> bytearray | None:
        async with uart:
            return await uart.readline_until_complete(start_timeout_ms=200, timeout_ms=200)

    assert run(scenario()) == bytearray(b"ok\n")


# ---------------------------------------------------------------------------
# write / writefrom
# ---------------------------------------------------------------------------


def test_write_empty_message_succeeds_without_touching_the_bus() -> None:
    # _write_all()'s `while sent < total` never executes when total == 0 - mirrors
    # test_read_until_complete_zero_nbytes_returns_empty_immediately on the read side; there's
    # nothing to send, so it must not block waiting on ready(POLLOUT) for a write that never happens.
    uart = make_uart()

    async def scenario() -> bool:
        async with uart:
            return await uart.write(bytearray())

    assert run(scenario()) is True
    assert fake(uart).log == []


def test_write_default_crc_is_pass_through() -> None:
    uart = make_uart()
    uart.poller = _StepPoller([select.POLLOUT])  # type: ignore[assignment]  # see test_read_returns_bytes_once_ready's comment

    async def scenario() -> bool:
        async with uart:
            return await uart.write(bytearray(b"raw"))

    assert run(scenario()) is True
    assert fake(uart).log[-1] == ("write", b"raw")


def test_write_frames_with_configured_crc() -> None:
    uart = make_uart(crc=CRC16())
    uart.poller = _StepPoller([select.POLLOUT])  # type: ignore[assignment]  # see test_read_returns_bytes_once_ready's comment

    async def scenario() -> bool:
        async with uart:
            return await uart.write(bytearray(b"hello"))

    assert run(scenario()) is True
    op, framed = fake(uart).log[-1]
    assert op == "write"
    assert framed[:5] == b"hello"
    assert len(framed) == 5 + CRC16().length()
    assert run(CRC16().check(bytearray(framed))) == bytearray(b"hello")


def test_write_can_be_cancelled_while_waiting_for_tx_ready() -> None:
    # _write_all()'s own `if not await self.ready(select.POLLOUT): return False` - write() calls
    # ready() with no timeout_ms (waits forever), so cancellation is the only way it ever returns
    # False, same mechanism as test_cancel_read_timeout_unblocks_a_pending_wait's read-side version.
    uart = make_uart()
    uart.poller = _StepPoller([0])  # type: ignore[assignment]  # POLLOUT never arrives on its own

    async def writer() -> bool:
        async with uart:
            return await uart.write(bytearray(b"x"))

    async def scenario() -> tuple[bool, bool]:
        task = asyncio.create_task(writer())
        await asyncio.sleep_ms(5)  # let writer enter ready()'s poll loop, holding the lock
        cancelled = await uart.cancel_read_timeout()
        result = await asyncio.wait_for(task, 2)
        return result, cancelled

    result, cancelled = run(scenario())
    assert result is False
    assert cancelled is True


def test_write_waits_until_tx_becomes_writable() -> None:
    uart = make_uart()
    calls = {"n": 0}

    def not_ready_once_then_ready() -> int:
        calls["n"] += 1
        return select.POLLOUT if calls["n"] >= 2 else 0

    uart.poller = _StepPoller([not_ready_once_then_ready])  # type: ignore[assignment]

    async def scenario() -> bool:
        async with uart:
            return await uart.write(bytearray(b"x"))

    assert run(scenario()) is True
    assert calls["n"] >= 2  # genuinely waited through at least one not-ready round, not a lucky first check


def test_writefrom_frames_with_crc_in_place() -> None:
    uart = make_uart(crc=CRC16())
    uart.poller = _StepPoller([select.POLLOUT])  # type: ignore[assignment]  # see test_read_returns_bytes_once_ready's comment
    buf = bytearray(b"hello" + b"\x00" * 10)  # extra room for the trailing CRC

    async def scenario() -> bool:
        async with uart:
            return await uart.writefrom(buf, 5)

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
            return await uart.writefrom(buf, 5)

    assert run(scenario()) is False
    assert fake(uart).log == []  # rejected before ever touching the bus


def test_write_retries_after_a_short_write_until_everything_is_sent() -> None:
    # Regression test: uart.write() used to be called once and its return value discarded
    # entirely, silently dropping the untransmitted tail of a message larger than the TX ring
    # buffer's available room - confirmed as a real gap against ports/rp2/machine_uart.c's own
    # write() loop, which can return a short count. write_limit=3 forces every fake write() call to
    # accept at most 3 bytes, so a 7-byte message needs 3 rounds (3+3+1) to fully send.
    uart = make_uart()
    fake(uart).write_limit = 3
    uart.poller = _StepPoller([select.POLLOUT])  # type: ignore[assignment]  # see test_read_returns_bytes_once_ready's comment

    async def scenario() -> bool:
        async with uart:
            return await uart.write(bytearray(b"1234567"))

    assert run(scenario()) is True
    writes = [data for op, data in fake(uart).log if op == "write"]
    assert len(writes) > 1  # genuinely needed more than one round, not a lucky single call
    assert b"".join(writes) == b"1234567"  # nothing dropped, nothing duplicated


def test_write_returns_false_when_uart_write_returns_none() -> None:
    # write_limit=0 models a total send failure - uart.write() hit its own internal timeout before
    # accepting anything at all, matching real MP_EAGAIN -> None (see module docstring).
    uart = make_uart()
    fake(uart).write_limit = 0
    uart.poller = _StepPoller([select.POLLOUT])  # type: ignore[assignment]  # see test_read_returns_bytes_once_ready's comment

    async def scenario() -> bool:
        async with uart:
            return await uart.write(bytearray(b"x"))

    assert run(scenario()) is False
    assert fake(uart).log == []  # nothing was ever actually recorded as sent


def test_writefrom_retries_after_a_short_write_until_everything_is_sent() -> None:
    uart = make_uart(crc=CRC16())
    fake(uart).write_limit = 4
    uart.poller = _StepPoller([select.POLLOUT])  # type: ignore[assignment]  # see test_read_returns_bytes_once_ready's comment
    buf = bytearray(b"hello" + b"\x00" * 10)

    async def scenario() -> bool:
        async with uart:
            return await uart.writefrom(buf, 5)

    assert run(scenario()) is True
    writes = [data for op, data in fake(uart).log if op == "write"]
    assert len(writes) > 1
    framed = b"".join(writes)
    assert framed[:5] == b"hello"
    assert len(framed) == 5 + CRC16().length()


# ---------------------------------------------------------------------------
# base_classes.Lockable integration - real inheritance (UART(Lockable)), not
# mocked - mirrors test_asy_i2c_driver.py's own Lockable integration coverage
# ---------------------------------------------------------------------------


def test_exception_inside_session_still_releases_the_lock() -> None:
    uart = make_uart()

    def boom() -> None:  # raised from a helper, so the raise isn't lexically inside the try below
        raise RuntimeError("boom")

    async def scenario() -> None:
        try:
            async with uart:
                boom()
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
        async with uart, uart:
            pass

    async def scenario() -> bool:
        try:
            await asyncio.wait_for(reentrant(), 0.2)
        except asyncio.TimeoutError:
            return True
        else:
            return False

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

    async def add(self, _bytearr: bytearray, _init: "int | None" = None) -> bytearray | None:  # both called positionally
        raise MemoryError("simulated allocation failure")

    async def check(self, _bytearr: bytearray, _init: "int | None" = None) -> bytearray | None:
        raise MemoryError("simulated allocation failure")


def test_write_returns_false_on_crc_add_memoryerror() -> None:
    uart = make_uart(crc=CRC16())
    uart.crc = _MemoryErrorCRC(CRC16())  # type: ignore[assignment]

    async def scenario() -> bool:
        async with uart:
            return await uart.write(bytearray(b"x"))

    assert run(scenario()) is False
    assert fake(uart).log == []  # rejected before ever touching the bus


class _NoneCRC:
    # A real CRC_Base's add() only ever returns None via its own _validate_init() rejecting an
    # explicit init argument - write() never passes one, so this path can't be reached through any
    # real CRC object. Minimal fake matching just the add()/length() surface write() calls, same
    # technique as _MemoryErrorCRC above for its own otherwise-unreachable branch.
    def length(self) -> int:
        return 0

    async def add(self, _bytearr: bytearray, _init: "int | None" = None) -> bytearray | None:  # called positionally
        return None


def test_write_returns_false_when_crc_add_returns_none() -> None:
    uart = make_uart()
    uart.crc = _NoneCRC()  # type: ignore[assignment]

    async def scenario() -> bool:
        async with uart:
            return await uart.write(bytearray(b"x"))

    assert run(scenario()) is False
    assert fake(uart).log == []  # rejected before ever touching the bus


def test_read_until_complete_returns_none_on_crc_check_memoryerror() -> None:
    uart = make_uart(crc=CRC16())
    framed = run(CRC16().add(bytearray(b"hello")))
    assert framed is not None
    fake(uart).feed_rx(bytes(framed))
    uart.crc = _MemoryErrorCRC(CRC16())  # type: ignore[assignment]
    uart.poller = _StepPoller([select.POLLIN])  # type: ignore[assignment]  # see test_read_returns_bytes_once_ready's comment

    async def scenario() -> bytearray | None:
        async with uart:
            return await uart.read_until_complete(5)

    assert run(scenario()) is None


# `msg += add`'s own MemoryError guard in read_until_complete()/readline_until_complete() (see the
# module docstring's "MemoryError guarding" section) is deliberately NOT fault-injected here the
# same way: unlike self.crc, `msg` is a plain bytearray built and grown entirely inside those
# methods - there's no substitutable object to wrap/monkeypatch the way _MemoryErrorCRC does above,
# and bytearray.__iadd__ has no Python-level hook to force MemoryError deterministically without
# either a constrained interpreter heap (not controllable from within a running test - see
# SPECIFICATION.md Part E) or genuinely exhausting memory (flaky/unsafe for CI). Same category of
# documented, deliberate testing gap as test_print_log.py's own
# test_history_length_huge_is_capped_instead_of_crashing_the_interpreter comment. The surrounding
# behavior is still covered: test_read_until_complete_assembles_across_multiple_rounds and
# test_readline_until_complete_assembles_multi_part_line already exercise this exact line
# successfully across multiple rounds, proving the guard doesn't break normal accumulation.


# ---------------------------------------------------------------------------
# Counted reads never ask the peripheral for bytes that have not arrived
# ---------------------------------------------------------------------------
# Real machine.UART.read()/readinto() wait out timeout_char for every requested byte still in
# flight, synchronously, without ever yielding to asyncio - measured at 4.4ms of held event loop
# per 53-byte frame on the dev bench (SPECIFICATION.md Part F.5.8). The clamp to any() is what
# keeps this driver non-blocking, so these tests pin the *request*, which the fake cannot.


def _record_requests(fk: FakeUART, method: str) -> "list[int | None]":
    # Wraps the fake's own read method to capture the nbytes the driver asks for. The fake serves
    # min(nbytes, queued) either way, so only the request distinguishes a clamped call from one
    # that would have blocked on real hardware.
    asked: list[int | None] = []
    original = getattr(fk, method)

    def spy(buf_or_n: "Any" = None, nbytes: "int | None" = None) -> "Any":
        asked.append(nbytes if method == "readinto" else buf_or_n)
        return original(buf_or_n, nbytes) if method == "readinto" else original(buf_or_n)

    setattr(fk, method, spy)  # the project's mocking mechanism - MicroPython has no unittest.mock
    return asked


def test_readinto_until_complete_never_asks_for_more_than_is_buffered() -> None:
    uart = make_uart()
    fk = fake(uart)
    fk.feed_rx(b"ab")  # only two of the five bytes have "arrived" when POLLIN first fires

    def feed_rest_and_ready() -> int:
        fk.feed_rx(b"cde")
        return select.POLLIN

    uart.poller = _StepPoller([select.POLLIN, feed_rest_and_ready])  # type: ignore[assignment]
    asked = _record_requests(fk, "readinto")
    buf = bytearray(5)

    async def scenario() -> int | None:
        async with uart:
            return await uart.readinto_until_complete(buf, 5, start_timeout_ms=200, timeout_ms=200)

    assert run(scenario()) == 5
    assert bytes(buf) == b"abcde"
    # The first round must ask for 2, not 5: asking for 5 is exactly the call that blocks the loop
    # for the three bytes still on the wire.
    assert asked[0] == 2, f"first round asked for {asked[0]}, not the 2 bytes actually buffered"
    assert all(n is not None and n <= 5 for n in asked), f"a round asked past the frame: {asked}"


def test_read_until_complete_never_asks_for_more_than_is_buffered() -> None:
    uart = make_uart()
    fk = fake(uart)
    fk.feed_rx(b"ab")

    def feed_rest_and_ready() -> int:
        fk.feed_rx(b"cde")
        return select.POLLIN

    uart.poller = _StepPoller([select.POLLIN, feed_rest_and_ready])  # type: ignore[assignment]
    asked = _record_requests(fk, "read")

    async def scenario() -> bytearray | None:
        async with uart:
            return await uart.read_until_complete(5, start_timeout_ms=200, timeout_ms=200)

    assert run(scenario()) == bytearray(b"abcde")
    assert asked[0] == 2, f"first round asked for {asked[0]}, not the 2 bytes actually buffered"


def test_single_shot_reads_clamp_to_what_is_buffered_and_report_nothing_as_none() -> None:
    uart = make_uart()
    fk = fake(uart)
    fk.feed_rx(b"xyz")
    asked_read = _record_requests(fk, "read")

    async def read_scenario() -> bytes | None:
        async with uart:
            return await uart.read(64)  # asks far past what has arrived

    assert run(read_scenario()) == b"xyz"
    assert asked_read[0] == 3, f"read() asked for {asked_read[0]}, not the 3 bytes buffered"

    uart2 = make_uart()
    fk2 = fake(uart2)
    asked_readinto = _record_requests(fk2, "readinto")
    buf = bytearray(8)

    async def empty_scenario() -> int | None:
        async with uart2:  # POLLIN is always set by make_uart()'s poller, but nothing is queued
            return await uart2.readinto(buf, 8)

    # Nothing buffered: the documented None, and no zero-length call handed to the peripheral.
    assert run(empty_scenario()) is None
    assert asked_readinto == [], f"a read was issued with an empty buffer: {asked_readinto}"


# ---------------------------------------------------------------------------
# ready() is this driver's one yield point, and it has two poll rates
# ---------------------------------------------------------------------------
# Every read loop above reaches the peripheral through ready(), so "ready() always yields" is what
# bounds how long any of them can hold the event loop. The clamp alone made the stall worse without
# it, because ipoll() reports the mask with no await of its own (SPECIFICATION.md Part F.5.8).


def test_ready_yields_even_when_the_mask_is_already_satisfied() -> None:
    uart = make_uart()  # this poller reports the mask on its very first ipoll() call
    ran: list[int] = []

    async def competitor() -> None:
        ran.append(1)

    async def scenario() -> bool:
        async with uart:
            other = asyncio.create_task(competitor())  # runnable, but only if ready() yields
            got = await uart.ready(select.POLLIN, timeout_ms=100)
            assert ran, "ready() returned True without yielding: a read loop through it cannot be preempted"
            await other
            return got

    assert run(scenario()) is True


def test_a_deadlineless_wait_polls_at_the_idle_rate_and_a_bounded_one_does_not() -> None:
    # A wait with no deadline is an idle listener waiting for traffic that may never come; one with
    # a deadline is inside a transaction. Two not-ready rounds separate the two rates (F.5.9).
    async def wait_on(uart: UART, timeout_ms: int) -> int:
        async with uart:
            t0 = time.ticks_ms()
            assert await uart.ready(select.POLLIN, timeout_ms=timeout_ms) is True
            return time.ticks_diff(time.ticks_ms(), t0)

    idle = make_uart(poll_wait_ms=1, poll_idle_ms=40)
    idle.poller = _StepPoller([0, 0, select.POLLIN])  # type: ignore[assignment]
    assert run(wait_on(idle, -1)) >= 2 * 40

    bounded = make_uart(poll_wait_ms=1, poll_idle_ms=40)
    bounded.poller = _StepPoller([0, 0, select.POLLIN])  # type: ignore[assignment]
    assert run(wait_on(bounded, 1000)) < 40


def test_uncounted_reads_are_clamped_to_what_is_buffered_too() -> None:
    # read()/readinto() with no count asked the peripheral for the whole buffer, and every byte of
    # that which has not arrived costs the same synchronous timeout_char wait as a counted read.
    uart = make_uart()
    fk = fake(uart)
    fk.feed_rx(b"hi")
    asked_read = _record_requests(fk, "read")

    async def read_scenario() -> bytes | None:
        async with uart:
            return await uart.read()

    assert run(read_scenario()) == b"hi"
    assert asked_read[0] == 2, f"read() asked for {asked_read[0]}, not the 2 bytes buffered"

    uart2 = make_uart()
    fk2 = fake(uart2)
    fk2.feed_rx(b"hi")
    asked_into = _record_requests(fk2, "readinto")

    async def readinto_scenario() -> int | None:
        async with uart2:
            return await uart2.readinto(bytearray(64))

    assert run(readinto_scenario()) == 2
    assert asked_into[0] == 2, f"readinto() asked for {asked_into[0]}, not the 2 bytes buffered"


def test_readline_does_not_probe_an_empty_buffer() -> None:
    # readline() has no count to clamp, so it gates on any() instead: the C read would otherwise
    # spin out its EAGAIN probe on every empty call, for the ~1ms it takes ticks_ms() to advance.
    uart = make_uart()  # POLLIN always set by this poller, nothing queued behind it
    fk = fake(uart)

    async def scenario() -> bytes | None:
        async with uart:
            return await uart.readline()

    assert run(scenario()) is None
    assert not [entry for entry in fk.log if entry[0] == "readline"], fk.log


def test_a_whole_frame_read_never_asks_for_a_byte_that_has_not_arrived() -> None:
    # The whole-driver version of the per-path assertions above: the fake counts the bytes a real
    # peripheral would have blocked on, so one number covers every path a frame read goes through.
    FakeUART.would_have_blocked_bytes = 0
    uart = make_uart()
    fk = fake(uart)
    fk.feed_rx(b"ab")

    def feed_rest_and_ready() -> int:
        fk.feed_rx(b"cdefgh")
        return select.POLLIN

    uart.poller = _StepPoller([select.POLLIN, feed_rest_and_ready])  # type: ignore[assignment]
    buf = bytearray(8)

    async def scenario() -> int | None:
        async with uart:
            return await uart.readinto_until_complete(buf, 8, start_timeout_ms=200, timeout_ms=200)

    assert run(scenario()) == 8
    assert FakeUART.would_have_blocked_bytes == 0, FakeUART.would_have_blocked_bytes


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
