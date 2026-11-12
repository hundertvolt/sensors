# R5 unit gtest: board tests for eight behaviours the real board never proved (lead, 2026-11-06)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `gtest_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then SPECIFICATION.md E.6.6's rows
named below (each row's "why" column says what is missing), `tests_hardware/README.md` (tiers, fixtures, wear gates,
the budget table) and `S/u35r/r5/HANDBACK_R5C.md` (the last unit that added silicon tests here, and how).

## Owner ruling behind this unit (2026-11-06 10:20:31 UTC, verbatim)
"I would like all of the tests, except #9 for the reason it's almost no added value at a very high cost."
(#9 is the NTP failure modes against a scriptable responder; it becomes a limitation, item 9 below.)

## Your work (worktree `S/wt-gtest`, branch `audit/gtest`, at int `c4f56186`; create it; commit locally, never push)
Each test is real silicon work for the bench to run; it never needs a `src/` change. Read the row, the twin scenario it
mirrors and the product path before writing; a device script uses the shared helpers in `device_scripts/_shared/`.
1. `system-commands-instrumented`: a system command (reboot) arriving in the boot window, while the setup batch runs
   (`scenarios.a_command_right_after_the_first_answer_resets_cleanly` is the twin's): bench tier, zero wear.
2. `timer-pool-under-graph`: the product's failed-arm paths with the alarm pool emptied beside the running graph
   (`timer_alarm_pool_exhaustion.py` proves only the platform's ENOMEM): flash tier device script, zero wear.
3. `watchdog-fault-planted`: a device script ending or raising inside the running system (the row's `main()` ending
   and a raise escaping the supervisor's dead-task report), each stopping every feed, so the watchdog resets: flash
   tier, zero wear. Check first what `bench/test_reset_reasons.py`'s loop-end test already proves; do not duplicate.
4. `clock-step-on-silicon`: the RTC stepped forward and back under the running graph (`test_digital_twin_clock_jump`
   is the twin's): flash tier device script, zero wear.
5. `uart-load-flush`: a real config write during link traffic under the bench's API load: bench tier, one owned
   flash write per run behind `persistence_write`, its row in the README's budget table. The link here runs its normal
   transactions, which the 512 B ring is sized for; not a continuous stream.
6. `webserver-requests-bench`: a negative Content-Length over the bench's HTTP, and each refusal at the ceiling counted
   exactly once in `HTTPDropped`: bench tier, zero wear. The client gone mid-response stays a limitation (the row says
   why).
7. `reader-saturation-floor`: four zero-think-time `/status` readers beside an unchanged `DebugLevel` PUT: each reader
   answered at least the twin's floor, then a GET and a PUT each within the per-call cap: bench tier; confirm from the
   code that an unchanged value persists nothing (else it goes behind `persistence_write`).
8. `held-i2c-line-silicon`: the held SDA's one report (the first reader's `_init_done()`), asserted by neither silicon
   test today: add it to the existing test(s) in `flash/test_bus_concurrency.py`.
9. `ntp-responder-modes`: becomes an accepted limitation with the owner's reason, one sentence (quote above).
For each: the E.6.6 row says what silicon now proves (the gap words go), the test declares its `COVERS_TWIN_SCENARIOS`
by scenario id, and the README's tier-parity and owed lists follow.

## Never
No hardware: `tests_hardware` runs only with `--collect-only` or `--twin`. Never edit `src/`, `ext/`; never read
`arduino/`; never open `/root/.claude/`. Never weaken a check, never a skip; a wait polls for its state with a deadline.

## Rules for the text
Text outside `audit/` cites no audit IDs, unit names or finding numbers. A choice carries "(agent, 2026-11-06)" or the
owner ruling it follows. Comment-block and line rules as CLAUDE.md states them (3 prose lines, a line over 120 counts
twice).

## Checks
`S/u35/lead/lint_direct.sh`; the three mypy passes; every new or changed `tests_hardware` file with `--collect-only`,
and `--twin` where it runs there (a planted break seen failing where the twin can run it); `tests_scripts` whole, once,
under `S/u35/lead/heavy.lock` as common_r1 says (`test_level_containment.py`, `test_device_script_facts.py`,
`test_persistence_write_marker_completeness.py` and the comment cap among them).

## Limits
Write only `tests_hardware/` (new device scripts and tests, the changed tests, README.md), SPECIFICATION.md (E.6.6 rows
only) and BACKLOG.md if an owed line changes. One commit. Budget about 1.5 % of the week. Hand back by 13:30 UTC so the
bench can run them today.

## Hand-back
`S/u35r/r5/HANDBACK_GTEST.md`, at most 25 lines, and return its path: per item the test (file:line), tier, wear, what it
asserts in one line and the bench's `PYTEST_K`; lines in and out; each check with its result. Last line: "nothing of
mine is running".
