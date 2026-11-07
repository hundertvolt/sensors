# Worst and >40 ms overshoots of a 1 ms asyncio sleep over 12 s.
import time, asyncio
async def main():
    worst = 0; big = 0; end = time.ticks_add(time.ticks_ms(), 12000)
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        t0 = time.ticks_ms(); await asyncio.sleep_ms(1); d = time.ticks_diff(time.ticks_ms(), t0) - 1
        worst = max(worst, d); big += d > 40
    print("worst_ms", worst, "over40", big)
asyncio.run(main())
