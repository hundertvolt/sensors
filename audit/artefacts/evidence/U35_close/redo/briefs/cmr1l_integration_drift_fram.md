# CMr1l: the integration file's supervised-death drift check, and its Wi-Fi scenarios' FRAM assertions (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; "Quality comes first" and "Efficiency" are binding, and it says how
you hand back), then CMr1j's hand-back `S/u35r/handbacks_redo/CMr1j.md`: its items 1-2 (the driven clock on this file)
and "Findings for the lead" 1 and 3. HP2's hand-back `S/u35r/handbacks_redo/HP2.md` for child_last (a finished task
kept alive by a stale pairing-heap pointer, bounded) and its heap-reading method. Worktree `S/wt-u35cm3`, branch
`audit/u35-cm3` at 562cf582 (CMr1j's head; clean, rebuilt). Logs in `S/u35/laneC/cmr1l/`.

## The lead's review of CMr1j (binding)
- `test_a_supervised_task_death_reaches_the_console_through_the_pc_report_at_level_0`
  (tests/test_digital_twin_sensortask_integration.py) failed once on 5a8c6e35's file, arzi at 32768, load 5.4
  (`S/u35/laneC/cmr1j/p2_base_arzi_t.log`): Theil-Sen slope exactly 32 B against `slope < _DRIFT_SLOPE_BYTES` (32),
  readings [946816, 945600, 945280, 945280, 945280, 945280, 945696, 945280, 945472, 945472]. The constant's own
  comment names transient modes reading 38 B and 32 B. A check a healthy run can fail is a test defect, and no failure
  is called a flake without a root cause. It passed 8 head runs: that does not clear it.
- The widened Wi-Fi scenarios write through to each device's FRAM but assert on the error log's RAM copy only: a
  FRAM-only wiring fault would pass on every device.
- CMr1j's next-boot /status read at BOOT_DONE is accepted: begin_boot() latches the code before any construction.

## Items, in order (each committed green on its own)
1. Root-cause the transients with evidence: which objects hold the +416 B at death 6 and the +192 B at deaths 8-9 (a
   heap reading per death and what is alive; candidates: HP2's child_last, the supervisor's death record, where a
   32768-threshold collection lands). Then give the check a form a healthy run cannot fail and a real per-death leak
   still fails: the planted 16 B per death must still fail, and so must a plant at the smallest leak the check claims
   to see. Efficiency first. The bound or the window changes only from a measured basis (healthy runs at both stages,
   quiet and loaded, on every wiring the test runs on), put to the lead with the numbers before the change. No
   gc.collect() or gc setting is added beyond what the test already uses to read the collected heap (CLAUDE.md).
2. The FRAM assertions: each widened Wi-Fi scenario that persists an entry also asserts it in the device's FRAM copy
   (read the twin chip the way the suite already does; `digital_twin/_fram_chip.py`), on every device it runs on.
   Bite: a planted FRAM-only wiring fault (a write that does not raise and does not land) fails each scenario; the
   control passes.
- Checks: every changed file at both stages on all six devices (PER_DEVICE files), zero memory markers; on the final
  head the whole tests_scripts tier; lint_direct, the six mypy passes, the three audit checks; review rows for changed
  or new tests (`review_rows.py --check`).
- Lane N11d may tag real-time waits in this file meanwhile: change no wait's value; a conflict is the lead's to merge.
- Run to the end; hand back early only as redo_common says.

## Hand-back (the file, per redo_common)
Commits; the transients' cause with its evidence; the check's new form with its measured basis and bites; per scenario
its FRAM assertion and bite; the checks; last line "nothing of mine is running".
