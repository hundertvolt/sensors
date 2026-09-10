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
- **Per-field domains — `_LIMITS`**: `buildgen.limits` AST-parses `(toml_field, constraint)`, the
  constraint either a `(min, max)` 2-tuple or a `frozenset` of exact legal ints. Only
  `asy_bmp3xx_driver.py` declares one today (`address` ∈ {0x76, 0x77}, `trigger_sec` ∈ [1, 3600],
  both from constants already in that file) — no invented bounds anywhere.
- **Wiring defaults and per-value measurement wiring**: `buildgen.defaults` AST-discovers a
  driver's `_Default<Field>` classes (the `__init__` signature *is* the schema for a
  `{default = true, ...}` TOML sub-table), and `buildgen.value_wiring` parses `_VALUE_WIRING` —
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
4. **Website `definitions.json` generator** — resolves BACKLOG.md's `@web`/`@web-group` open
   sub-questions, combined with each device's TOML instance list. **Read
   BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md first**: its §2/§2.9 (landed 2026-09-10) changed the
   device TOML shape a real device's instance list can carry (`comp_source` → independent
   `temperature_source`/`humidity_source` fields, plus the general `{default = true, ...}` opt-in
   shape now legal on any defaultable wiring field) - a definitions.json generator built against
   the pre-2026-09-10 shape would silently miss both.
5. **Digital twin generalization** — consumes the Session 3 generated module directly, replacing
   `configure_i2c_wiring("wozi"|"dev")`'s 2-profile enum. **Same pointer as Session 4 above** - the
   generated module's own construction calls now use the post-§2.9 `SGP40_Reader` signature; a twin
   boot path assuming the old one-argument `comp_source` shape will not match reality.
6. **Build chain + CI matrix + `build/` artifact directory.**
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
- **Which of the two forms a new driver-declared fact takes — a real `_`-prefixed tuple, or a
  comment tag — is decided by what the fact is *about*, not by whether the firmware reads it**
  (settled 2026-09-10, after the question was raised on `_LIMITS` specifically). None of
  `_WIRING`/`_VALUE_WIRING`/`_LIMITS`/`_Default*` is read at runtime either, so "the firmware never
  reads it" cannot be the dividing line, and the frozen-bytecode cost it points at was measured
  rather than argued: stripping `asy_bmp3xx_driver.py`'s entire `_LIMITS` tuple changes its
  `mpy-cross` output by **71 bytes** (10062 → 9991), against a >2 MB flash budget. The real line:
  - **A declaration states a property of this module's own schema** — which of its constructor
    parameters are wireable (`_WIRING`, `_VALUE_WIRING`), what domain one of its own TOML fields
    has (`_LIMITS`), what a default provider's keys are (`_Default*`). It is structured, typed,
    multi-element data that has a natural Python home right beside the schema it describes, so real
    syntax carries it: the AST parser stays trivial, ruff and mypy see it, and a malformed one is a
    `SyntaxError` the interpreter itself catches before any generator runs.
  - **A comment tag states a constraint about an object this module does not own** — the bus it
    happens to be attached to (`@requires`), the website that renders it (the planned `@web`). There
    is no module-level Python object to hang it on, so a real constant would be pure cost with no
    syntax checking to buy back, and the near-miss detector (`buildgen/tag_comments.py`) exists
    precisely because a comment gets none of the interpreter's own validation for free.
  So `_LIMITS` stays a tuple, and a future per-field domain belongs there too; a future
  cross-object predicate (a second bus property, a display/website fact) is a tag, built on
  `tag_comments.py` rather than on a second detector.
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
