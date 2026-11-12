U31 lane T block T FINAL
Branch audit/u31-t in S/wt-u31t, from aba11d5. Commits: 9a43798 (steps 55 and 57), e57754a (step 60 and OF-198), 03bc27e (steps 8, 10 and 11). Nothing pushed, nothing uncommitted.

Steps:
- 55 applied. TestFlags gains `loop_lag_ms` and `drop_timer_fire`, appended at the end; every positional site is updated, the help text too. `--test-loop-lag-ms N` prints one `LOOP_LAG max_us p99_us samples` line per 5 s window from a fixed 64-bin histogram. `--test-drop-timer-fire reset|sequencer` sets `Timer.drop_next_soft_callbacks` before that one product one-shot arms and clears it once that fire was dropped (`DROP_ARMED` / `FIRE_DROPPED` lines).
- 57 applied. test_twin_runner_test_flags.py now holds an explicit `_FLAG_TABLE`, and its default-on bite no longer depends on the field count.
- 60 applied for item (j): `loop_lag_under_combined_load` runs on every device, with a ceiling of readers on every GET route, an SGP40 fault storm and the link exercisers.
- OF-198: two of three applied. The reset one-shot runs on the first generated device; the stagger one-shot runs on the first device whose boot arms one (2+ read triggers, via the new registry field `first_device`).
- OF-198's NTP retry site did not land. Its one-shot arms only when a due resync fails while synced, which needs NTPInterval hours. A resync after a settings change clears Synced first (asy_ntp_client.py:551-559), so it takes the unsynced backoff path instead. The loss is already stated in the comment at :281.
- 8: already landed except the flash-gap test, now added (persistence_write). `COVERS_TWIN_SCENARIOS` gains "loop_lag". 10: new flash_write_loop_gap.py, writing a relative `_stretch.bin` (R-5). 11: the :30 comment now cites F.3's `hold.fram_block` row.
- Check 49 green (marker completeness; the new test is collected and deselected by its gate). Check 56 green (harness mechanism and its L0).

Seen failing first:
- Flag L0: "--test-loop-lag-ms is in the flag table but not in the runner".
- Runner tests: 4 failed against the base runner.
- Scenario L0: 2 failed (AttributeError `_stagger_waits`).
- Bites not run (left): the lag verdict with `--test-stall-loop-ms` past the bound plus `STALL_TRIGGER` at load start, and each OF-198 scenario booted without its flag.

Runs and results:
- At -1: reset PASS on arzi (12.4 s), stagger PASS on dev (10.0 s), loop lag PASS on arzi (75.5 s; max 237 ms under load against an 8 s bound, 5.7 ms after).
- Not run yet:
  - loop lag on the other five devices at -1, and every new scenario at 32768;
  - the six devices' whole scenario jobs at both stages;
  - test_digital_twin_generated_boot.py and test_stripped_image_boots.py.
  - Untested risk: dev's loop-lag bound is 1000 ms, against arzi's 8 s.
- twin_runs.sh was killed by pid (rc 144) after both loop-lag runs reset mid-load. Root cause: a 60 s SGP40 storm crosses the 300-count task-failure ceiling ("Task error counter above 300 - reboot triggered!"), first as a writeto storm, then as a 1000-read storm.
- Runner test 1.34 s at -1 against 1.20 s base (+11.7 %, the new tests' ~0.1 s of real waits), 1.36 s against 1.27 s at 32768. Flag L0 0.56 s. No MemoryError or "memory allocation failed" anywhere.
- ruff and all three mypy passes clean; `--collect-only tests_hardware` rc 0.

Red checks:
- test_tunables_register: `l2.twin_loop_lag_report_ms`, `l2.loop_lag_{load_s,settle_s,recovered_ms,period_ms}` and `l3.memory_stress_flash_gap_script_timeout_s` are tagged but have no Part N row. Waits on the lead (R-24).
- test_twin_record (expected; the lead re-records).
- All other repo-wide scans and the tests_scripts reader files green (512 passed). The silent-failure scan over the lane's files is not done.

Decisions, all (agent, 2026-10-21):
- The fault storm is capped at 5 reads, the SGP40's give-up streak (max_module_error), so neither the task nor the device restarts.
- The loop-lag bound reads `_DEFAULT_TIMEOUT_MS` (1000 ms), the same source as the landed L3 test, not the plan's 925 ms.
- R-12's "exit 3": the twin's watchdog records a trigger and never exits, so exit 3 is what the bite produces; the head run asserts a trigger and no reset.

Relay: two lines written under `## T` (README rows for D, the Part N tags and the re-record for the lead).
nothing of mine is running
