"""Isolated-driver device script for flash-tier candidate A.3 (tmp_hardware_test_candidates.md):
construct real machine.Timer objects until Timer.init() raises OSError(ENOMEM) once the RP2040's
real hardware alarm pool is exhausted - SPECIFICATION.md Part F.2's already-verified claim
(confirmed against real ports/rp2/machine_timer.c source: Timer.init()'s documented failure mode
is exactly OSError(MP_ENOMEM) when alarm_pool_add_alarm_in_us() reports the pool exhausted), never
exercised against real silicon before this. Run via `mpremote run <this> soft-reset`.
Prints exactly one line: "RESULT: PASS constructed=<n> errno=<e>" or "RESULT: FAIL <reason>"."""

import errno

import machine

timers = []
attempt = 0
try:
    for attempt in range(1, 65):  # noqa: B007 - deliberately read after the loop (below) to report how many Timers were constructed before the raise; generous upper bound, the real pool is small and fixed
        t = machine.Timer()
        t.init(period=60_000, callback=lambda _t: None)  # 60s period - never expected to fire during this script
        timers.append(t)
    print(f"RESULT: FAIL never raised OSError after constructing {attempt} Timers - pool larger than assumed, or exhaustion not reachable this way")
except OSError as exc:
    code = exc.args[0] if exc.args else None
    if code == errno.ENOMEM:
        print(f"RESULT: PASS constructed={attempt - 1} errno={code}")
    else:
        print(f"RESULT: FAIL raised OSError with errno={code} (expected ENOMEM={errno.ENOMEM}) after constructing {attempt - 1} Timers")
finally:
    for t in timers:
        try:
            t.deinit()
        except Exception:  # noqa: BLE001 - best-effort cleanup, never let a deinit failure mask the real result above
            pass
