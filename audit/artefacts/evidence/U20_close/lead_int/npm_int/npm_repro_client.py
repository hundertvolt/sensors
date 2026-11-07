"""Replays the live PUT matrix's arzi SCD30 sequence against a twin, printing each answer with its time."""

import json
import sys
import time
import urllib.request

BASE = sys.argv[1]
T0 = time.monotonic()


def call(method: str, path: str, body: "dict | None" = None) -> "dict":
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read() or b"{}")
    except Exception as e:  # noqa: BLE001 - a repro prints whatever went wrong
        return {"error": repr(e)}


def remount() -> None:
    # The page's remount reads every section the UI shows.
    for path in ("/sensors", "/system", "/networking", "/notification", "/status", "/measurements"):
        call("GET", path)


def put(key: str, value: object) -> None:
    answer = call("PUT", "/sensors", {"SCD30": {key: value}})
    status = call("GET", "/status")
    t = time.monotonic() - T0
    print(f"t={t:6.1f}s PUT {key}={value!r}: {json.dumps(answer.get('result', answer))} ConfigUnpersisted={status.get('ConfigUnpersisted')} up={status.get('SysUptime')}", flush=True)
    remount()
    time.sleep(1.5)


if "debug" in sys.argv[2:]:
    print("debug:", call("PUT", "/system", {"DebugLevel": 5}), flush=True)
steps = [("TempOffset", v) for v in (0.0, -0.5, 655.85, 1.5, 0, 327.68, 655.35)]
steps += [("MeasInterval", v) for v in (2, 1, 1801, 2.5, 2, 901, 1800)]
steps += [("Altitude", v) for v in (0, -1, 65536, 0.5, 0, 32768, 65535)]
steps += [("SelfCal", True), ("FRCNoise", 20.0), ("FRCNoise", 10.0), ("FRCRate", 10.0)]
for key, value in steps:
    put(key, value)
for _ in range(2):
    time.sleep(5)
    put("FRCNoise", 20.0)

print("STATUS", json.dumps(call("GET", "/status")), flush=True)
