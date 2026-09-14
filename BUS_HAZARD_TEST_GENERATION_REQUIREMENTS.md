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

## 7. Phase 1 status — design decisions actually made, and what landed

Section 4's questions resolved by research/judgment (no genuinely blocking ambiguity turned up —
none needed raising to the project owner):

1. **Driver declaration**: resolved to the doc's own leaned-toward answer. No new comment-tag
   family. The specific/datasheet-derived hazard tests stay 100% hand-written
   (`test_bus_hazard_multi_device.py` untouched in kind, only refactored for shared helpers — see
   below). Only the generic, cross-sensor half is generated.
2. **What "generated" means**: for the mock and digital-twin tiers (both run under the real
   MicroPython Unix-port interpreter via `tests/microtest.py`), "generated" means *reading the
   already-generated* `build/generated_src/sensortask_<device>_wiring_plan.json`
   (`buildgen.twin_wiring.compute_twin_wiring()`'s own output, produced by
   `scripts/_generate_sensortask_modules.py` before every test run — confirmed already required by
   the existing `machine.configure_i2c_wiring("dev")` twin test) at test-collection/call time via
   plain `json.load()`. **Not** a written `.py` file: MicroPython's Unix-port `tomllib`-free,
   `buildgen`-free test process can't run `buildgen` itself (it's genuinely CPython-only host
   tooling — `ast`/`tomllib` imports, no MicroPython stub for either), so the CPython-side JSON
   artifact `buildgen` already produces for the twin's own wiring is the one bridge across that
   process boundary — reused, not re-derived a third time. No new codegen work was needed in
   `buildgen/` itself.
3. **Where "all occupants at once" executes**: mock tier — one shared fake `I2C` bus, one instance
   per real occupant (from a small per-driver adapter catalog, `tests/_bus_hazard_catalog.py`),
   `asyncio.gather()` over all of them (genuinely N-way, not pairwise — confirmed new: no existing
   test drives SCD30+SGP40+ISL29125 all three at once, only pairs). Digital-twin tier — the real
   object graph already does this mechanically once booted; what was missing was the TOML-driven
   half of *which* sensors' `get_data()` must be checked, now read from the same wiring-plan JSON
   instead of a hardcoded sgp40/bmp3xx/scd30/isl29125 list. Real-hardware tiers: **out of scope this
   phase**, per item 4 below — not resolved, not attempted.
4. **Scope**: `dev`'s real `i2c1` (SCD30+SGP40+ISL29125) only, mock + digital-twin tiers only, as
   the doc itself suggested. Confirmed via the boundary in this file's own governing instructions:
   stop before any other device or the real-hardware tiers.
5. **Replace vs. run-alongside**: run alongside. Nothing hand-written was deleted this phase.
   `test_bus_hazard_multi_device.py`'s existing pairwise tests are untouched in behavior — only its
   five shared byte/frame helpers (`make_i2c`, `fake`, `_crc8`/`_sgp_word`/`_scd_register_frame`/
   `_scd_data_frame`, `seed_isl_ready`) moved into the new `tests/_bus_hazard_catalog.py` (imported
   back under their original names) so the new generated coverage builds byte-identical frames
   instead of a second hand-copy — a pure refactor, not a coverage change. The digital-twin tier's
   TOML-driven check was folded into the existing shared `_run_real_task_graph_and_assert_healthy()`
   helper as one more pass over the *same already-booted* graph, rather than a new test function
   with its own second boot — see the real memory-pressure finding below for why. Both hand-written
   cross-sensor tests (Section 1) and the new mock-tier generated file stay in the suite.

**A real bug the new mock-tier catalog caught immediately** (the "does the catalog actually catch
real bugs" proof, though not the kind expected going in): the very first N-way run of `dev`'s real
`i2c1` group — SCD30 and SGP40 *concurrently* active, which no test anywhere had ever done before,
mock or twin — corrupted both drivers' reads. Root cause: `tests/machine.py`'s `FakeI2C.read_queue`
is one shared, address-agnostic FIFO (`readfrom_into()` "has no register to key off", per its own
comment) — fine for every existing test, which never has *two* raw-word-protocol (register-less)
devices reading concurrently on one shared fake bus, but wrong the moment two are: each device's
`readfrom_into()` call popped whichever reply was next regardless of who actually asked, so SCD30
and SGP40 read back fragments of *each other's* queued frames. Fixed with an additive,
backward-compatible `read_queue_by_address: dict[int, list[bytes]]` on `FakeI2C`, checked before the
existing shared queue (empty by default, so every existing caller — which only ever populates the
shared one — is provably unaffected: the full `scripts/test.sh` suite was re-run afterward and
every other file that touches `tests/machine.py`'s I2C fake still passes). `tests/
_bus_hazard_catalog.py`'s `_seed_scd30`/`_seed_sgp40` seed by address now; `I2CHazardAdapter.seed`'s
own signature grew a `address` parameter to support it. This is exactly the kind of gap that only
surfaces once "all real occupants at once" is actually exercised generically instead of by hand —
the whole reason this design work exists.

A second, related finding while proving this against the real interpreter: adding a *second* full
`sensortask_dev.build_system()` boot to `tests/test_digital_twin_bus_hazard_concurrency.py` (this
file already runs 10 other heavy full-graph-boot tests sharing one Unix-port process/heap, per
`scripts/test.sh`'s own `-X heapsize=8M`) pushed it into real, measured intermittent
`MemoryError`s — roughly 1 run in 3 across repeated direct runs, a real violation of CLAUDE.md's
"zero `MemoryError`s, not just usually" memory-safety discipline. Fixed by not adding a second boot
at all: the TOML-driven check reuses the *same* already-booted graph the existing hand-written test
already builds, as one more (free) pass over data already in hand — 5/5 clean repeated runs
afterward, same as the pre-existing 8M-heap bar. Catching-power itself was confirmed by hand
(temporarily reverting `ISL29125_I2C`'s destructive-status-read protection made the new mock-tier
`test_dev_i2c1_all_real_occupants_concurrent_reads_stay_correct_and_genuinely_interleave` fail
exactly as expected; the revert was then undone) — not committed as a test, since deliberately
breaking production code as a checked-in regression test isn't this repo's pattern.

What actually landed:

- `tests/_bus_hazard_catalog.py` (new): the per-I2C-driver `I2CHazardAdapter` catalog (scd30/sgp40/
  isl29125 — the three real occupants of `dev`'s `i2c1`; bmp3xx isn't in it yet since no real device
  TOML ever shares a bus with it) plus four generic, driver-agnostic scenario builders:
  all-occupants-concurrent-reads, a-write-vs-concurrent-sibling-reads, general-call-vs-concurrent-
  siblings, and the per-occupant address sweep. Plain classes, not `@dataclass` — `dataclasses` has
  no stub in the MicroPython-target typeshed this file type-checks under and nothing in
  `src/`/`tests/`/`digital_twin/` uses it anywhere else (confirmed by grep before adding a second,
  incompatible usage — `buildgen/` is genuinely CPython-only and doesn't share this file's runtime).
- `tests/test_bus_hazard_generated.py` (new): the mock-tier assembly, deliberately hardcoded to
  `dev`/`i2c1` (not a loop over every device/bus — see the file's own comment on why, and the
  boundary this phase stops at).
- `tests/machine.py`: additive `read_queue_by_address` fix (above) — required for the mock tier's
  own SCD30+SGP40 concurrent case to work at all, not optional polish.
- `tests/test_digital_twin_bus_hazard_concurrency.py` (extended): the existing shared
  `_run_real_task_graph_and_assert_healthy()` helper (used by both the wozi and dev hand-written
  tests) gained one more TOML-driven pass at the end, reading the real generated wiring-plan JSON's
  own `i2c1` membership generically instead of a hardcoded sgp40/bmp3xx/scd30/isl29125 list — no new
  test function, no second boot.
- `tests/test_bus_hazard_multi_device.py`: refactored (imports only) to reuse the moved helpers;
  zero behavior change.
- `pyproject.toml`: one new `[tool.ruff.lint.per-file-ignores]` entry for
  `tests/_bus_hazard_catalog.py` (`ANN401`, same "driver-agnostic fan-in seam" category already
  used for `src/asy_notification_service.py`/`tests/test_setter_microdot_integration.py`).
- `.gitignore`: added the untracked `.mypy_cache/` (found while running `scripts/typecheck.sh` in
  this session; unrelated to the bus-hazard work itself but a genuine pre-existing gap).

Verification run: `scripts/lint.sh`/`ruff` clean on every touched/added file; `scripts/typecheck.sh`
(main pass + `digital_twin/typecheck.ini` pass both clean; `host_typecheck.ini`'s pre-existing
201-error `pytest`/`pyserial`-stub gap in this sandbox is unrelated to this branch — confirmed
identical on the pre-change tree via `git stash`); the full MicroPython Unix-port suite built from
scratch in this session and re-run to green, plus 5 repeated direct runs each of the two new/changed
files with zero failures — see the PR description for the actual run's result.

## 8. "Same test bar as `src/`/buildgen" compliance check (project owner, 2026-09-14)

Asked directly whether this session's own new code, and `buildgen` in general, meet the project
owner's standing requirement (quoted directly): *"Ensure that the buildgen scripts have the same,
complete set of tests as the actual source code - full functional tests, all error paths, coverage
and regression. The only difference with the error and resilience paths being that the build always
aborts on errors and reports them such that a user can easily see what to do as a resolution."* This
is documented in this repo as BUILD_CHAIN_PLAN.md's own "Tested to the same bar as `src/` code"
bullet (correct-path functioning, full error-handling-path coverage, code coverage — "every abort
condition gets its own test, driven by deliberately malformed fixture definition files").

**This session's own new code**: none of it is `buildgen/` code — phase 1's design decision (Section
7 item 2) was to reuse `buildgen`'s already-generated wiring-plan JSON rather than add new codegen,
so this policy's literal scope (`buildgen/`) was never touched. Checked anyway, honestly, against the
same spirit for the `tests/` code actually added: the two fail-loud `KeyError` paths in `tests/
_bus_hazard_catalog.py` (`build_bus_occupants()` and `scenario_each_occupant_never_touches_an_
unexpected_address()` both raising for a real bus occupant with no catalog adapter yet) had **no
test** covering them until this check prompted adding one — fixed: `tests/
test_bus_hazard_generated.py` now has `test_build_bus_occupants_fails_loud_for_a_driver_with_no_
catalog_adapter` and `test_address_sweep_scenario_fails_loud_for_a_driver_with_no_catalog_adapter`.

**`buildgen` in general**: the policy is real, written down, and substantially followed — a mature
`tests_scripts/` pytest suite (one file per module in most cases: `test_buildgen_validate.py`,
`test_buildgen_tag_comments.py`/`test_buildgen_requires_tag.py` explicitly called out in
BUILD_CHAIN_PLAN.md as "the reference implementation of this bar"), with real `pytest.raises(
BuildError, ...)` coverage for abort conditions including otherwise-hard-to-reach ones (e.g.
`test_buildgen_validate.py`'s `test_driver_resolvable_but_missing_buildspec_entry_reports_the_real_
cause` builds a synthetic driver file on disk specifically to reach a branch no real device TOML
can). **This was a targeted spot-check prompted by the question, not an exhaustive audit of every
`raise` site in `buildgen/` against test coverage** — that would be separate, larger work. The
spot-check found two concrete gaps, both now fixed in this session:
1. `buildgen/twin_wiring.py`'s `compute_twin_wiring()` has one defensive `raise ValueError(...)`
   (a bus-attached driver with no address rule) that was provably unreachable via any real device
   TOML and had zero test coverage — confirmed by grep (`pytest.raises` had zero hits in `tests_
   scripts/test_buildgen_twin_wiring.py`). Fixed: `test_bus_attached_driver_with_no_address_rule_
   fails_loud_not_silently_miswired` now reaches it via `monkeypatch`, the same synthetic-fixture
   technique the `buildspec`-entry test above already established for this exact class of gap. This
   is also the one function phase 1's own new code depends on most directly.
2. `digital_twin/machine.py`'s own analogous fallback in `_build_i2c_chip()` (`raise ValueError(f"
   digital twin has no I2C chip fake for driver {driver!r}...")`) has the same shape of gap — found,
   **not fixed this session** (lower priority: it's `digital_twin/`, not `buildgen/` itself, and
   further from phase 1's own work) — left as a named follow-on, not silently dropped.

No claim is made here that every `buildgen/`/`digital_twin/` abort condition has a matching test —
only that this specific check found these two gaps, fixed the one most relevant to this branch's own
work, and named the other rather than leaving it undiscovered. A full audit (enumerating every
`raise BuildError`/`raise ValueError` across all ~20 `buildgen/*.py` modules against `tests_scripts/`
coverage) is separate work this session did not do.

**Stopping here per this file's own governing boundary** (Section 6 item 4 / the session's own
instructions): not touching the real-hardware tiers, not extending to any other device/bus, not
retiring the hand-written cross-sensor tests. Follow-on work, if the project owner wants it
continued: generalize `test_bus_hazard_generated.py`'s hardcoded `dev`/`i2c1` into a loop over every
real device/bus pairing with 2+ occupants (the file's own comment marks exactly where); add a
`bmp3xx` adapter once some device TOML actually shares a bus with it; design the real-hardware
tiers' own version of "all occupants at once" (Section 4 item 3's still-open half).
