# A-C3 apply, applier 4: TWIN, HW_BENCH, HW_DEV, TEST_UNIT, TEST_HELP (2026-10-01)

Brief: `audit/sweeps/ac3_apply_prompt.md`. Inputs read in full: `AC3_O.md`, `AC3_S.md`, `AC3_R.md` (findings and the
checked/settled sections; the appendix scanned for this cluster set), `AC_NOTES.md` 1-50, `WORK_ORDER.md` sections 1-3
and `work_order.json` (units of the new changes). Every anchor was read at the current text (A-C2's Unit/Depends edits
and order-notes tables left as they are). Code facts re-checked at HEAD: the docstring sites (AST), the public
`def make_` counts, the 40 `tests_hardware/` future imports, `digital_twin/network.py`'s five `Any`,
`tests/test_tmp_scratch.py:116-123`, the UART load script's churn loop and its five load counters. Every touched
bullet was rewrapped to the files' 120-column form; each M file's ledger gained the rows named below.

## Applied findings

| finding | M-ID / block | result | note |
|---|---|---|---|
| AC3 O-15 | M.TWIN.019 | applied | the `install()` comment → "# Bound from outside, as every test adapts a product seam: src/ stays unchanged." |
| AC3 O-17 | M.TWIN.052 | applied | the sampler comment ends at the check's path; the verdict clause is appended only when B3 keeps the collect |
| AC3 O-18 | M.TWIN.062 | applied | "(M.TWIN.032)" leaves the quoted README text, named outside the quote |
| AC3 O-23 | M.TWIN.044 | applied | Change header tag → "(owner, 2026-08-12: chosen over a probabilistic flaky mode)"; the From slot still quotes the HEAD tag A.U0.31 rewrites (audit text) |
| AC3 O-23 | M.TEST_UNIT.127 | applied | `:215` tag → "(owner, 2026-09-26; SPECIFICATION.md C.8)" |
| AC3 O-23 | M.HW_BENCH.076 | applied | docstring tag → "(owner, 2026-09-01)" |
| AC3 O-23 | M.HW_BENCH.080 | applied | section comment tag → "(owner, 2026-09-02)" |
| AC3 O-16 | M.TEST_UNIT.279 | applied | comment cites SPECIFICATION.md C.7, not A.U3.03 |
| AC3 O-26 | M.HW_BENCH.075 (1) | applied | the unpatched-image test passes only when the stall reproduces, fails with the given message otherwise; Resolved names OR19.a/OR21.a/OR114.a |
| AC3 O-27 | M.HW_DEV.122 | applied | Blast gains the `gc.collect()` allowance row → M.SCR.015 (U31 stage); M.SCR.015's own text is a hand-off |
| AC3 S-05 | M.TWIN.165 | new | U10; Site from the AST (5 docstrings); the unwedge module's one converts in U10 and leaves with the file in U25 (M.TWIN.056) |
| AC3 S-05 | M.TEST_UNIT.340 | new | U10; `test_system_service.py` named with its same-unit rename |
| AC3 S-05 | M.TEST_HELP.068 | new (adapted) | U10; `_webserver_concurrency_scenarios.py` has seven docstrings at HEAD (AC3_S says six), all leaving with the file in U25 (M.TEST_HELP.033, not .031 as Part S §6 names) — stated in Resolved |
| AC3 S-05 | M.HW_BENCH.136 | new (adapted) | U10; Site split from S-05's single AST query: 83 docstrings in 17 files outside `device_scripts/`/`flash/` (`manual/runner.py`'s two stay M.HW_BENCH.100's); Resolved "the B3 convention is this change" and records the B3 count difference |
| AC3 S-05 | M.HW_DEV.158 | new | U10; `device_scripts/` and `flash/`: 19 in 11 files, listed |
| AC3 S-06 | M.HW_BENCH.137 | new | U20; the 28 files; Change is B2's text; Blast → M.TOOL.079 |
| AC3 S-07 | M.TEST_UNIT.341 | new | U24, Depends A.U24.49; the 19 files with HEAD counts (all re-counted, matching) |
| AC3 S-07 | M.TWIN.166 | new | U24, Depends A.U24.49; the three twin test files |
| AC3 S-08 | M.TEST_UNIT.338 | applied | From/Site gain A.U24.38 `:116-123`; the missing-key test runs under `_RecordingOs` |
| AC3 S-09 | M.TWIN.040 | adapted | From gains A.U25.63; the types are written, but `config_calls`/`connect_calls` are `BoundedLog` at the end state (M.TWIN.040's own Change; M.TWIN.001's class is not generic), so they are annotated `BoundedLog` with the entry types stated, not `deque[...]` |
| AC3 S-10 | M.HW_DEV.051 | applied | From gains A.U26.47 (3); Change (2) records one bounded failure, the host asserts `alloc_failures == 0` |
| AC3 S-10 | M.HW_DEV.045 | adapted | From gains A.U26.47 (3); the assertion goes into (7) (the load test), not (3) (the parametrisation); (7)'s "every load counter > 0" now excepts `alloc_failures`, which is one of the script's five load counters and would otherwise be required > 0 |
| AC3 S-10 | M_HW_DEV ledger A.U26.47 | applied | "merged into M.HW_DEV.045, M.HW_DEV.051; M.HW_DEV.095 (soak markers)" |
| AC3 S-18 | M.TEST_UNIT.306 | applied | Resolved names `tests/test_asy_fram_manager.py` |
| AC3 S §4 | M.HW_BENCH.050 | applied | From gains A.U2.03 (the U2 import already stated in Unit); ledger row A.U2.03 gains .050 |
| AC3 S §4 | M.TEST_HELP.001 | applied | From gains A.U21.13; its ledger row changes from "blast-only, holds" to M.TEST_HELP.001 |
| AC3 S §5 | M.HW_DEV.060 | applied | Blast seam count → M.TEST_UNIT.041 (no TSC change carries A.U26.43); M.TEST_UNIT.041 confirmed to carry `test_one_chunk_write_is_five_driver_transfers_in_seam_order` |
| AC3 S §5 | M.HW_DEV.063 | applied | same pointer |
| AC3 R-08 (h) | M.HW_BENCH.115, .130 | applied | Unit slot gains the work order's placement of each A.S0930 part (.115: .05/.06 in U26; .130: .06/.19 in U26, .30 in U36), from `work_order.json` |
| AC3 R-08 (h) | M.HW_BENCH.119 | adapted | not named by number, but its Unit slot names the same "SUPP_owner_0930" stage; placed the same way (.15/.28/.29/.39/.40 in U26, .30/.41 in U36) |

## Findings in these clusters with no M-file edit owed

| finding | why |
|---|---|
| AC3 R-07 (M.HW_BENCH.007, M.HW_DEV.004 cited) | register State amendment only (G4/R54, G7/R23, G8/R31) |
| AC3 R-08 (a), (d), (e), (f) (M.TEST_UNIT.211, .236, .290, M.TWIN.146 cited) | register State amendments; WORK_ORDER 3.6 checked them against the order |
| AC3 R-09 (M.TEST_UNIT.201 cited) | the amendment is M.SPEC.021 and the register (G6/R51); no test-side change named — none owed here |
| AC3 R-01 (M.HW_DEV.010, M.TEST_HELP.042 cited) | carried by M.PROC.022's amendment |
| AC3 S-15 (TEST_UNIT/TWIN/HW_BENCH/HW_DEV rename conventions) | the step is M.PROC.046 (M_PROC); the conventions stay as its per-cluster wording |
| AC3 O section E (M.TEST_UNIT.029/.205/.324, M.TWIN.158, M.HW_DEV.118) | confirmed, no amendment |

## Declined

None.

## Hand-offs

- **Applier 2 (M_SCR)**: AC3 O-27's M.SCR.015 half — the U31 "measured collection pause" row for
  `tests_hardware/device_scripts/loop_stretch_timing.py` and the "by category" rewording. M.HW_DEV.122's Blast now points
  at it.
- **Applier 1 (M_DOCS)**: AC3 S §5's M.DOCS.085 pointer (M.TWIN.153 → M.TWIN.154/.156); M.TWIN.154 and .156 exist as named.
- **Lead / register**: R-07, R-08 (a)-(g), R-09's register States citing M-IDs of these clusters (no M-file text owed).
- **Lead (optional)**: the HW_BENCH preamble's B3 count "91 in 11 files" is A.U10.34's count; M.HW_BENCH.136's Resolved
  records the AST count at this HEAD instead of rewriting the convention.

## Counts

- Finding parts handled: 30 rows — applied 19, adapted 3 (S-09, S-10's M.HW_DEV.045, R-08 (h)'s M.HW_BENCH.119), new 8
  (M.TWIN.165, .166, M.TEST_UNIT.340, .341, M.TEST_HELP.068, M.HW_BENCH.136, .137, M.HW_DEV.158; two of them, .068 and
  M.HW_BENCH.136, adapted in Site/Resolved), declined 0.
- Files edited: `M_TWIN.md`, `M_HW_BENCH.md`, `M_HW_DEV.md`, `M_TEST_UNIT.md`, `M_TEST_HELP.md`; no Unit or Depends slot
  changed beyond R-08 (h)'s three placement lines; every new change carries the unit `WORK_ORDER.md` 3.6 gives it.
- Ledger rows: TWIN 1 extended + 7 new; HW_BENCH 3 extended + 3 new; HW_DEV 1 rewritten + 4 new; TEST_UNIT 2 extended +
  5 new; TEST_HELP 1 rewritten + 1 new.
