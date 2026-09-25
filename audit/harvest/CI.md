# Harvest — CI: CI, dependency pins and supply chain

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: SETTLED 40, INVAR 21, MIRROR 4, LIMIT 23, RISK 8, ASSUME 19, PLATFORM 8, WORKAROUND 16, SUPPRESS 36, TODO 14, DRIFT 16, NOTE 4 — 209 items.


## tests/test_setter_microdot_integration.py

- **CI.N001** TODO · `tests/test_setter_microdot_integration.py:24-25` — "ext/ isn't on this project's
  mypy search path yet (see pyproject.toml's [tool.mypy]) - same gap as src/asy_webserver_service.py's
  own import" — microdot imports are unchecked by mypy; suppressed with import-not-found · [H05]

## scripts/test.sh

- **CI.N002** SETTLED · `scripts/test.sh:473-475, 551-553` — "Coverage is a report and never gates, but
  the test result under this binary must (exit 3 below)" — Exit 0/1/3 contract; CI gates on 1 and
  tolerates 3 (Part E.5.3). · related: CI.T11 · [H09]
- **CI.N003** PLATFORM · `scripts/test.sh:509-510` — "GitHub keeps only 10 error annotations per step" —
  Annotation budget (1 pytest + 8 files + 1 overflow) depends on a GitHub platform limit. · [H09]
- **CI.N004** RISK · `scripts/test.sh:505-507, 522-523` — "A workflow-command annotation is the only
  channel that carries a failing file's own output off the runner" — Last 40 log lines of a failing file
  are emitted into public PR annotations. · covered-by: CI.T15 · [H09]

## scripts/lint.sh

- **CI.N005** SUPPRESS · `scripts/lint.sh:24-26` — "--offline drops the two audits needing the GitHub
  API" — zizmor runs with two online audits permanently disabled, in every environment. · related:
  CI.T06 · [H09]

## scripts/typecheck.sh

- **CI.N006** LIMIT · `scripts/typecheck.sh:65-67` —
  "micropython-rp2-rpi_pico_w-stubs==${firmware_version}.*" — Stubs float across `.postN` releases and
  are fetched from the network on every run. · covered-by: CI.T04 · [H09]
- **CI.N007** DRIFT · `scripts/typecheck.sh:105-107` — "CI's lint-and-typecheck job passes `src tests`"
  — ci.yml passes `src tests tests_hardware/device_scripts`. · covered-by: CI.S03 · [H09]

## scripts/setup_cross_browser_toolchain.sh

- **CI.N008** SETTLED · `scripts/setup_cross_browser_toolchain.sh:6-7` — "None of the three channels
  below is the obvious one for its engine" — Channel choice per engine is deliberate (Part H.7). · [H09]
- **CI.N009** SUPPRESS · `scripts/setup_cross_browser_toolchain.sh:10-14` — "Non-fatal, like
  toolchain/setup_toolchain.py's own ensure_apt_packages()" — `apt-get update` failures swallowed via
  `|| echo`; only installs gate. · related: CI.T14 · [H09]
- **CI.N010** RISK · `scripts/setup_cross_browser_toolchain.sh:29` — "curl -sS
  https://packages.microsoft.com/keys/microsoft.asc — gpg --dearmor" | Apt key imported without
  fingerprint check. · covered-by: CI.S18 · [H09]
- **CI.N011** PLATFORM · `scripts/setup_cross_browser_toolchain.sh:30` — "deb [arch=amd64
  signed-by=...]" — Edge repo hardcoded to amd64. · covered-by: CI.S06 · [H09]
- **CI.N012** SETTLED · `scripts/setup_cross_browser_toolchain.sh:39-40` — "Deliberately unpinned,
  unlike toolchain/versions.toml's MicroPython pin (Part H.7)" — Firefox/geckodriver float; `latest`
  micromamba fetched with no checksum (:50). · covered-by: CI.S06 · [H09]
- **CI.N013** LIMIT · `scripts/setup_cross_browser_toolchain.sh:18, 27, 45` — "if ! command -v
  WebKitWebDriver >/dev/null 2>&1" — Idempotency by presence only; an installed but outdated engine is
  never refreshed. (low) · [H09]

## scripts/_render_coverage.py

- **CI.N014** LIMIT · `scripts/_render_coverage.py:4` — "# dependencies = [\"coverage\"]" — PEP 723
  dependency is unpinned. · covered-by: CI.T04 · [H09]

## scripts/_digital_twin_ci_suite.py

- **CI.N015** SETTLED · `scripts/_digital_twin_ci_suite.py:436-437` — "S603 exemption is central, see
  pyproject.toml." — subprocess-without-shell exemption lives in pyproject. · [H09]

## scripts/cross_browser_smoke.mjs

- **CI.N016** WORKAROUND · `scripts/cross_browser_smoke.mjs:33` — "same dev-sandbox path
  vitest.config.js already special-cases" — Hard-coded `/opt/pw-browsers/chromium` sandbox fallback;
  removal trigger: none stated. · related: CI.S15 · [H09]
- **CI.N017** RISK · `scripts/cross_browser_smoke.mjs:476-479, 498-501` — "SKIP ${engine.name}: binary
  not found (run scripts/setup_cross_browser_toolchain.sh)" — A missing engine is a warning; the run
  passes if any engine (Chromium is always "available") ran. · related: TEST.T16 · [H09]

## toolchain/setup_toolchain.py

- **CI.N018** MIRROR · `toolchain/setup_toolchain.py:121` — "UV_SYNC_ATTEMPTS = 3 # mirrors ci.yml's
  unit-tests job" — Retry count hand-mirrored from CI. · related: CI.S17 · [H09]
- **CI.N019** WORKAROUND · `toolchain/setup_toolchain.py:124-133` — "uv sync builds actionlint-py, which
  fetches its binary from a release URL; a 502 there once failed a clean install" — Retry around a
  third-party download; removal trigger: none stated. · related: CI.T04 · [H09]
- **CI.N020** SETTLED · `toolchain/setup_toolchain.py:929-931` — "so there is exactly one pin rather
  than a second one living here" — Node major is taken from `.nvmrc` only. · [H09]
- **CI.N021** LIMIT · `toolchain/setup_toolchain.py:951-966, 992` — "Resolved rather than assembled: the
  patch version moves" — Node floats within the major (`latest-vNN.x`); arch map covers aarch64/x86_64
  only. · covered-by: TOOL.T13 · [H09]
- **CI.N022** RISK · `toolchain/setup_toolchain.py:996-1003` — "Verified against the same SHASUMS the
  filename came from" — Checksum from the same origin, no signature; `next(...)` without default raises
  a raw StopIteration. · covered-by: TOOL.S02 · [H09]
- **CI.N023** LIMIT · `toolchain/setup_toolchain.py:1014-1019` — "run_retried([\"uv\", \"sync\"],
  cwd=repo_root)" — `uv sync` without `--locked`/`--frozen`; inherits caller env. · related: CI.S04 ·
  [H09]
- **CI.N024** RISK · `toolchain/setup_toolchain.py:1042-1060` — "non-fatal throughout, so a Python-only
  machine still finishes `env`" — Playwright install failure is logged and `env` still reports the tier
  "ready". · covered-by: TOOL.T13 · [H09]

## .github/actions/setup-micropython-toolchain/action.yml

- **CI.N025** DRIFT · `.github/actions/setup-micropython-toolchain/action.yml:4-7` — "(web-unit-tests,
  web-coverage, web-cross-browser-smoke, unit-tests, digital-twin-e2e, firmware-build-verify) ... all
  six" — Nine jobs use the action (also web-put-matrix, unit-tests-gc-threshold, unit-tests-coverage). ·
  covered-by: CI.S08 · [H09]
- **CI.N026** LIMIT · `.github/actions/setup-micropython-toolchain/action.yml:8-11` — "this action only
  restores the cache, it never runs setup_toolchain.py itself" — Each caller hand-copies an `-x`-only
  build-if-missing step (no variant/staleness probe). · related: CI.T12 · [H09]
- **CI.N027** LIMIT · `.github/actions/setup-micropython-toolchain/action.yml:16-18` — "run: pip install
  uv" — uv itself unpinned. · covered-by: CI.S04 · [H09]
- **CI.N028** WORKAROUND · `.github/actions/setup-micropython-toolchain/action.yml:19-30` —
  "actionlint-py fetches its binary at build time, so one bad response fails a healthy lane" — Retried
  `uv sync` (3 attempts, no `--locked`); removal trigger: none stated. · related: CI.S17 · [H09]
- **CI.N029** LIMIT · `.github/actions/setup-micropython-toolchain/action.yml:35-38` — "Hashes
  setup_toolchain.py too, not just versions.toml ... a versions.toml-only key once kept a stale binary
  alive" — Key omits `toolchain/micropython_overrides.py` and any runner image/compiler identity. ·
  covered-by: CI.S01 · [H09]
- **CI.N030** ASSUME · `.github/actions/setup-micropython-toolchain/action.yml:36-37` — "Shared by every
  caller: first job builds, later ones hit." — Cache is saved only on job success. · covered-by: CI.S09
  · [H09]

## .github/zizmor.yml

- **CI.N031** SETTLED · `.github/zizmor.yml:1-3` — "Only unpinned-uses is configured; every other audit
  stays at its default, so a new release surfaces new checks to triage" — Default-on audits by policy. ·
  related: CI.T06 · [H09]
- **CI.N032** SETTLED · `.github/zizmor.yml:8-10` — "First-party actions: a tag is enough - a
  compromised actions/* org compromises the platform itself" — `actions/*` ref-pinned (no Dependabot). ·
  covered-by: CI.T06 · [H09]
- **CI.N033** SETTLED · `.github/zizmor.yml:11-13` — "Everything third-party (codecov/, dorny/) is
  SHA-pinned" — SHA bumps are manual. · covered-by: CI.T06 · [H09]
- **CI.N034** SUPPRESS · `.github/zizmor.yml:14-18` — "Disabled, not fixed: it wants `uses: $/.github/...`,
  which actionlint 1.7.12 rejects" — `self-repository` audit disabled; removal trigger: actionlint
  accepts the syntax. · related: CI.T06 · [H09]

## .github/workflows/ci.yml

- **CI.N035** SETTLED · `.github/workflows/ci.yml:3-9` — "`push` is the load-bearing one: a PR
  conflicted with its base has no merge ref ... (128 commits once" — Dual trigger by design; `branches: ['**']`
  excludes tag pushes. · related: CI.T09 · [H09]
- **CI.N036** RISK · `.github/workflows/ci.yml:11-15` — "cancel-in-progress keeps exactly one run per
  push; which survives does not matter" — Combined with the per-push filter base, a cancelled run's web
  change may never be re-filtered. · covered-by: CI.S11 · [H09]
- **CI.N037** SETTLED · `.github/workflows/ci.yml:17-19` — "Deny-by-default GITHUB_TOKEN; each job
  grants itself contents: read" — Enforced by zizmor. · covered-by: CI.T06 · [H09]
- **CI.N038** LIMIT · `.github/workflows/ci.yml:22-57` — "Gates the web tier on whether THIS PUSH
  touched the website or its tooling" — Filter omits `src/**`, `buildgen/**`, `devices/**`,
  `digital_twin/**`, `toolchain/**` though web/live-twin tests depend on them. · covered-by: CI.S02 ·
  [H09]
- **CI.N039** ASSUME · `.github/workflows/ci.yml:38-41` — "naming the pushed branch compares against the
  commit before the push" — dorny/paths-filter push semantics (first push of a branch, force-push). ·
  covered-by: CI.T09 · [H09]
- **CI.N040** RISK · `.github/workflows/ci.yml:59-64, 88-93` — "needs: [web-changes,
  web-lint-and-typecheck]" — Web tests are success-gated on web lint (no `!cancelled()`), unlike
  CLAUDE.md's sequencing-not-gating rule for the Python lanes. · related: CI.T01 · [H09]
- **CI.N041** ASSUME · `.github/workflows/ci.yml:124-129, 174-179, 218-223, 291-296` — "if [ ! -x
  \"$bin\" ]; then uv run toolchain/setup_toolchain.py setup" — Four copies of an existence-only
  build-if-missing step. · covered-by: CI.T12 · [H09]
- **CI.N042** SETTLED · `.github/workflows/ci.yml:135-147` — "one runner per shard, so the twin's fixed
  port never collides" / "fail-fast: false" — PUT matrix sharding relies on one runner per shard for
  port isolation. · related: TEST.T14 · [H09]
- **CI.N043** SUPPRESS · `.github/workflows/ci.yml:224-228` — "A report, not a gate ...
  continue-on-error: true" — web-coverage's test step is advisory, unlike the Python coverage job. ·
  covered-by: CI.S12 · [H09]
- **CI.N044** SUPPRESS · `.github/workflows/ci.yml:229-252` — "continue-on-error: true" — Web coverage
  summary and artifact upload steps advisory. · related: CI.T11 · [H09]
- **CI.N045** LIMIT · `.github/workflows/ci.yml:299-305` — "cached under a fixed key - bump the suffix
  to force a refresh" — Firefox cache key `cross-browser-firefox-v1-<os>` never invalidates on its own.
  · covered-by: CI.S06 · [H09]
- **CI.N046** DRIFT · `.github/workflows/ci.yml:311-314, 338-339` — "mypy names only the main pass's" /
  "Mypy (src/, tests/, digital_twin/, tests_hardware/device_scripts/, and the whole host build chain)" —
  CI narrows the main pass to `src tests tests_hardware/device_scripts` while typecheck.sh:105-107 says
  CI passes `src tests`. · covered-by: CI.S03 · [H09]
- **CI.N047** WORKAROUND · `.github/workflows/ci.yml:325-335, 354-362, 380-388, 405-413, 437-447, 491-501`
  — "`actionlint-py` ships no wheel and fetches its binary inside its own build backend ... HTTP 500 on
  2026-09-13, 504 on 2026-09-14" — Six hand copies of the retried `uv sync` (plus the composite
  action's); CLAUDE.md forbids removing the unit-tests one. · covered-by: CI.S17 · [H09]
- **CI.N048** LIMIT · `.github/workflows/ci.yml:323-324, 352-353, 378-379, 403-404` — "run: pip install
  uv" — uv unpinned in every lint lane. · covered-by: CI.S04 · [H09]
- **CI.N049** SETTLED · `.github/workflows/ci.yml:341-343` — "scripts/ only: the legacy build-*.sh are
  out of scope forever (CLAUDE.md)" — shellcheck scope. · [H09]
- **CI.N050** SETTLED · `.github/workflows/ci.yml:392-394, 415` — "--offline skips the two API audits,
  so it behaves the same everywhere" — Two zizmor audits never run. · related: CI.T06 · [H09]
- **CI.N051** SETTLED · `.github/workflows/ci.yml:417-426` — "needs: lint-and-typecheck is sequencing
  only, the standing hang backstop; `if: !cancelled()` drops the success gating" — unit-tests runs even
  if lint fails (CLAUDE.md). · covered-by: CI.T01 · [H09]
- **CI.N052** ASSUME · `.github/workflows/ci.yml:423-424, 430` — "45 minutes: a ~17-minute warm run plus
  one hung file's full retry budget" — Timeout sized from a measured warm run. · related: CI.T01 · [H09]
- **CI.N053** LIMIT · `.github/workflows/ci.yml:451-469` — "Run unit tests at the shipped gc.threshold"
  — `unit-tests-gc-threshold` has no job-level retried sync of its own (relies on the composite
  action's). (low) · related: CI.S17 · [H09]
- **CI.N054** ASSUME · `.github/workflows/ci.yml:471-475` — "45 minutes over the measured 14m01s/16m56s
  instrumented reruns; a 30-minute cap once cancelled a passed suite" — Timeout from dated measurements.
  · [H09]
- **CI.N055** SETTLED · `.github/workflows/ci.yml:476-480` — "Success-gated on purpose (no `if: !cancelled()`,
  unlike unit-tests' own edge above)" — Coverage job gated on the plain suite passing. · covered-by:
  CI.T01 · [H09]
- **CI.N056** SETTLED · `.github/workflows/ci.yml:502-516` — "This step is NOT advisory: build-settrace
  is the only interpreter no other job runs. Exit 1 ... goes red; exit 3 ... stays advisory (Part
  E.5.3)" — Owner decision 2026-09-22. · related: CI.T11 · [H09]
- **CI.N057** SUPPRESS · `.github/workflows/ci.yml:517-556` — "continue-on-error: true" — Six
  report/upload steps (`always()`) advisory. · related: CI.T11 · [H09]
- **CI.N058** LIMIT · `.github/workflows/ci.yml:525-534, 535-542` — "needs a CODECOV_TOKEN repo secret
  ... once this repo is registered at codecov.io ... fail_ci_if_error keeps a missing/invalid token from
  ever failing the job" — Codecov uploads currently no-op (CLAUDE.md). · related: CI.T11 · [H09]
- **CI.N059** SETTLED · `.github/workflows/ci.yml:559-569` — "needs: unit-tests, success-gated on
  purpose: fail-fast is the intent" — digital-twin-e2e is the deliberate gated exception (CLAUDE.md). ·
  covered-by: CI.T01 · [H09]
- **CI.N060** LIMIT · `.github/workflows/ci.yml:577, 610` — "device: [wozi, dev, arzi, klkizi, grkizi,
  schlafzi]" — Hand-kept 6-device matrices (twice). · covered-by: CI.T07 · [H09]
- **CI.N061** SUPPRESS · `.github/workflows/ci.yml:586-593` — "if-no-files-found: ignore ...
  continue-on-error: true" — Twin log upload advisory. · related: CI.T15 · [H09]
- **CI.N062** SETTLED · `.github/workflows/ci.yml:595-602` — "needs: unit-tests for the toolchain cache
  only, so `if: !cancelled()`" — Firmware build runs even when unit-tests fails. · covered-by: CI.T01 ·
  [H09]
- **CI.N063** ASSUME · `.github/workflows/ci.yml:617-618` — "A cache miss fails on build_firmware.py's
  own \"no toolchain found\" rather than skipping the build." — Cold-cache failure mode documented as
  intended. · covered-by: CI.S09 · [H09]
- **CI.N064** PLATFORM · `.github/workflows/ci.yml:620-632` — "python3 - <<'PYEOF' ...
  st.ensure_apt_packages(" — Runs the installer module under the runner's bare `python3` (needs >= 3.11
  for tomllib); ARM GCC is the distro's (`ubuntu-latest` floats). · covered-by: SCR.T09 · [H09]
- **CI.N065** ASSUME · `.github/workflows/ci.yml:595-634` — "Builds a real firmware.uf2 per device
  (B.11)" — The job installs apt packages only; picotool (installed to `/usr/local` by `setup`) is not
  in the cached `~/pico-toolchain`. (low) · related: CI.T03 · [H09]

## pyproject.toml

- **CI.N066** PLATFORM · `pyproject.toml:8-11` — ">=3.11: scripts/typecheck.sh needs tomllib. At 3.10,
  `uv sync` once built a venv without it" — Host Python floor; the chroot recipe exists partly because
  of this. · related: SCR.T09 · [H09]
- **CI.N067** DRIFT · `pyproject.toml:18-24` — "PINNED, like every tool here ... \"pytest\",
  \"mpremote\"," — `pytest` and `mpremote` are unpinned despite the comment; hardware harness depends on
  mpremote behaviour and the skip gate on pytest output format. · covered-by: CI.S05 · [H09]
- **CI.N068** SETTLED · `pyproject.toml:18-20` — "select = [\"ALL\"] and a zero-findings gate turn an
  unpinned upgrade's new rule into a hard CI failure ... Bump deliberately" — Update obligation for mypy
  2.3.1 / ruff 0.16.6: bump deliberately and re-run lint.sh + typecheck.sh; after any `uv.lock` merge,
  verify installed versions (CLAUDE.md). · covered-by: CI.T04 · [H09]
- **CI.N069** ASSUME · `pyproject.toml:25-27` — "\"types-pyserial==3.5.0.20260712\"" — Stub pin; update
  obligation same as tools. · covered-by: CI.T04 · [H09]
- **CI.N070** LIMIT · `pyproject.toml:28-32` — "actionlint-py downloads its binary at install time, so a
  fully offline sync lacks it" — Offline `uv sync` cannot provide actionlint; root cause of the retried
  syncs. · covered-by: CI.T04 · [H09]
- **CI.N071** ASSUME · `pyproject.toml:33-35` — "\"zizmor==1.30.1\"" — Pinned; a bump may surface new
  default-on audits (zizmor.yml policy). · related: CI.T06 · [H09]
- **CI.N072** SETTLED · `pyproject.toml:38-40` — "The RPI_PICO_W MicroPython stubs are deliberately NOT
  a dependency group" — Load-bearing isolation (CLAUDE.md). · [H09]
- **CI.N073** SETTLED · `pyproject.toml:42-44` — "the legacy tree (python/, modules/) is never in scope"
  — Scope rule; device_scripts joined after a signature-change incident. · [H09]
- **CI.N074** SETTLED · `pyproject.toml:50-52` — "ruff format is never used - line breaks are
  hand-chosen (CLAUDE.md); 320 is ruff's own ceiling" — line-length 320 + E501 ignore. · [H09]
- **CI.N075** SUPPRESS · `pyproject.toml:58-60` — "allowed-confusables = [\"×\"]" — RUF003 allowance for
  bmp3xx oversampling labels. · [H09]
- **CI.N076** SUPPRESS · `pyproject.toml:63-64` — "\"E501\", # line length - not enforced" — Ignore:
  hand-chosen line breaks. · [H09]
- **CI.N077** SUPPRESS · `pyproject.toml:66-69` — "only the docstring-PRESENCE rules are off" — Ignore
  D100-D107 (one header block per module). · [H09]
- **CI.N078** SUPPRESS · `pyproject.toml:71-78` — "No `pathlib` in the rp2 port at all" / "No async file
  I/O either ... every real flash write is reachable only through the REST PUT path" — Ignore PTH,
  ASYNC230 (target impossibility; blocking flash writes accepted, Part F.3). · [H09]
- **CI.N079** SUPPRESS · `pyproject.toml:80-85` — "tests/ runs under the real MicroPython interpreter
  with microtest.py, not pytest" / "`print()` is the log transport" — Ignore PT, T20. · [H09]
- **CI.N080** SUPPRESS · `pyproject.toml:87-93` — "an Event would change the protocol" / "`global` is
  how tests/ keeps its per-process port and scratch counters" — Ignore ASYNC110 (neopixel yield
  handshake), PLW0603. · [H09]
- **CI.N081** SUPPRESS · `pyproject.toml:95-98` — "Part G.2 REQUIRES `except Exception` -> err_s() ->
  \"Failed\" around a caller-supplied callback" — Ignore BLE001 globally, including src/. · [H09]
- **CI.N082** SUPPRESS · `pyproject.toml:100-106` — "Cost without a defect caught, on a 264KB-SRAM
  target" — Ignore TRY003, EM101, EM102, SIM105 (contextlib not frozen). · [H09]
- **CI.N083** SUPPRESS · `pyproject.toml:108-114` — "PERF203: ... hoisting aborts the loop" / "S110
  wants a log call at sites that are deliberately silent" — Ignore PERF203, S110 (silent
  `try/except/pass` allowed globally). · [H09]
- **CI.N084** SUPPRESS · `pyproject.toml:131-137` — "`int — float` is load-bearing" / "typing.Self is
  gated behind 3.11" | Ignore PYI041, PYI034. · [H09]
- **CI.N085** SUPPRESS · `pyproject.toml:139-148` — "TRY301: an inner raise function is a closure
  allocation" / "SIM115: `with open(...)` would newly swallow an OSError" / "PLW1641 would make
  RunConfig hashable" — Ignore TRY301, SIM115, PLW1641. · [H09]
- **CI.N086** SUPPRESS · `pyproject.toml:155-158` — "FBT003's remaining calls are into C entry points
  that reject keywords" — Ignore FBT003; FBT001/002 stay on. · [H09]
- **CI.N087** SUPPRESS · `pyproject.toml:160-163` — "`x != x` is asy_scd30_driver.py's NaN test in its
  two setters" — Ignore PLR0124. · [H09]
- **CI.N088** SUPPRESS · `pyproject.toml:171-179` — "Identifiers deliberately mirror the datasheet /
  reference algorithm" — Ignore N801, N802, N803, N806, N811, N814. · [H09]
- **CI.N089** SUPPRESS · `pyproject.toml:181-184` — "D205/D209 each ADD a line to a header already at
  the cap" — Ignore D205, D209 (3-line cap). · [H09]
- **CI.N090** INVAR · `pyproject.toml:202-212` — "Ceilings sit at the measured maximum, so they gate
  regression without forcing a rewrite; ratchet DOWN only." — max-complexity 20, max-args 24,
  max-branches 20, max-statements 80, max-returns 12; ratchet-down by convention. · [H09]
- **CI.N091** DRIFT · `pyproject.toml:214-215` — "Per-file exemptions live HERE, centrally and with a
  reason, never as scattered `# noqa`" — Line-level `# noqa` exist in scripts/ (E402 x8, PLC0415),
  toolchain/ (PLR2004) and generated code (F401). (low) · [H09]
- **CI.N092** SUPPRESS · `pyproject.toml:360-362` — "Extends `silent` to the (upstream-Beta) stub
  package itself: its types are used, its own issues not reported." — Stub-package errors hidden. ·
  related: PLAT.T05 · [H09]
- **CI.N093** SUPPRESS · `pyproject.toml:403-406` — "no_implicit_reexport stays off here only ... which
  would need 175 inline ignores" — The one strict-flag exemption in the main pass; count dated. ·
  related: SCR.T15 · [H09]
- **CI.N094** LIMIT · `pyproject.toml:415-418` — "testpaths = [\"tests_scripts\"]" — No
  `--strict-markers`/`xfail_strict`; a misspelled wear-gate marker would be a silent no-op. ·
  covered-by: CI.S13 · [H09]

## .gitignore

- **CI.N095** DRIFT · `.gitignore:5-6` — "same \"dev-tooling only\" split as .venv/ above" — `.venv/` is
  at line 59, below. · covered-by: CI.S19 · [H09]
- **CI.N096** DRIFT · `.gitignore:22-25` — "Build output (see build-*.sh)" — Legacy-tree reference for
  `*.uf2`, which `scripts/build_firmware.py` now also writes under `build/`. (low) · [H09]
- **CI.N097** DRIFT · `.gitignore:33-41` — "confirmed directly against the pinned v1.28.0 source" /
  "scripts/test.sh's own \"src:tests:.frozen\" MICROPYPATH" — Pin is v1.29.0 and test.sh's MICROPYPATH
  is `build/generated_src:src:tests:frozen_modules:.frozen`. · covered-by: CI.S19 · [H09]
- **CI.N098** DRIFT · `.gitignore:27, 33, 75, 84` — "# digital_twin/run_wozi_integration.py's own
  persistent run state -" — Comment blocks over the 3-line cap; `:75` names the retired
  `run_wozi_integration.py`. · covered-by: CI.S10 · [H09]
- **CI.N099** RISK · `.gitignore:9-14` — "Vitest 5 moved these ... both are listed so a checkout still
  ignores whatever an older local install leaves behind" — Two attachment paths kept for version drift.
  (low) · [H09]

## tests_scripts/test_device_tomls.py

- **CI.N100** INVAR · `tests_scripts/test_device_tomls.py:271-282` — "A GitHub Actions matrix is a
  literal - no expression can glob devices/ at parse time" — Enforces both ci.yml `device: [...]`
  matrices equal DEVICE_NAMES via regex (expects exactly 2 one-line flow sequences; pyyaml deliberately
  not a dependency) · covered-by: CI.T07 · [H10]

## tests_scripts/test_js_coverage_excludes_json.py

- **CI.N101** WORKAROUND · `tests_scripts/test_js_coverage_excludes_json.py:1-3` — "a JSON file left in
  the coverage set throws a rolldown parse stack per run before being dropped anyway" — Pins
  vitest.config.js `coverage.exclude` globs covering every repo JSON, working around the v8 coverage
  provider re-parsing JSON as JS; removal trigger: none stated · [H10]
- **CI.N102** LIMIT · `tests_scripts/test_js_coverage_excludes_json.py:16-22,25-38` —
  "re.search(r\"exclude:\\s*\\[([^\\]]*)\\]\", text[block:])" — Reads vitest.config.js by regex (first
  `exclude: [...]` after `coverage: {`) and re-implements glob semantics by hand (low) · [H10]

## tests_scripts/test_js_coverage_report_dir.py

- **CI.N103** WORKAROUND · `tests_scripts/test_js_coverage_report_dir.py:1-3` — "its default name -
  `coverage` - is importable as a namespace package, shadowing the real `coverage` distribution and
  turning scripts/typecheck.sh red" — Report dir must not be named like any top-level module the repo
  imports; removal trigger: none stated · [H10]
- **CI.N104** MIRROR · `tests_scripts/test_js_coverage_report_dir.py:44-111 (agent cited tests_scripts/test_js_coverage_report_dir.py:101-111)`
  — "ci.yml gates the JS coverage upload on a directory vitest no longer writes" — vitest.config.js
  `reportsDirectory` ↔ ci.yml `hashFiles(...)`/`path:` ↔ .gitignore entry (enforced) · [H10]
  ⟨re-anchored: quote found at line 44⟩

## tests_scripts/test_test_sh.py

- **CI.N105** INVAR · `tests_scripts/test_test_sh.py:742-743` — "GitHub drops every error annotation
  past the tenth in a step" — Annotation ordering/cap behaviour depends on a GitHub limit · [H10]
- **CI.N106** INVAR · `tests_scripts/test_test_sh.py:791-839` — "while its whole run was
  continue-on-error a failure there was invisible. One really was." — --coverage exit codes 0/1/3 (test
  failure outranks renderer failure); ci.yml's unit-tests-coverage step must not be continue-on-error,
  tolerate exit 3, and six report steps use `always() &&` (enforced) · related: CI.T11 · [H10]

## package.json

- **CI.N107** SUPPRESS · `package.json:14,18` — "--exclude \"tests_js/live-backend-put-matrix.test.js\""
  — `test:unit` and `test:coverage` deselect the live PUT matrix (it runs only via
  `test`/`test:put-matrix`); coverage never includes it · related: CI.S12 · [H11]
- **CI.N108** ASSUME · `package.json:23-37` — "\"eslint\": \"^10.10.0\", ... \"typescript\": \"^7.0.2\",
  \"vitest\": \"^5.0.0\"" — every devDependency is a caret range; reproducibility rests on
  package-lock.json + `npm ci`, unlike pyproject's exact pins for tools with opt-in-to-everything
  configs · related: CI.T04 · [H11]
- **CI.N109** PLATFORM · `package.json:35` — "\"typescript\": \"^7.0.2\"" — TypeScript 7 (a major line);
  tests_js/vitest-commands.d.ts's module-vs-script augmentation behaviour was "confirmed directly"
  against some tsc version and must be re-checked on a TS bump (low) · related: CI.T04 · [H11]
- **CI.N110** LIMIT · `package.json:1-38` — (no `engines` field) — Node version is constrained only by
  .nvmrc; `@types/node ^26` disagrees with it (low) · covered-by: CI.S07 · [H11] ⟨quote not matched at
  the anchor⟩

## eslint.config.js

- **CI.N111** SETTLED · `eslint.config.js:10-12` — "the curated counterpart of ruff's select = [\"ALL\"]
  - every core rule that catches a real defect or enforces a decision, style-preference bans left out" —
  deliberate curated rule set, not ALL · [H11] ⟨quote not matched at the anchor⟩
- **CI.N112** INVAR · `eslint.config.js:113-118` — "complexity ceilings at the measured maximum, so they
  gate regression: ratchet DOWN only" — `complexity: 41`, `max-depth: 4`, `max-nested-callbacks: 4`,
  `max-classes-per-file: 2` are measured maxima; "ratchet down only" is a convention nothing enforces ·
  [H11]
- **CI.N113** SUPPRESS · `eslint.config.js:184-186` — "rules: { ...BUG_CATCHING_RULES, \"no-console\":
  \"off\" }," — `no-console` disabled for scripts/**/*.mjs (CLI output channel) · [H11]

## tsconfig.json

- **CI.N114** ASSUME · `tsconfig.json:11-13` — "All of these were verified to hold before being switched
  on" — undated verification claim for the beyond-strict flags · [H11]
- **CI.N115** DRIFT · `tsconfig.json:14-15` — "skipLibCheck stays TRUE deliberately: the only findings
  it hides are inside third-party .d.ts files this project does not own." — deliberate setting, but
  `skipLibCheck` skips every `.d.ts`, including the project's own tests_js/vitest-commands.d.ts that
  `include` names (:28), so the claim is broader than true (low) · [H11]
- **CI.N116** MIRROR · `tsconfig.json:10-26 vs tsconfig.node.json:16-32` —
  "\"noUncheckedIndexedAccess\": true, ... \"skipLibCheck\": true" — the strict flag set and its comment
  are duplicated verbatim across the two configs; kept in sync by hand · [H11]

## tsconfig.node.json

- **CI.N117** DRIFT · `tsconfig.node.json:2-6 vs :34` — "Second, separate tsc invocation for
  tests_js/_live_twin_command.js and tests_js/_live_matrix_command.js" — `include` also lists
  scripts/cross_browser_smoke.mjs, which the header does not mention (low) · [H11]
- **CI.N118** PLATFORM · `tsconfig.node.json:12` — "\"types\": [\"node\"]," — Node typings come from
  @types/node ^26 while .nvmrc pins Node 22 · covered-by: CI.S07 · [H11]

## vitest.config.js

- **CI.N119** WORKAROUND · `vitest.config.js:15-19` — "The dev sandbox pre-installs Chromium at this
  fixed path; CI runners lack it" — uses /opt/pw-browsers/chromium when present instead of the
  lock-pinned Playwright build; removal trigger: none stated · covered-by: CI.S15 · [H11]
- **CI.N120** WORKAROUND · `vitest.config.js:33-36` — "A `coverage/` directory at the repo root is
  importable as a namespace package and shadows the real `coverage` distribution" — coverage output
  renamed to htmlcov_js to avoid shadowing Python's `coverage` in scripts/_render_coverage.py; removal
  trigger: none stated · [H11]
- **CI.N121** WORKAROUND · `vitest.config.js:37-40` — "The v8 provider re-parses every file V8 reported
  coverage for as JavaScript, so the JSON ... threw a rolldown parse stack per file" — `exclude: ["**/*.json"]`
  works around v8/rolldown parse noise; guarded by tests_scripts/test_js_coverage_excludes_json.py;
  removal trigger: none stated · [H11]
- **CI.N122** LIMIT · `vitest.config.js:32-41` — "coverage: {" — no coverage thresholds; JS coverage is
  advisory · related: CI.S12 · [H11]

## .nvmrc

- **CI.N123** PLATFORM · `.nvmrc:1` — "22" — major-only Node pin; the exact 22.x installed floats
  (CLAUDE.md records v22.23.2 on 2026-09-12) · related: CI.S07 · [H11]

## tests_js/vitest-commands.d.ts

- **CI.N124** PLATFORM · `tests_js/vitest-commands.d.ts:19-24` — "without at least one top-level
  import/export of its own, TS treats this file as an ambient *script* ... (confirmed directly ...)" —
  relies on tsc's module-vs-script augmentation semantics; re-check on a TypeScript major bump · [H11]

## tests_js/live-backend-put-matrix.test.js

- **CI.N125** ASSUME · `tests_js/live-backend-put-matrix.test.js:55-56` — "this one file is 567s of the
  web tier's 578s" — single dated measurement (SPECIFICATION.md:880-881, 2026-09-19) · [H11] ⟨quote not
  matched at the anchor⟩

## SPECIFICATION.md Part A.3 (Refactor status, 129-146)

- **CI.N126** DRIFT · `SPECIFICATION.md:131-133` — "ruff, mypy, shellcheck, actionlint and zizmor each
  as their own stage, plus unit-tests, digital-twin-e2e and a real `firmware.uf2` build" — Stage list
  omits unit-tests-gc-threshold, unit-tests-coverage and the web tier (B.10 lists 15 jobs). (low) ·
  [H12]

## SPECIFICATION.md Part B.10 / B.10.1 (CI perspective, 828-929)

- **CI.N127** ASSUME · `SPECIFICATION.md:830-831` — "`.github/workflows/ci.yml` runs fifteen jobs
  (fourteen of them real work plus `web-changes`" — Job count (matches ci.yml today: 15); goes stale on
  any job change. · covered-by: DOC.T08 · [H12]
- **CI.N128** ASSUME · `SPECIFICATION.md:837-839` — "567s of the suite's 578s, measured 2026-09-19" —
  Dated web-tier wall-clock figure (repeated :881 with "243 of 778 tests"). · [H12]
- **CI.N129** INVAR · `SPECIFICATION.md:841-845` — "Cache key hashes both `versions.toml` and
  `setup_toolchain.py`" — Key omits `micropython_overrides.py`, whose override is compiled into the
  cached binary. · covered-by: CI.S01 · [H12]
- **CI.N130** SETTLED · `SPECIFICATION.md:846-853` — "`uv sync` is retried three times in every job that
  syncs ... CLAUDE.md says not to simplify that one away" — Protected retry; outages observed
  2026-09-13/14/21. · covered-by: CI.S17 · [H12]
- **CI.N131** ASSUME · `SPECIFICATION.md:857-860` — "Measured on run `34755468619` (2026-09-13): the
  plain suite reported `60/60 files passed` ... ran 13m24s longer, and the 30-minute cap cancelled the
  job" — Dated run evidence; file count now ~87. · [H12]
- **CI.N132** SETTLED · `SPECIFICATION.md:867-868` — "Permissions deny by default (`permissions: {}`,
  then `contents: read` per job) ... zizmor enforces it." — Enforced by zizmor. · covered-by: CI.T06 ·
  [H12]
- **CI.N133** INVAR · `SPECIFICATION.md:869-875` — "It passes `base: ${{ github.ref }}` ... Python jobs
  never consult it." — Path-filter design; cancellation interaction open. · covered-by: CI.S11 · [H12]
- **CI.N134** ASSUME · `SPECIFICATION.md:880-885` — "567 s of the suite's 578 s, 243 of 778 tests
  (2026-09-19) ... `tests_js/mock-server-put-matrix.test.js` proves the partition" — Dated counts; shard
  partition claimed proven by a test. · [H12]
- **CI.N135** INVAR · `SPECIFICATION.md:894-896` — "Firefox/geckodriver come from conda-forge via
  micromamba (~106 MB, no version file to key on), cached under a fixed key whose suffix is bumped to
  force a refresh" — Manual cache-key bump; unpinned browser. · covered-by: CI.S06 · [H12]
- **CI.N136** SETTLED · `SPECIFICATION.md:902-903` — "shellcheck covers `scripts/` only: the legacy
  `build-*.sh` are out of scope forever (CLAUDE.md), 28 findings included" — Legacy lint gap by
  decision; "28" is a dated count. · [H12]
- **CI.N137** ASSUME · `SPECIFICATION.md:908-909` — "Cold-cache runs measured 16m58s and 16m42s
  including the toolchain build." — Dated timing basis for `timeout-minutes: 45`. · [H12]
- **CI.N138** SUPPRESS · `SPECIFICATION.md:914-917` — "report steps (`always() && hashFiles(...)`,
  `continue-on-error`) do not (E.5.3); the Codecov upload needs the repo registered and a
  `CODECOV_TOKEN`, and `fail_ci_if_error` stays off" — Advisory coverage report; Codecov upload
  currently a no-op. · related: CI.T11 · [H12]
- **CI.N139** TODO · `SPECIFICATION.md:916-917` — "the Codecov upload needs the repo registered and a
  `CODECOV_TOKEN`" — Registration/token not done (CLAUDE.md: "hasn't happened yet"). · [H12]
- **CI.N140** SETTLED · `SPECIFICATION.md:920-922` — "A six-device matrix, `fail-fast: false` ...
  `needs: unit-tests` and stays success-gated: fail-fast is its stated intent." — digital-twin-e2e is
  the deliberate gated exception. · covered-by: CI.T01 · [H12]
- **CI.N141** INVAR · `SPECIFICATION.md:924-929` — "`needs: unit-tests` for the toolchain cache only, so
  `if: !cancelled()` ... A cache miss fails on `build_firmware.py`'s own \"no toolchain found\"" —
  Cold-cache failure mode accepted. · covered-by: CI.S09 · [H12]

## SPECIFICATION.md Part D (src/ Production-Quality Checklist, 2576-2728)

- **CI.N142** MIRROR · `SPECIFICATION.md:2709-2710` — "Extend the lint/typecheck config's scope and CI's
  explicit path arguments to the new location." — lint scope ↔ CI explicit paths hand-mirrored. ·
  related: CI.S03 · [H12]

## SPECIFICATION.md Part E.5 / E.5.1-E.5.3 (Coverage, 2951-3088)

- **CI.N143** SETTLED · `SPECIFICATION.md:2957-2958` — "No threshold enforced anywhere — CI reports
  numbers, never gates." — Coverage never gates. · [H12]
- **CI.N144** TODO · `SPECIFICATION.md:2965-2966` — "`coverage.xml` uploads to Codecov, but that
  account-linking hasn't been done, so it currently no-ops silently" — Pending registration. · [H12]

## SPECIFICATION.md Part H.7 — Cross-browser coverage

- **CI.N145** INVAR · `SPECIFICATION.md:4678-4679` — "CI always installs all three (a skip there is the
  bug to chase)" — CI must never skip a browser engine. · related: CI.S06 · [H13]
- **CI.N146** WORKAROUND · `SPECIFICATION.md:4687-4692` — "Ubuntu's `firefox` package is a snap-only
  stub ... conda-forge, reached through a standalone `micromamba` binary" — Workaround for distro
  packaging and network policy; removal trigger none stated. · related: CI.S06 · [H13]
- **CI.N147** SETTLED · `SPECIFICATION.md:4692-4694` — "That install is deliberately **unpinned** ...
  whatever conda-forge publishes today is acceptable" — Deliberate unpinned supply-chain input (Firefox,
  geckodriver, micromamba). · covered-by: CI.S06 · [H13]

## SPECIFICATION.md Part H.8 — Web CI / tooling stack

- **CI.N148** SETTLED · `SPECIFICATION.md:4705` — "**`@vitest/coverage-v8`** (report-only, no threshold"
  — JS coverage never gates. · related: CI.T11, CI.S12 · [H13]
- **CI.N149** WORKAROUND · `SPECIFICATION.md:4705-4710` — "writing to `htmlcov_js/` rather than its
  default `coverage/`, which Python imports as a namespace package ... `exclude: [\"**/*.json\"]`
  because the provider re-parses every file V8 reported as JavaScript" — Two tool-interaction
  workarounds; the JSON exclusion is pinned by `tests_scripts/test_js_coverage_excludes_json.py`;
  removal trigger none stated. · [H13]
- **CI.N150** SETTLED · `SPECIFICATION.md:4713-4718` — "**ESLint's rule set is curated, not
  `eslint:all`** ... pure style-preference bans (`no-bitwise`, `no-plusplus`, ...) left out" —
  Deliberate lint-scope decision (contrast ruff `select = ["ALL"]`). · [H13]
- **CI.N151** INVAR · `SPECIFICATION.md:4722-4724` — "Complexity ceilings (`complexity` 41, `max-depth`
  4, `max-nested-callbacks` 4) sit at the measured maximum ... and only ever ratchet down" —
  Ratchet-down rule is convention; values are dated measurements (mock-server dispatcher 41,
  `validateDefinitions` 37). · [H13]
- **CI.N152** SETTLED · `SPECIFICATION.md:4729-4731` — "`dorny/paths-filter` gate job ... deliberately
  not a second workflow file with its own trigger-level filter" — CI structure decision. · related:
  CI.T02, CI.S11 · [H13]
- **CI.N153** SETTLED · `SPECIFICATION.md:4738-4748` — "The workflow triggers on `push` to every branch
  as well as on `pull_request`, and that is not redundancy." — Do-not-narrow marker, born of the
  2026-09-18 "128 commits went unverified" incident. · related: CI.T09 · [H13]
- **CI.N154** INVAR · `SPECIFICATION.md:4748-4749` — "**When judging whether a branch is green, check
  that CI actually ran on its head commit**, not just that nothing is red." — Review-only practice rule.
  · related: CI.T09 · [H13]

## SPECIFICATION.md Part K.2 — Driver to the Part C/D bar

- **CI.N155** INVAR · `SPECIFICATION.md:5724-5729` — "Ruff's `FBT001`/`FBT002` ... reject a `bool`-typed
  parameter that isn't keyword-only" — Enforced by lint (`select = ["ALL"]`). · [H13]

## SPECIFICATION.md Part L.5 — Build/generator script quality bar

- **CI.N156** INVAR · `SPECIFICATION.md:6416-6417` — "Newly-built generator/validator modules join
  `pyproject.toml`'s ruff/mypy scope ... from day one" — Scope rule. · related: CI.T05 · [H13]

## CLAUDE.md

- **CI.N157** INVAR · `CLAUDE.md:468-477` — "Every tool is a `[dependency-groups] dev` entry ... All are
  **pinned**" — pytest and mpremote are unpinned (pyproject.toml:23-24), against the "PINNED, like every
  tool here" comment at :18. · covered-by: CI.S05 · [H14]
- **CI.N158** SETTLED · `CLAUDE.md:478-490` — "Its coverage number is advisory but its test result is
  not — owner decision, 2026-09-22" — Matches ci.yml:476-516, where exit 3 means rendering failed and is
  tolerated. · related: CI.T11 · [H14]
- **CI.N159** SUPPRESS · `CLAUDE.md:488-490 (ci.yml:518-556)` — "a failure unique to that binary was
  invisible while the whole job was `continue-on-error`" — The job's report and upload steps are still
  `continue-on-error: true` (ci.yml:520, 524, 534, 542, 549, 556). · related: CI.T11, CI.S12 · [H14]
- **CI.N160** WORKAROUND · `CLAUDE.md:496-499` — "`self-repository` is deliberately `disable: true` ...
  actionlint 1.7.12 rejects that as invalid" — The zizmor audit is disabled (.github/zizmor.yml:14-18).
  Removal trigger: "revisit when actionlint learns it". · related: DOC.T14 · [H14]
- **CI.N161** DRIFT · `CLAUDE.md:493-494` — "only `unpinned-uses` is configured — ... every other audit
  runs at its default" — `self-repository` is configured too, as disabled (zizmor.yml:14-18).
  zizmor.yml:1-3 repeats the "Only unpinned-uses is configured" claim (low). · [H14]
- **CI.N162** LIMIT · `CLAUDE.md:495` — "Always invoked `--offline`, which skips the two audits needing
  the GitHub API" — Two zizmor audits never run anywhere (scripts/lint.sh:26). · related: CI.T06 · [H14]
- **CI.N163** INVAR · `CLAUDE.md:499-500` — "Adding a SHA-pinned third-party action means bumping that
  SHA by hand — no Dependabot is configured." — No .github/dependabot.yml; convention. · covered-by:
  CI.T06 · [H14]
- **CI.N164** TODO · `CLAUDE.md:584-586` — "needs this repo registered at codecov.io plus a token/OIDC
  setup that hasn't happened yet, so that upload currently no-ops" — Codecov upload is a silent no-op
  (ci.yml:525-535). · [H14]
- **CI.N165** SETTLED · `CLAUDE.md:588-600` — "Don't \"simplify\" the retry away" — 3-attempt `uv sync`
  before test.sh (ci.yml:442-447). The same loop exists in lint lanes (:330, 357, 383, 408), in coverage
  (:496) and in the composite action. · covered-by: CI.S17 (CI.T12) · [H14]
- **CI.N166** WORKAROUND · `CLAUDE.md:591-593` — "`actionlint-py` ships no wheel and downloads its
  binary from a release URL inside its own build backend" — Third-party packaging defect, absorbed by
  the retry. Removal trigger: none stated. · related: CI.T04 · [H14]
- **CI.N167** SETTLED · `CLAUDE.md:604-612` — "The `needs:` edge is for SEQUENCING only ... Keep the
  sequencing; never restore the gating." — Matches ci.yml:425-426, 456-457, 604-605. · covered-by:
  CI.T01 · [H14]
- **CI.N168** DRIFT · `CLAUDE.md:604-612` — "`unit-tests` and `firmware-build-verify` carry `if: ${{ !cancelled() }}`
  ... `digital-twin-e2e` is the deliberate exception" — Incomplete. `unit-tests-gc-threshold` also
  carries `!cancelled()` (ci.yml:456-457), and `unit-tests-coverage` is a second deliberately
  success-gated job (ci.yml:477-480) (low). · related: CI.T01 · [H14]
- **CI.N169** SETTLED · `CLAUDE.md:732-738` — "`ruff format` is deliberately not used anywhere" —
  `line-length = 320` and E501 ignored (pyproject.toml:52, 64). Side effect: one-line essays evade the
  comment cap. · related: TEST.S22 · [H14]
- **CI.N170** SETTLED · `CLAUDE.md:739-741` — "Bare `except:` (E722) is intentionally left enabled ...
  flag existing bare excepts as a tracked to-do" — No bare `except:` remains in the eight scopes, so the
  "tracked to-do" framing is stale (low). · [H14]
- **CI.N171** INVAR · `CLAUDE.md:742-751` — "always PEP 604 `X \| Y` ... This is already
  machine-enforced: ruff's `UP007` rule" — Enforced by ruff UP007 (select ALL); no `Union[` in scope. ·
  [H14]
- **CI.N172** SUPPRESS · `CLAUDE.md:755-763` — "The one exemption is `no_implicit_reexport`, and only in
  the `[tool.mypy]` pass" — pyproject.toml:403-406. The other two passes enforce it
  (digital_twin/typecheck.ini:24-25, host_typecheck.ini:31-33). · related: SCR.T15 · [H14]
- **CI.N173** ASSUME · `CLAUDE.md:761-762` — "enforcing the flag would mean 175 inline ignores in
  `tests/`" — Hypothetical count, undated. · [H14]
- **CI.N174** SUPPRESS · `CLAUDE.md:764-769` — "`disallow_untyped_decorators` is off for
  `tests/test_setter_microdot_integration.py`" — pyproject.toml:408-413. Removal trigger: "Revisit if
  Microdot ships hints". · related: SCR.T15 · [H14]
- **CI.N175** INVAR · `CLAUDE.md:788-790` — "A merge resolved by taking one side wholesale hides
  test/source mismatches — run every tier after it." — Convention only. · [H14]
- **CI.N176** INVAR · `CLAUDE.md:791-804` — "After any merge that touches `uv.lock`, run `uv sync` and
  check the installed `ruff --version`/`mypy --version`" — Convention only. CI runs `uv sync` without
  `--locked`. · related: CI.S04, CI.T04 · [H14]
- **CI.N177** LIMIT · `CLAUDE.md:795-798` — "`uv lock --check` compares `pyproject.toml` against the
  lock's *manifest* section only" — Tool limitation: a self-contradictory lock passes. · related: CI.T04
  · [H14]
- **CI.N178** ASSUME · `CLAUDE.md:1016-1018` — "confirmed: `lint.sh` and all three `typecheck.sh` passes
  report zero findings as of the eight-scope extension" — Dated claim (low). · [H14]
- **CI.N179** INVAR · `CLAUDE.md:1047-1050` — "Always create a pull request with a meaningful
  description ... Automatically subscribe to the pull request's activity" — Convention only. · [H14]

## README.md

- **CI.N180** LIMIT · `README.md:217` — "the real browser Vitest drives - `npm test` cannot start
  without it" — Vitest prefers a sandbox Chromium over the lock-pinned build. · related: CI.S15 · [H14]
- **CI.N181** LIMIT · `README.md:245-248` — "gated by a `dorny/paths-filter` job so they only run when
  this push changed `html/`, `js/`, `tests_js/`, or their own tooling configs" — The filter omits src/,
  buildgen/, devices/, digital_twin/ and toolchain/, which the live twin tests depend on. · covered-by:
  CI.S02 · [H14]

## BACKLOG.md

- **CI.N182** TODO · `BACKLOG.md:56-71` — "Deferred to a dedicated future session (project owner,
  2026-09-11) - not to be picked up as part of unrelated work." — Unnumbered "Mypy shall disallow Any"
  (owner-specified): `disallow_any_explicit` is off in all three configs; needs a typing strategy for
  test wrappers and a decision on variadic/opaque `src/` uses. Status: deferred. · related: ENV.T06 ·
  [H15]
- **CI.N183** TODO · `BACKLOG.md:559-570` — "should still confirm it whenever one is next convenient" —
  Session 7's `max-args` 21→22 got only the noble leg; trixie blocked by egress. Whether the 2026-09-12
  trixie leg already covers it is unstated; `max-args` is now 24 (`pyproject.toml:209`). (low) · [H15]
- **CI.N184** SETTLED · `BACKLOG.md:689-726` — "Additional checker candidates, measured and mostly
  declined." — zizmor adopted; import-linter (flat `src/`, false green), vulture,
  gitleaks/detect-secrets, codespell, markdownlint, yamllint, hadolint, taplo, pip-audit/npm audit
  rejected with reasons. · related: DOC.T14 · [H15]
- **CI.N185** SUPPRESS · `BACKLOG.md:696-699` — "One audit is disabled with cause: self-repository ...
  Revisit when actionlint learns it." — zizmor `self-repository` disabled (actionlint 1.7.12 rejects the
  syntax). Removal trigger stated. · related: DOC.T14 · [H15]
- **CI.N186** DRIFT · `BACKLOG.md:719-720` — "Ruff's S105/S106 are live everywhere except the three
  known, individually-exempted sites" — More files are exempted than three. · covered-by: CI.S08 · [H15]
- **CI.N187** TODO · `BACKLOG.md:468` — "pyproject.toml (+159)" — · [H15]
- **CI.N188** TODO · `BACKLOG.md:468-470` — "package.json/vitest.config.js/eslint.config.js
  (2026-09-19's PUT-matrix split" — · [H15]
- **CI.N189** TODO · `BACKLOG.md:499-501` — "the tests/_coverage_runner.py = ['S102'] per-file-ignore is
  gone" — Suppression now inline at the one `exec()`. · [H15] ⟨quote not matched at the anchor⟩
- **CI.N190** TODO · `BACKLOG.md:524-525` — "pyproject.toml's max-args 24 (backlog=, chunk_bytes=) and
  the S603 per-file ignore for toolchain/micropython_overrides.py" — Lint config only (an added
  suppression). · [H15]
- **CI.N191** TODO · `BACKLOG.md:532-534` — "comments only: ... no setting, pin or step changed" —
  2026-09-24 comment-cap cut in `pyproject.toml`, `versions.toml`, `typecheck.sh`, `ci.yml`, composite
  action. · [H15]

## THIRD_PARTY_LICENSES.md (205 lines; owning area LIC). `arduino/` not read.

- **CI.N192** DRIFT · `pyproject.toml:192-194 vs src/*.py SPDX headers` — "CPY001: no file carries a
  copyright notice by design" — Ten `src/` files carry SPDX-FileCopyrightText notices. (low) · related:
  LIC.T08 · [H15]

## Commit messages (chronological)

- **CI.N193** TODO · `commit b743df8` — "the shape needed for it to later become a standalone CI step
  once this project has a CI pipeline" — Offline `setup_toolchain.py test` intended as a future CI step.
  · status: check whether any ci.yml job runs `setup_toolchain.py test` (low) | - · [H17]
- **CI.N194** TODO · `commit 2308fcc` — "Codecov (needs repo registration/token that hasn't been done
  yet, so it currently no-ops)" — Codecov upload no-ops. · tracked: CLAUDE.md "Code quality tooling"
  (still "currently no-ops") | related: CI.T* · [H17]
- **CI.N195** TODO · `commit c55f012` — "Owner decision to configure mypy against accepting Any types" —
  disallow_any_explicit deferred. · tracked: BACKLOG "Mypy shall be configured to disallow Any" |
  related: CI.T* · [H17]
- **CI.N196** WORKAROUND · `commit 1b37826 / 9cf1b0f / f4ec8e5 → 6d3a5e3` — "The per-file timeout/retry,
  stdbuf, and job-sequencing changes never stopped the hang - confirmed by reverting all three" —
  Mitigations kept as standing backstop though disproven as the fix. · tracked: CLAUDE.md "Standing
  backstop: hanging tests are never allowed" | related: CI.T* · [H17]
- **CI.N197** WORKAROUND · `commit 7079757` — "The capability is granted fresh on every invocation ...
  because GNU tar - what actions/cache's restore step uses - doesn't preserve the xattr" —
  CAP_NET_BIND_SERVICE setcap per run for port-53 test; depends on libcap2-bin and sudo. · tracked:
  CLAUDE.md chroot recipe (libcap2-bin note) | related: CI.T* · [H17]
- **CI.N198** SUPPRESS · `commit 454f6a2` — "Per-file exemptions live centrally in
  [tool.ruff.lint.per-file-ignores], never as inline noqa comments." — Stated rule (still at
  pyproject.toml:214-215) vs reality: 2 inline `# noqa: B905` in src/ (asy_wifi_service.py:709,
  asy_webserver_service.py:778) and 74 inline `# noqa` across
  tests/digital_twin/scripts/buildgen/toolchain/tests_scripts/tests_hardware; BACKLOG 2026-09-22 also
  moved S102 from per-file to inline deliberately. · status: UNTRACKED as a doc/practice contradiction
  (low) | related: CI.T* (plan line 2376 "E402 noqa split") · [H17]
- **CI.N199** SUPPRESS · `commit 454f6a2 / 770cf13 / 8428517` — "Rules excluded because the only
  available \"fix\" would change runtime behavior or cannot run on the MicroPython target ... (PERF203,
  S110, PYI024, PTH, ASYNC230, ASYNC110, BLE001, PLW0603 ...) ... PYI041 ... FBT003 ignored globally" —
  Global ruff ignore list with reasons; complexity ceilings pinned at measured maxima. · tracked:
  pyproject.toml [tool.ruff.lint] ignore (lines ~90-158) | related: CI.T* · [H17]
- **CI.N200** SUPPRESS · `commit 1ffc1fb` — "The 16 ANN401 and 56 ARG findings that remain are scoped
  centrally in per-file-ignores, in four evidence-backed categories" — Any/unused-arg exemptions:
  heterogeneous **kwargs into print(), asyncio.start_server() single-Stream seam, the three-file `_wlan`
  family (Any bridges board stub to tests/network.py), test doubles matching real signatures. · tracked:
  pyproject.toml per-file-ignores | related: CI.T* · [H17]
- **CI.N201** SUPPRESS · `commit bfaf4c6` — "self-repository (6): audit disabled with cause ... Revisit
  when actionlint learns the syntax" — zizmor audit disabled; actions/* tag-pinned by policy; removal
  trigger stated (actionlint support). · tracked: CLAUDE.md, BACKLOG checker list, .github/zizmor.yml |
  related: CI.T* · [H17]
- **CI.N202** SETTLED · `commit c225b04` — "The two remaining `# noqa: E402` in build_firmware.py are
  deliberately left inline: they are line-scoped ... a per-file entry would disable E402 for the whole
  file" — Inline-noqa exception rationale (partially reconciles the pyproject "never scattered noqa"
  statement). · status: see DRIFT item above | - · [H17]
- **CI.N203** WORKAROUND · `commit 90e8c17` — "scripts/typecheck.sh now repairs both at install time
  rather than encoding a stub defect into src/ as type: ignore ... Both repairs are conditional on the
  defect still being present, so they no-op once upstream re-ships" — micropython-stdlib-stubs
  1.29.0.post1/.post2 defects repaired at install; removal trigger = upstream fix (self-disabling). ·
  tracked: CLAUDE.md "scripts/typecheck.sh repairs two verified defects" | related: CI.T* · [H17 (also
  H17)]
- **CI.N204** SUPPRESS · `commit 3402e95` — "no_implicit_reexport - 175 findings, not adopted ... Off in
  the [tool.mypy] pass only" — mypy strict minus one flag; disallow_untyped_decorators overridden for
  test_setter_microdot_integration.py. · tracked: CLAUDE.md "mypy runs full --strict, minus exactly one
  flag" | - · [H17]
- **CI.N205** INVAR · `commit 0648df8` — "Shipped src/ code has no business reassigning a method ...
  scripts/lint.sh enforces it directly" — src/ never suppresses method-assign; ~157 inline test
  suppressions kept. · tracked: CLAUDE.md; scripts/lint.sh grep guard | - · [H17]
- **CI.N206** NOTE(DEFERRED) · `commit 390c14d` — Session 6 deferred "the 6-device twin CI matrix" and
  whitebox test parameterisation — Twin e2e ran wozi/dev only. · status: done (ci.yml digital-twin-e2e
  `matrix.device: [wozi, dev, arzi, klkizi, grkizi, schlafzi]`) | related: CI.T* · [H17]
- **CI.N207** NOTE(RATCHET) · `commit 8e70914` — "ratchets asy_webserver_service.py's constructor
  max-args from 21 to 22" — Lint threshold raised for one class. · tracked: pyproject.toml | - · [H17]
- **CI.N208** NOTE(DIAG) · `commit 279740c` — "Diagnostic-only, kept permanently" (print soak log on Run
  11 failure; artifact download blocked by egress) — Permanent CI diagnostic. · status: done | - · [H17]
- **CI.N209** NOTE(CALIBRATION) · `commit 846c78b` — "Also keeps a defense-in-depth retry (one
  independent fresh boot) on the trend check specifically" — Retry on a noisy check. · tracked:
  scripts/_digital_twin_ci_suite.py (by design) | - · [H17]
