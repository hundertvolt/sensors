"""Unit tests for digital_twin/machine.py's UART fake and its wire-timed crossover link.
Re-runs tests/_uart_link_contract.py's shared bodies against the twin backend, so the twin and
mock link models can differ in fidelity but never in semantics."""

import errno
import select
import sys
import time

# digital_twin/ must precede tests/ so `machine` resolves to the twin's own fake, not
# tests/machine.py's - see test_digital_twin_machine.py's own comment for the full reasoning.
sys.path.insert(0, "digital_twin")

import _flash_stall
import _uart_link_contract
import machine
import microtest
import rp2
from _async_harness import run
from _src_const import src_int
from _tmp_scratch import TmpScratch
from _twin_common import COUNTER_CAP
from machine import UART, LinkPoller, Pin, UARTLink

import asy_uart_driver

# @tunable l2.machine_uart_wire_time_floor_ms = 100
_WIRE_TIME_FLOOR_MS = 100
# @tunable l2.machine_uart_pump_deadline_ms = 500
_PUMP_DEADLINE_MS = 500
# @tunable l2.machine_uart_frame_wire_ms = 5
_FRAME_WIRE_MS = 5
# @tunable l2.machine_uart_frame_timeout_ms = 50
_FRAME_TIMEOUT_MS = 50
# The flash-stall cases' slow wire, 260 us a byte: a 32-page stall (12.8 ms) still spans more than the FIFO's 32 bytes
# when the code run before it starts takes up to 8 ms of the 64-byte burst's 16.7 ms.
# @tunable l2.machine_uart_stall_baud = 38400
_STALL_BAUD = 38400
# @tunable l2.machine_uart_stall_pages = 32
_STALL_PAGES = 32
_STALL_BURST = bytes(range(64))  # twice the 32-byte RX FIFO

microtest.after_each(machine.reset_test_state)
_scratch = TmpScratch("dtuart")
_RSR = (0x40034004, 0x40038004)  # UART0/UART1 UARTRSR (RP2040 datasheet 4.2.8)
_RSR_OE = 0x08


def _driver_pair(baudrate: int = 115200) -> "tuple[asy_uart_driver.UART, asy_uart_driver.UART, UARTLink]":
    # The product driver on both twin UARTs, joined by the bench jumper and polled by bounded pollers.
    machine.reset_peripherals()
    sender = asy_uart_driver.UART(0, tx_pin=0, rx_pin=1, baudrate=baudrate, poll_wait_ms=1, poll_idle_ms=1)
    receiver = asy_uart_driver.UART(1, tx_pin=8, rx_pin=9, baudrate=baudrate, poll_wait_ms=1, poll_idle_ms=1)
    link, sender_poll, receiver_poll = machine.attach_crossover_jumper(sender._uart, receiver._uart)  # type: ignore[arg-type]
    sender.poller = sender_poll  # type: ignore[assignment]
    receiver.poller = receiver_poll  # type: ignore[assignment]
    assert receiver.setup_rx_ring() is True
    return sender, receiver, link


def test_twin_link_satisfies_the_shared_contract() -> None:
    for check in _uart_link_contract.ALL_CHECKS:
        check(_make_link)


def test_ioctl_answers_einval_to_get_fileno() -> None:
    # ports/rp2/machine_uart.c:694-697: every request but POLL is EINVAL, so a real poll never takes the fd path.
    _a, b, _link = _make_link()
    assert b.ioctl(10, 0) == -errno.EINVAL  # MP_STREAM_GET_FILENO


def test_poll_mask_reports_what_the_link_delivered() -> None:
    a, b, link = _make_link()
    assert b.poll_mask(select.POLLIN | select.POLLOUT) == select.POLLOUT
    a.write(b"x")
    link.settle()
    assert b.poll_mask(select.POLLIN) == select.POLLIN


def test_a_second_construction_on_one_bus_id_returns_the_same_live_object() -> None:
    # machine_uart.c:461-475: the static object is re-initialised - its settings replaced, its ring re-allocated
    # empty - and the jumper is wiring, so the link keeps delivering.
    a, b, link = _make_link()
    b.write(b"old")
    link.settle()
    again = UART(a.id, tx=Pin(0), rx=Pin(1), baudrate=9600)
    assert again is a and (a.baudrate, a.rxbuf) == (9600, 256)
    assert a.read() is None
    b.write(b"new")
    link.settle()
    assert a.read() == b"new"


def test_init_refuses_a_keyword_rp2_does_not_take() -> None:
    uart = UART(0, tx=Pin(0), rx=Pin(1))
    try:
        uart.init(flow=1)
        raise AssertionError("an unknown keyword was taken")
    except TypeError as e:
        assert str(e) == "extra keyword arguments given", str(e)  # mp_arg_parse_all(), py/argcheck.c:129


def test_uart_takes_rp2s_ids_pins_buffers_and_defaults() -> None:
    # machine_uart.c:73-78, 355-475: TX on pins 0/4 of eight, RX one above; buffers clamped to 32-32766;
    # an unconfigured baudrate starts at 115200 with timeout_char at least one 13-bit character.
    machine.reset_peripherals()
    assert _value_error(lambda: UART(2, tx=Pin(0), rx=Pin(1))) == "UART(2) doesn't exist"
    assert _value_error(lambda: UART(0, tx=Pin(1), rx=Pin(1))) == "bad TX pin"
    assert _value_error(lambda: UART(1, tx=Pin(8), rx=Pin(1))) == "bad RX pin"
    assert _value_error(lambda: UART(0, tx=Pin(0), rx=Pin(1), rxbuf=40000)) == "rxbuf too large"
    uart = UART(0, tx=Pin(0), rx=Pin(1), rxbuf=10)
    assert (uart.rxbuf, uart.baudrate, uart.timeout_char) == (32, 115200, 1)
    UART(0, tx=Pin(0), rx=Pin(1), baudrate=1200)
    assert (uart.rxbuf, uart.timeout_char) == (256, 13000 // 1200 + 1)


def _dues_inside_the_stall(link: "UARTLink", dues: "list[int]") -> int:
    # Measured, never assumed: how many of the bytes due at `dues` (link wire time) arrived with interrupts off.
    return sum(1 for due in dues if _flash_stall.irqs_were_off(link._stall_offset_us + due))


def test_a_full_in_flight_queue_counts_the_byte_it_could_not_take() -> None:
    a, _b, link = _make_link()
    direction = link.direction_from(a)
    a.baudrate = 1200  # slow enough that every byte is still in flight
    link.a_to_b.baudrate = 1200
    a.write(bytes(4097))
    assert (len(direction.in_flight), direction.dropped_overrun) == (4096, 1)


def test_the_delay_buffer_holds_at_most_the_receivers_capacity() -> None:
    a, _b, link = _make_link(capacity_a_to_b=4)
    direction = link.direction_from(a)
    direction.delay = True
    a.write(bytes(10))
    assert (len(direction.pending), direction.dropped_delayed) == (4, 6)


def test_the_link_and_uart_counters_saturate_at_the_counter_cap() -> None:
    a, b, link = _make_link()
    direction = link.direction_from(a)
    direction.offered = direction.delivered = COUNTER_CAP
    UART.would_have_blocked_bytes = COUNTER_CAP
    a.write(b"x")
    link.settle()
    b.read(5)
    assert (direction.offered, direction.delivered, UART.would_have_blocked_bytes) == (COUNTER_CAP,) * 3


def test_settle_refuses_to_block_a_running_loop() -> None:
    a, _b, link = _make_link()
    a.write(b"x")

    async def inside() -> str:
        try:
            link.settle()
        except RuntimeError as e:
            return str(e)
        return "settled"

    assert run(inside()).startswith("settle() blocks the interpreter")


def test_settle_waits_out_the_wire_time_in_a_bounded_number_of_steps() -> None:
    machine.reset_peripherals()
    a = UART(0, tx=Pin(0), rx=Pin(1), baudrate=9600)
    b = UART(1, tx=Pin(8), rx=Pin(9), baudrate=9600)
    link = UARTLink(a, b)
    steps = [0]
    advance = link._advance

    def counted() -> None:
        steps[0] += 1
        advance()

    link._advance = counted  # type: ignore[method-assign]
    a.write(bytes(8))
    start = time.ticks_ms()
    link.settle()
    assert time.ticks_diff(time.ticks_ms(), start) >= 8 * 10 * 1000 // 9600 - 1
    assert steps[0] <= 3, steps


def test_a_real_poll_over_a_uart_is_counted_and_fails_the_test() -> None:
    # A real select.poll() over a fake is CLAUDE.md's CI hang: the after-each check fails the test that made one.
    _a, b, _link = _make_link()
    poller = select.poll()
    poller.register(b, select.POLLIN)
    poller.poll(0)
    assert UART.real_poll_queries >= 1
    try:
        machine.reset_test_state()
        raise AssertionError("the state reset passed a real poll")
    except AssertionError as e:
        assert "a real select.poll() queried a UART fake" in str(e), str(e)
    assert UART.real_poll_queries == 0


async def _frame_through(sender: "asy_uart_driver.UART", receiver: "asy_uart_driver.UART", link: UARTLink, payload: bytes, rsr_bits: int) -> "int | None":
    async with sender:
        assert await sender.write(bytearray(payload)) is True
    link.elapse(_FRAME_WIRE_MS)
    if rsr_bits:
        receiver._uart.plant_rx_error(rsr_bits)  # type: ignore[union-attr]
    buf = bytearray(16)
    async with receiver:
        return await receiver.readinto_until_complete(buf, len(payload), start_timeout_ms=_FRAME_TIMEOUT_MS, timeout_ms=_FRAME_TIMEOUT_MS)


def _make_link(baudrate: int = 115200, **kwargs: "int | None") -> "tuple[UART, UART, UARTLink]":
    machine.reset_peripherals()  # each test constructs its own pair, never a shared module-level one
    a = UART(0, tx=Pin(0), rx=Pin(1), baudrate=baudrate)
    b = UART(1, tx=Pin(8), rx=Pin(9), baudrate=baudrate)
    return a, b, UARTLink(a, b, **kwargs)


def _short_stall(pages: int) -> None:
    # A flush of `pages` page programs and no erase: long enough to cover the bytes in flight, short for the suite.
    erases, extra = _flash_stall.FLUSH_ERASES, _flash_stall.FLUSH_EXTRA_PAGES
    _flash_stall.FLUSH_ERASES, _flash_stall.FLUSH_EXTRA_PAGES = 0, pages
    try:
        _flash_stall.stall(0)
    finally:
        _flash_stall.FLUSH_ERASES, _flash_stall.FLUSH_EXTRA_PAGES = erases, extra


def test_a_planted_framing_or_break_error_fails_the_frame_and_the_next_reads_whole() -> None:
    # The twin wire's FE and BE reach the product driver as the L1 fake's do: that frame fails as an overrun.
    for bits in (0x01, 0x04):  # UARTRSR FE, BE (RP2040 datasheet Table 427)
        sender, receiver, link = _driver_pair()
        try:
            assert run(_frame_through(sender, receiver, link, b"\x01\x02\x03\x04", bits)) is None, bits
            assert receiver.rx_overruns == 1, bits
            assert run(_frame_through(sender, receiver, link, b"\x01\x02\x03\x04", 0)) == 4, bits
        finally:
            sender.deinit()
            receiver.deinit()


def test_delivery_takes_real_wire_time() -> None:
    # A twin link that ran faster than real time would make every drain/cooldown test pass
    # for the wrong reason. 64 bytes at 1200 baud is ~533ms of wire time; assert a floor well
    # under that but far above zero, so the test is about the mechanism, not the exact clock.
    machine.reset_peripherals()
    a = UART(0, tx=Pin(0), rx=Pin(1), baudrate=1200)
    b = UART(1, tx=Pin(8), rx=Pin(9), baudrate=1200)
    link = UARTLink(a, b)
    a.write(bytes(64))
    assert b.read() is None  # nothing has arrived yet - the wire is still busy
    start = time.ticks_ms()
    link.settle()
    elapsed = time.ticks_diff(time.ticks_ms(), start)
    assert elapsed > _WIRE_TIME_FLOOR_MS, f"delivery took {elapsed}ms, expected real wire time"
    got = b.read()
    assert got is not None
    assert len(got) == 64


def test_faster_baud_delivers_faster() -> None:
    # The wire time derives from the configured baud rate, not a constant.
    def elapsed_for(baudrate: int) -> int:
        machine.reset_peripherals()
        a = UART(0, tx=Pin(0), rx=Pin(1), baudrate=baudrate)
        b = UART(1, tx=Pin(8), rx=Pin(9), baudrate=baudrate)
        link = UARTLink(a, b)
        a.write(bytes(32))
        start = time.ticks_us()
        link.settle()
        return time.ticks_diff(time.ticks_us(), start)

    assert elapsed_for(115200) < elapsed_for(2400)


def test_reads_pump_the_wire_without_settle() -> None:
    # ioctl()/read() advance the link themselves, so a real asyncio consumer polling in a loop
    # never needs settle() - that helper exists only for synchronous assertions.
    a, b, _link = _make_link()
    a.write(b"pump")
    deadline = time.ticks_add(time.ticks_ms(), _PUMP_DEADLINE_MS)
    got = bytearray()
    while len(got) < 4 and time.ticks_diff(deadline, time.ticks_ms()) > 0:
        part = b.read()  # arrives byte by byte as its wire time elapses, like a real stream
        if part is not None:
            got += part
    assert bytes(got) == b"pump"


def test_twin_poller_requeries_ioctl() -> None:
    a, b, link = _make_link()
    poller = LinkPoller(b)
    assert poller.ipoll(0) == [(None, select.POLLOUT)]
    a.write(b"x")
    link.settle()
    assert poller.ipoll(0) == [(None, select.POLLIN | select.POLLOUT)]


def test_twin_poller_is_not_a_real_select_poll() -> None:
    _a, b, _link = _make_link()
    assert type(LinkPoller(b)).__name__ != type(select.poll()).__name__


def test_the_finaliser_aborts_the_channel() -> None:
    # rp2.DMA's __del__ is close() (rp2_dma.c:673): a soft reset stops a running ring and frees it.
    channel = rp2.DMA()
    number = channel.channel
    channel.config(read=bytearray(4), write=bytearray(4), count=4, ctrl=channel.pack_ctrl(treq_sel=21))
    channel.active(True)
    assert channel.active()
    channel.__del__()
    assert number not in machine._DMA_CHANNELS
    try:
        channel.active()
        raise AssertionError("a finalised channel was usable")
    except ValueError:
        pass


def test_reset_peripherals_frees_every_dma_channel() -> None:
    # A new board: channels a previous build claimed are released, as a soft reset's finalisers do.
    claimed = [rp2.DMA() for _ in range(3)]
    machine.reset_peripherals()
    assert machine._DMA_CHANNELS == {}
    assert all(channel.channel == 0xFF for channel in claimed)


def test_a_poller_asks_only_for_its_mask() -> None:
    # The driver registers POLLOUT alone; a bounded poller asking for POLLIN too would count as a receive poll.
    _a, b, _link = _make_link()
    b.rx_api_calls = 0
    assert LinkPoller(b, mask=select.POLLOUT).ipoll(0) == [(None, select.POLLOUT)]
    assert b.rx_api_calls == 0
    LinkPoller(b).ipoll(0)
    assert b.rx_api_calls == 1


def _value_error(call: "object") -> str:
    try:
        call()  # type: ignore[operator]
    except ValueError as e:
        return str(e)
    raise AssertionError("expected ValueError")


def test_the_largest_config_flush_at_the_maxima_is_the_hold_the_ring_floor_assumes() -> None:
    # 5 erases and 7 + 36 page programs at tSE 400 ms, tPP 3 ms: asy_uart_comm's _FLASH_HOLD_MAX_MS exactly.
    _flash_stall.use_max = True
    assert _flash_stall.flush_us(1700) == src_int("src/asy_uart_comm.py", "_FLASH_HOLD_MAX_MS") * 1000


def test_a_config_flush_through_the_installed_open_stalls_once_for_its_pages() -> None:
    class _Module:
        pass

    module = _Module()
    _flash_stall.install(module)
    erases, extra = _flash_stall.FLUSH_ERASES, _flash_stall.FLUSH_EXTRA_PAGES
    _flash_stall.FLUSH_ERASES, _flash_stall.FLUSH_EXTRA_PAGES = 0, 0
    try:
        path = _scratch.path("flush.cfg")
        start = time.ticks_us()
        with module.open(path, "w") as f:  # type: ignore[attr-defined]
            f.write("x" * 600)  # 3 pages at tPP 0.4 ms
        assert time.ticks_diff(time.ticks_us(), start) >= 1200
        with module.open(path) as f:  # type: ignore[attr-defined]
            assert f.read() == "x" * 600  # a read never stalls
    finally:
        _flash_stall.FLUSH_ERASES, _flash_stall.FLUSH_EXTRA_PAGES = erases, extra
    assert (_flash_stall.stalls, _flash_stall.longest_ms) == (1, 1)


def test_the_dma_keeps_filling_the_ring_through_a_flash_stall() -> None:
    # The driver's ring masks the RX interrupt: the DMA, which interrupts-off never stops, takes every byte.
    sender, receiver, link = _driver_pair(_STALL_BAUD)
    try:

        async def scenario() -> "tuple[int | None, int]":
            async with sender:
                assert await sender.write(bytearray(_STALL_BURST)) is True
            dues = [due for due, _byte in link.a_to_b.in_flight]
            _short_stall(_STALL_PAGES)
            buf = bytearray(len(_STALL_BURST))
            async with receiver:
                got = await receiver.readinto_until_complete(buf, len(buf), start_timeout_ms=_FRAME_TIMEOUT_MS, timeout_ms=_FRAME_TIMEOUT_MS)
            assert bytes(buf) == _STALL_BURST
            return got, _dues_inside_the_stall(link, dues)

        got, inside = run(scenario())
        assert got == len(_STALL_BURST)
        assert inside > 32, inside  # past the FIFO's depth: only the DMA can have taken them
        assert machine.mem32[_RSR[1]] & _RSR_OE == 0
    finally:
        sender.deinit()
        receiver.deinit()


def test_a_set_mask_overflows_the_fifo_inside_a_flash_stall() -> None:
    # RXIM left set: with interrupts off nothing drains the 32-byte FIFO, so OE sets and every later byte is lost.
    a, b, link = _make_link(_STALL_BAUD)
    a.write(_STALL_BURST)
    dues = [due for due, _byte in link.a_to_b.in_flight]
    _short_stall(_STALL_PAGES)
    link.settle()
    inside = _dues_inside_the_stall(link, dues)
    assert inside > 32, inside  # the FIFO's depth: the run-up to the stall left too few bytes inside it
    # A byte outside the window reaches the buffer through the interrupt; inside it, the FIFO keeps 32 and drops the rest.
    assert (len(b.read() or b""), b.rx_fifo_dropped, b.rsr & _RSR_OE) == (len(_STALL_BURST) - inside + 32, inside - 32, _RSR_OE)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
