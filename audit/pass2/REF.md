# Refined harvest — new requirements

### REF/R01 One term per concept: device variant, build flavour, peripheral, board
- **Req**: One short term table in SPECIFICATION.md's front matter fixes one name for each concept, and docs, identifiers, comments and CLI help use it: the unit a `devices/<name>.toml` defines (the owner's "board variant", OR78; SPEC L.1 "Device variants"), a Unix-port build flavour (`build-standard`/`build-settrace`; `scripts/test.sh` calls it `want_variant`, MicroPython calls it `VARIANT`), a bus peripheral (`I2CDevice`, "one device address") and the Pico board itself. No term names two of these concepts. The owner's own wording in quoted owner rows stays verbatim.
- **Sources**: RF066 · OR24, OR78/OR78.a, harmonization 44 · `SPECIFICATION.md:6012`, `:140`; `CLAUDE.md:159`, `:239`, `:572`; `scripts/test.sh:75-108`
- **Rank**: agent — "(agent, 2026-09-28)"; basis owner: "The whole repo code shall be made out of one material once the audit is over." (owner, 2026-09-25, OR24); "board variant" is the owner's term (owner, 2026-09-28, OR78)
- **State**: work: doc in U36 — term table; L.1 heading, `SPECIFICATION.md:140`, `CLAUDE.md:159/:239/:572` harmonised; code in U27 — `scripts/test.sh:75-108` `want_variant`/`unix_port_variant` renamed to the build-flavour term
- **Home**: SPECIFICATION.md front matter
- **Pillar**: P4
- **Pass 2**: new (refined harvest, RF066). Not DOC.T09's glossary (G9/R12, overtaken by OR68.a (4)): that one defined decision labels; this table fixes the names of four technical concepts.

### REF/R02 Confirmed leftovers are removed
- **Req**: A function, method, constant, export or helper with no caller in the product, the build chain, the generated code or the tooling is removed, together with any test that only exercises it. Each removal is confirmed by hand against a repo-wide reference search that includes generated code (buildgen resolves drivers and `@web` fields by name). API that completes a driver for its hardware stays (G3/R21, OR36.a (3)). A helper that exists in product or build-chain code only for its tests is a test artifact (OR36.a (1)).
- **Sources**: RF231, RF232, RF234, RF240, RF241, RF248, RF249, RF250, RF251, RF252, RF253 · OR46.a (2), OR36.a (1)(3), OR78.a (1) · STOR.N191, SENS.md:133, WEB.N115, TEST.md:2483, HW.N840, TWIN.N088
- **Rank**: owner — "2. a" (owner, 2026-09-26, OR46.a (2): "confirmed leftovers … are removed, except general-purpose driver API (OR36.a (3))"); candidate list and per-item verdicts "(agent, 2026-09-28)"
- **State**: work: code in U16 — `src/asy_fram_driver.py:45-47, :51` `_SPI_OPCODE_WREN`/`_WRDI`/`_RDSR`/`_RDID` are referenced nowhere, and the same opcodes also exist as the `_CMD_*` bytes at :56-59, which the code uses (RF231); `AsyFramChunk.get_size()`/`AsyFramTimestampedChunk.get_size()` (`src/asy_fram_manager.py:427, :509`) are called only by tests and are not hardware API (RF234); code in U15 — `src/asy_isl29125_driver.py:44` `_REGISTER_CONFIG3` is referenced nowhere (RF232); code in U23 — the `export` of `DEFAULT_TIMEOUT_MS` (`js/poll-manager.js:8`) has no importer, and `tests_js/definitions.test.js:295` copies 15000: the test imports the constant (G1/R41) or the export goes (RF240); code in U20 — `buildgen/tag_comments.py:225` `looks_like_tag_payload()` is called only by `tests_scripts/test_buildgen_tag_comments.py` (RF241); code in U25/U24 — `direction_to()` (`digital_twin/machine.py:516`, `tests/machine.py:527`) is never called (RF248); `configure_i2c_wiring()` (`digital_twin/machine.py:184`), "kept for tests", gets a verdict: its callers move to `configure_wiring()` with the derived plan, and its literal `("wozi", "dev")` check (:192) goes under OR78.a in either case (RF253); code in U26 — `tests_hardware/bench_control.py:263, :277` `is_valid_mac()`/`wait_for_link_local_teardown()` (RF249), `tests_hardware/error_log_helpers.py:43` `assert_module_error_log_nonempty()` (RF250), `tests_hardware/harness.py:461` `Board.soft_reset()` (RF251), `tests_hardware/device_scripts/isl29125_lighting_scenarios.py:33` `_STEP_MS` (RF252)
- **Home**: none (audit ledger, OR46.a (1)); the removals land in code
- **Pillar**: P4
- **Pass 2**: new (refined harvest, RF231, RF232, RF234, RF240, RF241, RF248, RF249, RF250, RF251, RF252, RF253)

### REF/R03 Elapsed time is measured, not counted
- **Req**: Every value that reports or enforces an elapsed time is derived from wrap-safe `ticks_ms()` or RTC deltas (G5/R10), never from counted 1 s wake-ups. This covers `SysUptime`, WiFi uptime, the NTP sync age and the LED pause countdown (`PauseTime`, up to 3,600 s). A dropped soft callback or a stalled loop then costs latency, never accuracy, and a pause never runs more than one tick longer than set. The 1 s periodic counters (system uptime, WiFi, NTP) share one starter shape and one ENOMEM-degrade wording, or one tick source. They stay out of the read stagger and start with the timer starters (G6/R37).
- **Sources**: RF189, RF262 · G5 gap 1 (proposed in pass 2, not adopted), XCUT.T21, CORE.S18, NET.S02, NET.N044 · OR44 (P1), OR24, OR47.a (3)
- **Rank**: agent — "(agent, 2026-09-28)"; the timers stay out of the stagger by the owner's decision (owner, 2026-09-26, OR47.a (3), G6/R37)
- **State**: work: code in U9 — the pause countdown advances one step per `asyncio.sleep(1)` round, after two lock operations (`src/asy_notification_service.py:317-330`) (RF189); code in U10 — three separate 1 s Timers, events and counting tasks (`src/asy_ntp_client.py:341-346`, `src/asy_wifi_service.py:660-665`, `src/system_service.py:202-204`): two of the starters are byte-equivalent and the ENOMEM degrade is worded three ways (RF262); code in U11 — `SysUptime` (`src/system_service.py:204, 379-380`, G5 gap 1); test in U35 — a driven-clock proof with dropped wake-ups (LEAD/R04)
- **Home**: SPEC C.9 (timers); G.2
- **Pillar**: P1
- **Pass 2**: new (refined harvest, RF189, RF262)

### REF/R04 One primitive for the current UTC timestamp
- **Req**: "Current UTC timestamp" is one Part G.2 primitive that every module uses. It has one expression, one sentinel for "not available" (NTP not synced, `OverflowError`/`OSError`) and one logging decision. A sensor reader takes the timestamp outside its read `try`, so a clock failure is never recorded as a sensor read failure. The handlers around the primitive take G4/R15's verdict (removed if unreachable on target).
- **Sources**: RF257 · OR24, OR46.b (scope), harmonization 30 · PLAT.md:1602, STOR.N060, G4/R15
- **Rank**: agent — "(agent, 2026-09-28)"; basis owner: "one material" (owner, 2026-09-25, OR24) and "adopt the solutions at any place they improve code tidyness" (owner, 2026-09-26, OR46.b)
- **State**: work: code in U10 — `time.mktime(time.gmtime())` is written ten times in nine modules (`src/asy_notification_service.py:183`, `src/asy_ntp_client.py:146`, `src/asy_wifi_service.py:193`, `src/system_service.py:143`, `src/asy_fram_manager.py:547, :611`, `src/asy_bmp3xx_driver.py:190`, `src/asy_isl29125_driver.py:376`, `src/asy_scd30_driver.py:177`, `src/asy_sgp40_driver.py:283`). Three identical `_now()` copies return `None` silently, system and FRAM log the failure under their own errno (2, 86, 88), and the four readers compute it inside the read's `try`. Doc in U10 — the G.2 entry
- **Home**: SPEC G.2
- **Pillar**: P4
- **Pass 2**: new (refined harvest, RF257)

### REF/R05 One job, one implementation
- **Req**: A derivation or helper is written once and then imported. This holds within a module (SGP40's backup-verify count), across host tools (the `device_max_connections` lookup) and across the twin's entry points and chip fakes (BMP3xx calibration decode, argument parsing). G2/R26 states the same rule for `tests/`.
- **Sources**: RF265, RF266, RF267, RF268 · OR24, OR46.a (3), OR46.b (scope) · SENS.md:551, PAR.md:720, HW.N031
- **Rank**: owner — "The whole repo code shall be made out of one material once the audit is over." (owner, 2026-09-25, OR24); site list "(agent, 2026-09-28)"
- **State**: work: code in U15 — `src/asy_sgp40_driver.py:353, :410` backup-verify derivation written twice (RF265); code in U27 — `scripts/_digital_twin_ci_suite.py:202-209` and `tests_hardware/harness.py:39-46` hold the same path insert, late import and call (RF266); code in U25 — `digital_twin/_bmp3xx_chip.py:43` `_decode_calibration()` and `digital_twin/launch.py:216` `_decode_bmp3xx_calibration()` have identical bodies (RF267); `_pop_value()` is identical in `digital_twin/launch.py:141` and `digital_twin/run_generic_integration.py:111` (RF268)
- **Home**: SPEC G.1 (reuse before writing), D.10
- **Pillar**: P4
- **Pass 2**: new (refined harvest, RF265, RF266, RF267, RF268)

### REF/R06 SCD30 calibration preconditions are visible to the operator
- **Req**: The SCD30 calibration fields state their datasheet preconditions in their help text. `ForceCalRef` needs continuous measurement at the configured interval for at least max(6 min, 5 × interval) in a stable environment (Interface Description 1.4.5, Field Calibration note, Low Power Mode note; OR98.a). `SelfCal` needs at least 7 days of uninterrupted power with daily fresh air (1.4.6). FRC readiness is decided by OR98.a's four criteria — continuous measurement running; at the configured interval; uninterrupted for at least max(6 min, 5 × interval) (Low Power Mode note); CO₂ change rate and spread within limits over a minimum window (floor from repeatability ±10 ppm, window from τ63 20 s) (owner, 2026-09-29); it is reported as a code, `ForceCalRef` never refused; counting saturates at its target (no overflow); state in RAM only, no flash or FRAM; noise floor, change-rate limit and window are config parameters with bench-measured defaults (owner, 2026-09-29, OR99.a). Today, an FRC applied too early is answered "Valid".
- **Sources**: RF335 · G3 gap 2 (proposed in pass 2, not adopted), OR76 (the ISL29125 analogue), OR43.a (1), OR52.a (2), A14 · SENS.T13, SENS.S22 · LEAD/R14
- **Rank**: agent — help text "(agent, 2026-09-28)"; manual FRC procedure (owner, 2026-08-11, A14); the readiness field is the owner's call
- **State**: work: code in U15 — the `@web ForceCalRef`/`SelfCal` descriptions (`src/asy_scd30_driver.py:69-70`); doc in U36 — DEVICE_REFERENCE.md via LEAD/R14; work: code in U15 — readiness code, saturating counter, RAM-only state, three config parameters; U23 label; U26 bench values for the defaults (OR98.a, OR99.a) (RF335)
- **Home**: the fields' `@web` tags; DEVICE_REFERENCE.md; SPEC M (SCD30)
- **Pillar**: P3
- **Pass 2**: new (refined harvest, RF335)
