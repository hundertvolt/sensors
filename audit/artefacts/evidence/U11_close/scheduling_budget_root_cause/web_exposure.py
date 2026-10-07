# Exposure sweep for test_asy_webserver_service.py: for each test_* function, the n-th wait_for()
# made by asy_webserver_service.py blocks the whole interpreter D ms before (pre) or after (post)
# its deadline is fixed, for every n the clean run makes (capped). A FAIL here is a verdict flip.
# Usage (cwd = worktree): micropython -X heapsize=16M web_exposure.py <test_file> <D_ms> <nmax> [substr] [gc_threshold]
import gc
import sys
import time

import asyncio as _real_asyncio

import asy_webserver_service

TEST_FILE, D_MS, NMAX = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
SUBSTR = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != "-" else ""
if len(sys.argv) > 5:
    gc.threshold(int(sys.argv[5]))

ST = {"n": 0, "target": -1, "mode": "pre", "on": False}


class _Shim:
    def __init__(self) -> None:
        for name in dir(_real_asyncio):
            if not name.startswith("__") and name != "wait_for":
                setattr(self, name, getattr(_real_asyncio, name))

    def wait_for(self, aw, timeout):  # noqa: ANN001,ANN201
        if not ST["on"]:
            return _real_asyncio.wait_for(aw, timeout)
        ST["n"] += 1
        hit = ST["n"] == ST["target"]
        if hit and ST["mode"] == "pre":
            time.sleep_ms(D_MS)
        if not (hit and ST["mode"] == "post"):
            return _real_asyncio.wait_for(aw, timeout)

        async def sleep(t):  # noqa: ANN001,ANN202
            gen = _real_asyncio.sleep(t)  # deadline fixed here
            time.sleep_ms(D_MS)
            await gen

        return _real_asyncio.wait_for(aw, timeout, sleep)


SHIM = _Shim()
asy_webserver_service.asyncio = SHIM

ns = {"__name__": "web_exposure", "__file__": TEST_FILE}
with open(TEST_FILE) as f:
    exec(compile(f.read(), TEST_FILE, "exec"), ns)  # noqa: S102
# Only the tests listed in web_exposure_names.txt (fakes only, no real sockets - other suites bind ports).
with open(__file__.rsplit("/", 1)[0] + "/web_exposure_names.txt") as f:
    allowed = {line.strip() for line in f if line.strip()}
names = sorted(n for n, v in ns.items() if n in allowed and callable(v) and SUBSTR in n)


def attempt(fn, target, mode):  # noqa: ANN001,ANN201
    ST["n"] = 0
    ST["target"] = target
    ST["mode"] = mode
    ST["on"] = True
    asy_webserver_service.asyncio = SHIM  # a test may have swapped it (and restored the real one)
    t0 = time.ticks_ms()
    try:
        fn()
        verdict = None
    except Exception as e:  # noqa: BLE001
        verdict = "%s: %s" % (type(e).__name__, e)
    ST["on"] = False
    return verdict, ST["n"], time.ticks_diff(time.ticks_ms(), t0)


for name in names:
    fn = ns[name]
    verdict, count, ms = attempt(fn, -1, "pre")
    if verdict is not None:
        print("BASEFAIL %s %s" % (name, verdict[:160]))
        continue
    if count == 0:
        continue  # never reaches a webserver wait_for - nothing to race
    if ms > 4000:
        print("SKIPLONG %s clean=%dms calls=%d" % (name, ms, count))
        continue
    flips = []
    for n in range(1, min(count, NMAX) + 1):
        for mode in ("pre", "post"):
            v, _, _ = attempt(fn, n, mode)
            if v is not None:
                flips.append("%s#%d" % (mode, n))
                first = v[:160]
    if flips:
        print("FLIP %s %d/%d %s first=%s" % (name, len(flips), 2 * min(count, NMAX), flips, first))
    else:
        print("ok   %s 0/%d calls=%d clean=%dms" % (name, 2 * min(count, NMAX), count, ms))
sys.exit(0)
