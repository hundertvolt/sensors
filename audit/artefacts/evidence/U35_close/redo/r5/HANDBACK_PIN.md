PIN hand-back, written by the agent (2026-11-10 16:13:34 UTC)

Worktree S/wt-pin, branch audit/pin from 3bee346e, one local commit 4242b1fd (not pushed). Newest stable re-queried today (PyPI, npm view, nodejs.org): same as W2's U01 table.
| moved | before | after |
| mypy, ruff, pytest | 2.4.0, 0.16.10, 9.1.1 | 2.4.1, 0.17.4, 9.2.0 |
| coverage (dev group + _render_coverage.py), zizmor, types-pyserial | 7.16.2, 1.30.1, 3.5.0.20260712 | 7.17.2, 1.32.0, 3.5.0.20261104 |
| uv required-version (uv.lock revision 3 -> 5; uv lock --upgrade also moved 5 transitives) | 0.8.17 | 0.13.7 |
| Node (.nvmrc, engines, devEngines, @types/node) | 24, 24.19.1 | 26 (26.13.0 Active LTS), 26.6.6 |
| npm lock (regenerated; 305 -> 236 entries) | vitest/@vitest 5.0.3, eslint 10.12.0, globals 17.13.0, html-validate 11.16.2, stylelint 17.16.0, -standard 40.0.0, playwright 1.63.0 | 5.1.0, 10.14.0, 17.14.0, 11.21.0, 18.0.0, 41.0.0, 1.65.0 (Chromium 158, rev 1254) |
Stayed (nothing newer): MicroPython + submodules, stubs, Microdot, freezefs, picotool, mpremote, shellcheck-py, actionlint-py, Actions. CLAUDE.md "Last run" untouched.
What each new version demanded, and where:
- ruff 0.17: ICN001 now aliases `datetime as dt` - 4 findings fixed at site (buildgen/model.py, scripts/record_twin_instrument_runs.py, tests_hardware/manual/manual_sensor_accuracy.py, tests_scripts/_toml_fixtures.py); select=ALL kept, no ignore added. Nothing else fired (TID254/TID255/RUF071 stabilised; target-version set).
- mypy 2.4.1, types-pyserial: nothing (283/309/58 files clean, no unused ignore). pytest 9.2.0: nothing; visit_BoolOp still in rewrite.py (pyproject comment re-stamped); new -m marker check: bench floor collects 210/250.
- zizmor 1.32: nothing; root-aware collection finds the same 6 inputs and the repo config. W32 stays (actionlint unchanged).
- uv 0.9-0.13 breaking notes read: none applies (0.12 script-relative discovery finds the same root). CI's uv-sync reads required-version; README recipe and the tree-care skill path re-stamped.
- Node 26 / npm: npm install could not resolve vitest 5.1.0 peers against the old lock -> regenerated from scratch (as 2026-10-06). Stylelint 18 + config 41 (migration guide read): no config change needed, no finding. ESLint 10.13-14: no new core rule. html-validate 11.18 presentation-role-style (in recommended): no finding. Every direct package's engines admit 26. W34 stays (coverage-v8 provider.js file selection unchanged 5.0.3->5.1.0, read not trialled); W36 stays (5.1.0 BrowserPage has no navigation). Vitest timeout message unchanged; SPEC's "pinned vitest" re-stamped.
- Playwright 1.65: CI's Chromium cache keys on package-lock.json, so CI installs 158 itself; no CI edit.
Records: audit/artefacts/ENV/dependency_refresh.md new section (table, notes, W32-W36, checks); BACKLOG build-env list: the 09-12 line made version-free, two lines added (Python tools+uv; Node+npm); README (Node pin, recipe uv), SPEC (vitest), pyproject comment, .claude tree-care skill.
Checks (own venv S/wt-pin/.venv, own uv/Node under ftmp_pin, run_pin.sh = run.sh copy): rebuild ok; lint_direct rc 0; mypy x3 clean; npm lint/typecheck/lint:css/lint:html/lint:html:built rc 0; npm test:unit 1,192/1,192 no retry; cross_browser_smoke Chromium 12/12 (WebKit/Firefox/Edge not installed, SKIP); pin-related pytest files 61 passed.
Gate under heavy.lock (pin, released): PICO_TOOLCHAIN_DIR=S/tc-c scripts/test.sh at -1 PASS, 120 files, 5,252 tests, tests_scripts 6,566 passed/6 skipped, retried 0, zero memory markers, 657 s. 32768 stage, twin legs and CI not run (brief).
Held back: nothing. Not bumped: CI's cross-browser engine cache suffix (engines unpinned by decision).
Decisions (agent, 2026-11-10): uv lock --upgrade per the family action (5 transitives moved); npm lock from scratch; Chromium 158 fetched from storage.googleapis.com (Playwright CDN 403 here), --version checked, then deleted for disk - local web tiers ran on the sandbox Chromium 153 fallback; tests_scripts/test_tool_pins.py's example literals (uv==0.8.17, ruff==0.16.10) left: regex inputs, not pins (W1a's file).
Sizes: no src/ or image input changed; generated modules equal int's but for _BUILD_DATE; no firmware built (brief), no module bytecode changed. Cost: no firmware operation changed.
Findings: (c) host disk at 1.7-2.5 GB free during this unit (3 GB rule; ~3.2 GB at its start); this unit still holds ~0.6 GB (ftmp_pin node 230M, uvcache 162M, uvenv 66M; wt-pin/node_modules 146M) - delete with the worktree.
(c) npm audit: 4 moderate, one chain, minimatch <=11.0.0 (GHSA-g3hv-75wg-m249) under eslint's @eslint/config-array ^10.2.4, already in the old lock; no fixed release in range, dev-only; recorded. The old stylelint braces chain is gone.
(c) the npm unit run read the Unix port from /root/pico-toolchain (shared lock, read only) before I set PICO_TOOLCHAIN_DIR=S/tc-c in my wrapper; the smoke and the gate used S/tc-c.
