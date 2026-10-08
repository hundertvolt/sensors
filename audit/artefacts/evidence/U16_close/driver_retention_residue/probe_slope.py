# Heap delta per run for reads(n) and control(n) at two lengths, alternating, after the wrap-once warm-up.
import gc
import test_asy_uart_driver as t
from machine import mem32
uart = t.make_uart()
buf = bytearray(8)
async def reads(n):
    async with uart:
        for _ in range(n):
            t.fake(uart).feed_rx(b"01234567")
            await uart.readinto_until_complete(buf, 8)
async def noop():
    return
async def control(n):
    for _ in range(n):
        await noop()
for _ in range(4):
    t.run(reads(64))
def g(f, n):
    gc.collect(); b = gc.mem_alloc(); t.run(f(n)); gc.collect(); return gc.mem_alloc() - b
out = []
for k in range(5):
    out.append(("r1000", g(reads, 1000), "r2000", g(reads, 2000), "c1000", g(control, 1000), "c2000", g(control, 2000)))
for o in out: print(o)
