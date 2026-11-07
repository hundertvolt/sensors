# Probe for test_a_maximum_length_train_completes_and_still_yields: runs only that test (REPEATS times),
# recording every bounded ready() wait, every protocol fault and the ticker's largest gap. Optional stall
# injection: time.sleep_ms(D) once, right after the k-th bounded-wait poll sleep of the given role's UART
# (`init` = uart0 or `resp` = uart1), standing in for one host deschedule. Code under test is unchanged.
# argv (after runner's own two): REPEATS [ROLE K D]
import sys
import time
import asyncio
ARGS = sys.argv[3:]
REPEATS = int(ARGS[0]) if ARGS else 1
ROLE = ARGS[1] if len(ARGS) > 1 else ""
K = int(ARGS[2]) if len(ARGS) > 2 else 0
D = int(ARGS[3]) if len(ARGS) > 3 else 0
import os
TEST = os.getenv("UART_TEST") or "tests/test_digital_twin_uart_link.py"
ns = {"__name__": "not_main", "__file__": TEST}
exec(compile(open(TEST).read(), TEST, "exec"), ns)
import asy_uart_driver
import asy_uart_comm
import sensortask_dev

waits = []
faults = []
polls = {"init": 0, "resp": 0}
active = [False]
orig_ready = asy_uart_driver.UART.ready

def role_of(u):
    return "init" if u is sensortask_dev.uart0 else "resp"

real_sleep_ms = asyncio.sleep_ms
cur = [None]

import gc
long_waits = []
async def ready(self, mask, timeout_ms=-1):
    t0 = time.ticks_ms()
    f0 = gc.mem_free()
    r = await orig_ready(self, mask, timeout_ms)
    if active[0] and timeout_ms > 0:
        ms = time.ticks_diff(time.ticks_ms(), t0)
        waits.append((role_of(self), timeout_ms, ms, r))
        if ms > 100:
            long_waits.append((role_of(self), ms, r, "mem_free before/after", f0, gc.mem_free(), "chunk", chunk[0], "t_since_set", None if set_t0[0] is None else time.ticks_diff(time.ticks_ms(), set_t0[0])))
    return r
asy_uart_driver.UART.ready = ready

# stall injection through the driver module's asyncio namespace: count poll sleeps (non-zero) per role
class Shim:
    pass
shim = Shim()
for k in dir(asyncio):
    if not k.startswith("__"):
        setattr(shim, k, getattr(asyncio, k))
stalled = [False]
async def sleep_ms(ms):
    await real_sleep_ms(ms)
    if active[0] and ms > 0 and cur[0] is not None:
        polls[cur[0]] += 1
        if ROLE == cur[0] and polls[cur[0]] == K and not stalled[0]:
            stalled[0] = True
            faults.append(("STALL", cur[0], K, D))
            time.sleep_ms(D)
shim.sleep_ms = sleep_ms
asy_uart_driver.asyncio = shim
# which role is polling: set inside the wrapped ready (the only bounded poll sleeper we count)
_inner_ready = asy_uart_driver.UART.ready
async def ready_role(self, mask, timeout_ms=-1):
    prev = cur[0]
    cur[0] = role_of(self) if timeout_ms > 0 else None
    try:
        return await _inner_ready(self, mask, timeout_ms)
    finally:
        cur[0] = prev
asy_uart_driver.UART.ready = ready_role

orig_fault = asy_uart_comm.UARTComm._fault
async def fault(self, device, errno, *args):
    faults.append((self.name, errno, args, time.ticks_ms()))
    await orig_fault(self, device, errno, *args)
asy_uart_comm.UARTComm._fault = fault

chunk = [0]
set_t0 = [None]
orig_wfa = asy_uart_comm.UARTComm._write_frame_with_ack
async def wfa(self, device, cmd, chunks, cur_chunk, data, size):
    chunk[0] = cur_chunk
    return await orig_wfa(self, device, cmd, chunks, cur_chunk, data, size)
asy_uart_comm.UARTComm._write_frame_with_ack = wfa
orig_set = asy_uart_comm.UARTComm.uart_set
async def uart_set(self, set_id, payload=None):
    if "GCFIRST" in ARGS:
        gc.collect()  # diagnosis only: does a clean heap remove the early-chunk slowness?
    set_t0[0] = time.ticks_ms()
    long_waits.append(("uart_set start", "mem_free", gc.mem_free()))
    try:
        return await orig_set(self, set_id, payload)
    finally:
        long_waits.append(("uart_set end", time.ticks_diff(time.ticks_ms(), set_t0[0]), "ms"))
asy_uart_comm.UARTComm.uart_set = uart_set
slow_steps = []
import machine as _tm
def _timed(cls, name):
    orig = getattr(cls, name)
    def w(*a, **k):
        t = time.ticks_us()
        r = orig(*a, **k)
        d = time.ticks_diff(time.ticks_us(), t)
        if d > 30000 and set_t0[0] is not None:
            slow_steps.append((cls.__name__ + "." + name, d // 1000, "ms at", time.ticks_diff(time.ticks_ms(), set_t0[0]), "chunk", chunk[0]))
        return r
    setattr(cls, name, w)
for _c, _n in ((_tm.UARTLink, "transmit"), (_tm.UARTLink, "_advance"), (asy_uart_driver.UART, "_rx_copy"), (asy_uart_driver.UART, "_rx_level"), (asy_uart_driver.UART, "_buffered")):
    if hasattr(_c, _n):
        _timed(_c, _n)
tick_log = []
class TimeShim:
    pass
tshim = TimeShim()
for k in dir(time):
    if not k.startswith("__"):
        setattr(tshim, k, getattr(time, k))
def ticks_ms_rec():
    t = time.ticks_ms()
    tick_log.append(t)
    return t
tshim.ticks_ms = ticks_ms_rec
ns["time"] = tshim  # only the test module's own uses (its ticker) go through this
test = ns["test_a_maximum_length_train_completes_and_still_yields"]
fails = 0
for rep in range(REPEATS):
    set_t0[0] = None; waits.clear(); faults.clear(); polls["init"] = polls["resp"] = 0; stalled[0] = False
    t0 = time.ticks_ms()
    active[0] = True
    try:
        test()
        res = "PASS"
    except AssertionError as e:
        res = "FAIL " + str(e); fails += 1
    active[0] = False
    el = time.ticks_diff(time.ticks_ms(), t0)
    by = {}
    for role, tmo, ms, ok in waits:
        b = by.setdefault(role, [0, 0, 0, 0])
        b[0] += 1; b[1] = max(b[1], ms); b[3] += 0 if ok else 1
        if ms > 100: b[2] += 1
    print("rep", rep, res, "elapsed_ms", el, "polls", polls, "bounded waits role:[n,max_ms,n>100ms,n_false]", by)
    for f in faults:
        print("   fault", f)
    if tick_log and set_t0[0] is not None:
        gaps = sorted(((time.ticks_diff(tick_log[i], tick_log[i - 1]), time.ticks_diff(tick_log[i - 1], set_t0[0])) for i in range(1, len(tick_log))), reverse=True)
        print("   ticker: n", len(tick_log), "top gaps (gap_ms, at_ms_since_set):", gaps[:12])
    tick_log.clear()
    for x in slow_steps:
        print("   slowstep", x)
    slow_steps.clear()
    for w in long_waits:
        print("   long", w)
    long_waits.clear()
    if res != "PASS":
        for w in waits[-12:]:
            print("   lastwait", w)
print("test file", TEST)
print("fails", fails, "/", REPEATS)
