# V1: a never-written chunk read twice (baseline 25caf528). V5: a layout shifted by one equal-size chunk.
import asyncio
from _fram_chip_fake import FakeMB85RS64V
import asy_spi_driver
from asy_fram_manager import AsyFramManager
from asy_spi_driver import SPI
from crc_checks import CRC8
asy_spi_driver._SPI = FakeMB85RS64V

def mk():
    m = AsyFramManager(SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4), 1, max_size=0x2000, history_length=10)
    return m, m.fram._spidev.spi._spi

async def v1():
    m, chip = mk()
    await m.setup()
    c = m.get_chunk(12, crc=CRC8())
    st = c.size + c.crc.length()
    r1 = await c.read()
    s0 = (chip.memory[st], chip.memory[st + 1])
    r2 = await c.read()
    log = await m.pr.get_log()
    print("V1 read1", r1, "block0 status after read1", s0, "read2", r2, "FRAM log", log)

async def v5():
    m1, chip1 = mk()
    await m1.setup()
    a = m1.get_chunk(12, crc=CRC8())  # old layout: owner L1 first
    b = m1.get_chunk(12, crc=CRC8())  # owner L2
    await a.write(b"L1-history!!")
    await b.write(b"L2-history!!")
    m2, chip2 = mk()
    chip2.memory[:] = chip1.memory  # same chip after a reflash that dropped owner L1
    await m2.setup()
    l2_new = m2.get_chunk(12, crc=CRC8())  # owner L2 now sits where L1's chunk was
    print("V5 new L2 chunk reads", await l2_new.read())

asyncio.run(v1())
asyncio.run(v5())
