# U31 close evidence

What each folder proves (the scan record `audit/sweeps/scan_runs/20261021_U31_close.md` cites them). Logs only:
`assemble.sh` copies each lane's, block's and fix's `*.log`, `*.txt`, `*.out`, `*.tsv` and `*.time` files two levels
deep with the hand-backs, and then deletes every code file it picked up (`*.py`, `*.sh`, `*.js`, `*.mjs`, `*.toml`,
`*.ini`, `*.yml`, `*.diff`, `*.pid`), every empty file and every empty folder. So the lanes' base copies of the files
they changed, their bite trees and their run scripts are not here, nor is any JSON (the twin record's before-image, the
reasons file, the CI job lists, the scenario evidence files); the record names what each shows. The evidence check
(`final_evcheck.py`, kept outside the evidence) over `aba11d5` and the 95 revisions of `aba11d5..6eed1ff` (blob, name
and line overlap) flags only `README.md`, this index itself, as at U28 to U30; its 457 credential-word hits are test
names, help text and prose (two of them this index's own words). The withheld-value token hash check
(`withheld_check.py`, kept outside the evidence) found neither withheld bench password over 23057 files (this staging,
the unit's scratch and `audit/`), its control (the hotspot default's hash over `audit/harvest/`) 8 hits. No credential
value: the hotspot default reads `<row-8-default>` and the bench LAN's third octet `<bench>` in every file here. Files
over 20 KB are gzipped.

- `gates/gate1/`: gate1 on `6eed1ff`, every leg rc 0. Phase A (`gate_phaseA.out`, `vmstat_phaseA.log`): generation, lint,
  ruff, typecheck, collect-only (`collect_hw.log`), `scripts/test.sh` at -1 (`gc_default.log`) and 32768
  (`gc_32768.log`); `killed_0637/` the four twins' partial logs from the shell the harness stopped at 06:37 (no result
  read from them); phase B (`gate_phaseB.out`, `vmstat.log`): the six twins (`twin_<device>.log`), `npm_test.log`,
  `npm_coverage.log`, `npm_static/`, and the coverage leg (`coverage.log`).
- `lane_C/`: the re-arm's quiet form (CORE, `c1_*`), the sleep-form guard and the build's I2C-timeout rule (`c2_*`: each
  seen failing, then after), the supervisor's own fault and the bounded escalation entry (`c3_*`); the runs at -1, 32768
  and settrace, the bites (`bite_*`), the readers and scans; the C1, C2 and C3 hand-backs.
- `lane_S/`: the LED frame (LED), the notification sleeps, the I2C probe settle, BMP3XX's and SCD30's waits in ms: base,
  after and final runs at both stages, the bites, the boot contiguity run; the S1, S2 and S3 hand-backs.
- `lane_W/`: the WiFi constants and LED patterns (NET; `pre_*` before, `wifi*_m1`/`wifi*_32k` after, `seen_fail_*`), the
  UDP and captive-DNS backoffs (`w2_*`: before, seen failing, after at both stages), `w3/` the webserver block's batch
  (ruff, the four mypy passes, the readers, the scans); the W1, W2 and W3 hand-backs.
- `lane_F/`: the twin STA's EPERM, the access point's drop and the STA's deactivation: `pre/` the six twin integration
  runs at both stages before the change (`summary.tsv`), `seen_failing_nn.log`, `bite_ap.log`, `final/` the network and
  scenario runs after it; the hand-back.
- `lane_T/`: the runner's two test flags (`flags_*`), the runner test and the loop-lag scenario seen failing
  (`runnertest_seen_failing.log`, `scen_seen_failing.log`), `twin/`, `twin2/`, `twin3/` the scenario runs, `t2/` and
  `t3/` the T2 and T3 blocks (the bites per device, the finals at both stages, the readers: `t3/fin.tsv`;
  `T2_seen_fail_lagbound.log` the consumer bound seen failing); the T, T2 and T3 hand-backs.
- `lane_L1/`: the lead's fix block (the watchdog-feed bites re-anchored, the escalation's `MemoryError`, the shared ms
  recorder): seen failing, the bites, the finals at both stages; the hand-back.
- `lane_D/`: the documents and `tests_scripts/test_timing_budget.py` (`D1_seen_failing.log` first), the doc checks
  (`chk*`), each block's final; the D1, D2 and D3 hand-backs.
- `review/`: the five readers' hand-backs (`RA.md` to `RE.md`) and the lead's dispositions (`rulings.md`).
- `fix/`: one folder per fix with its hand-back and logs: `fx1/` (E115 and the WiFi re-arm: seen failing, bites,
  finals), `fx2/` (the sleep stand-ins' integer check: `before/` and `after/` the 40 changed files at both stages, the
  bites on the old and new stand-ins (`bite_*_old`, `bite_*_new`), the readers), `fx3/` (the scenario harness and F.3;
  `runs/batch.log` the 12 scenario runs), `fx4/` (the straddling window and the settle sleep's removal: `runs_before/`,
  `runs_after/`, `runs_after2/` each run's summary,
  `probe/summary.txt` the off-CPU probe, `final/` the readers and both stages, `results.tsv`), `fx5/` (the documents'
  corrections), `fx6/` (the flash-gap scratch name and its budget row: `bites/`, `readers/`).
- `lead/`: the checklist, concurrency rules and run record, the lane plan, the relay, the lead's edits and the lead's log
  for the unit (`lead_todo.md`, from U30's DONE entry on), `rec_harness_counts.txt` (the harness's tool-call count per
  agent, the burn the record cites); `runs/` the lead's own checks of `f108787` and `3595a49` (the two machine fakes'
  files at both stages and their bites, `re_*` and `re2_*` after the cancel-first change, the runner test `rgi_*`,
  `time_scenarios.tsv` the scenario check's times on `e507e9f`); `twin_record/` the re-record on the final tree
  (`run_first_missing_reason.log` the first run, stopped on the new flash-gap script having no reason; `run.log` the
  second, rc 0; `trace.txt`: 121 results and reasons unchanged, 44 entries' hashes moved, each traced to a file changed
  since `aba11d5`, 0 untraced, the new script added); `int_tier1/` the whole `tests_scripts` tier on the first
  integration head; `tier_final/` the whole tier on `e507e9f` (05:56-06:06: 3661, 958, 899 and 1131 passed in its
  four groups, 9 skipped, each with its reason, 0 failed, 0 memory markers); the tier on the squash runs after this
  staging (its result in U32's record); `records/` the records block's checks and hand-back.
