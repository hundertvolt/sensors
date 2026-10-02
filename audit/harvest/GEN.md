# Harvest — GEN: Build generator and device definitions

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`, moved to `4dc80ef` by V11).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: SETTLED 26, INVAR 63, MIRROR 51, LIMIT 54, RISK 7, ASSUME 45, PLATFORM 10, SUPPRESS 5, TODO 4, DRIFT 11, NOTE 4 — 280 items.


## src/asy_notification_service.py

- **GEN.N001** MIRROR · `src/asy_notification_service.py:80-82` — "their web metadata is generator-owned
  (buildgen.definitions._WARN_SIGNAL_WEB_CATALOG, the parallel of codegen._KNOWN_SIGNALS)" — Two
  hand-maintained buildgen catalogs must stay parallel. · covered-by: GEN.T06 · [H01]

## src/asy_uart_link_driver.py

- **GEN.N002** MIRROR · `src/asy_uart_link_driver.py:29` — "# @wiring fram_target AsyFramManager fram
  optional kwarg" — Machine-read buildgen tag must match the constructor's `fram=` kwarg (L.6.4) · [H02]

## src/asy_webserver_service.py

- **GEN.N003** MIRROR · `src/asy_webserver_service.py:90-93` — "resolved from
  [device.wiring].fram_target implicitly because this is mandatory infra... # @wiring fram_target
  AsyFramManager fram optional kwarg" — Tag line is buildgen input; must match the `fram=` kwarg · [H02]

## src/asy_wifi_service.py

- **GEN.N004** MIRROR · `src/asy_wifi_service.py:55-62` — "# @web SSID section=networking
  submitGroup=identity label=\"Wi-Fi SSID\"" — Machine-read `@web`/`@web-group` tags drive the generated
  website (buildgen/js) · [H02]
- **GEN.N005** MIRROR · `src/asy_wifi_service.py:100-108` — "# @wiring led_target NeopixelDriver
  set_ext_led optional setter / # @wiring fram_target AsyFramManager fram optional kwarg" — buildgen
  wiring tags must match `set_ext_led()`/`fram=` · [H02]

## src/config_manager.py

- **GEN.N006** SETTLED · `src/config_manager.py:46-48` — "A driver's generator-facing metadata is
  deliberately not a Python value at all - it lives in `# @wiring`/`# @value-wiring`/`# @limits` comment
  tags" — Tag-comment design (L.5, C.14.2) · [H02]
- **GEN.N007** MIRROR · `src/config_manager.py:72-73` — "Collision detection over a device's instance
  list is buildgen's." — Instance-name uniqueness enforced only in buildgen · related: CORE.T12 · [H02]

## src/system_service.py

- **GEN.N008** MIRROR · `src/system_service.py:49-52` — "# @wiring fram_target AsyFramManager fram
  optional kwarg" — buildgen tag must match the `fram=` kwarg · [H02]

## tests/_sensortask_scenarios.py

- **GEN.N009** ASSUME · `tests/_sensortask_scenarios.py:215-217` — "every device's TOML lists its
  instances in this same relative order (Part L.3), so the fixed shape below stays correct for all 6" —
  the expected FRAM chunk order is a fixed shape that relies on a TOML ordering convention · [H03]

## tests/test_bus_hazard_generated.py

- **GEN.N010** INVAR · `tests/test_bus_hazard_generated.py:69-71` — "the trailing digit IS the real
  hardware port id" — Relies on buildgen's "buses" key being exactly the TOML string `i2cN` · [H05]

## digital_twin/README.md

- **GEN.N011** PLATFORM · `digital_twin/README.md:238-239` — "`buildgen` needs `tomllib`, which the
  MicroPython Unix port doesn't have" — Wiring plan must be produced host-side in CPython · [H06]
- **GEN.N012** LIMIT · `digital_twin/README.md:270-275` — "asserting a real `GET` against five real REST
  endpoints all return 200" — Generated-boot test checks only five GET status codes per device ·
  related: TEST.T18 · [H06]
- **GEN.N013** MIRROR · `digital_twin/README.md:288-291` — "a fourth, optional `\"uart\"` key
  (`{\"initiator_var\", \"responder_var\"}`, the two generated Python variable names" — Twin reads
  generated variable names from the plan: a buildgen↔twin contract without schema version · related:
  TWIN.T12 · [H06]
- **GEN.N014** MIRROR · `digital_twin/README.md:824-827` — "add it to `buildgen/twin_wiring.py`'s own
  `FIXED_ADDRESSES` table too, matching the real driver's own hardcoded default address" — Copied
  address constant (driver ↔ buildgen table) · related: GEN (plan:1294) · [H06]

## digital_twin/run_generic_integration.py

- **GEN.N015** INVAR · `digital_twin/run_generic_integration.py:253-255` — "webserver is the last module
  build_system() assigns before its own grouped await x.setup() batch" — Readiness signal depends on
  generated-module assignment order (buildgen codegen); faults are applied only after this point, racing
  the boot setup batch · related: TWIN.T12 · [H06]
- **GEN.N016** MIRROR · `digital_twin/run_generic_integration.py:356-360, :373` —
  "`module.main(cfg_path=_CONFIG_DIR, web_host=config.host, web_port=config.port)`" / "`assert module.conn is not None and module.watchdog is not None`"
  — Contract with the generated module's `main()` signature and variable names · related: TWIN.T12 ·
  [H06]

## scripts/lint.sh

- **GEN.N017** LIMIT · `scripts/lint.sh:13` — "ruff check src tests digital_twin tests_hardware buildgen
  scripts toolchain tests_scripts" — ruff never sees `build/generated_src/` (the generated, frozen
  `sensortask_<device>.py`). · covered-by: GEN.S17 · [H09]

## scripts/_generate_sensortask_modules.py

- **GEN.N018** MIRROR · `scripts/_generate_sensortask_modules.py:47-50` — "\"instances\" is this
  script's addition, outside compute_twin_wiring()'s I2C/SPI-only contract" — Wiring-plan JSON schema is
  extended here, not in buildgen; consumers depend on both producers. · related: GEN.T15 · [H09]
- **GEN.N019** LIMIT · `scripts/_generate_sensortask_modules.py:40-44` — "except BuildError as e:" —
  Only `BuildError` is converted to exit 1; an `OSError` on write ends as a traceback. · covered-by:
  GEN.T16 · [H09]

## scripts/build_firmware.py

- **GEN.N020** DRIFT · `scripts/build_firmware.py:95-99` — "freshly generated text, never read off disk,
  so nothing to strip" — The generated module has its own `TYPE_CHECKING` block, frozen unstripped. ·
  covered-by: GEN.S07 · [H09]

## scripts/_digital_twin_ci_suite.py

- **GEN.N021** MIRROR · `scripts/_digital_twin_ci_suite.py:50-60` — "the real bus-level call each
  driver's own bus access goes through - confirmed directly against each driver's own read/write call
  sites" — `_BUS_FAULT_OPS` hand-mirrors each driver's bus call in `src/`; a driver change silently
  misdirects the fault. · covered-by: GEN.T06 · [H09]
- **GEN.N022** MIRROR · `scripts/_digital_twin_ci_suite.py:64-67` — "They all happen to equal
  driver.upper() here, which is NOT a general rule" — `_DRIVER_ERRCOUNT_NAME` is a verified narrow hand
  table. · covered-by: GEN.T06 · [H09]
- **GEN.N023** MIRROR · `scripts/_digital_twin_ci_suite.py:111` — "_SERVER_OUTER_CAP_S = 15.0 # mirrors
  asy_webserver_service.py's own outer_cap_s default - keep in sync" — Hand-mirrored constant. ·
  covered-by: GEN.T06 · [H09]
- **GEN.N024** RISK · `scripts/_digital_twin_ci_suite.py:615-621` — "That skip is SILENT, and it has
  cost real coverage: the ISL29125 ... sat outside every run here until 2026-09-18." — A new
  bus-attached driver is silently excluded from the fault matrix unless added to three hand tables in
  the same change. · covered-by: GEN.T06 · [H09]

## toolchain/versions.toml

- **GEN.N025** MIRROR · `toolchain/versions.toml:38-40` — "Sized for max_connections = 6 (Part H.7),
  2,324 B of GC heap per connection" — lwIP sizing is derived from every device TOML's `max_connections = 6`;
  the `[lwip]` table is read by both `buildgen.model.lwip_macros` and
  `setup_toolchain.load_lwip_macros`. · related: GEN.T15 · [H09]

## toolchain/micropython_overrides.py

- **GEN.N026** MIRROR · `toolchain/micropython_overrides.py:248-253, 293-296` — "The N-connection ones
  are checked per device by buildgen, which knows N." — Per-connection lwIP relationships are validated
  only through buildgen's per-device call, not at toolchain build time. · related: GEN.T15 · [H09]

## buildgen/__init__.py

- **GEN.N027** INVAR · `buildgen/__init__.py:1-3` — "Never imports `src/`; everything is derived by
  parsing TOML and AST-parsing driver source." — The never-import rule forces every src/ fact buildgen
  needs to be AST-read or hand-duplicated (see validate.py/codegen.py mirrors). · related: GEN.T06 ·
  [H09]

## buildgen/buildspec.py

- **GEN.N028** SETTLED · `buildgen/buildspec.py:5-7` — "The one hand-maintained per-driver table here
  ... It cannot be derived ... Adding a driver adds a row (Part L.6)." — Hand-maintained per-driver
  catalog, settled as such. · covered-by: GEN.T06 · [H09]
- **GEN.N029** ASSUME · `buildgen/buildspec.py:1-3` — "datasheet-checked by Session 2, not re-derived
  here" — Address facts rest on an earlier session's datasheet check; "Session 2" is an undefined
  historical label. (low) · related: DOC.S16 · [H09]
- **GEN.N030** INVAR · `buildgen/buildspec.py:49-51` — "Every BUS_ATTACHED_DRIVERS member belongs here."
  — `BUS_KIND_BY_DRIVER` must cover every bus-attached driver; convention only. · related: GEN.T13 ·
  [H09]

## buildgen/defaults.py

- **GEN.N031** LIMIT · `buildgen/defaults.py:36-45` — "positional = (item.args.posonlyargs +
  item.args.args)[1:] # drop \"self\"" — `_Default*` schema reads positional parameters only;
  keyword-only args are ignored. · covered-by: GEN.S10 · [H09]
- **GEN.N032** LIMIT · `buildgen/defaults.py:36-38` — "_path/_device/_driver are unused while this has
  no error path" — Unused context params kept for shape. (low) · [H09]

## buildgen/driver_registry.py

- **GEN.N033** SETTLED · `buildgen/driver_registry.py:13-21` — "Drivers that cannot follow the
  asy_<name>_driver.py/*_Reader convention" — `_OVERRIDES` hand table
  (fram/neopixel/notification/uart_link). · covered-by: GEN.T13 · [H09]
- **GEN.N034** SETTLED · `buildgen/driver_registry.py:28-31` — "uart_link is excluded on purpose - it
  needs the same override, but a device wires two instances" — `SINGLETON_SERVICE_DRIVERS` excludes
  uart_link (CLAUDE.md UART rule). · covered-by: GEN.T13 · [H09]
- **GEN.N035** ASSUME · `buildgen/driver_registry.py:62-64` — "SensorReaderConfig subclasses always need
  it ... bare SensorReader subclasses never do" — `needs_setup` inference from the base class, or `async def setup`
  for services. · related: GEN.T13 · [H09]
- **GEN.N036** INVAR · `buildgen/driver_registry.py:108-110` — "`_NAME = const(\"SCD30\")` (or a plain
  `_NAME = \"SCD30\"`) - the instance_name()/REST-key identity space" — Two naming spaces (TOML
  driver/name_ext vs `_NAME`) must never be conflated. · [H09]

## buildgen/errors.py

- **GEN.N037** INVAR · `buildgen/errors.py:1-3` — "every abort names exactly what's wrong and where -
  device, instance/bus, field - never a raw traceback" — Fail-loud contract; several raw-exception paths
  are already seeded. · covered-by: GEN.T01 · [H09]

## buildgen/frozen_modules.py

- **GEN.N038** MIRROR · `buildgen/frozen_modules.py:10-30` — "mandatory infra plus the modules
  build_system() itself always imports directly" — `CORE_MODULES` is a hand mirror of codegen's emitted
  imports; no test ties them. · covered-by: GEN.S11 · [H09]
- **GEN.N039** LIMIT · `buildgen/frozen_modules.py:41-42` — "continue # never executes on-device - not a
  real frozen-module dependency" — Skips a whole `if TYPE_CHECKING:` node including its `else:` branch.
  · covered-by: GEN.S11 · [H09]
- **GEN.N040** ASSUME · `buildgen/frozen_modules.py:47` — "level>0 (relative) doesn't occur in this flat
  layout" — Relative imports silently ignored. (low) · [H09]
- **GEN.N041** LIMIT · `buildgen/frozen_modules.py:53-61` — "tree = ast.parse(path.read_text(),
  filename=str(path))" — No `SyntaxError -> BuildError`; a module present in both roots resolves to
  `src/`. · covered-by: GEN.S11 · [H09]

## buildgen/generate.py

- **GEN.N042** DRIFT · `buildgen/generate.py:42, 57` — "write sensortask_<device>.py/<device>_boot.py
  here" — CLI names the boot entry `<device>_boot.py`, but firmware freezes it as `main.py` because a
  custom boot module "would cost USB entirely" (build_firmware.py:96-97). (low) · related: GEN.T16 ·
  [H09]
- **GEN.N043** LIMIT · `buildgen/generate.py:45-49` — "except BuildError as e:" — Only BuildError is
  caught; write errors end as tracebacks. · covered-by: GEN.T16 · [H09]

## buildgen/graph.py

- **GEN.N044** SUPPRESS · `buildgen/graph.py:16` — "# type: ignore[arg-type]" — Host-side type
  suppression. · [H09]
- **GEN.N045** INVAR · `buildgen/graph.py:30-32` — "sysfunct/conn/ntp are mandatory infra that inherit
  the device's FRAM chip implicitly ... webserver needs no entry ... codegen always emitting it last" —
  Ordering assumptions shared with codegen. · related: XCUT.T01 · [H09]
- **GEN.N046** LIMIT · `buildgen/graph.py:47-52` — "warn_* ... and Part L.6.3's generalized per-value
  measurement wiring share this exact shape, so one loop covers both" — Any `{source}` sub-table adds an
  edge, including stray `warn_*` keys on non-notification instances. · covered-by: GEN.S05 · [H09]
- **GEN.N047** SETTLED · `buildgen/graph.py:54-56` — "Stable priority tie-break: mandatory infra first
  ... then original TOML declaration order" — Determinism of construction order. · related: GEN.T11 ·
  [H09]

## buildgen/limits.py

- **GEN.N048** INVAR · `buildgen/limits.py:14-16` — "It must still carry range or choice-set
  punctuation, or prose beginning \"@limits\" would read as a tag" — Tag-vs-prose heuristic. ·
  covered-by: GEN.T03 · [H09]

## buildgen/model.py

- **GEN.N049** INVAR · `buildgen/model.py:26-28` — "The TOML's own driver/name_ext identity, never
  instance_name()/_NAME ... NotificationCoordinator's _NAME is \"NOTIFY\"" — Identity-space separation.
  · [H09]
- **GEN.N050** ASSUME · `buildgen/model.py:70-81` — "splitting the last \"_\"-group off as name_ext -
  which only a synthetic fixture needs today" — Wiring resolution fallback; unresolved keys returned for
  the caller to reject. · related: GEN.T04 · [H09]
- **GEN.N051** MIRROR · `buildgen/model.py:127-140` — "versions.toml's whole [lwip] table" — Second
  reader of `[lwip]` (the other is `setup_toolchain.load_lwip_macros`). · covered-by: GEN.T15 · [H09]

## buildgen/pico_gpio.py

- **GEN.N052** PLATFORM · `buildgen/pico_gpio.py:1-3` — "transcribed from
  RP-008312-DS-2-pico-w-datasheet.pdf Figure 2 (printed p.4)" — GPIO legality derived from the board
  figure, not RP2040 silicon function tables. · covered-by: GEN.T07 · [H09]
- **GEN.N053** LIMIT · `buildgen/pico_gpio.py:9-10, 26-27, 31-37` — "GP22/GP28 have no I2C function at
  all" / "GP20-22/GP26-28 have no SPI function" — Conservative tables (e.g. no UART1 on GP20/21, no SPI
  on GP20-22/26-28) reject pins silicon supports. · covered-by: GEN.T07 · [H09]
- **GEN.N054** MIRROR · `buildgen/pico_gpio.py:39-41` — "asy_uart_driver.py's module comment names
  GPIO24/25 and GPIO28/29 - a true claim about the RP2040 die's silicon mux" — Cross-file claim
  reconciled by comment only. · related: GEN.T07 · [H09]

## buildgen/requires_tag.py

- **GEN.N055** DRIFT · `buildgen/requires_tag.py:2, 59` — "placed at module level near
  `_WIRING`/`_VAL_*`" — Stale reference to `_VAL_*` placement. · covered-by: GEN.S14 · [H09]
- **GEN.N056** LIMIT · `buildgen/requires_tag.py:79-81` — "_check_bus_tables() validates only the bus
  fields it knows by name, not every field an @requires tag might name" — Coercion must handle arbitrary
  TOML types; `nan`/`inf` accepted. · covered-by: GEN.S10 · [H09]

## buildgen/schema_ast.py

- **GEN.N057** LIMIT · `buildgen/schema_ast.py:1-3, 44-46` — "Best-effort, never-imported AST extraction
  ... Anything else is silently skipped" — A schema constant in an unexpected shape silently drops out
  of the generated website definitions. · related: GEN.S10 · [H09]
- **GEN.N058** MIRROR · `buildgen/schema_ast.py:12, 36-37` — "config_manager.py's own FieldSchema width:
  (name, type, default, min, max, special)" — 6-tuple shape hand-mirrored from `src/config_manager.py`.
  · related: GEN.T15 · [H09]

## buildgen/tag_comments.py

- **GEN.N059** SETTLED · `buildgen/tag_comments.py:1-3, 238-240` — "a driver signature change once
  silently broke two tests_hardware/device_scripts/ call sites for a full day" — Near-miss tags must
  fail the build (L.5 standing rule). · covered-by: GEN.T03 · [H09]
- **GEN.N060** INVAR · `buildgen/tag_comments.py:21` — "A new family goes here, plus its own
  strict-grammar module beside requires_tag.py." — Registration of new tag families is by convention. ·
  related: GEN.T03 · [H09]
- **GEN.N061** DRIFT · `buildgen/tag_comments.py:121-126, 142-143` — "3-4 letters (the planned
  \"@web\")" / "the planned \"@web-group\" shape" — `@web`/`@web-group` are implemented (web_tag.py),
  not planned. · covered-by: GEN.S14 · [H09]
- **GEN.N062** DRIFT · `buildgen/tag_comments.py:142-149` — "A tag name is a word, optionally hyphenated
  ... anything after the first non-word character is payload" — Comment appears to sit above the wrong
  regex. · covered-by: GEN.S15 · [H09]
- **GEN.N063** LIMIT · `buildgen/tag_comments.py:161-164, 188-200` — "inside a class/function body, i.e.
  NOT module level" — Module-level detection heuristic (column-0 comment inside a function body reads as
  module level). · covered-by: GEN.S10 · [H09]
- **GEN.N064** ASSUME · `buildgen/tag_comments.py:260-262` — "\"required\"/\"require\" are within edit
  distance 2 of \"requires\" but are also ordinary English" — Typo detection requires the `@` sigil; a
  sigil-less typo is invisible by design. · covered-by: GEN.T03 · [H09]

## buildgen/twin_wiring.py

- **GEN.N065** MIRROR · `buildgen/twin_wiring.py:9-12` — "FIXED_ADDRESSES: \"dict[str, int]\" =
  {\"scd30\": 0x61, \"sgp40\": 0x59, \"isl29125\": 0x44}" — Hand copy of each driver's default I2C
  address. · covered-by: GEN.T06 · [H09]
- **GEN.N066** MIRROR · `buildgen/twin_wiring.py:1-36 (agent cited buildgen/twin_wiring.py:35-36)` —
  "the same shape `digital_twin/machine.py`'s `configure_wiring()` consumes" — Unversioned JSON contract
  with the twin. · covered-by: GEN.T15 · [H09] ⟨re-anchored: quote found at line 1⟩
- **GEN.N067** LIMIT · `buildgen/twin_wiring.py:56-59` — "raise ValueError(f\"digital twin twin_wiring
  has no address rule" — Raw `ValueError`, not `BuildError`, for a future driver. · covered-by: GEN.S10
  · [H09]
- **GEN.N068** ASSUME · `buildgen/twin_wiring.py:16-18` — "None on every device but \"dev\" today." —
  Only dev wires a UART pair. · [H09]

## buildgen/value_wiring.py

- **GEN.N069** INVAR · `buildgen/value_wiring.py:1-3` — "the per-value measurement wiring that
  generalizes `warn_*`'s `{source, field}` shape" — `field` existence on the source's data is not
  checked at build time. · covered-by: GEN.S06 · [H09]

## buildgen/version.py

- **GEN.N070** SETTLED · `buildgen/version.py:1-3` — "bump FIRMWARE_VERSION/WEBSITE_VERSION by hand; no
  automation exists or is planned" — Hand-bumped versions (`2.0b0`). · covered-by: GEN.T14 · [H09]

## buildgen/web_tag.py

- **GEN.N071** DRIFT · `buildgen/web_tag.py:19-21` — "Escaping a literal '\"' inside a quoted value is
  deliberately unsupported (see module docstring)." — The module docstring does not discuss it. ·
  covered-by: GEN.S14 · [H09]
- **GEN.N072** MIRROR · `buildgen/web_tag.py:30-32` — "js/definitions.js's own validateFieldHints()
  ceiling ... kept in step by hand" — `_MAX_DECIMALS` Python↔JS hand mirror. · covered-by: GEN.T15 ·
  [H09]
- **GEN.N073** MIRROR · `buildgen/web_tag.py:186-187` — "Mirrors js/definitions.js's own
  validateFieldHints() rule: a PUT body is always flat" — Writable-field path rule duplicated in JS. ·
  related: GEN.T15 · [H09]
- **GEN.N074** LIMIT · `buildgen/web_tag.py:100-102` — "Dot-joined rather than a JSON array" —
  Array-valued hints encoded as dot-joined strings. (low) · [H09]

## buildgen/wiring.py

- **GEN.N075** INVAR · `buildgen/wiring.py:15-17` — "dropping any one of the five leaves the line
  matching no tag at all - which check_for_near_miss_tags() then reports" — Tag grammar relies on
  near-miss detection to catch partial tags. · covered-by: GEN.T03 · [H09]

## buildgen/codegen.py

- **GEN.N076** MIRROR · `buildgen/codegen.py:17-21` — "_MAX_MODULE_ERROR = 5" — Hard-coded
  `_MAX_MODULE_ERROR`/`_DNS_TIMEOUT_MS`/`_DNS_TRIES`/`_NTP_FETCH_TIMEOUT_MS` emitted identically into
  every device. (low) · related: GEN.T06 · [H09]
- **GEN.N077** SETTLED · `buildgen/codegen.py:23-31` — "Every real device TOML uses identical threshold
  and colour values with no per-device override, so this hardcodes what the hand-written modules already
  did" — `_KNOWN_SIGNALS` catalog; mirrored by `definitions._WARN_SIGNAL_WEB_CATALOG`. · covered-by:
  GEN.T06 · [H09]
- **GEN.N078** TODO · `buildgen/codegen.py:280-281` — "only knows {sorted(_KNOWN_SIGNALS)} for now - ...
  or flag it as a future TOML-schema extension" — A new warn_* signal needs a code change; per-device
  thresholds are future work. · [H09]
- **GEN.N079** SUPPRESS · `buildgen/codegen.py:262` — "# type: ignore[union-attr]" — Host-side
  suppression. · [H09]
- **GEN.N080** SUPPRESS · `buildgen/codegen.py:301` — "import frozen_html # type:
  ignore[import-not-found] # noqa: F401" — Emitted into every generated (shipped) module. · related:
  GEN.S17 · [H09]
- **GEN.N081** SUPPRESS · `buildgen/codegen.py:303` — "from microdot import Microdot # type:
  ignore[import-not-found]" — Emitted into every generated module. · related: GEN.S17 · [H09]
- **GEN.N082** SUPPRESS · `buildgen/codegen.py:604, 607, 608, 609, 612, 613, 616` — "SettingsGroup(conn,
  (\"LedWifiOn\",)), # type: ignore[arg-type]" — Seven `arg-type` ignores emitted into generated
  firmware code (never checked: generated output is outside mypy reporting). · related: GEN.S17 · [H09]
- **GEN.N083** DRIFT · `buildgen/codegen.py:360-361, 375-376` — "mirrors build_system()'s documented
  shape in every hand-written sensortask_*.py" — No hand-written module exists since L.2. · covered-by:
  GEN.S16 · [H09] ⟨quote not matched at the anchor⟩
- **GEN.N084** LIMIT · `buildgen/codegen.py:336-343` — "lines.append(\"if TYPE_CHECKING:\")" — Generated
  module's own TYPE_CHECKING block ships unstripped. · covered-by: GEN.S07 · [H09]
- **GEN.N085** LIMIT · `buildgen/codegen.py:383-396, 405-411` — "timeout_kw = f\",
  timeout={bus_table['timeout']}\"" — TOML values emitted into source via `str()`/f-strings; safety
  depends entirely on validate.py type checks. · covered-by: GEN.T02 · [H09]
- **GEN.N086** LIMIT · `buildgen/codegen.py:426-429` — "lines.append(f\" conn.set_ext_led(" — Hard-coded
  consumer for `led_target`, not the tag's target. · covered-by: GEN.S09 · [H09]
- **GEN.N087** SETTLED · `buildgen/codegen.py:405-407` — "hostname/hotspot_password are [device]'s
  values, passed as the DEFAULTS of the two ConfigManager-persisted fields" — Device identity/hotspot
  password injected as defaults (shared hotspot password accepted-risk rule). · related: GEN.T08 · [H09]
- **GEN.N088** LIMIT · `buildgen/codegen.py:438` — "lines.append(\" timers_running =
  ThreadSafeFlag()\")" — Dead generated global. · covered-by: GEN.S13 · [H09]
- **GEN.N089** MIRROR · `buildgen/codegen.py:533-548 (agent cited buildgen/codegen.py:547-548)` —
  "sysfunct.pause_permanent_storage(300)" — 300 s mempause duration mirrored as "Pause backups for 5
  minutes" in `definitions.py:59`. (low) · [H09] ⟨re-anchored: quote found at line 533⟩
- **GEN.N090** LIMIT · `buildgen/codegen.py:563-567` — "lines.append(\" assert sgp40 is not None\")" —
  Bare global `sgp40` for any sgp40 instance; breaks under name_ext. · covered-by: GEN.S01 · [H09]
- **GEN.N091** INVAR · `buildgen/codegen.py:644-645` — "validate.py has already checked THAT value
  against the firmware's lwIP PCB count" — Emitted `max_connections`/`backlog` rely on validate.py's
  lwIP cross-check. · covered-by: GEN.T15 · [H09]
- **GEN.N092** ASSUME · `buildgen/codegen.py:660-662` — "Getting it wrong was AttributeError on every
  FRAM-wired device, caught only by Part L.4" — fram excluded from task/timer collectors by hand. ·
  [H09]
- **GEN.N093** PLATFORM · `buildgen/codegen.py:696-709` — "matching how a real deployed unit boots today
  (see modules/_boot.py)" — Boot entry: `gc.threshold(32768)`, import outside `try`,
  `asyncio.new_event_loop()` in `finally`; executed by no tier. · covered-by: GEN.T14 · [H09]

## buildgen/validate.py

- **GEN.N094** PLATFORM · `buildgen/validate.py:31-34` — "Pico W exposes exactly two I2C, two SPI and
  two UART peripheral indices" — RP2040 peripheral count fact. · [H09]
- **GEN.N095** MIRROR · `buildgen/validate.py:50-52` — "uart's optional fields mirror
  asy_uart_driver.UART's kwargs of the same name" — Allowed UART bus fields hand-mirror
  `src/asy_uart_driver.py`. · related: GEN.T15 · [H09]
- **GEN.N096** MIRROR · `buildgen/validate.py:58-61` — "asy_uart_comm.ROLE_INITIATOR/ROLE_RESPONDER's
  own literal values, duplicated here rather than imported" — String literals are the contract between
  buildgen and src/. · related: GEN.T06 · [H09]
- **GEN.N097** MIRROR · `buildgen/validate.py:64` — "_HOSTNAME_MAX_LEN = 32 # network.hostname()'s real
  cap; asy_wifi_service._VAL_HOST carries the same number" — Python↔src hand mirror; also a platform
  fact. · covered-by: GEN.T15 · [H09]
- **GEN.N098** MIRROR · `buildgen/validate.py:71` — "_NTP_CHECK_TICK_S = 10 #
  asy_ntp_client._NTP_CHECK_INTERV" — Hand-mirrored src constant. · covered-by: GEN.T06 · [H09]
- **GEN.N099** MIRROR · `buildgen/validate.py:72-73` — "_WPA2_MAX_PASSWORD_LEN = 63 # its maximum too;
  asy_wifi_service._VAL_HOTSPOT_PW carries the same pair" — WPA2 bounds mirrored with src. · covered-by:
  GEN.T15 · [H09]
- **GEN.N100** SETTLED · `buildgen/validate.py:66-67` — "the checks below run against that EFFECTIVE
  value - so no device can outrun its firmware by simply saying nothing" — Absent optional fields
  validated at their class defaults (AST-read). · [H09]
- **GEN.N101** ASSUME · `buildgen/validate.py:124-126` — "an over-long one would be dropped back to
  \"SensorNode\" by _with_default()" — Runtime fallback identity. · [H09]
- **GEN.N102** MIRROR · `buildgen/validate.py:191-193` — "toolchain/micropython_overrides.py owns the
  relationships ... Loaded by path" — buildgen imports toolchain code by file path. · covered-by:
  GEN.T15 · [H09]
- **GEN.N103** MIRROR · `buildgen/validate.py:236, 246-247` — "the shipped defaults, pinned coherent by
  tests_scripts/test_buildgen_validate.py" / "poll_idle_ms's None default means \"poll_wait_ms\",
  mirrored here rather than read" — Default semantics hand-mirrored from `asy_uart_driver.UART`. ·
  related: GEN.T06 · [H09]
- **GEN.N104** DRIFT · `buildgen/validate.py:280-282` — "[bus.*] may be absent entirely" — Declared
  legal, but codegen crashes with a raw KeyError on a TOML with no `[bus]`. · covered-by: GEN.S03 ·
  [H09]
- **GEN.N105** LIMIT · `buildgen/validate.py:383-386` — "These three reach codegen's hex()/str()
  argument-building unvalidated otherwise" — Only three fields are type-guarded here; `irq_pull_up` is
  not. · covered-by: GEN.S02 · [H09]
- **GEN.N106** ASSUME · `buildgen/validate.py:447-449` — "Unreachable with today's six driver names ...
  but latent for a future one" — Latent identity-collision gap. · related: GEN.T04 · [H09]
- **GEN.N107** INVAR · `buildgen/validate.py:539-544` — "RP2040 has two UART peripherals, so a device
  wires at most one crossover pair" — Enforced here; `compute_twin_wiring()` relies on it. · [H09]
- **GEN.N108** LIMIT · `buildgen/validate.py:580-591` — "resolved by attribute name alone rather than a
  fixed producer_class" — `{source, field}` never checks `field` exists. · covered-by: GEN.S06 · [H09]
- **GEN.N109** LIMIT · `buildgen/validate.py:645-672` — "per-signal getters (source/field pairs) -
  checked separately below" — `warn_*` accepted on any instance. · covered-by: GEN.S05 · [H09]
- **GEN.N110** INVAR · `buildgen/validate.py:707-709` — "Both device-wiring fields are optional today,
  so this never fires yet; kept in sync" — Required-field enforcement path untested by real devices. ·
  [H09] ⟨quote not matched at the anchor⟩
- **GEN.N111** INVAR · `buildgen/validate.py:747-749` — "it is the only stage that reads
  toolchain/versions.toml at all" — lwIP coherence is the last validation stage. · [H09]

## buildgen/definitions.py

- **GEN.N112** SETTLED · `buildgen/definitions.py:20-23` — "SCHEMA_VERSION is this file's wire-format
  shape version ... never conflate the two (Part L.7)" — `SCHEMA_VERSION = "1.0.0"` pairs with js
  `SUPPORTED_SCHEMA_MAJOR`. · covered-by: GEN.T15 · [H09]
- **GEN.N113** MIRROR · `buildgen/definitions.py:39-41` — "_SENSOR_DRIVERS = (\"scd30\", \"sgp40\",
  \"bmp3xx\", \"isl29125\")" — Hand catalog; a new sensor driver needs a row. · covered-by: GEN.T06 ·
  [H09]
- **GEN.N114** MIRROR · `buildgen/definitions.py:43-50` — "buildgen.codegen._KNOWN_SIGNALS' own parallel
  ... Min/max match that catalog's own field-schema literals exactly" — Two hand catalogs must agree. ·
  covered-by: GEN.T06 · [H09]
- **GEN.N115** MIRROR · `buildgen/definitions.py:87-121` — "Generator-owned like the catalogs above:
  cosmetic labels, owned by no source file." — `_ERRCOUNT_CATALOG`, `_ERRCOUNT_NAME`, `_CFGMGR_LABEL`,
  `_NAME_EXT_LABEL` hand tables mirroring src `_NAME`s and CFGMGR companions. · covered-by: GEN.T06 ·
  [H09]
- **GEN.N116** LIMIT · `buildgen/definitions.py:512-531` — "model = build_model(args.device_toml,
  args.src_dir)" — CLI path never builds `construction_order` (ordering can differ from codegen) and
  only catches BuildError. · covered-by: GEN.S08 · [H09]

## devices/dev.toml

- **GEN.N117** SETTLED · `devices/dev.toml:1-2` — "the bench rig, the only unit ever flashed; always
  built from this file, never from wozi's pins (CLAUDE.md's WoZi rule)" — dev-bench quirks are out of
  scope as bugs (CLAUDE.md). · [H09]
- **GEN.N118** MIRROR · `devices/dev.toml:11-14` — "kept below the firmware's own lwIP MEMP_NUM_TCP_PCB
  (toolchain/versions.toml) with margin ... backlog is omitted, so it derives max_connections + 1" —
  `max_connections = 6` must stay coherent with `[lwip]`; enforced by validate.py's lwIP check. Same
  comment in all six TOMLs. · covered-by: GEN.T15 · [H09]

## devices/wozi.toml

- **GEN.N119** SETTLED · `devices/wozi.toml:1-2` — "the exemplary/base device; never physically flashed,
  its correctness comes from tests/" — CLAUDE.md WoZi rule. · [H09]

## pyproject.toml

- **GEN.N120** LIMIT · `pyproject.toml:359-365` — "follow_imports = \"silent\"" / "build/generated_src
  for device_scripts' one static `import sensortask_dev`" — Errors inside generated modules and the stub
  package are never reported. · covered-by: GEN.S17 · [H09]

## tests_scripts/buildgen_fixtures/novel_combo.toml

- **GEN.N121** ASSUME · `tests_scripts/buildgen_fixtures/novel_combo.toml:2-5` — "existing drivers mixed
  in a pin/bus layout none of the 6 real devices/*.toml use" — Novelty claims (two SCD30s, BMP3xx at
  0x76, one warn_* signal, uart on GP16/17) are relative to the current six TOMLs and are not
  machine-checked; a device TOML adopting the same layout would silently make the fixture non-novel ·
  related: GEN.T06 · [H10]
- **GEN.N122** PLATFORM · `tests_scripts/buildgen_fixtures/novel_combo.toml:44-48` — "uart1 has only two
  legal pairs at all (GP4/5, GP8/9 - buildgen.pico_gpio.UART_ROLE)" — RP2040 pin-mux claim embedded in a
  fixture comment; correctness owned by pico_gpio's table · related: GEN.T07 · [H10]
- **GEN.N123** ASSUME · `tests_scripts/buildgen_fixtures/novel_combo.toml:107-109` — "dev.toml's own
  instance always wires fram_target, so this fixture is what exercises the \"no fram_target\" branch" —
  The only coverage of ISL29125's no-FRAM branch is this synthetic fixture · [H10]

## tests_scripts/test_buildgen_defaults.py

- **GEN.N124** ASSUME · `tests_scripts/test_buildgen_defaults.py:55-56` — "only the two required=True
  wiring fields need this mechanism" — Pins that only temperature_source/humidity_source/signal_sink
  have `_Default<Field>` providers; fram_target is not defaultable · [H10]
- **GEN.N125** LIMIT · `tests_scripts/test_buildgen_defaults.py:62-68` — "def __init__(self,
  required_one, optional_one=5)" — Parameter extraction is tested for positional args only; keyword-only
  args are never exercised (the plan records `default_init_params` ignoring them) · covered-by: GEN.S10
  · [H10]

## tests_scripts/test_buildgen_definitions.py

- **GEN.N126** LIMIT · `tests_scripts/test_buildgen_definitions.py:248-249` — "Dropping one @web tag
  doesn't break the build - it just means that field never reaches the website" — Known, pinned
  behaviour: a schema field missing its `@web` tag silently disappears from the UI · related: GEN.T03 ·
  [H10]
- **GEN.N127** ASSUME · `tests_scripts/test_buildgen_definitions.py:271-273` — "asy_ntp_client.py
  deliberately never declares its own @web-group for section=system submitGroup=settings
  (system_service.py is the sole owner)" — Ownership convention for the system settings group · [H10]
- **GEN.N128** ASSUME · `tests_scripts/test_buildgen_definitions.py:379-380,389-390,400` —
  "buildgen.validate._resolve_instances() always sets resolved_name before definitions generation ever
  runs" — Three "internal:" invariant guards reached only by hand-built models; relies on validate.py
  always resolving first (the CLI path is noted as differing in GEN.S08) · related: GEN.S08 · [H10]

## tests_scripts/test_buildgen_driver_registry.py

- **GEN.N129** INVAR · `tests_scripts/test_buildgen_driver_registry.py:73,80-81` — "assert {\"fram\",
  \"neopixel\", \"notification\", \"uart_link\"} == SERVICE_DRIVERS" — Pins the override/service driver
  set and that `uart_link` is excluded from `SINGLETON_SERVICE_DRIVERS` (CLAUDE.md UART rule) · related:
  GEN.T13 · [H10]
- **GEN.N130** ASSUME · `tests_scripts/test_buildgen_driver_registry.py:77-79` — "a device wires exactly
  two instances (initiator/responder)" — Stated uart_link cardinality; not enforced by this test ·
  related: UART.T05 · [H10]
- **GEN.N131** ASSUME · `tests_scripts/test_buildgen_driver_registry.py:94-96` —
  "NotificationCoordinator's _NAME is \"NOTIFY\", not \"NOTIFICATION\"" — Pins a confirmed-real naming
  mismatch (L.3) between log name space and TOML driver identity · [H10]

## tests_scripts/test_buildgen_frozen_modules.py

- **GEN.N132** LIMIT · `tests_scripts/test_buildgen_frozen_modules.py:108-111` — "one with no .py file
  anywhere in the roots contributes nothing rather than raising, so a stale seed name can't break a
  build" — A stale/misspelled seed name is silently tolerated at closure time (caught later only by
  build_stage_dir's missing-file check) · related: GEN.S11 · [H10]
- **GEN.N133** MIRROR · `tests_scripts/test_buildgen_frozen_modules.py:51-63,79-91` — "(tmp_path /
  \"config_manager.py\").write_text(\"\")" — Two synthetic trees hand-list the 13 `CORE_MODULES` names;
  a change to CORE_MODULES needs both lists edited · related: GEN.S11 · [H10]
- **GEN.N134** LIMIT · `tests_scripts/test_buildgen_frozen_modules.py:49-50,64-66` — "A module only
  reachable through an `if TYPE_CHECKING:` block never executes on-device" — Only the `try: from typing import TYPE_CHECKING / except ImportError`
  + plain `if TYPE_CHECKING:` shape is tested; `else:` branches are not (GEN.S11 notes the whole `If`
  incl. orelse is skipped) · related: GEN.S11 · [H10]
- **GEN.N135** LIMIT · `tests_scripts/test_buildgen_frozen_modules.py:23-26` — "for driver_module in
  (\"asy_scd30_driver\", ... \"asy_notification_service\")" — Real-device closure checks run on wozi
  only · [H10]

## tests_scripts/test_buildgen_generate.py

- **GEN.N136** LIMIT · `tests_scripts/test_buildgen_generate.py:5-7` — "never executed under a real
  interpreter - booting a generated module is Session 5's digital-twin work" — This file proves only
  `ast.parse` + structure; runtime is the twin tier's job; "Session 5" is an undefined historic label ·
  covered-by: GEN.T10 · [H10]
- **GEN.N137** INVAR · `tests_scripts/test_buildgen_generate.py:48-53` — "The generated module's single
  WDT() site needs its own proof." — Pins exactly one `WDT(` substring per generated module; the
  src/-side check in `test_reset_call_site_invariant.py` "is now vacuous" for sensortask_*.py ·
  covered-by: TEST.S17 · [H10]
- **GEN.N138** LIMIT · `tests_scripts/test_buildgen_generate.py:57-66` — "a feed after every await
  X.setup() - never inside a loop - is what guarantees" — Feed check matches only lines of the exact
  form `await <name>.setup()`; a setup call with arguments or another shape escapes it, and "never
  inside a loop" is not asserted · related: XCUT.T03 · [H10]
- **GEN.N139** SETTLED · `tests_scripts/test_buildgen_generate.py:108-121` — "the build date is
  explicitly injected rather than computed on-device" / "the version no longer lives on GET /status's
  \"system\" section" — Regression pins for L.7's version placement (`/system` build_info) · related:
  GEN.T14 · [H10]
- **GEN.N140** LIMIT · `tests_scripts/test_buildgen_generate.py:416-418` — "trigger_sec is declared only
  on scd30 in every real device and fixture, so bmp3xx's own trigger_sec rendering had never been
  exercised" — Coverage gap found by a sweep; now covered by a base_doc-mutation test only · [H10]
- **GEN.N141** ASSUME · `tests_scripts/test_buildgen_generate.py:470-472` — "No real bus id or instance
  label can reach this today (both are drawn from closed sets)" — Identifier guard is the "one guard
  standing between a bad name and generated source that would not parse"; reached only directly ·
  related: GEN.T02 · [H10]
- **GEN.N142** ASSUME · `tests_scripts/test_buildgen_generate.py:487-489,498-500,512-514,527-529` —
  "_check_required_fields() rejects a driver with no buildspec.py entry long before codegen sees it" —
  Four codegen "internal invariant" guards are reachable only by mutating already-validated models ·
  [H10]
- **GEN.N143** MIRROR · `tests_scripts/test_buildgen_generate.py:589-590` — "validate.py checks the
  stated values against the firmware's lwIP pools; that check is only worth anything if the same values
  are the ones the device is then built with" — Pins TOML max_connections/backlog → WebserverService
  kwargs; absent values are left to the class default · related: GEN.T15 · [H10]
- **GEN.N144** LIMIT · `tests_scripts/test_buildgen_generate.py:569-575` — "assert \"Traceback\" not in
  result.stderr" — CLI error path tested only for a BuildError-producing TOML; non-BuildError failures
  (e.g. OSError on write) are untested · covered-by: GEN.T16 · [H10]

## tests_scripts/test_buildgen_graph.py

- **GEN.N145** ASSUME · `tests_scripts/test_buildgen_graph.py:28-30` — "The hand-verified construction
  order (Part A.7): fram before conn/ntp/sysfunct" — Test pins construction order
  fram→conn→ntp→sysfunct; the plan records A.7 stating a different setup order · related: DOC.S09 ·
  [H10]
- **GEN.N146** ASSUME · `tests_scripts/test_buildgen_graph.py:62-64` — "No real driver's _WIRING
  requires SGP40_Reader as a producer, so a genuine cycle is not expressible with the actual driver set"
  — Cycle rejection tested only on a synthetic model · [H10]
- **GEN.N147** ASSUME · `tests_scripts/test_buildgen_graph.py:77-79` — "Only AsyConnTime declares one
  today, and it is mandatory infra" — Setter-mode wiring on an instance is exercised only synthetically
  · related: GEN.S09 · [H10]

## tests_scripts/test_buildgen_limits.py

- **GEN.N148** INVAR · `tests_scripts/test_buildgen_limits.py:185-203` — "assert tagged ==
  {\"asy_bmp3xx_driver.py\", \"asy_isl29125_driver.py\"}" — Pinned set of src/ modules carrying
  `@limits` (BMP3xx address {0x76,0x77} + trigger_sec 1..3600; ISL29125 trigger_sec 1..3600); a new tag
  elsewhere fails until recorded · related: GEN.T03 · [H10]
- **GEN.N149** LIMIT · `tests_scripts/test_buildgen_limits.py:97` — "One domain per field: two tags
  would silently let the second win." — Duplicate-domain rejection exists because of a silent-override
  hazard · [H10]

## tests_scripts/test_buildgen_requires_tag.py

- **GEN.N150** INVAR · `tests_scripts/test_buildgen_requires_tag.py:174-189` — "Every real tag any src/
  driver declares today ... assert tagged == {\"asy_scd30_driver.py\", \"asy_sgp40_driver.py\"}" —
  Pinned `@requires` set: SCD30 timeout>=200000 and frequency<=100000, SGP40 frequency<=400000;
  ISL29125, BMP3xx and FRAM declare none · related: SENS.T17 · [H10]
- **GEN.N151** LIMIT · `tests_scripts/test_buildgen_requires_tag.py:319-321` — "A None value is
  indistinguishable from an absent key here, and reports as the missing field it effectively is." —
  Known behaviour pinned · [H10]
- **GEN.N152** ASSUME · `tests_scripts/test_buildgen_requires_tag.py:258-262` — "mirrors the real
  near-collision in buildgen/validate.py ... \"# @requires tag, not here).\"" — False-positive guard
  modelled on a specific wrapped comment in validate.py; "edit distance 3 - outside the typo tolerance"
  pins the near-miss threshold · related: GEN.T03 · [H10]

## tests_scripts/test_buildgen_schema_ast.py

- **GEN.N153** LIMIT · `tests_scripts/test_buildgen_schema_ast.py:1-3,66-67,90-92` — "the silent-skip
  behavior for anything else" / "a real gap this best-effort pass must not crash on" — Schema extraction
  is best-effort: unresolvable names and unsupported literal shapes are silently skipped, so a driver
  schema that stops resolving silently drops out (no error) · related: GEN.S10 · [H10]
- **GEN.N154** ASSUME · `tests_scripts/test_buildgen_schema_ast.py:132-133` — "consts resolution walks
  tree.body in source order, so the later one must be the one used" — Last-assignment-wins semantics for
  reassigned module constants (ignores conditional/nested assignment) · [H10]

## tests_scripts/test_buildgen_tag_comments.py

- **GEN.N155** INVAR · `tests_scripts/test_buildgen_tag_comments.py:1-3` — "a typo'd or misplaced
  attempt must fail loud, never read as \"no tag here\"" — Standing rule for every tag family; pins typo
  tolerance at edit distance 2 (1 for short names like "web"), case-folded exact match · related:
  GEN.T03 · [H10]
- **GEN.N156** RISK · `tests_scripts/test_buildgen_tag_comments.py:364-366` — "at the accepted cost of
  flagging the prose nobody writes (\"@wiring is what this module needs\")" — Accepted false-positive: a
  sigil + bare-word payload in prose fails the build · related: GEN.T03 · [H10]
- **GEN.N157** ASSUME · `tests_scripts/test_buildgen_tag_comments.py:308-310` — "Mirrors a real
  near-collision in this repo, where a wrapped comment line began with the tag's own name" —
  False-positive guard modelled on one real comment; comment-reflow elsewhere could create new
  collisions · [H10]
- **GEN.N158** LIMIT · `tests_scripts/test_buildgen_tag_comments.py:378-379` — "A single shared
  heuristic would go blind on whichever shape it wasn't written for" — Near-miss detection is per-family
  shape predicates; a new tag family needs its own predicate or its typos go undetected · related:
  GEN.T03 · [H10]

## tests_scripts/test_buildgen_twin_wiring.py

- **GEN.N159** MIRROR · `tests_scripts/test_buildgen_twin_wiring.py:96-98` — "src/asy_scd30_driver.py's
  own _SCD30_DEFAULT_ADDR, src/asy_sgp40_driver.py's own address=0x59 default, and
  src/asy_isl29125_driver.py's own hard-wired 0x44" — `buildgen/twin_wiring.FIXED_ADDRESSES` mirrors
  three driver constants by hand · covered-by: GEN.T06 · [H10]
- **GEN.N160** ASSUME · `tests_scripts/test_buildgen_twin_wiring.py:114-116` — "Unreachable through any
  real TOML, buildspec.py's three classification sets partitioning BUS_ATTACHED_DRIVERS exhaustively" —
  Defensive fallback reached only by monkeypatch · [H10]

## tests_scripts/test_buildgen_validate.py

- **GEN.N161** RISK · `tests_scripts/test_buildgen_validate.py:92-94` — "dropped at boot back to the
  password published in src/ - silently, on every device at once" — Out-of-bounds TOML hotspot password
  would silently fall back to src/'s shared default at boot; the build-time 8..63 check is the only
  guard · related: SEC.T04 · [H10]
- **GEN.N162** RISK · `tests_scripts/test_buildgen_validate.py:160-165` — "an over-long one would be
  dropped back to the shared \"SensorNode\" default at boot instead of failing" — Silent boot fallback
  for an over-long hostname; build caps `SensorStation<Name>` at 32 ("one over network.hostname()'s cap"
  = 33) · related: NET.S17 · [H10]
- **GEN.N163** LIMIT · `tests_scripts/test_buildgen_validate.py:181-198` — "An empty/absent [bus.*] is
  not rejected on its own" / "is a logically valid, simplest-possible shape" — Validate accepts a device
  with no buses/instances; the plan records codegen crashing on a missing [bus] table · related: GEN.S03
  · [H10]
- **GEN.N164** PLATFORM · `tests_scripts/test_buildgen_validate.py:254,280,289,296-297` — "GP22 is a
  real, usable GPIO (not wireless-reserved) that simply has no I2C function" — RP2040/Pico W
  pin-function facts pinned by tests (GP2/3 I2C1, GP22 no I2C, ADC2-only, GP23/24/25/29
  wireless-reserved) · related: GEN.T07 · [H10]
- **GEN.N165** LIMIT · `tests_scripts/test_buildgen_validate.py:242-244` — "spi1 is legal but
  unexercised by any real device: fram is the only SPI-attached driver and is a forced singleton" — spi1
  path exercised only synthetically · [H10]
- **GEN.N166** ASSUME · `tests_scripts/test_buildgen_validate.py:549-551,634-636,648-650` — "No real
  driver's _NAME collides this way" / "unreachable with today's driver names" / "no real TOML can
  produce two" — Several uniqueness/collision checks reachable only via synthetic models; claims rest on
  today's driver set · [H10]
- **GEN.N167** ASSUME ·
  `tests_scripts/test_buildgen_validate.py:563-565,576-578,594-595,608-609,620-621` —
  "_resolve_instances() always sets resolved_name before this check ever runs" — Five "internal:"
  invariant guards driven only by hand-built specs/monkeypatch · [H10]
- **GEN.N168** ASSUME · `tests_scripts/test_buildgen_validate.py:1096-1098` — "Error-path coverage sweep
  (2026-09-10): every abort below was reachable but had no test of its own" — Dated one-time sweep;
  completeness after later validate.py changes is not re-checked · related: GEN.T01 · [H10]
- **GEN.N169** LIMIT · `tests_scripts/test_buildgen_validate.py:1181-1182` — "No driver in src/ declares
  one today, so the tag is staged onto sgp40." — The optional `@value-wiring` path exists only in staged
  copies · [H10]
- **GEN.N170** INVAR · `tests_scripts/test_buildgen_validate.py:1327-1332` — "dev is the only device
  with a link; this pins that its bench tuning really boots the link" — Globs every devices/*.toml
  without the `zz_test_*` filter used at :1735 (low) · related: TEST.T13 · [H10]
- **GEN.N171** SETTLED · `tests_scripts/test_buildgen_validate.py:1729-1730` — "The owner's decision
  (2026-09-22) is that the recommended setting ships on every device" — Every shipped device TOML must
  state `[device].max_connections` · [H10]

## tests_scripts/test_buildgen_value_wiring.py

- **GEN.N172** INVAR · `tests_scripts/test_buildgen_value_wiring.py:133-142` — "assert tagged ==
  {\"asy_sgp40_driver.py\"}" — Pinned: SGP40 is the only `@value-wiring` declarer
  (temperature_source/humidity_source, both required) · related: GEN.T03 · [H10]
- **GEN.N173** ASSUME · `tests_scripts/test_buildgen_value_wiring.py:36-37` — "The three names are
  independent by design - nothing requires the TOML field and the constructor kwarg to be spelled the
  same, they just happen to be in src/ today" — Coincidental same-spelling of TOML field/kwarg in src/ ·
  [H10]

## tests_scripts/test_buildgen_version.py

- **GEN.N174** DRIFT · `tests_scripts/test_buildgen_version.py:10-13` — "PEP 440-style
  release[.dev|a|b|rc][N] segment" — `_VERSION_RE` (`^\d+\.\d+(?:(?:a|b|rc)\d+)?$`) accepts no `.dev`
  and no patch component, contrary to the comment (low) · [H10]
- **GEN.N175** TODO · `tests_scripts/test_buildgen_version.py:24-27` — "SPECIFICATION.md Part L.7:
  \"firmware + website, both starting at 2.0b0\"." — Test pins both versions at 2.0b0; any hand bump
  must also edit this test (no bump mechanism exists) · related: GEN.T14 · [H10]

## tests_scripts/test_buildgen_web_tag.py

- **GEN.N176** INVAR · `tests_scripts/test_buildgen_web_tag.py:533-538` — "assert tagged ==
  {\"asy_scd30_driver.py\", \"asy_sgp40_driver.py\", ... \"asy_notification_service.py\"," — Pinned set
  of 8 `@web`-tagged src/ modules plus per-driver field-name sets (SCD30, BMP3xx, ISL29125, SGP40, WiFi,
  NTP, System, Notification); neopixel, webserver and uart_link carry no @web tags · related: WEB.T05 ·
  [H10]
- **GEN.N177** ASSUME · `tests_scripts/test_buildgen_web_tag.py:459-461` — "R/G/B/H/S/Bri are the first
  (and, at the time of writing, only) fields in src/ whose measurement body is nested" — Nested `path`
  capability exercised by ISL29125 only; dated claim · [H10]
- **GEN.N178** LIMIT · `tests_scripts/test_buildgen_web_tag.py:515-530` — "assert any((t.section,
  t.submit_group) == expected_key for t in tags)" — @web-group real-driver check asserts presence of one
  expected group, not the full group set per file (low) · [H10]

## tests_scripts/test_buildgen_wiring.py

- **GEN.N179** INVAR · `tests_scripts/test_buildgen_wiring.py:225-272` — "A new tag appearing in a
  module nobody expected it in should fail this test, not go unnoticed." — Pinned `@wiring` table for 11
  src/ modules (fram_target kwarg everywhere; SGP40's target is `fram_storage`; WiFi `led_target` setter
  `set_ext_led`; notification `signal_sink` attr `request_signal`, required) · related: GEN.S09 · [H10]
- **GEN.N180** SETTLED · `tests_scripts/test_buildgen_wiring.py:185-187` — "The one deletion that does
  NOT abort, deliberately and consistently with @requires" — A comment consisting only of the tag name
  is tolerated as prose (all tag families) · [H10]
- **GEN.N181** RISK · `tests_scripts/test_buildgen_wiring.py:146-148` —
  "(\"warning\"/\"writing\"/\"winning\" are all only two edits away and DO get flagged, which is the
  intended trade" — Accepted false-positive class for `@wiring` near-miss detection · related: GEN.T03 ·
  [H10]
- **GEN.N182** LIMIT · `tests_scripts/test_buildgen_wiring.py:119` — "Two tags for one field is
  ambiguous, not additive - the second would silently win." — Duplicate-tag rejection guards a
  silent-override hazard · [H10]

## tests_scripts/test_device_tomls.py

- **GEN.N183** DRIFT · `tests_scripts/test_device_tomls.py:3` — "Hand-implements the collision checks
  until Session 3's generator/validator exists." — The validator exists (buildgen/validate.py); this
  file keeps a second, hand-written subset of the same checks with the stale "until" rationale · [H10]
- **GEN.N184** ASSUME · `tests_scripts/test_device_tomls.py:373,383` — "Fact about the 6 real devices,
  not a schema requirement" — Pins that every real device wires fram_target on every wirable instance
  and all three warn_* signals · [H10]
- **GEN.N185** INVAR · `tests_scripts/test_device_tomls.py:428-436` — "Only device identity
  (name/hostname) may differ; everything else must be byte-for-byte identical." — klkizi/grkizi/schlafzi
  must be identical apart from name/hostname (hardcoded names) · related: PAR.T13 · [H10]
- **GEN.N186** ASSUME · `tests_scripts/test_device_tomls.py:575-577` — "this smoke suite instead checks
  the real devices' own convention (temperature_source always reads \"Temp\")" — Convention check
  narrower than the L.6.3 schema · [H10]
- **GEN.N187** LIMIT · `tests_scripts/test_device_tomls.py:835-848` — "only bmp3xx carries a TOML
  address field today" — Reserved-range sweep sees TOML addresses only; fixed-address drivers are
  checked via `buildgen.twin_wiring.FIXED_ADDRESSES` (itself a hand mirror of driver constants) ·
  related: GEN.T06 · [H10]

## tests_scripts/test_digital_twin_boot_contiguity.py

- **GEN.N188** LIMIT · `tests_scripts/test_digital_twin_boot_contiguity.py:246-252` — "setup_calls =
  len(re.findall(r\"^\\s*await \\w+\\.setup\\(\\)\\s*$\"" — Collect-count parity uses the same
  exact-shape `await X.setup()` regex as test_buildgen_generate.py · [H10]

## tests_scripts/test_generate_sensortask_modules.py

- **GEN.N189** MIRROR · `tests_scripts/test_generate_sensortask_modules.py:41-46` — "\"instances\" is
  main()'s addition on top of compute_twin_wiring()'s shape, an independent pre-construction
  driver-presence oracle" — Wiring-plan JSON carries an extra `instances` key only the pre-generation
  script adds; consumers (twin `configure_wiring()`) depend on it · related: GEN.T15 · [H10]

## SPECIFICATION.md Part A.2 (Architecture at a glance, 94-127)

- **GEN.N190** ASSUME · `SPECIFICATION.md:112-113` — "every real device — confirmed against all 6
  `devices/*.toml`, each declaring a `driver = \"fram\"` instance" — Count-dependent claim (6 TOMLs,
  each with FRAM); goes stale with a new device. · [H12]

## SPECIFICATION.md Part A.6 (Datasheets, 337-356)

- **GEN.N191** PLATFORM · `SPECIFICATION.md:347-351` — "UART TX on `pin % 4 == 0`, RX on `pin % 4 == 1`
  and the peripheral from `((pin + 4) & 8) >> 3`" — Pin-mux derived from pinned `machine_uart.c` macros;
  re-check on bump. · related: GEN.T07 · [H12]
- **GEN.N192** PLATFORM · `SPECIFICATION.md:351-352` — "p.8 lists GPIO23/24/25/29 as the pins the
  wireless chip takes" — Board datasheet fact feeding pin legality. · related: GEN.T07 · [H12]

## SPECIFICATION.md Part A.7 (wozi's construction order and dependency graph, 358-569)

- **GEN.N193** ASSUME · `SPECIFICATION.md:392-394` — "a device with none keeps the pre-WP1 order:
  `conn`/`ntp` first, `fram` wherever its own instance ordering puts it" — Fallback path when no
  `fram_target`; every real TOML sets it, so this path is fixture-only. · [H12]
- **GEN.N194** ASSUME · `SPECIFICATION.md:543-545` — "`buildgen` derives both from each device's own
  TOML rather than assuming wozi's answer applies everywhere (confirmed against `buildgen/codegen.py`)"
  — Claim of per-device derivation. · [H12]

## SPECIFICATION.md Part A.8 (REST API endpoint reference, 571-625)

- **GEN.N195** INVAR · `SPECIFICATION.md:592-595` — "generator-owned/fixed, never per-device, and
  reported live so a fleet operator can tell which build" — Build identity is hand-bumped versions +
  date only (no commit). · related: HW.T19 · [H12]

## SPECIFICATION.md Part B.14.2 / B.14.2.1 (`lwip_connection_counts`, 1215-1379)

- **GEN.N196** INVAR · `SPECIFICATION.md:1322-1323` — "`buildgen/validate.py` runs the N-connection half
  per device ... refuses a device whose `max_connections` the firmware's own pools cannot serve" —
  Enforced in buildgen. · related: GEN.T15 · [H12]

## SPECIFICATION.md Part B.15 (The three mypy passes, 1413-1473)

- **GEN.N197** LIMIT · `SPECIFICATION.md:1435-1437` — "`build/generated_src` is on `mypy_path` for the
  one static `import sensortask_dev` ... `typecheck.sh` generates it first." — Generated modules
  resolved (silently) but never reported. · covered-by: GEN.S17 · [H12]

## SPECIFICATION.md Part C.7.2 (Which failures may end a task, 1943-1973)

- **GEN.N198** MIRROR · `SPECIFICATION.md:1958-1965` — "`retry_s` (default 10 s) doubling ... up to
  `retry_max_s` (default 600 s) ... `ntp_retry_s`/`ntp_retry_max_s`, checked by buildgen" — Defaults and
  the 10 s tick mirrored between NTP code and buildgen validation (`_NTP_CHECK_TICK_S`). · related:
  GEN.T06 · [H12]
- **GEN.N199** MIRROR · `SPECIFICATION.md:1976-1979` — "`buildgen/validate.py`'s
  `_check_uart_link_buses()`, reading the thresholds out of `asy_uart_comm.py`); every other refusal
  needs code the generator never emits" — Build-time check reads src constants; "never emits" is an
  assumption. · related: UART.T05 · [H12]

## SPECIFICATION.md Part C.8 (Concurrency & locking model, 2016-2188)

- **GEN.N200** ASSUME · `SPECIFICATION.md:2181-2191` — "`wozi` wires `sgp40`+`bmp3xx` together on
  `i2c1`, and `dev` wires `scd30`+`sgp40`+`isl29125` together on `i2c1` ...
  `arzi`/`klkizi`/`grkizi`/`schlafzi` each wire `scd30` alone on `i2c0` and `sgp40` alone on `i2c1`" —
  Doc copy of TOML bus topology (Session 6.2 check); goes stale on TOML change. · related: HW.S12 ·
  [H12]

## SPECIFICATION.md Part C.14 / C.14.1 (Instance naming, 2380-2428)

- **GEN.N201** SETTLED · `SPECIFICATION.md:2394-2398` — "singleton services
  (WiFi/NTP/SystemService/Neopixel/NotificationCoordinator/FRAM/the DNS server/the webserver) are
  deliberately out of scope for the *naming* part" — Singletons never multi-instanced. · related:
  GEN.T13 · [H12]
- **GEN.N202** INVAR · `SPECIFICATION.md:2432-2436` — "Collision detection across a whole device's
  instance list is built in `buildgen/validate.py`" — Enforced by
  `_check_instance_name_collisions()`/`_check_instance_label_collisions()`. · [H12]

## SPECIFICATION.md Part C.14.2 (The `_WIRING` convention, 2430-2532)

- **GEN.N203** INVAR · `SPECIFICATION.md:2451-2454` — "Nothing the running firmware itself ever reads
  should become a real frozen-bytecode value just to serve the generator (SPECIFICATION.md Part L.5)" —
  Tag-as-comment rule. · related: GEN.T03 · [H12]
- **GEN.N204** ASSUME · `SPECIFICATION.md:2454-2456` — "converting it, plus `_VALUE_WIRING`, `_LIMITS`
  and the `TYPE_CHECKING` type aliases ... took 3,576 bytes out of `src/`'s frozen bytecode" — Dated
  single measurement. · [H12]
- **GEN.N205** INVAR · `SPECIFICATION.md:2456-2457` — "dropping any one of the five makes the tag fail
  the build loud rather than parse as \"no tag here\" (`tag_comments.py`)" — Enforced by buildgen
  parser. · covered-by: GEN.T03 · [H12]

## SPECIFICATION.md Part C.14.3 (Error-source and logger fan-in, 2534-2572)

- **GEN.N206** ASSUME · `SPECIFICATION.md:2573-2575` — "every real `devices/*.toml` compensates both off
  one `SCD30_Reader`" — Doc copy of TOML facts. · [H12]

## SPECIFICATION.md Part H.5.1 — Definitions-file autogeneration

- **GEN.N207** LIMIT · `SPECIFICATION.md:4428-4430` — "a best-effort, never-imported AST read of each
  driver's real `ConfigSchema`/`FieldSchema` constant (`buildgen/schema_ast.py`" — Schema inference is
  best-effort static evaluation. · related: GEN.S10 · [H13]
- **GEN.N208** INVAR · `SPECIFICATION.md:4426-4428` — "built on `buildgen/tag_comments.py`'s shared
  near-miss-enforcing scanner exactly like `@requires` — never a second, separately-tested detector" —
  One scanner for every tag family. · related: GEN.T03 · [H13]
- **GEN.N209** INVAR · `SPECIFICATION.md:4436-4440` — "`submitGroup=self` is a reserved sentinel ...
  used by scd30/sgp40/bmp3xx, the only drivers a device can carry more than one instance of" —
  Multi-instance set named in prose; ISL29125's status not stated (low). · related: GEN.T04 · [H13]
  ⟨quote not matched at the anchor⟩
- **GEN.N210** LIMIT · `SPECIFICATION.md:4442-4445` — "a quoted value may not contain a literal `\"` (no
  escaping), and every tag is a single physical line" — Deliberately minimal tag grammar. · related:
  GEN.T03 · [H13]
- **GEN.N211** MIRROR · `SPECIFICATION.md:4465-4469` — "`validateDefinitions()` rejects a `path` on
  anything but a `kind=readonly` field ... `buildgen/web_tag.py` enforces the identical rule at
  generation time" — Python↔JS duplicate validation of `path`. · related: GEN.T15 · [H13]
- **GEN.N212** MIRROR · `SPECIFICATION.md:4475-4478` — "bounded 0–100 ... checked at generation time in
  `buildgen/web_tag.py` and again in `js/definitions.js`'s `validateFieldHints()`" —
  `web_tag._MAX_DECIMALS` ↔ `validateFieldHints`. · covered-by: GEN.T15 · [H13]
- **GEN.N213** INVAR · `SPECIFICATION.md:4481-4482` — "A schema-declared sentinel special value must
  have a matching tag `special:<value>=\"<meaning>\"` or the build fails loud" — Enforced by the
  generator. · related: GEN.T09 · [H13]
- **GEN.N214** MIRROR · `SPECIFICATION.md:4491-4494` — "`_WARN_SIGNAL_WEB_CATALOG`, the same precedent
  `buildgen.codegen._KNOWN_SIGNALS` ... kept in sync by cross-reference/comment, not import" —
  Hand-mirrored catalog pair, comment-only sync. · covered-by: GEN.T06 · [H13]
- **GEN.N215** ASSUME · `SPECIFICATION.md:4496-4498` — "**Correctness proof**: `generate_definitions()`
  ... reproduces the existing hand-written `wozi.json`/`dev.json` exactly (order-insensitive)" —
  "Exactly" is order-insensitive only; generated field order differs. · covered-by: WEB.S13 · [H13]

## SPECIFICATION.md Part J (intro)

- **GEN.N216** PLATFORM · `SPECIFICATION.md:5172-5175` — "The jumper uses UART0 on GP0/GP1 and UART1 on
  GP8/GP9 ... GPIO24/25 and GPIO28/29 each have a half the wireless chip takes ... GPIO16/17 is left
  free because a BME688's BSEC coprocessor wants UART0 there" — Board pin-mux facts and a reservation
  for a future peripheral. · related: GEN.T07 · [H13]

## SPECIFICATION.md Part J.6 — Deployment parameters

- **GEN.N217** MIRROR · `SPECIFICATION.md:5549-5561 (sites buildgen/validate.py:246-276, src/asy_uart_comm.py:95, 260, 270)`
  — "`baud/10 × (poll_wait_ms + jitter)` ... `2 × poll_wait_ms + poll_idle_ms +` the measured worst-case
  GC pause" — Floor formulas duplicated in buildgen (`validate.py:247` "mirrored here rather than read")
  and the module. · covered-by: UART.T05 · [H13]

## SPECIFICATION.md Part K.3 — Wire into buildgen

- **GEN.N218** INVAR · `SPECIFICATION.md:5755-5757` — "confirm by actually running
  `buildgen/generate.py` against a fixture TOML ... not by inspection alone" — Review-only process step.
  · [H13]
- **GEN.N219** SETTLED · `SPECIFICATION.md:5759-5760` — "**`buildgen/buildspec.py`** — the one
  hand-maintained per-driver table (its own docstring says so; every other buildgen table is AST-derived
  from `src/`)" — Hand-maintenance settled (plan §2.3); "every other table AST-derived" conflicts with
  the plan's list of other hand catalogs (`_SENSOR_DRIVERS`, `_ERRCOUNT_CATALOG`, ...). · related:
  GEN.T06 · [H13]
- **GEN.N220** RISK · `SPECIFICATION.md:5764-5768` — "**Check the datasheet for a real address-select
  pin before deciding `ADDRESS_CAPABLE_DRIVERS` vs. `FIXED_ADDRESS_DRIVERS`** ... guessing this wrong
  lets a device TOML declare a meaningless `address` field that silently does nothing" — Silent
  misconfiguration risk; ISL29125 address hardwired (FN8424 p15). · related: GEN.T13 · [H13]
- **GEN.N221** ASSUME · `SPECIFICATION.md:5769-5775` — "Only add a `_OVERRIDES` entry if the driver
  genuinely can't follow that convention (today: `fram`, `neopixel`, `notification`, `uart_link`" —
  Dated inventory of overrides. · covered-by: GEN.T13 · [H13]
- **GEN.N222** INVAR · `SPECIFICATION.md:5779-5782` — "Every optional TOML field gets emitted only `if \"<field>\" in f:`
  ... never unconditionally" — Codegen convention, tested per field in `test_buildgen_generate.py`. ·
  related: GEN.T02 · [H13]
- **GEN.N223** RISK · `SPECIFICATION.md:5783-5785` — "add the driver to `_SENSOR_DRIVERS` ... Skipped,
  the driver silently never appears on the website with no error anywhere" — Hand catalog whose omission
  fails silently. · covered-by: GEN.T06 · [H13]
- **GEN.N224** INVAR · `SPECIFICATION.md:5786-5791` — "Add a case only if the driver needs a *real
  interrupt/GPIO line the twin's chip fake has to drive edges on* (today: `scd30`, `isl29125` — see
  `compute_twin_wiring()`'s own `if spec.driver in (\"scd30\", \"isl29125\")` branch)" — Hardcoded
  driver tuple in `twin_wiring.py`, another hand catalog. · related: GEN.T06, TWIN.T12 · [H13]
- **GEN.N225** MIRROR · `SPECIFICATION.md:5792-5794` — "`uart_link`'s `UART_ROLE` table, transcribed
  from the Pico W datasheet" — `buildgen/pico_gpio.py` ↔ Pico W datasheet. · related: GEN.T07 · [H13]

## SPECIFICATION.md Part K.4 — @web tags

- **GEN.N226** INVAR · `SPECIFICATION.md:5807-5811` — "Every tag family gets full accept/reject grammar
  test coverage ... extending a tag family's own grammar ... needs new tests in that same file" —
  Review-only test obligation. · related: GEN.T03 · [H13]

## SPECIFICATION.md Part K.6 — Tests, every tier

- **GEN.N227** INVAR · `SPECIFICATION.md:5865-5867` — "`test_device_tomls.py` — which real devices carry
  this driver (an explicit allow-list assertion ... never let a new instance land on a device by
  omission of a check)" — Allow-list rule per driver. · [H13]

## SPECIFICATION.md Part K.7 — devices/*.toml

- **GEN.N228** INVAR · `SPECIFICATION.md:5893-5898` — "Wiring facts ... must come from **real,
  bench-validated hardware**, never invented — cite where the fact came from in a TOML comment" —
  Review-only provenance rule. · related: GEN.T08 · [H13]

## SPECIFICATION.md Part K.10-K.11 — Verification and certification

- **GEN.N229** INVAR · `SPECIFICATION.md:5942-5945` — "**Actually generate all six real device TOMLs**
  ... inspect the output ... don't infer correctness from tests alone" — Manual review step; generated
  modules otherwise unlinted (GEN.S17). · related: GEN.T10 · [H13]

## SPECIFICATION.md Part L.1 — Device variants and acceptance criteria

- **GEN.N230** ASSUME · `SPECIFICATION.md:6009-6014` — "`klkizi`/`grkizi`/`schlafzi` (the three \"ArZi
  neu\" units — currently identical hardware ...) ... `wozi`/`dev` are the only two carrying a `bmp3xx`
  instance; every SCD30-carrying `i2c0` bus gets `timeout = 200000`" — Dated per-device inventory (true
  at 2a88cc8 per `devices/*.toml`); the 200000 timeout is a per-file convention. · related: GEN.T08,
  PAR.T13 · [H13]
- **GEN.N231** LIMIT · `SPECIFICATION.md:6016-6018` — "Two criteria define the scheme and must keep
  holding — they are the thing a change to `buildgen/` can most easily break without any test naming
  them" — Self-declared: the two acceptance criteria have no named guarding test. · related: GEN.T06,
  CI.T07 · [H13]
- **GEN.N232** DRIFT · `SPECIFICATION.md:6025-6032` — "**A new hardware combination of already-known
  drivers needs exactly one new file**, the device's own TOML" — Hardcoded six-device CI matrices,
  `KNOWN_DEVICES`, and per-device `tests/test_sensortask_<device>.py` wrappers each need an edit too. ·
  related: CI.T07, WEB.S22 · [H13]
- **GEN.N233** SETTLED · `SPECIFICATION.md:6034-6035` — "**Real hardware flashing is out of scope for
  this scheme**, and the watchdog stays fixed (hardcoded 8000 ms, uniform, never per-device)" — Uniform
  watchdog decision. · related: XCUT.S13 · [H13]

## SPECIFICATION.md Part L.2 — Core design decisions

- **GEN.N234** SETTLED · `SPECIFICATION.md:6040-6045` — "**Generation is build-time only; nothing
  generated is committed.** ... No static `src/sensortask_*.py` file exists" — Build design decision. ·
  related: XCUT.T14 · [H13]
- **GEN.N235** MIRROR · `SPECIFICATION.md:6055-6057` — "`[device].hostname` is capped at
  `network.hostname()`'s own 32 characters at build time, and `[device].hotspot_password` is held to
  WPA2-PSK's own 8-63" — buildgen bounds ↔ `asy_wifi_service` `_VAL_*` bounds. · covered-by: GEN.T15 ·
  [H13]
- **GEN.N236** INVAR · `SPECIFICATION.md:6064-6069` — "**Every real cross-instance link gets a
  TOML-visible `[instance.wiring]`/`[device.wiring]` field** — none stay hardcoded in `build_system()`"
  — Plan seed: codegen hardcodes `fram=` for device-level consumers and `conn.set_ext_led`. · related:
  GEN.S09 · [H13]
- **GEN.N237** INVAR · `SPECIFICATION.md:6074-6078` — "**No getters and no callback functions in
  generated code.**" — Generated-code convention; `signal_sink` resolves to a bound method
  (`mode="attr"`, 6225-6227), arguably a callback. · related: GEN.T04 · [H13]
- **GEN.N238** INVAR · `SPECIFICATION.md:6090-6093` — "no hardcoded pins anywhere in generated or
  hand-written driver-wiring code" — Scope excludes device scripts (plan HW.S18: ~20 scripts hardcode
  pins). · related: HW.T08 · [H13]
- **GEN.N239** INVAR · `SPECIFICATION.md:6094-6097` — "Frozen-module selection is dependency-driven ...
  Dynamic imports are disallowed project-wide, which is what makes the closure sound." — Soundness
  depends on F.1's rule. · covered-by: GEN.T05 · [H13]

## SPECIFICATION.md Part L.3 — Device TOML schema

- **GEN.N240** INVAR · `SPECIFICATION.md:6113-6121` — "Their per-device-tunable knobs ... live directly
  in `[device]`, **required, not defaulted** ... `max_connections`/`backlog` ...
  `ntp_retry_s`/`ntp_retry_max_s` ... buildgen checks the effective value either way" —
  Required-vs-defaulted split; "checks the effective value either way" is a claim to verify. · related:
  GEN.T01 · [H13]
- **GEN.N241** INVAR · `SPECIFICATION.md:6246-6251` — "resolves against the TOML's own
  `driver`+`name_ext` identity — **never** against `instance_name()`/each driver's own `_NAME` constant
  ... `_NAME` is `\"NOTIFY\"`, not `\"NOTIFICATION\"`" — Two naming spaces that must not be mixed. ·
  related: GEN.T04 · [H13]
- **GEN.N242** LIMIT · `SPECIFICATION.md:6253-6254` — "`tests_scripts/test_device_tomls.py` is a minimal
  shape/collision smoke-test suite run directly against the six real files" — Deliberately minimal
  independent check. · [H13]

## SPECIFICATION.md Part L.4 — Generator pipeline

- **GEN.N243** INVAR · `SPECIFICATION.md:6258` — "`buildgen/` is a real top-level CPython package, never
  imported by `src/`" — Package boundary. · [H13]
- **GEN.N244** INVAR · `SPECIFICATION.md:6273-6276` — "every failure is a `buildgen.errors.BuildError`
  naming the device, instance and field responsible" — Contract; plan seeds show raw
  `KeyError`/`AttributeError`/`ValueError` escapes. · covered-by: GEN.T01, GEN.T12 · [H13]
- **GEN.N245** LIMIT · `SPECIFICATION.md:6277-6279` — "each signal's threshold default/range and flash
  colour is a fixed, generator-owned catalog (`buildgen.codegen._KNOWN_SIGNALS`) ... no per-device
  override for them today" — No per-device tuning of warning signals. · related: GEN.T06 · [H13]
- **GEN.N246** MIRROR · `SPECIFICATION.md:6291-6296` — "scd30/sgp40's fixed hardware address
  (`FIXED_ADDRESSES`, matching `src/`'s own hardcoded defaults) and FRAM's real RDID reply bytes
  (`digital_twin/machine.py`'s `_FRAM_RDID_BY_MAX_SIZE`, keyed by size as the best available proxy)" —
  Twin-side hand tables mirroring `src/` defaults; `buildgen/twin_wiring.py:12` also lists `isl29125`,
  so the doc's list is stale (low). · covered-by: GEN.T06 · [H13]

## SPECIFICATION.md Part L.5 — Build/generator script quality bar

- **GEN.N247** INVAR · `SPECIFICATION.md:6322-6326` — "**Detect and react to every error class that
  would make a real build impossible**" — Build-tool contract (abort, not degrade). · covered-by:
  GEN.T01 · [H13]
- **GEN.N248** INVAR · `SPECIFICATION.md:6327-6348` — "**Global-resource-collision checks are their own
  error class and must not be skipped.** ... Every one of these must produce a specific, human-readable
  error naming the two colliding declarations" — GPIO, per-bus address, instance identity (two naming
  spaces), bus-id collisions. · related: GEN.T12 · [H13]
- **GEN.N249** INVAR · `SPECIFICATION.md:6352-6359` — "**Driver-declared bus requirements are enforced
  via a `# @requires` comment tag, never a real Python variable**" — Tag parsed as text, never imported.
  · related: GEN.T03 · [H13]
- **GEN.N250** SETTLED · `SPECIFICATION.md:6360-6364` — "**Every driver-declared fact the running
  firmware never reads is a comment tag, not a Python value** (project owner's ruling, 2026-09-10) ...
  The one exception is a `_Default<Field>` class" — Owner ruling. · related: DOC.T14 · [H13]
- **GEN.N251** INVAR · `SPECIFICATION.md:6365-6372` — "a tag that is present, or close to present with a
  typo, must be verified correct in every dimension ... or fail the build loud, never be silently
  treated as \"no tag here.\"" — Standing near-miss rule; plan notes column-0 comments inside function
  bodies are treated as module level. · related: GEN.T03, GEN.S10 · [H13]
- **GEN.N252** ASSUME · `SPECIFICATION.md:6413-6416` — "a driver signature change once silently broke
  two `tests_hardware/device_scripts/` call sites for a full day, undetected because nothing in that
  scope was checked at all" — Motivating incident; device_scripts are now in the main mypy pass
  (CLAUDE.md). · [H13]
- **GEN.N253** INVAR · `SPECIFICATION.md:6417-6419` — "**Never produce a corrupted or partial build.**
  ... no partial `build/<device>/` output left behind" — Atomic-build contract; not stated to be tested.
  · related: GEN.T16 · [H13]
- **GEN.N254** INVAR · `SPECIFICATION.md:6420-6423` — "not a raw traceback, not a silent wrong-default
  fallback" — Plan seeds record raw `KeyError`/`AttributeError`/`ValueError`. · covered-by: GEN.T01 ·
  [H13]

## SPECIFICATION.md Part L.6.1-L.6.2 — Wiring defaults

- **GEN.N255** SETTLED · `SPECIFICATION.md:6444-6446` — "Both are real, intentional device shapes rather
  than configuration errors, so the fix is a TOML-authored fallback the driver constructs itself — never
  a relaxed validator." — Design decision for absent producers. · [H13]
- **GEN.N256** INVAR · `SPECIFICATION.md:6450-6451` — "**Opt-in, never implicit**: a wiring field is
  never silently defaulted just because it is absent" — Explicit `{default = true, ...}` required. ·
  related: GEN.T01 · [H13]
- **GEN.N257** INVAR · `SPECIFICATION.md:6456-6458` — "That signature *is* the schema for the
  sub-table's allowed and required keys, never hand-duplicated in `buildgen/buildspec.py`" — AST-derived
  schema; plan notes `defaults.default_init_params` ignores keyword-only args. · related: GEN.S10 ·
  [H13]

## SPECIFICATION.md Part L.6.3 — Per-value measurement wiring

- **GEN.N258** INVAR · `SPECIFICATION.md:6467-6471` — "resolved at build time by checking that
  `source`'s `get_data()` result exposes an attribute named `field`" — Plan seed: `field` existence is
  never checked. · covered-by: GEN.S06 · [H13]
- **GEN.N259** LIMIT · `SPECIFICATION.md:6482-6484` — "Name-matching is the whole mechanism — there is
  no separate property or unit tag system" — No unit/semantic check: any same-named field wires
  regardless of unit. · [H13]
- **GEN.N260** INVAR · `SPECIFICATION.md:6475-6477` — "both self-contained, with no cross-module import,
  so a device with `sgp40` but no `scd30` never pulls `asy_scd30_driver` into its frozen-module set" —
  Default providers must stay import-free. · related: GEN.T05 · [H13]

## SPECIFICATION.md Part L.6.5 — Pico W GPIO legality

- **GEN.N261** PLATFORM · `SPECIFICATION.md:6517-6530` — "`buildgen/pico_gpio.py` hardcodes the Pico W's
  real, fixed GPIO→peripheral table ... **GP22/GP28** have no I2C or SPI function at all. **GP23–25/29**
  are reserved" — Board-specific table transcribed from datasheet Figure 2 p.4; no board
  parameterization. · covered-by: GEN.T07 · [H13]
- **GEN.N262** MIRROR · `SPECIFICATION.md:6517-6519` — "transcribed from `datasheets/pico w/RP-008312-DS-2-pico-w-datasheet.pdf`
  Figure 2 (p.4)" — Code table ↔ datasheet figure. · covered-by: GEN.T07 · [H13]

## SPECIFICATION.md Part L.6.6 — Validation coverage

- **GEN.N263** INVAR · `SPECIFICATION.md:6541-6553` — "Every check raises `buildgen.errors.BuildError`
  naming the device, instance and field responsible — never a generic failure, a raw traceback or a
  silent partial build" — Coverage claim contested by plan seeds GEN.S03/S04/S10. · covered-by: GEN.T01
  · [H13]
- **GEN.N264** LIMIT · `SPECIFICATION.md:6555-6561` — "**Known limitation**: `buildgen/buildspec.py`'s
  per-driver TOML-field schema ... is still hand-maintained ... BACKLOG.md's \"Deferred\" section" —
  Deferred work, settled as hand-maintained for now. · related: GEN.T06 · [H13]

## SPECIFICATION.md Part L.7 — Product versioning

- **GEN.N265** SETTLED · `SPECIFICATION.md:6578-6583` — "**Single source of truth:
  `buildgen/version.py`** ... No bump mechanism exists: one clear, documented place to change the two
  constants, no automation" — Manual bumping by design. · related: GEN.T14 · [H13]

## SPECIFICATION.md Part M.1.1 — Settled requirements (owner's list)

- **GEN.N266** SETTLED · `SPECIFICATION.md:6642-6643` — "18. **Scope is the `dev` variant only.**
  `devices/wozi.toml` declares no `isl29125` instance and must not gain one." — Enforced by
  `test_isl29125_only_present_on_dev` (K.6). · [H13]

## CLAUDE.md

- **GEN.N267** INVAR · `CLAUDE.md:147-155` — "resolved via `buildgen/driver_registry.py`'s `_OVERRIDES`
  table ... not a singleton (`SINGLETON_SERVICE_DRIVERS` excludes it)" — Matches
  driver_registry.py:16-21, 31. · covered-by: GEN.T13 · [H14]

## BACKLOG.md

- **GEN.N268** SETTLED · `BACKLOG.md:651-657` — "Owner decision, 2026-09-18: it stays hand-maintained
  ... don't re-propose it." — `buildspec.py` per-driver schema; same for `definitions.py`
  `status`/`errcount` sections (owner 2026-09-24). · covered-by: GEN.T06 · [H15]
- **GEN.N269** INVAR · `BACKLOG.md:668-675` — "validate.py now refuses a hostname longer than
  network.hostname()'s 32-character cap at build time" — Else ConfigManager answers `None` to every
  read; runtime `_with_default()` falls back. Silicon proof of substitution path still PARTIAL (queue
  N2). · related: GEN.T15, NET.T07 · [H15]
- **GEN.N270** SETTLED · `BACKLOG.md:864-865` — "bench rig only, not bugs to fix" — `dev` config quirks.
  · covered-by: plan §2.2 ("dev bench quirks" row) · [H15]

## Commit messages (chronological)

- **GEN.N271** INVAR · `commit 1fef17a` — "GPIO23/24/25/29 are wired on-board to the CYW43439 wireless
  chip and must not be used as tx_pin/rx_pin ... not enforced at runtime" — Runtime driver does not
  refuse wireless-reserved pins; build-time check exists. · status: enforced at build time
  (buildgen/pico_gpio.py:5 WIRELESS_RESERVED_GPIOS) | - · [H17]
- **GEN.N272** TODO · `commit 871333e / ea225a6` — "its wiring must derive FRAM-chunk allocation and
  sensor-specific bus parameters from each variant's actual module set ... its own emitted tests must
  look up each sensor's actual bus dynamically" — Per-variant generator requirements. · status: done
  (buildgen, PRs #59-#61, #73) | - · [H17]
- **GEN.N273** ASSUME · `commit 43364bc / beb6b2d` — "klkizi/grkizi/schlafzi share byte-for-byte
  identical wiring (only device.name/hostname differ) per modules/sensortask-neu.py" — Three field
  devices' TOMLs derived from one legacy file (the "3× neu" units); wiring never checked against
  physical units. · status: by construction; physical verification impossible by rule (only dev is
  flashed) (low) | related: PAR.T*, GEN.T* · [H17]
- **GEN.N274** TODO · `commit d7145e3 / 8e6031a / 95c50c4 / ec537a6` — "an all-absent [bus.*] table is
  unconditionally rejected even though it's a logically valid device shape, and bus pin declarations are
  never checked against the hardware's fixed per-GPIO peripheral capability ... hotspot_password has no
  type check, no numeric field has a range check, bmp3xx address isn't set-checked, bus id port-suffix
  isn't validated, GPIO range isn't validated ... resolved_name ... and instance_label ... two separate
  uniqueness spaces" — buildgen validation gap list (the §8 [FIX]/[TEST]/[DECIDE] catalog in a
  since-retired planning doc). · status: largely done in later buildgen work (buildgen/pico_gpio.py
  pin-legality, `_LIMITS`, address sets per SPECIFICATION Part L.6); per-item closure not verified here
  — see GEN area (low) | related: GEN.T* · [H17]
- **GEN.N275** ASSUME · `commit b272eea` — "GP23/24/25/29 are never named explicitly anywhere - the
  claim is a correct inference from Figure 2's omission" — Wireless-reserved GPIO set
  (buildgen/pico_gpio.py:5) rests on an inference from the Pico W datasheet, not an explicit statement
  (a later header comment cites datasheet p.8). · tracked: buildgen/pico_gpio.py:5,36-39;
  src/asy_uart_driver.py:4-5 | related: GEN.T* · [H17]
- **GEN.N276** LIMIT · `commit 6817042` — "Deliberately not tagged: bmp3xx (... any bound would be
  invented ...) and the FRAM's 40 MHz SPI ceiling (SPI bus tables carry no frequency field at all ...)"
  — No build-time check of SPI clock vs FRAM ceiling (SPI clock fixed in driver). · status: by design
  (low) | related: GEN.T*, BUS.T* · [H17]
- **GEN.N277** NOTE(OUT-OF-SCOPE) · `commit ffc17ae` — "No bump mechanism is built (deliberately out of
  scope ...)" — Versions bumped by hand. · tracked: buildgen/version.py:2 ("no automation exists or is
  planned") | - · [H17]
- **GEN.N278** NOTE(TRACKED) · `commit bb5354c` — "every other open item (buildspec.py's hand-maintained
  schema, hostname/hotspot_password not yet wired, bus_topology.py's dead-code status) was already
  tracked in BACKLOG.md" — Buildgen open items. · tracked: BACKLOG (buildspec settled; bus_topology
  deleted) | - · [H17]
- **GEN.N279** NOTE(NON-CLAIM) · `commit 7ef7fb8 / ec5c0b9` — "an explicit non-claim of
  mechanically-verified 100% coverage"; "digital_twin/machine.py's analogous _build_i2c_chip() fallback"
  gap found but not fixed — buildgen abort-path coverage is spot-checked, not proven complete. · status:
  _build_i2c_chip gap done-in 7fe0e17; completeness claim remains a non-claim (no mechanical gate) |
  related: GEN.T* · [H17]
- **GEN.N280** NOTE(FLAG) · `commit 038228a` — "BACKLOG item 31 ... the website's errcount catalog is
  keyed by driver KIND, while the API publishes one key per logger INSTANCE"; pinned in
  _KNOWN_CATALOG_DRIFT — Multi-instance devices would render wrong errcount rows. · status: done
  (_KNOWN_CATALOG_DRIFT removed; git -S shows b0f755c/edf11c2/86fb067) | - · [H17]
