T4r3b hand-back, saved by the lead from the message it sent (2026-10-27). Commits 7d31c0b5, f7d6962b on audit/u35-t4r3 (on 165489fd).

T4r3b hand-back (worktree S/wt-u35t4r3, branch audit/u35-t4r3). Two commits on 165489fd, not pushed, nothing uncommitted: **7d31c0b5** (L1 complete, twin driver gains a load gate and a proof run) and **f7d6962b** (the twin scan fix; arzi at both stages). I stopped at the tool-call valve at a device seam. 1 of 6 devices is done for item 3.

**Item 2 (L1): done, all 654 runs green.**
- 109 jobs: 84 files, with the five PER_DEVICE files run once per device. The set is derived by `ticks30_batch.py derive`: every tests/test_*.py whose import closure reaches a module whose code names ticks_ms/us/diff/add.
- Each job ran at ¼, ½ and ¾ of its build-standard wall clock, at both GC stages.
- Every run exited 0 with zero memory markers and read period 1073741824 from inside the run. Its start tick was exactly 2**30 minus its wrap point (all 690 runs), and the counter crossed.
- Each run's test summary is identical to its build-standard run, skip counts included.
- Six short files exited before a later wrap point, not four: config_manager, crc_checks, twin_http_client, twin_rp2_constants, twin_unix_port_unretrieved_report and fakes. The 10 runs that crossed nothing passed. `rewrap` re-placed all 36 of those six files' runs, all green.
- 8 runs waited in the load gate (at most 610 s). None was started past the gate.
- The table in timing.md's 2**30 section is replaced. Records are in S/u35/laneT/t4r3/l1/results.jsonl, logs in S/u35/laneT/t4r3/l1/logs/.

**Item 3 (twin): proof done, arzi done, 5 devices left.**
- **Proof, on arzi, before any long run:** Run 11 alone with the wrap at 168406 ms crossed one wrap at 0.491 of its window. The step across it was 106 ms (1073741763 to 45), which reads the 2**30 period from inside the run. The binary was build-ticks30's sha256 (7c241764…) before and after, the suite launched the copy's path, there was no "rebuilding the Unix ports" line and zero markers.
- arzi -1: PASS, 289 OK, 0 FAIL, the wrap at 0.511 of the window, 559 s.
- arzi 32768: PASS, 289 OK, 0 FAIL, the wrap at 0.809 of the window, 533 s.
- Before the twin runs I removed frozen_modules and build/generated_html, as CHECKLIST 13 asks. Logs are in S/u35/laneT/t4r3/twin/.
- **Resume**, one device per run, from the worktree, for each of dev, grkizi, klkizi, schlafzi and wozi: `S/u35/laneT/t4r3/tools/run.sh twin_<dev> "python3 -I audit/sweeps/ticks30_twin.py $S/u35/laneT/t4r3/twin $S/tc-t4r3 $BIN <dev>"`, with BIN=$S/u35/laneT/t4r3/build/micropython/ports/unix/build-ticks30/micropython. Then re-run `python3 -I S/u35/laneT/t4r3b/finalize.py <wt> S/u35/laneT/t4r3 S/u35/laneT/t4r3/twin <day>` and drop its "State (partial)" paragraph.
- **Open thread:** the -1 placement serves both stages, and Run 11 runs shorter at 32768 (1796 samples against 2067), so the wrap lands later in the window there (0.809). If any device's 32768 position comes out at 1 or more, that run is a placement miss: it needs its own 32768 place run, not a retry.

**Item 4 (failures):** no wrap-safety defect found. The one red was my driver's: its suite-log marker scan matched the suite's own passing line `OK: … log carries none of ('MemoryError', 'memory allocation failed')`. T4r3's original scan had the same flaw. Fixed red first: the old scan flagged the clean proof log; the new one clears it, and still catches a planted allocation failure and the same gate's FAIL line (S/u35/laneT/t4r3b/bite_markers.py, rc 0). The proof then ran again.

**Item 5, the F.1 sentence for D3r** (true for the twin half only after the resume): "Wrap safety was run once on a scratch Unix-port build with the `2**30` tick period, its counter started just before the wrap: every L1 test file whose code reads ticks (84 files, 109 runs with the per-device files on every derived device) passed with the wrap a quarter, half and three quarters into its run, and every derived device's twin suite passed with the wrap inside Run 11's soak window, at both GC stages and with no memory marker (agent, 2026-10-27)."

**Checks:** ruff and host mypy clean on ticks30_twin.py and ticks30_batch.py; test_citations and test_decision_vocabulary 21 passed, before each commit.

**Kept for the resume, not deleted:** S/tc-t4r3 and the scratch build. When the resume finishes, delete both: `rm -rf "${S:?}/tc-t4r3" "${S:?}/u35/laneT/t4r3/build"`.

**Facts for the lead:**
- Two container restarts (about 00:32 and 01:28) cut wrap3 and wrap4. Both times the results file ended on a whole record; the one run cut mid-way had no record and was re-run.
- The CFr orphans were reported to you and stopped by you.
- `ss` is missing in this container, so the suite's port-53 holder diagnostic prints "command not found". It ends in `|| true` and does not affect the result.

Runs: wrap4 was cut by the restart; wrap5 rc 0; checks2 and checks3 rc 0; twin_arzi rc 1 (the false marker hit above); twin_arzi2 rc 0.

nothing of mine is running
