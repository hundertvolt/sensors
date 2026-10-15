# usage: micropython inject_i2c_poll_stall.py <test_file> <name_substring> <k> <D_ms>
# Runs the matching test_* functions with one host-stall stand-in: time.sleep_ms(D) right after the k-th
# asyncio.sleep_ms() the asy_i2c_driver module makes (its SCL-release polls). k=0: no stall (control).
import sys
import time
import asyncio
import asy_i2c_driver as drv
test_file, sub, K, D = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
real = drv.asyncio
n = [0]
class Shim:
    Lock = real.Lock
    sleep = staticmethod(real.sleep)
    @staticmethod
    async def sleep_ms(ms):
        await real.sleep_ms(ms)
        n[0] += 1
        if n[0] == K:
            time.sleep_ms(D)
drv.asyncio = Shim()
ns = {"__name__": "not_main", "__file__": test_file}
exec(compile(open(test_file).read(), test_file, "exec"), ns)
for name in sorted(k for k in ns if k.startswith("test_") and sub in k):
    n[0] = 0
    try:
        ns[name]()
        print("PASS", name, "polls", n[0], "k", K, "D", D)
    except AssertionError as e:
        print("FAIL", name, "polls", n[0], "k", K, "D", D, repr(e)[:160])
