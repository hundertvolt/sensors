# Per-round machinery alone, 1200 rounds, sampled every 100: MODE 0 clock+listener+cancel+scrub, 1 no clock,
# 2 clock and scrub only, 3 clock only with one sleep per round.
import asyncio, gc, sys
import test_asy_uart_comm as t
from _uart_comm_harness import PollRoundClock, build_pair, transfer_limits
MODE = int(sys.argv[1])
samples = []
def body():
    pair = t.run(build_pair(limits=transfer_limits(timeout=t._SHORT_REPLY_TIMEOUT_MS)))
    async def one():
        if MODE in (0, 1):
            listener = asyncio.create_task(pair.responder.uart_listen())
            await asyncio.sleep_ms(1)
            listener.cancel()
            try:
                await listener
            except asyncio.CancelledError:
                pass
        else:
            await asyncio.sleep_ms(1)
        if MODE in (0, 1, 2):
            t._scrub(pair)
    async def scenario():
        for _ in range(4):
            await one()
        for i in range(1200):
            if i % 100 == 0:
                gc.collect(); samples.append(gc.mem_alloc())
            await one()
        gc.collect(); samples.append(gc.mem_alloc())
    t.run(scenario(), limit=3000)
if MODE == 1:
    body()
else:
    with PollRoundClock() as clock:
        clock.arm()
        body()
        clock.disarm()
print(MODE, [s - samples[0] for s in samples])
