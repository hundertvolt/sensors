# N4r: the ResetErrors probe holds NTP still; test.sh's tier order; the tier's host writes (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Base, worktree and branch named at launch; logs in `S/u35/laneN/n4r/`.
This redoes block N4 of U35, whose merge (33d9ad8) was lost in the container reset. Its original brief survives
verbatim in `S/u35r/recovered/briefs/blocks_n4_n5_d3.md` (section "blocks_n4.md"): read it, it is your task, with the
changes below. Only a partial summary of its outcome survives (the note under that section); treat it as a lead, not a
fact, and re-derive everything on your base.

## Changes to the original brief
- Base, branch, worktree and logs are the ones named here and at launch; decision tags "(agent, <date -u>)".
- Your files: `tests_js/live-backend-put-matrix.test.js` and the tests_js helpers it imports, `scripts/test.sh`,
  `tests_scripts/test_test_sh.py`, and for item 3 only the tests_scripts files whose writes you measure. SPECIFICATION.md
  lines your change makes stale: hand them back for D3r with their line.
- Item 1: LEAD NOTES 122-123 are lost; the root cause above (arzi's string case leaves NTPHost unresolvable, so E73
  climbs by itself) is the lead's summary: reproduce it before fixing it.
- Item 2: B2a's 1350.2 s and its no-frozen log are lost. Measure both arms yourself, back to back on the same machine
  state: one `scripts/test.sh` at -1 on your base, one with your change; state the noise you assume. The lead tells you
  when the machine is quiet enough; until then do items 1 and 3 and the item-2 test. The no-frozen failure count is
  yours to re-measure (one tests_scripts session with frozen_modules absent, in a scratch copy of the worktree).
- Item 3: one tests_scripts session with its basetemp retained, `du` per test file, then the basetemp deleted.
- Toolchain: your base has a changed `toolchain/`, so every `scripts/test.sh` run uses your own copy:
  `cp -a S/tc-int S/tc-n4r` and `PICO_TOOLCHAIN_DIR=S/tc-n4r`; never run its setup; never the shared toolchain. Delete
  the copy when you are done and say so.
- Every port-binding run (npm test, test.sh) inside `unshare -n S/u24/ns_xdg.sh`, under `nice -n 19`, each with its
  RUNS.md start and done lines; one test run at a time in your worktree.

## Not yours
src/, digital_twin/, toolchain/, ci.yml, audit/ records, every allow-list (hand back the row you need). Commit subject
`U35 lane N4r: <summary>`, the two trailers; do not push. Hand-back (at most 30 lines): commits; item 1's root cause as
reproduced, test-first and bite results and the npm counts; item 2's two measured walls and the choice; item 3's table
(top files, bytes) and what changed; anything for D3r with its line; last line "nothing of mine is running".

## Setup note
S/wt-u8 no longer exists: link your worktree's `node_modules` to `S/wt-base/node_modules` (as S/wt-u35int does), after
checking that your base's package-lock.json hashes equal S/wt-base's; if they differ, stop and hand back.
