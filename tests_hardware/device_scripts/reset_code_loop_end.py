"""Isolated-driver device script: the frozen boot entry imported again under the board's own config, the loop core's
wait patched to raise KIND (exception: OSError, base: SystemExit) at its first wait after this boot marks BOOT_DONE: the
entry records reset code 22 and returns, and the armed watchdog resets the board; no flash write, no FRAM seeding."""

import asyncio.core as core  # type: ignore[import-not-found]  # noqa: PLR0402 - the loop's own IOQueue; no stub covers it
import errno
import sys

import machine

# @include _shared/facts.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import fact
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py
_BOOT_DONE = int(BENCH.get("BOOT_DONE", "6"))  # the host passes src/asy_system_service.py's value
_KIND = BENCH.get("KIND", "exception")
_original_wait = core.IOQueue.wait_io_event
_this_boot = [False]  # set once this boot's begin_boot() marks a phase below BOOT_DONE: the mark before it is stale


def _wait(queue: object, dt: int) -> None:
    phase = machine.mem_backup(1)[1]
    if phase < _BOOT_DONE:
        _this_boot[0] = True
    elif _this_boot[0]:
        fact("raised_in_phase", phase)
        if _KIND == "base":
            raise SystemExit(3)  # a non-Exception BaseException; rp2 soft-resets on one that reaches pyexec
        raise OSError(errno.EIO)
    _original_wait(queue, dt)


core.IOQueue.wait_io_event = _wait
sys.path.insert(0, ".frozen")  # the frozen entry, never a filesystem main.py, as the entry itself orders its path
import main  # type: ignore[import-not-found]  # noqa: E402, F401 - the frozen boot entry, ended by the planted exception

fact("record", list(machine.mem_backup(0)))  # [magic, code, check, 0]: written before the watchdog's reset
