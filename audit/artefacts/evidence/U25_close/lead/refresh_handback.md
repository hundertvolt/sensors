U25 v0→v1 refresh done, file-only. I wrote only under S/u25/: no test, lint or build run, no worktree touched (both `git status` are clean). The record is `u25/refresh_delta.md`; the plan is `lane_plan_v1.md` (40 sites renumbered, 37 asserted edits).

**Sites.** v0's own sites (lane plan and gaps): 227 records, of which 161 unchanged, 45 moved, 11 changed, 0 gone, 9 scratch (the U23 drafts). 106 bare `:N` cites got their file by hand (`tools/v0_ctx.py`).
- Packet sites: 2357 have a line at e14d76f. U24 left 1162 unchanged, moved 1027, changed 103 and removed 65. That gives 138 distinct gone/changed entries, each sorted by cause in `tools/v1/u24_gone_changed_classes.txt`.
- Every one of those is a U24 stage of its change (renamed privates, the shared harness, rp2-shaped fakes, src_const reads, FixedRandom). Each U25 part is still owed.

**Already landed at U24.** No step landed whole. A.U25.49 is partly in: citations at `tests/test_digital_twin_isl29125.py:12-27`, plus `tests_scripts/test_const_mirrors.py` (A-29). A.U25.16 only has U24's own part (`digital_twin/machine.py:544-545, 558, 587-588`); the constructor's LSB refusal is still owed.

**Premises U24 changed:**
- `_TWIN_PENDING` is not in `_machine_contract.py`, as the brief assumed. It is `tests/test_digital_twin_machine.py:84-89`, checked by exact equality, plus a surface list at `test_fake_surface_conformance.py:27`. Both are in MN's files (A-3). C's fresh exceptions make the FIFO entry pass, so `:136` is red on api1 until MN drops that entry.
- F1 9(a) becomes A-27 (the oldest matching fault fires; C). 9(b) is handled by C's fresh exceptions. 9(c) becomes A-32 (the twin UART counts real polls; MN).
- `spawnTwin()` now lives in `tests_js/_twin_process.js`, which joins SH's set (A-30).
- The offline NTP writer now derives its file name from `src/` (R, A-28).
- `b63d9b0`: P runs every per-device job through the same interrupt-once wrapper.
- `8e7dedc`: SH keeps the put matrix's backups-off step; A-16's comment site is now `:104-106`.
- U24's deferrals (M.SCR.041, M.TEST_HELP.031, M.TSC.135, M.TWIN.108 to P; M.TOOL.032 to the lead) were already placed in v0.

**Open findings placed:** OF-149 to G (A-33); OF-155 at `_machine_contract.py:25` and `test_fakes.py:99` to MN, at `run_generic_integration.py:364` to R; OF-156 to SH, with the Part N row going to D. OF-151 (SCD30/ISL29125), OF-153, OF-154 and OF-155's two other sites sit in no U25 set, so they stay open (A-35).

**The cut** (steps/changes, files, est. changed lines):

| lane | wave | steps/changes | files | lines |
|---|---|---|---|---|
| MN | 1 | 20/37 | 22 | ~2700 |
| C | 1 | 12/16 | 13 | ~1800 |
| R | 1 | 20/30 | 22 | ~2000 |
| P | 1 | 24/30 | 37 (12 removed) | ~1300 |
| SH | 2 | 16/37 | 28 | ~3500 |
| G | 2 | 9/14 | 13 | ~3100 |
| lead | after 2 | 12/13 | 7 | small |
| D | 3 | 33/35 | 5 | ~1000 |

There is one API merge (api1: MN1, C1, R1, P1); SH and G run to their finals with no WIP stop.

**Disjointness:** `comm -12` is empty over all 28 pairs, lead included; 147 files, none listed twice.

**Rulings:** A-1, A-2, A-3, A-8, A-9, A-12, A-14, A-15 and A-16 changed (new lane names, corrected sites, the new cut). All others hold, re-checked on 8e7dedc. New, all (agent, 2026-10-14) and on the owner-review list: A-27 to A-36.

**Packets, sets and briefs:**
- Packets `pk/packet_lane{MN,C,R,P,SH,G,LEAD,D}.md`, cut from `pk/U25_steps_v1.md`, which adds a "Sites at 8e7dedc" block to every step (‡ on the 665 lines U24 touched). v0's C, R, P and LEAD packets are kept in `pk/v0/`.
- New sets `files_{MN,SH,G,D}.txt`; C, R, P and LEAD are unchanged.
- `briefs/`: `rulings.md`, 7 lane briefs (64-99 lines each), `brief_lead.md`, `launch_checklist.md`.

**Needs your ruling (my default first):**
1. A-3 against CHECKLIST 4: MN shrinks both twin pending lists itself, because the exact-equality check forces it, and reports each line.
2. A-35: retarget the out-of-set findings to the next unit that edits each file, U27 if none comes earlier.
3. A-36: keep SH whole at ~3500 lines. Splitting it into S and H would add a lane's fixed cost with no parallel gain.
4. A-28: the moved NTP writer imports the product's `config_filename()`; the UDP shim already imports `asy_udp_socket` the same way.
5. A-29: `test_isl29125_copies.py` is written only for copies that `test_const_mirrors.py` misses.
6. I added a `<W3>` placeholder (W2 plus the lead step) as D's base, beyond `<U24>` and `<W1>`.
