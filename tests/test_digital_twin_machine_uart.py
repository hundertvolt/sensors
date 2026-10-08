"""Unit tests for digital_twin/machine.py's UART fake and its wire-timed crossover link.
Re-runs tests/_uart_link_contract.py's shared bodies against the twin backend, so the twin and
mock link models can differ in fidelity but never in semantics."""

import select
import sys
import time

# digital_twin/ must precede tests/ so `machine` resolves to the twin's own fake, not
# tests/machine.py's - see test_digital_twin_machine.py's own comment for the full reasoning.
sys.path.insert(0, "digital_twin")

import _uart_link_contract
import machine
import rp2
from machine import UART, LinkPoller, Pin, UARTLink

# @tunable l2.machine_uart_wire_time_floor_ms = 100
_WIRE_TIME_FLOOR_MS = 100
# @tunable l2.machine_uart_pump_deadline_ms = 500
_PUMP_DEADLINE_MS = 500


def make_link(**kwargs: "int | None") -> "tuple[UART, UART, UARTLink]":
    UART._live.clear()  # each test constructs its own pair, never a shared module-level one
    a = UART(0, tx=Pin(0), rx=Pin(1), baudrate=115200)
    b = UART(1, tx=Pin(8), rx=Pin(9), baudrate=115200)
    return a, b, UARTLink(a, b, **kwargs)


def test_twin_link_satisfies_the_shared_contract() -> None:
    for check in _uart_link_contract.ALL_CHECKS:
        check(make_link)


def test_a_second_instance_on_one_bus_id_supersedes_the_first() -> None:
    # Real machine.UART() re-inits the peripheral rather than refusing, so what has to be
    # modelled is that the displaced instance stops carrying bytes - a half-live one would
    # silently mis-route a whole link.
    a, b, link = make_link()
    before = UART.superseded
    replacement = UART(a.id, tx=Pin(0), rx=Pin(1))
    assert UART.superseded == before + 1
    assert a.deinit_called is True
    assert a._link is None
    assert b._link is None  # the link is broken for both ends at once, never half-attached
    b.write(b"stale")
    link.settle()
    assert a.read() is None  # nothing reaches the displaced instance any more
    assert replacement.id == a.id


def test_delivery_takes_real_wire_time() -> None:
    # A twin link that ran faster than real time would make every drain/cooldown test pass
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
    assert elapsed > _WIRE_TIME_FLOOR_MS, f"delivery took {elapsed}ms, expected real wire time"
    got = b.read()
    assert got is not None
    assert len(got) == 64


def test_faster_baud_delivers_faster() -> None:
    # The wire time derives from the configured baud rate, not a constant.
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
    deadline = time.ticks_add(time.ticks_ms(), _PUMP_DEADLINE_MS)
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


def test_a_new_wiring_frees_every_dma_channel() -> None:
    # A new board: channels a previous build claimed are released, as a soft reset's finalisers do.
    claimed = [rp2.DMA() for _ in range(3)]
    machine.configure_wiring(machine._current_wiring_plan())
    assert machine._DMA_CHANNELS == {}
    assert all(channel.channel == 0xFF for channel in claimed)


def test_a_poller_asks_only_for_its_mask() -> None:
    # The driver registers POLLOUT alone; a bounded poller asking for POLLIN too would count as a receive poll.
    _a, b, _link = make_link()
    b.rx_api_calls = 0
    assert LinkPoller(b, mask=select.POLLOUT).ipoll(0) == [(None, select.POLLOUT)]
    assert b.rx_api_calls == 0
    LinkPoller(b).ipoll(0)
    assert b.rx_api_calls == 1


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
