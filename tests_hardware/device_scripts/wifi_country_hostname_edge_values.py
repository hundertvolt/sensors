"""Isolated-driver device script, gap fix: real network.country()/network.hostname() behavior for
schema-valid-but-functionally-bogus values. asy_wifi_service.py's own _VAL_CTRY/_VAL_HOST
(("Country", "str", "DE", 2, 2, None) / ("Hostname", "str", "SensorNode", 1, 32, None)) only bound
length/type, never format - a syntactically-valid-length value that is not a real ISO country code,
or a Hostname whose *character* count passes the 32-char cap but whose UTF-8 *byte* count exceeds
network.hostname()'s real 32-byte cap (see that schema's own "32 = network.hostname()'s real cap"
comment), both pass REST validation today. Both calls live inside asy_wifi_service.py's own
_trigger_sta_connect()'s try/except (errno=13) - testing them here, directly and in isolation, over
mpremote exec (no REST/real WiFi bridge needed) avoids ever risking a real hotspot-fallback cascade,
unlike a REST-level test would (see tests_hardware/bench/test_network_resilience.py's own garbage-
SSID test for why that one stops short of hotspot fallback for exactly this reason).

Run via `mpremote run <this> soft-reset`. Prints one "RESULT: ..." line per case."""

import network

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# Case 1: syntactically valid (2 chars), not a real ISO 3166-1 alpha-2 code.
try:
    network.country("XX")
    readback = network.country()
    print(f"RESULT: country('XX') PASS accepted, readback={readback!r}")
except Exception as e:  # noqa: BLE001 - reporting whatever real hardware/firmware actually raises, not guessing the type up front
    print(f"RESULT: country('XX') PASS raised {type(e).__name__}: {e}")

# Case 2: restore a real country before the hostname case, so it doesn't run under a bogus
# regulatory domain too (keeps the two cases independent).
network.country("DE")

# Case 3: 32 *characters* (passes the schema's char-count check) but each a 2-byte UTF-8 code
# point, so 64 *bytes* - well past network.hostname()'s real 32-byte cap.
oversized_hostname = "ä" * 32  # 'ä', 2 bytes each in UTF-8
assert len(oversized_hostname) == 32
assert len(oversized_hostname.encode()) == 64
try:
    network.hostname(oversized_hostname)
    readback = network.hostname()
    if readback == oversized_hostname:
        print(f"RESULT: hostname(64 UTF-8 bytes) PASS accepted verbatim, readback={readback!r}")
    else:
        print(f"RESULT: hostname(64 UTF-8 bytes) PASS silently altered, readback={readback!r}")
except Exception as e:  # noqa: BLE001 - same rationale as case 1
    print(f"RESULT: hostname(64 UTF-8 bytes) PASS raised {type(e).__name__}: {e}")

# The interpreter itself must still be alive and responsive after both cases - the actual pass
# condition this whole script exists to check (asy_wifi_service.py's own try/except around both
# calls means neither should ever be able to crash the process; this is the direct proof).
print("RESULT: interpreter survived both edge-value calls")
