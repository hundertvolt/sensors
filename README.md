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
build-{arzi,dev,neu,wozi}.sh   per-device build scripts
update_and_install.txt   handwritten toolchain setup notes (MicroPython/pico-sdk/picotool)
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
installs every dependency itself and passes all three checks below in ~3 minutes.

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
what's actually changed gets rebuilt.

**Testing** an already-installed toolchain (no `setup`/network/apt work, just a fast rebuild +
re-check — ~30s vs. minutes for `setup`):

```sh
uv run toolchain/setup_toolchain.py test
```

Meant to run manually today, with an eye toward becoming a CI step later (once this project has
a CI pipeline at all — see BACKLOG.md): `setup` provisions the toolchain once, `test` is the
repeatable, offline gate that checks it still builds cleanly.

**What a successful `setup` or `test` run proves**, every time:

1. A standard, unchanged firmware image builds for the target board with zero compiler
   errors/warnings.
2. `mpy-cross` (the cross-compiler) builds cleanly.
3. `mpy-cross` successfully cross-compiles a throwaway sample `.py` file.

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
mypy, ruff, and a GitLab CI pipeline (including a real firmware build) that don't exist for the
current codebase at all. See BACKLOG.md's "Final-goal requirements for the refactor" for the full,
detailed target.

## Further reading

- **CLAUDE.md** — AI-session operating constraints and architecture reference.
- **BACKLOG.md** — open questions and explicitly deferred work, with reasoning.
