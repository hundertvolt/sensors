"""Isolated-driver device script: UartLinkExerciser's fram_target wiring (WP3) against the real
MB85RS2MTA chip - records an error via its own .pr, simulates a fresh boot (a new AsyFramManager
against the same chip), and confirms the count survives. Mirrors fram_error_log_roundtrip.py's own
pattern one layer up (through UartLinkExerciser's forwarding, not print_log.py directly). No real
UART peripheral is exercised - only the FRAM-backed logger UartLinkExerciser wires through to."""

import asyncio

import asy_spi_driver
from asy_fram_manager import AsyFramManager
from asy_uart_comm import ROLE_INITIATOR
from asy_uart_link_driver import UartLinkExerciser

HISTORY_LENGTH = 5
TEST_ERRNO = 42


async def _main() -> None:
    spi0 = asy_spi_driver.SPI(0, 2, 3, 4)

    fram_a = AsyFramManager(spi0, 5, max_size=0x40000, debug=None)
    if not await fram_a.setup():
        print("RESULT: FAIL fram_a.setup() failed - real FRAM chip not responding on spi0/cs5")
        return

    # uart=None: this script exercises only the FRAM-backed logger UartLinkExerciser forwards
    # into UART_Comm, never a real transfer, so no real UART peripheral is needed at all.
    exerciser1 = UartLinkExerciser(None, ROLE_INITIATOR, name_ext="fram_log_test", fram=fram_a, history_length=HISTORY_LENGTH, debug=None)
    if type(exerciser1.pr).__name__ != "PrintLogHistoryStore":
        print(f"RESULT: FAIL fram=fram_a did not produce a FRAM-backed logger: got {type(exerciser1.pr).__name__}")
        return

    await exerciser1.pr.setup()
    if not exerciser1.pr.initialized:
        print("RESULT: FAIL exerciser1.pr failed to initialize against the real FRAM chunk")
        return

    await exerciser1.pr.reset()  # deterministic starting state regardless of what a prior run left behind
    await exerciser1.pr.err_s("test error for uart_fram_error_log_roundtrip.py", errno=TEST_ERRNO)

    # Simulate a fresh boot: a brand new AsyFramManager Python object against the same real chip,
    # allocating its own chunk 0 at the same physical address exerciser1's did, and a brand new
    # UartLinkExerciser wired to it exactly the way devices/dev.toml wires the real initiator.
    fram_b = AsyFramManager(spi0, 5, max_size=0x40000, debug=None)
    if not await fram_b.setup():
        print("RESULT: FAIL fram_b.setup() failed - real FRAM chip not responding on second probe")
        return

    exerciser2 = UartLinkExerciser(None, ROLE_INITIATOR, name_ext="fram_log_test", fram=fram_b, history_length=HISTORY_LENGTH, debug=None)
    await exerciser2.pr.setup()
    if not exerciser2.pr.initialized:
        print("RESULT: FAIL exerciser2.pr (simulated fresh boot) failed to initialize - real FRAM read did not succeed")
        return

    log = await exerciser2.get_error_counter()
    entry = log.get(exerciser2.name)
    if entry is None:
        print(f"RESULT: FAIL get_error_counter() returned no entry for {exerciser2.name!r}: {log!r}")
        return

    err_count = entry["ErrCount"]
    err_num = entry["ErrNum"]
    err_type = entry["ErrType"]
    if err_count != 1:
        print(f"RESULT: FAIL restored ErrCount={err_count!r}, expected 1 (real FRAM read did not reflect the recorded error)")
        return
    matched_type = next((t for n, t in zip(err_num, err_type) if n == TEST_ERRNO), None)  # noqa: B905 - MicroPython zip() rejects strict=, same list length by construction
    if matched_type != "E":
        print(f"RESULT: FAIL restored history does not contain errno={TEST_ERRNO} as type 'E': ErrNum={err_num!r} ErrType={err_type!r}")
        return

    print(f"RESULT: PASS restored ErrCount={err_count} ErrNum={err_num} ErrType={err_type}")


asyncio.run(_main())
