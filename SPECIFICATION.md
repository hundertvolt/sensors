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
- **Part J** — UART Message Protocol (`asy_uart_comm.py`)
- **Part K** — Adding a New Sensor/Module: The Full Checklist
- **Part L** — Build Chain: Device TOML Schema & the `buildgen` Generator

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
                          src/asy_webserver_service.py (A.8). No static src/sensortask_*.py entry
                          point any more (SPECIFICATION.md Part L.2) - every
                          device's own sensortask_<device>.py + boot entry is generated at build
                          time by buildgen/ from devices/<device>.toml instead (see C.14, H.5, this
                          Part's own build/ entry below). improved-quality/ (former WIP staging) has
                          been fully retired and deleted.
ext/                     Vendored third-party code, hands-off (CLAUDE.md)
  microdot.py               Microdot v2.6.2, unmodified (A.5)
  freezefs/                 freezefs 2.4, unmodified - gzip+freeze pipeline for html_stub/ (A.9)
devices/                 One TOML file per device variant (SPECIFICATION.md Part L) - the single source
                          of truth for that device's hardware/wiring facts; buildgen/ turns each one
                          into a real firmware build.
buildgen/                Host-CPython device-TOML-to-firmware-module generator (SPECIFICATION.md Part L,
                          Part C.14) - AST-parses src/ driver files, never imports them (real
                          MicroPython-only names aren't available under plain CPython here).
build/                   Gitignored, build-time-only output tree (scripts/build_firmware.py's
                          default --output location) - generation is never committed
                          (SPECIFICATION.md Part L.2); `rm -rf build/` is the
                          full cleanup.
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
- **FRAM storage** (every real device — confirmed against all 6 `devices/*.toml`, each declaring a
  `driver = "fram"` instance) — a bump allocator handing out chunks as two redundant copies, so
  power-loss/watchdog reset mid-write leaves one valid copy. Used today for SGP40's VOC baseline
  backup.
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
recovery, adds unit tests/mypy/ruff/CI (ruff, mypy, shellcheck, actionlint and zizmor each as their own
stage, plus unit-tests, digital-twin-e2e and a real `firmware.uf2` build; the still-uncovered path
is the legacy `python/`+`build-*.sh` pipeline, BACKLOG.md). Files land in `src/` once reviewed
against Part D.

Originally prototyped as hand-written `src/sensortask_wozi.py` ("wozi", A.7) and
`src/sensortask_dev.py` (dev bench, physically flashed, B.11/H.5) — not yet `arzi`/`neu`. That
per-variant build-script generator has since been built (`buildgen/`, SPECIFICATION.md Part L): every
one of the 6 real device variants (`wozi`/`dev`/`arzi`/`klkizi`/`grkizi`/`schlafzi`, one TOML file
each under `devices/`) now gets its own `sensortask_<device>.py` + boot entry generated at build
time, and neither hand-written file exists in `src/` any more (SPECIFICATION.md Part L.4
finish criterion). `dev` additionally carries the UART message protocol (Part J) as two instances
across its permanent crossover jumper; `wozi` deliberately does not, since it is never physically
flashed and would otherwise carry an untestable peripheral. Goal throughout: same top-level
features as today's deployed units, not a feature change.

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
  redundancy (every real device — see the FRAM-storage bullet above). `src/`'s promoted versions: each chunk stores two copies plus a
  busy/idle status byte guarding reads and writes (MB85RS64V reads are destructive internally — the
  datasheet's own endurance note says total reads *and* writes set the endurance limit "as an FRAM
  memory operates with destructive readout mechanism", i.e. every read is internally a
  read-then-restore — so a power loss mid-read is as real a risk as mid-write). The consequence is
  intended and worth stating outright, since it looks like a bug from the outside: `_read_chunk()`
  marks a block busy before reading and only restores idle on the way out, so an interruption in
  between leaves it marked, and an interruption hitting *both* copies makes every later read fail
  the status check (errno 31) even once the bus is healthy again — the payload bytes may still read
  back intact, but an interrupted restore means they cannot be trusted, so refusing them is
  correct. Only a write clears it. Pinned down by `tests/test_asy_fram_manager.py`'s
  `test_an_overrun_mid_read_leaves_the_chunk_unreadable_until_it_is_rewritten`; don't "fix" it.
  **What this costs at the error-log layer, and the decision on it** (project owner, 2026-09-11):
  when both copies are left marked, `PrintLogHistoryStore.setup()`'s `_read()` fails and its
  `_write()` fallback stores the empty ring, so an abrupt reset mid-write **loses that module's whole
  persisted error history**. Measured in the digital twin at roughly 1 abrupt restart in 8. That is
  **accepted** — no recovery scheme is wanted for a reboot that catches the chip mid-operation; the
  invariant that must hold instead is that the loss is *all-or-nothing*, never a partial or garbled
  restore. A *commanded* reboot is the case that must never lose anything, and already doesn't:
  `system_service.py`'s `_reboot()` pauses permanent storage before resetting, which gates every
  `_write()`/`_read()`/`clear()` so nothing can be in flight (measured 20/20 in the twin against the
  ~1-in-8 unpaused rate). Covered at every tier — `tests/test_fram_integration.py` (both blocks
  torn), `scripts/_digital_twin_ci_suite.py` runs 5b/5c, and
  `tests_hardware/flash/test_fram_storage.py`'s reset-race pair on real silicon.
  **Write protection gates reads too, and that is intended** (project owner, 2026-09-11):
  `_read_chunk()` must WRITE the transient busy marker before it may read, so a write-protected
  chip makes `chunk.read()` return `None` as surely as it makes `chunk.write()` return `False`. An
  *access* gate, not data loss — the stored bytes are untouched and come back intact once
  protection is cleared. Two properties separate it from the pause gate, both asserted: it fails
  *at* the chip (the status byte is clocked off the bus first, then the marker write is refused —
  errno 32 per block, then warning 72) where `set_pause()` short-circuits before SPI runs; and
  `override_pause=True` bypasses only the manager's pause flag, never the chip's protection.
  Asserted at mock, twin and flash tiers. One claim only real silicon can settle, and the flash
  tier does: every tier's write check stops at the driver's own guard, so
  `device_scripts/fram_write_protect_roundtrip.py` desyncs the cached `_wp` from the
  still-protected chip and sends a genuine WREN+WRITE — the bytes never land, so BP0|BP1 itself
  refuses it. Both chip fakes stop at the driver guard and cannot prove this.
  "Both copies valid but different" is a hard failure (no generation counter), never guessed. `AsyFramTimestampedChunk.write()`/`write_into()`
  return `(ntp_synced, utc, success)` — `success` is third, not first; don't reorder. `AsyFramManager`
  is a bump-pointer allocator: instantiation order is on-chip layout and must stay identical across
  firmware versions for existing data to decode correctly.
  **FRAM chunk determinism rule** (no deallocation exists by design): every FRAM-chunk-owning
  object's construction must be deterministic across every system event, especially reboot — an
  unconditional, fixed-position statement, never inside a branch/loop a task restart could
  re-enter. True today: task restarts only re-invoke an already-captured starter on the *existing*
  object, never `__init__`; a full reboot replays `build_system()`'s construction from scratch, and
  every current FRAM-chunk-owning construction (`sysfunct`, `sgp40`'s VOC chunk, `neopixel`,
  `notification`) is unconditional top-level. Prove single, deterministic construction before
  adding any new FRAM-backed class.
  Every deliberate system reset pauses FRAM first (`system_service.py`'s `_reboot()` calls
  `storage_pause(True)` before arming the reset timer, and before the watchdog-starve fallback).
  Margin is ample (FRAM at 1MHz, 8KB chip, no chunk near that size — a two-block write+CRC readback
  completes in low single-digit ms, three orders of magnitude under both the 4s reset delay and the
  ~8s watchdog-starve wait). The `machine.reset()`/`bootloader()`-site half is enforced by
  `tests/test_reset_call_site_invariant.py` (fails if either appears anywhere in `src/` but
  `system_service.py`). Its `WDT()`-site half is now permanently vacuous — no `sensortask_*.py` is
  ever committed to `src/` any more (every device's own is buildgen-generated at build/test time,
  SPECIFICATION.md Part L.4) — and the invariant it used to check is instead proven on the
  generated output directly by `tests_scripts/test_buildgen_generate.py::
  test_real_device_constructs_watchdog_exactly_once`, parametrized over all 6 real devices.
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
- Deployed task supervisor is a hand-rolled loop duplicated per device file; every generated
  `sensortask_<device>.py`'s `main()` instead calls `system_service.py`'s real
  `start_and_check_tasks()`/`start_timers()`.
- **Functional behaviors confirmed intentional by the project owner — don't "fix" these:**
  air-quality LED sequencing (one color per condition, paused between flashes); FRAM SGP40 backup
  "0 = disabled" for `BackupPeriod`/`BackupMaxAge` (`DEVICE_REFERENCE.md`); permanent WiFi
  deactivation after a second STA failure streak, `_PHASE_DEACTIVATED` special-cased through task
  restarts the same way `_PHASE_HOTSPOT` already is — only a physical power-cycle clears it; STA
  never auto-falls-back to hotspot once connected successfully even once in a task's lifetime — only
  a human resubmitting credentials or a full task restart resets this; the web UI shows raw numbers
  only, no color-coding (the LED is the at-a-glance indicator); SGP40 skipping its VOC read entirely
  (returning `SGP40(None, None, None)`, not substituting any fallback compensation values) when
  SCD30 compensation data isn't yet available, with no distinct signal (SCD30's own error counter
  covers it); FRAM's 8KB has ample headroom over SGP40's ~250-byte usage; `asy_uart_driver.py` intentionally
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
  The generated `sensortask_wozi.py` wires this to `AsyConnTime.is_hotspot_active()`. This is what makes phones'
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

**RP2040**: `datasheets/pico w/` holds the Pico W *board* datasheet only — the RP2040 *silicon*
datasheet is not in the repo, so its GPIO function-mux table is not readable here. For a pin-mux
question the authoritative substitute is the pinned MicroPython source itself
(`ports/rp2/machine_uart.c`'s `IS_VALID_PERIPH`/`IS_VALID_TX`/`IS_VALID_RX`, and the equivalent
macros in `machine_i2c.c`/`machine_spi.c`), which the toolchain checkout always has — not a web
search. Those macros give UART TX on `pin % 4 == 0`, RX on `pin % 4 == 1` and the peripheral from
`((pin + 4) & 8) >> 3` — so UART0 owns 0/1, 12/13, 16/17, 28/29 and UART1 owns 4/5, 8/9, 20/21,
24/25. The board datasheet does cover what is board-specific: p.8 lists GPIO23/24/25/29 as the
pins the wireless chip takes.

**BMP390**: `datasheets/bmp3xx/` holds BMP384/BMP388 but not BMP390. The project owner has confirmed
the whole family shares the same register map/protocol, so `asy_bmp3xx_driver.py` treating BMP390's
`0x60` chip ID the same as the other two is correct — the PDF's absence is a documentation gap only.

## A.7 wozi's construction order and dependency graph

Historically documented against a hand-written `src/sensortask_wozi.py`; that file no longer exists
(SPECIFICATION.md Part L.2) - `buildgen.generate.generate_device()` now
generates the equivalent `sensortask_wozi.py`/boot entry at build time from `devices/wozi.toml`
(Part C.14), reproducing the exact same construction order/FRAM chunk layout described below. This
section stays the architectural reference for *why* that order is what it is; the generator is what
actually emits it now.

`build_system(*, cfg_path="", debug=None, web_host="0.0.0.0", web_port=80) -> None` does pure
construction (every object assigned to a module-level global) plus a `setup()` batch; `main()`
calls `build_system()` then `start_timers()`/`start_and_check_tasks()`. Neither blocks at import
time — the real entry point (the generated boot entry, `asyncio.run(main())`) is kept separate so
importing the generated device module stays safe under tests.

**Why order matters**: `AsyFramManager` is a bump-pointer allocator — instantiation order is
on-chip layout and must stay identical across firmware versions (A.4's determinism rule).

**Construction order, top to bottom** (as of WP1/CLAUDE.md's implicit-FRAM-wiring rule: `fram` moved
ahead of `conn`/`ntp`/`sysfunct`, and all three — plus `conn`'s own `DNSServer` and the webserver —
now inherit it too, whenever `[device.wiring].fram_target` is set, which every real device's own
TOML does today):

1. `watchdog = WDT(timeout=8000)` — hardcoded, no injection point.
2. `i2c0`, `i2c1` = `asy_i2c_driver.I2C(...)` ×2. `i2c0` (SCD30, step 8) sets `timeout=200000`
   (200ms): SCD30 documents up to 150ms clock stretching/day, past rp2's 50ms default — without the
   override that expected stretch surfaces as a spurious `OSError`. `i2c1` (SGP40/BMP3xx) keeps the
   port default.
3. `spi0 = asy_spi_driver.SPI(...)`.
4. `fram = AsyFramManager(spi0, 1, max_size=0x2000, ...)` — no chunk of its own (Topic 11's rule:
   every module gets optional FRAM logging except the FRAM module itself — logging a FRAM fault into
   that same FRAM is pointless). Built here, before every mandatory-infra module below, specifically
   so each can receive a real chunk rather than `fram=None` — `buildgen.graph.build_construction_order()`
   adds an explicit dependency edge from each of `conn`/`ntp`/`sysfunct` onto `fram` whenever
   `[device.wiring].fram_target` is set (a device with none keeps the pre-WP1 order: `conn`/`ntp`
   first, `fram` wherever its own instance ordering puts it).
5. `conn = AsyConnTime(..., fram=fram, ...)` — **FRAM chunk 1**; `SensorReaderConfig.__init__`
   (which `AsyConnTime` goes through) builds its own `self.pr` chunk first, then its owned
   `ConfigManager` — **chunk 2** (WP2/CLAUDE.md's implicit-FRAM-wiring rule: every
   `SensorReaderConfig`'s own `cfgmgr` inherits the same `fram` its owner was given, its own
   separate `"CFGMGR_<name>"`-named logger, never folded into the owner's own history). `conn` then
   owns `DNSServer` internally (`captive_dns.py`), constructed with the same `fram=fram` —
   **chunk 3**, its own separate `"DNSSRV"`-named logger.
6. `ntp = AsyNtpClient(conn.get_wifi_mode_lock(), conn.network_available,
   conn.get_dns_server_ip, ..., fram=fram, ...)` — bound methods off `conn` — **chunk 4**, its own
   `cfgmgr` — **chunk 5**.
7. `sysfunct = SystemService(ntp.ntp_issynced, watchdog=watchdog, fram=fram, ...)` — **chunk 6**.
   Not a `SensorReaderConfig` subclass (no measurement data), but embeds its own `ConfigManager`
   directly the same way (`system_service.py`'s own comment) — **chunk 7**, same "own chunk, then
   cfgmgr chunk" shape as every `SensorReaderConfig`-based module.
8. `scd30 = SCD30_Reader(i2c0, 8, trigger_sec=3, ..., fram=fram, ...)` — **chunk 8**; no
   config schema (params live on-sensor, so no `cfgmgr`/chunk of its own). Constructed before
   `sgp40` (ordering-hazard #1, Part C.14): `sgp40` holds a direct reference to this already-built
   object as its `temperature_source`/`humidity_source`, so the producer must exist first — a pure
   Python name-resolution requirement, not a FRAM one (chunk order is random-access and doesn't
   itself care), but the two facts are deliberately kept in the same relative order here for
   readability. `wozi` is never physically flashed (CLAUDE.md), so reordering carries no
   deployed-data-loss risk.
9. `sgp40 = SGP40_Reader(i2c1, temperature_source=scd30, temperature_field="Temp",
   humidity_source=scd30, humidity_field="Hum", fram_storage=fram,
   fram_ntp_callback=ntp.ntp_issynced, ...)` — **chunk 9** (error log), then its own `cfgmgr` —
   **chunk 10**, then the VOC backup (**timestamped chunk**, not part of this numbering).
   `scd30` is passed directly as both value sources (C.14.3's generalized per-value
   measurement wiring) — no wrapping callback; the two fields resolve independently, so a future
   device could compensate temperature and humidity from two different sensors.
10. `bmp3xx = BMP3xx_Reader(i2c1, ..., fram=fram, ...)` — **chunk 11**, own `cfgmgr` — **chunk 12**.
    No cross-instance wiring dependency of its own on `wozi` (SCD30's `AmbPres` stays a static
    config value even though `wozi` physically has a live BMP388 — A.4's own note), so
    unconstrained by ordering-hazard #1. (`dev`-only `isl29125` follows the identical
    "own chunk, then cfgmgr chunk" shape, positioned here too when present.)
11. `neopixel = NeopixelDriver(15, fram=fram, ...)` — **chunk 13**; no on-flash config, no `cfgmgr`.
12. `notification = NotificationCoordinator(neopixel.request_signal, ntp.cettime, fram=fram, ...)`
    — **chunk 14**, own `cfgmgr` — **chunk 15**; staged `register()` ×3 (each a direct
    `(source, field)` reference — `scd30`/`"CO2"`, `sgp40`/`"VOC"`, `scd30`/`"Hum"`, Part C.14) then
    `finalize()`.
13. `conn.set_ext_led(neopixel)`.
13b. *(`dev` only)* two buildgen-generated `[[instance]]` entries construct
    `asy_uart_driver.UART(...)` ×2, then the new UART-crossover wrapper module (§Part J) wraps each
    in a `UART_Comm(...)` across the permanent crossover jumper — `dev.toml` wires
    `fram_target = "fram"` on both instances (WP3 - was wrongly, deliberately excluded; `UART_Comm`
    already supported `fram=`/`logger=` at the class level, only the buildgen wiring was missing),
    so `uart_link_init` and `uart_link_resp` each draw their own chunk here, right after
    `notification`'s own `cfgmgr` chunk (step 12) and before the webserver's (step 14) — never
    shared between the two instances, so a fault on one end stays attributable to it. Neither is a
    `SensorReaderConfig`, so neither gets a `cfgmgr` chunk of its own — the same "no absolute
    number, `dev`-only, positioned here when present" treatment step 10 already gives `isl29125`.
    Placed here, after every FRAM-allocating module and immediately before the webserver, because
    the webserver's own `error_sources=` list includes them. `wozi` has no such step, and no such
    chunks. The variant
    also runs a small **link exerciser** task on the initiator side: nothing on a live system would
    otherwise initiate a transfer, so every claim about the link coexisting with the webserver would
    be a claim about an idle link. Its transfer/failure counts ride the variable-length
    `maintenance_sensors` registration and surface through `/status`, which the bench tier asserts
    advancing under load (`tests_hardware/README.md`). The exercise logic lives in the wrapper
    module (not the generated file itself) because only application-level code knows what to ask a
    peer — the protocol itself carries no application semantics (Part J.1). See Part J for the
    wrapper module's exact shape and generated variable names.
14. `app = Microdot(); webserver = WebserverService(app, sensors=(...), ..., static_mount="/html",
    is_hotspot_active=conn.is_hotspot_active, host=web_host, port=web_port, fram=fram)` —
    **chunk 16** (as of WP1 — previously deliberately RAM-only; now folds into the same
    implicit-if-FRAM-present rule as every other mandatory-infra module); no on-flash config, no
    `cfgmgr`. `static_mount="/html"` registers the static route pair last, so an exact-match API
    route always wins.
15. `sysfunct.set_level_setters(_collect_level_setters())` — after every module has constructed.
16. **`await x.setup()` batch**: `sysfunct → fram → conn → ntp → sgp40 → bmp3xx →
    notification`. One hard constraint: `notification.setup()` needs `finalize()` (step 12)
    already run, satisfied by batching at the end. `scd30.setup()` isn't in this batch (no
    local config); neither is `webserver.setup()` — its own `self.pr.setup()` runs lazily, the
    first time its `_run()` task actually starts (see the boot-latency note below).
    **`sysfunct.feed_watchdog()` follows every single call in this batch** (WP6) — a one-time,
    boot-only, non-looping feed site, which is what makes it safe regardless of how many modules a
    device wires: it cannot degenerate into something that keeps feeding a genuinely hung system
    forever. `feed_watchdog()` itself is a no-op on a watchdog-less build or once
    `_force_watchdog_starve` latches (Part G.2), so this needs no per-device special-casing either.

**Real FRAM chunk order** (full wiring — every real device's own TOML today, wozi's own 16
`PrintLogHistoryStore` chunks plus 1 timestamped chunk): AsyConnTime → its own `CFGMGR_WIFI` →
DNSServer → AsyNtpClient → its own `CFGMGR_NTP` → SystemService → its own `CFGMGR_SYSTEM` → SCD30
(no `cfgmgr`) → SGP40 error log → its own `CFGMGR_SGP40` → SGP40 VOC backup (timestamped) → BMP3xx
→ its own `CFGMGR_BMP3XX` → (`dev`-only: ISL29125 → its own `CFGMGR_ISL29125`) → Neopixel (no
`cfgmgr`) → NotificationCoordinator → its own `CFGMGR_NOTIFY` → (`dev`-only: `UART_init` →
`UART_resp`, WP3 — neither has a `cfgmgr`) → WebserverService (no `cfgmgr`).
Every module with a FRAM-backed error log, and every `SensorReaderConfig`-based module's own
`cfgmgr` (WP2), uses it; must stay in this relative order. `src/` has no earlier on-chip layout to
preserve. (A device with no `[device.wiring].fram_target` keeps `conn`/`ntp`/`sysfunct`/
`webserver` RAM-only and none of them draw a chunk at all — WP1 changed nothing about that
fallback path; a `uart_link` instance with no `fram_target` in its own `[instance.wiring]` stays
RAM-only the same way, unaffected by whether the device's `fram_target` is set anywhere else.)

**Boot-latency note (WP1/WP2, both resolved — the finding below is the resolution, not open
work)**: `conn`/`ntp`/`sysfunct`/`webserver`'s FRAM-backed loggers only draw their chunk at
construction time (bump-pointer, instant); each one's *real* first chunk read/write happens later,
inside its own `self.pr.setup()` call, sharing one process-wide `asyncio.Lock` (`FRAM_SPI`'s own,
`asy_fram_driver.py`) with every other FRAM-wired module. `sysfunct → fram → conn → ntp → ...`'s own
explicit setup batch (step 16) runs before any task starts, so those calls never contend with
anything, including every `SensorReaderConfig`-based module's own `cfgmgr.setup()` (WP2) — it rides
the same pre-task-start batch as its owner, not the contended window below. `webserver`'s own
`self.pr.setup()` is different: it runs lazily inside `_run()`, `webserver`'s own task — and
`system_service.py`'s `start_and_check_tasks()` starts every task within one ~1-second stagger
window (Part C.9's own task-starter-staggering design, distinct from Part C.9.1's timer stagger),
with `webserver`'s task always last. By the time it runs, every other FRAM-wired module's own
task-start-time FRAM access is already contending for the same lock, so `webserver`'s first
setup() call queues behind all of it. **Measured directly against the real generated code for all 6
devices under the digital twin**: boot-to-first-`200` was ~1.9-2.2s before WP1; WP1 alone (wiring
`conn`/`ntp`/`sysfunct`/`webserver`'s own loggers into FRAM) moved it to ~4.5-6.3s (`dev` slowest —
the most FRAM-wired instances); WP2 (adding every `SensorReaderConfig`-based module's own `cfgmgr`
chunk) moved it further to ~6.1s (`wozi`) / ~7.7s (`dev`) — a modest further increase, not the much
larger jump the lock-contention theory alone would predict, precisely because WP2's own new chunks
ride the uncontended pre-task-start batch as just explained; only `webserver`'s own lazy setup is
exposed to the contended window, and WP2 adds no new chunk to `webserver` itself (still no
`cfgmgr`). Both final numbers stay comfortably inside `tests_scripts/
test_digital_twin_generated_boot.py`'s own 15s budget (raised from 6s for exactly this reason - see
that constant's own comment). This is a one-time, self-resolving cost (steady-state serving is
unaffected) and not something to "fix" by reordering `webserver` in the stagger, or by treating the
latency itself as a defect (CLAUDE.md's own "boot latency is not a metric to optimise" rule) — **but
every number above is a digital-twin measurement, not a real-hardware one.**
`digital_twin/_fram_chip.py` answers SPI opcodes in memory with zero wire time, so these numbers
exclude the entire real cost of a FRAM transaction; the "design itself needs no change on this
evidence" conclusion this paragraph previously drew is exactly the thing a real-hardware run could
overturn, since the dominant term in a real FRAM setup call (SPI wire time under lock contention) is
precisely what the twin cannot measure. Do not treat this paragraph's numbers as validated for
anything beyond "the twin's task graph resolves in this many simulated seconds."

**Re-checked on real hardware (`dev` bench, 2026-09-16), and the twin's absolute numbers do not
survive it.** Real `dev` firmware was built from each commit's own tree, flashed, then given 5 timed
`hard_reset()` cycles per image with the first post-flash boot discarded and `GET /status` polled
every 200ms for a real `200`: pre-WP baseline **7.74s**, WP1+WP2 **9.80s**, WP1–WP8 complete
**9.76s**, and **10.66s** with the `CFGMGR_SYSTEM` setup-order fix on top (medians of 5, spread
±0.06s at the two earlier points). So **WP1+WP2 costs ~+2.05s of real boot latency and WP3–WP8 add
nothing measurable**, and 23 consecutive reboots across the four images produced no `WDT_RESET` —
which is the standard that actually applies here (CLAUDE.md's "does not starve the watchdog", not
"boots fast"). The twin's *absolute* figures were never a real baseline, since it models no WiFi at
all and association plus DHCP dominate the real 7.7s floor; its *delta* prediction held up well
(~1.4–1.8s predicted for WP2 alone against a real WP1+WP2 delta of ~2.05s). **The contended-
`webserver` hypothesis above did not survive the measurement**: `webserver`'s own `pr.setup()` was
confirmed to *succeed* from a clean boot on real hardware (`initialized == True`), so the contended
window costs it time, not correctness — and since WP2 adds no new chunk to `webserver` itself, it
cannot account for a delta that WP1+WP2 produce jointly. One part stays open: the `CFGMGR_SYSTEM`
fix's own **+0.90s** is far more than one extra FRAM-backed logger's `setup()` should cost, and is
unexplained (`REAL_HARDWARE_TEST_QUEUE.md` R6).

**This order, and `i2c0`'s SCD30-specific `timeout=200000`, are wozi's own — derived from
`devices/wozi.toml`.** `buildgen` derives both from each device's own TOML rather than assuming
wozi's answer applies everywhere (confirmed against `buildgen/codegen.py`).

**Task/timer starter collection** (`_collect_task_starters()`/`_collect_timer_starters()`, from
`main()`): every module's `get_task_starters()`/`get_timer_starters()` is called uniformly.

**Error-source/debug-level fan-in** (`_collect_error_sources()`/`_collect_level_setters()`, Part
C.14): generic, not hand-enumerated — every constructed module's own `get_error_sources()`/
`get_loggers()` is called uniformly and the results flattened, the same "every module discovered
through a uniform method, never by name" shape `_collect_task_starters()`/
`_collect_timer_starters()` already used. `get_error_sources()` returns `[self]` plus any nested
error-logging sub-object a module owns (a `SensorReaderConfig`'s own `.cfgmgr`, `AsyConnTime`'s own
`.dns_server`); `get_loggers()` is the same shape for `PrintLogHistory` instances, feeding
`SystemService.set_level_setters()`/`_apply_level()`'s registry (each wrapped in its own
`try/except Exception`; calling `set_level()` at any time is safe — no interrupt handler touches
logging, `self.level` is a single atomic-store `int`).

**Dependency graph**: `ntp` holds `conn`'s bound methods; `notification` holds direct references
to `scd30`/`sgp40` (its registered `NotificationSignal`s' `source`) plus
`neopixel.request_signal`/`ntp.cettime`; `conn` holds `neopixel`; `sgp40` holds `ntp.ntp_issynced`
and direct references to `scd30` (its `temperature_source`/`humidity_source`, Part C.14.3).
Since C.14.3's per-value measurement wiring resolves any producer purely by attribute name
(`getattr(data, field_name)`), `asy_sgp40_driver.py` needs **no** static import of
`asy_scd30_driver` at all — a real change from the mechanism's earlier, whole-object `comp_source`
shape, which did import `SCD30_Reader` by name for its fixed constructor-parameter type. Every
module still constructs its own `ConfigManager`/`PrintLog` internally — no cross-module config
sharing, and every *instance*-level dependency stays constructor-injected, so the object graph is
still a clean DAG at that level.

Full coverage: `tests/_sensortask_scenarios.py` (imported by the six `tests/test_sensortask_<device>.py` files, one per real device).

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
  GMTOffset, DSTOffset` plus one nested, never-flattened `build` sub-entry (SPECIFICATION.md Part L
  Session 7 — `{"firmwareVersion", "websiteVersion", "buildDate"}`, verbatim from
  `WebserverService`'s own `build_info=` constructor kwarg, which every generated device supplies
  from `buildgen.version.FIRMWARE_VERSION`/`WEBSITE_VERSION` plus a real build timestamp captured
  once per `buildgen.generate.generate_device()` call — generator-owned/fixed, never per-device, and
  reported live so a fleet operator can tell which build a given physical unit is actually running
  without re-flashing to check); `/notification` → `OnH, OnM, OffH, OffM, FlashBri, Interv, FlashDur,
  AutoOn, WarnCO2, WarnVOC, WarnHum`; `/status` → live-only, sub-structured
  `networking`/`system`/`sensors`/`notification`/`errcount` (one entry per module plus per
  `ConfigManager` — `CFGMGR_<name>`).
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
table, so a real on-disk file there is silently unimportable. Every generated
`sensortask_<device>.py` does a module-level `import frozen_html`, mounting `/html` as a side
effect; `WebserverService(..., static_mount="/html")` registers the static route pair.

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
so the generated `sensortask_wozi.py` runs under the Unix-port interpreter and behaves like real
hardware. Independent of `tests/`; the swap is pure `MICROPYPATH` ordering. See
`digital_twin/README.md`.

**Chain-completeness requirement, generalized beyond sensor drivers**: any new module joins the
digital twin, provided it can form a complete chain. A new sensor driver needs the C.11 point 9
checklist. A new common/base module wired into `build_system()`'s real object graph is
automatically exercised — no separate question for a module with no hardware surface. A module that
can't yet complete the chain stays out until the missing piece exists (flagged per CLAUDE.md).

**Automated CI suite** (`scripts/run_digital_twin_ci.sh`, `digital-twin-e2e` job — a
`strategy.matrix` over all 6 real device variants as of SPECIFICATION.md Part L.4): wipes
leftover twin state; builds the Unix port and the real production website for that device
(`scripts/build_website.sh <device>`); `scripts/_digital_twin_ci_suite.py` drives
`run_generic_integration.py` through twelve top-level subprocess runs (two of them, 5b/5c, further
sub-runs of run 5 — fourteen real subprocess runs in total; fresh boot + every endpoint; settings
persistence across reboot; a sustained fault matrix, derived from that device's own real wiring
plan, proving graceful degradation and that the watchdog never starves under bounded failure; a
persistence-correctness sweep; recovery after a bounded fault clears; hotspot fallback with a real
answered UDP DNS query; NTP permanently unreachable; a real blocking hang proving the watchdog
backstop engages; a clean soak run at both `gc.threshold(-1)` and the project's chosen
`gc.threshold(32768)`, in that order — Part I.4(e)'s standing rule). Building this surfaced three confirmed Unix-port-only `socket`
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
`MICROPY_PY_SYS_SETTRACE=1`, so one binary backs both plain `scripts/test.sh` and `--coverage`
(E.5). RP2040 firmware never gets this flag. **Not inert when unused** (measured 2026-09-18,
corrected here and in CLAUDE.md): the flag makes the VM allocate a frame and a code object on every
call and every generator resume, callback or not, inflating every allocation figure measured under
this binary 4-5x relative to the firmware — see HEAP_FRAGMENTATION_MEASUREMENTS.md §1.2 item 7.

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
See CLAUDE.md's "Build-environment verification" for the re-check recipe.

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

`.github/workflows/ci.yml` runs **thirteen jobs** (twelve of them real work plus `web-changes`, a
path filter the four web jobs gate on), each its own stage so a failure names the tool
rather than going red under a shared "lint" label (corrected 2026-09-13 — this paragraph had
described a two-job workflow that stopped being true several stages ago). Python side:
`lint-and-typecheck`, `shellcheck`, `actionlint`, `zizmor`, `unit-tests` (`scripts/test.sh`,
building via `setup` on a cache miss), `unit-tests-coverage`, `digital-twin-e2e` and
**`firmware-build-verify`, which does
build a real `firmware.uf2` for wozi and verify it** — the "no RP2040 firmware-build CI stage yet"
this paragraph used to claim is long gone. Web side: `web-lint-and-typecheck`, `web-unit-tests`, `web-coverage`, `web-cross-browser-smoke`.

Cache key hashes **both** `versions.toml` and `setup_toolchain.py` — keying on `versions.toml`
alone once let a stale cached binary (built before `MICROPY_PY_SYS_SETTRACE=1`) survive across
commits, a real bug (`--coverage` failed in CI while passing locally). `unit-tests` additionally
runs its own retried `uv sync` before `scripts/test.sh`, so a third party's build-time download
failing cannot read as a red test result (CLAUDE.md's "Code quality tooling").

**The coverage rerun is its own job**, `unit-tests-coverage`, for the same reason `web-coverage` is
separate from `web-unit-tests`: `timeout-minutes` gates a whole job, not its real step, so a slow
instrumented rerun can kill a test step that already passed. Measured on run `34755468619`
(2026-09-13): the plain suite reported `60/60 files passed / ALL PASSED`, the `--coverage` rerun
then ran 13m24s longer, and the 30-minute cap cancelled the job — skipping `digital-twin-e2e` too,
on a tree with nothing wrong with it. Coverage gates nothing (E.5), so it gets its own budget.

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
PATH]` assembles a real `firmware.uf2` from a `buildgen`-generated device entry module + `src/` +
`ext/microdot.py` + the real website (H) — build-only. Every device needs its own
`devices/<device>.toml` (SPECIFICATION.md Part L); the generated boot entry (`buildgen.codegen.
generate_boot_entry_source()`) replaces the former hand-written `boot_entry/<device>_boot.py`
(retired, Session 6's finish criterion).

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

## B.14 MicroPython build overrides: a canonical, zero-touch patching framework

**Standing need**: a handful of real problems (so far: one fixed, two identified and planned) need
MicroPython's own *build behavior* changed — not this project's code — and none of them are things
upstream exposes as an ordinary, safe-by-default option. The wrong way to solve this is a one-off
hand-edit to the fetched `$PICO_TOOLCHAIN_DIR/micropython` checkout: it has to be reapplied by hand
after every fresh clone or version bump, it is invisible to code review, and it leaves no trace of
*why* once someone forgets. **`toolchain/micropython_overrides.py` is the one canonical place these
live instead** — every override there generates files or extra build flags entirely *outside* the
fetched checkout (never a single byte written into it), applied automatically by
`toolchain/setup_toolchain.py` on every build, from tracked, reviewed Python code. Each override
also *verifies a known anchor* in the pinned source before doing anything — a short excerpt of the
exact text it depends on — and raises a clear, actionable `OverrideError` if that anchor is gone,
rather than silently building an unpatched (or, worse, half-patched) binary. This is the same
"re-check every MicroPython-facing construct on a version bump" discipline CLAUDE.md's "Platform
target" section already establishes as standing practice — these anchors are exactly the kind of
thing to re-verify on the next `toolchain/versions.toml` `[micropython] ref` bump, alongside
everything else that section already tracks.

**Why not just a `CFLAGS_EXTRA -D...`, the way the mbedtls GCC-14 workaround and
`MICROPY_PY_SYS_SETTRACE=1` already do it?** That remains the right tool whenever the target macro
is itself written as `#ifndef X #define X ... #endif` upstream (lwIP's own options are - B.14.2).
It does **not** work for a plain, unguarded `#define` (B.14.1's case): confirmed directly
(2026-09-15) that a later plain `#define` in the same translation unit always wins over an earlier
command-line `-D`, unconditionally, and this project's own build already treats the resulting
"macro redefined" warning as a hard failure (`build_unix_port()`/`build_firmware()` grep their own
output for `warning:`). Those cases need a different mechanism - B.14.1 below.

**General shape every override in `toolchain/micropython_overrides.py` follows**: a `verify_*()`
function that reads one specific pinned-source file and raises `OverrideError` (naming the exact
file/line it expected, what to re-derive, and what real problem skipping the check would
reintroduce) if a known anchor string is missing; an `apply_*()` function that calls the verify
step first, then either writes small generator files into a directory the caller supplies
(never inside `micropython_dir`) or returns extra `make`/CMake variables, or both; and a docstring
covering the exact mechanism, why it's the mechanism (not a simpler one that doesn't actually
work), and what was verified. `toolchain/setup_toolchain.py`'s `build_unix_port()`/`build_firmware()`
call the relevant `apply_*()` unconditionally, every build - there is no opt-out flag, since an
override existing at all means the *unpatched* build is the one considered unsafe/insufficient.

**The first real test of any override here is not a dedicated test file - it's every ordinary
build.** Because `apply_*()` runs unconditionally inside `build_unix_port()`/`build_firmware()`,
simply running `uv run toolchain/setup_toolchain.py setup` (or `test`, or any of `scripts/test.sh`/
`scripts/run_digital_twin_ci.sh`/`scripts/run_unix_port_integration.sh`/`scripts/build_firmware.py`
— every one of them reaches the toolchain build through this same entry point, with no alternate
path anywhere in this project's own tooling) already exercises the anchor check and the generated
override end to end, on a genuinely fresh checkout, before a single dedicated test runs. A broken
anchor or a build that no longer accepts the injected variables surfaces immediately as a hard
`OverrideError`/build failure at that point - `tests_scripts/test_micropython_overrides.py`'s own
synthetic-fixture coverage exists for fast, isolated *unit* feedback on the override logic itself
(and for asserting the generated content's exact shape, which a successful build alone doesn't
check), not as the first or only place a regression would be caught.

### B.14.1 `unix_kbd_intr` (implemented) - safe SIGINT delivery for the Unix port test binary

**The problem, found root-causing a real, intermittent `digital-twin-e2e` CI failure**
(2026-09-14/15): `scripts/_digital_twin_ci_suite.py`'s shutdown step sends a real `SIGINT` to the
twin subprocess and expects a clean exit. Intermittently, only at `gc.threshold=32768` (never at
`gc.threshold=-1` in the same job), the process instead exited with code 1. Root-caused by
reproducing it directly (a tight hammer loop of the real `Run 3`/`Run 5` suite functions,
gc.threshold=32768, immediate SIGINT after boot, across all 6 real devices): the crash is a
genuinely **corrupted, impossible traceback** —
```
Traceback (most recent call last):
  File "digital_twin/run_generic_integration.py", line 473, in <module>
  File "/home/user/sensors/digital_twin/machine.py", line 1, in _build_i2c_chip
TypeError: 'frame' object isn't iterable
```
— line 473 is a plain `print()` statement that cannot call anything, `machine.py:1` is that file's
own module docstring not a function definition, and MicroPython has no user-facing `frame` type at
all. This is VM-internal state corruption, not an application bug: `mp_obj_get_type_str()` read a
type name from memory that used to hold (or still holds) an internal frame/code-state struct.

**Root mechanism, confirmed against the pinned `v1.29.0` source** (`ports/unix/unix_mphal.c`'s
`sighandler()`, gated by `ports/unix/variants/mpconfigvariant_common.h`'s `MICROPY_ASYNC_KBD_INTR
(!MICROPY_PY_THREAD_GIL)` - true for this project's non-threaded "standard" variant build): the
Unix port's default SIGINT handling calls `nlr_raise()` - an immediate, `longjmp`-based stack
unwind - **directly from the async signal handler**, which can fire at *any* point in the
interpreter's C execution, not just a safe bytecode-dispatch boundary. `gc.threshold(32768)` (vs.
MicroPython's own reactive-only `-1` default) means proactive `gc_collect()` calls happen far more
often, at essentially arbitrary points in real wall-clock time - which is exactly why the exit-1
flake only ever showed up at that threshold: it dramatically raises the odds that a real SIGINT
lands mid some non-reentrant operation. This is the *same root mechanism* as the already-fixed
Part F.6 heap-lock bug (SIGINT landing mid `gc_collect()` specifically leaves `GC_COLLECT_FLAG`
stuck) - `digital_twin/unix_port_gc_unwedge.py`'s `unwedge_heap_after_interrupt()` patches that one
specific downstream symptom, but does nothing for an interrupt landing mid some *other*
non-reentrant operation (frame/exception bookkeeping, in the reproduced case), which can corrupt VM
state beyond anything a userspace `gc.collect()` call can repair. Closing the root cause - never
delivering the interrupt at an unsafe point at all - closes every symptom in this whole class, not
just the one already found.

**The fix**: MicroPython's own `unix_mphal.c` already implements the safe alternative in its
`#else` branch (used automatically whenever `MICROPY_ASYNC_KBD_INTR` is 0) -
`mp_sched_keyboard_interrupt()`, which only *schedules* the interrupt, actually raised later at the
VM's own next safe bytecode-dispatch checkpoint via `mp_handle_pending()`. This is the same
deferred-signal-handling pattern CPython itself uses. `toolchain/micropython_overrides.py`'s
`apply_unix_kbd_intr_override()` forces this path for the Unix "standard" variant this project's
tests/twin actually run under, without editing anything inside the fetched checkout:

- `verify_unix_kbd_intr_anchor()` checks that `ports/unix/variants/mpconfigvariant_common.h` still
  contains the exact pinned line `#define MICROPY_ASYNC_KBD_INTR         (!MICROPY_PY_THREAD_GIL)`
  before doing anything else.
- The mechanism: `make`'s own `VARIANT_DIR` (`ports/unix/Makefile`: `VARIANT_DIR ?=
  variants/$(VARIANT)`) is only ever defaulted with `?=`, so passing it explicitly on the command
  line cleanly redirects the whole variant-config lookup with no `-I`-ordering tricks needed (a
  `CFLAGS_EXTRA`-appended `-I` was tried and empirically confirmed to lose: `ports/unix/Makefile`'s
  own `-I$(VARIANT_DIR)` is added to `CFLAGS` *before* `CFLAGS_EXTRA`, so the compiler always finds
  the real, unpatched header first). The override directory contains a generated
  `mpconfigvariant.h` that `#include`s the real one **by absolute path** and then
  `#undef`/`#define`s `MICROPY_ASYNC_KBD_INTR` to `0`; a generated `mpconfigvariant.mk` that plain
  `include`s the real one; and (mirrored via the freeze-manifest DSL's own `include()` primitive,
  never copied - so it can never silently drift from a future pinned-version change) a generated
  `manifest.py` that includes the real one. **Deliberately never a symlink**: [MicroPython issue
  #12671](https://github.com/micropython/micropython/issues/12671) documents that the Unix port's
  build breaks when the variant directory itself is a symlink, because the real
  `mpconfigvariant.h`'s own `#include "../mpconfigvariant_common.h"` fails to resolve through it -
  using a real file with an absolute-path `#include` instead sidesteps this entirely, since the
  *real* header's own relative include still resolves correctly relative to its own real,
  non-symlinked location. `VARIANT=standard` is passed alongside `VARIANT_DIR` explicitly, since
  otherwise `VARIANT_DIR ?= variants/$(VARIANT)`'s own companion line (`VARIANT ?=
  $(notdir $(VARIANT_DIR:/=))`) would derive `VARIANT` from the *override* directory's name and
  rename `BUILD ?= build-$(VARIANT)` away from `build-standard`, which every other script in this
  repo hardcodes.
- **This whole pattern (an external, `_DIR`-suffixed variable redirecting a port's own config
  lookup to an out-of-tree directory) is not a workaround invented for this project** - it is
  MicroPython's own officially-documented mechanism on other ports (`make BOARD=myboard
  BOARD_DIR=~/src/projects/myboard`, from the project's own porting guide); the Unix port's
  `VARIANT_DIR` is the same `?=`-based mechanism, just not spelled out in that port's own README
  (which only documents selecting an *in-tree* variant via `VARIANT=`).

**Verified**: preprocessing the resulting `unix_mphal.c` directly confirms the safe branch
(`mp_sched_keyboard_interrupt()`) is selected, never `nlr_raise()`. End-to-end: a hammer loop of
the real `Run 3` (sustained bus-fault matrix) + `Run 5` (bounded-fault recovery) suite functions at
`gc.threshold=32768`, across all 6 real devices, ran clean for a combined 700+ iterations against
the patched binary with zero shutdown failures - the same harness reproduced the real corrupted
traceback directly against the unpatched, upstream-default binary. `build_unix_port()` (both call
sites - the frozen-verification build and the vanilla test-rig rebuild) applies this unconditionally.
Unit coverage (synthetic fixture trees, no real compile): `tests_scripts/test_micropython_overrides.py`.

**Re-verification checklist for a MicroPython version bump** (do this alongside CLAUDE.md's
existing "Platform target" re-check practice, not as a separate pass): re-read
`ports/unix/unix_mphal.c`'s `sighandler()` and `ports/unix/variants/mpconfigvariant_common.h` at
the new pinned tag. If the anchor line is untouched, nothing else to do -
`verify_unix_kbd_intr_anchor()` passing is itself the confirmation. If it changed shape (renamed,
`#ifndef`-guarded, or the whole async/immediate-interrupt mechanism restructured), update the
anchor string and, if the mechanism itself changed, `apply_unix_kbd_intr_override()`'s generated
`#undef`/`#define` pair - then re-run this section's own hammer-loop verification before trusting
the new pin's shutdown safety again; do not assume "it built" is sufficient. If a future
MicroPython release makes deferred keyboard-interrupt delivery the Unix port's own default (i.e.
inverts `MICROPY_ASYNC_KBD_INTR`'s default value), this whole override becomes a documented no-op
and can be retired outright once confirmed.

### B.14.2 `lwip_connection_counts` (documented, not yet implemented)

**Real future need**: increase the number of simultaneous TCP connections/`netconn`s lwIP allows
(rp2 port firmware only - `ports/rp2/lwip_inc/lwipopts.h`), for scenarios needing more concurrent
sockets than the built-in defaults allow (the real webserver's own `max_connections` ceiling is a
separate, `src/`-level concern - this is about how many the underlying TCP stack itself can hold
open at once, upstream of that).

**Mechanism, verified workable against the pinned source, not yet wired in**: unlike B.14.1's case,
lwIP's own `lib/lwip/src/include/lwip/opt.h` guards every one of these options properly -
```c
#if !defined MEMP_NUM_TCP_PCB || defined __DOXYGEN__
#define MEMP_NUM_TCP_PCB                5
#endif
```
(likewise `MEMP_NUM_NETCONN`, default `4`, and every other `MEMP_NUM_*`/`TCP_*` count in that
file) - and this project's own `ports/rp2/lwip_inc/lwipopts.h` does not currently set any of them,
so there is nothing to conflict with. A plain `CFLAGS_EXTRA` `-D` addition in `build_firmware()`
(the same mechanism already carrying the mbedtls GCC-14 workaround) would therefore work cleanly,
e.g. `-DMEMP_NUM_TCP_PCB=8 -DMEMP_NUM_NETCONN=8` - no generated files, no `VARIANT_DIR`-style
redirection needed at all.

**What a real implementation still needs**: a `verify_lwip_connection_counts_anchor()` checking the
exact `#if !defined MEMP_NUM_TCP_PCB` guard (and each other option actually being overridden) is
still present and still a real, honored `#ifndef`-family guard at the pinned tag - a future lwIP
import that, say, hardcodes these instead would need this override reworked, not silently ignored.
Pick real target values against a concrete scenario (a specific concurrent-client count this
project actually needs to support) rather than an arbitrary increase - each `MEMP_NUM_*` bump also
grows the lwIP memory pool's own static RAM footprint, which is a real, finite budget on a Pico W
(SPECIFICATION.md Part I.1's own CYW43-firmware-reduces-usable-heap finding applies here too).

### B.14.3 `littlefs_flash_storage_size` (documented, not yet implemented)

**Real future need**: reduce (or otherwise resize) the bytes of on-board flash the rp2 port
reserves for its own littlefs filesystem, freeing that space for something else in the firmware's
own flash layout.

**Mechanism, verified workable against the pinned source, not yet wired in**: this is not a raw
macro at all — it is already a **first-class, directly-supported `make` variable** on this pinned
version. `ports/rp2/Makefile` already forwards it straight through:
```makefile
CMAKE_ARGS += -DMICROPY_HW_FLASH_STORAGE_BYTES=$(MICROPY_HW_FLASH_STORAGE_BYTES)
```
and the board's own `boards/RPI_PICO_W/mpconfigboard.cmake` wraps its default in `if(NOT DEFINED
MICROPY_HW_FLASH_STORAGE_BYTES) set(MICROPY_HW_FLASH_STORAGE_BYTES 868352) endif()` (848KB;
`mpconfigport.h`'s own generic rp2 default, used by boards that don't override it, is `1408 * 1024`
= 1408KB) - a passed-in value cleanly wins. So the real implementation is a single extra `make`
argument to `build_firmware()`, e.g. `f"MICROPY_HW_FLASH_STORAGE_BYTES={value}"` - no CFLAGS, no
generated files, no guard concerns of any kind.

**What a real implementation still needs**: a `verify_littlefs_flash_storage_size_anchor()`
checking both that `ports/rp2/Makefile` still forwards this exact variable name into `CMAKE_ARGS`
*and* that the target board's own `mpconfigboard.cmake` still guards its default with `if(NOT
DEFINED ...)` (a board file rewritten to hardcode the value instead would silently ignore an
override otherwise) - both at the pinned tag, before trusting a passed-in value took effect.
**This one is real-hardware-adjacent in a way the other two aren't**: shrinking the reserved
littlefs region changes the on-flash layout of a board that may already have deployed units
carrying real persisted state there - CLAUDE.md's own "real hardware go-ahead" gate and
SPECIFICATION.md Part C.8's flash/NVM write-safety rules apply to *validating* a chosen value on
real hardware, not just to building it.

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

- `_NAME = const("<SENSOR>")` — this driver type's fixed base name. `self.name` (`instance_name
  (_NAME, name_ext)`, C.14.1) is the real dict key everywhere at runtime (`get_dict_data()`/
  `get_dict_cfg()`/`get_error_counter()`, every `err_s(...)`'s implicit `self.pr.name` prefix) —
  identical to `_NAME` whenever `name_ext` is empty (every driver's default), diverging only for a
  second same-type instance.
- `<SENSOR> = namedtuple("<SENSOR>", (...))` — measurement shape, ending in a `TS` timestamp field.
  Field names become `make_dict()`'s keys (C.6).
- **`_NAME`'s string and the namedtuple's type-name string must be identical, always** — define
  the two next to each other. A class with no namedtuple (`NeopixelDriver`) is exempt by
  construction.
- `_VAL_<ABBREV> = const((("<Field>", "<type>", default, min, max, special),))` — one schema tuple
  per config field (C.5). `_WIRING: "WiringSchema" = ((toml_field_name, required_driver_class),)`
  — one tuple per live cross-instance dependency this driver's constructor needs (C.14.2); omit
  entirely if the driver has none.
- `<Sensor>_DeviceSession(Lockable)` — pure boilerplate, identical in all three drivers:
  ```python
  class <Sensor>_DeviceSession(Lockable):
      def __init__(self, i2c_device: I2CDevice) -> None:
          super().__init__()
          self.i2c_device = i2c_device
  ```
  Copy verbatim (swap `I2CDevice`/`SPIDevice`).
- `<Sensor>_I2C`/`_SPI` (layer 2), `<Sensor>_Reader` (layer 3). `*_Reader` constructor order (match
  exactly): bus handle, sensor-specific addressing/pins/callbacks/cross-instance wiring references
  (`_WIRING`-declared parameters, C.14.2), `trigger_sec: int = <n>` (only if configurable — SGP40
  isn't, C.11 item 6), `max_module_error: int = 5`, `name_ext: str = ""` (C.14.1), then (if
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

### C.3.2 UART variant — harmonized precedent

`asy_uart_driver.py`'s `UART(Lockable)` now has a real caller: `asy_uart_comm.py` (Part J), wired
into `dev` as the two ends of the bench rig's crossover jumper. It keeps no logger of its own for
the same reason `asy_i2c_driver.py` and `asy_spi_driver.py` keep none — every failure surfaces to
exactly one upstream owner, which does the logging (C.7.1).
Settled precedent: **one merged class**, not a session+protocol pair (no bus-sharing concept, so
the two lock layers collapse without losing distinction — the accepted shape for any future
point-to-point wrapper); **CRC framing lives in the bus-wrapper class itself** (no natural layer 2
above a point-to-point link to own it instead), joined by a **pluggable frame codec** in the same
position (`framing_codecs.py`, Part G.2 — pass-through by default, so the default emits exactly
what it always did); **`cancel_read_timeout()`** is a legitimate externally-triggerable cancel for
another coroutine's unbounded wait — a **latched request acknowledged on every exit from the locked
region**, published through monotonic request/ack counters and bounded so the call is provably
terminating. (It was an `asyncio.Event` handshake, which could both drop a request and hang the
canceller forever; see `UART_C_PORT_CHANGELOG.md` B15.); **raise contract** (re-verified against `ports/rp2/machine_uart.c` at v1.29.0): a
hardware framing/parity/overrun error is never raised — delivered corrupted, dropped, or skipped
silently instead, and `write()` can short-write. **`any()` cannot raise either** (re-traced
2026-09-13, since every read in the driver now funnels through it): `mp_machine_uart_any()` calls
`uart_drain_rx_fifo()`, which absorbs the OE/BE/PE bits with no error path, then returns
`ringbuf_avail()`; the generic `extmod/machine_uart.c` wrapper only boxes that int. `_buffered()`'s
`except (OSError, MemoryError)` is therefore defence in depth against a future port, not a
reachable rp2 case — worth its two lines precisely because it is the single choke point — a third position distinct from I2C (raises) and
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
cfg_vals) -> WriteValidity` validates and stages first, then pushes live only fields that both
changed (`"Valid"`, not `"Unchanged"`) and have a registered push callback; every field reports
independently including unrecognized keys; a whole-operation validation failure (an invalid
`ConfigManager`, or an internal error raised out of `write_config()`/`_set_mgr_cfg()` itself, never
a later flash-write failure - see below) marks every requested key `"Failed"`. **Since WP5**
(SPECIFICATION.md Part F.2), the actual flash write is deferred to an independent task, so
`"persisted"` here really means "validated and staged" - a genuine disk write failure surfaces only
later, as a logged `errno` on `cfgmgr.pr`, never back through this return value or the caller's own
response; `_set_dict_cfg()` therefore has no way to observe it and none is expected to. **A push
callback always receives the coerced, persisted value, not the caller's
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

**`reset()` writes unconditionally; `_store_err()` does not.** The asymmetry is deliberate.
`_store_err()` refuses to touch FRAM before `setup()` has run — a half-filled ring written over a
not-yet-restored chunk is stale state. A cleared ring is the opposite: it is exactly what the
caller asked to persist, so `reset()` writes it straight away and marks the logger initialized once
that write succeeds, which makes the later `setup()` return early instead of restoring over it. A
failed write leaves `initialized` False and `setup()` still runs normally. Without this, a
`ResetErrors` landing in the boot window was silently undone: every FRAM-backed logger runs its own
`pr.setup()` from *inside its task* (SGP40/BMP3XX/SCD30 in `read_loop()`'s `_init_*()`, NEOPIXEL in
`neopixel_signal()`, NOTIFY in `monitor_loop()`, SYSTEM in `start_and_check_tasks()`) while the
webserver's task does nothing before `start_server()` — so the server answers while some loggers
are uninitialized, and which ones is decided by task-scheduling order. The result was a *partial*
clear behind a `200`, inconsistent across modules. Fixed 2026-09-11; covered at the mock, twin and
flash tiers.

**A `ResetErrors` answering `OK` on a write the chip acknowledged but did not physically store is
accepted behaviour, not a defect** (owner decision, 2026-09-17; recorded here so the reasoning is not
re-derived). Detecting that would need a deferred read-back and a second failure path, which is
overkill for the risk: **if the bus transfer completed without error, the chip is trusted to have
stored the value.** `reset()` clears the in-RAM ring before attempting the write, so `/status` reads
0 either way, and a chip-level failure surfaces at the next boot — `setup()` restores the old history
— rather than at the call. The narrower case where `_write()` itself returns False (a *detected*
failure, `_diag()`-logged and not reflected in the response) has the same disposition: only reachable
with a chip that is already failing.

**Confirmed on real hardware (dev bench board, 2026-09-17).** Three properties of this layer that
had only ever been shown against the twin's fake chip were re-run against the real FM25xx, with the
board's own `dev` firmware:

- **The all-or-nothing abrupt-restart guarantee holds, with the "all" branch actually exercised.**
  WIFI's FRAM-backed log read `counter=3`, history `W5, W4, W4` before an abrupt `hard_reset()` and
  byte-identical values after it — not a partial remnant, and not the vacuous `0 → 0` a test built on
  a deauth would produce (`bench.kick_all_stations()` logs nothing at all; only a real
  `bench.ap_down()` outage generates entries).
- **`PUT /status {"ResetErrors": true}` clears every chunk and yields while doing it.** All 21 of
  `dev`'s chunks (`UART_init`/`UART_resp` included) read back 0 with their rings cleared, and a
  concurrent `GET /status` stayed at 0.56-0.76s throughout a `PUT` lasting 8.1s — so the sweep never
  holds the event loop and cannot threaten the 8388ms watchdog cap. Its cost is fixed **per chunk**
  (~305ms), not per history entry. Timings and the remaining load-case concern: BACKLOG.md item 24.
- **The UART link keeps its never-block invariant under sustained FRAM writing.** Across a 20.8s
  window carrying three back-to-back `ResetErrors` calls (~6.9s each, i.e. near-continuous chunk
  writing), `dev`'s crossover pair completed 23 further transfers with zero failures and held its 1s
  exerciser cadence — the guarantee in CLAUDE.md's `asy_uart_comm.py` rule, shown against the real
  peripheral rather than only the bench jumper at idle.

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
is expected; only overlap *within* one row matters. **The base range (`errno` 1-9/`wrnno` 1-2,
reserved to `base_classes.py`) and each driver's own 10+ numbering are a convention this table
records, not one the code itself enforces** — nothing raises if a new module picks a colliding
number or starts below 10; get it right by checking this table before assigning a new one (WP8),
the same "check the shared catalog first" discipline Part G.1 states generally.

| Module | `errno` | `wrnno` | Notes |
|---|---|---|---|
| `base_classes.py` | 1-9 | 1-2 | Reserved base range — every driver starts at 10+. |
| `config_manager.py` (`CFGMGR_<name>`) | 1-15 | 1-6 | Sequential in source order. 14=the deferred flush's own write failure (`_flush_staged()`, WP5); 15=a validation-phase `MemoryError`/`AttributeError` in `write_config()` itself, split off 14 once the actual file write moved into the separate deferred method. |
| `asy_fram_manager.py`/`asy_fram_driver.py` (`FRAM`) | 10-100 | 60-84 | `AsyFramManager` 10-88 (busy/idle status-byte helper spreads a base across 2-7 values per call); `FRAM_SPI` 89-98 (not-initialized ×5, invalid-range ×2, readback mismatch, lock-timeout, device-ID guard) + `wrnno` 81-83 (WRDI-stuck, WEL-didn't-set ×2). **WP8**: 99=`get_values()`'s own "access not locked" internal-contract violation, 100=`set_values()`'s (each its own number per the "grouped by the raising method" convention, matching the sibling not-initialized pair); `wrnno` 84=`_write()`'s "currently write protected" refusal — a benign, expected outcome (matches `AsyFramManager`'s own "communication paused" `wrn_s` precedent, `wrnno` 60/70/80), so `wrnno` rather than `errno` unlike the two lock violations. |
| `asy_bmp3xx_driver.py` (`BMP3XX`) | 10-22 | — | 10=init, 11=periodic read, 12=config read at init, 13=config write at init, 14=config read at store-time, 15-20=oversampling/filter forwards, 21=trigger-interval, 22=batched snapshot read. |
| `asy_scd30_driver.py` (`SCD30`) | 10-25 | — | 10=init, 11=periodic read, 12=unused (no init-time config), 13=stop-continuous-measurement, 14-25=per-field forwards. |
| `asy_isl29125_driver.py` (`ISL29125`) | 10-38 | 10-13 | 10=init, 11=periodic read, 12=config read at init, 13=config write at init, 14=config read at store-time, 15/17/19/21=resolution/range/IR-offset/IR-adjust getters, 16/18/20/22=their setters, 24=derived-persistence reapply, 25=trigger-interval, 26=gain-ratio/filter-coefficient setters (shared), 27=autorange-threshold/dwell setters (shared), 28=`_read_sensor_dict()`, 29=auto-range threshold-register write, 30=auto-range RNG-bit write, 31=status read, 32=all-ones bus-fault confirmation, 33=brownout re-apply, 34=diverged-config re-apply, 35=paired gain-ratio calibration leg (`_read_on()`), 38=`set_range_auto()`. `wrnno` 10=brownout detected, 11=chip config diverged from shadow, 13=range decided by the periodic path only for 5 decisions running (the interrupt line may be dead, requirement 17/C.11.5). **12 is retired, not reused**: it used to mean "saturated on the high range", but that status is a harmless, transient, always-current measurement fact, not a fault — it now lives in the measurement output as the `Overrange` field (mode-aware: true whenever nothing left could mitigate the saturation — the configured range itself under Fixed range, or Automatic Range already on its highest setting) rather than as a log entry. |
| `asy_sgp40_driver.py` (`SGP40`) | 10-18 | 10-13 | 10=init, 11=periodic read, 12=config read at init, 13-18=backup read/write/clear/deserialize/serialize/compensation. `wrnno`=backup missing/stale — a missing/not-yet-available *compensation* reading is no longer one of these (C.14.2's own note), only a genuine compensation-source read exception (`errno=18`) still logs. |
| `asy_wifi_service.py` (`WIFI`) | 11-19 | 1-7 | 11=mode-switch...17=hardware give-up, 18=disconnect-timeout; `wrnno` 1-3=missing-config, 4-7=WLAN status. **WP8**: 19=the hotspot auto-shutoff timer's own soft-callback-drop self-heal (`_hotspot_client_absent()`, F.1) actually firing — a real, actionable event, not the routine WiFi-mode-transition noise this file's own module docstring already documents everything else here as. |
| `asy_ntp_client.py` (`NTP`) | 11-20 | 1-3 | 11=missing-config...19=time-calc, 18/20=interval-fallback/give-up; `wrnno`=callback failures. |
| `captive_dns.py` (`DNSSRV`) | 1-3 | 1-3 | 1=invalid server_ip/netmask, 2=loop exception, 3=disconnect-cleanup; `wrnno` 1=dropped reply, 2=invalid recvfrom, 3=socket teardown incomplete. |
| `system_service.py` (`SYSTEM`) | 1-7 | dynamic (`n+1`) | 4=task-error-budget-exceeded, 5=`_log_dead_task()` recovering a real raised exception, 6=recovering a `CancelledError`-ended task (previously invisible, now persists). **WP8**: 7=`_apply_level()`'s own caller-supplied level-setter callback failing — the one caller-supplied-callback call site in this codebase that hadn't already persisted via `err_s()`. |
| `asy_notification_service.py` (`NOTIFY`) | 10-13 | 1-5 | 10=value-callback, 11=threshold-config-read, 12=`local_time_callback`, 13=`request_signal_cb`. Renumbered off 1-4 once `_error_check()`'s active use here collided with base's reserved 1/2. |
| `api_response.py`'s `handle_set_cmd()` | 99 | — | One defense-in-depth catch (a caller `post_fct`/`post_asy_fct` raising) — fixed at 99 since it runs against any registered module's `.pr`. |
| `asy_webserver_service.py` (`WEBSERVER`) | 1-6 | 1-5 | 1=unexpected exception in dispatch, 2=`system_cmd` callback, 3=`notification_led` callback, 4=uncaught exception via `errorhandler(Exception)`, 5=`notification_pause` callback, 6=one `/status` streamed-fragment source failed. `wrnno` 1-5=connection-lifecycle reclaim reasons. |
| `asy_neopixel_driver.py` | — | — | No persisted logging. |
| `asy_i2c_driver.py`/`asy_spi_driver.py`, `asy_udp_socket.py`, `asy_dns_client.py` (client) | — | — | Deliberately no logging — every failure surfaces to exactly one upstream owner. Coverage audit closed, no gaps. |
| `asy_uart_comm.py` (`UART`, `_NAME` only as the default) | 10-34 | 10-14 | 10-16=construction refusals (payload_size, timeout, role, bus handle, allocation — the module's own buffers *and* a frame codec whose one long-lived scratch failed, since a codec that reports itself not ready would otherwise fail every write instead — rxbuf, missing callback), 17=not-ready gate, 18=role refusal, 19=frame validation, 20=missing/mismatched ACK, 21=write, 22=read timeout, 23=payload too large, 24=destination allocation, 25=size mismatch, 26=callback, 27=re-entrant call, 28=wrong frame kind, 29=GET id mismatch, 30=listen loop, 31=peer initiated simultaneously, 32=bytes arriving but no frame ever valid (a CRC/baud/`payload_size` mismatch), 33=streamed chunk short-filled, 34=a caller's own argument refused (command id outside a byte, a non-integer or negative size, a non-buffer payload or destination). `wrnno` 10=resync, 11=drain bound reached, 12=fault episode cleared, 13=a *rise* in the driver's cumulative `cancel_unacknowledged` (reading it as a flag reported every later healthy cancel as wedged), 14=a callback declined a command id. **Exactly one of 10/11/14 is persisted per fault episode, and 14 at most once per command id until a `reset_error_counter()`** — deduping only the `errno` left every fault still persisting its own resync warning, which refilled the bounded history and evicted the entry naming the cause — and 14 escaped that fix until 2026-09-12, so a peer polling one unimplemented id spent two slots per refusal and erased a ten-slot history in five rounds; remembering only the *last* declined id then left an alternation between two unimplemented ids flooding it just the same, which a 32-byte one-bit-per-id map closed on 2026-09-13. **`wrnno` 11 outranks 10 for the episode's single slot** (owner decision, 2026-09-18, closing BACKLOG open question 23) — `_resync()` drains first and then persists 11 when the drain hit its bound, 10 otherwise, so "the peer never stopped sending", the one signal separating a babbling or misconfigured peer from ordinary line noise, is what a field log actually carries. The budget is unchanged at one persisted warning per episode. The same change closed the inverse leak: `setup()`'s boot drain is deliberately not a fault and not counted, yet it used to persist 11 on every boot of a babbling link, because the bound logged itself rather than flagging the caller. Numbered from 10 to stay clear of `base_classes.py`'s reservation even though this is not a `SensorReader` subclass, and disjoint from any owner's own range where the logger is reached through. |
| `asy_uart_driver.py` | — | — | Deliberately no logging — every failure surfaces to its one upstream owner (`asy_uart_comm.py`), the same treatment the other bus drivers get. `cancel_unacknowledged` is a plain counter that owner reads and logs under its own `wrnno` 13. |

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

**Lock 1's scope is per-driver, and the FRAM path's is a whole block operation, not a single
transaction** (owner's decision, 2026-09-18). `FRAM_SPI.__aenter__` takes lock 2 and then lock 1
together and holds both for one `_write_chunk`/`_read_chunk`/`_clear_chunk` — roughly 25 chip-select
cycles — so the byte-level commands inside run as plain synchronous functions
(`get_values_sync()`/`set_values_sync()`) with no coroutine and no lock acquisition each. That is
what makes the path affordable: it took a blank FRAM-backed logger `setup()` from 122,880 to
13,696 board-equivalent bytes. Ordering is unchanged (2 before 1), a second SPI device still
interleaves — between block operations rather than between commands — and the event loop still gets
a scheduling point after every status-byte pair, after each payload command and per read slice.
An I2C driver keeps the per-transaction scope: it has no equivalent synchronous session, and
SPECIFICATION.md Part F.5.8 refuses the generalisation. Full measurement and the ladder of scopes
considered: `HEAP_FRAGMENTATION_MEASUREMENTS.md` §7C/§7C.1 and §11 item 6.

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
(`test_sgp40_general_call_reset_does_not_corrupt_concurrent_scd30_and_isl29125_transactions`). The only
structural fix (a bus-wide "quiesce every session before broadcasting" mechanism) is flagged for a
project-owner decision if ever revisited, not justified without evidence of a live risk.

**Standing rule — bus-hazard test coverage, read before adding a new bus-facing device or rewiring
a bus (project owner's explicit standing direction)**: every promoted I2C/SPI device gets
same-device read-vs-write concurrency coverage, cross-device interleaving coverage (if sharing a
bus), and an address/command sweep, across as many of four tiers as apply (cheapest first):

1. **Mock/unit, two distinct collections, by design (project owner's own reframing,
   2026-09-15) — not one migrating into the other**:
   - **Sensor/module-specific hazards** — a driver's own known quirk, whose assertions only make
     sense for that one driver (ISL29125's destructive `0x08` status-read interleave, a driver's
     own full-API-surface address/command sweep) — live in that driver's own test file
     (`tests/test_asy_<driver>_driver.py`), alongside its other unit tests. These are hand-written,
     from the datasheet, and stay that way; no generic template could derive them.
   - **Genuinely generic, cross-sensor/driver-agnostic hazards** — the scenario *shape* (cross-device
     interleaving, general-call/broadcast effects, fault isolation, parallel sessions on one
     device, and whatever else belongs in this catalog) applies regardless of which specific
     drivers are involved — live in `tests/test_bus_hazard_multi_device.py`, which runs
     unconditionally as the permanent home for this category. It is not a staging area for the
     generated scheme below and is never retired or thinned once a generated equivalent exists for
     one of its scenarios (see the note at the end of this list) — extend it directly whenever a new
     driver-agnostic hazard shape is identified, the same way a new sensor-specific one goes into
     that driver's own file.
   - **Automatically assembled per-bus coverage also exists, alongside both of the above**,
     generated from a device's own real TOML wiring rather than hand-paired
     (`tests/test_bus_hazard_generated.py` + the per-driver adapter catalog in
     `tests/_bus_hazard_catalog.py`) — a third, complementary source of generic cross-sensor
     coverage, not a replacement for the hand-written generic collection above. The two are
     deliberately allowed to overlap in what they prove (layered coverage, not redundancy to prune)
     since they answer different questions: the generated scheme proves "this real device's actual
     wiring survives its own worst case," assembled automatically from the TOML so a new device or
     rewired bus needs no hand-written test at all; the hand-written generic file proves a hazard
     *shape* in isolation (including shapes the generated scheme structurally cannot produce, e.g.
     a rogue general call against a bus with no real broadcasting occupant).
2. **Digital twin** (`tests/test_digital_twin_bus_hazard_concurrency.py`) — the real object graph
   against higher-fidelity chip fakes under genuine concurrent task load. Its shared
   `_run_real_task_graph_and_assert_healthy()` helper also runs one TOML-driven generic pass over the
   same already-booted graph, alongside its hand-written checks.
3. **Flash tier** (`tests_hardware/flash/test_bus_concurrency.py`) — real hardware, dev bench only.
   **Real-hardware write-safety constraints, project-owner-mandated**: (a) respect any real
   NVM/EEPROM write budget — ideally at most one real write per bus-hazard test group, via a
   session-scoped fixture; (b) a concurrency test exercising persisted config must construct the
   real protocol-layer driver directly (the DUT), never the `*_Reader` layer, so it never touches
   the RP2040's own flash filesystem.
4. **Bench tier** (`tests_hardware/bench/test_bus_concurrency_under_api_load.py`) — real hardware,
   full HTTP stack, concurrent load. Extend the worker set only with requests safe under both
   constraints above (`GET` always safe; `PUT` only if documented command-only/never-persisted).

**The generated (mock + twin) coverage's own full requirements — every one of these is required to
call a bus-facing module's generated bus-hazard coverage "fully promoted and integrated", not
optional polish (project owner's explicit direction):**

- **Iterate every real I2C bus on every real device**, not a hardcoded single device/bus pair —
  `tests/test_bus_hazard_generated.py` dynamically generates one test group per `(device, bus)` pair
  found in that device's own generated wiring-plan JSON (`build/generated_src/
  sensortask_<device>_wiring_plan.json`), so a bus with 2+ real occupants automatically gets the full
  cross-sensor scenario set and every bus (single-occupant included) gets its own address/command
  sweep and its own same-device write-vs-own-read check. A new device or a re-wired bus needs *zero*
  edits to this file to be picked up.
- **Every real bus-attached driver has a `tests/_bus_hazard_catalog.py` adapter** — `scd30`, `sgp40`,
  `isl29125`, `bmp3xx` today. `build_bus_occupants()`/the address-sweep scenario both fail loud
  (`KeyError`) for a driver with none, rather than silently skipping that driver's own coverage.
- **Every timing-sensitive scenario systematically sweeps WHEN the hazard fires**, not one fixed
  injection point — a single fixed `asyncio.sleep(0)` before a write/general-call can miss a race a
  different timing would catch. `scenario_a_write_does_not_disturb_concurrent_sibling_reads`,
  `scenario_general_call_does_not_disturb_concurrent_siblings` and
  `scenario_same_occupant_own_write_does_not_disturb_own_concurrent_read` each rebuild fresh
  bus/occupant state and re-run once per offset across the reader loop's own iteration count, so one
  trial's leftover queue/log state can never mask or fake a later trial's result. Unrestricted on
  mock/twin (a fake bus has no real write-wear budget); real hardware's own limit is the next bullet.
- **Real-hardware tier parity is required, not optional — every generic mock/twin scenario type
  needs a real-hardware equivalent** for whichever bus a real device's own topology makes it
  applicable to (E.6.6's own general rule, applied here to bus-hazard specifically), with exactly
  one exception: **SCD30's own on-chip NVM write is opt-in, off by default, and capped at one real
  write per test session** — every real SCD30 write, flash wear being a real, always-relevant
  concern on real hardware, is gated behind `tests_hardware/conftest.py`'s
  `--allow-persistence-writes`/`@pytest.mark.persistence_write` (the single global permission: without it, a
  full flash-tier run spends zero real SCD30 writes, including the one routine per-session write
  `scd30_continuous_measurement_triggered` would otherwise make for the whole bus-hazard group).
  Any additional test that needs to fire SCD30's own write a second time is gated behind a further,
  narrower flag/marker pair, `--allow-scd30-extra-write`/`@pytest.mark.scd30_extra_write`, that is
  AND-gated on top of the global one — never an independent flag standing in for it, and never
  substitutable for it (passing only the extra-write flag still deselects the test). One flag
  decides whether any real SCD30 write happens at all; the second only ever narrows that further.
  Real hardware has no literal equivalent of the mock tier's `asyncio.sleep(0)`-count
  offset sweep (a yield count means nothing against a real preemptible interpreter and real bus
  timing) — a deliberately varied set of real elapsed-time delays is the honest, tier-appropriate
  substitute, cycled across several write cycles for an unrestricted writer; a write under SCD30's
  one-shot budget fires at one deliberately chosen representative offset instead, since a real
  multi-offset sweep is structurally impossible under that budget, not a design choice to skip it.
  Every other real write the sweep exercises (BMP3xx's/ISL29125's own config registers, both
  volatile per their datasheets) has no such budget and runs fully unrestricted on real hardware too.
- **Flash-tier bus-hazard coverage is always a subset of bench-tier coverage, never the other half**
  — whatever gets added to `tests_hardware/flash/test_bus_concurrency.py` gets a bench-tier
  counterpart in `tests_hardware/bench/test_bus_concurrency_under_api_load.py` too, driven through
  the real HTTP/REST stack instead of the bare driver (a `PUT`/`GET` pair reaching the same real I2C
  write/read the flash-tier script drives directly). Two allowed, structural exception shapes — both
  must be recorded explicitly as such, never left as a silent asymmetry between the tiers:
  1. **No REST-layer path exists to the write at all** — e.g. SCD30 registers zero `_push_callbacks`
     (`asy_scd30_driver.py`), so no `PUT /sensors` field can ever reach either its write-vs-siblings
     or its same-device write-vs-own-read hazard.
  2. **The hazard's own trigger is only reachable at driver setup/task-restart, never on a live,
     already-running system** — e.g. SGP40's real general-call broadcast only fires from
     `SGP40_I2C._reset()`, itself only called from `initialize()` at setup time; the one REST field
     that superficially resembles a trigger (`SGPResetVOC`) calls a software-only
     `vocalgorithm_reset()` instead and never reaches it. A bench test cannot force this hazard
     without a real reboot mid-load, which would confound the very load under test — confirmed by
     reading the real call chain, not assumed from the field's name.
- **`test_bus_hazard_multi_device.py` is never retired** (project owner's own reframing,
  2026-09-15, superseding an earlier plan to retire it once every test had a generated
  counterpart) — it is the permanent home for genuinely generic, driver-agnostic hazard shapes
  (item 1 above), run unconditionally alongside the generated scheme, not a staging area migrating
  into it. A generated equivalent existing for one of its scenarios is not a reason to delete or
  thin that scenario; the two are complementary, layered coverage. A test in this file that turns
  out, on inspection, to actually be sensor/module-specific (its assertions only make sense for one
  driver's own quirk) moves into that driver's own test file instead — the file's own bar is
  "genuinely generic," not "not yet generated."

**Per-real-device applicability, re-verified against all 6 device TOMLs (SPECIFICATION.md Part L's
Session 6.2)**: "cross-device interleaving if sharing a bus" only actually applies to a device that
does. Checked directly against every real `devices/*.toml`: `wozi` wires `sgp40`+`bmp3xx` together
on `i2c1`, and `dev` wires `scd30`+`sgp40`+`isl29125` together on `i2c1` (the `isl29125` instance is
dev-only — the ISL29125 migration's own scoping) — the only two real devices with any sensor pair
sharing a bus at all. `arzi`/`klkizi`/`grkizi`/`schlafzi` each wire `scd30` alone on `i2c0` and
`sgp40` alone on `i2c1` (no `bmp3xx`/`isl29125` instance at all) — there is no cross-device
interleaving window on these 4 devices for tier 2's own
`test_<device>_real_task_graph_survives_concurrent_bus_load_including_a_real_general_call()`
scenario to prove anything about, so that test staying wozi/dev-only is complete coverage, not a
gap to extend. FRAM's own same-device hazard coverage (tier 2's remaining tests: injected-fault
recovery, RX-overrun absorption, write-protect/storage-pause gating) and the WiFi-disconnect-under-
load scenario are device-independent by construction (FRAM sits alone on its own dedicated SPI bus
on every real device, unaffected by which other sensors exist alongside it) — proven once, against
one real assembled object graph (wozi), rather than six times over at six times the real
wall-clock cost (the WiFi-disconnect scenario alone is an unavoidable real ~75s).

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

### C.9.1 Read-trigger timer stagger: no-coincidence guarantee (WP7, verified 2026-09-16)

**Design intent (owner-established, not re-derived here)**: every sensor's read period is settable
in whole multiples of one second, one second being the shortest. The read-trigger timers are
started **staggered evenly across exactly one second in total** — not at a fixed per-timer gap —
so that, being real hardware timers that do not drift relative to one another once armed, **no two
sensor reads ever coincide, for the entire runtime, for any combination of configured periods**: no
harmonics, no beat frequencies, no races from period overlap. This is also why the timer starters
are triggered by another real timer (precise, interrupt/alarm driven) and not by `asyncio.sleep()`,
which offers only coarse, drift-prone timing. The one-second *total* spread is load-bearing and
must not become a fixed per-task gap or be rescaled — a fixed gap of `g` ms for `N` timers spans
`(N-1)*g` ms, which grows without bound as more timers are added and can itself become a multiple
of some sensor's own period, reintroducing the exact coincidence this design exists to prevent.

**The mechanism, traced end to end**:
- `SystemService._timer_sequencer()`/`start_timers()` (this file) starts each `get_timer_starters()`
  entry via a chain of `Timer.ONE_SHOT` callbacks, `_TIMER_BASE_PERIOD` (1000ms) divided by
  `len(timers) + 1` apart — the `+1` is what keeps the total span strictly under 1000ms even as the
  *last* timer starts, so every start offset lands strictly inside `(0, 1000)` ms, never at 0 or at
  a multiple of 1000ms itself. **This is a different stagger from the one three paragraphs up in
  Part A.7's boot-latency note** — that one staggers `get_task_starters()` *asyncio task* starts via
  plain `await asyncio.sleep(1.0 / len(task_starters))` inside `start_and_check_tasks()`, a coarse,
  scheduler-timed spread with no coincidence claim attached to it. The two mechanisms share
  "~1 second, N participants" only because both happened to pick that shape independently, not
  because they are the same code path — don't conflate them. **A third list, the one-time boot
  `setup()` batch (WP6, this Part's own text above the timer stagger), is deliberately not staggered
  at all** — no delay of any kind between calls, only a `feed_watchdog()` after each. It carries none
  of the read-timer stagger's coincidence concerns (these are one-shot construction calls, not
  periodic triggers) and must not be folded into either staggering mechanism, nor have a delay
  inserted between its own calls to "match" them — that would only reintroduce the very watchdog-
  starvation risk WP6 closes, for no benefit.
- Each software-counter-based driver (`asy_bmp3xx_driver.py`/`asy_isl29125_driver.py`) arms its own
  `Timer.PERIODIC` at a fixed 1000ms base tick (`asy_sgp40_driver.py`'s is also 1000ms, fixed, and
  never divided down — "voc algorithm needs 1s period fixed", its own comment) and increments a
  plain counter (`trigger_counter`/`self.trigger_counter`) each tick, firing the real read-trigger
  event only once the counter reaches the user-configured `trigger_period` (whole seconds). So the
  real read-trigger time for one of these three sensors is exactly `start_offset + k * 1000ms` for
  integer `k`, where `start_offset` is that sensor's own `_timer_sequencer()`-assigned start moment.
- **The no-coincidence proof**: every configured period is `1000 * n` ms for a positive integer
  `n`, so `gcd` of any two sensors' periods is itself always a multiple of 1000ms. Two sensors'
  read times coincide only if the difference between their `start_offset`s is congruent to 0 modulo
  that `gcd` — i.e. only if it is itself a multiple of 1000ms. Since `_timer_sequencer()` assigns
  every `start_offset` a distinct value strictly inside `(0, 1000)` ms (never 0, never ≥ 1000, and
  never repeated - integer division of 1000 by up to a handful of distinct small divisors doesn't
  coincide in practice either, and even a tie would only delay, never invalidate, the argument since
  the *sequencer* itself never reissues the same delay to two different timers at the same instant),
  that difference can never be a multiple of 1000ms — so the two sensors' read times can never
  coincide, for any combination of configured periods. This holds for the entire runtime, not just
  at startup, precisely because the underlying mechanism (below) never drifts.
- **Confirmed against the real rp2 MicroPython source, not assumed** (`ports/rp2/machine_timer.c`,
  the pinned v1.29.0 tag): a `Timer.PERIODIC`'s underlying Pico-SDK repeating alarm reschedules
  itself by returning `-self->delta_us` from its own alarm callback (`alarm_callback()`) — a
  **negative** return value tells the SDK's alarm pool to reschedule relative to the alarm's own
  previous *target* time, not to "now" (a positive return would do the latter, accumulating drift
  under scheduling jitter). This reschedule happens unconditionally inside the low-level alarm
  callback itself, before `mp_irq_dispatch()` ever runs the Python-level callback - so even a
  dropped **soft** callback (Part F.1's own documented depth-8-scheduler-queue drop) only ever
  costs that one tick's `.set()` notification, never the timer's own phase: the next tick still
  fires at the mathematically exact target time, not "one period after whenever the previous
  callback happened to run." This is precisely what "do not drift relative to one another once
  armed" means in the design intent above, and it is what makes the no-coincidence proof hold for
  the whole runtime rather than only approximately, near startup.
- **One real, deliberate exception to the pure phase-math argument, found while verifying this**:
  `asy_scd30_driver.py` does **not** use the counter-based mechanism — its own 500ms base tick
  (`start_trigger_timer`) only counts consecutive ticks (`trigger_half_sec = 2 * trigger_sec`)
  towards *arming* an IRQ-driven trigger (`scd_init_irq()`), and the actual read fires on the
  sensor's own physical data-ready interrupt (`irq_pin`), not at a purely-computed phase offset.
  SCD30's own base tick still gets a staggered, drift-free start via the identical
  `_timer_sequencer()` mechanism, but its *real* read time additionally depends on the physical
  sensor's own internal measurement cycle - so the strict "never coincide" proof above applies
  rigorously to BMP3xx/ISL29125/SGP40 relative to each other and to SCD30's own IRQ-*arming* checks,
  but SCD30's actual read moment is IRQ-modulated on top of that, not purely phase-determined. This
  matches the sensor's own real field behavior (an IRQ-driven data-ready signal, not a synthetic
  polling schedule) and is not a defect - flagged here, per this Part's own scope, as a fact about
  the design's actual boundary rather than left implicit.
- **Regression coverage**: `tests/test_system_service.py`'s `_timer_sequencer()`/`start_timers()`
  tests already cover the stagger's own arithmetic (`_TIMER_BASE_PERIOD / (len(timers) + 1)`, one
  ONE_SHOT chain, `timers_running` only set once every starter has run); no new test was added for
  this WP, since it verifies and documents an existing, already-tested mechanism rather than
  changing it (`system_service.py`/`buildgen/codegen.py` are read-only for WP7, per its own scope).

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

### C.11.1 Keeping a chip fake honest — the conformance probe

A chip fake drifts from the part it models silently: every test still passes, because the tests and
the fake share the same wrong assumption. The ISL29125 is the first driver with a standing guard
against that, and the pattern generalises to any new bus-facing device. Ported here from `main`'s
own PR #75; the findings below were measured on `main`'s real hardware run and apply unchanged to
this branch's byte-identical driver/chip-fake port.

`tests_hardware/device_scripts/isl29125_mock_conformance_probe.py` is one probe that talks **raw
`machine.I2C` only** — the single layer the real board and `digital_twin/machine.py` both
implement — so the identical file runs against real silicon over `mpremote` and against the chip
fake under the Unix port. `tests_hardware/isl29125_conformance.py` runs the twin half and diffs
the two; the flash-tier gate that calls it is
`tests_hardware/flash/test_sensor_accuracy.py::test_isl29125_register_probe_matches_the_digital_twins_fake_chip`
(wired 2026-09-15 — the porting session above had left this orphaned, per its own note that used to
stand here). Keys whose value depends on the light falling on the part are excluded **by
value** and covered by the probe's own derived yes/no keys instead, so nothing is merely unchecked.

**What the first real run found (2026-09-12), every item a fake that no test could have caught:**

| Behaviour | Real ISL29125 | The fake had |
|---|---|---|
| Address pointer | flat across the whole `0x00`-`0x0E` map — a 16-byte read from `0x00` returns id, `CONFIG1`-`3`, both thresholds, status and all six data bytes | one pointer per register block, zero-padding at each block's end |
| Past `0x0E` | keeps clocking zeros; does **not** roll over to `0x00`, despite p6's burst-*write* text | zero padding (correct) |
| Reserved config bits | read back zero — `0xFF` gives `3f`/`bf`/`1f`, matching the driver's own `_CONFIG*_MASK` | echoed whatever was written |
| `CONVENF` (`0x08` B1) | set by a completed conversion, cleared by the status read, flat `0x00` while powered down | never modelled at all |
| `RGBCF` (`0x08` B5:4) | **not** cleared by the status read; zero while powered down | not cleared (correct); retained in power-down (wrong) |
| `BOUTF` after the `0x46` reset | reads `0x00` — the reset command does not raise it | restored to `0x04`, treating reset like a power-up |
| `BOUTF` after a status read | **cleared by the read itself** | survived the read |
| The threshold persistence counter | restarts when `RGBTHF` is **cleared**, not on every status read (C.11.1.2) | reset on every read that touched `0x08` |

`digital_twin/_isl29125_chip.py` (already ported onto this branch, byte-identical) models every row
above; the findings are recorded here purely as the evidence trail for why it looks the way it
does.

#### C.11.1.1 `BOUTF`'s real lifecycle — settled 2026-09-13, and p12 is wrong about it

Measured on a genuinely just-powered board, with a status read as the **first** transaction (the
pre-ISL firmware never touches the part, so nothing had disturbed it):

| event | `BOUTF` | source |
|---|---|---|
| power-up | **set** (`0x08` reads `0x04`) | measured; p12 agrees |
| a status read of `0x08` | **cleared** | measured; **p12 contradicts this** |
| the `0x46` reset command | **cleared** | measured (first probe run: reset, then read `0x00`, with no status read before it) |
| a write of `0x00` to `0x08` | cleared | measured; p12 agrees |

p12 says the flag "should be reset to LOW by an I2C **write** command during the initial
configuration". The write does work — it is simply not the only thing that clears it. The
destructive status read clears `BOUTF` alongside `RGBTHF` and `CONVENF`; only the `RGBCF` field
survives a read.

**Consequences.** The fake models all four rows now, and separates the two events that look alike:
`_reset()` is the `0x46` **command**, `simulate_brownout()` is the **supply** event that raises the
flag again — a test wanting a brownout must call the latter. For the driver this is benign and
was already handled: `_handle_status()` reads `0x08` exactly once per cycle, so a real brownout is
reported exactly once, which is what `_recover_brownout()`'s own `_brownout_seen` latch already
assumes. Nothing in `src/` needed changing.

#### C.11.1.2 The threshold persistence counter and the once-per-cycle status read

Found by reading the fake rather than by the probe, then settled on the board (2026-09-13). The
fake reset `_prst_count` on **every** read that transferred `0x08`. If that were right, the
driver's own defaults would make the hardware interrupt unreachable: `PRST = 4` needs
four consecutive out-of-window RGB cycles (4 × 303 ms ≈ 1.21 s at 16 bit), `SampleInterv = 1`
reads the status register every second, and a count knocked back to zero each second never reaches
four.

Measured directly, with both thresholds parked at `0x0000` so the window is crossed in any light
and the persistence counter is the only variable:

| `PRST` | no reads for 3 s | one read per second, 8 reads |
|---|---|---|
| 1 | `RGBTHF` set | set in **8 of 8** |
| 4 | `RGBTHF` set | set in **4 of 8**, strictly alternating, INT low on exactly those |

The alternation is the whole answer. A read at t = 1 s finds the flag clear and does **not**
disturb the count, so the flag still sets at ≈ 1.21 s and the read at t = 2 s sees it — and that
read, which does clear it, restarts the count, so t = 3 s misses and t = 4 s sees it again. A
counter reset by every read would have produced 0 of 8; one never reset at all would have produced
8 of 8 (the flag would re-raise on the very next conversion after each clear). Neither happened.

**Reproducing it.** The *unit* half (RGB cycles, not channel integrations) is automated and now
asserted: `tests_hardware/device_scripts/isl29125_real_irq_edge.py`'s `_measure_persist_unit()`
times a `PRST` = 4 assertion and fails the script if the answer is not `rgb_cycles`, because
`persist_for_interval()` is built on it. The *restart* half above was a one-off bench probe, not a
committed script; the table's own method is the recipe — park both thresholds at `0x0000` so any
light crosses the window, then vary only the status-read cadence.

**Consequences.** The fake now resets `_prst_count` only inside the `if self._status &
_STATUS_RGBTHF` branch. `src/` needed no change — the driver already reads `0x08` exactly once per
cycle, which is the cadence this was measured at. What it does change is the twin: before the fix,
any twin-tier scenario at the real defaults was silently exercising the periodic fallback only,
with the interrupt path dead and nothing saying so.

#### C.11.1.3 The persistence window is derived from `SampleInterv`, never configured

Requirement 5 makes the threshold interrupt's GPIO mandatory and requirement 17 makes the periodic
re-check the safety net *behind* it. At the shipped defaults it was the other way round, and the
arithmetic says so: `PRST = 4` means four whole RGB cycles, 4 × 303 ms = **1212 ms** at
16 bit, while `SampleInterv = 1` re-evaluates the same switch condition in software every
**1000 ms** — with no persistence requirement at all. The software path therefore won every race,
and the hardware fast path was dead by construction.

**Settled 2026-09-13 by removing the field from the API entirely** (owner's decision): correcting
the default only moved the trap, since any later `SampleInterv` change could walk back into it.
`ISL29125_I2C.persist_for_interval()` now derives PRST as **the largest setting whose window still
closes inside one sample interval**, so the invariant holds for every combination the schema can
express rather than for the shipped pair alone. At 16 bit / 1 s that picks 2 — the configuration
measured below — and at 12 bit, where a cycle is ~16× shorter, it picks 8 and rejects far more
transient noise at no cost. Both inputs re-apply it when they change, which is why `SampleInterv`
is no longer a software-only knob: changing it writes CONFIG3.

The dedicated `wrnno` this trap used to need is gone along with the field it warned about: a
warning the derivation makes unreachable is complexity without a reader. The dead-line detector
therefore has a single meaning again — five decisions in a row went to the periodic path, so the
line looks dead — which is the question it was always meant to answer. **This branch's own C.7.1
table has no ISL29125 row yet** (flagged separately, below) — check the driver's own `errno=`/
`wrnno=` call sites directly for the current numbering rather than trusting a number quoted here.

Measured on the bench (2026-09-13), six forced crossings per setting, one reader, same scene:

| `PRST` | window at 16 bit | interrupt-led | periodic-led | switch latency |
|---|---|---|---|---|
| 4 | 1212 ms | 1 of 6 | **5 of 6** | pinned at ~1000 ms — the sample interval, not the light |
| 2 | 606 ms | **6 of 6** | 0 | 500-800 ms |
| 1 | 303 ms | **6 of 6** | 0 | 200-613 ms |

**Re-measured 2026-09-14**, after the settle window was fixed at two cycles (C.11.2). Three runs
of `isl29125_real_irq_edge.py`: **2.73 / 2.71 / 2.71 s**, all interrupt-led against a 30 s periodic
fallback. **That is not a regression against the 500–800 ms above, and the two numbers are not
comparable**: this script sets `SampleInterv = 30`, which the derivation turns into the largest PRST
the part offers (8 cycles, 2424 ms) — so most of the difference is the chip being *asked* to wait
longer before raising RGBTHF at all, and only ~303 ms of it is the settle doubling. The INT still
leads decisively. `settle discard 605/606` is directly visible in the driver's debug output.

**Two changes came out of the original measurement.** The window is **derived**, so at a 1 s interval
and 16 bit the driver picks 2 — still a cycle of transient rejection, and comfortably inside the
interval — while a longer interval or 12-bit resolution buys more. And the detector now keys on the
**line**, not the flag — see below. A third change, a separate warning for "the window outlasts the
interval", was made and then removed once deriving the window made that case unreachable.

**Why the flag alone was not enough.** `_note_decision_source()` originally counted a decision as
interrupt-led whenever `RGBTHF` was set in the status byte. But `RGBTHF` is raised by the *chip*,
so it is set exactly the same when the INT line is open — a missing pull-up or a broken jumper,
which is the fault requirement 17 (C.11.5) names. The driver now records the pin edge itself
(`_irq_fired`, set in the handler and consumed once per cycle) and requires **both** halves. This
also un-blinded the twin's own `isl29125:int_stuck_high` fault test, which had been passing for an
unrelated timing reason rather than because the detector worked.

**What this cost in test terms**: `test_isl29125_survives_recombined_realistic_lighting_scenarios`
(ported here as `tests_hardware/device_scripts/isl29125_lighting_scenarios.py`, wired into
`tests_hardware/flash/test_sensor_accuracy.py` 2026-09-15 — real segment durations sum to ~8.5
minutes, a genuinely long single test, not yet run against silicon) checks the dead-line warning
per scenario *and* asserts the run made at least five range switches, so the check can actually
fire.

### C.11.2 ISL29125 reference layer — the prior art, and the traps it closes

Every item here is something a future reader would otherwise re-derive, or "correct" back to a
worse answer.

**One owner per register — the property that makes the shadow model safe.** The driver keeps a
local shadow of `CONFIG1`-`CONFIG3` and writes it back whole; that is only sound while exactly one
function may touch each register.

| Register | Contents | Sole writer | Read by |
|---|---|---|---|
| `0x00` | Device ID / reset command | `reset()` (writes `0x46`) | `get_device_id()` |
| `0x01`-`0x03` | `CONFIG1`/`2`/`3` | `configure()` only | `get_config_snapshot()` only (one 3-byte burst, undecoded) |
| `0x04`-`0x07` | Low/high thresholds | `set_thresholds()` only | never read back |
| `0x08` | Status (`RGBTHF`/`CONVENF`/`BOUTF`/`RGBCF`) | `clear_brownout()` only | `read_status()`, **exactly once per cycle, destructive** |
| `0x09`-`0x0E` | Green, Red, Blue data, in that order | never written | `read_counts()`, one 6-byte burst |

Deliberately unused, with the reason, so nobody adds them later: `SYNC` (inverts the INT pin into
an input, p6/p10); `CONVEN` (muxes conversion-done onto the pin the thresholds need); `RGBCF` and
`CONVENF` (redundant — the data registers are double-buffered, p13).

**Prior art, and the three places this driver departs from it.** Four independent implementations
were read on `main`: the legacy `python/IndividualDrivers/` driver (this branch's own legacy tree
holds the same file, reference-only per CLAUDE.md), `jposada202020/MicroPython_ISL29125`,
SparkFun's Arduino library, and RIOT-OS `drivers/isl29125` (plus Linux's `drivers/iio/light/
isl29125.c` in a later pass).

1. **RIOT is the only prior art for the normalisation chain**, and this driver copies its shape
   (6-byte burst, `<< 4` for 12-bit, `range_FS / 65535.0` per LSB) deliberately — Linux's IIO
   driver independently confirms the same per-LSB scaling. The other three read per-channel and do
   no lux conversion at all.
2. **Nobody does auto-range or CCT.** Both are this driver's own, which is why its twin-tier tests
   carry more weight than usual: there is no reference implementation to differential-test against.
3. **RIOT's threshold scaling truncates, and that is a bug not to inherit.** `65535 / 375` in
   integer arithmetic is 174, not 174.76. `ISL29125_I2C.fraction_to_counts()` exists as a named method with
   a test named after this specifically (`..._does_not_truncate_like_the_riot_driver`) so it cannot
   recur.

SparkFun's `reset()` additionally verifies `CONFIG1`-`CONFIG3` **and** status all read `0x00`; this
driver verifies the config registers only, for two independent reasons (C.11.1.1 and the
destructive-read invariant above).

**Colour chain (`math_helpers.py`).** Three decisions that look like defects unless you know them:

- The **sRGB/Rec.709 D65 matrix is pinned as literals** because two published roundings of the same
  matrix differ in the 6th decimal (the CSS WG corrected its own), and both pass a `1e-6`
  tolerance. `test_rgb_to_xyz_coefficients_are_the_pinned_literals()` asserts the literals exactly
  rather than recomputing them from primaries, which would pass against either set.
- **The two published McCamy forms are algebraically identical**, not contradictory: flipping the
  sign of the denominator flips `n`, which flips the sign of the odd-power terms. Do not "correct"
  one into the other — it changes nothing but the reviewer's confidence.
- **The matrix is a placeholder by the datasheet's own statement**, not for want of a better source:
  FN8424 p13 Eq. 1 says its coefficients "will be changed respectively depending on the system
  setup". A per-unit matrix is the calibration hook; the reported colour is relative. There is
  deliberately **no gamma decode** — the sRGB transfer function undoes display encoding, while this
  sensor's output is linear in irradiance. The colour helpers take triples already normalised 0-1
  by the driver's own chain, so an out-of-domain input means that chain is broken and is rejected
  rather than clamped.

**Config-field classification.** Device and maths constants are not config fields: requirement 1
(C.11.5) governs *preferences*, and a dark-count offset, a CCT floor or a gain-learn period is not
one.

**The switch-down point is derived, not configured** (owner, 2026-09-14). It was `AutoRangeDown`,
a field carrying the one relation a per-field schema cannot express — `d <= u / (2r)`, with `r` the
range ratio — policed at runtime by `_check_cross_field()`. That made it the same class of trap
`AutoRangePersist` was (C.11.1.3): a user-facing number whose only correct values are a function of
another field, where a wrong one is a rejection the user has to decode, and where a single PUT
moving both ends could pass or fail on key order alone. `_down_thresh()` now returns
`AutoRangeThresh / _AR_DOWN_DIVISOR`, and the field and the cross-field check are both gone.
`AutoRangeUp` was renamed `AutoRangeThresh` to match: it sets both ends of the hysteresis now, not
just the upper one.

The divisor stays `2 × 26.67`, the part's **nominal** range ratio, deliberately not the measured
`GainRatio`. The factor 2 absorbs that field's whole 20.0–34.0 band — at the worst end a light
sitting exactly at the threshold reads `t/34` after the switch, still 1.57× above `t/53.33` — so
coupling the two would add a dependency without moving a single decision.

**The settle margin is a constant, not a field** (same pass). `AutoRangeSettle` exposed 1–10
conversion cycles to discard after a range change, where the hardware has exactly one principled
answer and no scene, light level or resolution makes another one right. It is `_SETTLE_CYCLES = 2`:
two rather than one because the ADC restarts during the I²C write itself (p10, Table 7) while the
driver arms its deadline once that write has *returned*, so one cycle can land on the wrong side of
that tie. `ISL29125_I2C.settle_cycles` went with the field — the protocol layer no longer carries
reader policy across the layer boundary at all.

**The Renesas application notes are unobtainable — do not re-attempt.** The four Intersil notes the
promotion wanted are not reachable (the vendor site refuses, no mirror carries them, and the
"AN1910" hits elsewhere are NXP's and Microchip's unrelated documents of the same number). Both
things they were wanted for are settled without them: the 12-bit cycle time comes from the
datasheet's own oscillator/counter model (p6, "the n-bit (n = 12, 16) counter inside the ADC", so
101 ms × 2⁻⁴ ≈ 6.3 ms), and the CCT matrix is a placeholder by p13's own wording.

### C.11.3 Calibration is user-triggered, user-applied, and writes nothing by itself

Owner's design, 2026-09-13, replacing an hourly background learner that persisted its own result
to a FRAM chunk. Three separate properties, and each is load-bearing:

**The applied factor is ordinary config.** `GainRatio` is a schema field like any other — `float`,
plausibility-banded to 20.0–34.0, defaulting to the nominal 26.667 — and `_gain_correction()` is
its only reader. **Only a user PUT ever changes it.** The driver never writes its own config, so
every flash write on this module stays on the REST path, which is the property Part F.2's
power-cycle recovery argument depends on. It is also what made a separate persisted-learner FRAM
chunk unnecessary.

**Measuring is a bounded run, started by hand.** `ISLCalibrate` is command-only (the special-alone
schema shape, C.5.2.1) and starts a window of `_CAL_WINDOW_MS`. While it is open the read loop's
own path takes sandwiches; the run ends early on convergence, or when the window closes. Nothing
schedules it, so normal operation pays nothing: a sandwich costs two range switches and two settle
windows, which would otherwise be a permanent tax on every sample interval.

**The measurement is a sandwich, not a pair, and that is the whole point.** Read this range, the
other, then **this range again**. The dominant error in this measurement is the scene changing
between the two legs, and a pair alone cannot distinguish a real ratio from a light that moved —
both produce a plausible number. If the first and third readings disagree by more than
`_CAL_STABILITY_TOL`, the sandwich is discarded however good the ratio looks. Convergence then
requires `_CAL_CONVERGE_N` consecutive stable sandwiches agreeing within `_CAL_CONVERGE_TOL`,
because a slow drift produces a run of self-consistent wrong answers.

**The result is a measurement, not a setting.** A candidate is published as `GainMeas`, riding the
same tuple as `Lux` and the colour fields, and held for `_CAL_HOLD_MS` before clearing. The user
reads it and copies it into `GainRatio` if they want it used. **A refused measurement is reported
by absence**: `GainMeas` stays `None`, which is the feedback — there is deliberately no warning for
an unusable scene, because a scene outside the overlap band is a fact about the light, not a fault.
Refusal reasons go to the debug log only. A real bus failure during a leg still logs an error.

**Proven on real silicon, 2026-09-14 (on `main`)** — the first sandwich any real chip has measured.
Three runs at ~138 lx (~37% of the low range's full scale), each converging early on three agreeing
readings within ~6–8 s: `24.012 → 23.916 → 24.131`, `23.703 → 23.841 → 23.915`, `24.128 → 24.046 →
23.869`. All nine candidates inside 23.70–24.13, a 1.8% spread. `GainRatio` read 26.666666 before
and after every run, confirming the driver never writes its own config. With the pixel parked dark
the sequence is empty and the error log stays empty — refusal by absence, exactly as designed.

**Applying the measured ratio cut the cross-range continuity step from 11.4% to 0.4%**, a ~28×
reduction on the same stationary light. That is the half of the mechanism nothing had exercised
before, and it is what the whole design is for.

**One interaction the bench found, and it is not a defect in either half** (2026-09-14). The
overlap-band gate tests **`green_counts`** — green is the quantity the sandwich divides, so it is
green that must clear the dark floor — while `_evaluate_range()` decides on **`max(counts)`**,
because a clipped red destroys Hue/Sat/CCT whatever green is doing. Both are right for their own
question. The consequence is that a strongly-coloured scene can be parked by auto-range on the high
range, where its green is too small to calibrate from, even though the *same* light on the low range
gives green ~24× larger and calibrates immediately. Measured: a blue-dominant white at ~153 lx
approached from above holds the high range with peak > 1044 counts and green ~1006, and calibration
refuses for the whole 120 s window. Approached from below it settles on the low range and converges
at once. **The operator procedure is therefore to park the scene dark first and let auto-range settle
onto the low range before raising it to the overlap level.** Loosening the gate to peak would be
worse, not better: it would admit scenes whose green is at the dark floor and silently produce a bad
ratio instead of refusing.

**One consequence worth knowing**: the third leg runs even when the second failed, because it is
also what puts the range back. Skipping it on a clipped or unreadable partner would strand every
later sample on the wrong range — caught by its own test, not by reasoning.

### C.11.4 The range ratio is not a constant — it varies with signal level

**Not an open question and not a defect: a measured property of the part, recorded because it sets
the limit of what any single `GainRatio` can do.** Unresolvable with one device and no reference
meter, so this is recorded as a bound, not tracked as something to decide.

Measured 2026-09-12 on `main`'s bench unit, static light, protocol layer only, with the stale
conversion window discarded. Six illuminants × three channels = 18 independent estimates, and the
pattern is unambiguous: in every scene the **brightest** channel has the **lowest** ratio,
regardless of colour. That makes it a level effect, not a spectral one.

| scene | low counts (G,R,B) | ratio (G,R,B) |
|---|---|---|
| ambient | 7645, 5995, 4101 | 28.11, 28.01, 28.09 |
| red `(6,0,0)` | 20298, **29674**, 8415 | 27.14, **24.44**, 29.32 |
| green `(0,6,0)` | **29068**, 9816, 16555 | **24.89**, 29.30, 27.92 |
| blue `(0,0,6)` | 13497, 5940, **37436** | 29.73, 28.15, **23.40** |
| white `(4,4,4)` | 32469, 24548, 36331 | 24.19, 25.05, 23.42 |

A level sweep agrees independently: low-range peak 7637 → 28.08, 36106 → 23.29, 50408 → 22.49,
64078 → 21.55. A third data point (2026-09-13, the envelope test's continuity measurement): one
stationary light at ~140 lx read 132.50 lx pinned to the 375 range against 147.76 lx pinned to the
10000 range, an 11.5 % step implying ~23.9 — sitting exactly between the ~28 at ambient and the ~22
near full scale.

PWM dimming cannot explain it: both ranges share the same 101 ms integration, so a duty-cycle
artefact cancels in the ratio. The likeliest reading is **low-range compression well below full
scale**. A high-range under-read at small counts fits the same data equally well, and separating the
two needs a reference meter, so this stays stated as the observation rather than as a mechanism.

**What it means for the driver.** The model is one scalar — `GainRatio`, plausibility-banded to
20.0–34.0 — and the whole observed span sits *inside* that band, so the guard never fires on it. A
ratio measured in the overlap band (where the low range is near its top) reads ~22–23, which is
right for switch-point continuity and is arguably exactly where it should be measured. The corollary
is the uncomfortable one: at genuinely low light the true ratio is ~28, so an applied 22.5 makes a
low-light cross-range comparison **worse**, not better. A measured instance of that: the driver
reported one static ambient as 37.84 lx on the high range against 39.91 lx on the low, 5.5 % apart —
matching nominal 26.67 against the true 28.08 exactly. **28.16 is therefore not "this unit's gain
ratio"; it is its ratio at ambient level only.**

C.11.3's design is what makes that survivable rather than a flaw. Calibration is a user-triggered run
under conditions the operator arranges, and the candidate is applied only if the operator copies it
across — so the model is still one scalar, but *which* scalar is a deliberate choice rather than a
property of whatever light happened to pass a gate. **Calibrate at the level you care about**, and
expect a ratio measured near the switch point to stay right there and drift by the amounts tabulated
above elsewhere.

**Do not re-raise this as actionable.** Whether the ~28 → ~22 span is this specimen or the part needs
a second board and a reference meter, neither of which exists — it is not a decision anyone can make.
The measurements stay here because they bound what a single number can achieve, and because a second
unit arriving later would make them the baseline to compare against.

### C.11.5 ISL29125 settled requirements — the project owner's own list

The twenty decisions the promotion was designed against, as the project owner settled them. **These
are the "requirement N" the driver, its tests and the sections above cite by number** — the
numbering is load-bearing and must not be re-flowed. Each item's own working-out is deliberately
absent; what survives is the decision.

1. **Every setting is API-settable and persisted.** No compile-time constant for anything a user
   might want to change. Device and maths constants are not settings — C.11.2's classification note
   is this requirement applied.
2. **Resolution** is a user-selected config field (12 or 16 bit), never auto-managed.
3. **Range** is either a fixed value or `auto`, and the auto-range parameters are themselves
   settable.
4. **Outputs are lux, RGB and HSB, each normalised over the full span** — the pinned range when one
   is selected, the whole auto-range span when `RangeAuto` is on.
5. **The threshold interrupt is used, and its GPIO is mandatory**, the same way `asy_scd30_driver.py`
   treats its RDY pin. Not optional, so there is no `None` pin to guard against by construction.
6. **IR compensation is an API parameter.** The sensor is openly exposed — no IR-tinted cover — so
   the datasheet's bare-sensor guidance of ~40 codes is the applicable default, not p10's `0xBF`.
7. **Register ownership is the driver's.** The chip's hardware interrupt never surfaces to the user;
   if an interrupt-as-event notification is ever wanted, software raises it — the INT pin and the
   threshold registers stay private.
8. **RGB output is normalised 0-1.**
9. **HSB's low-light behaviour is accepted** — no log scaling and no validity flag. Settled; do not
   re-propose either.
10. **The API follows the same conventions as the other promoted drivers** (Part C).
11. **Measurement output is structured**: `RGB` and `HSB` are nested sub-objects, never flattened
    sibling keys.
12. **`OperationMode` is not exposed.** The driver sets and keeps RGB mode itself.
13. **`CCT` is part of the output**, carrying its placeholder-matrix and low-light-floor caveats
    (C.11.2).
14. **SUPERSEDED.** It required auto-range to be fully tunable — switch points, hardware transient
    rejection, settle margin, dwell, and a command to discard a learned ratio. Three of those are
    gone: the persistence window is derived (C.11.1.3), the settle margin is a constant (C.11.2),
    and the ratio is an ordinary config value with nothing to discard (C.11.3). What remains
    settable is `AutoRangeThresh` and `AutoRangeDwell`.
15. **Logging and error history follow the promoted-driver pattern in full** — a `PrintLog` per
    module plus one per `ConfigManager`, FRAM-backed when a `fram=` is supplied, the `_error_check()`
    leaky bucket, and its own range in C.7.1's table.
16. **The driver is self-healing and never reports a stale value as fresh.** `BOUTF` set means the
    chip lost its configuration, so the whole shadow is re-applied and the cycle discarded; startup
    tolerates transient I²C failure on the same leaky-bucket terms as steady state; and a sample the
    driver cannot prove is current is reported as `None`, never as the last reading re-stamped.
17. **Auto-range must not depend on the interrupt alone.** If the INT line never asserts — a missing
    pull-up, a broken jumper, a mis-set `INTSEL` — auto-range would freeze on whatever range it
    started on, with only saturated or near-zero readings to show for it. The periodic read
    evaluates the same switch condition, so the interrupt is the *fast* path and the periodic read
    the *guaranteed* one, both on the same thresholds, dwell and settle.
18. **Scope is the `dev` variant only.** `wozi` carries no colour sensor and is not to be changed —
    on this branch specifically, `devices/wozi.toml` declares no `isl29125` instance and must not
    gain one.
19. **Every emitted value carries a declared unit and a declared precision.** The precision is a
    decided, tested property of each field, not an artefact of binary floating point. No driver in
    `src/` rounds any output; the renderer's `decimals` hint does it (Part H.5), so all four drivers
    stay identical to each other.
20. **Construction and `setup()` must complete on a bus where the chip never answers.** Not a
    restatement of 16 — that is a chip present and misbehaving, this is one absent for the whole
    run. This branch's own build-graph/digital-twin test coverage for `dev` must prove this property
    holds for the buildgen-generated object graph, the same way `main`'s hand-written
    `tests/test_sensortask_dev.py` proved it for its own hand-written one — confirm this is actually
    covered rather than assuming it, since the two branches' construction paths are not the same
    code.
21. **ADDED LATER (2026-09-15), not one of the original twenty above.** Saturation status is a
    measurement-output field (`Overrange`), never a log entry. Originally logged as `wrnno=12`
    ("saturated on the high range" — C.7.1's table), retired after a real-hardware bench test
    failure showed a harmless, transient, always-current sensor state should never be able to fail
    an error-log-empty assertion. `Overrange` is mode-aware: true whenever nothing left could
    mitigate the saturation — the configured range itself under Fixed range (auto-range off, so
    nothing will ever switch it), or Automatic Range already parked on its highest setting with
    nowhere further to switch. A saturated low-range sample *under* Automatic Range is deliberately
    excluded — requirement 17's own switch-up condition is already firing for it, so there is still
    an option left.

**One standing consequence, because it recurs**: CLAUDE.md's rule to verify a driver against the
legacy driver's own actually-proven field behaviour **has no purchase for this device**. The legacy
ISL29125 only ever ran a single config-and-read smoke test, and the project owner confirmed there is
nothing to preserve on those grounds — so the legacy code is evidence of intent at most, never of
proven behaviour, for naming, defaults and API shape alike.

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

## C.14 Instance naming, cross-instance wiring, and error/logger fan-in

Session 1 of the device-genericization initiative (`SPECIFICATION.md Part L`) — the mechanism
`buildgen/` (Session 3 on) now drives from each device's TOML, wired into the real build chain as
of Session 6. Applies to
`SensorReader`/`SensorReaderConfig` subclasses (the layer that can realistically have more than one
instance per device, e.g. two SCD30s, or several differential-pressure sensors); singleton services
(WiFi/NTP/SystemService/Neopixel/NotificationCoordinator/FRAM/the DNS server/the webserver) are
deliberately out of scope for the *naming* part below — never more than one per device by
construction — but do participate in the *fan-in* part, since that generalizes independently of
multi-instancing.

### C.14.1 Instance naming

Every `SensorReader`/`SensorReaderConfig` constructor takes a `name_ext: str = ""` parameter,
forwarded to `super().__init__(..., name_ext=name_ext)`. `config_manager.py`'s `instance_name(base,
ext) -> str` is the one place the rule is implemented: an empty extension (every driver's default
today) reproduces the driver's own fixed base name unchanged; a non-empty one appends `"_" + ext`.
`base_classes.py`'s `SensorReader.__init__` resolves this once into `self.name`, before either the
`logger=`-reuse or fresh-`make_logger()` branch, so `self.pr.name`/`self.name` always agree.
`SensorReaderConfig.__init__` then uses `self.name` (not the raw `name` argument) for **both** the
on-flash config filename (`config_<self.name>.cfg`) and the `ConfigManager`'s own `"CFGMGR_<self.
name>"` logger — so a name extension threads through the config filename automatically, with no
separate mechanism needed.

**REST dict keys must use `self.name` too, not a driver's `_NAME` module constant.** This was a
real, confirmed gap found during this session's audit: every `get_dict_cfg()` across the three
promoted drivers called `self._get_dict_cfg(_NAME, ...)` with the *literal* constant, and every
`get_dict_data()` called `make_dict(data, _FIELDS)`, which itself introspects `type(nt).__name__`
— the namedtuple's own fixed class name — neither keyed off `self.name` at all. With only one
instance per driver type in the system today, `self.name == _NAME == type(nt).__name__` always, so
this was invisible; a second same-type instance would have silently collided both REST dict keys
under the first instance's name. Fixed by threading `self.name` through both: `make_dict()` gained
an optional `name: str | None = None` override (`None` keeps today's introspection behavior, for
any caller that never needs more than one instance), and every `get_dict_cfg()` uses `self.name`
in place of the old `_NAME` literal — applied uniformly across every promoted driver's
`get_dict_cfg()`/`get_dict_data()`, including singletons (`AsyConnTime`/`AsyNtpClient`/
`NotificationCoordinator`), for D.10 consistency even though a singleton's `self.name` never
actually differs from its own `_NAME`.

The default (empty extension) case reproduces every existing path/filename/dict-key byte-for-byte
— covered by `tests/test_config_manager.py`'s `instance_name()` tests and each driver's own
`name_ext`-default regression test.

**Collision detection across a whole device's instance list is built in `buildgen/validate.py`**
(`_check_instance_name_collisions()`/`_check_instance_label_collisions()`, called from
`build_model()`) — it errors at build time when two instances would resolve to the same name with
no disambiguating extension. This Part's own contribution was making the naming mechanism itself
correct and usable; `buildgen` is what actually enforces it across a device's whole instance list.

### C.14.2 The `_WIRING` tuple convention

A driver that needs a live cross-instance value at construction time declares a `_WIRING:
"WiringSchema"` tuple next to its `_VAL_*` schema tuples. **Extended by Session 3 of
SPECIFICATION.md Part L** (the `buildgen/` generator) from this Part's original 2-element shape to a
5-element one, resolving that plan's own two open `_WIRING`-coverage questions (full rationale:
that session's PR description) — purely additive, no existing driver's constructor signature
changed to make this possible:

```
# @wiring <toml_field> <ProducerClass> <target> <required|optional> <kwarg|attr|setter>
```

**A comment, never a real Python value** — placed at module level beside the schema it describes.
Nothing the running firmware itself ever reads should become a real frozen-bytecode value just to
serve the generator (SPECIFICATION.md Part L.5), and this declaration is read only by
`buildgen/wiring.py`. It was a real `_WIRING` tuple until 2026-09-10; converting it, plus
`_VALUE_WIRING`, `_LIMITS` and the `TYPE_CHECKING` type aliases that described them, took 3,576
bytes out of `src/`'s frozen bytecode. Every element is a bare word, and dropping any one of the
five makes the tag fail the build loud rather than parse as "no tag here" (`tag_comments.py`).
`target`/`mode` say how the resolved producer instance is actually handed to the consumer:

- `mode="kwarg"`: the instance itself is passed as a constructor kwarg named `target` — e.g.
  `asy_sgp40_driver.py`'s `# @wiring fram_target AsyFramManager fram_storage optional kwarg`, the
  same shape on every other `fram_target`-wirable driver. (SGP40's own
  compensation-source dependency used to be a second wiring entry here, `comp_source` — see the
  generalized per-value mechanism below, which replaced it.)
- `mode="attr"`: the instance's `target` attribute/bound method is passed instead of the instance
  itself — `asy_notification_service.py`'s `signal_sink` resolves to `neopixel.request_signal`, not
  `neopixel`, satisfying `NotificationCoordinator.__init__`'s existing `request_signal_cb` parameter
  (left unchanged) while still keeping the *TOML-visible* link a direct instance reference, per
  SPECIFICATION.md Part L.2's "no getters, no callback functions in generated code" — the callback shape
  survives only as the one hand-written driver's own constructor parameter, never as
  generator-authored wiring.
- `mode="setter"`: `<consumer>.<target>(<resolved producer>)` is called once, after both already
  exist, instead of at construction time — `asy_wifi_service.py`'s
  `# @wiring led_target NeopixelDriver set_ext_led optional setter`, matching `set_ext_led()`'s own
  already-existing post-construction-call shape exactly.

This reuses the existing comment-tag family (`@requires`, and the planned `@web`) rather than
inventing new machinery; there is no separate "provides" registry — a constructed instance either is the
required class or it isn't, checked directly by whoever resolves the reference (`buildgen/`,
comparing the TOML's own `driver`/`name_ext` identity against `_WIRING`'s `producer_class`, never
against `instance_name()`/`_NAME` — see C.14.1's own naming-space distinction).
`[device.wiring]`'s two mandatory-infra-side fields (`led_target`/`fram_target`) resolve against
`_WIRING` declared on the *consumer* class instead (`AsyConnTime`/`SystemService`), since neither
is ever an `[[instance]]` entry itself.

**The constructor parameter itself is a direct reference to the producer's own instance** — passed
positionally/by keyword with the same name as `_WIRING`'s field (e.g. `fram_target`'s
`fram_storage` kwarg) — **not a getter or callback function.** The consumer reads the producer's
own already-concurrency-safe `get_data()` (`SensorReader`'s existing `_datalock`-guarded namedtuple
— C.4.2 — is itself the "locked state" value holder here; no new per-field `LockedValue` was
introduced) directly, inline, wherever the value is needed. This eliminates a real category of
hand-written wrapper functions that used to exist purely to close over a producer reference:
`sensortask_wozi.py`'s `sgp_comp_callback()` (SGP40's temperature/humidity compensation input) is
gone, replaced first by a `_WIRING`-declared `comp_source: SCD30_Reader` parameter, and — once
SPECIFICATION.md Part L.6.3 generalized per-value measurement wiring to every
module consuming one scalar out of another's `get_data()` result — by the independent
`temperature_source`/`temperature_field`/`humidity_source`/`humidity_field` parameters described in
C.14.3 below, resolved via `getattr(data, field_name)` inside `_read_sgp()` rather than a
whole-object reference fixed to one producer class.

**A `_WIRING` reference is a deliberate, narrow exception to "no `src/` driver module imports
another by name"** (A.7's dependency-graph note): e.g. `asy_notification_service.py` imports
`NeopixelDriver` from `asy_neopixel_driver.py` at module level, for `_WIRING`'s own `signal_sink`
class reference, and every `fram_target`-wirable driver similarly imports `AsyFramManager`. This is
a purely one-directional, no-cycle class-level reference — a consumer driver may import a producer
driver's class, never the reverse — the same direction the topological construction order below
already requires, so it doesn't reintroduce a real coupling cycle at the object-graph level.
`asy_sgp40_driver.py` used to be the canonical example of this (importing `SCD30_Reader` for its
old `comp_source` parameter's type) — §2.9's generalization removed that import entirely, since a
per-value producer is now resolved structurally (by attribute name) rather than nominally (by
class), so `asy_sgp40_driver.py` no longer needs to know its compensation source's concrete type at
all.

**Ordering hazard #1 (object existence)**: since the consumer's constructor call references the
producer's already-built Python object, the producer must be constructed first. The generated
`sensortask_wozi.py` constructs `scd30` before `sgp40` for exactly this reason (A.7's construction order) —
a real, deliberate reordering of wozi's FRAM chunk allocation order, safe only because wozi is never
physically flashed (CLAUDE.md). `buildgen/graph.py` (Session 3) topologically sorts a device's
whole instance list by `_WIRING` dependency (kwarg/attr modes only — a "setter"-mode reference is a
post-construction call, so it never gates construction order) plus two fixed mandatory-infra edges
and one conditional one (`sysfunct` needs its own `device.wiring.fram_target` instance, if set),
and rejects a cycle as a build-time error; `_WIRING`'s shape (an explicit, introspectable 5-tuple)
is what makes that sort possible.

**Ordering hazard #2 (live data availability)**: independent async tasks mean a consumer's first
read can happen before the producer's first real measurement completes. Every producer's
measurement holder already has a safe, defined initial value at construction — every `*_Reader`
constructs its namedtuple with every field `None` before any real read (`SCD30(None, None, None,
None, None, None)` etc., C.4.1) — so `get_data()` is always safe to call immediately, returning a
namedtuple whose individual fields may be `None`. Every direct-reference consumer tolerates that as
a normal, expected input, not an exceptional one, the same way `NotificationCoordinator._check_one()`
already does for its own `None` field (treated as "not triggered," not an error): `SGP40_Reader.
_read_sgp()` reads each field via `getattr(..., None)` and, if either is still `None`, skips this
cycle's compensated read (A.4's already-documented degrade behavior) without logging anything — only
a genuine exception from the producer's own `get_data()` (a violation of its never-raises contract)
still logs (`errno=18`, C.7.1). Fixed this way after `float()` being called on the still-`None` field
raised `TypeError` there instead, misreported as a real compensation-read failure alongside a
spurious "no compensation data" warning on every ordinary startup race (fixed 2026-09-12; a full
audit for the same class of bug - a cross-module producer/consumer read whose exception handling does
not separate "no data yet" from "a real exception" - found no other occurrence in `src/`).

### C.14.3 Error-source and logger fan-in (N-to-1)

Every module callable from a top-level `_collect_error_sources()`/`_collect_level_setters()`
(`sensortask_wozi.py`'s shape — `buildgen` emits the equivalent for any device) implements
`get_error_sources(self) -> list[Any]` and `get_loggers(self) -> list[PrintLogHistory]`,
structurally (duck-typed — matches `asy_webserver_service.py`'s own `_ModuleLike` `Protocol`
precedent, not a forced inheritance relationship). `base_classes.py`'s `SensorReader` provides the
default (`[self]` / `[self.pr]`); `SensorReaderConfig` extends it with its own `self.cfgmgr` (`[self,
self.cfgmgr]` / `[self.pr, self.cfgmgr.pr]`); `AsyConnTime` extends it once more with its
independently-logged `self.dns_server`. A non-`SensorReader` singleton (`AsyFramManager`,
`NeopixelDriver`, `SystemService`, `captive_dns.DNSServer`, `WebserverService`) implements the same
two methods directly, matching the same shape without inheriting from `SensorReader`.

This replaces `_collect_error_sources()`/`_collect_level_setters()`'s old hand-enumerated lists
(every module *and* every module's own nested `.cfgmgr`/`.dns_server`, listed by a human who had to
already know which module owned what) with a plain loop calling `get_error_sources()`/
`get_loggers()` uniformly on each top-level module — the same "every module discovered through a
uniform method, never hand-copied" shape `_collect_task_starters()`/`_collect_timer_starters()`
already used for task/timer starters. `NotificationCoordinator`'s own registered `NotificationSignal`
fan-in (`source`/`field` direct references) is a related but separate mechanism from `_WIRING`
(C.14.2): those are resolved at `register()` call time, already after every producer exists, so
they need no `_WIRING` declaration of their own.

**Generalized per-value measurement wiring (SPECIFICATION.md Part L.6.3,
2026-09-10)**: `NotificationSignal`'s `(source, field)` shape — resolve one named attribute off
another module's `get_data()` result, matched structurally rather than by a fixed producer class —
isn't specific to notification signals. `asy_sgp40_driver.py`'s `SGP40_Reader.__init__` uses the
same shape twice, independently, for its own compensation inputs: `temperature_source`/
`temperature_field` and `humidity_source`/`humidity_field` (replacing the earlier `_WIRING`-declared,
whole-object `comp_source: SCD30_Reader` parameter — see C.14.2's own note). `_read_sgp()` resolves
each the same way `NotificationCoordinator._check_one()` already does:
`getattr(await source.get_data(), field_name, None)`. The two fields may name the same producer
instance (the common case — every real `devices/*.toml` compensates both off one `SCD30_Reader`) or
two different ones, entirely independently. `buildgen/`'s own `_VALUE_WIRING` driver declaration
(parallel to `_WIRING`, parsed by `buildgen/value_wiring.py`) says which constructor kwargs a
per-value TOML field resolves to and whether it's required; a required field with nothing wired can
still build clean via an explicit `{default = true, ...}` opt-in (the wiring-defaults mechanism,
same document §2) — `_DefaultTemperatureSource`/`_DefaultHumiditySource` provide a constant
fallback duck-typed to the same `get_data()` contract.

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
BACKLOG.md. **CLAUDE.md's comment-discipline rule is the authority and this line used to contradict
it** (corrected 2026-09-13): the **3 lines, prefer fewer** cap is on the *module header block*;
inline `#` comments have **no hard numeric cap** but must stay a few short, load-bearing WHY notes
next to the line they explain, never a multi-paragraph block of narrative reasoning. The codebase
follows CLAUDE.md, not the old wording — `sensortask_wozi.py` alone carries fifteen blocks longer
than three lines. Where a file has settled on its own tighter norm, match *it* (D.10):
`asy_uart_comm.py` is uniformly ≤ 3, and the three blocks that drifted past it were trimmed back in
the same pass that found this.

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
per `tests/test_*.py`, and checks its exit code. `pytest` covers the host-only side instead:
`tests_scripts/` runs under real CPython, since none of what it covers is MicroPython-target code —
the build tooling (`scripts/build_firmware.py`, `build_frozen_html.sh`, `build_website.sh`),
`buildgen/` and `toolchain/`, `devices/*.toml`'s own shape, the pure helpers of host-side scripts
like `scripts/_digital_twin_ci_suite.py`, `tests_hardware/`'s pytest-level marker gating, and
cross-file invariants that can only be checked by reading real source text (`scripts/test.sh`'s own
step ordering; the `outer_cap_s` ceiling's mirrors, Part H.4).

`scripts/test.sh` runs both suites. **It launches pytest first but does not wait for it** — the
pytest tier is backgrounded so its single-process runtime overlaps the whole MicroPython loop
instead of serializing in front of it, and both are reaped by one `wait` at the end (it counts
against the same `TEST_PARALLELISM` budget as any test file, and carries its own `timeout` for the
standing "hanging tests are never allowed" rule). One ordering constraint follows from that
concurrency and is load-bearing: every step that globs `devices/*.toml` must run **before** the
background launch, because one `tests_scripts/` test necessarily writes a throwaway
`devices/zz_test_*.toml` into the live tree. See that script's own comments.

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

Any test file that imports a `sensortask_<device>.py` module directly (`tests/_sensortask_scenarios.py`,
`tests/_webserver_concurrency_scenarios.py`, and every `tests/test_digital_twin_*.py` that does the
same) needs one more
prerequisite first, since no such module is ever committed to `src/` any more (SPECIFICATION.md Part L's
Session 6): `uv run scripts/_generate_sensortask_modules.py` to populate the gitignored
`build/generated_src/` directory, and `build/generated_src` prepended to `MICROPYPATH` (ahead of
`src`) so the generated module resolves before anything else. `scripts/test.sh`/`scripts/
typecheck.sh` already do both automatically; running one such file directly, as the invocation above
does for `test_math_helpers.py`, needs them done by hand first or the import fails with
`ImportError: no module named 'sensortask_wozi'`.

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

**The allocator is the one other sanctioned mocking surface**, on the same
no-real-class-equivalent reasoning: the Unix-port test heap (`scripts/test.sh`'s own `-X heapsize`,
a deliberately generous multiple of the 2MB default) cannot be starved at a chosen moment, so
`tests/test_asy_uart_comm.py`'s `_StarvedAlloc` shadows *that module's own* `bytearray` global —
the reassign-a-module-name mechanism the rest of `tests/` already uses, pointed at an allocation
instead of a method. Two rules make it safe, both learned by getting them wrong first: it must be
**armed and one-shot**, because every degraded path allocates something itself and a
blanket-raising stub fires again inside the very handler under test; and it must restore the global
in `__exit__` so a failing assertion cannot leave the module shadowed for the next test in the same
process. Reach for it only where a real `MemoryError` is genuinely unreachable — never to avoid
writing the reachable case.

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
currently no-ops silently. Runs in its own `unit-tests-coverage` CI job (Session 8's
closing-consistency-pass PR split it out of `unit-tests` proper) — this pass re-runs the whole
real-interpreter suite a second time under `sys.settrace`, so keeping it off `unit-tests`' own
critical path means `digital-twin-e2e`/`firmware-build-verify` (which only need `unit-tests`' own
toolchain-cache population, never this job's report) no longer wait on it.

### E.5.1 Reading the numbers: three systematic false-negative patterns, not missed test cases

`micropython.const(...)` assignments whose name starts with `_` are compiled away entirely, so the
line never fires a trace event and always shows a 0-hit miss despite being fully "exercised."
**The rule is the leading underscore, verified at source** (`py/parse.c`, the `MICROPY_COMP_CONST`
fold): a private `const()` has its whole assignment replaced by `pass` in the parse tree, while a
public one keeps the store and therefore does register — which is why `ROLE_INITIATOR` and `CMD_GET`
show as covered in `asy_uart_comm.py` while all 58 of its `_`-prefixed constants do not. A decorated function's traced
event lands on the decorator line, not the `def` line, so every `@staticmethod`/`@classmethod`
shows missed even when called throughout the suite. A bare `while True:` header never fires its own
trace event at any iteration (folds into an unconditional jump at compile time).

Separately (not a tracer artifact, also not a missed-test hint): several `except` branches guard
against outcomes provably unreachable given guarantees the same function already establishes
before them (`crc_checks.py`'s masked-CRC guard, `math_helpers.py`'s domain-guarded blocks) — left
as documented dead code rather than chased for a coverage number. `print_log.py`'s `get_log()` has
the same shape from an `if`: it treats two sentinels as equivalent "nothing recorded" markers, but
only one is actually reachable — **confirmed intentional by the project owner**, kept for
defensive symmetry. `asy_uart_comm.py` carries six statements of a third variant: a buffer or a
bound re-checked immediately after the check that already settled it, so the second check cannot
fire through any call path that exists. Measured one by one: `_write_frame_with_ack()`'s second
`self._tx.get_buf()` (`_prepare_tx()` has already returned `False` if it were `None`);
`_listen_unlocked()`'s `rx is None` (`_read_frame()` returns `False` in exactly that case);
`_recv_train()`'s destination bound (`_get_unlocked()` refuses a short destination at the header, and
`_accept_set()` allocates exactly `room`); and `uart_get()`'s `own is None` (it passes neither a
destination nor a push callback, so `_run_get()` always allocates one). `asy_uart_driver.py` adds
four more of a different kind — the `except MemoryError` around `msg += add` in
`read_until_complete()`/`readline_until_complete()`, which guard an accumulator growing across rounds
with no deterministic injection point under the Unix-port test heap. Kept, like the rest — one branch of
defence in depth in a module contracted never to raise is cheaper than the day the surrounding logic
moves.

A `finally:` body is **not** one of these patterns, despite looking like one: its lines fire a trace
event only when an exception actually passes through, so a `finally` that only ever runs on the
normal return path reads as uncovered. That is a real missing test — of cancellation — not an
artefact; `test_a_cancelled_transaction_still_releases_the_re_entrancy_flag` is what it was hiding.

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
complementary. **This complementary relationship is about which *aspect* of a behavior each backend
proves (E.6.1's own table) — it does not exempt real-hardware-facing behavior from needing a
real-hardware check at all; see E.6.6.**

### E.6.6 Real-hardware parity requirement

**Standing rule (project owner's direction): every mock/digital-twin test that exercises
real-hardware-facing behavior needs a real-hardware equivalent, wherever technically possible** —
a real bus transaction shape, real timing, a real fault-injection scenario, a real REST endpoint
that reaches real hardware state, and so on. This generalizes what SPECIFICATION.md Part C.8's own
bus-hazard promotion checklist already requires for that one domain (mock → twin → flash → bench,
with flash ⊆ bench per E.6.1) to the whole test suite — C.8 is an instance of this rule, not a
special case of it. A gap here is a real gap to close, the same way a missing bus-hazard tier is,
not a documentation nicety.

This does **not** override three already-established, deliberate exceptions — the rule is scoped by
them, not in tension with them:

1. **Only `dev` is ever physically bench-tested** (CLAUDE.md's own hard rule). `wozi`/`arzi`/
   `klkizi`/`grkizi`/`schlafzi` have no real board to flash at all, so real-hardware parity for
   anything specific to one of them is structurally impossible, not a gap to chase — their own
   correctness is established entirely through mock/twin, by design (CLAUDE.md's "WoZi is the
   exemplary/base variant" entry). Only `dev`'s own real wiring/behavior can ever be checked for a
   missing real-hardware counterpart under this rule.
2. **A behavior with no real API/hardware surface to reach it at all** cannot get a real-hardware
   test for that specific path — e.g. SCD30 has zero REST-pushable fields (`asy_scd30_driver.py`
   registers no `_push_callbacks`), so no bench-tier `PUT` can ever reach its own NVM write (C.8's
   own SCD30/bench note). Document the structural absence explicitly, the way C.8 now does, rather
   than leaving it as a silent, unexplained gap — a documented structural exception is compliant
   with this rule; a silently missing test is not.
3. **A behavior only a human can verify** (a visual/instrument check, genuine power loss, a
   calibrated-reference accuracy claim) gets `tests_hardware/manual/` coverage instead of an
   automated one — `manual` is a different *execution mode* of the same real-hardware tier (E.6's
   own "`manual` is an execution mode, not a tier"), not a waiver from this rule.

**Out of scope entirely**: a test with no hardware-facing behavior to verify in the first place
(`math_helpers` formulas, config-schema validation, pure JSON/string handling, buildgen's own
CPython-only logic, ...) — a "real hardware equivalent" of testing arithmetic is meaningless. This
rule is about tests whose value comes from proving something a fake bus/network/filesystem can only
approximate, not every test in the suite indiscriminately.

---

## E.7 A digital-twin soak's wall clock measures GC timing, not the code under test

Measured against the soak as it ran in-process at the time (`digital_twin/run_dev_integration.py`,
since retired and replaced by `digital_twin/run_generic_integration.py` plus the host-side Run 11
in `scripts/_digital_twin_ci_suite.py` - E.9): a bounded soak driving ~294 real HTTP requests
through the whole constructed object graph. Its duration is **deterministic per build and
meaningless across builds**: it is set by where `gc` collections land on the Unix port's 8 MB heap,
and that moves with heap layout, which moves with almost any source change. The mechanism below is
unchanged by where the soak's request-driving loop runs (in-process or host-side, E.9) - it is a
property of the Unix port's allocator, not of which process issues the requests.

Measured on the dev variant (2026-09-11), same probe, same host, interleaved, three rounds each,
against three versions of `src/asy_uart_driver.py`:

| `asy_uart_driver.py` | Soak wall clock | `_buffered()` calls during the run |
|---|---|---|
| before the F.5.8 clamp | 44.07 / 44.07 / 44.07 s | — |
| with the clamp | 58.43 / 58.33 / 58.56 s | **0** |
| with the clamp and F.5.9's idle rate | 61.49 / 61.79 / 61.24 s | **0** |

The changed code is never executed during that run: the link is idle, so `ready()` never returns
`True` and no read path is entered at all — confirmed by instrumenting the module itself, not
inferred. Adding three counter increments to an *unchanged* version reproduces the slow figure on
its own. And calling `gc.threshold(-1)` for the duration of the soak **inverts the ordering**
(44.07 s → 57.7 s, 61.5 s → 44.5 s), which is what identifies the mechanism.

Two consequences, both load-bearing:

- **Never bisect a twin soak's runtime to a code change.** It will produce a confident, stable,
  wrong answer — it did once (2026-09-11), attributing a regression to a function with zero call
  sites reached. Count the operation you actually care about instead: F.5.9's finding was
  established by counting poll rounds (14 039 → 839), which is a property of the code rather than
  of the allocator.
- **A soak's own timing budget is a liveness backstop, not a performance assertion**, so it belongs
  above the whole observed range rather than near it — the in-process soak this was measured
  against gave itself 120 s for a 44-62 s run (`tests/test_digital_twin_run_dev_integration.py`,
  since retired). Run 11's own host-side equivalent (`scripts/_digital_twin_ci_suite.py`) has no
  single such budget to mistune in the first place: each `_http()` round trip has its own 5 s
  timeout and `_shutdown()` gives the subprocess 15 s to exit, neither tied to the soak's own
  GC-dependent wall clock at all — this is what E.9's host-side move buys for free, not just where
  the request-driving code lives.

## E.8 Measurement traps, and the guard-is-blind trap behind them

Every item here produced a confident, stable, wrong number before it produced a right one, so each
is a rule rather than an anecdote. E.7 is the largest of them and keeps its own section.

- **An absolute heap-delta bound is host-dependent; a leak is a rate.** Retention scales with the
  work done, while an interpreter's internal caching is a fixed sprinkle that varies by host *and
  by run*. Two hammer tests bounded `gc.mem_alloc()` growth at a few frames because both measured
  exactly 0 on the bench, and failed CI at 64 B. Assert a per-operation rate instead —
  `tests/test_uart_comm_hazard.py` uses `< 6.0 B/transaction` and `< 16.0 B/failure`, against a real
  retained frame's 13+ B/transaction and an injected 16 B/transaction leak's measured 636.
  **Two follow-on traps, both paid for:** the rate must be divided by the span actually measured,
  not by the loop's total round count — the clean hammer sampled a third of the way in and still
  divided by all 150, understating itself by half again. And one runner observation does not
  calibrate a floor: the same commit measured 64 B on one GitHub runner and 288 B on another, so a
  bound set just above the first reading went red on the second. Set it from the signal you must
  still catch, not from the noise you happened to see.
- **The twin's `UARTLink.wire_log` is unbounded** — one byte per delivered byte, ~15-95 kB over a
  few hundred transactions. It reads as a leak in the code under test. Clear it inside any
  measurement loop with direct object access to the link (every `tests/`-tier test that touches it
  already does). **`digital_twin/run_generic_integration.py` itself has no such access** — it boots
  the twin as a real subprocess — so it did not, and this was exactly the mechanism behind a real
  CI finding: `dev`'s Run 11 soak check (`scripts/_digital_twin_ci_suite.py`) reproducibly failed
  its `gc.mem_free()` trend check (only `dev` wires a `uart_link` pair; `wozi` has no UART bus and
  stayed flat), confirmed by isolating the run from CPU contention (magnitude dropped but the
  failure persisted) and root-caused to this exact bullet. Fixed by giving
  `run_generic_integration.py` its own periodic clearer (`_wire_log_clearer()`, every 5s, started
  whenever `_wire_uart_crossover()` actually wires a link) — this process never reads `wire_log`
  back, so clearing it here changes nothing about the link's real over-the-wire behavior.
- **An asyncio loop-latency probe cannot separate "idle on a timer" from "blocked."** The driver's
  own cooperative `sleep_ms(poll_wait_ms)` puts both at ~2 ms. Time the C calls directly (F.5.8).
- **A probe read before the watchdog task next runs reports 0 for everything.** Give it a turn —
  `await asyncio.sleep_ms(0)` a few times — before reading its peak.
- **`I2C.scan()` is synchronous** and blocks the loop for a 128-address sweep, so using it as "bus
  load" models nothing production does: it inflated a measured worst-case RTT from 112 ms to 574 ms.
- **Cross-test contamination is real.** One process, one task queue, and no parent/child tracking in
  MicroPython asyncio, so listeners parked by earlier tests keep allocating. Isolate before
  believing a per-test number.
- **`ErrNum` mixes errnos and wrnnos in one ring sharing a number space** (wrnno 10 = resync,
  errno 10 = bad `payload_size`), and every fault also resyncs, so the newest entry is almost always
  the resync warning. Filter on `ErrType == "E"`.

**The trap under the traps: a guard whose oracle cannot see the regression it guards.** Verified by
regressing each of `asy_uart_driver.py`'s seven read paths in turn and re-running the mock tier
(2026-09-12): four failed a named test, three passed silently. `test_readline_does_not_probe_an_empty_buffer`
asserted on the fake's own call log, but the fake returns early on an empty ring *before* it logs,
so deleting the gate left the log empty too and the test still passed. A guard is only established
by removing what it guards and watching it fail — the same standard I3.4's revert-and-confirm pass
applies to fixes, applied to test oracles.

**Run it as a scripted sweep, not by hand.** One list of `(source file, exact anchor, replacement,
expected failing tests)`; for each entry, write the mutation, run only the affected test file,
require the named test to be in the failures, restore the file in a `finally` regardless. Cheap
enough to run over twenty-odd guards in one pass, and it answers a question reading cannot: 27
mutations across 2026-09-12/13 found two tests that asserted *that* a refusal happened but not
*where*, so both survived a mutation that moved the refusal to the wrong end of the exchange — and
one **fix** that was itself dead code, an `isinstance(written, bool)` arm added on CPython reasoning
that nothing could fail once removed, because `bool` is not an `int` subclass here at all (F.1). A
mutation that fails nothing is as much a finding as a test that fails nothing.

**Standing rule, from the same sweep: every hazard check runs in both CRC modes.**
`tests/test_uart_comm_hazard.py` registers each `_check_*` twice (`_nocrc`, `_crc16`) — 48 checks,
96 tests. Two are single-mode by construction (`_MODE_SPECIFIC`), because their subject *is* one
configuration. The deployed link runs `CRC_Pass`, so the no-CRC path is the one in the field.

## E.9 Driver/DUT process separation

**Anything that can run outside the digital twin's own MicroPython process without losing coverage
must run outside it.** The twin (the DUT) is a real MicroPython Unix-port subprocess with its own
heap; a real host-side test driver is a real CPython process with its own, unbounded one. Code that
drives requests, observes responses, accumulates diagnostic history, or computes a pass/fail
verdict belongs in the driver, not smuggled into the DUT just because it's convenient to write there
— every byte it allocates competes with the exact allocation behavior the test exists to observe,
turning a test of the code under test into an accidental test of the test's own bookkeeping instead.

The one thing that never moves host-side: a value that only exists inside the DUT's own process and
has no other way out — `gc.mem_free()` is the standing example, real nowhere but inside the twin's
own heap. Get it out through the narrowest possible channel (a log line on a fixed timer, correlated
back by timestamp — `_mem_sampler()`) and do nothing else with it in-process; compute, threshold,
and report the verdict host-side.

Two real findings this rule caught, both worth re-reading in full:
- **The Run 11 memory-trend soak itself** used to drive its own request loop from inside the twin's
  process via an in-process client, sharing the twin's own heap with the code under test. Moved
  entirely host-side (2026-09-14): `scripts/_digital_twin_ci_suite.py`'s `_run_11_soak()` now drives
  every warmup/cycle request over real HTTP from the CPython suite process itself, and
  `digital_twin/run_generic_integration.py` (the retired per-device runners' replacement) keeps only
  `_mem_sampler()` — the one `gc.mem_free()` emitter above — plus the `gc.collect()` that settles it
  before each sample (I.4(e)'s own narrow, separately-litigated exception).
- **`digital_twin/machine.py`'s `UARTLink.wire_log`** — E.8's own bullet — is unbounded by design,
  fine for a unit test with direct object access to clear it, a real bug for any driver that boots
  the twin as an opaque subprocess and has no such access. The fix wasn't to bound `wire_log` (that
  would defeat its own purpose for the tests that need it) but to give the in-process side a
  periodic clearer of its own (`_wire_log_clearer()`) — the DUT-side code stays exactly as
  DUT-appropriate as before, the driver-shaped growth just stops happening where the driver can't
  reach it.

A fix under this rule must come out **strictly more capable of catching the real test case**, never
merely lighter on the DUT — E.7/E.8 already show what a test that stops looking at the right thing
costs. Moving request-driving host-side, in particular, converts a soak's wall clock from a
GC-timing artifact (E.7) into something no longer even measured — the check now bounds real
HTTP-failure counts and a `gc.mem_free()` trend directly, not a duration that never bounded anything
real to begin with.

Real GitHub-runner CI kept tripping the `gc.mem_free()` trend check occasionally even after that
move (2026-09-14) — a different device each time. A same-tree local investigation both reproduced it
directly (two independent `wozi` boots in a row, 3298/2854 and 4361/2847 bytes, past the
then-current tolerance) and measured the actual mechanism: the tolerance was `8192 * sqrt(25 /
quarter_size)`, assuming a trend's standard error shrinks with independent-sample statistics as
`quarter_size` grows. It doesn't — consecutive 25ms `gc.mem_free()` samples are heavily
autocorrelated (the same reactive-GC-paced heap barely moves between two adjacent readings), so the
formula was tightening fastest exactly where real per-run noise needed it loosest. `_mem_trend()`
(`scripts/_digital_twin_ci_suite.py`) now derives the tolerance from each attempt's own observed
noise — each quarter's own internal spread, never the early-vs-late difference itself, so a genuine
leak's own decline can't inflate the very tolerance meant to catch it — instead of a historical
constant extrapolated through a scaling law real sampling never matched. `_run_11_soak()` also
retries once — a second fully independent clean boot — before failing on the trend check
specifically, the same standard E.8's "a guard is only established by removing what it guards and
watching it fail" already sets: a real leak reproduces past tolerance on both independent boots,
transient noise essentially never does. Never retries an HTTP/watchdog/shutdown failure — those
aren't this measurement's own known noise source, and finding one still ends the run immediately,
same as before.

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

**Dynamic imports (`__import__`, `importlib`) must never be used anywhere in this codebase** —
project owner's explicit, standing rule, not just a style preference. Every import stays a real,
static `import`/`from ... import` statement, AST-scannable without executing any code — this is
what lets a future build-time tool (e.g. a per-device frozen-module selector deriving its module
set from the transitive closure of real imports) work by pure static analysis. `importlib` isn't
frozen into this project's own manifest today regardless, but the rule holds independent of that.

**A soft `machine.Timer` callback (the default — no `hard=True` anywhere) can be silently dropped,
not just delayed** — `mp_sched_schedule()` drops it if MicroPython's fixed-depth scheduler queue
(depth 8 on rp2, shared by every soft timer/IRQ) is full, with no exception and no way to detect a
dropped vs. not-yet-run callback. A periodic timer self-heals next tick; a one-shot does not fire
again. A software-timeout mitigation for this was considered and rejected (it would just race the
real hardware watchdog every deployment already arms) — don't re-propose without a materially
different justification.

**Iterable unpacking inside a list/tuple/set *display* (`[*a, b]`) raises `SyntaxError: *x must
be assignment target` at parse/compile time on this project's pinned MicroPython** — confirmed
directly against the real Unix-port interpreter (both a plain function call and a `super()` call as
the starred expression fail identically, so this isn't super()-specific). Use list concatenation
instead (`a + [b]`) — the established pattern project-wide (`base_classes.py`'s/`asy_wifi_service.
py`'s `get_error_sources()`/`get_loggers()`, Part C.14.3). Iterable unpacking in a *function call*'s
argument list (`f(*a, b)`) is unaffected — this gap is specifically about list/tuple/set displays.

**`[x] * n` (list repeat) can segfault the interpreter for n in roughly 2⁶¹-2⁶³** (below that it
raises `MemoryError` like `bytearray(n)`; at/above 2⁶³, `OverflowError` — the gap is likely an
internal size-multiplication overflow before bounds-checking). Any code sizing an allocation from
external/caller input must clamp the size *before* allocating, not just catch `MemoryError`
reactively (`LockableBuffer`/`PrintLogHistory` are the established pattern).

**`bool` is NOT a subclass of `int` on MicroPython, unlike CPython** — `mp_type_bool`
(`py/objbool.c`) is defined with no `parent` slot at all, so `isinstance(True, int)` and
`type(True) is int` are both **`False`**, while `True == 1`, `True + 1 == 2` and
`bytearray[i] = True` all still work through `bool_binary_op()`'s small-int coercion. Verified
directly against the pinned v1.29.0 build and its source, not assumed. Consequence:
`isinstance(x, int)` is *already* strict here — a parameter validator written for CPython would
need an extra `isinstance(x, bool)` arm that on this runtime is unreachable dead code (one was
written and removed again during the 2026-09-13 review). `config_manager.py`'s
`type(x) is not int` stays correct either way and is the form to copy; don't add the CPython-only
guard on top of it.

**`machine.Timer.init()` can raise `OSError(ENOMEM)`** if the RP2040's alarm pool is exhausted —
every call site must handle it. **`MemoryError` is not an `OSError` subclass** — both are direct
sibling `Exception` subclasses; catch `(OSError, MemoryError)` wherever both are plausible. A plain
`except Exception:` *does* catch `MemoryError`.

**RP2040's real firmware uses single-precision `float`** (24-bit mantissa, exact to `2**24`);
**this project's Unix-port test rig uses double precision** (exact to `2**53`) — `float(int)`
beyond either threshold silently rounds. `coerce_numeric()`'s int→float direction relies on this
(A.8) — accepted, since no real schema field's bounds go near it.

**`struct` format codes with no byte-order prefix use the host's own native sizes**, so `'L'` is
4 bytes on rp2 and 8 on the 64-bit Unix-port test interpreter — the same line reads a different
number of bytes in the two places. Pin any wire or on-chip layout with an explicit `"<"` prefix;
`dev_legacy/asy_bsec_driver.py`'s bare `struct.unpack("bbbbL", res)` against a hardcoded size of 8 is
the shape to avoid, and anything porting it forward has to fix that first.

**`struct.pack()`/`pack_into()` silently zero-pad or truncate on a mismatch instead of raising**,
unlike CPython — validate shape before packing if it matters. Still true on 1.29: the overflow
checks added to `py/binary.c` are gated behind `MICROPY_PREVIEW_VERSION_2`, so they only turn on in
a V2.0 preview build. Expect this fact to flip when upstream ships 2.0.

**Slice assignment has two different length contracts, and neither raises where you expect.** A
`bytearray` destination *resizes* on a length mismatch exactly as CPython's does — `b[0:2] = <3
bytes>` grows the object and shifts everything after it, silently — while a `memoryview`
destination raises `ValueError: lhs and rhs should be compatible`. Both measured on the pinned
Unix-port interpreter. Code copying a computed span into a buffer must therefore bound-check the
span itself (`asy_uart_comm.py`'s `written + size > len(dest)` guard); the destination's own type
will not do it. **There is also no `memoryview.readonly` attribute on MicroPython** — the way to
tell a writable destination from `memoryview(b"...")` without allocating or mutating anything is a
zero-length slice assignment (`buf[0:0] = b""`), which raises `TypeError` on a read-only view and
succeeds on every writable one.

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

**This backstop is safe in practice, with one narrow, accepted residual window (WP5,
2026-09-16).** Every real flash write is still *triggered* only through the REST PUT path — nothing
else ever calls `ConfigManager.write_config()`. But `write_config()` itself no longer performs that
write inline: it validates and stages synchronously, then hands the actual `open()`/`json.dump()`
call to an independent `asyncio.create_task()`, decoupled from the request/response entirely (see
this Part's own note below and BACKLOG.md, 2026-09-15 — the RP2040 flash write disables interrupts
port-wide for its duration, and doing it inline was resetting the very HTTP connection whose PUT
triggered it — see `config_manager.py`'s own `write_config()`/`_flush_staged()` comments for the
full mechanism). So the older, stronger claim — "a device whose API is unreachable structurally
cannot have a flash write in flight" — is no longer exactly true: there is now a brief window,
between the response being sent and the deferred flush actually running, where the API could in
principle already read as unreachable while a write is still pending. In practice this window is a
single scheduler tick (microseconds to low milliseconds), while the WiFi backstop only ever power-
cycles after a *sustained* outage (F.2's own measured data: essentially never inside 150s) — so the
two are separated by many orders of magnitude, and a power cycle triggered by that backstop lands
long after any pending flush has already resolved one way or the other. The real, intentionally-
accepted residual risk is narrower and different in kind: a power loss landing in that same brief
window loses the just-accepted config change silently (never corrupts anything - `_flush_staged()`
only ever replaces `_cache`/the on-disk file after its own write actually succeeds, exactly as
`write_config()` always did). Combined with the reboot-safe boot chain (A.4), power-cycle recovery
is still a deliberately stable, intended feature - this residual window narrows what "inherently
safe" means, it doesn't remove the design's own safety property.

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

**The pin is field-proven on the dev bench (2026-09-11).** Real `dev` firmware built from `src/` and
flashed; `sys.implementation` on target reports `(1, 29, 0)` / `_mpy=4870` / `RPI_PICO_W`, with the
flash tier (25 passed), bench tier (85 passed) and mid soak tier (4 passed) all clean against it.
Deployed units stay on 1.26 regardless (BACKLOG open question 3). Of the three findings that wanted
on-target confirmation beyond just running the suites, F.5.1's and F.5.3's are closed on real
silicon and F.5.2's is closed as far as the target allows — inducing a genuine RX overrun is not
reachable from Python, so its *consequence* is pinned instead (`device_scripts/
fram_busy_status_lockout.py`).

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
That makes the retry question (BACKLOG.md open question 15) much less pressing than it looked.

The same run also leaves the chunk marked busy and unreadable until rewritten, which is **intended
behavior, not a defect** — an interrupted read means an interrupted internal restore on a
destructive-readout part, so the data cannot be trusted even when it reads back intact. Part A.4's
FRAM entry has the full account.

### F.5.3 Free wins already compiled into the 1.29 build

- **The interpreter core now genuinely runs from SRAM.** 1.28's rp2 linker rule for SRAM code
  placement never matched its object suffixes, so the intended placement silently never happened.
  Fixed upstream; verified in this project's own `firmware.elf.map`, where `py/vm.c.o`,
  `py/parse.c.o` and `py/gc.c.o` sit at `0x2000xxxx` inside an `EXCLUDE_FILE(...)` clause. Cost,
  measured off that map: **12,918 B** of RAM no longer available as Python GC heap (vm 5,040,
  parse 3,298, gc 2,676, the linker's own 1,504, plus ~400 of libc/libm/libgcc helpers the same
  rule excludes) — relevant to every Part I budget. **Note this is purely a cost entry here:** the
  *benefit* (SRAM beats XIP flash for the hot interpreter loop) is upstream's rationale, has never
  been timed on this bench, and must not be quoted as a measured speedup.
  **What it actually leaves, measured on the real dev board at 1.29.0 (2026-09-11)** — the check
  that matters, since the cost lands entirely in static RAM rather than in any runtime behavior.
  The build reports `RAM: 66,792 B / 256 KB (25.48%)` static; a real `build_system()` on hardware
  then leaves **130,224 B free with a 115,536 B largest obtainable single block** (148,448/146,112
  before the build), at MicroPython's own reactive-only `gc.threshold(-1)` default — a proactive
  threshold changes neither figure. Against a largest known single allocation of ~5.7 KB (`GET
  /status`, itself streamed in 1 KB fragments since Part I.3), that is ample. Kept honest by
  `tests_hardware/flash/test_memory_stress.py`'s
  `test_real_gc_heap_headroom_survives_a_full_system_build`, which asserts floors of 100,000 B
  free and 80,000 B contiguous so a future bump relocating more code into SRAM shows up as a test
  failure rather than as slow attrition. The comparable 1.28 figure is the 2026-09-08 hammer-load
  `mem_free` floor of 91,312 B (Part I.5), which is a *loaded* floor, not an at-rest one — the two
  are not directly comparable, and measuring a loaded floor at 1.29 would need `mem_free` exposed
  over REST, which is deliberately not done.
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
supervisor tick would survive it at zero flash and zero FRAM wear. **Deliberately not adopted**
(project owner, 2026-09-11): there is no standing reason to carry it, and a breadcrumb written
every tick is cost with no current customer. It stays documented here as a tool to reach for *if* a
severe, hard-to-debug reset appears that the FRAM logs cannot explain — deliberate, temporary
instrumentation, never normal-path code.

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

### F.5.7 `machine.UART.deinit()` leaves the RX ring buffer unrooted — re-init by construction

Read out of `ports/rp2/machine_uart.c` at `v1.29.0` while auditing the UART promotion, not from a
changelog. It changes nothing about how this project behaves today, but it is the reason one line
of `asy_uart_driver.py` has to stay the way it is.

`mp_machine_uart_deinit()` clears `MP_STATE_PORT(rp2_uart_rx_buffer[id])` and its TX twin — the
`MP_REGISTER_ROOT_POINTER` entries that make those ring buffers reachable to the GC — but leaves
`self->read_buffer.buf` in the static `machine_uart_obj[]` entry still pointing at them. A static C
struct is not scanned, so after `deinit()` the buffers are garbage that the object still holds a
pointer to. Calling `uart.init(...)` again does **not** repair it: the reallocation is guarded by
`if (self->read_buffer.buf == NULL)`, which is false, and the root pointer is never restored — so
the UART IRQ handler resumes writing into memory the collector is free to hand out. The one
exception is an `init()` that asks for a **different** `rxbuf`/`txbuf` size: that branch sets
`buf = NULL` itself before the guard runs, so the buffer is reallocated and re-rooted. Re-initing
with the same parameters — the ordinary case, and the one a recovery path takes — does not.

The escape is that `mp_machine_uart_make_new()` sets `read_buffer.buf = NULL` itself, so
**constructing a fresh `machine.UART(id, ...)` always reallocates and re-roots**, while
`uart.init()` on a previously deinit'd object does not. `asy_uart_driver.UART.init()` therefore
calls `machine.UART(...)` rather than `self._uart.init(...)`, and that choice is load-bearing
rather than stylistic — `tests_hardware/device_scripts/uart_crossover_recovery.py`'s injector
deinits and re-inits a live port, which is exactly the sequence that would otherwise corrupt the
heap on real hardware.

### F.5.8 `machine.UART.read()/readinto()` block the asyncio loop for bytes not yet arrived

Read out of `ports/rp2/machine_uart.c` at `v1.29.0` and then **measured on the dev bench's own
crossover jumper**, because the consequence is a real-time property no code review makes obvious.

`mp_machine_uart_read()` loops once per requested byte. When the RX ring is empty it waits — and
that wait is `mp_event_handle_nowait()`, which runs scheduled callbacks but **never yields to
asyncio**. The per-byte budget is `self->timeout` for the first byte and `self->timeout_char`
(this project's drivers pass `1`) for every one after it. A byte at 115200 baud arrives every
~87 us, comfortably inside that 1 ms, so the loop never times out mid-frame: it simply spins,
synchronously, until the whole requested count has arrived. `select.poll()` does not protect
against this — `mp_machine_uart_ioctl()` reports `POLLIN` as soon as the FIFO holds *one* byte.

Measured across the jumper, asking for a whole 53-byte frame the moment `POLLIN` first fires:

| Trial | Bytes buffered at `POLLIN` | `readinto(buf, 53)` returned | CPU held, synchronously |
|---|---|---|---|
| 0 | 3 | 53 | 4195 us |
| 1-4 | 2 | 53 | 4370-4405 us |

Against a wire time of ~4600 us for that frame — i.e. the read holds the loop for essentially the
entire remaining transmission. **Nothing else in the event loop runs for that whole span**, which
is exactly what the UART driver and protocol module are required never to do (owner direction,
2026-09-11: they may time out and handle it, but may never block synchronously, not even in a wait
state).

**The fix has two halves, and the first alone is worse than useless.**

1. *Ask only for what is already buffered.* `mp_machine_uart_any()` drains the RX FIFO into the ring
   and returns its fill level, and the documented contract is exactly the property needed — "the
   number of characters that can be read without blocking" — so a read clamped to it never enters
   the per-byte wait loop. `asy_uart_driver.UART._buffered()` is that clamp, and **every** read in
   the module goes through it: the four counted paths (`read()`, `readinto()`,
   `read_until_complete()`, `readinto_until_complete()`), the two uncounted ones (`read(None)` and
   `readinto(buf)` asked the peripheral for the whole buffer, which blocks for every byte of it that
   has not arrived), and `_read_delimited()`'s one-byte read, which was still issued against an
   empty ring where the C read spins out its `EAGAIN` probe. `readline()` has no count to clamp and
   gates on `any()` instead. The docs' lower-bound wording ("may return 1 even if there is more than
   one character available") costs nothing here: under-reporting only ever means another round.
2. *Yield on the way out of `ready()`.* With the clamp alone the stall did not improve — it got
   **worse**, measured at 14.6ms. `ready()` returned `True` with **no `await` at all** whenever
   `ipoll()` already reported the mask, so a frame still mid-flight was simply read in a Python loop
   with no yield point: the same block, reimplemented one level up and slower than the C busy-wait
   it replaced. Every read loop in the module reaches the peripheral through `ready()`, so the yield
   belongs there and nowhere else — `await asyncio.sleep_ms(0)` immediately before it returns
   `True`. That makes it one guarantee in one place instead of an obligation each call site has to
   remember: **no path through this driver reaches a read without having just yielded.**
   `_read_delimited()` is the one loop that consumes buffered bytes without going back through
   `ready()`, so it yields every `_DELIMITED_YIELD_BYTES` (16) — a task switch every ~1.4ms of wire
   time rather than every ~87us.

A zero-length round additionally falls back to `sleep_ms(poll_wait_ms)`, so the retry can never
become an unyielding spin on `ready()` even if `any()` ever disagreed with `POLLIN`.

**Measured result, both halves in place.** The honest measurement is the *longest single
non-yielding call*, not a loop-latency probe: an `asyncio` probe task cannot distinguish "the loop
is idle waiting on a timer" from "the loop is blocked", and the driver's own cooperative
`sleep_ms(poll_wait_ms)` waits put both at the same ~2ms. Timing the C calls directly does
distinguish them:

| Call, in-flight 53-byte frame | Worst single synchronous span |
|---|---|
| `uart.readinto(buf, 53)` — before, asking for the whole frame | 4195-4405 us |
| `uart.readinto(buf, any())` — after, clamped | **278 us** |
| `uart.any()` | 72 us |
| `uart.write(53B)` | 171 us |

Re-measured on the dev bench (2026-09-12) after the yield moved from the four read loops into
`ready()` itself: unclamped 4422 us, clamped **137 us**, write 169 us — the same result from an
independent run against the reshaped driver, which is what makes the table a property of the
peripheral rather than of one arrangement of the code.

For scale, this board's own scheduler noise floor — the worst gap a `sleep_ms(0)` probe sees with
no UART activity at all — is 400-900us, so the clamped read is already below the point at which
the measurement means anything. An A/B on one firmware (defeating `_buffered()` at runtime to ask
for the whole frame again) moves the end-to-end worst loop gap from 3.1ms to 6.3ms, confirming the
same thing from the other direction.

**Why no test caught it, and what now does.** `tests/machine.py`'s and `digital_twin/machine.py`'s
UART fakes return `min(nbytes, len(rx_queue))` and never wait — they model a non-blocking read the
real peripheral does not provide, so the defect was invisible to every tier below the bench. This is
precisely the class of defect the flash tier exists to find: real electrical and timing behaviour
that no fake reproduces.
Making the fakes actually *wait* would only turn a real-time defect into a slow test; both instead
**count the stall they would have taken**. `UART.would_have_blocked_bytes` accumulates every byte a
read asked for that had not arrived, the two models are held to identical counting by
`tests/_uart_link_contract.py`, and a whole-frame read through the driver asserts it stays at zero.
A regression of the clamp now fails in the mock tier as a number, in the same shape as the twin's
own `WDT.would_have_triggered_count`.

**All seven read paths are guarded, and that was established by breaking each one.** The counted
paths (`read`/`readinto`, counted and uncounted, and both `*_until_complete` loops) clamp to
`any()`; the three that carry no count to clamp — `readline()`, `readline_until_complete()` and
`_read_delimited()`'s one-byte read — gate on one buffered byte instead. Removing each clamp in
turn and re-running the mock tier (2026-09-12) initially failed a named test for only four of the
seven: the two `readline` paths were uncounted by both fakes, and `_read_delimited`'s gate was
counted but asserted nowhere. Both gaps are closed, and the sweep now fails on all seven. Part E.8
records the test-oracle trap this exposed.

**This does not generalise to `asy_i2c_driver.py`/`asy_spi_driver.py`, and must not be applied
there.** A UART read is fixable only because the peripheral offers a genuinely non-blocking path —
`POLLIN` plus `any()` report what has already arrived, so the driver can take exactly that and come
back. `machine.I2C`/`machine.SPI` expose no equivalent: a transfer is one synchronous transaction
with no partial-read API to clamp to, so an SCD30's 18-byte read *is* a ~1.8ms synchronous span by
construction. That is the case Part F.2 already settles — the hardware watchdog is the accepted
backstop, and no I2C-level timeout mechanism is to be proposed for it.

The write side is the same shape but bounded, and needed no change: `mp_machine_uart_write()`
short-writes rather than waiting once `timeout` (0 here) elapses, and `_write_all()` gates on
`POLLOUT` and retries. Its theoretical worst case is the ~1 ms it takes `ticks_ms()` to advance,
never a frame time — and measured at 171 us for a whole 53-byte frame, since a `txbuf` with room
takes the lot in one copy and the wire drains by interrupt.

### F.5.9 An idle `ready()` poll is a permanent CPU cost, not a free wait

Same layer as F.5.8 and the same owner rule behind it, but the opposite failure: not a wait that
blocks, a wait that never stops working. `asy_uart_driver.UART.ready()` waits by polling —
`ipoll(0)`, then `sleep_ms(poll_wait_ms)`, round after round. For a transaction in flight that is
correct and deliberate: Part J.6 requires a single-digit `poll_wait_ms` precisely because poll
granularity, not baud rate, dominates a stop-and-wait exchange's throughput. For a *listener* it is
not. A responder parked in `uart_listen()` is waiting on a frame that may not come for hours, and at
2 ms it pays a scheduler round trip every 2 ms for the whole of that time — on the same core as the
sensor tasks and the webserver.

Counted in the digital twin's dev soak, which runs the real `sensortask_dev` graph including both
`UART_Comm` instances: **14 039 poll rounds** over a ~60 s run with one rate, against **839** with
the idle rate below. (Count the rounds, not the soak's wall clock — see Part E.7 for why that number
is not usable here.)

**Confirmed on real hardware (2026-09-12, dev bench.)** Counting `ipoll()` calls through a proxy
around the driver's own poller, so the shipped path is what is measured, an idle listener performs
**1244 / 1233 poll rounds over 3 s at 2 ms against 60 / 60 at 50 ms** — a 20.6x cut, and exactly
the ratio the two rates predict (one round per 2.4 ms vs one per 50.0 ms). Repeated interleaved; the
50 ms figure was identical to the round on both runs.

**What that costs the event loop is a smaller number than this section first inferred, and the
inference is withdrawn.** Reasoning from the 400-900 us round trip in F.5.8 to "a quarter to a half"
overstates it. Measured directly — a counter task running flat out beside the listener, interleaved
and order-reversed — an idle listener at 2 ms takes **~18-23 %** of that task's throughput, and at
50 ms the cost falls into the noise. The spread is real: absolute throughput on this board moves
with heap state between runs, exactly as Part E.7 describes, which is why the poll-round count above
is the load-bearing measurement and this one is only corroboration of its direction.

**The fix is a second poll rate, selected by whether the wait carries a deadline.** `ready(mask,
timeout_ms)` polls at `poll_wait_ms` when `timeout_ms > 0` and at `poll_idle_ms` otherwise, because
a wait with no deadline is by construction an idle listener — `_read_frame(device, -1)` inside
`uart_listen()` is the only one this protocol issues — while a wait with a deadline is inside a
transaction whose latency budget is that deadline. Nothing else moves: once the first byte lands,
every remaining wait in that frame carries `timeout` and runs at the fast rate.

`poll_idle_ms` bounds how late the first byte of a frame is noticed, so it belongs well under the
peer's own reply timeout. The dev bench uses 50 ms against `_UART_TIMEOUT_MS = 1000` — a twentieth
of the budget the initiator allows for an ACK, and a 17x cut in idle task switches. A wiring that
leaves it unset keeps the single rate the driver always had, so this is opt-in per instance rather
than a change to every existing caller.

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
similar Unix-port-quirk workaround. **`src/` needs nothing** — it has no `KeyboardInterrupt`
shutdown path, and rp2 has no SIGINT.

**Two call sites, not one (found 2026-09-14 while chasing a `scripts/_digital_twin_ci_suite.py`
`_shutdown()` timeout that needed an external SIGKILL, CI job `grkizi`).**
`run_generic_integration.py`'s own `main()` coroutine has its own `try/finally` that calls
`flush_fram()`/`flush_scd30()` directly (needed so a bounded `--duration` run, which never raises
`KeyboardInterrupt` at all, still flushes on a clean exit) — before this fix, that `finally:` block
called neither `unwedge_heap_after_interrupt()` nor anything else that clears a wedged heap before
its own allocations, in violation of this Part's own stated rule ("call it first ... before
`flush_fram()`/`flush_scd30()`"), which only ever described the *outer* `except KeyboardInterrupt:`
handler around `asyncio.run()`. A `KeyboardInterrupt` reaches one site or the other depending on
what the Unix-port SIGINT handler's `nlr_raise()` (an immediate, synchronous longjmp — see
`ports/unix/unix_mphal.c`'s `sighandler()`, gated on `MICROPY_ASYNC_KBD_INTR`, which the `standard`
build variant used here has enabled) happened to interrupt: `main()`'s own `finally:` runs only
when the interrupt lands while `main()`'s own coroutine is the one currently executing (not
suspended at its own `await asyncio.sleep(...)` line) — otherwise the exception propagates straight
out of `asyncio.core.run_until_complete()`'s scheduler loop without ever entering `main()`'s frame,
landing directly in the outer handler instead, which already called `unwedge_heap_after_interrupt()`
correctly. Fixed by calling it unconditionally at the top of `main()`'s own `finally:` block too,
matching this Part's "unconditional and cheap" reasoning for the outer site. **This was not
reproduced locally** — the SIGINT-during-`gc_collect()` race is inherently timing-dependent
(~5% per interrupt) and the `grkizi` failure's own captured job log has no
`MemoryError: ... heap is locked` line to confirm this was the actual mechanism that run hit, only
a bare `exit code -9` with zero other diagnostic content. This fix is offered as the one concrete,
source-confirmed gap found against this Part's own documented invariant, not as a confirmed
root cause. `scripts/_digital_twin_ci_suite.py`'s `_shutdown()` now captures `/proc/<pid>/status`
(`State`/`VmRSS`), `/proc/<pid>/wchan` (which kernel function, if any, the process is blocked in —
`select`/`poll` vs. a futex vs. genuinely runnable, distinguishing a wedged heap spinning in
Python from a real stuck syscall) and the run's own last 20 log lines on a shutdown timeout, before
the `SIGKILL` fallback — so a future recurrence is self-diagnosing from the CI job log alone.

**Amendment (2026-09-15): the root cause above is now closed, not just worked around.** This
whole race exists only because `MICROPY_ASYNC_KBD_INTR` (named explicitly two paragraphs up) makes
the Unix port's SIGINT handler call `nlr_raise()` directly from the async signal handler — unsafe
at *any* point in interpreter execution, not just inside `gc_collect()`; chasing a different,
more severe symptom of the same root cause (real VM-state corruption, not just a locked heap)
found and fixed this at the source: Part B.14.1's `unix_kbd_intr` build override forces
`MICROPY_ASYNC_KBD_INTR` to `0` for every Unix-port binary this project ever builds (there is no
other build path — every script that needs this binary goes through `toolchain/setup_toolchain.py
setup`), so the interrupt is now always deferred to the VM's own safe bytecode-dispatch checkpoint
(`py/vm.c`'s `pending_exception_check`) and can structurally never land mid `gc_collect()` again.
**`unwedge_heap_after_interrupt()`'s three call sites are kept, deliberately, as defense in
depth** — CLAUDE.md's own memory-safety-discipline ladder already treats a cheap, unconditional
`gc.collect()` this way — but none of them should be expected to ever actually recover a genuinely
wedged heap again via this mechanism; a real recurrence now points at something else entirely
(a different Unix-port SIGINT path, or a binary built outside this project's own tooling). The
digital-twin CI suite's own interrupt-driven shutdowns (cited above and in
`tests/test_digital_twin_unix_port_gc_unwedge.py`'s own comment as this mechanism's real-world
validation) no longer exercise the wedged-heap path at all now that they can't reach it — they
still prove the *shutdown paths themselves* stay correct, just not this specific recovery branch
within them.

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
- **The error-log envelope type** — `print_log.py`'s `ErrorLog` (`dict[str, ErrEntry]`, where
  `ErrEntry` is a `TypedDict` of `ErrCount: int`/`ErrNum: list[int]`/`ErrType: list[str]`), declared
  once under that module's `TYPE_CHECKING` block and imported by every module that returns one.
  Anything returning a `get_log()`/`get_error_counter()` result annotates it `"ErrorLog"` — never
  a re-spelled `dict[str, dict[str, int | list[int] | list[str]]]` or `dict[str, dict[str, Any]]`.
  Both loose spellings were in use across 12 `src/` files and 7 test files before the `--strict`
  pass unified them; because a `TypedDict` types each key exactly, the precise form is also what
  lets callers write `entry["ErrNum"][-1]` without an `isinstance` narrowing dance or an
  `# type: ignore[operator]` (three of which it removed outright).
- **Driver layering/naming/config-schema/error-handling/concurrency/timer shape** — Part C, for a
  sensor driver specifically; complementary to this Part.
- **Buffer ownership and zero-copy region handoff** — `base_classes.py`'s `LockableBuffer`, plus the
  paired-API shape every buffer-holding module in `src/` already follows. A module that moves bytes
  owns **one** contiguous allocation per logical record, sized once from configuration, and hands out
  `memoryview` slices of its regions (`get_buf()`, `get_data_buf()`, and a per-class accessor per
  further region) rather than returning freshly allocated copies. Three rules follow, and they are
  what separates the `src/` implementations from their `python/` ancestors:
  - **Every transfer method comes in pairs** — `write(data)`/`write_into(buf)` and
    `read()`/`read_into(buf)`: the convenience form allocates and copies, the `_into`/`_from` form
    takes a caller-owned buffer and neither allocates nor copies. `asy_fram_manager.py`'s
    `AsyFramChunk` is the reference shape.
  - **Serialisation writes into a caller-supplied buffer at an offset, never into a returned tuple
    or bytes** — `voc_algorithm.py`'s `pack_into(buf, offset)`/`unpack_from(buf, offset)` replacing
    the legacy `get_states()`/`set_states()` tuple pack.
  - **A failed allocation degrades to a `None` buffer, never an exception** — `LockableBuffer`
    catches `MemoryError`/`OverflowError` in its own constructor and leaves `self.buf = None`, and
    every consumer's first act is `if buf is None: return False`.
  The composition this buys is the actual point, and it is already live end to end:
  `asy_sgp40_driver.py` takes one `AsyFramChunkBuffer` from the FRAM chunk, passes its
  `get_data_buf()` memoryview down to `vocalgorithm_proc_ser_des()`, which `struct.pack_into()`s the
  algorithm state **directly into the FRAM chunk's payload region**, and the chunk then writes itself
  out — one allocation, zero copies, across three module layers. Long-lived per-instance scratch
  buffers (`asy_fram_driver.py`'s `_id_buf`/`_status_buf`/`_addr_buf`, `asy_sgp40_driver.py`'s
  `_measure_command`, `asy_i2c_driver.py`'s `_scratch`) are the same rule applied to fixed-size
  command/status traffic, replacing the legacy per-call `bytearray([...])`. `_scratch` is the one
  shared by more than one caller — every device on that bus reads through it — which is sound only
  because each method fills and decodes it with no `await` in between; a scratch reused across a
  suspension point needs an owner and a lock instead, not this shape.
- **Memory-bounded streaming of a dict-shaped GET response** — `_stream_dict_response()` (Part I).
  Any route whose response scales with device configuration returns `await
  _stream_dict_response(result)` instead of `return result`.
- **Frame codecs for a byte-stream link** — `framing_codecs.py`'s `Framing_Base`/`Framing_Pass`/
  `Framing_COBS`, deliberately shaped like `crc_checks.py`'s `CRC_Base`/`CRC_Pass` family so one
  dispatch table can hold either: a base parameterized by constants (`run_length`, `trailer`) that a
  subclass supplies rather than reimplementing the arithmetic, `ready()` reporting a failed scratch
  allocation, and `encode_into()`/`decode_from()` working through a long-lived buffer rather than
  allocating per frame. Injected into `asy_uart_driver.UART` exactly as a CRC is, sitting *above*
  it: write order is build → CRC → encode → delimiter and read order the exact reverse, so a
  protocol layer above stays CRC- and framing-agnostic. A pass-through codec is the default and
  emits byte-for-byte what the driver emitted before the concept existed, which is what makes this
  reusable by a future framed protocol rather than specific to this one.
- **Cross-language mirror: `js/` must encode the same policy `src/` enforces for anything it
  simulates** — `js/mock-server.js` must match the real `src/` endpoint field for field, bound for
  bound; a `src/`-side policy change and its `js/` mirror are one change, not two.
- **Per-instance naming** — `config_manager.py`'s `instance_name()`, never a hand-rolled
  string-concatenation/f-string. See Part C.14.1.
- **Cross-instance wiring declaration** — a `_WIRING: "WiringSchema"` tuple next to a driver's
  `_VAL_*` schema tuples, resolved into a direct constructor-injected reference to the producer's
  own instance (never a getter/callback function). See Part C.14.2.
- **N-to-1 error-source/logger fan-in** — every top-level module implements `get_error_sources()`/
  `get_loggers()` (structurally, `base_classes.py` provides the default for `SensorReader`/
  `SensorReaderConfig`); an aggregator calls these uniformly instead of hand-enumerating each
  module's own nested sub-objects. See Part C.14.3.
- **Watchdog feed** — `system_service.py`'s `SystemService.feed_watchdog()`, never a hand-rolled
  `if self.watchdog is not None: self.watchdog.feed()` at the call site. No-op-safe on a
  watchdog-less build and once `_force_watchdog_starve` latches, so every caller (the task-
  supervisor loop, and buildgen's own one-time boot setup batch, WP6) takes the identical path with
  no branching of its own. Only ever called from a one-time or bounded-loop context, never a place
  that could keep feeding a genuinely hung system forever - that constraint lives with the caller,
  not the method itself.

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
| Poll coordination | One shared poll-manager (single-flight queue) | Measurements and status/settings groups are never polled concurrently by design; every fetch has a shared `AbortController` timeout — `DEFAULT_TIMEOUT_MS = 15000`, see the row below for why that exact value. |
| Per-request timeout value | `poll-manager.js`'s `DEFAULT_TIMEOUT_MS` deliberately **equals** `asy_webserver_service.py`'s `outer_cap_s` (15.0s) | Not an independently-chosen UI number: the server aborts any request at `outer_cap_s` (applied via `asyncio.wait_for()`), so matching it is what makes a slow request surface as *the server's own abort*, which the UI can report, rather than a client-side give-up it cannot explain. Giving up earlier would hide real server aborts behind a generic timeout; later would leave the UI hanging past the point the server already gave up. The heaviest real request is `PUT /status {"ResetErrors": true}`, which resets every error source sequentially (BACKLOG item 24) — this ceiling is a product constraint for its operators, not a test-harness number. The mirror is enforced structurally by `tests_scripts/test_request_timeout_ceiling.py`, which parses `outer_cap_s` out of `src/` with `ast` and pins this constant and both test tiers' own `ResetErrors` client timeouts against it. |
| API reachability | No dedicated API-browser page | Reachable somewhere in the ordinary GUI is enough. |
| Definitions validation | Strict — visible error banner on mismatch | Checks shape/version including `pollGroup` and poll-interval fields. |
| Landing page | Measurements | Matches legacy's default. |
| Card/nav visual treatment | Modernized flat cards; slide-in drawer nav | Soft border/shadow, real light/dark tokens. |
| Rendering safety | `textContent` only, never `innerHTML` | XSS-safe by construction. |
| Numeric coercion/validation | `type_or_range_error()`/`coerce_numeric()`, mirrored in `mock-server.js` | Canonical for every numeric field (A.8, Part G). |
| Dispatch-only PUT fields | `SystemCmd`, `PauseTime`, `lightCmdLED`, `ResetErrors`, plus every schema field carrying `dispatch=true` in its own `@web` tag (`SGPResetVOC`, `ISLCalibrate` today — derive the set from the tags, never from this list alone) | None persisted — each re-dispatches fresh every submission. **This distinction is load-bearing beyond the UI**: a PUT to any *other* field is written straight through to the RP2040's flash filesystem by `config_manager.py`'s own `json.dump()`, i.e. it spends a real flash cycle, which is why `tests_hardware/`'s `@pytest.mark.persistence_write` gate exists and why a dispatch-only PUT is deliberately outside it. An enum field with no GET-matching state renders a blank placeholder by default. |
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
`{schemaVersion, websiteVersion, device, landingSection, defaultPollIntervalMs, sections[]}`.
`websiteVersion` (SPECIFICATION.md Part L.7, `buildgen.version.WEBSITE_VERSION`) is this
project's own product/build version — build provenance only, not validated or rendered anywhere in
the UI, and a genuinely different concept from `schemaVersion` (that field's own wire-format-shape
concern, unaffected by this addition — never conflate the two). **`section`** mirrors
one REST endpoint (`key`, `rest: {get, put?}`, `pollGroup: "live"|"settings"|"none"`, `groups[]`).
**`group`** is normally a `FieldGroup`; Status's error section is `ErrcountGroup`
(`kind: "errcount"`, `modules[]`). **`FieldDef`**: a `kind`
(`readonly|number|string|enum|toggle|composite`) plus kind-specific metadata (`min`/`max`, `mask`,
`options`, `specialValues`, `subFields`, `onLabel`/`offLabel`, `float`, `dispatch`,
`defaultValue`). `dispatch: true` marks a repeatable command field that must re-submit even when
unchanged — **and it is only consulted for `kind: "toggle"` and `kind: "enum"`** (`js/render.js`'s
`collectGroupBody()`, the two sites that compare a control against `resolveFieldValue()`). Every
other kind is already sparse-omitted on a different test — a `number`/`string` only when its input
is blank, a `composite` only when no sub-input is filled — so the flag would be inert on one. That
is why the shipped `wozi.json`/`dev.json` carry it on `SystemCmd` (enum), `ResetErrors` and
`SGPResetVOC` (toggles) but **not** on `PauseTime` (number) or `lightCmdLED` (composite), which are
just as dispatch-only behaviourally (H.6) and need no marking to behave that way. An earlier version
of this paragraph said the flag marks "H.6's list minus `ContMeas`", which read as a claim that all
five carry it; the JSON was right and the wording was wrong (resolved 2026-09-18 by
reading the one consumer, `js/render.js`). `defaultValue` marks a field's safe synthetic baseline when GET
never reports a real value — `ContMeas`'s `defaultValue` is `true` since `false` ("Off") actually
stops measurement, not a no-op (matching the legacy synthetic reference), not the toggle's naive
`false` default. See `wozi.json`/`dev.json` for worked examples — nearly identical field content
(same three drivers); only `device.id`/`displayName` and I2C bus pairing differ, which the
definitions files don't encode since a sensor's schema is driver-defined, not bus-defined.
**Autogeneration**: `buildgen/definitions.py` generates this correctly for all six real devices
today (H.5.1), and is wired into the real build chain as of SPECIFICATION.md Part L.4:
`scripts/build_website.sh` falls back to generating a device's `definitions.json` on the fly
whenever no hand-written `html/definitions/<device>.json` exists. `wozi`/`dev` keep their existing
hand-written files unchanged (`tests_js/` reads those exact files as fixtures); the other four real
devices (`arzi`/`klkizi`/`grkizi`/`schlafzi`), which never had a hand-written file, get one
generated this way — see H.5.1's own "Not yet built" note for what's still open.

## H.5.1 Definitions-file autogeneration

`buildgen.definitions.generate_definitions(model, src_dir)` builds the dict above from an already-
`buildgen.validate.build_model()`-validated `DeviceModel` plus two source-derived inputs: the
`# @web <Field> key=value ...` / `# @web-group key=value ...` comment-tag family
(`buildgen/web_tag.py`, built on `buildgen/tag_comments.py`'s shared near-miss-enforcing scanner
exactly like `@requires` — never a second, separately-tested detector) and a best-effort,
never-imported AST read of each driver's real `ConfigSchema`/`FieldSchema` constant
(`buildgen/schema_ast.py`, same never-import policy as `buildgen.driver_registry`). A tag supplies
only what the schema tuple can't structurally provide — label (always), unit, description, an
explicit `kind=` override for a field with no matching schema constant at all (`ContMeas` —
freestanding, fully tag-specified), and a `special:<value>="<meaning>"` label for a discrete/
sentinel schema value; `kind`/`min`/`max`/`minLength`/`maxLength`/`float` are inferred from the
schema automatically (`kind`: `toggle` for `bool`, `string` for `str`, `enum` when the schema's own
discrete-choice tuple is non-empty, `number` otherwise). `submitGroup=self` is a reserved sentinel
substituted with the TOML instance's own resolved name at generation time — used by scd30/sgp40/
bmp3xx, the only drivers a device can carry more than one instance of; every other group (WiFi's
`identity`/`wifiLed`, NTP's `ntp`, System's `settings`, Notification's `autoConfig`) uses a literal
key instead. Every tag names its target explicitly (`section=`/`submitGroup=`) rather than relying
on file position, since a field's group is not always inferable from where in the file it sits.
Grammar is deliberately minimal, matching BACKLOG.md's own original sketch: a quoted value may not
contain a literal `"` (no escaping), and every tag is a single physical line (no continuation
syntax, unlike `@wiring`'s bracketed-continuation-line allowance — a `@web` tag's payload never
needs it).

**`path`/`decimals` — nested-body and display-precision hints (added for ISL29125).** Most
`get_dict_data()` overrides are flat (`make_dict()`'s own one-level contract), so a tag's `key`
always doubled as the JSON lookup path. `asy_isl29125_driver.py` is the first driver whose
measurement body is genuinely nested (`{"RGB": {"R": ...}, "HSB": {"H": ...}, ...}` — its own
comment near `get_dict_data()` explains why: `make_dict()`'s flat contract cannot express it, so the
driver writes the dict out by hand instead of changing that shared primitive). A tag's optional
`path="RGB.R"` records where a field's real value actually lives in that nested body; `js/
definitions.js`'s `resolveFieldValue()` walks it instead of the flat `key` lookup, and
`validateDefinitions()` rejects a `path` on anything but a `kind=readonly` field (a PUT body is
always flat, so a path on a writable field would render one value and submit a different one) —
`buildgen/web_tag.py` enforces the identical rule at generation time, so a build fails before the
browser ever would. **Syntax: dot-joined (`path="RGB.R"`), not a JSON array** — `_KV_RE` only
captures one quoted-or-bare scalar per `key=value` pair (see its own regex), so a literal array
would need a second value grammar; splitting a plain string at consumption time
(`buildgen/definitions.py`) fits the grammar that already exists instead. `decimals=<int>` is the
sibling hint — a display-precision override, `js/field-format.js`'s `formatFieldValue()` is the one
place in the whole stack that rounds an emitted value (no driver in `src/` rounds anything), so
without it a declared precision is an aspiration; bounded 0–100 (`Number#toFixed()`'s own
`RangeError` ceiling), checked at generation time in `buildgen/web_tag.py` and again in
`js/definitions.js`'s `validateFieldHints()` since a hand-edited `mockdata/*.json`-adjacent file
never goes through the generator. Unlike `path`, `decimals` applies to any numeric field regardless
of `kind` — `GainRatio` (an ordinary flat `sensors` field) carries one too.

A schema-declared sentinel special value must have a matching tag `special:<value>="<meaning>"` or
the build fails loud; a tag's own `special:` entries also survive independently of whatever the
schema's own `special` slot says (SGP40's `BackupPeriod`/`BackupMaxAge`/`WaitTimeNTP` each document
a "0 means X" meaning despite an ordinary, non-sentinel schema tuple — a real in-range value that
also carries a UI meaning, not a validation bypass).

**What stays generator-owned rather than tag-derived**, since none of it is a per-driver fact any
one source file owns: the six-REST-endpoint section skeleton itself (pure routing architecture,
H.4's "mirrors the 6 REST endpoints 1:1"); the dispatch-only, webserver-level fields with no natural
owning file (`SystemCmd`, `PauseTime`, `lightCmdLED`, `ResetErrors`, the Status section's own
live-readonly field lists); and the `warn_co2`/`warn_voc`/`warn_hum` UI metadata
(`_WARN_SIGNAL_WEB_CATALOG`, the same precedent `buildgen.codegen._KNOWN_SIGNALS` already set for
these three TOML wiring keys — kept in sync by cross-reference/comment, not import, since the two
need different shapes for the same keys).

**Correctness proof**: `generate_definitions()` run against `devices/wozi.toml`/`dev.toml`
reproduces the existing hand-written `wozi.json`/`dev.json` exactly (order-insensitive); all six
real devices pass a `validateDefinitions()`-equivalent shape check written directly in Python
(`tests_scripts/test_buildgen_definitions.py`); the mandatory `novel_combo.toml`/
`multi_instance.toml` synthetic fixtures generate successfully, proving per-instance
`resolved_name`-keying genuinely generalizes beyond the two real devices that happen to need it.
**Not yet built**: retiring the two hand-written `wozi.json`/`dev.json` files in favor of generating
them too — the wiring into `scripts/build_website.sh`/CI, and generating one for the four real
devices that never had one, are both done as of Session 6 (see the "Autogeneration" paragraph
above; BACKLOG.md).

## H.6 Errcount (Status section) and dispatch-only field conventions

**Errcount module list**: `{key, label}` per registered module plus each module's `CFGMGR_<name>`
(except SCD30, NVM-backed) plus `WEBSERVER`, looked up in `/status`'s `errcount[key]`. **Keyed per
logger instance, not per driver kind**: the key has to be the name the live object graph actually
publishes, so an instance named `scd30_fan_pressure` needs rows under `SCD30_fan_pressure`/
`CFGMGR_SCD30_fan_pressure` (Part L's instance-naming rule, applied to the website). Getting this
wrong fails in both directions and neither is visible — a published source with no row is never
rendered at all, and a row with no published source renders a permanent, reassuring `0` from
`templates.js`'s own `?? {counter: 0}` fallback. **History
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
own config files — `eslint.config.js`/`vitest.config.js` are not just trigger paths but are
themselves linted (their own `files` block in `eslint.config.js`, Node globals, the same
`BUG_CATCHING_RULES` as `scripts/**/*.mjs`), so the linter is not held to a weaker standard than
the code it checks. Root `.nvmrc` pins the Node version.

**The workflow triggers on `push` to every branch as well as on `pull_request`, and that is not
redundancy.** A `pull_request` run builds `refs/pull/N/merge`; when a PR conflicts with its base
that ref cannot be created, so GitHub creates **no run at all** — the branch silently stops being
tested, with nothing red anywhere to notice. Found the hard way (2026-09-18): `main` landed its own
ISL29125 promotion on 2026-09-14, `claude/automated-build-chain-nuzumw` went conflicted the same
day, and because `push` was scoped to `main` alone, **128 commits went unverified** before anyone
looked. The `push` leg is the branch's own guaranteed coverage; the shared concurrency group
(`github.head_ref || github.ref_name`, identical for both triggers on one branch) plus
`cancel-in-progress` keeps exactly one of the two alive per push, so the second trigger costs no
extra matrix time. This is the same failure class as the `paths:`-filtered second workflow file
above — a check that never fires reads exactly like a check that passed. **When judging whether a
branch is green, check that CI actually ran on its head commit**, not just that nothing is red.

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

**Revisited 2026-09-18 — the I2C register buffers were safe but wasteful.** They are small and
datasheet-derived, as stated above, but `get_bits()`/`set_bits()`/`get_register_struct()` allocated
a *fresh* `bytes` for every single register read, at every sensor's own read interval, forever —
the churning-same-shaped-objects pattern I.4 names as the thing to fix at the source rather than
absorb. They now read through `machine.I2C.readfrom_mem_into()` into one long-lived 32-byte scratch
per `I2C` instance (a `memoryview` slice per call, which `struct.unpack()` already allocated anyway).
No public signature changed. The buffer is shared across every device on a bus, which is safe only
because each of these methods fills and decodes it with no `await` in between and no `Timer`/
`Pin.irq` callback in this codebase touches I2C — both verified against the real code. A read larger
than the scratch (nothing today; BMP3XX's 21-byte calibration block is the largest) falls back to
the allocating call rather than being refused.

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

**(a) Design for zero `MemoryError`s first — catching is a last-resort backstop for genuinely
unavoidable, uncontrollable conditions, never an acceptable steady-state outcome of ordinary or
worst-case load a well-designed code path should have avoided by construction.** A call site that
can raise `MemoryError` from a caller-controllable or growing allocation catches
`(OSError, MemoryError)` and degrades locally — but a caught `MemoryError`, even one that never
crashes anything, is a design defect to fix at its source, not a handled case to accept. Not a
blanket policy on every `asyncio` primitive (F.2) — only where a concrete, genuinely-unavoidable
risk exists (an external condition outside this code's own control), never as a substitute for
fixing an allocation pattern this code itself controls. **(b) Degrade gracefully** — a caught
failure produces a well-defined "unavailable"/`None`/`False` result, never an unguarded re-raise
(`_dump_status_source()` et al. substitute `{"error":"unavailable"}` for one failed source rather
than discarding the whole response). **(c) Restart the task when it really bubbles up** —
`start_and_check_tasks()` already restarts any task that ends for any reason, `MemoryError`
included; already correct. **(d) The watchdog is the final resort, and must stop being fed once
self-healing has genuinely failed** — the `task_errors` counter escalates past repeated restarts to
`reboot_system()`, at which point the loop stops feeding the watchdog — the same backstop principle
as a wedged bus/WiFi link.

**(e) Prove there are no memory issues under native `gc` defaults, first — for every test, not only
stress/hammer ones, and the bar is zero `MemoryError`s, caught or not.** The whole suite — digital
twin and real hardware alike, no relaxed bar for either — must run to completion with
`gc.threshold(-1)` (MicroPython's real reactive-only default) and with no nonstandard `gc` settings
or added `gc.collect()` calls anywhere in the business logic or the test's own setup propping it
up (the boot-confined placement reset in (f.1) is the one structural exception, and it is part of
the firmware's own boot rather than a test's setup — the suite must still clear this stage with it
in). A test that only passes because a `MemoryError` was caught and logged without crashing anything
is not a passing result at this stage — a caught-but-real allocation failure is exactly the signal
this stage exists to catch, and "it didn't crash" is not the same claim as "it didn't happen."
**One narrow, evidence-backed exception**: `digital_twin/run_generic_integration.py`'s
`_mem_sampler()` calls `gc.collect()` on its own fixed wall-clock timer (`--mem-sample-interval-ms`,
decoupled from the soak's request/response path entirely — E.9) purely to settle `gc.mem_free()`
before sampling it for the host-side memory-trend leak check
(`scripts/_digital_twin_ci_suite.py`'s Run 11). It runs nowhere near a request/response and cannot
mask a real `MemoryError` (every `fetch()` call already catches and records its own, independently).
Removing it (2026-09-14, auditing the now-retired in-process `_soak()`'s own identical `gc.collect()`
against this exact rule when the soak moved host-side) was tried and confirmed directly to make the
check *worse*: without a settled baseline, `gc.mem_free()` swings with incidental reactive-GC timing
alone (measured on a genuinely healthy `wozi` run: `min=99808, max=1347104` across 20 cycles, a
false-positive "trend declined by 413990 bytes" against an 18318-byte tolerance calibrated for the
collected regime). A `gc.collect()` call that stabilizes what a *later*, unrelated line measures —
rather than relieving pressure an allocation it's adjacent to would otherwise have failed under — is
not the pattern this rule exists to forbid; don't re-flag it without new evidence the trend check
itself has changed.
**(f) A `gc.threshold()` value (or a `gc.collect()` call) is defense in depth applied only once (e)
already holds — never the fix itself, and never reached for to make a failing (e)-stage test
pass.** Every generated boot entry (`buildgen.codegen.generate_boot_entry_source()`, formerly the
hand-written `boot_entry/*_boot.py`) sets `gc.threshold(32768)` for exactly this reason, chosen
*after* the `/status` fix already eliminated the real-hardware `MemoryError` with no threshold
change at all — it lifts an already-stable system further from a stability threshold it would
otherwise sit close to, it does not create that stability. Once applied, the *same* full suite must
still pass with it enabled too — it's an additive safety margin layered on an already-safe design,
never a swap of one mode for another, and never itself the explanation for why a test now passes.

**(f.1) The one structural exception: a boot-confined placement reset.** `gc.collect()` between the
units of the two *one-time* setup lists — the generated setup batch (`buildgen.codegen`'s
`_emit_build_system()`, one before the batch and one after each module's `feed_watchdog()`) and
`SystemService.start_and_check_tasks()`'s task-starter loop (one before the loop, one after each
starter) — **and nowhere else whatsoever**. This is not a threshold, not hygiene, and **not** a fix
for an allocation that failed: MicroPython's collector never moves an object, so nothing is
compacted. What each call changes is *where the next allocations land* — `gc_collect_end()` resets
the allocator's free-scan index to zero (`py/gc.c`), so the following module's permanent objects
take the lowest fitting holes instead of being pushed above the batch's own churn high-water mark.
It is therefore placement discipline for the survivors those two lists create, applied at the only
two points in the firmware's life where permanent objects are born in a known sequence.

Grounded in the pinned MicroPython documentation's own recommendation
(`docs/reference/constrained.rst:413-437` at `v1.29.0`: a demanded collection "is advantageous ...
firstly to preempt fragmentation", and "`gc.collect()` issued after the import will ameliorate the
problem"), and in this repo's own measurement. **The measured effect, stated so nobody later
mistakes it for (f)-stage margin**: on the twin at `gc.threshold(-1)` — the (e)-stage configuration
— it is worth a factor of 3.2 to 6.9 on largest-contiguous-over-free, taking the post-batch figure
from 11.9-14.2% to 44.6-45.0% and the post-task-list figure from 8.1-8.4% to 57.7-57.8%
(HEAP_FRAGMENTATION_MEASUREMENTS.md §7A.2/§7A.8). At the shipped `gc.threshold(32768)` it changes
nothing measurable (§7A.6), which is the honest reading: this earns its place at the (e) stage, not
as (f) margin.

Confined mechanically, not by convention: `tests_scripts/test_gc_collect_sites.py` walks `src/`
with `ast` and asserts the only `gc.collect()` call site is `system_service.start_and_check_tasks`,
attributing every call to its enclosing function — so a new call anywhere, including at module
level, and a rename of the allowed site both fail it — plus a textual assertion that `buildgen/`
emits one only from `codegen.py`. The test carries its own two self-tests, so the guard is checked
rather than assumed. `scripts/lint.sh` carries the same rule as a fast path, so a widening
fails the lint gate before the suite runs: `gc.collect(` under `src/` only in `system_service.py`,
under `buildgen/` only in `codegen.py`. Both were verified to bite on an injected call. **The prohibition in (e), (f) and (g) is otherwise unchanged**: no `gc.collect()` in
business logic, none in the run phase (the supervisor loop under the starter list is the run phase
and is asserted to have none), and none as the remedy for memory pressure.

**(g) When a genuine memory-pressure issue is found, fix it with a design-level technique that
relieves the pressure directly** — chunking a large operation, reusing/pre-allocating buffers
instead of churning same-shaped objects, streaming (`_stream_dict_response()`, I.3) — never a
GC-policy change or an added `gc.collect()` call.

**Applying this scheme to new code**: before adding a function/module that holds, builds, or grows
an allocation whose size isn't a small, provably-fixed constant, run it through (a)-(d) at design
time and give it its own (e)/(f)-shaped test pair. This is a standing rule, not a one-time audit
finding — it governs every test in this repo from now on, digital-twin and real-hardware alike.

## I.5 Real-hardware confirmation

Every parameter this audit's Unix-port tests couldn't reach (an 8MB heap vs. RP2040's real budget)
was confirmed on real target hardware (2026-09-08): `gc.threshold(32768)` (real hammer-load
`mem_free` floor 91312 bytes vs. 128 bytes at the reactive-only default), the real GC pause-length
range (I.1), and `_MAX_STATUS_PIECE_BYTES`'s real headroom (I.3).
`tests_hardware/bench/test_memory_stress_bench.py` carries the permanent real-hardware regression
coverage (a 120s always-run hammer test plus a `long_soak`-gated 600s variant) — nothing from this
audit remains open pending hardware. Those assert the *outcome* (no `MemoryError`, no reboot,
enough requests through); the headroom the system starts from is asserted separately by
`tests_hardware/flash/test_memory_stress.py`'s `test_real_gc_heap_headroom_survives_a_full_system_build`
(Part F.5.3 for the 1.29 figures). Note the 91,312 B above is a *loaded* floor and the F.5.3
numbers are at rest — don't compare them directly.

---

# Part J — UART Message Protocol (`asy_uart_comm.py`)

The wire protocol and role model of `src/asy_uart_comm.py`, the point-to-point UART message
transport. No vendor document or prior specification exists — this Part **is** the specification,
reconstructed from the field-proven legacy implementation (`python/IndividualDrivers/asy_uart_comm.py`)
and confirmed by the project owner (2026-09-11). Read it before changing anything about the protocol.

**The module is promoted.** It sits above `asy_uart_driver.UART` the way `asy_fram_manager.py` sits
above `asy_fram_driver.py`: a sync allocate-only constructor with a readiness gate, an injected
logger by either route, `get_task_starters()`/`get_timer_starters()`/`get_error_counter()`/
`reset_error_counter()` for generic supervision and observability, and a never-raise contract on
every entry point. `dev` carries two instances across its crossover jumper (A.7 step 13b); `wozi`
carries none. The jumper uses UART0 on GP0/GP1 and UART1 on GP8/GP9: of the other legal pin-mux
pairs, GPIO24/25 and GPIO28/29 each have a half the wireless chip takes (A.6), and GPIO16/17 is
left free because a BME688's BSEC coprocessor wants UART0 there and one peripheral serves one pair. Everything below describes what the promoted module does, not what the legacy one
did — the differences are enumerated in `UART_C_PORT_CHANGELOG.md`.

## J.1 Scope and the two-implementation contract

The module is **standalone and self-contained** — a general message transport over a point-to-point
serial link, with no sensor, device or application semantics of its own. Command IDs, payload layouts
and expected sizes all belong to the caller. Its first use case (a BME688/BSEC coprocessor) is
explicitly *not* part of its scope and does not constrain its design.

**Not constraining it is not the same as not serving it**, and that was checked rather than assumed
(2026-09-13). `dev_legacy/asy_bsec_driver.py`'s whole `BSEC_UART` control flow replays over the
promoted module at the sizes `dev_legacy/sensortask-dev.py` actually deployed — 13 datafields, a
221-byte BSEC state, `payload_size` 20, an 8-byte system status — covering all five shapes it used:
a fixed-size GET decoded with `struct`, a don't-care GET for when the stored state size was unknown,
a payload-less SET as a pure command, a small SET, and a 221-byte multi-chunk SET. Opcode and
payload stay separate fields (an id in chunk 1, data from chunk 2), and what the legacy left
implicit — that only one side ever initiates — is now the role gate. Two conformance tests in
`tests/test_asy_uart_comm.py` pin it, each verified to fail when the capability is removed; they
demonstrate rather than constrain, since any API able to express the flow passes them.
**One deployed value has to change in a faithful port**: `rxbuf` 32 is refused (`errno` 15) against
this module's 80-byte per-poll-interval `rxbuf` floor (J.6) at 115200 baud — loud at construction
rather than an intermittent lost tail, and 128 bytes of RX ring costs nothing. Two further
spellings the board's own exploratory script used still work unchanged: a GET declaring
`exp_size=0` (J.9's *must be exactly empty*, a different claim from *don't care*) and a SET whose
payload is an empty `bytearray()` rather than `None`.

**A second implementation of this protocol exists in C**, running on the Arduino peer. It mirrors the
Python implementation's *intended* behavior and is owner-validated over many real transmissions — but
**how far that mirroring extends to the known flaws is unverified**: it may share some, not others,
and may have introduced its own. Establishing that is future work, never an assumption to build on.
The C source is not yet in this repo; importing and reconciling it is a future session's job
(BACKLOG.md). Until then:

- **Every protocol-level change is logged in `UART_C_PORT_CHANGELOG.md`** — a temporary file, deleted
  once the C side is reconciled. A change is protocol-level ("Class A") if it alters the bytes
  emitted, which received frames are accepted vs. rejected, or any timing the peer depends on;
  everything else is Class B and is logged too, as explicitly-no-C-impact.
- **Prefer Class A changes that only tighten receiver validation, never ones that change emitted
  bytes.** A receiver-strictness change rejects only frames a *conforming* peer never sends, so a
  mixed-version pair (new Python ↔ old C) keeps working and the peer's reflash can happen in either
  order — **conditional on the C side actually conforming, which each such change must re-verify
  against the C source once it is imported.** A change to emitted bytes is a coordinated flag-day
  needing an explicit owner decision.

## J.2 Role model

**One side is constructed as the initiator, the other as the responder. This is not a symmetric peer
protocol, and initiation is restricted to one side by construction** — there is no collision
arbitration anywhere in the design, so simultaneous initiation is out of contract rather than a case
to handle.

Role governs *who may start a transaction*, not data direction: a responder still transmits a
complete payload train when answering a GET, and acknowledges every frame it receives. An initiator
uses `uart_get()`/`uart_set()` and never listens; a responder uses `uart_listen()` and never
initiates.

**The role is enforced structurally, not by convention.** The role is a constructor parameter, and
the initiation entry points refuse on the wrong role (C.13's readiness-gate treatment — a logged
refusal returning the module's normal failure sentinel, never an exception). Holding the session lock
for the duration of one `uart_listen()` call is *not* sufficient on its own: the lock is released
between calls, so an application could otherwise interleave an initiation into a responder's listen
loop and produce exactly the simultaneous initiation the design has no arbitration for. The
responder's own answer to a GET is unaffected — it runs through the internal unlocked SET path, not
through the public `uart_set()` entry point that the role gate covers.

## J.3 Frame format

Every frame is exactly `5 + payload_size` bytes, the payload field zero-padded to its full width.
There is no delimiter, no length prefix and no escaping: **the fixed size is the framing**, which is
what lets a receiver take a whole frame as one fixed-length read and verify it in one go.

CRC framing is **optional and not part of this layer** — it is configured on the `UART` bus object
and appended/verified/stripped transparently below it, and `CRC_Pass`'s zero length makes every
framing calculation degrade to the no-CRC case automatically, so this layer is entirely CRC-agnostic.
The same is true of the frame codec that now sits alongside it (`framing_codecs.py`, Part G.2):
`Framing_Pass` is the default and adds nothing, so the fixed size stays the framing. Selecting a
delimited codec is a wire change and a coordinated flag day (changelog A11), not a local decision.
Without a CRC, the only integrity checking left is this layer's own structural validation (command,
chunk index, size bounds, ACK `UID` match).

**The CRC algorithm and its byte order are part of the wire contract and must be specified, never
inherited.** The field-proven legacy configuration — `python/IndividualDrivers/asy_uart.py`'s own
`CRC16`, which is what the C peer mirrors — is an LSB-first/right-shifting variant over poly `0x1021`
with init `0xFFFF`, appended in the platform's **native** byte order; that is *not* CRC-16/CCITT-FALSE,
and it interoperates between the two peers only because both happen to be little-endian.
`src/crc_checks.py`'s `CRC16` is a genuine MSB-first CRC-16/CCITT-FALSE appended big-endian. **The two
are not wire-compatible** — verified directly: each is self-consistent (residue zero over payload+CRC)
and each rejects the other's frames. Moving this module onto `src/`'s driver therefore changes the
bytes on the wire, which is a coordinated flag-day rather than a receiver-strictness change
(`UART_C_PORT_CHANGELOG.md` A7).

| Offset | Field | Semantics |
|---|---|---|
| 0 | `UID` | Per-frame nonce, incremented per transmitted frame, wrapping `0xFE → 0`. Matches an ACK to the frame it acknowledges; carries no stream-ordering meaning. **Never `0xFF`** — see below. |
| 1 | `CMD` | `ACK 0x01`, `GET 0x02`, `SET 0x04`. |
| 2 | `SIZE` | Bytes of the payload field actually used (`0 … payload_size`). |
| 3 | `CHUNKS` | Total frames in this train (`1 … 0xFF`). |
| 4 | `CUR_CHUNK` | This frame's index within the train, 1-based. |
| 5… | payload | `SIZE` meaningful bytes, zero-padded to `payload_size`. |

An ACK frame carries the acknowledged frame's `UID`, `SIZE = 0`, `CHUNKS = 1`, `CUR_CHUNK = 1`. An
ACK echoes the received `UID` and does not consume one of the sender's own.

**`0xFF` is deliberately kept out of the `UID` space** (author-confirmed rationale, 2026-09-11): it is
a free off-by-one safety barrier, so that any implementation adding 1 to a UID it just received — in
either language — stays inside the byte rather than rolling over uncontrolled. The only route to `0`
is the controlled wrap. Two further properties follow, both worth preserving:

- The value space (`0 … 0xFE`, 255 values) is **exactly** as large as the longest possible train
  (`CHUNKS` maxes at 255, one UID consumed per frame), so no UID repeats within a single train and a
  stale ACK from an earlier frame of the same transfer can never be mistaken for the current one.
- Any code predicting the *next* expected UID must reuse the same controlled wrap, never a bare `+1`,
  which mispredicts precisely at the `0xFE → 0` boundary.

Do not "fix" the wrap to `0xFF`: it removes the barrier and the no-repeat-within-a-train property
together.

## J.4 Transactions

A logical message is a **chunk train**. Chunk 1 is always the command header: its payload is the
single command-ID byte, `SIZE = 1`. Chunks 2…N carry the data. **Every frame is individually
acknowledged before the next is sent** — stop-and-wait at frame granularity, never more than one
frame in flight, no windowing and no NAK.

**SET (initiator → responder)** — `CHUNKS = ceil(len(payload) / payload_size) + 1`, floored at 2, so
even a payload-less command still has one data chunk to acknowledge and is confirmed end-to-end
rather than merely heard. Each chunk gets a fresh `UID`.

**GET (initiator → responder)** — the initiator sends a one-chunk GET train whose payload is the
command ID; the responder answers with a **SET train in the opposite direction** whose chunk 1 echoes
that same ID. A GET answer is therefore literally a SET transfer, which is why two primitives (send a
train / receive a train) cover all four directions, and why the responder's GET branch and the
initiator's SET path are the same code.

**Receiving a train** — validate each frame (command, chunk index exactly as expected, `SIZE` within
bounds), append `SIZE` payload bytes, acknowledge. `SIZE = 0` on chunk 2 means a genuinely empty
payload, a distinct outcome from failure. An expected total size may be supplied — *don't care*,
*exactly empty*, or *exactly N* — enforced both incrementally (reject as soon as the running total
would overshoot) and finally (exact match).

**Rejection is signalled by withholding an ACK.** There is no NAK. The final chunk's acknowledgement
is deliberately deferred until after the total-size check passes, so a sender learns its transfer was
rejected by timing out rather than by a reply.

## J.5 Timing, flow control and recovery

**Two-level timeouts.** Waiting for a *new* message is either unbounded (a responder listening) or
bounded by `timeout` (an initiator awaiting a reply); once a frame has begun arriving, the inter-part
timeout is always `timeout`. A half-received frame must complete promptly or the whole frame is
abandoned — the anti-desync rule.

**Recovery is quiesce-and-resync, never retransmission.** Nothing is ever re-sent. On any fault — CRC
failure (the frame simply never completes), unexpected chunk index, size mismatch, missing ACK — the
side that noticed drains its receive path until the line has been quiet for `1.5 × timeout`, then
holds off initiating for a further `1.5 × timeout`. **"Any fault" includes a purely local one raised
mid-train**, which is easy to read as exempt because nothing arrived wrong: a streamed send whose
`pull` callback raises, returns a non-count or short-fills a non-final chunk has already put chunk 1
on the wire and had it acknowledged, so the peer is mid-train and will drain — and this side must
quiesce with it or transmit straight into that window. Found violating this on 2026-09-13 and fixed;
the code now routes every such abort through the same `_fault()` helper as a link fault. With no framing marker to resync against, this
mutual silence is what gets both sides back onto a clean frame boundary. **Both constants are part of
the contract** (J.1's Class A rule) — a peer draining for less can transmit into the other's drain
window.

The write hold-off gates *initiating* transmissions only: acknowledgements are always sent, so a side
keeps confirming the peer's traffic while backing off from its own.

**Unsticking from outside.** A listening responder blocks indefinitely while holding the bus lock, so
the only safe interruption comes from another task: cancel the in-flight read from outside the lock
and let that read's own failure path perform the drain, or — if nothing was in flight — take the lock
and drain directly. This is why `asy_uart_driver.py` keeps `cancel_read_timeout()` and infers "a read
is in flight" from the lock rather than a flag of its own (C.3.2). That handshake is **latched and
bounded**: a request survives an unrelated `ready()` entry, is acknowledged on every exit from the
locked region as well as from inside the poll loop, and reports rather than blocks if a wedged
holder never acknowledges — without which the recovery route could itself wedge (changelog B15).

**The drain is bounded** (changelog A5), and `setup()` runs one at boot before the readiness gate
opens: a peer mid-train, or one that outlived this side's reset, leaves partial-frame bytes in the
receive buffer, and recovering from those reactively would log a fault on every boot of a live link
— indistinguishable in the FRAM history from a real one. That boot drain shortens only its *first*
probe, so a healthy link pays nothing for it; once a byte does turn up, every later round uses the
full quiet window exactly as a resync does. **Hitting the bound is reported by flagging the caller,
never by logging in place**: the boot drain is not a fault and so persists nothing, while a resync
persists the more specific of its two warnings, once the drain has decided which case this is
(C.7.1's `wrnno` 10/11 note).

## J.6 Deployment parameters

`payload_size` and `timeout` are **agreed out of band and must match on both ends** — nothing is
negotiated, now or at the C reconciliation (owner decision, 2026-09-11). A mismatched pair is
therefore *diagnosed*, never recovered: bytes keep arriving while not one frame ever validates, and
the module logs that signature (`errno` 32) naming all three candidates (CRC algorithm, baud rate,
`payload_size`) rather than guessing one.

**That diagnostic has a known blind spot, accepted rather than fixed** (owner decision,
2026-09-12). `_resync()` gates it on `drained and self._valid_frames == 0`, but `drained` counts
only what `_drain()` finds *after* a failure — and `readinto_until_complete()` has already consumed
the short frame's bytes while waiting for a full-length one, discarding them on timeout. Measured
against a genuinely `payload_size`-mismatched peer: `drained == 0` at every one of five resyncs, so
`errno` 32 never fires. **What errno 32 does still catch is unparseable bytes arriving while this
side is not mid-read** — a peer spewing continuously onto an idle line, which is the shape a bad
baud rate often takes. **What it misses is a speak-when-spoken-to peer**, where every stray byte is
swallowed by the failing read: that presents as repeated `errno` 22 (read timeout) plus `wrnno` 10
resync warnings, and *that* is the signature to look for at the C reconciliation. Closing the gap
would mean either giving `asy_uart_driver.UART` a flag that exists solely for this layer to read,
or changing `readinto_until_complete()`'s sentinel contract to return a partial count for every
caller — both more coupling than a logging line is worth. `tests/test_uart_comm_hazard.py`'s
`..._a_peer_that_never_produces_a_valid_frame_is_diagnosed` pins the current behaviour, so it
inverts the day anyone does change it. `payload_size` must be in `1 … 255` (`SIZE`/`CHUNKS` are single bytes; a zero-width
payload has no room for the command ID). A mismatch desyncs the link outright, so an out-of-range
value must never be silently clamped — C.13's readiness-gate treatment instead. Maximum transferable
payload is `(0xFF - 1) × payload_size`.

**Wire cost.** Every frame is exactly `5 + payload_size + crc` bytes, ACKs included — an ACK carries
no payload but transmits `payload_size` bytes of padding regardless. At the defaults
(`payload_size=48`, CRC16) a chunk exchange therefore costs `55 + 55 = 110` bytes of airtime to move
48 payload bytes: 21.8 % efficiency for a single-chunk transfer, 39.7 % at 480 bytes, and an
asymptote of **43.6 %**. This is accepted for the intended traffic (short bursts between two
participants) and is not on its own a reason to change the wire format — see
`UART_C_PORT_CHANGELOG.md` A10/A11 for the two candidates that would.

**Poll granularity dominates throughput, not baud rate or protocol overhead.**
`asy_uart_driver.py`'s `ready()` yields via `asyncio.sleep_ms(poll_wait_ms)` between readiness
checks, defaulting to **20 ms**. A 55-byte frame takes 4.8 ms on the wire at 115200 baud but costs
one or more whole poll intervals to notice, in each direction, for every frame of a stop-and-wait
exchange. Measured against the defaults, a 480-byte transfer spends roughly 1.1 s of wall clock to
move 480 bytes over an 11.5 kB/s link — about 4 % of link capacity, of which the overwhelming
majority is poll latency. **A `UART` instance driving this protocol must therefore be constructed
with a single-digit `poll_wait_ms`**; leaving the default in place makes every other efficiency
property of the protocol irrelevant.

**That rate is for a transaction, and a responder must not idle at it.** A listener waiting on a
frame that may never come pays one scheduler round trip per poll for as long as it waits, which at
2 ms is a large and permanent share of the event loop (Part F.5.9). The same instance therefore
takes a second, slower `poll_idle_ms` for a wait with no deadline — 50 ms on the dev bench. It is
the first-byte notice latency, so it must stay well under the peer's `timeout`: the initiator's ACK
budget has to cover it, the frame read and the reply. **That is a construction refusal, not just a
rule** — `timeout`'s floor below is the enforcement, and it carries `poll_idle_ms` precisely because
a budget that cannot cover the idle poll expires before an idle responder has looked at the line
once, so every request on a physically sound link fails.

**`rxbuf` is checked at construction against two independent floors**, because stop-and-wait means a
*complete* frame can land before the reader is next scheduled, and a frame whose tail the driver
silently dropped is indistinguishable from a link fault: one whole framed frame (at
`payload_size = 255` that is 260 bytes against the driver's own 256-byte default, so the maximum
legal `payload_size` overruns the default outright), and one poll interval's worth of arrivals
(`baud/10 × (poll_wait_ms + jitter)` — about 288 bytes at 115200 baud, the 20 ms default and the
5 ms of scheduling slack the module adds; 230 without that slack). Too
small is a readiness-gate refusal with its own errno, never a silent degradation. `timeout` has a
floor too: `2 × poll_wait_ms + poll_idle_ms +` the measured worst-case GC pause. The GC term is what
stops an ordinary collection reading as a link fault and resyncing the link continuously under memory
pressure; the `poll_idle_ms` term is the peer's own first-byte notice latency above. Both ends agree
`timeout` out of band, so checking the local instance's idle rate against it is what guarantees the
peer's budget covers this side's latency — and it is checkable locally, which is the point.

## J.7 Testing: the loopback model

**Self-compatibility is a required, tested property**: one Python instance as initiator and one as
responder must interoperate perfectly. The dev bench embodies this physically (the permanent
UART0↔UART1 crossover jumper, `dev_legacy/README.md`), and it must also be reproducible without
hardware, at **the `machine.UART` level — below `asy_uart_driver.py`** — in `tests/machine.py` (unit
tier) and `digital_twin/machine.py` (twin tier, which has no `UART` at all today). The link is
modelled per direction, with byte-stream fault injection: dropped/corrupted bytes, mid-frame
truncation, injected noise, delayed delivery, stalled TX readiness, short writes, duplicated frames,
receive-buffer overrun, and one-sided silence.

Both models exist: `tests/machine.py`'s `UARTLink` (synchronous delivery, deterministic fault
knobs) and `digital_twin/machine.py`'s (the same semantics plus real wire time derived from the
configured baud rate, so a drain or cooldown cannot pass for the wrong reason). They are held to one
shared set of assertions in `tests/_uart_link_contract.py` — the two may differ in fidelity, never
in semantics — with `link.settle()` as the single seam between them.

**Constraint — a loopback harness must never register a fake UART with a real `select.poll()`.** The
Unix port does not re-evaluate a Python object's `ioctl()` after registration (the reason
`tests/test_asy_uart_driver.py`'s `_StepPoller` exists, and the cause of a CI-only hang — CLAUDE.md's
"Known hang cause"), and `digital_twin/unix_port_poll_prewarm.py` records a related `modselect.c`
segfault with non-fd poll objects. The mock layer therefore supplies a paired poller stand-in
re-querying each fake's `ioctl()` per call, installed by reassigning `uart.poller` after construction
— the project's established mocking mechanism, keeping `src/` free of a testability seam.

## J.8 Memory model

**The protocol chunks the wire; the API must chunk the memory too.** Splitting a payload into frames
is what lets a transfer cross a peer's small UART buffers, but it does nothing for RAM if both
endpoints still have to materialise the whole payload at once — and the legacy implementation does
exactly that: the receiver grows `res` by `+=` across the whole train (254 reallocations and a ~2×
peak at the final copy for a maximum 12192-byte transfer, on a 264 kB device), and a responder's GET
callback must return the complete answer as one buffer before the first frame goes out. Requirement
"large payloads over little buffers" is only half-met until this is fixed.

The module therefore follows Part G.2's buffer-ownership primitive, in the same paired shape
`asy_fram_manager.py` uses (all of the following is implemented, not proposed):

- **Two long-lived frame buffers per instance**, `LockableBuffer(framing.max_encoded(5 +
  payload_size + crc_length), data_start=5, data_length=payload_size)`, allocated once from
  configuration — the buffer holds what goes *on the wire*, so it has to carry the CRC the bus
  driver appends and any codec overhead above it, not just the `5 + payload_size` frame: `get_buf()` is what the bus driver's
  `writefrom()`/`readinto_until_complete()` operate on, `get_data_buf()` is the payload region. Header
  fields are written in place by index. Steady-state frame traffic allocates nothing.
- **Paired transfer APIs.** `uart_set(id, data)`/`uart_get(id)` keep today's allocate-and-copy
  convenience for small payloads; `_into`/`_from` counterparts take a caller-owned buffer, and a
  callback form drives a chunk at a time so a large transfer can stream to or from FRAM/flash without
  ever existing in RAM as a whole.
- **Preallocate from `CHUNKS`, never grow.** The total upper bound `CHUNKS × payload_size` is known
  the moment the first frame of a train arrives, and the exact size is known whenever the caller
  passed `exp_size` — neither case justifies an incrementally grown accumulator.
- **A failed allocation degrades to the module's normal failure sentinel** and the quiesce-and-resync
  path, never an exception (J.1).

One consequence is worth stating because it is counterintuitive: a received frame is read whole into
the instance's RX frame buffer and its payload region then slice-assigned into the destination, and
*not* read header-first so the payload can land directly at its final offset. The two-stage read
would save one ≤`payload_size` memcpy but costs an extra `ready()` round — one whole `poll_wait_ms`
(J.6) — and, with CRC enabled, is not available at all, since the CRC covers the frame as a unit.

**Padding must be zero-filled from a preallocated zero buffer**, not from a freshly built one. Today
the full-length framing means every frame carries `payload_size - size` unused bytes; leaving them
unwritten would transmit the previous frame's payload remnants.

## J.9 Module contract: shape, results and sentinels

**A plain class, not a `SensorReader` subclass** (owner-delegated decision, 2026-09-11, resolved
against precedent). Every existing subclass is one for a measurement snapshot or a
`ConfigManager`-backed schema, and this module has neither: `payload_size`/`timeout` are out-of-band
agreements a runtime write must not be able to desync, and a link-state snapshot would be a new
top-level feature the refactor is not for. `asy_fram_manager.py` is its closest structural match.
`_error_check()` is therefore neither reimplemented (G.1) nor needed — its give-up exists so the
supervisor can re-run an `_init_<sensor>()` and re-initialize hardware, and this module owns none.
C.9's capped exponential backoff is the primitive that fits a link fault. `errno`/`wrnno` still align
to `base_classes.py`'s reservation regardless of the base class (C.7.1).

**`None` means failure; an empty result means a genuinely empty payload.** The two must never
collapse, at any of the four result shapes: `uart_get()` returns `None` or a right-sized buffer that
may be zero-length; the `_into` and streaming forms mirror it as `None` versus 0 bytes written. The
same distinction exists on the request side — `exp_size=None` is *don't care*, `exp_size=0` is
*must be exactly empty*, and a peer answering a zero-size GET with data is refused rather than
delivered.

**`uart_listen()` returns a `ListenResult` namedtuple** (`cmd_id`, `cmd`, `payload`) on every path,
never a bare `None` off the end of the function. Its one allocation is per logical message, not per
frame — a 255-chunk train still allocates exactly one — so J.8's zero-allocation frame path is
untouched. C.6's `make_dict()` repr-parsing landmine does not apply: this namedtuple is never
serialized.

**A lost final ACK folds into failure**, deliberately, rather than becoming a third "delivered but
unconfirmed" state. Because the final chunk's acknowledgement is deferred until after the responder's
total-size check (J.4), losing it leaves the responder having *already* accepted and delivered the
whole train while the initiator reports failure. This is the protocol's at-least-once seam: a caller
that retries on a failed `uart_set()` must tolerate the peer seeing the message twice. A third state
would buy nothing — no retransmission exists to hang it on, and the application-level answer is the
same either way.

---

# Part K — Adding a New Sensor/Module: The Full Checklist

The procedural counterpart to Parts C/D: those describe what a driver's own code and quality bar
must look like; this Part is the concrete, ordered list of every file a promotion actually has to
touch to go from "a tested driver exists" to "wired into buildgen, generating correctly for every
device that needs it, with real coverage at every tier." Distilled from two real promotions done
this way — UART (`asy_uart_comm.py`/`asy_uart_link_driver.py`, PRs #70/#80) and ISL29125
(`asy_isl29125_driver.py`, PR #83) plus its own two immediate follow-ups (PR #86's `irq_pull_up`
TOML field, PR #87's `math_helpers` test gap) — not theorized in advance. Use it as a literal
checklist; the "Certification" list at the end (K.11) is the one to actually check off per
promotion. Where a step doesn't apply to a given driver (no interrupt pin, no shared-bus neighbour,
nothing datasheet-worthy), say so explicitly rather than silently skipping it — the same "flag,
don't silently change" instinct CLAUDE.md applies everywhere else.

## K.1 Before writing any code

1. **Read the datasheet first, not training memory** (CLAUDE.md's datasheets rule, Part A.6). Place
   the real PDF under `datasheets/<name>/` if it isn't there yet; every hardware-interaction claim
   in code comments cites a page number against it, same as every existing driver.
2. **Check Part G's shared-primitive catalog before writing anything new** — numeric validation/
   coercion, callback dispatch guarding, response envelopes, locked state, logging, the one shared
   EMA (`math_helpers.ema_step`, added for ISL29125 but not ISL29125-specific), and anything
   website-facing needs its `src/`↔`js/` mirror obligation honored too (Part G.3). Re-run the
   grep-for-the-shape check as part of this same pass.
3. **Find the closest existing driver and read it in full**, not just its shape. `asy_scd30_driver
   .py` (bare `SensorReader`, interrupt pin) and `asy_bmp3xx_driver.py` (`SensorReaderConfig`, no
   interrupt) are the two simplest precedents; `asy_isl29125_driver.py` is the fullest recent one
   (interrupt pin *and* `SensorReaderConfig` *and* a configurable internal pull-up *and* derived
   fields needing a shared-helpers extension) if the new driver is likely to need several of these
   at once.
4. **Decide the Part C.11 design questions** (bus, identity check, config location, derived fields,
   operating-range validation, trigger rate, FRAM persistence needs, errno/wrnno numbering) before
   writing the constructor — C.11 itself, not duplicated here.

## K.2 Write the driver, to the Part C/D bar

Layered shape (Part C.1–C.10), config schema (C.5), error/logging contract (C.7), concurrency model
(C.8), the full `src/` promotion checklist (Part D, all of D.0–D.15) — nothing in this Part changes
any of that. Two buildgen-era additions worth calling out because they're easy to miss reading Part
C/D alone:

- **Keyword-only past the required positional leaders.** Ruff's `FBT001`/`FBT002` (boolean-trap,
  live under this project's `select = ["ALL"]`) reject a `bool`-typed parameter that isn't
  keyword-only. Every existing bare-`bool` constructor parameter in `src/` already is (e.g.
  `asy_fram_driver.py`'s `wp`); a new one needs a `*,` separator before it (PR #86's own fix,
  found by `ruff check` after the fact rather than anticipated — run lint before assuming a new
  parameter's shape is fine).
- **A constructor parameter with a real "off"/"no-op" value needs that value to actually mean
  nothing changes, checked against the real underlying API, not assumed.** `irq_pull_up=False`
  constructs a bare `machine.Pin(id, mode=Pin.IN)` (omitting `pull=` entirely) rather than passing
  `pull=None` explicitly — this project's own `tests/machine.py`/`digital_twin/machine.py` fakes
  both type `pull` as a plain `int` with a `-1` sentinel, not `int | None`, so the real
  MicroPython-idiomatic `pull=None` would need both fakes' own signatures widened for no real
  benefit; matching SCD30's own existing no-pull construction style instead needed no fake changes
  at all. Check what the *existing* fakes already model before introducing a new value shape.

## K.3 Wire into `buildgen`

Every file below; a driver following the `asy_<name>_driver.py` → `*_Reader(SensorReader |
SensorReaderConfig)` naming convention (C.2) usually needs only the first three — confirm by
actually running `buildgen/generate.py` against a fixture TOML (or a real `devices/*.toml` with a
draft instance added), not by inspection alone.

1. **`buildgen/buildspec.py`** — the one hand-maintained per-driver table (its own docstring says
   so; every other buildgen table is AST-derived from `src/`). Add rows to
   `REQUIRED_TOML_FIELDS`/`OPTIONAL_TOML_FIELDS` (every constructor parameter with no default is
   required; every one with a default your device might want to override is optional — see PR #86
   for adding a single optional field to an already-promoted driver). If the driver sits on a bus,
   add it to `BUS_KIND_BY_DRIVER` too. **Check the datasheet for a real address-select pin before
   deciding `ADDRESS_CAPABLE_DRIVERS` vs. `FIXED_ADDRESS_DRIVERS`** — ISL29125's own datasheet
   states its address is hardwired with no select pin (FN8424 p15), which is why it lands in
   `FIXED_ADDRESS_DRIVERS` like SCD30/SGP40, not `ADDRESS_CAPABLE_DRIVERS` like BMP3xx; guessing
   this wrong lets a device TOML declare a meaningless `address` field that silently does nothing.
2. **`buildgen/driver_registry.py`** — usually **no change**: `resolve_driver()` AST-scans
   `asy_<name>_driver.py` for a `SensorReader`/`SensorReaderConfig` subclass automatically. Only
   add a `_OVERRIDES` entry if the driver genuinely can't follow that convention (today: `fram`,
   `neopixel`, `notification`, `uart_link` — none define a `SensorReader`/`SensorReaderConfig`
   subclass at all, or `uart_link`'s file isn't even `_driver.py`-shaped the same way). Confirm the
   auto-resolution path actually works rather than assuming — it did for ISL29125 with zero code
   here.
3. **`buildgen/codegen.py`** — a new `_build_args_<name>()` handler (closest existing shape:
   `_build_args_scd30` for a bare `SensorReader` with an interrupt pin, `_build_args_bmp3xx` for a
   `SensorReaderConfig` with none — `_build_args_isl29125` is the one driver combining both, a
   useful template if the new one does too), registered in `_BUILD_ARGS_HANDLERS`. Every optional
   TOML field gets emitted only `if "<field>" in f:`, matching every existing handler — never
   unconditionally, or a device that never set it gets a spurious explicit default in generated
   source.
4. **`buildgen/definitions.py`** — add the driver to `_SENSOR_DRIVERS` so the website-definitions
   generator scans its `@web`/`@web-group` tags (K.6 below) at all. Skipped, the driver silently
   never appears on the website with no error anywhere.
5. **`buildgen/twin_wiring.py`** — usually **no change**: `fram_target` and every other generic
   wiring field is handled uniformly by `codegen.py`'s own `_fram_kw()`/`ctx.wiring_expr()`, not
   per-driver here. Add a case only if the driver needs a *real interrupt/GPIO line the twin's chip
   fake has to drive edges on* (today: `scd30`, `isl29125` — see `compute_twin_wiring()`'s own
   `if spec.driver in ("scd30", "isl29125")` branch) or a genuinely novel cross-instance wiring
   shape (`uart_link`'s crossover-pair detection, `_compute_uart_wiring()`).
6. **`buildgen/pico_gpio.py`** — only if the driver needs a wholly new pin-role concept
   (`uart_link`'s `UART_ROLE` table, transcribed from the Pico W datasheet, is the only precedent
   so far). A plain interrupt/GPIO pin needs nothing here.

## K.4 `@web`/`@web-group` tags — the website comes from these, never hand-edited JSON

`html/definitions/<device>.json` is generated at build time from every tagged `src/` file (Part
H.5.1); it is never hand-maintained on this branch. Add `# @web-group`/`# @web <Field> ...` tags for
every field the website should show, in both the `measurements` and `sensors` sections as
applicable — `src/asy_bmp3xx_driver.py` (simple) and `src/asy_isl29125_driver.py` (uses `special:`
sentinel labels, `decimals` rounding hints, and `path="A.B"` for a value nested inside the
measurement body — the newest tag capabilities, added specifically because ISL29125 needed them,
Part H.5.1) are the two worked examples to copy from. If a bus prerequisite exists (a minimum I2C
bus timeout, say), add a `# @requires bus.<field><op><value>` tag too (C.2/SPECIFICATION.md Part L); if
a cross-instance reference exists beyond the generic `fram_target` shape, check whether `@wiring`/
`@value-wiring` already cover it before inventing a new tag family. Every tag family gets full
accept/reject grammar test coverage (`tests_scripts/test_buildgen_web_tag.py`,
`test_buildgen_requires_tag.py`, `test_buildgen_tag_comments.py` are the reference bar,
SPECIFICATION.md Part L's own standing rule) — extending a tag family's own grammar (like `path`/
`decimals`) needs new tests in that same file, not just new usages.

## K.5 Digital twin

A chip fake is **required, not optional**, the same session as promotion (C.11 item 9) —
`digital_twin/_<name>_chip.py`, wired into `digital_twin/machine.py`'s `_build_i2c_chip()`/
`_build_spi_chip()` dispatch (matched by `driver` string, reading whatever `buildgen.twin_wiring`
put in the attachment dict — K.3 item 5 above). If the chip's own datasheet has real
`# @requires`-worthy facts or interrupt-line electrical requirements (open-drain needing a pull-up,
active-low vs. active-high), model them in the fake too, not just the driver — ISL29125's own chip
fake needed the INT line to idle HIGH and the conversion timer to keep running through a range
switch, both found by writing real digital-twin tests against it, not by inspection. Add
`Pin.PULL_UP`/whatever other `machine`-fake constant the real driver now references to **both**
`tests/machine.py` and `digital_twin/machine.py` if it's the first driver needing it (ISL29125 was,
for `PULL_UP`).

## K.6 Tests, every tier — "biting," not just executing

**A dedicated unit-test file for the driver itself**
(`tests/test_asy_<name>_driver.py`, Part D.12's own bar): every parameter individually and in
combination, sanity-bounded typical values (not exact reference numbers unless independently
verifiable — see below), out-of-range on both sides of every bound, exact boundary values accepted,
`NaN`/`±inf` on every float argument, any formula-inherent quirk as a bounded regression.

**If the driver pulls in or extends a *shared* module** (Part G's own catalog, or `math_helpers`
specifically), **that module needs its own direct, dedicated tests too — exercising it only
incidentally through the new driver's own fixture values is not enough.** This is a real gap found
and fixed this session (PR #87): `math_helpers.py` gained five new functions for ISL29125 (colour-
space conversion, McCamy CCT, the shared EMA), and the promotion's own PR left `tests/
test_math_helpers.py` untouched — every other function there has its own suite, and these silently
didn't. Where possible, check new formula code against an independently-known reference value, not
just "returns not None" — PR #87's own `rgb_to_xyz(1,1,1)` → the D65 white point → chromaticity →
~6500K round-trip is the model: each step is a real, checkable number from outside this codebase,
not a self-referential assertion.

**Digital-twin test(s)** (`tests/test_digital_twin_<name>.py`, plus a dedicated behavior suite if
the driver has a real state machine worth its own file — ISL29125's autorange logic is the
precedent, `tests/test_digital_twin_<name>_autorange.py`-shaped). Follow "Driver/DUT process
separation" (Part E.9) for anything that drives requests against a running twin instance — host-side
against the real HTTP server, never sharing the twin process's own heap.

**`buildgen`-level tests** (`tests_scripts/`) — this is its own tier, easy to forget since it's
host-side pytest, not MicroPython:
- `test_buildgen_driver_registry.py` — confirm the new driver resolves (or, if it needed one,
  confirm the `_OVERRIDES` entry resolves correctly).
- `test_buildgen_generate.py` — the new `_build_args_<name>()` handler renders correctly with every
  optional field present, and correctly *omits* each one when absent from the TOML (PR #86's own
  `test_isl29125_irq_pull_up_false_is_rendered_into_the_constructor_call`/companion omission test
  is the exact shape).
- `test_buildgen_definitions.py` — the driver's `@web` tags produce the expected website-JSON
  shape.
- `test_buildgen_web_tag.py` — if a new tag capability was added (K.4), its own accept/reject
  coverage; otherwise, at minimum the real-driver field-name/group assertions every existing driver
  gets there.
- `test_device_tomls.py` — which real devices carry this driver (an explicit allow-list assertion,
  matching `test_isl29125_only_present_on_dev`'s own shape — never let a new instance land on a
  device by omission of a check).
- `tests_scripts/buildgen_fixtures/novel_combo.toml` — extend the synthetic multi-driver fixture so
  the driver is exercised there too, the same way `uart_link`/`isl29125` both were.

**Bus-hazard coverage, all four tiers, standing rule (CLAUDE.md, explicit — full detail in Part
C.8)** — same-device read/write concurrency, cross-device interleaving with every real neighbour on
a shared bus, and an address/command sweep:
- **Sensor-specific hazards are hand-written, from the datasheet, and live in the driver's own test
  file** (`tests/test_asy_<driver>_driver.py`), never in the cross-sensor collection — they encode a
  specific chip's own failure mode (ISL29125's destructive `0x08` status read; SCD30's finite NVM
  write budget) that no generic template could derive. Add the digital-twin/`tests_hardware/flash/`/
  `tests_hardware/bench/` equivalents too, following the shape of the driver's closest existing
  precedent there.
- **Cross-sensor hazard coverage is automatic for the generic scenario catalog, no longer
  hand-paired per driver.** Add the new driver to `tests/_bus_hazard_catalog.py`'s
  `I2C_HAZARD_CATALOG` (an adapter: construct/seed/read_once/exercise, plus write_once/general_call
  if it has a safe write or a real broadcast) and `tests/test_bus_hazard_generated.py` picks up
  every real bus this driver shares with another occupant automatically, on every real device TOML,
  with no further edits (C.8's own promotion checklist lists the full requirements). Only write a
  new **hand-written** cross-sensor test in `tests/test_bus_hazard_multi_device.py` for a scenario
  *shape* the generated scheme structurally can't produce (e.g. a rogue general call against a bus
  with no real broadcasting occupant) — that file is the permanent home for such shapes, not a
  fallback for drivers the generator hasn't reached yet.

## K.7 `devices/*.toml`

Add the `[[instance]]` block **only to the real devices that actually carry this hardware** —
`wozi` never gets a bench-only or not-yet-deployed-everywhere sensor just because `dev` does (C.f.
ISL29125: dev-only, `wozi` and the other four devices untouched). Wiring facts (bus, pin numbers,
any `irq_pull_up`-style board-specific override) must come from **real, bench-validated hardware**,
never invented — cite where the fact came from in a TOML comment (a prior hand-written
`sensortask_<device>.py`'s own construction comment, a real bench measurement, a datasheet page).
Placement within the `[[instance]]` list has FRAM-chunk-order consequences (bump-pointer allocator,
Part A.7) — no hard rule on where to put it beyond "after every earlier sensor whose chunk layout
shouldn't move," which usually just means "last." The TOML is now the only host-side copy of these
facts: `tests_hardware/bus_topology.py`, a hand-kept mirror that nothing imported and no tooling
cross-checked, was deleted (2026-09-18, BACKLOG item 20). Its one enforced invariant — no device
address inside an I2C-reserved range — moved to `tests_scripts/test_device_tomls.py`, where it runs
against the real device set rather than two hardcoded tuples. The on-target sweep
(`device_scripts/bus_topology_autodetect_and_hazard_sweep.py`) keeps its own address table, since it
is MicroPython on the board and cannot import host test code; it detects the live topology anyway,
so it does not need the wiring half at all.

## K.8 Regenerate and spot-check generated artifacts

`html/definitions/<device>.json` regenerates from K.4's tags automatically — actually regenerate it
and read the diff; a stale `mockdata/<device>.json` (a hand-written website-prototype fixture that
can predate the real driver, carrying placeholder field names that no longer match the real schema)
is a real, found-twice gap (PR #83's own ISL29125 fix) worth checking for explicitly, not just
assumed fine because nothing failed.

## K.9 Documentation

- **SPECIFICATION.md Part C** — new `C.11.x` subsections for any real, datasheet-derived design
  decisions or settled project-owner rulings worth recording permanently (the `C.11.1`–`C.11.5`
  ISL29125 subsections — the conformance-probe methodology, reference-layer traps, calibration
  model, range-ratio behavior, settled requirements list — are the shape to follow: real findings,
  with real evidence, not narrative). A `C.7.1` errno/wrnno table row if the driver claims a new
  range. Update C.8's per-device bus-sharing note if this driver changes which devices share a bus.
- **`DEVICE_REFERENCE.md`** — end-user-facing notes only (its own docstring: "not an AI-session or
  architecture doc"), so add an entry only if the new driver introduces a real user-configurable
  behavior worth explaining to someone operating a deployed unit — not a routine promotion step for
  most drivers.
- **`digital_twin/README.md`** — the new chip fake's own "What's here" entry, matching the doc's
  current section structure (don't clobber sections added since, e.g. PR #82's "Driver/DUT process
  separation").
- **`THIRD_PARTY_LICENSES.md`** — if the driver is adapted from third-party/vendor code (SPDX header
  + attribution, matching the file's existing entries).
- **BACKLOG.md** — only for a genuinely still-open question this promotion surfaced but didn't
  resolve (e.g. "no pytest gate wired for the new conformance-probe script yet" — PR #83's own
  disclosed, not-silently-resolved gap). Never process narrative (CLAUDE.md's pruning rule).

## K.10 Verification, before calling it done

- `scripts/lint.sh` (ruff, full scope + shellcheck + actionlint + zizmor) — clean.
- `scripts/typecheck.sh` (all three mypy passes: main, `digital_twin/`, host build chain) — clean.
- **Actually generate all six real device TOMLs** (`buildgen/generate.py` against each of
  `devices/*.toml`, or let `scripts/typecheck.sh`'s own generation step do it) and inspect the
  output for the device(s) that gained the new instance — confirm the constructor call, imports,
  and error/logger/task-starter fan-in all look right, don't infer correctness from tests alone.
- `scripts/test.sh` — the full MicroPython Unix-port suite plus `tests_scripts/` pytest, both
  clean.
- `scripts/run_digital_twin_ci.sh <device>` for every device that gained the new instance — this
  already runs the whole suite **twice**, once at `gc.threshold(-1)` and once at the shipped
  `gc.threshold(32768)` (`scripts/_digital_twin_ci_suite.py`'s own `main()`), per the standing
  memory-safety discipline (Part I.4) — zero `MemoryError`s under either pass is the bar, not just
  "the soak trend stayed in tolerance."
- If website files changed: the JS suite (`npm test`) clean too.

## K.11 Certification checklist

Check off per promotion; note explicitly (not silently) anywhere a step didn't apply:

- [ ] Datasheet in `datasheets/<name>/`; Part G catalog checked for reuse first
- [ ] Driver written to the Part C/D bar; keyword-only past required positionals; new "off" values
      checked against what the test fakes actually model
- [ ] `buildgen/buildspec.py` rows (required/optional fields, bus kind, address classification
      checked against the datasheet)
- [ ] `buildgen/driver_registry.py` — confirmed auto-resolves, or a deliberate `_OVERRIDES` entry
- [ ] `buildgen/codegen.py` — new `_build_args_<name>()`, registered, every optional field
      conditionally emitted
- [ ] `buildgen/definitions.py` — added to `_SENSOR_DRIVERS`
- [ ] `buildgen/twin_wiring.py` — special-cased only if a real interrupt line or novel wiring shape
      needs it; confirmed unneeded otherwise
- [ ] `@web`/`@web-group` (+ `@requires`/`@wiring` as needed) tags, with grammar tests if a tag
      capability was extended
- [ ] `digital_twin/_<name>_chip.py`, wired into `machine.py`'s dispatch
- [ ] Unit tests: functionality + resilience/error-path + biting boundary/NaN/inf coverage
- [ ] Any shared/`math_helpers`-style function this driver added has its **own** direct test suite,
      not just incidental coverage through the driver's fixtures
- [ ] Digital-twin tests (+ dedicated behavior suite if the driver has real internal state)
- [ ] `tests_scripts/test_buildgen_*.py` coverage (registry, codegen present/absent-field rendering,
      definitions, web_tag, device_tomls allow-list, `novel_combo.toml`)
- [ ] Bus-hazard, all four tiers: sensor-specific (hand-written) + cross-sensor (auto-generated if
      that capability has landed by the time you read this — check; hand-paired otherwise)
- [ ] `devices/*.toml` — only the real devices that carry this hardware, wiring facts cited to a
      real source (the only host-side copy there is; see K.7)
- [ ] `device_scripts/bus_topology_autodetect_and_hazard_sweep.py`'s `KNOWN_ADDRESSES` — the
      on-target table, which cannot import host code, so it needs the new address added by hand
- [ ] `html/definitions/*.json` regenerated and spot-checked; `mockdata/*.json` checked for stale
      placeholder fields
- [ ] SPECIFICATION.md Part C (+ C.7.1/C.8 if applicable), `DEVICE_REFERENCE.md`,
      `digital_twin/README.md`, `THIRD_PARTY_LICENSES.md` if applicable, BACKLOG.md only for
      genuinely open questions
- [ ] `scripts/lint.sh`/`scripts/typecheck.sh`/`scripts/test.sh` clean; all six device TOMLs
      actually generated and inspected; `scripts/run_digital_twin_ci.sh` clean at both
      `gc.threshold` values for every affected device
- [ ] Own branch off the current tracking branch, PR with a real description (not a file list),
      subscribed for CI/review activity, driven to green

---

# Part L — Build Chain: Device TOML Schema & the `buildgen` Generator

`src/`, the website (`html/`+`js/`), the build script chain and the test chain are fully
device-generic: every device-specific fact — hardware present, pin/bus assignments, included
software modules, how measurement values are shared between modules — lives in exactly one TOML
file per device variant, `devices/<device>.toml`, and everything else is derived from it at build
time. This Part is the durable specification of that scheme. Part K is the per-driver checklist for
working inside it; this Part is the mechanism itself.

## L.1 Device variants and the two standing acceptance criteria

**Six variants**, each with its own file even where two are byte-for-byte identical today:
`dev` (bench rig only — see CLAUDE.md's dev/wozi policy), `wozi` (the exemplary/base variant, never
physically flashed), `arzi` (distinct wiring from the "neu" family), and `klkizi`/`grkizi`/
`schlafzi` (the three "ArZi neu" units — currently identical hardware to each other, kept separate
because future hardware divergence is expected). `wozi`/`dev` are the only two carrying a `bmp3xx`
instance; every SCD30-carrying `i2c0` bus gets `timeout = 200000` of clock-stretch headroom.

Two criteria define the scheme and must keep holding — they are the thing a change to `buildgen/`
can most easily break without any test naming them:

1. **A new driver needs exactly one association**: its common name resolved to its class via the
   mandatory `asy_<name>_driver.py` naming convention. Schema, frozen-module inclusion, REST/config
   naming, website fields and wiring validation all follow automatically. True of every driver in
   `src/` today. **Named exception**: a genuinely new chip type still needs a hand-written
   digital-twin chip fake — inherently bespoke, and outside "the auto build" in the
   firmware/website-generation sense this criterion is about.
2. **A new hardware combination of already-known drivers needs exactly one new file**, the device's
   own TOML, with the full firmware+website build following automatically. Proven rather than
   assumed by two synthetic fixtures that exercise layouts none of the six real devices use:
   `tests_scripts/buildgen_fixtures/novel_combo.toml` (two `SCD30`s, `SGP40` taking temperature
   from one and humidity from the other, `BMP3xx` at the alternate address, `Notification` wired to
   only one `warn_*` signal) and `multi_instance.toml` (2× scd30 + 2× sgp40 at once, a
   cross-driver-type value reference, an explicit `{default = true, ...}` constant). Both run the
   full pipeline, including a real digital-twin boot.

**Real hardware flashing is out of scope for this scheme**, and the watchdog stays fixed
(hardcoded 8000 ms, uniform, never per-device).

## L.2 Core design decisions

- **Config format**: TOML, matching `toolchain/versions.toml`'s existing precedent.
- **Generation is build-time only; nothing generated is committed.**
  `build/<device>/{py,html,frozen,firmware}` is a single gitignored root and cleanup is
  `rm -rf build/`. CI regenerates and tests every variant, including a digital-twin boot, on every
  push. No static `src/sensortask_*.py` file exists: `scripts/_generate_sensortask_modules.py`
  generates all six devices' modules fresh into `build/generated_src/`, deliberately not into
  `src/`.
- **Naming**: `SensorStation<Name>` is the base stub — default hostname and website display
  identity. The hotspot AP's SSID is literally the `Hostname` config field's value; the hotspot
  password is a per-device TOML field defaulting to the existing hardcoded `"12345678"` (accepted
  risk, CLAUDE.md). Both reach the device as **defaults, not fixed values**: the generator passes
  them to `AsyConnTime(hostname=..., hotspot_password=...)`, which substitutes them into the two
  `ConfigManager`-persisted fields' schemas (`_with_default()`), so a rename through the web UI
  still wins on every later boot. Until 2026-09-18 nothing passed them at all and every device
  booted as the shared `"SensorNode"` whatever its TOML said. `[device].hostname` is capped at
  `network.hostname()`'s own 32 characters at build time, and `[device].hotspot_password` is held to
  WPA2-PSK's own 8-63, because a value outside either field's schema bounds is dropped back to that
  shared default at boot rather than failing - for the password, back to the one published in `src/`.
- **Cross-instance wiring is fully static, resolved at generation time, never at runtime.** There
  is no runtime registry or bus. Each driver declares a `# @wiring` comment tag naming which TOML
  field supplies a source instance and what class it must be (L.6); the generator resolves each
  reference to the actual constructed Python object and passes it into the consumer's constructor,
  so an instance either is the expected class or it isn't, checked directly.
- **Every real cross-instance link gets a TOML-visible `[instance.wiring]`/`[device.wiring]`
  field** — none stay hardcoded in `build_system()`. That covers
  `sgp40.temperature_source`/`.humidity_source` (per-value wiring, L.6),
  `notification.signal_sink`/`warn_co2`/`warn_voc`/`warn_hum`, `fram_target` on every driver or
  service taking an optional `fram=`/`fram_storage=` argument, and `device.wiring.led_target` for
  WiFi's `conn.set_ext_led(pixel)`. Each field is individually optional — absence disables that
  specific link. **Excluded** are links between two mandatory-infrastructure modules (both
  endpoints always exist unconditionally) and `WebserverService`'s
  `sensors=`/`settings=`/`maintenance_sensors=`/`is_hotspot_active=` arguments, which enumerate
  whichever instances the TOML already declares rather than naming one specific instance.
- **No getters and no callback functions in generated code.** A consumer holds a direct reference
  to the producer's existing concurrency-safe value holder (Part G's "locked state" primitive) and
  reads `.value` when needed. N-to-1 fan-in — error sources feeding `SystemService`,
  threshold-notifier sources feeding the Neopixel driver — collapses the same way: the aggregator
  holds a plain list of instances and reads each directly.
- **Two ordering hazards, both handled, neither by hand.** *Object existence*: a consumer's
  constructor call references the producer's Python object, so the producer must be constructed
  first — `buildgen.graph.build_construction_order()` topologically sorts instances by wiring
  dependency and rejects a cycle as a build-time error. *Live data availability*: independent async
  tasks mean a consumer's first read can precede the producer's first real measurement, so every
  producer's locked-value holder has a safe, defined initial value at construction and every
  consumer treats that "not yet measured" state as normal.
- **Instance naming**: every optional module takes an optional name-extension field defaulting to
  the empty string, and REST paths, config filenames and FRAM-backed error-log/errcount keys all
  incorporate it uniformly — `/sensors/scd30` by default, `/sensors/scd30_fan_pressure` when named.
  The generator errors on a naming collision when no disambiguating extension was given.
- **Bus/pin config**: every I2C/SPI bus pin, IRQ pin, CS pin, Neopixel pin and the like is defined
  in the device's TOML — no hardcoded pins anywhere in generated or hand-written driver-wiring
  code. An address field exists only for chips with a logically-selectable address; a
  hardwired-address chip gets no address field at all.
- **Frozen-module selection is dependency-driven**: the generator seeds from each device's declared
  driver list plus a fixed always-included core set, then takes the transitive closure of real
  `import`/`from ... import` statements, AST-scanned after `TYPE_CHECKING` stripping. Dynamic
  imports are disallowed project-wide, which is what makes the closure sound.
- **Testing**: generic driver/service logic is tested exactly once; only the device-specific slice
  (generated wiring module, generated website definitions, digital-twin boot of that config) runs
  once per device. Tests are generic bodies driven by each device's TOML and generated module,
  never hand-written or generated per-variant test files.
- **Build-time tooling gets a fundamentally different error-handling contract than the runtime code
  it emits** — detect every error that would make a build impossible and abort loudly rather than
  degrade. Full requirement: L.5.

## L.3 Device TOML schema

Two top-level shapes: a single `[device]` table (identity/network facts, plus mandatory-infra
tuning and wiring) and a uniform `[[instance]]` array of tables. **The `[[instance]]` array models
optional modules only** — driver-level sensors, plus the singleton services that vary or could
someday be absent per device: FRAM, Neopixel, NotificationCoordinator.

**WiFi, NTP and SystemService are mandatory infrastructure and are never `[[instance]]` entries** —
every buildable device has all three unconditionally. Their per-device-tunable knobs (WiFi's
`conn_fail_to_hotspot`/`hotspot_time_min`; NTP and SystemService have none) live directly in
`[device]`, **required, not defaulted**: a device TOML missing either is a build-time error. Their
crosslinks to optional instances live in `[device.wiring]` (`led_target`/`fram_target`, both
optional). The webserver is likewise unconditional and never modeled as an instance — its
constructor takes no independent per-device facts, only references to whichever other instances the
TOML already declares.

```toml
# example-device.toml - illustrative shape only; the 6 real files are devices/*.toml.

[device]
name = "Wozi"                              # feeds hostname = "SensorStation<name>"
hostname = "SensorStationWozi"             # also the hotspot AP's own SSID
hotspot_password = "12345678"              # accepted-risk default (CLAUDE.md)
conn_fail_to_hotspot = 5                   # mandatory-infra tuning, required
hotspot_time_min = 8

[device.wiring]
led_target = "neopixel"                    # optional; WiFi status LED
fram_target = "fram"                       # optional; SystemService's own error log

[bus.i2c0]
scl_pin = 13
sda_pin = 12
frequency = 50000
timeout = 200000                           # SCD30 clock-stretch headroom

[bus.i2c1]
scl_pin = 19
sda_pin = 18
frequency = 50000

[bus.spi0]
sck_pin = 2
mosi_pin = 3
miso_pin = 4

# --- sensor drivers (SensorReader/SensorReaderConfig subclasses - can repeat) -------------------

[[instance]]
driver = "scd30"                           # resolved to its class via naming convention, not a
name_ext = ""                              # lookup table (SPECIFICATION.md Part C.5)
bus = "i2c0"
irq_pin = 8
trigger_sec = 3

[instance.wiring]
fram_target = "fram"                       # optional

[[instance]]
driver = "sgp40"
name_ext = ""
bus = "i2c1"

[instance.wiring]
fram_target = "fram"                       # optional

# Per-value measurement wiring (Part L.6), each independently required (or explicitly
# defaulted via {default = true, ...}).
[instance.wiring.temperature_source]
source = "scd30"
field = "Temp"

[instance.wiring.humidity_source]
source = "scd30"
field = "Hum"

[[instance]]
driver = "bmp3xx"
name_ext = ""
bus = "i2c1"
address = 0x77                             # only chips with a real address-select pin get this

[instance.wiring]
fram_target = "fram"

# A second SCD30 on a different bus - name_ext disambiguates every derived name at once.
[[instance]]
driver = "scd30"
name_ext = "fan_pressure"
bus = "i2c1"
irq_pin = 9
trigger_sec = 3

# --- optional singleton services -----------------------------------------------------------------

[[instance]]
driver = "fram"
bus = "spi0"
cs_pin = 1
max_size = 0x2000                          # per-chip fact, varies per device

[[instance]]
driver = "neopixel"
pin = 15

[instance.wiring]
fram_target = "fram"

[[instance]]
driver = "notification"

[instance.wiring]
signal_sink = "neopixel"                   # required; defaultable, see Part L.6
fram_target = "fram"

# Per-signal getters - each optional; absence disables that specific warning signal.
[instance.wiring.warn_co2]
source = "scd30"
field = "CO2"

[instance.wiring.warn_voc]
source = "sgp40"
field = "VOC"

[instance.wiring.warn_hum]
source = "scd30"
field = "Hum"
```

**`_WIRING`'s shape** (a `# @wiring` comment tag, not a Python tuple — L.6):
`(toml_field_name, required_driver_class, target, required, mode)`, where `mode`
(`"kwarg"`/`"attr"`/`"setter"`) says how the resolved producer reaches the consumer. `signal_sink`
uses `mode="attr"`: the generator resolves it to `pixel.request_signal` — the bound method
`NotificationCoordinator.__init__`'s `request_signal_cb` parameter wants — not the `NeopixelDriver`
instance itself. `led_target` uses `mode="setter"`: `conn.set_ext_led(pixel)` is emitted once, after
both objects already exist.

**Wiring identity**: a wiring reference (`temperature_source`, `signal_sink`, `fram_target`,
`led_target`, every `[instance.wiring.<name>]`/`[device.wiring]` field) resolves against the TOML's
own `driver`+`name_ext` identity — **never** against `instance_name()`/each driver's own `_NAME`
constant, which is a different naming space serving REST/config-key identity. The concrete case a
naive implementation silently fails on: `asy_notification_service.py`'s `_NAME` is `"NOTIFY"`, not
`"NOTIFICATION"`.

`tests_scripts/test_device_tomls.py` is a minimal shape/collision smoke-test suite run directly
against the six real files, independent of `buildgen`'s own validator.

## L.4 The generator pipeline (`buildgen/`)

`buildgen/` is a real top-level CPython package, never imported by `src/`. It parses TOML via the
real stdlib `tomllib` and walks driver source via the real stdlib `ast`, which is why it goes
through `host_typecheck.ini`'s own mypy pass rather than the MicroPython-stubbed main one.

`buildgen.generate.generate_device(toml_path, src_dir, ext_dir)` runs the full pipeline —
`buildgen.validate.build_model()` → `buildgen.graph.build_construction_order()` →
`buildgen.codegen.generate_module_source()`/`generate_boot_entry_source()` — and returns the
generated module and boot-entry source, plus `buildgen.frozen_modules.compute_frozen_modules()`'s
module set. There is no separate `boot_entry/` directory: the generic boot entry is generated too.

- **`driver` → class**: `buildgen.driver_registry.resolve_driver()` AST-parses (never imports)
  `asy_<name>_driver.py` for a `SensorReader`/`SensorReaderConfig` subclass. An `_OVERRIDES` table
  covers the drivers that genuinely cannot follow that convention — `fram`/`neopixel`/
  `notification` (singleton services) and `uart_link` (not a singleton; a device wires exactly one
  initiator plus one responder).
- **Validation**: `buildgen.validate.build_model()` — schema shape, global GPIO exclusivity,
  per-bus address exclusivity, instance-name/instance-label collision, bus-id collision, and every
  wiring-reference and required-field check. Full coverage list in L.6; every failure is a
  `buildgen.errors.BuildError` naming the device, instance and field responsible.
- **Notification signal catalog**: each signal's threshold default/range and flash colour is a
  fixed, generator-owned catalog (`buildgen.codegen._KNOWN_SIGNALS`). Every real device uses
  identical values, and the schema has no per-device override for them today.
- **Website `definitions.json`**: `buildgen.definitions.generate_definitions(model, src_dir)` takes
  an already-validated `DeviceModel`, scans each relevant instance's and mandatory-infra file's
  `# @web`/`# @web-group` tags (`buildgen/web_tag.py`) and assembles the full
  `definitions.json`-shaped dict, keyed by each instance's own `resolved_name` so a multi-instance
  device gets distinct, correctly-labelled cards. `buildgen/schema_ast.py` AST-evaluates a driver's
  real `ConfigSchema`/`FieldSchema` constants so a tag only has to supply what the schema tuple
  structurally cannot: label, unit, description, an explicit `kind=` override, `special:` labels.
  Fixed, non-driver-schema UI facts (`SystemCmd`/`PauseTime`/`lightCmdLED`/`ResetErrors`, the
  Status section's live-readonly field lists, the six-REST-endpoint section skeleton) are
  generator-owned catalogs in `buildgen/definitions.py`, the same precedent `_KNOWN_SIGNALS` sets.
  Full grammar and architecture: Part H.5.1.
- **Digital-twin wiring**: `buildgen.twin_wiring.compute_twin_wiring(model)` walks the model and
  emits the twin's own per-attachment wiring facts. Two facts a `DeviceModel` structurally cannot
  carry get a small, explicit twin-side exception table: scd30/sgp40's fixed hardware address
  (`FIXED_ADDRESSES`, matching `src/`'s own hardcoded defaults) and FRAM's real RDID reply bytes
  (`digital_twin/machine.py`'s `_FRAM_RDID_BY_MAX_SIZE`, keyed by size as the best available
  proxy). `digital_twin/machine.py`'s `configure_wiring(plan)` is the generic entry point;
  `configure_i2c_wiring("wozi"|"dev")` is sugar over it, lazily loading
  `build/generated_src/sensortask_<profile>_wiring_plan.json`, since that module runs under the
  MicroPython Unix port, which has no `tomllib` and so cannot call `buildgen` directly at runtime.
  No hand-typed wiring literal exists anywhere.
- **Booting a generated device**: `digital_twin/run_generic_integration.py` boots any
  `sensortask_<device>` module against a `--wiring-plan` JSON file, resolving it via
  `__import__(--module)`. `tests_scripts/test_digital_twin_generated_boot.py` generates a device,
  writes its module source and wiring plan to a temp dir, spawns the real MicroPython Unix-port
  binary and asserts a real `GET` against five REST endpoints returns 200 — for all six real
  devices plus both synthetic fixtures. That is the point at which a generated module is proven to
  boot and serve, rather than merely to parse.
- **Known twin limitation**: `machine.py`'s single-chip SCD30/FRAM globals only persist the
  *last-wired* instance's NVM state across a simulated reboot on a multi-instance device — see
  `digital_twin/README.md`'s "SCD30 persistence" section.

`.github/workflows/ci.yml`'s `firmware-build-verify` and `digital-twin-e2e` both run a real
`strategy.matrix` over all six devices with `fail-fast: false`.

## L.5 Build/generator script quality bar

Binds every piece of build/generation logic — `buildgen/`'s validator and generator, the website
`definitions.json` generator, and the CI orchestration around them. It is deliberately distinct
from the sensor-code bar in Part D: a build script's job includes catching every way its own input
could be wrong and refusing to proceed, rather than degrading.

- **Detect and react to every error class that would make a real build impossible** —
  misconfigured or malformed TOML, an unresolved wiring reference, a driver-class/type mismatch, a
  REST/config-name collision with no disambiguating extension, a missing required pin/bus field, a
  missing or incomplete mandatory-infra field in `[device]` (required, not defaulted), a copy-paste
  duplicate, or any other structurally broken definitions file.
- **Global-resource-collision checks are their own error class and must not be skipped.**
  Overlapping bus addresses, double-claimed pin numbers and any other double-definition of a
  resource meant to be exclusive are *individually valid-looking fields that are still wrong in the
  whole-file view*, catchable only by a cross-instance pass over the entire device:
  - **Schema shape**: each bus (`i2c0`/`i2c1`/`spi0`-style) is its own top-level entry owning its
    shared wire pins, separate from each instance's *exclusive* resources (address, CS pin, IRQ
    pin).
  - **Global GPIO-pin exclusivity**: one flat namespace across the whole device — every bus's wire
    pins, every instance's CS/IRQ/standalone-peripheral pin. A physical pin wired to two different
    signals is always an error.
  - **Per-bus address exclusivity**: scoped, not global. Two instances on the *same* bus cannot
    share an address; the same address on two *different* buses is legitimate. Covers both an
    explicit `address` clash and two hardwired-address instances of the same chip type sharing a
    bus with no way to distinguish them at all.
  - **Instance identity collision**: two instances resolving to the same `instance_name()` (the
    REST/config-key identity) *or* the same `instance_label()` (the generated Python variable name,
    `driver`+`name_ext`) — two independent naming spaces, each with its own dedicated check.
  - **Any other single-owner resource claimed twice** — a bus id defined more than once, or a
    wiring field naming an instance that does not exist or is the wrong driver type.

  Every one of these must produce a specific, human-readable error naming the two colliding
  declarations — never a generic "build failed", and never a silent pick of one over the other.
- **A wiring reference resolves against the TOML's own `driver`+`name_ext` identity**, never
  against `instance_name()`/each driver's own `_NAME` constant. L.3 has the full reasoning and the
  concrete `"NOTIFY"`-vs-`"NOTIFICATION"` case a naive implementation silently fails to resolve.
- **Driver-declared bus requirements are enforced via a `# @requires` comment tag, never a real
  Python variable** — nothing the running firmware itself reads should become a real
  frozen-bytecode value just to serve this generator. Grammar: `# @requires bus.<field><op><value>`
  (e.g. `# @requires bus.timeout>=200000`), placed at module level near the driver's other tags.
  The generator parses driver source files as text for these tags (never imports and introspects),
  resolves the instance's `bus = "..."` reference to its `[bus.*]` table, and evaluates the
  predicate against that table's actual field value — failing loudly, naming device, instance, bus,
  field and expected-versus-actual value, if it is not satisfied.
- **Every driver-declared fact the running firmware never reads is a comment tag, not a Python
  value** (project owner's ruling, 2026-09-10) — uniformly for `# @wiring`, `# @value-wiring` and
  `# @limits` alike (L.6 has each grammar and rationale). The one exception is a `_Default<Field>`
  class, which is live code the generated module actually constructs, not metadata, so it stays
  real Python.
- **Standing rule for every tag in this comment-tag family: a tag that is present, or close to
  present with a typo, must be verified correct in every dimension — exact wording, location,
  format, content, validity — or fail the build loud, never be silently treated as "no tag here."**
  `buildgen/tag_comments.py` is the shared mechanism (a `KNOWN_TAG_NAMES` registry, tokenize-based
  comment scanning, edit-distance typo matching, and a payload-shape gate so ordinary prose
  mentioning a tag's name is not misflagged); every family
  (`@requires`/`@wiring`/`@value-wiring`/`@limits`/`@web`/`@web-group`) is built on it, never on a
  second, less-tested detector. Each family's unit tests must cover the whole matrix: **the accept
  side needs full dimensionality** (every operator against every value shape, every legal
  spacing/placement variant), **the reject side covers each dimension once without recombining**
  (wording typos including the edit-distance boundary that must stay silent; format — each
  structural piece individually wrong or dropped; location — indented into a body, or onto a
  continuation line; content; validity against a real bus table; scanning — tag-shaped text inside
  a string or docstring, an unparseable file), plus the false-positive checks that make the
  mechanism trustworthy (realistic prose merely mentioning the tag's name, an unrelated `@`-word).
  `tests_scripts/test_buildgen_tag_comments.py` and `test_buildgen_requires_tag.py` are the
  reference implementation of this bar. It was motivated by a real incident: a driver signature
  change once silently broke two `tests_hardware/device_scripts/` call sites for a full day,
  undetected because nothing in that scope was checked at all. A malformed comment tag silently
  parsing to "no tag declared" is the same class of risk one layer down.
- **Never produce a corrupted or partial build.** On any detected error, abort the entire build
  immediately — no partial `build/<device>/` output left behind that could be mistaken for a real
  artifact.
- **Fail loudly, clearly and human-readably.** A plain, actionable message naming exactly what is
  wrong and where (which device, which instance, which field) — not a raw traceback, not a silent
  wrong-default fallback. This is the build-tooling equivalent of CLAUDE.md's "flag, don't silently
  change" convention.
- **Tested to the same bar as `src/` code**: correct-path functioning, full error-handling-path
  coverage (every abort condition gets its own test, driven by deliberately malformed fixture
  definition files — never just incidentally exercised by the six real device TOMLs happening to be
  valid), and code coverage. Follows the established `tests_scripts/` convention (pytest, real
  CPython) rather than inventing a new test harness. This is the same "each module/function tested
  exactly one time" CI principle applied to error-handling paths specifically: a generator
  function's abort conditions are themselves testable units.
- Newly-built generator/validator modules join `pyproject.toml`'s ruff/mypy scope alongside
  `src/`/`tests/`/`digital_twin/` from day one.

## L.6 Wiring defaults, per-value wiring, comment tags and pin legality

Every mechanism in this section is shipped, tested code (`buildgen/`, plus `src/asy_sgp40_driver.py`'s
and `asy_notification_service.py`'s `_Default*` providers).

### L.6.1 Why wiring defaults exist

Two `# @wiring` fields have no real Python-level fallback in their consumer's own constructor and
would otherwise fail a build whenever the wired hardware genuinely is not present:
`asy_sgp40_driver.py`'s compensation sources (an SGP40 with no live temperature/humidity producer)
and `asy_notification_service.py`'s `signal_sink` (no Neopixel to blink). Both are real, intentional
device shapes rather than configuration errors, so the fix is a TOML-authored fallback the driver
constructs itself — never a relaxed validator.

### L.6.2 The wiring-defaults mechanism

- **Opt-in, never implicit**: a wiring field is never silently defaulted just because it is absent
  from `[instance.wiring]`. The TOML author writes `{default = true, ...}` explicitly.
- **Uniform shape** for every defaultable field, whether or not it carries a constant
  (`signal_sink = {default = true}`; `humidity_source = {default = true, relative_humidity = 35}`).
- **Naming convention**: `_Default<ToMLFieldInPascalCase>` (`humidity_source` →
  `_DefaultHumiditySource`), defined in the same driver module as its real producer class.
- **Discovery**: `buildgen/defaults.py` AST-parses the `_Default<Field>` class's own `__init__`
  signature — param names and which have a Python default. That signature *is* the schema for the
  sub-table's allowed and required keys, never hand-duplicated in `buildgen/buildspec.py`.
- **Generated code**: the default provider is constructed inline, at the exact call site the real
  wiring expression would occupy (e.g.
  `SGP40_Reader(i2c1, _DefaultTemperatureSource(temperature=25), ...)`). It contributes no
  construction-order edge in `buildgen/graph.py` — there is no producer instance to depend on, the
  same treatment an absent optional field already gets.

### L.6.3 Per-value measurement wiring

The mechanism is **per-value**, not per-producer: every individual measurement value a consumer
needs is independently wireable via `{source, field}` (mirroring `asy_notification_service.py`'s
pre-existing `warn_*` shape), resolved at build time by checking that `source`'s `get_data()` result
exposes an attribute named `field` — a structural check, not a fixed `producer_class` match. A
future driver exposing a matching field name becomes wireable with zero `buildgen` changes.

Real fields today are `asy_sgp40_driver.py`'s `temperature_source`/`humidity_source`, each
independently resolvable to any instance exposing a `Temp`/`Hum`-named attribute (`scd30` or
`bmp3xx`) or defaulted via `_DefaultTemperatureSource`/`_DefaultHumiditySource` — both
self-contained, with no cross-module import, so a device with `sgp40` but no `scd30` never pulls
`asy_scd30_driver` into its frozen-module set just because of this. `SGP40_Reader.__init__` takes
four parameters (`temperature_source`, `temperature_field`, `humidity_source`, `humidity_field`),
each pair resolved independently in `_read_sgp()` via
`getattr(await source.get_data(), field_name)`.

Name-matching is the whole mechanism — there is no separate property or unit tag system. A producer
naming the same physical quantity differently (`"Temperature"` instead of `"Temp"`) simply is not
recognised as interchangeable until its field is renamed to match.

### L.6.4 The comment-tag family

`_WIRING`, `_VALUE_WIRING` and `_LIMITS` are all `#`-comment tags rather than real tuples, for the
reason L.5 states. Measured saving from that conversion plus the `_Default*` `TYPE_CHECKING`
aliases: ~3,576 bytes, about 2.6 % of `src/`'s frozen bytecode.

| Tag | Grammar | Parser |
|---|---|---|
| `# @wiring` | `<toml_field> <ProducerClass> <target> <required\|optional> <kwarg\|attr\|setter>` | `buildgen/wiring.py` |
| `# @value-wiring` | `<toml_field> <source_kwarg> <field_kwarg> <required\|optional>` | `buildgen/value_wiring.py` |
| `# @limits` | `<field> <min>..<max>` or `<field> in {a, b, ...}` (`*` on either side of a range = unchecked that side; `min == max` = exact value) | `buildgen/limits.py` |
| `# @requires` | `bus.<field><op><value>` | `buildgen/requires_tag.py` |

Every family shares `buildgen/tag_comments.py`'s scanner: tokenize-based, so a `#` inside a string
or docstring is never mistaken for a real comment, and a near-miss or typo'd attempt at a known tag
name (wrong sigil, wrong operator, dropped piece, wrong location) fails the build loud rather than
reading silently as "no tag here" — see `check_for_near_miss_tags()` and L.5's standing rule.

Real declarations today: `asy_scd30_driver.py`/`asy_sgp40_driver.py`'s
`# @requires bus.timeout>=200000`/`bus.frequency<=100000` and `bus.frequency<=400000` respectively
(`bmp3xx` is deliberately untagged — its datasheet supports every I2C mode); every optional-instance
driver's `fram_target` (`kwarg`, optional); `signal_sink` (`attr`, required, target
`request_signal`); `led_target` (`setter` on `conn`, target `set_ext_led`);
`asy_sgp40_driver.py`'s `temperature_source`/`humidity_source` (L.6.3); and
`asy_bmp3xx_driver.py`'s `_LIMITS` (`address in {0x76, 0x77}`, `trigger_sec 1..3600`) — the only
driver with a real, datasheet-documented `_LIMITS` constraint today. Every other candidate field
was checked directly against its own module and has no equivalent documented domain to draw from,
so none was invented.

### L.6.5 Pico W GPIO and bus-pin legality

`buildgen/pico_gpio.py` hardcodes the Pico W's real, fixed GPIO→peripheral table — this project
targets the Pico W alone, so there is no board parameterization — transcribed from
`datasheets/pico w/RP-008312-DS-2-pico-w-datasheet.pdf` Figure 2 (p.4):

- **I2C**: SDA/SCL pairs alternate I2C0/I2C1 every 2 GPIOs (GP0/1→I2C0, GP2/3→I2C1, … GP26/27→I2C1),
  even GPIO = SDA, odd = SCL within each pair.
- **SPI**: 4-GPIO blocks with fixed MISO/CSn/SCK/MOSI roles at offsets 0–3, alternating SPI0/SPI1
  by block (GP0–3 and GP4–7 both SPI0, GP8–11 and GP12–15 both SPI1, GP16–19 SPI0 again).
  `asy_spi_driver.py` needs only `sck_pin`/`mosi_pin`/`miso_pin` — CS is a separate,
  instance-exclusive `cs_pin` — drawn from any GPIOs sharing the same peripheral index, not
  necessarily the same 4-GPIO block.
- **GP22/GP28** have no I2C or SPI function at all. **GP23–25/29** are reserved for the wireless
  interface and never exposed on the header (confirmed against the datasheet's own pin count and
  its wireless-interface section). Any GPIO ≥ 30, or negative, does not exist.

`buildgen/validate.py`'s `_check_gpio_collisions()` checks every claimed pin device-wide — bus wire
pins and instance-exclusive `cs_pin`/`irq_pin`/`pin` alike — for real existence and non-reserved
status, and additionally checks each bus's own wire pins against their required peripheral index
*and role* (SDA vs. SCL, MISO vs. SCK vs. MOSI — a transposed pair is exactly as wrong as an
out-of-range one). `_bus_kind()` validates that a bus id's port suffix is a real index
(`i2c0`/`i2c1`/`spi0`/`spi1`), not merely that the prefix matches.

### L.6.6 Validation coverage (`buildgen/validate.py`)

Every check raises `buildgen.errors.BuildError` naming the device, instance and field responsible —
never a generic failure, a raw traceback or a silent partial build (L.5). Covered: malformed,
missing, unexpected and misformatted fields at every level (`[device]`, `[bus.*]`, `[[instance]]`,
`[instance.wiring]`, `[device.wiring]`); global GPIO-pin exclusivity and per-bus address
exclusivity, including two hardwired-address instances of the same driver sharing a bus with no
`address` field; the two independent identity-collision checks — `resolved_name` (the
REST/config-key identity, from each driver's `_NAME` constant) and `instance_label` (the generated
Python variable name, from `driver`+`name_ext`), structurally different naming spaces; that a
wiring reference resolves against `driver`+`name_ext` and never against `resolved_name`; pin
legality and role (L.6.5); driver-declared value domains (`_LIMITS`, L.6.4); and driver-onboarding
registration — a driver that resolves via `driver_registry.resolve_driver()` but has no
`buildgen/buildspec.py` entry raises its own dedicated error naming that as the cause, rather than
reporting every one of its TOML fields as unrecognised.

**Known limitation**: `buildgen/buildspec.py`'s per-driver TOML-field schema
(`REQUIRED_TOML_FIELDS`/`ALLOWED_INSTANCE_FIELDS`/`ADDRESS_CAPABLE_DRIVERS`/
`FIXED_ADDRESS_DRIVERS`) is still hand-maintained — the one association `buildgen` needs from a
driver that is not AST-derivable from `_WIRING`/`_VALUE_WIRING`/`_LIMITS`/`_Default*` alone, since
the TOML field names and `src/`'s constructor parameter names are two independently-evolved naming
spaces. BACKLOG.md's "Deferred" section has the full account of why making it AST-derivable is a
separate unit of work rather than a mechanical continuation.

## L.7 Product versioning (firmware and website)

Firmware and website carry **independent** version constants, both starting at `"2.0b0"`, so a
website-only fix can bump one without forcing an unrelated firmware rebuild. `GET /system` gains
one nested, never-flattened `"build"` sub-entry — `{"firmwareVersion", "websiteVersion",
"buildDate"}` — supplied through `WebserverService.__init__`'s
`build_info: dict[str, Any] | None = None` parameter and merged into `_get_system()`'s result after
`_get_settings_flat()` runs, never through `SettingsGroup`, which would flatten it. The website
version also appears independently as a top-level `websiteVersion` key in `definitions.json`: build
provenance for the bundle currently rendering, as distinct from the device's own last-built
firmware. Never conflate the two.

Neither version nor the build date is rendered in the UI — the Status page's design intent is
*live* device state, and neither version fact has a live-data question to answer.

**Single source of truth: `buildgen/version.py`** (`FIRMWARE_VERSION`, `WEBSITE_VERSION`,
`current_build_date()`) — deliberately not a device TOML field (a per-build fact, not a per-device
one), not `toolchain/versions.toml` (which pins external dependency versions, a different kind of
"version"), and not a `pyproject.toml` field (the shipped product is never `pip`-versioned). No
bump mechanism exists: one clear, documented place to change the two constants, no automation,
matching `toolchain/versions.toml`'s own precedent.
