"""Bench probe (bench, 2026-11-10, lead relay 05:45 item 2): e8d48fab's FRAM chunk write and read timed on silicon from
mounted .mpy, board idle, at 0x30000 and up (production's layout sits at the chip's start); also the viper CRC32 over
264 B. FRAM writes only (not wear); nothing persisted to flash; production's chunks never touched."""
import asyncio
import gc
import sys
import time

import machine

from asy_fram_manager import FRAMManager
from asy_print_log import LogConfig
from asy_spi_driver import SPI
from crc_checks import CRC8, CRC32

wdt = machine.WDT(timeout=8000)
BASE = 0x30000  # far above dev's production layout, which the allocator lays from 0
N = 30


async def no_ntp():
    return False


def stats(name, ts, cmds):
    ts.sort()
    n = len(ts)
    print("FRAMCHUNK", name, "cmds", cmds, "n", n, "min", ts[0], "med", ts[n // 2], "max", ts[-1], "us")


def count_cmds(chunk, fn):
    dev = chunk.fram._spidev
    box = [0]
    orig = dev.session_begin

    def counted():
        box[0] += 1
        orig()

    dev.session_begin = counted
    try:
        fn()
    finally:
        del dev.session_begin  # back to the class's method
    return box[0]


async def count_cmds_async(chunk, coro_fn):
    dev = chunk.fram._spidev
    box = [0]
    orig = dev.session_begin

    def counted():
        box[0] += 1
        orig()

    dev.session_begin = counted
    try:
        await coro_fn()
    finally:
        del dev.session_begin
    return box[0]


async def main():
    spi = SPI(0, 2, 3, 4)
    mgr = FRAMManager(spi, 5, max_size=0x40000, log=LogConfig(None, 10, None))
    await mgr.setup()
    print("FRAMCHUNK initialized", mgr.initialized, "write_protected", mgr.fram.get_write_protected())
    if not mgr.initialized or mgr.fram.get_write_protected():
        print("FRAMCHUNK abort")
        return
    mgr._allocated_size = BASE
    log_chunk = mgr.get_chunk(12, crc=CRC8(), owner="PROBE_LOG")  # PrintLogHistoryStore's size at history 10: 13 B blocks
    bak_chunk = mgr.get_timestamped_chunk(256, no_ntp, crc=CRC32(), owner="PROBE_BAK")  # the SGP40 backup: 268 B blocks
    print("FRAMCHUNK addrs log", hex(log_chunk._block_addr[0]), hex(log_chunk._block_addr[1]),
          "bak", hex(bak_chunk._block_addr[0]), hex(bak_chunk._block_addr[1]), "end", hex(mgr._allocated_size))
    lbuf = log_chunk.get_buffer()
    ld = lbuf.get_data_buf()
    for i in range(len(ld)):
        ld[i] = i
    bbuf = bak_chunk.get_buffer()
    bd = bbuf.get_data_buf()
    for i in range(len(bd)):
        bd[i] = (i * 7) & 0xFF

    print("FRAMCHUNK first_write_ok log", log_chunk.write_into(lbuf), "bak", (await bak_chunk.write_into(bbuf))[0])
    c_lw = count_cmds(log_chunk, lambda: log_chunk.write_into(lbuf))
    c_lr = count_cmds(log_chunk, lambda: log_chunk.read_into(lbuf))

    async def bw():
        await bak_chunk.write_into(bbuf)

    async def br():
        await bak_chunk.read_into(bbuf)

    c_bw = await count_cmds_async(bak_chunk, bw)
    c_br = await count_cmds_async(bak_chunk, br)

    for name, cmds, fn in (("log_write_13B", c_lw, lambda: log_chunk.write_into(lbuf)),
                           ("log_read_13B", c_lr, lambda: log_chunk.read_into(lbuf))):
        gc.collect()
        ts = []
        ok = True
        for i in range(N):
            wdt.feed()
            t0 = time.ticks_us()
            r = fn()
            ts.append(time.ticks_diff(time.ticks_us(), t0))
            ok = ok and bool(r)
        stats(name, ts, cmds)
        print("FRAMCHUNK", name, "all_ok", ok)
    for name, cmds, coro in (("backup_write_268B", c_bw, bak_chunk.write_into), ("backup_read_268B", c_br, bak_chunk.read_into)):
        gc.collect()
        ts = []
        ok = True
        for i in range(N):
            wdt.feed()
            t0 = time.ticks_us()
            r = await coro(bbuf)
            ts.append(time.ticks_diff(time.ticks_us(), t0))
            ok = ok and bool(r[0])
        stats(name, ts, cmds)
        print("FRAMCHUNK", name, "all_ok", ok)
    rd = bytearray(bd)  # the data read back last must equal what was written
    print("FRAMCHUNK backup_readback_matches", rd == bytearray(((i * 7) & 0xFF) for i in range(len(bd))))

    crc = CRC32()
    cbuf = bytearray(268)
    for i in range(264):
        cbuf[i] = (i * 13) & 0xFF
    gc.collect()
    ts = []
    for i in range(N):
        t0 = time.ticks_us()
        crc.add_into(cbuf, 264)
        ts.append(time.ticks_diff(time.ticks_us(), t0))
    stats("viper_crc32_add_into_264B", ts, 0)
    print("FRAMCHUNK log_errors", mgr.pr.history if hasattr(mgr.pr, "history") else "-", "count", mgr.pr._err_count)
    print("FRAMCHUNK mounted", sorted(k for k in sys.modules if k.startswith(("asy_", "crc_"))))


asyncio.run(main())
print("FRAMCHUNK done")
