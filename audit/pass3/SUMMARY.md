# Pass 3 — the question-raising scans (2026-09-29, HEAD `c6561e5`)

Ten read-only scans (brief `audit/sweeps/pass3_prompt.md`), one file each in this directory.

| Scan | Input | Verdicts |
|---|---|---|
| D1 | 82 defect candidates, G1-G2 | COVERED 41, DEFECT 28 (all test-side, authorised by OR12/OR19.a/OR21.a → register), NOT-DEFECT 10, FIXED 3 |
| D2 | 34 defect candidates, G3-G5 (+8 Truth lines, 3 conflicts) | COVERED 28, NOT-DEFECT 13, DEFECT 3 (one question), UNPROVABLE-HERE 1 (FRAM CS power-up, phase C) |
| D3 | 73 items, G6-G10 | COVERED 43, NOT-DEFECT 28, DEFECT 1, UNPROVABLE-HERE 1 (grkizi Run 5c SIGSEGV, twin runs) |
| D4 | 324 plan seeds, 339 topics | seeds: COVERED 277, NOT-DEFECT 26, DEFECT 8, UNPROVABLE-HERE 4; topics: COVERED 2, UNPROVABLE-HERE 2 |
| N | Appendix B + delta (76) | SETTLED 33, KEEP 18, DO 14, ADAPT 8, RETIRE-CANDIDATE 3 |
| O | 228 open, stale and deferred items | mostly COVERED/SETTLED/RESOLVED; TRIGGER-MET 3 (`ext/` on mypy path, upstream poll report, `test_device_tomls.py` collision check) |
| C1 | S03/S04/S07 gaps | NEW 6, KNOWN+ 7, KNOWN 7, rejected 16 |
| C2 | S10/S12 gaps | NEW 5, KNOWN+ 11 |
| H1 | multi-commit drift | DRIFT 16, REASON-SWAPPED 2, KNOWN/HOLDS aggregates |
| H2 | 112 untraced owner-decision commits | KNOWN 29, NO-DECISION 26, HOLDS 19, OVERTAKEN 15, MISATTRIBUTED 11, LOST 6, DRIFTED 1 |

## Proposed questions settled by the lead without asking (OR51.a (3), OR68.a (2))

- D4 Q2 (reset timer backstop): owner, 2026-07-18 (`af24a01`): `reboot_system()`/`reboot_bootloader()`
  "left as-is by owner's explicit choice" ("brittle wrt. wdt timeout settings"). Stays; G5/R08's
  wrong "watchdog backstops it" reason is corrected (D3 extra).
- D4 Q4 (boot-time I2C bus clear): option (a), fact in SPEC F.2 and a phase-C row; a bus clear is
  foreclosed by harmonization 38 (OR64.a) and CLAUDE.md's wedged-bus rule.
- O Q1 (UART peer-sized allocations): stays deferred, owner 2026-09-26 (OR69.a (7)).
- D3 Q1 = D4 Q8 (NTP `Synced`), N Q1 = O Q2 (upstream poll report): merged.
- D4 Q6 (SCD30 offset rounding) folded into the defect-approval question.

## Owner questions (asked 2026-09-29)

1. Approve twelve proven bug fixes (D4 Q1 + D4 Q6).
2. SGP40 backup verification off for long periods (D2 Q1).
3. NTP settings change clears `Synced`, as legacy (D3 Q1, D4 Q8, G6/R30).
4. Echoed password mask: refuse or store (D3 Q2, G6/R29).
5. LED command while a signal runs (D4 Q5).
6. Boot-phase crash: record a `reset_reason` code (D4 Q3).
7. Captive DNS non-A queries (D4 Q7, NET.S12).
8. Wi-Fi uptime counted while the hotspot runs (D4 Q7, NET.S15).
9. BACKLOG 30 reset: closed, reopened or detected (H2 Q1).
10. Unix-port poll bug: who reports it upstream (N Q1, O Q2).

Register lines from all ten files are integrated after the answers, in one pass.
