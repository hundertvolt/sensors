# T4r3c: the 2**30 wrap through the twin suite on the five remaining devices (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first, then `S/u35r/briefs/t4r3_ticks30_wrap.md` (the task) and the hand-backs
`S/u35r/handbacks_redo/T4r3.md` and `T4r3b.md` (state, the proof, the exact resume commands). Worktree `S/wt-u35t4r3`,
branch `audit/u35-t4r3` at f7d6962b (clean). Logs continue in `S/u35/laneT/t4r3/`; the scratch build and S/tc-t4r3
are kept for you.

## What to do
1. For each of dev, grkizi, klkizi, schlafzi and wozi, one device run at a time, T4r3b's resume command (read
   `audit/sweeps/ticks30_twin.py` and `S/u35/laneT/t4r3/tools/run.sh` before using them). Each run records the wrap's
   position in Run 11's window, the step across it, the binary hash before and after, and any rebuild line.
2. T4r3b's open thread: Run 11 runs shorter at 32768, so the -1 placement lands later there (arzi 0.809). A device
   whose 32768 position is 1 or more is a placement miss: give that stage its own place run and run it again placed;
   never count the miss.
3. Any failure is a wrap-safety defect until root-caused (T4r3's brief item 4): never retried away.
4. Then T4r3b's finalize step (`S/u35/laneT/t4r3b/finalize.py`; read it first), its "State (partial)" paragraph
   dropped, timing.md's 2**30 section complete; commit `U35 lane T4r3c: <summary>`.
5. The F.1 sentence (T4r3b's, with the final figures and date) handed back for D3r.
6. Delete S/tc-t4r3 and the scratch build with T4r3b's literal command when done, and say so.

## Notes
Shell rules (binding): scripts as files you wrote, never `bash -c` holding rm, never nohup chains; a deletion is its
own command with a literal path or "${var:?}"; a refused command stops you. Your long runs are the bulk: run them in the
background and keep your tool calls for checking and recording. nice 19; RUNS.md lines; disk check first. Last line
"nothing of mine is running".
