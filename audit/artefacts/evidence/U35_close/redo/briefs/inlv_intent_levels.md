# IN+LV: intent.md's rows bite and its open layers written; levels.md's cells confirmed (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; "Quality comes first" and "Efficiency" are binding, and it says how
you hand back). Then, on your worktree:
- CLAUDE.md;
- `audit/actions/U35.md` A.U35.07 (:195-224) and A.U35.22 (:590-613);
- `S/u35r/handbacks_redo/Q35.md` (its intent.md and levels.md rows, NOT IN THE PLAN item 2, and the six codes);
- `audit/b3/intent.md`, `audit/b3/levels.md` and their walk `audit/b3/levels_walk.py`, in full;
- `audit/b3/review.md`'s header and `audit/sweeps/review_rows.py` (each test's verdict lives there);
- SPECIFICATION.md E.6/E.6.1 (the levels L0-L4), E.2.1 (device scope), L.6.4 (the `@limits` tags).
- For the six codes: P36a's finding in REDO.md's additions section. Its line numbers are from an older head, so
  re-locate them.

Worktree and base: in your launch message. Logs go in `S/u35/laneB/inlv/`.

## Why
A.U35.07 needs two things.
- **The intent map:** every intent item at four layers, mapped to a biting test. The layers are function, module,
  functional integration and system integration. An item is normal behaviour, an error path or a resilience path.
- **The file × level matrix:** every file mapped to the levels that test it, each gap filled at the lowest level that
  can prove it.

Both records were walked at e1ad71f, older than the head. Their cells are reference matches, which the walk's own
header says still need a bite check:
- intent.md has 6 "no test" codes, and its schema-bound, None/NaN and integration-layer rows are unwritten;
- levels.md's 137 cells are all "open: confirm the cells bite", and its two entry-point rows are open.

A defect a new row exposes is fixed in-lane, src/ included, under the owner's "Firmware really complete, don't push
fixes to future units" (REDO.md's additions: records lanes own their defects).

## Items, in order (each committed green on its own)
1. Re-run `levels_walk.py` on your base, committed alone (it writes both files).
2. **The bite check, made mechanical.** Extend the walk, or add a reader beside it in `audit/b3/`:
   - each cell names its test **functions**, not files;
   - each is joined with review.md's verdict;
   - a cell with no function verdicted biting, fixed or justified is open.
   - A file-level mention that no test function drives (a comment, an import kept for a fixture) does not count.
   - Its no-change proof: the old cells are a superset of the new ones on your base.
   - Commit it alone, with the re-rendered records.
3. **intent.md's six codes** (asy_base_classes.py CFG_SET_RAISED .. RECOVERY_WRITE_RAISED, asy_uart_comm.py
   UART_WRONG_KIND).
   - Find each code's naming test on the head and show it bites: a plant at the code's log site (the code swapped or
     the log removed, in a private copy) fails it at both stages.
   - Close each row. Close OF-245's row in `audit/sweeps/open_findings.md` with that evidence. That one row is the
     only edit to that file (REC2 owns the rest), named in your hand-back.
   - If a code has no path that logs it, that is a defect: either a test that reaches it, red first, or the code's
     removal. The removal changes the catalog, so stop and hand back with the facts.
4. **Schema-bound rows, the function layer.**
   - Derive them mechanically from the four sensor drivers' config schemas and constructor parameters (the `@limits`
     tags and the schema definitions). Each bound gets rows for: below it, at it, at the other bound and above it.
     Each field also gets `None`, and each float field `NaN`, `+inf` and `-inf`.
   - Map each row to a biting test function. A gap gets its test at the lowest level that proves it (L1, or L0 where
     buildgen's validation is the claim), seen failing first on a plant (the check removed or moved by one), at both
     stages, zero memory markers.
   - Combinations of fields are CM3's (the config-value dimensions). They are not yours; say so in the header.
5. **The two integration layers.**
   - Functional integration: each module's real-chain row made concrete. Name the real consumer, and the test function
     that drives the module through it in a generated device's graph.
   - System integration: one row per top-level feature of a generated device, from SPECIFICATION.md A.2/A.4 (the
     "functional behaviors confirmed intentional" list included), plus each REST route in the API reference. Each row
     names the L2 test that drives it on every device it applies to, or E.2.1's single-device scope with the row that
     covers the other devices.
   - Recovery paths already have rows in conformance.md (A.U35.52's rungs). Cite those rows; do not duplicate them.
   - A gap gets a test at the lowest level that proves it, red first.
6. **The reverse direction (OR25.a (2)): a test tied to no item is tied or removed.**
   - First compute it mechanically: the test functions that no row reaches, counted per tier.
   - If the count is at most about 150, tie each one to its row, or class it with its reason.
   - If it is larger, stop and hand the count, a sample of 20 and your proposed method to the lead before tying.
   - Never remove a test in-lane. A test you judge redundant is listed with the test that duplicates its assertion on
     the same path, for the lead.
7. **levels.md.**
   - State each level's scope in the header (E.6.1).
   - Close the 137 cells through item 2's check.
   - Write the two entry-point rows (`build/generated_src/sensortask_<device>_main.py` and `_main_noautostart.py`):
     their L0 and L3 cells, with the tests named.
   - Name the covering row for each single-device narrowing (A.U25.48's real-website test, `digital_twin/launch.py`'s
     raw-bus demo).
   - A "-" cell that a lower level can prove gets a test, red first. Otherwise give the reason it cannot.
8. **A.U35.22's multi-chunk SET ladder**, as levels.md rows:
   - L1: `tests/test_asy_uart_comm.py`'s trains;
   - L2: `tests/test_digital_twin_uart_link.py`'s two tests (the payload larger than one chunk, and the link working
     while the graph runs);
   - L3/L4: A.U26.87's scripts and bench test.
   - Confirm that A.U26.87's commit touches no src/ file (`git diff --stat` over src/).
   - If the second L2 test carries only single-chunk transfers, it gains one multi-chunk SET echo. That file belongs
     to the UART lane (UM4) unless UM4's merge is in your base (`git log --oneline --grep 'merge lane.*UM'`). If it is
     not, write the row, hold the extension, and name it in your hand-back.
9. Checks:
   - every changed test or src file at both stages (PER_DEVICE files on all six devices), zero memory markers;
   - `python3 -I audit/sweeps/review_rows.py` re-rendered if a test's text changed, then `--check`;
   - the readers of audit text (test_citations, test_decision_vocabulary, test_comment_block_cap);
   - lint_direct, the six mypy passes, and the three audit checks;
   - on the final head, the whole tests_scripts tier.

## Notes
- Files other lanes are changing are not yours:
  - the UART twin files (UM4);
  - `digital_twin/machine.py` and the drift check's file (CMr1m);
  - `tests/_uart_comm_harness.py` and the twin bus-hazard and loop-end files (N11e);
  - the bench and flash tiers' log fixture and markers (the CRr2 lane).
  A gap test whose natural home is one of these goes into another file, or is named in your hand-back.
- Matrices (CM3/CM4) and load.md (LD) are the next lane's, not yours.
- Run to the end; hand back early only as redo_common says.

## Hand-back (the file, per redo_common)
- Commits.
- Per record: cells or rows by state, before and after.
- The reader's no-change proof.
- The six codes' plants and OF-245's close.
- Every test added, with its red-first evidence.
- Every defect: site, test and fix.
- The reverse map's count, and its ties or the proposal.
- Held items with their owner.
- The checks.
- Last line: "nothing of mine is running".
