"""Read-only odds and ends on the bare image: the identity of i2c0's unknown device at 0x18 (raw reads and the register
IDs of the usual candidates: MCP9808 0x06/0x07, LIS3DH 0x0F), and whether I2C/SPI deinit() is a no-op on rp2 (F.5.1)."""

from machine import I2C, SPI, Pin

i2c = I2C(0, scl=Pin(13), sda=Pin(12), freq=50000, timeout=200000)
for label, fn in (("raw4", lambda: i2c.readfrom(0x18, 4)), ("reg06", lambda: i2c.readfrom_mem(0x18, 0x06, 2)),
                  ("reg07", lambda: i2c.readfrom_mem(0x18, 0x07, 2)), ("reg0f", lambda: i2c.readfrom_mem(0x18, 0x0F, 1))):
    try:
        print("SUM dev18 %s=%s" % (label, fn().hex()))
    except OSError as e:
        print("SUM dev18 %s raised %r" % (label, e))
i2c.deinit()
try:
    print("SUM deinit i2c0 then scan=%s (a list means deinit was a no-op)" % [hex(a) for a in i2c.scan()])
except Exception as e:
    print("SUM deinit i2c0 then scan raised %r" % e)
spi = SPI(0, baudrate=1000000, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
cs = Pin(5, Pin.OUT, value=1)
spi.deinit()
try:
    buf = bytearray(4)
    cs(0)
    spi.write(b"\x9f")
    spi.readinto(buf)
    cs(1)
    print("SUM deinit spi0 then rdid=%s (an answer means deinit was a no-op)" % buf.hex())
except Exception as e:
    cs(1)
    print("SUM deinit spi0 then transfer raised %r" % e)
print("DONE=1")
