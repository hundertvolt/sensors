# Harvest H12 — SPECIFICATION.md lines 1-3421 (front matter, Parts A–E) (snapshot 2a88cc8)

Grouped by Part/subsection (partition note). All anchors are `SPECIFICATION.md:<line>` at 2a88cc8
unless another path is named. Undefined work-package labels (`WP1`-`WP8`) and `Session N` labels are
recorded once each where first material, not at every occurrence.

## SPECIFICATION.md front matter (1-28)
- DRIFT | SPECIFICATION.md:6-7 | "CLAUDE.md (AI-session operating constraints — hard rules, working agreements, PR workflow, pre-push verification" | Calls the chroot check "pre-push verification", but CLAUDE.md (owner, 2026-09-18) made it a periodic owner-run check, not a push gate. | area: DOC | covered-by: DOC.S08
- SETTLED | SPECIFICATION.md:6-9 | "Not here, by design: CLAUDE.md ... and BACKLOG.md (active working memory" | Doc-placement decision: rules stay in CLAUDE.md, open work in BACKLOG.md, never folded into the spec. | area: DOC | related: DOC.T06

## SPECIFICATION.md Part A.1 (Repository layout, 29-92)
- SETTLED | SPECIFICATION.md:36-39 | "arduino/ ... Outside this project's scope (owner, 2026-09-24): no lint/type/test, no reconciliation" | Owner decision placing the C peer entirely out of scope. | area: DOC | related: LIC.T04
- LIMIT | SPECIFICATION.md:40-41 | "a 2026-08-27 snapshot of its on-device filesystem (reference only, in no lint/type/test scope)" | Dated bench-filesystem snapshot used as reference; ages silently. | area: HW | related: HW.S20
- ASSUME | SPECIFICATION.md:42-44 | "Legacy, still-deployed ... superseded by html/ for devices the refactor has reached (H.1)" | Which devices the refactor has "reached" is unstated; deployed units still run html_raw. | area: PAR | related: PAR.T10
- DRIFT | SPECIFICATION.md:47-49 | "sensortask-{arzi,dev,neu,wozi}.py per-device app" | Legacy has 4 device apps (incl. `neu`), refactor has 6 TOMLs; the neu→klkizi/grkizi/schlafzi mapping is not stated here. (low) | area: PAR | related: PAR.T02
- LIMIT | SPECIFICATION.md:88 | "update_and_install.txt Legacy manual toolchain recipe, superseded by toolchain/ (kept for reference)" | A kept-but-superseded recipe; can drift from toolchain/. | area: DOC | related: DOC.S15
- DRIFT | SPECIFICATION.md:90 | "scripts/ lint.sh/typecheck.sh/test.sh, build_frozen_html.sh, run_unix_port_integration.sh" | Layout lists 5 of ~20 scripts (build_firmware.py, build_website.sh, twin/hardware runners omitted). (low) | area: DOC | -

## SPECIFICATION.md Part A.2 (Architecture at a glance, 94-127)
- RISK | SPECIFICATION.md:102-104 | "self-heals corruption by overwriting the entire file with hardcoded defaults (data-loss risk on firmware upgrades that add keys — BACKLOG.md)" | Deployed ConfigManager's known data-loss risk; relevant to reflash migration. | area: PAR | related: PAR.S08
- ASSUME | SPECIFICATION.md:112-113 | "every real device — confirmed against all 6 `devices/*.toml`, each declaring a `driver = \"fram\"` instance" | Count-dependent claim (6 TOMLs, each with FRAM); goes stale with a new device. | area: GEN | -
- DRIFT | SPECIFICATION.md:114-115 | "Used today for SGP40's VOC baseline backup." | Understates FRAM use: since WP1-WP3 every FRAM-wired logger/cfgmgr owns a chunk (A.7 lists 16-21). | area: STOR | related: XCUT.S09
- DRIFT | SPECIFICATION.md:123-125 | "once the score exceeds a threshold, the loop stops feeding the watchdog and lets it force a hard reset" | Supervisor text vs code's explicit reboot path. | area: XCUT | covered-by: PAR.S04
- DRIFT | SPECIFICATION.md:123 | "Task supervisor (`main()` in every `sensortask-*.py`)" | Names the legacy files; refactor supervisor is `system_service.py` called from generated modules. (low) | area: DOC | related: DOC.S09
- DRIFT | SPECIFICATION.md:125 | "Units run years unattended." | CLAUDE.md's WP6 rule says "months between reboots"; inconsistent lifetime claims. (low) | area: DOC | -

## SPECIFICATION.md Part A.3 (Refactor status, 129-146)
- DRIFT | SPECIFICATION.md:131-134 | "the still-uncovered path is the legacy `python/`+`build-*.sh` pipeline, BACKLOG.md" | Frames legacy CI coverage as open work; CLAUDE.md says the legacy tree never gets work ("the gap is the decision"). | area: DOC | covered-by: DOC.S21
- DRIFT | SPECIFICATION.md:131-133 | "ruff, mypy, shellcheck, actionlint and zizmor each as their own stage, plus unit-tests, digital-twin-e2e and a real `firmware.uf2` build" | Stage list omits unit-tests-gc-threshold, unit-tests-coverage and the web tier (B.10 lists 15 jobs). (low) | area: CI | -
- SETTLED | SPECIFICATION.md:142-145 | "`wozi` deliberately does not, since it is never physically flashed and would otherwise carry an untestable peripheral" | UART pair on dev only, never wozi. | area: UART | related: PAR.S13
- SETTLED | SPECIFICATION.md:145-146 | "Goal throughout: same top-level features as today's deployed units, not a feature change." | Parity goal the PAR area audits against. | area: PAR | related: PAR.T01

## SPECIFICATION.md Part A.4 (Architecture — deep reference, 148-285)
- SETTLED | SPECIFICATION.md:152-155 | "exposes `get_long_block_lock()` ... `src/` splits this ... and retires the lock (F.2)" | Retired legacy lock; must not be reintroduced. | area: PAR | -
- INVAR | SPECIFICATION.md:159-161 | "`import async_manager` silently resolves to whichever file defines that name — always import by name from `config_manager`/`base_classes`, never `async_manager`" | Import-hygiene rule for the flat frozen namespace; no lint/test guard found (grep of scripts/tests/src/buildgen). | area: CORE | -
- RISK | SPECIFICATION.md:161-163 | "a read can't detect on-disk corruption after that, and `write_config()` silently repairs an externally-corrupted file from the cache (accepted: this device is the file's only writer)" | Accepted: in-RAM cache wins over disk; premise "only writer" (mpremote/manual edits, tests) is an assumption. | area: CORE | related: CORE.T01
- SETTLED | SPECIFICATION.md:163-165 | "`NeopixelDriver` is the one deliberate exception to \"every module owns a schema\" (no schema at all, confirmed by the project owner)" | Owner-confirmed schema exception. | area: LED | -
- INVAR | SPECIFICATION.md:170-178 | "The byte-level path is synchronous under a caller-held lock (2026-09-18 restructure, wire-identical)" | FRAM command bodies must never await while holding driver+bus lock; blocking 2 us CS settle; "wire-identical" is a claim. | area: STOR | related: STOR.T04
- ASSUME | SPECIFICATION.md:174-175 | "Every `errno`/`wrnno` keeps its number and meaning; only the logging site moved up." | Claim after the sync restructure; C.7.1's FRAM row vs code already disputed. | area: STOR | related: STOR.S04
- PLATFORM | SPECIFICATION.md:178-181 | "MB85RS64V reads are destructive internally ... \"as an FRAM memory operates with destructive readout mechanism\"" | Datasheet fact driving the busy/idle-on-read design; power loss mid-read is a real risk. | area: STOR | related: STOR.T10
- SETTLED | SPECIFICATION.md:182-188 | "an interruption hitting *both* copies makes every later read fail the status check (errno 31) ... don't \"fix\" it" | Chunk stays unreadable until rewritten, by design; pinned by `tests/test_asy_fram_manager.py` test named at :187-188. | area: STOR | related: STOR.S01
- RISK | SPECIFICATION.md:189-195 | "an abrupt reset mid-write loses that module's whole persisted error history ... That is accepted" | Owner decision 2026-09-11: evidence loss on abrupt reset accepted; twin-measured ~1 in 8. | area: STOR | related: CORE.T11
- ASSUME | SPECIFICATION.md:192 | "Measured in the digital twin at roughly 1 abrupt restart in 8." | Single twin measurement, no silicon rate. | area: STOR | -
- INVAR | SPECIFICATION.md:193-195 | "the invariant that must hold instead is that the loss is *all-or-nothing*, never a partial or garbled restore" | Stated invariant; tested per :198-200 (mock/twin/flash). | area: STOR | related: STOR.T12
- ASSUME | SPECIFICATION.md:195-198 | "`_reboot()` pauses permanent storage before resetting ... (measured 20/20 in the twin against the ~1-in-8 unpaused rate)" | Commanded reboot claimed lossless; supervisor/WDT paths differ. | area: XCUT | related: XCUT.S01
- SETTLED | SPECIFICATION.md:201-205 | "Write protection gates reads too, and that is intended (project owner, 2026-09-11)" | WP chip makes `chunk.read()` return None — an access gate, not data loss. | area: STOR | related: STOR.T03
- LIMIT | SPECIFICATION.md:209-213 | "every tier's write check stops at the driver's own guard ... Both chip fakes stop at the driver guard and cannot prove this." | Only the flash tier proves BP0|BP1 refusal; mock/twin fakes cannot. | area: TWIN | related: HW.S07
- SETTLED | SPECIFICATION.md:214 | "\"Both copies valid but different\" is a hard failure (no generation counter), never guessed." | Design decision: no generation counter. | area: STOR | related: STOR.T02
- INVAR | SPECIFICATION.md:214-215 | "return `(ntp_synced, utc, success)` — `success` is third, not first; don't reorder." | Return-order contract upheld by caller discipline. | area: STOR | related: STOR.T06
- INVAR | SPECIFICATION.md:215-217 | "instantiation order is on-chip layout and must stay identical across firmware versions" | Bump allocator: any reorder silently misdecodes persisted data. | area: XCUT | related: XCUT.T09
- INVAR | SPECIFICATION.md:218-225 | "every FRAM-chunk-owning object's construction must be deterministic across every system event ... Prove single, deterministic construction before adding any new FRAM-backed class." | Determinism rule by convention; buildgen emits top-level construction. | area: XCUT | related: XCUT.T09
- DRIFT | SPECIFICATION.md:221-224 | "every current FRAM-chunk-owning construction (`sysfunct`, `sgp40`'s VOC chunk, `neopixel`, `notification`) is unconditional top-level" | List predates WP1-WP3: conn/ntp/DNSServer/webserver/cfgmgr/uart_link/isl29125 chunks omitted. | area: DOC | related: XCUT.S09
- ASSUME | SPECIFICATION.md:228-230 | "Margin is ample (FRAM at 1MHz, 8KB chip ... low single-digit ms, three orders of magnitude under both the 4s reset delay and the ~8s watchdog-starve wait)" | Timing margin asserted from arithmetic, not measured here; C.7 later measures ~305 ms per chunk (yielding). | area: PERF | related: XCUT.T03
- DRIFT | SPECIFICATION.md:230-236 | "Its `WDT()`-site half is now permanently vacuous" | A permanently vacuous half remains in `tests/test_reset_call_site_invariant.py`; invariant moved to `tests_scripts/test_buildgen_generate.py::test_real_device_constructs_watchdog_exactly_once`. | area: TEST | covered-by: TEST.S17
- SETTLED | SPECIFICATION.md:237-240 | "SCD30's `AmbPres` is stored in the sensor's own NVM ... hence a static config value even on wozi ... Confirmed deliberate by the project owner." | Owner-confirmed; `force=True` resend doubles as resume-measurement command. | area: SENS | related: SENS.T09
- SETTLED | SPECIFICATION.md:241-242 | "SCD30's `ForceCalRef` recalibration is manual ... No automation planned." | No FRC automation. | area: SENS | related: SENS.T13
- LIMIT | SPECIFICATION.md:243-245 | "`set_temperature_offset()` sends `int(offset * 100)` — a genuine truncation ... silently truncated by the chip, not rejected" | Silent truncation; text attributes it to "the chip" though `int()` in the driver truncates. | area: SENS | covered-by: SENS.S09
- PLATFORM | SPECIFICATION.md:246-251 | "45 sampling intervals must elapse before the index moves off 0 ... a *higher* raw tick count reads as *cleaner* air" | Sensirion VOC semantics depended on; reference C source not in repo. | area: ALGO | related: SENS.S04
- INVAR | SPECIFICATION.md:253-254 | "`request_signal()` returns once queued, not once its ramp finishes" | Neopixel API contract (disputed by LED seeds). | area: LED | related: LED.S01
- INVAR | SPECIFICATION.md:258-262 | "`finalize()` (sync, once) builds the combined schema ... Rejections during the sync `register()`/`finalize()` window are buffered and drained by `monitor_loop()`" | Staged-construction contract for NotificationCoordinator. | area: LED | related: LED.T03
- SETTLED | SPECIFICATION.md:263-265 | "Config field names drop the \"Led\" prefix everywhere ... a deliberate wire-format change; only legacy `html_raw/` isn't updated (accepted debt, H.1)" | Wire change deliberate; legacy UI incompatible by accepted debt. | area: PAR | related: PAR.S06
- SETTLED | SPECIFICATION.md:269-285 | "Functional behaviors confirmed intentional by the project owner — don't \"fix\" these" | Do-not-reopen list (LED sequencing, BackupPeriod/BackupMaxAge 0=disabled, permanent WiFi deactivation, no STA→hotspot after first success, raw-number UI, SGP40 skip without SCD30 comp, no UART flow control, no midnight-wrap window, SCD30 AmbPres readback). | area: PAR | covered-by: PAR.T03
- DRIFT | SPECIFICATION.md:278-279 | "FRAM's 8KB has ample headroom over SGP40's ~250-byte usage" | Headroom claim predates the 16-21 logger/cfgmgr chunks now sharing the chip. | area: STOR | covered-by: XCUT.S09
- LIMIT | SPECIFICATION.md:280-283 | "active-window check doesn't handle a window wrapping past midnight (`OnH=22`/`OffH=6` silently never triggers)" | Settled limitation; silent non-trigger. | area: LED | related: PAR.T03
- ASSUME | SPECIFICATION.md:283-285 | "`get_ambient_pressure()` reuses the same command word used to *set* it ... even though neither Sensirion reference driver documents that command as readable" | Undocumented readback relied on (legacy-proven). | area: SENS | covered-by: SENS.T09

## SPECIFICATION.md Part A.5 (Microdot / REST layer, 287-335)
- ASSUME | SPECIFICATION.md:291-293 | "Upstream v2.7.0 (checked 2026-09-23) changes only f-strings, a `QUERY` decorator and `Vary` merging ... a bump would move none of Part H.7's serving walls" | Dated upstream-diff claim. | area: REST | covered-by: REST.T09
- PLATFORM | SPECIFICATION.md:295-303 | "Every exception raised by our own code inside a route handler — including ... `MemoryError` — is already caught by Microdot itself" | Relies on v2.6.2 `dispatch_request()` shape; changes with a Microdot bump. | area: REST | related: REST.T09
- LIMIT | SPECIFICATION.md:304-307 | "The one gap: exceptions raised while writing the response itself ... the client hits a timeout, as expected." | Known uncaught path in vendored code; per-connection only. | area: REST | related: REST.T09
- INVAR | SPECIFICATION.md:308-310 | "Microdot's own exception logging (`print_exception`) is not wired into this project's `PrintLog`/FRAM logging — anything caught by the blanket catch needs an `@app.errorhandler`" | Evidence visibility depends on registered handlers. | area: REST | related: REST.T13
- LIMIT | SPECIFICATION.md:311-313 | "`Request.json` has no internal guarding (raises straight out on malformed body)" | Contained by the blanket catch only. | area: REST | related: REST.T02
- PLATFORM | SPECIFICATION.md:314-317 | "`max_content_length` (16KB default, 413 if exceeded) → tightened to 2048 bytes ... `max_readline` (2KB default)" | Request bounds depend on Microdot internals (see REST.S01 negative Content-Length). | area: REST | related: REST.S01
- PLATFORM | SPECIFICATION.md:318-322 | "each accepted connection runs in its own independent `asyncio.Task` (confirmed against `extmod/asyncio/stream.py`)" | Isolation relies on pinned asyncio. | area: PLAT | related: PLAT.T01
- PLATFORM | SPECIFICATION.md:323-325 | "Registering `@app.errorhandler(HTTPException)` never fires for `abort()`." | Microdot lookup-key fact. | area: REST | -
- DRIFT | SPECIFICATION.md:332-335 | "one drift: its `HTTPException` branch invokes a status-code handler directly ... irrelevant today since neither app registers handlers there" | Understates legacy/vendored gap: CLAUDE.md records the deployed copy as a pre-v2.1.0 snapshot ~441 lines behind. (low) | area: PAR | related: PAR.T11

## SPECIFICATION.md Part A.6 (Datasheets, 337-356)
- DRIFT | SPECIFICATION.md:339-340 | "(`bmp3xx/`, `fram/`, `pico w/`, `scd30/`, `sgp40/`)" | Omits `datasheets/isl29125/` (present on disk; A.1:34 lists it). | area: DOC | covered-by: DOC.S08
- LIMIT | SPECIFICATION.md:345-347 | "the RP2040 *silicon* datasheet is not in the repo, so its GPIO function-mux table is not readable here" | Missing primary reference; pin-mux substituted by MicroPython macros. | area: PLAT | covered-by: SENS.S20
- PLATFORM | SPECIFICATION.md:347-351 | "UART TX on `pin % 4 == 0`, RX on `pin % 4 == 1` and the peripheral from `((pin + 4) & 8) >> 3`" | Pin-mux derived from pinned `machine_uart.c` macros; re-check on bump. | area: GEN | related: GEN.T07
- PLATFORM | SPECIFICATION.md:351-352 | "p.8 lists GPIO23/24/25/29 as the pins the wireless chip takes" | Board datasheet fact feeding pin legality. | area: GEN | related: GEN.T07
- SETTLED | SPECIFICATION.md:354-356 | "BMP390 ... The project owner has confirmed the whole family shares the same register map/protocol ... a documentation gap only" | Owner-confirmed assumption covering the missing BMP390 PDF. | area: SENS | covered-by: SENS.S20
- LIMIT | SPECIFICATION.md:337-356 | "(`bmp3xx/`, `fram/`, `pico w/`, `scd30/`, `sgp40/`)" | No WS2812/NeoPixel or Pico W QSPI flash datasheet listed or mentioned as missing. | area: LED | covered-by: SENS.S20

## SPECIFICATION.md Part A.7 (wozi's construction order and dependency graph, 358-569)
- MIRROR | SPECIFICATION.md:360-365 | "reproducing the exact same construction order/FRAM chunk layout described below. This section stays the architectural reference" | Doc ↔ `buildgen/codegen.py` output; no test ties this prose to the generator. | area: XCUT | related: DOC.S09
- DRIFT | SPECIFICATION.md:376 | "as of WP1/CLAUDE.md's implicit-FRAM-wiring rule" | Undefined `WP1`-`WP8` labels used throughout Parts A-E; CLAUDE.md never states an "implicit-FRAM-wiring rule" as such. | area: DOC | covered-by: DOC.S16
- LIMIT | SPECIFICATION.md:381 | "`watchdog = WDT(timeout=8000)` — hardcoded, no injection point." | Fixed WDT timeout (cap 8388 ms); not configurable per device. | area: XCUT | related: XCUT.S13
- PLATFORM | SPECIFICATION.md:382-385 | "`i2c0` ... sets `timeout=200000` (200ms): SCD30 documents up to 150ms clock stretching/day, past rp2's 50ms default" | Datasheet + rp2 default fact; per-bus singleton reconfig risk. | area: BUS | related: HW.S18
- DRIFT | SPECIFICATION.md:387-389 | "no chunk of its own (Topic 11's rule: every module gets optional FRAM logging except the FRAM module itself" | "Topic 11" is an undefined/retired reference. | area: DOC | related: DOC.T02
- ASSUME | SPECIFICATION.md:392-394 | "a device with none keeps the pre-WP1 order: `conn`/`ntp` first, `fram` wherever its own instance ordering puts it" | Fallback path when no `fram_target`; every real TOML sets it, so this path is fixture-only. | area: GEN | -
- MIRROR | SPECIFICATION.md:394-460 | "FRAM chunk 1 ... chunk 16" | Hand-numbered chunk list must match generated construction; not machine-checked. | area: XCUT | related: XCUT.T09
- ASSUME | SPECIFICATION.md:414-415 | "`wozi` is never physically flashed (CLAUDE.md), so reordering carries no deployed-data-loss risk" | Holds for wozi only; the same generator emits the other five devices' layouts. | area: XCUT | related: PAR.S13
- DRIFT | SPECIFICATION.md:437-438 | "(WP3 - was wrongly, deliberately excluded" | Self-contradicting history narrative in a current-state doc. (low) | area: DOC | related: DOC.T05
- INVAR | SPECIFICATION.md:446-451 | "The variant also runs a small link exerciser task on the initiator side ... surface through `/status`, which the bench tier asserts advancing under load" | Dev-only bench mechanism; its counters live in `/status`. | area: UART | related: UART.T06
- INVAR | SPECIFICATION.md:459-460 | "`static_mount=\"/html\"` registers the static route pair last, so an exact-match API route always wins" | Registration-order dependency. | area: REST | related: REST.T07
- DRIFT | SPECIFICATION.md:462-463 | "`await x.setup()` batch: `sysfunct → fram → conn → ntp → sgp40 → bmp3xx → notification`" | Generator emits `fram → sysfunct → ...`. | area: DOC | covered-by: DOC.S09
- INVAR | SPECIFICATION.md:463-464 | "One hard constraint: `notification.setup()` needs `finalize()` (step 12) already run" | Ordering constraint satisfied by batching at the end. | area: XCUT | -
- INVAR | SPECIFICATION.md:467-472 | "`sysfunct.feed_watchdog()` follows every single call in this batch (WP6) — a one-time, boot-only, non-looping feed site" | Must never become a looping feed. | area: XCUT | related: XCUT.T01
- ASSUME | SPECIFICATION.md:473-474 | "wozi's own 16 `PrintLogHistoryStore` chunks plus 1 timestamped chunk" | Dated count (dev: 21 per C.7). | area: XCUT | covered-by: DOC.T08
- INVAR | SPECIFICATION.md:480-482 | "must stay in this relative order. `src/` has no earlier on-chip layout to preserve." | Layout freeze from now on; assumes no legacy layout matters (legacy chunk 0 does, PAR.S09). | area: XCUT | related: PAR.S09
- LIMIT | SPECIFICATION.md:482-485 | "A device with no `[device.wiring].fram_target` keeps `conn`/`ntp`/`sysfunct`/`webserver` RAM-only" | Evidence loss for those modules on a FRAM-less device. | area: XCUT | -
- ASSUME | SPECIFICATION.md:500-509 | "boot-to-first-`200` was ~1.9-2.2s before WP1 ... ~6.1s (`wozi`) / ~7.7s (`dev`)" | Twin-only boot timings; 15s test budget raised from 6s. | area: PERF | related: PERF.T06
- LIMIT | SPECIFICATION.md:512-520 | "every number above is a digital-twin measurement ... `digital_twin/_fram_chip.py` answers SPI opcodes in memory with zero wire time" | Twin cannot measure FRAM wire time under contention. | area: TWIN | related: TWIN.T04
- SETTLED | SPECIFICATION.md:510-512 | "not something to \"fix\" by reordering `webserver` in the stagger, or by treating the latency itself as a defect" | Boot latency not a defect (CLAUDE.md WP6). | area: PERF | covered-by: PERF.T06
- ASSUME | SPECIFICATION.md:521-527 | "pre-WP baseline 7.74s, WP1+WP2 9.80s, WP1–WP8 complete 9.76s, and 10.66s ... 23 consecutive reboots ... no `WDT_RESET`" | Single dated silicon series (dev, 2026-09-16), 5 samples each. | area: PERF | related: HW.T16
- OPENQ | SPECIFICATION.md:535-537 | "the `CFGMGR_SYSTEM` fix's own +0.90s is far more than one extra FRAM-backed logger's `setup()` should cost, and is unexplained (`REAL_HARDWARE_TEST_QUEUE.md` R6)" | Unexplained boot-latency delta; queue row R6. | area: PERF | -
- ASSUME | SPECIFICATION.md:539-541 | "`buildgen` derives both from each device's own TOML rather than assuming wozi's answer applies everywhere (confirmed against `buildgen/codegen.py`)" | Claim of per-device derivation. | area: GEN | -
- ASSUME | SPECIFICATION.md:553-555 | "calling `set_level()` at any time is safe — no interrupt handler touches logging, `self.level` is a single atomic-store `int`" | Safety rests on no IRQ/timer callback ever logging; nothing enforces it. | area: CORE | related: XCUT.T08
- INVAR | SPECIFICATION.md:561-567 | "`asy_sgp40_driver.py` needs no static import of `asy_scd30_driver` ... the object graph is still a clean DAG" | No-cross-driver-import and DAG claims; not machine-checked. | area: XCUT | related: XCUT.T16

## SPECIFICATION.md Part A.8 (REST API endpoint reference, 571-625)
- ASSUME | SPECIFICATION.md:578-579 | "Six endpoints: `/measurements`, `/sensors`, `/networking`, `/system`, `/status`, `/notification`." | Count-based route claim (static `/html` routes excluded). | area: REST | related: REST.T02
- DRIFT | SPECIFICATION.md:585-586 | "SPECIFICATION.md Part L Session 7" | "Session N" labels (also :948, :2174, :2382-2384) are undefined — Part L has no Session headings. | area: DOC | related: DOC.S16
- INVAR | SPECIFICATION.md:588-591 | "generator-owned/fixed, never per-device, and reported live so a fleet operator can tell which build" | Build identity is hand-bumped versions + date only (no commit). | area: GEN | related: HW.T19
- INVAR | SPECIFICATION.md:595-597 | "must build results with `.update()`, never `result[name] = await module.get_dict_data()`" | Past production bug; convention for GET aggregation. | area: REST | -
- LIMIT | SPECIFICATION.md:603 | "`\"SystemCmd\": \"reboot\"|\"bootloader\"|\"mempause\"` (enum-validated; `mempause` duration fixed 300s)" | Unauthenticated destructive commands; fixed pause length. | area: SEC | related: SEC.T02
- INVAR | SPECIFICATION.md:604-606 | "`PauseTime` (range-checked 0-3600, rejected not clamped, before reaching `NotificationCoordinator.set_override_led()`)" | Validation convention (Invalid vs Failed semantics disputed). | area: REST | related: REST.S10
- RISK | SPECIFICATION.md:611-613 | "int→float has a known, accepted gap (every int representable as float only up to the mantissa precision, F.1) — accepted since no registered float field's bounds go near it (largest today: BMP3xx's `SeaLevelOffs` at `5000.0`)" | Accepted precision gap premised on current bounds. | area: CORE | related: CORE.T03
- PLATFORM | SPECIFICATION.md:613-615 | "NaN/±inf attempting int-coercion are caught via MicroPython's own `int(float)` exception shapes" | Depends on MicroPython's exception types for int(nan/inf). | area: PLAT | related: CORE.T03
- MIRROR | SPECIFICATION.md:615 | "`js/mock-server.js` mirrors the equivalent policy." | src coercion ↔ JS mock mirror. | area: WEB | covered-by: WEB.T04
- LIMIT | SPECIFICATION.md:617-621 | "One open exception: `SCD30_Reader.get_dict_cfg()` and three of `BMP3xx_Reader.get_dict_cfg()`'s fields ... can mix pre/post-write values across fields (BACKLOG.md)" | Non-atomic GET snapshot; open in BACKLOG. | area: REST | related: SENS.T16

## SPECIFICATION.md Part A.9 (The frozen-HTML pipeline, 627-653)
- DRIFT | SPECIFICATION.md:633 | "over a stream `_serve_static()` opens itself, in 256 B reads" | A.5:292 speaks of Microdot's "1,024 B `send_file` reads" as a serving wall; code has `_DEFAULT_CHUNK_BYTES = const(256)` (`src/asy_webserver_service.py:108`). Which bound governs is stated two ways. (low) | area: REST | related: REST.T07
- PLATFORM | SPECIFICATION.md:634-637 | "`.frozen/` is a hardcoded MicroPython import-machinery sentinel (`MP_FROZEN_PATH_PREFIX`)" | Version-specific import fact. | area: PLAT | -
- LIMIT | SPECIFICATION.md:649-652 | "left one case the real site has no file for, the binary `application/octet-stream` fallback, which Section G of `tests/test_asy_webserver_service.py` now pins on its synthetic fixture" | One serving path covered only synthetically. | area: TEST | -
- INVAR | SPECIFICATION.md:652-653 | "The two suites still must not run concurrently, for their ports (CLAUDE.md)" | Review-only rule; nothing prevents concurrent runs. | area: SCR | related: SCR.T06

## SPECIFICATION.md Part A.10 (Digital twin, 655-686)
- INVAR | SPECIFICATION.md:663-667 | "any new module joins the digital twin, provided it can form a complete chain ... A module that can't yet complete the chain stays out until the missing piece exists" | Review-only obligation; deferral allowed. | area: TWIN | -
- ASSUME | SPECIFICATION.md:669-673 | "a `strategy.matrix` over all 6 real device variants ... through its 14-run suite" | Dated counts (6 devices, 14 runs). | area: TWIN | covered-by: DOC.T08
- WORKAROUND | SPECIFICATION.md:681-684 | "three confirmed Unix-port-only `socket` quirks ... worked around entirely from twin-side code (`digital_twin/_unix_port_udp_addr_shim.py`)" | Unix-port defect workaround; removal trigger none stated. | area: TWIN | related: TWIN.T07

## SPECIFICATION.md Part B intro, B.1-B.3 (688-753)
- INVAR | SPECIFICATION.md:696-699 | "The four pieces must agree exactly, or the build silently breaks" | MicroPython/pico-sdk/picotool/ARM GCC coherence is derived, not pinned separately. | area: TOOL | related: TOOL.T02
- SETTLED | SPECIFICATION.md:721-724 | "Both subcommands also build/verify two Unix-port interpreters (owner decision, 2026-09-21)" | build-standard without settrace, build-settrace for --coverage only; firmware never gets the flag. | area: TOOL | related: TOOL.T05
- ASSUME | SPECIFICATION.md:724-730 | "The flag is not inert when unused (measured 2026-09-18) ... inflating every allocation figure 4-5x ... (`test_sensortask_wozi.py` 24.6s → 9.3s)" | Dated single measurements; cite the git-only HEAP_FRAGMENTATION archive §1.2. | area: TEST | related: DOC.S04
- INVAR | SPECIFICATION.md:730-732 | "Because a build directory's name no longer tells you which variant is in it, `scripts/test.sh` verifies the binary rather than the path" | Only test.sh probes the variant; twin/web runners hardcode `build-standard` and check existence only. | area: SCR | covered-by: SCR.S05
- PLATFORM | SPECIFICATION.md:734-735 | "Ubuntu's `universe` component (default on real Ubuntu images — `gcc-arm-none-eabi` lives there)" | Distro-packaging prerequisite. | area: TOOL | -
- ASSUME | SPECIFICATION.md:742-743 | "Derive the matching `picotool` version by resolving that commit to its nearest tag, taking major.minor, picking the newest `picotool` tag sharing it" | Heuristic version derivation; floats as picotool tags appear. | area: TOOL | covered-by: TOOL.T02
- RISK | SPECIFICATION.md:744 | "Install the ARM cross-compiler from `apt`'s `gcc-arm-none-eabi` (no pin needed)." | Compiler unpinned — the GCC-14 mbedtls break (B.7.1) shows a pin can matter. | area: TOOL | covered-by: TOOL.T12
- DRIFT | SPECIFICATION.md:746-748 | "clean up, rebuild a vanilla Unix port as the standing test rig" | Two Unix ports are kept now (B.5); step list names one. (low) | area: DOC | -

## SPECIFICATION.md Part B.4-B.9 (754-826)
- INVAR | SPECIFICATION.md:757-761 | "Every subprocess ... gets an explicit, constructed environment, never the caller's shell wholesale" | Isolation convention with one stated exception (B.12 :1005-1007). | area: TOOL | related: TOOL.T01
- RISK | SPECIFICATION.md:766 | "`picotool`'s install location is pinned explicitly (`-DCMAKE_INSTALL_PREFIX=/usr/local`)" | Host-wide install via `sudo make install` (B.5:778). | area: TOOL | covered-by: TOOL.T09
- SETTLED | SPECIFICATION.md:781 | "Full (non-shallow) clones — shallow clones make the update path unreliable." | Deliberate full clones. | area: TOOL | -
- DRIFT | SPECIFICATION.md:795 | "A completed run leaves no vanilla RP2 `firmware.uf2`; step 8's Unix port is the only kept artifact." | `build-settrace` is also built and kept (B.5:776, `toolchain/setup_toolchain.py:517`). (low) | area: DOC | -
- ASSUME | SPECIFICATION.md:799-803 | "Verified end-to-end in a clean `debootstrap` Ubuntu 24.04 chroot for both the deployed `v1.26.1` and latest stable ... `test` alone completes in ~30s offline" | Undated evidence claim from an earlier pin; CLAUDE.md dates the chroot legs 2026-09-12. | area: TOOL | related: HW.T16
- WORKAROUND | SPECIFICATION.md:807-813 | "Worked around via `-Wno-array-bounds` in `_MBEDTLS_GCC14_ARRAY_BOUNDS_WORKAROUND` ... recheck its status, and whether a future MicroPython ref vendors mbedtls ≥3.6.6, before removing this" | GCC ≥14 false positive (Debian #1085354, GCC #121044 UNCONFIRMED); removal trigger stated; applied to every build (`toolchain/setup_toolchain.py:335, 379`). | area: TOOL | related: CI.T10
- PLATFORM | SPECIFICATION.md:807-809 | "this project's pinned MicroPython vendors an mbedtls commit predating that fix" | Version-specific fact to re-check on each pin move. | area: PLAT | -
- DRIFT | SPECIFICATION.md:821-826 | "Does not yet wire up `build-*.sh`'s hardcoded `/home/nico/rpi_pico/...` paths ... the remaining gap is the RP2040 firmware build" | Legacy framed as TODO (contradicts CLAUDE.md "never gets work"); firmware build now covered by `firmware-build-verify`. | area: DOC | covered-by: DOC.S08

## SPECIFICATION.md Part B.10 / B.10.1 (CI perspective, 828-929)
- ASSUME | SPECIFICATION.md:830-831 | "`.github/workflows/ci.yml` runs fifteen jobs (fourteen of them real work plus `web-changes`" | Job count (matches ci.yml today: 15); goes stale on any job change. | area: CI | covered-by: DOC.T08
- ASSUME | SPECIFICATION.md:837-839 | "567s of the suite's 578s, measured 2026-09-19" | Dated web-tier wall-clock figure (repeated :881 with "243 of 778 tests"). | area: CI | -
- INVAR | SPECIFICATION.md:841-845 | "Cache key hashes both `versions.toml` and `setup_toolchain.py`" | Key omits `micropython_overrides.py`, whose override is compiled into the cached binary. | area: CI | covered-by: CI.S01
- SETTLED | SPECIFICATION.md:846-853 | "`uv sync` is retried three times in every job that syncs ... CLAUDE.md says not to simplify that one away" | Protected retry; outages observed 2026-09-13/14/21. | area: CI | covered-by: CI.S17
- ASSUME | SPECIFICATION.md:857-860 | "Measured on run `34755468619` (2026-09-13): the plain suite reported `60/60 files passed` ... ran 13m24s longer, and the 30-minute cap cancelled the job" | Dated run evidence; file count now ~87. | area: CI | -
- SETTLED | SPECIFICATION.md:867-868 | "Permissions deny by default (`permissions: {}`, then `contents: read` per job) ... zizmor enforces it." | Enforced by zizmor. | area: CI | covered-by: CI.T06
- INVAR | SPECIFICATION.md:869-875 | "It passes `base: ${{ github.ref }}` ... Python jobs never consult it." | Path-filter design; cancellation interaction open. | area: CI | covered-by: CI.S11
- ASSUME | SPECIFICATION.md:880-885 | "567 s of the suite's 578 s, 243 of 778 tests (2026-09-19) ... `tests_js/mock-server-put-matrix.test.js` proves the partition" | Dated counts; shard partition claimed proven by a test. | area: CI | -
- INVAR | SPECIFICATION.md:894-896 | "Firefox/geckodriver come from conda-forge via micromamba (~106 MB, no version file to key on), cached under a fixed key whose suffix is bumped to force a refresh" | Manual cache-key bump; unpinned browser. | area: CI | covered-by: CI.S06
- SETTLED | SPECIFICATION.md:902-903 | "shellcheck covers `scripts/` only: the legacy `build-*.sh` are out of scope forever (CLAUDE.md), 28 findings included" | Legacy lint gap by decision; "28" is a dated count. | area: CI | -
- DRIFT | SPECIFICATION.md:906-908 | "a ~17-minute warm run plus one file's full 9-minute retry budget (180 s x 3)" | test.sh default is 240 s. | area: SCR | covered-by: SCR.S03
- ASSUME | SPECIFICATION.md:908-909 | "Cold-cache runs measured 16m58s and 16m42s including the toolchain build." | Dated timing basis for `timeout-minutes: 45`. | area: CI | -
- SUPPRESS | SPECIFICATION.md:914-917 | "report steps (`always() && hashFiles(...)`, `continue-on-error`) do not (E.5.3); the Codecov upload needs the repo registered and a `CODECOV_TOKEN`, and `fail_ci_if_error` stays off" | Advisory coverage report; Codecov upload currently a no-op. | area: CI | related: CI.T11
- TODO | SPECIFICATION.md:916-917 | "the Codecov upload needs the repo registered and a `CODECOV_TOKEN`" | Registration/token not done (CLAUDE.md: "hasn't happened yet"). | area: CI | -
- SETTLED | SPECIFICATION.md:920-922 | "A six-device matrix, `fail-fast: false` ... `needs: unit-tests` and stays success-gated: fail-fast is its stated intent." | digital-twin-e2e is the deliberate gated exception. | area: CI | covered-by: CI.T01
- INVAR | SPECIFICATION.md:924-929 | "`needs: unit-tests` for the toolchain cache only, so `if: !cancelled()` ... A cache miss fails on `build_firmware.py`'s own \"no toolchain found\"" | Cold-cache failure mode accepted. | area: CI | covered-by: CI.S09

## SPECIFICATION.md Part B.11 (Building this project's firmware, 931-984)
- INVAR | SPECIFICATION.md:933-935 | "change `versions.toml`'s `[micropython] ref` — the only place. Everything else derives automatically" | Single-source pin; `--micropython-ref`/`--latest` paths bypass or move it silently. | area: TOOL | related: TOOL.S06
- DRIFT | SPECIFICATION.md:939-941 | "Still assumes `python/` is checked out as `py-include/python` alongside `micropython`, path not yet genericized (BACKLOG.md)" | Legacy framed as open work vs CLAUDE.md legacy rule. | area: DOC | covered-by: DOC.S21
- DRIFT | SPECIFICATION.md:946-948 | "replaces the former hand-written `boot_entry/<device>_boot.py` (retired, Session 6's finish criterion)" | Undefined "Session 6" label. (low) | area: DOC | related: DOC.S16
- PLATFORM | SPECIFICATION.md:950-958 | "That entry point is frozen under the literal name `\"main.py\"`, NOT imported from a custom `_boot.py` — load-bearing, re-confirmed against pinned v1.29.0" | Relies on `ports/rp2/main.c` boot order (USB after frozen `_boot.py`); upstream #15230. | area: PLAT | related: PLAT.T10
- LIMIT | SPECIFICATION.md:958-959 | "Confirmed working on real hardware for `dev`; not yet re-confirmed for `wozi` (never physically flashed)." | wozi boot entry never proven on silicon. | area: HW | related: PAR.S13
- ASSUME | SPECIFICATION.md:963-965 | "`mpy-cross` doesn't dead-code-eliminate `if TYPE_CHECKING:` ... dead weight (~3.6KB measured)" | Compiler behaviour + single measurement. | area: SCR | related: SCR.T03
- LIMIT | SPECIFICATION.md:966-970 | "Side effect: strips every comment from the file ... an on-device traceback's line numbers won't match checked-in `src/`" | Shipped bytecode differs from source line-for-line. | area: SCR | related: SCR.T10
- DRIFT | SPECIFICATION.md:972-976 | "`test_real_firmware_build_produces_a_valid_uf2` does the real end-to-end build (parametrized over `wozi`/`dev`)" | Test is parametrized over `DEVICE_NAMES` (all six, `tests_scripts/test_build_firmware.py:196`); CI runs six. | area: DOC | -
- SUPPRESS | SPECIFICATION.md:974 | "gated behind `RUN_SLOW_FIRMWARE_BUILD=1`" | Real firmware build skipped locally unless opted in (`tests_scripts/test_build_firmware.py:198-199`). | area: SCR | covered-by: SCR.T13
- DRIFT | SPECIFICATION.md:975-976 | "closing the \"no CI firmware-build stage\" gap for this pipeline (legacy `build-*.sh` stays open, BACKLOG.md)" | Legacy framed as open. | area: DOC | covered-by: DOC.S21
- LIMIT | SPECIFICATION.md:978-984 | "still build-only, not an on-device functional check ... This script's success is necessary, not sufficient, for a real device to boot." | Build pipeline proves assembly only. | area: SCR | related: SCR.T10
- SUPPRESS | SPECIFICATION.md:981 | "`tests_hardware/flash/test_toolchain_flash_boot.py` (`--allow-flash-cycle`-gated)" | Opt-in gate on the only on-silicon boot check. | area: HW | related: HW.S01

## SPECIFICATION.md Part B.12 (Tiered dev-environment setup, 986-1014)
- INVAR | SPECIFICATION.md:993-996 | "Exactly one match required; zero or multiple is a hard error naming `--device` as the escape hatch, never a silent guess." | USB detection by `idVendor=2e8a`. | area: TOOL | -
- RISK | SPECIFICATION.md:998-1003 | "A genuinely new bridge gets fresh random SSID/password (`secrets`-generated) unless overridden, printed once at creation only." | Bench AP secret printed (and in argv per TOOL.S01). | area: TOOL | covered-by: TOOL.S01
- SETTLED | SPECIFICATION.md:1005-1009 | "runs with `env=None` (inherit the caller's real environment) — the one deliberate exception to this script's isolation convention" | Deliberate isolation exception for uv/npm. | area: TOOL | -
- LIMIT | SPECIFICATION.md:1010-1014 | "Not exercised there: actually flashing a physical board, or creating the bridge/AP ... Full flash/bench real-hardware verification is DONE ... (2026-09-04)" | Sandbox cannot verify flash/bench tiers; single dated bench verification. | area: TOOL | related: TOOL.T13

## SPECIFICATION.md Part B.13 (Bench network safety, 1016-1061)
- INVAR | SPECIFICATION.md:1018-1021 | "must keep a recovery dead-man's-switch continuously armed for the entire risk window — never touch live network state with none armed" | Operator rule; `ensure_bench_bridge()` itself arms none. | area: HW | covered-by: TOOL.S03
- ASSUME | SPECIFICATION.md:1021-1023 | "One arm covering a whole atomic sequence is equivalent protection to per-command re-arming, provided the sequence's real timing is measured, not guessed." | Conditional equivalence claim. | area: HW | related: TOOL.T03
- SETTLED | SPECIFICATION.md:1028-1034 | "`ensure_bench_bridge()` now pins `bridge.mac-address` ... and warns (never auto-repairs — cycling a live bridge's MAC risks the same incident)" | Deliberately warn-only. | area: TOOL | related: TOOL.T03
- MIRROR | SPECIFICATION.md:1033-1034 | "`dev_legacy/README.md`'s manual recipe carries the identical fix." | MAC-pinning in code ↔ manual recipe doc. | area: HW | -
- SETTLED | SPECIFICATION.md:1036-1038 | "Recreate this script fresh in a session's own scratchpad each time (deliberately not a committed file)" | Recovery script intentionally uncommitted. | area: HW | -
- ASSUME | SPECIFICATION.md:1045-1048 | "nmcli connection modify \"Wired connection 1\" autoconnect yes" | Hardcoded NM profile name assumed present on the Pi. | area: HW | covered-by: TOOL.S03
- ASSUME | SPECIFICATION.md:1055-1059 | "a real run showed success in ~1s but no DHCP lease/default route until ~30s later, STP delay" | Single observed timing informing the arm window. | area: HW | -

## SPECIFICATION.md Part B.14 (MicroPython build overrides framework, 1063-1114)
- ASSUME | SPECIFICATION.md:1065 | "so far: two implemented, one identified and planned" | Dated count. (low) | area: TOOL | -
- INVAR | SPECIFICATION.md:1070-1073 | "every override there generates files or extra build flags entirely *outside* the fetched checkout (never a single byte written into it)" | Zero-touch rule by convention. | area: TOOL | related: TOOL.T04
- INVAR | SPECIFICATION.md:1077-1080 | "these anchors are exactly the kind of thing to re-verify on the next `toolchain/versions.toml` `[micropython] ref` bump" | Manual re-verification obligation beyond the literal anchor check. | area: PLAT | related: PLAT.T07
- PLATFORM | SPECIFICATION.md:1086-1090 | "confirmed directly (2026-09-15) that a later plain `#define` in the same translation unit always wins over an earlier command-line `-D`" | Toolchain fact behind the header mechanism. | area: TOOL | -
- SETTLED | SPECIFICATION.md:1100-1101 | "there is no opt-out flag, since an override existing at all means the *unpatched* build is the one considered unsafe" | No opt-out by design. | area: TOOL | -
- ASSUME | SPECIFICATION.md:1104-1108 | "every one of them reaches the toolchain build through this same entry point, with no alternate path anywhere in this project's own tooling" | But twin/web runners reuse a cached binary without rebuilding on override change. | area: TOOL | related: TOOL.T07

## SPECIFICATION.md Part B.14.1 (`unix_kbd_intr`, 1116-1213)
- WORKAROUND | SPECIFICATION.md:1159-1165 | "`apply_unix_kbd_intr_override()` forces this path for the Unix \"standard\" variant ... without editing anything inside the fetched checkout" | Upstream Unix-port async SIGINT (`MICROPY_ASYNC_KBD_INTR`) workaround; removal trigger at :1211-1213 (upstream default inverted). | area: TOOL | related: TOOL.S07
- PLATFORM | SPECIFICATION.md:1136-1138 | "`MICROPY_ASYNC_KBD_INTR (!MICROPY_PY_THREAD_GIL)` - true for this project's non-threaded \"standard\" variant build" | Pinned-source anchor. | area: PLAT | -
- LIMIT | SPECIFICATION.md:1145-1150 | "`unwedge_heap_after_interrupt()` patches that one specific downstream symptom, but does nothing for an interrupt landing mid some *other* non-reentrant operation" | Twin helper's scope limit; kept as defence in depth. | area: TWIN | covered-by: TWIN.T07
- PLATFORM | SPECIFICATION.md:1166-1172 | "`VARIANT_DIR ?= variants/$(VARIANT)` ... a `CFLAGS_EXTRA`-appended `-I` was tried and empirically confirmed to lose" | Makefile-ordering facts the override depends on. | area: TOOL | -
- SETTLED | SPECIFICATION.md:1175-1181 | "Deliberately never a symlink: MicroPython issue #12671" | Symlinked variant dir breaks; real files with absolute includes. | area: TOOL | -
- MIRROR | SPECIFICATION.md:1181-1185 | "would ... rename `BUILD ?= build-$(VARIANT)` away from `build-standard`, which every other script in this repo hardcodes" | `build-standard` path hardcoded in `scripts/run_digital_twin_ci.sh:28`, `run_unix_port_integration.sh:48`, `cross_browser_smoke.mjs:14`, `tests_js/_live_*_command.js`. | area: SCR | related: SCR.S05
- ASSUME | SPECIFICATION.md:1194-1198 | "ran clean for a combined 700+ iterations against the patched binary with zero shutdown failures" | Single hammer-loop verification (2026-09-14/15). | area: TOOL | -
- LIMIT | SPECIFICATION.md:1193-1194 | "preprocessing the resulting `unix_mphal.c` directly confirms the safe branch" | One-off manual proof; no in-build readback. | area: TOOL | covered-by: TOOL.S07
- DRIFT | SPECIFICATION.md:1198-1199 | "`build_unix_port()` (both call sites - the frozen-verification build and the vanilla test-rig rebuild)" | Three call sites now (settrace build, `toolchain/setup_toolchain.py:503, 514, 517`). (low) | area: DOC | -
- INVAR | SPECIFICATION.md:1202-1213 | "Re-verification checklist for a MicroPython version bump ... re-run this section's own hammer-loop verification ... do not assume \"it built\" is sufficient" | Manual version-bump obligation. | area: PLAT | related: PLAT.T06

## SPECIFICATION.md Part B.14.2 / B.14.2.1 (`lwip_connection_counts`, 1215-1379)
- PLATFORM | SPECIFICATION.md:1225-1228 | "`MEMP_NUM_NETCONN` is dead on this port." | `LWIP_NETCONN 0`/`LWIP_SOCKET 0` in pinned lwipopts_common.h. | area: PLAT | related: PLAT.T04
- PLATFORM | SPECIFICATION.md:1229-1234 | "`MEMP_NUM_UDP_PCB` is a bare `#define` (`4 + LWIP_MDNS_RESPONDER`), and so is `LWIP_STATS 0`" | Pinned-source guard shapes. | area: PLAT | related: NET.T05
- PLATFORM | SPECIFICATION.md:1235-1242 | "one atomic `#ifndef MEM_SIZE` block (8000 / 800 / 6400 / 6400 / 32 as pinned). Defining `MEM_SIZE` alone on the command line disables the whole block" | Trap the override must avoid. | area: TOOL | -
- PLATFORM | SPECIFICATION.md:1245-1248 | "`py/mkrules.cmake:81` folds `$ENV{CFLAGS_EXTRA}` into `CMAKE_C_FLAGS`" | Line-anchored upstream citation; drifts with the pin. | area: PLAT | -
- ASSUME | SPECIFICATION.md:1255-1262 | "checks twenty-one anchors ... a completeness test pins that list to the code's own" | Count; enforced by `tests_scripts/test_micropython_overrides.py`. | area: TOOL | -
- INVAR | SPECIFICATION.md:1273-1280 | "`verify_lwip_macros_in_build()` ... `build_firmware()` calls it after every build" | Post-build proof (asymmetry with unix_kbd_intr). | area: TOOL | covered-by: TOOL.T11
- MIRROR | SPECIFICATION.md:1283-1294 | "`check_lwip_ensemble()` restates every one of them ... `derive_lwip_dependents()` reproduces opt.h's four formulas" | Python restatement of lwIP `init.c` `#error`s / `opt.h` derivations; drifts on lwIP bump. | area: TOOL | covered-by: TOOL.T04
- INVAR | SPECIFICATION.md:1297-1300 | "Its own checks size the shared pools for one connection ... (and a `max_connections` below 1 is refused by name" | Three N-connection relationships lwIP doesn't check, enforced by the override. | area: TOOL | -
- RISK | SPECIFICATION.md:1309-1316 | "`modlwip.c`'s write retries `tcp_write()` up to 200 x 50 ms, blocking the whole VM for up to 10 s ... no asyncio timeout can interrupt it. Never observed on silicon" | Latent 10 s VM block when the arena is exhausted. | area: PLAT | covered-by: PLAT.T04
- PLATFORM | SPECIFICATION.md:1309-1311 | "`extmod/modlwip.c:802` calls `tcp_write()` with `TCP_WRITE_FLAG_COPY` unconditionally" | Line-anchored upstream fact. | area: PLAT | -
- INVAR | SPECIFICATION.md:1318-1319 | "`buildgen/validate.py` runs the N-connection half per device ... refuses a device whose `max_connections` the firmware's own pools cannot serve" | Enforced in buildgen. | area: GEN | related: GEN.T15
- SETTLED | SPECIFICATION.md:1321-1325 | "`PBUF_POOL_SIZE` is deliberately left alone. ... Confirmed on silicon: at an 8x advertised inbound over-commit ... it never surfaced" | Deliberate; evidence in git-only archive §7R.2. | area: MEM | related: DOC.S04
- ASSUME | SPECIFICATION.md:1328-1364 | "Measured cost, from real builds ... Absolute heaps are from the builds of that day; the deltas are what transfer." | Undated build-size tables; shipped 6-connection GC heap 192,488 / linker 192,360 B. | area: MEM | related: DOC.T08
- ASSUME | SPECIFICATION.md:1366-1368 | "A connection costs 2,324 B of GC heap, not 196 B" | Derived per-connection cost. | area: PERF | related: PERF.T02
- MIRROR | SPECIFICATION.md:1370-1374 | "update the anchor list and `LWIP_MACROS_GUARDED_IN_OPT_H`/`LWIP_MACROS_PREDEFINED_BY_MICROPYTHON` together" | Two lists that must move in step on a bump. | area: TOOL | -
- LIMIT | SPECIFICATION.md:1376-1379 | "this firmware never calls lwIP's C `stats_display()`, so reading them needs a probe of its own" | No pool-exhaustion diagnostics in the field. | area: PLAT | -

## SPECIFICATION.md Part B.14.3 (`littlefs_flash_storage_size`, 1381-1410)
- TODO | SPECIFICATION.md:1381-1390 | "(documented, not yet implemented) ... Mechanism, verified workable against the pinned source, not yet wired in" | Planned override not implemented. | area: TOOL | covered-by: TOOL.T06
- PLATFORM | SPECIFICATION.md:1391-1397 | "`set(MICROPY_HW_FLASH_STORAGE_BYTES 868352) endif()` (848KB; `mpconfigport.h`'s own generic rp2 default ... `1408 * 1024`" | littlefs size facts relevant to the 1.26 → 1.29 reflash. | area: PAR | covered-by: PAR.S10
- TODO | SPECIFICATION.md:1399-1404 | "What a real implementation still needs: a `verify_littlefs_flash_storage_size_anchor()`" | Missing anchor check spelled out. | area: TOOL | -
- RISK | SPECIFICATION.md:1405-1410 | "shrinking the reserved littlefs region changes the on-flash layout of a board that may already have deployed units carrying real persisted state" | Real-hardware data risk. | area: PAR | related: PAR.T06

## SPECIFICATION.md Part B.15 (The three mypy passes, 1413-1473)
- RISK | SPECIFICATION.md:1425-1426 | "`follow_imports_for_stubs` extends that to the (upstream-Beta) stub package itself" | Type-check correctness rests on a Beta third-party stub package (two repaired defects, CLAUDE.md). | area: SCR | related: PLAT.T05
- INVAR | SPECIFICATION.md:1429-1430 | "`files` names directories, never globs: a glob is pre-expanded into a file list that `exclude` can no longer prune." | Config convention. | area: SCR | -
- LIMIT | SPECIFICATION.md:1431-1433 | "`build/generated_src` is on `mypy_path` for the one static `import sensortask_dev` ... `typecheck.sh` generates it first." | Generated modules resolved (silently) but never reported. | area: GEN | covered-by: GEN.S17
- SUPPRESS | SPECIFICATION.md:1434-1445 | "Excluded, and why. `tests/network.py` ... `digital_twin/machine.py`, `network.py`, `neopixel.py` ... `launch.py`, `run_generic_integration.py`, `segfault_stress_repro.py`, every `tests/test_digital_twin_*.py` and the two shared scenario libraries" | Main-pass mypy exclusions (checked by the twin pass instead). | area: SCR | related: SCR.T15
- DRIFT | SPECIFICATION.md:1439-1441 | "and the two shared scenario libraries (`_webserver_concurrency_scenarios.py`, `_digital_twin_construction_scenarios.py`)" | CLAUDE.md's exclusion list omits these two libraries. (low) | area: DOC | -
- LIMIT | SPECIFICATION.md:1443-1445 | "Their apparent cleanliness in this pass was accidental: a real `no-any-return` in `test_digital_twin_bmp3xx.py` appeared only once `digital_twin` was in scope." | Exclusions can hide findings. | area: SCR | related: TEST.T19
- SUPPRESS | SPECIFICATION.md:1446-1449 | "The one exemption, `no_implicit_reexport = false`, and the `disallow_untyped_decorators` override for `test_setter_microdot_integration`" | Main-pass strictness exemptions. | area: SCR | related: SCR.T15
- MIRROR | SPECIFICATION.md:1454-1455 | "its strictness is kept in sync with the main pass by hand (INI has no include directive)" | Three configs hand-synced; no check. | area: SCR | covered-by: SCR.T15
- SUPPRESS | SPECIFICATION.md:1460-1461 | "`tests_hardware/device_scripts/` is excluded here (MicroPython code: 121 errors, 99 artifacts)" | Host-pass exclusion; dated counts. | area: SCR | -
- SUPPRESS | SPECIFICATION.md:1462-1466 | "`tests_scripts/conftest.py` is excluded ... an accepted gap against re-laying out either tier" | Accepted type-check gap. | area: SCR | covered-by: SCR.T15
- MIRROR | SPECIFICATION.md:1469-1473 | "The other `mypy_path` entries mirror the `sys.path` pytest builds at runtime" | mypy_path ↔ pytest sys.path hand mirror. | area: SCR | -

## SPECIFICATION.md Part C intro, C.1-C.2 (1475-1535)
- DRIFT | SPECIFICATION.md:1486, 1493-1494 | "A new driver adds layers 2-3 only (one file, `asy_<sensor>_driver.py`) plus a `_Reader` wiring block in the relevant `sensortask-*.py`." | Layer 4 is now buildgen-generated from `devices/*.toml`; no hand-written wiring block exists (Part K/L). | area: DOC | related: DOC.S09
- INVAR | SPECIFICATION.md:1500-1501 | "Name-mangled (`__`) methods are reserved for when mangling itself is load-bearing — `src/` has none." | Convention claim; no lint guard named. (low) | area: CORE | -
- SETTLED | SPECIFICATION.md:1501-1502 | "`voc_algorithm.py`'s internals trace their DFRobot/Sensirion source 1:1 (F.4), casing intentionally non-compliant" | Permanent naming exception. | area: ALGO | -
- INVAR | SPECIFICATION.md:1513-1515 | "`_NAME`'s string and the namedtuple's type-name string must be identical, always" | Holds today for SCD30/SGP40/BMP3XX/ISL29125 by convention; no test named. | area: SENS | related: SENS.T08
- PLATFORM | SPECIFICATION.md:1516-1517 | "`_VAL_<ABBREV> = const(((\"<Field>\", \"<type>\", default, min, max, special),))`" | Relies on `const()` accepting tuples on the pinned MicroPython. | area: PLAT | related: PLAT.T02
- MIRROR | SPECIFICATION.md:1520-1527 | "`<Sensor>_DeviceSession(Lockable)` — pure boilerplate, identical in all three drivers ... Copy verbatim" | Copied boilerplate across drivers (four now incl. ISL29125). | area: SENS | related: DOC.S08
- INVAR | SPECIFICATION.md:1528-1532 | "`*_Reader` constructor order (match exactly): bus handle, ... `max_module_error: int = 5`, `name_ext: str = \"\"` ... `debug: int | None = None`" | Constructor-shape convention (divergences seeded). | area: SENS | covered-by: SENS.S18

## SPECIFICATION.md Part C.3 (Layer 2 protocol class, 1537-1566)
- DRIFT | SPECIFICATION.md:1541-1543 | "A class built entirely on `I2CDevice.get_register_struct()`/`get_bits()` (`BMP3XX_I2C`) has no scratch buffer at all" | Stale per seed. | area: SENS | covered-by: SENS.S19
- LIMIT | SPECIFICATION.md:1544-1546 | "`FRAM_SPI`'s `_check_device_id()`/`_read_status()`/`_send_opcode()` do this (a real, low-severity D.4 violation left as-is" | Accepted per-call allocation; `_send_opcode()` doesn't exist. | area: STOR | covered-by: STOR.S04
- INVAR | SPECIFICATION.md:1548-1551 | "Contract: raises on any real failure — the layer that does not return sentinels." | Layer-2 contract. | area: SENS | related: BUS.T01
- PLATFORM | SPECIFICATION.md:1552-1556 | "`asy_spi_driver.py`'s `write()` cannot raise at all on rp2 ... `readinto()`/`write_readinto()` can raise `OSError(EIO)` on a 32+ byte RX overrun since MicroPython 1.29" | rp2 1.29-specific raise surface. | area: BUS | related: PLAT.T03
- LIMIT | SPECIFICATION.md:1555-1556 | "`write_readinto()` additionally turns a caller-input `ValueError` into `None`." | Success and swallowed error both return None. | area: BUS | covered-by: BUS.S04
- INVAR | SPECIFICATION.md:1557-1559 | "`setup()` verifies identity ... and raises if the sensor doesn't respond — fails loudly once at boot rather than degrading silently forever" | Identity-check obligation. | area: SENS | related: SENS.S06
- INVAR | SPECIFICATION.md:1560-1563 | "A multi-transaction sequence that must not be interleaved holds the session lock for the whole sequence" | Locking convention. | area: BUS | related: XCUT.T06
- INVAR | SPECIFICATION.md:1564-1565 | "Compensation/calibration math and datasheet operating-range checks live here — reject and raise rather than return an implausible value silently." | SCD30 lacks a range gate per seed. | area: SENS | related: SENS.S10

## SPECIFICATION.md Part C.3.1 (SPI sensor variant, 1567-1596)
- LIMIT | SPECIFICATION.md:1567-1571 | "SPI sensor variant — best effort, non-proven ... Needs extra datasheet/hardware scrutiny the first time used." | Unproven guidance for any SPI sensor. | area: BUS | -
- PLATFORM | SPECIFICATION.md:1575-1576 | "No bus-level presence probe exists for SPI, unlike I2C's zero-byte-write NAK check." | Identity must be content-checked. | area: BUS | -
- INVAR | SPECIFICATION.md:1582-1589 | "The settle inside the CS window must block (`time.sleep_us(2)`) — an awaited one hands the loop to another task with CS asserted and the bus locked" | Must-not-await rule inside CS. | area: BUS | related: BUS.T04
- PLATFORM | SPECIFICATION.md:1592-1596 | "Two real chips: `MB85RS64V` (8KB, `0x2000`) and `MB85RS2MTA` (256KB, `0x40000`, ... p.10) ... A genuinely new size needs its own table entry." | Address-width table; which part dev carries is disputed. | area: STOR | related: HW.T07

## SPECIFICATION.md Part C.3.2 (UART variant, 1598-1622)
- SETTLED | SPECIFICATION.md:1604-1606 | "Settled precedent: one merged class, not a session+protocol pair ... the accepted shape for any future point-to-point wrapper" | UART shape decision. | area: UART | -
- MIRROR | SPECIFICATION.md:1613 | "see `UART_C_PORT_CHANGELOG.md` B15." | Spec ↔ temporary changelog entry ID (changelog deletion would dangle). | area: DOC | related: DOC.S14
- PLATFORM | SPECIFICATION.md:1613-1615 | "raise contract (re-verified against `ports/rp2/machine_uart.c` at v1.29.0): a hardware framing/parity/overrun error is never raised ... `write()` can short-write" | rp2 UART error semantics. | area: BUS | related: BUS.T05
- ASSUME | SPECIFICATION.md:1615-1621 | "`any()` cannot raise either (re-traced 2026-09-13 ...) ... `_buffered()`'s `except (OSError, MemoryError)` is therefore defence in depth against a future port, not a reachable rp2 case" | Dated trace; catch kept as unreachable defence. | area: BUS | -

## SPECIFICATION.md Part C.4 (Layer 3 Reader, 1624-1697)
- INVAR | SPECIFICATION.md:1626-1628 | "Contract: never raises. ... Every layer-2 call is wrapped in its own `try/except Exception` ... (never bare `except:`)" | Layer-3 never-raise contract. | area: SENS | related: BUS.T01
- DRIFT | SPECIFICATION.md:1630 | "`read_loop()` skeleton (identical across all three drivers)" | Four sensor drivers now (ISL29125). | area: DOC | covered-by: DOC.S08
- MIRROR | SPECIFICATION.md:1653-1656 | "Each one costs `system_service.py`'s `_TASK_FAIL_INCREMENT` (100) against a `_TASK_FAIL_MAX` of 300 that decays by only 1 per clean supervisor pass ... about three restarts" | Doc restates `src/system_service.py:45-46` constants. | area: XCUT | related: XCUT.T02
- ASSUME | SPECIFICATION.md:1656-1658 | "a test that needs several drivers to log a chip-healthy error gives each its own process ... (Run 5c; measured both ways)" | Test design constrained by the reboot budget. | area: TWIN | -
- SUPPRESS | SPECIFICATION.md:1669-1672 | "identity return + scoped `# type: ignore[return-value]` ... the settled convention over a local `cast()` shim" | Settled suppression; sites `src/asy_bmp3xx_driver.py:310`, `asy_isl29125_driver.py:878`, `asy_notification_service.py:251`, `asy_ntp_client.py:365`, `asy_scd30_driver.py:238`, `asy_sgp40_driver.py:488`, `asy_wifi_service.py:684`. | area: SENS | -
- DRIFT | SPECIFICATION.md:1672-1673, 2306 | "`typing.cast()` still applies to narrowing a `struct.unpack()` result" / "`typing.cast()` has no runtime presence (C.4.2)" | SCD30 defines its own runtime no-op `cast()` shim (`src/asy_scd30_driver.py:27-31`), the shape C.4.2 calls the non-settled option. (low) | area: SENS | -
- INVAR | SPECIFICATION.md:1687-1689 | "Every method reachable before `finalize()` must guard against it explicitly (a private `self._finalized: bool` flag)" | Staged-construction guard obligation. | area: LED | related: LED.T03
- ASSUME | SPECIFICATION.md:1694-1695 | "(BMP3xx: 3 of 8 fields; SGP40: none; SCD30: all fields)" | Dated live-readback field counts. | area: SENS | -
- INVAR | SPECIFICATION.md:1695-1697 | "`asy_wifi_service.py`'s `callback=self._mask_pw` unconditionally overwrites the persisted `PW` with a fixed mask" | Masking contract (PUT-back of the mask seeded). | area: NET | related: NET.S16

## SPECIFICATION.md Part C.5 / C.5.1-C.5.3 (Config schema system, 1699-1797)
- PLATFORM | SPECIFICATION.md:1706-1708 | "A schema constant referenced inside another `const()`-wrapped tuple must itself be `const()`-wrapped — `const()` only folds references to other `const()`-defined names." | Compiler folding rule. | area: PLAT | related: PLAT.T02
- SETTLED | SPECIFICATION.md:1713-1716 | "`ConfigManager` carries three defensive type-mismatch catches ... as pure defense-in-depth ... don't remove them" | Kept catches; premise "REST validation already guarantees clean input". | area: CORE | -
- RISK | SPECIFICATION.md:1718-1721 | "constructing a `ConfigManager` with a schema narrower than the full production one is dangerous — `setup()` ... silently drops it on rewrite" | Operational hazard for scripts/tests; caller discipline only. | area: CORE | related: HW.T03
- SETTLED | SPECIFICATION.md:1729-1731 | "a plain sync `get_cfg_schema()` (no I/O, deliberately not `async`) ... `NeopixelDriver` is the one class with no schema" | Deliberate API shape. | area: CORE | -
- LIMIT | SPECIFICATION.md:1741-1745 | "Since WP5 ... `\"persisted\"` here really means \"validated and staged\" - a genuine disk write failure surfaces only later, as a logged `errno` on `cfgmgr.pr` ... none is expected to" | Client sees success before the flash write; settled. | area: CORE | related: CORE.T02
- INVAR | SPECIFICATION.md:1745-1748 | "A push callback always receives the coerced, persisted value, not the caller's raw one" | Setter contract. | area: CORE | related: CORE.T04
- INVAR | SPECIFICATION.md:1749-1752 | "For an `int`-typed field, narrow with `type(value) is not int`, not `isinstance` ... Every setter's return contract is uniformly `bool`" | bool-is-int convention; no guard named. | area: CORE | related: CORE.S12
- INVAR | SPECIFICATION.md:1761-1763 | "`get_dict_cfg()` must keep its own narrower explicit field list (excluding the special-alone field), since `ConfigManager.get_dict()` is all-or-nothing and would `KeyError`" | Command-only field constraint. | area: CORE | -
- INVAR | SPECIFICATION.md:1763-1766 | "a setter whose own return means something else (`reset_voc()`'s `False` = no-op, not failed) needs its wrapper to report success unconditionally" | Wrapper convention (SGP40 reset, SCD30 ContMeas). | area: SENS | -
- LIMIT | SPECIFICATION.md:1773-1777 | "deliberately not through `_push_callbacks` ... The caller-visible status stays `\"Failed\"` regardless of correction success — the repair is silent." | Recovery chain design; concurrency hazard seeded. | area: CORE | related: CORE.S05
- SETTLED | SPECIFICATION.md:1787-1788 | "A per-field failure never demotes the overall response below `\"OK\"`/`0` — detail lives in `\"result\"`." | Envelope convention. | area: REST | related: CORE.S06
- SETTLED | SPECIFICATION.md:1790-1792 | "every bool field is native JSON `true`/`false`, replacing legacy's `\"On\"`/`\"Off\"` string dtype. Only legacy `html_raw/` isn't updated (H.1)." | Deliberate wire change. | area: PAR | related: PAR.S06
- DRIFT | SPECIFICATION.md:1794-1797 | "`AsyConnTime` owns one schema but `/net/cmd`/`/led/cmd` each own only their own subset (`sensortask-wozi.py`'s `_cfg_subset(schema, keys)`)" | Routes and helper no longer exist (A.8 lists `/networking`). | area: DOC | covered-by: DOC.S09

## SPECIFICATION.md Part C.6 (Data model, 1799-1805)
- DRIFT | SPECIFICATION.md:1801-1805 | "via `repr()`-parsing ... Known dormant landmine: parsing splits on `\"(\"`/`\",\"`" | Seed says the code no longer repr()-parses. | area: DOC | covered-by: DOC.S09
- PLATFORM | SPECIFICATION.md:1802 | "not `_fields`/`_asdict()` (MicroPython's namedtuple provides neither)" | Port-feature claim to re-check at 1.29 (`MICROPY_PY_COLLECTIONS_NAMEDTUPLE__ASDICT`). | area: PLAT | related: PLAT.T13
- ASSUME | SPECIFICATION.md:1804-1805 | "Every current namedtuple is flat scalars only — check this first if a new driver adds a list/nested-tuple field" | Guard by review only. | area: CORE | -

## SPECIFICATION.md Part C.7 (Error handling & logging contract, 1807-1891)
- INVAR | SPECIFICATION.md:1810-1813 | "Known pitfall: a FRAM-backed history survives everything except an explicit reset, including a reflash — before treating a persisted `errcount`/history entry as evidence from *this* run, clear it first" | Tension with CLAUDE.md's read-FRAM-logs-BEFORE-clearing rule; order of operations is caller discipline. | area: HW | related: HW.T02
- SETTLED | SPECIFICATION.md:1817-1828 | "`reset()` writes unconditionally; `_store_err()` does not. The asymmetry is deliberate." | Fix for partial ResetErrors in the boot window (2026-09-11). | area: CORE | related: CORE.S04
- DRIFT | SPECIFICATION.md:1823-1826 | "every FRAM-backed logger runs its own `pr.setup()` from *inside its task* (... SYSTEM in `start_and_check_tasks()`)" | A.7:487-497 says conn/ntp/sysfunct loggers set up in the pre-task boot batch; which modules set up where is stated two ways. (low) | area: DOC | related: CORE.S03
- RISK | SPECIFICATION.md:1831-1840 | "A `ResetErrors` answering `OK` on a write the chip acknowledged but did not physically store is accepted behaviour, not a defect (owner decision, 2026-09-17" | Accepted: "if the bus transfer completed without error, the chip is trusted to have stored the value"; detected `_write()` False not reflected in the response. | area: STOR | related: REST.S04
- DRIFT | SPECIFICATION.md:1841-1843 | "re-run against the real FM25xx" | Chip family name (FM25xx, Cypress) vs MB85RS64V/MB85RS2MTA (Fujitsu) used everywhere else. (low) | area: DOC | related: HW.T07
- ASSUME | SPECIFICATION.md:1845-1849 | "WIFI's FRAM-backed log read `counter=3`, history `W5, W4, W4` before an abrupt `hard_reset()` and byte-identical values after it" | Single dated (2026-09-17) silicon observation. | area: HW | related: HW.T16
- ASSUME | SPECIFICATION.md:1850-1854 | "All 21 of `dev`'s chunks ... concurrent `GET /status` stayed at 0.56-0.76s throughout a `PUT` lasting 8.1s ... Its cost is fixed per chunk (~305ms)" | Dated silicon figures; load-case concern open in BACKLOG item 24. | area: PERF | covered-by: PERF.T03
- ASSUME | SPECIFICATION.md:1855-1860 | "Across a 20.8s window carrying three back-to-back `ResetErrors` calls (~6.9s each ...) ... 23 further transfers with zero failures" | Single silicon run supporting the UART never-block invariant. | area: UART | -
- INVAR | SPECIFICATION.md:1862-1865 | "`pr.err_s`/`pr.wrn_s` (async, persist to history/FRAM) for anything counting against `get_error_counter()`; `pr.err`/`pr.wrn` (sync, non-persisting)" | Log-tier contract (UART repeats via sync `pr.err` disputed). | area: CORE | related: UART.S01
- INVAR | SPECIFICATION.md:1867-1872 | "`base_classes.py` reserves `errno=1`-`9`/`wrnno=1`-`2` ... a driver's own numbering starts at 10+" | Numbering convention, explicitly unenforced (C.7.1:1896-1899). | area: XCUT | covered-by: XCUT.T07
- LIMIT | SPECIFICATION.md:1872-1874 | "A driver with no fixed, enumerable error-source list may assign numbers dynamically (`system_service.py`'s task-supervisor `wrnno=n + 1`)" | Persisted W-codes not stable across devices/versions. | area: XCUT | covered-by: XCUT.S07
- INVAR | SPECIFICATION.md:1879-1882 | "A call site with just one pass/fail flag passes a fixed one-element sentinel and drives the flag through `condition=`" | Style convention. (low) | area: SENS | -
- INVAR | SPECIFICATION.md:1883-1885 | "A per-field get/set forward always logs via `err_s()`/`wrn_s()` on failure, never a bare `except Exception: return None`" | Visibility convention. | area: SENS | related: SENS.T15
- INVAR | SPECIFICATION.md:1888-1891 | "a teardown/cleanup method on a class with no logger of its own must return `bool`, not `None`" | Silent-failure-masking convention (`AsyUDPSocket.disconnect()`, `WebserverService._close_writer()`, `UART.deinit()`). | area: CORE | -

## SPECIFICATION.md Part C.7.1 (Running errno/wrnno table, 1893-1941)
- INVAR | SPECIFICATION.md:1896-1900 | "a convention this table records, not one the code itself enforces — nothing raises if a new module picks a colliding number or starts below 10" | Explicitly unenforced catalogue. | area: XCUT | covered-by: XCUT.T07
- TODO | SPECIFICATION.md:1900-1906 | "Seven modules still number inside the reserved range ... Each is renumbered to 10+ on its next substantial change, not in one pass (owner decision, 2026-09-24)" | Deferred renumbering (config_manager, system_service, webserver, captive_dns, wifi, ntp, notification wrnno). | area: XCUT | related: XCUT.T07
- ASSUME | SPECIFICATION.md:1903-1904 | "No clash is live, since none shares a logger with a `SensorReader`." | Clash-freedom premise. | area: XCUT | -
- MIRROR | SPECIFICATION.md:1904-1906 | "a renumbering rides a change that already needs deploying, updating this table and its tests with it" | Table ↔ code ↔ tests three-way mirror. | area: DOC | -
- SETTLED | SPECIFICATION.md:1908-1921 | "A history is a bounded ring (ten slots per logger) ... the three answers differ on purpose" | Per-module episode definitions for `repeat=True` (UART one per episode; WiFi/FRAM one per distinct code). | area: XCUT | related: UART.T04
- DRIFT | SPECIFICATION.md:1910-1912 | "`repeat=True`, which still counts it and still writes the updated count through to FRAM" | UART repeats go to sync `pr.err()` which neither persists nor counts. | area: UART | covered-by: UART.S01
- DRIFT | SPECIFICATION.md:1926 | "`AsyFramManager` 10-88 ... (manager `errno` 17-88 + `wrnno` 80 ...)" | Row states the manager range two ways; code uses 10/11/19/20. | area: STOR | covered-by: STOR.S04
- DRIFT | SPECIFICATION.md:1926 | "the chunk logs into its OWNER's FRAM-backed history, not the manager's" | Code logs into the manager's RAM-only logger. | area: STOR | covered-by: XCUT.S08
- INVAR | SPECIFICATION.md:1926 | "because a synchronous body holding the bus lock must not await a persisted log entry" | Reporter split rule for FRAM. | area: STOR | related: STOR.S02
- DRIFT | SPECIFICATION.md:1929 | "`asy_isl29125_driver.py` (`ISL29125`) | 10-38 | ... 35=... 38=`set_range_auto()`" | Range 10-38 with 23, 36, 37 unassigned in the text. (low) | area: SENS | related: XCUT.T07
- INVAR | SPECIFICATION.md:1929, 1931, 1932 | "12 is retired, not reused" / "19 is retired, not reused" / "20 is retired, not reused" | Retired codes (ISL wrnno 12, WIFI errno 19, NTP errno 20) must never be reassigned; no guard. | area: XCUT | related: XCUT.T07
- PLATFORM | SPECIFICATION.md:1931 | "4 is cyw43-driver's catch-all for any failed auth or handshake ... not proof of a wrong password, BACKLOG item 29" | cyw43 status semantics. | area: NET | -
- ASSUME | SPECIFICATION.md:1936 | "`api_response.py`'s `handle_set_cmd()` | 99 | — | ... fixed at 99 since it runs against any registered module's `.pr`" | errno 99 lands in the calling module's history; collision with FRAM's own 99 or a future module's 99 not checked. (low) | area: CORE | related: CORE.S06
- ASSUME | SPECIFICATION.md:1939 | "Deliberately no logging — every failure surfaces to exactly one upstream owner. Coverage audit closed, no gaps." | Closed-audit claim for i2c/spi/udp/dns-client. | area: BUS | -
- DRIFT | SPECIFICATION.md:1940 | "(owner decision, 2026-09-18, )" | Empty trailing citation inside the parenthesis — a reference was dropped. (low) | area: DOC | -
- SETTLED | SPECIFICATION.md:1940 | "`wrnno` 11 outranks 10 for the episode's single slot (owner decision, 2026-09-18" | UART resync warning priority. | area: UART | -

## SPECIFICATION.md Part C.7.2 (Which failures may end a task, 1943-1973)
- INVAR | SPECIFICATION.md:1945-1949 | "A task ends — and the supervisor restarts it — only when the restart re-initialises something real" | Task-ending rule by convention. | area: XCUT | related: XCUT.T02
- SETTLED | SPECIFICATION.md:1949-1952 | "the NTP task used to end after six failed syncs ... (owner, 2026-09-24). The legacy client never gave up." | NTP handled in place. | area: NET | -
- MIRROR | SPECIFICATION.md:1954-1961 | "`retry_s` (default 10 s) doubling ... up to `retry_max_s` (default 600 s) ... `ntp_retry_s`/`ntp_retry_max_s`, checked by buildgen" | Defaults and the 10 s tick mirrored between NTP code and buildgen validation (`_NTP_CHECK_TICK_S`). | area: GEN | related: GEN.T06
- SETTLED | SPECIFICATION.md:1965-1969 | "Out of scope (owner, 2026-09-24): hardware that is inoperational from the start. Everything assumes defect-free hardware and a device config that matches it." | Init-failure reboot path excluded from C.7.2. | area: XCUT | related: SENS.T14
- MIRROR | SPECIFICATION.md:1970-1973 | "`buildgen/validate.py`'s `_check_uart_link_buses()`, reading the thresholds out of `asy_uart_comm.py`); every other refusal needs code the generator never emits" | Build-time check reads src constants; "never emits" is an assumption. | area: GEN | related: UART.T05

## SPECIFICATION.md Part C.7.3 (A failed config write costs persistence, 1975-2000)
- INVAR | SPECIFICATION.md:1985-1990 | "No write is ever retried ... exactly two write sites and nothing that re-runs either on its own (no timer, sleep or loop — pinned structurally by `tests/test_config_manager.py`)" | Enforced structurally by test. | area: CORE | related: CORE.T02
- SETTLED | SPECIFICATION.md:1995-2000 | "Bounded by boots, and deliberately no further - settled (owner, 2026-09-25). ... Don't add a cross-boot skip" | Do-not-reopen; one flash write attempt per boot while repair needed. | area: CORE | related: CORE.T12

## SPECIFICATION.md Part C.7.4 (Radio string bounds are bytes, 2002-2014)
- PLATFORM | SPECIFICATION.md:2004-2008 | "`network.country()` raises unless exactly 2 bytes, `network.hostname()` above 32 bytes, and `WLAN.connect()` raises `EINVAL` on a key over 64 bytes and copies an SSID over 32 bytes past its 36-byte buffer unchecked" | Pinned modnetwork/cyw43 limits, incl. an upstream unchecked copy. | area: NET | covered-by: NET.T07
- MIRROR | SPECIFICATION.md:2004, 2010-2014 | "The schema bounds every `str` field in characters (and the web UI mirrors that) ... `asy_wifi_service.py` now bounds ... in bytes" | Device checks bytes, web UI/mock check characters. | area: WEB | related: WEB.S12

## SPECIFICATION.md Part C.8 (Concurrency & locking model, 2016-2188)
- INVAR | SPECIFICATION.md:2024-2026 | "Lock ordering is fixed: always 2 before 1 — audited across every driver with no violation" | Audit claim; no mechanical guard. | area: XCUT | related: XCUT.T06
- SETTLED | SPECIFICATION.md:2028-2039 | "the FRAM path's is a whole block operation, not a single transaction (owner's decision, 2026-09-18)" | ~25 CS cycles per hold; I2C keeps per-transaction scope (F.5.8). | area: STOR | related: PERF.T04
- ASSUME | SPECIFICATION.md:2032-2034 | "it took a blank FRAM-backed logger `setup()` from 122,880 to 13,696 board-equivalent bytes" | Measurement cited to git-only archive §7C. | area: MEM | related: DOC.S04
- LIMIT | SPECIFICATION.md:2041-2044 | "`network_available()` requires the *caller* to already hold `wifi_mode_lock`, while its sibling getters assume the caller does *not* ... left as-is" | Known inconsistent lock contract. | area: NET | related: NET.S05
- RISK | SPECIFICATION.md:2044-2045 | "the 60s STA-retry branch holds `wifi_mode_lock` while NTP's sync task waits on it — an accepted priority-inversion cost, not a bug" | Accepted 60 s stall. | area: NET | covered-by: NET.S01
- RISK | SPECIFICATION.md:2047-2055 | "`writeto(0x00, b\"\\x06\")` is a true I2C general-call broadcast ... Low-risk, not fixed ... flagged for a project-owner decision if ever revisited" | Accepted risk; fires on every SGP40 restart. | area: SENS | related: SENS.T10
- ASSUME | SPECIFICATION.md:2050-2052 | "neither sibling's datasheet documents general-call listening, and address `0x00` gets no special handling in the pinned rp2 `machine_i2c.c`" | "Neither sibling" fits dev (SCD30/ISL29125, per the named test); wozi's i2c1 sibling is BMP3xx. (low) | area: SENS | -
- INVAR | SPECIFICATION.md:2057-2060 | "every promoted I2C/SPI device gets same-device read-vs-write concurrency coverage, cross-device interleaving coverage (if sharing a bus), and an address/command sweep, across as many of four tiers as apply" | Standing owner rule; review-enforced. | area: TEST | covered-by: SENS.T10
- SETTLED | SPECIFICATION.md:2062-2076 | "Mock/unit, two distinct collections, by design (project owner's own reframing, 2026-09-15)" | Sensor-specific hazards in driver files; generic in `test_bus_hazard_multi_device.py`, never retired. | area: TEST | -
- SETTLED | SPECIFICATION.md:2082-2088 | "The two are deliberately allowed to overlap in what they prove (layered coverage, not redundancy to prune)" | Overlap deliberate. | area: TEST | -
- INVAR | SPECIFICATION.md:2093-2098 | "ideally at most one real write per bus-hazard test group ... must construct the real protocol-layer driver directly (the DUT), never the `*_Reader` layer" | Owner-mandated write-safety constraints. | area: HW | related: HW.T01
- INVAR | SPECIFICATION.md:2099-2101 | "Extend the worker set only with requests safe under both constraints above (`GET` always safe; `PUT` only if documented command-only/never-persisted)" | "GET always safe" vs ISL GET writing chip/FRAM (SENS.S24). | area: HW | related: SENS.S24
- INVAR | SPECIFICATION.md:2114-2116 | "`build_bus_occupants()`/the address-sweep scenario both fail loud (`KeyError`) for a driver with none" | Enforced (adapters: scd30, sgp40, isl29125, bmp3xx). | area: TEST | -
- SUPPRESS | SPECIFICATION.md:2128-2138 | "SCD30's own on-chip NVM write is opt-in, off by default ... `--allow-persistence-writes`/`@pytest.mark.persistence_write` ... `--allow-scd30-extra-write`/`@pytest.mark.scd30_extra_write`, that is AND-gated" | Wear gates (deselect, not skip). | area: HW | covered-by: HW.T13
- LIMIT | SPECIFICATION.md:2139-2144 | "Real hardware has no literal equivalent of the mock tier's `asyncio.sleep(0)`-count offset sweep ... fires at one deliberately chosen representative offset instead" | Real-hardware timing sweep weaker than mock/twin. | area: HW | -
- ASSUME | SPECIFICATION.md:2145-2146 | "BMP3xx's/ISL29125's own config registers, both volatile per their datasheets" | Datasheet claim licensing unrestricted real writes. | area: SENS | -
- MIRROR | SPECIFICATION.md:2147-2152 | "whatever gets added to `tests_hardware/flash/test_bus_concurrency.py` gets a bench-tier counterpart ... never left as a silent asymmetry" | flash ↔ bench tier mirror obligation. | area: HW | related: HW.T09
- DRIFT | SPECIFICATION.md:2153-2155 | "No REST-layer path exists to the write at all — e.g. SCD30 registers zero `_push_callbacks`" | Seed says SCD30 NVM is reachable over REST via its own setter dispatch. | area: HW | covered-by: HW.S02
- ASSUME | SPECIFICATION.md:2156-2162 | "SGP40's real general-call broadcast only fires from `SGP40_I2C._reset()`, itself only called from `initialize()` at setup time ... confirmed by reading the real call chain" | Structural-exception claim. | area: HW | related: HW.T09
- SETTLED | SPECIFICATION.md:2163-2170 | "`test_bus_hazard_multi_device.py` is never retired (project owner's own reframing, 2026-09-15, superseding an earlier plan" | Permanent file. | area: TEST | -
- ASSUME | SPECIFICATION.md:2173-2183 | "`wozi` wires `sgp40`+`bmp3xx` together on `i2c1`, and `dev` wires `scd30`+`sgp40`+`isl29125` together on `i2c1` ... `arzi`/`klkizi`/`grkizi`/`schlafzi` each wire `scd30` alone on `i2c0` and `sgp40` alone on `i2c1`" | Doc copy of TOML bus topology (Session 6.2 check); goes stale on TOML change. | area: GEN | related: HW.S12
- ASSUME | SPECIFICATION.md:2184-2188 | "FRAM sits alone on its own dedicated SPI bus on every real device ... proven once, against one real assembled object graph (wozi)" | Topology assumption justifying wozi-only coverage. | area: TEST | -

## SPECIFICATION.md Part C.9 (Timer/task/IRQ integration contract, 2190-2209)
- LIMIT | SPECIFICATION.md:2193-2196 | "a task tied to a runtime mode transition (`asy_wifi_service.py`'s hotspot-mode DNS server task) is deliberately outside this generic supervision, a legitimate opt-out" | Unsupervised task by design. | area: XCUT | covered-by: XCUT.T05
- INVAR | SPECIFICATION.md:2198-2200 | "(default soft, no `hard=True` anywhere) whose callback only calls `.set()` on an `asyncio.ThreadSafeFlag` — never `time.sleep()` or business logic inside a callback" | Review-only rule; no lint guard found. | area: XCUT | related: XCUT.T04
- INVAR | SPECIFICATION.md:2200-2203 | "Use `Timer.PERIODIC`, not `ONE_SHOT`, for anything that must keep firing — a soft callback can be silently dropped" | ONE_SHOT used on critical paths per seed. | area: XCUT | covered-by: XCUT.S02
- INVAR | SPECIFICATION.md:2206-2209 | "Every `Timer.init()` failure handler catches `except (OSError, MemoryError) as e:`, not bare `OSError`" | Handler shape convention. | area: XCUT | related: XCUT.T04

## SPECIFICATION.md Part C.9.1 (Read-trigger timer stagger, 2211-2298)
- SETTLED | SPECIFICATION.md:2213-2224 | "Design intent (owner-established, not re-derived here) ... The one-second total spread is load-bearing and must not become a fixed per-task gap or be rescaled" | Owner design; do not re-propose. | area: XCUT | -
- DRIFT | SPECIFICATION.md:2226, 2230-2231, 2236 | "(this file)" / "three paragraphs up in Part A.7's boot-latency note" / "(WP6, this Part's own text above the timer stagger)" | Relative references copied from elsewhere; the boot batch lives in A.7, not Part C. (low) | area: DOC | -
- ASSUME | SPECIFICATION.md:2251-2259 | "never repeated - integer division of 1000 by up to a handful of distinct small divisors doesn't coincide in practice either, and even a tie would only delay, never invalidate, the argument" | Proof assumptions; seed disputes offsets (first at 0, accumulated latency, SCD30 500 ms collisions). | area: XCUT | covered-by: XCUT.S06
- PLATFORM | SPECIFICATION.md:2260-2272 | "a `Timer.PERIODIC`'s underlying Pico-SDK repeating alarm reschedules itself by returning `-self->delta_us` from its own alarm callback" | Pinned `ports/rp2/machine_timer.c` drift-freedom fact. | area: PLAT | related: PLAT.T03
- RISK | SPECIFICATION.md:2226-2227 | "starts each `get_timer_starters()` entry via a chain of `Timer.ONE_SHOT` callbacks" | The stagger itself rides soft ONE_SHOT callbacks that C.9 says can be dropped. | area: XCUT | covered-by: XCUT.S05
- LIMIT | SPECIFICATION.md:2273-2285 | "`asy_scd30_driver.py` does not use the counter-based mechanism ... the strict \"never coincide\" proof above applies rigorously to BMP3xx/ISL29125/SGP40" | SCD30 read moment is IRQ-modulated, outside the proof. | area: SENS | related: XCUT.S06
- LIMIT | SPECIFICATION.md:2286-2290 | "no new test was added for this WP, since it verifies and documents an existing, already-tested mechanism" | Proof has no test reading the real period. | area: TEST | covered-by: TEST.S06
- INVAR | SPECIFICATION.md:2292-2298 | "a retry loop that fails non-raising (returns a sentinel) needs its own capped exponential backoff ... A retry loop never ends its task to \"retry by restart\"" | Convention; captive DNS 0.5→4 s (cap 5 s). | area: NET | -

## SPECIFICATION.md Part C.10 (Typing conventions, 2300-2308)
- INVAR | SPECIFICATION.md:2302-2303 | "`TYPE_CHECKING` guarded via `try/except ImportError: TYPE_CHECKING = False`, never unconditional. PEP 604 `X | None` everywhere" | Typing conventions (UP007 enforces the `Union` half; the guard shape is also what `_strip_type_checking.py` matches). | area: CORE | related: GEN.S12

## SPECIFICATION.md Part C.11 / C.11.1 (Design decisions; conformance probe, 2310-2353)
- DRIFT | SPECIFICATION.md:2321-2322, 2326 | "SGP40's VOC-algorithm backup is the only, and largest, current example" / "same shape as the existing three" | Stale counts (five chip fakes exist: scd30, sgp40, bmp3xx, isl29125, fram). | area: DOC | covered-by: DOC.S08
- LIMIT | SPECIFICATION.md:2327-2329 | "A new SPI sensor sharing an already-occupied SPI bus id with the FRAM chip is not automatically supported by the twin's single-device-per-bus-id wiring." | Twin fidelity gap for shared SPI buses. | area: TWIN | related: DOC.S22
- INVAR | SPECIFICATION.md:2325-2333 | "Digital-twin extension — required, not optional ... Do this the same session as promotion ... Also update `html/definitions/<device>.json` ... Same session, not deferred." | Review-only promotion obligations; definitions hand-update contradicts K.4/K.8. | area: TWIN | covered-by: DOC.S03
- LIMIT | SPECIFICATION.md:2337-2344 | "A chip fake drifts from the part it models silently: every test still passes, because the tests and the fake share the same wrong assumption." | Stated fake-fidelity risk; guard exists only for ISL29125. | area: TWIN | covered-by: TEST.S20
- TODO | SPECIFICATION.md:2346-2349 | "The ISL29125 is the first driver with one ... Build one for every new bus-facing chip." | No probe for SCD30/SGP40/BMP3xx/FRAM. | area: TEST | covered-by: TEST.S20
- SUPPRESS | SPECIFICATION.md:2346-2348 | "gated by `tests_hardware/flash/test_sensor_accuracy.py::test_isl29125_register_probe_matches_the_digital_twins_fake_chip`" | The only conformance check runs only on the gated flash tier. | area: HW | -
- SETTLED | SPECIFICATION.md:2351-2353 | "Chip-specific facts go to Part M, not here." | Doc-placement rule. | area: DOC | -

## SPECIFICATION.md Part C.12 (Testing, 2355-2361)
- PLATFORM | SPECIFICATION.md:2359-2361 | "real hardware only raises `OSError(EIO)` or `OSError(ETIMEDOUT)` — never `ENODEV` (`SoftI2C`-specific)" | rp2 hardware-I2C error set tests must model. | area: BUS | related: TEST.T05

## SPECIFICATION.md Part C.13 (Readiness-gate scheme, 2363-2378)
- INVAR | SPECIFICATION.md:2368-2372 | "Gate name/polarity is standardized: `self.initialized: bool = False → True` — except ... `ConfigManager.valid`" | Naming convention with one exception. | area: CORE | covered-by: XCUT.T12
- INVAR | SPECIFICATION.md:2373-2378 | "The response to \"called before `setup()` ran\" must match the class's already-declared raise/never-raise contract — verify per class, don't assume" | Per-class obligation. | area: XCUT | covered-by: XCUT.T12

## SPECIFICATION.md Part C.14 / C.14.1 (Instance naming, 2380-2428)
- DRIFT | SPECIFICATION.md:2382-2384 | "Session 1 of the device-genericization initiative ... (Session 3 on) ... as of Session 6" | Undefined "Session N" labels. (low) | area: DOC | related: DOC.S16
- SETTLED | SPECIFICATION.md:2386-2390 | "singleton services (WiFi/NTP/SystemService/Neopixel/NotificationCoordinator/FRAM/the DNS server/the webserver) are deliberately out of scope for the *naming* part" | Singletons never multi-instanced. | area: GEN | related: GEN.T13
- INVAR | SPECIFICATION.md:2405-2418 | "REST dict keys must use `self.name` too, not a driver's `_NAME` module constant ... applied uniformly across every promoted driver" | Multi-instance key rule; "three promoted drivers" count stale. | area: SENS | related: GEN.T04
- ASSUME | SPECIFICATION.md:2420-2422 | "The default (empty extension) case reproduces every existing path/filename/dict-key byte-for-byte" | Claimed and tested by `tests/test_config_manager.py` + per-driver regression tests. | area: CORE | -
- INVAR | SPECIFICATION.md:2424-2428 | "Collision detection across a whole device's instance list is built in `buildgen/validate.py`" | Enforced by `_check_instance_name_collisions()`/`_check_instance_label_collisions()`. | area: GEN | -

## SPECIFICATION.md Part C.14.2 (The `_WIRING` convention, 2430-2532)
- DRIFT | SPECIFICATION.md:1517-1519 vs 2443-2449 | "`_WIRING: \"WiringSchema\" = ((toml_field_name, required_driver_class),)`" vs "A comment, never a real Python value ... It was a real `_WIRING` tuple until 2026-09-10" | C.2 still documents `_WIRING` as a 2-element Python tuple; C.14.2 says it is a 5-field `# @wiring` comment. | area: DOC | -
- INVAR | SPECIFICATION.md:2443-2446 | "Nothing the running firmware itself ever reads should become a real frozen-bytecode value just to serve the generator (SPECIFICATION.md Part L.5)" | Tag-as-comment rule. | area: GEN | related: GEN.T03
- ASSUME | SPECIFICATION.md:2446-2448 | "converting it, plus `_VALUE_WIRING`, `_LIMITS` and the `TYPE_CHECKING` type aliases ... took 3,576 bytes out of `src/`'s frozen bytecode" | Dated single measurement. | area: GEN | -
- INVAR | SPECIFICATION.md:2448-2449 | "dropping any one of the five makes the tag fail the build loud rather than parse as \"no tag here\" (`tag_comments.py`)" | Enforced by buildgen parser. | area: GEN | covered-by: GEN.T03
- DRIFT | SPECIFICATION.md:2469 | "This reuses the existing comment-tag family (`@requires`, and the planned `@web`)" | `@web` is implemented (CLAUDE.md lists it as live buildgen input). | area: DOC | related: GEN.S14
- DRIFT | SPECIFICATION.md:2493-2499 | "`asy_notification_service.py` imports `NeopixelDriver` from `asy_neopixel_driver.py` at module level ... every `fram_target`-wirable driver similarly imports `AsyFramManager`" | No `NeopixelDriver` import exists; `AsyFramManager` imports are TYPE_CHECKING-only (e.g. `src/asy_notification_service.py:29`, `src/asy_sgp40_driver.py:34`). | area: DOC | -
- ASSUME | SPECIFICATION.md:2506-2510 | "a real, deliberate reordering of wozi's FRAM chunk allocation order, safe only because wozi is never physically flashed (CLAUDE.md)" | Safety premise specific to wozi. | area: XCUT | related: PAR.S13
- DRIFT | SPECIFICATION.md:2510-2514 | "plus two fixed mandatory-infra edges and one conditional one (`sysfunct` needs its own `device.wiring.fram_target` instance, if set)" | A.7:390-392 says conn/ntp/sysfunct each get a conditional edge onto `fram`. (low) | area: DOC | -
- INVAR | SPECIFICATION.md:2517-2528 | "every `*_Reader` constructs its namedtuple with every field `None` before any real read ... Every direct-reference consumer tolerates that as a normal, expected input" | Producer/consumer initial-value contract. | area: XCUT | related: XCUT.T17
- ASSUME | SPECIFICATION.md:2530-2532 | "a full audit for the same class of bug ... found no other occurrence in `src/`" | Dated (2026-09-12) negative audit claim. | area: XCUT | -

## SPECIFICATION.md Part C.14.3 (Error-source and logger fan-in, 2534-2572)
- INVAR | SPECIFICATION.md:2536-2545 | "implements `get_error_sources(self) -> list[Any]` and `get_loggers(self) -> list[PrintLogHistory]`, structurally (duck-typed" | Duck-typed fan-in contract; no Protocol check at wiring time. | area: XCUT | related: XCUT.T08
- ASSUME | SPECIFICATION.md:2565-2567 | "every real `devices/*.toml` compensates both off one `SCD30_Reader`" | Doc copy of TOML facts. | area: GEN | -
- LIMIT | SPECIFICATION.md:2569-2572 | "a required field with nothing wired can still build clean via an explicit `{default = true, ...}` opt-in ... `_DefaultTemperatureSource`/`_DefaultHumiditySource` provide a constant fallback" | Constant compensation fallback possible by config. | area: SENS | related: SENS.T12

## SPECIFICATION.md Part D (src/ Production-Quality Checklist, 2576-2728)
- INVAR | SPECIFICATION.md:2593-2594 | "If verification surfaces a discrepancy, do not silently change it — flag and ask before altering real output." | Owner rule for formula/behaviour discrepancies; review-only. | area: XCUT | -
- ASSUME | SPECIFICATION.md:2595-2598 | "`wet_bulb_temperature`'s humidity lower bound was `0.5%`; Stull (2011) only validates to `5%` ... (`altitude_baro`'s range comes from the BMP388/390 datasheet" | Literature/datasheet domain claims; the BMP390 PDF is absent (A.6). | area: ALGO | related: SENS.S12
- RISK | SPECIFICATION.md:2606-2608 | "Don't defend against out-of-contract input at runtime if static typing already enforces it (mypy)" | Premise holds only where no untyped runtime input (JSON, TOML, restored FRAM state) can reach the function. | area: XCUT | related: ALGO.T05
- PLATFORM | SPECIFICATION.md:2612-2614 | "I2C raises broadly; SPI raises only from a 32+ byte read (F.5.2), never from a write; UART never raises from a transfer at all." | Per-bus raise surface on rp2 1.29. | area: BUS | related: BUS.T01
- DRIFT | SPECIFICATION.md:2618 | "Units run years without a reboot" | Same lifetime-claim tension as A.2:125 vs CLAUDE.md "months". (low) | area: DOC | -
- LIMIT | SPECIFICATION.md:2620-2621 | "Verified via design discipline and reading — no CI gate for \"ran a simulated year.\"" | Long-uptime stability untested (cf. ticks wraparound XCUT.T25). | area: TEST | related: XCUT.T25
- PLATFORM | SPECIFICATION.md:2625 | "Dual-core Cortex-M0+ @ up to 133MHz, 264KB SRAM (F.1)" | Silicon facts. | area: PLAT | -
- INVAR | SPECIFICATION.md:2631-2632 | "No blocking I/O, `time.sleep`, or unbounded loops." | Absolute rule with stated exceptions elsewhere (C.3.1 blocking `sleep_us(2)`; FRAM sync path). | area: PERF | related: PERF.T08
- PLATFORM | SPECIFICATION.md:2638-2643 | "`typing` isn't importable at all on the Unix-port test interpreter. `mpy-cross` does not dead-code-eliminate `if TYPE_CHECKING:` blocks" | Interpreter/compiler facts behind the guard and strip step. | area: PLAT | -
- SETTLED | SPECIFICATION.md:2645-2648 | "Quoting annotations (owner decision, 2026-09-24) ... existing files are not mass-edited to the rule" | Rule applies to new/touched lines only; mixed style accepted. | area: CORE | -
- INVAR | SPECIFICATION.md:2653-2655 | "mypy catches most of this — still read every `return` by eye" | Review-only. (low) | area: XCUT | -
- INVAR | SPECIFICATION.md:2659-2661 | "observable behavior stays identical for every valid input — a hard constraint, the full test suite must still pass unchanged" | Improvement-pass constraint. | area: XCUT | -
- PLATFORM | SPECIFICATION.md:2665-2670 | "the build target has moved to the latest stable (currently v1.29.0 — the last pass's findings are catalogued in Part F.5)" | Version-pinned statement to update on bump. | area: PLAT | related: PLAT.T06
- INVAR | SPECIFICATION.md:2674-2680 | "Give every member of a related set the same shape ... flag a questionable existing convention rather than silently diverging. An ongoing, project-wide check." | D.10 review obligation. | area: XCUT | related: XCUT.T15
- INVAR | SPECIFICATION.md:2684-2686 | "Per-function explanations are `#` comments, never docstrings mixed into an individual function." | Holds today (0 function docstrings in `src/`); not mechanically gated. | area: DOC | -
- INVAR | SPECIFICATION.md:2699-2701 | "a valid typical input against a sanity bound, not an exact reference value" | Test-oracle policy (weak oracles by design). | area: TEST | related: ALGO.T07
- INVAR | SPECIFICATION.md:2703-2705 | "module-level tests mocking only the raw bus transaction aren't enough — add integration tests driving the same scenarios through the actual real chain" | Test obligation. | area: TEST | -
- MIRROR | SPECIFICATION.md:2709-2710 | "Extend the lint/typecheck config's scope and CI's explicit path arguments to the new location." | lint scope ↔ CI explicit paths hand-mirrored. | area: CI | related: CI.S03
- INVAR | SPECIFICATION.md:2722-2724 | "A pure reorder ... verified via an AST-level comparison, not just a visual diff" | No tool named for the AST comparison. | area: CORE | related: CORE.T09

## SPECIFICATION.md Part E intro, E.1 (2732-2788)
- MIRROR | SPECIFICATION.md:2746-2747 | "cross-file invariants that can only be checked by reading real source text (`scripts/test.sh`'s own step ordering; the `outer_cap_s` ceiling's mirrors, Part H.4)" | Hand mirrors guarded by source-reading pytest tests. | area: TEST | related: GEN.T06
- INVAR | SPECIFICATION.md:2753-2756 | "every step that globs `devices/*.toml` must run before the background launch, because one `tests_scripts/` test necessarily writes a throwaway `devices/zz_test_*.toml` into the live tree" | Enforced by `tests_scripts/test_test_sh.py`. | area: SCR | related: SCR.T14
- RISK | SPECIFICATION.md:2758-2764 | "removes its own file in `finally`, which a SIGKILL ... defeats ... A leaked one ... aborts that script, `scripts/typecheck.sh` and both twin runners outright" | Test writes into the live tree; mitigated by an up-front sweep. | area: SCR | covered-by: TEST.T13
- INVAR | SPECIFICATION.md:2767-2781 | "Two per-file resources must stay disjoint ... A new test file that binds a socket claims an unused base below 32768 — never a neighbour's, never inside the ephemeral range." | Review-only; found violated before (2026-09-17) and again per seed. | area: TEST | covered-by: TEST.S21
- PLATFORM | SPECIFICATION.md:2771-2774 | "inside the OS ephemeral range (32768-60999) ... For UDP both modes are silent rather than `EADDRINUSE`" | Host-Linux default range assumed. | area: TEST | -

## SPECIFICATION.md Part E.2 / E.2.1 (Test framework; per-device libraries, 2790-2826)
- LIMIT | SPECIFICATION.md:2792-2794 | "`microtest.py` is a minimal collector/runner ... report PASS/FAIL, exit non-zero on failure" | Runner-level vacuity classes. | area: TEST | covered-by: TEST.S23
- SETTLED | SPECIFICATION.md:2809-2817 | "Why the split exists is memory ... a fix at the root, not a per-file heap override or a `gc.collect()` prop" | Measured 2026-09-17 (~29 → ~11 builds). | area: TEST | -
- LIMIT | SPECIFICATION.md:2823-2826 | "keeps its heavier tests wozi-only ... a ×6 parametrization would buy nothing" | Deliberate single-device coverage. | area: TEST | -

## SPECIFICATION.md Part E.3 / E.3.1 (Running; heap and timeouts, 2828-2921)
- PLATFORM | SPECIFICATION.md:2841-2846 | "`.frozen` is a literal MicroPython sentinel, not an ordinary directory" | Needed on MICROPYPATH. | area: PLAT | -
- INVAR | SPECIFICATION.md:2864-2866 | "Never write the verdict to `$GITHUB_STEP_SUMMARY`" | Pinned by `tests_scripts/test_test_sh.py`. | area: SCR | -
- SETTLED | SPECIFICATION.md:2870-2873 | "`-X heapsize=16M` ... must never be raised as a fix" | Do-not-reopen (CLAUDE.md). | area: TEST | -
- ASSUME | SPECIFICATION.md:2885-2890 | "reproducibly misses its own 9-second real-clock budget at 8M ... So 16M is a measured floor across every file" | Heap floor tied to a timing-sensitive test; dated measurement. | area: TEST | related: TEST.T04
- SETTLED | SPECIFICATION.md:2892-2896 | "`PER_FILE_TIMEOUT_S` (default 240) plus two retries is a standing backstop" | Keep even after hangs are fixed. | area: SCR | -
- PLATFORM | SPECIFICATION.md:2897-2898 | "MicroPython block-buffers 4096 bytes whenever stdout is not a tty" | Reason for `stdbuf`. | area: PLAT | -
- ASSUME | SPECIFICATION.md:2900-2907 | "Per-file overrides exist but the table is empty ... 114.8s/59.5s ... Re-measure and re-add an entry if a future device pushes one past the default." | Dated timings; manual re-measure trigger. | area: SCR | -
- DRIFT | SPECIFICATION.md:2918 | "validated once in `scripts/test.sh` rather than 85 times" | Stale file count. | area: DOC | covered-by: DOC.S08
- LIMIT | SPECIFICATION.md:2920-2921 | "`--coverage` has its own runner and says so out loud when both are given, rather than silently ignoring the threshold" | Coverage run never applies `GC_THRESHOLD`. | area: SCR | -

## SPECIFICATION.md Part E.4 (Mock at the raw bus-transaction level, 2923-2949)
- ASSUME | SPECIFICATION.md:2932-2935 | "Two Protocol-level failure scenarios (`get_chunk()` raising) have no real-class equivalent anymore (the real class is audited never to raise there)" | Tests of an unreachable contract via a local fake. | area: TEST | -
- INVAR | SPECIFICATION.md:2939-2949 | "`_StarvedAlloc` ... must be armed and one-shot ... must restore the global in `__exit__` ... Reach for it only where a real `MemoryError` is genuinely unreachable" | Sanctioned allocator mock rules; review-only. | area: TEST | related: TEST.T06

## SPECIFICATION.md Part E.5 / E.5.1-E.5.3 (Coverage, 2951-3088)
- SETTLED | SPECIFICATION.md:2957-2958 | "No threshold enforced anywhere — CI reports numbers, never gates." | Coverage never gates. | area: CI | -
- TODO | SPECIFICATION.md:2965-2966 | "`coverage.xml` uploads to Codecov, but that account-linking hasn't been done, so it currently no-ops silently" | Pending registration. | area: CI | -
- DRIFT | SPECIFICATION.md:2966-2967 | "(Session 8's closing-consistency-pass PR split it out of `unit-tests` proper)" | Undefined "Session 8" label. (low) | area: DOC | related: DOC.S16
- PLATFORM | SPECIFICATION.md:2974-2982 | "The rule is the leading underscore, verified at source (`py/parse.c`, the `MICROPY_COMP_CONST` fold) ... A bare `while True:` header never fires its own trace event" | Tracer false-negative patterns; "all 58" constants a dated count. | area: TEST | covered-by: TEST.T09
- SETTLED | SPECIFICATION.md:2984-3002 | "left as documented dead code rather than chased for a coverage number ... confirmed intentional by the project owner" | Unreachable-branch register (print_log `get_log()` sentinel owner-confirmed; UART six re-checks; UART driver `except MemoryError`). | area: TEST | -
- ASSUME | SPECIFICATION.md:3004-3017 | "Four more of the same class, enumerated on 2026-09-22 ... `voc_algorithm.py`'s `_FIX16_OVERFLOW` return ... unreachable ... 31 genuinely uncovered lines across 8 files, all of which now have tests" | Dated unreachability claims (VOC overflow disputed vs C int32 semantics). | area: TEST | related: ALGO.S01
- ASSUME | SPECIFICATION.md:3008-3009 | "`asy_sgp40_driver.py`'s `readlen is None` early return (no caller passes it — the buffer above is sized for the one `readlen=1`" | Serial read length seeded as a datasheet deviation. | area: SENS | related: SENS.S21
- ASSUME | SPECIFICATION.md:3030-3043 | "measured false on 2026-09-18 ... `py/profile.c:190` ... 651,680 B | 137,120 B (4.75x)" | Dated allocation table; line-anchored upstream citation. | area: MEM | -
- SETTLED | SPECIFICATION.md:3046-3049 | "builds two Unix-port variants rather than one (owner decision, 2026-09-21)" | Duplicate of B.2's decision. | area: TOOL | -
- LIMIT | SPECIFICATION.md:3053-3060 | "The build directory's path no longer identifies its variant ... locally, `scripts/test.sh` asks the binary itself" | Only test.sh probes; other runners check `-x`. | area: SCR | covered-by: SCR.S05
- LIMIT | SPECIFICATION.md:3061-3063 | "`--coverage`'s own figures stay inflated, inherently ... never as an allocation measurement" | Coverage-mode allocations meaningless. | area: TEST | -
- DRIFT | SPECIFICATION.md:3062-3063 | "HEAP_FRAGMENTATION_MEASUREMENTS.md §M3.7 (archive §1.2 item 7 and §3A)" | Archive § citations resolve only in git history. | area: DOC | covered-by: DOC.S04
- SETTLED | SPECIFICATION.md:3067-3088 | "`scripts/test.sh` now exits: 0 / 1 / 3 ... the owner's decision of 2026-09-22 chose this split" | Exit-code contract; renderer `|| coverage_render_failed=1` guards. | area: SCR | covered-by: SCR.T01
- SUPPRESS | SPECIFICATION.md:3084 | "Both `_render_coverage.py` invocations are `|| coverage_render_failed=1`-guarded" | Deliberate failure capture (exit 3 tolerated in CI). | area: SCR | -
- DRIFT | SPECIFICATION.md:3071-3072 | "(`tests/test_uart_comm_hazard.py`, 84/85) on a tree whose (e) and (f) stages were both 85/85" | Stale file count. | area: DOC | covered-by: DOC.S08

## SPECIFICATION.md Part E.6 / E.6.1-E.6.6 (Shared behaviours, real-hardware tier, 3090-3225)
- SETTLED | SPECIFICATION.md:3092-3096 | "don't force further sharing onto genuinely backend-specific coverage" | Test-sharing scope decision. | area: TEST | -
- ASSUME | SPECIFICATION.md:3104-3107 | "Both tiers run clean end to end on real hardware; the earlier WiFi-reconnection flakiness ... is root-caused and mitigated" | Undated status claim. | area: HW | related: HW.T16
- SETTLED | SPECIFICATION.md:3123-3130 | "Credential rotation is deliberately not a bench capability (owner decision, 2026-09-22)" | Removed `rotate_ap_password()`. | area: HW | -
- INVAR | SPECIFICATION.md:3144-3145 | "Documentation discipline (each shared function's docstring states applicable/N/A backends), not an automated check." | Review-only. | area: TEST | -
- LIMIT | SPECIFICATION.md:3154-3157 | "a trailing soft reset only restores the *appearance* of normal operation ... only a genuine `hard_reset()` reliably resumes the live system" | Isolated-driver mode caveat. | area: HW | related: HW.T06
- LIMIT | SPECIFICATION.md:3161-3162 | "The RP2040's own hotspot/AP mode is untestable in the digital twin (no AP-mode DHCP/second-radio model)." | Twin fidelity gap. | area: TWIN | related: TWIN.S05
- RISK | SPECIFICATION.md:3165-3169 | "a failed real-credential PUT lands in `_PHASE_DEACTIVATED` (a terminal state, A.4) ... hence the fixture's real `hard_reset()` fallback" | Role-reversal can strand WLAN deactivated. | area: HW | covered-by: HW.S25
- ASSUME | SPECIFICATION.md:3164-3165 | "a real, source-traced ~15-20s timing budget from a credential PUT to the DUT's first STA attempt" | Timing premise. | area: HW | -
- ASSUME | SPECIFICATION.md:3173-3176 | "FRAM (166 mock vs. 18 twin tests) ... one real cluster (Sensortask: 4 near-identical ... pairs)" | Dated counts. | area: TEST | covered-by: TEST.T15
- INVAR | SPECIFICATION.md:3184-3191 | "every mock/digital-twin test that exercises real-hardware-facing behavior needs a real-hardware equivalent, wherever technically possible" | Standing owner rule; review-only. | area: HW | related: TEST.T06
- SETTLED | SPECIFICATION.md:3196-3201 | "Only `dev` is ever physically bench-tested ... real-hardware parity for anything specific to one of them is structurally impossible" | Exception 1. | area: HW | -
- DRIFT | SPECIFICATION.md:3202-3207 | "SCD30 has zero REST-pushable fields (`asy_scd30_driver.py` registers no `_push_callbacks`), so no bench-tier `PUT` can ever reach its own NVM write" | Disputed: SCD30 dispatches PUTs via its own setters. | area: HW | covered-by: HW.S02
- SETTLED | SPECIFICATION.md:3212-3219 | "The UART fault-injection catalog stays mock-only until injection hardware exists (owner decision, 2026-09-22)" | Deferred; revisit trigger = hardware exists. | area: UART | -
- TODO | SPECIFICATION.md:3218-3219 | "Revisit when that hardware exists." | Deferred real-hardware UART fault injection. | area: HW | -

## SPECIFICATION.md Part E.7 (Twin soak wall clock measures GC timing, 3229-3269)
- DRIFT | SPECIFICATION.md:3235 | "where `gc` collections land on the Unix port's 8 MB heap" | E.3.1 says the test heap is 16M now; the 8 MB figure is from the retired run_dev_integration measurement. (low) | area: DOC | -
- ASSUME | SPECIFICATION.md:3240-3253 | "Measured on the dev variant (2026-09-11) ... 44.07 / 58.43 / 61.49 s" | Dated measurement against a retired runner. | area: TWIN | -
- SETTLED | SPECIFICATION.md:3257-3261 | "Never bisect a twin soak's runtime to a code change." | Do-not-re-diagnose rule. | area: TWIN | -
- INVAR | SPECIFICATION.md:3262-3265 | "A soak's own timing budget is a liveness backstop, not a performance assertion, so it belongs above the whole observed range" | Test-design rule. | area: TEST | related: TEST.T04

## SPECIFICATION.md Part E.8 (Measurement traps, 3271-3362)
- INVAR | SPECIFICATION.md:3276-3287 | "An absolute heap-delta bound is host-dependent; a leak is a rate." | Absolute heap bounds still exist per seed. | area: TEST | covered-by: TEST.S12
- ASSUME | SPECIFICATION.md:3280-3281 | "`< 6.0 B/transaction` and `< 16.0 B/failure`, against a real retained frame's 13+ B/transaction and an injected 16 B/transaction leak's measured 636" | Measured thresholds in `tests/test_uart_comm_hazard.py`. | area: TEST | -
- LIMIT | SPECIFICATION.md:3288-3299 | "The twin's `UARTLink.wire_log` is unbounded ... Fixed by giving `run_generic_integration.py` its own periodic clearer (`_wire_log_clearer()`, every 5s" | Twin fake grows without bound; mitigated by clearer. | area: TWIN | -
- LIMIT | SPECIFICATION.md:3300-3301 | "An asyncio loop-latency probe cannot separate \"idle on a timer\" from \"blocked.\"" | Measurement limitation. | area: PERF | related: PERF.T09
- LIMIT | SPECIFICATION.md:3304-3305 | "`I2C.scan()` is synchronous and blocks the loop for a 128-address sweep ... inflated a measured worst-case RTT from 112 ms to 574 ms" | Load-model trap. | area: PERF | -
- LIMIT | SPECIFICATION.md:3306-3308 | "Cross-test contamination is real. One process, one task queue, and no parent/child tracking in MicroPython asyncio" | Per-test numbers unreliable without isolation. | area: TEST | covered-by: TEST.T07
- LIMIT | SPECIFICATION.md:3309-3317 | "A 64-bit twin doubles dicts, lists and frames but not strings ... a non-frozen one spends ~541 KB on imports ... an unthrottled twin serves 50-100x faster than the board" | Twin heap/throughput infidelity. | area: TWIN | covered-by: TWIN.T06
- ASSUME | SPECIFICATION.md:3318-3321 | "`gc.threshold(32768)` hid it in the twin by re-placing the working set, and on silicon at peak did not reduce failures at all" | Silicon finding (git-only archive §7Q.11). | area: MEM | related: DOC.S04
- INVAR | SPECIFICATION.md:3322-3334 | "Collect before any heap sample, and say so ... Never let the offered load scale with the setting under test ... Ballast guards use the largest free run, never `gc.mem_free()`" | Measurement rules; review-only. | area: MEM | related: TEST.T03
- LIMIT | SPECIFICATION.md:3335-3337 | "`ErrNum` mixes errnos and wrnnos in one ring sharing a number space ... Filter on `ErrType == \"E\"`." | Log-reading trap from shared number spaces. | area: CORE | related: XCUT.T07
- LIMIT | SPECIFICATION.md:3339-3345 | "regressing each of `asy_uart_driver.py`'s seven read paths in turn ... four failed a named test, three passed silently" | Guard-is-blind finding (2026-09-12). | area: TEST | covered-by: TEST.T02
- DRIFT | SPECIFICATION.md:3344-3345 | "the same standard I3.4's revert-and-confirm pass applies to fixes" | "I3.4" ID resolves to no SPEC Part (Part I uses `I.n`). (low) | area: DOC | related: DOC.T02
- INVAR | SPECIFICATION.md:3347-3357 | "Run it as a scripted sweep, not by hand ... restore the file in a `finally` regardless" | Mutation-sweep method; no committed sweep script named. | area: TEST | related: TEST.T02
- PLATFORM | SPECIFICATION.md:3355-3356 | "because `bool` is not an `int` subclass here at all (F.1)" | MicroPython-specific type fact. | area: PLAT | -
- INVAR | SPECIFICATION.md:3359-3362 | "every hazard check runs in both CRC modes ... 48 checks, 96 tests ... The deployed link runs `CRC_Pass`" | Standing rule; counts dated; dev link is uncrc'd. | area: UART | related: UART.S04

## SPECIFICATION.md Part E.9 (Driver/DUT process separation, 3364-3421)
- INVAR | SPECIFICATION.md:3366-3372 | "Anything that can run outside the digital twin's own MicroPython process without losing coverage must run outside it." | Standing rule; review-only. | area: TWIN | -
- INVAR | SPECIFICATION.md:3374-3378 | "Get it out through the narrowest possible channel (a log line on a fixed timer ... `_mem_sampler()`)" | DUT-side exception. | area: TWIN | -
- SETTLED | SPECIFICATION.md:3385-3387 | "keeps only `_mem_sampler()` ... plus the `gc.collect()` that settles it before each sample (I.4(e)'s own narrow, separately-litigated exception)" | Approved `gc.collect()` in the twin runner. | area: MEM | related: TEST.T03
- INVAR | SPECIFICATION.md:3396-3401 | "A fix under this rule must come out strictly more capable of catching the real test case, never merely lighter on the DUT" | Rule. | area: TEST | -
- WORKAROUND | SPECIFICATION.md:3403-3417 | "`_mem_trend()` ... now derives the tolerance from each attempt's own observed noise ... `_run_11_soak()` also retries once" | CI-noise workaround (autocorrelated samples); retry only on the trend check. Removal trigger none stated. | area: SCR | -
- ASSUME | SPECIFICATION.md:3404-3406 | "two independent `wozi` boots in a row, 3298/2854 and 4361/2847 bytes" | Dated measurement. | area: TWIN | -
- RISK | SPECIFICATION.md:3415-3418 | "a real leak reproduces past tolerance on both independent boots, transient noise essentially never does" | Retry can mask an intermittent real leak; accepted. | area: TEST | -

## Coverage
| Part/subsection | doc lines read | items |
|---|---|---|
| Front matter | 1-28 | 2 |
| A.1 | 29-92 | 6 |
| A.2 | 94-127 | 6 |
| A.3 | 129-146 | 4 |
| A.4 | 148-285 | 30 |
| A.5 | 287-335 | 9 |
| A.6 | 337-356 | 6 |
| A.7 | 358-569 | 27 |
| A.8 | 571-625 | 11 |
| A.9 | 627-653 | 4 |
| A.10 | 655-686 | 3 |
| B intro, B.1-B.3 | 688-753 | 8 |
| B.4-B.9 | 754-826 | 8 |
| B.10/B.10.1 | 828-929 | 15 |
| B.11 | 931-984 | 11 |
| B.12 | 986-1014 | 4 |
| B.13 | 1016-1061 | 7 |
| B.14 | 1063-1114 | 6 |
| B.14.1 | 1116-1213 | 10 |
| B.14.2/B.14.2.1 | 1215-1379 | 15 |
| B.14.3 | 1381-1410 | 4 |
| B.15 | 1413-1473 | 11 |
| C intro, C.1-C.2 | 1475-1535 | 7 |
| C.3 | 1537-1566 | 8 |
| C.3.1 | 1567-1596 | 4 |
| C.3.2 | 1598-1622 | 4 |
| C.4 (+C.4.1-C.4.4) | 1624-1697 | 9 |
| C.5 (+C.5.1-C.5.3) | 1699-1797 | 13 |
| C.6 | 1799-1805 | 3 |
| C.7 | 1807-1891 | 14 |
| C.7.1 | 1893-1941 | 15 |
| C.7.2 | 1943-1973 | 5 |
| C.7.3 | 1975-2000 | 2 |
| C.7.4 | 2002-2014 | 2 |
| C.8 | 2016-2188 | 21 |
| C.9 | 2190-2209 | 4 |
| C.9.1 | 2211-2298 | 8 |
| C.10 | 2300-2308 | 1 |
| C.11/C.11.1 | 2310-2353 | 7 |
| C.12 | 2355-2361 | 1 |
| C.13 | 2363-2378 | 2 |
| C.14/C.14.1 | 2380-2428 | 5 |
| C.14.2 | 2430-2532 | 10 |
| C.14.3 | 2534-2572 | 3 |
| D.0-D.16 | 2576-2728 | 19 |
| E intro, E.1 | 2732-2788 | 5 |
| E.2/E.2.1 | 2790-2826 | 3 |
| E.3/E.3.1 | 2828-2921 | 9 |
| E.4 | 2923-2949 | 2 |
| E.5/E.5.1-E.5.3 | 2951-3088 | 14 |
| E.6/E.6.1-E.6.6 | 3090-3225 | 14 |
| E.7 | 3229-3269 | 4 |
| E.8 | 3271-3362 | 15 |
| E.9 | 3364-3421 | 7 |
(Per-row counts are approximate hand tallies; the totals below are machine counts.)

## Totals per kind
| kind | count |
|---|---|
| INVAR | 105 |
| ASSUME | 71 |
| SETTLED | 60 |
| DRIFT | 59 |
| LIMIT | 53 |
| PLATFORM | 43 |
| RISK | 19 |
| MIRROR | 19 |
| SUPPRESS | 11 |
| TODO | 7 |
| WORKAROUND | 4 |
| OPENQ | 1 |
| **total** | **452** (96 covered-by, 208 related, rest new) |

## Top 10
1. DRIFT SPECIFICATION.md:2493-2499: C.14.2 says `asy_notification_service.py` imports `NeopixelDriver` and wirable drivers import `AsyFramManager` at module level. Neither is true: there is no NeopixelDriver import, and the AsyFramManager imports are TYPE_CHECKING-only. New.
2. DRIFT SPECIFICATION.md:1517-1519 vs 2443-2449: C.2 still describes `_WIRING` as a 2-element Python tuple. C.14.2 says it has been a 5-field `# @wiring` comment since 2026-09-10. New.
3. OPENQ SPECIFICATION.md:535-537: the `CFGMGR_SYSTEM` setup-order fix costs +0.90 s of real boot latency, which is unexplained (queue R6). New.
4. RISK SPECIFICATION.md:1831-1840: a `ResetErrors` that answers OK after a write the chip did not store is accepted (owner, 2026-09-17), on the basis that the chip is "trusted". The evidence wipe also interacts with REST.S04.
5. ASSUME SPECIFICATION.md:228-230: says a reset has an "ample" FRAM margin (low single-digit ms), while C.7 measures ~305 ms per chunk and 21 chunks. Related to XCUT.T03.
6. DRIFT SPECIFICATION.md:1823-1826 vs A.7:487-497: the two sections disagree on where each FRAM logger's `pr.setup()` runs (inside its task vs the pre-task batch). This matters for CORE.S03 and the ResetErrors boot window.
7. INVAR SPECIFICATION.md:159-161: "never import `async_manager`". In the flat frozen namespace such an import resolves silently, and no guard exists. New.
8. PLATFORM SPECIFICATION.md:2004-2008: pinned cyw43 copies an SSID over 32 bytes past a 36-byte buffer unchecked. The byte bounds live only in `asy_wifi_service`; the web UI checks characters.
9. DRIFT SPECIFICATION.md:972-976: says the real firmware-build test is parametrized over wozi/dev. The code uses all six `DEVICE_NAMES`. New.
10. RISK SPECIFICATION.md:1309-1316: when the lwIP `MEM_SIZE` arena is exhausted, `modlwip` `tcp_write` retries can block the whole VM for up to 10 s, and no asyncio timeout can interrupt it. Covered by PLAT.T04.
