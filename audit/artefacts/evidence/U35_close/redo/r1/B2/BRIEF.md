# B2 brief: core (lead, 2026-11-02)

Read first, in order: `S/u35r/r1/common_r1.md` (binding), `S/u35r/r1/B2/ACTION_LIST.md` (your work list), PLAN.md
sections 2 and 4 and its B2 row (`S/u35r/plan/PLAN.md`, R1).

- Worktree `S/wt-b2`, branch `audit/r1-b2`, at the integration head named in your start message (B1 merged). Run labels
  start with `b2_`.
- Hand-back: `S/u35r/r1/B2/HANDBACK.md`.
- You run alone. Item 1 and the emitters touch what the website reads: the gate adds `npm run lint`, `npm run
  typecheck` and `npm run test:unit` (`node_modules` is linked in the worktree).
- B1 left the logger's `restored` flag for your item 5; B1's `err_nomem(what, e)` is the logger call for a caught
  `MemoryError`'s arm (fixed arity, no allocation). Level 0 prints nothing: a new console line goes through a logger.
- `tests_hardware` only with `--collect-only` or `--twin`: a reader you change there is checked by collection and, where
  it has a twin form, by `--twin`; nothing is skipped, disabled or deselected to get green.

Sources for the items (read the part you need, not whole files):
- Items 1 and 2: the rulings file (`S/u35r/recovered/owner_rulings_after_LN118.md`), 2026-11-02 21:11, 21:17 and 21:22;
  `S/u35r/plan/PLAN_before_rewrite.md`:196 (the B2 row's silicon facts: what the raw bits and `reset_cause()` read per
  reset kind; the record lost on a BOOTSEL round trip, so the next boot reads 2). Emitters
  `buildgen/codegen.py:293`, `:297`; website rows `buildgen/definitions.py:636`, `:649`;
  the bench test `tests_hardware/bench/test_reset_reasons.py`.
- Item 3: the rulings file, 21:25; `src/math_helpers.py:16-23` (`_WB_*`) and `:213` (`wet_bulb_temperature`).
- Item 4: `25caf528:src/math_helpers.py` (the pre-audit clamp); legacy `python/` for the field behaviour (read only).
- Item 5: `S/u35r/scan2/G4.md` S2-G4-21 (line 424); `PROJECT_AUDIT_PLAN.md`:542-543 (OR136, OR136.a: the write-once,
  and (3), the command-only schema's printed note).
- Items 6 and 9: `S/u35r/scan2/G4.md` S2-G4-7 (line 162), S2-G4-8 (line 189), S2-G4-22 (line 439), its closure table
  (lines 480-510) and the closure rows of your files in `S/u35r/scan2/G4_closure.tsv` and `G4b_closure.tsv`.
- Item 7: `S/u35r/plancheck/R1.md`:76 (B2.6) and the closure's keep at `S/u35r/scan2/G4.md`:526; read both, then decide
  from the code: the reset record is written before the entry write.
- Item 8: `PROJECT_AUDIT_PLAN.md`:496-497 (OR113, OR113.a: the ladder's rungs and their order).

Before you start removing, check each "remove" item for proof that it is good (PLAN.md 0, "Nothing proven good goes": an
observed or reproduced failure it fixes, a measured gain, or an owner approval). One with such proof becomes a shrink
item: say so in the hand-back. A pre-audit function found lost or changed without a recorded reason goes to the lead.
Items 1-3 are the owner's decisions: they go whatever proof exists, and you name any proof you find.
