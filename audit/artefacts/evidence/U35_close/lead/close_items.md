# U35 close: items the records and the owner report must carry (lead, 2026-10-22)

Sources: LEAD NOTES 86-104 in S/u35/lane_plan.md; hand-backs Z1, M1, O1, J1, D2d, D2e, SCREEN_review.

## REGISTER rows (audit/REGISTER.md, U35)
1. The owner's least-wear requirement as a central hard rule (owner quote, 2026-10-22, the "least wear rule is even
   more important for the production code" words), where it landed (CLAUDE.md hard rule, SPEC D.3, CHECKLIST 24) and
   its two guards (tests_scripts/test_firmware_write_sites.py, tests_scripts/test_uart_link_bench_only.py).
2. The config-write decision (owner, 2026-10-22, 06:32 UTC quote, with the steps it approved) and the owner's
   findings agreed by the lead (LEAD NOTES 86); lane P's sibling-and-rename scheme reverted by block Z (`447ae0b`),
   the boot write's lock kept ("1. is good."); the three leftovers (`b025371`).
3. The pillar screening: the owner's concern and go-ahead quotes (LEAD NOTES 90-92), the three marks and their
   proofs, the result (the config write the one violation of its kind; SCD30 NVM sites unchanged), the reviewer's
   three "simpler forms" kept with reasons (LEAD NOTES 96).
4. The UART link exception (owner quote, LEAD NOTES 95) and its guard.
5. Block M kept whole under the owner's no-regression condition (LEAD NOTES 99); the gate's two tests inline
   (`5b05a53`, lead decision, LEAD NOTES 103).
6. Block O (`15da695`) and the hazard text's overwrite warning (`cd8f077`, lead decision under O3's scope).
7. D.3's exception for the SCD30 commands sent on every PUT (`4f44af1`, lead).
8. Events: D2d's unrecorded stop (LEAD NOTES 98); the container restart at about 09:45 UTC (LEAD NOTES 102).
9. The provenance rule for cleanups (owner quote, LEAD NOTES 97) and how each block met it.

## Open findings
- OF-225 closed as an accepted degradation with its consequences (owner's 06:32 decision; SPEC F.3's consumers cell).
- The U36 item for `_finish_write()` (D2b's (a), LEAD NOTES 83) withdrawn: the function is gone.
- New, to U36: `erase_ready()` answers True in the chip-loss window (LEAD NOTES 99).
- To U37: step 142's rows without an instrument (LEAD NOTES 104).

## Owner review
- Every agent decision taken on the owner's behalf in U35 re-read against CHECKLIST 24: any that touches a flash or
  NVM write is listed for the owner as a question, never as decided.
- The report says which cleanups were done (Z, O, J, the hazard text), stopped and kept (M's two parts, the
  exception-handler guard, `_shutdown_task`, the captive DNS MemoryError re-raise) and why.
