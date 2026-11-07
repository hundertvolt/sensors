# Scratch calibration runner (lane S, not in the repo): runs the hammer's seven tests with every write,
# handshake and capacity recovery timed, and prints the maxima the l1.lwip_host_* values are set from.
import gc
import sys
import time

if len(sys.argv) > 1:
    gc.threshold(int(sys.argv[1]))  # the (f) stage, as tests/_threshold_runner.py sets it

ns = {"__name__": "calibration"}
exec(open("tests/lwip_host/test_modlwip_eagain.py").read(), ns)
stats = {"write_ms": 0, "connect_ms": 0, "recover_ms": 0, "writes": 0, "pairs": 0}
real_write, real_open, real_recovered = ns["_timed_write"], ns["_open_pair"], ns["_recovered"]


def timed_write(sock, piece):
    start = time.ticks_us()
    out = real_write(sock, piece)
    stats["write_ms"] = max(stats["write_ms"], time.ticks_diff(time.ticks_us(), start) / 1000)
    stats["writes"] += 1
    return out


def open_pair():
    start = time.ticks_us()
    out = real_open()
    if out is not None:
        stats["connect_ms"] = max(stats["connect_ms"], time.ticks_diff(time.ticks_us(), start) / 1000)
        stats["pairs"] += 1
    return out


def recovered(reference):
    start = time.ticks_us()
    out = real_recovered(reference)
    stats["recover_ms"] = max(stats["recover_ms"], time.ticks_diff(time.ticks_us(), start) / 1000)
    return out


ns["_timed_write"], ns["_open_pair"], ns["_recovered"] = timed_write, open_pair, recovered
for name in sorted(k for k in ns if k.startswith("test_")):
    start = time.ticks_ms()
    ns[name]()
    print("%-70s %6d ms" % (name, time.ticks_diff(time.ticks_ms(), start)))
print("slowest write %.2f ms over %d writes; slowest handshake %.2f ms over %d pairs; slowest recovery %.1f ms" % (stats["write_ms"], stats["writes"], stats["connect_ms"], stats["pairs"], stats["recover_ms"]))
