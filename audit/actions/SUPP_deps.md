# A-L supplement SUPP_deps — the dependency-refresh step (HEAD cbedc48)

Why: OR129 (owner, 2026-09-30) "Check all external dependencies for updates - both modules, repos and tooling, just
everything. - If you find updates, carefully check what was changed. - Solve possible breaking changes without any
regressions. - Check for opportunities, improvements, fixes we can profit from and update our code accordingly. - Check
especially for fixes we needed to implement workarounds for, if they were solved upstream, apply and fix no longer needed
workarounds to clean implementations." OR129.a (1)-(5) place it inside U0 right after the B0 baseline and before the first
B1 change, with a short second check in U37; register block LEAD/R33 (`audit/pass2/LEAD.md:347-355`).

Method: every pin site was found by search at HEAD `cbedc48` (`toolchain/`, `scripts/`, `pyproject.toml`, `uv.lock`,
`package.json`, `package-lock.json`, `.nvmrc`, `.github/`, `ext/`, `vitest.config.js`, PEP 723 headers, `THIRD_PARTY_LICENSES.md`;
greps for `git clone|curl |wget |pip install|npm install|uv pip|micromamba|apt-get install|https?://`, `# /// script`,
`uses:`); MicroPython submodule pins read from the scratchpad `mp/` checkout at `v1.29.0` (`0fd6c57`, `git submodule
status`), the rp2/Unix submodule lists from `ports/rp2/CMakeLists.txt:94-96, 365, 411`, `extmod/extmod.cmake:351`,
`py/mkrules.cmake:268`, `ports/unix/Makefile:47, 175-178`, `extmod/extmod.mk:247-249` and the manifests
`ports/rp2/boards/manifest.py`, `ports/unix/variants/manifest.py` at that tag. No network: the new versions are found at
execution time by the commands each action names. The legacy tree and `arduino/` are out (OR129.a (2)); nothing there was
read. The previous whole-tree refresh (`90e8c17`, 2026-09-10, "Update every external module to latest stable") is the
precedent for scope and record shape. Line citations of other units' actions were counted with the scanner kept at the
scratchpad `al/SUPP_deps/cites2.py` (its regex set is restated in A.SDEP.23). Permanent text quoted below carries no audit ID.

## Inventory at HEAD

"Moves by" says how the pin changes; "derived" means it follows another pin and is never set by hand.

| # | dependency | pin site (HEAD) | value at HEAD | moves by | what this repo uses it for |
|---|---|---|---|---|---|
| D1 | MicroPython | `toolchain/versions.toml:10` `ref` | `v1.29.0` (`0fd6c57`) | edit `ref` or `setup_toolchain.py --latest` (`:522-537`, `:554-557`) | firmware, `mpy-cross`, both Unix-port test binaries, frozen `extmod/asyncio` |
| D2 | pico-sdk | derived, `toolchain/setup_toolchain.py:225-233` (`lib/pico-sdk` submodule of D1) | `98a542c` (2.3.0, `90e8c17` message) | D1 | rp2 HAL (I2C/SPI/UART/watchdog/flash), CYW43 arch |
| D3 | pico-sdk's `lib/mbedtls` | `setup_toolchain.py:586` (`git submodule update --init lib/mbedtls` in `pico-sdk/`) | D2's pin | D2 | picotool build |
| D4 | picotool | derived, `setup_toolchain.py:236-255` (newest tag sharing D2's major.minor), installed `:258-285` under `/usr/local` | `2.3.1` at the last bump (`90e8c17`) | D2; newest matching patch floats at each `setup` | flashing, UF2 info |
| D5 | lwIP | D1's `lib/lwip` (`extmod/extmod.cmake:351`) | `77dcd25` | D1 | rp2 TCP/IP; options `versions.toml:41-52` via `micropython_overrides.py` |
| D6 | cyw43-driver | D1's `lib/cyw43-driver` (`ports/rp2/CMakeLists.txt:411`) | `055d642` | D1 | Wi-Fi STA/AP |
| D7 | mbedtls | D1's `lib/mbedtls` (`ports/rp2/CMakeLists.txt:95`; Unix `extmod/extmod.mk:247-249`, `MICROPY_SSL_MBEDTLS = 1` `ports/unix/mpconfigport.mk:31`) | `0bebf8b` (v3.6.6, pass 4 F.18) | D1 | compiled into both targets; `-Wno-array-bounds` workaround |
| D8 | tinyusb | D1's `lib/tinyusb` (`ports/rp2/CMakeLists.txt:96`) | `b549ac1` | D1 | USB CDC console |
| D9 | btstack | D1's `lib/btstack` (`RPI_PICO_W/mpconfigboard.cmake` `MICROPY_BLUETOOTH_BTSTACK ON` → `CMakeLists.txt:365`) | `77e752a` | D1 | compiled in, unused by `src/` (image size only) |
| D10 | micropython-lib | D1's `lib/micropython-lib` (`py/mkrules.cmake:268`) | `ee4bb8f` | D1 | frozen by the board manifests: `bundle-networking`, `aioble`, `onewire`, `ds18x20`, `dht`, `neopixel` (rp2); `unix-ffi`, `mip-cmdline`, `ssl` (Unix); `src/` imports `neopixel` |
| D11 | berkeley-db-1.xx | D1's submodule (`ports/unix/Makefile:47`) | `0f3bb69` | D1 | Unix port build only |
| D12 | ARM cross-compiler and host build tools | `versions.toml:14-29` `apt_packages` (`gcc-arm-none-eabi`, `libnewlib-arm-none-eabi`, `libstdc++-arm-none-eabi-newlib`, `build-essential`, `cmake`, `pkg-config`, `git`, `libusb-1.0-0-dev`, `libffi-dev` — system libffi, since `MICROPY_STANDALONE` is unset, `ports/unix/Makefile:175-178` — `libcap2-bin`) | distro version, unpinned by decision (SPEC B.3 step 4 "no pin needed") | the host's apt archive / the CI runner image | every build |
| D13 | Microdot | `ext/microdot.py` + `ext/LICENSE-microdot`; stated at `THIRD_PARTY_LICENSES.md:15-20`, SPEC `:62`, `:289-294`, CLAUDE.md `:108-115`, `:857`, `:1063` | tag `v2.6.2` (upstream `v2.7.0` exists, SPEC A.5 `:290-294`, checked 2026-09-23) | re-vendor an unmodified upstream tag | the REST/static server |
| D14 | freezefs | `ext/freezefs/` (`__main__.py`, `archive.py`, `ffsmount.py`, `ffsextract.py`, `LICENSE`); stated at `THIRD_PARTY_LICENSES.md:21-23`, SPEC `:63` ("freezefs 2.4") | upstream `main` synced 2026-09-10 (`90e8c17`); upstream `main` at `26be9e3` per `audit/actions/U34.md:7` | re-vendor upstream `main` (no tags) | website freezing (`scripts/build_frozen_html.sh:33`), runtime `VfsFrozen` |
| D15 | MicroPython stubs | `scripts/typecheck.sh:64-67` `micropython-rp2-rpi_pico_w-stubs==<ref X.Y.Z>.*` (pulls `micropython-stdlib-stubs`) | `1.29.0.*` — installed `1.29.0.post1`, stdlib `.post1/.post2` (SPEC F.5.5); the newest post-release floats at each install | D1 (X.Y.Z); post-release floats | main mypy pass typeshed (`typings/`) |
| D16 | Python dev tools | `pyproject.toml:17-36` | `mypy==2.3.1` (`:21`), `ruff==0.16.6` (`:22`), `pytest` unpinned (`:23`; `uv.lock:350` 9.1.1), `mpremote` unpinned (`:24`; `uv.lock:214` 1.29.0), `types-pyserial==3.5.0.20260712` (`:27`), `shellcheck-py==0.11.0.1` (`:31`), `actionlint-py==1.7.12.24` (`:32`), `zizmor==1.30.1` (`:35`) | edit the pin, `uv lock` | lint, typecheck, host tests, hardware runner |
| D17 | Python transitive set | `uv.lock` (21 packages, `version = 1`, `requires-python = ">=3.11"`) | e.g. `pluggy 1.6.0`, `pygments 2.21.0`, `packaging 26.3`, `pyserial 3.5` | `uv lock --upgrade` | the above |
| D18 | uv | unpinned: `pip install uv` at `.github/actions/setup-micropython-toolchain/action.yml:18`, `ci.yml:324, :353, :379, :404`; locally whatever is installed | floating | newest at each CI run | every Python step |
| D19 | coverage (renderer) | `scripts/_render_coverage.py:4` PEP 723 `dependencies = ["coverage"]` | unpinned, unlocked | newest at each run | `scripts/test.sh --coverage` (`:479, :481`) |
| D20 | host Python | `pyproject.toml:11` `requires-python = ">=3.11"`, the five PEP 723 headers | the host's / runner's interpreter | host | every host script |
| D21 | Node | `.nvmrc:1` `22` (major only); patch = newest `latest-v22.x` at install (`setup_toolchain.py:929-1011`); CI `actions/setup-node` `node-version-file: .nvmrc` (`ci.yml:75, :104, :156, :200, :271`) | 22.x | edit `.nvmrc` | web tier |
| D22 | npm packages | `package.json:23-37` (13 caret ranges) + `package-lock.json` (lockfileVersion 3, 307 packages) | `@eslint/js 10.0.1`, `@types/node 26.5.1`, `@vitest/browser-playwright 5.0.0`, `@vitest/coverage-v8 5.0.0`, `eslint 10.10.0`, `eslint-plugin-html 8.2.0`, `globals 17.12.0`, `html-validate 11.15.0`, `playwright 1.63.0`, `stylelint 17.15.0`, `stylelint-config-standard 40.0.0`, `typescript 7.0.2`, `vitest 5.0.0` (lock `:384`, `:943`, `:1317`, `:1341`, `:1939`, `:1998`, `:2364`, `:2462`, `:3382`, `:3839`, `:3922`, `:4187`, `:4352`) | edit ranges, `npm install` | web lint, typecheck, tests |
| D23 | Playwright Chromium | derived from `playwright-core 1.63.0` (lock `:3398`); `npx playwright install chromium` (`setup_toolchain.py:1050`, `ci.yml:118, :168, :212, :285`); cache key `hashFiles('package-lock.json')` (`ci.yml:115, :165, :209, :282`); sandbox fallback `/opt/pw-browsers/chromium` (`vitest.config.js:18-19`) | Playwright's pinned build | D22 | Vitest browser mode |
| D24 | cross-browser engines | `scripts/setup_cross_browser_toolchain.sh:21` (`webkit2gtk-driver`, `xvfb`, apt), `:29-33` (`microsoft-edge-stable`, Microsoft apt repo), `:50-53` (micromamba `latest`, conda-forge `firefox geckodriver`) | unpinned by decision (G8 contradiction 6: owner browser floor PQ10) | newest at install; CI cache key `cross-browser-firefox-v1` (`ci.yml:305`) | `scripts/cross_browser_smoke.mjs` |
| D25 | first-party GitHub Actions | `actions/checkout@v7` (`ci.yml:32, 70, 99, 151, 195, 266, 320, 349, 375, 400, 432, 463, 486, 579, 612`), `actions/setup-node@v5` (`:73, 102, 154, 198, 269`), `actions/cache@v6` (`:112, 162, 206, 279, 302`; `action.yml:32`), `actions/upload-artifact@v7` (`:248, 545, 552, 588`) | tag-pinned (`zizmor.yml:10` `ref-pin`) | edit the tag | CI |
| D26 | third-party GitHub Actions | `dorny/paths-filter@15192bc… # v3` (`ci.yml:35`); `codecov/codecov-action@a99c28d… # v7` (`:530, :537`) | SHA-pinned (`zizmor.yml:13` `hash-pin`) | hand bump; codecov goes (OR63.a, A.U28.15) | web path filter |
| D27 | CI runner image | `runs-on: ubuntu-latest` (every job) | floating | GitHub | D12's apt versions in CI |
| D28 | derived-code upstreams (not fetched) | `THIRD_PARTY_LICENSES.md:25-106, :123-156, :175-205`: Adafruit BMP3XX, SCD30, SGP40, FRAM; jposada202020/MicroPython_ISL29125 (archived 2024-12); micropython-lib `ntptime.py`; vshymanskyy/aiodns (inspiration only); p-doyle captive portal (Apache-2.0); DFRobot_SGP40 / Sensirion embedded-sgp (archived 2024-04), successor Sensirion/gas-index-algorithm; karfas/upy-simple-app | derivation point only; no pin | — | reference for fixes to the kept parts |

Not in scope: the `datasheets/` submodule (the owner's own private repository, OR80.a — data, not an external
dependency); the scratchpad reference clones (audit files); the legacy tree and `arduino/` (OR129.a (2)).

## Actions

### A.SDEP.01 Run the refresh after the baseline, one family per commit
- **Why**: LEAD/R33 — "After the B0 baseline and before the first B1 change, every external dependency … is checked
  for updates; each update's changes are read; breaking changes are fixed with no regression …; useful upstream fixes
  and improvements are adopted" (owner, 2026-09-30, OR129; OR129.a (1)-(3)).
- **Site**: U0 execution order: after A.U0.06 (baseline measured) and A.U0.02/A.U0.04 (baseline SHA, non-interference
  rules), before the first B1 unit (U1); worktree and branch per A.U0.04; record `audit/artefacts/ENV/dependency_refresh.md`
  (audit file, beside A.U0.06's `baseline.md`).
- **Change**: (1) The record holds one row per inventory line D1-D28: pin site, value before, newest available (with
  the command that found it, run at execution), changelog/diff read (link or tag range), decision (moved / held back /
  already newest / not applicable) with its reason, check result (A.SDEP.02), and the commit. (2) Order, one family per
  commit so a regression bisects to one family: (a) Python tools and `uv.lock` (A.SDEP.03); (b) Node, npm, Playwright
  (A.SDEP.04); (c) GitHub Actions (A.SDEP.05); (d) Microdot, freezefs (A.SDEP.06, A.SDEP.07); (e) MicroPython with
  everything it pulls in, then the stubs (A.SDEP.08, A.SDEP.09); (f) the workaround checks (A.SDEP.11-A.SDEP.19),
  each retirement its own commit; (g) derived-code upstreams (A.SDEP.10). Tools go first so the firmware bump's findings
  are measured with the final tool set. (3) "Newest" means the newest stable release of that family (no pre-release,
  release candidate or preview tag; for Node the newest release line in Active LTS; for MicroPython a plain `vX.Y.Z`
  tag, as `latest_stable_micropython_ref()` already selects, `setup_toolchain.py:522-537`); untagged upstream commits
  after a tag are noted in the record only (G4/R01 Req "newer upstream changes are noted only"). (4) Hold-back rule,
  self-resolved from OR129.a (3) "fix breaking changes with no regression": a dependency whose newest release breaks a
  check and whose break cannot be fixed within the standing rules (vendored code never edited, no test-only artefact in
  product code, no weakened gate) stays at the newest release that passes, and a BACKLOG "Deferred / explicitly
  out-of-scope work" entry names it, the failing release, the reason and "re-checked at the next refresh"; the U37 check
  (A.SDEP.25) re-reads it. (5) Routing: a breaking-change fix and a workaround retirement are made in this step; an
  adoption opportunity that changes project behaviour or structure beyond that (a new upstream API worth using, an
  upstream fix to derived code) is entered as a delta item for its owning unit (CONSOLIDATION section 2: "later
  findings (B0, B3, C) pass it as a delta"), with the upstream reference. A change that would alter an owner-decided
  behaviour is parked and logged for review (harmonization 1), never a stop. (6) No real hardware in this step:
  nothing is flashed and no `mpremote` runs; a firmware version change is validated in phase C (OR129.a (5), A.SDEP.08).
- **Blast**: callers — · generated — · js — · tests — (the checks are A.SDEP.02's) · twin — · docs audit file; the
  permanent records are A.SDEP.21 · toml — · uart —.
- **Depends**: A.U0.02, A.U0.04, A.U0.06.
- **Kind**: rule (audit file)

### A.SDEP.02 One check gate per family, against the baseline
- **Why**: LEAD/R33 — "breaking changes are fixed with no regression against the baseline at every level and both GC
  stages"; OR129.a (3) "lint and typecheck clean; a ruff/mypy upgrade's new findings are decided one by one, never
  blanket-ignored"; CLAUDE.md memory-safety bullet (the four `MemoryError` gates, both GC stages).
- **Site**: every family commit of A.SDEP.03-A.SDEP.19; results in the refresh record.
- **Change**: after each family commit, serialized under A.U0.04's port lock, the same command set A.U0.06 measured:
  L0 `uv run pytest tests_scripts`, `npm run lint`, `npm run typecheck`, `npm run lint:html`, `npm run lint:css`, `npm
  test` (all shards, the live PUT matrix included); L1 `scripts/test.sh` and `GC_THRESHOLD=32768 scripts/test.sh`, plus
  `scripts/test.sh --coverage` (coverage advisory, its test result gating, SPEC E.5.3); L2 `scripts/run_digital_twin_ci.sh`
  for every device (both GC stages inside); L3/L4 `uv run pytest tests_hardware --collect-only` (board-free, HW.T14);
  `scripts/lint.sh` (ruff, shellcheck, actionlint, zizmor); `scripts/typecheck.sh` (all three passes); every device's
  firmware built and verified (`RUN_SLOW_FIRMWARE_BUILD=1 uv run pytest tests_scripts/test_build_firmware.py -k
  test_real_firmware_build_produces_a_valid_uf2`); for families (e) and (a) also `uv run toolchain/setup_toolchain.py
  test`. Pass criteria against the A.U0.06 record: zero failures; collected/passed/skipped/deselected counts equal to the
  baseline or each difference explained in the record; zero `MemoryError` / `memory allocation failed` markers at both
  GC stages in the unit and twin gates (the flash/bench gates' shared `MEMORY_ERROR_MARKERS` stays covered by
  `tests_scripts/test_memory_error_gate_agreement.py`; those two gates themselves run in phase C); lint 0 and each mypy
  pass 0 findings; `tsc`, ESLint, Stylelint, html-validate 0 findings; wall clock, host peak RAM and image sizes
  (LEAD/R07) recorded — a figure worse than the baseline beyond run-to-run spread (established by one repeat of that
  level on the baseline worktree, inside A.U0.04's repeat budget) is a regression to root-cause, never accepted silently. New findings from an upgraded checker
  (ruff, mypy, ESLint, `tsc`, Stylelint, html-validate, shellcheck, actionlint, zizmor) are listed in the record one by
  one and each is decided: fix the code, or add the narrowest suppression the tool offers with its reason in the
  existing place (`pyproject.toml` `[tool.ruff.lint]` ignore list with a comment; the per-rule entries of
  `eslint.config.js`, `.stylelintrc.json`, `.htmlvalidate.json`; `zizmor.yml`) — never a blanket disable, never a
  version held back to avoid a finding. The family commit is pushed and CI goes green before the next family starts
  (the sync point of CONSOLIDATION section 2).
- **Blast**: callers — · generated — (regenerated by the runs) · js — · tests none changes by this action · twin state
  files archived first (A.U0.04) · docs audit record · toml — · uart —.
- **Depends**: A.U0.06, A.SDEP.01.
- **Kind**: test (audit file)

### A.SDEP.03 Refresh the Python dev tools and `uv.lock`
- **Why**: LEAD/R33 — "Python dev tools and `uv.lock`"; OR129.a (5) "tools stay pinned …; the `uv.lock` merge check";
  CLAUDE.md "Code quality tooling" (every tool pinned: `select = ["ALL"]` turns an unpinned upgrade into an unchosen
  rule) and the `uv.lock` bullet (`CLAUDE.md:791-804`).
- **Site**: `pyproject.toml:21-35` (pins), `uv.lock` (whole file); D16-D20.
- **Change**: find newest: `uv lock --upgrade --dry-run` (or `uv tree --outdated --depth 1`) for the direct and
  transitive set, and each tool's PyPI release list for the exact newest stable. Read, per tool, the changelog from the
  pinned version to the newest, for the parts this repo uses: **ruff** — every rule newly stable (select `ALL` enables
  it), rules renamed or removed (an ignore list or `noqa` naming a gone code), changes to rules in the `ignore` list and
  `per-file-ignores` (`pyproject.toml:62-` and the per-file table), `target-version = "py310"`, `allowed-confusables`;
  **mypy** — flags newly part of `--strict`, changes to `warn_unused_ignores`, `custom_typeshed_dir`/`follow_imports`
  handling (the main pass, SPEC B.15), the bundled typeshed (the host pass) and error-code renames used in `# type:
  ignore[...]` comments; **pytest** — deprecations touching `tests_scripts/conftest.py` and `tests_hardware/conftest.py`
  (custom options, markers and the deselect hook the wear gates use, `--collect-only`), `tmp_path`, `monkeypatch`,
  `parametrize`, `skip`; **mpremote** — the commands the hardware tier drives (`connect`, `exec`, `run`, `soft-reset`,
  `reset`; `tests_hardware/harness.py`, `scripts/mpremote_connect.sh`, `scripts/run_*_hardware_suite.sh`), its
  compatibility with the firmware pin D1 (mpremote's version equals the MicroPython release it ships with; after
  A.SDEP.08 moves D1, mpremote moves to the same release); **shellcheck-py / actionlint-py / zizmor** — new checks and
  config-schema changes (`zizmor.yml`; actionlint's `uses: $/` support, W32 of the catalog); **types-pyserial** —
  signature changes the host pass checks. Then: exact `==` pins in `pyproject.toml` for the tools that carry one today
  (pytest and mpremote stay unpinned here; A.U28.02 pins them, taking the versions this refresh resolved), `uv lock
  --upgrade`, `uv sync`, and the merge check CLAUDE.md prescribes, done on every lock rewrite, not only after a merge:
  `ruff --version`, `mypy --version`, `zizmor --version`, `actionlint --version`, `shellcheck --version` each equal the
  pin, and every `[package.metadata.requires-dev] dev` specifier in `uv.lock` agrees with the lock's `[[package]]
  version` of that name (A.U28.03 later makes this a test). uv itself: record `uv --version` before and after (A.U28.02
  pins it from this refresh's version). `coverage` (D19): record the version `uv run scripts/_render_coverage.py`
  resolves; A.U24.72/A.U28.02 pin it. Check gate A.SDEP.02; the new-findings list is decided there.
- **Blast**: callers every `uv sync`/`uv run` (local, CI, `setup_toolchain.py env`) · generated — · js — · tests
  existing: the whole suite runs under the new pytest; `tests_scripts/test_micropython_overrides.py`, `test_build_firmware.py`
  and every L0 file are what a pytest deprecation would break · twin — · docs CLAUDE.md "Code quality tooling" names
  no version numbers (grep at HEAD: `0.16.6`, `2.3.1` appear only in `pyproject.toml`/`uv.lock` and this repo's audit
  files) · toml `pyproject.toml`, `uv.lock` · uart — · build-environment: A.SDEP.21's BACKLOG chroot entry.
- **Depends**: A.SDEP.01, A.SDEP.02.
- **Kind**: code

### A.SDEP.04 Refresh Node, the npm packages and the Playwright browser
- **Why**: LEAD/R33 — "Node and npm packages"; OR129.a (2) "Node (`.nvmrc`) and every npm package".
- **Site**: `.nvmrc:1`; `package.json:23-37`; `package-lock.json`; D21-D24.
- **Change**: find newest: Node — the newest release line whose status is Active LTS in `https://nodejs.org/dist/
  index.json` (`lts` field); npm — `npm outdated` (wanted/latest per package) and `npm view <pkg> version` for each of the
  13 direct packages. Read the release notes from the locked version to the newest for the parts this repo uses:
  **Node** — the APIs of the Node-context files (`vitest.config.js`, `tests_js/_live_twin_command.js`,
  `tests_js/_live_matrix_command.js`, `scripts/cross_browser_smoke.mjs`: `child_process`, `fs`, `net`, timers) and the
  engines range of every direct package; **vitest / @vitest/browser-playwright / @vitest/coverage-v8** — browser mode,
  `provider: playwright({ launchOptions })`, the Commands API (`commands:` at `vitest.config.js:49-58`), `testTimeout`,
  `coverage.reportsDirectory`/`exclude` (catalog W34), `--exclude` CLI semantics used by `package.json:14, :18`;
  **playwright** — `chromium.launch({executablePath})`, `install`/`install-deps` CLI, the bundled Chromium revision;
  **eslint / @eslint/js / eslint-plugin-html / globals** — every core rule added since the pinned version (the curated
  `BUG_CATCHING_RULES` list in `eslint.config.js:13-` mirrors ruff `ALL`: each new core rule is decided — added with a
  reason or left out as a style preference, per the file's own header), `recommended` changes, flat-config changes;
  **typescript** — `checkJs`/JSDoc behaviour under the strict flags in `tsconfig.json:10-24` and `tsconfig.node.json`;
  **stylelint / stylelint-config-standard** and **html-validate** — rules added to the extended presets
  (`.stylelintrc.json`, `.htmlvalidate.json` `recommended`/`document`/`a11y`) and `require-sri`; **@types/node** — its
  major follows `.nvmrc` (A.U28.23 states the rule; the refresh applies it: `@types/node` takes the newest release of the
  `.nvmrc` major). Then: `.nvmrc` → the new major if it moved; `package.json` ranges → `^<newest>` (the caret form stays,
  the lock pins); `npm install` regenerates `package-lock.json`; `npm audit` read and every advisory in a shipped-path
  or CI-path package resolved by the update or recorded; `npx playwright install chromium` (the CI cache key follows the
  lock hash by itself). Check gate A.SDEP.02, plus the cross-browser smoke (`scripts/setup_cross_browser_toolchain.sh`
  then `node scripts/cross_browser_smoke.mjs`) where the sandbox can run it, else CI's `web-cross-browser-smoke` job.
- **Blast**: callers CI `setup-node` (`node-version-file: .nvmrc`, unchanged), `setup_toolchain.py` `ensure_node()`
  (reads the major, unchanged) · generated `build/generated_src/definitions/` rebuilt by `npm run build:site` (no
  content change expected) · js every `js/`, `tests_js/` file under the new lint/type rules · tests existing: the whole
  web tier; `tests_scripts/test_js_coverage_excludes_json.py`, `test_js_coverage_report_dir.py` (pin vitest config
  halves) · twin — (the live-twin commands spawn the twin; their Node APIs are the Node read above) · docs README
  "Website tooling" and SPEC H.8 name no package versions (grep at execution; a stated version is updated) · toml — ·
  uart — · build-environment: A.SDEP.21's BACKLOG chroot entry (`.nvmrc`, `package*.json`).
- **Depends**: A.SDEP.01, A.SDEP.02; co-lands A.U28.23 (`engines`, `@types/node` major rule — A-C moves it into this
  commit or leaves it in U28 with this refresh's versions).
- **Kind**: code

### A.SDEP.05 Refresh the GitHub Actions pins and record the runner image
- **Why**: LEAD/R33 — "GitHub Actions pins"; `zizmor.yml:5-13` policy (first-party tag-pinned, third-party SHA-pinned);
  CLAUDE.md `:499-500` "Adding a SHA-pinned third-party action means bumping that SHA by hand".
- **Site**: `.github/workflows/ci.yml` (D25 sites listed in the inventory), `.github/actions/setup-micropython-toolchain/
  action.yml:32`; D26, D27.
- **Change**: find newest: for each first-party action the newest major tag (`git ls-remote --tags
  https://github.com/actions/<name>`); read its release notes from the pinned major for the inputs this repo passes:
  `checkout` `persist-credentials: false`; `setup-node` `node-version-file` (and its default caching, which this repo
  does not enable); `cache` `path`/`key` (and restore semantics the toolchain and Playwright caches rely on);
  `upload-artifact` `name`/`path`/`if-no-files-found`/`continue-on-error` use (`ci.yml:248, 545, 552, 588`) and the
  artifact-name uniqueness rule per run. Tags move by editing `@vN` at every site of that action (one `sed` per action,
  the count per action recorded). `dorny/paths-filter`: A.U28.13 is executed here (newest `v4.x.y`, peeled commit, its
  changelog and code-path reading); A-C moves it into this commit. `codecov/codecov-action` is not refreshed: A.U28.15
  removes it (OR63.a). Runner: record the image name and version `ubuntu-latest` resolved to (the "Runner Image" block
  of any job log) and the `gcc-arm-none-eabi`/`gcc` versions `firmware-build-verify` installed; a runner OS move since
  the baseline is a D12 change, covered by that job. Check gate A.SDEP.02 (zizmor `unpinned-uses` and actionlint are the
  gates that read these lines) and a green CI run.
- **Blast**: callers every CI job · generated — · js — · tests existing: none pins an action version (grep `@v[0-9]` in
  `tests_scripts/`: none; A.U28.08 later adds workflow-rule checks) · twin — · docs SPEC B.10/B.10.1 name no action
  versions (grep at execution) · toml — · uart — · build-environment: A.SDEP.21's BACKLOG chroot entry (CI config).
- **Depends**: A.SDEP.01, A.SDEP.02; A.U28.13 (pulled forward).
- **Kind**: code

### A.SDEP.06 Re-vendor Microdot at its newest upstream tag, unmodified
- **Why**: LEAD/R33 — "vendored Microdot as an unmodified upstream tag"; OR129.a (2) "re-vendored only as an unmodified
  upstream tag, never edited"; CLAUDE.md hard rule (`ext/microdot.py` "No edits, no restyling, ever"); G6/R53 (hash pin).
- **Site**: `ext/microdot.py`, `ext/LICENSE-microdot`; `THIRD_PARTY_LICENSES.md:15-20`; SPEC `:62`, `:289-294`, `:334`,
  `:5197`; CLAUDE.md `:108-115`, `:857`, `:1063`; `tests/test_setter_microdot_integration.py:272` (comment naming v2.6.2).
- **Change**: find newest: `git ls-remote --tags https://github.com/miguelgrinberg/microdot` (newest `vX.Y.Z`). If newer
  than `v2.6.2`: read `CHANGES.md` and `git diff v2.6.2..<tag> -- src/microdot/microdot.py` for what this repo relies on
  (the facts SPEC A.5 states and A.U19.19's checklist lists): `Microdot.get`/`put` registration, `errorhandler()` by
  status code and by class, `after_request`, `dispatch_request()`'s blanket catch, `Response.write()`'s `OSError` muting
  and `MUTED_SOCKET_ERRORS`, the stream methods `handle_request()` calls (the `_TimeoutStreamProxy` forwards exactly
  those: `readline`, `readexactly`, `awrite`, `aclose`, `close`, `wait_closed`, `get_extra_info`,
  `src/asy_webserver_service.py:234-291`), header-per-write emission (catalog W29), `Request.create()` → body read order
  and the class attributes `max_content_length`, `max_body_length`, `max_readline` (`:363-370`), `send_file(...,
  compressed=True)`, `Response.send_file_buffer_size` (`:666`), `find_route()` first-match order (`:397`), HTTP/1.0
  default, `redirect`, `abort`, `URLPattern` `<path:...>` (`:400`). Default: adopt (OR129 "just everything"); hold back
  only under A.SDEP.01 (4). Adopt: replace `ext/microdot.py` with the tag's `src/microdot/microdot.py` byte-for-byte and
  `ext/LICENSE-microdot` with the tag's `LICENSE`; record both sha256 in the refresh record; every text naming `v2.6.2`
  (sites above) → the new tag; CLAUDE.md `:108` "~441 lines behind the `v2.6.2`" re-measured against the new tag
  (`diff` line count of `python/CommonDrivers/microdot.py` — read, not edited — against it); SPEC A.5 `:290-294`'s
  upstream-v2.7.0 note becomes the statement of what the new tag changed for this repo. The legacy copy
  `python/CommonDrivers/microdot.py` is not touched (legacy rule). Check gate A.SDEP.02; the REST tiers are the
  deciding ones (`tests/test_asy_webserver_service.py`, `tests/test_setter_microdot_integration.py`,
  `tests/test_website_build_integration.py`, `tests/_webserver_concurrency_scenarios.py` and its six
  `test_digital_twin_webserver_concurrency_<device>.py`, the live PUT matrix).
- **Blast**: callers `src/asy_webserver_service.py` (imports `Request, Response, abort, redirect, send_file`, `:10`),
  `buildgen/codegen.py:303` (generated `from microdot import Microdot`), `api_response.py` `_RequestLike` stand-in ·
  generated every `sensortask_<device>.py` imports it (text unchanged) · js — · tests the files above; A.U19.18's hash
  table (sha256 computed for `v2.6.2`) and A.U19.19's `ext/microdot.py` line citations and A.U8.23's vendored stubs take
  the new tag (A.SDEP.23 re-check) · twin the webserver concurrency scenarios · docs sites above; SPEC H.7 serving walls
  (A.5 says a 2.7.0 move shifts none — re-verified for the actual tag) · toml — · uart — · build-environment: none
  (pure Python, copied into the frozen build by `scripts/build_firmware.py`).
- **Depends**: A.SDEP.01, A.SDEP.02; co-lands A.U19.18/A.U19.19/A.U8.23/A.U34.12 (they execute later against the new tag).
- **Kind**: code, doc

### A.SDEP.07 Re-vendor freezefs at upstream `main`, recorded by commit
- **Why**: LEAD/R33 — "any other fetched source"; `THIRD_PARTY_LICENSES.md:21-23` ("Upstream publishes no release tags,
  so 'current' here means `main`"); G9/R22 (freezefs recorded by commit, A.U34.08).
- **Site**: `ext/freezefs/*`; `THIRD_PARTY_LICENSES.md:21-23`; SPEC `:63`; `scripts/build_frozen_html.sh:10-11, :30-33`.
- **Change**: find newest: `git ls-remote https://github.com/bixb922/freezefs HEAD` (and tags, in case upstream starts
  tagging — then the newest tag is taken, as for Microdot). If the commit differs from the vendored state (compare each
  vendored file byte-for-byte against the upstream file at that commit): read the upstream log since the vendored state
  and the diff of `archive.py`, `ffsmount.py`, `ffsextract.py`, `__main__.py` for what this repo uses — the CLI options
  `scripts/build_frozen_html.sh:33` passes, the archive format (`archive.py` `VERSION`, `:13`) that the frozen website
  module carries, and `ffsmount.VfsFrozen` (the runtime mount `asy_webserver_service.py` serves from, `:329`, `:652`).
  Adopt: copy the upstream files byte-for-byte, record the commit SHA and each sha256; THIRD_PARTY `:21-23` names the
  commit (A.U34.08's wording: by commit, holder and year); SPEC `:63` "freezefs 2.4" → the recorded commit (A.U34.08
  already corrects the "2.4" name). An archive-format change alters the frozen website on silicon: its L2 coverage is
  `tests/test_digital_twin_real_website_integration.py` and `tests_scripts/test_build_frozen_html_sh.py`; the silicon
  check joins A.SDEP.08's BACKLOG hardware entry. Check gate A.SDEP.02.
- **Blast**: callers `scripts/build_frozen_html.sh:33`, the frozen `frozen_html` module at boot · generated the frozen
  website module (rebuilt) · js — · tests `tests_scripts/test_build_frozen_html_sh.py`, `tests/test_asy_webserver_service.py:16,
  :1848` (hand-built `VfsFrozen`), `tests/test_website_build_integration.py`,
  `tests/test_digital_twin_real_website_integration.py`; A.U34.08's `tests_scripts/test_vendored_freezefs.py` hashes take
  this commit (A.SDEP.23) · twin as tests · docs THIRD_PARTY, SPEC `:63`, A.9 · toml — · uart — · build-environment:
  none new.
- **Depends**: A.SDEP.01, A.SDEP.02; co-lands A.U34.08.
- **Kind**: code, doc

### A.SDEP.08 Move the MicroPython pin with everything it pulls in
- **Why**: LEAD/R33 — "MicroPython pin with lwIP/cyw43/pico-sdk/mbedtls, ARM toolchain and every
  `toolchain/versions.toml` pin"; OR129.a (5) "CLAUDE.md's version-bump re-check practice runs and its SPEC F.5 record
  is updated … a firmware version change is validated on hardware in phase C under its own go-ahead"; G4/R01 (the pin
  moves only on the owner's call — OR129 is that call; the platform re-check follows every move) (owner, 2026-09-26,
  OR69.a (9)).
- **Site**: `toolchain/versions.toml:10`; D1-D12; every text stating the pinned version (grep `1\.29` outside `audit/`,
  `ext/`, the legacy tree and `datasheets/`: 24 files at HEAD — SPECIFICATION.md 35 hits, CLAUDE.md 9, BACKLOG.md 7,
  `tests/machine.py` 5, `HEAP_FRAGMENTATION_MEASUREMENTS.md` 4, `digital_twin/README.md` 4, `digital_twin/machine.py` 4,
  `tests/test_asy_spi_driver.py` 2, `tests_hardware/device_scripts/bus_deinit_is_a_noop_on_real_hardware.py` 2, one each
  in `src/asy_spi_driver.py:5`, `src/asy_i2c_driver.py:183`, `src/asy_udp_socket.py:174`, `scripts/typecheck.sh:83`,
  `tests_hardware/README.md:424`, `digital_twin/unix_port_poll_prewarm.py:1`, `tests/test_config_manager.py:929`,
  `tests/test_website_build_integration.py:43`, `tests/test_digital_twin_bus_hazard_concurrency.py:475`,
  `tests/test_asy_wifi_service.py:440`, `tests/test_digital_twin_machine.py:319`, `tests/_fram_chip_fake.py:106`,
  `tests/test_asy_fram_manager.py:2204`, and the fixture literals `tests_scripts/test_buildgen_validate.py:1576`,
  `tests_scripts/test_micropython_overrides.py:857`, which stay (synthetic inputs, not claims)).
- **Change**: (1) Find newest: `git ls-remote --tags https://github.com/micropython/micropython.git`, filtered as
  `latest_stable_micropython_ref()` does (`setup_toolchain.py:522-537`). Precondition: a
  `micropython-rp2-rpi_pico_w-stubs` release for that X.Y.Z exists on PyPI (`https://pypi.org/pypi/
  micropython-rp2-rpi_pico_w-stubs/json`); if not, the pin moves to the newest tag that has one, and the newer tag goes to
  BACKLOG as held back ("stubs not yet published", A.SDEP.01 (4)) — the message `scripts/typecheck.sh:68-79` prints says
  the same choice ("hold toolchain/versions.toml's [micropython] ref back"). No newer tag: record "already newest" and
  skip to (5). (2) Read: the release notes of every release after v1.29.0 up to the new tag; `git log --oneline
  v1.29.0..<new> --` and `git diff v1.29.0 <new> --` for the paths this repo relies on — `py/` (`gc.c`, `vm.c`,
  `scheduler.c`, `runtime.c`, `objexcept.c`, `binary.c`, `modstruct.c`, `parse.c`, `builtinimport.c`, `objbool.c`,
  `stream.c`, `mpconfig.h`, `mkrules.cmake`, `usermod.cmake`, `manifest.cmake`), `extmod/asyncio/` (all), `extmod/
  modlwip.c`, `extmod/modselect.c`, `extmod/modtime.c`, `extmod/modjson.c`, `extmod/machine_i2c.c`, `extmod/
  machine_spi.c`, `extmod/modnetwork.c`, `extmod/network_cyw43.c`, `extmod/lwip-include/`, `extmod/extmod.cmake`,
  `extmod/vfs*.c`, `ports/rp2/` (`machine_i2c.c`, `machine_spi.c`, `machine_uart.c`, `machine_timer.c`,
  `machine_wdt.c`, `machine_pin.c`, `machine_mem_backup.c`, `modmachine.c`, `modtime.c`, `datetime_patch.c`,
  `rp2_flash.c`, `main.c`, `mphalport.c/h`, `mpconfigport.h`, `CMakeLists.txt`, `Makefile`, `lwip_inc/`,
  `boards/RPI_PICO_W/`, `boards/manifest.py`), `ports/unix/` (`unix_mphal.c`, `modsocket.c`, `modtime.c`,
  `variants/`, `Makefile`), `shared/timeutils/`, `shared/netutils/dhcpserver.c`, `mpy-cross/`; and `git diff
  --submodule=log v1.29.0 <new> -- lib/` for every moved submodule, each read for its used parts: lwIP D5 (`tcp_out.c`,
  `tcp_in.c`, `pbuf.c`, `mem.c`, `memp.c`, `init.c`'s `#error`s, `opt.h`, `dns.c`, `dhcp.c` — the B.14.2.1 ensemble),
  cyw43 D6 (`cyw43_ctrl.c`, `cyw43_lwip.c`, link status and AP paths), pico-sdk D2 (`hardware_i2c`, `hardware_spi`,
  `hardware_uart`, `hardware_watchdog`, `hardware_flash`, `pico_cyw43_arch`; picotool D4 follows it), mbedtls D7
  (catalog W03), tinyusb D8 (CDC), btstack D9 (size only), micropython-lib D10 (`neopixel`, the `bundle-networking`
  members), berkeley-db D11. Security advisories in the range (GitHub advisories for micropython/micropython) are read
  with the same scope. (3) Move: `versions.toml:10` → the new tag; `uv run toolchain/setup_toolchain.py setup` (clones
  or updates D1, derives D2/D4, builds and verifies every artefact); the stub move is A.SDEP.09; mpremote to the same
  release (A.SDEP.03). (4) The platform re-check (CLAUDE.md "Platform target" practice, in full): every Part F fact
  and every upstream `file:line` citation in SPECIFICATION.md, CLAUDE.md, BACKLOG.md, `digital_twin/README.md` and
  code comments re-read at the new tag and re-stamped or corrected; every code, test and twin claim site above
  re-verified (each fake's modelled rp2 fact — `tests/machine.py:26, :153, :205-211, :351`,
  `digital_twin/machine.py:48, :250, :368, :836` — against the new port source); each construct asked whether a newer
  or better way now exists (adoptions routed per A.SDEP.01 (5)); every ruled-out item of F.5.6 re-checked, not carried;
  the override anchors and their mechanisms (A.SDEP.11, A.SDEP.13, A.SDEP.14); the heap-map parser anchor (G4/R01; the
  `micropython.mem_info(1)` block-map format the hardware heap tests parse, `tests_hardware/harness.py`). (5) Measure:
  for every device, `.bss`, `.data` and `__GcHeapEnd - __GcHeapStart` from `firmware.elf` (B.14.2.1's method) and the
  image size against the filesystem boundary (LEAD/R07), before and after; a GC-heap change updates B.14.2.1's
  "Baseline is …" line and table header ("v1.29.0"), and SPEC H.7/I budgets that quote the heap are updated or routed to
  U30 as a delta when the change is material. (6) Hardware (phase C, never here): BACKLOG "Real-hardware work still
  owed" gains "The firmware pin moved from v1.29.0 to <new> (<date>): on `dev`, run the flash, bench and mid-soak tiers
  against a `dev` build of the new pin, redo the on-target confirmations Part F.5 records (the I2C/SPI `deinit()` device
  script, the SPI RX-overrun consequence (`device_scripts/fram_busy_status_lockout.py`), the heap-headroom test in `tests_hardware/flash/test_memory_stress.py`), check
  `sys.implementation` reports the new version, and read the FRAM logs first (owner, 2026-09-30)." F.5's
  "field-proven on the dev bench" paragraph (`SPECIFICATION.md:3683-3691`) becomes "built and verified at L0-L2; silicon
  proof owed (BACKLOG)" until phase C closes it. Check gate A.SDEP.02, every device's firmware build included.
- **Blast**: callers `setup_toolchain.py` (all subcommands), `scripts/build_firmware.py`, `scripts/test.sh`,
  `scripts/run_digital_twin_ci.sh`, `scripts/run_unix_port_integration.sh`, CI cache key (`action.yml:38` hashes
  `versions.toml`: a cold cache on the next CI run, expected) · generated every generated module is rebuilt and frozen
  with the new `mpy-cross` (the `.mpy` format version may move — `sys.implementation._mpy`) · js — · tests every tier
  (the whole point); the fakes above where a modelled fact changed; `tests_hardware` device scripts whose stated floor
  or fact changed (`bus_deinit_is_a_noop_on_real_hardware.py:26-27`) · twin `digital_twin/machine.py` modelled facts;
  `unix_port_poll_prewarm.py`/`_unix_port_udp_addr_shim.py` (catalog W12/W13) · docs the sites above; SPEC F.5 record
  (A.SDEP.21); CLAUDE.md `:17` ("what the 1.29 pin changed (Part F.5)") and `:42-49` ("Last run") (A.SDEP.21);
  `THIRD_PARTY_LICENSES.md:157-173` (the `dhcpserver.c` note re-read) · toml `versions.toml:10` · uart — (the protocol
  module uses `machine.UART`; a changed UART fact is a Class B "no C impact" entry only if `asy_uart_comm.py` or
  `asy_uart_driver.py` changes, UART_C_PORT_CHANGELOG.md) · build-environment: A.SDEP.21's BACKLOG chroot entry (a new
  pin is exactly what both chroot legs must cover); hardware: the BACKLOG entry in (6).
- **Depends**: A.SDEP.01, A.SDEP.02, A.SDEP.03 (tools first), A.SDEP.24 (corpus at the new tag).
- **Kind**: code, doc, rule, hardware

### A.SDEP.09 Install the stubs of the new pin; record the post-releases
- **Why**: LEAD/R33 — "stub packages"; OR129.a (4) "the stub repairs in `scripts/typecheck.sh` … the Timer stub gap";
  G4/R35 (stubs at the version derived from the pinned ref).
- **Site**: `scripts/typecheck.sh:64-97`; D15.
- **Change**: with D1 at its new (or unchanged) X.Y.Z, delete `typings/` (so no older tree is overlaid — the defect
  A.U21.04 fixes later) and run `scripts/typecheck.sh`; record the installed `micropython-rp2-rpi_pico_w-stubs` and
  `micropython-stdlib-stubs` versions from `typings/*.dist-info`. Even with D1 unchanged, the `==1.29.0.*` spec picks the
  newest post-release at each install, so a newer `.postN` is taken here and recorded. Read the micropython-stubs
  release notes / changelog between the old and new stub releases. Then the stub workarounds of the catalog (W08-W11,
  A.SDEP.15). New mypy findings are decided one by one (A.SDEP.02); a genuine stub regression is repaired the same way
  F.5.5's two are (conditional repair at the stub tree, never `type: ignore` in `src/`), with its own trigger.
- **Blast**: callers CI `lint-and-typecheck` · generated — · js — · tests the main mypy pass · twin — · docs SPEC F.5.5
  (names `1.29.0.post1`), CLAUDE.md `:805-821`, `:841-` (name the stub versions) · toml — (A.U27.02 later pins the
  recorded post-releases in `[stubs]`: it takes this record's versions) · uart —.
- **Depends**: A.SDEP.08.
- **Kind**: code

### A.SDEP.10 Read the derived-code upstreams for fixes to the kept parts
- **Why**: OR129 "both modules, repos and tooling, just everything … Check for opportunities, improvements, fixes we can
  profit from" (owner, 2026-09-30); SPEC F.4 (Adafruit-derived code restructured freely; `voc_algorithm.py` a literal port
  kept diffable against its reference); CLAUDE.md "When changing a sensor driver's behavior, verify against the legacy
  driver's own actually-proven field behavior".
- **Site**: D28; `THIRD_PARTY_LICENSES.md:25-106, :123-156, :175-205` (derivation records).
- **Change**: for each non-archived upstream, read its commit log since the derivation point this repo records (or,
  where none is recorded, since the file's first commit in this repo, `git log --follow --diff-filter=A`), for changes
  to the parts this repo kept: Adafruit BMP3XX / SCD30 / SGP40 (register maps, command codes, CRC, conversion formulas,
  timing), Adafruit FRAM (opcodes), micropython-lib `ntptime.py` (the `0x1B` query, epoch delta, `MIN_NTP_TIMESTAMP`),
  Sensirion `gas-index-algorithm` (algorithm constants and fixed-point steps `voc_algorithm.py` mirrors), p-doyle
  captive portal (the `DNSQuery` byte layout). Archived upstreams (jposada ISL29125, Sensirion embedded-sgp) and
  inspiration-only ones (aiodns, karfas) are recorded "archived / not a copy — nothing to take". Each upstream fix that
  applies to a kept part is verified against the chip's datasheet (CLAUDE.md datasheet rule) and becomes a delta item for
  its owning unit (U12 `voc_algorithm.py`, U15 the drivers, U16 FRAM, U18 NTP/captive DNS), never a drive-by change here;
  a formula change follows D.1's flag-don't-silently-change treatment. THIRD_PARTY entries gain nothing unless a fix is
  taken (then U34 records the new upstream reference).
- **Blast**: callers — · generated — · js — · tests — (delta items carry their own) · twin — · docs audit record;
  delta items · toml — · uart —.
- **Depends**: A.SDEP.01.
- **Kind**: rule (audit file)

### A.SDEP.11 Re-check the SIGINT override and the heap-unwedge defence
- **Why**: OR129.a (4) "the `MICROPY_ASYNC_KBD_INTR` override and the other `toolchain/micropython_overrides.py`
  anchors … the `unix_port_gc_unwedge` defence"; SPEC B.14.1 re-verification checklist (`:1211-1222`); G4/R34 (the
  unwedge helper retires once the override is proven in every binary) (owner, 2026-09-26, OR52.a (6)). Catalog W01, W02.
- **Site**: `toolchain/micropython_overrides.py:40-90` (`_UNIX_KBD_INTR_ANCHOR`, `verify_unix_kbd_intr_anchor()`,
  `apply_unix_kbd_intr_override()`); `digital_twin/unix_port_gc_unwedge.py`.
- **Change**: at the new tag, re-read `ports/unix/unix_mphal.c` `sighandler()` and `ports/unix/variants/
  mpconfigvariant_common.h` (B.14.1's checklist). Three outcomes: (a) anchor line unchanged and the immediate
  `nlr_raise()` path still the default for the standard variant → override stays, nothing else changes; (b) the line
  changed shape but the immediate path still exists → re-derive the anchor and the generated `#undef`/`#define`,
  re-run B.14.1's hammer loop (Run 3 + Run 5 at `gc.threshold=32768` across every device, the 700-iteration bar B.14.1
  records) before trusting shutdowns, and update `tests_scripts/test_micropython_overrides.py`'s fake tree; (c) upstream
  made deferred delivery the Unix default (the retirement condition B.14.1 names) → the override goes: delete
  `_UNIX_KBD_INTR_ANCHOR`, `verify_unix_kbd_intr_anchor()`, `apply_unix_kbd_intr_override()` and their calls in
  `build_unix_port()` (`setup_toolchain.py:371-372` and the `override_make_vars` splice, `:380`), the variant redirect with
  them (`build-standard` then comes from the Makefile's own `BUILD ?= build-$(VARIANT)`); B.14.1 is rewritten to "retired:
  upstream <tag> delivers SIGINT through `mp_sched_keyboard_interrupt()` by default (`<file:line>`)" in present tense;
  A.U21.06's post-build proof keeps its deferred-branch check (it then proves upstream's default), without the sentinel
  half. The unwedge helper is not decided here: its retirement is already planned on the proof, independent of upstream
  (A.U25.39 after A.U21.06); this step only confirms F.6's mechanism (`py/gc.c` collect-flag handling) is unchanged at
  the new tag or rewrites F.6 to what the tag does.
- **Blast**: callers `build_unix_port()` (three builds) · generated — · js — · tests (c): `tests_scripts/
  test_micropython_overrides.py:40-270` (`TestVerifyUnixKbdIntrAnchor`, the apply/build tests) delete or retarget;
  `:227-232` structural asserts · twin every twin run's shutdown (Run 3/Run 5) · docs B.14 intro "(so far: two
  implemented …)" count, B.14.1, F.6 amendment, CLAUDE.md `:681-695` (the shutdown-flake bullet: its fix becomes
  "upstream's default since <tag>"), BACKLOG chroot entry · toml — · uart —.
- **Depends**: A.SDEP.08; A.U21.06 and A.U25.39 follow it.
- **Kind**: code, test, doc

### A.SDEP.12 Hand the mbedtls check its facts at the new pin
- **Why**: OR129.a (4) "the GCC 14 mbedtls workaround"; G8/R21 (trigger already met at v1.29.0: mbedtls v3.6.6 carries
  the fix; removal waits only for a clean GCC ≥ 14 build, A.U21.16). Catalog W03.
- **Site**: `toolchain/setup_toolchain.py:32-35`, `:335`, `:379`; A.U21.16.
- **Change**: read the new tag's `lib/mbedtls` version (`git -C lib/mbedtls describe --tags` in the toolchain checkout)
  and confirm the `mbedtls_xor()` fix is still in it (the file `A.U21.16` names); record the version in the refresh
  record. Nothing is removed here: A.U21.16's step 1 (a GCC ≥ 14 build of both targets without the flag — a trixie
  chroot when the session can build one, else the bench Pi4 in phase C) stays the deciding test, and its planned SPEC
  B.7.1 text takes this record's mbedtls version instead of "`0bebf8b` / v3.6.6" when the pin moved (A.SDEP.23). If
  this session can build a GCC ≥ 14 chroot (CLAUDE.md recipe, trixie leg), A.U21.16 step 1 may run now and its branch
  2a/2b be applied in this step (A-C moves it); otherwise it stays in U21.
- **Blast**: callers `build_firmware()`, `build_unix_port()` · generated — · js — · tests as A.U21.16 · twin — · docs
  as A.U21.16 · toml — · uart —.
- **Depends**: A.SDEP.08.
- **Kind**: rule

### A.SDEP.13 Decide the modlwip send override against the new pin
- **Why**: OR129.a (4) "the modlwip `ERR_MEM` override (issue 19704)"; OR114.a (1), (4) "the anchor check fails the build
  when upstream changes the loop, and the override is removed once the pin carries a real fix" (owner, 2026-09-30,
  OR114); G4/R44. Catalog W04, W05, W06.
- **Site**: planned `toolchain/micropython_overrides.py` `modlwip_eagain` (A.U21.09-A.U21.14); `extmod/modlwip.c` at the
  new tag; `src/asy_webserver_service.py:255-259, :269-270` (the `peer_gone` suppression).
- **Change**: at the new tag read `extmod/modlwip.c`'s `lwip_tcp_send()` and the state of issue 19704 and PRs 19705/19708
  (and any successor). Outcomes, each recorded: (a) the pin carries a real fix (a non-blocking send returns without
  sleeping when `tcp_write()` reports `ERR_MEM` — `EAGAIN`, or a partial write/`ENOBUFS`) → A.U21.09-A.U21.11 are not
  executed (no override; the BACKLOG watch entry A.U21.09 plans is not written); A.U21.12/A.U21.13's host lwIP build and
  hammer run against the upstream code instead (OR115.a's "prove it is solved and stable" applies to the upstream fix
  unchanged); A.U19.24 is re-read against the upstream return value (`EAGAIN` vs partial write); SPEC B.14.2.1's stall
  sentence (A.U14.30) states the fix at `<tag>`; phase C's A.U21.14 reproduces on v1.29.0 firmware and proves on the new
  pin. (b) the loop changed but no real fix (e.g. upstream `6e79dcf9c`, after v1.29.0, which only swaps the sleep for
  `poll_sockets()` with a ticks-based 10 s cap, per `audit/actions/SUPP_lwip.md`) → A.U21.09's anchor texts
  (`_MODLWIP_ERR_MEM_LOOP`, `_MODLWIP_INSERT_AFTER`, the include anchor, the `extmod.cmake`/`CMakeLists.txt`/`Makefile`/
  `usermod.cmake` line numbers) are re-derived at the new tag before A.U21.09 executes (A.SDEP.23). (c) unchanged → A.U21.09
  as planned. Separately: `setsockopt(TCP_NODELAY)`'s missing NULL check and lock (`extmod/modlwip.c:1527-1535` at
  v1.29.0) is re-read; if fixed, it is recorded only — "No `TCP_NODELAY` call" is the owner's decision (OR114.a (2)), not
  a workaround this step may lift; a change would go to the owner under harmonization 1. The write-after-reset
  behaviour behind `peer_gone` (a freed pcb still accepting writes that reach `tcp_write(NULL)`) is re-read in the same
  function: if the new tag refuses writes on a closed/freed pcb with an error, the suppression's comment changes to the
  new reason (it still saves a pointless write) and the retirement is a delta for U19; if not, unchanged.
- **Blast**: callers `build_firmware()` (A.U21.10) · generated — · js — · tests A.U21.11-A.U21.13, A.U19.24,
  `tests/test_asy_webserver_service.py:1648-1660` (`peer_gone` path) · twin — · docs SPEC B.14 (A.U21.09's new
  subsection or its absence), B.14.2.1, H.7.1 (A.U14.03), CLAUDE.md "Platform target" addition A.U21.09 plans, BACKLOG
  watch entry · toml — · uart —; hardware A.U21.14, A.U26.85.
- **Depends**: A.SDEP.08; decides the shape of A.U21.09-A.U21.14.
- **Kind**: rule, code

### A.SDEP.14 Re-verify the lwIP option override's anchors and ensemble
- **Why**: OR129.a (4) "the other `toolchain/micropython_overrides.py` anchors"; SPEC B.14.2 version-bump checklist
  (`:1379-1383`); CLAUDE.md "Platform target" ("re-reading the real mechanism behind each anchor"). Not a workaround —
  a configuration override — so it has no retirement condition; listed with the anchors it depends on.
- **Site**: `toolchain/micropython_overrides.py:93-345` (21 anchors, `LWIP_MACROS_GUARDED_IN_OPT_H`,
  `LWIP_MACROS_PREDEFINED_BY_MICROPYTHON`, `check_lwip_ensemble()`, `derive_lwip_dependents()`), `:405-466` (readback);
  `toolchain/versions.toml:41-52`; `buildgen/validate.py` (per-device N-connection check).
- **Change**: at the new tag: re-read `extmod/lwip-include/lwipopts_common.h`, `ports/rp2/lwip_inc/lwipopts.h`, lwIP
  `opt.h` and `init.c`; confirm each of the 21 anchors still states the same mechanism (not only that the string
  matches); confirm each macro's guard class (guarded in `opt.h` vs predefined by MicroPython) and the atomic `MEM_SIZE`
  block; re-derive `opt.h`'s four derived formulas (`TCP_SND_QUEUELEN`, `TCP_SNDLOWAT`, `TCP_SNDQUEUELOWAT`,
  `PBUF_POOL_BUFSIZE`) and `init.c`'s `#error` set against `check_lwip_ensemble()`; confirm the readback still reads
  `flags.make`/`CMakeCache.txt` as it does. A moved macro or formula updates the tuples, the ensemble checker and
  `tests_scripts/test_micropython_overrides.py`'s fake tree and parametrized anchor cases together. Simplification
  opportunity: if every option became `#ifndef`-guarded upstream, B.14.2's "why not `CFLAGS_EXTRA`" reasoning is
  re-read and recorded; the one-header mechanism stays unless the reasons it states are all gone (then a delta for U21).
  Re-measure the B.14.2.1 cost table only if lwIP's pools changed layout (per-connection cost 2,324 B).
- **Blast**: callers `build_firmware()` · generated — · js — · tests `tests_scripts/test_micropython_overrides.py`
  (the lwIP classes, `:274-880`), `tests_scripts/test_buildgen_validate.py` (ensemble cases) · twin — · docs B.14.2,
  B.14.2.1, H.7 · toml `versions.toml:41-52` if a value must move (it moves only with its reason, OR114.a (3)) · uart —.
- **Depends**: A.SDEP.08.
- **Kind**: rule, code

### A.SDEP.15 Re-check the stub repairs and the stub-gap suppressions
- **Why**: OR129.a (4) "the stub repairs in `scripts/typecheck.sh` … the Timer stub gap"; G4/R35 (each stub workaround
  names its removal trigger; A.U27.02/A.U27.03); CLAUDE.md `:841-` ("no-op once upstream re-ships … don't replace them
  with `type: ignore`"). Catalog W08-W11.
- **Site**: `scripts/typecheck.sh:83-97`; `src/asy_bmp3xx_driver.py:152-154`, `src/asy_isl29125_driver.py:235-237`
  (bare `Timer()`), and the other bare `Timer()` sites (`asy_ntp_client.py:140-142`, `asy_scd30_driver.py:142`,
  `asy_sgp40_driver.py:162`, `asy_wifi_service.py:175`); `src/asy_wifi_service.py:244`; `src/asy_notification_service.py:25-27`;
  `digital_twin/unix_port_poll_prewarm.py:7`; the `const()`-tuple and `DeflateIO` sites A.U27.03 lists.
- **Change**: after A.SDEP.09's install, before the repairs run (comment them out in a scratch copy of the script, never
  in the tree): (W08) does `typings/stdlib/asyncio/futures.pyi` exist, or do `asyncio/tasks.pyi`/`__init__.pyi` no longer
  import from it? (W09) is `NotImplemented` declared in `typings/stdlib/builtins.pyi`? Each fixed upstream → its repair
  block goes from `scripts/typecheck.sh` and its F.5.5 paragraph and CLAUDE.md sentence are rewritten to "fixed in
  <stub version>" in present tense (or dropped with the list entry A.U27.03 adds); still broken → kept, conditional as
  today. (W10) does the board stub's `Timer.__init__` accept no `id`? Run `mypy src` alone (no `tests` in scope) — the
  12 `call-overload` findings CLAUDE.md `:822-830` records are the symptom; zero → the gap is fixed: CLAUDE.md's bullet
  and A.U27.03's B.15 row and the two driver comments go. (W11) every `# type: ignore[...]` that exists for a stub gap
  is self-checking: `warn_unused_ignores = true` fails the main pass the day a stub fixes it (e.g.
  `asy_wifi_service.py:244` `return-value`, "stub types status(str) as int"); each such failure removes that ignore (and
  its reason comment) rather than being suppressed; `import asyncio.core` (`unix_port_poll_prewarm.py:7`,
  `import-not-found`) the same. No new `type: ignore` enters `src/` for a stub regression (F.5.5 rule).
- **Blast**: callers CI `lint-and-typecheck` · generated — · js — · tests A.U27.02's `tests_scripts/test_typecheck_sh.py`
  (its fabricated trees keep all three states) · twin the twin pass · docs SPEC F.5.5, B.15 (A.U27.03's list), CLAUDE.md
  `:805-830`, `:841-` · toml — · uart —.
- **Depends**: A.SDEP.09.
- **Kind**: code, doc

### A.SDEP.16 Re-check the Unix-port rig workarounds
- **Why**: OR129 "Check especially for fixes we needed to implement workarounds for" (owner, 2026-09-30); G4/R30 (every
  Unix-port-vs-rp2 difference worked around in test code only, "recorded in Part F with source and removal trigger" —
  A.U14.28's F.7 rows); owner, 2026-09-29 (OR102.a (10)) for the `modselect.c` row's trigger ("retired when a pin
  re-check finds it fixed"). Catalog W12-W17.
- **Site**: `digital_twin/unix_port_poll_prewarm.py` (and its 15 caller/doc files); `digital_twin/_unix_port_udp_addr_shim.py`
  (7 files); `tests/machine.py` `_StepPoller` and the bounded-poller rule (CLAUDE.md `:613-621`); `scripts/test.sh:23`,
  `scripts/run_digital_twin_ci.sh:25`, `scripts/run_unix_port_integration.sh:30` (`export TZ=UTC`); the port-band scan in
  `unix_port_poll_prewarm.py:28-47`; the two Unix binaries (`setup_toolchain.py:352-397`, `scripts/test.sh:75-99`).
- **Change**: at the new tag, per workaround: (W12) `extmod/modselect.c`'s pollfds-growth pointer update still rewrites a
  poll object whose `pollfd` is `NULL`? (`digital_twin/README.md:886-918` states the trace at `:132`; re-read the loop).
  Fixed → `prewarm_poll_set()` and its calls go (16 files: the module, `run_generic_integration.py:29, :331-332`,
  `segfault_stress_repro.py:15, :81-83`, the `digital_twin/machine.py:757` comment, the eleven `tests/` importers,
  `tests/test_digital_twin_poll_prewarm.py` deleted, README "What's here"/"Known gaps" entries rewritten to "fixed in
  <tag>"), `segfault_stress_repro.py` stays only if it still has a target (else deleted with its README entry — a delta
  for U25). (W13) `ports/unix/modsocket.c` `bind()`/`connect()`/`sendto()` still require a buffer sockaddr and `recvfrom()`
  still returns raw bytes? Each quirk fixed → that half of `_unix_port_udp_addr_shim.py` goes, and the `getaddrinfo(...)[0][-1]`
  pre-resolution in the 12 `tests/`/`digital_twin/` files A.U14.28 lists goes with it. (W14) the bounded-fake rule stays
  whatever upstream does (bounded fakes are the test design, CLAUDE.md); only its stated cause is re-read. (W15)
  `ports/unix/modtime.c` `mktime()` still host-libc/`$TZ`? Fixed → the three `export TZ=UTC` lines and CLAUDE.md `:709-717`
  go. (W16) `getsockname()` added to the Unix port's socket? Then `_bind_free_listener()`'s band scan can become a port-0
  bind read back (a delta for U25/U27; the band convention of the other listeners follows). (W17) settrace still
  allocating per call when compiled in (`py/vm.c`, `py/profile.c`)? If upstream made an idle `sys.settrace` free, the two
  binaries could become one — re-measured with E.5.2's method before any change; a delta for U21/U27, not done here.
  Each finding is written as the matching F.7 row's trigger outcome (A.U14.28 executes later with these results).
- **Blast**: callers the twin runner, `scripts/test.sh`, `scripts/_digital_twin_ci_suite.py` (shim) · generated — · js —
  · tests per outcome above; `tests/test_digital_twin_sensortask_integration.py:19-23`, the six webserver-concurrency files ·
  twin every real-socket twin entry · docs `digital_twin/README.md:78-92, :747-795, :867-918`; CLAUDE.md `:613-621`,
  `:709-717`; SPEC F.6/F.7, E.3, E.5.2 · toml — · uart —.
- **Depends**: A.SDEP.08; A.U14.28, A.U25.34, A.U25.43 take the results.
- **Kind**: rule, code, test, doc

### A.SDEP.17 Re-check the MicroPython runtime facts that shape code
- **Why**: OR129.a (4) "`getaddrinfo()`'s timeout status and the `I2C`/`SPI` `deinit()` facts"; CLAUDE.md "Platform
  target" practice ("is there now a newer/better/more-complete way to do this"). Catalog W18-W28.
- **Site**: SPEC F.1 (`:3459-3560`), F.2 (`:3604-3659`), F.5.1, F.5.7-F.5.9; the code shaped by each (catalog column).
- **Change**: at the new tag, each fact re-read at its source and the code shape it forces re-judged:
  (W18) nested `asyncio.run()` — `extmod/asyncio/core.py` `run()` still `run_until_complete(create_task(coro))` on the one
  queue? A raise instead of a crash changes CLAUDE.md `:650-664`'s symptom text only; the "sync scope only" rule stays.
  (W19) async generators — `py/compile.c`/`py/objgenerator.c` still lack `__aiter__`/`__anext__`? Supported → the
  `/status` "collect into a list" form may become an async generator: a delta for U19/U30 (memory impact measured first),
  not done here. (W20) `[*a, b]` in displays, `await` in comprehensions — now compiled? The concatenation / plain-loop
  forms stay valid; F.1's text changes; a style change is not forced (delta only if a rule prefers the new form).
  (W21) `struct.pack()` silent truncation — still gated behind `MICROPY_PREVIEW_VERSION_2` in `py/binary.c`? If the
  checks became default, F.1's fact flips and the shape validations before packing stay (defence against wrong data,
  not only against the runtime). (W22) soft `Timer` callbacks — `py/scheduler.c` `mp_sched_schedule()` still drops on a
  full queue silently? `PERIODIC` for must-fire timers stays either way (C.9); the text follows the source. (W23) `[x] *
  n` segfault range — `py/objlist.c`/`py/obj.c` size check; the clamp-before-allocate rule stays; F.1's range text
  follows. (W24) `machine.UART.deinit()` still leaves `read_buffer.buf` unrooted (`ports/rp2/machine_uart.c`)? Fixed →
  the fresh-construction in `src/asy_uart_driver.py:199-207` stays correct but stops being load-bearing: its comment and
  F.5.7 are rewritten to say so. (W25) `machine.UART.read()` still waits per missing byte in `mp_event_handle_nowait()`?
  The owner's no-blocking rule (CLAUDE.md, 2026-09-11) keeps the `any()` clamp (`asy_uart_driver.py:121-123`) and the
  yield in `ready()` (`:258`) either way; F.5.8/F.5.9's mechanism text follows the source. (W26) `machine.I2C`/`SPI`
  `deinit()` — does rp2 now set the protocol `.deinit` slot, or do constructors stop returning static singletons? Either
  changes F.5.1, the wrapper comments (`asy_i2c_driver.py:183`, `asy_spi_driver.py`), both fakes (`tests/machine.py:153`,
  `digital_twin/machine.py:250`), the device script `bus_deinit_is_a_noop_on_real_hardware.py`, and the controller
  re-initialise rung of the recovery ladder (A.U13.R01) — a delta for U13/U14 with a phase-C check. (W27)
  `socket.getaddrinfo()` — any asyncio-level timeout added (`extmod/asyncio/`, `extmod/modlwip.c`)? Recorded in F.2
  (A.U14.16's text takes the new tag); no code change (the project calls it only on a numeric host). (W28) the CYW43
  `isconnected()` false positive — any upstream fix in cyw43-driver D6 or `extmod/network_cyw43.c`? Recorded in F.2 only:
  the power-cycle recovery is an owner-settled, intended feature (CLAUDE.md hard rule), not retired by an upstream fix.
- **Blast**: callers per item · generated — · js — · tests per item (the fakes, the device scripts, `tests/test_asy_uart_driver.py`,
  `tests/_uart_comm_harness.py` sync-scope rule) · twin `digital_twin/machine.py` · docs SPEC F.1, F.2, F.5.x; CLAUDE.md
  `:17-20`, `:650-664`, the UART no-blocking hard rule's mechanism sentence · toml — · uart — (a UART text-only change is
  no C impact; any change to `asy_uart_driver.py` behaviour is a Class B entry in UART_C_PORT_CHANGELOG.md).
- **Depends**: A.SDEP.08.
- **Kind**: rule, doc

### A.SDEP.18 Re-check the Microdot gaps the webserver wrapper covers
- **Why**: OR129 "Check especially for fixes we needed to implement workarounds for" (owner, 2026-09-30); CLAUDE.md
  hard rule (Microdot's behaviour is changed only by wrapping it); SPEC A.5 ("The one gap: exceptions raised while
  writing the response itself"). Catalog W29, W30.
- **Site**: `src/asy_webserver_service.py:234-291` (`_TimeoutStreamProxy`: `_bounded_read()` read-timeout logging
  `:248-260`, header coalescing in `awrite()` `:268-278`), `:692-731` (`_serve()`'s write-phase catches).
- **Change**: at the Microdot tag A.SDEP.06 vendors: (W29) does `Response.write()` still emit the status line and each
  header as separate writes? If upstream now writes the header block in one call, the coalescing in `awrite()` is no
  longer needed: `_head` and its branch go, and `tests/test_asy_webserver_service.py:1977`'s "the whole header block is
  one write" assertion stays true through upstream (it pins the property, not the mechanism) — kept; SPEC I.3's
  "cut response never ends mid-headers" text states the upstream behaviour. (W30) does `dispatch_request()`/
  `handle_request()` still swallow read-phase exceptions (so a read timeout is observable only in the proxy) and let
  write-phase exceptions escape (A.5's one gap)? A change moves the logging point: the proxy's read-timeout log or
  `_serve()`'s write-timeout log is removed where Microdot now reports it through a hook this repo registers — decided
  against OR35.b/OR56.a (1) "one event, one entry", tested by the existing timeout tests; a delta for U19 if the change
  is more than removing a now-dead branch. Unchanged → recorded, nothing moves.
- **Blast**: callers `WebserverService._serve()` · generated — · js — · tests `tests/test_asy_webserver_service.py`
  (`:1648-1660`, `:1977`, the per-call-timeout tests), `tests/_webserver_concurrency_scenarios.py`, the twin
  webserver-concurrency files · twin as tests · docs SPEC A.5, I.3, H.7.1 · toml — · uart —.
- **Depends**: A.SDEP.06.
- **Kind**: rule, code

### A.SDEP.19 Re-check the CI and web-tooling workarounds
- **Why**: OR129.a (4) "zizmor's `self-repository` disable (actionlint syntax support)"; CLAUDE.md `:496-499`, `:588-603`
  (the `uv sync` retry: "Don't 'simplify' the retry away"); SPEC H.7 (engine channels), H.8 (coverage exclude). Catalog
  W32-W35.
- **Site**: `.github/zizmor.yml:11-18`; the nine `uses: ./.github/actions/setup-micropython-toolchain` sites (`ci.yml:123,
  173, 217, 290, 436, 467, 490, 583, 616`); the `uv sync` retry loops (`action.yml:22-30`; `ci.yml:326-335, 355-362,
  381-388, 406-413, 439-447, 493-501`; `setup_toolchain.py` `run_retried(["uv", "sync"])`, `:1019`); `vitest.config.js:30-38`;
  `scripts/setup_cross_browser_toolchain.sh:17-56`.
- **Change**: (W32) with the refreshed actionlint (A.SDEP.03): does it accept `uses: $/.github/actions/…` (the form
  zizmor's `self-repository` audit asks for)? Yes → the nine local `uses:` move to that form, the `self-repository`
  block in `zizmor.yml` goes, CLAUDE.md `:496-499`'s sentence goes (A.U28.14/A.U28.40 rewrite that bullet and the file
  header — they take this outcome); both gates must pass together. No → recorded, unchanged. (W33) does `actionlint-py`
  now ship a wheel carrying the binary (no build-time download)? The retries stay either way (CLAUDE.md: they guard any
  third party's outage during `uv sync`); only the reason text in CLAUDE.md `:588-603`, SPEC B.10 and `action.yml:19-21`
  is updated if the named example stopped being true. (W34) does `@vitest/coverage-v8` still re-parse non-JS files V8
  reported? Fixed → `exclude: ["**/*.json"]` goes with its comment and `tests_scripts/test_js_coverage_excludes_json.py`,
  SPEC H.8's sentence rewritten; the `htmlcov_js` directory choice is not an upstream defect (the `coverage/` shadowing
  is this repo's layout) and stays. (W35) the engine channels: is Ubuntu's `firefox` still a snap-only stub, and is
  Playwright's own Firefox/WebKit reachable from the sessions' network? The channel choice stays unless both reasons are
  gone (then a delta for U28); the engines stay unpinned (G8 contradiction 6), so "refresh" here means a fresh install
  (the CI cache key suffix `cross-browser-firefox-v1` bumped, `ci.yml:305`) and a passing smoke.
- **Blast**: callers CI jobs · generated — · js `vitest.config.js` · tests `tests_scripts/test_js_coverage_excludes_json.py`,
  `tests_scripts/test_setup_cross_browser_toolchain_sh.py`, A.U28.08's workflow-rule checks (take the `uses:` form) ·
  twin — · docs CLAUDE.md `:496-499`, `:588-603`; SPEC B.10, B.10.1, H.7 `:4698-4712`, H.8 · toml — · uart — ·
  build-environment: A.SDEP.21's BACKLOG chroot entry (CI config).
- **Depends**: A.SDEP.03, A.SDEP.04, A.SDEP.05.
- **Kind**: code, doc

