C1 hand-back (lane C, final block). Commit `0f55912` on audit/u34-c in S/wt-u34c (from 147ea3f, rebuilt with S/u23/rebuild.sh, rc 0). Nothing pushed. Nothing left uncommitted.

Steps:
- OF-208 (R-8): applied. The four Playwright caches (web-unit-tests, web-put-matrix, web-coverage, web-cross-browser-smoke) now each have an identity step before them. Its name, id, shell and run text are identical to `.github/actions/setup-micropython-toolchain/action.yml`'s `id: ident` step. Each key is now `playwright-chromium-${{ runner.os }}-${{ steps.ident.outputs.id }}-${{ hashFiles('package-lock.json') }}`. The web-unit-tests cache comment now names the new key input (a stated meaning change, recorded in the commit). The Firefox key is unchanged, per P2.1.
- Step 21 (TOOL.020): checked only, already landed. checkout@v7 ×16, setup-node@v7 ×8, cache@v6 ×6, upload-artifact@v7 ×6. These are the newest majors by `git ls-remote` (v7.0.1, v7.1.0, v6.1.0, v7.0.2). dorny/paths-filter `ceb8a2b…` = v4.0.3, the newest tag. Local `./` uses stay (actionlint 1.7.12; zizmor.yml keeps self-repository disabled). No `submodules:` or `fetch-depth`. `gh api` was refused (403), so `git ls-remote` was used instead.

Tests and bites:
- Seen failing first: the new `test_every_playwright_cache_keys_on_the_runner_identity_the_toolchain_action_computes` failed at base on all four jobs. Each job reported two lines: "key misses `${{ steps.ident.outputs.id }}`" and "no identity step … before its Playwright cache". Log: S/u34/laneC/seen_failing.log.
- Bites (scratch copy, now removed): five plants, each failing with the right message:
  - an identity run line differing in one job;
  - the identity step moved after the cache;
  - the id renamed to `identity`;
  - one key without the identity;
  - no `~/.cache/ms-playwright` at all (the floor).
- New private helper `_step_lines` and constant `_IDENT_ID` in tests_scripts/test_ci_workflow.py. The header docstring is still 3 lines.

Checks on the head (all green):
- lint.sh's passes run one by one (ruff over the eight scopes plus build/generated_src, shellcheck, actionlint, zizmor `--offline`, method-assign guard, gc sites): all rc 0. zizmor shows 15 suppressed, the same as base. lint.sh itself refuses to run without a `.venv` in the worktree, hence the split.
- Host mypy pass (host_typecheck.ini, cold cache): no issues in 305 files.
- C's readers:
  - test_ci_workflow: 18 passed;
  - test_build_firmware: 53 passed, 6 skipped (the opt-in `RUN_SLOW_FIRMWARE_BUILD` builds);
  - test_js_coverage_report_dir: 3 passed;
  - test_lint_type_scopes: 8 passed;
  - test_uv_sync_retried_sh: 7 passed;
  - test_test_sh: 190 passed, started with 3 heavy processes on the host.
- The 17 repo scans plus code_conventions, error_catalog, lint_ceilings and mypy_any_baseline, in one process: 965 passed. The 1 warning is the uninitialised datasheets submodule, as at base.
- Zero MemoryError and zero "memory allocation failed" in every log.

Times (test_ci_workflow.py, base and head alternating, 3 rounds): base 0.39/0.36/0.38 s, head 0.80/0.61/0.39 s wall (pytest's own figures 0.07-0.12 against 0.10-0.26 s). The largest gap is 0.40 s, under the 0.5 s bound.

Silent-failure scan (both files, all classes):
- New and closed: a key that reads the identity before its step has run gets an empty value and silently falls back to the old key without it (class 3/6, host/CI mode). The new test now checks the step order.
- Inherently safe: a missing `gcc`/`ldd` or an unset `ImageOS` changes the hash. The result is a cache miss, never a stale restore (class 4).
- Checked, no finding: setup-node's npm cache, which holds platform-independent tarballs; the Firefox cache, covered by its recorded decision.
- Per mode: STA, AP, Silent, Off and USB are all unaffected. This is CI-only; the firmware and website bytes do not change.

Facts owed:
- To N2 and the lead: SPECIFICATION.md B.10.1 still says "Playwright's browser is cached keyed on `package-lock.json` (which pins its version)". It should now also name the runner identity (image, compiler, C library) that comes from the toolchain action's identity step.
- To T2: ci.yml did land, so it belongs in the chroot-list paragraph (CI only, no chroot leg).
- No allowlist row is orphaned. No relay line was written, since my brief names none.
- Expected: the first CI run downloads the Playwright browser once.

Runs: one background run, S/u34/laneC/run_checks.sh (pid 18348), rc 0, with its RUNS.md start and exit lines written. Logs are in S/u34/laneC/. Nothing of mine is running.

Decisions: none beyond the rulings.