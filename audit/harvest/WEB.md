# Harvest — WEB: Website

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: SETTLED 15, INVAR 25, MIRROR 73, LIMIT 89, RISK 4, ASSUME 35, PLATFORM 8, SUPPRESS 3, TODO 8, OPENQ 1, DRIFT 20, NOTE 5 — 286 items.


## ext/freezefs/archive.py

- **WEB.N001** LIMIT · `ext/freezefs/archive.py:12, 30-31` — "MAX_FILENAME_LEN = 255 ... raise
  ValueError(f\"File name too long {self.mp_path}\")" — Build fails on a website path ≥255 chars (low) ·
  [H02]
- **WEB.N002** ASSUME · `ext/freezefs/archive.py:90, 96, 144-145` — "for path in
  glob(os.path.join(pc_infolder, \"**\"), recursive=True):" / "date_frozen = const( ... time.localtime()
  ...)" — Output embeds local build time; ordering sorted by path — reproducibility items · related:
  SCR.S04 · [H02]
- **WEB.N003** LIMIT · `ext/freezefs/archive.py:295-297` — "This is the only combination that is heavy
  in RAM use... --on-import=mount and --compress loads file in RAM" — Why the project never uses
  `--compress` (build script) · [H02]
- **WEB.N004** LIMIT · `ext/freezefs/archive.py:165-171` — "Don't copy comments nor empty lnes / Make
  indents one by one instead of by four" — Generator rewrites the mount driver textually (4 spaces → 1)
  into the frozen module; relies on the driver's formatting (low) · [H02] ⟨quote not matched at the
  anchor⟩

## tests/test_website_build_integration.py

- **WEB.N005** INVAR · `tests/test_website_build_integration.py:5-7` — "scripts/test.sh builds it first;
  the import mounts /html once per process" — Depends on test.sh having built
  frozen_modules/frozen_html.py for wozi before this file runs; only one device's build is tested ·
  [H05]
- **WEB.N006** MIRROR · `tests/test_website_build_integration.py:73-75, 102-103, 119-128` — "The seven
  production modules are concatenated into one js/app.js at staging time (Part H.7)" — The test
  hand-lists the seven js modules and their distinctive declarations; a new js module needs a manual
  update here · [H05]
- **WEB.N007** LIMIT · `tests/test_website_build_integration.py:132-137` — "A leftover `export { ... } from "./local-file.js";`
  re-export ... is not caught by the import-line check above - checked directly after a real instance
  ... was caught only by manually tracing the build" — The bundle's integrity is checked by string
  patterns, each added after a manual find · [H05]

## digital_twin/README.md

- **WEB.N008** MIRROR · `digital_twin/README.md:838-842` — "**Update `html/definitions/<device>.json`**
  ... skipping this step leaves the driver ... permanently invisible on the website" — New-driver
  obligation to the website definitions (review-only) · [H06]

## tests/test_digital_twin_real_website_integration.py

- **WEB.N009** ASSUME · `tests/test_digital_twin_real_website_integration.py:304-306` — "A real browser
  opens two connections per page load after bundling/inlining (Part H.7)" — Browser behaviour assumption
  sizing the burst · [H06]

## mockdata/dev.json, mockdata/wozi.json (no comments — JSON; provenance stated elsewhere)

- **WEB.N010** LIMIT · `SPECIFICATION.md:4286` — "mockdata/ Prototype-only mock backend fixtures - NOT
  shipped" — Stated provenance: hand-written prototype fixtures for `js/mock-server.js`. · related:
  WEB.T15 · [H08]
- **WEB.N011** LIMIT · `SPECIFICATION.md:5900-5903` — "a hand-written website-prototype fixture that can
  predate the real driver, carrying placeholder field names" — Stated fidelity limit, "found-twice gap";
  checked only by manual K.8 and K.11 checklist steps (:5972). · covered-by: WEB.T15 · [H08 (also H13)]
- **WEB.N012** LIMIT · `BACKLOG.md:779-782` — "`mockdata/`/`html/definitions/` only carry fixtures for
  those two devices" — Only wozi and dev have fixtures; the other four devices have none. · covered-by:
  WEB.T12 · [H08]
- **WEB.N013** DRIFT · `mockdata/dev.json:5-6, 13-14, 65-75` — "\"SHTC3\": { \"Temp\": 23.3" — dev
  fixture carries SHTC3 and MPRLS measurements/config/errcount, which `devices/dev.toml` does not wire
  (dev_legacy/README.md:52: SHTC3 "not present"). · related: WEB.T15 · [H08]
- **WEB.N014** DRIFT · `mockdata/dev.json:10-20, 46-89` — "\"sensorsConfig\": {" — dev fixture has no
  BMP3XX `sensorsConfig`, no `BMP3XX`/`CFGMGR_BMP3XX`/`UART_init`/`UART_resp` errcount entries although
  dev wires BMP3xx and two uart_link instances (it does carry `UARTLINK` status);
  `tests_js/definitions-mockdata-coverage.test.js` checks readonly fields only. · related: WEB.T15 ·
  [H08]
- **WEB.N015** MIRROR · `mockdata/dev.json:22, mockdata/wozi.json:16` — "\"PW\": \"testbench42\"" —
  Placeholder plaintext passwords in fixtures; masking mirrors `src/asy_wifi_service.py`'s `_mask_pw()`
  in `js/mock-server.js:459-461`. · related: NET.S16 (low) · [H08]

## scripts/build_website.sh

- **WEB.N016** TODO · `scripts/build_website.sh:26-27` — "retiring them is deferred work
  (SPECIFICATION.md Part L.4)" — wozi/dev keep hand-written `html/definitions/<device>.json` because
  tests_js fixtures load them from disk. · related: WEB.S13 · [H09]
- **WEB.N017** INVAR · `scripts/build_website.sh:20-22` — "a generated definitions.json written there
  would be frozen as an extra /definitions.json.gz and defeat H.7's inlining" — Generated definitions
  must stay in `scratch_dir`, never `stage_dir`. · related: WEB.T06 · [H09]
- **WEB.N018** INVAR · `scripts/build_website.sh:53-57` — "escaping every one of them is what stops a
  field value containing \"</script\" from closing the tag early" — Inlined definitions JSON must have
  every `<` escaped. · related: WEB.T06 · [H09]
- **WEB.N019** MIRROR · `scripts/build_website.sh:59-67` — "html/index.html's stylesheet <link> tag not
  found - update build_website.sh" — Exact-string contract with `html/index.html` (`<link rel=\"stylesheet\" href=\"style.css\">`,
  `</head>`); fails loudly on drift. · related: WEB.T06 · [H09]
- **WEB.N020** MIRROR · `scripts/build_website.sh:75-78` — "concatenation of js/field-format.js,
  poll-manager.js, templates.js, definitions.js, render.js, nav.js, main.js (in that dependency order)"
  — Hand-kept bundle order duplicated in the banner and the loop; the banner points to "this script's
  own header comment for why", which now just defers to Part H.2. · covered-by: WEB.S14 · [H09]
- **WEB.N021** LIMIT · `scripts/build_website.sh:81` — "grep -v -E '^import .* from
  \"\./[^\"]+\.js\";$'" — Import stripping matches only single-line, double-quoted, semicolon-terminated
  relative imports. (low) · related: WEB.T06 · [H09]

## scripts/cross_browser_smoke.mjs

- **WEB.N022** LIMIT · `scripts/cross_browser_smoke.mjs:38-44` — "WebKit and Firefox have no
  device-emulation API over plain WebDriver ... MOBILE_VIEWPORT is a request, not a guarantee" — Mobile
  check on WebKit/Firefox is a window resize only (no touch/UA), and the width lands at ~447-500 px. ·
  [H09] ⟨quote not matched at the anchor⟩
- **WEB.N023** ASSUME · `scripts/cross_browser_smoke.mjs:304-306` — "Polling only the attribute raced
  ahead of the caption during this file's own development" — Wait condition derived from an observed
  race. · [H09]
- **WEB.N024** ASSUME · `scripts/cross_browser_smoke.mjs:354-356` — "Given a real DISPLAY, `-headless`
  Firefox still uses it ... confirmed directly" — Engine behaviour claim. (low) · [H09]
- **WEB.N025** ASSUME · `scripts/cross_browser_smoke.mjs:471-473` — "an earlier version reused one and
  briefly masked a real timing bug" — Unique probe values per check are load-bearing. · [H09]

## buildgen/definitions.py

- **WEB.N026** MIRROR · `buildgen/definitions.py:25-37` — "Fixed, generator-owned REST-endpoint skeleton
  (H.4: \"Nav grouping: Mirrors the 6 REST endpoints 1:1\")" — Section skeleton (incl. `pollIntervalMs: 3000`)
  hand-mirrors the REST surface. · related: WEB.T05 · [H09]
- **WEB.N027** MIRROR · `buildgen/definitions.py:52-85` — "Each mirrors its own source in
  asy_webserver_service.py - lightCmdLED's bounds from _dispatch_notification_led(), SystemCmd from
  _SYSTEM_CMDS" — Dispatch-group bounds/options hand-mirrored from `src/asy_webserver_service.py` (and
  codegen's `_FIELD_LED_*`). · related: WEB.T04 · [H09]
- **WEB.N028** MIRROR · `buildgen/definitions.py:373-375, 468-473` — "matching every hand-written
  definitions.json's own fixed ordering" — Generated order must match the hand-written wozi/dev
  definitions. · covered-by: WEB.S13 · [H09]

## tests_scripts/test_build_website_sh.py

- **WEB.N029** LIMIT · `tests_scripts/test_build_website_sh.py:113-127` — "build_website.sh's cp lists
  are hand-kept ... Cross-checking the directories against the script's source makes that loud." — Guard
  is a substring match of each html/ root file and js/*.js name anywhere in the script text (a comment
  mention passes); html/ subdirectories and non-.js files under js/ are not checked · covered-by:
  WEB.S14 · [H10]
- **WEB.N030** LIMIT · `tests_scripts/test_build_website_sh.py:71-73` — "Four devices have no
  hand-written definitions.json ... \"arzi\" stands in for all four." — Only arzi exercises the
  buildgen-fallback path here; the count "four" is a dated claim · related: WEB.T12 · [H10]
- **WEB.N031** LIMIT · `tests_scripts/test_build_website_sh.py:49-55` —
  "test_prototype_only_files_are_never_staged" — Negative list is four hand-named paths (mock-server.js,
  definitions/*.json); a new prototype-only file is caught only by the :113 guard · [H10]

## tests_scripts/test_buildgen_definitions.py

- **WEB.N032** LIMIT · `tests_scripts/test_buildgen_definitions.py:39-41,62-67` — "comparison is
  insensitive to this generator's own field/group declaration order" — Golden comparison only for
  wozi/dev and order-insensitive, so field-order differences between generated and hand-written
  definitions pass · covered-by: WEB.S13 · [H10]
- **WEB.N033** MIRROR · `tests_scripts/test_buildgen_definitions.py:126-129,132-170` — "mirrors
  js/definitions.js's validateDefinitions() closely enough to prove a generated file would load" —
  Python re-implementation of the JS loader's shape check; no Node round trip, and drift between
  `_shape_problems` and `validateDefinitions()` is not detected · related: GEN.T15 · [H10]

## tests_scripts/test_buildgen_web_tag.py

- **WEB.N034** MIRROR · `tests_scripts/test_buildgen_web_tag.py:127-128` — "js/definitions.js's own
  validateFieldHints() enforces the identical rule" — `path` only on readonly fields — enforced in both
  buildgen/web_tag.py and js/definitions.js · related: GEN.T15 · [H10]
- **WEB.N035** SETTLED · `tests_scripts/test_buildgen_web_tag.py:500-501` — "GMTOffset/DSTOffset ...
  render on the System page instead (a deliberate cross-file section/group assignment, not a mistake to
  \"fix\")" — Deliberate placement of NTP timezone fields · [H10]

## tests_scripts/test_digital_twin_generated_boot.py

- **WEB.N036** MIRROR · `tests_scripts/test_digital_twin_generated_boot.py:113-133` — "The API derives
  itself from the live object graph; buildgen/definitions.py's catalog is hand-kept. Both drift
  directions are silent in the product" — Enforces /status errcount keys == website errcount rows at
  twin boot (per logger instance since 2026-09-18) · related: GEN.T06 · [H10]

## tests_scripts/test_live_twin_ceiling_parser.py

- **WEB.N037** MIRROR · `tests_scripts/test_live_twin_ceiling_parser.py:1-3` —
  "configuredMaxConnections() sizes the browser tier's tab count, so it must resolve every device's
  ceiling exactly as buildgen does" — JS line-matching TOML reader in tests_js/_live_twin_command.js ↔
  buildgen.validate.device_max_connections (enforced for real TOMLs + 4 synthetic shapes) · related:
  GEN.T15 · [H10]

## tests_scripts/test_request_timeout_ceiling.py

- **WEB.N038** MIRROR · `tests_scripts/test_request_timeout_ceiling.py:62-70` — "CLAUDE.md's src/<->js/
  cross-language mirror obligation (SPECIFICATION.md Part G) applied to the one number" —
  js/poll-manager.js `DEFAULT_TIMEOUT_MS` must equal src `outer_cap_s` (enforced); the plan notes the
  client clock starts before connect while the server's starts at accept · related: WEB.S06 · [H10]

## js/app.js

- **WEB.N039** SETTLED · `js/app.js:2-4` — "The `?device=` switch below is prototype-only (real firmware
  ships exactly one device's definitions.json, never branches on a query param)" — js/app.js is the
  prototype-only entry; production entry is js/main.js; any audit of the real build must look at
  main.js, not app.js · related: WEB.S18 · [H11]
- **WEB.N040** LIMIT · `js/app.js:15-16` — "const KNOWN_DEVICES = [\"wozi\", \"dev\"];" — prototype only
  knows two of the six devices; an unknown `?device=` silently falls back to wozi (:29) rather than
  erroring · covered-by: WEB.S22 · [H11]
- **WEB.N041** LIMIT · `js/app.js:46` — "fetchWithTimeout(`../mockdata/${device}.json`)" — prototype
  depends on a `mockdata/` fixture existing per device outside `html/`; only wozi/dev have one, so the
  other four devices cannot run in the prototype at all · related: WEB.T12 · [H11]
- **WEB.N042** ASSUME · `js/app.js:53` — "response was not valid JSON (likely a corrupted or truncated
  transmission)" — a JSON parse failure is presumed to be a transmission error, not a malformed fixture
  (low) · [H11]
- **WEB.N043** MIRROR · `js/app.js:72-84 vs js/main.js:45-57` — "selectSection" — `selectSection()` and
  the startup/error-banner logic are duplicated verbatim between the prototype and production entry
  points; a fix to one must be copied to the other · covered-by: WEB.S18 · [H11]
- **WEB.N044** ASSUME · `js/app.js:76-78` — "Defensive only: every real sectionKey traces back to
  defs.sections itself ... so this can't currently fire." — relies on validateDefinitions() rejecting a
  landingSection that matches no section key (it does, definitions.js:183-185); unreachable branch by
  stated assumption (same text at js/main.js:49-51) · [H11]

## js/field-format.js

- **WEB.N045** INVAR · `js/field-format.js:2-3` — "split out of js/templates.js so a Node-context test
  harness can reuse it with no DOM dependency" — this module must stay DOM-free because the Node-context
  live-matrix harness imports it (tests_js/_live_matrix_command.js); convention only, no lint rule
  enforces it (low) · [H11]
- **WEB.N046** SETTLED · `js/field-format.js:6-7` — "Deliberately a narrow local shape, not
  `import(\"./definitions.js\").FieldDef` - see SPECIFICATION.md Part H.8.1 for why." — deliberate
  narrow local type instead of FieldDef; not to be "tidied" into the shared typedef · [H11] ⟨quote not
  matched at the anchor⟩
- **WEB.N047** DRIFT · `js/field-format.js:27-28` — "Real shape: src/sensortask_wozi.py's
  _gmtimestruct_to_dict()" — src/sensortask_wozi.py no longer exists; the helper is generated from
  buildgen/codegen.py:518 · covered-by: WEB.S21 · [H11]
- **WEB.N048** MIRROR · `js/field-format.js:27-31 vs buildgen/codegen.py:518,588` — "{year, month, mday,
  hour, minute, second, weekday} (weekday unused here), never a pre-formatted string" — the JS
  `gmtimestruct` formatter hard-codes the key names of the generated `_gmtimestruct_to_dict()` output; a
  key rename on the Python side breaks rendering silently (NaN-free but "undefined" text) · [H11] ⟨quote
  not matched at the anchor⟩
- **WEB.N049** ASSUME · `js/field-format.js:33-35` — "the one place in the stack that rounds an emitted
  value: no driver in src/ rounds anything, so without this a declared precision is an aspiration." —
  states that no src/ driver rounds values and that JS `decimals` is the sole rounding point; a
  cross-tree claim an auditor should verify · [H11]
- **WEB.N050** LIMIT · `js/field-format.js:29-31` — "const t = /** @type {...} */ (value);" —
  gmtimestruct branch casts without checking the value is an object; a scalar or partial struct renders
  as "undefined-undefined..." rather than "—" (low) · [H11]

## js/main.js

- **WEB.N051** SETTLED · `js/main.js:1-5` — "Real production entry point - no mock, one build-fixed
  device, no `?device=` switch. Staged into the frozen build as `app.js`" — production entry is renamed
  to app.js at staging time; auditors reading "app.js" in build artifacts must map it to js/main.js, not
  js/app.js · related: WEB.T06 · [H11]
- **WEB.N052** MIRROR · `js/main.js:26` — "loadDefinitions(\"definitions.json\", inlinedDefinitionsEl)"
  — production relies on scripts/build_website.sh inlining definitions into index.html (the
  `inlinedDefinitionsEl`), with a fetch fallback to a staged definitions.json · related: WEB.T06 · [H11]
- **WEB.N053** ASSUME · `js/main.js:49-51` — "Defensive only: ... so this can't currently fire." — same
  unreachable-branch assumption as js/app.js:76-78 · covered-by: WEB.S18 · [H11]

## js/definitions.js

- **WEB.N054** ASSUME · `js/definitions.js:1-4` — "strictly validates a device's definitions.json ... A
  shape/version mismatch surfaces a visible error rather than ... skipping unknown fields" — claims
  strict validation, yet validateDefinitions() never checks field kind, key, label or unknown properties
  (only path/decimals hints), so an unknown kind renders as a text input · covered-by: WEB.S18 · [H11]
  ⟨quote not matched at the anchor⟩
- **WEB.N055** MIRROR · `js/definitions.js:44-46` — "float?: true marks a \"number\"-kind field whose
  real server-side type is Python float, not the int default (SPECIFICATION.md Part A.8)" — the `float`
  flag must match each src/ FieldSchema's "float"/"int" type; mismatch makes the client accept or reject
  fractional values differently from the server · related: WEB.T04 · [H11]
- **WEB.N056** MIRROR · `js/definitions.js:48-49` — "errcount history shape matches
  print_log.py/asy_webserver_service.py exactly: no per-entry timestamp exists" — the errcount history
  typedef mirrors src/print_log.py + src/asy_webserver_service.py; "type" only colours, never shown as
  text · related: WEB.S08 · [H11]
- **WEB.N057** INVAR · `js/definitions.js:51-53` — "collectGroupBody() must always resubmit it, unlike
  an ordinary sparse-omitted-when-unchanged persisted field" — `dispatch: true` fields must mirror
  SPECIFICATION.md Part H.6's dispatch-only list, and render.js must always resubmit them · covered-by:
  WEB.S02 · [H11] ⟨quote not matched at the anchor⟩
- **WEB.N058** ASSUME · `js/definitions.js:55-56` — "defaultValue is a field's safe synthetic baseline
  for when GET never reports a real value (a command with no persisted state, e.g. SCD30's ContMeas)" —
  a synthetic baseline stands in for a value the device never reports; interacts with baseline movement
  after Apply · related: WEB.S01 · [H11]
- **WEB.N059** MIRROR · `js/definitions.js:58-59` — "The only schema major version this build of the
  renderer understands." — `SUPPORTED_SCHEMA_MAJOR = 1` must agree with the schemaVersion buildgen emits
  and the hand-written html/definitions/*.json declare (buildgen `SCHEMA_VERSION`) · covered-by: GEN.T15
  · [H11]
- **WEB.N060** RISK · `js/definitions.js:61-63` — "so it is unvalidated too, and a bad value costs
  provenance, not rendering" — websiteVersion is accepted unvalidated and rendered nowhere; accepted as
  costing provenance only · related: WEB.S20 · [H11]
- **WEB.N061** INVAR · `js/definitions.js:66-68` — "Callers use this instead of reading
  `currentValues[field.key]` directly, so rendering and change-comparison never drift apart." —
  caller-discipline rule, not enforced; the plan already found a caller that bypasses it · covered-by:
  WEB.S10 · [H11]
- **WEB.N062** ASSUME · `js/definitions.js:70-72` — "readonly fields only, a PUT body being always flat"
  — `path` is restricted to readonly fields on the stated assumption that PUT bodies are always flat;
  enforced by validateFieldHints (:207-211) · [H11]
- **WEB.N063** LIMIT · `js/definitions.js:164-165` — "if (typeof g.key !== \"string\" || typeof g.label
  !== \"string\")" — a group entry is dereferenced before any object/null check (a `null` group throws
  instead of reporting a problem); duplicate section/group/field keys are not detected · covered-by:
  WEB.S23 · [H11]
- **WEB.N064** DRIFT · `js/definitions.js:201` — "return problems; // the group-level shape checks above
  already own this case" — the group-level loop only checks `Array.isArray(g.fields)` (:174), never that
  each field is a non-null object, so a `null`/scalar field produces no problem at all (low) · related:
  WEB.S23 · [H11]
- **WEB.N065** MIRROR · `js/definitions.js:213-216` — "f.decimals > 100" — the 0-100 `decimals` bound
  must match buildgen `web_tag._MAX_DECIMALS` (and tests_js/definitions.test.js:196-198's 101 probe) ·
  covered-by: GEN.T15 · [H11]
- **WEB.N066** PLATFORM · `js/definitions.js:213-214` — "100 is Number#toFixed's own ceiling, above
  which it throws a RangeError" — depends on the ES2018+ `toFixed` range (0-100); engines predating that
  throw above 20, so this is a browser-floor dependency · related: WEB.T09 · [H11]
- **WEB.N067** INVAR · `js/definitions.js:223-225` — "Never queried from `document` here - callers pass
  the element down, matching this module's usual convention." — the H.3 layering convention (no
  `document` queries in non-entry modules) is upheld by convention only · related: WEB.T11 · [H11]
- **WEB.N068** MIRROR · `js/definitions.js:231-233` — "A real device build inlines definitions.json
  straight into index.html (cuts one connection per page load); dev/preview mode never has this element"
  — depends on scripts/build_website.sh producing the inlined `<script type="application/json">`
  element; dev/preview never exercises the inlined path · related: WEB.T06 · [H11]
- **WEB.N069** ASSUME · `js/definitions.js:247-249` — "A genuine transmission error (truncated/corrupted
  response)" — any JSON parse failure of a fetched definitions.json is attributed to transmission, not
  to a bad build (low) · [H11]

## js/mock-server.js

- **WEB.N070** SETTLED · `js/mock-server.js:1-4` — "Prototype-only fake backend ... Replaced by the
  digital twin's real server per SPECIFICATION.md Part H.7 - everything outside this file targets the
  real API." — the mock is confined to the prototype; all other JS must target the real API contract ·
  related: WEB.T04 · [H11]
- **WEB.N071** MIRROR · `js/mock-server.js:7-14` — "const REST_PATHS = ... \"/measurements\",
  \"/sensors\", \"/networking\", \"/system\", \"/notification\", \"/status\"" — the six intercepted
  paths must match src/asy_webserver_service.py's REST routes; a new route is silently passed through to
  the real fetch · related: WEB.T04 · [H11]
- **WEB.N072** MIRROR · `js/mock-server.js:16` — "const SYSTEM_CMDS = [\"reboot\", \"bootloader\",
  \"mempause\"];" — copied constant; other end is src/asy_webserver_service.py:95 `_SYSTEM_CMDS` ·
  related: WEB.T04 · [H11]
- **WEB.N073** MIRROR · `js/mock-server.js:17` — "const PAUSE_TIME_MAX = 3600; // matches
  src/asy_webserver_service.py's own _PAUSE_TIME_MAX" — copied constant; other end is
  src/asy_webserver_service.py:98 · related: WEB.T04 · [H11]
- **WEB.N074** MIRROR · `js/mock-server.js:19-22` — "The /sensors fields with documented hardware quirks
  (Part H.4): each is a hardware dispatch re-run on every submit" — hard-coded `SENSOR_QUIRK_FIELDS`
  (ForceCalRef, ContMeas, SGPResetVOC, ISLCalibrate) must track every dispatch-only sensor field in src/
  drivers; a new one would be store-and-echoed wrongly · related: WEB.T04 · [H11]
- **WEB.N075** MIRROR · `js/mock-server.js:31-32` — "the real backend does a strict type() check before
  ever looking at magnitude, so a JSON string (even \"42\") is rejected outright" — number-kind
  strictness mirrors src/ config validation · related: WEB.T04 · [H11]
- **WEB.N076** MIRROR · `js/mock-server.js:36-38` — "Mirrors the real int<->float policy
  (SPECIFICATION.md Part A.8)" — int-typed fields reject fractional values, float-typed accept any
  finite; must match src/ validation · related: WEB.T04 · [H11]
- **WEB.N077** MIRROR · `js/mock-server.js:43-46` — "specialValues.some((special) => special.value ===
  value)" — a special value bypasses min/max; must match server-side special-value handling (low) ·
  related: WEB.T04 · [H11]
- **WEB.N078** MIRROR · `js/mock-server.js:52-54` — "the real backend's type_or_range_error() rejects a
  non-str JSON value outright" — string strictness mirrors src/ `type_or_range_error()` · related:
  WEB.T04 · [H11] ⟨quote not matched at the anchor⟩
- **WEB.N079** LIMIT · `js/mock-server.js:59-61` — "value.length >= minLength && value.length <=
  maxLength" — mock counts UTF-16 code units, the server counts UTF-8 bytes · covered-by: WEB.S12 ·
  [H11]
- **WEB.N080** MIRROR · `js/mock-server.js:64-66` — "an enum's real value can be numeric (e.g. BMP3XX's
  PressOvers), and needs the same int-only strictness as an ordinary int field" — enum strictness
  mirrors src/ · related: WEB.T04 · [H11]
- **WEB.N081** LIMIT · `js/mock-server.js:76` — "return { valid: true, value: rawValue };" — any other
  kind (e.g. a `readonly` key sent in a PUT) is accepted as valid and stored by the mock; server
  behaviour for such keys is not modelled (low) · related: WEB.T04 · [H11]
- **WEB.N082** LIMIT · `js/mock-server.js:131` — "unknown field - silently ignored, matches
  ConfigManager's own convention" — parity claim the plan found false (server reports Invalid + errno 10
  for an unknown /sensors sub-key) · covered-by: WEB.S12 · [H11]
- **WEB.N083** LIMIT · `js/mock-server.js:133-142` — "results[key] = allValid ? \"Valid\" :
  \"Invalid\";" — composite fields are validated but never stored and never report "Unchanged" (low) ·
  related: WEB.T04 · [H11]
- **WEB.N084** MIRROR · `js/mock-server.js:159-162` — "matching a real dispatched action (PauseTime)
  that never reports \"Unchanged\" the way a genuine persisted setting does" — PauseTime dispatch
  semantics mirror src/ · related: WEB.T04 · [H11]
- **WEB.N085** DRIFT · `js/mock-server.js:178-180` — "Legacy's own led_cmd() bounds
  (modules/sensortask-wozi.py), now enforced server-side too (src/sensortask_wozi.py's
  _notification_led_callback()" — src/sensortask_wozi.py no longer exists (buildgen-generated) ·
  covered-by: WEB.S21 · [H11]
- **WEB.N086** MIRROR · `js/mock-server.js:181-184` — "LIGHT_CMD_LED_RGB_MAX = 255; ...
  LIGHT_CMD_LED_T_MIN = 0.5; LIGHT_CMD_LED_T_MAX = 60.0;" — copied lightCmdLED bounds; other end is the
  generated notification LED callback's FieldSchema records (buildgen) and legacy led_cmd() · related:
  REST.S10 · [H11] ⟨quote not matched at the anchor⟩
- **WEB.N087** MIRROR · `js/mock-server.js:186-189` — "\"Invalid\" only when the payload isn't an
  object; \"Failed\" when r/g/b (int, 0-255) or t (float, 0.5-60.0) is missing/wrong-typed/out-of-range"
  — the Invalid/Failed split for lightCmdLED is a mirrored contract · related: REST.S10 · [H11]
- **WEB.N088** LIMIT · `js/mock-server.js:217-220` — "\"Valid\"/\"Invalid\" only (no real I2C bus to
  fail)" — mock never returns "Failed" for sensor dispatch fields, so client handling of a
  hardware-failed dispatch is not exercised by the mock · related: WEB.T15 · [H11]
- **WEB.N089** MIRROR · `js/mock-server.js:232-235` — "`ForceCalRef` always reports 400 (SCD30's
  volatile register), and the three command-only triggers are omitted entirely as the real schema omits
  them" — GET readback quirks mirror the SCD30 driver and the real schema; 400 is also
  src/asy_scd30_driver.py:61's range floor · related: WEB.T04 · [H11]
- **WEB.N090** MIRROR · `js/mock-server.js:244` — "key !== \"ContMeas\" && key !== \"SGPResetVOC\" &&
  key !== \"ISLCalibrate\"" — a second hard-coded list of command-only triggers, duplicating
  SENSOR_QUIRK_FIELDS minus ForceCalRef; the two must be kept in sync (low) · [H11]
- **WEB.N091** LIMIT · `js/mock-server.js:251-254` — "Simulates the backend's known gap (Part H.6): a
  settings group's post-write hook raising drops that group's fields from `result`" — the
  `partial-result` injection models a server gap the plan says is already fixed · covered-by: WEB.S12 ·
  [H11]
- **WEB.N092** LIMIT · `js/mock-server.js:263-266` — "const [key] = Object.keys(results);" —
  partial-result drops only the first key, not a whole settings group as the docstring describes (low) ·
  related: WEB.S12 · [H11]
- **WEB.N093** MIRROR · `js/mock-server.js:273-275` — "return { res: \"OK\", code: 0, descr: \"OK\",
  result };" — response envelope mirrors src/api_response.py · related: WEB.T04 · [H11]
- **WEB.N094** LIMIT · `js/mock-server.js:277-280` — "Timestamp-looking keys (ending \"TS\" or named
  \"Timestamp\") always increment instead of jittering." — recursive jitter random-walks non-measurement
  values and corrupts nested time structs · covered-by: WEB.S12 · [H11]
- **WEB.N095** DRIFT · `js/mock-server.js:294-280 vs :296 (agent cited js/mock-server.js:279-280 vs :296)`
  — "key.endsWith(\"TS\") || key === \"Timestamp\" || key.endsWith(\"Uptime\")" — the docstring omits
  the third `Uptime` rule the code applies (low) · [H11] ⟨re-anchored: quote found at line 294⟩
- **WEB.N096** LIMIT · `js/mock-server.js:299-301` — "Spread and rounding were sized for readings of
  order hundreds (CO2 ~600)." — jitter amplitude/rounding is a heuristic tuned per magnitude, not a
  model of real sensor noise (low) · related: WEB.T15 · [H11]
- **WEB.N097** LIMIT · `js/mock-server.js:338-341` — "REST_PATHS.find((candidate) => url === candidate
  || url.startsWith(`${candidate}?`))" — only exact relative paths are intercepted; an absolute URL or
  trailing slash passes through to the real fetch (low) · [H11]
- **WEB.N098** MIRROR · `js/mock-server.js:353-356` — "Matches the backend's own make_response(1) (Part
  A.8/A.5): a body Request.json cannot parse ... is a clean HTTP 200 with res:\"ERR\"" — malformed-body
  injection mirrors the server; the mock's own un-injected handling of a malformed body differs
  (JSON.parse throws) · covered-by: WEB.S12 · [H11]
- **WEB.N099** LIMIT · `js/mock-server.js:366` — "jsonResponse({ res: \"ERR\", code: 5, descr:
  \"Simulated failure\" }, failure)" — a numeric injected failure returns an envelope with no `result`
  key and fixed code 5 regardless of status (low) · related: WEB.T04 · [H11]
- **WEB.N100** LIMIT · `js/mock-server.js:369-371` — "setTimeout(resolve, 80 + Math.random() * 120);" —
  random 80-200 ms latency per request makes mock-backed tests timing-nondeterministic · covered-by:
  WEB.T15 · [H11]
- **WEB.N101** LIMIT · `js/mock-server.js:373-375` — "const rawBodyText = String(init?.body ?? \"{}\");
  ... JSON.parse(rawBodyText)" — an absent body is treated as `{}`; an unparseable or non-object body
  throws inside fetch instead of the server's clean res:"ERR" · covered-by: WEB.S12 · [H11]
- **WEB.N102** LIMIT · `js/mock-server.js:383-387` — "if (sensorDefs === undefined) { continue; }" —
  unknown sensor key in a /sensors PUT is silently dropped from the result · covered-by: WEB.S12 · [H11]
- **WEB.N103** LIMIT · `js/mock-server.js:415-418` — "const { SystemCmd, PauseTime, lightCmdLED,
  ...persistableBody } = rawBody;" — the three action keys are stripped on all three endpoints, so e.g.
  `SystemCmd` sent to /networking vanishes from the result instead of being reported (low) · related:
  WEB.T04 · [H11]
- **WEB.N104** MIRROR · `js/mock-server.js:415-418` — "which is what keeps a later GET matching
  _get_settings_flat()." — mock GET shape for settings endpoints mirrors
  src/asy_webserver_service.py:436 `_get_settings_flat()` · related: WEB.T04 · [H11]
- **WEB.N105** MIRROR · `js/mock-server.js:436-438` — "Real reset() (src/print_log.py) refills the
  fixed-length history with \"no error\" placeholders, it never shrinks/empties the array." —
  ResetErrors semantics mirror src/print_log.py reset() · related: WEB.T04 · [H11]
- **WEB.N106** LIMIT · `js/mock-server.js:432-441` — "if (body().ResetErrors === true) { ... } return
  jsonResponse({ res: \"OK\", code: 0, descr: \"OK\" });" — /status PUT returns no per-field `result`
  map and ignores every other key (including a non-true ResetErrors) (low) · related: WEB.T04 · [H11]
- **WEB.N107** MIRROR · `js/mock-server.js:443` — "jsonResponse({ res: \"ERR\", code: 4, descr: \"Method
  not allowed\" }, 405)" — 405 envelope and code 4 mirror the server (low) · related: WEB.T04 · [H11]
- **WEB.N108** MIRROR · `js/mock-server.js:459-461` — "Mirrors src/asy_wifi_service.py's _mask_pw()
  callback overlay: PW is a real credential, never returned in plaintext over GET" — the mock masks only
  PW; the real `_mask_pw()` (src/asy_wifi_service.py:197-201) masks PW and HotspotPW (HotspotPW is not
  in any definitions/mockdata, so no visible gap today) · related: NET.S16 · [H11]
- **WEB.N109** DRIFT · `js/mock-server.js:480-482` — "jitterInPlace mutates numeric leaves of a flat
  object" — stale: jitterInPlace now recurses into nested objects (:289-291) · covered-by: WEB.S12 ·
  [H11]

## js/nav.js

- **WEB.N110** INVAR · `js/nav.js:2-3` — "Builds no DOM itself - see SPECIFICATION.md Part H.3 for the
  full mechanics/visual split this file follows." — H.3 layering (controllers build no DOM) upheld by
  convention only; no lint rule · related: WEB.T11 · [H11]
- **WEB.N111** ASSUME · `js/nav.js:36` — "defensive only: buildNavDrawer() always sets this on every
  link it builds" — unreachable branch by stated assumption (low) · [H11]
- **WEB.N112** LIMIT · `js/nav.js:24-31` — "appShellEl.classList.remove(\"nav-open\");
  hamburgerEl.setAttribute(\"aria-expanded\", \"false\");" — drawer state is only a class +
  aria-expanded: no `inert`, no focus move/trap, static aria-label · covered-by: WEB.S16 · [H11]
- **WEB.N113** LIMIT · `js/nav.js:52-56` — "document.addEventListener(\"keydown\", ..." — a
  document-level Escape listener is added per initNav() call and never removed; safe only because
  initNav runs once per page load (low) · [H11]

## js/poll-manager.js

- **WEB.N114** DRIFT · `js/poll-manager.js:1-3 vs :11-13` — "every fetch in the app goes through the one
  shared instance below rather than calling fetch() directly" — the header says every fetch goes through
  the single-flight queue, while :12-13 and js/app.js:46 / js/definitions.js:240 use fetchWithTimeout()
  outside it (low) · related: WEB.T03 · [H11]
- **WEB.N115** MIRROR · `js/poll-manager.js:7-8` — "export const DEFAULT_TIMEOUT_MS = 15000;" — client
  timeout mirrors the server's `outer_cap_s` 15.0 per H.4; the two start at different moments so the
  client nearly always aborts first · covered-by: WEB.S06 · [H11]
- **WEB.N116** ASSUME · `js/poll-manager.js:10-13` — "so a hung connection is freed and rejected rather
  than waited on ... need the same never-hang guarantee" — the never-hang guarantee covers headers only:
  the timer is cleared in `finally` once fetch resolves, and `response.text()` (:63) is unbounded ·
  covered-by: WEB.S05 · [H11]
- **WEB.N117** PLATFORM · `js/poll-manager.js:38,41` — "#queue = Promise.resolve(); ... #activeCount =
  0;" — class private fields are a browser-floor dependency · covered-by: WEB.T09 · [H11]
- **WEB.N118** LIMIT · `js/poll-manager.js:43-46` — "get isBusy()" — used only by tests · covered-by:
  WEB.S18 · [H11]
- **WEB.N119** ASSUME · `js/poll-manager.js:65-66` — "The connection dropped mid-stream, after headers
  but before the full body arrived" — any body-read rejection is presumed to be a dropped connection
  (low) · [H11]
- **WEB.N120** ASSUME · `js/poll-manager.js:73-74` — "a truncated/corrupted transmission, or a non-JSON
  response from something other than this app's own backend" — JSON parse failure attributed to
  transmission or a foreign responder (e.g. captive-portal/proxy page) (low) · [H11]
- **WEB.N121** LIMIT · `js/poll-manager.js:71` — "body = text.length > 0 ? JSON.parse(text) : null;" —
  an empty 2xx body resolves as `{ok: true, body: null}` rather than an error; callers must check for
  null themselves (low) · [H11]
- **WEB.N122** LIMIT · `js/poll-manager.js:83-88` — "const scheduled = this.#queue.then(run, run);" —
  one global queue for every section: a stalled request blocks all sections; nothing aborts queued
  requests on a section switch · covered-by: WEB.S07 · [H11]
- **WEB.N123** ASSUME · `js/poll-manager.js:109-111` — "Defensive only: ... kept in case a future caller
  invokes tick() directly." — unreachable guard by stated assumption (low) · [H11]
- **WEB.N124** LIMIT · `js/poll-manager.js:116-117` — "console.error(\"Poll failed:\", error);" — the
  loop's only diagnostic is dead because render.js's fetchOnce() never rejects · covered-by: WEB.S11 ·
  [H11]
- **WEB.N125** LIMIT · `js/poll-manager.js:102-131` — "export function startPolling(pollOnce,
  intervalMs)" — no visibility (hidden-tab) pause and no backoff on repeated failure · covered-by:
  WEB.S07 · [H11]

## js/render.js

- **WEB.N126** INVAR · `js/render.js:1-3` — "Section controller - the mechanics half of the
  visual/mechanics split. Builds no DOM itself" — H.3 layering by convention only · related: WEB.T11 ·
  [H11]
- **WEB.N127** DRIFT · `js/render.js:27-29` — "a server-side Number(null) === 0 would turn garbage into
  a plausible in-range value ... so the backend's own Number() rejects it" — the comment reasons with
  JavaScript `Number()` semantics for a Python backend that does strict `type()` checks (low) · related:
  WEB.S03 · [H11] ⟨quote not matched at the anchor⟩
- **WEB.N128** LIMIT · `js/render.js:26-30` — "const num = Number(rawInputValue); ... return
  Number.isFinite(num) ? num : rawInputValue;" — whitespace-only input becomes 0; hex and exponent
  strings pass as numbers; a decimal comma goes as a string · covered-by: WEB.S03 · [H11]
- **WEB.N129** PLATFORM · `js/render.js:33-35` — "A <select>'s own .value is always a string (DOM
  behavior), even when the option's real value is numeric" — enum values are recovered via
  `String(option.value) === rawInputValue`; two options whose values stringify equally (e.g. 1 and "1")
  would be ambiguous (low) · [H11]
- **WEB.N130** MIRROR · `js/render.js:42-45` — "the server's own shaped-error `descr` when present
  (SPECIFICATION.md Part A.5's `_ERROR_SHAPES`/`_shaped_error_handler` - every 400/404/405/413/500
  carries one)" — GET error text relies on the server's shaped-error envelope for exactly those statuses
  · related: WEB.T04 · [H11]
- **WEB.N131** DRIFT · `js/render.js:61-64` — "Every field kind is sparse-omitted when it matches its
  resolveFieldValue() baseline and carries no `dispatch` flag." — number/string fields are omitted only
  when the input is empty (:115-117), never compared to the baseline; a re-typed identical value is sent
  (low) · related: WEB.T01 · [H11]
- **WEB.N132** ASSUME · `js/render.js:98-100` — "every real subField today is numeric (e.g.
  lightCmdLED's r/g/b/t), so this doesn't yet need readInputValue()'s own per-kind dispatch" — composite
  sub-fields are assumed numeric; a future string/enum sub-field would be mistyped. Deferred ("doesn't
  yet need") · [H11] ⟨quote not matched at the anchor⟩
- **WEB.N133** LIMIT · `js/render.js:127-130,159` — "const STATUS_SEVERITY = { Invalid: 0, Failed: 1,
  Valid: 2, Unchanged: 3 };" — any status string outside these four ranks as 4 (least severe), so an
  unexpected server status can never make a card worse than Unchanged (low) · [H11]
- **WEB.N134** LIMIT · `js/render.js:132-135` — "A submitted-but-unanswered field is treated as Failed
  ... a known real server-side gap where a settings group's post-write hook raising drops that group's
  fields" — reconciliation guards a server gap the plan says is fixed; the H.6 citation may be stale ·
  related: WEB.S12 · [H11]
- **WEB.N135** ASSUME · `js/render.js:160-161` — "an empty `result` map on a successful envelope still
  means the action completed, not that \"nothing changed\" - default to success." — an empty result map
  is read as success · related: WEB.S02 · [H11]
- **WEB.N136** LIMIT · `js/render.js:164-169` — "for (const [key, status] of Object.entries(results)) {"
  — per-field colours are set only for fields in the latest result; others keep a previous Apply's
  colour · covered-by: WEB.S04 · [H11]
- **WEB.N137** LIMIT · `js/render.js:197-200` — "if (putPath === undefined) { return; }" — an Apply on a
  submit group whose section has no `rest.put` silently does nothing; validateDefinitions() doesn't
  require it · covered-by: WEB.S10 · [H11]
- **WEB.N138** LIMIT · `js/render.js:202-209` — "Every field kind is sparse-omitted when untouched; only
  a `dispatch` field always resubmits." — because dispatch toggles in Off are always sent, a card
  containing one can never reach "Nothing to submit" · covered-by: WEB.S02 · [H11]
- **WEB.N139** MIRROR · `js/render.js:211-213` — "/sensors is the one endpoint whose PUT body nests
  fields under the sensor's own group key" — body shape and the hard-coded section key "sensors" must
  mirror the server's /sensors PUT contract and the definitions' section keys · related: WEB.T04 · [H11]
- **WEB.N140** MIRROR · `js/render.js:216-218` — "the backend accepts a JSON int for a float-typed field
  and coerces it (coerce_numeric(), Part A.8)" — the client relies on server-side int->float coercion ·
  related: WEB.T02 · [H11] ⟨quote not matched at the anchor⟩
- **WEB.N141** MIRROR · `js/render.js:225-229` — "a malformed body is a clean 200 with res:\"ERR\", a
  route-level failure a non-2xx carrying the same envelope" — failure detection mirrors src/ envelope
  conventions · related: WEB.T04 · [H11]
- **WEB.N142** MIRROR · `js/render.js:235-244` — "/status's PUT returns no per-field result for any
  submit group" — every submitted /status field is shown Valid on any OK envelope, including
  ResetErrors=false (dispatch Off), which the server treats as a no-op · related: WEB.S02 · [H11]
- **WEB.N143** LIMIT · `js/render.js:247-254` — "a field the server really stored (Valid or Unchanged)
  becomes the new baseline immediately." — baseline moves to the submitted value, including dispatch
  toggles, so the next Apply resends them · covered-by: WEB.S01 · [H11] ⟨quote not matched at the
  anchor⟩
- **WEB.N144** SUPPRESS · `js/render.js:260-263` — "// eslint-disable-next-line require-atomic-updates"
  — shipped-code suppression; justified as "`card` is a const DOM reference, never reassigned - no real
  race" plus the button's `disabled` re-entry guard · [H11]
- **WEB.N145** SETTLED · `js/render.js:264-266` — "legacy only console.error'd here, and this is a
  deliberate change." — a deliberate divergence from legacy: a failed Apply marks every submitted field
  failed · [H11]
- **WEB.N146** LIMIT · `js/render.js:296,311,320,325,329` —
  "grid.querySelector(`[data-group-key=\"${group.key}\"]`)" — selectors interpolate definition keys
  without `CSS.escape` · covered-by: WEB.S17 · [H11]
- **WEB.N147** LIMIT · `js/render.js:299-312` — "A live poll rebuilds this card from scratch every tick"
  — the errcount card is rebuilt each poll; expand state is restored but keyboard focus is lost ·
  covered-by: WEB.S08 · [H11]
- **WEB.N148** LIMIT · `js/render.js:321-335` — "Writable groups only refresh their read-only
  captions/spans in place" — in-place caption refresh reads `groupValues[field.key]` directly, bypassing
  resolveFieldValue(); baselines stay frozen at first render · covered-by: WEB.S10 · [H11]
- **WEB.N149** LIMIT · `js/render.js:345-349` — "Never rejects - the one place that catches every fetch
  failure for this section." — swallowing all errors here makes startPolling's console.error dead ·
  covered-by: WEB.S11 · [H11]
- **WEB.N150** MIRROR · `js/render.js:357-368` — "PauseTime is live data under GET /status's
  \"notification\" sub-key, not in GET /notification's settings-only response (Part A.8)" — the
  notification section issues a second /status GET per refresh and relies on that server layout and the
  hard-coded section key "notification" · related: WEB.T04 · [H11] ⟨quote not matched at the anchor⟩
- **WEB.N151** LIMIT · `js/render.js:377-383` — "if (section.pollGroup === \"live\") {" — "settings" and
  "none" poll groups behave identically (fetch once) · covered-by: WEB.S18 · [H11]
- **WEB.N152** ASSUME · `js/render.js:386-389` — "Errcount-only groups never reach this helper." —
  stated precondition of groupValuesFrom() (low) · [H11]
- **WEB.N153** MIRROR · `js/render.js:399-411` — "flatten one level so field keys can address it
  directly (e.g. \"SGP40_BackupTS\")" — the `${sensorKey}_${fieldKey}` convention and the hard-coded
  status group key "sensors" must match definitions (wozi `SGP40_*`, dev `UARTLINK_*`) and
  buildgen/definitions.py; a sensor name containing `_` makes keys ambiguous (low) · related: WEB.T05 ·
  [H11] ⟨quote not matched at the anchor⟩

## js/templates.js

- **WEB.N154** INVAR · `js/templates.js:1-3` — "Every DOM element this app ever creates is built here,
  and only here" — H.3 layering by convention only · related: WEB.T11 · [H11]
- **WEB.N155** INVAR · `js/templates.js:6-8` — "never re-exported: the bundler keeps every `export` as
  written, so a second one would collide once concatenated (SPECIFICATION.md Part H.7's splitting rule)"
  — no module may re-export another's symbol because scripts/build_website.sh concatenates files;
  convention only · related: WEB.S14 · [H11]
- **WEB.N156** LIMIT · `js/templates.js:27-28` — "`Length: ${field.minLength ?? 0} to ${field.maxLength ?? \"∞\"} characters`"
  — the hint says "characters" while server bounds (e.g. WiFi SSID/PW) are UTF-8 bytes (low) · related:
  WEB.S12 · [H11]
- **WEB.N157** INVAR · `js/templates.js:54-56` — "data-field-key below (which must keep pointing at the
  specific control - collectGroupBody()/paint() rely on that exact element)" — the data-* hook contract
  between templates.js and render.js · related: WEB.T11 · [H11]
- **WEB.N158** LIMIT · `js/templates.js:61,85,105,161` — "label.htmlFor = `field-${field.key}`;" — ids
  not namespaced by group (dev's SampleInterv/FiltCoeff duplicated); labels for readonly/composite
  fields point at no element · covered-by: WEB.S15 · [H11]
- **WEB.N159** SETTLED · `js/templates.js:91` — "Purely cosmetic self-flip - no network call, safe to
  wire directly here." — the one behaviour wired in the presentation layer, a stated H.3 exception (low)
  · related: WEB.T11 · [H11]
- **WEB.N160** ASSUME · `js/templates.js:109-114` — "No value to preselect (SystemCmd is write-only,
  never returned by GET /system)." — the "Select…" placeholder prevents accidentally submitting the
  first command; relies on SystemCmd never appearing in GET · [H11]
- **WEB.N161** LIMIT · `js/templates.js:158-164` — "input.type = field.mask === true ? \"password\" :
  \"text\";" — number fields use a text input; masked inputs lack `autocomplete` · covered-by: WEB.S17 ·
  [H11]
- **WEB.N162** LIMIT · `js/templates.js:215-224, 283` — "function worstErrcountType(entry)" — rollup
  uses history types, while row colour uses `counter > 0`; the two can disagree · covered-by: WEB.S08 ·
  [H11]
- **WEB.N163** LIMIT · `js/templates.js:245-246` — "entry: errcount[moduleInfo.key] ?? { counter: 0 },"
  — a module missing from /status errcount (unwired, or a degraded source) renders as a healthy zero
  row, indistinguishable from "no errors"; SPECIFICATION.md:4502-4504 (H.6) documents this "permanent,
  reassuring `0`" and makes the per-instance key list the only guard · related: WEB.S09 · [H11]
- **WEB.N164** SETTLED · `js/templates.js:292-293` — "Always rendered, never independently hidden ...
  (project owner, session 2 follow-up)." — owner decision on history visibility · [H11]
- **WEB.N165** ASSUME · `js/templates.js:303-304` — "No pagination or truncation - realistic history
  depth is well under 20 entries (project owner, session 2)" — unbounded render justified by an
  owner-stated history depth · [H11]
- **WEB.N166** SETTLED · `js/templates.js:338-341` — "See SPECIFICATION.md Part H.3's \"One deliberate
  exception\" note for why this returns `{grid, errorBanner}` directly." — a stated exception to the H.3
  contract · related: WEB.S18 · [H11]
- **WEB.N167** PLATFORM · `js/templates.js:347,380` — "mainEl.replaceChildren();" — `replaceChildren` is
  a browser-floor dependency · covered-by: WEB.T09 · [H11]

## html/index.html

- **WEB.N168** MIRROR · `html/index.html:29-30` — "import { startApp } from \"../js/app.js\";" — source
  page loads the prototype entry; the build must rewrite this import to the staged production `app.js`
  (js/main.js) · related: WEB.T06 · [H11]
- **WEB.N169** DRIFT · `html/index.html:40-43` — "scripts/build_website.sh's own \"Inlining\" comment
  inlines this element straight into index.html" — 4-line `//` block (over the 3-line cap) citing a
  comment that no longer exists · covered-by: WEB.S19 · [H11]
- **WEB.N170** MIRROR · `html/index.html:44` — "document.getElementById(\"inlined-definitions\")" — the
  id must match scripts/build_website.sh:64's `id="inlined-definitions"` · related: WEB.T06 · [H11]
- **WEB.N171** LIMIT · `html/index.html:7` — "<link rel=\"icon\" href=\"data:,\">" — empty data-URI
  favicon hack to suppress a /favicon.ico request; interacts with any future CSP `img-src` (low) ·
  related: WEB.T13 · [H11]
- **WEB.N172** LIMIT · `html/index.html:3-9` — "<head> ... </head>" — no CSP meta tag and no other
  security headers at page level; the inline `<script type="module">` bootstrap (:29-46) would need a
  hash/nonce or `unsafe-inline` under any CSP · related: WEB.T13 · [H11]
- **WEB.N173** LIMIT · `html/index.html:13` — "aria-label=\"Open navigation\" aria-expanded=\"false\"" —
  static aria-label regardless of state · covered-by: WEB.S16 · [H11]
- **WEB.N174** LIMIT · `html/index.html:21` — "<div class=\"nav-backdrop\" id=\"nav-backdrop\"></div>" —
  clickable backdrop with no role/keyboard affordance (Escape is handled at document level) (low) ·
  related: WEB.S16 · [H11]

## html/style.css

- **WEB.N175** SETTLED · `html/style.css:3` — "dark only redefines tokens under prefers-color-scheme, no
  manual toggle." — no manual theme toggle, by design; no `color-scheme` declared, so native controls
  stay light in dark mode · covered-by: WEB.S16 · [H11]
- **WEB.N176** LIMIT · `html/style.css:16,20,22,11` — "--color-success: #1f9d55; ... --color-danger:
  #d64545; ... --color-warn: #9457c7;" — light-mode status colours/borders below 4.5:1 contrast ·
  covered-by: WEB.S16 · [H11]
- **WEB.N177** LIMIT · `html/style.css:122,141` — "transition: opacity 0.18s ease;" — transitions with
  no `prefers-reduced-motion` override · related: WEB.T07 · [H11]
- **WEB.N178** ASSUME · `html/style.css:234-237` — ".field:first-of-type {" — relies on the card heading
  being an `h3` (not a `div`) so the first `.field` div matches `:first-of-type` (low) · [H11]
- **WEB.N179** LIMIT · `html/style.css:261-263` — ".field input[type=\"text\"], .field
  input[type=\"number\"], .field select {" — `input[type=password]` (masked PW) is unstyled ·
  covered-by: WEB.S16 · [H11]
- **WEB.N180** ASSUME · `html/style.css:273-277` — "grid-template-columns: repeat(4, 1fr);" — the
  composite grid assumes four sub-fields (lightCmdLED r/g/b/t) (low) · [H11]
- **WEB.N181** SETTLED · `html/style.css:314-316` — "a left accent stripe rather than legacy's full
  background recolor ... Two levels, as legacy had" — deliberate visual divergence from legacy, keeping
  legacy's two-level granularity (low) · [H11]
- **WEB.N182** ASSUME · `html/style.css:351-353` — "a device can have 15+ registered modules" — undated
  module-count figure (wozi has 17, dev 21 errcount modules) (low) · [H11]
- **WEB.N183** ASSUME · `html/style.css:411-413` — "a module can carry 10+ entries" — history-depth
  figure; compare templates.js:303-304's "well under 20 entries" (low) · [H11]
- **WEB.N184** LIMIT · `html/style.css:427-428` — "\"N\"/\"E\"/\"W\" (no error/error/warning) never
  render as text, they only pick this pill's color" — colour-only information by design · covered-by:
  WEB.S16 · [H11]
- **WEB.N185** SUPPRESS · `html/style.css:472-474` — ".hidden { display: none !important; }" — the
  stylesheet's only `!important`: a utility override that beats every other display rule (low) · [H11]
- **WEB.N186** PLATFORM · `html/style.css:476` — "@media (width >= 640px) {" — media-query range syntax
  is a browser-floor dependency (stylelint-config-standard enforces this notation) · covered-by: WEB.T09
  · [H11]
- **WEB.N187** PLATFORM · `html/style.css:136` — "width: min(280px, 80vw);" — CSS `min()` and `inset`
  (:117) are browser-floor dependencies (low) · related: WEB.T09 · [H11]

## html/definitions/wozi.json

- **WEB.N188** DRIFT · `html/definitions/wozi.json:1 (whole file)` — "wozi/dev keep their hand-written
  html/definitions/<device>.json" (scripts/build_website.sh:26) — provenance is stated three ways:
  hand-written (build_website.sh:26-27, SPECIFICATION.md:4405-4406), "generated at build time ... never
  hand-maintained" (SPECIFICATION.md:5785-5786), "generated *and committed*" (BACKLOG.md:439-440) ·
  covered-by: WEB.S13 · [H11] ⟨quote not matched at the anchor⟩
- **WEB.N189** TODO · `html/definitions/wozi.json:1 (whole file)` — "retiring them is deferred work
  (SPECIFICATION.md Part L.4)" (scripts/build_website.sh:27) — retiring the hand-written wozi/dev files
  in favour of generated ones is deferred; tests_js reads them as fixtures · related: WEB.S13 · [H11]
  ⟨quote not matched at the anchor⟩
- **WEB.N190** MIRROR · `html/definitions/wozi.json:60-130,147-168,184-186,311-346` — "\"min\": 2,
  \"max\": 1800" etc. — every hand-written min/max/float/maxLength must match src/ FieldSchema tuples
  (e.g. NTP_Host maxLength 1024 — BACKLOG.md:439-441; SPECIFICATION.md:2331 "Also update
  html/definitions/<device>.json") · related: WEB.S13 · [H11] ⟨quote not matched at the anchor⟩
- **WEB.N191** LIMIT · `html/definitions/wozi.json:72-75` — "\"key\": \"ContMeas\" ... \"defaultValue\":
  true" — ContMeas is dispatch-only server-side (mock SENSOR_QUIRK_FIELDS) but carries no `dispatch`
  flag, and GET never reports it, so after a reload the toggle always shows On even when measurement was
  stopped; H.6 (SPECIFICATION.md:4508-4510) lists ContMeas as dispatch-only while H.4 (:4361) does not —
  see the cross-list item under tests_js/_put_field_cases.js (low) · related: WEB.S01 · [H11]
- **WEB.N192** MIRROR · `html/definitions/wozi.json:197` — "{ \"value\": \"mempause\", \"label\":
  \"Pause backups for 5 minutes\" }" — the label hard-codes mempause's fixed 300 s, which lives in src/
  system_cmd() (src/asy_webserver_service.py:95-97) · [H11]
- **WEB.N193** LIMIT · `html/definitions/wozi.json:290-293` — "\"description\": \"... Absent/No is a
  no-op.\", \"dispatch\": true" — with dispatch, "No" is always sent and render.js marks it Valid, so an
  Apply with the toggle at No reports success while doing nothing · related: WEB.S02 · [H11]
- **WEB.N194** MIRROR · `html/definitions/wozi.json:264-282` — "\"modules\": [ { \"key\": \"WIFI\" ... {
  \"key\": \"WEBSERVER\" ..." — hand-kept errcount module list must match the loggers the device
  registers (buildgen/definitions.py:97-115,365-387 generates it; SCD30 has no CFGMGR_ by design) ·
  related: WEB.S13 · [H11]
- **WEB.N195** MIRROR · `html/definitions/wozi.json:6,209` — "\"defaultPollIntervalMs\": 3000 ...
  \"pollIntervalMs\": 3000" — poll cadence vs the server's measured throughput (~2.2 requests/s) ·
  related: WEB.S07 · [H11]

## html/definitions/dev.json

- **WEB.N196** DRIFT · `html/definitions/dev.json:1 (whole file)` — 2-space indent and `—` escapes
  (Python `json.dump` style) — dev.json is formatted like generator output while wozi.json is
  hand-formatted; consistent with BACKLOG.md:439-440's "generated *and committed*" and inconsistent with
  "hand-written" (build_website.sh:26) (low) · covered-by: WEB.S13 · [H11] ⟨quote not matched at the
  anchor⟩
- **WEB.N197** MIRROR · `html/definitions/dev.json:964-970` — "UARTLINK_Transfers ... Bench-only - a
  deployed unit has no such link." — status/sensors key `UARTLINK` must match the server's /status
  sensors sub-key via render.js's flatten convention · related: WEB.T05 · [H11]
- **WEB.N198** LIMIT · `html/definitions/dev.json (sensors section)` — "SampleInterv" and "FiltCoeff" in
  both BMP3XX and ISL29125 groups — duplicate DOM ids `field-SampleInterv`/`field-FiltCoeff` ·
  covered-by: WEB.S15 · [H11]
- **WEB.N199** LIMIT · `html/definitions/dev.json:305-306` — "Setting this to Off stops continuous
  measurement ... \"defaultValue\": true" — same ContMeas no-`dispatch` / always-On-after-reload issue
  as wozi (low) · related: WEB.S01 · [H11]

## package.json

- **WEB.N200** LIMIT · `package.json:10-11` — "\"build:site\": \"scripts/build_website.sh wozi && uv run
  scripts/_generate_sensortask_modules.py\"" — every `pretest*` hook builds the wozi site only and needs
  `uv` (Python) on PATH; the other five devices' sites are never built by the web tier · covered-by:
  WEB.T12 · [H11]

## eslint.config.js

- **WEB.N201** PLATFORM · `eslint.config.js:126,138,152,165,178,194` — "ecmaVersion: \"latest\"" — lint
  accepts any syntax level, so nothing mechanically bounds shipped js/ to a browser floor · related:
  WEB.T09 · [H11]
- **WEB.N202** DRIFT · `eslint.config.js:108-111` — "poll-manager's \"Poll failed:\" and the
  live-backend test's skip warning are real signal" — the cited `console.error("Poll failed:")` is
  unreachable · covered-by: WEB.S11 · [H11]
- **WEB.N203** MIRROR · `eslint.config.js:189-190` — "build_website.sh relies on its literal
  \"../js/app.js\" import (H.8)" — the inline bootstrap's import string in html/index.html:30 is a
  contract with scripts/build_website.sh's rewrite · related: WEB.T06 · [H11] ⟨quote not matched at the
  anchor⟩

## tsconfig.json

- **WEB.N204** PLATFORM · `tsconfig.json:3-6` — "\"target\": \"ES2022\", ... \"lib\": [\"ES2022\",
  \"DOM\"]," — type-checking assumes an ES2022 + current-DOM runtime (Error `cause`, private fields,
  `structuredClone`, `replaceChildren`), the de facto browser floor · related: WEB.T09 · [H11]
- **WEB.N205** LIMIT · `tsconfig.json:28` — "\"include\": [\"js/**/*.js\", \"tests_js/**/*.js\",
  \"tests_js/**/*.d.ts\"]" — html/index.html's inline module bootstrap is never type-checked (it passes
  `HTMLElement | null` values to startApp) (low) · related: WEB.T06 · [H11]

## vitest.config.js

- **WEB.N206** LIMIT · `vitest.config.js:42-46` — "instances: [{ browser: \"chromium\" }]," — the unit
  and live tiers run Chromium only; other engines only via the separate cross-browser smoke · related:
  WEB.T09 · [H11]

## .htmlvalidate.json

- **WEB.N207** SUPPRESS · `.htmlvalidate.json:7-9` — "\"require-sri\": [\"error\", { \"target\":
  \"crossorigin\" }]" — SRI required only for cross-origin resources (same-origin script/style exempt) —
  a narrowed rule (low) · related: WEB.T08 · [H11]
- **WEB.N208** LIMIT · `.htmlvalidate.json:1-10 with package.json:19` — "\"lint:html\": \"html-validate
  \\\"html/**/*.html\\\"\"" — only the source page is validated, never the built index.html with inlined
  CSS/JSON/bundle (low) · related: WEB.T06 · [H11]

## tests_js/_live_twin_command.js

- **WEB.N209** LIMIT · `tests_js/_live_twin_command.js:56-62` — "\"--module\", \"sensortask_wozi\", ...
  \"--device\", \"wozi\"," — live tier boots wozi only · covered-by: WEB.T12 · [H11]

## tests_js/_put_field_cases.js

- **WEB.N210** MIRROR · `tests_js/_put_field_cases.js:11-14` — "export const DISPATCH_ONLY_KEYS = new
  Set([\"SystemCmd\", \"PauseTime\", \"lightCmdLED\", \"ResetErrors\"]);" — yet another hand-kept
  "special field" list; the lists disagree: H.4 (SPECIFICATION.md:4361) =
  SystemCmd/PauseTime/lightCmdLED/ResetErrors + `dispatch=true` tags (SGPResetVOC, ISLCalibrate),
  "derive the set from the tags, never from this list alone"; H.6 (:4508-4510) adds ContMeas, omits
  ISLCalibrate; definitions `dispatch: true` = SystemCmd, SGPResetVOC, ISLCalibrate, ResetErrors;
  js/mock-server.js:22 SENSOR_QUIRK_FIELDS = ForceCalRef/ContMeas/SGPResetVOC/ISLCalibrate (+ :244's own
  list); tests_js/mock-server-put-matrix.test.js:26 adds PW; tests_js/live-backend-put-matrix.test.js:21
  = ForceCalRef/ContMeas/SGPResetVOC · related: WEB.S01 · [H11]

## tests_js/live-backend.test.js

- **WEB.N211** LIMIT · `tests_js/live-backend.test.js:19, 50` —
  "expect(result.deviceName).toContain(\"wozi\");" — wozi only · covered-by: WEB.T12 · [H11]

## tests_js/live-backend-put-matrix.test.js

- **WEB.N212** SETTLED · `tests_js/live-backend-put-matrix.test.js:131-132` — "An empty-string current
  value has no \"resubmit\" gesture" — consequence of H.4's accepted gap "An empty string can't be set
  via this UI for any field" (SPECIFICATION.md:4365) · [H11]

## tests_js/mock-server.test.js

- **WEB.N213** MIRROR · `tests_js/mock-server.test.js:247-249` — "Mirrors
  _dispatch_notification_pause(): PauseTime is a runtime action, checked 0-3600 ... follows
  coerce_numeric()" — mock contract pinned to src/asy_webserver_service.py:530 · related: WEB.T04 ·
  [H11]
- **WEB.N214** LIMIT · `tests_js/mock-server.test.js:342-343` — "there's no real I2C bus here to ever
  produce the real driver's \"Failed\"" — ContMeas "Failed" path untested in the mock tier · related:
  WEB.T15 · [H11] ⟨quote not matched at the anchor⟩
- **WEB.N215** MIRROR · `tests_js/mock-server.test.js:349-350, 360-361, 367-368` — "ContMeas has no
  schema entry on the real backend" / "A command-only, repeatable trigger (SPECIFICATION.md C.5.2.1)" /
  "SGPResetVOC is a special-alone schema field, deliberately excluded from get_dict_cfg()" — mock GET
  omissions pinned to src/ schema facts · related: WEB.T04 · [H11]
- **WEB.N216** LIMIT · `tests_js/mock-server.test.js:545-546` — "the real backend's own gap: overall
  envelope still reports OK" — asserts a gap H.6 (SPECIFICATION.md:4513-4515) says is closed ·
  covered-by: WEB.S12 · [H11]

## tests_js/render.test.js

- **WEB.N217** MIRROR · `tests_js/render.test.js:418-420` — "_put_status() never builds a `result` dict,
  so /status's PUT structurally cannot report a per-field outcome" — pinned to
  src/asy_webserver_service.py:380 `_put_status` · [H11]
- **WEB.N218** DRIFT · `tests_js/render.test.js:679-681` — "a server-side Number(null) === 0 made it
  look like a deliberate in-range value." — same JS-semantics-for-a-Python-server reasoning as
  js/render.js:27-29 (low) · related: WEB.S03 · [H11] ⟨quote not matched at the anchor⟩
- **WEB.N219** LIMIT · `tests_js/render.test.js:1016-1018` — "A real server-side gap (Part H.6): a
  settings group's post-write hook raising drops that group's fields" — contradicts H.6's current text ·
  covered-by: WEB.S12 · [H11]

## tests_js/templates.test.js

- **WEB.N220** DRIFT · `tests_js/templates.test.js:41-42` — "Real shape (src/sensortask_wozi.py's
  _gmtimestruct_to_dict())" — cites a removed file · covered-by: WEB.S21 · [H11]
- **WEB.N221** ASSUME · `tests_js/templates.test.js:48-49` — "no driver in src/ rounds any output" —
  same cross-tree claim as js/field-format.js:33-35 · [H11]
- **WEB.N222** MIRROR · `tests_js/templates.test.js:399-401` — "Real backend shape (src/print_log.py's
  get_log()): no per-entry timestamp exists ... (project owner, session 2 follow-up)" — pinned to
  src/print_log.py:180; owner decision that type is never shown as text · [H11]

## tests_js/definitions-mockdata-coverage.test.js

- **WEB.N223** LIMIT · `tests_js/definitions-mockdata-coverage.test.js:6-7` — "import wozi ... import
  dev" — wozi/dev only; generated devices have no mockdata · covered-by: WEB.T12 · [H11]

## tests_js/main.test.js

- **WEB.N224** ASSUME · `tests_js/main.test.js:144-145` — "scripts/build_website.sh always writes valid
  JSON" — stated build guarantee (low) · [H11]
- **WEB.N225** LIMIT · `tests_js/main.test.js:11-12 (and tests_js/app.test.js:11-12)` — "startApp() has
  no stop handle exposed to callers, so a \"live\" section here would keep polling" — startApp() cannot
  be stopped; entry-point tests avoid live sections (low) · [H11]

## tests_js/app.test.js

- **WEB.N226** LIMIT · `tests_js/app.test.js:11-12` — "startApp() has no stop handle exposed to callers"
  — see main.test.js item (low) · [H11]

## tests_js/poll-manager.test.js

- **WEB.N227** ASSUME · `tests_js/poll-manager.test.js:108-110` — "the device has very few available
  sockets, SPECIFICATION.md Part H.4" — rationale for the hung-connection timeout (low) · [H11]

## SPECIFICATION.md Part A.8 (REST API endpoint reference, 571-625)

- **WEB.N228** MIRROR · `SPECIFICATION.md:615` — "`js/mock-server.js` mirrors the equivalent policy." —
  src coercion ↔ JS mock mirror. · covered-by: WEB.T04 · [H12]

## SPECIFICATION.md Part C.7.4 (Radio string bounds are bytes, 2002-2014)

- **WEB.N229** MIRROR · `SPECIFICATION.md:2004, 2010-2014` — "The schema bounds every `str` field in
  characters (and the web UI mirrors that) ... `asy_wifi_service.py` now bounds ... in bytes" — Device
  checks bytes, web UI/mock check characters. · related: WEB.S12 · [H12]

## SPECIFICATION.md Part G.0-G.1 — Shared primitive reuse rule

- **WEB.N230** MIRROR · `SPECIFICATION.md:4153-4155` — "A new feature with both a `src/` and `js/` side
  must encode the *identical* policy in the same change" — src↔js policy mirror, one change. ·
  covered-by: WEB.T04 · [H13]

## SPECIFICATION.md Part G.2 — Known reusable primitives

- **WEB.N231** MIRROR · `SPECIFICATION.md:4229-4231` — "`js/mock-server.js` must match the real `src/`
  endpoint field for field, bound for bound; a `src/`-side policy change and its `js/` mirror are one
  change" — src↔js mock-server mirror. · covered-by: WEB.T04 · [H13]

## SPECIFICATION.md Part H.1 — Website purpose and constraints

- **WEB.N232** INVAR · `SPECIFICATION.md:4265-4266` — "Every REST endpoint's functionality must be
  reachable somewhere in the GUI." — Standing product constraint; contradicted for `/system`'s `build`
  by L.7 (plan WEB.S20). · covered-by: WEB.S20 · [H13]
- **WEB.N233** ASSUME · `SPECIFICATION.md:4266-4271` — "Standing constraints, all met: ...
  `render.js`/`nav.js` have zero device-specific branching ... stable on major browsers" — Blanket "all
  met" claim over several constraints (full REST coverage, no deps, browsers). · related: WEB.T09,
  WEB.T12 · [H13]

## SPECIFICATION.md Part H.2 — Folder structure and module map

- **WEB.N234** INVAR · `SPECIFICATION.md:4304-4306` — "`js/mock-server.js` is deliberately never staged
  at all — its `fetch` patching has no business near production" — Build rule; cross-checked by
  `tests_scripts/test_build_website_sh.py`. · related: WEB.T06 · [H13]
- **WEB.N235** INVAR · `SPECIFICATION.md:4310-4312` — "the bundler strips local `import` lines but never
  `export` lines ... a split-out module (`field-format.js`) must never be *re-exported*" — Bundling
  constraint upheld by convention. · related: WEB.T06 · [H13]
- **WEB.N236** DRIFT · `SPECIFICATION.md:4312-4315` — "Concatenation order is fixed so every file
  follows the local files it imports from ... `scripts/build_website.sh` re-checks that mechanically on
  every build" — Plan WEB.S14: no such check exists and the order is violated. · covered-by: WEB.S14 ·
  [H13]
- **WEB.N237** LIMIT · `SPECIFICATION.md:4315-4318` — "`tsc`'s JSDoc checking doesn't cover inline
  scripts (accepted — it's a thin bootstrap)" — Accepted type-check gap for `index.html`'s inline
  module. · [H13]

## SPECIFICATION.md Part H.3 — Visual vs mechanics layering

- **WEB.N238** INVAR · `SPECIFICATION.md:4323-4324` — "A purely visual/layout redesign must never
  require editing data-fetching, validation, submission, or poll-coordination code." — Standing layering
  requirement; review-only. · covered-by: WEB.T11 · [H13]
- **WEB.N239** INVAR · `SPECIFICATION.md:4334-4340` — "controllers reach into a template only via
  `data-*` attributes/CSS classes ... Controllers only ever set the semantic `data-apply-status` value"
  — The `data-*` contract list is the redesign-stable interface; not mechanically checked. · covered-by:
  WEB.T11 · [H13]
- **WEB.N240** LIMIT · `SPECIFICATION.md:4340-4342` — "**In-place refresh only ever touches a
  number/string field's caption** — a toggle/enum field's round-trip needs a genuine full remount" —
  Toggle/enum state is not refreshed by polling. · related: WEB.S01, WEB.S10 · [H13]

## SPECIFICATION.md Part H.4 — Architecture decisions table

- **WEB.N241** ASSUME · `SPECIFICATION.md:4352` — "A realistic depth stays well under 20 entries, rides
  along in `/status`" — No pagination rests on this history-depth assumption. · [H13]
- **WEB.N242** INVAR · `SPECIFICATION.md:4353` — "Measurements and status/settings groups are never
  polled concurrently by design" — Single-flight rule. · related: WEB.T03 · [H13]
- **WEB.N243** MIRROR · `SPECIFICATION.md:4354` — "`poll-manager.js`'s `DEFAULT_TIMEOUT_MS` deliberately
  **equals** `asy_webserver_service.py`'s `outer_cap_s` (15.0s)" — js↔src constant mirror, enforced by
  `tests_scripts/test_request_timeout_ceiling.py`; rationale contested by WEB.S06 (client clock starts
  before connect). · related: WEB.S06, GEN.T06 · [H13]
- **WEB.N244** SETTLED · `SPECIFICATION.md:4355` — "No dedicated API-browser page" — Deliberate UI scope
  decision. · [H13]
- **WEB.N245** ASSUME · `SPECIFICATION.md:4356` — "Strict — visible error banner on mismatch" —
  Strictness claim for `validateDefinitions`; plan records it as shallow (WEB.S18/WEB.S23). · related:
  WEB.T05, WEB.S23 · [H13]
- **WEB.N246** MIRROR · `SPECIFICATION.md:4360` — "`type_or_range_error()`/`coerce_numeric()`, mirrored
  in `mock-server.js`" — src↔js validation mirror. · covered-by: WEB.T04 · [H13]
- **WEB.N247** INVAR · `SPECIFICATION.md:4361` — "derive the set from the tags, never from this list
  alone" — The dispatch-only list in the doc is illustrative; tags are authoritative. · related: WEB.T01
  · [H13 (also H13)]
- **WEB.N248** LIMIT · `SPECIFICATION.md:4361` — "An enum field with no GET-matching state renders a
  blank placeholder by default." — UI degraded display for command-only enums. · [H13]
- **WEB.N249** RISK · `SPECIFICATION.md:4365` — "Known accepted gap — An empty string can't be set via
  this UI for any field ... Accepted." | Accepted UI gap (`PW` open-network sentinel unreachable). ·
  [H13]
- **WEB.N250** MIRROR · `SPECIFICATION.md:4367-4370` — "`js/mock-server.js` mirrors every real backend
  quirk, not just the happy path: `PW` masked ... `ForceCalRef` always reports `400` ...
  `ContMeas`/`SGPResetVOC` never reported" — Mock↔backend quirk parity, covered by
  `tests_js/mock-server.test.js`; plan lists divergences. · related: WEB.S12 · [H13]

## SPECIFICATION.md Part H.5 — Definitions JSON schema

- **WEB.N251** INVAR · `SPECIFICATION.md:4377-4380` — "`websiteVersion` ... build provenance only, not
  validated or rendered anywhere in the UI ... never conflate the two" — Two version fields with
  different meaning. · related: GEN.T14 · [H13]
- **WEB.N252** LIMIT · `SPECIFICATION.md:4386-4393` — "`dispatch: true` ... is only consulted for `kind: \"toggle\"`
  and `kind: \"enum\"`" — Flag is inert on other kinds; behaviour relies on sparse-omission rules. ·
  related: WEB.S02 · [H13]
- **WEB.N253** TODO · `SPECIFICATION.md:4408` — "see H.5.1's own \"Not yet built\" note for what's still
  open" — Open retirement of hand-written definitions. · covered-by: WEB.S13 · [H13]

## SPECIFICATION.md Part H.5.1 — Definitions-file autogeneration

- **WEB.N254** ASSUME · `SPECIFICATION.md:4461-4462` — "`js/field-format.js`'s `formatFieldValue()` is
  the one place in the whole stack that rounds an emitted value (no driver in `src/` rounds anything)" —
  Unverified whole-stack claim. · [H13]
- **WEB.N255** TODO · `SPECIFICATION.md:4490-4493` — "**Not yet built**: retiring the two hand-written
  `wozi.json`/`dev.json` files ... done as of Session 6" — Open item; "Session 6" is an undefined label.
  · related: WEB.S13, DOC.T09 · [H13]

## SPECIFICATION.md Part H.6 — Errcount and dispatch-only conventions

- **WEB.N256** INVAR · `SPECIFICATION.md:4497-4501` — "plus each module's `CFGMGR_<name>` (except SCD30,
  NVM-backed) plus `WEBSERVER` ... **Keyed per logger instance, not per driver kind**" — Key-naming rule
  shared by firmware and website. · related: GEN.T06 · [H13]
- **WEB.N257** RISK · `SPECIFICATION.md:4501-4504` — "Getting this wrong fails in both directions and
  neither is visible ... a row with no published source renders a permanent, reassuring `0` from
  `templates.js`'s own `?? {counter: 0}` fallback" — Silent failure mode of errcount wiring. · related:
  WEB.S09 · [H13]
- **WEB.N258** MIRROR · `SPECIFICATION.md:4512-4513` — "`js/mock-server.js` mirrors this via dedicated
  dispatch functions — none ever persisted" — Mock dispatch mirror. · covered-by: WEB.T04 · [H13]

## SPECIFICATION.md Part H.7 — Digital twin integration / connection ceiling

- **WEB.N259** INVAR · `SPECIFICATION.md:4535-4536` — "seven modules concatenated into one `js/app.js`,
  plain text concatenation, safe since none use default exports/dynamic imports/re-exports" — Bundling
  safety rests on a convention; module count "seven" is a count to re-check. · related: WEB.T06 · [H13]

## SPECIFICATION.md Part H.8 — Web CI / tooling stack

- **WEB.N260** DRIFT · `SPECIFICATION.md:4718-4720` — "`js/poll-manager.js`'s \"Poll failed:\" is the
  poll loop's only failure diagnostic and is asserted by a test" — Plan: the `console.error("Poll failed:")`
  is dead (`fetchOnce` catches everything) and lives in `render.js`, not `poll-manager.js`. ·
  covered-by: WEB.S11 · [H13]
- **WEB.N261** INVAR · `SPECIFICATION.md:4725-4727` — "`scripts/build_website.sh` relies on it importing
  the literal `../js/app.js`" — The inline bootstrap's import path must never change. · related: WEB.T06
  · [H13]

## SPECIFICATION.md Part H.8.1 — JSDoc typedef imports

- **WEB.N262** INVAR · `SPECIFICATION.md:4755-4758` — "**Convention**: declare a narrow, structural
  local typedef instead of importing the real one" — Convention to keep Node-context type-check programs
  DOM-free. · [H13]

## SPECIFICATION.md Part L.7 — Product versioning

- **WEB.N263** MIRROR · `SPECIFICATION.md:6556-6558 (sites buildgen/version.py:7-8, html/definitions/wozi.json:3, dev.json:3)`
  — "The website version also appears independently as a top-level `websiteVersion` key in
  `definitions.json`" — Hand-written wozi/dev JSON hard-code `"2.0b0"`, so a `WEBSITE_VERSION` bump
  leaves them behind. · covered-by: GEN.T14 · [H13]

## CLAUDE.md

- **WEB.N264** MIRROR · `CLAUDE.md:84-85` — "the `src/`↔`js/` cross-language mirror obligation" — `src/`
  validation must be mirrored by `js/` (Part G.2). Convention only. · covered-by: WEB.T04 · [H14]

## README.md

- **WEB.N265** INVAR · `README.md:240-242` — "The `?device=` switch is a prototype-only convenience ...
  real firmware always serves exactly one definitions.json, never branches on a query param" —
  `js/app.js` hardcodes `KNOWN_DEVICES = ["wozi","dev"]`. · related: WEB.S22 · [H14]
- **WEB.N266** LIMIT · `README.md:238-241` — "a fake in-browser backend (`js/mock-server.js`,
  `mockdata/*.json`), driven by one of two worked-example `html/definitions/*.json` files" — Only wozi
  and dev can be previewed or mocked; the four generated devices have no mockdata. · related: WEB.T12,
  WEB.T15 · [H14]
- **WEB.N267** ASSUME · `README.md:258-260` — "it's wired to a single Playwright provider, which can
  only automate Chromium-family browsers" — Stated capability limit, unverified; it is the reason
  cross-browser runs outside Vitest (low). · [H14]
- **WEB.N268** LIMIT · `README.md:255-258` — "one field edit+apply per engine, at both a desktop and a
  mobile-sized viewport, against a real booted digital twin" — Minimal cross-browser coverage, wozi site
  only. · covered-by: WEB.T12 · [H14]

## BACKLOG.md

- **WEB.N269** MIRROR · `BACKLOG.md:163` — "html/definitions/dev.json/mockdata/dev.json updated with the
  new field" — A new driver data field must be hand-mirrored into the committed dev definitions and the
  mock fixture. · related: WEB.S13, WEB.T05 · [H15]
- **WEB.N270** TODO · `BACKLOG.md:771-782` — "Still open: retiring wozi/dev's own hand-written
  html/definitions/{wozi,dev}.json ... needs a tests_js/ fixture audit nobody has done yet" — Plus
  `KNOWN_DEVICES = ["wozi","dev"]` and no mockdata for the other four devices. · covered-by: WEB.S13,
  WEB.S22, WEB.T12 · [H15]
- **WEB.N271** TODO · `BACKLOG.md:783-787` — "Manual cross-browser/cross-device spot check not yet done
  — needs the project owner directly." — No real Safari / mobile pass. · related: WEB.T09 · [H15]
- **WEB.N272** RISK · `BACKLOG.md:816-820` — "harmless today (called exactly once per real page load),
  but a latent leak" — `js/nav.js` `initNav()` keydown listener never removed. · [H15]
- **WEB.N273** TODO · `BACKLOG.md:821-824` — "selectSection() is duplicated near-verbatim between
  js/app.js and js/main.js" — Low-priority duplicate (Part G.3). · covered-by: WEB.S18 · [H15]

## Commit messages (chronological)

- **WEB.N274** LIMIT · `commit 342c610 / d101e2a` — "The HTML/JS frontend is unchanged (known brittle,
  already deferred) and will need matching updates" — Wire-format changes (prefix drops, native bools,
  Led-prefix removal) not reflected in the legacy frontend at the time. · status: superseded by the
  website redesign (PRs #42-#49) | - · [H17]
- **WEB.N275** TODO · `commit b6cb852 / e4143c2` — "Left open, flagged for follow-up: the legacy HTML
  frontend's stale setSGP/setBMP field names" — Frontend redesign scope. · status: done (website
  redesign PRs #42-#49) | - · [H17]
- **WEB.N276** SETTLED · `commit cc999c1` — "the sparse-PUT convention can't submit an empty PW) per the
  project owner's explicit decision to leave both as-is" — UI cannot set an empty string (open-network
  PW). · tracked: SPECIFICATION.md:4365 | related: NET.S17 · [H17]
- **WEB.N277** SETTLED · `commit 2b927b2 / ffc9dcd` — "not a standing relaxation of \"never touch
  src/\"" — Website-effort sessions were barred from src/ edits except two owner-confirmed exceptions. ·
  status: historic (WEBSITE_PLAN.md later retired) | - · [H17]
- **WEB.N278** OPENQ · `commit 2b927b2` — "dev.json's unconfirmed SHTC3/MPRLS/ISL29125 projection" —
  dev.json projected fields for sensors never promoted (SHTC3/MPRLS). · status: ISL29125 promoted later
  (PR #75/#83); SHTC3/MPRLS still not in src/ — whether html/definitions/dev.json still carries them not
  verified (low) | related: WEB.T* · [H17]
- **WEB.N279** LIMIT · `commit b373034` — "The real backend's \"Unchanged\" PUT result essentially never
  fires in practice, matching an already-established tolerance in tests_js/live-backend.test.js" — Live
  tests tolerate a result code the backend defines but practically never emits (write_config compare
  semantics). · status: tolerance lives in tests_js; not found stated in SPECIFICATION (low) — UNTRACKED
  | related: WEB.T*, REST.T* · [H17]
- **WEB.N280** DRIFT · `commit e624018 / d082272` — "Document why DEV_UNIQUE_GROUPS currently matches
  zero dev sensor groups ... Dev is expected to gain its own unique sensor(s) later" —
  tests_js/mock-server-put-matrix.test.js:21 still names {SHTC3, MPRLS, ISL29125} and
  mockdata/dev.json:5-6,13-14,65-75 still carries SHTC3/MPRLS data/errcount entries, although
  html/definitions/dev.json has neither (rewritten in d082272; ISL29125 later added). Owner later
  decided "leave the mockdata orphans" (commit 12a616a, q5) but only in the retired ISL29125 planning
  doc; the test comment "matches none of dev's real groups today" is now stale since ISL29125 is a real
  dev group. · status: UNTRACKED (low; owner decision not in live docs) | related: HW.T07, PAR.S14 ·
  [H17]
- **WEB.N281** DRIFT · `commit 8e121ae` — "SPECIFICATION.md H.5's \"dispatch: true... H.6 minus
  ContMeas\" claim doesn't match the real wozi.json (lightCmdLED/PauseTime carry no dispatch:true there
  either)" — Flagged for owner. · status: resolved in wording — SPECIFICATION.md:4361,4393 now
  distinguish dispatch-only webserver fields from `dispatch=true` tag fields | - · [H17]
- **WEB.N282** NOTE(FLAG) · `commit 8ff9591` — "js/app.js's prototype-only KNOWN_DEVICES list only
  covers wozi/dev"; tests_hardware/bus_topology.py dead code — Website fixture gap; dead code. · status:
  KNOWN_DEVICES tracked: BACKLOG.md:776-781; bus_topology.py deleted (CLAUDE.md) | related: WEB.T* ·
  [H17]
- **WEB.N283** NOTE(OWNER) · `commit 12a616a` — q4 keep nested RGB/HSB; q5 "leave mockdata's SHTC3/MPRLS
  placeholders alone"; q6 rounding in the renderer via decimals hint — Decisions. · tracked: SPEC H.5
  (decimals/path); q5 only in retired planning doc (see e624018 above) | - · [H17]
- **WEB.N284** NOTE(FLAG) · `commit 1a858af` — "BACKLOG 29: html/definitions/dev.json advertises
  UARTLINK_Transfers ... mockdata/dev.json provides neither" — Mock-site gap and missing coverage check.
  · status: done-in 699836e (tests_js/definitions-mockdata-coverage.test.js) | - · [H17]
- **WEB.N285** NOTE(WIDENED-SCOPE) · `commit c1ab149` — web-unit-tests wedged on ENAMETOOLONG
  failure-screenshot names; "live-backend-put-matrix.test.js could NOT be run here" — Fixed; one file
  verified only by CI. · status: done | - · [H17]
- **WEB.N286** NOTE(DELIBERATE) · `commit 0260f60` — "cross_browser_smoke.mjs stays single-session,
  because engine diversity is what it exists for" — No concurrency in cross-browser smoke. · tracked:
  CONNECTION_SCALING_PLAN.md (deleted by 2a88cc8; not re-verified that this note migrated) | - · [H17]
