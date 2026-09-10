# Buildgen wiring defaults & clean-build test matrix

**Status: design discussion with the project owner, 2026-09-10. Nothing here is implemented yet** —
`buildgen/` and `src/` are unchanged as of this file's creation. This document exists purely to
capture what was agreed before any code is written, so none of it gets lost. Every "shall"/"will"
below is a decided design intent, not a description of current code. Implementation needs an
explicit go-ahead from the project owner before it starts (given directly, same as any other
real-hardware-adjacent or scope-expanding decision in this repo).

## 1. Background

Session 3's `buildgen/` (PR #61, branch `claude/session3-generator-85eb44`) shipped with
`_WIRING`'s `required=True` meaning "the TOML must supply a live instance reference for this
field, or the build fails." Two fields are `required=True` today:

- `asy_sgp40_driver.py`'s `comp_source` (must resolve to a real `SCD30_Reader`)
- `asy_notification_service.py`'s `signal_sink` (must resolve to a real `NeopixelDriver`)

While building a "every logically valid device shape must produce a clean build" test matrix with
the project owner, this turned out to be too strict: a device with an SGP40 but genuinely no
SCD30 (SGP40 falling back to its own on-chip constant-compensation reading) or a notification
setup that shouldn't blink an LED are real, intentional configurations — the driver just needs a
sensible constant/no-op fallback instead of being unbuildable. This document is the resulting
design for that fallback mechanism, plus the test matrix it unblocks.

## 2. The wiring-defaults mechanism

### 2.1 Core decision

The TOML author must **explicitly opt into using the default** — a wiring field is never silently
defaulted just because it's absent from `[instance.wiring]`. For a default that carries a
meaningful constant value, that value is **TOML-authored**, not hardcoded in the driver, and flows
into the constructor of the driver's own built-in default provider.

### 2.2 TOML shape

Reuses the sub-table convention `[instance.wiring]`'s `warn_*` fields already established
(`{source = ..., field = ...}`), keyed by a literal `default = true` instead:

```toml
[instance.wiring]
comp_source = {default = true, temperature = 25, relative_humidity = 50}
```

For a field with no meaningful constant (`signal_sink`), the shape stays uniform rather than
switching to a bare string/flag — **decided: uniform shape for every defaultable field**:

```toml
[instance.wiring]
signal_sink = {default = true}
```

### 2.3 Default-provider naming convention

One fixed pattern, used the same way in every driver module, no per-field declaration needed:
**`_Default<ToMLFieldInPascalCase>`**, defined in the same source file as the real `_WIRING`
tuple.

| `_WIRING` field | Default class          |
|-----------------|-------------------------|
| `comp_source`   | `_DefaultCompSource`    |
| `signal_sink`   | `_DefaultSignalSink`    |

### 2.4 Discovery: buildgen reads the definition, no hand-maintained schema

buildgen AST-parses `_Default<Field>`'s own `__init__` signature (param names, whether each has a
Python-level default) to learn what keys the TOML `{default = true, ...}` sub-table may/must
carry — the same spirit as how it already parses `_WIRING`/`_NAME` (never imported). The class
definition **is** the schema, consistent with buildgen's existing "never duplicate what the source
already states" philosophy (same principle as `driver_registry.py`'s AST-based class resolution).

### 2.5 Worked designs

**`asy_sgp40_driver.py`** — `mode="kwarg"`. `_read_sgp()` only ever reads `.Temp`/`.Hum` off
whatever `comp_source.get_data()` returns (confirmed directly:
`comp_data: list[int | float | None] = [float(scd_data.Temp), float(scd_data.Hum)]`), so the
default provider's return value only strictly needs to expose those two attributes — no change
needed to `_read_sgp()` itself:

```python
class _DefaultCompSource:
    def __init__(self, temperature: float = 25, relative_humidity: float = 50) -> None:
        self._data = SCD30(None, temperature, relative_humidity, None, None, None)  # CO2/WetBulb/DewPoint/TS unused by sgp40
    async def get_data(self) -> "SCD30":
        return self._data
```
`SCD30 = namedtuple("SCD30", ("CO2", "Temp", "Hum", "WetBulb", "DewPoint", "TS"))` is
`asy_scd30_driver.py`'s real return-value shape (confirmed directly) — reusing it keeps the
default provider duck-type-identical to a real `SCD30_Reader.get_data()` result rather than a
bespoke shape. 25°C/50%RH matches `SGP40_I2C.measure_raw()`'s own datasheet-documented defaults
(Table 9) — not arbitrary.

**Superseded by §2.9 below**: this worked example treats `comp_source` as one field pointing at a
whole producer object. The project owner has since decided that every individual measurement value
(temperature, humidity, ...) must be independently source-selectable, so `comp_source` actually
splits into two per-value fields rather than staying one whole-object reference — see §2.9. Kept
here as the smaller worked example that motivated the generalization, not as the final design.

**`asy_notification_service.py`** — `mode="attr"`, target `request_signal`. Because codegen's
existing attr-mode rendering is just `f"{var}.{wf.target}"`, a default provider that exposes an
attribute/method of the *same name* as `wf.target` needs **no mode-specific special-casing** in
codegen — `_DefaultSignalSink().request_signal` flows through the exact same rendering path as a
real `pixel.request_signal`:

```python
class _DefaultSignalSink:
    async def request_signal(self, r: int, g: int, b: int, t: float) -> bool:
        return False  # no-op: no neopixel wired, no LED signal ever fires
```

### 2.6 Generated-code shape (proposed, not yet confirmed with the project owner)

Construct the default provider **inline**, at the exact call-site the real wiring expression would
occupy — not as a separate named global/instance:

```python
sgp40 = SGP40_Reader(i2c1, _DefaultCompSource(temperature=25, relative_humidity=50), ...)
notify_service = NotificationCoordinator(_DefaultSignalSink().request_signal, ntp.cettime, ...)
```

Consequence: `graph.py`'s dependency-edge computation needs a branch — a `{default: true, ...}`
wiring value contributes **no construction-order edge** (there's no producer instance to depend
on), the same treatment an absent optional field already gets today. This keeps the
default-selection mechanism fully local to `codegen.py`/`validate.py`; `graph.py`'s topological
sort is otherwise unaffected.

### 2.7 Scope — which fields actually need this

Only the two current `required=True` fields (`comp_source`, `signal_sink`). Every other `_WIRING`
field today is `required=False` and the underlying driver constructor already has a real
Python-level `None` default with existing, already-tested handling (e.g.
`fram_storage: "AsyFramManager | None" = None`) — those don't need a default-provider class at
all; omitting the field already produces a clean build today.

### 2.8 Open implementation questions (not yet resolved)

- Exact validation behavior for unknown/wrong-type keys inside a `{default = true, ...}` sub-table
  — presumably mirrors the existing instance/device/bus "unrecognized field" pattern already in
  `validate.py`, keyed against the discovered `__init__` signature instead of a hand-maintained
  `buildspec.py` table.
- For `mode="attr"` fields, should buildgen additionally verify the default provider actually
  defines an attribute/method named `wf.target` (mirroring how it already verifies things about
  real producer classes)? Leaning yes — same fail-loud-at-generation-time philosophy as everything
  else in `buildgen/`.
- Whether `validate.py`'s existing `_check_wiring_reference`/`resolve_instance_key` path needs a
  parallel "resolve a default selection" path, or a shared branch point right at the top (a
  `{default: true, ...}` value vs. a plain string value are distinguished before any instance
  resolution is attempted).

### 2.9 Generalization (confirmed by project owner, 2026-09-10): uniform per-value wiring for every measurement

Not limited to SGP40's `comp_source`. **Every individual measurement value must be freely
selectable for wiring, from any producer that exposes that same physical property/unit —
independent of which whole producer object it happens to live on.** This is not new machinery:
`asy_notification_service.py`'s `warn_*` fields already work exactly this way (`{source, field}`,
`NotificationCoordinator` resolving `source.get_data()` then reading `field` off it dynamically,
tolerant of any field name). The decision is to apply that same shape everywhere a module consumes
one scalar value out of another module's `get_data()` result, not just for notification signals.

**Full measurement-surface survey** (every real `namedtuple` in `src/`, confirmed directly,
2026-09-10):

| Producer (`src/` module)     | Measurement fields (excluding `TS`) |
|-------------------------------|---------------------------------------|
| `SCD30` (`asy_scd30_driver.py`)   | `CO2`, `Temp`, `Hum`, `WetBulb`, `DewPoint` |
| `BMP3XX` (`asy_bmp3xx_driver.py`) | `Pres`, `Temp`, `SLPres` |
| `SGP40` (`asy_sgp40_driver.py`)   | `VOC`, `Raw` |

**Only genuine overlap today: `Temp`** (`SCD30.Temp` / `BMP3XX.Temp` — identical attribute name
already, confirmed directly, not by convention/enforcement — see the open question below). Every
other field is single-sourced right now (`CO2`/`Hum`/`WetBulb`/`DewPoint` only on `SCD30`;
`Pres`/`SLPres` only on `BMP3XX`; `VOC`/`Raw` only on `SGP40`). So the *practical* effect today is
scoped to `SGP40`'s two compensation inputs, but the **mechanism itself must be written generically
in buildgen** (uniform `{source, field}` resolution, no per-property special-casing, no hardcoded
`producer_class`) so a future driver exposing a matching field name becomes wireable automatically
with zero buildgen changes — the same reason `warn_*` was already built generically rather than as
three hardcoded CO2/VOC/Hum cases.

**Consequence for `comp_source`**: splits into two independent per-value wiring fields (exact TOML
field names still open — `temperature_source`/`humidity_source` used as placeholders below):

```toml
[instance.wiring]
temperature_source = {source = "bmp3xx", field = "Temp"}    # e.g. compensate from BMP3xx's Temp instead of SCD30's
humidity_source = {default = true, value = 50}               # no live humidity source wired - constant fallback
```

This is a real `src/` behavior change beyond §2's original scope: `SGP40_Reader.__init__` moves
from one `comp_source: SCD30_Reader` parameter to two independent value-getters, and `_read_sgp()`
resolves each the same generic way `NotificationCoordinator._check_one()` already resolves a
`(source, field)` pair, instead of one direct `self.comp_source.get_data()` call. `_WIRING`'s
`producer_class`/nominal-class-match check no longer applies to fields using this shape — the
constraint becomes structural (source exposes an attribute named `field`), not nominal.

**RESOLVED (2026-09-10)**: name-matching is sufficient — the same attribute-name check `warn_*`
already uses ("does `source`'s `get_data()` result have an attribute named `field`"), no separate
property/unit tag system. A future driver naming the same physical quantity differently (e.g.
`"Temperature"` instead of `"Temp"`) simply isn't recognized as interchangeable until its field is
renamed to match — an accepted limitation, not a gap to design around now.

## 3. To-dos (added by the project owner, 2026-09-10)

- **Every `src/` change this mechanism requires** (`_DefaultCompSource`, `_DefaultSignalSink`, and
  anything else it turns out to need) **must be written against the relevant paragraphs of
  `SPECIFICATION.md`** — not just made to satisfy buildgen's own generation needs. Applies at
  minimum: Part C (driver/service architecture shape — layering, naming, error handling), Part D
  (the "fully reviewed and tested" promotion checklist), Part C.14 (the `_WIRING`/cross-instance-
  dependency convention this mechanism extends).
- **Every such `src/` change needs its own `tests/` coverage** — functioning (does it produce the
  right default values/behavior), resilience (error handling — e.g. what happens if a
  TOML-supplied constant is out of a sensible range, does construction fail loud rather than
  silently misbehave), and coverage (per `scripts/test.sh --coverage`'s existing non-gating
  report) — the same bar every other `src/` promotion already meets, not a buildgen-only shortcut
  just because the class is small.
- Resolve the open items in §2.8 before writing any of this for real.

## 4. Clean-build test matrix

**Status: still being assembled with the project owner. Not final — treat every list below as
"collected so far," not "complete."**

### 4.1 Ground-truth `_WIRING` graph (verified directly against `src/`, 2026-09-10)

| Consumer                | Field         | Required?                          | Mode    | Producer type   |
|--------------------------|---------------|-------------------------------------|---------|------------------|
| scd30                    | `fram_target` | optional                            | kwarg   | AsyFramManager   |
| sgp40                    | `comp_source` | required *(→ defaultable, §2)*      | kwarg   | SCD30_Reader     |
| sgp40                    | `fram_target` | optional                            | kwarg   | AsyFramManager   |
| bmp3xx                   | `fram_target` | optional                            | kwarg   | AsyFramManager   |
| neopixel                 | `fram_target` | optional                            | kwarg   | AsyFramManager   |
| notification             | `signal_sink` | required *(→ defaultable, §2)*      | attr    | NeopixelDriver   |
| notification             | `fram_target` | optional                            | kwarg   | AsyFramManager   |
| conn (device-level)      | `led_target`  | optional                            | setter  | NeopixelDriver   |
| sysfunct (device-level)  | `fram_target` | optional                            | kwarg   | AsyFramManager   |

Plus notification's own separate per-signal mechanism (not `_WIRING`): `warn_co2`/`warn_voc`/
`warn_hum`, each an independently optional `{source, field}` sub-table.

### 4.2 Hard structural constraints (things that prune the matrix, not things the matrix tests as "invalid")

- ~~sgp40 present ⇒ scd30 present~~ — **superseded by §2**: once the defaults mechanism lands,
  sgp40 is legal with or without scd30 present (explicit default `comp_source` when scd30 is
  absent or simply not wired).
- ~~notification present ⇒ neopixel present~~ — **superseded by §2**: same, via
  `_DefaultSignalSink`.
- FRAM absent ⇒ every `fram_target`-shaped field is forced to its absent state (nothing to wire
  to) — this one's a genuine physical impossibility, **not** solved by §2's mechanism (§2 is
  specifically for `required=True` fields; `fram_target` is `required=False` everywhere, so "FRAM
  absent" already produces a clean build today by simply omitting the kwarg — no default provider
  needed or planned for it).

### 4.3 Axes collected so far

**Merge note (2026-09-10)**: the old axis 3 ("sensor↔sensor wiring, sgp40's `comp_source`
specifically") and old axis 10 ("shared-property cross-wiring") are now one axis — §2.9 generalized
`comp_source` into independent per-value fields, matched by attribute name across *any* producer,
so there's no longer a separate "is this interchangeable across drivers" question distinct from
"how is this one field wired." Folded into axis 3 below; every real detail from both old axes is
preserved, not dropped.

1. **Sensor population** — which of {scd30, sgp40, bmp3xx} are present. With §2 landed, all 8
   subsets of the 3-element set become legal (no more sgp40⇒scd30 pruning).
2. **FRAM presence** — with / without.
3. **Per-value measurement wiring** (§2.9's generalized mechanism — today concretely: sgp40's
   `temperature_source`/`humidity_source`, independently). Per value, per consuming instance:
   - a real reference to **any** instance whose `get_data()` exposes a matching attribute name —
     not restricted to one hardcoded producer class (temperature: scd30 *or* bmp3xx, matched by
     the shared `Temp` attribute name, §2.9);
   - an explicit default with TOML-authored constants (§2);
   - not applicable when the consuming driver itself is absent (e.g. no sgp40 present at all).
   "Full / partial / none" wiring density (the project owner's original framing) now means: across
   every value a present consumer needs, how many are real references vs. explicit defaults.
4. **Sensor↔FRAM wiring** (`fram_target` on scd30/sgp40/bmp3xx/neopixel) — full (every present
   instance wires it) / partial (some do, some don't) / none (FRAM present but nothing wires to
   it) / N/A (FRAM absent).
5. **Notification↔signal wiring** (`warn_co2`/`warn_voc`/`warn_hum`) — full / partial / none, each
   individually gated on whether a suitable `source` instance (scd30 for CO2/Hum, sgp40 for VOC)
   is present at all.
6. **Notification↔neopixel wiring** (`signal_sink`) — real neopixel reference / explicit no-op
   default (§2).
7. **Device-level `led_target`** (conn↔neopixel) — wired / not-wired, when neopixel present.
8. **Device-level `fram_target`** (sysfunct↔FRAM) — wired / not-wired, when FRAM present.
9. **Multi-instance variants** — 2× scd30, 2× sgp40, plus bmp3xx (name_ext-disambiguated where
   needed) — where axis 3 becomes a genuinely free *per-instance* choice, richer than the
   single-instance case: each sgp40 instance's `temperature_source` can independently point at any
   scd30 instance, at bmp3xx, at the same source another sgp40 instance uses, or use the explicit
   default — independently of what its `humidity_source` does. This is where "full vs. partial
   wiring against different sensors measuring the same property," across multiple instances of
   multiple driver types, actually lives — the richest corner of the whole matrix.
10. **Bus topology** — all sensors on one shared bus vs. spread across separate buses vs. i2c+spi
    mixed, grounded against the real RP2040/Pico W GPIO-to-peripheral mapping (datasheets/pico
    w/RP-008312-DS-2-pico-w-datasheet.pdf, Figure 2, p.4 — read directly for this, not from
    training memory):
    - **No buses at all** — no `[bus.*]` table, no bus-attached instance (no sensors, no FRAM).
      Today `_check_bus_tables()` (`buildgen/validate.py`) unconditionally `raise`s
      `"no [bus.*] table declared"` if `[bus.*]` is absent entirely — so this combination, despite
      being logically the simplest possible device, is currently **unbuildable** as-is. Flagged as
      a real gap for §4.4, not something to fix in this design-only phase.
    - **One or two I2C buses**, each a legal GPIO pin pair for its own peripheral index. RP2040
      fixes, per pin, which of I2C0/I2C1 (if either) it can reach — never an arbitrary software
      choice. Reading straight off Figure 2: I2C-capable pins run in fixed SDA/SCL pairs that
      alternate I2C0/I2C1 every 2 GPIOs (GP0/1→I2C0, GP2/3→I2C1, GP4/5→I2C0, GP6/7→I2C1, GP8/9→I2C0,
      GP10/11→I2C1, GP12/13→I2C0, GP14/15→I2C1, GP16/17→I2C0, GP18/19→I2C1, GP20/21→I2C0,
      GP26/27→I2C1), always even-GPIO=SDA/odd-GPIO=SCL within a pair. GP22 and GP28 have no I2C
      function at all; GP23-25/29 are reserved for the onboard CYW43439 wireless SPI link (datasheet
      p.7) and must never be claimed by a device's own bus/instance pins. A legal two-I2C-bus device
      picks one pair from the I2C0 set and one from the I2C1 set (today's real devices, e.g.
      `devices/wozi.toml`, do exactly this: `bus.i2c0` on GP12/GP13, `bus.i2c1` on GP26/GP27).
      **Gap**: `_check_gpio_collisions()` only enforces device-wide pin-number uniqueness — it never
      checks a bus's declared `scl_pin`/`sda_pin` against this fixed table at all, so e.g. a
      `bus.i2c0` table wired to GP2/GP3 (silicon-wise, an I2C1-only pair) or to GP22 (no I2C function
      at all) currently passes `buildgen` cleanly and would only fail at real-hardware
      `machine.I2C()` construction time — a raw runtime error, not this package's fail-loud
      `BuildError` contract. Same gap applies symmetrically to SPI below. Flagged for §4.4.
    - **One or two SPI buses**, same grounding. SPI-capable pins run in fixed 4-GPIO blocks with a
      fixed RX/CSn/SCK/TX role assignment, alternating SPI0/SPI1 by block: GP0-3 and GP4-7 are both
      SPI0 (RX/CSn/SCK/TX respectively within each block), GP8-11 and GP12-15 are both SPI1,
      GP16-19 is SPI0 again. `asy_spi_driver.SPI.__init__` takes `sck_pin`/`mosi_pin`/`miso_pin`
      only (no CS — that's an instance-exclusive `cs_pin`, per `_check_bus_tables()`'s own
      `cs_pin` rejection), so a legal SPI bus table needs its three pins' TX/RX/SCK roles to all
      belong to the *same* SPI peripheral index, per this table. Today's real devices use exactly
      one SPI bus (`bus.spi0`, FRAM-only — `asy_spi_driver.py`'s own docstring: "Sole consumer:
      asy_fram_driver.py's FRAM_SPI"); a second, SPI1-routed bus is logically legal but unexercised
      by any real `devices/*.toml` today.
    - i2c+spi mixed (today's real shape: `i2c0` + `i2c1` + `spi0` together) remains a distinct,
      already-covered sub-case of the above, not a separate axis.
11. **name_ext on a singleton-adjacent instance** — giving the sole scd30 instance a non-empty
    `name_ext` anyway (legal, just unusual).

### 4.4 Still to do

- Enumerate the actual cross-product of axes 1-8 (pruned by §4.2), decide which become individual
  TOML fixtures vs. which get covered by targeted unit tests against `validate.py`/`codegen.py`
  directly (matching the existing `test_buildgen_validate.py` pattern of driving internals
  directly for cases no real/6-device TOML can reach).
- Design the multi-instance (axis 9) fixture set — likely extends
  `tests_scripts/buildgen_fixtures/novel_combo.toml` or adds a sibling fixture, not yet decided.
- **Two real gaps found while grounding axis 10 against the Pico W datasheet (2026-09-10),
  design-only for now, not fixed**:
  1. `_check_bus_tables()` unconditionally requires at least one `[bus.*]` table — a device with
     no bus-attached instance at all (no sensors, no FRAM) can't build today, even though it's a
     logically valid, simplest-possible shape under axis 1/2's "no sensors" × "no FRAM" corner.
  2. Buses' declared pins are never checked against the RP2040's fixed per-GPIO I2C0/I2C1/SPI0/SPI1
     capability table — only device-wide pin-number uniqueness is enforced
     (`_check_gpio_collisions()`). An `scl_pin`/`sda_pin`/`sck_pin`/`mosi_pin`/`miso_pin`
     combination that's real-hardware-illegal for its bus's own peripheral index (or that claims
     GP22/28, or the GP23-25/29 wireless-reserved pins) currently passes `buildgen` and would only
     surface as a raw runtime error from `machine.I2C()`/`machine.SPI()` on real hardware, not this
     package's fail-loud `BuildError` contract.
- Keep collecting axes/combinations with the project owner before finalizing which become real
  test files.

## 5. Must-fail matrix (negative/mutation testing)

**Framing, different from §4**: §4 is a *state-space* matrix — combinations of axis choices that
must all build clean. This section is a *mutation* matrix — the project owner's own framing is
"must fail **independently from any config variants**": take any point in §4's clean-build space
(any device, any axis combination) and apply exactly one of the corruptions below to it; the build
must fail, every time, regardless of which clean baseline it was applied to. These are two
orthogonal test dimensions, not one more axis bolted onto §4 — a fixture generator for this section
can start from *any* already-valid TOML and mutate it, rather than needing its own combinatorial
space.

Every category below is annotated against current `buildgen/validate.py`/`buildgen/buildspec.py`
coverage as of this session (`already covered` = a real check exists today and a test could target
it now; `gap` = confirmed unvalidated, would either silently pass or crash raw instead of
`BuildError`).

### 5.1 The project owner's list, as given

1. **Any duplicate field or property.** Two sub-cases with different mechanisms:
   - Same key twice in one TOML table (`bus = "i2c0"` appearing twice under one `[[instance]]`) —
     **already covered**, but not by `buildgen` at all: `tomllib` itself rejects this as invalid
     TOML (`TOMLDecodeError`) before `buildgen` ever sees the doc, and `load_device()` wraps that
     into a `BuildError`. Same for a duplicate `[bus.i2c0]` table declared twice, or a duplicate
     `[device]` table.
   - A duplicate `[[instance]]` *entry* for the same driver+name_ext pair (legal TOML — arrays can
     repeat) — **already covered**, `load_device()`'s own explicit check (`model.py`, "duplicate
     [[instance]] entry").
2. **Any missing field or property** — **already covered** at every level found so far: `[device]`
   (`_check_device_table`'s `_REQUIRED_DEVICE_FIELDS` loop), `[bus.*]` (`_check_bus_tables`'s
   per-kind wire-pin/frequency loop), `[[instance]]` (`_check_required_fields`'s
   `REQUIRED_TOML_FIELDS` loop), `[instance.wiring]` (`_check_instance_wiring`'s required-`_WIRING`
   loop), `[device.wiring]` (`_check_device_wiring`'s required-field loop, this session's own
   earlier addition).
3. **Any misspelled field or property** — mechanically the same failure path as #5 (unexpected
   field): a misspelling *is* an unrecognized-field name from `buildgen`'s point of view, there's
   no separate "did you mean" mechanism and none is proposed. Listed as its own bullet here only
   because it's a distinct real-world *cause*, not a distinct *check* — one test fixture per level
   (device/bus/instance/wiring) covers both #3 and #5 at once.
4. **Any misformatted field or property** (wrong type/shape) — **partially covered, real gaps
   remain.** Covered today: bus `frequency`/`timeout` (int), instance `address`/`max_size`/
   `trigger_sec` (int, non-bool), `bus`/`driver`/`name_ext` (string), `[instance.wiring]` string
   fields (must be `str`), `warn_*` sub-tables (must be `{source, field}` dict with both string).
   **Gap**: `[device]`'s `hotspot_password` has no type check at all (only `name`/`hostname` do);
   no field anywhere checks for a TOML array/inline-table where a scalar is expected beyond the
   specific fields already listed (e.g. `bus = ["i2c0"]`, `pin = [5]`) — falls through to a raw
   `TypeError`/wrong-shape crash instead of `BuildError` for any field not already covered above.
5. **Any unexpected field or property** — **already covered** at `[device]`, `[bus.*]`, and
   `[[instance]]` level (all three have an explicit `unknown = set(...) - ALLOWED...` check).
   **Gap**: `[instance.wiring]` has no equivalent "reject a wiring sub-key with no matching
   `_WIRING` entry and no `warn_` prefix" catch-all beyond what `_resolve_wiring_field` already
   raises for named fields — worth a dedicated test confirming an entirely bogus
   `wiring.frobnicate = "x"` fails (should already fail via the `wf is None` branch in
   `_check_instance_wiring`, but not yet an explicit test per this document's search).
6. **A "special property" set incorrectly (e.g. i2c timeout for scd30)** — range/exact-value
   validation. **Confirmed gap, and a new mechanism the project owner is explicitly requesting**,
   not just a missing test: today `timeout`/`frequency`/`address`/`max_size`/`trigger_sec` are only
   checked for *type* (int), never for being a *sane value* of that type (a `frequency = -5` or
   `timeout = 999999999` currently builds clean). See §5.2 for the proposed min/max mechanism this
   would need — **design sketch only, not agreed/implemented**.
7. **Impossible configs**: non-existent buses, non-existent pins, pins that don't fit their bus,
   any pin double-used anywhere in the device.
   - Non-existent bus reference (`bus = "i2c9"` on an instance) — **already covered**,
     `_check_required_fields`'s `spec.fields["bus"] not in buses` check.
   - Pin double-used anywhere (bus pins vs. bus pins, bus pins vs. instance `cs_pin`/`irq_pin`/
     `pin`, instance vs. instance) — **already covered**, `_check_gpio_collisions()` claims every
     pin device-wide into one dict and raises on any second claim.
   - Non-existent pin (a GPIO number the Pico W doesn't expose at all, e.g. 30+, or negative) —
     **gap**, only int-type is checked, never range.
   - Pin that doesn't fit its bus (silicon-wise illegal for that bus's I2C0/I2C1/SPI0/SPI1 index,
     or one of GP22/28 with no bus function, or one of the GP23-25/29 wireless-reserved pins) —
     **gap**, this is §4.3 axis 10's already-flagged finding, restated here as a must-fail case
     rather than a must-build case: the *same* underlying missing check would need to both permit
     the legal combinations in axis 10 and reject the illegal ones here — one implementation, two
     matrix entries.
   - Bus name with a recognized kind prefix but a nonexistent port suffix (`[bus.i2c2]` — RP2040
     only has I2C0/I2C1; `[bus.spi7]`) — **gap, newly found while drafting this section**:
     `_bus_kind()` only checks the *prefix* (`"i2c"`/`"spi"`) is recognized, never that the
     trailing digit is a real port index; `codegen.py`'s `bus_id[len("i2c"):]` then blindly emits
     `asy_i2c_driver.I2C(2, ...)` for `"i2c2"`, which would only fail on real hardware. Same family
     of gap as the pin-legality one above, one level up (bus identity itself vs. its pins).
8. **Unknown selected modules** (`driver = "bogus_chip"`) — **already covered**,
   `driver_registry.resolve_driver()` raises for a driver name with no matching module (verified by
   its own existing tests per this session's earlier work; not re-verified line-by-line here).
9. **Missing properties or settings** — same as #2, listed again by the project owner for emphasis;
   no new mechanism, folded in.
10. **Wrong properties and settings** (nonsense content, out-of-range values, missing values) —
    union of #4 (misformatted) and #6 (out-of-range) above; no separate mechanism.
11. **Duplicate sensors on the same I2C bus without distinguishing addresses, or with identical
    addresses, or with impossible addresses** — three sub-cases:
    - Two fixed-address instances of the *same* driver sharing a bus with neither declaring
      `address` — **already covered**, `_check_address_collisions()`'s `per_bus_driver_fixed`
      branch (`FIXED_ADDRESS_DRIVERS` — scd30/sgp40 today; bmp3xx is address-capable, not fixed).
    - Two instances on the same bus with identical *explicit* `address` values — **already
      covered**, `_check_address_collisions()`'s `per_bus_explicit` branch.
    - An **impossible** address (an int that isn't actually a legal, chip-datasheet-documented
      address for that driver — e.g. BMP388/390's SDO pin only ever selects 0x76 or 0x77, so
      `address = 0x50` is real-hardware-impossible even though it's a well-typed int on a
      `ADDRESS_CAPABLE_DRIVERS` member) — **confirmed gap**, and the project owner's own note ("this
      might require a systematically findable address inside the modules") is exactly right: today
      `_check_required_fields` only checks `address` is an int, never that it's a member of the
      chip's real legal set. See §5.2 — this is the same shape of problem as #6 (a driver-declared
      constraint buildgen needs to discover, not hand-maintain), not a separate mechanism.
12. **Duplicate CS pins on SPI** — the project owner's own note is correct: this is already
    subsumed by #7's global pin-collision check (`cs_pin` is one of the three fields
    `_check_gpio_collisions()` claims per-instance), so no separate mechanism or test category is
    needed here — just confirmed as in-scope of the existing check, not a new one.

### 5.2 New mechanism sketch: driver-declared value constraints (design-only, not agreed)

Items #6 and #11's "impossible address" both need the same underlying capability: a **numeric or
enumerated legal-value constraint that lives in the driver module itself** (`src/`), discovered by
`buildgen` via AST rather than hand-maintained in `buildgen/buildspec.py` — the same discovery
philosophy already settled for `_WIRING`/`_Default*` in §2. Strawman only, following that existing
shape (naming/exact form **not** decided, needs the project owner's go-ahead like everything else
in this document):

- A module-level structure alongside a driver's `_WIRING` tuple, e.g. `_LIMITS`, holding one entry
  per constrained TOML field: `(toml_field, min, max)`, where `min`/`max` are each either a number
  or `None` (`None` = that side unchecked). `min == max` expresses an exact-value requirement (the
  project owner's own framing) rather than needing a separate "exact value" shape.
- For an **enumerated** legal set rather than a contiguous range (BMP388/390's address: exactly
  `{0x76, 0x77}`, not a min/max span) — the min/max shape alone can't express this. Open question,
  not resolved here: either a separate `_CHOICES`-style structure parallel to `_LIMITS`, or
  `_LIMITS` gaining a third shape (an explicit tuple/set of legal values instead of a min/max pair).
  Needs a decision before implementation, not before continuing to collect matrix entries.
- `buildgen` would AST-parse this the same way `buildgen/wiring.py` already parses `_WIRING` —
  never importing the driver module, matching the established never-import design philosophy.
- Scope, following §2.7's precedent for the wiring-defaults mechanism: only fields that already
  have a real, datasheet-documented constraint need this (scd30's `timeout` headroom, bmp3xx's
  `address`) — not a blanket requirement for every numeric TOML field to declare bounds.

### 5.3 Additional must-fail possibilities found while drafting this section

Beyond the project owner's own list, thinking through what else "must fail independently from any
config variant" should mean:

- **Bool-for-int confusion** — TOML `true`/`false` parse to Python `bool`, a subtype of `int`.
  Every existing int-type check already guards this explicitly (`isinstance(x, int) and not
  isinstance(x, bool)`) — confirmed already covered everywhere the pattern is used, worth a test
  per such field rather than just trusting the pattern held everywhere it was copy-pasted.
- **Float-for-int** (`frequency = 100000.0`) — same `isinstance(x, int)` checks already reject this
  (a Python `float` is never an `int` instance) — already covered, same "worth testing per field"
  note as above.
- **Array/inline-table where a scalar is expected, and vice versa** (`pin = [5]`,
  `[instance.wiring] comp_source = ["scd30"]` instead of a bare string) — partially covered per
  §5.1 #4's gap note; worth its own fixture per field family (device/bus/instance/wiring) rather
  than assuming one test generalizes.
- **Case-sensitivity of `driver =`** (`"SCD30"` vs `"scd30"`) — checked directly while drafting
  this section: **already covered**, and not actually a distinct mechanism from #8. `resolve_driver()`
  builds the module filename directly from the TOML string (`f"asy_{driver}_driver.py"`) and does a
  real filesystem lookup — on this project's case-sensitive filesystem, `"SCD30"` looks for
  `asy_SCD30_driver.py`, finds nothing, and raises the same "unknown driver" `BuildError` as any
  other nonexistent driver name. No separate case-folding/matching logic exists to have a bug in.
- **A wiring reference resolving to a real instance of the wrong driver type** (e.g.
  `signal_sink = "scd30"` — a real, declared instance, but not a `NeopixelDriver`) — **already
  covered** for named `_WIRING` fields (`_check_wiring_reference`'s `producer_class` check,
  confirmed while drafting §5.1). **Not** covered for `warn_*`'s generic `{source, field}` shape —
  by §2.9's own design this is inherent (any instance exposing a matching attribute name is valid
  by construction, there's no fixed "correct producer class" to check against at build time), so
  this isn't a gap, just a documented boundary of what build-time validation can ever catch for the
  generalized per-value mechanism versus what only fails at runtime if the named attribute is
  genuinely absent from the source's `get_data()` result.
- **Self-referential wiring** (an instance's own wiring field pointing at itself) — not yet checked
  anywhere found so far; whether this is actually invalid depends on the field (a sensor wiring its
  own `fram_target` to itself is nonsensical, but nothing about the general mechanism forbids it
  structurally) — flagged as a real open question, not yet a confirmed gap or confirmed non-issue.
- **Empty `[[instance]]` array or entirely empty device** (no `[[instance]]` key at all) — ties
  directly into §4.3 axis 10's "no buses at all" gap finding: an empty-instance device is exactly
  the shape that currently can't build at all today because of the unconditional `[bus.*]`
  requirement.

### 5.4 Still to do (must-fail matrix)

- Decide the §5.2 mechanism shape (min/max vs. enumerated choices vs. both) with the project owner
  before any implementation.
- Write the actual negative fixtures/targeted-internals tests once the project owner gives the go-
  ahead — likely mostly targeted `validate.py`-internals tests (matching the existing
  `test_buildgen_validate.py` pattern), since most single-field corruptions don't need a whole new
  TOML fixture file, just one mutated copy of an existing valid one.
- Resolve the §5.1 #3/#5 open item (an explicit test for a bogus `[instance.wiring]` key with no
  `_WIRING` match and no `warn_` prefix) and the §5.3 case-sensitivity/self-reference open
  questions before considering this section closed.
