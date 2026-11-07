# B7 brief: LED (lead, 2026-11-03)

Read first, in order: `S/u35r/r1/common_r1.md` (binding; its standing direction: target low complexity),
`S/u35r/r1/B7/ACTION_LIST.md` (your work list, with the lead's decisions at its end), PLAN.md sections 2 and 4 and its
B7 row (`S/u35r/plan/PLAN.md`, R1), and CLAUDE.md's FRAM rule (read FRAM-backed logs before clearing them, in the twin
too).

- Worktree `S/wt-b7`, branch `audit/r1-b7`, at the integration head d6bc7617 (B1-B6 merged). Run labels start with
  `b7_`. Hand-back: `S/u35r/r1/B7/HANDBACK.md`.
- You run alone; a read-only agent drafts B8's list beside you. In the three shared files
  (`buildgen/error_catalog.json`, the `/status` emitter in `buildgen/codegen.py`, `buildgen/definitions.py`) change only
  your own rows and keys (W67, `NotifyState`, the `State` key and row); everything else in `buildgen/` is B8's.
- Item 7 waits for the owner: do every other item first. The lead sends the answer by message; if none has come when
  the rest is done and green, hand back with item 7 open and say so. Do not ask the owner yourself.
- The catalog and definitions are read by the website: the gate adds `npm run lint`, `npm run typecheck` and
  `npm run test:unit` (`node_modules` is linked in the worktree). A caught `MemoryError` logs through a plain `err()`;
  level 0 prints nothing. `tests_hardware` only with `--collect-only` or `--twin`; nothing is skipped, disabled or
  deselected. The gate runs once, only after the lead's message that the host is free.

Sources for each item are its basis column; read the part you need, not whole files. Before you remove, check each
"remove" item for proof that it is good (PLAN.md 0): one with such proof becomes a shrink item, said so in the
hand-back. A pre-audit or legacy function found lost or changed without a recorded reason goes to the lead.
