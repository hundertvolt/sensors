# Warm-up until every capped fake log the reads write has wrapped once (or is untouched by a batch); then batches.
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
logs = (t.fake(uart).log, mem32.log)
rounds = 0
while True:
    before = [(len(l), l.dropped) for l in logs]
    t.run(reads(64)); rounds += 1
    if all(l.dropped >= l.maxlen or (len(l), l.dropped) == b for l, b in zip(logs, before)):
        break
print("warm rounds", rounds, [(len(l), l.dropped, l.maxlen) for l in logs])
for i in range(4):
    gc.collect(); b = gc.mem_alloc()
    t.run(reads(1000))
    gc.collect(); print("batch", i, gc.mem_alloc() - b)
