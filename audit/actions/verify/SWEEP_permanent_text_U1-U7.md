# Sweep: temporary audit IDs in planned permanent text, U1-U7 (2026-09-29)

Rule: G9/R12, OR68.a (4). Dates are from PROJECT_AUDIT_PLAN.md 3.2: OR32 2026-09-25, OR28.a 2026-09-25,
OR29.a 2026-09-25, OR61/OR61.a, OR48.a, OR52.a, OR35.b, OR56, OR42.c, OR46.b, OR72.a, OR40.a, OR45.a and
OR64.a 2026-09-26, PQ10 answer 2026-09-26 (WEB.T09 row), OR77/OR79 2026-09-28. Where an ID had to stay
visible to the executor, it now sits outside the planned text as `[src: …]`. These brackets are notes for
the executor and are never written into the permanent file.

## Changes

- U1.md A.U1.03 Change §1: `(owner, 2026-09-26, PQ10)` … `(owner, 2026-09-25, OR32).` → `(owner, 2026-09-26)` … `(owner, 2026-09-25). [src: PQ10, OR32 — not written]` (source: OR32 row; PQ10 answer, WEB.T09 "owner 2026-09-26")
- U1.md A.U1.03 Change §2: `(owner, 2026-09-26, OR61 "all legacy real devices run 1.24.1")` → `(owner, 2026-09-26: "all legacy real devices run 1.24.1") [src: OR61]` (source: OR61 row)
- U1.md A.U1.03 Change §4: `(owner, 2026-09-26, OR48.a (4)).` → `(owner, 2026-09-26). [src: OR48.a (4)]` (source: OR48.a row)
- U1.md A.U1.04 Change (MPRLS): `a Phase C bench scan settles it, G1/R40` → `a bench scan settles it [src: Phase C, G1/R40]` (source: G1/R40 register block)
- U1.md A.U1.04 Change (BME688): `the owner confirms at the first Phase C round, O.12` → `the owner confirms at the first hardware round [src: Phase C, O.12]` (source: A.U1 open point O.12)
- U1.md A.U1.04 Change (bench state): `at the first Phase C round, O.11 — … task, G8/R26` → `at the first hardware round — … task [src: Phase C, O.11, G8/R26]` (source: G8/R26 register block)
- U1.md A.U1.04 Change (VFS rule): `(OR86.a carries this pitfall into LEAD/R22's docs, U27/U20)` → `[note, not written: OR86.a carries … U27/U20]` (source: OR86.a row)
- U1.md A.U1.10 Change: `(owner, 2026-09-25, OR32)` → `(owner, 2026-09-25)` (source: OR32 row; Why cites OR32.a)
- U1.md A.U1.11 Change: `(owner, 2026-09-26, OR61.a)."` → `(owner, 2026-09-26)." [src: OR61.a]` (source: OR61.a row)
- U1.md A.U1.19 Change (:149-151): `never on the dev bench (OR61.a)"` → `never on the dev bench (owner, 2026-09-26)" [src: OR61.a]` (source: OR61.a row)
- U1.md A.U1.19 Change (:160-162): `(owner, 2026-09-26, OR52.a (1), OR61.a)"` → `(owner, 2026-09-26)" [src: OR52.a (1), OR61.a]` (source: OR52.a, OR61.a rows)
- U2.md A.U2.01 Change, errno row 1 (catalog `text`): `retired (A.U3.03): the streak …` → `retired: the streak …`; the ID moves to the "replaces" column as `(retired by A.U3.03)` (source: action ID only, no owner row)
- U2.md A.U2.01 Change, wrnno row 46: `retired with A.U5.06 (no \`register()\` after construction); never reused` → `retired: no \`register()\` after construction; never reused`; the ID moves to the "replaces" column (source: action ID only)
- U2.md A.U2.01 Change, wrnno row 47: `retired with A.U5.06 (no \`finalize()\`); never reused` → `retired: no \`finalize()\`; never reused`; the ID moves to the "replaces" column (source: action ID only)
- U2.md A.U2.22 Change (C.7 paragraph): `the catalog test (A.U2.02) enforces all of it` → `the catalog test (\`tests_scripts/test_error_catalog.py\`) enforces all of it [src: A.U2.02]` (source: A.U2.02's own site)
- U2.md A.U2.22 Change (C.7.1): `with OR28.a's owner words and date` → `with the owner's words and the tag "(owner, 2026-09-25)" [src: OR28.a]` (source: OR28.a row)
- U3.md A.U3.10 Change: `(owner words OR35.b, dated)` → `(the owner's words "just don't repeat the same error in the slots. Pure and simple", tagged "(owner, 2026-09-26)" [src: OR35.b])` (source: OR35.b row)
- U3.md A.U3.10 Change: `(OR56 (1) owner words)` → `with the owner's words "Either it's a fault or a warning, but never both at a time" and "(owner, 2026-09-26)" [src: OR56 (1)]` (source: OR56 row)
- U3.md A.U3.11 Change (allow-list reason): `separate conditions, G6/R20)` → `separate conditions) [src: G6/R20]` (source: G6/R20 register block)
- U4.md A.U4.07 Change (quoted THR/test-comment text): `… or its wear reason is listed (U26, G1/R17)".` → `… or its wear reason is listed" [src: U26, G1/R17].` (source: G1/R17 register block)
- U4.md A.U4.08 Change (C.8/conftest text): `… SelfCal (OR42.c (4)).` → `… SelfCal [src: OR42.c (4)].` (source: OR42.c row)
- U5.md A.U5.17 Change (pyproject comment): `with the owner's OR46.b words and date` → `with the owner's words and the tag "(owner, 2026-09-26)" [src: OR46.b]` (source: OR46.b row)
- U5.md A.U5.17 Change (per-file reason): `mirror \`machine.UART\`/\`SPI\`, G2/R23)` → `mirror \`machine.UART\`/\`SPI\`) [src: G2/R23]` (source: G2/R23 register block)
- U6.md A.U6.15 Change (`_NOT_YET_CLEANED` values): `maps each file … to the unit that removes it (U23 js, …, U28 ci.yml)` → `maps each file … to a short statement of the change that removes it, named by its content, never by an audit unit label [src: the removing units are U23 js, …, U28 ci.yml]` (source: G8/R01 register block; values in a permanent test file)
- U6.md A.U6.25 Blast docs (`asy_wifi_service.py:168-169` comment): `"shown on the Networking page (OR72.a (8))"` → `"shown on the Networking page (owner, 2026-09-26)" [src: OR72.a (8)]` (source: OR72.a row)
- U7.md A.U7.01 Change (E.6.1 GC-stage column): `L3/L4 the two-image proof of OR40.a (3)` → the fact in place (a `dev` image built without the threshold runs the full flash and bench levels first, then the normal image, once in the final hardware phase) with `"(owner, 2026-09-26)" [src: OR40.a (3)]` (source: OR40.a row)
- U7.md A.U7.01 Change (text below the table): `containment in both senses of OR45.a (2) — … first (A.U7.18), … (A.U7.24)` → `containment in both senses, "(owner, 2026-09-26)" [src: OR45.a (2)] — … first (\`scripts/_run_lower_levels.sh\` [src: A.U7.18]), … (\`tests_scripts/test_level_containment.py\` [src: A.U7.24])` (source: OR45.a row)
- U7.md A.U7.04 Change (printed root-cause line): `… record it as a root-cause item (LEAD/R03)\`` → `… record it as a root-cause item\` [src: LEAD/R03]` (source: LEAD/R03 register block)
- U7.md A.U7.25 Change row (1): `the owner's decision (A05, "(owner, 2026-09-03)"), not "no real board" (V03, OR61.a)` → `the owner's decision "(owner, 2026-09-03)", not "no real board" [src: A05, V03, OR61.a]` (source: A05 tag as given; OR61.a row)
- U7.md A.U7.25 Change row (2): `(OR64.a "(owner, 2026-09-26)")` → `"(owner, 2026-09-26)" [src: OR64.a]` (source: OR64.a row)
- U7.md A.U7.25 Change row (3): `("(owner, 2026-09-22)"; one wording, V33)` → `"(owner, 2026-09-22)" [src: V33, one wording]` (source: tag as given)
- U7.md A.U7.25 Change row (7): `pending the OR77/OR79 bench attempt (harmonization 45)` → `pending a real-bench attempt; the skip stays only if that attempt shows unreasonable effort or covers nothing an L1-L3 test cannot "(owner, 2026-09-28)" [src: OR77/OR79, harmonization 45]` (source: OR77.a, OR79.a rows)
- U7.md A.U7.25 Change row (8): `(G3/R34, OR29.a (4), owner 2026-09-25)` → `"(owner, 2026-09-25)" [src: G3/R34, OR29.a (4)]` (source: OR29.a row)
- U7.md A.U7.25 Change row (9): `(G3/R34, same source)` → `"(owner, 2026-09-25)" [src: G3/R34, OR29.a (4)]` (source: OR29.a row)

Counts: U1 11 · U2 5 · U3 3 · U4 2 · U5 2 · U6 2 · U7 8 (33 total).

## Flags (not changed)

- U5.md A.U5.02 (`AsyFramManager` bullet) cites "C.7.1" for the owner's rule "the ONLY module which NEVER has
  own FRAM logging is the FRAM module itself". A.U2.22 deletes every per-module row of C.7.1, and SPEC does not
  hold that quote verbatim at HEAD (grep). The pointer resolves only if A-C keeps A.U2.22's FRAM-manager
  statement in C.7.1. If the text lands as a code comment, it should name the statement it points to.
- Checked, no flag: A.U2.01 errno 33 `text` "(C.7.3)" (A.U2.22 does not touch C.7.3); A.U6.26 description
  "Part H.4's accepted gap" (A.U6.17 rewrites H.4 :4378, the gap row :4382 stays); A.U4.04 "(compare-before-write,
  G.2)" (A.U4.01 adds the entry); E.6.1/E.6.6 (A.U7.01/A.U7.25) and B.9 (A.U1.16) keep their numbers and only
  change titles or content. No planned text in U1-U7 cites an E.6.6 numbered item. BACKLOG items 1 and 3 stay
  (A.U1.19). The items A.U1.19/A.U2.23 delete are cited by no planned text.

## Unresolved

- U7.md A.U7.25 row (10) `fram-write-protect-no-rest` carries "(agent, recorded at `test_fram_storage.py:81`; …)"
  with no date. It has no audit ID, so it was left unchanged here. The date is not in the cited register
  blocks; it needs `git blame` at execution.

## U0 and U8 (2026-09-29)

Same rule and style as above. Dates are from PROJECT_AUDIT_PLAN.md 3.2: OR30/OR30.a 2026-09-25; OR37.a,
OR39.a, OR40/OR40.a, OR58.a, OR70.a (C07 settled there) and OR72.a 2026-09-26; OR81/OR81.a 2026-09-28; RF014's
owner words 2026-07-28 (`5ddbcd3`, as A.U8.09's Why cites them). The U8 agent reading of '≪' is dated by the
commits that wrote it (`afebcad`/`25584c4`, both 2026-09-29, `git log -S`). "Phase C", "B0" and "B2" are audit
phase labels, and L-COMPAT/L-BLOCK are audit lens labels, so they are treated as IDs too.

### U8 changes

- U8.md header "Classes" (N.1's class list): `(N.1, from OR30.a (1))` … `excluded, OR30.a (1))` … `not tagged, L-COMPAT)` … `(V.U8.02)` → `(N.1's class list, written as below) [src: OR30.a (1)]` … `excluded "(owner, 2026-09-25)") [src: OR30.a (1)]` … `not tagged) [src: L-COMPAT]` … `[src: V.U8.02]` (source: OR30.a row)
- U8.md A.U8.01 Change (N.1): `the per-service timeout rule (RF014) quoted with its owner tag` → `the per-service timeout rule quoted with the owner's words and the tag "(owner, 2026-07-28)" [src: RF014]` (source: RF014 owner words as quoted in A.U8.09's Why)
- U8.md A.U8.01 Change (N.3 Basis form): `` `owner decision <date> (<row>)` `` → `` `owner decision (owner, <date>)` (the owner row's ID stays in the action's `[src: …]` note, never in the Part N row) `` (source: G9/R12 rule; the form is a template)
- U8.md A.U8.01 Blast (CLAUDE.md bullet): `(OR30 "updated on changing parameters …")` → `[src: OR30 "updated on changing parameters …"]` (source: OR30 row)
- U8.md A.U8.01 Blast (SPEC TOC line): `` `- **Part N** — Tunable Parameters (the OR30 register)` `` → `` `- **Part N** — Tunable Parameters` [src: OR30 register] `` (source: OR30 row)
- U8.md A.U8.02 Change (row label): `"agent reading (U8): HEAD's ratio; the real margin is U10's supervisor-scan budget (RF183, XCUT.S01), written into `wdt.timeout_ms`'s row"` → `"agent reading (agent, 2026-09-29): HEAD's ratio; the real margin is the supervisor-scan budget, written into `wdt.timeout_ms`'s row" [src: U8's reading; U10's supervisor-scan budget, RF183, XCUT.S01]` (source: `git log -S` on U8.md, 2026-09-29)
- U8.md A.U8.04 Change (`outer_cap_s`/`per_call_timeout_s` Basis): `measurement owed: C (silicon 5.12-5.16 s / 15.1 s, …)"` → `measurement owed: real hardware (silicon 5.12-5.16 s / 15.1 s, …)" [src: Phase C]` (source: phase label only)
- U8.md A.U8.04 Change (`chunk_bytes` Basis): `"owner decision 2026-09-26 (OR72.a (3))"` → `"owner decision (owner, 2026-09-26)" [src: OR72.a (3)]` (source: OR72.a row)
- U8.md A.U8.06 Change (`gc_pause_worst_ms` Basis): `re-measure owed (C, with the two-image GC proof, OR40.a (3))"` → `re-measure owed on real hardware, with the two-image GC proof" [src: Phase C, OR40.a (3)]` (source: OR40.a row)
- U8.md A.U8.08 Change (`wdt.timeout_ms` Basis): `"owner decision 2026-09-26 (C07, OR70.a); cap 8388 ms …"` → `"owner decision (owner, 2026-09-26); cap 8388 ms …" [src: C07, OR70.a]` (source: OR70.a row, C07 settled there)
- U8.md A.U8.09 Change (N.1): `with RF014's owner quote` → `with the owner's words and the tag "(owner, 2026-07-28)" [src: RF014]` (source: RF014 in A.U8.09's Why)
- U8.md A.U8.11 Change (idle-rate Basis): `"measurement owed (U18/C): loop-share at idle on L2 and L4"` → `"measurement owed: loop-share at idle on L2 and L4" [src: U18, Phase C]` (source: unit and phase labels only)
- U8.md A.U8.14 Change (`gc.threshold_bytes` Basis): `"owner direction (`887da0e`), OR40 (owner, 2026-09-26)"` → `"owner direction (`887da0e`); (owner, 2026-09-26)" [src: OR40]` (source: OR40 row)
- U8.md A.U8.14 Change (`tool.uv_sync_attempts` Basis): `basis OR37.a (2) "(owner, 2026-09-26)" keeps the three-attempt retry` → `basis "the three-attempt retry stays (owner, 2026-09-26)" [src: OR37.a (2)]` (source: OR37.a row)
- U8.md A.U8.15 Change (`runner.per_file_timeout_s` Margin): `(B0 records them, OR39.a (3))` → `[src: B0 records them, OR39.a (3)]` (source: OR39.a row)
- U8.md A.U8.15 Change (`ci.web_unit_tests_timeout_min` Basis): `measurement owed: B0 wall clock of `web-unit-tests` on GitHub runners"` → `measurement owed: wall clock of `web-unit-tests` on GitHub runners" [src: B0]` (source: phase label only)
- U8.md A.U8.15 Change (`ci.unit_tests_gc_threshold_timeout_min` Basis): `measurement owed: B0"` → `measurement owed: wall clock of `unit-tests-gc-threshold` on GitHub runners" [src: B0]` (source: the sibling row's wording; the job is the one the ID names)
- U8.md A.U8.16 Change (band Basis): `"calibration on the Pi4 owed (U35/C)"` → `"calibration on the Pi4 owed" [src: U35, Phase C]` (source: unit and phase labels only)
- U8.md A.U8.17 Change (widening Basis): `measurement owed: B0 per-test elapsed at both GC stages on the slowest host"` → `measurement owed: per-test elapsed at both GC stages on the slowest host" [src: B0]` (source: phase label only)
- U8.md A.U8.19 Change (`loop.sync_wait_max_us` Checked by): `"B2 L-BLOCK review" (lens per file, plan 4.2)` → `"code review of each `src/` file for synchronous waits" [src: B2 L-BLOCK review, lens per file, plan 4.2]` (source: plan 4.2 lens)
- U8.md A.U8.24 Change (config comment): `"baseline: cleared by the unit that owns the file (G8/R61)"` → `"baseline: a module leaves this list once its explicit-`Any` findings are cleared; the list ends empty (owner, 2026-09-28)" [src: G8/R61, OR81/OR81.a; the clearing units are U10-U34]` (source: OR81/OR81.a rows)
- U8.md Appendix C.0.2 Deferred: `mark it "deferred U25" / "deferred U26".` → `… in the classification working list only, never in a tag, a Part N row or a code comment.` (source: G9/R12 rule)

Checked, kept: the `@tunable` IDs (`web.outer_cap_s`, `l1.…`, …) are product identifiers; L0-L4 are SPEC E.6 test
levels; "H.7.1", "B.14.2", "E.3.1" etc. are SPEC sections; commit SHAs stay.

### U0 changes

Every "The commit message carries …" note (19, not 15: A.U0.10, .11, .19, .21, .22, .23, .24, .25, .27, .29, .32,
.33, .34, .35, .36, .37, .38, .39, .40) now reads "The commit message cites no audit ID [src: <the same IDs,
verbatim>]". One entry per note:

- U0.md A.U0.10 Change note: `The commit message carries OR68 '4. yes', OR64 and OR68.a (2).` → `The commit message cites no audit ID [src: OR68 '4. yes', OR64 and OR68.a (2)].` (source: AC_NOTES.md item 4)
- U0.md A.U0.11 Change note: `… carries OR71.a (1), OR2, OR2.a, OR2.c, OR3, OR6.a (1)(2) and PQ8.` → `… cites no audit ID [src: OR71.a (1), OR2, OR2.a, OR2.c, OR3, OR6.a (1)(2) and PQ8].` (source: same)
- U0.md A.U0.19 Change note: `… carries OR72.a (8).` → `… cites no audit ID [src: OR72.a (8)].` (source: same)
- U0.md A.U0.21 Change note: `… carries OR87 and OR87.a (a).` → `… cites no audit ID [src: OR87 and OR87.a (a)].` (source: same)
- U0.md A.U0.22 Change note: `… carries OR89.a (4) and OR68.a (2).` → `… cites no audit ID [src: OR89.a (4) and OR68.a (2)].` (source: same)
- U0.md A.U0.23 Change note: `… carries OR24.a (2) and OR68.a (1).` → `… cites no audit ID [src: OR24.a (2) and OR68.a (1)].` (source: same)
- U0.md A.U0.24 Change note: `… carries OR61.a (2); the runbook is U32's.` → `… cites no audit ID [src: OR61.a (2)]; the runbook is U32's.` (source: same)
- U0.md A.U0.25 Change note: `… carries OR68.a (1), OR66.a, OR83.a, OR69.a (6), OR58.a, OR52.a (2), OR89.a (3) and the list-A IDs (A49 among them).` → `… cites no audit ID [src: …same…].` (source: same)
- U0.md A.U0.27 Change note: `… carries OR68.a (1) and OR89.a (3).` → `… cites no audit ID [src: OR68.a (1) and OR89.a (3)].` (source: same)
- U0.md A.U0.29 Change note: `` … carries OR58.a, OR73.a and the `ee5310c` decision numbers (#1, #2, #3, #6, #7). `` → `… cites no audit ID [src: …same…].` (source: same)
- U0.md A.U0.32 Change note: `… carries OR69.a (9), OR70.a (1)(2)(8)(10), OR52.a (3) and OR72.a (9)(10).` → `… cites no audit ID [src: …same…].` (source: same)
- U0.md A.U0.33 Change note: `… carries OR69.a (1)(3)(4)(5)(8)(9), …, OR83 and OR33.a, and names the retired labels this text replaces (T1, T4, W3, F18, LEAD/R07).` → `… cites no audit ID [src: …same…].` (source: same)
- U0.md A.U0.34 Change note: `… carries OR68.a (2), OR69.a (2), OR70.a (4), OR72.a (1)-(5), (7), (10), LEAD/R07 and the retired labels F18/T4/W3/T1/WP5.` → `… cites no audit ID [src: …same…].` (source: same)
- U0.md A.U0.35 Change note: `… carries OR69 '4. a', OR69.a (3)(4)(8), …, OR68.a (2) and OR77/OR79 (the off-subnet attempt, U26).` → `… cites no audit ID [src: …same…].` (source: same)
- U0.md A.U0.36 Change note: `… carries OR70.a (2) and OR71.a (4)(5).` → `… cites no audit ID [src: OR70.a (2) and OR71.a (4)(5)].` (source: same)
- U0.md A.U0.37 Change note: `… carries OR5.a (2), OR12, …, OR49 and OR52.a (3).` → `… cites no audit ID [src: …same…].` (source: same)
- U0.md A.U0.38 Change note: `… carries OR5.a (3), OR18.a, …, OR4.a and OR87.a (b).` → `… cites no audit ID [src: …same…].` (source: same)
- U0.md A.U0.39 Change note: `… carries OR82/OR82.a, OR83.a and OR54.a (1)/OR78.a (L51's device scope).` → `… cites no audit ID [src: …same…].` (source: same)
- U0.md A.U0.40 Change note: `… carries OR82.a (L11, L62), OR24/HR165 (L01) and OR30.a (L10).` → `… cites no audit ID [src: …same…].` (source: same)
- U0.md A.U0.40 Change (SPEC:3452-3453 aside): `` (the later owner tag `6aed3c9` has no owner source, OR82.a — commit message) `` → `` (the later owner tag `6aed3c9` has no owner source; the commit message cites no audit ID [src: OR82.a]) `` (source: same)
- U0.md Open points: `the OR ID itself goes into the commit message, never the permanent text (OR68.a (4)).` → `` the OR ID itself goes into the action's `[src: …]` note, never into the permanent text or the commit message (OR68.a (4); AC_NOTES.md item 4). `` (source: AC_NOTES.md item 4)
- U0.md A.U0.34 Change (BACKLOG T4 text): `"… The A6 timing script below is its only copy, …"` → `"… The command-envelope timing script below is its only copy, …" [src: A6, the deleted hardware queue's label]` (source: the script's own docstring, BACKLOG.md:398; A6 comes from the queue deleted in `03f8bcf`)
- U0.md A.U0.33 Change (SPEC:4950): `"… re-decided with the key harmonization (owner, 2026-09-26)"` → `"… re-decided when the REST API's key names are harmonised to one scheme before the release (owner, 2026-09-26)" [src: OR58.a key harmonization, OR70.a (4)]` (source: OR58.a row, OR70.a (4) B06)
- U0.md A.U0.34 Change (BACKLOG:484-489): `"**`NTP_Host`'s 1024-character bound is re-decided with the key harmonization, together with …**"` → `"**… re-decided when the REST API's key names are harmonised to one scheme before the release, together with …**" [src: OR58.a key harmonization, OR70.a (4)]` (source: same)

Counts: U8 22 · U0 24 (19 commit-message notes, 1 commit-message aside, 1 Open-points convention, 3 labels the
earlier pass missed). 46 total.

### Flags (not changed)

- A.U8.19: the `loop.sync_wait_max_us` row's checker was an audit review (B2's L-BLOCK lens), which ends with the
  audit. The row now names ordinary code review. A-C should decide whether a standing check (a test) is owed.
- Actor tags without the standard form, no audit ID, so left: A.U8.01's Basis form `estimated (agent, <commit>)`,
  A.U8.06's `agent 2026-09-11 (`7cf989d`)`, A.U8.07's "legacy value kept (agent)" (no date).
- A.U0.29 appends to SPEC:485-486, which keeps "`cfgmgr` (WP2)". The WP label is U36's under G9/R12. Unlike A.U0.25's
  F11 note, A.U0.29 does not say so; A-C merges.
- A.U0.33's `[src: …]` still reads "names the retired labels this text replaces". It is kept verbatim as source.
  The commit message now names none of them.

### Unresolved

- None. The one inferred text is A.U8.15's second CI row "how" (see its entry).
