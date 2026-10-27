# CRr1b: the review's twelve open weak rows, three files read by hand, one dead suite helper (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Base, worktree and branch named at launch; logs in `S/u35/laneC/crr1b/`.
The second block of CRr1: read `S/u35r/briefs/crr1_review_every_test.md` (its items 3-4, proof and checks, "Not
yours") and CRr1's hand-back `S/u35r/handbacks_redo/CRr1.md`. The rows, the tool and the verdicts are in your base
(audit/b3/review.md, audit/sweeps/redflags.py, review_rows.py, review_verdicts.json): update verdicts through them and
re-render review.md with review_rows.py, never by hand.

## Items
1. The 12 open weak rows CRr1 lists (tests/test_asy_base_classes.py, test_asy_fram_driver.py, test_digital_twin_
   http_client.py, test_asy_ntp_client.py, tests/_sensortask_scenarios.py, tests_js/site-functions.test.js; re-locate
   each by its test name): each fixed with its goal kept, per review.md's planned fix (or a better one, stated). Each fix
   bites as CRr1's did: a scratch edit of the input or expectation shows the old form passing and the new one failing.
   A row whose fix would need a product change: hand it back with its evidence, unfixed.
2. CR2's lost fixes in three files the scan does not flag (tests/_generated_tree.py, tests/test_asy_sgp40_driver.py,
   tests/test_asy_uart_comm.py; CR2 changed 7, 12 and 10 lines there): read each file's tests by hand against
   A.U35.03's red-flag list and the scan's stated blind spots (review.md's "cannot see" list), and fix what is weak,
   bitten as above. If nothing is weak, say per file what you checked; that is a valid result.
3. `_restore_is_all_or_nothing` (scripts/_digital_twin_ci_suite.py near :790): CRr1 found it called by no run, only by
   tests_scripts/test_digital_twin_ci_suite_errcount.py near :105-128; it became dead when Run 5b began asserting the
   exact ring. Lead's decision (test tooling, no wear): remove it and the tests that exercise only it, after you confirm
   by search that nothing else reaches it (`git grep`, getattr strings, the suite's run table). Its review.md row and
   any README or SPEC line naming it updated (a SPEC line: hand it back for D3r).

## Proof and checks
Each changed MicroPython file at both stages with build-standard directly, zero memory markers, base and head timed
back to back per file (CHECKLIST 14); tests_js changes with `npm run test:unit` in the namespace (node_modules linked
after checking the lock, redo_common.md); tests_scripts readers of changed files; lint with `S/u35/lead/lint_direct.sh`;
the mypy passes; the comment cap, test_citations, test_decision_vocabulary, test_tunables_register. No scripts/test.sh
or twin CI against the shared toolchain. Commit subject `U35 lane CRr1b: <summary>`, the two trailers; do not push.
Hand-back: commits; per row its fix and bite with log paths; item 2 per file; item 3's search and removal; the new
counts from review_rows.py; last line "nothing of mine is running".
