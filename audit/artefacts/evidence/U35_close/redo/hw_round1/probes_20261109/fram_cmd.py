"""Bench probe (lead, 2026-11-09): one FRAM command on dev's spi0 at 8 MHz, its parts timed (the firmware's own path
measured 0.55-0.65 ms per command on 11-05). Reads only: RDSR and READ at address 0, no WREN, no write, no FRAM
manager built, nothing persisted; the status byte is printed, never the data read."""
import asyncio
import gc
import time

import machine
from machine import SPI, Pin

wdt = machine.WDT(timeout=8000)
spi = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
spi.init(baudrate=8_000_000, polarity=0, phase=0, bits=8, firstbit=SPI.MSB)
cs = Pin(5, Pin.OUT, value=1)
N = 300
RDSR = b"\x05"
CMD = b"\x03\x00\x00\x00"  # READ, 3-byte address 0 (256 KB part)
st = bytearray(1)
xo = bytearray(b"\x05\x00")
xi = bytearray(2)
r13 = bytearray(13)
r268 = bytearray(268)


def init():
    spi.init(baudrate=8_000_000, polarity=0, phase=0, bits=8, firstbit=SPI.MSB)


def empty():
    pass


def rdsr_lean():
    cs.value(0)
    spi.write(RDSR)
    spi.readinto(st)
    cs.value(1)


def rdsr_one_call():
    cs.value(0)
    spi.write_readinto(xo, xi)
    cs.value(1)


def rdsr_init_settle():  # the C calls the driver makes per command: configure, CS, 2 us settle, transfer, CS
    init()
    cs.value(0)
    time.sleep_us(2)
    spi.write(RDSR)
    spi.readinto(st)
    cs.value(1)


def read13_lean():
    cs.value(0)
    spi.write(CMD)
    spi.readinto(r13)
    cs.value(1)


def read268_lean():
    cs.value(0)
    spi.write(CMD)
    spi.readinto(r268)
    cs.value(1)


def read268_init_settle():
    init()
    cs.value(0)
    time.sleep_us(2)
    spi.write(CMD)
    spi.readinto(r268)
    cs.value(1)


def stats(name, ts):
    ts.sort()
    n = len(ts)
    print("FRAMCMD", name, "n", n, "min", ts[0], "med", ts[n // 2], "p95", ts[(n * 95) // 100], "max", ts[-1], "us")


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


async def run_async(name, with_init):  # the async layering alone: a lock held around the command, then one yield
    lock = asyncio.Lock()
    gc.collect()
    ts = []
    for i in range(N):
        if i % 50 == 0:
            wdt.feed()
        t0 = time.ticks_us()
        async with lock:
            if with_init:
                rdsr_init_settle()
            else:
                rdsr_lean()
        await asyncio.sleep(0)
        ts.append(time.ticks_diff(time.ticks_us(), t0))
    stats(name, ts)


rdsr_lean()
print("FRAMCMD status_register", hex(st[0]))
for name, fn in (
    ("empty_call", empty),
    ("spi_init_only", init),
    ("rdsr_lean", rdsr_lean),
    ("rdsr_one_call", rdsr_one_call),
    ("rdsr_init_settle", rdsr_init_settle),
    ("read13_lean", read13_lean),
    ("read268_lean", read268_lean),
    ("read268_init_settle", read268_init_settle),
):
    run(name, fn)
asyncio.run(run_async("rdsr_lean_async_lock_yield", False))
asyncio.run(run_async("rdsr_init_settle_async_lock_yield", True))
print("FRAMCMD done")
