# One brownout, one entry; calibration expiries every cycle (U15, lane C, second commit)

What failed (tests written first, on `a5bdf44`): `u15c_f12_unit_before.log`, 236/239, the three new tests
`test_one_brownout_gives_one_entry_and_one_reapply`, `test_failing_reads_past_the_window_end_the_run_and_drop_the_candidate`
and `test_a_week_of_failing_reads_never_revives_a_run_or_a_candidate_across_the_wrap`; `u15c_f12_twin_before.log`,
19/20, `test_each_brownout_is_one_warning_and_nothing_else`.

Why: the per-cycle CONFIG snapshot saw the zeroed registers before the status read saw BOUTF, so one brownout
persisted W31 then W30 and re-applied twice (`probe_brownout.py` is the lane's twin probe); the candidate hold and
the calibration window were compared only on successful cycles.

Fix: commit `67e5848`.

What proves it: `twin_after_gc-1.log` and `twin_after_gc32768.log`, 20/20. The unit file's run after the fix was not
kept in this folder; lane A's run of the merged lane tree shows it 239/239 at both stages (`../lane_a_runs/run4.txt`).
