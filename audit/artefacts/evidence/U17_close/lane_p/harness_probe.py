import asyncio, time
import asy_uart_comm, asy_uart_driver
from asy_base_classes import PieceBuffer
from _uart_comm_harness import Pair, PollRoundClock, copied_out, transfer_limits, run, build_pair, accept_set
from asy_uart_comm import DEFAULT_LIMITS

assert copied_out(None) is None
pb = PieceBuffer(5, 2); pb.write_at(0, b"hello")
assert copied_out(pb) == b"hello"
assert copied_out(PieceBuffer(0, 2)) == b""
lim = transfer_limits(chunk_bytes=16)
assert lim.payload_size == 8 and lim.timeout == 100 and lim.chunk_bytes == 16 and lim.max_transfer_bytes == DEFAULT_LIMITS.max_transfer_bytes
p = Pair()
assert p.initiator._payload_size == 8 and p.responder._timeout == 100
assert p.initiator._chunk_bytes == DEFAULT_LIMITS.chunk_bytes
p = Pair(payload_size=16, timeout=200)
assert p.initiator._payload_size == 16 and p.responder._timeout == 200
p = Pair(limits=transfer_limits(chunk_bytes=4, max_transfer_bytes=64))
assert p.initiator._chunk_bytes == 4 and p.responder._max_transfer_bytes == 64
# clock: swaps and restores, stall fires once after arm
t0, a0 = asy_uart_comm.time, asy_uart_driver.asyncio
clock = PollRoundClock(stall_after=2, stall_ms=50)
with clock:
    assert asy_uart_comm.time is not t0 and asy_uart_driver.asyncio is not a0
    x = asy_uart_comm.time.ticks_ms(); y = asy_uart_comm.time.ticks_ms()
    assert asy_uart_comm.time.ticks_diff(y, x) == 1
    async def sleeps(n):
        for _ in range(n):
            await asy_uart_comm.asyncio.sleep_ms(0)
    asyncio.run(sleeps(5))
    assert not clock.disarm()  # planted, not armed: did not fire
    clock.arm()
    w = time.ticks_ms(); asyncio.run(sleeps(3)); el = time.ticks_diff(time.ticks_ms(), w)
    assert clock.disarm() and el >= 50, el
assert asy_uart_comm.time is t0 and asy_uart_driver.asyncio is a0
assert PollRoundClock().disarm()
# a real exchange under the clock
from _uart_comm_harness import echo_get
pair = Pair(get_callback=echo_get(b"x"), set_callback=accept_set())
async def go():
    print("setup", await pair.setup())
    r = await pair.with_listener(pair.initiator.uart_set(1, b"abc")); print(r, await pair.initiator.get_error_counter(), await pair.responder.get_error_counter()); return r
with PollRoundClock():
    assert run(go())
print("probe ok")
