"""Tests for digital_twin/network.py and digital_twin/neopixel.py. neopixel.py is a near-verbatim duplicate of tests/neopixel.py, already proven correct there - this file only locks in its basic shape.
network.py's WLAN has real behavioral differences (a real, bounded connect() delay instead of instant/inert) exercised for real here, the one genuine wall-clock wait in this file."""

import asyncio
import errno
import sys

sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

import microtest
import network
from _async_harness import run
from _src_const import src_const
from _twin_common import COUNTER_CAP, LOG_MAXLEN
from neopixel import NeoPixel
from network import (
    AP_IF,
    STA_IF,
    STAT_CONNECT_FAIL,
    STAT_CONNECTING,
    STAT_GOT_IP,
    STAT_IDLE,
    STAT_NO_AP_FOUND,
    STAT_WRONG_PASSWORD,
    WLAN,
    set_access_point_up,
)

# @tunable l2.network_neopixel_wait_timeout_s = 5.0
_WAIT_TIMEOUT_S = 5.0
# @tunable l2.network_neopixel_poll_ms = 20
_POLL_MS = 20
_UNSET = ("0.0.0.0", "0.0.0.0", "0.0.0.0", "0.0.0.0")

microtest.after_each(network.reset_test_state)


def _raised(call: "object") -> "BaseException | None":
    try:
        call()  # type: ignore[operator]
    except Exception as e:  # the raised object is what each case asserts
        return e
    return None


def _value_error(call: "object") -> str:
    try:
        call()  # type: ignore[operator]
    except ValueError as e:
        return str(e)
    raise AssertionError("expected ValueError")


def test_one_connect_phase_fits_the_services_poll_budget() -> None:
    # The twin's connect phase stays under _poll_sta_connect_status()'s whole wait, or every boot would fall back.
    budget_s = src_const("src/asy_wifi_service.py", "_STA_CONNECT_POLL_S") * src_const("src/asy_wifi_service.py", "_STA_CONNECT_POLL_ITERS")  # type: ignore[operator]
    assert budget_s > network._CONNECT_DELAY_S


def test_wlan_starts_disconnected() -> None:
    wlan = WLAN(STA_IF)
    assert wlan.isconnected() is False
    assert wlan.status() == STAT_IDLE


def test_wlan_deinit_sets_the_deinit_called_flag() -> None:
    wlan = WLAN(STA_IF)
    assert wlan.deinit_called is False
    wlan.deinit()
    assert wlan.deinit_called is True


def test_wlan_status_rssi_and_stations_read_the_underlying_fields() -> None:
    sta, ap = WLAN(STA_IF), WLAN(AP_IF)
    assert sta.status("rssi") == sta._rssi
    assert ap.status("stations") == ap._stations == []


async def _wait_until_connected(wlan: WLAN, timeout_s: float = _WAIT_TIMEOUT_S) -> None:
    async def poll() -> None:
        while not wlan.isconnected():
            await asyncio.sleep_ms(_POLL_MS)

    await asyncio.wait_for(poll(), timeout_s)


def test_status_answers_by_cyw43s_interface_rules() -> None:
    # extmod/network_cyw43.c:352-392: rssi needs the STA, stations the AP, any other query raises.
    sta, ap = WLAN(STA_IF), WLAN(AP_IF)
    assert _value_error(lambda: ap.status("rssi")) == "STA required"
    assert _value_error(lambda: sta.status("stations")) == "AP required"
    assert _value_error(lambda: sta.status("channel")) == "unknown status param"


def test_the_access_point_comes_up_with_its_address_and_the_shared_dns() -> None:
    # cyw43_config.h:194, 206's /24 layout on the loopback (digital_twin/network.py) and network_lwip.c:70-73's one lwIP
    # DNS server both interfaces share.
    ap = WLAN(AP_IF)
    ap.active(True)
    assert (ap.status(), ap.ifconfig()) == (STAT_GOT_IP, ("127.0.0.1", "255.255.255.0", "127.0.0.1", "192.0.2.1"))
    ap.active(False)
    assert (ap.status(), ap.ifconfig()) == (STAT_IDLE, _UNSET)


def test_deinit_powers_the_one_radio_down() -> None:
    # cyw43_deinit() powers the whole chip off (network_cyw43.c:133-137, cyw43_ctrl.c:118-139): both interfaces go down.
    async def scenario() -> None:
        sta, ap = WLAN(STA_IF), WLAN(AP_IF)
        sta.active(True)
        sta.connect("ssid", "password")  # still joining: its pending attempt goes with the radio
        ap.active(True)
        ap.deinit()
        assert (sta.active(), sta.isconnected(), sta.status(), sta.ifconfig(), sta._connect_task) == (False, False, STAT_IDLE, _UNSET, None)
        assert (ap.active(), ap.status(), ap.ifconfig(), ap.deinit_called) == (False, STAT_IDLE, _UNSET, True)

    run(scenario())


def test_config_truncates_as_cyw43_and_reads_the_essid_back() -> None:
    # cyw43.h:431-448: the AP ssid keeps 32 bytes, the key 64; only the essid reads back (network_cyw43.c:410-465).
    ap = WLAN(AP_IF)
    ap.config(essid="x" * 40, password="p" * 70)
    assert ap.config_calls[-1] == {"essid": "x" * 32, "password": "p" * 64}
    assert ap.config("essid") == "x" * 32
    assert _value_error(lambda: ap.config("password")) == "unknown config param"


def test_wlan_config_calls_stays_bounded_across_many_calls() -> None:
    wlan = WLAN(STA_IF)
    for _ in range(LOG_MAXLEN + 50):
        wlan.config(essid="hotspot")
    assert (len(wlan.config_calls), wlan.config_calls.dropped) == (LOG_MAXLEN, 50)
    assert wlan.config_calls[-1] == {"essid": "hotspot"}


def test_country_and_hostname_set_then_get_round_trip() -> None:
    import network as network_module

    assert network_module.country("US") == "US"
    assert network_module.country() == "US"
    assert network_module.hostname("MyDevice") == "MyDevice"
    assert network_module.hostname() == "MyDevice"


def test_wlan_connect_shows_a_real_connecting_phase_before_got_ip() -> None:
    async def scenario() -> None:
        wlan = WLAN(STA_IF)
        wlan.active(True)
        wlan.connect("ssid", "password")
        # Real hardware never resolves instantly - this must still be in progress right after
        # connect() returns, matching the "all phases" strategy (see network.py's own docstring).
        assert wlan.status() == STAT_CONNECTING
        assert wlan.isconnected() is False
        await _wait_until_connected(wlan)
        assert wlan.status() == STAT_GOT_IP
        assert list(wlan.connect_calls) == [("ssid", "password")]  # a deque, not a list

    run(scenario())


def test_a_connected_sta_reports_a_test_net_address() -> None:
    # RFC 5737 TEST-NET-1: the DNS server the twin's DHCP hands out routes nowhere, so no run reaches a public resolver.
    async def scenario() -> None:
        wlan = WLAN(STA_IF)
        assert wlan.ifconfig() == _UNSET  # not yet connected
        wlan.connect("ssid", "password")
        await _wait_until_connected(wlan)
        assert wlan.ifconfig() == ("192.0.2.42", "255.255.255.0", "192.0.2.1", "192.0.2.1")

    run(scenario())


def test_wlan_disconnect_resets_state() -> None:
    async def scenario() -> None:
        wlan = WLAN(STA_IF)
        wlan.connect("ssid", "password")
        await _wait_until_connected(wlan)
        wlan.disconnect()
        assert wlan.isconnected() is False
        assert wlan.status() == STAT_IDLE
        assert wlan.disconnect_called is True

    run(scenario())


def test_wlan_disconnect_before_connecting_finishes_cancels_the_pending_connection() -> None:
    async def scenario() -> None:
        wlan = WLAN(STA_IF)
        wlan.connect("ssid", "password")
        wlan.disconnect()
        await asyncio.sleep(1.0)  # longer than _CONNECT_DELAY_S - must never flip to connected
        assert wlan.isconnected() is False
        assert wlan.status() == STAT_IDLE

    run(scenario())


def test_wlan_fault_injection() -> None:
    wlan = WLAN(STA_IF)
    wlan.raise_on["connect"] = (OSError, ("simulated radio failure",), 1)
    try:
        wlan.connect("ssid", "password")
        raise AssertionError("expected OSError")
    except OSError:
        pass
    assert wlan.isconnected() is False


async def _wait_until_settled(wlan: WLAN, timeout_s: float = _WAIT_TIMEOUT_S) -> None:
    async def poll() -> None:
        while wlan.status() == STAT_CONNECTING:
            await asyncio.sleep_ms(_POLL_MS)

    await asyncio.wait_for(poll(), timeout_s)


def test_one_wlan_object_per_interface_any_other_id_the_access_point() -> None:
    sta = WLAN(STA_IF)
    assert WLAN(STA_IF) is sta and WLAN() is sta
    ap = WLAN(AP_IF)
    assert ap is not sta and WLAN(AP_IF) is ap and WLAN(7) is ap
    assert network.constructions == {STA_IF: 3, AP_IF: 3}


def test_reset_interfaces_forgets_both_objects_and_their_counts() -> None:
    sta = WLAN(STA_IF)
    network.reset_interfaces()
    assert network.constructions == {STA_IF: 0, AP_IF: 0}
    assert WLAN(STA_IF) is not sta


def test_the_construction_count_saturates_at_the_counter_cap() -> None:
    network.constructions[STA_IF] = COUNTER_CAP
    WLAN(STA_IF)
    assert network.constructions[STA_IF] == COUNTER_CAP


def test_raise_on_with_a_count_raises_that_many_fresh_exceptions() -> None:
    wlan = WLAN(STA_IF)
    wlan.raise_on["isconnected"] = (OSError, (errno.EIO, "planted"), 2)
    first = _raised(wlan.isconnected)
    second = _raised(wlan.isconnected)
    assert isinstance(first, OSError) and first.errno == errno.EIO
    assert isinstance(second, OSError) and second is not first
    assert _raised(wlan.isconnected) is None
    assert "isconnected" not in wlan.raise_on


def test_raise_on_without_a_count_raises_until_cleared() -> None:
    wlan = WLAN(STA_IF)
    wlan.raise_on["active"] = (OSError, (errno.EIO,), None)
    assert all(isinstance(_raised(wlan.active), OSError) for _ in range(3))
    del wlan.raise_on["active"]
    assert _raised(wlan.active) is None


def test_a_status_entry_with_a_parameter_filter_fails_only_those_queries() -> None:
    wlan = WLAN(AP_IF)
    wlan.raise_on["status"] = (OSError, (errno.EIO,), None, ("stations",))
    assert wlan.status() == STAT_IDLE
    assert isinstance(_raised(lambda: wlan.status("stations")), OSError)


def test_a_joined_link_with_no_address_holds_status_two() -> None:
    # cyw43's CYW43_LINK_NOIP: joined, but the DHCP server never answers - it stays there, unconnected and unaddressed.
    async def scenario() -> None:
        wlan = WLAN(STA_IF)
        wlan.script_connect_outcomes([2])
        wlan.connect("ssid", "password")
        await _wait_until_settled(wlan)
        await asyncio.sleep_ms(_POLL_MS * 2)
        assert (wlan.status(), wlan.isconnected(), wlan.ifconfig()) == (2, False, _UNSET)

    run(scenario())


def test_reset_test_state_restores_every_network_knob() -> None:
    network.country("US")
    network.hostname("MyDevice")
    set_access_point_up(up=False)
    sta = WLAN(STA_IF)
    network.reset_test_state()
    assert (network.country(), network.hostname(), network._access_point_up) == ("XX", "PicoW", [True])  # rp2's power-on seeds
    assert network.constructions == {STA_IF: 0, AP_IF: 0} and WLAN(STA_IF) is not sta


def test_wlan_script_connect_outcomes_defaults_to_always_succeeding() -> None:
    # Empty/unset queue - every test above this line keeps passing unchanged.
    async def scenario() -> None:
        wlan = WLAN(STA_IF)
        wlan.connect("ssid", "password")
        await _wait_until_settled(wlan)
        assert wlan.status() == STAT_GOT_IP
        assert wlan.isconnected() is True

    run(scenario())


def test_wlan_scripted_failure_outcome_sets_status_and_stays_disconnected() -> None:
    async def scenario() -> None:
        wlan = WLAN(STA_IF)
        wlan.script_connect_outcomes([STAT_NO_AP_FOUND])
        wlan.connect("ssid", "password")
        await _wait_until_settled(wlan)
        assert wlan.status() == STAT_NO_AP_FOUND
        assert wlan.isconnected() is False
        assert wlan.ifconfig() == ("0.0.0.0", "0.0.0.0", "0.0.0.0", "0.0.0.0")

    run(scenario())


def test_wlan_scripted_outcomes_are_consumed_in_order_one_per_completed_attempt() -> None:
    async def scenario() -> None:
        wlan = WLAN(STA_IF)
        wlan.script_connect_outcomes([STAT_WRONG_PASSWORD, STAT_CONNECT_FAIL, STAT_GOT_IP])

        wlan.connect("ssid", "wrong")
        await _wait_until_settled(wlan)
        assert wlan.status() == STAT_WRONG_PASSWORD

        wlan.connect("ssid", "still wrong")
        await _wait_until_settled(wlan)
        assert wlan.status() == STAT_CONNECT_FAIL

        wlan.connect("ssid", "right")
        await _wait_until_settled(wlan)
        assert wlan.status() == STAT_GOT_IP
        assert wlan.isconnected() is True

    run(scenario())


def test_wlan_exhausted_scripted_queue_falls_back_to_always_succeeding() -> None:
    async def scenario() -> None:
        wlan = WLAN(STA_IF)
        wlan.script_connect_outcomes([STAT_NO_AP_FOUND])

        wlan.connect("ssid", "password")
        await _wait_until_settled(wlan)
        assert wlan.status() == STAT_NO_AP_FOUND

        wlan.connect("ssid", "password")  # queue is now empty
        await _wait_until_settled(wlan)
        assert wlan.status() == STAT_GOT_IP
        assert wlan.isconnected() is True

    run(scenario())


def test_wlan_a_successful_reconnect_after_an_earlier_scripted_failure_reports_a_real_address() -> None:
    async def scenario() -> None:
        wlan = WLAN(STA_IF)
        wlan.script_connect_outcomes([STAT_CONNECT_FAIL])
        wlan.connect("ssid", "password")
        await _wait_until_settled(wlan)
        assert wlan.ifconfig()[0] == "0.0.0.0"

        wlan.connect("ssid", "password")  # queue exhausted - succeeds
        await _wait_until_connected(wlan)
        assert wlan.ifconfig()[0] != "0.0.0.0"

    run(scenario())


def test_wlan_disconnect_of_a_pending_attempt_does_not_consume_a_scripted_outcome() -> None:
    async def scenario() -> None:
        wlan = WLAN(STA_IF)
        wlan.script_connect_outcomes([STAT_WRONG_PASSWORD])
        wlan.connect("ssid", "password")
        wlan.disconnect()  # cancels before _run_connect() ever completes - nothing "used"
        await asyncio.sleep(1.0)  # longer than _CONNECT_DELAY_S - must never resolve at all
        assert wlan.isconnected() is False
        assert wlan.status() == STAT_IDLE

        # The queued outcome must still be there for the next attempt that actually completes.
        wlan.connect("ssid", "password")
        await _wait_until_settled(wlan)
        assert wlan.status() == STAT_WRONG_PASSWORD

    run(scenario())


def test_wlan_a_second_connect_that_cancels_the_first_pending_attempt_does_not_consume_an_outcome() -> None:
    async def scenario() -> None:
        wlan = WLAN(STA_IF)
        wlan.script_connect_outcomes([STAT_GOT_IP])
        wlan.connect("ssid", "first")  # immediately superseded below - never completes
        wlan.connect("ssid", "second")
        await _wait_until_settled(wlan)
        assert wlan.status() == STAT_GOT_IP
        assert list(wlan.connect_calls) == [("ssid", "first"), ("ssid", "second")]  # a deque, not a list

    run(scenario())


def test_wlan_connect_calls_stays_bounded_across_many_calls() -> None:
    async def scenario() -> None:
        wlan = WLAN(STA_IF)
        wlan.active(True)
        for _ in range(LOG_MAXLEN + 50):
            wlan.connect("ssid", "password")  # each call cancels/replaces the prior pending task -
            # never accumulates asyncio tasks, only entries in connect_calls itself.
        assert (len(wlan.connect_calls), wlan.connect_calls.dropped) == (LOG_MAXLEN, 50)
        assert wlan.connect_calls[-1] == ("ssid", "password")

    run(scenario())


def test_a_downed_access_point_fails_the_station_until_switched_back() -> None:
    async def scenario() -> None:
        first = WLAN(STA_IF)
        first.connect("ssid", "password")
        await _wait_until_connected(first)  # an address the downed access point must take away
        set_access_point_up(up=False)
        try:
            first.script_connect_outcomes([STAT_WRONG_PASSWORD])
            first.connect("ssid", "password")
            await _wait_until_settled(first)
            assert (first.status(), first.isconnected(), first.ifconfig()) == (STAT_NO_AP_FOUND, False, _UNSET)
            assert WLAN(STA_IF) is first  # the service's next mode switch reaches the same failing interface
            set_access_point_up(up=True)
            first.connect("ssid", "password")
            await _wait_until_settled(first)
            assert first.status() == STAT_WRONG_PASSWORD  # the outcome scripted while the access point was down stayed queued
            first.connect("ssid", "password")
            await _wait_until_settled(first)
            assert (first.status(), first.isconnected()) == (STAT_GOT_IP, True)
        finally:
            set_access_point_up(up=True)

    run(scenario())


def test_a_chip_down_stations_answer_is_32_unfilled_entries() -> None:
    wlan = WLAN(AP_IF)
    client = (b"\x02\x00\x00\x00\x00\x01",)
    wlan._stations = [client]
    wlan.stations_chip_down = True
    stations = wlan.status("stations")
    assert isinstance(stations, list)
    assert len(stations) == 32 and all(entry == (bytes(6),) for entry in stations), stations
    wlan.stations_chip_down = False
    assert wlan.status("stations") == [client]


class _Pin:
    # The one Pin method the library calls: init(OUT) at construction (micropython-lib neopixel.py:16).
    OUT = 1

    def __init__(self) -> None:
        self.modes: list[int] = []

    def init(self, mode: int) -> None:
        self.modes.append(mode)


def test_neopixel_records_committed_frames() -> None:
    pin = _Pin()
    pixel = NeoPixel(pin, 1, bpp=3)
    assert pin.modes == [_Pin.OUT]
    pixel[0] = (10, 20, 30)
    assert pixel[0] == (10, 20, 30)  # readback before the next write() commits it
    pixel.write()
    pixel[0] = (0, 0, 0)
    pixel.write()
    assert list(pixel.writes) == [[(10, 20, 30)], [(0, 0, 0)]]


def test_neopixel_stores_bytes_in_grb_order_as_the_library_does() -> None:
    # micropython-lib neopixel.py:9, 28-31: an int keeps its low byte (py/binary.c:512-521), a float raises TypeError
    # at its component, the earlier components already stored.
    pixel = NeoPixel(_Pin(), 1)
    pixel[0] = (1, 2, 3)
    assert pixel.buf == bytearray(b"\x02\x01\x03")
    pixel[0] = (256, 0, 0)
    assert pixel[0] == (0, 0, 0)
    try:
        pixel[0] = (10, 1.5, 0)  # type: ignore[assignment]
        raise AssertionError("a float colour was stored")
    except TypeError:
        pass
    assert pixel.buf[1] == 10  # R, stored before G raised


def test_a_power_dip_blanks_what_the_pixel_shows_until_the_next_write() -> None:
    pixel = NeoPixel(_Pin(), 1)
    assert pixel.displayed() == [(0, 0, 0)]
    pixel[0] = (5, 6, 7)
    pixel.write()
    pixel.power_dip()
    assert (pixel.displayed(), pixel[0]) == ([(0, 0, 0)], (5, 6, 7))
    pixel.write()
    assert pixel.displayed() == [(5, 6, 7)]


def test_neopixel_writes_stays_bounded_across_many_writes() -> None:
    pixel = NeoPixel(_Pin(), 1, bpp=3)
    for i in range(LOG_MAXLEN + 50):
        pixel[0] = (i & 0xFF, 0, 0)
        pixel.write()
    assert (len(pixel.writes), pixel.writes.dropped) == (LOG_MAXLEN, 50)
    assert pixel.writes[-1] == [((LOG_MAXLEN + 49) & 0xFF, 0, 0)]  # most recent write survives


def test_neopixel_fault_injection() -> None:
    pixel = NeoPixel(_Pin(), 1)
    pixel.raise_on_write = RuntimeError("simulated bit-bang failure")
    try:
        pixel.write()
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass


def test_country_and_hostname_enforce_the_real_byte_bounds() -> None:
    # Mirrors extmod/modnetwork.c: country() takes exactly 2 BYTES, hostname() at most 32 - the
    # checks that make a character-valid "ÄT" raise on silicon (SPECIFICATION.md C.7.4).
    import network as network_module

    for bad in ("D", "DEU", "ÄT"):
        try:
            network_module.country(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("country() accepted " + repr(bad))
    assert network_module.hostname("ä" * 16) == "ä" * 16  # 32 bytes: the bound itself
    try:
        network_module.hostname("ä" * 16 + "x")
    except ValueError:
        pass
    else:
        raise AssertionError("hostname() accepted 33 bytes")


def test_connect_refuses_what_the_real_driver_cannot_take() -> None:
    wlan = WLAN(STA_IF)
    wlan.active(True)
    try:
        wlan.connect("net", "ä" * 32 + "x")  # 65 bytes: cyw43_ll_wifi_join()'s -CYW43_EINVAL
    except OSError as e:
        assert e.args[0] == 22
    else:
        raise AssertionError("connect() took a 65-byte key")
    try:
        wlan.connect("ä" * 16 + "x", "password")  # 33 bytes would overflow the driver's SSID buffer
    except AssertionError:
        pass
    else:
        raise AssertionError("connect() took a 33-byte SSID")


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
