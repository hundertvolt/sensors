# A-C3 apply, applier 2: M_SPEC, M_SCR and the register `audit/pass2/` (2026-10-01)

Brief: `audit/sweeps/ac3_apply_prompt.md`. Inputs read in full: `AC3_R.md` (findings and the settled list), `AC3_O.md`,
`AC3_S.md`, `audit/sweeps/ac_prompt.md`, `audit/actions/AC_NOTES.md` 1-50, `audit/order/WORK_ORDER.md` sections 1-3
(3.4 table and 3.6 notes). The register-fix sections of `U35.md`, `U36a.md`, `U36b.md`, `U37.md` and `C.md` were read in full.
Every amendment was applied against the current text of its target: A-C2's Unit/Depends edits and the `## A-C2 order
notes` tables were left as they are, and R-08 (h)'s Unit edits (M.SCR.054/.059/.060/.061) were already in place and
were not redone. The register blocks are tagged on their Pass 2 line: "A-C3: AC3_R R-nn." for a finding, and "A-L: <unit>
register fix <k> (applied at A-C3, AC3_R R-12)." for a fix that had not been applied before. Line citations the fixes
introduce were spot-checked at HEAD (`scripts/_digital_twin_ci_suite.py:1134, 1144, 1155, 1171`,
`tests/test_asy_bmp3xx_driver.py:1223-1248`, `scripts/_strip_type_checking.py:10, 21, 67`); the lead's withdrawal note
at the end of `U13.md` was read for R-03. Afterwards `audit/sweeps/pass2_index.py` regenerated `audit/pass2/INDEX.md` and
`audit/sweeps/pass2_check.py` reports 0 missing in every category, with 547 requirements and no duplicate IDs (exit 0).
No commit. Nothing outside M_SPEC.md, M_SCR.md, `audit/pass2/` and this file was edited.

## Rows: M files

| finding | M-ID / block | result | reason (adapted / declined / new) |
|---|---|---|---|
| AC3_R R-03 | M.SPEC.049 (1), Resolved | adapted | Text as given, except the quoted SPEC sentence's tag is "(agent, 2026-09-29)", not "(lead, 2026-09-30)". The lead's note at the end of `U13.md` is dated 2026-09-29, and G9/R11 allows only "(owner, …)" or "(agent, …)" as a permanent actor tag. The executor note (re-read the datasheet pages) is kept. |
| AC3_R R-04 | M.SPEC.073, M.SPEC.140 Blast | adapted | The finding says M.SPEC.046/.142, but the "→ A.U36.543 (9)/(9)-(10) (DOCS)" pointers are in M.SPEC.073 and M.SPEC.140; .046 and .142 do not name the skill. Those two now name M.DOCS.109 and M.PROC.048. This also covers the coordinator's hand-off (2) from applier 1. |
| AC3_S S-13 | M.SPEC.073, M.SPEC.140 | applied | Same edit as R-04 (one change, M.DOCS.109, which applier 1 owns). |
| AC3_R R-05 | M.SCR.066 Change, Resolved, Blast | adapted | The expansion text and the executor note are appended as given. The opening `_MANIFEST_TEMPLATE = 'include(…)…'` clause is reworded to "the expanded board manifest followed by `freeze(…)`" so the Change does not state both forms. Blast names M.TSC.094, the carrier of `test_frozen_inputs_reproducible.py`; the assertion itself is a hand-off (H-2). |
| AC3_R R-09 | M.SPEC.021 item 8, From | applied | The sentence goes inside item 8's quoted text; the executor check follows it outside the quotes. From gains G3/R31. |
| AC3_O O-14 | M.SCR.039 | applied | |
| AC3_O O-19 | M.SPEC.070 | applied | |
| AC3_O O-20 | M.SPEC.116 | applied | A.U32.06 added to From (it was not there), so the source stays recorded. |
| AC3_O O-21 | M.SPEC.129 | applied | A.C.09 is already in From. |
| AC3_O O-22 (SPEC half) | M.SPEC.136 | applied | Applier 1 applied the M.DOCS.076 half. |
| AC3_O O-23 (SPEC rows) | M.SPEC.054, .064, .075, .082 | applied | In .064 and .082 the tag sits in kept HEAD text, so each now carries a "tag → (owner, date)" instruction. The other tags are in other appliers' files. |
| AC3_O B (placeholders) | M.SPEC.111, M.SPEC.144 | applied | `<A.U10.08's check>` → `tests_scripts/test_watchdog_feed_sites.py` (M.TSC.155); `<A.U6.15's check>` → `test_no_variant_literals.py` (M.TSC.110). |
| AC3_O O-27 | M.SCR.015 Change, Unit | adapted | Rows are now by category, with the U31 measured-collection-pause row for `loop_stretch_timing.py`. "(OR39.a (2), OR91.a (9); M.HW_DEV.122)" sits outside the quoted row reason, which is permanent text (G9/R12). The Unit slot now names U31 as the completing unit, with stages U27 and U30. Applier 4 applied M.HW_DEV.122's Blast half. |
| AC3_S S-05 | M.SCR.075 | new | `scripts/_strip_type_checking.py`'s three function docstrings (HEAD :10, :21, :67) become comment blocks, in U10, with S-05's body. It sits in its own section after M.SCR.074, and the SCR ledger row for A.U10.34 gains it. |
| AC3_S §5 | M.SPEC.153 Blast | applied | "→ A.U36.020 (TEST_UNIT)" → "(TWIN, M.TWIN.122/.126)". |

Each row above also has a ledger row in its M file (M_SPEC: rows labelled "A-C3"; M_SCR: rows labelled "AC3_…").

## Rows: register

| finding | block(s) | result | reason |
|---|---|---|---|
| AC3_R R-01 | — | no edit | The amendment is M_PROC's (M.PROC.022). The affected States already name U35, and the finding gives no register text. |
| AC3_R R-02 | — | no edit | M_PROC's (M.PROC.021). G9/R05's State already names U32. |
| AC3_R R-03 | G3/R16 | no edit | Its State already says "no hardware item … SPEC C.3.1 … AC_NOTES 11". G5/R29 is covered by C fix 1 below. |
| AC3_R R-04 / R-10 | G9/R18 State | applied | The skill names M.DOCS.109 and the baseline runs name M.PROC.048 (U36). The Home's directory is now created, which closes R-10's G9/R18 item. |
| AC3_R R-05 | LEAD/R13 State | applied | "Residual … parked for A-C" → expanded to a sorted list (M.SCR.066, U27). The cited v1.29.0 facts are kept in the sentence. |
| AC3_R R-06 | LEAD/R34 State | applied | M.PROC.003 (5a) (U0) and the WORK_ORDER.md test schedule. This is the coordinator's hand-off (1). |
| AC3_R R-07 | G4/R54, G7/R23, G8/R31 | applied | |
| AC3_R R-08 (a) | G4/R04 | applied | |
| AC3_R R-08 (b) | G8/R49 | adapted | Written to WORK_ORDER.md: the A.3 pointer lands in U28 as M.SPEC.007's A-C2 stage, and the rest of A.3 lands in U36. The finding had said U36. |
| AC3_R R-08 (c) | G2/R11 | adapted | Only the D1.41 clause moves to "code in U25 (host-side, OR125; M.TEST_HELP.033, M.SCR.018 (a))". The D1.49 and D1.57 clauses after it shared the old "code in U24 —" header and keep "code in U24". |
| AC3_R R-08 (d) | LEAD/R30, G9/R34 | applied | |
| AC3_R R-08 (e) | LEAD/R24 | adapted | Written to WORK_ORDER.md: the K.28 product fill lands in U11 (M.SRC_CORE.063) and its test in M.TEST_UNIT.290's U24 stage with A.U24.39; the U35 checklist is M.PROC.022. |
| AC3_R R-08 (f) | LEAD/R05 | applied | |
| AC3_R R-08 (g) | G4/R22 | applied | |
| AC3_R R-08 (h) (register part) | LEAD/R31 | applied | The units are listed in order: U25 (L2 twin pair), U26, U27 (CRC16 rerun, M.SCR.061). LEAD/R32's "U25 (L2)" stays. |
| AC3_R R-09 | G6/R51 State | applied | |
| AC3_R R-10 | G3/R22, G4/R20, G4/R55, G4/R56, G4/R44 (Home) | applied | G9/R18 is closed by R-04. |
| AC3_R R-11 | G4/R31 State | applied | |
| AC3_R R-12, U35 fix 1 | G4/R50 | applied | Both the `:1155` line fix and the short-window text. |
| AC3_R R-12, U35 fix 2 | — | no edit | It targets `SUPP_recovery.md`, an action file (as R-12 says). |
| AC3_R R-12, U35 fixes 3, 4, 5, 7, 8, 9, 10 | G3/R13, G7/R17, G2/R15, G5/R25, G5/R54, G2/R17, G6/R49 | applied | |
| AC3_R R-12, U35 fix 6 | G6/R54 | adapted | The first clause becomes "test in U35 — the cancel-at-each-await sweep (A.U35.48)" and "code+test in U35/U18 (RF204):" becomes "code+test in U18 (A.U18.31) (RF204):". This keeps the colon that introduces RF204's description. |
| AC3_R R-12, U36a fixes 1-7, 9 | G1/R11, G1/R12, G3/R29, G6/R10, G6/R53, G7/R12, G7/R15, G2/R10 | applied | G6/R53 also carries the fix's `git describe` evidence. |
| AC3_R R-12, U36a fix 8 | G4/R06 | adapted | The `.gitignore:35-38` citation is in State, not Sources, so it was fixed there. |
| AC3_R R-12, U36b fixes 1, 6-9 | G7/R39 (Req), G8/R19, G8/R48, G9/R19 (Req), G9/R12 | applied | |
| AC3_R R-12, U36b fixes 2-5 | G7/R40, G7/R39, G7/R31, G7/R37 | applied | Each "→ carried by A.U0.2x" is written as a U0 clause naming its carrier: M.GEN.062, M.WEB.016's U0 stage, M.SPEC.116's U0 stage, M.SPEC.115's U0 stage. In G7/R37 the "stable long-term" reading stays in U36. |
| AC3_R R-12, U36b fix 10 | G9/R11, G9/R13 | applied | Appended to both blocks. |
| AC3_R R-12, U37 fixes 1-3 | LEAD/R15, G9/R24, G9/R25 | applied | |
| AC3_R R-12, C fix 1 | G5/R29 | adapted | As R-12 directs: the delete target was already gone (U16 fix 10), so only the append was applied, pointed at M.SPEC.049 (1). |
| AC3_R R-12, C fixes 2-5 | G6/R28, G1/R14 + G5/R03 + G7/R07, G4/R44, G1/R04 | applied | C fix 4 includes its `SPECIFICATION.md:5238-5243` premise sentence. |
| AC3_R R-12, C fix 6 | — | no edit | It targets `audit/sweeps/al_input.py`, a sweep script (as R-12 says). |
| AC3_R R-13 | G3/R19, G3/R55, G4/R52, G6/R37, G10/R22, G6/R38 | applied | |
| AC3_R R-13 | G3/R14 | adapted | The unit is U3, not U2. WORK_ORDER.md's A-C2 note on M.SPEC.059 defers A.U2.22's part to U3 (it needs A.U2.02). |
| AC3_R R-14 | — | no edit | Recorded so the drop is not raised again; no amendment. |

## Hand-offs and notes for the lead

- **H-1 (order).** M.SCR.015 now completes in U31, with stages U27 and U30, because AC3_O O-27 adds the
  measured-collection-pause row with `loop_stretch_timing.py`. That U31 step is not in `audit/order/work_order.json`;
  re-run `audit/sweeps/ac_order.py`, or add the step. M.SCR.075 (U10) is already placed there as an S-05 change.
- **H-2 (TSC).** AC3_R R-05: M.TSC.094 (`tests_scripts/test_frozen_inputs_reproducible.py`) should gain "and the
  rendered manifest holds no bare directory `freeze(path)`: every freeze lists its files". M.SCR.066's Blast now names it.
- **H-3 (observed, not applied).** M.SPEC.136's end-state J text keeps "`UART_C_PORT_CHANGELOG.md` A10/A11 hold the two
  candidates that would change it". That is a changelog-entry citation in permanent SPEC text, and the changelog is a
  temporary file. G9/R12's Req forbids it, but AC3_O did not raise it. The lead decides whether to state the two candidates
  in place.
- **H-4 (observed, not applied).** G3/R16's State dates the lead's withdrawal "2026-09-30". The note at the end of
  `U13.md`, and C fix 1, date it 2026-09-29. The register text was left as it is; M.SPEC.049 uses 2026-09-29.
- Other appliers had already applied the other-file halves this file's findings point at: M.DOCS.076 (O-22),
  M.HW_DEV.122 Blast (O-27), M.DOCS.109 and M.PROC.048 (R-04/S-13), M.PROC.003 (5a) (R-06).

## Counts

- M files: 15 finding rows. M_SPEC: 15 changes amended (.021, .049, .054, .064, .070, .073, .075, .082, .111, .116,
  .129, .136, .140, .144, .153). M_SCR: 3 amended (.015, .039, .066), 1 new (M.SCR.075), and the A.U10.34 ledger row
  updated. By result: 10 applied, 4 adapted, 1 new, 0 declined.
- Register: 66 blocks edited and tagged.
  - R-12: all 36 unapplied register fixes (U35 1, 3-10; U36a 1-9; U36b 1-10; U37 1-3; C 1-5).
  - Findings: R-04/R-10 (G9/R18), R-05, R-06, R-07 (3 blocks), R-08 (a)-(h) (9 blocks), R-09, R-10 (5 Homes), R-11,
    R-13 (7 blocks).
  - Adapted: 8 (R-08 (b), (c), (e); U35 fix 6; U36a fix 8; C fix 1; R-13 G3/R14; R-05's LEAD/R13 wording kept the cited
    facts).
  - No register edit needed: R-01, R-02, R-03 (G3/R16), R-14, U35 fix 2, C fix 6.
  - Declined: 0.
- Hand-offs: 2 (H-1 order, H-2 TSC). Observations: 2 (H-3, H-4).
- `pass2_index.py` regenerated INDEX.md; `pass2_check.py` is clean (exit 0).
