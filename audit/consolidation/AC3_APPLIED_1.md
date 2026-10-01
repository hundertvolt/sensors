# A-C3 apply, applier 1: M_WEB, M_DOCS, M_PROC, M_GEN, M_TOOL (2026-10-01)

Brief: `audit/sweeps/ac3_apply_prompt.md`. Inputs read in full: `AC3_O.md`, `AC3_R.md` (findings and the appendix rows
naming these clusters), `AC3_S.md`, `audit/actions/AC_NOTES.md` 1-50, the WORK_ORDER.md placement notes (3.6, the
summary lines). Every amendment was applied against the current text of its change (A-C2's Unit/Depends edits and the
`## A-C2 order notes` tables left untouched); every applied finding has a ledger row in its M file naming the finding.
Anchors were spot-checked against HEAD where a finding cites a line (`tests_js/` files for O-04..O-13, `CLAUDE.md:159-169`
for O-28, `buildgen/*.py` by AST for S-05, `buildgen/version.py`, A.U36.543's text in `U36b.md` for R-04/S-13). No
commit; nothing outside the five target files and this report was edited.

## Rows

| finding | M-ID / block | result | reason (adapted / declined / new) |
|---|---|---|---|
| AC3_O O-01 | M.WEB.052 | applied | |
| AC3_O O-02 | M.WEB.052 | applied | |
| AC3_O O-03 | M.WEB.052 | applied | appended right after O-02's comment edits in the same Change |
| AC3_O O-04 | M.WEB.052 | applied | both line-reference fixes |
| AC3_O O-05 | M.WEB.053 | applied | (a) `:242-246`/`:248-252`; (b) `:205-213` and the `:2-3` comment |
| AC3_O O-06 | M.WEB.054 | applied | |
| AC3_O O-07 | M.WEB.054 | applied | appended to the "Found while merging" note |
| AC3_O O-08 | M.WEB.054 | adapted | the existing "latency comment `:399-401` → the fake-timer switch's plain reason" clause corrected in place to `:403-405` with the finding's text, rather than repeated in the appended block; the rest appended to Change as written |
| AC3_O O-09 | M.WEB.058 | applied | |
| AC3_O O-10 | M.WEB.058 | applied | |
| AC3_O O-11 | M.WEB.059 | applied | |
| AC3_O O-12 | M.WEB.059 | applied | |
| AC3_O O-13 | M.WEB.057 | applied | |
| AC3_O O-22 (DOCS half) | M.DOCS.076 | applied | Resolved gains the reason; the M.SPEC.136 half is another applier's |
| AC3_O O-23 (WEB, DOCS rows) | M.WEB.060, M.DOCS.008 | applied | the other twelve tags are other appliers' files |
| AC3_O O-24 | M.PROC.033 | adapted | as written, plus the same Resolved sentence's "predates OR84-OR133" → "OR84-OR135" so it does not contradict itself |
| AC3_O O-25 | M.PROC.035 | applied | From gains OR135 (LEAD/R35) |
| AC3_O O-28 | M.DOCS.078 | adapted | `:159-161` cuts CLAUDE.md mid-sentence (`:162` "which stays the source of truth … unaffected by any real-hardware work." would dangle), so the span runs to `:162`'s sentence end; the now-redundant "`:159-160` gains (owner, 2026-09-03, `a19691c`)" clause removed (the new text carries the tag); title "… "device"" → "… never flashed, …"; Resolved cites OR78.a |
| AC3_O O-28 | M.GEN.055 | adapted | the header already says "never physically flashed"; a literal swap would repeat it, so the whole first clause becomes `# wozi.toml - never physically flashed; its correctness rests on L1/L2 (CLAUDE.md).` |
| AC3_O O-28 | M.DOCS.045 (the README row at M_DOCS.md:871) | applied | "the exemplary device" dropped |
| AC3_R R-01 | M.PROC.022 | applied | From, Change (2), Kind → "rule, test"; 14 PROC ledger rows |
| AC3_R R-02 | M.PROC.021 | applied | title, From, Change, Depends |
| AC3_R R-03 (DOCS half) | M.DOCS.064 | applied | A.U13.04 out of From; "no FRAM CS power-on row" in Change; DOCS ledger row for A.U13.04 → dropped. M.SRC_CORE.108 and M.SPEC.049 halves are other appliers' |
| AC3_R R-04 (doc) | M.DOCS.109 | new | merged with AC3_S S-13 (one change, per the brief); new section `## .claude/skills/integrate-module/SKILL.md (new)` |
| AC3_R R-04 (runs) | M.PROC.048 | new | the work order's `M.PROC.R04`; placed in P4 after M.PROC.045; two clauses of A.U36.543 (10)'s own text kept that R-04 shortened ("not by design freedom", "reported at the unit's end") |
| AC3_R R-06 | M.PROC.003 | applied | step (5a) and From; the register LEAD/R34 State half is the register applier's |
| AC3_S S-01 | M.GEN.064 | new | new section `## ext/freezefs/* (vendored)`; Unit notes the work order's U0R step |
| AC3_S S-02 | M.PROC.003 | applied | Change step (8), Site, From; PROC ledger row |
| AC3_S S-05 (GEN) | M.GEN.065 | new | new section `## buildgen/*.py (function and class docstrings)`; the 21 HEAD lines re-derived by AST and equal to S-05's list. The other seven S-05 changes are other appliers' |
| AC3_S S-11 | M.GEN.009 | applied | From, Change, Depends gains M.GEN.035 |
| AC3_S S-12 | M.WEB.074 | applied | Unit unchanged (no finding moves it; the work order places it as a constituent, so the tag lands in U28 with its Part N row per M.SPEC.156) |
| AC3_S S-13 | M.DOCS.109 | adapted | S-13's body summary "… then apply Part D" declined: A.U36.543 (9)'s own text (R-04's wording) has no Part D step — Part K applies Part D itself; Resolved records it |
| AC3_S S-15 | M.PROC.046, M.PROC.047 | new | placed under "File edits carried elsewhere" as S-15 says; M.PROC.047 written out in full format (Site, Depends, Blast filled from S-15's prose and M.TSC.044/.064); PROC ledger rows for A.U10.18/.35/.44 extended, A.U10.37/.38/.40/.43 and A.U36.038 (2) added |
| AC3_S S-16 | M.PROC.018 | applied | From, Site; ledger row; A.U28.35 removed from the "read for order or context" list (it is now a constituent) |
| AC3_S S-17 | M.PROC.022 | applied | merged with R-01 (the same set, WORK_ORDER 3.6); the file mapping kept in From |
| AC3_S §4 | M.DOCS.064 (A.C.10) | applied | |
| AC3_S §4 | M.WEB.031 (A.U23.04) | applied | |
| AC3_S §4 | M.WEB.054 (A.U23.36) | declined (no edit needed) | already in its From as `.36` in the `A.U23.03, .05, …` run, and WEB's ledger already maps A.U23.36 → M.WEB.054; the parser missed the shorthand. Ledger row annotated |
| AC3_S §4 | M.PROC.023 (A.U35.22) | applied | |
| AC3_S §5 | M.DOCS.085 | applied | Blast `M.TWIN.153/.154` → `M.TWIN.154/.156` (both verified in M_TWIN) |
| — | M_TOOL | no finding | no AC3 amendment, From completion or Blast fix lands in M_TOOL (S-05's `toolchain/` docstrings are already carried by M.TOOL.035/.043/.066/.067) |

## Hand-offs

1. Register (register applier): AC3_R R-06's LEAD/R34 State addition ("carried by M.PROC.003 (5a) (U0) and A-C2's
   `audit/order/WORK_ORDER.md` test schedule").
2. Lead / WORK_ORDER.md: `M.PROC.R04` is now `M.PROC.048` (U36, after M.DOCS.109).
3. SPEC applier (optional pointer precision, not an AC3 finding): M.SPEC.046/.142 hand A.U36.543 (9)-(10) to "DOCS" in
   their Blast; the carriers are now M.DOCS.109 and M.PROC.048.
4. Lead, observation only (not applied, no finding names it): M.DOCS.076 keeps "kept until the post-audit C
   reconciliation" and "reconciling it is post-audit only (owner, … 'anything there is post-audit only')" — the second
   is the owner's own quote; the first is the same kind of audit reference O-22 removed ("this audit"), so a
   G9/R12 reading may want "until the C reconciliation" there too.

## Counts

- Finding parts handled: 41 rows — applied 29, adapted 5 (O-08, O-24, O-28 ×2, S-13), new 5 rows carrying 6 changes
  (M.DOCS.109, M.GEN.064, M.GEN.065, M.PROC.046, M.PROC.047, M.PROC.048), declined 1 (S §4 M.WEB.054: already carried;
  S-13's "then apply Part D" clause is declined inside its adapted row), 1 no-finding row (M_TOOL).
- Merged changes per file now: M_WEB 60 (max .082), M_DOCS 109, M_PROC 48, M_GEN 65, M_TOOL 79 (unchanged); every
  block carries all eight slots, no duplicate IDs (scripted check).
- Hand-offs: 1 register, 1 work order, 1 optional SPEC pointer, 1 observation.
