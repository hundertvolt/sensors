# SPECIFICATION

Central specification: architecture, build/toolchain mechanics, sensor-driver architecture,
`src/` production-quality checklist, testing/coverage.

**Not here, by design:** `CLAUDE.md` (AI-session operating constraints — hard rules, working
agreements, PR workflow, pre-push verification, code-quality tooling) and `BACKLOG.md` (active
working memory — open questions, deferred work; churns as items resolve, so folding it in here
would recreate the scattering problem this document exists to fix).

## Table of contents

- **Part A** — Repository & Architecture Overview
- **Part B** — Toolchain & Build
- **Part C** — Sensor Driver Architecture Specification
- **Part D** — `src/` Production-Quality Checklist
- **Part E** — Testing & Coverage
- **Part F** — Platform Target & MicroPython Runtime Facts
- **Part G** — Shared Pattern & Primitive Reuse
- **Part H** — Website (JS/HTML/CSS) Architecture
- **Part I** — Memory-Safety Audit & Discipline

---

# Part A — Repository & Architecture Overview

## A.1 Repository layout

```
datasheets/              Real datasheet PDFs for the chips this codebase drives (CLAUDE.md)
  bmp3xx/, fram/, pico w/, scd30/, sgp40/
html_raw/               Legacy, still-deployed per-device HTML/CSS/JS - targets the pre-refactor
  arzi/, dev/, wozi/,     REST shape, superseded by html/ for devices the refactor has reached (H.1)
  general/
html_stub/              Placeholder website content for the refactored build's generic pipeline
                          tests (A.9)
html/, js/, tests_js/,  The real, refactored website - source, tests, prototype-only mock-backend
  mockdata/               fixtures (Part H)
modules/                Auto-started entry points, one set copied into the firmware build per device
  _boot.py                 mounts the flash filesystem, starts the sensor task
  sensortask-{arzi,dev,neu,wozi}.py   per-device app (renamed sensortask.py at build time)
python/
  CommonDrivers/          shared across all device configs
  IndividualDrivers/      only copied in if a device config needs them
  Manifest/manifest.py    MicroPython freeze manifest
src/                     Fully-reviewed/tested refactor code, freely editable (Part D). Includes
                          src/sensortask_wozi.py (A.7), src/sensortask_dev.py (dev bench, B.11/H.5),
                          src/asy_webserver_service.py (A.8). improved-quality/ (former WIP staging)
                          has been fully retired and deleted.
ext/                     Vendored third-party code, hands-off (CLAUDE.md)
  microdot.py               Microdot v2.6.2, unmodified (A.5)
  freezefs/                 freezefs 2.4, unmodified - gzip+freeze pipeline for html_stub/ (A.9)
boot_entry/              Real firmware entry point for sensortask_wozi.py/sensortask_dev.py
  wozi_boot.py/dev_boot.py  the only files that block on asyncio.run(main()) - kept separate so
                            sensortask_*.py stays import-safe for tests
digital_twin/            Hardware simulator for I2C/SPI/WiFi under the MicroPython Unix-port
                          interpreter (A.10, digital_twin/README.md, Part C.11 point 9)
frozen_modules/          Gitignored build artifact (build_frozen_html.sh's gzip+freezefs output) -
                          deliberately not under .frozen/ (a reserved import-machinery sentinel, A.9)
SPECIFICATION.md         This file
tests/                   Unit tests for src/, real MicroPython interpreter (Part E)
toolchain/               MicroPython/pico-sdk/picotool build-environment installer
  versions.toml             single source of truth for the target MicroPython version (Part B)
  setup_toolchain.py        setup/test - builds RP2040 firmware and the Unix port
build-{arzi,dev,neu,wozi}.sh   per-device build scripts
pyproject.toml           dev-tooling config (ruff/mypy/pytest/uv)
scripts/                 lint.sh/typecheck.sh/test.sh, build_frozen_html.sh, run_unix_port_integration.sh
.github/workflows/       CI: lint.sh/typecheck.sh/test.sh on every push/PR
```

## A.2 Architecture at a glance

- **Sensor Reader/Driver split** — every `asy_<chip>_driver.py` pairs a low-level chip driver
  (register-level I2C/SPI, several adapted from Adafruit) with a `*_Reader` wrapper giving the
  common async-task surface (`start_asy_read`/`start_asy_trigger`/`start_timer`, a locked
  `DataManager`, an error counter, config callbacks). Full spec: Part C.
- **Bus layer** — `asy_i2c_driver.py`/`asy_spi_driver.py` wrap `machine.I2C`/`machine.SPI` with an
  `asyncio.Lock` and an `async with device as dev:` pattern so multiple sensors share one bus.
- **Config management** — deployed `python/`/`modules/` use `async_manager.ConfigManager`: one
  ad hoc instance per device, flat JSON, self-heals corruption by overwriting the entire file with
  hardcoded defaults (data-loss risk on firmware upgrades that add keys — BACKLOG.md).
  `src/config_manager.py`'s `ConfigManager` replaces it: every module owns its own schema
  (`ConfigSchema` tuple) and config file via a public `cfg_schema` attribute (C.5).
- **REST API pipeline** — deployed `api_helpers.py` chains `cmd_pre_check → init_json_from_cfg →
  update_valid_json → set_sensor_value → cmd_post_check` per PUT. `src/api_response.py` replaces it:
  `base_classes.py`'s `_set_dict_cfg()` gives every `SensorReaderConfig` a generic schema-driven
  setter; `api_response.py`'s `make_response()`/`parse_cmd_request()`/`handle_set_cmd()` replace the
  per-endpoint glue with one response envelope (C.5.3).
- **FRAM storage** (arzi/neu/wozi only) — a bump allocator handing out chunks as two redundant
  copies, so power-loss/watchdog reset mid-write leaves one valid copy. Used today for SGP40's VOC
  baseline backup.
- **LED notification signalling** — `asy_neopixel_driver.py` (pure LED hardware: overlay toggle,
  dimmed ramp, internal/external arbitration for the one shared pixel; no config schema) +
  `asy_notification_service.py` (`NotificationCoordinator`: generic threshold signalling replacing
  legacy's hardcoded CO2/VOC/Humidity checks).
- **Networking** — `asy_wifi_service.py` (STA + captive-portal AP/hotspot fallback),
  `asy_ntp_client.py` (NTP + CET/CEST DST math), `asy_dns_client.py` (non-blocking DNS resolver
  replacing `socket.getaddrinfo()`). Deployed code still uses the monolithic `async_connect.py`.
- **Task supervisor** (`main()` in every `sensortask-*.py`) — two-tier self-healing: dead tasks
  restart silently (decaying error score); once the score exceeds a threshold, the loop stops
  feeding the watchdog and lets it force a hard reset. Units run years unattended.
- **Frontend** — hand-written HTML/CSS/vanilla JS, gzipped and packed into `frozen_html.py` via
  `freezefs` at build time, served through Microdot's `send_file(..., compressed=True)`.

## A.3 Refactor status

Targets the latest *stable* MicroPython/pico-sdk/picotool/Microdot, expands error handling/fault
recovery, adds unit tests/mypy/ruff/CI (lint/type-check/unit-tests today; a firmware build CI stage
is planned, BACKLOG.md). Files land in `src/` once reviewed against Part D.

Prototype covers `src/sensortask_wozi.py` ("wozi", A.7) and `src/sensortask_dev.py` (dev bench,
physically flashed, B.11/H.5) — not yet `arzi`/`neu`. Goal: same top-level features as today's
deployed units, not a feature change. A future per-variant build-script generator (one
setup-definition file → every variant's app/website pair) is planned but not built (A.8's
registration API and A.9's `HTML_SRC_DIRS` are shaped around it). Real-hardware genericization for
`arzi`/`neu` is open (BACKLOG.md).

## A.4 Architecture — deep reference

- `python/CommonDrivers/api_helpers.py` — generic REST pipeline repeated by hand per endpoint, no
  shared schema/route generation.
- `python/CommonDrivers/async_connect.py` — WiFi STA + AP/hotspot + NTP with manual CET/CEST DST
  (`cettime()`); exposes `get_long_block_lock()`, a lock serializing `socket.getaddrinfo()` against
  Neopixel animation. Deployed-only — `src/` splits this into `asy_wifi_service.py`/
  `asy_ntp_client.py`/`asy_dns_client.py` and retires the lock (F.2).
- `python/CommonDrivers/async_manager.py` — `ConfigManager`, `DataManager`, `TimeCounterManager`,
  `LockedValue`/`Flag`. `src/config_manager.py`/`src/base_classes.py`'s `LockedValue`/
  `LockedCounter`/`LockedFlag` (snake_case, unlike the old camelCase) replace these. MicroPython's
  flat frozen-module namespace means `import async_manager` silently resolves to whichever file
  defines that name — always import by name from `config_manager`/`base_classes`, never
  `async_manager`. Its config loads once at `__init__` into an in-memory cache; a read can't detect
  on-disk corruption after that, and `write_config()` silently repairs an externally-corrupted file
  from the cache (accepted: this device is the file's only writer). `src/asy_neopixel_driver.py`'s
  `NeopixelDriver` is the one deliberate exception to "every module owns a schema" (no schema at
  all, confirmed by the project owner). A module whose caller needs `write_config()` directly
  exposes the schema via a public `self.cfg_schema` attribute (`asy_wifi_service.py`/
  `asy_ntp_client.py`).
- `asy_fram_driver.py`/`asy_fram_manager.py` — raw SPI FRAM driver + chunk allocator with dual-copy
  redundancy (arzi/neu/wozi). `src/`'s promoted versions: each chunk stores two copies plus a
  busy/idle status byte guarding reads and writes (MB85RS64V reads are destructive internally, so a
  power loss mid-read is as real a risk as mid-write); "both copies valid but different" is a hard
  failure (no generation counter), never guessed. `AsyFramTimestampedChunk.write()`/`write_into()`
  return `(ntp_synced, utc, success)` — `success` is third, not first; don't reorder. `AsyFramManager`
  is a bump-pointer allocator: instantiation order is on-chip layout and must stay identical across
  firmware versions for existing data to decode correctly.
  **FRAM chunk determinism rule** (no deallocation exists by design): every FRAM-chunk-owning
  object's construction must be deterministic across every system event, especially reboot — an
  unconditional, fixed-position statement, never inside a branch/loop a task restart could
  re-enter. True today: task restarts only re-invoke an already-captured starter on the *existing*
  object, never `__init__`; a full reboot replays `build_system()`'s construction from scratch, and
  every current FRAM-chunk-owning construction (`sysfunct`, `sgp_reader`'s VOC chunk, `pixel`,
  `notify_service`) is unconditional top-level. Prove single, deterministic construction before
  adding any new FRAM-backed class.
  Every deliberate system reset pauses FRAM first (`system_service.py`'s `_reboot()` calls
  `storage_pause(True)` before arming the reset timer, and before the watchdog-starve fallback).
  Margin is ample (FRAM at 1MHz, 8KB chip, no chunk near that size — a two-block write+CRC readback
  completes in low single-digit ms, three orders of magnitude under both the 4s reset delay and the
  ~8s watchdog-starve wait). Enforced by `tests/test_reset_call_site_invariant.py` (fails if
  `machine.reset()`/`bootloader()` appear anywhere but `system_service.py`, or `WDT()` anywhere but
  `sensortask_wozi.py`).
- **SCD30's `AmbPres`** is stored in the sensor's own NVM as a one-time-set value, not a
  continuously-updated live input — hence a static config value even on wozi (which has a live
  BMP388); `set_ambient_pressure` uses `force=True` since resending the same value is also SCD30's
  documented command to resume continuous measurement. Confirmed deliberate by the project owner.
- **SCD30's `ForceCalRef`** recalibration is manual: ventilate until indoor CO2 matches outdoor
  ambient, then set `ForceCalRef` to that value via REST. No automation planned.
- **SCD30's `TempOffs`** has real 0.01°C resolution: `set_temperature_offset()` sends
  `int(offset * 100)` — a genuine truncation, unique to this field; more than two decimals is
  silently truncated by the chip, not rejected.
- **SGP40's VOC index** is deviation-from-learned-baseline, not absolute concentration (confirmed
  against `voc_algorithm.py`'s Sensirion port): (1) 45 sampling intervals must elapse before the
  index moves off 0; (2) under any constant raw input the index converges toward 100 ("clean air") —
  a spike needs a real step change, not just a high absolute value; (3) a *higher* raw tick count
  reads as *cleaner* air — the inverse of what "raw" suggests. Not a bug — how Sensirion's reference
  algorithm works; `asy_sgp40_driver.py` treats `VOC` as an opaque index throughout (F.4).
- Legacy `neopixel_signal.py` (LED hardware + hardcoded threshold monitoring) was split:
  `asy_neopixel_driver.py`'s `NeopixelDriver` (pure LED hardware, unchanged mechanism —
  `request_signal()` returns once queued, not once its ramp finishes; also serves
  `asy_wifi_service.py`'s `LEDControl` Protocol) and `asy_notification_service.py`'s
  `NotificationSignal` (plain data holder) + `NotificationCoordinator(SensorReaderConfig)` (generic
  threshold signalling — owns sleep-window/interval/`AutoOn`/global `FlashBri`/`FlashDur`, one
  combined `ConfigManager`/logger). **Staged registration, deferred construction**: `__init__()`
  stashes args only; `register()` (sync) accepts `NotificationSignal`s in check-order; `finalize()`
  (sync, once) builds the combined schema and is the point `self.pr`/`self.cfgmgr` come into
  existence via a delayed `super().__init__()`. Rejections during the sync
  `register()`/`finalize()` window are buffered and drained by `monitor_loop()`.
  `NotificationSignal.color` is a per-channel weight (0/1) scaled by the shared `FlashBri` at
  trigger time. Config field names drop the "Led" prefix everywhere (`WarnCO2` not `LedWarnCO2`) —
  a deliberate wire-format change; only legacy `html_raw/` isn't updated (accepted debt, H.1).
- Deployed task supervisor is a hand-rolled loop duplicated per device file;
  `src/sensortask_wozi.py`'s `main()` instead calls `system_service.py`'s real
  `start_and_check_tasks()`/`start_timers()`.
- **Functional behaviors confirmed intentional by the project owner — don't "fix" these:**
  air-quality LED sequencing (one color per condition, paused between flashes); FRAM SGP40 backup
  "0 = disabled" for `BackupPeriod`/`BackupMaxAge` (`DEVICE_REFERENCE.md`); permanent WiFi
  deactivation after a second STA failure streak, `_PHASE_DEACTIVATED` special-cased through task
  restarts the same way `_PHASE_HOTSPOT` already is — only a physical power-cycle clears it; STA
  never auto-falls-back to hotspot once connected successfully even once in a task's lifetime — only
  a human resubmitting credentials or a full task restart resets this; the web UI shows raw numbers
  only, no color-coding (the LED is the at-a-glance indicator); SGP40 silently degrading to
  uncompensated VOC when SCD30 is down, with no distinct signal (SCD30's own error counter covers
  it); FRAM's 8KB has ample headroom over SGP40's ~250-byte usage; `asy_uart_driver.py` intentionally
  exposes no hardware flow control; `asy_notification_service.py`'s active-window check doesn't
  handle a window wrapping past midnight (`OnH=22`/`OffH=6` silently never triggers) — byte-for-byte
  identical to legacy's proven field behavior, a future overnight-window feature would need
  `on_min_of_day > off_min_of_day` handling; SCD30's `get_ambient_pressure()` reuses the same command
  word used to *set* it, matching every sibling getter and legacy's proven behavior even though
  neither Sensirion reference driver documents that command as readable.

## A.5 Microdot / REST layer

`ext/microdot.py` is vendored, unmodified upstream Microdot (pinned `v2.6.2` — no edits/cleanup;
CLAUDE.md's Hard rules are authoritative; MIT text at `ext/LICENSE-microdot`). Facts below confirmed
against its actual source, not docs/memory.

- **Every exception raised by our own code inside a route handler — including a before/after-request
  hook, and `MemoryError` — is already caught by Microdot itself, per request, and can never crash
  the server.** `dispatch_request()` wraps the whole handler chain in `except HTTPException` /
  `except Exception`. `HTTPException` (from `abort()`) resolves by numeric status code; any other
  exception resolves by exact class then MRO walk, so one `@app.errorhandler(Exception)` is a
  catch-all for any subtype. Deployed `python/CommonDrivers/microdot.py` registers no handler at all
  (Microdot's bare default response, safe but not our shape). `src/asy_webserver_service.py`
  registers shaped-JSON handlers for 400/404/405/413/500 plus a catch-all persisting the exception
  into `pr.err_s()`/FRAM history.
- **The one gap: exceptions raised while writing the response itself.** `Response.write()` only
  catches `OSError`, muting a short allow-list of expected socket errors — anything else propagates
  uncaught out of the per-connection handler. By then the response is already in flight, so there's
  no hook left to convert the failure into a reply — the client hits a timeout, as expected.
- Microdot's own exception logging (`print_exception`) is **not** wired into this project's
  `PrintLog`/FRAM logging — anything caught by the blanket catch needs an `@app.errorhandler` calling
  `pr.err_s(...)` to leave a trace.
- `Request.json` has no internal guarding (raises straight out on malformed body) — already
  contained by the blanket catch; guarding it ourselves is about a precise reply, not crash
  prevention.
- Request size is bounded before any handler runs: `max_content_length` (16KB default, 413 if
  exceeded) → tightened to 4096 bytes in `asy_webserver_service.py`; `max_readline` (2KB default).
- The Microdot server task is wired into `start_and_check_tasks()` like every other module — a dead
  server task restarts automatically with the same decaying-failure/reboot fallback, no
  Microdot-specific code needed, since **each accepted connection runs in its own independent
  `asyncio.Task`** (confirmed against `extmod/asyncio/stream.py`) — the one confirmed
  `Response.write()` gap only ever takes down that one client's connection, never the accept loop.
- `errorhandler()`'s two lookup keys are independent: numeric status code (what `abort()` resolves
  through, by `exc.status_code`, never class) vs. exception class (exact then MRO). Registering
  `@app.errorhandler(HTTPException)` never fires for `abort()`.
- **Captive-portal hotspot redirect fallback**: `_serve_static()`'s `except OSError` branch (no
  matching file) redirects to `/` (302) instead of 404 whenever `is_hotspot_active: Callable[[],
  bool] | None` is provided and returns `True` (default `None` = old always-404 behavior).
  `sensortask_wozi.py` wires this to `AsyConnTime.is_hotspot_active()`. This is what makes phones'
  captive-portal probes (`generate_204`, `hotspot-detect.html`) trigger the OS "Sign in to network"
  popup instead of a silent 404, while `captive_dns.py` answers every domain with the AP's IP.
- Deployed `python/CommonDrivers/microdot.py` already implements essentially the same protective
  architecture, predating `ext/microdot.py`'s vendoring — one drift: its `HTTPException` branch
  invokes a status-code handler directly rather than through v2.6.2's async-safe `invoke_handler()`
  wrapper — irrelevant today since neither app registers handlers there.

## A.6 Datasheets

`datasheets/` (repo root) holds real datasheet PDFs for the chips this codebase drives (`bmp3xx/`,
`fram/`, `pico w/`, `scd30/`, `sgp40/`) — read the PDF first for any hardware-interaction claim,
rather than reconstructing from training memory/web search. If a needed one isn't there and can't
be fetched, say so explicitly.

**BMP390**: `datasheets/bmp3xx/` holds BMP384/BMP388 but not BMP390. The project owner has confirmed
the whole family shares the same register map/protocol, so `asy_bmp3xx_driver.py` treating BMP390's
`0x60` chip ID the same as the other two is correct — the PDF's absence is a documentation gap only.

## A.7 `src/sensortask_wozi.py` construction order and dependency graph

`build_system(*, cfg_path="", debug=None, web_host="0.0.0.0", web_port=80) -> None` does pure
construction (every object assigned to a module-level global) plus a `setup()` batch; `main()`
calls `build_system()` then `start_timers()`/`start_and_check_tasks()`. Neither blocks at import
time — the real entry point, `boot_entry/wozi_boot.py` (`asyncio.run(main())`), is kept separate so
`import sensortask_wozi` stays safe under tests.

**Why order matters**: `AsyFramManager` is a bump-pointer allocator — instantiation order is
on-chip layout and must stay identical across firmware versions (A.4's determinism rule).

**Construction order, top to bottom**:

1. `watchdog = WDT(timeout=8000)` — hardcoded, no injection point.
2. `conn = AsyConnTime(...)` — owns `DNSServer` internally (`captive_dns.py`).
3. `ntp = AsyNtpClient(conn.get_wifi_mode_lock(), conn.network_available,
   conn.get_dns_server_ip, ...)` — bound methods off `conn`.
4. `i2c0`, `i2c1` = `asy_i2c_driver.I2C(...)` ×2. `i2c0` (SCD30, step 10) sets `timeout=200000`
   (200ms): SCD30 documents up to 150ms clock stretching/day, past rp2's 50ms default — without the
   override that expected stretch surfaces as a spurious `OSError`. `i2c1` (SGP40/BMP3xx) keeps the
   port default.
5. `spi0 = asy_spi_driver.SPI(...)`.
6. `fram = AsyFramManager(spi0, 1, max_size=0x2000, ...)` — no chunk of its own.
7. `sysfunct = SystemService(ntp.ntp_issynced, watchdog=watchdog, fram=fram, ...)` — **FRAM chunk 1**.
8. `sgp_reader = SGP40_Reader(i2c1, sgp_comp_callback, fram_storage=fram,
   fram_ntp_callback=ntp.ntp_issynced, ...)` — **chunks 2-3** (error log, then VOC backup).
9. `bmp_reader = BMP3xx_Reader(i2c1, ..., fram=fram, ...)` — **chunk 4**.
10. `scd_reader = SCD30_Reader(i2c0, 8, trigger_sec=3, ..., fram=fram, ...)` — **chunk 5**; no
    config schema (params live on-sensor).
11. `pixel = NeopixelDriver(15, fram=fram, ...)` — **chunk 6**.
12. `notify_service = NotificationCoordinator(pixel.request_signal, ntp.cettime, fram=fram, ...)`,
    staged `register()` ×3 then `finalize()` — **chunk 7**.
13. `conn.set_ext_led(pixel)`.
14. `app = Microdot(); webserver = WebserverService(app, sensors=(...), ..., static_mount="/html",
    is_hotspot_active=conn.is_hotspot_active, host=web_host, port=web_port)` — **no `fram=`**
    (deliberately RAM-only — a connection-reclaim warning could churn faster than a sensor's fault
    log, and this keeps the seven-chunk order unchanged). `static_mount="/html"` registers the
    static route pair last, so an exact-match API route always wins.
15. `sysfunct.set_level_setters(_collect_level_setters())` — after every module has constructed.
16. **`await x.setup()` batch**: `sysfunct → fram → conn → ntp → sgp_reader → bmp_reader →
    notify_service`. One hard constraint: `notify_service.setup()` needs `finalize()` (step 12)
    already run, satisfied by batching at the end. `scd_reader.setup()` isn't in this batch (no
    local config).

**Real FRAM chunk order**: SystemService → SGP40 error log → SGP40 VOC backup → BMP3xx → SCD30 →
Neopixel → NotificationCoordinator. Seven chunks — every module with a FRAM-backed error log uses
it; must stay in this relative order. `src/` has no earlier on-chip layout to preserve.

**This order, and `i2c0`'s SCD30-specific `timeout=200000`, are wozi's own** — a future per-variant
generator must derive both from the variant's own module set, not assume wozi's answer applies
everywhere.

**Task/timer starter collection** (`_collect_task_starters()`/`_collect_timer_starters()`, from
`main()`): every module's `get_task_starters()`/`get_timer_starters()` is called uniformly.

**Debug-level registry** (`_collect_level_setters()`, `SystemService.set_level_setters()`/
`_apply_level()`): collects every logger's bound `set_level` method into one registry at boot;
`_apply_level()` calls each wrapped in its own `try/except Exception`. Calling `set_level()` at any
time is safe (no interrupt handler touches logging, `self.level` is a single atomic-store `int`).

**Dependency graph**: `ntp` holds `conn`'s bound methods; `notify_service` holds
`pixel.request_signal`/`ntp.cettime`; `conn` holds `pixel`; `sgp_reader` holds `ntp.ntp_issynced`.
Every module constructs its own `ConfigManager`/`PrintLog` internally — no cross-module config
sharing. No `src/` module imports another by name to reach a sibling — every dependency is
constructor-injected, so the graph is a clean DAG at the import level.

Full coverage: `tests/test_sensortask_wozi.py`.

## A.8 REST API endpoint reference (`src/asy_webserver_service.py`)

`WebserverService` is **registration-based**: modules hand it named callback groups at construction
(`sensors=`, `settings=`, `system_cmd=`, `notification_led=`, `notification_pause=`,
`status_sources=`, `maintenance_sensors=`, `error_sources=`) and it auto-constructs the REST
surface.

**Six endpoints**: `/measurements`, `/sensors`, `/networking`, `/system`, `/status`,
`/notification`. `/measurements`/`/status` are the only live-data endpoints; the rest are pure
settings.

- **GET shapes**: `/measurements` → `{"SCD30": {...}, "SGP40": {...}, "BMP3XX": {...}}` (each
  `get_dict_data()`); `/sensors` → same, each `get_dict_cfg()`; `/networking` → `SSID, PW(masked),
  Country, Hostname, LedWifiOn, NTP_Host, NTP_Offset_S, NTP_Interv_H`; `/system` → `DebugLevel,
  GMTOffset, DSTOffset`; `/notification` → `OnH, OnM, OffH, OffM, FlashBri, Interv, FlashDur, AutoOn,
  WarnCO2, WarnVOC, WarnHum`; `/status` → live-only, sub-structured `networking`/`system`/`sensors`/
  `notification`/`errcount` (one entry per module plus per `ConfigManager` — `CFGMGR_<name>`).
- **Real production bug, fixed**: `_get_measurements()`/`_get_sensors()` must build results with
  `.update()`, never `result[name] = await module.get_dict_data()` — every driver's own return is
  already `{name: {...}}`, so indexing doubled it into `{"SCD30": {"SCD30": {...}}}`.
- **PUT shapes** — sparse JSON, no `cmd` envelope: present fields apply, omitted stay untouched,
  unknown fields ignored. `/measurements` — no PUT. `/sensors` — per-sensor field subsets; SCD30
  dispatches through its own non-persisting setter (no `cfgmgr`, NVM-backed). `/networking` — WiFi
  fields fire `reconnect_wifi()`, NTP fields fire `ntp_force_sync()`, `LedWifiOn` fires nothing —
  one `SettingsGroup` per subset keeps these independent. `/system` — settings +
  `"SystemCmd": "reboot"|"bootloader"|"mempause"` (enum-validated; `mempause` duration fixed 300s).
  `/status` — `{"ResetErrors": true}` only. `/notification` — settings + `lightCmdLED` (r/g/b/t) +
  `PauseTime` (range-checked 0-3600, rejected not clamped, before reaching
  `NotificationCoordinator.set_override_led()`).

**Numeric coercion policy** (`config_manager.py`'s `coerce_numeric()`): a JSON int is always
accepted for a float field; a JSON float is accepted for an int field only with no fractional part
(`5.0`→`5`, `5.7` rejected as `"Invalid"`, never truncated). Float→int is exactly round-trip
checked; int→float has a known, accepted gap (every int representable as float only up to the
mantissa precision, F.1) — accepted since no registered float field's bounds go near it (largest
today: BMP3xx's `SeaLevelOffs` at `5000.0`). `bool` never accepted for int/float (`type()`, not
`isinstance()`). NaN/±inf attempting int-coercion are caught via MicroPython's own `int(float)`
exception shapes. `js/mock-server.js` mirrors the equivalent policy.

**GET copy-safety**: `get_dict_data()`/`ConfigManager.get_dict()`/`PrintLogHistory.get_log()` all
build a fresh dict/list per call with no `await` mid-construction, so cooperative scheduling makes
each snapshot atomic. **One open exception**: `SCD30_Reader.get_dict_cfg()` and three of
`BMP3xx_Reader.get_dict_cfg()`'s fields are live hardware-readback fields whose callback awaits mid-
construction, so a concurrent write can mix pre/post-write values across fields (BACKLOG.md).

Connection hardening (per-call/outer-cap timeouts, reject-when-full, no bespoke restart mechanism)
and `Connection: close` live in `WebserverService`/`_TimeoutStreamProxy` — see that module's own
comments and `tests/test_asy_webserver_service.py`.

## A.9 Website stub / frozen-HTML pipeline

`html_stub/` (7 flat files) is placeholder content standing in for real website content in the
refactored build's generic pipeline tests. `scripts/build_frozen_html.sh` gzips a temp copy of the
source dir(s) (`html_stub/` default, `HTML_SRC_DIRS` overridable), then runs `python -m freezefs
<tmp> frozen_modules/frozen_html.py --on-import mount --target /html --overwrite always` (never
`--compress`: this project pre-gzips by hand, served via Microdot's `send_file(...,
compressed=True, file_extension=".gz")`). Output goes to `frozen_modules/` (gitignored), not
`.frozen/`: `.frozen/` is a hardcoded MicroPython import-machinery sentinel
(`MP_FROZEN_PATH_PREFIX`) — any path starting with that string routes to the compiled-in frozen
table, so a real on-disk file there is silently unimportable. `src/sensortask_wozi.py` does a
module-level `import frozen_html`, mounting `/html` as a side effect; `WebserverService(...,
static_mount="/html")` registers the static route pair.

`tests/test_frozen_html_integration.py` is the real-pipeline proof;
`tests/test_asy_webserver_service.py`'s Section G exercises the generic route-wiring against a
synthetic fixture. The real, non-stub website is Part H.

**`scripts/test.sh` and `npm test` both write `frozen_modules/frozen_html.py`, with different
content — never run the two concurrently.** `scripts/test.sh` puts the *stub* there (and the real
wozi site in the separately-named `frozen_website_wozi.py`); `npm`'s `pretest` hook runs
`scripts/build_website.sh wozi` with no output argument, which defaults to that same
`frozen_html.py` and stages the *real* site. Interleaving them makes whichever suite loses the race
fail confusingly — `test_frozen_html_integration.py` 404s on stub-only paths, or
`tests_js/live-backend*.test.js` times out waiting for a real section in the placeholder page. Both
are harmless artifacts of a local run, not regressions; CI never hits this (each tier is its own
runner). Run one suite at a time locally, and drive the JS side through `npm test` so its `pretest`
hook actually stages the right content.

## A.10 Digital twin (hardware simulator)

`digital_twin/` fakes `machine`/`network`/`neopixel` at the same raw bus-transaction mocking
boundary `tests/machine.py` uses, but with real-time-firing `Timer`s and plausible sensor values,
so `src/sensortask_wozi.py` runs under the Unix-port interpreter and behaves like real hardware.
Independent of `tests/`; the swap is pure `MICROPYPATH` ordering. See `digital_twin/README.md`.

**Chain-completeness requirement, generalized beyond sensor drivers**: any new module joins the
digital twin, provided it can form a complete chain. A new sensor driver needs the C.11 point 9
checklist. A new common/base module wired into `build_system()`'s real object graph is
automatically exercised — no separate question for a module with no hardware surface. A module that
can't yet complete the chain stays out until the missing piece exists (flagged per CLAUDE.md).

**Automated CI suite** (`scripts/run_digital_twin_ci.sh`, `digital-twin-e2e` job): wipes leftover
twin state; builds the Unix port and the real production website (`scripts/build_website.sh wozi`);
`scripts/_digital_twin_ci_suite.py` drives `run_wozi_integration.py` through eleven subprocess runs
(fresh boot + every endpoint; settings persistence across reboot; a sustained fault matrix proving
graceful degradation and that the watchdog never starves under bounded failure; a
persistence-correctness sweep; recovery after a bounded fault clears; hotspot fallback with a real
answered UDP DNS query; NTP permanently unreachable; a real blocking hang proving the watchdog
backstop engages; a clean soak run). Building this surfaced three confirmed Unix-port-only `socket`
quirks (real, required behavior on real rp2 hardware, not a `src/` bug — BACKLOG.md has the
source-level account) worked around entirely from twin-side code
(`digital_twin/_unix_port_udp_addr_shim.py`).

---

# Part B — Toolchain & Build

One command sets up (or updates) everything needed to build MicroPython firmware for the Pico W:
MicroPython, a matching `pico-sdk`, a version-matched `picotool`, the ARM cross-compiler, plus a
host-side Unix port build for running tests under the real interpreter (E.1).

## B.1 Why not just "apt install the toolchain"

1. **The four pieces must agree exactly, or the build silently breaks** — `picotool` enforces a
   matching major.minor against `pico-sdk` since 2.0.0 ("Incompatible picotool installation
   found"), and `pico-sdk` must match whatever MicroPython's build compiles against (B.3 derives
   this instead of hand-tracking it).
2. **A dev machine's own tools/env vars could silently change the build output** — a stray
   `CFLAGS`, a shadowing `~/bin/cmake`, a different `picotool` — none should affect a reproducible
   build (B.4).

## B.2 Quick start

```sh
uv run toolchain/setup_toolchain.py                              # install/update per versions.toml
uv run toolchain/setup_toolchain.py --latest                      # pin + install newest stable
uv run toolchain/setup_toolchain.py --micropython-ref v1.26.1     # build a specific ref
uv run toolchain/setup_toolchain.py --clean                       # wipe + rebuild from scratch
uv run toolchain/setup_toolchain.py --skip-apt                    # skip apt-get install
uv run toolchain/setup_toolchain.py --jobs 4                      # override parallel make jobs
uv run toolchain/setup_toolchain.py --toolchain-dir /path         # default ~/pico-toolchain

uv run toolchain/setup_toolchain.py test                          # re-verify existing install, offline
```

`setup` is the default subcommand; `test` skips network/apt and re-verifies an existing install.
`--toolchain-dir`/`--jobs` apply to both; the rest are `setup`-only. `scripts/test.sh` exposes
`--skip-apt` as `SKIP_APT=1`. No venv needed — `uv run` provisions an ephemeral interpreter (B.8).
Both subcommands also build/verify a Unix-port interpreter, always with
`MICROPY_PY_SYS_SETTRACE=1` (inert when unused), so one binary backs both plain `scripts/test.sh`
and `--coverage` (E.5). RP2040 firmware never gets this flag.

**Prerequisites**: `sudo`; outbound network to GitHub/apt; `uv`; Ubuntu's `universe` component
(default on real Ubuntu images — `gcc-arm-none-eabi` lives there).

## B.3 How it works

1. Check out MicroPython at the pinned ref (`versions.toml`'s `[micropython] ref`).
2. Derive the matching `pico-sdk` version from MicroPython's own git submodule pin at
   `lib/pico-sdk`, rather than tracking it separately.
3. Derive the matching `picotool` version by resolving that commit to its nearest tag, taking
   major.minor, picking the newest `picotool` tag sharing it.
4. Install the ARM cross-compiler from `apt`'s `gcc-arm-none-eabi` (no pin needed).
5. Build inside an explicit, isolated environment (B.4).
6. Verify before declaring success, every run, via a frozen-bytecode chain (B.6): freeze a test
   module into both the Unix port and RP2 firmware, import it by name in the Unix port and check
   its result, clean up, rebuild a vanilla Unix port as the standing test rig.

Firmware/Unix-port builds always wipe first; `mpy-cross`'s build dir is left alone (relinks if
unchanged). `--clean` forces a from-scratch rebuild of everything without re-cloning. `test` is
`setup` with steps 1-4 skipped.

## B.4 Environment isolation

Every subprocess (`git`, `apt-get`, `cmake`, `make`, `picotool`, `mpy-cross`) gets an explicit,
constructed environment, never the caller's shell wholesale:

- **`build_env()`** (compile steps) — a fixed `PATH` plus a small allowlist (`HOME`, `USER`,
  `LOGNAME`, `TERM`, `TMPDIR`); everything else (`CC`/`CFLAGS`/`CMAKE_*`/`PICO_SDK_PATH`/
  `PYTHONPATH`/stray proxy vars) is dropped. `LANG`/`LC_ALL` forced to `C.UTF-8` (B.7.1).
- **`network_env()`** — the same base plus real proxy/CA vars, explicitly named. Used for
  `git`/`apt-get`, and for the rp2 port's `make submodules` (fetches over git *and* runs a
  preliminary `cmake` configure — needs both the deterministic `PATH` and network access).

`picotool`'s install location is pinned explicitly (`-DCMAKE_INSTALL_PREFIX=/usr/local`).

## B.5 Directory layout

```
<toolchain-dir>/          default: $PICO_TOOLCHAIN_DIR or ~/pico-toolchain
  micropython/             full clone at the pinned ref
    ports/rp2/build-<board>/    transient - removed after verification
    ports/unix/build-standard/  host-side interpreter build - the standing test-rig artifact
    mpy-cross/build/            cross-compiler build output
  pico-sdk/                full clone at the ref MicroPython pins
  picotool/                full clone at the derived matching tag; built + sudo make install'ed
```

Full (non-shallow) clones — shallow clones make the update path unreliable.

## B.6 Verification

Every run (`run_verification_sequence()`), each step gating the next:

1. Write a small test module (arithmetic, exception handling, stdlib import, a `RESULT` value).
2. Build `mpy-cross`. 3. Cross-compile the test module directly. 4. Build the Unix port with it
   frozen via `FROZEN_MANIFEST=`, zero warnings. 5. Import the frozen module by name in that
   binary, no source `.py` on disk — proves it was actually baked in. This is the host-side build
   tests run under (Part E). 6. Build the RP2 firmware with the same module frozen, zero warnings
   (build-only, no hardware here). 7. Clean up the RP2 firmware/Unix-port build dirs (keep
   `mpy-cross`/`picotool`). 8. Rebuild a vanilla Unix port — the standing test rig.

A completed run leaves no vanilla RP2 `firmware.uf2`; step 8's Unix port is the only kept artifact.

## B.7 Evidence this actually works

Verified end-to-end in a clean `debootstrap` Ubuntu 24.04 chroot for both the deployed `v1.26.1`
and latest stable; an in-place version update leaves no stale state; `test` alone completes in
~30s offline; both `setup`/`test` were run against a deliberately hostile environment (poisoned
`PATH`, garbage `CFLAGS`/`CMAKE_*`, non-English `LANG`) with zero poison surviving into the build.
See CLAUDE.md's "Pre-push verification" for the re-check recipe.

### B.7.1 GCC ≥14 host: mbedtls array-bounds workaround

`ctr_drbg.c` fails `-Werror=array-bounds` inside `mbedtls_xor()` on any GCC ≥14 host (confirmed on
Debian trixie, GCC 14.2) — a confirmed GCC false positive (Debian bug #1085354), fixed upstream in
mbedtls 3.6.6; this project's pinned MicroPython vendors an mbedtls commit predating that fix.
Worked around via `-Wno-array-bounds` in `_MBEDTLS_GCC14_ARRAY_BOUNDS_WORKAROUND` (both build
functions treat any warning as a hard failure). **Not yet fixed upstream** ([GCC bug
#121044](https://gcc.gnu.org/bugzilla/show_bug.cgi?id=121044) still UNCONFIRMED) — recheck its
status, and whether a future MicroPython ref vendors mbedtls ≥3.6.6, before removing this.

## B.8 Why not a full venv

Mostly apt packages/git trees/`cmake` builds, not `.venv` territory. The installer script's own
interpreter uses `uv run`'s ephemeral per-script environment — no `pyproject.toml`/`uv sync` step.
Source trees/build artifacts live in `--toolchain-dir`, outside this repo.

## B.9 Not yet covered

Proves the toolchain builds/cross-compiles/runs real Python. Does **not** yet wire up
`build-*.sh`'s hardcoded `/home/nico/rpi_pico/...` paths or the `py-include` symlink this project's
builds expect (BACKLOG.md). The Unix port build itself is wired into the test suite; the remaining
gap is the RP2040 firmware build.

## B.10 CI perspective

`.github/workflows/ci.yml`: `lint-and-typecheck` + `unit-tests` (`scripts/test.sh`, building via
`setup` on a cache miss). Cache key hashes **both** `versions.toml` and `setup_toolchain.py` —
keying on `versions.toml` alone once let a stale cached binary (built before
`MICROPY_PY_SYS_SETTRACE=1`) survive across commits, a real bug (`--coverage` failed in CI while
passing locally). No RP2040 firmware-build CI stage yet (BACKLOG.md).

## B.11 Building this project's firmware

**Bumping the MicroPython version**: change `versions.toml`'s `[micropython] ref` — the only place.
Everything else derives automatically: matching pico-sdk/picotool (B.3), the mypy type stubs
(`scripts/typecheck.sh`, failing clearly if no matching stub release exists yet), the Unix port.

Each legacy `build-<device>.sh`: assembles `python/build/` → swaps `modules/_boot.py`/
`sensortask-<device>.py` into upstream's `ports/rp2/modules/` → `make -C ports/rp2
BOARD=RPI_PICO_W FROZEN_MANIFEST=<path>` → copies `firmware.uf2` → restores `_boot.py`. Still
assumes `python/` is checked out as `py-include/python` alongside `micropython`, path not yet
genericized (BACKLOG.md).

**The `src/`-based build (parallel pipeline)**: `scripts/build_firmware.py <device> [--output
PATH]` assembles a real `firmware.uf2` from `src/` + `ext/microdot.py` + the real website (H) —
build-only. Every device needs its own `boot_entry/<device>_boot.py`.

**That entry point is frozen under the literal name `"main.py"`, NOT imported from a custom
`_boot.py` — load-bearing**, re-confirmed against pinned v1.29.0: `ports/rp2/main.c`'s boot sequence
is `pyexec_frozen_module("_boot.py", ...) → pyexec_file_if_exists("boot.py") → mp_usbd_init() →
pyexec_file_if_exists("main.py")` — USB initializes only *after* the frozen `_boot.py` call
returns. A custom `_boot.py` whose `asyncio.run(main())` never returns (this script's earlier
approach) means USB never initializes on a real hard reset — never a problem for a headless unit,
but a real gap for a bench harness expecting `board.hard_reset()` to yield a serial-observable boot
(documented rp2-port behavior, `micropython/micropython#15230`). Fixed: freeze the real entry
point as `"main.py"`, reusing the stock `manifest.py` unchanged. Confirmed working on real hardware
for `dev`; not yet re-confirmed for `wozi` (never physically flashed).

Every staged `.py` file is passed through `scripts/_strip_type_checking.py`'s
`strip_type_checking_blocks()` — an AST transform dropping each bare `if TYPE_CHECKING:` block
(with no `elif`/`else`) plus its `try/except ImportError` header, then `ast.unparse()`. `mpy-cross`
doesn't dead-code-eliminate `if TYPE_CHECKING:` the way it does `if micropython.const(0):`, so
guarded imports would otherwise survive into the `.mpy` bytecode as dead weight (~3.6KB measured).
Only the *bare* form is matched; a handler doing real work outside `TYPE_CHECKING` keeps its guard.
Only the staged temp copy is rewritten. Side effect: strips **every** comment from the file (not
just the targeted blocks — `ast.unparse()` never carries comments) — harmless for frozen firmware,
but an on-device traceback's line numbers won't match checked-in `src/`; re-derive via the same
strip.

`tests_scripts/` (CPython/pytest) covers the build tooling fast and offline;
`test_real_firmware_build_produces_a_valid_uf2` does the real end-to-end build (parametrized over
`wozi`/`dev`), gated behind `RUN_SLOW_FIRMWARE_BUILD=1`, run in CI's `firmware-build-verify` job on
every push/PR — closing the "no CI firmware-build stage" gap for this pipeline (legacy
`build-*.sh` stays open, BACKLOG.md).

**Production-readiness scope**: proves the build assembles and (via
`tests/test_digital_twin_real_website_integration.py`, H.7) that the booted twin serves the real
website — still build-only, not an on-device functional check.
`tests_hardware/flash/test_toolchain_flash_boot.py` (`--allow-flash-cycle`-gated) exercises real
output on real hardware, and on first run caught a real bug (an early manifest omitted
`ports/rp2/modules/rp2.py`, since fixed by reusing the stock manifest). This script's success is
necessary, not sufficient, for a real device to boot.

## B.12 Tiered dev-environment setup (`env` subcommand)

`toolchain/setup_toolchain.py env --tier {generic,flash,bench}`, each a strict superset of the last:
`generic` (Python/Node deps + the toolchain build), `flash` (+ real USB serial), `bench` (+ a real
WiFi bridge/AP so a flashed board reaches genuine internet/NTP, automating `dev_legacy/README.md`'s
manual `nmcli` recipe).

**USB device detection** reads `/sys/class/tty/<name>/device` for `idVendor=2e8a` across every
`ttyACM*`/`ttyUSB*` entry (not `lsusb`/`udevadm`, not guaranteed present). Exactly one match
required; zero or multiple is a hard error naming `--device` as the escape hatch, never a silent
guess.

**`bench`'s bridge/AP creation is idempotent** (`ensure_bench_bridge()`): recognized purely by
nmcli connection name (`br0`/`br0-eth0`/`br0-wifi-ap`), so a second run never recreates/
re-randomizes an already-configured bridge. A genuinely new bridge gets fresh random SSID/password
(`secrets`-generated) unless overridden, printed once at creation only. Uplink/WiFi-adapter
interfaces auto-detect the same "exactly one or hard error" way, only when actually creating a
bridge (checked via `bench_ap_exists()` first).

`run_project_dependency_install()` (`uv sync`/`npm ci`) runs with `env=None` (inherit the caller's
real environment) — the one deliberate exception to this script's isolation convention, since
`uv`/`npm` live wherever the host's own installer put them, never the fixed system-tool `PATH`.
`ip`/`nmcli` stay on the fixed `PATH` correctly; missing ones auto-install via `apt`.

**Local-test scope**: `generic` verified fully end-to-end in a cloud sandbox; USB/network
*detection* logic exercised for real where safe. Not exercised there: actually flashing a physical
board, or creating the bridge/AP (would disrupt the sandbox's own networking). **Full `flash`/
`bench` real-hardware verification is DONE** — both tiers run clean end to end on the real bench
Rpi4 (2026-09-04); see B.13 for the incident that interrupted the first attempt.

## B.13 Bench network safety: standing dead-man's-switch rule

**Standing rule**: any destructive test of the bench host's own network/access config (tearing
down a bridge, revoking `dialout`, anything that could cut the connection a session is using to
reach the host) must keep a recovery dead-man's-switch continuously armed for the entire risk
window — never touch live network state with none armed. One arm covering a whole atomic sequence
is equivalent protection to per-command re-arming, provided the sequence's real timing is measured,
not guessed. Confirmed the hard way on 2026-09-04: a one-shot recovery timer, consumed by an
earlier dry run, gave zero protection to the real run that followed, costing the bench Pi4's own
SSH access (recovered via SD-card edit of the wired-connection profile NetworkManager had
auto-suppressed once the bridge claimed the interface — normal NM behavior, not corruption).

**Second-order fix, now standing practice**: a Linux bridge synthesizes its own MAC (can shift over
its lifetime), distinct from the underlying interface's real hardware MAC — the router's static
DHCP reservation gets orphaned if it was keyed to a synthesized MAC that later changes.
`ensure_bench_bridge()` now pins `bridge.mac-address` to the uplink's real hardware MAC before the
bridge comes up on every fresh creation, and warns (never auto-repairs — cycling a live bridge's
MAC risks the same incident) if an existing bridge's MAC doesn't match. `dev_legacy/README.md`'s
manual recipe carries the identical fix.

**The recovery script, and the arm/verify/disarm pattern** — validated on a real successful run.
Recreate this script fresh in a session's own scratchpad each time (deliberately not a committed
file):

```bash
#!/bin/bash
# Idempotent teardown of whatever partial bridge state exists, restoring the known-good default
# wired profile. Safe to fire even if the bridge was never created or already torn down.
set -x
nmcli connection down br0-wifi-ap; nmcli connection down br0-eth0; nmcli connection down br0
nmcli connection delete br0-wifi-ap; nmcli connection delete br0-eth0; nmcli connection delete br0
nmcli connection modify "Wired connection 1" autoconnect yes connection.autoconnect-priority 0
nmcli connection up "Wired connection 1"
```

1. Confirm current state first (`ip -o addr show br0`, `nmcli -t -f NAME connection show`).
2. Arm immediately before the risky action, generously timed for the actual operation: `sudo
   systemd-run --unit=bench-recovery --on-active=<N> /bin/bash <script>`. Confirm armed.
3. Run the real operation.
4. **Poll for the real outcome immediately — don't go diagnose something else in between.** A
   bridge finishing `nmcli connection up` doesn't mean it's forwarding yet (a real run showed
   success in ~1s but no DHCP lease/default route until ~30s later, STP delay) — exactly the gap
   that let the timer fire on a working bridge once, because the operator diagnosed instead of
   checking. Use a short bounded poll, never a fixed sleep.
5. Once confirmed, disarm: `sudo systemctl stop bench-recovery.timer bench-recovery.service`.
   Confirm it's gone.

---

# Part C — Sensor Driver Architecture Specification

Extracted from the three drivers first promoted to `src/` (`asy_scd30_driver.py`,
`asy_bmp3xx_driver.py`, `asy_sgp40_driver.py`) plus shared infrastructure (`base_classes.py`,
`asy_i2c_driver.py`/`asy_spi_driver.py`, `config_manager.py`, `print_log.py`,
`system_service.py`). The shape a *new* driver should take; Part D is the separate "is it good
enough to move" checklist. Writing a new driver needs only this Part, the datasheet, and C.11.

## C.1 Layered architecture

```
sensortask-*.py               (per-device integration: wires Readers to REST routes, task supervisor)
*_Reader(SensorReader[Config]) (layer 3 - asyncio task/config/data-distribution; never raises)
*_I2C / *_SPI                  (layer 2 - chip protocol: registers/CRC/compensation; raises on failure)
I2CDevice / SPIDevice           (project-wide bus wrapper - not sensor-specific, never touched)
machine.I2C / machine.SPI      (MicroPython hardware bus)
```

A new driver adds layers 2-3 only (one file, `asy_<sensor>_driver.py`) plus a `_Reader` wiring
block in the relevant `sensortask-*.py`.

## C.2 File & naming conventions

CapWords classes, `lower_snake_case` public functions/methods, `_lower_snake_case` private ones. A
compound class name (sensor + role) keeps each half CapWords (`BMP3xx_Reader`, `SCD30_I2C`,
`FRAM_SPI`). Name-mangled (`__`) methods are reserved for when mangling itself is load-bearing —
`src/` has none. One permanent exception: `voc_algorithm.py`'s internals trace their DFRobot/
Sensirion source 1:1 (F.4), casing intentionally non-compliant.

One file per sensor. Within it:

- `_NAME = const("<SENSOR>")` — the dict key everywhere (`get_dict_data()`/`get_dict_cfg()`/
  `get_error_counter()`, every `err_s(_NAME, ...)`).
- `<SENSOR> = namedtuple("<SENSOR>", (...))` — measurement shape, ending in a `TS` timestamp field.
  Field names become `make_dict()`'s keys (C.6).
- **`_NAME`'s string and the namedtuple's type-name string must be identical, always** — define
  the two next to each other. A class with no namedtuple (`NeopixelDriver`) is exempt by
  construction.
- `_VAL_<ABBREV> = const((("<Field>", "<type>", default, min, max, special),))` — one schema tuple
  per config field (C.5).
- `<Sensor>_DeviceSession(Lockable)` — pure boilerplate, identical in all three drivers:
  ```python
  class <Sensor>_DeviceSession(Lockable):
      def __init__(self, i2c_device: I2CDevice) -> None:
          super().__init__()
          self.i2c_device = i2c_device
  ```
  Copy verbatim (swap `I2CDevice`/`SPIDevice`).
- `<Sensor>_I2C`/`_SPI` (layer 2), `<Sensor>_Reader` (layer 3). `*_Reader` constructor order (match
  exactly): bus handle, sensor-specific addressing/pins/callbacks, `trigger_sec: int = <n>` (only
  if configurable — SGP40 isn't, C.11 item 6), `max_module_error: int = 5`, then (if
  `SensorReaderConfig`) `cfg_path: str = ""`, FRAM param(s), `history_length: int = 10`,
  `debug: int | None = None`. **`max_module_error` is a generic failure-streak threshold, not
  I2C-specific** — `asy_wifi_service.py`/`asy_ntp_client.py` (no I2C) use it too via
  `_error_check()` (C.7).

## C.3 Layer 2: `*_I2C`/`*_SPI` protocol class

Owns one `*_DeviceSession` plus chip-specific cached state. **Pre-allocated scratch buffers are
required only for raw `write()`/`readinto()`/`writeto()`/`readfrom_into()` I/O** (sized once in
`__init__`, reused every call, D.4 — `SCD30_I2C`/`SGP40_I2C`). A class built entirely on
`I2CDevice.get_register_struct()`/`get_bits()` (`BMP3XX_I2C`) has no scratch buffer at all — those
helpers already allocate internally. This carve-out doesn't extend to a class that builds its own
buffers but still allocates fresh ones per call anyway — `FRAM_SPI`'s `_check_device_id()`/
`_read_status()`/`_send_opcode()` do this (a real, low-severity D.4 violation left as-is; every
call site already holds the relevant lock, so a shared-buffer fix would be safe if ever done).

**Contract: raises on any real failure — the layer that does not return sentinels.**

- A real bus/protocol failure — `OSError` (NAK/timeout/gone), a CRC mismatch, an out-of-range bit
  field — propagates as an exception (D.2's raw-bus-call carve-out).
- **This carve-out's fault surface is bus-specific.** `asy_i2c_driver.py` raises `OSError`;
  `asy_spi_driver.py`'s `write()` **cannot raise at all** on rp2 (no ACK/NAK, and the write-only
  path has no failure flag), while `readinto()`/`write_readinto()` can raise `OSError(EIO)` on a
  32+ byte RX overrun since MicroPython 1.29 (F.5.2). `write_readinto()` additionally turns a
  caller-input `ValueError` into `None`.
- `setup()` verifies identity (chip-ID register for BMP3xx, CRC-valid firmware version for SCD30,
  serial-number + self-test for SGP40) and raises if the sensor doesn't respond — fails loudly once
  at boot rather than degrading silently forever.
- A multi-transaction sequence that must not be interleaved holds the session lock for the whole
  sequence — `async with self.i2c_<sensor> as dev: async with dev.i2c_device as i2c: ...` — nested
  again if more than one bus transaction is needed (`SCD30_I2C.read_measurement()`). One continuous
  hold spanning an internal delay doesn't need the second nesting (`_read_dev_register`).
- Compensation/calibration math and datasheet operating-range checks live here — reject and raise
  rather than return an implausible value silently.

### C.3.1 SPI sensor variant — best effort, non-proven

No SPI *sensor* driver has been promoted yet — extrapolated from `asy_spi_driver.py`'s contract and
`FRAM_SPI` (a memory chip, so its write-enable-latch mechanics are FRAM/EEPROM-specific). Needs
extra datasheet/hardware scrutiny the first time used. General structure follows I2C; `FRAM_SPI`
itself doesn't split into two classes (extends `Lockable` directly) — either shape is fine as long
as both lock layers (C.8) stay genuinely distinct. What differs:

- **No bus-level presence probe exists for SPI, unlike I2C's zero-byte-write NAK check.** Identity
  verification must be a real, content-checked register read against the datasheet's documented ID.
- **Register/command framing is far more chip-specific than I2C's uniform shape** — this codebase
  has one real example (`FRAM_SPI`'s opcode-then-address-then-data). Check the specific datasheet;
  don't assume it transfers.
- **Write-enable-latch mechanics are FRAM/EEPROM-specific** — most sensor registers are plainly
  writable; don't build a latch step unless the datasheet documents one.
- Everything else (scratch buffers, session lock, compensation math, range checks) carries over
  unchanged.
- **`FRAM_SPI._setup_addr_buffer()` trusts caller-supplied `max_size` for address width (3 vs. 4
  bytes); `_check_device_id()` cross-validates it against the chip's reported identity.** Two real
  chips: `MB85RS64V` (8KB, `0x2000`) and `MB85RS2MTA` (256KB, `0x40000`, `datasheets/fram/
  MB85RS2MTA-DS501-00032-3v0-E.pdf` p.10). `setup()` raises `OSError` on a size/chip mismatch,
  `ValueError` on an unrecognized `max_size`. A genuinely new size needs its own table entry.

### C.3.2 UART variant — orphan module, harmonized precedent

`asy_uart_driver.py`'s `UART(Lockable)` is promoted/tested but has zero live callers (BACKLOG.md).
Settled precedent: **one merged class**, not a session+protocol pair (no bus-sharing concept, so
the two lock layers collapse without losing distinction — the accepted shape for any future
point-to-point wrapper); **CRC framing lives in the bus-wrapper class itself** (no natural layer 2
above a point-to-point link to own it instead); **`cancel_read_timeout()`** is a legitimate
externally-triggerable cancel for another coroutine's unbounded wait (a plain `asyncio.Event`
handshake); **raise contract** (re-verified against `ports/rp2/machine_uart.c` at v1.29.0): a
hardware framing/parity/overrun error is never raised — delivered corrupted, dropped, or skipped
silently instead, and `write()` can short-write — a third position distinct from I2C (raises) and
SPI (writes cannot raise; 32+ byte reads can, since 1.29 — F.5.2), already matched correctly (every
method returns a sentinel).

## C.4 Layer 3: `*_Reader(SensorReader | SensorReaderConfig)`

**Contract: never raises.** Every public method returns a sentinel on failure. Every layer-2 call
is wrapped in its own `try/except Exception`, logged via `err_s(_NAME, "...", e, errno=N)` (never
bare `except:`).

### C.4.1 `read_loop()` skeleton (identical across all three drivers)

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

Returning `False` is the task supervisor's restart signal. `_init_<sensor>()`: `await
self.pr.setup()` first, reset the internal error counter, then `try: await protocol.setup() except
Exception: err_s(..., errno=10); return False`; push stored config into the sensor here if
applicable. `_read_<sensor>()`: capture the timestamp first; on failure reset every field
(including timestamp) to `None` together and log. `_store_<sensor>()`: if any required field is
`None`, don't overwrite the cached reading; otherwise build the namedtuple (computing derived
fields via `math_helpers`) and call `_set_meas_data(...)`.

### C.4.2 Data-access contract (same 3(+1) methods, every driver)

```python
async def get_data(self) -> <Sensor>:                                            # cached last-good reading
async def get_dict_data(self) -> dict[str, dict[str, ...]]:                      # make_dict(await self.get_data())
async def get_dict_cfg(self) -> dict[str, dict[str, ...]]:                       # schema + optional live readback
async def get_error_counter(self) -> dict[str, dict[str, int | list[int] | list[str]]]:  # await self.pr.get_log(_NAME)
```

`get_data()` narrows `_get_meas_data()`'s generic return with an identity return + scoped
`# type: ignore[return-value]` (no runtime `cast()` on MicroPython, C.10 — the settled convention
over a local `cast()` shim or a field-by-field rebuild, since it needs no shim code and allocates
nothing on this hot path). `typing.cast()` still applies to narrowing a `struct.unpack()` result
before a non-`Any` return (`SCD30_I2C._read_dev_register()`).

### C.4.3 `SensorReader` vs. `SensorReaderConfig`

Pick based on where config values live: **`SensorReaderConfig`** (BMP3xx, SGP40) when values need
a locally-cached, file-backed schema (software-only knobs, or sensor settings that reset on
power-cycle). **Plain `SensorReader`** (SCD30) when every value lives in the sensor's own NVM —
`get_dict_cfg()`'s `callback` does all the work, no `ConfigManager` exists (A.4's `AmbPres` note).
Mixing within one sensor is fine: use `SensorReaderConfig` once any field needs local storage, omit
NVM-only fields from the schema and read/write them straight from the sensor.

**A `SensorReaderConfig` subclass whose field set isn't fixed at class-definition time needs a
different construction shape.** `NotificationCoordinator` defers `super().__init__()` until an
explicit `finalize()`, after `register()` calls assemble a combined schema at runtime — a
legitimate variant; everything else in C.4-C.5 applies once `finalize()` has run. **Every method
reachable before `finalize()` must guard against it explicitly** (a private `self._finalized: bool`
flag) — not just the two staging methods.

### C.4.4 `get_dict_cfg()`'s `callback` parameter

`_get_dict_cfg(name, cfg_vals, callback=None)` merges stored values with an optional callback's
live readback. Only pass `callback=` for a field with a real, independent live-sensor source of
truth (BMP3xx: 3 of 8 fields; SGP40: none; SCD30: all fields). **Second legitimate reason**:
sanitizing a sensitive value before it's ever returned — `asy_wifi_service.py`'s `callback=
self._mask_pw` unconditionally overwrites the persisted `PW` with a fixed mask.

## C.5 Config schema system (`config_manager.py`)

Each field is a 6-tuple: `(name, type: "int"|"float"|"str"|"bool", default, min, max, special)`.
`special` is a single sentinel value (an "unset" value outside the normal range, e.g. SCD30's
`AmbPres=0`; a field with `default=None` + a single-value `special` is "special-alone" — valid but
never written to disk, entirely sensor-managed) or a **discrete allowed-value set** (tuple/list,
for non-continuous legal values, e.g. BMP3xx's oversampling `1/2/4/8/16/32` — set `min`/`max` to
`None` for a pure enum, or combine both for a range plus bypass values). A schema constant
referenced inside another `const()`-wrapped tuple must itself be `const()`-wrapped — `const()` only
folds references to other `const()`-defined names.

One JSON file per sensor: `config_<name>.cfg`. Both `SensorReaderConfig.__init__` and
`ConfigManager.__init__` only stash constructor args; load/write happens once `setup()` is awaited
(C.13's readiness-gate pattern), cached in `self._cache`, re-synced to disk only by
`write_config()`. `ConfigManager` carries three defensive type-mismatch catches (`setup()`,
`get_dict()`, `write_config()`) as pure defense-in-depth (the REST layer's own validation already
guarantees clean input) — don't remove them, covered independently by
`tests/test_config_manager.py`.

**A real operational hazard**: constructing a `ConfigManager` with a schema narrower than the full
production one is dangerous — `setup()` treats any on-disk key not in the constructed schema as
invalid and silently drops it on rewrite. A one-off script touching one field must still construct
with the *entire* real schema, or every sibling field gets reset to its default.

Four typed accessors — `get_int_values()`/`get_float_values()`/`get_str_values()`/
`get_bool_values()` — return already-narrowed cache values for a key list; a new driver's getters
should use these directly rather than `isinstance`-checking `get_dict()`'s wider type.

### C.5.1 `get_cfg_schema()`

`SensorReaderConfig.__init__` captures `default_vals` as `self.cfg_schema`, exposed via a plain
sync `get_cfg_schema()` (no I/O, deliberately not `async`) and as a public attribute directly.
`NeopixelDriver` is the one class with no schema at all, so no `get_cfg_schema()` either.

### C.5.2 Setter dispatch (`_set_mgr_cfg`/`_set_dict_cfg`, `base_classes.py`)

`_set_mgr_cfg(data, cfg_vals) -> (bool, WriteValidity)` (`SensorReaderConfig`-only extension point;
SCD30 keeps hand-rolled setters) delegates to `cfgmgr.write_config(...)`. `_set_dict_cfg(data,
cfg_vals) -> WriteValidity` persists first, then pushes live only fields that both changed
(`"Valid"`, not `"Unchanged"`) and have a registered push callback; every field reports
independently including unrecognized keys; a whole-operation persist failure marks every requested
key `"Failed"`. **A push callback always receives the coerced, persisted value, not the caller's
raw one** — a type-checking callback would otherwise wrongly reject a coercible value like `45.0`
for an int field. `self._push_callbacks` is a plain `{field: async_fn}` dict populated per subclass
`__init__` (no central registry). **For an `int`-typed field, narrow with `type(value) is not int`,
not `isinstance`**, to correctly exclude `bool` (matches `type_or_range_error`'s own check); for
`bool`-typed fields the two are equivalent. **Every setter's return contract is uniformly `bool`**
(applied/rejected).

#### C.5.2.1 Command-only trigger fields (replaces legacy's `cmd_keys`)

A field validated/reported but never persisted (SGP40's `SGPResetVOC` → `reset_voc()`) reuses the
**special-alone field** convention on a `"bool"`-typed field: `_VAL_RESET = (("SGPResetVOC",
"bool", None, None, None, True),)`. Two existing behaviors give the right "repeatable trigger"
semantics for free: `"bool"` never inspects `special`, so both values are always valid; and a
special-alone write always reports `"Valid"` (no previous value to compare), so the push callback
re-fires every request. **Consequence**: `get_dict_cfg()` must keep its own narrower explicit field
list (excluding the special-alone field), since `ConfigManager.get_dict()` is all-or-nothing and
would `KeyError` on it. **A push callback's return means "push succeeded/failed"** — a setter whose
own return means something else (`reset_voc()`'s `False` = no-op, not failed) needs its wrapper to
report success unconditionally once the type check passes (SCD30's `ContMeas`, inverted, is the
other instance).

#### C.5.2.2 Failed-push recovery chain (replaces legacy's `set_sensor_value` fallback)

`_recover_failed_push()`, on any push failure, tries in order: a live getter read-back
(`self._get_callbacks`), the pre-write snapshot (`_set_dict_cfg()` snapshots before persisting), the
schema's own default. A getter's return is validated against its own field's schema — an
out-of-range readback falls through like a getter failure. The corrected value writes back through
`_set_mgr_cfg`, deliberately **not** through `_push_callbacks` (avoiding a retry loop on a
persistently-failing field). A command-only field is skipped entirely. The caller-visible status
stays `"Failed"` regardless of correction success — the repair is silent. `tests/
test_base_classes.py` covers every rung.

### C.5.3 Response envelope (`api_response.py`)

Replaces the old ad hoc pipeline. Wire shape: `{"res": "OK"|"ERR", "code": int, "descr": str,
"result": ...}`. `make_response(code, descr=None, result=None)` — a small standard catalog (`0`-`5`,
`100`) plus support for a fully custom pair. `parse_cmd_request(request, keys)` — body parsing +
`"cmd"` validation, decoupled from `microdot.Request`'s type via a local `Protocol`.
`handle_set_cmd(reader, data, cfg_vals, post_fct=None, post_asy_fct=None, ok_descr=None)` —
orchestrates `_set_dict_cfg()` plus one optional post-write hook (fires once per call, only if a
field actually changed). Build `data` from only the keys the client sent. A per-field failure never
demotes the overall response below `"OK"`/`0` — detail lives in `"result"`.

Two wire-format conventions: a field's wire name drops any redundant per-driver prefix
(`"BackupPeriod"`, not `"SGPBackupPeriod"`); every bool field is native JSON `true`/`false`,
replacing legacy's `"On"`/`"Off"` string dtype. Only legacy `html_raw/` isn't updated (H.1).

**A module whose single schema spans more than one REST route must narrow `get_cfg_schema()`'s
tuple per route** — `AsyConnTime` owns one schema but `/net/cmd`/`/led/cmd` each own only their own
subset (`sensortask-wozi.py`'s `_cfg_subset(schema, keys)`), or `setNetwork` would spuriously fire
`reconnect_wifi()` for an LED-only change and vice versa.

## C.6 Data model (`config_manager.py`'s `make_dict()`)

`make_dict(nt) -> dict[str, dict[str, ...]]` turns a namedtuple into `{<TypeName>: {field: value}}`
via `repr()`-parsing — not `_fields`/`_asdict()` (MicroPython's namedtuple provides neither).
**Known dormant landmine**: parsing splits on `"("`/`","` in the `repr()`, so a field whose *value*
contains one corrupts the result. Every current namedtuple is flat scalars only — check this first
if a new driver adds a list/nested-tuple field.

## C.7 Error handling & logging contract (`print_log.py`, `base_classes.py`)

`self.pr` is `PrintLogHistory` (in-memory) or `PrintLogHistoryStore` (FRAM-backed), chosen
automatically from the `fram` constructor argument. **Known pitfall**: a FRAM-backed history
survives everything except an explicit reset, including a reflash — before treating a persisted
`errcount`/history entry as evidence from *this* run, clear it first (`PUT /status
{"ResetErrors": true}`). The same fram-vs-memory branch is available standalone as
`make_logger(fram, history_length, debug, name)` for a non-`SensorReader` class
(`system_service.py`'s `SystemService`).

Log-level methods, two tiers: `pr.one`/`pr.evt`/`pr.all` (sync, print-only, no history) for
info/trace; `pr.err_s`/`pr.wrn_s` (async, persist to history/FRAM) for anything counting against
`get_error_counter()`; `pr.err`/`pr.wrn` (sync, non-persisting) for a genuinely sync call site
(e.g. a `Timer.init()` failure handler) or a routine observation that shouldn't count at all.

`errno=`/`wrnno=` are small positive ints, per driver, grouped by the raising method.
**`base_classes.py` reserves `errno=1`-`9`/`wrnno=1`-`2`**, inherited unmodified — a driver's own
numbering starts at 10+ (why `errno=10` = "init failed" recurs everywhere). **Three fixed common
slots after the base range, used only if applicable**: `10` = init failed (universal); `11` = the
driver's primary/periodic read failed; `12` = a persisted-config read at init failed (BMP3XX/SGP40
have it; SCD30 doesn't, `12` simply unused). Remaining errors renumber starting right after the
highest common slot used, preserving original relative order (C.7.1's table). **A driver with no
fixed, enumerable error-source list may assign numbers dynamically** (`system_service.py`'s
task-supervisor `wrnno=n + 1`) — stable within one run, not a fixed catalog.

`_error_check(results, condition=True) -> bool` is the shared consecutive-failure-streak counter
every `read_loop()` calls once per cycle — `False` (give up, restart) once the streak exceeds
`max_module_error`; decrements on a good read. `condition` lets a driver suppress counting a
non-sensor failure (SGP40's `condition=compensated`). **A call site with just one pass/fail flag**
passes a fixed one-element sentinel and drives the flag through `condition=`
(`_error_check((None,), condition=<flag>)`), not a ternary swapping the whole tuple.

A per-field get/set forward always logs via `err_s()`/`wrn_s()` on failure, never a bare
`except Exception: return None` — a transient bus fault on a REST-triggered get/set must stay
visible in error history. **An owned helper with no registered task/timer starter of its own may
still own an independent, uniquely-named logger** instead of sharing its owner's — `captive_dns.py`'s
`DNSServer` (owned by `AsyConnTime`) gets its own `"DNSSRV"` logger; aggregation happens at the
wiring level (`/status`'s `errcount`, A.8). **Silent-failure-masking convention: a teardown/cleanup
method on a class with no logger of its own must return `bool`, not `None`**, so its caller can log
the failure — `AsyUDPSocket.disconnect()`, `WebserverService._close_writer()`,
`UART.deinit()`.

### C.7.1 Running `errno`/`wrnno` table

Real numbers per module — each module's history stream is independent, so overlap *between* rows
is expected; only overlap *within* one row matters.

| Module | `errno` | `wrnno` | Notes |
|---|---|---|---|
| `base_classes.py` | 1-9 | 1-2 | Reserved base range — every driver starts at 10+. |
| `config_manager.py` (`CFGMGR_<name>`) | 1-14 | 1-6 | Sequential in source order. |
| `asy_fram_manager.py`/`asy_fram_driver.py` (`FRAM`) | 10-98 | 60-83 | `AsyFramManager` 10-88 (busy/idle status-byte helper spreads a base across 2-7 values per call); `FRAM_SPI` 89-98 (not-initialized ×5, invalid-range ×2, readback mismatch, lock-timeout, device-ID guard) + `wrnno` 81-83 (WRDI-stuck, WEL-didn't-set ×2). |
| `asy_bmp3xx_driver.py` (`BMP3XX`) | 10-22 | — | 10=init, 11=periodic read, 12=config read at init, 13=config write at init, 14=config read at store-time, 15-20=oversampling/filter forwards, 21=trigger-interval, 22=batched snapshot read. |
| `asy_scd30_driver.py` (`SCD30`) | 10-25 | — | 10=init, 11=periodic read, 12=unused (no init-time config), 13=stop-continuous-measurement, 14-25=per-field forwards. |
| `asy_sgp40_driver.py` (`SGP40`) | 10-18 | 10-14 | 10=init, 11=periodic read, 12=config read at init, 13-18=backup read/write/clear/deserialize/serialize/compensation. `wrnno`=backup missing/stale. |
| `asy_wifi_service.py` (`WIFI`) | 11-18 | 1-7 | 11=mode-switch...17=hardware give-up, 18=disconnect-timeout; `wrnno` 1-3=missing-config, 4-7=WLAN status. |
| `asy_ntp_client.py` (`NTP`) | 11-20 | 1-3 | 11=missing-config...19=time-calc, 18/20=interval-fallback/give-up; `wrnno`=callback failures. |
| `captive_dns.py` (`DNSSRV`) | 1-3 | 1-3 | 1=invalid server_ip/netmask, 2=loop exception, 3=disconnect-cleanup; `wrnno` 1=dropped reply, 2=invalid recvfrom, 3=socket teardown incomplete. |
| `system_service.py` (`SYSTEM`) | 1-6 | dynamic (`n+1`) | 4=task-error-budget-exceeded, 5=`_log_dead_task()` recovering a real raised exception, 6=recovering a `CancelledError`-ended task (previously invisible, now persists). |
| `asy_notification_service.py` (`NOTIFY`) | 10-13 | 1-5 | 10=value-callback, 11=threshold-config-read, 12=`local_time_callback`, 13=`request_signal_cb`. Renumbered off 1-4 once `_error_check()`'s active use here collided with base's reserved 1/2. |
| `api_response.py`'s `handle_set_cmd()` | 99 | — | One defense-in-depth catch (a caller `post_fct`/`post_asy_fct` raising) — fixed at 99 since it runs against any registered module's `.pr`. |
| `asy_webserver_service.py` (`WEBSERVER`) | 1-6 | 1-5 | 1=unexpected exception in dispatch, 2=`system_cmd` callback, 3=`notification_led` callback, 4=uncaught exception via `errorhandler(Exception)`, 5=`notification_pause` callback, 6=one `/status` streamed-fragment source failed. `wrnno` 1-5=connection-lifecycle reclaim reasons. |
| `asy_neopixel_driver.py` | — | — | No persisted logging. |
| `asy_i2c_driver.py`/`asy_spi_driver.py`, `asy_udp_socket.py`, `asy_dns_client.py` (client) | — | — | Deliberately no logging — every failure surfaces to exactly one upstream owner. Coverage audit closed, no gaps. |
| `asy_uart_driver.py` | — | — | Orphan module, no `self.pr` yet. |

## C.8 Concurrency & locking model

Two independent lock layers: **(1) Bus lock** (`I2C.async_lock`/`SPI.async_lock`, shared by every
device on that bus) serializes any single transaction against other devices sharing the bus.
**(2) Device-session lock** (`*_DeviceSession(Lockable)`'s own `asyncio.Lock()`) serializes a
multi-transaction sequence against another coroutine starting its own sequence on the same sensor —
without it, two coroutines could interleave and corrupt a shared scratch buffer even though each
individual transaction is already serialized by lock 1. Pattern: `async with self.i2c_<sensor> as
dev:` (lock 2) wrapping `async with dev.i2c_device as i2c:` (lock 1). **Lock ordering is fixed:
always 2 before 1** — audited across every driver with no violation; reversing risks a real
deadlock.

**Known inconsistency (`asy_wifi_service.py`)**: `network_available()` requires the *caller* to
already hold `wifi_mode_lock`, while its sibling getters assume the caller does *not* — already
caused one since-fixed bug (`get_dns_server_ip()` always `None`); left as-is, but a new getter
should pick a contract deliberately. Separately, the 60s STA-retry branch holds `wifi_mode_lock`
while NTP's sync task waits on it — an accepted priority-inversion cost, not a bug.

**Known structural gap, accepted risk (`SGP40_I2C._reset()`)**: `writeto(0x00, b"\x06")` is a true
I2C **general-call broadcast** resetting all devices on the bus — neither lock layer protects a
sibling device, and this fires on every SGP40 task-supervisor restart. **Low-risk, not fixed**:
neither sibling's datasheet documents general-call listening, and address `0x00` gets no special
handling in the pinned rp2 `machine_i2c.c` (an unacknowledged broadcast just times out/NAKs like
any unaddressed write, already handled). A real-hardware regression test exists
(`test_sgp40_general_call_reset_does_not_corrupt_a_concurrent_scd30_transaction`). The only
structural fix (a bus-wide "quiesce every session before broadcasting" mechanism) is flagged for a
project-owner decision if ever revisited, not justified without evidence of a live risk.

**Standing rule — bus-hazard test coverage, read before adding a new bus-facing device or rewiring
a bus (project owner's explicit standing direction)**: every promoted I2C/SPI device gets
same-device read-vs-write concurrency coverage, cross-device interleaving coverage (if sharing a
bus), and an address/command sweep, across as many of four tiers as apply (cheapest first):

1. **Mock/unit** (`tests/test_bus_hazard_multi_device.py`) — byte-exact wire-log proof, plus the
   full address/command sweep.
2. **Digital twin** (`tests/test_digital_twin_bus_hazard_concurrency.py`) — the real object graph
   against higher-fidelity chip fakes under genuine concurrent task load.
3. **Flash tier** (`tests_hardware/flash/test_bus_concurrency.py`) — real hardware, dev bench only.
   **Real-hardware write-safety constraints, project-owner-mandated**: (a) respect any real
   NVM/EEPROM write budget — ideally at most one real write per bus-hazard test group, via a
   session-scoped fixture; (b) a concurrency test exercising persisted config must construct the
   real protocol-layer driver directly (the DUT), never the `*_Reader` layer, so it never touches
   the RP2040's own flash filesystem.
4. **Bench tier** (`tests_hardware/bench/test_bus_concurrency_under_api_load.py`) — real hardware,
   full HTTP stack, concurrent load. Extend the worker set only with requests safe under both
   constraints above (`GET` always safe; `PUT` only if documented command-only/never-persisted).

## C.9 Timer/task/IRQ integration contract

Every `Reader`/service exposes `get_task_starters()`/`get_timer_starters()` (even trivially
one-element) — `system_service.py` discovers/supervises every driver generically through these,
never by name. **This is the boot-time-lifecycle mechanism, not the only legitimate way to start a
task** — a task tied to a runtime mode transition (`asy_wifi_service.py`'s hotspot-mode DNS server
task) is deliberately outside this generic supervision, a legitimate opt-out.

Periodic reads use `machine.Timer` (default **soft**, no `hard=True` anywhere) whose callback only
calls `.set()` on an `asyncio.ThreadSafeFlag` — never `time.sleep()` or business logic inside a
callback. **Use `Timer.PERIODIC`, not `ONE_SHOT`, for anything that must keep firing** — a soft
callback can be silently dropped if MicroPython's fixed-depth scheduler queue is full (F.1); a
periodic timer self-heals next tick, a dropped one-shot never fires again. A driver needing more
than one rate (BMP3xx: 1Hz base tick divided down) runs a small counting sub-task rather than
reprogramming the Timer's period at runtime.

**Every `Timer.init()` failure handler catches `except (OSError, MemoryError) as e:`, not bare
`OSError`** (F.1) — its documented failure is `OSError(MP_ENOMEM)` on alarm-pool exhaustion; no
separate `Timer.init()`-specific `MemoryError` path exists, but the widening is correct generic
insurance regardless.

**Cascading-recovery-storm convention: a retry loop that fails non-raising (returns a sentinel)
needs its own capped exponential backoff**, distinct from any outer exception-based backoff, or it
spins at full speed — an outer `except Exception` never fires for a sentinel-returning failure.
`captive_dns.py`'s `DNSServer.run()` now backs off 0.5s→1s→2s→4s (capped 5s, reset on success) on
persistent `recvfrom()` failure — before this fix, a persistent failure produced ~5 log lines/sec
continuously. Contrast `asy_ntp_client.py`'s already-bounded retry (3 tries, 15s interval, then lets
the supervisor restart) — a new retry loop should follow one of these two shapes.

## C.10 Typing conventions

`TYPE_CHECKING` guarded via `try/except ImportError: TYPE_CHECKING = False`, never unconditional.
PEP 604 `X | None` everywhere, never `typing.Union`. A caller-supplied object touched only
structurally gets a `Protocol` fully inside `if TYPE_CHECKING:` (`print_log.py`'s `_FramChunk`/
`_FramManager`, `api_response.py`'s `_RequestLike`, `asy_wifi_service.py`'s `LEDControl`).
`typing.cast()` has no runtime presence (C.4.2). A driver-local `*Results` tuple-of-optionals alias
is declared under `TYPE_CHECKING`, used only as `_read_<sensor>()`'s return annotation — a plain
tuple, not `NamedTuple` (internal, not the public model, C.6).

## C.11 Design decisions a new driver must make (datasheet + judgment, not precedent)

1. **Bus**: I2C or SPI (C.3.1 for SPI — best-effort/unproven).
2. **Identity check**: chip-ID register, firmware-version CRC, serial-number + self-test, per the
   datasheet's documented mechanism.
3. **Config location**: sensor NVM (live readback only) vs. software-only/volatile (schema, C.4.3)?
4. **Derived fields**: `math_helpers`-style computation needed, and the formula's source/domain
   (D.1)?
5. **Operating-range validation**: protocol layer (no CRC, a bit-flip is otherwise undetectable) vs.
   relying on CRC/self-test alone?
6. **Trigger rate**: fixed (SGP40 needs exact 1Hz) or user-configurable?
7. **FRAM/persistence needs**: state worth surviving a reboot beyond generic error logging
   (SGP40's VOC-algorithm backup is the only, and largest, current example)?
8. **Errno/wrnno numbering**: sequential, grouped by method, reusing `errno=10` for "init failed"
   (C.7).
9. **Digital-twin extension — required, not optional.** A matching chip fake under `digital_twin/`
   (`_<name>_chip.py`, same shape as the existing three), wired into `machine.py`'s bus maps, plus
   `tests/test_digital_twin_<name>.py` (`digital_twin/README.md`'s "Adding a new chip fake"). A new
   SPI sensor sharing an already-occupied SPI bus id with the FRAM chip is **not** automatically
   supported by the twin's single-device-per-bus-id wiring. Do this the same session as promotion —
   a driver with no twin counterpart silently regresses the Unix-port integration run's coverage
   (A.10). **Also update `html/definitions/<device>.json`** for every device the driver's fields
   should appear on (H.5) — the website comes entirely from that file, so a driver with no
   definitions-file entry stays invisible indefinitely. Same session, not deferred.

## C.12 Testing

Covered fully by Part E.4: mock `tests/machine.py`'s raw bus transactions only, letting real logic
(bit-packing, CRC, locking, error paths) run against a dict-of-registers fake. D.12's
parameter-combination/boundary/NaN-inf coverage applies to any pure computation helper a new driver
adds. For I2C fault injection: real hardware only raises `OSError(EIO)` or `OSError(ETIMEDOUT)` —
never `ENODEV` (`SoftI2C`-specific).

## C.13 Readiness-gate scheme (sync `__init__` / async `setup()`)

Project-wide pattern for a class whose construction needs an `await` but starts inside sync
`__init__` (proven first by `FRAM_SPI`/`SPIDevice`; standard for `ConfigManager`,
`NotificationCoordinator`'s staged variant). `__init__` only stashes args and sets a readiness gate
to "not ready"; `async def setup()` does the deferred work and flips it. **Gate name/polarity is
standardized**: `self.initialized: bool = False → True` — except where the meaning is genuinely
different (`ConfigManager.valid` means "setup ran *and* produced trustworthy data," a real
distinction). A `Type | None`-typed attribute is the complementary mechanism for a sub-resource
that can independently fail *during* setup (`PrintLogHistoryStore.fram`) — both can coexist.
**The response to "called before `setup()` ran" must match the class's already-declared
raise/never-raise contract** — verify per class, don't assume from the last example read (a
"never raises" class returns its sentinel and logs, even `FRAM_SPI`; `SPIDevice.__aenter__`'s
raise is a structural necessity of `async with`, not a precedent extending elsewhere). **Not every
readiness question needs a gate** — `AsyFramManager.get_chunk()` is pure bookkeeping, safe before
`setup()`; add a gate only where construction genuinely has an unready window.

---

# Part D — `src/` Production-Quality Checklist

Files land in `src/` once they clear this bar in full (CLAUDE.md). "Production quality": correct
against real documentation, never raises an uncaught exception, safe unattended indefinitely,
respectful of RP2040's limited resources, never blocks, always returns a well-defined value. For a
new sensor driver, see Part C first for the shape; this checklist is how you know it's good enough.

## D.0 Understand the function's purpose first

Read it alongside its callers and existing comments before judging correctness — "mathematically
consistent" isn't "does what it's meant to." If purpose/domain/expectations are genuinely unclear,
ask up to 10 targeted questions rather than guess.

## D.1 Correctness, verified against real documentation

Identify the authoritative source for every non-obvious claim and verify against *current* sources
— never training memory; note it in a comment. Verify coefficients/sign/order/units actually match
— don't assume deployed code is correct. **If verification surfaces a discrepancy, do not silently
change it** — flag and ask before altering real output. Verify the coded validity range matches the
source's *actual* domain, not whatever the code already had (found: `wet_bulb_temperature`'s
humidity lower bound was `0.5%`; Stull (2011) only validates to `5%`). Where a formula's domain is
wider than its use, cross-check against the real caller's hardware constraints instead
(`altitude_baro`'s range comes from the BMP388/390 datasheet, not the formula). Look specifically
for functions with **no validity range check at all**. A genuine quirk found on review (not a bug)
gets a comment and a regression test matched to *measured* behavior, never a guessed fix.

## D.2 No uncaught, unhandled exceptions

Every function returns a "no data" sentinel — **never raises, under any input** — for missing
input, out-of-domain input (a guard clause before computation), and any residual computational
failure (wrap only the computation, catch specific types, never bare `except:`). **Don't defend
against out-of-contract input at runtime if static typing already enforces it (mypy)** — dead
weight for a scenario that can't occur. Do verify `NaN`/`inf` (real sensor faults can produce them)
degrade cleanly through range checks — confirm, don't assume, and test it. Walk the function line
by line to confirm the exception net is complete. **Specialty: raw hardware bus-transaction calls
are the one deliberate exception to "never raises"** — a real `OSError` is allowed to propagate out
of a low-level bus driver; verify every upstream caller actually catches what it can raise. **The
`OSError` surface differs per bus, so check the specific one** — I2C raises broadly; SPI raises
only from a 32+ byte read (F.5.2), never from a write; UART never raises from a transfer at all.

## D.3 Stability for indefinite, unattended operation

Units run years without a reboot: no unbounded growth; no retained state unless deliberately
stateful (prefer pure functions); no resource acquisition without a guaranteed release on every
exit path, exception paths included. Verified via design discipline and reading — no CI gate for
"ran a simulated year."

## D.4 Resource discipline for the RP2040 target

Dual-core Cortex-M0+ @ up to 133MHz, 264KB SRAM (F.1): avoid unnecessary allocations in anything
called frequently (reuse buffers); avoid recursion/large intermediates; prefer the cheaper stdlib
call (`math.sqrt(x)` over `pow(x, 0.5)`); don't add runtime type checks "just in case" (D.2).

## D.5 Never block

No blocking I/O, `time.sleep`, or unbounded loops. Anything genuinely needing I/O must be `async`
and yield appropriately, never stalling timing-sensitive work like the Neopixel animation (F.3).

## D.6 Typing

Type-hint every parameter/return. Verify annotation syntax is safe on the target runtime against
*current* docs (`X | None` is parsed but never evaluated at runtime, confirmed on every MicroPython
version checked). Not over/under-typed. Typing-only utilities beyond plain annotations (`TypeVar`,
`Protocol`, `TYPE_CHECKING` itself) go behind `if TYPE_CHECKING:` with a `try/except ImportError`
fallback — `typing` isn't importable at all on the Unix-port test interpreter. **`mpy-cross` does
not dead-code-eliminate `if TYPE_CHECKING:` blocks** the way it does `const(0)` — the guard is still
correct/required; stripping these from the frozen build is `build_firmware.py`'s job (B.11), not an
individual file's own concern.

## D.7 Always-defined return values

Every code path returns explicitly, matching the declared type — no implicit `None`, no
partially-initialized variable reaching `return` on some path but not others. mypy catches most of
this — still read every `return` by eye for something technically valid but semantically wrong (a
clamp that silently clips instead of signaling invalid).

## D.8 General improvement pass, without changing functionality

Look for genuine improvements (speed, resources, accuracy, complexity) as long as observable
behavior stays identical for every valid input — a hard constraint, the full test suite must still
pass unchanged. A genuine pass, not a mandate to rewrite for style.

## D.9 Check against current MicroPython, not the version this code predates

Much of this codebase predates MicroPython 1.20; the build target has moved to the latest stable
(currently v1.29.0 — the last pass's findings are catalogued in Part F.5). Check the changelog between whatever the code targeted and the current pin for
relevant changes — note findings even when nothing needs to change. Look for old `u`-prefixed
module names (`uasyncio`, `ustruct`) — a clear tell of pre-consolidation code. Same "without
changing functionality" constraint as D.8 for a pure modernization; a genuine semantic difference
(not just a rename/speedup) is a D.1-style behavior change — flag and ask.

## D.10 API consistency, within a file and across the project

Give every member of a related set the same shape (parameter names/order/optionality/return
convention), even where one member's shape looks locally unnecessary (`crc_checks.py`'s
`CRC_Pass`/`CRC8`/`CRC16`/`CRC32` all take `poly:` even though `CRC_Pass` never uses it, so a
dispatch table can treat all four identically). Prefer forwarding through a shared base and
relying on its invariants over hardcoding a special case. Check how comparable code elsewhere
already expresses the same thing and match it — flag a questionable existing convention rather than
silently diverging. An ongoing, project-wide check.

## D.11 Readability / conciseness

One-line "why" comment per function citing the formula's source/domain (D.1). Per-function
explanations are `#` comments, never docstrings mixed into an individual function. State a shared
contract once at module level rather than repeating it per function — applies across files too.
Consistent control-flow order: `None`-check, range-check (plain guard), then `try`-wrapped
computation. **Keep documentation itself concise — a module docstring is a short header, not an
essay.** A permanent design fact belongs in CLAUDE.md/this document; an open question belongs in
BACKLOG.md. Inline comments stay within **3 lines, prefer fewer**.

## D.12 Unit tests

Run under the real target interpreter (Part E), not "whatever's convenient." For every function,
cover each parameter individually **and interacting combinations**: `None` for each input
individually and combined; a valid typical input against a **sanity bound**, not an exact reference
value; just-out-of-range on each side of every bound; the exact boundary values *accepted*; `NaN`
and `±inf` on every argument; any formula-inherent quirk (D.1) as a bounded regression; physical/
logical invariants where they exist. Do **not** test scenarios the type system already rules out
(D.2). **If this file is one layer in a larger real call chain**, module-level tests mocking only
the raw bus transaction aren't enough — add integration tests driving the same scenarios through
the actual real chain to the real consumer.

## D.13 Wire into the existing pipeline

Extend the lint/typecheck config's scope and CI's explicit path arguments to the new location. Add
the file's tests to the existing test-runner script.

## D.14 Verify, don't assume

Actually run lint/typecheck/tests and read the output after every change — don't report success
without having done so. Diff the finding count before/after against untouched files.

## D.15 Method ordering within a class

Private (`_`-prefixed) methods first, then public. Within each group, order by role (omit empty
categories): 1. Starters (`start_*`/`stop_*`/`get_*_starters` — `stop_*` pairs a task/timer-lifecycle
stop with its `start_*`, not any method merely named "stop"), 2. Getters, 3. Setters, 4. Others.
`__init__`/dunders always stay first. A pure reorder — no change to any body/decorator/comment/
module-level statement, verified via an AST-level comparison, not just a visual diff. Existing
tests must pass unchanged; lint/typecheck finding counts must match the pre-reorder baseline.

## D.16 Only then

Move the file into `src/`, only once all of the above is actually done and passing.

---

# Part E — Testing & Coverage

Unit tests for `src/`. Get the current count with `ls tests/test_*.py | wc -l` and `grep -c
'^def test_' tests/test_*.py` rather than a fixed number here.

## E.1 Why not pytest

Tests run under a **real MicroPython interpreter** (the Unix port), not CPython plus
MicroPython-flavored stubs. `scripts/test.sh` shells out to a built Unix-port binary directly, once
per `tests/test_*.py`, and checks its exit code. `pytest` stays in the dev dependency group for
possible future CPython-side orchestration; nothing uses it yet.

## E.2 Test framework

`microtest.py` is a minimal collector/runner (find every `test_*` function, call it, report
PASS/FAIL, exit non-zero on failure) — not CPython's `unittest`, unavailable on the Unix port's
"standard" build. Plain `assert`.

## E.3 Running

```
scripts/test.sh
```

Builds the Unix port on first run (via `setup`, Part B, cached under `$PICO_TOOLCHAIN_DIR`).
`SKIP_APT=1 scripts/test.sh` skips the first-run apt-get install. To run one file directly:

```
MICROPYPATH="src:tests:frozen_modules:.frozen" ~/pico-toolchain/micropython/ports/unix/build-standard/micropython tests/test_math_helpers.py
```

`.frozen` is required in `MICROPYPATH` because it replaces the interpreter's default `sys.path`
rather than extending it, and the default path is what makes frozen-in modules (`asyncio` included)
importable. **`.frozen` is a literal MicroPython sentinel, not an ordinary directory** — any path
starting with `MP_FROZEN_PATH_PREFIX` routes to the compiled-in frozen table, never the real
filesystem. `frozen_modules` is a separate, ordinary, gitignored directory (A.9's output) needed
too, since `sensortask_wozi.py`'s `import frozen_html` needs it.

## E.4 Hardware-touching files: mock at the raw bus-transaction level only

`tests/machine.py` is a fake `machine` module (the Unix port's real one has no `I2C`/`SPI`/real
`Pin`), mocking only raw bus transactions (`readfrom_mem`/`writeto_mem`/`readfrom_into`/`writeto`/
`scan`/`deinit`), backed by a real dict-of-registers store — the driver's own logic (bit-packing,
locking, error paths) runs for real against it. `tests/test_print_log.py`/`test_base_classes.py`
apply the same boundary for FRAM: real `AsyFramManager` against `tests/_fram_chip_fake.py`'s
simulated MB85RS64V. "Survives a reboot" is proven by constructing a second `AsyFramManager`
pointed at the same fake chip and replaying the same `get_chunk()` sequence — genuinely
round-tripping the real dual-copy+CRC format. Two Protocol-level failure scenarios (`get_chunk()`
raising) have no real-class equivalent anymore (the real class is audited never to raise there) —
proven via a minimal local raising fake instead, defense-in-depth against the Protocol contract in
the abstract. This caught a real gap during `print_log.py`'s review: `_write()`/`_read()` called
buffer methods *before* their `try:` block started — fixed by widening both to cover the whole
body.

## E.5 Coverage

```
scripts/test.sh --coverage
```

Reports `src/` line coverage only. No threshold enforced anywhere — CI reports numbers, never
gates. `coverage.py` only runs under CPython while `src/` only runs under the Unix port, so
collection and reporting are two stages: `tests/_coverage_runner.py` runs *inside* MicroPython via
`sys.settrace`, recording every executed line under `src/` and dumping JSON;
`scripts/_render_coverage.py` (CPython) merges the dumps, feeds them into `coverage.py` via
`CoverageData.add_lines()`, and renders HTML/XML/markdown. Produces (gitignored, at repo root):
`htmlcov/index.html`, `coverage.xml`, `coverage_summary.md`. Locally nothing opens automatically. On
GitHub: `coverage_summary.md` appends to the run's Job Summary; `htmlcov/` uploads as a downloadable
artifact; `coverage.xml` uploads to Codecov, but that account-linking hasn't been done, so it
currently no-ops silently.

### E.5.1 Reading the numbers: three systematic false-negative patterns, not missed test cases

`micropython.const(...)` assignments are compiled away entirely, so the line never fires a trace
event and always shows a 0-hit miss despite being fully "exercised." A decorated function's traced
event lands on the decorator line, not the `def` line, so every `@staticmethod`/`@classmethod`
shows missed even when called throughout the suite. A bare `while True:` header never fires its own
trace event at any iteration (folds into an unconditional jump at compile time).

Separately (not a tracer artifact, also not a missed-test hint): several `except` branches guard
against outcomes provably unreachable given guarantees the same function already establishes
before them (`crc_checks.py`'s masked-CRC guard, `math_helpers.py`'s domain-guarded blocks) — left
as documented dead code rather than chased for a coverage number. `print_log.py`'s `get_log()` has
the same shape from an `if`: it treats two sentinels as equivalent "nothing recorded" markers, but
only one is actually reachable — **confirmed intentional by the project owner**, kept for
defensive symmetry.

## E.6 Shared behaviors and the real-hardware test tier

**`tests/_shared_rest_roundtrip.py`** holds the two genuine near-duplicate assertion *shapes* found
scanning mock against twin ("every long-lived module got constructed," "a GET payload isn't
self-wrapped" — regression coverage for A.8's `.update()` bug); every other REST-round-trip pair
scanned was either too structurally different or too trivial to be worth sharing (E.6.5) — don't
force further sharing onto genuinely backend-specific coverage.

**`tests_hardware/`** — a top-level tier for tests needing real RP2040 hardware over `mpremote`
(flash tier) and/or a real WiFi bridge (bench tier, a strict superset of flash), under CPython/
pytest orchestrating `mpremote`/`nmcli`/`iptables`. `tests_hardware/manual/` (never collected by
pytest) holds tests needing a human's hands, kept structurally apart so an automated pass never
silently stalls waiting on one.

**Real-hardware execution is standing practice**, on the bench Pi4, always under the project
owner's go-ahead given directly in the running session (CLAUDE.md). Both tiers run clean end to end
on real hardware; the earlier WiFi-reconnection flakiness this section used to flag is root-caused
and mitigated (`tests_hardware/README.md`'s "Known assumptions and open findings"). Lint/type-check
scope does **not** extend to `tests_hardware/` (matching `tests_scripts/`'s own non-scoping).

### E.6.1 The five-backend model

| | **mock** | **twin** | **flash** | **bench** | **manual** |
|---|---|---|---|---|---|
| Executes on | Unix-port, `tests/machine.py` fakes | Unix-port, `digital_twin/` fakes (real asyncio graph) | real RP2040, USB serial | real RP2040, USB + real WiFi bridge | rides on flash or bench |
| Fault injection | synthetic, in-process | synthetic, higher-fidelity, same interface shape | none | real (bridge host: AP down/up, `iptables`, credential rotation) | a human closes the loop |
| Proves | raw bus byte/frame correctness, schema boundaries, NAK/CRC error paths | realistic stateful/concurrent/timing/persistence behavior of the whole system | real timing, WDT reset, Timer/IRQ, flash/littlefs persistence, BOOTSEL | real lwIP/WiFi transport, real fault-injected scenarios | unplug/replug, genuine power loss, a real second device joining a hotspot |

`bench` ⊇ `flash` (same board, same one-time flash). `manual` is an execution *mode*, not a tier.

### E.6.2 Shared behavior catalog + per-backend capability adapters

The general pattern behind `_shared_rest_roundtrip.py`: pull only backend-agnostic claims into a
shared layer of plain functions taking a small explicit capability object (a `driver_factory()`, an
`http_client`, a `reboot()` callable, a `raise_on(...)` fault-injection callable) rather than a raw
driver. Each backend supplies just that narrow adapter, never a reimplementation — mock constructs
in-process; twin drives via `digital_twin/_http_client.py`; flash/bench isolated-driver uses one
generic `mpremote run`-backed mechanism; flash/bench live-system uses a real HTTP client mirroring
the twin's interface closely enough to run the same shared test body by swapping the client object;
bench fault-injection is the real equivalent of the twin's synthetic surface (`flash` has no
adapter here, correctly — no bridge to control). What stays out: mock's raw byte/frame assertions,
twin's persistence/IRQ/random-walk behavior, real-hardware-only electrical/timing checks.
Documentation discipline (each shared function's docstring states applicable/N/A backends), not an
automated check.

### E.6.3 Real-hardware harness: honoring "no extra flash cycles"

The one allowed flash puts the real, unmodified production UF2 on the board — never a
test-instrumented build. After that: **live-system mode** (the board runs normally, tests interact
only through real external interfaces — where almost every bench test lives) or **isolated-driver
mode** (`mpremote run <script>` interrupts into the raw REPL to exercise the real frozen driver
modules directly, then a soft reset restores normal operation — free/unlimited, the constraint is
about *flashing* only). **One load-bearing exception**: a trailing soft reset only restores the
*appearance* of normal operation — it doesn't resume a specific live system state a test depends on
(e.g. the already-running `main.py`'s own WiFi task); only a genuine `hard_reset()` reliably
resumes the live system.

### E.6.4 Hotspot role-reversal (bench, single-radio)

The RP2040's own hotspot/AP mode is untestable in the digital twin (no AP-mode DHCP/second-radio
model). `tests_hardware/bench/test_hotspot_role_reversal.py` closes this on real hardware: the
bench rig's one radio temporarily becomes a *client* of the DUT's own hotspot, then flips back —
sequential, safe because of a real, source-traced ~15-20s timing budget from a credential PUT to
the DUT's first STA attempt, comfortably inside a scripted `nmcli connection up`. **Load-bearing
finding**: by the scenario's last stage the DUT has necessarily been in hotspot mode since stage 0,
so a failed real-credential PUT lands in `_PHASE_DEACTIVATED` (a terminal state, A.4) rather than
falling back to hotspot — hence the fixture's real `hard_reset()` fallback if the reachability wait
times out. The hotspot's SSID/password are fully deterministic, needing no scan/discovery.

### E.6.5 Mock vs. digital-twin: overlap scan

Six subsystem pairs scanned in full: BMP3xx, SGP40, FRAM (166 mock vs. 18 twin tests), Neopixel/
WiFi, Webserver, Sensortask each found complementary, with only small pockets of intentional or
low-value duplication — one real cluster (Sensortask: 4 near-identical "same REST round-trip, once
direct, once over real HTTP" pairs) is the cluster `_shared_rest_roundtrip.py` targets.
Consolidation should target that specific shape, not force uniformity onto pairs already correctly
complementary.

---

# Part F — Platform Target & MicroPython Runtime Facts

## F.1 Core platform facts

Deployed units run **MicroPython 1.26** on **Pico W (RP2040)**; code ships as **frozen bytecode**,
not loaded from a filesystem at runtime — CPython-only stdlib behavior cannot be assumed. The
refactor pins **v1.29.0** (`toolchain/versions.toml`) and targets whatever's most recent stable at
the time, using new features, not just reproducing 1.26-era behavior. F.5 catalogs what 1.29
changed for this codebase. MicroPython 1.26 bundles pico-sdk 2.1.1;
since pico-sdk 2.0.0, a standalone `picotool` must match its major.minor or the build fails.
`machine.WDT` hard-caps at **8388ms**; current code uses `WDT(timeout=8000)` (388ms margin) — don't
casually increase without re-checking the cap. **USB (`mp_usbd_init()`) initializes only *after*
the frozen `_boot.py` returns** — a `_boot.py` that blocks forever means USB never initializes on a
real hard reset (B.11). RP2040: dual-core Cortex-M0+ @ up to 133MHz, 264KB SRAM, 2×I2C, 2×SPI,
2×UART, 8×PIO. Pico W's littlefs partition (~848KB) is smaller than plain Pico's (~1.37MB) purely
because the CYW43 firmware blobs make the image larger.

**A soft `machine.Timer` callback (the default — no `hard=True` anywhere) can be silently dropped,
not just delayed** — `mp_sched_schedule()` drops it if MicroPython's fixed-depth scheduler queue
(depth 8 on rp2, shared by every soft timer/IRQ) is full, with no exception and no way to detect a
dropped vs. not-yet-run callback. A periodic timer self-heals next tick; a one-shot does not fire
again. A software-timeout mitigation for this was considered and rejected (it would just race the
real hardware watchdog every deployment already arms) — don't re-propose without a materially
different justification.

**`[x] * n` (list repeat) can segfault the interpreter for n in roughly 2⁶¹-2⁶³** (below that it
raises `MemoryError` like `bytearray(n)`; at/above 2⁶³, `OverflowError` — the gap is likely an
internal size-multiplication overflow before bounds-checking). Any code sizing an allocation from
external/caller input must clamp the size *before* allocating, not just catch `MemoryError`
reactively (`LockableBuffer`/`PrintLogHistory` are the established pattern).

**`machine.Timer.init()` can raise `OSError(ENOMEM)`** if the RP2040's alarm pool is exhausted —
every call site must handle it. **`MemoryError` is not an `OSError` subclass** — both are direct
sibling `Exception` subclasses; catch `(OSError, MemoryError)` wherever both are plausible. A plain
`except Exception:` *does* catch `MemoryError`.

**RP2040's real firmware uses single-precision `float`** (24-bit mantissa, exact to `2**24`);
**this project's Unix-port test rig uses double precision** (exact to `2**53`) — `float(int)`
beyond either threshold silently rounds. `coerce_numeric()`'s int→float direction relies on this
(A.8) — accepted, since no real schema field's bounds go near it.

**`struct.pack()`/`pack_into()` silently zero-pad or truncate on a mismatch instead of raising**,
unlike CPython — validate shape before packing if it matters. Still true on 1.29: the overflow
checks added to `py/binary.c` are gated behind `MICROPY_PREVIEW_VERSION_2`, so they only turn on in
a V2.0 preview build. Expect this fact to flip when upstream ships 2.0.

**A `micropython.const()`-wrapped value does not survive as an importable module attribute in a
frozen build** — `mpy-cross` inlines every `const()` value at each use site rather than leaving a
real bound name. A one-off script needing a promoted driver's `const()`-wrapped schema tuple must
hand-copy the literal, not import it.

**`time.ticks_ms()` wraps every `2**30` ms (~12.4 days) on rp2**; `ticks_diff()` is correct for
elapsed time under `2**29` ms (~6.2 days) regardless of wraparound — every real use in `src/` is a
short bounded timeout well inside that window. `time` module attributes cannot be monkeypatched (a
builtin C module's globals dict is fixed) — test rollover logic with synthetic ticks-space integers
via `ticks_add()`/`ticks_diff()` instead. This project's own Unix-port rig has a much larger period
(`2**62`, 64-bit) and cannot empirically exercise the real `2**30` rollover — verified by shared,
period-parametric code identity instead.

**`globals()` does not preserve a module's top-level statement order** — a test starting a
background task must keep an explicit reference and cancel it in its own `finally`, never relying
on file position. **Nesting `asyncio.run()` inside a coroutine already running one segfaults the
interpreter outright** — `await` directly instead. **`await` inside a comprehension is a
`SyntaxError`** — use a plain `for` loop. **`async def ... yield ...` ("async generator") parses
but produces a broken runtime object** (`__next__` but no `__aiter__`/`__anext__`) that **segfaults
the interpreter** the moment execution reaches a real `await` inside it, driven via plain `next()`
— documented upstream as PEP 525 "not implemented." The fix for `/status`'s JSON-streaming
(Part I): `await` everything up front inside an ordinary `async def`, collect into a list, hand
Microdot `iter(that_list)`.

**A response streamed as many small pieces has a real per-piece cost**: every stream write wraps in
its own `asyncio.wait_for()`, so splitting one response into N pieces multiplies that overhead by
N (measured: ~20 pieces regressed a fixed workload +53% versus 5 pieces for the same
memory-safety property) — keep piece count bounded to a small, fixed number of sections.
**`asyncio.TimeoutError` is a plain `Exception`, not `OSError`** — catch it separately from
`OSError` handling in the same call site.

**A MicroPython `list`'s backing array is sized by element *count*, never by what its elements
point to** — a short list of independently-sized JSON fragments never itself becomes one large
contiguous allocation. **`gc.threshold()`**: no-arg call returns the current threshold (or `-1` if
disabled — MicroPython's own real default); called with an argument, sets it and always returns
`None` (save the previous value yourself first). A negative argument re-disables rather than
raising.

**`scripts/build_firmware.py`'s type-checking strip removes every comment from a file**, a side
effect of reconstructing via `ast.unparse()` (which never carries comments) — harmless for frozen
firmware, but an on-device traceback's line numbers won't match checked-in `src/`; re-derive via
the same strip.

**`asyncio.run()`'s `KeyboardInterrupt` handling has a real gap while every task is parked in the
scheduler's poll wait** — a real SIGINT propagates straight out without resuming/unwinding the
suspended coroutine, so its own `try`/`finally` never runs. `digital_twin/`'s `__main__` blocks
re-run cleanup from plain synchronous code in an outer `except KeyboardInterrupt:` to compensate.

**Always check current MicroPython/Microdot documentation before asserting how an API behaves** —
never rely on training-data memory. **Whenever the pinned version changes (and periodically
otherwise), re-check every MicroPython-facing construct against the current source/docs/issue
tracker** — not just "is this still correct" but "is there now a better way" (e.g. F.2's
`socket.getaddrinfo()` status is exactly the kind of fact a version bump could invalidate). Repeat
every time `versions.toml`'s ref moves.

## F.2 Blocking calls: the wedged-bus backstop, and what can/can't be timeout-wrapped

**For a genuinely wedged I2C bus/sensor, the hardware watchdog is the accepted backstop, not a
software fix to chase.** MicroPython's cooperative scheduler can't preempt a synchronous
`machine.I2C` call in progress. Settled. **`socket.getaddrinfo()` belongs in this same bucket** — a
raw synchronous call with no coroutine boundary to attach a timeout to (confirmed against real
MicroPython issue-tracker reports). Moot for DNS: `src/asy_dns_client.py` resolves via its own
non-blocking UDP resolver instead. Calls that genuinely *can* be timeout-wrapped (FRAM SPI,
`asy_udp_socket.py`'s `select.poll`-driven `ready()`) should standardize on one mechanism.

**Don't wrap every `asyncio` primitive call in `try`/`except` against a theoretical
`MemoryError`** as a blanket policy — only worth closing for a concrete, non-hypothetical threat.

**Hot-unplug/replug I2C recovery is two-tier: task-death-and-respawn plus the watchdog backstop.**
Each `read_loop()`'s `_init_<sensor>()` fresh on every restart re-probes and soft-resets the sensor
— fully recovers a clean unplug/replug or a bad sensor state, but doesn't reconstruct the
underlying `machine.I2C` peripheral (only a full reboot does that). For a **bus-level** fault
(SDA/SCL physically wedged), a respawn's own probe can hang the same way — but
`start_and_check_tasks()`'s `task_errors` counter escalates repeated respawn failures to watchdog
starvation, which is what actually reconstructs `machine.I2C`.

**The same backstop applies to a WiFi link stuck in a CYW43-firmware-level false positive**
(`isconnected()` reporting connected well after the link is gone — confirmed on real hardware). A
well-documented, long-standing upstream MicroPython characteristic (open since v1.19.1/2022), not
project-specific — no upstream fix, no known-good independent detection method anywhere. **Decided:
investigated, no `src/` change** — every real consumer of connection state is harmless (NTP's own
robust timeout/backoff absorbs a doomed sync; `WifiUptime` is a cosmetic inaccuracy consumed by
nothing that acts on it) — a physical power cycle/`hard_reset()` is the accepted recovery. Real
timing data: a sustained outage essentially never self-resolves within 150s (5/5 trials rode out
the full wait); repeated brief flapping self-heals reliably instead (3/3 trials, ~30s) — a genuine
asymmetry, not chased further since the fallback covers either case regardless.
`network.STAT_GOT_IP` is not STA-only (an AP interface reports it too) — `_run_hotspot_mode()`'s
`status != STAT_GOT_IP` branch is only true on the first tick after entering hotspot mode.

**This backstop is inherently safe**: every real `ConfigManager.write_config()` call is reachable
only through the REST PUT path, so a device whose API is unreachable structurally cannot have a
flash write in flight — a power cycle carries zero flash-corruption risk. Combined with the
reboot-safe boot chain (A.4), power-cycle recovery is a deliberately stable, intended feature, not
merely a fallback.

## F.3 Long-blocking operations must not stall timing-sensitive work

Any new code that blocks the event loop for a noticeable time must not do so while timing-sensitive
work like the Neopixel animation needs to run — a standing design principle, not tied to a past
case. **The `get_long_block_lock()` shared-lock mechanism has been retired** (its one user,
`socket.getaddrinfo()`, was replaced by the non-blocking DNS resolver) — a new genuinely long
blocking call would need a fresh coordination mechanism designed, not a resurrection of the old
lock.

## F.4 Vendor-derived code: two opposite policies by vendor

**Adafruit-derived driver code is fair game to restructure/rewrite (keeping attribution)** — unlike
`ext/microdot.py`, which stays hands-off (A.5). **Sensirion-derived reference-algorithm ports stay
literal, the opposite policy.** `voc_algorithm.py` is a direct port of Sensirion's fixed-point
reference implementation — internal naming traces the original C source 1:1 so it stays diffable
against Sensirion's own reference. A genuine bug fix or behavior-preserving optimization (D.8) is
still in scope; a stylistic rewrite is not.

## F.5 MicroPython 1.29 delta (audited 2026-09-10, `v1.28.0..v1.29.0`)

Everything here was read out of upstream source at the two tags, or measured on the firmware
`toolchain/setup_toolchain.py` actually builds — not taken from changelog prose.

### F.5.1 `machine.I2C.deinit()`/`machine.SPI.deinit()` do not deactivate an rp2 bus

**Both are no-ops on this port**, and both were previously documented in this repo as if they
tore the hardware down. The generic `machine_i2c_deinit()`/`machine_spi_deinit()` in
`extmod/` only call through to a `.deinit` slot on the port's protocol struct; rp2's
`machine_i2c_p`/`machine_spi_p` (`ports/rp2/machine_i2c.c`, `ports/rp2/machine_spi.c`) never set
that slot, and `mp_machine_soft_i2c_p` sets it to `NULL` explicitly. The peripheral keeps running
and the pins keep their `GPIO_FUNC_I2C`/`SPI` assignment.

Two consequences the wrappers now state accurately:

- **There is no way to release an rp2 I2C/SPI bus from Python.** `machine.I2C(id)`/`machine.SPI(id)`
  return a **static per-bus singleton** (`&machine_i2c_obj[id]`, `&machine_spi_obj[id]`), so
  re-constructing reconfigures the same object rather than allocating a new one — nothing leaks on
  a re-`init()`, and nothing is reclaimable on a `deinit()`. `asy_i2c_driver.I2C.deinit()` /
  `asy_spi_driver.SPI.deinit()` still matter, but only because dropping `self._i2c`/`self._spi`
  is what puts the wrapper into its documented "bus unavailable" state.
- **`machine.I2C.deinit()` did not exist at all before 1.29** — `machine_i2c_locals_dict_table[]`
  at `v1.28.0` has no `deinit` entry, so the call raises `AttributeError` there. That gives
  `asy_i2c_driver.py` a hard **1.29 floor** on its `deinit()` path (unreachable from a fresh
  construct, since `_i2c` starts `None`; reachable via an explicit `deinit()` or a re-`init()`).
  `machine.SPI.deinit()` has existed for far longer, as a no-op the whole time.

`machine.UART.deinit()`, `machine.Timer.deinit()` and `network.WLAN.deinit()` are **real** on rp2
(`uart_deinit()`, `alarm_pool_cancel_alarm()`, `cyw43_deinit()` respectively) — the wrappers'
claims about those three are correct and unchanged.

`tests/machine.py` and `digital_twin/machine.py` model the no-op faithfully: their `deinit()`
records the call but leaves every bus operation working, exactly like hardware. One deliberate
divergence stays: both fakes hand back a **fresh object** per construction rather than a singleton,
so a test can tell the pre- and post-re-`init()` bus apart. Nothing in `src/` observes bus identity.

### F.5.2 rp2 SPI reads can now raise `OSError(EIO)`

`ports/rp2/machine_spi.c`'s `machine_spi_transfer()` gained an RX-overrun check (upstream #18471):
after a DMA transfer it drains the FIFO, and if `SPI_SSPRIS_RORRIS` is set **and the transfer was
reading**, it aborts the RX channel and ends with `mp_raise_OSError(MP_EIO)`.

Two bounds make this precise, and both are modeled at the bus level in `tests/machine.py`'s SPI
fake and in `digital_twin/machine.py`'s (`rx_overrun` for the blanket case, `rx_overrun_remaining`
for a transient glitch the bus recovers from, plus `inject_fault()` on the test fake for a single
call of any size — the same shape its I2C fake already had). The twin's chip-level
`_fram_chip.py` `FaultInjector` raises an identical-looking `OSError`, but it is the wrong place
for *this* fault: it cannot express the size threshold below, so a 1-byte status-register read
would raise there when real hardware could not.

- **Write-only transfers can still never raise** — the failure flag is only set under
  `if (!write_only)`.
- **Only transfers of ≥ 32 bytes are affected** — `dma_min_size_threshold` is 32; anything shorter
  uses `spi_write_read_blocking()`, which has no overrun check.

Reachable in this codebase: `asy_fram_driver.py`'s `_read_address()` reads the SGP40 VOC parameter
chunk in one 260-byte `readinto()` (`_VOC_PARAMS_MEMSIZE` 256 + CRC32 4), well past the threshold.
It propagates uncaught out of `get_values()`, matching `asy_i2c_driver.py`'s "a real `OSError`
always propagates" contract — an overrun leaves garbage in the buffer, so reporting success would
be strictly worse.

**It does not reach the reader task, though**, and an earlier draft of this section that said it
did was wrong. Driving the fault through the real stack (`tests/test_asy_fram_manager.py`'s
live-path tests, mirrored in the twin tier) shows `_read_chunk()`'s blanket `except Exception`
catching it, logging errno 47, and returning a clean failure — after which `_read()` reads block 1
instead, so **a single transient overrun costs nothing at all**: the caller gets its data and the
repair write restores block 0. Only an overrun hitting both copies degrades the read to `None`.
That makes the retry question (BACKLOG.md open question 15) much less pressing than it looked —
but the same run surfaced a genuine defect in the interrupted-read path, which is a separate,
still-open matter: see BACKLOG.md's own entry.

### F.5.3 Free wins already compiled into the 1.29 build

- **The interpreter core now genuinely runs from SRAM.** 1.28's rp2 linker rule for SRAM code
  placement never matched its object suffixes, so the intended placement silently never happened.
  Fixed upstream; verified in this project's own `firmware.elf.map`, where `py/vm.c.o`,
  `py/parse.c.o` and `py/gc.c.o` sit at `0x2000xxxx` inside an `EXCLUDE_FILE(...)` clause. Cost,
  measured off that map: **12,918 B** of RAM no longer available as Python GC heap (vm 5,040,
  parse 3,298, gc 2,676, the linker's own 1,504, plus ~400 of libc/libm/libgcc helpers the same
  rule excludes) — relevant to every Part I budget.
- **`-fno-math-errno`** is now on for the rp2 port (verified in the build's CMake flags), so
  `math.sqrt` compiles to the hardware instruction. `math_helpers.py` uses it twice;
  `voc_algorithm.py`'s `_fix16_sqrt` is pure integer and unaffected.

### F.5.4 `machine.mem_backup()` — new, unused, and the one worth adopting

New in 1.29 and **enabled by default on rp2** (`MICROPY_PY_MACHINE_MEM_BACKUP`); confirmed present
in this project's own built firmware (`strings firmware.elf | grep -x mem_backup`) and declared in
the 1.29 stubs. Backed by the RP2040 watchdog scratch registers: **28 bytes** across two regions
(`scratch[0..3]` and `scratch[5..7]`; `scratch[4]` is reserved by the pico-sdk), `itemsize=4`,
returned as a writable `memoryview`. **Survives a WDT reset, `machine.reset()` and a deepsleep
wake; lost on power-off.**

That is exactly the reset class the 2026-09-08 `WDT_RESET` investigation could not diagnose (see
CLAUDE.md's FRAM-log rule). A few bytes of last-phase/last-tick breadcrumb written on every
supervisor tick would survive it at zero flash and zero FRAM wear. Not adopted yet — tracked as
BACKLOG.md open question 14.

### F.5.5 Two defects in the 1.29 stub package, repaired at install time

`micropython-rp2-rpi_pico_w-stubs` 1.29.0.post1 (pulling `micropython-stdlib-stubs`
1.29.0.post1/.post2) ships two defects that together accounted for **every one of the 26 findings**
the version bump surfaced across both mypy passes. `scripts/typecheck.sh` repairs both right after
installing into `typings/`, each guarded on the defect still being present so it no-ops once
upstream re-ships:

- **An incomplete rename.** `stdlib/_asyncio.pyi` privatised `Future` to `_Future` and
  `stdlib/asyncio/futures.pyi` — which re-exported it under the public name — was dropped from the
  wheel, but `asyncio/tasks.pyi` still does `from .futures import Future`, `asyncio/__init__.pyi`
  still does `from .futures import *`, and `_asyncio.pyi`'s own docstring still describes the
  re-export as existing. With both importers dangling, `Future` degrades to `Any`, `_FutureLike[_T]`
  collapses, and every `asyncio.wait_for()`/`gather()` result in this repo becomes un-inferable.
- **`NotImplemented` is commented out** of `stdlib/builtins.pyi`. MicroPython genuinely has it and
  honors it from `__eq__` — verified directly on the pinned Unix-port interpreter: with an `__eq__`
  returning `NotImplemented` for a foreign type, `A() == 5` is `False`, not the truthy
  `NotImplemented` object.

Repairing the stubs is deliberate, and preferred over `type: ignore` comments in `src/`/
`digital_twin/`: the code is correct on the real interpreter in both cases, and
`warn_unused_ignores = true` would turn every such comment into a failure the day upstream fixes
this. The one place a `type: ignore` *is* right is `asy_udp_socket.py`'s `recvfrom()` — there the
1.29 stub got genuinely *more* precise (its address is now socket's full `_Address` union, IPv6's
4-tuple and AF_UNIX's `str` included), and our AF_INET-only narrowing is the thing that needs
declaring.

### F.5.6 Smaller 1.29 facts, and the non-events

- **`X: int = const(...)` now folds.** `py/parse.c`'s `fold_constants()` handles `RULE_annassign`,
  so a PEP 526-annotated `const()` no longer leaves a real module global behind. Verified
  empirically on both interpreters: `_A: int = const(60)` leaves `"_A" in globals()` `True` on
  1.28, `False` on 1.29. Buys nothing for typing (`const()`'s stub is already `Const_T -> Const_T`);
  it removes a 1.28 footgun. This project's 21 `const()`-using files are all unannotated.
- `int.to_bytes(signed=True)` is new; the one `to_bytes` call in `src/` is always non-negative.
- `MICROPY_C_HEAP_SIZE` is now settable from the make command line — a knob for trading C heap
  against Python heap without a custom board directory.
- mpy-cross gained `-X no-source-lines`; it would shrink frozen bytecode at the cost of traceback
  line numbers. Not worth it at current flash headroom.
- **`extmod/asyncio/` is byte-identical between the two tags** (`git diff --stat` empty) — no new
  primitives, and specifically **no timeout/cancellation support added to `socket.getaddrinfo()`**.
  F.2's status is unchanged, which is exactly the check F.1's standing practice calls for.
- **Zero commits** to `py/profile.c`, `py/modsys.c`, `extmod/modselect.c`, `shared/timeutils/`,
  `ports/rp2/datetime_patch.c` or `ports/unix/modtime.c` — the E.3 `select.poll()` GH-Actions hang
  cause and the `TZ=UTC` Unix-port fact both stand.
- The upstream I2C `WRITE1` transfer fix is behind `MICROPY_PY_MACHINE_I2C_TRANSFER_WRITE1`, which
  rp2 leaves at 0. DHCP's new `send_router` option defaults to `true` and isn't Python-visible, so
  the captive portal is unaffected. `gc.mem_free()`/`mem_alloc()` still call the slow `gc_info()`
  (`gc_info_fast()` is C-only). The RP2350 watchdog ~16 s fix is RP2350-only — the 8388 ms cap in
  F.1 stands.
- `SOCK_RAW` is now default-on and present in the built firmware. Noted only; F.2 settles the
  reachability-probe question.

## F.6 A SIGINT during `gc_collect()` can wedge the Unix-port heap

**Not a 1.29 regression** — measured at the same ~5% rate on Unix ports built from both `v1.28.0`
and `v1.29.0`, and `py/gc.c`'s locking path is unchanged between the tags. Found because it failed
one run of the digital-twin CI suite (2026-09-10); documented here because the symptom is deeply
misleading and the obvious fix is the wrong one.

**Mechanism.** `gc_collect_start_common()` sets `GC_COLLECT_FLAG` (bit 0) in
`MP_STATE_THREAD(gc_lock_depth)`; `gc_collect_end()` clears it on the way out. A SIGINT-driven
`KeyboardInterrupt` raised inside that window `nlr_jump`s past the clear, so the flag stays set for
the rest of the process. `gc_alloc()` returns `NULL` whenever `gc_lock_depth > 0`, and
`m_malloc_fail()` then reports **`MemoryError: memory allocation failed, heap is locked`** — for
*every* subsequent allocation, including the ones a `except KeyboardInterrupt:` shutdown handler
needs. The message is misleading twice over: nothing in this project ever calls
`micropython.heap_lock()`, and the heap is not full (`gc.mem_free()` read 1.7 MB at one captured
failure — it is purely the stuck flag).

**The recovery is `gc.collect()`, and only `gc.collect()`.** It re-enters
`gc_collect_start_common()` and leaves through `gc_collect_end()`, which clears the flag properly;
it needs no allocation of its own, so it works while the heap is locked. Verified 3/3 on captured
failures. **`micropython.heap_unlock()` is not a substitute** — it subtracts
`1 << GC_LOCK_DEPTH_SHIFT` from a `gc_lock_depth` holding only the 1-bit collect flag, leaving it
negative and still "locked".

`digital_twin/unix_port_gc_unwedge.py` packages this, alongside `unix_port_poll_prewarm.py`'s
similar Unix-port-quirk workaround; both digital-twin runners call it first in their
`except KeyboardInterrupt:` handler, before `flush_fram()`/`flush_scd30()`. **`src/` needs nothing**
— it has no `KeyboardInterrupt` shutdown path, and rp2 has no SIGINT.

---

# Part G — Shared Pattern & Primitive Reuse

Where D.10 states the general principle ("give related code the same shape; check how comparable
code elsewhere already does this"), this Part is its concrete, checkable instance: a living catalog
of established shared primitives plus the discovery procedure to run *before* writing new code —
cross-cutting across `src/`, `js/`/`tests_js/` (Part H), and any future layer.

## G.0 What this Part prevents

A freshly-invented, locally-plausible solution to a problem this project has already solved
elsewhere is a correctness risk, not just a style inconsistency — an established primitive
typically encodes edge cases (type coercion, NaN/±inf, error-shape conventions, boundary
inclusivity) a fresh reimplementation easily misses. Reuse is the default.

## G.1 The rule

Before writing new code, identify the *kind* of problem it solves (numeric type/range validation,
a caller-supplied callback that could misbehave, a REST response envelope, shared mutable state, a
per-module error log, a task/timer registration, a config-backed setting). Search G.2, then the
wider codebase, for an existing primitive solving that kind of problem — a search to actually
perform, grep for the shape. If a match exists, use it directly, never reimplement even a version
that looks locally simpler. If no exact match but a comparable one exists for a structurally
similar problem, model the new code on it explicitly (cite it in a comment). Only then design
something new — and if plausibly reusable, add it to G.2 in the same change. A new feature with
both a `src/` and `js/` side must encode the *identical* policy in the same change — there is no
backend-only or frontend-only validation/coercion policy change in this project.

## G.2 Known reusable primitives (living catalog — extend whenever a new one is established)

- **Numeric type/range validation & coercion** — `config_manager.py`'s
  `type_or_range_error()`/`coerce_numeric()`, for schema-backed or dispatch-only (synthetic
  `FieldSchema`) fields alike. Never hand-roll a cast/range comparison.
- **Caller-supplied callback dispatch guarding** — the `_dispatch_system_cmd()`/
  `_dispatch_notification_led()`/`_dispatch_notification_pause()` shape: validate payload, `try/
  await` the callback, `except Exception` → `err_s(...)` → `"Failed"`.
- **REST response envelope construction** — `api_response.py`'s `make_response()` only, never a
  hand-built `{"res", "code", "descr", "result"}` dict.
- **Task-scoped mutable state shared across coroutines** — `base_classes.py`'s `Lockable`/
  `LockedCounter`/`LockedFlag`/`LockedValue`, never a bare module-level variable plus an ad hoc
  lock.
- **Per-module logging/error-history** — `print_log.py`'s `make_logger()`/`PrintLog`/
  `PrintLogHistory`/`PrintLogHistoryStore`, never a bespoke print-based counter.
- **Driver layering/naming/config-schema/error-handling/concurrency/timer shape** — Part C, for a
  sensor driver specifically; complementary to this Part.
- **Memory-bounded streaming of a dict-shaped GET response** — `_stream_dict_response()` (Part I).
  Any route whose response scales with device configuration returns `await
  _stream_dict_response(result)` instead of `return result`.
- **Cross-language mirror: `js/` must encode the same policy `src/` enforces for anything it
  simulates** — `js/mock-server.js` must match the real `src/` endpoint field for field, bound for
  bound; a `src/`-side policy change and its `js/` mirror are one change, not two.

## G.3 Re-validating the existing project against this Part

Whenever a new file lands in `src/` (already part of CLAUDE.md's bird's-eye-scan rule) or `js/`,
grep the whole tree for the *shape* of each G.2 primitive's problem, not just its name. Each
finding is a candidate migration, not a known quirk to leave alone — flag and discuss before
changing (D.1's "flag, don't silently change" applies here too). A periodic, ongoing check, not a
one-time pass — re-run whenever G.2 gains a new entry, since an earlier instance of that problem
may predate it.

---

# Part H — Website (JS/HTML/CSS) Architecture

## H.1 Purpose and design constraints

The website is the sensor station's browser UI: show measurements/config, set config, issue
commands, show system/error state and history. Every REST endpoint's functionality must be
reachable somewhere in the GUI. Standing constraints, all met: no boilerplate (content generated
dynamically from a per-device definitions file, H.5); same skeleton/JS for every device
(`render.js`/`nav.js` have zero device-specific branching); full REST coverage retained versus
legacy; small, lean, no external runtime deps; stable on major browsers, light/dark (automatic-only
via `prefers-color-scheme`); modern hamburger/drawer nav; build = gzip → `freezefs` → frozen
bytecode → mount on startup → served via Microdot as gzip-compressed HTML (A.9).

**Predecessor**: `html_raw/{general,arzi,dev,wozi}` is the legacy, still-deployed site targeting
the legacy REST shape (PUT-with-`cmd`-envelope, `Led`-prefixed fields) predating
`asy_webserver_service.py` (A.8). This Part's website targets the refactored REST shape from the
start — not a reskin. `html_stub/` (A.9) is a separate placeholder used only by the generic
frozen-HTML pipeline's own tests.

## H.2 Folder structure and module map

```
html/               Hand-written HTML skeleton(s) + CSS
html/definitions/    Per-device definitions.json (H.5) - shipped, frozen by build_website.sh
js/                  Hand-written ES module JS source (poll-manager, mock backend, definitions
                     loader/validator, generic renderer, templates, nav)
tests_js/            JS unit tests (Vitest)
mockdata/            Prototype-only mock backend fixtures - NOT shipped
```

`package.json` mirrors `pyproject.toml`'s role (dev-tooling only, shipped code stays hand-written).
`npm run preview` serves the repo root — `localhost:8000/html/index.html?device=wozi` against
`js/mock-server.js`'s fake backend.

**JS modules**: `app.js` (prototype-only: mock fetch, `?device=` switch), `main.js` (real
production entry — no mock, staged as `app.js` in the real build), `definitions.js` (loader +
validator, no DOM), `field-format.js` (pure formatting, split so Node-context tests can reuse it
without DOM types, H.8.1), `render.js` (controller, delegates DOM to `templates.js`),
`templates.js` (DOM/markup layer, H.3), `nav.js` (drawer wiring), `poll-manager.js`
(single-flight queue + shared fetch-timeout), `mock-server.js` (prototype-only fake backend
answering the six REST paths, A.8).

**`scripts/build_website.sh <device>`** stages one device's real site: `index.html` (with
`style.css` and `definitions.json` inlined, H.7), the production `js/` modules concatenated into
one `js/app.js` bundle, `main.js` renamed `app.js`. Staging the production entry under the name
`app.js` means `index.html`'s import path never needs a build-time rewrite. Cross-checked against
`html/`/`js/`'s real contents by `tests_scripts/test_build_website_sh.py`.

**Splitting a module**: the bundler strips local `import` lines but never `export` lines — two
production files exporting the same name would collide once concatenated; a split-out module
(`field-format.js`) must never be *re-exported*. **`index.html`'s inline bootstrap `<script
type="module">`** can't be extracted (must keep importing the literal, never-rewritten path).
`eslint-plugin-html` still lints it in place; `tsc`'s JSDoc checking doesn't cover inline scripts
(accepted — it's a thin bootstrap).

## H.3 Layering: visual vs. mechanics (standing requirement)

The REST API is expected to stay stable long-term; the visual design is expected to be revisited
repeatedly, independently. **A purely visual/layout redesign must never require editing
data-fetching, validation, submission, or poll-coordination code.**

- **Visual layer** — colors/spacing/typography/dark-mode tokens (`style.css`) and DOM
  structure/order/CSS-class choices (`templates.js`), including any purely cosmetic interactivity
  that never touches network/app state. A redesign touches these two files (plus `definitions.json`
  for schema/labeling) and nothing else.
- **Mechanics layer** — data fetching, polling, validation, PUT submission:
  `poll-manager.js`/`mock-server.js`/`definitions.js` (pure) and the non-presentational parts of
  `render.js`/`nav.js`. None build DOM elements.

**Contract between them**: controllers reach into a template only via `data-*` attributes/CSS
classes, the one thing a redesign must keep stable — `[data-field-key]`/`[data-sub-field-key]`
(inputs, collected by `render.js`), `[data-current-value-for]` (readonly captions, refreshed on
poll), `[data-group-key]`/`[data-field-wrapper-key]` (card/field-level status coloring),
`[data-apply-status]` (written only by the controller; appearance decided entirely by CSS),
`.apply-button`, `[data-section-key]` (nav). Controllers only ever set the semantic
`data-apply-status` value, never a color/class directly. **In-place refresh only ever touches a
number/string field's caption** — a toggle/enum field's round-trip needs a genuine full remount
(a nav-drawer click), never an in-place poll.

## H.4 Architecture decisions

| Topic | Current behavior | Rationale / notes |
|---|---|---|
| Page model | Single-page shell, JS-driven view switching | One HTML skeleton; menu swaps sections via JS, no reload — makes the poll-manager's single-active-poll rule trivial. |
| Definitions file | One JSON per device, fetched once | Covers nav, labels, units, ranges, special values (H.5). |
| REST target | `asy_webserver_service.py` (A.8) | Six endpoints, sparse-body PUT, no `cmd` envelope, no `Led` prefix. |
| Nav grouping | Mirrors the 6 REST endpoints 1:1 | Measurements, Sensors, Networking, System, Status, Notification. |
| History depth | Counts always visible; full history on demand; no pagination | A realistic depth stays well under 20 entries, rides along in `/status`. |
| Poll coordination | One shared poll-manager (single-flight queue) | Measurements and status/settings groups are never polled concurrently by design; every fetch has a shared `AbortController` timeout. |
| API reachability | No dedicated API-browser page | Reachable somewhere in the ordinary GUI is enough. |
| Definitions validation | Strict — visible error banner on mismatch | Checks shape/version including `pollGroup` and poll-interval fields. |
| Landing page | Measurements | Matches legacy's default. |
| Card/nav visual treatment | Modernized flat cards; slide-in drawer nav | Soft border/shadow, real light/dark tokens. |
| Rendering safety | `textContent` only, never `innerHTML` | XSS-safe by construction. |
| Numeric coercion/validation | `type_or_range_error()`/`coerce_numeric()`, mirrored in `mock-server.js` | Canonical for every numeric field (A.8, Part G). |
| Dispatch-only PUT fields | `SystemCmd`, `PauseTime`, `lightCmdLED`, `ResetErrors` | None persisted — each re-dispatches fresh every submission. An enum field with no GET-matching state renders a blank placeholder by default. |
| PUT-result coloring | 4-state (`Valid`/`Unchanged`/`Invalid`/`Failed`), colored at group and field level | Matches the backend vocabulary. A whole-request failure marks every field `Failed` individually. |
| PUT/GET error handling | Non-2xx / null body / `res:"ERR"` = whole-request failure, surfacing the server's `descr` | A field missing from `result` shows `"Failed"`. A GET failure shows a per-section banner without clearing stale data. |
| Per-device page-scheme mechanism | The definitions file itself | `render.js`/`nav.js` have zero device-specific branching. |
| Known accepted gap | An empty string can't be set via this UI for any field | The sparse-PUT "blank = untouched" convention makes it structurally impossible (`PW`'s "open network" sentinel). Accepted. |

**`js/mock-server.js` mirrors every real backend quirk, not just the happy path**: `PW` masked on
every GET; SCD30's `ForceCalRef` always reports `400` on GET (a real register limitation);
`ContMeas`/`SGPResetVOC` never reported by GET (command-only triggers, C.5.2.1) — each dispatched
separately from the generic sparse-PUT path, covered explicitly by `tests_js/mock-server.test.js`.

## H.5 Definitions JSON schema

One JSON file per device (`html/definitions/<device>.json`). `js/definitions.js` documents the
shape via JSDoc and strictly validates it at load time. **Top level**:
`{schemaVersion, device, landingSection, defaultPollIntervalMs, sections[]}`. **`section`** mirrors
one REST endpoint (`key`, `rest: {get, put?}`, `pollGroup: "live"|"settings"|"none"`, `groups[]`).
**`group`** is normally a `FieldGroup`; Status's error section is `ErrcountGroup`
(`kind: "errcount"`, `modules[]`). **`FieldDef`**: a `kind`
(`readonly|number|string|enum|toggle|composite`) plus kind-specific metadata (`min`/`max`, `mask`,
`options`, `specialValues`, `subFields`, `onLabel`/`offLabel`, `float`, `dispatch`,
`defaultValue`). `dispatch: true` marks a repeatable command field (H.6, minus `ContMeas`) that
must re-submit even when unchanged. `defaultValue` marks a field's safe synthetic baseline when GET
never reports a real value — `ContMeas`'s `defaultValue` is `true` since `false` ("Off") actually
stops measurement, not a no-op (matching the legacy synthetic reference), not the toggle's naive
`false` default. See `wozi.json`/`dev.json` for worked examples — nearly identical field content
(same three drivers); only `device.id`/`displayName` and I2C bus pairing differ, which the
definitions files don't encode since a sensor's schema is driver-defined, not bus-defined.
**Autogeneration is not yet built** — hand-written today (BACKLOG.md).

## H.6 Errcount (Status section) and dispatch-only field conventions

**Errcount module list**: `{key, label}` per registered module plus each module's `CFGMGR_<name>`
(except SCD30, NVM-backed) plus `WEBSERVER`, looked up in `/status`'s `errcount[key]`. **History
entry**: `{"num": <raw errno>, "type": "N"|"E"|"W"}`, a fixed `history_length`-long list, no
per-entry timestamp — `type` only colors `num`. **Errcount UX**: same `.card` shell as other
groups, starts collapsed to a rollup + two filter buttons, wired entirely inside `templates.js`
(no controller involvement). **Dispatch-only field semantics** — `SystemCmd`, `PauseTime`,
`lightCmdLED` (r/g/b/t, bounds matching legacy exactly, rejecting not clamping),
`ResetErrors`, `ContMeas`, `SGPResetVOC`: `"Invalid"` only for a structurally wrong payload; a
well-formed submission always reports `"Valid"`, including on an identical repeat (never
`"Unchanged"`). `js/mock-server.js` mirrors this via dedicated dispatch functions — none ever
persisted into the generic settings store. **Server-side settings-group failure**: if a
`SettingsGroup`'s post-write hook raises, every field that group attempted is reported `"Failed"` —
never silently dropped — while the overall envelope still reports success.

## H.7 Digital twin integration

The website joins `digital_twin/` under A.10's generalized rule. CI/local test hooks build the real
production `wozi` website automatically (`package.json`'s `pretest` hooks), so a plain `npm test`
always exercises the real site. **Build-chain integration proof, two layers**:
`tests/test_website_build_integration.py` proves the staged site mounts/serves correctly on its
own; `tests/test_digital_twin_real_website_integration.py` closes the gap by pre-registering
`sys.modules["frozen_html"]` to the real build before `import sensortask_wozi`, booting the real
object graph against the twin's buses, and driving real HTTP. **Live-backend browser test**:
`tests_js/live-backend.test.js` drives the real website's JS in a real Chromium browser against a
real, live-booted twin subprocess; `live-backend-put-matrix.test.js` extends this to every real
writable field in `wozi.json`.

**Connection-concurrency ceiling and mitigations**: real rp2040/lwIP has a hard ceiling of 5
simultaneous TCP connections (lwIP's compile-time default). A page load stays well under it via
**bundling** (seven modules concatenated into one `js/app.js`, plain text concatenation, safe since
none use default exports/dynamic imports/re-exports) and **inlining** (`style.css` and the device's
`definitions.json` embedded directly into the staged `index.html`, with `<` escaped to avoid a
literal `</script` closing the tag early) — 2 connections per page load (down from ~9).
`max_connections` is `4` (raised from `3`), one more slot of the freed headroom.

HTTP keep-alive is deliberately not implemented: vendored `ext/microdot.py` always closes after one
request by design (no keep-alive support upstream either), and this project's hard rule never
touches that file's behavior; persistent connections proved fragile when tried in application code.
`max_connections` only ever rejects a *new* arrival — never touches an already-open connection,
reclaimed only by its own timeout.

### Cross-browser coverage

Vitest's browser mode only automates Chromium-family browsers via Playwright.
`scripts/cross_browser_smoke.mjs` closes this gap: boots the real twin and drives the real website
through **WebKitGTK** (real WebKit), **real Firefox** (`geckodriver` via `micromamba`, since
Ubuntu's `firefox` apt package is a snap-only stub), and **real Microsoft Edge** — plus Playwright's
own Chromium. Each engine, desktop and mobile viewport: nav → drawer → Sensors → edit a field →
Apply → confirm the backend validated it and the UI reflects it (polling for both
`data-apply-status` and the current-value caption together, since the caption refreshes via a
separate, slightly later GET). Deliberately narrow scope (not a second exhaustive PUT matrix — each
real WebDriver round trip costs seconds). `scripts/setup_cross_browser_toolchain.sh` installs the
three non-Chromium toolchains (idempotent), shared between CI and local dev; CI always installs all
three (a skip there is the bug to chase).

## H.8 CI / tooling stack

Mirrors Python's role split: **ESLint** (flat config, beyond `eslint:recommended` — covers `js/`,
`tests_js/`, `scripts/*.mjs`, and via `eslint-plugin-html` the inline script) for ruff;
**TypeScript `checkJS` mode** (`tsc --noEmit` reading JSDoc, two invocations — browser-context
`tsconfig.json` with DOM lib, Node-context `tsconfig.node.json` without, since the two contexts
can't share one `tsc` program's ambient globals, H.8.1) for mypy; **Vitest in real-browser mode**
(`@vitest/browser-playwright`, real Chromium, deliberately not jsdom — same "real engine over a
shim" principle as E.1; `testTimeout: 20000` mirrors "hanging tests never allowed") for the
real-interpreter test principle; **`@vitest/coverage-v8`** (report-only, no threshold) for
`--coverage`; **html-validate** for `html/`, **Stylelint** for CSS.

**CI mechanism**: `.github/workflows/ci.yml` carries a `dorny/paths-filter` gate job feeding `if:`
conditions on `web-lint-and-typecheck`/`web-unit-tests` — deliberately not a second workflow file
with its own trigger-level filter (which can leave a PR stuck on a required check that never
fires). Web CI runs only against `html/`, `js/`, `tests_js/`, `scripts/*.mjs`, `mockdata/`, and its
own config files. Root `.nvmrc` pins the Node version.

### H.8.1 JSDoc typedef imports across the browser/Node split

A JSDoc `@typedef {import("./x.js").Y}` pulls the *entire* referenced file into whichever
type-check program does the importing. A Node-context module referencing a DOM-context shape
inherits that module's DOM-typed JSDoc and fails to type-check. **Convention**: declare a narrow,
structural local typedef instead of importing the real one (`field-format.js`'s
`FormattableField`, intersected with `Record<string, unknown>` so a wider real object doesn't trip
excess-property checking, is the worked example). **Testing an async DOM refresh**: poll for the
exact expected rendered text, never a fixed sleep — a caption refresh via a separate async GET can
otherwise be caught mid-flight from a *previous* case.

---

# Part I — Memory-Safety Audit & Discipline

Written up during the 2026-09-07 systematic memory-safety audit, after a real-hardware
`MemoryError` investigation fixed one endpoint (`GET /status`) reactively and flagged that no
systematic audit of every other large-allocation site in `src/` had been done. **Scope**: found
exactly one class of genuine gap beyond `/status` — four other GET routes with the identical shape
(I.2/I.3) — and fixed it. Everything else scanned was already correct.

## I.1 Research findings: MicroPython memory management, general and rp2-specific

**The collector is mark-and-sweep, non-compacting** — it never moves a live object to defragment
the heap, so "insufficient contiguous space despite substantial free RAM" is a real, expected
failure mode; every finding below is about *contiguous* free memory, not total free memory. The
heap's allocation unit is a 16-byte block on a 32-bit target — a large allocation needs that many
contiguous blocks in a row. **Official guidance for reducing fragmentation**, matching what the
`/status` investigation already found: instantiate large, permanent buffers early (this project's
`LockableBuffer`/`AsyFramChunk` already do); minimize repeated creation/destruction of same-shaped
objects (`_stream_dict_response()`, I.3, exists to avoid exactly this); prefer `bytes`/`bytearray`
and pre-allocated I/O buffers over per-transaction ones (already this project's pattern); avoid
needless string concatenation (`+=` on immutable `str`/`bytes` is O(n²) — every accumulation loop
in `src/` either bounds total size or already guards the one failure that matters,
`asy_uart_driver.py`).

**`MemoryError` and `OSError` are direct sibling subclasses of `Exception`** — a plain `except
Exception:` *does* catch `MemoryError`, so `system_service.py`'s task-supervisor loop already
correctly restarts a task that dies from an uncaught `MemoryError`, no change needed. **A real
`gc.collect()` pause is ~1ms typically, up to ~15-21ms measured on real target hardware under
hammer load** (both `gc.threshold(-1)` and `32768`) — over 400x smaller than the 8388ms WDT cap, so
a single collection is conclusively ruled out as a cause of any real watchdog reset; cumulative
back-to-back collections checked too and ruled out (~10% of the cap worst-case). **No
async-generator-shaped alternative exists anywhere** to this project's "await everything up front,
hand Microdot a plain list" workaround — every MicroPython PEP 525 discussion converges on the same
"not implemented" status; the existing workaround *is* the standard answer for this platform.
**RP2040-specific findings checked and found not applicable**: a real upstream rp2-port
heap-corruption report concerns a C++ module's `new`/`delete` competing with the GC heap — this
project ships pure-`.py`/frozen-bytecode only. Pico W's CYW43 firmware genuinely reduces usable
heap versus a plain Pico (roughly half the 264KB SRAM) — an accepted, unavoidable fact of this
board choice.

## I.2 Hotspot catalog — every `src/` file scanned, function by function

**Needed a mitigation (fixed this session, I.3)**: `asy_webserver_service.py`'s
`_get_measurements()`, `_get_sensors()`, `_get_networking()`, `_get_system()`,
`_get_notification()` — each built a dict and returned it directly, letting Microdot's
`Response.__init__` run one `json.dumps()` over the whole aggregate, the identical shape `/status`
used to have. None of the five has a fixed, provably-small upper bound (they scale with
sensor-module/`SettingsGroup` count).

**Reviewed, found already safe (no change made)**: the VOC algorithm backup buffer (fixed
256 bytes, allocated once, in-place read/write forever); `asy_uart_driver.py`'s accumulation loops
(wrapped in `try/except MemoryError`, bounded or documented-unbounded-and-accepted);
`PrintLogHistory`/`LockableBuffer` (already clamp-then-allocate); `captive_dns.py`'s `DNSQuery`
(bounded by a single DNS datagram's structural limits); UDP receive buffers and I2C/SPI register
buffers (small, fixed, datasheet-derived sizes); `ConfigManager` (each instance owns one small
file, no aggregation); `asy_fram_manager.py`'s `allocated_size` (tracks FRAM address space, not
RAM); `asy_wifi_service.py` (no `network.WLAN.scan()` call anywhere).

## I.3 The shared primitive: `_stream_dict_response()`

Generalizes the already-shipped `/status` mitigation to any flat, dict-shaped GET response: one
small `json.dumps(key) + ":" + json.dumps(value)` fragment per top-level entry, batched into as few
pieces as practical under a `_MAX_STATUS_PIECE_BYTES` (1024) byte budget, handed to Microdot as
`Response(iter(pieces), ...)` — byte-identical JSON, with the largest single allocation bounded
regardless of how large the result grows. `/status` itself is untouched (its own sub-sections need
per-fragment dumps before coalescing). **Why byte-budget batching, not per-module/per-section**:
one piece per section scales with real module count (17 on real hardware, ~4.9KB — almost as large
as the original whole-aggregate failure); one piece per module would push piece count high enough
to hit the measured +53% throughput regression from per-write `asyncio.wait_for()` overhead (F.1).
Byte-budget batching bounds both piece size and count regardless of module count.
`_MAX_STATUS_PIECE_BYTES = 1024`'s real headroom, confirmed on real hardware: the smallest
largest-allocatable-contiguous-block under real hammer load was 49152 bytes — **~48x headroom**.

Test coverage: direct primitive tests; a hammer test at the real 17-module scale for each fixed
route; a combined final test hammering all six memory-bounded GET routes concurrently. Every hammer
helper asserts the response is a genuinely bounded *stream* (an iterator, never a plain
`str`/`bytes`, each piece under a margin) — added after confirming the original hammer tests would
still pass even with a fix fully reverted, since an 8MB Unix-port heap trivially absorbs a payload
this small regardless of contiguity; reverting each fix now fails exactly the hammer tests
exercising that route.

## I.4 The standing multi-stage memory-error handling scheme

**Every module in `src/`, present and future, follows this ladder for anything that can plausibly
exhaust memory or hold a large/growing allocation — not only once something has already broken.**
This was largely already true before this audit; writing it down makes it checkable for new code
too.

**(a) Catch and handle where reasonable** — a call site that can raise `MemoryError` from a
caller-controllable or growing allocation catches `(OSError, MemoryError)` and degrades locally.
Not a blanket policy on every `asyncio` primitive (F.2) — only where a concrete risk exists.
**(b) Degrade gracefully** — a caught failure produces a well-defined "unavailable"/`None`/`False`
result, never an unguarded re-raise (`_dump_status_source()` et al. substitute
`{"error":"unavailable"}` for one failed source rather than discarding the whole response).
**(c) Restart the task when it really bubbles up** — `start_and_check_tasks()` already restarts
any task that ends for any reason, `MemoryError` included; already correct. **(d) The watchdog is
the final resort, and must stop being fed once self-healing has genuinely failed** — the
`task_errors` counter escalates past repeated restarts to `reboot_system()`, at which point the
loop stops feeding the watchdog — the same backstop principle as a wedged bus/WiFi link.
**(e) Prove there are no memory issues under native `gc` defaults, first** — every stress test runs
with `gc.threshold(-1)` before ever running with a chosen threshold; a test only passing with a
threshold was never proving the code path memory-safe. **(f) A `gc.threshold()` value is defense in
depth on top of an already-safe design, never the fix itself** — `boot_entry/*_boot.py` sets
`gc.threshold(32768)` for exactly this reason, chosen *after* the `/status` fix already eliminated
the real-hardware `MemoryError` with no threshold change at all. Don't "fix" a failing (e)-stage
test by reaching for a threshold change instead of the underlying allocation pattern.

**Applying this scheme to new code**: before adding a function/module that holds, builds, or grows
an allocation whose size isn't a small, provably-fixed constant, run it through (a)-(d) at design
time and give it its own (e)/(f)-shaped test pair.

## I.5 Real-hardware confirmation

Every parameter this audit's Unix-port tests couldn't reach (an 8MB heap vs. RP2040's real budget)
was confirmed on real target hardware (2026-09-08): `gc.threshold(32768)` (real hammer-load
`mem_free` floor 91312 bytes vs. 128 bytes at the reactive-only default), the real GC pause-length
range (I.1), and `_MAX_STATUS_PIECE_BYTES`'s real headroom (I.3).
`tests_hardware/bench/test_memory_stress_bench.py` carries the permanent real-hardware regression
coverage (a 120s always-run hammer test plus a `long_soak`-gated 600s variant) — nothing from this
audit remains open pending hardware.
