# U29 close evidence

What each folder proves (the scan record `audit/sweeps/scan_runs/20261020_U29_close.md` cites them). Logs only: no copy of a
tracked file (checked over `e27b782` and every commit of `e27b782..a8d4ebb`: blob, name, 90 % line overlap; the one name hit is this index itself), no credential value: the history scan names a found value by commit, path, length, character
classes and `sha256[:8]` only; the hotspot default reads `<row-8-default>` and the bench LAN's third octet `<bench>` in every
file here. Files over 100 KB are gzipped.

- `gates/gate1/`: the gate on `4ac9a7f` (`gate.out` the timeline): generation, lint, ruff with CI's paths,
  typecheck with no arguments and with CI's paths, `pytest --collect-only tests_hardware`; `scripts/test.sh` at -1 and 32768;
  the six twin runners; `npm test`, `npm run test:coverage` and the web statics (`npm_static/`); the coverage leg.
- `lane_D/`: SPECIFICATION.md A.11 and its check: the check red on the base, the bites (in scratch copies), the 12 checks,
  the reader runs (105 files) and the new file's time.
- `lane_R/`: the pyflakes allowance's liveness and the radio rung's L2 case: before/after/final times at -1, 32768 and
  settrace (`times.tsv`), the bites, the checks.
- `lane_S/`: the one-time history secret scan: `report.md` (the full result), `scan_final.txt` (the final run's masked
  output) and its time.
- `lane_T/`: the timeout-retry rule: the guard red first, the pytest tier's stubbed proofs, the vitest proof in a scratch
  copy, the budgets' derivation, the checks and times.
- `lead/`: the checklist, concurrency rules, run record, rulings (R-1 to R-11), relay, the lead's log for the unit (with the
  owner's decisions and questions quoted), the review list, the REGISTER and open-finding rows, the parked hardware items;
  `tier/` the whole `tests_scripts` tier on the merged tree (`08c733a`), `tier2/` on `d4c71e7` (the twin record's red
  before the re-record), `tier3/` on `4ac9a7f` (green, with group 0's rerun); `review/` the review of the unit's diff
  (its hand-back) and the lead's checks of its fixes on `a8d4ebb`.
