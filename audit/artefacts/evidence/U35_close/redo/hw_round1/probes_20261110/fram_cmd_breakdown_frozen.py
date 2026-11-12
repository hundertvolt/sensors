"""Bench probe (bench, 2026-11-10): the image's frozen FRAM command path (snapshot 58) layer by layer, 300 calls each,
after one begin(); the raw machine.SPI status read as the control. Reads, and writes at 0x3ff00 only (FRAM writes are not
wear; production's layout sits at the chip's start)."""
import asyncio
import gc
import time

import machine
from machine import Pin

from asy_fram_manager import FRAMManager
from asy_print_log import LogConfig
from asy_spi_driver import SPI

wdt = machine.WDT(timeout=8000)
ADDR = 0x3FF00
N = 300


def stats(name, ts):
    ts.sort()
    n = len(ts)
    print("FRAMCMD3", name, "n", n, "min", ts[0], "med", ts[n // 2], "p95", ts[(n * 95) // 100], "max", ts[-1], "us")


def run(name, fn):
    gc.collect()
    ts = []
    for i in range(N):
        if i % 50 == 0:
            wdt.feed()
        t0 = time.ticks_us()
        fn()
        ts.append(time.ticks_diff(time.ticks_us(), t0))
    stats(name, ts)


async def main():
    spi = SPI(0, 2, 3, 4)
    mgr = FRAMManager(spi, 5, max_size=0x40000, log=LogConfig(None, 10, None))
    await mgr.setup()
    fram = mgr.fram
    raw = spi._spi
    cs = Pin(5)
    b1 = bytearray(1)
    b13 = bytearray(13)
    one = b"\x05"
    print("FRAMCMD3 initialized", mgr.initialized, "write_protected", fram.get_write_protected(), "gc_threshold", gc.threshold())
    if not mgr.initialized or fram.get_write_protected():
        return

    def empty():
        pass

    def raw_rdsr():
        cs.value(0)
        raw.write(one)
        raw.readinto(b1)
        cs.value(1)

    fram.begin()
    for name, fn in (
        ("empty_call", empty),
        ("raw_rdsr", raw_rdsr),
        ("begin_only", fram.begin),
        ("send_and_read_rdsr", fram._read_status),
        ("send_command_wrdi", lambda: fram._send_command(b"\x04")),
        ("get_values_1B_no_begin", lambda: fram.get_values(b1, ADDR)),
        ("get_values_13B_no_begin", lambda: fram.get_values(b13, ADDR)),
        ("set_values_13B_no_begin", lambda: fram.set_values(b13, ADDR)),
    ):
        run(name, fn)


asyncio.run(main())
print("FRAMCMD3 done")
