"""Isolated-driver device script: provokes enough concurrent real Timer IRQs to exceed
MicroPython's fixed-depth scheduler queue (MICROPY_SCHEDULER_DEPTH=8 on rp2, SPECIFICATION.md Part
F.1) and confirms a periodic timer self-heals rather than permanently stopping. Widen BUSY_WAIT_MS if `dropped` comes back 0."""

import time

import machine

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable

N_TIMERS = 10
TIMER_PERIOD_MS = 2
BUSY_WAIT_MS = 100
HEAL_WINDOW_MS = 500

fire_counts = [0] * N_TIMERS


def _make_cb(i: int) -> "Callable[[machine.Timer], None]":
    def _cb(_t: "machine.Timer") -> None:
        fire_counts[i] += 1

    return _cb


timers = [machine.Timer() for _ in range(N_TIMERS)]
for i, t in enumerate(timers):
    t.init(period=TIMER_PERIOD_MS, callback=_make_cb(i))

# Busy-wait with no yield point the scheduler can drain through - starves the queue on purpose.
start = time.ticks_ms()
while time.ticks_diff(time.ticks_ms(), start) < BUSY_WAIT_MS:
    pass

counts_after_busy_wait = list(fire_counts)
naive_expected_min = BUSY_WAIT_MS // TIMER_PERIOD_MS  # a lower bound if nothing were ever dropped
dropped = any(c < naive_expected_min for c in counts_after_busy_wait)

# Self-heal window: let the timers run normally (main loop free to drain the scheduler again) and
# confirm every one of them fires at least once more - proves none permanently stopped.
time.sleep_ms(HEAL_WINDOW_MS)
counts_after_heal = fire_counts
all_self_healed = all(counts_after_heal[i] > counts_after_busy_wait[i] for i in range(N_TIMERS))

for t in timers:
    t.deinit()

if all_self_healed:
    print(f"RESULT: PASS dropped={dropped} all_self_healed={all_self_healed} counts_busy={counts_after_busy_wait} counts_heal={counts_after_heal}")
else:
    print(f"RESULT: FAIL a timer never fired again after the busy-wait - not self-healing. counts_busy={counts_after_busy_wait} counts_heal={counts_after_heal}")
