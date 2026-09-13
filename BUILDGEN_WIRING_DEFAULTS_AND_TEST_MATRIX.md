# Buildgen wiring-defaults & validation design record

Durable design record for `buildgen`'s wiring-defaults mechanism, per-value measurement wiring, and
the driver-onboarding/pin-legality validation it enabled. **Status: shipped.** Every mechanism below
is real, tested code (`buildgen/`, plus `src/asy_sgp40_driver.py`'s and
`asy_notification_service.py`'s `_Default*` providers) — this document states current behavior, not
a plan. See BUILD_CHAIN_PLAN.md's own Session 3 entry for delivery/session context; BACKLOG.md for
the one still-open follow-on (`buildgen/buildspec.py`'s hand-maintained schema).

## 1. Why this exists

Two `_WIRING`/`# @wiring` fields have no real Python-level fallback in their consumer's own
constructor and would otherwise make a build fail whenever the wired hardware genuinely isn't
present: `asy_sgp40_driver.py`'s compensation sources (SGP40 with no live temperature/humidity
producer) and `asy_notification_service.py`'s `signal_sink` (no Neopixel to blink). Both are real,
intentional device shapes, not configuration errors — the fix is a TOML-authored fallback the driver
constructs itself, not a relaxed validator.

## 2. Wiring-defaults mechanism

- **Opt-in, never implicit**: a wiring field is never silently defaulted just because it's absent
  from `[instance.wiring]`. The TOML author writes `{default = true, ...}` explicitly.
- **Uniform shape** for every defaultable field, whether or not it carries a constant
  (`signal_sink = {default = true}`; `humidity_source = {default = true, relative_humidity = 35}`).
- **Naming convention**: `_Default<ToMLFieldInPascalCase>` (`humidity_source` →
  `_DefaultHumiditySource`), defined in the same driver module as its real producer class.
- **Discovery**: `buildgen/defaults.py` AST-parses the `_Default<Field>` class's own `__init__`
  signature (param names, which have a Python default) — that signature *is* the schema for the
  sub-table's allowed/required keys, never hand-duplicated in `buildgen/buildspec.py`.
- **Generated code**: the default provider is constructed inline, at the exact call-site the real
  wiring expression would occupy (e.g. `SGP40_Reader(i2c1, _DefaultTemperatureSource(temperature=25), ...)`).
  It contributes no construction-order edge in `buildgen/graph.py` — there is no producer instance to
  depend on, the same treatment an absent optional field already gets.

### 2.9 Per-value measurement wiring

The mechanism actually shipped is **per-value**, not per-producer: every individual measurement
value a consumer needs is independently wireable via `{source, field}` (mirroring
`asy_notification_service.py`'s pre-existing `warn_*` shape), resolved at build time by checking that
`source`'s `get_data()` result exposes an attribute named `field` — a structural check, not a fixed
`producer_class` match. A future driver exposing a matching field name becomes wireable with zero
`buildgen` changes.

Real fields today: `asy_sgp40_driver.py`'s `temperature_source`/`humidity_source`, each independently
resolvable to any instance exposing a `Temp`/`Hum`-named attribute (`scd30` or `bmp3xx`) or defaulted
via `_DefaultTemperatureSource`/`_DefaultHumiditySource` — both self-contained, no cross-module
import (so a device with `sgp40` but no `scd30` never pulls `asy_scd30_driver` into its frozen-module
set just because of this). `SGP40_Reader.__init__` takes four parameters
(`temperature_source`, `temperature_field`, `humidity_source`, `humidity_field`), each pair resolved
independently in `_read_sgp()` via `getattr(await source.get_data(), field_name)`.

Name-matching is the whole mechanism — no separate property/unit tag system. A producer naming the
same physical quantity differently (e.g. `"Temperature"` instead of `"Temp"`) simply isn't recognized
as interchangeable until its field is renamed to match.

## 3. Declared as comment tags, not Python values

`_WIRING`, `_VALUE_WIRING`, and `_LIMITS` (below) are all `#`-comment tags, not real tuples — nothing
the running firmware itself reads should compile into frozen bytecode just to serve the generator
(BUILD_CHAIN_PLAN.md's quality bar). Measured saving from this conversion plus `_Default*`
`TYPE_CHECKING` aliases: ~3,576 bytes (~2.6%) of `src/`'s frozen bytecode. `_Default<Field>` classes
stay real Python — the generated module actually constructs them, so they're live code, not metadata.

| Tag | Grammar | Parser |
|---|---|---|
| `# @wiring` | `<toml_field> <ProducerClass> <target> <required\|optional> <kwarg\|attr\|setter>` | `buildgen/wiring.py` |
| `# @value-wiring` | `<toml_field> <source_kwarg> <field_kwarg> <required\|optional>` | `buildgen/value_wiring.py` |
| `# @limits` | `<field> <min>..<max>` or `<field> in {a, b, ...}` (`*` on either side of a range = unchecked that side; `min == max` = exact value) | `buildgen/limits.py` |
| `# @requires` | `bus.<field><op><value>` | `buildgen/requires_tag.py` |

Every tag family shares `buildgen/tag_comments.py`'s scanner: tokenize-based (a `#` inside a
string/docstring is never mistaken for a real comment), and a near-miss/typo'd attempt at a known tag
name (wrong sigil, wrong operator, dropped piece, wrong location) fails the build loud rather than
silently reading as "no tag here" — see that module's `check_for_near_miss_tags()` for the incident
that motivated this rule.

Real `_WIRING`/`_VALUE_WIRING`/`_LIMITS` declarations today: `asy_scd30_driver.py`/`asy_sgp40_driver.py`
(`# @requires bus.timeout>=200000`/`bus.frequency<=100000` and `bus.frequency<=400000` respectively —
`bmp3xx` is deliberately untagged, its datasheet supports every I2C mode); every optional-instance
driver's `fram_target` (`kwarg`, optional); `signal_sink` (`attr`, required, target
`request_signal`); `led_target` (`setter` on `conn`, target `set_ext_led`); `asy_sgp40_driver.py`'s
`temperature_source`/`humidity_source` (§2.9); `asy_bmp3xx_driver.py`'s `_LIMITS`
(`address in {0x76, 0x77}`, `trigger_sec 1..3600`) — the only driver with a real,
datasheet-documented `_LIMITS` constraint today (every other candidate field, checked directly
against its own module, has no equivalent documented domain to draw from, so none was invented).

## 4. Pico W GPIO / bus pin legality

`buildgen/pico_gpio.py` hardcodes the Pico W's real, fixed GPIO→peripheral table (this project
targets the Pico W alone — no board parameterization), transcribed from
`datasheets/pico w/RP-008312-DS-2-pico-w-datasheet.pdf` Figure 2 (p.4):

- **I2C**: SDA/SCL pairs alternate I2C0/I2C1 every 2 GPIOs (GP0/1→I2C0, GP2/3→I2C1, ... GP26/27→I2C1),
  even GPIO = SDA, odd = SCL within each pair.
- **SPI**: 4-GPIO blocks, fixed MISO/CSn/SCK/MOSI role at offsets 0-3, alternating SPI0/SPI1 by block
  (GP0-3 and GP4-7 both SPI0, GP8-11 and GP12-15 both SPI1, GP16-19 SPI0 again). `asy_spi_driver.py`
  only needs `sck_pin`/`mosi_pin`/`miso_pin` (CS is a separate, instance-exclusive `cs_pin`) drawn
  from any GPIOs sharing the same peripheral index — not necessarily the same 4-GPIO block.
- **GP22/GP28** have no I2C or SPI function at all. **GP23-25/29** are reserved for the wireless
  interface (never exposed on the header, confirmed against the datasheet's own pin count and its
  wireless-interface section). Any GPIO ≥30 or negative doesn't exist.

`buildgen/validate.py`'s `_check_gpio_collisions()` checks every claimed pin device-wide (bus wire
pins and instance-exclusive `cs_pin`/`irq_pin`/`pin` alike) for real existence and non-reserved
status, and additionally checks each bus's own wire pins against their required peripheral index
*and role* (SDA vs. SCL, MISO vs. SCK vs. MOSI — a transposed pair is exactly as wrong as an
out-of-range one). `_bus_kind()` validates a bus id's port suffix is a real index (`i2c0`/`i2c1`/
`spi0`/`spi1`), not just that the prefix matches.

## 5. Validation coverage (`buildgen/validate.py`)

Every check below raises `buildgen.errors.BuildError` naming the device/instance/field responsible —
never a generic failure, a raw traceback, or a silent partial build (BUILD_CHAIN_PLAN.md's quality
bar). Malformed/missing/unexpected/misformatted fields at every level (`[device]`, `[bus.*]`,
`[[instance]]`, `[instance.wiring]`, `[device.wiring]`); global GPIO-pin exclusivity and per-bus
address exclusivity (including two hardwired-address instances of the same driver sharing a bus with
no `address` field); two independent identity-collision checks — `resolved_name` (the REST/config-key
identity, from each driver's `_NAME` constant) and `instance_label` (the generated Python variable
name, from `driver`+`name_ext`) — since the two naming spaces are structurally different
(`asy_notification_service.py`'s `_NAME` is `"NOTIFY"`, not `"NOTIFICATION"`); a wiring reference
resolves against the TOML's own `driver`+`name_ext` identity, never against `resolved_name`; pin
legality/role (§4); driver-declared value domains (`_LIMITS`, §3); and driver-onboarding
registration — a driver that resolves via `driver_registry.resolve_driver()` but has no
`buildgen/buildspec.py` entry raises its own dedicated error naming that as the cause, rather than
reporting every one of its TOML fields as unrecognized.

## 6. Known limitation

`buildgen/buildspec.py`'s per-driver TOML-field schema (`REQUIRED_TOML_FIELDS`/
`ALLOWED_INSTANCE_FIELDS`/`ADDRESS_CAPABLE_DRIVERS`/`FIXED_ADDRESS_DRIVERS`) is still hand-maintained
— the one association `buildgen` needs from a driver that isn't AST-derivable from `_WIRING`/
`_VALUE_WIRING`/`_LIMITS`/`_Default*` alone, since Session 2's TOML field names and `src/`'s
constructor parameter names are two independently-evolved naming spaces. See BACKLOG.md's
"Deferred" section for the full account and why it's a separate, unstarted unit of work rather than a
mechanical continuation.
