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

## Repository layout

```
html_raw/               Hand-written HTML/CSS/JS for the web UI, per device config
  arzi/, dev/, wozi/       device-specific pages
  general/                 shared assets (style.css, functions.js, favicon.ico, nettimeconfig.html)
modules/                Auto-started entry points, one set copied into the firmware build per device
  _boot.py                 mounts the flash filesystem, then starts the sensor task
  sensortask-{arzi,dev,neu,wozi}.py   per-device application (renamed to sensortask.py at build time)
python/
  CommonDrivers/          shared across all device configs, always copied into the build
  IndividualDrivers/      only copied in if a given device config needs them
  Manifest/manifest.py    MicroPython freeze manifest used by the build
improved-quality/        WIP refactor target (out of scope for day-to-day work; see CLAUDE.md)
src/                     Files moved out of improved-quality/ once fully reviewed/tested
tests/                   Unit tests for src/, run under a real MicroPython interpreter - see
                          tests/README.md
toolchain/               MicroPython/pico-sdk/picotool build-environment installer
  versions.toml             single source of truth for the target MicroPython version - see
                            "Toolchain setup" below for how everything else derives from it
  setup_toolchain.py        `setup`/`test` - builds RP2040 firmware and the MicroPython Unix port (for tests/)
build-{arzi,dev,neu,wozi}.sh   per-device build scripts
update_and_install.txt   handwritten toolchain setup notes (MicroPython/pico-sdk/picotool)
pyproject.toml           dev-tooling config (ruff/mypy/pytest/uv) - see "Code quality tooling" below
scripts/                 lint.sh / typecheck.sh / test.sh - manual code-quality check runners
.github/workflows/       CI: runs lint.sh/typecheck.sh/test.sh on every push/PR
```

## Architecture at a glance

- **Sensor Reader/Driver split** — every `IndividualDrivers/asy_<chip>_driver.py` has a low-level
  chip driver (register-level I2C/SPI calls, several adapted from Adafruit CircuitPython
  libraries) plus a `*_Reader` wrapper providing the common async-task surface
  (`start_asy_read()`/`start_asy_trigger()`/`start_timer()`, a lock-protected `DataManager`, an
  error counter, and config callbacks). New sensors are expected to follow this shape.
- **Bus layer** — `asy_i2c_driver.py`/`asy_spi_driver.py` wrap `machine.I2C`/`machine.SPI` with an
  `asyncio.Lock` and a CircuitPython-style `async with device as dev:` pattern so multiple sensors
  can share one physical bus.
- **Config management** (`async_manager.ConfigManager`) — flat JSON file on the flash filesystem.
  Self-heals on corruption/missing keys by overwriting the *entire* file with hardcoded defaults —
  see BACKLOG.md, this is a known data-loss risk on firmware upgrades that add config keys.
- **REST API pipeline** (`api_helpers.py`) — every `PUT` handler follows `cmd_pre_check` →
  `init_json_from_cfg` → `update_valid_json` → `set_sensor_value` → `cmd_post_check` (validate →
  load current → per-field validate → apply to sensor → persist + post-hooks).
- **FRAM storage** (`asy_fram_driver.py`/`asy_fram_manager.py`, arzi/neu/wozi only) — a bump
  allocator handing out chunks stored as two redundant copies, so an abrupt power-loss or watchdog
  reset mid-write still leaves one valid copy to recover. Currently used for SGP40's VOC
  baseline/humidity-compensation backup.
- **Networking** (`async_connect.py`) — STA-mode WiFi with captive-portal AP+hotspot fallback,
  NTP client with hardcoded CET/CEST DST math.
- **Task supervisor** (`main()` in every `sensortask-*.py`) — two-tier self-healing: dead tasks are
  silently restarted (decaying error score); if the error score exceeds a threshold, the loop stops
  feeding the hardware watchdog and lets it force a hard reset. Units are meant to run for years
  unattended.
- **Frontend** — hand-written HTML/CSS/vanilla JS, no build tooling. At build time the per-device
  folder + `general/` are gzipped and packed into a `frozen_html.py` module via `freezefs`, served
  through Microdot's `send_file(..., compressed=True)`.

## Build process

### Toolchain setup (`toolchain/setup_toolchain.py`)

Building firmware needs a matching set of MicroPython + `pico-sdk` + `picotool` + the ARM
cross-compiler. Getting these four to actually agree with each other used to be a manual,
error-prone recipe (`update_and_install.txt`); it's now one scripted, updatable command. Full
design details live in `toolchain/README.md` — this section is the everyday-usage cheat sheet.

**Bumping the MicroPython version**: change `toolchain/versions.toml`'s `[micropython] ref`
(by hand, or via `setup_toolchain.py --latest` — see "Updating" below). That's the *only* place
to change it — everything else derives from that one value automatically, with no second file to
keep in sync:

- The matching `pico-sdk`/`picotool` versions (see "How it works" in `toolchain/README.md`).
- The MicroPython type stubs `scripts/typecheck.sh` uses for `mypy` (see "Code quality tooling"
  below) — it reads this same `ref` and installs the matching stub release, failing with a clear
  error instead of silently drifting if no matching stub release exists upstream yet.
- The Unix port build (`ports/unix`, used for running tests under the real interpreter later) —
  it's built from the same MicroPython clone `setup_toolchain.py` already checks out at this
  `ref`, not a separately-versioned artifact.

Every build step runs in an explicitly constructed environment (fixed `PATH`, a small
variable allowlist), not whatever happens to be ambient in your shell — a stray `CC`/`CFLAGS`,
a shadowing binary earlier in `PATH`, or a leftover `PICO_SDK_PATH` from an unrelated project
can't silently change what gets built. Verified adversarially against a deliberately poisoned
environment (fake compilers/tools placed ahead in `PATH`, garbage build-flag env vars) — see
"Environment isolation" in `toolchain/README.md`.

**Prerequisites** (a stock Ubuntu 24.04 install already satisfies all of these):

- A Debian/Ubuntu system with the `universe` component enabled in apt sources (on by default for
  every official Ubuntu image/ISO — only relevant if you're on a deliberately minimal base, e.g. a
  `debootstrap`-built rootfs, which only enables `main` unless told otherwise). `gcc-arm-none-eabi`
  and friends live in `universe`.
- `sudo` access (the script uses it for `apt-get install` and `picotool`'s `make install`).
- [`uv`](https://docs.astral.sh/uv/) itself installed — `pip install uv`, or the official installer
  `curl -LsSf https://astral.sh/uv/install.sh | sh` (the script's own dependencies are then handled
  automatically by `uv run`, no separate `pip install`/venv step needed for anything else).
- Outbound network access to GitHub and your distro's package mirrors.

**Verified from scratch on a genuinely clean Ubuntu 24.04 system** (a `debootstrap`-built `noble`
chroot with nothing preinstalled beyond the minimal base — no apt cache, no build tools, no `uv`):
installs every dependency itself and passes verification. (That specific clean-chroot run predates
the 8-step chain below and covered the simpler design it replaced — see `toolchain/README.md`'s
"Evidence this actually works" for exactly what's been re-verified since, and CLAUDE.md's "Pre-push
verification" for when a fresh clean-chroot pass is required again.)

**Everyday usage:**

```sh
# First-time setup (also the command you re-run for everyday use — see "Updating" below)
uv run toolchain/setup_toolchain.py

# Build a specific MicroPython version instead of the pinned default
# (e.g. matching the version actually deployed on units today, see CLAUDE.md)
uv run toolchain/setup_toolchain.py --micropython-ref v1.26.1

# Install somewhere other than the default ~/pico-toolchain
uv run toolchain/setup_toolchain.py --toolchain-dir /path/to/toolchain
```

**Updating** an existing install is the same command, not a separate procedure:

```sh
# Detect + pin + install the newest stable MicroPython release
uv run toolchain/setup_toolchain.py --latest

# Or bump toolchain/versions.toml's [micropython] ref by hand, then:
uv run toolchain/setup_toolchain.py
```

Either way, the matching `pico-sdk`/`picotool` versions are re-derived automatically and only
what's actually changed gets rebuilt — including, deliberately, not rebuilding `mpy-cross` at
all if its source hasn't changed since last time (see below for when you don't want that).

**Forcing a truly from-scratch rebuild** without re-cloning the (multi-gigabyte) git sources:

```sh
uv run toolchain/setup_toolchain.py --clean
```

Normal `setup`/update runs are intentionally incremental where it's safe to be: the firmware and
Unix-port builds always fully recompile (so "builds with zero errors/warnings" stays a genuine
proof every run), but `mpy-cross`'s build directory is otherwise left alone and just rebuilds
whatever actually changed. `--clean` wipes every build-artifact directory (`picotool/build`,
`mpy-cross/build`, `ports/rp2/build-<board>`, `ports/unix/build-standard`) before building,
bringing the toolchain back to a from-scratch build state on demand — useful if you suspect a
stale build artifact, or just want to confirm a truly clean build still succeeds.

**Testing** an already-installed toolchain (no `setup`/network/apt work, just a fast rebuild +
re-check — ~30s vs. minutes for `setup`):

```sh
uv run toolchain/setup_toolchain.py test
```

`setup` provisions the toolchain once, `test` is the repeatable, offline gate that checks it
still builds cleanly. `scripts/test.sh` (see "Code quality tooling" below) relies on this
directly: it runs `setup` automatically the first time it needs the Unix-port interpreter, then
reuses the cached build on later runs — including in CI, via `.github/workflows/ci.yml`.

**What a successful `setup` or `test` run proves**, every time — an 8-step frozen-bytecode
verification chain (`run_verification_sequence()`), each step gating the next:

1. Write a small test module.
2. Build `mpy-cross` (the cross-compiler).
3. Cross-compile the test module with `mpy-cross` directly.
4. Build the MicroPython Unix port with the test module frozen in — zero compiler errors/warnings.
5. Import the frozen module *by name* inside that Unix port binary (no source `.py` file anywhere
   on disk) and check its result — proves `mpy-cross` and the Unix port build both actually work.
   This is the host-side interpreter used for running tests later, see "Code quality tooling"
   below and BACKLOG.md's "Self-contained venv via uv".
6. Build the RP2 firmware for the target board with the same test module frozen in — zero
   errors/warnings (build-only; there's no RP2 hardware here to run it on).
7. Clean up the frozen-bytecode build artifacts from steps 4–6.
8. Rebuild a vanilla (non-frozen) Unix port — the standing test rig `scripts/test.sh` runs tests
   under.

Full step-by-step rationale and verification evidence: `toolchain/README.md`'s "Verification" and
"Evidence this actually works".

### Building this project's firmware

Each `build-<device>.sh`: assembles `python/build/` from `CommonDrivers` + the manifest + the
device's needed `IndividualDrivers` + gzipped/frozen HTML → temporarily swaps `modules/_boot.py`
and `modules/sensortask-<device>.py` (renamed to `sensortask.py`) into the upstream MicroPython
`ports/rp2/modules/` directory → runs
`make -C ports/rp2 BOARD=RPI_PICO_W FROZEN_MANIFEST=<path>` → copies out `firmware.uf2` → restores
the original `_boot.py`.

This still assumes the repo's `python/` directory is checked out as `py-include/python` alongside
the `micropython` tree that `toolchain/setup_toolchain.py` sets up, with `FROZEN_MANIFEST`'s
hardcoded `/home/nico/rpi_pico/...` path in each `build-<device>.sh` genericized to match — not yet
done, see BACKLOG.md.

## Refactor in progress

The `improved-quality/` refactor (see "Repository layout" above) isn't just a cleanup — it targets
the most recent *stable* MicroPython/pico-sdk/picotool/Microdot releases, expands error handling
and bus/sensor fault recovery considerably beyond what's described above, and adds unit tests,
mypy, ruff, and a CI pipeline (including a real firmware build, eventually — the current pipeline
covers lint/type-check/unit-tests only) that don't exist for the current codebase at all. Files
move to `src/` once fully reviewed and tested against that bar — see `src/` and `tests/` in
"Repository layout" above. See BACKLOG.md's "Final-goal requirements for the refactor" for the
full, detailed target.

## Code quality tooling

Ruff and mypy checks, scoped to `improved-quality/`, `src/`, and `tests/` (the pre-refactor
codebase — `python/`, `modules/` — isn't covered yet), plus unit tests for `src/`, can be run
manually. Needs Python 3.11+ (`tomllib`, stdlib only since 3.11 — `uv sync` enforces this
automatically via `pyproject.toml`'s `requires-python`, so this only matters if `uv` has to fall
back to whatever `python3` it finds):

```sh
uv sync                    # one-time, and after pulling changes - installs ruff/mypy/pytest into .venv
source .venv/bin/activate  # scripts/lint.sh and scripts/typecheck.sh assume ruff/mypy are already on PATH

scripts/lint.sh            # ruff check
scripts/typecheck.sh       # mypy, using MicroPython stubs matching toolchain/versions.toml (see above)
scripts/test.sh            # runs every test in tests/, under a real MicroPython Unix-port interpreter -
                            # builds that interpreter automatically on first run (see tests/README.md)
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

Reports line coverage of `src/` only, from the same `tests/test_*.py` suite `scripts/test.sh`
already runs — no coverage threshold is enforced, this only reports numbers, it never fails the
build over them. Since `coverage.py` itself only runs under CPython while `src/` only ever runs
under the real MicroPython Unix-port interpreter, collection and reporting are two separate
stages (`tests/_coverage_runner.py` inside MicroPython, `scripts/_render_coverage.py` under
CPython via `uv run`) glued together through `coverage.py`'s own `CoverageData` API — see
`tests/README.md`'s "Coverage" section for the full pipeline. Builds a second,
`sys.settrace`-enabled Unix port binary on first use (`uv run toolchain/setup_toolchain.py
coverage`, cached under `ports/unix/build-coverage/` alongside the plain `build-standard/` one),
the same way plain `scripts/test.sh` builds `build-standard/` automatically.

Produces, at the repo root (all gitignored, regenerated every run):

- `htmlcov/index.html` — browsable line-by-line HTML report.
- `coverage.xml` — Cobertura XML, uploaded to [Codecov](https://about.codecov.io/) in CI
  (`.github/workflows/ci.yml`) for PR-level visualization; free for public repos.
- `coverage_summary.md` — a markdown table, appended to the GitHub Actions run's Job Summary in
  CI so the numbers show up on the GitHub site with no external service required, even if Codecov
  itself isn't (yet) configured with a repo token.

## Further reading

- **CLAUDE.md** — AI-session operating constraints and architecture reference.
- **BACKLOG.md** — open questions and explicitly deferred work, with reasoning.
