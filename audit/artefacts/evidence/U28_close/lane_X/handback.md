U28 lane X: commit 253ae85 on audit/u28-x (based on 1e4c743). Only my 6 files are changed. Setup: lock_check rc 0; rebuild.sh rc 0.

Steps written: all 24, each limited to its U28 part. M.SPEC.126 verify: nothing written.
- Lead fix: BACKLOG lines 571 and 744 now point at `tests_js/vitest-commands.ts`. Each is described as the command declarations file as it is today. No allow-list row added.
- SPEC: A.3, A.6, B.10, B.10.1, D.6, F.5.5, L.5, E.1 (R-18, tagged agent 2026-10-19), E.5, H.2, H.7's cross-browser section, H.8.
- Part N: 5 new rows (ci.devices_timeout_min, ci.last_green_lookup_timeout_s, ci.playwright_install_timeout_min, runner.unix_port_probe_timeout_s, l0.smoke_display_ready_timeout_ms). Sites updated for tool.apt_acquire_timeout_s, tool.uv_sync_attempts, tool.uv_sync_backoff_step_s and the two l0.live_twin rows. Budget rows unchanged.
- I also wrote the relay's owed SPEC lines: E.5.2 (probe bound), B.15 (CI mypy with no arguments, test_config_paths_resolve.py) and C.8 (the twin cancelled-session case).
- R-5 is in D.6's host group with actor, date, the question, the options and both owner quotes, and is quoted in the commit message. No BACKLOG owner-question entry.
- README, CLAUDE.md (only the five sentence groups the brief names), BACKLOG (the chroot paragraph by leg plus two hardware rows), tests_hardware/README.md and the UART changelog row B78 (Class B) are done.

Where the relay and the tree differ (I wrote what the tree shows):
- The flash and bench runners call uv_sync_retried.sh after their lower levels, not first. The docs say "before its hardware step".
- `build/generated_src/**` exempts only PLW0603 and S104 (plus E402/F401/T20 on the boot entries), not src/'s whole set.
- The tree also edits tests_hardware/bench_control.py (a code change: contextlib.suppress) and website_identity.py (a comment). Neither is in plan §7's R1 list; I added both to the BACKLOG row.

Meaning changes (each listed in the commit message for owner review):
- CLAUDE.md retry bullet: the owner's 2026-09-26 tag moved to the head sentence, as the packet planned. The incident account and the "!cancelled() edge" clause are dropped.
- B.10.1 unit-tests: the measured minutes leave B.10.1; Part N's row already holds them. The coverage figures 14m01s/16m56s stay in B.10.1, because the Part N row lacks them.
- README: dropped "which keep gating on Python paths exactly as before", which was false.
- H.7: "CI always installs all three" now reads as the enforced `--require-all-engines` flag.

One red check, waiting on the lead: test_decision_vocabulary.py::test_the_allowlist_only_shrinks. The row to delete is `tests_scripts/_decision_vocab_allowlist.txt:14`, "CLAUDE.md	- **A third party's momentary outage must never read as a red test result.** `sc" (that sentence was rewritten and is now tagged). Everything else is green: citations, tunables_register, comment_block_cap, legacy_paths, import_placement, code_conventions, error_catalog, host_annotations, lint_ceilings, mypy_any_baseline, memory_error_gate_agreement, level_containment, uart_changelog, lock_order, device_script_bench_facts, ci_workflow.

Facts owed to the lead (not written, because the brief limits CLAUDE.md to its five sentence groups):
- (a) CLAUDE.md's chroot recipe still runs `pip install --break-system-packages uv` (unpinned). required-version "==0.8.17" refuses any other uv, so the owner's chroot leg fails at `uv sync`. The fix is `"uv==0.8.17"`. In the meantime, the BACKLOG chroot paragraph tells the run to pin it.
- (b) CLAUDE.md's `--coverage` bullet still says the Cobertura XML uploads to Codecov.
- (c) The relay owes more CLAUDE.md lines: the "Wired into CI" job list (add `devices`), the uv.lock merge bullet (test_tool_pins.py), `tsconfig*.json` in the config-header list, and D100/D104 now enforced.
- (d) A.6, README and CLAUDE.md state that datasheets/ is a submodule (R-15). That is true only after your move at <W2>.
- (e) The BACKLOG gated-round row lists the persistence-gated files from their markers; please confirm that list from the lanes' diffs.

Silent-failure scan: these are docs, so there is no code site. One finding, new: (a) above, mode "twin and tooling / build environment". It is parked through BACKLOG.

Runs: run_checks.sh in four batches (base, r1, r2, final), each file in its own namespace at nice 19, no failure I could not explain. Only r1 took over a minute (72 s); it is in RUNS.md with done rc=1 (the allow-list row). Nothing of mine is running. Logs are in u28/laneX/.
