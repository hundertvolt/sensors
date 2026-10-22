# U27 close: points the drafts could not settle from sources

Revised after the lead's rulings on the first draft's 15 points (2026-10-15). Final tree `7f34f35`.

## Settled by the lead's rulings (applied in the drafts)

- 1: the length rule is BACKLOG.md owner question 6 (text in `draft_backlog.md`), asked in the unit-end report, default (a).
- 2: the fallback rule (agent, 2026-10-15): next unit holding the file, else U35 for a test file, U37 for any other; applied
  to OF-150, OF-197, OF-199, OF-200 (no FALLBACK-TBD left).
- 3: OF-186 on the owner-review list only (OF-16's precedent), no BACKLOG question.
- 4, 8: OF-181 and the deviation counts re-sourced from `handbacks_TBS.md` (T 7, U 9, B 7, S 4, M 1, X 5, E 4 = 37).
- 5: the `zz_test_` globbers: checked, not raised; no `website_identity.py` row.
- 6: SPEC F.7 row 17: old/new text in `draft_lead_edits.md` (old line matched byte for byte at `7f34f35:SPECIFICATION.md:6554`).
- 7, 10, 13: as drafted; the two rounds tagged (agent, 2026-10-15); parked-delta states left as U26 left its own; OF-198 in
  the open findings only.
- 11, 12: both hold in the code at `7f34f35`: raised as OF-201 (U36) and OF-202 (U30).
- 14: the lead's wording used in the review and scan drafts; the microtest guard is
  `tests_scripts/test_microtest.py:301` (`test_json_loads_reads_no_response_body`), an M-set file.
- 15: lane E's figures, bites and four deviations in the review and scan drafts.

## Still open

1. **No U27 R-26.** `rulings.md` holds R-1 to R-25, `rulings_lead.md` R-27; R-17 cites "U26 R-26". Whether U27's R-26 was
   skipped on purpose was not found.
2. **How some deviations are counted.** B 7 counts the four items its hand-back lists under "Deviations" as "carried from
   earlier blocks"; X 5 counts its four stale-text fixes as one and leaves the brief's missing test file to the lead's row;
   M 1 leaves out its first run stopped on a stale generated tree (listed beside the deviation, a run event). Other readings
   give B 3, X 8 or M 2.
3. **`test_test_sh.py`'s growth.** Lane T timed it at 50.4 s (+14.9 % over the 43.88 s base, above R-17's 10 % bar); the
   lead's alone run at W1 gave 46.2 s (+5.3 %). The review row uses the lead's figure; the gate's own timing (GATE-TBD)
   decides.
4. **OF-150's unit.** The fallback rule gives U35 (no later unit holds `tests/test_voc_algorithm.py`), while the cause the
   numbers show is the harness heap's sweep length (`scripts/test.sh:542`, `l1.unix_heapsize`, next unit U28); CLAUDE.md
   rules out raising the heap or a per-file override as a fix, so the row carries a measurement, not a change.
5. **Owner question 6's numbers** (675 blocks in 399 files at 110, 116 in 106 at 120) were measured on lane U's tree
   (`494cb74`, relay U :37). Since then M added one keyword per call (AST-checked, no comment touched), X changed docs (not
   counted), and the W1 lead step, lanes T, B, S merges and lane E's two test files may have moved a block or two, so the
   figures may differ slightly at `7f34f35`; not re-measured (no runs here).
6. **OF-201's reach.** Only a caller passing a root other than `build/staged_html` can lose a directory; every recipe found
   at `7f34f35` uses the default or names it (`package.json:32`, README.md:375, SPECIFICATION.md:7642), so the row records
   a hazard of the documented `out_root` argument, not a seen loss.
