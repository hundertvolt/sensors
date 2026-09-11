"""Unit tests for digital_twin/machine.py's UART fake and its wire-timed crossover link (A4).
Re-runs tests/_uart_link_contract.py's shared bodies against the twin backend, so the twin and mock link models can differ in fidelity but never in semantics (A4.1)."""

import sys
import time

# digital_twin/ must precede tests/ so `machine` resolves to the twin's own fake, not
# tests/machine.py's - see test_digital_twin_machine.py's own comment for the full reasoning.
sys.path.insert(0, "digital_twin")

import _uart_link_contract
from machine import UART, LinkPoller, Pin, UARTLink


def make_link(**kwargs: "int | None") -> "tuple[UART, UART, UARTLink]":
    UART._live.clear()  # each test constructs its own pair (A3.3), never a shared module-level one
    a = UART(0, tx=Pin(0), rx=Pin(1), baudrate=115200)
    b = UART(1, tx=Pin(8), rx=Pin(9), baudrate=115200)
    return a, b, UARTLink(a, b, **kwargs)


def test_twin_link_satisfies_the_shared_contract() -> None:
    for check in _uart_link_contract.ALL_CHECKS:
        check(make_link)


def test_bus_id_is_allocated_exclusively() -> None:
    # A4.2: a second live instance on one peripheral id would silently mis-route a whole link.
    a, _b, _link = make_link()
    try:
        UART(a.id, tx=Pin(0), rx=Pin(1))
    except ValueError:
        pass
    else:
        raise AssertionError("a second live UART on the same id must be refused")
    a.deinit()
    UART(a.id, tx=Pin(0), rx=Pin(1))  # the id is free again once the first one is deinit'd


def test_delivery_takes_real_wire_time() -> None:
    # A4.3: a twin link that ran faster than real time would make every drain/cooldown test pass
    # for the wrong reason. 64 bytes at 1200 baud is ~533ms of wire time; assert a floor well
    # under that but far above zero, so the test is about the mechanism, not the exact clock.
    UART._live.clear()
    a = UART(0, tx=Pin(0), rx=Pin(1), baudrate=1200)
    b = UART(1, tx=Pin(8), rx=Pin(9), baudrate=1200)
    link = UARTLink(a, b)
    a.write(bytes(64))
    assert b.read() is None  # nothing has arrived yet - the wire is still busy
    start = time.ticks_ms()
    link.settle()
    elapsed = time.ticks_diff(time.ticks_ms(), start)
    assert elapsed > 100, f"delivery took {elapsed}ms, expected real wire time"
    got = b.read()
    assert got is not None
    assert len(got) == 64


def test_faster_baud_delivers_faster() -> None:
    # The wire time derives from the configured baud rate, not a constant (A4.3).
    def elapsed_for(baudrate: int) -> int:
        UART._live.clear()
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
    a, b, _link = make_link()
    a.write(b"pump")
    deadline = time.ticks_add(time.ticks_ms(), 500)
    got = bytearray()
    while len(got) < 4 and time.ticks_diff(deadline, time.ticks_ms()) > 0:
        part = b.read()  # arrives byte by byte as its wire time elapses, like a real stream
        if part is not None:
            got += part
    assert bytes(got) == b"pump"


def test_twin_poller_requeries_ioctl() -> None:
    a, b, link = make_link()
    poller = LinkPoller(b)
    import select

    assert poller.ipoll(0) == [(None, select.POLLOUT)]
    a.write(b"x")
    link.settle()
    assert poller.ipoll(0) == [(None, select.POLLIN | select.POLLOUT)]


def test_twin_poller_is_not_a_real_select_poll() -> None:
    import select

    _a, b, _link = make_link()
    assert type(LinkPoller(b)).__name__ != type(select.poll()).__name__


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
