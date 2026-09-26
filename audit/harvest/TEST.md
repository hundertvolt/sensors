# Harvest — TEST: Software test tiers

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`, moved to `4dc80ef` by V11).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: SETTLED 24, INVAR 125, MIRROR 96, LIMIT 195, RISK 9, ASSUME 105, PLATFORM 7, WORKAROUND 32, SUPPRESS 121, TODO 4, DRIFT 30, NOTE 19 — 767 items.


## src/asy_webserver_service.py

- **TEST.N001** LIMIT · `src/asy_webserver_service.py:721-723` — "never actually raised by any of this
  module's own fakes/proxy, kept for real hardware defense-in-depth" — OSError path has no mock coverage
  · [H02]

## src/asy_wifi_service.py

- **TEST.N002** MIRROR · `src/asy_wifi_service.py:119-121` — "Not importable as a module attribute once
  const()-folded (see tests/test_asy_wifi_service.py's own mirrored copy)" — Phase constants duplicated
  in the test file · [H02]

## tests/_boot_contiguity_probe.py

- **TEST.N003** LIMIT · `tests/_boot_contiguity_probe.py:3` — "Not a test_*.py file, so
  scripts/test.sh's glob never runs it" — runs only via its consumer
  `tests_scripts/test_digital_twin_boot_contiguity.py`; not part of the MicroPython-tier memory-error
  gate · related: TEST.T18 · [H03]
- **TEST.N004** MIRROR · `tests/_boot_contiguity_probe.py:34-38` — "Bounds mirroring
  tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py's" —
  `_STARTER_LOOP_TIMEOUT_MS=20000`, `_GRACE_MS=250`, `_TIMERS_TIMEOUT_S=15` copied by hand from
  `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py:32-38` (currently equal);
  nothing enforces the match · [H03]
- **TEST.N005** LIMIT · `tests/_boot_contiguity_probe.py:58-60` — "the suppressed arm keeps the leading
  collect and loses the per-module ones, which makes it a conservative control" — the "suppressed"
  control arm is not collect-free; `_dump()` itself calls `gc.collect()` on both arms · [H03]
- **TEST.N006** LIMIT · `tests/_boot_contiguity_probe.py:77-78` — "tests/machine.py's Timer fake never
  fires by itself, so the chain is advanced with the same sequencer_timer.trigger()" — timer-chain
  timing is driven manually, not by real timer periods · related: TEST.T05 · [H03]
- **TEST.N007** ASSUME · `tests/_boot_contiguity_probe.py:111-113` — "its final sleep and its final
  collect are still to come" — waits `1000 // n + 250` ms assuming the supervisor's per-starter sleep is
  `1.0/len(task_starters)` s (`src/system_service.py:225`); a change there silently shifts the measured
  position · [H03]
- **TEST.N008** INVAR · `tests/_boot_contiguity_probe.py:92-102` — "its task list is a local, so the
  loop's own end is only observable by counting the starters" — replaces private `sysfunct._start_task`
  to observe progress; couples to a private SystemService method · related: TEST.T11 · [H03]
- **TEST.N009** LIMIT · `tests/_boot_contiguity_probe.py:153` — "reported, never asserted on: the run
  phase undoes most of it (MEASUREMENTS M3.9)" — the post-settle map is deliberately not asserted ·
  [H03]
- **TEST.N010** INVAR · `tests/_boot_contiguity_probe.py:161-162` — "sys.exit() unconditionally: the
  real supervised task graph leaves siblings parked" — relies on forced exit to avoid known hang cause
  #2 · [H03]
- **TEST.N011** SUPPRESS · `tests/_boot_contiguity_probe.py:102,124,131` — "# type:
  ignore[method-assign]" / "[misc]" / "[assignment]" — three type suppressions: private-method swap,
  `asy_spi_driver._SPI` rebinding, `system_service.gc` replacement · [H03]
- **TEST.N012** DRIFT · `tests/_boot_contiguity_probe.py:86,108` — "NOTE start_timers did not complete"
  — failure paths print `NOTE ...` and return 1, while the hardware twin script prints `RESULT: FAIL ...`
  for the same conditions (`heap_layout_after_full_boot_sequence.py:168,192`) (low) · [H03]

## tests/_bus_hazard_catalog.py

- **TEST.N013** MIRROR · `tests/_bus_hazard_catalog.py:2-3,36-37` — "Shared wire-frame helpers moved
  here from test_bus_hazard_multi_device.py so both files build identical bytes" — the frame builders
  are said to be the single source · related: TEST.T08 · [H03]
- **TEST.N014** DRIFT · `tests/_bus_hazard_catalog.py:77-87` — "the same one
  test_bus_hazard_multi_device.py used before this catalog absorbed it, and the same one
  test_asy_bmp3xx_driver.py uses" — the BMP calibration dataset and expected 28.4607952.../713.765147...
  constants still exist as separate copies in `tests/test_bus_hazard_multi_device.py:87-88` and
  `tests/test_asy_bmp3xx_driver.py:124-125` (three copies, kept in sync by hand) · related: TEST.T08 ·
  [H03]
- **TEST.N015** MIRROR · `tests/_bus_hazard_catalog.py:26-33` — "checked against every real occupant's
  TOML-declared address, not a hand-kept constant table" — the reserved-range table
  `_RESERVED_I2C_RANGES` itself is still hand-kept and duplicates the logic in
  `test_bus_hazard_multi_device.py` · related: TEST.S05 · [H03]
- **TEST.N016** LIMIT · `tests/_bus_hazard_catalog.py:126-127` — "Only covers drivers that actually
  share a bus with another on some real device today" — catalog is incomplete by design; fails loud via
  KeyError at `:358`/`:531` when a new sharer appears · [H03]
- **TEST.N017** DRIFT · `tests/_bus_hazard_catalog.py:142,170-171` — "one safe, non-destructive config
  write, if this driver has one" — SCD30's `write_once` is `set_temperature_offset`, which
  `src/asy_scd30_driver.py:564` documents as NVM-persisted; "safe" holds only on the mock (low) · [H03]
- **TEST.N018** ASSUME · `tests/_bus_hazard_catalog.py:155-157` — "SCD30 speaks the same register-less,
  write-then-read protocol shape SGP40 does" — per-address read queues (`read_queue_by_address`) are a
  fake-only mechanism to separate their replies · [H03]
- **TEST.N019** SUPPRESS · `tests/_bus_hazard_catalog.py:196,225,259,304,538` — "except Exception: #
  only the addresses touched matter for this sweep, not success" — five swallowed exceptions in the
  `_exercise_*` sweeps and the address-sweep scenario; an early raise shrinks the touched set and still
  passes · covered-by: TEST.S02 · [H03]
- **TEST.N020** ASSUME · `tests/_bus_hazard_catalog.py:230-233,264-266` — "a fixed register snapshot
  stays valid across any number of reads, so this adapter's own seed is a deliberate no-op" —
  ISL29125/BMP3xx seeds are no-ops; the torn-read check relies on a static register map · [H03]
- **TEST.N021** INVAR · `tests/_bus_hazard_catalog.py:270-274` — "primed lazily on this occupant's own
  first read, exactly once" — BMP adapter calls `setup()` when the private `_temp_calib` attribute is
  absent; couples to a private driver name · related: TEST.T11 · [H03]
- **TEST.N022** SUPPRESS · `tests/_bus_hazard_catalog.py:46` — "# type: ignore[return-value]" — `fake()`
  returns the private `_i2c` as FakeI2C · [H03]
- **TEST.N023** ASSUME · `tests/_bus_hazard_catalog.py:369-384` — "the switch-count floor below
  additionally rules out silent full serialization" — the heuristic `switches >= len(occupants)` is the
  only interleaving check; the fraction is not stated to be sufficient · [H03]
- **TEST.N024** LIMIT · `tests/_bus_hazard_catalog.py:388-392` — "writer = writers[0]" — only the first
  writing occupant is ever driven against its siblings · covered-by: TEST.S10 · [H03]
- **TEST.N025** LIMIT · `tests/_bus_hazard_catalog.py:415-416,507-515` — "A no-op, not a skip, if
  nothing here has a safe write" / "A no-op if no real occupant of this bus ever broadcasts" — scenarios
  silently pass without exercising anything on buses lacking a writer/broadcaster · covered-by: TEST.S09
  · [H03]
- **TEST.N026** LIMIT · `tests/_bus_hazard_catalog.py:132-134` — "A plain class, not @dataclass -
  `dataclasses` has no stub in the MicroPython-target typeshed" — stub-driven design constraint · [H03]

## tests/_coverage_runner.py

- **TEST.N027** LIMIT · `tests/_coverage_runner.py:1-2,24` — "recording every line executed in src/ or
  digital_twin/ only" — generated `sensortask_*.py` and everything outside those prefixes is untraced;
  relies on relative `co_filename` prefixes · covered-by: TEST.S13 · [H03]
- **TEST.N028** SUPPRESS · `tests/_coverage_runner.py:57` — "# noqa: S102" — `exec()` of the test file ·
  [H03]
- **TEST.N029** LIMIT · `tests/_coverage_runner.py:50-66` — "except SystemExit as exc:" — only
  `SystemExit` is caught; any other exception escaping the test file skips the JSON dump entirely (low)
  · related: TEST.T12 · [H03]

## tests/_digital_twin_construction_scenarios.py

- **TEST.N030** DRIFT · `tests/_digital_twin_construction_scenarios.py:2 vs :147,:193` — "fast, no real
  wall-clock waits" — the docstring claims no real waits, but two scenarios `await asyncio.sleep(1.0)`
  for webserver bind · related: TEST.S14 · [H03]
- **TEST.N031** SUPPRESS · `tests/_digital_twin_construction_scenarios.py:25-27` — "# noqa: E402" —
  three E402 suppressions made necessary by the two pre-import calls above · [H03]
- **TEST.N032** MIRROR · `tests/_digital_twin_construction_scenarios.py:45-47` — "_DEVICES = (\"wozi\",
  \"dev\", \"arzi\", \"klkizi\", \"grkizi\", \"schlafzi\")" — hand-kept list of all real devices vs
  `devices/*.toml`; also assumes buildgen output already exists in `build/generated_src/` before the
  file runs · [H03]
- **TEST.N033** INVAR · `tests/_digital_twin_construction_scenarios.py:64-67` — "distinct from
  test_digital_twin_sensortask_integration.py's 19100+/\"dtsi\" ... (19300+, 19400+, 19700+)" —
  port-range and scratch-key disjointness across test files is convention only (19500+10*i per device) ·
  related: TEST.T06, TEST.S21 · [H03]
- **TEST.N034** ASSUME · `tests/_digital_twin_construction_scenarios.py:144-147,190-193` — "measured at
  ~400ms here too" — fixed 1.0 s sleep for webserver bind rests on a single measured ~400 ms
  `pr.setup()` duration · covered-by: TEST.S14 · [H03]
- **TEST.N035** DRIFT · `tests/_digital_twin_construction_scenarios.py:165-167` — "which no
  tests/machine.py-backed test can do, that fake having no comparable fault surface" — stale:
  `tests/machine.py` has `inject_fault`; also the injected SGP40 fault is probably never consumed by a
  `/measurements` GET · covered-by: TEST.S04 · [H03]
- **TEST.N036** ASSUME · `tests/_digital_twin_construction_scenarios.py:174-176` — "SGP40 is
  fixed-address (0x59) on every real device (buildgen.twin_wiring.FIXED_ADDRESSES)" — hard-coded 0x59
  lookup · [H03]
- **TEST.N037** INVAR · `tests/_digital_twin_construction_scenarios.py:180-184` — "asy_i2c_driver.I2C
  wraps the real machine.I2C at its private _i2c attribute" — test couples to a private attribute of the
  bus wrapper · related: TEST.T11 · [H03]
- **TEST.N038** NOTE(MEM) · `tests/_digital_twin_construction_scenarios.py:185-187` — "the Unix-port
  heap is small enough that a needlessly large `times` ... measurably adds to this file's cumulative
  memory pressure" — per-file cumulative heap pressure across several `build_system()` calls is a known
  constraint (Part E.3.1 heapsize) — recorded as ASSUME · related: TEST.T03 · [H03]
- **TEST.N039** ASSUME · `tests/_digital_twin_construction_scenarios.py:196-199` — "never a 500 - a
  sensor read failure degrades to whatever get_dict_data() already returns" — asserts only 200 + key
  presence · covered-by: TEST.S04 · [H03]

## tests/_fram_chip_fake.py

- **TEST.N040** ASSUME · `tests/_fram_chip_fake.py:1-2` — "WEL semantics are verified directly against
  the MB85RS64V datasheet (DS501-00015-4v0-E)" — fake's WEL/WRSR/WRITING PROTECT behaviour is claimed
  datasheet-verified; no conformance probe exists · related: TEST.S20, STOR.T03 · [H03]
- **TEST.N041** LIMIT · `tests/_fram_chip_fake.py:2` — "simulate one transaction's effect being eaten by
  a bus disturbance, not \"unplug the whole bus\"" — fault knobs model single-transaction corruption
  only · [H03]
- **TEST.N042** LIMIT · `tests/_fram_chip_fake.py:32-36` — "These two suppress the datasheet's own
  auto-clear specifically so FRAM_SPI's explicit WRDI-verification and retry path ... stays exercised" —
  `disturb_*_autoclear` knobs model non-datasheet chip behaviour on purpose · [H03]
- **TEST.N043** LIMIT · `tests/_fram_chip_fake.py:53` — "2-byte address form, matches this driver's
  <=0xFFFF path" — only 2-byte addressing modelled; the chip is fixed at 8 KB (`bytearray(0x2000)`), no
  address wrap-around at 0x1FFF (a slice write past the end grows the bytearray) (low) · related:
  STOR.T07 · [H03]
- **TEST.N044** LIMIT · `tests/_fram_chip_fake.py:57-67,103-121` — "data phase of a previously-opened
  WRITE (opcode+address arrived in the prior call)" — the fake has no chip-select model: transactions
  are inferred from the call sequence (one opcode write, then one data write/readinto), WEL clears at
  the data call rather than at the CS edge, a READ continuing over several `readinto()` calls is not
  modelled, and block-protect (BP) bits never gate WRITE (low) · related: TEST.S20 · [H03]
- **TEST.N045** SUPPRESS · `tests/_fram_chip_fake.py:25,56` — "# type: ignore[arg-type]" / "# type:
  ignore[call-overload]" — two type suppressions in the fake · [H03]

## tests/_sensortask_scenarios.py

- **TEST.N046** WORKAROUND · `tests/_sensortask_scenarios.py:9-12` — "scripts/test.sh's MICROPYPATH
  excludes ext/ ... extending sys.path reaches the real vendored ext/microdot.py" — test-side sys.path
  insert instead of a build-environment scope change; removal trigger none stated · [H03]
- **TEST.N047** SUPPRESS · `tests/_sensortask_scenarios.py:22` — "# type: ignore[import-not-found]" —
  microdot import unresolvable by mypy in this pass · [H03]
- **TEST.N048** MIRROR · `tests/_sensortask_scenarios.py:27-31` — "keep in sync with
  asy_wifi_service.py's own definitions if those ever change" —
  `_PHASE_STA_SEEKING=0`/`_PHASE_HOTSPOT=2` hand-copied from `src/asy_wifi_service.py` (const()-folded,
  not importable); a third copy lives in `tests/test_asy_wifi_service.py`; nothing enforces the match ·
  [H03]
- **TEST.N049** MIRROR · `tests/_sensortask_scenarios.py:60-62` — "_DEVICES = (\"wozi\", \"dev\",
  \"arzi\", \"klkizi\", \"grkizi\", \"schlafzi\")" — hand-kept device list duplicated with
  `tests/_digital_twin_construction_scenarios.py:47`; assumes buildgen output exists before the run ·
  [H03]
- **TEST.N050** LIMIT · `tests/_sensortask_scenarios.py:65-72` — "Only the RDID changes - that is what
  asy_fram_manager.py's setup() keys its chip check off." — dev's 256 KB MB85RS2MTA fake inherits the 8
  KB memory and the 2-byte address decode (`tests/_fram_chip_fake.py:26,53`), while
  `src/asy_fram_driver.py:120` sends 24-bit addresses when `max_size > 0xFFFF`; so on dev the mock tier
  maps FRAM addresses coarsely and may alias chunks (observation, not run) · related: TEST.S20, HW.T07,
  STOR.T07 · [H03]
- **TEST.N051** MIRROR · `tests/_sensortask_scenarios.py:74-80` — "Same \"keyed by the real chip's own
  max_size\" table digital_twin/machine.py's _FRAM_RDID_BY_MAX_SIZE uses" — three-way table
  (`_FRAM_FAKE_BY_MAX_SIZE`, twin `_FRAM_RDID_BY_MAX_SIZE`, `twin_wiring.py`) must gain an entry
  together for a third FRAM size · [H03]
- **TEST.N052** ASSUME · `tests/_sensortask_scenarios.py:94` — "every real device has exactly one
  FRAM/SPI instance" — tuple unpack fails on a second SPI attachment · [H03]
- **TEST.N053** INVAR · `tests/_sensortask_scenarios.py:103-105` — "each device's batch is its own OS
  process, potentially concurrent, so two devices must never resolve TmpScratch's tests/_tmp/<key>/ path
  to the same directory" — scratch-key disjointness across processes is convention only · related:
  TEST.T06 · [H03]
- **TEST.N054** INVAR · `tests/_sensortask_scenarios.py:190-192` — "setters[i] is paired with loggers[i]
  elsewhere, so this is load-bearing" — `_all_loggers()` order must match buildgen's topological
  construction order and every TOML's relative instance order (Part L.3) · [H03]
- **TEST.N055** LIMIT · `tests/_sensortask_scenarios.py:237-243,768-785` — "Every
  SensorReader/SensorReaderConfig instance real construction wires a task/timer starter for" —
  `_sensor_reader_owners()` omits `isl29125` and the two `uart_link` instances, so the
  task/timer-starter membership scenarios never check them · [H03]
- **TEST.N056** LIMIT · `tests/_sensortask_scenarios.py:289,890` — "every real device has scd30 today,
  but this stays correct if a future one doesn't" — early `return` counts as PASS when a device lacks
  the module · covered-by: TEST.S09 · [H03]
- **TEST.N057** ASSUME · `tests/_sensortask_scenarios.py:898-905,1163` — "SCD30_Reader is the only
  sensors=-registered module that is a plain SensorReader" — the SCD30 PUT scenario and the ResetErrors
  boot-window scenario have no `_has()` guard and assume every device has scd30/sgp40 · related:
  TEST.S09 · [H03]
- **TEST.N058** INVAR · `tests/_sensortask_scenarios.py:314-317` — "If this test hangs, that's the
  regression to report - not something to work around here." — the never-blocks property of
  `build_system()` is proven only by the per-file timeout backstop · related: TEST.T16 · [H03]
- **TEST.N059** LIMIT · `tests/_sensortask_scenarios.py:341-343,797-800` — "the real Timer-sequencing
  chain never completes under machine.py's fake" — `main()` scenarios fake
  `start_timers`/`ntp_force_sync`/`start_and_check_tasks`; the real chain is covered only by
  test_system_service.py · related: TEST.T05 · [H03]
- **TEST.N060** DRIFT · `tests/_sensortask_scenarios.py:377` — "FRAM chunk order - exact relative
  sequence (six or seven chunks, depending on bmp3xx presence)" — stale count:
  `_expected_fram_chunk_calls()` (`:218-233`) builds 13-19 entries per device · [H03]
- **TEST.N061** MIRROR · `tests/_sensortask_scenarios.py:483-487` — "scripts/_digital_twin_ci_suite.py's
  Run 5c sweeps the whole errcount table and exempts its _IN_MEMORY_ONLY_ERROR_SOURCES" — exemption list
  in the CI suite and this pinned `["FRAM"]` must agree · [H03]
- **TEST.N062** LIMIT · `tests/_sensortask_scenarios.py:515-544` — "Only asserted for whichever of the
  two this device actually has." — the dead-FRAM scenario checks degraded logging for
  SYSTEM/SGP40/BMP3XX/SCD30 only; ISL29125, UART, WIFI, NTP, WEBSERVER, NOTIFY are not exercised · [H03]
- **TEST.N063** DRIFT · `tests/_sensortask_scenarios.py:552 vs :643` —
  "setup_batch_runs_sysfunct_then_fram_then_conn..." — the scenario name says sysfunct before fram; the
  asserted order is `fram` then `sysfunct` · related: TEST.S08 · [H03]
- **TEST.N064** LIMIT · `tests/_sensortask_scenarios.py:552-647` — "expected = [\"notify_finalize\",
  \"fram\", \"sysfunct\", \"conn\", \"ntp\", \"sgp\"]" — only 7-8 setup() calls are tracked; scd30,
  isl29125, uart_link, neopixel, webserver setup positions are not checked · related: XCUT.T01 · [H03]
- **TEST.N065** ASSUME · `tests/_sensortask_scenarios.py:652-662` — "The expected count comes from the
  generated source, not by hand." — counts lines that start with `await ` and end with `.setup()`; a
  setup call with arguments or different formatting is not counted · related: XCUT.T03 · [H03]
- **TEST.N066** ASSUME · `tests/_sensortask_scenarios.py:775-777` — "neopixel/notification/webserver all
  return [] today" — current timer-starter shape · [H03]
- **TEST.N067** LIMIT · `tests/_sensortask_scenarios.py:987-991` —
  "..._light_cmd_led_dispatches_to_the_real_pixel_driver" — asserts only "Valid" · covered-by: TEST.S08
  · [H03]
- **TEST.N068** INVAR · `tests/_sensortask_scenarios.py:1071-1073` — "a second request_signal() would
  find start_signal_event already set and never cleared, hanging in its own wait loop" — one lightCmdLED
  dispatch per test is required; a second hangs because the consumer task never runs under per-call
  `asyncio.run()` · related: TEST.T04 · [H03]
- **TEST.N069** ASSUME · `tests/_sensortask_scenarios.py:1108-1110` — "SGP40 and UARTLINK are the only
  maintenance-status sources any real device has today" — current-state assumption · [H03]
- **TEST.N070** LIMIT · `tests/_sensortask_scenarios.py:1135` — "Build-info values are checked for shape
  only." — build info content is not validated · [H03]
- **TEST.N071** INVAR · `tests/_sensortask_scenarios.py:1179-1181` — "conn._conn_phase is set directly,
  this file's test seam" — hotspot scenarios drive a private attribute, not the WiFi task · related:
  TEST.T11 · [H03]
- **TEST.N072** LIMIT · `tests/_sensortask_scenarios.py:1235` — "real (stub) index.html, not a redirect
  loop" — static root served from stub content in this tier · [H03]
- **TEST.N073** SUPPRESS · `tests/_sensortask_scenarios.py:126,364,504,833` — "# type: ignore[misc]" —
  four `asy_spi_driver._SPI = ...` rebinding suppressions (plus 32 method-assign, see aggregate) · [H03]
- **TEST.N074** INVAR · `tests/_sensortask_scenarios.py:360-370,408-414,614-638,829-839` —
  "SystemService.start_timers = _fake_start_timers" — class-level monkeypatching of real src classes
  inside one shared process, restored only by `finally` · related: TEST.T07 · [H03]

## tests/_shared_rest_roundtrip.py

- **TEST.N075** INVAR · `tests/_shared_rest_roundtrip.py:1-3` — "Backend-agnostic REST-round-trip
  assertion helpers shared by mock and digital-twin tests (and tests_hardware/'s CPython runner)" — the
  module must stay importable and correct under both MicroPython and CPython; a change affects three
  tiers at once · related: TEST.T17 · [H03]
- **TEST.N076** LIMIT · `tests/_shared_rest_roundtrip.py:26-32` — "checks each sensor's own value isn't
  re-wrapped ... and isn't empty" — the self-wrap guard only detects a nested key equal to the sensor's
  own name, and emptiness; field content is unchecked (low) · related: TEST.T17 · [H03]
- **TEST.N077** INVAR · `tests/_shared_rest_roundtrip.py:35-40` — "the synchronous list_iterator some
  streamed routes use (see SPECIFICATION.md Part F.1)" — draining consumes the iterator: a body can be
  checked only once · [H03]

## tests/_strict_json.py

- **TEST.N078** MIRROR · `tests/_strict_json.py:2-3` — "while the browser's JSON.parse() rejects the
  page's data outright" — this hand-written RFC 8259 checker stands in for the browser's parser (oracle)
  · related: TEST.T17 · [H03]
- **TEST.N079** LIMIT · `tests/_strict_json.py:83-98` — "One comma between members, none before the
  first or after the last" — the checker does not reject duplicate object keys (a streamed-dict assembly
  bug that duplicates a key would pass) (low) · related: TEST.T17 · [H03]

## tests/_threshold_runner.py

- **TEST.N080** MIRROR · `tests/_threshold_runner.py:18-23` — "the same shape tests/_coverage_runner.py
  uses" — duplicated exec/SystemExit handling with `_coverage_runner.py` · related: TEST.T08 · [H03]
- **TEST.N081** LIMIT · `tests/_threshold_runner.py:15-24` — "return 0" — a test file that finishes
  without raising SystemExit (no microtest footer) returns 0 here too; a non-integer SystemExit arg
  would raise ValueError (low) · related: TEST.T12, TEST.S23 · [H03]
- **TEST.N082** SUPPRESS · `tests/_threshold_runner.py:20` — "# noqa: S102" — `exec()` of the test file
  · [H03]

## tests/_tmp_scratch.py

- **TEST.N083** INVAR · `tests/_tmp_scratch.py:1-3` — "Every op stays scoped to <key>, never
  tests/_tmp's shared root." — the no-shared-root-listing property; enforced structurally by
  `tests/test_tmp_scratch.py` (CLAUDE.md wear rule) · related: TEST.T17 · [H03]
- **TEST.N084** INVAR · `tests/_tmp_scratch.py:37-39` — "Construct once at module level with a key
  unique to that file" — key uniqueness across files (and across concurrently running processes) is
  convention only · related: TEST.T06 · [H03]
- **TEST.N085** SUPPRESS · `tests/_tmp_scratch.py:15-16,23-24,27-29,32-33,50-51,54-55,65-66,76-77` —
  "except OSError: pass # path doesn't exist - nothing to remove" — eight swallowed `OSError`s: any
  error other than "absent" (e.g. EACCES, ENOTEMPTY) is silently ignored, so a failed wipe leaves stale
  state without a signal · related: TEST.T17 · [H03]
- **TEST.N086** INVAR · `tests/_tmp_scratch.py:2` — "wiped clean at construction and by teardown_all()
  (tests/microtest.py's run())" — teardown happens only if a file reaches `microtest.run()` · [H03]

## tests/_uart_comm_harness.py

- **TEST.N087** INVAR · `tests/_uart_comm_harness.py:37-39` — "Every test is bounded: a protocol wedge
  must surface as a fast FAIL, never as a hung file." — `run()` wraps `asyncio.run(wait_for(..., 10))`;
  per CLAUDE.md this `run()` must only ever be called from synchronous test scope (nested
  `asyncio.run()` segfaults) — review-only · related: TEST.T06 · [H03]
- **TEST.N088** WORKAROUND · `tests/_uart_comm_harness.py:67-70` — "A bounded stand-in, never a real
  select.poll(): the Unix port does not re-evaluate a Python object's ioctl() after registration" —
  `LinkPoller` replaces the driver's poller (CLAUDE.md known CI hang); removal trigger none stated ·
  [H03]
- **TEST.N089** SUPPRESS · `tests/_uart_comm_harness.py:43,69,70` — "# type: ignore[return-value]" / "#
  type: ignore[assignment]" — private `_uart` access and poller replacement · [H03]
- **TEST.N090** ASSUME · `tests/_uart_comm_harness.py:94-109` — "the listener is awaited out and
  cancelled only if it truly stalls" — fixed 5 s listener grace inside the 10 s `run()` limit; a
  listener exception raised in `finally` would mask the work's own exception (low) · related: TEST.T04 ·
  [H03]
- **TEST.N091** LIMIT · `tests/_uart_comm_harness.py:116-119` — "await pair.setup()" — `build_pair()`
  discards `Pair.setup()`'s boolean · covered-by: TEST.S07 · [H03]

## tests/_uart_link_contract.py

- **TEST.N092** MIRROR · `tests/_uart_link_contract.py:1-3` — "tests/machine.py and
  digital_twin/machine.py supply their own, so the two models diverge in fidelity but never in
  semantics" — mock and twin UART link models share this one semantic contract; `link.settle()` is the
  only fidelity seam · related: TEST.T05 · [H03]
- **TEST.N093** INVAR · `tests/_uart_link_contract.py:225-246` — "ALL_CHECKS = (" — every `check_*` must
  be listed by hand; an unlisted check never runs · covered-by: TEST.T06 · [H03]
- **TEST.N094** ASSUME · `tests/_uart_link_contract.py:72-79` — "a.write_limit = 0 ... assert
  a.write(b\"12345\") is None" — fakes return None for a zero-byte write; the real rp2 return is not
  cited (low) · [H03]
- **TEST.N095** ASSUME · `tests/_uart_link_contract.py:82-90` — "Fixed capacity per direction, explicit
  drop-newest policy, counted." — overflow policy chosen by the model; not stated to match the rp2 RX
  ring buffer/FIFO overrun behaviour · related: TEST.T05 · [H03]
- **TEST.N096** LIMIT · `tests/_uart_link_contract.py:195-198` — "the real peripheral would instead wait
  out timeout_char per missing byte without yielding (F.5.8)" — neither fake blocks;
  `would_have_blocked_bytes` is a counted stand-in for the real stall · related: BUS.T05 · [H03]
- **TEST.N097** INVAR · `tests/_uart_link_contract.py:200-207,215-222` —
  "type(b).would_have_blocked_bytes = 0" — the stall counter is class-level shared state reset by each
  check · related: TEST.T07 · [H03]

## tests/_webserver_concurrency_scenarios.py

- **TEST.N098** LIMIT · `tests/_webserver_concurrency_scenarios.py:7-9` — "Section F drives _serve()
  against in-process fakes, never real accept()/poll()" — before this file no test drove more than one
  simultaneous real TCP connection; the in-process Section F is fake-based · related: REST.T06 · [H03]
- **TEST.N099** SETTLED · `tests/_webserver_concurrency_scenarios.py:15-21` — "One thing this file
  deliberately does NOT attempt is a \"different source host\" variant" — deliberately untested:
  per-source-IP behaviour (none exists in `_serve()`) · [H03]
- **TEST.N100** SUPPRESS · `tests/_webserver_concurrency_scenarios.py:37` — "# type:
  ignore[import-not-found]" — microdot import · [H03]
- **TEST.N101** INVAR · `tests/_webserver_concurrency_scenarios.py:70-77` — "Own port range base
  (19700+, one 200-port block per device), distinct from the twin integration suites' 19100+ and
  19300+." — cross-file port disjointness by convention; the list omits the 19400+/19500+ ranges named
  in `_digital_twin_construction_scenarios.py:66`, and 19700+200*5 exceeds E.1's 17400-19999 ·
  covered-by: TEST.S21 · [H03]
- **TEST.N102** MIRROR · `tests/_webserver_concurrency_scenarios.py:105,804` — "_BODY_CAP = 2048 #
  WebserverService's shipped max_content_length (Part I.6), stated, never read back" — restated
  constant; the comment says "never read back" but `:804` does assert it equals
  `Request.max_content_length` · related: REST.S01 · [H03]
- **TEST.N103** ASSUME · `tests/_webserver_concurrency_scenarios.py:114-116` — "under 4 they would
  exceed the ceiling and assert refusals away, so such a device needs scenario shapes of its own" — all
  scenarios assume `max_connections >= 4` (asserted) · [H03]
- **TEST.N104** ASSUME · `tests/_webserver_concurrency_scenarios.py:129-140` — "So: 0.5s, recalibrated
  down from 1.0s (~400ms typical here)" — readiness is a fixed sleep calibrated from a single ~400 ms
  observation; margin vs a slower host is unstated · related: TEST.S14, TEST.T04 · [H03]
- **TEST.N105** NOTE(MEM) · `tests/_webserver_concurrency_scenarios.py:153-155` — "an in-process client
  that materializes a body it never looks at competes with the DUT for the same heap" — test client and
  DUT share one heap; client allocation can perturb DUT memory results (Part E.9) — recorded as LIMIT ·
  [H03]
- **TEST.N106** SUPPRESS · `tests/_webserver_concurrency_scenarios.py:183-184` — "except Exception:
  pass" — `_still_serving()` swallows every exception during its retry budget (no comment on the except
  itself) · [H03]
- **TEST.N107** DRIFT · `tests/_webserver_concurrency_scenarios.py:249-254` — "A real config write
  reaching ConfigManager.write_config() through the real object graph (SCD30 is on every device" — the
  helper PUTs `{"SCD30": {"Interval": ...}}`, but SCD30's REST field is `MeasInt`
  (`src/asy_scd30_driver.py:58`) and SCD30_Reader has no ConfigManager
  (`src/asy_scd30_driver.py:252-262`); with `read_body=False` only the HTTP status is checked, so
  "concurrent real config write" (`:587-608`) and the body-burst scenario (`:800-801`) may exercise no
  write at all (observation, not run) · [H03]
- **TEST.N108** LIMIT ·
  `tests/_webserver_concurrency_scenarios.py:299-304,370-374,449-450,497-501,623-627` — "except OSError:
  return \"rejected\" # the documented reject-when-full outcome - a clean reset" — any `OSError` (not
  only a reset from a full server) is counted as a clean rejection · [H03]
- **TEST.N109** ASSUME · `tests/_webserver_concurrency_scenarios.py:307-313` — "(a real run here saw
  6/8)" — single observed figure; reject-when-full not asserted as must-happen because timing-dependent
  · [H03]
- **TEST.N110** DRIFT · `tests/_webserver_concurrency_scenarios.py:316` — "unexpected exception type
  leaked out of any of the 8 concurrent attempts" — the burst is `_ceiling(module) * 2`, not fixed at 8
  (low) · [H03]
- **TEST.N111** ASSUME · `tests/_webserver_concurrency_scenarios.py:503-506` — "Enough concurrent
  attempts to exceed the remaining headroom by a full ceiling, so at least one must be rejected" —
  asserts a rejection as must-happen, although `:311-313` says rejection under a burst is
  timing-dependent and not asserted · related: TEST.T04 · [H03]
- **TEST.N112** ASSUME · `tests/_webserver_concurrency_scenarios.py:518-520` — "Real production wiring's
  own outer_cap_s default (15.0s - no generated device module overrides it)" — test timing
  (`timeout_s=20.0` at `:543`) relies on no device overriding `outer_cap_s` · related: REST.T06 · [H03]
- **TEST.N113** DRIFT · `tests/_webserver_concurrency_scenarios.py:541` — "the server reclaims all four"
  — the loop fills `_ceiling(module)` slots, not four (low) · [H03]
- **TEST.N114** LIMIT · `tests/_webserver_concurrency_scenarios.py:675-678` — "Complete and correct, not
  merely non-empty" — the check is `isinstance(body, dict) and body` plus `elapsed_ms < 10000`; content
  is not compared · [H03]
- **TEST.N115** PLATFORM · `tests/_webserver_concurrency_scenarios.py:719-721` — "within one SYN retry
  (1 s on Linux) of the stall" — host-kernel timing fact the backlog scenario depends on; deliberate
  `time.sleep_ms(200)` stall at `:740` · [H03]
- **TEST.N116** SUPPRESS · `tests/_webserver_concurrency_scenarios.py:736-739` — "except OSError: pass #
  EINPROGRESS" — every connect `OSError` is swallowed, not only EINPROGRESS · [H03]
- **TEST.N117** ASSUME · `tests/_webserver_concurrency_scenarios.py:812` — "a 413 sent over a body it
  never read can arrive as a reset" — an OSError is accepted as equivalent to 413 · [H03]
- **TEST.N118** LIMIT · `tests/_webserver_concurrency_scenarios.py:817-818` — "assert all(r not in (413,
  \"rejected\") for r in at_cap)" — at-cap bodies only need to not be 413/reset; any other status
  (400/500) passes (low) · [H03]
- **TEST.N119** WORKAROUND · `tests/_webserver_concurrency_scenarios.py:835-840,861` — "gc.collect()
  after every real object-graph build: a real MemoryError was found without it" — test-side
  `gc.collect()` kept as "defense-in-depth backstop" against CLAUDE.md's no-gc-prop rule · covered-by:
  TEST.S11 · [H03]
- **TEST.N120** DRIFT · `tests/_webserver_concurrency_scenarios.py:839` — "one process only does 15
  builds rather than 90" — the file registers 20 scenarios, each booting once (20 per process, 120
  total) · related: TEST.S11 · [H03]
- **TEST.N121** SUPPRESS · `tests/_webserver_concurrency_scenarios.py:767` — "# type:
  ignore[method-assign]" — `_close_writer` replaced on the instance (counted in the aggregate) · [H03]
- **TEST.N122** INVAR · `tests/_webserver_concurrency_scenarios.py:113,122,197,742,761` —
  "module.webserver._max_connections" — scenarios read private WebserverService attributes
  (`_max_connections`, `_backlog`, `_open_conns`, `_close_writer`) · related: TEST.T11 · [H03]

## tests/machine.py

- **TEST.N123** LIMIT · `tests/machine.py:1` — "mocks only the raw I2C/SPI bus-transaction level (per
  SPECIFICATION.md Part E.4's mocking boundary) ... Only implements what src/'s own imports need." — the
  fake's surface is deliberately minimal; anything else in `machine` is absent · related: TEST.T19 ·
  [H03]
- **TEST.N124** SETTLED · `tests/machine.py:2` — "it's what makes `from machine import Timer` resolve
  under mypy's `src tests` scope" — main mypy pass resolves `machine` to this fake, not the board stub ·
  covered-by: TEST.T19 · [H03]
- **TEST.N125** LIMIT · `tests/machine.py:51-54` — "Real machine.Pin.init(): omitted/-1 args leave the
  current setting untouched." — the fake's `init()` ignores `pull` even when given (comment implies both
  args are honoured) · covered-by: TEST.S15 · [H03]
- **TEST.N126** LIMIT · `tests/machine.py:80-92` — "trigger_irq() simulates one edge" — `trigger_irq()`
  ignores the registered trigger mask (edge direction) and `hard=`; a `trigger=0` registration is not
  treated as disabled · covered-by: TEST.S15 · [H03]
- **TEST.N127** LIMIT · `tests/machine.py:95-111` — "a long run exhausts the heap as a MemoryError
  inside the code under test" — call logs are capped at 4096 entries and drop the oldest half; a test
  that reads the whole log (e.g. `_touched_addresses()` in `_bus_hazard_catalog.py:364-365`) sees a
  truncated history unless it checks `.dropped` · related: TEST.T17 · [H03]
- **TEST.N128** NOTE(MEM) · `tests/machine.py:99-101` — "the UART fake records ~18 entries per
  transaction, so a long run exhausts the heap" — a fake's own allocation can surface as a MemoryError
  inside code under test (recorded as RISK) · related: TEST.T03 · [H03]
- **TEST.N129** SUPPRESS · `tests/machine.py:98,176,177,182,196,200,201,307,318,323,453` — "# type:
  ignore[type-arg]" / "[arg-type]" / "[index]" / "[call-overload]" — eleven type suppressions (2
  arg-type, 6 call-overload, 1 index, 1 type-arg, 1 combined index,arg-type) on `object`-typed buffer
  params · [H03]
- **TEST.N130** LIMIT · `tests/machine.py:127-132,186-201` — "self.registers: dict[tuple[int, int],
  bytearray] = {} # a real round trip through readfrom_mem/writeto_mem" — registers are keyed by exact
  (address, memaddr): no auto-increment, a multi-byte write at N does not update register N+1;
  `timeout`/`freq` have no behavioural effect (low) · [H03]
- **TEST.N131** LIMIT · `tests/machine.py:160-167` — "return sorted({addr for addr, _ in self.registers}
  - self.nak_addresses)" — `scan()` reports only addresses with seeded registers (not queue-only
  devices) · covered-by: TEST.S15 · [H03]
- **TEST.N132** LIMIT · `tests/machine.py:351-353` — "Not modeled, none of them raising: the
  MIN_BUFFER_SIZE clamp, baudrate/bits/stop, pins (A.6)." — UART constructor validation is partial ·
  related: TEST.T19 · [H03]
- **TEST.N133** LIMIT · `tests/machine.py:395-398` — "def deinit(self) -> None:" — the fake UART's
  `deinit()` only records the call and leaves the port working, whereas rp2's `UART.deinit()` is real
  and unroots the ring buffers (Part F.5.7); the F.5.7 re-init hazard is not modelled (the fake has no
  `init()`) (low) · [H03]
- **TEST.N134** LIMIT · `tests/machine.py:401-413` — "these fakes serve what they hold and return, so
  the stall is counted here instead of taken" — the real per-byte `timeout_char` stall (F.5.8) is a
  counter, not a delay; `would_have_blocked_bytes` is class-level shared state · related: BUS.T05,
  TEST.T07 · [H03]
- **TEST.N135** ASSUME · `tests/machine.py:469,510-511` — "far-side FIFO bound; overflow drops the
  newest bytes" / "Default each direction's bound to the *destination's* own rxbuf" — overflow model =
  destination rxbuf only, drop-newest; the rp2 32-byte hardware FIFO and its overrun are not modelled ·
  related: BUS.T12 · [H03]
- **TEST.N136** LIMIT · `tests/machine.py:559-563` — "this model delivers synchronously, so there is
  nothing to wait for" — no wire time on the mock; only the twin models it · [H03]
- **TEST.N137** WORKAROUND · `tests/machine.py:579-601` — "Never wraps a real select.poll(): the port
  never re-checks ioctl() - CLAUDE.md's known CI hang." — `LinkPoller` bounded stand-in;
  `register`/`unregister` are no-ops and `ipoll()` ignores its timeout · [H03]
- **TEST.N138** INVAR · `tests/machine.py:608-611` — "Tests must clear it between functions, since it
  persists for the whole process." — `Timer.all_timers` class registry must be cleared by each test ·
  related: TEST.T07 · [H03]
- **TEST.N139** INVAR · `tests/machine.py:613-620` — "A shared class attribute, so a test must reset it
  afterward." / "Shared class attribute as well; reset both." — `Timer.raise_on_arm`/`raise_on_arm_exc`
  must be reset by caller discipline · related: TEST.T07, TEST.S18 · [H03]
- **TEST.N140** LIMIT · `tests/machine.py:646-660` — "No real-hardware equivalent - lets test code fire
  a callback deterministically" — `trigger()` runs the callback synchronously in the caller (no
  soft/hard scheduling, never against real time); `drop()` models a lost soft callback · related:
  TEST.T05 · [H03]
- **TEST.N141** INVAR · `tests/machine.py:667-670` — "Class-level, not per-instance: one physical
  peripheral" — `RTC._shared_datetime`/`raise_exc` persist across tests in one process · related:
  TEST.T07 · [H03]
- **TEST.N142** LIMIT · `tests/machine.py:684-691` — "class WDT:" — the fake WDT accepts any id/timeout
  (no 8388 ms cap) and only counts feeds · covered-by: TEST.S15 · [H03]
- **TEST.N143** LIMIT · `tests/machine.py:694-707` — "this fake just records the call so a test can
  assert a reboot was triggered" — `reset()`/`bootloader()` return, unlike real hardware and unlike the
  twin · covered-by: TEST.S15 · [H03]

## tests/microtest.py

- **TEST.N144** LIMIT · `tests/microtest.py:17-28` — "value()" — a test PASSes whenever the call raises
  nothing (an `async def test_*` passes without running); only `Exception` is caught, so a
  `BaseException` aborts the rest of the file · covered-by: TEST.S23, TEST.T12 · [H03]
- **TEST.N145** LIMIT · `tests/microtest.py:14,34,42` — "print(f\"{total - failed}/{total} passed\")" —
  a file with zero collected tests prints `0/0 passed` and exits 0 · covered-by: SCR.S02 · [H03]
- **TEST.N146** LIMIT · `tests/microtest.py:17` — "for name, value in namespace.items():" — execution
  order is dict iteration order (non-deterministic in MicroPython), so inter-test state leaks are
  order-dependent · covered-by: TEST.T07 · [H03]
- **TEST.N147** INVAR · `tests/microtest.py:35-42` — "Always exits explicitly, not just on failure" —
  forced `sys.exit()` is the fix for known hang cause #2; must be kept · [H03]
- **TEST.N148** INVAR · `tests/microtest.py:30-33` — "Runs even on a test failure, so a file's scratch
  dir never outlives its own run." — scratch teardown only if `run()` is reached · [H03]

## tests/neopixel.py

- **TEST.N149** LIMIT · `tests/neopixel.py:23-26` — "kept even though a real rp2 NeoPixel.write() never
  raises" — `raise_on_write` models a failure the hardware cannot produce · [H03]
- **TEST.N150** LIMIT · `tests/neopixel.py:28-29` — "self._buf[i] = value" — no validation of tuple
  length/range on `__setitem__` (low) · [H03]

## tests/network.py

- **TEST.N151** SETTLED · `tests/network.py:8-9` — "What actually matters for a test double is this
  fake's internal consistency with asy_wifi_service.py's comparisons, not bit-for-bit fidelity to a real
  chip." — fidelity limit declared by design · [H03]
- **TEST.N152** LIMIT · `tests/network.py:41-106` — "class WLAN:" — the fake never changes connection
  state on `connect()`, validates no `config()` keys (AP mode included) and models no `isconnected()`
  false positive · related: TEST.T05 · [H03]
- **TEST.N153** INVAR · `tests/network.py:21-22` — "_country_code = [\"DE\"]" — module-level
  country/hostname state persists across tests in one process · related: TEST.T07 · [H03]

## tests/test_api_response.py

- **TEST.N154** LIMIT · `tests/test_api_response.py:121-178` — "# parse_cmd_request" —
  `parse_cmd_request` is exercised only here; it has no `src/` caller · covered-by: CORE.S14 · [H03]
- **TEST.N155** LIMIT · `tests/test_api_response.py:43-45` — "Minimal stand-in for microdot.Request,
  mocking only the one boundary parse_cmd_request actually touches (the .json property)" — fake Request
  models only `.json` · [H03]
- **TEST.N156** SUPPRESS · `tests/test_api_response.py:36-39` — "except OSError: pass # already gone" —
  cleanup swallow · [H03]

## tests/test_asy_bmp3xx_driver.py

- **TEST.N157** MIRROR · `tests/test_asy_bmp3xx_driver.py:21-30,991-1017` — "Kept in sync by citation
  below, not re-derived." — register constants and the `_VAL_*` schema bounds/discrete sets are
  hand-mirrored from `const()`-folded values in `src/asy_bmp3xx_driver.py` (Part E.5.1); nothing
  enforces the match · [H03]
- **TEST.N158** WORKAROUND · `tests/test_asy_bmp3xx_driver.py:64-78` — "asyncio.sleep is process-wide,
  so it is restored however the block exits." — `_FastAsyncSleep` replaces `asyncio.sleep` globally to
  skip `_probe_for_device()`'s two real 0.1 s sleeps · related: TEST.T07 · [H03]
- **TEST.N159** MIRROR · `tests/test_asy_bmp3xx_driver.py:82-84` — "Same technique as the _RaiseOnArm in
  the system_service/wifi suites" — one more copy of the Timer raise-on-arm context manager ·
  covered-by: TEST.S18 · [H03]
- **TEST.N160** ASSUME · `tests/test_asy_bmp3xx_driver.py:100-102` — "a matching expected (pressure_hpa,
  temperature) pair computed independently via the Bosch formula (sec 9.1-9.3)" — the oracle's
  independence from the driver code is asserted, not shown; the same constants are copied into two other
  files · related: TEST.T17 · [H03]
- **TEST.N161** LIMIT · `tests/test_asy_bmp3xx_driver.py:164-170` — "readfrom_mem() returning one blob
  keyed by the burst's starting register is faithful, since this driver only ever requests a burst
  starting at the documented base register" — fake fidelity depends on the driver never reading
  mid-burst; multi-byte address/data-pair writes are not modelled · [H03]
- **TEST.N162** LIMIT · `tests/test_asy_bmp3xx_driver.py:190-192` — "tests/machine.py's fake I2C cannot
  produce this shape (readfrom_mem always returns exactly nbytes)" — short/None burst results need a
  method monkeypatch · [H03]
- **TEST.N163** LIMIT · `tests/test_asy_bmp3xx_driver.py:947-949,1129-1131,1140` — "has to be seeded
  directly into the underlying cache to simulate a config file written before this bound existed" —
  stale-config tests poke the private ConfigManager cache · related: TEST.T11 · [H03]
- **TEST.N164** LIMIT · `tests/test_asy_bmp3xx_driver.py:1224-1230` — "get_bits()/set_bits() never
  suspend in this fake, so the interleaving itself can't be reproduced here" — the torn-read regression
  proves the mechanism (one lock for the batch), not the interleaving · [H03]
- **TEST.N165** LIMIT · `tests/test_asy_bmp3xx_driver.py:1388-1390` — "the MeanAtmTemp fallback (15.0)
  has no observable effect at this height offset, by construction" — the MeanAtmTemp fallback is not
  observable in this test · [H03]
- **TEST.N166** DRIFT · `tests/test_asy_bmp3xx_driver.py:1432 vs :550` — "errno=11, \"Lesefehler:\"" —
  cites the legacy German message; `src/asy_bmp3xx_driver.py:195` logs "Read failed:" (low) · [H03]
- **TEST.N167** SUPPRESS · `tests/test_asy_bmp3xx_driver.py:2030` — "only the addresses *touched* matter
  for this sweep, not success" — swallowed exceptions in the per-driver address sweep · related:
  TEST.S02 · [H03]
- **TEST.N168** SUPPRESS · `tests/test_asy_bmp3xx_driver.py:19,74,141,874,1244,2062,2068` — "# type:
  ignore[misc]" / "[assignment]" / "[return-value]" / "[arg-type]" / "[attr-defined]" — type
  suppressions (plus 2 method-assign in the aggregate) · [H03]

## tests/test_asy_dns_client.py

- **TEST.N169** INVAR · `tests/test_asy_dns_client.py:27-35` — "Below the OS ephemeral range
  (32768-60999) so a concurrently-running ephemeral socket can never be assigned this port" — UDP port
  counter from 24000 relies on host ephemeral-range config and on no other file using 24000+
  (convention, cf. `scripts/test.sh` TEST_PARALLELISM) · related: TEST.S21, TEST.T06 · [H03]
- **TEST.N170** WORKAROUND · `tests/test_asy_dns_client.py:41-56,66-68` — "this build's raw
  bind()/connect()/sendto() reject a plain (host, port) tuple, only getaddrinfo()'s resolved opaque
  object works" — Unix-port quirk: `asy_dns_client.AsyUDPSocket` is replaced for the whole process by a
  pre-resolving wrapper; production passes a plain tuple (correct on rp2) that the mock tier therefore
  never exercises; removal trigger none stated · related: TWIN.T07 · [H03]
- **TEST.N171** INVAR · `tests/test_asy_dns_client.py:70-78` — "so no test here ever calls out to the
  public internet" — `_FALLBACK_DNS_SERVERS` (real 8.8.8.8/1.1.1.1) is overridden process-wide; each
  test that touches it must restore the loopback baseline · related: NET.S04 · [H03]
- **TEST.N172** SUPPRESS · `tests/test_asy_dns_client.py:368-377 (agent cited tests/test_asy_dns_client.py:374-377)`
  — "except OSError: pass" — `recvfrom()` errors in the fake DNS server are swallowed silently · [H03]
  ⟨re-anchored: quote found at line 368⟩
- **TEST.N173** ASSUME · `tests/test_asy_dns_client.py:332` — "assert elapsed < 200" — tight wall-clock
  bound under parallel runs · covered-by: TEST.S14 · [H03]
- **TEST.N174** ASSUME · `tests/test_asy_dns_client.py:444-445` — "10.255.255.254 is never a local
  interface address in this environment" — environment assumption for the unroutable-server test · [H03]
- **TEST.N175** SUPPRESS · `tests/test_asy_dns_client.py:14,68,367,525,560,564` — "# type:
  ignore[no-redef]" / "[misc, assignment]" / "[assignment]" / "[assignment,misc]" / "[misc]" — six type
  suppressions for module-attribute monkeypatching · [H03]

## tests/test_asy_fram_allocation_budget.py

- **TEST.N176** DRIFT · `tests/test_asy_fram_allocation_budget.py:3-5` — "a MICROPY_PY_SYS_SETTRACE=1
  build (which scripts/test.sh's interpreter is)" — stale since the two-binary split (owner 2026-09-21):
  plain runs use `build-standard` without settrace; the code itself (`:35-37`) handles both · [H03]
- **TEST.N177** INVAR · `tests/test_asy_fram_allocation_budget.py:44-54,72,85` — "One setup() inside a
  collection-free window. The collect comes first so the window starts from a known floor" — the test
  calls `gc.collect()` itself and asserts no collection ran inside the window (`allocated == consumed`)
  · related: TEST.T03 · [H03]
- **TEST.N178** LIMIT · `tests/test_asy_fram_allocation_budget.py:89-93` — "A budget nothing could ever
  exceed would pass forever." — the "not trivially satisfied" check compares hard-coded historical
  figures against the budgets; it measures nothing · related: TEST.T01 · [H03]
- **TEST.N179** ASSUME · `tests/test_asy_fram_allocation_budget.py:65-66,77-78` — "18 byte-level
  commands over 74 CS cycles" / "47 CS cycles" — transaction counts stated, not asserted · [H03]
- **TEST.N180** SUPPRESS · `tests/test_asy_fram_allocation_budget.py:19` — "# type: ignore[misc]" —
  `asy_spi_driver._SPI` swap · [H03]

## tests/test_asy_fram_driver.py

- **TEST.N181** INVAR · `tests/test_asy_fram_driver.py:10-13` — "asy_spi_driver.SPI.init() resolves
  `_SPI` as a module global at call time, so reassigning it before any bus is constructed needs no
  per-test patch/restore" — process-wide `_SPI` swap relies on one-file-per-process execution · [H03]
- **TEST.N182** LIMIT · `tests/test_asy_fram_driver.py:657-658` — "_VERIFY_PRESENT_LOCK_TIMEOUT_S is a
  real const() and cannot be monkeypatched, so this test sits out the real ~1s timeout" — real-time wait
  inside a unit test · related: TEST.T04 · [H03]
- **TEST.N183** SUPPRESS · `tests/test_asy_fram_driver.py:1263` — "# noqa: ANN401 - must mirror
  wrn_s()'s own signature exactly, kwargs included" — Any-typed kwargs in a capture double · [H03]
- **TEST.N184** SUPPRESS · `tests/test_asy_fram_driver.py:13,1175,1329,1358` — "# type: ignore[misc]" /
  "[method-assign,assignment]" / "[method-assign, assignment] # deliberate monkeypatch" — type
  suppressions (combined method-assign ones included here; single method-assign in the aggregate) ·
  [H03]

## tests/test_asy_fram_manager.py

- **TEST.N185** MIRROR · `tests/test_asy_fram_manager.py:26-31` — "these are hardcoded, matching
  test_asy_fram_driver.py's own convention" — `_STATUS_UNINIT/IDLE/BUSY` = 0/1/2 hand-copied from
  `const()` values in `src/asy_fram_manager.py`; nothing enforces the match · [H03]
- **TEST.N186** INVAR · `tests/test_asy_fram_manager.py:924-926` — "Parameter name must match
  FakeMB85RS64V.readinto()'s own (_write_value)" — monkeypatch doubles must mirror real signatures for
  mypy · [H03]
- **TEST.N187** SUPPRESS · `tests/test_asy_fram_manager.py:12,699,1352,1602,1960,2108,2154,2193` — "#
  type: ignore[misc]" / "[assignment]" / "[return-value]" / "[call-overload]" — non-method-assign type
  suppressions (16 method-assign counted in the aggregate) · [H03]

## tests/test_asy_fram_wire_trace.py

- **TEST.N188** MIRROR · `tests/test_asy_fram_wire_trace.py:35` — "asy_fram_driver.py's own
  _SPI_OPCODE_WRDI is a const() and so not importable" — opcode hand-copied · [H03]
- **TEST.N189** INVAR · `tests/test_asy_fram_wire_trace.py:43-44` — "Patched in permanently at import
  and inert while _TRACE is None" — the recorder monkeypatches the fake SPI class for the whole process;
  only the FRAM CS pin is watched · related: TEST.T07 · [H03]
- **TEST.N190** ASSUME · `tests/test_asy_fram_wire_trace.py:145,451` — "a fixed, unsynced clock keeps
  every timestamped trace deterministic" — goldens cover only the unsynced-clock timestamp path · [H03]
- **TEST.N191** SUPPRESS · `tests/test_asy_fram_wire_trace.py:20,58` — "# type: ignore[misc]" / "# type:
  ignore[call-overload]" — plus 7 method-assign (aggregate) · [H03]

## tests/test_asy_i2c_driver.py

- **TEST.N192** LIMIT · `tests/test_asy_i2c_driver.py:83-85` — "A never-initialized bus cannot be
  observed separately - I2C.__init__ always calls init() immediately." — state not reachable/testable ·
  [H03]
- **TEST.N193** LIMIT · `tests/test_asy_i2c_driver.py:604-606` — "Fake-only: real rp2 machine.I2C(id)
  returns one static per-bus singleton ... tests/machine.py deliberately diverges here" — the fake
  returns a new object per construction, unlike rp2 · related: TEST.T05 · [H03]
- **TEST.N194** DRIFT · `tests/test_asy_i2c_driver.py:605` — "(see its own note)" — `tests/machine.py`
  has no note about the per-bus singleton divergence (dangling reference) (low) · [H03]
- **TEST.N195** MIRROR · `tests/test_asy_i2c_driver.py:1063-1067` — "asy_i2c_driver._SCRATCH_SIZE is 32,
  and const() folds the name out of the module" — scratch size mirrored by hand; the oversized-read
  fallback has zero callers today · [H03]
- **TEST.N196** SUPPRESS · `tests/test_asy_i2c_driver.py:31,269,281,1033` — "# type:
  ignore[return-value]" / "[assignment]" / "[index,arg-type]" — plus 2 method-assign (aggregate) · [H03]

## tests/test_asy_isl29125_driver.py

- **TEST.N197** MIRROR · `tests/test_asy_isl29125_driver.py:18-42` — "Kept in sync by citation, not
  re-derived." — register addresses, device ID, GainRatio band, derived down-point factor and the
  agreement-run constant are hand-mirrored `const()` values; nothing enforces the match · [H03]
- **TEST.N198** MIRROR · `tests/test_asy_isl29125_driver.py:67-69,90` — "Same technique as
  test_asy_bmp3xx_driver.py's." — duplicated `_FastAsyncSleep` and `_RaiseOnArm` helpers (process-wide
  `asyncio.sleep` swap) · covered-by: TEST.S18 · [H03]
- **TEST.N199** SUPPRESS · `tests/test_asy_isl29125_driver.py:174-176` — "# noqa: B905" / "No strict=
  (ruff B905): MicroPython's zip() rejects it (CPython 3.10+-only)" — B905 suppressed; same note in
  `src/asy_webserver_service.py` · [H03]
- **TEST.N200** INVAR · `tests/test_asy_isl29125_driver.py:170-172` — "print_log.py keeps errors and
  warnings in ONE history list, discriminated by the parallel ErrType entry" — assertions on ErrNum
  alone would conflate errno and wrnno with the same number · related: XCUT.T07 · [H03]
- **TEST.N201** LIMIT · `tests/test_asy_isl29125_driver.py:534-535,794-795,810-812` —
  "tests/machine.py's I2C is a plain dict of registers with no reset semantics" / "0x00 is read-only as
  the device ID and write-only as the reset command on real hardware, a split tests/machine.py's flat
  register dict cannot model" — fake fidelity gaps worked around per test by re-seeding · related:
  TEST.S20, TEST.T05 · [H03]
- **TEST.N202** LIMIT · `tests/test_asy_isl29125_driver.py:653-655` — "ticks_ms() wraps, so this must
  use ticks_diff()/ticks_add(), never a subtraction" — tests cover a deadline 1 s in the past only, not
  a deadline older than 2**29 ms · related: SENS.S27, XCUT.T25 · [H03]
- **TEST.N203** LIMIT · `tests/test_asy_isl29125_driver.py:806-808,1466-1468,3039-3040,3057` — "these
  tests run in zero wall clock - so the first conversion is marked complete here rather than every test
  sleeping 303ms" — settle deadlines are cleared by hand; real conversion timing is not exercised here ·
  [H03]
- **TEST.N204** LIMIT · `tests/test_asy_isl29125_driver.py:826-827` — "Requirement 20, and it is
  satisfied here or nowhere: tests/test_sensortask_dev.py builds the whole dev object graph against a
  fake with no ISL registers in it at all" — the dev sensortask tier has no ISL register model ·
  related: TEST.T15 · [H03]
- **TEST.N205** WORKAROUND · `tests/test_asy_isl29125_driver.py:2334-2347` — "Leaked registrations grow
  asyncio's pollfds array and segfault the process (unix_port_poll_prewarm.py)" — tests must await
  cancelled ThreadSafeFlag waiters and read `.state` directly instead of `wait_for_ms()` probes
  (Unix-port defect); removal trigger none stated · related: TWIN.T07 · [H03]
- **TEST.N206** SUPPRESS · `tests/test_asy_isl29125_driver.py:3267` — "only the addresses *touched*
  matter for this sweep, not success" — swallowed exceptions in the address sweep · related: TEST.S02 ·
  [H03]
- **TEST.N207** SUPPRESS ·
  `tests/test_asy_isl29125_driver.py:80,81,118,204,453,803,887,936,1159,1279,1284,1304,1647,1655,1866,1950,1952,1969,2035,2169,2528,2618,2656,2738,2752,2886`
  — "# type: ignore[arg-type]" / "[assignment]" / "[return-value]" / "[method-assign, assignment]" — 13
  arg-type, 5 assignment, 1 return-value, plus combined ones (21 method-assign in the aggregate) · [H03]

## tests/test_asy_neopixel_driver.py

- **TEST.N208** ASSUME · `tests/test_asy_neopixel_driver.py:32-34,88-272` — "These tests drive real
  asyncio.sleep() rather than a simulated clock" — ordering/ramp assertions rest on fixed real sleeps
  (0.02-0.3 s, e.g. `:167`, `:238` "both ramps' worth of real time, plus margin") with `freq=100`
  instead of the real default 20; timing-sensitive under parallel load · related: TEST.T04, TEST.S14 ·
  [H03]
- **TEST.N209** DRIFT · `tests/test_asy_neopixel_driver.py:163-164` — "(see this file's own module
  docstring)" — the file has no module docstring (it starts with `import asyncio`); dangling reference
  (low) · [H03]
- **TEST.N210** SUPPRESS · `tests/test_asy_neopixel_driver.py:495,504,555` — "# type: ignore[arg-type] #
  structurally satisfies the Protocol" — three arg-type suppressions · [H03]

## tests/test_asy_notification_service.py

- **TEST.N211** MIRROR · `tests/test_asy_notification_service.py:27` — "Mirrors asy_ntp_client.py's own
  GMTimeStruct (hour/minute are all monitor_loop() actually reads)" — partial hand-copied structure;
  assumes monitor_loop reads only hour/minute · [H03]
- **TEST.N212** WORKAROUND · `tests/test_asy_notification_service.py:101-110` — "asyncio.sleep is a
  shared, process-wide function; restored on __exit__" — another process-wide `asyncio.sleep`
  monkeypatch (third copy in this partition) · covered-by: TEST.S18 · [H03]
- **TEST.N213** ASSUME · `tests/test_asy_notification_service.py:139-141,908-909,1008` — "FlashDur's
  real schema minimum is 0.5 - each triggered signal costs a real 2*0.5=1.0s settle sleep, so 3
  triggered signals need >=3.0s of real wall-clock wait" — monitor_loop tests run on real wall-clock
  waits sized from the schema floor · related: TEST.T04 · [H03]
- **TEST.N214** MIRROR · `tests/test_asy_notification_service.py:1213-1214` — "_MAX_OVERRIDE_TIME is
  const()-folded and not importable (Part E.5.1), so 3600 is hardcoded" — hand-copied constant · [H03]
- **TEST.N215** ASSUME · `tests/test_asy_notification_service.py:1257-1268` — "assert 59.0 < result <
  60.0 # ~60s minus the ~50ms actually elapsed" — wall-clock bound after a real `sleep_ms(50)`;
  full-cycle behaviour not observed because Interv's floor is 60 s · covered-by: TEST.S14 · [H03]
- **TEST.N216** LIMIT · `tests/test_asy_notification_service.py:1241-1242` — "Corrupt the cache directly
  to simulate a malformed read without touching ConfigManager itself" — failure injection via private
  cache · related: TEST.T11 · [H03]
- **TEST.N217** SUPPRESS · `tests/test_asy_notification_service.py:110,565,579,677,1475,1491` — "# type:
  ignore[assignment] # deliberate monkeypatch" / "[arg-type]" / "[method-assign, assignment]" — six type
  suppressions · [H03]

## (partition-wide aggregates)

- **TEST.N218** SUPPRESS · `9 files, 83 sites` — "# type: ignore[method-assign]" — test-side method
  reassignment (the project's mocking mechanism; CLAUDE.md requires per-site suppressions, none in
  src/): `_sensortask_scenarios.py` 32, `test_asy_isl29125_driver.py` 21, `test_asy_fram_manager.py` 16,
  `test_asy_fram_wire_trace.py` 7, `test_asy_bmp3xx_driver.py` 2, `test_asy_i2c_driver.py` 2,
  `_boot_contiguity_probe.py` 1, `_webserver_concurrency_scenarios.py` 1, `test_asy_fram_driver.py` 1
  (combined `[method-assign, assignment]` forms counted separately in their file items) · related:
  TEST.T11 · [H03]
- **TEST.N219** MIRROR · `7+ files` — "Mirrors of ... micropython.const() values ... not importable" —
  hand-copied `const()` values across the unit tier (bmp3xx, isl29125, fram manager/wire trace, i2c
  scratch size, notification, wifi phases); no mechanical check that the copies match `src/` · [H03]
- **TEST.N220** INVAR · `10+ files` — "asy_spi_driver._SPI = FakeMB85RS64V # type: ignore[misc]" —
  process-wide module-global swaps (`_SPI`, `asyncio.sleep`, `AsyUDPSocket`, `_FALLBACK_DNS_SERVERS`,
  class methods) rely on one-file-per-process execution and restore discipline · related: TEST.T07 ·
  [H03]

## tests/test_asy_ntp_client.py

- **TEST.N221** MIRROR · `tests/test_asy_ntp_client.py:50-52` — "Mirrors asy_ntp_client.py's own
  _VAL_NH/_VAL_NOS/_VAL_NIH/_VAL_GMT/_VAL_DST schema tuples" — the NTP config schema is hand-copied into
  the test because the src tuples are const()-folded; ends: `src/asy_ntp_client.py` `_VAL_*` ↔ this
  file; drift is caught only by the equality tests at :2256-2262/:2291-2296 · related: GEN.T06 · [H04]
- **TEST.N222** INVAR · `tests/test_asy_ntp_client.py:140-141` — "Below the OS ephemeral range
  (32768-60999) so a concurrently-running ephemeral socket can never be assigned this port" — fixed-port
  allocation for parallel test processes relies on staying below the host's ephemeral range and on
  per-file base disjointness (convention; see scripts/test.sh TEST_PARALLELISM) · related: TEST.T06 ·
  [H04]
- **TEST.N223** WORKAROUND · `tests/test_asy_ntp_client.py:148-150` — "a plain (host, port) tuple is
  rejected by bind()/connect()/sendto() on this port's \"standard\" build" — Unix-port-only address
  workaround (pre-resolved opaque addr); rp2 accepts plain tuples, so tests do not exercise the exact
  production addr shape; removal trigger: none stated · [H04]
- **TEST.N224** LIMIT · `tests/test_asy_ntp_client.py:154-156` — "make_addr()'s own return value is
  opaque/non-indexable on this Unix port" — Unix-port sockaddr objects cannot be indexed, so port
  redirection needs a separate raw-port counter — a fidelity gap vs rp2's plain tuples · [H04]
- **TEST.N225** DRIFT · `tests/test_asy_ntp_client.py:285-288` — "Setters are explicitly out of scope
  (see BACKLOG.md)." — section header says setters are out of scope, yet the same file tests
  `_set_dict_cfg()` setter support at :2265-2289 · - (low) · [H04]
- **TEST.N226** SUPPRESS · `tests/test_asy_ntp_client.py:85,87` — "lambda: True # noqa: E731" — two E731
  (lambda assignment) suppressions for config-callback stand-ins · [H04]
- **TEST.N227** SUPPRESS · `tests/test_asy_ntp_client.py:2336` — "# noqa: B905 - MicroPython zip()
  rejects strict=" — B905 suppressed because MicroPython's zip() has no `strict=`; platform fact to
  recheck on a version bump · [H04]
- **TEST.N228** SUPPRESS · `tests/test_asy_ntp_client.py:1684,150,419,... (agent cited tests/test_asy_ntp_client.py:21,150,419,...)`
  — "type: ignore[assignment, method-assign]" — 54 mypy suppressions in this file: 20 `[assignment, method-assign]`,
  13 `[method-assign]`, 11 `[assignment]`, 4 `[arg-type]`, 3 `[misc]`, 2 `[assignment, misc]`, 1
  `[return-value]` — monkeypatching of `_run_ntp_sync_attempt`, `asy_dns_client.resolve_ipv4`,
  `AsyUDPSocket`, `time`, and deliberate wrong-type args · related: TEST.T11 · [H04] ⟨re-anchored: quote
  found at line 1684⟩
- **TEST.N229** LIMIT · `tests/test_asy_ntp_client.py:842-848` — "No real-network end-to-end test
  through _resolve_ntp_server() itself" — the resolve step is never exercised against a real DNS peer
  (port 53 needs root); coverage is argued by composition of a recording stub plus
  test_asy_dns_client.py · [H04]
- **TEST.N230** ASSUME · `tests/test_asy_ntp_client.py:945-948` — "without this yield the request could
  race ahead of the responder's own bind() (confirmed directly)" — loopback tests rely on one
  `asyncio.sleep(0)` being enough for the peer to bind/register before the client sends · related:
  TEST.T04 · [H04]
- **TEST.N231** LIMIT · `tests/test_asy_ntp_client.py:1026-1027` — "must not raise - result (None or a
  valid tm) not asserted" — a full-length non-NTP 48-byte payload's parse result is deliberately not
  asserted; only no-exception is checked · related: TEST.T01 · [H04]
- **TEST.N232** MIRROR · `tests/test_asy_ntp_client.py:1095,1104,1175,1198,1375,517` —
  "_NTP_MIN_PLAUSIBLE_UNIX_TIME, compiled away, hardcoded" — const()-folded NTP constants
  (_NTP_MIN/_MAX_PLAUSIBLE_UNIX_TIME, _NTP_RETRY_INTERV, _NTP_SYNC_RETRIES, _NTP_CHECK_INTERV,
  _NTP_ASYNC_INTERV) are hardcoded in the tests; ends: src/asy_ntp_client.py consts ↔ test literals ·
  related: GEN.T06 · [H04]
- **TEST.N233** WORKAROUND · `tests/test_asy_ntp_client.py:1422-1424,1433-1435` — "every test below
  normalizes gmtime()'s result to 8 elements through a monkeypatched `time` shim" — test-side shim for
  the Unix-port 9-tuple; removal trigger: none stated · [H04]
- **TEST.N234** WORKAROUND · `tests/test_asy_ntp_client.py:2051-2061` — "Two Unix-port-only workarounds
  ... binding a test server there needs root/CAP_NET_BIND_SERVICE ... connect() rejects
  (micropython/micropython#6924)" — end-to-end NTP tests redirect port 123 to an ephemeral port and wrap
  AsyUDPSocket to pre-resolve; must NOT be applied where addr is already resolved; removal trigger: none
  stated (upstream #6924) · [H04]
- **TEST.N235** ASSUME · `tests/test_asy_ntp_client.py:2167,2191,2488` — "await asyncio.sleep(1) #
  comfortably longer than _NTP_CONN_TIMEOUT would need to fail once" — integration tests use fixed
  wall-clock sleeps (1 s, 0.2 s) and a 100 ms fetch timeout assumption against a real loopback ·
  related: TEST.S14 · [H04]
- **TEST.N236** DRIFT · `tests/test_asy_ntp_client.py:2258-2259` — "cfg_schema itself stays a public
  attribute too, for the legacy REST layer's own direct reads" — no REST-layer reader of `.cfg_schema`
  exists in src/ (only base_classes/system_service); "legacy REST layer" reference appears stale · -
  (low) · [H04]
- **TEST.N237** LIMIT · `tests/test_asy_ntp_client.py:124-126` — "toggles tests/machine.py's shared
  Timer.raise_on_arm for the `with` block, simulating rp2 alarm-pool exhaustion" — rp2 alarm-pool
  exhaustion (OSError(ENOMEM)) and MemoryError are only simulated via a shared class-level mock flag;
  another copy of the raise-on-arm helper · related: TEST.S18 · [H04]

## tests/test_asy_scd30_driver.py

- **TEST.N238** LIMIT · `tests/test_asy_scd30_driver.py:92-94` —
  "_read_dev_register()/_send_dev_command() each make real 0.05s asyncio.sleep() calls ... asyncio.sleep
  is process-wide" — `_FastAsyncSleep` replaces the process-wide `asyncio.sleep` with sleep(0), so the
  concurrency/snapshot tests never model SCD30's real 50 ms bus-lock holds · related: SENS.S11 · [H04]
- **TEST.N239** SUPPRESS · `tests/test_asy_scd30_driver.py:45,59,101,318,1010,...` — "type:
  ignore[method-assign]" — 20 mypy suppressions: 15 `[method-assign]`, 2 `[return-value]`, 2
  `[assignment]` (incl. the process-wide `asyncio.sleep` monkeypatch at :101), 1 `[arg-type]` (float
  passed to int-typed `set_altitude`, :318) · related: TEST.T11 · [H04]
- **TEST.N240** LIMIT · `tests/test_asy_scd30_driver.py:109-111` — "toggles tests/machine.py's shared
  Timer.raise_on_arm ... simulating an rp2 Timer.init() that cannot arm" — alarm-pool exhaustion only
  simulated through a shared class-level fake flag; yet another copy of `_RaiseOnArm` · related:
  TEST.S18 · [H04]
- **TEST.N241** LIMIT · `tests/test_asy_scd30_driver.py:607-609` — "Kept to two tests (the delay is real
  elapsed time, not simulated) rather than exercised from every angle" — setup()/reset() coverage
  deliberately thin because of the real ~2.5 s soft-reset delay · related: SENS.S22 · [H04]
- **TEST.N242** INVAR · `tests/test_asy_scd30_driver.py:908-910` — "nesting that inside a coroutine
  already driven by an outer run() segfaults the MicroPython Unix port" —
  `register_frame()`/`crc8_byte()` call asyncio.run() internally, so fixtures must be queued from sync
  scope; review-only rule · related: TEST.T06 · [H04]
- **TEST.N243** LIMIT · `tests/test_asy_scd30_driver.py:1113-1118` — "never caught because
  test_asy_webserver_service.py's _put_sensors tests use a fake module that already defines it" —
  webserver tests' fake sensor module is more complete than the real SCD30_Reader, masking a real PUT
  /sensors 500; fake-fidelity gap · related: REST.S03 · [H04]
- **TEST.N244** LIMIT · `tests/test_asy_scd30_driver.py:1198-1199` — "scd.setup()'s own I2C behavior is
  covered above; here it is monkeypatched to a fast no-op" — read_loop()/_init_scd() tests never run the
  real setup()/soft reset · - (low) · [H04]
- **TEST.N245** MIRROR · `tests/test_asy_scd30_driver.py:1420-1423` — "Bus-hazard coverage moved from
  tests/test_bus_hazard_multi_device.py" — SCD30's mock-tier same-device concurrency and address sweep
  live here, while CLAUDE.md's four-tier rule names only `tests/test_bus_hazard_multi_device.py` for the
  mock tier · related: SENS.T10 · [H04]
- **TEST.N246** SUPPRESS · `tests/test_asy_scd30_driver.py:1520-1523` — "except Exception: # only the
  addresses *touched* matter for this sweep, not success" — address sweep swallows every exception from
  17 calls; guarded by `touched == {_ADDR}` equality (an all-raise run touching nothing would fail) ·
  related: TEST.S02 · [H04]
- **TEST.N247** ASSUME · `tests/test_asy_scd30_driver.py:1496` — "generous - some methods issue more
  than one read" — the sweep pre-queues 40 read pairs, assumed sufficient for all 17 calls · - (low) ·
  [H04]

## tests/test_asy_sgp40_driver.py

- **TEST.N248** SETTLED · `tests/test_asy_sgp40_driver.py:1` — "matching SPECIFICATION.md Part E.4's
  mocking boundary: asy_sgp40_driver.py's own protocol/CRC/locking logic and voc_algorithm.py's real
  VOCAlgorithm run unmocked" — mocking boundary is the raw I2C transaction (fake `read_queue` extension
  in tests/machine.py) · [H04]
- **TEST.N249** ASSUME · `tests/test_asy_sgp40_driver.py:51-52` — "Independent CRC-8 reimplementation
  for building fixtures - not the driver's own crc_checks.CRC8" — test oracle for SGP40 frames is a
  second CRC implementation, anchored to the datasheet example (:92-93) · related: TEST.T17 · [H04]
- **TEST.N250** SUPPRESS · `tests/test_asy_sgp40_driver.py:39,115,1473,1651,1815,2186,...` — "type:
  ignore[union-attr]" — 17 mypy suppressions: 5 `[assignment]` (incl. process-wide `asyncio.sleep` and
  `asy_fram_manager.time` monkeypatches), 4 `[method-assign]`, 4 `[arg-type]`, 2 `[union-attr]`, 1
  `[return-value]`, 1 `[misc]` · related: TEST.T11 · [H04]
- **TEST.N251** LIMIT · `tests/test_asy_sgp40_driver.py:545-547` — "toggles tests/machine.py's shared
  Timer.raise_on_arm for the `with` block" — alarm-pool/MemoryError arm failures are simulated only via
  the shared fake flag; one more `_RaiseOnArm` copy · related: TEST.S18 · [H04]
- **TEST.N252** WORKAROUND · `tests/test_asy_sgp40_driver.py:720-722,769-771` — "sidesteps a real mypy
  narrowing limitation" — local-variable snapshots work around mypy keeping `is True` narrowing across
  awaited calls; removal trigger: none stated · - (low) · [H04]
- **TEST.N253** DRIFT · `tests/test_asy_sgp40_driver.py:800-802` — "Structurally safe inside
  _read_sgp()'s try, but untested." — comment says untested while it heads the very test covering it · -
  (low) · [H04]
- **TEST.N254** MIRROR · `tests/test_asy_sgp40_driver.py:1277-1279,1327-1329` — "Mirrors of
  asy_sgp40_driver.py's own _VAL_BP/_VAL_BMAX/_VAL_WT const() tuples - not importable once
  const()-folded" — schema tuples and bounds (BackupPeriod 0-1440 def 1, BackupMaxAge 0-10080 def 7200,
  WaitTimeNTP 0-600 def 30) hand-copied into the test · related: GEN.T06 · [H04]
- **TEST.N255** LIMIT · `tests/test_asy_sgp40_driver.py:1464-1466` — "_init_sgp()/initialize()/_reset()
  make several real asyncio.sleep() calls (3ms/500ms/100ms command delays, plus _reset()'s 1s settle)" —
  read_loop tests replace process-wide asyncio.sleep with sleep(0); real command delays are not modelled
  · related: SENS.S07 · [H04]
- **TEST.N256** DRIFT · `tests/test_asy_sgp40_driver.py:1599 vs :1634` — "past the 46-sample initial
  blackout" / "well past the 45s initial blackout" — the blackout length is stated as 46 samples and 45
  s in the same test · related: SENS.S04 (low) · [H04]
- **TEST.N257** LIMIT · `tests/test_asy_sgp40_driver.py:1641-1647` — "poking the chip's stored timestamp
  bytes does not work either: it only corrupts one redundant copy's CRC, and _read() then self-heals" —
  an old-backup case can only be staged by monkeypatching `asy_fram_manager.time`, not via the fake chip
  · - (low) · [H04]
- **TEST.N258** MIRROR · `tests/test_asy_sgp40_driver.py:2374-2376` — "Bus-hazard coverage moved from
  tests/test_bus_hazard_multi_device.py" — SGP40 mock-tier address sweep lives here, not in the file
  CLAUDE.md's four-tier rule names · related: SENS.T10 · [H04]
- **TEST.N259** LIMIT · `tests/test_asy_sgp40_driver.py:2379-2405` — "except Exception: # only the
  addresses touched matter for this sweep, not success" / "assert touched <= {0x59, 0x00}" — address
  sweep swallows every exception and asserts only a subset, so a run where every call raises before
  touching the bus passes; the name's "reset touches only the general call address" half is not
  separately asserted · related: TEST.S02 · [H04]

## tests/test_asy_spi_driver.py

- **TEST.N260** SUPPRESS · `tests/test_asy_spi_driver.py:39` — "type: ignore[return-value]" — single
  mypy suppression in the fake-bus accessor · - (low) · [H04]
- **TEST.N261** MIRROR · `tests/test_asy_spi_driver.py:240` — "FakeSPI.LSB mirrors the real constant
  value" — fake constant ↔ rp2 `machine.SPI.LSB` · related: TEST.T19 (low) · [H04]
- **TEST.N262** LIMIT · `tests/test_asy_spi_driver.py:460-462` — "real rp2 machine.SPI(id) returns one
  static per-bus singleton ... tests/machine.py deliberately diverges here" — fake SPI re-init returns a
  new object unlike rp2; "nothing in src/ depends on either" is an unverified claim · related: TEST.T19
  · [H04]

## tests/test_asy_uart_comm.py

- **TEST.N263** MIRROR · `tests/test_asy_uart_comm.py:33-45` — "_ERR_ALLOC = 14 # asy_uart_comm.py's own
  errnos; const() folds the names out of that module" — wire command codes (0x01/0x02/0x04), frame
  offsets and errnos 14/15 are hand-copied from src/asy_uart_comm.py; Class A constants duplicated in
  tests · related: GEN.T06 · [H04]
- **TEST.N264** INVAR · `tests/test_asy_uart_comm.py:58,83` — "# never a real select.poll()" — every
  UART test injects the bounded `LinkPoller` fake (CLAUDE.md known-hang rule: no real select.poll() on
  fake streams); enforced only by review · related: TEST.T06 · [H04]
- **TEST.N265** SUPPRESS · `tests/test_asy_uart_comm.py:58,83,109,147,357,844,1358,1715,1807,...` —
  "type: ignore[assignment,arg-type]" — 29 mypy suppressions: 11 `[assignment,arg-type]` (poller
  injection), 8 `[arg-type]` (deliberate bad caller args), 4 `[method-assign]`, 3 `[union-attr]`, 2
  `[attr-defined]` (module-global `bytearray` shadowing, :1807/:1811), 1 `[no-any-return]` · related:
  TEST.T11 · [H04]
- **TEST.N266** DRIFT · `tests/test_asy_uart_comm.py:536-537` — "Today's bitmask test lets 0x03 and 0x06
  pass validation" — "Today's" describes the pre-fix behaviour; the test asserts rejection, so the
  comment reads as current but is history · - (low) · [H04]
- **TEST.N267** WORKAROUND · `tests/test_asy_uart_comm.py:731-732` — "asserting the same attribute's
  identity twice in sequence narrows it to a literal and makes the rest of the test statically
  unreachable" — mypy narrowing workaround via locals; removal trigger: none stated · - (low) · [H04]
- **TEST.N268** LIMIT · `tests/test_asy_uart_comm.py:748-756` — "A raw now - t0 subtraction is wrong at
  the 2**30 ms rollover" — the "survives the ticks rollover" test only sets a deadline 1 ms in the past
  with real `ticks_ms()`; on the Unix port (tick period 2**62) it never crosses the rp2 2**30 boundary
  it names · related: XCUT.T25 · [H04]
- **TEST.N269** ASSUME · `tests/test_asy_uart_comm.py:949` — "past the driver's own 1000ms
  acknowledgement bound" — test timing tied to asy_uart_driver.py's 1000 ms cancel-acknowledgement bound
  · - (low) · [H04]
- **TEST.N270** LIMIT · `tests/test_asy_uart_comm.py:1705-1707` — "machine.py's own write_limit is a
  fixed per-call cap ... None is the real rp2 return: its internal per-byte timeout hit before anything
  was sent" — fake UART cannot fail the Nth write, so tests wrap writefrom; rp2 returns None on a TX
  timeout (platform fact) · related: TEST.T19 · [H04]
- **TEST.N271** LIMIT · `tests/test_asy_uart_comm.py:1784-1786` — "Shadows asy_uart_comm.py's
  module-global `bytearray` ... Armed and one-shot" — MemoryError paths are only reachable by shadowing
  the module's `bytearray` builtin · related: TEST.T11 (low) · [H04]
- **TEST.N272** LIMIT · `tests/test_asy_uart_comm.py:673,679,...` — "pair =
  run(build_pair(get_callback=echo_get(b\"\"), set_callback=accept_set()))" — 60 `build_pair()` call
  sites in this file rely on the harness, which discards `Pair.setup()`'s result, so a negative-only
  test (e.g. :685-691 asserting `is False`) would pass on a failed setup · covered-by: TEST.S07 · [H04]
- **TEST.N273** LIMIT · `tests/test_asy_uart_comm.py:1-3` — "The comm-hazard tier lives in
  test_uart_comm_hazard.py." — protocol hazard coverage is split into another file (not in this
  partition) · - (low) · [H04]

## tests/test_asy_uart_driver.py

- **TEST.N274** INVAR · `tests/test_asy_uart_driver.py:23-26` — "Bounded via wait_for(), not a bare
  asyncio.run() ... 5s is generous next to this file's tightest inner bound" — this file's run() is
  bounded at 5 s (one of the few bounded local run() helpers); the bound is a fixed wall-clock guess ·
  related: TEST.S14 · [H04]
- **TEST.N275** INVAR · `tests/test_asy_uart_driver.py:32-34,44-46,857-859` — "the Unix port never
  re-checks a Python object's ioctl() after registration, so readiness waits hang on CI" — every UART
  here must use the bounded `_StepPoller`; enforced for this file only by
  `test_no_uart_built_here_polls_through_a_real_select_poll` (:439-445), which checks just
  `make_uart()`/`cobs_uart()` · related: TEST.T06 · [H04]
- **TEST.N276** SUPPRESS · `tests/test_asy_uart_driver.py:881,40,154,284,364,...,1876 (agent cited tests/test_asy_uart_driver.py:35,40,154,284,364,...,1876)`
  — "type: ignore[assignment] # see test_read_returns_bytes_once_ready's comment" — 66 mypy
  suppressions: 58 `[assignment]` (almost all `uart.poller = _StepPoller(...)`), 5 `[method-assign]`, 2
  `[arg-type]`, 1 `[return-value]` · related: TEST.T11 · [H04] ⟨re-anchored: quote found at line 881⟩
- **TEST.N277** MIRROR · `tests/test_asy_uart_driver.py:62-63,73,79,85,136,163,180` — "Real
  mp_machine_uart_init_helper()/make_new() constants (see tests/machine.py's own docstring for the
  source citations - not guessed)" — UART id 0-1, MIN/MAX_BUFFER_SIZE, invert mask 0-3, GPIO 0-28 copied
  from rp2 source into the fake/tests · related: TEST.T19 · [H04]
- **TEST.N278** ASSUME · `tests/test_asy_uart_driver.py:196-198,208-209,219,229` — "matches
  mp_machine_uart_make_new() fully checking uart_id before init_helper() ever runs" —
  multi-invalid-parameter tests encode rp2's C check order (id → invert → rxbuf → txbuf) in the fake ·
  related: TEST.T19 (low) · [H04]
- **TEST.N279** LIMIT · `tests/test_asy_uart_driver.py:1059-1061` — "the fake's queue-driven readline()
  not otherwise being able to return b\"\" while data is still pending" — fake UART cannot produce an
  empty readline() under POLLIN; path covered only by monkeypatch · related: TEST.T19 (low) · [H04]
- **TEST.N280** ASSUME · `tests/test_asy_uart_driver.py:1304-1306` — "Confirmed for I2CDevice;
  UART(Lockable) shares that exact implementation." — cancellation-through-`async with` behaviour
  inferred for UART from the I2C confirmation · related: PLAT.T01 (low) · [H04]
- **TEST.N281** LIMIT · `tests/test_asy_uart_driver.py:1456-1458` — "`msg += add`'s own MemoryError
  guard is deliberately not fault-injected ... A documented gap (SPECIFICATION.md Part E)" — a stated
  coverage gap: the multi-round assembly MemoryError guard is never exercised · [H04]
- **TEST.N282** LIMIT · `tests/test_asy_uart_driver.py:1464-1472` — "these pin the *request*, which the
  fake cannot" — the fake serves min(nbytes, queued) and never blocks, so the never-block invariant is
  proven only by recording requested byte counts, not by timing · related: BUS.T05 · [H04]

## tests/test_asy_uart_link_driver.py

- **TEST.N283** INVAR · `tests/test_asy_uart_link_driver.py:30,43` — "A bounded stand-in, never a real
  select.poll() - CLAUDE.md's known CI-hang cause." — every test bounded and every link uses a bounded
  poller; review-only rule · related: TEST.T06 · [H04]
- **TEST.N284** SUPPRESS · `tests/test_asy_uart_link_driver.py:40-45,105-106,304,323,333,344,349` —
  "type: ignore[arg-type]" — 11 mypy suppressions: 5 `[arg-type]` (fake FRAM manager passed as `fram=`),
  4 `[assignment]` (poller injection), 2 `[method-assign]` · related: TEST.T11 · [H04]
- **TEST.N285** MIRROR · `tests/test_asy_uart_link_driver.py:201-203` — "exactly as
  tests_hardware/device_scripts/uart_crossover_exchange.py does against real hardware" — the
  SET-then-GET ECHO exchange is duplicated between this mock test and the hardware device script ·
  related: HW.T05 (low) · [H04]
- **TEST.N286** LIMIT · `tests/test_asy_uart_link_driver.py:260-262` — "UART_Comm's own fram=/logger=
  reach-through already existed and is unit-tested by the digital-twin FRAM-order check" — UART_Comm's
  FRAM reach-through is covered only by the twin tier, not by a mock-tier unit test · related: TEST.T15
  · [H04]
- **TEST.N287** LIMIT · `tests/test_asy_uart_link_driver.py:358-360` — "the fake chunk's methods are
  coroutines, so this proves no regression" — the FRAM-path never-block claim is tested against a
  trivial coroutine fake chunk (no SPI session) and only asserts `ticks > 2`; a real FRAM write's
  synchronous SPI time is not modelled · related: UART.T06 · [H04]

## tests/test_asy_udp_socket.py

- **TEST.N288** INVAR · `tests/test_asy_udp_socket.py:27-28` — "Below the OS ephemeral range
  (32768-60999) so a concurrently-running ephemeral socket can never be assigned this port" — fixed
  loopback port base per file; disjointness across parallel test files is by convention · related:
  TEST.T06 · [H04]
- **TEST.N289** WORKAROUND · `tests/test_asy_udp_socket.py:35-41,52-54` — "rejects a plain (host, port)
  tuple ... (micropython/micropython#6924), unlike the real rp2 target" — tests pass an opaque
  getaddrinfo() sockaddr bytearray where rp2 gets a tuple; the rp2 tuple path is never exercised on the
  Unix port; removal trigger: none stated (upstream #6924) · [H04]
- **TEST.N290** SUPPRESS · `tests/test_asy_udp_socket.py:42,54,79,89,107,...,1633` — "type:
  ignore[arg-type]" — 30 mypy suppressions: 14 `[arg-type]` (deliberate malformed args, opaque
  sockaddrs), 12 `[assignment]` (module `socket`/`asyncio` shadowing, private-field mutation), 4
  `[return-value]` · related: TEST.T11 · [H04]
- **TEST.N291** LIMIT · `tests/test_asy_udp_socket.py:285-296` — "if poller.ipoll(0):" — the test peer
  `AdversarialPeer.recv()` truth-tests `ipoll(0)`, which test_asy_ntp_client.py:928-930 says is always
  truthy on this port, then calls a non-blocking `recvfrom()` · covered-by: TEST.S16 · [H04]
- **TEST.N292** ASSUME · `tests/test_asy_udp_socket.py:771-773` — "10.255.255.254 is never a local
  interface address in this environment, so bind() there raises OSError(EADDRNOTAVAIL)" —
  forced-bind-failure tests depend on the host's interface configuration · - (low) · [H04]
- **TEST.N293** ASSUME · `tests/test_asy_udp_socket.py:785-786` — "await asyncio.sleep(0.6) # after >=1
  failed attempt (0.5s backoff), before conn_tries=3 is exhausted (1.5s)" — wall-clock race window
  (0.5-1.0 s) that parallel load could miss; not in TEST.S14's list · related: TEST.S14 · [H04]
- **TEST.N294** ASSUME · `tests/test_asy_udp_socket.py:926,987,994,1350-1351` — "assert elapsed < 2000 #
  generously below the 10000ms+ the old seconds-interpretation bug would take" — wall-clock elapsed
  bounds (<2000 ms, POLLERR detection well under 5000 ms, disconnect waited ~1.5 s but not forever) ·
  covered-by: TEST.S14 · [H04]
- **TEST.N295** MIRROR · `tests/test_asy_udp_socket.py:1043-1045,1146-1148` — "These mirror each
  caller's documented, stable call shape (mode, buffer sizes, timeout/tries, acquire-use-release)" —
  integration tests hand-copy the call shapes of asy_ntp_client.py and captive_dns.py; drift is not
  detected · [H04]
- **TEST.N296** DRIFT · `tests/test_asy_udp_socket.py:1050-1052` — "Mirrors asy_ntp_client.py's exact
  call shape, including disconnect() on the success path AND unconditionally again in finally" —
  src/asy_ntp_client.py:175-191 `_fetch_ntp_reply` has no try/finally and calls disconnect() once; the
  mirrored shape is stale · related: NET.S13 · [H04]
- **TEST.N297** DRIFT · `tests/test_asy_udp_socket.py:1120` — "validating NTP structure is
  async_connect.py's own job" — names the legacy `async_connect.py`; the NTP validator is now
  src/asy_ntp_client.py · - (low) · [H04]

## tests/test_asy_webserver_service.py

- **TEST.N298** DRIFT · `tests/test_asy_webserver_service.py:1` — "this file predates the implementation
  and no longer mirrors it exactly" — the module docstring admits the suite does not mirror the current
  API contract; readers are told to trust the class signatures instead · [H04]
- **TEST.N299** WORKAROUND · `tests/test_asy_webserver_service.py:10-12` — "scripts/test.sh's
  MICROPYPATH deliberately excludes ext/, so reaching the real vendored ext/microdot.py needs this" —
  test-local sys.path insertion to import vendored Microdot/freezefs; removal trigger: none stated ·
  [H04]
- **TEST.N300** SUPPRESS · `tests/test_asy_webserver_service.py:16-17,421,1005,1622,1673,2396,3011` —
  "type: ignore[import-not-found]" — 8 mypy suppressions: 2 `[import-not-found]` (vendored
  `freezefs.ffsmount`, `microdot`), 2 `[method-assign]`, 2 `[assignment]`, 2 `[arg-type]` · [H04]
- **TEST.N301** INVAR · `tests/test_asy_webserver_service.py:46-48,148-151,1149-1151` — "Never backed by
  a real select.poll()/socket - CLAUDE.md's CI-hang note says why that is a hard requirement here." —
  stream doubles must stay pure-Python scripted fakes; run() is bounded; review-only · related: TEST.T06
  · [H04]
- **TEST.N302** LIMIT · `tests/test_asy_webserver_service.py:53-55,98-100` — "_set_dict_cfg() mirrors
  config_manager.write_config()'s per-field Invalid/Valid semantics closely enough to stand in" — one
  lightweight fake stands in for every sensor and settings module; it already defines
  `get_cfg_schema()`, which masked the real SCD30 500 (test_asy_scd30_driver.py:1113-1118) · related:
  REST.S03 · [H04]
- **TEST.N303** MIRROR · `tests/test_asy_webserver_service.py:155-157,179,187,205-207` — "matches
  extmod/asyncio/stream.py's Stream.readexactly()" — fake reader/writer model asyncio Stream semantics
  (readline no-raise on early close, readexactly EOFError, hang when exhausted); fake ↔ upstream
  stream.py · related: TEST.T19 (low) · [H04]
- **TEST.N304** LIMIT · `tests/test_asy_webserver_service.py:1108-1135` — "Characterizes the known,
  already-flagged gap (SPECIFICATION.md Part A.8's GET-shapes note) rather than asserting it fixed" —
  test pins a torn live-readback as "documented, accepted", but it only calls a fake's get_dict_cfg()
  (the service is built and never used), SPEC A.8's GET-shapes paragraph (:582-593) says nothing about a
  torn read, and test_asy_scd30_driver.py:1140-1146 says the SCD30 torn read is fixed · related:
  TEST.T01 · [H04]
- **TEST.N305** INVAR · `tests/test_asy_webserver_service.py:1244` — "the gate always opens: a task left
  parked on it would wake inside a later test's loop" — tests sharing one process must never leave tasks
  parked in the shared queue · related: TEST.T07 · [H04]
- **TEST.N306** ASSUME · `tests/test_asy_webserver_service.py:1272-1277,1972-1973` — "_make_service()'s
  0.5s outer cap cut a 37 KB body short on a loaded CI runner. 4s stays under run_timed()'s 5s" —
  several tests rely on wall-clock caps (0.02 s/line pacing, 0.5 s → 4 s outer cap, 5 s run_timed) that
  already flaked once under CI load · related: TEST.T04 · [H04]
- **TEST.N307** SUPPRESS · `tests/test_asy_webserver_service.py:1468-1492,2625-2643,2758-2770,...` —
  "gc.threshold(32768) # the project owner's chosen value" — ~50 lines in this file save, set and
  restore the process-global `gc.threshold()` (-1 and 32768) inside test bodies, so the file-level
  (e)-stage run is overridden per test; CLAUDE.md forbids nonstandard gc settings in a test's own setup
  propping a result · related: TEST.T03 · [H04]
- **TEST.N308** LIMIT · `tests/test_asy_webserver_service.py:1807-1833` — "a generous fixed tolerance
  (not scaled per-cycle) catches that while tolerating ordinary allocator fragmentation" — soak uses
  `gc.collect()` + an absolute 4,096 B `mem_free()` bound on the 64-bit Unix heap · covered-by: TEST.S12
  · [H04]
- **TEST.N309** INVAR · `tests/test_asy_webserver_service.py:1852-1853` — "os.mount() raises EEXIST on a
  repeat target, and every test in this file shares one interpreter process" — unique mount point per
  test · - (low) · [H04]
- **TEST.N310** MIRROR · `tests/test_asy_webserver_service.py:2072-2074,2469-2470` — "Mirrored as a
  literal because const() leaves no module attribute to read" — NTP_Host bound (1,024) and `chunk_bytes`
  (256) hand-copied into the test · related: GEN.T06 · [H04]
- **TEST.N311** LIMIT · `tests/test_asy_webserver_service.py:2590,2650` — "A Unix-port heap can never
  reproduce an embedded-scale MemoryError - these are guards." — the hammer tests are correctness guards
  only; embedded memory behaviour is untested at this tier · related: TWIN.T06 · [H04]
- **TEST.N312** INVAR · `tests/test_asy_webserver_service.py:2592-2594` — "That setting is
  process-global (py/modgc.c has no per-object/per-task scoping), so every test below saves and restores
  the value it finds already set" — shared process-wide gc state across tests in one file, restored by
  convention · related: TEST.T07 · [H04]
- **TEST.N313** INVAR · `tests/test_asy_webserver_service.py:2615-2617,2717-2719` — "this test alone
  would still pass with /status's streaming reverted to one plain dict" — the body-drain helper accepts
  both shapes, so every hammer test must call `_assert_body_is_bounded_stream()` to be meaningful ·
  related: TEST.T01 · [H04]

## tests/test_asy_wifi_service.py

- **TEST.N314** MIRROR · `tests/test_asy_wifi_service.py:14-16,22-23` — "Keep these four in sync with
  asy_wifi_service.py's own definitions." — `_PHASE_*` values and the
  `_VAL_SSID/_VAL_PW/_VAL_CTRY/_VAL_HOST/_VAL_LED` schema tuples are hand-copied from src
  (const()-folded); kept in sync by hand · related: GEN.T06 · [H04]
- **TEST.N315** WORKAROUND · `tests/test_asy_wifi_service.py:60-62` — "_wlan(client) is typed against
  the real network.WLAN stub (pyproject.toml's tests/network.py exclude is deliberate), but at runtime
  MICROPYPATH constructs tests/network.py's fake" — one Any-narrowing helper hides the fake-vs-stub type
  split; removal trigger: none stated · related: TEST.T19 (low) · [H04]
- **TEST.N316** SUPPRESS · `tests/test_asy_wifi_service.py:217,838,1724,2119,2309,2569,...` — "type:
  ignore[method-assign, assignment] # deliberate monkeypatch" — 35 mypy suppressions: 23
  `[method-assign]`, 6 `[method-assign, assignment]`, 5 `[assignment]` (incl. process-wide
  `asyncio.sleep` and module `time`), 1 `[return-value]` · related: TEST.T11 · [H04]
- **TEST.N317** SUPPRESS · `tests/test_asy_wifi_service.py:245,255` — "# noqa: S106 - a literal test
  value, not a credential" — two S106 (hardcoded password) suppressions for test hotspot passwords ·
  related: CI.S08 · [H04]
- **TEST.N318** LIMIT · `tests/test_asy_wifi_service.py:112-114` — "toggles tests/machine.py's shared
  Timer.raise_on_arm for the `with` block, simulating rp2 alarm-pool exhaustion" — another copy of the
  raise-on-arm helper; alarm-pool exhaustion only simulated · related: TEST.S18 · [H04]
- **TEST.N319** LIMIT · `tests/test_asy_wifi_service.py:141-143` — "tests/machine.py's fake Pin doesn't
  accept the real Pin(..., value=0) kwarg asy_wifi_service.py passes" — every WiFi test passes
  `led_pin=None`; the real onboard-LED Pin construction path is never exercised at the mock tier ·
  related: TEST.S15 · [H04]
- **TEST.N320** LIMIT · `tests/test_asy_wifi_service.py:208-210` — "_switch_wlan_mode()'s happy path
  makes several real asyncio.sleep() calls (2s+1s+1s of settle time)" — settle sleeps collapsed to
  sleep(0) via a process-wide monkeypatch; the CYW43 settle timing is not modelled · - (low) · [H04]
- **TEST.N321** DRIFT · `tests/test_asy_wifi_service.py:741` — "exactly the shape a future REST endpoint
  will use" — `/networking` PUT already exists; "future" is stale · - (low) · [H04]
- **TEST.N322** LIMIT · `tests/test_asy_wifi_service.py:830-832` — "a finally only fires a trace event
  when something actually passes through it" — coverage of lock-release finally blocks needs dedicated
  tests (E.5.1 false-negative class) · related: TEST.T09 (low) · [H04]
- **TEST.N323** DRIFT · `tests/test_asy_wifi_service.py:1194` — "Mirrors _run_sta_mode()'s own
  acquire-then-call shape (src/asy_wifi_service.py:527-533)" — src/asy_wifi_service.py:527-533 is
  `_flash_led_off()`; `_run_sta_mode()` starts at :583 (stale line citation) · [H04]
- **TEST.N324** LIMIT · `tests/test_asy_wifi_service.py:1563-1565` — "this runs the full
  _STA_DISCONNECT_WAIT_ITERS(20) * 0.5s bound in real time, since const() values are compiled away and
  can't be fast-forwarded (Part E.5.1)" — a 10 s real-time test; const()-folded timing constants cannot
  be shortened in tests · related: TEST.T04 · [H04]
- **TEST.N325** WORKAROUND · `tests/test_asy_wifi_service.py:2289-2291` — "DNSServer.__init__ hardcodes
  privileged port 53 (no root in CI), redirected here by swapping client.dns_server.udps" — captive DNS
  integration tests replace the server socket; relies on DNSServer.run() never rebuilding udps; removal
  trigger: none stated · [H04]
- **TEST.N326** INVAR · `tests/test_asy_wifi_service.py:2294-2296` — "27000+, not a base shared with
  another test file: scripts/test.sh runs files concurrently, so a base must be disjoint from every
  other file's" — per-file port bases must stay disjoint and below 32768; convention only · related:
  TEST.T06 · [H04]
- **TEST.N327** PLATFORM · `tests/test_asy_wifi_service.py:2298-2300` — "A duplicate unicast UDP bind
  does not fail with EADDRINUSE here (both sockets set SO_REUSEADDR, confirmed directly) - it silently
  delivers each datagram to one socket only" — a port collision between parallel files surfaces as an
  unexplained timeout · related: TEST.T04 · [H04]
- **TEST.N328** WORKAROUND · `tests/test_asy_wifi_service.py:2307-2308` — "Same Unix-port-only
  workaround as test_asy_ntp_client.py's own make_addr()" — #6924 opaque-sockaddr workaround repeated;
  removal trigger: none stated · [H04]
- **TEST.N329** LIMIT · `tests/test_asy_wifi_service.py:2356-2361` — "Without this, a real two-socket
  round trip drops every packet as \"unparseable address\" regardless of subnet (confirmed directly)" —
  on the Unix port captive_dns cannot parse the opaque sockaddr, so the subnet-filter accept/reject path
  is testable only through a scripted fake socket · related: NET.T06 · [H04]
- **TEST.N330** LIMIT · `tests/test_asy_wifi_service.py:2727-2732` — "Neither WLAN fake ever transitions
  _status to STAT_GOT_IP for AP mode on its own (a deliberate mocking simplification, not a modeling bug
  to fix here)" — the fakes cannot reproduce the AP steady state; "a real AP interface does reach
  STAT_GOT_IP" is verified against source only · related: NET.S08 · [H04]

## Partition-wide aggregates

- **TEST.N331** SUPPRESS · `tests/test_base_classes.py:23; tests/test_fram_integration.py:21; tests/test_notification_fram_integration.py:24; tests/test_ntp_fram_system_integration.py:28; tests/test_print_log.py:13; tests/test_system_service.py:16; tests/test_voc_algorithm.py:14`
  — "asy_spi_driver._SPI = FakeMB85RS64V # type: ignore[misc]" — 7 files replace the real SPI class
  module-wide with the FRAM chip fake at import time; this is safe only because every test file runs as
  its own Unix-port process ("Same one-process-per-test-file swap"), so the process-per-file model is
  load-bearing · related: TEST.T07 · [H05]
- **TEST.N332** SUPPRESS · `partition-wide (45 sites incl. combined codes: test_config_manager.py 36, test_base_classes.py 3, test_captive_dns.py 3, test_crc_checks.py 1, test_ntp_fram_system_integration.py 1, test_ntp_wifi_dns_integration.py 1)`
  — "# type: ignore[arg-type]" — Deliberate wrong-type inputs for defensive-contract tests; the largest
  suppression class in this partition · [H05]
- **TEST.N333** SUPPRESS · `partition-wide (39 sites incl. combined `[assignment, misc]`: test_captive_dns.py 17, test_config_manager.py 6, test_ntp_fram_system_integration.py 4, test_system_service.py 4, test_ntp_wifi_dns_integration.py 3, test_bus_hazard_multi_device.py/test_notification_scd30_sgp40_integration.py/test_notification_sgp40_integration.py/test_print_log.py/test_tmp_scratch.py 1 each)`
  — "# type: ignore[assignment]" — Module-global monkeypatching (asyncio.sleep, udps, DNSQuery, json,
  AsyUDPSocket) is the mocking mechanism; each site silences mypy · related: TEST.T11 · [H05]
- **TEST.N334** SUPPRESS · `tests/test_base_classes.py:897,1162; tests/test_system_service.py:486,1304; tests/test_uart_comm_hazard.py:530,1003,1044`
  — "# type: ignore[method-assign]" — 7 method-assign suppressions in this partition (CLAUDE.md's "~157"
  repo-wide count is already flagged stale by DOC.S08) · related: DOC.S08 · [H05]
- **TEST.N335** SUPPRESS · `tests/test_ticks_rollover.py:35,49,51,61,62,70,71,88,89` — "# type:
  ignore[type-var] # stub gap, see module docstring" — 9 suppressions for a stub gap in
  `time.ticks_add()`'s typing (see test_ticks_rollover.py section) · [H05]
- **TEST.N336** SUPPRESS · `tests/test_captive_dns.py:113-114,383-384,717-718,779-780; tests/test_system_service.py (17 CancelledError sites, 342-1228); tests/test_uart_comm_hazard.py (3); tests/test_neopixel_wifi_integration.py:40; tests/test_notification_*_integration.py (4); tests/test_ntp_*_integration.py (3)`
  — "except asyncio.CancelledError: pass" / "except (TypeError, AttributeError): pass" — Expected
  exceptions swallowed with no further assertion: CancelledError in cancel/cleanup helpers, and in
  test_captive_dns.py the pinned contract that a non-str input RAISES TypeError/AttributeError (not
  degrades) · related: TEST.T01 · [H05]
- **TEST.N337** INVAR · `tests/test_base_classes.py:41; tests/test_captive_dns.py:21; tests/test_config_manager.py:21; tests/test_crc_checks.py:17; tests/test_fram_integration.py:42 (and most files)`
  — "drives a coroutine to completion for these sync test_* functions" — Each file keeps its own local
  `run()` wrapper around `asyncio.run()`; the CLAUDE.md no-nested-`asyncio.run()` rule depends on these
  only ever being called from sync scope, review-only · related: TEST.T06, TEST.S18 · [H05]

## tests/test_base_classes.py

- **TEST.N338** LIMIT · `tests/test_base_classes.py:54-56` — "proving SensorReader's FRAM-backed path
  stays exception-safe against the general _FramManager/_FramChunk Protocol contract" — The raise-path
  tests use a local fake because the real AsyFramManager's own try/except means write_into()/read_into()
  can no longer raise, so those defensive branches are exercised only through a double · [H05]
- **TEST.N339** INVAR · `tests/test_base_classes.py:61-63, 85-87` — "Every parameter below keeps its
  exact name (and stays unused)" — The fakes must keep the Protocol's exact parameter names because mypy
  matches Protocols structurally by name and print_log.py calls `get_chunk(size, crc=CRC8())` by keyword
  · [H05]
- **TEST.N340** MIRROR · `tests/test_base_classes.py:54` — "Minimal local fake (mirroring
  tests/test_print_log.py's)" — The raising FRAM fakes here are copies of test_print_log.py's; two
  copies to keep aligned · related: TEST.T08 · [H05]
- **TEST.N341** INVAR · `tests/test_base_classes.py:699-701` — "history_length=4 matches
  _RaisingFramChunk.get_buffer()'s hardcoded 6-byte buffer" — The test's history_length must match the
  fake's hardcoded buffer, or the test fails for the wrong reason (buffer size, not raise_on_write) ·
  [H05]
- **TEST.N342** LIMIT · `tests/test_base_classes.py:1531-1533` — "Unreachable via _set_dict_cfg's normal
  flow" — Tests a defensive early return that normal flow never reaches (low) · [H05]
- **TEST.N343** LIMIT · `tests/test_base_classes.py:1790-1792` — "The real ConfigManager-backed
  _set_mgr_cfg never does this, but a subclass override could" — Malformed-override tests (raise /
  non-dict / missing key) cover shapes only a misbehaving subclass could produce (low) · [H05]
- **TEST.N344** SUPPRESS · `tests/test_base_classes.py:611, 686, 702, 724, 1775` — "# type:
  ignore[return-value]" / "# type: ignore[arg-type]" — Deliberately malformed overrides and
  Protocol-fake arguments · [H05]

## tests/test_bus_hazard_generated.py

- **TEST.N345** ASSUME · `tests/test_bus_hazard_generated.py:41-43` — "tests/ runs as the Unix-port
  interpreter's cwd == repo root (scripts/test.sh's own convention" — The relative path
  `build/generated_src` works only when test.sh's cwd convention holds · [H05]
- **TEST.N346** INVAR · `tests/test_bus_hazard_generated.py:48-50, 64` — "discovered from whichever
  wiring-plan JSONs scripts/_generate_sensortask_modules.py already wrote" — The file depends on
  generation having run first (asserts non-empty); a stale build dir would test stale wiring · related:
  TEST.T09 · [H05]
- **TEST.N347** LIMIT · `tests/test_bus_hazard_generated.py:68-73` — "assert bus_name.startswith("i2c"),
  f"unexpected I2C bus key shape" — The generated scheme handles I2C buses only; any SPI bus key in a
  wiring plan would abort the file, and SPI hazards stay hand-written · [H05]
- **TEST.N348** LIMIT · `tests/test_bus_hazard_generated.py:104-106` — "a lone occupant on its own bus
  has no cross-sensor hazard to prove anything about" — Cross-occupant scenarios are generated only for
  buses with 2+ occupants; the membership test is then tautological · covered-by: TEST.S01 · [H05]
- **TEST.N349** INVAR · `tests/test_bus_hazard_generated.py:139-141` — "a real occupant with no
  tests/_bus_hazard_catalog.py adapter yet must abort with a clear, actionable message" — A new driver
  on an I2C bus needs a catalog adapter, and the file must fail loud rather than skip · related:
  TEST.T06 · [H05]

## tests/test_bus_hazard_multi_device.py

- **TEST.N350** SETTLED · `tests/test_bus_hazard_multi_device.py:1-3` — "Holds only driver-agnostic
  hazard shapes ... Runs alongside test_bus_hazard_generated.py, not a staging area for it" — Division
  of labour between the hand-written and generated mock bus-hazard tiers · [H05]
- **TEST.N351** MIRROR · `tests/test_bus_hazard_multi_device.py:78-80, 99-100` — "the same one
  test_asy_bmp3xx_driver.py uses" — BMP3xx calibration/ADC dataset and STATUS register shape copied from
  test_asy_bmp3xx_driver.py · related: TEST.T08 · [H05]
- **TEST.N352** LIMIT · `tests/test_bus_hazard_multi_device.py:275-276` — "This is the ROGUE-broadcast
  case tests/_bus_hazard_catalog.py's TOML-driven scheme cannot generate" — Rogue general-call coverage
  exists only as this hand-written test · [H05]
- **TEST.N353** LIMIT · `tests/test_bus_hazard_multi_device.py:391-392` — "The generated TOML-driven
  scheme cannot produce this shape (every device TOML puts the FRAM alone on spi0)" — Multi-device SPI
  is covered only by this synthetic pair; no real device has two SPI occupants · [H05]
- **TEST.N354** SUPPRESS · `tests/test_bus_hazard_multi_device.py:52, 457` — "# type:
  ignore[assignment]" / "# type: ignore[union-attr] # the fake SPI behind the wrapper" — asyncio.sleep
  patch; reaching into the fake SPI behind the wrapper · [H05]
- **TEST.N355** LIMIT · `tests/test_bus_hazard_multi_device.py:36-38` — "asyncio.gather() itself returns
  a Future, not a Coroutine - mypy rejects passing it straight to run()" — Typing workaround convention
  (wrap gather in a scenario coroutine) shared with test_asy_i2c_driver.py (low) · [H05]

## tests/test_captive_dns.py

- **TEST.N356** INVAR · `tests/test_captive_dns.py:29-31` — "Below the OS ephemeral range (32768-60999)
  so a concurrently-running ephemeral socket can never be assigned this port" — UDP base 22000 (E.1's
  per-file disjoint port bases) is kept disjoint by review only; `make_port()` increments per call (8
  call sites today) toward the 23000 ntp_client base (low) · related: TEST.T06, TEST.S21 · [H05]
- **TEST.N357** WORKAROUND · `tests/test_captive_dns.py:41-44` — "rejects a plain (host, port) tuple in
  bind()/sendto() with "TypeError: object with buffer protocol required" (micropython/micropython#6924)"
  — Unix-port-only defect; tests resolve via getaddrinfo first; removal trigger: none stated · [H05]
- **TEST.N358** LIMIT · `tests/test_captive_dns.py:327-333, 800-806` — "this environment can never
  itself produce a real string addr[0] for a server-mode socket" — In the Unix-port build recvfrom()
  returns an opaque raw sockaddr, so the real-socket tests can only assert liveness/rebind;
  reply-to-client over a real socket is never tested at this tier · [H05]
- **TEST.N359** ASSUME · `tests/test_captive_dns.py:479-482` — "well under that margin proves the guard
  is actually what's preventing it" — Wall-clock bound `elapsed_ms < 1000` against a 3 s backoff ·
  covered-by: TEST.S14 · [H05]
- **TEST.N360** MIRROR · `tests/test_captive_dns.py:867-872` — "replicates asy_wifi_service.py's real
  DNSServer usage exactly. That module cannot be imported here" — Test hand-copies the real caller's
  construct-once / create_task / fire-and-forget cancel() pattern (src/asy_wifi_service.py:170, 299-301,
  329-330, 394); must be kept in sync by hand · [H05]
- **TEST.N361** LIMIT · `tests/test_captive_dns.py:902-904` — "The one fault category that genuinely
  cannot be produced for real ... simulated with a monkeypatched DNSQuery" — run()'s catch-all backoff
  is reachable only by monkeypatching a dependency · [H05]
- **TEST.N362** ASSUME · `tests/test_captive_dns.py:1005-1017` — "possibly a 5th call too (run() loops
  straight back into recvfrom() again after replying, racing this test's own _wait_until poll)" —
  Backoff-gap tests assert wall-clock windows (400-800, 900-1400, 1900-2600 ms) and tolerate a known
  race on call count · related: TEST.S14 · [H05]
- **TEST.N363** SUPPRESS · `tests/test_captive_dns.py:44, 934, 947` — "# type: ignore[return-value]" /
  "# type: ignore[assignment,misc]" / "# type: ignore[misc]" — getaddrinfo sockaddr typing; DNSQuery
  class monkeypatch · [H05]

## tests/test_config_manager.py

- **TEST.N364** LIMIT · `tests/test_config_manager.py:339-341` — "this is a defensive check on the
  function's own general contract, not a reachable production path" — coerce_numeric non-(int,float)
  scalar_type branch is unreachable in production (low) · [H05]
- **TEST.N365** ASSUME · `tests/test_config_manager.py:1743-1745, 1974-1976` — "two separate top-level
  run() calls would race the independently-scheduled flush task" — Tests must keep write+read in one
  coroutine with no await; test determinism depends on that discipline · related: TEST.T04 · [H05]
- **TEST.N366** LIMIT · `tests/test_config_manager.py:1750-1752` — "Deliberately not asserting
  mgr._cache's exact value here" — Whether the deferred flush has run is non-deterministic under this
  harness, so that state is left unasserted · [H05]
- **TEST.N367** LIMIT · `tests/test_config_manager.py:2207-2212` — "no config file small enough to be
  safe in a test can provoke it" — MemoryError arms of setup()/write_config()/_flush_staged() are
  reachable only by substituting the module's `json` name · [H05]
- **TEST.N368** SUPPRESS · `tests/test_config_manager.py:2360` — "# noqa: B905 - MicroPython zip()
  rejects strict=" — Ruff rule suppressed for a MicroPython limitation · [H05]
- **TEST.N369** SUPPRESS · `tests/test_config_manager.py:820-821, 1216, 2348, 2352` — "# type:
  ignore[arg-type, comparison-overlap]" / "[list-item, comparison-overlap]" / "[attr-defined]" —
  Non-string-name schema tests; module-level `open` shadowing · [H05]

## tests/test_crc_checks.py

- **TEST.N370** LIMIT · `tests/test_crc_checks.py:734-740` — "no real bytearray can force that to fail"
  — check()'s MemoryError arm is reachable only through a stand-in buffer whose slice raises · [H05]
- **TEST.N371** ASSUME · `tests/test_crc_checks.py:778-780` — "Observed under the real interpreter:
  exactly one tick per byte processed, asserted against half that" — The cooperative-yield test pins a
  Unix-port scheduler observation with a 2x margin · [H05]
- **TEST.N372** SUPPRESS · `tests/test_crc_checks.py:761` — "# type: ignore[arg-type]" — Stand-in buffer
  passed where bytearray is typed · [H05]

## tests/test_fake_timer_and_network.py

- **TEST.N373** MIRROR · `tests/test_fake_timer_and_network.py:1-3` — "a fake that drifts from silicon
  would let a test pass for code that fails on the board" — tests/machine.py Timer (ONE_SHOT spent after
  one fire, PERIODIC re-arms, drop() models F.1's lost soft callback) and tests/network.py byte bounds
  (C.7.4) are asserted against the fakes only, never against rp2 silicon or source here · related:
  TEST.T19, TEST.T05 · [H05]
- **TEST.N374** LIMIT · `tests/test_fake_timer_and_network.py:86` — "the fake's connect_calls is
  test-only, absent from the board stub" — The test reads a fake-only attribute · [H05]
- **TEST.N375** INVAR · `tests/test_fake_timer_and_network.py:74-75, 81` — "network.country("DE")" /
  "network.hostname("SensorNode")" — Tests mutate process-global fake network state and restore it by
  hand at the end (low) · related: TEST.T07 · [H05]
- **TEST.N376** SUPPRESS · `tests/test_fake_timer_and_network.py:64` — "# type: ignore[operator]" —
  Generic `_raises()` helper · [H05]

## tests/test_fram_integration.py

- **TEST.N377** MIRROR · `tests/test_fram_integration.py:37-38` — "asy_fram_manager.py's own _STATUS_*
  are micropython.const() and compiled away - not importable" — The test hand-copies the on-chip status
  constants; drift from src is not detected · [H05]
- **TEST.N378** WORKAROUND · `tests/test_fram_integration.py:159-164, 177` — "gc.collect() each cycle:
  without it this tight allocate-heavy loop exhausts the Unix-port binary's heap after ~7 cycles" — A
  gc.collect() in a test loop props up a MemoryError, attributed to a "test-environment GC-timing
  artifact" (CLAUDE.md forbids gc.collect() in test setup propping a result); removal trigger: none
  stated · covered-by: TEST.S11 · [H05]
- **TEST.N379** MIRROR · `tests/test_fram_integration.py:304-305` — "Mirrored at the twin tier (Run 5b)
  and on real silicon (tests_hardware/flash/test_fram_storage.py)" — Same both-blocks-BUSY scenario is
  claimed at three tiers · [H05]
- **TEST.N380** SUPPRESS · `tests/test_fram_integration.py:21` — "# type: ignore[misc]" — See
  partition-wide `_SPI` swap aggregate · [H05]

## tests/test_framing_codecs.py

- **TEST.N381** LIMIT · `tests/test_framing_codecs.py:172-175` — "the except clause that catches a real
  MemoryError/OverflowError ... had no test of its own" — The allocation-failure arm is exercised with a
  `1 << 40` bound on the 64-bit host; whether it raises MemoryError or OverflowError is host-specific ·
  [H05]

## tests/test_machine_uart_link.py

- **TEST.N382** MIRROR · `tests/test_machine_uart_link.py:1-3` — "The backend-agnostic half lives in
  _uart_link_contract.py and is re-run against digital_twin/machine.py's own link" — Mock and twin UART
  link models share one contract suite; link-model specifics (A1) and the bounded poller (A2) are
  mock-only · related: TEST.T05 · [H05]
- **TEST.N383** INVAR · `tests/test_machine_uart_link.py:103` — "Without this the timeout paths are
  unreachable and every timeout test passes blindly" — `force_not_ready(n)` is the only way timeout
  paths get exercised; tests that skip it cannot reach them · [H05]
- **TEST.N384** INVAR · `tests/test_machine_uart_link.py:114-120` — "The standing rule, asserted rather
  than left to review. Compared by type *name*" — CLAUDE.md's "bounded fake poller, never a real
  select.poll()" rule is machine-checked only for `LinkPoller` itself, by a type-name comparison; other
  fake-stream doubles remain review-only · related: TEST.T06 · [H05]
- **TEST.N385** ASSUME · `tests/test_machine_uart_link.py:171-173` — "measured at ~18 entries per fake
  per protocol transaction, which exhausts the interpreter heap on a long run" — Single measurement
  behind bounding the fakes' call log at `_LOG_MAXLEN` · [H05]
- **TEST.N386** LIMIT · `tests/test_machine_uart_link.py:171-186` — "Bounded now, and the drop is
  visible rather than silent" — The fake's `log` drops old entries past `_LOG_MAXLEN`; any assertion on
  early log entries in a long test silently sees a truncated log unless it checks `log.dropped` · [H05]
- **TEST.N387** INVAR · `tests/test_machine_uart_link.py:77, 159` — "an endpoint belongs to exactly one
  link" / "no module-level shared link object" — Cross-test isolation of fake UART links rests on
  per-test make_link() · related: TEST.T07 · [H05]

## tests/test_neopixel_wifi_integration.py

- **TEST.N388** SUPPRESS · `tests/test_neopixel_wifi_integration.py:40-41` — "except
  asyncio.CancelledError: pass" — Cancel helper; see aggregate · [H05]

## tests/test_notification_fram_integration.py

- **TEST.N389** SUPPRESS · `tests/test_notification_fram_integration.py:24` — "# type: ignore[misc]" —
  See partition-wide `_SPI` swap aggregate · [H05]

## tests/test_notification_neopixel_integration.py

- **TEST.N390** ASSUME · `tests/test_notification_neopixel_integration.py:60-61, 94, 120, 145-147` —
  "one triggered cycle's real settle time (2*0.5=1.0s) + margin" — Fixed real-time sleeps (1.3 s, 2.5 s,
  0.1 s, 1.5 s) with ~0.3-0.5 s margins; host load can fail them · related: TEST.T04 · [H05]

## tests/test_notification_scd30_integration.py

- **TEST.N391** LIMIT · `tests/test_notification_scd30_integration.py:139-141` — "driven directly
  instead of through the full irq/timer machinery" — Integration tests hand-drive read_loop's per-cycle
  steps; the irq/timer path is not part of this integration · [H05]
- **TEST.N392** MIRROR · `tests/test_notification_scd30_integration.py:139-141` — "Exactly what
  read_loop() itself does per cycle (see asy_scd30_driver.py)" — The test re-implements read_loop()'s
  per-cycle call sequence; drift in src is not detected · [H05]
- **TEST.N393** INVAR · `tests/test_notification_scd30_integration.py:227-236` — "MicroPython's asyncio
  does not reject that with a clean RuntimeError as CPython does - it corrupts the scheduler badly
  enough to segfault" — Frame builders call `asyncio.run()` via crc8_byte(), so they must stay at sync
  top level; review-only convention · related: TEST.T06 · [H05]
- **TEST.N394** ASSUME · `tests/test_notification_scd30_integration.py:148, 176, 201, 253` — "one
  triggered cycle's real settle time (2*0.5=1.0s) + margin" — Fixed real-time sleeps with 0.3 s margin ·
  related: TEST.T04 · [H05]
- **TEST.N395** SUPPRESS · `tests/test_notification_scd30_integration.py:63` — "# type:
  ignore[return-value]" — Reaching the raw fake bus through the wrapper chain · [H05]

## tests/test_notification_scd30_sgp40_integration.py

- **TEST.N396** MIRROR · `tests/test_notification_scd30_sgp40_integration.py:84, 122` — "register/data
  frame builders, verbatim from test_notification_scd30_integration.py" / "word/CRC builders, verbatim
  from test_notification_sgp40_integration.py" — Verbatim copies of helpers across three files ·
  related: TEST.T08 · [H05]
- **TEST.N397** LIMIT · `tests/test_notification_scd30_sgp40_integration.py:145-150` — "scd_reader's
  real reading is deliberately not used" — SGP40 compensation uses a fixed stand-in, not the real SCD30
  reading, so the scd30→sgp40 compensation seam is not exercised here · [H05]
- **TEST.N398** ASSUME · `tests/test_notification_scd30_sgp40_integration.py:228-231` — "may run one
  after another rather than simultaneously ... generous margin covers either ordering" — Fixed 2.6 s
  sleep for two 1.0 s ramps · related: TEST.T04 · [H05]
- **TEST.N399** SUPPRESS · `tests/test_notification_scd30_sgp40_integration.py:48` — "# type:
  ignore[assignment] # deliberate monkeypatch" — Process-wide asyncio.sleep replacement
  (_FastAsyncSleep) · [H05]

## tests/test_notification_sgp40_integration.py

- **TEST.N400** INVAR · `tests/test_notification_sgp40_integration.py:202-204` — "a nested one segfaults
  the interpreter - found the hard way while writing this test" — No-nested-asyncio.run rule, second
  confirmed instance · related: TEST.T06 · [H05]
- **TEST.N401** ASSUME · `tests/test_notification_sgp40_integration.py:181, 211, 255` — "one triggered
  cycle's real settle time (2*0.5=1.0s) + margin" — Fixed real-time sleeps · related: TEST.T04 · [H05]
- **TEST.N402** SUPPRESS · `tests/test_notification_sgp40_integration.py:52` — "# type:
  ignore[assignment] # deliberate monkeypatch" — Process-wide asyncio.sleep replacement · [H05]

## tests/test_ntp_fram_system_integration.py

- **TEST.N403** ASSUME · `tests/test_ntp_fram_system_integration.py:326-328` — "1.0s, not a razor-thin
  0.2s ... margin enough that scheduling jitter cannot produce a false failure" — Timing margin claim ·
  related: TEST.T04 · [H05]
- **TEST.N404** ASSUME · `tests/test_ntp_fram_system_integration.py:443, 550, 614, 644` — "real
  wall-clock wait for start_and_check_tasks()'s own 2s poll" — Fixed 2.5 s waits against a 2 s
  supervisor poll · related: TEST.T04 · [H05]
- **TEST.N405** LIMIT · `tests/test_ntp_fram_system_integration.py:504-509, 589-591` — "by tests a
  coverage audit found had never been called at all before" / "flagged SCD30 and SGP40 as the two
  Readers never driven through a real SystemService" — Coverage-audit findings; only BMP3xx, SCD30,
  SGP40 starters are driven through real start_and_check_tasks here · related: TEST.T15 · [H05]
- **TEST.N406** WORKAROUND · `tests/test_ntp_fram_system_integration.py:148-150` — "redirects
  _NTP_UDP_PORT away from the real privileged port 123, and pre-resolves AsyUDPSocket's addr" —
  Unix-port-only workaround (privileged port; #6924 tuple rejection); removal trigger: none stated ·
  [H05]
- **TEST.N407** MIRROR · `tests/test_ntp_fram_system_integration.py:56-58, 126-127` — "kept file-local
  rather than imported (no test file in this suite imports another, SPECIFICATION.md Part E's per-file
  self-containment convention)" — FakeNtpServer/_RedirectNtpNetworking and conn/ntp builders duplicated
  from test_ntp_wifi_dns_integration.py by convention · related: TEST.T08 · [H05] ⟨quote not matched at
  the anchor⟩
- **TEST.N408** INVAR · `tests/test_ntp_fram_system_integration.py:130-131` — "Below the OS ephemeral
  range (32768-60999)" — UDP port base 26000 disjointness is review-only; same dangling
  "TEST_PARALLELISM comment" pointer as test_captive_dns.py:30 · related: TEST.T06 · [H05]
- **TEST.N409** MIRROR · `tests/test_ntp_fram_system_integration.py:370` — "past _NTP_WAIT_TIME (120s,
  one tick per uptime second)" — Test hardcodes 121 ticks against system_service's 120 s constant ·
  [H05]
- **TEST.N410** SUPPRESS · `tests/test_ntp_fram_system_integration.py:28, 138, 163, 168, 173, 528, 596, 626`
  — "# type: ignore[misc]" / "[return-value]" / "[arg-type]" / "[assignment, misc]" / "[assignment]" —
  Module-level socket/SPI/bus monkeypatches · [H05]

## tests/test_ntp_wifi_dns_integration.py

- **TEST.N411** LIMIT · `tests/test_ntp_wifi_dns_integration.py:3-5` — "No real port-53 or port-123
  end-to-end test is attempted, both needing root and neither being CI-portable" — NTP/DNS real-port
  paths untested at this tier; note CLAUDE.md says test.sh grants CAP_NET_BIND_SERVICE via setcap for a
  real port-53 DNS-server test, so "needing root" is at least partly stale (low) · [H05]
- **TEST.N412** LIMIT · `tests/test_ntp_wifi_dns_integration.py:89-91` — "Bypasses the real
  wlan_connect() state machine, out of scope here" — WLAN connected state is set directly on the fake ·
  [H05]
- **TEST.N413** MIRROR · `tests/test_ntp_wifi_dns_integration.py:41-44, 113-114` — "Narrows to Any once
  here, matching test_asy_wifi_service.py's helper" / "duplicated, not imported" — `_wlan()` and
  `_last_err()` helpers duplicated across files · related: TEST.T08 · [H05]
- **TEST.N414** WORKAROUND · `tests/test_ntp_wifi_dns_integration.py:261-263` — "redirects _NTP_UDP_PORT
  away from the real privileged port 123, and pre-resolves AsyUDPSocket's addr" — Same Unix-port-only
  workaround as the NTP suites · [H05]
- **TEST.N415** INVAR · `tests/test_ntp_wifi_dns_integration.py:243-244` — "Below the OS ephemeral range
  (32768-60999)" — UDP base 25000; same dangling TEST_PARALLELISM pointer · [H05]
- **TEST.N416** ASSUME · `tests/test_ntp_wifi_dns_integration.py:216-217` — "_fetch_ntp_reply() blocks
  for its own _NTP_CONN_TIMEOUT (5s), giving this test a window" — Lock-held observation window depends
  on a 5 s src constant · [H05]
- **TEST.N417** SUPPRESS · `tests/test_ntp_wifi_dns_integration.py:142, 167, 251, 276, 284, 289` — "#
  type: ignore[assignment] # deliberate monkeypatch" etc. — Resolver/socket monkeypatches · [H05]

## tests/test_print_log.py

- **TEST.N418** LIMIT · `tests/test_print_log.py:331-336` — "cannot be forced deterministically through
  a real allocation at any size small enough to be safe in a test" — PrintLogHistory's MemoryError
  fallback is reachable only by substituting the module's `deque` name · [H05]
- **TEST.N419** MIRROR · `tests/test_print_log.py:43-45` — "A minimal local fake, not a full FRAM
  simulation" — Source of the raising-fake pattern copied into test_base_classes.py · related: TEST.T08
  · [H05]
- **TEST.N420** SUPPRESS · `tests/test_print_log.py:13, 345, 349` — "# type: ignore[misc]" / "# type:
  ignore[assignment,misc]" — `_SPI` swap; `deque` substitution · [H05]

## tests/test_reset_call_site_invariant.py

- **TEST.N421** ASSUME · `tests/test_reset_call_site_invariant.py:7` — "scripts/test.sh always invokes
  tests from the repo root" — Relative `src` path depends on cwd · [H05]

## tests/test_sensortask_arzi.py

- **TEST.N422** INVAR · `tests/test_sensortask_arzi.py:1-2` — "one of six wrappers over the shared
  tests/_sensortask_scenarios.py library (SPECIFICATION.md Part E.2.1)" — The six per-device wrappers
  are hand-added (unlike test_bus_hazard_generated.py's auto-discovery); a 7th device needs a new
  wrapper file, and nothing enforces it (scripts/test.sh:392-415 only lists them for scheduling) ·
  related: TEST.S09 · [H05]

## tests/test_sensortask_dev.py

- **TEST.N423** MIRROR · `tests/test_sensortask_dev.py:1-11` — "one of six wrappers" — Identical to the
  other five apart from the device name (see arzi item) · [H05]

## tests/test_sensortask_grkizi.py

- **TEST.N424** MIRROR · `tests/test_sensortask_grkizi.py:1-11` — "one of six wrappers" — Identical
  wrapper (see arzi item) · [H05]

## tests/test_sensortask_klkizi.py

- **TEST.N425** MIRROR · `tests/test_sensortask_klkizi.py:1-11` — "one of six wrappers" — Identical
  wrapper (see arzi item) · [H05]

## tests/test_sensortask_schlafzi.py

- **TEST.N426** MIRROR · `tests/test_sensortask_schlafzi.py:1-11` — "one of six wrappers" — Identical
  wrapper (see arzi item) · [H05]

## tests/test_sensortask_wozi.py

- **TEST.N427** MIRROR · `tests/test_sensortask_wozi.py:1-11` — "one of six wrappers" — Identical
  wrapper (see arzi item); the scenario bodies live in tests/_sensortask_scenarios.py (not this
  partition) · related: TEST.S08, TEST.S09 · [H05]

## tests/test_setter_microdot_integration.py

- **TEST.N428** SETTLED · `tests/test_setter_microdot_integration.py:19-21` — "scripts/test.sh's
  MICROPYPATH deliberately excludes ext/, and changing that would be a scripts/ change needing a full
  clean-chroot re-verification" — Per-file `sys.path.insert(0, "ext")` (also
  tests/test_website_build_integration.py:13) instead of changing MICROPYPATH · [H05]
- **TEST.N429** SUPPRESS · `tests/test_setter_microdot_integration.py:27` — "# type:
  ignore[import-not-found]" — See TODO above · [H05]
- **TEST.N430** LIMIT · `tests/test_setter_microdot_integration.py:276-277` — "No real TCP socket is
  opened: Request is constructed directly" — Microdot parsing from a socket stream is not exercised here
  · [H05]
- **TEST.N431** DRIFT · `tests/test_setter_microdot_integration.py:4-6, 688-697, 709-710` — "the one
  sensor whose REST surface is hand-rolled per field instead of schema-driven" / "exactly as in the real
  file" / "the real generated module builds this once" — The SCD30 section never calls
  `SCD30_Reader._set_dict_cfg()`; it re-implements a local dispatch, while
  src/asy_scd30_driver.py:257-289 now holds a "Schema-driven setter" dispatch; the test's local field
  schemas (defaults 2/0/400, :700-704) also differ from src's `def=None`
  (`src/asy_scd30_driver.py:58-61`) · [H05]
- **TEST.N432** LIMIT · `tests/test_setter_microdot_integration.py:692-693` — "only the three fields
  this file exercises are mirrored, not all seven" — SCD30 REST coverage here spans 3 of 7 fields ·
  [H05]
- **TEST.N433** INVAR · `tests/test_setter_microdot_integration.py:709-710, 783-785` — "iterated in a
  fixed order, which the one-shot bus fault below relies on" — The fault-injection test depends on
  dispatch order (tests/machine.py inject_fault is a FIFO) · [H05]

## tests/test_system_service.py

- **TEST.N434** ASSUME · `tests/test_system_service.py:77-79` — "a single sleep(0) not always being
  enough to drain a multi-await iteration" — `_pump()` uses 5 sleep(0) yields per tick; a loop iteration
  with more awaits could outrun it · related: TEST.T04 · [H05]
- **TEST.N435** MIRROR · `tests/test_system_service.py:623, 754, 761, 1237-1239` — "_RESET_DELAY:
  micropython.const(), compiled away, hardcoded per SPECIFICATION.md Part E.5.1" — Tests hardcode 4 s
  reset delay, 3600 s max storage pause, `_TASK_FAIL_MAX` 300 (+100 per restart), `_TASK_CHECK_TIME` 2 s
  · [H05]
- **TEST.N436** SUPPRESS · `tests/test_system_service.py:16, 96, 294, 318, 486, 982, 1304` — "# type:
  ignore[misc]" / "[assignment]" / "[method-assign]" / "[method-assign, assignment] # deliberate
  monkeypatch" — Module/method monkeypatches · [H05]

## tests/test_ticks_rollover.py

- **TEST.N437** WORKAROUND · `tests/test_ticks_rollover.py:32-35 (9 sites :35-89)` — "Stub gap:
  typings/time.pyi types ticks_add()'s first parameter as the opaque _Ticks TypeVar, excluding plain
  int" — Stub defect worked around with `type: ignore[type-var]`; removal trigger: none stated · [H05]
- **TEST.N438** LIMIT · `tests/test_ticks_rollover.py:98-110` — "its absence next to a subtraction is
  the thing to catch" — The subtraction scan is a per-line heuristic over `src/` only: a `now - t0` on a
  line without `ticks_`, generated `sensortask_*.py`, and digital_twin/ are not scanned · related:
  XCUT.T25 · [H05]
- **TEST.N439** INVAR · `tests/test_ticks_rollover.py:8-18, 113-126` — "Named explicitly so a module
  that silently stops using ticks - or a new one that starts - is visible here" — `_KNOWN_TICKS_USERS`
  hand list (6 modules), enforced both ways by the test itself · [H05]

## tests/test_tmp_scratch.py

- **TEST.N440** SETTLED · `tests/test_tmp_scratch.py:165-178` — "This replaces a test that populated the
  shared root with 400,000 real sibling directories ... at a measured 396MB of physical disk writes per
  run" — Structural invariant (no TmpScratch op reads tests/_tmp's shared root) replaces brute force,
  per CLAUDE.md's host-wear rule · [H05]
- **TEST.N441** INVAR · `tests/test_tmp_scratch.py:195-196` — "mkdir(_ROOT) is the one legitimate touch
  of the root itself: idempotent, EEXIST-swallowed, and what makes concurrent construction from several
  test processes safe" — Concurrent-process safety of the scratch root · [H05]
- **TEST.N442** INVAR · `tests/test_tmp_scratch.py:81-83` — "the actual mechanism that used to make a
  "Valid" write silently read back as "Unchanged"" — Construction wipes the whole key subtree to kill
  stale leftovers; hence two concurrently running files sharing one key would wipe each other, so keys
  must stay disjoint (E.1, review-only) · related: TEST.T06 · [H05]
- **TEST.N443** SUPPRESS · `tests/test_tmp_scratch.py:87-88, 208-209, 214-215, 230-231` — "except
  OSError: pass" — Cleanup errors swallowed in test helpers · [H05]
- **TEST.N444** SUPPRESS · `tests/test_tmp_scratch.py:182` — "# type: ignore[assignment]" — `os` binding
  swap inside _tmp_scratch · [H05]

## tests/test_uart_comm_hazard.py

- **TEST.N445** ASSUME · `tests/test_uart_comm_hazard.py:62-64, 68-70` — "measured as transactions
  timing out at this tier's deliberately tiny 30ms" / "at 1x the no-CRC arm sits 1.25x over the 24ms
  floor, well inside the scheduling gap scripts/test.sh's own 16-way oversubscription produces" —
  Timeout budgets (×8 for CRC and sustained runs) are sized from measurements under test.sh's
  parallelism; derivation in Part J.7 · related: TEST.T04 · [H05]
- **TEST.N446** ASSUME · `tests/test_uart_comm_hazard.py:490-492` — "With it raised, 120/120 complete
  with zero errors in both CRC modes, so the shortfall was the harness's" — Single measurement behind
  the 3-rounds-per-transaction listen budget · [H05]
- **TEST.N447** ASSUME · `tests/test_uart_comm_hazard.py:502-515, 1014-1017, 1059-1063` — "gc.collect()"
  — Eight gc.collect() calls bracket gc.mem_alloc() samples in the heap-retention/hammer measurements;
  measurement-only, not a MemoryError prop, but they sit inside tests that must pass at gc.threshold(-1)
  (low) · related: TEST.T03 · [H05]
- **TEST.N448** LIMIT · `tests/test_uart_comm_hazard.py:539-541` — "every test above asserts ErrCount,
  none ErrNum, so a fault reporting the wrong code would pass the whole suite" — Errno-specific coverage
  exists only in the later catalog section · [H05]
- **TEST.N449** INVAR · `tests/test_uart_comm_hazard.py:745-746, 766-767` — "a transaction that times
  out returns None here too, which would read as "the corruption was caught" and quietly retire the
  claim" — Corruption tests must use the sustained budget or pass vacuously · related: TEST.T01 · [H05]
- **TEST.N450** INVAR · `tests/test_uart_comm_hazard.py:527, 602-603, 1121-1123` — "hazard_pair(crc) is
  built out here (its asyncio.run() cannot nest)" — No-nested-asyncio.run rule applied to
  hazard_pair()/errnos()/_clean_ack_bytes() · related: TEST.T06 · [H05]
- **TEST.N451** LIMIT · `tests/test_uart_comm_hazard.py:1092-1093` — "the three cases the systematic
  sweep over the general UART failure taxonomy found uncovered" — Lost final ACK, peer reboot mid-train,
  and mid-frame reconnect were late additions · [H05]
- **TEST.N452** SUPPRESS · `tests/test_uart_comm_hazard.py:530, 1003, 1044` — "fake.log.append = lambda
  entry: None # type: ignore[method-assign]" — Fake recorders muted so heap numbers are src/'s alone ·
  [H05]

## tests/test_voc_algorithm.py

- **TEST.N453** SUPPRESS · `tests/test_voc_algorithm.py:14` — "# type: ignore[misc]" — See
  partition-wide `_SPI` swap aggregate · [H05]

## tests/test_website_build_integration.py

- **TEST.N454** SUPPRESS · `tests/test_website_build_integration.py:15-16, 50` — "# type:
  ignore[import-not-found] # noqa: F401 # mounts /html on import" / "# type: ignore[no-any-return]" —
  Side-effect import, unchecked microdot import · [H05]

## digital_twin/README.md

- **TEST.N455** LIMIT · `digital_twin/README.md:225-230` — "masked by
  `tests/test_asy_webserver_service.py`'s own uniform fakes, which happened to return an already-flat
  shape" — Documents a mock-fidelity blind spot class (fakes returning a simplified shape); also
  historic narrative in docs (low) · related: TEST.T05 · [H06]
- **TEST.N456** RISK · `digital_twin/README.md:761-767` — "**Two different faults produce the identical
  message** ... Neither is a bug in the code under test." — An ambiguous failure message (missing setcap
  vs CPU starvation) · related: TEST.T04 · [H06]

## digital_twin/machine.py

- **TEST.N457** INVAR · `digital_twin/machine.py:59-60` — "Test-only: real GPIO pins never \"reset\"
  between test functions the way this registry needs to for isolation" — Class-level Pin registry shared
  across tests in one process; isolation depends on each test calling `reset_registry()` · related:
  TEST.T07 · [H06]
- **TEST.N458** MIRROR · `digital_twin/machine.py:127-129` — "`tests/machine.py`'s trigger_irq() fires
  unconditionally - a deterministic unit test needs no edge fidelity; a twin does" — Deliberate
  mock↔twin divergence in edge semantics · covered-by: TEST.S15 · [H06]
- **TEST.N459** MIRROR · `digital_twin/machine.py:443-445` — "Same knobs and same semantics as
  tests/machine.py's own _LinkDirection (both are held to tests/_uart_link_contract.py)" — Mock/twin
  UART link contract; enforced by the shared contract tests · related: TEST.T05 · [H06]
- **TEST.N460** LIMIT · `digital_twin/machine.py:553-559` — "Blocks until every in-flight byte has
  landed" — `settle()` busy-waits with `time.sleep_us()`; a test-only seam that blocks the loop · [H06]
- **TEST.N461** INVAR · `digital_twin/machine.py:601-603` — "tests still swap .poller for a bounded
  stand-in (CLAUDE.md's known hang cause)" — CLAUDE.md rule that a UART poller double must be bounded,
  not `select.poll()` · [H06]
- **TEST.N462** MIRROR · `digital_twin/machine.py:756-758` — "Bounded select.poll() stand-in, identical
  in behaviour to tests/machine.py's own" — Duplicate poller in mock and twin; `ipoll()` ignores its
  timeout, `register()`/`unregister()` are no-ops · related: TEST.T05 · [H06]
- **TEST.N463** ASSUME · `digital_twin/machine.py:899-900` — "One physical peripheral - class-level
  shared state, matches real singleton hardware" — Class-level RTC state persists across tests in one
  process · related: TEST.T07 · [H06]

## digital_twin/_fault_injection.py

- **TEST.N464** MIRROR · `digital_twin/_fault_injection.py:1` — "mirroring (independently of)
  `tests/machine.py`'s own `inject_fault()`/`_maybe_raise()` convention" — Two independent fault APIs
  held equal by convention only · related: TEST.T05 · [H06]

## digital_twin/_http_client.py

- **TEST.N465** MIRROR · `digital_twin/_http_client.py:48-59` — "the same case
  tests_hardware/http_client.py's CEILING_CLOSE covers by including http.client.BadStatusLine" — Refusal
  classification mirrored in the hardware client · related: TEST.T17 · [H06]
- **TEST.N466** RISK · `digital_twin/_http_client.py:66-72` — "or an EOF-truncated readline() (b\"\")
  from a connection that closed mid-headers" — A connection cut mid-headers is accepted as a complete
  header block; a body-less truncated response can pass (low) · related: TEST.T17 · [H06]
- **TEST.N467** LIMIT · `digital_twin/_http_client.py:141-181` — "`content_length = headers.get(\"Content-Length\")`"
  — No timeout inside `fetch()`; case-sensitive header lookup; no chunked transfer-encoding support
  (low) · related: TEST.T16 · [H06]

## digital_twin/unix_port_poll_prewarm.py

- **TEST.N468** MIRROR · `digital_twin/unix_port_poll_prewarm.py:23-26` — "Its own band, clear of
  test_digital_twin_http_client.py's canned servers at 18099-18103" — Port bands coordinated by hand
  across files · related: TEST.S21 · [H06]

## digital_twin/neopixel.py

- **TEST.N469** MIRROR · `digital_twin/neopixel.py:1` — "Independent copy from `tests/neopixel.py`, not
  shared." — Deliberate duplicate fake · related: TEST.T05 · [H06]

## tests/test_digital_twin_bmp3xx.py

- **TEST.N470** LIMIT · `tests/test_digital_twin_bmp3xx.py:151-157` — "would violate the default 1.0/5.0
  bounds - proves the override took" — Step-override test cannot fail (scripted deltas lie inside both
  bounds) · covered-by: TEST.S03 · [H06]

## tests/test_digital_twin_bus_hazard_concurrency.py

- **TEST.N471** SUPPRESS · `tests/test_digital_twin_bus_hazard_concurrency.py:22-25` — "`# noqa: E402 - must follow the prewarm above, which is the point of it`"
  — Three E402 suppressions · [H06]
- **TEST.N472** MIRROR · `tests/test_digital_twin_bus_hazard_concurrency.py:50-52` — "`_next_port = 19400 # own range, avoids TIME_WAIT/port collision with the 19100+ range`"
  — Hand-coordinated port bands across test files · related: TEST.S21 · [H06]
- **TEST.N473** INVAR · `tests/test_digital_twin_bus_hazard_concurrency.py:81-86` — "A new driver added
  to a device's own i2c1 needs an entry here before it gets this generic check - see the fail-loud
  assert there." — `_I2C_DRIVER_HEALTH_FIELD` must grow per driver; enforced by an assert at :167-168 ·
  [H06]

## tests/test_digital_twin_construction_{arzi,dev,grkizi,klkizi,schlafzi,wozi}.py

- **TEST.N474** LIMIT · `tests/test_digital_twin_construction_wozi.py:1-6 (same in all six)` — "one of
  six wrappers over the shared tests/_digital_twin_construction_scenarios.py library (SPECIFICATION.md
  Part E.2.1)" — The six wrappers hold no test logic; all coverage (and its prewarm/UDP-shim setup)
  lives in the scenario library outside this partition · related: TEST.S04 · [H06]

## tests/test_digital_twin_fram.py

- **TEST.N475** SETTLED · `tests/test_digital_twin_fram.py:1` — "independently reimplemented, not
  sharing tests/_fram_chip_fake.py" — Deliberate duplicate FRAM fakes · related: TEST.T05 · [H06]
- **TEST.N476** INVAR · `tests/test_digital_twin_fram.py:245-247` — "it is temporarily shrunk to 1 to
  force a straddle" — Module constant monkeypatched and restored in `finally` · [H06]

## tests/test_digital_twin_generic_wiring.py

- **TEST.N477** INVAR · `tests/test_digital_twin_generic_wiring.py:14` — "digital_twin/ must precede
  tests/ here" — sys.path order discipline per file · [H06]
- **TEST.N478** INVAR · `tests/test_digital_twin_generic_wiring.py:183-190` — "machine._wiring_plan
  being process-global state that later tests mutate" — Shared mutable module state across tests; each
  test must reset it · related: TEST.T07 · [H06] ⟨quote not matched at the anchor⟩

## tests/test_digital_twin_http_client.py

- **TEST.N479** ASSUME · `tests/test_digital_twin_http_client.py:51-52` — "asy_webserver_service.py's
  own _mark_connection_close() always sets this on the response too - this client never implements
  keep-alive" — Oracle relies on server hook · related: TEST.T17 · [H06]
- **TEST.N480** MIRROR · `tests/test_digital_twin_http_client.py:81-83` — "as
  tests_hardware/http_client.py's CEILING_CLOSE does by including http.client.BadStatusLine" — Refusal
  classification mirrored across the twin and hardware clients · related: TEST.T17 · [H06]
- **TEST.N481** RISK · `tests/test_digital_twin_http_client.py:92-94` — "a ValueError there escaped as a
  test failure under a burst big enough to make FIN-without-bytes the common outcome rather than RST" —
  Refusal shape depends on kernel TCP behaviour · [H06]
- **TEST.N482** LIMIT · `tests/test_digital_twin_http_client.py:313-317` — "not a claim about
  src/asy_webserver_service.py's behavior - that is the twin integration suite's job" — Smoke test
  against a hand-built server only · [H06]
- **TEST.N483** MIRROR · `tests/test_digital_twin_http_client.py (canned servers) vs digital_twin/unix_port_poll_prewarm.py:23`
  — "clear of test_digital_twin_http_client.py's canned servers at 18099-18103" — Fixed ports
  18099-18103 coordinated by hand · related: TEST.S21 · [H06]

## tests/test_digital_twin_isl29125.py

- **TEST.N484** SUPPRESS · `tests/test_digital_twin_isl29125.py:58` — "`# type: ignore[arg-type]`" —
  mypy suppression on the chip factory · [H06]

## tests/test_digital_twin_isl29125_autorange.py

- **TEST.N485** SUPPRESS · `tests/test_digital_twin_isl29125_autorange.py:95-96` — "No strict= (ruff
  B905): MicroPython's zip() rejects it" / "`# noqa: B905`" — Platform-forced lint suppression · [H06]

## tests/test_digital_twin_launch.py

- **TEST.N486** MIRROR · `tests/test_digital_twin_launch.py:220-225, 252-256` — "duration must clear
  both network.py's _CONNECT_DELAY_S (0.7s) ... and _sensor_loop()'s 2.0s poll interval" — Test
  durations coupled to twin timing constants · related: TEST.T04 · [H06]
- **TEST.N487** ASSUME · `tests/test_digital_twin_launch.py:216, 261` — "only 0.5s, well under the
  8000ms WDT timeout" — Smoke-test wall-clock bounds · [H06]

## tests/test_digital_twin_machine.py

- **TEST.N488** INVAR · `tests/test_digital_twin_machine.py:19-21` — "digital_twin/ must precede tests/
  here specifically so `machine` resolves to the twin's own fake" — Per-file sys.path order discipline ·
  [H06]
- **TEST.N489** ASSUME · `tests/test_digital_twin_machine.py:350-355` — "a granularity close to its
  period races it, the observed count depending on scheduling" — Timing-sensitive test design (5 ms vs
  150 ms) · related: TEST.T04 · [H06]

## tests/test_digital_twin_machine_uart.py

- **TEST.N490** MIRROR · `tests/test_digital_twin_machine_uart.py:1-3` — "Re-runs
  tests/_uart_link_contract.py's shared bodies against the twin backend, so the twin and mock link
  models can differ in fidelity but never in semantics" — Mock↔twin UART contract, test-enforced ·
  related: TEST.T05 · [H06]

## tests/test_digital_twin_network_neopixel.py

- **TEST.N491** MIRROR · `tests/test_digital_twin_network_neopixel.py:1` — "neopixel.py is a
  near-verbatim duplicate of tests/neopixel.py, already proven correct there - this file only locks in
  its basic shape" — Duplicate fake; shape-only test · related: TEST.T05 · [H06]

## tests/test_digital_twin_poll_prewarm.py

- **TEST.N492** SUPPRESS · `tests/test_digital_twin_poll_prewarm.py:74, 78` — "`# type: ignore[attr-defined, assignment] # deliberate monkeypatch`"
  — Monkeypatching the module's `socket` · [H06]
- **TEST.N493** ASSUME · `tests/test_digital_twin_poll_prewarm.py:36-38` — "two files calling
  prewarm_poll_set() within the same ~45ms window both bound one fixed port" — Dated failure analysis ·
  [H06]
- **TEST.N494** INVAR · `tests/test_digital_twin_poll_prewarm.py:21-22, 102-103, 136-137` — "The helper
  tests scan a band of their own" / "Never a silent fallback onto some other port" / "18099-18103 belong
  to test_digital_twin_http_client.py" — Port band allocation by convention · related: TEST.S21 · [H06]

## tests/test_digital_twin_real_website_integration.py

- **TEST.N495** SUPPRESS · `tests/test_digital_twin_real_website_integration.py:19-21` — "`# noqa: E402`"
  — Three E402 suppressions after the prewarm · [H06]
- **TEST.N496** MIRROR · `tests/test_digital_twin_real_website_integration.py:23-25` — "Mirrors
  asy_wifi_service.py's own _PHASE_STA_SEEKING/_PHASE_HOTSPOT values ... keep in sync with
  asy_wifi_service.py's own definitions" — Copied `const()` values · [H06]
- **TEST.N497** MIRROR · `tests/test_digital_twin_real_website_integration.py:45-47` — "Own port range
  (19300+)" — Port band coordination · related: TEST.S21 · [H06]
- **TEST.N498** ASSUME · `tests/test_digital_twin_real_website_integration.py:69-74` — "Measured
  directly against this file's real twin fakes: consistently ready within ~400ms, so 1.0s keeps a ~2.5x
  margin" — Fixed sleep sized from a measurement · related: TEST.T04 · [H06]
- **TEST.N499** SUPPRESS · `tests/test_digital_twin_real_website_integration.py:95` — "`# type: ignore[no-any-return]`"
  — mypy suppression · [H06]
- **TEST.N500** LIMIT · `tests/test_digital_twin_real_website_integration.py:200-201` — "No real WiFi
  task is started - conn._conn_phase is set directly instead" — Hotspot redirect tested via a
  private-state seam · [H06]

## tests/test_digital_twin_run_generic_integration.py

- **TEST.N501** MIRROR · `tests/test_digital_twin_run_generic_integration.py:108-112` — "32768 matches
  buildgen.codegen.generate_boot_entry_source()'s own real-firmware boot entry" — Test pins a copied
  constant · covered-by: SCR.S10 · [H06]

## tests/test_digital_twin_scd30.py

- **TEST.N502** LIMIT · `tests/test_digital_twin_scd30.py:202-210` — "would violate the default
  50.0/1.0/3.0 bounds - proves the override took" — Step-override test cannot fail · covered-by:
  TEST.S03 · [H06]

## tests/test_digital_twin_sensortask_integration.py

- **TEST.N503** SUPPRESS · `tests/test_digital_twin_sensortask_integration.py:32-38` — "`# noqa: E402`"
  — Six E402 suppressions · [H06]
- **TEST.N504** INVAR · `tests/test_digital_twin_sensortask_integration.py:85-90` — "configure_wiring()
  explicitly, every call ... MicroPython's globals() does not preserve definition order" — Test order is
  undefined; shared `machine._wiring_plan` must be reset per test · related: TEST.T07 · [H06]
- **TEST.N505** ASSUME · `tests/test_digital_twin_sensortask_integration.py:98-104` — "consistently
  ready within ~400ms, so 1.0s keeps a ~2.5x margin" — Fixed sleep from a measurement · related:
  TEST.T04 · [H06]
- **TEST.N506** WORKAROUND · `tests/test_digital_twin_sensortask_integration.py:128-136` — "since this
  build's socket may not support settimeout()" / "sendto() rejects a plain (host, port) tuple here" —
  Test-side Unix-port socket quirks; removal trigger: none stated · [H06]
- **TEST.N507** LIMIT · `tests/test_digital_twin_sensortask_integration.py:229-231` — "The exact values
  cannot be cross-checked against buildgen from a MicroPython-run test" — `build` field checked for
  shape only · [H06]
- **TEST.N508** INVAR · `tests/test_digital_twin_sensortask_integration.py:286-288` — "a nested
  asyncio.run() call here segfaulted the real interpreter instead of raising a clean error" — CLAUDE.md
  nested-`asyncio.run()` rule · related: TEST.T06 · [H06]
- **TEST.N509** RISK · `tests/test_digital_twin_sensortask_integration.py:429-431` — "those orphaned
  references starved the Unix-port heap - a real MemoryError once, and a hard segfault once" —
  Orphaned-task hazard in shared-process tests · [H06]
- **TEST.N510** SUPPRESS · `tests/test_digital_twin_sensortask_integration.py:505, 530` — "`# type: ignore[method-assign]`"
  — Two method-assign suppressions (only instances in twin tests) · [H06]
- **TEST.N511** ASSUME · `tests/test_digital_twin_sensortask_integration.py:575-577` — "Eight, not one,
  so the transition does not depend on WHEN the seeding below lands ... (MEASUREMENTS archive 7C)" —
  Timing-window workaround in test design · related: TEST.T04 · [H06]
- **TEST.N512** ASSUME · `tests/test_digital_twin_sensortask_integration.py:663-666, 694, 735, 772` —
  "No public \"init done\" flag exists to poll, so this is a plain, generously-bounded sleep." — Fixed
  2.5 s sleep for SGP40 init · related: TEST.T04 · [H06]

## tests/test_digital_twin_sgp40.py

- **TEST.N513** SETTLED · `tests/test_digital_twin_sgp40.py:5-7` — "digital_twin/ is not on
  scripts/test.sh's MICROPYPATH, deliberately kept separate from the unit-test set" — Per-file sys.path
  insertion convention · [H06]

## tests/test_digital_twin_uart_link.py

- **TEST.N514** SUPPRESS · `tests/test_digital_twin_uart_link.py:24-26` — "`# noqa: E402`" — Three E402
  suppressions · [H06]
- **TEST.N515** INVAR · `tests/test_digital_twin_uart_link.py:67-69` — "a real select.poll() never
  re-checks a Python object's ioctl(), so readiness would never be seen" — Bounded poller rule
  (CLAUDE.md known hang) · [H06]
- **TEST.N516** SUPPRESS · `tests/test_digital_twin_uart_link.py:166, 273` — "`# type: ignore[union-attr]`"
  — mypy suppressions · [H06]
- **TEST.N517** SUPPRESS · `tests/test_digital_twin_uart_link.py:411-413` — "MicroPython has no `await`
  inside a comprehension, so ruff's suggested rewrite does not compile" / "`# noqa: PERF401`" —
  Platform-forced lint suppression · [H06]

## tests/test_digital_twin_webserver_concurrency_{arzi,dev,grkizi,klkizi,schlafzi,wozi}.py

- **TEST.N518** LIMIT · `tests/test_digital_twin_webserver_concurrency_wozi.py:1-2 (same in all six)` —
  "one of six wrappers over the shared tests/_webserver_concurrency_scenarios.py library (Part E.2.1)" —
  Wrappers hold no logic; coverage lives outside this partition · [H06]
- **TEST.N519** SUPPRESS · `tests/test_digital_twin_webserver_concurrency_wozi.py:14 (same in all six)`
  — "`# noqa: E402 - must follow the prewarm`" — Six E402 suppressions · [H06]

## scripts/test.sh

- **TEST.N520** SETTLED · `scripts/test.sh:20-23` — "Not a production bug; CLAUDE.md's \"Local test runs
  pin $TZ\" has the account." — Unix-port `time.mktime()` reads host `$TZ`, so every local/CI unit run
  is pinned to `TZ=UTC`; results under any other TZ are not meaningful. · related: XCUT.T18 · [H09]
- **TEST.N521** LIMIT · `scripts/test.sh:129-131` — "One hazard is NOT closed: a twin test asserting a
  real background transition inside a fixed budget measures host speed" — Declared open hazard: CPU
  starvation fails a healthy twin test; only the speed probe mitigates it. · related: TEST.T04 · [H09]
- **TEST.N522** ASSUME · `scripts/test.sh:214-216, 229-231` — "never this repo's real
  build/generated_src/ or frozen_modules/" / "build_website.sh resolves devices/<device>.toml from the
  repo root, so that one test cannot be handed a tmp_path tree" — The pytest tier's isolation from the
  live tree is by convention, with one acknowledged exception that touches real `devices/`. · related:
  TEST.T13 · [H09]
- **TEST.N523** SETTLED · `scripts/test.sh:311-313` — "the heap value is a measured floor that must
  never be RAISED as a fix" — `-X heapsize=16M`, per-file timeout+retry and stdbuf are standing
  backstops (CLAUDE.md), not fixes. · related: SCR.T01 · [H09]
- **TEST.N524** MIRROR · `scripts/test.sh:321-333` — "Both spellings, because src/'s degrade handlers
  log str(e) and not the class" — Unit-tier MemoryError gate pattern must match the twin and two
  hardware gates; enforced by `tests_scripts/test_memory_error_gate_agreement.py`. · related: TEST.T18 ·
  [H09]

## scripts/_render_coverage.py

- **TEST.N525** ASSUME · `scripts/_render_coverage.py:56-59` — "confirmed against coverage.py's own
  morfs= handling" — 0%-row behaviour relies on coverage.py internals of an unpinned version; anchor
  glob is non-recursive (`<src_dir>/*.py`) and generated modules are never in scope. · related: TEST.T09
  · [H09]

## scripts/_digital_twin_ci_suite.py

- **TEST.N526** MIRROR · `scripts/_digital_twin_ci_suite.py:184-187` — "_MEMORY_ERROR_MARKERS =
  (\"MemoryError\", \"memory allocation failed\")" — Twin-tier gate markers; must agree with test.sh and
  `tests_hardware/harness.py` (`tests_scripts/test_memory_error_gate_agreement.py`). · related: TEST.T18
  · [H09]

## scripts/cross_browser_smoke.mjs

- **TEST.N527** MIRROR · `scripts/cross_browser_smoke.mjs:20-23, 35-36` — "see
  tests_js/_live_twin_command.js's own comment for the full enumeration this continues (19481, 19482
  already taken" — Fixed ports 19420/4444/4445; port uniqueness is a hand-kept enumeration across files.
  · related: TEST.T14 · [H09] ⟨quote not matched at the anchor⟩
- **TEST.N528** LIMIT · `scripts/cross_browser_smoke.mjs:102-105, 110` — "stdio: [\"ignore\",
  \"ignore\", \"pipe\"]" — Twin stdout discarded, state paths empty (in-memory); no MemoryError gate on
  this twin launch. · covered-by: TEST.T18 · [H09]

## pyproject.toml

- **TEST.N529** SUPPRESS · `pyproject.toml:217-229` — "Test code asserts, reaches into privates under
  test, imports lazily after sys.path setup" — tests/**, tests_scripts/** (+S603), tests_hardware/**:
  S101, SLF001, PLC0415, PLR2004, ARG001/002/004/005; digital_twin/**: S101, SLF001, PLC0415, PLR2004. ·
  related: TEST.T11 · [H09]
- **TEST.N530** SUPPRESS · `pyproject.toml:237-243` — "The machine fakes mirror MicroPython's own
  constructors" — tests/machine.py and digital_twin/machine.py: A002, FBT001, FBT002, ANN401. · related:
  TEST.T05 · [H09]
- **TEST.N531** SUPPRESS · `pyproject.toml:244-247` — "fake_run() doubles must accept
  setup_toolchain.run()'s signature exactly" — tests_scripts/test_setup_toolchain_env.py: FBT001,
  FBT002. · [H09]
- **TEST.N532** SUPPRESS · `pyproject.toml:264-276` — "ANN401, category 2 - the asyncio.start_server()
  callback seam" / "category 3 - `_wlan` bridges the real WLAN board stub" / "category 4 - ...
  deliberately passes a TYPE-INVALID value" — ANN401 on test_asy_wifi_service.py, two integration tests,
  test_asy_udp_socket.py; category 3 is a three-file family to change together. · [H09]
- **TEST.N533** SUPPRESS · `pyproject.toml:408-413` — "Vendored, unannotated microdot's
  @app.get()/@app.put() make every handler \"untyped\" ... Revisit if Microdot ships hints." —
  `disallow_untyped_decorators = false` for test_setter_microdot_integration; removal trigger: Microdot
  ships type hints. · [H09]

## tests_scripts/_devices.py

- **TEST.N534** INVAR · `tests_scripts/_devices.py:1-3` — "Six test modules carried their own copy of
  the same six names; a seventh device would have been generated" — The device set for every
  device-parametrized host suite is discovered from `devices/*.toml`, not listed; any suite that still
  hardcodes the six names (CI matrices, JS) is outside this guard · related: CI.T07 · [H10]
- **TEST.N535** INVAR · `tests_scripts/_devices.py:15-18` — "A leaked live-tree fixture ... must never
  be mistaken for a real device" — Device discovery filters `zz_test_*` because the pytest tier runs
  concurrently and `devices/` can hold a live-tree fixture mid-test; filter is by name prefix only ·
  related: TEST.T13 · [H10]
- **TEST.N536** INVAR · `tests_scripts/_devices.py:20` — "every device-parametrized suite would silently
  collect nothing" — Import-time assert fails the whole tier if `devices/` has no TOML (guards vacuous
  parametrization) · [H10]

## tests_scripts/_script_loader.py

- **TEST.N537** INVAR · `tests_scripts/_script_loader.py:2-3` — "Split out of conftest.py so this bare
  import cannot collide with tests_hardware/'s own bare \"conftest\"" — Module split exists only because
  mypy resolves one bare name to one file per run (host_typecheck pass covers both tiers) · related:
  SCR.T15 · [H10]
- **TEST.N538** ASSUME · `tests_scripts/_script_loader.py:19-22` — "Registered in sys.modules BEFORE
  exec_module()" — Loader registers every script under a bare name in `sys.modules` (needed for
  `@dataclass` + future annotations); a name collision between two loaded scripts or a real module would
  silently shadow (low) · [H10]

## tests_scripts/_toml_fixtures.py

- **TEST.N539** LIMIT · `tests_scripts/_toml_fixtures.py:5-6` — "dump_toml() is not a general TOML
  writer - it covers only the shape buildgen/'s own schema uses" — Fixture serializer cannot emit inline
  tables, arrays of tables beyond `[[instance]]`, or nesting deeper than `[instance.wiring.X]`;
  negative-path tests needing those shapes skip (see test_buildgen_validate.py:1208) · [H10]
- **TEST.N540** MIRROR · `tests_scripts/_toml_fixtures.py:13-16` — "matches buildgen.model.TomlDoc's own
  shape; kept as a local alias" — Local `TomlDoc` alias duplicates `buildgen.model.TomlDoc` by hand ·
  [H10]

## tests_scripts/conftest.py

- **TEST.N541** INVAR · `tests_scripts/conftest.py:15-18` — "pytest's rootless import mode puts only
  tests_scripts/ on sys.path, never the repo root" — conftest prepends REPO_ROOT to `sys.path` at
  import; every `import buildgen` in the tier depends on this side effect · [H10]
- **TEST.N542** INVAR · `tests_scripts/conftest.py:22-28` — "Reclaims any `devices/zz_test_*.toml` a
  KILLED earlier run left behind ... race-free by construction" — Session-start autouse fixture unlinks
  files in the real `devices/` tree; "race-free" assumes no concurrent pytest session (e.g. two local
  runs, or test.sh's own sweep) is mid-test · covered-by: TEST.T13 · [H10]
- **TEST.N543** ASSUME · `tests_scripts/conftest.py:46-48` — "Mirrors scripts/build_firmware.py's own
  main()'s --toolchain-dir default resolution exactly" — `micropython_dir` fixture hand-mirrors
  build_firmware.py's PICO_TOOLCHAIN_DIR/~/pico-toolchain default; "scripts/test.sh/CI always provisions
  a real checkout here before this suite runs" · [H10]
- **TEST.N544** MIRROR · `tests_scripts/conftest.py:46-48,55` — "Same path
  scripts/run_digital_twin_ci.sh's own $micropython_bin resolves to" — Unix-port binary path
  (`ports/unix/build-standard/micropython`) is duplicated from build_firmware.py and
  run_digital_twin_ci.sh by hand · related: SCR.S05 · [H10]
- **TEST.N545** SUPPRESS · `tests_scripts/conftest.py:55-60` — "pytest.skip(f\"MicroPython Unix port not
  built at {path}" — Every test using `micropython_bin` SKIPS (not fails) when the standard Unix port is
  absent; a bare `pytest tests_scripts` on an unprovisioned box passes with those tests silently skipped
  · related: TEST.T13 · [H10]
- **TEST.N546** LIMIT · `tests_scripts/conftest.py:60` — "build-standard" — The fixture never checks
  which variant the binary is (settrace vs standard), unlike test.sh's `hasattr(sys, "settrace")` probe
  (low) · related: SCR.S05 · [H10]

## tests_scripts/buildgen_fixtures/malformed_missing_device_table.toml

- **TEST.N547** INVAR · `tests_scripts/buildgen_fixtures/malformed_missing_device_table.toml:1-5` —
  "copied into devices/ under a test-only name for the duration of that one test, then removed" —
  Fixture is placed into the live `devices/` tree (not tmp) because build_website.sh always cd's to the
  repo root · covered-by: TEST.T13 · [H10]

## tests_scripts/test_bench_harness_helpers.py

- **TEST.N548** SUPPRESS · `tests_scripts/test_bench_harness_helpers.py:22-24` — "# noqa: E402 (the
  sys.path line above is what makes these importable)" — Three E402 suppressions; needed because a
  non-sys.path statement (`TESTS_HARDWARE = ...`, `if TYPE_CHECKING:`) precedes the imports (CLAUDE.md's
  E402 rule) · [H10]
- **TEST.N549** SUPPRESS · `tests_scripts/test_bench_harness_helpers.py:78` — "# type: ignore[arg-type]"
  — Duck-typed FakeBoard/FakeBench passed where real harness types are declared · [H10]
- **TEST.N550** LIMIT · `tests_scripts/test_bench_harness_helpers.py:44,52,59,135` — "assert 0.4 <
  time.monotonic() - started < 2.0" — Wall-clock bounds (0.5 s, 0.4-2.0 s, 2.0 s) on host timing;
  sensitive to a loaded CI runner (the tier runs concurrently with the MicroPython tier) · related:
  TEST.T04 · [H10]
- **TEST.N551** LIMIT · `tests_scripts/test_bench_harness_helpers.py:138-143` — "for toml in
  sorted((harness.REPO_ROOT / \"devices\").glob(\"*.toml\"))" — Globs the live `devices/` without
  `_devices.py`'s `zz_test_*` filter; would pick up a live-tree fixture if one existed at that moment
  (low) · related: TEST.T13 · [H10]

## tests_scripts/test_bench_no_task_ended_completeness.py

- **TEST.N552** SUPPRESS · `tests_scripts/test_bench_no_task_ended_completeness.py:13,69` — "# noqa:
  E402" / "# noqa: FBT001" — E402 after `_TESTS_HARDWARE =` statement; FBT001 on a bool parametrize
  argument · [H10]

## tests_scripts/test_build_firmware.py

- **TEST.N553** LIMIT · `tests_scripts/test_build_firmware.py:90,124,149,160` —
  "@pytest.mark.parametrize(\"device\", [\"wozi\", \"dev\"])" — Staging-logic tests hardcode two devices
  instead of `_devices.DEVICE_NAMES`; the four other devices' staging is exercised only by the opt-in
  real build · related: CI.T07 · [H10]
- **TEST.N554** ASSUME · `tests_scripts/test_build_firmware.py:114-116` — "\"dev\" legitimately wires
  every driver in src/, so its unrelated set is empty" — Non-vacuity of the "no unrelated module staged"
  check rests on wozi alone (never wired to uart_link) · [H10]

## tests_scripts/test_build_website_sh.py

- **TEST.N555** INVAR · `tests_scripts/test_build_website_sh.py:93-110` — "copied into devices/ under a
  test-only name, removed again in `finally`" — Test writes
  `devices/zz_test_malformed_buildgen_fixture.toml` into the live tree; a KILLED run leaks it (reclaimed
  at next session start by conftest.py) · covered-by: TEST.T13 · [H10]

## tests_scripts/test_buildgen_definitions.py

- **TEST.N556** MIRROR · `tests_scripts/test_buildgen_definitions.py:19-20` — "BMP3XX_DEVICES =
  {\"dev\", \"wozi\"}" / "ISL29125_DEVICES = {\"dev\"}" — Hand-kept per-driver device sets must match
  `devices/*.toml` while the parametrization itself is discovered; a new device carrying BMP3xx/ISL29125
  fails until edited · related: GEN.T06 · [H10]

## tests_scripts/test_buildgen_twin_wiring.py

- **TEST.N557** LIMIT · `tests_scripts/test_buildgen_twin_wiring.py:26-40` — "import machine # type:
  ignore[import-not-found]" — Fixture removes digital_twin/ from sys.path afterwards but leaves
  `sys.modules["machine"]` (the twin fake) in the shared pytest process for every later test (low) ·
  [H10]
- **TEST.N558** SUPPRESS · `tests_scripts/test_buildgen_twin_wiring.py:36` — "# type:
  ignore[import-not-found] # only resolvable once digital_twin_dir is on sys.path" — Type-check
  suppression for a runtime path import · [H10]

## tests_scripts/test_buildgen_validate.py

- **TEST.N559** SUPPRESS · `tests_scripts/test_buildgen_validate.py:1203-1208` — "pytest.skip(\"an
  inline table can't be produced by this fixture writer\")" — The dict-valued `led_target` case of a
  parametrized test always skips (fixture-writer limitation), so an inline-table wiring value is never
  exercised here · [H10]

## tests_scripts/test_buildgen_version.py

- **TEST.N560** LIMIT · `tests_scripts/test_buildgen_version.py:34-38` — "before - timedelta(seconds=1)
  <= parsed <= after + timedelta(seconds=1)" — Wall-clock test with 1 s slack (second-truncated
  timestamp) (low) · related: TEST.T04 · [H10]

## tests_scripts/test_ceiling_probe.py

- **TEST.N561** LIMIT · `tests_scripts/test_ceiling_probe.py:58,99-101,115-126,146` — "time.sleep(0.1) #
  long enough for a refusal to land" — Many sub-second timing assumptions (0.05 s poll, 0.1 s dwell, 0.6
  s idle, 0.8 s drain timeout); CI-load sensitive · related: TEST.T04 · [H10]

## tests_scripts/test_coverage_runner.py

- **TEST.N562** SUPPRESS · `tests_scripts/test_coverage_runner.py:20-28` — "pytest.skip(f\"the
  --coverage variant is not built at {path}" — All runner tests skip when `build-settrace` is absent;
  they also transitively skip when `build-standard` is absent (fixture depends on `micropython_bin`)
  even though only settrace is used · related: TEST.T13 · [H10]
- **TEST.N563** MIRROR · `tests_scripts/test_coverage_runner.py:35` — "\"MICROPYPATH\":
  \"build/generated_src:src:tests:frozen_modules:.frozen\", \"TZ\": \"UTC\"" — Hand copy of test.sh's
  MICROPYPATH order and TZ pin · related: SCR.S07 · [H10]
- **TEST.N564** LIMIT · `tests_scripts/test_coverage_runner.py:77-86` — "the report describes src/ and
  digital_twin/ and nothing else" — Coverage traces src/ and digital_twin/ only; generated modules and
  staged/stripped copies are never traced · covered-by: TEST.S13 · [H10]

## tests_scripts/test_device_tomls.py

- **TEST.N565** MIRROR · `tests_scripts/test_device_tomls.py:66-67,441-486` — "reusable collision/shape
  checks ... Standalone functions so the negative-path tests below can exercise the same logic" —
  Duplicate implementation of GPIO/address/instance-name/wiring checks alongside buildgen.validate, with
  its own `_BASE_DOC` (a second base fixture besides `_toml_fixtures.base_doc()`; its `hotspot_password = "x"`
  would fail validate's 8..63 bound) — the two can drift · related: TEST.T08 · [H10]
- **TEST.N566** MIRROR · `tests_scripts/test_device_tomls.py:18-40` — "_DEVICES_WITH_BMP3XX = {\"wozi\",
  \"dev\"}" — Hand-kept facts: always-present drivers, BMP3xx on wozi/dev only, UART link and ISL29125
  on dev only, multi-instance/singleton/mandatory-infra/FRAM-wirable sets — parallel to
  buildgen/driver_registry and test_buildgen_definitions.py:19-20 · related: GEN.T06 · [H10]
- **TEST.N567** INVAR · `tests_scripts/test_device_tomls.py:247-269` — "Each scenario library's
  `_DEVICES` tuple stays hand-written deliberately: its ORDER assigns the twin's TCP port bases." —
  Enforces that
  `tests/test_{sensortask,digital_twin_construction,digital_twin_webserver_concurrency}_<device>.py` and
  three scenario `_DEVICES` tuples equal DEVICE_NAMES; does NOT cover other device-specific lists (e.g.
  js/app.js KNOWN_DEVICES, tests_js) · related: WEB.S22 · [H10]

## tests_scripts/test_digital_twin_boot_contiguity.py

- **TEST.N568** SUPPRESS · `tests_scripts/test_digital_twin_boot_contiguity.py:101-109` — "Skipped
  rather than failed when absent" — Whole file skips when `build/generated_src/` or the standard Unix
  port is absent (plain `pytest tests_scripts` without test.sh) · related: TEST.T13 · [H10]
- **TEST.N569** MIRROR · `tests_scripts/test_digital_twin_boot_contiguity.py:31-32,279-285` —
  "scripts/test.sh's own MICROPYPATH, heap size and interpreter, so this measures what the suite
  measures" — `_MICROPYPATH`/`_HEAPSIZE="16M"` pinned against test.sh by substring presence · [H10]
- **TEST.N570** LIMIT · `tests_scripts/test_digital_twin_boot_contiguity.py:34` — "_PROBE_TIMEOUT_S =
  120" — Per-probe subprocess timeout; up to 6 devices + 2 control arms boot sequentially in the pytest
  tier · related: TEST.T16 · [H10]

## tests_scripts/test_digital_twin_ci_suite_ceiling.py

- **TEST.N571** SUPPRESS · `tests_scripts/test_digital_twin_ci_suite_ceiling.py:30` — "# noqa: A002 -
  the base class's own signature" — Builtin-shadowing `format` parameter required by
  BaseHTTPRequestHandler · [H10]
- **TEST.N572** ASSUME · `tests_scripts/test_digital_twin_ci_suite_ceiling.py:113` — "assert
  all(\"RemoteDisconnected\" in r for r in results)" — Pins CPython http.client's exception name for a
  hang-up (host-Python-version dependent) (low) · [H10]

## tests_scripts/test_digital_twin_generated_boot.py

- **TEST.N573** MIRROR · `tests_scripts/test_digital_twin_generated_boot.py:153` — "env[\"MICROPYPATH\"]
  = f\"{tmp_path}:src:digital_twin:ext:.frozen\"" — Uses a different MICROPYPATH than test.sh
  (`build/generated_src:src:tests:frozen_modules:.frozen`) — intended, but a second resolution layout
  (low) · [H10]
- **TEST.N574** RISK · `tests_scripts/test_digital_twin_generated_boot.py:73-76` — "s.bind((_HOST, 0))"
  — `_free_port()` releases the port before the twin binds it (small TOCTOU window; accepted per
  CLAUDE.md's concurrency note) (low) · related: SCR.T06 · [H10]
- **TEST.N575** LIMIT · `tests_scripts/test_digital_twin_generated_boot.py:53-57` — "this is the one
  suite that would actually BOOT that deliberately malformed fixture" — Fixture discovery excludes files
  prefixed `malformed_` by name only · [H10]

## tests_scripts/test_heap_map_parser.py

- **TEST.N576** SUPPRESS · `tests_scripts/test_heap_map_parser.py:16` — "# noqa: E402 (the sys.path line
  above is what makes this importable)" — E402 after `REPO_ROOT = ...` statement · [H10]

## tests_scripts/test_http_client_ceiling_close.py

- **TEST.N577** SUPPRESS · `tests_scripts/test_http_client_ceiling_close.py:69` — "# type:
  ignore[arg-type]" — HTTPError constructed with `{}` headers · [H10]
- **TEST.N578** LIMIT · `tests_scripts/test_http_client_ceiling_close.py:80-84` — "import
  test_bus_concurrency_under_api_load as bench" — Host tier imports a real bench test module (and leaves
  tests_hardware/bench on sys.path) to test its retry wrapper; BACKLOG 30 discriminator · [H10]

## tests_scripts/test_lint_sh.py

- **TEST.N579** ASSUME · `tests_scripts/test_lint_sh.py:72` — "tests/ and digital_twin/ carry ~157 of
  these deliberately - that IS the mocking mechanism" — Dated approximate count of `type: ignore[method-assign]`
  suppressions outside src/ · related: DOC.T08 · [H10]

## tests_scripts/test_live_twin_ceiling_parser.py

- **TEST.N580** LIMIT · `tests_scripts/test_live_twin_ceiling_parser.py:20-25` — "assert node is not
  None, \"node is not on PATH - the browser tier this pins cannot run without it either\"" — Hard
  dependency: the pytest tier FAILS (does not skip) without `node` on PATH · related: SCR.T13 · [H10]

## tests_scripts/test_request_timeout_ceiling.py

- **TEST.N581** SUPPRESS · `tests_scripts/test_request_timeout_ceiling.py:199-204` —
  "warnings.simplefilter(\"ignore\", pytest.PytestUnknownMarkWarning)" — Loads a real bench test module
  into the host process with unknown-marker warnings silenced · [H10]
- **TEST.N582** LIMIT · `tests_scripts/test_request_timeout_ceiling.py:211-238,280-291` — "window_s:
  float = 0.6" — Loopback thread timing (0.6 s windows, 2 ms sampling, 0.2 s sleeps) — CI-load sensitive
  · related: TEST.T04 · [H10]

## tests_scripts/test_test_sh.py

- **TEST.N583** LIMIT · `tests_scripts/test_test_sh.py:56-72` — "text = (repo_root / \"tests_scripts\" /
  \"test_build_website_sh.py\").read_text()" — The reserved-prefix guard inspects only
  test_build_website_sh.py; a live-tree writer added in any other file is not checked · related:
  TEST.T13 · [H10]
- **TEST.N584** SUPPRESS · `tests_scripts/test_test_sh.py:405-408` — "pytest.skip(f\"the --coverage
  variant is not built at {settrace_bin}" — Settrace-variant self-report test skips without that binary
  · [H10]

## tests_scripts/test_threshold_runner.py

- **TEST.N585** INVAR · `tests_scripts/test_threshold_runner.py:1-3` — "a runner that quietly stopped
  applying the threshold would leave CI's unit-tests-gc-threshold job just as green while measuring the
  (e) stage twice" — Pins tests/_threshold_runner.py: applies the threshold before the file imports,
  runs `microtest.run()` under `__main__`, propagates SystemExit only · related: SCR.T01 · [H10]

## vitest.config.js

- **TEST.N586** ASSUME · `vitest.config.js:29-31` — "covers the longest explicit wait (5000ms,
  render.test.js) with margin." — the 20000 ms backstop is sized against one test's wait
  (tests_js/render.test.js:665); a longer wait elsewhere would need it re-sized (low) · related:
  TEST.T16 · [H11]

## tests_js/_live_twin_command.js

- **TEST.N587** WORKAROUND · `tests_js/_live_twin_command.js:1-3` — "Vitest's own browser-mode `page`
  has no API for navigating to an external origin - vitest-dev/vitest#7875" — live tests drive a raw
  Playwright page through the Commands API; removal trigger: none stated (upstream issue) · [H11] ⟨quote
  not matched at the anchor⟩
- **TEST.N588** MIRROR · `tests_js/_live_twin_command.js:12-13 (and _live_matrix_command.js:15-16)` —
  "\"ports\", \"unix\", \"build-standard\", \"micropython\"" — hard-coded Unix-port build directory must
  match toolchain/setup_toolchain.py's `build-standard` (the non-settrace binary, CLAUDE.md) (low) ·
  [H11]
- **TEST.N589** ASSUME · `tests_js/_live_twin_command.js:14-17` — "package.json's own
  \"pretest\"/\"pretest:coverage\" hooks generate it fresh there, via buildgen, before this spawns." — a
  bare `vitest run` (no npm hook) boots whatever stale or missing build/generated_src exists · related:
  SCR.T01 · [H11]
- **TEST.N590** INVAR · `tests_js/_live_twin_command.js:19-22` — "Clear of every fixed port and band
  tests/, tests_scripts/, scripts/ and digital_twin/ bind (the full map is in SPECIFICATION.md Part
  E.1)" — fixed port 19481 (19482 for the matrix) kept disjoint by convention only · covered-by:
  TEST.T14 · [H11]
- **TEST.N591** WORKAROUND · `tests_js/_live_twin_command.js:75-78` — "stdout ignored rather than piped:
  an unconsumed pipe keeps Node's event loop alive" — twin stdout is discarded, so nothing scans it for
  `MemoryError`/`memory allocation failed` · covered-by: TEST.T18 · [H11]
- **TEST.N592** SUPPRESS · `tests_js/_live_twin_command.js:81-84` — "proc.on(\"error\", () => { /* no-op
  by design, per the comment above */ });" — spawn errors swallowed; failure surfaces only via the
  readiness timeout · [H11]
- **TEST.N593** MIRROR · `tests_js/_live_twin_command.js:93-95` — "run_generic_integration.py's own
  graceful-shutdown path (FRAM/SCD30 flush) only runs on KeyboardInterrupt ... same reasoning as
  scripts/_digital_twin_ci_suite.py's own _shutdown()" — SIGINT-based shutdown contract shared with the
  twin CI suite · [H11]
- **TEST.N594** WORKAROUND · `tests_js/_live_twin_command.js:97-99` — "a pending timer keeps Node's
  event loop alive - which showed up as Vitest's \"something prevents Vite server from exiting\"" — kill
  timer cleared explicitly · [H11]
- **TEST.N595** ASSUME · `tests_js/_live_twin_command.js:119-121` — "Delegated to buildgen rather than
  re-parsed here ... package.json's \"pretest\" hook already needs uv on PATH." — live tests shell out
  to `uv run python` for buildgen's max_connections · covered-by: GEN.T15 · [H11]
- **TEST.N596** LIMIT · `tests_js/_live_twin_command.js:144-149, 225-230` — "skipped: true, reason:
  `MicroPython Unix port not built at ...`" — live tests return a skip result that the calling test
  turns into a pass · covered-by: TEST.S19 · [H11]
- **TEST.N597** RISK · `tests_js/_live_twin_command.js:151-154, 231` — "config/ is the one thing that
  still persists to a fixed path by default (run_generic_integration.py exposes no --cfg-path flag)" —
  deletes the repo-level digital_twin/config before each live run · covered-by: SCR.S09 · [H11]
- **TEST.N598** LIMIT · `tests_js/_live_twin_command.js:218-220 vs :233-235` — "the tier exercising the
  connection ceiling from a real browser" vs "Half the ceiling, so it is never exceeded" — the
  concurrent-tab test never reaches `max_connections`; it rests on the stated assumption that a tab
  holds one slot, two while releasing · related: WEB.T16 · [H11]
- **TEST.N599** SUPPRESS · `tests_js/_live_twin_command.js:38,46,197,200,247` — "//
  eslint-disable-next-line no-await-in-loop -- deliberate sequential polling" — 5 no-await-in-loop
  disables, each with a reason · [H11]
- **TEST.N600** SUPPRESS · `tests_js/_live_twin_command.js:43-45, 212, 260` — "} catch { // Not up yet -
  keep polling. }" / "catch(() => { /* best-effort teardown ... */ })" — swallowed exceptions with a
  comment (readiness poll, page teardown) · [H11]

## tests_js/_live_matrix_command.js

- **TEST.N601** ASSUME · `tests_js/_live_matrix_command.js:9-12` — "Reused (not hand-duplicated) so this
  module knows the *exact* expected caption text" — expected captions are computed with the same
  `formatFieldValue()` under test, so a formatting defect cannot fail the live matrix · related:
  TEST.T17 · [H11]
- **TEST.N602** MIRROR · `tests_js/_live_matrix_command.js:14-116 vs tests_js/_live_twin_command.js:11-117`
  — "Same reasoning as tests_js/_live_twin_command.js's own stdio choice" —
  TOOLCHAIN_DIR/MICROPYTHON_BIN/MICROPYPATH/HOST, sleep, waitUntilServing, spawnTwin, stopTwin are
  copy-pasted between the two harnesses · related: TEST.T08 · [H11]
- **TEST.N603** RISK · `tests_js/_live_matrix_command.js:22-23, 136` — "this harness's twin runs
  alongside that file's (19481) in one `npm test` run." — both harnesses `rmSync` the same
  digital_twin/config; if the two live files run concurrently one can delete the other twin's config
  mid-run · related: SCR.S09 · [H11]
- **TEST.N604** ASSUME · `tests_js/_live_matrix_command.js:172-174` — "Vitest dispatches Commands API
  calls strictly sequentially from one file's await chain, so the race the rule guards cannot happen." —
  justification for four `require-atomic-updates` disables (:159,164,178,183) · [H11]
- **TEST.N605** SUPPRESS · `tests_js/_live_matrix_command.js:159,164,178,183` — "//
  eslint-disable-next-line require-atomic-updates -- see comment above" — 4 disables on module-level
  mutable state · [H11]
- **TEST.N606** SUPPRESS · `tests_js/_live_matrix_command.js:43,51,201,203,239,244,264,269` — "//
  eslint-disable-next-line no-await-in-loop" — 8 no-await-in-loop disables with reasons · [H11]
- **TEST.N607** SUPPRESS · `tests_js/_live_matrix_command.js:48-50, 158, 177` — "} catch { // Not up yet
  - keep polling. }" — swallowed exceptions (readiness poll, best-effort page close) · [H11]
- **TEST.N608** LIMIT · `tests_js/_live_matrix_command.js:202-204` — "out[p] = await res.json();" —
  baseline GETs don't check HTTP status or envelope before use (low) · [H11]
- **TEST.N609** ASSUME · `tests_js/_live_matrix_command.js:218-221` — "js/main.js's selectSection()
  always tears down and rebuilds fresh regardless" — remount proof depends on this main.js behaviour ·
  [H11]
- **TEST.N610** LIMIT · `tests_js/_live_matrix_command.js:307-308` — "composite/readonly/dispatch-only
  fields aren't driven through this generic matrix (see SPECIFICATION.md Part H.7)" — lightCmdLED,
  SystemCmd, PauseTime, ResetErrors have no live-UI coverage · related: WEB.T10 · [H11]
- **TEST.N611** ASSUME · `tests_js/_live_matrix_command.js:320-322` — "just worth a short event-loop
  beat." — fixed `sleep(50)` before reading toggle/select state (low) · related: TEST.T04 · [H11]
- **TEST.N612** MIRROR · `tests_js/_live_matrix_command.js:356` — "\"Nothing to submit - no fields were
  changed.\"" — literal UI string duplicated from js/render.js:207 (also
  live-backend-put-matrix.test.js:166) (low) · [H11]

## tests_js/_put_field_cases.js

- **TEST.N613** ASSUME · `tests_js/_put_field_cases.js:11-12` — "covered by dedicated tests in
  mock-server.test.js and render.test.js" — dispatch-only keys are covered by the mock tier only, never
  by the live twin · related: WEB.T10 · [H11]
- **TEST.N614** ASSUME · `tests_js/_put_field_cases.js:55-56` — "measurements has no PUT; status's only
  field (ResetErrors) is dispatch-only" — section list hard-coded; a new writable status field would be
  silently skipped (low) · [H11]

## tests_js/vitest-commands.d.ts

- **TEST.N615** MIRROR · `tests_js/vitest-commands.d.ts:16-17` — "These return types are kept in sync by
  hand with each file's own `@returns` JSDoc" — command signatures duplicated by hand from the two
  harness files · [H11] ⟨quote not matched at the anchor⟩

## tests_js/live-backend.test.js

- **TEST.N616** LIMIT · `tests_js/live-backend.test.js:1-3, 13-16, 41-44` — "Skips itself with a clear
  message if the MicroPython toolchain/frozen website aren't built yet, rather than failing the suite."
  — skip-and-pass via `console.warn` + `return` · covered-by: TEST.S19 · [H11] ⟨quote not matched at the
  anchor⟩
- **TEST.N617** ASSUME · `tests_js/live-backend.test.js:20-23` — "\"Valid\" or \"Unchanged\" both mean
  the backend accepted the write" — tolerance for either result · [H11]
- **TEST.N618** RISK · `tests_js/live-backend.test.js:31-33` — "Known harmless quirk: this file prints
  \"close timed out after 10000ms\" ... appears to miss Vitest's fast path" — accepted teardown warning;
  cause stated as "appears to", unverified · [H11]
- **TEST.N619** LIMIT · `tests_js/live-backend.test.js:46-48` — "The tab count is derived from the
  build's own max_connections, so this bites harder the moment that ceiling is raised." — tabs =
  floor(ceiling/2) (_live_twin_command.js:235), so the ceiling itself is never exercised · related:
  WEB.T16 · [H11]

## tests_js/live-backend-put-matrix.test.js

- **TEST.N620** LIMIT · `tests_js/live-backend-put-matrix.test.js:58` — "collectPutFieldCases(\"wozi\",
  ..." — live PUT matrix covers wozi only · covered-by: TEST.S19 · [H11]
- **TEST.N621** SUPPRESS · `tests_js/live-backend-put-matrix.test.js:65-66` — "it.skip(`live-backend PUT matrix (skipped: ${boot.reason})`"
  — the whole matrix collapses to one skipped placeholder without the toolchain · covered-by: TEST.S19 ·
  [H11]
- **TEST.N622** LIMIT · `tests_js/live-backend-put-matrix.test.js:252-253` — "minLength === 1's own
  \"too short\" probe is the empty string ... so only minLength 2+ has a real probe" — too-short
  rejection untested for minLength-1 fields · [H11]
- **TEST.N623** WORKAROUND · `tests_js/live-backend-put-matrix.test.js:271-273` — "vitest derives a
  screenshot filename - and NTP_Host's maxLength 1024 made that ENAMETOOLONG, wedging a run" — tests
  parametrised over lengths to keep names short; removal trigger: none stated · [H11]
- **TEST.N624** LIMIT · `tests_js/live-backend-put-matrix.test.js:283-299` — "flipping to the opposite
  state renders Valid" / "selecting option %s renders Valid" — no live rejection probes for toggle/enum
  (wrong type, unknown option) (low) · related: WEB.T10 · [H11]

## tests_js/mock-server-put-matrix.test.js

- **TEST.N625** DRIFT · `tests_js/mock-server-put-matrix.test.js:18-21` — "This matches none of dev's
  real groups today ... stays for a future dev-unique sensor (owner, 2026-09-08)." — ISL29125 in
  DEV_UNIQUE_GROUPS is a real dev-only group now; SHTC3/MPRLS name no driver in src/ · [H11]
- **TEST.N626** MIRROR · `tests_js/mock-server-put-matrix.test.js:23-26` — "const
  GET_READBACK_QUIRK_FIELDS = new Set([\"ForceCalRef\", \"ContMeas\", \"SGPResetVOC\", \"ISLCalibrate\",
  \"PW\"]);" — part of the disagreeing special-field lists (see tests_js/_put_field_cases.js) · [H11]
- **TEST.N627** DRIFT · `tests_js/mock-server-put-matrix.test.js:153-154` — "e.g. FiltCoeff's min 0 and
  special -1" — dev's ISL29125 FiltCoeff is min -1.0 with special -1.0; BMP3XX FiltCoeff is an enum
  (low) · [H11]
- **TEST.N628** ASSUME · `tests_js/mock-server-put-matrix.test.js:269-271` — "Every currently-declared
  numeric enum's own real options are whole numbers" — still true (BMP3XX, ISL29125
  Resolution/Range/IrCompOffset) but unchecked (low) · [H11]

## tests_js/mock-server.test.js

- **TEST.N629** SUPPRESS · `tests_js/mock-server.test.js:462,464` — "// eslint-disable-next-line
  no-await-in-loop -- see the comment above" — 2 disables · [H11]

## tests_js/render.test.js

- **TEST.N630** LIMIT · `tests_js/render.test.js:5-6` — "the mock server's fetch has randomized latency
  (js/mock-server.js)" — render tests poll against a nondeterministic mock · covered-by: TEST.T14 ·
  [H11]
- **TEST.N631** SUPPRESS · `tests_js/render.test.js:17-18` — "// eslint-disable-next-line
  no-await-in-loop" — 1 disable (reason on the line above) · [H11]
- **TEST.N632** LIMIT · `tests_js/render.test.js:85-87, 469-471` — "Deliberately not the real SCD30 key
  \"ContMeas\": mock-server.js special-cases that exact name" — the mock's behaviour is keyed on literal
  field names, so fixtures must avoid them; also cites "Part H.7" where the quirks note is H.4 (low) ·
  [H11] ⟨quote not matched at the anchor⟩
- **TEST.N633** ASSUME · `tests_js/render.test.js:403-405` — "switching earlier would hang waitFor's own
  real-timer polling loop." — fake-timer ordering constraint (low) · related: TEST.T04 · [H11]
- **TEST.N634** ASSUME · `tests_js/render.test.js:883-885` — "No real definitions file nests a readonly
  field inside a submit:true group in a \"live\" section today" — path exercised by a synthetic fixture
  only · [H11]

## tests_js/definitions.test.js

- **TEST.N635** MIRROR · `tests_js/definitions.test.js:295` — "await vi.advanceTimersByTimeAsync(15000);
  // fetchWithTimeout()'s own DEFAULT_TIMEOUT_MS" — literal copy of js/poll-manager.js:8 (low) · [H11]

## tests_js/definitions-mockdata-coverage.test.js

- **TEST.N636** DRIFT · `tests_js/definitions-mockdata-coverage.test.js:14-16` — "Mirrors js/render.js's
  own groupValuesFrom(), duplicated deliberately ... If the two ever disagree this test goes red" — a
  private copy does not follow render.js changes, so a disagreement would not turn this test red (low) ·
  related: TEST.T08 · [H11]
- **TEST.N637** LIMIT · `tests_js/definitions-mockdata-coverage.test.js:73-74` — "Only readonly fields:
  a writable one legitimately falls back to defaultValue" — writable fields' presence in mockdata is not
  checked · related: WEB.T15 · [H11]

## SPECIFICATION.md Part A.4 (Architecture — deep reference, 148-285)

- **TEST.N638** DRIFT · `SPECIFICATION.md:230-236` — "Its `WDT()`-site half is now permanently vacuous"
  — A permanently vacuous half remains in `tests/test_reset_call_site_invariant.py`; invariant moved to
  `tests_scripts/test_buildgen_generate.py::test_real_device_constructs_watchdog_exactly_once`. ·
  covered-by: TEST.S17 · [H12]

## SPECIFICATION.md Part A.9 (The frozen-HTML pipeline, 627-653)

- **TEST.N639** LIMIT · `SPECIFICATION.md:653-656` — "left one case the real site has no file for, the
  binary `application/octet-stream` fallback, which Section G of `tests/test_asy_webserver_service.py`
  now pins on its synthetic fixture" — One serving path covered only synthetically. · [H12]

## SPECIFICATION.md Part B intro, B.1-B.3 (688-753)

- **TEST.N640** ASSUME · `SPECIFICATION.md:728-734` — "The flag is not inert when unused (measured
  2026-09-18) ... inflating every allocation figure 4-5x ... (`test_sensortask_wozi.py` 24.6s → 9.3s)" —
  Dated single measurements; cite the git-only HEAP_FRAGMENTATION archive §1.2. · related: DOC.S04 ·
  [H12]

## SPECIFICATION.md Part C.8 (Concurrency & locking model, 2016-2188)

- **TEST.N641** INVAR · `SPECIFICATION.md:2065-2068` — "every promoted I2C/SPI device gets same-device
  read-vs-write concurrency coverage, cross-device interleaving coverage (if sharing a bus), and an
  address/command sweep, across as many of four tiers as apply" — Standing owner rule; review-enforced.
  · covered-by: SENS.T10 · [H12]
- **TEST.N642** SETTLED · `SPECIFICATION.md:2070-2084` — "Mock/unit, two distinct collections, by design
  (project owner's own reframing, 2026-09-15)" — Sensor-specific hazards in driver files; generic in
  `test_bus_hazard_multi_device.py`, never retired. · [H12]
- **TEST.N643** SETTLED · `SPECIFICATION.md:2090-2096` — "The two are deliberately allowed to overlap in
  what they prove (layered coverage, not redundancy to prune)" — Overlap deliberate. · [H12]
- **TEST.N644** INVAR · `SPECIFICATION.md:2122-2124` — "`build_bus_occupants()`/the address-sweep
  scenario both fail loud (`KeyError`) for a driver with none" — Enforced (adapters: scd30, sgp40,
  isl29125, bmp3xx). · [H12]
- **TEST.N645** SETTLED · `SPECIFICATION.md:2171-2178` — "`test_bus_hazard_multi_device.py` is never
  retired (project owner's own reframing, 2026-09-15, superseding an earlier plan" — Permanent file. ·
  [H12]
- **TEST.N646** ASSUME · `SPECIFICATION.md:2192-2196` — "FRAM sits alone on its own dedicated SPI bus on
  every real device ... proven once, against one real assembled object graph (wozi)" — Topology
  assumption justifying wozi-only coverage. · [H12]

## SPECIFICATION.md Part C.9.1 (Read-trigger timer stagger, 2211-2298)

- **TEST.N647** LIMIT · `SPECIFICATION.md:2294-2298` — "no new test was added for this WP, since it
  verifies and documents an existing, already-tested mechanism" — Proof has no test reading the real
  period. · covered-by: TEST.S06 · [H12]

## SPECIFICATION.md Part C.11 / C.11.1 (Design decisions; conformance probe, 2310-2353)

- **TEST.N648** TODO · `SPECIFICATION.md:2354-2357` — "The ISL29125 is the first driver with one ...
  Build one for every new bus-facing chip." — No probe for SCD30/SGP40/BMP3xx/FRAM. · covered-by:
  TEST.S20 · [H12]

## SPECIFICATION.md Part D (src/ Production-Quality Checklist, 2576-2728)

- **TEST.N649** LIMIT · `SPECIFICATION.md:2628-2629` — "Verified via design discipline and reading — no
  CI gate for \"ran a simulated year.\"" — Long-uptime stability untested (cf. ticks wraparound
  XCUT.T25). · related: XCUT.T25 · [H12]
- **TEST.N650** INVAR · `SPECIFICATION.md:2707-2709` — "a valid typical input against a sanity bound,
  not an exact reference value" — Test-oracle policy (weak oracles by design). · related: ALGO.T07 ·
  [H12]
- **TEST.N651** INVAR · `SPECIFICATION.md:2711-2713` — "module-level tests mocking only the raw bus
  transaction aren't enough — add integration tests driving the same scenarios through the actual real
  chain" — Test obligation. · [H12]

## SPECIFICATION.md Part E intro, E.1 (2732-2788)

- **TEST.N652** MIRROR · `SPECIFICATION.md:2754-2755` — "cross-file invariants that can only be checked
  by reading real source text (`scripts/test.sh`'s own step ordering; the `outer_cap_s` ceiling's
  mirrors, Part H.4)" — Hand mirrors guarded by source-reading pytest tests. · related: GEN.T06 · [H12]
- **TEST.N653** INVAR · `SPECIFICATION.md:2775-2789` — "Two per-file resources must stay disjoint ... A
  new test file that binds a socket claims an unused base below 32768 — never a neighbour's, never
  inside the ephemeral range." — Review-only; found violated before (2026-09-17) and again per seed. ·
  covered-by: TEST.S21 · [H12]
- **TEST.N654** PLATFORM · `SPECIFICATION.md:2779-2782` — "inside the OS ephemeral range (32768-60999)
  ... For UDP both modes are silent rather than `EADDRINUSE`" — Host-Linux default range assumed. ·
  [H12]

## SPECIFICATION.md Part E.2 / E.2.1 (Test framework; per-device libraries, 2790-2826)

- **TEST.N655** LIMIT · `SPECIFICATION.md:2800-2802` — "`microtest.py` is a minimal collector/runner ...
  report PASS/FAIL, exit non-zero on failure" — Runner-level vacuity classes. · covered-by: TEST.S23 ·
  [H12]
- **TEST.N656** SETTLED · `SPECIFICATION.md:2817-2825` — "Why the split exists is memory ... a fix at
  the root, not a per-file heap override or a `gc.collect()` prop" — Measured 2026-09-17 (~29 → ~11
  builds). · [H12]
- **TEST.N657** LIMIT · `SPECIFICATION.md:2831-2834` — "keeps its heavier tests wozi-only ... a ×6
  parametrization would buy nothing" — Deliberate single-device coverage. · [H12]

## SPECIFICATION.md Part E.3 / E.3.1 (Running; heap and timeouts, 2828-2921)

- **TEST.N658** SETTLED · `SPECIFICATION.md:2878-2881` — "`-X heapsize=16M` ... must never be raised as
  a fix" — Do-not-reopen (CLAUDE.md). · [H12]
- **TEST.N659** ASSUME · `SPECIFICATION.md:2893-2898` — "reproducibly misses its own 9-second real-clock
  budget at 8M ... So 16M is a measured floor across every file" — Heap floor tied to a timing-sensitive
  test; dated measurement. · related: TEST.T04 · [H12]

## SPECIFICATION.md Part E.4 (Mock at the raw bus-transaction level, 2923-2949)

- **TEST.N660** ASSUME · `SPECIFICATION.md:2940-2943` — "Two Protocol-level failure scenarios
  (`get_chunk()` raising) have no real-class equivalent anymore (the real class is audited never to
  raise there)" — Tests of an unreachable contract via a local fake. · [H12]
- **TEST.N661** INVAR · `SPECIFICATION.md:2947-2957` — "`_StarvedAlloc` ... must be armed and one-shot
  ... must restore the global in `__exit__` ... Reach for it only where a real `MemoryError` is
  genuinely unreachable" — Sanctioned allocator mock rules; review-only. · related: TEST.T06 · [H12]

## SPECIFICATION.md Part E.5 / E.5.1-E.5.3 (Coverage, 2951-3088)

- **TEST.N662** PLATFORM · `SPECIFICATION.md:2982-2990` — "The rule is the leading underscore, verified
  at source (`py/parse.c`, the `MICROPY_COMP_CONST` fold) ... A bare `while True:` header never fires
  its own trace event" — Tracer false-negative patterns; "all 58" constants a dated count. · covered-by:
  TEST.T09 · [H12]
- **TEST.N663** SETTLED · `SPECIFICATION.md:2992-3010` — "left as documented dead code rather than
  chased for a coverage number ... confirmed intentional by the project owner" — Unreachable-branch
  register (print_log `get_log()` sentinel owner-confirmed; UART six re-checks; UART driver `except MemoryError`).
  · [H12]
- **TEST.N664** ASSUME · `SPECIFICATION.md:3012-3025` — "Four more of the same class, enumerated on
  2026-09-22 ... `voc_algorithm.py`'s `_FIX16_OVERFLOW` return ... unreachable ... 31 genuinely
  uncovered lines across 8 files, all of which now have tests" — Dated unreachability claims (VOC
  overflow disputed vs C int32 semantics). · related: ALGO.S01 · [H12]
- **TEST.N665** LIMIT · `SPECIFICATION.md:3069-3071` — "`--coverage`'s own figures stay inflated,
  inherently ... never as an allocation measurement" — Coverage-mode allocations meaningless. · [H12]

## SPECIFICATION.md Part E.6 / E.6.1-E.6.6 (Shared behaviours, real-hardware tier, 3090-3225)

- **TEST.N666** SETTLED · `SPECIFICATION.md:3100-3104` — "don't force further sharing onto genuinely
  backend-specific coverage" — Test-sharing scope decision. · [H12]
- **TEST.N667** INVAR · `SPECIFICATION.md:3152-3153` — "Documentation discipline (each shared function's
  docstring states applicable/N/A backends), not an automated check." — Review-only. · [H12]
- **TEST.N668** ASSUME · `SPECIFICATION.md:3181-3184` — "FRAM (166 mock vs. 18 twin tests) ... one real
  cluster (Sensortask: 4 near-identical ... pairs)" — Dated counts. · covered-by: TEST.T15 · [H12]

## SPECIFICATION.md Part E.7 (Twin soak wall clock measures GC timing, 3229-3269)

- **TEST.N669** INVAR · `SPECIFICATION.md:3270-3273` — "A soak's own timing budget is a liveness
  backstop, not a performance assertion, so it belongs above the whole observed range" — Test-design
  rule. · related: TEST.T04 · [H12]

## SPECIFICATION.md Part E.8 (Measurement traps, 3271-3362)

- **TEST.N670** INVAR · `SPECIFICATION.md:3284-3295` — "An absolute heap-delta bound is host-dependent;
  a leak is a rate." — Absolute heap bounds still exist per seed. · covered-by: TEST.S12 · [H12]
- **TEST.N671** ASSUME · `SPECIFICATION.md:3288-3289` — "`< 6.0 B/transaction` and `< 16.0 B/failure`,
  against a real retained frame's 13+ B/transaction and an injected 16 B/transaction leak's measured
  636" — Measured thresholds in `tests/test_uart_comm_hazard.py`. · [H12]
- **TEST.N672** LIMIT · `SPECIFICATION.md:3314-3316` — "Cross-test contamination is real. One process,
  one task queue, and no parent/child tracking in MicroPython asyncio" — Per-test numbers unreliable
  without isolation. · covered-by: TEST.T07 · [H12]
- **TEST.N673** LIMIT · `SPECIFICATION.md:3347-3353` — "regressing each of `asy_uart_driver.py`'s seven
  read paths in turn ... four failed a named test, three passed silently" — Guard-is-blind finding
  (2026-09-12). · covered-by: TEST.T02 · [H12]
- **TEST.N674** INVAR · `SPECIFICATION.md:3355-3365` — "Run it as a scripted sweep, not by hand ...
  restore the file in a `finally` regardless" — Mutation-sweep method; no committed sweep script named.
  · related: TEST.T02 · [H12]

## SPECIFICATION.md Part E.9 (Driver/DUT process separation, 3364-3421)

- **TEST.N675** INVAR · `SPECIFICATION.md:3404-3409` — "A fix under this rule must come out strictly
  more capable of catching the real test case, never merely lighter on the DUT" — Rule. · [H12]
- **TEST.N676** RISK · `SPECIFICATION.md:3423-3426` — "a real leak reproduces past tolerance on both
  independent boots, transient noise essentially never does" — Retry can mask an intermittent real leak;
  accepted. · [H12]

## SPECIFICATION.md Part F.1 — Core platform facts

- **TEST.N677** LIMIT · `SPECIFICATION.md:3530-3532` — "Unix-port rig has a much larger period (`2**62`,
  64-bit) and cannot empirically exercise the real `2**30` rollover — verified by shared,
  period-parametric code identity instead" — Rollover coverage is by argument, not by test. · related:
  XCUT.T25, TWIN.T09 · [H13]
- **TEST.N678** PLATFORM · `SPECIFICATION.md:3528-3530` — "`time` module attributes cannot be
  monkeypatched (a builtin C module's globals dict is fixed)" — Test-design constraint (synthetic ticks
  via `ticks_add()`/`ticks_diff()`). · [H13]
- **TEST.N679** INVAR · `SPECIFICATION.md:3534-3536` — "a test starting a background task must keep an
  explicit reference and cancel it in its own `finally`" — Test-discipline rule, convention only. ·
  [H13]
- **TEST.N680** INVAR · `SPECIFICATION.md:3570-3571` — "a test of emitted JSON checks it with
  `tests/_strict_json.py`" — Test convention; nothing named enforces every emitted-JSON test uses it. ·
  [H13]

## SPECIFICATION.md Part F.5.1 — I2C/SPI deinit no-ops

- **TEST.N681** MIRROR · `SPECIFICATION.md:3714-3716` — "`tests/machine.py` and
  `digital_twin/machine.py` model the no-op faithfully" — Fake↔real obligation in two fakes for I2C/SPI
  `deinit()`. · related: TEST.T19, TEST.T05 · [H13]

## SPECIFICATION.md Part F.5.8 — UART read() blocks the loop

- **TEST.N682** LIMIT · `SPECIFICATION.md:3967-3971` — "UART fakes return `min(nbytes, len(rx_queue))`
  and never wait — they model a non-blocking read the real peripheral does not provide" — Fake fidelity
  gap; the defect was invisible below the bench tier. · related: TEST.T19 · [H13]
- **TEST.N683** MIRROR · `SPECIFICATION.md:3972-3977` — "`UART.would_have_blocked_bytes` ... the two
  models are held to identical counting by `tests/_uart_link_contract.py`" — `tests/machine.py` ↔
  `digital_twin/machine.py` stall counting, enforced by the shared contract. · related: TEST.T05 · [H13]

## SPECIFICATION.md Part H.7 — Digital twin integration / connection ceiling

- **TEST.N684** LIMIT · `SPECIFICATION.md:4531-4540` — "CI/local test hooks build the real production
  `wozi` website automatically ... `live-backend-put-matrix.test.js` extends this to every real writable
  field in `wozi.json`" — Browser/live tiers cover wozi only. · covered-by: TEST.S19, WEB.T12 · [H13]
- **TEST.N685** INVAR · `SPECIFICATION.md:4618-4621` — "every admitted connection must come back with a
  complete, correct, parseable response ... A test that only counts `200`s passes on a truncated body" —
  Test-oracle rule across tiers. · related: TEST.T01 · [H13]

## SPECIFICATION.md Part H.7 — Cross-browser coverage

- **TEST.N686** LIMIT · `SPECIFICATION.md:4678` — "Vitest's browser mode only automates Chromium-family
  browsers via Playwright." — Non-Chromium engines covered only by the narrow smoke script. · related:
  WEB.T12 · [H13]
- **TEST.N687** SETTLED · `SPECIFICATION.md:4685-4688` — "Deliberately narrow scope (not a second
  exhaustive PUT matrix ...), and single-session" — Cross-browser smoke scope decision. · [H13]

## SPECIFICATION.md Part H.8.1 — JSDoc typedef imports

- **TEST.N688** INVAR · `SPECIFICATION.md:4770-4772` — "poll for the exact expected rendered text, never
  a fixed sleep" — JS test-timing rule, review-only. · related: TEST.T14 · [H13]

## SPECIFICATION.md Part I.3 — Bounded response assembly

- **TEST.N689** LIMIT · `SPECIFICATION.md:4972-4976` — "added after confirming the original hammer tests
  would still pass even with a fix fully reverted" — Unix-port heap cannot reproduce contiguity failure;
  tests assert stream shape instead. · related: TEST.T01, TWIN.T06 · [H13]

## SPECIFICATION.md Part I.4 — Multi-stage memory-error scheme, (a)-(e)

- **TEST.N690** INVAR · `SPECIFICATION.md:5013-5022` — "The whole suite — digital twin and real hardware
  alike ... must run to completion with `gc.threshold(-1)` ... with no nonstandard `gc` settings or
  added `gc.collect()` calls" — Stage (e) bar; the plan records `gc.collect()` props present in tests. ·
  covered-by: TEST.S11, TEST.T03 · [H13]
- **TEST.N691** INVAR · `SPECIFICATION.md:5038-5046` — "There are **four** such gates ... All four now
  match `MemoryError` *or* `memory allocation failed` ... pinned by
  `tests_scripts/test_memory_error_gate_agreement.py` ... Don't narrow any of them back" — Enforced
  agreement; do-not-narrow marker. · related: TEST.T18 · [H13]
- **TEST.N692** ASSUME · `SPECIFICATION.md:5049-5053` — "measured over a full 85-file run at
  `gc.threshold(-1)` ... all 26 of the suite's own deliberate injections ... 25 read `\"simulated allocation failure\"`
  (11 ... 14 ...) and one reads `\"starved\"`" — Dated counts (85 files is stale vs 87). · covered-by:
  DOC.S08 · [H13]
- **TEST.N693** INVAR · `SPECIFICATION.md:5053-5056` —
  "`tests_scripts/test_memory_error_gate_agreement.py` walks `tests/` and `digital_twin/` with `ast` for
  every injected exception message and fails one that borrows the interpreter's own words" — Enforced
  for tests/ and digital_twin/ only (not tests_hardware/device_scripts or tests_js). · related: TEST.T18
  · [H13]

## SPECIFICATION.md Part I.4 — (f), (f.1), (g)

- **TEST.N694** INVAR · `SPECIFICATION.md:5081-5084` — "`GC_THRESHOLD=32768 scripts/test.sh` (E.3) runs
  every file through `tests/_threshold_runner.py` ... CI's own `unit-tests-gc-threshold` job does the
  same" — Enforced second stage; the plan notes twin launches run only at 32768, never at -1. · related:
  TEST.T18 · [H13]

## SPECIFICATION.md Part J.7 — Loopback testing model

- **TEST.N695** MIRROR · `SPECIFICATION.md:5574-5578` — "They are held to one shared set of assertions
  in `tests/_uart_link_contract.py` — the two may differ in fidelity, never in semantics" — Mock↔twin
  UART link mirror, test-enforced. · related: TEST.T05 · [H13]
- **TEST.N696** LIMIT · `SPECIFICATION.md:5580-5586` — "**The mock tier's `timeout` is a scheduling
  budget, not a wire budget** ... `scripts/test.sh` deliberately oversubscribes the runner (4× the core
  count" — Mock-tier timing assertions depend on host scheduling. · related: TEST.T04 · [H13]
- **TEST.N697** ASSUME · `SPECIFICATION.md:5593-5604` — "real `dev` link — 1000 ms | 2·2 + 50 + 21 = 75
  ms | 13.3× ... same file, no CRC | 30 ms | 24 ms | **1.25×**" | Margin table built on the 21 ms GC
  constant; failure seen on CI run `35468454090`. · related: UART.T10, TEST.S14 · [H13]
- **TEST.N698** SETTLED · `SPECIFICATION.md:5606-5612` — "The accepted trade-off is that neither test
  would now catch a *latency* regression below 240 ms" — Accepted test-coverage gap for
  `_hammer_clean`/`_measure_retention`. · related: TEST.T04 · [H13]
- **TEST.N699** INVAR · `SPECIFICATION.md:5614-5620` — "**Constraint — a loopback harness must never
  register a fake UART with a real `select.poll()`.**" — Hang/segfault avoidance rule (CLAUDE.md known
  hang cause); `digital_twin/unix_port_poll_prewarm.py` records a `modselect.c` segfault with non-fd
  poll objects. · related: TWIN.T07 · [H13]

## SPECIFICATION.md Part K.2 — Driver to the Part C/D bar

- **TEST.N700** LIMIT · `SPECIFICATION.md:5743-5750` — "this project's own
  `tests/machine.py`/`digital_twin/machine.py` fakes both type `pull` as a plain `int` with a `-1`
  sentinel, not `int — None`, so the real MicroPython-idiomatic `pull=None` would need both fakes' own
  signatures widened" | Fake signatures diverge from the real `machine.Pin` API and constrain `src/`
  call shapes. · related: TEST.T19 · [H13]

## SPECIFICATION.md Part K.5 — Digital twin

- **TEST.N701** MIRROR · `SPECIFICATION.md:5823-5825` — "Add `Pin.PULL_UP`/whatever other `machine`-fake
  constant the real driver now references to **both** `tests/machine.py` and `digital_twin/machine.py`"
  — Two-fake mirror obligation. · related: TEST.T19 · [H13]

## SPECIFICATION.md Part K.6 — Tests, every tier

- **TEST.N702** INVAR · `SPECIFICATION.md:5829-5833` — "every parameter individually and in combination
  ... out-of-range on both sides of every bound, exact boundary values accepted, `NaN`/`±inf` on every
  float argument" — Per-driver unit-test bar (D.12). · related: TEST.T02 · [H13]
- **TEST.N703** INVAR · `SPECIFICATION.md:5835-5844` — "that module needs its own direct, dedicated
  tests too — exercising it only incidentally through the new driver's own fixture values is not enough"
  — Shared-module test rule (PR #87 gap). · related: ALGO.T01 · [H13]
- **TEST.N704** INVAR · `SPECIFICATION.md:5871-5889` — "**Bus-hazard coverage, all four tiers, standing
  rule** ... Add the new driver to `tests/_bus_hazard_catalog.py`'s `I2C_HAZARD_CATALOG`" — Four-tier
  rule; cross-sensor now generated. · related: TEST.T06 · [H13]

## SPECIFICATION.md Part K.9 — Documentation

- **TEST.N705** TODO · `SPECIFICATION.md:5934-5936` — "\"no pytest gate wired for the new
  conformance-probe script yet\" — PR #83's own disclosed, not-silently-resolved gap" — Example of an
  open gap; whether still open is not stated here (low). · related: TEST.S20 · [H13]

## SPECIFICATION.md Part L.4 — Generator pipeline

- **TEST.N706** ASSUME · `SPECIFICATION.md:6303-6307` — "asserts a real `GET` against five REST
  endpoints returns 200 — for all six real devices plus both synthetic fixtures" — Five of the six
  routes; plan notes this test reads output only on nonzero exit. · related: TEST.T18 · [H13]

## SPECIFICATION.md Part L.5 — Build/generator script quality bar

- **TEST.N707** INVAR · `SPECIFICATION.md:6372-6413` — "Each family's unit tests must cover the whole
  matrix: **the accept side needs full dimensionality** ... **the reject side covers each dimension once
  without recombining**" — Test-matrix bar per tag family; reference files
  `test_buildgen_tag_comments.py`, `test_buildgen_requires_tag.py`. · related: GEN.T03 · [H13]
- **TEST.N708** INVAR · `SPECIFICATION.md:6424-6430` — "every abort condition gets its own test, driven
  by deliberately malformed fixture definition files" — Test obligation for buildgen error paths. ·
  related: GEN.T01 · [H13]

## CLAUDE.md

- **TEST.N709** INVAR · `CLAUDE.md:237-245` — "A new bus-facing (I2C/SPI) device gets bus-hazard test
  coverage across all four test tiers that apply to it — never forget this" — Owner's standing
  direction. Only partly mechanical: tests/test_bus_hazard_generated.py derives mock-tier cases from
  TOML wiring. The twin, flash and bench tiers are review-only. · covered-by: SENS.T10 (related
  TEST.T06) · [H14]
- **TEST.N710** INVAR · `CLAUDE.md:271-274` — "a test must not generate mass filesystem churn, and an
  invariant gets proven *structurally*" — Host-SSD wear rule. Convention only; no gate measures host
  I/O. · related: TEST.T02 · [H14]
- **TEST.N711** ASSUME · `CLAUDE.md:274-281` — "costing a measured **396MB of physical disk writes on
  every single run**" — Dated single measurement, with 0.006 s vs 21.3 s and 392 KB vs 396 MB after the
  fix (tests/test_tmp_scratch.py). · [H14]
- **TEST.N712** LIMIT · `CLAUDE.md:322-325` — "with no `gc.collect()` calls or other nonstandard `gc`
  settings anywhere in the business logic or the test's own setup" — The lint guard covers only src/ and
  buildgen/ (scripts/lint.sh:42-49). `gc.collect()` in tests/ and digital_twin/ is unguarded. ·
  covered-by: TEST.S11 (TEST.T03) · [H14]
- **TEST.N713** SETTLED · `CLAUDE.md:613-621` — "Known hang cause, fixed ... Don't re-diagnose this
  specific symptom as a new code bug if it recurs elsewhere." — Real `select.poll()` on non-fd fakes
  hangs on GitHub Actions only. · related: DOC.T14 · [H14]
- **TEST.N714** INVAR · `CLAUDE.md:619-620` — "any test double for `uart.poller` ... must be a bounded
  fake like `_StepPoller`, never backed by a real `select.poll()`" — Convention only (e.g.
  tests/test_asy_uart_driver.py:35, 43); no meta-test. · related: TEST.T06 · [H14]
- **TEST.N715** LIMIT · `CLAUDE.md:614-616` — "never detects readiness on GitHub Actions runners
  specifically (not reproducible locally)" — Root cause never explained; only avoided. · [H14]
- **TEST.N716** SETTLED · `CLAUDE.md:622-649` — "Known hang cause #2, fixed ... Fixed in
  `tests/microtest.py`: `run()` now always calls `sys.exit()`" — Present at tests/microtest.py:42. ·
  related: TEST.T12 · [H14]
- **TEST.N717** INVAR · `CLAUDE.md:658-662` — "must only ever be called from synchronous test-function
  scope, never from inside a coroutine" — Nested `asyncio.run()` segfaults. Convention only; no guard or
  meta-test. · covered-by: TEST.T06 · [H14]
- **TEST.N718** ASSUME · `CLAUDE.md:662-663` — "Audited across `tests/`, `digital_twin/` and `src/`: no
  other call site does this." — Point-in-time audit, not re-run mechanically. · covered-by: TEST.T06 ·
  [H14]
- **TEST.N719** ASSUME · `CLAUDE.md:698-700` — "could exhaust the interpreter's 2MB default heap roughly
  1 run in 3" — Historical measurement. · [H14]
- **TEST.N720** INVAR · `CLAUDE.md:718-727` — "Two suites that both bind real ports must never run at
  the same time." — Convention only; no lock. "don't re-diagnose this pattern as a code or merge
  defect." · related: TEST.T14 · [H14]
- **TEST.N721** ASSUME · `CLAUDE.md:727-731` — "its HTTP ports are ephemeral ... captive DNS on 53 - is
  `SO_REUSEADDR` and degrades to \"not connected\"" — Asserted safe overlap of the backgrounded tier. ·
  related: TEST.T14 · [H14]
- **TEST.N722** SUPPRESS · `CLAUDE.md:771-779` — "each of those ~157 sites carries its own inline `# type: ignore[method-assign]`"
  — At 2a88cc8 there are 199 lines with a method-assign ignore across 22 files in tests/ and
  digital_twin/. `src/` is guarded by the scripts/lint.sh:31-34 grep. · covered-by: DOC.S08 · [H14]
- **TEST.N723** SUPPRESS · `CLAUDE.md:780-787` — "`# noqa: E402` belongs only on files with a real
  statement before their imports" — 24 sites in tests/. The split is enforced mechanically by E402 plus
  RUF100. · [H14]
- **TEST.N724** LIMIT · `CLAUDE.md:821-831` — "resolves every `from machine import X` project-wide to
  `tests/machine.py`'s fake module, not the real `typings/machine.pyi` board stub" — `src/` is
  type-checked against the fake. A src-only run shows 12 call-overload errors (system_service 4, ntp 3,
  wifi 2, plus sgp40/scd30/bmp3xx). · covered-by: TEST.T19 (DOC.S17 counts) · [H14]
- **TEST.N725** WORKAROUND · `CLAUDE.md:828-831` — "a genuine **gap in the third-party
  `micropython-rp2-rpi_pico_w-stubs` package**" — No zero-arg `Timer()` overload. Masked only because
  the fake wins resolution. Removal trigger: none stated. · related: TEST.T19 · [H14]

## README.md

- **TEST.N726** ASSUME · `README.md:146-147` — "The suite is sleep-bound rather than CPU-bound, so
  oversubscribing a fast host is close to free" — Tight wall-clock assertions under 1-4× parallelism
  exist. · related: TEST.S14, TEST.T04 · [H14]
- **TEST.N727** ASSUME · `README.md:148-149` — "default 1200 — roughly 5x its real runtime, so it only
  fires on a genuine hang" — Unmeasured ratio; the only hang backstop for `tests_scripts/` is
  suite-wide. · related: TEST.T13, TEST.T16 · [H14]

## BACKLOG.md

- **TEST.N728** TODO · `BACKLOG.md:81-95` — "Named follow-ons still open, tracked in that section, not
  repeated here" — Unnumbered "tier/layering-completeness scan" (owner 2026-09-15): open follow-ons live
  in `tests_hardware/README.md` "Tenth pass". · related: HW.T09, TEST.T15 · [H15]
- **TEST.N729** LIMIT · `BACKLOG.md:94-95` — "Re-running this sweep against other domains ... is
  future work, not assumed done everywhere." — Sweep did not cover sensortask/system_service integration
  beyond FRAM/memory. · related: TEST.T15 · [H15]
- **TEST.N730** LIMIT · `BACKLOG.md:113-116` — "only ever proved wire-level atomicity, never this
  shadow-vs-chip timing race" — A named mock test covered less than it appeared to. · related: TEST.T01
  · [H15]
- **TEST.N731** LIMIT · `BACKLOG.md:683-696` — "What remains genuinely unmodelled is the duration" —
  UART fakes deliberately don't wait; count `would_have_blocked_bytes` (identical semantics held by
  `tests/_uart_link_contract.py`); only the bench measures ms. · related: BUS.T05, TEST.T05 · [H15]
- **TEST.N732** MIRROR · `BACKLOG.md:903-905` — "Both test fakes gained readfrom_mem_into() delegating
  to their own readfrom_mem" — Fault injection depends on the fakes keeping this delegation. · related:
  TEST.T05 · [H15]

## HEAP_FRAGMENTATION_MEASUREMENTS.md (current, 393 lines; owning area HW)

- **TEST.N733** INVAR · `HEAP_FRAGMENTATION_MEASUREMENTS.md:154` — "Mocking by rebinding a module
  attribute misses from x import name consumers" — Rebind across `sys.modules` and assert the count. ·
  related: TEST.T17 · [H15]
- **TEST.N734** INVAR · `HEAP_FRAGMENTATION_MEASUREMENTS.md:244-247` — "it runs a suppressed control arm
  that must violate every bound, or the guard is not a guard" — `test_digital_twin_boot_contiguity.py`
  bounds are twin-only, never copied to the board. · [H15]
- **TEST.N735** LIMIT · `HEAP_FRAGMENTATION_MEASUREMENTS.md:242-244` — "scripts/test.sh runs every file
  at a fixed -X heapsize=16M and a test cannot change its own heap." — Calibrated-heap checks impossible
  in the unit tier. · [H15]

## Commit messages (chronological)

- **TEST.N736** SETTLED · `commit 5dec62b` — "no automated soak test needed (design discipline instead)
  ... no hard coverage gate yet" — Early owner decision "no automated soak test" was later overtaken
  (twin soak Runs, `long_soak` bench tests exist); coverage gate later settled as never-gating
  (CLAUDE.md). Historic — audit should not treat the soak tests as contradicting a live rule (low). ·
  status: superseded | - · [H17]
- **TEST.N737** LIMIT · `commit 8ac4ddf` — "the single-character stdout lines interleaved with PASS/FAIL
  in the CI log - not a bug ... Documented, left as-is" — Known noisy CI log output from test_print_log.
  · tracked: per commit, location not verified (low) | - · [H17]
- **TEST.N738** SUPPRESS · `commit 55e4453` — "a MicroPython Unix-port heap-exhaustion effect under a
  tight allocate-heavy loop without periodic gc.collect()" — Per-cycle gc.collect() in
  tests/test_fram_integration.py:159-177 props up a 40-cycle loop, labelled a test-environment artifact.
  · tracked: plan | covered-by: TEST.S11 · [H17]
- **TEST.N739** LIMIT · `commit 639e992` — "this Unix-port test build can only ever produce an opaque
  raw sockaddr ... so the actual subnet-membership decision logic can't be exercised through a genuine
  socket here" — Captive-DNS subnet filtering is unit-tested only through a duck-typed fake transport. ·
  status: real-hardware coverage later via bench DNS tests (BACKLOG #5) — partial (low) | related:
  NET.T* · [H17]
- **TEST.N740** INVAR · `commit b67d69d` — "scripts/test.sh's per-file loop doesn't treat a file with no
  invocation as an error (nothing to fail)" — A tests/test_*.py file lacking its `run(globals())`
  trailer passes with zero tests; still convention-only (test.sh:455-470 counts PASS by status file
  only). · covered-by: TEST.T12 (SCR.T01) · [H17]
- **TEST.N741** SUPPRESS · `commit 0d68b8d / 184db4f / e8d612e / b4a9c54` — "Suppressed the resulting
  mismatch with type: ignore[return-value] ... rather than mistyping the annotation to match the stub" —
  Stub-vs-runtime gather() list/tuple gap; ignore still present at tests/test_asy_fram_manager.py:1602.
  Four commits re-fixed this churn because mypy was then unpinned. · status: mypy now pinned (CLAUDE.md)
  | - · [H17]
- **TEST.N742** PLATFORM · `commit b686e32` — "nesting asyncio.run() inside an already-running coroutine
  segfaults this MicroPython Unix port build instead of raising cleanly" — First sighting of the
  nested-asyncio.run segfault. · tracked: CLAUDE.md "Known segfault cause, fixed" | related: TEST.T* ·
  [H17]
- **TEST.N743** WORKAROUND · `commit 980f76f` — "its select.poll() doesn't re-check a plain Python
  stream object's ioctl() per call ... Worked around with a small _StepPoller test helper" — Unix-port
  poll limitation on fake streams. · tracked: CLAUDE.md "Known hang cause, fixed" (removal trigger: none
  stated) | - · [H17]
- **TEST.N744** SETTLED · `commit 500851c` — "recorded the general \"leave the catch, skip an untestable
  test, note why\" convention in BACKLOG.md, confirmed directly by the project owner" — Owner convention
  for untestable defensive catches; no longer in BACKLOG (grep) and not visible in SPECIFICATION Part
  D/E. · status: UNTRACKED (low) | related: TEST.T* · [H17]
- **TEST.N745** WORKAROUND · `commit cc911be` — "a confirmed Unix-port-vs-rp2 time.gmtime() tuple-length
  difference the test suite works around" — Unix-port gmtime shape differs from rp2 (8-tuple); tests
  paper over it. · status: not found restated in SPECIFICATION Part F (grep); removal trigger none
  stated — UNTRACKED (low) | related: PLAT.T* · [H17]
- **TEST.N746** MIRROR · `commit dd22d43` — "tests/test_asy_wifi_service.py now defines its own literal
  mirrors of the four phase values instead of importing them" — const() phase values duplicated in tests
  (const values not importable). · tracked: tests/test_asy_wifi_service.py:14-18 comment; enforcement
  none | related: TEST.T* · [H17]
- **TEST.N747** PLATFORM · `commit c5478f0` — "MicroPython's globals() does not preserve insertion order
  (unlike CPython 3.7+), so test execution order within a file is effectively hash-dependent ... no test
  in this suite should depend on order" — Test independence from order is convention only. · tracked:
  CLAUDE.md "non-deterministic test-function run order" (partial) | related: TEST.T* · [H17]
- **TEST.N748** TODO · `commit 6c7903c` — "NTP transient-outage retry x concurrent bus load: ...
  Twin/mock deliberately not extended in this pass ... flagged as a real, still-open opportunity" —
  Recombination gap. · tracked: BACKLOG "Network fault injection ... Still open: the
  NTP-outage-x-bus-load fault recombination has no twin/mock-tier equivalent" | related: TEST.T* · [H17]
- **TEST.N749** SUPPRESS · `commit c623bc8` — "the single skip this branch introduces is an
  honestly-marked fixture-writer limitation on a case three sibling parametrizations already cover" —
  pytest.skip at tests_scripts/test_buildgen_validate.py:1208 ("an inline table can't be produced by
  this fixture writer"). · status: still present | related: TEST.T* · [H17]
- **TEST.N750** NOTE(BUG-FOUND) · `commit c4046a5` — two test files lacked the `run(globals())` trailer
  and ran zero tests; MicroPython dicts do not preserve insertion order — Dead tests fixed; no
  structural guard mentioned. · status: done-in c4046a5 (guard: see TEST.T12) | covered-by: TEST.T12 ·
  [H17]
- **TEST.N751** NOTE(GC-WORKAROUND) · `commit a9dd34f` — "Fixed by wrapping each generated test's body
  in try/finally: gc.collect()" (MemoryError at gc.threshold(32768)) — gc.collect() in test body as
  MemoryError fix; conflicts with the later CLAUDE.md rule "no gc.collect() ... in the test's own setup
  propping the result up". · status: likely superseded when test_sensortask.py was split per device
  (E.3.1) — not re-verified whether the try/finally gc.collect() survives in test_digital_twin_* files |
  related: MEM.T*, TEST.T* · [H17]
- **TEST.N752** NOTE(OPEN-ITEM) · `commit fd333ce / 2b9c997` — "the fakes still not modelling a blocking
  read" -> "duration remains unmodelled, and only the bench tier measures it" — Mock fakes count
  would-block bytes but not wait duration. · tracked: SPEC F.5.8 + BACKLOG | related: TWIN.T* · [H17]
- **TEST.N753** NOTE(TEST-BOUND) · `commit fd333ce / 1e1a26a` — leak bounds recalibrated per-operation
  (< 6.0 B/transaction) after runner-dependent noise — Calibrated tolerance, not zero. · tracked: SPEC
  Part E.8 | - · [H17]
- **TEST.N754** NOTE(FLAKY) · `commit 2e7e4eb` — "a real but unrelated CI-timing flake
  (tests/test_asy_ntp_client.py::test_integration_recovers_on_retry_after_one_dropped_request, a
  TimeoutError on a real 5-second UDP round-trip wait) ... confirmed transient, not a regression, not
  touched" — Flaky real-UDP test left as is. · UNTRACKED (low; no BACKLOG/SPEC mention; test still at
  tests/test_asy_ntp_client.py:2205) | related: NET.T*, TEST.T* · [H17]
- **TEST.N755** WORKAROUND · `commit 9cf8a9c / 0dc9799` — "raised scripts/test.sh's -X heapsize to 32M";
  8M experiment reverted "to the known-safe 32M rather than gambling" — Heap ceiling raised to pass
  tests. · status: done — per-device split, now 16M (CLAUDE.md, SPEC E.3.1) | related: MEM.T* · [H17]
- **TEST.N756** NOTE(BUDGET-RAISED) · `commit 9cf8a9c / f83cd79 / a335923` — boot duration budget
  raised; webserver start wait 0.1s -> 0.5s; per-file timeout 180 -> 240s; "Tried a polling readiness
  check first ... Reverted to a fixed sleep" — Fixed sleeps as readiness waits. · status: partly
  superseded by per-device split (cbe07a6); fixed-sleep readiness remains by design (not re-verified) |
  related: TEST.T* · [H17]
- **TEST.N757** NOTE(CLAIM-RETRACTED) · `commit e47d4e1` — "retracts the 'tests/_tmp growth confirmed
  unrelated to WP1/WP2' claim"; "adds an open item for the heap-footprint bump (8M->32M) being a
  workaround"; "Also flags a CFGMGR_SYSTEM setup-ordering anomaly" — Several open items. · status:
  CFGMGR_SYSTEM done-in 7cd8dd1; heap item resolved (16M, E.3.1); tmp growth fixed 07b1e2b | - · [H17
  (also H17)]
- **TEST.N758** NOTE(REVERTED) · `commit 1e2c001 -> 874e3da` — "Revert gc.collect() additions - wrong
  tool, and empirically didn't work anyway" — Rule enforcement. · status: done | - · [H17]
- **TEST.N759** NOTE(ACCEPTED-FLOOR) · `commit 5cd7e30` —
  "tests/test_digital_twin_bus_hazard_concurrency.py's own dev-variant scenario cleanly bisected ... to
  a real 8M-fails/16M-passes floor - a genuine real-time-budget margin issue ... not something changed
  here (would alter what the test proves, not this session's call to make)" — The 16M heap is
  load-bearing for one real-time-budget test, not purely a harness margin. · tracked: SPEC E.3.1
  (heapsize history); the "fixed 9-second real-clock window" design question not in BACKLOG (low) |
  related: TEST.T*, MEM.T* · [H17]
- **TEST.N760** NOTE(OPEN-DECISION) · `commit af5c733 -> d370413` — "a twin assertion with a real-time
  budget is a third hazard ... BACKLOG 28 carries the open decision"; resolved by TEST_PARALLELISM
  autodetect — Parallelism vs real-time budgets. · status: done-in d370413 (probe thresholds
  250ms/900ms) | - · [H17]
- **TEST.N761** NOTE(F15 / F16) · `commits 02cc4c5, 5633a0b -> 3a1e5f3` — "the guard has
  _JUSTIFIED_UNREADABLE_BODIES ... but no concept of a call it cannot recognise"; "one CI-only
  test_uart_comm_hazard failure at 149/150 ... stays undiagnosed rather than dismissed" — Guard blind
  spot and flaky-under-load UART test. · status: both done-in 3a1e5f3 (F16 root-caused to host
  rescheduling at 1.25x margin; clean-run tests take the CRC arm's margin) | - · [H17]
- **TEST.N762** NOTE(DEFENSIVE-UNTESTED) · `commit 83c1c57` — "Four sites are left untested deliberately
  and are now named in SPECIFICATION.md Part E.5.1's register" (config_manager type-name except, wifi
  ifconfig length fallback, sgp40 readlen=None return, voc_algorithm overflow return) — Accepted
  untested branches. · tracked: SPEC E.5.1 | - · [H17]
- **TEST.N763** NOTE(DEAD-END-KEPT) · `commit 8a603f2 / 448bd02` — "the _drained() hardening kept from
  the dead end fixes nothing that was ever observed, and no longer pretends to"; real cause fixed port
  18099 collision — Kept hardening + root-cause fix. · status: done-in 448bd02 | - · [H17]
- **TEST.N764** NOTE(TEST-GAP-CLOSED) · `commit cca4fd3` — "MicroPython's json.loads() treats ',' and
  ':' as whitespace ... so no streamed-body test could catch a separator slip the browser rejects" —
  Strict JSON recogniser added. · status: done (tests/_strict_json.py; SPEC F.1) | - · [H17]

## GitHub PRs and issues (hundertvolt/sensors)

- **TEST.N765** NOTE(LEAK-IN-TOOL) ·
  `https://github.com/hundertvolt/sensors/pull/95#issuecomment-5692708409` — "`tests/machine.py`'s
  `Timer.all_timers` is a process-lifetime registry that file never clears ... An unverified one-line
  fix sits in `1bfd631` on the backup branch" — Registry still unbounded at 2a88cc8
  (tests/machine.py:611,630); only per-driver tests clear it; masked by the per-device test_sensortask
  split, not fixed · UNTRACKED | related: CLAUDE.md heapsize history (E.3.1) · [H17 (also H17)]
- **TEST.N766** NOTE(FUTURE) · `https://github.com/hundertvolt/sensors/pull/104` — "going further would
  need `tests_scripts/` itself parallelized (e.g. `pytest-xdist`), flagged as a further opportunity, not
  attempted" — tests_scripts single-process tier is the suite's wall-clock floor · UNTRACKED | - · [H17]

## Delta `2a88cc8` → `4dc80ef` (main head, V11)

- **TEST.N767** INVAR · `tests/test_asy_sgp40_driver.py:1068-1128` — "Bench finding 2026-09-25: one slot
  per 1-min backup filled the ring after one hotspot episode." — Four W13 episode tests (outage,
  timestamped end on both branches, deferral and E14 not ending it); the commit says each failed against
  a matching mutation (`83c9920`). · related: SENS.S28 · [D1]
