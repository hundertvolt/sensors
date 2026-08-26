# SPECIFICATION

The single central specification document for this repository — architecture, build/toolchain
mechanics, the sensor-driver architecture spec, the `src/` production-quality checklist, and
testing/coverage, all in one place instead of scattered across `DRIVER_SPEC.md`, `src/README.md`,
`tests/README.md`, `toolchain/README.md`, and parts of the root `README.md`.

**What's deliberately *not* in this document, and why:**

- **`CLAUDE.md` stays separate.** It's the file auto-loaded into every AI session's context as
  operating instructions — hard rules, working agreements, the pre-push verification recipe, PR
  workflow. That's a different kind of content (session operating constraints) from what's
  actually specification (code/architecture facts). Cross-references from this document to
  CLAUDE.md point at the real file. What stays in `CLAUDE.md` outright, never duplicated here: its
  Hard rules/Working agreements/PR workflow/Pre-push verification recipe/Code quality tooling
  sections — session-operating-procedure and dev-tooling-narrative content, not
  architecture/interface specification. Its former "Platform target" facts (Part F below),
  "Architecture reference" deep-dive (A.4), and "Microdot / REST layer" contract (A.5) live here as
  the single copy instead — a deliberate tradeoff, since `CLAUDE.md` is auto-loaded into every AI
  session's context and this document is not, so a session that never opens `SPECIFICATION.md` no
  longer gets those facts for free. If that ever bites in practice, the fix is re-duplicating the
  highest-value load-bearing facts back into `CLAUDE.md`, not reverting the consolidation.
- **`BACKLOG.md` stays separate.** By its own stated nature it is not a specification: it's active
  working memory (open questions, deferred work) that churns as items resolve. Folding live churn or
  provisional planning content into a stable spec would immediately start recreating the scattering
  problem this document exists to fix.

**Where the source files went**: `DRIVER_SPEC.md`, `src/README.md`, `tests/README.md`, and
`toolchain/README.md` held no content of their own beyond a "moved here" pointer once their content
was consolidated into Parts B-E below, and have since been deleted — every reference to them
elsewhere in the repo (docs and code comments alike) points directly at the relevant Part here
instead. `README.md` keeps its human-facing project description and the units-deployed table; its
former "Repository layout"/"Architecture at a glance"/"Refactor in progress"/"Building this
project's firmware" sections moved into Part A/B below, replaced there with a pointer. `AUDIT_PLAN.md`
(the master action list for the full `src/` audit this document's Parts C/D harmonization came out
of) and, later, `WIRING_CONTRACT.md`/`FINAL_WIRING_PLAN.md` (the temporary planning docs for the
`improved-quality/` → `src/` wiring effort) were each deleted once their own effort closed —
everything permanent each one settled was migrated here first: `WIRING_CONTRACT.md`'s construction
order/FRAM-chunk order/dependency graph/debug-level registry now live in Part A.7,
`FINAL_WIRING_PLAN.md`'s REST API design in Part A.8, its website-stub pipeline in Part A.9, and two
checkable conventions its own failure-mode audit found in Parts C.7/C.9. `WEBSITE_PLAN.md` (the
temporary planning doc for the JS/HTML/CSS website redesign) followed the same lifecycle once that
effort completed: its settled architecture now lives in Part H below, its still-open items moved to
`BACKLOG.md`, and the file itself was deleted.

## Table of contents

- **Part A — Repository & Architecture Overview**: repository layout, architecture at a glance,
  refactor status, the deep module-by-module architecture reference, the Microdot/REST layer
  contract, datasheets, the assembled prototype's construction order/dependency graph, the REST API
  endpoint reference, the website-stub/frozen-HTML pipeline, and the digital twin.
- **Part B — Toolchain & Build**: the MicroPython/pico-sdk/picotool/cross-compiler installer, and
  building this project's own firmware.
- **Part C — Sensor Driver Architecture Specification**: the shared contract a new sensor driver
  follows (layering, naming, config schema, error handling, concurrency, timers, typing).
- **Part D — `src/` Production-Quality Checklist**: what "done" means for any file added to
  `src/`.
- **Part E — Testing & Coverage**: why/how unit tests run under a real MicroPython interpreter,
  the hardware-mocking boundary, and the coverage pipeline.
- **Part F — Platform Target & MicroPython Runtime Facts**: RP2040/MicroPython-1.26 specifics,
  gotchas, and the load-bearing constraints they impose on every driver/service in Parts C-E.
- **Part G — Shared Pattern & Primitive Reuse**: the living catalog of established shared
  primitives (numeric validation/coercion, callback dispatch guarding, response envelopes, locked
  state, logging, driver architecture, the `src/`↔`js/` cross-language mirror) and the discovery
  procedure to run against it before writing any new function/module — cross-cutting across
  `src/`, `js/`, and any future layer, not scoped to one language the way Part D is.
- **Part H — Website (JS/HTML/CSS) Architecture**: the browser-side sensor-station website's
  purpose/design constraints, folder/module map, the visual-vs-mechanics layering contract, its
  REST-mirroring architecture and definitions-file schema, digital-twin integration (bundling,
  connection-concurrency ceiling, cross-browser coverage), and its CI/tooling stack.

---

# Part A — Repository & Architecture Overview

## A.1 Repository layout

```
datasheets/              Real datasheet PDFs for the chips this codebase drives - see CLAUDE.md
  bmp3xx/, fram/, pico w/, scd30/, sgp40/
html_raw/               Legacy, still-deployed hand-written HTML/CSS/JS for the web UI, per device
                          config - targets the pre-refactor REST shape, superseded by html/ below
                          for devices the refactor has reached - see Part H.1
  arzi/, dev/, wozi/       device-specific pages
  general/                 shared assets (style.css, functions.js, favicon.ico, nettimeconfig.html)
html_stub/              Placeholder ("Hello world"-shaped) website content standing in for the real
                          site in the refactored build's generic pipeline tests - see "Website stub /
                          frozen-HTML pipeline" below
html/, js/, tests_js/,  The real, refactored website (JS/HTML/CSS) - source, tests, and prototype-
  mockdata/               only mock-backend fixtures respectively - see Part H below
modules/                Auto-started entry points, one set copied into the firmware build per device
  _boot.py                 mounts the flash filesystem, then starts the sensor task
  sensortask-{arzi,dev,neu,wozi}.py   per-device application (renamed to sensortask.py at build time)
python/
  CommonDrivers/          shared across all device configs, always copied into the build
  IndividualDrivers/      only copied in if a given device config needs them
  Manifest/manifest.py    MicroPython freeze manifest used by the build
src/                     Fully-reviewed/tested refactor code, freely editable - see Part D below
                          for the review checklist any file here must pass. Includes the assembled
                          refactor prototype itself, src/sensortask_wozi.py (see A.7 below) and
                          src/asy_webserver_service.py (the registration-based REST/API service,
                          see A.8 below). `improved-quality/`, the refactor's former WIP staging
                          directory, has been fully retired and deleted - see CLAUDE.md
ext/                     Vendored third-party code, hands-off (see CLAUDE.md's vendoring policy)
  microdot.py               Microdot v2.6.2, unmodified - see A.5 below
  freezefs/                 freezefs 2.4, unmodified - gzip+freeze pipeline for html_stub/, see
                            "Website stub / frozen-HTML pipeline" below
boot_entry/              Real firmware entry point for src/sensortask_wozi.py
  wozi_boot.py              the only file that actually blocks on `asyncio.run(main())` - kept
                            separate from src/sensortask_wozi.py so the latter stays import-safe
                            for tests (see that module's own docstring)
digital_twin/            Hardware simulator standing in for real I2C/SPI/WiFi hardware under the
                          MicroPython Unix-port interpreter - see A.7's "Digital twin" pointer,
                          digital_twin/README.md, and SPECIFICATION.md Part C.11's per-driver
                          "digital-twin extension" requirement
frozen_modules/          Gitignored build artifact - scripts/build_frozen_html.sh's gzip+freezefs
                          output (frozen_html.py), deliberately not placed under `.frozen/` (a
                          reserved MicroPython import-machinery sentinel - see "Website stub /
                          frozen-HTML pipeline" below)
SPECIFICATION.md         This file - the central specification (repo root)
tests/                   Unit tests for src/, run under a real MicroPython interpreter - see
                          Part E below
toolchain/               MicroPython/pico-sdk/picotool build-environment installer
  versions.toml             single source of truth for the target MicroPython version - see
                            Part B below for how everything else derives from it
  setup_toolchain.py        `setup`/`test` - builds RP2040 firmware and the MicroPython Unix port (for tests/)
build-{arzi,dev,neu,wozi}.sh   per-device build scripts
update_and_install.txt   handwritten toolchain setup notes (MicroPython/pico-sdk/picotool)
pyproject.toml           dev-tooling config (ruff/mypy/pytest/uv) - see CLAUDE.md's "Code quality tooling"
scripts/                 lint.sh / typecheck.sh / test.sh - manual code-quality check runners.
                          build_frozen_html.sh - gzip+freezefs pipeline for html_stub/ (see
                          "Website stub / frozen-HTML pipeline" below). run_unix_port_integration.sh -
                          the digital-twin end-to-end entry point, see A.7's "Digital twin" pointer
.github/workflows/       CI: runs lint.sh/typecheck.sh/test.sh on every push/PR
```

## A.2 Architecture at a glance

- **Sensor Reader/Driver split** — every `IndividualDrivers/asy_<chip>_driver.py` has a low-level
  chip driver (register-level I2C/SPI calls, several adapted from Adafruit CircuitPython
  libraries) plus a `*_Reader` wrapper providing the common async-task surface
  (`start_asy_read()`/`start_asy_trigger()`/`start_timer()`, a lock-protected `DataManager`, an
  error counter, and config callbacks). New sensors are expected to follow this shape (full spec:
  Part C below).
- **Bus layer** — `asy_i2c_driver.py`/`asy_spi_driver.py` wrap `machine.I2C`/`machine.SPI` with an
  `asyncio.Lock` and a CircuitPython-style `async with device as dev:` pattern so multiple sensors
  can share one physical bus.
- **Config management** — the deployed, pre-refactor codebase (`python/`, `modules/`) uses
  `async_manager.ConfigManager`: one ad hoc top-level instance per device, flat JSON file on the
  flash filesystem, self-heals on corruption/missing keys by overwriting the *entire* file with
  hardcoded defaults (a known data-loss risk on firmware upgrades that add config keys — see
  BACKLOG.md). `src/config_manager.py`'s `ConfigManager` replaces this in the refactor: every
  module with user-settable configuration (each sensor `*_Reader`, `asy_wifi_service.py`,
  `asy_ntp_client.py`, `asy_notification_service.py`, ...) owns its own schema (a `ConfigSchema`
  tuple) and its own config file/instance via a public `cfg_schema` attribute (also available
  through the base-class-owned `get_cfg_schema()` getter), instead of one shared grab-bag — see
  Part C.5 below and CLAUDE.md's "Code quality tooling"/BACKLOG.md for the migration state.
- **REST API pipeline** — the *deployed* pipeline (`python/CommonDrivers/api_helpers.py`, left
  untouched/out of scope — see CLAUDE.md) has every `PUT` handler follow `cmd_pre_check` →
  `init_json_from_cfg` → `update_valid_json` → `set_sensor_value` → `cmd_post_check` (validate →
  load current → per-field validate → apply to sensor → persist + post-hooks).
  `src/api_response.py` is its generalized replacement, and is now wired into every real REST
  handler in `src/asy_webserver_service.py` (the old `improved-quality/api_helpers.py`'s own copy
  of the legacy pipeline, and later `improved-quality/sensortask-wozi.py` itself, were both
  removed entirely once fully migrated off it and superseded — see CLAUDE.md's "Hard rules"):
  `base_classes.py`'s `_set_dict_cfg()` gives every `SensorReaderConfig` a generic,
  schema-driven setter mirroring `get_dict_cfg()`'s existing generic getter, and
  `api_response.py`'s `make_response()`/`parse_cmd_request()`/`handle_set_cmd()` replace the old
  per-endpoint validate→apply→persist glue with one small, open-catalog response envelope — see
  Part C.5.3 below for the full mechanism.
- **FRAM storage** (`asy_fram_driver.py`/`asy_fram_manager.py`, arzi/neu/wozi only) — a bump
  allocator handing out chunks stored as two redundant copies, so an abrupt power-loss or watchdog
  reset mid-write still leaves one valid copy to recover. Currently used for SGP40's VOC
  baseline/humidity-compensation backup.
- **LED notification signalling** — split into `asy_neopixel_driver.py` (pure LED hardware:
  overlay toggle, dimmed ramp-up/ramp-down, internal/external arbitration for the one shared
  pixel; no config schema) and `asy_notification_service.py` (`NotificationCoordinator`: generic
  threshold-triggered signalling replacing the legacy file's hardcoded CO2/VOC/Humidity checks,
  driving the LED through the former's `request_signal()`). Promoted from
  `improved-quality/neopixel_signal.py`.
- **Networking** — split into three peers, wired together by each `sensortask-*.py`, not one
  owning the others: `asy_wifi_service.py` (STA-mode WiFi with captive-portal AP+hotspot fallback),
  `asy_ntp_client.py` (NTP client with CET/CEST DST math), and `asy_dns_client.py` (a non-blocking
  DNS resolver replacing `socket.getaddrinfo()` — see BACKLOG.md). The deployed, pre-refactor
  codebase (`python/`, `modules/`) still uses the older monolithic `async_connect.py`.
- **Task supervisor** (`main()` in every `sensortask-*.py`) — two-tier self-healing: dead tasks are
  silently restarted (decaying error score); if the error score exceeds a threshold, the loop stops
  feeding the hardware watchdog and lets it force a hard reset. Units are meant to run for years
  unattended.
- **Frontend** — hand-written HTML/CSS/vanilla JS, no build tooling. At build time the per-device
  folder + `general/` are gzipped and packed into a `frozen_html.py` module via `freezefs`, served
  through Microdot's `send_file(..., compressed=True)`.

## A.3 Refactor status

This refactor (see repository layout above) isn't just a cleanup — it targets
the most recent *stable* MicroPython/pico-sdk/picotool/Microdot releases, expands error handling
and bus/sensor fault recovery considerably beyond what's described above, and adds unit tests,
mypy, ruff, and a CI pipeline (including a real firmware build, eventually — the current pipeline
covers lint/type-check/unit-tests only) that don't exist for the current codebase at all. Files
land in `src/` once fully reviewed and tested against that bar — see `src/` and `tests/` in the
repository layout above, and Part D/Part E below. See BACKLOG.md's "Refactor targets not yet done"
for what's still open.

**The assembled prototype (`src/sensortask_wozi.py`, A.7 above) currently covers the "wozi" device
variant only** — not `arzi`/`dev`/`neu`. The refactor's goal is the *same top-level features* as
today's deployed units, just more consistent/stable, not a feature change (see the working
agreement above), and a future per-variant build-script generator turning one setup-definition file
into every variant's `sensortask-*.py`/website pair is a real planned direction (see A.8's
"generator-friendly" registration-API note and A.9's `HTML_SRC_DIRS` mechanism, both already shaped
around it) — but that generator itself, and wiring the other three variants through it, is not yet
built. Real website content (beyond A.9's placeholder stub) and real-hardware build genericization
(see BACKLOG.md's "Dev/build environment setup" item) are likewise still open, not part of what's
landed so far.

## A.4 Architecture — deep reference

The condensed version is A.2 above. Key modules if you need to go deeper (folded in from
`CLAUDE.md`'s "Architecture reference" section):

- `python/CommonDrivers/api_helpers.py` — generic REST validate → apply-to-sensor → persist
  pipeline, repeated by hand for every endpoint (no shared schema/route generation — see
  BACKLOG.md's config-duplication item).
- `python/CommonDrivers/async_connect.py` — WiFi STA + AP/hotspot fallback + NTP client with
  manual CET/CEST DST math (`cettime()`); exposes `get_long_block_lock()`, a shared lock
  serializing `socket.getaddrinfo()` against Neopixel animation. This is the deployed, pre-refactor
  version only — `src/` split this into `asy_wifi_service.py`/
  `asy_ntp_client.py`/`asy_dns_client.py` and retired the lock entirely (see F.2 below and
  BACKLOG.md); don't assume the two describe the same current state.
- `python/CommonDrivers/async_manager.py` — `ConfigManager`, `DataManager`,
  `TimeCounterManager`, `LockedValue`/`Flag`. `src/config_manager.py`'s `ConfigManager` and
  `src/base_classes.py`'s `LockedValue`/`LockedCounter`/`LockedFlag` (snake_case `set_value()`/
  `get_value()`, unlike the old module's camelCase `setValue()`/`getValue()`) replace these in the
  refactor — see A.2's "Config management" bullet for the class-replacement summary and the
  project-wide "every module owns its own schema" convention, not restated here. MicroPython's
  flat frozen-module namespace means `import async_manager` silently resolves to whichever file
  defines that module name — a new or promoted module must import `ConfigManager`/`LockedValue`/
  etc. from `config_manager`/`base_classes` by name, never `async_manager`, or it gets the old,
  incompatible classes with no import error to catch it. Its config is loaded once at
  `__init__` and served entirely from an in-memory cache thereafter — a deliberate consequence is
  that a read can no longer detect the on-disk file being corrupted/deleted out-of-band after a
  valid `__init__`; the cache is the sole source of truth, and a later `write_config()` silently
  *repairs* an externally-corrupted file from it. Accepted given this device is the file's only
  writer. Two details beyond A.2's summary: `src/asy_neopixel_driver.py`'s `NeopixelDriver` is the
  one deliberate exception to the "every module owns a schema" convention — no config schema at
  all, confirmed by the project owner (see its own entry below). And a module whose own
  REST/caller layer needs to call `write_config()` directly against its `cfgmgr` exposes the
  schema via a public `self.cfg_schema` attribute (see `asy_wifi_service.py`/`asy_ntp_client.py`)
  rather than the caller reaching into a private module-level schema constant —
  `base_classes.py`'s `SensorReaderConfig` doesn't provide this itself, so any new module needing
  it adds the attribute the same way.
- `python/IndividualDrivers/asy_fram_driver.py` / `asy_fram_manager.py` — raw SPI FRAM driver +
  chunk allocator with dual-copy redundancy (arzi/neu/wozi only, not dev). `src/`'s promoted
  versions keep the same design: each chunk stores two redundant copies plus a busy/idle status
  byte guarding both reads and writes (MB85RS64V reads are destructively read internally, so a
  power loss mid-read is as real a risk as mid-write); "both copies valid but different" is a hard
  failure (no generation counter to say which is newer), never silently guessed.
  `AsyFramTimestampedChunk.write()`/`write_into()` return `(ntp_synced, utc, success)` — `success`
  is the *third* element, not first, unlike every other bool-returning method in this codebase;
  don't reorder it, callers already unpack it this way. `AsyFramManager` is a bump-pointer
  allocator: `get_chunk()`/`get_timestamped_chunk()` carve out fixed offsets in call order, so a
  device's *instantiation order* of these calls is its on-chip layout and must stay identical
  across firmware versions for existing stored data to keep decoding correctly.
  **FRAM chunk determinism rule** (no deallocation exists — intentional, bump allocator by design;
  byte-offset/placement doesn't matter): what must hold, verified per file touching a FRAM-backed
  class, not assumed, is that **every FRAM-chunk-owning object's construction (and therefore its
  one-time `get_chunk()`/`get_timestamped_chunk()` call) is deterministic across every system
  event, especially reboot** — an unconditional, fixed-position statement in the wiring sequence,
  never inside a branch, a loop with variable order, or anything a task restart could re-enter.
  Verified true today: task-level restarts (`system_service.py`'s `start_and_check_tasks()`) only
  re-invoke an already-captured `task_starters[n]` callable on the *existing* object, never re-run
  `__init__`; a full reboot replays `src/sensortask_wozi.py`'s entire `build_system()`
  construction sequence from scratch, and every current FRAM-chunk-owning construction (`sysfunct`,
  `sgp_reader`'s VOC-backup chunk, `pixel`, `notify_service`) is an unconditional top-level
  statement, confirmed by direct reading, not assumption. Before adding any *new* FRAM-backed class
  (a new driver, or a currently-in-memory-only logger — e.g. a `CFGMGR_*` or `"DNSSRV"` logger ever
  becoming FRAM-backed), prove single, deterministic construction first, not after.
  **Every deliberate system reset already pauses FRAM first, confirmed directly**:
  `system_service.py`'s `_reboot()` (backing both `reboot_system()`/`reboot_bootloader()`) calls
  `self.storage_pause(True)` before arming the delayed reset timer, and before the
  `_force_watchdog_starve` fallback too. The margin is sufficient: the FRAM bus runs at 1MHz
  (`asy_spi_driver.py`'s default `baudrate`) over a `max_size=0x2000` (8KB) chip, and no single
  chunk approaches that whole size (individual chunks are tens of bytes), so even a two-block write
  plus CRC-verify readback completes in low single-digit milliseconds — three orders of magnitude
  under both the deliberate 4s `_RESET_DELAY` and the worst-case ~8s watchdog-starve wait; a
  genuinely wedged bus is the separate, already-accepted "hardware watchdog is the backstop" case
  (CLAUDE.md). The invariant is actively enforced, not just true by chance:
  `tests/test_reset_call_site_invariant.py` scans every `src/*.py` file and fails if
  `machine.reset()`/`machine.bootloader()` appear anywhere but `system_service.py`, or `WDT()`
  anywhere but `sensortask_wozi.py`.
- **SCD30's `AmbPres` (ambient-pressure compensation) is stored in the sensor's own internal
  non-volatile memory as a one-time-set value, not a continuously-updated live input.** This is why
  it's a static config value on every unit — including wozi, which has a live BMP388 — and why
  `set_ambient_pressure` is called with `force=True` in the REST handler: resending the same value
  is also the SCD30's documented command to resume continuous measurement after it's been stopped.
  Don't "fix" this into a live BMP388→SCD30 feed; it's intentional, confirmed by the project owner.
- **SCD30's `ForceCalRef` field-recalibration procedure, confirmed by the project owner**: done
  manually today, not automated. The unit is exposed to air where the true CO2 concentration is
  known to match outside/ambient air (i.e. the space is ventilated until indoor CO2 reads the same
  as outdoor ambient), then `ForceCalRef` is set to that known reference concentration via the
  REST setter. There is no separate exposure-timing/frequency schedule beyond "whenever a
  recalibration is judged needed" — no automation of this procedure is planned.
- **SCD30's `TempOffs` (temperature offset) has a real 0.01°C hardware resolution, not just a
  cosmetic rounding choice**: `set_temperature_offset()` sends `int(offset * 100)` to the sensor's
  register — a genuine truncation (not rounding) unique to this one field/driver (no other driver
  scales-then-truncates a value this way). A value with more than two decimal digits is silently
  truncated by the real chip, not rejected; anything writing or testing this field should account
  for that instead of expecting an exact round-trip.
- **SGP40's VOC index is a deviation-from-learned-baseline number, not an absolute-concentration
  one — confirmed directly against `voc_algorithm.py`'s real Sensirion Gas Index Algorithm port
  while calibrating a real threshold-crossing integration test (see
  `tests/test_notification_sgp40_integration.py`'s own top-of-file comment for the full derivation).**
  Three facts worth knowing before writing any test or reasoning about real-world VOC behavior: (1)
  `_VOCALGORITHM_INITIAL_BLACKOUT = 45` sampling intervals must elapse before the index moves off 0
  at all; (2) under *any* constant raw-tick input, however extreme, the index converges toward 100
  (the algorithm's own "clean air" baseline) — a real spike needs a genuine step change away from
  whatever raw value the sensor has already been reporting, not just a high absolute value; (3) a
  *higher* raw tick count reads as *cleaner* air on this driver's convention (index moves down as
  raw goes up, and vice versa) — the inverse of what "raw" might suggest. None of this is a bug;
  it's how Sensirion's own reference algorithm is designed to work, and `asy_sgp40_driver.py`
  already treats `VOC` as an opaque index throughout (see F.4 below for why this file's internals
  stay a literal, undisturbed port).
- **The former `improved-quality/neopixel_signal.py` (LED hardware control + hardcoded CO2/VOC/Humidity
  threshold monitoring combined in one file) was promoted and split into two `src/` files** - the old
  file is deleted, `src/sensortask_wozi.py` wires the two replacements directly.
  - `src/asy_neopixel_driver.py`'s `NeopixelDriver` — pure LED hardware service: overlay
    switch/toggle, the dimmed ramp-up/ramp-down signal, and the internal/external
    (`request_signal()`/`led_signal()`) arbitration for the one shared physical pixel, unchanged
    from the original file's proven mechanism (`request_signal()` returns once a request is queued,
    not once its ramp finishes — preserve this exact contract if touching this file again). No
    config schema at all (confirmed by the project owner) and no namedtuple/measurement data, so it
    doesn't extend `SensorReaderConfig` — the one exception to this codebase's own `_NAME`/namedtuple
    pairing convention (see C.2 above). Also serves `asy_wifi_service.py`'s
    `LEDControl` Protocol (`ext_led=`) unchanged.
  - `src/asy_notification_service.py`'s `NotificationSignal` (a plain, dependency-free per-condition
    data holder) + `NotificationCoordinator(SensorReaderConfig)` (generic threshold-triggered
    signalling, replacing the old file's hardcoded three-condition logic) — owns sleep-window/
    interval/`AutoOn`/global `FlashBri`/`FlashDur`, the override/pause countdown, one combined
    `ConfigManager`, and one combined `PrintLogHistory`(Store) covering its own fields plus every
    registered `NotificationSignal`'s threshold field. **Staged registration, deferred
    construction**: `__init__()` only stashes constructor args; `register()` (sync) accepts
    `NotificationSignal`s in check-order; `finalize()` (sync, exactly once) builds the combined
    schema and is the single point `self.pr`/`self.cfgmgr` actually come into existence, via a
    delayed `super().__init__()` call — the whole mechanism achieved with zero changes to
    `ConfigManager`/`PrintLogHistory`(Store)/`base_classes.py` themselves, relying on the guarantee
    that the number/order of registered signals stays constant once `finalize()` has run (a one-time
    boot handshake). `register()`/`finalize()` are sync but can't call the async `self.pr.wrn_s()`
    directly (and `self.pr` may not exist yet pre-`finalize()`) — rejections are buffered and
    drained by `monitor_loop()` each cycle instead. `NotificationSignal.color` is a per-channel
    weight (0/1), not an absolute color — scaled by the shared `FlashBri` at trigger time, which is
    what makes one global brightness setting actually apply to every registered condition.
  - Config field names drop the "Led" prefix everywhere (`WarnCO2` not `LedWarnCO2`) — a deliberate
    wire-format change; the (already known-brittle, deferred — see BACKLOG.md) frontend isn't
    updated to match yet.
- In the deployed, pre-refactor codebase (`modules/sensortask-*.py`), the task supervisor is a
  hand-rolled loop inside each file's `main()`, not a shared module — duplicated per device file.
  `src/sensortask_wozi.py` no longer matches this: its `main()` now calls
  `system_service.py`'s real `start_and_check_tasks()`/`start_timers()` instead of reimplementing
  the loop. Don't assume the two describe the same current state.
- **Functional behaviors confirmed intentional by the project owner, not obvious from the code
  alone — don't "fix" any of these:**
  - Air-quality warning LED sequencing (one color per condition, paused between flashes rather than
    combined) is exactly as designed.
  - FRAM SGP40 backup "0 = disabled" semantics: `SGPBackupPeriod=0` disables periodic backup
    writes, `SGPBackupMaxAge=0` disables the staleness check (currently undocumented user-facing —
    see BACKLOG.md).
  - Permanent WiFi deactivation after a second STA failure streak (post-hotspot) is a deliberate
    safety feature, preventing an unclaimed hotspot from staying open indefinitely — a physical
    power-cycle is the accepted recovery path. `_reset_wlan_connect_state()` (run on every task
    restart) special-cases `_PHASE_DEACTIVATED` the same way it already special-cased
    `_PHASE_HOTSPOT`: left as-is rather than reset to `_PHASE_STA_SEEKING`, so a task-level restart
    can't silently re-enable WLAN out from under this safety feature.
  - STA never automatically falls back to hotspot mode again once it has connected successfully
    even once in a task's lifetime — only a human resubmitting WiFi credentials over the REST API,
    or a full task restart, resets this. Confirmed deliberate for physically-accessible, easy-to-
    power-cycle devices, not an oversight — don't add an automatic repeat-fallback path.
  - The web UI intentionally shows raw sensor numbers only, no color-coding — the physical LED is
    the sufficient at-a-glance indicator.
  - SGP40 silently falling back to uncompensated VOC readings when SCD30 is down/stale, with no
    distinct "degraded" signal, is acceptable as-is — SCD30's own error counter already surfaces
    the cause.
  - FRAM's 8KB allocation has plenty of headroom over SGP40's current ~250-byte usage for future
    FRAM-backed features.
  - `asy_uart_driver.py` intentionally does not expose hardware flow control (`rts`/`cts`/`flow`) —
    confirmed directly, not planned for the future either. Not a gap to revisit unprompted.
  - `asy_notification_service.py`'s `monitor_loop()` active-window check (`on_min_of_day <=
    cur_min_of_day <= off_min_of_day`) doesn't handle a window that wraps past midnight (e.g.
    `OnH=22`/`OffH=6`) — such a configuration silently never triggers, no error or warning either.
    Confirmed byte-for-byte identical to `python/IndividualDrivers/neopixel_signal.py`'s
    `airquality_auto_signal()` (`onMinOfDay <= curMinOfDay <= offMinOfDay`), a faithful port of
    already-proven legacy field behavior, not a promotion regression — leave as-is per CLAUDE.md's
    legacy-behavior-verification rule; a future session adding real overnight-window support should
    treat it as a deliberate feature addition; needs `on_min_of_day > off_min_of_day` handling.
  - SCD30's `get_ambient_pressure()` read-back reuses the same command word used to *set* it —
    matches every sibling getter's pattern and the legacy driver's own proven field behavior, even
    though neither Sensirion's `embedded-scd` reference driver nor their `python-i2c-scd30` driver
    documents that command as readable (their worked examples only show a write path for it). No
    alternate documented read-back path exists to switch to regardless. Leave as-is.

## A.5 Microdot / REST layer

`ext/microdot.py` is vendored, unmodified upstream Microdot (currently pinned to tag `v2.6.2` —
treated as a plain external resource, no edits, no "cleanup" of its style; CLAUDE.md's Hard rules
section is the authoritative vendoring policy; its MIT license text lives alongside it as
`ext/LICENSE-microdot` rather than inside the file itself, the same sibling-file pattern
`ext/freezefs/LICENSE` already uses — see `THIRD_PARTY_LICENSES.md` for the full third-party
attribution list). The facts below were confirmed by reading its
actual source directly (`Microdot.dispatch_request()`/`handle_request()`/`Response.write()`/
`Request.json` in `ext/microdot.py`), not assumed from Microdot's docs or training memory — treat
this section as the standing reference for how much stability Microdot already gives us for free
versus what our own REST layer still has to add.

- **Every exception raised by our own code inside a route handler — including a before/after-request
  hook, and including `MemoryError` — is already caught by Microdot itself, per request, and can
  never crash the server.** `dispatch_request()` wraps the whole handler chain (before-request
  hooks → route handler → response coercion, which includes `json.dumps()` of a returned dict/list
  → after-request hooks) in one `except HTTPException` / `except Exception`. An `HTTPException`
  (from `abort()`) resolves by **numeric status code** through `self.error_handlers`; any other
  exception resolves by **exact exception class**, then by walking the class's MRO — so a single
  `@app.errorhandler(Exception)` registration is reachable as a catch-all fallback from any
  exception subtype, without needing one registration per exception type. The deployed,
  pre-refactor `python/CommonDrivers/microdot.py` app still registers no `errorhandler` at all
  (confirmed) — Microdot's own bare default response is used there (`'Internal server error',
  500`, or `'Not found', 404`, etc.), safe but not one of our own reply shapes. `src/`'s own
  `asy_webserver_service.py` now does register handlers - see A.8 below and that module's own
  `_ERROR_SHAPES`/`__init__`: shaped-JSON handlers for 400/404/405/413/500, plus a catch-all
  `@app.errorhandler(Exception)` whose sole job is persisting the exception into `pr.err_s()`/FRAM
  history (the matching status-code handler above already shapes the actual reply either way, per
  `ext/microdot.py`'s own `error_response()` fallthrough - see that module's own comments).
- **The one place this blanket catch does *not* cover: exceptions raised while writing the response
  itself.** `Response.write()` (and the `handle_request()` code that calls it) only catches
  `OSError`, and only mutes a short allow-list of expected socket errors (broken pipe, connection
  reset, write to an already-closed socket — `MUTED_SOCKET_ERRORS`); anything else — a non-`OSError`
  from a streamed body's `.read()`/generator, or an unmuted `OSError` — propagates all the way out of
  the per-connection handler coroutine uncaught. This is the one genuine "a reply may not be
  possible" case: by the time this code runs, the response is already (partially) in flight, so
  there is no remaining hook to convert the failure into a REST reply — the client runs into a
  timeout instead, exactly as expected/accepted.
- Microdot's own exception logging (`print_exception(exc)`, a bare MicroPython traceback dump) is
  **not** wired into this project's own `PrintLog`/FRAM-backed logging in any way. Anything caught
  by Microdot's blanket per-request catch that we want reflected in our own error counters/history
  has to come from an `@app.errorhandler` we register ourselves calling into `pr.err_s(...)` (or
  equivalent) — Microdot's default handling alone leaves no trace anywhere a deployed, headless unit
  can be expected to surface.
- `Request.json` has no internal guarding at all (`json.loads(self.body.decode())`, no try/except) —
  a malformed body or bad encoding raises straight out of the property access. Given the point
  above, this is already contained by Microdot's own blanket catch either way; guarding it ourselves
  (as `cmd_pre_check` already does, legacy and WIP alike) is about producing a precise, on-brand
  error reply instead of a generic 500, not about crash prevention.
- Request size is already bounded by Microdot itself before any handler runs:
  `Request.max_content_length` (16KB default) → 413 for an oversized body,
  `Request.max_readline` (2KB default) → guards a single request/header line. This project's JSON
  payloads are tiny; the defaults are already generous headroom on a 264KB-SRAM target, no override
  needed — just worth knowing the guard already exists rather than re-adding one at our own layer.
- The Microdot server task is already wired into `system_service.py`'s generic
  `start_and_check_tasks()` supervisor exactly like every other sensor task (see
  `src/sensortask_wozi.py`'s `_collect_task_starters()`: `webserver.get_task_starters()` is folded
  into the same `task_starters` list as every other module's). A Microdot task that terminates — by returning or by an exception escaping it —
  is detected the same way any other dead task is (`task.done()`) and restarted automatically, with
  the same decaying failure counter and eventual full-reboot fallback as any other task.
  **"Restart Microdot if it crashes" is therefore already implemented generically — it does not need
  Microdot-specific supervisor code —** provided the failure actually terminates that task rather
  than being silently contained at a level the supervisor never observes (answered by the next
  bullet: each connection is its own Task, so a per-connection failure never reaches this level at
  all — only a fully-dead server task does).
- **Each accepted connection runs in its own independent `asyncio.Task`** (confirmed against
  `extmod/asyncio/stream.py`'s `Server._serve()`, which calls `core.create_task(cb(s2s, s2s))` per
  accepted connection — the same isolation CPython's `asyncio.start_server()` gives). Combined with
  the blanket per-request catch above, the one confirmed gap (a non-`OSError` escaping
  `Response.write()`/`handle_request()`) only ever takes down that one client's connection Task —
  the rest of the Microdot server, including its accept loop, keeps running unaffected. "Microdot
  restarts itself when it crashes" (the task-supervisor point above) stays a backstop for a fully-
  dead server task, not something made load-bearing by this one gap.
- `errorhandler()`'s two lookup keys are independent and easy to conflate: **numeric HTTP status
  code** (`@app.errorhandler(404)`, also what `abort()`/`HTTPException` resolves through — matched
  by `exc.status_code`, never by exception class) versus **Python exception class**
  (`@app.errorhandler(SomeException)`, matched by exact class then MRO walk). Registering
  `@app.errorhandler(HTTPException)` would never fire for an `abort()` call; the status-code form is
  required for that.
- The deployed, out-of-scope `python/CommonDrivers/microdot.py` copy already implements essentially
  the same protective architecture (blanket per-request catch, exception-class + status-code error
  handlers with MRO fallback) — this safety model predates the `ext/microdot.py` v2.6.2 vendoring,
  it is not a new v2.6.2-only improvement. One confirmed version-drift detail:
  the deployed copy's `HTTPException` branch invokes a registered status-code handler directly
  rather than through the async-safe `invoke_handler()` wrapper v2.6.2 uses uniformly (so a
  registered handler there would need to be a plain sync callable) — irrelevant today since neither
  app currently registers any handlers, but worth remembering if the current deployed codebase's
  REST layer is ever touched again before the refactor lands.

## A.6 Datasheets

The `datasheets/` folder (root of the repo) holds real datasheet PDFs the project owner has
collected for the sensors/chips this codebase drives (currently: `bmp3xx/`, `fram/`, `pico w/`,
`scd30/`, `sgp40/`) — read the actual PDF from here first for any hardware-interaction claim
(register layout, opcodes, timing, electrical characteristics), rather than reconstructing it
from training memory or web search. If a datasheet you need isn't in this folder and you can't
download it yourself (blocked fetch, paywall, dead link, etc.), say so explicitly and immediately
rather than silently falling back to web search summaries or training memory for a claim the real
datasheet would settle — the project owner will add it to `datasheets/` if you tell them what's
missing (exact part number / document number is enough, a specific URL isn't required).

**BMP390 specifically**: `datasheets/bmp3xx/` holds BMP384/BMP388 but not BMP390 itself. The
project owner has confirmed directly that the whole BMP3xx family (384/388/390) shares the same
register map/protocol, so `asy_bmp3xx_driver.py` treating BMP390's `0x60` chip ID the same as the
other two is correct, not just an unverified assumption — the PDF's absence from `datasheets/` is
a documentation-completeness gap only, not an open technical question anymore.

## A.7 `src/sensortask_wozi.py` construction order and dependency graph

`src/sensortask_wozi.py` is the assembled, testable refactor prototype (the "wozi" device variant
only — see A.3): an `async def build_system(*, cfg_path: str = "", debug: int | None = None,
web_host: str = "0.0.0.0", web_port: int = 80) -> None` function doing pure construction plus the
`setup()` batch below (no task loop of its own — every constructed object is assigned to a
module-level global, declared `global` at the top of the function, not returned), and `async def
main()` (calls `build_system()`, then `start_timers()`/`start_and_check_tasks()`). Neither function
blocks at import time — the real firmware entry point that does is the separate, minimal
`boot_entry/wozi_boot.py` (`import asyncio; from sensortask_wozi import main; asyncio.run(main())`),
kept apart specifically so `import sensortask_wozi` stays safe under `tests/test_sensortask_wozi.py`
and every other test file that imports it.

**Why construction order matters**: `AsyFramManager` is a bump-pointer allocator — `get_chunk()`/
`get_timestamped_chunk()` carve out fixed offsets in call order, so a device's *instantiation
order* of these calls is its on-chip layout and must stay identical across firmware versions for
existing stored data to keep decoding correctly (the "FRAM chunk determinism rule", A.4 above).

**Construction order, top to bottom** (module-level object names as they appear in
`build_system()`):

1. `watchdog = WDT(timeout=8000)` — hardcoded at construction time, no injection point (so no code
   path can ever disable it once armed).
2. `conn = AsyConnTime(...)` — owns `DNSServer` internally (`captive_dns.py`).
3. `ntp = AsyNtpClient(conn.get_wifi_mode_lock(), conn.network_available, conn.get_dns_server_ip,
   ...)` — takes bound methods off `conn`, not a direct import-time reference.
4. `i2c0`, `i2c1` = `asy_i2c_driver.I2C(...)` ×2.
5. `spi0` = `asy_spi_driver.SPI(...)`.
6. `fram = AsyFramManager(spi0, 1, max_size=0x2000, ...)` — constructs `FRAM_SPI` internally with a
   shared `logger=`; allocates no FRAM chunk of its own.
7. `sysfunct = SystemService(ntp.ntp_issynced, watchdog=watchdog, fram=fram, ...)` — **FRAM chunk
   1**.
8. `sgp_reader = SGP40_Reader(i2c1, sgp_comp_callback, fram_storage=fram,
   fram_ntp_callback=ntp.ntp_issynced, ...)` — **FRAM chunks 2 and 3**, in this fixed sub-order
   within `SGP40_Reader.__init__` itself: chunk 2 is `self.pr` (already FRAM-backed via
   `fram_storage` forwarded as `fram=fram_storage` into `super().__init__()`, which calls
   `make_logger()` → `PrintLogHistoryStore.__init__()` → `fram.get_chunk()`); chunk 3 is the VOC
   backup itself (`self.ts_storage = fram_storage.get_timestamped_chunk(...)`, a few lines later).
   Both are unconditional whenever `fram_storage`/`fram_ntp_callback` are non-`None`, which they
   always are in the real wiring.
9. `bmp_reader = BMP3xx_Reader(i2c1, ...)` — no `fram=`, in-memory logging only.
10. `scd_reader = SCD30_Reader(i2c0, 8, trigger_sec=3, ...)` — no `fram=`, no config schema at all
    (params live on-sensor).
11. `pixel = NeopixelDriver(15, fram=fram, ...)` — **FRAM chunk 4**.
12. `notify_service = NotificationCoordinator(pixel.request_signal, ntp.cettime, fram=fram, ...)`,
    staged registration (`register()` ×3 for `WarnCO2`/`WarnVOC`/`WarnHum`, then `finalize()`
    exactly once — the single point `notify_service.pr`/`notify_service.cfgmgr` come into
    existence) — **FRAM chunk 5**.
13. `conn.set_ext_led(pixel)` — wires the WiFi-status LED callback after both exist.
14. `app = Microdot(); webserver = WebserverService(app, sensors=(scd_reader, bmp_reader,
    sgp_reader), settings={...}, system_cmd=..., notification_led=..., notification_pause=...,
    status_sources={...},
    maintenance_sensors=(("SGP40", ...),), error_sources=_collect_error_sources(),
    static_mount="/html", host=web_host, port=web_port)` — registers every real driver's REST
    surface; built here because every module it registers must already exist. **No `fram=`** —
    deliberately RAM-only: a per-call/outer-cap connection-reclaim warning (see A.8's "Connection
    hardening" below) could churn far faster than any sensor's rare-hardware-fault log, and this
    keeps the five-chunk FRAM order above unchanged — no sixth chunk. `static_mount="/html"`
    registers the generic `/`+`/<path:filename>` static-file route pair *last*, after every API
    route, so an exact-match API route always wins over the wildcard (Microdot's `find_route()`
    returns the first registered pattern that matches). `web_host`/`web_port` default to today's
    production values (`"0.0.0.0"`/`80`); a Unix-port integration run overrides them to a
    non-privileged host/port (see `digital_twin/run_wozi_integration.py`).
15. `sysfunct.set_level_setters(_collect_level_setters())` — collects every logger's own
    `set_level()` bound method (see "Debug-level registry" below) into `sysfunct`'s registry, sync,
    after every module (including `notify_service.finalize()` and the webserver from step 14) has
    fully constructed.
16. **Grouped `await x.setup()` batch** (not interleaved with construction above): `await
    sysfunct.setup()` → `await fram.setup()` → `await conn.setup()` → `await ntp.setup()` → `await
    sgp_reader.setup()` → `await bmp_reader.setup()` → `await notify_service.setup()`. These are
    independent readiness domains (`sysfunct.setup()` is its own local `config_SYSTEM.cfg`;
    `fram.setup()` is FRAM-hardware/SPI readiness; the rest are each module's own local-JSON-config
    `ConfigManager.setup()`, unrelated to FRAM or each other) with one hard ordering constraint:
    `notify_service.setup()` is only valid after `finalize()` (step 12) has run — `self.cfgmgr`
    doesn't exist before then — which batching at the end satisfies automatically. `sysfunct` goes
    first so every subsequent `setup()` call's own diagnostic logging already reflects the real
    persisted debug level. `conn`/`ntp` both need `cfgmgr.setup()` too (both are
    `SensorReaderConfig` subclasses) and are placed right after `fram`'s slot, matching their own
    real construction order (both built before `fram`/`sysfunct`).

**Real FRAM chunk order**: `SystemService` → `SGP40_Reader` (its own error log, chunk 2) →
`SGP40_Reader` (VOC backup, chunk 3) → `NeopixelDriver` → `NotificationCoordinator`. Five chunks
total. Must stay in this relative order in any future change, regardless of byte offset (which
doesn't matter per the FRAM chunk determinism rule in A.4).

**Task/timer starter collection** (`_collect_task_starters()`/`_collect_timer_starters()`, called
from `main()`, never from `build_system()` itself): every constructed module's own
`get_task_starters()`/`get_timer_starters()` is called uniformly, not hand-copied per module —
including `AsyConnTime.get_task_starters()`'s `start_hotspot_timeout_watcher` (the task backing
`hotspot_time_min`'s actual timeout) and `webserver.get_task_starters()`'s `_start_serving` (no
bespoke restart mechanism — it participates in `start_and_check_tasks()`'s ordinary supervisor loop
like every other module).

**Debug-level registry** (`_collect_level_setters()`, `system_service.py`'s
`SystemService.set_level_setters()`/`_apply_level()`/`get_debug_level()`/`set_debug_level()`) — a
registry of function references, not a shared mutable value: `_collect_level_setters()` collects
every logger's own `set_level` **bound method** (every module's own top-level `self.pr`, every
nested `cfgmgr.pr`, and `AsyConnTime`'s own separately-named `dns_server.pr`) into a flat list,
mirroring `_collect_task_starters()`/`_collect_timer_starters()`'s own shape.
`sysfunct.set_level_setters(...)` receives that list once, at boot (construction step 15 above) —
stored, not consumed immediately, since it's called again on every future level change.
`SystemService._apply_level(value)` iterates the registry calling each entry with the new value,
each wrapped individually in `try`/`except Exception` so one bad entry can't stop the rest of the
registry from updating; both `setup()` and `set_debug_level()` call it, and `set_debug_level()`
additionally validates via `ConfigManager.write_config()`'s own `type_or_range_error` range check
first. Calling `set_level()` on any `PrintLog` instance at any time is safe: the only interrupt
handler in `src/` (`asy_scd30_driver.py`'s pin IRQ) never touches logging, every real `PrintLog`
call site is either plain synchronous code or a soft `machine.Timer` callback (never true hardware
preemption — see F.1's soft-Timer-callback fact), and `self.level` is a single plain `int`
attribute (an atomic store on this platform, no torn-write case) — worst case from a level change
racing a log call is one line using the old-vs-new threshold at the boundary, not corruption.

**Dependency graph** (who holds a reference to whom): `ntp` holds `conn`'s `wifi_mode_lock`,
`network_available`, `get_dns_server_ip` — bound methods, not a module import. `notify_service`
holds `pixel.request_signal` and `ntp.cettime` — same pattern. `conn` holds `pixel` (via
`set_ext_led()`, called after both exist) for the WiFi-status LED. `sgp_reader` holds
`ntp.ntp_issynced` for its VOC-backup timestamp validity check. Every `*_Reader`/service constructs
its own `ConfigManager`/`PrintLog` instance internally (`base_classes.py`'s
`SensorReaderConfig.__init__`) — no cross-module config sharing anywhere. No module in `src/`
imports another `src/` module *by name* to reach a sibling driver/service — every cross-module
dependency in the real wiring is constructor-injected (bound method or object reference), so the
dependency graph is already a clean DAG at the Python-import level; the object graph above is the
only thing a future rewrite of this file needs to reproduce.

Full coverage of the above (construction order, FRAM chunk order, the `setup()`-batch order and its
`notify_service`/`finalize()` constraint, task/timer starter collection, the debug-level registry)
lives in `tests/test_sensortask_wozi.py`.

## A.8 REST API endpoint reference (`src/asy_webserver_service.py`)

`WebserverService` (see A.5 above for what Microdot itself already guarantees underneath it) is a
**registration-based** service: modules hand it named callback groups at construction
(`sensors=`, `settings=`, `system_cmd=`, `notification_led=`, `notification_pause=`, `status_sources=`,
`maintenance_sensors=`, `error_sources=`, all supplied as lists/dicts at init — see
`src/sensortask_wozi.py`'s real construction-step-14 call for the live wiring) and it
auto-constructs the REST surface from them, generator-friendly: a future per-variant build-script
generator only ever needs to know "does this variant have module X," never anything about field
names or endpoint shapes.

**Six external endpoints**, registered in `WebserverService._register_routes()`:
`/measurements`, `/sensors`, `/networking`, `/system`, `/status`, `/notification`. Clean
live-vs-settings split: `/measurements` and `/status` are the only two live-data endpoints (no
persisted settings in either); `/sensors`, `/networking`, `/system`, `/notification` are pure
settings (no live telemetry in any of them).

- **GET shapes**:
  - `/measurements` → `{"SCD30": {...}, "SGP40": {...}, "BMP3XX": {...}}`, one entry per registered
    sensor reader, each `get_dict_data()`.
  - `/sensors` → same per-sensor sub-structure, each `get_dict_cfg()`.
  - `/networking` → flat settings only: `SSID, PW(masked), Country, Hostname, LedWifiOn, NTP_Host,
    NTP_Offset_S, NTP_Interv_H`.
  - `/system` → flat settings only: `DebugLevel, GMTOffset, DSTOffset`.
  - `/notification` → flat settings only: `OnH, OnM, OffH, OffM, FlashBri, Interv, FlashDur,
    AutoOn, WarnCO2, WarnVOC, WarnHum`.
  - `/status` → live-only, sub-structured with top-level keys named after the settings endpoints
    they mirror: `networking` (`WifiUptime, Mode, Connected, IP, IPv4, Subnet, Gateway, DNS, Rssi,
    NtpSynced, NtpLastSyncAge, NtpLastSync`), `system` (`SysUptime, BootSignature, MemPaused,
    LocalTime, UtcTime`), `sensors` (one entry per sensor with maintenance data — today only
    `SGP40`'s `BackupTS`/`RestoreTS`), `notification` (`Triggered, TS, PauseTime`), `errcount` (one
    entry per registered module plus one per `ConfigManager` instance, `CFGMGR_<name>` — `"counter"`
    always present, `"history"` present exactly when that logger persists `ErrNum`/`ErrType`
    entries).
- **PUT shapes** — one sparse JSON body per endpoint, no `cmd` envelope: any field present is
  applied, any field/sub-object omitted is left untouched, unknown fields are silently ignored
  (`ConfigManager.write_config()`/`_set_dict_cfg()`'s existing per-key tolerance, extended to be the
  only strategy at the HTTP layer too).
  - `/measurements` — no PUT.
  - `/sensors` — `{"SCD30": {<any subset of TempOffs,MeasInt,AmbPres,Altitude,ForceCalRef,SelfCal,
    ContMeas>}, "SGP40": {<any subset of BackupPeriod,BackupMaxAge,WaitTimeNTP,SGPResetVOC>},
    "BMP3XX": {<any subset of the 8 fields>}}`. SCD30 dispatches through its own schema-driven,
    non-persisting setter (`asy_scd30_driver.py` — every validated field calls straight through to
    its already-existing individual I2C setter method; no `cfgmgr`, no local JSON file, since
    SCD30's settings live in the sensor's own NVM, see A.4's `AmbPres` note).
  - `/networking` — `{<any subset of SSID,PW,Country,Hostname,LedWifiOn,NTP_Host,NTP_Offset_S,
    NTP_Interv_H>}`; a body touching only `AsyConnTime`'s WiFi-credential fields fires
    `conn.reconnect_wifi()`, only `LedWifiOn` fires nothing, only NTP fields fire
    `ntp.ntp_force_sync()` — one `SettingsGroup` per field subset, per module, keeps these
    independent (mirrors the legacy `setNetwork`/`setWiFiLED` route split).
  - `/system` — `{<any subset of DebugLevel,GMTOffset,DSTOffset>, "SystemCmd":
    "reboot"|"bootloader"|"mempause"}` — `SystemCmd` optional, strictly enum-validated;
    `mempause`'s duration is always the fixed 300s, never client-supplied.
  - `/status` — `{"ResetErrors": true}` only (absent/`false` is a no-op) — resets every registered
    module's error counter *and* history in one call.
  - `/notification` — `{"lightCmdLED": {"r":.., "g":.., "b":.., "t":..}, "PauseTime": int, <any
    subset of OnH,OnM,OffH,OffM,FlashBri,Interv,FlashDur,AutoOn,WarnCO2,WarnVOC,WarnHum>}`.
    `PauseTime` is range-checked `0`-`3600` inclusive by `_dispatch_notification_pause()` itself
    (rejected as `"Invalid"`, not silently clamped) before ever reaching
    `NotificationCoordinator.set_override_led()`, whose own `LockedCounter.set_value()` clamps
    into the same range — matching legacy's `pauseAutoLED` command's own reject-out-of-range
    behavior rather than relying on the clamp.

**Numeric int/float coercion policy** (`config_manager.py`'s `coerce_numeric()`, called from
`type_or_range_error()`): every schema-backed int/float field, plus the two dispatch-only numeric
fields that reuse the same function against a synthetic `FieldSchema` (`PauseTime` via
`_dispatch_notification_pause()`) or the same acceptance policy directly (`lightCmdLED`'s r/g/b/t
via `sensortask_wozi.py`'s `_notification_led_callback()`), applies one uniform rule instead of
each caller hand-rolling its own int/float shape check: a JSON int is **always** accepted for a
float-typed field (coerced to float — a blanket accept, with no exact-round-trip check on this
direction); a JSON float is accepted for an int-typed field **only when it carries no fractional
part** (e.g. `5.0` → coerced to `5`) — a fractional value (`5.7`) is rejected outright as
`"Invalid"`, the same treatment an out-of-range value gets, never truncated or rounded. The intent
is for both directions to be symmetric ("accept only what's exactly representable, either
direction") and never silently discard a digit the caller actually sent — true for the float→int
direction (an exact `int(check_val)`/`float(as_int) == check_val` round-trip is checked, see
`coerce_numeric()`), but the int→float direction is a **known, accepted gap** in that symmetry, on
the premise that every int is representable as a float — true only up to a float's mantissa
precision (Part F.1's `MICROPY_FLOAT_IMPL_FLOAT`-vs-`_DOUBLE` fact), not in general. Accepted as-is
because no currently-registered float field's own `min`/`max` bounds go anywhere near that range
(the largest today is BMP3xx's `SeaLevelOffs` at `5000.0`) — the field's own range check already
catches every value that could otherwise slip through, in practice; see `coerce_numeric()`'s own
inline comment and `tests/test_config_manager.py`'s
`test_coerce_numeric_large_int_to_float_precision_limit_is_a_documented_accepted_gap` for this same
caveat at the code/test level. `bool` is still never accepted for an int or
float field either way (`type()`, not `isinstance()`, already excludes it — see A.4/F.4's
discussion of this same distinction elsewhere). NaN/±inf attempting int-coercion are caught (not
raised) via MicroPython's own `int(float)` exception shapes (`ValueError` for NaN, `OverflowError`
for ±inf — confirmed against `py/objint.c`'s `mp_obj_new_int_from_float()`) and rejected the same
way as any other non-representable value. The website's JS mirror (`js/mock-server.js`'s
`coerceAndValidate()`/`dispatchRangedAction()`/`dispatchLightCmdLed()`) applies the equivalent
policy — trivially simpler there, since JS has no int/float runtime type distinction to begin with
(`5` and `5.0` parse to the identical JS number): only a `field.float`-marked field's own value is
ever checked for having no fractional part, via `Number.isInteger()`, with no need to recover or
compare the original JSON literal's shape at all (the now-removed `scanNumericLiteralShapes()`
JSON-text regex scan, and `js/render.js`'s now-removed `serializePutBody()` decimal-point-forcing,
both existed only to fight that literal-shape problem under the old strict-shape-match policy).

**GET copy-safety**: `get_dict_data()` (via `config_manager.make_dict()`), `ConfigManager.get_dict()`,
and `PrintLogHistory.get_log()` all build a brand-new dict/list of copied scalar values on every
call with no `await` in the middle of construction, so MicroPython's cooperative, non-preemptive
scheduling already makes each snapshot atomic — no caller ever gets a live reference into
`_cache`/`history`. **One known, still-open exception**: `SCD30_Reader.get_dict_cfg()` (entirely)
and three of `BMP3xx_Reader.get_dict_cfg()`'s fields (`PressOvers`/`TempOvers`/`FiltCoeff`) are live
hardware-readback fields whose callback `await`s a real I2C transaction mid-dict-construction, so a
concurrent config write interleaving between two such awaited reads can produce one response
mixing pre- and post-write values across fields — see BACKLOG.md for this item's tracked status.

Connection hardening (per-call/outer-cap timeouts, reject-when-full at the connection-count
ceiling, no bespoke whole-server-restart mechanism — the webserver task participates in
`start_and_check_tasks()`'s ordinary supervisor like every other module) and the `Connection: close`
response header are implemented directly in `WebserverService`/`_TimeoutStreamProxy`
(`src/asy_webserver_service.py`) — see that module's own inline comments (near `max_connections`/
`_TimeoutStreamProxy`) for the current constants and mechanism, and `tests/test_asy_webserver_service.py`
for the full regression
coverage (including its F.9 soak test, `gc.mem_free()` flat over 100+ start/wedge/reclaim cycles).

## A.9 Website stub / frozen-HTML pipeline

`html_stub/` (7 flat files: `index.html`, `style.css`, `functions.js`, `favicon.ico`,
`nettimeconfig.html`, `sensorconfig.html`, `systemledconfig.html`) is placeholder ("Hello
world"-shaped) content standing in for `html_raw/{general,wozi}`'s real site content in the
refactored build — real website content is out of scope for the refactor prototype (see A.3).

`scripts/build_frozen_html.sh` gzips a temp copy of the source directory(ies) (`html_stub/` by
default, overridable via the `HTML_SRC_DIRS` env var — a space-separated list merged into one flat
tree first, mirroring `build-wozi.sh`'s own `general`+board-variant merge; the merge step is a
recursive `cp -r "$src_dir"/. "$tmp_dir"/` and the gzip step a recursive `find ... -exec gzip -9`, so
nested subdirectories such as `html/definitions/` survive intact), then runs
`PYTHONPATH=ext python -m freezefs <tmp> frozen_modules/frozen_html.py --on-import mount --target
/html --overwrite always` (never `--compress`: this project pre-gzips by hand and serves via
Microdot's `send_file(..., compressed=True, file_extension=".gz")`, which only sets
`Content-Encoding` and never decompresses on-device — mixing the two would double-encode). The
output directory is deliberately `frozen_modules/` (gitignored), not `.frozen/`: `.frozen/` is a
hardcoded sentinel in MicroPython's own import machinery (`py/builtinimport.c`'s
`MP_FROZEN_PATH_PREFIX ".frozen/"`) — any path starting with that literal string is routed straight
to the compiled-in frozen-module table, so a real file placed on disk there is silently
unimportable even though it genuinely exists. `src/sensortask_wozi.py` does a module-level,
unconditional `import frozen_html`, mounting `/html` as a side effect of the import itself (matching
freezefs's own on-import design); `WebserverService(..., static_mount="/html")` (construction step
14 in A.7 above) then registers the generic static-route pair that serves it.

`tests/test_frozen_html_integration.py` is the real-pipeline proof (imports the actual built
`frozen_html` module and drives real requests through a real `WebserverService`);
`tests/test_asy_webserver_service.py`'s Section G exercises the generic route-wiring mechanism
against a synthetic fixture, independent of the real stub content.

This section describes the generic, device-agnostic pipeline itself. The real, non-stub website that
now ships via this same pipeline (`scripts/build_website.sh`, digital-twin wiring, cross-browser
coverage) is Part H.

## A.10 Digital twin (hardware simulator)

`digital_twin/` is a set of fake `machine`/`network`/`neopixel` modules sitting at the same raw
I2C/SPI bus-transaction mocking boundary `tests/machine.py` establishes for unit tests, but with
real-time-firing `Timer`s and randomized-but-plausible sensor values, so `src/sensortask_wozi.py`
can run under the real MicroPython Unix-port interpreter and behave like it's attached to real
hardware. It is deliberately independent of `tests/` (duplicated, not shared, fakes for
`network`/`neopixel`) and needs zero twin-awareness from `src/sensortask_wozi.py` itself — the swap
is pure `MICROPYPATH` ordering. See `digital_twin/README.md` for the full reference (what's there,
how to swap it in, FRAM/SCD30 persistence, running its own tests, and the required steps for adding
a new chip fake — also covered from the driver side in Part C.11 point 9 above) and README.md's
"Digital twin (hardware simulator)" section for the user-facing quick-start commands.

**Chain-completeness requirement, generalized beyond sensor drivers (owner decision).** Part C.11
point 9 above already mandates a matching chip fake for every new *sensor* driver. That's the
specific instance of a broader standing rule: **any new module added to this project shall be
added to the digital twin, provided all requirements are met for it to form a complete chain
inside the twin** — the twin's whole point is exercising the real, assembled system end to end, not
just the three sensors it started with. Two concrete shapes this takes:

- A new **sensor driver**: the existing per-driver checklist (Part C.11 point 9) — bus-level chip
  fake, wired into `machine.py`, exercised all the way up through its REST endpoint.
- A new **common/base module** (e.g. a shared mixin `base_classes.py` gains, or a new cross-cutting
  service alongside `system_service.py`/`asy_webserver_service.py`): if it's wired into
  `sensortask_wozi.build_system()`'s own real object graph, it is automatically exercised by every
  twin-backed run and test tier already listed here — no separate "does it need a twin fake"
  question exists for a module that has no hardware surface of its own to fake in the first place.

"As long as all requirements are met for it to form a complete chain" is the actual gate, not an
automatic yes: a module only joins the twin once it can be driven through a real, observable path —
bus/hardware surface (if any) through to construction, to `setup()`, to whatever REST-visible
behavior it produces. A module that can't yet complete that chain (e.g. it depends on hardware this
project has no chip fake for yet) stays out until the missing piece exists, flagged the same way
any other genuinely-blocking gap is (CLAUDE.md's "flag, don't silently change" working agreement) —
not silently deferred with no record.

**Automated CI suite (`scripts/run_digital_twin_ci.sh`).** The manual on-demand walkthrough this
project's own baseline verification passes used (fresh clean boot, every GET/PUT endpoint,
`DebugLevel=5` verbose logging from boot, bus/WiFi/network fault injection with logging still on,
settings and error-history persistence across a real process restart, recovery after a fault
clears, the automated soak check) is also wired into CI as its own job (`digital-twin-e2e` in
`.github/workflows/ci.yml`), `needs: unit-tests`. **Clean**: wipes any leftover
`digital_twin/*.json`/`digital_twin/config/` state before starting, so every run — CI or local —
begins from a genuinely blank twin. **Build**: builds the MicroPython Unix port (cached, same
convention as `scripts/test.sh`) and `frozen_modules/frozen_html.py` — via `scripts/build_website.sh
wozi`, i.e. the real, production website (Part H.7), not the generic `html_stub` default; a build
failure fails the job before any test phase runs. **Test**: `scripts/_digital_twin_ci_suite.py` (a self-contained
`uv run` CPython script — it only orchestrates the MicroPython subprocess and speaks plain
HTTP/UDP to it, the code under test still only ever runs under the real Unix-port interpreter)
drives `digital_twin/run_wozi_integration.py` through eleven real subprocess runs covering: fresh
boot + every GET/PUT endpoint; settings persistence + verbose logging across a real reboot; a
sustained/high-repeat-count ("permanent") fault matrix across every bus-level error-counted module
at once, proving both graceful degradation *and* that the (simulated) watchdog never starves under
bounded-but-sustained failure; a persistence-correctness sweep checking both directions (FRAM-backed
modules should survive a reboot, in-memory-only modules should not); recovery after a small bounded
fault clears; WiFi hotspot fallback proving a real answered UDP DNS query, not just an internal
state flip; NTP permanently unreachable; the one dedicated case that genuinely can starve the
watchdog — a real blocking hang inside a chip fake's handler (`--hang`,
`digital_twin/_fault_injection.py`'s `inject_hang()`/`maybe_hang()`) that freezes the whole
interpreter past the WDT window, proving the backstop itself actually engages; and a dedicated
clean soak run. Building this suite surfaced three confirmed Unix-port-only `socket` quirks
(`BACKLOG.md`'s "Real-hardware verification gap for `asy_udp_socket.py`/`captive_dns.py`" has the
full source-level account) that made a real UDP round trip (DNS, NTP) genuinely impossible under
this harness — `bind()`/`connect()`/`sendto()` rejecting `AsyUDPSocket`'s own plain
`(host, port)` tuple, and `recvfrom()` returning a raw C struct instead of the `(str, int)` shape
production code expects — all three correct, required behavior for real rp2 hardware (confirmed by
reading both the Unix port's and rp2's actual socket module C sources side by side, not just a type
stub), so not something to fix in `src/`. Worked around entirely from twin-side code instead:
`digital_twin/_unix_port_udp_addr_shim.py`, applied by `run_wozi_integration.py`'s own `main()`
before anything constructs a socket — see that module's own docstring and
`digital_twin/README.md`'s own section on it for the full mechanism. This closes the gap for good:
run 7 now asserts a real DNS reply, not just that the hotspot state flipped. See
`digital_twin/README.md`'s "Automated CI suite" section for the full per-run breakdown.

---

# Part B — Toolchain & Build

One command sets up (or updates) everything needed to build MicroPython firmware for the
Raspberry Pi Pico W: MicroPython itself, a matching `pico-sdk`, a version-matched `picotool`,
and the ARM cross-compiler — plus a host-side MicroPython Unix port build, used for running
tests under the real interpreter later instead of just CPython with MicroPython-flavored stubs
on top (see Part E.1, "Why not pytest").

## B.1 Why this isn't just "apt install the toolchain"

Two problems make a naive install unreliable, and this script exists specifically to solve
both:

1. **The four pieces have to agree with each other exactly, or the build silently breaks.**
   `picotool` has enforced a matching major.minor version against the `pico-sdk` it's built with
   since pico-sdk 2.0.0 (a mismatch fails outright with "Incompatible picotool installation
   found"), and the `pico-sdk` version has to be whatever MicroPython's own build actually
   compiles against — not just "some recent pico-sdk". Getting this right by hand means cross-
   referencing three separate repos' tags/submodule pins every time you change versions. See
   B.3 ("How it works") below for how the script avoids this by construction instead of by
   careful bookkeeping.
2. **Every dev machine has its own installed tools and environment variables, and any of them
   could silently change what gets built.** A leftover `CFLAGS` from an unrelated project, a
   personal `~/bin/cmake` earlier in `PATH`, a different `picotool` already installed — none of
   these should be able to change the output of a build that's supposed to be reproducible. See
   B.4 ("Environment isolation") below.

## B.2 Quick start

```sh
uv run toolchain/setup_toolchain.py                              # install/update per versions.toml
uv run toolchain/setup_toolchain.py --latest                      # pin + install newest stable MicroPython
uv run toolchain/setup_toolchain.py --micropython-ref v1.26.1     # build a specific ref instead
uv run toolchain/setup_toolchain.py --clean                       # wipe build dirs, then rebuild from scratch
uv run toolchain/setup_toolchain.py --skip-apt                    # skip apt-get install (packages already present)
uv run toolchain/setup_toolchain.py --jobs 4                      # override parallel make jobs (default: os.cpu_count())
uv run toolchain/setup_toolchain.py --toolchain-dir /path/to/dir  # install somewhere other than ~/pico-toolchain

uv run toolchain/setup_toolchain.py test                          # re-verify an existing install, offline
```

`--toolchain-dir`/`--jobs` also apply to `test` (both `setup` and `test` take them, via a shared
parent parser); `--micropython-ref`/`--latest`/`--skip-apt`/`--clean` are `setup`-only.
`scripts/test.sh` exposes `--skip-apt` as `SKIP_APT=1` (see its own header comment) for the
`setup` call it makes on a cache miss.

No `pip install`/venv setup needed by hand for the script itself — `uv run` provisions an
ephemeral, cached interpreter (see B.8, "Why not a full venv"). There are two subcommands,
`setup` and `test`; `setup` is the default if you omit it, so all of the invocations above except
the last one are really `setup` in disguise. Both also build and verify a MicroPython Unix-port
interpreter at the same pinned ref (sharing the same `--toolchain-dir` checkout, just a different
`ports/` subdirectory) alongside the RP2040 firmware — see B.3 below and Part E.1 ("Why not
pytest") for why the test suite runs under that instead of CPython/pytest. `scripts/test.sh` runs
`setup` automatically the first time it needs the interpreter. That Unix-port binary is
always built with `MICROPY_PY_SYS_SETTRACE=1` (an inert, behavior-neutral hook check when unused —
see `build_unix_port()`), so the same binary backs both plain `scripts/test.sh` and
`scripts/test.sh --coverage` (see Part E.5, "Coverage") — no second Unix port
build. The RP2040 firmware build never gets this flag; it's dev/test tooling only.

**Prerequisites:**

- `sudo` access (used for `apt-get install` and `picotool`'s `make install`).
- Outbound network access to GitHub and your distro's package mirrors.
- [`uv`](https://docs.astral.sh/uv/) itself already installed (`pip install uv`, or the official
  `curl -LsSf https://astral.sh/uv/install.sh | sh` installer).
- Ubuntu's `universe` apt component enabled — the default on every official Ubuntu image, so
  this only matters on a deliberately minimal base (e.g. a bare `debootstrap` rootfs, which
  enables only `main` unless told otherwise); `gcc-arm-none-eabi` and its newlib packages live
  in `universe`.

## B.3 How it works

The whole design follows from the two problems in B.1. Walking through what `setup` actually
does, in order:

1. **Check out MicroPython at the pinned ref.** `versions.toml` records exactly one hand-picked
   version — the MicroPython tag — because everything downstream can be *derived* from it rather
   than tracked separately (see step 2). This is also the only version a human ever needs to
   decide on; bumping it (by hand, or via `--latest`) is the entire "what do I upgrade to" question.
2. **Derive the matching `pico-sdk` version, instead of pinning it separately.** MicroPython's own
   git repo already records which `pico-sdk` commit it builds against, as an ordinary git
   submodule pin at `lib/pico-sdk`. The script reads that pin directly
   (`derive_pico_sdk_commit()`) rather than maintaining a second, independent version number that
   could drift out of sync with the first one.
3. **Derive the matching `picotool` version the same way.** Since `picotool` only requires a
   major.minor match against `pico-sdk` (not an exact commit), the script resolves the derived
   pico-sdk commit to its nearest tag, takes the major.minor, and picks the newest `picotool` tag
   sharing it (`derive_picotool_ref()`). Two derivations, zero independently-tracked version
   numbers beyond the one in step 1.
4. **Install the ARM cross-compiler from the distro's `gcc-arm-none-eabi` package.** Unlike the
   other three, this one genuinely doesn't need a hand-tracked pin — it's a known-working,
   reproducibly-installable toolchain for pico-sdk 2.x straight from `apt`.
5. **Build everything inside an explicitly constructed, isolated environment**, not whatever the
   caller's shell happens to have set — see B.4 below. This is what makes
   the versions derived in steps 1–4 the actual versions used, instead of being second-guessed
   by a stray environment variable or a shadowing binary.
6. **Verify the result before declaring success**, every single run, via a frozen-bytecode chain
   rather than separate throwaway checks: freeze one small test module into both the Unix port
   and the RP2 firmware, import it *by name* inside the Unix port binary and check its result,
   clean up, then rebuild a vanilla Unix port as the standing test rig (see B.6 below,
   and `run_verification_sequence()`'s docstring in `setup_toolchain.py` for the exact step
   order). A `setup` that finished without running this chain would just be an assertion that the
   pieces are probably fine; running it is what makes it a proof.

Step 6 is intentionally a mix of from-scratch and incremental: the firmware and Unix-port builds
always wipe their build directories first, so "builds with zero errors/warnings" is a genuine
proof every run rather than a cached one, but `mpy-cross`'s build directory is otherwise left
alone — if nothing in its source changed, it just relinks instead of recompiling. That's a
deliberate, useful property (a `setup`/update re-run doesn't waste time re-verifying unchanged
output), not an oversight — but it means there's normally no single command that forces
*everything* back to a truly from-scratch build state without also re-cloning gigabytes of
unchanged git history. `--clean` is that command: it wipes every build-artifact directory
(`picotool/build`, `mpy-cross/build`, `ports/rp2/build-<board>`, `ports/unix/build-standard`, via
`clean_build_dirs()`) before the steps above run, without touching the git clones themselves,
then proceeds through the normal build+verify flow — so it ends in the same state a genuinely
fresh install would.

`test` is `setup` with steps 1–4 skipped: it assumes an install already exists at
`--toolchain-dir` and just re-runs step 6's verification chain against whatever is already
checked out there. That split exists because steps 1–4 need network/apt access and can change
what's installed, while the verification chain doesn't need either and is what you actually want
to re-run repeatedly (locally, or eventually in CI — see B.10 below) to confirm the
toolchain still builds cleanly.

## B.4 Environment isolation

Every subprocess this script runs — `git`, `apt-get`, `cmake`, `make`, `picotool`, the built
`mpy-cross` binary — gets an explicit, constructed environment instead of inheriting the
caller's shell wholesale. Two flavors, both defined right at the top of `setup_toolchain.py`:

- **`build_env()`** — for the actual compile steps (picotool's build, `mpy-cross`, the firmware
  build, running the cross-compiled sample): a fixed, deterministic `PATH`
  (`/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`) plus a small allowlist
  (`HOME`, `USER`, `LOGNAME`, `TERM`, `TMPDIR`). Everything else — `CC`/`CXX`/`CFLAGS`/
  `CXXFLAGS`/`LDFLAGS`/`MAKEFLAGS`, any `CMAKE_*` variable, `PICO_SDK_PATH`/`PICO_BOARD`,
  `PYTHONPATH`, a leftover `http_proxy` meant for some unrelated tool — is dropped. The fixed
  `PATH` also means a shadowing binary earlier in the caller's `PATH` (a personal `~/bin/cmake`,
  a different `gcc-arm-none-eabi` build, an old `picotool`) can never be picked up instead of
  the toolchain this script itself just built/installed. `LANG`/`LC_ALL` are also *not* passed
  through — they're forced to `C.UTF-8` instead (see B.7 below for why
  this matters more than it looks).
- **`network_env()`** — the same base, plus whatever proxy/CA configuration is actually present
  (`HTTPS_PROXY`/`https_proxy`/`HTTP_PROXY`/`http_proxy`/`NO_PROXY`/`no_proxy`/`ALL_PROXY`/
  `all_proxy`/`SSL_CERT_FILE`/`GIT_SSL_CAINFO`/`CURL_CA_BUNDLE`/`REQUESTS_CA_BUNDLE`), explicitly
  named rather than inherited wholesale. Used for `git`/`apt-get` calls, and for the rp2 port's
  `make submodules` target specifically because that one Makefile target both fetches submodules
  over git *and* runs a preliminary `cmake` configure pass — it needs the deterministic `PATH`
  and real network access at the same time (the concrete bug this exact split was built to fix —
  see B.7 below).

`picotool`'s own install location is also pinned explicitly
(`-DCMAKE_INSTALL_PREFIX=/usr/local`, matching where it's later invoked from by absolute path)
rather than left to whatever a stray `CMAKE_INSTALL_PREFIX` or local `cmake` cache would
otherwise resolve to.

## B.5 Directory layout

```
<toolchain-dir>/          default: $PICO_TOOLCHAIN_DIR or ~/pico-toolchain
  micropython/             full clone, checked out at the pinned ref
    ports/rp2/build-<board>/    transient - built once with the frozen test module (step 6 of
                                 "Verification"), then removed in step 7; does not exist after a
                                 completed setup/test run
    ports/unix/build-standard/  host-side interpreter build output (micropython) - the one build
                                 artifact kept as a standing deliverable (step 8)
    mpy-cross/build/            cross-compiler build output (mpy-cross)
  pico-sdk/                full clone, checked out at the ref MicroPython pins
  picotool/                full clone, checked out at the derived matching tag; built + `sudo make install`ed
```

Full (non-shallow) clones are used deliberately, not just for the initial install — shallow
clones make the *update* path (fetch + checkout an arbitrary new ref) unreliable, and update
is a first-class requirement here, not an afterthought.

## B.6 Verification

Every `setup` or `test` run re-verifies the environment end-to-end via a single frozen-bytecode
chain (`run_verification_sequence()` in `setup_toolchain.py`), each step gating the next — a
`SetupError` from any step aborts the whole chain, so later steps never run against a broken
earlier one:

1. Write a small test module (`frozen_verify_test.py`: arithmetic, a comprehension, exception
   handling, a stdlib import, and a `RESULT` value to check).
2. Build `mpy-cross` (the cross-compiler).
3. Cross-compile the test module with `mpy-cross` directly — proves the cross-compiler itself
   works, independently of the freeze/build pipeline exercised next.
4. Build the Unix port (`ports/unix`, "standard" variant) with the test module frozen in via
   `FROZEN_MANIFEST=`, with no compiler errors or warnings.
5. Import the frozen module *by name* inside that Unix port binary — with no source `.py` file
   anywhere on disk for the interpreter to find — and check its result. The only way this can
   succeed is if the module was actually baked into the binary as frozen bytecode, not merely
   compiled and left on disk. `mpy-cross` and the Unix port build are now both verified. This is
   the host-side MicroPython build that tests run under (see Part E).
6. Build the RP2 firmware for the target board (default `RPI_PICO_W`) with the same test module
   frozen in, with no compiler errors or warnings. Build-only: there's no RP2 hardware here to
   run it on, so a clean build is the whole check. Freezing extra bytecode is strictly additive
   to a build — it can't make an otherwise-broken toolchain succeed — so this is a strict
   superset of what a vanilla (no frozen module) RP2 build would have proven anyway; see
   `run_verification_sequence()`'s docstring for why a separate vanilla RP2 build isn't also kept.
7. Clean up the RP2 firmware and Unix port build directories from steps 4–6. `mpy-cross`'s and
   `picotool`'s build output are *not* touched — both are real toolchain deliverables needed for
   actual project work later, not verification-only artifacts.
8. Rebuild a vanilla (non-frozen) Unix port. This becomes the standing test rig used for running
   tests under the real interpreter later (see Part E).

Any failure aborts with a non-zero exit and the build log leading up to it. Note this means a
completed `setup`/`test` run does **not** leave a vanilla RP2 `firmware.uf2` anywhere — only the
(also cleaned-up) frozen-module build from step 6, which existed purely to prove the toolchain
works. The Unix port from step 8 is the only build artifact kept as a standing deliverable.

## B.7 Evidence this actually works

Verified end-to-end, not just written down: a genuinely clean Ubuntu 24.04 system (a
`debootstrap`-built `noble` chroot with nothing preinstalled beyond the minimal base) installs
every dependency itself and passes the full 8-step verification chain, for both the
currently-deployed `v1.26.1` pin and the latest stable release; an in-place update from one
pinned version to another re-checks out existing clones (no re-clone), rebuilds only the affected
pieces, and leaves no stale state from the old build; `test` in isolation (no `setup`-only steps)
completes in ~30s against an existing install with no network/apt access; and both `setup`/`test`
were run against a deliberately hostile environment (poisoned `PATH` with fake `cmake`/
`arm-none-eabi-gcc`/`picotool`, garbage `CFLAGS`/`CMAKE_*`/`PICO_SDK_PATH`, a non-English `LANG`)
with zero trace of the injected poison surviving into the build — this is what B.4 ("Environment
isolation") is verified against, not just designed against. See CLAUDE.md's "Pre-push
verification" for the standing recipe to re-run this kind of check after a change to this script
or `versions.toml`.

## B.8 Why not a full venv

This mostly isn't Python-package territory: apt packages, multi-gigabyte git source trees,
and `cmake`/`make` builds of C/C++ toolchains can't live inside a `.venv`. The one thing that
*can* be venv-managed — the installer script's own interpreter — is handled by `uv run`'s
per-script ephemeral environment (see the `# /// script` block at the top of
`setup_toolchain.py`), which is why there's no `pyproject.toml`/`uv sync` step here at all:
the script has zero extra dependencies, so `uv run` alone is the complete, single-command
setup path. The source trees and build artifacts live in `--toolchain-dir` instead
(`~/pico-toolchain` by default) — deliberately outside this git repo, matching how
`build-*.sh` already expects a sibling MicroPython tree today (see A.1 above).

## B.9 Not yet covered

This installs the generic MicroPython/pico-sdk/picotool/cross-compiler toolchain (plus the Unix
port) and proves it builds, cross-compiles, and runs real Python. It does **not** yet wire up
`build-*.sh`'s hardcoded `/home/nico/rpi_pico/...` paths or the `py-include` symlink this
project's own firmware builds expect — that's the next step (see BACKLOG.md). The Unix port build
itself **is** wired into the actual test suite now (`scripts/test.sh` runs `setup` automatically
the first time it needs the interpreter, see CLAUDE.md's "Code quality tooling") — the
remaining gap is the RP2040 firmware build, not the Unix port.

## B.10 CI perspective

A CI pipeline now exists (`.github/workflows/ci.yml`, GitHub Actions), with two jobs:
`lint-and-typecheck` (ruff/mypy) and `unit-tests`, which runs `scripts/test.sh` — building the
toolchain (including the Unix port) via plain `setup` on a cache miss and reusing the cached
`--toolchain-dir` on a hit. The cache key hashes **both** `toolchain/versions.toml` and
`toolchain/setup_toolchain.py`, not just the former — keying on `versions.toml` alone let a stale
cached binary built before `build_unix_port()` gained `MICROPY_PY_SYS_SETTRACE=1` survive
untouched across later commits, a real bug (surfaced as `scripts/test.sh --coverage` failing in CI
with `"module 'sys' has no attribute 'settrace'"` while passing locally, where a fresh
`~/pico-toolchain` always picks up the current flags) rather than a hypothetical one; see
`ci.yml`'s own cache-step comment. It does **not** yet include a real RP2040
firmware-build stage. `test` (the offline re-verification subcommand) is still written with that
eventual stage in mind (see BACKLOG.md's "Refactor targets not yet done"): a `setup`
job would provision (or restore a cache of) `--toolchain-dir` once, and a `test` job would run
against it as the actual gate — offline, fast, and not dependent on GitHub/apt reachability at
gate time. The `unit-tests` job actually running today already follows this same
provision-then-cache shape, just using `setup` directly rather than a separate `setup`/`test`
split (there's nothing to re-verify offline yet beyond what the test suite itself already
exercises). Nothing about `setup`/`test` assumes a specific CI system; they're plain script
invocations with a clean exit code, so either would drop into a different pipeline without
changes if this repo ever moved off GitHub Actions.

## B.11 Building this project's firmware

**Bumping the MicroPython version**: change `toolchain/versions.toml`'s `[micropython] ref`
(by hand, or via `setup_toolchain.py --latest`). That's the *only* place to change it — everything
else derives from that one value automatically, with no second file to keep in sync:

- The matching `pico-sdk`/`picotool` versions (see B.3 above).
- The MicroPython type stubs `scripts/typecheck.sh` uses for `mypy` (see CLAUDE.md's "Code
  quality tooling") — it reads this same `ref` and installs the matching stub release, failing
  with a clear error instead of silently drifting if no matching stub release exists upstream yet.
- The Unix port build (`ports/unix`, used for running tests under the real interpreter later) —
  it's built from the same MicroPython clone `setup_toolchain.py` already checks out at this
  `ref`, not a separately-versioned artifact.

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

**The `src/`-based build (parallel, separate pipeline)**: `scripts/build_firmware.py <device>
[--output PATH]` is a self-contained `uv run` script assembling a real `firmware.uf2` from `src/` +
`ext/microdot.py` + the real website (Part H) for one device — build-only, like the legacy path
above; nothing here flashes or tests real hardware. It needs its own `manifest.py` rather than the
board's default one: the default's `freeze("$(PORT_DIR)/modules")` line freezes
`ports/rp2/modules/_boot.py` under the exact frozen name `shared/runtime/pyexec.c`'s rp2 `main.c`
looks up via `pyexec_frozen_module("_boot.py", ...)` at every boot, but `src/`'s own real entry point
needs a different `_boot.py` — one that mounts the filesystem (identical to the port's own stock
logic) and then imports `wozi_boot` (`boot_entry/wozi_boot.py`) instead of anything from
`ports/rp2/modules`. Freezing a second file under the same name would collide with the default
manifest's own copy, so `build_firmware.py` skips the default manifest entirely and re-states its
other `require()`s verbatim (`bundle-networking`, `aioble`, `asyncio`, `onewire`, `ds18x20`, `dht`,
`neopixel`) alongside its own single `freeze()` of a self-built staging directory (`src/*.py`
flattened + `ext/microdot.py` + the real website frozen as `frozen_html.py`, so
`src/sensortask_wozi.py`'s existing `import frozen_html` resolves with no code change, + the new
`_boot.py` + `boot_entry/wozi_boot.py`). This repo's own top-level `modules/_boot.py` is never read,
copied from, or touched by this script — consistent with CLAUDE.md's hard rule with no exception
needed, since that file is never in this script's path. `build_stage_dir()` raises immediately if
any `src/` filename collides with one of its own reserved staging names (`microdot.py`,
`wozi_boot.py`, `_boot.py`, `frozen_html.py`) rather than silently overwriting one or the other.

`tests_scripts/` (CPython/pytest — see `tests_scripts/conftest.py` and CLAUDE.md's "Code quality
tooling") covers `build_frozen_html.sh`'s recursive merge, `build_website.sh`'s staging, and
`build_firmware.py`'s assembly logic (`_BOOT_PY`/`_MANIFEST_TEMPLATE` content, `build_stage_dir()`'s
file set, CLI error paths) fast and offline. One test in that suite,
`test_real_firmware_build_produces_a_valid_uf2`, does the real end-to-end build, gated behind
`RUN_SLOW_FIRMWARE_BUILD=1` so it stays opt-in for fast local iteration. `scripts/test.sh` runs the
fast `tests_scripts/` suite as one more step alongside the MicroPython one;
`.github/workflows/ci.yml`'s `firmware-build-verify` job (`needs: unit-tests`, reusing its toolchain
cache) sets that env var and runs the real build in CI on every push/PR. `tests_scripts/` is not in
`pyproject.toml`'s `[tool.mypy]`/`[tool.ruff]` scope, matching the existing decision that
`scripts/`/`toolchain/` themselves aren't linted/type-checked either. This closes the "no CI
firmware-build stage" gap for this `src/`-based toolchain specifically — the separate legacy
`build-*.sh` scripts above stay open (see BACKLOG.md).

**Production-readiness scope**: this pipeline proves the build assembles correctly and (via
`tests/test_digital_twin_real_website_integration.py`, Part H.7) that the booted Unix-port digital
twin serves the real website end to end. It does not prove anything about real rp2040 hardware —
nothing produced by this pipeline has been flashed or booted on one.

---

# Part C — Sensor Driver Architecture Specification

Extracted from the three drivers that reached `src/` first (`asy_scd30_driver.py`,
`asy_bmp3xx_driver.py`, `asy_sgp40_driver.py`) plus the shared infrastructure they all build on
(`base_classes.py`, `asy_i2c_driver.py`/`asy_spi_driver.py`, `config_manager.py`, `print_log.py`,
`system_service.py`). This is the shared contract a *new* driver should follow — not a rehash of
Part D's promotion checklist (correctness/exception-safety/typing bar every file must
clear), but the architecture and interface shape the checklist is applied *to*. Read both: this
Part for "what shape does the code take," Part D for "how do I know it's good enough."

Writing a new driver should need only this Part, the sensor's own datasheet, and the design
decisions in C.11 below — everything else here is already decided by precedent.

## C.1 Layered architecture

Three layers, strictly one-directional (each layer only calls the one below it):

```
sensortask-*.py               (per-device integration: wires Readers to REST routes, task supervisor)
        |
*_Reader(SensorReader[Config]) (this Part's layer 3 - asyncio task/config/data-distribution;
        |                       never raises; owns one *_I2C or *_SPI instance)
        |
*_I2C / *_SPI                  (this Part's layer 2 - chip protocol: registers/commands, CRC,
        |                       compensation math; raises on real failure)
        |
I2CDevice / SPIDevice           (project-wide bus wrapper, asy_i2c_driver.py/asy_spi_driver.py -
        |                       not sensor-specific, never touched by a new driver)
        |
machine.I2C / machine.SPI      (MicroPython hardware bus)
```

A new driver adds exactly layers 2 and 3 (one new file, e.g. `asy_<sensor>_driver.py`) plus a
`_Reader` wiring block in the relevant `sensortask-*.py`. Layers below that are shared,
already-promoted infrastructure — don't reimplement bus handling.

## C.2 File & naming conventions

**Identifier casing, project-wide**: `ClassNamingStyle` (CapWords) for classes, `public_function_style`
(`lower_snake_case`) for public functions/methods, `_private_function_style` (a single leading
underscore + `lower_snake_case`) for private/internal functions/methods. A compound class name that
pairs a sensor/device name with a role suffix keeps each half in CapWords, joined by an underscore
rather than run together (`BMP3xx_Reader`, `SCD30_I2C`, `FRAM_SPI`) — still CapWords, just composed
differently from a single-word class like `ConfigManager`. A private class follows the same
underscore-prefix rule as a private function (`_AsyBaseFramChunk`). Double-leading-underscore
(name-mangled) methods are reserved for the rare case where mangling itself is load-bearing
(protecting a name from an actual subclass override) — not an alternate "more private" spelling of
the ordinary single-underscore convention; `src/` has none. Every class project-wide is CapWords,
with one permanent exception: `voc_algorithm.py`'s internals (`DFRobot_vocalgorithmParams`, the
`_vocalgorithm__*` method names) trace their DFRobot/Sensirion source 1:1 per F.4, so its casing is
intentionally not project-style-compliant and never will be.

One file per sensor: `asy_<sensor>_driver.py`. Within it:

- `_NAME = const("<SENSOR>")` — the dict key used everywhere this driver identifies itself:
  `get_dict_data()`/`get_dict_cfg()`/`get_error_counter()`'s returned dict, and every
  `self.pr.err_s(_NAME, ...)`/`wrn_s(_NAME, ...)` call.
- `<SENSOR> = namedtuple("<SENSOR>", (...))` — the measurement result shape, always ending in a
  `TS` (timestamp) field. Field names become the keys `make_dict()` (config_manager.py) exposes
  over the config dict pipeline — see C.6 below.
- **`_NAME`'s string content and the namedtuple's own type-name string must be identical, always**
  — not just similar/related. Confirmed as a deliberate, checkable convention (not a coincidence of
  the three original drivers): `asy_sgp40_driver.py`'s `_NAME = const("SGP40")` pairs with
  `SGP40 = namedtuple("SGP40", ...)`, and `asy_wifi_service.py`/`asy_bmp3xx_driver.py`/
  `asy_scd30_driver.py`/`asy_ntp_client.py` all follow the same pairing — define the two right next
  to each other (as all of those do) specifically so a mismatch is visually obvious at review time.
  A class with no namedtuple at all (no `SensorReader`/`SensorReaderConfig` measurement data - e.g.
  a pure hardware-control class like `asy_neopixel_driver.py`'s `NeopixelDriver`) is exempt from
  this pairing by construction, since there's nothing to match against; `_NAME` there still exists
  purely as the `self.pr.*(_NAME, ...)` logging tag.
- `_VAL_<ABBREV> = const((("<FieldName>", "<type>", default, min, max, special),))` — one schema
  tuple per config field (C.5 below). `<ABBREV>` is a short mnemonic (`_VAL_SI`, `_VAL_POV`, ...),
  concatenated with `+` wherever a full schema is needed (`_VAL_SI + _VAL_POV + ...`).
- `<Sensor>_DeviceSession(Lockable)` — pure boilerplate, identical shape in all three drivers:
  ```python
  class <Sensor>_DeviceSession(Lockable):
      def __init__(self, i2c_device: I2CDevice) -> None:
          super().__init__()
          self.i2c_device = i2c_device
  ```
  Copy this verbatim (swap `I2CDevice`/`SPIDevice` as needed) — don't invent a variant shape.
- `<Sensor>_I2C` (or `_SPI`) — layer 2, protocol class. `<Sensor>_Reader` — layer 3, framework
  class. Constructor parameter order for `*_Reader` (match exactly, even when a sensor doesn't
  need every parameter): bus handle first (`i2c: I2C`), then sensor-specific addressing/pins/
  mandatory callbacks (`address`, `irq_pin`, `asy_comp_callback`, ...), then `trigger_sec: int =
  <n>` (only if the sensor has a configurable trigger rate — SGP40 doesn't, see C.11 point
  6), `max_module_error: int = 5`, then (only if `SensorReaderConfig`, see C.4.3) `cfg_path: str
  = ""`, then the FRAM-related parameter(s) (`fram: AsyFramManager | None = None`, or — if a
  second, paired argument is needed alongside it, as SGP40's `fram_ntp_callback` is for its
  VOC-algorithm-state backup — `fram_storage`/`fram_ntp_callback` kept adjacent to each other in
  that same position), then `history_length: int = 10`, `debug: int | None = None`.

  **`max_module_error` is a generic consecutive-failure-streak threshold, not I2C-specific** —
  `asy_wifi_service.py` and `asy_ntp_client.py` (neither has an I2C bus) rely on the same
  constructor parameter via `_error_check()` (C.7 below). Renamed project-wide from the old,
  misleading `max_i2c_err` (owner-authorized) — every promoted driver/service's constructor and
  every test file that constructs one was updated together in that one pass.

## C.3 Layer 2: `*_I2C`/`*_SPI` protocol class

Owns one `*_DeviceSession`, and any chip-specific cached state (SCD30's last-read
temperature/humidity/CO2; SGP40's `VOCAlgorithm` instance).

**The pre-allocated scratch buffer below is required only for a protocol class doing raw
`write()`/`readinto()`/`writeto()`/`readfrom_into()` I/O itself** (`self._buffer`/
`self._command_buffer`, sized once in `__init__`, reused every call — no per-call allocation,
per Part D.4; `SCD30_I2C`/`SGP40_I2C` are the real examples). A protocol class built entirely on
`I2CDevice.get_register_struct()`/`get_bits()` (`BMP3XX_I2C`) has no scratch buffer of its own at
all, by design — those helpers already allocate internally on every call via `readfrom_mem()`
(`asy_i2c_driver.py`), so there is nothing local left to pre-allocate. Both are conformant; the
buffer requirement scopes to whichever concrete I/O style a protocol class actually uses, not
every protocol class unconditionally. **This carve-out doesn't extend to a class that *does* build
its own raw scratch buffers but still allocates a fresh one on every call anyway** (`FRAM_SPI`'s
`_check_device_id()`/`_read_status()`/`_send_opcode()` each build a fresh one-byte command
bytearray on every call — a real, current instance of this; corrected from an earlier draft of
this bullet that named `_setup_addr_buffer()` as the third offender instead of `_send_opcode()` —
`_setup_addr_buffer()` itself already reuses the pre-allocated `self._addr_buf`, confirmed by
reading `asy_fram_driver.py` directly, not one of the three) — that's a genuine D.4 violation, not
an example of this exemption. Low-severity and deliberately left as-is for now: every real call
site already holds `self._spidev`'s underlying lock (directly, or via the caller-enforced
`self.asy_lock` contract on `get_values()`/`set_values()`), so a future fix reusing one shared
one-byte scratch buffer across these three methods would be safe under today's call pattern, but
isn't itself a correctness/exception-safety issue worth the churn in this pass.

**Contract: raises on any real failure — this is the layer that does *not* return sentinels.**

- A real bus/protocol failure — I2C `OSError` (NAK, timeout, device gone), a CRC mismatch, an
  out-of-range register bit-field, a malformed argument — propagates as an exception
  (`OSError`/`RuntimeError`/`ValueError`, chosen for what actually went wrong). This matches
  Part D.2's raw-bus-call carve-out.
- **This carve-out's actual fault surface is bus-specific — verify against the real bus driver's
  own docstring, don't assume I2C's shape transfers to SPI.** `asy_i2c_driver.py`'s methods raise
  `OSError` on a real transaction fault; `asy_spi_driver.py`'s `write()`/`readinto()` **cannot
  raise at all** on rp2 (no ACK/NAK concept, confirmed against `extmod/machine_spi.c`) —
  `write_readinto()` is the one SPI exception, and it's a caller-input `ValueError` (mismatched
  buffer lengths), not a hardware fault, already caught and turned into `None` inside
  `asy_spi_driver.py` itself. A new SPI-bus sensor driver therefore has a different exception
  surface at this layer than an I2C one — check the concrete bus wrapper before assuming either
  shape.
- `setup()` performs identity verification (chip-ID register read for BMP3xx, CRC-valid
  firmware-version read for SCD30, serial-number + self-test read for SGP40) and raises if the
  sensor doesn't respond as expected — this is deliberate: a misconfigured bus fails loudly once
  at boot rather than producing a driver that silently degrades every later call.
- Every multi-transaction sequence that must not be interleaved by another coroutine (e.g.
  write-command-then-read-reply into a shared buffer) holds the `*_DeviceSession`'s own lock for
  the whole sequence — `async with self.i2c_<sensor> as dev: async with dev.i2c_device as i2c: ...`
  — with the bus-lock `async with` block re-entered (nested a second time inside the same
  device-session acquisition) if the sequence needs more than one separate bus transaction (see
  `SCD30_I2C.read_measurement()`'s three-transaction sequence). A sequence that only needs a single
  continuous bus-lock hold spanning an internal delay — write, `asyncio.sleep()`, then readinto,
  all under the *same* `async with dev.i2c_device as i2c:` block — doesn't need a second nesting at
  all (see `SCD30_I2C._read_dev_register`, which receives an already-open `i2c: I2CDevice` from its
  caller and never re-enters the bus lock itself).
- Compensation/calibration math (BMP3xx's coefficient decode, SGP40's tick conversions) lives
  here, cited against the datasheet section it implements (see Part D.1 and C.11 below).
- Datasheet-documented operating-range checks belong here too, where the raw ADC/compensated
  value is available — reject and raise rather than returning an implausible value silently (see
  BMP3xx's pressure/temperature range check on every `_read()`).

### C.3.1 SPI sensor variant — best effort, non-proven

**Flag on this whole subsection: no SPI *sensor* driver has gone through this project's
promotion process yet.** Everything above (C.1-C.2) is proven against three real I2C
drivers; what follows is extrapolated from `asy_spi_driver.py`'s own contract (verified, but
never exercised by a sensor) and `asy_fram_driver.py`'s `FRAM_SPI` (a real, promoted SPI driver —
but for a memory chip, not a sensor, so its write-enable-latch mechanics below are FRAM/EEPROM-
specific, not a general SPI-sensor pattern). Treat this as a starting point that needs extra
scrutiny — datasheet cross-checks and real-hardware testing both — the first time it's actually
used, not as settled precedent the way C.1-C.2 are.

The general structure follows the I2C case (C.1-C.2): a `Lockable`-based session object wraps an
`SPIDevice` instead of an `I2CDevice`; the protocol class becomes `*_SPI`; the `*_Reader` layer is
unchanged (it only ever calls the protocol class, never the bus directly, so nothing about layer 3
depends on which bus layer 2 uses). **`FRAM_SPI` itself, the one real example, does not actually
split this into two classes** — unlike the I2C drivers' `<Sensor>_DeviceSession(Lockable)` +
`<Sensor>_I2C` pair (C.2), `FRAM_SPI` extends `Lockable` directly and owns `self._spidev =
SPIDevice(...)` itself, with no separate `FRAM_DeviceSession` class anywhere. Both of C.8's lock
layers are still genuinely present (`FRAM_SPI.asy_lock` as the device-session lock, `SPIDevice`'s
own bus lock underneath) — merging the two classes doesn't collapse the two lock layers, it just
means one class holds both roles. A new SPI sensor driver may follow either shape (the two-class
split for consistency with the I2C drivers, or `FRAM_SPI`'s merged single-class form) as long as
both lock layers stay genuinely distinct; don't assume a two-class split is required just because
C.1-C.2 phrase the I2C convention that way. What genuinely differs from the I2C case:

- **No bus-level presence probe exists for SPI, unlike I2C.** `I2CDevice.setup()` has
  `__probe_for_device()` — a zero-byte write that raises `ValueError` on a NAK, catching "wrong
  address / nothing there" before any real protocol traffic. SPI has no addressing and no
  ACK/NAK concept at all (`asy_spi_driver.py`'s own contract: `write()`/`readinto()` cannot raise
  on rp2 hardware once the bus is constructed) — there is no equivalent bus-level check to lean
  on. **Identity verification must be a real, content-checked register read** — the *only* signal
  available — modeled on `FRAM_SPI._check_device_id()`: send the chip's documented ID-read
  opcode, read back the documented number of bytes, and compare against the datasheet's fixed
  ID/manufacturer values before trusting anything else. Skipping this (or doing it as a bare
  "did the read not raise" check, which SPI can't give you anyway) leaves `setup()` with no way
  to detect "wrong/no chip on this CS line" at all.
- **Register/command framing is far more chip-specific than I2C's fairly uniform
  `readfrom_mem`/`writeto_mem` shape**, and this codebase only has one real example (`FRAM_SPI`'s
  opcode-then-address-then-data framing, `_setup_addr_buffer()`). A real SPI sensor may instead
  use a single address byte with a read/write bit (common on accelerometers/gyros: bit 7 of the
  first byte selects read vs. write, the rest is the register address) or another scheme
  entirely — **check the specific datasheet's SPI command format before assuming
  `FRAM_SPI`'s shape transfers**; it's one example of the general "opcode/address framed into a
  small scratch buffer, then a data phase" idea, not a template to copy verbatim.
- **Write-enable-latch mechanics (`_enable_write()`/`_disable_write()`'s WREN/WRDI-and-verify
  pattern) are FRAM/EEPROM-specific, not a general SPI-sensor concern.** Most sensor registers
  (configuration, calibration, oversampling-equivalent settings) are plainly writable without a
  separate enable-latch step — don't build this into a new SPI sensor driver unless its own
  datasheet documents an equivalent latch/protection mechanism.
- Everything else — pre-allocated scratch buffers, the `*_DeviceSession` lock covering a whole
  multi-transaction sequence, datasheet-cited compensation math, operating-range checks — carries
  over from the I2C case unchanged; `SPIDevice`'s own CS-assert/deassert and settle-time handling
  (`asy_spi_driver.py`) is already transparent to the protocol layer, the same way `I2CDevice`'s
  bus session is.
- **`FRAM_SPI._setup_addr_buffer()` trusts its caller-supplied `max_size` without re-deriving it
  from `_check_device_id()`'s own chip-ID read.** `max_size` fixes the address-buffer width (3 vs.
  4 bytes) once in `__init__`, and the class's RDID check is hardwired to one real 8KB chip
  (0x0000-0x1FFF) — a caller passing a `max_size` larger than the chip actually has would let
  addresses validate and silently alias on real hardware rather than being caught. Not a bug (the
  one real construction site passes the correct, matching constant), but a real SPI sensor driver
  reusing this pattern should decide deliberately whether its own address-buffer width should be
  derived from the verified chip ID instead of trusted from the constructor argument.

### C.3.2 UART variant — orphan module, harmonized late, precedent now settled

**`asy_uart_driver.py`'s `UART(Lockable)` is a real, promoted, tested module with zero live callers
anywhere in `src/` today** (see BACKLOG.md). Three real architectural choices
are resolved here as accepted, documented precedent — none were bugs, and none needed a code
change:

- **One merged `UART(Lockable)` class, not a `*_DeviceSession(Lockable)` + `*_I2C`/`*_SPI` pair.**
  C.1/C.2's two-layer split exists to separate "one physical bus, possibly shared by several
  devices" (layer 1, one lock per bus) from "one logical multi-transaction operation on one device"
  (layer 2, a second lock per device-session). UART has no bus-sharing concept at all — one UART
  peripheral is wired to exactly one point-to-point link, so there is only ever one "device" per
  bus instance and the two lock layers collapse onto the same object without losing any real
  distinction. `FRAM_SPI` (C.3.1) already established that a merged single-class shape is legitimate
  when both lock layers are still genuinely present under the hood; `UART`'s single
  `Lockable.asy_lock` plays both roles the same way, and is the accepted shape for any future
  point-to-point (non-multi-device) bus wrapper.
- **CRC framing lives inside the bus-wrapper class itself** (`self.crc: CRC_Base`, applied inside
  `read_until_complete()`/`readinto_until_complete()`/`write()`/`writefrom()`), unlike `I2CDevice`/
  `SPIDevice`, which have zero CRC awareness and leave all framing to the layer-2 protocol class.
  Accepted as UART-specific, not a precedent that blurs C.1's layer-1/layer-2 boundary for I2C/SPI:
  a point-to-point serial link has no register/command addressing scheme of its own the way I2C/SPI
  do, so there is no natural "layer 2" above it to own framing instead — CRC framing is optional
  (`CRC_Pass()` by default) and belongs to *this* layer specifically because there's no other layer
  for it to belong to.
- **`cancel_read_timeout()`** — a real, sensible externally-triggerable cancel for another
  coroutine's in-flight indefinite `ready()` wait. Accepted as a legitimate extension to C.9's
  timer/task/IRQ contract for any bus wrapper that exposes an unbounded (`timeout_ms=-1`) wait: a
  second coroutine holding no lock of its own can still request cancellation of the lock-holder's
  in-flight wait via a plain `asyncio.Event`-based handshake (`self.cancel`/`self.cancelled`), no
  `Timer`/IRQ involved. Not currently needed by any I2C/SPI driver (none of their waits are
  unbounded the way UART's default `timeout_ms=-1` is), but the pattern is now documented precedent
  for one that does.
- **Raise contract, verified against `ports/rp2/machine_uart.c` at the pinned MicroPython v1.28.0
  tag**: a hardware-level framing/parity/overrun error on rp2 is detected at the C level but never
  raised as an exception — a framing/parity error still delivers the (corrupted) byte, an overrun
  silently drops one, a break condition is silently skipped; `write()` can genuinely short-write
  instead of raising. Unlike `asy_i2c_driver.py` (raises `OSError` on a real transaction fault, C.3)
  or `asy_spi_driver.py` (cannot raise on rp2 at all, C.3), `machine.UART` occupies a third, distinct
  position: no raise path exists for a hardware fault, but the failure isn't silently invisible
  either — it's baked into the returned bytes with no separate signal. `asy_uart_driver.py` already
  matches this correctly (every method returns a plain sentinel, never raises); confirming the real
  hardware contract closes the C.3.1 finding that flagged this as unverified, with no code change
  required.

## C.4 Layer 3: `*_Reader(SensorReader | SensorReaderConfig)`

**Contract: never raises.** Every public method returns a well-defined sentinel (`None`/`False`/
an all-`None` namedtuple) on failure — this is the boundary past which nothing from layer 2
propagates uncaught. Every call into the layer-2 protocol object is wrapped in its own
`try/except Exception`, logged via `self.pr.err_s(_NAME, "...", e, errno=N)` (never a bare
`except:` — see CLAUDE.md's bare-except tracked-finding note) before degrading to the sentinel.

### C.4.1 `read_loop()` skeleton (identical shape across all three drivers)

```python
async def read_loop(self) -> bool:
    if not await self._init_<sensor>():
        return False
    while True:
        await self.trigger_event.wait()
        self.pr.evt(_NAME, "sensor trigger")
        results = await self._read_<sensor>()
        if not await self._error_check(results):
            return False
        await self._store_<sensor>(results)
```

Returning `False` from `read_loop()` (init failure or `_error_check` giving up) is the task
supervisor's restart signal (`system_service.py`'s `start_and_check_tasks()` treats a done task
the same whether it returned or raised — but returning cleanly is the contract here, not raising
out of the task).

- **`_init_<sensor>()`**: `await self.pr.setup()` first (required before any logged error/warning
  persists), `self._err_cnt_internal = 0`, then `try: await self.<protocol>.setup() except
  Exception as e: await self.pr.err_s(_NAME, "Error in initial setup:", e, errno=10); return
  False`. If the driver has `SensorReaderConfig`-backed hardware config (oversampling, filter
  coefficient, ...), push the stored config values into the sensor here too, after protocol
  setup succeeds.
- **`_read_<sensor>()`**: `timestamp = time.mktime(time.gmtime())` captured before the read; the
  whole protocol-layer call sequence wrapped in one `try/except Exception`, on failure every
  field (including `timestamp`) reset to `None` together and logged via
  `self.pr.err_s(_NAME, "Lesefehler:", e, errno=N)`. Returns a plain tuple of optionals (a
  driver-local `*Results` type alias under `TYPE_CHECKING`), not the sensor's own namedtuple —
  that conversion happens in `_store_<sensor>()`.
- **`_store_<sensor>()`**: if any field that must be present is `None`, return without storing
  (don't overwrite the last-known-good cached reading with partial data). Otherwise build the
  sensor's namedtuple — computing any derived fields (wet-bulb, dew point, altitude) via
  `math_helpers` here — and call `await self._set_meas_data(...)`.

### C.4.2 Data-access contract (same 3(+1) methods, every driver)

```python
async def get_data(self) -> <Sensor>:                                            # cached last-good reading
async def get_dict_data(self) -> dict[str, dict[str, ...]]:                      # make_dict(await self.get_data())
async def get_dict_cfg(self) -> dict[str, dict[str, ...]]:                       # schema + optional live readback
async def get_error_counter(self) -> dict[str, dict[str, int | list[int] | list[str]]]:  # await self.pr.get_log(_NAME)
```

`get_data()`'s return type can't be narrowed with `typing.cast()` inside the base class (no
runtime presence on MicroPython — see C.10), so every driver's override narrows
`_get_meas_data()`'s generic `NamedTuple` return the same way: an identity return with a scoped
`# type: ignore[return-value]` and a one-line comment explaining why (see any of the three
drivers' `get_data()`). This is the settled convention — don't reach for a local `cast()` shim or
reconstruct the namedtuple field-by-field (`<Sensor>(*data)`) instead: both were tried during the
original three-way promotion (one driver used a runtime no-op `cast()` shim, another rebuilt the
namedtuple from its own unpacked fields on every call) and dropped in favor of this one, since
`# type: ignore[return-value]` needs no extra shim code and — unlike the rebuild — allocates
nothing on a call this hot (every REST read of a sensor's data goes through `get_data()`).
`typing.cast()` still has a real, separate use elsewhere: narrowing a `struct.unpack()`/
`unpack_from()` result (typed `Any` by the installed MicroPython stubs) before a `return`
statement whose declared type isn't `Any` — mypy's `warn_return_any` flags that specific pattern
regardless of this convention; `SCD30_I2C._read_dev_register()` is the current example. Use
`cast()` there if a new driver's protocol layer hits the same stub gap, just not for `get_data()`.

### C.4.3 `SensorReader` vs. `SensorReaderConfig`

This is a real per-sensor decision, not boilerplate — pick based on where the sensor's config
values actually live:

- **`SensorReaderConfig`** (BMP3xx, SGP40): the sensor has values that need a locally-cached,
  file-backed schema (`config_<name>.cfg`) — software-only knobs with no sensor-side counterpart
  (SGP40's `BackupPeriod`), and/or sensor-adjustable settings that reset on power-cycle and must
  be reapplied at every `_init_<sensor>()` (BMP3xx's oversampling/filter coefficient, which the
  chip itself doesn't persist across a soft reset).
- **Plain `SensorReader`** (SCD30): every "config-like" value the sensor exposes is stored in the
  sensor's own NVM and durable across power cycles — nothing to cache locally, so
  `get_dict_cfg()`'s `callback` does all the work (every field is a live I2C readback) and no
  `ConfigManager`/`config_<name>.cfg` exists at all for this sensor. See A.4's SCD30
  `AmbPres` note for why this is deliberate, not a gap.

These two aren't mutually exclusive within one sensor, and mixing them needs no new mechanism:
use `SensorReaderConfig` as soon as *any* field needs local storage, and for the fields that
don't (sensor-NVM-persisted, no local cache needed) simply omit them from the schema and
`ConfigManager` entirely — read/write them straight from the sensor, the same way SCD30 does for
*all* of its fields today, just for a subset instead of the whole set. `get_dict_cfg()`'s
`callback` (C.4.4) already merges schema-backed and live-readback fields into one dict
regardless of how many of each a given driver has, so a driver with, say, 3 schema fields and 2
NVM-only fields looks the same to `get_dict_cfg()`'s caller as one with 8-and-0 (BMP3xx) or 0-and-6
(SCD30) — only the schema tuple passed to `_get_dict_cfg()` and the `callback`'s own field list
change.

**A `SensorReaderConfig` subclass whose own field set isn't fixed at class-definition time needs a
different construction shape than the single-shot `__init__` above.**
`asy_notification_service.py`'s `NotificationCoordinator` is the current example: it deliberately
defers calling `super().__init__()` (and therefore `self.pr`/`self.cfgmgr`/`self.cfg_schema`)
until an explicit `finalize()` call, after zero or more `register()` calls have assembled a
combined config schema at runtime from whatever's registered. This is a legitimate, deliberate
variant of the C.4.3 construction contract for a driver whose schema is composed dynamically,
not a shortcut — everything else in C.4-C.5 (the getter/setter dispatch, `get_cfg_schema()`)
still applies unchanged once `finalize()` has run.

**Every method reachable before `finalize()` has run must guard against it explicitly, not just
`register()`/`finalize()` themselves.** A staged-construction class's `self.pr`/`self.cfgmgr`/
`self.cfg_schema` genuinely don't exist yet in the window between `__init__()` returning and
`finalize()` running — any public method callable in that window needs its own sentinel-based
early-return guard (a private `self._finalized: bool` flag, checked first, matching the class's own
declared never-raises contract — C.4 above), not just the two staging methods. `NotificationCoordinator`
is the current example: `get_data()`, `get_dict_cfg()`, `get_error_counter()`, `reset_error_counter()`,
`monitor_loop()`, `auto_led_override()`, and its own `setup()` override all gained this guard —
found as a real gap (only `register()`/`finalize()` were guarded, every other method would raise a
bare `AttributeError` if called first), not a hypothetical.

### C.4.4 `get_dict_cfg()`'s `callback` parameter

`_get_dict_cfg(name, cfg_vals, callback=None)` (`base_classes.py`) merges the config manager's
stored values with an optional callback's live sensor readback. Only pass `callback=` for fields
that have a real, independent live-sensor source of truth to reconcile against — a field backed
only by the local schema cache needs no callback entry, its stored value is already authoritative.
(BMP3xx passes a callback covering 3 of its 8 fields — oversampling ×2 + filter coefficient, the
only ones the sensor itself reports back; SGP40 passes no callback at all, since all 3 of its
fields are pure software knobs; SCD30 — no `SensorReaderConfig`, see C.4.3 — passes a callback
covering *all* its fields, since none have any other storage.)

**A second, legitimate reason to pass `callback=` for a field with no live-sensor counterpart at
all: sanitizing a sensitive stored value before it's ever returned to a caller.**
`asy_wifi_service.py`'s `get_dict_cfg()` passes `callback=self._mask_pw`, which unconditionally
overwrites the persisted `PW` field with a fixed mask string rather than reconciling against any
live reading — `_get_dict_cfg()`'s merge logic doesn't care what a callback's return value actually
represents, so this reuse works without any new mechanism. A field whose stored value should never
be echoed back verbatim (a credential, a secret) is a second real use case for `callback=`, not
just live-sensor reconciliation.

## C.5 Config schema system (`config_manager.py`)

Each field is a 6-tuple: `(name: str, type: "int"|"float"|"str"|"bool", default, min, max,
special)`. `special` is either a single sentinel value or a **discrete allowed-value set** (a
tuple/list of values), both bypassing the min/max range check via `type_or_range_error`'s
`check_special`:

- **Single-value special** — an "unset"/"disabled" value that's outside the field's normal
  operating range (e.g. SCD30's `AmbPres` field uses `special=0` for "ambient pressure
  compensation not yet set" — see A.4 above). A field with `default=None` and a non-`None`
  single-value `special` is a "special-alone" field: valid but never written to the JSON file —
  used for a field that's entirely sensor-managed with no meaningful local default at all.
- **Discrete allowed-value set** (`special` is a tuple/list) — for a field whose legal values
  aren't a continuous range at all, e.g. BMP3xx's `PressOvers`/`TempOvers` (only `1/2/4/8/16/32`
  are real oversampling multipliers) or a closed string enum. Set `min`/`max` to `None` for a pure
  enumeration (no separate continuous range at all); combine a real range with a small discrete
  set of extra bypass values by passing both. Every element of the set must match the field's own
  declared `type`, checked the same "malformed special rejects every value" way a wrong-typed
  single-value special already does. A schema constant embedded this way (e.g. BMP3xx's
  `_OSR_SETTINGS`) must itself be `micropython.const()`-wrapped if it's referenced inside another
  `const()`-wrapped schema tuple — `const()` only folds references to other `const()`-defined
  names, not plain module-level variables (confirmed directly against the pinned interpreter: a
  plain-tuple reference inside a `const()` expression raises `SyntaxError: not a constant`).

One JSON file per sensor: `config_<name>.cfg` (`SensorReaderConfig.__init__` constructs
`self.cfgmgr = ConfigManager(cfg_path + "config_" + name + ".cfg", default_vals, name)` —
`ConfigManager` builds its own `"CFGMGR_" + name`-identified `PrintLogHistory` internally rather
than reusing its owner's). Both `__init__`s only stash constructor
args (synchronous, cheap) — `SensorReaderConfig.__init__` doesn't call `self.cfgmgr.setup()`
itself, mirroring `ConfigManager.__init__`'s own stash-only shape one level down. The actual file
load/write happens once `SensorReaderConfig`'s own `async def setup()` is awaited (which just
awaits `self.cfgmgr.setup()`, extending the sync-`__init__`/async-`setup()` readiness-gate pattern
up from `ConfigManager` — see C.13 below), cached in `self._cache`, and only
re-synced to disk by `write_config()` — every `get_*` call reads the cache directly, no per-call
file I/O.

`ConfigManager` also carries three defensive type-mismatch catches, spread across three different
methods rather than bunched into one — `setup()`'s `except (MemoryError, OSError, TypeError)`
(a non-string filename), `get_dict()`'s `except (KeyError, TypeError)` (a non-iterable/malformed
`keys` argument), and `write_config()`'s own `except (MemoryError, OSError, ValueError,
AttributeError)` (an `AttributeError` from calling `.items()` on a non-dict `data` argument — the
one of the three that's actually inside `write_config()`; it has no `TypeError` catch of its own).
All three are pure defense-in-depth, confirmed by direct re-investigation once the Microdot REST
layer actually landed (not just anticipated) — `asy_webserver_service.py`'s own `_body_as_dict()`
and `_put_sensors()`'s per-sensor `isinstance(fields, dict)` check already guarantee only
dict-shaped data ever reaches `write_config()`, and `get_dict()`'s `keys` always comes from a
schema (`schema_names()`), never request data, so the REST layer's own validation fully absorbs
the risk before it gets this far. Don't remove them as "unreachable dead code" regardless — they're
still real protection against a future caller that skips that validation, and are already covered
by direct unit tests (`tests/test_config_manager.py`) independent of caller discipline (see
BACKLOG.md).

`ConfigManager` also exposes four typed accessor methods — `get_int_values()`/`get_float_values()`/
`get_str_values()`/`get_bool_values()` — a driver's typed-read half of the config API, returning
already-narrowed values straight from `self._cache` for a given key list without the caller doing
its own `isinstance`/cast dance on `get_dict()`'s wider value type. Real `src/` drivers/services
already call these directly (not just `get_dict()`); a new driver's own field getters should reach
for whichever of these matches a field's declared schema type, the same way. A single-field
convenience wrapper, `name_cfg(schema) -> str`, also exists alongside `schema_names()`/
`schema_dict()` for the common case of pulling one field's own name back out of a one-field schema
tuple.

### C.5.1 `get_cfg_schema()`

`SensorReaderConfig.__init__` captures whatever `default_vals` a subclass passes it as
`self.cfg_schema`, and exposes it through a plain sync `get_cfg_schema()` method — no I/O or
locking involved (unlike `_get_mgr_cfg`/`_get_dict_cfg`), so this is deliberately not `async`.
Every subclass gets this for free from the schema it already passes into `super().__init__()`;
no subclass-local assignment is needed (`asy_bmp3xx_driver.py`/`asy_sgp40_driver.py` never had
one). `self.cfg_schema` itself stays a public attribute too, not just the getter — existing
callers (the legacy REST layer) already reach into it directly. No current `src/` module needs a
local `get_cfg_schema()` reimplementation — every `SensorReaderConfig` subclass gets it from the
base class for free; `asy_neopixel_driver.py`'s `NeopixelDriver` is the one class with no schema
at all (see C.2), so it has no `get_cfg_schema()` either.

### C.5.2 Setter dispatch (`_set_mgr_cfg`/`_set_dict_cfg`, `base_classes.py`)

Config setters are implemented, mirroring the getter pair (C.4.4) one level down:

- **`_set_mgr_cfg(data, cfg_vals) -> (bool, WriteValidity)`** — an overridable extension point
  (only defined on `SensorReaderConfig`, not the plain `SensorReader` base — unlike reads, a
  generic write is fundamentally schema-validation-driven and needs a real `ConfigManager` to
  validate against, so there's no meaningful stub for a class with no schema at all; SCD30 keeps
  its own hand-rolled setters instead of using this path, see A.4 above). The concrete
  implementation delegates to `self.cfgmgr.write_config(data, cfg_vals)`; a subclass with a
  fundamentally different persistence backend (the "hypothetical sensor with onboard nonvolatile
  storage" case) could override this alone and still reuse `_set_dict_cfg`'s orchestration —
  storage location stays fully abstracted away from the caller.
- **`_set_dict_cfg(data, cfg_vals) -> WriteValidity`** — persists first (`_set_mgr_cfg`), then
  pushes live only the fields that both actually changed (`"Valid"`, not `"Unchanged"` — no
  generic force-resend semantics; SCD30's `AmbPres` is the only case that ever needed that, and it
  doesn't use this path) and have a registered push callback. Every field is reported
  independently in the returned dict, including an unrecognized key (matches
  `ConfigManager.write_config()`'s own existing per-key tolerance — one bad key never invalidates
  the rest of a multi-field request). A whole-operation persist failure (invalid `ConfigManager`,
  or an internal write error) marks every requested key `"Failed"`, not `"Invalid"`.
- **`self._push_callbacks`** — a plain `{field_name: async_push_fn}` dict, initialized empty in
  `SensorReaderConfig.__init__` and populated by each subclass's own `__init__`, once, at
  construction time (project decision: no central field→module registry anywhere — each module
  is self-contained/"plugin-style", bringing everything it needs). A field with no entry is
  persist-only (`asy_ntp_client.py`'s config fields, and `asy_sgp40_driver.py`'s
  `BackupPeriod`/`BackupMaxAge`/`WaitTimeNTP`, all fall in this category — those files needed
  **zero** source changes to gain full setter support for those fields, purely from inheriting
  `_set_dict_cfg`). A push callback's signature is always the wide
  `Callable[[int | float | str | bool | None], Coroutine[Any, Any, bool]]` (matching every real
  setter's now-uniform bool return contract — see below); a real setter with a narrower parameter
  type needs a thin type-narrowing wrapper registered instead of the setter itself. **For an
  `int`-typed field specifically**, narrow with `type(value) is not int` — not `isinstance(value,
  int)` — to correctly exclude `bool` (a subclass of `int` in Python) the same way
  `config_manager.py`'s own `type_or_range_error` already does (`asy_bmp3xx_driver.py`'s four push
  callbacks — oversampling ×2, filter coefficient, trigger interval — all follow this). **For a
  `bool`-typed field, this `int`/`bool`-subclass concern doesn't apply at all** — there's no
  further subclass of `bool` to wrongly admit — so `isinstance(value, bool)` and `type(value) is
  not bool` are equivalent, and the two real bool-field wrappers (`asy_wifi_service.py`'s
  `_push_wifi_led`, `asy_sgp40_driver.py`'s `_push_reset_voc`) both use `isinstance`. Match
  whichever of the two a field's own type actually calls for, not `type(value) is not <T>`
  unconditionally.

**Every setter method's return contract is uniformly `bool`** (`True` = applied,
`False` = rejected/failed) — a driver adding a new setter should follow this from the start rather
than returning `None`.

#### C.5.2.1 Command-only trigger fields (replaces legacy's `cmd_keys`)

The legacy `api_helpers.py` pipeline had a separate `cmd_keys` parameter for a field that's
validated and reported alongside real config fields but deliberately never persisted (e.g. SGP40's
`SGPResetVOC`, dispatched to `reset_voc()`). The new schema-driven dispatch has no separate
mechanism for this — it reuses C.5's existing **special-alone field** convention instead
(`default=None` + a non-tuple `special`, the same shape SCD30's `AmbPres` already uses), applied
here to a `"bool"`-typed field for the first time: `_VAL_RESET = (("SGPResetVOC", "bool", None,
None, None, True),)`, with a push callback registered exactly like any other live field. This
needs no new code anywhere — two existing, already-tested behaviors combine to produce exactly the
right semantics for a repeatable trigger:

- `type_or_range_error`'s `"bool"` branch never inspects `special` at all (a longstanding,
  deliberate asymmetry — see `config_manager.py`'s own test coverage), so both `True` and `False`
  are always structurally valid regardless of what `special` is set to.
- `ConfigManager.write_config()`'s `not use_value` branch (a special-alone field is never actually
  stored) always reports `"Valid"`, never `"Unchanged"` — there's no previous stored value to
  compare against, so the push callback re-fires on *every* request, not just the first time the
  value changes. This is exactly the "each request is its own independent trigger" semantic
  `reset_voc()` needs, unlike an ordinary field's "only push on an actual change" default.

**One consequence a driver adding a command-only trigger field must handle explicitly**:
`ConfigManager.get_dict()` (used by `_get_mgr_cfg`/`_get_dict_cfg`) is all-or-nothing across its
requested keys — a special-alone field is never in `self._cache`, so including it in a
`get_dict_cfg()` read would raise `KeyError` internally and fail the *entire* read, not just that
one field (see `config_manager.py`'s own `test_configmanager_special_only_field_not_persisted`).
`get_dict_cfg()` must therefore keep passing its own explicit, narrower field list rather than
`self.get_cfg_schema()` — `asy_sgp40_driver.py`'s `get_dict_cfg()` still passes
`_VAL_BP + _VAL_BMAX + _VAL_WT` only, deliberately excluding `_VAL_RESET`, even though
`get_cfg_schema()` (used for the *setter* side, `_set_dict_cfg(data, reader.get_cfg_schema())`)
includes it.

**A push callback's return value means "push succeeded/failed" to `_set_dict_cfg`** (`False` →
`"Failed"` status plus a `_recover_failed_push()` attempt — C.5.2.2). A setter like
`reset_voc(flag)`, whose own return contract means something else (`False` = "no-op, `flag` was
`False`", not "failed" — see its docstring/tests), must not have its return value forwarded
directly as the push callback's success signal: `_push_reset_voc` reports success unconditionally
once the type check passes. **Any command-only/repeatable-trigger field whose setter has its own
"no-op vs. applied" contract, distinct from "push succeeded/failed", needs the same normalization**
in its push-callback wrapper — `src/asy_scd30_driver.py`'s own `_set_dict_cfg()` ContMeas branch/
SCD30's `stop_continuous_measurement()` is the other live instance (inverted: `True` input is the
no-op there). This exact normalization was dropped when `_scd_apply_field()`'s old
`improved-quality/sensortask-wozi.py` implementation was superseded by `_set_dict_cfg()`'s own
ContMeas dispatch — found and fixed directly in this same pass (a real client's `ContMeas: true`
was reporting `"Failed"` for a pure no-op; see `tests/test_asy_scd30_driver.py`'s
`test_set_dict_cfg_reports_contmeas_true_as_valid_not_failed`), not a hypothetical risk.

#### C.5.2.2 Failed-push recovery chain (replaces legacy's `set_sensor_value` fallback)

Legacy's `set_sensor_value()` guaranteed the config file never ends up holding a value that failed
to actually reach the sensor: on a setter exception it tried, in order, a live `getter()` read-back,
the previous config value, then a hardcoded default, and persisted whichever one it landed on.
`_set_dict_cfg()` reintroduces this as `_recover_failed_push()`, called automatically whenever a
push callback returns/raises failure — adapted to two things that changed since legacy:

- **Persist-first means "the previous config value" no longer exists by the time a push fails** —
  `_set_dict_cfg()` already overwrote it. `_set_dict_cfg()` therefore snapshots every requested
  field's pre-write value (via `_get_mgr_cfg`) *before* persisting, specifically so this fallback
  rung survives the overwrite.
- **There's no caller-supplied `getter`/`default` function argument anymore** — a driver instead
  registers an optional per-field live read-back in `self._get_callbacks` (same
  `{field_name: async_fn}` shape as `self._push_callbacks`, added in `__init__` the same way; a
  field with no entry just skips straight to the next rung), and the "default" is simply pulled
  from the schema's own `def` value via `check_cfg_get_default` — no separate parameter needed since
  the schema already carries a canonical default per field.
- **A getter's return value is validated against its own field's schema before being accepted** —
  a getter reads live, possibly-adversarial hardware state, so a value outside the field's own
  type/range/discrete-set (e.g. a corrupted register read-back) is treated the same as the getter
  raising: fall through to the next rung, rather than attempting (and silently failing) a persist
  through `_set_mgr_cfg` that would leave the recovery attempt doing nothing.

The corrected value is written straight back through `_set_mgr_cfg`, deliberately **not** through
`_push_callbacks` — re-pushing a recovered/default value to the sensor would risk looping on a
persistently-failing field. A command-only/special-alone field (C.5.2.1) is skipped entirely
(`check_cfg_get_default`'s `use_value=False`), mirroring legacy's own `cmd_keys` exclusion from this
exact fallback — there's nothing to persist-correct for a field that's never in `ConfigManager`'s
`_cache`. The field's caller-visible status in `_set_dict_cfg()`'s returned dict stays `"Failed"`
regardless of whether the correction itself succeeds, matching legacy exactly: the client is told
the truth about their request; the persisted-value repair happens silently underneath. See
`tests/test_base_classes.py` for coverage of every rung (getter wins over the snapshot, a raising
getter falls through to it, a first-ever request falls through to the schema default, the
special-alone exclusion, and both the snapshot-read and correction-write failure paths).

### C.5.3 Response envelope (`api_response.py`)

Replaces the old, now-deleted `improved-quality/api_helpers.py`'s ad hoc `cmd_post_check`/
`special_err`/`generic_error_return` pipeline. Same wire shape as before
(`{"res": "OK"|"ERR", "code": int, "descr": str, "result": ...}`):

- `make_response(code, descr=None, result=None)` — a small standard code catalog (`0`–`5`, `100`)
  with per-call text override, plus support for an entirely custom `(code, descr)` pair outside
  the catalog — generalizes the legacy `special_err` closed `Literal` enum into an open set.
- `parse_cmd_request(request, keys)` — request-body parsing + `"cmd"` validation, mirroring
  `cmd_pre_check()`. Decoupled from `microdot.Request`'s concrete type via a local `Protocol`
  (mirrors `print_log.py`'s own `_FramManager`/`_FramChunk` Protocols) rather than importing
  `ext/microdot.py`, which isn't on this project's mypy search path.
- `handle_set_cmd(reader, data, cfg_vals, post_fct=None, post_asy_fct=None, ok_descr=None)` —
  orchestrates `_set_dict_cfg()` plus one optional post-write hook (fires at most once per call,
  only if at least one field actually changed — one hook per endpoint, not one per field, matching
  the legacy pipeline's own `post_fct`/`post_asy_fct` semantics), wrapped in its own try/except as
  defense-in-depth on top of Microdot's blanket per-request catch (project decision, based on
  prior field experience with Microdot behaving unexpectedly) — `reader._set_dict_cfg()` already
  catches its own internal failure modes, so what actually reaches this outer catch is almost
  always a caller-supplied `post_fct`/`post_asy_fct` raising. Build `data` from only the keys the
  client actually sent — an omitted key is never validated/persisted/pushed (`_set_dict_cfg` only
  iterates `data.items()`); this is the full replacement for the legacy pipeline's `""`-string-
  means-unchanged convention, not a gap.
- A per-field validation failure (including an unrecognized key) never demotes the overall
  response below `"OK"`/code `0` — the request was validly processed and dispatched; per-field
  detail lives entirely in `"result"`. See `tests/test_setter_microdot_integration.py` for a real
  `ext/microdot.py` (v2.6.2) end-to-end proof of this whole pipeline, dispatched through
  Microdot's own real `dispatch_request()`.

Every REST endpoint handler in `src/asy_webserver_service.py` now calls these directly (the old
`improved-quality/sensortask-wozi.py` was first migrated onto this same pipeline, under a scoped,
project-owner-authorized exception to CLAUDE.md's hard rule on editing `improved-quality/` source,
before being superseded outright and deleted once `asy_webserver_service.py` replaced it - see
CLAUDE.md's "Hard rules"). `setSGP`/`setBMP` route directly through `sgp_reader.get_cfg_schema()`/
`bmp_reader.get_cfg_schema()` now, not a separate `config_SYSTEM.cfg` — the legacy handlers wrote
into that parallel file, which neither driver's own logic ever read, so a REST client setting these
fields never actually reached the sensor; routing through the real schema fixed that disconnect.
Two wire-format conventions apply project-wide as a result: a field's wire name drops any redundant
per-driver prefix (`"BackupPeriod"`, not `"SGPBackupPeriod"` — the endpoint itself already scopes
the field set), and every bool-typed field is native JSON `true`/`false`, replacing the legacy
`"switch"` `"On"`/`"Off"` string dtype everywhere it had a live route. The HTML/JS frontend has not
been updated to match either change yet (see BACKLOG.md).

**A module whose single schema is split across more than one REST route must narrow
`get_cfg_schema()`'s tuple per route, not hand each route the whole schema**: `AsyConnTime` owns
one schema/`cfgmgr` for all of `SSID`/`PW`/`Country`/`Hostname`/`LedWifiOn`, but `/net/cmd`'s
`setNetwork` and `/led/cmd`'s `setWiFiLED` each only own their own subset (matching the legacy
handler's own per-route scoping) — passing the full schema to `handle_set_cmd()` from both routes
would let `setNetwork` accept/persist `LedWifiOn` (spuriously firing `reconnect_wifi()` for an
LED-only change) and let `setWiFiLED` silently accept/persist `SSID`/`PW`/`Country`/`Hostname` with
no reconnect at all. `sensortask-wozi.py`'s `_cfg_subset(schema, keys)` narrows the tuple to a
named subset before passing it to `handle_set_cmd()`; any future module in this shape needs the
same per-route narrowing.

## C.6 Data model (`config_manager.py`'s `make_dict()`)

`make_dict(nt: NamedTuple) -> dict[str, dict[str, ...]]` turns a sensor's namedtuple into
`{<TypeName>: {field: value, ...}}` via `repr()`-parsing — **not** `_fields`/`_asdict()`, because
MicroPython's `collections.namedtuple` implementation doesn't provide either. Don't assume
CPython namedtuple introspection is available; this is why `make_dict()` exists at all instead of
every driver writing its own `_asdict()`-based dict conversion.

**Known landmine, dormant today**: because the parsing splits on `"("`/`","` in the namedtuple's
own `repr()`, a field whose *value* itself contains one of those characters corrupts the result —
a nested-tuple-valued field silently truncates every subsequent field out of the returned dict,
and a list-valued field (comma inside `[...]`) produces a garbage key that collapses the whole
dict to all-`None` via the function's own outer `except Exception`. Every current config
namedtuple (`SGP40`/`BMP3XX`/`NTP`/`SCD30`/`WIFI`) is flat scalar fields only, so this doesn't
fire today — but check this function first if a new driver adds a list/nested-tuple-valued field
and its config read-back comes back silently wrong/empty.

## C.7 Error handling & logging contract (`print_log.py`, `base_classes.py`)

- `self.pr` is a `PrintLogHistory` (in-memory, bounded `deque`) or `PrintLogHistoryStore`
  (FRAM-backed, survives reboot) depending on whether the `Reader`'s `fram` constructor argument
  was given — chosen automatically inside `SensorReader.__init__`, transparent to everything
  above it. A new driver never picks between the two itself. `SensorReader.__init__` also takes
  `name: str = ""` (baked into the constructed logger's own identity, per print_log.py's
  name-baking change) and `logger: PrintLogHistory | None = None` — passing an existing logger
  reuses it instead of constructing a fresh one, the reach-through mechanism for a directly-bound
  sibling object that should share one identity/history instead of getting its own.
- **The same fram-vs-memory selection logic is also available standalone**, as `print_log.py`'s
  module-level `make_logger(fram, history_length, debug, name) -> PrintLogHistory` — the exact
  branch `SensorReader.__init__` runs internally, extracted so a non-`SensorReader` class needing
  the identical choice (`system_service.py`'s `SystemService`, which owns its own error history but
  isn't a sensor driver and has nothing to inherit the branch from) doesn't hand-duplicate it. Any
  future class in the same position — owns a `PrintLogHistory(Store)`, takes a `fram=` constructor
  argument, but doesn't subclass `SensorReader` — should call `make_logger()` rather than
  reimplementing the `if fram is None: ... else: ...` branch a third time.
- Log-level methods, two tiers: `pr.one`/`pr.evt`/`pr.all` (sync, unconditional print gated on
  level, no history entry) for informational/trace messages; `pr.err_s`/`pr.wrn_s` (async, `await`
  required — they persist to `self.history`/FRAM) for anything that should count against
  `get_error_counter()`'s reported `ErrCount`/`ErrNum`/`ErrType`. **A third pair, `pr.err`/`pr.wrn`,
  is the sync, non-persisting counterpart of `err_s`/`wrn_s`** — same print-only/level-gated/
  no-history shape as `pr.one`/`pr.evt`/`pr.all`, just named for the error/warn levels instead —
  used project-wide (every current driver/service) for two real, recurring situations: (1) a
  genuinely sync call site that can't `await` (e.g. a `Timer.init()` failure handler inside
  `start_timer()`, which isn't itself `async`), and (2) a routine, expected state observation that
  shouldn't count toward `get_error_counter()`'s history at all — `asy_wifi_service.py`'s own
  module docstring states this second distinction explicitly: "'Attempt' operations persist a real
  errno via `self.pr.err_s()`...; routine state observations degrade silently via `self.pr.err()`
  instead." Choose `err`/`wrn` over `err_s`/`wrn_s` for either reason, not just when `async` isn't
  available.
- `errno=`/`wrnno=` are small positive integers, defined and reported **per driver** — each
  driver owns and reports its own error list on top of a small, already-reserved shared base. Within
  that per-driver list, group sequentially by the method that raises it (BMP3xx: 10=init, 11-14=
  config read/write, 15-20=oversampling/filter forwards, 21=trigger-interval) — a representative
  pattern worth following, not a fixed convention to match number-for-number.
- **`base_classes.py` itself already reserves `errno=1`-`9`/`wrnno=1`-`2`, inherited unmodified by
  every `SensorReader`/`SensorReaderConfig` subclass** — `_error_check()` (`errno=1`/`2`),
  `_get_dict_cfg()` (`wrnno=1`/`2`, `errno=3`/`4`), and `_set_dict_cfg()`/`_recover_failed_push()`
  (`errno=5`-`9`). Every driver-owned `errno`/`wrnno` list therefore isn't independent of the
  others the way "per driver, no project-wide numbering" alone would suggest — it's scoped
  starting from whatever the shared base class has already claimed, since a driver's own numbers
  land in the *same* `self.pr.history`/`get_error_counter()` stream the base class's calls already
  populate. **This is also the real reason `errno=10` for "initial setup failed" isn't purely
  coincidental convergence**: it's the first number free after the base class's own reserved 1-9,
  not just three drivers independently picking the same number for unrelated reasons. A new
  driver's own numbering should start at 10 (or higher) for exactly this reason — starting lower
  would collide with a base-class entry already using that number for something unrelated
  (e.g. a driver-chosen `errno=3` would be indistinguishable in `get_error_counter()`'s history
  from a `_get_dict_cfg()` internal failure).
- **Common error classes (decided scheme, closing BACKLOG.md's former "common driver error
  classes" entry)**: `base_classes.py`'s 1-9 reservation above already means the same condition
  across every driver *by construction* (shared code, inherited unmodified) — the owner's
  direction was to extend that same "same number, same meaning" property one step further into
  the driver-owned 10+ range, without collapsing per-driver numbering into one shared enum. Three
  fixed common slots, immediately after the base range, each driver uses if and only if it
  actually has that failure mode:
  - **`errno=10` = initial setup/init failed.** Already universal (see above) - formalized, not
    changed.
  - **`errno=11` = the driver's own primary/periodic read (measurement) failed** - what
    `read_loop()` reports each cycle. Found genuinely inconsistent before this scheme (SCD30 was
    already at 11 by chance; BMP3XX was at 13, SGP40 at 17) - all three now use 11.
  - **`errno=12` = a persisted-config read at init failed** (reading stored config values needed
    to push into the sensor during `_init_*()`, distinct from a *later*, per-cycle config read like
    SGP40's own backup-schedule lookup, which stays driver-specific). BMP3XX and SGP40 both have
    this failure mode (moved from their old 11); SCD30 doesn't (`SCD30_Reader` has no local
    `cfgmgr` at all - its params live purely on-sensor NVM, see its own module docstring) - `12` is
    simply unused by SCD30, not repurposed.
  Each driver's own remaining, driver-specific errors are renumbered to start immediately after
  the highest common slot it actually uses (13+ for BMP3XX/SGP40, 13+ for SCD30 since it skips
  unused `12`), preserving each driver's own original relative ordering among its own conditions -
  see the per-driver table rows below for the resulting exact numbers. Room to extend to a fourth+
  common slot (up to the existing 1-20ish range before needing to renumber everything again) is
  open if another genuinely-shared category turns up later; none was added beyond these three in
  this pass.
- **A driver/service whose error sources aren't a fixed, enumerable-ahead-of-time list can assign
  `wrnno`/`errno` dynamically instead of from a fixed per-number catalog** — `system_service.py`
  assigns a task-supervisor warning's `wrnno` from that task's own position in a dynamically
  registered task list (`wrnno=n + 1`), since there's no fixed roster of tasks to enumerate in
  advance the way a single sensor's own fixed method list allows. This is an accepted variant of
  the "small positive integers, defined and reported per driver" rule above for a genuinely
  dynamic/enumerable error source, not a departure from it — the numbers still mean something
  stable *within one run*, just not a fixed number-to-meaning mapping across runs the way a static
  per-driver catalog gives you.
- `_error_check(results, condition=True) -> bool` (`base_classes.py`) is the shared
  consecutive-failure-streak counter every `read_loop()` calls once per cycle with that cycle's
  results tuple — `name` is no longer a parameter (`self.pr` already carries it, per print_log.py's
  name-baking change); every current call site was confirmed to always pass exactly its own
  `_NAME` before the parameter was dropped. Returns `False` (give up, triggers task-supervisor
  restart) once
  `self._err_cnt_internal` exceeds `max_module_error`; decrements the streak back down on a good read.
  `condition` lets a driver suppress counting a "failure" that isn't really the sensor's fault
  (SGP40 passes `condition=compensated` — a `None` result from a missing compensation callback
  isn't a sensor failure).
- **A call site with no real per-field measurement tuple — just one plain pass/fail flag (e.g.
  `asy_wifi_service.py`'s `hw_op_failed`, `asy_notification_service.py`'s `cfg_read_failed`) —
  passes a fixed one-element sentinel and drives the flag through `condition=`**:
  `_error_check((None,), condition=<failed flag>)`, not a ternary that swaps the whole tuple
  (`(None,) if flag else (1,)`). Both are behaviorally identical (`condition=` gates whether the
  fixed `None` is allowed to count), but `condition=` reads directly as "check this failure under
  this condition" instead of asking the reader to notice that `(1,)`'s `1` is an arbitrary
  non-`None` placeholder with no meaning of its own — established as the house style during the
  `src/` harmonization pass.
- A per-field get/set forward (C.4.4-adjacent — `get_pressure_oversampling()`-style thin
  wrappers around the protocol layer) **always logs via `self.pr.err_s()`/`wrn_s()` on failure**,
  not just a bare `try/except Exception: return None`/`False` — a transient bus fault on a
  REST-triggered config get/set must stay visible in the sensor's own error history, the same way
  a `read_loop()` failure already is. (BMP3xx established this pattern first; SCD30's forwards
  originally didn't follow it and were brought in line with it — see any of SCD30's forwards for
  the now-shared shape.)
- **An owned helper with no registered `get_task_starters()`/`get_timer_starters()` entry of its
  own may still own an independent, uniquely-named `PrintLogHistory` instead of sharing its
  owner's `self.pr`** — the rule for `captive_dns.py`'s `DNSServer` (owned/lifecycle-managed by
  `AsyConnTime`, not itself a registered `Reader`):
  it gets its own `"DNSSRV"`-named `PrintLogHistory` rather than reusing `AsyConnTime`'s. The
  rationale is one level up from C.7 itself — at the `sensortask`/wiring level, multiple owned
  helpers' independent histories are expected to be folded into one combined REST-facing endpoint
  (e.g. a "networking" endpoint aggregating `AsyConnTime`/`asy_dns_client`/`DNSServer`) rather
  than merged at the `self.pr` level, so C.7 doesn't need to pick a single shared-vs-independent
  rule — both are valid, and which one a given owned helper uses is a wiring-layer decision, not a
  per-class one. This aggregation has since landed: see A.8 above for `/status`'s `errcount`
  sub-structure, which folds every registered module's (and every `ConfigManager`'s) own logger
  into one response.
- **Silent-failure-masking convention: a teardown/cleanup method on a class with no logger of its
  own must return `bool` (success/failure), not `None`, so its caller — which does have a
  logger — can observe and log the failure instead of a bare `except Exception: pass` silently
  swallowing it.** This is a generalizable, checkable rule: any class documented (in its module
  docstring, or the comment immediately below it if the header itself was trimmed — see CLAUDE.md's
  docstring-length rule) as a plain sentinel-return, never-raises primitive (no `self.pr` of its own) and
  that owns a teardown/cleanup helper should follow this shape. Three real instances in `src/`
  today: `asy_udp_socket.py`'s `AsyUDPSocket.disconnect()` (its one real production caller,
  `captive_dns.py`'s `DNSServer.run()`, logs a `wrn_s()` on a `False` return — a repeated, silent
  failure here across many short-lived DNS/NTP UDP sockets over a long uptime could otherwise
  exhaust the platform's genuinely finite socket/poll-slot budget with zero log trail pointing back
  to the cause); `asy_webserver_service.py`'s `WebserverService._close_writer()` (logs via
  `self.pr.wrn_s()` on the caller's own side, since this one *does* have a logger — matching this
  file's established connection-lifecycle logging convention); and `asy_uart_driver.py`'s
  `UART.deinit()` (returns `bool` for consistency, ready for whoever wires this orphan module in —
  see C.3.2). Check any new teardown/cleanup helper that currently returns `None` unconditionally
  against this rule before adding it — the failure signal is cheap (a `bool`) and the alternative is
  a class of bug that never shows up until the resource it's supposed to free is already exhausted.

### C.7.1 Running `errno`/`wrnno` table (error-code convention, pass 2)

Real numbers, per module, as actually assigned in the promoted code — not a global registry (each
module's own `self.pr`/history stream is independent, so numeric overlap *between* rows is expected
and harmless; only overlap *within* one row's own range would be a real bug). Kept here permanently
so a new module's numbering has a real precedent list to extend, per the "Error-code convention"
pass-1/pass-2 process this table is pass 2's own output.

| Module (`self.pr`'s name) | `errno` range | `wrnno` range | Notes |
|---|---|---|---|
| `base_classes.py` (inherited by every `SensorReader`/`SensorReaderConfig` subclass) | 1-9 | 1-2 | Reserved base range — see the bullet above; every driver's own numbering starts at 10+ to avoid colliding with this. |
| `config_manager.py` (`"CFGMGR_" + name`, per instance) | 1-14 | 1-6 | Sequential in source order (`setup()`'s load/validate/first-write paths, then the three already-async accessor methods). |
| `asy_fram_manager.py`/`asy_fram_driver.py` (shared `"FRAM"` logger — `AsyFramManager`, its chunk classes, and `FRAM_SPI` all share one stream) | 10-97 | 60-83 | `AsyFramManager`: 10-88, non-sequential — the shared `_handle_status_bytes()`/`_set_check_sb()` busy/idle-status-byte helper spreads its caller-supplied base `err` across 2 values when `check_idle=False` (`err`/`err+1`, one per status byte) or up to 7 when `check_idle=True` (`err` through `err+6`, covering both bytes' read-fail/mismatch/write-fail outcomes plus the two-bytes-disagree case) - confirmed directly from `_set_check_sb()`'s own branches, not just the inline comments at each call site. `_write_chunk()`=10-11 (busy-check, `check_idle=False`)/17 (CRC)/18 (write failed)/19-20 (idle-check, `check_idle=False`)/26 (exception), `_read_chunk()`=30-36 (busy-check, `check_idle=True`)/37 (read error)/38 (incremental CRC)/39-40 (idle-check, `check_idle=False`)/46 (final CRC)/47 (exception)/48 (zero-length buffer), `_clear_chunk()`=50-51 (busy-check, `check_idle=False`)/57 (write failed)/58 (exception), the block-pair `_write()`/`_read()`/`clear()` helpers reuse 60-64/70-73/80 for both their own `errno` and matching `wrnno` (pause/invalid-block-data warnings), the remaining higher-level methods (`write()`, timestamp write/sync/`setup()`)=81-88. `FRAM_SPI`: 89-97, continuing sequentially (not-initialized ×5, invalid-range ×2, readback mismatch, lock-timeout) + `wrnno`=81-83 (WRDI-stuck, WEL-didn't-set ×2). |
| `asy_bmp3xx_driver.py` (`"BMP3XX"`) | 10-22 | — | 10=init (common slot), 11=periodic read failed (common slot), 12=config data read failed at init (common slot), 13=config data write failed at init, 14=config data read failed at store-time (`_store_bmp()`), 15-20=oversampling/filter forwards, 21=trigger-interval, 22=batched oversampling/filter-coefficient snapshot read (`_read_sensor_dict()`). See the common-error-class bullet above the table. |
| `asy_scd30_driver.py` (`"SCD30"`) | 10-25 | — | 10=init (common slot), 11=periodic read failed (common slot; already matched the common slot before it existed), 12=reserved/unused (SCD30 has no init-time persisted-config-read step - see the common-error-class bullet above), 13=stop-continuous-measurement, 14-25=per-field get/set forwards in pairs. |
| `asy_sgp40_driver.py` (`"SGP40"`) | 10-18 | 10-14 | 10=init (common slot), 11=periodic read failed (common slot), 12=config data read failed at init (common slot), 13-18=per-cycle backup-config-read/write/clear-FRAM/deserialize/serialize/compensation-callback. `wrnno`=backup-missing/stale conditions. |
| `asy_wifi_service.py` (`"WIFI"`, `AsyConnTime`) | 11-18 | 1-7 | 11=mode-switch, 12=hotspot-activate, 13=STA-connect-attempt, 14=STA-poll, 15-16=STA-disconnect/deactivate, 17=hardware-failure-streak give-up (mirrors NTP's own give-up errno below), 18=disconnect-timeout; `wrnno` 1-3=missing-config per connection phase, 4-7=WLAN status conditions. |
| `asy_ntp_client.py` (`"NTP"`) | 11-20 | 1-3 | 11=missing-config, ..., 19=time-calc, 18/20=missing-config-interval-fallback/give-up; `wrnno`=callback failures. |
| `captive_dns.py` (`"DNSSRV"`, `DNSServer`) | 1-3 | 1-3 | 1=invalid server_ip/netmask at startup, 2=unexpected loop exception, 3=disconnect-cleanup exception; `wrnno` 1=dropped `sendto()` reply, 2=invalid recvfrom data/address, 3=socket teardown (`disconnect()`) didn't complete cleanly (added alongside Part C.7's silent-failure-masking convention fix - previously missing from this table). |
| `system_service.py` (`"SYSTEM"`) | 1-4 | dynamic (`n + 1`) | 4=task-error-budget-exceeded-rebooting; `wrnno` assigned per task-supervisor index — see the "dynamic assignment" bullet above, not a fixed catalog. |
| `asy_notification_service.py` (`"NOTIFY"`) | 10-13 | 1-5 | 10=value-callback failure, 11=threshold-config-read failure, 12=`local_time_callback` failure, 13=`request_signal_cb` callback failure. Renumbered off an original 1-4 (Step 7 audit finding): `_error_check()` is actively called from `monitor_loop()`, so a 1-4 errno range genuinely collided with base_classes.py's own reserved, actively-used errno=1/2 in this module's history stream - unlike wrnno (still 1-5), whose collision with base's wrnno=1-2 stays dormant here the same way it already does for `asy_wifi_service.py`/`asy_ntp_client.py` (see the bullet above). |
| `api_response.py`'s `handle_set_cmd()` (logs onto whichever caller-supplied `SensorReaderConfig`'s own `self.pr` it's given, not a logger of its own) | 99 | — | One defense-in-depth catch (a caller-supplied `post_fct`/`post_asy_fct` raising - see Part C.5.3), fixed at 99 specifically because this can run against *any* registered module's own `.pr` (`AsyConnTime`, `AsyNtpClient`, `NotificationCoordinator`, ...) - a small number picked for one of them would still collide with another's own range or with base's reserved 1-9. |
| `asy_webserver_service.py` (`"WEBSERVER"`) | 1-5 | 1-5 | Not a `SensorReader`/`SensorReaderConfig` subclass (own bare `PrintLogHistory` via `make_logger()`, like `captive_dns.py`/`system_service.py`), so it starts at 1 like those, not 10+. 1=unexpected exception escaping `_serve()`'s per-connection dispatch, 2=`system_cmd` callback failure, 3=`notification_led` callback failure (found missing entirely - Step 7 second-pass audit finding: both callback dispatches were unguarded, letting a raising caller-supplied `system_cmd`/`notification_led` escape the route handler instead of degrading to a `"Failed"` result with a persisted errno like every comparable callback call site elsewhere in this codebase), 4=an otherwise-unlogged exception caught by the `app.errorhandler(Exception)` catch-all (Step 8 audit finding - see BACKLOG.md's former "No `@app.errorhandler` registrations exist anywhere yet" item, now closed), 5=`notification_pause` callback failure (the `PauseTime` dispatch - restored the legacy `pauseAutoLED` override-countdown command, dropped entirely during the wire-format redesign until this fix); `wrnno` 1=peer closed early, 2=per-call or outer-cap timeout reclaim, 3=socket error reclaim, 4=writer close failed, 5=`wait_closed()` failed. Previously missing from this table entirely despite live usage - added alongside the errno=2/3 fix above. |
| `asy_neopixel_driver.py` (`"NEOPIXEL"`) | — | — | No persisted logging today — only informational `evt()` calls, nothing that fails in a way worth counting against `get_error_counter()`. |
| `asy_i2c_driver.py`/`asy_spi_driver.py`, `asy_udp_socket.py`, `asy_dns_client.py` (client side) | — | — | Deliberately no logging (reverted) — every real failure already surfaces to and gets logged by exactly one upstream owner; see the standing "Bus layer"/"`asy_udp_socket.py`/`asy_dns_client.py`" conventions above. **Coverage audit (closed, no gaps found)**: every I2C-bus-touching call site in `asy_scd30_driver.py`/`asy_sgp40_driver.py`/`asy_bmp3xx_driver.py` is reachable only from a higher-level method wrapped in `try`/`except Exception` that logs via `self.pr.err_s()` with its own `errno` (confirmed by matching every driver's actual `errno`/`wrnno` call sites 1:1 against this table's own per-driver row - the BMP3XX `errno=22` fix above is what that cross-check found). SGP40's one bare `except OSError: pass` (the general-call reset broadcast) is a documented, deliberately-suppressed *expected* NAK, not a swallowed real error. FRAM's SPI path has no exception-based bus errors to catch in the first place - real RP2040 SPI transfers can't NAK, so `FRAM_SPI` already detects failures via its own status-byte checks (rows above), a different and already-complete mechanism. No dedicated bus-layer REST endpoint/logger is needed on top of this - see BACKLOG.md's former "Bus-layer status has no dedicated REST endpoint" entry, closed by this audit. |
| `asy_uart_driver.py` | — | — | Orphan module, zero live callers — no `self.pr` at all (C.3.2); would follow this same table's shape once wired in and given an owner. |

See the "reserved base range" bullet above for why `errno=10` means "init failed" almost everywhere
a driver reaches that number — a new module should follow the same reasoning, not treat this table
as a lookup requiring a specific unused global number.

## C.8 Concurrency & locking model

Two independent lock layers, both needed:

1. **Bus lock** (`I2C.async_lock`/`SPI.async_lock`, one per physical bus instance) — held by
   every `I2CDevice`/`SPIDevice` on that bus (they share the *same* lock object, passed in via
   `Lockable.__init__(asy_lock=...)`), serializing *any* single transaction against every other
   device sharing the bus.
2. **Device-session lock** (`*_DeviceSession(Lockable)`, its own independent
   `asyncio.Lock()`) — serializes a *multi-transaction sequence* belonging to one logical
   operation (e.g. SCD30's write-then-sleep-then-read for one register) against a *different*
   coroutine trying to start its own sequence on the same sensor mid-way through — without this,
   two coroutines could interleave and corrupt the shared per-sensor scratch buffer even though
   each individual bus transaction is itself already serialized by lock 1.

Pattern: `async with self.i2c_<sensor> as dev:` (acquires lock 2) wrapping one or more
`async with dev.i2c_device as i2c:` blocks (acquires lock 1 for just that one transaction) —
see any `*_I2C` class's multi-step methods for the concrete nesting. **Lock ordering is fixed and
must stay that way**: every call site acquires the device-session lock (2) before the bus lock (1),
never the reverse — audited across every `*_DeviceSession(Lockable)` driver in `src/`
(SCD30/BMP3xx/SGP40/I2CDevice, plus FRAM's structurally identical `_op_lock`) with no violation
found: no method re-acquires an already-held lock, `Lockable.__aexit__` always releases
(try/except around `.release()`, never suppresses the original exception), and every extended hold
is a bounded, protocol-justified delay. A new driver that acquires these two locks in the opposite
order risks a real deadlock against a concurrent caller of an existing driver.

**Known inconsistency (`asy_wifi_service.py`), worth checking before adding a similar getter
anywhere**: its getters hide two opposite locking contracts under one shape —
`network_available()` requires the *caller* to already hold `wifi_mode_lock` (documented inline),
while `get_wlan_ifconfig()`/`get_dns_server_ip()`/`get_wlan_rssi()`/`wlan_isconnected()` assume
the caller does *not* hold it (each checks `.locked()` defensively instead). This exact mismatch
already caused one real, since-fixed bug (`get_dns_server_ip()` always returning `None`) — the
underlying inconsistency itself is intentionally left as-is (not urgent enough to redesign), but a
new getter following this file's pattern should pick one contract deliberately, not copy whichever
neighboring method happens to be closest. Separately, `asy_wifi_service.py`'s 60s STA-retry branch
holds `wifi_mode_lock` for up to a minute, and `asy_ntp_client.py`'s sync task waits on that same
shared lock — a known, accepted priority-inversion-shaped cost (NTP sync can be delayed up to a
minute during active WLAN instability), not a correctness bug.

## C.9 Timer/task/IRQ integration contract

- Every `Reader`/service class exposes both:
  ```python
  def get_task_starters(self) -> list[Callable[[], asyncio.Task[Any]]]: ...
  def get_timer_starters(self) -> list[Callable[[], None]]: ...
  ```
  even if trivially one-element lists — `system_service.py`'s `start_and_check_tasks()`/
  `start_timers()` discover and supervise every driver generically through these, never by name.
  **This is the boot-time-lifecycle discovery mechanism, not the only legitimate way a
  `Reader`/service may ever start a task.** A task whose lifecycle is tied to a runtime mode
  transition rather than to boot itself — `asy_wifi_service.py`'s hotspot-mode DNS server task,
  started with a raw `evtloop.create_task(...)` when hotspot mode is entered and cancelled/
  recreated as `_conn_phase` changes — is deliberately outside `get_task_starters()`'s generic
  supervision, because its lifecycle is owned and driven by the module itself, not by
  `system_service.py`'s boot sequence. This is a legitimate opt-out for a genuinely mode-scoped
  task, not a gap in the discovery mechanism — a task with a real boot-time lifecycle still belongs
  in `get_task_starters()`.
- Triggering a periodic read uses `machine.Timer` (default **soft**, no `hard=True` anywhere in
  this codebase) whose callback only ever calls `.set()` on an `asyncio.ThreadSafeFlag` — never
  `time.sleep()`, never business logic, inside a Timer callback. The read loop's own
  `while True: await self.trigger_event.wait(); ...` is what actually does the work, woken by the
  flag. This is the only safe way to wake a waiting coroutine from a callback context that isn't
  itself running inside the event loop.
- **Use `Timer.PERIODIC`, not `Timer.ONE_SHOT`, for anything that must keep firing** — see
  F.1's soft-Timer-callback-drop gotcha: a soft callback can be silently dropped if
  MicroPython's fixed-depth scheduler queue is full, with no exception anywhere in that chain. A
  periodic timer self-heals on its next tick; a one-shot timer that gets dropped never fires
  again. SCD30's IRQ self-heal task (`scd_init_irq`) exists specifically to work around its data-
  ready *pin* being missed/stuck, illustrating the same "assume a signal can be silently lost,
  build in a self-healing re-check" principle at the hardware-IRQ level too — the equivalent
  `Pin.irq()` pattern (`handler=lambda b: self.irq_trigger_event.set()`) if a new driver uses an
  interrupt pin, not just a Timer.
- A driver needing more than one periodic rate (BMP3xx: 1 Hz base tick divided down by
  `trigger_period` to the user-configured interval) runs a second small `_base_trigger()` task
  that counts base ticks and sets the "real" `trigger_event` once the configured interval is
  reached — rather than reprogramming the `Timer`'s own period at runtime.
- **Every `Timer.init()` call site's failure handler catches `except (OSError, MemoryError) as e:`,
  not a bare `except OSError:`** — a project-wide defensive widening (`asy_bmp3xx_driver.py`,
  `asy_scd30_driver.py`, `asy_sgp40_driver.py`, `asy_wifi_service.py`, `asy_ntp_client.py`,
  `system_service.py`), matching F.1's general "an `OSError` catch around a call that could
  plausibly exhaust memory should also catch `MemoryError`" rule. **Verified against
  `ports/rp2/machine_timer.c` at the pinned MicroPython v1.28.0 tag**: `Timer.init()`'s own
  documented failure mode is exactly
  `OSError(MP_ENOMEM)`, raised when `alarm_pool_add_alarm_in_us()` reports the RP2040's small,
  fixed hardware alarm pool is exhausted — there is no separate, `Timer.init()`-specific
  `MemoryError` path distinct from that `OSError`. The one real allocation in a `Timer`'s lifecycle
  (`mp_obj_malloc_with_finaliser()`, which — like any MicroPython object allocation — could
  theoretically raise `MemoryError` on a GC-heap-exhausted device) happens once, at construction
  (`Timer(...)`), not inside `init()`/`start_timer()`'s own call. The `MemoryError` half of the
  catch is therefore genuinely cheap, generic insurance against that construction-time or
  general-heap-exhaustion scenario, not a proven `Timer.init()`-internal failure mode — confirms the
  widening was correct to apply unconditionally rather than gated on proving the mode first, exactly
  as the project owner's original decision assumed.
- **Cascading-recovery-storm convention: a retry loop that fails non-raising (returns a sentinel
  like `(None, None)` rather than raising) needs its own capped exponential backoff, distinct from
  any outer `except Exception` backoff, or it will spin at full speed on a persistent failure.**
  This is a generalizable, checkable rule: any loop whose per-iteration call can fail by returning a
  sentinel rather than raising must check for that sentinel and back off — an outer
  `except Exception`-based backoff never fires for a call that fails this way, since nothing ever
  raises. The real, fixed instance: `captive_dns.py`'s `DNSServer.run()` calls
  `self.udps.recvfrom(4096)` (default `timeout_ms=-1`) in a loop; on a persistent `(None, None)` it
  now backs off 0.5s → 1s → 2s → 4s, capped at 5s, reset to the floor on the next successful
  `recvfrom()` — distinct from the same method's existing flat 3s backoff on its outer
  `except Exception`. Before this fix, a persistently-failing `recvfrom()` produced roughly 5
  warning-level log lines/second, continuously, for the DNS server task's entire lifetime. See
  `tests/test_captive_dns.py` for the regression coverage (real-timing tests proving the backoff
  curve and its reset-on-success behavior). Contrast `asy_ntp_client.py`'s own sync-retry path,
  which was already correctly bounded (`_NTP_SYNC_RETRIES=3`, `_NTP_RETRY_INTERV=15s`, then gives up
  and lets the task supervisor restart the whole task) — a new retry loop should follow that
  existing bounded shape, or `captive_dns.py`'s capped-exponential shape, rather than looping with
  no backoff of its own.

## C.10 Typing conventions

Already stated generally in Part D.6 — the sensor-driver-specific instances:

- `TYPE_CHECKING` guarded via `try/except ImportError: TYPE_CHECKING = False`, never an
  unconditional `from typing import ...`.
- PEP 604 `X | None` everywhere; never `typing.Union`.
- A caller-supplied object this file only touches structurally (a real `machine.Pin`, a
  `microdot.Request`, an `AsyFramManager` chunk/manager) gets a `Protocol` class defined fully
  inside `if TYPE_CHECKING:` describing just the methods/properties actually used — never
  instantiated at runtime, purely a typing aid. See `print_log.py`'s `_FramChunk`/`_FramManager`,
  `api_response.py`'s `_RequestLike`, `asy_wifi_service.py`'s `LEDControl`.
- `typing.cast()` has no runtime presence on MicroPython — see C.4.2 for the settled
  `get_data()` narrowing convention and the one genuine remaining use of a local `cast()` shim.
- A driver-local `*Results` tuple-of-optionals type alias (`SCDResults`, `BMPResults`) is
  declared under `if TYPE_CHECKING:`, used only as `_read_<sensor>()`'s return annotation — it's
  a plain tuple, not a `NamedTuple`, since it's an internal intermediate shape, not the public
  data model (C.6 covers that).

## C.11 Design decisions a new driver must make (datasheet + judgment, not precedent)

Everything above is already decided by the existing three drivers. What's genuinely new per
sensor:

1. **Bus**: I2C or SPI — determines which protocol-layer exception surface applies (C.3;
   SPI specifically is C.3.1, flagged best-effort/unproven).
2. **Identity check**: what does `setup()` verify before trusting the sensor is really there
   (chip-ID register, firmware-version CRC, serial-number + self-test, ...) — per the datasheet's
   own documented identification mechanism.
3. **Config location** (C.4.3): does each adjustable value live in the sensor's own NVM
   (→ no local schema, live readback only) or is it a software-only/volatile-on-power-cycle
   setting (→ `SensorReaderConfig` + schema)?
4. **Derived fields**: does this sensor's raw reading need `math_helpers`-style derived
   computation (wet-bulb, dew point, altitude, ...), and if so what's the formula's own
   authoritative source and valid domain (Part D.1)?
5. **Operating-range validation**: what does the datasheet document as the valid measurement
   range, and where's the right layer to reject an out-of-range reading — protocol layer (BMP3xx,
   no CRC framing so a bit-flip is otherwise undetectable) vs. relying on CRC/self-test alone
   (SCD30/SGP40, which do have per-transaction CRC framing)?
6. **Trigger rate**: fixed (SGP40's VOC algorithm needs an exact 1 Hz cadence) or user-configurable
   (BMP3xx's `SampleInterv`, SCD30's on-chip `MeasInt`)?
7. **FRAM/persistence needs**: does this sensor have state worth surviving a reboot beyond the
   generic error-history logging every driver gets for free (SGP40's VOC-algorithm-state backup
   is the only current example — a much larger addition than most sensors will need)?
8. **Errno/wrnno numbering**: pick a sequential scheme grouped by failing method, scoped to this
   driver's own `_NAME` stream, reusing `errno=10` for "initial setup failed" to match the other
   three drivers (C.7) — no cross-driver registry to consult or update beyond that one
   precedent.
9. **Digital-twin extension — required, not optional.** Every new sensor driver needs a matching
   chip fake under `digital_twin/` (`_<name>_chip.py`, same `FaultInjector`/`random_source`/
   datasheet-range/bounded-random-walk shape as `_scd30_chip.py`/`_sgp40_chip.py`/`_bmp3xx_chip.py`),
   wired into `machine.py`'s `_wire_i2c_devices()`/`_wire_spi_device()` bus maps, plus its own
   `tests/test_digital_twin_<name>.py` — see `digital_twin/README.md`'s "Adding a new chip fake"
   section for the concrete steps. A new **I2C** sensor is a small, mechanical addition (one new
   chip-fake file + one new dict entry); a new **SPI** sensor sharing an already-occupied SPI bus id
   with the FRAM chip is **not** automatically supported by the twin's current single-device-per-
   bus-id wiring — same README section explains what extending it would take. Do this as part of
   finishing the driver, the same session it's promoted to `src/` (Part D's checklist), not deferred
   — the digital twin exists to track the *whole* real driver portfolio, not just the sensors it
   started with, and a driver with no twin counterpart silently regresses the Unix-port integration
   run's own coverage (Part A.10). **Also update `html/definitions/<device>.json`** for every device
   the new driver's REST fields should appear on (Part H.5) — the website's own nav/
   sections/fields come entirely from that file (zero device-specific branching in `js/render.js`/
   `js/nav.js`), so a promoted driver with a working chip fake and REST endpoint but no matching
   definitions-file entry stays invisible on the website indefinitely, with nothing else in the
   pipeline surfacing the gap. Same session, not deferred, same rationale as the digital-twin
   extension itself.

## C.12 Testing

Covered fully by Part E.4 ("Hardware-touching files: mock at the raw bus-transaction
level only") — restated as the one sensor-driver-specific summary: mock `tests/machine.py`'s
raw `readfrom_mem`/`writeto_mem`/`readfrom_into`/`writeto`/`scan` only, letting the real
`*_I2C`/`*_Reader` logic (bit-packing, CRC, locking, error paths) run against a real
dict-of-registers fake. Part D.12's parameter-combination/boundary/NaN-inf
coverage requirements apply to any pure-computation helper a new driver adds (compensation math,
tick conversion) the same as they do to `math_helpers.py`. For I2C fault injection specifically,
real hardware only ever raises `OSError(EIO)` (NAK/bus fault) or `OSError(ETIMEDOUT)`
(bus-busy/clock-stretch) — never `ENODEV`, which is `SoftI2C`-specific; don't inject a fault code
a real bus can't actually produce.

## C.13 Readiness-gate scheme (sync `__init__` / async `setup()`)

Project-wide pattern for any class whose real construction work needs an `await` (I/O, or just
calling an inherited async logging method) but starts out attempted inside a synchronous
`__init__`. First proven by `asy_fram_driver.py`'s `FRAM_SPI` and `asy_spi_driver.py`'s
`SPIDevice`; now the standard for any class in the same position (`ConfigManager`,
`NotificationCoordinator`'s staged `register()`/`finalize()` variant — C.4.3).

- `__init__` stays synchronous: it only stashes constructor arguments and sets a readiness gate to
  "not ready." An explicit `async def setup()` does the real deferred work and flips the gate to
  "ready" on success.
- **Gate name/polarity is standardized**: `self.initialized: bool = False` → `True` — *except*
  where the underlying meaning is genuinely different from "has setup run," not just differently
  spelled. `ConfigManager.valid` stays `valid` on purpose: it means "setup ran *and* produced
  trustworthy data," a real distinction every current caller already relies on, not just a
  differently-named identical concept. Don't force a uniform name onto a genuinely different
  meaning.
- A `Type | None`-typed attribute is the *complementary* mechanism for one specific sub-resource
  that can independently fail *during* an otherwise-successful `setup()` (`PrintLogHistoryStore.fram`
  is the example — a `PrintLogHistory` still works, just without FRAM persistence, if its own FRAM
  chunk allocation failed). Not a competing choice against the bool gate — both can coexist on the
  same class, answering different questions ("has setup run at all" vs. "did this one piece work").
- **The response to "called before `setup()` ran" is never a free stylistic choice — it must match
  whatever raise/never-raise contract the class already declares (in its module docstring, or the
  comment immediately below it if the header itself was trimmed — see CLAUDE.md's docstring-length rule).**
  - A class documented as "never raises" (every `SensorReader`/`SensorReaderConfig` subclass,
    `PrintLog` family, `ConfigManager`) returns its documented sentinel and logs, exactly like every
    other failure mode that class already handles. This holds even for `FRAM_SPI` specifically,
    whose own docstring/comment promises "self-healing to a safe state without raising, except
    `__init__`/`setup()`'s one-time setup errors" — its pre-`setup()` sentinel-returning behavior
    was already correct.
  - `SPIDevice.__aenter__`'s raise is a structural necessity of Python's `async with` protocol (no
    sentinel-return option exists for a failed `__aenter__`), not a stylistic precedent — it doesn't
    extend to any other method on any other class.
  - **Verify per class, don't assume**: check the specific class's own module docstring/comment for
    an already-declared raise/never-raise contract before deciding the response shape, rather than
    copying whichever example was read most recently.
- **Not every readiness question needs a gate at all.** `AsyFramManager.get_chunk()`/
  `get_timestamped_chunk()` are pure bookkeeping (offset arithmetic, no hardware access) — safe
  before any `setup()` runs, and real hardware access always goes through `self.fram` (`FRAM_SPI`),
  which already has its own gate; a second one at the manager level would be redundant.
  `I2CDevice.setup()` performs only an *optional* identity probe with no state transition to
  guard — the underlying `I2C` bus is fully ready immediately from `I2C.__init__` itself, unlike
  `SPIDevice`'s CS-pin configuration. Add a gate because a class's own construction genuinely has an
  unready window to guard, not by default.
- **A staged, multi-call construction variant exists alongside single-shot `setup()`** —
  `NotificationCoordinator`'s deferred `register()`×N → `finalize()` shape (C.4.3). The same rules
  above apply once translated: every method reachable in the pre-`finalize()` window needs its own
  guard, not just the staging methods themselves (C.4.3's own note on this, closing a real gap found
  in this codebase — only `register()`/`finalize()` were originally guarded).

---

# Part D — `src/` Production-Quality Checklist

Files land in `src/` once they've cleared the full **production-quality** bar below (see CLAUDE.md's
"Hard rules"). This checklist keeps
getting refined against whatever file is going through it next; apply the current version in full
to every file making the move, not just whichever ones already have. "Production quality" here
means concretely: correct against real documentation, never raises
an uncaught exception, safe to run unattended and uninterrupted indefinitely, respectful of the
RP2040's limited resources, never blocks, and always returns a well-defined value — each expanded
below.

For a *new sensor driver* specifically, see Part C first — the shared architecture/
interface shape (layering, naming, error handling, config schema, ...) extracted from the three
drivers already promoted here. This checklist is how you know a file (that spec's shape or any
other) is good enough to move; Part C is what shape a sensor driver's code should take
in the first place.

Out of scope for this checklist: setting up the CI pipeline itself and the MicroPython Unix-port
toolchain build — that's already done (see BACKLOG.md/Part B) and is a one-time
project-level setup, not something each new file redoes. What follows is what changes, and what
you check, per file.

## D.0 Understand the function's purpose first

- [ ] Before judging correctness, be sure you actually understand what the function is *for* —
      read it alongside its callers, its existing comments, and any adjacent context, not in
      isolation. "It's mathematically consistent" isn't the same as "it does what it's meant to."
- [ ] If the intended purpose, expected input domain, or a caller's actual expectations are
      genuinely unclear after that, **ask up to 10 targeted clarifying questions** before
      proceeding — don't guess, and don't ask more than the ambiguity actually warrants. This is
      the same standing principle as CLAUDE.md's working agreement to flag genuinely ambiguous
      decisions rather than guess; the cap is there so "asking" doesn't become its own way of
      stalling.

## D.1 Correctness, verified against real documentation

- [ ] Identify the authoritative source for every non-obvious claim the code makes or depends on
      — a published paper/standard for a formula, a hardware datasheet for a sensor's operating
      range, an external library's own docs/repo for how its API actually behaves — and verify
      against *current* sources (web search, the actual datasheet, the actual upstream repo),
      never training memory or "how it probably works." Note the source in a code comment.
- [ ] Verify the implementation actually matches that source (coefficients, sign, order of
      operations, argument order/units) — don't assume existing code is correct just because it's
      already deployed.
- [ ] **If verifying against the authoritative source surfaces a discrepancy — the code doesn't
      match the documented behavior/formula/range — do not silently change it to match.** Flag the
      specific discrepancy to the project owner and ask before altering anything that changes real
      output. (This is distinct from fixing an internal bug you introduced earlier in the very
      same review, e.g. a typo in a range you just added — that doesn't need the same round-trip.)
- [ ] Verify the coded validity range/domain matches the source's *actual* valid domain, not just
      whatever range the existing code happened to have. (Found a real bug this way:
      `wet_bulb_temperature`'s humidity lower bound was `0.5%`; Stull (2011) only validates down
      to `5%`.)
- [ ] Where the formula's own domain is wider than how it's actually used, cross-check against the
      real caller's hardware constraints instead (e.g. a sensor's datasheet operating range).
      (`altitude_baro`'s 300-1250 hPa / -40-85 degC range comes from the BMP388/390 datasheet, its
      only caller — not from the barometric formula itself, which has no such bound.)
- [ ] Look specifically for functions with **no validity range check at all** — an easy gap to
      miss since the function still "works" for any input right up until it's asked to
      extrapolate a formula miles outside where it was ever validated.
- [ ] If review surfaces an inherent quirk or non-ideality (not a bug) — e.g. two independently-
      fit formula branches that don't perfectly agree at their boundary — don't silently
      "fix" it by guessing new coefficients. Document it with a code comment and add a regression
      test with a tolerance matched to the *measured* behavior, not an idealized one.

## D.2 No uncaught, unhandled exceptions

- [ ] Every function returns a clear "no data" sentinel (`None` here) — **never raises, under any
      input** — for:
  - missing input (`None`)
  - out-of-domain input, checked *before* any computation runs (guard clause, not a try/except)
  - any residual computational failure within the valid type contract (e.g. a near-boundary
    float edge case the range check didn't quite anticipate) — wrap only the actual computation
    in `try/except`, catching the *specific* exception types that can genuinely occur for that
    domain (`ValueError` for math domain errors, `ArithmeticError` for overflow/zero-division),
    never a bare `except:`.
- [ ] **Do not defend against out-of-contract input (wrong types) at runtime** if static typing
      already enforces the contract at every call site in CI (mypy here). That's dead weight on
      a resource-constrained target for a scenario that provably can't occur — scope defensive
      code to what the type contract actually allows through, not to "anything a Python caller
      could theoretically pass."
- [ ] Do explicitly verify `NaN`/`inf` — which *are* valid values within the type contract (still
      `float`) and which a real sensor fault could plausibly produce — degrade cleanly through
      the existing range checks. Don't assume; a naive range check usually already handles these
      correctly (a `NaN` comparison is always `False`), but confirm it and add a regression test.
- [ ] Confirm the exception net is complete: every `raise`-capable statement in the function body
      (arithmetic, indexing, attribute access, external calls) is inside a `try` that catches it,
      or is provably unreachable given the guard clauses above. Not "probably fine" — walk the
      function line by line and account for each one.
- [ ] **Specialty: raw hardware bus-transaction calls (`machine.I2C`/`machine.SPI` read/write/mem
      operations) are the one deliberate exception to "never raises."** A real transaction failure
      (`OSError` — NAK, timeout, device gone) is allowed to propagate uncaught out of a low-level
      bus driver, rather than being swallowed into a `None` sentinel here — this matches the
      legacy codebase's own existing pattern and is what every current Reader class (e.g.
      `asy_scd30_driver.py`'s `SCD30_Reader._read_scd`) already expects: it wraps a *whole*
      read/write sequence in its own `try/except Exception`, using the propagated exception itself
      to detect and count a real hardware failure. Silently returning `None` at the bus-driver
      layer instead would make that upstream detection invisible. This carve-out applies only to
      the actual bus-transaction call; a bus driver's own non-hardware failures (an uninitialized
      bus, a malformed caller-supplied format string) still get the normal `None`-sentinel
      treatment from the bullets above.
      **When reviewing a file that takes this carve-out, verify — don't assume — that every
      upstream caller of it actually closes the gap**: confirm each call site sits inside a
      `try/except` broad enough to catch what the low-level call can raise (typically `OSError`,
      but check the specific driver), so a real bus fault degrades to the caller's own error
      counting/self-healing path instead of ever reaching the top-level task supervisor and
      crashing the main loop. If a call site doesn't already do this, that's a real finding to fix
      or flag — don't take the carve-out as license to skip checking who actually catches it.
      **The `OSError`-NAK/timeout fault surface this bullet describes is I2C-specific on this
      port, confirmed during `asy_spi_driver.py`'s own `src/` promotion — don't assume it applies
      identically to SPI.** SPI has no ACK/NAK concept, and real RP2040 hardware SPI transfers
      (`extmod/machine_spi.c`'s blocking transfer path) have no error return at all once the bus
      is constructed: `write()`/`readinto()` genuinely cannot raise, not merely "in practice, let
      it propagate" the way this bullet frames I2C. `write_readinto()` is the one SPI exception,
      and it's a different shape entirely — a real `ValueError` for mismatched buffer lengths
      (`mp_machine_spi_write_readinto()`, shared by hardware and soft SPI), which is a caller-input
      mistake, not a hardware fault, so `asy_spi_driver.py` catches it and returns `None` rather
      than taking this carve-out. Check each bus's actual fault surface against current source
      before assuming this bullet's I2C-derived shape transfers unchanged.

## D.3 Stability for indefinite, unattended operation

These units run for years without a reboot. For any file moving to `src/`:

- [ ] No unbounded growth: no list/dict/buffer that grows with each call and is never trimmed, no
      accumulating counters that assume they'll be reset externally without confirming they are.
- [ ] No retained state between calls unless the function is deliberately stateful and documented
      as such — prefer pure functions (like `math_helpers.py`'s) wherever the problem allows it;
      they can't leak or drift by construction.
- [ ] No resource acquisition (file handles, locks, bus transactions) without a guaranteed release
      on every exit path, including the exception paths from D.2.
- [ ] Verified via design discipline and code reading, not an automated soak test — there's no CI
      gate for "ran for a simulated year," so this has to be reasoned about directly per function.

## D.4 Resource discipline for the RP2040 target

Dual-core Cortex-M0+ @ up to 133MHz, 264KB SRAM total (see F.1 above) — this
is not a machine with memory or cycles to spare:

- [ ] Avoid unnecessary allocations in anything called frequently (new lists/dicts/strings per
      call add up under MicroPython's GC, and a GC pause is itself a mild blocking risk — see
      D.5). Reuse buffers where the existing codebase already has a pattern for it.
- [ ] Avoid recursion (limited stack) and large intermediate data structures — prefer the
      straight-line, fixed-size-working-set version of an algorithm over a more "elegant" one that
      needs more scratch space.
- [ ] Prefer the cheaper stdlib call where it's a drop-in equivalent (e.g. `math.sqrt(x)` over
      `math.pow(x, 0.5)` — faster and more numerically precise for a square root specifically).
- [ ] Don't add runtime type/shape checks "just in case" (see D.2's out-of-contract-input
      bullet) — every unnecessary branch and comparison is cycles spent on hardware that doesn't
      have cycles to spare.

## D.5 Never block

- [ ] Confirm the function is non-blocking: no blocking I/O, no `time.sleep`, no unbounded loops.
      A pure computation like `math_helpers.py` is inherently safe here, but this must be checked
      explicitly for anything that isn't.
- [ ] If a function genuinely must do I/O or another long-running operation, it must be `async`
      and yield control appropriately, and must not stall timing-sensitive work like the Neopixel
      animation (see F.3 below — this is a standing design principle, not tied to
      any specific mechanism; the `get_long_block_lock()` shared lock that once coordinated this
      has since been retired along with its only real user, `socket.getaddrinfo()`). Never assume
      a one-off "it's probably fast enough."

## D.6 Typing

- [ ] Type-hint every parameter and return value.
- [ ] Verify the annotation *syntax itself* is actually safe on the target runtime by checking
      *current* official docs — don't reason from general Python knowledge alone. (Confirmed via
      MicroPython's own docs that `X | None` annotations are parsed but never evaluated at
      runtime, on every version checked — so they're safe regardless of whether the runtime
      otherwise supports `X.__or__`/`UnionType`. This was a real open question on record before
      being checked, not something to assume either way.)
- [ ] "Reasonable" also means not over- or under-typing: no `Any` where a real type is knowable,
      no unnecessarily narrow type that will make legitimate future callers fight the checker.
- [ ] If a file needs typing-only utilities that aren't plain annotation syntax — `TypeVar`,
      `Protocol`, `Generic`, `overload`, `TYPE_CHECKING` itself, ... — guard the import behind
      `if TYPE_CHECKING:` with a `try/except ImportError: TYPE_CHECKING = False` fallback, rather
      than importing `typing` unconditionally. Confirmed directly: `typing` is not an importable
      module at all on the MicroPython Unix-port test interpreter (`tests/test_crc_checks.py`'s
      `run()` helper needed this guard to use `Coroutine`/`TypeVar` for its generic return type).
      Plain `X | None` annotations don't need this — the bullet above already established that
      annotation expressions are never evaluated at runtime, so names inside them don't need to
      resolve either — but a real runtime call like `TypeVar("T")` does. This is the pattern every
      new `src/`/test file should use going forward.
- [ ] **`mpy-cross` does not dead-code-eliminate `if TYPE_CHECKING:` blocks the way it does an
      `if micropython.const(0):` branch** — confirmed empirically by compiling real `src/`/`ext/`
      files with this repo's own `mpy-cross`: the guarded imports/`Protocol` classes/type aliases
      fully survive into the `.mpy` bytecode (qstrs included), since `TYPE_CHECKING` is a plain
      runtime-checked global, not a compile-time constant. This doesn't change anything you need to
      write differently in a file going through this checklist — the `if TYPE_CHECKING:` guard
      convention above is still correct and required — but don't assume the guard is "free" at
      build time the way a `const()`-gated branch is; stripping these blocks from the frozen build
      is a real, measured space saving (~3.6KB across the files promoted at time of measurement)
      still tracked as unbuilt future work in BACKLOG.md's "Firmware build script should strip..."
      item, not something any individual file's own promotion needs to act on.

## D.7 Always-defined return values

- [ ] Every code path returns explicitly and matches the declared return type — no falling off
      the end of a function into an implicit `None` that isn't in the annotated return type, no
      partially-initialized variable reaching a `return` on some path but not others.
- [ ] mypy's `warn_return_any`/`disallow_incomplete_defs` (already enabled, see pyproject.toml)
      catch most of this statically — but still read every `return` by eye; a function that
      type-checks can still have a path that returns something *technically* valid but
      semantically wrong (e.g. a clamped value that silently clips instead of signaling invalid).

## D.8 General improvement pass, without changing functionality

- [ ] Beyond the required fixes above, look for opportunities to genuinely improve the function —
      speed, resource usage, numerical accuracy, or reduced complexity — as long as the observable
      behavior for every valid input stays identical. (The `math.sqrt(x)` vs. `math.pow(x, 0.5)`
      swap in D.4 is this in practice: faster *and* more precise, zero behavior change.)
- [ ] "Without changing functionality" is a hard constraint, not a suggestion: the full existing
      test suite must still pass unchanged after the improvement, and if the improvement is
      significant enough to want its own regression test, add one rather than relying on manual
      spot-checking.
- [ ] This is a genuine pass, not a rubber stamp — but also not a mandate to rewrite working code
      for style. If nothing meaningfully improves speed/resources/accuracy/complexity, say so and
      move on rather than manufacturing a change.

## D.9 Check against current MicroPython, not the version this code predates

- [ ] Much of this codebase's history predates MicroPython 1.20; the project's own build target
      has since moved forward to whatever's the latest *stable* release (see F.1 above and
      `toolchain/versions.toml`'s `[micropython] ref`, currently v1.28.0). Don't assume
      code written years ago still reflects the best way to do something on the current target —
      check, every time a file goes through this review, not just once.
- [ ] Check the MicroPython changelog/release notes
      ([github.com/micropython/micropython/releases](https://github.com/micropython/micropython/releases))
      between whatever version the code plausibly targeted and the current pin for anything
      relevant to the file under review: new stdlib module features, simplified semantics,
      interpreter-level performance work that changes what's worth hand-optimizing, deprecated
      patterns replaced by better ones. Note findings even when nothing needs to change in the code
      itself — that's still a useful outcome, not a wasted check. (`crc_checks.py`'s own heavy
      bytearray/memoryview slicing already benefits for free from 1.26's "avoid heap-allocating
      slices when subscripting bytearray/memoryview" interpreter change; nothing to rewrite there,
      just confirmation of why it's already reasonably fast on the current target.)
- [ ] Look specifically for the old `u`-prefixed module names (`uasyncio`, `ustruct`, `ujson`,
      `ucollections`, ...) — MicroPython consolidated these to their plain names years ago; the
      `u`-prefixed forms still work as aliases today but are the clearest tell that a file predates
      that consolidation. (`crc_checks.py` already uses the modern `asyncio`/`struct` names — check
      any legacy (`python/`, `modules/`) file going through this review for the old `u`-prefixed
      pattern, don't assume it's already been swept everywhere.)
- [ ] Same "without changing functionality" hard constraint as D.8 applies when a
      modernization is purely a rewrite for currentness — the existing test suite must still pass
      unchanged. If a newer API's *semantics* genuinely differ from what the old pattern did (not
      just a rename or an interpreter-level speedup), treat that like any other behavior change
      under D.1: flag it and ask before adopting it, don't silently swap it in.

## D.10 API consistency, within a file and across the project

- [ ] Within a set of related functions/classes, give every member the same shape — same
      parameter names, same parameter order, same optionality, same return convention — even
      where one member's shape looks initially unnecessary for that member alone. (`crc_checks.py`'s
      `CRC_Pass`/`CRC8`/`CRC16`/`CRC32` all take `poly: int | None = <default>` and forward it to
      `CRC_Base.__init__`, even though `CRC_Pass` can never actually use a `poly` — a caller or
      future dispatch table can treat all four identically without special-casing one of them.)
- [ ] Prefer the mechanism that makes the uniform shape *actually* consistent, not just
      superficially matching — forwarding a parameter through to a shared base/helper and letting
      *its* existing invariants do the work is more consistent than hardcoding a special case per
      member. (`CRC_Pass` forwards `poly` to `CRC_Base` and relies on the base class's own
      `num_bytes == 0` invariant to nullify it, rather than hardcoding `None` itself.)
- [ ] Beyond the current file: check how comparable functions/classes elsewhere in the project
      already express the same kind of thing — parameter naming, return-value conventions (e.g.
      `None` for invalid/no-data, matching the module's own stated contract), guard-clause
      ordering, comment style — and match them, rather than introducing a locally-plausible but
      differently-shaped alternative. Where an existing file's convention is itself questionable,
      flag it rather than silently diverging from it in the new file.
- [ ] This is a deliberate, ongoing check across the whole project, not just "whatever pattern
      happens to already be in the file you're editing" — if two files solve the same kind of
      problem in visibly different ways, that's a finding worth raising, not something to leave
      for a future session to notice.

## D.11 Readability / conciseness

- [ ] One-line "why" comment per function — cite the formula's name/source and its valid domain
      where that's the "why" (see D.1). For a file organized as a set of related
      methods/classes around one shared algorithm rather than several independent formulas (e.g.
      `crc_checks.py`), a comment on what that specific method does differently from its siblings
      is enough — it doesn't need to re-cite the algorithm identity already stated once at module
      level. Don't restate what the code already says.
- [ ] Per-function/per-method explanations are always `#` comments, never docstrings — a
      module-level docstring for the file's own shared contract is expected (see below), but don't
      mix a docstring into an individual function within the same file.
- [ ] State a shared contract once, at module level (e.g. "returns `None`, never raises, if ...")
      instead of repeating it in every function's docstring/comment — and this applies across
      files too, not just within one: a principle already established once as a project-wide rule
      elsewhere in this checklist (e.g. D.2's "trust the type contract, mypy already enforces
      it at every call site") doesn't need independent restating in every file's own module
      docstring just because an earlier file's docstring happened to spell it out locally.
- [ ] Keep the control flow simple and in a consistent order: `None`-check, then range-check
      (plain guard clause, no `try` needed if it can't raise), then the `try`-wrapped computation.
- [ ] **Keep documentation itself concise — a module docstring is a short header, not an essay.**
      State the file's purpose and shared contract in a few short paragraphs. A genuinely
      permanent design fact belongs in CLAUDE.md/this document as current-state documentation,
      not spelled out at length in the file itself; a still-open question or deferred item belongs
      in BACKLOG.md instead — BACKLOG.md is active working memory, not a place to archive design
      history once it's settled. Per-function/inline comments stay within **3 lines, prefer
      fewer** — a block running longer than that is a sign the detail belongs in one of those
      other docs, not in the file itself. (`config_manager.py`'s cache-based design has one real
      consequence — a corrupted on-disk file is silently repaired from cache rather than detected —
      that lives as a permanent fact in CLAUDE.md's architecture reference instead of an essay in
      the file.)

## D.12 Unit tests

- [ ] Tests must run in whatever environment the project's testing-architecture docs actually
      require (check first — e.g. this project requires the real target interpreter, not just a
      CPython stand-in; see BACKLOG.md/Part E), not just "whatever's convenient."
- [ ] For every function, cover each parameter individually **and the combinations where
      parameters interact** (e.g. a branch selected by one parameter's sign, tested against both
      valid and invalid values of the other parameter — not just each parameter varied in
      isolation while the other stays at a fixed "safe" value):
  - `None` for each input individually, and combined
  - a valid, typical input asserted against a **sanity bound**, not an exact reference value
    (these are numerical approximations, not identities)
  - just-out-of-range on each side of every checked bound
  - the exact boundary values themselves are *accepted*, not rejected
  - `NaN` and `+inf`/`-inf` on every argument
  - any known formula-inherent quirk found in D.1, as a bounded regression check
  - physical/logical invariants where they exist (e.g. dew point never exceeds air temperature;
    an inverse pair like abs/rel-humidity round-tripping back to its own input; clamping
    behavior at the clamp's own bounds)
- [ ] Do **not** write tests for scenarios the type system already rules out (see D.2) —
      keep the suite focused on what can actually happen, not padded with impossible cases.
- [ ] **If this file is one layer in a larger real call chain** (a driver under a manager, a
      manager under a real consumer), module-level tests alone are not enough, even ones that
      mock only the raw bus transaction. Also add integration tests that drive the same
      good-and-failure scenarios through the actual real chain up to the real consumer, not by
      calling this file's own methods directly. (Established for `asy_fram_manager.py`:
      `tests/test_fram_integration.py` proves the same self-heal/hard-fail/pause outcomes already
      covered in `tests/test_asy_fram_manager.py`'s own tests still hold when driven through the
      real `SensorReader` → `PrintLogHistoryStore` → chunk → `FRAM_SPI` chain instead.)

## D.13 Wire into the existing pipeline

- [ ] Extend the lint/typecheck config's scope, and the CI job's explicit path arguments, to
      include the file's new location.
- [ ] Add the file's tests to (or confirm they're picked up by) the existing manual test-runner
      script, so the exact same command works locally and in CI.

## D.14 Verify, don't assume

- [ ] After every change, actually run lint/typecheck/tests locally and read the output — don't
      report success without having done so.
- [ ] Diff the finding count before/after against files you didn't touch, to confirm you haven't
      introduced or masked a regression elsewhere.
- [ ] If working in parallel with other sessions touching the same shared infrastructure (e.g.
      after a rebase), re-check for duplicated or conflicting mechanisms and reconcile docs
      carefully — don't leave two contradictory descriptions of the same thing.

## D.15 Method ordering within a class

- [ ] Within each class, order methods private-first, then public: a) private (`_`-prefixed)
      methods on top, b) public methods on the bottom.
- [ ] Within each of those two groups, order by role (omit a category entirely if the class has no
      methods of that kind): 1. Starters (`start_*`/`stop_*`/`get_*_starters`), 2. Getters,
      3. Setters, 4. Others. Keep each sub-bucket's original relative order among its own members.
      **The Starters bucket's `stop_*` covers a task/timer-lifecycle stop paired with a `start_*`
      of the same resource** (e.g. `stop_timer()` alongside `start_timer()`/`get_timer_starters()`)
      — not every method whose name happens to start with "stop". A setter-shaped business-logic
      method that's merely named `stop_<something>` (e.g. a sensor command like
      `stop_continuous_measurement()`, which stops a *sensor mode*, not this driver's own
      task/timer) belongs in Setters or Others per its actual role, not in the Starters bucket by
      name alone.
- [ ] `__init__` and other dunders always stay first in the class, ahead of this scheme, untouched.
- [ ] This is a pure reorder: it must not change any method's body, decorators, or docstring/
      comments, and must not change the file's module-level statements (imports, constants, module
      functions) at all — verify with an AST-level comparison against the pre-reorder version (per-
      class multiset of method name + full source text, decorators and trailing same-line comments
      included), not just a visual diff, since a manual reorder can silently drop a decorator or a
      trailing `# type: ignore` comment. The existing test suite must still pass unchanged, and
      lint/typecheck finding counts must match the pre-reorder baseline exactly.

## D.16 Only then

Move the file into `src/`, and only after all of the above is actually done and passing — not
planned, not "should be fine."

---

# Part E — Testing & Coverage

Unit tests for `src/` (fully-reviewed code — see CLAUDE.md). Total
test/file count drifts every time a test is added, so it isn't tracked as a fixed number here — get
the current count with `ls tests/test_*.py | wc -l` (files) and `grep -c '^def test_'
tests/test_*.py` (tests).

## E.1 Why not pytest

Tests run under a **real MicroPython interpreter** (the Unix port), not CPython — "as close to the
real environment as possible" means the actual MicroPython runtime, not CPython plus
MicroPython-flavored stubs.
Since pytest itself only runs under CPython, it isn't the test runner here: `scripts/test.sh`
instead shells out to a built MicroPython Unix-port binary directly, once per `tests/test_*.py`
file, and checks its exit code. `pytest` stays available in `pyproject.toml`'s dev dependency
group for possible future CPython-side orchestration, but nothing here uses it yet.

## E.2 Test framework

`microtest.py` is a minimal collector/runner (find every `test_*` function in a module, call it,
report PASS/FAIL, exit non-zero on any failure) — not CPython's `unittest`, which isn't part of
the MicroPython Unix port's default "standard" build. Test files just use plain `assert`.

## E.3 Running

```
scripts/test.sh
```

Builds the MicroPython Unix port on first run (via `uv run toolchain/setup_toolchain.py`'s
`setup` — building/verifying the Unix port is just part of what `setup`/`test` already do, see
Part B — cached under `$PICO_TOOLCHAIN_DIR`, default `~/pico-toolchain`) and
reuses it afterwards. `SKIP_APT=1 scripts/test.sh` skips that first-run apt-get install if the
required system packages (see `toolchain/versions.toml`) are already present. To run a single
test file directly once the interpreter is built:

```
MICROPYPATH="src:tests:frozen_modules:.frozen" ~/pico-toolchain/micropython/ports/unix/build-standard/micropython tests/test_math_helpers.py
```

`.frozen` is required in `MICROPYPATH` (not just `src:tests`) because MicroPython's `MICROPYPATH`
env var replaces the interpreter's default `sys.path` rather than extending it, and the default
path is what makes frozen-in modules (`asyncio` included) importable at all. `math_helpers.py`
never surfaced this since it doesn't use `asyncio`; confirmed directly against the built
interpreter for `crc_checks.py`, which does. **`.frozen` is a literal MicroPython sentinel, not an
ordinary directory** — `py/builtinimport.c`'s `MP_FROZEN_PATH_PREFIX ".frozen/"` routes any path
starting with that exact string straight to the compiled-in frozen-module table, never touching the
real filesystem; a real file placed on disk under a directory actually named `.frozen/` is silently
unimportable (confirmed directly against the pinned v1.28.0 source, after `frozen_modules/`'s own
build pipeline hit exactly this — see Part A.9). `frozen_modules` is a separate, ordinary,
gitignored directory (`scripts/build_frozen_html.sh`'s own output) added alongside `.frozen` for
this reason — `src/sensortask_wozi.py`'s `import frozen_html` needs it on `MICROPYPATH` too.

## E.4 Hardware-touching files: mock at the raw bus-transaction level only

For a `src/` file that talks to real hardware (`asy_i2c_driver.py` and `asy_spi_driver.py`), the
MicroPython Unix port's own `machine` module has no `I2C`/`SPI`/real `Pin` (confirmed directly:
only `PinBase`/`Signal`/`mem8`/`mem16`/`mem32`/`idle`/`time_pulse_us`). `tests/machine.py` is a
fake `machine` module, resolved ahead of any real one because `tests` comes before `.frozen` on
`MICROPYPATH`. Per this project's mocking-boundary convention, it mocks only the raw bus
transactions (`readfrom_mem`/`writeto_mem`/`readfrom_into`/`writeto`/`scan`/`deinit`), backed by a real
dict-of-registers store, so the driver's own logic (bit-packing, byte order, locking, error paths)
runs for real against it.

`asy_i2c_driver.py`/`asy_spi_driver.py` resolve `Lockable` against the real `src/base_classes.py`
(along with its own dependencies, `config_manager.py` and `print_log.py`), like any other `src/`
import.

`tests/test_print_log.py`/`tests/test_base_classes.py` are a third instance of the same mocking
boundary, for FRAM: they now drive `print_log.py`'s `PrintLogHistoryStore` (and, through it,
`base_classes.py`'s `SensorReader`) against the real `AsyFramManager` (`asy_fram_manager.py`, now
itself promoted to `src/`), running against `tests/_fram_chip_fake.py`'s simulated MB85RS64V chip
- the same fake `asy_fram_driver.py`'s own tests use, driven by `tests/machine.py`'s fake SPI.
`PrintLogHistoryStore` only ever calls `AsyFramManager.get_chunk()` and, on the chunk it gets back,
`get_buffer()`/`write_into()`/`read_into()`; `print_log.py`'s own `_FramManager`/`_FramChunk` stay
`TYPE_CHECKING`-only `Protocol`s describing just that narrow surface (kept even now that the real
class is promoted, to avoid a runtime import cycle and stay decoupled from its concrete shape - see
`print_log.py`'s own module docstring). "Survives a reboot" is proven by constructing a second
`AsyFramManager` whose underlying `FRAM_SPI` is pointed at the *same* `FakeMB85RS64V` instance and
replaying the same `get_chunk()` call sequence - genuinely round-tripping through the real
dual-copy+CRC on-chip format, the same as a real chip's contents surviving a power cycle.

Real chip-level fault injection (`tests/_fram_chip_fake.py`'s `drop_wren` etc., and directly poking
simulated on-chip bytes to model a torn write or exhausted dual-copy redundancy) covers every FRAM
failure mode still reachable through the real, audited `AsyFramManager` - a hardware-reported
failure `write_into()`/`read_into()` already turn into a clean `False`, no catch needed. Two
Protocol-level scenarios no longer have a real-class equivalent at all: `asy_fram_manager.py`'s own
`src/` promotion audit confirmed `get_chunk()` never raises and `_write_chunk()`/`_read_chunk()`
wrap their entire bodies in `try`/`except`, so `write_into()`/`read_into()` can no longer actually
raise through it. Those two are still proven via a minimal local `_RaisingFramChunk`/
`_RaisingFramManager` fake (structurally satisfying the same Protocol, not inheriting from the real
classes) in each test file - defense-in-depth against the Protocol contract in the abstract, not
against what this one concrete implementation currently guarantees. This was what caught a real gap
during `print_log.py`'s own review: `_write()`/`_read()` originally called `get_buffer()`/
`get_data_buf()` (and, in `_read()`, `read_into()`) *before* their `try:` block started, so a raise
from any of those would have propagated uncaught instead of degrading to a clean `False` return
like every other FRAM failure here already does. Fixed by widening both `try` blocks to cover the
whole body.

## E.5 Coverage

```
scripts/test.sh --coverage
```

Reports line coverage of `src/` only (not `tests/`'s own helper/mock modules), from the same
`tests/test_*.py` suite `scripts/test.sh` already runs. No coverage threshold is enforced
anywhere — CI reports the numbers, it never fails the build over them.

Since `coverage.py` only runs under CPython and `src/` only ever runs under the real MicroPython
Unix-port interpreter (see E.1 above), coverage collection and reporting are two
separate stages, not one tool doing both:

1. `tests/_coverage_runner.py` runs *inside* MicroPython, wrapping each `test_*.py` file with
   `sys.settrace` — verified directly against a real build (not assumed from CPython
   documentation): MicroPython's `sys.settrace` reports the same `(frame, event)` shape closely
   enough that a CPython-style line tracer records exactly the executed-line set `coverage.py`
   itself would expect. It records every line executed whose `co_filename` starts with `src/`
   (so `tests/machine.py` and the test files themselves are never counted) and dumps the result
   as JSON.
2. `scripts/_render_coverage.py` (a separate, self-contained `uv run` script, like
   `toolchain/setup_toolchain.py`) runs under CPython afterwards, merges every test file's JSON
   dump, feeds the result into `coverage.py` via its `CoverageData.add_lines()` API — a
   documented integration point for exactly this "foreign coverage source" case — and lets
   `coverage.py`'s own report engine render the HTML/XML/markdown output from data it never
   collected first-hand.

The one MicroPython Unix port binary (`ports/unix/build-standard/`) backs both plain
`scripts/test.sh` and `scripts/test.sh --coverage` — it's always built with
`MICROPY_PY_SYS_SETTRACE=1` (`build_unix_port()` in `toolchain/setup_toolchain.py`), so there's no
separate coverage-only interpreter to build or cache. Compiling settrace support in adds an inert
hook check in the bytecode dispatch loop when `sys.settrace()` is never called — a negligible,
behavior-neutral cost for a plain (non-coverage) test run, confirmed directly by running the full
suite both ways and comparing results. `ports/rp2`'s firmware build never gets this flag; it's
dev/test tooling only, entirely separate from what ships to real hardware.

Produces, at the repo root (all gitignored, regenerated every run):

- `htmlcov/index.html` — browsable line-by-line HTML report.
- `coverage.xml` — Cobertura XML.
- `coverage_summary.md` — a markdown table.

**Locally, `scripts/test.sh --coverage` does not open anything automatically** — it only prints
the three paths above; open `htmlcov/index.html` yourself (e.g. `xdg-open htmlcov/index.html` on
Linux, `open htmlcov/index.html` on macOS) to browse the HTML report.

**On GitHub, there is no visualization on the repo's main page** — no README badge, no GitHub
Pages. What CI (`.github/workflows/ci.yml`) actually does with each of the three files, all as
non-gating, `continue-on-error: true` steps:

- `coverage_summary.md` is appended to that workflow run's **Job Summary** — click into the
  specific run under the repo's Actions tab, the table is at the bottom of that run's page. This
  needs no external service and always works.
- `htmlcov/` is uploaded as a **downloadable build artifact** on that same run's page — GitHub
  doesn't render it inline; download the zip and open `index.html` locally to browse it.
- `coverage.xml` is uploaded to [Codecov](https://about.codecov.io/) (free for public repos), which
  can add PR comments/checks and its own hosted dashboard — but only once this repo is registered
  at [codecov.io](https://about.codecov.io/) and either a `CODECOV_TOKEN` repo secret or Codecov's
  OIDC/tokenless support is set up; that account-linking step hasn't been done yet, so today this
  step just runs and silently produces nothing visible.

### E.5.1 Reading the numbers: three systematic false-negative patterns, not missed test cases

A below-100% file isn't automatically a missed-test hint - three patterns recur across every
`src/` file's "missed" line list and are artifacts of this specific tracing pipeline, confirmed
directly against a real build (`sys.settrace` during both class-body execution and a plain
function call, dumping the traced `(lineno, co_name)` pairs):

- **`micropython.const(...)` assignments are compiled away entirely** — MicroPython folds the
  named constant into every place it's used at compile time, so the assignment statement itself
  never becomes bytecode and never fires a `line` trace event, e.g. `print_log.py`'s
  `_LOG_OFF = const(0)` block. `coverage.py`'s own static analysis (run separately, under CPython,
  by `scripts/_render_coverage.py`) still lists these as executable source lines, so they always
  show as 0-hit misses despite being fully "exercised" in the only sense that's meaningful for a
  folded constant.
- **A decorated function's traced `line` event lands on the decorator line, not the `def` line
  underneath it** — confirmed by tracing a class body's own execution (where a bare `def foo():`
  correctly traces as its own `def`-line hit, but a `@staticmethod`-decorated one traces the
  `@staticmethod` line instead). `coverage.py`'s CPython-based line map still expects a hit on the
  `def` line (matching Python's own `ast` module), so every `@staticmethod`/`@classmethod`
  definition's `def` line shows as missed even when the method is called throughout the suite -
  see e.g. `print_log.py`'s `level_off()`/`level_err()`/etc. or `asy_i2c_driver.py`'s
  `_bitfield_range_ok()`/`_bitmask()`/`_bytes_to_int()`/`_readfrom_mem()`/`_writeto_mem()`. The
  method's own body line (e.g. the `return` statement) is traced normally and shows as covered.
- **A bare `while True:` header never fires its own `line` trace event, at any iteration** —
  confirmed directly (a minimal repro traced every other statement in the loop body across four
  iterations, but never once traced the `while True:` line itself): the always-true condition is
  folded away at compile time into an unconditional jump, the same spirit as the `const()` folding
  above but for a control-flow statement rather than an assignment. Found via `system_service.py`'s
  own `src/` promotion (`status_counter()`'s and `start_and_check_tasks()`'s outer loops), both
  otherwise fully exercised by `tests/test_system_service.py`.

Separately (not a tracer artifact, but also not a missed-test hint): several `except` branches
across `src/` guard against outcomes that are provably unreachable given the guarantees the rest
of the same function already establishes before reaching them - e.g. `crc_checks.py`'s
`add()`/`add_into()` wrap `pack_into()` in a `try` for a `ValueError` that can't fire because the
CRC value is always masked (`crc &= self.all_set`) into exactly the range `self.fmt` encodes, or
`_crc()`'s own `if self.poly is None: return crc` guard, which every current caller already
checks for before ever calling `_crc()`. Writing a test to reach one of these would mean
monkeypatching `struct.pack_into`/an internal method to lie about its own success - testing the
mock, not the driver - so these are left as documented dead code (defense-in-depth against a
future caller violating today's invariants) rather than chased for a coverage number.
`math_helpers.py`'s five `except (ValueError, ArithmeticError)` blocks are the same category: each
function's own domain guard (checked *before* the `try`) already rejects every input - including
NaN/Inf, per `tests/test_math_helpers.py`'s own `*_nan_and_inf_return_none` tests - that could
otherwise reach a math-domain error inside it.
`print_log.py`'s `get_log()` has the same shape from an `if` branch rather than an `except`:
its per-entry loop's `if errno == _NO_ERR or errno == _NO_WRN:` treats both sentinels as
equivalent "nothing recorded" markers, but only `_NO_ERR` can actually land in `self.history` -
`wrn_s()`'s own "nothing to record" default is `wrnno=_NO_ERR` (not `_NO_WRN`), and
`_store_err()`'s `if errno <= _NO_ERR: return` guard fires on that default before the `_NO_WRN`
offset is ever added, so a real warning always stores `_NO_WRN + N` for some `N >= 1`, never bare
`_NO_WRN`. **Confirmed intentional, not a bug, per the project owner**: kept for defensive
symmetry with the `_NO_ERR` arm (which *is* reachable, via `reset()`'s history-refill), and
because a fresh/reset history slot needs a well-defined "nothing recorded" value regardless of
which sentinel a future caller might end up storing there.

---

# Part F — Platform Target & MicroPython Runtime Facts

Folded in from `CLAUDE.md`'s former "Platform target" section (and the genuinely spec-shaped items
from its "Hard rules" section) — the load-bearing hardware/runtime constraints referenced
throughout Parts C-E above. This is now the sole copy; `CLAUDE.md` carries only short pointers to
this Part — see this document's front matter for that tradeoff.

## F.1 Core platform facts

- Deployed units run **MicroPython 1.26** on **Raspberry Pi Pico W (1st gen / RP2040)**. Code
  ships as **frozen bytecode** compiled into the firmware — it is not loaded from the device
  filesystem at runtime, and CPython-only stdlib features/behavior cannot be assumed.
  - Upstream MicroPython has moved past 1.26 (1.28.0 was the latest stable as of the last
    doc-verification pass) — don't assume "current docs" and "1.26 behavior" are the same thing.
    When in doubt about whether an API changed between 1.26 and latest, say so explicitly rather
    than silently documenting latest-only behavior as if it applies to deployed devices.
  - **1.26 is the pin for the current, deployed codebase only.** This refactor
    is explicitly meant to move the version target forward to whatever is the most recent *stable*
    release at that time (MicroPython, pico-sdk, picotool, Microdot) and to actively use relevant
    improvements/new features those releases introduced — not just reproduce 1.26-era behavior
    under a newer version number.
  - **MicroPython 1.26 already bundles pico-sdk 2.1.1 as its internal `ports/rp2` submodule** —
    confirmed via web search, not training-data memory. Since pico-sdk 2.0.0, a standalone
    `picotool` build must match the pico-sdk major.minor version it's used against (enforced via
    marker files from `sudo make install`/`cmake --install`, not just having the binary on `PATH`)
    or the build fails with "Incompatible picotool installation found." This means
    `update_and_install.txt`'s standalone `pico-sdk`/`picotool` clones need to be checked out at a
    matching `2.1.x` tag *today*, not just "whatever's current" — see BACKLOG.md's "Dev/build
    environment setup" item for the full finding.
  - `machine.WDT` hard-caps at **8388ms** on RP2040. Current code uses `WDT(timeout=8000)` — only
    388ms of margin. Don't casually increase this without checking the cap still holds against
    current docs.
  - `RP2040`: dual-core Cortex-M0+ @ up to 133MHz, 264KB SRAM (6 banks), 2×I2C, 2×SPI, 2×UART,
    8×PIO state machines.
  - Pico W's littlefs partition (~848KB) is smaller than plain Pico's (~1.37MB) because Pico W's
    firmware image is larger (CYW43 driver + WiFi/BT firmware blobs baked in) — the filesystem
    occupies whatever flash remains after the firmware image, not a fixed per-board reservation.
  - **A soft `machine.Timer` callback (the default — no code in this repo passes `hard=True`) can
    be silently dropped, not just delayed.** Confirmed against real `py/scheduler.c`/
    `shared/runtime/mpirq.c`/`ports/rp2/machine_timer.c` source: firing dispatches via
    `mp_sched_schedule()`, which returns `False` and drops the callback if MicroPython's
    fixed-depth scheduler queue (`MICROPY_SCHEDULER_DEPTH=8` on rp2, shared by every soft
    timer/IRQ on the device) is already full — no exception anywhere in that chain, and no way for
    Python code to detect a dropped vs. not-yet-run callback. A periodic timer self-heals on the
    next tick; a one-shot timer does not fire again. A software timeout to guard against this was
    considered for `system_service.py`'s two exposed call sites (the reboot-reset timer,
    `start_timers()`'s chained sequencer) and rejected: it would just be a second, uncoordinated
    clock racing the real hardware watchdog every real deployment already arms, and the scenario it
    defends against (no watchdog configured) is test-only. Don't re-propose a software-timeout
    mitigation for this without a materially different justification. `asy_wifi_service.py`'s
    `_hotspot_client_absent()` handles its own `ONE_SHOT` hotspot-timeout timer differently — no new
    clock, just counting the existing `wifi_refresh_sec` ticks it already gets while hotspot mode has
    no client, and forcing the reconnect once that count implies the timer should have fired by now.
  - **`[x] * n` (list repeat) can segfault the whole interpreter process, not just raise, for n in
    roughly 2⁶¹–2⁶³** — confirmed by direct reproduction (`[0] * (2**62)` → SIGSEGV, no `try/except`
    catches it). Below ~2⁶¹ it raises `MemoryError` like `bytearray(n)`; at/above 2⁶³ it raises
    `OverflowError`; the gap in between is the dangerous range, likely from the repeat's internal
    `n * sizeof(pointer)` byte-count multiplication overflowing before being bounds-checked (`bytearray`
    has no such intermediate multiplication, hence no gap). Any new code allocating a
    list/deque/buffer sized from external or caller-supplied input must clamp the size *before* the
    allocation, not just catch `MemoryError` reactively — see `base_classes.py`'s `LockableBuffer`/
    `print_log.py`'s `PrintLogHistory` for the established clamp-then-allocate pattern.
  - **`machine.Timer.init()` can raise `OSError(ENOMEM)` if the RP2040's alarm pool is exhausted** —
    confirmed against real `ports/rp2/machine_timer.c` source. Every `Timer.init()` call site in this
    codebase must handle it (degrade gracefully if a safe fallback exists, otherwise let the failure
    stay isolated to whatever that one timer was for) — see `system_service.py` for the established
    pattern. `Timer()`'s bare constructor and `Timer.deinit()` never allocate/raise; `WDT.feed()` is a
    bare register write and cannot raise either.
  - **`MemoryError` is not an `OSError` subclass in MicroPython** — an `except OSError:` alone is
    blind to allocation failure; anywhere an `OSError` is caught around a call that could also
    plausibly exhaust memory, catch `(OSError, MemoryError)` instead.
  - **RP2040's real firmware build uses single-precision `float` (`MICROPY_FLOAT_IMPL_FLOAT`,
    24-bit mantissa, exact integer range up to `2**24`); this project's own Unix-port test rig uses
    double precision instead (`MICROPY_FLOAT_IMPL_DOUBLE`, 52-bit mantissa, exact up to `2**53`)**
    — confirmed directly against `ports/rp2/mpconfigport.h` and
    `ports/unix/variants/mpconfigvariant_common.h`. Both targets use arbitrary-precision `int`
    (`MICROPY_LONGINT_IMPL_MPZ`), so an `int` value can exceed either threshold; `float(int)`
    beyond it silently rounds rather than raising. Same "the Unix-port test rig can't reproduce a
    real-hardware boundary" shape as the `ticks_ms()` period fact below — a test proving exactness
    up to `2**53` on this rig says nothing about the stricter `2**24` real-hardware limit.
    `config_manager.py`'s `coerce_numeric()` (A.8's numeric-coercion policy) is the one place this
    currently matters: its int→float direction has no exact-round-trip check, on the premise every
    int is representable as a float — true only within this limit. Accepted, not fixed, because no
    real schema field's own bounds go anywhere near it (see A.8 for the full reasoning).
  - **`struct.pack()`/`pack_into()` silently zero-pad or truncate on a value/argument-count
    mismatch instead of raising**, unlike CPython. Don't rely on a mismatch surfacing as an
    exception; validate shape before packing if it matters.
  - **`time.ticks_ms()` wraps every `2**30` ms (~12.4 days)** — confirmed directly against the
    pinned v1.28.0 source: `py/mpconfig.h`'s `MICROPY_PY_TIME_TICKS_PERIOD` is
    `MP_SMALL_INT_POSITIVE_MASK + 1`, which resolves to `2**30` for `MICROPY_OBJ_REPR_A` (the rp2
    port's representation) on a 32-bit target per `py/smallint.h`. `time.ticks_diff(a, b)` is
    correct for any true elapsed time under `2**29` ms (~6.2 days) regardless of whether the raw
    integers wrapped in between — every real `ticks_ms()`/`ticks_diff()` use site in `src/` (Step
    6's own audit, `tests/test_ticks_rollover.py`) is a short, bounded timeout loop well inside
    that window; a raw `now - t0` subtraction anywhere would not be. **`time.ticks_ms` (and every
    other `time` module attribute) cannot be monkeypatched in a test** — confirmed directly against
    `py/objmodule.c`: a builtin C module's globals dict is built via `MP_DEFINE_CONST_DICT`
    (`map.is_fixed = 1`), and the store-attribute path explicitly rejects writing to a fixed map for
    every module except `builtins` (which gets a dedicated override-dict special case via
    `MICROPY_CAN_OVERRIDE_BUILTINS`) — unlike a plain `.py`-sourced module (e.g.
    `tests/test_captive_dns.py`'s `captive_dns_module.DNSQuery = ...`), whose globals dict is an
    ordinary, mutable dict. Test rollover-sensitive logic with synthetic ticks-space integers built
    from `time.ticks_add()`/passed straight to `time.ticks_diff()`, not by trying to control what a
    live `time.ticks_ms()` call returns.
  - **This project's own MicroPython Unix-port "standard" test rig has a much larger
    `ticks_ms()` period than real RP2040 hardware, and cannot empirically exercise the real
    rollover boundary.** `MICROPY_PY_TIME_TICKS_PERIOD` resolves to `2**62` on the Unix port's
    64-bit host word versus `2**30` on rp2's 32-bit one — the same shared formula
    (`MP_SMALL_INT_POSITIVE_MASK + 1`), parametric on word size, not two different
    implementations. `tests/test_ticks_rollover.py` proves `ticks_diff()`/`ticks_add()`'s wraparound
    math is correct at *this test rig's own* period boundary; the RP2040-specific `2**30` boundary
    can only be verified by code identity (one shared, period-parametric C implementation), never by
    a test that actually rolls over the value under the Unix-port interpreter.
  - **`globals()` does not preserve a module's own top-level `def`/statement order on this
    interpreter** — confirmed directly (a test file's own `test_*` functions ran in a different
    order than written). Any test file that starts a background task from one `test_*` function must
    keep an explicit reference to it and cancel it in its own `finally`, never relying on file
    position (e.g. "the last test in the file") for cleanup ordering.
  - **Calling `asyncio.run()` from inside a coroutine that is already running inside another
    `asyncio.run()` call segfaults the real interpreter outright**, rather than raising the clean
    error CPython's own reentrancy guard would give — confirmed directly (a real interpreter crash,
    not a Python-level exception), while writing `tests/test_digital_twin_sensortask_integration.py`/
    `tests/test_digital_twin_run_wozi_integration.py`. `await` directly instead once already inside
    an async context; never nest a second `asyncio.run()` call.
  - **`await` inside a comprehension is a `SyntaxError` on MicroPython** (`'await' outside
    function`, confirmed directly), unlike CPython. Use a plain `for` loop to build a dict/list from
    a sequence of `await`ed calls instead — e.g. `src/asy_webserver_service.py`'s settings/status
    aggregation methods all do this rather than a dict/list comprehension.
  - **`asyncio.TimeoutError` is a plain `Exception`, not an `OSError` subclass** — confirmed directly
    against the pinned v1.28.0 `extmod/asyncio/core.py` source (`class TimeoutError(Exception):
    pass`, immediately next to `class CancelledError(BaseException): pass`). A timeout raised by
    `asyncio.wait_for()` therefore is **not** caught by an `except OSError:` clause and is unrelated
    to `errno`/`MUTED_SOCKET_ERRORS`-style socket-error filtering — catch it with its own
    `except asyncio.TimeoutError:` (or a broader `except Exception:`) arm, distinct from any
    `OSError` handling in the same call site. `src/asy_webserver_service.py`'s `_serve()`/
    `_TimeoutStreamProxy` is the real example of code that needs both arms.
- **Always check current MicroPython and Microdot documentation before asserting how an API
  behaves** — do not rely on training-data memory for either. This has already caught real
  discrepancies once; treat it as a standing requirement for every session, not a one-time step.
- **Whenever the pinned MicroPython version changes (and periodically otherwise), re-check every
  MicroPython-facing code construct against the current pinned version's own source, the current
  rp2 port documentation, and MicroPython developer-forum/issue-tracker findings** — not just "is
  this still correct," but specifically "is there now a newer/better/more-complete way to do this
  that a stale construct is missing out on." Examples of the kind of thing this is meant to catch:
  a newly widened set of types accepted by `micropython.const()`, or real `asyncio`-level
  timeout/cancellation support being added to something that previously had none (e.g.
  `socket.getaddrinfo()` — see F.2 below for its current
  can't-be-timeout-wrapped status, which is exactly the kind of fact a version bump could change
  and silently invalidate). This is a standing practice, not a one-time pass — repeat it every time
  `toolchain/versions.toml`'s MicroPython `ref` moves.

## F.2 Blocking calls: the wedged-bus backstop, and what can/can't be timeout-wrapped

**For a genuinely wedged I2C bus/sensor (e.g. SCD30 hanging mid-transaction), the hardware
watchdog is the accepted backstop, not a software fix to chase.** MicroPython's cooperative
scheduler can't preempt a synchronous `machine.I2C` call already in progress, so an asyncio-level
timeout can't interrupt it either way. This is settled — don't re-propose an I2C-level timeout
mechanism. **`socket.getaddrinfo()` turned out to belong in this same "can't be timeout-wrapped"
bucket, not the "genuinely can" one** — confirmed against real MicroPython issue tracker reports
(micropython#18797, micropython#8326, micropython-lib#1078): it's a raw synchronous call with no
coroutine boundary for `asyncio.wait_for()` (or any asyncio-level timeout) to attach to, the same
preemption gap as a wedged `machine.I2C` transaction. This is now moot for DNS specifically —
`src/asy_ntp_client.py` no longer calls `socket.getaddrinfo()` at all; `src/asy_dns_client.py`
resolves hostnames with its own non-blocking UDP-based resolver instead (see its own module
docstring and BACKLOG.md). Calls that genuinely *can* be timeout-wrapped from within the asyncio
loop — FRAM SPI transactions, `src/asy_udp_socket.py`'s own `select.poll`-driven
`ready()`/`write_and_recvfrom(timeout_ms=..., tries=...)` — should standardize on one consistent
timeout/cancellation mechanism; re-check any new blocking-call candidate against this same
"does it have a coroutine boundary to attach a timeout to" question rather than assuming.

**Don't wrap every `asyncio` primitive call (`asyncio.sleep()`, `Lock.acquire()`, etc.) in
`try`/`except` against a theoretical internal `MemoryError` as a blanket policy** — overkill and
outside this project's own standard. Only worth closing when a concrete, non-hypothetical threat
exists in a specific context (a real caller-supplied value reaching an unguarded
comparison/construct), not just "any `await` could theoretically raise."

**Hot-unplug/replug I2C recovery is two-tier by design, confirmed directly against the code (not
assumed) — task-death-and-respawn is sufficient, but not by itself; it's one half of a mechanism
whose other half is the watchdog backstop above.** Each `*_Reader`'s own `read_loop()` calls its
`_init_<sensor>()` fresh on every task (re)start (both the first start and every supervisor
respawn via `system_service.py`'s `start_and_check_tasks()`), which calls the low-level driver's
own `setup()` - `BMP3xx_I2C.setup()`/`SCD30_I2C.setup()` both re-probe the bus and send a real
device-level soft-reset command (datasheet-documented `CMD`/`D304` opcodes); `SGP40_I2C.setup()`
re-probes and re-verifies via a serial-number read + self-test round-trip (no dedicated reset
opcode exists for this chip). This **does** fully recover a clean unplug/replug (device
power-cycles itself, comes back, responds to the next probe+reset) or a device stuck in a bad
internal state - genuine device-level faults. What it does **not** do is reconstruct the
underlying `machine.I2C` peripheral object itself (constructed once, inside `src/sensortask_wozi.py`'s
`build_system()`) - only a full reboot replays that construction (see A.4's
"FRAM chunk determinism rule" for the same "full reboot replays module-level construction from
scratch" fact used there). For a **bus-level** fault (SDA/SCL physically wedged mid-transaction,
not just a device gone quiet) a respawn's own probe call can itself hang/repeatedly fail the same
way any other wedged transaction does - but this is where the two tiers connect, not a gap:
`start_and_check_tasks()` increments `task_errors` on every respawn and stops feeding the watchdog
once `task_errors > _TASK_FAIL_MAX`, so repeated respawn failures already escalate to watchdog
starvation on their own, without any dedicated bus-recovery code - the resulting hardware reset is
what actually reconstructs `machine.I2C` from scratch. Task respawn therefore only ever needs to
handle the device-level case; the bus-level case was never its job in the first place, consistent
with the wedged-bus policy stated above.

## F.3 Long-blocking operations must not stall timing-sensitive work

Any new code that blocks the event loop for a noticeable time must not do so while timing-sensitive
work like the Neopixel animation needs to run — either avoid the block, or coordinate so
timing-sensitive code runs before/around it. This is a standing design principle for all new code,
not tied to any one past case. **The `get_long_block_lock()` shared-lock mechanism itself has been
retired** — its one real user, `socket.getaddrinfo()`, was replaced by `src/asy_dns_client.py`'s
non-blocking resolver (see F.2 above and BACKLOG.md), so there is no longer a long-blocking network
call in this codebase to coordinate against Neopixel timing in the first place.
`asy_ntp_client.py`/`src/asy_neopixel_driver.py`/`src/asy_notification_service.py` (the promoted
split of the former `neopixel_signal.py` — see A.4 above) no longer reference the lock at all. If
new code reintroduces a genuinely long blocking call, a coordination mechanism would need to be
designed fresh — don't assume the old lock still exists or try to resurrect/reuse it.

## F.4 Vendor-derived code: two opposite policies by vendor, not one blanket rule

Two vendors' code is currently vendored into this project, under **opposite** editing policies —
"vendor-derived" alone doesn't imply either one, so check which vendor before assuming. Each
file's own SPDX header carries its specific attribution; `THIRD_PARTY_LICENSES.md` at the repo
root is the single place all of it is also listed together.

- **Adafruit-derived driver code is fair game to restructure/rewrite (keeping attribution)** —
  unlike `python/CommonDrivers/microdot.py`/`ext/microdot.py`, which stay hands-off/vendored (see
  A.5 above).
- **Sensirion-derived reference-algorithm ports stay literal, the opposite of the Adafruit
  policy.** `voc_algorithm.py` (`VOCAlgorithm`) is a direct, deliberate port of Sensirion's
  fixed-point reference implementation (`embedded-sgp`'s VOC algorithm, cited in C.11 point 7)
  — its internal naming traces the original C source 1:1 (e.g.
  `_vocalgorithm__mean_variance_estimator___calculate_gamma`) on purpose, so that this file stays
  diffable against Sensirion's own reference if it's ever updated. Don't restructure/rename/
  "clean up" this file's internals the way Adafruit-derived code is fair game for — a genuine bug
  fix or a real behavior-preserving optimization (see D.8) is still in scope, the same as for any
  other file going through Part D's checklist; a stylistic rewrite for idiomaticity is not.

---

# Part G — Shared Pattern & Primitive Reuse

Where D.10 states the general principle ("give related functions/classes the same shape; check how
comparable code elsewhere already does this"), this Part is its concrete, checkable instance: a
living catalog of the actual shared primitives this project has already established, plus the
discovery procedure every new function/module/endpoint must run *before* being written, not after.
Cross-cutting by design — it applies to `src/`, `js/`/`tests_js/` (the website, Part H), and any
future layer this project grows, not just Python's `src/` the way Part D is scoped.

## G.0 What this Part prevents

A freshly-invented, locally-plausible solution to a problem this project has already solved
elsewhere is a correctness risk, not just a style inconsistency: an established shared primitive
typically encodes edge cases (type coercion, NaN/±inf handling, error-shape conventions, boundary
inclusivity) that a fresh reimplementation easily misses or narrows. Each independent
reimplementation is a separate place that gap can hide, and each one only surfaces when a later
review happens to compare it against the primitive it should have used — strictly more expensive
than checking G.2's catalog before writing the new code in the first place. Reuse is therefore the
default; a new primitive is what needs justifying, not the other way around.

## G.1 The rule

- [ ] Before writing a new function, method, module, or endpoint, identify what *kind* of problem
      it solves — not its specific field names or business logic, its *shape*: a numeric value
      needing type/range validation, a caller-supplied callback that could misbehave, a REST
      response envelope, a piece of mutable state shared across tasks, a per-module error/event
      log, a background task/timer registration, a config-file-backed setting, and so on.
- [ ] Search this Part's catalog (G.2) first, then the wider codebase, for an existing primitive
      that already solves that *kind* of problem — not just within the file being edited (D.10
      already requires that), across `src/` as a whole, and across `js/` too when the new code has
      a website-facing counterpart. This is a search to actually perform, not a rhetorical
      question — grep for the shape (e.g. a `FieldSchema`-like tuple, a `try/except` around an
      awaited caller-supplied callable, a hand-built `{"res": ...}`-shaped dict) before concluding
      nothing already exists.
- [ ] If a matching primitive exists: use it directly. Import it, construct the right
      tuple/record/argument shape it expects, call it — never reimplement any part of what it
      already does, even a version that looks locally simpler for this one call site. A simpler
      *inline* version is exactly the shape of mistake G.0 describes.
- [ ] If no primitive covers this exact *kind* of problem, but a comparable one already exists for
      a structurally similar problem (e.g. `_PAUSE_TIME_FIELD`'s synthetic-record pattern, built for
      a scalar dispatch-only field, generalizes directly to `lightCmdLED`'s per-subfield case), model
      the new code on that existing shape explicitly — cite it in a comment — rather than designing
      a fresh shape from first principles.
- [ ] Only once the above turn up nothing to reuse or model on, design something new. If the new
      thing is plausibly going to recur elsewhere (a second, third call site would want the same
      shape), add it to G.2's catalog in the same change that introduces it — don't leave that for
      a future retrospective audit to notice and backfill.
- [ ] When the new code has both a `src/` (or other backend) side and a `js/` (website) side, the
      two must encode the *identical* policy, written or updated together in the same change — see
      G.2's own "cross-language mirror" entry. Shipping one side now and "the other later" is
      exactly how a real policy gap survives into a merged PR; there is no such thing as a
      backend-only or frontend-only validation/coercion policy change in this project.

## G.2 Known reusable primitives (living catalog — extend whenever a new one is established)

- [ ] **Numeric type/range validation & coercion** — `config_manager.py`'s `type_or_range_error()`
      (+ `coerce_numeric()`, which it now calls internally). The canonical way to validate/coerce
      *any* int/float value against declared bounds, whether the value is genuinely schema-backed
      (a real `ConfigSchema` tuple, e.g. any driver's `_VAL_*` constants) or dispatch-only (a
      synthetic `FieldSchema` record built just for this check — `asy_webserver_service.py`'s
      `_PAUSE_TIME_FIELD`, `sensortask_wozi.py`'s `_FIELD_LED_R`/`_FIELD_LED_G`/`_FIELD_LED_B`/
      `_FIELD_LED_T`). Never hand-roll a bespoke `int()`/`float()` cast, a manual `min <= x <= max`
      comparison, or a standalone `coerce_numeric()` call with no accompanying range check for any
      new numeric field, dispatch-only or not — construct a `FieldSchema` tuple (real or synthetic)
      and call `type_or_range_error()` against it instead.
- [ ] **Caller-supplied callback dispatch guarding** — `asy_webserver_service.py`'s
      `_dispatch_system_cmd()`/`_dispatch_notification_led()`/`_dispatch_notification_pause()`
      three-part shape: validate the payload first (type/range via the primitive above, or an
      allowed-value check), `try/await` the caller-supplied callback, `except Exception` →
      `self.pr.err_s(...)` with a dedicated errno → return `"Failed"`. Every new dispatch-only PUT
      action follows this exact shape; a bespoke try/except around a callback invocation is a sign
      this primitive wasn't checked first.
- [ ] **REST response envelope construction** — `api_response.py`'s `make_response()` is the only
      way to build a `{"res", "code", "descr", "result"}` envelope. Never hand-build this dict
      shape inline, even for a one-off error path.
- [ ] **Task-scoped mutable state shared across coroutines** — `base_classes.py`'s
      `Lockable`/`LockedCounter`/`LockedFlag`/`LockedValue`. Any new piece of state that's written
      from one task and read from another (or vice versa) uses one of these, not a bare
      module-level variable plus an ad hoc `asyncio.Lock()`.
- [ ] **Per-module logging/error-history** — `print_log.py`'s `make_logger()`/`PrintLog`/
      `PrintLogHistory`/`PrintLogHistoryStore`. Every module that logs events/warnings/errors or
      exposes an error counter to `/status` (SPECIFICATION.md A.8) goes through this, constructed
      via `make_logger()` — never a bespoke `print()`-based or hand-rolled counter/history
      mechanism.
- [ ] **Driver layering/naming/config-schema/error-handling/concurrency/timer shape** — Part C in
      full is this same cross-cutting-reuse principle already applied, in depth, to one specific
      *kind* of module (a sensor driver) — read it before writing a new driver rather than treating
      this Part as a replacement for it. Part C and this Part are complementary, not overlapping:
      Part C is the deep spec for one module *kind*; this Part is the general discovery procedure
      plus the catalog of primitives that cut across every kind.
- [ ] **Cross-language mirror: `js/` must encode the same policy `src/` enforces for anything it
      simulates.** `js/mock-server.js` (SPECIFICATION.md's website effort) is not "a JS server that
      seems reasonable" — every validation/coercion/dispatch rule it implements must match the real
      `src/` endpoint it stands in for, field for field, bound for bound. This is D.10's
      within-project consistency principle applied across a language boundary: a `src/`-side policy
      change and its `js/` mirror are one change, not two, and neither side is ever "done" while the
      other still reflects the old behavior.

## G.3 Re-validating the existing project against this Part

- [ ] Whenever a new file lands in `src/` (already required by CLAUDE.md's own bird's-eye-scan
      hard rule — this Part's catalog is now explicitly part of what that scan checks, alongside
      Part D's checklist) or in `js/`, grep the whole of `src/` (and `js/` for a website-facing
      change) for the *shape* of each G.2 primitive's problem, not just its name — a raw
      `int(`/`float(` cast on a value that then gets compared against literal bounds inline; a
      `try/except Exception` wrapping an `await` of a caller-supplied callable that doesn't end in
      `self.pr.err_s(...)` + a `"Failed"`-shaped return; a dict literal containing `"res"`/`"code"`
      keys built by hand instead of via `make_response()`; a plain module-level variable mutated
      from more than one coroutine with no `Lockable`-family wrapper; a per-module log/error/event
      mechanism that isn't `make_logger()`-based.
- [ ] Each such finding is a candidate migration to the matching G.2 primitive, not something to
      "leave as a known quirk" — flag it the same way D.10's own last bullet already requires for a
      plain API-shape mismatch, then discuss before changing (this Part doesn't relax D.1's
      "flag, don't silently change" convention for anything behavior-relevant).
- [ ] This is a periodic, ongoing check across the whole project, the same standing cadence D.10
      already establishes for general API-shape consistency — not a one-time pass to run once and
      consider done. Re-run it whenever G.2 gains a new catalog entry too, since a primitive named
      today may have earlier, still-unmigrated instances of its exact problem sitting elsewhere in
      the codebase from before it existed.

---

# Part H — Website (JS/HTML/CSS) Architecture

## H.1 Purpose and design constraints

The website is the sensor station's browser-facing UI: show current measurement values, show
current configuration, set configuration, issue commands, and show system/error state and history.
Every REST endpoint's functionality must be reachable somewhere in the GUI — not necessarily a
dedicated API-browser page, just reachable.

Standing design constraints, all currently met:

- No boilerplate — small HTML skeleton(s) only; look/content is generated dynamically by JS from a
  per-device definitions file (H.5).
- Same skeleton/JS for every device — `js/render.js`/`js/nav.js` contain zero device-specific
  branching (H.4's "per-device page-scheme mechanism" row).
- Full REST API coverage retained, nothing dropped versus the legacy site.
- Stays small, lean, fully self-contained — no external runtime dependencies.
- Stable and good-looking on major mobile/desktop browsers, light and dark schemes (H.7's
  cross-browser coverage; dark mode is automatic-only, via `prefers-color-scheme`, no manual
  toggle/stored preference — CSS custom-property tokens on `:root`, redefined under
  `@media (prefers-color-scheme: dark)` in `html/style.css`).
- Modern nav (hamburger/drawer menu) replacing the legacy bottom link list.
- Build process: gzip each file individually at highest compression → wrap with `freezefs` →
  include in the cross-compile/frozen-bytecode build → mount on startup → serve via Microdot as
  gzip-compressed HTML (Part A.9).

**Predecessor**: `html_raw/{general,arzi,dev,wozi}` is the legacy, still-deployed per-device site
(four hand-written pages per device, cross-linked via a bottom `.links` bar, targeting the legacy
`/sensors/status`, `/sensors/config`, `/sensors/cmd`, `/net/config`, `/net/cmd`, `/led/cmd`,
`/led/config`, `/system/cmd`, `/system/status` REST shape — a PUT-with-`cmd`-envelope, `Led`-prefixed
convention that predates `src/asy_webserver_service.py`, see Part A.8). The website described in
this Part targets the refactored backend's REST shape from the start, not the legacy one; it is not
a reskin of `html_raw/`. `html_stub/` (Part A.9) remains a separate, deliberately placeholder-shaped
stand-in used by the generic frozen-HTML pipeline's own tests, independent of both.

## H.2 Folder structure and module map

New source lives in top-level siblings of `src/`/`tests/`, matching the repo's existing flat
convention:

```
html/               Hand-written HTML skeleton(s) + CSS - the website source
html/definitions/    Per-device definitions.json (schemaVersion/device/sections - see H.5) - shipped,
                     frozen alongside html/ by the build pipeline (scripts/build_website.sh)
js/                  Hand-written ES module JS source (poll-manager, mock backend, definitions
                     loader/validator, generic renderer, templates, nav) - see H.8
tests_js/            JS unit tests (Vitest, see H.8)
mockdata/            Prototype-only mock backend fixtures - NOT shipped, NOT part of the frozen-HTML
                     pipeline; consumed only by js/mock-server.js for local viewing without a real
                     backend/digital-twin
```

`package.json`/`package-lock.json` at repo root (dev-tooling only, `node_modules/` gitignored)
mirror `pyproject.toml`'s role: shipped code stays hand-written plain files, never restructured into
a build/bundle output. `npm run preview` serves the repo root via `python3 -m http.server 8000` —
open `http://localhost:8000/html/index.html?device=wozi` (or `?device=dev`) to click through the
live prototype locally, against `js/mock-server.js`'s fake backend.

**JS modules**: `app.js` (**prototype-only** entry point: mock fetch, `?device=` switch,
dev-server-relative paths — never shipped), `main.js` (the **real production** entry point — no
mock install, single build-fixed device via a plain `definitions.json` fetch, no `?device=`
branching; staged as `app.js` in the real build — see below), `definitions.js` (loader + strict
validator + JSDoc type definitions for the whole schema, no DOM code), `field-format.js` (pure
field-value formatting, no DOM dependency — split out of `templates.js` so Node-context test
harnesses can reuse it without pulling in DOM types, see H.8.1), `render.js` (section/group/field
controller — fetch/validate/submit logic, delegates all DOM building to `templates.js`),
`templates.js` (the DOM/markup-building layer — owns every element/class/order choice, see H.3),
`nav.js` (drawer wiring), `poll-manager.js` (single-flight request queue + shared fetch-timeout
helper), `mock-server.js` (**prototype-only** fetch-intercepting fake backend, answers the same six
REST paths/shapes A.8 documents — a placeholder for a real digital-twin backend, never shipped).

**`scripts/build_website.sh <device> [output_path]`** stages exactly one device's real site
(matching `html/definitions/<device>.json`) into a temp dir, then calls `build_frozen_html.sh` via
`HTML_SRC_DIRS`: `html/index.html` (with `html/style.css` and the device's own `definitions.json`
inlined directly into it — see H.7), the production `js/` module set concatenated into one bundled
`js/app.js` (H.7), and `js/main.js` renamed to `app.js` within that bundle's role. `js/mock-server.js`
and `js/app.js` (the prototype entry) are never staged. Staging the production entry point under the
name `app.js` means `html/index.html`'s one `<script type="module">` tag
(`import { startApp } from "../js/app.js";`) never needs a build-time text rewrite — that one import
path resolves identically in `npm run preview` (to the separate prototype `js/app.js`) and in a real
build (to the staged bundle), since relative-URL resolution keys off the document's own URL in both
cases. `build_website.sh`'s file lists are cross-checked against `html/`'s and `js/`'s real directory
contents by `tests_scripts/test_build_website_sh.py`, so a file added to either later fails the
suite instead of silently shipping or silently staying unshipped.

**Splitting a module**: `scripts/build_website.sh`'s bundler strips local `import` lines but never
strips `export` lines — two production files that both `export` the same name would collide into a
duplicate-export `SyntaxError` once concatenated. A module split out for reuse (like
`field-format.js`) must therefore never be *re-exported* by another production file; every importer
imports it directly.

**`html/index.html`'s inline bootstrap `<script type="module">`** cannot be extracted into its own
`js/` file for the reason above (it must keep importing the literal path `"../js/app.js"`, which
only resolves correctly because it is never rewritten). ESLint still covers it in place —
`eslint-plugin-html` (wired into `eslint.config.js`'s `html/**/*.html` block) parses and lints the
inline script with the same rules as every other browser JS file; `npm run lint` includes `html/`
accordingly. `tsc`'s JSDoc-based type-checking has no equivalent mechanism for inline `<script>`
blocks and does not cover it — accepted, since the inline script is a thin, low-logic bootstrap
(element lookups plus one `startApp(...)` call) rather than a place non-trivial type errors are
likely to hide.

## H.3 Layering: visual vs. mechanics (standing requirement)

The REST API and overall concept are expected to stay stable for a long time; the visual design is
expected to be revisited — restyled, reordered, regrouped — independently of that, more than once.
**A purely visual/layout redesign must never require editing data-fetching, validation, submission,
or poll-coordination code.**

- **Visual layer** — owns colors, spacing, typography, dark-mode tokens (`html/style.css`) **and**
  DOM structure/order/nesting/CSS-class choices (`js/templates.js`). `js/templates.js` also owns any
  interactivity that's purely cosmetic and never touches the network or app state — a toggle button
  flipping its own On/Off label, an errcount rollup expanding/collapsing its own filtered module
  list. A redesign touches these two files (plus, for a schema/labeling change, the
  `definitions.json` content itself — H.5) and nothing else.
- **Mechanics layer** — owns data fetching, polling coordination, input validation, PUT submission,
  and anything that calls the REST API or the poll-manager: `js/poll-manager.js`,
  `js/mock-server.js`, `js/definitions.js` (pure — no DOM code at all), and the non-presentational
  parts of `js/render.js`/`js/nav.js` (the controllers). None of these files build DOM elements,
  choose CSS classes, or decide element order/nesting.

**The contract between them**: controllers never reach into a template's internals by structure (no
"third child of the second div") — only by the `data-*` attributes and CSS classes the templates
already expose, which is the one thing a redesign must keep stable (renaming a hook needs a matching
one-line change on the controller side, the same way renaming a REST field needs a matching change
in `definitions.json`):

| Hook | Set by (`js/templates.js`) | Read by (controller) |
|---|---|---|
| `[data-field-key]` | every field's input/select/toggle-button/readonly span | `render.js` collects submitted values, updates readonly text/current-value captions on poll |
| `[data-sub-field-key]` | a composite field's per-subfield input | `render.js` collects the composite's nested PUT body |
| `[data-current-value-for]` | a writable field's "Current value: …" caption (number/string fields only) | `render.js` refreshes it after a poll/Apply |
| `[data-group-key]` | a field-group's card (both `buildFieldGroupCard()` and `buildErrcountGroup()` set it themselves) | `render.js` locates the card to re-render/restyle |
| `[data-field-wrapper-key]` | each field's own wrapper (distinct from `[data-field-key]`, which must keep pointing at the control itself) | `render.js` colors each field's own per-result outcome independently of the group card's own status |
| `[data-apply-status]` | *(unset by templates.js; only ever written by the controller)* | CSS alone decides what each status value looks like (`html/style.css`'s `[data-apply-status="…"]` rules), on both the group card and each field wrapper |
| `.apply-button` | the submit button | `render.js` attaches the real (networked) click handler |
| `.errcount-rollup .action-button` ("Show flagged"/"Show all") | `buildErrcountGroup()`'s two filter buttons | *(no controller involvement — purely cosmetic expand/collapse, wired entirely inside `js/templates.js` itself)* |
| `[data-section-key]` | each nav-drawer link | `nav.js` attaches the section-select click handler |

Controllers only ever set the semantic `data-apply-status` value (`"valid"`/`"invalid"`/
`"unchanged"`/`"failed"`) — never a color, class, or style directly. What that status *looks like* is
entirely `html/style.css`'s decision.

**In-place refresh only ever touches a number/string field's caption.** `render.js`'s `paint()`
"existing card" branch (the one a background poll or a post-Apply `fetchOnce()` triggers) updates
`[data-current-value-for]` captions and readonly spans only — it never rewrites a toggle button's own
On/Off state or a `<select>`'s selected option. Proving a toggle/enum field's persisted value
actually round-tripped therefore needs a genuine full remount (a nav-drawer click — `main.js`'s
`selectSection()` always tears down and rebuilds, even for the already-active section), not an
in-place poll. The one deliberate exception to "hooks are `data-*` attributes": `buildSectionShell()`
returns `{grid, errorBanner}` directly to its one caller (`render.js`'s `renderSection()`) rather than
making the controller look `errorBanner` up by attribute — there's only ever one error banner per
rendered section, handed back at the exact point it's created, so a lookup hook would add indirection
with no reuse benefit; the controller still only ever touches it by toggling the `.hidden` utility
class and setting `.textContent`, never a color or custom style.

## H.4 Architecture decisions

| Topic | Current behavior | Rationale / notes |
|---|---|---|
| Page model | Single-page shell, JS-driven view switching | One HTML skeleton; hamburger/three-dot menu swaps sections via JS, no page reload. Makes the poll-manager's single-active-poll rule trivial to enforce globally. |
| Definitions file | One single JSON per device, fetched once | Covers nav, page/field labels, units, valid ranges, special values, etc. Concrete schema in H.5. |
| REST target | `src/asy_webserver_service.py` API (Part A.8) | Six endpoints (`/measurements`, `/sensors`, `/networking`, `/system`, `/status`, `/notification`), sparse-body PUT, no `cmd` envelope, no `Led`-prefixed fields. |
| Nav grouping | Mirrors the 6 REST endpoints 1:1 | Sections: Measurements, Sensors, Networking, System, Status, Notification. |
| History depth/pagination | Counts always visible; full history on demand; **no pagination/truncation** | Per-module error-count/last-error always shown. Clicking a module's error-count entry expands its full `history` array as-is — a realistic history depth stays well under 20 entries. History rides along in the same `/status` response (fetch-once-per-poll), not a separate paginated endpoint. |
| Poll coordination | One shared JS poll-manager module (single-flight queue) | Single source of truth for "is a request in flight." The measurements group and the status/settings group are never polled concurrently by design (a page only ever needs one or the other); if that ever becomes unavoidable, a new poll must wait until the pending request has resolved **and its connection has fully closed** before starting — the device has very few available sockets (H.7). Every fetch (recurring polls and one-time startup loads alike) goes through a shared `AbortController`-based timeout so nothing can hang forever. |
| API reachability | No dedicated API-browser page | Every endpoint's functionality just needs to be reachable somewhere in the ordinary GUI (satisfied by the nav-mirrors-endpoints decision above), not a Swagger-style reference/try-it tool. |
| Definitions validation | Strict — visible error state on mismatch | The JS checks the fetched definitions file's shape/version before rendering, including `pollGroup` (must be `"live"`/`"settings"`/`"none"`) and both poll-interval fields (must be a positive number) — a mismatch surfaces a visible error banner rather than silently rendering something broken or skipping unknown fields. |
| Landing page | Measurements page | Matches legacy's default landing page. |
| Card/nav visual treatment | Modernized flat cards; slide-in drawer nav | Cards: soft border/shadow (not legacy's flat grey fill), real light/dark tokens. Nav: a slide-in drawer opened by a hamburger button, listing the six section links plus the device name, no other global actions in it. |
| Rendering safety | Server-supplied text via `textContent` only, never `innerHTML` | Standing coding guideline for all JS — keeps the page XSS-safe by construction. |
| Numeric int/float coercion & validation | `config_manager.py`'s `type_or_range_error()`/`coerce_numeric()`, mirrored in `js/mock-server.js` | Canonical policy for every numeric field, schema-backed or dispatch-only alike — see Part A.8 (backend) and Part G (the reuse pattern this establishes for any new numeric field). A float-typed field's `definitions.json` entry sets `"float": true`. |
| Dispatch-only PUT fields | `SystemCmd`, `PauseTime`, `lightCmdLED`, `ResetErrors` — the complete set | None of these are persisted settings: each re-dispatches fresh on every submission (never reports `"Unchanged"`), and each has its own validation shape (H.6). `js/mock-server.js` excludes all four from its generic sparse-PUT persistence path. An enum field with no value matching the current GET-reflected state (true for every dispatch-only enum, since these are never returned by GET) renders with a blank placeholder option selected by default — never silently defaulting to the first real option — so an untouched Apply click submits nothing rather than an unintended command. |
| PUT-result coloring | 4-state vocabulary (`Valid`/`Unchanged`/`Invalid`/`Failed`), colored at two levels | Matches the real backend's own vocabulary (`base_classes.py`/`api_response.py`). Colored on the group card as a whole (worst status across the group — `Invalid`/`Failed` always outrank `Valid`/`Unchanged`; between the two non-problem outcomes, `Valid` outranks `Unchanged`) **and** on each individual field's own wrapper (only for fields actually present in the response's `result`; an untouched, sparse-omitted field keeps no stripe). A whole-request failure (network/communication error) marks every field in that submission `Failed` individually, not just the card border. |
| PUT/GET error handling | Every fetch treats a non-2xx status, a null body, or `res:"ERR"` as a whole-request failure, surfacing the server's own `descr` text | Applies uniformly to polls and submissions. A field the visitor submitted but that doesn't come back in the response's `result` is shown `"Failed"` (client-side defense; the matching server-side contract — a failing settings-group hook never silently drops fields either — is stated in H.6). A GET failure shows a per-section error banner without clearing the stale-but-still-useful data already on screen, clearing again on the next successful poll. `/status`'s own PUT (`ResetErrors`) never returns a per-field `result` at all — every submitted field there is marked `Valid` directly once a request-level failure has been ruled out, not run through the generic per-field reconciliation above. |
| Per-device page-scheme mechanism | The definitions file itself | `js/render.js`/`js/nav.js` contain zero device-specific branching — every card, field, and nav entry comes from the fetched `definitions.json`. All devices share the same `html/index.html` + `js/` tree, pointed at different definitions files. |
| Known accepted gap: empty-string fields | Cannot currently be set to an empty string via this UI, for any field | The sparse-PUT convention (a blank input means "untouched, omit from the body") makes an explicit empty-string submission structurally impossible — affects `PW`'s real "configure an open network" sentinel (`asy_wifi_service.py`'s `_VAL_PW`). Accepted as-is. |

**`js/mock-server.js` mirrors every real backend quirk it fakes, not just the happy path** — the
prototype-only mock backend is only useful for local development if it behaves like the real one,
including its edge cases. Confirmed instances: `/networking`'s `PW` field is masked as `"********"`
on every GET response (`_mask_pw()`'s overlay in `src/asy_wifi_service.py`, mirrored in
`handleGet()`); SCD30's `ForceCalRef` always reports `400` on GET regardless of what was applied (a
real sensor register limitation — see `src/asy_scd30_driver.py`'s own docstring); `ContMeas` and
`SGPResetVOC` are never reported by GET at all (both are command-only trigger fields — C.5.2.1 — with
no persisted value to read back). `js/mock-server.js` dispatches all of these separately from its
generic sparse-PUT/store-and-echo path used by every ordinary settings field, and `tests_js/
mock-server.test.js` covers each explicitly rather than relying on the generic PUT-matrix tests
(whose own categories — "resubmit ⇒ Unchanged", "valid value ⇒ reflected in the next GET" — don't
hold for any of these).

## H.5 Definitions JSON schema

One JSON file per device (`html/definitions/<device>.json`), shipped and frozen alongside `html/` by
the build pipeline (H.2). `js/definitions.js` documents this shape via JSDoc typedefs and strictly
validates it at load time (H.4's "Definitions validation" row).

- **Top level**: `{schemaVersion, device, landingSection, defaultPollIntervalMs, sections[]}`.
- **`section`**: mirrors one of the six REST endpoints — `key` matches the endpoint name,
  `rest: {get, put?}`, `pollGroup: "live"|"settings"|"none"` — and holds `groups[]`.
- **`group`**: normally a `FieldGroup` (`key`, `label`, optional `submit`/`submitLabel`, `fields[]`).
  Status's error section is instead the distinct `ErrcountGroup` (`kind: "errcount"`, `modules[]`),
  since its shape (per-module counter + optional history) doesn't fit the field-list model.
- **`FieldDef`**: a `kind` (`readonly | number | string | enum | toggle | composite`) plus
  kind-specific metadata (`min`/`max`, `minLength`/`maxLength`, `mask`, `options`, `specialValues`,
  `subFields`, `onLabel`/`offLabel`, `float`).
- See `html/definitions/wozi.json` and `html/definitions/dev.json` for two worked, real examples
  (wozi's SCD30/SGP40/BMP388 vs. dev's SCD30/SGP40/SHTC3/MPRLS/ISL29125 — deliberately different
  sensor sets, field kinds, and value ranges). `dev.json`'s SHTC3/MPRLS/ISL29125 entries are a
  projection from the same pattern every promoted sensor follows, not confirmed against real driver
  code — these sensors have no real driver under `src/` yet; resolves naturally once a future
  session promotes those drivers.

**Autogeneration is not yet built.** The definitions file is currently hand-written; a build-time
generator deriving it from tagged schema comments in the real `.py` source (before `mpy-cross` strips
comments) is a deferred future direction — see `BACKLOG.md`'s "Website definitions-file
autogeneration" entry for the worked grammar sketch this direction already has.

## H.6 Errcount (Status section) and dispatch-only field conventions

- **Errcount module list**: `{key, label}` per entry — one per registered module, plus each module's
  own `CFGMGR_<name>` config-store instance (except SCD30, which persists to the sensor's own NVM,
  not a `ConfigManager`, so it has no config-store error source), plus the webserver's own
  `WEBSERVER` entry — matching `asy_webserver_service.py`'s `_build_errcount()` shape exactly.
  Looked up directly in `/status`'s `errcount[key]` response at render time, no transformation beyond
  the key lookup.
- **History entry shape**: `{"num": <raw errno>, "type": "N"|"E"|"W"}` per slot, always a fixed
  `history_length`-long list (never shorter — a healthy module's history is all `"N"` placeholders,
  not an empty array). No per-entry timestamp anywhere in the system. `type` is never rendered as
  text — its only job is to color `num` (green/yellow/red for no-error/warning/error) via
  `data-err-type`, styled entirely by `html/style.css`.
- **Errcount UX**: rendered in the same `.card` shell every other field group uses. Starts fully
  collapsed to a rollup ("N modules with errors" / "M modules with warnings") plus two filter buttons
  ("Show flagged"/"Show all"); revealing a module row shows its history immediately, no further
  per-row click needed. Wired entirely inside `js/templates.js` (purely cosmetic expand/collapse, no
  controller/network involvement) — including preserving which filter state was showing across a
  live poll's card rebuild (`js/render.js`'s `paint()` re-applies the previously active filter button
  to the freshly built card).
- **Dispatch-only field semantics** — `SystemCmd`, `PauseTime`, `lightCmdLED` (r/g/b/t composite,
  bounds 0-255/0-255/0-255/0.5-60.0, matching legacy's own bounds exactly and rejecting — never
  clamping — a value outside them), `ResetErrors`: `"Invalid"` only for a structurally wrong payload
  (non-dict for `lightCmdLED`, not in the allowed set for `SystemCmd`, out of type/range for
  `PauseTime`); anything else wrong (missing/non-numeric/out-of-range subfield) reports `"Failed"`; a
  well-formed submission always reports `"Valid"`, including on an identical repeat (never
  `"Unchanged"` — these re-dispatch fresh every call). `js/mock-server.js` mirrors this exactly via
  `dispatchRangedAction()` (`PauseTime`) and `dispatchLightCmdLed()`, writing straight to each field's
  real destination state and never persisting into the generic settings store.
- **Server-side settings-group failure**: if a `SettingsGroup`'s post-write hook raises, every field
  that group actually attempted is reported `"Failed"` in the PUT response — never silently dropped —
  while the overall envelope still reports success (per-field detail carries the failure, matching
  every other endpoint's own convention of never failing the overall request for per-field detail).

## H.7 Digital twin integration

The website is wired into `digital_twin/` alongside every sensor/module that has a real REST/API
connection there — the same generalized "any new module joins the twin once it can complete a real,
observable chain" rule Part A.10 states for drivers and common modules, applied here to the website
itself. `scripts/run_digital_twin_ci.sh` (and therefore `digital-twin-e2e`'s CI job) and
`scripts/run_unix_port_integration.sh` build the real, production `wozi` website via
`scripts/build_website.sh wozi` — the twin serves the real site by default, for the one device
`src/` currently assembles, matching what real deployed hardware serves.
`scripts/build_frozen_html.sh`'s own `html_stub` default (Part A.9) is unchanged and still used
elsewhere (`scripts/test.sh`'s `test_frozen_html_integration.py` coverage of the generic pipeline).

**Build-chain integration proof, two layers**: `tests/test_website_build_integration.py` (a
MicroPython Unix-port integration test, mirroring `test_frozen_html_integration.py`) proves the
staged site mounts and serves correctly on its own — nested `js/*.js` paths, `definitions.json` at
the root, the real `main.js` content (not the prototype) at `/js/app.js`, every prototype-only path
404ing — without booting the full application. `tests/test_digital_twin_real_website_integration.py`
closes the remaining gap: neither that test nor `test_frozen_html_integration.py` boots the real
`sensortask_wozi.build_system()` object graph, so neither proves the real, *booted* system actually
serves the real website. This file pre-registers `sys.modules["frozen_html"]` to the real website
build before `import sensortask_wozi` runs (the same "check `sys.modules` before the filesystem"
import-resolution rule CPython uses too), boots the real object graph against `digital_twin/`'s
buses, and drives real HTTP at it.

**Living-integration checklist**: Part C.11 point 9 (the driver-promotion checklist) and
`digital_twin/README.md`'s "Adding a new chip fake" list both require updating
`html/definitions/<device>.json` for any device a new driver/module's fields should appear on,
whenever that module gains a live REST connection — same session as the digital-twin extension
itself, not deferred.

**Live-backend browser test**: `tests_js/live-backend.test.js` drives the real website's own JS (not
`js/mock-server.js`) in a real Chromium browser against a real, live-booted digital twin subprocess —
opens the real page, submits a real PUT through the real UI, asserts the backend's response reflects
in the UI. `tests_js/_live_twin_command.js` is a server-side Vitest Commands-API function
(`vitest.config.js`'s `test.browser.commands`) that spawns the twin subprocess and drives a second
real Playwright page (`context.newPage()`) at it directly — needed since Vitest's browser-mode `page`
object has no API for navigating to an external origin (`vitest-dev/vitest#7875`, open upstream).
`tests_js/live-backend-put-matrix.test.js` extends this to every real writable field in `wozi.json`
(the only device the twin ever boots as), verified both same-view (the caption/control right after
Apply) and via a full from-scratch remount (needed because only a number/string field's caption
self-refreshes in place — H.3's "in-place refresh" note).

**Connection-concurrency ceiling and mitigations**: the real rp2040/lwIP build has a hard ceiling of 5
simultaneously active TCP connections (`MEMP_NUM_TCP_PCB=5`, lwIP's own compile-time default, no
project override). A page load is kept well under that ceiling two ways, both at build time
(`scripts/build_website.sh`'s own "Bundling"/"Inlining" comments have the full mechanism):

- **Bundling**: the seven production JS modules are concatenated into one `js/app.js` bundle — no
  real bundler, a plain dependency-free text concatenation (`import`/`export` lines dropped/left
  as-is), safe specifically because every production `js/*.js` file uses only simple
  same-relative-path imports with no default exports, dynamic imports, re-exports, or cross-file
  naming collisions.
- **Inlining**: `html/style.css` and the device's own `definitions.json` are embedded directly into
  the staged `index.html` — a `<style>` block, and a `<script type="application/json">` element with
  every literal `<` escaped to `<` (since `<script>` is an HTML raw-text element that a literal
  `</script` substring inside the JSON would otherwise prematurely close).

A page load is 2 connections (`index.html` + `app.js`), down from up to ~9 before this.
`js/definitions.js`'s `loadDefinitions()` accepts an optional already-parsed DOM element and uses it
in preference to fetching, falling back to a real fetch identically to before whenever that element
is absent (always true in dev/preview mode, where `html/index.html` is never inlined).
`src/asy_webserver_service.py`'s `max_connections` is `4` (raised from an original `3`), one more
slot of the headroom the bundling/inlining above freed up under the same 5-PCB ceiling.

HTTP keep-alive/persistent connections are deliberately not implemented: vendored `ext/microdot.py`
always closes the connection after exactly one request by design (confirmed against its current
upstream `main` branch too, not just the pinned tag — no keep-alive support exists there either), and
this project's own hard rule never touches that file's behavior (CLAUDE.md's vendoring policy).
Persistent connections would have to be built entirely in application code around Microdot's own
request lifecycle, which proved fragile in practice; the bundling/inlining reduction above achieves
the same practical goal without touching Microdot's behavior at all. Raising the rp2 firmware's own
`MEMP_NUM_TCP_PCB` compile constant is a firmware-level change, out of scope for a website-only fix.

The `max_connections` ceiling only ever rejects a *new* arrival (silently, before any response is
written) — it never touches an already-open connection, and a stale one is reclaimed only by its own
per-call/outer-cap timeout. `tests/test_digital_twin_webserver_concurrency.py` covers this with
genuinely concurrent real-socket connections.

### Cross-browser coverage

Vitest's own browser mode is wired to a single provider (Playwright), which can only automate
Chromium-family browsers — it cannot drive a real, unpatched WebKit or Firefox at all.
`scripts/cross_browser_smoke.mjs` is a standalone (non-Vitest) script that closes this gap: it boots
the real digital twin and drives the real production website through **WebKitGTK** (real WebKit, via
`WebKitWebDriver`'s own W3C WebDriver server — installed by `apt`'s `webkit2gtk-driver`), **real
Firefox** (Gecko, via Mozilla's own `geckodriver` — installed from conda-forge via a standalone
`micromamba` binary, since Ubuntu's `firefox` apt package is a snap-only stub with no working snapd in
this project's CI/sandbox environments), and **real Microsoft Edge** (Chromium-family, installed from
Microsoft's own apt repo, driven the same way as Chromium via Playwright's `executablePath`) — plus
Playwright's own Chromium, included so every engine goes through the identical check. Each engine
runs at both a desktop-sized and a mobile-sized viewport: nav to the live site → open the nav drawer
→ go to Sensors → edit one field → Apply → confirm the real backend validated it and the UI reflects
it (both the `data-apply-status` attribute and the current-value caption, which updates via a
separate, slightly later GET round trip — `render.js`'s `onApplied()` → `fetchOnce()` — so a correct
check has to poll for both together, not just the former).

Deliberately narrow scope, not a second exhaustive PUT matrix: each real WebDriver round trip costs
low single-digit seconds, so replicating the full field-by-field matrix across three more engines
would cost many extra CI minutes for marginal confidence beyond what engine diversity alone already
buys. WebKit/Firefox have no device-emulation API over plain WebDriver (no touch synthesis, no mobile
UA) — their "mobile" viewport is a real window resize only, confirmed to still land under the site's
own 640px responsive breakpoint (`html/style.css`) but not an exact device match; Chromium/Edge get
Playwright's fuller `devices` preset emulation (real touch, exact device viewport, mobile UA).

`scripts/setup_cross_browser_toolchain.sh` installs all three non-Chromium-Playwright toolchains
(idempotent, safe to re-run) and is shared between CI (`web-cross-browser-smoke` job in
`.github/workflows/ci.yml`) and local dev. A missing engine binary is skipped with a clear message
rather than failing the whole script — CI always installs all three, so a skip there is itself the
bug to chase; a local run without the full toolchain just gets partial coverage.

Two process-hygiene gotchas worth keeping in mind for anything similar: (1) spawning
`WebKitWebDriver`/`geckodriver` via the `xvfb-run` wrapper script can leave both the driver process
and its own `Xvfb` still running after `SIGINT` is sent to the wrapper's PID alone — spawn `Xvfb`
directly instead and kill both processes explicitly. (2) reading an applied result immediately after
`data-apply-status` appears can occasionally read back the *previous* check's stale caption instead
of the one just applied, since the caption's own GET round trip can complete slightly after the PUT's
— poll for both together instead.

## H.8 CI / tooling stack

Mirrors Python's role split (ruff/mypy/pytest), not just "any linter/tester":

| Python role | JS/HTML/CSS equivalent | Notes |
|---|---|---|
| ruff (lint) | **ESLint** (flat config, `eslint.config.js`) | Beyond `eslint:recommended`: `array-callback-return`, `no-await-in-loop`, `no-constructor-return`, `no-duplicate-imports`, `no-promise-executor-return`, `no-self-compare`, `no-template-curly-in-string`, `no-unmodified-loop-condition`, `no-unreachable-loop`, `no-use-before-define`, `require-atomic-updates`. Covers `js/`, `tests_js/`, `scripts/*.mjs`, and (via `eslint-plugin-html`) the inline script in `html/index.html` — see H.2. |
| mypy (type-check) | **TypeScript `checkJS` mode** (`tsc --noEmit`) reading JSDoc annotations in plain `.js` | Pure dev-time checker, zero transpilation. Two separate invocations — `tsconfig.json` (browser context, DOM lib) and `tsconfig.node.json` (Node context, `@types/node` only, no DOM lib) — since a Node-context file (`tests_js/_live_twin_command.js`, `tests_js/_live_matrix_command.js`, `scripts/cross_browser_smoke.mjs`) and a browser-context file can't correctly share one `tsc` program's ambient globals (see H.8.1). |
| MicroPython Unix-port interpreter for tests (real environment, not CPython+stubs) | **Vitest in real-browser mode** (`@vitest/browser-playwright`'s `playwright()` provider, against real Chromium) | Deliberately not jsdom — same "real engine over a DOM/interpreter shim" principle Part E.1 argues for the Python side. `testTimeout: 20000` is an explicit hang-avoidance backstop, mirroring the Python side's own standing "hanging tests are never allowed" practice. |
| `scripts/test.sh --coverage` (non-gating) | `@vitest/coverage-v8` + non-gating `npm run test:coverage` | Report-only, no threshold enforced anywhere. |
| — | **html-validate** for `html/`'s skeleton(s); **Stylelint** for the CSS | Lightweight npm packages, no JVM dependency. |

**CI mechanism**: the single `.github/workflows/ci.yml` carries a `web-changes` `dorny/paths-filter`
gate job whose output feeds `if:` conditions on `web-lint-and-typecheck` (ESLint + `tsc --noEmit` +
html-validate + Stylelint) and `web-unit-tests` (Vitest browser mode) — deliberately not a second
workflow file with its own trigger-level `paths:` filter, which can leave a PR stuck on a required
status check that never fires because the whole workflow never triggered. Python CI keeps running
only against its existing paths; web CI runs only against `html/`, `js/`, `tests_js/`,
`scripts/*.mjs`, `mockdata/`, plus its own config files (`package.json`, ESLint/TS/Vitest/
html-validate/Stylelint configs, `.nvmrc`). Root `.nvmrc` pins the Node version, read by
`actions/setup-node`'s `node-version-file` in CI.

Manual local-trigger instructions for the whole web-CI tier live in README.md's "Website tooling
(JS/HTML/CSS)" section (`npm ci` + `npm run lint`/`typecheck`/`lint:html`/`lint:css`/`test`) — the
JS-side equivalent of that same README's "Code quality tooling" section for Python.

### H.8.1 JSDoc typedef imports across the browser/Node split

A JSDoc `@typedef {import("./x.js").Y}` reference pulls the *entire* referenced file into whichever
type-check program (`tsconfig.json`, browser context, or `tsconfig.node.json`, no `"dom"` lib) does
the importing, even when only one exported type is used — not just that type. A Node-context module
(e.g. a Vitest Commands-API file under `tests_js/`) that references a shape from a DOM-context module
(`js/definitions.js`, `js/templates.js`) this way inherits that module's own DOM-typed JSDoc too, and
fails to type-check on it. **Convention**: a Node-context module needing a shape from a DOM-context
one declares its own narrow, structural local typedef instead of importing the real one — a real
object satisfies it structurally either way. `js/field-format.js`'s own `FormattableField` typedef
(intersected with `Record<string, unknown>` so a real, wider object literal doesn't trip
excess-property checking at call sites) is the worked example.

**Testing an async DOM refresh** (live-backend browser tests, `tests_js/_live_matrix_command.js`):
poll for the exact expected rendered text/state, never a fixed sleep. A number/string field's
"Current value" caption refreshes via a real, separate async GET round-trip (`js/render.js`'s
`onApplied()` → `fetchOnce()`) after the click handler's own synchronous `data-apply-status` write —
a fixed delay can catch a still-in-flight *previous* case's caption instead of a real race. Poll the
DOM for the specific text a real GET response should produce (computed via `formatFieldValue()`) up
to a generous bounded timeout instead.
