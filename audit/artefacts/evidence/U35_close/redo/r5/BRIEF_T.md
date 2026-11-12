# R5 unit T: the test tiers, the twin and the test tooling at their need, nothing dropped (lead, 2026-11-10)

## Read first
`S/u35r/r1/common_r1.md` (binding, all of it - the two source rules, the retired-code rule, the coverage-build check;
label `t_`). S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. The rows and
their evidence: FINDINGS (`S/u35r/findings/FINDINGS.md`) 12.124-12.126, 12.137, 12.138, 12.143, 12.145, 12.155-12.157;
`S/u35r/r5/SIMPLER_3.md`, `SIMPLER_4.md` (#5, #11), `CONSENT_3.md` + ledger (the tests pass: REMOVE and SIMPLIFY rows),
`GIVEUP_3.md` + ledger (the apparatus bounds), `CREDIT_ledger.tsv` and `CREDIT2_ledger.tsv` (credits in your files).
Code: int `S/wt-u35int` at 81e2ebcd. Unit P9 writes at the same time: it owns SPECIFICATION.md, CLAUDE.md, README.md,
BACKLOG.md, UART_C_PORT_CHANGELOG.md, `.claude/`, THIRD_PARTY_LICENSES.md and credit comments in `src/`, `buildgen/`,
`devices/`, `js/`, `scripts/`. You own `tests/`, `digital_twin/`, `tests_hardware/`, `tests_scripts/`, `tests_js/` and
the one `buildgen/definitions.py` removal below. A SPEC sentence your change makes false: name it in the hand-back for
P9 (file:line, the new fact); do not edit SPEC.

## Owner (verbatim)
- 2026-11-09 22:27:31: "... don't drop real features and don't introduce or reintroduce gaps. Lean, functional, no
  losses, no gaps, efficient by smart design appropriate for limited devices like the rp2"
- 2026-11-09 21:33:48 (5): the twin demo is obsolete.
- Earlier, on self-bites: "Planting errors for those straightforward tests would be complete overkill."

## Your work (worktree `S/wt-t`, branch `audit/t` from 81e2ebcd; create it; commit locally, never push)
1. CONSENT_3 REMOVE rows: the 55 self-bite tests; the tests_scripts checks that pin SPECIFICATION.md tables (F.3
   timing rows, I.2, C.9, the readiness-flag layout, A.11, the sleep and suppression forms, old legacy paths). Each
   removal names its remaining catcher in the hand-back. C.8/C.9's per-lock and per-task data move beside the check
   that reads them (P9 then states each rule once in SPEC).
2. CONSENT_3 SIMPLIFY rows: per-handler C-stack pins to one logger check; watchdog feed sites to one rule (feed only in
   the system service); counter steps to the cap rule; lock order keeps the order check, drops C.8's table match. The
   static await-depth analysis stays (12.137: the margin is near critical).
3. GIVEUP_3 (12.138): the unit and twin tiers' wall-clock limits on the code's own coroutines go (the per-file timeout
   stays the hang backstop and names the file); the twin harness's product-timing numbers are read from `src/` (its
   10 s request wait follows the product's cap); the async harness's reap limit in rounds. Twin Run 3's 627 ms
   ceiling: derived from a source, or it goes.
4. SIMPLER_3: (1) the 14 per-device scenarios the unit tier already pins, plus the boot-order merge; (2) the twin's
   copied unretrieved report -> the product's PrintLog; (4) seven single cases a sweep proves; (6) the ~300 lines of
   helper copies and the dead `rx_stall_ms` knob. SIMPLER_4 #5: tests_scripts' twin boots on `distinct_devices()`;
   #11: the twin harness helpers into `_twin_process.py`.
5. Twin fakes (12.137): `rp2.py` and `neopixel.py` one copy each in a neutral directory both MICROPYPATH layouts
   read; the twin imports nothing from `tests/` and `tests/` tests nothing from `digital_twin/`; machine/network
   stay per tier.
6. `digital_twin/launch.py`'s demo goes (owner: obsolete); its `--fault`/`--hang` vocabulary moves into the runner
   that serves the real website (`scripts/run_unix_port_integration.sh` path) only where a test or doc uses it.
7. Fixes: `test_digital_twin_uart_comm_hazard.py` hangs to its per-file timeout when its scenario raises (make it fail
   at once); `tests_hardware/bench/_load.py:477`'s comment names the removed `arm_tick_timer()`.
8. cr2's R0 growths (CREDIT2_ledger rule R0, units T): the bench test's FRAM_STATUS_BYTE/FRAM_BLOCK_INVALID
   tolerance; `tests_scripts/test_import_placement.py` and the imports-at-module-load rule it checks (OR141.a (2)
   called the rule unchanged); the twin's notice on a state file that cannot be loaded. Judge each by common_r1's two
   source rules: keep with "(agent, date)" and its need, or remove; say which and why.
9. `buildgen/definitions.py`'s `main()` and `__main__` block go with their tests (12.157: no caller since C's #4;
   `_generate_sensortask_modules.py --device-toml --out-dir` keeps the capability).
10. Credits in your files: the "owner-reviewed, 2026-11-06" suffix goes ("(agent, date)" stays); audit-era
   STRETCHED/UNBACKED take CREDIT_ledger's plain form; pre-audit ones take CREDIT2_ledger's new plain form.

## Never
Never remove a feature or a test's only catcher of a real behaviour; a behaviour test (what the product does) stays.
Never change `src/` behaviour, a stored FRAM byte, a wire byte, a /status byte or a generated module's content. Never
edit `ext/`; never read `arduino/` (`':!arduino'` in every git grep and git log); never open `/root/.claude/`; no
hardware (`tests_hardware` only `--collect-only` or `--twin`). No new bound or mechanism without a source. Credential
filter as common_r1 says. Scratch only under `S/u35r/r5/ftmp_t/`. Until `S/u35/lead/heavy.lock` is gone (the lead's
gate holds it now): reading, editing and single test files that bind no port only.

## Checks and hand-back
Touched test files at both GC stages and under the coverage build while fixing; `lint_direct.sh`; three mypy passes;
npm lint, typecheck, unit tests when `tests_js/` changes; then the gate as common_r1 says (PICO_TOOLCHAIN_DIR=S/tc-c:
it carries the qstr override int now needs) under `S/u35/lead/heavy.lock` holding `t` (P9 may hold it: wait while it
exists; `rm` it, literal path, its own command). Lines and tests removed per item; suite wall-clock at -1 against
81e2ebcd. One commit; budget about 4 % of the week. Hand back by 15:00 UTC: `S/u35r/r5/HANDBACK_T.md` (at most 40
lines: per item what went, its remaining catcher, the figure; SPEC sentences for P9), your commit, one line per
headline result, and last "nothing of mine is running".
