# U13 close: the coverage runner's line table inside heap measurements, and the gate's coverage leg under load

## What failed
- Gate coverage leg on 8d359a2 (`gate_coverage_t0.log.gz`, started at t0 beside both full suites and two twins;
  `gate_vmstat.log.gz` shows 100% CPU): 4 tests failed, 9 files passed only on retry after exceeding the 240 s per-file bound.
- The same tree's coverage suite alone (`coverage_alone.log.gz`, `coverage_alone_vmstat.log.gz`): 89/90 files, no retry,
  no timeout; one failure, `test_a_supervised_task_death_reaches_the_console_through_the_pc_report_at_level_0`:
  drift samples `[947168, 946144, 945600, 945536, 946784, 946720, 947264, 946784, 949632, 948544]`, 2464 B over its
  2048 B bound. In the gate run, `test_hammering_a_faulted_link_never_raises_and_still_recovers_nocrc` read 19.2 B/failure
  against 16 (first attempt).

## Cause 1: the tracer's own bookkeeping (SF-U13-19)
`tests/_coverage_runner.py` recorded each line in `hits[filename][lineno] = True`. A line run for the first time inside
a test's measured span grows that dict, and a dict resize moves the collected heap in steps. Reading `f_code`,
`f_lineno` and `co_filename` allocates nothing (`py/profile.c` `frame_attr`: stored pointers and small ints); the frame
and code objects `mp_prof_frame_enter()` builds per call are garbage once collected, apart from one per suspended
generator, which the untraced settrace arm carries as well.

Probe (`run_arms.sh`, `arms.log`): the death-after-death test alone (`probe_test_file.diff`: only that test, plus a print
of the drift samples and the old runner's recorded-line count), sequential runs under `unshare -n` in `wt-u13int`:

| arm | drift span, three runs |
|---|---|
| old runner (`probe_runner.diff`: the old runner exposing `hits`) | 1856, 1824, 1856 B; +2400 B where 20 new lines are recorded (3642 → 3662) |
| new runner (line tables sized before the test file runs) | 224, 224, 256 B |
| build-settrace, no tracer | 0, 256, 256 B |
| build-standard (control) | 288 B |

The new runner's drift follows the untraced profile sample by sample. In the full file, earlier tests leave a different
table size, so the step lands larger (the 4096 B range above).

First-touch check (`first_touch.py`, now `tests_scripts/test_coverage_runner.py`'s
`test_lines_run_for_the_first_time_leave_the_collected_heap_where_it_was`): a measured span calling every
`math_helpers` function but the warm-up's grows the collected heap 32 B with no tracer (both binaries: the program's
own first calls), 32 B under the new runner, 832 B under the old one. Both runners write identical dumps.

## Cause 2: host load on the slowest build (OF-47, OF-33)
The gate started the coverage leg at t0; with two full suites and two twins on four cores the settrace binary's
wall-clock bounds tripped: nine per-file retries, three `run_timed()` `TimeoutError`s in the twin integration file
(OF-47, U25) and the crc16 hammer's 144/150 (OF-33's signature, U17). None of these reproduced alone. The gate now starts
the coverage leg after the 32768 run (gate_v7).

## Cause 3: the first fix made coverage 2.6x slower (fixed in the same unit)
d8ac624's per-line trace function was a closure over `hits`, `tables` and itself; with its three arguments that is six
values, and `closure_call()` (`py/objclosure.c:44-53`) copies closed-over values plus arguments into a stack array only up
to five, else `m_new`/`m_del` on every call - every traced line. Its coverage run on d8ac624 (`coverage_d8ac624_under_load.log.gz`,
beside four twins, npm and a probe agent) timed nine files out on all three attempts.
- `slowdown/voc_timing_closure_runner.txt`: `tests/test_voc_algorithm.py` under build-settrace, alternated: old runner 169.4 s,
  167.9 s; closure runner 444.8 s, 444.7 s.
- `slowdown/bench_case.py` (20000 traced `dew_point` calls), bisected: old 2.0 s; closure runner 10.3-10.5 s; the same with an
  empty table dict (`var_empty.py`) 10.2 s, so not the tables' memory; the old body plus one module-global dict lookup
  (`v_get.py`) 2.0 s; plus the same lookup on a closed-over dict (`v_get_local.py`) 10.5 s; untraced 0.4 s.
- Fix 8bfcd7b: state in module globals, module-level trace functions: bench 1.76-1.88 s (old 1.71-1.76 s);
  `slowdown/voc_timing_and_drift_final_runner.txt`: voc 163.0 s (old 167.8 s), drift span 224, 256, 224 B.
- First-touch check: the module-level runner showed one 64 B block (`h=`, a frame object's size) on the FIRST measured span
  with `MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen` only (each element dropped: 0; env padding: no
  effect); the untraced binary shows 32-128 B on a first span too, 0 after (`ft_two.py`: two spans of first-run lines:
  old runner 384 then 416 B, module-level runner 64 then 0, untraced 64 or 128 then 0). The permanent check therefore
  measures a second span after a warm-up span, exact against an untraced run on the same path.
