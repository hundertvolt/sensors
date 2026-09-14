# ISL29125 buildgen migration — requirements

A temporary, living requirements/tracking file for one unit of work: porting the ISL29125 RGB
colour sensor driver — already promoted to `src/`, real-hardware-verified, and fully tested on
`main` — onto this branch's buildgen (TOML → generated firmware) architecture, which `main` does
not have. Same shape as `UART_PROMOTION_REQUIREMENTS.md` (now retired): a phase-by-phase plan this
session updates as it goes, deleted once the work lands and is reconciled. **Read this whole file
before making any change**, then re-verify every factual claim in it against the actual current
source — it was written by another session reading a snapshot of both branches on 2026-09-14; the
branches may have moved, and some of its own findings are flagged below as needing your own
confirmation rather than being asserted as settled.

## 0. Ground rules carried over from CLAUDE.md/SPECIFICATION.md — do not re-derive, just follow

- **Step-session workflow** (CLAUDE.md "Working agreements"): refine scope → ask blocking
  questions early (Section 9 below has a first pass) → write tests first (TDD) against the settled
  scope → implement against those tests → maximize coverage → **stop and report back before
  merging or starting unrelated scope.** This file's own phases are that refined scope.
- **Memory-safety discipline is a standing rule, sharpened recently** (CLAUDE.md "Hard rules",
  SPECIFICATION.md Part I.4): every test — not just soak/hammer ones — must pass with
  `gc.threshold(-1)` (MicroPython's real default) and **zero `MemoryError`s, caught-and-logged
  included**, with no `gc.collect()` calls or nonstandard `gc` settings anywhere in the business
  logic or test setup, *before* it's ever run again with the project's `gc.threshold(32768)`
  enabled (which it must then also still pass). A `gc.threshold()`/`gc.collect()` call is never an
  acceptable fix for a real allocation-pattern defect — chunk, reuse/pre-allocate, or stream
  instead. This applies to every new test this session adds, digital-twin and (once gated in,
  Section 6) real hardware alike.
- **"Driver/DUT process separation"** (new architectural rule from PR #82, `digital_twin/README.md`
  and `run_generic_integration.py`'s own comments): request-driving/response-observing test code
  runs host-side against the twin's real HTTP server, not inside the twin process sharing the
  DUT's own heap — a known false-positive-prone anti-pattern. Read that rule's own doc before
  writing any new digital-twin-driving test/script.
- **Flag, don't silently change** (CLAUDE.md, BUILD_CHAIN_PLAN.md): if this port's own review
  surfaces a discrepancy between the ported driver's behavior and this repo's current guidelines,
  or between two files that should agree, report it and discuss before changing it — the same
  treatment already required for `src/`-wide consistency scans.
- **A session needs the project owner's own go-ahead, given directly in that session's own
  conversation, before running anything against real hardware** (CLAUDE.md). The user's own
  instruction that started this work already says a *separate*, already-prepared real-hardware
  session/rig is being spun up from a sibling branch for exactly this purpose — this branch's own
  session should NOT attempt real-hardware commands itself unless the project owner explicitly
  says so in *this* session's conversation. Build everything so that a real-hardware validation
  pass is ready to run (Section 6), but treat the digital-twin/mock tiers as this session's own
  finish line.
- **Header-comment discipline**: one header block per module/function/class, capped at 3 lines.
  The ported driver's existing header already fits this — check it still does after any edits.
- **Bus-hazard four-tier rule** (CLAUDE.md, standing/explicit): any new I2C/SPI device gets
  same-device read-vs-write, cross-device interleaving, and an address/command sweep, across all
  four tiers that apply — mock (`tests/test_bus_hazard_multi_device.py`), digital twin
  (`tests/test_digital_twin_bus_hazard_concurrency.py`), real hardware flash
  (`tests_hardware/flash/test_bus_concurrency.py` + `tests_hardware/bus_topology.py`), real
  hardware bench-under-API-load (`tests_hardware/bench/test_bus_concurrency_under_api_load.py`).
  `main` already has all four for ISL29125 (Section 1) — port and adapt them, don't design fresh.
- **PR workflow**: this branch's PR must point at `claude/automated-build-chain-nuzumw` (this
  work's own parent branch), never at `main` — `main` never had buildgen and this work doesn't
  belong there. Subscribe to its own CI/review activity immediately once opened, and drive any
  failure to green per CLAUDE.md's PR babysitting rules before considering the session done.

## 1. What already exists on `main` — fully written, tested, real-hardware-verified

`main` merged PR #75 "Promote the ISL29125 RGB colour sensor to `src/` (dev variant only)"
(merge commit `32e9a8e`) — 62 files, ~10.3k lines, built entirely against the **pre-buildgen**
hand-written `src/sensortask_dev.py`/`src/sensortask_wozi.py` shape (`main` has no `buildgen/`
directory at all — confirm with `git show origin/main:buildgen 2>&1` if in doubt). The real
content, in commit order (`git log --oneline origin/main` from merge-base `348be6d` forward, or
just read the files at `origin/main` HEAD directly — don't rely on intermediate commits, several
things changed again after their first landing, e.g. gain-ratio calibration UI):

- `src/asy_isl29125_driver.py` (1387 lines) — the driver itself. Two-layer shape per
  SPECIFICATION.md Part C: `ISL29125_I2C`/`ISL29125_DeviceSession` (protocol layer) and
  `ISL29125_Reader(SensorReaderConfig)` (asyncio task/config layer, `_NAME = const("ISL29125")`).
  Already follows the `asy_<name>_driver.py` → `*_Reader(SensorReaderConfig)` convention
  `buildgen/driver_registry.py` auto-resolves via AST — **this specific file should need no
  `_OVERRIDES` entry**, unlike `uart_link` (verify this holds once ported, don't assume).
  `__init__(self, i2c, irq_pin, address=0x44, trigger_sec=1, max_module_error=5, cfg_path="",
  fram=None, history_length=10, debug=None)` — **no `name_ext` parameter**, unlike
  SCD30/SGP40/BMP3xx/UartLinkExerciser. Decide (Section 9, question 1) whether to add one for
  architectural consistency even though only one instance is ever wired.
  Address `0x44` is **hardware-fixed, no address-select pin** (the driver's own comment says so
  directly) — this is `FIXED_ADDRESS_DRIVERS` territory (like SCD30/SGP40), not
  `ADDRESS_CAPABLE_DRIVERS` (like BMP3xx) — verify this against the driver source and datasheet
  yourself, don't just trust this summary.
- `digital_twin/_isl29125_chip.py` (321 lines) — the twin-tier chip fake. Models the destructive
  0x08 status read, active-low INT line (idles HIGH — open-drain + pull-up), `BOUTF` high at
  power-up, per-instance non-nominal range ratio, and a real conversion timer that must keep
  running for a post-range-switch settle to see fresh data (two real chip-fake bugs were found and
  fixed by the twin tests during development — read the driver's own git history if you want the
  detail, not just the current file).
- `tests/test_asy_isl29125_driver.py` (3090 lines), `tests/test_digital_twin_isl29125.py` (511
  lines), `tests/test_digital_twin_isl29125_autorange.py` (414 lines) — unit + digital-twin
  coverage, including a dedicated autorange-behavior suite (continuity/span-continuity across a
  real range switch, hysteresis, hue/saturation/CCT invariance, the single-clipped-channel peak
  rule, the dead-interrupt path, gain-ratio-convergence error reduction).
- `tests_hardware/isl29125_conformance.py`, `tests_hardware/device_scripts/isl29125_*.py` (6
  files: `mechanism_envelope`, `lighting_scenarios`, `plausibility_read`, `real_irq_edge`,
  `mock_conformance_probe`, `cross_device_concurrency`, `same_device_rw_concurrency`) — real
  hardware validation scripts, already run against the actual dev board (per the user: "already
  tested on real hardware").
- `datasheets/isl29125/REN_isl29125_DST_20151201_1.pdf` — the datasheet (FN8424 Rev 3.00), already
  in the repo per CLAUDE.md's "read the datasheet first" rule.
- `src/math_helpers.py` gained real additions (95 lines) — likely CCT/colour-space maths shared
  helpers. Check what's new there against what's already in our branch's `math_helpers.py` (it may
  have diverged independently since the branches split) before porting — this is exactly the kind
  of file a naive merge could silently regress.
- `src/sensortask_dev.py` (hand-written, pre-buildgen) wired one `ISL29125_Reader` instance:
  **i2c1, IRQ on GPIO6 (`Pin(6, mode=Pin.IN, pull=Pin.PULL_UP)`)**, constructed after
  `notify_service.finalize()`, no `address=` override (uses the fixed 0x44 default), no
  `trigger_sec=` override (uses the 1s default). This is real, bench-validated wiring — **carry
  the `i2c1`/`GPIO6` facts into `devices/dev.toml` as-is**; don't re-derive or guess a different
  pin. Our branch's `devices/dev.toml` `[bus.i2c1]` is `scl=15, sda=14` (SCD30 also lives there,
  `irq_pin=11`) — GPIO6 is currently unused in our `dev.toml`, so there is no pin conflict, but
  re-check this yourself against the file's current content before writing anything (something
  else may have claimed GPIO6 since this summary was written).
- `html/definitions/dev.json`, `js/definitions.js`, `js/field-format.js`, `js/mock-server.js`,
  `mockdata/dev.json` — hand-edited website wiring (`main` predates the `@web`/`@web-group`
  comment-tag generation system entirely, so it has no other way to do this). **The authoritative,
  final field catalog** (after later commits like `f05f82d` changed the calibration UI) is what's
  actually at `origin/main:html/definitions/dev.json` HEAD right now — re-fetch and re-read it
  yourself (`git show origin/main:html/definitions/dev.json`), don't trust a stale copy pasted into
  this file or into any earlier session's chat transcript. As of this writing it defines:
  - A `measurements` group `ISL29125` with fields `Lux`, `R`/`G`/`B` (nested under a `path:
    ["RGB", ...]`), `H`/`S`/`Bri` (nested under `path: ["HSB", ...]`), `CCT`, `RangeAct`,
    `GainMeas`, `TS` — several with a `decimals` rounding hint.
  - A `sensors` (settable config) group `ISL29125` with `SampleInterv`, `Resolution` (enum
    12/16-bit), `RangeAuto` (toggle), `Range` (enum 375/10000 lx), `AutoRangeThresh`,
    `AutoRangeDwell`, `IrCompOffset` (enum), `IrCompAdjust`, `FiltCoeff`, `GainRatio`,
    `ISLCalibrate` (a dispatch-only command field, like SGP40's `ForceCalRef` — always re-runs on
    submit, never compared against a stored value).
  - **Important, and NOT yet supported by this branch's `@web` tag system**: `path` (a nested
    field lookup, e.g. `["RGB", "R"]`) and `decimals` (a rounding hint applied at format time) are
    both real features `main` added specifically for this driver, entirely independently of
    buildgen (which doesn't exist there). Grepping this branch's `buildgen/web_tag.py`,
    `js/definitions.js`, `js/field-format.js`, `js/mock-server.js` for `path`/`decimals` turned up
    nothing — **this branch's tag-driven generation pipeline does not have this capability yet and
    it needs to be added, not just consumed.** See Section 4.
  - The driver's own `get_data()` return type is a **flat** namedtuple (`ISL29125 = namedtuple(...,
    ("Lux", "Red", "Green", "Blue", "Hue", "Sat", "Bri", "CCT", "RangeAct", "GainMeas", "TS"))`) —
    so the `RGB`/`HSB` nesting seen in the JSON is produced somewhere else (the driver has its own
    comment near its measurement-serialization code, something like "one-level contract cannot
    express..." — read that comment directly in the ported file and follow where it points; do not
    guess at the mechanism from this summary). Figure out whether that nesting already happens
    generically (e.g. in `config_manager.py`'s `make_dict()`, SPECIFICATION.md Part C.6) or is a
    driver-specific override, and whether it needs any buildgen/codegen change at all, or whether
    it's purely a `js/`-side (`path`-based) concern once the flat-but-nested-in-JSON response
    already exists. This is a real open question this session must resolve by reading code, not by
    assuming either answer.
- `tests_hardware/bus_topology.py`, `tests_hardware/conftest.py`,
  `tests_hardware/error_log_helpers.py`, several `tests_hardware/bench/`/`tests_hardware/flash/`
  files, `DEVICE_REFERENCE.md`, `BACKLOG.md`, `CLAUDE.md`, `SPECIFICATION.md`,
  `THIRD_PARTY_LICENSES.md`, `dev_legacy/README.md`, `digital_twin/README.md`,
  `digital_twin/run_dev_integration.py`, `digital_twin/machine.py`, `tests_js/*` — all touched;
  read each one's actual diff on `main` (`git log --oneline origin/main -- <path>`) rather than
  relying on the file list in this document, which is a snapshot, not a live index.

**None of the above exists on this branch yet.** `git show origin/main:buildgen` fails with "path
exists on disk, but not in origin/main" — i.e. `buildgen/` is entirely absent from `main`, and
conversely `origin/main:src/asy_isl29125_driver.py` etc. are entirely absent from this branch. This
is not a mergeable pair of branches for this file set — do not attempt
`git merge origin/main`/`git cherry-pick` for the ISL29125-related commits; the surrounding files
they touch (`src/sensortask_dev.py`, `html/definitions/dev.json`, ...) have completely different,
incompatible shapes on the two branches (hand-written vs. buildgen-generated). Port the *content*
(driver logic, chip fake, tests, datasheet, requirements/decisions) by reading `main`'s files and
re-expressing them against this branch's actual current architecture — exactly the treatment
`4f8caf5` ("Port UART crossover-link promotion onto the buildgen model") already gave the UART
promotion. That commit (and its follow-ups `eea882d`/`442a559`/`09469f7`, all on this branch's own
history) is the direct precedent for this whole task — read it in full before starting.

## 2. Why this needs porting, not a raw copy

Every device's construction (`sensortask_<device>.py`) is now generated by `buildgen/` from
`devices/<device>.toml` (BUILD_CHAIN_PLAN.md). Adding a sensor means teaching the generator about
it, not hand-editing a `sensortask_dev.py` that no longer exists as committed source (it's
build-output now, gitignored). The generic parts (config schema plumbing, error/logger fan-in,
FRAM wiring via a `fram=` constructor kwarg, task/timer collection) already work for *any*
`SensorReaderConfig` subclass with no driver-specific buildgen code at all — only the genuinely
driver-specific facts need new entries, in exactly the same small set of places every existing
driver (scd30/sgp40/bmp3xx) already has one:

| File | What needs a new row/branch for `isl29125` |
|---|---|
| `buildgen/buildspec.py` | `REQUIRED_TOML_FIELDS["isl29125"] = ("bus", "irq_pin")`; `OPTIONAL_TOML_FIELDS["isl29125"] = ("trigger_sec",)` — **not** `"address"`, per the fixed-address finding above (re-verify first); `BUS_KIND_BY_DRIVER["isl29125"] = "i2c"`. `ALLOWED_INSTANCE_FIELDS`/`BUS_ATTACHED_DRIVERS`/`FIXED_ADDRESS_DRIVERS` are all derived automatically from the two dicts above — don't hand-edit those. |
| `buildgen/codegen.py` | A new `_build_args_isl29125()` handler (closest existing shape: a hybrid of `_build_args_scd30`'s `irq_pin` positional arg and `_build_args_bmp3xx`'s `cfg_path`/optional-`trigger_sec` kwargs — `ISL29125_Reader` is a `SensorReaderConfig` like BMP3xx/SGP40, so it needs `cfg_path`, unlike bare-`SensorReader` SCD30), registered in `_BUILD_ARGS_HANDLERS`. |
| `buildgen/definitions.py` | Add `"isl29125"` to `_SENSOR_DRIVERS` so the website-definitions generator scans it for `@web`/`@web-group` tags. |
| `buildgen/driver_registry.py` | Probably **no change** — AST auto-resolution should find `ISL29125_Reader(SensorReaderConfig)` on its own. Confirm by actually running the generator against a `devices/dev.toml` with the new instance declared, not by inspection alone. |
| `buildgen/twin_wiring.py` | Probably **no change** — ISL29125 needs only the generic `fram_target` wiring every other sensor already gets for free; it has no `uart_link`-style special-cased bus-pairing need. Confirm, don't assume. |
| `buildgen/pico_gpio.py` | Probably **no change** — this only gained content for UART because of its distinct pin-role table; a plain I2C IRQ pin needs nothing new there. Confirm. |
| `devices/dev.toml` | New `[[instance]] driver = "isl29125"` entry: `bus = "i2c1"`, `irq_pin = 6`, `[instance.wiring] fram_target = "fram"`. Placed in the "sensor drivers" section, after the existing scd30/sgp40/bmp3xx entries (construction-order/FRAM-chunk-order consequences — see below). **No other `devices/*.toml` gets this** — dev only, per the user's instruction and `main`'s own "(dev variant only)" scoping. |
| `tests_hardware/bus_topology.py` | Add `I2CDeviceSpec("ISL29125", 0x44)` to `DEV_I2C_BUSES`' `port_id=1` bus's `devices` tuple, and `0x44: "ISL29125"` to `KNOWN_ADDRESSES`. This file is a hand-kept, tool-uncross-checked mirror of `devices/dev.toml` (its own docstring says so) — it will not update itself. |

**FRAM chunk order**: `AsyFramManager`'s allocator is a bump pointer — construction order is
on-chip layout order (CLAUDE.md/SPECIFICATION.md Part A.7). `main`'s hand-written
`sensortask_dev.py` deliberately constructed `isl_reader` *after* `notify_service.finalize()` so
chunks 1–7 stayed byte-identical to `wozi`'s own layout (chunks 8–9 were the new ones). On this
branch, `wozi` never gets an ISL29125 instance at all, so there is no equivalent "stay
byte-identical to wozi" constraint to preserve — buildgen's own construction order is whatever
`devices/dev.toml`'s instance-declaration order says. Placing the new `[[instance]]` after the
existing `scd30`/`sgp40`/`bmp3xx` entries (as suggested above) is a reasonable default, but **any
test asserting specific FRAM offsets/chunk counts for `dev`** (mirroring `main`'s own
`tests/test_sensortask_dev.py` chunk-offset assertions, ported into whatever this branch's
equivalent generated-`dev`-graph test is) needs updating to match whatever order you actually
choose — write that test to assert the property (N chunks, in *some* documented order), not a
magic offset copied from `main`, unless you have a real reason to match `main`'s numbers exactly.

## 3. `@web`/`@web-group` tags — port the field catalog as tags, not hand-edited JSON

`html/definitions/dev.json` is generated at build time on this branch (see the
`# regenerated by scripts/test.sh`/`buildgen-generated per-device build tree` notes in
`.gitignore`), not hand-maintained like on `main`. Every field `main`'s hand-written JSON exposes
must become a `# @web <Field> ...` / `# @web-group ...` comment tag on `src/asy_isl29125_driver.py`
itself (`buildgen/web_tag.py`'s grammar; see `src/asy_bmp3xx_driver.py`'s own tags, lines ~89-109,
for the closest existing worked example — irq-driven `SensorReaderConfig`, submit-group semantics,
`special:<value>=` sentinel labels for e.g. `FiltCoeff`'s `-1.0 = "Off"`). Cross-reference every
field in `main`'s current `html/definitions/dev.json` `ISL29125` groups (Section 1 above) against
this branch's `_FIELD_KNOWN_KEYS`/`_GROUP_KNOWN_KEYS` in `buildgen/web_tag.py` and decide, field by
field, whether the existing tag grammar already covers it or whether it needs the new `path`/
`decimals` keys from Section 4.

## 4. New capability: `path` and `decimals` in the `@web` tag system

This is genuinely new work, not a port — `main` invented `path`/`decimals` directly in
`js/definitions.js`/`js/field-format.js` because it never had a tag-generation layer to go through.
This branch does have one, and it needs to grow to cover the same need, becoming ISL29125's real
first consumer. Two independent things need extending, matched to each other:

1. **`buildgen/web_tag.py`**: add `path` and `decimals` to `_FIELD_KNOWN_KEYS`. `path` needs a
   value shape decision — `main`'s JSON uses a JSON array (`["RGB", "R"]`); the tag grammar's
   `_KV_RE` only captures a single quoted-or-bare scalar per `key=value` pair (see its regex) — you
   will likely want a syntax like `path="RGB.R"` (dot-joined, split at consumption time) rather
   than trying to embed a literal array inside one tag attribute. This is a real design decision,
   not a mechanical port — pick something that fits the existing grammar's actual shape, document
   it in SPECIFICATION.md Part H.5.1 (the `@web` tag's own design-rationale home), and give it full
   accept/reject test coverage per BUILD_CHAIN_PLAN.md's "every tag family gets the same bar"
   standing rule (quoted above in Section 0) — `tests_scripts/test_buildgen_web_tag.py` (or
   wherever this branch's existing `@web` tag tests live; locate them, don't guess the filename).
2. **`buildgen/definitions.py`**: thread the new `path`/`decimals` tag attributes through into the
   generated JSON's field objects, matching `main`'s own JSON shape exactly (`"path": [...]`,
   `"decimals": N`) so the `js/` side (below) doesn't need to know which branch's tooling produced
   the file.
3. **`js/definitions.js`**: port `main`'s own `resolveFieldValue()` nested-`path`-walking logic and
   `validateDefinitions()`'s validation of `path`/`decimals` (see `main`'s commit `196a02c`'s own
   diff for the exact shape it landed on — `git show 196a02c -- js/definitions.js` against a
   session with `main` fetched, or ask a sibling session/the project owner for the file content if
   `main` isn't reachable from this branch's own checkout).
4. **`js/field-format.js`**: port `formatFieldValue()`'s honoring of the `decimals` hint (`main`'s
   own commit message: "the one place anything in this stack rounds — no driver in `src/` does" —
   true on `main`; re-check it's still true on this branch before assuming no existing rounding
   logic conflicts).
5. **`js/mock-server.js`**: `jitterInPlace()` needs the same nested-path recursion `main` gave it
   (its own commit message says so directly), and `ISLCalibrate` (or whatever this branch's tag
   naming lands on for the calibration-trigger field) needs to join `SENSOR_QUIRK_FIELDS` — it's a
   dispatch-only command field, the same category `ForceCalRef`/`ContMeas`/`SGPResetVOC` already
   are in that same file.
6. **`tests_js/`**: `main`'s commit message notes `definitions.test.js` grew to validate *both*
   shipped definitions files where nothing did before — check this branch's own `tests_js/
   definitions.test.js` coverage and extend it the same way once `dev.json` actually has an
   ISL29125 section to validate against.

## 5. Test-tier checklist (write these; make them "bite" — CLAUDE.md's own phrasing)

Per CLAUDE.md's explicit instruction for this task ("wherever fitting — tiers, layers, and all
including functionality, resilience and max coverage tests (which should be 'biting' themselves,
not just executing')"), every tier below needs real assertions that would fail on a broken
implementation, not just exercise-and-ignore-the-result smoke tests:

- **Unit** (`tests/test_asy_isl29125_driver.py`, ported/adapted from `main`'s 3090-line file):
  protocol-layer register math, config schema push/get/recovery paths, the autorange state
  machine's own decision logic, calibration convergence/timeout, the destructive-status-read
  handling, IRQ-vs-periodic race resolution.
- **Digital twin** (`tests/test_digital_twin_isl29125.py`,
  `tests/test_digital_twin_isl29125_autorange.py`): the full real object graph against
  `digital_twin/_isl29125_chip.py`'s fake — continuity across range switches, hysteresis, hue/sat/
  CCT invariance under the modelled clipping, the dead-interrupt fallback path, gain-ratio
  convergence actually shrinking measured error. Follow the "driver/DUT process separation" rule
  (Section 0) for anything that drives requests against a running twin instance.
- **Buildgen-level** (`tests_scripts/test_buildgen_*.py` — `test_buildgen_driver_registry.py`,
  `test_buildgen_codegen.py`/equivalent, `test_buildgen_web_tag.py`/equivalent,
  `test_device_tomls.py`): confirm `isl29125` resolves correctly through
  `driver_registry.resolve_driver()`, generates a correct `build_system()` call for a fixture TOML
  with realistic field combinations (with/without `trigger_sec`, with/without `fram_target`), and
  that a *missing* required field (`irq_pin`) or a *wrong-bus-kind* `bus` reference fails loudly at
  build time — the same "abort conditions are themselves testable units" bar BUILD_CHAIN_PLAN.md
  states explicitly (quoted in Section 0-adjacent material above). Also extend
  `tests_scripts/buildgen_fixtures/novel_combo.toml` (or wherever this branch's synthetic
  multi-driver fixture lives — `4f8caf5`'s diff shows `uart_link` was added there; do the same for
  `isl29125`) so the fixture-driven tests actually exercise a device with this driver present.
- **Bus-hazard, all four tiers** (Section 0's standing rule): port and adapt
  `test_bus_hazard_multi_device.py`'s ISL29125 additions, `test_digital_twin_bus_hazard_concurrency
  .py`'s additions, and the two `tests_hardware/` files, from `main`.
- **Generic-integration / soak**: `digital_twin/run_generic_integration.py`'s CI suite
  (`scripts/_digital_twin_ci_suite.py`) builds `dev` generically from its TOML — once the TOML has
  an `isl29125` instance, the sensor is automatically part of every existing twin CI run (boot,
  soak, hammering, the two-gc-threshold pass) with **no additional wiring needed there** — but
  actually run it and check nothing about the new instance regresses timing/memory assumptions
  calibrated before it existed (e.g. `_SOAK_WARMUP_CYCLES`, mem-free plateau timing) — this is
  exactly the kind of thing PR #82 found was under-calibrated for `dev`'s heavier profile; a new
  sensor makes `dev` heavier still.
- **Real hardware** (gated on go-ahead, Section 6): `tests_hardware/isl29125_conformance.py`,
  the `device_scripts/isl29125_*.py` set, and the bus-hazard flash/bench-under-API-load tiers.

## 6. Real-hardware validation

**Do not run this yourself without the project owner's go-ahead given directly in this session's
own conversation** (Section 0). Everything up through Section 5 should be completable and fully
green without touching real hardware at all — the digital twin plus mock/unit/buildgen tiers are
this session's actual finish line. If/when go-ahead is given, `tests_hardware/README.md` is the
durable reference for prerequisites/environment/safety gates; the six `device_scripts/isl29125_*
.py` files ported from `main` (already validated there against real silicon, per the user) are the
starting point, not something to write from scratch.

## 7. Documentation

- **SPECIFICATION.md**: `main`'s own SPECIFICATION.md grew ISL29125-specific numbered requirements
  (its driver source comments reference things like "requirement 1 (C.11.5)", "requirement 17",
  "requirement 18") that don't exist in this branch's SPECIFICATION.md (this branch's Part C is the
  generic architecture spec extracted from the drivers already promoted here, not `main`'s own
  possibly-differently-numbered document). Before porting the driver file verbatim, either: (a)
  strip/renumber those comment references to point at wherever the equivalent generic guidance
  already lives in *this* branch's SPECIFICATION.md, or (b) if the referenced content is genuinely
  new (ISL-specific design decisions not yet captured anywhere on this branch), migrate it in as
  new SPECIFICATION.md content, numbered to fit this branch's own existing Part C/other-Part
  structure. Don't leave dangling references to a numbering scheme this branch doesn't have.
- **DEVICE_REFERENCE.md** (if this branch has an equivalent, or `main`'s own new-on-that-branch
  file — check): `main` added ISL29125 documentation here; port the relevant facts.
- **BACKLOG.md**: check `main`'s ISL29125-era BACKLOG.md changes for anything still-open that's
  relevant to this branch (most of `main`'s own churn there was process narrative that CLAUDE.md's
  pruning rule says drop, not port — use judgment).
- **`digital_twin/README.md`**: port the "What's here" addition documenting the ISL29125 chip fake,
  matching this branch's own current doc style/section structure (it has evolved further on this
  branch than on `main`, e.g. PR #82's "Driver/DUT process separation" section — don't clobber it).
- **THIRD_PARTY_LICENSES.md**: the driver's own header attributes "Jose D. Montoya (original
  MicroPython_ISL29125)" under MIT — port the corresponding license-file entry.
- **This file**: update it as phases complete; delete it once the work is done and reconciled with
  its own PR merged, exactly as `UART_PROMOTION_REQUIREMENTS.md` was retired
  (`706f9e0`/equivalent commit on `main`, or find this branch's own retirement precedent if UART's
  requirements file was retired here too — check).

## 8. Done criteria

- `devices/dev.toml` declares the `isl29125` instance; `devices/wozi.toml` and the other four real
  device TOMLs are untouched.
- `buildgen` generates a correct `dev` build with the new instance wired (bus, IRQ pin, FRAM
  target, error/logger/task-starter fan-in, webserver `sensors=` inclusion) with no manual
  post-generation edits.
- The website (`html/definitions/dev.json`, generated) carries a complete, correct ISL29125
  section in both `measurements` and `sensors`, matching `main`'s own field catalog (Section 1),
  produced entirely from `@web`/`@web-group` tags on `src/asy_isl29125_driver.py` — no hand-edited
  JSON.
- Every test tier in Section 5 (short of real hardware) passes, including the full CI suite twice
  (both `gc.threshold` settings, Section 0), with zero `MemoryError`s under either.
- `scripts/lint.sh`/`scripts/typecheck.sh`/`scripts/test.sh` all exit 0 across all eight scopes
  (CLAUDE.md "Code quality tooling").
- A draft PR exists, based on and pointing at `claude/automated-build-chain-nuzumw`, with a real
  description (what/why, not a file list), subscribed for CI/review activity, driven to a green,
  mergeable state per CLAUDE.md's PR babysitting rules.
- This file is deleted once the above holds and the PR reflects it.

## 9. Open questions worth resolving early (step-session workflow's clarifying-question round)

1. Give `ISL29125_Reader` a `name_ext` constructor parameter for architectural symmetry with every
   other buildgen-integrated sensor driver, even though `devices/dev.toml` only ever wires one
   instance today? (Recommendation: yes, for consistency and because it's a small, low-risk
   addition — but it's genuinely optional scope, flag it to the project owner if it feels like
   scope creep relative to "port what exists.")
2. `path` tag-value syntax (Section 4, item 1) — dot-joined string (`path="RGB.R"`) vs. some other
   spelling. Pick one, document the choice's rationale in SPECIFICATION.md Part H.5.1, don't leave
   it undocumented.
3. Whether the `RGB`/`HSB` JSON nesting (Section 1's namedtuple-vs-JSON-shape finding) needs any
   change to `config_manager.py`'s `make_dict()` / the webserver's measurement-response builder, or
   is purely a `js/`-side concern once the flat-but-structured response already exists — resolve by
   reading the actual driver code's own comment near its measurement serialization, not by
   guessing.
4. FRAM instance-declaration ordering in `devices/dev.toml` (Section 2) — any real reason to try to
   match `main`'s exact chunk numbering, or is "some documented, tested order" sufficient given
   `wozi` never carries this sensor and the two branches' FRAM layouts already diverged when
   buildgen was introduced?
