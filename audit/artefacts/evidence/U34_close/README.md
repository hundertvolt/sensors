# U34 close evidence

What each folder proves (the scan record `audit/sweeps/scan_runs/20261021_U34_close.md` cites them). Logs only:
`assemble.sh` copies each lane's `*.log`, `*.txt`, `*.out`, `*.tsv`, `*.time` and `*.times` files three levels deep
(the bite folders hold one scratch copy per plant) with the hand-backs, the plan and the lead's files, removes any file
whose git blob id is in the base's or the head's tree outside `audit/` (a copy of a tracked file; earlier units'
evidence under `audit/` holds logs a rerun reproduces byte for byte, so it is not compared), and then deletes every code file it
picked up (`*.py`, `*.sh`, `*.js`, `*.mjs`, `*.toml`, `*.ini`, `*.yml`, `*.diff`, `*.pid`), every empty file and every
empty folder. So the lanes' run scripts, edit helpers and scratch configs, the plan's helper scripts (`lead/plan/`
holds the two hand-backs alone) and the mpy-cross outputs (bytecode; their byte compares are in A2's and N1's
hand-backs) are not here. `final_evcheck.py` over the close head and every commit of `970b63b..` it (116 revisions, 958 blobs) flags one file,
this README by its name, as in every earlier unit; a first run also flagged lane N's K.9 draft, SPECIFICATION.md's own
text, which `assemble.sh` now leaves out. Its 90 credential-pattern hits are all names (test names, the twin's
`wrong_password` outcome in help text, the word "token" in prose), no value. The withheld-value check (two sha256[:8]
prefixes and the control's against every token, gzip read through) reads 368 files with 0 hits; its control token,
planted in a scratch file, was caught. No credential value: the hotspot default reads `<row-8-default>` and the bench LAN's
third octet `<bench>` in every file here. Files over 20 KB are gzipped.

- `lane_A/`: THIRD_PARTY_LICENSES.md, README.md, `src/LICENSE-captive_dns`, four `src/` headers, the attribution and
  freezefs tests. A1: the doc checks after each of its seven commits (`chk_s1.log` to `chk_s33.log`, 37 passed each),
  the R-5 plant (`bite_r5.log`), the paired times (`pair_time.tsv`). A2: the new test seen failing on a scratch export
  of `978d1bf` (`seen_attr.log`), the seven bites and their control (`bites_a2/*.log`), the readers (`a2/r_*.log`, red
  only on `test_twin_record`, expected before the re-record), the four unit files at -1 and 32768, base and head
  (`a2/u_*.log`), the paired doc-check times (`a2/p_*.log`), the 17 scans with the attribution files (`a2/scans.log`,
  984 passed), the mypy passes (`a2/mypy_*.log`), `checks_a2.log`. The A1 and A2 hand-backs.
- `lane_N/`: `src/asy_udp_socket.py`, `tests/test_asy_udp_socket.py`, SPECIFICATION.md. N1: the header commit's checks
  (`hdr_checks.log`), the removal's checks (`r7_checks.log`), the main mypy pass in both forms (`mypy_main_*.log`), the
  four bites (`bites/*.log`), the four UDP-family unit files at both stages, base and head (`paired.tsv`, `plogs/`),
  the twin dev integration on the head. N2: `test_tunables_register` seen failing on `d6db0e7`
  (`n2_seen_failing_tunables.log`), the pre-commit checks per commit (`n2_commit*_checks.log`), the SPEC readers and
  the 17 scans, base and head (`n2/base_*.log`, `n2/head_*.log`, `n2/head_17scans.log`), the three-round re-time
  (`n2/retime.tsv`), K.9's citation on a scratch copy (`k9_scratch_citations.log`). The N1 and N2 hand-backs.
- `lane_T/`: `pyproject.toml`, both inis, `tests_scripts/test_mypy_any_baseline.py`, BACKLOG.md. T1: the six mypy runs
  with every exemption dropped (`noex.*.log`, the residue's sites), base and head (`base*.log`, `head*.log`), the guard
  seen failing at the old configs (`seen_failing.log`) and bitten (`bite.log`), the full `scripts/typecheck.sh`
  (`typecheck_full.log`). T2: `disallow_any_unimported` forced on (`unimp.*.log`, `unimp.times`; the host run's 4
  findings), the probe that the forced flag takes effect (`probe.log`), the final checks base and head
  (`fin.base.*.log`, `fin.head.*.log`, `fin.lint.log`, `fin.typecheck.log`). The T1 and T2 hand-backs.
- `lane_C/`: `.github/workflows/ci.yml`, `tests_scripts/test_ci_workflow.py`. The pin seen failing on all four jobs at
  base (`seen_failing.log`), the five bites (`bite.log`), lint's passes (`lint_parts.log`), the host mypy pass
  (`mypy_host.log`), the six readers (`reader_*.log`), the scans (`scans.log`, 965 passed), the paired times
  (`time_*.log`). The C1 hand-back.
- `lead/`: the checklist and the run record (`CHECKLIST.md`, `RUNS.md`), the lane plan with P1's step table, P2's
  rulings and the LEAD NOTES (`lane_plan.md`), the relay, the facts owed to wave 2 (`owed_w2.md`), the captive DNS's
  upstream facts R-11 rests on (`upstream_captive.md`), `harness_counts.txt` (the harness's tool-call count per agent,
  the counts the record cites), the briefs (`briefs/`), the lead's log for the unit (`lead_todo.md`, from U34's first
  entry on; U33's and U35's entries interleave); `plan/` the two planning blocks' hand-backs; `twin_record/` the
  re-record on the merged lanes (`run.log`, `trace.txt`: 122 of 122 results and reasons unchanged, every moved
  `api_sha256` traced, 0 untraced); `int/` the whole `tests_scripts` tier on the integration head `1dd6dd5`
  (`tier_1dd6dd5/summary.txt`: 3686, 994, 887 and 1136 passed in its four groups, 6 + 3 skipped, 0 memory-marker logs);
  `records/` the records block's hand-back.
- `gates/`: `gate1/`, the gate on `7023cd2`, every leg's log (`gc_default.log`, `gc_32768.log`, `twin_<device>.log`,
  `npm_*.log`, `npm_static/`, `coverage.log`, `vmstat.log`), and `gate1.out`, the gate's timeline (18:00 to 19:35 UTC).
- `lead/ci/`: U33's squash run 39647170466, its 46 jobs with their minutes (`run_39647170466_jobs.tsv`).
