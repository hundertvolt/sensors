T2 hand-back (lane T's final block). Branch audit/u34-t in S/wt-u34t. Lane T's commits are 1b3c13c and 334acd0 (both T1) and **f689820** (T2, BACKLOG.md only). Nothing is uncommitted and nothing is pushed.

**Steps**
- **R-14 (measured; no config line changed):** I forced `disallow_any_unimported` on in scratch copies of the three configs (S/u34/laneT/cfg_unimp/) and ran the six typecheck.sh mypy runs with a cold cache. Total: **4 findings, all in the host pass, all `[no-any-unimported]`.** The main, twin, bench conftest, network and conftest runs had 0 each.
  - scripts/_hardware_verdict.py:73 (`_Verdict` base `Summary`)
  - scripts/_hardware_verdict.py:131 (`_CollectionOnly` base `Summary`)
  - scripts/_hardware_verdict.py:136 (`_not_a_run` argument 1)
  - tests_hardware/manual/runner.py:46 (`_run_one` argument 2)
  - All four come from the bare sibling import `from _summary_block import Summary  # type: ignore[import-not-found]` (scripts/_hardware_verdict.py:22, tests_hardware/manual/runner.py:18), which R-4 routes to U37.
  - The forced flag does take effect in all three configs: a probe file outside the tree fails under each flagged copy and passes under each head config (S/u34/laneT/probe.log).
  - Logs: S/u34/laneT/unimp.{main,twin,host,bench,network,conftest}.log and unimp.times.
- **R-15 / step 24 (applied):** BACKLOG.md:1049-1063 is a new dated 2026-10-21 paragraph after U33's last one (the "Node on `PATH`" paragraph) and before "Kept here as the running list…". It has no audit IDs and names:
  - lint and typecheck legs: the CPY001 reason, the four removed pyproject baseline entries and `[mypy-http_client]`;
  - `scripts/test.sh` leg: the subset guard, test_third_party_attribution.py, test_vendored_freezefs.py ("not named in this list before"), host Python only, no new dependency;
  - CI only: the ci.yml Playwright keys, no chroot leg.
- **Step 3 (lane T's complete checks), all on the head:**
  - `scripts/lint.sh`: rc 0, 7 checks passed, 5.9 s.
  - `scripts/typecheck.sh`: rc 0, 10 checks passed, all six runs clean, 28.0 s.
  - 16 reader files plus decision_vocabulary, code_conventions and error_catalog (which covers the 12 pre-commit checks), each base then head in its own `unshare -n` process: all green on both sides except citations on the head.
  - The 17 scans in one process: base 874 passed; head 873 passed, 1 failed (the same citations finding).

**Red check, waiting on lane A's merge:** tests_scripts/test_citations.py:251 `unresolved citations … BACKLOG.md: tests_scripts/test_third_party_attribution.py`.
- The cause: lane A's new file is not on this branch. It exists, uncommitted, in S/wt-u34a. It should resolve once A is merged into audit/u34-int; the lead's tier run there confirms it.
- This contradicts P2.3's "no merge dependency" for this one check.

**Decisions**
- (agent, 2026-10-21) I kept the path cited, as the brief requires, rather than rewording it to slip past the check.
- (agent, 2026-10-21) I also named tests_scripts/test_ci_workflow.py, lane C's key check, under the `scripts/test.sh` leg. The brief's list did not include it, but it is a changed pytest-tier file that every other paragraph would name.

**Times (base → head):**
- decision_vocabulary 8.48 → 9.29 s (+9.6 %, under 10 %)
- citations 12.22 → 12.86 s (+5 %)
- 17 scans 77.05 → 79.06 s (+2.6 %)
- mypy_any_baseline 0.29 → 0.37 s (under 0.5 s)
- lint_ceilings 14.68 → 12.79 s; the rest are within noise
- Nothing is over 10 % and over 0.5 s.

**Other results**
- Memory: zero `MemoryError` and zero "memory allocation failed" in every log.
- Silent-failure scan: BACKLOG.md is a doc only, so no class applies in any mode (STA, AP, Silent, Off, USB), and the change has no runtime effect in any mode.
- Seen failing and bites: none (T2 adds no test). Relay lines: none. Allowlist rows orphaned: none.

**Runs (logged in RUNS.md):**
- u34/laneT/unimp.sh: exit 0. The host run's rc 1 is the 4 measured findings.
- u34/laneT/final.sh (pid 6874): exit 0; only the citations red above.
- Nothing of mine is running.
- I removed $W/.venv, $W/typings and $W/.mypy_cache with literal paths. The gitignored .ruff_cache and build/ stay.