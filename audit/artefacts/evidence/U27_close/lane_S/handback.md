# received 2026-10-15T07:44:37.834Z (subagent transcript agent-a170ccaa7e1fba587.jsonl)
U27 lane S done. Commit c8c44e4 on audit/u27-s (based on 89b37a0, 22 files). Worktree is clean, nothing of mine is running, and every run has a done line in RUNS.md. The relay is under "## S" in S/u27/relay.md, inserted between "## S" and "## M" (an in-place edit, not an append at the end).
Steps: 1 shared frame done. 2 suite done. 3 harness and runner done. 4 both twin runners done, plus the new test_run_digital_twin_ci_sh.py. 5 JS frame and smoke done, with deviations below. 6 Timer drop knob done; the SGP40 walk is unchanged because the datasheet gives only −870 ticks per doubling and no per-sample step (R-12, measurement parked to R1). 7 idiom done. D.15 order is the last edit to every edited module.
Deviations (each agent, 2026-10-15, in the commit message):
(a) tests_js/_micropypath.js is a pure parser (LAYOUT_FILE, twinLayout, withSite) and _twin_process.js reads the file. Its vitest case runs in the browser, so it follows the _memory_markers.js precedent and stays out of eslint's Node list and tsconfig.node.json (steps 197/198 not applied). Both tsc passes still reach it through imports.
(b) The uart scenario's free-block floor (2×16,384 B) is asserted at 32768 only (752-789 KB there). At -1 the largest block was 11,872-30,080 B out of 870 KB free, so it is printed, not asserted.
(c) Run 9 ends on the third NTP failure plus one supervisor pass, because the 10 s doubling backoff makes five failures in 90 s impossible.
(d) The smoke keeps its own spawnTwin, as test_live_command_device_args requires; it gets only the probe, the layout and the port-53 lock.
Seen failing first (detail in S/u27/laneS/sff.txt): errcount 8 red (no wdt/gc fields, no GC-summary check, no feed_gap_verdict, no starves kwarg); runner L1 5 red; flags 1; scenarios 2 (feed gap, held 53); ceiling 2 (_get_routes, routes); soak 9; run_digital_twin_ci_sh 8; micropypath.test.js import failed; Timer knob L1 3 red. Bites in a scratch copy (Run 10 wait, Run 10 exemption, warm-up, runner guards, knob ×2) all caught. OF-147 grep went from 2 hits to 0. A planted port-53 holder made the smoke exit 1 naming it.
Red checks:
- test_citations test_the_allowlist_only_shrinks: _citation_allowlist.txt rows `scripts/run_digital_twin_ci.sh	src/sensortask_*.py` and `scripts/run_unix_port_integration.sh	src/sensortask_*.py` (lead).
- test_no_variant_literals: the _NOT_YET_CLEANED entry for scripts/_digital_twin_ci_suite.py is now clean (lead).
- test_tunables_register: no Part N rows yet for l2.feed_gap_share_max, l2.ntp_unreachable_failures, l2.soak_plateau_cycles, l0.run_digital_twin_ci_sh_timeout_s (X).
- test_port_lock.py 5 red (T): its sandbox needs scripts/_devices.sh and _unix_port.sh, and run_digital_twin_ci.sh's first uv call past the locks is now the archive.
- test_twin_never_needs_tests_on_its_path: test_digital_twin_generated_boot.py:361 (B) and test_tool_help.py:104 (T).
- test_shell_conventions 12 reds, none in my scripts (T/B).
Lead: host_typecheck.ini's [mypy-scripts._digital_twin_ci_suite] baseline is unused; the cold pass without it finds 0 issues in 276 files.
Scan findings:
(1) The twin's free-block figures are not the silicon's (1.2 MB live in the twin vs the board's 88 KB graph); no after-load reading exists on silicon (parked to hardware).
(2) The Timer knob is reached only at L1. The product's ONE_SHOT sites (asy_system_service.py:327, :701; asy_ntp_client.py:282) have no twin scenario that drops their fire, so their recovery is unchecked. This is an A-C delta for the next unit holding the harness.
(3) The JS frame's `check` compares only the flavour, so a binary with a stale record passes the live tier until U28's ensure steps.
Never-started twin, missing or empty log, held port and both GC stages are covered. Remaining checks are green: ruff, the 4 mypy passes cold, shellcheck, npm lint/typecheck, lint-ceilings, and 10 of the 12 doc checks.
After-times over 10 %: test_digital_twin_ci_suite_errcount.py 0.76-0.85 s vs 0.73 (16 new cases). Everything else is within 10 % or faster (ceiling 2.98→0.62 s); the full list is in the relay.
Time saved per stage on dev: Run 9 about 15-20 s, Run 10 about 2 s, Run 11 about 70 s (84/63 cycles vs 120). The hung-step scenario's S1 now ends on HUNG S1 (99.6/111.5 s).
Runs, all rc 0 with zero memory markers: live-backend 237 s (18 passed); put-matrix 765 s (348 passed, 6 skipped as at base); Runs 1, 6-9, 10, 11, 11b; harness uart ×2 stages (the first -1 run failed on the floor, deviation (b)) and hung-step ×2 stages; L1 machine and runner at both stages.
/dev/null: my shell writes into it were reported to main; one more later (`ls … >/dev/null`, two path lines). Pre-existing "wozi" literals remain in tests/test_digital_twin_machine.py `_wire()` and tests/test_digital_twin_run_generic_integration.py:215 (lead).

