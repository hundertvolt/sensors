"""Isolated-driver device script, phase 2 of 2 - runs after the board comes back from the reset
fram_error_log_reset_race_seed_and_race.py raced against an in-flight error-log chunk write. Proves
the restored history is ALL-OR-NOTHING (never partial, never garbage) and the chunk is usable again."""

import asyncio

import asy_spi_driver
from asy_fram_manager import AsyFramManager
from print_log import make_logger

HISTORY_LENGTH = 10
SEEDED_ERRNO = 5
RACED_ERRNO = 6
POST_RECOVERY_ERRNO = 7
LOG_NAME = "ERRRACE"

# The only three outcomes a reset landing mid-chunk-write may leave behind. Losing the whole history
# is accepted behavior, not a defect (project owner's call, 2026-09-11): an interrupted chunk write
# leaves a status byte at _STATUS_BUSY, PrintLogHistoryStore.setup()'s _read() then fails and its
# _write() fallback stores the empty ring. What must never happen is a PARTIAL or garbled restore -
# that would mean the dual-block + CRC + busy-flag protocol had failed at its actual job.
_ACCEPTED: "tuple[list[int], ...]" = ([], [SEEDED_ERRNO] * 3, [SEEDED_ERRNO] * 3 + [RACED_ERRNO])


async def _main() -> None:
    spi0 = asy_spi_driver.SPI(0, 2, 3, 4)
    fram = AsyFramManager(spi0, 5, max_size=0x40000, debug=None)
    if not await fram.setup():
        print("RESULT: FAIL fram.setup() did not succeed after the reset - device not found?")
        return

    # Same two objects in the same order as the seed script, so this addresses the same chunk.
    store = make_logger(fram, history_length=HISTORY_LENGTH, debug=None, name=LOG_NAME)
    await store.setup()
    if not store.initialized:
        print("RESULT: FAIL PrintLogHistoryStore.setup() did not initialize after the reset")
        return

    log = await store.get_log()
    entry = log[LOG_NAME]
    recovered = [n for n, t in zip(entry["ErrNum"], entry["ErrType"]) if t == "E"]  # noqa: B905 - MicroPython zip() rejects strict=
    warnings = [t for t in entry["ErrType"] if t == "W"]
    if recovered not in _ACCEPTED:
        print(f"RESULT: FAIL restored history is neither intact nor cleanly empty: {recovered} (ErrCount {entry['ErrCount']})")
        return
    if warnings:
        print(f"RESULT: FAIL restored history grew warning entries out of nowhere: {entry['ErrType']}")
        return
    if entry["ErrCount"] != len(recovered):
        print(f"RESULT: FAIL restored ErrCount {entry['ErrCount']} disagrees with the {len(recovered)} restored entries")
        return

    # The chunk must be writable again afterwards - a reset-wedged chunk that stays unreadable
    # forever would be a real defect even under the accepted-loss rule above.
    await store.err_s("post-recovery", errno=POST_RECOVERY_ERRNO)
    after = await store.get_log()
    tail = [n for n, t in zip(after[LOG_NAME]["ErrNum"], after[LOG_NAME]["ErrType"]) if t == "E"]  # noqa: B905 - MicroPython zip() rejects strict=
    # `recovered + [...]`, not `[*recovered, ...]`: MicroPython has no iterable unpacking inside a
    # list display, only in an assignment target - the star form is a runtime SyntaxError on target
    # and neither ruff nor mypy sees it (caught by the real board, 2026-09-11).
    if tail != recovered + [POST_RECOVERY_ERRNO]:
        print(f"RESULT: FAIL the chunk did not accept a fresh entry after the reset: {tail}")
        return

    outcome = "empty (interrupted write, accepted loss)" if not recovered else f"intact ({len(recovered)} entries)"
    print(f"RESULT: PASS restored history is all-or-nothing - {outcome} - and the chunk takes new entries again")


asyncio.run(_main())
