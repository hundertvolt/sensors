"""Bench probe (bench, 2026-11-10, lead relay 12:03, item 3 under load): snap58_heap_stack.py with a 150 s run, the host
loading /status (6 readers, 60 s) from 20 s after BOOT_DONE, so the webserver and log-store leaves are reached; the
deepest micropython.stack_use() per leaf. No flash write. Serves after DONE."""
from machine import WDT

watchdog = WDT(timeout=8000)

import sys

sys.path.insert(0, ".frozen")

import gc

import micropython

micropython.alloc_emergency_exception_buf(100)

import asyncio
import time

import asy_fram_driver
import asy_i2c_driver
import asy_print_log
import asy_system_service
import asy_uart_driver
import asy_webserver_service
from sensortask_dev import main

gc.threshold(32768)
RUN_S = 150
PEAK = {}
PHASES = [0]
DONE_AT = [None]


def heap(tag, full):
    print("HEAP", tag, "free", gc.mem_free(), "alloc", gc.mem_alloc(), "uptime_ms", time.ticks_ms())
    micropython.mem_info(1) if full else micropython.mem_info()
    print("HEAP_END", tag)


def wrap(cls, name, tag):
    orig = getattr(cls, name)
    PEAK[tag] = 0

    def w(*a, **k):
        u = micropython.stack_use()
        if u > PEAK[tag]:
            PEAK[tag] = u
        return orig(*a, **k)

    setattr(cls, name, w)


wrap(asy_fram_driver.FRAM_SPI, "_send_and_read", "fram_send_and_read")
wrap(asy_fram_driver.FRAM_SPI, "_send_and_write", "fram_send_and_write")
wrap(asy_i2c_driver.I2C, "_read_into_scratch", "i2c_read")
wrap(asy_i2c_driver.I2C, "writeto", "i2c_writeto")
wrap(asy_uart_driver.UART, "_rx_copy", "uart_rx_copy")
wrap(asy_webserver_service._PieceWriter, "flush", "web_flush")
wrap(asy_print_log.PrintLogHistoryStore, "_write", "log_store_write")

_boot_phase = asy_system_service.SystemService.boot_phase


def boot_phase(self, phase):
    _boot_phase(self, phase)
    PHASES[0] += 1
    if PHASES[0] == 5:  # BOOT_DONE: setups run, tasks and timers started, the first NTP sync returned
        DONE_AT[0] = time.ticks_ms()
        heap("BOOT_DONE", True)


asy_system_service.SystemService.boot_phase = boot_phase


async def sampler():
    print("STACK top_level", micropython.stack_use())
    while DONE_AT[0] is None:
        await asyncio.sleep(1)
    last = -1
    while True:
        el = time.ticks_diff(time.ticks_ms(), DONE_AT[0]) // 1000
        if el // 10 != last:
            last = el // 10
            print("SAMPLE s", el, "free", gc.mem_free(), "peaks", sorted(PEAK.items()))
        if el >= RUN_S:
            break
        await asyncio.sleep(5)
    heap("RUN_END", False)
    print("STACK peaks", sorted(PEAK.items()), "max", max(PEAK.values()))
    gc.collect()
    heap("RUN_END_COLLECTED", False)
    print("DONE")


async def top():
    asyncio.create_task(sampler())
    await main(watchdog=watchdog)


try:
    asyncio.run(top())
except KeyboardInterrupt:  # as main.py: record why, or the watchdog's reset reads as a plain expiry (RR 2, 11-10 11:37)
    asy_system_service.write_reset_record(asy_system_service.RR_INTERRUPTED)
    raise
