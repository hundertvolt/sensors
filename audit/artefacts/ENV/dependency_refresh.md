# Dependency refresh (U0 step (6), M.PROC.008-.013), 2026-10-06

Branch `audit/u0-refresh` (worktree), one family per commit; each commit's gate (M.PROC.009) runs against the B0
column of `baseline.md` before it merges into the audit branch. Newest versions found 2026-10-06 with: `curl
https://pypi.org/pypi/<pkg>/json`, `npm view <pkg> version` / `npm outdated`, `https://nodejs.org/dist/index.json`,
`git ls-remote --tags <repo>`.

## Inventory (D1-D28)

| D | dependency | before | newest stable | decision | commit |
|---|---|---|---|---|---|
| D1 | MicroPython | `v1.29.0` | `v1.29.0` | already newest | — |
| D2-D11 | pico-sdk, mbedtls, picotool, lwIP, cyw43-driver, mbedtls, tinyusb, btstack, micropython-lib, berkeley-db | D1's submodules (pico-sdk 98a542c 2.3.0, lwIP 77dcd25, cyw43 055d642, micropython-lib ee4bb8f) | follow D1 | unchanged with D1; picotool floats to the newest 2.3.x patch at each `setup` | — |
| D12 | apt build tools | distro | distro | unpinned by decision; this session's `setup` installed them from the host archive | — |
| D13 | Microdot | `v2.6.2` | `v2.7.0` | moved; upstream type stubs vendored alongside | family (d) |
| D14 | freezefs | upstream `main` synced 2026-09-10 | `main` at `26be9e3` | already newest: all five vendored files byte-identical to `26be9e3` | — |
| D15 | MicroPython stubs | `1.29.0.post1` (rp2), stdlib `.post2` | same | already newest; both stub defects still ship (W08, W09) | — |
| D16 | Python dev tools | mypy 2.3.1, ruff 0.16.6, actionlint-py 1.7.12.24 (pytest 9.1.1, mpremote 1.29.0, types-pyserial, shellcheck-py, zizmor at newest) | mypy 2.4.0, ruff 0.16.10, actionlint-py 1.7.12.25 | moved | family (a) |
| D17 | Python transitive set | `uv.lock` | `uv lock --upgrade`: ast-serialize 0.12.1, librt 0.16.0, platformdirs 4.12.3 | moved | family (a) |
| D18 | uv | local 0.8.17; CI floats | 0.12.23 | recorded; local install moves with the gate (A.U28.02 pins it later) | — |
| D19 | coverage (renderer) | floats | 7.16.2 | recorded (A.U24.72/A.U28.02 pin it) | — |
| D20 | host Python | `>=3.11` | — | not applicable (host interpreter) | — |
| D21 | Node | `.nvmrc` 22 | 24 (Active LTS "Krypton", 24.21.0; 26 is Current, not LTS) | moved | family (b) |
| D22 | npm packages | lock of 2026-09 | every direct package at its newest; `@types/node` 24.19.1 (follows the Node major); `@eslint-community/eslint-plugin-eslint-comments` 4.8.1 added | moved; lock regenerated from scratch (the old lock's vitest 5.0.0 peers blocked 5.0.3) | family (b) |
| D23 | Playwright Chromium | playwright 1.63.0 | 1.63.0 | already newest | — |
| D24 | cross-browser engines | unpinned by decision | — | not applicable | — |
| D25 | first-party Actions | checkout v7, setup-node v5, cache v6, upload-artifact v7 | checkout v7, setup-node v7, cache v6, upload-artifact v7 | setup-node moved (5 sites) | family (c) |
| D26 | third-party Actions | paths-filter `15192bc` (v3 tag object) | v4.0.3, peeled commit `ceb8a2b` | moved (pulled-forward pin to a commit) | family (c) |
| D27 | runner image | `ubuntu-latest` | — | recorded from the gate's CI run | — |
| D28 | derived-code upstreams | derivation points | — | read in family (g) | — |

## Per-family notes

- (a) mypy 2.4: the native parser is now the default; no `for`/`with` type comment exists in the tree, and no flag
  joined `--strict`. ruff 0.16.7-0.16.10: no rule stabilised. lint.sh 0, the three typecheck passes 0 (167/48/131
  files). Lock merge check: every pinned tool's installed version equals its pin; every dev specifier equals its
  resolved version.
- (a) chroot (M.PROC.009): noble leg run on `b3a9f67` (debootstrap minbase from `archive.ubuntu.com`, GCC 13.3.0): `uv sync`, `lint.sh` 0, `typecheck.sh` 0. `scripts/test.sh` as the recipe writes it fails 10 `tests_scripts/` tests (`test_live_twin_ceiling_parser.py`: `node` is not on `PATH`; the recipe installs no Node — parked for U36); after `setup_toolchain.py env --tier generic` (Node v22.23.3 from nodejs.org) it passes: 87/87 files, pytest 2135 passed / 7 skipped. `env --tier generic`'s Playwright step could not reach `cdn.playwright.dev` (egress 403, also `playwright.download.prss.microsoft.com`), so Chrome for Testing 153.0.8010.12 (`chrome-linux64.zip`, `chrome-headless-shell-linux64.zip`) came from `storage.googleapis.com/chrome-for-testing-public` and FFmpeg 1011 from the host image's own Playwright install (`/opt/pw-browsers/ffmpeg-1011`), both served through `PLAYWRIGHT_DOWNLOAD_HOST`; then `npx playwright install-deps chromium` (skipped by `env` after the failed download) and `npm test` in its own namespace: 12/12 files, 817/817. The trixie leg is unreachable (`deb.debian.org` 403): owed in BACKLOG's chroot list.
- (b) ESLint 10.11-10.12 add no core rule. `npm audit`: the old lock's brace-expansion and fast-uri advisories are gone;
  the remaining `braces <=3.0.3` chain (via stylelint's fast-glob/micromatch) has no fixed release (3.0.3 is the newest)
  and reaches only Stylelint's matching of this repo's own CSS globs, a dev-only CI path: recorded, not fixable here.
  npm lint, typecheck, lint:html, lint:css pass under Node 24.21.0.
- (c) setup-node v7: inputs used here unchanged; automatic npm caching stays off (no `packageManager` in
  `package.json`). paths-filter v3.0.4..v4.0.3: `getChangedFilesFromGit()` (push with a branch `base`) and the PR API
  path keep v3's semantics; v4 adds a safe-directory wrapper around git and merge-queue support. The CI filter's
  reasoning (SPEC B.10.1) is unaffected.
- (d) Microdot v2.6.2..v2.7.0: f-strings (compiled by `mpy-cross`, which enables `MICROPY_PY_FSTRINGS`; the Unix port
  runs them), a `QUERY` decorator, a `Vary` merge only the session/CSRF extensions trigger. `Response.write()`,
  `send_file()` (1,024 B reads at `:567, :746`), `dispatch_request()`/`handle_request()` unchanged; Part I.6's cited
  lines move `:1400/:1410/:1443` → `:1418/:1428/:1461`. sha256: `microdot.py` d9e0bea6…, `LICENSE-microdot` 1f509e83…
  (unchanged), `typings/microdot/__init__.pyi` 6fed3ee8…, `microdot.pyi` f6a3c4d9…, `multipart.pyi` 208e9355….
  `.gitignore`'s `typings/` is anchored to the root so the vendored stubs are tracked (the entry only ever meant the
  installed stub directory).
- (e) No pin moved. M.PROC.011's issue states, read 2026-10-06: micropython#9455 open, #9505 open, #19704 open,
  #18797 closed (milestone 1.28.0, PRs #18801/#18805) — already inside the `v1.29.0` pin.

## Gates (M.PROC.009)

Each family commit's full gate ran on its own worktree with every port-binding suite in its own network namespace
(U0 (5a)) and the toolchain rows under the shared toolchain lock; logs under the gate worktrees, summaries below.

| family | commit | result |
|---|---|---|
| (a) | `9f32315` (merged) | green. First run: `firmware_build_verify` and `toolchain_test` rc 1 from the unlocked baseline firmware build sharing `mpy-cross/build`; both pass on a quiet re-run (logs archived under `audit/archive/20261006T072405Z/`); the toolchain lock was added. |
| (b) | `b10a3f1` (merged `d2bb623`, CI green) | green. `L1_test_sh_gc_default` rc 1 once (`_hammer_faulted`'s retention bound under host contention, finding X01); 10/10 isolated repeats and the quiet re-run pass. |
| (c) | `3c37346` (merged `e8f5dc0`, CI green) | green, all 19 rows rc 0 (pytest 319 s, npm test 571 s, unit tier 334/375 s, coverage 497 s, firmware 247 s, twins 748-898 s). |
| (d) | `e0e9b0c` (merged `6ca1d7f`, CI green) | green, all 19 rows rc 0 (firmware 495 s while queued on the toolchain lock). |

## Workarounds (W01-W45)

With the MicroPython pin unchanged, every check "at the new pin" (W01-W06, W10-W28, W37-W42, W44, W45) has nothing new
to read: each stays as it is. The checks with a moved dependency:

| W | check | outcome |
|---|---|---|
| W08, W09 | stdlib stubs `1.29.0.post2` | both defects still ship (`asyncio/futures.pyi` absent, `# NotImplemented` commented out); repairs stay |
| W29, W30, W43 | Microdot `v2.7.0` | `Response.write()`, `dispatch_request()`/`handle_request()` and the 1,024 B `send_file` default unchanged; all three stay |
| W32 | actionlint | still 1.7.12 (actionlint-py 1.7.12.25 repackages it); `self-repository` stays disabled |
| W33 | `uv sync` retry | stays (guards any third-party outage) |
| W34 | `@vitest/coverage-v8` 5.0.3 | trial on the family (b) tree with `exclude: ["**/*.json"]` removed: 574/574 pass but rolldown logs 28 `Failed to parse ….json?import` errors; the exclude stays (M.TSC.167's deletion does not fire) |
| W35 | cross-browser channels | unchanged reasons; stays |
| W36 | Vitest browser navigation | vitest#7875 closed; Vitest 5.0.3's browser `page` (`@vitest/browser/context.d.ts`) has no navigation method; the Commands-API route stays |

## Family (g): derived-code upstreams (M.PROC.010)

THIRD_PARTY records no upstream commit for any derived file, and each file's first commit here is the 2026-07-13
import, so the whole history of every kept upstream file was read, not only the window since the import. Already
present or not applicable: Adafruit BMP3XX (`05ba78b`; constants, coefficient table, formulas identical), Adafruit SGP40
(`8bfcca6`; `a94d620`'s 500 ms measure delay is not a chip requirement, Table 8 gives 30 ms max), Adafruit FRAM
(`eebbba5`; opcodes identical to the MB85RS2MTA table), Sensirion gas-index-algorithm (`2ef9f13`; every constant
identical; algorithm 3.1's split gammas are a version upgrade, not a fix, and would change output and FRAM state),
DFRobot VOCAlgorithm (`7fa498f`; whitespace only), p-doyle captive portal (`27cc627`; nothing since 2019). Archived or
inspiration-only (jposada ISL29125, Sensirion embedded-sgp, aiodns, karfas): nothing to take. Three applicable fixes,
parked as A-C deltas in the register: Adafruit SCD30 `3eb3b52` (temperature offset `round()`, U15), micropython-lib
`9ec1830` (reject NTP replies under 48 bytes, U18) and `5139530` (reject a zero transmit timestamp, U18; its stratum-0
half is already present).

## Second check before the release (A.SDEP.25), 2026-11-10

Newest stable releases re-queried on the day (PyPI JSON, `npm view`, `nodejs.org/dist/index.json`); the pins that stay
(MicroPython and its submodules, the stubs, Microdot, freezefs, picotool, mpremote, shellcheck-py, actionlint-py, the
Actions) are as the W2 hand-back's table found them. Moved, one commit on `audit/pin`:

| D | dependency | before | after |
|---|---|---|---|
| D16 | mypy, ruff, pytest, zizmor, types-pyserial | 2.4.0, 0.16.10, 9.1.1, 1.30.1, 3.5.0.20260712 | 2.4.1, 0.17.4, 9.2.0, 1.32.0, 3.5.0.20261104 |
| D17 | transitive (`uv lock --upgrade`) | ast-serialize 0.12.1, iniconfig 2.3.0, mypy-extensions 1.1.0, platformdirs 4.12.3, pluggy 1.6.0 | 0.13.1, 2.3.1, 1.2.0, 4.14.5, 1.7.0 |
| D18 | uv (`required-version`) | 0.8.17 | 0.13.7 (lock revision 3 → 5) |
| D19 | coverage (dev group and `_render_coverage.py`) | 7.16.2 | 7.17.2 |
| D21 | Node (`.nvmrc`, `engines`, `devEngines`) | 24 | 26 (26.13.0, Active LTS "Lithium") |
| D22 | npm (lock regenerated from scratch: the old lock's vitest 5.0.3 peers blocked 5.1.0) | vitest/@vitest 5.0.3, eslint 10.12.0, globals 17.13.0, html-validate 11.16.2, stylelint 17.16.0, -config-standard 40.0.0, @types/node 24.19.1 | 5.1.0, 10.14.0, 17.14.0, 11.21.0, 18.0.0, 41.0.0, 26.6.6; 305 → 236 lock entries |
| D23 | Playwright Chromium | 1.63.0, rev 1243 (153.0.8010.12) | 1.65.0, rev 1254 (158.0.8127.18) |

- (a) ruff 0.17.0 adds `datetime as dt` to ICN001's conventional aliases: four findings, fixed at their sites
  (`buildgen/model.py`, `scripts/record_twin_instrument_runs.py`, `tests_hardware/manual/manual_sensor_accuracy.py`,
  `tests_scripts/_toml_fixtures.py`); no other new finding (TID254/TID255/RUF071 stabilised, none fires;
  `target-version` is set, so the py311 default does not apply). mypy 2.4.1: the three passes clean (283/309/58 files),
  no unused ignore. pytest 9.2.0: `visit_BoolOp` still in `_pytest/assertion/rewrite.py` (the PT018 reason, re-stamped);
  `-m` names are now checked against registered markers: the bench floor collects (`--collect-only`, 210/250, 40
  deselected). zizmor 1.32.0: root-aware collection finds the same six inputs and the repo config (14 suppressed, no
  finding); `self-repository` stays disabled (actionlint still 1.7.12). Lock merge check: installed ruff 0.17.4, mypy
  2.4.1, zizmor 1.32.0, pytest 9.2.0, coverage 7.17.2 equal their pins; every dev specifier equals its locked version.
- (b) uv 0.9-0.13 breaking notes read; the one touching this repo, 0.12's script-relative project discovery, finds the
  same root for every `uv run scripts/…`/`toolchain/…`. Node 26: no semver-major change reaches the Node-context files'
  `child_process`/`fs`/`net`/timers; every direct package's `engines` admits 26. ESLint 10.13-10.14 add no core rule.
  Stylelint 18 (migration guide read): the config only extends the standard set, none of its removals applies; config
  41's newly enabled rules find nothing in `html/`. html-validate 11.18's `presentation-role-style` is in `recommended`:
  no finding. `npm audit`: 4 moderate, all one chain, minimatch ≤ 11.0.0 (GHSA-g3hv-75wg-m249) under eslint's
  `@eslint/config-array` (`^10.2.4`, already in the old lock); no fixed release in that range, dev-only CI path matching
  this repo's own globs: recorded, not fixable here. The stylelint `braces` chain is gone.
- (b) Chromium 158 is not on the Playwright CDN reachable here; Chrome for Testing 158.0.8127.18 was fetched from
  `storage.googleapis.com` and started (`--version`), then removed: the host had 1.7 GB free with it (3 GB rule). The
  local web tiers therefore ran on the sandbox's Chromium 153 fallback; CI's browser cache is keyed on
  `package-lock.json`, so its next web job installs 158.

| W | check | outcome |
|---|---|---|
| W32 | zizmor 1.32.0, actionlint 1.7.12.25 | actionlint unchanged: `self-repository` stays disabled |
| W33 | `uv sync` retry | stays (actionlint-py still an sdist fetching its binary) |
| W34 | `@vitest/coverage-v8` 5.1.0 | `provider.js` differs from 5.0.3 only by the CJS-interop ignore and an `ignoreNode` option; file selection unchanged, so the exclude stays (read, not trialled) |
| W36 | Vitest 5.1.0 browser `page` | `BrowserPage` still has no navigation method; the Commands-API route stays |

Checks on the moved tree, the unit's own venv and Node 26.13.0: `lint_direct.sh` rc 0; the three mypy passes clean; npm
`lint`, `typecheck`, `lint:css`, `lint:html`, `lint:html:built` rc 0; `npm run test:unit` 1,192/1,192; the
cross-browser smoke's Chromium 12/12 (the three other engines not installed here); `PICO_TOOLCHAIN_DIR=S/tc-c
scripts/test.sh` at -1 PASS: 120 files, 5,252 tests, `tests_scripts` 6,566 passed, no retry, no memory marker. The
32768 stage, the twin legs and CI run at the merge (B5's re-verification passes are this family's gate).
