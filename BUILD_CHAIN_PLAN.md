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

Binds every session that writes build/generation logic — Session 1's wiring/schema validator,
Session 3's Python code generator, Session 4's website `definitions.json` generator, and Session
6's CI orchestration around them. Distinct from the sensor-code quality bar in one key way: a
build script's job includes catching every way its own input could be wrong, and refusing to
proceed rather than degrading:

- **Detect and react to every error class that would make a real build impossible** —
  misconfigured/malformed TOML, an unresolved wiring reference, a driver-class/type mismatch, a
  REST/config-name collision with no disambiguating extension, a missing required pin/bus field, a
  copy-paste duplicate, or any other structurally broken definitions file. Typical real-world
  causes: misconfigured definition files, and plain wrong/missing/copy-pasted fields.
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
    not false-positive.
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
