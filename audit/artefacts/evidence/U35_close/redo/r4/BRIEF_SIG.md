# Diagnosis unit: a scenario twin that did not act on its SIGINT (lead, 2026-11-06)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `sig_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.

## The failure
CI on snapshot 41 (`ba581e5c`, run 42157783475, job 127696270505, "Unit tests (shipped gc.threshold)", 03:49 UTC):
`scenarios[arzi]` at GC 32768, scenario `a_hung_shutdown_step_is_ended_by_the_watchdog`
(`scripts/_digital_twin_scenarios.py:1071`): "twin 7: the SIGINT shutdown ended killed by the caller after it ignored
SIGINT (exit code -9) (114.7s)". All other 62 arzi scenarios and every other device passed. The push changed only
SPECIFICATION.md and `tests/test_digital_twin_hot_replug.py`; snapshot 40's CI, on the same product and harness code,
was green. The runner's instruments for exactly this case (`scripts/_twin_process.py`: the `/proc` signal state, a
second SIGINT, `--test-kbd-traceback`) printed into the CI log's scenario block, which this session cannot fetch (the
log host is outside the network allowlist; the GitHub tool returns only the log's tail). Do not try.

## What is known
The same symptom once before, on dev at the same GC stage: read
`audit/artefacts/evidence/U28_close/lead/hang/handback.md` whole, `lead/fix2/*.txt` beside it, and the REGISTER rows
that name the item (`git grep -n OF-215 audit/REGISTER.md`). About 1,900 deliberate SIGINTs reproduced nothing then;
no handler that swallows a KeyboardInterrupt was found; the left candidates were runtime or environment level. The
instruments (its proposals a-c) landed; the in-band stop (d) was routed to this round and not done. Since then the
shutdown path changed (`git log` on `scripts/_twin_process.py`, `digital_twin/run_generic_integration.py`,
`digital_twin/machine.py`); read those changes.

## Your work (worktree `S/wt-sig`, branch `audit/sig`, at int `f509c906`; create it; commit locally, never push)
1. Find which hang step twin 7 is, and what that twin is doing when the runner sends SIGINT.
2. Reproduce with the instruments on, as close to CI as this host allows: arzi at 32768, first the six devices'
   scenario sets as `scripts/test.sh` runs them, then this scenario looped under parallel load. Each run holds the
   heavy slot as common_r1 says; at most ten heavy runs, one at a time. A reproduction's instrument output is the
   evidence.
3. Root cause, from evidence. If the fix lies in `digital_twin/`, `scripts/` or a test: make it, seen failing first
   where it can be, and run the checks below. If it lies in `src/` or the toolchain: propose it and stop.
4. Not reproduced within the budget: say what ran, what the instruments would need to show, and whether the in-band
   stop is now the right step (its own test seen failing first with a twin whose SIGINT is blocked).

## Never
Weaken the check: no longer wait, no retry, no skip, no deselection, no "flake". Never edit `ext/` or `src/`; never
read `arduino/`; never open `/root/.claude/`. No hardware.

## Checks for a fix
`S/u35/lead/lint_direct.sh`, the three mypy passes, every changed test file at both GC stages, the scenario on arzi
and dev at both stages, `tests_scripts` whole (heavy slot).

## Limits
Budget about 1.5 % of the week; at 80 % of it stop at a clean commit and report. Hand back by 08:00 UTC.

## Hand-back
`S/u35r/r4/HANDBACK_SIG.md`, at most 30 lines, and return its path: the cause (or why not found), the evidence, the fix
and its checks (or the proposal). Last line: "nothing of mine is running".
