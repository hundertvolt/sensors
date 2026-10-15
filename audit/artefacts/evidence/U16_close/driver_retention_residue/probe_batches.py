# Fresh process: heap growth per batch of driver reads after a 10-read warm-up and filled fake logs.
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
t.run(reads(10))
for log in (t.fake(uart).log, mem32.log):
    while len(log) < log.maxlen:
        log.append(None)
for i in range(12):
    gc.collect(); b = gc.mem_alloc()
    t.run(reads(100))
    gc.collect(); print("batch", i, gc.mem_alloc() - b, "rxq", len(t.fake(uart).rx_queue), "loglen", len(t.fake(uart).log))
async def noop():
    return
async def control(n):
    for _ in range(n):
        await noop()
for i in range(4):
    gc.collect(); b = gc.mem_alloc()
    t.run(control(100))
    gc.collect(); print("control", i, gc.mem_alloc() - b)
for n in (100, 1000):
    for i in range(3):
        gc.collect(); b = gc.mem_alloc()
        t.run(reads(n))
        gc.collect(); print("reads", n, i, gc.mem_alloc() - b)
