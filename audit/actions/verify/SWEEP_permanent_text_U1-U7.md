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
