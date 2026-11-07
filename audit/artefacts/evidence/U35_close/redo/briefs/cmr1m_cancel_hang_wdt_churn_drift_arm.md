# CMr1m: the hung cancel root-caused, the twin watchdog's per-feed churn, the drift check's concurrent arm (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; "Quality comes first" and "Efficiency" are binding, and it says how
you hand back), then CMr1l's hand-back `S/u35r/handbacks_redo/CMr1l.md` (all of it) and its evidence in
`S/u35/laneC/cmr1l/` (`dbg/`, `dbg1_arzi_m1.log`, `dbg2_arzi_m1.log`, `nolink_arzi_m1.log`), and HP1's/HP2's
hand-backs on `child_last` (`S/u35r/handbacks_redo/HP1.md` item 2, `HP2.md`). Worktree and base: in your launch
message. Logs in `S/u35/laneC/cmr1m/`.

## The lead's review of CMr1l (binding)
- Its two commits are kept and merged into int. The transients' causes are accepted: the twin watchdog's cancelled
  per-feed countdown tasks, pinned by a stale `child_last`, and one stale C-stack word below `gc.collect()`.
  - On the driven clock, every death reads the same heap.
  - The 32 B and 64 B plants fail 12/12; healthy runs read slope 0.0 on 36/36.
  - Bound, window and statistic are unchanged.
- Two of its findings cannot stay as they are:
  - Finding 5 is a hang whose cause is not known: a cleanup `cancel()` of a sensor `_read_loop` cancelled at
    virtual t=0 never returned, after `_settle()` raised under the supervisor's loop. Until its cause is known, it
    may be a product defect. The owner's rules are "root-cause faults", "no uncaught exceptions" and "firmware
    really complete".
  - Finding 2 narrows what the drift check sees. The real-clock form ran deaths while other tasks cycled, even
    though it could not tell a leak there from noise. The new form parks every other task. Checks are never
    weakened, so that interplay needs its own arm that separates.

## Items, in order (each committed green on its own)
1. Finding 5, root cause.
   - Rebuild the hung variant (supervisor started before the link wait) in a scratch copy.
   - Name what `_settle()` raised, and the exact await the cancelled `_read_loop` never returns from, by an
     instrumented copy. MICROPYPATH-first copies outside the worktree, as CMr1j did; never edit src/ to probe.
   - Then decide:
     - (a) A product defect: a task cancelled at t=0 in a real boot order hangs its canceller, or an exception
       escapes unhandled. Write the test that fails on it first, then the fix in src/, small and local, its bite,
       and every importer of the changed module at both stages. If the fix is not small and local, stop and hand
       the facts back to the lead for an owner question in prose.
     - (b) A harness artefact: the driven clock holds a wake the cancel needs, or the test drives no virtual time
       while it awaits. Fix it in the harness (tests/_fake_time.py is shared: every importer at both stages), with
       a test that fails on the old harness. Or, if the harness is right, state why, with the evidence.
   - Either way, the hand-back states which, with the trace.
2. Finding 1: the twin watchdog's per-feed countdown task (digital_twin/machine.py `WDT._arm`) becomes one long-lived
   countdown that re-reads its deadline, so a feed allocates no task. rp2's feed allocates nothing (state the source).
   - The would-trigger semantics, the late-feed backstop (digital_twin/README.md) and every WDT twin test's verdict
     stay exactly as they are.
   - Add a test: N feeds build no task and keep the heap flat.
   - Bite: the old per-feed arm fails it.
   - digital_twin/machine.py is shared by every twin test, so run the whole twin tier (every tests/
     test_digital_twin_*.py, all six devices, both stages) and the twin CI for dev and wozi.
   - Each file's time before and after goes in a formal pair, with the load.
   - The README's WDT text goes to your hand-back for the lead's D3r.
3. Finding 2: the drift check's concurrent arm, beside the parked one, in the same file.
   - Deaths at a fixed virtual interval with every other task cycling on the driven clock, the interval chosen so
     each death meets the other tasks' cycles.
   - Healthy runs on all six devices at both stages, and the 32 B and 64 B plants.
   - If the arm separates (healthy below the bound, every plant above it) with the same bound, window and
     statistic, commit it.
   - If it needs a different value, or cannot separate, stop and hand the measured basis to the lead. No bound,
     window or statistic changes without the lead, and no gc.collect() is added.
   - Item 2 lands first, because the per-feed churn is (B)'s source.
4. audit/b3/review.md: re-render with `python3 -I audit/sweeps/review_rows.py` on your head if any test's text changed,
   then `--check`.
5. Checks: every changed file at both stages (PER_DEVICE files on all six devices), zero memory markers; on the final
   head the whole tests_scripts tier; lint_direct, the six mypy passes, the three audit checks.
- The lead's merge check on your base (the importers of tests/_fake_time.py) may still be running when you start. A
  red in a file you did not touch goes to the lead by message; you do not fix it.
- Run to the end; hand back early only as redo_common says.

## Hand-back (the file, per redo_common)
Commits; item 1's trace and verdict (product or harness) with its red-first test and bite; item 2's change, test,
bite and the twin tier's formal pairs; item 3's table (healthy and planted, per device and stage) or the basis
handed to the lead; the checks; last line "nothing of mine is running".
