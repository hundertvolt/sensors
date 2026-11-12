# B3 brief: storage (lead, 2026-11-03)

Read first, in order: `S/u35r/r1/common_r1.md` (binding; its standing direction: target low complexity),
`S/u35r/r1/B3/ACTION_LIST.md` (your work list, with the lead's decisions at its end), PLAN.md sections 2 and 4 and its
B3 row (`S/u35r/plan/PLAN.md`, R1), and CLAUDE.md's FRAM rule (read FRAM-backed logs before clearing them, in the twin
too).

- Worktree `S/wt-b3`, branch `audit/r1-b3`, at the integration head (B1, B2, B4 and B5 merged). Run labels start with
  `b3_`. Hand-back: `S/u35r/r1/B3/HANDBACK.md`.
- You run beside B6 (`S/wt-b6`). Never edit B6's files: the UART driver, comm, link driver, framing codecs,
  `PieceBuffer` and their tests, `UART_C_PORT_CHANGELOG.md`. In the three shared files (`buildgen/error_catalog.json`,
  the `/status` emitter in `buildgen/codegen.py`, `buildgen/definitions.py`) change only your own rows and keys; the
  lead merges. Rows 4 and 19 edit `asy_system_service.py`: only the lines they name. Every run goes through `run.sh`.
- Row 7's clock: the datasheets are in the main checkout's submodule (`/home/user/sensors/datasheets/`), read-only.
- The catalog is read by the website: the gate adds `npm run lint`, `npm run typecheck` and `npm run test:unit`
  (`node_modules` is linked in the worktree). A caught `MemoryError` logs through a plain `err()`; level 0 prints
  nothing. `tests_hardware` only with `--collect-only` or `--twin`; nothing is skipped, disabled or deselected.

Sources for each item are its basis column; read the part you need, not whole files. Before you remove, check each
"remove" item for proof that it is good (PLAN.md 0): one with such proof becomes a shrink item, said so in the
hand-back. A pre-audit or legacy function found lost or changed without a recorded reason goes to the lead.
