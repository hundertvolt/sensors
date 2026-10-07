"""Backend-agnostic semantic assertions for a byte-stream UART crossover link (Part J.7).
Each check takes a factory returning (uart_a, uart_b, link); tests/machine.py and digital_twin/machine.py supply their own, so the two models diverge in fidelity but never in semantics.
link.settle() is that one fidelity seam - a no-op on the mock, a wait for pending wire time on the twin."""

import select
from array import array

import machine
import rp2
import uctypes

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from typing import Any, Protocol

    LinkFactory = Callable[[], tuple[Any, Any, Any]]

    class _BoundedRecord(Protocol):
        # What both fakes' bounded logs offer a reader: a size, a drop count, entries oldest first.
        dropped: int

        def __getitem__(self, index: int) -> object: ...
        def __iter__(self) -> Iterator[object]: ...
        def __len__(self) -> int: ...

# The receive-ring wiring both fakes model (RP2040 datasheet 4.2.8 and 2.5; DREQ from pico-sdk dreq.h).
_UART_BASES = (0x40034000, 0x40038000)  # UARTDR sits at offset 0: the paced channel's read address
_UARTRSR = 0x004  # read: OE 0x08, BE 0x04, FE 0x01; a write (UARTECR) clears them
_UARTIMSC = 0x038  # RXIM 0x10, RTIM 0x40
_UARTDMACR = 0x048  # RXDMAE 0x01
_RX_DREQ = (21, 23)
_DMA_TRANS_COUNT_TRIG = 0x5000001C  # channel n's AL1_TRANS_COUNT_TRIG at + 0x40 * n
_RUN = 2**29  # the paced channel's transfer count, the driver's (a multiple of every legal ring size)


def check_byte_moves_one_way(make: "LinkFactory") -> None:
    a, b, link = make()
    a.write(b"Z")
    link.settle()
    assert b.read(1) == b"Z"
    assert a.read(1) is None  # never reads back what it just wrote


def check_both_directions_independent(make: "LinkFactory") -> None:
    a, b, link = make()
    a.write(b"ab")
    b.write(b"xyz")
    link.settle()
    assert a.read() == b"xyz"
    assert b.read() == b"ab"


def check_reads_split_at_arbitrary_offsets(make: "LinkFactory") -> None:
    # A write boundary is not a frame boundary - the reader splits wherever it asks.
    a, b, link = make()
    a.write(b"0123456789")
    link.settle()
    assert b.read(3) == b"012"
    assert b.read(1) == b"3"
    assert b.read() == b"456789"
    assert b.read() is None  # real rp2: None, not b"", on an empty FIFO


def check_write_boundaries_are_not_preserved(make: "LinkFactory") -> None:
    a, b, link = make()
    a.write(b"AB")
    a.write(b"CD")
    link.settle()
    assert b.read(4) == b"ABCD"


def check_pollin_follows_fifo_content(make: "LinkFactory") -> None:
    a, b, link = make()
    assert not (b.ioctl(3, select.POLLIN) & select.POLLIN)
    a.write(b"q")
    link.settle()
    assert b.ioctl(3, select.POLLIN) & select.POLLIN
    b.read()
    assert not (b.ioctl(3, select.POLLIN) & select.POLLIN)


def check_pollout_follows_writable_gate(make: "LinkFactory") -> None:
    a, _b, _link = make()
    assert a.ioctl(3, select.POLLOUT) & select.POLLOUT
    a.writable = False
    assert not (a.ioctl(3, select.POLLOUT) & select.POLLOUT)


def check_short_write_returns_real_count(make: "LinkFactory") -> None:
    a, b, link = make()
    a.write_limit = 2
    assert a.write(b"12345") == 2
    link.settle()
    assert b.read() == b"12"
    a.write_limit = 0
    assert a.write(b"12345") is None


def check_capacity_drops_newest(make: "LinkFactory") -> None:
    # Fixed capacity per direction, explicit drop-newest policy, counted.
    a, b, link = make()
    direction = link.direction_from(a)
    direction.capacity = 4
    assert a.write(b"123456") == 6  # the wire accepted them; the far buffer did not
    link.settle()
    assert b.read() == b"1234"
    assert direction.dropped_overrun == 2


def check_silence_drops_everything(make: "LinkFactory") -> None:
    a, b, link = make()
    link.direction_from(a).silent = True
    a.write(b"hello")
    link.settle()
    assert b.read() is None
    link.direction_from(a).silent = False
    a.write(b"hi")
    link.settle()
    assert b.read() == b"hi"


def check_drop_indices_remove_exactly_those_bytes(make: "LinkFactory") -> None:
    a, b, link = make()
    link.direction_from(a).drop_indices = {1, 3}
    a.write(b"ABCDE")
    link.settle()
    assert b.read() == b"ACE"


def check_corruption_preserves_length(make: "LinkFactory") -> None:
    # Corruption and truncation are separate knobs, so a failure is attributable.
    a, b, link = make()
    link.direction_from(a).corrupt_indices = {0: 0xFF}
    a.write(b"\x00\x01")
    link.settle()
    got = b.read()
    assert got is not None
    assert len(got) == 2
    assert got[0] == 0xFF
    assert got[1] == 0x01


def check_truncate_after_cuts_the_tail(make: "LinkFactory") -> None:
    a, b, link = make()
    link.direction_from(a).truncate_after = 3
    a.write(b"ABCDEFGH")
    link.settle()
    assert b.read() == b"ABC"
    a.write(b"IJK")
    link.settle()
    assert b.read() is None  # the cut is on the direction's whole stream, not per write


def check_noise_is_injected_before_the_next_delivery(make: "LinkFactory") -> None:
    a, b, link = make()
    link.direction_from(a).noise_before_next = bytearray(b"\xde\xad")
    a.write(b"OK")
    link.settle()
    assert b.read() == b"\xde\xadOK"
    a.write(b"OK")
    link.settle()
    assert b.read() == b"OK"  # injected once, not per write


def check_delayed_delivery_holds_until_released(make: "LinkFactory") -> None:
    a, b, link = make()
    link.direction_from(a).delay = True
    a.write(b"late")
    link.settle()
    assert b.read() is None
    assert link.release_delayed() == 4
    link.settle()
    assert b.read() == b"late"


def check_duplication_repeats_the_next_bytes(make: "LinkFactory") -> None:
    a, b, link = make()
    link.direction_from(a).duplicate_next = 2
    a.write(b"XY")
    link.settle()
    assert b.read() == b"XYXY"
    a.write(b"Z")
    link.settle()
    assert b.read() == b"Z"


def check_wire_log_records_what_was_delivered(make: "LinkFactory") -> None:
    # every knob's effect is verifiable against a recorded wire log, not inferred.
    a, b, link = make()
    link.direction_from(a).drop_indices = {0}
    a.write(b"AB")
    link.settle()
    b.read()
    assert bytes(link.direction_from(a).wire_log) == b"B"


def check_readinto_moves_the_same_bytes(make: "LinkFactory") -> None:
    a, b, link = make()
    a.write(b"12345")
    link.settle()
    buf = bytearray(3)
    assert b.readinto(buf) == 3
    assert bytes(buf) == b"123"
    assert b.readinto(bytearray(8), 2) == 2


def check_readinto_returns_none_when_empty(make: "LinkFactory") -> None:
    _a, b, _link = make()
    assert b.readinto(bytearray(4)) is None


def check_overask_is_counted_not_taken(make: "LinkFactory") -> None:
    # Both models serve what they hold and return; the real peripheral would instead wait out
    # timeout_char per missing byte without yielding (F.5.8). The count is the shared stand-in for
    # that stall, so a driver regression shows up as a number rather than as a slow test.
    a, b, link = make()
    type(b).would_have_blocked_bytes = 0
    a.write(b"xy")
    link.settle()
    assert b.read(5) == b"xy"
    assert type(b).would_have_blocked_bytes == 3
    assert b.read(4) is None
    assert type(b).would_have_blocked_bytes == 7
    type(b).would_have_blocked_bytes = 0


def check_readline_on_an_empty_line_is_counted_too(make: "LinkFactory") -> None:
    # readline() is clamped to any() like every counted read; with no size and no newline buffered the C
    # read still waits for one byte past the buffer, so a fake must count that byte too (the sweep that
    # found this is in SPECIFICATION.md Part E.8). One byte per empty call, none once a line is buffered.
    a, b, link = make()
    type(b).would_have_blocked_bytes = 0
    assert b.readline() is None
    assert type(b).would_have_blocked_bytes == 1
    a.write(b"hi\n")
    link.settle()
    assert b.readline() == b"hi\n"
    assert type(b).would_have_blocked_bytes == 1
    type(b).would_have_blocked_bytes = 0


def check_readline_with_a_size_is_clamped_and_counted(make: "LinkFactory") -> None:
    # readline(n) stops at n bytes or a newline; asking for more than is buffered and no newline
    # among them is the per-byte wait the real C read takes (F.5.8), counted like every overask.
    a, b, link = make()
    type(b).would_have_blocked_bytes = 0
    a.write(b"abc")
    link.settle()
    assert b.readline(5) == b"abc"
    assert type(b).would_have_blocked_bytes == 2
    a.write(b"de\nfg")
    link.settle()
    assert b.readline(4) == b"de\n"  # the newline ends it: no wait
    assert type(b).would_have_blocked_bytes == 2
    type(b).would_have_blocked_bytes = 0
    b.read()


def _wire_ms(uart: "machine.UART", nbytes: int) -> int:
    return nbytes * 10_000 // uart.baudrate + 2  # 8N1: ten bit times a byte, plus a margin


def _arm_ring(uart: "machine.UART", ring_size: int, first_count: int = _RUN) -> "tuple[memoryview, rp2.DMA, rp2.DMA]":
    # The driver's two-channel ring: a byte-wide paced channel writing a naturally aligned window that
    # wraps on its write address, and a reload channel it chains to, rewriting its count and re-triggering.
    raw = bytearray(2 * ring_size)
    start = (-uctypes.addressof(raw)) % ring_size
    ring = memoryview(raw)[start : start + ring_size]
    log2 = 0
    while (1 << log2) < ring_size:  # MicroPython's int has no bit_length()
        log2 += 1
    data, reload = rp2.DMA(), rp2.DMA()
    reload.config(read=array("I", [_RUN]), write=_DMA_TRANS_COUNT_TRIG + 0x40 * data.channel, count=1, ctrl=reload.pack_ctrl(inc_read=False, inc_write=False))
    ctrl = data.pack_ctrl(size=0, inc_read=False, inc_write=True, ring_sel=True, ring_size=log2, treq_sel=_RX_DREQ[uart.id], chain_to=reload.channel)
    data.config(read=_UART_BASES[uart.id], write=ring, count=first_count, ctrl=ctrl, trigger=True)
    return ring, data, reload


def _mask_off(uart: "machine.UART") -> None:
    address = _UART_BASES[uart.id] + _UARTIMSC
    machine.mem32[address] &= ~0x50


def _received(data: "rp2.DMA") -> int:
    return _RUN - data.count


def _close(*channels: "rp2.DMA") -> None:
    for channel in channels:
        channel.close()


def check_init_sets_the_rx_interrupt_mask(make: "LinkFactory") -> None:
    # Every construction and init() enables RX and RX-timeout interrupts (machine_uart.c:455), so a
    # driver taking the receive path for DMA has to clear them again after each.
    _a, b, _link = make()
    imsc = _UART_BASES[b.id] + _UARTIMSC
    assert machine.mem32[imsc] & 0x50 == 0x50
    _mask_off(b)
    assert machine.mem32[imsc] & 0x50 == 0
    b.init(baudrate=b.baudrate)
    assert machine.mem32[imsc] & 0x50 == 0x50
    assert machine.mem32[_UART_BASES[b.id] + _UARTDMACR] & 0x01  # uart_init() always enables the DREQs


def check_dma_fills_the_ring_without_a_loop_turn(make: "LinkFactory") -> None:
    a, b, link = make()
    ring, data, reload = _arm_ring(b, 64)
    try:
        _mask_off(b)
        b.rx_api_calls = 0
        a.write(b"hello")
        link.settle()
        link.elapse(_wire_ms(b, 5))  # time passes, nothing awaits: the channel still moves the bytes
        assert _received(data) == 5
        assert bytes(ring[:5]) == b"hello"
        assert b.rx_api_calls == 0  # reading the count is not a receive call on machine.UART
    finally:
        _close(data, reload)


def check_the_ring_wraps_on_its_write_address(make: "LinkFactory") -> None:
    a, b, link = make()
    ring, data, reload = _arm_ring(b, 16)
    try:
        _mask_off(b)
        a.write(b"0123456789ABCDEFGHIJ")
        link.settle()
        link.elapse(_wire_ms(b, 20))
        assert _received(data) == 20
        assert bytes(ring) == b"GHIJ456789ABCDEF"
    finally:
        _close(data, reload)


def check_the_chained_channel_reloads_the_count(make: "LinkFactory") -> None:
    a, b, link = make()
    ring, data, reload = _arm_ring(b, 16, first_count=4)
    try:
        _mask_off(b)
        a.write(b"abcdef")
        link.settle()
        link.elapse(_wire_ms(b, 6))
        assert data.count == _RUN - 2  # four moved, the reload re-triggered it, two more moved
        assert data.active()
        assert not reload.active()  # its one transfer is done
        assert bytes(ring[:6]) == b"abcdef"
    finally:
        _close(data, reload)


def check_a_lap_is_visible_in_the_totals(make: "LinkFactory") -> None:
    # More bytes than the ring holds: the ring keeps only the newest, the modular total says so.
    a, b, link = make()
    _ring, data, reload = _arm_ring(b, 16)
    try:
        _mask_off(b)
        a.write(bytes(range(40)))
        link.settle()
        link.elapse(_wire_ms(b, 40))
        assert _received(data) == 40  # a lap: more than the 16 the ring holds
    finally:
        _close(data, reload)


def check_a_set_mask_steals_bytes(make: "LinkFactory") -> None:
    # RXIM/RTIM left set: the RX interrupt drains the FIFO into machine.UART's own buffer first.
    a, b, link = make()
    _ring, data, reload = _arm_ring(b, 64)
    try:
        a.write(b"stolen")
        link.settle()
        link.elapse(_wire_ms(b, 6))
        assert _received(data) == 0
        assert b.read() == b"stolen"
    finally:
        _close(data, reload)


def check_an_undrained_fifo_overruns_into_oe(make: "LinkFactory") -> None:
    # No interrupt and no DMA draining it: the 32-byte RX FIFO keeps the first 32 and sets OE.
    a, b, link = make()
    rsr = _UART_BASES[b.id] + _UARTRSR
    machine.mem32[_UART_BASES[b.id] + _UARTDMACR] &= ~0x01
    _mask_off(b)
    a.write(bytes(40))
    link.settle()
    link.elapse(_wire_ms(b, 40))
    assert machine.mem32[rsr] & 0x08
    machine.mem32[rsr] = 0  # UARTECR: any write clears the error bits
    assert machine.mem32[rsr] & 0x0F == 0


def check_planted_framing_and_break_errors_read_in_rsr(make: "LinkFactory") -> None:
    # FE and BE are plantable beside OE; a break also loads one 0x00 character (datasheet Table 426).
    _a, b, _link = make()
    ring, data, reload = _arm_ring(b, 16)
    rsr = _UART_BASES[b.id] + _UARTRSR
    try:
        _mask_off(b)
        b.plant_rx_error(0x01)
        assert machine.mem32[rsr] & 0x0F == 0x01
        machine.mem32[rsr] = 0
        ring[0] = 0xAA
        b.plant_rx_error(0x04)
        assert machine.mem32[rsr] & 0x0F == 0x04
        assert _received(data) == 1
        assert ring[0] == 0x00
        machine.mem32[rsr] = 0
        assert machine.mem32[rsr] & 0x0F == 0
    finally:
        _close(data, reload)


def check_dma_channels_are_twelve_then_ebusy(make: "LinkFactory") -> None:
    # DMA() claims the lowest free channel and raises OSError(EBUSY) once all twelve are taken
    # (rp2_dma.c:357-366); close() frees one and a closed object refuses further use.
    make()
    claimed: list[rp2.DMA] = []
    try:
        while len(claimed) < 13:
            claimed.append(rp2.DMA())
        raise AssertionError("a thirteenth channel was claimed")
    except OSError as exc:
        assert exc.args[0] == 16  # EBUSY
    freed = claimed.pop()
    number = freed.channel
    freed.close()
    try:
        freed.active()
        raise AssertionError("a closed channel was usable")
    except ValueError:
        pass
    again = rp2.DMA()
    assert again.channel == number
    _close(again, *claimed)


def check_pack_ctrl_follows_rp2(make: "LinkFactory") -> None:
    make()
    channel = rp2.DMA()
    try:
        default = channel.pack_ctrl()
        assert default == (1 << 21) | (0x3F << 15) | (channel.channel << 11) | (1 << 5) | (1 << 4) | (2 << 2) | 1
        fields = rp2.DMA.unpack_ctrl(channel.pack_ctrl(size=0, ring_sel=True, ring_size=6, treq_sel=21))
        assert (fields["size"], fields["ring_sel"], fields["ring_size"], fields["treq_sel"], fields["enable"]) == (0, 1, 6, 21, 1)
        try:
            channel.pack_ctrl(ring_size=16)
            raise AssertionError("a 5-bit value in a 4-bit field was packed")
        except ValueError:
            pass
    finally:
        _close(channel)


def check_a_misaligned_ring_is_refused(make: "LinkFactory") -> None:
    # Silicon would wrap the address bits and write outside the window; the fakes refuse it.
    _a, b, _link = make()
    raw = bytearray(64)
    start = (-uctypes.addressof(raw)) % 32 + 1
    channel = rp2.DMA()
    try:
        channel.config(read=_UART_BASES[b.id], write=memoryview(raw)[start : start + 16], count=_RUN, ctrl=channel.pack_ctrl(size=0, inc_read=False, ring_sel=True, ring_size=4, treq_sel=_RX_DREQ[b.id]))
        raise AssertionError("a misaligned ring was accepted")
    except ValueError:
        pass
    finally:
        _close(channel)


def check_the_write_address_reads_stale(make: "LinkFactory") -> None:
    # RP2040-E12: WRITE_ADDR is wrong during ring transfers, so progress comes from the count alone.
    a, b, link = make()
    ring, data, reload = _arm_ring(b, 16)
    try:
        _mask_off(b)
        start = data.write
        a.write(b"xyz")
        link.settle()
        link.elapse(_wire_ms(b, 3))
        assert _received(data) == 3
        assert data.write == start == uctypes.addressof(ring)
    finally:
        _close(data, reload)


def check_the_mem32_log_stays_bounded(make: "LinkFactory") -> None:
    # A DMA reader reads UARTRSR at every fill-level read, so over a long run the record of register
    # accesses must keep only its newest entries and say how many it dropped.
    _a, b, _link = make()
    rsr = _UART_BASES[b.id] + _UARTRSR
    dropped = machine.mem32.log.dropped
    for _ in range(1000):
        machine.mem32[rsr]
    assert len(machine.mem32.log) <= 64
    assert machine.mem32.log.dropped >= dropped + 1000 - 64
    assert machine.mem32.log[-1] == ("read", rsr, 0)


def check_the_wire_log_stays_bounded(make: "LinkFactory") -> None:
    # Every delivered byte is recorded; a long run keeps the newest 4096 and counts the rest.
    a, b, link = make()
    direction = link.direction_from(a)
    direction.capacity = 1 << 20
    for _ in range(3):
        a.write(bytes(range(256)) * 8)  # 2048 bytes a time, read out so the far buffer stays small
        link.settle()
        b.read()
    assert len(direction.wire_log) <= 4096
    assert direction.wire_log.dropped + len(direction.wire_log) == direction.delivered == 6144
    assert direction.wire_log[-1] == 255


def check_the_wire_holds_at_most_4096_bytes_in_flight(make: "LinkFactory") -> None:
    # Bytes written faster than the receiver takes them wait on the wire; past 4096 the rest are an
    # overrun by another name, counted and dropped, never a growing buffer.
    a, b, link = make()
    _mask_off(b)
    machine.mem32[_UART_BASES[b.id] + _UARTDMACR] &= ~0x01
    a.write(bytes(5000))
    assert link.direction_from(a).dropped_overrun == 5000 - 4096


def check_a_full_uart_buffer_leaves_bytes_to_the_fifo(make: "LinkFactory") -> None:
    # The RX interrupt drains the FIFO only while machine.UART's own buffer has room (machine_uart.c:163),
    # and never stores a break's 0x00 (:172-176); bytes it cannot take stay in the FIFO.
    a, b, link = make()
    imsc, dmacr = _UART_BASES[b.id] + _UARTIMSC, _UART_BASES[b.id] + _UARTDMACR
    b.plant_rx_error(0x04)
    assert b.any() == 0
    a.write(bytes(b.rxbuf))
    link.settle()
    assert b.any() == b.rxbuf  # the buffer is full
    _mask_off(b)
    machine.mem32[dmacr] &= ~0x01
    a.write(b"x" * 40)
    link.settle()
    link.elapse(_wire_ms(b, 40))
    machine.mem32[imsc] = 0x50  # the interrupt back on: no room, so the FIFO's 32 stay where they are
    assert b.any() == b.rxbuf
    b.read(32)
    assert b.any() == b.rxbuf  # room again: the FIFO drained into it
    assert b.read()[-32:] == b"x" * 32


def _assert_fixed_occupancy(name: str, log: "_BoundedRecord", append: "Callable[[int], object]", cap: int) -> None:
    # Once full, a bounded log overwrites its oldest entry in place: its live size never swings (a
    # swing reads as retention in the heap tests), and it still reads oldest first.
    while len(log) < cap:
        append(0)
    dropped = log.dropped
    for k in range(1, 2 * cap + 3):
        append(k)
        assert len(log) == cap, f"{name}: {len(log)} entries after an append past the cap of {cap}"
    assert log.dropped == dropped + 2 * cap + 2, f"{name}: the overwritten entries were not counted"
    entries = list(log)
    assert entries[-1] == log[-1] and entries[0] == log[0] == log[-cap], f"{name}: not read oldest first"


def check_the_bounded_logs_keep_a_fixed_occupancy(make: "LinkFactory") -> None:
    a, b, link = make()
    rsr = _UART_BASES[b.id] + _UARTRSR
    _assert_fixed_occupancy("mem32.log", machine.mem32.log, lambda _k: machine.mem32[rsr], 64)
    direction = link.direction_from(a)
    direction.capacity = 1 << 20

    def deliver(k: int) -> None:
        a.write(bytes([k & 0xFF]))
        link.settle()
        b.read()

    _assert_fixed_occupancy("wire_log", direction.wire_log, deliver, 4096)
    machine.Pin.reset_registry()
    pin = machine.Pin(20, machine.Pin.OUT)
    _assert_fixed_occupancy("Pin.value_log", machine.Pin.value_log(20), lambda k: pin.value(k & 1), 64)
    machine.Pin.reset_registry()
    if hasattr(a, "log"):  # the unit tier's own call log
        _assert_fixed_occupancy("UART.log", a.log, lambda k: a.log.append(("synthetic", k)), 4096)


ALL_CHECKS = (
    check_byte_moves_one_way,
    check_both_directions_independent,
    check_reads_split_at_arbitrary_offsets,
    check_write_boundaries_are_not_preserved,
    check_pollin_follows_fifo_content,
    check_pollout_follows_writable_gate,
    check_short_write_returns_real_count,
    check_capacity_drops_newest,
    check_silence_drops_everything,
    check_drop_indices_remove_exactly_those_bytes,
    check_corruption_preserves_length,
    check_truncate_after_cuts_the_tail,
    check_noise_is_injected_before_the_next_delivery,
    check_delayed_delivery_holds_until_released,
    check_duplication_repeats_the_next_bytes,
    check_wire_log_records_what_was_delivered,
    check_readinto_moves_the_same_bytes,
    check_readinto_returns_none_when_empty,
    check_overask_is_counted_not_taken,
    check_readline_on_an_empty_line_is_counted_too,
    check_readline_with_a_size_is_clamped_and_counted,
    check_init_sets_the_rx_interrupt_mask,
    check_dma_fills_the_ring_without_a_loop_turn,
    check_the_ring_wraps_on_its_write_address,
    check_the_chained_channel_reloads_the_count,
    check_a_lap_is_visible_in_the_totals,
    check_a_set_mask_steals_bytes,
    check_an_undrained_fifo_overruns_into_oe,
    check_planted_framing_and_break_errors_read_in_rsr,
    check_dma_channels_are_twelve_then_ebusy,
    check_pack_ctrl_follows_rp2,
    check_a_misaligned_ring_is_refused,
    check_the_write_address_reads_stale,
    check_the_mem32_log_stays_bounded,
    check_the_wire_log_stays_bounded,
    check_the_wire_holds_at_most_4096_bytes_in_flight,
    check_a_full_uart_buffer_leaves_bytes_to_the_fifo,
    check_the_bounded_logs_keep_a_fixed_occupancy,
)
