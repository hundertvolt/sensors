# U33 close evidence

What each folder proves (the scan record `audit/sweeps/scan_runs/20261021_U33_close.md` cites them). Logs only:
`assemble.sh` copies each lane's and block's `*.log`, `*.txt`, `*.out`, `*.tsv` and `*.time` files two levels deep with
the hand-backs, the plan and the lead's files, and then deletes every code file it picked up (`*.py`, `*.sh`, `*.js`,
`*.mjs`, `*.toml`, `*.ini`, `*.yml`, `*.diff`, `*.pid`), every empty file and every empty folder. So the lanes' run
scripts and edit helpers and the plan's helper scripts are not here (the plan's scratch held only helpers, so
`lead/plan/` holds the two hand-backs alone); U33 changed documents only, so there are no bite trees or base copies of
code. `final_evcheck.py` over the close head and every commit of `970b63b..` it (84 revisions, 929 blobs) flags one file, this README by its name, as in every earlier unit; its 146 credential-pattern hits are all names (test names, the words "password" and "tokens"), no value. The withheld-value check (two sha256[:8] prefixes against every token, gzip read through) reads 126 files with 0 hits; its control token, planted in a scratch file, was caught. No credential value: the hotspot default reads `<row-8-default>` and the bench LAN's third octet
`<bench>` in every file here. Files over 20 KB are gzipped.

- `lane_B/`: BACKLOG.md, CLAUDE.md and the two allow-lists. B2: the three doc checks on each head
  (`b2_checks_0.log` to `b2_checks_3.log`, 24 passed each), the allow-list rows seen named by the stale-entry checks
  after 1b's deletions (`b2_seen1.log`), item 32's deletion on a throwaway tree without SPECIFICATION.md's repoint
  (`b2_seen2_nocite.log`, naming `SPECIFICATION.md: BACKLOG item 32`). B3: the E722 row seen named first
  (`b3_seen1.log`), the step and wozi checks (`b3_step4.log`, `b3_r6.log`), the 17 repo-wide scans on `629069e`
  (`b3_scans17.log`, 874 passed), the five readers' paired base and head times (`b3_pairs.tsv`, `b3_pair_*.log`,
  `b3_checks.out`), the rebuild. The B1 (research only), B2 and B3 hand-backs.
- `lane_S/`: SPECIFICATION.md and `tests_hardware/README.md`. S1: the twelve readers, base `c6b8a07` and head
  alternating twice (`readers_*.log`, `readers_summary.log`, 140 passed every run), H.8's pointer seen failing before
  B.16 existed and green after (`b16_seen_failing.log`, `b16_green.log`), the repoint's citation check
  (`cite_check.log`). S2: the pre-commit checks (`S2_precommit.log`, 665 passed), the 27-file runs, base and head
  alternating twice (`r2_*.log`, `r2_summary.log`, `r2_times.log`, 1158 passed every run), the three-round focused
  timing rerun (`r3_*.log`), `tier/` (the whole `tests_scripts` tier on `ade93e6`: 6692 passed, 9 skipped, 0
  memory-marker logs), the rebuilds. The S1 and S2 hand-backs.
- `lead/`: the checklist and the run record (`CHECKLIST.md`, `RUNS.md`), the lane plan with P1's step table, P2's
  rulings and the LEAD NOTES (`lane_plan.md`), the relay, `harness_counts.txt` (the harness's tool-call count per agent,
  the counts the record cites), the briefs (`briefs/`, the lead's rulings L-1 to L-7 in `b2.md`), the lead's log for the
  unit (`lead_todo.md`, from U33's first entry on; U34's entries interleave); `plan/` the two planning blocks'
  hand-backs; `int/` the whole `tests_scripts` tier on the integration head `147ea3f` (`tier_147ea3f/summary.txt`: 3678,
  965, 899 and 1150 passed in its four groups, 9 skipped, 0 memory-marker logs); `records/` the records block's
  hand-back; `ci/` U32's CI job minutes (`run_39624933720_jobs.tsv` read while three harness legs still showed as in
  progress, `run_39624933720_jobs_refetch.tsv` the settled 46/46); `cg/` the coverage step's growth measured per file
  (the CG block's tables on U31's and U32's trees as they stood at this close; its hand-back and final figures are
  U35's evidence).
- `gates/`: `gate1/`, the gate on `c26db17`, every leg's log (`gc_default.log`, `gc_32768.log`, `twin_<device>.log`,
  `npm_*.log`, `npm_static/`, `coverage.log` the coverage leg's re-run, `coverage_enospc_1713.log` its first run, cut
  off when the host's disk was full), and `gate1.out`, the gate's timeline with the re-run's lines.
