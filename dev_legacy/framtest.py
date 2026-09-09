

async def foo():
    return True



import asyncio
from asy_spi_driver import SPI, SPIDevice

from asy_fram_manager import AsyFramManager
from crc_checks import CRC8, CRC16, CRC32

async def tsfake():
    return True

spi0 = SPI(0, 2, 3, 4)

fram = AsyFramManager(spi0, 5, max_size=0x40000, debug=5)

print("setup", asyncio.run(fram.setup()))

foo = fram.get_timestamped_chunk(400, tsfake, crc=CRC32(), verify=0)
foo2 = fram.get_timestamped_chunk(400, tsfake, crc=CRC32(), verify=0)
bar = foo.get_buffer()
bar2 = foo2.get_buffer()

print("read", asyncio.run(foo.read_into(bar)))
print("read", asyncio.run(foo2.read_into(bar2)))


baz = bar.get_data_buf()
baz2 = bar2.get_data_buf()
for n in range(400):
    baz[n] = n
    baz2[n] = n+8

print("write", asyncio.run(foo.write_into(bar)))
print("write", asyncio.run(foo2.write_into(bar2)))


print("read", asyncio.run(foo.read()))
print("read", asyncio.run(foo2.read()))


print("errcnt", asyncio.run(fram.get_error_counter()))



print(asyncio.run(foo.clear()))
print(asyncio.run(foo2.clear()))


print(asyncio.run(foo.read()))
print(asyncio.run(foo2.read()))


print(asyncio.run(foo.write(bytearray(range(400)))))
print(asyncio.run(foo2.write(bytearray(range(400)))))


print(asyncio.run(foo.read()))
print(asyncio.run(foo2.read()))

