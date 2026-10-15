"""Isolated-driver device script: a reset-reason record that is not valid - a non-magic word in mem_backup(0)'s magic
slot, then machine.reset() - which the next boot must read as code 0. STATE="valid_record_wait" writes a valid record
(code 3) instead and waits, fed, for the operator's RUN-pin reset; no flash write either way, the facts first."""

import machine

from asy_system_service import write_reset_record

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import fact
    from _shared.watchdog import arm, fed_wait_ms
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

_NOT_MAGIC = 0x12345678  # neither asy_system_service.py's record magic nor 0 (the cleared slot)
# asy_system_service.py's _RR_REBOOT: a const() whose name starts with "_" is no module global on MicroPython, so it
# cannot be imported and is restated here.
_RR_REBOOT = 3
# @tunable l4.reset_code_invalid_record_run_wait_s = 60
_RUN_WAIT_S = 60


def _invalid_record_reset() -> None:
    record = machine.mem_backup(0)
    record[0] = _NOT_MAGIC
    fact("invalid_record", [record[0], record[1], record[2]])
    print("RESET NOW")
    machine.reset()


def _main() -> None:
    wdt = arm()
    state = BENCH.get("STATE", "invalid")
    fact("state", state)
    if state == "valid_record_wait":
        write_reset_record(_RR_REBOOT)  # magic last, as every intended reset writes it
        record = machine.mem_backup(0)
        fact("valid_record", [record[0], record[1], record[2]])
        print("PRESS_RUN_NOW")
        fed_wait_ms(wdt, _RUN_WAIT_S * 1000)  # a RUN-pin reset ends the run inside this wait
        fact("run_not_pressed", _RUN_WAIT_S)
    _invalid_record_reset()


_main()
