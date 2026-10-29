"""uart_hang.py: where prims4's UART pair stops the loop: stepwise, printing before and after each call."""
import time, asyncio, machine, asy_uart_driver
from machine import Pin, UART
wdt = machine.WDT(timeout=8000)
T0 = time.ticks_ms()
def p(*a): print(time.ticks_diff(time.ticks_ms(), T0), *a)
tx = UART(0, 115200, tx=Pin(0), rx=Pin(1), txbuf=512)
u = asy_uart_driver.UART(1, 8, 9, baudrate=115200, rxbuf=512, txbuf=512, rx_ring=512)
p("ring", u._rx_dma is not None or u.setup_rx_ring())
f = bytearray(64); f[0] = 0xA5
for i in range(10):
    tx.write(f); time.sleep_ms(8); p("sync", i, "level", u._rx_level())
wdt.feed()
async def writer(n):
    for i in range(n):
        p("w", i); tx.write(f); await asyncio.sleep_ms(8)
async def reader(n):
    for i in range(n):
        p("r>", i); c = await u.read(128, 200); p("r<", i, None if c is None else len(c))
async def main():
    p("reader alone"); await reader(3)
    p("writer alone"); await writer(5)
    p("both"); w = asyncio.create_task(writer(40)); await reader(40); await w
asyncio.run(main())
p("DONE")
