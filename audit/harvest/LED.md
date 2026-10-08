# Harvest — LED: Notification and LED

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`, moved to `4dc80ef` by V11).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: SETTLED 8, INVAR 18, MIRROR 8, LIMIT 13, ASSUME 6, PLATFORM 3, SUPPRESS 6, TODO 1, DRIFT 1 — 64 items.


## src/asy_neopixel_driver.py

- **LED.N001** SETTLED · `src/asy_neopixel_driver.py:5` — "No config schema (confirmed by the project
  owner)." — Owner decision: LED driver has no config. · [H01]
- **LED.N002** MIRROR · `src/asy_neopixel_driver.py:5-6` — "Also satisfies asy_wifi_service.py's
  LEDControl Protocol via `on()`/`off()`/`toggle()`." — Structural protocol conformance kept by hand. ·
  [H01]
- **LED.N003** LIMIT · `src/asy_neopixel_driver.py:29, 163-169` — "_MIN_SIGNAL_S = const(0.1) # floor
  for a signal's ramp duration; also the NaN/garbage fallback" / "except OverflowError: # t is +inf" —
  Duration has a floor and NaN/inf handling but no ceiling at driver level. · covered-by: LED.S01 ·
  [H01]
- **LED.N004** SUPPRESS · `src/asy_neopixel_driver.py:36-40` — "except (ValueError, OverflowError): #
  NaN/inf: int() raises for both" → 0 — NaN/inf colour silently becomes 0; a non-numeric (TypeError) is
  not caught. · related: LED.T02 · [H01]
- **LED.N005** INVAR · `src/asy_neopixel_driver.py:54-55, 110-114` — "matches self.pr.name - the
  _ModuleLike registration shape" / "duck-typed, not inherited" — Registration shape mirrored with
  SensorReader/webserver by convention. · related: CORE.T09 · [H01]
- **LED.N006** INVAR · `src/asy_neopixel_driver.py:107-108` — "no machine.Timer anywhere in this file
  (SPECIFICATION.md C.9 shape, kept empty rather than omitted so callers can treat every driver
  uniformly)" — Uniform starter interface (low). · [H01]
- **LED.N007** INVAR · `src/asy_neopixel_driver.py:156` — "await self.pr.setup() # required for all
  logged warnings and errors" — Only the signal task sets the logger up; the other two tasks log
  print-only `evt` (low). · related: XCUT.T08 · [H01]
- **LED.N008** PLATFORM · `src/asy_neopixel_driver.py:163` — "`not >=`, not `<`: a NaN comparison is
  always False, so the floor kicks in" — NaN comparison semantics relied on (low). · related: LED.T02 ·
  [H01]

## src/asy_notification_service.py

- **LED.N009** INVAR · `src/asy_notification_service.py:5, 145-146, 276, 291, 307` — "Registration is
  staged: `register()` each signal, then `finalize()` once" / "call exactly once, after all register()
  calls, before any task starter runs" — Construction order is caller discipline (generated code);
  violations degrade to guarded no-ops and buffered wrnno 1-4. · covered-by: LED.T03 · [H01]
- **LED.N010** MIRROR · `src/asy_notification_service.py:33-35` — "a namedtuple (asy_ntp_client.py's
  GMTimeStruct, the production wiring) satisfies it too" — `_LocalTime` Protocol mirrors
  asy_ntp_client's struct by hand. · [H01]
- **LED.N011** MIRROR · `src/asy_notification_service.py:63-66` — "Signature and return-value contract
  match NeopixelDriver.request_signal exactly" — `_DefaultSignalSink` must track
  `NeopixelDriver.request_signal` by hand. · related: GEN.T06 · [H01]
- **LED.N012** MIRROR · `src/asy_notification_service.py:84-85` — "Literal submitGroup (\"autoConfig\")
  ... the hand-written definitions established it" — Tag value mirrors hand-written website definitions
  (low). · related: WEB.T05 · [H01]
- **LED.N013** SETTLED · `src/asy_notification_service.py:87, 369` — "Auto On must be before Off, on the
  same day." / "if on_min_of_day <= cur_min_of_day <= off_min_of_day:" — Midnight-wrapping window
  silently never triggers — SETTLED as legacy-identical (SPECIFICATION.md:280-283). · related: LED.T06,
  PAR.T03 · [H01]
- **LED.N014** MIRROR · `src/asy_notification_service.py:103-107` — "_FIELDS = const((\"Triggered\",
  \"TS\")) # kept in sync with NOTIFY's own fields above" — Enforced by
  `tests_scripts/test_measurement_field_tuple_agreement.py`. · [H01]
- **LED.N015** ASSUME · `src/asy_notification_service.py:128` — "self.color = color # per-channel weight
  (0/1), scaled by FlashBri at trigger time" — Weights assumed 0/1; larger weights are only clamped
  downstream by the neopixel driver (low). · related: LED.T02 · [H01]
- **LED.N016** INVAR · `src/asy_notification_service.py:130-132` — "Only ever touched by the
  coordinator's single poll-loop task - no lock needed." — Single-writer convention. · [H01]
- **LED.N017** INVAR · `src/asy_notification_service.py:155-157` — "Buffered: register()/finalize() are
  sync and self.pr may not exist yet, so rejections drain via monitor_loop()" — Registration warnings
  persist only once monitor_loop runs. · covered-by: LED.T03 · [H01]
- **LED.N018** SUPPRESS · `src/asy_notification_service.py:188-192` — "caller-supplied callback, could
  legitimately misbehave" err_s "local_time_callback failed:" errno=12 — Callback failure swallowed;
  persisted every cycle it fails. · related: LED.T04 · [H01]
- **LED.N019** ASSUME · `src/asy_notification_service.py:195-197` — "get_data() never raises, but the
  specific field can legitimately be None" — Relies on every producer's never-raise get_data(). ·
  related: LED.T04 · [H01]
- **LED.N020** SUPPRESS · `src/asy_notification_service.py:199-204` — err_s notif.name, "Value read
  failed:" errno=10 — Source read failure swallowed to None (persisted, no repeat rule). · related:
  LED.T04 · [H01]
- **LED.N021** ASSUME · `src/asy_notification_service.py:209` — "works for an \"int\" schema field too -
  float(cached_int) never raises" — Threshold read path assumption. · [H01]
- **LED.N022** LIMIT · `src/asy_notification_service.py:210-213` — err_s notif.name, "Threshold config
  read failed!" errno=11 — Persisted per signal per cycle with no repeat rule (unlike own-config wrnno 5
  at :355). · related: XCUT.T07 · [H01]
- **LED.N023** LIMIT · `src/asy_notification_service.py:215-218` — "float(value): getattr()'s own return
  is untyped ... narrows to a real numeric comparison" — `float()` outside the try; a non-numeric field
  ends monitor_loop. · covered-by: LED.S02 · [H01]
- **LED.N024** SUPPRESS · `src/asy_notification_service.py:225-228` — err_s notif.name,
  "request_signal_cb failed:" errno=13 — LED sink failure swallowed. · [H01]
- **LED.N025** INVAR · `src/asy_notification_service.py:249-250, 258, 265, 308, 313, 318, 333` —
  "caller-ordering bug, defense-in-depth only" — Pre-finalize guards return empty/neutral values instead
  of failing. · covered-by: LED.T03 · [H01]
- **LED.N026** SUPPRESS · `src/asy_notification_service.py:251` — "# type: ignore[return-value]" —
  get_data() narrowing. · related: SENS.T08 · [H01]
- **LED.N027** ASSUME · `src/asy_notification_service.py:270, 274` — "never None: never constructed/set
  with a None sentinel" / "LockedCounter clamps into [0, _MAX_OVERRIDE_TIME] itself" — Relies on
  base_classes.LockedCounter semantics. · related: CORE.T08 · [H01]
- **LED.N028** SETTLED · `src/asy_notification_service.py:297` — "0, # no failure streak: a restart
  re-reads nothing monitor_loop() doesn't (Part C.7.2)" — max_module_error = 0 by design. · [H01]
- **LED.N029** INVAR · `src/asy_notification_service.py:320, 337-339` — "No self._auto_active = True
  here ... two independently-restartable tasks over one unlocked flag." — Only auto_led_override writes
  `_auto_active` (it resets it to True on its own restart). · related: LED.T01 · [H01]
- **LED.N030** LIMIT · `src/asy_notification_service.py:346-356` — "interv = 600.0" + wrn_s "Error
  reading own configuration!" wrnno=5 repeat=cfg_failing — Degraded mode: fixed 600 s poll, no checks,
  and the NOTIFY snapshot is not refreshed (stale TS) (low). · related: XCUT.T17 · [H01]
- **LED.N031** LIMIT · `src/asy_notification_service.py:365` — "if cur_time is not None: # no NTP sync,
  missing config, or a raising callback" — No notifications at all without NTP sync. · related: NET.T11
  · [H01]
- **LED.N032** LIMIT · `src/asy_notification_service.py:370-374` — "await asyncio.sleep(2 * flash_dur)"
  — Extra sleep after the last signal too. · covered-by: LED.S03 · [H01]

## src/asy_wifi_service.py

- **LED.N033** INVAR · `src/asy_wifi_service.py:789-790` — "if called even after init, call
  set_wifi_led(status=True) to init LED" — Caller discipline for late `set_ext_led()` · [H02]

## tests/neopixel.py

- **LED.N034** ASSUME · `tests/neopixel.py:19-21` — "this driver only ever uses n=1, but the fake stays
  general" — current usage assumption · [H03]

## tests/test_asy_neopixel_driver.py

- **LED.N035** INVAR · `tests/test_asy_neopixel_driver.py:163-165,430-432` — "request_signal() only
  awaits until the request is queued, not until the ramp itself finishes" — callers cannot await ramp
  completion; tests sleep for the ramp's real duration · [H03]
- **LED.N036** INVAR · `tests/test_asy_neopixel_driver.py:349-355` — "An implementation using
  start_signal_lock.locked() as led_signal()'s busy check would see it unlocked here and be correct by
  accident" — busy detection must use `start_signal_event`, not the lock; pinned by this test · [H03]
- **LED.N037** PLATFORM · `tests/test_asy_neopixel_driver.py:528-530` — "a real NeoPixel's __setitem__
  writes straight into a bytearray and raises ValueError for an out-of-range int (confirmed against
  micropython-lib's real neopixel.py)" — not modelled by `tests/neopixel.py` (its `__setitem__` accepts
  anything); `_clamp_byte()` is the only guard · related: TWIN.T11 · [H03]
- **LED.N038** LIMIT · `tests/test_asy_neopixel_driver.py:567-569,594` — "inf passes neopixel_signal()'s
  own \"t >= 0.1\" floor check (inf >= 0.1 is True) and then raises OverflowError out of the steps
  computation, caught there directly" — non-finite durations handled by a catch, not by validation ·
  related: XCUT.T23 · [H03]

## tests/test_asy_notification_service.py

- **LED.N039** INVAR · `tests/test_asy_notification_service.py:624-626` — "register() runs before the
  logger exists, so a rejection is queued and flushed by the monitor loop" — registration warnings are
  persisted only once monitor_loop drains the queue · related: XCUT.T08 · [H03]
- **LED.N040** INVAR · `tests/test_asy_notification_service.py:646-653,720` — "Four rejection reasons,
  four numbers (1-4): they are what a /status read distinguishes them by" — wrnno 1-4 contract; `:720`
  notes one shared errno for two callback failures, distinguished only by message text · related:
  XCUT.T07 · [H03]
- **LED.N041** SETTLED · `tests/test_asy_notification_service.py:690-691` — "The wiring-defaults no-op
  LED sink (Part L.6.2) ... Its False is the contract NeopixelDriver.request_signal shares: \"not
  signalled\"." — no-op sink contract · [H03]
- **LED.N042** PLATFORM · `tests/test_asy_notification_service.py:769,799-800` — "NaN comparisons are
  always False on both sides" / "+inf >= any finite threshold" — non-finite readings: NaN never
  triggers, ±inf always triggers one side · related: XCUT.T23 · [H03]
- **LED.N043** SETTLED · `tests/test_asy_notification_service.py:839` — "Confirmed by the project owner:
  no failure-escalation cap - every failing cycle logs." — unbounded per-cycle error logging for signal
  failures is owner-decided · [H03]
- **LED.N044** SETTLED · `tests/test_asy_notification_service.py:1134-1140,1171-1177` —
  "auto_led_override() is its sole writer, monitor_loop() only ever reading it" — two independently
  restartable tasks share one unlocked `_auto_active` flag; correctness relies on single-writer
  discipline · related: XCUT.T02, XCUT.T06 · [H03]
- **LED.N045** SETTLED · `tests/test_asy_notification_service.py:1351-1352,1376-1377` — "giving up would
  only spend the supervisor's reboot budget (Part C.7.2). Every failure still counts." — monitor loop
  never gives up; a failure run uses one ring slot · related: XCUT.T02 · [H03]

## tests/test_neopixel_wifi_integration.py

- **LED.N046** MIRROR · `tests/test_neopixel_wifi_integration.py:1-2` — "proving the LEDControl Protocol
  (on/off/toggle) holds end to end - test_asy_wifi_service.py only exercises a FakeLED double" — The
  real NeopixelDriver-as-ext_led seam is proven only here, with fixed 0.05 s sleeps between steps ·
  [H05]

## tests/test_notification_fram_integration.py

- **LED.N047** INVAR · `tests/test_notification_fram_integration.py:83-85` — "the "number and order of
  registered signals stays constant" invariant this design relies on" — NotificationCoordinator's
  combined FRAM chunk layout (built once in finalize()) decodes across reboots only if signal
  registration order/count never changes · [H05]
- **LED.N048** LIMIT · `tests/test_notification_fram_integration.py:119-121` — "NeopixelDriver
  structurally can't fail on any of its own real code paths" — The FRAM history of the NEOPIXEL logger
  is exercised directly, not via a real failure · [H05]

## tests/test_notification_neopixel_integration.py

- **LED.N049** INVAR · `tests/test_notification_neopixel_integration.py:128-129` — "registration order
  (CO2 then VOC) must produce a fully-contiguous red block before any green frame" — Arbitration
  contract between notification signals: no interleaving · [H05]

## tests_hardware/README.md

- **LED.N050** LIMIT · `tests_hardware/README.md:229-231` — "driven **raw** because `NeopixelDriver`
  offers only a steady white and a 0->peak->0 triangle" — Lighting scenarios bypass the production
  driver API. · [H08]
- **LED.N051** LIMIT · `tests_hardware/README.md:596-600` — "WS2812/Neopixel timing has no datasheet in
  this repo's `datasheets/` folder at all" — WS2812 timing check stays manual/qualitative; datasheet
  list given omits isl29125. · related: LED.T07, HW.S17 · [H08]

## pyproject.toml

- **LED.N052** SUPPRESS · `pyproject.toml:277-290` — "ANN401, category 5 - driver-agnostic fan-in seams"
  / "ARG002: _DefaultSignalSink.request_signal() is a no-op sink" — src/asy_notification_service.py:
  ANN401, ARG002; src/asy_sgp40_driver.py: ANN401, FBT001; five tests files: ANN401. · [H09]

## SPECIFICATION.md Part A.4 (Architecture — deep reference, 148-285)

- **LED.N053** SETTLED · `SPECIFICATION.md:163-165` — "`NeopixelDriver` is the one deliberate exception
  to \"every module owns a schema\" (no schema at all, confirmed by the project owner)" —
  Owner-confirmed schema exception. · [H12]
- **LED.N054** INVAR · `SPECIFICATION.md:253-254` — "`request_signal()` returns once queued, not once
  its ramp finishes" — Neopixel API contract (disputed by LED seeds). · related: LED.S01 · [H12]
- **LED.N055** INVAR · `SPECIFICATION.md:258-262` — "`finalize()` (sync, once) builds the combined
  schema ... Rejections during the sync `register()`/`finalize()` window are buffered and drained by
  `monitor_loop()`" — Staged-construction contract for NotificationCoordinator. · related: LED.T03 ·
  [H12]
- **LED.N056** LIMIT · `SPECIFICATION.md:280-283` — "active-window check doesn't handle a window
  wrapping past midnight (`OnH=22`/`OffH=6` silently never triggers)" — Settled limitation; silent
  non-trigger. · related: PAR.T03 · [H12]

## SPECIFICATION.md Part A.6 (Datasheets, 337-356)

- **LED.N057** LIMIT · `SPECIFICATION.md:337-356` — "(`bmp3xx/`, `fram/`, `pico w/`, `scd30/`,
  `sgp40/`)" — No WS2812/NeoPixel or Pico W QSPI flash datasheet listed or mentioned as missing. ·
  covered-by: SENS.S20 · [H12]

## SPECIFICATION.md Part C.4 (Layer 3 Reader, 1624-1697)

- **LED.N058** INVAR · `SPECIFICATION.md:1691-1693` — "Every method reachable before `finalize()` must
  guard against it explicitly (a private `self._finalized: bool` flag)" — Staged-construction guard
  obligation. · related: LED.T03 · [H12]

## DEVICE_REFERENCE.md

- **LED.N059** DRIFT · `DEVICE_REFERENCE.md:11-14` — "This is a static preference ... not a live
  connectivity signal" — The code still toggles and flashes the WiFi LED with connection state. ·
  covered-by: LED.S04 · [H14]
- **LED.N060** ASSUME · `DEVICE_REFERENCE.md:15-17` — "fully overriding the WiFi overlay while it plays
  (the overlay's own value is restored once the flash finishes)" — A signal cancelled mid-ramp leaves
  the pixel lit and replays `rgbt`, so the restore is not guaranteed. · related: LED.T05, LED.T01 ·
  [H14]
- **LED.N061** MIRROR · `DEVICE_REFERENCE.md:17-18` — "Brightness (`FlashBri`, 1–255) and duration
  (`FlashDur`, 0.5–10s)" — The doc bounds mirror src/asy_notification_service.py:75, 77 (they match at
  2a88cc8). · [H14]
- **LED.N062** MIRROR · `DEVICE_REFERENCE.md:18-25` — "each threshold's own **color** is fixed at build
  time, not user-configurable" — The table (WarnCO2 red, WarnVOC green, WarnHum blue) mirrors
  buildgen/codegen.py:26-31 `_KNOWN_SIGNALS` (1,0,0)/(0,1,0)/(0,0,1); it matches. · related: GEN.T06 ·
  [H14]

## BACKLOG.md

- **LED.N063** TODO · `BACKLOG.md:94-94` — "a hard-reset-recovery bench test for NOTIFY's own FRAM
  chunk (needs an observable-write signal analogous to SGP40's BackupTS first)" — Follow-on (d). · [H15]
  ⟨4dc80ef: G4 scratched by the owner 2026-09-25: src/ is never changed only for a test (230a8df)⟩

## Commit messages (chronological)

- **LED.N064** LIMIT · `commit 3692a0a` — "asy_notification_service.py's active-window check doesn't
  handle a window that wraps past midnight ... left as-is per CLAUDE.md's legacy-verification rule" —
  Legacy-parity limitation. · tracked: SPECIFICATION.md:281 | related: LED.T* · [H17]
