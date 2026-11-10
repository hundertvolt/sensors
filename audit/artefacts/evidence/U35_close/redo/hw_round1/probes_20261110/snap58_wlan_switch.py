"""Bench probe (bench, 2026-11-10, lead relay 11:16 item 6): the image's own boot entry under `mpremote run`, no flash write;
asyncio loop lag sampled every 10 ms in 5 s windows, the WLAN mode at every change, and the UART link's counters, while
the host takes the bench AP down (STA -> hotspot) and up again (hotspot -> STA). Serves throughout."""
from machine import WDT

watchdog = WDT(timeout=8000)

import sys

sys.path.insert(0, ".frozen")

import gc

import micropython

micropython.alloc_emergency_exception_buf(100)

import asyncio
import time

import network

import asy_system_service
import sensortask_dev as st
from sensortask_dev import main

gc.threshold(32768)
BINS = (10, 50, 100, 250, 500, 1000)  # ms upper edges; the last bin is >= 1000
hist = [0] * (len(BINS) + 1)
DONE_AT = [None]
_boot_phase = asy_system_service.SystemService.boot_phase
PH = [0]


def boot_phase(self, phase):
    _boot_phase(self, phase)
    PH[0] += 1
    if PH[0] == 5:
        DONE_AT[0] = time.ticks_ms()


asy_system_service.SystemService.boot_phase = boot_phase


async def sampler():
    sta = network.WLAN(network.STA_IF)
    ap = network.WLAN(network.AP_IF)
    while DONE_AT[0] is None:
        await asyncio.sleep_ms(100)
    t_base = time.ticks_ms()
    win_max = 0
    win_start = t_base
    i = 0
    state = None
    while True:
        t0 = time.ticks_ms()
        await asyncio.sleep_ms(10)
        lag = time.ticks_diff(time.ticks_ms(), t0) - 10
        if lag > win_max:
            win_max = lag
        b = 0
        while b < len(BINS) and lag >= BINS[b]:
            b += 1
        hist[b] += 1
        i += 1
        if i % 25 == 0:
            now_state = (int(sta.isconnected()), int(ap.active()))
            if now_state != state:
                state = now_state
                lk = st.uart_link_init
                print("MODE t_ms", time.ticks_diff(time.ticks_ms(), t_base), "sta_conn", state[0], "ap", state[1],
                      "uart_tr", lk._transfers, "uart_fail", lk._failures, "free", gc.mem_free())
        now = time.ticks_ms()
        if time.ticks_diff(now, win_start) >= 5000:
            lk = st.uart_link_init
            print("LAG t_ms", time.ticks_diff(now, t_base), "max_ms", win_max, "sta_conn", state[0] if state else -1,
                  "ap", state[1] if state else -1, "uart_tr", lk._transfers, "uart_fail", lk._failures)
            win_max = 0
            win_start = now
            if i % 3000 < 600:  # about every minute
                print("HIST edges_ms", BINS, "counts", hist)


async def top():
    asyncio.create_task(sampler())
    await main(watchdog=watchdog)


try:
    asyncio.run(top())
except KeyboardInterrupt:  # as main.py: record why, so the watchdog's reset reads 21
    print("HIST final edges_ms", BINS, "counts", hist)
    asy_system_service.write_reset_record(asy_system_service.RR_INTERRUPTED)
    raise
