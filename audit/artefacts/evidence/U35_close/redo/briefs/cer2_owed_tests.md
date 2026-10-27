# CEr2: the owed direct tests for every uncovered src site CEr1 classed (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first, then CEr1's hand-back `S/u35r/handbacks_redo/CEr1.md` ("Owed tests" and the
classes), `audit/b3/e51.md` and `audit/sweeps/e51_verdicts.json` in your base, and the owner's dead-code rule in
`S/u35r/recovered/owner_rulings_after_LN118.md`. Base, worktree and branch named at launch; logs in
`S/u35/laneE/cer2/`. Specification: audit/actions/U35.md A.U35.41 and A.U35.04.

## Items
1. One direct test per owed row, in the test file CEr1 names, driven by the input CEr1 names: the 11 class (a) lines
   (reachable, untested) first, then the class (b) guards exercised through a double, and the class (d) feature
   (webserver without a system-command handler answers Invalid). Re-locate every line on your base first. Each test is
   proven to reach its line by the coverage run of item 5. Plants follow the owner's Q2 ruling (verbatim in
   `S/u35r/recovered/owner_rulings_after_LN118.md`): not for the straightforward tests, which are most of these. Plant
   only for the complex ones, where a test could pass without testing what it claims: the uart_driver overrun, lap and
   never-block guards, the C-stack-overflow re-raise, the cancel during the double initiation, and the bmp3xx run
   bound. A plant goes in a scratch copy of src/ and is never committed.
2. If a test exposes wrong behaviour (a class (a) line that does the wrong thing when reached), stop that row and hand
   it back with the evidence: it is a firmware fix for the lead, never changed by you. A guard double that cannot be
   built without editing src/ goes back to the lead too.
3. The bmp3xx test (705: the bus goes down between reset()'s two sessions) under a run bound, so a reset() that never
   writes the soft reset fails the test and the file still finishes.
4. The three type-narrowing sites with no in-place comment (CEr1: uart_comm 601 and 902, uart_link 186): a one-line
   comment each, in the form the other narrowing sites use (read them). These are src/ edits, comments only. Rebuild
   with `S/u23/rebuild.sh` after them, and run the two modules' test files at both stages.
5. e51_verdicts.json: each row you cover moves to covered with its test named. Re-render; `--check` rc 0. Then one
   coverage run of only the changed test files (`tests/_coverage_runner.py` with build-settrace, the way scripts/test.sh
   --coverage runs one file) shows each owed line executed. If any line stays uncovered, say why. Use the binaries
   built from your base's toolchain/: `S/tc-int/micropython/ports/unix/build-settrace/micropython` and
   `.../build-standard/micropython`. Run them directly and never rebuild them; the shared /root/pico-toolchain
   binaries are older.

## Checks
Every changed MicroPython test file at both stages with build-standard, zero memory markers, its time before and after
(CHECKLIST 14); lint with `S/u35/lead/lint_direct.sh`; the mypy main pass; test_comment_block_cap, test_citations,
test_decision_vocabulary, test_code_conventions. No scripts/test.sh run needed. Shell rules (binding): scripts as files
you wrote, never `bash -c` holding rm, never nohup chains, never a `tail --pid` wait, rm only as its own command with a
literal path or "${var:?}", a timed-out run's children killed; a refused command stops you.

## Not yours
src/ beyond item 4's three comments, toolchain/, digital_twin/, every allow-list. Commit subject `U35 lane CEr2:
<summary>`, the two trailers; do not push. Past 80 tool calls, commit what is green and hand back at a seam, with the
rows left. Hand-back: commits; per row the test, its reach proof and its plant; any wrong behaviour found; the coverage
result; times; last line "nothing of mine is running".
