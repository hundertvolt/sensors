# A-C merge TOOL (HEAD 263cd06)

Scope: CLUSTERS.md "## TOOL" — `.github/actions/setup-micropython-toolchain/action.yml`, `.github/actions/uv-sync/action.yml`
(new, A.U28.01), `.github/workflows/ci.yml`, `.github/zizmor.yml`, `pyproject.toml`, `toolchain/micropython_overrides.py`,
`toolchain/setup_toolchain.py`, `toolchain/versions.toml`, `uv.lock`. Every file read in full at HEAD. Action set: the
site index plus a grep of `audit/actions/*.md` for each path (219 actions name one of the nine files; each was read and
classified — constituent, blast-only or mention-only — in the Ledger) plus U28's closing inventory (`U28.md:1279-`),
which adds the CI-duty actions the path grep cannot see (A.U7.10, A.U27.14, A.U27.38, A.U25.37, A.U25.55, A.U25.74,
A.S0930.04, A.S0930.27, A.U26.75, A.U27.39, A.U27.31, A.U7.12).

Dependency refresh (OR129, LEAD/R33, `SUPP_deps.md`): every pin these files hold — `versions.toml` `ref` and the new
`[stubs]`, the `pyproject.toml` dev pins and `[tool.uv] required-version`, `uv.lock`, the `actions/*` tags, the dorny
commit — moves in U0 after the B0 baseline (A.SDEP.01 order: Python tools, then Node, then Actions, then MicroPython and
stubs) and is re-checked in U37 (A.SDEP.25). Every merged change below that cites a pinned upstream line carries
"re-check against the refreshed pin" (A.SDEP.23): the executor maps each `v1.29.0` citation to the new tag before
landing it, and permanent text cites the new tag's lines.

Staging convention: a change lands in the unit of its latest constituent; an earlier stage is written only where an
earlier unit needs the intermediate state (named per change). Tag lines are `# @tunable <id> = <literal>` directly above
the line holding the literal (A.U8.02 grammar); tag lines are exempt from the comment cap, the prose around them is not.

## .github/actions/setup-micropython-toolchain/action.yml

### M.TOOL.001 Toolchain action: uv-sync first, identity-keyed cache, build input
- **From**: A.U21.07 (third hashed file + comment), A.U28.04 (header, input, identity step, key, build step), A.U28.01
  (3) (the two sync steps become `uses: ./.github/actions/uv-sync`), A.U28.42 (line-1 header comment), A.U27.12 (the
  build step's body), A.SDEP.05 (`actions/cache` tag refresh), A.SDEP.19 (W32 `uses:` form; W33 reason text), A.SDEP.08
  (blast: a pin move busts the key — expected, no edit). Dropped: A.U8.14's two tag sites in this file (`:25` loop head
  `3`, `:28` `sleep $((attempt * 10))`) — A.U28.01 removes both lines; the tags move with the loop to
  `scripts/uv_sync_retried.sh` (SCR, A.U28.01 (1)).
- **Site**: `.github/actions/setup-micropython-toolchain/action.yml:1-38` (whole file).
- **Change**: end state, in order:
  line 1 comment `# Restores (or builds) the cached MicroPython Unix-port toolchain after the retried uv sync - used by
  nine CI jobs (SPECIFICATION.md B.10).`; `name: Setup MicroPython toolchain`; `description:` (three lines) "Runs the
  retried uv sync, restores the Unix-port toolchain cache under ~/pico-toolchain and, with `build-unix-port: 'true'`,
  builds it when missing. Used by web-unit-tests, web-put-matrix, web-coverage, web-cross-browser-smoke, unit-tests,
  unit-tests-gc-threshold, unit-tests-coverage, digital-twin-e2e and firmware-build-verify."; `inputs: build-unix-port:`
  `required: false`, `default: 'false'`, `description: Build the Unix-port toolchain when the restored cache lacks
  build-standard`; `runs: using: composite`; steps: (1) `- uses: ./.github/actions/uv-sync` (first, so every caller syncs
  before anything else); (2) `- name: Runner and compiler identity for the cache key`, `id: ident`, `shell: bash`,
  `run: printf 'id=%s\n' "$(printf '%s\n' "${ImageOS:-unknown}" "$(gcc --version | head -n1)" "$(ldd --version | head
  -n1)" | sha256sum | cut -c1-16)" >> "$GITHUB_OUTPUT"` (the executor confirms `ImageOS` on GitHub-hosted runners);
  (3) `- name: Cache MicroPython Unix port build`, `uses: actions/cache@<refreshed major>`, `path: ~/pico-toolchain`,
  comment (≤ 3 lines) "Every input compiled into the cached binaries: pin, build flags, build overrides, runner image,
  host compiler and C library (SPECIFICATION.md B.10).", `key: unix-port-${{ runner.os }}-${{ steps.ident.outputs.id
  }}-${{ hashFiles('toolchain/versions.toml', 'toolchain/setup_toolchain.py', 'toolchain/micropython_overrides.py') }}`;
  (4) `- name: Build the Unix-port toolchain if the cache lacks it`, `if: inputs.build-unix-port == 'true'`, `shell:
  bash`, `run: scripts/_unix_port.sh ensure standard` (the input never enters the script text). No retry loop and no
  `pip install uv` remain in this file. W32 (A.SDEP.19, decided in U0): when the refreshed actionlint accepts `uses:
  $/.github/actions/…`, step (1) uses that form, like every local `uses:` (M.TOOL.020); otherwise `./`.
- **Resolved**: A.U21.07 and A.U28.04 edit the same `key:` line — one edit, A.U21.07's file list inside A.U28.04's key
  (both actions say so). A.U28.04's interim body (`[ -x "$bin" ] || uv run toolchain/setup_toolchain.py setup`) vs
  A.U27.12's command — A.U28.04: "Once A.U27.12 lands, the body is its command form … (A-C keeps that body)"; U27 < U28,
  so the body is written once as A.U27.12's. A.SDEP.19 (W33) reason text and A.U28.01 — one reason, in the uv-sync
  action's header (A.SDEP.19 Depends: "A-C keeps one"); the HEAD comment `:19-21` goes with its steps.
- **Unit**: U28. Stages: U0 — `actions/cache@v6` → the refreshed major (A.SDEP.05) and, if W32 says yes, the `uses:`
  form; U21 — the key's file list gains `'toolchain/micropython_overrides.py'` and the comment becomes "Hashes every file
  whose content is compiled into the cached binaries: the pin, the build flags and the build overrides (SPECIFICATION.md
  B.10)." (A.U21.07): U21 changes what the overrides compile (A.U21.06/.09/.12), and CI must not serve binaries built
  from older overrides through U21-U27, the staleness B.10 records; U28 — the rest.
- **Depends**: M.TOOL.002 (the uv-sync action); A.U27.12 (`scripts/_unix_port.sh`, SCR); M.TOOL.020 (W32 form).
- **Blast carried by**: the nine callers' steps → M.TOOL.007-.010, .013-.015, .017, .018; SPEC B.10 `:850-853` key
  sentence → A.U28.37 (SPEC, merging A.U21.07's text); A.U28.08's key/header/no-repeat checks → A.U28.08 (TSC); BACKLOG
  chroot list → A.U28.38 (DOCS); lint gates actionlint, zizmor (`--offline`).
- **Kind**: code

## .github/actions/uv-sync/action.yml (new)

### M.TOOL.002 New uv-sync action: pinned uv, one retried locked sync
- **From**: A.U28.01 (2) (the action), A.U28.42 (line-1 header), A.U28.02 (the uv pin it installs), A.U27.10 (the bare
  `python3` checked first), A.SDEP.19 (W32 form; W33 reason text kept here once), A.U28.43 (a caller).
- **Site**: new `.github/actions/uv-sync/action.yml`.
- **Change**: line 1 `# Installs the pinned uv and runs the one retried uv sync --locked - used by every CI job that needs
  the Python environment (SPECIFICATION.md B.10).`; `name: uv sync (retried)`; `description:` "Installs the uv version
  pyproject.toml's [tool.uv] required-version pins, then runs scripts/uv_sync_retried.sh: a third party's build-time
  download (actionlint-py fetches its binary) must not read as a red run (owner, 2026-09-26). Used by lint-and-typecheck,
  shellcheck, actionlint, zizmor, web-lint-and-typecheck and, through setup-micropython-toolchain, nine more jobs.";
  `runs: using: composite`; step "Install uv (pinned in pyproject.toml)", `shell: bash`, `run: source
  scripts/_require_python.sh && require_python311 && pip install "uv==$(python3 -c 'import tomllib;
  print(tomllib.load(open("pyproject.toml", "rb"))["tool"]["uv"]["required-version"].removeprefix("=="))')"`; step "Sync
  dev dependencies (retried)", `shell: bash`, `run: scripts/uv_sync_retried.sh`. No `${{ }}` in either `run:`. The W33
  sentence (A.SDEP.19): if the refreshed `actionlint-py` ships its binary in a wheel, the description's example names
  whichever third-party download still happens at sync time; the retry stays either way (CLAUDE.md "Don't simplify the
  retry away").
- **Resolved**: A.U28.01's step text and A.U28.42's header — one file, both applied. The uv version: A.U28.02 pins
  "the uv version `uv --version` reports in the B0 environment"; AC_NOTES 38 (U28 applied) "execution pins the uv version
  current at B0"; A.SDEP.03 records uv before and after the refresh and A.U28.02 "pins it from this refresh's version".
  Settled by OR129 (owner, 2026-09-30, the most recent row): the pin is the uv version the U0 refresh ends with, recorded
  in A.U0.06's post-refresh environment column (A.SDEP.20).
- **Unit**: U28.
- **Depends**: A.U28.02 (`required-version`, M.TOOL.024); A.U27.10 (`scripts/_require_python.sh`, SCR); A.U28.01 (1)
  (`scripts/uv_sync_retried.sh`, SCR).
- **Blast carried by**: callers M.TOOL.001, M.TOOL.006, M.TOOL.011, M.TOOL.012; `tests_scripts/test_uv_sync_retried_sh.py`
  (no second retry loop in `.github/`, the sync before `scripts/test.sh`) → A.U28.01 (TSC); A.U28.03 (4) no second uv
  version literal in `.github/**` (the pin is read, never written here) → A.U28.03 (TSC); CLAUDE.md retry bullet →
  A.U28.10 (DOCS); SPEC B.10/B.10.1 → A.U28.37 (SPEC); lint gates actionlint (a local composite inside a composite),
  zizmor.
- **Kind**: code

## .github/workflows/ci.yml

### M.TOOL.003 Open the workflow with its header block
- **From**: A.U28.42 (ci.yml part), A.U27.28 (5) (hands the config headers to U28).
- **Site**: `.github/workflows/ci.yml:1` (before `name: CI`).
- **Change**: a first comment block, before `name: CI`: "# CI: every lint, type, test and build check as its own job;
  web jobs gate on web-changes, the per-device jobs read devices. Why each job is shaped as it is: SPECIFICATION.md
  B.10.1." (≤ 3 lines). The trigger comment `:3-5` stays below `name: CI`.
- **Resolved**: —
- **Unit**: U28.
- **Depends**: M.TOOL.016 (the `devices` job the header names).
- **Blast carried by**: A.U27.28's header check drops `ci.yml` from its pending set → A.U27.28 (TSC).
- **Kind**: code

### M.TOOL.004 Concurrency and permission comments state the new base and token scope
- **From**: A.U28.07 (5) (concurrency comment), A.U28.07 (1) blast (web-changes gains `actions: read`; agent decision
  D11: the top-level permissions comment follows).
- **Site**: `.github/workflows/ci.yml:11-12` (concurrency comment), `:17-18` (permissions comment).
- **Change**: `:11-12` → "# Shared by both triggers (head_ref on a PR, ref_name on a push name the same branch), so
  cancel-in-progress keeps one run per push; which one survives does not matter, since web-changes compares against the
  last green commit." `:17-18` → "# Deny-by-default GITHUB_TOKEN; each job grants itself contents: read, and web-changes
  alone adds actions: read to find the last green run (B.10.1, enforced by zizmor)." (each ≤ 3 lines). `permissions: {}`
  unchanged.
- **Resolved**: — (A.U28.07 makes "nothing needs more" false; the comment is corrected in the same change, CLAUDE.md
  "docs hold current state").
- **Unit**: U28.
- **Depends**: M.TOOL.005.
- **Blast carried by**: SPEC B.10.1 `web-changes` bullet → A.U28.37 (SPEC).
- **Kind**: code

### M.TOOL.005 web-changes: last-green base, every input, dorny at a v4 commit
- **From**: A.U28.07 (base step, `actions: read`, filter list, output fallback, `:38-40` comment), A.U6.12 (`src/**`,
  `buildgen/**`, `devices/**`), A.U28.13 (dorny re-pin), A.SDEP.05 (executes A.U28.13 in U0), A.U28.25 (blast:
  `'tsconfig*.json'` replaces the two tsconfig lines), A.U8.15 (tag on `timeout-minutes`, M.TOOL.019), A.SDEP.05
  (checkout tag, M.TOOL.020).
- **Site**: `.github/workflows/ci.yml:22-57` (`web-changes`).
- **Change**: job comment `:23-24` kept. `permissions:` `contents: read`, `actions: read` with the comment line "# reads
  this workflow's run list to find the base below; nothing else". `outputs: web: ${{ (github.event_name == 'push' &&
  steps.base.outputs.sha == '') && 'true' || steps.filter.outputs.web }}` with the comment "# No green run to compare a
  push against: run the web tier rather than guess (B.10.1)." Steps: checkout (unchanged, `persist-credentials: false`);
  new step `- name: Last commit CI passed on this branch`, `id: base`, `if: github.event_name == 'push'`, `env: GH_TOKEN:
  ${{ github.token }}`, `REPO: ${{ github.repository }}`, `BRANCH: ${{ github.ref_name }}`, `run: sha=$(gh api
  "repos/$REPO/actions/workflows/ci.yml/runs?branch=$BRANCH&status=success&per_page=1" --jq '.workflow_runs[0].head_sha
  // empty') || sha=""; echo "sha=$sha" >> "$GITHUB_OUTPUT"` (the executor confirms `gh` on the hosted image and the
  endpoint's `branch`/`status` parameters against GitHub's REST reference); filter step `uses:
  dorny/paths-filter@<peeled commit of the newest v4.x.y> # v4.<x>.<y>` (`git ls-remote … 'refs/tags/v4.x.y^{}'`, never
  the tag object), `id: filter`, comment `:38-40` → "# A push compares against the last commit CI passed on this branch
  (with none found, the whole web tier runs), so a cancelled or failed run's web change is filtered again; a
  pull_request ignores base and lists the whole PR (B.10.1).", `base: ${{ steps.base.outputs.sha ||
  github.event.repository.default_branch }}`, `filters: web:` = `'html/**'`, `'js/**'`, `'tests_js/**'`, `'mockdata/**'`,
  `'scripts/**'`, `'src/**'`, `'buildgen/**'`, `'devices/**'`, `'digital_twin/**'`, `'toolchain/**'`, `'ext/**'`,
  `'package.json'`, `'package-lock.json'`, `'eslint.config.js'`, `'tsconfig*.json'`, `'vitest.config.js'`,
  `'.htmlvalidate.json'`, `'.stylelintrc.json'`, `'.nvmrc'`, `'pyproject.toml'`, `'uv.lock'`, `'.github/workflows/ci.yml'`,
  `'.github/actions/**'`.
- **Resolved**: A.U6.12 and A.U28.07 edit one filter list — one edit (A.U28.07 Depends). A.U28.13 runs inside A.SDEP.05
  (SUPP_deps co-landing 2) — U0; A.U28.07 relies on the re-read push semantics at that commit, and "a change in any of
  them re-opens A.U28.07 before the pin moves" stays the executor's gate. A.U28.25's `'tsconfig*.json'` replaces the two
  explicit tsconfig lines (it adds `tsconfig.base.json`).
- **Unit**: U28. Stages: U0 — the dorny line (A.SDEP.05/A.U28.13) with its exact-version comment; U6 — the three
  definitions-source paths (A.U6.12: a `@web` tag edit in `src/` must re-run the web tier from U6 on, when generated
  definitions first feed `tests_js/`); U28 — the rest.
- **Depends**: A.U6.03 (U6 stage, WEB/SCR); A.U28.25 (WEB, `tsconfig.base.json`).
- **Blast carried by**: the four web jobs' `if:` (unchanged expressions) → M.TOOL.006-.010; `test_ci_workflow.py` (2), (3)
  (filter list ⊇, `base:` reads `steps.base.outputs.sha`, empty-base fallback, SHA pin with `# v<maj>.<min>.<patch>`) and
  A.U6.12's planned filter test folded into it → A.U28.08 (TSC); SPEC B.10.1 `:878-884`, H.8 `:4746-4751` → A.U28.37
  (SPEC); CLAUDE.md head-commit rule → A.U28.11 (DOCS); refresh record of the dorny commit → A.SDEP.05 (PROC); U37
  re-check → A.SDEP.25 (PROC).
- **Kind**: code

### M.TOOL.006 web-lint-and-typecheck: synced Python, every built page validated
- **From**: A.U28.43, A.U23.38 (the `lint:html:built` script, WEB), A.U28.01 (the action), A.U8.15/A.U28.36 (timeout,
  M.TOOL.019), A.SDEP.05 (tags, M.TOOL.020).
- **Site**: `.github/workflows/ci.yml:59-86`.
- **Change**: after "Install dependencies" (`npm ci`): `- uses: ./.github/actions/uv-sync`; after "html-validate
  (html/)": `- name: html-validate (every device's built page)` / `run: npm run lint:html:built`. Header comment `:60-62`
  unchanged.
- **Resolved**: —
- **Unit**: U28.
- **Depends**: M.TOOL.002; A.U23.38 (`package.json` script, WEB).
- **Blast carried by**: `test_ci_workflow.py` (9) → A.U28.08 (TSC); SPEC B.10.1 web-lint bullet, H.8 → A.U28.37 (SPEC).
- **Kind**: code

### M.TOOL.007 web-unit-tests: a red web lint never skips it; the build lives in the action
- **From**: A.U28.09 (`if:`, comment), A.U28.04 (4) (own build step goes, `build-unix-port: 'true'`), A.U27.12 (its build
  step's body, now the action's), A.U6.12 (`:130` comment), A.U7.10 (blast: the summary reporter adds lines; no step
  change here).
- **Site**: `.github/workflows/ci.yml:88-133`.
- **Change**: `if: ${{ !cancelled() && needs.web-changes.outputs.web == 'true' }}`; job comment `:89-91` keeps its three
  lines and gains, as a new block, "# needs web-lint-and-typecheck for order only: a red web lint never skips the web
  tests (CLAUDE.md)."; the toolchain step → `- name: Set up MicroPython toolchain (uv sync, restore or build)`, `uses:
  ./.github/actions/setup-micropython-toolchain`, `with: build-unix-port: 'true'`; the "Build MicroPython Unix port (if
  not cached)" step goes; `:130` comment → "# npm's pretest hook builds every device's website first. Everything but the
  live PUT matrix, which is its own sharded job below (B.10.1)."
- **Resolved**: —
- **Unit**: U28. Stage U6: the `:130` comment (A.U6.12, with the build-every-device change).
- **Depends**: M.TOOL.001.
- **Blast carried by**: `test_ci_workflow.py` (1)/(1a) (`!cancelled()` on web-unit-tests), (6) (no repeated build block)
  → A.U28.08 (TSC); CLAUDE.md carrier list → A.U28.11 (DOCS).
- **Kind**: code

### M.TOOL.008 web-put-matrix: stated fail-fast; the build lives in the action
- **From**: A.U28.09 (`:139` comment), A.U28.04 (4).
- **Site**: `.github/workflows/ci.yml:135-183`.
- **Change**: `:139` → "# needs: web-unit-tests, success-gated on purpose: no three runners on the slow matrix if the
  fast suite already failed."; toolchain step `with: build-unix-port: 'true'`; own build step goes. `env:
  PUT_MATRIX_SHARD: ${{ matrix.shard }}/3` unchanged.
- **Resolved**: —
- **Unit**: U28.
- **Depends**: M.TOOL.001.
- **Blast carried by**: `test_ci_workflow.py` (1) → A.U28.08 (TSC).
- **Kind**: code

### M.TOOL.009 web-coverage: the test result gates, the reports never do
- **From**: A.U28.16, A.U28.09 (comment inside the job), A.U7.10 (summary step prints the coverage table by its header),
  A.U28.04 (4).
- **Site**: `.github/workflows/ci.yml:185-252`.
- **Change**: `:185-186` (above the job key) kept; directly under `web-coverage:` the comment "# Success-gated on
  purpose, like unit-tests-coverage: nothing to measure if the plain suite failed."; toolchain step `with:
  build-unix-port: 'true'`, own build step goes; `:224-225` → "# Re-runs the suite instrumented, minus the live matrix,
  whose js/ paths the mock-server matrix already drives; a red test gates, the report never does (B.10.1)."; test step
  name "Run unit tests with coverage (the test result gates, the report does not)", `run: |` `set -o pipefail` /
  `npm run test:coverage 2>&1 | tee coverage-output.txt`, no `continue-on-error`; summary step `if: ${{ always() &&
  hashFiles('coverage-output.txt') != '' }}`, its body prints the lines from Vitest's coverage-table header up to the
  summary block A.U7.10 appends: `awk '/% Coverage report from/{p=1} /^== Summary: npm test ==/{p=0} p'
  coverage-output.txt` inside the existing fenced heredoc (the header text confirmed against the installed
  `@vitest/coverage-v8` at execution), `continue-on-error: true`; artifact step `if: ${{ always() &&
  hashFiles('htmlcov_js/index.html') != '' }}`, `continue-on-error: true`.
- **Resolved**: A.U7.10 (U7) changes the summary step's body, A.U28.16 (U28) its `if:` — different lines of one step,
  both kept (U28 inventory "A.U7.10's body change stands").
- **Unit**: U28. Stage U7: the summary body (A.U7.10 lands its reporter there).
- **Depends**: M.TOOL.001; A.U7.10 (WEB).
- **Blast carried by**: `test_js_coverage_report_dir.py:43-45` holds; `test_test_sh.py:828-830` comment → A.U28.16
  (TSC); `test_ci_workflow.py` (5) → A.U28.08 (TSC); SPEC B.10.1, H.8 → A.U28.37 (SPEC); README "Test coverage" →
  A.U36.526 (DOCS).
- **Kind**: code

### M.TOOL.010 web-cross-browser-smoke: every device's site, a rolling Firefox, all engines required
- **From**: A.U6.12 (build step → `npm run build:site`), A.U6.03 (via A.U6.12), A.U28.04 (4) (the build-if-missing part
  moves into the action), A.U28.19 (Firefox key), A.U28.17 (`--require-all-engines`), A.U28.09 (`:258` comment),
  A.SDEP.19 (W35: a fresh Firefox at the refresh), A.U27.11 (blast: the generator call goes with `build:site`), A.U7.21,
  A.U27.39, A.U6.11 (blast: `main()` changes only; CI line is A.U28.17's).
- **Site**: `.github/workflows/ci.yml:254-309`.
- **Change**: `:258` → "# needs: web-unit-tests, success-gated on purpose: no browser installs if the fast suite already
  failed."; toolchain step `with: build-unix-port: 'true'`; the step `:291-298` → `- name: Build every device's website`
  / `run: npm run build:site`; new step before the Firefox cache, `- name: Cache period for the floating Firefox`, `id:
  month`, `run: echo "month=$(date -u +%Y-%m)" >> "$GITHUB_OUTPUT"`; the cache step's comment `:299-300` → "#
  Firefox+geckodriver float by design (the owner's floor is the current engines): the key rolls monthly and with the
  installer (B.10.1). WebKit and Edge reinstall every run." and `key: cross-browser-firefox-${{ runner.os }}-${{
  hashFiles('scripts/setup_cross_browser_toolchain.sh') }}-${{ steps.month.outputs.month }}`; the smoke step `run: node
  scripts/cross_browser_smoke.mjs --require-all-engines`.
- **Resolved**: A.U6.12's build line and A.U28.04's move of the build-if-missing block act on the same step: the
  toolchain part goes to the action, the site part is `npm run build:site` (U28 inventory, A.U6.12 first). W35's "bump
  the `-v1` suffix" at the refresh is superseded at U28 by A.U28.19's self-rolling key.
- **Unit**: U28. Stages: U0 — `cross-browser-firefox-v1` → `-v2` (A.SDEP.19 W35, a fresh install at the refresh); U6 —
  the build step (A.U6.12).
- **Depends**: M.TOOL.001; A.U28.17's flag in `scripts/cross_browser_smoke.mjs` (SCR); A.U6.03 `build:site` (WEB/SCR).
- **Blast carried by**: `test_ci_workflow.py` (8) → A.U28.08 (TSC); SPEC H.7 "Cross-browser coverage", B.10.1 smoke
  bullet → A.U28.37 (SPEC).
- **Kind**: code

### M.TOOL.011 lint-and-typecheck: one synced environment, generated output in both scopes
- **From**: A.U28.01 (4) (the uv steps), A.U27.09 (4) (generation step, ruff list), A.U27.25 (mypy step name and paths),
  A.U28.41 (blast: the generated code's exemptions, M.TOOL.030), A.U27.24 (blast: its scope-pin test parses these lines),
  A.U1.01 (blast: no legacy path in the lists).
- **Site**: `.github/workflows/ci.yml:311-339`.
- **Change**: job comment `:312-314` → "# ruff names every scope; mypy names exactly the main pass's files, and
  scripts/typecheck.sh always runs the twin and host passes too (B.15)." Steps: checkout; `- uses:
  ./.github/actions/uv-sync` (the "Install uv" step, the retry comment `:325-327` and the retried sync go); new `- name:
  Generate the device modules (ruff checks them)` / `run: uv run scripts/_generate_sensortask_modules.py`; `- name: Ruff
  (every scope, the generated device modules included)` / `run: uv run ruff check src tests digital_twin tests_hardware
  buildgen scripts toolchain tests_scripts build/generated_src` (plus `--no-respect-gitignore` on this invocation only if
  the executor finds ruff skips the explicitly named, git-ignored path, A.U28.41); `- name: Mypy (all three passes;
  typecheck.sh)` / `run: uv run scripts/typecheck.sh src tests digital_twin tests_hardware/device_scripts
  build/generated_src`.
- **Resolved**: —
- **Unit**: U28 (A.U27.09/A.U27.25 are U27's actions on U28's file; they co-land in U27 as a stage).
  Stage U27: the generation step, the ruff path, the mypy step (A.U27.09, A.U27.25 — their scope change lands with the
  pyproject/`lint.sh`/`typecheck.sh` change, OR6.a CI green); U28: the uv-sync action.
- **Depends**: M.TOOL.002; M.TOOL.032 (`files` gains `build/generated_src`); A.U27.11 generator (SCR).
- **Blast carried by**: `tests_scripts/test_lint_type_scopes.py` (4) (CI mypy paths == `files`; ruff list == `lint.sh`'s)
  → A.U27.24 (TSC); SPEC B.10.1 `:906-908`, B.15 → A.U27.25 (SPEC); BACKLOG chroot entry → A.U27.09 (DOCS).
- **Kind**: code

### M.TOOL.012 shellcheck, actionlint and zizmor jobs take the uv-sync action
- **From**: A.U28.01 (4), A.U1.21 (`:342-343` comment), A.SDEP.19 (W32, the zizmor job's audit of the `uses:` form).
- **Site**: `.github/workflows/ci.yml:341-415`.
- **Change**: each of the three jobs replaces "Install uv" + its "# Retried for the same reason …" comment + the
  retried-sync step with `- uses: ./.github/actions/uv-sync`; shellcheck's comment `:342-343` → "# Its own stage so the
  tool has its own check run. scripts/ only: the legacy tree is never in scope (CLAUDE.md)." Tool steps unchanged
  (`uv run shellcheck scripts/*.sh`, `uv run actionlint`, `uv run zizmor --offline .github/`).
- **Resolved**: A.U1.21 (U1) rewrites the comment above steps A.U28.01 (U28) replaces — different lines, both kept (U28
  inventory).
- **Unit**: U28. Stage U1: the shellcheck comment (A.U1.21, with the legacy move).
- **Depends**: M.TOOL.002.
- **Blast carried by**: `test_uv_sync_retried_sh.py` (no second `for attempt in` loop in `.github/`) → A.U28.01 (TSC).
- **Kind**: code

### M.TOOL.013 unit-tests: the retried sync is the toolchain action's first step
- **From**: A.U28.01 (5), A.U21.12 (blast: the lwIP host build lengthens the job — budget only, M.TOOL.019), A.U7.03
  (blast: exit codes kept).
- **Site**: `.github/workflows/ci.yml:417-449`.
- **Change**: the second sync step `:437-447` and its comment go; the toolchain step's name → "Set up MicroPython toolchain
  (uv sync, restore cache)" with the comment "# Its first step is the retried uv sync, ahead of scripts/test.sh: `uv run`
  builds the whole dev group (CLAUDE.md)."; `needs: lint-and-typecheck`, `if: ${{ !cancelled() }}` and the job comments
  `:418-421` unchanged; `:423-424` per M.TOOL.019.
- **Resolved**: —
- **Unit**: U28.
- **Depends**: M.TOOL.001.
- **Blast carried by**: `test_uv_sync_retried_sh.py` (the toolchain action runs before `scripts/test.sh`) → A.U28.01 (TSC).
- **Kind**: code

### M.TOOL.014 unit-tests-gc-threshold: the shipped threshold is tagged
- **From**: A.U8.14 (`:469`).
- **Site**: `.github/workflows/ci.yml:468-469`.
- **Change**: a tag line `# @tunable gc.threshold_bytes = 32768` directly above `run: GC_THRESHOLD=32768 scripts/test.sh`
  (inside the step, between `name:` and `run:`).
- **Resolved**: —
- **Unit**: U8.
- **Depends**: A.U8.01/A.U8.02 (Part N row, tag check).
- **Blast carried by**: Part N `gc.threshold_bytes` Sites column → A.U8.14 (SPEC); `test_tunables_register.py` scans
  `.github/` → A.U8.02 (TSC).
- **Kind**: code

### M.TOOL.015 unit-tests-coverage: no Codecov, five reports, its gate stated plainly
- **From**: A.U28.15 (Codecov steps go; two new summaries and artifacts), A.U24.72 (the generated-module and host
  reports CI publishes), A.U0.37 ("(owner, 2026-09-22)" on the test-step comment), A.U36.526 (same tag, carried here),
  A.U28.01 (5) (second sync copy goes); D12 (the "no longer purely advisory" sentence restated as current state).
- **Site**: `.github/workflows/ci.yml:471-556`.
- **Change**: the second sync step `:491-501` and its comment go; job comment `:477-479` → "# Success-gated on purpose (no
  `if: !cancelled()`): there is nothing to measure if the plain suite did not pass. Its own test step gates; only the
  reports are advisory (Part E.5.3)."; `:502-507` → "# Report steps are `always() && hashFiles(...)` and continue-on-error,
  so a red test never swallows what did render." / "#" / "# This step is NOT advisory (owner, 2026-09-22): build-settrace
  is the only interpreter no other job runs. Exit 1 (a test failed) goes red; exit 3 (only the report failed) stays
  advisory (Part E.5.3)." (the "src/ and digital_twin/ from one run" clause goes: four reports now); the test step
  unchanged; the two Codecov steps and their comment `:525-542` go; after the existing summary steps, "Add
  generated-module coverage summary to job summary" (`if: ${{ always() && hashFiles('coverage_summary_generated.md') !=
  '' }}`, `run: cat coverage_summary_generated.md >> "$GITHUB_STEP_SUMMARY"`, `continue-on-error: true`) and "Add host
  build-chain coverage summary to job summary" (`coverage_summary_host.md`, same form); after the existing artifact steps,
  "Upload generated-module HTML coverage report artifact" (`name: coverage-html-generated`, `path: htmlcov_generated/`,
  `if: ${{ always() && hashFiles('htmlcov_generated/index.html') != '' }}`, `continue-on-error: true`) and "Upload host
  build-chain HTML coverage report artifact" (`coverage-html-host`, `htmlcov_host/`, same guard).
- **Resolved**: A.U0.37's tag lands on the kept test-step comment (U28 inventory; A.U28.15 (6)). Codecov's removal
  (OR63.a) precedes the refresh: A.SDEP.05 does not refresh `codecov/codecov-action` (SUPP_deps co-landing 4) — the two
  steps are deleted, not re-pinned, so the U0 stage leaves them untouched.
- **Unit**: U28. Stage U0: the owner tag (A.U0.37).
- **Depends**: A.U24.72 (the two renders exist, SCR/TEST_HELP); M.TOOL.001.
- **Blast carried by**: `test_test_sh.py:826-842` `count("always() &&") == 8` → A.U28.15 (TSC); `test.sh`/
  `_render_coverage.py` `--xml-file` and `.gitignore` → A.U28.15 (SCR, LEAD); SPEC E.5, B.10.1, README, CLAUDE.md
  Codecov sentences → A.U36.526 (SPEC, DOCS); `zizmor.yml` codecov mention → M.TOOL.021.
- **Kind**: code

### M.TOOL.016 New `devices` job derives the device set
- **From**: A.U28.06 (the job), A.U8.15 (its tag, via A.U28.06).
- **Site**: `.github/workflows/ci.yml`, new job `devices` (placed after `web-changes`).
- **Change**: comment "# The device set, derived from devices/*.toml like tests_scripts/_devices.py - a variant is never
  named here (CLAUDE.md)."; `permissions: contents: read`; `runs-on: ubuntu-latest`; `# @tunable ci.devices_timeout_min =
  5` / `timeout-minutes: 5`; `outputs: list: ${{ steps.list.outputs.list }}`; checkout `persist-credentials: false`;
  step `id: list`, `run:` `names=(); for f in devices/*.toml; do n=$(basename "$f" .toml); [[ $n == zz_test_* ]] ||
  names+=("\"$n\""); done; [ "${#names[@]}" -gt 0 ] || { echo "::error::no devices/*.toml found"; exit 1; }; (IFS=,; echo
  "list=[${names[*]}]") >> "$GITHUB_OUTPUT"`.
- **Resolved**: —
- **Unit**: U28.
- **Depends**: A.U6.12, A.U6.15 (the other variant literals gone first).
- **Blast carried by**: matrices → M.TOOL.017, M.TOOL.018; Part N `ci.devices_timeout_min` row (basis "estimated (agent,
  2026-09-30) — a glob") → A.U28.06/A.U8.15 (SPEC); `test_ci_workflow.py` (7) → A.U28.08 (TSC); `test_device_tomls.py:271-282`
  moves → A.U28.06 (TSC).
- **Kind**: code

### M.TOOL.017 digital-twin-e2e: one job per derived device
- **From**: A.U28.06, A.U25.48 (blast: CI passes the matrix device, unchanged), A.U27.16 (blast: log artifact path
  unchanged), D1 (adherence: the matrix value reaches `run:` through `env`).
- **Site**: `.github/workflows/ci.yml:559-593`.
- **Change**: `needs: [unit-tests, devices]` (still success-gated; the `:567-568` comment unchanged in intent);
  `:564-565` "Six-device matrix, fail-fast: false" → "One job per device, fail-fast: false"; `matrix: device: ${{
  fromJSON(needs.devices.outputs.list) }}`; the run step gains `env: DEVICE: ${{ matrix.device }}` and becomes `run:
  scripts/run_digital_twin_ci.sh "$DEVICE"`; the artifact name keeps `digital-twin-ci-logs-${{ matrix.device }}` (a
  `with:` field, not a script).
- **Resolved**: D1 (agent): once the matrix is read from a job output rather than a literal, its value is passed through
  `env` (zizmor's template-injection remedy) instead of being expanded inside the script; no constituent conflict.
- **Unit**: U28.
- **Depends**: M.TOOL.016.
- **Blast carried by**: `test_ci_workflow.py` (1a), (7) → A.U28.08 (TSC); SPEC B.10 `:844-845`, B.10.1 → A.U28.37 (SPEC).
- **Kind**: code

### M.TOOL.018 firmware-build-verify: derived matrix, checked python3, cached picotool
- **From**: A.U28.06 (matrix, `needs`, `if`), A.U28.05 (picotool step, `:617-618` comment), A.U27.10 (`_require_python.sh`
  before the heredoc), A.U21.29 (blast: the heredoc's `load_versions()`/`["toolchain"]["apt_packages"]` shape holds),
  A.U21.18 (blast: `ensure_apt_packages()` now `sudo --preserve-env=…`; holds on the hosted runner), A.U21.10/A.U21.11
  (blast: the real modlwip proof runs in this job), A.U27.31 (blast: size report printed), D1 (env).
- **Site**: `.github/workflows/ci.yml:595-634`.
- **Change**: `needs: [unit-tests, devices]`; `if: ${{ !cancelled() && needs.devices.result == 'success' }}`; comment
  `:596-597` "Six-device matrix" → "One job per device"; `matrix: device: ${{ fromJSON(needs.devices.outputs.list) }}`;
  the comment block `:617-622` → "# A cache miss fails the picotool step below by name (no cached build tree), never
  skipping the build." / "#" / "# apt packages never survive between jobs, so the ARM compiler is installed here from
  versions.toml via ensure_apt_packages(); without it this job once failed with \"arm-none-eabi-gcc not found\"."; the
  apt step's `run: |` begins `source scripts/_require_python.sh && require_python311` then the unchanged `python3 -`
  heredoc; new step after it, `- name: Install the cached picotool`, comment "# picotool lives in /usr/local, outside the
  cache; its build tree is inside it, so a hit installs the very binary setup built (B.10.1).", `run: |` `if [ ! -x
  /usr/local/bin/picotool ]; then sudo make -C "$HOME/pico-toolchain/picotool/build" install; fi` /
  `/usr/local/bin/picotool version`; the build step `env: DEVICE: ${{ matrix.device }}`, `run: RUN_SLOW_FIRMWARE_BUILD=1
  uv run pytest "tests_scripts/test_build_firmware.py::test_real_firmware_build_produces_a_valid_uf2[$DEVICE]" -v` (step
  name keeps `${{ matrix.device }}`).
- **Resolved**: A.U28.05 (U28) and A.U27.10 (U27) edit adjacent steps of one job — both kept (U28 inventory). A.U21.27
  keeps the `/usr/local` prefix, so A.U28.05's install target holds (A.U28.05 Depends).
- **Unit**: U28. Stage U27: the `_require_python.sh` line (A.U27.10).
- **Depends**: M.TOOL.001, M.TOOL.016; M.TOOL.052 (picotool prefix); A.U27.10 helper (SCR).
- **Blast carried by**: `test_build_firmware.py:202` real build unchanged → (TSC); SPEC B.10.1 `firmware-build-verify`
  bullet (what a build without an installed picotool does, read once in `tools/Findpicotool.cmake`) → A.U28.05/A.U28.37
  (SPEC); `test_ci_workflow.py` (1a), (7) → A.U28.08 (TSC).
- **Kind**: code

### M.TOOL.019 Every job's timeout is tagged, then re-measured once the tiers have grown
- **From**: A.U8.15 (one `ci.<job>_timeout_min` tag per job, two "measurement owed" bases), A.U28.36 (re-measure and
  re-set ten budgets), A.U28.06 (`devices` tag, M.TOOL.016), A.U6.10, A.U6.11, A.U21.12, A.U24.72, A.U25.37, A.U25.48,
  A.U25.55, A.U25.74, A.U27.14, A.U27.38, A.U23.38/A.U28.43, A.U7.21, A.S0930.04, A.S0930.27 (blast: each lengthens a job
  A.U28.36 re-measures); D4 (budget comments keep reasons, numbers live in Part N).
- **Site**: `.github/workflows/ci.yml` every `timeout-minutes:` (`:28, :68, :97, :145, :193, :264, :318, :347, :373,
  :398, :430, :461, :484, :573, :606`) and the budget comments `:423-424`, `:474-475`.
- **Change**: each `timeout-minutes: <n>` gets the line `# @tunable ci.<job id, - → _>_timeout_min = <n>` directly above
  it (sixteen jobs with `devices`). Values: `web-changes` 5, `devices` 5, `lint-and-typecheck` 15, `shellcheck`,
  `actionlint`, `zizmor` 5 each stay; the ten A.U28.36 jobs (`web-lint-and-typecheck`, `web-unit-tests`,
  `web-put-matrix`, `web-coverage`, `web-cross-browser-smoke`, `unit-tests`, `unit-tests-gc-threshold`,
  `unit-tests-coverage`, `digital-twin-e2e`, `firmware-build-verify`) take the larger of the cold-cache wall clock and the
  warm wall clock plus the job's largest single retry budget, plus 25 %, rounded up to 5 minutes, measured on the first
  CI run after the last of A.U28.36's Depends lands (a cold run forced once by M.TOOL.001's key change); a budget that
  falls is lowered. `:423-424` → "# Its budget: a warm run plus one hung file's full retry budget (Part N); the per-file
  timeout in scripts/test.sh is the real hang defence (B.10.1)."; `:474-475` → "# Its budget covers the instrumented
  rerun with margin (Part N): a tighter cap once cancelled a passed suite and digital-twin-e2e with it." (each ≤ 3 lines).
- **Resolved**: A.U8.15 (U8) tags today's values; A.U28.36 (U28) replaces them with measurements — two stages of one
  line. D4 (agent): the measured minutes and their run ids live in the Part N rows (A.U28.36 "each tag's Part N basis
  becomes the measurement with its run id"), so the two comments drop their numbers rather than keep a second copy.
- **Unit**: U28 (the re-measured values at the sync point after A.U28.36's Depends). Stage U8: the fifteen tags at HEAD's
  values (A.U8.15).
- **Depends**: M.TOOL.016; every action in A.U28.36's Depends.
- **Blast carried by**: Part N `ci.*_timeout_min` rows (basis, run id, margin) → A.U8.15/A.U28.36 (SPEC); SPEC B.10.1
  per-job minutes → A.U28.37 (SPEC); `test_tunables_register.py` → A.U8.02 (TSC).
- **Kind**: code

### M.TOOL.020 First-party action tags at the refreshed majors; local `uses:` form per actionlint
- **From**: A.SDEP.05 (tag refresh of `actions/checkout`, `actions/setup-node`, `actions/cache`,
  `actions/upload-artifact`), A.SDEP.19 (W32), A.U28.35 (3) (no `submodules:` key — no edit), A.U34.09 (blast: CI
  uploads coverage and logs only — holds).
- **Site**: `.github/workflows/ci.yml` every `uses: actions/<name>@vN` (`checkout` ×15 + `devices`, `setup-node` ×5,
  `cache` ×5, `upload-artifact` ×4 at HEAD, ×6 after M.TOOL.015) and every local `uses: ./.github/actions/…`.
- **Change**: each `actions/<name>@vN` → the newest major tag of that action (one `sed` per action, the count recorded in
  the refresh record), its release notes read for the inputs this repo passes (A.SDEP.05); every later step added by
  U28 (M.TOOL.005, .015, .016) uses the same refreshed tags. W32: if the refreshed actionlint accepts `uses:
  $/.github/actions/…`, every local `uses:` (nine toolchain-action sites, the uv-sync sites, M.TOOL.001's inner one) takes
  that form and `zizmor.yml`'s `self-repository` block goes (M.TOOL.022); otherwise `./` stays. No checkout gains
  `fetch-depth` or `submodules:`.
- **Resolved**: —
- **Unit**: U0 (refresh; later steps written with the refreshed tags). Re-checked in U37 (A.SDEP.25).
- **Depends**: A.SDEP.03 (the refreshed actionlint decides W32).
- **Blast carried by**: zizmor `unpinned-uses` and actionlint gates; `test_ci_workflow.py` (3), (4) → A.U28.08 (TSC);
  BACKLOG chroot entry "ci.yml/composite-action pins" → A.SDEP.21 (DOCS); CLAUDE.md zizmor sentence → A.U28.40/A.SDEP.19
  (DOCS).
- **Kind**: code

## .github/zizmor.yml

### M.TOOL.021 zizmor.yml header and policy comments say what it configures
- **From**: A.U28.14 (`:1-3`, `:11-12`), A.U36.526 (Why names `zizmor.yml:11` codecov — carried by A.U28.14, its register
  fix 7), A.U28.15/A.U28.13 (blast: Codecov gone, dorny the one third-party action).
- **Site**: `.github/zizmor.yml:1-3`, `:11-12`.
- **Change**: `:1-3` → "# zizmor (GitHub Actions security audit) config, run offline by scripts/lint.sh and CI's zizmor
  job. Two audits are configured, unpinned-uses's policy and self-repository's disable; every other audit runs at its
  default, so a zizmor bump surfaces new checks to triage (CLAUDE.md)."; `:11-12` → "# Everything third-party (dorny/
  today) is pinned to a commit SHA: a force-pushed tag there is the tj-actions/changed-files attack." The two policies
  `actions/*: ref-pin`, `"*": hash-pin` unchanged. If W32 removes `self-repository` (M.TOOL.022), the header's second
  sentence reads "One audit is configured, unpinned-uses's policy; every other audit runs at its default, …".
- **Resolved**: —
- **Unit**: U28.
  A-C2 step order: A.U28.13's part lands in U0 (A.SDEP.05: "A.U28.13 (pulled forward)" into the GitHub Actions pin refresh).
- **Depends**: M.TOOL.015 (Codecov gone first, A.U28.14 Depends), M.TOOL.022 (which audits remain).
- **Blast carried by**: CLAUDE.md zizmor bullet → A.U28.40 (DOCS); BACKLOG chroot entry → A.U28.38 (DOCS).
- **Kind**: doc

### M.TOOL.022 self-repository: actor, retirement trigger, the refreshed actionlint
- **From**: A.U0.40 (L42: actor and trigger at `:15-16`), A.SDEP.19 (W32: with the refreshed actionlint the block goes, or
  its version text is re-stamped), A.SDEP.03 (the actionlint pin moves).
- **Site**: `.github/zizmor.yml:13-18` (the `self-repository` block).
- **Change**: W32 "no" (actionlint still rejects `uses: $/…`): the comment → "# Disabled, not fixed: it wants `uses:
  $/.github/...`, which actionlint <refreshed version> rejects, so both gates cannot pass (agent, 2026-09-10). Re-enable
  when actionlint accepts the syntax (checked at each actionlint pin bump)." (3 lines), `disable: true`. W32 "yes": the
  whole block `:13-18` goes (and M.TOOL.020 moves every local `uses:` to `$/`).
- **Resolved**: A.U0.40 (U0) and A.SDEP.19 (U0, after A.SDEP.03) both edit `:15-16` in U0 — one text: A.U0.40's actor
  and trigger with A.SDEP.19's version stamp; "Low severity" goes with A.U0.40's rewrite.
- **Unit**: U0.
- **Depends**: A.SDEP.03 (actionlint version).
- **Blast carried by**: CLAUDE.md `:496-499` and BACKLOG `:749` version text → A.SDEP.19/A.U0.40 (DOCS); A.U28.08's
  workflow checks take the `uses:` form → A.U28.08 (TSC).
- **Kind**: doc, code

## pyproject.toml

### M.TOOL.023 The Python floor comment names the one check for bare python3
- **From**: A.U27.10 (toml blast: `:8-11` comment), A.U20.33 (blast: host code relies on `>=3.11` natively).
- **Site**: `pyproject.toml:8-11`.
- **Change**: the comment → "# >=3.11: host tooling needs tomllib and datetime.UTC; at 3.10 `uv sync` once built a venv
  without them, surfacing as a raw traceback. scripts/_require_python.sh checks every bare python3; setup_toolchain.py's
  PEP 723 header pins the same." (3 lines); `requires-python = ">=3.11"` unchanged.
- **Resolved**: —
- **Unit**: U27.
- **Depends**: A.U27.10's helper (SCR).
- **Blast carried by**: BACKLOG chroot entry "every bare python3 in scripts/ is version-checked first" → A.U27.10 (DOCS).
- **Kind**: doc

### M.TOOL.024 uv itself is pinned
- **From**: A.U28.02 (`[tool.uv] required-version`), A.SDEP.03 (records uv before/after the refresh), A.SDEP.25 (U37
  re-check), AC_NOTES 38 (U28 applied: "execution pins the uv version current at B0").
- **Site**: `pyproject.toml:13-14` (`[tool.uv]`).
- **Change**: `[tool.uv]` → `package = false` and `required-version = "==<v>"`, `<v>` the uv version the U0 refresh ends
  with (A.SDEP.03 record; the post-refresh environment column of A.U0.06, A.SDEP.20); the executor confirms in uv's
  documentation that `required-version` makes every other uv version refuse to run. One comment line above it: "# CI and
  the chroot recipe install exactly this uv (the uv-sync action reads it)."
- **Resolved**: B0 version (A.U28.02, AC_NOTES 38) vs the refreshed version (A.SDEP.03): settled by OR129 (owner,
  2026-09-30), the most recent decision — tools are refreshed in U0 and stay pinned, so the pin is the refreshed uv; the
  B0 value stays in A.U0.06's B0 column for reference.
- **Unit**: U28. Re-checked at U37 (A.SDEP.25: a newer uv there reruns A.SDEP.03 for it).
- **Depends**: A.SDEP.03.
- **Blast carried by**: M.TOOL.002 reads it; `test_tool_pins.py` (4) → A.U28.03 (TSC); CLAUDE.md/SPEC B.17 chroot recipe
  `pip install "uv==<v>"` → A.U28.02/A.U36.524 (DOCS); `tests_hardware/README.md` bench prerequisite and BACKLOG "check the
  bench Pi4's uv" → A.U28.02 (HW_BENCH, DOCS); BACKLOG chroot entry → A.U28.38 (DOCS).
- **Kind**: code

### M.TOOL.025 Every dev tool pinned at its refreshed version, coverage included
- **From**: A.SDEP.03 (refresh of the pinned tools), A.U28.02 (`pytest`, `mpremote` pinned), A.U24.72 (`coverage` joins
  the group, exact pin), D16/D19 of the SUPP_deps inventory.
- **Site**: `pyproject.toml:16-36` (`[dependency-groups] dev`).
- **Change**: `dev = [` comment `:18-20` kept ("PINNED, like every tool here: …" — true now of every entry);
  `"mypy==<refreshed>"`, `"ruff==<refreshed>"`, `"pytest==<refreshed>"`, `"mpremote==<the release equal to the refreshed
  MicroPython pin, else the newest that A.SDEP.03's notes allow>"`, `"types-pyserial==<refreshed>"`, `"shellcheck-py==<…>"`,
  `"actionlint-py==<…>"`, `"zizmor==<…>"`, `"coverage==<the version A.SDEP.03 recorded for the renderer>"` (with a one-line
  comment "# The renderer scripts/_render_coverage.py pins the same version in its PEP 723 header (test_tool_pins.py
  checks)."); the stub-isolation comment `:38-40` unchanged.
- **Resolved**: A.U28.02 pins "the versions the lock resolves today" (`pytest==9.1.1`, `mpremote==1.29.0`); after A.SDEP.03
  they take the refreshed lock's versions and mpremote the release equal to the refreshed MicroPython pin (SUPP_deps
  co-landing 1); A.U24.72/A.U28.02 take A.SDEP.03's `coverage` version (co-landing 14). Every new rule the refreshed
  ruff/mypy brings is decided at A.SDEP.02's gate (fixed, or added with a reason in M.TOOL.028/.030) — no rule enters
  unchosen (CLAUDE.md pin rationale).
- **Unit**: U0 (refresh of the existing pins); U24 (`coverage`, A.U24.72); U28 (`pytest`/`mpremote` pins, A.U28.02).
  Re-checked at U37 (A.SDEP.25).
- **Depends**: M.TOOL.078 (lock rewritten with each change).
- **Blast carried by**: `scripts/_render_coverage.py:4` pin → A.U28.02 (SCR); `test_tool_pins.py` (1)-(3) → A.U28.03
  (TSC); the merge check (installed `ruff --version`/`mypy --version` = the pins) → A.SDEP.03 (PROC), CLAUDE.md
  `uv.lock` bullet → A.U36.528 (DOCS); BACKLOG chroot entry → A.SDEP.21/A.U28.38 (DOCS).
- **Kind**: code

### M.TOOL.026 The scope comment names legacy/ and the generated tree
- **From**: A.U1.21 (`:42-43` "(python/, modules/)" → "(legacy/)"), A.U27.09 (adherence: the generated output joins the
  scope).
- **Site**: `pyproject.toml:42-44`.
- **Change**: → "# Lint/type scope is the eight directories CLAUDE.md's "Code quality tooling" lists, plus the generated
  build/generated_src/; the legacy tree (legacy/) is never in scope. tests_hardware/device_scripts/ joined after a driver
  signature change broke two unchecked scripts for a day." (3 lines).
- **Resolved**: — (A.U27.09 changes the scope this comment states; the comment follows in the same change).
- **Unit**: U27. Stage U1: "(legacy/)" (A.U1.21, with the legacy move).
- **Depends**: A.U1.01 (LEAD).
- **Blast carried by**: CLAUDE.md "Scope is eight directories" sentence → A.U27.09 (DOCS).
- **Kind**: doc

### M.TOOL.027 The confusables allowance says where `×` lives
- **From**: A.U6.04 (`:58-59` "html/definitions/*.json's" → "generated definitions.json's"), A.U28.31 (3) (names the
  rules; `allowed-confusables` liveness).
- **Site**: `pyproject.toml:58-60`.
- **Change**: comment → "# `×` is real content in bmp3xx's `@web` tag lines and the generated oversampling labels, which
  RUF001-RUF003 would flag as a look-alike."; `allowed-confusables = ["×"]` kept while A.U28.31's check sees a RUF001-
  RUF003 finding naming `×`, else removed.
- **Resolved**: A.U6.04 (U6) and A.U28.31 (U28) rewrite one comment — A.U28.31's text "follows A.U6.04" (its own words).
- **Unit**: U28. Stage U6: "generated definitions.json's" (A.U6.04, with the hand-written files' deletion).
- **Depends**: —
- **Blast carried by**: `test_ruff_exemptions_live.py` → A.U28.31 (TSC).
- **Kind**: doc

### M.TOOL.028 The global ignore list keeps only what holds in every scope
- **From**: A.U28.27 (global narrowing), A.U11.38 (T20), A.U10.38 (N801), A.U9.02 (ASYNC110 reason), A.U0.37 (S104
  heading), A.U0.35 (`:168-169` "accepted permanently"), A.U28.29 (4) (`:168-169`), A.U28.32 + A.U34.07 (CPY001 reason),
  A.U36.544 (`:77` "F.3" → "F.2"), A.U28.31 (liveness of every global code), A.U29.01 (S104 may cite A.11), A.SDEP.03
  (rules the refreshed ruff adds), A.U10.47/A.U33.06 (blast: E722 stays enabled; no rule beyond these narrowed).
- **Site**: `pyproject.toml:53-195` (`[tool.ruff.lint]` `select`, `ignore`).
- **Change**: `select = ["ALL"]` and its comment `:54-55` unchanged. `ignore` keeps exactly: `"E501"` (comment as
  today), `"D100"`-`"D107"` (comment `:66-68` as today), `"BLE001"` (Part G.2 reason as today), `"PERF203"` (reason as
  today), `"S110"` with "# S110 wants a log call at sites that are deliberately silent; on the target its other escape,
  contextlib.suppress, is unavailable (per-file SIM105 below).", `"RUF037"`, `"RUF012"`, `"PYI024"`, `"FURB122"` (their
  MicroPython-runtime reasons as today; no host site today), `"PYI041"`, `"PYI034"`, `"TRY301"`, `"SIM115"`,
  `"PLW1641"`, `"FBT003"`, `"N803"`, `"N806"`, `"N811"`, `"N814"` (comment → "# Identifiers mirror the datasheet and
  reference algorithm (Part D.1/C.2): BMP3xx's T1/P1..P11 (N806), the VOC algorithm's L/X0/K (N803), acronym imports such
  as `from machine import I2C as FakeI2C` (N811/N814)."), `"D205"`, `"D209"`, `"INP001"`, `"CPY001"` with "# CPY001:
  project-authored files carry no copyright notice; files derived from third-party code carry an attribution header
  (SPDX where a license is named), and THIRD_PARTY_LICENSES.md holds every notice.", and the one line "# S105/S106 stay
  on: the per-file block below names only test doubles' literal passwords (the accepted hotspot password lives in a
  shape these rules do not see)." Leave the list, each to M.TOOL.030's per-file groups: `PTH`, `ASYNC230` (reason cites
  SPECIFICATION.md F.2), `PT`, `T20`, `ASYNC110` (A.U9.02's reason), `PLW0603`, `TRY003`, `EM101`, `EM102`, `SIM105`,
  `RUF005`, `PLR0124`, `S104` (A.U0.37's heading text becomes its reason), `N801`, `N802`. A rule the refreshed ruff makes
  stable is fixed in code or listed here or per file with its reason at A.SDEP.02's gate. A code A.U28.31 finds with no
  finding anywhere is removed in the same commit (a policy rule with no current site is listed in that test with its
  reason). E722 stays enabled (not listed).
- **Resolved**: A.U0.35/A.U0.37 (U0) edit comments A.U28.27/.29 (U28) move or rewrite — the U0 words survive in the U28
  text (the S104 heading text becomes the per-file reason, A.U28.27 Depends; "accepted permanently (owner, 2026-09-26)"
  lands on the credential comment, A.U28.29 (2)). A.U28.32's CPY001 text vs A.U34.07's: A.U34.07 (U34, later) words it
  ("an attribution header (SPDX where a license is named)") — kept. A.U28.29 (4)'s "test copies of the accepted hotspot
  password" clause is dropped: A.U26.49 (U26, before U28) removes those literals, so no copy entry remains.
- **Unit**: U28. Stages: U0 — A.U0.35/A.U0.37 comment edits at HEAD's lines, and the refresh's rule decisions; U9 — the
  ASYNC110 reason text (A.U9.02); U10 — N801 leaves (A.U10.38); U11 — T20 leaves (A.U11.38); U34 — CPY001 wording
  (A.U34.07); U36 — `:77` F.2 if not yet carried (A.U36.544, DONE by U28's move otherwise).
- **Depends**: M.TOOL.030 (same rewrite of the exemption scheme).
- **Blast carried by**: `test_ruff_exemptions_live.py` → A.U28.31 (TSC); `test_code_conventions.py` unaffected → A.U10.47
  (TSC); CLAUDE.md scope/exemption sentence → A.U28.34 (DOCS); SPEC D.6/B.15 name the two groups → A.U28.27 (SPEC);
  BACKLOG "lint config only" line → A.U28.38 (DOCS).
- **Kind**: code, rule

### M.TOOL.029 Lint ceilings sit at the measured maximum; max-args is 8
- **From**: A.U5.17 (`max-args = 8`, comment), A.U5.18 (every ceiling at its measured maximum, enforced).
- **Site**: `pyproject.toml:202-212` (`[tool.ruff.lint.mccabe]`, `[tool.ruff.lint.pylint]` and their comment).
- **Change**: comment → "# Ceilings sit at the measured maximum and only go down, enforced by
  tests_scripts/test_lint_ceilings.py; a signature mirroring an external API is exempted per file below, never by
  raising a limit (owner, 2026-09-26: "8 is fine")."; `max-complexity`, `max-branches`, `max-statements`, `max-returns`
  = the measured maxima at landing (HEAD: complexity 20, branches 20, statements 79, returns 11); `max-args = 8`. Every
  later unit that lowers a measured maximum lowers its ceiling in the same commit (the check fails otherwise).
- **Resolved**: —
- **Unit**: U5.
- **Depends**: A.U5.02-A.U5.16 (the measured maximum of 8); M.TOOL.030 (PLR0913 per-file entries, same commit).
- **Blast carried by**: `test_lint_ceilings.py` → A.U5.18 (TSC); SPEC D.10/Part E → A.U5.18 (SPEC); BACKLOG "Lint config
  only" line → A.U5.17 (DOCS).
- **Kind**: rule

### M.TOOL.030 One per-file exemption block: two scope groups, every entry live and reasoned
- **From**: A.U28.27 (groups and per-file narrowing), A.U28.28 (inline `noqa` → central entries), A.U28.29 (credential
  block), A.U28.31 (liveness; removals ARG004/ARG002/ARG005 and S106), A.U28.41 (`build/generated_src/**` in the
  MicroPython-run group, no S106), A.U0.39 (L44 opening comment), A.U0.35 (credential wording), A.U29.03 (texts point at
  SPEC A.11), A.U11.38 (T20 per-file), A.U11.S03 (`print_log` ANN401 goes), A.U10.37 (renamed `src/` keys), A.U10.38 (N801
  per-file), A.U5.17 (PLR0913 per-file), A.U15.43, A.U19.05, A.U19.17, A.U22.04, A.U24.73, A.U25.63, A.U20.32 (ANN401
  entries go file by file), A.U34.11 (no ANN401 left, category comments go), A.U26.19 (repro S106 goes), A.U26.49 (copy
  S105 entries go), A.U26.54 (S112 comment), A.U21.17 (FBT001/FBT002 trial for `test_setup_toolchain_env.py`), A.U0.07 +
  A.U37.02 (PLC0415 per scope), A.U25.42 (the twin's named exception), A.U36.544 (F.3 → F.2), A.U9.02 (ASYNC110 reason),
  A.U0.37 (S104 heading text), A.U29.01 (S104 may cite A.11); M.TWIN gap (`:294`/`:310` ANN401 with A.U25.63);
  M.TEST_HELP.003/.004 (S102 entries), M.HW_BENCH.038 (the conformance file's subprocess goes), M.TEST_HELP.031 (the
  concurrency scenario library deleted), M_SCR gap 2 (b) (gap pass: the stripper's N802 entry). Dropped: A.U28.28 (3)'s new `tests_hardware/isl29125_conformance.py` `S603`
  entry — M.HW_BENCH.038 (U26) moves the file to `tests_hardware/conformance.py` and removes its subprocess launch and
  `noqa: S603`, so nothing is left to exempt; A.U28.29 (2)'s "copies of that password" group — empty after A.U26.49 (U26);
  A.U28.27's `"scripts/_strip_type_checking.py" = ["N802"]` — the rewritten stripper defines no `visit_*` method
  (M.SCR.070), so A.U28.31's liveness check would fail on it (gap pass, M_SCR gap 2 (b)).
- **Site**: `pyproject.toml:214-351` (`[tool.ruff.lint.per-file-ignores]`).
- **Change**: end state (each comment block ≤ 3 prose lines; every cell confirmed with `ruff check --select <rule>` per
  scope at landing, A.U28.31's check the arbiter):
  Opening: "# Per-file exemptions live here, centrally and with a reason, rather than as `# noqa` comments scattered
  inline (owner, 2026-09-10: enable the strict rule, do not paper it over inline). Each is a property of what the file
  IS." / "#" / "# MicroPython-run code (src/, build/generated_src/, tests/, digital_twin/, tests_hardware/device_scripts/)
  runs on the board or the Unix port; host code (buildgen/, scripts/, toolchain/, tests_scripts/, the rest of
  tests_hardware/) runs under CPython."
  MicroPython-run group, reason block: "# No pathlib (PTH), no async file I/O - every flash write is reachable only through
  the REST PUT path, SPECIFICATION.md F.2 (ASYNC230) - no contextlib in the frozen build (SIM105), no PEP 448 unpacking
  in displays (RUF005), and zip() takes no keyword, so strict= raises TypeError (B905; py/objzip.c, v<pin>)." / "#" / "#
  TRY003/EM101/EM102 add exception classes and locals on the error path for no behavioural gain on a 264KB-SRAM target
  (Part D.4)." Entries: `"src/**"` and `"build/generated_src/**"` = `["ASYNC230", "B905", "EM101", "EM102", "PTH",
  "RUF005", "SIM105", "TRY003"]`.
  Test suites, reason block: "# Test code asserts, reaches into privates under test and asserts literal values (Part
  E.3); a double accepts the real API's full signature, and mypy checks Protocol and monkeypatch parameter NAMES (ARG).
  Tests and tools print by design (T20)." / "#" / "# tests/ and digital_twin/ run under microtest.py, not pytest (PT),
  poll a fake's plain state flag - the fakes expose no Event to wait on (ASYNC110) - and keep per-process counters and
  module-level fake state (PLW0603)." Entries: `"tests/**"` = `["ARG001", "ARG002", "ARG005", "ASYNC110", "ASYNC230",
  "B905", "EM101", "EM102", "PLR2004", "PLW0603", "PT", "PTH", "RUF005", "S101", "SIM105", "SLF001", "T20", "TRY003"]`;
  `"digital_twin/**"` = `["ASYNC110", "ASYNC230", "B905", "EM101", "EM102", "PLR2004", "PLW0603", "PT", "PTH", "RUF005",
  "S101", "SIM105", "SLF001", "T20", "TRY003"]`; `"tests_hardware/device_scripts/**"` = `["ASYNC230", "B905", "EM101",
  "EM102", "PLW0603", "PT", "PTH", "RUF005", "RUF007", "SIM105", "TRY003"]` with "# RUF007: itertools does not exist in
  the rp2 port, so pairwise() is unimplementable." (the `tests_hardware/**` entry below applies too: ruff unions every
  matching glob); `"tests_scripts/**"` = `["ARG001", "ARG005", "PLR2004", "S101", "S603", "SLF001", "T20"]` with "# S603:
  running the repo's own scripts as subprocesses IS what tests_scripts/ verifies, every argv in-repo.";
  `"tests_hardware/**"` = `["ARG001", "ARG002", "PLR2004", "S101", "SLF001", "T20"]`.
  Host tools, reason block: "# Host tools print by design (T20); a user error prints its message alone, with no traceback
  to duplicate it (error contract: owner, 2026-09-25; this exemption: agent, 2026-09-30)." Entries: `"buildgen/**"`,
  `"scripts/**"`, `"toolchain/**"` = `["EM101", "EM102", "T20", "TRY003"]` (EM/TRY kept only where the executor confirms
  the tool's entry point prints user errors without a traceback, U20/U21/U27's error-contract actions).
  Per file, each with its reason line(s) above it:
  `"src/asy_api_response.py"` = `["SLF001"]` (Part C.5.2's `_set_dict_cfg` dispatch contract, as today);
  `"src/asy_webserver_service.py"` = `["S104", "SLF001"]`, `"src/asy_captive_dns.py"` = `["S104"]`,
  `"src/asy_dns_client.py"` = `["S104"]`, `"digital_twin/network.py"` = `["S104"]`, `"tests_hardware/rogue_udp_responder.py"`
  = `["S104"]` under "# S104: the webserver and captive DNS bind every interface on a trusted home LAN (owner,
  2026-09-26; SPECIFICATION.md A.11); asy_dns_client.py and the twin's network.py only compare with the unset address;
  the rogue responder binds the bench LAN.";
  `"src/asy_bmp3xx_driver.py"` = `["FBT001", "N801"]`, `"src/asy_scd30_driver.py"` = `["FBT001", "N801", "N802",
  "PLR0124"]`, `"src/asy_sgp40_driver.py"` = `["FBT001", "N801"]`, `"src/asy_wifi_service.py"` = `["FBT001"]`,
  `"src/asy_isl29125_driver.py"` = `["N801", "PLR0124", "PLR0913"]`, `"src/asy_fram_driver.py"` = `["N801"]`,
  `"src/voc_algorithm.py"` = `["N801"]`, `"src/asy_uart_driver.py"` = `["PLR0913"]`, under one block per rule: FBT001 —
  the `_push_*` family takes the config-value union through Part C.5.2's single-positional-argument contract (as today);
  N801 — "C.2's `<CHIP>_<Role>` compounds and the Sensirion port's names"; N802 — `get_CO2`, the datasheet's name;
  PLR0124 — "`x != x` is the NaN test at each site, commented there; math.isnan() would work too" (every test file ruff
  reports carries it too, e.g. `tests/test_asy_i2c_driver.py`); PLR0913 — `UART.__init__`/`init()` take `machine.UART`'s
  twelve parameters plus the wrapper's own four, `ISL29125_I2C.configure()` one keyword per CONFIG1-3 field (FN8424
  p10-11);
  `"src/asy_notification_service.py"` = `["ARG002"]` (`_DefaultSignalSink.request_signal()` mirrors NeopixelDriver's
  signature, as today); `"src/asy_print_log.py"` = `["T20"]` ("print() is the log transport, not debug residue -
  asy_print_log.py is built on it");
  `"tests/machine.py"` and `"digital_twin/machine.py"` = `["A002", "FBT001", "FBT002", "PLR0913"]` (the machine fakes
  mirror MicroPython's constructors, `id`, positional-only `stop`, and `machine.UART`/`SPI`'s parameter lists);
  `"tests/_coverage_runner.py"`, `"tests/_threshold_runner.py"` = `["S102"]` ("a runner exec()s the test file it runs");
  `"tests_scripts/test_bench_no_task_ended_completeness.py"` = `["FBT001"]` ("pytest passes parametrized values by name");
  `"tests_scripts/test_digital_twin_ci_suite_ceiling.py"` = `["A002", "N802"]` ("overrides http.server's
  log_message(format, …)" / "http.server dispatches by this exact method name, do_GET"); no entry for
  `scripts/_strip_type_checking.py`: M.SCR.070 (U27) leaves it no `visit_*` method before N802 leaves the global list (U28);
  `"scripts/build_firmware.py"`, `"scripts/_digital_twin_ci_suite.py"`, `"toolchain/setup_toolchain.py"`,
  `"toolchain/micropython_overrides.py"` = `["S603"]` (reasons as today), `_digital_twin_ci_suite.py` also `"PLW0603"`
  ("the pass label the log helpers read") unless U27 passes it explicitly first; `"tests_hardware/harness.py"`,
  `"tests_hardware/bench_control.py"`, `"tests_hardware/flash/test_toolchain_flash_boot.py"`,
  `"tests_hardware/manual/manual_toolchain.py"` = `["S603", "S607"]` (as today); `"tests_hardware/http_client.py"` =
  `["S310"]` (as today); `"tests_hardware/bench/test_bus_concurrency_under_api_load.py"` = `["S112"]` with "# S112:
  injected packet loss makes individual request failures the fault itself; they are counted, and floored, never logged
  one by one.";
  credential block, directly above its entries: "# S105/S106 stay on everywhere else, so a new credential in keyword or
  assignment form is caught. The hotspot fallback password is accepted permanently (owner, 2026-09-26; SPECIFICATION.md
  A.11); it lives in `_VAL_HOTSPOT_PW` and devices/*.toml, a shape these rules do not see." / "# Literal passwords of
  test doubles and bound checks (the twin's own AP, fake WLAN calls, length limits) - not credentials." —
  `"digital_twin/launch.py"` = `["S105"]`, `"tests/test_digital_twin_network_neopixel.py"` = `["S106"]`,
  `"tests/test_asy_wifi_service.py"` = `["S106"]`, `"tests_scripts/test_buildgen_validate.py"` = `["S105"]`;
  `"tests/test_digital_twin_uart_link.py"` = `["PERF401"]` ("MicroPython compiles no await inside a comprehension
  (py/compile.c, v<pin>)") only if ruff still flags the two-statement body (A.U28.28 (7));
  named function-level imports (SPEC F.1) each get a per-file `PLC0415` entry with the F.1 reason, e.g.
  `"digital_twin/_http_client.py"` = `["PLC0415"]` ("tests/ is absent from a standalone twin's path, so _strict_json is
  imported where used, SPECIFICATION.md F.1").
  Rule for files born later (agent decision D8): a new host file that spawns the repo's own interpreter or scripts
  (`scripts/_twin_process.py`, `scripts/_digital_twin_scenarios.py`, `tests_hardware/twin_board.py`, …) gets its `S603`
  (and `S607` where the tool resolves from `PATH`) entry in the unit creating it, worded as the `_digital_twin_ci_suite.py`
  reason, only when ruff reports it.
  Gone from HEAD's block: every `ANN401` entry and the six category comments; `"src/asy_wifi_service.py"`'s `S106`;
  `"tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py"`; the three `tests_hardware/` `S105`
  copies; `"tests/_webserver_concurrency_scenarios.py"`; `"tests_scripts/test_setup_toolchain_env.py"`'s
  `FBT001`/`FBT002` if A.U21.17's trial passes; `ARG004` everywhere, `ARG002` from `tests_scripts/**`, `ARG005` from
  `tests_hardware/**`; each scope's `PLC0415` once its pending list is empty.
- **Resolved**: (1) A.U37.02 gives a surviving named function-level import an inline `# noqa: PLC0415`, A.U28.28 (9) a
  per-file entry: settled by the owner's rule (owner, 2026-09-10, `2badee1`, L44, restored by OR83/OR83.a: "exemptions
  live centrally … never as scattered `# noqa`"; an inline form stands only where ruff has no per-file expression, which
  PLC0415 has) — per-file entries. (2) A.U11.38 adds `["ANN401", "T20"]` to `print_log`, A.U11.S03 removes ANN401 —
  `["T20"]` under the renamed key (A.U10.37 lands in U10, before both; AC_NOTES 4-a). (3) A.U19.17 rewrites the category-2
  comment to name only `digital_twin/_http_client.py`; A.U25.63 (later) removes that file's `Any` — the entry and comment
  go (M_TWIN gap). (4) A.U28.29 keeps the three `tests_hardware/` copy entries "until A.U26.49 removes the literals":
  A.U26.49 lands in U26, so the U28 block has no copy group. (5) A.U28.28's isl29125_conformance `S603` entry: dropped
  (M.HW_BENCH.038, above).
- **Unit**: U28 (the restructure). Stages (each removal or rename lands with the unit that makes it true, so lint stays
  green, OR6.a): U0 — A.U0.35/A.U0.39 comment words at HEAD's lines; U5 — PLR0913 entries (A.U5.17); U10 — the two key
  renames (A.U10.37), N801 entries (A.U10.38); U11 — T20 entries and `print_log`'s ANN401 → T20 (A.U11.38, A.U11.S03);
  U15 — SGP40 ANN401 (A.U15.43); U19 — webserver `S101`/`ANN401` go, category-2 comment (A.U19.05, A.U19.17); U21 —
  `test_setup_toolchain_env.py` trial (A.U21.17); U22 — notification ANN401 (A.U22.04); U24 — the `tests/` and
  `tests_scripts/` ANN401 entries (A.U24.73, A.U20.32), `tests/**` PLC0415 when empty; U25 — the twin's ANN401 entries
  (A.U25.63), the concurrency-library entry (file deleted), `digital_twin/**` PLC0415 → the named per-file entry
  (A.U25.42); U26 — repro S106 (A.U26.19), copy S105s (A.U26.49), S112 comment (A.U26.54), `tests_hardware/**` PLC0415
  (M.HW_BENCH B6); U27 — `tests_scripts/**` PLC0415 when empty; U28 — the groups, inline-noqa moves, credential block,
  generated entry, liveness removals; U34 — confirm no ANN401 entry or category comment is left (A.U34.11); U37 — DONE
  check (A.U37.02).
- **Depends**: M.TOOL.028 (same scheme), M.TOOL.031 (pyflakes table), M.TOOL.011 (generated tree in ruff's scope);
  A.U20.14/M.GEN.003 (the emitted `_HOTSPOT_PW_DEFAULT`, GEN) before the generated entry carries no S106.
- **Blast carried by**: inline `noqa` removals in `src/`, `tests/`, `tests_hardware/`, `digital_twin/`, `scripts/` →
  A.U28.28 (per-file owners: SRC_NET, TEST_UNIT, TEST_HELP, HW_DEV, HW_BENCH, TWIN, SCR — each named in their merges);
  `test_ruff_exemptions_live.py`, `test_suppression_form.py` → A.U28.31, A.U28.30 (TSC); `test_lint_ceilings.py` exempt
  set → A.U5.18 (TSC); CLAUDE.md per-file sentence → A.U28.34 (DOCS); SPEC D.6/B.15 groups → A.U28.27 (SPEC); BACKLOG
  chroot "lint config only" lines → A.U5.17/A.U28.38 (DOCS); missing chroot lines → Gaps.
- **Kind**: code, rule

### M.TOOL.031 One pyflakes table names the side-effect imports
- **From**: A.U20.14 (3) (`frozen_html`), A.U28.28 (4) (the five manual modules; the two F401 `noqa` go),
  M.HW_BENCH.106 (U26: the manual imports move into `tests_hardware/manual/__main__.py` and rely on this table).
- **Site**: `pyproject.toml`, new `[tool.ruff.lint.pyflakes]` table after `[tool.ruff.lint.pydocstyle]`.
- **Change**: "# Imported for their side effect: frozen_html mounts the website; the manual modules register their
  tests." / `allowed-unused-imports = ["frozen_html", "manual_bus_electrical", "manual_persistence",
  "manual_sensor_accuracy", "manual_toolchain", "manual_wifi"]`.
- **Resolved**: A.U20.14 and A.U28.28 write the same key — one table (A.U28.28's own note). Staging forced by RUF100: the
  day a name joins the table, every inline `# noqa: F401` on an import of it becomes unused and fails lint, so each name
  lands with its noqa's removal.
- **Unit**: U28 (final text). Stages: U20 — `["frozen_html"]` with the inline `noqa: F401` at
  `tests/test_website_build_integration.py:15` removed in the same commit (the generated module's own suppression is
  already gone, A.U20.14); U26 — the five manual names, with M.HW_BENCH.106's module-level imports in `__main__.py`
  (no inline noqa there) and `runner.py:72-76`'s noqa lines gone with the moved imports.
- **Depends**: A.U20.14 (GEN), M.HW_BENCH.106 (HW_BENCH).
- **Blast carried by**: the `test_website_build_integration.py:15` noqa removal pulled into U20 → Gaps (TEST_UNIT);
  `test_ruff_exemptions_live.py` → A.U28.31 (TSC).
- **Kind**: code

### M.TOOL.032 Main mypy pass: vendored Microdot stub, unixport shims, generated sources, strict flags
- **From**: A.U8.23 (`mypy_path` gains `"ext/typings"`; firm by OR131 / AC_NOTES 41, GEN Q1 (a)), A.U18.12 (`mypy_path`
  gains the shim directory, `digital_twin/unixport` per M.TWIN), A.U27.09 (`files` gains `build/generated_src`), A.U27.25
  (`:363-364` comment), A.U26.44 (`:363`/`:370` comment — superseded), A.U8.24 (`disallow_any_explicit = true`), A.U27.22
  (`enable_error_code`), A.U27.23 (`:377` exclude comment), A.U25.40 (`:383` exclude goes), A.U25.46/M.TEST_HELP.031
  (`tests/_webserver_concurrency_scenarios.py` deleted: its exclude and comment go), M.TWIN.108 (the six construction
  wrappers become one file: the `:388-389` comment follows), A.U0.21 (owned by A.U8.23), GAPS_G3 hand-off 1 / A.U26.05
  (`digital_twin/run_device_script.py` excluded, M_TOOL gap 9's rule, gap pass).
- **Site**: `pyproject.toml:353-406` (`[tool.mypy]`).
- **Change**: `platform`, `python_version` and comment, `follow_imports = "silent"`, `follow_imports_for_stubs` and their
  comments unchanged. `:363-365` → "# typings/ is the board stub tree, ext/typings/ the vendored upstream Microdot stub,
  digital_twin/unixport/ the Unix-port shims (no hardware fake there); build/generated_src holds the generated device
  modules (checked as sources) and the twin pass's imports - typecheck.sh generates it first." / `mypy_path = ["typings",
  "ext/typings", "src", "digital_twin/unixport", "build/generated_src"]`. `custom_typeshed_dir`, `no_site_packages`, the
  `files` comment unchanged; `files = ["src", "tests", "digital_twin", "tests_hardware/device_scripts",
  "build/generated_src"]`. Exclude comment `:373-375` → "# Excluded, each for a reason B.15 states: tests/network.py would
  hijack the real `network` stub project-wide, so typecheck.sh checks it alone; the twin's fakes collide with
  tests/machine.py; the rest need the twin's own API, so digital_twin/typecheck.ini checks them."; `exclude` = the
  seven entries `tests/network\\.py$`, `digital_twin/machine\\.py$`, `digital_twin/network\\.py$`,
  `digital_twin/neopixel\\.py$`, `digital_twin/launch\\.py$`, `digital_twin/run_generic_integration\\.py$`,
  `tests/test_digital_twin_.*\\.py$`, then "# The shared construction scenario library (leading underscore, so the glob
  above misses it), same reason." / `tests/_digital_twin_construction_scenarios\\.py$`, then (U26, gap pass G3 hand-off 1)
  `digital_twin/run_device_script\\.py$` under the block's reason — it calls the twin-only `machine.configure_wiring()`,
  which `tests/machine.py` lacks (M.TWIN.054; confirmed at landing by running the main pass). A new `digital_twin/` module
  that needs the twin's own `machine`/`network` API joins this list in the unit creating it, with the block's reason
  (agent decision D9; the twin pass's `digital_twin` glob checks it, G8/R47). Strictness: `strict = true` and its
  comment, then "# a bare `# type: ignore` is itself an error, so no suppression hides its code" / `enable_error_code =
  ["ignore-without-code"]`, then `disallow_any_explicit = true`; `no_implicit_optional`, `warn_unreachable`,
  `no_implicit_reexport = false` and their comments unchanged.
- **Resolved**: A.U26.44 (U26) rewrites the `:363`/`:370` comment to "the generated modules typecheck.sh writes";
  A.U27.25 (U27, later) gives the final text and states "A-C keeps this text" — kept, extended by the two new path
  entries. A.U8.24 and A.U27.22 edit the strictness lines — one edit per config (A.U27.22 Depends). A.U27.23 writes the
  twin pass's `files` after U25 retired the concurrency library — that file leaves this exclude list in U25 too (A.U27.23's
  own rule "a file A.U25.46/A.U24.65 retires leaves the list with it").
- **Unit**: U27. Stages: U8 — `"ext/typings"` with A.U8.23's ignore removals in `src/`/`tests/` (same commit: under
  `warn_unused_ignores` a resolved import makes those ignores errors) and `disallow_any_explicit` (A.U8.24, U8's end);
  U18 — `"digital_twin/unixport"` with the shim's move (A.U18.12, M.TWIN); U24 — the construction-library comment
  (M.TWIN.108); U25 — `segfault_stress_repro` and `_webserver_concurrency_scenarios` excludes go (A.U25.40, A.U25.46);
  U26 — A.U26.44's interim comment and the `run_device_script` exclude (with M.TWIN.054's file); U27 — `files`, the final comments, `enable_error_code` (A.U27.09, A.U27.22-.25).
- **Depends**: M.GEN.050/M.GEN.051 (the stub files vendored in U0's re-vendor); M.TWIN.053/.075 (unixport directory);
  M.TOOL.033.
- **Blast carried by**: `tests_scripts/test_lint_type_scopes.py` (strictness flags in all three configs; CI paths ==
  `files`) → A.U27.24 (TSC); `test_config_paths_resolve.py` (every `mypy_path`/`files` entry resolves; `build/generated_src`
  excepted) → A.U28.39 (TSC); `digital_twin/typecheck.ini`, `host_typecheck.ini` same flags → M.TWIN.075, M.TOOL.079 (TWIN, TOOL;
  gap pass); CLAUDE.md mypy and vendoring bullets, SPEC B.15/A.1 → A.U8.23, A.U27.22 (DOCS, SPEC); BACKLOG chroot entries
  → A.U27.09/A.U27.22/A.U27.23 (DOCS), U8/U18/U25 lines → Gaps.
- **Kind**: code, rule

### M.TOOL.033 Mypy overrides: the decorator exemption retires, frozen_html is declared, the Any baseline empties
- **From**: A.U8.23 (override reason restated; "Revisit if Microdot ships hints" goes), A.U0.21 (owned by A.U8.23),
  A.U27.07 (override removed with the test's last decorated route), A.U20.14 (3) (`frozen_html` override), A.U8.24
  (baseline block), A.U10.46, A.U11.S01, A.U11.S02, A.U11.S03, A.U15.43, A.U16.S01, A.U17.26, A.U18.44, A.U19.17,
  A.U20.32, A.U22.04, A.U23.47, A.U24.73, A.U25.63 (modules leave the baseline), A.U34.11 (block removed), A.U37.02 (DONE
  check).
- **Site**: `pyproject.toml:408-413` (`[[tool.mypy.overrides]]`) and two new override blocks.
- **Change**: end state: the `test_setter_microdot_integration` override and its comment are gone; one block remains:
  "# frozen_html is the frozen website the generated modules import only to mount it; it exists on no search path." /
  `[[tool.mypy.overrides]]` / `module = "frozen_html"` / `ignore_missing_imports = true`. No baseline block.
- **Resolved**: A.U8.23 (U8) keeps the decorator override with the reason "upstream stub leaves `route/get/put`
  unannotated (v<vendored tag>)"; A.U27.07 (U27) removes it once no decorated local route remains and says so ("if its
  override restatement lands first, this action removes the override it restated") — removed in U27.
- **Unit**: U34 (end state). Stages: U8 — the override's comment → "# Upstream's stub leaves route/get/put unannotated
  (v<vendored Microdot tag>): every handler they decorate is untyped under --strict; this is the one file registering
  real routes." (A.U8.23; "Revisit if Microdot ships hints" goes), and the baseline block after U8's B1 foundations:
  "# baseline: a module leaves this list once its explicit-Any findings are cleared; the list ends empty (owner,
  2026-09-28)." / `module = [<modules with findings, from A.U0.06's per-pass counts>]` / `disallow_any_explicit = false`;
  U10-U34 — each clearing action drops its modules (the constituents above); U20 — the `frozen_html` block (A.U20.14);
  U27 — the decorator override goes (A.U27.07); U34 — the empty baseline block goes (A.U34.11; A.U37.02 records DONE).
- **Depends**: M.TOOL.032 (flags), A.U27.07's rewire of the test (TEST_UNIT).
- **Blast carried by**: `tests_scripts/test_mypy_any_baseline.py` (baseline modules exist; then no `false` anywhere) →
  A.U8.24/A.U34.11 (TSC); CLAUDE.md `disallow_untyped_decorators` sentence → A.U27.07/A.U36.527 (DOCS); `disallow_any_
  unimported` count parked for the owner under OR2.c → A.U34.11 (PROC).
- **Kind**: code

### M.TOOL.034 pytest: strict markers and the repo root on the path
- **From**: A.U26.74 (1) (`addopts`), A.U27.37 (`pythonpath`).
- **Site**: `pyproject.toml:415-418` (`[tool.pytest.ini_options]`).
- **Change**: comment `:416-417` kept; `testpaths = ["tests_scripts"]`; "# A misspelled or renamed marker fails collection
  instead of running ungated (the wear and soak gates, tests_hardware/conftest.py)." / `addopts = ["--strict-markers"]`;
  "# The repo root, for tests_scripts/'s buildgen and scripts/ imports." / `pythonpath = ["."]`.
- **Resolved**: —
- **Unit**: U27. Stage U26: `addopts` (A.U26.74).
- **Depends**: —
- **Blast carried by**: `tests_scripts/conftest.py:18` insert goes → A.U27.37 (TSC); marker registration and flag renames
  → A.U26.74 (HW_BENCH, TSC); BACKLOG chroot "pytest pythonpath = ['.']" → A.U27.37 (DOCS), `addopts` line → Gaps.
- **Kind**: code

## toolchain/micropython_overrides.py

### M.TOOL.035 Module head: no future import, explanations as comments, one error class family
- **From**: A.U20.33 (the `__future__` import goes), A.U10.34 (function/class docstrings → `#` comments; the module
  docstring stays), A.U27.29 (2) (`OverrideError` derives from `Exception`).
- **Site**: `toolchain/micropython_overrides.py:1-28` (docstring, imports, `OverrideError`, `_read_anchor_source()`), and
  every function/class docstring in the file (`:16-18`, `:61-63`, `:143-145`, `:191-193`, `:206-208`, `:257`, `:307-309`,
  `:356-357`, `:392-393`, `:406-408`, `:449-450`).
- **Change**: module docstring `:1-3` unchanged. `from __future__ import annotations` goes; imports `ast`, `re`,
  `shlex`, `struct` (M.TOOL.040), `subprocess`, `tempfile`, `Path`. `class OverrideError(Exception):` with its docstring
  as a `#` comment block under the `class` line ("# A pinned MicroPython source no longer matches what an override
  expects, so the override was NOT applied. Re-verify against the new source and update the anchor/generated content
  (SPECIFICATION.md B.14) - never silence this by removing the check.") and `pass`. Every function docstring in the file,
  existing or added by M.TOOL.036-.042, is a `#` block directly under its `def` line, ≤ 3 lines (overflow to SPEC B.14).
- **Resolved**: —
- **Unit**: U27 (A.U27.29). Stages: U10 — docstrings → comments at HEAD's functions (A.U10.34); U20 — the future import
  (A.U20.33); later units write new functions in the comment form.
- **Depends**: —
- **Blast carried by**: `pytest.raises(OverrideError)` holds (same class, base changed) and any `except RuntimeError`
  catching it (grep at execution) → A.U27.29 (TSC); `test_comment_block_cap.py` over `toolchain/` → A.U10.34 (TSC);
  `test_host_annotations.py` → A.U20.33 (TSC); `buildgen/validate.py`'s by-path load of this module keeps working (it
  imports only stdlib) → A.U10.30 (GEN).
- **Kind**: code

### M.TOOL.036 One guard for every path written into generated files
- **From**: A.U21.08 (`_embeddable()`; quoting of CMake/manifest includes).
- **Site**: new `_embeddable(path: Path, what: str) -> Path` after `_read_anchor_source()`; its callers in M.TOOL.037-.040.
- **Change**: returns `path.resolve()`, or raises `OverrideError(f"{what}: the path {path} contains {char!r}, which the
  generated make/CMake/C/manifest text cannot carry - use a --toolchain-dir (or $PICO_TOOLCHAIN_DIR) without whitespace,
  quotes, backslashes, '$', '#', ';' or ':'")` when the resolved path contains whitespace or any of `"\\$#;:'`. Every
  `apply_*()` passes `micropython_dir` and `overrides_dir` through it before any `mkdir`, so every path written is
  absolute and clean; comment "# paths are resolved, and refused when a generated file cannot carry them".
- **Resolved**: —
- **Unit**: U21.
- **Depends**: —
- **Blast carried by**: `test_micropython_overrides.py` new cases (space, quote, relative dir) and the changed include
  forms → A.U21.08 (TSC); `scripts/build_firmware.py` resolves `--toolchain-dir` → A.U21.08 (SCR); SPEC B.14, B.2 →
  A.U21.08 (SPEC).
- **Kind**: code

### M.TOOL.037 unix_kbd_intr: sentinel, one header writer, permanent pointers
- **From**: A.U21.06 (a) (sentinel define; `UNIX_KBD_INTR_SENTINEL`), A.U21.12 (the host variant reuses the same header
  text, "produced by the same helper"), A.U21.08 (`_embeddable`, manifest `include({str(p)!r})`, the make `include`
  stays unquoted), A.U36.544 (`:34` ", CLAUDE.md's Part F.6 entry" deleted; `:55` "CLAUDE.md/SPECIFICATION.md Part F.6" →
  "SPECIFICATION.md B.14.1"; `:70` "/ CLAUDE.md Part F.6" deleted), A.SDEP.11 (re-check at the new pin; outcome (c)
  retires the override), A.U21.16 (2b) (a one-file mbedtls suppression in the generated variant makefile, only if a GCC ≥
  14 build still warns), A.U8.14 (blast: none here).
- **Site**: `toolchain/micropython_overrides.py:31-84`.
- **Change**: banner prose `:32-34` → "unix_kbd_intr: force the Unix port's "standard" variant to use MicroPython's own
  SAFE, deferred SIGINT-delivery path instead of its default immediate one. Full account: SPECIFICATION.md Part B.14.1."
  `_UNIX_KBD_INTR_ANCHOR` and its comment unchanged; new `UNIX_KBD_INTR_SENTINEL =
  "MICROPY_SENSORS_KBD_INTR_OVERRIDE_APPLIED"`. `verify_unix_kbd_intr_anchor()`'s message: "…update this override's
  anchor and generated #undef/#define pair accordingly - SPECIFICATION.md Part B.14.1. Do NOT remove this check and build
  unpatched: an interrupt mid critical section can corrupt VM state (reproduced as a garbled, impossible traceback -
  SPECIFICATION.md B.14.1)." New `_unix_kbd_intr_header(real_variant_dir: Path) -> str` returning `#include
  "<real>/mpconfigvariant.h"`, `// SPECIFICATION.md Part B.14.1: force MicroPython's own safe,`, `// deferred
  SIGINT-delivery path - see toolchain/micropython_overrides.py.`, `#undef MICROPY_ASYNC_KBD_INTR`, `#define
  MICROPY_ASYNC_KBD_INTR (0)`, `#define MICROPY_SENSORS_KBD_INTR_OVERRIDE_APPLIED 1`. `apply_unix_kbd_intr_override()`:
  `_embeddable()` both dirs; writes the header through the helper; `mpconfigvariant.mk` `include <real>/mpconfigvariant.mk`
  (unquoted: GNU make takes none; the refusal guards it) plus, under A.U21.16 2b only, `$(BUILD)/lib/mbedtls/library/
  ctr_drbg.o: CFLAGS += -Wno-array-bounds` with a one-line reason; `manifest.py` `include({str(real_manifest)!r})`;
  returns `{"VARIANT": "standard", "VARIANT_DIR": str(override_dir)}` as today. A.SDEP.11 outcome (c) (upstream made
  deferred delivery the Unix default): this section, its call in `build_unix_port()` and `"unix_kbd_intr_variant"` in
  M.TOOL.042 go; M.TOOL.041's kbd proof keeps its deferred-branch check without the sentinel half; outcome (b): the anchor
  and generated pair re-derived first.
- **Resolved**: A.U36.544's `:70` edit lands in the emitted C comment, which M.TOOL.037's helper now writes — one text.
- **Unit**: U21. Stages: U0 — A.SDEP.11's re-check (outcome recorded; (b)/(c) act here); U36 — none left (A.U36.544's
  pointer edits land with U21's rewrite of the same lines; A.U36.544 records DONE).
- **Depends**: M.TOOL.036; A.SDEP.08 (the pin).
- **Blast carried by**: `test_micropython_overrides.py:83-96` (sentinel line), `:105-112` (`!r` manifest), the fake
  `make` branches for `unix_mphal.pp` → A.U21.06/A.U21.08 (TSC); SPEC B.14.1 → A.U21.06 (SPEC); CLAUDE.md F.6/shutdown
  bullets under (c) → A.SDEP.11 (DOCS).
- **Kind**: code

### M.TOOL.038 lwip_connection_counts: quoted includes, tagged floors, true comments, a named floor
- **From**: A.U21.08 (CMake `include("…")`, manifest `!r`, `_embeddable`), A.U8.14 (tags `lwip.mem_size_per_connection_
  floor = 2000`, `lwip.spare_tcp_pcbs = 3`), A.U21.31 (`:175-177`, `:269-271` comments), A.U14.30 (3) (`:263-265`
  comment), A.U36.544 (`:265` "Part H.7" → B.14.2), A.U28.28 (5) (`_MIN_TCP_SND_QUEUELEN`, the `noqa: PLR2004` goes),
  A.SDEP.14 (21 anchors and the ensemble re-verified at the new pin), A.U21.12 (the redefine text shared with the host
  build), A.U21.16 (2b) (a one-file mbedtls suppression in the generated board cmake), A.U18.18/A.U26.03 (blast: the
  `> 0` UDP check and `check_lwip_ensemble()`'s public signature stay).
- **Site**: `toolchain/micropython_overrides.py:87-343`.
- **Change**: `:175-177` → "# 2,000 B = MicroPython's own MEM_SIZE 8000 (lwipopts_common.h) over the refactor's earlier
  max_connections 4 (agent, 2026-09-22). A relationship, not a tuning target: raising the ceiling may not shrink a
  connection's share of the arena every outbound byte is copied into." then `# @tunable lwip.mem_size_per_connection_floor
  = 2000` directly above `MEM_SIZE_BYTES_PER_CONNECTION_FLOOR = 2000`; the `SPARE_TCP_PCBS` comment kept, then `#
  @tunable lwip.spare_tcp_pcbs = 3` above it; beside `_MEM_ALIGNMENT`/`_U16_MAX`: `_MIN_TCP_SND_QUEUELEN = 2  # lwIP's own
  floor, lib/lwip/src/core/init.c:157` (re-checked against the refreshed lwIP), and `check_lwip_ensemble()` compares
  `queuelen < _MIN_TCP_SND_QUEUELEN` with the message naming the constant, no `noqa`; `:263-265` → "# Segments are a
  GLOBAL pool while TCP_SND_QUEUELEN is PER connection, so one connection can drain the pool. / # Every admitted
  connection gets a full window of full-MSS segments; short writes and / # closing pcbs can still drain it
  (SPECIFICATION.md Part B.14.2.1)." (the check and its message unchanged); `:269-271`'s last sentence → "Its
  per-connection share may not fall below the floor above." New `_lwip_redefines(macros: dict[str, int]) -> str` (the
  sentinel define plus every `#undef`/`#define` pair, `LWIP_SETTABLE_MACROS` order), used here and by M.TOOL.040.
  `apply_lwip_connection_counts_override()`: `_embeddable()` both dirs; header body from `_lwip_redefines()`; board cmake
  `include("<real board>/mpconfigboard.cmake")` (quoted) and, under A.U21.16 2b only,
  `set_source_files_properties("${MICROPY_DIR}/lib/mbedtls/library/ctr_drbg.c" PROPERTIES COMPILE_OPTIONS
  "-Wno-array-bounds")` with a one-line reason; `manifest.py` `include({str(...)!r})`; returns as today. A.SDEP.14: a
  moved macro or formula at the new pin updates the tuples, the anchors and the ensemble together.
- **Resolved**: A.U14.30 (U14) and A.U36.544 (U36) rewrite `:265`'s pointer — A.U14.30's "Part B.14.2.1" (a subsection
  of A.U36.544's B.14.2, the section that now states the fact) satisfies both; A.U21.31 asks A-C to merge its wording
  into A.U14.30's — they touch different lines (`:269-271` vs `:263-265`), both kept.
- **Unit**: U21. Stages: U0 — A.SDEP.14's re-check (anchor/tuple changes if the pin moved); U8 — the two tags (A.U8.14);
  U14 — `:263-265` (A.U14.30); U28 — `_MIN_TCP_SND_QUEUELEN` (A.U28.28 (5)).
- **Depends**: M.TOOL.036.
- **Blast carried by**: `test_micropython_overrides.py:398-418` (quoted include, `!r`), `:643-646` test rename, ensemble
  cases → A.U21.08/A.U21.31/A.SDEP.14 (TSC); `tests_scripts/test_buildgen_validate.py` ensemble cases → A.SDEP.14 (TSC);
  Part N rows `lwip.*` → A.U8.14 (SPEC); SPEC B.14.2/B.14.2.1, H.7 → A.U14.30/A.SDEP.14 (SPEC); `buildgen/validate.py`'s
  per-device check (same API) → A.SDEP.14 (GEN).
- **Kind**: code, doc

### M.TOOL.039 modlwip_eagain: a patched copy of modlwip.c swapped into every rp2 build
- **From**: A.U21.09 (constants, anchors, `apply_modlwip_eagain_override()`), A.SDEP.13 (decided against the refreshed
  pin first), A.U21.10 (its readback, M.TOOL.041), A.U21.08 (`_embeddable`).
- **Site**: new section after `:343` (before the readback section).
- **Change**: as A.U21.09's Change, in full: banner (≤ 3 prose lines) "modlwip_eagain: a non-blocking modlwip send returns
  EAGAIN on ERR_MEM instead of retrying for up to 10 s inside one call (micropython issue 19704). Removed, not re-anchored,
  once the pin carries a real fix (owner, 2026-09-30). Full account: SPECIFICATION.md B.14."; `MODLWIP_OVERRIDE_DIR_NAME =
  "modlwip_eagain"`, `_MODLWIP_ERR_MEM_LOOP` (the verbatim retry loop of the pinned `extmod/modlwip.c`), `_MODLWIP_INSERT_AFTER`,
  `_MODLWIP_EAGAIN_BLOCK` (upstream PR 19708's change), `_MODLWIP_LOCAL_INCLUDE` and its rewrite to `#include
  "extmod/modnetwork.h"`; `verify_modlwip_eagain_anchor(micropython_dir)` (each anchor exactly once, the CMake/Makefile/
  usermod order checks by `str.index`, the message tail naming issue 19704 and SPECIFICATION.md B.14);
  `apply_modlwip_eagain_override(micropython_dir, overrides_dir) -> dict[str, str]` writing `modlwip_eagain/modlwip.c`
  (the pinned text with the block inserted and the include rewritten, no `#line`, prefixed by "// Generated by
  toolchain/micropython_overrides.py from extmod/modlwip.c of MicroPython <X.Y.Z> - SPECIFICATION.md B.14. Do not edit.",
  `<X.Y.Z>` read from `py/mpconfig.h`'s `MICROPY_VERSION_MAJOR/MINOR/MICRO` defines — agent decision D15, since the
  function is not handed the ref) and `modlwip_eagain/micropython.cmake` (byte text as A.U21.09), returning
  `{"USER_C_MODULES": str(overrides_dir / MODLWIP_OVERRIDE_DIR_NAME)}`. Every anchor and line citation is the refreshed
  pin's (A.SDEP.13 (b): re-derived at the new tag before landing). No `TCP_NODELAY` anywhere (OR114.a (2)); `[lwip]` keeps
  its values (OR114.a (3)). A.SDEP.13 outcome (a) (the pin carries a real fix): this section is not written, and the
  BACKLOG watch entry with it.
- **Resolved**: A.U21.09's "at <pinned ref>" header text — the apply function has no ref parameter; the version comes
  from the checkout's own `py/mpconfig.h` (D15), the toolchain record ties the directory to its exact ref (A.U21.03).
- **Unit**: U21. Stage U0: A.SDEP.13's decision and, under (b), the re-derived anchor texts in the action file (audit
  working copy, A.SDEP.23).
- **Depends**: M.TOOL.036; A.SDEP.13.
- **Blast carried by**: `build_firmware()` → M.TOOL.055; L0 tests `TestVerifyModlwipEagainAnchor`,
  `TestApplyModlwipEagainOverride` (module-level per A.U24.75) → A.U21.11 (TSC); SPEC B.14 subsection, B.14.2.1 stall
  sentence → A.U21.09/A.U14.30 (SPEC); CLAUDE.md "Platform target" addition, BACKLOG watch item and chroot entry →
  A.U21.09 (DOCS); phase C → A.U21.14 (PROC).
- **Kind**: code

### M.TOOL.040 unix_lwip_host: a third Unix binary that runs the real patched modlwip over loopback lwIP
- **From**: A.U21.12 (`apply_unix_lwip_host_override()` and its generated variant), A.SDEP.13 (a) (the host build then
  compiles upstream's `modlwip.c`), A.SDEP.11 (c) (the kbd header part drops if upstream made it the default), A.U21.16
  (2b) (one-file suppressions in this variant's makefile), A.U21.08 (`_embeddable`).
- **Site**: new section after M.TOOL.039's.
- **Change**: as A.U21.12's Change: `apply_unix_lwip_host_override(micropython_dir, overrides_dir, lwip_macros) ->
  dict[str, str]` verifying the kbd anchor, the modlwip anchors and the host anchors (`extmod.mk`, the Unix `Makefile`,
  `py/mkrules.mk`'s `vpath`, `py/mphal.h`'s hook guard, `poll_sockets()`, `opt.h`'s loopback lines,
  `lib/lwip/src/core/tcp_out.c` exists), then writing under `_embeddable()` the directory `unix_lwip_host_variant/`:
  `mpconfigvariant.h` (`_unix_kbd_intr_header()` text plus `void mp_lwip_host_poll(void);` and `#define
  MICROPY_INTERNAL_EVENT_HOOK mp_lwip_host_poll()`), `mpconfigvariant.mk` (`include <real standard mk>`, `INC +=
  -I<variant>/lwip_inc`, `vpath extmod/modlwip.c <variant>/src`, and any first-build host-only `$(BUILD)/<file>.o: CFLAGS
  += -Wno-<name>` lines, each with a one-line reason and listed in SPEC B.7), `manifest.py` (relay), `src/extmod/modlwip.c`
  (M.TOOL.039's generator, same bytes), `lwip_inc/lwipopts.h` (rp2's settings, the common include, `MEM_ALIGNMENT` from
  `struct.calcsize("P")` as an integer literal, `_lwip_redefines(lwip_macros)`, `LWIP_RAND()`), `lwip_inc/arch/cc.h`
  (loud `LWIP_PLATFORM_ASSERT`), `lwip_inc/arch/sys_arch.h`, `lwip_host_port.c`; returns `{"VARIANT": "standard",
  "VARIANT_DIR": …, "BUILD": "build-lwip", "MICROPY_PY_LWIP": "1", "MICROPY_PY_LWIP_LOOPBACK": "1", "MICROPY_PY_SOCKET":
  "0"}`. Under A.SDEP.13 (a): no copy, no `vpath`; its readback proves the original is compiled. Under A.SDEP.11 (c): the
  header carries only the hook lines.
- **Resolved**: —
- **Unit**: U21.
- **Depends**: M.TOOL.036, M.TOOL.037, M.TOOL.038, M.TOOL.039.
- **Blast carried by**: `build_unix_lwip_port()` → M.TOOL.056; `scripts/test.sh` lwIP file set and rebuild condition →
  A.U21.12 (SCR); `scripts/_unix_port.sh` `lwip` flavour → A.U27.12 (SCR); `tests/lwip_host/` hammer → A.U21.13
  (TEST_UNIT); L0 classes → A.U21.12 (TSC); SPEC B.2/B.5/B.6/B.14/E.1/E.3/F.7, CLAUDE.md "three binaries", README →
  A.U21.12 (SPEC, DOCS); CI `unit-tests` budget → M.TOOL.019.
- **Kind**: code

### M.TOOL.041 Readback section: the timeout is tagged; three new post-build proofs
- **From**: A.U8.14 (`tool.preprocess_timeout_s = 120`), A.U21.06 (b) (`verify_unix_kbd_intr_in_build()`), A.U21.10
  (`verify_modlwip_eagain_in_build()`), A.U21.12 (`verify_unix_lwip_host_in_build()`), A.U26.02 (blast:
  `read_lwip_macros_from_build()` stays public for the image record), D16 (the caller hands its environment in).
- **Site**: `toolchain/micropython_overrides.py:346-466` and three new functions after `:466`.
- **Change**: `# @tunable tool.preprocess_timeout_s = 120` directly above `_PREPROCESS_TIMEOUT_S = 120`. New
  `verify_unix_kbd_intr_in_build(unix_dir: Path, make_vars: dict[str, str], build_dir_name: str, *, env: dict[str, str])`
  as A.U21.06 (b): `make <same vars> <build_dir_name>/unix_mphal.pp` in `ports/unix` (timeout `_PREPROCESS_TIMEOUT_S`),
  then the sentinel define present, the last `MICROPY_ASYNC_KBD_INTR` define `(0)`, the preprocessed `sighandler()` body
  holding `mp_sched_keyboard_interrupt()` and no `nlr_jump(`, each miss a named `OverrideError`, the `.pp` deleted after.
  New `verify_modlwip_eagain_in_build(build_dir: Path, micropython_dir: Path, copy_path: Path)` as A.U21.10 (the
  firmware target's `build.make` names the copy and not the original; exactly one non-empty `…modlwip.c.obj` on the
  copy's path; the executor pins `build.make`'s source-line form and the object path as constants on the first real
  build). New `verify_unix_lwip_host_in_build(build_dir: Path, micropython_dir: Path, binary: Path, *, env: dict[str,
  str])` as A.U21.12 (`build-lwip/extmod/modlwip.P` names the copy and not the original; `<binary> -c "import lwip,
  socket; print(socket is lwip)"` prints `True`, timeout `_PREPROCESS_TIMEOUT_S`). `env` is passed by
  `setup_toolchain.py` (its `build_env()`), since this module never imports the installer (D16).
- **Resolved**: A.U21.06 runs the preprocess "with `build_env()`", which lives in `setup_toolchain.py`, the importer of
  this module — the function takes `env` as a keyword rather than importing it back (D16).
- **Unit**: U21. Stage U8: the tag (A.U8.14).
- **Depends**: M.TOOL.037, M.TOOL.039, M.TOOL.040.
- **Blast carried by**: callers → M.TOOL.055, M.TOOL.056; L0 `TestUnixKbdIntrBuildReadback`, `TestModlwipBuildReadback`,
  `TestUnixLwipHostBuildReadback` → A.U21.06/.11/.12 (TSC); A.U26.02's record reads `read_lwip_macros_from_build()` → Gaps
  (SCR); Part N `tool.preprocess_timeout_s` → A.U8.14 (SPEC).
- **Kind**: code

### M.TOOL.042 The current override directory names, in one tuple
- **From**: A.U21.30 (`CURRENT_OVERRIDE_DIRS`).
- **Site**: new module constant after the readback section's constants.
- **Change**: `CURRENT_OVERRIDE_DIRS = ("unix_kbd_intr_variant", LWIP_OVERRIDE_BOARD_DIR_NAME,
  MODLWIP_OVERRIDE_DIR_NAME, "unix_lwip_host_variant", TICK_OFFSET_DIR_NAME)` (the last from M.TOOL.080, OR139.a, A-C
  review fold) with "# Every directory the apply_*() functions write under
  build_overrides/; setup removes any other it finds there." (`"unix_kbd_intr_variant"` and the host variant's name become
  named constants `UNIX_KBD_INTR_DIR_NAME`, `UNIX_LWIP_HOST_DIR_NAME`, used by their apply functions). A retired override
  (A.SDEP.11 (c), A.SDEP.13 (a)) leaves the tuple with its section.
- **Resolved**: —
- **Unit**: U21.
- **Depends**: M.TOOL.037, M.TOOL.039, M.TOOL.040, M.TOOL.080.
- **Blast carried by**: `remove_outdated_leftovers()` → M.TOOL.063; L0 (the tuple equals the names the apply functions
  write, read from their output) → A.U21.30 (TSC).
- **Kind**: code

### M.TOOL.080 tick_offset_test: a test-only override that starts the millisecond count 15 minutes before the wrap
- **From**: OR139.a (1), (2), (5) (A-C review fold: the rollover round's test image differs from the dev image by one
  build define, applied here as a test-only override with its anchor check, named in the build info, refused in any
  release build, its anchors re-verified at every MicroPython bump).
- **Site**: new section after M.TOOL.042's constant (before the readback section's callers).
- **Change**: banner (≤ 3 prose lines) "tick_offset_test: a TEST-ONLY build in which mp_hal_ticks_ms() returns the time
  since boot plus 2**32 ms minus 15 minutes, so ticks_ms() and the 32-bit millisecond count wrap about 15 minutes after
  boot (owner, 2026-10-01). Never in a release image. Full account: SPECIFICATION.md B.14."; constants
  `TICK_OFFSET_DIR_NAME = "tick_offset_test"`, `TICK_OFFSET_SENTINEL = "MICROPY_SENSORS_TICK_OFFSET_TEST_APPLIED"`,
  `TICK_OFFSET_MS = 2**32 - 15 * 60 * 1000` (with "# 15 minutes before the 32-bit wrap; 2**32 is also a multiple of
  ticks_ms()'s 2**30 period, so both wrap together"), and `_TICK_OFFSET_ANCHOR`, the pinned body of `mp_hal_ticks_ms()`
  in `ports/rp2/mphalport.h` (`return to_ms_since_boot(get_absolute_time());`, `:96-98` at v1.29.0, re-derived at the
  refreshed pin). `verify_tick_offset_anchor(micropython_dir)`: the anchor exactly once inside `mp_hal_ticks_ms()`, else
  `OverrideError` naming the file and "re-derive this override's anchor and its replacement (SPECIFICATION.md B.14); do
  not build the test image unpatched". `apply_tick_offset_override(micropython_dir, overrides_dir) -> dict[str, str]`
  (`_embeddable()` both dirs, M.TOOL.036) makes the pinned `mp_hal_ticks_ms()` return `(mp_uint_t)(to_ms_since_boot(
  get_absolute_time()) + MICROPY_SENSORS_TICK_OFFSET_MS)` (32-bit unsigned arithmetic, so the sum wraps), defines
  `MICROPY_SENSORS_TICK_OFFSET_MS` as `TICK_OFFSET_MS`'s literal and the sentinel `1`, and returns the make variables
  `build_firmware()` merges; the hardware timer is never written (RP2040 datasheet 4.6.2: the SDK expects it to
  increase monotonically). How the replacement reaches the inline function (a patched header copy put ahead of the
  original on the include path, as `modlwip_eagain` swaps its source, or an equivalent the pinned build allows) is
  decided at execution against the pinned `ports/rp2` build, with its reason recorded in SPEC B.14. Readers:
  `tick_offset_in_build(build_dir) -> bool` (the sentinel among the build's compile definitions, read the way
  M.TOOL.041 reads the others) and `verify_tick_offset_in_build(build_dir, *, expected: bool)` raising `OverrideError`
  on a mismatch — "a release build carries the tick-offset test override" when `expected` is false, the release
  refusal. `CURRENT_OVERRIDE_DIRS` gains `TICK_OFFSET_DIR_NAME` (M.TOOL.042).
- **Resolved**: OR139.a (1) says "one build define": the define is `MICROPY_SENSORS_TICK_OFFSET_MS`; the inline
  function's body has no hook for it at v1.29.0, so the override also supplies the one replaced line (the anchor), the
  same verify-then-apply shape as the other overrides.
- **Unit**: U21 (with the other overrides; the build-info and runner sides in U27, M.SCR.065/.067/.074).
- **Depends**: M.TOOL.035, M.TOOL.036, M.TOOL.042.
- **Blast carried by**: `build_firmware()`'s keyword and the release readback → M.TOOL.055; L0 cases (anchor present
  once → applies, anchor moved → `OverrideError`, the sentinel read back, a build without the flag carrying it →
  refused) → M.TSC.229; the image record and build info → M.SCR.067 [fold F04 M_GEN]; SPEC B.14 subsection, E.6's
  rollover paragraph → [fold F04 M_SPEC]; CLAUDE.md's version-bump practice names this anchor among the re-checked ones →
  [fold F04 M_DOCS]; the round → M.PROC.041.
- **Kind**: code

## toolchain/setup_toolchain.py

### M.TOOL.043 Module head: no future import, no explicit Any, explanations as comments
- **From**: A.U20.33 (future import goes), A.U21.29 (`from typing import Any` goes; `TypedDict` joins), A.U10.34 (every
  function/class docstring → `#` comments; the module docstring stays — it feeds argparse, `:1102`), A.U21.03/.17/.22/.23
  (the imports their code needs).
- **Site**: `toolchain/setup_toolchain.py:1-31` and every function docstring in the file (46 at HEAD, AST count A.U10.34).
- **Change**: PEP 723 header and module docstring `:6-8` unchanged; imports: `argparse`, `contextlib`, `fcntl`, `grp`,
  `hashlib`, `json`, `os`, `re`, `secrets`, `shlex`, `shutil`, `signal`, `subprocess`, `sys`, `tempfile`, `threading`,
  `time`, `Path`, `from collections.abc import Iterator`, `from typing import TypedDict`, `tomllib`, then the existing
  `sys.path` insert and `import micropython_overrides`. Every function's explanation, existing or added below, is a `#`
  block directly under its `def` line, ≤ 3 lines (overflow to SPEC Part B).
- **Resolved**: —
- **Unit**: U21. Stages: U10 — docstrings → comments at HEAD's functions (A.U10.34); U20 — the future import (A.U20.33);
  U21 — `Any`/`TypedDict` and the new imports.
- **Depends**: —
- **Blast carried by**: `test_comment_block_cap.py`, `test_host_annotations.py`, `test_mypy_any_baseline.py` (the module
  leaves the host baseline) → A.U10.34/A.U20.33/A.U8.24 (TSC); `host_typecheck.ini` pass clean (SCR).
- **Kind**: code

### M.TOOL.044 The mbedtls array-bounds flag goes from the make lines
- **From**: A.U21.16 (step 1 the GCC ≥ 14 build; 2a clean → removed; 2b warning or no build before B5 → scoped to
  `ctr_drbg.c`), A.SDEP.12 (the refreshed pin's mbedtls version; may run step 1 in U0 if a GCC ≥ 14 chroot can be built).
- **Site**: `toolchain/setup_toolchain.py:33-36` (constant and comment), `:335`, `:379` (`CFLAGS_EXTRA` uses).
- **Change**: `_MBEDTLS_GCC14_ARRAY_BOUNDS_WORKAROUND` and its comment go from this file in both branches; the firmware
  `make` line carries no `CFLAGS_EXTRA`; the Unix line carries `CFLAGS_EXTRA=-DMICROPY_PY_SYS_SETTRACE=1` only for the
  settrace flavour (M.TOOL.056). Branch 2b (a warning remains on GCC ≥ 14, or no GCC ≥ 14 build ran before B5): the
  suppression lives only in the two generated files (M.TOOL.037, M.TOOL.038), with "persists on GCC <version> despite
  mbedtls <refreshed version>; scoped to ctr_drbg.c; goes when a GCC ≥ 14 build is clean without it, checked at every ref
  move (agent, <date>)" as its reason line.
- **Resolved**: A.SDEP.12 vs A.U21.16 on where step 1 runs — SUPP_deps co-landing 8: inside the refresh when a GCC ≥ 14
  build is available, else U21; the B.7.1 text takes the refreshed mbedtls version either way.
- **Unit**: U21 (or U0 when A.SDEP.12 runs step 1 there).
- **Depends**: step 1's build (trixie chroot or the bench Pi4 in phase C under the owner's go-ahead); M.TOOL.037/.038
  for 2b.
- **Blast carried by**: `test_micropython_overrides.py:194-215` (`next(..., "")` form) and the 2b L0 cases → A.U21.16 (TSC);
  SPEC B.7.1, B.14 intro; CLAUDE.md `:979-983`; BACKLOG "the GCC ≥ 14 leg decides the mbedtls flag" → A.U21.16 (SPEC,
  DOCS).
- **Kind**: code, doc, hardware

### M.TOOL.045 SetupError joins the one host error family
- **From**: A.U27.29 (2).
- **Site**: `toolchain/setup_toolchain.py:65-66`.
- **Change**: `class SetupError(Exception):` with the comment "# A user error: what failed, where, and how to fix it;
  main() prints it as one line, with no traceback." and `pass`.
- **Resolved**: —
- **Unit**: U27.
- **Depends**: —
- **Blast carried by**: `pytest.raises(SetupError)` holds; `except RuntimeError` sites (grep) → A.U27.29 (TSC).
- **Kind**: code

### M.TOOL.046 run() streams, is always bounded, retries network steps and redacts secrets
- **From**: A.U21.17 (`run()`, three budgets, retries, `run_retried()` forwarding, `node_on_path_matches()` timeout),
  A.U8.14 (tags on `UV_SYNC_ATTEMPTS` and `backoff_s`), A.U28.01 (the one shell retry definition `run_retried()` matches),
  A.U21.19/A.U21.25 (users of `stdin_text`, `secrets`; A.U21.19's `stdin_text` use dropped by OR140.a (1), the PSK
  passed plainly — `secrets=` still redacts it from the echoed command, A-C review fold).
- **Site**: `toolchain/setup_toolchain.py:110-133` and every `run()` call site (`:168-173, :188, :193-206, :228, :240,
  :246, :270-283, :292, :298, :309, :318, :338, :386, :395, :441, :463, :526, :586, :703, :749, :760, :774, :798, :803,
  :819-838, :855-923, :960, :995-1007, :1019, :1038, :1050, :1058`) plus `:945`.
- **Change**: `run(cmd, cwd=None, *, check=True, env=None, timeout_s: float, stdin_text: str | None = None, secrets:
  tuple[str, ...] = ()) -> str` exactly as A.U21.17's Change (redacted echo, `Popen` in its own session, a reader thread
  streaming each line, `wait(timeout=timeout_s)`, `killpg` SIGTERM then SIGKILL after 5 s, `SetupError` naming the
  limit). Budgets as module constants, each under its tag: `# @tunable tool.remote_query_timeout_s = 120` /
  `_REMOTE_QUERY_TIMEOUT_S = 120`; `# @tunable tool.network_step_timeout_s = 1800` / `_NETWORK_STEP_TIMEOUT_S = 1800`;
  `# @tunable tool.build_step_timeout_s = 3600` / `_BUILD_STEP_TIMEOUT_S = 3600`; every call site passes the budget of
  its class (A.U21.17's table; `usermod`, `ip`, `nmcli`, `systemctl`, `systemd-run`, `sudo -n` probes and `tee` take the
  remote-query budget). Retry constants: `# @tunable tool.uv_sync_attempts = 3` / `NETWORK_ATTEMPTS = 3  # mirrors
  scripts/uv_sync_retried.sh (test_uv_sync_retried_sh.py checks)`; `run_retried(cmd, cwd=None, *, env=None, timeout_s:
  float, secrets: tuple[str, ...] = (), attempts: int = NETWORK_ATTEMPTS, backoff_s: float = 10.0)` with `# @tunable
  tool.uv_sync_backoff_step_s = 10.0` on the line above its `def` (the literal on the signature line), forwarding `env`,
  `timeout_s`, `secrets`; its comment "# run(), retried with a growing pause, for a step that downloads from a third party
  (rung R1); after the last attempt the SetupError names the step and the fix." Network steps routed through it as
  A.U21.17 lists (clone with partial-destination removal, fetches, `ls-remote`, submodule updates, `make submodules` ×2,
  the two Node `curl`s with `timeout_s = <curl --max-time> + 30` and their `--max-time` literals tagged
  `tool.node_shasums_timeout_s = 60`, `tool.node_tarball_timeout_s = 600`). `node_on_path_matches()` gets
  `timeout=_REMOTE_QUERY_TIMEOUT_S` and treats `TimeoutExpired` as no match.
- **Resolved**: A.U21.17 renames `UV_SYNC_ATTEMPTS` → `NETWORK_ATTEMPTS` "tag ID unchanged or renamed by A-C with
  A.U8.14": the IDs stay `tool.uv_sync_attempts`/`tool.uv_sync_backoff_step_s` (agent decision D2) — A.U28.01 already
  places the same IDs on `scripts/uv_sync_retried.sh`, the mirror its test compares, and one ID per tunable keeps one Part
  N row; the row's text names both sites ("every retried network step, uv sync included"). The `backoff_s` tag literal
  is `10.0`, the token A.U8.02's whole-token check finds on that line; the shell site's literal is `10`.
- **Unit**: U21. Stage U8: the two tags on HEAD's names (A.U8.14).
- **Depends**: A.U8.01/A.U8.02 (Part N, grammar); A.U8.14.
- **Blast carried by**: every fake `run` in `test_setup_toolchain_env.py`/`test_micropython_overrides.py` gains the
  keywords; new `run()` L0 cases; `run_retried` pause tests → A.U21.17 (TSC); `test_uv_sync_retried_sh.py` reads
  `setup_toolchain.NETWORK_ATTEMPTS` → Gaps (TSC/SCR); Part N rows (three budgets, two curl bounds, the retry pair naming
  both sites) → A.U21.17/A.U8.14 (SPEC); SPEC B.4 → A.U21.17 (SPEC).
- **Kind**: code

### M.TOOL.047 versions.toml is a typed, validated table
- **From**: A.U21.29 (`Versions` `TypedDict`, `load_versions()` validates, `SetupError` for malformed/unreadable files),
  A.U27.02 (blast: the table gains `stubs: {board, stdlib}`), A.U8.24 (the module leaves the host baseline).
- **Site**: `toolchain/setup_toolchain.py:136-151` (`load_versions()`, `VERSIONS_PATH`, `load_lwip_macros()`), `:550`,
  `:601`, `:1063` (`versions: dict[str, Any]`).
- **Change**: `class MicropythonPin(TypedDict): ref: str`, `class ToolchainPin(TypedDict): board: str; apt_packages:
  list[str]`, `class StubPins(TypedDict): board: str; stdlib: str`, `class Versions(TypedDict): micropython:
  MicropythonPin; toolchain: ToolchainPin; lwip: dict[str, int]; stubs: StubPins`; `load_versions(path) -> Versions` as
  A.U21.29 (each key and type checked, first defect → `SetupError(f"{path}: [{table}] {key} is missing / must be {kind} -
  see SPECIFICATION.md B.3")`; `TOMLDecodeError`/`OSError` → `SetupError` naming the file), plus `[stubs]` `board` and
  `stdlib` non-empty strings; `load_lwip_macros()` reads `load_versions(path)["lwip"]`; the three runners take `versions:
  Versions`.
- **Resolved**: —
- **Unit**: U27. Stage U21: the table without `stubs` (A.U21.29); U27 adds `StubPins` with A.U27.02's `[stubs]` table
  (M.TOOL.077) in the same commit.
- **Depends**: M.TOOL.077 (U27 stage).
- **Blast carried by**: `scripts/build_firmware.py:129` and CI's inline heredoc (shape unchanged) → A.U21.29 (SCR,
  M.TOOL.018); `test_micropython_overrides.py:855-859` match text; new L0 cases → A.U21.29/A.U27.02 (TSC).
- **Kind**: code

### M.TOOL.048 write_micropython_ref() refuses a missing, duplicate or misplaced ref
- **From**: A.U21.01.
- **Site**: `toolchain/setup_toolchain.py:154-157`.
- **Change**: as A.U21.01: `re.subn(r'(?m)^ref = "[^"\n]*"$', …)`; `n == 0` / `n > 1` → named `SetupError`, nothing
  written; after writing, `load_versions()` re-read and `["micropython"]["ref"] != ref` → `SetupError` naming
  `[micropython]`.
- **Resolved**: —
- **Unit**: U21.
- **Depends**: M.TOOL.047.
- **Blast carried by**: L0 cases → A.U21.01 (TSC).
- **Kind**: code

### M.TOOL.049 Privileged apt steps keep the named proxy and CA variables
- **From**: A.U21.18, A.U21.17 (budgets).
- **Site**: `toolchain/setup_toolchain.py:160-173`.
- **Change**: as A.U21.18: `_sudo_prefix(env) -> list[str]` (`["sudo", "--preserve-env=<names>"]` from
  `NETWORK_ENV_EXTRA` present in `env` plus `DEBIAN_FRONTEND`); `[*_sudo_prefix(env), "apt-get", "update"]` (`check=False`,
  network budget) and `[*_sudo_prefix(env), "apt-get", "install", "-y", "--no-install-recommends", *packages]` (network
  budget) with `env={**network_env(), "DEBIAN_FRONTEND": "noninteractive"}`; their `SetupError` text gains the env_keep /
  `--skip-apt` hint. Signature unchanged (CI's heredoc calls it).
- **Resolved**: —
- **Unit**: U21.
- **Depends**: M.TOOL.046.
- **Blast carried by**: L0 argv/env cases → A.U21.18 (TSC); SPEC B.4 → A.U21.18 (SPEC); the bench Pi's sudoers read in
  phase C → A.U21.18 (PROC); CI `firmware-build-verify` → M.TOOL.018.
- **Kind**: code

### M.TOOL.050 Clones and fetches retry; an interrupted clone is named, never deleted
- **From**: A.U21.17 (retried clone/fetches, partial-clone cleanup), A.U21.22 (b) (`git rev-parse --verify HEAD` before
  reuse).
- **Site**: `toolchain/setup_toolchain.py:176-217` (`is_sha()`, `clone_full()`, `checkout_ref()`, `ensure_repo_at_ref()`).
- **Change**: `clone_full()` through `run_retried()` (network budget, `network_env()`), removing only a destination it
  created itself before a retry; `checkout_ref()`'s two fetches through `run_retried()`, the checkouts on the
  remote-query budget; `ensure_repo_at_ref()` on an existing `dest` first runs `git rev-parse --verify HEAD` (remote-query
  budget) and on failure raises `SetupError(f"{dest} is not a complete clone (an interrupted clone?) - remove it and re-run
  setup")`, the directory untouched. The full-clone comment (`:184-186`) and `ensure_repo_at_ref()`'s reason kept as `#`
  comments.
- **Resolved**: —
- **Unit**: U21.
- **Depends**: M.TOOL.046.
- **Blast carried by**: L0 (fabricated `.git` without HEAD) → A.U21.22 (TSC).
- **Kind**: code

### M.TOOL.051 pico-sdk and picotool derivation states picotool's real rule and returns what it read
- **From**: A.U21.05 (`derive_picotool_ref()` comment), A.U21.03 (the `git describe` string returned for the record),
  A.U21.17 (budgets; `ls-remote` retried), A.U14.24 (blast: F.1 text — SPEC).
- **Site**: `toolchain/setup_toolchain.py:220-255`.
- **Change**: `derive_pico_sdk_commit()` unchanged in behaviour (remote-query budget); `derive_picotool_ref(pico_sdk_dir,
  commit) -> tuple[str, str]` returning `(tag, described)`; its comment → "# pico-sdk accepts a picotool of its own major
  version and at least its picotool_VERSION_REQUIRED (pico-sdk tools/CMakeLists.txt; picotool's SameMajorVersion config
  file); an older same-major or another major fails the build. The newest tag sharing pico-sdk's major.minor is this
  installer's own narrower choice (agent, 2026-09-22), always inside that range." (3 lines; the executor re-reads both
  cites in the refreshed pico-sdk/picotool checkouts); `git describe` on the remote-query budget, `ls-remote` through
  `run_retried()`.
- **Resolved**: A.U14.24's "must match that major.minor or the build fails" is replaced by A.U21.05's rule (U21 register
  fix 2; AC: the F.1 sentence is SPEC's).
- **Unit**: U21.
- **Depends**: M.TOOL.046.
- **Blast carried by**: caller `run_setup()` unpacks the pair → M.TOOL.060; SPEC B.1/B.3/F.1 → A.U21.05/A.U14.24 (SPEC);
  `versions.toml` header → M.TOOL.074.
- **Kind**: code, doc

### M.TOOL.052 picotool is built only when its tag changed; a USB-less or shadowed one is reported
- **From**: A.U21.27, A.U21.17 (budgets), A.U28.05 (blast: CI installs from the cached build tree into the same prefix).
- **Site**: `toolchain/setup_toolchain.py:258-285` (`PICOTOOL_INSTALL_PREFIX`, `build_and_install_picotool()`).
- **Change**: as A.U21.27: `build_and_install_picotool(picotool_dir, pico_sdk_dir, jobs, *, tag: str, previous_record:
  "ToolchainRecord | None", tier: str)`: (a) skip when the previous record names the same `picotool_tag`, `/usr/local/bin/picotool`
  exists and its `version` output contains the tag's version (form pinned by the executor from a real install) — log
  "picotool <tag> already installed in /usr/local - not rebuilt", no `cmake`, no `sudo`; else build (build budget) and
  `sudo make install` (build budget) as today; (b) `--help` containing "compiled without USB support" → `SetupError` in
  `flash`/`bench`, a warning in `setup`/`generic`; (c) `shutil.which("picotool", path=BUILD_ENV_PATH)` other than
  `/usr/local/bin/picotool` → warning naming both. The install prefix stays `/usr/local` (A.U28.05 relies on it).
  (`ToolchainRecord` is the record's `TypedDict`, M.TOOL.061: no `dict` of `Any`.)
- **Resolved**: —
- **Unit**: U21.
- **Depends**: M.TOOL.061 (record), M.TOOL.046.
- **Blast carried by**: L0 cases → A.U21.27 (TSC); SPEC B.5, README, `tests_hardware/README.md:31-40` → A.U21.27 (SPEC,
  DOCS, HW_BENCH); CI picotool step → M.TOOL.018.
- **Kind**: code

### M.TOOL.053 One build-diagnostics check; mpy-cross gains the error grep
- **From**: A.U21.15.
- **Site**: `toolchain/setup_toolchain.py:288-300` and the inline pairs at `:338-342`, `:386-390`.
- **Change**: `_fail_on_build_diagnostics(out: str, what: str) -> None` as A.U21.15 (`error:` then `warning:`, both
  case-insensitive, messages "… reported an error (see log above)" / "… produced warnings (see log above) - every build is
  warning-free; see SPECIFICATION.md B.7"); `build_mpy_cross()` (build budget) and the firmware/Unix builds call it with
  "mpy-cross build", "firmware build", "Unix port build".
- **Resolved**: —
- **Unit**: U21.
- **Depends**: —
- **Blast carried by**: L0 `build_mpy_cross()` cases → A.U21.15 (TSC); SPEC B.6 step 2 → A.U21.15 (SPEC).
- **Kind**: code

### M.TOOL.054 Submodule fetches retry; the Unix port fetches lwIP for the host build
- **From**: A.U21.12 (`make submodules MICROPY_PY_LWIP=1`), A.U21.17 (retried, network budget).
- **Site**: `toolchain/setup_toolchain.py:303-318`.
- **Change**: `fetch_rp2_submodules()` → `run_retried(["make", f"BOARD={board}", "submodules"], …, env=network_env(),
  timeout_s=_NETWORK_STEP_TIMEOUT_S)`; `fetch_unix_submodules()` → `run_retried(["make", "submodules",
  "MICROPY_PY_LWIP=1"], …)` with its comment gaining "MICROPY_PY_LWIP=1 adds lib/lwip for the lwIP host build
  (extmod/extmod.mk)". (Under A.SDEP.13 (a) the host build still needs lwIP: unchanged.)
- **Resolved**: —
- **Unit**: U21.
- **Depends**: M.TOOL.046.
- **Blast carried by**: `run_test()` (offline) assumes fetched submodules — a toolchain dir set up before U21 lacks
  `lib/lwip` for the Unix port; `scripts/test.sh`'s rebuild runs `setup` (A.U21.12 (rebuild condition), SCR).
- **Kind**: code

### M.TOOL.055 build_firmware(): two overrides in, both proven, no global flag
- **From**: A.U21.10 (modlwip override applied and proven), A.U21.15, A.U21.16/A.SDEP.12 (no `CFLAGS_EXTRA`, M.TOOL.044),
  A.U21.17 (build budget), A.U26.02 (blast: the image record's lwIP dict), D3; OR139.a (1)-(2) (A-C review fold: the
  tick-offset test override by keyword, refused in every build without it).
- **Site**: `toolchain/setup_toolchain.py:321-350`.
- **Change**: after `apply_lwip_connection_counts_override()`, `micropython_overrides.apply_modlwip_eagain_override(
  micropython_dir, overrides_dir)`; the two dicts merged into `override_make_vars` (a duplicate key → `SetupError`);
  `make_cmd = ["make", f"-j{jobs}", *(f"{k}={v}" …)]` plus `FROZEN_MANIFEST=` as today; `run(make_cmd, …,
  env=build_env(), timeout_s=_BUILD_STEP_TIMEOUT_S)`; `_fail_on_build_diagnostics(out, "firmware build")`; the uf2 check;
  `verify_lwip_macros_in_build(build_dir, lwip_macros)`; then `verify_modlwip_eagain_in_build(build_dir, micropython_dir,
  copy_path)` (copy path from `USER_C_MODULES`). Comment `:322-324` → "# Builds the RP2 firmware, optionally with an
  extra FROZEN_MANIFEST=. Always applies and then proves the lwIP-options and modlwip_eagain overrides (SPECIFICATION.md
  B.14); lwip_macros defaults to versions.toml's [lwip], toolchain_dir to micropython_dir's parent." Returns the uf2
  path as today. Under A.SDEP.13 (a): no modlwip call or proof. A keyword `tick_offset_test: bool = False` (OR139.a, A-C
  review fold): when true, `micropython_overrides.apply_tick_offset_override()` joins the merged make variables and the
  build dir is the test image's own (so a later release build never reuses its objects); after every build,
  `verify_tick_offset_in_build(build_dir, expected=tick_offset_test)` — a build without the flag that carries the
  override fails (the release refusal; CI's `firmware-build-verify` builds every device without it, so CI proves the
  absence each run).
- **Resolved**: A.U26.02 wants the built image's lwIP dict "returned from it or re-read from its build dir" — D3 (agent):
  the return type stays a `Path` (callers `run_verification_sequence()` and `scripts/build_firmware.py` unchanged); the
  image record re-reads `micropython_overrides.read_lwip_macros_from_build(uf2.parent, lwip_macros)`.
- **Unit**: U21.
- **Depends**: M.TOOL.039, M.TOOL.041, M.TOOL.044, M.TOOL.053, M.TOOL.080.
- **Blast carried by**: `test_micropython_overrides.py:804-880` fakes (`build.make`, the object, `USER_C_MODULES` in
  `make_cmd`) → A.U21.10 (TSC); `test_build_firmware.py:202` real proof in CI → M.TOOL.018; A.U26.02's re-read → Gaps (SCR).
- **Kind**: code

### M.TOOL.056 Three Unix-port build flavours from one build body, each proven
- **From**: A.U21.06 (c) (kbd proof after every Unix build), A.U21.12 (`UNIX_LWIP_BUILD_DIR`, `build_unix_lwip_port()`,
  one private `_build_unix_variant()`), A.U21.15, A.U21.16 (settrace-only `CFLAGS_EXTRA`), A.U21.17 (budgets), A.U36.512
  (`:353`, `:361`, `:364-365`, `:373` "variant" → "build flavour"), A.SDEP.11 (c) (no kbd override if upstream made it the
  default), A.SDEP.16 (W17: the two-binary split re-checked at the new pin — parked for the owner only if upstream made an
  idle settrace free; no change otherwise).
- **Site**: `toolchain/setup_toolchain.py:353-397`.
- **Change**: comment `:353-355` → "# The Unix-port build flavours and what each backs. The plain test rig is settrace-FREE:
  with MICROPY_PY_SYS_SETTRACE compiled in, py/vm.c allocates a frame and a code object per call and per generator resume,
  inflating every allocation figure 4-5x (SPECIFICATION.md Part E.5.2)."; constants `UNIX_BUILD_DIR = "build-standard"`,
  `UNIX_SETTRACE_BUILD_DIR = "build-settrace"`, `UNIX_LWIP_BUILD_DIR = "build-lwip"` (comment "# the lwIP host build:
  the real patched modlwip over loopback lwIP (SPECIFICATION.md B.14)"). `_build_unix_variant(micropython_dir,
  toolchain_dir, jobs, *, make_vars: dict[str, str], build_dir_name: str, label: str, frozen_manifest=None) -> Path`:
  removes the build dir, runs `make -j<jobs> <make_vars> [BUILD=…] [FROZEN_MANIFEST=…]` (build budget, `build_env()`),
  `_fail_on_build_diagnostics(out, "Unix port build")`, the binary-exists check,
  `micropython_overrides.verify_unix_kbd_intr_in_build(unix_dir, make_vars, build_dir_name, env=build_env())`, the
  `sys.implementation` print (remote-query budget). `build_unix_port(…, settrace=False)` keeps its signature: make vars
  = `apply_unix_kbd_intr_override()`'s plus, for settrace only, `CFLAGS_EXTRA=-DMICROPY_PY_SYS_SETTRACE=1` and
  `BUILD=build-settrace`; its comment "# Builds one Unix-port build flavour; needs mpy-cross, takes frozen_manifest like
  build_firmware(). settrace=False is the test rig, True is --coverage's own binary. Always applies
  apply_unix_kbd_intr_override() for the safe SIGINT path (Part B.14.1)."; `:373` comment → "# BUILD= only for a
  non-default build flavour: the Makefile's own `BUILD ?= build-$(VARIANT)` already lands the settrace-free rig in
  build-standard, which every other script resolves."; local `variant` → `flavour`. New `build_unix_lwip_port(
  micropython_dir, toolchain_dir, jobs) -> Path`: `apply_unix_lwip_host_override(micropython_dir, overrides_dir,
  load_lwip_macros())`, the shared body, then `verify_unix_lwip_host_in_build(…, env=build_env())`. Under A.SDEP.11 (c)
  the kbd apply call goes and the proof keeps only its deferred-branch half.
- **Resolved**: A.U36.512 (U36) renames words in lines A.U21.12 (U21) restructures — the U21 text is written with
  "build flavour" already (A.U36.512 Depends A.U21.12/A.U27.12); "variant" stays only where it names MicroPython's own
  `VARIANT`/`VARIANT_DIR`.
- **Unit**: U21.
- **Depends**: M.TOOL.037, M.TOOL.040, M.TOOL.041, M.TOOL.044, M.TOOL.053.
- **Blast carried by**: `test_micropython_overrides.py:144-270` (fake `make` branches, `CFLAGS_EXTRA` asserts, flavour
  test names) → A.U21.06/A.U21.16/A.U36.512 (TSC); `scripts/test.sh`/`_unix_port.sh` → A.U21.12/A.U27.12 (SCR); SPEC
  B.2/B.5/B.6/E.5.2, CLAUDE.md, README → A.U21.12 (SPEC, DOCS).
- **Kind**: code

### M.TOOL.057 Clean-up lists share the current build names
- **From**: A.U21.12 (`build-lwip` in `clean_build_dirs()`), A.U21.30 (the current-name list shared with the leftover
  remover), A.U36.512 (`:479` "the default variant" → "the default build flavour"; `--clean` help in M.TOOL.073).
- **Site**: `toolchain/setup_toolchain.py:400-417`, `:472-488`.
- **Change**: `CURRENT_UNIX_BUILD_DIRS = (UNIX_BUILD_DIR, UNIX_SETTRACE_BUILD_DIR, UNIX_LWIP_BUILD_DIR)`;
  `clean_build_dirs()` targets picotool/build, mpy-cross/build, `ports/rp2/build-<board>` and every name in that tuple;
  `clean_frozen_verification_build_dirs()` unchanged except its comment "# UNIX_BUILD_DIR only: the verification chain
  builds the default build flavour, never the others, so removing those here would delete a real deliverable instead of
  an artifact."
- **Resolved**: —
- **Unit**: U21.
- **Depends**: M.TOOL.056.
- **Blast carried by**: `remove_outdated_leftovers()` reads the tuple → M.TOOL.063.
- **Kind**: code

### M.TOOL.058 Verification chain: three binaries built, the summary says so
- **From**: A.U21.12 (the lwIP host build after the settrace build), A.U1.22 (`:450` comment repath), A.U21.03 (the
  sequence returns what the record needs).
- **Site**: `toolchain/setup_toolchain.py:420-547` (frozen-verify helpers, `run_verification_sequence()`,
  `print_verification_summary()`).
- **Change**: `write_freeze_manifest()`'s comment: "(python/Manifest/manifest.py)" → "(legacy/firmware/python/Manifest/
  manifest.py)". `run_verification_sequence()` builds, after the settrace binary, `build_unix_lwip_port(…)`, and returns
  `(mpy_cross_binary, unix_binary)` as today; `print_verification_summary()` lines "8. Vanilla Unix port rebuilt as the
  standing test rig: <path>" then "   The settrace build flavour for --coverage and the lwIP host build flavour, each
  proven post-build: <two paths>".
- **Resolved**: —
- **Unit**: U21. Stage U1: the `:450` repath (A.U1.22).
- **Depends**: M.TOOL.056.
- **Blast carried by**: `test_micropython_overrides.py:217-232` (structural: three flavours) → A.U21.12 (TSC); SPEC B.6
  step 8 → A.U21.12 (SPEC).
- **Kind**: code

### M.TOOL.059 latest_stable_micropython_ref(): retried; its comment tells the truth about the hand pins
- **From**: A.U21.17 (`ls-remote` retried), A.U27.02 (adherence: `[stubs]` makes "the only hand-tracked version" false).
- **Site**: `toolchain/setup_toolchain.py:522-537`.
- **Change**: `ls-remote` through `run_retried()` (remote-query budget, `network_env()`); comment `:523-525` → "# Backs
  --latest: writes the newest stable tag to versions.toml's ref; pico-sdk and picotool follow by derivation, the [stubs]
  pins by hand at the platform re-check (scripts/typecheck.sh refuses a mismatch)."
- **Resolved**: — (an adherence fix: once A.U27.02 lands, HEAD's comment would state a false fact).
- **Unit**: U27. Stage U21: the retry.
- **Depends**: M.TOOL.077.
- **Blast carried by**: the notice text (M.TOOL.060) names the stub version among the re-check items.
- **Kind**: code, doc

### M.TOOL.060 run_setup()/run_test(): the pin notice, the record, the leftovers, picotool by tier
- **From**: A.U21.02 (pinned/moved_from/off_pin, exclusive flags, `_PLATFORM_RECHECK_NOTICE`), A.U21.03 (record deleted at
  the start of verification, written after the summary; `run_test()` fills pico-sdk/picotool from the previous record),
  A.U21.22 (b) (the record marks an interrupted run), A.U21.27 (tier passed for picotool), A.U21.30 (leftover removal
  after the summary), A.U21.17 (the pico-sdk `submodule update` retried), A.U21.05 (blast: the derivation pair).
- **Site**: `toolchain/setup_toolchain.py:550-624`.
- **Change**: `run_setup(args, versions_path, versions: Versions, *, tier: str = "setup") -> int`: `pinned =
  versions["micropython"]["ref"]` first; `--latest` with `--micropython-ref` → `SetupError("--latest and
  --micropython-ref are exclusive")`; `--latest` resolving to `pinned` logs "already on the newest stable tag" and writes
  nothing, else writes (M.TOOL.048) and sets `moved_from = pinned`; `--micropython-ref X != pinned` sets `off_pin = X`
  (never writes). Then as today (apt, clones, pico-sdk commit, the `lib/mbedtls` submodule update through
  `run_retried()`, picotool tag and describe via M.TOOL.051, `build_and_install_picotool(…, tag=…, previous_record=
  read_toolchain_record(toolchain_dir), tier=tier)`, submodules); `delete_toolchain_record(toolchain_dir)` right before
  `run_verification_sequence()`; after `print_verification_summary()`: `write_toolchain_record(…)` (M.TOOL.061),
  `remove_outdated_leftovers(toolchain_dir, board)` (M.TOOL.063), then, when `moved_from` or `off_pin`, the
  `_PLATFORM_RECHECK_NOTICE` block exactly as A.U21.02 words it (exit 0). `run_test()` the same record and leftover steps
  around its offline sequence, pico-sdk/picotool fields from the previous record or `null`. Comments as `#` blocks.
- **Resolved**: A.SDEP.08 moves the pin in U0, before the notice exists — A.SDEP.08 (4) runs the platform re-check in full
  regardless (SUPP_deps co-landing 9).
- **Unit**: U21.
- **Depends**: M.TOOL.047, .048, .050-.052, .058, .061-.063.
- **Blast carried by**: L0 `run_setup()` cases (notice, byte-identical file, exclusive flags) → A.U21.02 (TSC); README
  flag table, SPEC B.2/B.11, Part F intro → A.U21.02/A.U36.023 (DOCS, SPEC).
- **Kind**: code

### M.TOOL.061 The toolchain record ties a toolchain directory to its inputs
- **From**: A.U21.03 (record content, atomic write), A.U21.21 (Node record), A.U21.22 (b) (a missing record marks an
  incomplete toolchain), A.SDEP.25 (blast: U37 re-checks the record's fields).
- **Site**: new `TOOLCHAIN_RECORD = "toolchain-record.json"`, `class ToolchainRecord(TypedDict)`,
  `write_toolchain_record()`, `read_toolchain_record()`, `delete_toolchain_record()`.
- **Change**: as A.U21.03: JSON object, sorted keys — `pinned_ref`, `built_ref`, `micropython_commit`, `pico_sdk_commit`,
  `pico_sdk_describe`, `picotool_tag`, `picotool_version`, `board`, `lwip`, `input_sha256` (`versions.toml`,
  `setup_toolchain.py`, `micropython_overrides.py`), `compilers`, `unix_binaries` (the three build-dir names),
  `recorded_utc`; written via a same-dir temp file and `os.replace`; `read_toolchain_record()` returns `None` for a
  missing or unparseable file. `ensure_node()` writes `node/node-record.json` (`major`, `tarball`, `sha256`) the same
  way (M.TOOL.070).
- **Resolved**: —
- **Unit**: U21.
- **Depends**: —
- **Blast carried by**: `scripts/build_firmware.py` prints `built_ref`/`micropython_commit` and refuses a dir without a
  record; `scripts/test.sh` treats a missing record as a missing binary → A.U21.03/A.U21.22 (SCR); L0 round-trip →
  A.U21.03 (TSC); SPEC B.5/B.3 → A.U21.03 (SPEC).
- **Kind**: code

### M.TOOL.062 One lock per toolchain directory
- **From**: A.U21.22 (a).
- **Site**: new `toolchain_lock(toolchain_dir: Path) -> Iterator[None]` (`@contextlib.contextmanager`).
- **Change**: as A.U21.22 (a): `<toolchain_dir>/.toolchain.lock`, `fcntl.flock(LOCK_EX | LOCK_NB)`; held → `SetupError(
  f"another setup or firmware build (pid {pid}) is using {toolchain_dir} - wait for it to finish, or use another
  --toolchain-dir")`; the pid written on success; fail-fast, never a wait. Taken once, in `main()`'s dispatch of
  `setup`/`test`/`env` (M.TOOL.073), never inside the runners.
- **Resolved**: —
- **Unit**: U21.
- **Depends**: —
- **Blast carried by**: `scripts/build_firmware.py` takes it → A.U21.22 (SCR); the two-process L0 and `main()` cases →
  A.U21.22 (TSC); SPEC B.5/B.11/E.1 → A.U21.22 (SPEC); hardware runners that call `build_firmware.py` see the message →
  A.U21.22 (HW_BENCH, read).
- **Kind**: code

### M.TOOL.063 Setup removes its own outdated leftovers
- **From**: A.U21.30.
- **Site**: new `remove_outdated_leftovers(toolchain_dir: Path, board: str) -> None`.
- **Change**: as A.U21.30: `micropython/ports/unix/build-*` not in `CURRENT_UNIX_BUILD_DIRS` (M.TOOL.057);
  `build_overrides/*` not in `micropython_overrides.CURRENT_OVERRIDE_DIRS` (M.TOOL.042); `node/node-v*-linux-*` other
  than the tree `node/node-record.json` names; `ports/rp2/build-*` untouched; each removal printed with its reason; a path
  resolving outside `toolchain_dir` skipped with a warning.
- **Resolved**: —
- **Unit**: U21.
- **Depends**: M.TOOL.042, M.TOOL.057, M.TOOL.061.
- **Blast carried by**: L0 fabricated-dir test → A.U21.30 (TSC); SPEC B.5 → A.U21.30 (SPEC).
- **Kind**: code

### M.TOOL.064 One board resolver: vendor 2e8a plus the MicroPython by-id name
- **From**: A.U21.28.
- **Site**: `toolchain/setup_toolchain.py:627-683`.
- **Change**: as A.U21.28: `BOARD_BY_ID_GLOB = "usb-MicroPython_Board_in_FS_mode_*-if00"`; `resolve_board_serial(by_id_dir
  =Path("/dev/serial/by-id"), sys_tty_dir=Path("/sys/class/tty"), dev_dir=Path("/dev")) -> list[Path]`;
  `resolve_pico_device(explicit)`: `explicit` or `$MPREMOTE_DEVICE`, else exactly one candidate's by-id path, else the
  named `SetupError`s; the `PICO_USB_VENDOR_ID` comment → "# Vendor 2e8a narrows to Raspberry Pi devices, the MicroPython
  by-id name to a board running MicroPython - a debug probe shares the vendor ID." `_read_usb_id_vendor()` kept;
  `detect_pico_serial_devices()` kept only if a caller remains after U26's harness delegation (else removed with its
  tests).
- **Resolved**: —
- **Unit**: U21.
- **Depends**: —
- **Blast carried by**: `board` subcommand → M.TOOL.073; `tests_hardware/harness.py` delegation → A.U26 (HW_BENCH);
  `scripts/mpremote_connect.sh` → A.U27.13 (SCR, Gaps); L0 cases → A.U21.28 (TSC); SPEC B.12, README → A.U21.28 (SPEC,
  DOCS).
- **Kind**: code

### M.TOOL.065 Every command a tier runs is checked from one table, and the bench tier's sudo too
- **From**: A.U21.24 (`_TIER_COMMANDS`, `ensure_commands()`), A.U21.26 (`check_passwordless_sudo()`), G10/R07 (the three
  `ensure_*()` one shape); OR140.a (A-C review fold: bench-sudo-checked owner-reviewed, the tag form).
- **Site**: `toolchain/setup_toolchain.py:707-742` (three constants, three functions).
- **Change**: as A.U21.24: the three functions and constants → `_TIER_COMMANDS = {"generic": (("curl", "curl"),),
  "bench": (("nmcli", "network-manager"), ("ip", "iproute2"), ("iptables", "iptables"), ("sysctl", "procps"), ("modprobe",
  "kmod"), ("iw", "iw"), ("tc", "iproute2"), ("tcpdump", "tcpdump"), ("timeout", "coreutils"))}` (package names
  confirmed with `apt-cache policy` on both chroot legs) and `ensure_commands(pairs, *, skip_apt: bool)` (`shutil.which()`
  on `BUILD_ENV_PATH`; missing packages installed together; the `--skip-apt` and still-missing messages). As A.U21.26:
  `_BENCH_SUDO_COMMANDS = ("nmcli", "iw", "iptables", "tc", "tee", "picotool", "timeout", "systemd-run", "systemctl")`,
  `check_passwordless_sudo(commands)` probing `sudo -n <abs path> <version arg>` (remote-query budget), one `SetupError`
  naming every refused command and `tests_hardware/README.md` Prerequisites; root passes. The installer writes no sudoers
  file; the comment above `check_passwordless_sudo()` says so with the tag "(agent, 2026-09-30; owner-reviewed,
  2026-10-02)" (A-C review fold: decision bench-sudo-checked, the tag form; no audit ID in the comment).
- **Resolved**: —
- **Unit**: U21.
- **Depends**: M.TOOL.049.
- **Blast carried by**: `test_setup_toolchain_env.py:154-198` → table-driven tests, new L0 → A.U21.24/A.U21.26 (TSC);
  README tier table, `tests_hardware/README.md` Prerequisites, SPEC B.12 → A.U21.24/A.U21.26 (DOCS, HW_BENCH, SPEC);
  phase C sudo check → A.U21.26 (PROC).
- **Kind**: code

### M.TOOL.066 Bench connection-name and credential comments point at the live recipe
- **From**: A.U1.22 (`:790-791`, `:808-809`), A.U10.34 (comment form).
- **Site**: `toolchain/setup_toolchain.py:790-812`.
- **Change**: `:790-791` → "# Connection names match tests_hardware/README.md's manual nmcli recipe exactly, so a
  bridge/AP created by that recipe by hand is recognized as "already configured" here too, and vice versa.";
  `generate_bench_ap_credentials()`'s comment → "# A fresh, random, test-only SSID/password per bridge creation - never a
  fixed default, never a committed one (CLAUDE.md credential rule; tests_hardware/README.md's recipe)."
- **Resolved**: —
- **Unit**: U1.
- **Depends**: A.U1.05 (the recipe's new home, HW_BENCH/DOCS).
- **Blast carried by**: `test_setup_toolchain_env.py:5-7` comment → A.U1.22 (TSC).
- **Kind**: doc

### M.TOOL.067 br_netfilter persists without temporary files; its reason stated in place
- **From**: A.U21.25 (`sudo tee` with `stdin_text`), A.U36.544 (`:817` "SPECIFICATION.md Part B.13" → the reason in
  place), A.U21.17 (budgets), A.U10.34.
- **Site**: `toolchain/setup_toolchain.py:815-840`.
- **Change**: comment → "# Idempotent: loads br_netfilter and sets net.bridge.bridge-nf-call-iptables=1 - without it
  bridged traffic bypasses iptables and bench_control.py's fault injection silently does nothing. Host-kernel state, so
  it runs whether or not the bridge profile exists."; `modprobe`/`sysctl` with `env=build_env()` and the remote-query
  budget; each persistence file written by `run(["sudo", "tee", str(path)], stdin_text=line, env=build_env(),
  timeout_s=_REMOTE_QUERY_TIMEOUT_S)` then `sudo chmod 644`; no `NamedTemporaryFile`, no `os.unlink`.
- **Resolved**: —
- **Unit**: U21. Stage U36: none (A.U36.544's pointer edit is done by U21's rewrite of the same comment; DONE).
- **Depends**: M.TOOL.046.
- **Blast carried by**: `test_setup_toolchain_env.py:370-382` (no `/tmp` path in argv; `stdin_text` cases) → A.U21.25
  (TSC).
- **Kind**: code

### M.TOOL.068 ensure_bench_bridge(): the throwaway password passed plainly; every change runs under an armed switch
- **From**: A.U21.19 (`secrets=`, the one print; its `nmcli connection edit` stdin path and argv fallback dropped by
  OR140.a (1): the password is a throwaway used once, passed plainly, A-C review fold), A.U21.23 (`_armed_recovery()`,
  the post-up poll, the channel self-heal armed, the MAC remedy text, two tags), A.U21.17 (budgets), A.U36.522 (blast:
  README describes it).
- **Site**: `toolchain/setup_toolchain.py:843-926` and new `_armed_recovery()`.
- **Change**: as A.U21.23: `@contextlib.contextmanager _armed_recovery(uplink_iface, restore_profile, window_s)` (the
  script built in memory from B.13's teardown plus the shell-quoted restore of the profile read at run time; `sudo
  systemd-run --unit=sensors-bench-recovery-<pid> --on-active=<window_s>`, verified `active` before any change, disarmed
  and verified gone on success, left armed with the logged message on an exception); `# @tunable
  tool.bench_bridge_recovery_arm_s = 300` / `_BRIDGE_RECOVERY_ARM_S = 300`, `# @tunable tool.bench_bridge_up_poll_s = 90` /
  `_BRIDGE_UP_POLL_S = 90`; the creation sequence inside one `_armed_recovery()`, then the bounded 2 s poll for an `br0`
  address and `dev br0` in `ip -o route get 1.1.1.1`; the channel self-heal inside its own `_armed_recovery(uplink, None,
  …)` with the same poll; the MAC-mismatch remedy gains "arm SPECIFICATION.md B.13's recovery timer first". The
  `modify` keeps `wifi-sec.key-mgmt … wifi-sec.pmf disable` and carries the PSK pair `wifi-sec.psk <password>` plainly
  on its command line (the password from `$BENCH_AP_PASSWORD`, or generated; a throwaway used once, never committed),
  `secrets=(password,)` keeping it out of the echoed command; no interactive `nmcli connection edit`, no
  known-limitation note; a generated password printed once with "Save this password now", a `$BENCH_AP_PASSWORD` one
  never printed; the comment names the variable and states "a throwaway password used once, passed plainly (owner,
  2026-10-02)".
- **Resolved**: A.U21.19 and A.U21.23 rewrite one creation sequence — both in one change (A.U21.19 Depends A.U21.23).
- **Unit**: U21.
- **Depends**: M.TOOL.046, M.TOOL.067.
- **Blast carried by**: `test_setup_toolchain_env.py:293-429` (arm/disarm order; the PSK in the one `modify`'s argv,
  redacted from the echo, printed once when generated) → A.U21.19/A.U21.23 (TSC, M.TSC.126); Part N rows for the two tags → A.U21.23 (SPEC); SPEC B.13, CLAUDE.md dead-man's-switch rule,
  `tests_hardware/README.md` → A.U21.23 (SPEC, DOCS, HW_BENCH); README bridge text → A.U36.522 (DOCS); phase C
  first real run → A.U21.23 (PROC).
- **Kind**: code

### M.TOOL.069 Node: one SHASUMS fetch, named errors, a recorded tree, curl checked first
- **From**: A.U21.21 (`_node_release()`, `SystemExit` → `SetupError`), A.U21.17 (curl budgets, `node_on_path_matches()`
  timeout), A.U21.24 (`curl` checked before the first download), A.U21.03 (`node-record.json`), A.U21.30 (superseded
  trees removed), A.SDEP.04 (blast: `.nvmrc` major read unchanged).
- **Site**: `toolchain/setup_toolchain.py:929-1011`.
- **Change**: as A.U21.21: `_node_release(major, env) -> tuple[str, str]` from one SHASUMS fetch (strict line parse,
  64-hex hash check, named `SetupError`s); `ensure_node()` calls `ensure_commands(_TIER_COMMANDS["generic"], …)` before
  its first `curl`, downloads to the temp dir, `sha256sum` against the same fetch's hash, extracts only on a match,
  writes `node/node-record.json`; every `SystemExit` in these functions → `SetupError`; the two `curl` calls through
  `run_retried()` with their tagged `--max-time` literals (M.TOOL.046).
- **Resolved**: —
- **Unit**: U21.
- **Depends**: M.TOOL.046, M.TOOL.061, M.TOOL.065.
- **Blast carried by**: `test_setup_toolchain_env.py:519-571` (`_node_release` monkeypatch), new L0 → A.U21.21 (TSC);
  README "Website tooling" → A.U21.21 (DOCS).
- **Kind**: code

### M.TOOL.070 Project dependencies: the sync forwards its environment; a failed Playwright install stops env
- **From**: A.U21.17 (`run_retried(["uv", "sync"], …, env=None, timeout_s=_NETWORK_STEP_TIMEOUT_S)`; `npm ci` and the
  Playwright calls on the network budget), A.U28.20 (`ensure_playwright_browser()` raises).
- **Site**: `toolchain/setup_toolchain.py:1014-1060`.
- **Change**: `run_project_dependency_install()` as today with the budgets; `ensure_playwright_browser()` as A.U28.20:
  the `install chromium` failure raises `SetupError("Playwright's Chromium did not install (<cmd> failed) - `npm test`
  cannot run. Re-run `env`, or pass --skip-npm to set up without the web tier")`; `install-deps` skipped under
  `skip_apt`, else its failure raises the same way with the `sudo npx playwright install-deps chromium` / `--skip-apt`
  hint; comment "# Vitest drives a real Chromium (SPECIFICATION.md Part H), so a machine that ran `npm ci` needs it: a
  failure stops `env` by name."
- **Resolved**: A.U28.20 (U28's clause on U21's file) and A.U21.17 change one function's calls — merged (A.U28.20
  Depends).
- **Unit**: U28. Stage U21: the budgets.
- **Depends**: M.TOOL.046, M.TOOL.045.
- **Blast carried by**: L0 failure cases → A.U28.20 (TSC); README tier table, BACKLOG bench re-run → A.U28.20 (DOCS);
  BACKLOG chroot (installer leg) → A.U28.38 (DOCS).
- **Kind**: code

### M.TOOL.071 run_env(): tier checks in order, the AP password from the environment
- **From**: A.U21.24 (bench command table replaces `:1080-1082`), A.U21.26 (sudo check before the bridge), A.U21.27
  (tier passed to `run_setup()`), A.U21.19 (`$BENCH_AP_PASSWORD`), A.U21.03 (the Node version in use logged), A.U28.20
  (ready lines only after Playwright succeeded — no extra change).
- **Site**: `toolchain/setup_toolchain.py:1063-1087`.
- **Change**: `run_setup(args, versions_path, versions, tier=args.tier)`; then `run_project_dependency_install(…)` and
  one log of `node --version` of the resolved binary; flash: `ensure_dialout_group()` (remote-query budget on its
  `usermod`), `resolve_pico_device(args.device)`; bench: `ensure_commands(_TIER_COMMANDS["bench"], skip_apt=…)`,
  `check_passwordless_sudo(_BENCH_SUDO_COMMANDS)`, `ensure_bench_bridge(args.uplink_iface, args.wifi_iface, args.ssid,
  os.environ.get("BENCH_AP_PASSWORD") or None)`; comment as `#` block.
- **Resolved**: —
- **Unit**: U21.
- **Depends**: M.TOOL.060, .064, .065, .068, .069, .070.
- **Blast carried by**: L0 `run_env()` cases (env var read; order) → A.U21.19/A.U21.24/A.U21.26 (TSC).
- **Kind**: code

### M.TOOL.072 The CLI: exclusive pin flags, no password option, a board subcommand, one lock, one error line
- **From**: A.U21.02 (help texts; exclusive flags), A.U21.19 (`--password` goes), A.U21.22 (lock in the dispatch),
  A.U21.28 (`board` subcommand), A.U36.512 (`--clean` help "build flavour"), A.U27.29 (error handling inside `main()`,
  `raise SystemExit(main())`), A.U7.19 (`--help` exits 0 with no side effect), A.U36.547/A.U36.007 (blast: README CLI
  reference and E.6.1 read the help), D6, D7.
- **Site**: `toolchain/setup_toolchain.py:1090-1171`.
- **Change**: parsers as today, with: `--micropython-ref` help "Build this MicroPython ref instead of the pin, without
  changing versions.toml (an off-pin build: the platform re-check applies before trusting it)" and `--latest` help "Pin
  versions.toml to the newest stable MicroPython tag (a pin move: the owner's call, and the platform re-check follows)"
  on both `setup` and `env`; `setup`'s `--clean` help "… ports/rp2/build-<board>, and every Unix-port build flavour
  (ports/unix/build-standard, build-settrace, build-lwip) …"; `env`'s `--password` removed (an explicit PSK comes from
  `$BENCH_AP_PASSWORD`; `--ssid` help unchanged); new subparser `board` (no `--toolchain-dir`/`--jobs`; one option, `--device`)
  "Print the resolved MicroPython board's serial path". The bare-argv convenience accepts `board` too. `main()`: parse
  (so `-h` exits 0 before any lock, file read or side effect); `board` → print `resolve_pico_device(args.device)`,
  return 0 — before `load_versions()` and without the lock (D6: it reads /sys only); `setup`/`test`/`env` → `with
  toolchain_lock(args.toolchain_dir.expanduser().resolve()): …` around `load_versions()` and the runner; `except
  (SetupError, micropython_overrides.OverrideError, subprocess.CalledProcessError) as exc:` → `print(f"setup_toolchain:
  {exc}", file=sys.stderr)`, `return 1`. Module end: `if __name__ == "__main__": raise SystemExit(main())`.
- **Resolved**: A.U21.28 prints "FAILED: …" for `board`, A.U27.29 (U27, later; G10/R30's one error contract) prints
  `<tool>: <message>` for every host CLI — A.U27.29's form for all subcommands (D7); A.U27.13's quoted
  "FAILED: no MicroPython board found …" follows (Gaps, SCR).
- **Unit**: U27. Stages: U21 — options, `board`, the lock (A.U21.02/.19/.22/.28), with HEAD's `__main__` handler; U27 —
  the handler moves into `main()`, the exit idiom (A.U27.29); U36 — none (A.U36.512's `--clean` wording written in U21).
- **Depends**: M.TOOL.045, .060, .062, .064, .071.
- **Blast carried by**: `test_setup_toolchain_env.py:573-588` and new CLI cases (`--password` rejected, `board` via
  `main()`) → A.U21.19/A.U21.28 (TSC); `test_tool_help.py` → A.U7.19 (TSC); README CLI reference (help comparison) →
  A.U36.547 (DOCS); `scripts/mpremote_connect.sh` → A.U27.13 (SCR).
- **Kind**: code

## toolchain/versions.toml

### M.TOOL.073 The MicroPython ref at the refreshed tag
- **From**: A.SDEP.08 (the pin moves with everything it pulls in; OR129 is the owner's call), A.SDEP.25 (U37 re-check),
  A.U21.02 (blast: a pin move announces the platform re-check — A.SDEP.08 (4) runs it in full).
- **Site**: `toolchain/versions.toml:9-10` (`[micropython] ref`).
- **Change**: `ref = "<newest stable tag that has a micropython-rp2-rpi_pico_w-stubs release>"` (A.SDEP.08 (1); a newer
  tag without stubs is recorded as held back, BACKLOG owner-question list), or unchanged with "already newest" recorded.
  The build-and-verify (`setup`), the platform re-check, the per-device image and heap measurements and the phase-C
  BACKLOG entry are A.SDEP.08's (PROC/DOCS).
- **Resolved**: —
- **Unit**: U0. Re-checked at U37 (A.SDEP.25).
- **Depends**: A.SDEP.01-A.SDEP.03 (tools first).
- **Blast carried by**: CI cache key (cold cache on the next run, expected) → M.TOOL.001; `[stubs]` follow at the same X.Y.Z
  → M.TOOL.077; every version-stamped claim → A.SDEP.08 (4) (SPEC, DOCS, every cluster's comments); citations in
  unexecuted actions → A.SDEP.23 (PROC); BACKLOG chroot entry "MicroPython ref <old> → <new>" → A.SDEP.21 (DOCS).
- **Kind**: code

### M.TOOL.074 The header states the hand pins, the derivations and whose call a move is
- **From**: A.U21.05 (`:3-5` picotool clause), A.U27.02 (adherence: `[stubs]` makes "Only the MicroPython ref is pinned by
  hand" false), A.U21.02/OR69.a (9) (adherence: the pin moves only on the owner's call; the `:6-7` "To move" line invites
  `--latest` without saying so), A.U36.519 (blast: L.7 cites this file's "no bump automation" precedent — holds).
- **Site**: `toolchain/versions.toml:1-8`.
- **Change**: → "# Pins for the build-environment installer (toolchain/setup_toolchain.py)." / "#" / "# The MicroPython
  ref and the stub releases ([stubs]) are pinned by hand. pico-sdk is derived from MicroPython's own lib/pico-sdk
  submodule at this ref, picotool as the newest tag sharing its major.minor (inside pico-sdk's same-major rule,
  SPECIFICATION.md B.1)." / "#" / "# A move is the owner's call and the platform re-check follows (SPECIFICATION.md Part
  F): change `ref` and [stubs], or run the installer with --latest, then re-run the installer." (each block ≤ 3 lines).
- **Resolved**: — (two of the three sentences are adherence fixes, agent decision D5: once `[stubs]` exists and the
  pin policy is the owner's, HEAD's header states two false facts).
- **Unit**: U27. Stage U21: the picotool clause (A.U21.05) and the "owner's call" sentence (with A.U21.02's notice).
- **Depends**: M.TOOL.077.
- **Blast carried by**: SPEC B.1/B.3/B.11 → A.U21.05/A.U27.02 (SPEC).
- **Kind**: doc

### M.TOOL.075 The [lwip] comment's per-connection cost re-verified at the new pin
- **From**: A.SDEP.14 (the 2,324 B per-connection cost re-measured only if lwIP's pools changed layout), A.U21.31/A.U14.30/
  A.U18.18 (blast: the comment's "MEM_SIZE = limit x 2,000 B" and the `MEMP_NUM_UDP_PCB` value hold).
- **Site**: `toolchain/versions.toml:31-40` (the `[lwip]` comment block).
- **Change**: unchanged unless A.SDEP.14 re-measures a different per-connection cost at the refreshed pin, in which case
  "2,324 B of GC heap per connection" takes the new figure (with SPEC B.14.2.1/H.7 `:4572`).
- **Resolved**: —
- **Unit**: U0.
- **Depends**: M.TOOL.073.
- **Blast carried by**: SPEC B.14.2.1, H.7, `HEAP_FRAGMENTATION_MEASUREMENTS.md:237` → A.SDEP.14 (SPEC, DOCS).
- **Kind**: doc

### M.TOOL.076 The seven independent lwIP options are tagged
- **From**: A.U8.14 (tags `lwip.<macro lower-case> = <n>`; the three derived values stay untagged, named as dependants),
  A.SDEP.14 (a value moves only with its reason, OR114.a (3)), A.U14.30/A.U18.18 (values unchanged).
- **Site**: `toolchain/versions.toml:43-52`.
- **Change**: a tag line directly above each of `MEMP_NUM_TCP_PCB_LISTEN = 8` (`# @tunable lwip.memp_num_tcp_pcb_listen =
  8`), `MEMP_NUM_PBUF = 16`, `PBUF_POOL_SIZE = 16`, `MEMP_NUM_UDP_PCB = 5`, `TCP_MSS = 800`, `TCP_WND = 6400`,
  `TCP_SND_BUF = 6400` (same form); `MEMP_NUM_TCP_PCB = 9`, `MEMP_NUM_TCP_SEG = 48`, `MEM_SIZE = 12000`, `LWIP_STATS = 0`
  untagged. Values unchanged (OR114.a (3)); `tomllib` ignores the comments.
- **Resolved**: —
- **Unit**: U8.
- **Depends**: A.U8.01/A.U8.02.
- **Blast carried by**: Part N `lwip.*` rows (basis B.14.2; dependants of `lwip.spare_tcp_pcbs` and
  `lwip.mem_size_per_connection_floor`) → A.U8.14 (SPEC); `check_lwip_ensemble()` reads the values unchanged.
- **Kind**: code

### M.TOOL.077 Exact stub post-releases pinned beside the ref
- **From**: A.U27.02 (1) (`[stubs]` `board`, `stdlib`), A.SDEP.09 (the post-releases installed and recorded at the
  refresh), A.SDEP.15 (stub repairs re-checked against them), A.SDEP.25 (U37 re-check); OR140.a (11) (A-C review fold:
  the stub version moves with every MicroPython bump, enforced by a check — decision stub-versions-pinned).
- **Site**: `toolchain/versions.toml`, new table after `[micropython]`.
- **Change**: "# Exact stub releases; they move with every [micropython] ref change, X.Y.Z equal to the ref's
  (scripts/typecheck.sh and tests_scripts check; owner, 2026-10-02). Re-run typecheck.sh after a bump." / `[stubs]` / `board = "<X.Y.Z.postN>"` / `stdlib = "<X.Y.Z.postM>"` — the
  `micropython-rp2-rpi_pico_w-stubs` and `micropython-stdlib-stubs` versions A.SDEP.09 recorded from `typings/*.dist-info`.
- **Resolved**: A.U27.02 reads the versions "after one run at execution (A.U21.04 prints them)"; A.SDEP.09 records them at
  the refresh — the pins are A.SDEP.09's recorded versions (SUPP_deps co-landing 10), re-read at U27 if a later
  post-release was installed meanwhile.
- **Unit**: U27. Re-checked at U37 (A.SDEP.25).
- **Depends**: M.TOOL.073, A.SDEP.09; M.TOOL.047 (same commit: the typed table accepts `[stubs]`).
- **Blast carried by**: `scripts/typecheck.sh` reads and checks the pins → A.U27.02 (SCR, M.SCR.027); `test_typecheck_sh.py`
  → A.U27.02 (TSC), whose case over the real `toolchain/versions.toml` fails the unit tier on a mismatched bump
  (M.TSC.221); SPEC F.5.5/B.11, CLAUDE.md stub bullets → A.U27.02 (SPEC, DOCS); BACKLOG chroot entry → A.U27.02 (DOCS).
- **Kind**: code

## uv.lock

### M.TOOL.078 The lock is refreshed, then re-written for every pin change, and checked against the pins
- **From**: A.SDEP.03 (`uv lock --upgrade`, the merge check on every lock rewrite), A.U28.02 (re-lock so the `specifier`
  lines read `==` for pytest/mpremote/coverage), A.U24.72 (`coverage` joins the group), A.U28.03 (test reads the lock),
  A.U36.528 (CLAUDE.md rule text — no lock edit), A.U37.16 (blast: the final merge's check), A.U27.26 (blast: `uv sync
  --locked --check --offline` reads it), D17 of the inventory.
- **Site**: `uv.lock` (whole file).
- **Change**: never hand-edited: regenerated by `uv lock` with every `pyproject.toml` dependency change (U0 refresh with
  `--upgrade`; U24 `coverage`; U28 pytest/mpremote/uv pins), each regeneration followed by `uv sync` and the check that
  `ruff --version`, `mypy --version`, `zizmor --version`, `actionlint --version`, `shellcheck --version` equal the pins and
  every `[package.metadata.requires-dev] dev` specifier agrees with that package's resolved `version` (from U28 on,
  `tests_scripts/test_tool_pins.py` asserts the second half).
- **Resolved**: —
- **Unit**: U28 (last rewrite). Stages: U0 (A.SDEP.03), U24 (A.U24.72). Re-checked at U37 (A.SDEP.25).
  A-C2 step order: A.U37.16's part lands in D, not U37 (it needs A.U37.15, which lands in D).
- **Depends**: M.TOOL.024, M.TOOL.025.
- **Blast carried by**: CI `uv sync --locked` → M.TOOL.002; `test_tool_pins.py` → A.U28.03 (TSC); CLAUDE.md `uv.lock`
  bullet → A.U36.528 (DOCS); the release-merge check → A.U37.16 (PROC).
- **Kind**: code

## host_typecheck.ini (A-C gap pass: the file sits in no cluster; TOOL carries it beside `pyproject.toml`'s passes)

### M.TOOL.079 Host pass: scripts on the path, the strict flags, a true conftest reason
- **From**: M_SCR gap 2 (a) / A.U27.27 (`mypy_path` gains `scripts`, so `build_firmware.py`'s and the suite's sibling
  imports resolve and their ignores go), A.U27.22 (`enable_error_code`), A.U27.23 (2)-(3) (the conftest comment; the file
  checked alone), A.U0.60 (the conftest label), A.U8.24 (`disallow_any_explicit` and the `[mypy-<module>]` baseline
  sections), A.U20.32, A.U21.29, A.U23.47, A.U24.73, A.U26.76 (host modules leave the baseline as they clear),
  A.U34.11 (the emptied sections go), A.U37.02 (DONE check); blast-only: A.U1.01 (no legacy path in `files`, holds),
  M_SPEC's B.15 blast "`host_typecheck.ini` … comments → (TOOL)".
- **Site**: `host_typecheck.ini:1-36` (whole file).
- **Change**: end state, in order: `:1-6` header unchanged; `[mypy]`, `python_version = 3.11`, `files = buildgen,
  scripts, toolchain, tests_scripts, tests_hardware` unchanged; `:11-12` comment unchanged; `:14-16` → "#
  tests_scripts/conftest.py is checked alone by typecheck.sh: with both test tiers on mypy_path it would be a second
  bare `conftest` in this run." (if A.U27.23's single-file run still reports a duplicate module at landing, the line
  states that true reason instead, tagged "(agent, 2026-09-24)" — A.U0.60, the same outcome M.SPEC.043 (6) writes into
  B.15); `exclude` unchanged; `:19` unchanged; `:21-22` → "# The other entries mirror the sys.path pytest and a running
  script build (harness, dns_probe, runner, _toml_fixtures, micropython_overrides, the scripts' sibling modules),
  without which those imports type as Any (B.15)."; `namespace_packages`, `explicit_package_bases` unchanged;
  `mypy_path = ., tests_hardware, tests_hardware/bench, tests_hardware/manual, tests_scripts, toolchain, scripts`;
  the three display flags unchanged; `:31-32` comment and `strict = true` unchanged; then "# a bare `# type: ignore` is
  itself an error, so no suppression hides its code" / `enable_error_code = ignore-without-code`, then
  `disallow_any_explicit = true`; `:34` comment, `no_implicit_optional = true`, `warn_unreachable = true` unchanged.
  No `[mypy-<module>]` section remains. Every comment block ≤ 3 prose lines.
- **Resolved**: A.U8.24 (U8) and A.U27.22 (U27) edit the strictness lines — one edit per config (A.U27.22 Depends), the
  same structure M.TOOL.032 gives `pyproject.toml`'s pass. A.U0.60 is conditional on A.U27.23: the file stays excluded
  from the directory pass and is checked alone, so the reason is restated without "an accepted gap"; the dated tag is
  written only in the fallback outcome, as M.SPEC.043 does for B.15 (one text in both places). A.U27.27's ignore removal
  in `scripts/build_firmware.py` lands in the same commit as the `scripts` entry (M.SCR.065), since
  `warn_unused_ignores` (part of `strict`) fails it the day the import resolves.
- **Unit**: U34 (end state). Stages: U8 — `disallow_any_explicit = true` and one `[mypy-<module>]` section with
  `disallow_any_explicit = false` per host module holding findings at U8's end (A.U0.06's host-pass count gives the
  list), under A.U8.24's comment "baseline: a module leaves this list once its explicit-`Any` findings are cleared; the
  list ends empty (owner, 2026-09-28)"; U20 (`buildgen`, A.U20.32), U21 (`toolchain`, A.U21.29), U23 (A.U23.47), U24
  (`tests_scripts`, A.U24.73), U26 (`tests_hardware`, A.U26.76) — each unit removes its modules' sections in the commit
  that clears them; U27 — `scripts` on `mypy_path` with the `scripts/` sections removed (A.U27.27), `enable_error_code`
  (A.U27.22), the conftest and `mypy_path` comments (A.U27.23, A.U0.60); U34 — any emptied section and the baseline
  comment removed (A.U34.11); U37 — DONE check (A.U37.02).
- **Depends**: A.U0.06 (the U8 list), M.SCR.028 (`typecheck.sh` runs the single-file check), M.SCR.065/M.SCR.046
  (their import ignores go with the `scripts` entry).
- **Blast carried by**: `tests_scripts/test_lint_type_scopes.py` (the three configs' strictness flags) → A.U27.24 (TSC);
  `tests_scripts/test_mypy_any_baseline.py` → A.U8.24/A.U34.11 (TSC); `test_config_paths_resolve.py` (every `files`/
  `mypy_path` entry resolves) → A.U28.39 (TSC); SPEC B.15 → M.SPEC.043; CLAUDE.md mypy bullet → A.U27.22 docs slot
  (DOCS); BACKLOG chroot entries "all three mypy configs enable ignore-without-code", "typecheck.sh runs two single-file
  mypy checks", "host_typecheck.ini mypy_path gains scripts" → A.U27.22/A.U27.23/A.U27.27 (DOCS), the U8 baseline line →
  M_TOOL gap 7 (DOCS, M.DOCS.066); CLUSTERS.md names no cluster for this file → GAPS_G4 (orchestrator).
- **Kind**: code, rule

## Gaps for other clusters

1. **TSC** — A.U28.39's config-path check fails on a `pyproject.toml` per-file glob matching no tracked file; M.TOOL.030's
   `"build/generated_src/**"` entry matches only git-ignored, generated files. The check excepts that glob as it already
   excepts the mypy `files`/`mypy_path` entry (A.U28.31 proves the entry live on a generated tree).
2. **SCR / TSC** — `scripts/uv_sync_retried.sh` carries `# @tunable tool.uv_sync_attempts = 3` and `# @tunable
   tool.uv_sync_backoff_step_s = 10` (A.U8.14 via A.U28.01); the Python mirror is `setup_toolchain.NETWORK_ATTEMPTS` and
   `run_retried()`'s `backoff_s` default `10.0` under the same IDs (M.TOOL.046, D2): `test_uv_sync_retried_sh.py`
   compares against `NETWORK_ATTEMPTS`.
3. **SCR** — A.U26.02's image record reads the built image's lwIP options with
   `micropython_overrides.read_lwip_macros_from_build(uf2.parent, lwip_macros)`; `st.build_firmware()` keeps returning the
   uf2 path (M.TOOL.055, D3).
4. **SCR** — A.U27.13's `scripts/mpremote_connect.sh` relays the resolver's own failure line, which reads
   `setup_toolchain: no MicroPython board found …` (A.U27.29's form, D7), not `FAILED: …`; `setup_toolchain.py board`
   takes no toolchain lock and reads no `versions.toml` (D6).
5. **TEST_UNIT** — the inline `# noqa: F401` at `tests/test_website_build_integration.py:15` goes in U20, in the commit
   that adds `allowed-unused-imports = ["frozen_html"]` (RUF100 fails on it the same day), not in U28 (M.TOOL.031).
6. **HW_BENCH** — M.HW_BENCH.106's five module-level manual imports in `tests_hardware/manual/__main__.py` carry no inline
   `noqa`; M.TOOL.031's U26 stage adds their names to the pyflakes table in the same commit.
7. **DOCS (BACKLOG)** — the chroot list (CLAUDE.md "Pull request workflow"; A.U33.04's rule, A.U37.04 (3)'s close check)
   has no planned line for these build-environment changes: U0 `pyproject.toml`/`zizmor.yml`/`ci.yml` comment edits
   (A.U0.35/.37/.39/.40); U1 (A.U1.21, A.U1.22 — comments only); U8 (A.U8.14 tags in `versions.toml`, `ci.yml`,
   `setup_toolchain.py`, `micropython_overrides.py`; A.U8.15 `ci.yml` tags; A.U8.23 `mypy_path`; A.U8.24
   `disallow_any_explicit` and its baseline); U9 (A.U9.02 comment); U10 (A.U10.34 toolchain comments, A.U10.37/.38
   per-file keys); U15 (A.U15.43); U18 (A.U18.12 `mypy_path`); U21 — the installer leg for A.U21.01-.08, .10, .12, .15,
   .17-.30 (only A.U21.09 and A.U21.16 word a line: timeouts and streaming, the lock, the record, `sudo
   --preserve-env`, picotool skip, the command table and sudo probe, the armed bridge, Node record, leftovers, the third
   Unix binary); U22 (A.U22.04); U24 (A.U24.73); U25 (A.U25.40, A.U25.63, the deleted concurrency library's two entries);
   U26 (A.U26.19, A.U26.49, A.U26.54, A.U26.74 `addopts`); U27 (A.U27.07 override removal, A.U27.12 composite-action body,
   A.U27.25, A.U27.29 CLI); U36 (A.U36.512, A.U36.544 — comments only). One line per unit, "comments only, no build
   impact" where so.
8. **SPEC (Part N, B.10/B.10.1)** — rows: `ci.devices_timeout_min` (M.TOOL.016); `tool.uv_sync_attempts`/
   `tool.uv_sync_backoff_step_s` name both sites and "every retried network step, uv sync included" (D2);
   `tool.preprocess_timeout_s` also bounds the kbd and lwIP-host readbacks (M.TOOL.041); `tool.remote_query_timeout_s`
   covers the `sudo -n` probes, `tee`, `systemd-run`/`systemctl` (M.TOOL.046). B.10.1 (A.U28.37) states the two composite
   actions, the `devices` job and that matrix values reach scripts through `env` (D1).
9. **TWIN** — a new `digital_twin/` module that imports the twin's own `machine`/`network` (e.g. `run_device_script.py`,
   `_twin_common.py`) joins the main mypy pass's `exclude` in the unit creating it (M.TOOL.032 rule, D9): TWIN names which
   at landing by running the main pass.
10. **SCR / HW_BENCH** — a new host file spawning the repo's interpreter or scripts (`scripts/_twin_process.py`,
    `scripts/_digital_twin_scenarios.py`, `tests_hardware/twin_board.py`) gets its `S603`/`S607` per-file entry in the
    creating unit when ruff reports it (M.TOOL.030 rule, D8).
11. **PROC** — A.SDEP.19's W32 outcome (U0) fixes the local `uses:` form every later `.github` edit writes (M.TOOL.001,
    .002, .020, .022); A.SDEP.05 executes A.U28.13 in U0 (M.TOOL.005).

## Adherence findings (per file: rule → result; breaches fixed by M-ID or raised as Qn)

**`.github/actions/setup-micropython-toolchain/action.yml`** (end state M.TOOL.001): one header block (G9/R16) → line-1
comment, M.TOOL.001; comment cap → 1-line comments; tag-pinned `actions/*`, no third-party action (zizmor policy) → ok;
template injection (the input never in `run:`) → ok; no audit ID, no history narrative → ok (the "versions.toml-only key
once kept a stale binary" sentence moves to SPEC B.10 with A.U28.37); retry never simplified away (OR37.a (2)) → the
retry runs first, through the uv-sync action.

**`.github/actions/uv-sync/action.yml`** (M.TOOL.002): header → ok; bare `python3` version-checked (G8/R05) → ok; uv
pinned (G8/R54) → ok; the retry's reason stated once with its actor tag → ok.

**`.github/workflows/ci.yml`** (M.TOOL.003-.020): header block → M.TOOL.003; comment cap → every rewritten comment ≤ 3
lines; sequencing-not-gating (CLAUDE.md) → `unit-tests`, `unit-tests-gc-threshold`, `firmware-build-verify`,
`web-unit-tests` carry `!cancelled()`, every success-gated job states why (M.TOOL.007-.010, .015, .017); hang backstop
(`needs: lint-and-typecheck`, per-file timeout, `stdbuf`) → kept; retried sync ahead of `scripts/test.sh` → M.TOOL.013;
no variant literal (OR78.a) → derived matrices, `npm run build:site`, the `:130` comment (M.TOOL.007, .010, .016-.018);
no new permanent control arm (OR21.a (2)) → none added; coverage reports never gate, test results do (E.5.3) →
M.TOOL.009, .015; checkouts shallow, no `submodules:` (OR80.a) → ok; token scope stated truthfully → BREACH after
A.U28.07 (top comment "nothing needs more") fixed by M.TOOL.004; matrix values from a job output expanded inside `run:`
→ BREACH risk (template injection, zizmor) fixed by M.TOOL.017/.018 (`env`, D1); "no longer purely advisory" (history
wording, docs hold current state) → fixed by M.TOOL.015; budget numbers stated in comments and Part N (two homes) →
fixed by M.TOOL.019 (D4); no audit ID → ok (the one `run 34755468619` id in HEAD's comment goes with D4).

**`.github/zizmor.yml`** (M.TOOL.021-.022): header ≤ 3 lines → ok; Codecov named after its removal → fixed by M.TOOL.021;
actor tag and retirement trigger on the disable (G9/R38) → M.TOOL.022.

**`pyproject.toml`** (M.TOOL.023-.034): tool pins stay pinned (CLAUDE.md) → every dev entry and uv exact
(M.TOOL.024/.025); exemptions central, never inline noqa (owner, 2026-09-10, L44; OR83) → M.TOOL.030 (and the A.U37.02
inline-PLC0415 form settled against it); every exemption live (OR50.a (2)) → A.U28.31's check, M.TOOL.030; comment cap
→ every block ≤ 3 lines (the per-file block's reasons split into blocks); scope comment false after the generated tree
joins → fixed by M.TOOL.026; S110's "ruled out above" false once SIM105 narrows → fixed by M.TOOL.028; entries for a
deleted file (`tests/_webserver_concurrency_scenarios.py`, M.TEST_HELP.031) carried by no action → fixed by M.TOOL.030
and M.TOOL.032; the construction-library comment stale after M.TWIN.108 → fixed by M.TOOL.032; pyflakes allowances vs
RUF100 timing → staged by M.TOOL.031; E722 stays enabled (CLAUDE.md) → ok; `src/` carries no `method-assign` suppression
→ unchanged; no credential added (S105/S106 live everywhere else) → M.TOOL.030; no audit ID → ok.

**`toolchain/micropython_overrides.py`** (M.TOOL.035-.042): zero-touch (nothing written into the checkout) → every new
override writes under `build_overrides/` (M.TOOL.039/.040); each override proven in the built artefact (G8/R20) →
M.TOOL.041; anchors fail loudly (CLAUDE.md "Platform target") → M.TOOL.039/.040; comment cap and `#`-form explanations →
M.TOOL.035; pointers to permanent targets (G9/R12) → M.TOOL.037/.038; importable standalone by `buildgen/validate.py`
(stdlib only) → ok; no `TCP_NODELAY` (OR114.a (2)) → ok; no audit ID → ok.

**`toolchain/setup_toolchain.py`** (M.TOOL.043-.072): no explicit `Any` (OR81) → M.TOOL.043/.047/.052; user errors as one
line without traceback (OR23.a (3)) → M.TOOL.045/.072 (and every `SystemExit` → `SetupError`, M.TOOL.069); no secret in
argv or logs (G5/R59) → M.TOOL.068; dead-man's switch armed for every bridge change (CLAUDE.md hard rule) → M.TOOL.068;
every subprocess bounded (OR37.a (1)) → M.TOOL.046; `--help` without side effect (G8/R38) → M.TOOL.072; comment cap,
`#` form → M.TOOL.043; real hardware only with the owner's go-ahead → the installer is run by a person; its tests mock
every host command (A.U21.* L0); host disk churn (owner, 2026-09-17) → one small record file per run; a comment stating
"the only hand-tracked version is the MicroPython ref" false after `[stubs]` → fixed by M.TOOL.059.

**`toolchain/versions.toml`** (M.TOOL.073-.077): "Only the MicroPython ref is pinned by hand" false after `[stubs]` →
fixed by M.TOOL.074; the pin moves only on the owner's call (OR69.a (9)) stated where a move starts → fixed by M.TOOL.074
(D5); tags on tuned values (OR30.a) → M.TOOL.076; comment cap → ok.

**`uv.lock`** (M.TOOL.078): never hand-edited; pin-vs-resolved agreement checked on every rewrite (CLAUDE.md `uv.lock`
rule) → M.TOOL.078.

## Owner questions

None new. GEN Q1 is answered (OR131, AC_NOTES 41: option (a)); M.TOOL.032 writes `mypy_path` += `"ext/typings"` as firm.
GEN Q2 (OR132) touches no TOOL file.

## Agent decisions for the OR2.c review

- **D1** CI matrix values reach `run:` scripts through `env:` (`DEVICE`) once the matrices are derived from a job
  output (M.TOOL.017, M.TOOL.018) — template-injection hygiene; behaviour unchanged.
- **D2** The retry tunables keep A.U8.14's IDs (`tool.uv_sync_attempts`, `tool.uv_sync_backoff_step_s`) while the Python
  constant becomes `NETWORK_ATTEMPTS` (A.U21.17 allowed either) — one Part N row for the mirrored pair (M.TOOL.046).
- **D3** `build_firmware()` keeps returning the uf2 path; A.U26.02's record re-reads the lwIP options from the build dir
  (M.TOOL.055).
- **D4** CI budget comments keep their reason; the measured minutes and run ids live only in the Part N rows (M.TOOL.019).
- **D5** `versions.toml`'s header names the hand pins and the owner's-call rule (M.TOOL.074).
- **D6** `setup_toolchain.py board` runs before the lock and before `versions.toml` is read (M.TOOL.072).
- **D7** Every `setup_toolchain.py` failure prints `setup_toolchain: <message>` (A.U27.29's form), `board` included
  (M.TOOL.072).
- **D8** New subprocess-spawning host files get their `S603`/`S607` entries in the creating unit (M.TOOL.030).
- **D9** New `digital_twin/` modules needing the twin's API join the main pass's `exclude` in the creating unit
  (M.TOOL.032).
- **D10** A.U28.28's `S603` entry for `tests_hardware/isl29125_conformance.py` is not written: M.HW_BENCH.038 removes the
  subprocess it exempted (M.TOOL.030).
- **D11** The CI permissions comment names web-changes' `actions: read` (M.TOOL.004).
- **D12** `unit-tests-coverage`'s comment states its gate in present tense (M.TOOL.015).
- **D13** The `frozen_html` pyflakes allowance lands in U20 with the one inline noqa it makes unused; the manual names in
  U26 (M.TOOL.031).
- **D14** The global S110 and N8xx comments rewritten to stay true after the narrowing (M.TOOL.028).
- **D15** The generated `modlwip.c` header names the MicroPython version read from `py/mpconfig.h` (M.TOOL.039).
- **D16** The new readback functions take `env` from the installer rather than import it (M.TOOL.041).
- **D17** (A-C gap pass) TOOL carries `host_typecheck.ini`, which CLUSTERS.md names under no cluster, beside the other
  two mypy configs' strictness lines (M.TOOL.079); the stripper's N802 per-file entry is not written (M.TOOL.030).
- Carried, decided in A-L and listed there for this review: A.U21.26 (sudoers checked and listed, never written),
  A.U21.19's argv fallback for the PSK (superseded: passed plainly, owner, 2026-10-02, OR140.a (1)), A.U21.13's one-time unpatched control build (not a CI arm), A.U28.07 (the web
  filter's last-green base), A.U28.19 (monthly Firefox period), A.U28.27 (host TRY003/EM exemptions), A.U28.36 (budget
  margin rule), A.U28.01 (the second composite action).

## Ledger

| action ID | merged into M-ID / dropped (reason) |
|---|---|
| A.C.01 | no TOOL edit (C round frame reads `get_interface_mac()`/`ensure_bench_bridge()` behaviour; PROC) |
| A.C.02 | no TOOL edit (R0 runs the installer's checks; PROC) |
| A.S0930.04 | M.TOOL.019 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.S0930.27 | M.TOOL.019 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.SDEP.01 | no TOOL edit (refresh order and record; PROC) — order applied in every U0 stage above |
| A.SDEP.02 | no TOOL edit (check gate; PROC) — new-rule decisions land via M.TOOL.025/.028/.030 |
| A.SDEP.03 | M.TOOL.022, M.TOOL.024, M.TOOL.025, M.TOOL.028, M.TOOL.078 |
| A.SDEP.04 | M.TOOL.069 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.SDEP.05 | M.TOOL.001, M.TOOL.005, M.TOOL.006, M.TOOL.020 |
| A.SDEP.08 | M.TOOL.001, M.TOOL.073 |
| A.SDEP.09 | M.TOOL.077 |
| A.SDEP.11 | M.TOOL.037, M.TOOL.040, M.TOOL.056 |
| A.SDEP.12 | M.TOOL.044, M.TOOL.055 |
| A.SDEP.13 | M.TOOL.039, M.TOOL.040 |
| A.SDEP.14 | M.TOOL.038, M.TOOL.075, M.TOOL.076 |
| A.SDEP.15 | M.TOOL.077 |
| A.SDEP.16 | M.TOOL.056 |
| A.SDEP.19 | M.TOOL.001, M.TOOL.002, M.TOOL.010, M.TOOL.012, M.TOOL.020, M.TOOL.022 |
| A.SDEP.21 | no TOOL edit (BACKLOG/SPEC/CLAUDE.md records; DOCS) |
| A.SDEP.24 | no TOOL edit (plan corpus; audit file) |
| A.SDEP.25 | M.TOOL.024, M.TOOL.061, M.TOOL.073, M.TOOL.077 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U0.03 | no TOOL edit (toolchain built for the corpus; PROC) |
| A.U0.06 | no TOOL edit (baseline record; its uv line feeds M.TOOL.024) |
| A.U0.07 | M.TOOL.030 |
| A.U0.21 | M.TOOL.032, M.TOOL.033 |
| A.U0.35 | M.TOOL.028, M.TOOL.030 |
| A.U0.37 | M.TOOL.015, M.TOOL.028, M.TOOL.030 |
| A.U0.39 | M.TOOL.030 |
| A.U0.40 | M.TOOL.022 |
| A.U0.55 | no TOOL edit (CLAUDE.md actor tags; `ci.yml:419-420` comment needs none) |
| A.U0.57 | no TOOL edit (`pyproject.toml:50` needs none) |
| A.U1.01 | M.TOOL.011 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U1.05 | no TOOL edit (recipe moved to `tests_hardware/README.md`; the two comments are A.U1.22 → M.TOOL.066) |
| A.U1.07 | no TOOL edit (README prerequisite) |
| A.U1.08 | no TOOL edit (`dev_legacy/` citers in `setup_toolchain.py` are A.U1.22 → M.TOOL.066) |
| A.U1.09 | no TOOL edit (`tests_scripts` check; S603 already exempt) |
| A.U1.12 | no TOOL edit (CLAUDE.md) |
| A.U1.21 | M.TOOL.012, M.TOOL.026 |
| A.U1.22 | M.TOOL.058, M.TOOL.066 |
| A.U5.17 | M.TOOL.029, M.TOOL.030 |
| A.U5.18 | M.TOOL.029 |
| A.U6.03 | M.TOOL.010 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U6.04 | M.TOOL.027 |
| A.U6.10 | M.TOOL.019 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U6.11 | M.TOOL.010, M.TOOL.019 |
| A.U6.12 | M.TOOL.005, M.TOOL.007, M.TOOL.010 |
| A.U6.15 | no TOOL edit (variant-literal check; its `ci.yml` entry clears with M.TOOL.016-.018) |
| A.U7.03 | M.TOOL.013 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U7.08 | no TOOL edit (`scripts/test.sh` pytest record) |
| A.U7.09 | no TOOL edit (twin suite summary; CI reads the exit code) |
| A.U7.10 | M.TOOL.007, M.TOOL.009 |
| A.U7.11 | no TOOL edit (`lint.sh` summary; CI runs tools directly) |
| A.U7.12 | no TOOL edit (summary records; CI reads exit codes) |
| A.U7.19 | M.TOOL.072 |
| A.U7.21 | M.TOOL.010, M.TOOL.019 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U7.26 | no TOOL edit (`tests_scripts` skip → fail) |
| A.U8.14 | M.TOOL.001, M.TOOL.014, M.TOOL.037, M.TOOL.038, M.TOOL.041, M.TOOL.046, M.TOOL.076 (the two `action.yml` loop tags dropped: A.U28.01 removes the loop; they move with it to `scripts/uv_sync_retried.sh`, SCR) |
| A.U8.15 | M.TOOL.005, M.TOOL.006, M.TOOL.016, M.TOOL.019 |
| A.U8.23 | M.TOOL.032, M.TOOL.033 (its restated decorator-override comment is an interim U8-U27 stage; A.U27.07 removes the override) |
| A.U8.24 | M.TOOL.032, M.TOOL.033, M.TOOL.047; M.TOOL.079 (gap pass: `host_typecheck.ini`) |
| A.U9.02 | M.TOOL.028, M.TOOL.030 |
| A.U10.30 | blast only — `buildgen/validate.py` loads `micropython_overrides.py` by path; stays stdlib-only (M.TOOL.035) |
| A.U10.34 | M.TOOL.035, M.TOOL.043, M.TOOL.066, M.TOOL.067 |
| A.U10.37 | M.TOOL.030 |
| A.U10.38 | M.TOOL.028, M.TOOL.030 |
| A.U10.46 | M.TOOL.033 |
| A.U10.47 | M.TOOL.028 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U11.38 | M.TOOL.028, M.TOOL.030 |
| A.U11.S01 | M.TOOL.033 |
| A.U11.S02 | M.TOOL.033 |
| A.U11.S03 | M.TOOL.030, M.TOOL.033 |
| A.U14.23 | no TOOL edit (BACKLOG text) |
| A.U14.24 | M.TOOL.051 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U14.30 | M.TOOL.038, M.TOOL.075, M.TOOL.076 (its OR112 sizing already withdrawn by OR114.a (3); text change 3 kept) |
| A.U15.02 | no TOOL edit (no shim-specific pyproject entry) |
| A.U15.43 | M.TOOL.030, M.TOOL.033 |
| A.U16.S01 | M.TOOL.033 |
| A.U17.11 | no TOOL edit (L0 reads the working tree; no `ci.yml` change) |
| A.U17.26 | M.TOOL.033 |
| A.U18.12 | M.TOOL.032 |
| A.U18.18 | M.TOOL.038, M.TOOL.075, M.TOOL.076 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U18.44 | M.TOOL.033 |
| A.U19.05 | M.TOOL.030 |
| A.U19.17 | M.TOOL.030, M.TOOL.033 |
| A.U20.14 | M.TOOL.031, M.TOOL.033 |
| A.U20.32 | M.TOOL.030, M.TOOL.033; M.TOOL.079 (gap pass: `host_typecheck.ini`) |
| A.U20.33 | M.TOOL.023, M.TOOL.035, M.TOOL.043 |
| A.U20.35 | no TOOL edit (SPEC L.3 states `[lwip]`'s HEAD values, M.TOOL.076 keeps them) |
| A.U21.01 | M.TOOL.048 |
| A.U21.02 | M.TOOL.060, M.TOOL.072, M.TOOL.073, M.TOOL.074 |
| A.U21.03 | M.TOOL.043, M.TOOL.051, M.TOOL.058, M.TOOL.060, M.TOOL.061, M.TOOL.069, M.TOOL.071 |
| A.U21.04 | no TOOL edit (`scripts/typecheck.sh`, SCR; CI runs it unchanged) |
| A.U21.05 | M.TOOL.051, M.TOOL.060, M.TOOL.074 |
| A.U21.06 | M.TOOL.037, M.TOOL.041, M.TOOL.056 |
| A.U21.07 | M.TOOL.001 |
| A.U21.08 | M.TOOL.036, M.TOOL.037, M.TOOL.038, M.TOOL.039, M.TOOL.040 |
| A.U21.09 | M.TOOL.039 |
| A.U21.10 | M.TOOL.018, M.TOOL.039, M.TOOL.041, M.TOOL.055 |
| A.U21.11 | M.TOOL.018 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U21.12 | M.TOOL.013, M.TOOL.019, M.TOOL.037, M.TOOL.038, M.TOOL.040, M.TOOL.041, M.TOOL.054, M.TOOL.056, M.TOOL.057, M.TOOL.058 |
| A.U21.15 | M.TOOL.053, M.TOOL.055, M.TOOL.056 |
| A.U21.16 | M.TOOL.037, M.TOOL.038, M.TOOL.040, M.TOOL.044, M.TOOL.055, M.TOOL.056 |
| A.U21.17 | M.TOOL.030, M.TOOL.046, M.TOOL.049, M.TOOL.050, M.TOOL.051, M.TOOL.052, M.TOOL.054, M.TOOL.055, M.TOOL.056, M.TOOL.059, M.TOOL.060, M.TOOL.067, M.TOOL.068, M.TOOL.069, M.TOOL.070 |
| A.U21.18 | M.TOOL.018, M.TOOL.049 |
| A.U21.19 | M.TOOL.046, M.TOOL.068, M.TOOL.071, M.TOOL.072 |
| A.U21.20 | no TOOL edit (`tests_scripts` fixture, TSC) |
| A.U21.21 | M.TOOL.061, M.TOOL.069 |
| A.U21.22 | M.TOOL.050, M.TOOL.060, M.TOOL.061, M.TOOL.062, M.TOOL.072 |
| A.U21.23 | M.TOOL.068 |
| A.U21.24 | M.TOOL.065, M.TOOL.069, M.TOOL.071 |
| A.U21.25 | M.TOOL.046, M.TOOL.067 |
| A.U21.26 | M.TOOL.065, M.TOOL.071 |
| A.U21.27 | M.TOOL.052, M.TOOL.060, M.TOOL.071 |
| A.U21.28 | M.TOOL.064, M.TOOL.072 (its "FAILED: …" line superseded by A.U27.29's form, D7) |
| A.U21.29 | M.TOOL.018, M.TOOL.043, M.TOOL.047; M.TOOL.079 (gap pass: `host_typecheck.ini`) |
| A.U21.30 | M.TOOL.042, M.TOOL.057, M.TOOL.060, M.TOOL.063, M.TOOL.069 |
| A.U21.31 | M.TOOL.038, M.TOOL.075 |
| A.U22.04 | M.TOOL.030, M.TOOL.033 |
| A.U23.38 | M.TOOL.006, M.TOOL.019 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U23.47 | M.TOOL.033; M.TOOL.079 (gap pass: `host_typecheck.ini`) |
| A.U24.40 | no TOOL edit (`tests_scripts` anchor-count test, TSC) |
| A.U24.48 | no TOOL edit (ESLint; CI web lint step unchanged) |
| A.U24.51 | no TOOL edit (`tests_scripts` device loops) |
| A.U24.52 | no TOOL edit (JS message names `setup_toolchain.py setup`; command unchanged) |
| A.U24.66 | no TOOL edit (`tests_scripts` device fixtures) |
| A.U24.72 | M.TOOL.015, M.TOOL.019, M.TOOL.025, M.TOOL.078 |
| A.U24.73 | M.TOOL.030, M.TOOL.033; M.TOOL.079 (gap pass: `host_typecheck.ini`) |
| A.U24.75 | no TOOL edit (`test_micropython_overrides.py` → module-level tests, TSC) |
| A.U25.37 | M.TOOL.019 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U25.39 | no TOOL edit (no pyproject/CI entry names the unwedge helper; its retirement rests on M.TOOL.041's proof) |
| A.U25.40 | M.TOOL.032 |
| A.U25.42 | M.TOOL.030 |
| A.U25.46 | M.TOOL.032 |
| A.U25.48 | M.TOOL.017, M.TOOL.019 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U25.55 | M.TOOL.019 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U25.62 | no TOOL edit (N801 comment is A.U10.38's → M.TOOL.028/.030) |
| A.U25.63 | M.TOOL.030, M.TOOL.033 |
| A.U25.74 | M.TOOL.019 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U26.02 | M.TOOL.041, M.TOOL.055 |
| A.U26.03 | M.TOOL.038 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U26.19 | M.TOOL.030 |
| A.U26.31 | no TOOL edit (collect matrix; reads `files`) |
| A.U26.44 | M.TOOL.032 (its `:363`/`:370` comment text superseded by A.U27.25's, U27) |
| A.U26.49 | M.TOOL.030 |
| A.U26.54 | M.TOOL.030 |
| A.U26.74 | M.TOOL.034 |
| A.U26.75 | no TOOL edit (hardware runners call `scripts/uv_sync_retried.sh`, SCR) — provided by M.TOOL.002's script |
| A.U27.02 | M.TOOL.047, M.TOOL.059, M.TOOL.074, M.TOOL.077 |
| A.U27.07 | M.TOOL.033 |
| A.U27.09 | M.TOOL.011, M.TOOL.026, M.TOOL.032 |
| A.U27.10 | M.TOOL.002, M.TOOL.018, M.TOOL.023 |
| A.U27.11 | M.TOOL.010 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U27.12 | M.TOOL.001, M.TOOL.007 |
| A.U27.13 | no TOOL edit (SCR) — its quoted failure text follows M.TOOL.072 (Gap 4) |
| A.U27.14 | M.TOOL.019 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U27.16 | M.TOOL.017 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U27.21 | no TOOL edit (CI runs the checker through the pytest tier) |
| A.U27.22 | M.TOOL.032; M.TOOL.079 (gap pass: `host_typecheck.ini`) |
| A.U27.23 | M.TOOL.032; M.TOOL.079 (gap pass: `host_typecheck.ini`) |
| A.U27.24 | M.TOOL.011 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U27.25 | M.TOOL.011, M.TOOL.032 |
| A.U27.26 | M.TOOL.078 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U27.28 | M.TOOL.003 |
| A.U27.29 | M.TOOL.035, M.TOOL.045, M.TOOL.072 |
| A.U27.31 | M.TOOL.018 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U27.35 | no TOOL edit (`build_website.sh` interface unchanged in CI) |
| A.U27.37 | M.TOOL.034 |
| A.U27.38 | M.TOOL.019 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U27.39 | M.TOOL.010 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U28.01 | M.TOOL.001, M.TOOL.002, M.TOOL.006, M.TOOL.011, M.TOOL.012, M.TOOL.013, M.TOOL.015, M.TOOL.046 |
| A.U28.02 | M.TOOL.002, M.TOOL.024, M.TOOL.025, M.TOOL.078 |
| A.U28.03 | M.TOOL.078 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U28.04 | M.TOOL.001, M.TOOL.007, M.TOOL.008, M.TOOL.009, M.TOOL.010 |
| A.U28.05 | M.TOOL.018, M.TOOL.052 |
| A.U28.06 | M.TOOL.016, M.TOOL.017, M.TOOL.018, M.TOOL.019 |
| A.U28.07 | M.TOOL.004, M.TOOL.005 |
| A.U28.08 | no TOOL edit (TSC) — its rules are what M.TOOL.001-.020 satisfy |
| A.U28.09 | M.TOOL.007, M.TOOL.008, M.TOOL.009, M.TOOL.010 |
| A.U28.10 | no TOOL edit (CLAUDE.md) |
| A.U28.13 | M.TOOL.005, M.TOOL.021 |
| A.U28.14 | M.TOOL.021 |
| A.U28.15 | M.TOOL.015, M.TOOL.021 |
| A.U28.16 | M.TOOL.009 |
| A.U28.17 | M.TOOL.010 |
| A.U28.19 | M.TOOL.010 |
| A.U28.20 | M.TOOL.070, M.TOOL.071 |
| A.U28.21 | no TOOL edit (cross-browser installer; `ci.yml:307` unchanged) |
| A.U28.22 | no TOOL edit (cross-browser installer) |
| A.U28.23 | no TOOL edit (`package.json`, WEB) |
| A.U28.24 | no TOOL edit (`package.json`/preview server, WEB/SCR) |
| A.U28.25 | M.TOOL.005 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U28.27 | M.TOOL.028, M.TOOL.030; (gap pass: the stripper's N802 entry dropped from M.TOOL.030, M_SCR gap 2 (b)) |
| A.U28.28 | M.TOOL.030, M.TOOL.031, M.TOOL.038 (its `tests_hardware/isl29125_conformance.py` `S603` entry dropped: M.HW_BENCH.038 removes the subprocess, D10) |
| A.U28.29 | M.TOOL.028, M.TOOL.030 (its "copies of that password" group dropped: empty after A.U26.49, U26) |
| A.U28.31 | M.TOOL.027, M.TOOL.028, M.TOOL.030 |
| A.U28.32 | M.TOOL.028 |
| A.U28.34 | no TOOL edit (CLAUDE.md scope sentence) |
| A.U28.35 | M.TOOL.020 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U28.36 | M.TOOL.006, M.TOOL.019 |
| A.U28.37 | no TOOL edit (SPEC) — carries the B.10/B.10.1 texts of M.TOOL.001-.020 |
| A.U28.38 | no TOOL edit (BACKLOG) — carries the U28 chroot line |
| A.U28.39 | no TOOL edit (TSC) — Gap 1 |
| A.U28.40 | no TOOL edit (CLAUDE.md zizmor bullet) |
| A.U28.41 | M.TOOL.011, M.TOOL.030 |
| A.U28.42 | M.TOOL.001, M.TOOL.002, M.TOOL.003 |
| A.U28.43 | M.TOOL.002, M.TOOL.006, M.TOOL.019 |
| A.U29.01 | M.TOOL.028, M.TOOL.030 |
| A.U29.03 | M.TOOL.030 |
| A.U33.04 | no TOOL edit (BACKLOG chroot list) — Gap 7 |
| A.U33.05 | no TOOL edit (BACKLOG → SPEC B.16) |
| A.U33.06 | M.TOOL.028 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U34.05 | no TOOL edit (CPY001 reason unaffected) |
| A.U34.07 | M.TOOL.028 |
| A.U34.08 | no TOOL edit (freezefs record) |
| A.U34.09 | M.TOOL.020 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U34.11 | M.TOOL.030, M.TOOL.033; M.TOOL.079 (gap pass: `host_typecheck.ini`) |
| A.U35.04 | no TOOL edit (faults planted in a throwaway worktree only) |
| A.U35.23 | no TOOL edit (timings recorded in an audit file) |
| A.U36.007 | M.TOOL.072 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U36.023 | no TOOL edit (SPEC Part F intro; the notice text M.TOOL.060 cites it) |
| A.U36.043 | no TOOL edit (CLAUDE.md/SPEC exclusion lists; the pyproject line is A.U25.40 → M.TOOL.032) |
| A.U36.512 | M.TOOL.056, M.TOOL.057, M.TOOL.072 |
| A.U36.519 | M.TOOL.074 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U36.522 | M.TOOL.068 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U36.524 | no TOOL edit (chroot recipe → SPEC B.17; its uv line follows M.TOOL.024) |
| A.U36.526 | M.TOOL.015, M.TOOL.021 |
| A.U36.528 | M.TOOL.078 |
| A.U36.542 | no TOOL edit (SPEC 0.4 cites `max-args`) |
| A.U36.544 | M.TOOL.028, M.TOOL.030, M.TOOL.037, M.TOOL.038, M.TOOL.067 |
| A.U36.547 | M.TOOL.072 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U37.02 | M.TOOL.030, M.TOOL.033 (its inline `# noqa: PLC0415` form dropped for per-file entries: owner rule L44/OR83); M.TOOL.079 (gap pass: `host_typecheck.ini`) |
| A.U37.04 | no TOOL edit (close check of the chroot list) — Gap 7 |
| A.U37.15 | no TOOL edit (no `audit/` exclusion in any TOOL file, grep) |
| A.U37.16 | M.TOOL.078 (blast/read: no edit of its own to a TOOL file beyond what the cited change states) |
| A.U0.60 | M.TOOL.079 (the `host_typecheck.ini` half; gap pass) |
| A.U27.27 | M.TOOL.079 (`mypy_path` gains `scripts`; gap pass, M_SCR gap 2 (a)) |
| A.U26.76 | M.TOOL.079 (`tests_hardware` host modules leave the baseline; gap pass) |
| A.U26.05 | M.TOOL.032 (the `run_device_script` exclude; gap pass, GAPS_G3 hand-off 1) |

## A-C2 order notes (2026-10-01)

Unit and Depends edits made by the A-C2 work order (`audit/order/WORK_ORDER.md`); one row per edit.

| M-ID | slot | edit | reason |
|---|---|---|---|
| M.TOOL.021 | Unit | appended: A-C2 step order: A.U28.13's part lands in U0 (A.SDEP.05: "A.U28.13 (pulled forward)" into the GitHub Actions pin refresh). | a part lands outside the Unit slot's units by an action's own text |
| M.TOOL.078 | Unit | appended: A-C2 step order: A.U37.16's part lands in D, not U37 (it needs A.U37.15, which lands in D). | dependency deferral (an edge ran from a later step) |
