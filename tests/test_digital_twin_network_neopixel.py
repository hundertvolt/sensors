"""Tests for digital_twin/network.py and digital_twin/neopixel.py. neopixel.py is a near-verbatim
duplicate of tests/neopixel.py (owner's explicit "duplicate for independence" choice,
FINAL_WIRING_PLAN.md's Step 3), already proven correct there by test_asy_neopixel_driver.py - this
file only locks in its basic shape. network.py's WLAN has real behavioral differences from
tests/network.py's own inert fixture (owner's own specified strategy, same session): connect()
transitions through STAT_CONNECTING -> STAT_GOT_IP over a short, real delay instead of resolving
instantly or staying inert, and ifconfig() reports the host's own real network address - these are
exercised for real here (the one place in this whole file with a genuine, bounded, generous-timeout
wall-clock wait, matching test_digital_twin_machine.py's own precedent for Timer).
"""

import asyncio
import sys

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")

sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

from neopixel import NeoPixel  # noqa: E402
from network import STA_IF, STAT_CONNECTING, STAT_GOT_IP, STAT_IDLE, WLAN  # noqa: E402


def run(coro: "Coroutine[Any, Any, T]") -> "T":
    return asyncio.run(coro)


async def _wait_until_connected(wlan: WLAN, timeout_s: float = 5.0) -> None:
    async def poll() -> None:
        while not wlan.isconnected():
            await asyncio.sleep_ms(20)

    await asyncio.wait_for(poll(), timeout_s)


def test_wlan_starts_disconnected() -> None:
    wlan = WLAN(STA_IF)
    assert wlan.isconnected() is False
    assert wlan.status() == STAT_IDLE


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
        assert wlan.connect_calls == [("ssid", "password")]

    run(scenario())


def test_wlan_ifconfig_reports_a_plausible_address_once_connected() -> None:
    async def scenario() -> None:
        wlan = WLAN(STA_IF)
        assert wlan.ifconfig()[0] == "0.0.0.0"  # not yet connected
        wlan.connect("ssid", "password")
        await _wait_until_connected(wlan)
        ip = wlan.ifconfig()[0]
        assert ip != "0.0.0.0"  # a real connected device never reports the unconfigured address
        parts = ip.split(".")
        assert len(parts) == 4 and all(part.isdigit() for part in parts)

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
    wlan.raise_on["connect"] = OSError("simulated radio failure")
    try:
        wlan.connect("ssid", "password")
        raise AssertionError("expected OSError")
    except OSError:
        pass
    assert wlan.isconnected() is False


def test_neopixel_records_committed_frames() -> None:
    pixel = NeoPixel(None, 1, bpp=3)
    pixel[0] = (10, 20, 30)
    pixel.write()
    pixel[0] = (0, 0, 0)
    pixel.write()
    assert pixel.writes == [[(10, 20, 30)], [(0, 0, 0)]]


def test_neopixel_fault_injection() -> None:
    pixel = NeoPixel(None, 1)
    pixel.raise_on_write = RuntimeError("simulated bit-bang failure")
    try:
        pixel.write()
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
