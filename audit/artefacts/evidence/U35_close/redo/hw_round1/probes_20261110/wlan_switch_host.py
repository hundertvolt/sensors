"""Host side of snap58_wlan_switch.py (bench, 2026-11-10, item 6): runs it under mpremote, stamps each console line with
host time, takes the bench AP down until the DUT reports its hotspot, up again until it reports STA (ap_up() in a
finally on every path), then stops the run and restores the board. Bounded: every wait has a cap."""
import os
import subprocess
import sys
import threading
import time

sys.path[:0] = ["tests_hardware", "."]
import harness  # noqa: E402
from bench_control import BenchBridge  # noqa: E402

SCRIPT = "audit/artefacts/evidence/U35_close/redo/hw_round1/probes_20261110/snap58_wlan_switch.py"
OUT = sys.argv[1]
HOTSPOT_PERIOD_S = 8 * 60  # devices/dev.toml hotspot_time_min = 8
lines = []
lock = threading.Lock()


def stamp():
    return time.strftime("%H:%M:%S", time.gmtime()) + ".%03d" % (int(time.time() * 1000) % 1000)


def note(text):
    with lock:
        lines.append("HOST " + stamp() + " " + text)
    print("HOST", stamp(), text, flush=True)


def reader(p, f):
    for raw in iter(p.stdout.readline, b""):
        s = raw.decode(errors="replace").rstrip("\r\n")
        with lock:
            lines.append(stamp() + " " + s)
        f.write(stamp() + " " + s + "\n")
        f.flush()


def wait_for(pred, cap_s, what):
    end = time.monotonic() + cap_s
    while time.monotonic() < end:
        with lock:
            hit = [ln for ln in lines if pred(ln)]
        if hit:
            note("seen " + what + ": " + hit[-1][:140])
            return True
        time.sleep(0.5)
    note("NOT seen within %d s: %s" % (cap_s, what))
    return False


dev = harness.resolve_board_device()
bench = BenchBridge()
with open(OUT, "w") as f:
    p = subprocess.Popen([".venv/bin/mpremote", "connect", dev, "run", SCRIPT], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    threading.Thread(target=reader, args=(p, f), daemon=True).start()
    try:
        ok = wait_for(lambda ln: " MODE " in ln and "sta_conn 1 ap 0" in ln, 180, "boot done and STA")
        if ok:
            time.sleep(60)
            note("ap_down()")
            bench.ap_down()
            ok = wait_for(lambda ln: " MODE " in ln and " ap 1" in ln, 300, "hotspot (ap 1)")
        if ok:
            time.sleep(20)
            mark = len(lines)
            note("ap_up()")
            bench.ap_up()
            t_up = time.monotonic()
            ok = wait_for(lambda ln: lines.index(ln) > mark and " MODE " in ln and "sta_conn 1 ap 0" in ln, HOTSPOT_PERIOD_S + 120, "back in STA")
            note("ap_up() to STA seen: %.1f s" % (time.monotonic() - t_up) if ok else "stayed in hotspot past its period")
            if ok:
                time.sleep(60)
    finally:
        bench.ap_up()
        note("ap_up() in finally (no-op when already up)")
        p.send_signal(2)
        try:
            p.wait(30)
        except subprocess.TimeoutExpired:
            p.kill()
        time.sleep(2)
        f.write("\n".join(ln for ln in lines if ln.startswith("HOST ")) + "\n")
board = harness.Board(dev)
harness.restore_board_to_serving(board, bench, os.environ["DUT_IP"])
note("serving")
