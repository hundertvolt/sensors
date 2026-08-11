# Wiring Contract — `improved-quality/sensortask-wozi.py` study

**Status update (Step 1 landed)**: this doc's own original header said it would be deleted once the
real Stage-1 standalone `sensortask-wozi.py` successor landed — that's now true, `src/sensortask_wozi.py`
exists (Step 1 of `FINAL_WIRING_PLAN.md`'s five-step effort). Kept alive anyway, deliberately
deviating from that stated lifecycle: Steps 2-5 still need this exact construction order/dependency
graph preserved as they build on top of it (Step 2's registration API, in particular, needs the
construction order below to stay unchanged), so this remains the living reference until the whole
five-step effort merges back, not just until Step 1 alone lands. Still **keep it up to date**
whenever a change to `src/sensortask_wozi.py` touches anything documented below.

Historical note: this doc started as a pre-Step-1 study of `improved-quality/sensortask-wozi.py`'s
own flat, synchronous construction sequence (kept below, still accurate as a description of that
reference file, which stays unedited) — the sections below now describe `src/sensortask_wozi.py`'s
actual, current, async-safe equivalent.

## Why instantiation order matters

`AsyFramManager` is a bump-pointer allocator (see CLAUDE.md) — `get_chunk()`/
`get_timestamped_chunk()` carve out fixed offsets in call order, so a device's *instantiation
order* of these calls is its on-chip layout and must stay identical across firmware versions for
existing stored data to keep decoding correctly. See `SPECIFICATION.md` Part A.4's "FRAM chunk
determinism rule" for the full standing check.

## Current construction order (`src/sensortask_wozi.py`'s `build_system()`, top to bottom)

Same relative construction order as the reference file (below), inside an `async def
build_system(*, cfg_path="", debug=False)` instead of bare module-level statements — required for
testability (a bare top-level blocking call, matching the reference file's own bottom-of-file
`asyncio.run(main())`, would hang on plain `import`; see `src/sensortask_wozi.py`'s own docstring
and `FINAL_WIRING_PLAN.md`'s Step 1 refined plan for the full reasoning and the resulting two-file
split with `boot_entry/wozi_boot.py`). No `app = Microdot()`/routes/`import frozen_html` — deliberately
excluded from Step 1 (Step 2/Step 4's job respectively, owner-confirmed).

1. `watchdog = WDT(timeout=8000)` — hardcoded at construction time, no injection point (owner:
   "must be hardcoded so no error ever can circumvent it")
2. `conn = AsyConnTime(...)` — owns `DNSServer` internally (`captive_dns.py`)
3. `ntp = AsyNtpClient(conn.get_wifi_mode_lock(), conn.network_available, conn.get_dns_server_ip, ...)`
   — takes bound methods off `conn`, not a direct import-time reference
4. `i2c0`, `i2c1` = `asy_i2c_driver.I2C(...)` ×2
5. `spi0` = `asy_spi_driver.SPI(...)`
6. `fram = AsyFramManager(spi0, 1, max_size=0x2000, ...)` — **first real FRAM-chunk consumer of
   itself is none; it constructs `FRAM_SPI` internally with a shared `logger=`**
7. `sysfunct = SystemService(ntp.ntp_issynced, watchdog=watchdog, fram=fram, ...)` — **FRAM chunk 1**
8. `sgp_reader = SGP40_Reader(i2c1, sgp_comp_callback, fram_storage=fram, fram_ntp_callback=ntp.ntp_issynced, ...)`
   — **FRAM chunks 2 and 3**, allocated in this fixed sub-order within `SGP40_Reader.__init__`
   itself, confirmed directly against `src/asy_sgp40_driver.py`: `fram_storage` is forwarded as
   `fram=fram_storage` into `super().__init__()` (line 72), so `SGP40_Reader`'s own `self.pr` is
   already FRAM-backed (chunk 2, via `make_logger()` → `PrintLogHistoryStore.__init__()`'s
   `fram.get_chunk()`) — the same `fram_storage` argument does double duty. Chunk 3 is the VOC
   backup itself (`self.ts_storage = fram_storage.get_timestamped_chunk(...)`, a few lines later
   in `__init__`). Both are unconditional as long as `fram_storage`/`fram_ntp_callback` are non-
   `None`, which they always are in the real wiring — deterministic, matches the rule.
9. `bmp_reader = BMP3xx_Reader(i2c1, ...)` — no `fram=` passed, in-memory logging only
10. `scd_reader = SCD30_Reader(i2c0, 8, trigger_sec=3, ...)` — no `fram=`, no config schema at all
    (params live on-sensor, see CLAUDE.md)
11. `pixel = NeopixelDriver(15, fram=fram, ...)` — **FRAM chunk 4**
12. `notify_service = NotificationCoordinator(pixel.request_signal, ntp.cettime, fram=fram, ...)`,
    staged registration (`register()` ×3 for `WarnCO2`/`WarnVOC`/`WarnHum`, then `finalize()`
    exactly once — the single point `notify_service.pr`/`notify_service.cfgmgr` actually come into
    existence) — **FRAM chunk 5**
13. `conn.set_ext_led(pixel)` — wires the WiFi-status LED callback after both exist
14. **Grouped `await x.setup()` batch** (new in Step 1, resolved by dependency-domain analysis, not
    interleaved with construction above): `await fram.setup()` → `await sgp_reader.setup()` →
    `await bmp_reader.setup()` → `await notify_service.setup()`. These are two independent
    readiness domains (`fram.setup()` is FRAM-hardware/SPI readiness; the other three are each
    module's own local-JSON-config `ConfigManager.setup()`, unrelated to FRAM or each other), so
    there's no ordering requirement *between* them — grouping is correct rather than merely tidy
    because of one real constraint: `notify_service.setup()` is only valid to call after
    `finalize()` (step 12) has run (`asy_notification_service.py`'s own documented contract,
    `self.cfgmgr` doesn't exist before then), and batching at the end automatically satisfies that
    for every module, not just `notify_service`. `fram` keeps its first position, matching the
    reference file's own existing `async_onetime` list; the three new calls are appended in their
    own construction order.

**Real FRAM chunk order**: `SystemService` → `SGP40_Reader` (its own error log, chunk 2) →
`SGP40_Reader` (VOC backup, chunk 3) → `NeopixelDriver` → `NotificationCoordinator`. Five chunks
total, not four — corrected from this doc's earlier count once `SGP40_Reader`'s own logger was
confirmed to already be FRAM-backed (see item 8 above). Must stay in this relative order in any
future change, regardless of byte offset (which doesn't matter per the determinism rule).

**Task/timer starter collection** (`src/sensortask_wozi.py`'s `_collect_task_starters()`/
`_collect_timer_starters()`, called from `main()`, never from `build_system()` itself): every
constructed module's own `get_task_starters()`/`get_timer_starters()` is called uniformly, not
hand-copied from the reference file's own flat lists — a real, deliberate behavior difference, not
just a style choice. Confirmed by direct comparison: `AsyConnTime.get_task_starters()` includes
`start_hotspot_timeout_watcher` (the real task backing `hotspot_time_min`'s timeout), which the
reference file's own hand-written `task_starters` list in `main()` never actually starts.
`src/sensortask_wozi.py` now starts it, since calling `conn.get_task_starters()` is the whole point
of that method existing. Flagged to the project owner as a believed-correct fix, not silently
carried forward or silently dropped — worth a second look if hotspot-timeout behavior on a real
deployed unit ever seems to disagree with `hotspot_time_min`'s documented meaning.

## Reference: the pre-Step-1 flat construction order (`improved-quality/sensortask-wozi.py`, unedited)

Kept for historical/comparison purposes — this is what the section above was rewritten from, not
what's current. `improved-quality/sensortask-wozi.py` itself stays unedited (CLAUDE.md's hard rule).

1. `conn = AsyConnTime(...)`
2. `ntp = AsyNtpClient(...)`
3. `app = Microdot()`
4. `i2c0`, `i2c1` = `asy_i2c_driver.I2C(...)` ×2
5. `spi0 = asy_spi_driver.SPI(...)`
6. `fram = AsyFramManager(...)`
7. `sysfunct = SystemService(...)`
8. `sgp_reader = SGP40_Reader(...)`
9. `bmp_reader = BMP3xx_Reader(...)`
10. `scd_reader = SCD30_Reader(...)`
11. `pixel = NeopixelDriver(...)`
12. `notify_service = NotificationCoordinator(...)`, `register()` ×3, `finalize()`
13. `conn.set_ext_led(pixel)`
14. Module-level route decorators (`@app.get`/`@app.put`), then `async def main()` (task starting
    only — no construction, no `setup()` batch of its own beyond `fram.setup()` via
    `async_onetime`), then bare `asyncio.run(main())` at the very bottom of the file.

## Dependency graph (who holds a reference to whom)

- `ntp` holds `conn`'s `wifi_mode_lock`, `network_available`, `get_dns_server_ip` — bound methods,
  not a module import, so no real Python import cycle exists despite the logical dependency.
- `notify_service` holds `pixel.request_signal` (callback) and `ntp.cettime` (callback) — same
  pattern, injection not import.
- `conn` holds `pixel` (via `set_ext_led()`, called after both exist) for the WiFi-status LED.
- `sgp_reader` holds `ntp.ntp_issynced` (callback) for its VOC-backup timestamp validity check.
- Every `*_Reader`/service constructs its own `ConfigManager`/`PrintLog` instance internally
  (`base_classes.py`'s `SensorReaderConfig.__init__`) — no cross-module config sharing anywhere.

No module in `src/` imports another `src/` module *by name* to reach a sibling driver/service —
every cross-module dependency in the real wiring is constructor-injected (bound method or object
reference), confirmed by reading every `import`/`from` statement in `src/` this session. This is
good news for the eventual rewrite: the dependency graph is already a clean DAG at the Python-import
level, and the *runtime* object graph above is the only thing a rewrite needs to reproduce.

## Structural fallout from the `ConfigManager` setup()-ripple decision — resolved by Step 1

The sync-`__init__`/async-`setup()` readiness-gate scheme (`SPECIFICATION.md` Part C.13 is the
permanent record of the pattern itself) extends up through `ConfigManager` → `SensorReaderConfig` →
every concrete `SensorReaderConfig` subclass. Concretely, this meant the reference file's
construction sites for `bmp_reader` (`BMP3xx_Reader`), `sgp_reader` (`SGP40_Reader`), and
`notify_service` (`NotificationCoordinator`) each needed an added `await x.setup()` call after
construction — `scd_reader` (`SCD30_Reader`) and `pixel` (`NeopixelDriver`) stay exempt (plain
`SensorReader` subclasses, no `ConfigManager`).

**Resolved**: `src/sensortask_wozi.py`'s `build_system()` is an `async def`, so this no longer
"breaks" anything structurally the way it would have inside a flat, top-level-statement file — see
"Current construction order" above for the actual resolution (grouped `await x.setup()` batch,
item 14). The FRAM chunk-order determinism rule holds across this change (verified directly:
`get_chunk()`/`get_timestamped_chunk()` are called synchronously inside each object's own
`__init__`, before any `setup()` call ever runs — chunk allocation and `setup()` timing are
independent, so the async restructure doesn't touch chunk ordering at all).

## Current state of the file (mechanical fixes, allowed now per owner authorization — no full promotion)

`/time/config`'s and `/led/config`'s `None`-handling is intentional, not an open gap: both routes
already return `None` safely, matching `/net/config`'s own established "let it be `None`"
convention. The import is `from asyncio import ThreadSafeFlag` (current MicroPython naming —
`uasyncio` stays a compatibility alias but every import in this file and across `src/` uses the
plain name).

`_MAX_I2C_ERR = const(5)` here still uses the pre-rename name — the project-wide `max_i2c_err` →
`max_module_error` rename (`SPECIFICATION.md` C.2) landed in `src/` during Step 1, but this file is
`improved-quality/sensortask-wozi.py`, which stays untouched per CLAUDE.md's hard rule regardless
(not a "deferred rename" gap anymore, just out of scope like the rest of that file).
`src/sensortask_wozi.py` now uses the new name (`_MAX_MODULE_ERROR`).

## Forward API-design notes (not this audit's scope — recorded for whenever the REST layer is next touched)

- Bus-layer status: once each I2C/SPI bus instance has its own logger name (`"I2C0"`/`"I2C1"`/
  `"SPI0"`), the natural REST shape is one endpoint with one field per bus instance.
- Networking status: `captive_dns.py`'s own logger plus, once built, the future Microdot
  connection-timeout wrapper (`asy_webserver_service.py`, BACKLOG's "Microdot hardening design")
  both belong under one future "Networking" endpoint, one JSON field per component.
- **`debug` needs to become a persisted, API-settable config value** (owner requirement, Step 1
  session) instead of `src/sensortask_wozi.py`'s current construction-time-only constant, forwarded
  unchanged into every module's `debug=` constructor argument. Making it live would need every
  module's `PrintLog.level` to become re-readable from a shared source instead of a one-time
  constructor snapshot (`print_log.py`'s `PrintLog.__init__` just stores `self.level` once,
  confirmed directly) — a cross-cutting change, not a one-file fix. Where this persisted value
  should actually live (a new small `SystemService`-owned schema field is the leading candidate,
  since it's a whole-device operational setting rather than any one driver's own config) is still
  an open question for Step 2 (owns the config/REST layer) or a dedicated follow-up — not resolved
  here, just recorded so it isn't rediscovered from scratch.
- `watchdog = WDT(timeout=8000)` stays hardcoded at construction time in `build_system()`, no
  injection point — owner-confirmed, deliberately not part of the `debug`-style
  persisted-config direction above ("must be hardcoded so no error ever can circumvent it when it
  is set active").

## Status

**Step 1 landed**: `src/sensortask_wozi.py` exists, with `boot_entry/wozi_boot.py` as its separate
real firmware entry point (see that module's own docstring). "Current construction order" above
now describes `src/sensortask_wozi.py` as it actually is, not a plan for a future rewrite; the
"Reference" section right after it keeps the pre-Step-1 flat order for comparison. Full unit-test
coverage lives in `tests/test_sensortask_wozi.py` (construction order, FRAM chunk order, the
setup()-batch order and its `notify_service`/`finalize()` constraint, task/timer starter
collection) — all passing under the real MicroPython Unix-port interpreter as of this session,
alongside the full existing suite (`scripts/lint.sh`/`scripts/typecheck.sh`/`scripts/test.sh` all
clean). The `get_error_counter()` gap on `DNSServer`/`NeopixelDriver` is closed and the
`max_i2c_err` → `max_module_error` rename is done project-wide (both `src/`-wide, not scoped to
this one file).

Kept alive per the "Status update" note at the top of this document, not deleted — Steps 2-5 still
need this exact construction order/dependency graph preserved as they build on top of it. Re-verify
the sections above whenever a future change to `src/sensortask_wozi.py` (or, still, a change to
`improved-quality/sensortask-wozi.py`, unlikely as that is) could plausibly affect construction
order, the dependency graph, or the FRAM chunk sequence.
