# B2 falsification brief (lead, 2026-11-03)

Your job: try to REFUTE the claims below about commit `8019a9ef` (base `93224dab`, pre-audit `25caf528`, where the
core files were named `base_classes.py`, `system_service.py`, `config_manager.py`, `api_response.py`). You get the
claims, not the reasoning behind them. A claim stands only if you could not break it; say how hard you tried. Also look
for a lost feature or a reintroduced real defect in these files against the pre-audit code.

- Read-only worktree `S/wt-b2f` (detached at `8019a9ef`); S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.
  You may plant a temporary break there to test a claim, then restore it (`git -C S/wt-b2f checkout -- <path>`).
  Never commit, never push, never touch any other worktree.
- `S/u35r/r1/common_r1.md` gives the environment, the run wrapper (`S/u35/lead/run.sh`, labels `b2f_`), the one-file
  test commands and `S/u23/rebuild.sh <worktree>` (run it once before any test file). Its binding rules apply. No whole
  gate: single test files only, at most ten runs in all. Never open anything under `/root/.claude/`. Never read
  `arduino/` (`':!arduino'` in every git grep and git log). `tests_hardware` only with `--collect-only` or `--twin`.
- The legacy tree (`python/`, `modules/`) is reference-only: read it, never run or change it.

## Claims
1. Reset codes: the reboot command records 3, a config reset 7, an FRAM erase 8, an incomplete command 9, and the
   bootloader command 9; only the bootloader command calls `machine.bootloader()`, the others `machine.reset()`. Nothing
   writes, decodes or expects code 4 (firmware, catalog, website, `tests/`, `tests_hardware/`, the twin).
2. `ResetBits` and `ConfigUnpersisted` are gone from every generated device's `/status`, the website definitions and
   pages, `mockdata/` and `js/`; nothing in `src/` reads the chip's reset registers. `ResetReason` still reads the
   recorded reason, and the shutdown flush still reports a store whose last write failed. No `tests_hardware` test was
   skipped, disabled or deselected for this.
3. `wet_bulb_temperature()` answers a finite value at every point of -20..50 degC by 5..99 %RH and None outside it.
   `rel_humidity()` answers exactly what `25caf528:src/math_helpers.py` answers, for every input.
4. Config store: an absent file logs one persisted W22 per store per boot, and its defaults are written once; an
   unreadable file logs W22 and is never overwritten; a schema that stores no values logs nothing persisted for a
   missing file. A fresh dev boot (empty config dir) persists exactly one W22 per value-storing store and nothing else.
5. Nothing in `src/`, the generated modules, the website or the tests reads W69, `absent_at_boot` or `restored`.
6. With the uptime tick timer refused at boot, nothing reboots for it and `SysUptime` reads right on every read; what
   stops is exactly this: the boot signature stays unresolved and the mempause auto-unpause does not run.
7. The supervisor's escalation records its reset code (5, or 20 for a C-stack overflow) before its entry write; if that
   write never ends, the watchdog's reset reads that code, not 2.
8. A chip-setup failure in BMP3XX, ISL29125, SCD30 or SGP40 runs no bus recovery: its task ends, the supervisor
   restarts it, the budget's reboot follows a persistent failure. A read failure's recovery ladder is unchanged.
9. With `_read_failing`, `_timer_reported` and `quiet=` gone, a repeated failure prints every time and persists into
   one FRAM slot (the logger's newest-entry rule); no run of repeats uses more slots than before.
10. No product caller reads any `setup()`'s return value. The system command's shutdown sequence still runs to its
    end with no reference kept to its task.
11. The only reply of `asy_api_response.py` that differs from `25caf528:src/api_response.py` is a raising post-write
    hook (then ERR code 100; now OK, the group's fields "Failed"); codes 2-5 had no product producer at `25caf528`.
12. No product check got weaker: every test change is the mechanical consequence of an item above. Look hardest at
    the storm bound in `scripts/_digital_twin_scenarios.py`, `_check_quiet_boot` in `scripts/_digital_twin_ci_suite.py`,
    the four FRAM-layout scenarios in `tests/_sensortask_scenarios.py`, and every removed test.
13. Numbers: `src/` bytecode 205,832 B at `8019a9ef` (-1,323 B against `93224dab`), no module grew
    (`S/u35r/r0/module_sizes.sh`); dev's `imageFreeBytes` 46,468 B.

## Hand-back
Write `S/u35r/r1/B2/FALSIFY.md`, first line "B2 falsification, written by the agent (<date -u>)": per claim STANDS or
REFUTED, with file:line evidence (and the planted break or run label where you used one). Then any defect you found
outside the claims. Your final message: the path, one line per REFUTED claim, last "nothing of mine is running".
