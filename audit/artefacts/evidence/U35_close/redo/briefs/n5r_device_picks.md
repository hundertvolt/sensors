# N5r: no test picks its device by name; the wiring scanner's comprehension scope (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Worktree `S/wt-u35n5r`, branch `audit/u35-n5r` at `df670c35` (656fc82 plus
F1r, F2r, F4b merged; rebuild it with `S/u23/rebuild.sh` before the first run); logs in `S/u35/laneR/n5r/`.
Your brief is the "## blocks_n5.md: N5" section of `S/u35r/recovered/briefs/blocks_n4_n5_d3.md` (the lost block's; its
line numbers are from an older head, re-locate them), with its base, branch, worktree and log dir replaced by the ones
above. The owner's device ruling, verbatim: `S/u35r/recovered/owner_rulings_after_LN118.md`. The lost N5's outcome (the
note at that section's end: `_BOARD`, `_ISL29125_BUS`, `_board_plan(**buses)`, `_wire(**buses)`) is a map, not proof:
re-derive it; you may reach a different form, and say why.
Added: item 3, the red that form caused last time (`S/u35r/recovered/briefs/blocks_c_parts.md` "## CM2" item 1):
`tests_scripts/test_twin_wiring_contract.py::test_every_key_a_consumer_reads_off_a_plan_is_declared` read a
comprehension's loop variable as a plan key. If your change makes it red, give each comprehension its own scope as
Python 3 does, and show that a planted undeclared key read still fails it (a scratch copy). If it stays green, say so.
Not yours: `src/`, `digital_twin/`, `scripts/`, `buildgen/`, the twin CI suite, `tests/test_digital_twin_loop_end.py`,
SPECIFICATION.md (stale lines to the hand-back), audit/. Commit subject `U35 lane N5r: <summary>`, the two trailers; do
not push. Hand-back: each site with its verdict, item 2's lines, the checks with log paths; last line "nothing of mine
is running".
