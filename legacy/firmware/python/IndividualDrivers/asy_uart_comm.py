import asyncio
import struct
import math
from micropython import const
from asy_uart import AsyUART
from machine import Timer

_CMD_ACK  = const(0x01)
_CMD_GET  = const(0x02)
_CMD_SET  = const(0x04)

_NUM_MSG_FIELDS = const(5)
_MSG_UID = const(0)
_MSG_CMD = const(1)
_MSG_SIZE = const(2)
_MSG_CHUNKS = const(3)
_MSG_CUR_CHUNK = const(4)
_MSG_PAYLOAD = const(5)


# Message format: [UID][CMD][SIZE][CHUNKS][CUR_CHUNK][...Payload...]
class UART_Comm:
    def __init__(self, asy_uart, payload_size=48, timeout=1000, debug=False):
        self.payload_size = payload_size
        self.timeout = timeout
        self.uart = asy_uart
        self.uid = 0
        self.debug = debug
        self.enable_write_timer = Timer()
        self.enable_writing = asyncio.ThreadSafeFlag()
        self.enable_writing.set()
        
    async def clear(self):
         if not await self.uart.cancel_read_timeout():  # must be done outside the with statement in case it's blocked!
            async with self.uart as uart:               # only if nothing was cancelled - otherwise, the timeout return
                await self._clear_buffers(uart)         # will clear the buffers by itself inside the cancelled function!

    async def _clear_buffers(self, device):
        if self.debug: print("Clearing UART buffers")
        self.enable_writing.clear()
        timeout = int(1.5 * self.timeout)
        while True:
            if await device.read(timeout_ms=timeout) is None:
                break
        self.enable_write_timer.init(period=timeout, mode=Timer.ONE_SHOT, callback=lambda b: self.enable_writing.set()) # wait another timeout for write enable
        if self.debug: print("UART buffers cleared!")

    async def uart_listen(self, get_callback, set_callback):  # returns GET or SET, CmdID, content.
        async with self.uart as uart:
            self.enable_write_timer.deinit() # skip timer onĺy in listen mode.
            self.enable_writing.set()        # if peer requests something, it's definitely up again.
            exp_cmd = _CMD_GET | _CMD_SET
            if self.debug: print("uart_listen waiting for new message")
            msg = await self._read_with_ack(uart, wait=True)  # wait infinitely for message to come
            if not self._check_msg(msg, exp_cmd, 1): # expect SET or GET, chunk 1
                if self.debug: print("uart_listen unexpected message command")
                await self._clear_buffers(uart)
                return None, None, None
            cmdID = msg[_MSG_PAYLOAD]
            
            if msg[_MSG_CMD] == _CMD_GET:
                valid, payload = get_callback(cmdID) # call with getID, return validity and payload to be sent (bytearray, can be empty)
                if not valid:
                    if self.debug: print("uart_listen get_callback not valid")
                    await self._clear_buffers(uart)
                    return None, _CMD_GET, None
                if not await self._uart_set_unlocked(uart, cmdID, payload):  # clears buffers by itself if returning False
                    if self.debug: print("uart_listen error in answer to GET")
                    return None, _CMD_GET, None
                return cmdID, _CMD_GET, None

            if msg[_MSG_CMD] == _CMD_SET:
                valid, exp_size = set_callback(cmdID) # call with setID, return validity and expected size (can be None)
                if not valid:
                    if self.debug: print("uart_listen set_callback not valid")
                    await self._clear_buffers(uart)
                    return None, _CMD_SET, None
                if exp_size is None:
                    exp_size = -1
                res, filled = await self._uart_read_get_unlocked(uart, exp_size=exp_size)  # GET process without GET request message; clears buffers by itself if returning None
                if res is None:
                    if self.debug: print("uart_listen error in answer to SET")
                    return None, _CMD_SET, None
                if not filled:
                    return cmdID, _CMD_SET, None
                return cmdID, _CMD_SET, res

    async def uart_get(self, getID, exp_size=None):
        async with self.uart as uart:
            if not await self._uart_request_get_unlocked(uart, getID):
                return None
            if exp_size is None:
                exp_size = -1
            res, filled = await self._uart_read_get_unlocked(uart, exp_size=exp_size)
            del filled  # not required here, only for listen-set
            return res
    
    async def _uart_request_get_unlocked(self, device, getID):
        self._inc_uid() # get new UID for message
        bGetId = bytearray(1)
        bGetId[0] = getID
        msg = self._build_msg(self.uid, _CMD_GET, size=1, chunks=1, cur_chunk=1, payload=bGetId)
        if not await self._write_with_ack(device, msg):
            if self.debug: print("uart_get command write failed!")
            await self._clear_buffers(device)
            return False
        msg = await self._read_with_ack(device, wait=False)
        if not self._check_msg(msg, _CMD_SET, 1): # expect SET as reply to GET, with chunk index 1
            await self._clear_buffers(device)
            return False
        if msg[_MSG_PAYLOAD] != getID:
            if self.debug: print("uart_get getID to setID mismatch!")
            await self._clear_buffers(device)
            return False
        return True
        
    async def _uart_read_get_unlocked(self, device, exp_size=-1):
        exp_chunk = 2  # one chunk always was receiced before, either by the GET->SET answer or the command in the listen mode
        res = bytearray()
        while True:
            msg = await self._read_only(device, wait=False)
            if not self._check_msg(msg, _CMD_SET, exp_chunk): # expect SET as reply to GET
                await self._clear_buffers(device)
                return None, False
            if msg[_MSG_SIZE] == 0: # received empty message
                if (exp_size > 0):  # reject if not don't care or not exactly 0 expected
                    if self.debug: print("uart_get expected message with payload but got empty!")
                    await self._clear_buffers(device)
                    return None, False
                if self.debug: print("uart_get sending ACK for message with no payload")
                if not await self._read_only_ack(device, msg): # ack empty message
                    await self._clear_buffers(device)
                    return None, False
                return res, False
            if (exp_size >= 0) and ((len(res) + msg[_MSG_SIZE]) > exp_size):
                if self.debug: print("uart_get message size too large!")
                await self._clear_buffers(device)
                return None, False
            res += msg[_MSG_PAYLOAD:_MSG_PAYLOAD + msg[_MSG_SIZE]] # add used length of payload
            if msg[_MSG_CUR_CHUNK] == msg[_MSG_CHUNKS]:
                break  # break BEFORE last ack, so ack is only given if final size fits
            if not await self._read_only_ack(device, msg):
                await self._clear_buffers(device)
                return None, False
            exp_chunk += 1
        if (exp_size >= 0) and (len(res) != exp_size):
            if self.debug: print("uart_get message size does not match expected size!")
            await self._clear_buffers(device)
            return None, False
        if not await self._read_only_ack(device, msg): # last ack for last chunk, only if size fits
            await self._clear_buffers(device)
            return None, False
        return res, True
        
    async def uart_set(self, setID, payload):
        async with self.uart as uart:
            return await self._uart_set_unlocked(uart, setID, payload)
    
    async def _uart_set_unlocked(self, device, setID, payload):
        if payload is None:
            payload = bytearray(0)
        num_chunks = math.ceil(len(payload) / self.payload_size) + 1  # +1 --> first payload = setID
        if num_chunks < 2: num_chunks = 2    # add one chunk (empty, just for ACK feedback) if message without payload
        if num_chunks > 0xFF: # 16bit payload field
            if self.debug: print("uart_set payload size too large!")
            await self._clear_buffers(device)
            return False
        self._inc_uid() # get new UID for message
        bSetId = bytearray(1)
        bSetId[0] = setID
        cur_chunk = 1
        msg = self._build_msg(self.uid, _CMD_SET, size=1, chunks=num_chunks, cur_chunk=cur_chunk, payload=bSetId)
        while True:
            if not await self._write_with_ack(device, msg):
                if self.debug: print("uart_set write failed!")
                await self._clear_buffers(device)
                return False
            if cur_chunk >= num_chunks:
                if self.debug: print("uart_set successful!")
                return True
            self._inc_uid()  # get new UID for message
            cur_chunk += 1
            size = self.payload_size if len(payload) >= self.payload_size else len(payload) # determine used payload size
            msg = self._build_msg(self.uid, _CMD_SET, size=size, chunks=num_chunks, cur_chunk=cur_chunk, payload=payload[:size])
            payload = payload[size:] # cut sent chunk from remaining payload

    def _inc_uid(self):
        self.uid = 0 if self.uid >= 0xFE else self.uid + 1

    def _build_msg(self, uid, cmd, size=0, chunks=1, cur_chunk=1, payload=bytearray()):
        msg = bytearray(_NUM_MSG_FIELDS)
        msg[_MSG_UID] = uid
        msg[_MSG_CMD] = cmd
        msg[_MSG_SIZE] = size
        msg[_MSG_CHUNKS] = chunks
        msg[_MSG_CUR_CHUNK] = cur_chunk
        msg += payload # add payload
        msg += bytearray(self.payload_size - len(payload)) # length padding
        return msg
        
    def _check_msg(self, msg, exp_cmd, exp_chunk):
        if msg is None:
            if self.debug: print("Invalid message!")
            return False
        if not (msg[_MSG_CMD] & exp_cmd):
            if self.debug: print("Unexpected command ID!")
            return False
        if msg[_MSG_CUR_CHUNK] > msg[_MSG_CHUNKS]:
            if self.debug: print("Chunk index too high!")
            return False
        if msg[_MSG_CUR_CHUNK] != exp_chunk:
            if self.debug: print("Unexpected chunk ID!")
            return False
        if not (0 <= msg[_MSG_SIZE] <= self.payload_size):
            if self.debug: print("Invalid payload size!")
            return False
        return True
        
    async def _write_with_ack(self, device, msg):
        if self.debug: print("wait write enable")
        await self.enable_writing.wait()  # wait for write enable
        if self.debug: print("write enabled!")
        if not await device.write(msg):
            if self.debug: print("Could not send write command!")
            return False
        res = await device.read_until_complete(_NUM_MSG_FIELDS + self.payload_size,
                                               start_timeout_ms=self.timeout,
                                               timeout_ms=self.timeout)            
        if res is None:
            if self.debug: print("No or invalid response for write command!")
            return False
        if res[_MSG_CMD] == _CMD_ACK: # message is ACK as expected
            if res[_MSG_UID] == msg[_MSG_UID]: # message is answer to sent message
                if self.debug: print("Write command successful!")
                self.enable_writing.set() # set ready only if successful
                return True
            if self.debug: print("Wrong UID response in write command!")
            return False
        else:
            if self.debug: print("Unexpected message type in write command!")
            return False    

    async def _read_with_ack(self, device, wait=True):
        res = await self._read_only(device, wait=wait)
        if res is None:
            return None
        if not await self._read_only_ack(device, res):
            return None
        return res
        
    async def _read_only(self, device, wait=True):  # read_with_ack -> read part
        timeout = -1 if wait else self.timeout
        res = await device.read_until_complete(_NUM_MSG_FIELDS + self.payload_size,
                                               start_timeout_ms=timeout,
                                               timeout_ms=self.timeout)            
        if res is None:
            if self.debug: print("No or invalid input for read command!")
            return None
        if self.debug: print("New message received in read command!")
        return res
    
    async def _read_only_ack(self, device, res):   # read_with_ack -> ACK part
        msg = self._build_msg(res[_MSG_UID], _CMD_ACK) # ACK
        if not await device.write(msg):
            if self.debug: print("Could not send ACK message in write command!")
            return False
        return True

