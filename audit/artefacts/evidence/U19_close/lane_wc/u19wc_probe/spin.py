import asyncio, time, gc

class C:
    def __init__(self):
        self.now = 0.0

async def spinner(c, until):
    while c.now < until:
        await asyncio.sleep_ms(0)

async def driver(c, n):
    for _ in range(n):
        await asyncio.sleep_ms(0)
        c.now += 0.005

async def main(k):
    c = C()
    tasks = [asyncio.create_task(spinner(c, 4.0)) for _ in range(k)]
    t0 = time.ticks_ms()
    await driver(c, 1000)
    for t in tasks:
        await t
    return time.ticks_diff(time.ticks_ms(), t0)

for k in (1, 5, 20):
    gc.collect()
    print("spinners", k, "ms per 1000 rounds", asyncio.run(main(k)))
