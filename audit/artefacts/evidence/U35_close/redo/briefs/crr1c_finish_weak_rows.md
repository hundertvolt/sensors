# CRr1c: finish CRr1b's uncommitted weak-row fixes, its two hand-read finds, the dead suite helper (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first, then `S/u35r/briefs/crr1b_weak_rows.md` (your task's specification) and
CRr1b's hand-back `S/u35r/handbacks_redo/CRr1b.md`. Worktree `S/wt-u35crr1b`, branch `audit/u35-crr1b` at 4d6cf385:
CRr1b's edits to six files are there UNCOMMITTED. Logs in `S/u35/laneC/crr1c/` (CRr1b's in `S/u35/laneC/crr1b/` are
yours to read). Review CRr1b's diff yourself first (`git diff`); keep what is right, fix what is not, say which.

## Why CRr1b stopped (binding for you)
A safety check refused one of its commands: a `nohup bash -c "..."` chain that also ran `rm` on a scratch file, which
the checker could not inspect. It was correctly not retried, and nothing in it ran. You do not run that command or any
variant of it. Every script you run is a file you wrote first (under your log dir) and run as `bash <file>` or
`python3 <file>`, its content plain to read; never `bash -c` holding `rm`, never `nohup` chains; a deletion is its own
command with a literal path. If any command is refused, stop at once and hand back; never retry it in any form.

## What to do
1. The bites CRr1b designed (its "Bites still owed"; `S/u35/laneC/crr1b/tools/mkbites.py` holds the edits, never run:
   read it before using it), one scratch copy per bite, old form passing and new failing, each logged.
2. The runs CRr1b did not reach: tests/test_digital_twin_http_client.py, tests/test_sensortask.py on all six devices
   (TEST_DEVICE), each at both stages with build-standard directly, base (a scratch copy of 4d6cf385, as CRr1b's
   basetree) and head back to back per file, zero markers; tests_js/site-functions.test.js through `npm run test:unit`
   in the namespace (node_modules linked; CRr1b's lock check holds).
3. Commit item 1 (`U35 lane CRr1b: ...` is fine for CRr1b's work; your own commits `U35 lane CRr1c: <summary>`).
4. CRr1b's item 2 finds: (a) tests_scripts/test_generated_tree.py gains the removed-TOML case
   (`require_fresh()`'s length clause pinned), bitten by dropping that clause in a scratch copy of tests/_generated_tree.py;
   (b) tests/test_asy_uart_comm.py's six provoked faults checked only by membership (CRr1b lists :567, :616, :636, :2268,
   :2854, :2977): each asserts its exact entry (number and type, one entry per event; a repeat raises ErrCount with no
   new slot), each exact value read from a run first, bitten by a scratch edit; 6x-slower-than-base is not acceptable:
   time base and head back to back (the file is about 60 s per stage).
5. CRr1b's item 3: remove `_restore_is_all_or_nothing` and the four tests that exercise only it, after checking whether
   `_non_empty_slots`/`_counter` keep other callers (remove a helper only when nothing else reaches it; say which).
6. The verdicts (`was:<flag>` -> fixed, the new rows for item 4's cases) through review_verdicts.json, review.md
   re-rendered with review_rows.py.

## Checks
lint with `S/u35/lead/lint_direct.sh`; the mypy passes (stubs at `S/shared/typings`); the comment cap, test_citations,
test_decision_vocabulary, test_tunables_register, and every tests_scripts reader of a changed file. Other lanes share
the 4-core host: nice 19, one test run at a time. Past 80 tool calls, commit what is green and hand back at a seam.

## Not yours
src/, toolchain/, digital_twin/, every allow-list, audit/ records other than the review files. Do not push. Hand-back:
commits; per row its fix and bite with log paths; item 4 and 5 results; times; the new counts; last line "nothing of
mine is running".
