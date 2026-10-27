# CRr1: review every test (A.U35.03, A.U35.37): the scan, the rows, the fixes it finds (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Base, worktree and branch named at launch; logs in `S/u35/laneC/crr1/`.
This redoes lane C's CR and CR2 (c564719, 146df65; lost in the container reset). What survives of them is a map, not
proof: `S/u35r/recovered/lead_notes_119_148.md` (the CR line: audit/sweeps/redflags.py, review_rows.py,
audit/b3/review.md with 8,514 rows; CR2's 14 fixes), the CR branch diff stat at the end of
`S/u35r/recovered/handbacks/CR4_final.md` (which test files CR2 touched, and how much), and CR3's counts in
`S/u35r/recovered/handbacks/CR3_final.md` (8,514 rows, 284 flagged; biting 8,356, justified 133, fixed 24, weak 1).
Re-derive everything on your base. The specification is audit/actions/U35.md A.U35.03 and A.U35.37 (their Change
lines), audit/b3/review.md's header (its completion rule) and the owner's rulings in
`S/u35r/recovered/owner_rulings_after_LN118.md` (Question 2 on planting faults is binding: plants only for complex
measurement tests, never for the straightforward majority).

## Items
1. `audit/sweeps/redflags.py` (rewritten; a CPython `ast` scan, run with `python3 -I`): every test in tests/,
   tests_scripts/, tests_js/ and tests_hardware/ (flash, bench, manual, device scripts) and every registered twin
   scenario, one record per test, each of A.U35.03's red flags as a named, separately counted detector, and the pass-3 C2
   credit rule (only an `assert`, `AssertionError` or `pytest.raises` in the test or a helper it calls counts; never a
   `raise` in the code under test). Helper resolution must follow subscripts, attributes and f-string keys well enough
   that a flag is a candidate, never a verdict: a known false-flag shape (CR3: facts read through f-string keys; the
   lead's: a subscript index read as a code literal, as test_error_catalog's scanner once did) gets a detector test.
   tests_js: the `it(`/`test(` bodies, `expect(` as the credit (state what the scan cannot see there).
2. `audit/sweeps/review_rows.py` renders `audit/b3/review.md` (header kept; one row per test: file:line, test, level,
   verdict, red flag, fix or "biting as is"). Counts per scope, per flag, per verdict at the top, from the script.
3. Every flagged row read and given a terminal verdict by you (biting with the reason a flag is false; justified with
   its reason, stated in the test or citing what already states it; weak or blank: fixed). A.U35.37's normal-situation
   scan inside it: each hit classed (a) normal situation tolerating a code: the product question goes to the lead with
   its evidence, never a silent test change; (b) a provoked fault expecting its code, kept exact (number and type, one
   entry per event); (c) a hardware test tolerating a code: the in-place reason, or it stops tolerating it.
4. Fixes for weak and blank tests, goal kept, in the same test file; each fix bites: a straightforward test by a
   scratch edit of its input or expectation showing the old form passes and the new one fails; a complex measurement
   test by a planted fault in a scratch copy of the code under test. CR2's 14 fixes are re-found by your scan or
   explained (the diff stat names their files: tests/_generated_tree.py, _sensortask_scenarios.py, test_asy_bmp3xx,
   dns_client, isl29125, notification_service, sgp40, system_service, uart_comm, wifi_service, test_math_helpers).
   A product defect a row shows goes to the lead with its evidence (OR12.a), not into the test.
5. T4r1's `_restore_is_all_or_nothing` (scripts/_digital_twin_ci_suite.py, called only by a tests_scripts reader): a
   row with its verdict (dead suite code under the library rule, or a kept helper with its reason); change nothing
   there, hand it back.
6. The four identical `_stack_overflow()` copies (tests/test_asy_bmp3xx_driver.py, test_asy_isl29125_driver.py,
   test_asy_print_log.py, test_asy_webserver_service.py; lane CE2r's find): one shared helper under tests/ beside
   tests/_untraced.py, each file importing it, each file green at both stages and under `untraced()` as now.
Device-script facts, the bench log fixture and marker and the flash tier's `logs` fact are CRr2's, not yours: give
their rows the verdict "CRr2" so the count stays whole.

## Proof and checks
Each changed MicroPython test file at both stages with build-standard directly, zero memory markers, times against the
base table (CHECKLIST 14); changed tests_scripts files and their readers under pytest; changed tests_js files with the
pinned Node, after checking `S/wt-base/node_modules` matches your lock (link it, do not install); tests_hardware changes
`--collect-only` and `--twin` only. ruff, the mypy passes (stubs at `S/shared/typings`), the comment cap,
test_citations, test_decision_vocabulary, test_tunables_register. Your base has a changed `toolchain/`: no
scripts/test.sh, no twin CI against the shared toolchain. Other lanes run: nice 19. Port-binding runs in the namespace.
Past 80 tool calls, commit what is green at a seam (the tool and rows first, then the fixes) and hand back the rest.

## Not yours
src/, toolchain/, digital_twin/, scripts/ (rows only), every allow-list (hand back the row you need), other audit/
records. Commit subject `U35 lane CRr1: <summary>`, the two trailers; do not push. Hand-back: commits; the counts
(rows, flagged, per verdict, per flag); the fixes with their bites and log paths; the product questions; what the scan
cannot see; last line "nothing of mine is running".
