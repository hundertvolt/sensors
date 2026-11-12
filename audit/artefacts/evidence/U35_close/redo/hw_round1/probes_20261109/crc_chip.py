"""Bench probe (lead, 2026-11-09): the FRAM chunk CRC (CRC-32/MPEG-2) on the chip, the image's per-byte form against a
nibble table, a byte table and native (viper) code, which must give the same value, each timed; binascii's C crc32
(another CRC: ISO-HDLC) timed alongside. RAM only: no bus, no file, no flash."""
import asyncio
import binascii
import gc
import time

import machine
import micropython
from asy_crc_checks import CRC32

wdt = machine.WDT(timeout=8000)
P = 0x04C11DB7


def table(bits):
    th, tl = [], []
    for i in range(1 << bits):
        hi, lo = i << (16 - bits), 0
        for _ in range(bits):
            carry = lo >> 15
            lo = (lo << 1) & 0xFFFF
            if hi & 0x8000:
                hi = (((hi << 1) | carry) & 0xFFFF) ^ (P >> 16)
                lo ^= P & 0xFFFF
            else:
                hi = ((hi << 1) | carry) & 0xFFFF
        th.append(hi)
        tl.append(lo)
    return tuple(th), tuple(tl)


t0 = time.ticks_us()
NH, NL = table(4)
BH, BL = table(8)
print("tables_build_us", time.ticks_diff(time.ticks_us(), t0))
wdt.feed()


def bitwise(buf, hi=0xFFFF, lo=0xFFFF):
    for c in buf:
        hi ^= c << 8
        for _ in range(8):
            carry = lo >> 15
            lo = (lo << 1) & 0xFFFF
            if hi & 0x8000:
                hi = (((hi << 1) | carry) & 0xFFFF) ^ 0x04C1
                lo ^= 0x1DB7
            else:
                hi = ((hi << 1) | carry) & 0xFFFF
    return (hi << 16) | lo


def nibble(buf, hi=0xFFFF, lo=0xFFFF):
    th, tl = NH, NL
    for c in buf:
        i = (hi >> 12) ^ (c >> 4)
        hi = (((hi << 4) & 0xFFFF) | (lo >> 12)) ^ th[i]
        lo = ((lo << 4) & 0xFFFF) ^ tl[i]
        i = (hi >> 12) ^ (c & 0xF)
        hi = (((hi << 4) & 0xFFFF) | (lo >> 12)) ^ th[i]
        lo = ((lo << 4) & 0xFFFF) ^ tl[i]
    return (hi << 16) | lo


def bytetab(buf, hi=0xFFFF, lo=0xFFFF):
    th, tl = BH, BL
    for c in buf:
        i = (hi >> 8) ^ c
        hi = (((hi << 8) & 0xFFFF) | (lo >> 8)) ^ th[i]
        lo = ((lo << 8) & 0xFFFF) ^ tl[i]
    return (hi << 16) | lo


@micropython.viper
def viper_crc(buf, n: int) -> uint:
    p = ptr8(buf)
    crc = uint(0xFFFFFFFF)
    i = 0
    while i < n:
        crc ^= uint(p[i]) << 24
        for _ in range(8):
            if crc & uint(0x80000000):
                crc = (crc << 1) ^ uint(0x04C11DB7)
            else:
                crc = crc << 1
        crc &= uint(0xFFFFFFFF)
        i += 1
    return crc


def viper(buf):
    return viper_crc(buf, len(buf))


@micropython.viper
def viper_hoisted_crc(buf, n: int) -> uint:
    # The same loop with every 32-bit constant converted once, before it: a constant beyond the small-int range is
    # an object that uint() converts at each use.
    p = ptr8(buf)
    poly = uint(0x04C11DB7)
    top = uint(0x80000000)
    mask = uint(0xFFFFFFFF)
    crc = mask
    i = 0
    while i < n:
        crc ^= uint(p[i]) << 24
        j = 0
        while j < 8:
            if crc & top:
                crc = (crc << 1) ^ poly
            else:
                crc = crc << 1
            j += 1
        crc &= mask
        i += 1
    return crc


def viper_hoisted(buf):
    return viper_hoisted_crc(buf, len(buf))


buf = bytearray((i * 37 + 11) & 0xFF for i in range(264))


async def current():
    t0 = time.ticks_us()
    crc = await CRC32()._crc(memoryview(buf), 0xFFFFFFFF, P)
    return crc, time.ticks_diff(time.ticks_us(), t0)


ref, cur_us = asyncio.run(current())
print("current_per_byte_yield_264B_us", cur_us, "crc", hex(ref))
gc.collect()
for name, f in (("bitwise_no_yield", bitwise), ("nibble_table", nibble), ("byte_table", bytetab), ("viper", viper), ("viper_hoisted", viper_hoisted)):
    wdt.feed()
    same = f(buf) == ref
    best, worst = 10**9, 0
    for _ in range(10):
        t0 = time.ticks_us()
        f(buf)
        d = time.ticks_diff(time.ticks_us(), t0)
        best, worst = min(best, d), max(worst, d)
    print(name, "same" if same else "DIFFERENT", "264B_best_us", best, "264B_max_us", worst)
best = 10**9
for _ in range(10):
    t0 = time.ticks_us()
    binascii.crc32(buf)
    best = min(best, time.ticks_diff(time.ticks_us(), t0))
print("binascii_crc32_C_other_algorithm", "264B_best_us", best)
full = buf + bytes(((ref >> 24) & 0xFF, (ref >> 16) & 0xFF, (ref >> 8) & 0xFF, ref & 0xFF))
print("residue_with_crc_appended", bitwise(full), nibble(full), bytetab(full), viper(full), viper_hoisted(full))
print("done")
