# U26 close evidence

What each folder proves (the scan record `audit/sweeps/scan_runs/20261015_U26_close.md` cites them). Logs only:
no copy of a tracked file (checked by `final_evcheck.py`: blob, name, 90 % line overlap; 1 flagged over 58 revisions, rule b's name match on this README itself), no credential
(218 pattern hits, each a test or function name, an import-time line or an assertion message; the hotspot fallback value is in no file). Files over 100 KB are gzipped.

- `gates/gate1/`: the gate on `72f8f6d` (`gate.out` the timeline): lint, the three type passes, `test.sh` at -1 (green) and
  32768 (one `tests_scripts` red: a whole-repo scan walked into the MicroPython tier's scratch, OF-189); the six twins (suite
  and harness at both stages, green); `npm test` (four ESLint-ceiling reds from a stale install in the gate's own worktree,
  not the tree); coverage (5725 passed, the `tests_scripts` tier over its 1200 s bound beside the instrumented tier, OF-190).
- `gates/gate2/`: the re-gate on the close head after the fixes (`gate_v15`): lint, the type passes, `test.sh` at -1 and
  32768, the harness part of the six twins at both stages from trees without a site build, `npm test` on an install equal
  to the lock (checked before any leg) and coverage. The suite part of the twins stands on gate1: nothing in the diff
  since reaches `src/`, `digital_twin/` or `tests/`.
- `gates/final_times/`: every `tests_scripts` file of the unit's sets and every one changed since the base, each alone
  (`times.tsv`: file, base s, now s, exit, verdict; `base_e1106ac.tsv` four files re-timed at the base).
- `lane_<L>/`: each lane's hand-back (`handback.md`, its record) and the top-level logs behind its seen-failing, bite,
  before/after and timing claims; `lane_DR/` the U25 CI fix lane's drift probes.
- `lead/`: the checklist, concurrency rules, run record, rulings, relay facts, the plan's gaps, the lane plan and the base
  timing table; the review list, owner questions and parked hardware items; `api/`, `w1/`, `w2/` the merge sweeps and the
  twin record's first runs (`w2_rec/` its reasons and outcomes, `w2_voc/` the SGP40 walk simulation behind OF-181);
  `walk/` the scratch-churn probe (OF-189: the old walk raised on 365 of 3000 churned walks, the shared walk on 0);
  `of66/` the pause script with its pool premise forced to fail, before and after (OF-66); `close__work/` the close's
  citation remap and seen-failing outputs; `rec2/` the close record run; `memscan/` the second run with every board output
  teed (`run.txt`; the teed log itself gzipped: 178 outputs, no memory marker).
