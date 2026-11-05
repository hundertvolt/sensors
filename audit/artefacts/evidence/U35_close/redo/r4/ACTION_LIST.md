# R4 action list (lead)

1. 2026-11-05: phase A briefed (BRIEF_A.md) on S/wt-r4 (audit/r4 at c78bbcf1), read-only, in parallel with round 1's
   runner (owner's parallel-work rule: independent, no shared files).
2. Phase A read (ROWS.md): net about -711 lines; adds 2, both demanded by owner rows (OR15.a (1) check, OR10.a (1)
   skill). Lead's decisions: no owner round now. Rows 6, 7, 8, 11, 14, 15 and the 12 rule proposals with owner rows
   are decided topics: written, wording shown in the R4 report. 528, 536, 539 (no owner row) not adopted, listed
   for the owner. 002 is no meaning change (list becomes a pointer to A.7). F.3 crossings wait on round 1. U36 532
   renumbering, 514/532/537 test halves not taken. 524's chroot recipe moves to README in lane B (CLAUDE.md shrinks,
   no cross-lane edit). Two writing units at once (PLAN 4.3): lane A now beside the bench runner; B after the
   runner; C after A or B.
3. Lane A briefed (BRIEF_LA.md), S/wt-r4a (audit/r4a at c78bbcf1).
4. Lane B briefed (BRIEF_LB.md), S/wt-r4b (audit/r4b at c78bbcf1); a rule ledger LEDGER_B.md (no rule may vanish).
   Lane C waits for A or B; it also takes FINDINGS 11.1/11.2 (the hotspot soak invocation, the manual prompt's
   missing README passage).
5. Lane A back at its 2 % share, partly done: 4 commits to 34ae00a3, SPEC +487/-430 (I.6 move 134 in/out), skill +21,
   Part 0 92 lines. Checks: 783 pass, 2 expected allow-list shrinks (20 citation, 5 vocabulary entries). Read: the
   skill is a thin pointer, Part 0 is owner-row OR44.a; no self-inflicted mechanism. Owner list for the R4 report:
   G.3 "flag and discuss" kept (U36 540 (6) not taken); K.10/E.2.3 "(owner, 2026-09-25, paraphrase)"; L.6.6 line vs
   buildgen/validate.py:542 (FINDINGS 11.3); C-stack 25 vs bench depth 28; U36 543 vs the heading map. Lane A2
   (fresh agent) briefed for the remainder: row 1's history pass, row 22's two, 40 U36 SPEC actions; 1.5 %.
6. Budget: R4 will pass its 6 % forecast (phase A, A, A2, B, C, OR10.b's three fresh builds, gate, falsification).
7. Owner 06:51: OR10.b option (b), two runs; ask about a third when done. Runs start after lane A2 (Part K final).
8. Lane B back: f9b907f1 CLAUDE.md 1276 -> 1022 (+292/-546), 373f8f65 README +653/-377 (114 the moved chroot recipe,
   about 260 the OR15.a CLI reference) and test_tool_help.py +31/-9 (the check bites on a removed row and an extra
   option), 5386fcb9 BACKLOG +15/-23, UCL +4/-4. Over the estimates; the agent did not stop at the half-overrun mark
   (a slip, recorded). Lead read: ledger 40 kept, 38 rewritten, 8 pointed, 0 vanished; spot-check of the hard rules
   (go-ahead, dead-man, br0 MAC, FRAM, credentials, loop blocking, gc, _boot.py, vendoring, wear, uv.lock, hazard)
   all present. Kept as is: CLAUDE.md accounts with no SPEC home (no further moves: churn). Owner list for the R4
   report: the hazard rule's "either variant" -> "on any device" (a fact update, six devices); the bird's-eye scan's
   "D.1 flag-first" vs the change-classes rule; U36 034 contradicted by the code (code written). Open owner directive:
   disallow_any_explicit (2026-09-28 "do it in this audit") not done (FINDINGS 11.4, R5). Follow-ups: SPEC:1614 and
   the front matter's pre-push pointer (to A2); devices/dev.toml:2 (lane C); Further reading's skill line (lead).
9. Lane C next (S/wt-r4c, audit/r4c at c78bbcf1).
   Lane C briefed (BRIEF_LC.md), 0.7 %; FINDINGS 11.1/11.2 and dev.toml:2 included.
10. Lane A2 back: 34e9b19a, e6b293e4, 6e006a95 (+238/-327); SPEC net -32 from c78bbcf1. Row 22 done, the lead's
    pointer done, 18 U36 actions done or met. Left (lane A3, after lane C): about -250 history (B.10.1, B.14.2.1,
    B.14.4, C.7's "Confirmed" blocks) and U36 500, 501, 503-510, 514, 515, 517, 537 (Part H/L/M checklist). Listed for
    the owner or lead: 022, 044, 512 (new headings off the map: not taken, low complexity); 521 (heading removal,
    BACKLOG); 046 (re-derive the F.2 rung tests). Drifted: 519 (version bump stays "a deferral"), 036 (the owner's
    .frozen-first rule kept), 012 (false claim not written).
11. OR10.b prep agent next (Part K final at 6e006a95): two history-free stripped trees and two one-page briefs.
    OR10.b prep briefed (BRIEF_P10.md), 0.8 %; two writing units now (lane C, prep).
12. Lane C back: 940edaa4 (16 files, +87/-36): rows 11 (sites), 12, 13, 16, 28 (bytecode identical), U36 001, 004,
    507, 513, 029, 531; FINDINGS 11.1 and 11.2 done (README only, no script). Checks pass (one expected citation
    shrink). Left: tests/test_asy_notification_service.py:53's C.14.2 pointer (lead at merge). Touches devices/dev.toml
    line 2 only (the ring change touches lines 52-66: no conflict).
13. Owner 09:09: 51 %; parallel work allowed per PLAN 4.3. Lane A3 briefed (BRIEF_LA3.md), 1.2 %, S/wt-r4a at
    6e006a95; Part K/K.0/Part 0/skill frozen for the OR10.b runs. Writing units: OR10.b prep and A3. Lead merges lanes
    B and C into int meanwhile (read each diff first).
14. Lanes B and C read and merged into int: d05aa3d1 (B), 3b9d7218 (C); no conflict with the ring commit. Lane C's
    diff: comments and doc lines only (wozi.toml header now names its legacy source, verified present). R5's closure
    inventory started read-only in a free slot (S/u35r/r5/BRIEF_INV.md, 0.7 %), against int 3b9d7218. Slots now: OR10.b
    prep and A3 writing, the inventory read-only.
15. R5 inventory back (S/u35r/r5/INVENTORY.md, 172 lines): OR5.a 85 rows (F 21, R 15, D 36, O 7, N 6; 40 wait on
    round 1), OR11 12 rows. Lead fixes on int: 70655a2a (C.14.3 pointer), f6846c10 (BACKLOG's ring item states
    dev.toml's 8,192 B responder ring; the settings line names `_VAL_DEBUG_LEVEL`). Not a defect: UCL B20's old wrnno
    numbers (B33 records the renumbering; a changelog keeps each entry as made). Found: R4 row 1's marker grep missed
    tests_hardware/README.md's "Third pass" to "Tenth pass" (1388-1990, about 600 lines of audit-pass narrative) and
    "Known assumptions and open findings" (1088-1388) needs the same read. Lane C2 (THR history pass, facts and rules
    kept, open findings left for R5) when a writing slot frees.
16. Lane A3 back: 85cbe951, 5b16a9ab, 59d91860 (+187/-205); SPEC net -50 from c78bbcf1. Row 1's named places only
    -39: the rest is live mechanism (accepted; no cut of facts). U36 500 (part), 501, 503 (2), 504, 505, 506 (2),
    507, 508 (part), 510 (2), 514/515/537 doc halves; 509, 517 met. Lead checked: H.4's timeout reason (client timer
    starts before connect, js/poll-manager.js:76-77; server cap after accept: true); M.1.1 item 16 aligned to C.4.2's
    later owner rule with the replaced words quoted (owner list for the R4 report, with 503's paraphrase). Checks
    783 pass, 2 expected allow-list shrinks. Merged: int 3ca3d25d. README's skill line: lead commit on int.
    Lane C2's worktree S/wt-r4c2 (audit/r4c2) cut from int's head.
17. Lane C2 briefed (BRIEF_LC2.md), 0.8 %, S/wt-r4c2 at 74c7b21b. Writing units: OR10.b prep and C2.
18. Lane C2 back: 54def63f, THR 2112 -> 1704 (+365/-773), BACKLOG :36/:140 citing words; sections recast as topics
    (Sensor/FRAM/supervisor coverage, Network-robustness tests, Harness mechanisms, Bus-hazard coverage, Tier parity);
    drifted plain facts restated as the tree has them; owner list: the bus-hazard parity rule's "(project owner)"
    lacks a date, the reset/assert/reset policy has no actor. Merged: int 339b9f5d; lead 1b73daef (the source-filter
    test's pointer). Allow-lists pruned once: 837697e9 (66 citations, 24 vocabulary).
19. R4 gate started on int 837697e9 (r4L_gate: lint, mypy, test.sh -1 and 32768, twin dev both stages, npm). R4
    falsification briefed (FALSIFY_BRIEF.md), read-only on S/wt-r4f at 837697e9, 1 %. Base for R4's diff: 33974760.
20. First gate run invalid (lead's error: /root/pico-toolchain and scripts/typecheck.sh instead of S/tc-int and the
    direct mypy passes): setup tried a network fetch; nothing changed. Corrected script u35/lead/gate_r4.sh.
21. Falsification back (FALSIFY.md): 3 stand (6, 9, 10), 7 refuted. Fix round on int: 088951f6 (the CLI check leaves
    the synopsis line out; planted --coverage row deletion now fails, r4fx_plant), 932510fc (B.13's recovery script
    restored to the validated "Wired connection 1" lines; owner tags: THR FRAM CS "measured on the bench", M.3
    "owner-confirmed", CLAUDE.md's precedent unquoted; SPEC stall row :692-703/:702-710; history residue at SPEC
    E.5.3/B.7/CI/M.1.1, THR hotspot join (open finding moved into "Open on silicon"), THR first-cut note, Tier parity
    intro, README chroot gap; C.8 names the sweep script; L's "per-driver" -> "one checklist"; PAP's THR cite).
    Doc checks 723 passed (r4fx_help2). Owner list (R4 report): CLAUDE.md's exception precedent now "never reaches the
    legacy tree" (old: it extended to the legacy microdot/_boot rules; later owner rule 2026-09-11); C-side testing
    "post-audit" (old: "testable now"; OR5.a); WoZi rule dropped "dev's firmware covers the shared SCD30/SGP40 bus"
    (OR140.a (18)). Stated limit, not fixed: a shell tool's parser accepting an option its --help omits is outside the
    README-vs-help check. Not a defect: claim 8's wording (test_tool_help.py's new test is code by design).
