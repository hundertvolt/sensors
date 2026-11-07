"""uart_hang2.py: the driver's ring state around an overrun, then prims4's reader with a 100 ms feeder trace."""
import time, asyncio, machine, asy_uart_driver
from machine import Pin, UART, mem32
wdt = machine.WDT(timeout=8000)
T0 = time.ticks_ms()
def p(*a): print(time.ticks_diff(time.ticks_ms(), T0), *a)
tx = UART(0, 115200, tx=Pin(0), rx=Pin(1), txbuf=512)
u = asy_uart_driver.UART(1, 8, 9, baudrate=115200, rxbuf=512, txbuf=512, rx_ring=512)
u._rx_dma is not None or u.setup_rx_ring()
def state(tag):
    d = u._rx_dma
    p(tag, "count", hex(d.count), "pos", hex(u._rx_pos), "rsr", hex(mem32[u._reg_rsr]), "pending", u._rx_overrun_pending,
      "overruns", u.rx_overruns, "busy", d.active(), "reload_busy", u._rx_reload.active(), "level", u._rx_level())
state("fresh")
f = bytearray(64); f[0] = 0xA5
tx.write(f); time.sleep_ms(8); state("after 64")
for i in range(9): tx.write(f); time.sleep_ms(8)
state("after 640")
async def main():
    for i in range(4):
        c = await u.read(128, 200); state("read %d -> %s" % (i, None if c is None else len(c)))
    tx.write(f); await asyncio.sleep_ms(8); state("one more frame")
    c = await u.read(128, 200); state("read -> %s" % (None if c is None else len(c)))
    beats = [0]
    async def feeder():
        while True: wdt.feed(); beats[0] += 1; p("beat", beats[0]); await asyncio.sleep_ms(100)
    async def reader():
        n = 0
        while True:
            c = await u.read(128, 200); n += 1
            if n % 500 == 0: p("reads", n)
    async def writer():
        while True: tx.write(f); await asyncio.sleep_ms(8)
    for t in (feeder(), reader(), writer()): asyncio.create_task(t)
    await asyncio.sleep(3)
    state("end")
asyncio.run(main())
p("DONE")
