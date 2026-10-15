# Harvest — XCUT: System-wide contracts

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`, moved to `4dc80ef` by V11).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: SETTLED 9, INVAR 34, MIRROR 3, LIMIT 5, RISK 13, ASSUME 12, PLATFORM 1, SUPPRESS 8, TODO 3, DRIFT 2, NOTE 6 — 96 items.


## src/asy_ntp_client.py

- **XCUT.N001** RISK · `src/asy_ntp_client.py:157, 217, 250 vs src/base_classes.py:198, 207` — wrn_s
  "network_available() callback failed:" wrnno=1 / "NTP reply unsynchronized or Kiss-of-Death" wrnno=2
  vs base "Sensor callback adds unknown keys" wrnno=1 / "config manager adds unknown keys" wrnno=2 —
  AsyNtpClient is a SensorReaderConfig, so both sets log onto the same NTP logger — contradicting
  SPECIFICATION.md:1907-1908 "No clash is live, since none shares a logger with a SensorReader" (same
  for NOTIFY's wrnno 1-4). Renumbering is owner-deferred to the next substantial change
  (SPECIFICATION.md:1908-1910). · related: XCUT.T07 · [H01]

## Cross-file (typing fallback sites)

- **XCUT.N002** SUPPRESS · `src/asy_bmp3xx_driver.py:25; src/asy_fram_driver.py:23; src/asy_fram_manager.py:20; src/asy_isl29125_driver.py:25; src/asy_neopixel_driver.py:18; src/asy_notification_service.py:18; src/asy_ntp_client.py:27; src/asy_scd30_driver.py:28; src/asy_sgp40_driver.py:27; src/asy_spi_driver.py:24`
  — "except ImportError: # typing has no runtime presence on MicroPython" — Same swallowed-ImportError
  idiom as `src/api_response.py:12`, one site per file (i2c/dns have none). · [H01]

## src/system_service.py

- **XCUT.N003** INVAR · `src/system_service.py:40` — "_RESET_DELAY = const(4) # seconds between reset
  command and execution (keep < watchdog timeout!)" — Relationship to the 8 s WDT
  (`buildgen/codegen.py`) kept by comment only; legacy was 5 s · covered-by: PAR.S04 · [H02]
- **XCUT.N004** INVAR · `src/system_service.py:44` — "_TASK_CHECK_TIME = const(2) # seconds period to
  check running tasks (keep << watchdog timeout!)" — Supervisor period vs WDT, by comment only; legacy
  was 3 s · covered-by: PAR.S04 · [H02]
- **XCUT.N005** ASSUME · `src/system_service.py:45-46` — "_TASK_FAIL_INCREMENT = const(100) # absolute
  value important for decrease time,... / _TASK_FAIL_MAX = const(300) # ...ratio important for
  triggering reset" — Score arithmetic (4th death within the decay window reboots; −1 per 2 s) stated,
  not derived · covered-by: XCUT.T02 · [H02]
- **XCUT.N006** SETTLED · `src/system_service.py:95-97` — "Set when _reboot()'s reset_timer can't be
  armed, so the supervisor loop stops feeding the watchdog and lets it reset us instead (one-way)." —
  Watchdog-starve fallback is intentional · related: XCUT.T13 · [H02]
- **XCUT.N007** INVAR · `src/system_service.py:112-114` — "The one reusable, no-op-safe watchdog access
  point (SPECIFICATION.md Part G.2): every feed site calls this" — Convention that all feed sites go
  through `feed_watchdog()` · related: XCUT.T03 · [H02]
- **XCUT.N008** RISK · `src/system_service.py:118-126` — "self.reset_timer.deinit() ...
  self.reset_timer.init(period=_RESET_DELAY * 1000, mode=Timer.ONE_SHOT" — Every call re-arms the
  ONE_SHOT reset (postponable) while FRAM stays paused · covered-by: XCUT.S03 · [H02]
- **XCUT.N009** SUPPRESS · `src/system_service.py:127-130` — "except (OSError, MemoryError) as e: #
  alarm-pool exhaustion (ENOMEM) - falls back to the same watchdog-starve backstop" — Print-only; only
  ENOMEM path covered, not a dropped ONE_SHOT callback · covered-by: XCUT.S02 · [H02]
- **XCUT.N010** SUPPRESS · `src/system_service.py:151-154` — "sync Timer-callback context (no event
  loop), so only pr.err() is usable, not the async err_s()" — Timer-starter failures are print-only ·
  related: XCUT.T04 · [H02]
- **XCUT.N011** RISK · `src/system_service.py:159` — "delay = int(_TIMER_BASE_PERIOD / (len(timers) +
  1))" — Stagger formula and latency accumulation · covered-by: XCUT.S06 · [H02]
- **XCUT.N012** SUPPRESS · `src/system_service.py:169-171` — "except (OSError, MemoryError) as e: #
  alarm-pool exhaustion (ENOMEM) - stop sequencing rather than leaving start_timers() waiting" —
  Remaining timers silently never start (print-only) · covered-by: XCUT.S05 · [H02]
- **XCUT.N013** SUPPRESS · `src/system_service.py:180-182` — "except Exception as e: # driver-supplied
  starter (get_task_starters()) - could legitimately misbehave ... errno=3" — Broad catch, persisted ·
  [H02]
- **XCUT.N014** SUPPRESS · `src/system_service.py:205-207` — "except (OSError, MemoryError) as e: #
  alarm-pool exhaustion (ENOMEM) - degrades gracefully rather than rebooting; only uptime/boot-signature
  stay unresolved this boot." — Print-only degraded mode · related: XCUT.T04 · [H02]
- **XCUT.N015** RISK · `src/system_service.py:238-240` — "\"Task ended - attempting restart, error
  counter increased to\", task_errors, wrnno=n + 1" — Dynamic wrnno varies by device/firmware and must
  stay ≤127 · covered-by: XCUT.S07 · [H02]
- **XCUT.N016** RISK · `src/system_service.py:248-253` — "self.reboot_system() / return" — Supervisor
  reboot: no config flush, feed only after a full scan, supervisor returns ~4 s before the reset ·
  covered-by: XCUT.S11 · [H02] ⟨quote not matched at the anchor⟩
- **XCUT.N017** SUPPRESS · `src/system_service.py:370-373` — "except (OSError, MemoryError) as e: #
  alarm-pool exhaustion (ENOMEM) - without the auto-unpause timer, storage would stay paused forever;
  safer to abort the pause" — Degraded: `mempause` silently not applied (print-only); ONE_SHOT unpause
  otherwise · covered-by: XCUT.S02 · [H02]

## ext/freezefs/ffsmount.py

- **XCUT.N018** SUPPRESS · `ext/freezefs/ffsmount.py:179-185` — "try: os.stat( target ) ... except: pass
  / if file_exists: raise OSError( errno.EEXIST )" — Bare except in vendored code; import-time EEXIST if
  `/html` exists on littlefs · covered-by: XCUT.S14 · [H02] ⟨quote not matched at the anchor⟩

## tests/_sensortask_scenarios.py

- **XCUT.N019** RISK · `tests/_sensortask_scenarios.py:1159-1161` — "a ResetErrors PUT can land on a
  stale chunk" — Part C.7 boot window where the webserver answers before FRAM loggers' setup(); scenario
  simulates it by setting the private `initialized=False` · related: XCUT.T08 · [H03]

## tests/test_asy_bmp3xx_driver.py

- **XCUT.N020** RISK · `tests/test_asy_bmp3xx_driver.py:1827-1829` — "this failure prints but is
  deliberately never recorded as a numbered error in the counter" — a timer-arming failure
  (ENOMEM/MemoryError) is print-only, never persisted or counted · related: XCUT.T04, XCUT.T24 · [H03]

## tests/test_asy_ntp_client.py

- **XCUT.N021** SETTLED · `tests/test_asy_ntp_client.py:1840-1842` — "matches every other supervised
  task in this codebase, which relies on the outer task-supervisor to notice and restart it, not a
  catch-all here" — an unexpected exception is allowed to kill asy_ntp_time(); recovery relies on
  system_service's supervisor · [H04]

## scripts/build_frozen_html.sh

- **XCUT.N022** RISK · `scripts/build_frozen_html.sh:17` — "mount_target=\"/html\"" — Generated module
  mounts at `/html` on import; freezefs raises EEXIST if `/html` exists on the device FS. · covered-by:
  XCUT.S14 · [H09]

## buildgen/codegen.py

- **XCUT.N023** RISK · `buildgen/codegen.py:381` — "lines.append(\" watchdog = WDT(timeout=8000)\")" —
  Hard-coded 8000 ms WDT (CLAUDE.md: fixed, never per-device) created before every constructor. ·
  covered-by: XCUT.S13 · [H09]
- **XCUT.N024** INVAR · `buildgen/codegen.py:441-443` — "fram must precede sysfunct ... The other order
  left CFGMGR_SYSTEM degrading every boot, 0ms against ~170ms" — Setup-order invariant with a single
  measurement. · related: XCUT.T01 · [H09]
- **XCUT.N025** INVAR · `buildgen/codegen.py:462-465` — "fed after every one-time setup() call, never
  inside a loop" — Watchdog feed placement; `setup()` return values are ignored. · related: XCUT.T01 ·
  [H09]
- **XCUT.N026** RISK · `buildgen/codegen.py:502-504` — "the accepted residual risk is power loss between
  response and write (Part F.2)" — Accepted risk for staged config writes. · related: XCUT.T10 · [H09]
- **XCUT.N027** RISK · `buildgen/codegen.py:703` — "f\"from {module} import main\\n\\n\"" — Import (and
  frozen_html mount) runs before any WDT exists. · covered-by: XCUT.S14 · [H09]

## tests_scripts/test_timer_stagger_no_coincidence.py

- **XCUT.N028** LIMIT · `tests_scripts/test_timer_stagger_no_coincidence.py:7,11-18` — "An exact replica
  of _timer_sequencer()'s arithmetic ... rather than the real recursive implementation" — Proof
  re-implements `1000 // (n+1)` and hand-copies `_TIMER_BASE_PERIOD`; the real sequencer is never read ·
  covered-by: TEST.S06 · [H10]
- **XCUT.N029** ASSUME · `tests_scripts/test_timer_stagger_no_coincidence.py:28-30,90-92` — "every real
  period being a whole-second multiple makes every pairwise gcd one too" — Proof holds only for
  software-counter sensors with whole-second trigger periods and offsets relative to one common start ·
  related: XCUT.S06 · [H10]

## SPECIFICATION.md Part A.2 (Architecture at a glance, 94-127)

- **XCUT.N030** DRIFT · `SPECIFICATION.md:123-125` — "once the score exceeds a threshold, the loop stops
  feeding the watchdog and lets it force a hard reset" — Supervisor text vs code's explicit reboot path.
  · covered-by: PAR.S04 · [H12]

## SPECIFICATION.md Part A.4 (Architecture — deep reference, 148-285)

- **XCUT.N031** ASSUME · `SPECIFICATION.md:195-198` — "`_reboot()` pauses permanent storage before
  resetting ... (measured 20/20 in the twin against the ~1-in-8 unpaused rate)" — Commanded reboot
  claimed lossless; supervisor/WDT paths differ. · related: XCUT.S01 · [H12]
- **XCUT.N032** INVAR · `SPECIFICATION.md:215-217` — "instantiation order is on-chip layout and must
  stay identical across firmware versions" — Bump allocator: any reorder silently misdecodes persisted
  data. · related: XCUT.T09 · [H12]
- **XCUT.N033** INVAR · `SPECIFICATION.md:218-225` — "every FRAM-chunk-owning object's construction must
  be deterministic across every system event ... Prove single, deterministic construction before adding
  any new FRAM-backed class." — Determinism rule by convention; buildgen emits top-level construction. ·
  related: XCUT.T09 · [H12]

## SPECIFICATION.md Part A.7 (wozi's construction order and dependency graph, 358-569)

- **XCUT.N034** MIRROR · `SPECIFICATION.md:360-365` — "reproducing the exact same construction
  order/FRAM chunk layout described below. This section stays the architectural reference" — Doc ↔
  `buildgen/codegen.py` output; no test ties this prose to the generator. · related: DOC.S09 · [H12]
- **XCUT.N035** LIMIT · `SPECIFICATION.md:381` — "`watchdog = WDT(timeout=8000)` — hardcoded, no
  injection point." — Fixed WDT timeout (cap 8388 ms); not configurable per device. · related: XCUT.S13
  · [H12]
- **XCUT.N036** MIRROR · `SPECIFICATION.md:394-460` — "FRAM chunk 1 ... chunk 16" — Hand-numbered chunk
  list must match generated construction; not machine-checked. · related: XCUT.T09 · [H12]
- **XCUT.N037** ASSUME · `SPECIFICATION.md:414-415` — "`wozi` is never physically flashed (CLAUDE.md),
  so reordering carries no deployed-data-loss risk" — Holds for wozi only; the same generator emits the
  other five devices' layouts. · related: PAR.S13 · [H12]
- **XCUT.N038** INVAR · `SPECIFICATION.md:463-464` — "One hard constraint: `notification.setup()` needs
  `finalize()` (step 12) already run" — Ordering constraint satisfied by batching at the end. · [H12]
- **XCUT.N039** INVAR · `SPECIFICATION.md:467-472` — "`sysfunct.feed_watchdog()` follows every single
  call in this batch (WP6) — a one-time, boot-only, non-looping feed site" — Must never become a looping
  feed. · related: XCUT.T01 · [H12]
- **XCUT.N040** ASSUME · `SPECIFICATION.md:473-474` — "wozi's own 16 `PrintLogHistoryStore` chunks plus
  1 timestamped chunk" — Dated count (dev: 21 per C.7). · covered-by: DOC.T08 · [H12]
- **XCUT.N041** INVAR · `SPECIFICATION.md:480-482` — "must stay in this relative order. `src/` has no
  earlier on-chip layout to preserve." — Layout freeze from now on; assumes no legacy layout matters
  (legacy chunk 0 does, PAR.S09). · related: PAR.S09 · [H12]
- **XCUT.N042** LIMIT · `SPECIFICATION.md:482-485` — "A device with no `[device.wiring].fram_target`
  keeps `conn`/`ntp`/`sysfunct`/`webserver` RAM-only" — Evidence loss for those modules on a FRAM-less
  device. · [H12]
- **XCUT.N043** INVAR · `SPECIFICATION.md:565-571` — "`asy_sgp40_driver.py` needs no static import of
  `asy_scd30_driver` ... the object graph is still a clean DAG" — No-cross-driver-import and DAG claims;
  not machine-checked. · related: XCUT.T16 · [H12]

## SPECIFICATION.md Part C.4 (Layer 3 Reader, 1624-1697)

- **XCUT.N044** MIRROR · `SPECIFICATION.md:1657-1660` — "Each one costs `system_service.py`'s
  `_TASK_FAIL_INCREMENT` (100) against a `_TASK_FAIL_MAX` of 300 that decays by only 1 per clean
  supervisor pass ... about three restarts" — Doc restates `src/system_service.py:45-46` constants. ·
  related: XCUT.T02 · [H12]

## SPECIFICATION.md Part C.7 (Error handling & logging contract, 1807-1891)

- **XCUT.N045** INVAR · `SPECIFICATION.md:1871-1876` — "`base_classes.py` reserves
  `errno=1`-`9`/`wrnno=1`-`2` ... a driver's own numbering starts at 10+" — Numbering convention,
  explicitly unenforced (C.7.1:1896-1899). · covered-by: XCUT.T07 · [H12]
- **XCUT.N046** LIMIT · `SPECIFICATION.md:1876-1878` — "A driver with no fixed, enumerable error-source
  list may assign numbers dynamically (`system_service.py`'s task-supervisor `wrnno=n + 1`)" — Persisted
  W-codes not stable across devices/versions. · covered-by: XCUT.S07 · [H12]

## SPECIFICATION.md Part C.7.1 (Running errno/wrnno table, 1893-1941)

- **XCUT.N047** INVAR · `SPECIFICATION.md:1900-1904` — "a convention this table records, not one the
  code itself enforces — nothing raises if a new module picks a colliding number or starts below 10" —
  Explicitly unenforced catalogue. · covered-by: XCUT.T07 · [H12]
- **XCUT.N048** TODO · `SPECIFICATION.md:1904-1910` — "Seven modules still number inside the reserved
  range ... Each is renumbered to 10+ on its next substantial change, not in one pass (owner decision,
  2026-09-24)" — Deferred renumbering (config_manager, system_service, webserver, captive_dns, wifi,
  ntp, notification wrnno). · related: XCUT.T07 · [H12]
- **XCUT.N049** ASSUME · `SPECIFICATION.md:1907-1908` — "No clash is live, since none shares a logger
  with a `SensorReader`." — Clash-freedom premise. · [H12]
- **XCUT.N050** SETTLED · `SPECIFICATION.md:1912-1925` — "A history is a bounded ring (ten slots per
  logger) ... the three answers differ on purpose" — Per-module episode definitions for `repeat=True`
  (UART one per episode; WiFi/FRAM one per distinct code). · related: UART.T04 · [H12]
- **XCUT.N051** INVAR · `SPECIFICATION.md:1933, 1935, 1936` — "12 is retired, not reused" / "19 is
  retired, not reused" / "20 is retired, not reused" — Retired codes (ISL wrnno 12, WIFI errno 19, NTP
  errno 20) must never be reassigned; no guard. · related: XCUT.T07 · [H12]

## SPECIFICATION.md Part C.7.2 (Which failures may end a task, 1943-1973)

- **XCUT.N052** INVAR · `SPECIFICATION.md:1949-1953` — "A task ends — and the supervisor restarts it —
  only when the restart re-initialises something real" — Task-ending rule by convention. · related:
  XCUT.T02 · [H12]
- **XCUT.N053** SETTLED · `SPECIFICATION.md:1971-1975` — "Out of scope (owner, 2026-09-24): hardware
  that is inoperational from the start. Everything assumes defect-free hardware and a device config that
  matches it." — Init-failure reboot path excluded from C.7.2. · related: SENS.T14 · [H12]

## SPECIFICATION.md Part C.8 (Concurrency & locking model, 2016-2188)

- **XCUT.N054** INVAR · `SPECIFICATION.md:2032-2034` — "Lock ordering is fixed: always 2 before 1 —
  audited across every driver with no violation" — Audit claim; no mechanical guard. · related: XCUT.T06
  · [H12]

## SPECIFICATION.md Part C.9 (Timer/task/IRQ integration contract, 2190-2209)

- **XCUT.N055** LIMIT · `SPECIFICATION.md:2201-2204` — "a task tied to a runtime mode transition
  (`asy_wifi_service.py`'s hotspot-mode DNS server task) is deliberately outside this generic
  supervision, a legitimate opt-out" — Unsupervised task by design. · covered-by: XCUT.T05 · [H12]
- **XCUT.N056** INVAR · `SPECIFICATION.md:2206-2208` — "(default soft, no `hard=True` anywhere) whose
  callback only calls `.set()` on an `asyncio.ThreadSafeFlag` — never `time.sleep()` or business logic
  inside a callback" — Review-only rule; no lint guard found. · related: XCUT.T04 · [H12]
- **XCUT.N057** INVAR · `SPECIFICATION.md:2208-2211` — "Use `Timer.PERIODIC`, not `ONE_SHOT`, for
  anything that must keep firing — a soft callback can be silently dropped" — ONE_SHOT used on critical
  paths per seed. · covered-by: XCUT.S02 · [H12]
- **XCUT.N058** INVAR · `SPECIFICATION.md:2214-2217` — "Every `Timer.init()` failure handler catches
  `except (OSError, MemoryError) as e:`, not bare `OSError`" — Handler shape convention. · related:
  XCUT.T04 · [H12]

## SPECIFICATION.md Part C.9.1 (Read-trigger timer stagger, 2211-2298)

- **XCUT.N059** SETTLED · `SPECIFICATION.md:2221-2232` — "Design intent (owner-established, not
  re-derived here) ... The one-second total spread is load-bearing and must not become a fixed per-task
  gap or be rescaled" — Owner design; do not re-propose. · [H12]
- **XCUT.N060** ASSUME · `SPECIFICATION.md:2259-2267` — "never repeated - integer division of 1000 by up
  to a handful of distinct small divisors doesn't coincide in practice either, and even a tie would only
  delay, never invalidate, the argument" — Proof assumptions; seed disputes offsets (first at 0,
  accumulated latency, SCD30 500 ms collisions). · covered-by: XCUT.S06 · [H12]
- **XCUT.N061** RISK · `SPECIFICATION.md:2234-2235` — "starts each `get_timer_starters()` entry via a
  chain of `Timer.ONE_SHOT` callbacks" — The stagger itself rides soft ONE_SHOT callbacks that C.9 says
  can be dropped. · covered-by: XCUT.S05 · [H12]

## SPECIFICATION.md Part C.13 (Readiness-gate scheme, 2363-2378)

- **XCUT.N062** INVAR · `SPECIFICATION.md:2381-2386` — "The response to \"called before `setup()` ran\"
  must match the class's already-declared raise/never-raise contract — verify per class, don't assume" —
  Per-class obligation. · covered-by: XCUT.T12 · [H12]

## SPECIFICATION.md Part C.14.2 (The `_WIRING` convention, 2430-2532)

- **XCUT.N063** ASSUME · `SPECIFICATION.md:2514-2518` — "a real, deliberate reordering of wozi's FRAM
  chunk allocation order, safe only because wozi is never physically flashed (CLAUDE.md)" — Safety
  premise specific to wozi. · related: PAR.S13 · [H12]
- **XCUT.N064** INVAR · `SPECIFICATION.md:2525-2536` — "every `*_Reader` constructs its namedtuple with
  every field `None` before any real read ... Every direct-reference consumer tolerates that as a
  normal, expected input" — Producer/consumer initial-value contract. · related: XCUT.T17 · [H12]
- **XCUT.N065** ASSUME · `SPECIFICATION.md:2538-2540` — "a full audit for the same class of bug ...
  found no other occurrence in `src/`" — Dated (2026-09-12) negative audit claim. · [H12]

## SPECIFICATION.md Part C.14.3 (Error-source and logger fan-in, 2534-2572)

- **XCUT.N066** INVAR · `SPECIFICATION.md:2544-2553` — "implements `get_error_sources(self) -> list[Any]`
  and `get_loggers(self) -> list[PrintLogHistory]`, structurally (duck-typed" — Duck-typed fan-in
  contract; no Protocol check at wiring time. · related: XCUT.T08 · [H12]

## SPECIFICATION.md Part D (src/ Production-Quality Checklist, 2576-2728)

- **XCUT.N067** INVAR · `SPECIFICATION.md:2601-2602` — "If verification surfaces a discrepancy, do not
  silently change it — flag and ask before altering real output." — Owner rule for formula/behaviour
  discrepancies; review-only. · [H12]
- **XCUT.N068** RISK · `SPECIFICATION.md:2614-2616` — "Don't defend against out-of-contract input at
  runtime if static typing already enforces it (mypy)" — Premise holds only where no untyped runtime
  input (JSON, TOML, restored FRAM state) can reach the function. · related: ALGO.T05 · [H12]
- **XCUT.N069** INVAR · `SPECIFICATION.md:2661-2663` — "mypy catches most of this — still read every
  `return` by eye" — Review-only. (low) · [H12]
- **XCUT.N070** INVAR · `SPECIFICATION.md:2667-2669` — "observable behavior stays identical for every
  valid input — a hard constraint, the full test suite must still pass unchanged" — Improvement-pass
  constraint. · [H12]
- **XCUT.N071** INVAR · `SPECIFICATION.md:2682-2688` — "Give every member of a related set the same
  shape ... flag a questionable existing convention rather than silently diverging. An ongoing,
  project-wide check." — D.10 review obligation. · related: XCUT.T15 · [H12]

## SPECIFICATION.md Part F.1 — Core platform facts

- **XCUT.N072** SETTLED · `SPECIFICATION.md:3447-3452` — "**Dynamic imports (`__import__`, `importlib`)
  must never be used anywhere in this codebase** — project owner's explicit, standing rule" — Owner
  rule, justified by a future static frozen-module selector; no mechanical check is named here. ·
  related: XCUT.T16 · [H13]
- **XCUT.N073** INVAR · `SPECIFICATION.md:3447-3452` — "Every import stays a real, static `import`/`from ... import`
  statement, AST-scannable" — Rule upheld by convention; this Part names no lint/test that enforces it.
  · related: XCUT.T16, GEN.T05 · [H13]
- **XCUT.N074** INVAR · `SPECIFICATION.md:3457-3459` — "every timer that must fire uses `PERIODIC`
  (C.9), the WiFi hotspot shutoff included (stopped by `reconnect_wifi()` on its first delivered fire)"
  — Convention-only rule; the plan already records ONE_SHOT timers on critical paths contradicting it. ·
  covered-by: XCUT.S02 · [H13]
- **XCUT.N075** SETTLED · `SPECIFICATION.md:3459-3462` — "A software-timeout mitigation for this was
  considered and rejected ... don't re-propose without a materially different justification" —
  Do-not-reopen marker for dropped-soft-callback mitigation. · covered-by: XCUT.T22 · [H13]
- **XCUT.N076** ASSUME · `SPECIFICATION.md:3584-3590` — "**Every measurement source is gated at the
  driver, not in the response layer** (audited 2026-09-24)" — Dated audit claim listing BMP3xx,
  ISL29125, SGP40, math_helpers, `ema_step()`, SCD30; the plan says "Only SCD30 checks `isfinite`". ·
  covered-by: XCUT.T23 · [H13]

## SPECIFICATION.md Part F.2 — Blocking calls / timeout-wrapping

- **XCUT.N077** TODO · `SPECIFICATION.md:3606-3607` — "Calls that genuinely *can* be timeout-wrapped
  (FRAM SPI, `asy_udp_socket.py`'s `select.poll`-driven `ready()`) should standardize on one mechanism."
  — Standing, undated to-do; no owner or tracking item named. · [H13]

## SPECIFICATION.md Part F.3 — Long-blocking operations

- **XCUT.N078** SETTLED · `SPECIFICATION.md:3659-3662` — "The `get_long_block_lock()` shared-lock
  mechanism has been retired ... not a resurrection of the old lock" — Do-not-resurrect marker. · [H13]

## SPECIFICATION.md Part G.0-G.1 — Shared primitive reuse rule

- **XCUT.N079** INVAR · `SPECIFICATION.md:4158-4165` — "Search G.2, then the wider codebase, for an
  existing primitive ... never reimplement even a version that looks locally simpler ... add it to G.2
  in the same change" — Review-only discovery procedure. · covered-by: XCUT.T15 · [H13]

## SPECIFICATION.md Part G.3 — Re-validation

- **XCUT.N080** INVAR · `SPECIFICATION.md:4263-4268` — "grep the whole tree for the *shape* of each G.2
  primitive's problem ... A periodic, ongoing check, not a one-time pass" — Review-only recurring
  obligation; findings are flag-and-discuss. · covered-by: XCUT.T15 · [H13]

## SPECIFICATION.md Part K (intro) and K.1 — Before writing code

- **XCUT.N081** INVAR · `SPECIFICATION.md:5715-5719` — "Check Part G's shared-primitive catalog before
  writing anything new ... website-facing needs its `src/`↔`js/` mirror obligation honored too (Part
  G.3)" — Restates G.1/G.3 obligations per promotion. · covered-by: XCUT.T15 · [H13]

## SPECIFICATION.md Part L.2 — Core design decisions

- **XCUT.N082** ASSUME · `SPECIFICATION.md:6083-6085` — "every producer's locked-value holder has a
  safe, defined initial value at construction and every consumer treats that \"not yet measured\" state
  as normal" — Convention across all producers/consumers; not mechanically checked. · related: XCUT.T17
  · [H13]

## SPECIFICATION.md Part L.4 — Generator pipeline

- **XCUT.N083** DRIFT · `SPECIFICATION.md:6301-6303 vs 3439-3444` —
  "`digital_twin/run_generic_integration.py` boots any `sensortask_<device>` module ... resolving it via
  `__import__(--module)`" — F.1 forbids `__import__`/`importlib` "anywhere in this codebase"; sites:
  `digital_twin/run_generic_integration.py:356`, `tests/_sensortask_scenarios.py:127`,
  `tests/_webserver_concurrency_scenarios.py:100`, `tests/_digital_twin_construction_scenarios.py:98`,
  `tests/_boot_contiguity_probe.py:125`, `tests/test_asy_isl29125_driver.py:1301, 1306`,
  `buildgen/validate.py:6, 194-197`. · related: XCUT.T16 · [H13]

## CLAUDE.md

- **XCUT.N084** INVAR · `CLAUDE.md:68-72` — "SPECIFICATION.md Part D is the full checklist ... apply it
  to every file that makes this move" — The promotion bar is enforced by review only. Generated
  `sensortask_<device>.py` is frozen firmware that never "moves into src/", so Part D review never
  reaches it. · related: XCUT.T14 · [H14]
- **XCUT.N085** INVAR · `CLAUDE.md:78-88` — "Whenever a new file is added to `src/`, run a
  bird's-eye-view scan over the whole content of `src/`" — Covers D.9/D.10, the Part G catalogue and the
  G.3 grep-for-shape check. Convention only; no tool runs it. · covered-by: XCUT.T15 · [H14]
- **XCUT.N086** INVAR · `CLAUDE.md:215-218` — "approaching the hardware watchdog's own timeout while the
  one-time boot `setup()` batch runs, which is what `SystemService.feed_watchdog()` exists to prevent" —
  Relies on feeds between setup units. The worst-case gap is never computed or tested. · covered-by:
  XCUT.T01 · [H14]
- **XCUT.N087** ASSUME · `CLAUDE.md:627-628` — "its ~18 independently-`create_task()`-spawned sibling
  tasks" — Approximate count. · related: XCUT.T05 · [H14]

## README.md

- **XCUT.N088** PLATFORM · `README.md:17-20` — "active (8000ms)" — The watchdog is configured at 8000 ms
  against the 8388 ms rp2 cap; every feed-gap budget is measured against it. · related: XCUT.T03 · [H14]

## BACKLOG.md

- **XCUT.N089** TODO · `BACKLOG.md:58-67` — "No standardized timeout/cancellation mechanism yet ...
  PRIORITIZED (project owner, 2026-09-11): to be done soon" — Unnumbered, owner-PRIORITISED refactor:
  FRAM SPI transactions and `asy_udp_socket.py` `ready()`/`write_and_recvfrom()` each use a bespoke
  timeout approach; one consistent mechanism wanted "ahead of the other items". No plan topic names this
  work item. Status: open. · related: XCUT.T19 · [H15]

## Commit messages (chronological)

- **XCUT.N090** SETTLED · `commit b5502c8` — "don't guard against inputs violating their
  already-declared types ... every caller in this codebase is our own code, type-checked and reviewed" —
  Owner rule: guard only NaN/inf-class failures of correctly-typed values. · tracked:
  SPECIFICATION.md:2614 ("Don't defend ...") | - · [H17]
- **XCUT.N091** NOTE(OWNER-DECISION LOST) · `commit 9f4c084 -> 41762dc -> 080cde3 -> merge e5d2c43` —
  41762dc: "The reorder itself is a decided task now ... moves ... into 'Refactor targets not yet done'
  at high priority, naming all eleven non-compliant classes" and amends D.15's comment clause ("comments
  move with the code they annotate") — The HIGH-PRIORITY BACKLOG item "Sort every class in src/ to D.15"
  and the D.15 amendment were added on main, then silently dropped when merge e5d2c43 took this branch's
  side on all 36 conflicts; neither text exists at 2a88cc8 (SPEC D.15 at :2717 still says "no change to
  any ... comment"). An AST check at 2a88cc8 finds 9 classes still non-compliant (SCD30_Reader,
  UART_Comm, UART, _ModuleLike, AsyConnTime, ConfigManager, Framing_Base, Framing_COBS, SystemService).
  · UNTRACKED | related: XCUT.T* · [H17]
- **XCUT.N092** NOTE(OWNER-PRINCIPLE) · `commit 8a45060` — "Project owner's direction: this is a general
  principle - no error/warning should ever be logged for expected startup jitter on any boot, on any
  module - to be addressed, and audited for elsewhere in the codebase, in a dedicated follow-up session"
  — 7727ad1 fixed SGP40 and audited only the narrower "None vs exception" class; the general
  no-startup-jitter-logging principle is not written as a standing rule in CLAUDE.md/SPEC
  (SPEC:2526-2532 records only the SGP40 fix), and the owner's grace-period idea was never decided or
  recorded. · UNTRACKED (principle) | related: SENS.T* · [H17]
- **XCUT.N093** NOTE(FLAG) · `commit a7f7291` — "Five surfaced; all five are in BACKLOG as open question
  17, unfixed" (FiltCoeff two meanings, four trigger-event names, ThreadSafeFlag import, _N_*_CFG axes,
  return-annotation quoting) — Cross-file consistency. · status: done-in 58abf8f (owner's four
  consistency decisions; FiltCoeff settled-keep) | - · [H17]
- **XCUT.N094** NOTE(FLAG) · `commit 4303242 / 38a1753 / 7e0d507` — "seven classes elsewhere in src/ do
  not satisfy D.15" -> "eleven of 74" — See the "OWNER-DECISION LOST" D.15 item above (41762dc owner
  ruling later dropped in merge e5d2c43). · UNTRACKED (same item as 41762dc) | - · [H17]
- **XCUT.N095** NOTE(SCOPE-MARKER LOST) · `commit 179a10c` — "BACKLOG 17's five cross-file consistency
  findings, 25's reserved-range errno/wrnno audit, 26's unreachable UART wrnno 11, and the src/-wide
  D.15 reorder - each now carry the same marker ... 'Independent session - out of the ISL29125'" — Three
  of four later done (58abf8f, b0f755c); the D.15 reorder has no BACKLOG entry at 2a88cc8 (marker grep
  finds nothing). · UNTRACKED (D.15 reorder; same as 41762dc item) | - · [H17]
- **XCUT.N096** NOTE(OWNER-RULES) · `commit 9894e85` — "external sources are always fair game ... no
  working around a failing test (adapt a test only with a solid, specific justification), and keep
  BACKLOG.md updated with any unrelated issues or CI failures found along the way" — Standing
  implementation rules for WP1-WP8; not in CLAUDE.md verbatim. · status: largely reflected in CLAUDE.md
  working agreements; "keep BACKLOG updated with unrelated CI failures" not stated there (low) | - ·
  [H17]
