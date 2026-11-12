"""Bench probe (bench, 2026-11-10, lead relay 12:23): the image's own boot entry under `mpremote run`, no flash write; from
BOOT_DONE every 1 s mem_free and micropython.mem_info() (its "max free sz" is the largest free block, 16 B blocks) while
the host loads /status on each LOAD line (6, 6, 6, then 2 readers, 60 s, 120 s idle after each, one collect after it)."""
from machine import WDT

watchdog = WDT(timeout=8000)

import sys

sys.path.insert(0, ".frozen")

import gc

import micropython

micropython.alloc_emergency_exception_buf(100)

import asyncio
import time

import asy_system_service
from sensortask_dev import main

gc.threshold(32768)
PLAN = ((1, 6), (2, 6), (3, 6), (4, 2))  # (load number, readers)
LOAD_S = 65  # the host's 60 s plus its start and its readers' last answers
IDLE_S = 120
DONE_AT = [None]
PH = [0]
_boot_phase = asy_system_service.SystemService.boot_phase


def boot_phase(self, phase):
    _boot_phase(self, phase)
    PH[0] += 1
    if PH[0] == 5:
        DONE_AT[0] = time.ticks_ms()


asy_system_service.SystemService.boot_phase = boot_phase
TAG = ["boot"]


async def sampler():
    while DONE_AT[0] is None:
        await asyncio.sleep_ms(100)
    while True:
        print("S", TAG[0], "t_s", time.ticks_diff(time.ticks_ms(), DONE_AT[0]) // 1000, "free", gc.mem_free())
        micropython.mem_info()
        await asyncio.sleep(1)


async def schedule():
    while DONE_AT[0] is None:
        await asyncio.sleep_ms(100)
    TAG[0] = "idle0"
    await asyncio.sleep(20)
    for n, readers in PLAN:
        TAG[0] = "load%d" % n
        print("LOAD", n, readers)
        await asyncio.sleep(LOAD_S)
        TAG[0] = "idle%d" % n
        await asyncio.sleep(IDLE_S)
        gc.collect()  # the relay's one collect after each idle gap: a measurement baseline only
        print("AFTER", n, "collected free", gc.mem_free())
        micropython.mem_info()
    print("DONE")


async def top():
    asyncio.create_task(sampler())
    asyncio.create_task(schedule())
    await main(watchdog=watchdog)


try:
    asyncio.run(top())
except KeyboardInterrupt:  # as main.py: record why, so the watchdog's reset reads 21
    asy_system_service.write_reset_record(asy_system_service.RR_INTERRUPTED)
    raise
