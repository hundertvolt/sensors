import time
def _cpu():
    f = open("/proc/self/stat"); st = f.read().split(); f.close()
    f = open("/proc/self/status"); nv = [l for l in f.read().split("\n") if l.startswith("nonvoluntary")][0].split()[1]; f.close()
    return int(st[13]) + int(st[14]), int(nv)
a = _cpu(); t = time.ticks_ms()
while time.ticks_diff(time.ticks_ms(), t) < 300: pass
b = _cpu(); time.sleep_ms(300); c = _cpu()
print("busy 300ms ->", b[0] - a[0], "ticks; sleep 300ms ->", c[0] - b[0], "ticks; nvcsw", c[1])
