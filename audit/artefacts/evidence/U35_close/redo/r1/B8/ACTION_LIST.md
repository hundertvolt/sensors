B8 build chain and generated code: action list (lead, 2026-11-03 21:28 UTC, from the agent's draft of 19:39 UTC)

Final: the owner's answers (O1, O2a-d, 20:40-20:53 UTC) and the lead's decisions are folded in; nothing goes to the
owner. Line numbers below are `d6bc7617`'s; the re-base to the post-B7 head follows.

Re-base (lead, 2026-11-04 06:25 UTC): B7 merged as `d5c90b71`; each mapped line was checked by content.
- `codegen.py`: every cited line from 306 on is one lower (B7 removed `State`); `:305` itself is gone.
- `definitions.py`: `:107-115` unchanged; `:692-694` gone (B7's `State` rows).
- `asy_notification_service.py:225` is `:207`. `asy_neopixel_driver.py:181` is `:168` and reads `-> None`: row 11 is
  unblocked.
- SPECIFICATION.md: `:660-676` is `:647-663`, `:1961` `:1948`, `:3070-3073` `:3057-3060`, `:11144-11173`
  `:11124-11153`, `:11260-11261` `:11240-11241`, `:11416` `:11396`, Part N `:13261` `:13240`.
- `pyproject.toml`, `tests_js/templates.test.js`, `validate.py`, `js/`, `html/` and the scripts: unchanged by B7.
- Row 21 is done by B7 (`State`, NotifyState, W67, the NP/NT rows); nothing of it is left for B8.

Base: `S/wt-b8` (`audit/r1-b8`) at `d6bc7617` (B1-B6 merged); line numbers are that tree's, before B7. Files:
`buildgen/` (the generated modules by their emitter `codegen.py`), `devices/*.toml`, `js/` and `html/` as frozen, the
stager's website half (`scripts/_stage_website.py`, `build_website.sh`, the stamp lines of `build_firmware.py`).
Sources: PLAN B8 row, plancheck B8.1-B8.K, scan D (rows B1-B7, G1-G31, D1-D4, H1-H32), scan2 G3 (S2-G3-1..17),
G4/G4b closure roots (G4R01, G4R08c/d, round-2 lines 44-52), DECREV 3.1/3.2, PICTURE 4-5, REPORT 3 and 6.4.
`review_hunks.py 25caf528 d6bc7617` leaves 463 unmarked hunks in `buildgen/` and `devices/`, and 361 in `js/`,
`html/` and the scripts named; rows 1-21 name them by mechanism, row 22 takes any they miss. B7 runs first and removes
its own rows in the three shared files; the lead re-bases these line numbers after B7 merges.
Every row: what (file:line) / decision / basis / the test that shows it (pinning tests that go first, by file:line).
Test files: TV = `tests_scripts/test_buildgen_validate.py`, EC = `tests_scripts/test_buildgen_error_contract.py`
(its rule rows; `:549` keeps one row per live rule, so a removed rule's row goes in the same change),
TG = `tests_scripts/test_buildgen_generate.py`, BE = `tests/test_generated_boot_entry.py`.

**1. I2C timeout rules** (`validate.py:88-96`, `:201-218`, `:591-611`, `:614-634`, calls `:1434`, `:1454`)
- decision: change. `bus.i2c-timeout-range` and `bus.i2c-timeout-max` become one 1..200,000 us check; the boot-clear
  budget (`_BOOT_CLEAR_BUDGET_MS`, `_check_boot_clear_budget`) and the loop-hold rule `bus.i2c-timeout-consumer` go;
  `smallest_hard_consumer()`/`HardConsumer` `:127-131`, `:1519-1532` stay for their readers (twin scenario
  `_digital_twin_scenarios.py:1269`, flash and bench lag tests, `test_timing_budget.py:67`). The constant's comment
  states the boot clear (2 buses x 11 waits x 200 ms = 4.4 s unfed under the 8 s watchdog) and rp2's `uint32_t`.
- basis: PLAN B8 ("the I2C timeout stays one 1-200,000 us range, `smallest_hard_consumer()` stays for its tests");
  S2-G3-1 (the budget is dominated: both buses at the bound build), S2-G3-2 (the watchdog branch never binds; only
  dev's link above ~575 ms `poll_idle_ms`), DECREV 3.2; rp2 `machine_i2c.c:47` (v1.29.0).
- test: go first TV `:668`, `:677`, `:699`, `:708`, `:720`, `:732`, `:742`, EC rows `:352`, `:353`, `:369-375`; TV
  `:633` and `:642` become one range test (0 and 200,001 refused, both bounds build); TV `:685` keeps its bound half,
  `:751` stays (the entry arms `_WDT_TIMEOUT_MS`); `test_digital_twin_scenarios.py:250` green.

**2. Build checks no device TOML can trip, none a boot refusal or loop** (about 200 `validate.py` lines)
- what and decision (remove, unless marked restore): `bus.i2c-frequency-range` `:582-590` with `_I2C_FREQUENCY_MAX_HZ`;
  `bus.uart-baudrate-range` `:949-957` (the port keeps its default for 0 or less, `machine_uart.c:286-288`); the
  rxbuf/txbuf lower bound `_UART_BUFFER_MIN` `:86` (the port raises a smaller one to 32, `:372-373`, `:387-388`;
  upper bound: row 3); `bus.uart-shared` `:980-999` (dev uses uart0 and uart1); `instance.uart-baud-mismatch`
  `:1112-1122` (a mismatch is a dead link, CLAUDE.md "diagnosed, never negotiated");
  `device.conn-fail-to-hotspot-range` `:456-465`;
  `device.hostname-label` `:424-431` with `_host_label_ok` `:1289-1293` (Wi-Fi's own default check stays, S2-G2-14);
  `instance.irq-pull-up-type` `:673-681`; `instance.name-ext-missing` `:842-850`; restore: `names.logger-collision` to
  the pre-audit instance-against-instance check (`25caf528:buildgen/validate.py:431-443`, keeping `rule=`/`fix=`),
  `_MANDATORY_MODULE_FILES` `:111-112` goes with it; `names.settings-key-collision` `:886-903` (only a buildgen edit
  repeats a key; the runtime's last-wins rule, owner 2026-08-12); `source.field-unknown` `:930-944` with
  `driver_registry.data_fields()` and its helpers `:189-244` and rule `source.fields-unreadable` (a misnamed field reads
  None: `asy_notification_service.py:225`, `asy_sgp40_driver.py:303`); restore: `wiring.warn-outside-notification`
  `:1210-1218` to the pre-audit skip (a warn_* off the notification is ignored; codegen reads only the notification's,
  `codegen.py:359-363`, `:721-732`).
- basis: PLAN B8 "Go: the build checks no device TOML can trip ... except those whose violation would make a boot
  refuse or loop"; D-H12, H13, H15, H16, H19, H20, H22b, H23, H24, H25 (H, "a TOML edit only"); G4R08d; owner,
  2026-10-28 06:43 ("building upon hypothetical findings is a clear no-go").
- test: go first TV `:650`, `:660`, `:1963`, `:2096`, `:1914`, `:283`, `:229`, `:248`, `:559`, `:567`, `:543`, `:899`,
  `:909`, `:929`, `:946`, `:1432`, `test_buildgen_driver_registry.py:163-214`; EC rows `:248`, `:330`, `:333`, `:350`,
  `:354`, `:363`, `:376`, `:385`, `:389`, `:411`, `:428`, `:439`; EC `:356` (txbuf 31) moves to 32,767; TV `:1983`
  keeps the upper edges; TV `:871` and EC `:407-410` green on the restored collision check; TV `:1414` changes first
  (a warn_* on scd30 builds and is emitted nowhere: red today), then green.

**3. Build checks that stay under the same condition** (keep)
- what: the UART timing ranges `:1134-1169` (B6's mirror of E91 and E76's horizon) and ring, cap and CRC checks
  `:1037-1132` (owner, OR143.a (2), OR116/OR123); rxbuf/txbuf above 32,766 (`machine_uart.c:374-375`, `:389-390` raise
  ValueError at construction: a boot loop); `device.hotspot-time-min-range` `:447-454` (above 35,791 minutes
  `Timer.init()`'s period overflows a machine int, outside `_arm_hotspot_timer()`'s `(MemoryError, OSError)` catch,
  `asy_wifi_service.py:330`, so the Wi-Fi task dies at each hotspot window up to a reboot; 0 arms a 1 us periodic
  alarm, `machine_timer.c:101-102`); keyword-only `_Default` parameters, `defaults.py:41` (a missing one raises
  TypeError at construction); `@limits` non-finite refusal (H22a, owner 2026-09-10).
- basis: PLAN B8's condition; plancheck B8.1/B8.3; by reading, not reproduced (For the lead, point 1).
- test: existing TV `:266`, `:276`, `:1866`, `:1926-1957`, `:2127-2202`; EC rows.

**4. Compile check of the generated text** (`generate.py:45-51`, its calls `:157`, `:161-162`)
- decision: remove. basis: D-H3 (H: a generator bug, never a TOML's), closure G4R08c; the generated tree is compiled by
  mpy-cross in every image build, by ruff and mypy (`pyproject.toml:367`) and by every test importing it.
- test: go first EC `:600-612`; TG and the generated-tree tests green.

**5. The boot entry's unread C-stack call** (`codegen.py:854` import, `:869` `report_if_fatal(ended)`)
- decision: remove. basis: PLAN B8 "Go: ... the boot entry's unread C-stack call"; S2-G3-5 (after `asyncio.run()` has
  raised, nothing reads `_fatal`; the supervisor's reader is gone); CARRY (B1 left it).
- test: change first TG `:151`, `:160`, `_shared_head` `:629`; BE `:33-34`, `:123`; red, then the emitter.

**6. The loop-end print at DebugLevel 0** (`codegen.py:865-871`: `sys.print_exception(ended)`, the `ended` pre-bind
`:856-857`, `pyproject.toml:192-195` F811) -- owner decided (O1)
- decision: remove the print: `except BaseException:` with `record_loop_end()` alone, so the pre-bind, its comment and
  the F811 exemption go (scan D B7, C of the print).
- basis: owner, 2026-11-03 20:40 UTC ("drop the traceback print and keep the start line, as you recommended"), under
  2026-11-02 20:53 ("There must be a mode which is really silent on the console, ever. That's level 0."); CARRY (B1
  replaced `console()` by an unconditional print); REPORT 3 keeps the label 22, not the print.
- test: change first TG `:154`, `:159-160` (body `record_loop_end()`, no binding), BE `:114-125` records
  `sys.print_exception` in the stub and asserts no call (red today); `test_ruff_exemptions_live.py` flags F811 stale.

**7. The no-autostart start line** (`codegen.py:839-847`, `pyproject.toml:196` T20) -- keep (owner, O1, 20:40 UTC)
- basis: OR86 (owner, 2026-09-28: "start it manually in Thonny's REPL mode and watch the console logs"); it prints
  before any firmware runs or reads the stored level; the print itself is OR86.a's agent integration.
- test: BE `:138-147` green.

**8. The boot entry, kept as landed** (`codegen.py:818-835`, `:848-874` less rows 5-6)
- what: `WDT()` first (OR31.a), `.frozen` first (OR59), the 100 B emergency buffer (REPORT 3, V1; the bench saw a bare
  `MemoryError:` without it), labels 21 and 22 (REPORT 3), `gc.threshold(32768)`, `new_event_loop()`.
- basis: PLAN B8 Keep; plancheck B8.K. test: TG `:121`, `:134`, `:145`; BE `:98`, `:128`, `:150`; twin loop-end file.

**9. The read triggers' bus-spread order** (`codegen.py:453-468`, `trigger_spread()` `:900-908`)
- decision: keep. basis: PLAN B8 Keep (OR47: "it's always only about sensors with bus access"), overriding plancheck
  B8.5; D V5 (equals construction order on all six devices). test: TG `:974`, `:979`, `:1033` green.

**10. The generated device module** (`codegen.py` hunks by D rows G1-G31)
- decision: keep G1-G21, G23-G31 (owner rows, D.md 2); `ResetBits` and `ConfigUnpersisted` are gone (B2, owner
  2026-11-02 21:11: "(a), remove both"); `State` (G22) is B7's. U10 names, the D.15 member order, `_lit()` and
  `_sorted_imports()` (OR22.a (2)) stay. test: TG's `test_real_device_*` set.

**11. `SetupFct`** (`asy_base_classes.py:50`, `Awaitable[object]` since B2)
- decision: change to `Callable[[], Awaitable[None]]` once B7 has turned `asy_neopixel_driver.py:181` to `None`;
  `UARTComm.setup()` keeps its bool (read by the link driver, never in a setup list, `codegen.py:756-768`).
- basis: CARRY_LATER (B8 line); PLAN R1's setup-bool rule. test: mypy's main pass over `build/generated_src` (a bool
  setup left in a list fails it).

**12. Website W1, the page build-date stamp** -- remove (owner, O2a, 2026-11-03 20:43 UTC: "Remove it")
- what: `js/shell.js:19-26`, `:57`, `:61`, `:118-121`; `js/main.js:9`, `:41`; `js/app.js:10`, `:94`;
  `scripts/_stage_website.py:10`, `:27-28`, `:469`, `:474-476`, `:486`, `:498-499`; `build_firmware.py:117-118`;
  `build_website.sh:6`, `:9`, `:14`, `:21`, `:30-35`, `:73-74`. The build date stays a firmware input
  (`codegen.py:432`, `:611`; owner 2026-10-05: "They must differ for being genuine").
- basis: S2-G3-14 (H, one request's window); DECREV 3.1 ("none"); OF-144 (agent, 2026-10-15); no owner agreement.
- test: go first `tests_js/shell.test.js:358-371`, `:373-386`, `:603-618`, `:653-690`; `test_build_website_sh.py:148`,
  `:165-169`; `test_build_firmware.py:81-82`; the watch's first-build reload cases green.

**13. Website W2, the non-object GET banner** (`js/render.js:619`, `:322`) -- restore (owner, O2b, 20:45 UTC: "Yes,
restore"): `25caf528:js/render.js:353` (`response.body === null`, the typing cast)
- basis: REPORT 6.4 (no agreement found); PLAN R1 (a branch that never runs becomes a typing-side form); every GET
  route answers an object. test: change first `tests_js/render.test.js:1557`.

**14. Website W3, a saturated counter shown as "65535+"** (`js/templates.js:429`, `js/api-contract.js:12`) -- keep
(owner, O2c, 20:47 UTC: "Yes, that was a good addition, keep it").
test: `tests_js/templates.test.js:1059-1061`, `:1209-1211`; `test_js_api_mirrors.py:129`, `:161`.

**15. Website W4, double stripes for Invalid and Failed** (`html/style.css:378-411`) -- restore the solid stripes of
`25caf528:html/style.css:325-346` (owner, O2d, 20:53 UTC: "No, don't keep it, ... color alone is fine."). test: none
(CSS only); the diff of those rules against `25caf528` is empty but for selectors renamed since.

**16. Website rows with a recorded agreement** (keep)
- what: the Build group with `BuildDate` (`definitions.py:107-115`; `buildDate` was in GET /system before the audit,
  `25caf528:buildgen/codegen.py:603`); `ResetBits`/`ConfigUnpersisted` rows already gone (B2); the rest of `js/`,
  `html/` and `definitions.py` by G3 5's mapping: watch, hidden-tab pause, back-off, in-place cards
  (`website-unattended` ok), ages and "clock mismatch", code buttons and tones, decimals (`website-display-details`),
  inert drawer, AA tokens, reduced motion (`website-accessibility`, OR132 "2a"), Back history (that item's note),
  dialogs and Clear (`dns-fallback-clear-confirm`), the Altitude warning (OR100 "20 c"), Device Clock (OR94 "15 a"),
  favicon (`favicon-inline` ok), the generated definitions (OR43.a (3)), the section hand-over (C of WS-3/WS-4,
  S2-G3-15), the "unavailable" marker (K).
- basis: OR43.a (2), owner "1. yes 2. yes 3. yes" (2026-09-26): every API value appears on the website.
- test: npm `test:unit`, `test_buildgen_definitions.py`.

**17. The browser's definitions validator** (`js/definitions.js:95-400`, `:482-530`; pre-audit `:100-219`)
- decision: restore the pre-audit scope (schema major, shape, pollGroup, intervals; lead decision 2); the per-hint
  validators go (~135 lines frozen into every image). basis: S2-G3-13 (X + OV: buildgen's `web.*` rules, the stager's
  `_check_inlined` `_stage_website.py:150-159`, two test tiers check the same generated, inlined file); round-2 root
  47. A malformed file cannot reach a built image, so no user sees a difference.
- test: go first the per-hint cases of `tests_js/definitions.test.js:33-255`; every device's generated definitions
  still validate; npm lint, typecheck, `test:unit` green.

**18. Buildgen host code kept as landed**
- what: the error contract H1/H2 (OR23.a (3)), the frozen set H4 and caches H5 (F, measured), the boot oracle H6
  (OR47.a (1); its third copy of two codegen rules is the independent oracle by design, `generate.py:138-139`), the REST
  reference H7, definitions H8, catalog H9, AST reads H27, GPIO table H28 (OR53), tag parsers H29 (L13), typed twin
  wiring H31 (strict mypy; addresses read from the drivers, P8), `class_has_read_triggers()` (G5), `_urgency`
  (S2-G3-17), one errcount table per group (S2-G3-9, form only, -0.2 KB gz), the remaining module tables (S2-G3-12
  shrinks with row 2), the watch's extra /status (S2-G3-16).
- basis: scan D 4-9, G3 6. test: the `tests_scripts/test_buildgen_*` set.

**19. Device TOMLs** (`devices/*.toml`)
- decision: keep: `bench` (OR78.a), `hardware_family` (OR141.a (1), "every recommendation stands as an owner
  decision"), `rx_ring`/`max_transfer_bytes` at the driver defaults (OR143.a (2)), `trigger_s` (U10), comment tags.
  The `@tunable` lines are R2's (Part N scope); `devices/wozi.toml:1`'s "exemplary/base" wording is R4's (DECREV 4.1).
  B6 changed no UART key, so nothing follows. test: `test_device_tomls.py`, every device builds.

**20. Stager and scripts**
- decision: keep `_stage_website.py` (E.md keep) and `build_website.sh` less row 12's lines. R2's, not B8's:
  `js/mock-server.js` (never staged, `_stage_website.py:490`), the rest of `scripts/`,
  `device_max_connections_by_name()` (`validate.py:1468-1472`, read by two tool sites only), and `HardConsumer.what`/
  `.relief`, unread once row 1's rule goes (every reader takes `.ms`).

**21. Shared files with B7**: B7 removes `State` (`codegen.py:305`, `definitions.py:692-694`), NotifyState, W67 and the
NP/NT rows; B8 owns no catalog row (ResetReason 21 and 22 stay with row 8).

**22. Every other hunk** against `25caf528`: restore it, or name it to the lead; comment-only hunks stay where they
state the current code (PLAN section 2, step 4; the review script marks it).

Proof check (PLAN 0) for rows 1, 2, 4, 5, 17 and the removals in 6, 12, 13 (the owner's): none has an observed or
reproduced failure, a measured gain or an owner approval (D-H3, H12-H26 H; S2-G3-1..3 dominated or unreachable;
S2-G3-5 no reader; S2-G3-13 X; S2-G3-14 H). Kept by proof: row 8's buffer and labels (REPORT 3), H5 (measured).
Legacy check (OR48.a): every generated-module change has its D.md row with a recorded reason (the WDT moved, OR31.a;
only read triggers staggered, WP7/OR47.a (3); boot order, OR75; UnixTime back, OR94.a (15)); nothing lost without one.
O1's answer drops the traceback legacy's loop end printed through pyexec (D-B6: `sensortask-wozi.py:610-613`).
Docs, same commit (lines before B7): SPECIFICATION.md A.7 `:660-676` (O1), `:1961` and `:11416` (W1), `:3070-3073`
(the budget), the rule list `:11144-11173`, `:11260-11261` (the source-field claim), Part N `:13261`
(`i2c.timeout_consumer_us` goes), Part H for rows 13 and 17. Each removed item: one knowledge line (what it refused or
did, why it went, code at `d6bc7617`). Gate: a website change also runs npm lint, typecheck and `test:unit`.

## Lead decisions (2026-11-03 21:29 UTC)

1. Row 2's `bus.i2c-frequency-range` goes: frequency 0 reaches `i2c_set_baudrate()`'s division
   (`pico-sdk/src/rp2_common/hardware_i2c/i2c.c:68`, its `invalid_params_if` compiled out), whose divide-by-zero calls
   `__aeabi_idiv0` (`pico_divider/divider_hardware.S:145`), and the toolchain's libgcc (13.2.1, thumb/v6-m) has that as
   a bare `bx lr`: no fault, so the bus runs at a wrong rate and reads fail with logged errors; no boot refusal or loop
   by reading. Row 3's three keeps stand: each one's violation raises at construction or kills the Wi-Fi task.
2. Row 17 is taken: the per-hint validators are hunks with no proof under PLAN 0, so the hunk rule restores the
   pre-audit scope; no user sees a difference.
3. Row 9 follows PLAN over plancheck B8.5 (PLAN wins, brief). Row 16 as drafted: `BuildDate` has OR43.a (2).
4. The drafter's source copy (`validate_pre.py.txt`) is deleted; nothing of it is kept.
5. B7 has taken the TS row (label and format included) with item 7; row 21 stands for the rest.
