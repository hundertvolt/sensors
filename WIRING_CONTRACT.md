# Wiring Contract — `improved-quality/sensortask-wozi.py` study

Temporary, but on a different clock than `BACKLOG.md`'s usual "resolved items get pruned" rule:
deleted once the real Stage-1 standalone `sensortask-wozi.py` successor actually lands in a future
session and this document's job is done — not before. Until Stage 1 happens, this file is the
single, permanent home for the instantiation-order/dependency-graph facts a future wiring rewrite
must preserve, plus forward notes for that future REST API design — **keep it up to date** whenever
a change to `src/` or `improved-quality/sensortask-wozi.py` touches anything documented below.

## Why instantiation order matters

`AsyFramManager` is a bump-pointer allocator (see CLAUDE.md) — `get_chunk()`/
`get_timestamped_chunk()` carve out fixed offsets in call order, so a device's *instantiation
order* of these calls is its on-chip layout and must stay identical across firmware versions for
existing stored data to keep decoding correctly. See `SPECIFICATION.md` Part A.4's "FRAM chunk
determinism rule" for the full standing check.

## Current construction order (`sensortask-wozi.py`, module level, top to bottom)

1. `conn = AsyConnTime(...)` — owns `DNSServer` internally (`captive_dns.py`)
2. `ntp = AsyNtpClient(conn.get_wifi_mode_lock(), conn.network_available, conn.get_dns_server_ip, ...)`
   — takes bound methods off `conn`, not a direct import-time reference
3. `app = Microdot()`
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
12. `notify_service = NotificationCoordinator(pixel.request_signal, ntp.cettime, fram=fram, ...)` —
    **FRAM chunk 5**, staged registration (`register()` ×3 for `WarnCO2`/`WarnVOC`/`WarnHum`, then
    `finalize()` exactly once)
13. `conn.set_ext_led(pixel)` — wires the WiFi-status LED callback after both exist

**Real FRAM chunk order today**: `SystemService` → `SGP40_Reader` (its own error log, chunk 2) →
`SGP40_Reader` (VOC backup, chunk 3) → `NeopixelDriver` → `NotificationCoordinator`. Five chunks
total, not four — corrected from this doc's earlier count once `SGP40_Reader`'s own logger was
confirmed to already be FRAM-backed (see item 8 above). Must stay in this relative order in any
rewrite, regardless of byte offset (which doesn't matter per the determinism rule).

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

## New structural fallout from the `ConfigManager` setup()-ripple decision

The sync-`__init__`/async-`setup()` readiness-gate scheme (`SPECIFICATION.md` Part C.13 is the
permanent record of the pattern itself) extends up through `ConfigManager` → `SensorReaderConfig` →
every concrete `SensorReaderConfig` subclass. Concretely, this means `sensortask-wozi.py`'s construction sites for
`bmp_reader` (`BMP3xx_Reader`), `sgp_reader` (`SGP40_Reader`), and `notify_service`
(`NotificationCoordinator`) each need an added `await x.setup()` call after construction —
`scd_reader` (`SCD30_Reader`) and `pixel` (`NeopixelDriver`) are exempt (plain `SensorReader`
subclasses, no `ConfigManager`).

**This breaks a load-bearing assumption of the current construction order**: every step in "Current
construction order" below is a plain, synchronous, module-level statement today. The moment any one
of them needs `await`, the whole sequence (or at least everything from the first `await`ed step
onward) has to run inside an async context — `sensortask-wozi.py` can no longer be a flat sequence of
top-level statements the way it is now. Resolving *how* Stage 1's rewrite handles that is out of
scope here too — Stage 1 itself is a later session's job — but Stage 1 must not be blindsided by it:
whatever shape the rewrite takes (an `async def main()` wrapping construction, a staged boot
sequence, etc.), it needs to preserve the FRAM chunk-order determinism rule
(`SPECIFICATION.md` Part A.4's "FRAM chunk determinism rule") across that change — an `await`-ed
setup step is still a single, unconditional, deterministic point in the sequence, so the rule itself
doesn't break, but it's worth being explicit that "deterministic" now has to be verified across an
async sequence, not just a synchronous one.

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
`src/sensortask_wozi.py`, once it exists, uses the new name.

## Forward API-design notes (not this audit's scope — recorded for whenever the REST layer is next touched)

- Bus-layer status: once each I2C/SPI bus instance has its own logger name (`"I2C0"`/`"I2C1"`/
  `"SPI0"`), the natural REST shape is one endpoint with one field per bus instance.
- Networking status: `captive_dns.py`'s own logger plus, once built, the future Microdot
  connection-timeout wrapper (`asy_webserver_service.py`, BACKLOG's "Microdot hardening design")
  both belong under one future "Networking" endpoint, one JSON field per component.

## Status

Last verified accurate against `src/` and `improved-quality/sensortask-wozi.py` as of commit
`acc4993`, with one correction made during Step 1's own session: `SGP40_Reader`'s own error log was
confirmed FRAM-backed (chunks 2+3, not chunk 2 alone — see item 8 above), fixing a stale "recheck
whether that's deliberate" note. The "Current construction order" and "Dependency graph" sections
above hold with that correction folded in. The "New
structural fallout" section's analysis (every `SensorReaderConfig` subclass's construction site
needing an added `await x.setup()`, and the resulting break of the current flat synchronous
construction sequence) is still accurate and still unresolved — genuinely Stage 1's job, not this
document's.

This document's job is Stage 1's wiring rewrite, not a one-time audit — re-verify the sections above
whenever a future change to `src/` or `improved-quality/sensortask-wozi.py` could plausibly affect
construction order, the dependency graph, or the fallout item above.
