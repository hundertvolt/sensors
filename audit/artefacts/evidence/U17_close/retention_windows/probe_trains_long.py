# The cap-train scenario with heap samples every 25 rounds after the 4 warm-up rounds, on the poll-round clock.
import asyncio, gc
import test_asy_uart_comm as t
from _uart_comm_harness import PollRoundClock, build_pair, copied_out, transfer_limits
cap = 2 * t.PAYLOAD_SIZE
at_cap = bytes(range(cap))
limits = transfer_limits(timeout=t._SHORT_REPLY_TIMEOUT_MS, chunk_bytes=t.PAYLOAD_SIZE, max_transfer_bytes=cap)
samples = []
with PollRoundClock() as clock:
    clock.arm()
    pair = t.run(build_pair(limits=limits, get_callback=t.echo_get(at_cap), set_callback=t.accept_set()))
    async def one_round(i):
        listener = asyncio.create_task(pair.responder.uart_listen())
        over = i % 2 == 1
        if i % 4 < 2:
            pair.initiator._max_transfer_bytes = 3 * cap
            await pair.initiator.uart_set(1, bytes(cap + 1) if over else at_cap)
        else:
            pair.initiator._max_transfer_bytes = cap
            pair.responder._get_callback = t.echo_get(bytes(cap + 1) if over else at_cap)
            got = await pair.initiator.uart_get(2)
            if got is not None:
                copied_out(got)
        try:
            await asyncio.wait_for(listener, t._STEP_BOUND_S)
        except asyncio.TimeoutError:
            listener.cancel()
        t._scrub(pair)
    async def scenario():
        for i in range(4):
            await one_round(i)
        for i in range(4, 1204):
            if (i - 4) % 100 == 0:
                gc.collect(); samples.append(gc.mem_alloc())
            await one_round(i)
        gc.collect(); samples.append(gc.mem_alloc())
    t.run(scenario(), limit=3000)
    clock.disarm()
print([s - samples[0] for s in samples])
