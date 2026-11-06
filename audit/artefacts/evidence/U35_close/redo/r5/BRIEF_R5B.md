# R5 unit B: level containment per scenario, and the sweep's records (lead, 2026-11-06)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `r5b_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then `S/u35r/r5/SWEEP.md`, FINDINGS
12.34 (`S/u35r/findings/FINDINGS.md`) and `S/u35r/r5/HANDBACK_R5C.md` (the silicon tests just added, and why they
declare no twin counterparts yet).

## Owner decisions behind this unit (2026-11-06, UTC, verbatim)
- 07:01, "Option A": level containment matches each scenario, and each CI-suite run cell, by its own id; coverage
  declarations and E.6.6 rows name scenarios, not families.
- 06:13, "B": the sweep's findings are fixed or recorded, then BACKLOG's sweep item comes out.

## Your work (worktree `S/wt-r5b`, branch `audit/r5b`, at int `54a769e1`; create it; commit locally, never push)
1. `tests_scripts/test_level_containment.py` identifies each host-harness scenario and each CI-suite run cell by its own
   id. Every `COVERS_TWIN_SCENARIOS` in `tests_hardware/flash` and `tests_hardware/bench` and every E.6.6 row
   (SPECIFICATION.md) names the scenarios or cells it really covers or excuses, read from what each test does (not
   carried over from its family). The silicon tests the last unit added declare theirs (its hand-back names them).
   The test itself grows by as little as it can; a new scenario then fails CI until it is mapped.
2. The sweep's finding 1: `flash/test_task_supervisor.py` claims the twin's Run 5, an SGP40 read fault recovered in
   place; it declares what it covers (a restarted task), and Run 5's cells go to the `bus-fault-injection` row.
3. The sweep's finding 5: the two dropped one-shot fires (the reset fire, the boot stagger fire) are named in their
   E.6.6 rows, each stating which silicon script proves which half.
4. The sweep's finding 7: one BACKLOG.md line owing the supervisor scan-budget measurement (`system.scan_budget`).
5. BACKLOG.md:29-44 (the sweep item) comes out: the account is in `tests_hardware/README.md`'s tier-parity section.
6. BACKLOG.md's bus-recovery item ("What SCL and SDA do on silicon during an I2C bus recovery"): the line levels are a
   limitation at F.5.1 now and the resets have a flash test, so it becomes a one-line owed first run of that test, or
   comes out if the README's owed list already carries it. `tests_hardware/README.md`'s "Open on silicon" FRAM CS row
   points at the FRAM section's limitation instead of an instrument.
7. `bench/test_reset_reasons.py::test_a_harness_hard_reset_reads_as_watchdog_without_a_record` expects ResetReason 2,
   but the harness's mpremote Ctrl-C ends the running firmware first, so the boot entry records `RR_INTERRUPTED` (21,
   `src/asy_system_service.py:93`) and the next boot reads 21 (`S/u35r/bench/HANDBACK_1320.md` shows 21 after harness
   resets). Confirm from the code path; if so, the test expects what the product does and its name says it.

## Never
No hardware: `tests_hardware` runs only with `--collect-only` or `--twin`. Never weaken a check; no skip. Never edit
`src/`, `ext/`, or `tests_hardware/flash/test_uart_crossover.py`, `tests_hardware/flash/test_watchdog_starvation.py` or
`tests_hardware/conftest.py` beyond their `COVERS_TWIN_SCENARIOS` line (another unit is fixing them); never read
`arduino/`; never open `/root/.claude/`.

## Rules for the text
Text outside `audit/` cites no audit IDs, unit names or finding numbers. A choice carries "(agent, 2026-11-06)" or
the owner ruling it follows. Comment-block and line rules as CLAUDE.md states them.

## Checks
`S/u35/lead/lint_direct.sh`; the three mypy passes; `tests_scripts/test_level_containment.py` seen failing first on an
unmapped scenario (a planted one, then removed); every changed `tests_hardware` file with `--collect-only`;
`tests_scripts` whole, once, under `S/u35/lead/heavy.lock` as common_r1 says.

## Limits
Write only `tests_scripts/test_level_containment.py`, the `tests_hardware` files above (declarations; the one test in
item 7), `tests_hardware/README.md`, SPECIFICATION.md (E.6.6 rows only) and BACKLOG.md. One commit. Budget about 1 % of
the week. Hand back by 11:30 UTC.

## Hand-back
`S/u35r/r5/HANDBACK_R5B.md`, at most 20 lines, and return its path: the id counts before and after (families, scenarios,
cells; declarations and rows touched), per item where it went, lines in and out, each check with its result. Last line:
"nothing of mine is running".
