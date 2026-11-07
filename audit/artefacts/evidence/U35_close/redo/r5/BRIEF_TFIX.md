# R5 unit tfix: the test-side fixes for the bench's day-2 failures (lead, 2026-11-06)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `tfix_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then `S/u35r/r5/DX5.md` (35 lines:
the read-only diagnosis; each line gives a class, a cause with file:line and a fix). Read each test and the product
path it names before changing anything; the diagnosis is a reading, not a proof, so check its claim in the code first.

## Owner ruling behind this unit (2026-11-06 11:05:17 UTC, verbatim)
"Test fix now (A)." (The test-side fixes, so they reach the bench with the next push today.)

## Your work (worktree `S/wt-tfix`, branch `audit/tfix`, at int `c4f56186`; create it; commit locally, never push)
Every DX5.md item classed (b), plus these (c)/(d) items:
- (c) rogue NTP and rogue DNS: the redirect in `tests_hardware/bench_control.py:268` (`-j REDIRECT --to-ports`); code
  change only, nothing is ever run against the network here.
- (d) loop lag 967 ms: `loop_lag_under_combined_load.py` also reports when (after `main()` started) its worst lag fell.
- (d) packet-fault tests: each probe failure states its reason instead of hiding it.
- (d) NTP E71 in `test_heap_at_peak`: the script's output is kept where the bench can read it after the run (the
  pytest log or the session's artefacts), not only parsed.
Out of scope, each waiting on the owner (do not touch, do not pre-empt): whether SGP40 logs W65 after an FRAM erase
(follow today's specification: W65 is expected after an erase, declare it where a test provokes it); the 413 body cut
in `test_concurrent_mixed_body_sizes` (test fix or a server-side drain); the product finding in item c (an overflow
escaping while SYSTEM's FRAM lock is held). The item-c test fix (record before the raise in the device script) is in.
Also out: the "first 200 after the RTC was set" item (the bench checks its boot log first).

## Never
No hardware: `tests_hardware` runs only with `--collect-only` or `--twin`. Never edit `src/`, `ext/`; never read
`arduino/`; never open `/root/.claude/`. Never weaken a check, never a skip: where a fix changes what passes (a reset
counted as a refusal, a wider timing allowance), the new rule must still fail on the real defect it guards, and your
hand-back says in one line per such fix why it is not weaker. Prefer measuring on the board to widening a tolerance.
A wait polls for its state with a deadline. Another unit (gtest) edits `tests_hardware/` at the same time: change only
what each fix needs, restructure nothing, so the two merge cleanly.

## Rules for the text
Text outside `audit/` cites no audit IDs, unit names or finding numbers. A choice carries "(agent, 2026-11-06)" or the
owner ruling it follows. Comment-block and line rules as CLAUDE.md states them (3 prose lines, a line over 120 counts
twice).

## Checks
`S/u35/lead/lint_direct.sh`; the three mypy passes; every changed `tests_hardware` file with `--collect-only`, and
`--twin` where it runs there; `tests_scripts` whole, once, under `S/u35/lead/heavy.lock` as common_r1 says (wait while
the lock exists; gtest uses it too); `test_device_script_facts.py`, `test_level_containment.py` and the comment cap
among them.

## Limits
Write only `tests_hardware/` and, if a test's documented behaviour changes, its line in `tests_hardware/README.md`. One
commit. Budget about 0.8 % of the week. Hand back by 13:45 UTC.

## Hand-back
`S/u35r/r5/HANDBACK_TFIX.md`, at most 25 lines, and return its path: per fix the file:line, one line on what changed,
the not-weaker line where it applies, and the bench's `PYTEST_K` for every test to rerun (one expression per tier);
lines in and out; each check with its result. Last line: "nothing of mine is running".
