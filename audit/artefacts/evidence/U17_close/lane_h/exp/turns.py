import asyncio, time
from _uart_comm_harness import Pair, PollRoundClock, accept_set, echo_get, run
from asy_crc_checks import CRC16

def mk(crc):
    m = (lambda: None) if crc is None else crc
    p = Pair(payload_size=8, timeout=30 if crc is None else 240, get_callback=echo_get(b"v"), set_callback=accept_set(), crc_a=m(), crc_b=m())
    t0 = time.ticks_ms()
    assert run(p.setup()) is True
    return p, time.ticks_diff(time.ticks_ms(), t0)

for crc in (None, CRC16):
    p, setup_ms = mk(crc)
    with PollRoundClock():
        async def sc():
            done = [False]
            async def work():
                r = await p.initiator.uart_set(1, bytes(16))
                done[0] = True
                return r
            lt = asyncio.create_task(p.responder.uart_listen())
            wt = asyncio.create_task(work())
            turns = 0; io = 0
            n0 = len(p.fake_a.log) + len(p.fake_b.log)
            while not done[0]:
                await asyncio.sleep_ms(0)
                turns += 1
            io = len(p.fake_a.log) + len(p.fake_b.log) - n0
            r = await wt
            await lt
            return r, turns, io
        t0 = time.ticks_ms()
        r, turns, io = run(sc())
        print("crc" if crc else "nocrc", "setup_ms", setup_ms, "result", r, "turns", turns, "io", io, "ms", time.ticks_diff(time.ticks_ms(), t0))
    print(p.fake_a.log[:6])
