# Bytes one overlay wake allocates: toggle(), then yields until the frame is written; gc off for the window.
import asyncio
import gc

from asy_neopixel_driver import NeopixelDriver

WAKES = 20


async def main():
    driver = NeopixelDriver(0)
    overlay = driver.start_asy_overlay()
    for _ in range(10):
        await asyncio.sleep(0)
    pix = driver._pixel
    pix.writes = None  # the fake's per-write list copy is the fake's cost: drop the record
    calls = [0]

    def write():
        calls[0] += 1

    pix.write = write
    deltas = []
    for _ in range(WAKES):
        n = calls[0]
        gc.collect()
        gc.disable()
        before = gc.mem_alloc()
        driver.toggle()
        while calls[0] == n:
            await asyncio.sleep(0)
        for _ in range(4):  # the next wait set up, its waiter registered
            await asyncio.sleep(0)
        after = gc.mem_alloc()
        gc.enable()
        deltas.append(after - before)
    overlay.cancel()
    try:
        await overlay
    except asyncio.CancelledError:
        pass
    print("per-wake bytes:", deltas[2:])


asyncio.run(main())
