"""Unit tests for tests/machine.py's UART crossover link model and its bounded poller stand-in
(requirements A1-A3). The backend-agnostic half lives in _uart_link_contract.py and is re-run
against digital_twin/machine.py's own link by test_digital_twin_machine_uart.py (A4.1)."""

import select

import _uart_link_contract
from machine import UART, LinkPoller, Pin, UARTLink

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any


def make_link(**kwargs: "Any") -> "tuple[UART, UART, UARTLink]":
    a = UART(0, tx=Pin(0), rx=Pin(1))
    b = UART(1, tx=Pin(8), rx=Pin(9))
    return a, b, UARTLink(a, b, **kwargs)


# ---------------------------------------------------------------------------
# A1/A3 - the shared semantic contract, run against the mock backend
# ---------------------------------------------------------------------------


def test_link_satisfies_the_shared_contract() -> None:
    for check in _uart_link_contract.ALL_CHECKS:
        check(make_link)


# ---------------------------------------------------------------------------
# A1 - link model specifics
# ---------------------------------------------------------------------------


def test_unattached_uart_still_behaves_as_before() -> None:
    # Every existing tests/machine.py user constructs a bare UART and feeds it via feed_rx().
    uart = UART(0, tx=Pin(0), rx=Pin(1))
    uart.feed_rx(b"abc")
    assert uart.read() == b"abc"
    assert uart.write(b"xy") == 2
    assert uart.log[-1] == ("write", b"xy")


def test_capacity_defaults_to_the_destination_rxbuf() -> None:
    # A1.3 and C2.9/C2.10: the far side's own rxbuf is what really drops a frame's tail.
    a = UART(0, tx=Pin(0), rx=Pin(1), rxbuf=64)
    b = UART(1, tx=Pin(8), rx=Pin(9), rxbuf=128)
    link = UARTLink(a, b)
    assert link.direction_from(a).capacity == 128  # a -> b is bounded by b's rxbuf
    assert link.direction_from(b).capacity == 64


def test_direction_from_rejects_a_foreign_endpoint() -> None:
    a, _b, link = make_link()
    other = UART(0, tx=Pin(0), rx=Pin(1))
    assert link.direction_from(a) is link.a_to_b
    try:
        link.direction_from(other)
    except ValueError:
        return
    raise AssertionError("a foreign endpoint must be rejected")


def test_each_direction_counts_its_own_traffic() -> None:
    a, b, link = make_link()
    a.write(b"123")
    b.write(b"45")
    assert link.direction_from(a).offered == 3
    assert link.direction_from(a).delivered == 3
    assert link.direction_from(b).offered == 2


def test_a_second_link_on_the_same_fakes_is_refused() -> None:
    # A3.3's cross-test contamination, one level down: an endpoint belongs to exactly one link.
    a, b, _link = make_link()
    try:
        UARTLink(a, b)
    except ValueError:
        return
    raise AssertionError("re-attaching an already-linked UART must raise")


# ---------------------------------------------------------------------------
# A2 - bounded poller stand-in
# ---------------------------------------------------------------------------


def test_poller_requeries_ioctl_on_every_call() -> None:
    # A2.2: readiness that was true once must not stay true.
    a, b, _link = make_link()
    poller = LinkPoller(b)
    assert poller.ipoll(0) == [(None, select.POLLOUT)]
    a.write(b"x")
    assert poller.ipoll(0) == [(None, select.POLLIN | select.POLLOUT)]
    b.read()
    assert poller.ipoll(0) == [(None, select.POLLOUT)]


def test_poller_can_be_forced_not_ready_for_n_calls() -> None:
    # A2.3: without this the timeout paths are unreachable and every timeout test passes blindly.
    a, b, _link = make_link()
    a.write(b"x")
    poller = LinkPoller(b)
    poller.force_not_ready(2)
    assert poller.ipoll(0) == []
    assert poller.ipoll(0) == []
    assert poller.ipoll(0) == [(None, select.POLLIN | select.POLLOUT)]


def test_poller_is_not_a_real_select_poll() -> None:
    # A1.2/A2.1: the standing rule, asserted rather than left to review.
    _a, b, _link = make_link()
    poller = LinkPoller(b)
    assert not isinstance(poller, type(select.poll()))


def test_poller_register_and_unregister_are_inert() -> None:
    _a, b, _link = make_link()
    poller = LinkPoller(b)
    poller.register(b, select.POLLIN)
    poller.unregister(b)
    assert poller.ipoll(0) == [(None, select.POLLOUT)]


# ---------------------------------------------------------------------------
# A3 - determinism
# ---------------------------------------------------------------------------


def test_fault_knobs_are_deterministic_across_identical_runs() -> None:
    # A3.1: no unseeded randomness anywhere - two identical runs produce identical wire logs.
    def run_once() -> bytes:
        a, b, link = make_link()
        link.direction_from(a).drop_indices = {2, 5}
        link.direction_from(a).corrupt_indices = {0: 0x0F}
        a.write(bytes(range(8)))
        b.read()
        return bytes(link.direction_from(a).wire_log)

    assert run_once() == run_once()


def test_knobs_are_per_direction_and_independent() -> None:
    # A3.2: a one-sided fault is the realistic case and must be expressible.
    a, b, link = make_link()
    link.direction_from(a).silent = True
    a.write(b"lost")
    b.write(b"kept")
    assert b.read() is None
    assert a.read() == b"kept"


def test_each_link_is_freshly_constructed() -> None:
    # A3.3: no module-level shared link object - two make_link() calls share no state.
    a1, _b1, link1 = make_link()
    link1.direction_from(a1).silent = True
    a2, b2, _link2 = make_link()
    a2.write(b"ok")
    assert b2.read() == b"ok"


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
