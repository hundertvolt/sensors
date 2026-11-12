W2 hand-back, written by the agent (2026-11-10 15:42:56 UTC)

Worktree S/wt-w2, branch audit/w2 from 651af010, one local commit d7ac6018 (not pushed). No src/, buildgen/ or TOML line changed.
1 U01 (report only; nothing moved; queried git ls-remote / PyPI / npm / nodejs.org 2026-11-10):
  | pin | pinned | newest stable | move? |
  | MicroPython | v1.29.0 | v1.29.0 (v1.30.0-preview only) | no |
  | stubs board/stdlib | 1.29.0.post1 / .post2 | same, newest for 1.29.0 | no |
  | Microdot (ext/) | v2.7.0 | v2.7.0 | no |
  | freezefs (ext/) | main 26be9e33 | main 26be9e33 | no |
  | picotool | 2.3.1 | 2.3.1 | no |
  | pico-sdk / lwIP / cyw43 / mbedtls (MicroPython's submodules) | 2.3.0 / 2.2.1 / v1.1.1 / 3.6.6 | 2.3.1 / 2.2.1 / v2.0.0 / 3.6.7 | only with a MicroPython move |
  | mypy, ruff, pytest | 2.4.0, 0.16.10, 9.1.1 | 2.4.1, 0.17.4, 9.2.0 | would move: lint/typecheck/pytest gates (select=ALL, strict) |
  | coverage, zizmor, types-pyserial | 7.16.2, 1.30.1, 3.5.0.20260712 | 7.17.2, 1.32.0, 3.5.0.20261104 | would move: coverage job, workflow audit, host mypy |
  | mpremote, shellcheck-py, actionlint-py | 1.29.0, 0.11.0.1, 1.7.12.25 | same | no |
  | uv (required-version) | 0.8.17 | 0.13.7 | would move: uv.lock, the chroot recipe's uv, CI |
  | Node (.nvmrc major) | 24 (installer takes newest 24.x: 24.22.2) | 26.13.0 LTS | would move: .nvmrc, engines, @types/node, installer |
  | npm lock | vitest+@vitest 5.0.3, eslint 10.12.0, globals 17.13.0, html-validate 11.16.2, playwright 1.63.0, stylelint 17.16.0, -config-standard 40.0.0, @types/node 24.19.1 | 5.1.0, 10.14.0, 17.14.0, 11.21.0, 1.65.0, 18.0.0 (major), 41.0.0 (major), 24.19.2 | would move: website tier, CI Chromium |
  | Actions | checkout/setup-node/upload-artifact v7, cache v6 (major tags), dorny/paths-filter v4.0.3 | same majors, v4.0.3 | no |
  None reopens the image. CLAUDE.md's "last re-check, 2026-10-06" line NOT re-dated (pins would move, per brief); its MicroPython claim still holds today.
2 BACKLOG: P08 build-env bullet = noble satisfied 2026-11-07 (4 and 16 jobs, scratch in RAM), trixie's 11-07 run not satisfied (8 card-stall failures, not re-run, owner 11-07 words quoted), installer's single apt update+install (no wall-clock limit); also the lwIP-compiler line to both 11-07 legs (stale "only GCC 13.3 x86-64"). B40: bootloader 2 (not 4) and, same row, harness hard reset 21 (not 2) as bench/test_reset_reasons.py expects (agent, 2026-11-10: the row's second wrong code). N05: names the flash test and supervisor_scan_timing.py. README N03/U04(6): work-routines (+references/symptoms.md), bench-routines, tree-care added.
3 P06: README "## Release" + "### Changes from the legacy firmware": pins, the REST surface, new status keys/SystemCmd words, behaviour, corrections; each line checked against src/ (test names) and legacy/firmware/. Decisions (agent, 2026-11-10): wet-bulb cold-dry-corner line dropped (owner removed the corner 11-02, 82cbf08a), replaced by the true 5-99 %RH vs legacy 0.5 %RH line; ISL29125 line phrased against legacy (no autorange/peak rule there); "the boot order" left out (no user-visible fact found); key names corrected (TempOffset, PresOffset); Microdot v2.7.0 and legacy 482ab6d per THIRD_PARTY_LICENSES (the old CLAUDE.md copy is stale); Part N's 73 estimated rows one pointer line, not listed.
4 P05: NOT done - no release number from the lead by hand-back; version stays 2.0b0. Sites ready: buildgen/version.py, test_buildgen_version.py, mockdata/samples.json, SPEC L.7 (no release paragraph yet), README Release's first sentence.
5 P04+S03: 6+6 fixtures committed (tests_scripts/golden/<device>.json, tests_scripts/fixtures/api_reference/<device>.json); both tests compare and name "PYTHONPATH=. uv run python tests_scripts/test_<x>.py --regenerate" (plain uv run lacks buildgen on sys.path). Seen red: 12 failures with no fixture; green; red again on a planted key change in each dev fixture (2 failures), restored. SPEC C.5/A.8 updated. The three files had no _PENDING entries and no function-level imports: nothing to drop. S03's two prefixes now name real paths (test_no_variant_literals green). Fixtures carry field names only: the Wi-Fi fallback literal appears in none (AST check printing paths/counts only).
Checks: touched-file readers 14 files green; ruff clean; host mypy 309 files clean; under heavy.lock (w2, released): rebuild ok, lint_direct rc 0, tests_scripts 6562 passed 1 failed 9 skipped.
  The 1 failure: test_twin_process_spawn long-launch-string, "FATAL: uncaught NLR" from S/tc-int's build-standard, built from an older micropython_overrides.py (dc3b9251 vs tree 80997ab1, the two-byte qstr lengths); green against S/tc-c (2 passed). Class (c): common_r1's tc-int is stale for that test.
Sizes: dev imageFreeBytes 71,188 B (tc-int and tc-c alike) = 651af010's, no image input changed; no module bytecode changed.
Cost: no operation of the firmware changed.
