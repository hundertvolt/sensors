# Wiring Contract — `improved-quality/sensortask-wozi.py` study

**Status update (Steps 1-3 landed)**: this doc's own original header said it would be deleted once the
real Stage-1 standalone `sensortask-wozi.py` successor landed — that's now true, `src/sensortask_wozi.py`
exists (Step 1 of `FINAL_WIRING_PLAN.md`'s five-step effort), Step 2 (the generic webserver/API
service, `src/asy_webserver_service.py`, wired into `build_system()`) has landed on top of it too,
and Step 3 (the `digital_twin/` hardware simulator, a separate module at the `machine`-mocking
boundary with zero `src/sensortask_wozi.py` awareness by design) has landed alongside it without
touching this construction order at all.
Kept alive anyway, deliberately deviating from that stated lifecycle: Steps 4-5 still need this exact
construction order/dependency graph preserved as they build on top of it, so this remains the living
reference until the whole five-step effort merges back, not just until Step 1 alone lands. Still
**keep it up to date** whenever a change to `src/sensortask_wozi.py` touches anything documented
below.

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
build_system(*, cfg_path: str = "", debug: int | None = None)` instead of bare module-level
statements — required for
testability (a bare top-level blocking call, matching the reference file's own bottom-of-file
`asyncio.run(main())`, would hang on plain `import`; see `src/sensortask_wozi.py`'s own docstring
and `FINAL_WIRING_PLAN.md`'s Step 1 refined plan for the full reasoning and the resulting two-file
split with `boot_entry/wozi_boot.py`). `app = Microdot()`/routes are Step 2's own addition (item 14
below, landed in a later session than Step 1's original construction sequence) — `import
frozen_html` is still excluded, Step 4's job, owner-confirmed.

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
14. **`app = Microdot(); webserver = WebserverService(app, ...)`** (Step 2, landed in a later session
    than the rest of this list) — registers every real driver's `SettingsGroup`/`status_source`/
    `system_cmd`/`notification_led`/`maintenance_sensor`/`error_source`, built here because every
    module it registers must already exist. **No `fram=`** — deliberately RAM-only (see
    `FINAL_WIRING_PLAN.md`'s Step 2 status update for the full reasoning: a per-call/outer-cap
    reclaim warning could churn far faster than any sensor's rare-hardware-fault log, and this keeps
    the five-chunk FRAM order below unchanged — no sixth chunk).
15. `sysfunct.set_level_setters(_collect_level_setters())` — collects every logger's own
    `set_level()` bound method (see "Debug level" below) into `sysfunct`'s registry, sync, after
    every module (including `notify_service.finalize()` and the webserver from step 14) has fully
    constructed.
16. **Grouped `await x.setup()` batch** (new in Step 1, resolved by dependency-domain analysis, not
    interleaved with construction above): `await sysfunct.setup()` → `await fram.setup()` →
    `await conn.setup()` → `await ntp.setup()` → `await sgp_reader.setup()` →
    `await bmp_reader.setup()` → `await notify_service.setup()`.
    These are independent readiness domains (`sysfunct.setup()` is its own local `config_SYSTEM.cfg`;
    `fram.setup()` is FRAM-hardware/SPI readiness; the rest are each module's own local-JSON-config
    `ConfigManager.setup()`, unrelated to FRAM or each other), so there's no ordering requirement
    *between* them except one: `notify_service.setup()` is only valid to call after `finalize()`
    (step 12) has run (`asy_notification_service.py`'s own documented contract, `self.cfgmgr` doesn't
    exist before then), and batching at the end automatically satisfies that for every module, not
    just `notify_service`. `sysfunct` goes first — its `setup()` is what resolves the real persisted
    debug level and pushes it through the registry from step 15, so every subsequent `setup()` call's
    own diagnostic logging already reflects it. `fram` keeps its next position, matching the reference
    file's own existing `async_onetime` list. `conn.setup()`/`ntp.setup()` are a real gap fix found
    while wiring Step 2 (not part of the original Step 1 finding) — `AsyConnTime`/`AsyNtpClient` are
    `SensorReaderConfig` subclasses under the exact same pattern as `sgp_reader`/`bmp_reader`/
    `notify_service`, but nothing anywhere in the system ever called their `cfgmgr.setup()` before
    this fix, confirmed directly (a config write failed with `"Failed"` until fixed); placed right
    after `fram`'s fixed slot, matching `conn`/`ntp`'s own real construction order (both built before
    `fram`/`sysfunct`). The remaining three calls are appended in their own construction order.

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
`webserver.get_task_starters()` (Step 2) is appended the same uniform way — its one task
(`_start_serving`) participates in `start_and_check_tasks()`'s ordinary supervisor loop like every
other module, no bespoke restart mechanism (`FINAL_WIRING_PLAN.md`'s Step 2 decision 1).

**Debug level** (`src/sensortask_wozi.py`'s `_collect_level_setters()`, `system_service.py`'s
`SystemService.set_level_setters()`/`_apply_level()`/`get_debug_level()`/`set_debug_level()`) —
**a registry of function references, not a shared mutable value.** An earlier version of this
mechanism during the same session used a shared object every logger's `level` read from live
(`base_classes.py`'s `SharedLevel`, `print_log.py`'s `PrintLog.level` as a `@property`) — reverted
per explicit owner feedback: it made `PrintLog` harder to read/understand, broke separation between
classes, and made manual debugging harder (inspecting `logger.level` no longer showed a plain
value). The registry design keeps every `PrintLog` instance a plain, independent object with its
own already-existing `set_level()` method (no changes to `print_log.py` at all) and no coupling to
any cross-module concept.

- `_collect_level_setters()` collects every logger's own `set_level` **bound method** (not the
  logger object itself) into a flat list — the exact same 16-logger list the reverted
  `_attach_debug_level()` used to iterate (every module's own top-level `self.pr`, every nested
  `cfgmgr.pr`, and `AsyConnTime`'s own separately-named `dns_server.pr`) — mirroring
  `_collect_task_starters()`/`_collect_timer_starters()`'s own shape exactly, per owner direction
  ("in the same style as the task or timer starters — so we stay coherent in style as well").
- `sysfunct.set_level_setters(...)` receives that list once, at boot (see "Current construction
  order" step 14 above) — stored, not consumed immediately, since it needs calling again on every
  future level change, unlike `start_timers()`/`start_and_check_tasks()`'s own one-shot lists.
- `SystemService._apply_level(value)` iterates the registry calling each entry with the new value,
  wrapped individually in `try`/`except Exception` (matches this codebase's established
  "driver/caller-supplied callback could misbehave" defense, e.g. `_timer_sequencer()`'s own
  per-starter guard) — one bad entry can't stop the rest of the registry from updating.
  `setup()`/`set_debug_level()` both call it; `set_debug_level()` still validates via
  `ConfigManager.write_config()`'s own `type_or_range_error` range check before ever touching the
  registry, exactly as before.
- **Concurrency safety, checked directly rather than assumed** (owner asked): calling `set_level()`
  on any `PrintLog` instance at any time is safe on this codebase's real execution model. The only
  interrupt handler in the whole of `src/` (`asy_scd30_driver.py`'s pin IRQ) only sets a
  `ThreadSafeFlag`, never touches logging — confirmed by grep, not assumed. Every real
  `PrintLog` call site is either plain synchronous code or a `machine.Timer` callback, and rp2
  MicroPython's `Timer` callbacks run via `micropython.schedule()` (soft-scheduled, deferred into
  the main loop between bytecode instructions — never true hardware preemption; see CLAUDE.md's own
  "soft-Timer-callback-drop" platform fact for the same underlying mechanism). `self.level` is a
  single plain `int` attribute; a MicroPython attribute assignment is a single atomic pointer/
  immediate-value store with no torn-write case. Worst case from a level change racing a log call:
  one line uses the old-vs-new threshold — a transient start/stop right at the boundary, explicitly
  accepted by the owner as fine, never corruption or a crash.

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
- Networking status: `captive_dns.py`'s own logger plus the Microdot connection-timeout wrapper
  (`asy_webserver_service.py`, BACKLOG's "Microdot hardening design" — implemented, Step 2) both
  landed under one `/networking`/`/status.networking` endpoint pair, one JSON field per component,
  per FINAL_WIRING_PLAN.md's Step 2 endpoint design.
- **`debug` is now a persisted, live config value — resolved during Step 1, not deferred.** Full
  mechanism (the level-setter registry, `system_service.py`'s `config_SYSTEM.cfg`, and the
  reverted shared-value alternative) is documented under "Debug level" in "Current construction
  order" above, not duplicated here. The REST route itself now exists too, landed as Step 2:
  `sysfunct.set_debug_level()`/`get_debug_level()` are wired into `/system`'s `SettingsGroup` via
  `SystemService.get_dict_cfg()`/`_set_dict_cfg()` (a later, follow-up-session addition to Step 2 —
  see FINAL_WIRING_PLAN.md's Step 2 status update).
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
collection, the system-wide debug-level registry) plus `tests/test_base_classes.py`,
`tests/test_print_log.py` (both back to their pre-debug-level-work baseline), and
`tests/test_system_service.py` (`config_SYSTEM.cfg`/`set_level_setters()`/`get_debug_level()`/
`set_debug_level()`) — all passing under the real MicroPython Unix-port interpreter as of this
session, alongside the full existing suite (`scripts/lint.sh`/`scripts/typecheck.sh`/
`scripts/test.sh` all clean). The `get_error_counter()` gap on `DNSServer`/`NeopixelDriver` is
closed, the `max_i2c_err` → `max_module_error` rename is done project-wide, and the general,
persisted, live debug-level mechanism (owner-directed follow-up mid-Step-1, went through one real
design iteration — see "Debug level" above — before landing on the registry shape) is fully wired
end to end, REST route included (landed as part of Step 2, see above).

**Step 2 landed** (later session): `src/asy_webserver_service.py`/`WebserverService` exist and are
wired into `build_system()` (construction-order item 14 above) against real driver objects, the
100+-cycle soak test passes, and `src/asy_webserver_service.py` is at 99% line coverage — see
FINAL_WIRING_PLAN.md's Step 2 status updates for the full detail, including the two real
construction-order findings made while wiring it in (`conn.setup()`/`ntp.setup()`, item 16 above)
and the "no `fram=`" decision preserving this document's five-chunk FRAM invariant.

Kept alive per the "Status update" note at the top of this document, not deleted — Steps 4-5 still
need this exact construction order/dependency graph preserved as they build on top of it. Re-verify
the sections above whenever a future change to `src/sensortask_wozi.py` (or, still, a change to
`improved-quality/sensortask-wozi.py`, unlikely as that is) could plausibly affect construction
order, the dependency graph, or the FRAM chunk sequence.
