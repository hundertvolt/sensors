import asyncio
from print_log import PrintLogHistStore
from asy_spi_driver import SPI, SPIDevice
from asy_fram_manager import AsyFramManager

spi0 = SPI(0, 2, 3, 4)
fram = AsyFramManager(spi0, 5, max_size=0x40000, debug=5)
asyncio.run(fram.setup())

foo = PrintLogHistStore(fram, 10, 5)
asyncio.run(foo.setup())
print(asyncio.run(foo.get_log("foo")))

asyncio.run(foo.err_s("ErrTest", errno=5))
asyncio.run(foo.err_s("ErrTest", errno=6))
asyncio.run(foo.err_s("ErrTest", errno=7))
asyncio.run(foo.err_s("ErrTest", errno=127))

asyncio.run(foo.wrn_s("ErrTest", wrnno=5))
asyncio.run(foo.wrn_s("ErrTest", wrnno=6))
asyncio.run(foo.wrn_s("ErrTest", wrnno=7))
asyncio.run(foo.wrn_s("ErrTest", wrnno=127))

print(asyncio.run(foo.get_log("foo")))

asyncio.run(foo.reset())
print(asyncio.run(foo.get_log("foo")))

