# B6 brief: UART (lead, 2026-11-03)

Read first, in order: `S/u35r/r1/common_r1.md` (binding; its standing direction: target low complexity),
`S/u35r/r1/B6/ACTION_LIST.md` (your work list, with the lead's decisions at its end), PLAN.md sections 2 and 4 and its
B6 row (`S/u35r/plan/PLAN.md`, R1), and CLAUDE.md's UART protocol rule.

- Worktree `S/wt-b6`, branch `audit/r1-b6`, at the integration head (B1, B2, B4 and B5 merged). Run labels start with
  `b6_`. Hand-back: `S/u35r/r1/B6/HANDBACK.md`.
- You run beside B3 (`S/wt-b3`). Never edit B3's files: the FRAM driver and manager, the SPI driver and their tests.
  In the three shared files (`buildgen/error_catalog.json`, the `/status` emitter in `buildgen/codegen.py`,
  `buildgen/definitions.py`) change only your own rows and keys; the lead merges. Every run goes through `run.sh`.
- The wire format, the accept/reject rules and the recovery timings stay as they are; every change gets its
  `UART_C_PORT_CHANGELOG.md` row (Class B unless it changes the wire, which nothing on your list does).
- Row 9 (W57) goes (the lead's decision at the list's end).
- The fix carried from `916fb878` is read with `git show` (branch `origin/claude/u35-bench-campaign`); take its code
  and tests, not its changelog number (B94 here).
- The catalog is read by the website: the gate adds `npm run lint`, `npm run typecheck` and `npm run test:unit`
  (`node_modules` is linked in the worktree). A caught `MemoryError` logs through a plain `err()`; level 0 prints
  nothing. `tests_hardware` only with `--collect-only` or `--twin`; nothing is skipped, disabled or deselected.

Sources for each item are its basis column; read the part you need, not whole files. Before you remove, check each
"remove" item for proof that it is good (PLAN.md 0): one with such proof becomes a shrink item, said so in the
hand-back. A pre-audit or legacy function found lost or changed without a recorded reason goes to the lead.
