N3 hand-back (lane N, last block). Branch audit/u35-n, commit aa521ac on top of 66e496d, in S/wt-u35n. It changes 7 test files and no src/. Nothing is uncommitted and nothing of mine is running. I used about 73 tool calls. S = /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad.

Steps by verdict:
- 86, applied (R-3). Each of the 7 `NeopixelDriver(0)` sites in test_neopixel_wifi_integration.py now runs `run(pixel.setup())` before any task starts. `_run_until` stays (it counts yields and reads no clock).
- 87, 88, 89, 90, applied. Every real sleep or real poll moved to one `_driven()` clock, which is `DrivenTime(asy_neopixel_driver, asy_notification_service, sleeps=True)`. The new `_cycle(clock, notify, flashes)` uses the service's own rule with no margin. A cycle lasts 2 x FlashDur per flash. 1 ms before that end, State is still unset. The loop then parks exactly FlashInterval after its start. The ramp ends at the driver's own steps rule: `_ramp_ms(0.5)` = 500 ms. In 90, `drive_scd_cycle` is renamed `_drive_scd_cycle`, and "coordinator" now reads "service" (no meaning change).
- LEAD NOTES 22, applied. The setup test in test_asy_neopixel_driver.py now runs under `_driven()`.
- 99, partly applied:
  - The two 1.0 s windows and the 40 ms status-two window are now structural: the connect task is kept, then checked `done()`, and awaiting it raises `CancelledError`.
  - Fold (1)'s driver case is added: `test_the_driver_rewrites_a_dipped_pixel_at_its_next_overlay_refresh`. It runs in-process on the twin pixel. The pixel is dark 1 ms before `_OVERLAY_REFRESH_MS` and grey at it.
  - Not done: the A.U22.01 restarted-signal-task test. It needs a booted generated device, which is outside N3's driven-clock scope. It is left for the lead.
- D.15 member order is the last edit in all 7 files (pure moves; the d15 checker shows no slips). A stale "# --- shared downstream stack ---" heading in the dual-sensor file is gone.

Wait table (old wait → new bound):
- neopixel_integration:
  - 1.3 s → 1 cycle (1000 ms); 2.5 s → 2 cycles (2000 ms).
  - The lit-frame poll → `run_until(..., 0)`. The ramp-end poll → `run_until(..., 500)`, asserted == 500.
  - The err≥1 poll → 1 cycle, on the service's clock only. The driver keeps `_LateTicks`.
  - The TS polls → 1 cycle; the out-of-window case → 0 cycles. The 10 s real guard is gone.
- scd30: three 1.3 s waits → 1 cycle each; 0.2 s → 0 cycles.
- sgp40: two 1.3 s waits → 1 cycle each; 0.2 s → 0 cycles.
- scd30_sgp40: 2.6 s → 2 cycles; 1.3 s → 1 cycle.
- network_neopixel: the two 1.0 s windows and the 40 ms window → structural.
- What stays and why:
  - The twin's `_wait_until_connected/settled`: the twin's real 0.7 s connect delay is the subject (tags l2.network_neopixel_wait_timeout_s and _poll_ms kept).
  - The FastAsyncSleep calibration loops: they are bounded in rounds.

Seen failing (12 plants in a scratch copy, each at -1 and 32768; nothing committed; zero memory markers in every run):
- XS (settle +1 ms), NS (no settle), PI (interval +1 ms) and NE (elapsed time ignored) fail every converted cycle test in the four files. XS and PI show the bounds have no margin. PI also fails the 0-flash cases.
- RF (ramp one frame longer), RS (one frame shorter) and LB (a busy LED accepts) fail the refused-at-once test, each at its own line (run_until, `ended_at ==`, `result is False`).
- SU (a task sets the logger up) fails the setup test.
- OT (refresh never rewrites) and OM (refresh +1 ms) fail the new power-dip test.
- DC (disconnect does not cancel) fails both structural windows. LN (a late status change) fails the status-two test at its new line.
- The first bite run hit ENOENT because the scratch tree had no buildgen/ or ext/. I re-ran it on a full copy; the results above are from that re-run.

Times (paired, base S/wt-u35base, alternating; -1 / 32768):
| File | Base | Head |
|---|---|---|
| neopixel_int | 6.42 / 6.43 | 0.23 / 0.27 |
| scd30 | 4.49 / 4.55 | 0.40 / 0.42 |
| sgp40 | 2.93 / 3.01 | 0.15 / 0.20 |
| dual | 4.14 / 4.20 | 0.42 / 0.43 |
| neopixel_driver | 7.20 / 7.31 | 0.72 / 0.74 |
| neopixel_wifi | 2.75 / 2.83 | 2.71 / 2.90 (+2.5 %) |
| network_neopixel | 16.27 / 16.28 | 14.33 / 14.37 |

Settrace: all 7 files rc 0, zero memory markers. The twin file takes no TEST_DEVICE.

Lane N's complete checks:
- ruff clean.
- mypy: main pass 264 files and args pass 230 files clean; twin pass 52 files clean (re-run after the last edit).
- One pytest process ran the 12 pre-commit checks, the 17 scans and ticks_wrap_scan: 988 passed, 2 failed. A re-check on aa521ac gives the same two reds:
  1. test_decision_vocabulary::test_the_allowlist_only_shrinks: rows 300-301 of tests_scripts/_decision_vocab_allowlist.txt (the two "longer than _CONNECT_DELAY_S - must never …" comments) are now orphaned. The lead removes them.
  2. test_tunables_register: SPECIFICATION.md:11780 `l1.notification_neopixel_wait_until_timeout_ms` (I withdrew its tag, relayed for D/lead), plus the expected :11860 `l1.bus_fault_isolation_bound_s`.

Decisions (agent, 2026-10-21):
- The tag is withdrawn with its literal, as step 87's "Resolved" text says. I relayed one line under ## N.
- The cycle end is checked through the stored State, not `wakes()[0]`. The pause and overlay tasks also park on the clock, so `wakes()[0]` could hide a late settle.
- The dropped-signal test drives only the service's clock.
- The power-dip driver case lives in the twin file, where the driver imports the twin pixel.
- `setup()` is added at all 7 neopixel_wifi sites, the webserver one included.

Silent-failure scan (my 7 files; all classes; Outputs, Supervision and Time modes): nothing new. Effect: test-only; no device and no mode (STA, AP, Silent, Off, USB) changes. Facts owed: the lead removes allowlist rows 300-301; D or the lead withdraws the Part N row at :11780.

Runs and exits:
- head at both stages: rc 0.
- bites: 2 runs (the first is invalid, ENOENT) plus LN, all red as planted.
- pair: rc 0. settrace: rc 0.
- pytest: rc 1 twice (the reds above). mypy: 4 runs, rc 0.
- RUNS.md has every line.

Logs and tools: S/u35/laneN/n3_*.log, n3_pair.txt, n3_bites2.log, n3_checks.log, n3_checks2.log. Tools in S/u35/laneN/tools/: conv3.py, reorder.py, d15.py, bites_n3.py, run_n3.sh, pair_n3.sh, settrace_n3.sh.