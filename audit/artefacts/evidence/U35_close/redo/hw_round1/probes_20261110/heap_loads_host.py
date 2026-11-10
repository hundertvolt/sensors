"""Host side of snap58_heap_loads.py (bench, 2026-11-10, lead relay 12:23): mpremote writes the console straight to a file
(never a pipe: 12:06's void run); each "LOAD n readers" line starts heap_probe/status_load.py for 60 s; DONE ends the
run with SIGINT, then the board is restored. Every wait capped."""
import os
import subprocess
import sys
import time

sys.path[:0] = ["tests_hardware", "."]
import harness  # noqa: E402
from bench_control import BenchBridge  # noqa: E402

SCRIPT = "audit/artefacts/evidence/U35_close/redo/hw_round1/probes_20261110/snap58_heap_loads.py"
LOAD = "audit/artefacts/evidence/U35_close/redo/hw_round1/heap_probe/status_load.py"
OUT = sys.argv[1]
notes = []


def note(text):
    s = "HOST " + time.strftime("%H:%M:%S", time.gmtime()) + " " + text
    notes.append(s)
    print(s, flush=True)


def console():
    with open(OUT, errors="replace") as f:
        return f.read().splitlines()


def wait_line(pred, cap_s):
    end = time.monotonic() + cap_s
    while time.monotonic() < end:
        hit = [ln for ln in console() if pred(ln)]
        if hit:
            return hit[0]
        time.sleep(0.5)
    return None


dev = harness.resolve_board_device()
with open(OUT, "w") as f:
    p = subprocess.Popen([".venv/bin/mpremote", "connect", dev, "run", SCRIPT], stdout=f, stderr=subprocess.STDOUT)
    try:
        for n in (1, 2, 3, 4):
            ln = wait_line(lambda s, n=n: s.startswith("LOAD %d " % n), 420)
            if ln is None:
                note("LOAD %d not seen" % n)
                break
            readers = ln.split()[2]
            note("load %d start, %s readers" % (n, readers))
            r = subprocess.run(["timeout", "120", "python3", LOAD, readers, "60", "/status"], capture_output=True, text=True)
            note("load %d end: %s" % (n, r.stdout.strip()))
        note("DONE seen" if wait_line(lambda s: s.startswith("DONE"), 300) else "DONE not seen")
    finally:
        p.send_signal(2)
        try:
            p.wait(30)
        except subprocess.TimeoutExpired:
            p.kill()
with open(OUT + ".host", "w") as h:
    h.write("\n".join(notes) + "\n")
harness.restore_board_to_serving(harness.Board(dev), BenchBridge(), os.environ["DUT_IP"])
note("serving")
