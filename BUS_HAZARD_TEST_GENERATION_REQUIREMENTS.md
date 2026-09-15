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

## 9. The full compliance audit, on request (project owner, 2026-09-14, follow-up to Section 8)

Section 8's own two-gap spot-check was explicitly *not* an exhaustive audit. Asked directly to find
and fix more rather than stop at a spot-check, this session did the full module-by-module pass
Section 8 named as separate work: every `raise BuildError(...)`/`raise ValueError(...)`/etc. site in
every `buildgen/*.py` module, cross-referenced against actual `tests_scripts/` test *content* (never
a raw grep-count of `pytest.raises` occurrences — confirmed early on to be badly misleading, since
many test files share one parametrized `pytest.raises()` helper across dozens of `@pytest.mark.
parametrize` cases, undercounting real coverage 5-10x; several early "gap" candidates turned out to
already be covered once the actual test body was read, not just grepped).

**Confirmed real gaps found and fixed** (all in `tests_scripts/`, zero `buildgen/`/`src/` behavior
changes):

- `buildgen/web_tag.py`: `@web-group`'s own "must be at module level" rejection had no test at all,
  unlike `@web`'s own `test_parse_web_tags_rejects_locations_inside_a_body` — added the `@web-group`
  sibling.
- `buildgen/definitions.py` (six real, TOML-reachable gaps + three `"internal:"` invariants): a
  `@web` tag with no matching `ConfigSchema` constant and no explicit `kind=` override; `kind=enum`
  declared but the schema has no discrete choice set; a tag's `special:` entries naming a value the
  schema's own choice set doesn't contain; a schema's scalar sentinel `special` value with no
  matching tag documentation; a mandatory `@web-group` (system/networking/notification settings)
  never declared in any scanned file; a mandatory group declared but with no `@web` field tags
  referencing it. All six reached via the established "mutate a copy of a real driver file"
  technique (`_copy_driver_without`/`_copy_driver_replacing`, extended with one small generic
  synthetic-notification-instance case). Plus the three `"internal:"` `resolved_name`/`driver_info`
  invariant guards, driven directly against a hand-built `InstanceSpec`.
- `buildgen/model.py`: `load_device()`'s "TOML parsed but not to a table at the top level" guard —
  provably unreachable via real `tomllib.load()` behavior (TOML's own grammar guarantees a dict at
  the document root), closed via `monkeypatch.setattr(tomllib, "load", ...)`.
- `buildgen/codegen.py` (three `"internal:"` invariants, none previously covered — no dedicated test
  file for this module exists): `_build_args_notification()`'s missing `signal_sink` wiring field;
  `_emit_header_and_imports()`'s unresolved `driver_info`; `_emit_build_system()`'s construction-order
  entry that is neither a known bare node nor an instance key. All three driven directly by mutating
  an otherwise-valid, already-`build_model()`-validated model and calling the containing function
  (`_build_args_notification`, `generate_module_source`) directly — the same "mutate a validated
  model, call the internal function" technique `test_codegen_has_no_build_recipe_for_an_unknown_
  driver` (already in the suite) established.
- `buildgen/validate.py` — by far the largest concentration, all in the shared i2c/spi/uart bus-table
  and GPIO-role-checking code: the **uart-kind branches never got the same dedicated test their i2c/
  spi siblings did** (missing required `tx_pin`/`rx_pin`; `frequency` declared on a uart bus;
  `rxbuf`/`txbuf`/`poll_wait_ms`/`poll_idle_ms` wrong type; unrecognized bus field; a pin with no
  UART function at all; a real UART pin belonging to the *other* uart index; transposed tx/rx pins),
  plus `uart_link`'s own `role` field holding a value that is neither `"initiator"` nor
  `"responder"` (missing entirely was already tested; present-but-wrong was not). Five more
  `"internal:"` invariants (`BUS_KIND_BY_DRIVER` missing an entry for a `BUS_ATTACHED_DRIVERS`
  member; `resolved_name`/`driver_info` unresolved at three different check sites; a non-table
  wiring value reaching `_check_default_value_selection()`) driven the same "hand-built
  `InstanceSpec`, call the private check function directly" way this file's own pre-existing
  `test_instance_name_collision_via_distinct_drivers_same_resolved_name` and
  `test_device_wiring_required_field_missing_is_rejected` already do — not a new technique.
- `digital_twin/machine.py`: the `_build_i2c_chip()` "no chip fake for this driver" fallback named
  in Section 8 as found-but-not-fixed — fixed now, driven directly (no real device TOML can name a
  driver `machine.py` doesn't know, since it and `compute_twin_wiring()` are kept in sync by hand for
  the same fixed driver set today).

**Confirmed clean, no fixes needed** (read in full, not just grep-counted):
`buildgen/driver_registry.py`, `buildgen/tag_comments.py`, `buildgen/requires_tag.py`,
`buildgen/graph.py`, `buildgen/defaults.py`, `buildgen/schema_ast.py` (its three raises are
*internal control flow* for an intentional "best-effort, silently skip anything unparseable" design,
already correctly tested via behavioral silent-skip assertions, not `pytest.raises` — reading the
module's own docstring before concluding "zero raises tested = gap" mattered here),
`buildgen/value_wiring.py`, `buildgen/wiring.py`, `buildgen/limits.py`.

**A real mypy finding from this round**: two of the new tests (the `model.py` and `validate.py`
`"internal:"` fixes) initially failed `host_typecheck.ini`'s dedicated pass — `no_implicit_reexport`,
which the main `[tool.mypy]` pass relaxes for `tests/`'s own mocking convention but `tests_scripts/`
never does — by accessing `some_module.NAME` where `NAME` was only *imported* into `some_module`,
not defined there (`buildgen.model.tomllib`, `buildgen.validate.BUS_KIND_BY_DRIVER`). Fixed by
importing the name directly from its origin module instead (`import tomllib` at the test's own top
level; `from buildgen.buildspec import BUS_KIND_BY_DRIVER`) — both bind the identical shared object,
so mutating either reference is still what the code under test reads.

**Verification**: full `tests_scripts/` pytest suite (1100 passed, 7 skipped, up from 1067 before
this round), all three `scripts/typecheck.sh` passes clean (main + `digital_twin/typecheck.ini` +
`host_typecheck.ini`, modulo the pre-existing `pytest`/`pyserial`-stub sandbox gap unrelated to this
branch), `ruff` clean.

**Still not claimed**: this is now a genuinely thorough, function-by-function audit — not a
statistical spot-check — but it is still one session's own reading, not a mechanically-verified
100%-coverage guarantee (no coverage-gating tool was run against `buildgen/` specifically; `scripts/
test.sh --coverage` measures `src/`, never `buildgen/`). If a coverage tool is ever pointed at
`buildgen/` and finds a line this audit's manual read missed, that finding stands on its own merits,
not as a contradiction of this section.

## 10. Phase 2 — timing sweep, all-buses iteration, BMP3xx, hand-written-test porting, real hardware (project owner, 2026-09-15)

Follow-on direction, in the project owner's own words: systematically vary WHEN concurrency fires to
find races (mock/twin unrestricted; real hardware's SCD30 gets an opt-in, one-write-only exception);
iterate every real I2C bus, not just dev/i2c1; add the BMP3xx catalog adapter now (not deferred until
some device shares a bus with it); fully port the hand-written pairwise tests
(`test_bus_hazard_multi_device.py`) into the generation scheme, removing them only once 100% ported;
and the whole scheme must be runnable at every tier, real hardware included, with the same SCD30
exception applying there.

**Landed, verified (mock + twin tiers — full `tests/test_bus_hazard_generated.py` +
`tests/test_digital_twin_bus_hazard_concurrency.py` + `tests/test_bus_hazard_multi_device.py` runs,
`ruff`, all three `scripts/typecheck.sh` passes, all clean):**

- **BMP3xx adapter added to `I2C_HAZARD_CATALOG`** — `tests/_bus_hazard_catalog.py`'s `seed_bmp_ready`/
  calibration-fixture helpers absorbed from `test_bus_hazard_multi_device.py`, plus a lazy-`setup()`
  wrinkle unique to this driver (its correctness depends on real calibration registers computed by an
  *async* `setup()`, unlike the other three adapters' sync-only `construct()` — primed on the
  occupant's own first `read_once()` instead of widening the adapter API for one driver).
- **`tests/test_bus_hazard_generated.py` now iterates every real device × every real I2C bus**,
  discovered from `build/generated_src/sensortask_*_wiring_plan.json` (`os.listdir()` + filename
  filtering — MicroPython's Unix-port test build has no `glob` module), not a hand-kept device list.
  34 tests generated across all 6 devices' 10 real I2C buses today (up from 5 hardcoded to
  `dev`/`i2c1`): every bus gets its own address/reserved-range sweep and same-occupant
  write-vs-own-read check; a bus with 2+ occupants additionally gets the membership guard,
  all-occupants-concurrent, cross-occupant-write and general-call scenarios. A 7th device or a
  re-wired bus needs zero edits here.
- **The digital-twin tier's own generic health-check pass now loops over every bus in the wiring
  plan** (`plan["buses"].items()`), not a hardcoded `"i2c1"` key — harmless, deliberate overlap with
  the pre-existing hardcoded checks on dev/wozi's own i2c0 buses (project's own "run alongside, don't
  replace" policy for layered coverage).
- **Systematic timing-offset sweep**, unrestricted on mock/twin: `scenario_a_write_does_not_disturb_
  concurrent_sibling_reads`, `scenario_general_call_does_not_disturb_concurrent_siblings`, and a new
  `scenario_same_occupant_own_write_does_not_disturb_own_concurrent_read` (see below) each rebuild
  fresh bus/occupant state and re-run once per offset across `range(iterations)`, instead of firing
  after one fixed `asyncio.sleep(0)`. Fresh state per offset is deliberate, not incidental — a fake
  bus's `.log`/read queues are NOT naturally reset between trials the way a real bus's own protocol
  state is, so reusing state across offsets could let one trial's stale log entry silently mask or
  fake a later trial's own result (e.g. the general-call scenario's own "did it actually fire" check).
- **New generic scenario closing a real hand-written-test-porting gap**:
  `scenario_same_occupant_own_write_does_not_disturb_own_concurrent_read` — the SAME-device hazard
  (one occupant's own write vs its own concurrent read loop), as opposed to the cross-occupant one
  above. Generated unconditionally for every bus (even single-occupant ones), since it needs no
  sibling to mean something — this is what gives arzi/klkizi/grkizi/schlafzi's lone-SCD30/lone-SGP40
  buses genuine concurrency coverage for the first time, not just an address sweep.
- **The reserved-I2C-address-range check is now generic too**, folded into
  `scenario_each_occupant_never_touches_an_unexpected_address` (checked against every real occupant's
  own TOML-declared address, not a hand-kept four-entry table).

**Landed, NOT yet verified against real hardware (no go-ahead this session — CLAUDE.md's own
standing gate; written, `ruff`/`mypy`-clean, structurally consistent with every proven-on-hardware
script in `tests_hardware/`, but not run):**

- Two new flash-tier tests closing a real coverage gap the mock-tier audit surfaced: no prior
  real-hardware test proved a config WRITE from one dev/i2c1 occupant landing concurrently with its
  SIBLINGS' own reads (only same-device write-vs-own-read and the SGP40-general-call-vs-SCD30 case
  existed). `test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads` (ISL29125 as
  writer — volatile register, unrestricted, part of the routine group) and
  `test_scd30_config_write_does_not_disturb_concurrent_sibling_reads` (SCD30 as writer — one
  additional real NVM write, gated behind the new `@pytest.mark.scd30_write` /
  `--allow-scd30-writes` opt-in, same precedent as `--allow-flash-cycle`, off by default, never part
  of the routine group's own one-write budget). See `tests_hardware/README.md`'s "Seventh pass" for
  the full account and the honesty note about unverified status.
- Real hardware has no literal equivalent of the mock tier's `asyncio.sleep(0)`-count offset sweep —
  an artificial yield count means nothing against a real preemptible interpreter and real bus timing.
  The two new device scripts substitute real hardware's own natural equivalent instead: many repeated
  write cycles (`WRITE_CYCLES=8`) over a real multi-second window, so genuine uncontrolled
  scheduling/serial jitter puts each write at a different real relative offset — the honest,
  tier-appropriate reading of "systematically vary when it fires," not a literal port of the mock
  tier's mechanism.

**Explicitly NOT done this round — disclosed gaps, not silent ones:**

- **`test_bus_hazard_multi_device.py` (the hand-written pairwise suite) has NOT been deleted.** Most
  of its I2C scenarios now have a generated equivalent with parity or better (often stronger — the
  timing sweep, and the all-occupants/3-way generalization on dev/i2c1), but three do not yet:
  (1) its byte-exact wire-log command-sequence parse (`_parse_scd30_log`) proves non-interleaving at
  the literal byte level, while the generic same-occupant scenario proves it via `read_once()`'s own
  value-correctness assertion instead — the same bar every other generic scenario here already uses,
  but not literally identical proof; (2) `test_general_call_absent_sibling_bmp3xx_alone_on_the_bus_
  survives_a_broadcast_too` — a ROGUE general call from no real occupant's own driver, fired against
  a lone occupant with no broadcaster on its bus at all — the generic scheme only ever fires a general
  call that a real catalog occupant's own adapter issues, so a bus with no broadcasting occupant (e.g.
  dev's own bmp3xx-alone i2c0) gets no general-call coverage generically at all; (3) FRAM (SPI) same-
  device concurrency — entirely out of scope for `I2C_HAZARD_CATALOG`, and out of scope for this
  round's own "iterate every I2C bus" direction, which named I2C specifically. Per the project
  owner's own explicit conditional, the hand-written file is retired only once every one of its tests
  has a demonstrated generated counterpart — not before, and not thinned in place in the meantime.
- The rogue-general-call gap above (item 2) would need the per-bus occupant-factory to also expose
  the raw shared `I2C` wrapper (today's factory returns only `(fake_bus, occupants)`), a small but
  real interface widening not done this round to keep the already-verified scenario functions'
  signatures stable while everything else changed underneath them.

**Verification**: `tests/test_bus_hazard_generated.py` (34/34), `tests/test_digital_twin_bus_hazard_
concurrency.py` (10/10), `tests/test_bus_hazard_multi_device.py` (13/13, unchanged, confirming no
regression) all run clean under the real Unix-port interpreter (`-X heapsize=8M`); `ruff check`
clean; all three `scripts/typecheck.sh` passes clean. The two new real-hardware tests/scripts are
new code with no execution evidence yet — see their own "NOT yet verified" callout above.

## 11. Full mock/twin-to-real-hardware scenario parity, and flash-tier/bench-tier parity (project owner, 2026-09-15, follow-up to Section 10)

Direct follow-up: does every generic mock/twin scenario type have a real-hardware equivalent, and
does everything added to the flash tier also exist at the bench tier (flash-tier bus-hazard coverage
is always meant as a subset of bench-tier coverage)? Checked systematically against dev's own real
topology (i2c0: BMP3xx alone; i2c1: SCD30+SGP40+ISL29125) — full account in
`tests_hardware/README.md`'s own "Eighth pass" section; summary here:

- **Timing-offset sweep, made explicit on real hardware**: `bus_concurrency_isl29125_write_vs_
  siblings.py` (unrestricted writer) now cycles through a deliberately varied, explicit set of
  pre-write delays (`5, 15, 40, 80, 120` ms, each used twice) instead of a fixed cadence — a designed
  spread of relative timings, not reliance on natural jitter alone.
  `bus_concurrency_scd30_write_vs_siblings.py` still fires at exactly one fixed offset — the one-write
  budget makes a real sweep structurally impossible there, now stated explicitly in its own docstring
  rather than left implicit.
- **Two real gaps closed**: `sgp40_general_call_reset_hazard.py` now reads ISL29125 concurrently too
  (it only checked SCD30 before, even though ISL29125 is also a real non-broadcasting sibling on
  dev's i2c1) — the flash-tier test wrapping it was renamed to `test_sgp40_general_call_reset_does_
  not_corrupt_concurrent_scd30_and_isl29125_transactions` to say so. `bus_topology_autodetect_and_
  hazard_sweep.py`'s own `KNOWN_ADDRESSES` table had silently drifted out of sync with
  `tests_hardware/bus_topology.py`'s copy (its own docstring's stated invariant) — missing ISL29125
  (`0x44`) entirely; fixed, and the self-hazard branch now also handles it.
- **Everything else already had a real-hardware equivalent** once checked systematically:
  same-occupant write-vs-own-read (per-driver same-device scripts), all-occupants-concurrent-reads
  (`isl29125_cross_device_concurrency.py` already runs all three of i2c1's real occupants at once),
  and the rogue-general-call-against-a-lone-occupant case (the topology script's own self-hazard
  branch, which — unlike the mock tier's own generic scheme (Section 10's own item 2) — already
  covered this before this pass, since it isn't tied to any real occupant's own adapter issuing the
  broadcast).
- **Flash-tier → bench-tier parity**: added `test_isl29125_config_write_does_not_disturb_concurrent_
  sibling_reads_under_api_load` (`tests_hardware/bench/test_bus_concurrency_under_api_load.py`) —
  the same hazard as the flash-tier ISL29125 test, driven through real `PUT`/`GET /sensors` instead
  of the bare driver, with the board's original `Resolution` restored afterward.
- **SCD30 has no bench-tier counterpart, and this is structural, not a scope gap**:
  `asy_scd30_driver.py` registers zero `_push_callbacks`, so there is no `PUT /sensors` field that
  could ever reach SCD30's own write at all — the flash tier's own opt-in test is the only real-
  hardware coverage this hazard can ever have, by construction of `src/` itself. Recorded explicitly
  rather than left as a silent asymmetry between the two tiers.

**Verification**: `ruff check` clean (after extracting a `_failures()` helper in
`sgp40_general_call_reset_hazard.py` to stay under the C901 complexity gate once the ISL29125 branch
was added), all three `scripts/typecheck.sh` passes clean, `scripts/lint.sh` (shellcheck/actionlint/
zizmor included) clean. All real-hardware device-script/bench changes in this section carry the same
honesty caveat as Section 10's: written and typed with no real-hardware go-ahead this session, not
yet run against silicon.

## 12. Anchoring real-hardware parity as a general rule, then auditing against it (project owner, 2026-09-15)

Two more follow-ups in the same thread: (1) the "every mock/twin test needs a real-hardware
equivalent" expectation should be anchored in `SPECIFICATION.md` as a standing rule, not left as
narrative in this file or `tests_hardware/README.md`; (2) once anchored, are the bus-hazard tests
actually adhering to it?

**(1) Anchored**: `SPECIFICATION.md` Part E.6.6 (new) states the general rule — every mock/twin test
exercising real-hardware-facing behavior needs a real-hardware equivalent wherever technically
possible — scoped against three pre-existing exceptions so it doesn't contradict them: only `dev` is
ever bench-tested (CLAUDE.md), a behavior with no real API/hardware surface gets a documented
structural exception, and a human-only check gets `tests_hardware/manual/`. Part C.8's own
real-hardware-parity bullet is now stated as one instance of this general rule.

**(2) Audited, and one real, non-obvious miscoverage found**: checking the *pre-existing* flash-tier
bus-hazard tests (not just this session's own additions) against their bench-tier counterparts found
that `test_bus_concurrency_under_api_load.py`'s `sgp40_reset_trigger_worker()` looks like it exercises
the SGP40 general-call hazard but does not — `PUT SGPResetVOC` only reaches a software-only VOC reset,
never the real `_reset()`/general-call broadcast, which has no REST trigger on a live system at all.
Closed as a documented structural exception (not fixable - a bench test can't force this without a
real reboot mid-load). Two more gaps were closeable and closed: SGP40 was never schema-sanity-checked
in any bench GET worker (a real corrupted-VOC-reading blind spot); BMP3xx's same-device
write-vs-own-read had no bench counterpart despite having real REST-pushable fields. SCD30's own
same-device write-vs-own-read shares its write-vs-siblings hazard's existing structural exception
(zero `_push_callbacks`), recorded as the same note, not a new one. Full account:
`tests_hardware/README.md`'s own "Ninth pass".

**Verification**: `ruff check` and all three `scripts/typecheck.sh` passes clean on the changed bench
file. Same real-hardware honesty caveat as every other section here: not yet run against silicon.
