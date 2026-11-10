"""Host side of snap58_stack_load.py (bench, 2026-11-10, lead relay 12:03): runs it under mpremote, starts 6 /status
readers for 60 s 20 s after BOOT_DONE (heap_probe/status_load.py), waits for its DONE, then stops it and restores the
board. Every wait capped. Second form (12:19): mpremote writes straight to the file (no pipe in between), read back by polling.""" 
import os
import subprocess
import sys
import time

sys.path[:0] = ["tests_hardware", "."]
import harness  # noqa: E402
from bench_control import BenchBridge  # noqa: E402

SCRIPT = "audit/artefacts/evidence/U35_close/redo/hw_round1/probes_20261110/snap58_stack_load.py"
LOAD = "audit/artefacts/evidence/U35_close/redo/hw_round1/heap_probe/status_load.py"
OUT = sys.argv[1]
lines = []


def stamp():
    return time.strftime("%H:%M:%S", time.gmtime())


def note(text):
    lines.append("HOST " + stamp() + " " + text)
    print("HOST", stamp(), text, flush=True)


def wait_for(text, cap_s):
    end = time.monotonic() + cap_s
    while time.monotonic() < end:
        with open(OUT, errors="replace") as f:
            if any(ln.startswith(text) for ln in f.read().splitlines()):
                note("seen " + text)
                return True
        time.sleep(0.5)
    note("NOT seen within %d s: %s" % (cap_s, text))
    return False


dev = harness.resolve_board_device()
with open(OUT, "w") as f:
    p = subprocess.Popen([".venv/bin/mpremote", "connect", dev, "run", SCRIPT], stdout=f, stderr=subprocess.STDOUT)
    try:
        if wait_for("SAMPLE s 0 ", 180):
            time.sleep(20)
            note("load start")
            r = subprocess.run(["timeout", "120", "python3", LOAD, "6", "60", "/status"], capture_output=True, text=True)
            note("load end: " + r.stdout.strip())
            wait_for("DONE", 150)
    finally:
        p.send_signal(2)
        try:
            p.wait(30)
        except subprocess.TimeoutExpired:
            p.kill()
with open(OUT + ".host", "w") as h:
    h.write("\n".join(lines) + "\n")
harness.restore_board_to_serving(harness.Board(dev), BenchBridge(), os.environ["DUT_IP"])
note("serving")
