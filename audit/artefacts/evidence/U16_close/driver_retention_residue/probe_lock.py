# Is the per-run extra the driver's lock section? n lock sections inside ONE asyncio.run.
import gc
import test_asy_uart_driver as t
uart = t.make_uart()
buf = bytearray(8)
async def locked(n):
    for _ in range(n):
        async with uart:
            t.fake(uart).feed_rx(b"01234567")
            await uart.readinto_until_complete(buf, 8)
async def bare_run(n):
    for _ in range(n):
        await t.asyncio.sleep_ms(0)
for _ in range(3):
    t.run(locked(64))
def g(f, n):
    gc.collect(); b = gc.mem_alloc(); t.run(f(n)); gc.collect(); return gc.mem_alloc() - b
for k in range(3):
    print("locked 10", g(locked, 10), "locked 1000", g(locked, 1000), "sleep0 x1000", g(bare_run, 1000))
