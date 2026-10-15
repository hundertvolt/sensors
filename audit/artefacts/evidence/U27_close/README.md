# U27 close evidence

What each folder proves (the scan record `audit/sweeps/scan_runs/20261015_U27_close.md` cites them). Logs only: no copy of a
tracked file (checked by `final_evcheck.py` over `0c0ad52` and every commit of `0c0ad52..61ff487`, 28 revisions: blob, name,
90 % line overlap; 1 flagged, rule b's name match on this README itself), no credential (154 pattern hits at staging: test,
function and parameter names, profile lines, assertion messages, a test's random marker and this sentence; the hotspot password value of
`devices/*.toml` is in no file). Files over 100 KB are gzipped.

- `gates/gate1/`: the gate on `7f34f35` (`gate.out` the timeline): generation, lint, ruff with CI's paths, typecheck with no
  arguments and with CI's paths, `pytest --collect-only tests_hardware` (196 of 226); `scripts/test.sh` at -1 and 32768
  (each PASS, 114 files, 5434 tests, 6184 `tests_scripts` tests, the six scenario jobs); the six twin runners (suite at both
  stages, harness at -1 and 32768, rc 0); `npm test` (1647 passed); the coverage leg (every test passed, exit 3: the
  renderer's unpinned dependency could not resolve offline, OF-203).
- `gates/gate_cov2/`: the coverage leg again on `70312f6` after one online warm-up of the render environment: every
  MicroPython test passed and all four reports rendered; its `tests_scripts` tier's one red was the new guard's own literal
  (SF-U27-25, fixed in `34d7497`).
- `gates/final_times/`: the final timing pass on `70312f6`, each file alone against the base table (`times.tsv`,
  `summary.txt`, `logs/`); its eight failed rows were its own tree, cleaned without the frozen website.
- `gates/npm_static/`: `npm run lint`, `typecheck`, `lint:html` and `lint:css` on `70312f6`, each rc 0.
- `gates/final_tail/`: the final tree `61ff487`: the whole `tests_scripts` tier alone (`tier.log`, 6193 passed, 6 skipped)
  and the nine rows the timing pass could not judge, timed again alone after the rebuild (`times.tsv`, `logs/`).
- `lane_<L>/`: each lane's hand-back (`handback.md`, its record: T's T1 and final, U, B, S, M and X as received) and the
  top-level logs behind its seen-failing, bite, before/after and timing claims; `lane_E/` the efficiency pass's before,
  after and bite runs (its figures are in the review list); `lane_E2/` the second pass on the files the final timing
  pass flagged: its A/B runs against `34d7497` and `0c0ad52`, profiles, bites and hand-back.
- `lead/`: the checklist, concurrency rules, run record, rulings (R-1 to R-25, R-27), relay, the plan and its gaps, the lead's
  log, the `/dev/null` incident, the base timing table and `base_logs/` (the one timed sweep at `0c0ad52`); the review list,
  the open-finding updates with their evidence lines, the parked hardware items, owner question 6, the lead's SPECIFICATION.md
  F.7 edit and the close's open points; `verify_rows.txt` (the 51 verify rows, R-10); `api/`, `w1/` (with `run1/`, `run2/`,
  `tier/`, `fix4/` the cross-lane reds and their fixes, `rec/` the twin record's re-run), `w2/` the merge sweeps;
  `rebuild/` the instance rebuild's timeline, fingerprints before and after, step logs and `proof/` the re-proof on
  `233c8f9`; `eff/` lane E's profiles;
  `close_checks/` the five doc checks on the integrated tree (`70312f6` plus the close records), each alone, all green.
