
######## SubagentHandback 2026-10-13T21:17:21.900Z
U24 lane K hand-back. Commit e262d67 on audit/u24-k (S/wt-u24k), built on 31d5bfc plus a clean cherry-pick of 9efb630 (5b92b67). Not pushed. Proof logs are in S/u24/laneK/.

**Steps applied (all 5):**
- Reap ends on every path: each task is cancelled on its own; the reap stops on a stall at once and at `l1.async_harness_reap_limit_ms` otherwise, names what it could not end, and unparks it.
- No finished task is kept (amortised compaction).
- Per-call cost cut.
- A hang names its test: SIGINT first, ABORT around the after-each reset, the summary names ABORT lines.
- An aborted test.sh stops every background job (`jobs -rp` plus each attempt's timeout group, by recorded pid) and waits for them before releasing port 53.

**Deviations:**
- New tunable `l1.async_harness_reap_limit_ms = 5000` (`tests/_async_harness.py:29`).
- Two messages added in test.sh: the hard stop (137) and the cleanup's SIGKILL backstop.
- Two existing 0.05 s bounds in test_async_harness cut to 0.01 s.
- New helpers in test_test_sh.py and test_microtest.py are placed by topic, as those files already are, not sorted by D.15.
- Once I used a pattern kill (`pkill -f "sleep 30"`) on my own probe's orphans. After that, pid only.

**Seen failing first on W1** (logs `seen_failing_*_W1.log`):
- Four reap scenarios hung at `_async_harness.py:78`.
- Retention: 46,784 B released against 48,800 held.
- Interrupt in a run: the file never ended. Interrupt in the drain: exit 130 with no ABORT line.
- test.sh: the summary named no ABORT, SIGTERM left no ABORT, and an aborted run left 12 processes running.
- The 137 and SIGKILL message tests failed on my pre-message code.
- Bites: the lock released before the stop gives "released"; with stall detection removed the stall test takes 3000 ms (`bite_stall.log`).

**Real consumer:** U3's file without its polling workaround hung 330 s in W1's `_reap`. On the new harness: 166/166 in 25 s.

**Per call** (median over plain asyncio.run, standard binary, `per_call_bench.txt`):
- W1: +6.9 µs at -1, +84 µs at 32768, +1,120 B per call.
- Now: +2.0 µs at -1, +3.1 µs at 32768, +0 B.
- Limit path: +82 µs → +3.5 µs at 32768.

**ABORT line from a planted hang:** `ABORT test_b_hangs:`, then a traceback ending at `test_case.py, line 13, in spins` and `KeyboardInterrupt:`. The closing line reads `1/3 passed, 1 failed, 0 skipped - aborted at test_b_hangs, later tests not run`.

**Twin runners in-process:** with a planted serve-forever, both test_digital_twin_run_generic_integration and _launch end with ABORT at the INT (rc 124).

**Checks:**
- test_async_harness is 14/14 at -1, 32768 and settrace.
- harness users and test_microtest_hooks are green at both stages.
- test_test_sh 130/130.
- test_microtest 21/24: its 3 reds are W1's (now at :301, :308, :312).
- ruff, shellcheck, mypy main, twin and host passes add no error. Zero MemoryError lines.

**Red checks:**
- `test_tunables_register`: `tests/_async_harness.py:29` has no Part N row (waits on X).
- W1's own reds are unchanged: decision_vocabulary allow-list, import_placement `_PENDING`, the live_twin Sites.

**Scan findings:**
- Fixed (all new): class 6 reap hang, class 2 retention, class 6/7 hang without a name, port held after the lock (aborted run), class 7 silent 137 and silent SIGKILL.
- New, partly covered:
  - class 4: broad `except BaseException` can swallow the timeout's INT (tests/_machine_contract.py:25, test_fakes.py:99, test_generated_boot_entry.py:61, test_asy_system_service.py:3764, test_digital_twin_unix_port_unretrieved_report.py:84, digital_twin/run_generic_integration.py:364).
  - class 6: microtest's drain is still unbounded; an interrupt there is now named.

**Owed to X:**
- Part N row for `l1.async_harness_reap_limit_ms` = 5000, Sites `tests/_async_harness.py — 5000`. Basis: post-cancel cleanup here is ms-scale.
- The `runner.kill_after_s` row: the first signal is now SIGINT, and a new site is `_cleanup`'s 2× stop bound.
- E.3.1: INT, then ABORT, then the hard stop (137, with its own line); the EXIT trap stops and waits for every job.
- The harness's guarantees, as above.

**Owed to Y:** none.

**Owed to the lead:**
- A file that swallows the INT now fails at the hard stop (137) with no retry. SIGTERM gave 124 and a retry. The retry logic is kept as briefed.
- The class 4 sites above.

**After-times** (base -1/32768):
- test_async_harness: 0.067/0.065 s against 0.128/0.130 (settrace 0.093).
- system_service: 23.6/26.8 against 23.7/27.4, same 30 failures as W1.
- fram_driver: 0.19/0.31 against 0.187/0.328.
- test_test_sh grew by about 7.5 s of inherent timeout waits (37.7 s now). The lead's table has no base for it.

**Runs:** everything I ran is logged in RUNS.md and has exited. Nothing of mine is running.

