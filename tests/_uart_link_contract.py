"""Backend-agnostic semantic assertions for a byte-stream UART crossover link (A1/A3/A4.1).
Each check takes a factory returning (uart_a, uart_b, link); tests/machine.py and digital_twin/machine.py supply their own, so the two models diverge in fidelity but never in semantics.
link.settle() is that one fidelity seam - a no-op on the mock, a wait for pending wire time on the twin."""

import select

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    LinkFactory = Callable[[], tuple[Any, Any, Any]]


def check_byte_moves_one_way(make: "LinkFactory") -> None:
    a, b, link = make()
    a.write(b"Z")
    link.settle()
    assert b.read(1) == b"Z"
    assert a.read(1) is None  # A1.4: never reads back what it just wrote


def check_both_directions_independent(make: "LinkFactory") -> None:
    a, b, link = make()
    a.write(b"ab")
    b.write(b"xyz")
    link.settle()
    assert a.read() == b"xyz"
    assert b.read() == b"ab"


def check_reads_split_at_arbitrary_offsets(make: "LinkFactory") -> None:
    # A1.5: a write boundary is not a frame boundary - the reader splits wherever it asks.
    a, b, link = make()
    a.write(b"0123456789")
    link.settle()
    assert b.read(3) == b"012"
    assert b.read(1) == b"3"
    assert b.read() == b"456789"
    assert b.read() is None  # A1.1/real rp2: None, not b"", on an empty FIFO


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
    # A1.3: fixed capacity per direction, explicit drop-newest policy, counted.
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
    # A3.4: corruption and truncation are separate knobs, so a failure is attributable.
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
    # A3.1: every knob's effect is verifiable against a recorded wire log, not inferred.
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
)
