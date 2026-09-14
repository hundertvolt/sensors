# Generating bus-hazard/concurrency tests from the TOML — problem statement and starting materials

A temporary, living requirements/tracking file for one unit of exploratory design-and-build work:
teaching `buildgen` to assemble a device's own worst-case bus-concurrency test coverage from its
TOML wiring, instead of every new driver needing its cross-device hazard tests hand-written by
whoever promotes it. Same shape as `UART_PROMOTION_REQUIREMENTS.md`/
`ISL29125_BUILDGEN_MIGRATION_REQUIREMENTS.md` (both now retired): a phase-by-phase plan this session
updates as it goes, deleted once the work lands. **This one is different from those two in one
important way: this is new design, not a port.** Nothing in this repo does this today — read
Section 0 before assuming otherwise. Treat every section below as a starting point for the step-
session workflow's own scoping/clarifying-question round (CLAUDE.md "Working agreements"), not as
settled requirements to implement literally.

## 0. The idea, in the project owner's own words

> I imagine the real bus concurrency tests as not too complicated. Every sensor module has two
> types of hazard tests and concurrency tests - sensor specific, and cross module. When a module is
> included in the TOML, the specific tests are imported - that probably mostly matches with today's
> status. The cross sensor tests are in the style of "what bad could this sensor do on the bus -
> concurrency, parallel sessions, timeouts, addresses, broadcasts, and many more" are imported into
> a per-bus scheme and then executed all in parallel, so the bus receives a worst case test in its
> actually configuration automatically - both in the twin and the hardware suites.

Two distinct kinds of coverage, per this vision:

1. **Sensor-specific hazard tests** — a driver's own known quirks (ISL29125's destructive `0x08`
   status read, SCD30's NVM write budget, ...). **Confirmed already mostly true today**: every
   promoted driver already has these, hand-written (Section 1). What's missing is only the
   *automatic inclusion* half — today a device TOML declaring a driver does nothing to pull its
   hazard tests into that device's own coverage; a human has to know to look.
2. **Generic cross-sensor bus hazards** — a reusable catalog of "what can go wrong when two+
   things share a bus" (concurrent read/write interleaving, parallel sessions, timeouts, address
   confusion, general-call/broadcast effects, and whatever else belongs in that catalog) that
   buildgen assembles **per bus, from the TOML's own wiring**, and runs **all combinations in
   parallel** against that bus's actual real occupants — for a device where `i2c1` carries
   SCD30+SGP40+ISL29125, the generated worst-case test drives all three at once, not pairwise, and
   this happens automatically the moment a TOML says so, in **both** the digital-twin tier and the
   real-hardware tier. **This does not exist yet at all** (Section 0 below).

## 1. What already exists — the manual version of half of this

Read `tests/test_bus_hazard_multi_device.py`, `tests/test_digital_twin_bus_hazard_concurrency.py`,
`tests_hardware/flash/test_bus_concurrency.py`, and
`tests_hardware/bench/test_bus_concurrency_under_api_load.py` in full before designing anything —
they are the real, working, hand-written version of "sensor-specific + cross-sensor hazard
coverage," proven out most recently for the ISL29125 promotion (PR #83). Concretely, for `dev`'s
own `i2c1` (SCD30+SGP40+ISL29125):

- **Sensor-specific** (same-device): e.g.
  `test_same_device_isl29125_concurrent_read_and_write_never_interleave_on_the_wire` targets the
  ISL's own destructive-status-read hazard specifically — a config write landing between the
  status read and the data burst that follows it must not tear the sample. This is written by
  someone who read the datasheet and knows this chip's own failure mode; it is not (and probably
  should not become) a generic template.
- **Cross-sensor** (today, hand-written, pairwise, not "all at once"): e.g.
  `test_cross_device_isl29125_and_sgp40_interleave_and_both_stay_correct`,
  `test_sgp40_general_call_reset_does_not_disturb_a_concurrent_isl29125_read`. Each pairs two
  drivers by hand, and someone had to know these two share a bus to write it.
- `tests/test_digital_twin_bus_hazard_concurrency.py`'s own
  `test_dev_real_task_graph_survives_concurrent_bus_load_including_a_real_general_call` **is the
  closest existing thing to the "all sharers at once, driven from the real object graph" idea** —
  it already builds the real `dev` task graph and hammers it under load, checking every sensor still
  produces real data. It is not, however, derived from the TOML's bus-membership fact
  programmatically; it is a hand-written test that happens to know `dev`'s i2c1 grouping.
- `tests_hardware/bus_topology.py`'s own docstring says outright: "a hand-kept second copy of
  `devices/dev.toml`'s/`wozi.toml`'s own wiring facts, cross-checked by no tooling and imported by
  nothing today." This is exactly the kind of fact buildgen already computes once, correctly, for
  the real build (`buildgen/twin_wiring.py`'s `compute_twin_wiring()`, `buildgen/buildspec.py`'s
  `BUS_KIND_BY_DRIVER`) — a second, hand-maintained copy existing purely for hazard tests is a
  concrete sign this is worth automating.

## 2. What does not exist — confirmed, not assumed

Before scoping a design, this session already checked (2026-09-14) that none of the following
exists anywhere in this repo: `buildgen/` generating any *test* file (it generates firmware source
and website JSON only — `buildgen/codegen.py`, `buildgen/definitions.py` — never anything under
`tests/`/`tests_hardware/`); any comment-tag family (`@requires`/`@wiring`/`@value-wiring`/
`@limits`/`@web`/`@web-group`, `buildgen/tag_comments.py`'s `KNOWN_TAGS`) that declares a hazard
fact about a driver; and any mention of this idea anywhere in `BACKLOG.md`, `SPECIFICATION.md`,
`CLAUDE.md`, or `BUILD_CHAIN_PLAN.md`. This is genuinely new ground for this codebase, not a gap
in an existing, mostly-built system.

## 3. Real constraints this design has to fit, found by reading the actual test infrastructure

- **Two different test frameworks, not one.** The mock tier (`tests/test_bus_hazard_multi_device
  .py`) and the digital-twin tier (`tests/test_digital_twin_bus_hazard_concurrency.py`) run under
  the real MicroPython Unix-port interpreter via `tests/microtest.py` (CLAUDE.md/SPECIFICATION.md
  Part E.1's "why not pytest" — not optional, not swappable). The real-hardware tiers
  (`tests_hardware/flash/`, `tests_hardware/bench/`) run under real CPython pytest instead. Any
  generation mechanism has to produce (or drive) both, and they are not the same collection model —
  a design that only works for one of the two tiers doesn't satisfy the ask.
- **`buildgen`'s own driver-to-bus mapping already exists and is the correct source of truth** —
  don't reinvent it. `buildgen/buildspec.py`'s `BUS_KIND_BY_DRIVER`/`BUS_ATTACHED_DRIVERS` and
  `buildgen/twin_wiring.py`'s `compute_twin_wiring()` (`{"buses": {"i2cN": [{"driver", ...}, ...]}}`)
  already answer "which drivers share which bus, for this device" from a validated `DeviceModel`.
  Whatever assembles the per-bus worst-case test needs exactly this fact, computed once, the same
  way, for firmware generation and test generation alike — not a third hand-copy.
- **The existing per-tag-family bar applies if this becomes a new comment-tag family**
  (BUILD_CHAIN_PLAN.md, quoted in the ISL29125 requirements doc's own Section 0): full accept/
  reject grammar test coverage, fail-loud on a malformed/near-miss tag, no silent "no tag here."
  `buildgen/web_tag.py`'s recent `path`/`decimals` extension (PR #83) is the most recent worked
  example of adding to this family correctly.
- **Standing four-tier bus-hazard rule stays the bar, not a ceiling** (CLAUDE.md, explicit): mock,
  digital twin, real-hardware flash, real-hardware bench-under-API-load. Whatever this design
  produces has to still satisfy that rule for every existing and future driver — the goal is
  removing the *manual, easy-to-forget* half of satisfying it, not lowering the bar.
- **"Parallel" and "worst case" need real definitions before code gets written.** The project
  owner's own phrasing — concurrency, parallel sessions, timeouts, addresses, broadcasts, "and many
  more" — is a catalog to build, not a spec already written down anywhere. Read the existing hazard
  tests (Section 1) as the seed of that catalog (same-device read/write interleaving, cross-device
  interleaving, general-call/broadcast effects, address-touch sweeps, reserved-address collision
  checks) and decide, with the project owner if genuinely ambiguous, what else belongs in it (a
  bus-wide timeout/NAK storm? a mid-transaction disconnect? something UART-specific for
  `uart_link`, which is point-to-point rather than multi-drop and already sits outside the
  I2C-address-based hazard model the existing tests assume?).

## 4. Open design questions (step-session workflow's clarifying-question round — a first pass)

1. **What does a driver *declare* about its own hazard surface, and how?** A new comment-tag
   family (`# @hazard ...`, matching `@requires`'s own shape) naming things like "has a destructive
   status register at 0x08," "has a finite on-chip NVM write budget," "is general-call sensitive"?
   Or does the *specific* hazard test stay fully hand-written (as it is today, and probably should
   stay — Section 0 above already says the specific half "probably mostly matches today's status"),
   with only the *cross-sensor, generic* half becoming generated? Lean toward the latter unless a
   real need for the former turns up — the specific tests are datasheet-derived judgment calls
   (CLAUDE.md's own "verify against real hardware/datasheet" ethos), which is a much worse fit for
   a declarative tag than "this bus exists and these drivers are on it."
2. **What does "generated" actually mean — a written `.py` file, or a runtime-parametrized
   collection?** Firmware/website generation always produces a real file
   (`build/generated_src/...`, `html/definitions/*.json`) that gets committed nowhere and is
   regenerated every build. Tests could go the same way (buildgen writes
   `tests/generated/test_<device>_bus_hazard.py` at test-collection time, gitignored, mirroring
   `build/generated_src/`) or the generic cross-sensor scenarios could live as data/callables in
   `buildgen` itself, with a thin, hand-written test file per tier that reads the TOML-derived bus
   membership and pytest-parametrizes/microtest-loops over it at collection time (no generated
   source file at all, closer to how `tests_scripts/buildgen_fixtures/novel_combo.toml`-driven
   tests already work). The two-test-framework constraint (Section 3) may make these two answers
   look different for the mock/twin tier vs. the hardware tier — that's fine, they don't have to be
   architecturally identical, only both derived from the same TOML fact.
3. **Where does "run every real occupant of this bus at once, not pairwise" actually execute?**
   For the mock tier this is straightforward (spin up N fake driver instances against one shared
   fake bus, `asyncio.gather()` a scenario per instance, matching the existing hand-written pattern
   almost exactly). For real hardware, "all at once" already has a working precedent worth
   studying first: `tests_hardware/bench/test_bus_concurrency_under_api_load.py` drives the whole
   system through its real REST API rather than device-script-level bus calls — is a generated
   worst-case scenario built on that same approach, or on `board.run_isolated()`-style device
   scripts (Section 3's UART point-to-point exception may force a different shape there too)?
4. **Scope the first landing to one real bus, not all six devices at once.** `dev`'s `i2c1`
   (SCD30+SGP40+ISL29125, three real drivers actually sharing one bus today) is the obvious proving
   ground — it already has hand-written coverage to compare a generated version against for parity,
   and it's the only bus in any real device TOML with three-way sharing today. Land mock +
   digital-twin tiers there first (both run in CI on every push, no real-hardware go-ahead needed);
   treat extending to the real-hardware tiers, and to every other device's own bus groupings, as
   follow-on work once the design is actually proven, not a single all-at-once retrofit.
5. **Does this replace the existing hand-written cross-sensor tests, or run alongside them until
   proven equivalent?** Given how recently (PR #83) and carefully those were written, deleting them
   the same session that introduces their generated replacement is real risk — consider generating
   the new coverage first, diffing its actual failure-catching power against the hand-written
   version (does it, e.g., still catch a regression that broke the destructive-status-read
   hazard?), and only retiring the hand-written cross-sensor tests once that's demonstrated — this
   mirrors CLAUDE.md's own "flag, don't silently change" instinct applied to test infrastructure
   itself.

## 5. Standing rules carried over (do not re-derive — same set the ISL29125 migration doc named)

- **Step-session workflow** (CLAUDE.md): scope → ask blocking/architecturally-significant questions
  early (Section 4 above is the first pass, not the final word) → TDD → implement → maximize
  coverage → **stop and report before merging or expanding scope.** Given how open-ended Section 4
  is, expect at least one real round of this with the project owner before implementation starts in
  earnest — this file existing is not permission to build the first design that comes to mind.
- **Memory-safety discipline** (CLAUDE.md "Hard rules", SPECIFICATION.md Part I.4): any new
  digital-twin-tier test this work adds must pass under `gc.threshold(-1)` with zero `MemoryError`s
  before `gc.threshold(32768)` is ever credited, same as every other test in this repo now.
- **"Driver/DUT process separation"** (PR #82): any new digital-twin-driving test/script drives the
  twin's real HTTP server from host-side code, never shares its process/heap.
- **Real-hardware go-ahead gate** (CLAUDE.md): don't run anything against real hardware without the
  project owner's go-ahead given directly in *this* session's own conversation. Given Section 4
  item 4's own scoping suggestion (mock + twin first), this should rarely come up before the
  real-hardware follow-on phase.
- **PR workflow**: base this branch's PR on `claude/automated-build-chain-nuzumw`, subscribe to its
  CI/review activity immediately, drive it to green per CLAUDE.md's PR babysitting rules.
- **This file**: update it as the design settles and phases complete; delete it once the work lands
  and is reconciled with its own PR, same as `UART_PROMOTION_REQUIREMENTS.md`/
  `ISL29125_BUILDGEN_MIGRATION_REQUIREMENTS.md` were.

## 6. A reasonable first landing (not a mandate — revisit after Section 4's questions settle)

1. Read Section 1's four files in full, and `buildgen/twin_wiring.py`/`buildgen/buildspec.py` for
   the bus-membership fact already computed.
2. Resolve Section 4's open questions — at minimum items 1, 2, and 4 — either from your own
   research and judgment (the step-session workflow permits this where the answer is genuinely
   clear) or by raising them to the project owner where it isn't.
3. Build the generic cross-sensor hazard catalog as reusable scenario building blocks (not yet
   wired to generation) and prove them, by hand, against `dev`'s real `i2c1` three-way grouping —
   this is the "does the catalog actually catch real bugs" proof before investing in the generation
   machinery around it.
4. Wire TOML-driven assembly for the mock and digital-twin tiers on that one bus, diff its
   catching-power against the existing hand-written tests (Section 4 item 5), and report back
   before touching the real-hardware tiers or any other device.
