# Fresh process per warm-up length: growth of the first 100-read batch after it, with the ring size.
import gc, sys
import test_asy_uart_driver as t
from machine import mem32
warm = int(sys.argv[1])
uart = t.make_uart()
buf = bytearray(8)
async def reads(n):
    async with uart:
        for _ in range(n):
            t.fake(uart).feed_rx(b"01234567")
            await uart.readinto_until_complete(buf, 8)
t.run(reads(warm))
for log in (t.fake(uart).log, mem32.log):
    while len(log) < log.maxlen:
        log.append(None)
for i in range(3):
    gc.collect(); b = gc.mem_alloc()
    t.run(reads(100))
    gc.collect(); print("warm", warm, "ring", uart._rx_ring_size, "batch", i, gc.mem_alloc() - b)
