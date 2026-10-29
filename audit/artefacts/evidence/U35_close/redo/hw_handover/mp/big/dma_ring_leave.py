# Builds the UART driver's receive ring on UART1 (as the firmware does, for the program's life) and ends; MODE "deinit"
# stops it through the driver first. A watchdog stays armed so a hang at the following soft reset resets the board.
import machine, asy_uart_driver
MODE = "leave"
wdt = machine.WDT(timeout=8000)
u = asy_uart_driver.UART(1, 8, 9, baudrate=115200, rxbuf=512, txbuf=512, rx_ring=512, poll_wait_ms=2, poll_idle_ms=50)
ok = u._rx_dma is not None or u.setup_rx_ring()
print("SUM dma_soft", MODE, "ring", ok, "data", u._rx_dma.channel, "reload", u._rx_reload.channel, "busy", u._rx_dma.active())
if MODE == "deinit":
    print("SUM dma_soft deinit", u.deinit(), "busy_after", u._rx_dma.active())
print("DONE")
