# CRr2d: every bench provokes_log set run through the dev twin and compared with its ring (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; "Quality comes first" and "Efficiency" are binding, and it says how
you hand back). Then `S/u35r/briefs/crr2_hardware_rows.md` (its "Proof and checks", "Not yours", "Shell discipline"
and "Added for CRr2b" are binding here). Then, on your worktree:
- `tests_hardware/bench/conftest.py` (`no_unprovoked_log_entry`, `_expected_entries`, the collection-time refusal),
  `tests_hardware/markers.py`'s `provokes_log` row and `tests_hardware/error_log_helpers.py`;
- every bench test carrying `provokes_log`, and the hand-backs that built their sets: `S/u35r/handbacks_redo/CRr2b*.md`
  (CRr2b7's lesson: "a set derived by reading alone is run through the twin wherever its script runs there, rings
  dumped" was applied to some sets, not all);
- how a bench test runs on the dev twin (`--twin`, TwinBoard, the dev twin's HTTP stack), and `tests_hardware/README.md`.

Worktree and base: in your launch message. Logs go in `S/u35/laneC/crr2d/`.

## Why
Each bench test's `provokes_log` set names the E and W entries its provocation may leave. Most sets were derived by
reading src/; CRr2b7 found that reading alone missed entries the real script leaves through the twin (three E
CHIP_GET entries) and kept entries that are unreachable. A set that is too wide hides an unprovoked entry; one too
narrow fails a healthy run on silicon.

## Items, in order (each committed green on its own)
1. **The inventory.** Every bench test with a `provokes_log` set: its set, whether its device script or HTTP body runs
   on the dev twin through `--twin`, and if not, why (silicon-only, an instrument the twin lacks, a wear gate).
2. **Each runnable set through the twin**, once per GC stage, with the rings dumped (every logger's E and W entries
   after the test) and compared with the set.
   - An entry the ring holds that the set lacks: reachable from the provocation (add it, with its source lines) or a
     defect (root-cause it: a product defect is the lead's with its evidence, never a widened set).
   - An entry the set holds that no run produced: reachable but not observed (keep it, with the lines that reach it,
     the NTP mid-flight rule) or unreachable (remove it, with the lines that show why).
   - A twin infidelity is named with the twin's and rp2's source lines and handed to the lead (digital_twin/ is not
     yours).
3. **Bites** for each changed set: the fixture fails on an entry outside the new set and passes on the set, through the
   twin where it runs, else on synthetic errcount.
4. **Checks:** the "Proof and checks" list of crr2_hardware_rows.md, plus `--collect-only` of the whole tests_hardware
   tier (state collected and deselected), and review rows re-rendered if a test's text changed.

## Notes
- No real hardware. `tests_hardware` only with `--collect-only` or `--twin`. Port-binding runs in
  `unshare -n S/u24/ns_xdg.sh`, nice 19. One test run at a time in your worktree.
- Lane CRr2c may run beside you on the flash tier. You own the bench tests' markers and `tests_hardware/bench/
  conftest.py`; CRr2c owns `tests_hardware/flash/`, `tests_hardware/device_scripts/`, `tests_hardware/error_log_helpers.py`
  and `tests_hardware/markers.py`. A change you need in the other's files goes to the lead.
- test_twin_record stays red for changed hardware files; hand the lead the list of files whose twin record changes.
- Run to the end; hand back early only as redo_common says.

## Hand-back (the file, per redo_common)
- Commits; item 1's inventory (runnable or not, with reasons).
- Per set and stage: the ring against the set, each added or removed entry with its lines, each defect or infidelity.
- The bites with their red-first evidence; the checks; the twin-record list.
- Last line: "nothing of mine is running".
