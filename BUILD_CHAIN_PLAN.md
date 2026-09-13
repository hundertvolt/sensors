# Automated Build Chain — Plan

Shared plan for making `src/`, the website (`html/`+`js/`), the build script chain, and the test
chain fully device-generic — every device-specific fact (hardware present, pin/bus assignments,
included software modules, how measurement values are shared between modules) lives in exactly one
TOML config file per device variant. Every session spun off `claude/automated-build-chain-nuzumw`
works against this doc. This branch merges into `main` only once every session has landed and the
whole chain is verified end-to-end — that merge is the project owner's own call, not implied by
anything below.

## Status

All eight planned sessions (below) are shipped. The device TOML schema and `_WIRING`/
`instance_name()` mechanism (Session 1) plus the 6 real `devices/*.toml` files (Session 2) exist;
`buildgen/` (Session 3) generates a device's firmware entry module, computes its frozen-module set,
and validates its TOML against a full fail-loud error catalog; `buildgen/definitions.py` (Session 4)
generates a device's website `definitions.json`; the digital twin (Session 5) boots any device from a
plain, JSON-serializable wiring plan; the real build chain and CI matrix (Session 6/6.2/6.3) wire all
of the above together, delete the last hand-written `sensortask_wozi.py`/`sensortask_dev.py` files,
and generalize the digital-twin test suite to run against a freshly-generated module for all 6 real
devices; firmware/website versioning (Session 7) ship as independent constants on `GET /system`.

**Acceptance criteria: both hold.**
1. A new driver needs exactly one association — its common name resolved to its class via the
   mandatory `asy_<name>_driver.py` naming convention — with schema, frozen-module inclusion,
   REST/config naming, website fields, and wiring validation all derived automatically. True of
   every driver in `src/` today. **Named exception**: a genuinely new chip type still needs a
   hand-written digital-twin chip fake — inherently bespoke, outside "the auto build" in the
   firmware/website-generation sense this criterion is about.
2. A new hardware combination of already-known drivers needs exactly one new file — the device's
   TOML — with the full firmware+website build following automatically. Proven, not assumed, by two
   synthetic fixtures (`tests_scripts/buildgen_fixtures/novel_combo.toml`,
   `multi_instance.toml`) exercising layouts none of the 6 real devices use, passing the full
   pipeline since Session 3.

**Known open gaps** — tracked in BACKLOG.md, not duplicated here: `[device].name`/`hostname`/
`hotspot_password` are schema-validated but not wired into any generated boot path (every device
actually boots as `"SensorNode"`/`"12345678"`); `wozi`/`dev`'s hand-written `html/definitions/*.json`
still aren't retired in favor of generated output (blocks `js/app.js`'s `?device=` switch from
listing all 6 devices); `tests_hardware/bus_topology.py` is a dead, unenforced duplicate of two real
devices' wiring facts (BACKLOG.md item 20); `buildgen/buildspec.py`'s per-driver schema is still
hand-maintained (BACKLOG.md's "Deferred" section); SPECIFICATION.md Part H.5.1's `dispatch: true`
claim doesn't match two real fields in `wozi.json`/`dev.json` (BACKLOG.md item 21).

## Target device variants

Six: `dev` (bench rig only, never physically absent from testing — see CLAUDE.md), `wozi`
(exemplary/base variant, never physically flashed), `arzi` (distinct wiring from the "neu" family),
and `klkizi`/`grkizi`/`schlafzi` (the three "ArZi neu" units — currently identical hardware to each
other, but each gets its own independent TOML file since future hardware divergence is expected).

## Core design decisions

- **Config format**: TOML (matches `toolchain/versions.toml`'s existing precedent).
- **Generation is build-time only, nothing committed.** `build/<device>/{py,html,frozen,firmware}`
  is a single gitignored root; cleanup is `rm -rf build/`. CI regenerates and tests every variant
  (including a digital-twin boot) on every push.
- **Naming**: `SensorStation<Name>` is the base stub — default hostname, website display identity.
  The hotspot SSID is literally the `Hostname` config field's value. Hotspot password is a
  per-device TOML field defaulting to the existing hardcoded `"12345678"`.
- **Cross-instance wiring is fully static, resolved at generation time, never at runtime.** No
  runtime registry/bus. Each driver declares a `# @wiring` comment tag
  (`toml_field, required_driver_class, target, required, mode` — see
  BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md) naming which TOML field supplies a source instance
  and what class it must be. The generator resolves each reference to the actual constructed Python
  object and passes it directly into the consumer's constructor — an instance either is the expected
  class or it isn't, checked directly.
- **Every real cross-instance link gets a TOML-visible `[instance.wiring]`/`[device.wiring]`
  field** — none stay hardcoded in `build_system()`. Covers `sgp40.temperature_source`/
  `.humidity_source` (per-value wiring, BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md),
  `notification.signal_sink`/`warn_co2`/`warn_voc`/`warn_hum`, `fram_target` on every driver/service
  with an optional `fram=`/`fram_storage=` argument, and `device.wiring.led_target` for WiFi's
  `conn.set_ext_led(pixel)`. Each field is individually optional — absence disables that specific
  link. **Excluded**: links between two mandatory-infrastructure modules (both endpoints always
  exist unconditionally), and `WebserverService`'s `sensors=`/`settings=`/`maintenance_sensors=`/
  `is_hotspot_active=` arguments, which enumerate whichever instances a device's TOML already
  declares rather than naming one specific instance.
- **No getters, no callback functions in generated code.** A consumer holds a direct reference to
  the producer's existing concurrency-safe value holder (SPECIFICATION.md Part G's "locked state"
  primitive) and reads `.value` directly when needed. N-to-1 fan-in (error sources feeding
  `SystemService`, threshold-notifier sources feeding the Neopixel driver) collapses the same way:
  the aggregator holds a plain list of instances and reads each one directly.
- **Two ordering hazards, both handled, neither by hand:**
  1. *Object existence*: a consumer's constructor call references the producer's Python object
     directly, so the producer must be constructed first. `buildgen.graph.build_construction_order()`
     topologically sorts instances by wiring dependency and rejects a cycle as a build-time error.
  2. *Live data availability*: independent async tasks mean a consumer's first read can happen
     before the producer's first real measurement completes. Every producer's locked-value holder
     has a safe, defined initial value at construction; every consumer tolerates that "not yet
     measured" state as normal.
- **Instance naming**: every optional module gets an optional name-extension field, default empty
  string. REST paths, config filenames, and FRAM-backed error-log/errcount keys all incorporate it
  uniformly: `/sensors/scd30` by default, `/sensors/scd30_fan_pressure` when named. The generator
  errors on a naming collision when no disambiguating extension was given.
- **Bus/pin config**: every I2C/SPI bus pin, IRQ pin, CS pin, Neopixel pin, etc. is defined in the
  device's TOML — no hardcoded pins anywhere in generated or hand-written driver-wiring code. A
  device address field only exists for chips with a logically-selectable address; hardwired-address
  chips get no address field at all.
- **Frozen-module selection is dependency-driven**: the generator seeds from each device's declared
  driver list plus a fixed always-included core set, then takes the transitive closure of real
  (never dynamic — dynamic imports are disallowed project-wide) `import`/`from...import` statements,
  AST-scanned post-`TYPE_CHECKING`-stripping.
- **Testing**: generic driver/service logic is tested exactly once; only the device-specific slice
  (generated wiring module, generated website definitions, digital-twin boot of that config) runs
  once per device in CI. Tests are generic bodies driven by each device's TOML/generated module,
  never hand-written or generated per-variant test files.
- **Watchdog stays fixed** (hardcoded 8000ms, uniform, never per-device).
- **Real hardware flashing is out of scope for this entire initiative.**
- **Build-time tooling gets a fundamentally different error-handling contract than the runtime code
  it emits** — detect every error that would make a build impossible and abort loudly rather than
  degrade. Full requirement: "Build/generator script quality bar" below.

## Device TOML schema

Two top-level shapes: a single `[device]` table (identity/network facts, plus mandatory-infra tuning
and wiring) and a uniform `[[instance]]` array of tables. **The `[[instance]]` array models optional
modules only** — driver-level sensors, plus singleton services that vary or could someday be absent
per device: FRAM, Neopixel, NotificationCoordinator.

**WiFi, NTP, and SystemService are mandatory infrastructure and are never `[[instance]]`
entries** — every buildable device has all three unconditionally. Their own per-device-tunable knobs
(WiFi's `conn_fail_to_hotspot`/`hotspot_time_min`; NTP/SystemService have none) live directly in
`[device]`, **required, not defaulted** — a device TOML missing either is a build-time error. Their
crosslinks to optional instances live in `[device.wiring]` (`led_target`/`fram_target`, both
optional). The webserver is also unconditional and never modeled as an instance — its constructor
takes no independent per-device facts, only references to whichever other instances the TOML already
declares.

```toml
# example-device.toml - illustrative shape only; the 6 real files are devices/*.toml.

[device]
name = "Wozi"                              # feeds hostname = "SensorStation<name>"
hostname = "SensorStationWozi"             # also the hotspot AP's own SSID
hotspot_password = "12345678"              # accepted-risk default (CLAUDE.md)
conn_fail_to_hotspot = 5                   # mandatory-infra tuning, required
hotspot_time_min = 8

[device.wiring]
led_target = "neopixel"                    # optional; WiFi status LED
fram_target = "fram"                       # optional; SystemService's own error log

[bus.i2c0]
scl_pin = 13
sda_pin = 12
frequency = 50000
timeout = 200000                           # SCD30 clock-stretch headroom

[bus.i2c1]
scl_pin = 19
sda_pin = 18
frequency = 50000

[bus.spi0]
sck_pin = 2
mosi_pin = 3
miso_pin = 4

# --- sensor drivers (SensorReader/SensorReaderConfig subclasses - can repeat) -------------------

[[instance]]
driver = "scd30"                           # resolved to its class via naming convention, not a
name_ext = ""                              # lookup table (SPECIFICATION.md Part C.5)
bus = "i2c0"
irq_pin = 8
trigger_sec = 3

[instance.wiring]
fram_target = "fram"                       # optional

[[instance]]
driver = "sgp40"
name_ext = ""
bus = "i2c1"

[instance.wiring]
fram_target = "fram"                       # optional

# Per-value measurement wiring (BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md), each independently
# required (or explicitly defaulted via {default = true, ...}).
[instance.wiring.temperature_source]
source = "scd30"
field = "Temp"

[instance.wiring.humidity_source]
source = "scd30"
field = "Hum"

[[instance]]
driver = "bmp3xx"
name_ext = ""
bus = "i2c1"
address = 0x77                             # only chips with a real address-select pin get this

[instance.wiring]
fram_target = "fram"

# A second SCD30 on a different bus - name_ext disambiguates every derived name at once.
[[instance]]
driver = "scd30"
name_ext = "fan_pressure"
bus = "i2c1"
irq_pin = 9
trigger_sec = 3

# --- optional singleton services -----------------------------------------------------------------

[[instance]]
driver = "fram"
bus = "spi0"
cs_pin = 1
max_size = 0x2000                          # per-chip fact, varies per device

[[instance]]
driver = "neopixel"
pin = 15

[instance.wiring]
fram_target = "fram"

[[instance]]
driver = "notification"

[instance.wiring]
signal_sink = "neopixel"                   # required; defaultable, see BUILDGEN_WIRING_...md
fram_target = "fram"

# Per-signal getters - each optional; absence disables that specific warning signal.
[instance.wiring.warn_co2]
source = "scd30"
field = "CO2"

[instance.wiring.warn_voc]
source = "sgp40"
field = "VOC"

[instance.wiring.warn_hum]
source = "scd30"
field = "Hum"
```

**`_WIRING`'s final shape** (a `# @wiring` comment tag, not a Python tuple — see
BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md): `(toml_field_name, required_driver_class, target,
required, mode)`, where `mode` (`"kwarg"`/`"attr"`/`"setter"`) says how the resolved producer reaches
the consumer. `signal_sink` uses `mode="attr"`: the generator resolves it to `pixel.request_signal`
(the bound method `NotificationCoordinator.__init__`'s `request_signal_cb` parameter wants), not the
`NeopixelDriver` instance itself. `led_target` uses `mode="setter"`: `conn.set_ext_led(pixel)` is
emitted once, after both already exist.

**Wiring identity**: a wiring reference (`temperature_source`, `signal_sink`, `fram_target`,
`led_target`, every `[instance.wiring.<name>]`/`[device.wiring]` field) resolves against the TOML's
own `driver`+`name_ext` identity — **never** against `instance_name()`/each driver's own `_NAME`
constant, which is a different naming space serving REST/config-key identity instead (confirmed
`asy_notification_service.py`'s `_NAME` is `"NOTIFY"`, not `"NOTIFICATION"` — a generator matching
against `instance_name()` output would silently fail to resolve this case).

**The 6 real device TOML files** live at `devices/<device>.toml`. `device.name` values are
`Wozi`/`Dev`/`Arzi`/`Klkizi`/`Grkizi`/`Schlafzi`. `wozi`/`dev` are the only two with a `bmp3xx`
instance; `klkizi`/`grkizi`/`schlafzi` share byte-for-byte identical wiring (only `device.name`/
`hostname` differ). Every SCD30-carrying `i2c0` bus gets `timeout = 200000` clock-stretch headroom.
A minimal shape/collision smoke-test suite (`tests_scripts/test_device_tomls.py`) checks these 6
files directly, independent of `buildgen`'s own validator.

## Session breakdown (dependency-ordered)

1. **Wiring mechanism + device TOML schema design** (`src/`) — the wiring convention; instance
   naming across REST/config/error-log; the shared base class(es) for N-to-1 fan-in collection; the
   locked-value primitive as the wiring holder, with every producer defaulting safely pre-measurement.
2. **The 6 real device TOML files**, built from the wiring facts in `src/sensortask_wozi.py`,
   `src/sensortask_dev.py`, `modules/sensortask-arzi.py`, `modules/sensortask-neu.py`.
3. **Python generator** (`buildgen/`, a top-level CPython package, never imported by `src/`).
   `buildgen.generate.generate_device(toml_path, src_dir, ext_dir)` runs the full pipeline
   (`buildgen.validate.build_model()` → `buildgen.graph.build_construction_order()` →
   `buildgen.codegen.generate_module_source()`/`generate_boot_entry_source()`) and returns the
   generated module + boot-entry source, plus `buildgen.frozen_modules.compute_frozen_modules()`'s
   module set. Concretely:
   - **`driver` → class**: `buildgen.driver_registry.resolve_driver()` AST-parses (never imports)
     `asy_<name>_driver.py` for a `SensorReader`/`SensorReaderConfig` subclass; a fallback table
     covers `fram`/`neopixel`/`notification`, the one named exception the acceptance criteria itself
     allows.
   - **Global resource-collision validation**: `buildgen.validate.build_model()` — schema shape,
     global GPIO exclusivity, per-bus address exclusivity, instance-name/instance-label collision,
     bus-id collision, every wiring-reference/required-field check. Every failure is a
     `buildgen.errors.BuildError` naming the device/instance/field responsible.
   - **`# @requires bus.<field><op><value>`**: driver-declared bus requirements
     (`asy_scd30_driver.py`'s clock-stretch/frequency ceiling, `asy_sgp40_driver.py`'s frequency
     ceiling) — see "Build/generator script quality bar" below.
   - **Wiring defaults, per-value measurement wiring, `# @limits`, pin legality**: see
     BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md — the durable design record for all of `buildgen`'s
     validation mechanisms beyond the base wiring/construction-order pipeline.
   - **Notification signal catalog**: each signal's threshold default/range and flash color is a
     fixed, generator-owned catalog (`buildgen.codegen._KNOWN_SIGNALS`) — every real device uses
     identical values with no per-device override in the schema today.
   - **Frozen-module selection**: `buildgen.frozen_modules.compute_frozen_modules()` — AST-scanned
     transitive import closure, seeded from a fixed core set plus each device's declared driver
     modules.
   - **Mandatory synthetic fixtures**: `tests_scripts/buildgen_fixtures/novel_combo.toml` (two
     `SCD30`s, `SGP40` taking temperature from one and humidity from the other, `BMP3xx` at the
     alternate address, `Notification` wired to only one `warn_*` signal) and `multi_instance.toml`
     (2× scd30 + 2× sgp40 at once, a cross-driver-type value reference, an explicit
     `{default = true, ...}` constant) — pin/bus/wiring layouts none of the 6 real devices use,
     proving the generator's full generality.
   - **Correctness proof depth**: generated output is proven syntactically valid Python
     (`ast.parse()`) matching the documented construction-order/wiring shape
     (`tests_scripts/test_buildgen_generate.py`) — not executed under the real MicroPython
     interpreter (Session 5/6 close that gap).
   Test coverage: `tests_scripts/test_buildgen_{driver_registry,wiring,requires_tag,frozen_modules,
   graph,validate,generate}.py`.
4. **Website `definitions.json` generator.** `# @web <Field> section=<key> submitGroup=<key|self>
   label="..." [unit=...] [description="..."] [kind=...] [onLabel=...] [offLabel=...] [mask=true]
   [dispatch=true] [defaultValue=...] [special:<value>="<meaning>"]...` and `# @web-group
   section=<key> submitGroup=<key|self> label="..." [submit=true] [submitLabel=...]` comment tags
   (`buildgen/web_tag.py`, built on `buildgen/tag_comments.py`'s shared scanner), plus
   `buildgen/schema_ast.py` (AST-evaluates a driver's real `ConfigSchema`/`FieldSchema` constants to
   infer most per-field metadata automatically — a tag only supplies what the schema tuple
   structurally can't: label, unit, description, an explicit `kind=` override, `special:` labels).
   `submitGroup=self` is a reserved sentinel meaning "this TOML instance's own resolved name," used
   by scd30/sgp40/bmp3xx (multi-instance-capable); every other group uses a literal key. Fixed,
   non-driver-schema UI facts (`SystemCmd`/`PauseTime`/`lightCmdLED`/`ResetErrors`, the Status
   section's live-readonly field lists, the six-REST-endpoint section skeleton) are generator-owned
   catalogs in `buildgen/definitions.py`, not tag-derived — the same precedent
   `buildgen.codegen._KNOWN_SIGNALS` already set. Full grammar/architecture:
   SPECIFICATION.md Part H.5.1.
   `generate_definitions(model, src_dir)` takes an already-validated `DeviceModel`, scans each
   relevant instance's/mandatory-infra file's tags, and assembles the full `definitions.json`-shaped
   dict, keyed by each instance's own `resolved_name` so a multi-instance device gets distinct,
   correctly-labeled cards. Seven `src/` files carry real tags: `asy_scd30_driver.py`,
   `asy_sgp40_driver.py`, `asy_bmp3xx_driver.py`, `asy_wifi_service.py`, `asy_ntp_client.py`,
   `system_service.py`, `asy_notification_service.py`. Proof: `generate_definitions()` run against
   `devices/wozi.toml`/`dev.toml` produces output structurally identical to the pre-existing
   hand-written `html/definitions/wozi.json`/`dev.json`; all 6 real devices plus both synthetic
   fixtures pass a `js/definitions.js`-`validateDefinitions()`-equivalent shape check
   (`tests_scripts/test_buildgen_definitions.py`). Test coverage:
   `tests_scripts/test_buildgen_{web_tag,definitions,schema_ast}.py`.
5. **Digital twin generalization** — consumes the Session 3 generated module directly, replacing
   `configure_i2c_wiring("wozi"|"dev")`'s 2-profile enum.
   - **`buildgen/twin_wiring.py`'s `compute_twin_wiring(model)`** walks `model.instances.values()`
     and emits the digital twin's own per-attachment wiring facts. Two facts a `DeviceModel`
     structurally can't carry get a small, explicit twin-side exception table instead: scd30/sgp40's
     fixed hardware address (`FIXED_ADDRESSES`, matching `src/`'s own hardcoded defaults), and FRAM's
     real RDID reply bytes (`digital_twin/machine.py`'s `_FRAM_RDID_BY_MAX_SIZE`, keyed by size as
     the best available proxy).
   - **`digital_twin/machine.py`**: `configure_wiring(plan)` is the generic entry point;
     `configure_i2c_wiring("wozi"|"dev")` is now pure sugar over it, fed from a literal
     `_LEGACY_WIRING_PLANS` table (this module runs under the MicroPython Unix port, which has no
     `tomllib`, so it can't call `buildgen` directly). `tests_scripts/test_buildgen_twin_wiring.py`
     cross-checks `compute_twin_wiring()` against that literal table for both real devices.
   - **`digital_twin/run_generic_integration.py`** boots any `sensortask_<device>` module against a
     `--wiring-plan` JSON file, resolving it via `__import__(--module)`. `run_wozi_integration.py`/
     `run_dev_integration.py` were retired in Session 6.2 (see below) once this superseded them.
   - **Correctness proof**: `tests_scripts/test_digital_twin_generated_boot.py` generates a device,
     writes its module source + wiring plan to a temp dir, spawns the real MicroPython Unix-port
     binary running `run_generic_integration.py`, and asserts a real `GET` against five REST
     endpoints returns 200 — for all 6 real devices plus both synthetic fixtures. The first point in
     the whole initiative a generated module actually boots and serves traffic, not just parses.
   - **Known limitation**: `machine.py`'s single-chip SCD30/FRAM globals only persist the
     *last-wired* instance's NVM state across a simulated reboot on a multi-instance device — see
     `digital_twin/README.md`'s "SCD30 persistence" section.
6. **Build chain + CI matrix + `build/` artifact directory.** Finish criterion (project owner's
   direction): zero static `src/sensortask_*.py` files, and the *entire* existing digital-twin test
   suite generalized to run against a freshly-generated module for all 6 real device variants.
   - `scripts/build_firmware.py` calls `buildgen.generate.generate_device()` and stages only that
     device's own computed `frozen_modules` set (resolved against `src/`/`ext/`) instead of globbing
     every `src/*.py` file.
   - `boot_entry/` retired outright — `buildgen.codegen.generate_boot_entry_source()` already
     produced an equivalent, generic boot entry since Session 3.
   - `scripts/build_website.sh` generates a device's `definitions.json` on the fly whenever
     `html/definitions/<device>.json` doesn't already exist; `wozi`/`dev` keep their existing
     hand-written files (`tests_js/live-backend-put-matrix.test.js`/`mock-server-put-matrix.test.js`
     read those two files directly as fixtures — switching them over needs a `tests_js/` fixture
     audit, tracked in BACKLOG.md).
   - `.github/workflows/ci.yml`'s `firmware-build-verify`/`digital-twin-e2e` both run a real
     `strategy.matrix` over all 6 devices, `fail-fast: false`.
   - **`src/sensortask_wozi.py`/`sensortask_dev.py` deleted from git.** `scripts/
     _generate_sensortask_modules.py` generates all 6 devices' modules fresh into
     `build/generated_src/` (gitignored) — deliberately not into `src/` itself.
   - **Session 6.2** finished generalizing the digital-twin test suite: `--soak`/`--soak-cycles`
     ported into `run_generic_integration.py`; `scripts/_digital_twin_ci_suite.py` rewritten
     device-generic, driving `run_generic_integration.py` via a `RunContext` dataclass, with
     `.github/workflows/ci.yml`'s `digital-twin-e2e` job gaining its own 6-device matrix;
     `run_wozi_integration.py`/`run_dev_integration.py` retired outright once nothing depended on
     them uniquely; `tests/test_sensortask_wozi.py`/`test_sensortask_dev.py` collapsed into one
     `tests/test_sensortask.py` (315 tests, device-derived expectations, never a hardcoded 3-sensor
     literal); `tests/test_digital_twin_sensortask_integration.py`/
     `test_digital_twin_bus_hazard_concurrency.py` stay a deliberate hybrid — their fast,
     no-real-wall-clock scenarios are parametrized across all 6 devices, their heavier
     seconds-to-tens-of-seconds scenarios (WiFi/hotspot fallback, watchdog escalation, FRAM/SGP40
     reboot survival) stay wozi/dev-scoped since the mechanism they prove is device-independent and
     a full ×6 parametrization would overrun `scripts/test.sh`'s per-file timeout with no real
     margin. **Session 6.3** closed the remaining SGP40 boot-race false-error finding
     (BACKLOG.md item 17).
   - Test coverage: `tests_scripts/test_buildgen_generate.py::test_real_device_constructs_watchdog_exactly_once`
     (parametrized over all 6 devices — the CPython-side replacement for
     `tests/test_reset_call_site_invariant.py`'s now-vacuous `sensortask_*.py`-skip logic);
     `tests_scripts/test_build_firmware.py` (staged set matches `compute_frozen_modules()`, with a
     sanity check that at least one real `src/` module is genuinely excluded).
7. **Versioning** — firmware + website, both starting at `"2.0b0"`, independent constants (a
   website-only fix can bump one without forcing an unrelated firmware rebuild). `GET /system` gains
   one nested, never-flattened `"build"` sub-entry: `{"firmwareVersion", "websiteVersion",
   "buildDate"}` — `src/asy_webserver_service.py`'s `WebserverService.__init__` gained a
   `build_info: dict[str, Any] | None = None` parameter, merged into `_get_system()`'s result after
   `_get_settings_flat()` runs (never through `SettingsGroup`, which would flatten it). Neither
   version nor the build date is rendered in the UI — the Status page's design intent is *live*
   device state, and neither version fact has a live-data question to answer. Website version also
   appears independently as a top-level `websiteVersion` key in `definitions.json` (build provenance
   for the website bundle currently rendering, as distinct from the device's own last-built
   firmware). Single source of truth: `buildgen/version.py` (`FIRMWARE_VERSION`, `WEBSITE_VERSION`,
   `current_build_date()`) — deliberately not a device TOML field (a per-build fact, not a
   per-device one), not `toolchain/versions.toml` (that pins external dependency versions, a
   different kind of "version"), not a `pyproject.toml` field (the shipped product is never
   `pip`-versioned). No bump mechanism exists yet — one clear, documented place to change the two
   constants, no automation, matching `toolchain/versions.toml`'s own precedent. Test coverage:
   `tests_scripts/test_buildgen_{generate,definitions,version}.py`,
   `tests/test_asy_webserver_service.py`, `tests/test_sensortask.py`,
   `tests/test_digital_twin_sensortask_integration.py`.
8. **Closing consistency pass (Session 8)** — bird's-eye scan across everything Sessions 1-7 touched, confirming
   zero device-specific content remains outside the 6 TOML files. `src/`, `buildgen/`, and the bulk
   of `digital_twin/` are clean (every remaining device-name hit is either a historical-precedent
   comment or a previously-documented, deliberate exception). Confirmed both acceptance criteria
   above still hold. Two real findings this pass produced that weren't previously tracked precisely
   enough are now BACKLOG.md items 20 (`tests_hardware/bus_topology.py` dead-code duplication) and
   the `js/app.js` `KNOWN_DEVICES` gap (folded into BACKLOG.md's "Website definitions-file
   autogeneration" entry). This is the last session this doc's own session breakdown calls for.

## Merge-back review checklist

Applied to every spun-off session's PR before it merges into this branch:

1. **Reasonableness/efficiency/expectations** — does the result actually match what that session
   was scoped and primed to do, and is it a sensible, non-bloated way of doing it?
2. **Scope leakage** — did the session implement something that properly belongs to a *different*
   (usually later) session? If so, flag it to that later session when it's spun off — as "question
   whether this is the right way and adapt if required," not "already done, keep it." A later
   session inheriting earlier work must not blindly accept it just because it's already there.
3. **CI-fix legitimacy** — if a session's PR had to fix a CI failure, confirm the fix landed in the
   actual source, not by weakening or working around the test.

## `main` merged in (2026-09-11)

`main` independently landed a large code-quality hardening pass (ruff `select = ["ALL"]`, mypy full
`--strict` everywhere, lint/typecheck scope widened, shellcheck/actionlint/zizmor added) plus the
MicroPython 1.28→1.29 pin move, while this initiative was running. Merged in to keep the initiative
under the same bar; every build-chain-specific decision from Sessions 1-3 survived unchanged.
`buildgen/` needed real fixes to clear the new bar: `generate_module_source()` decomposed into
smaller `_emit_*` functions for mypy's/ruff's complexity ceiling, every internal `assert` converted
to a proper `raise BuildError(...)`, and `tests_scripts/conftest.py`'s `load_script_module()` helper
split into `tests_scripts/_script_loader.py` (mypy resolves each bare module name to exactly one
file per run, so `tests_hardware/`'s and `tests_scripts/`'s own `conftest.py` files can't both
resolve bare in one `host_typecheck.ini` pass).

## Build/generator script quality bar

Binds every session that writes build/generation logic (`buildgen/`'s validator/generator, the
website `definitions.json` generator, the CI orchestration around them). Distinct from the
sensor-code quality bar: a build script's job includes catching every way its own input could be
wrong, and refusing to proceed rather than degrading.

- **Detect and react to every error class that would make a real build impossible** —
  misconfigured/malformed TOML, an unresolved wiring reference, a driver-class/type mismatch, a
  REST/config-name collision with no disambiguating extension, a missing required pin/bus field, a
  missing or incomplete mandatory-infra field in `[device]` (required, not defaulted), a copy-paste
  duplicate, or any other structurally broken definitions file.
- **Global-resource-collision checks are their own error class and must not be skipped.**
  Overlapping bus addresses, double-claimed pin numbers, and any other double-definition of a
  resource meant to be exclusive are *individually valid-looking fields that are still wrong in the
  whole-file view* — only catchable by a cross-instance pass over the entire device:
  - **Schema shape**: each bus (`i2c0`/`i2c1`/`spi0`-style) is its own top-level entry owning its own
    shared wire pins, separate from each instance's own *exclusive* resources (address, CS pin, IRQ
    pin).
  - **Global GPIO-pin exclusivity**: one flat namespace across the whole device — every bus's wire
    pins, every instance's CS/IRQ/standalone-peripheral pin. A physical pin wired to two different
    signals is always an error.
  - **Per-bus address exclusivity**: scoped, not global — two instances on the *same* bus can't
    share an address; the same address on two *different* buses is legitimate. Covers both an
    explicit `address` clash and two hardwired-address instances of the same chip type sharing a bus
    with no way to distinguish them at all.
  - **Instance identity collision** — two instances resolving to the same `instance_name()` (the
    REST/config-key identity) *or* the same `instance_label()` (the generated Python variable name,
    `driver`+`name_ext`) — two independent naming spaces, each with its own dedicated check.
  - **Any other single-owner resource claimed twice** — a bus id defined more than once, or a wiring
    field naming an instance that doesn't exist or is the wrong driver type.
  Every one of these must produce a specific, human-readable error naming the two colliding
  declarations — never a generic "build failed" and never a silent pick of one over the other.
- **A wiring reference resolves against the TOML's own `driver`+`name_ext` identity — never
  against `instance_name()`/each driver's own `_NAME` constant.** See "Device TOML schema" above
  for the full reasoning (`asy_notification_service.py`'s `_NAME` is `"NOTIFY"`, not
  `"NOTIFICATION"` — the concrete case a naive implementation would silently fail to resolve).
- **Driver-declared bus requirements are enforced via a `# @requires` comment tag, never a real
  Python variable** — nothing the running firmware itself ever reads should become a real frozen-bytecode
  value just to serve this generator. Grammar: `# @requires bus.<field><op><value>` (e.g.
  `# @requires bus.timeout>=200000`), placed at module level near the driver's other tags. The
  generator parses driver source files as text for these tags (never imports+introspects), resolves
  the instance's `bus = "..."` reference to its `[bus.*]` table, and evaluates the predicate against
  that table's actual field value — failing loudly (naming device, instance, bus, field, and
  expected-vs-actual value) if not satisfied.
- **Every driver-declared fact the running firmware never reads is a comment tag, not a Python
  value** (project owner's ruling, 2026-09-10) — applies uniformly to `# @wiring`, `# @value-wiring`,
  and `# @limits` alike (BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md has the full grammar/rationale
  for each). The one exception: a `_Default<Field>` class is live code the generated module actually
  constructs, not metadata, so it stays real Python.
- **Standing rule for every tag in this comment-tag family: a tag that's present, or close to
  present with a typo, must be verified correct in every dimension — exact wording, location,
  format, content, validity — or fail the build loud, never be silently treated as "no tag here."**
  `buildgen/tag_comments.py` is the shared mechanism (`KNOWN_TAG_NAMES` registry, tokenize-based
  comment scanning, edit-distance typo matching, a payload-shape gate so ordinary prose mentioning a
  tag's name isn't misflagged) — every tag family (`@requires`/`@wiring`/`@value-wiring`/`@limits`/
  `@web`/`@web-group`) is built on it, never a second, less-tested detector. Each family's own unit
  tests must cover the whole matrix: the accept side needs full dimensionality (every operator
  against every value shape, every legal spacing/placement variant), the reject side covers each
  dimension once without recombining (wording typos including the edit-distance boundary that must
  stay silent; format — each structural piece individually wrong or dropped; location — indented
  into a body, or onto a continuation line; content; validity against a real bus table; scanning —
  tag-shaped text inside a string/docstring, an unparseable file), plus the false-positive checks
  that make the mechanism trustworthy (realistic prose merely mentioning the tag's name, an
  unrelated `@`-word). `tests_scripts/test_buildgen_tag_comments.py` and
  `test_buildgen_requires_tag.py` are the reference implementation of this bar — motivated by a real
  incident: an actual driver signature change once silently broke two
  `tests_hardware/device_scripts/` call sites for a full day, undetected because nothing in that
  scope was checked at all. A malformed comment-tag silently parsing to "no tag declared" is the
  same class of risk one layer down.
- **Never produce a corrupted or partial build.** On any detected error, abort the entire build
  immediately — no partial `build/<device>/` output left behind that could be mistaken for a real
  artifact.
- **Fail loudly, clearly, and human-readably.** A plain, actionable message naming exactly what's
  wrong and where (which device, which instance, which field) — not a raw traceback, not a silent
  wrong-default fallback. This is the build-tooling equivalent of CLAUDE.md's "flag, don't silently
  change" convention.
- **Tested to the same bar as `src/` code**: correct-path functioning, full error-handling-path
  coverage (every abort condition gets its own test, driven by deliberately malformed fixture
  definition files — never just incidentally exercised by the six real device TOMLs happening to be
  valid), and code coverage. Follows the established `tests_scripts/` convention (pytest, real
  CPython) rather than inventing a new test harness.
- Newly-built generator/validator modules join `pyproject.toml`'s ruff/mypy scope alongside
  `src/`/`tests/`/`digital_twin/` from day one — fresh code, not pre-existing legacy tooling.

This is the same "each module/function tested exactly one time" CI principle already agreed, applied
to error-handling paths specifically: a build/generator function's abort conditions are themselves
testable units, not just incidentally covered by the real device TOMLs happening to be valid.
