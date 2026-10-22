# Every >25 ms overshoot of a 1 ms asyncio sleep over 180 s, with the monotonic ms it happened at.
import time, asyncio
async def main():
    end = time.ticks_add(time.ticks_ms(), 180000); hits = []
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        t0 = time.ticks_ms(); await asyncio.sleep_ms(1); d = time.ticks_diff(time.ticks_ms(), t0) - 1
        if d > 25: hits.append((t0, d))
    print("hits", hits)
asyncio.run(main())
