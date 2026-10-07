import asyncio
import gc
import select
import time

from _uart_comm_harness import Pair, accept_set, echo_get
from machine import UART as FakeUART
from machine import Timer, mem32
from rp2 import DMA

import asy_uart_driver
from asy_crc_checks import CRC16, CRCBase, CRCPass
from asy_framing_codecs import COBS_DELIMITER, FramingBase, FramingCOBS, FramingPass
from asy_uart_driver import UART

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")

# @tunable l1.asy_uart_driver_run_bound_s = 5
_RUN_BOUND_S = 5
# @tunable l1.asy_uart_driver_data_timeout_ms = 200
_DATA_TIMEOUT_MS = 200
# @tunable l1.asy_uart_driver_no_data_timeout_ms = 20
_NO_DATA_TIMEOUT_MS = 20
# @tunable l1.asy_uart_driver_task_inside_ms = 5
_TASK_INSIDE_MS = 5
# @tunable l1.asy_uart_driver_step_bound_s = 2
_STEP_BOUND_S = 2
# @tunable l1.asy_uart_driver_no_delimiter_timeout_ms = 100
_NO_DELIMITER_TIMEOUT_MS = 100
# @tunable l1.asy_uart_driver_locked_work_ms = 30
_LOCKED_WORK_MS = 30
# @tunable l1.asy_uart_driver_short_cancel_ack_ms = 50
_SHORT_CANCEL_ACK_MS = 50
# @tunable l1.asy_uart_driver_holder_work_ms = 20
_HOLDER_WORK_MS = 20
# @tunable l1.asy_uart_driver_cancel_ack_ms = 500
_CANCEL_ACK_MS = 500
# @tunable l1.asy_uart_driver_ready_timeout_ms = 100
_READY_TIMEOUT_MS = 100
# @tunable l1.asy_i2c_driver_deadlock_wait_s = 0.2
_DEADLOCK_WAIT_S = 0.2
# @tunable l1.asy_uart_driver_poll_wait_ms = 1
_POLL_WAIT_MS = 1
# @tunable l1.asy_uart_driver_idle_poll_ms = 40
_IDLE_POLL_MS = 40
# @tunable l1.asy_uart_driver_silent_line_timeout_ms = 30
_SILENT_LINE_TIMEOUT_MS = 30
# @tunable l1.asy_uart_driver_feed_delay_ms = 3
_FEED_DELAY_MS = 3
# @tunable l1.asy_uart_driver_hammer_bound_s = 60
_HAMMER_BOUND_S = 60

# Mirrors of asy_uart_driver.py's private const()s, which are no module attributes on MicroPython - keep in sync.
_UART0_RSR = 0x40034004
_UART0_IMSC = 0x40034038
_UART0_DMACR = 0x40034048
_IMSC_RX = 0x50
_DMACR_RXDMAE = 0x01
_RSR_FE = 0x01
_RSR_PE = 0x02
_RSR_BE = 0x04
_RSR_OE = 0x08
_UART_MIN_RXBUF = 32
_RX_RELOAD = 0x20000000


def run(coro: "Coroutine[Any, Any, T]", limit: float = _RUN_BOUND_S) -> "T":
    # Bounded via wait_for(), not a bare asyncio.run(): a timeout_ms=-1 read through a real
    # select.poll() against a pure-Python fake hangs forever on CI runners (CLAUDE.md's known hang).
    # 5s is generous next to this file's tightest inner bound, and a TimeoutError FAILs fast.
    return asyncio.run(asyncio.wait_for(coro, limit))


def make_uart(**kwargs: "Any") -> UART:
    # One fast rate unless a test names its own, so every interleaving keeps the equal-rate timing it was
    # written against; the ring is armed as the link's setup() arms it.
    kwargs.setdefault("poll_wait_ms", 1)
    kwargs.setdefault("poll_idle_ms", 1)
    DMA.reset_registry()  # no per-test reset exists, and each armed ring holds two of the twelve channels
    uart = UART(0, tx_pin=0, rx_pin=1, **kwargs)
    unpaced(uart)
    # Replaces the real select.poll() init() installs: the Unix port never re-checks a Python object's
    # ioctl() after registration, so a wait hangs on CI (CLAUDE.md). Only the transmit side polls - the
    # receive side reads the ring's fill level - so this is always-ready for POLLOUT.
    uart.poller = _StepPoller([select.POLLOUT])  # type: ignore[assignment]
    assert uart.setup_rx_ring() is True
    return uart


def fake(uart: UART) -> FakeUART:
    return uart._uart  # type: ignore[return-value]


def unpaced(uart: UART) -> None:
    # Fed bytes land at once instead of at the line rate on the fake clock; a re-init builds a new fake.
    fake(uart).rx_rate = float("inf")


async def feed_after(uart: UART, data: bytes, delay_ms: int = _FEED_DELAY_MS) -> None:
    # Bytes "arriving" while a read is already waiting on the ring.
    await asyncio.sleep_ms(delay_ms)
    fake(uart).feed_rx(data)


def plant_rx_errors(uart: UART, bits: int) -> None:
    # The fake UART's UARTRSR error flags, as the peripheral sets them on a bad byte; a break also
    # receives one 0x00 character (Table 426).
    fake(uart).plant_rx_error(bits)


def skip_ahead(uart: UART, n: int) -> None:
    # As if n bytes had arrived and been read: the data channel's count and write position advance
    # together with the driver's consumer position, so a test reaches the count's reload or the ring's end.
    channel = uart._rx_dma
    assert channel is not None
    channel._count -= n
    channel._offset += n
    uart._rx_pos = (uart._rx_pos + n) & (_RX_RELOAD - 1)


class _StepPoller:
    # Stands in for uart.poller: the Unix port's select.poll() never re-checks a Python object's
    # ioctl(), so it cannot exercise a not-ready -> ready transition (CLAUDE.md's known hang). Each
    # ipoll() consumes the next `steps` entry - a mask, or a callable returning one - then repeats it.
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
    assert uart.rxbuf == 32
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
    # Real hardware silently ignores a non-positive baudrate, keeping the previous or default value, rather
    # than raising - confirmed directly, not guessed (tests/machine.py's docstring). The raise/no-raise
    # contract is what this checks; it makes no claim the fake models the silent-ignore behavior itself.
    uart = make_uart(baudrate=0)
    assert fake(uart).id == 0  # construction completed, nothing raised


def test_valid_crc_configurations() -> None:
    default = make_uart()
    assert isinstance(default.crc, CRCPass)
    explicit_pass = CRCPass()
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



def test_the_peripheral_receive_buffer_stays_at_its_minimum() -> None:
    # The ring replaces machine.UART's own receive buffer, so the configured rxbuf is the protocol's
    # sizing figure alone and never reaches the peripheral - not even one the peripheral would refuse.
    for rxbuf in (32, 1024, 40000):
        uart = make_uart(rxbuf=rxbuf)
        assert uart.rxbuf == rxbuf
        assert fake(uart).rxbuf == _UART_MIN_RXBUF


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
    # asy_uart_driver.py's init() constructs Pin(tx_pin) as a call argument to _UART(...), so a bad tx_pin
    # always raises before _UART()'s own body, and therefore its port_id check, ever runs - a consequence of
    # how this driver is structured, not an assumption about the C constructor's internal check order.
    try:
        UART(99, tx_pin=29, rx_pin=1)
        message = ""
    except ValueError as e:
        message = str(e)
    assert "pin" in message.lower()



def test_bad_port_id_wins_over_bad_invert_and_txbuf() -> None:
    # Once inside _UART()'s own body (both pins valid), id is checked before invert/txbuf -
    # matches mp_machine_uart_make_new() fully checking uart_id before init_helper() ever runs.
    try:
        UART(99, tx_pin=0, rx_pin=1, txbuf=99999, invert=255)
        message = ""
    except ValueError as e:
        message = str(e)
    assert "UART(99)" in message



def test_bad_invert_wins_over_bad_txbuf() -> None:
    # invert is checked before txbuf in mp_machine_uart_init_helper()'s own body.
    try:
        make_uart(invert=255, txbuf=99999)
        message = ""
    except ValueError as e:
        message = str(e)
    assert "inversion" in message.lower()


def test_multiple_invalid_pins_still_raises_cleanly() -> None:
    try:
        UART(0, tx_pin=29, rx_pin=-1)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_failed_reinit_leaves_the_bus_deinitialized_not_reverted() -> None:
    # init() always deinit()s the previous bus first, so a failing re-init cannot roll back to the previous
    # working bus - the instance is left deinitialized until a caller re-inits with valid parameters. The
    # same shape as asy_i2c_driver.py's and asy_spi_driver.py's init(), not unique to UART.
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
    assert uart.session_lock.locked() is False

    async def scenario() -> None:
        async with uart:
            assert uart.session_lock.locked() is True
        assert uart.session_lock.locked() is False

    run(scenario())


# ---------------------------------------------------------------------------
# ready / cancel_read_timeout
# ---------------------------------------------------------------------------



def test_ready_returns_true_once_data_is_available() -> None:
    uart = make_uart()
    fake(uart).feed_rx(b"x")
    assert run(uart.ready(select.POLLIN, timeout_ms=_DATA_TIMEOUT_MS)) is True



def test_ready_times_out_when_nothing_arrives() -> None:
    uart = make_uart()  # an empty ring
    assert run(uart.ready(select.POLLIN, timeout_ms=_NO_DATA_TIMEOUT_MS)) is False



def test_ready_survives_a_concurrent_deinit_mid_loop() -> None:
    # Regression test: ready() used to check self._uart/self.poller for None only at entry, then loop
    # indefinitely - a concurrent deinit() mid-loop nulled self.poller and crashed the next iteration.
    # Fixed to re-check every iteration, matching asy_udp_socket.py's ready().
    uart = make_uart()

    async def scenario() -> bool:
        async with uart:
            waiter = asyncio.create_task(uart.ready(select.POLLIN, timeout_ms=_DATA_TIMEOUT_MS))
            await asyncio.sleep_ms(_TASK_INSIDE_MS)
            uart.deinit()
            return await waiter

    assert run(scenario()) is False  # must not raise


def test_ready_returns_false_on_a_malformed_mask() -> None:
    # A non-int mask makes `event & mask` inside ready()'s own loop raise TypeError - not caught by
    # any caller's own except clause (those only wrap the real UART call, not this await) - so
    # ready() must catch it itself and degrade to False rather than propagating.
    uart = make_uart()
    assert run(uart.ready("not-a-mask")) is False  # type: ignore[arg-type]


def test_cancel_read_timeout_returns_false_if_not_locked() -> None:
    uart = make_uart()
    assert run(uart.cancel_read_timeout()) is False



def test_cancel_read_timeout_unblocks_a_pending_wait() -> None:
    uart = make_uart()  # nothing arrives on its own

    async def waiter() -> bytes | None:
        async with uart:
            return await uart.read(timeout_ms=-1)  # waits forever unless cancelled

    async def scenario() -> tuple[bytes | None, bool]:
        task = asyncio.create_task(waiter())
        await asyncio.sleep_ms(_TASK_INSIDE_MS)  # let waiter enter ready()'s poll loop, holding the lock
        cancelled = await uart.cancel_read_timeout()
        result = await asyncio.wait_for(task, _STEP_BOUND_S)
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
    # forever on a runner. The receive side never polls at all: it reads the ring, never the FIFO API.
    real_poll_type = type(select.poll()).__name__
    plain = make_uart()
    assert type(plain.poller).__name__ != real_poll_type
    assert fake(plain).rx_api_calls == 0
    delimited = cobs_uart()
    assert type(delimited.poller).__name__ != real_poll_type
    assert fake(delimited).rx_api_calls == 0


# ---------------------------------------------------------------------------
# B3 - optional-buffer gaps and caller-buffer validation
# ---------------------------------------------------------------------------


def test_a_complete_write_reslices_nothing() -> None:
    # The re-slice happens only after a short write has actually occurred, so the normal
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
    # Silent truncation, or an out-of-range write, would both be worse than the sentinel.
    uart = make_uart()
    assert run(locked_writefrom(uart, bytearray(4), 8)) is False
    assert run(locked_writefrom(uart, bytearray(4), -1)) is False


def test_writefrom_rejects_a_buffer_with_no_room_for_the_crc() -> None:
    uart = make_uart(crc=CRC16())
    assert run(locked_writefrom(uart, bytearray(4), 4)) is False  # 4 payload + 2 CRC > 4
    assert run(locked_writefrom(uart, bytearray(6), 4)) is True


def test_into_methods_move_the_same_bytes_as_their_allocating_siblings() -> None:
    # The zero-allocation path exists for the whole related set, not half of it.
    allocating = make_uart()
    into = make_uart()
    payload = bytearray(b"\x01\x02\x03\x04")
    assert run(locked_write(allocating, bytearray(payload))) is True
    assert run(locked_writefrom(into, bytearray(payload), len(payload))) is True
    assert written(allocating) == written(into)

    reader_alloc = make_uart()
    fake(reader_alloc).feed_rx(bytes(payload))
    got = run(locked_read_until_complete(reader_alloc, 4, start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS))
    reader_into = make_uart()  # read in turn: each build frees every channel (make_uart())
    fake(reader_into).feed_rx(bytes(payload))
    buf = bytearray(4)
    size = run(locked_readinto_until_complete(reader_into, buf, 4, start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS))
    assert got is not None
    assert size == 4
    assert bytes(got) == bytes(buf)


# ---------------------------------------------------------------------------
# B2 - the pluggable framing codec
# ---------------------------------------------------------------------------


def cobs_uart(max_frame: int = 64, **kwargs: "Any") -> UART:
    return make_uart(framing=FramingCOBS(max_frame), **kwargs)


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
    explicit = make_uart(framing=FramingPass())
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
    # A half-codec'd API, where write() frames and writefrom() does not, is the defect.
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
    fake(receiver).feed_rx(written(sender))
    buf = bytearray(64)
    size = run(locked_readinto_until_complete(receiver, buf, len(payload), start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS))
    assert size == len(payload)
    assert bytes(buf[:size]) == bytes(payload)


def test_cobs_round_trips_through_the_allocating_read() -> None:
    # The codec again, on the read half: read_until_complete() and readinto_until_complete() move
    # together or not at all.
    sender = cobs_uart()
    payload = bytearray(b"\x09\x00\x0a")
    assert run(locked_write(sender, bytearray(payload))) is True
    receiver = cobs_uart()
    fake(receiver).feed_rx(written(sender))
    got = run(locked_read_until_complete(receiver, len(payload), start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS))
    assert got is not None
    assert bytes(got) == bytes(payload)


def test_cobs_round_trips_with_a_crc_underneath_it() -> None:
    # The ordering claim itself: build -> CRC -> encode on write, the exact reverse on read.
    sender = make_uart(crc=CRC16(), framing=FramingCOBS(64))
    payload = bytearray(b"\x01\x02\x00\x03")
    assert run(locked_write(sender, bytearray(payload))) is True
    receiver = make_uart(crc=CRC16(), framing=FramingCOBS(64))
    fake(receiver).feed_rx(written(sender))
    buf = bytearray(64)
    size = run(locked_readinto_until_complete(receiver, buf, len(payload), start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS))
    assert size == len(payload)
    assert bytes(buf[:size]) == bytes(payload)



def test_a_peer_that_never_sends_a_delimiter_fails_the_read_rather_than_blocking() -> None:
    # A delimited read is length-unknown, so only the codec's own worst-case bound stops a
    # silent peer from owning the read loop forever.
    uart = cobs_uart(max_frame=16)
    fake(uart).feed_rx(b"\x01" * 200)  # plenty of bytes, not one delimiter
    buf = bytearray(64)
    assert run(locked_readinto_until_complete(uart, buf, 8, start_timeout_ms=_NO_DELIMITER_TIMEOUT_MS, timeout_ms=_NO_DELIMITER_TIMEOUT_MS)) is None


def test_the_fragment_after_a_resync_is_discarded_never_decoded() -> None:
    # A delimiter means "end of something"; only the *next* one bounds a whole frame.
    sender = cobs_uart()
    assert run(locked_write(sender, bytearray(b"\x41\x42\x43"))) is True
    whole_frame = written(sender)
    # A resync lands somewhere inside a frame, so the stream starts with that frame's tail,
    # then its delimiter, then the next whole frame.
    tail = b"\x77\x88" + bytes([COBS_DELIMITER])

    receiver = cobs_uart()
    fake(receiver).feed_rx(tail + whole_frame)
    receiver.resync_framing()
    buf = bytearray(64)
    size = run(locked_readinto_until_complete(receiver, buf, 3, start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS))
    assert size == 3
    assert bytes(buf[:size]) == b"\x41\x42\x43"

    # Without the resync the same stream decodes the fragment instead - which is exactly the
    # garbage resync_framing() exists to keep out, so the flag has to be what makes the difference.
    naive = cobs_uart()
    fake(naive).feed_rx(tail + whole_frame)
    assert run(locked_readinto_until_complete(naive, bytearray(64), 3, start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS)) is None


def test_empty_frames_are_skipped_at_the_codec_layer() -> None:
    # Two consecutive delimiters must never surface as a zero-length frame to index into.
    sender = cobs_uart()
    assert run(locked_write(sender, bytearray(b"\x31\x32"))) is True
    receiver = cobs_uart()
    fake(receiver).feed_rx(bytes([COBS_DELIMITER, COBS_DELIMITER]) + written(sender))
    buf = bytearray(64)
    size = run(locked_readinto_until_complete(receiver, buf, 2, start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS))
    assert size == 2
    assert bytes(buf[:size]) == b"\x31\x32"


def test_a_corrupt_code_byte_is_a_decode_failure_not_an_overrun() -> None:
    # Through the driver: the sentinel, never a walk off the end of the buffer.
    uart = cobs_uart()
    fake(uart).feed_rx(b"\x40\x01\x02" + bytes([COBS_DELIMITER]))  # code 0x40 runs past the frame
    buf = bytearray(64)
    assert run(locked_readinto_until_complete(uart, buf, 3, start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS)) is None


def test_a_caller_buffer_too_small_for_the_encoded_frame_is_refused() -> None:
    # Silent truncation or a per-frame allocation are both worse than the sentinel.
    uart = cobs_uart()
    assert run(locked_readinto_until_complete(uart, bytearray(4), 8, start_timeout_ms=50, timeout_ms=50)) is None


def test_a_delimited_frame_that_decodes_to_nothing_is_a_failed_read() -> None:
    # An encoded empty frame is no payload the caller asked for: the read fails, never reports 0 bytes.
    uart = cobs_uart()
    fake(uart).feed_rx(b"\x01" + bytes([COBS_DELIMITER]))
    assert run(locked_readinto_until_complete(uart, bytearray(64), 3, start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS)) is None


def test_a_codec_whose_allocation_failed_degrades_every_framed_call() -> None:
    # A driver that looks constructed but cannot frame must say so on every framed path.
    uart = make_uart(framing=FramingCOBS(-1))
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
    # The cancel arrives while the lock is held but no ready() is in flight (here, during the
    # post-read CRC yield) and the read then completes normally. Before the fix nothing ever
    # acknowledged it and cancel_read_timeout() awaited forever - a wedge in the anti-wedge.
    uart = make_uart()
    fake(uart).feed_rx(b"abcd")

    async def reader() -> bytes | None:
        async with uart:
            data = await uart.read(4)
            await asyncio.sleep_ms(_LOCKED_WORK_MS)  # stands in for crc.check()'s own per-byte yields
            return data

    async def scenario() -> tuple[bytes | None, bool]:
        task = asyncio.create_task(reader())
        await asyncio.sleep_ms(_TASK_INSIDE_MS)  # the read has completed; the lock is still held
        cancelled = await asyncio.wait_for(uart.cancel_read_timeout(), _STEP_BOUND_S)
        return await asyncio.wait_for(task, _STEP_BOUND_S), cancelled

    result, cancelled = run(scenario())
    assert result == b"abcd"  # the read was already done, so it is not disturbed
    assert cancelled is True  # and the canceller still returns instead of hanging



def test_cancel_between_two_reads_is_not_lost() -> None:
    # ready() used to begin with `self._cancel = False`, erasing a request that arrived
    # between two reads - the canceller then blocked on an acknowledgement that never came.
    uart = make_uart()
    fake(uart).feed_rx(b"xy")

    async def reader() -> "list[object]":
        async with uart:
            first = await uart.read(2)
            await asyncio.sleep_ms(_LOCKED_WORK_MS)  # cancel lands in here, with no ready() in flight
            second = await uart.read(2, timeout_ms=-1)
            return [first, second]

    async def scenario() -> "tuple[list[object], bool]":
        task = asyncio.create_task(reader())
        await asyncio.sleep_ms(_TASK_INSIDE_MS)
        cancelled = await asyncio.wait_for(uart.cancel_read_timeout(), _STEP_BOUND_S)
        return await asyncio.wait_for(task, _STEP_BOUND_S), cancelled

    results, cancelled = run(scenario())
    assert cancelled is True
    assert results[0] == b"xy"
    assert results[1] is None  # the latched cancel aborts the *next* read rather than vanishing



def test_two_concurrent_cancellers_both_return() -> None:
    # The acknowledgement is broadcast - one canceller consuming it must not strand another.
    uart = make_uart()

    async def waiter() -> bytes | None:
        async with uart:
            return await uart.read(timeout_ms=-1)

    async def scenario() -> "tuple[bool, bool]":
        task = asyncio.create_task(waiter())
        await asyncio.sleep_ms(_TASK_INSIDE_MS)
        first = asyncio.create_task(uart.cancel_read_timeout())
        second = asyncio.create_task(uart.cancel_read_timeout())
        results = (await asyncio.wait_for(first, _STEP_BOUND_S), await asyncio.wait_for(second, _STEP_BOUND_S))
        await asyncio.wait_for(task, _STEP_BOUND_S)
        return results

    first_result, second_result = run(scenario())
    assert first_result is True
    assert second_result is True



def test_no_read_happens_after_the_cancel_is_acknowledged() -> None:
    # Acknowledgement means "the read path has left the loop", not "it is about to": bytes arriving
    # after it stay in the ring, unread.
    uart = make_uart()

    async def waiter() -> bytes | None:
        async with uart:
            return await uart.read(timeout_ms=-1)

    async def scenario() -> "bytes | None":
        task = asyncio.create_task(waiter())
        await asyncio.sleep_ms(_TASK_INSIDE_MS)
        await asyncio.wait_for(uart.cancel_read_timeout(), _STEP_BOUND_S)
        fake(uart).feed_rx(b"late")
        return await asyncio.wait_for(task, _STEP_BOUND_S)

    assert run(scenario()) is None
    assert uart._rx_level() == 4  # nothing was consumed after the acknowledgement


def test_cancel_with_a_wedged_holder_is_bounded_and_counted() -> None:
    # J.5's "provably terminating" half: a lock holder that never calls ready() again and never
    # exits cannot make cancel_read_timeout() block forever. It returns True (a cancel is
    # outstanding, so clear() must not then take the lock) and records the un-acknowledged case.
    uart = make_uart()

    async def wedged() -> None:
        async with uart:
            await asyncio.sleep_ms(400)  # never touches the bus again

    async def scenario() -> "tuple[bool, int]":
        task = asyncio.create_task(wedged())
        await asyncio.sleep_ms(_TASK_INSIDE_MS)
        result = await asyncio.wait_for(uart.cancel_read_timeout(timeout_ms=_SHORT_CANCEL_ACK_MS), _STEP_BOUND_S)
        unacked = uart.cancel_unacknowledged
        await asyncio.wait_for(task, _STEP_BOUND_S)
        return result, unacked

    result, unacked = run(scenario())
    assert result is True
    assert unacked == 1


def test_leaving_the_locked_region_acknowledges_a_latched_cancel() -> None:
    # The other half of J.5's handshake: the request is acknowledged on every exit from
    # the locked region, not only from inside ready()'s loop.
    uart = make_uart()

    async def holder() -> None:
        async with uart:
            await asyncio.sleep_ms(_HOLDER_WORK_MS)

    async def scenario() -> "tuple[bool, int]":
        task = asyncio.create_task(holder())
        await asyncio.sleep_ms(_TASK_INSIDE_MS)
        result = await asyncio.wait_for(uart.cancel_read_timeout(timeout_ms=_CANCEL_ACK_MS), _STEP_BOUND_S)
        await asyncio.wait_for(task, _STEP_BOUND_S)
        return result, uart.cancel_unacknowledged

    result, unacked = run(scenario())
    assert result is True
    assert unacked == 0  # acknowledged by the __aexit__, well inside the bound



def test_a_new_ready_call_does_not_clear_an_unrelated_cancel() -> None:
    # At the unit level: entering ready() must not consume a request it did not serve.
    uart = make_uart()
    fake(uart).feed_rx(b"x")  # readiness is there, so only the cancel can make ready() report False
    uart._cancel = True
    assert run(one_shot_ready(uart)) is False  # the latched cancel wins over readiness
    assert uart._cancel is False  # and is consumed exactly once


async def one_shot_ready(uart: UART) -> bool:
    async with uart:
        return await uart.ready(select.POLLIN, timeout_ms=_READY_TIMEOUT_MS)


# ---------------------------------------------------------------------------
# read / readinto / readline - single-round
# ---------------------------------------------------------------------------



def test_read_returns_bytes_once_ready() -> None:
    uart = make_uart()
    fake(uart).feed_rx(b"hello")

    async def scenario() -> bytes | None:
        async with uart:
            return await uart.read()

    assert run(scenario()) == b"hello"



def test_read_returns_none_on_timeout() -> None:
    uart = make_uart()  # nothing arrives

    async def scenario() -> bytes | None:
        async with uart:
            return await uart.read(timeout_ms=_NO_DATA_TIMEOUT_MS)

    assert run(scenario()) is None


def test_read_with_explicit_nbytes_reads_exactly_that_many_bytes() -> None:
    uart = make_uart()
    fake(uart).feed_rx(b"hello world")

    async def scenario() -> bytes | None:
        async with uart:
            return await uart.read(5)

    assert run(scenario()) == b"hello"


def test_readinto_fills_buffer_and_returns_count() -> None:
    uart = make_uart()
    fake(uart).feed_rx(b"hi")
    buf = bytearray(4)

    async def scenario() -> int | None:
        async with uart:
            return await uart.readinto(buf)

    assert run(scenario()) == 2
    assert bytes(buf[:2]) == b"hi"


def test_readinto_with_explicit_nbytes_reads_exactly_that_many_bytes() -> None:
    uart = make_uart()
    fake(uart).feed_rx(b"hello world")
    buf = bytearray(11)

    async def scenario() -> int | None:
        async with uart:
            return await uart.readinto(buf, 5)

    assert run(scenario()) == 5
    assert bytes(buf[:5]) == b"hello"


def test_readline_returns_bytes_once_ready() -> None:
    uart = make_uart()
    fake(uart).feed_rx(b"line\n")

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
    fake(uart).feed_rx(b"ab")  # round 1 sees only this; the rest arrives while the read waits

    async def scenario() -> bytearray | None:
        async with uart:
            feeder = asyncio.create_task(feed_after(uart, b"cde"))
            got = await uart.read_until_complete(5, start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS)
            await feeder
            return got

    assert run(scenario()) == bytearray(b"abcde")


def test_read_until_complete_default_crc_is_pass_through() -> None:
    uart = make_uart()
    assert isinstance(uart.crc, CRCPass)
    fake(uart).feed_rx(b"raw")

    async def scenario() -> bytearray | None:
        async with uart:
            return await uart.read_until_complete(3)

    assert run(scenario()) == bytearray(b"raw")


def test_read_until_complete_strips_and_verifies_real_crc() -> None:
    uart = make_uart(crc=CRC16())
    framed = run(CRC16().add(bytearray(b"hello")))
    assert framed is not None
    fake(uart).feed_rx(bytes(framed))

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
    fake(uart).feed_rx(b"partial-")  # round 1 sees only this - no \n yet

    async def scenario() -> bytearray | None:
        async with uart:
            feeder = asyncio.create_task(feed_after(uart, b"line\n"))
            got = await uart.readline_until_complete(start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS)
            await feeder
            return got

    assert run(scenario()) == bytearray(b"partial-line\n")



def test_a_line_split_across_the_ring_end_reads_whole() -> None:
    # Read from the ring by index, never through the FIFO API: a line wrapping past the last ring byte
    # comes back whole and in order.
    uart = make_uart(rx_ring=16)
    skip_ahead(uart, 12)
    fake(uart).feed_rx(b"wrapped\n")

    async def scenario() -> bytearray | None:
        async with uart:
            return await uart.readline_until_complete(start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS)

    assert run(scenario()) == bytearray(b"wrapped\n")
    assert fake(uart).rx_api_calls == 0


# ---------------------------------------------------------------------------
# write / writefrom
# ---------------------------------------------------------------------------


def test_write_empty_message_succeeds_without_touching_the_bus() -> None:
    # write() returns before the CRC and codec when there is nothing to send - mirrors
    # test_read_until_complete_zero_nbytes_returns_empty_immediately on the read side, so it must
    # not block waiting on ready(POLLOUT) for a write that never happens.
    uart = make_uart()

    async def scenario() -> bool:
        async with uart:
            return await uart.write(bytearray())

    assert run(scenario()) is True
    assert fake(uart).log == []


def test_write_default_crc_is_pass_through() -> None:
    uart = make_uart()

    async def scenario() -> bool:
        async with uart:
            return await uart.write(bytearray(b"raw"))

    assert run(scenario()) is True
    assert fake(uart).log[-1] == ("write", b"raw")


def test_write_frames_with_configured_crc() -> None:
    uart = make_uart(crc=CRC16())

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
        await asyncio.sleep_ms(_TASK_INSIDE_MS)  # let writer enter ready()'s poll loop, holding the lock
        cancelled = await uart.cancel_read_timeout()
        result = await asyncio.wait_for(task, _STEP_BOUND_S)
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
    # Regression test: write()'s return value used to be discarded, silently dropping the tail of a
    # message larger than the TX ring's free room - real, since rp2's own write() can return a short
    # count. write_limit=3 makes a 7-byte message need three rounds (3+3+1).
    uart = make_uart()
    fake(uart).write_limit = 3

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

    async def scenario() -> bool:
        async with uart:
            return await uart.write(bytearray(b"x"))

    assert run(scenario()) is False
    assert fake(uart).log == []  # nothing was ever actually recorded as sent


def test_writefrom_retries_after_a_short_write_until_everything_is_sent() -> None:
    uart = make_uart(crc=CRC16())
    fake(uart).write_limit = 4
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
# asy_base_classes.Lockable integration - real inheritance (UART(Lockable)), not
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
        assert not uart.session_lock.locked()
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
            uart.session_lock.release()  # released early by hand
        # __aexit__'s own release() must swallow the resulting RuntimeError, not propagate it

    run(scenario())  # must not raise
    assert not uart.session_lock.locked()


def test_task_cancellation_while_holding_the_lock_still_releases_it() -> None:
    # Interrupts a session via real asyncio cancellation, not just an exception raised by our own code -
    # MicroPython's asyncio still runs __aexit__ via CancelledError propagating through `async with`, as
    # CPython does. Confirmed for I2CDevice; UART(Lockable) shares that exact implementation.
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
        assert uart.session_lock.locked()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert not uart.session_lock.locked()

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
            await asyncio.wait_for(reentrant(), _DEADLOCK_WAIT_S)
        except asyncio.TimeoutError:
            return True
        else:
            return False

    assert run(scenario())
    assert not uart.session_lock.locked()


# ---------------------------------------------------------------------------
# asy_crc_checks.py integration - real CRCBase subclasses (not mocked), plus
# MemoryError fault injection at the guarded call sites (module docstring's
# "MemoryError guarding" section)
# ---------------------------------------------------------------------------


class _MemoryErrorCRC:
    # Wraps a real CRCBase so length(), which read_until_complete() needs, keeps working while
    # add()/check() raise MemoryError instead of doing real work - the UDP socket suite's own technique,
    # proving asy_uart_driver.py's try/except around these two calls actually catches it.
    def __init__(self, real: "CRCBase") -> None:
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
    # A real CRCBase's add() only ever returns None via its own _validate_init() rejecting an explicit init
    # argument, which write() never passes, so this path is unreachable through any real CRC object. A
    # minimal fake matching just the add()/length() surface write() calls, like _MemoryErrorCRC above.
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

    async def scenario() -> bytearray | None:
        async with uart:
            return await uart.read_until_complete(5)

    assert run(scenario()) is None


# The frame buffer's own MemoryError guard is not fault-injected: unlike self.crc, the
# bytearray has no substitutable object and no hook to force the raise deterministically.
# A documented gap (SPECIFICATION.md Part E); the multi-round assembly tests still cover the line.


# ---------------------------------------------------------------------------
# Every read copies from the ring by index, clamped to its fill level
# ---------------------------------------------------------------------------
# machine.UART.read() waits out timeout_char per requested byte without yielding (SPECIFICATION.md Part
# F.5.8), so the driver never calls the FIFO API at all: every read copies what the ring already holds.



def test_a_multi_round_read_copies_only_what_has_arrived() -> None:
    uart = make_uart()
    fake(uart).feed_rx(b"ab")  # only two of the five bytes have "arrived" when the read starts
    buf = bytearray(5)

    async def scenario() -> int | None:
        async with uart:
            feeder = asyncio.create_task(feed_after(uart, b"cde"))
            got = await uart.readinto_until_complete(buf, 5, start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS)
            await feeder
            return got

    assert run(scenario()) == 5
    assert bytes(buf) == b"abcde"
    assert fake(uart).rx_api_calls == 0



def test_single_shot_reads_clamp_to_what_is_buffered_and_report_nothing_as_none() -> None:
    uart = make_uart()
    fake(uart).feed_rx(b"xyz")

    async def read_scenario() -> bytes | None:
        async with uart:
            return await uart.read(64)  # asks far past what has arrived

    assert run(read_scenario()) == b"xyz"
    uart2 = make_uart()

    async def empty_scenario() -> int | None:
        async with uart2:
            return await uart2.readinto(bytearray(8), 8, timeout_ms=_NO_DATA_TIMEOUT_MS)

    assert run(empty_scenario()) is None  # nothing buffered: the documented None


def test_a_negative_count_reads_nothing_and_consumes_nothing() -> None:
    # A negative count used to reach machine.UART.read(-1) - a read-all that waits out the UART's timeout
    # (py/stream.c) - and readinto(); clamped at zero, the read reports nothing and the bytes stay put.
    uart = make_uart()
    fake(uart).feed_rx(b"abc")

    async def scenario() -> "tuple[Any, Any]":
        async with uart:
            return await uart.read(-1), await uart.readinto(bytearray(8), -5)

    assert run(scenario()) == (None, None)
    assert uart._rx_level() == 3


def test_read_until_complete_refuses_a_negative_size() -> None:
    # The read side's twin of writefrom()'s negative-size refusal; zero stays "nothing to transfer".
    uart = make_uart()
    fake(uart).feed_rx(b"abc")
    assert run(locked_read_until_complete(uart, -1)) is None
    assert run(locked_read_until_complete(uart, 0)) == bytearray()
    assert uart._rx_level() == 3


def test_readinto_until_complete_refuses_a_negative_size() -> None:
    uart = make_uart()
    fake(uart).feed_rx(b"abc")
    assert run(locked_readinto_until_complete(uart, bytearray(8), -1)) is None
    assert run(locked_readinto_until_complete(uart, bytearray(8), 0)) == 0
    assert uart._rx_level() == 3


def test_a_delimited_read_refuses_a_negative_size() -> None:
    uart = cobs_uart()
    fake(uart).feed_rx(b"\x02\x41\x00")  # one whole encoded frame, waiting unread
    assert run(locked_read_until_complete(uart, -1)) is None
    assert run(locked_readinto_until_complete(uart, bytearray(64), -1)) is None
    assert uart._rx_level() == 3


# ---------------------------------------------------------------------------
# ready() is this driver's one yield point, and it has two poll rates
# ---------------------------------------------------------------------------
# Every read loop reaches the peripheral through ready(), so "ready() always yields" bounds how long
# any of them holds the loop. The clamp alone made the stall worse, ipoll() reporting the mask with
# no await of its own (SPECIFICATION.md Part F.5.8).



def test_ready_yields_even_when_the_mask_is_already_satisfied() -> None:
    uart = make_uart()
    fake(uart).feed_rx(b"x")  # the fill level reports the mask on the very first round
    ran: list[int] = []

    async def competitor() -> None:
        ran.append(1)

    async def scenario() -> bool:
        async with uart:
            other = asyncio.create_task(competitor())  # runnable, but only if ready() yields
            got = await uart.ready(select.POLLIN, timeout_ms=_READY_TIMEOUT_MS)
            assert ran, "ready() returned True without yielding: a read loop through it cannot be preempted"
            await other
            return got

    assert run(scenario()) is True



def test_a_deadlineless_wait_polls_at_the_idle_rate_and_a_bounded_one_does_not() -> None:
    # A wait with no deadline is an idle listener waiting for traffic that may never come; one with
    # a deadline is inside a transaction. A byte arriving a few ms in is noticed one poll later (F.5.9).
    async def wait_on(uart: UART, timeout_ms: int) -> int:
        async with uart:
            feeder = asyncio.create_task(feed_after(uart, b"x"))
            t0 = time.ticks_ms()
            assert await uart.ready(select.POLLIN, timeout_ms=timeout_ms) is True
            elapsed = time.ticks_diff(time.ticks_ms(), t0)
            await feeder
            return elapsed

    idle = make_uart(poll_wait_ms=_POLL_WAIT_MS, poll_idle_ms=_IDLE_POLL_MS)
    assert run(wait_on(idle, -1)) >= _IDLE_POLL_MS
    bounded = make_uart(poll_wait_ms=_POLL_WAIT_MS, poll_idle_ms=_IDLE_POLL_MS)
    assert run(wait_on(bounded, 1000)) < _IDLE_POLL_MS



def test_uncounted_reads_are_clamped_to_what_is_buffered_too() -> None:
    # read()/readinto() with no count copy what the ring holds, never the whole buffer's worth.
    uart = make_uart()
    fake(uart).feed_rx(b"hi")

    async def read_scenario() -> bytes | None:
        async with uart:
            return await uart.read()

    assert run(read_scenario()) == b"hi"
    uart2 = make_uart()
    fake(uart2).feed_rx(b"hi")

    async def readinto_scenario() -> int | None:
        async with uart2:
            return await uart2.readinto(bytearray(64))

    assert run(readinto_scenario()) == 2



def test_readline_reads_the_ring_never_the_fifo_api() -> None:
    # Read from the ring by index, never through the FIFO API: an empty ring is no line, and a line is
    # cut at its LF with the rest left for the next read.
    uart = make_uart()

    async def scenario() -> "tuple[Any, Any, Any]":
        async with uart:
            empty = await uart.readline(timeout_ms=_NO_DATA_TIMEOUT_MS)
            fake(uart).feed_rx(b"one\ntwo")
            return empty, await uart.readline(), await uart.readline()

    assert run(scenario()) == (None, b"one\n", b"two")
    assert fake(uart).rx_api_calls == 0



def test_a_delimited_frame_read_across_rounds_reads_the_ring_only() -> None:
    # _read_delimited() takes one byte at a time (a wider read would swallow the next frame's head),
    # each copied from the ring; a frame arriving in two parts is assembled across rounds.
    sender = cobs_uart()
    payload = bytearray(b"\x09\x00\x0a")
    assert run(locked_write(sender, bytearray(payload))) is True
    frame = written(sender)
    receiver = cobs_uart()
    fake(receiver).feed_rx(frame[:2])

    async def scenario() -> "bytearray | None":
        async with receiver:
            feeder = asyncio.create_task(feed_after(receiver, frame[2:]))
            got = await receiver.read_until_complete(len(payload), start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS)
            await feeder
            return got

    got = run(scenario())
    assert got is not None and bytes(got) == bytes(payload), got
    assert fake(receiver).rx_api_calls == 0


# ---------------------------------------------------------------------------
# The never-raises contract's own edges: a raising any(), a read that comes
# back empty after reporting ready, and the delimited path's own failures
# ---------------------------------------------------------------------------


class _NamelessDelimiter(FramingBase):
    # Reports itself delimited but names no delimiter byte - inconsistent by construction, which is
    # precisely what the read path's own guard is for: there is nothing to frame on.
    def is_delimited(self) -> bool:
        return True




def test_a_closed_receive_channel_reads_as_a_silent_line() -> None:
    # rp2.DMA raises ValueError("channel closed") for a closed channel's count (rp2_dma.c), which only its
    # finaliser does here. The read neither raises nor fails at once: it waits out its timeout as on a silent
    # line, so a listener on a dead ring idles at its poll rate instead of failing and logging every round.
    uart = make_uart()
    fake(uart).feed_rx(b"abcd")
    channel = uart._rx_dma
    assert channel is not None
    channel.close()

    async def scenario() -> "tuple[Any, Any, Any, int]":
        async with uart:
            t0 = time.ticks_ms()
            got = await uart.read(4, timeout_ms=_NO_DATA_TIMEOUT_MS)
            waited = time.ticks_diff(time.ticks_ms(), t0)
            return got, await uart.readinto(bytearray(4), timeout_ms=_NO_DATA_TIMEOUT_MS), await uart.readline(timeout_ms=_NO_DATA_TIMEOUT_MS), waited

    read, readinto, readline, waited = run(scenario())
    assert (read, readinto, readline) == (None, None, None)
    assert waited >= _NO_DATA_TIMEOUT_MS, waited


class _LappingChannel:
    # Stands in for the data channel at the post-copy check: its count reports the producer a whole
    # ring ahead, as when the DMA overtakes a copy in progress.
    def __init__(self, real: "Any", ring: int) -> None:
        self._real = real
        self._ring = ring

    @property
    def count(self) -> int:
        count: int = self._real.count
        return count - self._ring - 1


def test_bytes_lapped_during_the_copy_fail_the_read() -> None:
    # A copy is checked again after it: bytes the DMA overwrote while they were being copied are no data,
    # so the copy fails, the overrun is counted and nothing is consumed as if read.
    uart = make_uart(rx_ring=16)
    fake(uart).feed_rx(b"abcd")
    assert uart._rx_level() == 4
    real = uart._rx_dma
    uart._rx_dma = _LappingChannel(real, 16)  # type: ignore[assignment]
    before = uart.rx_overruns
    assert uart._rx_copy(bytearray(4), 0, 4) == -1
    assert uart.rx_overruns == before + 1


def test_the_allocating_read_yields_rather_than_spinning_on_an_empty_ring() -> None:
    # Nothing buffered yet: the loop must hand the scheduler a turn instead of calling ready() again
    # at once, which on real hardware burns the whole latency budget inside one task.
    uart = make_uart(poll_wait_ms=_POLL_WAIT_MS)

    async def scenario() -> "bytearray | None":
        async with uart:
            feeder = asyncio.create_task(feed_after(uart, b"abcd"))
            got = await uart.read_until_complete(4, start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS)
            await feeder
            return got

    got = run(scenario())
    assert got is not None and bytes(got) == b"abcd", got


def test_a_delimited_read_with_nothing_on_the_line_times_out_on_both_paths() -> None:
    # The delimited path's own deadline. With no byte to inspect the loop never reaches the
    # delimiter check at all, so ending the wait is ready()'s job - and the allocating read then
    # has to turn _read_delimited()'s sentinel into its own rather than returning a partial frame.
    uart = cobs_uart()
    assert run(locked_readinto_until_complete(uart, bytearray(64), 8, start_timeout_ms=_SILENT_LINE_TIMEOUT_MS, timeout_ms=_SILENT_LINE_TIMEOUT_MS)) is None
    assert run(locked_read_until_complete(uart, 8, start_timeout_ms=_SILENT_LINE_TIMEOUT_MS, timeout_ms=_SILENT_LINE_TIMEOUT_MS)) is None


def test_a_delimited_codec_that_names_no_delimiter_fails_the_read() -> None:
    # A codec cannot be framed on nothing, so the read path checks rather than trusting that
    # is_delimited() and delimiter() agree - the same shape as every other sentinel here.
    uart = make_uart(framing=_NamelessDelimiter(64, run_length=254, trailer=1))
    fake(uart).feed_rx(b"\x01\x02\x03")
    assert run(locked_readinto_until_complete(uart, bytearray(64), 2, start_timeout_ms=30, timeout_ms=30)) is None
    assert run(locked_read_until_complete(uart, 2, start_timeout_ms=30, timeout_ms=30)) is None
    # Refused before the first byte, not after reading a whole worst-case frame looking for a
    # delimiter that does not exist - which is the difference the guard actually makes.
    assert uart._rx_level() == 3, uart._rx_level()


def test_a_delimited_read_whose_worst_case_buffer_will_not_fit_fails_cleanly() -> None:
    # read_until_complete() sizes its own buffer from the codec's worst case, so a length
    # the heap cannot serve has to come back as the sentinel - not as a MemoryError out of a driver
    # contracted never to raise, and not as a read against a buffer that was never allocated.
    uart = cobs_uart(max_frame=1 << 30)
    assert run(locked_read_until_complete(uart, 1 << 30, start_timeout_ms=10, timeout_ms=10)) is None


def test_a_delimited_frame_longer_than_the_yield_interval_still_yields() -> None:
    # _read_delimited() consumes one buffered byte per round without ever reaching ready()'s own
    # yield, so a frame longer than the yield interval would hold the loop for its whole wire time.
    # Measured against a competing task rather than asserted: the count is what proves the yield.
    sender = cobs_uart()
    assert run(locked_write(sender, bytearray(b"\x41" * 40))) is True  # well past the 16-byte interval
    receiver = cobs_uart()
    fake(receiver).feed_rx(written(sender))
    turns = [0]

    async def competitor() -> None:
        while True:
            turns[0] += 1
            await asyncio.sleep_ms(0)

    async def scenario() -> "bytearray | None":
        other = asyncio.create_task(competitor())
        try:
            return await locked_read_until_complete(receiver, 40, start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS)
        finally:
            other.cancel()
            try:
                await other  # awaited out, so no task is left parked in the shared queue
            except asyncio.CancelledError:  # expected; anything else is a real failure
                pass

    got = run(scenario())
    assert got is not None and bytes(got) == b"\x41" * 40, got
    assert turns[0] >= 2, turns[0]  # 40 bytes / 16 per yield, so the loop gave up the CPU twice


def test_a_crc_framed_write_of_nothing_succeeds_and_sends_nothing() -> None:
    # A zero-length payload is nothing to transfer: writefrom() reports success and sends nothing, never a bare CRC.
    uart = make_uart(crc=CRC16())
    assert run(locked_writefrom(uart, bytearray(8), 0)) is True
    assert written(uart) == b""


def test_a_crc_framed_read_of_nothing_returns_empty() -> None:
    # Bytes already waiting stay unread: a read of nothing never consumes a frame as a bare CRC.
    uart = make_uart(crc=CRC16())
    fake(uart).feed_rx(b"abc")
    assert run(locked_read_until_complete(uart, 0)) == bytearray()
    assert run(locked_readinto_until_complete(uart, bytearray(8), 0)) == 0
    assert fake(uart).log == []
    assert uart._rx_level() == 3


def test_a_zero_length_payload_is_nothing_to_transfer_in_every_crc_and_codec_mode() -> None:
    # Every CRC and codec pairing: writes report success and send nothing, reads return an empty
    # result without touching the bus.
    for crc, framing in ((CRCPass(), FramingPass()), (CRC16(), FramingPass()), (CRCPass(), FramingCOBS(64)), (CRC16(), FramingCOBS(64))):
        uart = make_uart(crc=crc, framing=framing)
        fake(uart).feed_rx(b"\x01\x00")  # one encoded empty COBS frame, waiting unread
        assert run(locked_write(uart, bytearray())) is True
        assert run(locked_writefrom(uart, bytearray(8), 0)) is True
        assert run(locked_read_until_complete(uart, 0)) == bytearray()
        assert run(locked_readinto_until_complete(uart, bytearray(8), 0)) == 0
        assert fake(uart).log == []
        assert uart._rx_level() == 2

def test_a_readline_that_never_becomes_ready_returns_the_sentinel() -> None:
    # readline() has no count to clamp, so its only bound is ready()'s deadline - a line that never
    # starts must end the call rather than leave a caller parked on a silent peer.
    uart = make_uart()

    async def scenario() -> "bytes | None":
        async with uart:
            return await uart.readline(timeout_ms=_SILENT_LINE_TIMEOUT_MS)

    assert run(scenario()) is None


# ---------------------------------------------------------------------------
# Default poll rates, and writes only into an empty TX ring
# ---------------------------------------------------------------------------


def test_the_default_rates_are_two_and_fifty_ms() -> None:
    uart = UART(0, tx_pin=0, rx_pin=1)  # built directly: make_uart() pins this file's own 1/1 rates
    assert uart.poll_wait_ms == 2
    assert uart.poll_idle_ms == 50


def test_a_long_message_goes_out_in_txbuf_sized_writes() -> None:
    # POLLOUT means one free TX ring byte, and a longer write waits per byte inside machine.UART.write()
    # (F.5.8): no single write asks for more than an empty ring holds.
    uart = make_uart(txbuf=32)
    payload = bytearray(range(96))
    assert run(locked_write(uart, payload)) is True
    writes = [entry[1] for entry in fake(uart).log if entry[0] == "write"]
    assert [len(w) for w in writes] == [32, 32, 32], [len(w) for w in writes]
    assert b"".join(writes) == bytes(payload)


def test_no_write_happens_while_the_ring_is_draining() -> None:
    # txdone() false means the previous write is still on its way out: no write that round, and the
    # loop yields while it waits.
    uart = make_uart(txbuf=32)
    fk = fake(uart)
    fk.tx_pending_rounds = 3
    writes_seen: list[int] = []
    real_txdone = fk.txdone

    def spy() -> bool:
        writes_seen.append(len([entry for entry in fk.log if entry[0] == "write"]))
        return real_txdone()

    fk.txdone = spy  # type: ignore[method-assign]
    turns = [0]

    async def counter() -> None:
        while True:
            turns[0] += 1
            await asyncio.sleep_ms(0)

    async def scenario() -> bool:
        other = asyncio.create_task(counter())
        try:
            return await locked_write(uart, bytearray(b"abc"))
        finally:
            other.cancel()
            try:
                await other  # awaited out, so no task is left parked in the shared queue
            except asyncio.CancelledError:  # expected; anything else is a real failure
                pass

    assert run(scenario()) is True
    assert writes_seen[:4] == [0, 0, 0, 0], writes_seen  # three draining rounds, then the one that writes
    assert [entry[0] for entry in fk.log].count("write") == 1
    assert turns[0] >= 3, turns[0]


def test_cancel_or_deinit_during_the_drain_wait_returns_false() -> None:
    for action in ("cancel", "deinit"):
        uart = make_uart()
        fk = fake(uart)
        fk.tx_pending_rounds = 1 << 20  # the line never goes idle on its own

        async def writer(u: UART = uart) -> bool:
            async with u:
                return await u.write(bytearray(b"x"))

        async def scenario(u: UART = uart, act: str = action) -> bool:
            task = asyncio.create_task(writer())
            await asyncio.sleep_ms(_TASK_INSIDE_MS)
            if act == "cancel":
                await u.cancel_read_timeout()
            else:
                u.deinit()
            return await asyncio.wait_for(task, _STEP_BOUND_S)

        assert run(scenario()) is False, action
        assert not [entry for entry in fk.log if entry[0] == "write"], action


# ---------------------------------------------------------------------------
# Delimited reads yield on every consumed byte; ready() re-checks after its yield
# ---------------------------------------------------------------------------


def test_a_run_of_delimiters_lets_another_task_run() -> None:
    # The skip branches consume a buffered byte per round too, so they count toward the yield.
    sender = cobs_uart()
    assert run(locked_write(sender, bytearray(b"\x41\x42"))) is True
    receiver = cobs_uart()
    fake(receiver).feed_rx(bytes([COBS_DELIMITER]) * 64 + written(sender))
    turns = [0]

    async def counter() -> None:
        while True:
            turns[0] += 1
            await asyncio.sleep_ms(0)

    async def scenario() -> "bytearray | None":
        other = asyncio.create_task(counter())
        try:
            return await locked_read_until_complete(receiver, 2, start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS)
        finally:
            other.cancel()
            try:
                await other
            except asyncio.CancelledError:
                pass

    got = run(scenario())
    assert got is not None and bytes(got) == b"\x41\x42", got
    assert turns[0] >= 4, turns[0]  # 64 delimiters, a yield every 16


def test_a_deinit_during_readys_closing_yield_hands_back_no_dead_uart() -> None:
    # Another task may deinit() the bus during ready()'s closing yield: the caller gets the sentinel,
    # never a read or write on the dead UART.
    for op in ("read", "readinto_until_complete", "write"):
        uart = make_uart()
        fk = fake(uart)
        fk.feed_rx(b"abcd")

        async def killer(u: UART = uart) -> None:
            u.deinit()

        async def scenario(u: UART = uart, which: str = op) -> object:
            result: object
            async with u:
                killing = asyncio.create_task(killer())  # runnable from ready()'s closing yield on
                if which == "read":
                    result = await u.read(4)
                elif which == "readinto_until_complete":
                    result = await u.readinto_until_complete(bytearray(4), 4)
                else:
                    result = await u.write(bytearray(b"x"))
            await killing
            return result

        assert run(scenario()) in (None, False), op
        assert not [entry for entry in fk.log if entry[0] == "write"], op
        assert uart._rx_pos == 0, op  # nothing was consumed from the ring


def test_a_deinit_during_the_delimited_reads_periodic_yield_ends_the_read() -> None:
    sender = cobs_uart()
    assert run(locked_write(sender, bytearray(b"\x41" * 40))) is True
    receiver = cobs_uart()
    fake(receiver).feed_rx(written(sender))

    async def killer() -> None:
        receiver.deinit()

    async def scenario() -> "bytearray | None":
        async with receiver:
            killing = asyncio.create_task(killer())  # first runs at the yield after 16 consumed bytes
            got = await receiver.read_until_complete(40, start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS)
        await killing
        return got

    assert run(scenario()) is None


def test_an_idle_wait_beyond_the_ticks_range_returns_false() -> None:
    # asyncio.sleep_ms() raises OverflowError for a delta of half the ticks period or more; ready()
    # degrades that to False like a malformed mask. 2**61 is the 64-bit Unix port's half-period.
    try:
        time.ticks_add(time.ticks_ms(), 2**61)
        raised = False
    except OverflowError:
        raised = True
    assert raised, "this interpreter's ticks period is not 2**62: the wait below would not reach the degrade path"
    uart = make_uart(poll_idle_ms=2**61)  # an empty ring, so the first round sleeps the idle rate

    async def scenario() -> bool:
        async with uart:
            return await uart.ready(select.POLLIN, timeout_ms=-1)

    assert run(scenario()) is False


# ---------------------------------------------------------------------------
# The DMA receive ring
# ---------------------------------------------------------------------------


class _ChannelProbe:
    # Wraps the data channel: records whether WRITE_ADDR was ever read (RP2040-E12: it reads wrong
    # during ring transfers) and the receive mask at the moment the channel is configured.
    def __init__(self, real: "Any") -> None:
        self._real = real
        self.write_reads = 0
        self.imsc_at_config: list[int] = []
        self.channel = real.channel

    @property
    def count(self) -> int:
        count: int = self._real.count
        return count

    @property
    def write(self) -> int:
        self.write_reads += 1
        address: int = self._real.write
        return address

    def active(self, value: "bool | None" = None) -> bool:
        result: bool = self._real.active(value)
        return result

    def config(self, **kwargs: "Any") -> None:
        self.imsc_at_config.append(mem32[_UART0_IMSC])
        self._real.config(**kwargs)

    def pack_ctrl(self, **kwargs: "Any") -> int:
        ctrl: int = self._real.pack_ctrl(**kwargs)
        return ctrl


def test_every_init_clears_the_rx_interrupt_mask_and_enables_rx_dma() -> None:
    # machine.UART enables its RX and RX-timeout interrupts at every construction, and their handler
    # drains the FIFO the ring reads: after setup and after each re-init the mask is clear, RX DMA on.
    uart = make_uart()
    for _ in range(3):
        assert mem32[_UART0_IMSC] & _IMSC_RX == 0, hex(mem32[_UART0_IMSC])
        assert mem32[_UART0_DMACR] & _DMACR_RXDMAE, hex(mem32[_UART0_DMACR])
        uart.init(0, 0, 1)
        unpaced(uart)


def test_a_re_init_masks_first_and_fails_the_next_read() -> None:
    # The mask is cleared before the ring is re-armed, and the restarted stream's first read fails as an
    # overrun: a byte the interrupt handler took before the mask is never stitched into a frame.
    uart = make_uart()
    probe = _ChannelProbe(uart._rx_dma)
    uart._rx_dma = probe  # type: ignore[assignment]
    uart.init(0, 0, 1)
    unpaced(uart)
    assert probe.imsc_at_config, "the re-init did not re-arm the ring"
    assert all(imsc & _IMSC_RX == 0 for imsc in probe.imsc_at_config), probe.imsc_at_config
    fake(uart).feed_rx(b"abcd")
    assert run(locked_readinto_until_complete(uart, bytearray(4), 4, start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS)) is None
    fake(uart).feed_rx(b"wxyz")
    buf = bytearray(4)
    assert run(locked_readinto_until_complete(uart, buf, 4, start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS)) == 4
    assert bytes(buf) == b"wxyz"


def test_the_receive_path_never_touches_the_fifo_api() -> None:
    uart = make_uart()
    fake(uart).feed_rx(b"line\nabcdefgh")

    async def scenario() -> "tuple[Any, Any, Any, Any]":
        async with uart:
            line = await uart.readline()
            four = await uart.read(4)
            rest = await uart.readinto_until_complete(bytearray(4), 4)
            idle = await uart.ready(select.POLLIN, timeout_ms=_NO_DATA_TIMEOUT_MS)
            return line, four, rest, idle

    assert run(scenario()) == (b"line\n", b"abcd", 4, False)
    assert fake(uart).rx_api_calls == 0
    assert fake(uart).rxbuf == _UART_MIN_RXBUF


def test_progress_is_read_from_the_transfer_count_only() -> None:
    uart = make_uart()
    probe = _ChannelProbe(uart._rx_dma)
    uart._rx_dma = probe  # type: ignore[assignment]
    fake(uart).feed_rx(b"abcd")
    buf = bytearray(4)
    assert run(locked_readinto_until_complete(uart, buf, 4)) == 4
    assert bytes(buf) == b"abcd"
    assert probe.write_reads == 0


def test_the_count_reload_keeps_reception_going() -> None:
    # The data channel's count runs out every 2**29 bytes; the chained channel reloads it, no byte lost,
    # and the reload value keeps DMA.count a small int.
    uart = make_uart(rx_ring=16)
    skip_ahead(uart, _RX_RELOAD - 3)  # three transfers left before the reload
    fake(uart).feed_rx(b"0123456789")
    buf = bytearray(10)
    assert run(locked_readinto_until_complete(uart, buf, 10, start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS)) == 10
    assert bytes(buf) == b"0123456789"
    channel = uart._rx_dma
    assert channel is not None
    assert channel.count == _RX_RELOAD - 7
    assert channel.count <= (1 << 30) - 1


def test_the_fill_level_is_the_modular_difference_of_totals() -> None:
    uart = make_uart(rx_ring=16)
    skip_ahead(uart, _RX_RELOAD - 2)  # the totals cross the count's wrap below
    assert uart._rx_level() == 0
    fake(uart).feed_rx(b"abcde")
    assert uart._rx_level() == 5
    buf = bytearray(2)
    assert run(locked_readinto_until_complete(uart, buf, 2)) == 2
    assert uart._rx_level() == 3
    assert bytes(buf) == b"ab"


def test_a_frame_split_across_the_ring_end_reads_whole() -> None:
    payload = bytearray(b"\x10\x00\x20\x30\x40")
    for crc in (None, CRC16):
        for delimited in (False, True):
            sender = make_uart(crc=crc() if crc else None, framing=FramingCOBS(64) if delimited else FramingPass())
            assert run(locked_write(sender, bytearray(payload))) is True
            receiver = make_uart(rx_ring=64, crc=crc() if crc else None, framing=FramingCOBS(64) if delimited else FramingPass())
            skip_ahead(receiver, 61)  # the frame starts three bytes before the ring's end
            fake(receiver).feed_rx(written(sender))
            buf = bytearray(64)
            size = run(locked_readinto_until_complete(receiver, buf, len(payload), start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS))
            assert size == len(payload), (crc, delimited)
            assert bytes(buf[:size]) == bytes(payload), (crc, delimited)


def test_a_lap_is_an_overrun_never_data() -> None:
    # More unread bytes than the ring holds: the read fails, the overrun is counted, every unread byte
    # is dropped, and the next bytes read whole.
    uart = make_uart(rx_ring=16)
    fake(uart).feed_rx(bytes(range(20)))
    assert run(locked_readinto_until_complete(uart, bytearray(4), 4, start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS)) is None
    assert uart.rx_overruns == 1
    assert uart._rx_level() == 0
    fake(uart).feed_rx(b"wxyz")
    buf = bytearray(4)
    assert run(locked_readinto_until_complete(uart, buf, 4, start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS)) == 4
    assert bytes(buf) == b"wxyz"


def test_a_ring_size_the_dma_cannot_wrap_is_refused() -> None:
    for size in (0, 1, 3, 100, 65536):
        uart = UART(0, tx_pin=0, rx_pin=1, rx_ring=size)
        assert uart.setup_rx_ring() is False, size
        assert uart._ring is None and uart._rx_dma is None, size


def test_a_misaligned_ring_or_no_free_channel_is_refused_with_nothing_armed() -> None:
    real_addressof = asy_uart_driver.addressof
    asy_uart_driver.addressof = lambda obj: real_addressof(obj) + 1  # the window lands one byte off
    DMA.reset_registry()
    try:
        uart = UART(0, tx_pin=0, rx_pin=1)
        assert uart.setup_rx_ring() is False
        assert uart._ring is None and uart._rx_dma is None and uart._rx_reload is None
    finally:
        asy_uart_driver.addressof = real_addressof
    real_dma = asy_uart_driver.DMA

    def busy() -> "Any":
        raise OSError(16)  # EBUSY: rp2.DMA() with every channel claimed

    asy_uart_driver.DMA = busy  # type: ignore[assignment,misc]
    try:
        uart = UART(0, tx_pin=0, rx_pin=1)
        assert uart.setup_rx_ring() is False
        assert uart._ring is None and uart._rx_dma is None
    finally:
        asy_uart_driver.DMA = real_dma  # type: ignore[misc]


def test_the_ring_is_allocated_once_in_setup() -> None:
    uart = make_uart()
    ring = uart._ring
    assert uart.setup_rx_ring() is True  # a second setup reallocates nothing
    uart.init(0, 0, 1)  # nor does a re-init
    assert uart._ring is ring
    try:
        uart.init(0, 0, 1, rx_ring=1024)
        raised = False
    except ValueError:
        raised = True
    assert raised, "a re-init silently ignored a different ring size"
    assert uart._ring is ring


def test_a_read_retains_nothing() -> None:
    # 2,000 frame reads copied by index into one buffer grow the heap no more than 1,000 do: each run's
    # asyncio.run() leaves the same fixed residue, which the difference cancels, so any per-read retention shows.
    uart = make_uart()
    buf = bytearray(8)

    async def reads(n: int) -> int:
        done = 0
        async with uart:
            for _ in range(n):
                fake(uart).feed_rx(b"01234567")
                done += 1 if await uart.readinto_until_complete(buf, 8) == 8 else 0
        return done

    def grown(n: int) -> int:
        gc.collect()
        before = gc.mem_alloc()
        assert run(reads(n)) == n
        gc.collect()
        return gc.mem_alloc() - before

    assert run(reads(10)) == 10  # warm-up: every path taken before the heap is sampled
    # The fake's capped logs (mem32's above all) grow until they wrap once, by a count per read that varies with
    # poll rounds: reading on until each has wrapped, or a batch leaves it untouched, keeps that out of the samples.
    logs = (fake(uart).log, mem32.log)
    for _ in range(128):  # 8,192 reads: a 4,096-entry log wraps within them at one entry per read
        before = [(len(log), log.dropped) for log in logs]
        assert run(reads(64)) == 64
        if all(log.dropped >= log.maxlen or (len(log), log.dropped) == b for log, b in zip(logs, before)):  # noqa: B905 - MicroPython zip() rejects strict=
            break
    else:
        raise AssertionError("a fake log still grew after 8,192 reads")
    short = grown(1000)
    long = grown(2000)
    assert long <= short, (long, short)


def _frame(i: int) -> bytes:
    return bytes((i + k) & 0xFF for k in range(53))  # the dev link's 53-byte frame, distinct per index



def test_thousands_of_back_to_back_frames_at_line_rate_lose_nothing() -> None:
    # 5,000 frames arriving at 115200 baud's 11.52 B/ms on the fake clock, the consumer reading one frame
    # per frame of wire time, so the 512-byte ring sits at its fill boundary: nothing lost, no overrun.
    uart = make_uart(baudrate=115200)
    fake(uart).rx_rate = 0.0  # the line rate
    buf = bytearray(53)
    start = Timer.clock_ms

    async def scenario() -> int:
        intact = 0
        async with uart:
            for i in range(8):  # 424 bytes: eight frames' head start, so one arriving frame fills it to 477 of 512
                fake(uart).feed_rx(_frame(i))
            Timer.clock_ms += 37  # their wire time
            for i in range(5000):
                fake(uart).feed_rx(_frame(i + 8))
                Timer.clock_ms += 5  # one frame's wire time, rounded up: 57.6 bytes of credit
                if await uart.readinto_until_complete(buf, 53) != 53 or bytes(buf) != _frame(i):
                    return intact
                intact += 1
        return intact

    try:
        assert run(scenario(), _HAMMER_BOUND_S) == 5000
    finally:
        Timer.clock_ms = start
    assert uart.rx_overruns == 0



def test_random_consumer_stalls_within_and_beyond_the_bound() -> None:
    # Seeded consumer stalls of 0-90 ms against a sender at the line rate; the 512-byte ring holds 44 ms of
    # it. A stall within that loses nothing, one past it is exactly one detected overrun, and the next frame
    # reads whole either way.
    uart = make_uart(baudrate=115200)
    fake(uart).rx_rate = 0.0  # the line rate
    buf = bytearray(53)
    seed = 12345
    start = Timer.clock_ms

    async def scenario() -> "tuple[int, int]":
        nonlocal seed
        within = beyond = 0
        async with uart:
            for i in range(200):
                seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF  # a file-local LCG, fixed seed
                stall_ms = seed % 91
                frames = stall_ms * 1152 // (53 * 100)  # whole frames whose wire time fits the stall
                for k in range(frames):
                    fake(uart).feed_rx(_frame(i * 16 + k))
                Timer.clock_ms += stall_ms
                before = uart.rx_overruns
                if frames * 53 <= 512:
                    for k in range(frames):
                        assert await uart.readinto_until_complete(buf, 53) == 53 and bytes(buf) == _frame(i * 16 + k), (i, k)
                    within += 1
                else:
                    assert await uart.readinto_until_complete(buf, 53, timeout_ms=_NO_DATA_TIMEOUT_MS) is None, i
                    assert uart.rx_overruns == before + 1, i
                    beyond += 1
                fake(uart).feed_rx(_frame(i))
                Timer.clock_ms += 5
                assert await uart.readinto_until_complete(buf, 53) == 53 and bytes(buf) == _frame(i), i
        return within, beyond

    try:
        within, beyond = run(scenario(), _HAMMER_BOUND_S)
    finally:
        Timer.clock_ms = start
    assert within > 0 and beyond > 0, (within, beyond)
    assert uart._rx_level() == 0


def test_a_uart_receive_error_fails_the_frame_and_the_next_reads_whole() -> None:
    payload = bytearray(b"\x01\x02\x03\x04")
    for bits in (_RSR_OE, _RSR_FE, _RSR_BE):
        for crc in (None, CRC16):
            sender = make_uart(crc=crc() if crc else None)
            assert run(locked_write(sender, bytearray(payload))) is True
            frame = written(sender)
            uart = make_uart(crc=crc() if crc else None)
            fake(uart).feed_rx(frame[:2])
            plant_rx_errors(uart, bits)
            fake(uart).feed_rx(frame[2:])
            buf = bytearray(16)
            assert run(locked_readinto_until_complete(uart, buf, 4, start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS)) is None, (bits, crc)
            assert uart.rx_overruns == 1, (bits, crc)
            assert uart._rx_level() == 0, (bits, crc)
            assert mem32[_UART0_RSR] & (_RSR_OE | _RSR_FE | _RSR_BE) == 0, (bits, crc)  # cleared through UARTECR
            fake(uart).feed_rx(frame)
            assert run(locked_readinto_until_complete(uart, buf, 4, start_timeout_ms=_DATA_TIMEOUT_MS, timeout_ms=_DATA_TIMEOUT_MS)) == 4, (bits, crc)
            assert bytes(buf[:4]) == bytes(payload), (bits, crc)


def test_a_parity_error_alone_is_outside_the_mask() -> None:
    uart = make_uart()  # no link configures parity, so PE carries nothing
    fake(uart).feed_rx(b"ab")
    plant_rx_errors(uart, _RSR_PE)
    fake(uart).feed_rx(b"cd")
    buf = bytearray(4)
    assert run(locked_readinto_until_complete(uart, buf, 4)) == 4
    assert bytes(buf) == b"abcd"
    assert uart.rx_overruns == 0


def test_an_error_flag_left_before_the_ring_existed_is_not_reported() -> None:
    DMA.reset_registry()
    uart = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=1, poll_idle_ms=1)
    uart.poller = _StepPoller([select.POLLOUT])  # type: ignore[assignment]
    unpaced(uart)
    plant_rx_errors(uart, _RSR_OE)  # the FIFO overflowed before the link existed
    assert uart.setup_rx_ring() is True
    assert mem32[_UART0_RSR] & _RSR_OE == 0
    fake(uart).feed_rx(b"abcd")
    buf = bytearray(4)
    assert run(locked_readinto_until_complete(uart, buf, 4)) == 4
    assert uart.rx_overruns == 0


def test_a_receive_overrun_fails_the_initiators_transaction_and_the_next_succeeds() -> None:
    # Through the protocol: the responder never ACKs a frame that crossed an overrun, so the initiator's
    # transaction fails as for a missing ACK, and after the resync the next one completes.
    for fault in ("oe", "fe", "be", "lap"):
        for crc in (None, CRC16):
            pair = Pair(get_callback=echo_get(b"v"), set_callback=accept_set(), crc_a=crc() if crc else None, crc_b=crc() if crc else None)
            assert run(pair.setup()) is True
            if fault == "lap":
                pair.fake_b.feed_rx(bytes(600))  # more than the responder's 512-byte ring holds
            else:
                bits = {"oe": _RSR_OE, "fe": _RSR_FE, "be": _RSR_BE}[fault]
                plant_rx_errors(pair.driver_b, bits)
            first = run(pair.with_listener(pair.initiator.uart_set(1, b"abc"), listener_may_stall=True))
            assert first is False, (fault, crc)
            second = run(pair.with_listener(pair.initiator.uart_set(1, b"abc")))
            assert second is True, (fault, crc)
            assert pair.driver_b.rx_overruns == 1, (fault, crc)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
