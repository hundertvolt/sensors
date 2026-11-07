import sys
sys.path.append("ext")
import asyncio
from machine import WDT
import asy_uart_comm
import sensortask_dev as m


async def run():
    await m.build_system(watchdog=WDT(timeout=8000))
    for link in (m.uart_link_init, m.uart_link_resp):
        comm = link._comm if hasattr(link, "_comm") else None
        found = [v for v in link.__dict__.values() if hasattr(v, "_max_transfer_bytes")]
        c = found[0]
        got = asy_uart_comm.TransferLimits(c._payload_size, c._timeout, c._chunk_bytes, c._max_transfer_bytes)
        print("limits", got, "== DEFAULT_LIMITS:", got == asy_uart_comm.DEFAULT_LIMITS)
    print("rx ring", [getattr(b, "_rx_ring", None) for b in (m.uart0, m.uart1)][:2])


asyncio.run(run())
