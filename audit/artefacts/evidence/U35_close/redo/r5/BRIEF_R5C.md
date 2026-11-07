# R5 unit C: the silicon tests the owner chose, and the heater-off tick (lead, 2026-11-06)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `r5c_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then `S/u35r/r5/SWEEP.md` (the
sweep; its findings carry file:line) and FINDINGS 12.33 and 12.34 (`S/u35r/findings/FINDINGS.md`): 12.34 rejects the
sweep's finding 2, so it is not yours. CLAUDE.md's wear rules and its FRAM-log rule bind every test you write;
`tests_hardware/README.md` is the reference for markers, budgets and device scripts.

## Owner decisions behind this unit (2026-11-06, UTC)
- 06:43, "Option A, I have no oscilloscope at hand": no scope checks; one device script holds SDA, resets the board
  by `machine.reset()` and by a starved watchdog, and the next boot's bus answers.
- 06:59, "Option A": the read-trigger spacing test gets a short fixed window in the standard bench run.
- 06:13, "B": the sweep's findings are fixed or recorded.

## Your work (worktree `S/wt-r5c`, branch `audit/r5c`, at int `f509c906`; create it; commit locally, never push)
1. **Held SDA through a reset** (BACKLOG.md:198's reset half): one device script, reusing how
   `i2c_held_sda_recovery.py` makes the held SDA, two modes (`machine.reset()`; a starved watchdog), and one flash
   test that reads, after the reboot, that every I2C device answers and the reset is attributed. Zero wear.
2. **Sweep finding 3:** ResetErrors refused after a reset decision: the assertion and the bench test SWEEP.md names;
   the errcount is read and saved before any ResetErrors call, as CLAUDE.md requires.
3. **Sweep finding 4:** the escalation entry that never finishes: the one parametrisation SWEEP.md names (code 20,
   the TIMER bit).
4. **Sweep finding 6:** ConfigFaults on silicon: one flash test over a scratch config file, behind
   `persistence_write` for its one repair write.
5. **Sweep finding 8:** the boot signature's random fallback: the NTP-blocked boot held past `_NTP_WAIT_TIME`;
   BootSignature set, and two such boots differ.
6. **Trigger spacing:** `bench/test_boot_order_and_triggers.py::test_bus_triggers_keep_their_minimum_spacing` runs
   without `--soak-duration` over a fixed window of several full trigger cycles (about a minute), and keeps the
   named duration when the option is given.
7. **Heater-off:** `src/asy_sgp40_driver.py:754` waits `_HEATER_OFF_MAX_MS + 1` again, with the one-line reason
   (`asyncio.sleep_ms()` counts whole ticks, so it can end up to 1 ms early); SPECIFICATION.md M.3 already states it.
8. Each new test declares its twin counterparts as the existing ones do (family ids today; a later unit converts all
   of them to per-scenario ids). `tests_hardware/README.md`'s "Tier parity beyond the bus hazards" gets the sweep's
   account for this domain, at most 8 lines.

## Never
No hardware: `tests_hardware` runs only with `--collect-only` or `--twin`. No new marker, budget or fixture where an
existing one serves. Never edit `ext/`, `arduino/` or SPECIFICATION.md's E.6.6 table (another unit owns it); never
read `arduino/`; never open `/root/.claude/`.

## Rules for the text
Text outside `audit/` cites no audit IDs, unit names or finding numbers. A choice carries "(agent, 2026-11-06)" or
the owner ruling it follows; a fact its source. Comment-block and line rules as CLAUDE.md states them.

## Checks
`S/u35/lead/lint_direct.sh`; the three mypy passes; `tests/test_asy_sgp40_driver.py` at both GC stages; every changed
`tests_hardware` file with `--collect-only`, and with `--twin` where it runs there; `tests_scripts` whole, once, under
`S/u35/lead/heavy.lock` as common_r1 says (another unit may hold it: wait, never two heavy runs at once).

## Limits
Write only `tests_hardware/` (tests, device scripts, README) and the one line in `src/asy_sgp40_driver.py`. One commit.
Budget about 1.5 % of the week; at 80 % of it stop at a clean commit and report. Hand back by 10:30 UTC.

## Hand-back
`S/u35r/r5/HANDBACK_R5C.md`, at most 25 lines, and return its path: per item where it went (file:line) and what the
bench must run to see it, lines in and out, each check with its result. Last line: "nothing of mine is running".
