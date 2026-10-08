"""Isolated-driver device script: PrintLogHistoryStore (asy_print_log.py), the FRAM-backed error/
warning history every FRAM-chunk-owning module uses, against the real MB85RS2MTA chip. Records an
error via err_s(), simulates a fresh boot (a new FRAMManager), and confirms get_log() reads it back from the chip."""

import asyncio

import asy_spi_driver
from asy_fram_manager import FRAMManager
from asy_print_log import LogConfig, make_logger

HISTORY_LENGTH = 5
TEST_ERRNO = 42
LOG_NAME = "TEST"


async def _main() -> None:
    spi0 = asy_spi_driver.SPI(0, 2, 3, 4)

    fram_a = FRAMManager(spi0, 5, max_size=0x40000)
    if not await fram_a.setup():
        print("RESULT: FAIL fram_a.setup() failed - real FRAM chip not responding on spi0/cs5")
        return

    pr1 = make_logger(LogConfig(fram_a, HISTORY_LENGTH, None), LOG_NAME)
    await pr1.setup()
    if not pr1.initialized:
        print("RESULT: FAIL pr1 failed to initialize against the real FRAM chunk")
        return

    await pr1.reset()  # deterministic starting state regardless of what a prior run left behind
    await pr1.err_s("test error for fram_error_log_roundtrip.py", errno=TEST_ERRNO)

    # Simulate a fresh boot: a brand new FRAMManager Python object against the same real chip,
    # allocating its own chunk 0 at the same physical address pr1's did.
    fram_b = FRAMManager(spi0, 5, max_size=0x40000)
    if not await fram_b.setup():
        print("RESULT: FAIL fram_b.setup() failed - real FRAM chip not responding on second probe")
        return

    pr2 = make_logger(LogConfig(fram_b, HISTORY_LENGTH, None), LOG_NAME)
    await pr2.setup()
    if not pr2.initialized:
        print("RESULT: FAIL pr2 (simulated fresh boot) failed to initialize - real FRAM read did not succeed")
        return

    log = await pr2.get_log()
    entry = log.get(LOG_NAME)
    if entry is None:
        print(f"RESULT: FAIL get_log() returned no entry for {LOG_NAME!r}: {log!r}")
        return

    # asy_print_log.py's ErrEntry types all three fields exactly (ErrCount int, ErrNum list[int],
    # ErrType list[str]), so the shape needs no isinstance re-check before use here.
    err_count = entry["ErrCount"]
    err_num = entry["ErrNum"]
    err_type = entry["ErrType"]
    if err_count != 1:
        print(f"RESULT: FAIL restored ErrCount={err_count!r}, expected 1 (real FRAM read did not reflect the recorded error)")
        return
    # err_num/err_type both narrow to the same list[int] | list[str] union (get_log()'s one shared
    # value type covers all three keys - see the comment above) - zip()+== sidesteps .index()'s
    # per-overload argument-type mismatch that a bare err_num.index(TEST_ERRNO) would hit.
    matched_type = next((t for n, t in zip(err_num, err_type) if n == TEST_ERRNO), None)  # noqa: B905 - MicroPython zip() rejects strict=, same list length by construction
    if matched_type != "E":
        print(f"RESULT: FAIL restored history does not contain errno={TEST_ERRNO} as type 'E': ErrNum={err_num!r} ErrType={err_type!r}")
        return

    print(f"RESULT: PASS restored ErrCount={err_count} ErrNum={err_num} ErrType={err_type}")


asyncio.run(_main())
