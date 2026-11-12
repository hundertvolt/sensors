"""Long UART run over dev's crossover jumper (115200, rxbuf 512) at GC threshold GC: both directions stream sequence
bytes beside allocation churn, every byte checked; counts bytes, mismatches and the worst receive backlog, and the
worst gap between two reader passes (how long the reader was held off). DUR_S per run."""

import asyncio
import gc
import time

from machine import UART, Pin

DUR_S = 1200
GC = -1


async def main() -> None:
    u0 = UART(0, 115200, tx=Pin(0), rx=Pin(1), timeout=0, timeout_char=1, rxbuf=512, txbuf=512)
    u1 = UART(1, 115200, tx=Pin(8), rx=Pin(9), timeout=0, timeout_char=1, rxbuf=512, txbuf=512)
    for u in (u0, u1):
        while u.any():
            u.read()
    end = time.ticks_add(time.ticks_ms(), DUR_S * 1000)
    res = {}

    async def send(u: UART) -> None:
        buf, s = bytearray(64), 0
        while time.ticks_diff(end, time.ticks_ms()) > 0:
            for i in range(64):
                buf[i] = (s + i) & 0xFF
            s = (s + 64) & 0xFF
            u.write(buf)
            await asyncio.sleep_ms(6)

    async def recv(u: UART, name: str) -> None:
        buf = bytearray(256)
        exp, ok, bad, backlog, gap = 0, 0, 0, 0, 0
        last = time.ticks_us()
        stop = time.ticks_add(end, 500)
        while time.ticks_diff(stop, time.ticks_ms()) > 0:
            now = time.ticks_us()
            gap = max(gap, time.ticks_diff(now, last))
            last = now
            n = u.any()
            backlog = max(backlog, n)
            if n:
                k = u.readinto(buf, min(n, 256)) or 0
                for i in range(k):
                    if buf[i] == exp:
                        ok += 1
                    else:
                        bad += 1
                    exp = (buf[i] + 1) & 0xFF
            await asyncio.sleep_ms(1)
        res[name] = (ok, bad, backlog, gap)

    async def churn() -> None:
        ring, i = [None] * 64, 0
        while time.ticks_diff(end, time.ticks_ms()) > 0:
            ring[i & 63] = bytearray(16 + (i * 37) % 497)
            i += 1
            if i % 8 == 0:
                await asyncio.sleep_ms(0)

    await asyncio.gather(send(u0), send(u1), recv(u1, "0to1"), recv(u0, "1to0"), churn())
    for name, (ok, bad, bl, gap) in res.items():
        print("SUM L uart dir=%s threshold=%d bytes_ok=%d mismatches=%d max_backlog=%d worst_reader_gap_us=%d" % (name, GC, ok, bad, bl, gap))


gc.threshold(GC)
asyncio.run(main())
gc.threshold(-1)
print("DONE=1")
