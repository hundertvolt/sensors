import asyncio
import struct
import time
from micropython import const
from asy_fram_driver import FRAM_SPI
from async_manager import TimeCounterManager

_STATUS_UNINIT = const(0x00)
_STATUS_IDLE = const(0x01)
_STATUS_BUSY = const(0x02)
_ADDR_STATUS_1 = const(0)
_ADDR_STATUS_2 = const(1)
_NUM_STATUS_BYTES = const(2)
_CURRENT_TS_BYTES = const(8)
_TS_UNINIT = const(0)

class asy_FRAM_manager():
    def __init__(self, spi_bus: SPI, spi_cs: int, max_size: int=0x2000, debug=False):
        self.size = max_size
        self.allocated_size = 0
        self.debug = debug
        self.pause = False
        self.fram = FRAM_SPI(spi_bus, spi_cs, max_size=self.size, debug=self.debug)

    async def setup(self):
        try:
            await self.fram.setup()
        except:
            return False
        return True

    def set_pause(self, value):
        if self.debug: print("Storage pause set to", value)
        self.pause = value

    def get_pause(self):
        return self.pause

    def get_chunk(self, size, verify=0):
        full_size = 2 * (size + _NUM_STATUS_BYTES)  # memsize + status bytes, 1-redundant
        if self.debug: print("Storage for", size, "bytes requested, allocating", full_size, "bytes allover.")
        if (self.allocated_size + full_size) > self.size:
            if self.debug: print("FRAM out of memory!")
            return None  # out of memory
        chunk = asy_FRAM_chunk(self, self.fram, self.allocated_size, size, verify=verify, debug=self.debug)
        self.allocated_size += full_size
        if self.debug: print("Allocation successful, FRAM now has", self.allocated_size, "Bytes allocated.")
        return chunk

    def get_timestamped_chunk(self, size, ntp_sync_callback, verify=0):
        full_size = (2 * (_CURRENT_TS_BYTES + size + _NUM_STATUS_BYTES))  # timestamp +  memsize + status bytes, 1-redundant
        if self.debug: print("Storage for", size, "bytes and timestamp requested, allocating", full_size, "bytes allover.")
        if (self.allocated_size + full_size) > self.size:
            if self.debug: print("FRAM out of memory!")
            return None  # out of memory
        chunk = asy_FRAM_timestamped_chunk(self, self.fram, self.allocated_size, size, ntp_sync_callback, verify=verify, debug=self.debug)
        self.allocated_size += full_size
        if self.debug: print("Allocation successful, FRAM now has", self.allocated_size, "Bytes allocated.")
        return chunk

class asy_FRAM_timestamped_chunk():
    def __init__(self, fram_mgr, fram, base_addr, size, ntp_sync_callback, verify=0, debug=False):
        self.ntp_sync_callback = ntp_sync_callback
        self.chunk = asy_FRAM_chunk(fram_mgr, fram, base_addr, _CURRENT_TS_BYTES + size, verify=verify, debug=debug)
        self.debug = debug

    async def set_verify(self, value):
        await self.chunk.set_verify(value)

    async def get_verify(self):
        return await self.chunk.get_verify()

    async def get_size(self):
        ts_size = await self.chunk.get_size()
        return ts_size - _CURRENT_TS_BYTES

    async def write(self, data, require_ntp=False, override_pause=False):
        ntp_synced = await self.ntp_sync_callback()
        utc = _TS_UNINIT
        if ntp_synced:
            utc = time.mktime(time.gmtime())
            if self.debug: print("FRAM write timestamp is valid")
        else:
            if self.debug: print("FRAM write timestamp not valid")
            if require_ntp:
                return False, None, False
        ts = struct.pack("Q", utc)
        res = await self.chunk.write(bytearray(ts) + data, override_pause=override_pause)
        return ntp_synced, utc, res

    async def read(self, override_pause=False):
        ts_data = await self.chunk.read(override_pause=override_pause)
        if ts_data is None:
            return None, None, None
        age = None
        ts = struct.unpack("Q", ts_data[0:_CURRENT_TS_BYTES])[0]
        if ts == _TS_UNINIT:
            if self.debug: print("FRAM read data timestamp not valid")
            ts = None
        else:
            if self.debug: print("FRAM read data timestamp is valid")
            ntp_synced = await self.ntp_sync_callback()
            if ntp_synced:
                if self.debug: print("FRAM read current time is valid")
                age = time.mktime(time.gmtime()) - ts
        return ts, age, ts_data[_CURRENT_TS_BYTES:]

    async def clear(self, override_pause=False):
        return await self.chunk.clear(override_pause=override_pause)

    async def get_pause(self):
        return await self.chunk.get_pause()

    async def get_error_counters(self):
        return await self.chunk.get_error_counters()

class asy_FRAM_chunk():
    # data chunk layout:
    # [...Data 0...][Status 0-1][Status 0-2][...Data 1...][Status 1-1][Status 1-2]
    def __init__(self, fram_mgr, fram, base_addr, size, verify=0, debug=False):
        self.fram_mgr = fram_mgr
        self.fram = fram
        self.base_addr = base_addr
        self.size = size
        self.error_noncritical = TimeCounterManager()  # use inherently limited counter here as overall error counter
        self.error_critical = TimeCounterManager()
        self.last_error = -1
        self.verify = verify
        self.verify_counter = 0
        self.debug = debug

    async def set_verify(self, value):
        if self.debug: print("FRAM verification set to", value, "write cycles.")
        self.verify_counter = 0
        self.verify = value

    async def get_verify(self):
        return self.verify

    async def get_size(self):
        return self.size

    async def write(self, data, override_pause=False):
        if (not override_pause) and (self.fram_mgr.get_pause()):
            if self.debug: print("FRAM communication paused, not writing FRAM!")
            return False
        if len(data) != self.size:
            await self.error_critical.increment()
            if self.debug: print("Data size does not match chunk size!")
            return False
        if self.debug: print("Writing block 0 data")
        res = await self._write_chunk(self.base_addr, data)
        if not res:
            await self.error_critical.increment()
            if self.debug: print("Writing block 0 failed!")
            return False
        if self.debug: print("Writing block 1 data")
        res = await self._write_chunk(self.base_addr + self.size + _NUM_STATUS_BYTES, data)
        if not res:
            await self.error_critical.increment()
            if self.debug: print("Writing block 1 failed!")
            return False
        if self.verify > 0:
            self.verify_counter += 1
            if self.verify_counter >= self.verify:
                self.verify_counter = 0
                if self.debug: print("Verifying written data")
                check_data = await self.read(override_pause=True) # let operation complete if it gets paused meanwhile
                if check_data is None:  # in this case, last_error is set by the failing subfunction
                    await self.error_critical.increment()
                    if self.debug: print("Write verification error while reading!")
                    return False
                if check_data != data:
                    if self.debug: print("Write verification data valid but different from input!")
                    await self.error_critical.increment()
                    self.last_error = 40
                    return False
                if self.debug: print("Write verification successful")
        return True

    async def read(self, override_pause=False):
        if (not override_pause) and (self.fram_mgr.get_pause()):
            if self.debug: print("FRAM communication paused, not reading FRAM!")
            return None
        uninit0, data0 = await self._read_chunk(self.base_addr)  # read first copy
        uninit1, data1 = await self._read_chunk(self.base_addr + self.size + _NUM_STATUS_BYTES) # read second copy
        if data0 is None:  # if first copy is invalid, read second copy
            if uninit0:
                if self.debug: print("Uninitialized data in block 0, using block 1")
            else:
                await self.error_noncritical.increment()
                if self.debug: print("Invalid data in block 0, using block 1")
            if data1 is None:
                if uninit0 and uninit1:
                    if self.debug: print("Uninitialized data in both blocks")
                else:
                    await self.error_noncritical.increment()
                    if self.debug: print("Invalid data in both blocks")
                return None  # none of the copies is valid
            if self.debug: print("Valid data in block 1, overwriting block 0")
            res = await self._write_chunk(self.base_addr, data1)  # if block 1 is valid, overwrite invalid block 0 with valid data
            if not res:
                await self.error_critical.increment()
                if self.debug: print("Writing block 0 failed!")
                return None  # writing failed, means something is really wrong, better do not use data
            if self.debug: print("Data read successfully from block 1")
            return data1
        if self.debug: print("Data read successfully from block 0")
        if data1 is None:  # check block 1 even if block 0 is valid
            await self.error_noncritical.increment()
            if self.debug: print("Invalid data in block 1, overwriting with block 0 data")
            res = await self._write_chunk(self.base_addr + self.size + _NUM_STATUS_BYTES, data0) # write valid data into block 1
            if not res:
                await self.error_critical.increment()
                if self.debug: print("Writing block 1 failed!")
                return None  # writing failed, means something is really wrong, better do not use data
            if self.debug: print("Data read successfully from block 0")
            return data0
        if data0 != data1:
            await self.error_critical.increment()
            self.last_error = 50
            if self.debug: print("Both blocks valid but different data")
            return None
        if self.debug: print("Both blocks valid and data verified")
        return data0

    async def clear(self, override_pause=False):
        if (not override_pause) and (self.fram_mgr.get_pause()):
            if self.debug: print("FRAM communication paused, not clearing FRAM!")
            return False
        res = await self._clear_chunk(self.base_addr)
        if not res:
            await self.error_critical.increment()
            return False
        if self.debug: print("Block 0 cleared")
        res = await self._clear_chunk(self.base_addr + self.size + _NUM_STATUS_BYTES)
        if not res:
            await self.error_critical.increment()
            return False
        if self.debug: print("Block 1 cleared")
        return True

    async def get_pause(self):
        return self.fram_mgr.get_pause()

    async def get_error_counters(self):
        critical = await self.error_critical.get_counter()
        noncritical = await self.error_noncritical.get_counter()
        return critical, noncritical, self.last_error

    async def _write_chunk(self, addr, data):
        async with self.fram as fram:
            try:
                res = await fram.set_values(addr + self.size + _ADDR_STATUS_1, bytearray([_STATUS_BUSY]))
                if not res:
                    self.last_error = 10
                    return False
                res = await fram.set_values(addr + self.size + _ADDR_STATUS_2, bytearray([_STATUS_BUSY]))
                if not res:
                    self.last_error = 11
                    return False
                res = await fram.set_values(addr, data)
                if not res:
                    self.last_error = 12
                    return False
                res = await fram.set_values(addr + self.size + _ADDR_STATUS_1, bytearray([_STATUS_IDLE]))
                if not res:
                    self.last_error = 13
                    return False
                res = await fram.set_values(addr + self.size + _ADDR_STATUS_2, bytearray([_STATUS_IDLE]))
                if not res:
                    self.last_error = 14
                    return False
            except:
                self.last_error = 15
                return False
        return True

    async def _read_chunk(self, addr):
        async with self.fram as fram:
            data = None
            try:
                uninit = False
                res = await fram.get_values(addr + self.size + _ADDR_STATUS_1, addr + self.size + _ADDR_STATUS_1)
                if res is None:
                    self.last_error = 20
                    return False, None
                if res != bytearray([_STATUS_IDLE]):  # check if first byte is free
                    if res != bytearray([_STATUS_UNINIT]):
                        self.last_error = 21
                        if self.debug: print("Read status byte 0 is not idle (0x01) but", res)
                        return False, None
                    uninit = True # no error yet
                res = await fram.set_values(addr + self.size + _ADDR_STATUS_1, bytearray([_STATUS_BUSY]))
                if not res:              # set first byte busy before reading second byte
                    self.last_error = 22
                    return False, None
                res = await fram.get_values(addr + self.size + _ADDR_STATUS_2, addr + self.size + _ADDR_STATUS_2)
                if res is None:
                    self.last_error = 23
                    return False, None
                if res != bytearray([_STATUS_IDLE]):  # check if second byte is free
                    if res != bytearray([_STATUS_UNINIT]):
                        self.last_error = 24
                        if self.debug: print("Read status byte 1 is not idle (0x01) but", res)
                        return False, None
                    if uninit:   # both uninitialized, no content but no error
                        return True, None
                    if self.debug: print("Read status uninit bytes inconsistent!", res)
                    self.last_error = 25
                    return False, None
                res = await fram.set_values(addr + self.size + _ADDR_STATUS_2, bytearray([_STATUS_BUSY]))
                if not res:              # set second byte busy before reading data
                    self.last_error = 26
                    return False, None
                data = await fram.get_values(addr, addr + self.size - 1)
                # after reading data, set both bytes idle again
                res = await fram.set_values(addr + self.size + _ADDR_STATUS_1, bytearray([_STATUS_IDLE]))
                if not res:
                    self.last_error = 27
                    return False, None
                res = await fram.set_values(addr + self.size + _ADDR_STATUS_2, bytearray([_STATUS_IDLE]))
                if not res:
                    self.last_error = 28
                    return False, None
            except:
                self.last_error = 29
                return False, None
        return False, data

    async def _clear_chunk(self, addr):
        async with self.fram as fram:
            try:
                res = await fram.set_values(addr + self.size + _ADDR_STATUS_1, bytearray([_STATUS_UNINIT]))
                if not res:
                    self.last_error = 30
                    return False
                res = await fram.set_values(addr + self.size + _ADDR_STATUS_2, bytearray([_STATUS_UNINIT]))
                if not res:
                    self.last_error = 31
                    return False
                res = await fram.set_values(addr, bytearray([_STATUS_UNINIT] * self.size))
                if not res:
                    self.last_error = 32
                    return False
            except:
                self.last_error = 33
                return False
        return True
