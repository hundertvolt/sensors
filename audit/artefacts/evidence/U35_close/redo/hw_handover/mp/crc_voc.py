"""Run over `mpremote mount` of the staged .mpy modules: the project's CRC8/16/32 over 256 bytes through run_inc() (it
yields per byte) with time per byte and heap allocated per call, and VOCAlgorithm.vocalgorithm_process() time and
allocation per sample (F.3 stall.crc_byte, stall.voc_process). gc.collect() only sets each measurement's baseline."""

import asyncio
import gc
import time

from asy_crc_checks import CRC8, CRC16, CRC32
from voc_algorithm import VOCAlgorithm

BUF = bytearray(range(256))


async def crc(cls: type) -> None:
    c = cls()
    for rnd in range(2):  # the first round includes any lazy setup
        gc.collect()
        a0, t = gc.mem_alloc(), time.ticks_us()
        await c.run_inc(BUF)
        dt, a1 = time.ticks_diff(time.ticks_us(), t), gc.mem_alloc()
        await c.check_inc()
        print("SUM crc %s round=%d bytes=256 us=%d us_per_byte=%d alloc_bytes=%d" % (cls.__name__, rnd, dt, dt // 256, a1 - a0))


async def main() -> None:
    for cls in (CRC8, CRC16, CRC32):
        await crc(cls)


asyncio.run(main())
v = VOCAlgorithm()
v.vocalgorithm_init()
worst = total = 0
gc.collect()
a0 = gc.mem_alloc()
for i in range(200):
    t = time.ticks_us()
    v.vocalgorithm_process(30000 + (i % 50))
    d = time.ticks_diff(time.ticks_us(), t)
    worst, total = max(worst, d), total + d
a1 = gc.mem_alloc()
print("SUM voc process n=200 avg_us=%d worst_us=%d alloc_bytes_per_sample=%d" % (total // 200, worst, (a1 - a0) // 200))
print("DONE=1")
