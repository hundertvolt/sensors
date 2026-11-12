# R5 close unit W1a: the test and tooling items the close list holds open (lead, 2026-11-10)

## Read first
`S/u35r/r1/common_r1.md` (binding, all of it; the filter rule above all; label `w1a_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Your rows, with their evidence:
`S/u35r/r5/CLOSE_STATUS.tsv` (B01, U02, S04, H01, H02, H03, H04, H05, H12, H27, B37, F3's first half, B27's twin half).
FINDINGS (`S/u35r/findings/FINDINGS.md`) 12.137, 12.138, 12.164, 12.170, 12.171. Code: int `S/wt-u35int` at 651af010.
Unit W2 writes at the same time (BACKLOG lines 28-400 but your two items, README, CLAUDE.md, SPEC L.7, `buildgen/version.py`,
`mockdata/`, and `tests_scripts/test_stored_config_golden.py`, `test_api_reference.py`, `test_buildgen_version.py` whole,
their import-placement entries included); a later unit reorders members (D.15): do not reorder.

## Owner (verbatim)
- 2026-11-10 14:57:50: "We still are at 40. Do (A), finish as planned" (every planned close item, by hand).
- 2026-09-28 (B01): "do it in this audit". 2026-11-09 22:27:31: "... don't drop real features and don't introduce or
  reintroduce gaps. Lean, functional, no losses, no gaps, efficient by smart design appropriate for limited devices like
  the rp2"

## Your work (worktree `S/wt-w1a`, branch `audit/w1a` from 651af010; create it; commit locally, never push)
1. B01: the 7 mypy Any exemptions (pyproject.toml:404-411, digital_twin/typecheck.ini:37-38, host_typecheck.ini:45-46,
   25 explicit Any) typed (Protocol or delegation, the leanest that holds); the three baselines go;
   `test_mypy_any_baseline` keeps its flag check; BACKLOG's B01 item (about :13-22) goes.
2. U02 + S04: `test_import_placement.py`'s `_PENDING` (68) emptied by moving each import to module level, or, where a
   real need forces a function-level import (a path set at run time, a circular import), a `_NAMED_EXCEPTIONS` entry
   with that reason; the scope-wide PLC0415 ignores (pyproject.toml ~:208, :225) go when nothing needs them;
   `_NOT_YET_CLEANED` (test_no_variant_literals.py:27-32) shrinks as the row says. W2's three files: leave them.
3. H01-H03: each test or twin bound named there (`LISTENER_DRAIN_S`, `_STALL_DRAIN_S`, the caught listener
   `wait_for`s in test_uart_comm_hazard.py / test_asy_ntp_client.py, `_ESCALATION_WAIT_S` 120 s and the twin's other
   unsourced numbers) gets its source by common_r1's bound rule (read from `src/`, or derived and named) or goes.
4. H04/H05: one shared helper for the `_cycle` copies (4 notification integration tests) and the `_crc8` copies (3);
   the device scripts' `_REPORT = PrintLog(...)` copies (6) into the scripts' shared module.
5. H12: `scripts/cross_browser_smoke.mjs:83` boots one device per hardware family, as `scripts/test.sh` does
   (npm lint, typecheck and unit tests after). H27: the last "owner-reviewed, 2026-11-06" tag
   (tests/test_digital_twin_run_generic_integration.py:1168) takes its plain form.
6. B37: the twin's SGP40 answers an unknown command as silicon did (ETIMEDOUT about 0.5 s, recovered 528 ms;
   READING_20261029.md:76, cite it); SPEC's fidelity row 222 states the fact; BACKLOG's B37 item (about :222-226) goes.
7. F3, first half: root-cause on the host why `sgp40_voc_algorithm_quality` fails 2 in 15 on the twin at 32768 only
   (run it at both stages, enough runs to see it); fix it if the cause is in the test or the twin, report it if it is
   in `src/`. The twin's raw walk correction waits for the last round.
8. B27, twin half: the idle poll rate measured on the host, the Part N `udp.poll_idle_ms` row's Basis states it.

## Never
Never change `src/` behaviour, a generated module's content, a stored FRAM byte, a wire byte or a /status byte. Never
remove a test that is a behaviour's only catcher; never weaken a check. Never edit `ext/`; never read `arduino/`
(`':!arduino'` in every git grep and git log); never open `/root/.claude/`; no hardware (`tests_hardware` only
`--collect-only` or `--twin`). No new bound or mechanism without a source. Credential filter as common_r1 says.
Scratch only under `S/u35r/r5/ftmp_w1a/`. While `S/u35/lead/heavy.lock` exists: reading, editing and single test files
that bind no port only.

## Checks and hand-back
Touched test files at both GC stages and under the coverage build; `lint_direct.sh`; three mypy passes; npm lint,
typecheck and unit tests for item 5; then the gate as common_r1 says (PICO_TOOLCHAIN_DIR=S/tc-c) under
`S/u35/lead/heavy.lock` holding `w1a` (wait while it exists; `rm` it, literal path, its own command). One commit; budget
about 3 % of the week. Hand back: `S/u35r/r5/HANDBACK_W1A.md` (at most 40 lines: per item what changed and its count,
F3's cause, any SPEC or BACKLOG sentence W2 or the lead must change), your commit, one line per headline result, and
last "nothing of mine is running".
