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

**Open sub-question, not yet resolved**: `Temp` happens to be named identically on `SCD30` and
`BMP3XX` today by coincidence, not by any enforced convention. Should buildgen match purely by
attribute name (simplest, consistent with `warn_*`'s existing precedent — "does `source`'s
`get_data()` result have an attribute named `field`"), or should each measurement field carry an
explicit property/unit tag so a future sensor naming the same physical quantity differently (e.g.
`"Temperature"` instead of `"Temp"`) is still recognized as interchangeable? Name-matching needs no
new machinery; a tagging system is more robust against naming drift but doesn't exist anywhere in
this codebase yet.

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

1. **Sensor population** — which of {scd30, sgp40, bmp3xx} are present. With §2 landed, all 8
   subsets of the 3-element set become legal (no more sgp40⇒scd30 pruning).
2. **FRAM presence** — with / without.
3. **Sensor↔sensor wiring** (sgp40's `comp_source` specifically) — real scd30 reference / explicit
   default with TOML-authored constants / not applicable when sgp40 absent.
4. **Sensor↔FRAM wiring** (`fram_target` on scd30/sgp40/bmp3xx/neopixel) — full (every present
   instance wires it) / partial (some do, some don't) / none (FRAM present but nothing wires to
   it) / N/A (FRAM absent).
5. **Notification↔signal wiring** (`warn_co2`/`warn_voc`/`warn_hum`) — full / partial / none, each
   individually gated on whether a suitable `source` instance (scd30 for CO2/Hum, sgp40 for VOC)
   is present at all.
6. **Notification↔neopixel wiring** (`signal_sink`) — real neopixel reference / explicit no-op
   default.
7. **Device-level `led_target`** (conn↔neopixel) — wired / not-wired, when neopixel present.
8. **Device-level `fram_target`** (sysfunct↔FRAM) — wired / not-wired, when FRAM present.
9. **Multi-instance variants** — 2× scd30, 2× sgp40 (name_ext-disambiguated) — where sensor↔sensor
   wiring (axis 3) becomes a genuinely free per-instance choice: each sgp40 instance can
   independently point at a different scd30 instance, the same scd30 instance, or use the explicit
   default — this is where "full vs. partial wiring against different sensors measuring the same
   property" lives.
10. **Shared-property cross-wiring — RESOLVED, generalized (2026-09-10, see §2.9)**: not scoped to
    `comp_source`/temperature specifically. Every individual measurement value must be freely
    selectable for wiring from any producer exposing that same property, uniformly, the same way
    `warn_*` already works — full survey and the `comp_source`→per-value-field consequence are in
    §2.9. Remaining open sub-question (§2.9's last paragraph): name-matching vs. an explicit
    property/unit tag for cross-driver field-identity matching.
11. **Bus topology** — all sensors on one shared bus vs. spread across separate buses vs. i2c+spi
    mixed.
12. **name_ext on a singleton-adjacent instance** — giving the sole scd30 instance a non-empty
    `name_ext` anyway (legal, just unusual).

### 4.4 Still to do

- Enumerate the actual cross-product of axes 1-8 (pruned by §4.2), decide which become individual
  TOML fixtures vs. which get covered by targeted unit tests against `validate.py`/`codegen.py`
  directly (matching the existing `test_buildgen_validate.py` pattern of driving internals
  directly for cases no real/6-device TOML can reach).
- Resolve §2.9's name-matching-vs-unit-tag open sub-question with the project owner.
- Design the multi-instance (axis 9) fixture set — likely extends
  `tests_scripts/buildgen_fixtures/novel_combo.toml` or adds a sibling fixture, not yet decided.
- Once §2.9's per-value wiring shape is finalized, axis 3 (sensor↔sensor wiring) needs re-wording
  in terms of it (temperature_source/humidity_source independently, not one comp_source choice) —
  not yet done here.
- Keep collecting axes/combinations with the project owner before finalizing which become real
  test files.
