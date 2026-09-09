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
- **Build-time tooling (the generator, `definitions.json` builder, and any other build-chain
  script — Sessions 3/4/6) gets a fundamentally different error-handling contract than the
  runtime sensor/service code it emits (project owner's explicit direction, 2026-09-09).** Runtime
  `src/` code degrades gracefully and never raises (SPECIFICATION.md Part D.2) because a device
  has to keep running unattended for years — a build script has no such constraint and must do the
  opposite: **detect any error that would make a correct build impossible — a misconfigured
  definition file, a wrong/missing/copy-pasted TOML field, an unresolvable `_WIRING` reference, a
  naming collision with no disambiguating `name_ext`, a dependency cycle, anything structurally
  invalid — and abort the whole build immediately, never emitting a partial or corrupted result.**
  Every such abort must fail loudly: a clear, human-readable message naming the specific device
  variant, the specific TOML file/field/line at fault, and what's wrong with it — never a bare
  traceback or a silent skip. A build script that "degrades gracefully" past a real configuration
  error is a bug, not a feature — the entire point is that a bad config must never silently produce
  firmware/a website that looks fine but doesn't match its own TOML.
  **Every build function needs its own unit test suite** (this is host-side CPython/pytest tooling,
  matching `tests_scripts/`'s existing precedent — Part E.1's "real MicroPython interpreter"
  rationale is about `src/`-target code specifically and doesn't apply here), covering: correct
  output for valid input, and — the harder, more important half — that every documented error case
  above is actually detected and produces the specific abort/message it's supposed to, not just
  "doesn't crash." Aim for real coverage of the error-handling paths themselves (via
  `scripts/test.sh --coverage`'s existing pipeline, Part E.5), not just the happy path — an
  untested error branch is exactly the kind of thing that silently stops firing the day the code
  around it changes. Each session building a piece of this tooling (3, 4, 6) owns writing this test
  suite as part of that session's own "done" criteria, the same TDD-first step-session workflow
  CLAUDE.md already requires.

## Device TOML schema (Session 1 deliverable — shape only, not the 6 real files)

The shape every device's TOML file follows once Session 2 writes the real ones. Not itself
authoritative production config — an illustrative, heavily-commented example, kept here since this
doc is this initiative's own shared, living reference (its own front matter: "update it as
decisions evolve"). References the mechanism `src/` now has after Session 1 (`config_manager.py`'s
`instance_name()`, `WiringSchema`; `base_classes.py`'s `name_ext`/`get_error_sources()`/
`get_loggers()`; each driver's own `_WIRING` — see `SPECIFICATION.md` Part C.14 for the full
mechanism reference).

Two top-level shapes: a single `[device]` table (identity/network facts, not repeated) and a
uniform `[[instance]]` array of tables — **every** constructed module is an instance, not just
sensor drivers: a singleton service (WiFi, NTP, SystemService, FRAM, Neopixel,
NotificationCoordinator) still varies per device by its own pin/bus/chip-size facts (confirmed
directly: `sensortask_wozi.py`'s FRAM is an 8KB `MB85RS64V` on `spi0`/cs `1`; `sensortask_dev.py`'s
is a 256KB `MB85RS2MTA` on a differently-pinned `spi0`/cs `5` — a real per-device fact, not a
sensor-only concern), so there is no second, special-cased declaration mechanism for "the modules
every device always has." A device variant that lacks a given singleton (if one ever does) simply
omits that `[[instance]]` entry — the same absence-means-absent handling a missing sensor already
gets.

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
cs_pin = 1

# --- sensor drivers (SensorReader/SensorReaderConfig subclasses - can repeat) ---------------

[[instance]]
driver = "scd30"           # maps to a real driver class the generator resolves statically -
# never a dynamic import (SPECIFICATION.md Part F.1) - e.g. via a small, hand-maintained
# driver-name -> class table, not built in this session.
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

# --- singleton services (never more than one per device, but still per-device-configurable) -----

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
driver = "wifi"
conn_fail_to_hotspot = 5
hotspot_time_min = 8

[[instance]]
driver = "ntp"

[[instance]]
driver = "system"

[[instance]]
driver = "notification"
# NotificationSignal registrations (WarnCO2/WarnVOC/WarnHum today) are a related but separate
# mechanism from _WIRING (SPECIFICATION.md C.14.3) - resolved at register()-call time, after every
# producer already exists, so they don't need their own _WIRING declaration; how the generator
# expresses "register WarnCO2 against the scd30 instance's CO2 field" from this table is Session
# 3's own design question, not settled here.
```

**What this session settles**: the two top-level shapes above, the uniform `[[instance]]`
convention (singleton services included, not special-cased), `name_ext`'s default-empty-means-
unchanged rule, `[instance.wiring]`'s shape (a flat `{toml_field_name = "another instance's
resolved name"}` table), and that an address field only exists for a driver kind whose chip
actually has one (checked per datasheet, not assumed).

**What Session 2 does**: write the 6 real files (`dev`, `wozi`, `arzi`, `klkizi`, `grkizi`,
`schlafzi`) from this shape, using the wiring facts already gathered from
`src/sensortask_wozi.py`, `src/sensortask_dev.py`, `modules/sensortask-arzi.py`,
`modules/sensortask-neu.py`.

**What Session 3 (the generator) does, not settled here**: the `driver` string → Python class
lookup table; topologically sorting `[[instance]]` entries by `[instance.wiring]`/`_WIRING`
dependency and rejecting a cycle; erroring at build time on a naming collision with no
disambiguating `name_ext`; resolving `NotificationSignal` registrations from this table; emitting
the real `sensortask_<device>.py` + boot entry; and the full **global resource-collision
validation pass** below — every one of these is a real build blocker per the fail-loud contract
above, not a warning, and not built in this session.

**Global resource-collision validation (Session 3, required — project owner's explicit direction,
2026-09-09)**: the single hardest class of build-time error to catch, because each individual field
involved is independently syntactically valid — the corruption only exists in the *combination*,
across the whole device's TOML, not in any one `[[instance]]`/`[bus.*]` table read in isolation. A
schema-level check (right type, right range) can't see this at all; it needs a dedicated pass that
builds a flat map of every physical resource a device's TOML claims and rejects any resource
claimed twice. At minimum:
- **Pin reuse across *anything*** — two `[[instance]]`/`[bus.*]` entries naming the same GPIO for
  any purpose (an SCL/SDA/SCK/MOSI/MISO/CS pin, an IRQ pin, the Neopixel pin, an LED pin, ...),
  including a bus's own pins colliding with a *different* bus's pins or with a plain digital
  instance pin — not just two same-typed pins colliding with each other.
- **I2C/SPI address collision on the same bus** — two instances both wired to the same `bus = "..."`
  resolving to the same address (either both give the same explicit `address`, or two
  hardwired-address instances of the same chip type share a bus with no way to distinguish them at
  all — itself a real, catchable misconfiguration, not just an address-field mismatch).
- **Instance name collision** (C.14.1's own case, restated here as one instance of this same general
  category) — two instances resolving to the same `instance_name(driver_base, name_ext)`.
- **Any other single-owner resource claimed twice** — a `cs_pin` reused across two SPI chips on the
  same bus without independent chip-select being possible, a bus id (`bus.i2c0`) defined more than
  once, a `[instance.wiring]` field naming an instance that doesn't exist or exists but is the wrong
  driver type (already covered above, listed here for completeness of "same category, different
  shape").
Every one of these must produce a specific, human-readable error naming the two colliding
declarations (which instance/bus, which field, which value) — never a generic "build failed," and
never a silent pick of one over the other. This validation pass is exactly the kind of build
function this doc's own "Build-time tooling" bullet (above) requires a dedicated unit test suite
for: one test per collision category above, each proving the specific error fires on a
deliberately corrupted fixture TOML, plus proving a clean, non-colliding TOML produces no false
positive.

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
