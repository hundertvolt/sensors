# received 2026-10-15T07:23:49.606Z (subagent transcript agent-a7d120f57b3c76781.jsonl)
U27 lane B hand-back. All 8 blocks are done in commit f4f6a49 (S/wt-u27b, audit/u27-b, from 89b37a0); full detail is under "## B" in S/u27/relay.md.

Steps by verdict:
- Applied: blocks 1–8 (stripper and generator, buildgen and the caches, firmware build, website builds, gates, configs and toolchain, ci.yml's two U27 stages, the exit-idiom test).
- Verify rows: written nothing, as instructed.

Deviations (decided on the owner's behalf, for review):
1. host_typecheck.ini does not add `scripts` to mypy_path. With it, the host pass stops with "found twice: _summary_block and scripts._summary_block", because S and T import `scripts.<module>` dotted. build_firmware.py now imports `scripts._strip_type_checking` dotted, with no ignore.
2. The CI python check is two lines (`source …` then `require_python311`). With the `&&` form, a failed source would skip the check under bash -e.
3. The idiom test accepts `raise SystemExit(main(argv))`, e.g. the generator's `main(sys.argv[1:])`.
- Carried from earlier blocks: the manifest sorts through an `os.walk` patch; build_device_websites removes only staged pages; the stripped-image boot keeps the device module as .py; build_website.sh gains `--build-date`.

Seen failing first: every new or changed test was red on the prior code. Logs are in S/u27/laneB/red_*.txt, including red_exit_idiom, red_typecheck_sh and red_lit (the non-BMP string literal case). The new wrong-`--root` checker case was also run red first.

Red at hand-back, and who it waits on:
- test_host_cli_exit_idiom: T's `_archive_evidence.py:113`, `kick_then_reset.py:25`, `spoof_udp.py:64`; S's `_digital_twin_ci_suite.py:1731`, `record_twin_instrument_runs.py:153`.
- test_buildgen_source_ast (M's file), 2 cases: the lead applies S/u27/laneB/lead_source_ast_test.diff (it applies cleanly).
- test_decision_vocabulary / test_citations "only shrinks": the lead deletes `_decision_vocab_allowlist.txt` rows 129, 139, 413 and `_citation_allowlist.txt` rows 92, 96. T's `micropypath.toml` citation stays red until S adds the file it cites.
- test_shell_conventions and test_twin_never_needs_tests_on_its_path name only T's and S's scripts.

Checks:
- ruff clean over all eight scopes plus build/generated_src; shellcheck, actionlint and `zizmor --offline` clean.
- All six mypy runs are cold and clean, and the main pass is also clean with CI's paths.
- 9 of the 12 doc and convention checks are green, plus test_lint_type_scopes; the other three are the reds above.
- Unit files at −1 and 32768 have no memory marker. test_digital_twin_generated_boot has 22 passing. My refactor had made its source boots skip writing the module; I fixed that.

Silent-failure scan:
- /dev/null: test_typecheck_sh's stub uv appended to /dev/null in its two stub-install cases. I reported it to you at once and it is fixed.
- Also fixed: a gc checker run against a root with no src/*.py now exits 2 instead of passing.
- Left as is: a checker run with zero devices passes, though it prints "checked: 0".
- Left as is: build_firmware turns an unwritable `--output` (OSError) into a traceback.
- Pre-existing writes onto caller-given paths: `--output`, `--out`, and `rm -f` on build_frozen_html.sh's output.

Facts owed:
- S: run_generic_integration reads its module's source through `__file__`, so a compiled .mpy device module cannot boot there.
- T: toolchain_lock now names a shared holder: "a test run is using the Unix ports of <dir> …".
- X: doc lines for B.3, B.11, B.15, F.5.5, I.4(f.1), L.4, L.5, L.7, E.1/E.3, README, CLAUDE.md and tests_hardware/README, plus the BACKLOG lines (all in the relay).

After-times: none is more than 10 % over its base and over 10 s. The new files take 0.3–13.3 s.

Runs: all are logged in RUNS.md with their exits, and none of mine is running. typings symlink and scratch are removed.

