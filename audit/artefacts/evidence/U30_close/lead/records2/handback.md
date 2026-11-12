U30 records2 FINAL (saved by the lead from the delivered message, 2026-10-20)
Commit 9e3819c on audit/u30-rec2 (S/wt-u30rec2, on fef34d0). Only audit/REGISTER.md (+12 rows, 8 edited) and audit/sweeps/open_findings.md.
1. REGISTER:735 new U30 CI row: run 39394914980 on 5ba138c, 46/46 green (re-checked via gh api).
2. :778 (SF-A12), :795 (SF-M3-06): closed (U30, lane X2 c12668a), stating SPEC I.4(e) :8609-8633.
3. OF-215 (open_findings:223): V2's landing with sites (_twin_process.py:170-184, :366-378, _digital_twin_scenarios.py:263, Part N :11722-11723), hang not reproduced; stage 3 to U31 (next unit holding runner and harness); _twin_process.py next held at U35; runner has --stop-file (:238). Partly closed.
4. New rows :730 (M+M2), :731 (V2/V3/V4), :732 (C's class-5 early first read, kept, no OF); :727 updated (OF-215 to U31, 2 new OFs, fixes list).
5. :725 time growth: V's Run 12 (12.5-14.8 -> 20.2-23.6 s, +54-64 %), V2's errcount +24 %, V3's shell test from its record (0.47/0.59 -> 0.98/0.80 s: +108 %/+36 %, not the brief's +70-100 %), M/M2 within 4 %/4.4 %.
6. :734 pointer row to audit/artefacts/evidence/U30_close/lane_<L>/handback.md (15 lanes).
7. :724 residual routed to U37 (no later unit holds src/asy_print_log.py; U27's fallback rule; its test next at U35); new OF-220 (open_findings:228); OF-145's pointer names OF-220.
8. :723 lists the 14 files pairs2 paired; neopixel_wifi re-pair not taken; time-only (py/gc.c:574-582, :620-639), layout.py: lay_A/lay_B differ only in heap base address.
9. :733 twin record 7ab7dd2 (only dates 121, runner 121, api 50, c_stack_budget own hash).
10. :728 working-economy direction row (question + four answers verbatim from CLAUDE.md bf21d9e).
Beyond the brief (agent, 2026-10-20): :729 records "Option 1 is good" with the lead's question (paraphrase), plus V's and X2's halves.
PENDING-LEAD: REGISTER:56 unit row; gate line; tier line; U30 CI line.
Checks: 16 scans 837 passed rc 0 68 s, zero markers (log S/u30/rec2/scans16.log). Nothing running.
