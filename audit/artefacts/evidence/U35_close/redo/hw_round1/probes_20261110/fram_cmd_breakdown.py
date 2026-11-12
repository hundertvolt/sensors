"""Bench probe (bench, 2026-11-10): where e8d48fab's ~0.5 ms per FRAM command goes, layer by layer, from mounted .mpy;
plus 11-09's raw machine.SPI status read as the control for the mount. Reads, and writes at 0x3ff00 only (FRAM writes
are not wear; production's layout sits at the chip's start)."""
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
    print("FRAMCMD2", name, "n", n, "min", ts[0], "med", ts[n // 2], "p95", ts[(n * 95) // 100], "max", ts[-1], "us")


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
    dev = fram._spidev
    raw = spi._spi
    cs = Pin(5)
    b1 = bytearray(1)
    b13 = bytearray(13)
    one = b"\x05"
    print("FRAMCMD2 initialized", mgr.initialized, "write_protected", fram.get_write_protected())
    if not mgr.initialized or fram.get_write_protected():
        return

    def empty():
        pass

    def raw_rdsr():  # 11-09's rdsr_lean on the same bus object: the control for the mount
        cs.value(0)
        raw.write(one)
        raw.readinto(b1)
        cs.value(1)

    def sess():
        dev.session_begin()
        dev.session_end()

    def sess_rdsr():
        dev.session_begin()
        dev.write_sync(one)
        dev.readinto_sync(b1)
        dev.session_end()

    for name, fn in (
        ("empty_call", empty),
        ("raw_rdsr", raw_rdsr),
        ("session_begin_end_only", sess),
        ("session_rdsr_via_spidevice", sess_rdsr),
        ("driver_read_status", fram._read_status),
        ("driver_wel_is_set", fram._wel_is_set),
        ("driver_get_values_1B", lambda: fram.get_values(b1, ADDR)),
        ("driver_get_values_13B", lambda: fram.get_values(b13, ADDR)),
        ("driver_set_values_1B", lambda: fram.set_values(b1, ADDR)),
        ("driver_set_values_13B", lambda: fram.set_values(b13, ADDR)),
    ):
        run(name, fn)


asyncio.run(main())
print("FRAMCMD2 done")
