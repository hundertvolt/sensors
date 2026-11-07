# Exposure sweep: re-runs every test_* function of one tests/ file with ONE whole-interpreter stall
# of D ms injected right after the k-th asyncio.sleep_ms() inside asy_uart_driver/asy_uart_comm
# (the deadline is already computed, so the parked task is overdue on wake - a host preemption).
# Usage (cwd = worktree): micropython -X heapsize=16M exposure_sweep.py <test_file> <D_ms> <kmax> <stride, 0=auto ~150 samples, -N=~N samples> [substr] [gc_threshold]
import gc
import sys
import time

import asyncio as _real_asyncio

import asy_uart_comm
import asy_uart_driver

TEST_FILE = sys.argv[1]
D_MS = int(sys.argv[2])
KMAX = int(sys.argv[3])
STRIDE = int(sys.argv[4])
SUBSTR = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] != "-" else ""
if len(sys.argv) > 6:
    gc.threshold(int(sys.argv[6]))

ST = {"k": 0, "target": -1, "on": False}


class _Shim:
    def __init__(self) -> None:
        for name in ("sleep", "get_event_loop", "create_task", "wait_for", "TimeoutError", "CancelledError", "Event", "Lock", "current_task", "gather"):
            if hasattr(_real_asyncio, name):
                setattr(self, name, getattr(_real_asyncio, name))

    def sleep_ms(self, t):  # noqa: ANN001,ANN201
        gen = _real_asyncio.sleep_ms(t)
        if ST["on"]:
            ST["k"] += 1
            if ST["k"] == ST["target"]:
                time.sleep_ms(D_MS)
        return gen


SHIM = _Shim()
asy_uart_driver.asyncio = SHIM
asy_uart_comm.asyncio = SHIM

ns = {"__name__": "exposure", "__file__": TEST_FILE}
with open(TEST_FILE) as f:
    exec(compile(f.read(), TEST_FILE, "exec"), ns)  # noqa: S102

names = sorted(n for n, v in ns.items() if n.startswith("test_") and callable(v) and SUBSTR in n)


def attempt(fn, target):  # noqa: ANN001,ANN201
    ST["k"] = 0
    ST["target"] = target
    ST["on"] = True
    t0 = time.ticks_ms()
    try:
        fn()
        verdict = None
    except Exception as e:  # noqa: BLE001
        import io  # noqa: PLC0415
        buf = io.StringIO()
        sys.print_exception(e, buf)
        where = [ln.strip() for ln in buf.getvalue().split("\n") if ", line " in ln][-1:]  # innermost frame
        verdict = "%s: %s @ %s" % (type(e).__name__, e, where[0] if where else "?")
    ST["on"] = False
    return verdict, ST["k"], time.ticks_diff(time.ticks_ms(), t0)


for name in names:
    fn = ns[name]
    verdict, count, ms = attempt(fn, -1)
    if verdict is not None:
        print("BASEFAIL %s %s" % (name, verdict))
        continue
    if ms > 4000:
        print("SKIPLONG %s clean=%dms sleeps=%d" % (name, ms, count))
        continue
    flips = []
    # 0 = auto (about 150 samples per test); -N = about N samples per test
    stride = STRIDE if STRIDE > 0 else max(1, count // (150 if STRIDE == 0 else -STRIDE))
    for k in range(1, min(count, KMAX) + 1, stride):
        v, _, _ = attempt(fn, k)
        if v is not None:
            flips.append((k, v[:220]))
    tested = len(range(1, min(count, KMAX) + 1, stride))
    if flips:
        kinds = sorted({v for _, v in flips})
        print("FLIP %s %d/%d k=%s first=%s" % (name, len(flips), tested, [k for k, _ in flips], flips[0][1]))
        for kind in kinds:
            print("     kind: %s  k=%s" % (kind, [k for k, v in flips if v == kind]))
    else:
        print("ok   %s 0/%d sleeps=%d clean=%dms" % (name, tested, count, ms))
sys.exit(0)
