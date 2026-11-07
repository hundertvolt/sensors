# U25 close evidence

What each folder proves (the scan record `audit/sweeps/scan_runs/20261014_U25_close.md` cites them). Logs only:
no copy of a tracked file (checked by `final_evcheck.py`: blob, name, 90 % line overlap; 0 flagged over 51 revisions), no credential
(163 pattern hits, every one a test name, a CLI help line or the word "token" (CSS design tokens, a citation message)). Files over 100 KB are gzipped.

- `gates/gate1/`: the gate on `f69fc2a` (`gate.out` the timeline): lint and both typecheck scopes; `test.sh` at -1 and
  32768 (every MicroPython file green, one `tests_scripts` red each, SF-U25-28 and -29); the six twins (the suite green at
  both stages, every harness scenario failing on the missing per-device site, SF-U25-30); `npm test`; coverage.
- `gates/gate2/`: the gate on `e1106ac` after the three fixes: lint, both typecheck scopes, `test.sh` at -1 and 32768,
  and the harness part for the six devices at both stages from trees without a site build. The suite part, `npm test`
  and coverage stand on gate1: nothing in the diff since reaches them but the `tests_scripts` tier, which gate2 runs.
- `lane_<L>/`: each lane's hand-back (`handback.md`, its record) and the top-level logs behind its seen-failing, bite,
  before/after and timing claims; `lane_G/bite/` the guards bitten in a scratch copy.
- `lead/`: the checklist, concurrency rules, run record, rulings, relay facts, refresh record and base timing table;
  `w2/` and `api/` the merge sweeps; `w4/` the per-part CI job measurements and the watchdog-line bite; `w6/` and
  `leadfix/` the lead fixes seen failing; `a15/` the grkizi relaunch repeats (not reproduced, BACKLOG owner question 1);
  `fix2/` the gate fixes: the installer and counter tests on the old code, the counter race (17 of 300 kills left the old
  file empty, 0 of 300 the new), the touched files alone and five repeats, the dev harness run from a clean tree.
