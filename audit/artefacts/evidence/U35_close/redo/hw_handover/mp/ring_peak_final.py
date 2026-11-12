"""Final-image receive-ring peak: the shipped main() on dev's own config, both UART links running, each driver's unread
DMA ring bytes read every millisecond from its channel's count (read-only, the driver untouched) for RUN_S; the peak
per ring against its size. main() writes production FRAM chunks: refuses until CONFIRM is set (sed), evidence saved."""

import asyncio
import time

import machine

CONFIRM = False
DEVICE = "dev"
RUN_S = 600
RELOAD, POS_MASK = 0x20000000, 0x1FFFFFFF  # asy_uart_driver.py's _RX_RELOAD and _RX_POS_MASK (consts, not exported)

if not CONFIRM:
    print("SUM ring refused: CONFIRM is False (save errcount and the raw FRAM first)")
    print("DONE=1")
    raise SystemExit

wdt = machine.WDT(timeout=8000)  # main() feeds it from here on
device = __import__("sensortask_" + DEVICE)


def level(drv: object) -> int:
    data, ring = getattr(drv, "_rx_dma", None), getattr(drv, "_ring", None)
    if data is None or ring is None:
        return -1
    return (RELOAD - data.count - drv._rx_pos) & POS_MASK


async def run() -> None:
    asyncio.create_task(device.main(watchdog=wdt))
    await asyncio.sleep(15)  # past the setup batch (the SCD30 reset alone waits 2 s): the rings exist
    names = [n for n in ("uart0", "uart1") if hasattr(device, n)]
    drvs = [getattr(device, n) for n in names]
    peak, laps0 = [0] * len(drvs), [d.rx_overruns for d in drvs]
    samples = 0
    end = time.ticks_add(time.ticks_ms(), RUN_S * 1000)
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        for i, d in enumerate(drvs):
            peak[i] = max(peak[i], level(d))
        samples += 1
        await asyncio.sleep_ms(1)
    for i, n in enumerate(names):
        d = drvs[i]
        print("SUM ring %s size=%d peak=%d overruns=%d samples=%d" % (n, d.rx_ring, peak[i], d.rx_overruns - laps0[i], samples))


asyncio.run(run())
print("DONE=1")
machine.reset()  # ends the session in a hard reset (tests_hardware/README.md); no record: 2 next boot
