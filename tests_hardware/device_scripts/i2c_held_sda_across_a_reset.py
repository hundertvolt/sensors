"""Isolated-driver device script: holds SDA as i2c_held_sda_recovery.py does, then resets the board with the line still
held - mode "machine_reset" by machine.reset(), mode "watchdog" by starving the watchdog - for the next production boot
to meet. Both reset-reason regions are cleared first, so that boot reads an unrecorded reset; no register is written."""

import time

import machine

# @include _shared/facts.py
# @include _shared/watchdog.py
# @include _shared/held_sda.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact
    from _shared.held_sda import _hold_sda_low, _target, _wrapper
    from _shared.watchdog import arm
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

_MODES = ("machine_reset", "watchdog")
_FLUSH_MS = 200  # the facts leave rp2's USB queue before machine.reset() cuts it, as an immediate reset can lose them
_STARVE_STEP_MS = 100


def _main() -> None:
    wdt = arm()
    mode = BENCH.get("mode", "machine_reset")
    fact("mode", mode)
    known = BENCH["addresses"].values()
    buses = sorted(b for b in BENCH["bus"] if b.startswith("i2c"))
    fact("answering", {b: [a for a in _wrapper(BENCH["bus"][b]).scan() or [] if a in known] for b in buses})
    target = _target(BENCH) if mode in _MODES else None
    if target is None:
        fact("held", None)
        done()
        return
    bus_id, _i2c, _scan, address = target
    for region in (0, 1):  # the harness's Ctrl-C recorded 21 there: cleared, as begin_boot() clears a record it read
        words = machine.mem_backup(region)
        for i in range(len(words)):
            words[i] = 0
    wdt.feed()  # the last feed: the watchdog mode starves it from here
    fact("held", {"bus": bus_id, "address": address, "sda_low": _hold_sda_low(BENCH["bus"][bus_id], address)})
    if mode == "machine_reset":
        time.sleep_ms(_FLUSH_MS)
        machine.reset()
    while True:  # unfed: the watchdog resets the board within one period of the feed above
        time.sleep_ms(_STARVE_STEP_MS)


_main()
