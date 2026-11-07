"""Isolated-driver device script: records how the radio reacts to malformed country codes - for each, the station
interface torn down, network.country() set, a fresh interface raised and one scan - then restores the country found at
the start and the radio on. Reports what happened per value; nothing here is a verdict."""

import network

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    import machine
    from _shared.facts import done, fact
    from _shared.watchdog import arm

# Two characters each, so network.country() takes every one (extmod/modnetwork.c:134-147, v1.29.0, refuses only a length
# other than two); the radio meets them at active(True), cyw43_wifi_set_up() with the code (network_cyw43.c:149).
_VALUES = ("ZZ", "12", "\x01\x02")


def _attempt(value: str, wdt: "machine.WDT") -> "dict[str, object]":
    # One value: deinit, country, a fresh active(True) and one scan. scan() blocks up to its own 10 s
    # (network_cyw43.c:233), past the 8 s watchdog, so the feed comes right before it.
    outcome: dict[str, object] = {"value": value}
    network.WLAN(network.STA_IF).deinit()
    try:
        network.country(value)
        outcome["set"] = True
    except (ValueError, OSError) as e:
        outcome["set"] = repr(e)
    wlan = network.WLAN(network.STA_IF)
    try:
        wlan.active(True)
        outcome["radio_on"] = wlan.active()
        wdt.feed()
        outcome["scan_count"] = len(wlan.scan())
    except OSError as e:
        outcome["radio_on"] = repr(e)
    outcome["readback"] = network.country()
    wdt.feed()
    return outcome


def _main() -> None:
    wdt = arm()
    before = network.country()
    fact("country_before", before)
    try:
        for i, value in enumerate(_VALUES):
            fact(f"value_{i}", _attempt(value, wdt))
    finally:
        try:
            network.WLAN(network.STA_IF).deinit()
            network.country(before)
            wlan = network.WLAN(network.STA_IF)
            wlan.active(True)
            restored = "ok" if network.country() == before and wlan.active() else f"country {network.country()!r}, radio {wlan.active()}"
        except (ValueError, OSError) as e:
            restored = repr(e)
        fact("restored", restored)
    done()


_main()
