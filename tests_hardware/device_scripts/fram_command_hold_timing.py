"""Times one FRAM command envelope and one block operation on the real chip, bus held: the longest
non-yielding stretch must stay under one UART poll floor (SPECIFICATION.md J.6). Writes only at
0x3FF00, above every chunk; never calls get_chunk()."""

import asyncio
import time

import asy_spi_driver
from asy_fram_manager import FRAMManager

_SCRATCH_REGIONS = ((0x3FF00, 0x100),)  # the top 256 B of the 256 KB part, above every chunk
_SCRATCH_ADDR = _SCRATCH_REGIONS[0][0]
_UART_FLOOR_US = 80 * 10 * 1_000_000 // 115_200  # 80 B of 8N1 at 115200 baud (J.6): 6,944 us
_BLOCK_COMMANDS = 4  # a block operation's own command count


async def _main() -> None:
    spi0 = asy_spi_driver.SPI(0, 2, 3, 4)
    fram = FRAMManager(spi0, 5, max_size=0x40000)
    if not await fram.setup():
        print("RESULT: FAIL fram.setup() failed - real chip not responding on spi0/cs5")
        return
    chip = fram.fram
    one = bytearray(1)
    eight = bytearray(8)

    # (a) the synchronous, non-yielding stretches, bus already held.
    async with chip:
        t0 = time.ticks_us()
        w_status = chip.set_values_sync(one, _SCRATCH_ADDR)
        t1 = time.ticks_us()
        r_status = chip.get_values_sync(eight, _SCRATCH_ADDR)
        t2 = time.ticks_us()
    write_us = time.ticks_diff(t1, t0)
    read_us = time.ticks_diff(t2, t1)
    if not await chip.report_set_values(w_status):
        print("RESULT: FAIL the 1-byte write reported a failure status")
        return
    if not await chip.report_get_values(r_status):
        print("RESULT: FAIL the 8-byte read reported a failure status")
        return

    # (b) the bus-lock hold: entry to exit, yields inside it included; every status is judged.
    w_status = r_status = 0
    t3 = time.ticks_us()
    async with chip:
        for _ in range(_BLOCK_COMMANDS):
            w_status |= chip.set_values_sync(one, _SCRATCH_ADDR)
            await asyncio.sleep(0)
            r_status |= chip.get_values_sync(eight, _SCRATCH_ADDR)
            await asyncio.sleep(0)
    hold_us = time.ticks_diff(time.ticks_us(), t3)
    if not await chip.report_set_values(w_status) or not await chip.report_get_values(r_status):
        print("RESULT: FAIL a command inside the timed block operation reported a failure status")
        return

    print(f"HOLD write_us={write_us} read_us={read_us} hold_us={hold_us} uart_floor_us={_UART_FLOOR_US}")
    longest = max(write_us, read_us)
    if longest > _UART_FLOOR_US:
        print(f"RESULT: FAIL longest non-yielding stretch {longest}us exceeds the UART poll floor {_UART_FLOOR_US}us")
        return
    print(f"RESULT: PASS longest non-yielding stretch {longest}us under the UART poll floor {_UART_FLOOR_US}us, bus held {hold_us}us")


asyncio.run(_main())
