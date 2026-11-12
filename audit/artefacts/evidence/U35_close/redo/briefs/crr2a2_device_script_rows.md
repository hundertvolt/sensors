# CRr2a2: the review's 84 open device-script rows (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first, then `S/u35r/briefs/crr2_hardware_rows.md` (block CRr2a's item 1 is your
task, and its "Proof and checks", "Not yours" and shell sections apply) and CRr2a's hand-back
`S/u35r/handbacks_redo/CRr2a.md` ("Item 1, left open, state"). Base, worktree and branch named at launch; logs in
`S/u35/laneC/crr2a2/`. Your base holds CRr2a's work merged: review_rows.py reads a device script's verdict from
review_verdicts.json key `tests_hardware/device_scripts/<f>.py::<stem>` -> `"ds_facts": [verdict, reason]`.

## Items
1. Re-run CRr2a's extractor (`S/u35/laneC/crr2/ds_keys.py`; read it first) on your base: ds_keys.txt and ds_open.txt.
2. Every one of the 84 open rows (165 unasserted keys in 64 scripts at CRr2a's count) gets a terminal verdict:
   - a fact a host test asserts by key: biting, the test named;
   - a fact no host test reads: a host assertion in the test that runs the script (CR3's rule: synthetic-output bite,
     vacuous output passes the old test and fails the new one, healthy output passes both; through TwinBoard where the
     twin runs the script), or a stated diagnostic, justified in place (a trailing comment on the run line, or a
     citation of a statement already there, as CR3 did: harness.py's saved-evidence lines, a script's docstring).
   CRr2a's leads, each re-checked: the likely fixes (reboot_persist_read.py's remove_errno, which
   test_reboot_persistence.py lacks the absence check for that test_config_float_round_trip.py makes; scratch_remove_errno
   in isl29125_mechanism_envelope.py and uart_dma_ring_interrupts_off.py); the likely justified (leftover_errno in 15
   scripts, each followed by an os.mkdir() of the same path that raises, so no DONE line: check each script;
   fram_raw_dump.py's saved evidence; initialized and seeded_system as CR3 classed them; heap_* facts and
   result_note-only facts as diagnostics); the f-string false flags re-checked.
3. The verdicts through review_verdicts.json, review.md re-rendered with review_rows.py, `--check` rc 0, the counts
   from it in your hand-back.
Commit per group of scripts green; past 80 tool calls hand back the rest at a seam with the remaining list.
Commit subject `U35 lane CRr2a2: <summary>`, the two trailers; do not push. Last line "nothing of mine is running".
