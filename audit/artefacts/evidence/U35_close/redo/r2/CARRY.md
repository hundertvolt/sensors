# R2 carry-ins (lead, 2026-11-04)

From B8 (`S/u35r/r1/B8/ACTION_LIST.md` decisions 8 and 12):
- `_UART_BUFFER_MAX`'s comment cites stale `machine_uart.c` line numbers (pinned 1.29.0: `:374-375`, `:389-390`).
- `SETTINGS_GROUPS` and `_owns_config_store()` have no reader left in `buildgen/validate.py`; with them, the removed
  settings-group guard: the kept test checks only `networking` and `system` (FALSIFY claim 11).
- `HardConsumer.what`/`.relief` (B8 row 20).
- rp2's REPL banner and "Type help()" print after the boot entry returns at a loop end, at every DebugLevel
  (`ports/rp2/main.c:246-259`, `shared/runtime/pyexec.c:626-631`). Pre-audit, port behaviour; judge it against
  "There must be a mode which is really silent on the console, ever. That's level 0." (owner, 2026-11-02).
