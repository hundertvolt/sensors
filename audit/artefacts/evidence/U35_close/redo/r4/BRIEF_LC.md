# R4 phase B, lane C: the other docs and the comments (lead, 2026-11-05)

## Read first, in order
1. `S/u35r/r1/common_r1.md` (binding; your labels start with `r4C_`).
2. `S/u35r/r4/ROWS.md`. Your lane is section 5's item 3.
3. Lane A's brief, `S/u35r/r4/BRIEF_LA.md`. Its rules, its heading map, its size stop and its report form bind you
   unchanged.

S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.

## Where you work
- **Worktree:** `S/wt-r4c`, branch `audit/r4c`, at `c78bbcf1`. Commit locally; never push.
- **Files you may write:**
  - `tests_hardware/README.md`, `digital_twin/README.md`, `DEVICE_REFERENCE.md`, `HEAP_FRAGMENTATION_MEASUREMENTS.md`,
    `PROJECT_AUDIT_PLAN.md`, `audit/REGISTER.md`;
  - `devices/wozi.toml`, `devices/dev.toml` (comment lines only);
  - `src/asy_uart_driver.py` (row 28's comment only; the bytecode must not change);
  - `tests/test_digital_twin_bus_hazard_concurrency.py`, and the test files of U36 004 and 513 (comments only);
  - `js/templates.js`, `html/style.css` (U36 507's comments only).
- **Files other lanes own:** SPECIFICATION.md, CLAUDE.md, README.md, BACKLOG.md and the UART changelog. Never touch
  them.

## Your rows
- **Rows 12, 13, 16 and 28.**
- **Row 11:** its comment and TOML sites. `devices/dev.toml:2` cites "CLAUDE.md's WoZi rule"; that rule is now
  "A device's result counts only from its own build on its own hardware" (CLAUDE.md, lane B).
- **U36 001:** tests_hardware/README.md's new "How a round runs".
- **U36 029 and 531:** DEVICE_REFERENCE.md's local time and commissioning.
- **U36 004, 507 and 513.**
- **Two findings from round 1's preparation:**
  - **FINDINGS 11.1:** tests_hardware/README.md's hotspot case (b) soak invocation selects case (b) alone, because the
    soak runner ANDs `-m role_reversal` with its `soak_duration` floor. Case (b) then fails without the module's
    earlier credential write. Give the invocation that works: the module whole, as the bench runner's `hotspot_b()`
    does (claude/u35-bench-campaign, `audit/artefacts/evidence/U35_close/redo/hw_round1/round1.sh`). Change no script.
  - **FINDINGS 11.2:** the manual runner's DUT-address prompt (`tests_hardware/manual/`) cites a README passage that
    does not exist. Make the README hold that passage, or name the one that does. Change the prompt text only if the
    README cannot serve.

## Checks and limits
- **Checks**, at most six runs:
  - the comment cap;
  - citations and decision vocabulary (expected allow-list shrinks listed, not fixed);
  - THR facts;
  - lint (`S/u35/lead/lint_direct.sh`);
  - for the two website files: `npm run lint` and `npm run typecheck`, with `node_modules` linked from `S/wt-base` and
    the link removed before you hand back;
  - for `src/asy_uart_driver.py`: show that its frozen bytecode is unchanged.
- **Size:** about +50/−75 in all.
- **Budget:** about 0.7 % of the week.

## Report
At most 25 lines. The last line is "nothing of mine is running".
