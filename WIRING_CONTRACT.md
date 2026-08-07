# Wiring Contract — `improved-quality/sensortask-wozi.py` study

Companion to `AUDIT_PLAN.md` (also temporary — deleted once the real Stage-1 standalone
`sensortask-wozi.py` successor lands in a future session and this document's job is done). Captures
the instantiation-order/dependency-graph facts a future wiring rewrite must preserve, plus forward
notes for that future REST API design. The full study happens at Cluster 10; seeded now with what
reading the file in full this session already turned up.

## Why instantiation order matters

`AsyFramManager` is a bump-pointer allocator (see CLAUDE.md) — `get_chunk()`/
`get_timestamped_chunk()` carve out fixed offsets in call order, so a device's *instantiation
order* of these calls is its on-chip layout and must stay identical across firmware versions for
existing stored data to keep decoding correctly. See `AUDIT_PLAN.md`'s "FRAM chunk determinism
rule" for the full standing check.

## Current construction order (`sensortask-wozi.py`, module level, top to bottom)

1. `conn = asy_conn_time(...)` — owns `DNSServer` internally (`captive_dns.py`)
2. `ntp = asy_ntp_client(conn.get_wifi_mode_lock(), conn.network_available, conn.get_dns_server_ip, ...)`
   — takes bound methods off `conn`, not a direct import-time reference
3. `app = Microdot()`
4. `i2c0`, `i2c1` = `asy_i2c_driver.I2C(...)` ×2
5. `spi0` = `asy_spi_driver.SPI(...)`
6. `fram = AsyFramManager(spi0, 1, max_size=0x2000, ...)` — **first real FRAM-chunk consumer of
   itself is none; it constructs `FRAM_SPI` internally with a shared `logger=`**
7. `sysfunct = SystemService(ntp.ntp_issynced, watchdog=watchdog, fram=fram, ...)` — **FRAM chunk 1**
8. `sgp_reader = SGP40_Reader(i2c1, sgp_comp_callback, fram_storage=fram, fram_ntp_callback=ntp.ntp_issynced, ...)`
   — **FRAM chunk 2** (its own `PrintLogHistoryStore`, if `fram=` were forwarded — currently only
   `fram_storage=` for the VOC backup chunk is passed, not `fram=` for its own error log; recheck
   during Cluster 7 whether that's deliberate)
9. `bmp_reader = BMP3xx_Reader(i2c1, ...)` — no `fram=` passed, in-memory logging only
10. `scd_reader = SCD30_Reader(i2c0, 8, trigger_sec=3, ...)` — no `fram=`, no config schema at all
    (params live on-sensor, see CLAUDE.md)
11. `pixel = NeopixelDriver(15, fram=fram, ...)` — **FRAM chunk 3**
12. `notify_service = NotificationCoordinator(pixel.request_signal, ntp.cettime, fram=fram, ...)` —
    **FRAM chunk 4**, staged registration (`register()` ×3 for `WarnCO2`/`WarnVOC`/`WarnHum`, then
    `finalize()` exactly once)
13. `conn.set_ext_led(pixel)` — wires the WiFi-status LED callback after both exist

**Real FRAM chunk order today**: `SystemService` → `SGP40_Reader` (VOC backup only) →
`NeopixelDriver` → `NotificationCoordinator`. Must stay in this relative order in any rewrite,
regardless of byte offset (which doesn't matter per the determinism rule).

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

## Already-found gaps in the current file (mechanical fixes, allowed now per owner authorization — no full promotion)

- Three `# TODO` None-handling gaps: `/net/config`, `/time/config`, `/led/config` GET handlers
  don't define what happens when the underlying `cfgmgr.get_dict()` call returns `None` (one
  sibling case, `/net/config`'s `PW` assignment, already crashed for real and was fixed — see the
  file's own top-of-file migration comment).
- Old-style `from uasyncio import ThreadSafeFlag` import (should be `from asyncio import
  ThreadSafeFlag` per current MicroPython naming — `src/README.md` section 9's exact example case).
- `_MAX_I2C_ERR = const(5)` — the project-wide `max_i2c_err` rename (BACKLOG.md, deferred) hasn't
  reached this file yet either.

## Forward API-design notes (not this audit's scope — recorded for whenever the REST layer is next touched)

- Bus-layer status: once each I2C/SPI bus instance has its own logger name (`"I2C0"`/`"I2C1"`/
  `"SPI0"`), the natural REST shape is one endpoint with one field per bus instance.
- Networking status: `captive_dns.py`'s own logger plus, once built, the future Microdot
  connection-timeout wrapper (`asy_webserver_service.py`, BACKLOG's "Microdot hardening design")
  both belong under one future "Networking" endpoint, one JSON field per component.

## Status

`[ ]` Full Cluster 10 study not yet started — this document currently only reflects what surfaced
incidentally while reading the file for the logging/naming design work.
