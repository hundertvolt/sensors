# Diagnostic probe (scratch only): the EAGAIN spin round of tests/lwip_host/test_modlwip_eagain.py, repeated,
# with this process's own scheduler counters read around each round (outside its timed window).
import gc
import select
import sys
import time

import lwip
import test_modlwip_eagain as t

ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
THRESHOLD = int(sys.argv[2]) if len(sys.argv) > 2 else -1
gc.threshold(THRESHOLD)


_buf = bytearray(4096)


def raw():
    # One read of the counters, parsed later: the parse is not inside the window the deltas span.
    with open("/proc/self/sched", "rb") as f:
        n = f.readinto(_buf)
    return bytes(_buf[:n])


def sched(text):
    rt = 0.0
    inv = vol = 0
    if True:
        for line in text.decode().split("\n"):
            if line.startswith("se.sum_exec_runtime"):
                rt = float(line.split(":")[1])
            elif line.startswith("nr_involuntary_switches"):
                inv = int(line.split(":")[1])
            elif line.startswith("nr_voluntary_switches"):
                vol = int(line.split(":")[1])
    return rt, inv, vol


pair = t._open_pair()
client, _server = pair
client.setsockopt(lwip.IPPROTO_TCP, lwip.TCP_NODELAY, 1)
t._write_until_eagain(client, t._QUEUE_PIECE, pump=False)
poller = select.poll()
poller.register(client, select.POLLOUT)
for _ in poller.ipoll(0):
    pass
remaining = memoryview(t._MSS_PIECE)
hist = [0] * 8  # rounds by elapsed: <1 ms, <2, <5, <10, <20, <50, <100, >=100
bounds = (1000, 2000, 5000, 10000, 20000, 50000, 100000)
slow = []  # the 8 slowest rounds: (elapsed us, on-CPU us, involuntary, voluntary, collection)
inv_rounds = 0
max_on_cpu = 0.0
for _ in range(ROUNDS):
    r0 = raw()
    allocated = gc.mem_alloc()
    start = time.ticks_us()
    written = client.write(remaining[0:])
    writable = False
    for _, events in poller.ipoll(0):
        writable = bool(events & select.POLLOUT)
    el = time.ticks_diff(time.ticks_us(), start)
    grown = gc.mem_alloc() - allocated
    r1 = raw()
    s0, s1 = sched(r0), sched(r1)
    assert written is None and writable
    on_cpu = (s1[0] - s0[0]) * 1000.0
    i = 0
    while i < len(bounds) and el >= bounds[i]:
        i += 1
    hist[i] += 1
    inv_rounds += 1 if s1[1] > s0[1] else 0
    max_on_cpu = max(max_on_cpu, on_cpu)
    if len(slow) < 8 or el > slow[-1][0]:
        slow.append((el, int(on_cpu), s1[1] - s0[1], s1[2] - s0[2], grown < 0))
        slow.sort(key=lambda r: -r[0])
        del slow[8:]
print("rounds", ROUNDS, "threshold", THRESHOLD, "by elapsed <1ms,<2,<5,<10,<20,<50,<100,>=100:", hist)
for el, ex_us, inv, vol, col in slow:
    print("slow round", el, "us: on-CPU", ex_us, "us, involuntary", inv, "voluntary", vol, "collection", col)
print("rounds with an involuntary switch:", inv_rounds, "max on-CPU us of any round:", int(max_on_cpu))
t._close([pair], reset=True)
