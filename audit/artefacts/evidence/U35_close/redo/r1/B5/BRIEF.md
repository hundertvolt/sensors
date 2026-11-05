# B5 brief: network (lead, 2026-11-03)

Read first, in order: `S/u35r/r1/common_r1.md` (binding; its standing direction: target low complexity),
`S/u35r/r1/B5/ACTION_LIST.md` (your work list, with the lead's decisions at its end), PLAN.md sections 2 and 4 and its
B5 row (`S/u35r/plan/PLAN.md`, R1).

- Worktree `S/wt-b5`, branch `audit/r1-b5`, at `3129bf21` (B1, B2 and the plain-`err()` change merged). Run labels
  start with `b5_`. Hand-back: `S/u35r/r1/B5/HANDBACK.md`.
- You run beside B4 (`S/wt-b4`) and a lead gate. Never edit B4's files:
  the I2C, SPI, SCD30, SGP40 (with `voc_algorithm.py`), BMP3XX and ISL29125 files.
  In the three shared files (`buildgen/error_catalog.json`, the `/status` emitter in `buildgen/codegen.py`,
  `buildgen/definitions.py`) change only your own rows and keys; the lead merges. Every run goes through `run.sh`
  (its own network namespace).
- Wi-Fi is form only. Never print, copy or write the hotspot fallback literal or any Wi-Fi credential.
- One NTP item may be added while you work (the unsynced retry interval, on the owner's word): the lead sends it as a
  message; until then item 6 leaves the retry backoff alone.
- The catalog is read by the website: the gate adds `npm run lint`, `npm run typecheck` and `npm run test:unit`
  (`node_modules` is linked in the worktree).
- A caught `MemoryError` logs through a plain `err()` (`err_nomem()` is gone, owner 2026-11-03); level 0 prints
  nothing. `tests_hardware` only with `--collect-only` or `--twin`; nothing is skipped, disabled or deselected to get
  green.

Sources for each item are its basis column; read the part you need, not whole files. Before you remove, check each
"remove" item for proof that it is good (PLAN.md 0): one with such proof becomes a shrink item, said so in the
hand-back. A pre-audit or legacy function found lost or changed without a recorded reason goes to the lead.
