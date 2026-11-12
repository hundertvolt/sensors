U31 lane C block C1 FINAL
Branch audit/u31-c in S/wt-u31c, built from aba11d5 (rebuild.sh rc 0). Head 8f11025, nothing uncommitted, nothing pushed.
Commit: 8f11025 "U31 lane C: arm_tick_timer() takes quiet= for a re-arm inside one failed episode". This is <CORE>, alone in its own commit: src/asy_base_classes.py (+3/-2) and tests/test_asy_base_classes.py (+16).
Relay: wrote "<CORE> 8f11025" under "## C" in S/u31/relay.md.
Steps:
- <CORE>, applied. `arm_tick_timer(timer, flag, pr, what, *, quiet: bool = False) -> bool`. With quiet=True it drops the alarm-pool refusal's `pr.err` line and returns the same result either way. No caller passes quiet= yet, so nothing changes in any mode (STA, AP, Silent, Off, USB). In C3 (system loop) and W (WiFi sibling), passing it cuts repeated console lines at level 1 and above.
- asy_base_classes.py's other steps: none found. lane_C.md names no other site in this file; sleepforms.py finds no sleep or wait_for in it. OF-222 touches :123-126, but its fix (a bounded wait on the escalation's entry write) sits in asy_system_service.py, C3's file.
Decision (agent, 2026-10-21): quiet= never hides the MemoryError `console()` line, which the memory gates read; the commit message records this.
Seen failing first: test_arm_tick_timer_quiet_drops_only_the_alarm_pool_line on the base: "TypeError: unexpected keyword argument 'quiet'" (189/190).
Bites (scratch copies, deleted): quiet ignored -> `AssertionError: (<class 'OSError'>, [('T', 'Could not arm', 'test', 'timer:', ...)])`; quiet also hiding the MemoryError line -> `AssertionError: (<class 'MemoryError'>, [])`.
Runs (rc 0 each, zero "MemoryError" and zero "memory allocation failed"):
- test_asy_base_classes.py 190/190 at -1 (0.37 s, base 0.86), 32768 (0.45 s, base 0.45), settrace (0.61 s).
- callers' tests at -1 and 32768: test_asy_system_service.py 173/173, 23.3 s and 24.3 s (base 23.41, 24.76); test_ntp_wifi_dns_integration.py 13/13, 1.5 s each; test_ntp_fram_system_integration.py 12/12, 7.6 s and 7.7 s.
- ruff clean; mypy main (260 files) and `src tests tests_hardware/device_scripts` (226) clean via a temporary typings symlink, since removed.
- 12 doc and convention checks: 787 passed; tests_scripts readers of asy_base_classes.py (12 files): 790 passed.
- RUNS.md lines for both runs; logs S/u31/laneC/.
Red checks: none. test_twin_record.py expected red for this src/ change (the lead re-records); not run.
Silent-failure scan over the change: nothing new (rp2 v1.29.0 Timer.init raises only OSError(ENOMEM), ports/rp2/machine_timer.c:107-109).
Facts owed: to D, the API end state, and that quiet= drops only the refusal line (SPEC mentions arm_tick_timer at :4019, :8285); to W, the WiFi sibling (asy_wifi_service.py:413) can pass quiet=; to C3, the system loop's re-arm (asy_system_service.py:477) passes `quiet=reported`, start_uptime_timer (:573) keeps the default.
Next block (C2) starts from 8f11025: test_src_sleep_forms.py (seen failing on <BASE> with its bites), then buildgen/validate.py with test_buildgen_validate.py and test_buildgen_error_contract.py. Nothing half-done.
nothing of mine is running
