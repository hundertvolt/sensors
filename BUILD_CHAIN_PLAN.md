# Automated Build Chain — Plan

Working plan for making `src/`, the website (`html/`+`js/`), the build script chain, and the test
chain fully device-generic — every device-specific fact (hardware present, pin/bus assignments,
included software modules, how measurement values are shared between modules) lives in exactly one
TOML config file per device variant. This doc is the shared reference for every session spun off
this branch; update it as decisions evolve. Once the whole chain lands and is verified, this
branch merges into `main` as the single final step — not before.

## Target device variants

Six: `dev` (bench rig only, never physically absent from testing — see CLAUDE.md), `wozi`
(exemplary/base variant, never physically flashed), `arzi` (distinct wiring from the "neu"
family), and `klkizi`/`grkizi`/`schlafzi` (the three "ArZi neu" units — currently identical
hardware to each other, but each gets its own independent TOML file since future hardware
divergence between them is expected).

## Acceptance criteria — the actual promise (project owner's explicit direction, 2026-09-09)

These are the literal, testable definition of "done" for Sessions 2/3/4/6 collectively — not new
scope, a crystallization of what the rest of this doc already implies. Any future session touching
the generator/website builder/CI matrix should validate its own work against these directly:

1. **Adding a new driver module to the repo requires exactly one small, explicit fact: associating
   its common name (the one used in a device TOML) with its actual Python file/class — nothing
   else.** Everything else (schema fields, frozen-module inclusion, REST/config/error-log naming,
   website field generation, wiring-port validation) is derived automatically from the driver file
   itself once that association exists.
   - Prefer deriving this association from the codebase's own already-mandatory naming convention
     (`asy_<name>_driver.py` → `<Name>_Reader` class → `_NAME` constant, SPECIFICATION.md Part
     C.5) rather than a separate hand-maintained lookup table — a `driver = "<name>"` TOML value
     maps to its class purely by that existing naming rule, so writing the file correctly (already
     mandatory) *is* the association, with nothing extra to keep in sync. Fall back to an explicit
     table only where a driver genuinely can't follow the naming pattern.
   - **Named exception, not a broken promise**: digital-twin coverage of a genuinely new chip type
     still needs someone to hand-write that chip's simulated register/protocol behavior — inherently
     bespoke, not derivable from the driver file. This is outside "the auto build" in the firmware/
     website-generation sense this criterion is about.
2. **Wiring up a new hardware combination of already-known modules requires exactly one new file —
   the device's TOML — and nothing else; the full firmware+website build follows automatically.**
   No driver code changes, no generator changes, no per-device test file. Session 3's and Session
   6's own test suites must include a **synthetic "novel combination" fixture device** — existing
   drivers mixed in a pin/bus layout none of the 6 real devices use — proving the full pipeline
   (firmware build, website generation, digital-twin boot) succeeds from that one new file with
   zero code changes elsewhere. This is a stronger proof than the 6 real devices alone, since those
   are all hand-verified against real wiring facts rather than exercising the generator's full
   generality.

## Core design decisions

- **Config format**: TOML (matches `toolchain/versions.toml`'s existing precedent).
- **Generation is build-time only, nothing committed.** `build/<device>/{py,html,frozen,firmware}`
  is a single gitignored root; cleanup is `rm -rf build/`. Local `scripts/test.sh`-style runs are
  sufficient for iteration; CI regenerates and tests every variant (including a digital twin boot)
  on every push, so there's no coverage gap versus committing generated output.
- **Naming**: `SensorStation<Name>` is the base stub (liked by the project owner), used as the
  default hostname, website display identity, and anywhere else device identity shows up. The
  hotspot SSID is literally the `Hostname` config field's value (confirmed via
  `src/asy_wifi_service.py` — no separate SSID mechanism exists). Hotspot password becomes a
  per-device TOML field defaulting to the existing hardcoded `"12345678"`.
- **Cross-instance wiring is fully static, resolved at generation time, never at runtime.** No
  runtime registry/bus. Each driver declares a `_WIRING` tuple next to its existing `ConfigSchema`
  tuples — `(toml_field_name, required_driver_class)` — naming which TOML field supplies a source
  instance and what class it must be. The generator resolves each reference to the actual
  constructed Python object and passes it directly into the consumer's constructor. No
  "provides" registry needed — an instance either is the expected class or it isn't, checked
  directly.
- **Every real cross-instance link gets a TOML-visible `[instance.wiring]`/`[device.wiring]`
  field — none stay hardcoded in `build_system()`.** Covers `sgp40.temperature_source`/
  `.humidity_source` (originally one whole-object `comp_source` field; generalized into two
  independent per-value fields by BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md §2.9, 2026-09-10 -
  see that document for the full mechanism, including the `{default = true, ...}` fallback opt-in),
  `notification.signal_sink`/`warn_co2`/`warn_voc`/`warn_hum`, and `fram_target` on every
  driver/service with an optional `fram=`/`fram_storage=` argument (`scd30`, `sgp40`, `bmp3xx`,
  `neopixel`, `notification`, plus `device.wiring.fram_target` for `SystemService`'s own `fram=`)
  and `device.wiring.led_target` for WiFi's `conn.set_ext_led(pixel)`. Each field is individually
  optional; absence disables that specific link rather than erroring — wiring only some of a
  device's instances to FRAM and not others is a deliberate degree of freedom. **Excluded**: links
  between two mandatory-infrastructure modules (both endpoints always exist unconditionally, so
  there's no real presence/absence choice), and `WebserverService`'s `sensors=`/`settings=`/
  `maintenance_sensors=`/`is_hotspot_active=` arguments, which enumerate whichever instances a
  device's TOML already declares rather than naming one specific instance.
- **No getters, no callback functions in generated code.** A consumer holds a direct reference to
  the producer's existing concurrency-safe value holder (SPECIFICATION.md Part G's "locked state"
  primitive) and reads `.value` directly when needed — eliminating the
  `sgp_comp_callback()`/`co2_value_callback()`/`voc_value_callback()`/`hum_value_callback()`-style
  functions in `src/sensortask_wozi.py` (lines ~78-232) as a category. N-to-1 fan-in (error
  sources feeding `SystemService`, threshold-notifier sources feeding the Neopixel driver)
  collapses the same way: the aggregator holds a plain list of instances (collected via a shared
  base class in `base_classes.py`, to be confirmed/extended in Session 1) and reads each one
  directly — replacing `_collect_error_sources()`/`_collect_level_setters()`'s hand-enumerated
  getter/setter lists.
- **Two ordering hazards, both must be handled, neither by hand:**
  1. *Object existence*: a consumer's constructor call references the producer's Python object
     directly, so the producer must be constructed first. The generator topologically sorts
     instances by `_WIRING` dependency (not raw TOML declaration order) and rejects a cycle as a
     build-time error. (FRAM chunk order genuinely doesn't matter — random access — so this is
     purely a Python name-resolution requirement, not a FRAM one.)
  2. *Live data availability*: independent async tasks mean a consumer's first read can easily
     happen before the producer's first real measurement completes. Every producer's locked-value
     holder must have a safe, defined initial value at construction (before any real measurement),
     and every consumer must already tolerate that "not yet measured" state as normal, not
     exceptional — audited per existing driver in Session 1, not assumed.
- **Instance naming**: every optional module gets an optional name-extension field, default empty
  string. REST paths, config filenames, and (audit needed) FRAM-backed error-log/errcount keys all
  incorporate it uniformly: `/sensors/scd30` by default, `/sensors/scd30_fan_pressure` when named.
  The generator errors on a naming collision when no disambiguating extension was given.
- **Bus/pin config**: every I2C/SPI bus pin, IRQ pin, CS pin, Neopixel pin, etc. is defined in the
  device's TOML — no hardcoded pins anywhere in generated or hand-written driver-wiring code. A
  device address field only exists for chips with a logically-selectable address (check
  datasheets); hardwired-address chips get no address field at all.
- **Frozen-module selection is dependency-driven**: the generator seeds from each device's declared
  driver list plus a fixed always-included core set, then takes the transitive closure of real
  (never dynamic — dynamic imports are disallowed project-wide, to be noted in SPECIFICATION.md)
  `import`/`from...import` statements, AST-scanned post-`TYPE_CHECKING`-stripping.
- **Testing**: generic driver/service logic is tested exactly once; only the device-specific slice
  (generated wiring module, generated website definitions, digital-twin boot of that config) runs
  once per device in CI. Tests are generic bodies driven by each device's TOML/generated module,
  never hand-written or generated per-variant test files, so adding a 7th variant never means
  writing a 7th test file.
- **Watchdog stays fixed** (hardcoded 8000ms, uniform, never per-device — settled project rule, not
  revisited here).
- **Real hardware flashing is out of scope for this entire initiative.**
- **Build-time tooling gets a fundamentally different error-handling contract than the runtime
  code it emits** — detect every error that would make a build impossible and abort loudly rather
  than degrade. Full requirement, including the mandatory unit-test-suite bar: see "Build/
  generator script quality bar" below.

## Device TOML schema (Session 1 deliverable — shape only, not the 6 real files)

The shape every device's TOML file follows (the 6 real files live at `devices/<device>.toml`).
Uses the mechanism `src/` has after Session 1 (`config_manager.py`'s `instance_name()`,
`WiringSchema`; `base_classes.py`'s `name_ext`/`get_error_sources()`/`get_loggers()`; each driver's
own `_WIRING` — full mechanism reference: `SPECIFICATION.md` Part C.14).

Two top-level shapes: a single `[device]` table (identity/network facts, plus mandatory-infra
tuning and wiring — see below) and a uniform `[[instance]]` array of tables. **The `[[instance]]`
array models optional modules only** — driver-level sensors, plus singleton services that vary or
could someday be absent per device: FRAM, Neopixel, NotificationCoordinator.

**WiFi, NTP, and SystemService are mandatory infrastructure and are never `[[instance]]`
entries** — every buildable device has all three unconditionally, so there is no
presence-or-absence question for the schema to encode. Their own per-device-tunable knobs (WiFi's
`conn_fail_to_hotspot`/`hotspot_time_min`; NTP/SystemService have none today) live directly in
`[device]`, and their crosslinks to optional instances live in `[device.wiring]`
(`led_target`/`fram_target`, both optional). Both `[device]` tuning fields are **required, not
defaulted**: a device TOML missing either is a build-time error, the same fail-loud contract
"Build/generator script quality bar" below gives every other structurally-broken definitions file.

The webserver — also unconditional — is never modeled as an instance either: its constructor takes
no independent per-device facts, only references to whichever other instances the TOML already
declares, so there's nothing for a `[[instance]]` entry to carry.

A device variant that lacks a given *optional* singleton simply omits that `[[instance]]` entry —
the same absence-means-absent handling a missing sensor gets. WiFi/NTP/SystemService are never
optional and never omitted.

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

# Per-value measurement wiring (§2.9 of BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md), replacing
# the original single, required, _WIRING-declared whole-object comp_source field above: each
# independently required (or explicitly defaulted via {default = true, ...}).
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
signal_sink = "neopixel"                   # required; not yet resolvable by _WIRING as specified -
fram_target = "fram"                       # see note below

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

**Resolved by Session 3** (previously open here): `_WIRING`'s tuple shape is extended from 2 to 5
elements — `(toml_field_name, required_driver_class, target, required, mode)` — where `mode`
(`"kwarg"`/`"attr"`/`"setter"`) says how the resolved producer is actually handed to the consumer.
`signal_sink` uses `mode="attr"`: the generator resolves it to `pixel.request_signal` (the bound
method `NotificationCoordinator.__init__`'s existing `request_signal_cb` parameter wants), not the
`NeopixelDriver` instance itself — no change to that constructor's own signature. `led_target` uses
`mode="setter"`: `conn.set_ext_led(pixel)` is emitted once, after both already exist, instead of at
construction time. Full rationale, and why this is purely additive (no existing driver's
constructor signature changed): SPECIFICATION.md Part C.14.2 and this session's own PR description.
Each notification signal's own threshold default/range and flash color: also resolved — see
"Session 3 done" below.

**Settled by this schema**: the two top-level shapes above, `[[instance]]` for optional modules
only, `name_ext`'s default-empty-means-unchanged rule, `[instance.wiring]`'s shape (a flat
`{field = "driver[_name_ext]"}` table for a required single-instance reference, or a
`[instance.wiring.<name>]` sub-table of `{source, field}` for an optional getter reference — see
"Build/generator script quality bar" below for exactly what that identifier means and why it isn't
`instance_name()`), `[device.wiring]` as the mandatory-infra-side mirror of `[instance.wiring]`,
the standing "every real cross-instance link is TOML-visible" rule and its two exclusions (see
"Core design decisions" above), that a getter/optional-producer reference defaults to disabled when
absent rather than erroring (unlike a required reference like `signal_sink`, or `temperature_source`/
`humidity_source` without an explicit `{default = true, ...}` opt-in - see
BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md §2), and that an `address` field only exists for a
driver kind whose chip actually has one.

**Session 2 done**: the 6 real files live at `devices/<device>.toml`. The six `device.name` values
are `Wozi`/`Dev`/`Arzi`/`Klkizi`/`Grkizi`/`Schlafzi`, feeding `hostname = "SensorStation<name>"`.
Every device's `hotspot_password` is the accepted-risk default (`"12345678"`, CLAUDE.md). `wozi`/
`dev` are the only two with a `bmp3xx` instance; `klkizi`/`grkizi`/`schlafzi` share byte-for-byte
identical wiring (only `device.name`/`hostname` differ), sourced from `modules/sensortask-neu.py`.
Every SCD30-carrying `i2c0` bus gets `timeout = 200000` clock-stretch headroom
(`src/asy_i2c_driver.py` supports it; the legacy `asy_i2c_driver.py` arzi/neu were built against did
not).

A minimal shape/collision smoke-test suite lives at `tests_scripts/test_device_tomls.py` (parses as
valid TOML, matches this schema's shape, and re-implements — by hand, since no generator/validator
exists yet — the global-GPIO-pin/per-bus-address/instance-name collision checks below against these
6 real files specifically; **not** a substitute for Session 3's own full validator and its
malformed-fixture test coverage).

**Session 3 done** (the mechanisms below are the end state, after the six implementation phases
recorded in `BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md` §10 — read that document before building
anything against a device TOML's or a generated module's shape): the generator lives at `buildgen/` (a new top-level CPython package, never
imported by `src/` — chosen over putting it under `scripts/` specifically so it joins
`pyproject.toml`'s ruff/mypy scope under the full quality bar immediately, per that doc's own #10
below, rather than inheriting `scripts/`'s/`toolchain/`'s documented legacy gap). `buildgen.
generate.generate_device(toml_path, src_dir, ext_dir)` runs the full pipeline (`buildgen.validate.
build_model()` → `buildgen.graph.build_construction_order()` → `buildgen.codegen.
generate_module_source()`/`generate_boot_entry_source()`) and returns the generated
`sensortask_<device>.py`-equivalent + boot-entry source as strings, plus
`buildgen.frozen_modules.compute_frozen_modules()`'s module set — callers (this session's own
tests; a future Session 6) decide whether/where to write them. Concretely:

- **`driver` → class**: `buildgen.driver_registry.resolve_driver()` AST-parses (never imports —
  `src/` modules need real `machine`/`neopixel`/`asyncio.ThreadSafeFlag`, unavailable under plain
  CPython) `asy_<name>_driver.py` for a `SensorReader`/`SensorReaderConfig` subclass; a fallback
  table (`fram`/`neopixel`/`notification` — none of the three follows the file-naming convention or
  is a `SensorReader` subclass) covers the one named exception the acceptance criteria itself
  allows. Also determines whether the resolved class needs `await <instance>.setup()` called
  (`SensorReaderConfig` base, or a bare `async def setup` on the class) — again by AST inspection,
  not a hand-maintained table.
- **Topological construction order**: `buildgen.graph.build_construction_order()` — see
  SPECIFICATION.md Part C.14.2's updated account.
- **Wiring resolution**: strictly against the TOML's own `driver`/`name_ext` identity, never
  `instance_name()`/`_NAME` (confirmed via a dedicated `parse_name_constant()` check that
  `NotificationCoordinator`'s own `_NAME` really is `"NOTIFY"`, not `"NOTIFICATION"` —
  `tests_scripts/test_buildgen_driver_registry.py::test_parse_name_constant_confirms_notify_is_not_notification`).
- **Global resource-collision validation**: `buildgen.validate.build_model()` — schema shape,
  global GPIO exclusivity, per-bus address exclusivity (including the two-hardwired-address-
  instances-with-no-`address`-field case, scoped per `(bus, driver kind)` so two *different*
  fixed-address chip types sharing a bus correctly doesn't false-positive), instance-name collision,
  bus-id collision (TOML's own duplicate-key rule already covers this), and every wiring-reference/
  mandatory-`[device]`-field/required-instance-field check — every failure is a `buildgen.errors.
  BuildError` naming the device/instance/field responsible, never a generic failure or a raw
  traceback.
- **`# @requires bus.<field><op><value>`**: `buildgen.requires_tag`, on the shared
  `buildgen.tag_comments` scanner (tokenize-based, typo-tolerant near-miss detection — see the
  quality bar's standing rule for the whole tag family) — text-parsed from driver source, never a
  real Python value. Three tags across two drivers today: `asy_scd30_driver.py`'s
  `bus.timeout>=200000` (its real clock-stretch requirement) and `bus.frequency<=100000`
  (Interface Description p.2, "Maximal I2C speed is 100 kHz"), and `asy_sgp40_driver.py`'s
  `bus.frequency<=400000` (datasheet Table 3's fSCL max). A bus shared by both is held to the
  stricter of the two. `bmp3xx` is deliberately untagged — its datasheet supports every I2C mode,
  so any bound would be invented rather than documented.
- **Per-field domains — `# @limits`**: `buildgen.limits` parses `<field> <min>..<max>` or
  `<field> in {a, b}`. Only `asy_bmp3xx_driver.py` declares one today (`address` ∈ {0x76, 0x77}, `trigger_sec` ∈ [1, 3600],
  both from constants already in that file) — no invented bounds anywhere.
- **Wiring defaults and per-value measurement wiring**: `buildgen.defaults` AST-discovers a
  driver's `_Default<Field>` classes (the `__init__` signature *is* the schema for a
  `{default = true, ...}` TOML sub-table), and `buildgen.value_wiring` parses `# @value-wiring` —
  independent per-value `{source, field}` fields resolved by attribute name, replacing SGP40's old
  whole-object `comp_source`. See BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md §2/§2.9.
- **Pin legality and role**: `buildgen.pico_gpio` holds the Pico W's fixed GPIO→peripheral table
  (datasheet Figure 2), so every claimed pin device-wide is checked for real existence and
  non-reserved status, and each bus's own wire pins additionally for the right peripheral index
  *and* role — catching a transposed `scl_pin`/`sda_pin` pair, not just an illegal pin.
- **Notification signal catalog**: each notification signal's own threshold default/range and
  flash color (BUILD_CHAIN_PLAN's own previously-open question) is a fixed, generator-owned catalog
  (`buildgen.codegen._KNOWN_SIGNALS`) covering `warn_co2`/`warn_voc`/`warn_hum` — every real device
  TOML today uses identical values with no per-device override in the schema, so hardcoding them in
  the generator (not per-device) mirrors exactly what `src/sensortask_wozi.py`/`sensortask_dev.py`
  already do. A `warn_*` key outside this catalog is a fail-loud `BuildError`, not a silent
  no-op — flagged here as a genuine future TOML-schema extension point, not solved by this session.
- **Frozen-module selection**: `buildgen.frozen_modules.compute_frozen_modules()` — AST-scanned
  transitive `import`/`from...import` closure, seeded from a fixed core set plus each device's own
  declared driver modules, `TYPE_CHECKING` blocks stripped. Computes *which modules*; wiring that
  list into the real `freeze()`/`scripts/build_firmware.py` call is Session 6's job.
- **Mandatory synthetic "novel combination" fixture**: `tests_scripts/buildgen_fixtures/
  novel_combo.toml` — two `SCD30`s (multi-instance, name_ext-disambiguated), `SGP40` taking its
  temperature from one and its humidity from the *other*, `BMP3xx` at the alternate
  hardwired-address value, and `Notification` wired to only one of the three `warn_*` signals — a
  pin/bus/wiring layout none of the 6 real devices use, proving the generator's full pipeline
  succeeds from this one new file alone. A second fixture, `multi_instance.toml`, adds 2× scd30 and
  2× sgp40 at once, a cross-driver-type value reference (`bmp3xx`'s own `Temp`) and an explicit
  `{default = true, ...}` constant.
- **Correctness proof depth** (this doc's own former open question 3): generated output is proven
  syntactically valid Python (`ast.parse()`) matching the documented construction-order/wiring
  shape, via `tests_scripts/test_buildgen_generate.py` against all 6 real devices plus the
  synthetic fixture — **not** executed under the real MicroPython Unix-port interpreter. Decided
  against going further: `buildgen/` is deliberately AST-only, never importing `src/` (real
  MicroPython-only names aren't available under plain CPython) — actually booting a generated
  module needs the same hardware-fake environment Session 5's digital-twin generalization is
  explicitly tasked with building; attempting a shallow version of that here risked exactly the
  scope-leakage this doc's merge-back checklist flags.
- **Not built here** (deliberately, per this session's own scope): wiring the generator into
  `scripts/build_firmware.py`/`boot_entry/*.py`, replacing either hand-written `sensortask_wozi.py`/
  `sensortask_dev.py` file, website `definitions.json` generation, digital-twin generalization, the
  CI matrix, versioning, the closing consistency pass — all later sessions' own jobs, per the
  session breakdown below.

Full test coverage (TDD, written first): `tests_scripts/test_buildgen_driver_registry.py`,
`test_buildgen_wiring.py`, `test_buildgen_requires_tag.py`, `test_buildgen_frozen_modules.py`,
`test_buildgen_graph.py`, `test_buildgen_validate.py` (every abort condition, driven by
deliberately malformed fixtures built from `tests_scripts/_toml_fixtures.py`'s `base_doc()` — never
just incidentally exercised by the 6 real device TOMLs happening to be valid), and
`test_buildgen_generate.py` (end-to-end, all 6 real devices + the synthetic fixture).

**Global resource-collision validation, required of Session 3** (project owner's explicit
direction, 2026-09-09) — the full requirement, including the two schema-level fields this example
TOML above already reflects (buses as top-level entries owning their own shared wire pins,
`[instance.wiring]` as the one place a cross-instance reference lives), is in "Build/generator
script quality bar" below, not repeated here.

## Session breakdown (dependency-ordered)

1. **Wiring mechanism + device TOML schema design** (`src/`) — the `_WIRING` tuple convention;
   audit/extend instance-naming across REST/config/error-log; confirm/extend the shared base
   class(es) needed for N-to-1 fan-in collection; confirm the locked-value primitive is the right
   holder and that every producer has a safe pre-measurement default; design the TOML schema shape
   (not the 6 real files). Does **not** build the generator itself (topological sort + code
   emission is Session 3) — designs `_WIRING` so Session 3 can consume it.
2. **The 6 real device TOML files**, built from the wiring facts already gathered from
   `src/sensortask_wozi.py`, `src/sensortask_dev.py`, `modules/sensortask-arzi.py`,
   `modules/sensortask-neu.py`.
3. **Done. Python generator** (`sensortask_<device>.py` + boot entry) — topological construction
   ordering, dependency-driven frozen-module selection, generic definitions-file-derived tests.
   Lives at `buildgen/`; see "Session 3 done" above for the full account.
4. **Done. Website `definitions.json` generator** — resolves BACKLOG.md's `@web`/`@web-group` open
   sub-questions, combined with each device's TOML instance list. **Read
   BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md first**: its §2/§2.9 (landed 2026-09-10) changed the
   device TOML shape a real device's instance list can carry (`comp_source` → independent
   `temperature_source`/`humidity_source` fields, plus the general `{default = true, ...}` opt-in
   shape now legal on any defaultable wiring field) - a definitions.json generator built against
   the pre-2026-09-10 shape would silently miss both.

   **Session 4 done**: the `@web`/`@web-group` comment-tag family lives at `buildgen/web_tag.py`,
   built on `buildgen/tag_comments.py`'s shared scanner exactly like `requires_tag.py` (registered
   in `tag_comments.KNOWN_TAGS`, its own `_looks_like_web_payload`/`_looks_like_web_group_payload`
   near-miss predicates). **Grammar, resolving the sketch's three open questions**: every tag names
   its target explicitly rather than relying on file position - `# @web <Field> section=<key>
   submitGroup=<key|self> label="..." [unit=...] [description="..."] [kind=...] [onLabel=...]
   [offLabel=...] [mask=true] [dispatch=true] [defaultValue=...] [special:<value>="<meaning>"]...`
   and `# @web-group section=<key> submitGroup=<key|self> label="..." [submit=true]
   [submitLabel=...]` - a deliberate departure from the sketch's pure key=value-only shape (which
   had no way to say *which* field/group a tag described once a field has no nearby schema tuple to
   sit next to, e.g. `ContMeas`), while keeping every other tag family's existing "identity is a
   leading token, not position" convention. `submitGroup=self` is a reserved sentinel meaning "this
   TOML instance's own resolved name" (substituted at generation time) - used by scd30/sgp40/bmp3xx,
   which can have more than one instance per device; every other group (WiFi's `identity`/`wifiLed`,
   NTP's `ntp`, System's `settings`, Notification's `autoConfig`) uses a literal key instead, since
   none of those drivers is ever multi-instance.
   - **Open question 1** (where does a non-driver-schema value like `lightCmdLED` anchor a tag):
     resolved by **not** tagging it at all. `SystemCmd`/`PauseTime`/`lightCmdLED`/`ResetErrors` and
     the entire Status section's own live-readonly field lists are fixed, generator-owned catalogs
     in `buildgen/definitions.py` - the same precedent Session 3 already set for
     `buildgen.codegen._KNOWN_SIGNALS` (universal across every device, hardcoded rather than
     inventing a TOML/tag mechanism for something that never varies). `_WARN_SIGNAL_WEB_CATALOG` is
     this module's own parallel of `_KNOWN_SIGNALS` (label/unit UI metadata for the same three
     `warn_*` keys) - kept in sync by cross-reference/comment, not import, since the two need
     genuinely different shapes.
   - **Open question 2** (does `@web-group`'s `endpoint`/grouping duplicate `SettingsGroup(...)`'s
     own wiring): resolved by making the six-REST-endpoint section skeleton itself
     (`_SECTION_SKELETON` - keys, labels, REST paths, `pollGroup`) fixed/generator-owned too, never
     tag-derived - it's pure routing architecture (H.4: "mirrors the 6 REST endpoints 1:1"), not a
     per-driver fact any tag could sensibly own. `@web-group` tags only ever supply a *group's* own
     label/submit metadata, never section-level facts, so there is nothing left to duplicate against
     `SettingsGroup(...)`.
   - **Open question 3** (a full formal grammar): still deliberately minimal, matching the sketch's
     own stated scope - a quoted value may not contain a literal `"` (no escaping), and every tag is
     a single physical line (no continuation syntax, unlike `@wiring`'s bracketed-continuation-line
     allowance, since a `@web` tag's payload volume - a label, an optional unit/description, a
     handful of `special:` entries - never needed it).
   - **What's tag-derived vs. inferred vs. generator-owned**: most per-field metadata is inferred
     automatically from the real `ConfigSchema`/`FieldSchema` constant already in the driver file
     (`buildgen/schema_ast.py` - AST-evaluates the exact `_VAL_*`/bare-`FieldSchema` literal shapes
     `src/` actually uses, resolving `const()`-wrapped named references like `_OSR_SETTINGS`,
     without importing) - `kind` (`toggle` for `bool`, `string` for `str`, `enum` when the schema's
     own discrete-choice tuple is non-empty, `number` otherwise), `min`/`max`/`minLength`/
     `maxLength`, `float`. A tag only ever supplies what the schema tuple structurally can't: label
     (always required), unit, description, an explicit `kind=` override for a field with no matching
     schema constant at all (`ContMeas` - freestanding, fully tag-specified), and `special:` labels
     for a schema-declared discrete/sentinel value. One real-code finding this surfaced: SGP40's
     `BackupPeriod`/`BackupMaxAge`/`WaitTimeNTP` each have a documented "0 means X" meaning
     (matching AmbPres's sentinel pattern in the hand-written JSON) despite their own schema tuples
     carrying `special=None` (0 is a perfectly ordinary in-range value, not a validation bypass) -
     the generator honors a tag's own `special:` entries whenever present, regardless of what the
     schema's `special` slot says, rather than requiring a schema-declared sentinel to unlock them.
   - **The generator**: `buildgen/definitions.py`'s `generate_definitions(model, src_dir)` takes an
     already-`buildgen.validate.build_model()`-validated `DeviceModel`, scans each relevant
     instance's/mandatory-infra file's tags (cached per source path), and assembles the full
     `definitions.json`-shaped dict - measurements/sensors groups keyed by each instance's own
     `resolved_name` (so a multi-instance device gets distinct, correctly-labeled cards), the
     networking/system/notification groups assembled from tags spanning more than one file (e.g.
     `GMTOffset`/`DSTOffset` are real `asy_ntp_client.py` fields that render on the System page's
     `settings` card - contributed there via `section=system submitGroup=settings`, with
     `system_service.py` as that group's sole `@web-group` declarer; declaring `@web-group` for the
     same `(section, submitGroup)` in two files is a `BuildError`, the cross-file "global resource
     collision" check this quality bar's own section calls for), and the errcount module catalog/
     Status section's own live field lists gated by which optional instances the device actually has
     (`have`). Seven `src/` files carry the real tags: `asy_scd30_driver.py`, `asy_sgp40_driver.py`,
     `asy_bmp3xx_driver.py`, `asy_wifi_service.py`, `asy_ntp_client.py`, `system_service.py`,
     `asy_notification_service.py`.
   - **Correctness proof**: `generate_definitions()` run against `devices/wozi.toml`/`dev.toml`
     produces output structurally identical (order-insensitive) to the existing hand-written
     `html/definitions/wozi.json`/`dev.json` - the strongest available signal, since those two files
     are the sketch's own already-checked-against-real-code reference. All 6 real devices pass a
     `js/definitions.js`-`validateDefinitions()`-equivalent shape check written directly in Python
     (`tests_scripts/test_buildgen_definitions.py`), and the mandatory `novel_combo.toml`/
     `multi_instance.toml` synthetic fixtures generate successfully, proving the per-instance
     `resolved_name`-keying genuinely generalizes beyond the two real devices that happen to need it
     (`wozi`/`dev`'s own instance lists never repeat a driver). Full test coverage (TDD, written
     first): `tests_scripts/test_buildgen_web_tag.py` mirrors `test_buildgen_requires_tag.py`'s own
     dimensionality (field-name/key=value shapes, format/spacing, placement, multiplicity, the full
     near-miss matrix including cross-family contamination checks, and a real-driver spot check);
     `tests_scripts/test_buildgen_definitions.py` covers the golden-file comparison, per-device
     instance variation, the synthetic fixtures, and targeted failure paths (a missing `@web-group`,
     a missing `special:` label, a duplicate cross-file group declaration) built by mutating a
     temporary copy of one real driver file rather than a synthetic TOML fixture, since this
     generator's own malformed-input surface is source-file tags, not TOML.
   - **Not built here** (deliberately, per this session's own scope - flagged per the merge-back
     checklist, not silently absorbed): wiring this generator into `scripts/build_website.sh`/CI, or
     retiring the hand-written `wozi.json`/`dev.json` (Session 6's job); generating a
     `definitions.json` for the four real devices that don't have one yet (`arzi`/`klkizi`/`grkizi`/
     `schlafzi`) - the generator itself already produces a correct one for all six (proven by the
     shape-validation test above), but writing those four files to `html/definitions/` and wiring
     them into the build is bundled with the same Session 6 work as retiring the two hand-written
     ones, rather than landing four new committed files this session that Session 6 would then have
     to reconcile against its own generated output; digital twin generalization (Session 5).
   - **A one-line `pyproject.toml` addition**: `[tool.ruff.lint].allowed-confusables = ["×"]` - the
     real BMP3xx oversampling option labels (`"×1"`, matching the existing hand-written JSON
     exactly) use U+00D7 MULTIPLICATION SIGN, which RUF003 otherwise flags as a suspected ASCII "x"
     look-alike inside the `# @web ... special:N="×N"` tags carrying it.
   - **Post-merge self-audit found and fixed three gaps** (project owner asked for a paragraph-by-
     paragraph check against SPECIFICATION.md/this plan/the test-completeness bar/documentation
     rules - none of these were caught by the original PR's own review or by CI):
     - `buildgen/web_tag.py`/`schema_ast.py`/`definitions.py`'s module docstrings, plus both new
       test files' own docstrings, had drifted well past CLAUDE.md's hard 3-line header-comment cap
       (up to 22 lines) - the exact "website-facing facts" that same rule says belong in
       SPECIFICATION.md instead. Fixed by adding **SPECIFICATION.md Part H.5.1** (the architecture/
       rationale content that used to live in those docstrings) and trimming every docstring to a
       short pointer at it; H.5's own stale "Autogeneration is not yet built" line is corrected too.
       The two test files' "Matrix dimensions" blocks moved from inside the docstring to a plain
       `#`-comment block below it, matching `test_buildgen_requires_tag.py`'s own established
       pattern (that file was never in violation - it already split the two).
     - `buildgen/schema_ast.py` had **zero dedicated unit tests** - unlike every sibling AST-scanning
       module (`buildgen.driver_registry` included, the module its own docstring says it matches).
       Its real behavior (both assignment shapes, `const()`-wrapped `Name` resolution, negative
       numbers, list-vs-tuple literals, and the silent-skip paths for an unresolvable name/
       unsupported node/non-numeric negation) was previously proven only incidentally, through
       `generate_definitions()`'s own golden-file tests happening to exercise some of it. Fixed with
       `tests_scripts/test_buildgen_schema_ast.py` (17 tests, synthetic + a real-driver spot check
       against `asy_bmp3xx_driver.py`'s `_OSR_SETTINGS`/`_IIR_SETTINGS`-resolving fields).
     - `test_buildgen_web_tag.py`'s own matrix had real holes against the standing tag-family bar:
       no coverage of the `_WebGrammarError` "dropped-piece" path (trailing junk, a dropped value, a
       duplicate key) for either `@web` or `@web-group`, no edit-distance-boundary "stays silent"
       case for either family's own typo tolerance, no "valid tag beside a near-miss" regression
       guard, and real-driver spot checks thin everywhere but scd30/bmp3xx. Closed with 17 more
       tests (66 → 83), including exhaustive field-name-set checks for the five previously
       under-covered real driver files.
     - **Flagged, not fixed** (pre-existing, out of this session's scope, genuinely ambiguous):
       `buildgen/tag_comments.py`'s `iter_comment_tokens`/`check_for_near_miss_tags` docstrings
       already exceeded the 3-line cap before this session (Session 3) - a cross-file consistency
       discrepancy to flag per CLAUDE.md's "flag, don't silently fix" rule, not this session's tag
       family's own docstring to correct. Separately, SPECIFICATION.md H.5's own claim that
       `dispatch: true` covers "H.6, minus `ContMeas`" doesn't match the real hand-written
       `wozi.json`: `lightCmdLED`/`PauseTime` are both in H.6's dispatch-only list but carry no
       `dispatch: true` in the actual JSON (only `SystemCmd`/`ResetErrors`/`SGPResetVOC` do) -
       `buildgen/definitions.py` faithfully reproduces the real, golden behavior either way, so this
       is a pre-existing spec-vs-reality mismatch to resolve with the project owner, not a
       generator bug.
5. **Done. Digital twin generalization** — consumes the Session 3 generated module directly,
   replacing `configure_i2c_wiring("wozi"|"dev")`'s 2-profile enum.

   **Session 5 done**: the twin's I2C/SPI wiring is now driven by a plain, JSON-serializable wiring
   plan instead of a hardcoded `if profile == "dev": ... else: ...` branch.
   - **`buildgen/twin_wiring.py`'s `compute_twin_wiring(model)`** (host-side, CPython, mirrors
     `buildgen/definitions.py`'s own "take an already-`build_model()`-validated `DeviceModel`, return
     a plain dict" shape) walks `model.instances.values()`, and for every `BUS_ATTACHED_DRIVERS`
     member emits `{"driver", "name_ext", "address", ["irq_pin"]}` per I2C attachment (grouped by bus
     name) or `{"driver": "fram", "name_ext", "max_size"}` per SPI bus. Two facts a `DeviceModel`
     structurally can't carry (per `buildgen.buildspec.FIXED_ADDRESS_DRIVERS`'s own "no TOML address
     field at all" rule) get a small, explicitly-named twin-side exception table instead: scd30/
     sgp40's own fixed hardware address (`FIXED_ADDRESSES = {"scd30": 0x61, "sgp40": 0x59}`, matching
     `src/asy_scd30_driver.py`'s/`asy_sgp40_driver.py`'s own hardcoded defaults - the same "a chip's
     real electrical identity has to be told, not derived" shape `driver_registry._OVERRIDES` already
     uses), and FRAM's real RDID reply bytes (not TOML-visible at all - only `max_size` is;
     `digital_twin/machine.py`'s `_FRAM_RDID_BY_MAX_SIZE` keys the one currently-known non-default
     RDID, dev's 256KB MB85RS2MTA, by size as the best available proxy, falling back to `FramChip`'s
     own default RDID for every other size - flagged as a real, narrow limitation rather than
     silently assumed exact).
   - **`digital_twin/machine.py`**: `configure_wiring(plan)` is the new generic entry point (replaces
     `_wire_i2c_devices()`'s/`_wire_spi_device()`'s own profile branch with a plan-driven dispatch
     over a small hand-maintained `driver -> chip fake class` table, `_build_i2c_chip()` - the one
     part of this mechanism that can't be auto-derived, matching the project owner's own "a
     genuinely new chip type still needs someone to hand-write its digital-twin chip fake" carve-out
     for every driver already in play today: scd30/sgp40/bmp3xx/fram, so none needed writing here).
     `configure_i2c_wiring("wozi"|"dev")` becomes pure sugar over `configure_wiring()`, fed from a
     `_LEGACY_WIRING_PLANS` table kept as plain literal data (not derived by calling `buildgen` at
     import time - this module runs under the MicroPython Unix port, which has no `tomllib` at all).
     `tests_scripts/test_buildgen_twin_wiring.py` cross-checks `compute_twin_wiring()` against that
     literal table for both real devices, so the two can never silently drift apart.
   - **`digital_twin/run_generic_integration.py`** (new): boots any `sensortask_<device>` module -
     most usefully a freshly-`buildgen.generate.generate_device()`-generated one written to disk by
     the caller first - against a `--wiring-plan` JSON file, resolving it via `__import__(--module)`
     rather than a static `import sensortask_wozi`. Its `_collect_chips()` is the generalized form of
     `run_wozi_integration.py`'s/`run_dev_integration.py`'s own hardcoded
     `{"scd30": sensortask_wozi.i2c0._i2c.devices[0x61], ...}` fault-injection lookup dict (this
     mission's item 4): it walks the same wiring plan `configure_wiring()` was given and resolves
     each attachment's own bus variable on the booted module by name. A driver with more than one
     instance on one device (e.g. `novel_combo.toml`'s two `scd30`s) is reachable unambiguously only
     via its own `driver_nameext` key; the plain driver-name key still exists too (first instance
     wins), since `launch.py`'s `parse_fault_spec()`/`parse_hang_spec()` (reused unchanged here, per
     `digital_twin/README.md`'s own "deliberately reused, not reimplemented" convention) only ever
     speak the plain-driver-name vocabulary and can't address one specific instance among several at
     all - a real, narrow limitation of the *fault-injection CLI*, not of the wiring mechanism itself.
   - **Design decision (this mission's item 3 - resolved, not left open)**:
     `run_wozi_integration.py`/`run_dev_integration.py` stay exactly as they were - thin,
     device-specific wrappers that keep booting the hand-written `sensortask_wozi.py`/
     `sensortask_dev.py` - rather than being rewritten onto the new generic mechanism. Reasoning:
     they're still Session 6's to retire (see below), still the actual driver behind
     `scripts/run_digital_twin_ci.sh`'s 11-run CI suite and dozens of `tests/test_digital_twin_*.py`
     files, and every one of those already passes today - touching either file for a generalization
     whose whole point is *not* to be device-specific would be a pure regression risk for zero
     payoff. `digital_twin/launch.py` is left alone for the same "different, static-demo use case"
     reason its own module docstring already gives (a `src/`-free raw-bus-read demo, no
     `sensortask_*` import at all - never in scope for this mission's "2-profile enum" target). The
     generalization instead landed as one new, genuinely generic sibling
     (`run_generic_integration.py`) that reaches **beyond** wozi/dev - proven directly against both
     real devices' own freshly-generated modules *and* the two mandatory synthetic fixtures
     (`novel_combo.toml`, `multi_instance.toml` - Session 3's own proof-of-generality pair), a wider
     device set than either hand-written entry point ever covered.
   - **Correctness proof, at the depth this mission actually asked for**: Session 3's own
     "correctness proof depth" note stopped at `ast.parse()` - generated code was never actually
     *run*. `tests_scripts/test_digital_twin_generated_boot.py` closes that gap: it generates a
     device (via `buildgen.generate.generate_device()`), writes the module source and a
     `compute_twin_wiring()`-derived JSON plan to a temp dir, spawns the real MicroPython Unix-port
     binary running `run_generic_integration.py` against them (same subprocess-over-real-HTTP pattern
     `scripts/_digital_twin_ci_suite.py` already uses for the hand-written wozi module), and asserts
     a real `GET` against five real REST endpoints all return 200 - for all 6 real devices (`wozi`,
     `dev`, `arzi`, `klkizi`, `grkizi`, `schlafzi`) plus the `novel_combo`/`multi_instance` synthetic
     fixtures - the full "ideally every" bar this mission's own write-up set, not just the two real
     devices with a hand-written `sensortask_*.py` to fall back on. This is the first point in the
     whole initiative a generated module has ever actually booted and served real traffic, not just
     parsed.
   - **A real bug this proof depth actually caught, and fixed**: every generated module crashed on
     boot with `AttributeError: 'AsyFramManager' object has no attribute 'get_task_starters'` the
     first time this session's own boot test ran it - `buildgen/codegen.py`'s `_emit_collectors()`
     put every constructed module, `fram` included, into the same `modules` list used by all four
     collector loops (`_collect_error_sources`/`_collect_level_setters`/`_collect_task_starters`/
     `_collect_timer_starters`) uniformly. `AsyFramManager` genuinely has no `get_task_starters()`/
     `get_timer_starters()` at all (a synchronous flash-backed store owns no `asyncio` task or
     `Timer` of its own) - confirmed directly against `src/asy_fram_manager.py`'s own method list,
     and against every hand-written `sensortask_wozi.py`/`sensortask_dev.py`, whose own
     `_collect_task_starters()`/`_collect_timer_starters()` already exclude `fram` from exactly
     those two loops while still including it in the error-source/level-setter ones. Fixed by
     computing a second `task_timer_modules` list (the same `modules` list, minus `fram`'s own
     instance variable when a `fram` instance exists) and using it for just those two loops -
     `_collect_error_sources()`/`_collect_level_setters()` are unaffected. This is exactly the kind
     of bug `ast.parse()`-only correctness proof structurally cannot see (the generated syntax was
     always valid Python; only actually *running* `main()` reaches the broken call), and exactly why
     this session's mission specified running generated code, not just parsing it. Landed as a
     forced, minimal, narrowly-scoped fix to `buildgen/codegen.py` itself - not a workaround in
     `digital_twin/`, and not deferred - per this plan's own "forced cascade, not an early attempt
     at [a later session's] job" precedent (see Session 6's own entry below for where that phrase
     first appears): fixing it was required to deliver this session's own actual mission
     (proving generated code boots), and every one of Session 3's/Session 4's own existing tests
     (golden-file comparisons, shape validation, the synthetic-fixture generation checks) still pass
     unchanged - confirmed directly, not assumed.
   - **Not built here** (flagged, not silently absorbed, per the merge-back checklist): wiring this
     generalized boot path into `scripts/run_digital_twin_ci.sh`/CI, extending that CI suite's own
     11-run matrix to `dev`/generated devices, or retiring `run_wozi_integration.py`/
     `run_dev_integration.py`/`sensortask_wozi.py`/`sensortask_dev.py` outright - all explicitly
     Session 6's ("Build chain + CI matrix") job per this plan's own session breakdown, and its
     "Testing" design decision already anticipates the exact shape this session's own
     `test_digital_twin_generated_boot.py` proves works: *"only the device-specific slice (generated
     wiring module, generated website definitions, digital-twin boot of that config) runs once per
     device in CI."* A genuinely new digital-twin chip fake was not needed either - every driver in
     play across the 6 real devices and both synthetic fixtures (`scd30`/`sgp40`/`bmp3xx`/`fram`)
     already had one. **One real, narrow limitation flagged rather than fixed**: `machine.py`'s
     `_current_scd30_chip`/`flush_scd30()` (and the equivalent FRAM pair) are single-chip globals -
     a device with more than one SCD30 instance (both synthetic fixtures) only ever persists the
     *last-wired* one's NVM settings across a simulated reboot; every other twin behavior for such a
     device is unaffected (proven directly by `test_digital_twin_generated_boot.py`'s own boot+REST
     smoke test), and a real multi-instance-persistence fix is out of this mission's own scope
     (nothing in BUILD_CHAIN_PLAN.md ever asked for it, and no real device needs it today).
6. **Build chain + CI matrix + `build/` artifact directory.** **Flagged by Session 3's merge-back
   review, per the checklist above:** Session 3 was scoped not to touch `src/sensortask_wozi.py`/
   `sensortask_dev.py`, and did not delete or replace them — but its Phase 5 change to
   `SGP40_Reader.__init__` forced a call-site update in both (one construction call each,
   `comp_source` → the four per-value arguments). That is a forced cascade, not an early attempt at
   this session's job; treat both files as still fully yours to replace, and question the shape
   rather than inheriting it. Same session also reflowed `scripts/build_firmware.py`'s module
   docstring under CLAUDE.md's 3-line header cap — docstring text only, no functional change.
7. **Versioning** — firmware + website, both starting at "2.0b0".
8. **Closing consistency pass** — bird's-eye scan across everything sessions 1-7 touched; confirm
   zero device-specific content remains outside the 6 TOML files.

Every session works on its own branch off `claude/automated-build-chain-nuzumw` (this branch), not
`main`, and opens its PR against this branch. This branch merges into `main` only once every
session has landed and the whole chain is verified end-to-end.

## Merge-back review checklist

Applied, rigorously and step by step, to every spun-off session's PR before it merges into this
branch — not a one-time check, repeated on every incoming merge:

1. **Reasonableness/efficiency/expectations** — does the result actually match what that session
   was scoped and primed to do, and is it a sensible, non-bloated way of doing it?
2. **Scope leakage** — did the session implement something that properly belongs to a *different*
   (usually later) session, whether to reach a self-contained working result or by
   misunderstanding its own scope boundary? If so, note it here and explicitly flag it to that
   later session when it's spun off — not as "this is already done, keep it," but as "question
   whether this is actually the right way and adapt if required." A later session inheriting
   earlier work must not blindly accept it just because it's already there.
3. **CI-fix legitimacy** — if a session's own PR had to fix a CI failure, confirm the fix landed in
   the actual source, not by weakening or working around the test. A test changed because the
   source legitimately changed is fine, but only if the test isn't made less strict in the
   process.

## `main` merged in (2026-09-11)

While this initiative was running, `main` independently landed a large code-quality hardening pass
(ruff moved to `select = ["ALL"]` with a real tool-version bump, mypy went to full `--strict` across
all three passes, lint/typecheck scope extended to `boot_entry/`, `toolchain/`, `scripts/`,
`tests_scripts/` and `tests_hardware/`'s own host-CPython code, shellcheck/actionlint/zizmor added
as their own CI stages) plus the MicroPython pin moving to 1.29.0. `main` was merged into this
branch to bring the initiative's own work under the same bar rather than letting it drift stale —
conflicts were resolved favoring `main`'s newer conventions throughout (its CI job split, its
`host_typecheck.ini` — the renamed, generalized successor to `buildgen/`'s own
`hosttools_typecheck.ini`, now also covering `tests_hardware/`'s host-side pytest code — its
`TomlDoc`-shaped generic-type strictness), while every build-chain-specific decision from Sessions
1-3 (the 5-element `_WIRING` comment-tag shape, per-value SGP40 wiring, per-instance naming, the
per-device hotspot password) stayed in place unchanged. `buildgen/` itself needed real fixes to
clear the new bar (not just merge-resolution): `generate_module_source()` decomposed into six
smaller `_emit_*` functions to clear mypy's/ruff's complexity ceiling, every internal `assert`
converted to a proper `raise BuildError(...)` (this package's own established fail-loud
convention), and `tests_scripts/conftest.py`'s `load_script_module()` helper split out to a new
`tests_scripts/_script_loader.py` module — `host_typecheck.ini` needs both `tests_hardware/` and
`tests_scripts/` on its `mypy_path` for their own bare sibling imports, and each directory's own
`conftest.py` can't both resolve to the same bare `conftest` module name in one mypy run (mypy
resolves each bare name to exactly one file per invocation, the same constraint that already
justifies `digital_twin/typecheck.ini`'s own separate pass) — moving the one thing that actually
needed `tests_scripts/conftest.py` to resolve bare eliminated the only real reason for the
collision; see `host_typecheck.ini`'s own `exclude` comment for the small, accepted coverage gap
this still leaves (that one file's own two trivial fixtures go unchecked by this pass).

## Build/generator script quality bar

Binds every session that writes build/generation logic — Session 3's Python code generator (which
validates a device's TOML against Session 1's own `_WIRING`/`instance_name()` runtime mechanism;
Session 1 itself builds only that mechanism, not a validator — no device TOML exists yet at that
point, so there's nothing to validate), Session 4's website `definitions.json` generator, and
Session 6's CI orchestration around them. Distinct from the sensor-code quality bar in one key way:
a build script's job includes catching every way its own input could be wrong, and refusing to
proceed rather than degrading:

- **Detect and react to every error class that would make a real build impossible** —
  misconfigured/malformed TOML, an unresolved wiring reference, a driver-class/type mismatch, a
  REST/config-name collision with no disambiguating extension, a missing required pin/bus field, a
  missing or incomplete mandatory-infra field in `[device]` (`conn_fail_to_hotspot`/
  `hotspot_time_min`, required, not defaulted — see "Device TOML schema" above), a copy-paste
  duplicate, or any other structurally broken definitions file. Typical
  real-world causes: misconfigured definition files, and plain wrong/missing/copy-pasted fields.
- **Global-resource-collision checks are their own error class and must not be skipped.**
  Overlapping bus addresses, double-claimed pin numbers, and any other double-definition of a
  resource meant to be exclusive are *syntactically valid, individually valid-looking fields that
  are still wrong in the whole-file view* — they can only be caught by a cross-instance pass over
  the entire device, never by validating one field at a time. Concretely:
  - **Schema shape**: model each bus (`i2c0`/`i2c1`/`spi0`-style peripheral instantiation) as its
    own top-level entry owning its own shared wire pins (SCL/SDA, SCK/MOSI/MISO), separate from
    each instance's own *exclusive* resources (its address on that bus, its CS pin, its IRQ pin) —
    mirrors how the real code already builds a bus once and passes it into each device
    constructor. This lets the validator use schema shape to tell "shared by design" apart from
    "must be exclusive," rather than guessing per field.
  - **Global GPIO-pin exclusivity**: one flat namespace across the whole device — every bus's wire
    pins, every instance's CS pin, every instance's IRQ pin, every standalone peripheral pin
    (Neopixel data, any future direct-GPIO driver). A physical pin wired to two different signals
    is always an error, regardless of what role either signal plays.
  - **Per-bus address exclusivity**: scoped, not global — two instances on the *same* bus can't
    share an address, but the same address value on two *different* buses is legitimate and must
    not false-positive. Covers both an explicit `address` clash and two hardwired-address instances
    of the same chip type sharing a bus with no way to distinguish them at all — itself a real,
    catchable misconfiguration even with no `address` field involved.
  - **Instance name collision** — two instances resolving to the same
    `instance_name(driver_base, name_ext)` (C.14.1) is this same category's naming-namespace case.
  - **Any other single-owner resource claimed twice** — a bus id (`bus.i2c0`) defined more than
    once, or an `[instance.wiring]`/`_WIRING` field naming an instance that doesn't exist or is the
    wrong driver type (a specific case of "unresolved reference"/"type mismatch" above, restated
    here for completeness of this category).
  Every one of these must produce a specific, human-readable error naming the two colliding
  declarations (which instance/bus, which field, which value) — never a generic "build failed" and
  never a silent pick of one over the other.
- **A wiring reference (`temperature_source`, `humidity_source`, `signal_sink`, `fram_target`,
  `led_target`, every `[instance.wiring.<name>]`/`[device.wiring]` field) resolves against the TOML's own
  `driver`+`name_ext` identity — never against `instance_name()`/each driver's own `_NAME`
  constant, and the two must never be conflated.** These are two unrelated naming spaces: the TOML
  identifier is the literal `driver` string as written (`"notification"`, `"scd30"`, ...) plus
  `_<name_ext>` when set; `instance_name()`'s result (REST dict keys/config filenames/error-log
  keys, C.14.1) is built from the driver's own `_NAME` module constant instead, which is **not**
  reliably `driver.upper()` — confirmed directly: `asy_notification_service.py`'s `_NAME =
  const("NOTIFY")`, not `"NOTIFICATION"`. A generator that resolved a wiring string by matching it
  against `instance_name()` output would silently fail to resolve exactly this case. The correct
  (and only sound) implementation: the generator already builds a `(driver, name_ext) ->
  constructed instance` map to instantiate every `[[instance]]` entry in the first place: a wiring
  reference resolves against that same map, purely at build time, and hands the consumer the
  already-constructed Python object directly — `instance_name()`/`_NAME` never enters wiring
  resolution at all, since it exists to serve a completely different concern (what the running
  firmware calls that instance over REST).
- **Driver-declared bus requirements are enforced via a `# @requires` comment tag, never a real
  Python variable.** A driver whose correctness depends on a property of the bus it's wired to
  (e.g. `asy_scd30_driver.py`'s clock-stretch timeout requirement — today only satisfied by hand,
  per device TOML) declares it as a module-level comment, not a module-level constant: nothing the
  running firmware itself ever reads should become a real frozen-bytecode value just to serve this
  generator — the same reasoning behind `BACKLOG.md`'s `@web`/`@web-group` website-definitions
  sketch, whose tag-family convention this reuses rather than inventing a second one. Grammar: `#
  @requires bus.<field><op><value>` (e.g. `# @requires bus.timeout>=200000`), placed at module
  level near `_WIRING`/`_VAL_*`. The generator parses driver source files as text for these tags
  (never imports+introspects for this), resolves the instance's own `bus = "..."` TOML reference to
  its `[bus.*]` table, and evaluates the tag's predicate against that table's actual field value —
  silently continuing if satisfied, failing loudly (naming the device, instance, bus, field, and
  expected-vs-actual value) if not, the same as every other check in this section.
- **Every driver-declared fact the running firmware never reads is a comment tag, not a Python
  value** (project owner's ruling, 2026-09-10, restating the rule the `@requires` bullet above
  already stated). The question was raised against `_LIMITS`, whose defence was that it is
  structured data with a natural Python home; the ruling is that the original rule holds and the
  subject matter of the fact doesn't change it. Applied consistently, it caught three declarations,
  all now converted:
  - `_WIRING` → `# @wiring <toml_field> <ProducerClass> <target> <required|optional>
    <kwarg|attr|setter>`
  - `_VALUE_WIRING` → `# @value-wiring <toml_field> <source_kwarg> <field_kwarg>
    <required|optional>`
  - `_LIMITS` → `# @limits <field> <min>..<max>` or `# @limits <field> in {a, b}` (`*` on either
    side of a range means that side is unchecked; `min == max` is an exact-value requirement)

  Confirmed by direct grep before converting: none of the three had a single runtime read anywhere
  in `src/`. What the rule does **not** catch is a `_Default<Field>` class — the generated module
  imports and constructs those (`_DefaultHumiditySource(relative_humidity=35)`), so they are live
  code, not metadata, and stay Python. The generator still reads their `__init__` signature by AST,
  but that is reading real code's shape rather than a constant planted for it to find.

  Measured, so the payoff is on record rather than assumed: the three tuples plus the
  `TYPE_CHECKING` type aliases that described them (`WiringSchema`/`LimitsSchema`/
  `ValueWiringSchema`, real compiled statements on-device since `TYPE_CHECKING` is `False` at
  runtime) came to **3,576 bytes** of `src/`'s frozen bytecode, about 2.6% of it. Two imports went
  with them — `asy_notification_service.py` and `asy_wifi_service.py` each imported
  `NeopixelDriver` solely to name it in `_WIRING` — with no change to any device's computed frozen
  module set, confirmed by regenerating all six.

  What a comment costs in exchange is that the interpreter validates nothing: a typo'd or partial
  tag is invisible unless something looks for it. That is what `buildgen/tag_comments.py` is for,
  and why every family registered there carries its own payload-shape predicate — a single shared
  heuristic goes blind on whichever shape it wasn't written for, which is the exact silent miss
  the mechanism exists to prevent.
- **Standing rule for every tag in this comment-tag family (project owner's explicit direction, not
  scoped to `@requires` alone): a tag that's present, or close to present with a typo, must be
  verified correct in every dimension — exact wording, location, format, content, validity — or
  fail the build loud, never be silently treated as "no tag here, nothing to check."** A comment
  isn't Python the interpreter validates for you; a driver author can misspell `@requires` as
  `@require`, drop the `bus.` prefix, use a bare `=` instead of `==`, or bury the tag inside a
  method body where it's no longer "near the schema" it's meant to describe — every one of those
  must raise a `BuildError`, the same as a real malformed field would. `buildgen/tag_comments.py`
  is the shared mechanism (`KNOWN_TAG_NAMES` registry, tokenize-based comment scanning so a `#`
  inside a string/docstring is never mistaken for a real comment, edit-distance typo matching, and
  a payload-shape gate so ordinary prose that happens to mention a tag's name isn't misflagged) —
  `buildgen/requires_tag.py` is built on it today; whichever session eventually builds the
  `@web`/`@web-group` website-definitions parser (`BACKLOG.md`'s sketch) must build on the same
  module, not reinvent a second, less-tested detector. Each tag-family's own unit tests must cover
  the whole matrix, not a sample of it, split by which side of the accept/reject line a case sits
  on. **The accept side carries the full dimensionality** — every operator against every value
  shape, every legal spacing variant, every legal placement, and none/one/several tags per file —
  because a build that silently accepts the wrong thing is the exact failure the tag exists to
  prevent. **The reject side covers each dimension once and does not recombine** — an abort is an
  abort, so a typo'd tag name crossed with a wrong operator proves nothing the two separate cases
  don't. The dimensions to walk: *wording* (the name typo'd by an insertion, deletion, substitution
  or transposition, mis-cased, or with the `@` sigil dropped outright, plus the edit-distance
  boundary just outside tolerance, which must stay silent), *format* (each structural piece
  individually wrong — missing `bus.` prefix, bare `=`, operator dropped, value dropped, trailing
  junk), *location* (indented into a class or method body, or onto a bracketed continuation line),
  *content* (a value that isn't a number), *validity* (each operator satisfied **and** violated
  against a real bus table, plus a missing field, a falsy-but-present value, and a non-comparable
  type), *scanning* (tag-shaped text inside a string or docstring, an unreadable file encoding, an
  unparseable file — the last two must fail as a `BuildError`, never a raw traceback), and — the
  false-positive checks that make the whole mechanism trustworthy — realistic prose that merely
  mentions the tag's name and an unrelated `@`-word, neither of which may raise. Every dimension
  above also has to be walked in the *dropped-piece* direction, not just the *wrong-piece* one: the
  three holes this bar's own first implementation still had (a dropped operator, a dropped value,
  and a dropped `@`, each silently parsing to "no tag declared") were only found by enumerating the
  grammar element by element and deleting each in turn. `tests_scripts/test_buildgen_tag_comments.py` and
  `tests_scripts/test_buildgen_requires_tag.py` are the concrete reference implementation of this
  bar - motivated by the same failure pattern (not the same mechanism) as a real incident earlier in
  this session: an actual driver signature change silently broke two `tests_hardware/device_scripts/`
  call sites for a full day, undetected only because nothing in that scope was ever checked at all.
  A malformed comment-tag silently parsing to "no tag declared" is the same class of risk one layer
  down - present-but-wrong content that nothing verifies.
- **Never produce a corrupted or partial build.** On any detected error, abort the entire build
  immediately — no partial `build/<device>/` output left behind that could be mistaken for a real
  artifact.
- **Fail loudly, clearly, and human-readably.** A plain, actionable message naming exactly what's
  wrong and where (which device, which instance, which field) — not a raw traceback, not a silent
  wrong-default fallback. This is the build-tooling equivalent of CLAUDE.md's "flag, don't silently
  change" convention.
- **Tested to the same bar as `src/` code**: correct-path functioning, full error-handling-path
  coverage (every abort condition above gets its own test, driven by deliberately malformed
  fixture definition files — not just incidentally exercised by the six real device TOMLs
  happening to be valid), and code coverage. Follows the already-established `tests_scripts/`
  convention (pytest, real CPython — CLAUDE.md's "Code quality tooling" section already documents
  this as the home for host-only build-tooling tests, distinct from `src/`'s real-MicroPython-
  interpreter suite) rather than inventing a new test harness.
- Newly-built generator/validator modules join `pyproject.toml`'s ruff/mypy scope alongside
  `src/`/`tests/`/`digital_twin/` — this is fresh code, not pre-existing legacy `scripts/`/
  `toolchain/` tooling, so it starts under the full quality bar rather than inheriting CLAUDE.md's
  documented (and still separately-decided) gap for that legacy tooling.

This is the same "each module/function tested exactly one time" CI principle already agreed,
applied to error-handling paths specifically: a build/generator function's abort conditions are
themselves testable units, not just incidentally covered by the real device TOMLs happening to be
valid.
