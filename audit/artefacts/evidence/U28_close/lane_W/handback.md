U28 lane W hand-back. Commit 083bc49 on audit/u28-w (base b1fecfb). Not pushed. 18 files changed, all in files_W.txt. tests_js/_twin_process.js is untouched because no export was missing.
Steps: all applied. 129/133/113: engineVerdict, the flag, and the closing line that counts skipped engines. 130: shared twin frame, startVirtualDisplay with -displayfd, Chromium fallback rule. 115/127: the installer. 64/97/112: the preview server. 128/135: the tsc base and the .ts declarations. 111/134: config headers. OF-140: closed in code (below). 77/80/85: the Playwright step. L0 PTH105×3 and PTH211×3: fixed. Verify rows 75, 76, 110 and 147 are yours (lead).
Deviations:
(1) The smoke's :196 stopProcess survives as stopHelper, used only for the drivers and Xvfb. The twin stops through stopTwin. Its fallback timer is now cleared; it used to hold Node's event loop up to 15 s after a pass.
(2) The driver wait is now pollUntil plus driverAnswers(), which names a dead driver; this replaces :119. READY/SHUTDOWN timeouts are imported from _twin_process.js.
(3) Declarations: getLiveMatrixConfig stays {shard}, since the module returns no reason. applyField.field is the module's DisplayField. defaultDecimals stays `number | undefined` because callers pass undefined.
(4) The micromamba download goes to <bin>.part beside the binary so the rename is atomic. An older unverified binary is re-hashed and fetched again.
(5) The Edge fingerprint comes from the key itself. The publication page learn.microsoft.com answered 403, so the cross-check against Microsoft's published value is unfinished.
Seen-failing-first:
- probe test :130 "no export engineVerdict" ×5, and flag test :182.
- installer test: 13 red at b1fecfb (apt options, Xvfb ×3, key ×3, micromamba ×4, temp ×2). The temp guard was also bitten in scratch: no trap fails :259, a kept .part fails :260.
- preview test: red (no file).
- html_validate test :55 at b1fecfb's config, run in scratch.
- test_setup_toolchain_env.py :787, :796, :808: DID NOT RAISE.
- tsc bite: a type error in the .ts gives TS2322; the same error as .d.ts gives no error.
- startVirtualDisplay scratch run: displays :0/:1/:2 distinct; an early exit quotes Xvfb's stderr.
Other checks:
- Trials: skipLibCheck false gave third-party errors only (vitest 3, playwright-core and @vitest/browser 173), so it stays true. isolatedModules and erasableSyntaxOnly were clean and are on. isolatedDeclarations conflicts with allowJs; noPropertyAccessFromIndexSignature contradicts ESLint dot-notation (344 sites). Both are named in the base header.
- npm lint, typecheck, lint:html: clean. lint-ceilings: 4/4, no maximum moved. A quick vitest file starts its browser under the new options. shellcheck, ruff (current and R1's pyproject) and host mypy cold: clean.
Red checks:
- test_citations.py:251 (BACKLOG.md:571/:744 cite vitest-commands.d.ts) and test_tunables_register.py:253: wait on X (rows in the relay).
- test_comment_block_cap.py:273 (delete the eslint.config.js and vitest.config.js rows at :43) and test_decision_vocabulary.py:94 (one of the three identical smoke rows at _decision_vocab_allowlist.txt:136-138 is stale): wait on the lead (R-10).
- test_live_command_device_args.py:115: the file is in no lane's set, so it waits on the lead. The smoke now boots through spawnTwin; the fix text is in the relay.
Scan (my files, all classes):
- New, fixed here: an engine that never ran read as a pass (class 4); a display another process holds (class 3, the old lock-file readiness); a kept HTTP error body and an unchecked key or binary (class 1/4, installer :44/:65); a preview serving the repo root on every interface (class 7); env reporting ready without a browser (class 4); a dead driver waited out, and the pending stop timer (class 5); the unchecked .d.ts (class 3).
- New, parked: a Microsoft keyring an older run wrote stays when Edge is already installed (class 1, installer Edge branch). No step owns it.
Owed:
- C: ci.yml `node scripts/cross_browser_smoke.mjs --require-all-engines`; the web filter `'tsconfig*.json'` so the base file triggers; the installer changed, so the Firefox key rolls once; preview_server.py answers --help if test_tool_help TOOLS should list it.
- X: SPEC H.2/H.7/H.8, README, tests_hardware/README bench note, BACKLOG citations and the W line, Part N rows, all in the relay.
- R: none.
- Lead: CI-only proofs. These are the engine legs with the flag, the -displayfd display on the runner, the Edge key check and micromamba fetch on a clean runner, and the browser under the pinned build. Plus the R-10 rows and :115.
After-times beyond 10%: test_setup_cross_browser_toolchain_sh.py 0.80 s, re-timed 0.68 s with 2 heavy processes, against a base of 0.44 s. It went from 4 tests to 17 bash runs; the real tools are now symlinks. The others are under base or new: probe 1.66 (base 1.71), env 3.34 (base 4.93), preview 0.41, html_validate 0.64.
Runs: rebuild.sh rc0; the two Xvfb probes and four scratch node runs rc0; stage-only to scratch rc0; vitest twin-start-failure and lint-ceilings rc0; the 12 checks rc1 (the reds above, logged in RUNS.md after the fact); tier pid 31099 rc1 (121/131/109/171 s, the five reds above, 6 skips that were already there); after-time runs rc0. Nothing of mine is running. Logs and the relay entry are in /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u28/laneW/ and /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u28/relay.md under "## W".
