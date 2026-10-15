"""Isolated-driver device script: forces a soft-Timer callback drop - twelve 1 ms periodic timers armed back to back,
then three straight-line 900 us busy-waits the VM drains nothing through, so more callbacks fall due than the
scheduler queue holds (SPECIFICATION.md Part F.1) - counts the drop, then checks every timer fires again."""

import time

import machine

# @include _shared/facts.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable

    from _shared.facts import done, fact
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

_N_TIMERS = 12  # more than the scheduler's depth (BENCH["depth"]), so a drop is forced, never hoped for
# @tunable l3.scheduler_saturation_drop_timer_period_ms = 1
_TIMER_PERIOD_MS = 1
# @tunable l3.scheduler_saturation_drop_busy_step_us = 900
_BUSY_STEP_US = 900
# @tunable l3.scheduler_saturation_drop_heal_window_ms = 500
_HEAL_WINDOW_MS = 500

_fire_counts = [0] * _N_TIMERS


def _make_cb(i: int) -> "Callable[[machine.Timer], None]":
    def _cb(_t: "machine.Timer") -> None:
        _fire_counts[i] += 1

    return _cb


_timers = [machine.Timer() for _ in range(_N_TIMERS)]
try:
    start = time.ticks_us()
    for i, t in enumerate(_timers):
        t.init(period=_TIMER_PERIOD_MS, callback=_make_cb(i))
    arming_span_us = time.ticks_diff(time.ticks_us(), start)
    # Straight-line, no branch between them: the VM runs no scheduled callback inside sleep_us().
    time.sleep_us(_BUSY_STEP_US)
    time.sleep_us(_BUSY_STEP_US)
    time.sleep_us(_BUSY_STEP_US)
    counts_busy = list(_fire_counts)
    # The heal window: the loop free to drain the queue again, every timer must fire at least once more.
    time.sleep_ms(_HEAL_WINDOW_MS)
    counts_heal = list(_fire_counts)
finally:
    for t in _timers:
        t.deinit()
fact("n_timers", _N_TIMERS)
fact("depth", BENCH["depth"])
fact("arming_span_us", arming_span_us)
fact("counts_busy", counts_busy)
fact("counts_heal", counts_heal)
fact("dropped", sum(1 for c in counts_busy if c == 0))
fact("all_self_healed", all(counts_heal[i] > counts_busy[i] for i in range(_N_TIMERS)))
done()
