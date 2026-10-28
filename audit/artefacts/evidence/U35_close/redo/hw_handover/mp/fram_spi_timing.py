"""Bare-image FRAM timing on dev's SPI0 (GP2/GP3/GP4, CS GP5; MB85RS2MTA op-codes): RDID stability, each command's
duration at 1 MHz, and 256-byte reads per baud rate checked for OSError and wrong bytes. Writes only the scratch block
0x3FF00-0x3FFFF, above every chunk, and puts back the bytes it found there."""

import binascii
import time

from machine import SPI, Pin

SCRATCH = 0x3FF00
cs = Pin(5, Pin.OUT, value=1)


def spi_at(baud: int) -> SPI:
    return SPI(0, baudrate=baud, polarity=0, phase=0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))


def xfer(spi: SPI, head: bytes, rx: bytearray | None = None, tx: bytes | None = None) -> None:
    cs(0)
    try:
        spi.write(head)
        if rx is not None:
            spi.readinto(rx)
        if tx is not None:
            spi.write(tx)
    finally:
        cs(1)


def addr(op: int, a: int) -> bytes:
    return bytes((op, (a >> 16) & 0xFF, (a >> 8) & 0xFF, a & 0xFF))


def write(spi: SPI, a: int, data: bytes) -> None:
    xfer(spi, b"\x06")
    xfer(spi, addr(0x02, a), tx=data)


def timed(fn, n: int = 200) -> int:
    worst = 0
    for _ in range(n):
        t = time.ticks_us()
        fn()
        worst = max(worst, time.ticks_diff(time.ticks_us(), t))
    return worst


spi = spi_at(1_000_000)
print("SUM fram spi=%s" % spi)
idb, cur = bytearray(4), bytearray(4)
xfer(spi, b"\x9f", idb)
diff = 0
for _ in range(1000):
    xfer(spi, b"\x9f", cur)
    diff += cur != idb
sr = bytearray(1)
xfer(spi, b"\x05", sr)
print("SUM fram rdid=%s mismatches_in_1000=%d status=0x%02x" % (binascii.hexlify(idb).decode(), diff, sr[0]))

saved = bytearray(256)
xfer(spi, addr(0x03, SCRATCH), saved)
b1, b32, b256 = bytearray(1), bytearray(32), bytearray(256)
print("SUM fram_cmd_worst_us rdsr=%d read1=%d read32=%d read256=%d write1=%d" % (
    timed(lambda: xfer(spi, b"\x05", sr)),
    timed(lambda: xfer(spi, addr(0x03, SCRATCH), b1)),
    timed(lambda: xfer(spi, addr(0x03, SCRATCH), b32)),
    timed(lambda: xfer(spi, addr(0x03, SCRATCH), b256)),
    timed(lambda: write(spi, SCRATCH, b"\xa5"))))

pattern = bytes((i * 7 + 3) & 0xFF for i in range(256))
try:
    write(spi, SCRATCH, pattern)
    for baud in (1_000_000, 4_000_000, 10_000_000, 20_000_000):
        s = spi_at(baud)
        errs, wrong, last = 0, 0, ""
        for _ in range(500):
            try:
                xfer(s, addr(0x03, SCRATCH), b256)
                wrong += b256 != pattern
            except OSError as e:
                errs += 1
                last = repr(e)
        print("SUM fram_read256 baud=%d actual=%s oserrors=%d wrong=%d of 500 last=%s" % (baud, s, errs, wrong, last))
finally:
    spi = spi_at(1_000_000)
    write(spi, SCRATCH, saved)
    xfer(spi, addr(0x03, SCRATCH), b256)
    print("SUM fram scratch_restored=%d" % (b256 == saved))
print("DONE=1")
