"""Isolated-driver device script for flash-tier candidate A.2: provoke enough concurrent real
Timer IRQs to exceed MicroPython's fixed-depth scheduler queue (MICROPY_SCHEDULER_DEPTH=8 on rp2 -
SPECIFICATION.md Part F.1, confirmed against real shared/runtime/mpirq.c/ports/rp2/machine_timer.c
source) and confirm a periodic timer self-heals on a later tick rather than permanently stopping,
matching Part F.1's documented (but never hardware-tested before this) drop behavior.

Mechanism: `machine.Timer` callbacks are soft (deferred via mp_sched_schedule() to the next VM
opcode boundary, not run in the hard-IRQ context itself) by default. Ten short-period timers are
started, then the main "loop" deliberately busy-waits (never yielding back to the point where
MicroPython drains the scheduler queue) for long enough that more than 8 timer IRQs should fire
within that window - the 9th+ should be silently dropped (mp_sched_schedule() returning False, no
exception anywhere in that chain, per Part F.1). The busy-wait then ends and every timer is given
a further window to prove it's still alive (fires at least once more) - the "self-heals" claim.

TUNE_ON_FIRST_REAL_RUN: BUSY_WAIT_MS/TIMER_PERIOD_MS are a starting guess (10 timers at 2ms period
against a 100ms uninterrupted busy-wait should produce ~50 IRQs per timer, far more than the queue
depth), not measured on real hardware yet - widen BUSY_WAIT_MS if `dropped` comes back 0 on a real
run (the busy-wait wasn't actually long enough to starve the drain point on this build/clock speed).
Run via `mpremote run <this> soft-reset`. Prints "RESULT: PASS dropped=<n> all_self_healed=<bool>"
or "RESULT: FAIL <reason>"."""

import time

import machine

N_TIMERS = 10
TIMER_PERIOD_MS = 2
BUSY_WAIT_MS = 100
HEAL_WINDOW_MS = 500

fire_counts = [0] * N_TIMERS


def _make_cb(i: int):
    def _cb(_t) -> None:
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
