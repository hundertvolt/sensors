W3a hand-back, written by the agent (Tue Nov 10 22:10:01 UTC 2026)
Read-only on S/wt-u35int at 51c9c75f: nothing run, built, committed or edited in any tree; no hardware. Outputs in
S/u35r/r5/W3A/ (N01.tsv, O4.tsv, LOAD.md, DNR.md); scratch in ftmp_w3a/ (two read-only lookup scripts, extracts).
## 1. N01 + N02 (N01.tsv)
- 73 rows: DONE 35, PLACED 13, TO PLACE 9, DROPPED 8, BENCH 7, OWNER 1. Outside the 73, the five rows whose state
  cell was never filled (OF-253/254/255/258/259): DONE 3, TO PLACE 2.
- N02 = DECREV 4's ninth place = OF-16: done in code (87c14760, SPEC:11950); open_findings.md:24 and REGISTER.md:243
  still read open: two record lines before the tag, one final-report line.
- 12 rows U24 closed at aa3530f7 (2026-10-14) still read "open" (the recovery's planned record correction never
  landed), so "73 open" overstated the open work; a third of the DONE rows are such record lags.
- Lead: OF-60/OF-70's manual pulls (tests_hardware/README.md:1322-1324) are in no step of the final relay (j).
  OF-193: FINDINGS 12.174 (W2's red on tc-int's stale binary) is evidence admitting a ~5-line `check` fix under
  PLAN 4.2 (a); else one BACKLOG line. OF-239 is OWNER: the `disallow_any_unimported` question the audit planned
  and never put (one site left). Nine TO PLACE lines are written out in N01.tsv, ID-free, for W3b or D.
## 2. O4 (O4.tsv)
- 64 credits on 62 lines: 2026-11-06 28, 11-07 10, 11-09 16, 11-10 10 (CS's 65: 11-07 -2 by cf5724ae, 11-10 +1 by
  W1b). Topics: rules of method 6, FRAM/logging synchronous 17, bounds 6, UART layout 2, reset sequence 1, test tiers
  5, E.6.6 allow-list 10, bench/flash design 14, website 1, Wi-Fi 1, /status streaming 1.
- Owner's eye first: SPEC:3187-3188, `verify_present()` removed (agent, 2026-11-09, 1547690d) against the owner's
  2026-09-26 "So they remain as they are." (do-not-reopen V14), without the 18:30:08 ask: restore or accept.
  tests/test_asy_webserver_service.py:1283 credits the agent where src/asy_webserver_service.py:815 credits the owner.
## 3. Load entries (LOAD.md)
- audit/b3/load.md never held cells (header only, 656fc82f): CLOSE_STATUS P07's premise does not hold. The cells
  are scratch-only: the LD lane's S/u35/laneB/ldcm3/full/load.md (52, 10-28) and R3's S/u35r/r3/d2/or49_load.md (13).
- LD 52: 43 right, 8 corrected, 1 still owed (a captive-DNS flood on silicon: justify or call it a gap). R3 13: 8
  right, 5 corrected. Nine lookups (eight names) gone or renamed. OR49.a (3) entries: 6 (LD's ledger held 1).
## 4. D's check (DNR.md)
- 271 rows: 244 present and current, 6 superseded (docs carry the later ruling), 5 moot, 1 contradicted (V14 above),
  11 not located by search (one reading before D), 4 not read (filtered rows A43, A47, B01, D03). The 221
  "correction owed" cells of 10-06 were not rechecked one by one.
## 5. The final report's draft
- The Write of W3A/REPORT_DRAFT.md was refused by the harness ("Subagents should return findings as text"). Not
  retried, as the Q35 lane's precedent; its full text (about 140 lines, <BENCH> and <D> placeholders) is in my final
  message for the lead to save.
## Decisions and slips (agent, 2026-11-10)
- Took the two scratch files as "the load cells" (git's has none); counted the unfilled rows apart from the 73;
  classed OF-239 OWNER as the audit's own plan put it.
- Slip: one git grep ran without the filter and printed a test function name holding a filtered word
  (tests/test_asy_wifi_service.py:2027's name); no secret value. Every other view was filtered.
nothing of mine is running
