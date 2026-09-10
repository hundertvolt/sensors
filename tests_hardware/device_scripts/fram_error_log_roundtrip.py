"""Isolated-driver device script: PrintLogHistoryStore (print_log.py), the FRAM-backed error/
warning history every FRAM-chunk-owning module uses, against the real MB85RS2MTA chip. Records an
error via err_s(), simulates a fresh boot (a new AsyFramManager), and confirms get_log() reads it back from the chip."""

import asyncio

import asy_spi_driver
from asy_fram_manager import AsyFramManager
from print_log import make_logger

HISTORY_LENGTH = 5
TEST_ERRNO = 42
LOG_NAME = "TEST"


async def _main() -> None:
    spi0 = asy_spi_driver.SPI(0, 2, 3, 4)

    fram_a = AsyFramManager(spi0, 5, max_size=0x40000, debug=None)
    if not await fram_a.setup():
        print("RESULT: FAIL fram_a.setup() failed - real FRAM chip not responding on spi0/cs5")
        return

    pr1 = make_logger(fram_a, history_length=HISTORY_LENGTH, debug=None, name=LOG_NAME)
    await pr1.setup()
    if not pr1.initialized:
        print("RESULT: FAIL pr1 failed to initialize against the real FRAM chunk")
        return

    await pr1.reset()  # deterministic starting state regardless of what a prior run left behind
    await pr1.err_s("test error for fram_error_log_roundtrip.py", errno=TEST_ERRNO)

    # Simulate a fresh boot: a brand new AsyFramManager Python object against the same real chip,
    # allocating its own chunk 0 at the same physical address pr1's did.
    fram_b = AsyFramManager(spi0, 5, max_size=0x40000, debug=None)
    if not await fram_b.setup():
        print("RESULT: FAIL fram_b.setup() failed - real FRAM chip not responding on second probe")
        return

    pr2 = make_logger(fram_b, history_length=HISTORY_LENGTH, debug=None, name=LOG_NAME)
    await pr2.setup()
    if not pr2.initialized:
        print("RESULT: FAIL pr2 (simulated fresh boot) failed to initialize - real FRAM read did not succeed")
        return

    log = await pr2.get_log()
    entry = log.get(LOG_NAME)
    if entry is None:
        print(f"RESULT: FAIL get_log() returned no entry for {LOG_NAME!r}: {log!r}")
        return

    # get_log()'s return type covers all three keys with one int|list[int]|list[str] union (same
    # shape tests/test_asy_ntp_client.py's own _last_err() helper narrows) - isinstance-checked
    # here rather than indexed blind.
    err_count = entry["ErrCount"]
    err_num = entry["ErrNum"]
    err_type = entry["ErrType"]
    if not isinstance(err_count, int) or not isinstance(err_num, list) or not isinstance(err_type, list):
        print(f"RESULT: FAIL get_log() returned unexpected field types: {entry!r}")
        return
    if err_count != 1:
        print(f"RESULT: FAIL restored ErrCount={err_count!r}, expected 1 (real FRAM read did not reflect the recorded error)")
        return
    positions = [i for i, num in enumerate(err_num) if num == TEST_ERRNO]
    if not positions or err_type[positions[0]] != "E":
        print(f"RESULT: FAIL restored history does not contain errno={TEST_ERRNO} as type 'E': ErrNum={err_num!r} ErrType={err_type!r}")
        return

    print(f"RESULT: PASS restored ErrCount={err_count} ErrNum={err_num} ErrType={err_type}")


asyncio.run(_main())
