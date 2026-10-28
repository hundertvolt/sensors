"""Long FRAM run at dev's 1 MHz for rare-event rates: RDID against its first read (the ID retries' W29), 256-byte reads
of a known pattern (F.5.2's EIO, wrong bytes), and 1-byte writes read back, each counted with its worst duration.
Writes only the scratch block 0x3FF00-0x3FFFF and puts back what it found; DUR_S per run."""

import time

from machine import SPI, Pin

DUR_S = 1200
SCRATCH = 0x3FF00
cs = Pin(5, Pin.OUT, value=1)
spi = SPI(0, baudrate=1_000_000, polarity=0, phase=0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))


def xfer(head: bytes, rx: bytearray | None = None, tx: bytes | None = None) -> None:
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


class C:
    def __init__(self, op: str) -> None:
        self.op = op
        self.n = self.errs = self.bad = self.worst = 0

    def run(self, fn) -> None:
        t = time.ticks_us()
        try:
            self.bad += fn() is False
        except OSError:
            self.errs += 1
        self.n += 1
        self.worst = max(self.worst, time.ticks_diff(time.ticks_us(), t))


RDID, READ, WREN = b"\x9f", addr(0x03, SCRATCH), b"\x06"
idb, cur, buf, one = bytearray(4), bytearray(4), bytearray(256), bytearray(1)
xfer(RDID, idb)
saved = bytearray(256)
xfer(READ, saved)
pattern = bytes((i * 7 + 3) & 0xFF for i in range(256))
xfer(WREN)
xfer(addr(0x02, SCRATCH), tx=pattern)
w_heads = [addr(0x02, SCRATCH + k) for k in range(256)]
r_heads = [addr(0x03, SCRATCH + k) for k in range(256)]
w_vals = [pattern[k : k + 1] for k in range(256)]
c_id, c_rd, c_wr = C("rdid"), C("read256"), C("write1")


def write1(k: int) -> bool:
    xfer(WREN)
    xfer(w_heads[k], tx=w_vals[k])
    xfer(r_heads[k], one)
    return one[0] == pattern[k]


end = time.ticks_add(time.ticks_ms(), DUR_S * 1000)
i = 0
try:
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        c_id.run(lambda: xfer(RDID, cur) or cur == idb)
        c_rd.run(lambda: xfer(READ, buf) or buf == pattern)
        k = i & 255
        c_wr.run(lambda: write1(k))
        i += 1
        if i % 64 == 0:
            time.sleep_ms(1)
finally:
    xfer(WREN)
    xfer(addr(0x02, SCRATCH), tx=saved)
    xfer(READ, buf)
for c in (c_id, c_rd, c_wr):
    print("SUM L fram op=%s n=%d oserrors=%d bad=%d worst_us=%d" % (c.op, c.n, c.errs, c.bad, c.worst))
print("SUM L fram scratch_restored=%d" % (buf == saved))
print("DONE=1")
