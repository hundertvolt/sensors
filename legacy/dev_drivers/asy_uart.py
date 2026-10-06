import time
import asyncio
import select
import struct
from machine import UART, Pin

class AsyUART:
    def __init__(self, uart_id, tx, rx,
                 baudrate=9600, bits=8, parity=None, stop=1, rxbuf=256, txbuf=256,
                 timeout=0, timeout_char=1, invert=0, poll_wait_ms=0,
                 crc=None):
        self.uart = UART(uart_id, baudrate=baudrate,
                         tx=Pin(tx),
                         rx=Pin(rx),
                         bits=bits,
                         parity=parity,
                         stop=stop,
                         rxbuf=rxbuf,
                         txbuf=txbuf,
                         timeout=timeout,
                         timeout_char=timeout_char,
                         invert=invert)
        self.poller = select.poll()
        self.poller.register(self.uart, select.POLLIN | select.POLLOUT)
        self.poll_wait_ms = poll_wait_ms
        self.uart_lock = asyncio.Lock()
        self.cancel = False
        self.cancelled = asyncio.Event()
        if crc is None:
            self.crc = CRC_Pass()
        else:
            self.crc = crc
            
    async def cancel_read_timeout(self):
        if not self.uart_lock.locked():  # nothing to cancel if not in use
            return False
        self.cancel = True
        await self.cancelled.wait()
        return True
            
    async def __aenter__(self) -> "AsyUART":
        await self.uart_lock.acquire()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[type]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
        ) -> bool:
        try:
            self.uart_lock.release()
        except RuntimeError:   # in case it's already released somehow
            pass
        return False
        
    async def ready(self, mask, timeout_ms=-1):
        self.cancel = False
        self.cancelled.clear()
        t0 = time.ticks_ms()
        while True:
            res = self.poller.ipoll(0)
            for sock, event in res:
                if (event & mask):
                    return True
            if ( self.cancel or
                 ( (timeout_ms > 0) and
                   (time.ticks_diff(time.ticks_ms(), t0) > timeout_ms) ) ):  # timeout or cancel wait time
                self.cancel = False
                self.cancelled.set()
                return False
            await asyncio.sleep_ms(self.poll_wait_ms) # waittime before re-check poll
            
    async def read(self, nbytes=None, timeout_ms=-1):
        if not self.uart_lock.locked():   # only use inside a async with statement!
            return None
        if await self.ready(select.POLLIN, timeout_ms=timeout_ms):
            if nbytes is None:
                return self.uart.read()
            return self.uart.read(nbytes)
        return None
    
    async def read_until_complete(self, nbytes, start_timeout_ms=-1, timeout_ms=-1):
        if not self.uart_lock.locked():   # only use inside a async with statement!
            return None
        timeout = start_timeout_ms   # wait time for first message part
        msg = bytearray()
        nbytes += self.crc.length()
        while len(msg) < nbytes:
            if await self.ready(select.POLLIN, timeout_ms=timeout):
                add = self.uart.read(nbytes - len(msg))
                if add is None:
                    return None
                msg += add
                timeout = timeout_ms # if message started and is not complete, use regular timeout for following parts
            else:
                return None # Select ran into timeout
        msg = await self.crc.check(msg)  # CRC check
        return msg

    async def readinto(self, buf, nbytes=None, timeout_ms=-1):
        if not self.uart_lock.locked():   # only use inside a async with statement!
            return None
        if await self.ready(select.POLLIN, timeout_ms=timeout_ms):
            if nbytes is None:
                return self.uart.readinto(buf)
            return self.uart.readinto(buf, nbytes)
        return None
    
    async def readinto_until_complete(self, buf, nbytes, start_timeout_ms=-1, timeout_ms=-1):
        if not self.uart_lock.locked():   # only use inside a async with statement!
            return None
        timeout = start_timeout_ms   # wait time for first message part
        size = 0
        nbytes += self.crc.length()
        if nbytes > len(buf):
            return None
        buf_mv = memoryview(buf)
        while size < nbytes:
            if await self.ready(select.POLLIN, timeout_ms=timeout):
                nb = self.uart.readinto(buf_mv[size:], nbytes - size)
                if nb is None:
                    return None
                size += nb
                timeout = timeout_ms  # if message started and is not complete, use regular timeout for following parts
            else:
                return None  # Select ran into timeout
        size = await self.crc.checkfrom(buf_mv, size)
        return size  # allover number of bytes
    
    async def readline(self, timeout_ms=-1):
        if not self.uart_lock.locked():   # only use inside a async with statement!
            return None
        if await self.ready(select.POLLIN, timeout_ms=timeout_ms):
            return self.uart.readline()
        return None

    async def readline_until_complete(self, start_timeout_ms=-1, timeout_ms=-1):
        if not self.uart_lock.locked():   # only use inside a async with statement!
            return None
        timeout = start_timeout_ms   # wait time for first message part
        msg = bytearray()
        while True:
            if await self.ready(select.POLLIN, timeout_ms=timeout):
                add = self.uart.readline() # reads until \n or buffer empty
                if add is None:
                    return None
                msg += add
                if msg[-1] == 10:     # b'10 = "\n" means really end of the line  
                    break
                timeout = timeout_ms # if message started and is not complete, use regular timeout for following parts
            else:
                return None # Select ran into timeout
        return msg

    async def write(self, msg):  # write bytearray until complete
        if self.uart_lock.locked():   # only use inside a async with statement!
            msg = await self.crc.add(msg)
            if await self.ready(select.POLLOUT):
                self.uart.write(msg)
                return True
        return False
    
    async def writefrom(self, buf, size):  # write buffer content up to size
        if self.uart_lock.locked():   # only use inside a async with statement!
            buf_mv = memoryview(buf)
            crcsize = await self.crc.addinto(buf_mv, size)
            if crcsize is None:
                return False
            if await self.ready(select.POLLOUT):
                self.uart.write(buf_mv[0:crcsize])
                return True
        return False
    
# *** CRC Definitions ***

_CRCPASS_LENGTH = const(0)
class CRC_Pass:    
    def __init__(self):
        pass
    
    def length(self):
        return _CRCPASS_LENGTH
    
    async def add(self, bytearr):
        return bytearr
    
    async def check(self, bytearr):
        return bytearr
    
    async def addinto(self, buf_mv, size):
        return size
    
    async def checkfrom(self, buf_mv, size):
        return size


_CRC16_LENGTH = const(2)
class CRC16:
    def __init__(self, preset=0xFFFF, poly=0x1021):
        self.preset = preset
        self.poly = poly
        
    def length(self):
        return _CRC16_LENGTH

    async def _crc16(self, bytearr):
        crc = self.preset
        for c in bytearr:
            crc = crc ^ c
            for j in range(8):
                if (crc & 1) == 0:
                    crc = crc >> 1
                else:
                    crc = crc >> 1
                    crc = crc ^ self.poly
            await asyncio.sleep(0)  # opportunity for other tasks to run after each byte
        return bytearray(struct.pack("H", crc))

    async def add(self, bytearr):
        crc = await self._crc16(bytearr)
        return bytearr + crc
    
    async def check(self, bytearr):
        crc = await self._crc16(bytearr)
        if struct.unpack("H", crc)[0] == 0:
            return bytearr[0:len(bytearr) - _CRC16_LENGTH]
        return None
    
    async def addinto(self, buf_mv, size):  # expects memoryview from buffer
        if len(buf_mv) < (size + _CRC16_LENGTH):  # buffer must be sufficient for CRC
            return None
        crc = await self._crc16(buf_mv[0:size])
        buf_mv[size:size + _CRC16_LENGTH] = crc
        return size + _CRC16_LENGTH
    
    async def checkfrom(self, buf_mv, size):  # expects memoryview from buffer
        crc = await self._crc16(buf_mv[0:size])
        if struct.unpack("H", crc)[0] == 0:
            return size - _CRC16_LENGTH
        return None
        