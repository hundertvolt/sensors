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

The shape every device's TOML file follows once Session 2 writes the real ones. Not itself
authoritative production config — an illustrative, heavily-commented example, kept here since this
doc is this initiative's own shared, living reference (its own front matter: "update it as
decisions evolve"). References the mechanism `src/` now has after Session 1 (`config_manager.py`'s
`instance_name()`, `WiringSchema`; `base_classes.py`'s `name_ext`/`get_error_sources()`/
`get_loggers()`; each driver's own `_WIRING` — see `SPECIFICATION.md` Part C.14 for the full
mechanism reference).

Two top-level shapes: a single `[device]` table (identity/network facts, not repeated) and a
uniform `[[instance]]` array of tables. **The TOML models optional modules only** — driver-level
sensors, plus singleton services that themselves vary per device or could someday be entirely
absent: FRAM (`sensortask_wozi.py`'s is an 8KB `MB85RS64V` on `spi0`/cs `1`; `sensortask_dev.py`'s
is a 256KB `MB85RS2MTA` on a differently-pinned `spi0`/cs `5` — a real per-device fact), Neopixel
(its own data pin varies per device), NotificationCoordinator (today wired to a Neopixel in every
real device, but a genuinely optional software capability a future device could lack or wire to a
different sink entirely).

**WiFi, NTP, and SystemService are mandatory infrastructure and are never `[[instance]]`
entries** (project owner's explicit direction, 2026-09-09, revising this doc's own earlier draft,
which had modeled them as instances too — corrected before it ever reached a real device TOML).
Every buildable device has all three unconditionally: there is no real variant that omits network
connectivity, time sync, or the task supervisor/watchdog, so — unlike a sensor or an optional
peripheral — there is no presence-or-absence question for the schema to encode. Their own
per-device-tunable knobs (today: WiFi's `conn_fail_to_hotspot`/`hotspot_time_min`; NTP/SystemService
have none) live instead in one top-level `[system_config]` table, **required, not defaulted**: a
device TOML missing either field is a build-time error, the same fail-loud contract "Build/
generator script quality bar" below gives every other structurally-broken-definitions-file case.

The same reasoning is why the webserver — also unconditional, present on every device — was never
modeled as an instance either, even before this revision: its own constructor takes no independent
per-device facts at all, only references to whichever other instances the TOML already declares
(`WebserverService(app, sensors=(scd_reader, bmp_reader, sgp_reader), settings=[...])`-style
composition over the already-resolved instance graph) — there was never anything for a
`[[instance]]` entry to carry for it in the first place.

A device variant that lacks a given *optional* singleton (if one ever does) simply omits that
`[[instance]]` entry — the same absence-means-absent handling a missing sensor already gets. This
does not extend to WiFi/NTP/SystemService, which are never optional and never omitted.

```toml
# example-device.toml - illustrative shape only (Session 2 writes the 6 real files: dev, wozi,
# arzi, klkizi, grkizi, schlafzi - see this doc's own "Target device variants").

[device]
# "SensorStation<name>" is the base stub (CLAUDE.md/this doc's own "Core design decisions") - this
# field supplies just the <name> part.
name = "Wozi"
# Default hostname AND the hotspot AP's own SSID (src/asy_wifi_service.py's essid=hostname - no
# separate SSID field exists or is needed, confirmed directly against that module).
hostname = "SensorStationWozi"
# Per-device hotspot AP password (src/asy_wifi_service.py's HotspotPW config field, added this
# session) - defaults to the existing hardcoded "12345678" if omitted (CLAUDE.md's accepted-risk
# credential note); a device TOML may override it, but never needs to.
hotspot_password = "12345678"

# Mandatory infrastructure tuning - WiFi/NTP/SystemService are never [[instance]] entries (every
# buildable device has all three unconditionally; see this doc's "Device TOML schema" intro above
# for the full reasoning). Required, not defaulted: a device TOML missing either field below is a
# build-time error (this doc's own "Build/generator script quality bar" fail-loud contract).
[system_config]
conn_fail_to_hotspot = 5   # src/asy_wifi_service.py's AsyWifiService constructor param, same name.
hotspot_time_min = 8       # ditto. NTP/SystemService have no tunable fields today, so nothing of
# theirs lives here yet - this table only ever grows if/when they do.

# One table per bus an [[instance]] entry below can reference by id. Every I2C/SPI pin, frequency,
# and per-bus timeout override lives here - no hardcoded pins anywhere in generated or
# hand-written driver-wiring code (this doc's own "Core design decisions").
[bus.i2c0]
scl_pin = 13
sda_pin = 12
frequency = 50000
# SCD30-specific: up to 150ms/day clock stretching, past rp2's 50ms default (SPECIFICATION.md Part
# A.7) - a per-bus override, not a per-instance one, since it's a property of what shares this bus.
timeout = 200000

[bus.i2c1]
scl_pin = 19
sda_pin = 18
frequency = 50000

[bus.spi0]
sck_pin = 2
mosi_pin = 3
miso_pin = 4
# No cs_pin/frequency here: cs_pin is each instance's own *exclusive* resource (see this doc's own
# "Build/generator script quality bar" schema-shape requirement below - a bus table owns only its
# shared wire pins), and asy_spi_driver.SPI has no frequency parameter at all (confirmed directly
# against src/asy_spi_driver.py's own SPI.__init__/init()) - unlike asy_i2c_driver.I2C, which does
# and so every [bus.i2c*] table above does carry one. Session 2 found this exact duplication (a
# stray cs_pin = 1 sitting in both this table and the fram instance below) in an earlier draft of
# this same illustrative example and corrected it here rather than carrying the inconsistency into
# the 6 real files at devices/*.toml.

# --- sensor drivers (SensorReader/SensorReaderConfig subclasses - can repeat) ---------------

[[instance]]
driver = "scd30"           # maps to a real driver class the generator resolves statically -
# never a dynamic import (SPECIFICATION.md Part F.1). Per this doc's own "Acceptance criteria"
# above, this resolution should be derived from the existing asy_<name>_driver.py -> <Name>_Reader
# naming convention (SPECIFICATION.md Part C.5), not a separate hand-maintained lookup table -
# not built in this session.
name_ext = ""               # optional, default "" - instance_name()'s own default-unchanged case
# (SPECIFICATION.md Part C.14.1): produces the plain "SCD30" REST/config/error-log key. Every
# driver kind that can have more than one instance per device accepts this field; a singleton
# service kind (see below) doesn't declare it at all.
bus = "i2c0"
irq_pin = 8
trigger_sec = 3
# No `address` field: SCD30 has no logically-selectable I2C address (hardwired per
# datasheets/scd30/..._Interface_Description.pdf) - only a chip with a real address-select
# mechanism gets this field (see bmp3xx below).

[[instance]]
driver = "sgp40"
name_ext = ""
bus = "i2c1"
# _WIRING-declared cross-instance dependency (SPECIFICATION.md Part C.14.2): names another
# [[instance]]'s own resolved name (its `driver` + `name_ext`, not a Python identifier) - the
# generator resolves this to that instance's already-constructed object and checks it's actually
# an SCD30_Reader (asy_sgp40_driver.py's own `_WIRING = (("comp_source", SCD30_Reader),)`),
# erroring at build time on a type mismatch or an unresolvable name - not built in this session.
[instance.wiring]
comp_source = "scd30"

[[instance]]
driver = "bmp3xx"
name_ext = ""
bus = "i2c1"
# BMP388/BMP390 support a real address-select pin (SDO), so this driver kind does get an address
# field - two legal values, 0x76/0x77 (datasheets/bmp3xx/...).
address = 0x77

# A second SCD30 on a different bus/pins - the multi-instance case this whole mechanism exists for
# (project owner's own "two SCD30s, or the multi-differential-pressure-sensor case" example). Its
# name_ext disambiguates every one of REST dict keys/config filename/error-log key at once
# (instance_name()'s single resolved name, threaded through all three - SPECIFICATION.md C.14.1):
# "SCD30_fan_pressure", not a second, colliding "SCD30".
[[instance]]
driver = "scd30"
name_ext = "fan_pressure"
bus = "i2c1"
irq_pin = 9
trigger_sec = 3

# --- optional singleton services (never more than one per device, but still per-device- ----------
# --- configurable, or could someday be entirely absent - see this doc's "Device TOML schema" ------
# --- intro above for why WiFi/NTP/SystemService don't belong in this list) ------------------------

[[instance]]
driver = "fram"
bus = "spi0"
cs_pin = 1
max_size = 0x2000            # MB85RS64V (8KB) here; dev's own real file uses 0x40000 (MB85RS2MTA,
# 256KB) - a real per-chip fact, confirmed directly against both existing sensortask-*.py files,
# not a hypothetical.

[[instance]]
driver = "neopixel"
pin = 15

[[instance]]
driver = "notification"

# Makes notification's dependency on a signal sink explicit in the TOML (project owner's direction,
# 2026-09-09) - today that's always the neopixel instance, but a future device might drive
# notifications a different way entirely (e.g. a network call) instead of an LED, so this is
# declared the same way sgp40's comp_source is: a plain instance-name reference, not hardcoded.
# NOT YET RESOLVABLE by the generator as specified: _WIRING's documented contract (this doc's "Core
# design decisions" above) resolves a reference to the *whole* constructed instance and passes it
# directly into the consumer's constructor, but `NotificationCoordinator.__init__`'s
# `request_signal_cb` param wants one specific bound coroutine method off that instance
# (`pixel.request_signal`, confirmed directly against src/asy_notification_service.py's own
# signature and src/asy_neopixel_driver.py's own `async def request_signal(self, r, g, b, t)`), not
# the instance itself. Whether that gets solved by extending `_WIRING`'s tuple shape with an
# optional attribute-name element, generator-side special-casing, or something else is left open -
# deliberately not settled by this session ("no refactor of notification or neopixel" scope,
# 2026-09-09); `asy_notification_service.py` itself declares no `_WIRING` tuple yet either (unlike
# `asy_sgp40_driver.py`), for the same reason.
[instance.wiring]
signal_sink = "neopixel"

# Notification's own per-signal getters (project owner's direction, 2026-09-09) - the same
# treatment as signal_sink above, extended to what was previously hardcoded inside
# notify_service.register(NotificationSignal("WarnCO2", scd_reader, "CO2", ...)) calls in
# build_system(). Confirmed directly against both code paths this TOML schema covers: the
# refactored sensortask_wozi.py/sensortask_dev.py register exactly these three
# (WarnCO2<-scd30.CO2, WarnVOC<-sgp40.VOC, WarnHum<-scd30.Hum), and the legacy
# modules/sensortask-arzi.py/sensortask-neu.py's own (differently-mechanized, pre-refactor)
# airqualMeasCallback() sources the identical three values the identical way
# (`[scd_data[_SCD30_CO2], sgp_data[_SGP40_VOC], scd_data[_SCD30_Humidity]]`) - not assumed to
# match, checked.
#
# Each one is OPTIONAL, unlike signal_sink: a device TOML may omit any of the three sub-tables
# below entirely, or reference an instance this device doesn't have. Either way the generator must
# simply not register that one notification signal on this device - disabled by default, not a
# build-time error. This is the same absence-means-absent handling this schema already gives a
# missing optional instance (see this doc's "Device TOML schema" intro above), now applied at the
# level of one instance's individual wired getters rather than the instance's own presence.
[instance.wiring.warn_co2]
source = "scd30"
field = "CO2"

[instance.wiring.warn_voc]
source = "sgp40"
field = "VOC"

[instance.wiring.warn_hum]
source = "scd30"
field = "Hum"

# Each signal's own threshold default/range and flash color (_FIELD_WARN_CO2's (0, 3000, ...)-style
# range, the (1, 0, 0)-style RGB tuple) are a related but still-separate, still-open question - not
# settled by this addition, which covers only the source+field getter half. How the generator
# expresses either from this table is Session 3's own design question.
```

**What this session settles**: the two top-level shapes above, the `[[instance]]` convention for
*optional* modules (WiFi/NTP/SystemService excluded — mandatory infrastructure, tuned instead via
`[system_config]`), `name_ext`'s default-empty-means-unchanged rule, `[instance.wiring]`'s shape (a
flat `{toml_field_name = "another instance's resolved name"}` table for a single-instance
reference, or a `[instance.wiring.<name>]` sub-table of `{source = "...", field = "..."}` for a
getter reference), that a getter-shaped wiring reference is optional and defaults to "disabled" when
absent or unresolvable (unlike a plain instance reference, which is required), and that an address
field only exists for a driver kind whose chip actually has one (checked per datasheet, not
assumed).

**What Session 2 does**: write the 6 real files (`dev`, `wozi`, `arzi`, `klkizi`, `grkizi`,
`schlafzi`) from this shape, using the wiring facts already gathered from
`src/sensortask_wozi.py`, `src/sensortask_dev.py`, `modules/sensortask-arzi.py`,
`modules/sensortask-neu.py`.

**Session 2 done**: the 6 real files live at `devices/<device>.toml` (a new top-level directory,
not specified elsewhere in this doc before now — chosen as the natural sibling of
`toolchain/versions.toml`'s own top-level-config precedent; Session 3's generator should read from
here). The six `device.name` values are `Wozi`/`Dev`/`Arzi`/`Klkizi`/`Grkizi`/`Schlafzi` (plain
capitalized device id, feeding `hostname = "SensorStation<name>"` per this doc's own convention).
Every device's `hotspot_password` is the existing accepted-risk default (`"12345678"`, CLAUDE.md) —
no device has a reason to differ. `wozi`/`dev` are the only two with a `bmp3xx` instance (confirmed
directly: neither `modules/sensortask-arzi.py` nor `modules/sensortask-neu.py` imports/constructs
one); `klkizi`/`grkizi`/`schlafzi` share byte-for-byte identical wiring (only `device.name`/
`hostname` differ), all sourced from `modules/sensortask-neu.py` alone, per this doc's own device
list. One real fact this session applied consistently that the pre-refactor legacy files couldn't:
`arzi`/`klkizi`/`grkizi`/`schlafzi`'s SCD30-carrying `i2c0` bus now gets the same `timeout = 200000`
clock-stretch headroom `wozi`/`dev` already have — the old, pre-refactor `asy_i2c_driver.py`
(`python/IndividualDrivers/asy_i2c_driver.py`) never had a `timeout` parameter at all, so its
absence in the legacy arzi/neu files was a driver limitation, not a considered decision that this
chip-level datasheet fact (datasheets/scd30/..._Interface_Description.pdf) doesn't apply there too;
`src/asy_i2c_driver.py` (what these TOML files target) does support it. **Revision, same session
(2026-09-09)**: the project owner (this doc's own author) reviewed the first draft of these 6 files
and rejected modeling WiFi/NTP/SystemService as `[[instance]]` entries — they're mandatory
infrastructure, not optional modules, so the TOML shouldn't carry them at all; see "Device TOML
schema" above for the corrected shape. All 6 files were revised to drop those three `[[instance]]`
blocks and add a `[system_config]` table (`conn_fail_to_hotspot = 5`, `hotspot_time_min = 8` —
unchanged values, just relocated) instead. A minimal shape/collision smoke-test suite lives at
`tests_scripts/test_device_tomls.py` (parses as valid TOML, matches this schema's shape — including
that `[system_config]` is present with both required fields and that WiFi/NTP/SystemService never
appear as instances — and re-implements — by hand, since no generator/validator exists yet — the
global-GPIO-pin/per-bus-address/instance-name collision checks below against these 6 real files
specifically; **not** a substitute for Session 3's own full validator and its malformed-fixture
test coverage).

**Revision 2, same session (2026-09-09)**: the project owner also asked for notification's own
per-signal getters (`WarnCO2`/`WarnVOC`/`WarnHum` — previously hardcoded inside
`notify_service.register(NotificationSignal(...))` calls in `build_system()`) wired up explicitly
the same way `sgp40`'s `comp_source` already is, plus a default-disables-the-signal behavior when
one is left unwired. All 6 files gained three `[instance.wiring.warn_co2/warn_voc/warn_hum]`
sub-tables on their `notification` instance (`{source = "scd30"/"sgp40", field = "CO2"/"VOC"/
"Hum"}`), confirmed against both the refactored and legacy source paths (see "Device TOML schema"
above for the exact evidence) — every real device declares all three today, since every real device
has both `scd30` and `sgp40`; the disables-when-absent behavior exists in the schema for a future
device that might not.

**What Session 3 (the generator) does, not settled here**: resolving the `driver` string to its
Python class — per this doc's own "Acceptance criteria" above, derived from the existing
`asy_<name>_driver.py` → `<Name>_Reader` naming convention rather than a separate hand-maintained
lookup table, falling back to an explicit table only for a driver that genuinely can't follow the
naming pattern; topologically sorting `[[instance]]` entries by `[instance.wiring]`/`_WIRING`
dependency and rejecting a cycle; erroring at build time on a naming collision with no
disambiguating `name_ext`; resolving `NotificationSignal` registrations from this table; emitting
the real `sensortask_<device>.py` + boot entry; and the full **global resource-collision
validation pass** below — every one of these is a real build blocker per the fail-loud contract
above, not a warning, and not built in this session.

**Global resource-collision validation is required of Session 3** (project owner's explicit
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
3. **Python generator** (`sensortask_<device>.py` + boot entry) — topological construction
   ordering, dependency-driven frozen-module selection, generic definitions-file-derived tests.
4. **Website `definitions.json` generator** — resolves BACKLOG.md's `@web`/`@web-group` open
   sub-questions, combined with each device's TOML instance list.
5. **Digital twin generalization** — consumes the Session 3 generated module directly, replacing
   `configure_i2c_wiring("wozi"|"dev")`'s 2-profile enum.
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
  missing or incomplete `[system_config]` table (required, not defaulted — see "Device TOML schema"
  above), a copy-paste duplicate, or any other structurally broken definitions file. Typical
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
