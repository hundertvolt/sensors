"""Isolated-driver device script: a ResetErrors landing before a FRAM-backed logger's own
pr.setup() has run must still stick - the reset is persisted and the later setup() must not restore
the old history over it. BACKLOG.md #16, on the real chip rather than a fake one."""

import asyncio

import asy_spi_driver
from asy_fram_manager import AsyFramManager
from print_log import make_logger

HISTORY_LENGTH = 10
SEEDED_ERRNO = 5
LOG_NAME = "ERRBOOT"


async def _main() -> None:
    spi0 = asy_spi_driver.SPI(0, 2, 3, 4)
    fram = AsyFramManager(spi0, 5, max_size=0x40000, debug=None)
    if not await fram.setup():
        print("RESULT: FAIL fram.setup() failed - real FRAM chip not responding on spi0/cs5")
        return

    store = make_logger(fram, history_length=HISTORY_LENGTH, debug=None, name=LOG_NAME)
    await store.setup()
    if not store.initialized:
        print("RESULT: FAIL could not initialize the error-log chunk on the real chip")
        return
    await store.reset()  # this chunk is real persistent storage - start from a known baseline
    for _ in range(3):
        await store.err_s("seeded", errno=SEEDED_ERRNO)
    seeded = (await store.get_log())[LOG_NAME]
    if seeded["ErrType"].count("E") != 3:
        print(f"RESULT: FAIL could not seed a real 3-entry history to reset against ({seeded!r})")
        return

    # The boot window itself: a fresh logger over the same chunk, bytes still on the chip, its own
    # pr.setup() not yet run (on the real system that call lives inside read_loop()'s _init_*()).
    # make_logger() always hands back initialized=False, which is exactly the boot-window state.
    rebooted = make_logger(fram, history_length=HISTORY_LENGTH, debug=None, name=LOG_NAME)
    await rebooted.reset()  # the PUT lands here
    if not rebooted.initialized:
        print("RESULT: FAIL the reset write never reached the real chip, so nothing was persisted")
        return
    await rebooted.setup()  # ... and only now does the task get there

    after = (await rebooted.get_log())[LOG_NAME]
    if after["ErrCount"] != 0 or any(t != "N" for t in after["ErrType"]):
        print(f"RESULT: FAIL setup() restored the pre-reset history over a reset that had been persisted ({after!r})")
        return

    # Third logger, no reset: proves the cleared state really is what is on the chip now, not just
    # what the second object happens to hold in RAM.
    verify = make_logger(fram, history_length=HISTORY_LENGTH, debug=None, name=LOG_NAME)
    await verify.setup()
    persisted = (await verify.get_log())[LOG_NAME]
    if persisted["ErrCount"] != 0 or any(t != "N" for t in persisted["ErrType"]):
        print(f"RESULT: FAIL the chip still holds the pre-reset history ({persisted!r})")
        return

    print("RESULT: PASS a reset issued before the logger's own setup() was persisted to the real chip and survived it")


asyncio.run(_main())
