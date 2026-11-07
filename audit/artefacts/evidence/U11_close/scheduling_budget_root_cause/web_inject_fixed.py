# Same injection points as web_inject.py, for the FIXED test: the n-th wait_for() the webserver makes
# (now routed through the test's _VirtualClock) blocks the whole interpreter D ms either before its
# deadline is fixed (pre) or after its timer started (post). Also "everywhere": stall on every call.
# Usage (cwd = worktree): micropython -X heapsize=16M web_inject_fixed.py <test_file> <test_name> <pre|post|every> <n> <D_ms> [gc_threshold]
import gc
import sys
import time

TEST_FILE, TEST_NAME, MODE, N, D_MS = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
if len(sys.argv) > 6:
    gc.threshold(int(sys.argv[6]))

ns = {"__name__": "web_inject_fixed", "__file__": TEST_FILE}
with open(TEST_FILE) as f:
    exec(compile(f.read(), TEST_FILE, "exec"), ns)  # noqa: S102

Clock = ns["_VirtualClock"]
orig_wait_for = Clock.wait_for
orig_sleep = Clock.sleep
ST = {"n": 0, "armed_post": False}


def wait_for(self, aw, timeout):  # noqa: ANN001,ANN202
    ST["n"] += 1
    hit = MODE == "every" or ST["n"] == N
    if hit and MODE in ("pre", "every"):
        time.sleep_ms(D_MS)
    if hit and MODE in ("post", "every"):
        ST["armed_post"] = True
    return orig_wait_for(self, aw, timeout)


async def sleep(self, t):  # noqa: ANN001,ANN202
    if ST["armed_post"]:
        ST["armed_post"] = False
        deadline_fixed = orig_sleep(self, t)  # the coroutine computes its deadline on first resume
        time.sleep_ms(D_MS)
        await deadline_fixed
        return
    await orig_sleep(self, t)


Clock.wait_for = wait_for
Clock.sleep = sleep

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
import asyncio  # noqa: E402

entry = asyncio.run(built[0].get_error_counter())["WEBSERVER"] if built else None
print("mode=%s n=%d D=%d calls=%d -> %s   ErrNum=%r ErrCount=%r" % (MODE, N, D_MS, ST["n"], verdict, entry["ErrNum"][-3:] if entry else None, entry["ErrCount"] if entry else None))
sys.exit(0)
