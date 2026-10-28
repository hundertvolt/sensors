N4 hand-back (lane N, last block). Branch audit/u35-n, commit 5ce41a4 on top of 189d4e8, in S/wt-u35n. One file changed: tests/test_digital_twin_network_neopixel.py. No src/ change. Nothing is uncommitted and nothing of mine is running. I used about 47 tool calls. S = /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad.

Verdict: step 99's last item (the restarted-signal-task case) is applied. The test is `test_a_restarted_signal_task_ends_dark_with_the_overlay_restored`, and it passes at -1, at 32768 and under settrace.
- Device: it boots arzi, which is `device_with("neopixel")`. The file header now has the C4 order: prewarm, then the UDP shim, then the imports.
- Scenario: overlay on, `request_signal(255,0,0,0.5)`, then `raise_on_write` is set after the first red frame, so the next frame write ends the signal task. The fault is cleared once the task is `done()`. One released supervisor pass then logs the end and restarts the task.
- Asserts: the frames since the restart are exactly [black, overlay grey], with no red frame among them. The only driven wait left is the overlay's refresh, one full period away. The overlay task survived. SYSTEM's FRAM chunk, read back with `_read()`, holds exactly one task-end entry (TASK_RAISED).
- Waits: they are events and conditions on the pixel's writes (the supervisor's park, `run_until(len(frames) > n, 0)`). There is no wall-clock wait.
- The file also registers `machine.reset_test_state` as an after-each hook, next to network's (the step's "both reset hooks").

Bites. Each was planted in a scratch copy of the full tree and run from there at -1 and 32768. Every one failed only the new test, at its own line, with zero memory markers:
- RA (the finally no longer clears the request, so the old ramp resumes) → "the restarted task resumed the old ramp: [(0, 0, 0), (51, 0, 0)]".
- OO (the restart's overlay flag is dropped) → "the restart did not leave the pixel dark with the overlay restored: [(0, 0, 0)]".
- NP (the task end goes through `pr.err`, so nothing is persisted) → "SYSTEM persisted (0, (0,...))".
- RL (a stale request resumes one frame late) → "a wait of the old ramp outlived the restart: [100, 300050]".
- My first RL plant also hit the first boot, so it failed at the first red-frame wait. I replaced it; it is not counted.

Times, paired and alternating, 2 rounds against the file at 189d4e8 (-1 / 32768):
- Base: 14.25 / 14.30 s.
- Head: 14.69 / 14.74 s, which is +0.44 s (+3.1 %). The new test adds about 0.4 s, including the prewarm and the generated-module import.
- Settrace: 14.96 s, rc 0.

Checks:
- ruff: clean.
- mypy twin pass: cold cache, 52 files, clean.
- D.15: no slips (`_yields_until` comes last among the helpers, `_SupervisorPasses` after `_Pin`).
- One pytest process ran the 12 commit checks, the 17 scans, ticks_wrap_scan and the readers (twin_entry_point_order, import_placement, config_paths_resolve, lint_type_scopes, test_sh, threshold_runner). Result: 1205 passed, 1 failed.
- The one red is the known one: test_tunables_register::test_the_tags_and_the_part_n_rows_agree, for SPECIFICATION.md:11780 `l1.notification_neopixel_wait_until_timeout_ms` (N3's withdrawn tag) and :11860 `l1.bus_fault_isolation_bound_s`. It waits on D or the lead. I added no tag.
- Silent-failure scan of my file (all classes; modes Outputs, Supervision, Time, plus the brief's list): nothing new.
  - A raising after-each hook fails the test (microtest.py:92-98).
  - A stale generated tree now fails the whole file loudly at import (require_fresh).
  - The prewarm's port scan runs in the netns.
  - A supervisor that never parks again hangs to the per-file timeout. That is the twin integration file's stated bound; I added no wall-clock bound.
- Effect: test-only. No device and no mode (STA, AP, Silent, Off, USB) changes.

Decisions (agent, 2026-10-21):
- The boot goes through the shared `boot_generated()`, as the fram twin file does. It follows the same order as the integration file's `_boot()`, and arzi wires no UART link.
- Only the NeoPixel's two starters go to the real `start_tasks()`/supervisor, so no other task's real waits enter the scenario.
- The gate covers only asy_system_service's view of asyncio, like the integration file's _FastSupervisorAsyncio. The driver runs on DrivenTime.
- "Persisted" is read back from the FRAM chunk, not from the RAM history.
- "No frame of the old ramp follows" is checked structurally (the pending driven waits), not with a virtual window.
- The bites re-hash the bitten file into the scratch copy's generator stamp. A body-only change leaves the generated modules unchanged, so otherwise require_fresh() would refuse for the wrong reason.

Facts owed: none new. Relay lines written: none.

Runs, each with a start and a done line in RUNS.md:
- head at both stages: rc 0.
- bites, 3 runs: all red as planted.
- pair plus settrace: rc 0.
- pytest: rc 1 (the known red above).
- mypy: rc 0.

Logs are in S/u35/laneN/: n4_h1_*.log, n4_bites.txt, n4_bites_rl.txt, n4_bite_*.log, n4_pair.txt, n4_settrace_*.log, n4_checks.log, n4_mypy_twin.log. Tools are in S/u35/laneN/tools/: n4_patch.py, bites_n4.py, run_n4.sh, settrace_n4.sh.