# LD+CM3: load.md's resource × level cells; matrices.md's assembly matrix (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; "Quality comes first" and "Efficiency" are binding, and it says how
you hand back). Then, on your worktree:
- CLAUDE.md;
- `audit/actions/U35.md`: A.U35.28 (:727-765) and A.U35.08 (:225-254), part (1) only;
- `audit/b3/load.md` and `audit/b3/matrices.md` (keep its device-pick table as it is);
- `S/u35r/handbacks_redo/Q35.md`'s load and matrices rows;
- SPECIFICATION.md Part N's rate and budget rows (`rate.persisted_log`, `system.scan_budget`, the feed rows), E.2.1,
  and E.6.1;
- `audit/b3/review.md`'s header (a cell's test must bite: review.md holds each test's verdict);
- `audit/b3/queue_c.md` (where silicon-only cells go).

Worktree and base: in your launch message. Logs go in `S/u35/laneB/ldcm3/`.

## Why
- **A.U35.28 (load.md, empty on the head)** needs one cell per finite resource × level, each with its load, limit,
  degradation, recovery and caveat. The pass condition (G4/R65):
  - graceful degradation;
  - a checked full return to baseline once the load stops;
  - no crash, reboot, WDT reset, MemoryError marker or log flood;
  - no write to a limited-endurance store (FRAM writes are not wear, OR49.a (2)).
- **A.U35.08 part (1) (the assembly matrix, unwritten on the head)** lists every assembly dimension with its values:
  driver set per device, bus sharing, optional FRAM, UART wiring and its `crc` key, behaviour-switching config values
  and the shipped TOMLs.
  - A small dimension is covered exhaustively.
  - A large one is covered all-pairs, plus the risky higher-order combinations ("shared bus + shared FRAM + REST
    writes").
  - Each combination is either shipped or a `zz_test_*` fixture TOML generated at test time, never committed, and
    booted at L2.
- Many of the tests already exist: the L1 fault-storm scenario, the L2 bounded storm, the bench full-ceiling and soak
  tests, `scheduler_saturation_drop.py`, `timer_alarm_pool_exhaustion.py`, the twin UART hammer, the captive-DNS and
  webserver malformed-input tests. Map them first. Fill only real gaps.
- A defect a cell exposes is fixed in-lane, src/ included, under the owner's "Firmware really complete, don't push
  fixes to future units" (REDO.md's additions).

## Items, in order (each committed green on its own)
1. **load.md, mapped.**
   - Resources: heap; sockets and connections; asyncio tasks; the 8-deep soft-IRQ scheduler queue and its drop
     behaviour; the timer alarm pool; bus locks; error-log slots; the persisted-log FRAM write queue; UART buffers;
     CPU time against the watchdog.
   - Inputs: request rates; DNS queries; malformed, partial and oversized requests.
   - Levels: L1-L4.
   - Each cell names the test **function** that loads it and its review.md verdict. It also states whether that test
     asserts all of the pass condition: degradation, return to baseline, no marker, no flood.
   - A test that loads a resource but asserts only part of the condition is a gap in that test. Strengthen it with its
     goal kept, red first on a plant.
   - L3/L4-only cells (silicon timing, CYW43 under load) go to queue_c.md rows, not tests.
2. **load.md, gaps.**
   - Each gap gets a test at the lowest level where the load is real, in the same pass/fail shape, seen failing first
     on a plant, at both stages, zero memory markers.
   - A gap at L3/L4 you cannot run here is written and checked with `--collect-only`, plus `--twin` where its script
     runs there. Its silicon run goes to queue_c.md.
   - No test writes the flash filesystem or SCD30 NVM; a cell that would need one is the owner's question (CHECKLIST
     24): stop and hand back.
   - Each new load test gets its entry (gap, load, limit, degradation, recovery), which is the OR49.a (3) ledger.
3. **The assembly matrix (CM3).**
   - Write an `audit/sweeps/` script that reads `devices/*.toml`, `buildgen/validate.py`'s optional keys and every
     behaviour-switching schema field. The fields include SGP40 `BackupPeriod` 0, `WaitTimeNTP`, the notification
     window and `DebugLevel`; find the rest by reading the schemas, and list them with the reason each one switches
     behaviour.
   - The script lists each dimension's values and computes the exhaustive or all-pairs set, plus the named
     higher-order combinations.
   - Each combination is marked as covered by a shipped device or not.
   - Commit the script and the matrix with its `--check`.
4. **CM3's gaps.**
   - Every combination no shipped device carries is built as a `zz_test_*` fixture TOML at test time (the existing
     exclusion, `tests_scripts/_devices.py`) and booted at L2. Use the cheapest boot that proves the combination: one
     shared boot per fixture, on the driven clock, as the CMr lane's device jobs do.
   - Its assertion is the system's normal behaviour on that combination (a full boot, every wired task cycling,
     REST serving, zero markers), plus the switched behaviour where a config value is the dimension.
   - A combination that fails is a defect: red first, then a fix in-lane if it is small and local; otherwise stop and
     hand back with the facts.
5. Checks:
   - every changed file at both stages (PER_DEVICE files on all six devices), zero memory markers;
   - `python3 -I audit/sweeps/review_rows.py` re-rendered if a test's text changed, then `--check`;
   - the readers of audit text;
   - lint_direct, the six mypy passes, and the three audit checks;
   - on the final head, the whole tests_scripts tier.

## Notes
- Not yours: the interaction matrix and the recombination row (CM4, the next block), intent.md and levels.md (IN+LV).
- Files other lanes are changing:
  - the UART lane (UM4): the UART twin files, `digital_twin/run_generic_integration.py` and
    `scripts/_digital_twin_scenarios.py` (add any new scenario at the end of its registry, so the merge stays
    mechanical);
  - CMr1m: `digital_twin/machine.py` and the drift check's file;
  - N11e: `tests/_uart_comm_harness.py` and the twin bus-hazard and loop-end files;
  - the CRr2 lane: the bench and flash tiers' log fixture and markers.
  A gap test whose natural home is one of these files is named in your hand-back.
- Forced interleavings use a gate or barrier fake, never a sleep count. Real waits get an `@tunable` tag and a
  measured row.
- Run to the end; hand back early only as redo_common says.

## Hand-back (the file, per redo_common)
- Commits.
- load.md's cells by state, before and after; each strengthened or new test with its red-first evidence and ledger
  entry.
- queue_c.md rows added.
- The assembly matrix's dimensions and counts (exhaustive, pairs, higher-order, shipped, fixture); each fixture's
  boot result at both stages.
- Every defect: site, test and fix.
- Every question for the owner, in prose.
- The checks.
- Last line: "nothing of mine is running".
