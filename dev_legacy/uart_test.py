import asyncio
from asy_uart import AsyUART, CRC16
from asy_uart_comm import UART_Comm
#from asy_uart_comm_failtest import UART_Comm as UART_Fail
from machine import Timer

crc16 = CRC16()

uart0 = AsyUART(0, 0, 1, baudrate=115200, rxbuf=512, txbuf=256, crc=crc16)
uart1 = AsyUART(1, 8, 9, baudrate=115200, rxbuf=512, txbuf=256, crc=crc16)
comm1 = UART_Comm(uart1, debug=True)
comm0 = UART_Comm(uart0, debug=True)



async def wr0():
    b0=bytearray([0,1,2,3,4,5,6,7,8,9,0,0])
    #b0 = bytearray(b'\x00\x01\x02\x03\x04\x05')
    #b1 = bytearray(b'\x06\x07\x08\t\x88\x01')
    while True:
        print("Send0")
        async with uart0 as uart:
            await uart.writefrom(b0, 10)
        await asyncio.sleep_ms(400)
    #    print("Send1")
    #    async with uart0 as uart:
    #        await uart.write(b1)
    #    await asyncio.sleep_ms(400)

async def rd1():
    buf=bytearray(12)
    while True:
        async with uart1 as uart:
            #print("Getting:", await uart.read_until_complete(10, start_timeout_ms=1000, timeout_ms=500))
            #print(await uart.read())
            l = await uart.readinto_until_complete(buf, 10, start_timeout_ms=1000, timeout_ms=500)
            print(l)
            print(buf[0:l])


async def set0():
    while True:
        b=bytearray([0,1,2,3,4,5,6,7,8,9,0,1,2,3,4,5,6,7,8,9,0,1,2,3,4,5,6,7,8,9,0,1,2,3,4,5,6,7,8,9])
        print("Set:", await comm0.uart_set(0x40, bytearray(1)))
        await asyncio.sleep(2)
        
async def get0():
    while True:
        print("Get:", await comm0.uart_get(0x34))
        await asyncio.sleep(2)

def setCallback(cmdID):
    print("SetCallback with ID", cmdID)
    if cmdID == 0x40:
        return True, 0
    return False, None
    
def getCallback(cmdID):
    print("GetCallback with ID", cmdID)
    b=bytearray([11,12,22,32,42,52,62,72,82,92]*5)
    if cmdID == 0x34:
        return True, bytearray(1)
    return False, None

async def listen1():
    b=bytearray([0,1,2,3,4,5,6,7,8,9]*2)
    while True:
        cmdID, cmdType, payload = await comm1.uart_listen(getCallback, setCallback)
        print("Listen:", cmdID, cmdType, payload)

async def main():
    evtloop = asyncio.get_event_loop()
    print("Start")
    comm0.clear()
    comm1.clear()
    #evtloop.create_task(wr0())
    #evtloop.create_task(rd1())
    evtloop.create_task(listen1())
    evtloop.create_task(get0())
    #evtloop.create_task(set0())

    while True:
        await asyncio.sleep(1)

asyncio.run(main())