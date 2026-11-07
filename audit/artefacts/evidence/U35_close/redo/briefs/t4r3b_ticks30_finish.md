# T4r3b: finish the 2**30 wrap runs (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first, then `S/u35r/briefs/t4r3_ticks30_wrap.md` (your task) and T4r3's hand-back
`S/u35r/handbacks_redo/T4r3.md` (state, facts, the exact resume command). Worktree `S/wt-u35t4r3`, branch
`audit/u35-t4r3` at 165489fd (clean). Logs continue in `S/u35/laneT/t4r3/`. The scratch build
(`S/u35/laneT/t4r3/build`) and the private toolchain `S/tc-t4r3` (build-standard swapped for build-ticks30) are kept
for you; delete both when done, with the literal-path command T4r3 gives, and say so.

## What to do
1. Item 2's remaining runs: T4r3's resume command (wrap, then rewrap for the four short files whose 3/4 point fell
   after their exit), then `table` and the timing.md table replaced. Every one of the 654 runs recorded.
2. Item 3: `audit/sweeps/ticks30_twin.py` per derived device, both stages, one device run at a time. Before the long
   runs, prove on one device that the suite ran build-ticks30 (the period read from inside a run, the binary's hash
   unchanged before and after, no "rebuilding the Unix ports" line) and that the wrap fell inside Run 11's window.
3. Any failure: root-cause it; never retry it away (T4r3's brief item 4).
4. Item 5: the F.1 sentence with the real figures and date, handed back for D3r.

## Notes
CFr's planted-fault runs share the host and once left four interpreters running for an hour (now stopped); your load
gate may wait on them: wait, never kill another lane's process. Run scripts you wrote to files (`bash <file>`), never a
`bash -c` holding rm or a nohup chain; a deletion is its own command with a literal path; a refused command stops you.
nice 19; RUNS.md lines; disk check before long runs (keep 3 GB free). Commit what is recorded at a seam; past 80 tool
calls hand back with the exact resume command. Last line "nothing of mine is running".
