"""uart_hang3.py: read()'s steps one by one after a ring lap."""
import time, asyncio, select, machine, asy_uart_driver
from machine import Pin, UART
tx = UART(0, 115200, tx=Pin(0), rx=Pin(1), txbuf=512)
u = asy_uart_driver.UART(1, 8, 9, baudrate=115200, rxbuf=512, txbuf=512, rx_ring=512)
u._rx_dma is not None or u.setup_rx_ring()
f = bytearray(64)
for i in range(10): tx.write(f); time.sleep_ms(8)
def s(tag): print(tag, "pending", u._rx_overrun_pending, "pos", hex(u._rx_pos), "count", hex(u._rx_dma.count), "active_uart", u._active_uart() is not None, "cancel", u._cancel)
async def main():
    s("lapped")
    print("level", u._rx_level()); s("after level")
    print("ready", await u.ready(select.POLLIN, 200)); s("after ready")
    print("buffered", u._buffered(128)); s("after buffered")
    print("level", u._rx_level()); s("after level 2")
    print("read", await u.read(128, 200)); s("after read")
    tx.write(f); await asyncio.sleep_ms(10)
    print("read", await u.read(128, 200)); s("after read 2")
asyncio.run(main())
print("DONE")
