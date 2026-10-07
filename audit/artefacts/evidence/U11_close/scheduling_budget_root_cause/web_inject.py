# In-process stall injection for test_asy_webserver_service.py's read-timeout-then-capped-400 test.
# Every asyncio.wait_for() asy_webserver_service.py makes goes through a shim; on the n-th call the
# whole interpreter blocks D ms, either BEFORE that wait_for's timer deadline is computed (pre) or
# right AFTER it (post) - a host preemption at that exact point, nothing else changed.
# Usage (cwd = worktree): micropython -X heapsize=16M web_inject.py <test_file> <test_name> <mode> <n> <D_ms> [gc_threshold]
import gc
import sys
import time

import asyncio as _real_asyncio

import asy_webserver_service

TEST_FILE, TEST_NAME, MODE, N, D_MS = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
if len(sys.argv) > 6:
    gc.threshold(int(sys.argv[6]))

ST = {"n": 0, "trace": [], "t0": None}


def _stamp(*what) -> None:  # noqa: ANN002
    if ST["t0"] is None:
        ST["t0"] = time.ticks_ms()
    ST["trace"].append((time.ticks_diff(time.ticks_ms(), ST["t0"]),) + what)


class _Shim:
    def __init__(self) -> None:
        for name in dir(_real_asyncio):
            if not name.startswith("__") and name != "wait_for":
                setattr(self, name, getattr(_real_asyncio, name))

    def wait_for(self, aw, timeout):  # noqa: ANN001,ANN201
        ST["n"] += 1
        n = ST["n"]
        _stamp("wait_for#%d" % n, timeout)

        async def sleep(t):  # noqa: ANN001,ANN202
            if n == N and MODE == "pre":
                time.sleep_ms(D_MS)
                _stamp("STALL pre", n, D_MS)
            gen = _real_asyncio.sleep(t)  # the deadline is fixed here
            if n == N and MODE == "post":
                time.sleep_ms(D_MS)
                _stamp("STALL post", n, D_MS)
            await gen

        async def traced():  # noqa: ANN202
            try:
                r = await _real_asyncio.wait_for(aw, timeout, sleep)
            except BaseException as e:
                _stamp("wait_for#%d ->" % n, type(e).__name__)
                raise
            _stamp("wait_for#%d -> ok" % n)
            return r

        return traced()


asy_webserver_service.asyncio = _Shim()

ns = {"__name__": "web_inject", "__file__": TEST_FILE}
with open(TEST_FILE) as f:
    exec(compile(f.read(), TEST_FILE, "exec"), ns)  # noqa: S102

# Capture the service the test builds, so its full history can be printed whatever the verdict.
_orig_make = ns["_make_service"]
built = []


def _make_service(**kw):  # noqa: ANN003,ANN202
    s = _orig_make(**kw)
    built.append(s[0])
    return s


ns["_make_service"] = _make_service
try:
    ns[TEST_NAME]()
    verdict = "PASS"
except Exception as e:  # noqa: BLE001
    verdict = "FAIL %s: %s" % (type(e).__name__, e)
entry = _real_asyncio.run(built[0].get_error_counter())["WEBSERVER"] if built else None
print("mode=%s n=%d D=%d -> %s" % (MODE, N, D_MS, verdict))
print("   ErrNum=%r ErrType=%r ErrCount=%r" % (entry["ErrNum"], entry["ErrType"], entry["ErrCount"]) if entry else "   no service")
for row in ST["trace"]:
    print("   ", row)
sys.exit(0)
