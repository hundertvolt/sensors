# CRr2b3: the bench log check sees every test, the provoking ones included, and across a test's own clears (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first, then `S/u35r/briefs/crr2_hardware_rows.md` (the task: its proof, checks,
"Not yours" and shell discipline apply), `crr2b2_bench_log_check_rest.md`, and the hand-backs
`S/u35r/handbacks_redo/CRr2b.md` and `CRr2b2.md`. Worktree `S/wt-u35crr2b`, branch `audit/u35-crr2b` at 2d73a934
(clean). Logs in `S/u35/laneC/crr2b3/`; CRr2b2's class map is `S/u35/laneC/crr2b2/bench_class.txt`.

## Why (the lead's review of 2d73a934; the lead's call: test code, no wear, a stronger check)
Two gaps remain in the check as built, and the design came from the lead's own brief:
- `provokes_log("<why>")` exempts the whole test. In the 29 marked tests (the ceiling, heap and sweep runs among them,
  where an unexpected caught allocation failure is most likely) an E or W entry the test did not set out to provoke
  goes unseen.
- 88 `reset_all_error_logs()` calls sit in bench tests. Anything logged before a test's own clear is erased before the
  after-read, and `cleared=True` then credits only what follows.
Plus a find of CRr2b2's: test_isl29125_calibrate_command_push can end with a calibration still running, whose later W75
ISL_CAL_TIMEOUT would land in the next test's window.

## Items, in order (each red first, committed green on its own)
1. The marker names what the test provokes. `provokes_log` keeps its reason and gains the expected entries, each as
   logger, kind and catalog name (resolved through tests/_error_codes.py; a name with no live row is refused at
   collection). The fixture runs for marked tests too and fails on any E or W entry outside the test's set, naming it
   as today. It does not require an expected entry to appear: the tests assert their own provocations. Each of the 29
   gets its exact set from src (the logger call sites that test reaches, with file:line in your map); a reason alone
   is refused. Where a set depends on timing or on which of several paths ran, list every entry src can produce there
   and say why. Tests for the marker form, the refusal and an outside entry in a marked test; plants.
2. Clears inside a test. `reset_all_error_logs()` reads GET /status before its PUT and keeps that read. The fixture then
   checks each segment between the test's bounds and its clears (before -> first pre-clear read, each clear's after ->
   the next pre-clear read, the last -> after) against the same rule. This is CLAUDE.md's "read the FRAM logs before
   any ResetErrors" applied by the harness. The read adds no write. Its failure is bounded as `_read_logs()` is. Tests:
   an entry logged then cleared inside an unmarked test fails it (red on 2d73a934); a clear with nothing before it
   passes.
3. Cross-test bleed. Re-locate the calibrate test and read src: can W75 land after the test ends? If so, the test waits,
   bounded, until the calibration run has ended, and asserts how it ended. Then scan every bench test for device
   activity still in flight at its end that can log later (a calibration, a retry timer after an outage, a pending
   reboot, a background load) and list each with src lines. For each, show it settled or make the test settle it.
4. audit/sweeps/redflags.py: `hw_no_log` (and any other flag reading the test's source segment) is satisfied today by a
   decorator's text, so the marker's reason silences it. The segment for those flags is the function's body and
   helpers, never its decorators. A self-test, red first. Re-render. The rows that reappear get their verdicts: fixed,
   covered by item 1's check, named. `--check` rc 0.

## Not this block
The flash tests' markers and the flash fixture are CRr2c's. The overlap fix in the SCD30 sibling script and the HTTP
bench counterpart comes after this block. Commit subject `U35 lane CRr2b3: <summary>`, the two trailers; do not push.
Past 80 tool calls, commit what is green and hand back at a seam. Hand-back: commits; per item the evidence with log
paths; the 29 sets (counts per logger); the bleed list; the review_rows.py counts; the files whose twin record changes;
last line "nothing of mine is running".
