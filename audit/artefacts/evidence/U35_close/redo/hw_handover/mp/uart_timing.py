"""Bare-image UART timing over dev's crossover jumper (UART0 GP0/GP1, UART1 GP8/GP9, 115200): how long read() waits
for missing bytes per timeout_char, a whole frame read against reads clamped to any(), any()'s latency for one byte,
and DUR_S of both directions streaming beside allocation churn, every byte checked. SUM lines summarise."""

import asyncio
import gc
import time

from machine import UART, Pin

DUR_S = 120
BAUD = 115200


def uarts(tc: int = 1) -> tuple:
    u0 = UART(0, BAUD, tx=Pin(0), rx=Pin(1), timeout=0, timeout_char=tc, rxbuf=512, txbuf=512)
    u1 = UART(1, BAUD, tx=Pin(8), rx=Pin(9), timeout=0, timeout_char=tc, rxbuf=512, txbuf=512)
    time.sleep_ms(20)
    for u in (u0, u1):
        while u.any():
            u.read()
    return u0, u1


def wait_any(u: UART, n: int, ms: int = 50) -> bool:
    t = time.ticks_ms()
    while u.any() < n:
        if time.ticks_diff(time.ticks_ms(), t) > ms:
            return False
    return True


def missing_bytes_wait() -> None:
    for tc in (1, 2, 5, 10):
        u0, u1 = uarts(tc)
        worst, got = 0, 0
        for _ in range(10):
            u0.write(b"abcdefghij")
            wait_any(u1, 10)
            t = time.ticks_us()
            got = len(u1.read(53) or b"")
            worst = max(worst, time.ticks_diff(time.ticks_us(), t))
        print("SUM uart_read_short timeout_char=%d got=%d of 53 worst_us=%d" % (tc, got, worst))


def frame_read() -> None:
    u0, u1 = uarts(1)
    frame = bytes(range(53))
    whole, clamp_call, clamp_total = 0, 0, 0
    for _ in range(10):
        u0.write(frame)
        wait_any(u1, 1)
        t = time.ticks_us()
        u1.read(53)
        whole = max(whole, time.ticks_diff(time.ticks_us(), t))
    for _ in range(10):
        u0.write(frame)
        got, t0 = 0, time.ticks_us()
        while got < 53 and time.ticks_diff(time.ticks_us(), t0) < 50000:
            n = u1.any()
            if n:
                t = time.ticks_us()
                got += len(u1.read(n))
                clamp_call = max(clamp_call, time.ticks_diff(time.ticks_us(), t))
        clamp_total = max(clamp_total, time.ticks_diff(time.ticks_us(), t0))
    print("SUM uart_frame53 whole_read_worst_us=%d clamped_call_worst_us=%d clamped_frame_worst_us=%d" % (whole, clamp_call, clamp_total))


def any_latency() -> None:
    u0, u1 = uarts(1)
    worst, best = 0, 1 << 30
    for _ in range(20):
        t = time.ticks_us()
        u0.write(b"x")
        while not u1.any() and time.ticks_diff(time.ticks_us(), t) < 20000:
            pass
        d = time.ticks_diff(time.ticks_us(), t)
        worst, best = max(worst, d), min(best, d)
        u1.read()
    print("SUM uart_any_latency_1byte best_us=%d worst_us=%d (wire time 87 us)" % (best, worst))


async def stream() -> None:
    u0, u1 = uarts(1)
    end = time.ticks_add(time.ticks_ms(), DUR_S * 1000)
    res = {}

    async def send(u: UART, name: str) -> None:
        buf, s = bytearray(64), 0
        while time.ticks_diff(end, time.ticks_ms()) > 0:
            for i in range(64):
                buf[i] = (s + i) & 0xFF
            s = (s + 64) & 0xFF
            u.write(buf)
            await asyncio.sleep_ms(6)

    async def recv(u: UART, name: str) -> None:
        buf = bytearray(256)
        exp, n_ok, n_bad, backlog = 0, 0, 0, 0
        idle_end = time.ticks_add(end, 500)
        while time.ticks_diff(idle_end, time.ticks_ms()) > 0:
            n = u.any()
            backlog = max(backlog, n)
            if n:
                k = u.readinto(buf, min(n, 256)) or 0
                for i in range(k):
                    if buf[i] == exp:
                        n_ok += 1
                    else:
                        n_bad += 1
                    exp = (buf[i] + 1) & 0xFF
            await asyncio.sleep_ms(1)
        res[name] = (n_ok, n_bad, backlog)

    async def churn() -> None:
        ring, i = [None] * 64, 0
        while time.ticks_diff(end, time.ticks_ms()) > 0:
            ring[i & 63] = bytearray(16 + (i * 37) % 497)
            i += 1
            if i % 8 == 0:
                await asyncio.sleep_ms(0)

    await asyncio.gather(send(u0, "0to1"), send(u1, "1to0"), recv(u1, "0to1"), recv(u0, "1to0"), churn())
    for name, (ok, bad, bl) in res.items():
        print("SUM uart_stream %s dur_s=%d bytes_ok=%d mismatches=%d max_backlog=%d of 512" % (name, DUR_S, ok, bad, bl))


gc.threshold(-1)
missing_bytes_wait()
frame_read()
any_latency()
asyncio.run(stream())
print("DONE=1")
