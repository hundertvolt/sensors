N1 hand-back (lane N, block 1). Branch audit/u35-n at feae592, worktree S/wt-u35n, rebuilt with S/u23/rebuild.sh. Commit 32bb1eb (only tests/test_asy_neopixel_driver.py). Nothing uncommitted. S = /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad.

Steps:
- 43, applied. The local `_YieldOnlyAsyncio` and `_DrivenClock` are deleted, replaced by a `_driven()` helper that returns `DrivenTime(asy_neopixel_driver, sleeps=True)`. The parts landed earlier are still in place.
- 44, applied. `sleep(1.5)` and `sleep(1.1)` now elapse by the ramp's own length. `>= 30` became `== 31`. Deviation: the count is taken with the signal task running alone, because with the overlay task running its restore black makes 32 frames.
- 53, applied. All 15 real sleeps are now `elapse()` or `run_until()`, sized by `_ramp_ms()` (the driver's own steps rule) with no margin. The deadline case uses `jump()`. The start-yield comment now says "a limit". `cancel_all` is kept. `debug=4` and `neopixel_freq` stay as the tree has them. `_make_driver` takes `freq` and `overlay_bri`. Ramp tests now assert their exact frames or frame count.
- Deviation: the bound gets one extra frame only where a request polls behind a running ramp (the two concurrent requests). Everywhere else the bound is the exact ramp length.
- A yield bound, `_yields_until`, is kept. It is used by the guard on the real `wait_for` (that test runs on the real asyncio) and to clear an injected fault before the next task writes.

Decision (agent, 2026-10-21): `test_setup_initialises_the_logger_and_the_driver_before_any_task` stays on the real asyncio. It waits on no time, and under the shared clock it hangs (next point).

Unexplained failure, for C (owner of tests/_fake_time.py):
- What hangs: under `DrivenTime(sleeps=True)`, start both driver tasks, give one yield, then cancel both. Both cancels finish and the scenario returns, but `run()` never completes. The full-file run sat idle until its 300 s timeout (rc 124, 4.6 s of CPU).
- What does not hang: the same scenario on the real asyncio, or with `clock.elapse(0)` before the cancels.
- Reproducer: S/u35/laneN/dbg/dbg_setup.py (compare with dbg_real.py and dbg_settle.py). Run it from the worktree with that dbg directory first on MICROPYPATH. The output of the hung run is in S/u35/laneN/head1_m1.log.
- I did not root-cause it inside the shim. My guess is the external-cancel path at _fake_time.py:162 (`runner.cancel()`), because the real funcs.py cancels the awaited task instead.

Seen failing and bites (no `src/` change, so the check is the file green at both stages plus planted drivers in scratch copies, nothing committed):
- 23 planted drivers ran at -1 and 32768, all in S/u35/laneN/bites{1,2,3}.log. They covered the brief's three (no restore, lock ignored, t truncated), an extra frame, no wait, the overlay's on/off/toggle and clamp paths, and the deadline.
- Every converted test fails under at least one plant at both stages, with zero memory-error markers.
- The extra-frame plant fails 23 tests, which shows the bounds have no margin. It also fails 44's `== 31`; the old `>= 30` would have passed.
- `test_on_sets...` and `test_toggle_flips_from_off_to_on` were not bitten at first: the overlay task's own start-up wake hid the call. They now let the start frames land first, and are bitten.
- During the conversion, two tests failed on a red-detection bound of 0 (a 0.5 s ramp's first two frames are black). Fixed to a 20 ms bound.

Times (paired, alternating, base S/wt-u35base): -1 7.19 s to 0.73 s; 32768 7.22 s to 0.82 s. 54/54 pass at both stages.

Checks, all exit 0:
- ruff clean.
- mypy main pass (264 files) and the `src tests tests_hardware/device_scripts` pass (230 files) clean; the temporary typings link is removed.
- One pytest process over the 12 pre-commit checks plus test_ticks_wrap_scan: 817 passed. It warns that the worktree's datasheets/ submodule is not initialised, so citations under it are unchecked.
- No red checks, no orphaned allowlist rows, no tags added or withdrawn, no relay lines written.

Silent-failure scan (all classes, Outputs/Supervision/Runtime-limit modes, this file):
- Nothing new.
- The "UNRETRIEVED TASK EXCEPTION" print in the supervisor-restart test is also in the base log. The supervisor still logs `TASK_RAISED`, which the test asserts, so it is covered.

Retries: none. RUNS.md lines were appended after the fact for the hung run, the bite runs and the pytest run.

OF-233 owed: N2 converts tests/test_asy_notification_service.py (45-49, merging <PARTN> before its reader run). N3 converts the four notification integration files, test_neopixel_wifi_integration.py (which also holds the `l1.asy_neopixel_driver_*` tag site) and test_digital_twin_network_neopixel.py, then runs N's final checks: the 17 repo-wide scans and its readers.

N2 starts from 32bb1eb in S/wt-u35n, with the clean tree and the shim hang above as a known hazard: let tasks start before cancelling them.

Logs and tools are in S/u35/laneN/. Nothing of mine is running.
