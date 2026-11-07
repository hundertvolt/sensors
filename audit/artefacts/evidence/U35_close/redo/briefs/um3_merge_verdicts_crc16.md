# UM3: the UART work onto the integration head, its walk verdicts, and the one unexplained red (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; "Quality comes first" and "Efficiency" are binding, and it says how
you hand back), then UM2's hand-back `S/u35r/handbacks_redo/UM2.md`, then `S/u35r/briefs/um2_uart_catches_echo.md`
(its rules stand). Worktree `S/wt-u35um1`, branch `audit/u35-um1` at d57ad57b (clean). Logs in `S/u35/laneB/um3/`.

## The lead's review of UM2 (binding)
- Its three commits are kept: option C as the owner chose it, the changelog entries A17/B90/B91, the docs, and the
  dev echo answered from its stored pieces (a design-level fix, no catch, no wire change). The silicon reasoning for
  not taking the twin's largest-block reading is accepted.
- Its walk could not run on its base (845 lines apart before BR4's merge). On the integration head it can, and every
  row is terminal there; UM2's 7 new `read_at()` call rows need verdicts.
- test_digital_twin_generated_boot's CRC16 dev link test failed once on 3a24c773 and has no root cause. No failure is
  called a flake without one, and it sits in the UART path UM2 changed, so it is settled before this work merges.

## Items, in order (each committed green on its own)
1. Merge the integration head 158058ed into your branch (a merge commit; never a rebase). Generated audit files are
   re-rendered by their tools, never hand-resolved; where both sides changed code, keep both behaviours. Rebuild.
2. The raising walk on the merged tree: verdicts for UM2's open rows (the 7 `read_at()` rows and any other), in the
   verdict files' conventions; the walk, e51 and review_rows checks green. review.md rows for UM2's new tests.
3. The CRC16 red: reproduce it (the test in a loop at both stages, with and without host load, on ad624cca and on
   your head, so the base tells whether UM2's change brought it). Name the root cause with evidence: a log, a timing,
   a bite. Fix where it lies (product or test), with a red-first test or a bite that fails without the fix. If it
   never reproduces, say how many runs under which load, and what the code reading excludes.
4. Checks on the head: every test file importing asy_uart_comm, asy_uart_driver, asy_uart_link_driver or
   asy_base_classes at both stages (PER_DEVICE files on all six devices), zero memory markers; the whole
   tests_scripts tier; lint_direct, the six mypy passes, the three audit checks.

## Hand-back (the file, per redo_common)
Commits; the merge's conflicts and how each was resolved; the verdicts; the CRC16 cause with its evidence and fix;
the checks; last line "nothing of mine is running".
