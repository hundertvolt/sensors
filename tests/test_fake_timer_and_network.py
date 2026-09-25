"""Fidelity tests for two tests/ fakes other suites lean on: machine.Timer spends a ONE_SHOT the way
rp2 does (so a dropped fire is modelled), and network enforces the real byte bounds (C.7.4) - a
fake that drifts from silicon would let a test pass for code that fails on the board."""

import machine
import network
from machine import Timer

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any


def test_a_triggered_one_shot_is_spent() -> None:
    fired = []
    timer = Timer()
    timer.init(period=1000, mode=Timer.ONE_SHOT, callback=lambda _t: fired.append(1))
    timer.trigger()
    timer.trigger()  # the period cannot elapse twice for a one-shot
    assert fired == [1]
    assert timer.callback is None


def test_a_triggered_periodic_stays_armed() -> None:
    fired = []
    timer = Timer()
    timer.init(period=1000, mode=Timer.PERIODIC, callback=lambda _t: fired.append(1))
    for _ in range(3):
        timer.trigger()
    assert fired == [1, 1, 1]


def test_a_dropped_one_shot_never_fires_but_a_dropped_periodic_fires_next_period() -> None:
    # Part F.1: a soft callback lost to a full scheduler queue. drop() is that lost period.
    one_shot, periodic = [], []
    a = Timer()
    a.init(period=1000, mode=Timer.ONE_SHOT, callback=lambda _t: one_shot.append(1))
    b = Timer()
    b.init(period=1000, mode=Timer.PERIODIC, callback=lambda _t: periodic.append(1))
    a.drop()
    b.drop()
    a.trigger()
    b.trigger()
    assert (one_shot, periodic) == ([], [1])


def test_a_deinit_timer_neither_fires_nor_minds_a_drop() -> None:
    fired = []
    timer = Timer()
    timer.init(period=1000, mode=Timer.PERIODIC, callback=lambda _t: fired.append(1))
    timer.deinit()
    timer.drop()
    timer.trigger()
    assert fired == []
    assert machine.Timer is Timer


def _raises(exc: "type[BaseException]", fn: "object", *args: object) -> bool:
    try:
        fn(*args)  # type: ignore[operator]
    except exc:
        return True
    return False


def test_country_takes_exactly_two_bytes() -> None:
    assert network.country("AT") == "AT"
    for bad in ("A", "AUT", "ÄT"):  # "ÄT" is 2 characters and 3 bytes
        assert _raises(ValueError, network.country, bad), bad
    assert network.country() == "AT"  # a refused call changes nothing
    network.country("DE")


def test_hostname_takes_at_most_thirty_two_bytes() -> None:
    assert network.hostname("ä" * 16) == "ä" * 16
    assert _raises(ValueError, network.hostname, "ä" * 16 + "x")
    assert network.hostname() == "ä" * 16
    network.hostname("SensorNode")


def test_connect_refuses_an_over_long_key_and_ssid() -> None:
    wlan: Any = network.WLAN(network.STA_IF)  # the fake's connect_calls is test-only, absent from the board stub
    assert _raises(OSError, wlan.connect, "net", "ä" * 32 + "x")  # 65 bytes
    assert _raises(AssertionError, wlan.connect, "ä" * 16 + "x", "password")  # 33 bytes
    wlan.connect("ä" * 16, "ä" * 32)  # both exactly at the bound
    assert wlan.connect_calls[-1] == ("ä" * 16, "ä" * 32)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
