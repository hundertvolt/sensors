import sys
sys.path.insert(0, sys.argv[1])
import _sensortask_scenarios as ss
cls = ss._FRAM_FAKE_BY_MAX_SIZE[0x40000]
print(cls, cls.__init__)
import machine
c = cls(0, baudrate=1000000, polarity=0, phase=0, sck=machine.Pin(2), mosi=machine.Pin(3), miso=machine.Pin(4))
print(len(c.memory), c.size, c._addr_width, c.memory is cls._array)
