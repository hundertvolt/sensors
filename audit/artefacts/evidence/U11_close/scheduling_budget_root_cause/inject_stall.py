# Deterministic in-process stall injection for test_uart_comm_hazard's size-mismatch check.
# Usage (cwd = worktree, MICROPYPATH as scripts/test.sh):
#   micropython -X heapsize=16M inject_stall.py <gc_threshold> <mode> <D_ms> <k_list|sweep> [variant]
# mode: post = block the whole interpreter D ms right AFTER the k-th asyncio.sleep_ms() call has
#   computed its deadline (the task is parked, then the process is "descheduled" - the realistic
#   host-preemption model); pre = block BEFORE the deadline is computed.
# variant: orig (the test as committed) | fixed (the proposed structure) | planted (fixed + planted defect)
import gc
import sys
import time

import asyncio as _real_asyncio

import asy_uart_comm
import asy_uart_driver
import test_uart_comm_hazard as T
from _uart_comm_harness import Pair, accept_set, echo_get, run

THRESH = int(sys.argv[1])
MODE = sys.argv[2]
D_MS = int(sys.argv[3])
KSPEC = sys.argv[4]
VARIANT = sys.argv[5] if len(sys.argv) > 5 else "orig"
gc.threshold(THRESH)

ST = {"k": 0, "target": -1, "listener": None, "trace": [], "on": False, "phase": None, "rf": 0, "arm": False}


def _who() -> str:
    try:
        t = _real_asyncio.current_task()
    except Exception:
        return "?"
    return "R" if t is ST["listener"] else "I"


class _Shim:
    # Stands in for the `asyncio` module inside asy_uart_driver / asy_uart_comm only.
    def __init__(self) -> None:
        for name in ("sleep", "get_event_loop", "create_task", "wait_for", "TimeoutError", "CancelledError", "Event", "Lock", "current_task", "gather"):
            if hasattr(_real_asyncio, name):
                setattr(self, name, getattr(_real_asyncio, name))

    def sleep_ms(self, t):  # noqa: ANN001,ANN201
        if not ST["on"]:
            return _real_asyncio.sleep_ms(t)
        ST["k"] += 1
        k = ST["k"]
        ST["trace"].append(("sleep", k, _who(), t, time.ticks_ms()))
        if ST["arm"] and _who() == "I":
            ST["arm"] = False
            ST["target"] = k
        if k == ST["target"] and MODE == "pre":
            time.sleep_ms(D_MS)
            ST["trace"].append(("STALL", k, D_MS))
        gen = _real_asyncio.sleep_ms(t)
        if k == ST["target"] and MODE == "post":
            time.sleep_ms(D_MS)
            ST["trace"].append(("STALL", k, D_MS))
        return gen


SHIM = _Shim()
asy_uart_driver.asyncio = SHIM
asy_uart_comm.asyncio = SHIM


def _wrap_ready(drv, tag):  # noqa: ANN001,ANN202
    orig = drv.ready

    async def ready(mask, timeout_ms=-1):  # noqa: ANN001,ANN202
        t0 = time.ticks_ms()
        ok = await orig(mask, timeout_ms=timeout_ms)
        if ST["on"]:
            ST["trace"].append(("ready", tag, "IN" if mask & 1 else "OUT", timeout_ms, ok, time.ticks_diff(time.ticks_ms(), t0)))
        return ok

    drv.ready = ready


def _wrap_writes(fake, tag):  # noqa: ANN001,ANN202
    orig = fake.write

    def write(buf):  # noqa: ANN001,ANN202
        n = orig(buf)
        if ST["on"]:
            b = bytes(buf)
            ST["trace"].append(("wire", tag, "cmd=%d size=%d chunks=%d cur=%d uid=%d" % (b[1], b[2], b[3], b[4], b[0]), time.ticks_ms()))
        return n

    fake.write = write


def build() -> Pair:
    pair = Pair(payload_size=T._PAYLOAD, timeout=T._TIMEOUT_MS, get_callback=echo_get(b"vv"), set_callback=accept_set())
    assert run(pair.setup()) is True
    _wrap_ready(pair.driver_a, "I")
    _wrap_ready(pair.driver_b, "R")
    _wrap_writes(pair.fake_a, "I->")
    _wrap_writes(pair.fake_b, "R->")
    orig_listen = pair._listen_rounds

    async def listen_rounds(rounds):  # noqa: ANN001,ANN202
        ST["listener"] = _real_asyncio.current_task()
        await orig_listen(rounds)

    pair._listen_rounds = listen_rounds
    orig_rf = pair.initiator._read_frame

    async def read_frame(device, timeout_ms):  # noqa: ANN001,ANN202
        ST["rf"] += 1
        if ST["on"]:
            ST["trace"].append(("I._read_frame#%d" % ST["rf"], time.ticks_ms()))
        if ST["on"] and ST["phase"] == ST["rf"]:
            ST["arm"] = True
        return await orig_rf(device, timeout_ms)

    pair.initiator._read_frame = read_frame
    return pair


def one(k: int, verbose: bool) -> "tuple[object, list[int], list[int]]":
    ST["k"] = 0
    ST["rf"] = 0
    ST["arm"] = False
    ST["target"] = -1 if PHASE else k
    ST["phase"] = k if PHASE else None
    ST["trace"] = []
    pair = build()
    ST["on"] = True
    if VARIANT == "orig":
        result = run(pair.with_listener(pair.initiator.uart_get(0x01, exp_size=5)), limit=T._LIMIT_S)
    else:
        import fixed_variant  # noqa: PLC0415
        result = fixed_variant.exchange(pair, planted=VARIANT == "planted")
    ST["on"] = False
    ei = T.errnos(pair.initiator)
    er = T.errnos(pair.responder)
    if verbose:
        for row in ST["trace"]:
            print("   ", row)
    return result, ei, er


PHASE = KSPEC.startswith("phase:")
if PHASE:
    KSPEC = KSPEC[len("phase:"):]
SIZE_MISMATCH = T.code("E", "UART_SIZE_MISMATCH")

if KSPEC == "count":
    r, ei, er = one(-1, True)
    print("clean: sleeps=%d result=%r initiator=%r responder=%r" % (ST["k"], r, ei, er))
elif KSPEC == "sweep":
    r, ei, er = one(-1, False)
    n = ST["k"]
    print("clean run: %d sleep_ms calls, result=%r initiator=%r responder=%r" % (n, r, ei, er))
    for k in range(1, n + 1):
        r, ei, er = one(k, False)
        last = ei[-1] if ei else 0
        flag = "ok  " if (r is None and last == SIZE_MISMATCH) else "FLIP"
        print("%s k=%2d D=%d result=%r initiator=%r responder=%r" % (flag, k, D_MS, r, ei, er))
else:
    for k in [int(x) for x in KSPEC.split(",")]:
        r, ei, er = one(k, True)
        last = ei[-1] if ei else 0
        flag = "ok  " if (r is None and last == SIZE_MISMATCH) else "FLIP"
        print("%s k=%2d D=%d result=%r initiator=%r responder=%r" % (flag, k, D_MS, r, ei, er))
sys.exit(0)
