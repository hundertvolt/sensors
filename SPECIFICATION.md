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
- **`BACKLOG.md`, `WIRING_CONTRACT.md` stay separate.** By their own stated nature they are not
  specifications: `BACKLOG.md` is active working memory (open questions, deferred work) that churns
  as items resolve; `WIRING_CONTRACT.md` is explicitly temporary, deleted once its purpose is
  served — until then it stays live and current, not frozen planning content. Its purpose outlived
  its original one-time framing: `src/sensortask_wozi.py` (Step 1 of `FINAL_WIRING_PLAN.md`'s
  five-step wiring effort) has already landed, but the document deliberately stays alive past that
  point since Steps 2-5 and Step 6 (added after the original five-step plan was scoped, its own
  dedicated session/branch alongside them) all build on the exact construction order/dependency
  graph it documents — see its own "Status update" section. Folding live churn or provisional
  planning content into a
  stable spec would immediately start recreating the scattering problem this document exists to fix.

**Where the source files went**: `DRIVER_SPEC.md`, `src/README.md`, `tests/README.md`, and
`toolchain/README.md` are now short stub files pointing here, kept so existing links/references
elsewhere in the repo still resolve to a real file; their full content lives in Parts B-E below.
`README.md` keeps its human-facing project description and the units-deployed table; its former
"Repository layout"/"Architecture at a glance"/"Refactor in progress"/"Building this project's
firmware" sections moved into Part A/B below, replaced there with a pointer. `AUDIT_PLAN.md`, the
master action list for the full `src/` audit this document's Parts C/D harmonization came out of,
followed the same temporary policy as `WIRING_CONTRACT.md` and was deleted once that audit closed
— everything permanent it settled is migrated here.

**Not every cross-reference throughout the repo's other docs (`BACKLOG.md`, `WIRING_CONTRACT.md`)
points directly here** — some still go through one of the stub files above, which resolve correctly
via that one extra hop. Worth rewriting to point here directly if the indirection itself becomes
annoying; not something this document tracks on its own.

## Table of contents

- **Part A — Repository & Architecture Overview**: repository layout, architecture at a glance,
  refactor status, the deep module-by-module architecture reference, the Microdot/REST layer
  contract, and datasheets.
- **Part B — Toolchain & Build**: the MicroPython/pico-sdk/picotool/cross-compiler installer, and
  building this project's own firmware.
- **Part C — Sensor Driver Architecture Specification**: the shared contract a new sensor driver
  follows (layering, naming, config schema, error handling, concurrency, timers, typing).
- **Part D — `src/` Production-Quality Checklist**: what "done" means for any file moving from
  `improved-quality/` into `src/`.
- **Part E — Testing & Coverage**: why/how unit tests run under a real MicroPython interpreter,
  the hardware-mocking boundary, and the coverage pipeline.
- **Part F — Platform Target & MicroPython Runtime Facts**: RP2040/MicroPython-1.26 specifics,
  gotchas, and the load-bearing constraints they impose on every driver/service in Parts C-E.

---

# Part A — Repository & Architecture Overview

## A.1 Repository layout

```
datasheets/              Real datasheet PDFs for the chips this codebase drives - see CLAUDE.md
  bmp3xx/, fram/, pico w/, scd30/, sgp40/
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
src/                     Files moved out of improved-quality/ once fully reviewed/tested - see
                          Part D below for the promotion checklist
SPECIFICATION.md         This file - the central specification (repo root)
DRIVER_SPEC.md           Stub -> Part C below: shared sensor driver architecture/interface spec
tests/                   Unit tests for src/, run under a real MicroPython interpreter - see
                          Part E below
toolchain/               MicroPython/pico-sdk/picotool build-environment installer
  versions.toml             single source of truth for the target MicroPython version - see
                            Part B below for how everything else derives from it
  setup_toolchain.py        `setup`/`test` - builds RP2040 firmware and the MicroPython Unix port (for tests/)
build-{arzi,dev,neu,wozi}.sh   per-device build scripts
update_and_install.txt   handwritten toolchain setup notes (MicroPython/pico-sdk/picotool)
pyproject.toml           dev-tooling config (ruff/mypy/pytest/uv) - see CLAUDE.md's "Code quality tooling"
scripts/                 lint.sh / typecheck.sh / test.sh - manual code-quality check runners
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
  handler in `improved-quality/sensortask-wozi.py` (`improved-quality/api_helpers.py`'s own copy of
  the old pipeline has been removed entirely, once that file was fully migrated off it — see
  BACKLOG.md): `base_classes.py`'s `_set_dict_cfg()` gives every `SensorReaderConfig` a generic,
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

The `improved-quality/` refactor (see repository layout above) isn't just a cleanup — it targets
the most recent *stable* MicroPython/pico-sdk/picotool/Microdot releases, expands error handling
and bus/sensor fault recovery considerably beyond what's described above, and adds unit tests,
mypy, ruff, and a CI pipeline (including a real firmware build, eventually — the current pipeline
covers lint/type-check/unit-tests only) that don't exist for the current codebase at all. Files
move to `src/` once fully reviewed and tested against that bar — see `src/` and `tests/` in the
repository layout above, and Part D/Part E below. See BACKLOG.md's "Refactor targets not yet done"
for what's still open.

## A.4 Architecture — deep reference

The condensed version is A.2 above. Key modules if you need to go deeper (folded in from
`CLAUDE.md`'s "Architecture reference" section):

- `python/CommonDrivers/api_helpers.py` — generic REST validate → apply-to-sensor → persist
  pipeline, repeated by hand for every endpoint (no shared schema/route generation — see
  BACKLOG.md's config-duplication item).
- `python/CommonDrivers/async_connect.py` — WiFi STA + AP/hotspot fallback + NTP client with
  manual CET/CEST DST math (`cettime()`); exposes `get_long_block_lock()`, a shared lock
  serializing `socket.getaddrinfo()` against Neopixel animation. This is the deployed, pre-refactor
  version only — `improved-quality/`/`src/` split this into `asy_wifi_service.py`/
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
  `__init__`; a full reboot replays `improved-quality/sensortask-wozi.py`'s entire module-level
  construction sequence from scratch, and every current FRAM-chunk-owning construction (`sysfunct`,
  `sgp_reader`'s VOC-backup chunk, `pixel`, `notify_service`) is an unconditional top-level
  statement, confirmed by direct reading, not assumption. Before adding any *new* FRAM-backed class
  (a new driver, or a currently-in-memory-only logger — e.g. a `CFGMGR_*` or `"DNSSRV"` logger ever
  becoming FRAM-backed), prove single, deterministic construction first, not after.
  **Every deliberate system reset already pauses FRAM first, confirmed directly** (found during a
  BACKLOG.md scan for settled facts sitting in working memory): `system_service.py`'s `_reboot()`
  (backing both `reboot_system()`/`reboot_bootloader()`) calls `self.storage_pause(True)` before
  arming the delayed reset timer, and before the `_force_watchdog_starve` fallback too — confirmed
  via grep that `machine.reset()`/`machine.bootloader()`/`WDT()` have no other call site anywhere
  in `src/` or `improved-quality/`. Whether the actual wait margin is sufficient for FRAM's own
  in-flight transaction time, and keeping this invariant preserved as more reset call sites are
  added, are still open — see BACKLOG.md's "Every deliberate system reset..." item.
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
- **SGP40's VOC index is a deviation-from-learned-baseline number, not an absolute-concentration
  one — confirmed directly against `voc_algorithm.py`'s real Sensirion Gas Index Algorithm port
  while calibrating a real threshold-crossing integration test (see
  `tests/test_notification_sgp40_integration.py`'s own module docstring for the full derivation).**
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
- **`improved-quality/neopixel_signal.py` (LED hardware control + hardcoded CO2/VOC/Humidity
  threshold monitoring combined in one file) is promoted and split into two `src/` files** - the old
  file is deleted, `improved-quality/sensortask-wozi.py` wires the two replacements directly.
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
  `improved-quality/sensortask-wozi.py` no longer matches this: its `main()` now calls
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
section is the authoritative vendoring policy). The facts below were confirmed by reading its
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
  exception subtype, without needing one registration per exception type. With no handler
  registered at all (today's state, in both `improved-quality/sensortask-wozi.py` and the deployed
  `python/CommonDrivers/microdot.py` app — confirmed, neither registers any `errorhandler`),
  Microdot's own bare default response is used (`'Internal server error', 500`, or `'Not found',
  404`, etc.) — safe, but not one of our own reply shapes.
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
  `improved-quality/sensortask-wozi.py`'s `main()`: `start_asy_webserver()` is one of the plain
  `task_starters`). A Microdot task that terminates — by returning or by an exception escaping it —
  is detected the same way any other dead task is (`task.done()`) and restarted automatically, with
  the same decaying failure counter and eventual full-reboot fallback as any other task.
  **"Restart Microdot if it crashes" is therefore already implemented generically — it does not need
  Microdot-specific supervisor code —** provided the failure actually terminates that task rather
  than being silently contained at a level the supervisor never observes (see BACKLOG.md for the
  still-open question of exactly what "crashes" means at the per-connection level on MicroPython's
  `asyncio`).
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
  misleading `max_i2c_err` during Step 1 of the final-wiring effort (owner-authorized; see
  `FINAL_WIRING_PLAN.md`) — every promoted driver/service's constructor and every test file that
  constructs one was updated together in that one pass.

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
`_check_device_id()`/`_read_status()`/`_setup_addr_buffer()` are a real, current instance of this —
see C.3.1) — that's a genuine D.4 violation, not an example of this exemption.

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
anywhere in `src/`/`improved-quality/` today** (see BACKLOG.md). Three real architectural choices
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
All three are currently dead weight — nothing in `src/`/`improved-quality/` calls any of them with
malformed input today, since every call site is type-checked at the mypy boundary. Kept
deliberately anyway: once the Microdot REST layer feeds real, untrusted request data into these
paths, the catches stop being defensive-only and become load-bearing. Don't remove them as
"unreachable dead code" — they're pre-positioned for wiring that hasn't landed yet (see
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
in its push-callback wrapper — `improved-quality/sensortask-wozi.py`'s `_scd_apply_field`/SCD30's
`stop_continuous_measurement()` is the other live instance (inverted: `True` input is the no-op
there).

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

Replaces `improved-quality/api_helpers.py`'s ad hoc `cmd_post_check`/`special_err`/
`generic_error_return` pipeline (left as read-only WIP reference, not edited or deleted). Same
wire shape as before (`{"res": "OK"|"ERR", "code": int, "descr": str, "result": ...}`):

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

Every REST endpoint handler in `improved-quality/sensortask-wozi.py` now calls these directly
(under a scoped, project-owner-authorized exception to CLAUDE.md's hard rule on editing
`improved-quality/` source, since that file was `improved-quality/api_helpers.py`'s last remaining
importer). `setSGP`/`setBMP` route directly through `sgp_reader.get_cfg_schema()`/
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
  `_get_dict_cfg()` (`wrnno=1`, `errno=3`/`4`), and `_set_dict_cfg()`/`_recover_failed_push()`
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
  from a `_get_dict_cfg()` internal failure). A broader, deliberate scheme of shared common-error
  *classes* (not just this base-range reservation) across drivers is a real future direction — see
  BACKLOG.md's "common driver error classes" entry — not implemented yet and out of scope for a
  driver's initial promotion.
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
  per-class one. See `WIRING_CONTRACT.md` for where that aggregation actually lands once it's
  designed.

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
| `asy_fram_manager.py`/`asy_fram_driver.py` (shared `"FRAM"` logger — `AsyFramManager`, its chunk classes, and `FRAM_SPI` all share one stream) | 17-97 | 60-83 | `AsyFramManager`: 17-88, non-sequential — `_write_chunk()`=17/18/26, `_read_chunk()`=37/38/46-48, `_clear_chunk()`=57/58, the block-pair `_write()`/`_read()`/`clear()` helpers reuse 60-64/70-73/80 for both their own `errno` and matching `wrnno` (pause/invalid-block-data warnings), the remaining higher-level methods (`write()`, timestamp write/sync/`setup()`)=81-88. `FRAM_SPI`: 89-97, continuing sequentially (not-initialized ×5, invalid-range ×2, readback mismatch, lock-timeout) + `wrnno`=81-83 (WRDI-stuck, WEL-didn't-set ×2). |
| `asy_bmp3xx_driver.py` (`"BMP3XX"`) | 10-21 | — | 10=init, 11-14=config read/write, 15-20=oversampling/filter forwards, 21=trigger-interval. |
| `asy_scd30_driver.py` (`"SCD30"`) | 10-24 | — | 10=init, 11=read, 12=stop-continuous-measurement, 13-24=per-field get/set forwards in pairs. |
| `asy_sgp40_driver.py` (`"SGP40"`) | 10-18 | 10-14 | 10=init, 11-12=config, 13-18=VOC-backup read/write/serialize; `wrnno`=backup-missing/stale conditions. |
| `asy_wifi_service.py` (`"WIFI"`, `AsyConnTime`) | 11-18 | 1-7 | 11=mode-switch, 12=hotspot-activate, 13=STA-connect-attempt, 14=STA-poll, 15-16=STA-disconnect/deactivate, 18=disconnect-timeout; `wrnno` 1-3=missing-config per connection phase, 4-7=WLAN status conditions. |
| `asy_ntp_client.py` (`"NTP"`) | 11-20 | 1-3 | 11=missing-config, ..., 19=time-calc, 18/20=missing-config-interval-fallback/give-up; `wrnno`=callback failures. |
| `captive_dns.py` (`"DNSSRV"`, `DNSServer`) | 1-3 | 1-2 | 1=invalid server_ip/netmask at startup, 2=unexpected loop exception, 3=disconnect-cleanup exception; `wrnno` 1=dropped `sendto()` reply, 2=invalid recvfrom data/address. |
| `system_service.py` (`"SYSTEM"`) | 1-4 | dynamic (`n + 1`) | 4=task-error-budget-exceeded-rebooting; `wrnno` assigned per task-supervisor index — see the "dynamic assignment" bullet above, not a fixed catalog. |
| `asy_notification_service.py` (`"NOTIFY"`) | 1-4 | 1-5 | 4=`request_signal_cb` callback failure. |
| `asy_neopixel_driver.py` (`"NEOPIXEL"`) | — | — | No persisted logging today — only informational `evt()` calls, nothing that fails in a way worth counting against `get_error_counter()`. |
| `asy_i2c_driver.py`/`asy_spi_driver.py`, `asy_udp_socket.py`, `asy_dns_client.py` (client side) | — | — | Deliberately no logging (reverted) — every real failure already surfaces to and gets logged by exactly one upstream owner; see the standing "Bus layer"/"`asy_udp_socket.py`/`asy_dns_client.py`" conventions above. |
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
see any `*_I2C` class's multi-step methods for the concrete nesting.

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
   started with, and a driver with no twin counterpart silently regresses Step 5's own coverage.

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
  whatever raise/never-raise contract the class already declares in its own module docstring.**
  - A class documented as "never raises" (every `SensorReader`/`SensorReaderConfig` subclass,
    `PrintLog` family, `ConfigManager`) returns its documented sentinel and logs, exactly like every
    other failure mode that class already handles. This holds even for `FRAM_SPI` specifically,
    whose own docstring promises "self-healing to a safe state without raising, except
    `__init__`/`setup()`'s one-time setup errors" — its pre-`setup()` sentinel-returning behavior
    was already correct.
  - `SPIDevice.__aenter__`'s raise is a structural necessity of Python's `async with` protocol (no
    sentinel-return option exists for a failed `__aenter__`), not a stylistic precedent — it doesn't
    extend to any other method on any other class.
  - **Verify per class, don't assume**: check the specific class's own module docstring for an
    already-declared raise/never-raise contract before deciding the response shape, rather than
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

Files land in `src/` once they've cleared the full **production-quality** bar below — moved out of
`improved-quality/` (WIP refactor target, see CLAUDE.md) once they have. This checklist keeps
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
      resolve either — but a real runtime call like `TypeVar("T")` does. This is a live, present
      gap across much of `improved-quality/` too (most files there do an unconditional `from
      typing import ...`, untested against the real interpreter) — not something to fix
      opportunistically in unrelated files during an unrelated review, but the pattern every new
      `src/`/test file should use going forward.
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
      that consolidation. (`crc_checks.py` and `improved-quality/sensortask-wozi.py` already use
      the modern `asyncio`/`struct` names — check any other `improved-quality/`/legacy file going
      through this review for the old `u`-prefixed pattern, don't assume it's already been swept
      everywhere.)
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

Unit tests for `src/` (fully-reviewed code moved out of `improved-quality/` — see CLAUDE.md). Total
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
`FINAL_WIRING_PLAN.md`/Step 4 story hit exactly this). `frozen_modules` is a separate, ordinary,
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
  - **1.26 is the pin for the current, deployed codebase only.** The `improved-quality/` refactor
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
underlying `machine.I2C` peripheral object itself (constructed once, at module level, in
`improved-quality/sensortask-wozi.py`) - only a full reboot replays that construction (see A.4's
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
"vendor-derived" alone doesn't imply either one, so check which vendor before assuming:

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
