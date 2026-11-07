# T4r3: a real 2**30 tick wrap under every L1 tick user and the twin suite (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Base, worktree and branch named at launch; logs in `S/u35/laneT/t4r3/`.
Specification: audit/actions/U35.md A.U35.32 (its Change line (1)-(3)); audit/b3/timing.md's 2**30 section (what B1
ran and what it left); `S/u35r/verify/V3.md` rows 108 and 112. The lost B2b2 had built this and written
`ticks30_batch.py` (lost; `S/u35r/recovered/lead_notes_119_148.md`'s B2b2 line); T4b2's plan for (2) is in
`S/u35r/recovered/handbacks/T4b2_final.md` item 4. Re-derive everything.

## Items
1. The build: `audit/sweeps/ticks30_build.sh build <scratch>` into your own scratch dir under S (never the toolchain;
   the script refuses that), then its `check`. The script hard-codes `py=/home/user/sensors/.venv/bin/python`, which
   this container may lack: make it take the interpreter from the environment with that as the default, nothing else.
2. (1) Every L1 file using ticks (A.U14.34's call-site list: find it in audit/actions/U14.md, re-located on your base,
   plus any tests/ file whose code under test reads `ticks_ms`/`ticks_us`/`ticks_diff`/`ticks_add` and is not driven
   by `DrivenTime`; derive the file set by search and state it): each at both GC stages on build-ticks30 with
   `TICKS30_WRAP_IN_MS` at a quarter, half and three quarters of that file's measured wall clock (your own
   build-standard run of it, or the base table), three runs per file per stage, zero memory markers, every result in
   timing.md's 2**30 section (file, wrap points, result, time). A batch driver in audit/sweeps/ (resumable).
3. (2) The twin suite on build-ticks30 for every derived device, both stages, with the wrap placed inside Run 11's
   cycle window (its start offset measured from a plain suite log of that device): one device run at a time. Find how
   the suite selects its binary; run it through a private toolchain copy (`cp -a S/tc-int S/tc-t4r3`, disk check
   first, its binary swapped for build-ticks30 or the suite pointed at it), and prove before the long runs that the
   suite really ran build-ticks30 (the period read from inside a run) and that `scripts/_unix_port.sh` did not rebuild
   it. Never the shared toolchain. Delete S/tc-t4r3 and the scratch build when done and say so.
4. (3) Any failure is a wrap-safety defect: root-cause it, never retry it away; a fix in src/ comes to the lead with
   its evidence and a proposed L1 test using the existing ticks30 test clock (tests/_ticks30.py) so the regression
   stays covered without the scratch build; a fix in a test or the twin is yours, red first.
5. SPECIFICATION.md F.1's run sentence: hand back the restated sentence for D3 (A.U35.32's Blast docs text, with what
   was actually run).

## Proof and checks
Long runs inside `unshare -n S/u24/ns_xdg.sh`, nice 19, RUNS.md lines, disk check before each; other lanes share the
host, so one run at a time. ruff and the host mypy pass on any changed script; test_citations,
test_decision_vocabulary. Past 80 tool calls, commit what is recorded at a seam (the L1 table first) and hand back
the rest with the exact command to resume.

## Not yours
src/, toolchain/, digital_twin/ (a twin fix comes to the lead first), every allow-list, audit/ records other than
timing.md's 2**30 section and your sweep scripts. Commit subject `U35 lane T4r3: <summary>`, the two trailers; do not
push. Hand-back: commits; the file set and how it was derived; every run's result with log paths; the proof the suite
ran the 2**30 binary; any failure's root cause; the F.1 sentence; last line "nothing of mine is running".
