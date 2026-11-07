B1 hand-back (lane B, block 1). Branch audit/u35-b in S/wt-u35b, from f3fff0e. Head d7d2f0c. Commits: d22a9e8 (A.U35.01), 3ffc195 (104), 87a4934 (137), e1ad71f (108, 138, 141, 153), d7d2f0c (generator fix). Nothing uncommitted, nothing pushed, nothing of mine running. I used 66 tool calls.

**Steps by verdict**
- A.U35.01: applied in d22a9e8. audit/b3/ now holds 11 files, each with its requirement, completion rule and row format.
- 102 (PROC.022): partly. The headers are in. The campaign still has to fill review, faults, matrices, e51, load, timing's columns and A.U18.05's idle measurement. SCR.024 had already landed (check-only).
- 104: applied. `audit/b3/raising_walk.py` walks all 7 modules: 1248 sites. All 5 raises are classified. Of the call groups outside a broad try, 414 are left "open" for a per-site proof. The walk is at f3fff0e; lanes P and Y edit 4 of these modules, so re-run it on the integration head.
- 137: applied, mechanically. `levels_walk.py` writes levels.md (137 files against L0-L4) and intent.md (236 rows). 6 catalog codes are named by no test: 5 in asy_base_classes.py:82-86 (CFG_SET_RAISED, PUSH_RAISED, CFG_SNAPSHOT_RAISED, RECOVERY_READ_RAISED, RECOVERY_WRITE_RAISED) and UART_WRONG_KIND in asy_uart_comm.py:137. Still open: the schema bounds, None and NaN rows, and the SET ladder.
- 138 and 153: partly. `conformance_walk.py` writes 120 rung rows from SUPP_recovery.md (236 of their L3/L4 cells go to queue_c) and 6 owner rows with the tests I found by grep. Every cell still needs B2's review.
- 141: applied. queue_c.md has 11 items, each mapped to an H row in audit/actions/C.md.
- 108: applied for this block's part (build, OF-32, wrap tests). Also open: two notes about wraps that were not exercised, in timing.md.

**The 2**30 results** (audit/sweeps/ticks30_build.sh, recorded in timing.md)
- The build: period 2**30; both counters cross the wrap; the rig's overrides are compiled in; no compiler diagnostics.
- The OF-32 probe on the real clock (a twin UARTLink, a byte every 100 s, a stall burst at 600 s):
  - base f3fff0e: FAIL. The byte at 601 s never arrives, and the 601 s burst keeps 0 and loses 0. This is the seen-failing case.
  - Y 5cf361c: PASS.
  - V 8edb5aa: PASS.
- V1's and Y3's wrap tests on V's head, on this build, with the wrap at 1/4, 1/2 and 3/4 of each file, at both GC stages:
  - test_ticks_rollover: 23/23 every time (3.76-3.82 s).
  - test_digital_twin_machine: 112/112 every time (1.15-1.18 s).
  - Verdict for both: pass. Zero memory markers.

**Relay:** `<T30> e1ad71f (B1, 2026-10-22): ...` is written under `## B` with these results.

**Decisions (agent, 2026-10-22)**
- The period is the literal 1073741824, the value of `(1<<30)`, so make's shell needs no quoting.
- M.PROC.024 (1) and (2) go to B2: they need timing.md's wall clocks and Run 11's calibration.
- Generated modules are listed one row per kind, `<device>`, so no device name appears in a file.

**Failures I fixed (root causes)**
- The offset self-check's bound was 1 µs too tight. Only the bound was wrong; the build was not rebuilt.
- The probe could not import asyncio: `.frozen` was missing from MICROPYPATH.
- The first base probe got a SyntaxError: concurrent probes shared one file. Each run now writes its own file, and the base run was re-run.

**Checks:** test_citations and test_decision_vocabulary on my head: 21 passed. The one warning says the datasheets submodule is not initialised in the worktree, so paths under it were not checked. No P2.2 reader reads audit/. shellcheck and ruff F/E9 are clean on my files.

**Silent-failure scan** (my files, classes 1-7, the "Twin and tooling" mode): one finding, class 4, fixed in d7d2f0c. Two generators could stamp an empty commit; they now write "unknown".

**Facts owed:** to the SPEC lane (U36): the F.1 sentence about the 2**30 run can now carry its date. To the lead: none new; Y's `_flash_stall.py:98` straddle and V's `machine.py:937` residual were not exercised here.

**B2's start state:** worktree S/wt-u35b at d7d2f0c, rebuilt. scripts/test.sh is untouched. The scratch build tree is deleted; `ticks30_build.sh build <dir>` rebuilds it. Re-run the three generators on the integration head.

**Runs** (all logged in RUNS.md): rebuild 0; build 0; check 0; the base probe's first try rc=1 (the shared-file race), then base 1 (expected), Y 0, V 0; 12 wrap runs 0; doc checks 0. Logs are in S/u35/laneB/.