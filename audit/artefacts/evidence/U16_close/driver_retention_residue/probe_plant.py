# Plants a retention in the driver read (one 16-byte object kept per read) and expects the test to fail.
import test_asy_uart_driver as t
import asy_uart_driver
kept = []
orig = asy_uart_driver.UART.readinto_until_complete
async def leaky(self, buf, n, *a, **k):
    kept.append(bytearray(1))
    return await orig(self, buf, n, *a, **k)
asy_uart_driver.UART.readinto_until_complete = leaky
try:
    t.test_a_read_retains_nothing()
    print("PLANT NOT CAUGHT")
except AssertionError as e:
    print("plant caught", e)
