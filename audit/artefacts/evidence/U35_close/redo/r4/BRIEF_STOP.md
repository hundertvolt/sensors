# Fix unit: twins end through their stop file, not SIGINT (lead, 2026-11-06)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `stop_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then `S/u35r/r4/HANDBACK_SIG.md`
and FINDINGS 12.32 (`S/u35r/findings/FINDINGS.md`, last entry): the cause, verified. Then `git show d0eb67f3` for
`scripts/`: what the removal of the launcher's stop file took out, and why.

## The cause, in short
A KeyboardInterrupt the Unix port raises asynchronously at an `async with` body's normal end comes out as
`AttributeError: 'NoneType' object has no attribute '__aexit__'` (a MicroPython defect, `py/emitbc.c:681-683` at
v1.29.0): the interrupt is lost and the twin serves on until it is killed. A thrown CancelledError is not exposed. The
runner's `--stop-file` ends serving in-band (`digital_twin/run_generic_integration.py:549`, `_serve_until`), so a twin
ended through it never meets the defect.

## Your work (worktree `S/wt-stop`, branch `audit/stop`, at int `f509c906`; create it; commit locally, never push)
1. `scripts/_twin_process.py`: `spawn()` gives every twin its stop file again; `shutdown()` ends a twin by creating
   it. A twin still running at the bound is described (`/proc` state, log tail) and killed, as today: no SIGINT
   fallback, no second attempt. SIGINT-first stays only for a caller that tests the SIGINT path on purpose (before
   d0eb67f3: the CI suite's Run 12 relaunch); find each such caller in today's tree and keep SIGINT for those alone.
2. The SIGINT-only instruments (`_second_sigint`, `_sigint_state`, the scenarios' `--test-kbd-traceback` arming and
   the runner flag behind it): keep what the remaining SIGINT path uses; remove what becomes dead, with its tests and
   doc rows.
3. A test, seen failing first on today's code: `shutdown()` ends a twin through its stop file and sends no signal.
   Prefer a structural one (a fake process that records signals; no twin launch).
4. Docs: where SPECIFICATION.md or `digital_twin/README.md` say SIGINT ends the twins, state the new truth. One short
   Part F fact beside F.6: the defect, what it loses, that cancellation and timeouts are not exposed, why twins end
   in-band; cite the source lines at v1.29.0. CLAUDE.md: one sentence at the end of the "Known intermittent
   `digital-twin-e2e` shutdown flake" bullet, pointing at that fact.

## Never
Weaken a check: no longer wait, no retry, no skip, no deselection. Never edit `src/`, `ext/`, `toolchain/` or the
MicroPython checkout; never read `arduino/`; never open `/root/.claude/`. No hardware.

## Rules for the text
Text outside `audit/` cites no audit IDs, unit names or run numbers. A choice carries "(agent, 2026-11-06)"; a fact
its source citation. Comment-block and line rules as CLAUDE.md states them.

## Checks
`S/u35/lead/lint_direct.sh`; the three mypy passes; every changed test file; the scenario tier for arzi and dev at
both GC stages, as `scripts/test.sh` runs it; the digital-twin CI suite as CI runs it; `tests_scripts` whole. Heavy
runs one at a time under `S/u35/lead/heavy.lock` as common_r1 says, at most six.

## Limits
Write only `scripts/_twin_process.py`, `scripts/_digital_twin_scenarios.py`, `scripts/_digital_twin_ci_suite.py`,
`digital_twin/run_generic_integration.py` (only to remove a dead flag), their tests, SPECIFICATION.md,
`digital_twin/README.md` and CLAUDE.md. Net growth across code and tests at most 30 lines. One commit. Budget about
0.8 % of the week; at 80 % of it stop at a clean commit and report. Hand back by 08:00 UTC.

## Hand-back
`S/u35r/r4/HANDBACK_STOP.md`, at most 20 lines, and return its path: what changed (file:line), lines in and out, each
check with its result. Last line: "nothing of mine is running".
