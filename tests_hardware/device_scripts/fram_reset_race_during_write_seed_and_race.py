"""Isolated-driver device script, phase 1 of 2 (fram_reset_race_during_write_verify_recovery.py is phase 2): seeds a
target between two guards, then fires a real machine.reset() inside the payload transfer of a write to the target, at
the driver's synchronous seam. Run through run_isolated_expect_reset(); its facts and banner come before the reset."""

import asyncio

import machine

import asy_spi_driver
from asy_fram_driver import FRAM_SPI
from asy_print_log import PrintLogHistory

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact
    from _shared.watchdog import arm
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# One region for both phases of the one host test; the guards around the target are never touched by the race.
_SCRATCH_REGIONS = ((0xA000, 0x40),)
_GUARD_BEFORE_ADDR = _SCRATCH_REGIONS[0][0]
_TARGET_ADDR = _GUARD_BEFORE_ADDR + 0x10
_GUARD_AFTER_ADDR = _GUARD_BEFORE_ADDR + 0x20

_GUARD_BEFORE_PATTERN = bytes(range(0x10, 0x20))
_ORIGINAL_TARGET_PATTERN = bytes(range(0x70, 0x80))
_NEW_TARGET_PATTERN = bytes((0xCC,) * 16)  # what the reset-raced write attempts
_GUARD_AFTER_PATTERN = bytes(range(0x30, 0x40))
# @tunable l3.fram_reset_race_during_write_seed_and_race_victim_bound_s = 30.0
_VICTIM_BOUND_S = 30.0
# The line the host waits for: printed right before the raced write, so a run without it never reached the race.
_BANNER = "RESET_RACE_ARMED"


async def _main() -> None:
    wdt = arm()
    raised_in_tasks: list[str] = []
    asyncio.get_event_loop().set_exception_handler(lambda _loop, context: raised_in_tasks.append(repr(context.get("exception"))))
    chip = BENCH["instances"]["fram"]
    bus = BENCH["bus"][chip["bus"]]
    spi = asy_spi_driver.SPI(bus["id"], sck_pin=bus["sck_pin"], mosi_pin=bus["mosi_pin"], miso_pin=bus["miso_pin"])
    fram = FRAM_SPI(spi, chip["cs_pin"], logger=PrintLogHistory(name="FRAMRESETRACE"), max_size=BENCH["fram_max_size"])
    await fram.setup()
    fact("initialized", fram.initialized)
    if not fram.initialized:
        done()
        return
    seeded = []
    for addr, pattern in ((_GUARD_BEFORE_ADDR, _GUARD_BEFORE_PATTERN), (_TARGET_ADDR, _ORIGINAL_TARGET_PATTERN), (_GUARD_AFTER_ADDR, _GUARD_AFTER_PATTERN)):
        async with fram:
            seeded.append(await fram.set_values(pattern, addr_start=addr))
    fact("seeded", seeded)
    fact("system_task_exceptions", raised_in_tasks)
    wdt.feed()
    if not all(seeded):
        done()
        return

    # The reset lands inside the victim's own payload transfer: the CS window does not yield, so this is the one seam.
    spidev = fram._spidev
    original_write_sync = spidev.write_sync

    def resetting_write_sync(buf: "bytes | bytearray | memoryview") -> bool:
        if len(buf) == len(_NEW_TARGET_PATTERN):  # the command buffers around the payload are 1 or 5 bytes
            machine.reset()  # never returns: a real RP2040 reset with CS still asserted
        return original_write_sync(buf)

    async def victim_writer() -> None:
        async with fram:
            await fram.set_values(_NEW_TARGET_PATTERN, addr_start=_TARGET_ADDR)

    print(_BANNER)
    spidev.write_sync = resetting_write_sync  # type: ignore[method-assign]
    try:
        await asyncio.wait_for(victim_writer(), _VICTIM_BOUND_S)
    finally:
        spidev.write_sync = original_write_sync  # type: ignore[method-assign]
    # Reached only when no payload transfer of the expected length came through the seam: nothing was tested.
    fact("reset_fired", False)
    done()


asyncio.run(_main())
