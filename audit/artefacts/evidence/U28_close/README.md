# U28 close evidence

What each folder proves (the scan record `audit/sweeps/scan_runs/20261019_U28_close.md` cites them). Logs only: no copy of a
tracked file (checked over `b1fecfb` and every commit of `b1fecfb..3e87082`: blob, name, 90 % line overlap), no credential
(the hotspot password value of `devices/*.toml` is in no file). Files over 100 KB are gzipped.

- `gates/gate1/`: the first attempt on `924f08f`, stopped at its own precondition before any leg (the shared toolchain record
  named older inputs); the re-record is in `lead/toolchain/`.
- `gates/gate1b/`: the gate on the final tree `3e87082` (`gate.out` the timeline): generation, lint, ruff with CI's paths,
  typecheck with no arguments and with CI's paths, `pytest --collect-only tests_hardware`; `scripts/test.sh` at -1 and
  32768; the six twin runners; `npm test`, `npm run test:coverage` and the web statics (`npm_static/`); the coverage leg.
- `lane_<L>/`: each lane's hand-back (`handback.md`, its record as received) and the top-level logs behind its seen-failing,
  bite, before/after and timing claims (C, W, R, P, X); `lane_P/runs/` the code-changed files at both stages.
- `lead/`: the checklist, concurrency rules, run record, rulings (R-1 to R-23), the launch checklist, relay, the plan and its
  gaps, the lead's log for the unit, the base timing table and `base_sweep/` (the one timed sweep at `b1fecfb`); `api/` the
  API checks; `w1/` the merge sweeps (`static/` the W1 static checks, `tail/` the tail's and W2's doc checks with the
  datasheet move's initialised and uninitialised runs, `times/` the W1 timing pass, `ab/` the A/B against `b1fecfb`,
  `tier/t1` and `tier/t2` the whole `tests_scripts` tier on `1e4c743` and on `b4b7557`, `twin_record/` the re-record's
  run); `w2/` the datasheet blob check and the doc checks on `3e87082`; `toolchain/` the shared toolchain's re-record,
  fingerprints before and after, and the dated `mpy-cross` rebuilds; `research/` the REGISTER, open-finding and verify-row
  tables; the review list, the open-finding updates and the parked hardware items; `fix/` the html-validate CI fix
  (`79c10b4`): the workflow test red then green, the config check in its four states, ruff, actionlint, zizmor, the doc
  checks, and `tier/` the whole `tests_scripts` tier on it.
  `fix2/` the ignored-SIGINT diagnostic (`bf42ac8`): the new test red then green, the probe of a healthy interpreter, ruff,
  the host mypy pass, and `tier/` the whole `tests_scripts` tier on it; `hang/` the hung-shutdown agent's hand-back and its
  runs (the SIGINT probe, `run1`-`run4`, the five storms), every run's logs; `putskip/` the hand-back naming `npm test`'s six skips.

Added with the records after the push (the CI runs and their two fixes):

- `lead/ci/`: each run's jobs as `gh api` returned them (U27's 38777834467, the unit push's cold run 39335426899, the fixes'
  warm run 39344544377), the inputs of the job budgets.
- `lead/fix3/`: the probe's mode (`836689a`): the workflow test red on the old mode, green after; `ensure standard` run as CI
  runs it; ruff, host mypy, shellcheck, the doc checks; `tier/` the whole `tests_scripts` tier on it.
- `lead/fix4/`: `scripts/test.sh` at -1 and at 32768 on `a628c4d`, in parallel as gate1b's two stage legs.
- `lead/sgp/`: the SGP40-in-the-idle-check root cause and fix: the agent's hand-back, its notes, the idle-twin measurement
  (`run1.out`), the CI job-log tails it read (`ci/`), the fix's red and green runs and the dev harness at both stages
  (`fix/h32768`, `fix/hneg1`).
