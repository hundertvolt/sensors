"""spin_gaps.py <seconds>: spin on one CPU and record each gap between consecutive clock reads, with this
thread's guest run-queue wait (/proc/self/schedstat) and the host's steal ticks (/proc/stat) across the window."""
import sys, time

def schedstat():
    with open("/proc/thread-self/schedstat") as f:
        on_cpu, run_delay, _ = (int(x) for x in f.read().split())
    return on_cpu, run_delay

def steal():
    out = {}
    with open("/proc/stat") as f:
        for line in f:
            if line.startswith("cpu"):
                p = line.split()
                out[p[0]] = int(p[8])  # steal, in USER_HZ ticks
    return out

secs = float(sys.argv[1])
st0, (c0, d0) = steal(), schedstat()
gaps = []  # (gap_ns, run_delay grown in the gap, on_cpu grown in the gap) for gaps >= 5 ms
hist = [0] * 6  # <1ms, <5, <10, <20, <50, >=50
end = time.perf_counter_ns() + int(secs * 1e9)
prev = time.perf_counter_ns()
pc, pd = c0, d0
n = 0
while prev < end:
    now = time.perf_counter_ns()
    g = now - prev
    n += 1
    if g >= 1_000_000:
        c, d = schedstat()
        k = 1 if g < 5e6 else 2 if g < 10e6 else 3 if g < 20e6 else 4 if g < 50e6 else 5
        hist[k] += 1
        if g >= 5_000_000:
            gaps.append((g, d - pd, c - pc))
        pc, pd = c, d
        now = time.perf_counter_ns()
    else:
        hist[0] += 1
    prev = now
st1, (c1, d1) = steal(), schedstat()
print(f"window {secs} s, {n} reads; gaps <1ms,<5,<10,<20,<50,>=50 ms: {hist}")
print(f"this thread: on-CPU {(c1 - c0) / 1e6:.1f} ms, guest run-queue wait {(d1 - d0) / 1e6:.1f} ms")
print("steal ticks (USER_HZ) per cpu over the window: " + ", ".join(f"{k} {st1[k] - st0[k]}" for k in sorted(st1)))
for g, dd, cc in sorted(gaps, reverse=True)[:15]:
    print(f"gap {g / 1e6:.2f} ms: guest run-queue wait in it ~{dd / 1e6:.2f} ms (since the previous >=1 ms gap), on-CPU {cc / 1e6:.2f} ms")
