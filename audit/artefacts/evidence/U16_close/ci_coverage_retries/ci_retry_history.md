# CI per-file 240 s retry history (scripts/test.sh), 2026-10-07

Source: mcp__github__get_job_logs (return_content). The tool caps at the LAST 5000 lines of each log
(original lengths 6188-7393 lines), so each job's first ~1200-2400 lines (setup, `uv sync`, the
"== Test parallelism: N (C usable cores x M, probe Xms)" line) are NOT visible. Step wall times are
from the jobs API. Re-run attempts: runs 37664628080 and 37643676687 have attempt-1 and attempt-2
job IDs for the unit-test jobs, but they are carried-over copies (identical timings and identical
log md5), so each commit had exactly one real execution of each unit-test job.
"Commit:" in test.sh's summary is the PR merge ref, not the branch head.

## Run 37671400411 (1cff5a2, U14), merge ref 5618df2

| job | test step | retry lines | Counts (files) |
|---|---|---|---|
| unit-tests-coverage 112967700755 (FAIL) | 19:11:54-19:25:43 = 13m49s | `test_sensortask_dev`, `test_sensortask_wozi`, `test_digital_twin_uart_link` exceeded 240s att 1/3 @19:15:58; `test_asy_framing_codecs` @19:17:41; `test_voc_algorithm` @19:19:51. root-cause item x5 ("needed attempt 2/3"). Passed only on retry: the same 5 (attempt 2/3) | passed 84 · failed 1 · retried 5 · recovered 0 |
| unit-tests 112964181872 | 19:03:24-19:11:02 = 7m38s | none; Passed only on retry: none | passed 90 · failed 0 · retried 0 |
| Unit tests (shipped gc.threshold) 112964181813 | 19:03:21-19:13:06 = 9m45s | none | passed 90 · failed 0 · retried 0 |

Coverage-job failure is NOT a timeout: `tests/test_uart_comm_hazard.py` 1 of 98 failed,
`test_hammering_a_faulted_link_never_raises_and_still_recovers_nocrc`: `AssertionError: 1216 bytes
over 30 failures = 40.5 B/failure` (allocation-budget assertion under settrace), at 19:14:37; the
file finished 19:15:57 (~239 s after t0), i.e. 1 s short of being killed itself.
Attempt-2 durations: voc 199 s, sensortask_dev 196 s, sensortask_wozi 180 s, uart_link 176 s,
framing_codecs 141 s. Next slowest first-attempt files (approx, from t0=19:11:58): uart_comm_hazard
~239 s, sensortask_klkizi/schlafzi/arzi/grkizi ~222-225 s, asy_sgp40_driver ~186 s.

## Run 37664628080 (cbb65df, U13), merge ref dd5d3ee

| job | test step | retry lines | Counts (files) |
|---|---|---|---|
| unit-tests-coverage 112957859185 | 18:19:20-18:27:51 = 8m31s | none; Passed only on retry: none | passed 90 · failed 0 · retried 0 |
| unit-tests 112957857953 | 18:10:10-18:18:56 = 8m46s | none | passed 90 · failed 0 · retried 0 |
| gc.threshold 112957856583 | 18:10:09-18:17:29 = 7m20s | none | passed 90 · failed 0 · retried 0 |

Coverage slowest: sensortask_dev ~181 s, sensortask_wozi ~167 s, sgp40 ~145 s, sensortask_* others
~137-142 s, voc_algorithm 139 s, framing_codecs 129 s, uart_link ~128 s.

## Run 37643676687 (2949ed9, U12), merge ref c08920f

| job | test step | retry lines | Counts (files) |
|---|---|---|---|
| unit-tests-coverage 112884684425 (PASS) | 15:35:26-15:47:23 = 11m57s | `test_sensortask_dev` exceeded 240s att 1/3 @15:39:30; `test_asy_framing_codecs` @15:41:05; `test_voc_algorithm` @15:42:51. root-cause item x3. Passed only on retry: those 3 (attempt 2/3) | passed 87 · failed 0 · retried 3 · recovered 0 |
| unit-tests 112884682175 | 15:25:53-15:34:17 = 8m24s | none | passed 90 · failed 0 · retried 0 |
| gc.threshold 112884683137 | 15:25:54-15:34:43 = 8m49s | none | passed 90 · failed 0 · retried 0 |

Attempt-2 durations: voc 217 s, framing_codecs 115 s, sensortask_dev 107 s. Next slowest first
attempts: sensortask_wozi ~232 s, sensortask_grkizi/klkizi/arzi/schlafzi ~200-207 s, uart_comm_hazard ~181 s.

## Run 37638089345 (8d44fd1, U11), merge ref 51b5e17

| job | test step | retry lines | Counts (files) |
|---|---|---|---|
| unit-tests-coverage 112854355333 (FAIL) | 14:46:38-14:54:19 = 7m41s | none; Passed only on retry: none | passed 88 · failed 2 · retried 0 |
| unit-tests 112849997394 | 14:37:36-14:46:12 = 8m36s | none | passed 90 · failed 0 · retried 0 |
| gc.threshold 112849997347 | 14:37:35-14:46:15 = 8m40s | none | passed 90 · failed 0 · retried 0 |

Coverage failures (not timeouts): test_asy_system_service 1/118, test_digital_twin_unix_port_unretrieved_report
1/9 (test_the_reports_outputs_allocate_nothing). Slowest: sensortask_dev ~150 s, bus_hazard_concurrency
~136 s, sensortask_wozi ~134 s; voc_algorithm only 20.7 s.

## Non-coverage jobs, slowest files (all four runs, approx from step start)
bus_hazard_concurrency ~120-136 s, asy_wifi_service ~117-120 s, sgp40 ~87-94 s, sensortask_dev 46-114 s.
Max well under 240 s; zero retries in all 8 non-coverage jobs.

## Parallelism / runner
"== Test parallelism" line is in the truncated head of every log - not visible. Dispatch order is
`_heavy_files_priority` (15 files) first, then alphabetical; in 112967700755 all three first-batch
files were killed at the same instant (inferred start 19:11:58, step start +4 s), consistent with the
whole heavy batch starting together. Repo is public, so ubuntu-latest is the standard 4-vCPU runner
(inference from GitHub's documented runner sizes, not printed in the visible log).

## Conclusion
Recurring, not new at 1cff5a2: the coverage job already needed 3 retries at 2949ed9 (U12, sensortask_dev,
framing_codecs, voc_algorithm), none at cbb65df (but framing 129 s, voc 139 s, sensortask_dev ~181 s
- within ~60 s of the limit), and 5 at 1cff5a2. 8d44fd1 (before U12) had no retries and voc took 21 s:
U12 (2949ed9) changed tests/test_voc_algorithm.py (+171/-16) and test_asy_framing_codecs.py (+35), and
those two jumped to ~130-220 s per attempt under settrace. 1cff5a2 adds many tests (incl. a 645-line
growth of test_ticks_rollover.py and a new tests_scripts/test_ticks_wrap_scan.py) which plausibly adds
contention. Closest to the limit under coverage: test_voc_algorithm (139-217+ s), test_sensortask_dev
(181 s to >240 s), test_sensortask_wozi (167-232 s, >240 once), test_uart_comm_hazard (~239 s at
1cff5a2), sensortask_{grkizi,klkizi,arzi,schlafzi} (~200-225 s), test_digital_twin_uart_link (>240 once),
test_asy_framing_codecs (129 s to >240 s). Non-coverage lanes peak at ~136 s with zero retries.
