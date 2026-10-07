# Plants ONE whole-interpreter stall of D ms inside the measured window of one hammer/retention body of
# tests/test_uart_comm_hazard.py, right after the k-th asyncio.sleep_ms() the UART modules make once that
# window has opened (the deadline is already computed, so the parked task wakes overdue: a host preemption).
# Usage (cwd = worktree, MICROPYPATH as scripts/test.sh, with the file under test's directory first):
#   micropython -X heapsize=16M repro_stall.py <body: faulted|clean|retention> <crc: nocrc|crc16> <gc_threshold> <D_ms> <k_list|sweep:start:stop:step|every:k:period,...|count> [show]
import gc
import sys
import time

import asyncio as _real_asyncio

import asy_uart_comm
import asy_uart_driver
import test_uart_comm_hazard as T
from asy_crc_checks import CRC16
from asy_uart_comm import UARTComm

BODY, CRCNAME, THRESH, D_MS, KSPEC = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
CRC = None if CRCNAME == "nocrc" else CRC16
if len(sys.argv) > 6 and sys.argv[6] == "show":  # report every figure: no measured value passes a negative bound
    T._RETENTION_PER_FAILURE_MAX_BYTES = T._RETENTION_PER_TRANSACTION_MAX_BYTES = -1.0
ST = {"period": 0, "k_end": -1, "k": 0, "target": -1, "window": False, "scrubs": 0, "stalled": 0, "opened_at": -1}

# Where the measured window opens, in calls of the body's own per-transaction _scrub():
# faulted: 30 warm-up failures; clean: sample taken after round _HAMMER_SAMPLE_AT; retention: 20 warm-up rounds.
OPEN_AFTER = {"faulted": 30, "clean": T._HAMMER_SAMPLE_AT + 1, "retention": T._WARMUP}[BODY]
CLOSE_AT = {"faulted": 60, "clean": T._HAMMER_ROUNDS, "retention": T._WARMUP + T._MEASURED}[BODY]


class _Shim:
    def __init__(self) -> None:
        for name in ("sleep", "get_event_loop", "create_task", "wait_for", "TimeoutError", "CancelledError", "Event", "Lock", "current_task", "gather"):
            if hasattr(_real_asyncio, name):
                setattr(self, name, getattr(_real_asyncio, name))

    def sleep_ms(self, t):  # noqa: ANN001,ANN201
        gen = _real_asyncio.sleep_ms(t)
        if ST["window"]:
            ST["k"] += 1
            if ST["k"] == ST["target"] or (ST["period"] and ST["k"] > ST["target"] > 0 and (ST["k"] - ST["target"]) % ST["period"] == 0 and (ST["k_end"] < 0)):
                time.sleep_ms(D_MS)
                ST["stalled"] += 1
        return gen


SHIM = _Shim()
asy_uart_driver.asyncio = SHIM
asy_uart_comm.asyncio = SHIM

_real_scrub = T._scrub


def _scrub(pair):  # noqa: ANN001,ANN202
    _real_scrub(pair)
    ST["scrubs"] += 1
    if ST["scrubs"] == OPEN_AFTER:
        ST["window"] = True
    if ST["scrubs"] == CLOSE_AT:
        ST["k_end"] = ST["k"]


T._scrub = _scrub
FAILS = [0, 0]  # failed initiator calls inside the measured window: uart_get, uart_set
_real_get, _real_set = UARTComm.uart_get, UARTComm.uart_set


async def _get(self, *a, **k):  # noqa: ANN001,ANN002,ANN003,ANN202
    r = await _real_get(self, *a, **k)
    if r is None and ST["window"] and ST["k_end"] < 0:
        FAILS[0] += 1
    return r


async def _set(self, *a, **k):  # noqa: ANN001,ANN002,ANN003,ANN202
    r = await _real_set(self, *a, **k)
    if not r and ST["window"] and ST["k_end"] < 0:
        FAILS[1] += 1
    return r


RESP = [0, 0, 0]  # responder: failed listens inside the window, listens failed after it closed, errnos logged at close
_real_listen = UARTComm.uart_listen


async def _listen(self):  # noqa: ANN001,ANN202
    r = await _real_listen(self)
    if r.cmd_id is None and ST["window"]:
        RESP[0 if ST["k_end"] < 0 else 1] += 1
    return r


UARTComm.uart_listen = _listen
UARTComm.uart_get = _get
UARTComm.uart_set = _set
BODIES = {"faulted": T._hammer_faulted, "clean": T._hammer_clean, "retention": T._check_a_long_run_of_transactions_retains_no_memory}


def attempt(target: int) -> "tuple[str, int]":
    FAILS[0] = FAILS[1] = 0
    RESP[0] = RESP[1] = 0
    ST.update(k_end=-1, k=0, target=target, window=False, scrubs=0, stalled=0)
    original = gc.threshold()
    gc.threshold(THRESH)
    t0 = time.ticks_ms()
    try:
        BODIES[BODY](CRC)
        verdict = "pass"
    except Exception as e:  # noqa: BLE001
        verdict = "FAIL %s: %s" % (type(e).__name__, e)
    finally:
        gc.threshold(original)
    return verdict, time.ticks_diff(time.ticks_ms(), t0)


if KSPEC == "count":
    v, ms = attempt(-1)
    print("clean run: %s, %d sleeps inside the measured window (of %d after it opened), %d failed calls in it, %d ms" % (v, ST["k_end"], ST["k"], FAILS[0] + FAILS[1], ms))
else:
    if KSPEC.startswith("sweep:"):
        a, b, s = (int(x) for x in KSPEC[6:].split(":"))
        ks = list(range(a, b, s))
    elif KSPEC.startswith("every:"):  # every:<first k>:<period>[,<first k>:<period>...]: a stall every period sleeps to the window's end
        ks = [tuple(int(x) for x in part.split(":")) for part in KSPEC[6:].split(",")]
    else:
        ks = [int(x) for x in KSPEC.split(",")]
    for k in ks:
        if isinstance(k, tuple):
            ST["period"] = k[1]
            k = k[0]
        v, ms = attempt(k)
        print("%s k=%d D=%d stalled=%d window_sleeps=%d window_failed_calls=%d responder_failed_listens=%d+%d %dms: %s" % ("FLIP" if v != "pass" else "ok  ", k, D_MS, ST["stalled"], ST["k_end"], FAILS[0] + FAILS[1], RESP[0], RESP[1], ms, v))
sys.exit(0)
