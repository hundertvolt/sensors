"""Ad-hoc, read-only (2026-10-08): how long the board's NTP takes to resync on its own after the bench NTP
tests leave it unsynced, with the timestamped console's NTP lines - the backoff the twin must reproduce."""

import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, "/home/nico/programming/sensors/tests_hardware")
import http_client  # noqa: E402
import serial  # noqa: E402
from harness import Board  # noqa: E402

DUT = "192.168.85.57"
OUT = Path(sys.argv[1])
LIMIT_S = 900.0
t0 = time.monotonic()
console: list[str] = []
stop = threading.Event()


def tail() -> None:
    with serial.Serial(Board().device, 115200, timeout=0.5) as port:
        while not stop.is_set() and time.monotonic() - t0 < LIMIT_S + 30:
            raw = port.readline()
            if raw:
                console.append(f"{time.monotonic() - t0:.3f} " + raw.decode("utf-8", "replace").rstrip("\r\n"))


th = threading.Thread(target=tail, daemon=True)
th.start()
samples = []
synced_at = None
while time.monotonic() - t0 < LIMIT_S:
    try:
        n = http_client.fetch(DUT, 80, "GET", "/status", timeout_s=8.0).json()["networking"]
        samples.append({"t": round(time.monotonic() - t0, 1), **{k: v for k, v in n.items() if k.startswith("NTP")}})
        if n.get("NTPSynced") is True:
            synced_at = round(time.monotonic() - t0, 1)
            break
    except Exception as e:  # noqa: BLE001 - recorded, not fatal
        samples.append({"t": round(time.monotonic() - t0, 1), "error": repr(e)})
    time.sleep(5.0)
time.sleep(5.0)
stop.set()
th.join(timeout=10)
ntp_lines = [ln for ln in console if " NTP " in ln or "DNS" in ln or "WIFI" in ln]
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "ntp_recovery.json").write_text(json.dumps({"synced_after_s": synced_at, "limit_s": LIMIT_S, "samples": samples, "console_ntp_lines": ntp_lines}, indent=1))
print("synced_after_s", synced_at, "samples", len(samples), "ntp lines", len(ntp_lines))
