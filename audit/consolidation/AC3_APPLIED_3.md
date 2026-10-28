# A-C3 apply, applier 3: M_SRC_CORE, M_SRC_SENS, M_SRC_NET, M_TSC (2026-10-01)

Brief: `audit/sweeps/ac3_apply_prompt.md`. Inputs read in full: `AC3_O.md`, `AC3_R.md` (findings and method; the
appendix scanned for every row naming these four clusters: no finding there amends them beyond R-03), `AC3_S.md`, the
`ac_prompt.md` format, AC_NOTES 1-50, `audit/order/WORK_ORDER.md` 2, 3.1-3.6. Every A-C2 Unit/Depends edit and every
`## A-C2 order notes` table was left as found. No commit. Each edit has a ledger row (finding ID) in its M file.

## Rows

| finding | M-ID / block | result | note |
|---|---|---|---|
| AC3_R R-03 | M.SRC_CORE.108 | applied | Title, Site "none (`src/asy_fram_driver.py:110` stays)", Change, Unit "— (no step)", Kind "rule", Blast "SPEC C.3.1 → M.SPEC.049 (1)" as given; its A.U13.04 ledger row → "dropped as a measurement (withdrawn, AC_NOTES 11); its fact carried by M.SPEC.049". From and Resolved kept (both already cite AC_NOTES 11) |
| AC3_S S-03 | M.SRC_CORE.060 | applied | From gains A.U10.31; Change appends the bare-annotation sentence; Unit gains the U10 stage. Checked at HEAD by AST: the one instance is `make_logger() -> "PrintLogHistory"` (`src/print_log.py:287`), which M.SRC_CORE.061 already writes bare in U5, so the U10 stage holds as a confirmation. A.U10.31 ledger row adds .060 |
| AC3_S S-03 | M.SRC_SENS.030 | applied | From gains A.U10.31; Change appends the sentence. HEAD AST check: the 3 are `:117` (`color`), `:233`, `:237` (`"asyncio.Task[None]"`). Unit untouched (already holds a U10 stage; S-03 gives none for this file). A.U10.31 ledger row adds .030 |
| AC3_S S-03 | M.SRC_NET.211 | applied | From gains A.U10.31 (`:87`, `:96`, `:101`, confirmed by AST); Change appends the three unquoted signatures (the methods survive: M.SRC_NET.213 passes them into `ResponderCallbacks`). Unit untouched (U10 stage exists). A.U10.31 ledger row adds .211 |
| AC3_S S-04 | M.SRC_CORE.132 | new | Full format, U10 per WORK_ORDER 3.6. Placed after the highest number (.131, end of the last section) under its own `##` heading naming the three files, not inside `## src/config_manager.py` as S-04 suggests: the brief's rule 3 governs placement; the Site names all three files. Class lines checked at HEAD |
| AC3_S S-04 | M.SRC_SENS.093 | new | Full format, U10. Placed after .092 (the file's highest number; .092 follows .088 in the ISL section) under its own `##` heading naming the six files. Class lines checked at HEAD; `asy_spi_driver.py:33 SPI` is distinct from M.SRC_SENS.004's `SPIDevice`, so no overlap. A.U10.33 ledger row adds .093 |
| AC3_S S-05 (TSC part) | M.TSC.228 | new | Body as S-05 gives it, Site = S-05's TSC list, U10. Re-derived by AST over `tests_scripts/` at HEAD: 71 function/class docstrings in 27 files, identical to the list; the 28th file, `test_comment_block_cap.py:37`, stays M.TSC.065's. A.U10.34 ledger row adds .228. (S-05's other seven clusters are other appliers') |
| AC3_S S-14 | M.TSC.165 | adapted | From gains A.S0930.34 (4); Change appends the deadline-helper case as given. S-14's Unit line ("with M.SCR.054 (S0930, after U25)") not written: A-C2 already placed this part in U26 in the Unit slot (WORK_ORDER 3.6: A.S0930.34 needs A.U26.71). A.S0930.34 ledger row adds .165 |
| AC3_S §4 | M.SRC_SENS.054 | applied | From gains A.U0.35 (B03, `:162-163`). Ledger A.U0.35 adds .054 |
| AC3_S §4 | M.SRC_SENS.033 | applied | From gains A.U10.21, A.U11.31. Ledger rows of both add .033 |
| AC3_S §4 | M.SRC_SENS.061 | applied | From gains A.U10.31. Ledger A.U10.31 adds .061 |
| AC3_S §5 | M.SRC_NET.165 | adapted | `test_suppression_form.py` → A.U28.30 label SCR → TSC as given; the same slot's `test_fatal_report_sites.py` → A.U30.19 label also SCR → TSC (also a `tests_scripts/` file, carried by M_TSC's `## tests_scripts/test_fatal_report_sites.py`) |
| AC3_S §5 | M.SRC_NET.172 | applied | "A.U10.47's check (SCR)" → "(TSC)" (M.TSC.064 carries A.U10.47) |
| AC3_S §5 | M.SRC_NET.204 | applied | "A.U10.47 check (SCR)" → "(TSC)" |
| AC3_O O-23 | M.SRC_CORE.013 | applied | `:133` comment "(owner-confirmed, 2026-07-18)" → "(owner, 2026-07-18)" |
| AC3_O O-23 | M.SRC_CORE.091 | applied | both after-texts → "(owner, 2026-07-18: reject generally at the top)" and "(owner, 2026-07-18)"; no "owner-confirmed" left in the file |
| AC3_O O-23 | M.SRC_SENS.017 | applied | "(owner-confirmed, 2026-07-21)" → "(owner, 2026-07-21)" |
| AC3_O O-23 | M.SRC_SENS.071 | applied | the Change's `:90-91` after-text → "(agent, 2026-09-14)"; its Resolved keeps the quote of A.U0.35's wording and states the normalised form. A grep of all four files for other non-standard actor tags in after-texts found none |
| AC3_O O-05 (b) / M.TSC.110 | M.TSC.110 | checked, no edit | The `wozi` comment at `tests_js/definitions.test.js:205-207` is M.WEB.053's to remove (WEB's applier); M.WEB.053's U6 stage holds that site and M.TSC.110's `_NOT_YET_CLEANED` covers any file still carrying a literal when its U6 stage lands. O-28's rewordings are in `devices/` and `*.md`, outside the scan. O-section B's `<A.U6.15's check>` → `test_no_variant_literals.py` is M.SPEC.144's (SPEC) |
| AC3_R R-08 (h) | M.TSC S0930 stages | checked, no edit | A-C2 already wrote the per-part units into M_TSC's Unit slots (its order-notes table) |
| AC3_R R-07, R-08 (e), R-09; R-12-R-14 | M.TSC.147, M.SRC_CORE.063, M.SRC_SENS.047/.053/.086 | checked, no edit | register or other-cluster amendments only; these M-IDs are cited, not amended |

## Hand-offs

- **Lead / work order**: M.SRC_CORE.108 now has no step; `audit/order/WORK_ORDER.md` (U13 line, and the C list) and
  `work_order.json` still list it (WORK_ORDER 3.6 left this to the lead).
- **DOCS / SPEC appliers (same finding, R-03)**: M.DOCS.064 drops the A.U13.04 BACKLOG row and M.SPEC.049 (1) takes the
  lead's rewrite; M.SRC_CORE.108's new Blast points at M.SPEC.049 (1) and assumes both land.
- None of my edits needs a change in a file I do not own.

## Counts

- Finding parts handled: 18 rows (13 applied, 2 adapted, 3 new, 0 declined) plus 3 checked-without-edit rows.
- New merged changes: 3 (M.SRC_CORE.132, M.SRC_SENS.093, M.TSC.228).
- Existing merged changes amended: 15 (M.SRC_CORE.013, .060, .091, .108; M.SRC_SENS.017, .030, .033, .054, .061, .071;
  M.SRC_NET.165, .172, .204, .211; M.TSC.165; plus ledger rows in all four files).
- Unit slots changed: M.SRC_CORE.108 ("— (no step)", R-03) and M.SRC_CORE.060 (U10 stage added, S-03); no Depends slot
  changed.
