# CO5: the five open L2 cells, the FRAM fault's log pair verified, the review rows (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; "Quality comes first" and "Efficiency" are binding, and it says how
you hand back), then `S/u35r/briefs/co4_recovery_rungs_rest.md` (its rules and the lead's decisions stand), then CO4's
hand-back `S/u35r/handbacks_redo/CO4.md`. `co1_recovery_rungs.md` item 3 for a defect. Worktree `S/wt-u35conf2`,
branch `audit/u35-conf2` at the integration head 158058ed (CO4 merged; clean, rebuilt). Logs in `S/u35/laneB/co5/`.

## The lead's review of CO4 (binding)
- Its seven commits are kept, merged into int with a green merge check.
- Its owner question is held: it rests on "a fault that persists ends at the chip-loss probe", which is not shown.
  The probe runs on a blank read (asy_fram_manager.py:151-152 at 158058ed); an RX-overrun read raises with the chip
  present. The facts come first, then the lead decides whether it is a design point for the owner or a rule break.
- Five L2 cells are open for want of a twin knob or test. Open cells are closed in this unit, not left.

## Items, in order (each committed green on its own)
0. The merge check's reader `test_level_containment.py::test_every_twin_scenario_is_covered_or_an_exception_row_with_a_reason`
   is red on 158058ed: CO4's new twin scenarios `held_i2c_line` and `setup_resets` have neither an L3/L4 counterpart
   nor an E.6.6 row with a reason. Decide per scenario on the facts (can the dev bench hold a line or reset a setup
   without wear or risk? read tests_hardware/README.md): the counterpart if it can, else the E.6.6 row with its
   reason. CO4 did not run this reader: run the whole tests_scripts tier, never a subset. The whole tier on
   158058ed (S/u35/lead/mc_tier158/tier.log) has three more reds: test_suppression_form's code order at
   tests/test_digital_twin_sgp40.py:314 (CO4's; fix it here); member_order (lane D2S fixes it; leave it); and
   test_twin_record's two (the known pre-re-record state; leave them).
1. The FRAM fault's log pair, measured: under a sustained read fault with the chip present (CO4's RX-overrun plant),
   does anything end the repeats? How many ring entries per boot, and per hour of the product's real read pattern?
   Which of the ring's other entries are evicted, and when? Then the alternative designs, each with what /status
   would report: keep the pair; fold a repeated pair; log the fall-through once per fault run. No src change.
2. U16 "latch does not clear after WRDI" and "write verification mismatch": read the MB85RS64V datasheet in
   `datasheets/` first, add the twin chip knobs (`digital_twin/_fram_chip.py`, modelled on its existing ones,
   default off), then the L2 tests. Each bitten on a planted fault.
3. U18 "hotspot timer cannot be armed": a twin test that empties the alarm pool while the hotspot shutoff timer arms.
4. U18 "a UDP socket cannot be set up, bound or connected", R1 and R2: twin tests that fail a product socket's setup,
   bind and connect and watch the next call rebuild it.
5. review.md: rows for CO4's 13 new tests and yours; the render, `review_rows.py --check` green.
- Every changed file at both stages (PER_DEVICE files on all six devices), zero memory markers; lint, the six mypy
  passes, the readers, the three audit checks.

## Hand-back (the file, per redo_common)
Commits; item 1's numbers and the designs; per cell its test and bite; any defect with its red-first test; the
checks; any owner question in prose with a recommendation; last line "nothing of mine is running".
