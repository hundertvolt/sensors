"""The closing reset of a step whose script leaves main.py stopped: harness reset_board() (the kick, then the hard
reset), as the flash soaks end, then /status answering, so the next session starts on a serving board (lead, 14:21)."""
import os
import sys
import time

sys.path.insert(0, "tests_hardware")
import http_client  # noqa: E402
from bench_control import BenchBridge  # noqa: E402
from harness import Board, reset_board, wait_until  # noqa: E402

bridge = BenchBridge()
reset_board(Board(), bridge if bridge.is_configured() else None)
started = time.monotonic()
dut = os.environ.get("DUT_IP")
if dut:
    wait_until(lambda: http_client.fetch(dut, 80, "GET", "/status", timeout_s=10.0).status_code == 200, timeout_s=120.0, poll_interval_s=2.0, description="/status answers after the closing reset")
    print(f"SUM closing reset: /status 200 after {time.monotonic() - started:.1f} s")
else:
    print("SUM closing reset: done, DUT_IP unset, /status not read")
