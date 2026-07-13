# Project Notes — Sensor Framework Knowledge Base

This file is a knowledge dump from an initial exploration/documentation session. It exists so a
new session (human or Claude) can pick this project up without re-deriving everything from
scratch. It captures verified facts, architectural understanding, open questions, and explicitly
deferred work. It is **not** yet the polished README.md/CLAUDE.md this project should eventually
have — see "Where this is heading" at the end.

## What this project is

A generic sensor-framework, currently applied to room air-quality sensors, running on
**Raspberry Pi Pico W (first generation, RP2040)** boards under **MicroPython 1.26**. Each
physical unit runs a monolithic asyncio program that reads sensors over I2C/SPI (experimental
UART also exists but is unused so far), exposes a REST API + a small web UI, persists
frequently-changing data to an external FRAM chip, and persists configuration to a JSON file on
the onboard flash filesystem. The code is compiled into the MicroPython firmware as frozen
bytecode (not loaded from the device filesystem at runtime).

**5 units are currently deployed**: `arzi`, `wozi`, and three physically-identical-to-arzi units
that share the `neu` build (same sensor set as arzi, different GPIO wiring). `dev` is a bench/test
rig only — explicitly out of scope for correctness concerns; ignore its quirks.

## Repository map

```
html_raw/               Hand-written HTML/CSS/JS for the web UI, per device config
  arzi/, dev/, wozi/       device-specific pages (index.html, sensorconfig.html, systemledconfig.html)
  general/                 shared assets (style.css, functions.js, favicon.ico, nettimeconfig.html)
  (no neu/ folder — see Open Questions)
modules/                 Auto-started entry points, one set copied into the firmware build per device
  _boot.py                 mounts the LFS2 flash filesystem, then starts the sensor task
  sensortask-{arzi,dev,neu,wozi}.py   the actual per-device application (renamed to sensortask.py at build time)
  (config.json used to live here — removed, see Security Notes)
python/
  CommonDrivers/          shared across all device configs, always copied into the build
    api_helpers.py           generic REST validate → apply-to-sensor → persist pipeline
    async_connect.py         WiFi STA + AP/hotspot fallback + NTP client, DST-aware local time
    async_manager.py         ConfigManager, DataManager, TimeCounterManager, LockedValue/Flag
    asy_udp_socket.py        minimal async UDP socket wrapper (used by NTP client + captive DNS)
    captive_dns.py           DNS server that answers all queries with the device's own IP (hotspot captive portal)
    math_helpers.py          wet-bulb temp, dew point, barometric altitude, absolute/relative humidity
    microdot.py               vendored 3rd-party web framework (github.com/miguelgrinberg/microdot) — verified matches upstream, don't restyle
    system_service.py        uptime counter, boot signature, reboot/bootloader triggers, storage-pause hook
  IndividualDrivers/      only copied into a build if that device config needs them
    asy_i2c_driver.py, asy_spi_driver.py         async bus wrappers (CircuitPython-style I2CDevice/SPIDevice `async with` pattern)
    asy_fram_driver.py, asy_fram_manager.py      raw SPI FRAM chip driver + chunk allocator with dual-copy redundancy
    asy_scd30_driver.py, asy_shtc3_driver.py, asy_mprls_driver.py, asy_isl29125_driver.py, asy_bmp3xx_driver.py, asy_sgp40_driver/   per-sensor Reader + low-level driver (several adapted from Adafruit CircuitPython libraries)
    asy_uart.py, asy_uart_comm.py                experimental UART transport — not used by any current sensortask-*.py
    neopixel_signal.py                            status/air-quality LED signaling
  Manifest/manifest.py    MicroPython freeze manifest used by the build
improved-quality/        WIP refactor target — OUT OF SCOPE for now, do not touch. Already has
                          base_classes.py, config_manager.py, print_log.py, mypy.ini, pycheck.sh —
                          i.e. some of the weaknesses noted below are already being addressed there.
build-{arzi,dev,neu,wozi}.sh   per-device build scripts (see Build Process below)
update_and_install.txt   handwritten setup notes for the MicroPython/pico-sdk/picotool toolchain
```

## Deployed units at a glance

| Config | Sensors | FRAM | Watchdog | debug | HTML source |
|---|---|---|---|---|---|
| arzi | SCD30 (CO2/temp/hum), SGP40 (VOC) | yes | active (8000ms) | False | `html_raw/arzi` |
| neu ×3 | same as arzi, different I2C/SPI/FRAM pin assignments | yes | active | False | `html_raw/arzi` (reused — see Open Questions) |
| wozi | SCD30, SGP40, BMP388 (pressure/temp) | yes | active | False | `html_raw/wozi` |
| dev | SCD30, SGP40, SHTC3, MPRLS, ISL29125 | no | disabled (commented out) | True | `html_raw/dev` — bench rig, ignore quirks |

## Architecture patterns

### Sensor Reader/Driver split
Every `IndividualDrivers/asy_<chip>_driver.py` has two layers:
- A low-level chip driver (register-level I2C/SPI calls, often adapted from Adafruit CircuitPython
  libraries — several still carry Adafruit's MIT-license docstrings/headers verbatim, adapted to
  `async`).
- A `*_Reader` wrapper providing the common async-task surface: `start_asy_read()` /
  `start_asy_trigger()` / `start_timer()` starter methods, a `DataManager` holding the latest
  reading (lock-protected fixed-size list), a `TimeCounterManager`-based error counter, and an
  `asy_cfg_callback` pulled from the shared `ConfigManager`. This is the "generic sensor
  framework" template — new sensors are expected to follow this shape.

### Bus layer
`asy_i2c_driver.py` / `asy_spi_driver.py` wrap `machine.I2C`/`machine.SPI` with an `asyncio.Lock`
and a CircuitPython-style `I2CDevice`/`SPIDevice` (`async with device as dev: ...`) so multiple
sensors can safely share one physical bus.

### Config management (`async_manager.ConfigManager`)
Flat JSON file on the flash filesystem (littlefs/LFS2, mounted by `_boot.py`). Self-heals: if the
file is missing, corrupt, or **missing even one key** relative to the hardcoded `_DEFAULT_CONFIG`
in that device's `sensortask-*.py`, the **entire file is overwritten with defaults** — see Open
Questions, this is a real data-loss risk on firmware upgrades that add config keys.

### REST API pipeline (`api_helpers.py`)
Every `PUT` handler in `sensortask-*.py` follows: `cmd_pre_check` (validate JSON envelope + command
name) → `init_json_from_cfg` (load current values) → `update_valid_json` (per-field type/range
validation, supports "empty string = don't change") → `set_sensor_value` (apply to the live sensor,
with getter-based readback / config-based / hardcoded-default fallback on failure) →
`cmd_post_check` (persist to config if anything changed, run post-hooks). This exact 4-step chain
is repeated by hand for every endpoint — no shared schema/route generation exists yet
(see Deferred Work: config-duplication centralization).

### FRAM storage (`asy_fram_driver.py`, `asy_fram_manager.py` — arzi/neu/wozi only, not dev)
`FRAM_SPI` is the raw chip driver. `asy_FRAM_manager` is a simple bump allocator handing out
`asy_FRAM_chunk` (or `asy_FRAM_timestamped_chunk`, which prepends a UTC timestamp guarded by NTP
sync status) objects. Each chunk is stored as **two redundant copies + 1-byte status flags per
copy**, specifically so an abrupt power-loss or watchdog reset mid-write (see Watchdog below) still
leaves one valid copy to recover from on next read. Currently the only FRAM consumer is SGP40's VOC
baseline/humidity-compensation backup (see Open Questions for exact semantics — not yet fully
verified by reading the driver in depth).

### Networking (`async_connect.py`)
STA-mode WiFi with automatic fallback to a captive-portal AP+DNS hotspot (`captive_dns.py`) after
`conn_fail_to_hotspot` consecutive failures; auto-reverts to STA after `hotspot_time_min` if no
client connects. NTP client with manual, hardcoded CET/CEST DST-transition math (not using a
timezone library — last-Sunday-of-March/October rule baked into `cettime()`). Exposes
`get_long_block_lock()` — a shared `asyncio.Lock` used to serialize `socket.getaddrinfo()` (a known
long-blocking call on this port) against the Neopixel LED animation, since both would otherwise
stall the whole event loop simultaneously. Scope/intent of this lock as a general convention for
*any* future long-blocking operation is an open question (see below).

### Task supervisor / self-healing (`main()` in every `sensortask-*.py`)
Two-tier design, confirmed important and deliberate (units are meant to run for years unattended):
1. **Tier 1**: every asyncio task started in `main()` is checked each `_TASK_CHECK_TIME` (3s); any
   finished/dead task is silently restarted, bumping a decaying error score
   (`_TASK_FAIL_INCREMENT`, decays by 1 per healthy check cycle).
2. **Tier 2**: if the error score exceeds `_TASK_FAIL_MAX` (300), the loop simply **stops feeding
   the hardware watchdog** and keeps trying to restart tasks — there is no explicit
   graceful-reboot call in between. The watchdog (`machine.WDT`, ~8.3s max on RP2040 — see
   Hardware Constraints) then forces a hard reset. Explicit user-triggered reboots
   (`System_Service.reboot_system()`/`reboot_bootloader()`) go through a graceful path that pauses
   FRAM I/O first via `storage_pause`, but the *automatic* watchdog path does not — this is
   presumably fine specifically because FRAM's dual-copy-redundancy design exists to survive
   exactly this kind of abrupt reset.
   Watchdog is meant as a last resort, not something normal operation should ever reach.

### Frontend
`html_raw/` is hand-written HTML/CSS/vanilla JS (no build tooling, no framework). At build time,
the relevant per-device folder + `general/` are copied together, gzipped, and packed into a
`frozen_html.py` module via `freezefs` (`python3 -m freezefs -s html frozen_html.py`), then served
through Microdot's `send_file(..., compressed=True, file_extension='.gz')`. Known to be
duplicative/brittle by the project owner — low priority now, intended to be automated/made
consistent once the Python-side refactor is done.

### Build process
Each `build-<device>.sh`: cleans previous build dir → assembles `python/build/` from
`CommonDrivers` + `Manifest/manifest.py` + the specific `IndividualDrivers` that device needs +
gzipped/frozen HTML → for non-dev builds, temporarily swaps `modules/_boot.py` and
`modules/sensortask-<device>.py` (renamed to `sensortask.py`) into the upstream MicroPython
`ports/rp2/modules/` directory → runs
`make -C ports/rp2 BOARD=RPI_PICO_W FROZEN_MANIFEST=<path to manifest.py>` → copies out
`firmware.uf2` → restores the original `_boot.py` → cleans up. Assumes this repo's `python/`
directory is checked out as `py-include/python` alongside a full `micropython` source tree,
`pico-sdk`, and `picotool` (per `update_and_install.txt`, hardcoded to `/home/nico/rpi_pico/...`
paths in the scripts — will need genericizing whenever the dev-env setup task happens).
`python/Manifest/manifest.py` just does `include(board manifest); freeze(".")`.

## Hardware & platform constraints (verified against current docs)

- **RP2040**: dual-core Cortex-M0+ @ up to 133MHz, 264KB SRAM, 2× I2C, 2× SPI, 2× UART, 8× PIO
  state machines. ([raspberrypi.com/products/rp2040/specifications](https://www.raspberrypi.com/products/rp2040/specifications/))
- **Pico W flash**: 2MB populated on-board, but MicroPython's littlefs storage partition on Pico W
  is smaller than on plain Pico (~848KB vs ~1.37MB) because the CYW43 WiFi firmware blob eats into
  the same 2MB. This is the space `config.json` + frozen HTML + frozen bytecode all compete for.
  ([micropython/ports/rp2/mpconfigport.h](https://github.com/micropython/micropython/blob/master/ports/rp2/mpconfigport.h))
- **Free heap**: roughly ~160KB has been reported free after MicroPython's own footprint on this
  port in past releases — treat as an approximate ballpark, not a hard current number, re-verify
  against the actual 1.26 build if it becomes load-bearing for a decision.
- **`machine.WDT` hard caps at 8388ms on RP2040.** ([MicroPython WDT docs](https://docs.micropython.org/en/latest/library/machine.WDT.html))
  Current code uses `WDT(timeout=8000)` — only 388ms of margin below the hardware ceiling.
- **MicroPython manifest `freeze()`/`module()` strip the `.py` extension** when determining the
  frozen module's import name — confirmed against docs. This is directly relevant to the
  `import sensortask.py` open question below.
- **Microdot vendored copy verified against upstream**: `send_file()` signature and
  `Request.json` behavior (raises on malformed JSON body when `Content-Type: application/json` is
  set, returns `None` only when there's no JSON content-type at all) both match the current
  upstream `microdot.py` source exactly. This confirms `api_helpers.cmd_pre_check`'s
  `try/except` around `request.json` is deliberately catching that parse exception, not dead code.

## Open questions (unresolved — need the project owner's input or further investigation)

1. **`modules/_boot.py:16` — `import sensortask.py`** (literal `.py` in the import statement).
   Confirmed working reliably on real hardware for a long time (that's how the task autostarts),
   but MicroPython's documented freeze/import behavior says the module should be named
   `sensortask` (extension stripped), so `import sensortask.py` looks like it should raise
   `ModuleNotFoundError` under standard dotted-import semantics. Mechanism is genuinely unclear —
   not yet root-caused against MicroPython's import source. **Do not "fix" this without testing on
   real hardware first** — it works today.
2. **SGP40 FRAM backup/restore semantics** — `asy_sgp40_driver/__init__.py` has not been read in
   depth yet (only signatures grepped). Working assumption: the FRAM timestamped chunk persists
   the VOC algorithm's baseline/humidity-compensation state across power loss/reboot so gas-sensor
   calibration doesn't restart cold every time, and `SGPBackupMaxAge` discards a too-stale backup.
   Needs verification by actually reading the driver before documenting it as fact.
3. **Physical wiring / schematics** — pin assignments (I2C/SPI buses, reset/eoc/irq pins) only
   exist encoded in each `sensortask-*.py`. Unknown whether a schematic/PCB design/wiring diagram
   exists anywhere outside this repo, or whether the code is the sole source of truth.
4. **Ambient-pressure compensation on arzi/neu** — `wozi` has a BMP388 for live pressure; arzi/neu
   have no barometric sensor, so SCD30's `AmbPres` compensation on those units can presumably only
   ever come from a manually-set static config value. Not yet confirmed as an accepted limitation
   vs. something to address.
5. **Treatment of Adafruit-derived driver code** — `I2CDevice`/`SPIDevice` and several low-level
   chip drivers still carry Adafruit CircuitPython docstrings/copyright headers, adapted to async.
   Unclear whether this should be treated as vendored/hands-off (like `microdot.py`) or as
   already-modified-enough to be fair game for the refactor.
6. **Scope of `asy_long_block_lock`** — currently shares one lock between NTP DNS resolution and
   the Neopixel animation. Unclear whether this is meant as a general "anything that blocks the
   event loop for a noticeable time must acquire this lock" convention to extend to future
   sensors/features, or was an ad hoc fix for that one interaction.
7. **`neu` reuses `arzi`'s HTML** (`build-neu.sh` copies `html_raw/arzi/*`, and no `html_raw/neu/`
   folder exists). Unconfirmed whether arzi's pages are generic/hostname-driven enough that this is
   fine, or whether they contain arzi-specific text that's technically wrong on a neu unit.
8. **Config-schema migration is a real data-loss risk, not just a design quirk**: `ConfigManager`
   overwrites the *entire* config file with hardcoded defaults the moment even one key is missing
   relative to the current firmware's `_DEFAULT_CONFIG` — meaning flashing a firmware update that
   adds a new config key (e.g. wozi's BMP settings) onto a unit with an older `config.json` would
   silently wipe WiFi credentials and all tuned calibration values. Not yet confirmed whether this
   is an accepted "always reconfigure via the web UI after a key-adding update" workflow, or an
   actual bug to fix.
9. **Hardcoded fallback-hotspot password** — `async_connect.py:241` (and duplicated in
   `improved-quality/async_connect.py:332`): `self.wlan.config(essid=hostname, password='12345678')`.
   Identical, hardcoded, real credential on every deployed unit's AP fallback mode. Flagged to the
   project owner; not yet decided whether to fix now (make configurable / randomize) or accept
   (only exploitable by someone in physical WiFi range of a unit that has already lost real WiFi).
10. **No `.gitignore` exists at all** in the repo. Worth adding one (config.json patterns, build
    output, etc.) to reduce the chance of another device-config backup getting committed by
    accident.

## Deferred / explicitly out-of-scope work (with reasoning, so it isn't re-litigated)

- **HTML/frontend automation & consistency** — known to be hand-written, inefficient, and brittle
  by the project owner. Not a priority. Revisit *after* the Python-side refactor is done, then aim
  for automatic/consistent generation.
- **UART sensor integration** (`asy_uart.py`/`asy_uart_comm.py`, currently unused by any deployed
  config) — address only after the refactor of already-deployed features is complete. Not before.
- **Config-duplication centralization** (the same config keys currently have to be kept in sync by
  hand across `_DEFAULT_CONFIG`, the REST handler, and the HTML form) — acknowledged as a real
  weakness, explicitly owned by the `improved-quality/` refactor. Not a concern for the current
  codebase.
- **`dev` config quirks** (e.g. LED/Neopixel REST routes referencing an object that's never
  instantiated since Neopixel task starters are commented out) — explicitly told to ignore, it's a
  bench rig only.
- **Unit tests** — not to be written against the current codebase. The plan is: fully understand
  how the current system works first (this document is part of that), confirm what's already been
  well-transferred into `improved-quality/`, and write tests as part of that refactor, not before.
- **Dev/build environment setup (venv, pinned toolchain versions)** — deliberately not started yet.
  General direction when it does happen: track the most recent *stable* releases of
  MicroPython/pico-sdk/picotool rather than pinning to what's in the current handwritten notes;
  MicroPython's rp2 port depends on specific pico-sdk submodules (e.g. `lib/mbedtls`), which
  `update_and_install.txt` already gestures at.

## Security notes

- A real WiFi SSID/password (and a device hostname revealing its physical location) were committed
  in `modules/config.json` in the repo's original initial commit. The password was confirmed
  already stale/rotated by the project owner. The commit history on `main` was rewritten (root
  commit rebuilt without the file, second commit re-parented on top, force-pushed) to remove it
  from every reachable commit — verified via the GitHub API that `main` now points to the clean
  history. Note that GitHub may still serve the *old* commit object directly by exact SHA for a
  time even after a force-push (expected, not yet purged from GitHub's own storage) — full removal
  would need GitHub support if that matters. **The project owner is planning to delete and recreate
  the repo from scratch regardless**, which resolves this fully; this note exists so the reasoning
  isn't lost on the next pass.
- Full repo sweep (working tree, all tracked files) turned up no other API keys, tokens, private
  keys, or email addresses. The one other real credential found is the hardcoded hotspot password
  (open question #9 above).

## Working agreements for future sessions

- **Always check current MicroPython and Microdot documentation before asserting how an API
  behaves** — don't rely on training-data memory for either. Several facts in this document were
  specifically verified this way (WDT limit, manifest freeze naming, Microdot `send_file`/`json`
  behavior) rather than assumed.
- Target is **MicroPython 1.26** on **Raspberry Pi Pico W (1st gen / RP2040)**, code ships as
  frozen bytecode — CPython-only stdlib features/behavior cannot be assumed.
- `improved-quality/` is the refactor target and currently out of scope — don't edit it, but it's
  useful context for what's already been identified/addressed (it independently has
  `base_classes.py`, `config_manager.py`, `print_log.py`, `mypy.ini`, `pycheck.sh`).
- `dev` config is a bench rig; don't treat its gaps as bugs needing fixes.
- Long-term goal stated by the project owner: fully understand the current (production) system in
  detail, then check what's already been addressed/transferred well into `improved-quality/`. The
  refactor should end up with the *same top-level features*, just more consistent and stable —
  not a feature change.

## Where this is heading

This single file is a working/transfer document, not the final documentation set. The previously
discussed plan (not yet executed) was three separate documents once things stabilize:
- **README.md** — human-facing project orientation.
- **CLAUDE.md** — AI-session operating constraints + architecture reference (auto-loaded by Claude
  Code).
- **BACKLOG.md** — the deferred-items list with reasoning (the "Deferred / explicitly out-of-scope
  work" section above, essentially).

Constraints for CLAUDE.md specifically are still to be elaborated together with the project owner;
"code must run correctly on MicroPython 1.26 for RP2040, verified against current docs" is the
agreed starting point.
