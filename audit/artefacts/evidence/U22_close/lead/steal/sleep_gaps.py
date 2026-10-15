"""sleep_gaps.py <seconds>: repeat a 1 ms sleep and record each overshoot, with this thread's guest run-queue wait
(/proc/thread-self/schedstat) read around each sleep, and the host's steal ticks (/proc/stat) across the window."""
import sys, time

def run_delay():
    with open("/proc/thread-self/schedstat") as f:
        return int(f.read().split()[1])

def steal():
    with open("/proc/stat") as f:
        return sum(int(line.split()[8]) for line in f if line.startswith("cpu") and line[3] != " ")

secs = float(sys.argv[1])
s0 = steal()
hist = [0] * 7  # overshoot <0.5ms, <1, <5, <10, <20, <50, >=50
worst = []  # (overshoot_ns, run_delay_ns) for overshoots >= 5 ms
end = time.monotonic() + secs
n = 0
while time.monotonic() < end:
    d0 = run_delay()
    t0 = time.perf_counter_ns()
    time.sleep(0.001)
    t1 = time.perf_counter_ns()
    d1 = run_delay()
    over = t1 - t0 - 1_000_000
    n += 1
    k = 0 if over < 5e5 else 1 if over < 1e6 else 2 if over < 5e6 else 3 if over < 10e6 else 4 if over < 20e6 else 5 if over < 50e6 else 6
    hist[k] += 1
    if over >= 5_000_000:
        worst.append((over, d1 - d0))
print(f"window {secs} s, {n} sleeps of 1 ms; overshoot <0.5,<1,<5,<10,<20,<50,>=50 ms: {hist}")
print(f"steal over the window, all cpus: {steal() - s0} ticks of 10 ms")
for over, rd in sorted(worst, reverse=True)[:15]:
    print(f"overshoot {over / 1e6:.2f} ms: guest run-queue wait in it {rd / 1e6:.2f} ms")
