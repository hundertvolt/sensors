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

**Note (added during the 2026-09-10 bird's-eye pass): every `comp_source`-specific example in this
subsection through §2.6 predates §2.9's per-value split and is superseded by it the same way §2.5
already flags for its own worked example** — `comp_source` itself stops existing as a single
whole-object field. Kept as-is below because the *shape* each example establishes (the
`{default = true, ...}` sub-table convention, the `_Default<Field>` naming pattern, inline
construction at the call-site) carries over unchanged to §2.9's split fields
(`temperature_source`/`humidity_source`) — only the specific field name `comp_source` does not.

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

**Note**: this table is *today's* ground truth (current code, nothing implemented from this document
yet), so `comp_source` correctly still appears as one whole-object field here. Once §2.9 lands,
this row is replaced by two independent per-value rows (`temperature_source`/`humidity_source`,
placeholder names) with no fixed `producer_class` — see §2.9 for why the "Producer type" column
stops applying to those two once the split happens.

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
      function at all (confirmed directly re-reading Figure 2 during the 2026-09-10 bird's-eye
      pass: GP22 carries no function label beyond plain GPIO, GP28 carries only `ADC2`). GP23-25/29
      are never claimed by a device's own bus/instance pins at all — **precision note, corrected
      during this bird's-eye pass**: the datasheet's text never names GP23/24/25/29 explicitly (a
      full-text search of the PDF for each found zero hits; the earlier "(datasheet p.7)" citation
      for this was simply wrong — p.7 is the mechanical-spec/physical-pin-numbering section,
      unrelated). This is an **inference** from Figure 2 (p.4) itself: those four GPIO numbers
      never appear anywhere on the 40-pin header pinout, and nothing else on the board exposes
      them. Two independent things corroborate the inference rather than just resting on absence:
      (1) p.4's own bullet list says the board "Exposes 26 multi-function 3.3 V general purpose I/O
      (GPIO)" — the header's own labeled pins are exactly GP0-22 plus GP26-28, 26 pins, so the 4
      unlisted numbers (23/24/25/29) are exactly RP2040's other 4 GPIOs (0-29 is 30 total); (2) §3.8
      "Wireless interface" (pp.17-18) confirms *why*, even without naming pin numbers: "the wireless
      interface is connected via SPI to the RP2040... due to pin limitations, some of the wireless
      interface pins are shared" (the CLK/VSYS-monitor share and the DIN/DOUT/IRQ share it
      describes). Net effect on this document's own claims: unchanged (GP23-25/29 still must never
      be claimed by a device's own bus/instance pins), only the citation and the "how do we know
      this" framing are corrected. A legal two-I2C-bus device picks one pair from the I2C0 set and
      one from the I2C1 set (today's real devices, e.g. `devices/wozi.toml`, do exactly this:
      `bus.i2c0` on GP12/GP13, `bus.i2c1` on GP26/GP27).
      **Gap**: `_check_gpio_collisions()` only enforces device-wide pin-number uniqueness — it never
      checks a bus's declared `scl_pin`/`sda_pin` against this fixed table at all, so e.g. a
      `bus.i2c0` table wired to GP2/GP3 (silicon-wise, an I2C1-only pair) or to GP22 (no I2C function
      at all) currently passes `buildgen` cleanly and would only fail at real-hardware
      `machine.I2C()` construction time — a raw runtime error, not this package's fail-loud
      `BuildError` contract. Same gap applies symmetrically to SPI below. Flagged for §4.4.
      **Scope note, added this pass**: the GP23-25/29-reserved and nonexistent-GPIO-number
      (§5.1 #7's separate "≥30 or negative" case) exclusions apply to **every** claimed pin
      device-wide, not just bus wire pins — an `irq_pin`/`cs_pin`/neopixel `pin` set to GP24 is
      exactly as wrong as a bus `scl_pin` set to GP24, even though an IRQ/CS/data pin has no
      peripheral *role* to validate the way a bus wire pin does. `_check_gpio_collisions()` already
      claims both categories (bus wire pins and instance-exclusive pins) into one shared dict today,
      so the eventual fix for this half is naturally one check applied uniformly there; only the
      *peripheral-index/role* legality check below is inherently bus-pin-specific.
    - **One or two SPI buses**, same grounding. SPI-capable pins run in fixed 4-GPIO blocks with a
      fixed RX/CSn/SCK/TX role assignment, alternating SPI0/SPI1 by block: GP0-3 and GP4-7 are both
      SPI0 (RX/CSn/SCK/TX respectively within each block), GP8-11 and GP12-15 are both SPI1,
      GP16-19 is SPI0 again. **GP20-22 and GP26-28 have no SPI function at all** (confirmed directly
      re-reading Figure 2 this pass — completeness fix: this was previously left implicit by the
      list simply stopping at GP19, the same way the I2C bullet above already states GP22/28's
      absence of I2C function explicitly rather than by omission). `asy_spi_driver.SPI.__init__`
      takes `sck_pin`/`mosi_pin`/`miso_pin` only (no CS — that's an instance-exclusive `cs_pin`, per
      `_check_bus_tables()`'s own `cs_pin` rejection), so a legal SPI bus table needs its three
      pins' TX/RX/SCK roles to all belong to the *same* SPI peripheral index, per this table —
      **confirmed against real usage this pass**: `devices/dev.toml`'s own `bus.spi0`
      (`sck_pin=2, mosi_pin=3, miso_pin=4`) draws its three pins from two different 4-GPIO blocks
      (GP0-3 and GP4-7) that are both SPI0, and that's legal precisely because the constraint is
      "same peripheral index," not "same contiguous block" — each RP2040 GPIO's function-select mux
      is independent, so any SPI0-capable RX/TX/SCK-labeled pin can be mixed with any other
      SPI0-capable one regardless of which block it's drawn from. Today's real devices use exactly
      one SPI bus (`bus.spi0`, FRAM-only — `asy_spi_driver.py`'s own docstring: "Sole consumer:
      asy_fram_driver.py's FRAM_SPI"); a second, SPI1-routed bus is logically legal but unexercised
      by any real `devices/*.toml` today.
    - i2c+spi mixed (today's real shape: `i2c0` + `i2c1` + `spi0` together) remains a distinct,
      already-covered sub-case of the above, not a separate axis.
11. **name_ext on a singleton-adjacent instance** — giving the sole scd30 instance a non-empty
    `name_ext` anyway (legal, just unusual).

### 4.4 Still to do

- Enumerate the actual cross-product of axes 1-8 and 11 (pruned by §4.2) — **corrected during the
  2026-09-10 bird's-eye pass**: axis 11 (name_ext on a singleton-adjacent instance) had silently
  fallen out of this bullet's range when axes 9/10 were split off into their own dedicated
  bullets below; it belongs with 1-8, not with either special-cased axis. Decide which become
  individual TOML fixtures vs. which get covered by targeted unit tests against
  `validate.py`/`codegen.py` directly (matching the existing `test_buildgen_validate.py` pattern of
  driving internals directly for cases no real/6-device TOML can reach).
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

## 6. Human-factors scenario: a new user hand-authoring a TOML for a new sensor

The project owner's prompt: think through what someone actually *does* wrong when hand-writing a
new device TOML with a mix of new and duplicate hardware — copy-paste, typos, single-character
slips, case, misread datasheets — and find what's **not yet in §4/§5**. Verified directly against
`buildgen/` source (not guessed) rather than just imagined; several items below sharpen or correct
earlier sections' framing based on what this pass actually found in the code.

### 6.1 A hard boundary: physical/semantic mismatches buildgen can never see

The single biggest class of realistic new-user error, and one no amount of TOML validation can
ever catch, because `buildgen` only ever sees the text file, never the physical board:

- **Copy-paste a whole `[[instance]]` block for a genuinely new sensor, update the bus/pins/
  name_ext correctly, but forget to change `driver = "scd30"`** to the new driver name. If the
  copied block's pins/bus genuinely don't collide with the original (easy, if it's meant for a
  different bus anyway), **nothing in §4 or §5 catches this** — `_check_address_collisions()`'s
  fixed-address-driver check is scoped to `(bus, driver)` pairs, so two same-driver instances on
  *different* buses are indistinguishable from a legitimate axis-9 multi-instance device. The build
  succeeds; the generated firmware just doesn't match the physical board (it thinks there are two
  SCD30s and zero of the new chip).
- **The same mistake one level down, specific to "some identical hardware"**: with two real SCD30
  instances (`name_ext = "a"`/`"b"`) already present, copy-pasting a *wiring* block (e.g. sgp40's
  `temperature_source`) and forgetting to update which one it points at. `_check_wiring_reference()`
  only checks the reference *resolves* and is the *right class* (§5.3 already notes this for the
  wrong-driver-entirely case) — when there are multiple valid instances of the *correct* class, it
  structurally cannot know which one is the "right" one; that's a build-time-unknowable fact about
  the real board. Worth keeping distinct from the point above: that one is "wrong driver entirely,"
  this one is "right driver, wrong specific instance among duplicates" — the sharper, more
  interesting failure mode once real duplicate hardware is involved.
- **A misread datasheet address that's still a *legal* value.** BMP388/390's SDO-pin address
  selection is exactly two values, 0x76 (low) or 0x77 (high) — `address = 0x76` in the TOML while
  the board's SDO pin is actually wired high is a real, plausible datasheet-reading mistake that
  produces a perfectly well-typed, perfectly *legal* (once §5.2's proposed enumerated-choices check
  exists) address value that's simply wrong for the real board. No TOML-only check can ever catch
  this - it needs a real-hardware oracle. **This project already has exactly that oracle for
  BMP3XX**, confirmed by reading `asy_bmp3xx_driver.py`: `setup()` reads the chip's real `CHIPID`
  register and requires it match `_BMP388_CHIP_ID`/`_BMP390_CHIP_ID` (0x50/0x60,
  datasheet-documented), raising `RuntimeError` on mismatch — a wrong-address BMP3XX would either
  NAK entirely (if nothing answers at that address) or, worse, silently talk to a *different* real
  chip that happens to share the bus and answer at that address, but the chip-ID check catches
  the "answered, but it's not really a BMP3XX" case either way. **Asymmetry worth noting, not
  claiming it's wrong**: `asy_scd30_driver.py`/`asy_sgp40_driver.py`'s own `setup()` methods have no
  equivalent chip-ID verification (no `CHIP_ID`/`WHO_AM_I`-style constant found in either file) —
  whether that's because their datasheets don't expose a comparable ID register, or simply hasn't
  been added, isn't something this design-only pass resolved; flagged as an observation for the
  project owner, not a confirmed gap.
- **Physical-header-pin-number vs. GPIO-number confusion** — grounds *why* the already-flagged
  §4.3 axis 10 / §5.1 #7 "pin that doesn't fit its bus" gap is so easy to hit by accident, not a new
  gap itself. The Pico W datasheet documents two entirely different numbering schemes for the same
  physical pins: Figure 2 (GPIO function pinout, "GP12"/"GP13"/etc.) and Figure 4 (bare physical pin
  position, 1-40, silkscreen-printed on the board) — e.g. physical pin 6 *is* GP4, not GP6. A new
  user reading the physical board's silkscreen while filling in `scl_pin`/`sda_pin` can easily write
  the physical pin number where a GPIO number belongs, producing a value that's still a
  perfectly-plausible-looking small int, possibly even a *legally I2C-capable* GPIO by coincidence,
  just not the one physically wired. This is the concrete, realistic root cause the abstract
  "pin doesn't fit its bus" gap needs a test fixture for, not a distinct mechanism.

### 6.2 Confirmed already covered (verified this pass) — including one correction to §5.2

- **`# @requires bus.<field><op><value>` already solves the "copied a bus table but the new
  sensor needs a stricter bus setting" scenario** — checked `buildgen/requires_tag.py` and
  `src/asy_scd30_driver.py` directly: SCD30's own module carries `# @requires
  bus.timeout>=200000` (its datasheet's clock-stretch headroom), enforced by
  `check_requires_tags()` against whichever bus table the instance actually references. So: copy an
  existing `[bus.i2c1]` (say, bmp3xx's, no `timeout` override) to host a *new* SCD30 instance and
  forget to add the timeout override — **this already fails loud**, correctly. This narrows §5.2's
  scope: the proposed min/max mechanism there is about a field's own *absolute* legal range
  (frequency, trigger_sec, an address value), while `@requires` already covers the *conditional,
  cross-object* case ("this bus needs field X to satisfy some comparison, but only because this
  particular driver is attached to it") — two different, already-partly-solved problems, not one
  gap. §5.2 should be read as extending the *unconditional* field-range side only.
- **Whitespace/invisible-character typos** (a trailing space in `driver = "scd30 "` or
  `comp_source = "scd30 "`) fail today, but via the *existing* "unknown driver"/"does not resolve to
  any declared instance" errors — not a distinct mechanism, just confirming the funnel catches this
  common real-world typo too.
- **Wrong TOML nesting** (`[instance]` instead of `[[instance]]`, or `[[bus.i2c0]]` instead of
  `[bus.i2c0]`) already fails — traced both through the actual parse path: `[instance]` makes
  `doc["instance"]` a dict, so `enumerate(doc.get("instance", []))` degrades to iterating dict keys
  as bare strings, which fails `isinstance(inst, dict)` and raises; `[[bus.i2c0]]` makes
  `doc["bus"]["i2c0"]` a list, and `_check_bus_tables()` already has an explicit `isinstance(...,
  dict)` guard for exactly this. **Message-quality note, not a coverage gap**: the `[instance]`
  case reports "entry #0 is missing a 'driver' field," which is technically true but doesn't point
  at the real mistake (wrong table syntax) — a new user would likely be confused rather than helped
  by this specific message. Worth keeping in mind if error messages are ever revisited, not
  something to fix as part of this design-only phase.
- **An illegal generated-code identifier** (`name_ext` or a bus id containing a character that
  can't be part of a Python identifier, e.g. a hyphen from copy-pasting a device name verbatim) —
  already fails, via `codegen.py`'s `_identifier()` (`name.isidentifier()`/`keyword.iskeyword()`).
  **Minor consistency note**: this is the one `BuildError` site in the whole reviewed codebase that
  doesn't pass `instance=`/`field=` (unlike essentially every `validate.py` check), and it fires at
  codegen time rather than validate time — cosmetic, not a functional gap, but worth a look if
  `BuildError` call-site consistency is ever audited.

### 6.3 A genuinely new gap: onboarding a brand-new driver isn't a single-source-of-truth operation

The scenario the project owner's framing points straight at — "a new sensor" — surfaces something
none of §4/§5 considered: adding a new sensor **driver module** to `src/` (not just a new TOML
instance of an existing driver) requires updating **two independently-maintained sources of truth**,
confirmed by reading both:

- `buildgen/driver_registry.py`'s `resolve_driver()` is fully automatic — it AST-discovers a new
  `asy_<name>_driver.py`'s `SensorReader`/`SensorReaderConfig` subclass with zero hand-maintenance,
  by design (its own docstring: "one small, explicit fact... nothing else").
- `buildgen/buildspec.py`'s `REQUIRED_TOML_FIELDS`/`OPTIONAL_TOML_FIELDS`/`ALLOWED_INSTANCE_FIELDS`/
  `ADDRESS_CAPABLE_DRIVERS`/`FIXED_ADDRESS_DRIVERS` are **not** — its own docstring already admits
  this is "the one piece of hand-maintained per-driver knowledge" — a new driver needs a new entry
  added by hand, or its instances are validated against an *empty* schema.

Traced the actual failure mode for a forgotten `buildspec.py` entry directly in
`_check_required_fields()`: `REQUIRED_TOML_FIELDS.get(spec.driver, ())` and
`ALLOWED_INSTANCE_FIELDS.get(spec.driver, frozenset())` both use `.get()` with an empty default, so
there's no raw crash — but an unregistered driver's *every* TOML field (including a perfectly
legitimate `bus = "i2c0"`) gets flagged by the unknown-field catch-all, since the allowed set is
empty. **The build does fail loud, but with a misleading message** ("declares unrecognized
field(s) ['bus', ...] for driver 'newchip'") that looks like a TOML typo rather than what it
actually is (buildgen doesn't know this driver's schema at all). One real edge case where it
wouldn't even fail: a hypothetical new driver needing *zero* extra TOML fields beyond `driver`/
`name_ext` would pass silently unregistered — low-realism for a bus-attached sensor (which always
needs at least `bus`), but structurally possible. Not proposing a fix here (that's implementation,
not this design phase) — just flagging that the human-factors scenario "onboarding a new sensor"
has a real rough edge at the buildspec.py hand-maintenance boundary, worth a dedicated must-fail
test (`driver` valid per `driver_registry` but absent from every `buildspec.py` dict) once tests are
written.

### 6.4 Subtlest version of the already-flagged pin-legality gap: role-swapped pins

One more sharpening of §4.3 axis 10 / §5.1 #7, found while thinking through exactly how a new user
would fat-finger a bus table: the Pico W's fixed GPIO table (§4.3 axis 10) assigns not just *which*
peripheral index a pin belongs to, but a fixed *role* within it (GP12 is I2C0 **SDA**, GP13 is I2C0
**SCL** — not interchangeable). A new user transposing the two field *values* while leaving both
pins individually legal for the intended bus — `scl_pin = 12, sda_pin = 13` instead of the correct
`scl_pin = 13, sda_pin = 12` — produces a bus table where every pin is still a real, legal pin for
that I2C index, just wired to the wrong role. Any future fix for the pin-legality gap needs to check
*role*, not just *peripheral-index membership*, or this specific (very easy) mistake would still
slip through. Same applies to SPI's `sck_pin`/`mosi_pin`/`miso_pin` triple.

### 6.5 Still to do (human-factors scenario)

- No new mechanism proposed in this section beyond what §5.2 already sketches (extended, per §6.2,
  to cover unconditional field-range/enumerated-choice checks; conditional cross-object checks
  already exist via `@requires`).
- §6.3's buildspec.py dual-source-of-truth gap needs its own must-fail test once implementation
  starts: a driver resolvable by `driver_registry` but absent from `buildspec.py`'s dicts.
  §6.4's role-swap case needs its own fixture distinct from a plain "illegal pin" fixture, once the
  underlying pin-legality check exists.
- **Confirmed by the project owner (2026-09-10): §6.4's pin-role check is scoped work, to be added**
  — not just a flagged observation anymore. **Also confirmed: this project targets the Pico W
  alone** — no second board's GPIO-to-peripheral table to support, so the eventual pin-legality/role
  mechanism (§4.3 axis 10, §5.1 #7, §6.4) can hardcode the one fixed table already transcribed from
  the datasheet in §4.3, rather than being designed as board-parameterized from the start.
- Keep collecting scenarios with the project owner before finalizing which become real test files.

## 7. Cross-checking §4/§5 against the actual test suite (`tests_scripts/test_buildgen_*.py`)

The project owner's prompt: given everything already designed in §4 (valid state space) and §5
(must-fail matrix), read the **actual, already-existing** `buildgen/` implementation and its real
test suite (`tests_scripts/test_buildgen_validate.py`/`test_buildgen_wiring.py`/
`test_buildgen_graph.py`/`test_buildgen_generate.py`/`test_buildgen_driver_registry.py`/
`test_buildgen_requires_tag.py`, plus `_toml_fixtures.py`'s `base_doc()` and the mandatory
`novel_combo.toml` fixture) and find (a) logically-valid combinations from §4 that nothing in that
suite currently exercises, and (b) invalid inputs that could still slip through un-caught, or are
probably caught but have no test locking that behavior in. This is a code+test audit, not new
design — every item below was verified by reading the actual test file and the actual
`buildgen/validate.py`/`buildgen/codegen.py`/`buildgen/model.py` source this pass, not inferred from
§4/§5's own prose.

### 7.1 Valid cases with no test today

1. **FRAM entirely absent (axis 2 "without").** Every real `devices/*.toml`, `base_doc()`, and
   `novel_combo.toml` always includes a `fram` instance. No test builds a doc with the `fram`
   instance *and* its `spi0` bus table both removed (removing only the instance would leave `spi0`
   "declared but never referenced" and fail for an unrelated reason) and confirms a clean build with
   every `fram_target` field consequently just absent. This is a logically simpler case than §4.4's
   already-flagged "no buses at all" gap — FRAM-absent-but-sensors-present is buildable *today*,
   just never exercised.
2. **Single shared I2C bus with no SPI bus at all** — only reachable once FRAM is absent (`spi0`'s
   sole real consumer per `asy_spi_driver.py`'s own docstring), so this is the same gap as #1 viewed
   from the bus-topology axis (§4.3 axis 10) rather than the sensor-population axis.
3. **Notification present with zero `warn_*` signals wired** (axis 5 "none"). `base_doc()`/
   `dev.toml`/`novel_combo.toml` always wire at least `warn_co2`. `warn_co2`/`warn_voc`/`warn_hum`
   are each individually optional (`_check_instance_wiring`'s `warn_` handling never requires any of
   them) — a notification instance with `signal_sink` wired but *no* `warn_*` keys at all should
   build clean, but nothing tests it.
4. **Device-level `fram_target` left unwired while FRAM *is* present** (axis 8 "not-wired"). Every
   real device and fixture wires it. No test removes just `[device.wiring].fram_target` while
   keeping the `fram` instance itself (distinct from `test_device_wiring_optional_field_absent_is_fine`,
   which removes `led_target`, not `fram_target`).
5. **Device-level `led_target` left unwired while neopixel *is* present, checked all the way through
   codegen.** `test_device_wiring_optional_field_absent_is_fine` (`test_buildgen_validate.py`)
   already confirms `validate.py` accepts this — but no `test_buildgen_generate.py` test confirms
   the *generated module* comes out right: that `conn.set_ext_led(...)` is correctly omitted and the
   module still `ast.parse()`s. The validate-level positive case has a test; the codegen-level
   consequence of that same case doesn't.
6. **Two `bmp3xx` instances on the *same* bus at the two different legal explicit addresses (0x76
   and 0x77).** `test_per_bus_explicit_address_collision` covers the same-address-same-bus failure;
   `test_per_bus_address_reuse_on_different_bus_is_legitimate` covers same-address-different-bus. The
   actually-common real case — two BMP3xx sharing one bus, legitimately told apart by address, which
   is the entire *reason* `ADDRESS_CAPABLE_DRIVERS` exists — has no positive test at all.
7. **A pin collision between two *bus* tables** (e.g. `bus.i2c0.scl_pin` == `bus.i2c1.sda_pin`, no
   instance involved). Confirmed by reading `_check_gpio_collisions()` (`validate.py:184-204`): it
   claims every bus-table wire pin and every instance's `cs_pin`/`irq_pin`/`pin` into one shared
   `claims` dict in a single pass, so a bus-vs-bus collision almost certainly already raises the same
   "claimed twice" error — but only bus-vs-instance
   (`test_global_gpio_pin_collision_bus_vs_instance`) and instance-vs-instance
   (`test_global_gpio_pin_collision_two_instances`) are actually tested. A bus-vs-bus case is the one
   pairing among the three the suite doesn't touch.
8. **SPI bus's own required wire pins, missing individually.** `test_bus_missing_required_wire_pin`
   only deletes `i2c0`'s `scl_pin`. `_BUS_WIRE_FIELDS["spi"] = ("sck_pin", "mosi_pin", "miso_pin")`
   goes through the identical loop, so all three are presumably enforced the same way — but none of
   the three has its own test (this is exactly the kind of case `@pytest.mark.parametrize` already
   handles for the device-level required fields; the bus-level equivalent isn't parametrized across
   both bus kinds).
9. **`[device].name`'s own type/non-emptiness check**, exercised only implicitly. Every fixture
   supplies a valid non-empty string `name`, and `test_hostname_mismatch` only exercises the
   *hostname*-derivation check (which itself depends on `name` already being valid). No test sets
   `name` to a non-string or an empty string directly, even though `_check_device_table()`
   (`validate.py:76-77`) has a dedicated check for exactly that.

### 7.2 Invalid cases that could still slip through

**(A) Confirmed code gaps — would build clean today, and shouldn't:**

- `[device].hotspot_password` has **no type/shape check at all**, confirmed by reading
  `_check_device_table()` line by line: only `name`/`hostname`/the two int fields get a value check;
  `hotspot_password` only gets the bare presence check every `_REQUIRED_DEVICE_FIELDS` member gets.
  `hotspot_password = 5` or `hotspot_password = ""` both build clean today.
- **No numeric field anywhere has a range check, only a type check** — confirmed directly for every
  one of: `[device].hotspot_time_min`/`conn_fail_to_hotspot` (`_REQUIRED_DEVICE_INT_FIELDS` loop,
  `isinstance` only), `[bus.*].frequency`/`.timeout` (`isinstance` only, no upper bound — a
  frequency far beyond the RP2040 I2C peripheral's real capability, or `0`, or negative, all pass),
  `[[instance]].max_size`/`.trigger_sec`/`.address` (same pattern in `_check_required_fields`,
  covered by existing type-only tests like `test_instance_int_field_wrong_type_rejected` but not by
  any range test). This is §5.1 #6's already-flagged gap, restated with concrete field names and
  concrete plausible fat-finger values (a dropped digit, a leftover minus sign from a template) — the
  kind of thing a new user genuinely does, not just a theoretical corner.
- **`bmp3xx` `address` outside its real legal set `{0x76, 0x77}`** (e.g. `0x50`, `0`, or `0x78`) —
  type-checked (`test_instance_address_field_wrong_type_rejected`) but never set-checked. Builds
  clean today; on real hardware either NAKs outright or — worse — silently talks to a different chip
  that happens to answer at that address (§6.1's chip-ID-readback note is the only real-hardware
  backstop that exists for this today). This is §5.1 #11's "impossible address" gap, concretely
  instantiated.
- **A bus id with a recognized kind prefix but no real port behind it** — confirmed via `_bus_kind()`
  (`validate.py:46-50`): it only checks `bus_name.startswith(kind)` for `kind in ("i2c", "spi")`, so
  `"i2c2"` (RP2040 only has I2C0/I2C1), `"spi9"`, and even the bare, digit-less `"i2c"` itself (still
  `startswith("i2c")`) all resolve to a recognized kind. `codegen.py`'s
  `bus_id[len("i2c"):]`/`bus_id[len("spi"):]` then blindly emits whatever's left as the port number —
  `""` for the bare-`"i2c"` case, which would only fail at real `machine.I2C()` construction time.
- **A GPIO pin number outside the Pico W's real usable range** (negative, or ≥30, or one of the
  wireless-reserved GP23-25/29) — only int-ness is checked anywhere a pin is claimed
  (`_check_gpio_collisions()`'s own `claim()` helper). Same underlying gap §4.3 axis 10/§5.1 #7
  already flag for "pin that doesn't fit its bus"; this is the simpler "pin doesn't exist at all"
  sub-case of the same missing mechanism.
- **Pin that's real-hardware-illegal for its bus's peripheral index, or role-swapped within an
  otherwise-legal pair** — already flagged (§4.3 axis 10, §5.1 #7, §6.4), restated here only to keep
  this section's "what slips through" answer complete.

**(B) Probably already caught, but zero test proves it — a regression here would go unnoticed:**

- A **literal duplicate key in one TOML table** (`bus = "i2c0"` twice under one `[[instance]]`) —
  §5.1 #1 already asserts `tomllib`'s own `TOMLDecodeError` catches this, but no test in
  `test_buildgen_validate.py` actually constructs such a file and checks it.
- **`[instance.wiring]` bogus key** with no `_WIRING` match and no `warn_` prefix — §5.1 #5 already
  flags this as unconfirmed by an explicit test; still true after this pass (the `wf is None` branch
  in `_check_instance_wiring` at `validate.py:258-259` should catch it, but nothing exercises it
  directly with a fabricated field name).
- **Bool-for-int outside the one field already tested.** `test_device_bool_rejected_for_int_field`
  only covers `[device].hotspot_time_min`. The identical `isinstance(x, int) and not isinstance(x,
  bool)` pattern also guards `frequency`/`timeout` (bus level) and `address`/`max_size`/
  `trigger_sec` (instance level), per §5.3's own note — but only the device-level field has a test
  actually passing `true`/`false` through it.
- **Float-for-int**, same story as bool-for-int: the pattern rejects it everywhere by construction
  (a Python `float` is never an `int`), but no test passes e.g. `frequency = 100000.0` or `address =
  119.0` through any field to confirm it.

**(C) A genuinely new finding from this pass: two different "must be unique" identity spaces, only
one of which is actually checked.**

Confirmed by reading `validate.py`, `model.py`, and `codegen.py` together: an instance has **two
separate name-like identities**, and only one has a dedicated collision check.

- `spec.resolved_name` (from each driver's `_NAME` constant + `name_ext`, via `_instance_name()`) is
  the REST/status-key identity — checked by `_check_instance_name_collisions()` (`validate.py:170`),
  with its own test (`test_instance_name_collision_via_distinct_drivers_same_resolved_name`).
- `instance_label(key)` (`model.py:26-28`, `f"{driver}_{name_ext}" if name_ext else driver`) is a
  **different** identity — the actual Python global variable name `codegen.py` assigns each
  instance's constructed object to (`ctx.instance_var()` → `_identifier(instance_label(key), ...)`).
  `_identifier()` only checks the string is a *syntactically legal* Python identifier
  (`str.isidentifier()`/not a keyword) — it never checks it's *unique* among the device's other
  instances.

With today's 6 real driver names (none contains an underscore that could line up with another
driver+`name_ext` combination — e.g. nothing is named like `"scd30_a"`), the two identity spaces
can't actually be made to collide, so this isn't a live bug today and isn't a "gap" in the same sense
as (A) above. But it's structurally latent, not just theoretical: a future driver whose module name
contains an underscore (ties back to §6.3's onboarding-a-new-driver rough edge — one more thing that
class of change would need to get right) could produce two instances that validate cleanly
(different `resolved_name`s, so `_check_instance_name_collisions()` passes) but silently share one
generated Python variable — the second construction line would silently overwrite the first
instance's global, and anything wired to the "shadowed" instance would receive the wrong live object
at runtime, with no `BuildError` anywhere in the path. Worth a dedicated direct-internals test (same
style as the existing `resolved_name`-collision test, since no real driver name can reach it via a
TOML fixture) whenever this area is worked on, not urgent on its own.

**One more currently-unreachable-but-real case, noted while checking (C):** §5.1 #12 ("duplicate CS
pins on SPI") is, today, in the same boat — `_check_gpio_collisions()`'s shared `claims` dict would
catch two `cs_pin`-bearing instances colliding, but `fram` is the *only* driver with a `cs_pin`
field and it's a forced singleton, so the current driver catalog can never actually produce two
`cs_pin` claims to collide. Like (C), this needs a direct-internals test against a synthetic model
rather than a real TOML fixture if it's ever locked in, not a gap in the check itself.

### 7.3 Still to do

- Decide with the project owner which of §7.1's "valid but untested" cases become real fixtures vs.
  targeted `validate.py`/`generate.py`-internals tests, matching the existing suite's own mix.
- §7.2(C)'s identity-space finding should get a short mention added wherever §6.3's buildspec.py
  onboarding gap eventually gets written up as an implementation task — the two are related (both
  are "a new driver can silently violate an assumption the existing checks don't cover").
- Keep collecting with the project owner before finalizing which of §7.1/§7.2 become real test
  files.

## 8. Consolidated status: every finding from this whole brainstorming (2026-09-10)

Every item found across §2/§4/§5/§6/§7 above, in one place, each tagged with what it still needs:
**[FIX]** buildgen code needs a new or extended check that doesn't exist today; **[TEST]** the
underlying behavior is believed correct already, but no test proves it — a regression here would go
unnoticed; **[DECIDE]** blocked on an open design question the project owner has to resolve before
either FIX or TEST work can be scoped; **[COSMETIC]** a real but non-blocking message-quality note.
Several items carry more than one tag. Nothing in this section is new analysis — it's an index into
what §2/§4/§5/§6/§7 already found, so none of it gets lost or has to be re-derived later.
**Clarifying how this relates to §4.4/§5.4/§6.5/§7.3's own "Still to do" lists, added during the
2026-09-10 bird's-eye pass so there's no ambiguity about which list is authoritative**: those four
subsections remain the local, in-context next-steps for their own section; §8 is the flattened,
cross-referenced master index over all of them plus §2's mechanism — read §8 to find everything at
once, read the local "Still to do" for a given section's own framing/context. Neither is stale
relative to the other as of this pass; if they ever diverge, the more specific local section wins
and §8 needs updating to match.

### 8.0 The standing contract every `[FIX]` below must be built to (already settled, not new)

The project owner's restated requirement — every failure must cancel the whole build, never let an
invalid build complete, and always fail with a clear, human-readable message pointing at exactly
what to revise — is not a new rule this document is introducing. It's `BUILD_CHAIN_PLAN.md`'s own
"Build/generator script quality bar" section, settled before Session 3 ever started:

- *"Never produce a corrupted or partial build. On any detected error, abort the entire build
  immediately — no partial `build/<device>/` output left behind that could be mistaken for a real
  artifact."*
- *"Fail loudly, clearly, and human-readably. A plain, actionable message naming exactly what's
  wrong and where (which device, which instance, which field) — not a raw traceback, not a silent
  wrong-default fallback."*

Confirmed directly against the actual code (not just the plan doc) while building §5/§7 above: every
existing check in `buildgen/validate.py` already raises `buildgen.errors.BuildError` with
`instance=`/`field=` naming exactly what's wrong (the one confirmed exception is `codegen.py`'s
`_identifier()`, §6.2/8.4 below — cosmetic, not a partial-build risk, since it still raises). There
is no code path in the current implementation that degrades, warns-and-continues, or emits partial
output on error — `build_model()`/`generate_device()` either fully succeed or raise before any
output is produced. **Every `[FIX]` item below must hold to this exact same bar**: a new check that
only warns, or that lets generation proceed past a detected problem, would violate a rule that
already governs every check that exists today — not a new bar being raised for new code specifically.

### 8.1 §2's wiring-defaults mechanism — entirely unimplemented

- **[FIX] [DECIDE]** The whole `_Default<Field>` provider mechanism (§2.1-§2.7): AST-discovery of
  `_Default<ToMLFieldInPascalCase>.__init__`, the `{default = true, ...}` TOML shape, inline
  construction at the wiring call-site (§2.6), and `graph.py`'s "no construction-order edge for a
  default selection" branch.
- **[FIX] [DECIDE]** §2.9's generalization: splitting `comp_source` into independent per-value
  fields (placeholder names `temperature_source`/`humidity_source`), the generic name-matched
  `{source, field}` resolution `warn_*` already uses, extended to every measurement-value wiring
  field project-wide — plus the real `src/` change this requires (`SGP40_Reader.__init__` moving
  from one `comp_source` parameter to two independent value-getters).
- **[DECIDE]** §2.8's three open implementation questions (unknown/wrong-type keys inside a
  `{default = true, ...}` sub-table; whether an `attr`-mode default provider's target attribute
  gets verified to exist; the exact `validate.py` branch point distinguishing a default selection
  from a plain reference) must be resolved before either FIX can start.
- **[TEST]** §3's own standing requirement: every `src/` change this mechanism needs
  (`_DefaultCompSource`, `_DefaultSignalSink`, the two-value-getter `SGP40_Reader` change) gets its
  own `tests/` coverage — functioning, resilience, and coverage — to the same bar as any other
  `src/` promotion, not a buildgen-only shortcut.

### 8.2 §4's clean-build matrix gaps

- **[FIX] [TEST]** No-buses-at-all is currently unbuildable (`_check_bus_tables()` unconditionally
  requires `[bus.*]`), even though "no sensors, no FRAM" is a logically valid, simplest-possible
  device shape.
- **[FIX] [TEST]** Bus pins are never checked against the RP2040's real, fixed per-GPIO
  I2C0/I2C1/SPI0/SPI1 capability table (§4.3 axis 10's own transcription of Pico W datasheet Figure
  2/4) — an illegal pin currently only fails at real `machine.I2C()`/`machine.SPI()` construction
  time, not as a `BuildError`. Two sub-parts, per §4.3's own scope note: (a) is this GPIO number
  real and not one of GP23-25/29 (wireless-reserved) — applies to **every** claimed pin device-wide,
  bus and instance-exclusive (`irq_pin`/`cs_pin`/neopixel `pin`) alike; (b) does this specific bus's
  pin assignment match its peripheral index and role (SDA vs SCL, RX vs TX vs SCK) — inherently
  bus-pin-only, since an IRQ/CS/data pin has no peripheral role to check.
- **[FIX] [TEST]** Pin **role** within an otherwise-legal pair (§6.4 — `scl_pin`/`sda_pin` or
  `sck_pin`/`mosi_pin`/`miso_pin` transposed) needs checking, not just peripheral-index membership —
  **confirmed by the project owner this session as scoped work**, folds into the same fix as the
  bullet above (one mechanism, both checks).
- **[FIX] [TEST]** Bus id with a recognized kind prefix but no real port behind it (`i2c2`, bare
  `i2c`, `spi9`) — `_bus_kind()` only checks the prefix, confirmed via direct code read.

### 8.3 §5's must-fail matrix gaps

- **[TEST]** §5.1 #1: literal duplicate key in one TOML table — code (via `tomllib`) is believed
  correct; no test constructs one.
- **[FIX] [TEST]** §5.1 #4: `[device].hotspot_password` has no type/shape check at all (only
  presence). Same bullet also covers the general array/inline-table-where-scalar-expected gap
  (`pin = [5]`, `bus = ["i2c0"]`) for every field not already covered.
- **[TEST]** §5.1 #5: `[instance.wiring]` bogus-key catch-all (`wiring.frobnicate = "x"`, no
  `_WIRING` match, no `warn_` prefix) — the `wf is None` branch should already catch this; no test
  exercises it.
- **[FIX] [DECIDE]** §5.1 #6 / §5.2: driver-declared value range/exact-value checking (scd30's
  `timeout` headroom is a floor `@requires` already covers conditionally — see §6.2's correction —
  but nothing checks an *unconditional* sane range on `frequency`/`timeout`/`trigger_sec`/
  `max_size`/`hotspot_time_min`/`conn_fail_to_hotspot`, per §7.2(A)'s concrete field list). Needs
  the `_LIMITS`-style mechanism sketched in §5.2, **not agreed/implemented** — min/max-with-`None`
  shape vs. an enumerated-choices shape (or both) is the blocking decision.
- **[FIX] [TEST] [DECIDE]** §5.1 #11: impossible `address` value (bmp3xx outside `{0x76, 0x77}`) —
  same blocked mechanism as the bullet above (an enumerated set, not a range, so needs whichever of
  §5.2's two shapes — or both — gets decided).
- **[TEST]** §5.1 #12: duplicate CS pins on SPI — the existing global-pin-collision check already
  subsumes this structurally, but the current driver catalog can't produce two `cs_pin`-bearing
  instances to exercise it (`fram` is the only one and it's a forced singleton) — needs a
  direct-internals test against a synthetic model, the same style as
  `test_instance_name_collision_via_distinct_drivers_same_resolved_name`, not a real TOML fixture.
- **[TEST]** §5.3: bool-for-int and float-for-int are only tested on one device-level field
  (`hotspot_time_min`); the identical `isinstance` pattern also guards `frequency`/`timeout`
  (bus level) and `address`/`max_size`/`trigger_sec` (instance level) with no test per field.
- **[DECIDE]** §5.3: self-referential wiring (an instance's own wiring field pointing at itself) —
  genuinely unresolved whether this should be invalid at all; needs a project-owner ruling before
  it can become either a FIX or a confirmed non-issue.
- **[FIX] [TEST]** §5.3: empty `[[instance]]` array / fully empty device — same underlying fix as
  §8.2's "no buses at all" gap, not a separate mechanism.

### 8.4 §6's human-factors findings

- **[FIX] [DECIDE]** §6.3: `buildspec.py`'s hand-maintained schema is a second, independently
  fallible source of truth alongside `driver_registry.py`'s fully-automatic one — a new driver
  registered in one but not the other currently fails loud, but with a misleading message. Needs a
  decision: make `buildspec.py`'s facts AST-derivable the way `_WIRING`/`_Default*` already are, or
  (smaller fix) special-case the error message when a driver resolves via `driver_registry` but is
  absent from every `buildspec.py` dict, so it names the real cause instead of looking like a TOML
  typo. **[TEST]** either way: a driver resolvable by `driver_registry` but unregistered in
  `buildspec.py` needs its own must-fail fixture.
- **[COSMETIC]** §6.2: the `[instance]`-instead-of-`[[instance]]` mistake already fails, but with a
  message ("missing a 'driver' field") that doesn't point at the real mistake (wrong table syntax).
  Not a coverage gap — a message-wording improvement only, if error messages are ever revisited.
- **[COSMETIC] [FIX]** §6.2: `codegen.py`'s `_identifier()` is the one `BuildError` call site in the
  reviewed codebase that doesn't pass `instance=`/`field=` like every other check does — small,
  mechanical consistency fix, not a functional gap (it already raises, so §8.0's contract already
  holds; this is only about the error naming exactly what/where per that same contract's second
  bullet).

### 8.5 §7's test-suite cross-check findings

- **[TEST]** §7.1's nine valid-but-currently-untested combinations, all needing either a fixture or
  a targeted internals test (no code fix implied unless writing the test reveals an actual bug):
  FRAM entirely absent; the single-I2C-no-SPI topology that implies; notification with zero `warn_*`
  wired; device-level `fram_target` left unwired with FRAM present; device-level `led_target` left
  unwired all the way through codegen (not just validate); two bmp3xx on one bus at 0x76/0x77;
  bus-vs-bus pin collision; SPI's own required pins missing individually; `[device].name`'s own
  type/non-emptiness check.
- **[FIX] [TEST]** §7.2(A)'s concrete field list for the §5.2 range-check mechanism (folded into
  §8.3's `_LIMITS` bullet above, listed there in full so it isn't duplicated here) plus the
  confirmed-gap bus-port-suffix/GPIO-range/pin-fit items (already in §8.2).
- **[TEST]** §7.2(B): duplicate-TOML-key test, `[instance.wiring]` bogus-key test, and
  bool/float-for-int per field — all the same items as §8.3's corresponding bullets, cross-referenced
  here since §7 is where they were re-confirmed against the actual test suite.
- **[FIX] [TEST]** §7.2(C): `instance_label()` (the codegen-time Python-variable identity) has no
  uniqueness check of its own — only `resolved_name` (the REST-key identity) does. Currently
  unreachable with the 6 real driver names, but structurally latent for a future driver whose module
  name contains an underscore. Needs a `_check_instance_label_collisions()`-equivalent (or folded
  into the existing `_check_instance_name_collisions()`), tested the same direct-internals way as
  §8.3's CS-pin bullet (no real driver name can reach it via a TOML fixture today).

## 9. Scope boundary: does a successfully-generated build artifact get run through the test suite?

Confirmed directly against `BUILD_CHAIN_PLAN.md` (not assumed): **the project owner's recollection
is correct — this is explicitly out of the current (Session 3) scope, and is planned for later
sessions, not this one.**

- Session 3's own "Correctness proof depth" note states this plainly: generated output is proven
  syntactically valid Python (`ast.parse()`) matching the documented construction-order/wiring shape
  — **not executed under the real MicroPython Unix-port interpreter.** `buildgen/` is deliberately
  AST-only and never imports `src/`, so it structurally cannot boot what it generates itself.
- **Session 5 ("Digital twin generalization")** is explicitly tasked with this: *"consumes the
  Session 3 generated module directly, replacing `configure_i2c_wiring("wozi"|"dev")`'s 2-profile
  enum"* — this is what actually boots a generated module under the digital-twin hardware-fake
  environment, the same environment `tests/test_digital_twin_*.py` already exercises for the
  hand-written `sensortask_wozi.py`/`sensortask_dev.py` files today.
- **Session 6 ("Build chain + CI matrix + `build/` artifact directory")** is where this presumably
  gets wired into an actual end-to-end pipeline — generate, then run the full test suite (including
  the digital-twin boot) against what was generated, per device, in CI. `BUILD_CHAIN_PLAN.md`'s own
  "Testing" bullet under "Core design decisions" already anticipates this shape: *"only the
  device-specific slice (generated wiring module, generated website definitions, digital-twin boot
  of that config) runs once per device in CI."*

So: nothing in this whole brainstorming session (§2-§8 above) should be read as needing a
Session-3-scope fix to "run generated code through tests" — that capability doesn't exist yet by
design, and every `[TEST]` tag in §8 above means a `buildgen/`-level test (validating the TOML/the
generated *source text*, under `tests_scripts/`, real CPython), never a test that boots the
generated module. Whether/how §8's eventual fixes also need a corresponding digital-twin-boot test
once Session 5 lands is that session's own question to pick up, not this document's to resolve now.
