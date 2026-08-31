# Sensor Framework

A generic asyncio-based sensor framework for **Raspberry Pi Pico W (1st gen, RP2040)** boards
running **MicroPython**, currently applied to room air-quality monitoring. Each physical unit
reads sensors over I2C/SPI, exposes a REST API plus a small web UI, persists frequently-changing
data to an external FRAM chip, and persists configuration to a JSON file on the onboard flash
filesystem. Code ships as frozen bytecode compiled into the MicroPython firmware, not loaded from
the device filesystem at runtime.

**5 units are currently deployed**: `arzi`, `wozi`, and three physically-identical-to-arzi units
sharing the `neu` build (same sensors, different GPIO wiring). `dev` is a bench/test rig only.

| Config | Sensors | FRAM | Watchdog | HTML source |
|---|---|---|---|---|
| arzi | SCD30 (CO2/temp/hum), SGP40 (VOC) | yes | active (8000ms) | `html_raw/arzi` |
| neu ×3 | same as arzi, different pin assignments | yes | active | `html_raw/arzi` (reused) |
| wozi | SCD30, SGP40, BMP388 (pressure/temp) | yes | active | `html_raw/wozi` |
| dev | SCD30, SGP40, SHTC3, MPRLS, ISL29125 | no | disabled | `html_raw/dev` (bench rig) |

## Repository layout, architecture, refactor status, and the build process

**Moved to [`SPECIFICATION.md`](SPECIFICATION.md)**, the project's central specification document
— Part A (repository layout, architecture at a glance, refactor status) and Part B (toolchain
internals + building this project's firmware). This section used to hold all of that content
directly; it's now a pointer, as part of a first-pass doc-scatter cleanup that consolidated
`DRIVER_SPEC.md`, `src/README.md`, `tests/README.md`, `toolchain/README.md`, and these sections
into one place. See "Further reading" below for the complete doc map.

Everyday build commands, unchanged:

```sh
uv run toolchain/setup_toolchain.py              # first-time setup / everyday re-run (see SPECIFICATION.md Part B)
uv run toolchain/setup_toolchain.py --latest      # detect + pin + install newest stable MicroPython
uv run toolchain/setup_toolchain.py test          # offline re-verify an existing install (~30s)
```

## Dev environment setup (generic / flash / bench)

`toolchain/setup_toolchain.py`'s `env` subcommand sets up one of three tiers, each a strict
superset of the one before it:

| Tier | Adds on top of the previous tier | Command |
|---|---|---|
| generic | Python (`uv sync`) + website (`npm ci`) deps, the firmware/Unix-port toolchain above | `uv run toolchain/setup_toolchain.py env --tier generic` |
| flash | Non-root USB serial access (`dialout` group) + an auto-detected real RP2040/Pico W board | `uv run toolchain/setup_toolchain.py env --tier flash` |
| bench | A real WiFi bridge/AP on this host (NetworkManager), so a flashed board reaches genuine internet/NTP | `uv run toolchain/setup_toolchain.py env --tier bench` |

Every tier needs only itself run once on a given host — `flash`/`bench` call straight through to
the tier(s) below rather than needing them run separately first. apt packages, `dialout` group
membership, and the `bench` NetworkManager bridge/AP all install/configure automatically via
`sudo` (pass `--skip-apt` to opt out of all of them). USB device detection (by Raspberry Pi's USB
vendor ID) and network interface detection (uplink = default-route interface, WiFi = a free
adapter that isn't the uplink) are automatic but overridable with `--device`/`--uplink-iface`/
`--wifi-iface` if a host has more than one candidate and auto-detection is ambiguous. `bench` is
idempotent: re-running it against an already-configured bridge reports the existing AP's SSID
rather than recreating (and re-randomizing) it — see `dev_legacy/README.md`'s WiFi/NTP/DNS section
for the manual `nmcli` recipe this automates, including the Pico W `cyw43439`-specific WPA2/PMF
tuning it applies.

## Code quality tooling

Ruff and mypy checks, scoped to `src/`, `tests/`, and `digital_twin/` (the
pre-refactor codebase — `python/`, `modules/` — isn't covered yet), plus unit tests for `src/`, can
be run manually. Needs Python 3.11+ (`tomllib`, stdlib only since 3.11 — `uv sync` enforces this
automatically via `pyproject.toml`'s `requires-python`, so this only matters if `uv` has to fall
back to whatever `python3` it finds):

```sh
uv sync                    # one-time, and after pulling changes - installs ruff/mypy/pytest into .venv
source .venv/bin/activate  # scripts/lint.sh and scripts/typecheck.sh assume ruff/mypy are already on PATH

scripts/lint.sh            # ruff check
scripts/typecheck.sh       # mypy, using MicroPython stubs matching toolchain/versions.toml (see above)
scripts/test.sh            # runs every test in tests/, under a real MicroPython Unix-port interpreter -
                            # builds that interpreter automatically on first run (see SPECIFICATION.md Part E) -
                            # plus tests_scripts/, a CPython/pytest suite covering the host-only build
                            # tooling (scripts/build_frozen_html.sh, build_website.sh, build_firmware.py)
scripts/test.sh --coverage # same, plus a src/-only line coverage report (HTML/XML/markdown) - see below
```

All three (`lint.sh`/`typecheck.sh`/`test.sh`) run in GitHub Actions CI
(`.github/workflows/ci.yml`) on every push/PR, plus `test.sh --coverage` as a non-gating extra
step. Config lives in the root `pyproject.toml`; see CLAUDE.md's "Code quality tooling" section
for the full rationale (why `ruff format` isn't used, why the MicroPython stubs install into a
separate `typings/` directory instead of the main dev venv, why tests don't run under
pytest/CPython, etc.).

### Test coverage

```sh
scripts/test.sh --coverage
```

Reports `src/`-only line coverage; non-gating, never fails the build. Full pipeline, output paths,
and CI behavior (Job Summary, build artifact, Codecov status): **moved to
[`SPECIFICATION.md`](SPECIFICATION.md) Part E.5, "Coverage"**.

## Website tooling (JS/HTML/CSS)

The website source (`html/`, `js/`, `tests_js/` — see [`SPECIFICATION.md`](SPECIFICATION.md) Part H
for its architecture) has its own dev-tooling stack, the JS/HTML/CSS equivalent of the Python
side's ruff/mypy/pytest above: ESLint (lint), TypeScript `checkJS` mode
(type-checks JSDoc annotations in plain `.js`, no transpilation), Vitest in real-browser mode
(Playwright + Chromium, not jsdom — same "real engine over a shim" principle as running Python
tests under a real MicroPython Unix-port interpreter), html-validate, and Stylelint. Needs Node
(version pinned in `.nvmrc`; `nvm use` or any Node manager that reads it will pick the right one)
and npm:

```sh
npm ci                            # one-time, and after pulling changes - installs into node_modules/ from package-lock.json
npx playwright install chromium   # one-time - only if `npm test` reports a missing browser executable
                                   # (a Claude Code web-session sandbox has this pre-installed already)

npm run lint           # ESLint (js/, tests_js/)
npm run typecheck      # tsc --noEmit (checkJS over js/, tests_js/)
npm run lint:html      # html-validate (html/*.html)
npm run lint:css       # Stylelint (html/*.css)
npm test               # Vitest, real-browser mode (Playwright/Chromium) - tests_js/*.test.js
npm run preview        # serves the repo root locally (python3 -m http.server 8000)
```

`web-cross-browser-smoke`'s check (real WebKit/Firefox/Edge, not just Vitest's own Playwright/Chromium)
needs the MicroPython Unix port and the real website built first, then its own one-time browser install:

```sh
uv run toolchain/setup_toolchain.py        # one-time - builds the MicroPython Unix port (see above)
scripts/build_website.sh wozi              # build the real website into frozen_modules/frozen_html.py
scripts/setup_cross_browser_toolchain.sh   # one-time - installs real WebKit/Firefox/Edge
node scripts/cross_browser_smoke.mjs       # drives the real site through all of them, desktop + mobile
```

`npm run preview`, then open `http://localhost:8000/html/index.html?device=wozi` (or `?device=dev`),
opens the locally-viewable prototype — the real `html/`+`js/`
tree against a fake in-browser backend (`js/mock-server.js`, `mockdata/*.json`), driven by one of
two worked-example `html/definitions/*.json` files. The `?device=` switch is a prototype-only
convenience (see `js/app.js`'s own docstring) — real firmware always serves exactly one
definitions.json, never branches on a query param.

All five CI-covered checks run in GitHub Actions CI (`.github/workflows/ci.yml`'s `web-lint-and-typecheck`/
`web-unit-tests` jobs), gated by a `dorny/paths-filter` job so they only run when `html/`, `js/`,
`tests_js/`, or their own tooling configs actually change — alongside, not replacing, the Python
jobs above, which keep gating on Python paths exactly as before. Config lives at the repo root
(`eslint.config.js`, `tsconfig.json`, `vitest.config.js`, `.htmlvalidate.json`,
`.stylelintrc.json`); see `SPECIFICATION.md` Part H.8 for the full role mapping and rationale. Vitest's
browser mode needs an actual Chromium install — CI installs its own via `playwright install`; see
the `npx playwright install chromium` line above if `npm test` reports a missing browser executable
locally.

A separate CI job, `web-cross-browser-smoke`, drives the real site through real WebKit, real
Firefox, and real Microsoft Edge too (not just Vitest's own Playwright/Chromium) — one field
edit+apply per engine, at both a desktop and a mobile-sized viewport, against a real booted digital
twin. Vitest's browser mode can't reach any of these itself (it's wired to a single Playwright
provider, which can only automate Chromium-family browsers), so this runs as a standalone script,
`scripts/cross_browser_smoke.mjs`, rather than a Vitest test file — see `SPECIFICATION.md` Part
H.7's "Cross-browser coverage" for the full account of why and how.

## Building real firmware

`scripts/build_firmware.py <device>` assembles a real, deployable `firmware.uf2` from `src/` +
`ext/microdot.py` + the real website (`html/`+`js/`, staged by `scripts/build_website.sh`) for one
device. Build-only, like every other RP2 build this project's tooling produces — nothing here
flashes or tests real hardware. Needs the toolchain already installed
(`uv run toolchain/setup_toolchain.py`, see above):

```sh
uv run scripts/build_firmware.py wozi                                   # -> build/firmware-wozi.uf2
uv run scripts/build_firmware.py wozi --output build/my-firmware.uf2    # explicit output path
uv run scripts/build_firmware.py wozi --jobs 8                          # override parallel make jobs
```

`<device>` must match an `html/definitions/<device>.json` file (`wozi` today — the only variant
`src/` currently assembles). Under the hood this also stages and freezes the real website for that
one device, runnable on its own for just that step:

```sh
scripts/build_website.sh wozi                                 # -> frozen_modules/frozen_html.py
scripts/build_website.sh wozi build/frozen_website_wozi.py    # explicit output path
```

`.github/workflows/ci.yml`'s `firmware-build-verify` job runs the real `build_firmware.py` build on
every push/PR; `scripts/test.sh` (above) covers both scripts' own logic fast and offline via
`tests_scripts/` instead of repeating the multi-minute real compile every run — see
`tests_scripts/test_build_firmware.py`'s `RUN_SLOW_FIRMWARE_BUILD=1` opt-in for running that real
compile locally.

## Real hardware access (mpremote)

`mpremote` (dev dependency, installed by `uv sync`) talks to a real RP2040/Pico W over its USB
serial port for flash-free iteration: `exec`/`run`/`ls`/`cat` execute or read against the device
without writing flash, unlike `cp`/`rm`/`mkdir`/`rmdir`, which do. `scripts/mpremote_connect.sh`
wraps `uv run mpremote connect <device>` with a default device path of `/dev/ttyACM0`, overridable
via `MPREMOTE_DEVICE`:

```sh
scripts/mpremote_connect.sh ls                                  # list the device's filesystem
scripts/mpremote_connect.sh exec "import sys; print(sys.implementation)"   # RAM-only REPL exec
scripts/mpremote_connect.sh run some_script.py                  # run a local script from RAM
MPREMOTE_DEVICE=/dev/ttyACM1 scripts/mpremote_connect.sh ls     # different serial device
```

Non-root serial access needs the connecting user in the `dialout` group (`sudo usermod -aG dialout
$USER`, then re-login) and a real board plugged in — both checked/added automatically, including
USB-vendor-ID auto-detection of which `/dev/ttyACM*` is the board (still pass it as
`MPREMOTE_DEVICE` yourself, or override with `--device` if more than one is plugged in), by
`uv run toolchain/setup_toolchain.py env --tier flash` (see "Dev environment setup" above). This
is a genuinely different tier from the mocked `tests/` suite (which
runs under the Unix port against `tests/machine.py`'s fake `machine` module — see
`SPECIFICATION.md` Part E) and from `scripts/build_firmware.py` (which builds a `.uf2` but never
flashes or touches real hardware, see above). Real-hardware-in-the-loop testing against a physical
bench unit — full workflow, including a frozen-firmware full-system bring-up and a bridged-AP
WiFi/NTP/DNS integration setup — is documented as its own single source of truth in
`dev_legacy/README.md` (see "Further reading" below).

## Digital twin (hardware simulator)

`digital_twin/` is a fake `machine`/`network`/`neopixel` implementation that mirrors the real `wozi` bus wiring — real-time-firing
`Timer`s, randomized-but-plausible sensor values, and a scripted `WLAN` connect sequence — so driver
code can run under the real MicroPython Unix-port interpreter with no physical hardware attached.
Its default wiring (`scripts/run_unix_port_integration.sh`, `scripts/run_digital_twin_ci.sh`) serves
the real, production `wozi` website (`scripts/build_website.sh wozi`), not the `html_stub`
placeholder — see `SPECIFICATION.md` Part H.7 for the full account.

**Quick start: twin + real website, in one command** (builds the MicroPython Unix port and the
website automatically if either is missing, then serves both forever):

```sh
scripts/run_unix_port_integration.sh --host 127.0.0.1 --port 8080
```

Then open `http://127.0.0.1:8080/` in a browser — that's the real `html/`+`js/` site, driven by the
real REST API, backed by the twin instead of physical hardware. See "Manual baseline verification
walkthrough" below for a longer copy-paste sequence that also exercises every endpoint and
fault-injection flag over `curl`.

Start the twin's standalone CLI demo (no website, twin only) directly with the same Unix-port binary
`scripts/test.sh` builds:

```sh
$HOME/pico-toolchain/micropython/ports/unix/build-standard/micropython digital_twin/launch.py \
    --seed 42 --duration 3 --no-wdt-feed --wifi-outcome success --fault scd30:writeto:1
```

(use `$PICO_TOOLCHAIN_DIR` instead of `$HOME/pico-toolchain` if you've overridden it — see
`scripts/test.sh`'s own `toolchain_dir` resolution for the exact path; run
`uv run toolchain/setup_toolchain.py` first if the binary doesn't exist yet). All flags are optional
and repeatable where noted:

- `--seed N` — seed every chip's random value walk for a reproducible run.
- `--duration SECONDS` — exit after a fixed run instead of looping forever (Ctrl-C also works).
- `--no-wdt-feed` — stop feeding the watchdog, to watch it actually trip.
- `--fault DEVICE:OP[:TIMES]` (repeatable) — script a one-shot/N-shot bus fault, e.g.
  `--fault scd30:writeto:2`. See `digital_twin/launch.py`'s own `_FAULT_DEVICE_OPS` for every valid
  `DEVICE:OP` pair.
- `--wifi-outcome OUTCOME` (repeatable) — queue a `WLAN.connect()` outcome:
  `success`/`no_ap`/`wrong_password`/`connect_fail`.
- `--fram-state-path PATH` — persist the FRAM twin's contents to a JSON file across runs, instead of
  in-memory only.

This standalone launcher is twin-only (no `src/` import). To instead run the real
`src/sensortask_wozi.py` prototype against the twin, see `digital_twin/README.md`'s own
"Swapping the twin in for a Unix-port run" section — that's a separate `MICROPYPATH`-based
invocation, not this launcher.

Full reference — what's simulated and how, FRAM persistence, running the twin's own unit tests, and
adding a new chip fake when a new sensor driver lands: **`digital_twin/README.md`**.

### Manual baseline verification walkthrough

A copy-paste sequence for manually checking the real assembled system (`src/sensortask_wozi.py`,
unchanged) against the digital twin, end to end, over real HTTP — the same walkthrough used to
establish this project's own known-working baseline (build → boot → set log level → reboot with
that level persisted → boot again with bus faults injected). Run each block from the repo root;
`curl` and a browser both work against `http://127.0.0.1:8080` while a run is up.

**1. Fresh build and boot** (`--soak` runs a built-in 20-cycle soak across every endpoint before it
starts serving — watch for a `PASS` line; omit it for a plain launch straight into serving, the same
as a real rp2040 boot):

```sh
rm -rf digital_twin/config digital_twin/fram_state.json   # start from a clean, unconfigured device
scripts/run_unix_port_integration.sh --host 127.0.0.1 --port 8080 --soak
```

Leave this running in its own terminal. In a second terminal, walk every GET endpoint plus the
real website (`scripts/run_unix_port_integration.sh` builds and serves the real `wozi` site by
default — not the `html_stub` placeholder, see "Digital twin" above):

```sh
curl -s http://127.0.0.1:8080/measurements | python3 -m json.tool
curl -s http://127.0.0.1:8080/sensors | python3 -m json.tool
curl -s http://127.0.0.1:8080/networking | python3 -m json.tool
curl -s http://127.0.0.1:8080/system | python3 -m json.tool
curl -s http://127.0.0.1:8080/notification | python3 -m json.tool
curl -s http://127.0.0.1:8080/status | python3 -m json.tool
open http://127.0.0.1:8080/   # the real website - a browser (not curl) is the useful way to view it
```

**2. Set the log level to `all` (5) via the real API, then reboot to see a full startup log.**
`DebugLevel` is a persisted `/system` setting (0-5, see `print_log.py`'s `PrintLog.level_*()`
methods) — like every config write, it's saved to disk immediately, and takes effect immediately
too: `system_service.py`'s `set_level_setters()`/`_apply_level()` registry pushes any accepted
`DebugLevel` write straight out to every other already-constructed module's own
`PrintLog.set_level()`, live, no reboot required (confirmed directly — a running twin's console
starts emitting full per-cycle event traces the instant the PUT below lands). The reboot that
follows is only to *see the early boot sequence itself* at full verbosity — construction/wiring
order, FRAM chunk allocation, task/timer startup — since those specific events already happened,
at the old level, before this PUT ever landed:

```sh
curl -s -X PUT -H "Content-Type: application/json" -d '{"DebugLevel": 5}' http://127.0.0.1:8080/system
curl -s http://127.0.0.1:8080/system   # confirm it reads back as 5
```

Now stop the running twin with **Ctrl-C in its own terminal** (a real `SIGINT` — this is what
`run_wozi_integration.py`'s own `except KeyboardInterrupt:` catches, letting its `finally` block
flush the FRAM twin's state to disk before exiting; a hard `kill`/`pkill` skips that cleanup, same
as it would skip any unsaved state on real hardware). Then boot again the same way as step 1, but
**without** wiping `digital_twin/config/` this time (that's the whole point — the persisted
`DebugLevel` survives):

```sh
scripts/run_unix_port_integration.sh --host 127.0.0.1 --port 8080 --soak
```

This boot's own console output is now the full verbose trace — every `PrintLog.evt()`/`.one()`/
`.all()` call, not just warnings/errors, across every module (FRAM chunk allocation, WiFi hotspot
fallback, NTP sync attempts, task/timer startup sequencing, ...).

**3. Exercise every PUT endpoint and check persistence.** Ctrl-C first if the level-5 instance from
step 2 is still up (same log-verbosity note applies to whatever ships next), then repeat step 1's
boot, and try:

```sh
curl -s -X PUT -H "Content-Type: application/json" \
  -d '{"SSID": "MyNetwork", "PW": "hunter2pw", "Country": "DE", "Hostname": "wozi-test"}' \
  http://127.0.0.1:8080/networking
curl -s -X PUT -H "Content-Type: application/json" -d '{"GMTOffset": 3600, "DSTOffset": 3600}' \
  http://127.0.0.1:8080/system
curl -s -X PUT -H "Content-Type: application/json" \
  -d '{"WarnCO2": 1500, "WarnVOC": 300, "WarnHum": 60.0}' http://127.0.0.1:8080/notification
curl -s -X PUT -H "Content-Type: application/json" \
  -d '{"SCD30": {"MeasInt": 4}, "SGP40": {"BackupPeriod": 2}, "BMP3XX": {"SampleInterv": 3}}' \
  http://127.0.0.1:8080/sensors
```

Every field type is checked strictly against its schema — a JSON integer where a `"float"` field is
declared (e.g. `60` instead of `60.0`) is correctly rejected as `"Invalid"`, not a bug; send a real
decimal point for float-typed fields (`WarnHum`/`TempOffs`/`Interv`/`FlashDur`, ...). Read each
endpoint back (`curl -s http://127.0.0.1:8080/<endpoint>`) to confirm the write took, then Ctrl-C
and boot once more without wiping `digital_twin/config/` (nor `digital_twin/scd30_state.json`, this
entry point's own default persisted path) to confirm it survived the restart — including SCD30's
own NVM-backed fields (`MeasInt`, `TempOffs`, ...), which `digital_twin/_scd30_chip.py` persists the
same explicit-flush way `_fram_chip.py` does (see `digital_twin/README.md`'s "SCD30 persistence"
section).

**4. Repeat with bus fault injection, and confirm recovery.** `--fault DEVICE:OP[:TIMES]` (see the
"Digital twin" section above for the full flag reference) queues a bounded, self-clearing failure
on a specific bus operation - the affected sensor's reader task should fail, log it, and recover on
its own once the fault count is exhausted:

```sh
rm -rf digital_twin/config digital_twin/fram_state.json
scripts/run_unix_port_integration.sh --host 127.0.0.1 --port 8080 \
    --fault scd30:writeto:2 --fault sgp40:readfrom_into:2 --fault bmp3xx:readfrom_mem:2 --fault fram:write:2
```

Watch `/status`'s `errcount` section for each affected module's counter to tick up, then confirm
`/measurements` still returns plausible readings from every sensor once the run has been up for a
few seconds — that's the fault having fired, been logged, and recovered from. A device-wide
task-failure streak beyond `system_service.py`'s own threshold triggers a real reboot request too
(logged as `SYSTEM ... reboot triggered!` at `DebugLevel >= 4`) - on real hardware this actually
restarts the unit; the twin can't do that (`machine.reset()` raises `SimulatedReset` instead, which
is expected and harmless - see `SimulatedReboot`'s own comment in `digital_twin/machine.py`), so the same process keeps serving
afterward instead of restarting, which is fine for continuing this walkthrough.

## Further reading

Every supporting doc in the repo, in one place — added to as a first pass at pulling scattered
specs/guidelines into a single map rather than leaving them locatable only by cross-reference.
When a new doc is added, add it here too instead of letting the map go stale again.

**Standing operating docs** (permanent, kept current):

- **CLAUDE.md** — AI-session operating constraints: hard rules, working agreements, PR workflow,
  pre-push verification. Start here for how AI sessions should operate in this repo. Its former
  Platform-target/Architecture-reference/Microdot content now lives solely in `SPECIFICATION.md`
  (Parts F/A.4/A.5) — CLAUDE.md carries short pointers to those spots instead of restating them,
  so read `SPECIFICATION.md` directly for that material (see its front matter for the tradeoff
  this creates: that content is no longer auto-loaded into every session for free).
- **BACKLOG.md** — active open questions, not-yet-done refactor targets, and deferred/out-of-scope
  work; see its own opening paragraph for the full scope. Resolved items move into this file or
  CLAUDE.md instead of staying there — it's working memory, not a changelog.

**The central specification** (permanent, code-facing):

- **[`SPECIFICATION.md`](SPECIFICATION.md)** — the single central specification document:
  repository/architecture overview, the toolchain/build-environment installer, the sensor driver
  architecture spec, the `src/` production-quality checklist, testing & coverage,
  MicroPython/RP2040 platform-target facts, the cross-cutting shared-pattern/primitive-reuse
  catalog, and the website's own architecture — all in one place, organized into lettered Parts
  (A-H) for different needs. Produced by a first-pass doc-scatter cleanup that merged
  `DRIVER_SPEC.md`, `src/README.md`, `tests/README.md`, `toolchain/README.md`, most of this
  file's former "Repository layout"/"Architecture at a glance"/"Refactor in progress"/"Build
  process" content, and the spec-shaped parts of `CLAUDE.md`/`BACKLOG.md` into one document. Start
  here for "how does this codebase actually work" or "what shape should a new driver's code take."
  `DRIVER_SPEC.md`, `src/README.md`, `tests/README.md`, and `toolchain/README.md` were deleted once
  every reference to them elsewhere in the repo (docs and code comments alike) was repointed
  directly at `SPECIFICATION.md`'s Parts C, D, E, and B respectively — they held no content of
  their own by then, just a "moved here" pointer.

**`DEVICE_REFERENCE.md`** (permanent, end-user-facing):

- **[`DEVICE_REFERENCE.md`](DEVICE_REFERENCE.md)** — notes for configuring/operating a deployed
  unit (Neopixel LED signal legend, SGP40 FRAM backup config semantics), not architecture/AI-session
  material — kept separate from README.md/CLAUDE.md/SPECIFICATION.md for that reason.

**`LICENSE` / `THIRD_PARTY_LICENSES.md`** (permanent, legal):

- **[`LICENSE`](LICENSE)** — this project's own license (MIT).
- **[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md)** — every piece of vendored or
  attribution-derived third-party code in one place (Microdot, freezefs, the Adafruit-derived
  sensor drivers, the DFRobot-derived VOC algorithm port), plus the one area where a specific
  source couldn't be established (`captive_dns.py`/`asy_ntp_client.py`/`asy_udp_socket.py`) and a
  disclosure that parts of this codebase were written with AI assistance.

**`digital_twin/README.md`** (permanent, not yet folded into `SPECIFICATION.md`):

- **`digital_twin/README.md`** — the standing reference for the hardware simulator: what's there,
  how to swap it in for a Unix-port run, FRAM/SCD30 persistence, running its own tests, and how to
  add a new chip fake when a new sensor driver lands (required per `SPECIFICATION.md` Part C.11
  point 9). Its own lifecycle isn't yet settled (still genuinely useful, but a later session may
  decide to fold it into `SPECIFICATION.md` the way `src/README.md`/`tests/README.md` were) —
  listed here for now so it isn't only locatable by cross-reference in the meantime. See
  `SPECIFICATION.md` Part A.10 for how it fits into the rest of the architecture.

**`dev_legacy/README.md`** (permanent, kept current):

- **`dev_legacy/README.md`** — the single source of truth for the physical "dev" RP2040 bench
  unit: wiring, chip identities, confirmed-working status (per peripheral and for the full
  assembled system), current bench state, the `mpremote` workflow for testing `src/` drivers
  against it (see "Real hardware access (mpremote)" above), building/flashing a frozen firmware for
  a full-system bring-up, and the bridged-AP setup for real WiFi/NTP/DNS integration testing — see
  that file itself for specifics, not restated here. Also holds, in its own clearly-marked final
  section, a historical, frozen-in-time snapshot of this unit's onboard filesystem from 2026-08-27
  (back when it still ran 1.24.1) — reference material for future `src/` promotion work, not
  itself reviewed, promoted, or covered by lint/type/test config.

`WIRING_CONTRACT.md`, `FINAL_WIRING_PLAN.md`, and `WEBSITE_PLAN.md` — temporary planning docs for,
respectively, the `improved-quality/` → `src/` wiring effort (`src/sensortask_wozi.py`'s
construction restructure, generic webserver/API service, digital-twin simulator, website placeholder
scaffold, full Unix-port integration, and the self-healing-system failure-mode audit) and the
JS/HTML/CSS website redesign — were each deleted once their effort merged back. Everything permanent
they settled was migrated into `SPECIFICATION.md` first: `WIRING_CONTRACT.md`/`FINAL_WIRING_PLAN.md`'s
construction order/FRAM-chunk order/dependency graph/debug-level registry (Part A.7), the REST API
endpoint reference (Part A.8), the website-stub/frozen-HTML pipeline (Part A.9), the digital-twin
pointer (Part A.10), and two new checkable conventions found during the audit (the
silent-failure-masking and cascading-recovery-storm rules, Parts C.7/C.9); `WEBSITE_PLAN.md`'s
settled website architecture (Part H) and its `src/`-based firmware-assembly pipeline (Part B.11) —
plus, in both cases, a handful of still-open items folded into `BACKLOG.md`. `AUDIT_PLAN.md`, the
master action list for the earlier full `src/` audit, was deleted the same way once that audit
closed — everything permanent it
settled was migrated into `SPECIFICATION.md` (the style-guideline harmonization it drove lives in
Parts C/D) first.
