"""Isolated-driver device script: real network.country()/network.hostname() behavior for
schema-valid-but-functionally-bogus values (a non-ISO country code; a Hostname whose char count
passes the schema cap but whose UTF-8 byte count exceeds the real 32-byte cap) - tested in isolation to avoid a real hotspot cascade."""

import network

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# Case 1: syntactically valid (2 chars), not a real ISO 3166-1 alpha-2 code.
try:
    network.country("XX")
    readback = network.country()
    print(f"RESULT: country('XX') PASS accepted, readback={readback!r}")
except Exception as e:
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
except Exception as e:
    print(f"RESULT: hostname(64 UTF-8 bytes) PASS raised {type(e).__name__}: {e}")

# The interpreter itself must still be alive and responsive after both cases - the actual pass
# condition this whole script exists to check (asy_wifi_service.py's own try/except around both
# calls means neither should ever be able to crash the process; this is the direct proof).
print("RESULT: interpreter survived both edge-value calls")
