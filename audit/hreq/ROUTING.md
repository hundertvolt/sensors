# Harvest requirements — routing (consolidation, HEAD 06eff58)

Audit working file (temporary, deleted with `audit/`, OR11.a). Input: the 965 candidates of `audit/hreq/G1.md` … `G10.md`, the owner rows OR1-OR55 (PROJECT_AUDIT_PLAN.md 3.2) and the unit list (4.1). Read-only routing: nothing here changes code, tests or docs.

## Conventions

- **Scope of Task 1**: every candidate whose Truth is not `holds` — 349 partly, 100 drifted, 19 wrong, 16 not checked, 15 unverifiable, 1 stale source = **500** — plus **13** candidates whose Truth reads `holds …` with a qualifier that still names work (a conflict, a drifted count, an open owner question), marked `[q]`. Total **513** lines, one unit each.
- **One unit per candidate**: the unit that must act. A fix that belongs to a B1 foundation (U1-U8) goes there, not to the area unit: SCD30 PUT/NVM writes to U4, errno numbering to U2, repeat-slot behaviour to U3, website definitions and derived device sets for the website to U6, runner summaries/skip visibility/tier containment to U7, tuned values to U8, bench references leaving `dev_legacy/` to U1. Otherwise the owning area of plan 5.0; test-standard work that needs the whole-suite review (fault planting, biting, forced interleavings) goes to U35; doc-set structure and content rules to U36.
- **Kinds**: `code-fix` (code, tests or config change; includes OR24 consistency changes), `doc-fix` (factual drift fixed in place, OR13.a), `test-add` (a missing test or mechanical check), `rule-write` (the only work is writing a rule that has no home yet), `hardware` (needs silicon: phase C / BACKLOG hardware list), `decide` (needs the owner; the question is named, with the harvest question it came from). A candidate with both a fix and a missing home is routed by its fix; Task 3 lists every missing home regardless.
- A `decide` line whose question traces to a recorded rule (CLAUDE.md hard rule, owner decision in SPEC) is an OR13.a rule-drift question; the others are OR48.a (2) or plain design questions. Where the owner already answered a harvest question in a later row (OR55 for G2 Q1, OR24.a for G5 Q1, OR52.a (6) for the heap-unwedge helper), the line is routed as work, not as a question.

## Summary

| Unit | Content | code-fix | doc-fix | test-add | rule-write | hardware | decide | total |
|---|---|---|---|---|---|---|---|---|
| U0 | B0 ENV |  | 1 | 1 |  |  |  | 2 |
| U1 | B1 legacy move to legacy/ | 1 | 4 |  | 1 |  |  | 6 |
| U2 | B1 errno/wrnno catalog | 5 |  | 1 |  |  |  | 6 |
| U3 | B1 central log-repeat rule | 3 |  |  |  |  | 2 | 5 |
| U4 | B1 compare-before-write primitive | 4 | 1 |  |  |  |  | 5 |
| U5 | B1 config objects and max-args | 2 |  |  |  |  |  | 2 |
| U6 | B1 one-source website definitions | 6 | 2 | 1 |  |  |  | 9 |
| U7 | B1 tier ladder and runner summary block | 4 | 1 | 1 |  |  |  | 6 |
| U8 | B1 @tunable scheme | 8 |  |  |  |  |  | 8 |
| U9 | B2 pilot LED | 1 |  |  |  |  |  | 1 |
| U10 | B2 XCUT | 27 | 3 | 5 |  |  | 4 | 39 |
| U11 | B2 CORE | 7 | 5 | 2 |  |  | 2 | 16 |
| U12 | B2 ALGO | 3 | 1 | 1 |  |  | 2 | 7 |
| U13 | B2 BUS | 3 | 1 |  | 1 |  |  | 5 |
| U14 | B2 PLAT |  | 12 | 2 | 1 |  | 1 | 16 |
| U15 | B2 SENS | 17 | 8 |  |  |  | 2 | 27 |
| U16 | B2 STOR | 5 | 2 | 1 |  |  |  | 8 |
| U17 | B2 UART | 2 | 1 | 1 |  |  |  | 4 |
| U18 | B2 NET | 8 | 2 |  |  |  |  | 10 |
| U19 | B2 REST | 6 | 1 |  |  |  | 2 | 9 |
| U20 | B2 GEN | 18 | 1 | 9 |  |  |  | 28 |
| U21 | B2 TOOL | 14 |  |  |  |  |  | 14 |
| U22 | B2 LED re-check |  | 1 |  |  |  |  | 1 |
| U23 | B2 WEB | 18 | 4 | 2 |  |  | 2 | 26 |
| U24 | B2 TEST | 30 | 3 | 9 |  |  | 1 | 43 |
| U25 | B2 TWIN | 22 | 5 |  | 1 |  |  | 28 |
| U26 | B2 HW | 40 | 6 | 6 |  |  |  | 52 |
| U27 | B2 SCR | 15 | 2 | 2 |  |  |  | 19 |
| U28 | B2 CI | 13 | 6 | 1 |  |  | 2 | 22 |
| U29 | B2 SEC |  | 2 |  | 1 |  |  | 3 |
| U30 | B2 MEM | 7 |  | 3 |  |  | 3 | 13 |
| U31 | B2 PERF | 1 | 1 |  |  |  |  | 2 |
| U32 | B2 PAR | 1 |  | 1 | 1 |  | 1 | 4 |
| U33 | B2 DOC |  | 7 |  |  |  | 1 | 8 |
| U34 | B2 LIC | 1 | 7 |  | 1 |  |  | 9 |
| U35 | B3 test campaign | 6 |  | 1 | 1 |  | 1 | 9 |
| U36 | B4 docs |  | 18 |  | 11 |  | 2 | 31 |
| C | Phase C hardware rounds (BACKLOG "Real-hardware work still owed") |  |  |  |  | 10 |  | 10 |
| **all** | | **298** | **108** | **50** | **19** | **10** | **28** | **513** |

Units with no routed line: U37 (B5 close) — it still runs its full close; no harvest candidate needs it specifically.

## Task 1 — routing of non-`holds` candidates

Format: `G… | unit | kind | what` (Truth word in brackets).

### U0 — B0 ENV (2)

- G2.069 | U0 | doc-fix | run the three mypy passes to confirm; move the one-module-per-run fact to SPEC B.15 [unverifiable]
- G8.107 | U0 | test-add | measure a full local run's host SSD writes at the B0 baseline and record the budget [unverifiable]

### U1 — B1 legacy move to legacy/ (6)

- G1.012 | U1 | doc-fix | README.md:331-333 exec/run "no flash write" claim; mpremote write table moves from dev_legacy/README.md into tests_hardware/README.md [partly]
- G9.047 | U1 | doc-fix | tie CLAUDE.md's dev-quirk example to legacy paths (src dev instantiates neopixel) [partly]
- G9.049 | U1 | doc-fix | dev_legacy/README.md "current single source of truth" claim; bench facts move to tests_hardware/README.md [drifted]
- G9.050 | U1 | code-fix | move update_and_install.txt to `legacy/firmware/`; drop its BACKLOG entry [drifted]
- G9.054 | U1 | doc-fix | SPEC A.3/B.9/B.11, CLAUDE.md, README, BACKLOG stop framing legacy lint/CI/path work as open [drifted]
- G9.055 | U1 | rule-write | legacy/README.md records the six post-import agent edits (behavioural `2bda920`) [partly]

### U2 — B1 errno/wrnno catalog (6)

- G5.023 | U2 | code-fix | catalog test checks every call site's number fits one byte; sentinel 0x80 not reported as ErrNum 128 [partly]
- G5.024 | U2 | code-fix | renumber the clashing NTP/ConnTime/Notification wrnno vs base_classes in the global catalog [drifted]
- G5.042 | U2 | code-fix | `handle_set_cmd` errno 99 collides with FRAM_SPI's; post-persist hook failure reports landed fields [partly]
- G6.064 | U2 | code-fix | NTP docstring "starts at 11"; webserver wrnno 2 used twice; range-sweep tests per module [drifted]
- G9.032 | U2 | test-add | catalog test over table, code and tests; supervisor `wrnno=n+1` per-device number [partly]
- G10.015 | U2 | code-fix | one error-number idiom and prefix in the catalog pass [partly]

### U3 — B1 central log-repeat rule (5)

- G3.062 | U3 | decide | [q] alternating errno 11/1 per failed read defeats the newest-entry rule: accept, stop per-streak errno 1, or collapse last-two repeats? (G3 Q1) [holds*]
- G3.066 | U3 | code-fix | [q] SGP40 W13 per-module slot rule replaced by the central rule [holds*]
- G5.025 | U3 | code-fix | implement the central repeat rule in `print_log.py`; rewrite C.7.1's repeat paragraph [drifted]
- G6.022 | U3 | decide | UART E/W fault pairs under the central repeat rule: exception, compare per kind, or two slots per fault? (G6 Q1) [drifted]
- G6.045 | U3 | code-fix | NTP errno 18 per tick and captive DNS wrn_s repeats through the central rule [partly]

### U4 — B1 compare-before-write primitive (5)

- G1.006 | U4 | code-fix | SCD30 PUT onto the shared compare-before-write primitive so unchanged/rejected fields persist nothing; drop the marker on the all-invalid PUT (test_hotspot_role_reversal.py:382) [partly]
- G1.045 | U4 | doc-fix | SPEC C.8/E.6.6/README "no PUT reaches SCD30 NVM" is wrong (`_set_dict_cfg()` writes NVM) [wrong]
- G3.070 | U4 | code-fix | SCD30 NVM setters compare-before-write via the shared primitive; drop SPEC's `force=True` text [drifted]
- G5.043 | U4 | code-fix | SCD30 onto the shared primitive; recovery write result checked, not discarded [partly]
- G9.062 | U4 | code-fix | SCD30 compare-before-write through the shared primitive (legacy compared in intent only) [partly]

### U5 — B1 config objects and max-args (2)

- G8.125 | U5 | code-fix | lower `max-args` to 8 (OR46.b) and enforce the ratchet [wrong]
- G10.042 | U5 | code-fix | constructor tail order in SensorReader, SystemService, SGP40_Reader with the config objects [partly]

### U6 — B1 one-source website definitions (9)

- G3.086 | U6 | code-fix | UI texts/DEVICE_REFERENCE and trigger-bound mirrors generated or agreement-checked [partly]
- G7.004 | U6 | doc-fix | C.11 item 9 "update html/definitions" contradicts OR43.a (3); one checklist step [drifted]
- G7.052 | U6 | test-add | cross-language pins: `_shape_problems` vs `validateDefinitions()`, schema major vs version [partly]
- G7.054 | U6 | code-fix | one derived dispatch-only set replaces five hand lists (H.4, H.6, mock-server, _put_field_cases) [drifted]
- G7.055 | U6 | code-fix | retire hand-written `html/definitions/{wozi,dev}.json`; one provenance statement in H.5.1 [drifted]
- G7.056 | U6 | code-fix | `js/app.js` KNOWN_DEVICES, package.json wozi-only build, live tier derive devices from devices/*.toml; README claim [wrong]
- G7.057 | U6 | code-fix | mockdata/dev.json carries exactly dev.toml's fields (SHTC3/MPRLS out, BMP3XX/UART rows in) [wrong]
- G8.045 | U6 | code-fix | golden-file comparison order-sensitive; hand files retired [partly]
- G9.026 | U6 | doc-fix | H.5 vs K.4/K.8 on hand-written definitions: one statement once the files retire [drifted]

### U7 — B1 tier ladder and runner summary block (6)

- G1.041 | U7 | code-fix | skip inventory: unconditional "pending" skip whitelisted as permanent; missing-UART skips surface in the summary block [partly]
- G1.044 | U7 | doc-fix | E.6.6 exception 1 wrong for SCD30; scenario containment measured by the ladder (OR45.a) [partly]
- G1.048 | U7 | code-fix | a reset-recovery pass is reported in the summary block; WIFI-log check not skipped on the reset path [partly]
- G2.055 | U7 | code-fix | skips visible in the summary; JS warn-and-return skips; one policy for missing node [partly]
- G2.061 | U7 | test-add | measure scenario containment across backends (OR45.a) [partly]
- G8.090 | U7 | code-fix | verdict whitelist exact-match; truncated NOTE sentence [partly]

### U8 — B1 @tunable scheme (8)

- G1.068 | U8 | code-fix | tag hardware-tier timings `@tunable` with basis and margin [partly]
- G2.048 | U8 | code-fix | test timing values tagged `@tunable` with register entries [partly]
- G4.080 | U8 | code-fix | test allocation/time budgets become `@tunable` entries [partly]
- G6.060 | U8 | code-fix | NTP time window `@tunable` with a re-check trigger [partly]
- G6.062 | U8 | code-fix | register `_GC_PAUSE_WORST_MS` and the WiFi 5 s/3 s settles with reasons [partly]
- G7.038 | U8 | code-fix | twin durations/tolerances `@tunable`; E.7 figures re-measured against the current runner [partly]
- G8.076 | U8 | code-fix | parallelism bands `@tunable`, calibrated on the Pi4; safe probe-failure fallback [partly]
- G8.113 | U8 | code-fix | CI time budgets `@tunable`; B.10.1 retry budget stale [partly]

### U9 — B2 pilot LED (1)

- G3.092 | U9 | code-fix | Neopixel duration ceiling and non-numeric colour handled at the driver; fake models the raise [partly]

### U10 — B2 XCUT (39)

- G3.063 | U10 | code-fix | a failed trigger-timer arm is re-armed or escalated, not silent until reboot; comment corrected [drifted]
- G4.030 | U10 | code-fix | repo-wide non-finite JSON gate (XCUT.T23); loader tolerant of both omitted-value behaviours [partly]
- G5.005 | U10 | decide | restore D.15's 2026-09-13 owner amendment dropped by merge e5d2c43, then reorder 18 classes? (OR13.a) [drifted]
- G5.006 | U10 | decide | static-import rule: firmware only or whole repo (twin/tests/buildgen dynamic imports)? [drifted]
- G5.011 | U10 | code-fix | `_timer_sequencer()` callback failures reach a persisted log (deferred from the Timer context) [partly]
- G5.014 | U10 | test-add | check logger-less teardown bool contract beyond the three named sites [not checked]
- G5.017 | U10 | test-add | per-class readiness-gate (`initialized`) contract check [not checked]
- G5.021 | U10 | code-fix | logger store setup into the boot batch before any persisted log (OR47.a); A.7 once [partly]
- G5.044 | U10 | test-add | per-setter bool/once-registration check [not checked]
- G5.048 | U10 | code-fix | single runtime feed site test; worst-case boot inter-feed step computed; `setup()` returns checked [partly]
- G5.050 | U10 | doc-fix | A.2/tests_hardware README/BACKLOG "stops feeding" wording vs `reboot_system()` then return [drifted]
- G5.057 | U10 | code-fix | four ONE_SHOT timers doing real work reviewed against C.9/F.1; one wording [drifted]
- G5.058 | U10 | code-fix | stagger computed from a common start, not accumulated one-shots; proof test runs the real sequencer [partly]
- G5.060 | U10 | code-fix | implement the one standard timeout mechanism for wrappable calls; F.2 states it [partly]
- G5.086 | U10 | doc-fix | stored-tick sites vs "same bounded-short-timeout shape" docstring [partly]
- G5.096 | U10 | test-add | mechanical lock-order guard [not checked]
- G6.086 | U10 | test-add | mechanical finite-value check per route [partly]
- G9.030 | U10 | doc-fix | FRAM-backed logger list adds isl29125 and becomes one SPEC A.7 list cited by CLAUDE.md [drifted]
- G9.048 | U10 | decide | restore D.15's dropped amendment ("comments move with code") and run the reorder under OR24 (same question as G5.005) [drifted]
- G10.001 | U10 | code-fix | `asy_` prefix scheme for all async modules (8 of 27 deviate); rule in C.2 [partly]
- G10.002 | U10 | code-fix | module/primary-class name mapping (`AsyConnTime`); rule in C.2 [partly]
- G10.004 | U10 | code-fix | one compound class-name scheme; N801 comment [partly]
- G10.009 | U10 | decide | rename legacy-spelled config keys to one scheme before the release freezes them? (G10 Q2) [drifted]
- G10.013 | U10 | code-fix | 6 literal config-key sites through the schema tuple [partly]
- G10.014 | U10 | code-fix | ~9 eligible plain constants to private `const()`; F.5.6 count 21→26 [partly]
- G10.019 | U10 | code-fix | one raised-message style; rule in C.3 [partly]
- G10.020 | U10 | code-fix | one exception-tuple order; rule in D.10 [partly]
- G10.025 | U10 | code-fix | apply annotation quoting everywhere; drop D.6's not-mass-edited clause [partly]
- G10.029 | U10 | code-fix | 3 src/ per-function docstring exceptions; one D.11 rule, CLAUDE.md points [partly]
- G10.033 | U10 | code-fix | one lock-attribute naming style; rule in C.8 [partly]
- G10.034 | U10 | code-fix | locks acquired with `async with` everywhere; rule in C.8 [partly]
- G10.035 | U10 | code-fix | 6 bare `asyncio.Lock()` sites use the Locked primitives or state why [partly]
- G10.037 | U10 | code-fix | one task/timer starter shape and naming in C.9 [partly]
- G10.038 | U10 | code-fix | task coroutine naming beyond `read_loop()` [partly]
- G10.039 | U10 | code-fix | three callbacks doing work (reset action, sequencer re-arm, storage unpause) only set a flag [partly]
- G10.041 | U10 | code-fix | one unit-suffix spelling in identifiers and TOML keys [partly]
- G10.044 | U10 | code-fix | uniform `setup()` return contract [partly]
- G10.045 | U10 | code-fix | reorder ~10 classes per D.15; setup/reset categorised [partly]
- G10.076 | U10 | code-fix | `asy`-marking of identifiers one scheme; rule in C.2 [partly]

### U11 — B2 CORE (16)

- G1.093 | U11 | doc-fix | trace mempause 300 s value; record window/cap in SPEC A.7 [partly]
- G4.025 | U11 | code-fix | byte-order prefixes on `print_log.py:234` and `voc_algorithm.py:141` formats [partly]
- G5.012 | U11 | code-fix | swallowing excepts in fram timestamp unpack, schema parse, print_log FRAM I/O leave a trace [partly]
- G5.020 | U11 | doc-fix | C.6 `make_dict()` "via repr()-parsing" is stale; audit `None`-initial half [partly]
- G5.029 | U11 | decide | first-boot missing config file persists wrnno 3 (and 6 for command-only) against the 2026-09-12 no-warning principle — print-only for missing, persisted for corrupt? (G5 Q5) [partly]
- G5.034 | U11 | decide | CLAUDE.md "flash writes only via REST PUT" vs ConfigManager's boot repair write — reword the hard rule to "user changes or boot repair"? (OR13.a) [drifted]
- G5.037 | U11 | test-add | golden full-schema fixture test for ConfigManager construction [partly]
- G5.038 | U11 | test-add | pin the int→float coercion bound; README.md:611-612 corrected [drifted]
- G5.039 | U11 | doc-fix | [q] config_manager.py:126-127 says `lightCmdLED` dispatch has no FieldSchema (it uses synthetic ones) [holds*]
- G5.040 | U11 | code-fix | a malformed default no longer aborts `write_config()`'s per-key results [partly]
- G5.045 | U11 | code-fix | command-only schema creates no empty config file on flash [partly]
- G5.055 | U11 | code-fix | boot signature and uptime survive a supervisor restart (`status_counter()` resets them) [wrong]
- G6.041 | U11 | code-fix | config_manager.py:185 `pass` catch logs [partly]
- G7.085 | U11 | doc-fix | README.md:605-607 "int for float rejected" contradicts `coerce_numeric()` [drifted]
- G10.017 | U11 | doc-fix | C.4 log call example passes `_NAME` (0 of 209 calls do) [drifted]
- G10.079 | U11 | code-fix | config file/logger name built in one place (1 duplicate) [partly]

### U12 — B2 ALGO (7)

- G3.004 | U12 | test-add | pin CRC exact-length blind spot [partly]
- G3.007 | U12 | code-fix | `rel_humidity()` clamp vs reject policy (no production caller: align or remove) [partly]
- G3.008 | U12 | decide | Stull/McCamy validity domains unverifiable — can the owner supply the papers, or accept code bounds as-is? [partly]
- G3.012 | U12 | doc-fix | VOC docstring names the reachable Sensirion reference [partly]
- G3.013 | U12 | code-fix | fixed-point shifts reproduce C int32 (overflow return, `_FIX16_MINIMUM`); reference-vector test [partly]
- G3.014 | U12 | code-fix | `"32q"` gets a byte-order prefix; restored VOC state validated [partly]
- G5.080 | U12 | decide | CRC empty-payload asymmetry: fix inside crc_checks.py despite the "not to be modified" ruling, or forbid zero-length payloads at callers? (G5 Q6) [partly]

### U13 — B2 BUS (5)

- G3.028 | U13 | doc-fix | asy_spi_driver.py:61-67 guard caller claim (session_begin too) [drifted]
- G3.029 | U13 | rule-write | missing I2C between-session yield asymmetry recorded in SPEC G.2 [partly]
- G3.030 | U13 | code-fix | `readline()`/`readline_until_complete()` call `uart.readline()` unclamped (blocks the loop) [partly]
- G6.025 | U13 | code-fix | enforce single-digit `poll_wait_ms` (driver default 20 ms) [partly]
- G10.046 | U13 | code-fix | `I2CDevice`/`SPIDevice` get `read()` pairs or G.2 narrows [partly]

### U14 — B2 PLAT (16)

- G1.039 | U14 | doc-fix | trace modlwip's NULL-pcb path at v1.29.0 and confirm H.7.1's probe-shape claim [not checked]
- G2.020 | U14 | doc-fix | CLAUDE.md/SPEC nested-asyncio.run mechanism is wrong at v1.29.0 (same queue, re-entrant scheduling) [partly]
- G2.049 | U14 | test-add | tick-subtraction scan covers generated modules and digital_twin/; real 2**30 rollover test [partly]
- G2.051 | U14 | rule-write | record Unix-port quirks (#6924, gmtime length) in Part F with removal triggers [partly]
- G3.011 | U14 | decide | test float32 off-silicon with a single-precision Unix-port build, or prove on L3 only? (G3 Q3); Part F.1 fact written either way [partly]
- G3.024 | U14 | doc-fix | SPEC C.12 "never ENODEV" wrong for zero-length writes; fakes' model follows [wrong]
- G4.003 | U14 | doc-fix | one Part F home per platform fact: mktime "~2037" (6 comments), print_log CLAUDE.md pointer, 1.28.0 stamp [partly]
- G4.035 | U14 | doc-fix | SPEC F.1 const() attribute claim holds only for `_`-prefixed names; check float const precision [wrong]
- G4.036 | U14 | doc-fix | SPEC F.5.3 `-fno-math-errno` "hardware sqrt" claim (M0+ has no FPU) [drifted]
- G4.037 | U14 | doc-fix | test_ticks_rollover.py range comment excludes `-period/2` [partly]
- G4.038 | U14 | doc-fix | seven src/ comments + two tests: rp2 epoch range ends 2106, not ~2037; one Part F fact [wrong]
- G4.042 | U14 | doc-fix | verify WLAN key/SSID exception types at source; record in Part F [partly]
- G4.047 | U14 | test-add | [q] static proof that lwIP MEM_SIZE covers every admitted connection's worst tcp_write (10 s stall > 8 s WDT, OR49.a) [holds*]
- G4.083 | U14 | doc-fix | SPEC I.1 "roughly half the 264KB" CYW43 heap wording [partly]
- G6.040 | U14 | doc-fix | F.5.5 "the one place a type: ignore is right" vs 20 others [drifted]
- G6.054 | U14 | doc-fix | verify wrnno 4 semantics against cyw43-driver source (submodule not checked out) [unverifiable]

### U15 — B2 SENS (27)

- G3.020 | U15 | doc-fix | SPEC:243-245 TempOffs "truncated by the chip" is the driver's `int()` [drifted]
- G3.022 | U15 | code-fix | SCD30 datasheet range gate (finiteness only today) [partly]
- G3.039 | U15 | code-fix | SGP40 serial reads all 3 words per datasheet §3.4; undocumented `word[0]==0` check; SCD30 firmware-version check [partly]
- G3.040 | U15 | doc-fix | BMP3xx docstring adds BMP390 sheet; hazard catalog seeds both addresses [drifted]
- G3.041 | U15 | code-fix | remove unused `_wait_time`, source `_CMD_RDY_TIMEOUT_MS`, IIR reserved-code note [partly]
- G3.042 | U15 | doc-fix | check AN006 for trim bounds; update "doesn't have the exact values" [partly]
- G3.044 | U15 | decide | [q] does "never stale as fresh" bind every driver or only ISL29125 (config-read-failure defaulted sample, SCD30 not-ready reuse)? (G3 Q2) [holds*]
- G3.045 | U15 | code-fix | drop ISL29125's test-only address parameter and its wrong "as BMP3XX's" comment (harmonization 10) [drifted]
- G3.046 | U15 | doc-fix | reconcile the Table 7 CONFIG1-restart citation across the unit test, flash test and device script [drifted]
- G3.052 | U15 | code-fix | `set_autorange_thresh()` writes the chip threshold registers, not only the cache; rescale outside RangeAuto [partly]
- G3.060 | U15 | code-fix | ISL29125 config-read-failure and bounded-settle paths must not publish stale samples as fresh [partly]
- G3.064 | U15 | code-fix | log the silent swallows in ISL29125 helpers (:436, :488, :1302) [partly]
- G3.079 | U15 | code-fix | SGP40 compensation out-of-range values rejected, not wrapped by `& 0xFFFF` [partly]
- G3.081 | U15 | code-fix | SGP40 backup: reject negative ages, stop per-second chunk re-read before NTP; "0 means" into C.5 [partly]
- G3.087 | U15 | code-fix | constructor divergences and a name-rule test; C.14.1 "three drivers" count [partly]
- G3.088 | U15 | code-fix | SCD30 runtime `cast()` shim replaced by the settled identity-return shape [partly]
- G4.024 | U15 | code-fix | SGP40 compensation values validated finite through the shared numeric primitive [partly]
- G8.036 | U15 | code-fix | ISL29125 `address` parameter exists only for test injection — remove (OR36, harmonization 10) [partly]
- G9.065 | U15 | doc-fix | re-read SCD30 tick period and publication tuple; record in C.9.1 [not checked]
- G9.066 | U15 | doc-fix | state SGP40 100 ms / 500 ms wait margins against datasheet maxima in Part M [partly]
- G9.067 | U15 | code-fix | `WaitTimeNTP = 0` restores at once (voc_init start 1 as legacy) [wrong]
- G9.068 | U15 | doc-fix | check SGP40 blackout against legacy; DEVICE_REFERENCE semantics [partly]
- G9.070 | U15 | decide | SGP40 general-call reset on every task restart is new vs field units — keep it? [partly]
- G9.073 | U15 | doc-fix | re-read BMP3xx poll bound and conversion mode against legacy; record in Part M [not checked]
- G10.006 | U15 | code-fix | [q] four byte-identical DeviceSession copies become one Part G.2 primitive; C.2 reworded [holds*]
- G10.024 | U15 | code-fix | remove SCD30's runtime typing shim; C.4.2 made consistent [drifted]
- G10.067 | U15 | code-fix | SCD30 `trigger_sec` gets `@limits` (TOML `trigger_sec = 0` passes) [partly]

### U16 — B2 STOR (8)

- G4.066 | U16 | code-fix | FRAM chunk buffers and persisted log entries reuse long-lived buffers (no per-call `AsyFramChunkBuffer`) [partly]
- G5.062 | U16 | doc-fix | drop "identical across firmware versions" (SPEC :216, :379, test comment); machine-check A.7 chunk list [drifted]
- G5.065 | U16 | code-fix | [q] `PrintLogHistoryStore.setup()` writes an empty ring on a transient boot read fault (history lost) [holds*]
- G5.068 | U16 | doc-fix | test_fram_integration.py "SPI cannot raise" comment vs F.5.2; absorb setup-time transient read fault [drifted]
- G5.069 | U16 | code-fix | `setup()`/`set_write_protected()` hold the FRAM lock around shared scratch [partly]
- G5.076 | U16 | code-fix | remove test-only `override_pause` from FRAM APIs (OR36) [partly]
- G5.077 | U16 | code-fix | pack-guard message; document or reject negative ages [partly]
- G9.088 | U16 | test-add | first-boot-after-reflash FRAM/VOC graceful case (OR47.a) [unverifiable]

### U17 — B2 UART (4)

- G6.002 | U17 | test-add | check that a UART `const()` change has a changelog entry; one scope wording [drifted]
- G6.018 | U17 | code-fix | `_holdoff_active` stale-deadline after >6.2 days idle; F.1 "every use short" corrected [partly]
- G7.003 | U17 | code-fix | remove `self.uart` twin comment/public seam; twin stops reading private `_i2c`/`_spi` [partly]
- G9.033 | U17 | doc-fix | changelog status values within the stated set [partly]

### U18 — B2 NET (10)

- G4.022 | U18 | code-fix | `asy_udp_socket.ready()` idles at a slow rate for undeadlined captive-DNS waits (50 Hz today) [partly]
- G4.043 | U18 | code-fix | name CYW43 magic literals with their source [partly]
- G6.033 | U18 | code-fix | remove test seams (`_FALLBACK_DNS_SERVERS`, `_NTP_UDP_PORT`, public `self.uart`, non-tuple addr) (OR36) [drifted]
- G6.043 | U18 | code-fix | NTP/DNS check and log `disconnect()`; NTP fetch disconnects in `finally` [partly]
- G6.050 | U18 | code-fix | QNAME 255-octet and empty-label checks in `_build_query()` [partly]
- G6.056 | U18 | code-fix | PUT of the mask string must not store it as the password [partly]
- G6.057 | U18 | code-fix | NTP check timer and uptime counters retry a failed arm [partly]
- G6.063 | U18 | code-fix | AP-mode `rssi` error on every `/status`; `STAT_GOT_IP` branch [partly]
- G6.080 | U18 | doc-fix | five NET workarounds state removal triggers; verify the `stations` 100 ms sleep [partly]
- G9.079 | U18 | doc-fix | re-read NTP retry cadence and "stale" rule against legacy [not checked]

### U19 — B2 REST (9)

- G4.067 | U19 | doc-fix | record the ~1,026 B NTP_Host piece as the stated bound (or split it) [partly]
- G4.087 | U19 | decide | F18: are zero-think-time concurrent FRAM-log readers in contract (3 readers reach 88-98 % of the 15 s cap)? [partly]
- G6.074 | U19 | code-fix | negative Content-Length guarded before `readexactly`; headroom counts bytes and untagged fields [partly]
- G6.079 | U19 | code-fix | unknown sensor key gets "Invalid"; `lightCmdLED` malformed payload "Invalid" [drifted]
- G6.085 | U19 | code-fix | `_PieceWriter` counts bytes, not characters [partly]
- G6.087 | U19 | decide | F18/BACKLOG #24: ResetErrors sweep near the 15 s cap at three readers — in contract? [partly]
- G10.010 | U19 | code-fix | one REST JSON key casing (four today); rule in A.8 [partly]
- G10.073 | U19 | code-fix | remove the firmware `assert` (asy_webserver_service.py:653) and its S101 ignore [partly]
- G10.078 | U19 | code-fix | envelope `code` one space; remove two dead catalog entries [partly]

### U20 — B2 GEN (28)

- G2.066 | U20 | test-add | per-tag-family full-accept/single-reject completeness (OR23) [not checked]
- G2.067 | U20 | code-fix | fixture writer emits inline tables so the dict `led_target` case runs [partly]
- G5.041 | U20 | test-add | schema-lint check (swapped bounds, duplicate/non-string names, wrong-typed bool special) [partly]
- G5.047 | U20 | code-fix | WDT created before the `sensortask_<device>` import in the generated boot entry [partly]
- G5.071 | U20 | doc-fix | driver "can tell which part" overstatement; four TOMLs name the FRAM part [partly]
- G8.002 | U20 | code-fix | new tag families register for the near-miss check mechanically [partly]
- G8.005 | U20 | code-fix | raw ValueErrors in schema_ast/twin_wiring become BuildError; `codegen.py:382` handles absent `bus` [partly]
- G8.006 | U20 | code-fix | generator writes atomically and prunes stale `build/generated_src/` [partly]
- G8.010 | U20 | test-add | agreement test for build-side copies of `_HOSTNAME_MAX_LEN`, `_NTP_CHECK_TICK_S`, `_WPA2_*` [partly]
- G8.011 | U20 | test-add | agreement test for `_KNOWN_SIGNALS`, `_WARN_SIGNAL_WEB_CATALOG`, `_SENSOR_DRIVERS` [partly]
- G8.012 | U20 | test-add | pin `FIXED_ADDRESSES` to driver defaults; L.4 list adds isl29125 [partly]
- G8.013 | U20 | test-add | `@web-group` test asserts the full group set [partly]
- G8.014 | U20 | code-fix | codegen reads `led_target`'s setter from the tag; fram exclusion from collectors not by hand [partly]
- G8.015 | U20 | code-fix | generated functions/bound-method sink: remove or name as exceptions in L.2 [partly]
- G8.017 | U20 | code-fix | `CORE_MODULES` tied to codegen imports; `TYPE_CHECKING` else-branch scanned; stale seeds fail [partly]
- G8.019 | U20 | code-fix | defaults read keyword-only parameters [partly]
- G8.020 | U20 | code-fix | `_check_source_field_reference` checks `field` as L.6.3 claims (GEN.S06) [wrong]
- G8.021 | U20 | code-fix | type-guard `irq_pull_up` [partly]
- G8.026 | U20 | code-fix | `pico_gpio.py` accepts every Table 279 function (GP22/28 I2C, GP20-22/26-28 SPI, UART1 20/21); comments corrected (OR53) [wrong]
- G8.027 | U20 | code-fix | `{source}` edge and `warn_*` accepted only on their owning instances [partly]
- G8.028 | U20 | code-fix | version test's `.dev`/patch promise vs `_VERSION_RE`; bump needs no test edit [partly]
- G8.029 | U20 | code-fix | WDT first in the boot entry before the device import; feed check asserts never-in-loop [partly]
- G8.034 | U20 | test-add | per-driver device allow-lists for every driver [partly]
- G8.039 | U20 | test-add | wiring-plan contract test (instances, `i2cN` shape) [partly]
- G8.040 | U20 | code-fix | [q] untagged/unresolvable schema field fails the build instead of silently leaving the website (OR16, OR43.a (2)) [holds*]
- G8.042 | U20 | test-add | one test reads the decimals bound on both sides [partly]
- G10.027 | U20 | code-fix | one annotation-evaluation mode for host code (55 of 210); rule in L.5 [partly]
- G10.068 | U20 | code-fix | module identifier across name spaces generated from one copy [partly]

### U21 — B2 TOOL (14)

- G1.082 | U21 | code-fix | verify/provision the bench sudo rules in `env --tier bench` [not checked]
- G4.001 | U21 | code-fix | `--latest`/`write_micropython_ref()` prompt the Part F re-check checklist when the pin moves [partly]
- G5.089 | U21 | code-fix | setup_toolchain.py stops echoing `wifi-sec.psk` argv and printing the password; history secret scan [partly]
- G8.046 | U21 | code-fix | pin picotool and stub `.postN`; F.1/update_and_install.txt 1.26 coupling stale [partly]
- G8.047 | U21 | code-fix | `--latest`/`--micropython-ref` announce the re-check; `write_micropython_ref()` fails when no `ref =` matches [partly]
- G8.050 | U21 | code-fix | post-build readback of the SIGINT override; cache key includes micropython_overrides.py [partly]
- G8.054 | U21 | code-fix | `sudo env` apt call keeps proxy variables; allowlist `PIP_CERT` [partly]
- G8.055 | U21 | code-fix | mpy-cross output grepped for errors too [partly]
- G8.056 | U21 | code-fix | mbedtls array-bounds flag scoped to mbedtls only; confirm vendored version [partly]
- G8.061 | U21 | code-fix | `ensure_bench_bridge()` creation and channel self-heal arm the dead-man's switch; README recipe [partly]
- G8.064 | U21 | code-fix | bench password out of nmcli argv; README literal example removed [partly]
- G8.066 | U21 | code-fix | sysctl temp file cleaned when `sudo cp` fails; host side effects stated [partly]
- G8.068 | U21 | code-fix | Node patch pinned, checksum/signature, StopIteration default; `@types/node` vs .nvmrc; `engines` [partly]
- G8.069 | U21 | code-fix | lock against concurrent builds in one toolchain dir [partly]

### U22 — B2 LED re-check (1)

- G9.082 | U22 | doc-fix | check LED arbitration against legacy (LED.S03/T01) [not checked]

### U23 — B2 WEB (26)

- G2.026 | U23 | code-fix | live matrix computes expected captions independently of `formatFieldValue()`; D.12 reworded [partly]
- G5.091 | U23 | code-fix | eslint rule forbidding innerHTML; hostile keys reaching selectors/ids tested [partly]
- G7.049 | U23 | code-fix | src↔js divergences: radio string bounds, unknown `/sensors` sub-key, post-write gap [partly]
- G7.050 | U23 | test-add | mock backend field-for-field pins as tests; unknown sub-key, composites [partly]
- G7.051 | U23 | code-fix | client fails loud on a renamed key; `_` in sensor names; `ResetErrors=false` shown as Valid [partly]
- G7.053 | U23 | code-fix | client clock/abort vs server accept; bounded `response.text()` [partly]
- G7.058 | U23 | code-fix | staging guard parses imports, covers subdirectories and non-.js files [partly]
- G7.059 | U23 | code-fix | de-duplicate `selectSection()` (app.js/main.js) [partly]
- G7.060 | U23 | code-fix | build_website.sh checks import order as H.2 claims (templates.js before definitions.js) [drifted]
- G7.063 | U23 | code-fix | startup loads through the poll queue; abort on section switch, hidden-tab pause [partly]
- G7.064 | U23 | doc-fix | H.8 "only failure diagnostic, asserted" vs `fetchOnce()` never rejecting [drifted]
- G7.065 | U23 | code-fix | validate field kind/key/label; null group and null field reported [partly]
- G7.066 | U23 | code-fix | number/string fields sparse-omitted when equal to baseline (OR42.a); whitespace/hex input rejected [drifted]
- G7.068 | U23 | doc-fix | mock/render.js/render.test.js "server-side gap" comments; mock drops whole group [drifted]
- G7.069 | U23 | code-fix | `templates.js:245` silent `{counter:0}` fallback; rollup vs row colour; focus retention [partly]
- G7.074 | U23 | decide | Apply-failure website divergence from legacy decided by a session agent (OR48.a (2)) — keep it? [partly]
- G7.076 | U23 | code-fix | show `/system` `build` in the GUI; H.1 "all met" rechecked for four generated sites [partly]
- G7.080 | U23 | decide | [q] timezone fields on the System or Networking page? (G7 Q1) [holds*]
- G7.082 | U23 | code-fix | validate the built page, not only html/**; check the bootstrap's `startApp` argument [partly]
- G7.083 | U23 | code-fix | in-place caption refresh through `resolveFieldValue()`; baselines refreshed after write [partly]
- G7.084 | U23 | code-fix | remove test-only `pollManager.isBusy` (OR36) [wrong]
- G7.086 | U23 | code-fix | website string bounds count UTF-8 bytes like `asy_wifi_service.py`; C.7.4 states both sides [wrong]
- G9.028 | U23 | code-fix | render `/system` `build` or state its exclusion in L.7/H [drifted]
- G9.084 | U23 | test-add | page-by-page legacy function check [not checked]
- G10.049 | U23 | doc-fix | `LIGHT_CMD_LED_*` cite generated sensortask; 5 references [drifted]
- G10.052 | U23 | doc-fix | H.3 controller contract text covers the real hooks [drifted]

### U24 — B2 TEST (43)

- G2.005 | U24 | code-fix | microtest fails a 0/0 file; trailer and ALL_CHECKS completeness enforced [partly]
- G2.006 | U24 | code-fix | coverage runner dumps on any escape; footerless file fails both runners [partly]
- G2.008 | U24 | code-fix | tests_scripts/conftest and JS live twin probe the binary variant; fix settrace claim in test_asy_fram_allocation_budget.py [partly]
- G2.013 | U24 | code-fix | test_asy_webserver_service.py:1833 absolute 4096 B drop becomes a rate bound [partly]
- G2.015 | U24 | code-fix | TmpScratch key-uniqueness check; `_tmp_scratch.py` swallows only expected errnos [partly]
- G2.016 | U24 | code-fix | reserved-prefix guard covers every writer; JS harnesses stop `rmSync` of shared digital_twin/config [partly]
- G2.017 | U24 | code-fix | port bands: E.1 vs `_webserver_concurrency_scenarios.py:77` drift; add a port-map check [partly]
- G2.018 | U24 | code-fix | clear the fake Timer class list; remove twin `machine` from sys.modules after test_buildgen_twin_wiring [partly]
- G2.019 | U24 | test-add | mechanical check that no task stays parked after a test [partly]
- G2.021 | U24 | test-add | enforce bounded fake pollers for every fake stream [partly]
- G2.024 | U24 | code-fix | ISL29125/UART starters through `_sensor_reader_owners()` and the real SystemService chain [partly]
- G2.027 | U24 | code-fix | concurrency scenarios check response completeness; twin HTTP client rejects EOF mid-headers [partly]
- G2.028 | U24 | code-fix | strict JSON checker rejects duplicate keys; every emitted-JSON test uses it [partly]
- G2.030 | U24 | test-add | sensor-fault-never-500 test proves the fault is consumed and checks values [partly]
- G2.031 | U24 | code-fix | fakes: `pull` honoured or gap stated; dev's FRAM fake models 256 KB/3-byte addressing [partly]
- G2.032 | U24 | test-add | fake semantics checked against rp2 source; FRAM WEL claim backed [partly]
- G2.033 | U24 | code-fix | machine fakes accept `pull=None`; webserver fake no richer than the real class [partly]
- G2.035 | U24 | decide | twin fakes: independent copies held by contract tests, or one shared implementation? (G2 Q2) [partly]
- G2.039 | U24 | test-add | tests_scripts const-mirror check (22 sites incl. `_PHASE_HOTSPOT`, UART Class A copies) [partly]
- G2.040 | U24 | code-fix | single-source duplicated test values (BMP calibration value ×3, mockdata coverage) [partly]
- G2.041 | U24 | code-fix | shared `_RaiseOnArm`/`_FastAsyncSleep` helpers; drop citation of a nonexistent self-containment convention [drifted]
- G2.042 | U24 | code-fix | Python test tiers derive the device set (test_build_firmware wozi/dev, per-driver sets) [partly]
- G2.043 | U24 | code-fix | bare vitest/Unix-port runs regenerate or refuse stale generated code [partly]
- G2.044 | U24 | doc-fix | CLAUDE.md vs SPEC C.8 mock-tier placement; generated hazard scheme I2C-only, first writer only [partly]
- G2.058 | U24 | code-fix | coverage of generated sensortask modules; pin coverage.py internals used by the renderer [partly]
- G2.063 | U24 | code-fix | only a reset counts as clean refusal; timing-dependence claim vs assertion [partly]
- G2.070 | U24 | doc-fix | [q] CLAUDE.md "~157 method-assign sites" count (201 at HEAD) dropped [holds*]
- G3.085 | U24 | code-fix | field-name test binds each driver to its own NamedTuple; ISL29125 wire keys from `_FIELDS` [partly]
- G4.028 | U24 | doc-fix | two test comments claim bool is an int subclass in MicroPython [drifted]
- G4.040 | U24 | code-fix | RTC fake recomputes weekday [partly]
- G6.081 | U24 | code-fix | hand copies (dispatch list, route shape, wire offsets, NTP window) taken from source [partly]
- G7.032 | U24 | test-add | pin `_NTP_ERRNO_NO_REPLY` and `_WIFI_SCRIPTED_FAILURES` to source [partly]
- G8.033 | U24 | code-fix | 12 per-device wrapper tests and literal CI matrices derived (L.1/L.2 claims) [drifted]
- G8.038 | U24 | test-add | execute the generated boot entry (threshold, import, finally) in a tier; stronger generated-boot assertions [partly]
- G8.092 | U24 | code-fix | lock/taken-port check for fixed ports 18080/53 [partly]
- G8.104 | U24 | code-fix | ResetErrors single-site guard AST-based [partly]
- G9.027 | U24 | code-fix | six hand-written `test_sensortask_<device>.py` and "6 real"/"all six" literals derived [partly]
- G9.041 | U24 | test-add | mechanical check that `asyncio.run()` helpers are called only from sync scope [unverifiable]
- G10.057 | U24 | test-add | test files for `pico_gpio` and the four buildgen modules tested only indirectly [partly]
- G10.060 | U24 | code-fix | shared test primitives in tests/ named in G.1; shared `run` [partly]
- G10.061 | U24 | code-fix | one test-double naming scheme; rule in Part E [partly]
- G10.062 | U24 | code-fix | `_DEVICES` 6-tuples, 18 wrappers, `["wozi","dev"]` literals derived [partly]
- G10.063 | U24 | code-fix | test_micropython_overrides.py classes to module-level tests [partly]

### U25 — B2 TWIN (28)

- G2.037 | U25 | code-fix | `settle()` busy-wait with `time.sleep_us()` [partly]
- G2.047 | U25 | code-fix | Python twin readiness waits poll instead of fixed sleeps [partly]
- G2.062 | U25 | code-fix | `_webserver_concurrency_scenarios.py` client leaves the DUT heap (OR20.a) [partly]
- G2.068 | U25 | code-fix | verify twin boots never resolve pool.ntp.org via asy_dns_client's public fallback [partly]
- G3.071 | U25 | code-fix | twin `_scd30_chip.py` and mock server model FRC readback as volatile per datasheet [wrong]
- G4.057 | U25 | code-fix | twin/fakes cite source for UART constants; model NeoPixel blocking/colour order; twin Timer accepts `freq=` [partly]
- G5.028 | U25 | doc-fix | digital_twin/README.md:505-507 boot-window ResetErrors claim [drifted]
- G7.002 | U25 | code-fix | no-tests/-on-path guard covers tests_scripts and tests_js twin launches [partly]
- G7.005 | U25 | code-fix | chip-fake ranges cite datasheet pages (SGP40, SCD30, ISL29125); SCD30 NVM set against the Interface Description [partly]
- G7.006 | U25 | doc-fix | fake reactions to unspecified input cite evidence or join the fidelity table [partly]
- G7.008 | U25 | rule-write | write the fidelity table in digital_twin/README.md [wrong]
- G7.015 | U25 | doc-fix | README.md:637 "keeps serving afterward" shown, not asserted [partly]
- G7.018 | U25 | code-fix | launch.py/twin_wiring/machine.py hand wiring literals derived from the generated plan; L.4 claim corrected [drifted]
- G7.021 | U25 | code-fix | prewarm enforced in every twin boot path; fact moved to Part F [partly]
- G7.022 | U25 | code-fix | UDP shim call order enforced; verify Run 7 port-53 failure is loud [partly]
- G7.023 | U25 | code-fix | retire the heap-unwedge helper (OR52.a (6)) after a test proves the override applies; F.6/CLAUDE.md updated [drifted]
- G7.024 | U25 | code-fix | segfault_stress_repro narrows its broad except [partly]
- G7.025 | U25 | doc-fix | README.md:579-582/615-619 Ctrl-C flush and "default persisted path" claims vs in-memory default [drifted]
- G7.026 | U25 | code-fix | FRAM twin state checks the `size` field; SCD30 non-dict JSON degrades to a blank chip [partly]
- G7.029 | U25 | code-fix | `maybe_hang` on BMP3xx/ISL29125 zero-byte probe; per-command/address fault targeting [partly]
- G7.031 | U25 | code-fix | `--fault`/`--hang` address every instance; uart_link instances fault-injectable [partly]
- G7.033 | U25 | code-fix | twin FRAM FaultInjector raises only where rp2 SPI can; re-read rp2 source [partly]
- G7.035 | U25 | doc-fix | digital_twin/README.md strict set (adds isl29125) and dangling BACKLOG pointer [partly]
- G7.042 | U25 | code-fix | bus-hazard twin test's shared bus log bounded or checked for wrap; unused 200-entry `I2C.log` [partly]
- G7.046 | U25 | code-fix | twin HTTP client distinguishes refusal from other empty responses; stub-gap ignore gets a trigger [partly]
- G7.048 | U25 | code-fix | per-run twin config dir instead of fixed `digital_twin/config/` [partly]
- G9.042 | U25 | code-fix | remove the heap-unwedge helper's 5 references (OR52.a (6)) [partly]
- G10.003 | U25 | code-fix | twin chip-model class names match src casing [partly]

### U26 — B2 HW (52)

- G1.004 | U26 | code-fix | gate isl29125_mechanism_envelope's ~9 flash writes behind persistence_write and correct `--allow-neopixel-sweep` help ("spends no write") [partly]
- G1.010 | U26 | code-fix | gate `test_env_tier_flash_recurring_run_is_idempotent` (host wear per flash pass) [partly]
- G1.011 | U26 | code-fix | isolated scripts: remove envelope flash writes, trace/prime scd30_plausibility_read's reader [partly]
- G1.013 | U26 | code-fix | device scripts remove board scratch files on every path (WiFi password left on flash after a WDT reset) [partly]
- G1.014 | U26 | code-fix | restore WarnCO2, move garbage-SSID PUT inside try, verify restored value not just HTTP 200, repair leftovers [partly]
- G1.015 | U26 | code-fix | read SCD30 MeasInt/pressure/offset preconditions and restore NVM values the scripts change [partly]
- G1.016 | U26 | code-fix | manual_persistence/manual_wifi restore MeasInt and SSID [partly]
- G1.017 | U26 | code-fix | session-start cleanup of iptables/netem/profile leftovers; `join_dut_hotspot()` inside try/finally [partly]
- G1.018 | U26 | code-fix | `ensure_bench_bridge()` arms the dead-man's switch itself; drop hard-coded "Wired connection 1" in B.13 [partly]
- G1.020 | U26 | code-fix | remove the committed bench PSK from wifi_reconnect_after_failed_attempts_repro.py; one run-time credential convention [partly]
- G1.024 | U26 | code-fix | harness snapshot primitive before `reset_all_error_logs()`; reword SPEC C.7 "clear it first" [partly]
- G1.025 | U26 | code-fix | FRAM seed/error-log scripts clear on every path and record what they left [partly]
- G1.026 | U26 | test-add | check raw FRAM scratch regions against production's chunk allocation (READ_REGION is chunk 0) [partly]
- G1.027 | U26 | code-fix | derive `_FRAM_BACKED_MODULES` from buildgen's FRAM wiring (omits WIFI/NTP/WEBSERVER/DNSSRV/CFGMGR_*/UART_*) [drifted]
- G1.028 | U26 | code-fix | fram_capacity script derives FRAM-wired names instead of a hand list [partly]
- G1.029 | U26 | code-fix | test_watchdog_starvation must not treat `CAUSE 3` alone as WDT proof [wrong]
- G1.030 | U26 | doc-fix | harness.hard_reset()/test_reboot_persistence "DTR-line hardware reset" is `machine.reset()` via raw REPL [partly]
- G1.031 | U26 | code-fix | feed the 8 s WDT in long/unbounded device scripts; commit the documented feeding wrapper [partly]
- G1.033 | U26 | code-fix | sgp40 scripts pass the bus timeout on i2c1 (silently lowers SCD30's) [partly]
- G1.042 | U26 | code-fix | enable `--strict-markers`; drop inert "timeout" from the marker allowlist [partly]
- G1.043 | U26 | code-fix | persistence-marker guard covers device_scripts writes and class-level markers [partly]
- G1.047 | U26 | code-fix | minimum-engagement floors in bus-concurrency, memory-stress, scheduler-saturation and UART-load tests [partly]
- G1.049 | U26 | code-fix | bench crash oracles cover the whole fault window, task-ended and WEBSERVER state [partly]
- G1.050 | U26 | code-fix | heap_map.py uses the shared MEMORY_ERROR_MARKERS; network-fault tests grep both markers [partly]
- G1.051 | U26 | code-fix | one shared boot-completion helper replaces `"CFGMGR_" in joined or "FRAM" in joined` (5 sites) [partly]
- G1.052 | U26 | code-fix | fixture reads DebugLevel before the bench tier; README ≥3 vs 5 made one value [partly]
- G1.056 | U26 | code-fix | fixture compares image `buildDate`/hash with the tree before tree-derived oracles [partly]
- G1.065 | U26 | code-fix | "does not leak" soak test asserts a trend or is renamed to liveness [partly]
- G1.069 | U26 | code-fix | ~30 hand-copied product constants derived or pinned (`range(6)`, "24 workers") [partly]
- G1.070 | U26 | code-fix | one shared plausibility-bounds module (400 vs 200 ppm drift) [drifted]
- G1.071 | U26 | test-add | guard bench pin copies against devices/dev.toml; drop dev_legacy pin citation [partly]
- G1.072 | U26 | test-add | host test cross-checks on-target `KNOWN_ADDRESSES` against devices/*.toml [partly]
- G1.073 | U26 | code-fix | isl29125_conformance twin run uses test.sh heapsize and both GC stages; clear error on missing build [partly]
- G1.074 | U26 | test-add | pin hardware/twin HTTP-client shape parity [not checked]
- G1.076 | U26 | test-add | record/enforce a twin run per device script before silicon [not checked]
- G1.077 | U26 | code-fix | host runners (or OR33.a drop) for four orphaned scripts; the two always-PASS scripts made to bite [partly]
- G1.079 | U26 | code-fix | HTTP_ERROR thread guard covers try-less workers, positional targets, helper fetches, flash scripts [partly]
- G1.080 | U26 | code-fix | kick-then-reset helper for ad-hoc scripts; reconnect retries report themselves [partly]
- G1.081 | U26 | doc-fix | bench workarounds state removal trigger and tool version [partly]
- G1.085 | U26 | code-fix | conftest.py:181-187 `is_ssid_visible()` while the AP is up [partly]
- G1.086 | U26 | code-fix | role-reversal fixture restores on a stage-1/2 failure; stage order enforced; rejected restore fails [partly]
- G1.087 | U26 | doc-fix | garbage-response tests' reach (DNAT delivery, redirect-verified claim) stated once and correctly [drifted]
- G1.096 | U26 | code-fix | isl29125_plausibility_read parks the rig on its early-return path [partly]
- G1.099 | U26 | code-fix | manual runner can record FAIL for confirm()-only tests [partly]
- G1.103 | U26 | doc-fix | manual_bus_electrical WS2812 "no datasheet" claim; BMP384/390 tolerance citation [drifted]
- G1.109 | U26 | code-fix | move the one inline subprocess suppression into pyproject's central block [partly]
- G2.064 | U26 | test-add | conformance probes for SCD30, SGP40, BMP3xx, FRAM with a pytest gate [partly]
- G3.107 | U26 | doc-fix | tests_hardware/README.md:596-600 "no WS2812 datasheet"; SGP40 algorithm reference now reachable [drifted]
- G6.053 | U26 | doc-fix | tests_hardware/README.md:635-641 "open owner question" on CYW43 power-cycle recovery (settled) [drifted]
- G8.016 | U26 | code-fix | ~20 device scripts hardcode pins (take them from devices/dev.toml) [partly]
- G8.134 | U26 | code-fix | `--strict-markers` in pyproject so a misspelled gate marker fails collection [wrong]
- G10.064 | U26 | code-fix | three flag spellings aligned; `--strict-markers` [partly]

### U27 — B2 SCR (19)

- G1.021 | U27 | code-fix | mpremote_connect.sh default `/dev/ttyACM0` and setup_toolchain.py 2e8a match select the board by USB identity [partly]
- G4.053 | U27 | doc-fix | typecheck stub workarounds state removal triggers [partly]
- G7.028 | U27 | code-fix | run_digital_twin_ci.sh archives twin FRAM/SCD30 state before wiping (OR38.a (2)) [partly]
- G8.037 | U27 | code-fix | lint/typecheck scope covers build/generated_src; codegen drops ignores/noqa/dead `timers_running`/unstripped TYPE_CHECKING [wrong]
- G8.053 | U27 | code-fix | one shared binary-variant probe for every runner (twin, JS, smoke, CI) [partly]
- G8.078 | U27 | doc-fix | B.10.1 "180 s x 3" vs 240 s; test.sh "85 files" [drifted]
- G8.080 | U27 | code-fix | unit MICROPYPATH includes `ext`; one twin path definition; E.3 example [partly]
- G8.086 | U27 | code-fix | lint.sh/typecheck.sh check tool versions against the pins [partly]
- G8.087 | U27 | code-fix | stub post-release pinned; moved stub tree fails the repair loudly [partly]
- G8.089 | U27 | test-add | check the three mypy configs stay in sync; CLAUDE.md exclusion list completed [partly]
- G8.091 | U27 | code-fix | run_bench_soak_tests.sh caller `-m` no longer replaces the soak exclusion [partly]
- G8.093 | U27 | code-fix | run_digital_twin_ci.sh gets the clean step its comments claim; smoke stops rmSync of shared config [drifted]
- G8.096 | U27 | code-fix | `gzip -n` for reproducibility; quote loop; `-s` drift comment [partly]
- G8.097 | U27 | code-fix | bare `python3` sites check ≥3.11 [partly]
- G8.098 | U27 | code-fix | TYPE_CHECKING strip handles compound/else forms [partly]
- G9.021 | U27 | code-fix | comment-cap gate: tag exemption per line, `_PEP723` anchored, long physical lines counted [partly]
- G10.028 | U27 | test-add | header-block presence check in test_comment_block_cap.py [partly]
- G10.056 | U27 | code-fix | one host CLI entry and error shape; rule in L.5 [partly]
- G10.074 | U27 | code-fix | 20 `# ====` rules to the dash form [partly]

### U28 — B2 CI (22)

- G2.072 | U28 | doc-fix | CLAUDE.md per-file-ignores claim for scripts/ and toolchain/ [drifted]
- G5.084 | U28 | doc-fix | confirm dev-tool pins in pyproject/uv.lock [not checked]
- G8.070 | U28 | decide | CI never builds with GCC 14 — add a trixie/GCC-14 CI leg or rely on the owner's manual chroot run? [partly]
- G8.082 | U28 | code-fix | `web-coverage` test step not `continue-on-error` (align with Python, OR decision 2026-09-22) [partly]
- G8.100 | U28 | code-fix | pin the coverage renderer's PEP 723 dependency [partly]
- G8.102 | U28 | code-fix | cross_browser_smoke fails when a required engine skipped; Firefox cache key; Playwright failure reported [partly]
- G8.111 | U28 | doc-fix | CLAUDE.md/zizmor.yml "only unpinned-uses configured" [drifted]
- G8.112 | U28 | doc-fix | CLAUDE.md `!cancelled()` carriers list; web lanes' gating intent stated [drifted]
- G8.114 | U28 | doc-fix | SPEC A.3 stage list omits gc-threshold, coverage and web jobs [drifted]
- G8.115 | U28 | code-fix | pin pytest/mpremote/pip uv; `uv sync --locked` [drifted]
- G8.116 | U28 | test-add | CI `uv sync --locked` (catches lock/pin contradictions) [unverifiable]
- G8.118 | U28 | code-fix | web path filter adds src/buildgen/devices/digital_twin/toolchain [partly]
- G8.119 | U28 | code-fix | toolchain cache key adds micropython_overrides.py; picotool cached [partly]
- G8.120 | U28 | code-fix | composite action header count; build-if-missing step into the action [drifted]
- G8.121 | U28 | decide | [q] Codecov: register the repo, drop the uploads, or keep the inert steps? (G8 Q1) [holds*]
- G8.124 | U28 | code-fix | 76 inline noqa move to central per-file-ignores; CLAUDE.md claim corrected [drifted]
- G8.127 | U28 | code-fix | skipLibCheck spares the project's .d.ts; shared tsconfig base; header list [partly]
- G8.132 | U28 | code-fix | one uv-sync retry source (composite action) [partly]
- G9.020 | U28 | code-fix | tsconfig.json, tsconfig.node.json, vitest-commands.d.ts comment blocks to the 3-line cap [drifted]
- G9.100 | U28 | doc-fix | pyproject CPY001 exemption reason vs 10 SPDX files [drifted]
- G10.072 | U28 | code-fix | suppression comment order and spacing; rule in D.6 [partly]
- G10.081 | U28 | code-fix | per-file suppression list folded into per-site or per-category; rule in B.15/D.6 [partly]

### U29 — B2 SEC (3)

- G5.087 | U29 | rule-write | write the threat-model statement into SPECIFICATION.md (OR52) [partly]
- G5.088 | U29 | doc-fix | one list of hotspot-password sites (six TOMLs, eight exempted files) vs CLAUDE.md's two [drifted]
- G9.091 | U29 | doc-fix | CLAUDE.md hotspot-password locations (six TOMLs, config default) [drifted]

### U30 — B2 MEM (13)

- G1.063 | U30 | decide | may a test gc.collect() before a timed window (UART timing scripts)? (G1 Q2); other hardware gc sites fixed and gc-site test scope extended [partly]
- G2.010 | U30 | code-fix | test_asy_webserver_service.py's 58 in-body `gc.threshold` calls vs the file's stage [partly]
- G2.011 | U30 | code-fix | remove gc.collect props in test_fram_integration.py/_webserver_concurrency_scenarios.py; extend gc-site guard to tests/ and digital_twin/ [drifted]
- G2.012 | U30 | code-fix | JS live twins and cross_browser_smoke scan twin stdout with the memory gate [partly]
- G4.062 | U30 | decide | F.2/CLAUDE.md "concrete, non-hypothetical threat" wording vs OR26.a — reword CLAUDE.md hard rule to OR26.a's? (OR13.a) [drifted]
- G4.070 | U30 | test-add | assert threshold set exactly once; threshold runner derives 32768 from codegen; hazard phase stays in its stage [partly]
- G4.071 | U30 | code-fix | scan twin boots in tests_scripts, Vitest twins and remaining hardware tests with the memory gate [partly]
- G4.073 | U30 | code-fix | remove gc.collect props in test_digital_twin_sensortask_integration/segfault_stress_repro; extend gc-site test to digital_twin/ [partly]
- G4.076 | U30 | code-fix | re-walk Part I.2 hotspots with the placement lens [partly]
- G7.034 | U30 | test-add | twin `_GC_THRESHOLD_DEFAULT` tied to codegen's 32768; one Part E statement [partly]
- G7.041 | U30 | code-fix | twin sampler measures after a settle (OR39.a/OR55.a); segfault_stress_repro tool use removed; I.4(e) reworded [partly]
- G8.083 | U30 | test-add | one test ties the four copies of 32768 [partly]
- G9.046 | U30 | decide | CLAUDE.md/F.2 "concrete, non-hypothetical threat" MemoryError wording vs OR26.a — reword? (same question as G4.062) [drifted]

### U31 — B2 PERF (2)

- G4.082 | U31 | doc-fix | [q] F.5.4 heading "the one worth adopting" vs the owner's non-adoption [holds*]
- G10.040 | U31 | code-fix | allocation-free `sleep_ms` in recurring paths (~17 float sleeps); rule in D.4/F.1 [partly]

### U32 — B2 PAR (4)

- G9.052 | U32 | code-fix | restore the legacy losses found (SGP40 NTP wait 0, SCD30 compare) — tracked via G9.067/G4 [partly]
- G9.083 | U32 | test-add | trace legacy `Task_LastErr`/per-sensor `ErrCnt` key by key into the OR43 inventory [partly]
- G9.089 | U32 | rule-write | write the legacy reflash runbook; F.5:3681 stale pointer [partly]
- G9.090 | U32 | decide | frozen-module shadowing: runbook only, `.frozen` first on sys.path in the generated boot entry, or both? (G9 Q2); README claim corrected either way [wrong]

### U33 — B2 DOC (8)

- G1.104 | U33 | doc-fix | remove retired queue/item citations from permanent files; rule into CLAUDE.md docs agreement [drifted]
- G3.101 | U33 | decide | ISL29125 legacy-parity exemption: add the pointer to CLAUDE.md's parity rule? (OR13.a rule drift) [drifted]
- G8.009 | U33 | doc-fix | K.3 "every other table AST-derived" vs further hand tables; settled BACKLOG item moves to L.6.6 [drifted]
- G8.059 | U33 | doc-fix | BACKLOG chroot list adds the build-env files changed since 2026-09-13 [drifted]
- G9.011 | U33 | doc-fix | README doc map adds update_and_install.txt and the licence files [partly]
- G9.014 | U33 | doc-fix | BACKLOG/README headers name SPECIFICATION.md as migration target; settled entry out [drifted]
- G9.015 | U33 | doc-fix | BACKLOG stub list adds item 29 [partly]
- G9.016 | U33 | doc-fix | BACKLOG.md:89-90 lists the delivered `_reboot()` alarm-pool test as open [partly]

### U34 — B2 LIC (9)

- G3.053 | U34 | doc-fix | THIRD_PARTY_LICENSES.md "FRAM-persisted self-calibration" claim; operator procedure into DEVICE_REFERENCE.md [drifted]
- G9.051 | U34 | doc-fix | THIRD_PARTY_LICENSES.md and README licence paragraph state `arduino/` is out of scope [partly]
- G9.093 | U34 | doc-fix | LICENSE/THIRD_PARTY opening paragraph names the BSD-3 and karfas cases [partly]
- G9.094 | U34 | doc-fix | ISL29125 double entry, "one non-Adafruit file", FRAM calibration claim [drifted]
- G9.096 | U34 | doc-fix | captive_dns SPDX scope and copyright line agree with the docs [drifted]
- G9.097 | U34 | doc-fix | asy_udp_socket/asy_ntp_client headers carry link and change list [drifted]
- G9.099 | U34 | doc-fix | freezefs SHA recorded; "2.4" vs main; copyright line [drifted]
- G9.101 | U34 | rule-write | UF2 notices section in THIRD_PARTY_LICENSES.md; datasheet terms checked [partly]
- G10.030 | U34 | code-fix | licence line position in 3 attribution headers [partly]

### U35 — B3 test campaign (9)

- G2.025 | U35 | test-add | per-parameter bound and float-edge tests per driver (OR25.a) [not checked]
- G2.045 | U35 | code-fix | force interleavings (BMP torn-read, NTP single-yield bind) [partly]
- G2.046 | U35 | code-fix | remaining real-time unit suites move to driven time [partly]
- G2.053 | U35 | code-fix | SGP40 sweep asserts full set; `_still_serving()`/connect loops stop swallowing [partly]
- G2.054 | U35 | code-fix | early-return PASS scenarios and the vacuous `WDT()` half of test_reset_call_site_invariant [partly]
- G2.056 | U35 | code-fix | UART hazard catalog asserts code and ErrType, not ErrCount [partly]
- G2.057 | U35 | rule-write | restate the unreachable-branch convention in Part E (its BACKLOG home is gone) [partly]
- G2.059 | U35 | code-fix | commit the fault-planting sweep script (OR21.a) [partly]
- G7.030 | U35 | decide | combined multi-driver twin faults: include the risky higher-order combinations (OR41.a) or keep one fault per process? [partly]

### U36 — B4 docs (31)

- G2.052 | U36 | rule-write | "every workaround names its removal trigger" into the principles Part [partly]
- G5.009 | U36 | rule-write | state D.2's "untyped entry points validated" half [partly]
- G5.082 | U36 | decide | D.10/CLAUDE.md "flag, don't silently fix" vs OR24.a — reword CLAUDE.md after the audit as OR24.a (1) says? [drifted]
- G5.083 | U36 | rule-write | "record unrelated failures found on the way" into CLAUDE.md working agreements [partly]
- G7.071 | U36 | rule-write | state the browser floor in SPECIFICATION.md H.1 [partly]
- G8.035 | U36 | rule-write | "integration proven by generating for real" as a checklist step [unverifiable]
- G8.072 | U36 | rule-write | "gate verdicts come from exit status" into CLAUDE.md working agreements [unverifiable]
- G8.117 | U36 | rule-write | one-sided-merge practice kept in CLAUDE.md (review-only; confirm home) [unverifiable]
- G9.001 | U36 | doc-fix | strip narrative from SPEC, tests_hardware/README, CLAUDE.md "Known … fixed", README, code comments (OR27) [drifted]
- G9.002 | U36 | doc-fix | remove undefined process labels (WP1/WP6 and 26 more) [drifted]
- G9.003 | U36 | doc-fix | fix two dangling hard-rule pointers and 47 others; add a pointer check [drifted]
- G9.005 | U36 | doc-fix | drop citations of temporary files (changelog B15/B17, A1/A3, F14/F15) [drifted]
- G9.006 | U36 | doc-fix | CLAUDE.md sheds facts/incidents; BACKLOG sheds settled entries [partly]
- G9.007 | U36 | doc-fix | SCD30/SGP40/BMP3xx/FRAM datasheet facts move to Part M [partly]
- G9.008 | U36 | doc-fix | version-bump re-check practice in one home (CLAUDE.md citing SPEC F) [drifted]
- G9.009 | U36 | doc-fix | CLAUDE.md incidents and chroot recipe move to SPEC B/E/F [drifted]
- G9.010 | U36 | doc-fix | SPECIFICATION.md numbering (I.6 after J, H.5.1, unnumbered H.7, F.5.7-9 placement) [drifted]
- G9.012 | U36 | doc-fix | README first screen describes the current system, not legacy builds [drifted]
- G9.013 | U36 | doc-fix | README `build_firmware.py <device>` needs devices/<device>.toml; help check test [drifted]
- G9.017 | U36 | rule-write | write the factual-drift vs rule-drift split (OR13.a) into CLAUDE.md working agreements [partly]
- G9.018 | U36 | doc-fix | reword CLAUDE.md's flag-first hard rule per OR24.a (1) (owner already decided) [drifted]
- G9.023 | U36 | doc-fix | drop dated counts (86/86, 85 files) outside evidence; rule into CLAUDE.md docs rule [stale]
- G9.025 | U36 | doc-fix | K/L/C checklist steps match the tree (L.1 "one association", K.5 `_build_spi_chip()`, C.1 wiring block) [drifted]
- G9.029 | U36 | doc-fix | 9 comments naming `sensortask_wozi.py`/retired runners [partly]
- G9.031 | U36 | decide | CLAUDE.md "structurally cannot have a write in flight" vs F.2 "no longer exactly true" — reword the hard rule to F.2? (OR13.a) [drifted]
- G9.035 | U36 | doc-fix | SPEC:7 and README:650 "pre-push verification" vs periodic owner-run; recipe scope and duplicate paragraph [drifted]
- G9.037 | U36 | doc-fix | README.md:177 vs :192 coverage gating wording [drifted]
- G9.080 | U36 | rule-write | [q] EU DST switch-date limitation into DEVICE_REFERENCE.md [holds*]
- G9.092 | U36 | rule-write | state arzi/neu "no pressure compensation" in SPEC A.4 or DEVICE_REFERENCE [drifted]
- G10.070 | U36 | doc-fix | SPEC A.2/B.11/C.1/C.5.3 describe live architecture with legacy names and routes [drifted]
- G10.071 | U36 | rule-write | commit-message convention in CLAUDE.md "Pull request workflow" [partly]

### C — Phase C hardware rounds (BACKLOG "Real-hardware work still owed") (10)

- G1.055 | C | hardware | prove supervisor-restart and wedged-bus WDT rungs on silicon with a discriminating oracle [partly]
- G1.060 | C | hardware | re-derive `_MAX_USED`/`_MAX_ROUTE_NEED` on a named image [partly]
- G1.095 | C | hardware | record light-rig geometry (BACKLOG M1) [partly]
- G3.047 | C | hardware | re-measure the ISL29125 silicon rows the twin cites [unverifiable]
- G3.076 | C | hardware | re-read bench NVM state and BMP/ISL register volatility [unverifiable]
- G3.100 | C | hardware | measure undocumented ISL29125 behaviour on silicon [unverifiable]
- G5.035 | C | hardware | measure the deferred-flush power-loss window and littlefs repair [unverifiable]
- G6.032 | C | hardware | confirm twin UART/network fakes against silicon [unverifiable]
- G7.007 | C | hardware | conformance probes for older chips' fakes, measured 12-bit cycle [partly]
- G8.032 | C | hardware | check the three neu units' TOML wiring against the physical units [unverifiable]

### Digest: the 28 `decide` lines

Sorted by id; each is also in its unit list above. 28 lines, 25 distinct questions (G4.062 = G9.046, G5.005 = G9.048, G4.087 = G6.087).

- G1.063 (U30): may a test gc.collect() before a timed window (UART timing scripts)? (G1 Q2); other hardware gc sites fixed and gc-site test scope extended
- G2.035 (U24): twin fakes: independent copies held by contract tests, or one shared implementation? (G2 Q2)
- G3.008 (U12): Stull/McCamy validity domains unverifiable — can the owner supply the papers, or accept code bounds as-is?
- G3.011 (U14): test float32 off-silicon with a single-precision Unix-port build, or prove on L3 only? (G3 Q3); Part F.1 fact written either way
- G3.044 (U15): does "never stale as fresh" bind every driver or only ISL29125 (config-read-failure defaulted sample, SCD30 not-ready reuse)? (G3 Q2)
- G3.062 (U3): alternating errno 11/1 per failed read defeats the newest-entry rule: accept, stop per-streak errno 1, or collapse last-two repeats? (G3 Q1)
- G3.101 (U33): ISL29125 legacy-parity exemption: add the pointer to CLAUDE.md's parity rule? (OR13.a rule drift)
- G4.062 (U30): F.2/CLAUDE.md "concrete, non-hypothetical threat" wording vs OR26.a — reword CLAUDE.md hard rule to OR26.a's? (OR13.a)
- G4.087 (U19): F18: are zero-think-time concurrent FRAM-log readers in contract (3 readers reach 88-98 % of the 15 s cap)?
- G5.005 (U10): restore D.15's 2026-09-13 owner amendment dropped by merge e5d2c43, then reorder 18 classes? (OR13.a)
- G5.006 (U10): static-import rule: firmware only or whole repo (twin/tests/buildgen dynamic imports)?
- G5.029 (U11): first-boot missing config file persists wrnno 3 (and 6 for command-only) against the 2026-09-12 no-warning principle — print-only for missing, persisted for corrupt? (G5 Q5)
- G5.034 (U11): CLAUDE.md "flash writes only via REST PUT" vs ConfigManager's boot repair write — reword the hard rule to "user changes or boot repair"? (OR13.a)
- G5.080 (U12): CRC empty-payload asymmetry: fix inside crc_checks.py despite the "not to be modified" ruling, or forbid zero-length payloads at callers? (G5 Q6)
- G5.082 (U36): D.10/CLAUDE.md "flag, don't silently fix" vs OR24.a — reword CLAUDE.md after the audit as OR24.a (1) says?
- G6.022 (U3): UART E/W fault pairs under the central repeat rule: exception, compare per kind, or two slots per fault? (G6 Q1)
- G6.087 (U19): F18/BACKLOG #24: ResetErrors sweep near the 15 s cap at three readers — in contract?
- G7.030 (U35): combined multi-driver twin faults: include the risky higher-order combinations (OR41.a) or keep one fault per process?
- G7.074 (U23): Apply-failure website divergence from legacy decided by a session agent (OR48.a (2)) — keep it?
- G7.080 (U23): timezone fields on the System or Networking page? (G7 Q1)
- G8.070 (U28): CI never builds with GCC 14 — add a trixie/GCC-14 CI leg or rely on the owner's manual chroot run?
- G8.121 (U28): Codecov: register the repo, drop the uploads, or keep the inert steps? (G8 Q1)
- G9.031 (U36): CLAUDE.md "structurally cannot have a write in flight" vs F.2 "no longer exactly true" — reword the hard rule to F.2? (OR13.a)
- G9.046 (U30): CLAUDE.md/F.2 "concrete, non-hypothetical threat" MemoryError wording vs OR26.a — reword? (same question as G4.062)
- G9.048 (U10): restore D.15's dropped amendment ("comments move with code") and run the reorder under OR24 (same question as G5.005)
- G9.070 (U15): SGP40 general-call reset on every task restart is new vs field units — keep it?
- G9.090 (U32): frozen-module shadowing: runbook only, `.frozen` first on sys.path in the generated boot entry, or both? (G9 Q2); README claim corrected either way
- G10.009 (U10): rename legacy-spelled config keys to one scheme before the release freezes them? (G10 Q2)

### Digest: the 10 `hardware` lines (phase C, BACKLOG real-hardware list)

- G1.055: prove supervisor-restart and wedged-bus WDT rungs on silicon with a discriminating oracle
- G1.060: re-derive `_MAX_USED`/`_MAX_ROUTE_NEED` on a named image
- G1.095: record light-rig geometry (BACKLOG M1)
- G3.047: re-measure the ISL29125 silicon rows the twin cites
- G3.076: re-read bench NVM state and BMP/ISL register volatility
- G3.100: measure undocumented ISL29125 behaviour on silicon
- G5.035: measure the deferred-flush power-loss window and littlefs repair
- G6.032: confirm twin UART/network fakes against silicon
- G7.007: conformance probes for older chips' fakes, measured 12-bit cycle
- G8.032: check the three neu units' TOML wiring against the physical units

## Task 2 — agent-rule adoption check (provenance A)

421 candidates carry provenance A. Listed below: every A candidate whose Fit states a conflict or tension (21), every A candidate that changes product behaviour against the legacy field firmware (OR48.a (2)), and every A candidate that restricts something an owner row allows. Recommendation vocabulary: **adopt** (keep as written, record at the OR2.c owner review), **reword** (keep the intent, change the text or scope), **yield to OR…** (the owner row wins, the rule is changed to match), **owner question** (needs the owner's answer; the question is named). 46 entries; 14 are owner questions.

### 2.1 Fit states a conflict or tension

- G2.036 | twin fakes independent of unit fakes | OR24 (one material) | owner question — independent copies held by contract tests, or one shared implementation (G2 Q2); lean independent + contract suite
- G3.029 | bus-layer asymmetries deliberate | OR24.a | adopt — not equivalent methods; the lost I2C between-session-yield decision is written into G.2
- G3.034 | uninitialised bus is a silent no-op | OR26 | yield to OR26 — the caller must be able to tell a skipped transfer from success (BMP logs a false "timeout")
- G3.044 | config-read failure publishes a defaulted sample | M.1.1 req 16 (owner) | owner question — does "never stale as fresh" bind every driver (G3 Q2)
- G3.058 | bounded settle may publish a stale sample | M.1.1 req 16 (owner) | owner question — same as G3.044
- G3.062 | failed read logs errno 11 then errno 1 | OR35.b | owner question — the alternation defeats the newest-entry rule (G3 Q1)
- G3.063 | failed trigger-timer arm degrades | OR31.a, OR18 | yield to OR31.a — re-arm or escalate; no silent stall until reboot
- G5.013 | provably unreachable branches may stay | OR46.a (2) | yield to OR46.a (2) — keep only branches with an OR26.a true alternative flow, each listed in E.5.1
- G6.042 | WiFi observation failures degrade print-only | OR26.a, OR18 (P7) | reword — kept for now (conservative); the OR26.a right-layer review decides which observations persist
- G7.003 | product code has no twin awareness | OR36.a (2) | adopt — `self.uart` public seam goes
- G7.030 | one driver fault per twin process | OR41.a (1) | reword — combined faults run as OR18.a escalation cases asserting the reboot
- G7.080 | timezone fields on the System page | OR43.a (2) | owner question — System or Networking page (G7 Q1)
- G8.034 | explicit per-driver device allow-lists | OR43.a (3) | reword — allow-lists only where an owner rule restricts a driver (ISL29125, UART link); elsewhere derived
- G8.040 | schema extraction silently drops fields | OR16, OR43.a (2) | yield to OR16 — an untagged or unresolvable field fails the build
- G8.056 | mbedtls `-Wno-array-bounds` build-wide | CLAUDE.md "any warning fails" | reword — scope the flag to mbedtls
- G8.100 | coverage renderer's PEP 723 dependency unpinned | OR50.a (1), CLAUDE.md pins | reword — pin it
- G8.103 | twin soak trend check retries once | OR37.a (2) | adopt — state that the retry answers measurement noise, not a race (G7.036 the same)
- G8.121 | Codecov uploads inert | OR5 | owner question — register, drop, or keep (G8 Q1)
- G8.126 | ESLint curated, ruff ALL | OR24 | adopt — two documented lint philosophies, code stays one material
- G9.019 | step-session workflow stops and reports | OR2, PQ8 | reword — inside the audit a report is a sync point, not a stop
- G10.006 | DeviceSession copied per driver | OR24, OR46.b | yield to OR46.b — one shared class

### 2.2 Product behaviour changed against the legacy field firmware by a session agent (OR48.a (2))

- G6.050 | public DNS fallback 8.8.8.8/1.1.1.1 (legacy used DHCP DNS via getaddrinfo) | OR48.a (2), OR52.a (3) | owner question (G6 Q2) — lean remove: legacy parity, LAN-only threat model
- G9.070 | SGP40 general-call reset on every task restart (field units never broadcast) | OR48.a (2) | owner question (G9 Q4)
- G10.009 | config-key scheme; legacy `SGP`/`BMP` prefixes already dropped by an agent, `SGPResetVOC`/`ISLCalibrate` keep theirs | OR52.a (1)/(2), OR24.a (2) | owner question — rename to one scheme before the release freezes keys (G10 Q2)
- G3.039 | chip identity check replaces legacy's feature-set check | OR48.a (2) | owner question — confirm the swap; complete SGP40's 3-word serial read either way
- G6.059 | hotspot answers unmatched static GETs with 302 (no legacy counterpart) | OR12 (features unchanged), OR48.a (2) | owner question — lean adopt (additive, hotspot-only)
- G4.004 | fielded units stay on MicroPython 1.26 | G9 Q3 (dev snapshot shows 1.24.1) | owner question — which version the fleet runs
- G4.087 | ResetErrors sweep reaches 88-98 % of the 15 s cap with three readers | F18 (open) | owner question — existing F18
- G5.035 | deferred flash flush: a PUT is answered before its write lands (legacy wrote inline) | OR48.a (2), OR12 | adopt — fixes the self-reset of the PUT connection; the power-loss window is recorded (G1.094 the same)
- G3.022 | datasheet plausibility gate raises (a value legacy published becomes an errno); SCD30 range gate to add | OR12.a (datasheet-proven) | adopt — log the SCD30 extension as a behaviour change
- G6.060 | NTP reply accepted only inside 2025-2100 with sync LI and non-zero stratum (legacy accepted any reply) | OR48.a (2) | adopt — rejects a bad clock; record
- G6.056 | `PW` returns the mask even when no password is set (legacy `null`) | OR48.a (2), OR43.a (1) | reword — mask only when set, as legacy; the mask-PUT defect is fixed separately
- G5.040 | per-field PUT result words labelled "Final project decision" | OR48.a (2); G9.058 (owner-confirmed) | reword — drop the owner-sounding label, the contract rests on G9.058 (G6.079 the same)
- G5.042 | `handle_set_cmd` own catch, "project decision based on prior field experience" | OR28.a (errno 99 clash) | reword — drop the label, renumber in U2
- G6.074 | 2,048 B request-body cap | OR52.a (3) | adopt — heap-bounded, proven by the headroom test
- G5.036 | out-of-band config-file edits are silently overwritten | OR38.a (4) (hardware tier writes config files) | adopt — state it in C.5
- G1.091 | API answers only after the NTP force-sync (~20 s) | CLAUDE.md boot-latency rule | adopt
- G9.080 | EU-only DST switch dates | legacy parity | adopt — document in DEVICE_REFERENCE.md

### 2.3 Restricts something an owner row allows

- G3.019 | unreachable defensive branches kept, labelled and tested | OR46.a (2) | yield to OR46.a (2) — same rule as G5.013
- G3.012 | VOC port stays literal, no stylistic rewrite | OR24.a (change directly) | adopt — a named OR24 exception (diffable against the Sensirion reference, OR4)
- G9.015 | cited numbering never changes, closed stubs stay | OR27.a, OR5, harmonization 3 | reword — at close, citations go with their items (G9.005) and stubs are dropped
- G8.067 | bare installer call runs `setup` for compatibility | OR46.a (2) | yield to OR46.a (2) unless a user of the path is found
- G7.043 | wozi-only L2 scopes | OR22.a (2) (all six) | yield to OR22.a (2) unless the OR25.a intent map shows the device paths covered elsewhere
- G10.042 | constructor tail order | OR46.b | yield to OR46.b — the config objects replace the tail
- G8.101 | website build fallback for devices without hand-written definitions | OR43.a (3) | reword — every device is generated once the hand files retire
- G8.070 | ARM GCC unpinned; CI never builds with GCC 14 | owner 2026-09-18 (chroot legs periodic) | owner question — add a GCC 14 CI leg or rely on the manual chroot run

## Task 3 — permanent homes

Method: each candidate's Home field (`where now → where it belongs`) was parsed; a rule counts for a target when the target appears on the right of the arrow and not on the left (a correction in the same place is not a new rule; `unchanged`/`stays`/`(fine)` counts nothing). One candidate can count for several targets. Of 965 candidates, **398** move or add a rule somewhere; **68** have no written home today (Home left side `none`/`nowhere`/`n/a`/empty, a commit message only, or only an owner row of the temporary plan).

### 3.1 New rules per target

| Target | rules to write | of which no home today |
|---|---|---|
| SPEC A | 27 | 4 |
| SPEC B | 14 | 0 |
| SPEC C | 51 | 13 |
| SPEC D | 18 | 6 |
| SPEC E | 84 | 10 |
| SPEC F | 35 | 5 |
| SPEC G | 24 | 1 |
| SPEC H | 6 | 1 |
| SPEC I | 7 | 1 |
| SPEC J | 3 | 0 |
| SPEC K (one ordered checklist) | 23 | 0 |
| SPEC L | 11 | 6 |
| SPEC M | 8 | 0 |
| SPEC principles Part (new) | 6 | 2 |
| SPEC tunables section (new) | 20 | 3 |
| SPEC threat model (new) | 3 | 1 |
| CLAUDE.md | 18 | 7 |
| README.md | 6 | 1 |
| BACKLOG.md | 5 | 1 |
| tests_hardware/README.md | 38 | 5 |
| digital_twin/README.md | 7 | 1 |
| DEVICE_REFERENCE.md | 6 | 2 |
| THIRD_PARTY_LICENSES.md | 2 | 1 |
| legacy/README.md | 2 | 2 |
| reflash runbook (new) | 4 | 2 |
| pyproject.toml | 3 | 1 |
| code comment | 2 | 0 |
| test/check | 49 | 7 |
| other (audit file / test) | 2 | 2 |

SPECIFICATION.md in total: 340 placements, led by Part E (the test standard: 84), Part C (51) and Part F (35); three sections do not exist yet and are created in B4 (U36): the principles Part (OR44.a), the tunables section (OR30.a, U8 writes its entries) and the threat-model statement (OR52.a (3), U29). `test/check` counts rules whose home is a mechanical check rather than prose.

### 3.2 Candidates with no written home today (rule-write), by target

Each line: `id | now → target | title`. The rule is written by the unit Task 1 routes the candidate to; where Task 1 routes a fix, the rule text lands with that fix.

**SPEC A** (3)

- G6.049 | (none) → SPEC A (one line) | Project networking is IPv4-only
- G9.088 | none → SPEC A.7 | FRAM and VOC state need not survive a reflash
- G10.010 | none → SPECIFICATION.md A.8 | REST JSON key casing

**SPEC C** (13)

- G5.029 | commit message only → SPECIFICATION.md C.7 (new rule) | Expected conditions never log errors or warnings
- G6.041 | (none) → SPEC C.7 / D.2 | Broad catches only at boundaries, always logged
- G6.047 | (none) → SPEC C.8 | Unlocked read-modify-write has no await inside
- G6.067 | (none) → SPEC C.8 | Cancellation leaves state consistent
- G10.002 | none → SPECIFICATION.md C.2 | Module name and primary class name agree
- G10.005 | none → SPECIFICATION.md C.2 | Driver file class order: consumer first
- G10.013 | none → SPECIFICATION.md C.5 | Config keys referenced through their schema tuple
- G10.019 | none → SPECIFICATION.md C.3 | Raised exception message style
- G10.032 | none → SPECIFICATION.md C.3 | Bus wrappers take the platform class name
- G10.033 | none → SPECIFICATION.md C.8 | Lock attribute naming
- G10.034 | none → SPECIFICATION.md C.8 | Locks acquired with `async with`
- G10.041 | none → SPECIFICATION.md C.2 and L.3 | Unit suffixes in identifiers and TOML keys
- G10.076 | none → SPECIFICATION.md C.2 | `asy`-marking of identifiers

**SPEC D** (5)

- G10.020 | none → SPECIFICATION.md D.10 | Exception tuples in one order
- G10.022 | none → SPECIFICATION.md D.2 | BaseException only for release-and-reraise
- G10.031 | none → SPECIFICATION.md D.10 (one line; the tool enforces it) | Import grouping and no late imports in firmware
- G10.040 | none → SPECIFICATION.md D.4 / F.1 | Allocation-free sleeps in recurring paths
- G10.072 | none → SPECIFICATION.md D.6 | Suppression comments: codes always, one spelling

**SPEC E** (9)

- G1.048 | commit, CLAUDE.md → SPECIFICATION.md Part E + OR15.a summary block | Reset recovery passes, but visibly
- G1.049 | nowhere → SPECIFICATION.md Part E test standard | Bench crash oracles watch the fault window
- G1.064 | OR40.a → SPECIFICATION.md Part E/I | Hardware GC stages: partial now, two images at release
- G1.069 | nowhere as a rule → SPECIFICATION.md Part E test standard (with Part G's single-source catalog) | Hardware oracles derive product constants
- G5.076 | (none) → SPECIFICATION.md E.9 / principles P4 | Shipped code carries no test-only hooks
- G6.033 | (none) → SPEC E.9 / principles Part | Nothing in src/ exists for a test
- G6.081 | (none) → SPEC E test standard | Tests take product values from source
- G10.061 | none → Part E | Test double naming
- G10.063 | none → Part E | pytest style

**SPEC F** (4)

- G1.029 | nowhere → SPECIFICATION.md Part F + tests_hardware/README.md trap | reset_cause cannot tell reset from starvation
- G1.032 | commit → SPECIFICATION.md Part F | rp2 alarm pool is 16 timers; arming can fail
- G1.033 | nowhere as a rule → SPECIFICATION.md Part F.5.1 | One rp2 bus, one set of parameters
- G9.090 | none → reflash runbook + SPEC F (platform fact) | No filesystem file may shadow a frozen module

**SPEC G** (1)

- G10.018 | none → Part G.2, with `T20` re-enabled for `src/` (per-file ignore for `print_log.py`) | Console output only through print_log

**SPEC H** (1)

- G7.071 | (none) → SPECIFICATION.md H.1 (state the floor) | Browser floor: current Chromium, Firefox and Safari

**SPEC I** (1)

- G1.063 | OR39.a → SPECIFICATION.md I.4(f.1) and the gc-site test scope | gc.collect in hardware scripts only as a baseline

**SPEC L** (5)

- G6.068 | (none) → SPEC L config-key stability rule | Stored hostname wins over TOML default
- G8.037 | none → `scripts/lint.sh`/`typecheck.sh` scope + SPEC L.5 | Generated modules meet the src/ lint and type bar
- G10.027 | none → SPECIFICATION.md L.5 | Host code: one annotation-evaluation mode
- G10.054 | none → SPECIFICATION.md L.5 | Shell script conventions
- G10.068 | none → SPECIFICATION.md L.4 | One identifier per module across name spaces

**SPEC tunables section (new)** (3)

- G2.048 | OR30 tunables section → OR30 tunables section | Every test timing value is a recorded tunable
- G6.062 | (none) → new SPECIFICATION.md tunables section | Tuned values are registered tunables
- G7.081 | (none) → SPECIFICATION.md tunables section | Poll cadence and per-page connections are tuned values

**SPEC threat model (new)** (1)

- G7.075 | (none) → SPECIFICATION.md threat-model statement (CONSOLIDATION §4) | Website security under the trusted-LAN threat model

**CLAUDE.md** (7)

- G1.104 | n/a → rule in CLAUDE.md docs working agreement (OR27) | Permanent files never cite retired working items
- G5.083 | commit only → CLAUDE.md working agreements (OR51.a (4) close-out practice) | Unrelated failures found on the way are recorded
- G8.072 | commit messages → CLAUDE.md working agreements | Gate verdicts come from exit status
- G9.002 | none → CLAUDE.md docs rule | No undefined process labels in permanent text
- G9.003 | none → CLAUDE.md docs rule; a `tests_scripts` pointer check is possible for file/Part pointers | Cross-references resolve to a living target
- G9.023 | none → CLAUDE.md docs rule | Measured numbers stay only as evidence
- G10.071 | none → CLAUDE.md "Pull request workflow" | Commit messages

**README.md** (1)

- G10.055 | none → README.md reference section intro | Internal helper scripts start with `_`

**BACKLOG.md** (1)

- G1.102 | nowhere → one line in BACKLOG decisions or SPECIFICATION.md E.6 (OR27.a) | No gc-policy or memory-pressure hardware tooling

**tests_hardware/README.md** (3)

- G1.013 | OR38.a → tests_hardware/README.md + device scripts | Device scripts remove their board scratch files
- G1.015 | nowhere → tests_hardware/README.md SCD30 section | SCD30 NVM preconditions asserted, not assumed
- G10.065 | none → `tests_hardware/README.md | Hardware test file naming

**digital_twin/README.md** (1)

- G7.008 | (none) → `digital_twin/README.md` fidelity table (CONSOLIDATION §4) | One fidelity table says which tier proves each fact

**DEVICE_REFERENCE.md** (2)

- G9.080 | none → DEVICE_REFERENCE.md | Local time follows the EU DST switch dates
- G9.092 | none → SPEC A.4 intentional list or DEVICE_REFERENCE.md | arzi/neu units have no pressure compensation

**THIRD_PARTY_LICENSES.md** (1)

- G9.101 | none → THIRD_PARTY_LICENSES.md (UF2 section) + datasheet note | A published UF2 ships its third-party notices

**legacy/README.md** (2)

- G9.055 | none → `legacy/README.md | Legacy HEAD is the parity baseline; its post-import edits are known
- G9.089 | none → `legacy/README.md` or `tests_hardware/README.md` (runbook) | Legacy units are reflashed with a runbook, not migrated

**pyproject.toml** (1)

- G8.134 | none → `pyproject.toml` `[tool.pytest.ini_options] | A misspelled wear-gate marker fails collection

**test/check** (1)

- G10.016 | none → the OR28 catalog test | Every persisted log call names its number

**other (audit file / test)** (2)

- G1.077 | nowhere → OR33.a verdicts | No orphaned hardware scripts
- G9.083 | none → OR43 inventory (audit working file) | Every value the legacy API exposed is exposed

