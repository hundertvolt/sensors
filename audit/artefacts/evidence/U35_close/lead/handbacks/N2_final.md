N2 hand-back (lane N, block 2). Branch audit/u35-n, commit 66e496d (only tests/test_asy_notification_service.py), worktree S/wt-u35n. Nothing uncommitted. Nothing of mine is running. S = /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad.

Steps:
- 45, applied. `_make_coordinator` is now `_make_service`. It takes no `debug=` (the default log is the same LogConfig) and it calls `setup()`. `_one_cycle()` runs on `DrivenTime(sleeps=True)`, over the service and asy_base_classes (the pause's TickSeconds). Its bound comes from the service's own rule, with no margin: 2 x FlashDur per flash, the last settle still running 1 ms before the end, then the loop parked exactly FlashInterval after the cycle's start. Variables and comments say "service". Tags, decided per literal: `override_bound_ms` is withdrawn with its literal. `elapsed_stimulus_ms`, `next_sleep_min_ms`, `override_secs` and `max_rounds` keep their literals.
- Deviation in 45: three tests build their service directly: the two that read state before `setup()`, and the debug=2 console test.
- 46, applied. The four ordering waits use exact flash counts. The sequential test checks that only the first flash has landed at t=0 and both have landed at t=1000.
- 47, applied. All six gating tests use driven cycles.
- 48, applied. The override ends on the round at its measured end (`ended_at == 2000`), with `_LOOP_TICK_S` read through `src_int`. The restart test also asserts that the restarted monitor's cycle ran (State 1). The `_MAX_OVERRIDE_TIME` src_int read was already in place.
- 49, applied. The no-signal test uses a driven cycle. The raising-callback test uses one 2 x 1000 ms cycle. The malformed-config test (the 0.1 s site) now shows the retry exactly one fail interval later (`_CFG_FAIL_INTERVAL_S` read from source).
- `FastAsyncSleep` / `_rounds_until` scenarios stay as they are. The next-sleep test keeps its real 50 ms stimulus.

Decisions (agent, 2026-10-21):
- The FastAsyncSleep scenarios stay. They wait on no real time and are bounded in rounds.
- The stalled-callback settle is `elapse(0)` instead of one `sleep(0)`. This makes sure the monitor really parks on the callback.

Seen failing (no src/ change; 18 services planted in scratch copies, each run at -1 and 32768; nothing committed):
- Every converted test fails under at least one plant at both stages. Zero memory-error markers in all 36 runs.
- XS adds 1 ms per settle. It fails 8 tests, so the bounds have no margin.
- NS (no settle) and SA (a settle after every signal) also fail, so the cycle's end is pinned from both sides.
- PI (+1 ms interval), NE (elapsed time ignored), PR (pause round +1 ms) and PE (pause ends early) all fail.
- RV, WX/WI, AO/PG, CB, CK, FI/FR, RC and NC each fail their tests. Each bite fails at its own assertion. Example: under XS, the sequential test fails at its two-flash assert, line 1008.

Checks:
- ruff clean. mypy main pass (264 files) and `src tests tests_hardware/device_scripts` pass (230 files) are clean, re-run on the committed tree. The temporary typings link is removed.
- One pytest process ran the 12 pre-commit checks plus ticks_wrap_scan (this covers all three readers): 816 passed, 1 failed. The one red is tunables_register on exactly one row: "SPECIFICATION.md:11860: l1.bus_fault_isolation_bound_s is a tuned row, but no file carries its @tunable tag". That is Y2's tag. The assert list holds only that row.
- The one warning is the uninitialised datasheets/ submodule. No orphaned allowlist rows. No relay lines written.

Times (paired, alternating against S/wt-u35base, 2 rounds):
- base: 19.04-19.08 s at both stages.
- head: 0.18-0.19 s at -1, 0.18-0.22 s at 32768.
- settrace: 0.32 s. 68/68 pass everywhere.

Silent-failure scan (this file; all classes; Outputs, Supervision, Runtime-limits and Time modes): nothing new. One behaviour is now pinned: a raising LED callback still settles 2 x FlashDur. It is logged and counted as CALLBACK, so it is not silent.

Effect: test-only. No device and no operating mode (STA, AP, Silent, Off, USB) changes.

Runs and exits:
- head at -1 and 32768: rc 0.
- settrace: rc 0.
- bites: 36 runs, all red as planted.
- pair: 8 runs, rc 0.
- pytest: rc 1 (the expected row only).
- mypy: 4 runs, rc 0.
- RUNS.md: lines added for the bites, the pair and the pytest run. The pytest lines were added after the run.

N3 starts from 66e496d in S/wt-u35n, with a clean tree. Left for N3: the four notification integration files, test_neopixel_wifi_integration.py (with its `l1.asy_neopixel_driver_*` tag site), test_digital_twin_network_neopixel.py, and moving N1's setup test to the driven clock (LEAD NOTES 22). Then N's final checks: the 17 repo-wide scans and the readers. Model for the integration files: `_driven()` and `_one_cycle()` in this file (:50, :167).

Logs: S/u35/laneN/n2_head1_*.log, n2_head2_m1.log, n2_settrace.log, n2_bites1.log, n2_pair.txt (+ .base/.head per-run logs), n2_checks.log, n2_mypy_*.log. Tools: S/u35/laneN/tools/conv2.py, bites_n2.py, pair_n2.sh.