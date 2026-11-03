# B1 brief: logging and catalog (lead, 2026-11-02)

Read first, in order: `S/u35r/r1/common_r1.md` (binding), `S/u35r/r1/B1/ACTION_LIST.md` (your work list), PLAN.md
sections 2 and 4 and its B1 row (`S/u35r/plan/PLAN.md`, R1).

- Worktree `S/wt-b1`, branch `audit/r1-b1`, at the integration head `4516e60e`. Run labels start with `b1_`.
- Hand-back: `S/u35r/r1/B1/HANDBACK.md`.
- You run alone: B1 touches 18 of the 28 modules. The UART protocol's wire format must not change; a logging change in
  the UART modules gets one `UART_C_PORT_CHANGELOG.md` entry, Class B (no C impact).

Sources for the items (read the part you need, not whole files):
- Item 1: `S/u35r/scan2/G4.md` 1.1 (S2-G4-1, S2-G4-2: the AST count of the 123 calls, which 118 end in `_line()`, the
  explicit sites); `S/u35r/r0/R0_CHECKS.md` item 3 (the logger-side form holds at a near-exhausted C stack, sync and
  async; `S/u35r/r0/cstack/cstack_check.py` is the probe). The owner's words: the review "ok" in
  `audit/review/answers.json` (`c-stack-reboot`), "The OK in the review stay valid." (2026-10-28).
- Item 2: the rulings file, 2026-11-02 20:53 and 20:58 (the decision and its blast radius as agreed: about 45 lines in
  11 `src/` files, the optional logger silent by default, the 12 logger-owning sites calling their own logger).
  `S/u35r/scan2/G4.md` 1.4 (S2-G4-6) lists the sites and what `console()` was for; CLAUDE.md's memory rule (the gates
  read printed text; the unit tests that can run out of memory run at level 1, owner "Option 1 is good", 2026-10-20).
- Items 3-6: `S/u35r/scan2/G4.md` 1.6 (S2-G4-8), `S/u35r/scan2/G4b.md`:264, the closure rows of `asy_print_log.py` in
  `S/u35r/scan2/G4_closure.tsv` and `G4b_closure.tsv` (roots A-P2, A-P3, A-P5, A-P7, A-P10, A-P11).
- Item 7: `buildgen/error_catalog.json`, `tests_scripts/test_error_catalog.py`, decision 6 (PLAN.md 6).

Before you start removing, check each "remove" item for proof that it is good (PLAN.md 0, "Nothing proven good goes": an
observed or reproduced failure it fixes, a measured gain, or an owner approval). One with such proof becomes a shrink
item: say so in the hand-back. A pre-audit function found lost or changed without a recorded reason goes to the lead.
