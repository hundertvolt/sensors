import asyncio
from asy_uart import AsyUART, CRC16
from asy_uart_comm import UART_Comm
# from asy_uart_comm_failtest import UART_Comm as UART_Fail
import struct

from asy_bsec_driver_all import BSEC_UART 

bsec = BSEC_UART(0, 16, 17, baudrate=115200, rxbuf=64, txbuf=64, payload_size=48, timeout=1000, debug=True)

state = bytearray(b'\x02\x00\x05\x02\xbd\x01\x00\x00\x00\x00\x00\x00\xc5\x00\x00\x004\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\x02\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\xe1D\x00\x00\xe1D\x01\x18\x00\x02\x00\x00\x00HB\x00\x00HB\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1b\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0c\x00\t\x00\xff\xff\xff\xff\xff\xff\xff\x7f\x08\x00\n\x00\x00\x00\x00\x00:\x00\x0b\x00\xf5\xbbDH\xab[\xbdK\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00f\x8f\x00\x00')

print(asyncio.run(bsec.setup(13)))
#print(asyncio.run(bsec.get_bsec_state()))
#print(asyncio.run(bsec.get_measurements()))
#print(asyncio.run(bsec.set_bsec_state(state)))
#print(asyncio.run(bsec.get_system_status()))
print(asyncio.run(bsec.start_measurement()))
print(asyncio.run(bsec.set_temp_comp(3.4)))
#print(asyncio.run(bsec.reset()))

#crc16 = CRC16()

#foo = 0

#uart0 = AsyUART(0, 16, 17, baudrate=115200, rxbuf=64, txbuf=64, crc=crc16)
#comm0 = UART_Comm(uart0, payload_size=48, timeout=2500, debug=True)

async def writebytes():
    ba="SendString"
    bae=bytearray(ba, "UTF-8")
    bae += bytearray(b'\x00\x00\x00\x00')
    #bae = bytearray(b'\x00\x10\x02\x30\x45\x0a\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    print("Send0")
    async with uart0 as uart:
        await uart.writefrom(bae, 10)
    

# asyncio.run(writebytes())

async def readbytes():
    print("start")
    while True:
        async with uart0 as uart:
            rec = await uart.read()
        print(rec)
        
# asyncio.run(readbytes())


async def sendbytes():
    print("Sending...")
    ba="SendString"
    bae=bytearray(ba, "UTF-8")
    async with uart0 as uart:
        msg = comm0._build_msg(5, 1, payload=bae)
        await comm0._write_with_ack(uart, msg)
        
# asyncio.run(sendbytes())

async def recvbytes():
    print("Reading...")
    async with uart0 as uart:
        foo = await comm0._read_with_ack(uart, wait=True)
        print(foo)
        print("UID = ", foo[0])
        print("CMD = ", foo[1])
        print("SIZE = ", foo[2])
        print("NUM_CHUNKS = ", foo[3])
        print("CUR_CHUNK = ", foo[4])
        
#asyncio.run(recvbytes())


async def listen():
    while True:
        cmd, payload = await comm0.uart_listen()
        print("CMD = ", cmd)
        print("Payload = ", payload)
    
# asyncio.run(listen())

async def listen1():
    ba="Quite a long response! Maybe we will need to split it into several pieces and put them together."
    bae=bytearray(ba, "UTF-8")
    while True:
        cmd, payload = await comm0.uart_listen()
        print("Listen:", cmd, payload)
        if cmd == 0x1b:
            print("Reply to get cmd!")
            print("Listen-Set:", await comm0.uart_set(0x1b, bae))

async def listencancel():
    # asyncio.create_task(listen1())
    print("1")
    await asyncio.sleep(2)
    print("2")
    await comm0.clear()
    print("3")

#asyncio.run(listen1())
# asyncio.run(listencancel())

async def uartset1():
    global foo
    while True:
        if foo == 10:
            ba="Quite a very long long Message! Maybe we will need to split it into several pieces and put them together."
            foo = 0
        else:
            ba="Quite a long long Message! Maybe we will need to split it into several pieces and put them together."
        bae=bytearray(ba, "UTF-8")
        print("Issuing set command!")
        foo += 1
        await comm0.uart_set(0x2d, bae)
    
async def uartset():
    while True:
        ba="Quite a long long Message! Maybe we will need to split it into several pieces and put them together."
        bae=bytearray(ba, "UTF-8")
        print("Issuing set command!")
        await comm0.uart_set(0x2d, bae)


async def uartset_zero():
    while True:
        print("Issuing set command without payload!")
        await comm0.uart_set(0x5f, None)

# asyncio.run(uartset_zero())

async def uartget_zero():
    while True:
        print("Issuing get command!")
        res = await comm0.uart_get(0x3c, exp_size=0)
        print(res)
        
#asyncio.run(uartget_zero())




async def uartget():
    while True:
        print("Issuing get command!")
        res = await comm0.uart_get(0x3b, exp_size=16)
        print(res)
        
#asyncio.run(uartget())

        
async def uart_get_measurements():
    print("Issuing get command!")
    res = await comm0.uart_get(0x20)
    print(len(res))
    (raw_temperature,
     raw_pressure,
     raw_humidity,
     gas_resistance,
     raw_gas_index,
     gas_estimate_1,
     gas_estimate_2,
     gas_estimate_3,
     gas_estimate_4) = struct.unpack("fffffffff", res)
    print("raw_temperature", raw_temperature)
    print("raw_pressure", raw_pressure)
    print("raw_humidity", raw_humidity)
    print("gas_resistance", gas_resistance)
    print("raw_gas_index", raw_gas_index)
    print("gas_estimate_1", gas_estimate_1)
    print("gas_estimate_2", gas_estimate_2)
    print("gas_estimate_3", gas_estimate_3)
    print("gas_estimate_4", gas_estimate_4)
    
#asyncio.run(uart_get_measurements())

async def uart_get_system_state():
    print("Issuing get command!")
    res = await comm0.uart_get(0x22)
    print(len(res))
    (meas_running,
     state_updated,
     last_bsec_error,
     last_sensor_error,
     system_uptime) = struct.unpack("bbbbL", res)
    print("meas_running", meas_running)
    print("state_updated", state_updated)
    print("last_bsec_error", last_bsec_error)
    print("last_sensor_error", last_sensor_error)
    print("system_uptime", system_uptime)
    



async def uart_start_bsec_measurement():
    print("Sending start command!")
    res = await comm0.uart_set(0x30, bytearray())
    print(res)

#asyncio.run(uart_start_bsec_measurement())


async def uart_reset_system():
    print("Sending reset command!")
    res = await comm0.uart_set(0x32, bytearray())
    print(res)

#asyncio.run(uart_reset_system())


async def uart_set_bsec_state():
    state = bytearray(b'\x02\x00\x05\x02\xbd\x01\x00\x00\x00\x00\x00\x00\xc5\x00\x00\x004\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\x02\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\xe1D\x00\x00\xe1D\x01\x18\x00\x02\x00\x00\x00HB\x00\x00HB\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1b\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0c\x00\t\x00\xff\xff\xff\xff\xff\xff\xff\x7f\x08\x00\n\x00\x00\x00\x00\x00:\x00\x0b\x00\xb2\x0e\x17H)\x93\x87KT\x15UK\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf4I\x00\x00')
    res = await comm0.uart_set(0x31, state)
    print(res)
    
#asyncio.run(uart_set_bsec_state())


async def uart_get_bsec_state():
    print("Issuing get command!")
    res = await comm0.uart_get(0x21)
    print(len(res))
    print(res)
    
#asyncio.run(uart_get_bsec_state())


def setCallback(cmdID):
    print("SetCallback with ID", cmdID)
    if cmdID == 0x1A:
        return True, 155
    if cmdID == 0x1B:
        return False, None
    return False, None
    
def getCallback(cmdID):
    print("GetCallback with ID", cmdID)
    b=bytearray([11,12,22,32,42,52,62,72,82,92]*5)
    if cmdID == 0x34:
        return True, b
    if cmdID == 0x22:
        return True, bytearray()
    return False, None

async def listen0():
    while True:
        cmdID, cmdType, payload = await comm0.uart_listen(getCallback, setCallback)
        print("Listen:", cmdID, cmdType, payload)
        


#asyncio.run(listen0())
#asyncio.run(uart_get_system_state())
