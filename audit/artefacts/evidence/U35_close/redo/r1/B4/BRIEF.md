# B4 brief: buses and sensors (lead, 2026-11-03)

Read first, in order: `S/u35r/r1/common_r1.md` (binding; its standing direction: target low complexity),
`S/u35r/r1/B4/ACTION_LIST.md` (your work list, with the lead's decisions at its end), PLAN.md sections 2 and 4 and its
B4 row (`S/u35r/plan/PLAN.md`, R1).

- Worktree `S/wt-b4`, branch `audit/r1-b4`, at `3129bf21` (B1, B2 and the plain-`err()` change merged). Run labels
  start with `b4_`. Hand-back: `S/u35r/r1/B4/HANDBACK.md`.
- You run beside B5 (`S/wt-b5`) and a lead gate. Never edit B5's files:
  the Wi-Fi, NTP, DNS, captive DNS, UDP socket and web server files.
  In the three shared files (`buildgen/error_catalog.json`, the `/status` emitter in `buildgen/codegen.py`,
  `buildgen/definitions.py`) change only your own rows and keys; the lead merges. Every run goes through `run.sh`
  (its own network namespace).
- `SPI.available` and the FRAM driver's readers of it are B3's: leave them. The reader timer trio in
  `asy_base_classes.py` is yours (item 18); touch nothing else of that file.
- The catalog is read by the website: the gate adds `npm run lint`, `npm run typecheck` and `npm run test:unit`
  (`node_modules` is linked in the worktree).
- A caught `MemoryError` logs through a plain `err()` (`err_nomem()` is gone, owner 2026-11-03); level 0 prints
  nothing. `tests_hardware` only with `--collect-only` or `--twin`; nothing is skipped, disabled or deselected to get
  green.

Sources for each item are its basis column; read the part you need, not whole files. Before you remove, check each
"remove" item for proof that it is good (PLAN.md 0): one with such proof becomes a shrink item, said so in the
hand-back. A pre-audit or legacy function found lost or changed without a recorded reason goes to the lead.
