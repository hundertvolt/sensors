# U24 close evidence

What each folder proves (the scan record `audit/sweeps/scan_runs/20261014_U24_close.md` cites them). Logs only:
no copy of a tracked file (checked by `final_evcheck.py`: blob, name, 90 % line overlap; 0 flagged over 58 revisions),
no credential (86 pattern hits, every one a test name or identifier). Files over 100 KB are gzipped.

- `gates/`: the gate on `be52286` (`gate.out` the timeline; lint, both typecheck scopes, `test.sh` at -1 and 32768,
  `npm test`, the six twins, coverage) and `post_*`: the typecheck scopes green after the offline sync.
- `lane_<L>/`: each lane's hand-back (its record) and the logs behind its seen-failing, bite, probe and timing claims.
- `lead/`: the lead's notes, rulings, checklist, concurrency rules, base timing table and run record; `w2/` the merge
  step's proofs (the cleared-task segfault seen failing and fixed, the drift probe, the reap-round regression on lane K's
  harness and the W1 harness, the 137 retry, the aborted-run mode leak seen failing with `GC_THRESHOLD=32768`);
  `u23_cifix/` U23's CI fixes (CI probe lines, the old code failing first under forced races, the fixes green, the
  coverage red's CI excerpt).
