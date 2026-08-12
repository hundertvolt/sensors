# Final Wiring Plan — Stage 1 standalone `sensortask-wozi` rewrite

Temporary planning doc, same lifecycle class as `WIRING_CONTRACT.md`/the retired `AUDIT_PLAN.md`:
this is the **global list** for the whole "final wiring-up" effort — ideas, goals, documentation
links, and the criteria that make the five steps' open ends meet when combined into one working
prototype. Deleted once all five steps below have merged back and the large post-merge audit
closes; whatever in here is still true and permanent at that point migrates into CLAUDE.md/
SPECIFICATION.md/`WIRING_CONTRACT.md` instead of staying here, exactly as `AUDIT_PLAN.md`'s own
findings did.

**Goal**: the first technically complete framework setup able to operate on a real RP2040-based
sensor arrangement — *same top-level features* as today's deployed units, just more
consistent/stable (CLAUDE.md's standing working agreement), not a feature change. Scope for this
whole effort stays a **prototype**: `improved-quality/sensortask-wozi.py` (the one deployed
variant, "wozi") only, not the other three variants, and not the future build-script generator
that would turn a setup-definition file into every variant's `sensortask-*.py`/website pair —
this effort must not block that generator (see "Generator-readiness constraint" below) but does
not build it.

## Where the new code actually lives

`improved-quality/sensortask-wozi.py` (755 lines today) is explicitly **read-only reference** for
this whole effort — "a declaration of intention" (owner, confirmed directly), not a file any of
the five steps edits. CLAUDE.md's hard rule already forbids editing `improved-quality/` source
without a scoped, severity-justified owner authorization, and none of the five steps below need
one: nothing here is a bug fix to that file, it's a rewrite that lands somewhere else.

That "somewhere else" is settled by a concrete technical constraint, not a style preference:
Step 5 requires running the finished prototype under the real MicroPython Unix-port interpreter
(`scripts/test.sh`'s `MICROPYPATH="src:tests:.frozen"`) — `improved-quality/` is not on that path
and never will be, so a file that stays there is structurally untestable under this project's own
test infrastructure. The prototype therefore gets built fresh as **`src/sensortask_wozi.py`**
(underscore, matching every other `src/` module's importable-identifier naming, vs. the legacy
hyphenated filename that was itself always renamed to the generic `sensortask.py` at freeze time —
see `build-wozi.sh`) — a new file, informed by the reference but not derived from it mechanically.
`improved-quality/sensortask-wozi.py` itself is untouched by any of the five steps.

Two more locations are settled the same way, by direct precedent already in the docs:

- The generic webserver/API service (Step 2) is **`src/asy_webserver_service.py`** —
  BACKLOG.md's own "Microdot hardening design" entry already names this module and location.
- The digital-twin simulator (Step 3) is **not** `tests/machine.py` (explicit owner instruction —
  don't modify or reuse it) and **not** `src/` either (it's test/dev tooling, not production
  firmware code that ever gets frozen into a real build). It needs its own new top-level location
  (e.g. `digital_twin/`) with its own opt-in `MICROPYPATH` wiring for Step 5's integration run,
  kept separate from the `src:tests:.frozen` set every existing unit test already relies on so
  this doesn't disturb `tests/machine.py`-based tests. Step 3's own session should settle the
  exact directory name and how Step 5 wires it in; this doc only fixes that it's a new location,
  not a repurposing of an existing one.

## Branch / session structure

One branch per step below, sequential, each merged back before the next starts, each branching
off the previous step's merged tip:

```
main
 └─ claude/framework-wiring-rest-api-hx99v7   (this branch — global prep, PR #31)
     └─ Step 1 branch  → merge back into claude/framework-wiring-rest-api-hx99v7
         └─ Step 2 branch  → merge back
             └─ Step 3 branch  → merge back
                 └─ Step 4 branch  → merge back
                     └─ Step 5 branch  → merge back
                                          └─ large audit, then PR #31 → main
```

Suggested branch names (each step's session can rename if it finds a better one, but should stay
inside this scheme so the sequencing is legible from branch names alone):

1. `claude/step1-wiring-construction`
2. `claude/step2-webserver-api-service`
3. `claude/step3-digital-twin-simulator`
4. `claude/step4-website-placeholder`
5. `claude/step5-unix-port-integration`

Each step's PR targets the *previous* branch (not `main`) — only the final, already-open PR #31
(`claude/framework-wiring-rest-api-hx99v7` → `main`) ever targets `main`, once Step 5 merges and
the large audit closes.

## Per-step-session workflow (owner-specified, mandatory for every step below)

Every one of the five step sessions follows this sequence, reproduced here so a fresh session
starting cold on a step branch has it without needing this conversation's history:

1. **Refine and extend this doc's section for your step** into your own, more detailed list:
   ideas, goals, documentation links, and the criteria that must be fulfilled for *your branch* to
   finish. Do your own research (datasheets, current MicroPython/Microdot docs, the legacy driver
   code, `improved-quality/sensortask-wozi.py` as reference) — don't just restate this doc.
2. **Ask 10 top-level clarifying questions**: what needs deciding, the realistic options, and the
   consequences of each. Resolve as much as possible yourself first from project context, internal
   docs, and legacy code before asking — but a genuinely blocking or architecturally significant
   decision is always fair to raise, at any point, not just this round.
3. **Write the full set of unit tests first** (TDD), covering the criteria your own refined list
   settled on.
4. **Write the implementation** against those tests — refine until every test passes and the
   result is lean and efficient, not just "technically satisfies the tests."
5. **Add unit tests for the resulting functional code**, maximizing coverage the same way
   `src/math_helpers.py`'s suite already does for its own file.
6. **Stop and report back to the owner before doing anything more** — merging, starting the next
   step, or any scope beyond what was just built is not this session's call.

A step session can come back to the owner with a blocking question at any point in this sequence,
not only at the end — but the expectation is to have tried project context, docs, and legacy code
as a reference first.

## Original scoping discussion (verbatim record)

The five steps above are a restructured, resolved-conclusions rewrite of the ten clarifying
questions asked at the very start of this effort and the owner's answers to them. Kept here
verbatim, not re-summarized again, because summarizing already lost one fact once: an earlier
first-draft task list (session-local, never committed) said the construction/wiring restructure
would be "implemented in `improved-quality/sensortask-wozi.py`" — wrong per "Where the new code
actually lives" above, and a symptom of exactly the kind of drift that happens when only a
compressed conclusion survives. If anything below and the step sections above ever disagree, the
step sections above win — they're the reconciled version — but this record is the fallback for
recovering *why*, and for anything a later compression pass might have dropped without anyone
noticing.

1. **Scope of "API setup" moving out of `sensortask.py`.** *Answer*: "The scope matters with regard
   to the future plan of creating the sensortask* files automatically. I could imagine a setup like
   giving the webserver wrapper a bunch of sensor data callbacks, a bunch of system state callbacks
   etc... maybe with some names, so it can automatically construct a canonical JSON for the API —
   would be a good scope. Still to be decided which values to wrap in a single endpoint with a
   structured JSON and which ones to get their own endpoint." — the registration-API shape in Step 2
   is settled; **which values land in the single structured status endpoint vs. get their own route
   is not** — still a real open sub-decision for Step 2's own session to make (fair game for one of
   its own 10 questions).
2. **Website placeholder strategy.** *Answer*: "Just stubs for whatever website endpoints will be
   created in (1). The API will significantly change compared to the legacy state." — matches Step
   4's "stub only" framing; the real `html_raw/wozi/` content stays untouched, referenced only.
3. **Unix-port hardware-simulation fidelity.** *Answer*: "let's take a) the digital twin. Some
   sensible in-range arbitrary or random values, and keep it separated from the unit tests for not
   breaking anything there accidentally." — settled, this is Step 3.
4. **System-status endpoint shape/scope, including bus-layer participation.** *Answer*: "Keep the
   buses as they are. DNSServer may be extended by an error counter - it makes sense that every
   module which uses persisted (RAM or FRAM) logging also gets an error counter." — the general rule
   behind Step 1's `get_error_counter()` gap-closing (not just `DNSServer` — the same audit also
   found `NeopixelDriver` missing it).
5. **Real RP2040 firmware build — in scope?** *Answer*: "Real RP2040 build also in this scope.
   Unix-build verification is first, but once that runs, we will try on the real target (manually)."
   — still true of the *overall* effort; predates the five-branch restructuring, so "in scope" here
   means "part of this whole effort," not "one of the five branches" — it's sequenced after all five
   merge, per "Out of scope for all five steps" below. Not a contradiction, just a later finish line.
6. **How far to take "generator-friendly" now vs. later.** *Answer*: "The automated generator shall
   not result in any additional quasi-constant variables which are once set at boot time and from
   then on are constant but consuming memory. So setting it up in the sense of having a template
   with empty constructor calls and the generator filling these calls with lists of callbacks (or
   whatever is appropriate) should do." — the "generator-readiness constraint" in Step 2, worded
   precisely: the objection is specifically to *memory-consuming* quasi-constant globals on a
   memory-constrained target, not to named globals in general.
7. **`@app.errorhandler` registration — bundle in or defer?** *Answer*: "this is fully in scope of
   the Microdot wrapper writing, therefore yes, we will do in this scope." — settled, in Step 2.
8. **Priority order / how to detect the best point to split into a new session.** *Answer*: "Your
   steps are already ordered in good priority. How will we be able to detect the best point to start
   a new session in case it grows too much?" — never answered in words at the time; **now resolved
   structurally, not verbally**, by the five-branch-per-step scheme itself: each step *is* its own
   session by construction, so there's no separate "when to split" judgment call left to make.
9. **Is `improved-quality/sensortask-wozi.py`'s current construction order authoritative, or does it
   need active fixing?** *Answer*: "Confirmed. All content of improved_quality/sensortask_wozi.py can
   be regarded as a declaration of intention, not necessarily complete, and a collection of comments
   and adaptations in the course of prior refactoring. So no need to work around it, structure it in
   the most efficient way for a constrained system like the RP2040." — the basis for "Where the new
   code actually lives" above: the reference file is intent, not a constraint to preserve mechanically.
10. **Verification bar / TDD sequencing.** *Answer*: "We will do the unit tests here as well. With
    'come later' I meant that we will first create an extensive ordered action list. Once that list,
    not actual code work, is complete and additional information was fetched / gathered, we will
    create a whole bunch of unit tests in the sense of test driven development and do some discussion
    and decision rounds before." — the origin of the "per-step-session workflow" above.

## The five steps

### Step 1 — Construction/wiring restructure

**Goal**: turn `improved-quality/sensortask-wozi.py`'s flat, synchronous, module-level
construction sequence into `src/sensortask_wozi.py`'s async-safe equivalent, preserving every
piece of runtime behavior the reference file establishes.

**Known findings to carry in** (already resolved by prior research this session, not open
questions for Step 1 to re-litigate):

- `WIRING_CONTRACT.md`'s central finding: the sync-`__init__`/async-`setup()` pattern
  (`SPECIFICATION.md` Part C.13) means `bmp_reader`, `sgp_reader`, and `notify_service` each need
  an added `await x.setup()` call that isn't in the reference file — this breaks the flat
  top-level-statement shape and forces some async wrapping (an `async def main()`-style boot
  sequence, most likely) for at least everything from the first `await`ed step onward.
- The **FRAM chunk-order determinism rule** (`SPECIFICATION.md` Part A.4) must survive this
  restructure exactly: `SystemService` → `SGP40_Reader` (its own error log) → `SGP40_Reader` (VOC
  backup chunk) → `NeopixelDriver` → `NotificationCoordinator` — five chunks, not four; corrected
  during Step 1's own session after confirming `SGP40_Reader`'s own logger is already FRAM-backed
  (`WIRING_CONTRACT.md` item 8) — in that relative order, regardless of `await`s introduced around
  them. `WIRING_CONTRACT.md` is the living reference for this — **update it**, don't let it drift,
  once Step 1's actual construction order is decided.
- Two modules are missing `get_error_counter()` despite persisting logs via `PrintLogHistory`:
  `captive_dns.py`'s `DNSServer` and `src/asy_neopixel_driver.py`'s `NeopixelDriver`. Every other
  promoted module already exposes it with the standard
  `{"<NAME>": {"ErrCount", "ErrNum", "ErrType"}}` shape. Step 2's aggregation endpoint needs this
  gap closed everywhere it touches, so it belongs in Step 1 (construction-time module completeness)
  rather than being rediscovered in Step 2.
- Bus construction stays as-is (`asy_i2c_driver.I2C`/`asy_spi_driver.SPI` wrapping
  `machine.I2C`/`machine.SPI` unchanged) — owner-confirmed, not something to redesign here.

**Doc links**: `WIRING_CONTRACT.md` (the whole document), `SPECIFICATION.md` Part A.4 (FRAM
determinism), Part C.13 (setup()-gate pattern), Part C generally (driver/service architecture
shape), CLAUDE.md's platform-target Part F pointers (soft-Timer-drop, `Timer.init()` `ENOMEM`,
`[x]*n` segfault range — all relevant to anything touching `Timer`/list-construction during boot).

**Criteria for this step to finish**: `src/sensortask_wozi.py` exists, constructs every module the
reference file constructs, in FRAM-chunk-preserving order, with every needed `await setup()` call
in place; `DNSServer`/`NeopixelDriver` both expose `get_error_counter()`; `WIRING_CONTRACT.md`
updated to describe the *new* construction order as current, not the old flat one; full unit-test
coverage per the workflow above (construction-order tests, FRAM-chunk-order tests, boot-sequence
tests using `tests/machine.py`, not the digital twin — Step 1 has no dependency on Step 3).

**Done** (this session): all of the above landed — `src/sensortask_wozi.py`'s `build_system()`,
`boot_entry/wozi_boot.py`, `get_error_counter()` on `DNSServer`/`NeopixelDriver`,
`tests/test_sensortask_wozi.py` (16 tests), `WIRING_CONTRACT.md` rewritten in place, the
`max_i2c_err` → `max_module_error` rename, and the full existing test suite re-verified green.
See the "Refined plan" subsection below for the design decisions this took, and its own trailing
note on the one real behavior finding (`AsyConnTime`'s `start_hotspot_timeout_watcher`) surfaced
along the way. **Also done, added later in the same session per explicit owner follow-up
direction** (not part of the original Step 1 scope above, but landed inside this step's session
rather than deferred): the "never insist on FRAM" audit (every FRAM-backed error log/persistence
path already degraded gracefully to plain RAM when `fram=None`; added one regression test
constructing the whole object graph against a simulated dead FRAM chip) and live, persisted,
range-checked debug-level setting via a boot-time-collected registry of each module's own
`set_level()` — see the `watchdog`/`debug` split bullet below and `WIRING_CONTRACT.md`'s "Debug
level" section for the full design and the rejected `SharedLevel` alternative.

**What Step 2 needs from this step**: every long-lived module Step 1 constructs must be reachable
(directly or via a bound method) from wherever `src/sensortask_wozi.py` ends up handing things to
the webserver service — Step 1 does not need to invent the registration API shape itself (that's
Step 2's job), just make sure nothing it builds makes registration harder (e.g. no module that's
only reachable through a closure Step 2 can't get a reference to).

**Refined plan — resolved via project-owner Q&A this session** (supersedes/extends the above
where the two differ; kept as its own subsection rather than rewritten in place so the original
findings above stay legible as the starting point):

- **File layout — two files, not one.** `src/sensortask_wozi.py` stays the single testable module
  ("Where the new code actually lives" above), but it gets **no top-level blocking call** — no
  bare `asyncio.run(main())` at module scope. Instead it exposes `async def build_system() ->
  <components>` (pure construction + the setup()-batch below, no task loop) and `async def main()`
  (calls `build_system()`, then `start_timers()`/`start_and_check_tasks()`, matching the reference
  file's own `main()` shape). A test can `import sensortask_wozi` and call `build_system()`
  directly without ever blocking. The actual "importing this triggers boot forever" behavior the
  real firmware needs (matching what `modules/_boot.py`'s `import sensortask.py` expects today)
  moves to a new, separate, minimal file — **`boot_entry/wozi_boot.py`** (new top-level folder,
  self-explanatory name, not `src/` or `tests/`): `import asyncio; from sensortask_wozi import
  main; asyncio.run(main())`, a handful of lines, nothing else. Owner-confirmed: this is new code
  in a new location, not an edit to any legacy file, and `modules/_boot.py`'s own import mechanism
  itself stays untouched (CLAUDE.md's hard rule) — how `boot_entry/wozi_boot.py` eventually gets
  frozen/wired into a real build is Step 5's "full Unix-port integration"/assembly job, not Step
  1's; Step 1 only needs the file to exist and be correct in isolation.
- **No Microdot, no routes, no `frozen_html` import in Step 1.** Confirmed: `app = Microdot()` and
  every `@app.get/put` handler stay reference-only in `improved-quality/sensortask-wozi.py` for
  Step 2 to reimplement as the registration-based service — copying them into `src/sensortask_wozi.py`
  now would be wasted work under a paradigm Step 2 replaces wholesale. Same for `import frozen_html`
  (Step 4's job to give that import something real).
- **Object graph stays bare module-level globals**, matching the legacy file's own shape — no
  wrapper dataclass/NamedTuple container. Confirmed this isn't in tension with the
  "generator-readiness" constraint (BACKLOG.md/Step 2's own concern): that constraint is about
  Step 2's *callback-registration* API not emitting many quasi-constant globals per field: it
  doesn't reach this dozen-or-so core singleton references, which have to live somewhere in memory
  regardless of how they're named.
- **`await x.setup()` batching, resolved by dependency analysis, not by default:** the four
  `setup()` calls in play are actually **three independent domains**, not one: (1)
  `AsyFramManager.setup()` — real FRAM-chip SPI readiness, gates any FRAM chunk read/write; (2)
  each module's own `PrintLogHistoryStore.setup()` (`self.pr.setup()`) — FRAM-backed error-log
  persistence, depends on (1) but already runs safely later, inside each module's own task, in the
  existing reference file; not something Step 1 needs to add or reorder. (3) `ConfigManager.setup()`
  (via `SensorReaderConfig.setup()`, called on `sgp_reader`/`bmp_reader`/`notify_service`) — reads
  each module's own local JSON config file, **entirely independent of FRAM** and of each other; this
  is what WIRING_CONTRACT.md's finding is actually about. Between the three new (3)-domain calls and
  the one existing (1)-domain call (`fram.setup()`), there is no real cross-dependency requiring
  interleaving. There **is** one hard, real ordering constraint, though, found by reading
  `asy_notification_service.py` directly: `NotificationCoordinator.setup()`'s own docstring says
  "call after `finalize()`, before any task starter runs" — its `self.cfgmgr` doesn't exist until
  `finalize()`'s delayed `super().__init__()` runs, so `await notify_service.setup()` immediately
  after `notify_service = NotificationCoordinator(...)` (before `register()`×3/`finalize()`) would be
  an outright bug, not just a style choice. **Resolution: grouped/batched, not interleaved** — one
  dedicated async phase, positioned exactly where the reference file's existing `async_onetime`
  list already sits (after all synchronous construction, including `notify_service`'s
  `register()`/`finalize()`, before `start_timers()`), in fixed order `fram.setup()` →
  `sgp_reader.setup()` → `bmp_reader.setup()` → `notify_service.setup()` (fram first, matching its
  existing position; the three new ones appended in their own construction order). This is the one
  scheme applied consistently, per the "don't mix schemes" instruction — no setup() call happens
  interleaved with construction anywhere in the file.
- **`_MAX_I2C_ERR` → `_MAX_MODULE_ERROR` rename, now in scope and project-wide** (previously
  deliberately deferred per `SPECIFICATION.md` C.2/BACKLOG.md — owner has now explicitly authorized
  it). Touches: `base_classes.py` (`SensorReader.__init__`'s `max_i2c_err` param and
  `self.max_i2c_err` attribute, plus every internal reference), every module that takes/forwards it
  (`asy_wifi_service.py`, `asy_ntp_client.py`, `asy_sgp40_driver.py`, `asy_bmp3xx_driver.py`,
  `asy_scd30_driver.py`, `asy_notification_service.py`), and every test file constructing these
  objects with `max_i2c_err=`. Rename to `max_module_error`/`_MAX_MODULE_ERROR` (mirrors the
  owner's own suggested name exactly). Mechanical but wide; done as part of Step 1's implementation
  pass since `src/sensortask_wozi.py`'s own top-level constant is exactly where this originates.
- **Constants organization**: every module-level constant in the new file (the renamed
  `_MAX_MODULE_ERROR`, DNS/NTP timeouts, hotspot timing, etc.) grouped together in one clearly
  readable block, since a future generator script is expected to fill/edit these — values copied
  verbatim from the reference file, no re-tuning.
- **`watchdog`/`debug` split**: `watchdog = WDT(timeout=8000)` constructed directly in
  `build_system()`, hardcoded, no injection point (owner: "must be hardcoded so no error ever can
  circumvent it"). `debug` seeds each module's constructor as before, but — per explicit owner
  follow-up direction later in this same session — it's no longer construction-time-only: it's now
  live-settable and persisted via `SystemService.set_debug_level()`/`config_SYSTEM.cfg`, broadcast
  to every module's logger through a boot-time-collected registry of `set_level()` bound methods
  (`SystemService.set_level_setters()`, populated by `sensortask_wozi.py`'s
  `_collect_level_setters()`), not a shared/live-read value on `PrintLog` itself — see
  `WIRING_CONTRACT.md`'s "Debug level" section for the full design, the concurrency-safety
  verification, and the rejected `SharedLevel` alternative. Landed inside Step 1's own scope rather
  than deferred to Step 2, since the owner asked for it directly in-session.
- **`WIRING_CONTRACT.md` maintenance**: rewritten in place once the new construction order lands
  (owner-confirmed), not kept alongside the old flat description.
- **Task/timer starter collection uses each module's own `get_task_starters()`/`get_timer_starters()`
  uniformly, not the reference file's hand-copied bound-method list — a real finding, not a style
  choice.** Confirmed by direct comparison: `AsyConnTime.get_task_starters()` includes
  `start_hotspot_timeout_watcher` (the task backing `hotspot_time_min`'s actual timeout behavior),
  which the reference file's own hand-written `task_starters` list in `main()` never starts.
  `src/sensortask_wozi.py` now starts it. Flagged here rather than silently carried forward or
  silently dropped, per CLAUDE.md's discrepancy-flagging convention — worth a second look if a real
  deployed unit's hotspot-timeout behavior is ever compared before/after this rewrite.

### Step 2 — Generic webserver/API service

**Goal**: move the Microdot wrapper (startup, stability/restart control, route construction) out
of `src/sensortask_wozi.py` entirely into `src/asy_webserver_service.py`, as a **registration-based
service** — modules hand it named sensor-data/system-state callback groups, and it auto-constructs
the canonical REST/JSON surface, including one regularly-structured system-status endpoint
aggregating every module's `get_error_counter()` output.

**Known findings to carry in**:

- BACKLOG.md's "Microdot hardening design" is a fully-settled, not-yet-implemented plan: composition
  around `asyncio.start_server()` (never call `app.start_server()`/`app.shutdown()` directly), a
  reader/writer timeout-wrapping proxy, per-connection open-count tracking (`LockedCounter`-style,
  decremented in a `finally`), whole-server restart when the open count sits at/above a threshold
  for longer than a grace period, registered as an ordinary task in `start_and_check_tasks()` so the
  existing task-supervisor/watchdog-escalation machinery handles restart-then-reboot for free. Read
  the whole entry, including its "verify before implementing" `asyncio.wait_for()` note and its
  "confirmed boundary" analysis of `handle_request()`'s shape (nothing inside `dispatch_request()`
  ever touches the transport, so the proxy alone is sufficient — no route-handler-level wrapping
  needed).
- The concurrent-socket/TCP-PCB ceiling this design's restart threshold must sit under is
  **confirmed at 5** (`MEMP_NUM_TCP_PCB`'s rp2-port default, `lwipopts_common.h` — see BACKLOG.md's
  now-resolved companion open question). Pick a real-margin threshold below that, not at it.
- `ext/microdot.py` (vendored, unmodified, pinned to `v2.6.2`) is hands-off — any behavior change
  happens by wrapping/calling it from `asy_webserver_service.py`, never by editing the vendored file
  itself. See CLAUDE.md's hard rule and `SPECIFICATION.md` Part A.5 for exactly what Microdot
  already guarantees per-request (blanket exception catch, the one real gap in `Response.write()`)
  versus what this project's layer still has to add — no `@app.errorhandler` is registered anywhere
  today; this step is also where that gets added (see BACKLOG's "REST/error-handling layer" entry
  right above the hardening design for the specific 400/404/405/413/500 + JSON-serializability
  requirements).
- **Generator-readiness constraint** (owner-specified): the registration API must not require the
  future per-variant build-script generator to emit many individually-named quasi-constant globals.
  The right shape is a small number of constructor/register calls, each filled with a *list* of
  callbacks — e.g. one call registering all of one module's status getters, not one named global
  per field. This doesn't block anything about this step's own design, it's a shape constraint on
  the registration API itself.

**Doc links**: BACKLOG.md's "Microdot hardening design" and "REST/error-handling layer" entries in
full, `SPECIFICATION.md` Part A.5, `ext/microdot.py` (read directly for exact call sites — grep for
every `reader.`/`writer.`/`stream.` method the proxy needs to forward, don't guess the list),
`src/system_service.py` (`start_and_check_tasks()` is the existing supervisor this service's restart
task plugs into unchanged).

**Criteria for this step to finish**: `src/asy_webserver_service.py` exists; registration API
matches the generator-readiness shape above; every route the reference file has today
(`/net/*`, `/time/*`, `/sensors/*`, `/led/*`, `/system/*`, plus static routes) is reachable through
it with identical response shapes; `@app.errorhandler` wired for at least 400/404/405/413/500;
timeout-wrapped proxy + open-count tracking + threshold-based restart implemented and soak-tested
(100+ start/wedge/reclaim/restart cycles under the Unix port, `gc.mem_free()` flat) per the design
sketch's own step 5; full unit-test coverage, test doubles for reader/writer are step-driven fakes
only (never a real `select.poll()` — see CLAUDE.md's CI-hang-investigation note for exactly why).

**Refined plan — this session's own research, before the owner Q&A round** (extends the above;
kept as its own subsection per Step 1's precedent, so the original scoping stays legible as the
starting point):

- **Doc-currency check done this session (CLAUDE.md's standing instruction, not skipped)**:
  upstream `miguelgrinberg/microdot`'s latest release is still `v2.6.1`/`v2.6.2` (May 2026) as of
  this check — no newer tag, and no timeout-related feature has landed since BACKLOG.md's own
  research confirmed "zero timeout occurrences anywhere in `microdot.py`." The vendored
  `ext/microdot.py` pin is current; the hardening-design's premise (Microdot itself will never grow
  this feature upstream in a way we could just adopt) still holds. MicroPython's own `asyncio` docs
  (latest + v1.25.0, both checked) confirm `asyncio.wait_for()`/`wait_for_ms()` is the documented,
  intended mechanism for bounding a stream read, raising `asyncio.TimeoutError` on expiry — matches
  the design sketch's assumption, nothing to revise there.
- **One concrete new finding from this check, worth folding into the design before implementation
  starts**: `asyncio.TimeoutError` **is** an `OSError` subclass (`errno=110`, `ETIMEDOUT`) on
  MicroPython, not a bare `Exception` — and `errno 110` is **not** in `ext/microdot.py`'s own
  `MUTED_SOCKET_ERRORS` list (`[32, 54, 104, 128]`). Concretely: `handle_request()` wraps
  `Request.create()` in `except OSError as exc: if exc.errno in MUTED_SOCKET_ERRORS: pass else:
  raise` — a timeout raised by our proxy's wrapped `readline()`/`readexactly()` call (reached from
  inside `Request.create()`) is an unmuted `OSError`, so Microdot's own catch **re-raises it out of
  `handle_request()` entirely**, rather than quietly resolving to a 400 response the way a non-`OSError`
  would. This means our own `serve()` wrapper (the one calling `await app.handle_request(...)`, per
  the design sketch's step 1) **must** itself catch this — it is the expected, common-case outcome
  for a wedged/slow-going-silent client, not a rare edge case — and treat it exactly like the design
  sketch's step 6 already says any wrapper-level failure should be treated: log via `pr.wrn_s`/`err_s`
  and let that one connection's task end, `finally`-decrementing the open-connection counter. Nothing
  in the settled design actually assumed otherwise, but this is worth stating explicitly rather than
  discovering it mid-implementation: **the timeout path does not flow through Microdot's own
  error-response machinery at all** (no 5xx ever gets written back — the socket is simply abandoned
  the way a genuinely dead TCP peer would be), which is the correct behavior for this failure mode
  (matching a real client timeout), not a gap to fix.
- **Resolved myself, not asked below** (context/legacy code already settles these):
  - The webserver service's own diagnostics need a plain `PrintLog` (`self.pr`), not a full
    `SensorReaderConfig`/`ConfigManager` — BACKLOG.md is explicit that "this module's own safety
    constants deliberately have no config schema/REST surface," so it has no config file to load and
    no `setup()`-gate need; it follows `NeopixelDriver`'s/`SCD30_Reader`'s shape (`self.pr` only, no
    `cfgmgr`), not `SGP40_Reader`'s. It still needs a `get_error_counter()` (so it participates in the
    aggregation it itself serves) and a `get_task_starters()` (the restart-capable server task) —
    `sensortask_wozi.py`'s `_collect_level_setters()`/`_collect_task_starters()`/
    `_collect_timer_starters()` all need one more entry each once this module is wired in; that edit
    to the already-merged `src/sensortask_wozi.py` is in scope for this step (it's a freely-editable
    `src/` file, not `improved-quality/`).
  - Every registered callback is async — matches literally every existing `get_dict_data()`/
    `get_dict_cfg()`/`get_error_counter()`/setter method in the whole codebase; no case for accepting
    sync callables and building `invoke_handler`-style dual dispatch to support them.
  - `abort()`/`HTTPException` is only ever needed for Microdot's own built-in triggers (413 from
    `max_content_length`, plus whatever `@app.errorhandler(404)`/`(405)` we register to shape their
    bodies) — no route handler in the reference file ever calls `abort()` today, they all return an
    `ar.make_response()`-shaped dict directly, including for validation failures. The new registration
    layer should keep that convention rather than introducing a second error-reporting path.

**What Step 4 needs from this step**: a defined extension point for static/frozen content —
whatever shape `register_static_routes()`-or-equivalent takes, Step 4 should only need to supply
content plus a freezefs build step, not touch webserver internals.

**Endpoint design — decided by the project owner ahead of the dedicated webserver-integration
session** (this is a design decision, not yet an implementation — the actual `asy_webserver_service.py`
build, including the registration API's exact call signatures, is explicitly deferred to that
session; this subsection is the settled contract it starts from):

- **Six external endpoints, replacing the legacy `/net/*`, `/time/*`, `/sensors/*`, `/led/*`,
  `/system/*`**: `/measurements`, `/sensors`, `/networking`, `/system`, `/status`, `/notification`.
  Legacy `/time/*` splits across `/system` (GMTOffset/DSTOffset — local-time *interpretation*) and
  `/networking` (NTP_Host/NTP_Offset_S/NTP_Interv_H — sync *mechanics*).
- **Clean live-vs-settings split, no endpoint mixes the two**: `/measurements` and `/status` are
  the only two live-data endpoints (fully live, no persisted settings in either); `/sensors`,
  `/networking`, `/system`, `/notification` are pure settings (fully persisted config, no live
  telemetry in any of them). This moved `Connected`/`IP`/`Rssi`/`Wifi_Uptime`/NTP sync state out of
  `/networking` and `NotificationCoordinator`'s `Triggered`/`TS`/`pauseTime` out of `/notification`
  — both now live under `/status` instead.
- **GET shapes**:
  - `/measurements` → `{"SCD30": {...}, "SGP40": {...}, "BMP3XX": {...}}` — one entry per sensor
    reader in a plain list at init (see "Registration style" below), `get_dict_data()` each.
  - `/sensors` → same per-sensor sub-structure as `/measurements`, `get_dict_cfg()` each.
  - `/networking` → flat settings only: `SSID, PW(masked), Country, Hostname, LedWifiOn, NTP_Host,
    NTP_Offset_S, NTP_Interv_H`.
  - `/system` → flat settings only: `DebugLevel, GMTOffset, DSTOffset`.
  - `/notification` → flat settings only: `OnH, OnM, OffH, OffM, FlashBri, Interv, FlashDur,
    AutoOn, WarnCO2, WarnVOC, WarnHum`.
  - `/status` → live-only, sub-structured with top-level keys named after the settings endpoints
    they mirror:
    ```
    {
      "networking": {WifiUptime, Mode, Connected, IP, IPv4, Subnet, Gateway, DNS, Rssi,
                     NtpSynced, NtpLastSyncAge, NtpLastSync},
      "system":     {SysUptime, BootSignature, MemPaused, LocalTime: {...}, UtcTime: {...}},
      "sensors":    {"SGP40": {BackupTS, RestoreTS}},   // only sensors with maintenance data
      "notification": {Triggered, TS, PauseTime},
      "errcount":   {"<Name>": {"counter": int, "history": [{"num": int, "type": "N"|"E"|"W"}, ...]}}
                    // one entry per module + one per ConfigManager ("CFGMGR_<name>"); "history"
                    // present wherever that module's logger actually persists ErrNum/ErrType entries
    }
    ```
- **PUT shapes — one sparse JSON per endpoint, no `cmd` envelope** (replaces
  `parse_cmd_request()`'s allowed-command-list pattern for these six routes): any field present is
  applied, any field/sub-object omitted is left untouched, unknown fields are ignored — the same
  permissive strategy `ConfigManager.write_config()`/`_set_dict_cfg()` already use internally, now
  extended to be the *only* strategy at the HTTP layer too.
  - `/measurements` — no PUT.
  - `/sensors` — `{"SCD30": {<any subset of TempOffs,MeasInt,AmbPres,Altitude,ForceCalRef,SelfCal,
    ContMeas>}, "SGP40": {<any subset of BackupPeriod,BackupMaxAge,WaitTimeNTP,SGPResetVOC>},
    "BMP3XX": {<any subset of the 8 fields>}}` — any sensor key or field can be omitted; a single
    field for a single sensor, all fields for one sensor, or all fields for all sensors are equally
    valid in one call.
  - `/networking` — `{<any subset of SSID,PW,Country,Hostname,LedWifiOn,NTP_Host,NTP_Offset_S,
    NTP_Interv_H>}`.
  - `/system` — `{<any subset of DebugLevel,GMTOffset,DSTOffset>, "SystemCmd":
    "reboot"|"bootloader"|"mempause"}` — `SystemCmd` optional, still strictly enum-validated (the
    "safe, non-accidental enum" property of the old `content` field is kept, just folded into the
    same JSON body instead of a separate `cmd`-wrapper route). `mempause`'s duration stays the
    legacy **fixed 300s**, not client-supplied — no companion duration field.
  - `/status` — `{"ResetErrors": true}` only, for now (absent/false is a no-op) — resets every
    module's error counter *and* history in one global action, not scoped per-module.
  - `/notification` — `{"lightCmdLED": {"r":.., "g":.., "b":.., "t":..}, "PauseTime": int, <any
    subset of OnH,OnM,OffH,OffM,FlashBri,Interv,FlashDur,AutoOn,WarnCO2,WarnVOC,WarnHum>}` —
    `lightCmdLED` nested, everything else flat top-level, all optional.
- **GET copy-safety, checked directly against `src/print_log.py`/`src/config_manager.py`, no new
  locking needed**: `get_dict_data()` (via `config_manager.make_dict()`), `ConfigManager.get_dict()`,
  and `PrintLogHistory.get_log()` already build a brand-new dict/list of copied scalar values on
  every call, with no `await` in the middle of that construction — MicroPython's cooperative,
  non-preemptive scheduling (CLAUDE.md Part F) means a synchronous stretch of code with no `await`
  can't be interleaved by another coroutine, so these snapshots are already atomic and independent
  of anything that happens afterward; no caller ever gets a live reference into `_cache`/`history`.
  `ConfigManager.config_lock` (an `asyncio.Lock`) exists and is used, but only inside
  `write_config()`, to serialize concurrent *writers* against each other (its own comment already
  documents why readers don't need it: the commit step `self._cache = new_cache` is a single
  reference swap with no `await` before it). **One known, pre-existing exception, not introduced by
  this design and not fixed by it**: `SCD30_Reader.get_dict_cfg()` (entirely) and three of
  `BMP3xx_Reader.get_dict_cfg()`'s fields (`PressOvers`/`TempOvers`/`FiltCoeff`) are live
  hardware-readback fields — their callback does `await` a real I2C transaction mid-dict-construction,
  so a concurrent config write interleaving between two such awaited reads could produce one response
  with a mix of pre- and post-write values across fields. This is a torn-read-across-fields
  characteristic already present in those two drivers today, unrelated to "a reference to mutable
  state leaking out" (each individual field value is still a fresh read, never a stale reference) —
  flagged for awareness, not treated as something this endpoint redesign needs to fix.
- **Registration style — everything supplied as lists at init, generator-fillable**: the
  constructor/registration surface `src/asy_webserver_service.py` exposes must, per module, be
  "append this module (or its relevant bound methods) to the right list" — never a new named global
  per field or per module. This mirrors `_collect_task_starters()`/`_collect_timer_starters()`/
  `_collect_level_setters()`'s existing shape exactly (uniform lists, even where a given variant
  only has one or two real entries), so a future per-variant generator only ever needs to know "does
  this variant have module X" and append accordingly — it never needs to know anything about field
  names or endpoint shapes.
- **Known gaps for the implementation session to close, not resolved here**:
  - `SCD30_Reader` has no generic `_set_dict_cfg`-style setter (individual named methods only,
    `ContMeas` handled by a bespoke wrapper in the legacy webserver file) — the sparse-JSON `/sensors`
    PUT contract above still has to apply to it, so either a schema-driven dispatch gets added to
    `asy_scd30_driver.py` itself, or the webserver layer carries its own field-dispatch table for
    this one sensor. Worth deciding early in that session since it affects the registration API's
    generality.
  - `reset_error_counter()` is confirmed present on `base_classes.py` (shared by every
    `SensorReader`/`SensorReaderConfig`), `SystemService`, `AsyFramManager`, and
    `NotificationCoordinator`, but not yet confirmed for `NeopixelDriver`, `DNSServer`, or
    `ConfigManager` — `/status`'s `ResetErrors` needs it everywhere `get_error_counter()` exists, so
    any gap needs adding (freely-editable `src/` files, same precedent as Step 1's
    `get_error_counter()` gap-closing on these same two modules).

**Detailed TDD action list — collected from this session's endpoint-design discussion plus
BACKLOG.md's "Microdot hardening design"/"REST/error-handling layer" entries and `SPECIFICATION.md`
Part A.5** (this is the concrete, expanded version of "Criteria for this step to finish" above —
the implementation session should write tests against this list before writing any
`asy_webserver_service.py` code, per the per-step-session workflow's TDD ordering). Every line is a
test to write, not yet a test that exists.

**A. Endpoint contract tests** (per endpoint, against the settled GET/PUT shapes above):
- [ ] `/measurements` GET returns the merged 3-sensor dict; empty sensor list registered → empty
      dict, not a crash (registration-list edge case, see C below).
- [ ] `/sensors` GET mirrors `/measurements`' per-sensor structure with config fields.
- [ ] `/sensors` PUT: empty body `{}` → no-op, all fields unchanged; single field for one sensor;
      all fields for one sensor; all fields for all sensors; unknown sensor key ignored; unknown
      field within a known sensor ignored (matches `_set_dict_cfg`'s existing per-field
      `"Invalid"`, not a whole-request failure); `SCD30`'s `ContMeas`/`SGP40`'s `SGPResetVOC`
      round-trip as ordinary fields, no `cmd` wrapper.
- [ ] `/networking` GET is flat settings only — no `Connected`/`IP`/`Rssi` present.
- [ ] `/networking` PUT: partial-field update triggers only the relevant post-write hook
      (`reconnect_wifi`/`ntp_force_sync`), not both, when only one module's fields are present.
- [ ] `/system` GET is flat `{DebugLevel, GMTOffset, DSTOffset}` only.
- [ ] `/system` PUT: settings-only body (no `SystemCmd`) applies settings and takes no lifecycle
      action; `SystemCmd` present with an invalid/non-enum value is rejected without side effects;
      each of `reboot`/`bootloader`/`mempause` fires the right `sysfunct` call; `mempause` always
      uses the fixed 300s, never a client-supplied duration.
- [ ] `/status` GET returns exactly the `networking`/`system`/`sensors`/`notification`/`errcount`
      sub-structure, no settings fields anywhere in it; `sensors` sub-key omits any sensor with no
      maintenance data (today: only `SGP40` present).
- [ ] `/status` PUT: `{}` and `{"ResetErrors": false}` are both no-ops; `{"ResetErrors": true}`
      resets every module's counter *and* history in one call.
- [ ] `/notification` GET is flat settings only — no `Triggered`/`TS`/`PauseTime`.
- [ ] `/notification` PUT: `lightCmdLED` nested sub-object round-trips independently of the flat
      top-level fields in the same body; a body with only `PauseTime` doesn't touch the notify
      schedule fields and vice versa.

**B. Cross-endpoint sparse-JSON PUT semantics** (one shared test matrix, run against every settings
endpoint so the convention is actually uniform, not just true by accident per-endpoint):
- [ ] Missing field/sub-object at any level → left untouched (not reset to default).
- [ ] Unknown top-level key, unknown nested key, unknown sensor name → silently ignored, no error
      surfaced (matches `ConfigManager.write_config()`'s existing per-key `"Invalid"` handling).
- [ ] Wrong top-level JSON type (array, string, number, `null` instead of an object) → clean
      rejection, not a crash inside the dispatch layer.
- [ ] Wrong type for a known field (string where int expected, etc.) → per-field rejection, doesn't
      abort the rest of the request's other valid fields.
- [ ] Malformed/undecodable JSON body entirely → same `request.json`-raises handling
      `api_response.py`'s `parse_cmd_request()` already does today (still relevant even though the
      `cmd` envelope itself is gone — `request.json`'s own failure mode doesn't change).
- [ ] Duplicate keys in the raw JSON text (undefined-order behavior) — confirm what MicroPython's
      `json` module actually does (last-wins is the CPython behavior; verify, don't assume) and
      write the test against the confirmed behavior, not an assumption.
- [ ] Deeply nested / recursive JSON body — confirm MicroPython's `json.loads()` has a sane
      recursion bound on this platform (embedded stack is small; this is a real crash vector, not
      theoretical) and that hitting it degrades to a clean rejection, not a hard fault.
- [ ] Body at/near `max_content_length` — boundary-tested both just under and just over.

**C. Registration API tests** (generator-readiness shape — lists at init):
- [ ] A list with zero entries for any registration group (e.g. no sensors registered) produces a
      well-formed empty response, not an exception.
- [ ] A list with one entry behaves identically whether supplied via the list-based API or
      hand-constructed — no special-casing "one module" vs "many."
- [ ] Registering the same module twice (a generator bug, not an expected real case) has a defined,
      tested behavior (last-wins, first-wins, or explicit rejection — pick one and test it, don't
      leave it as accidental behavior).

**D. Error aggregation / reset tests**:
- [ ] `/status`'s `errcount` includes one entry per module *and* one per `ConfigManager` instance
      (`CFGMGR_<name>`), built from the same registry list used elsewhere (mirrors
      `_collect_level_setters()`'s "every logger, including nested `cfgmgr.pr`" shape).
- [ ] `"counter"` is always present; `"history"` is present exactly when the underlying logger
      actually persists `ErrNum`/`ErrType` entries — test both a populated and an all-zero history.
- [ ] `ResetErrors` calls `reset_error_counter()` on every module in the same registry — including
      confirming/adding it on `NeopixelDriver`/`DNSServer`/`ConfigManager` first (the coverage gap
      already flagged above).
- [ ] A `reset_error_counter()` call on one module never affects another module's counter/history.

**E. GET snapshot/copy-safety tests** (regression coverage for the "full copy, no live references"
finding above):
- [ ] For at least one settings endpoint, interleave a concurrent PUT with a GET in the test event
      loop and assert the GET response is never a mix of pre- and post-write field values (should
      hold everywhere except the already-flagged `SCD30`/`BMP3xx` live-readback fields).
- [ ] A dedicated **characterization test** (expected to demonstrate the known gap, not to pass
      cleanly) for `SCD30_Reader`/`BMP3xx_Reader`'s torn-read behavior — documents the gap in a
      runnable form so a future fix (see the new BACKLOG.md entry) has a red test to turn green,
      instead of the gap being only prose.
- [ ] Mutating a list/dict returned from any getter (`get_dict_data`/`get_dict_cfg`/
      `get_error_counter`) never affects the module's own internal state on a subsequent call.

**F. Connection-lifecycle robustness — "must all self-heal"** (this is the deep-networking testing
the owner asked for; grouped by where in a connection's life each scenario happens, extending
BACKLOG.md's already-settled hardening design rather than redeciding it):

*F.1 — Before/at accept:*
- [ ] Client opens a TCP connection and sends nothing, ever (the actual 2026-08-03 incident shape)
      → reclaimed by the per-call timeout, open-count decremented, no leak.
- [ ] Client opens then immediately closes (RST or FIN) before sending any bytes → clean
      decrement, no exception escapes the connection task.
- [ ] Rapid connect/disconnect churn (many short-lived connections in quick succession) → counter
      stays accurate, no double-decrement, no drift.
- [ ] Legitimate concurrent connections at/near the TCP-PCB ceiling (5) → threshold-restart logic
      exercised by genuinely healthy-but-many clients, not just wedged ones — confirms the
      threshold doesn't fire on legitimate load.

*F.2 — Mid-request, headers/request-line:*
- [ ] Slow client trickling the request line/headers one byte at a time, each byte arriving just
      under the per-call timeout → **open design question, not yet answered**: does the per-call
      `wait_for()` wrapping (BACKLOG's design) allow this to stay alive indefinitely (a Slowloris
      shape)? If so, is the open-connection-count/threshold-restart backstop alone considered
      sufficient, or does this step also need a per-request wall-clock cap? Flag for Step 2's own
      Q&A round, don't silently decide either way here.
- [ ] Malformed request line/headers (garbage bytes, bad HTTP version, oversized header) → Microdot's
      own parsing failure path exercised, connection closed cleanly, no crash.
- [ ] `Content-Length` larger than the body actually sent, then the client goes silent → the
      `readexactly()` proxy call times out the same as any other wedge.
- [ ] `Content-Length` exceeding `max_content_length` → confirmed `@app.errorhandler(413)` fires
      with the project's shaped response, connection still closes/decrements cleanly.
- [ ] Body genuinely truncated (client sends FIN mid-body, not just going silent) → **needs its own
      research**: confirm what MicroPython's `asyncio.StreamReader.readexactly()` actually raises
      on early peer close (likely `EOFError`, not `OSError`/`TimeoutError`) and that the `serve()`
      wrapper's catch-and-log-and-end-connection handling (currently specified only for the
      `TimeoutError`/`OSError` path) also covers this distinct failure mode.

*F.3 — Mid-request, JSON body:* covered by section B above (sparse-JSON semantics under malformed/
adversarial input), applied per-endpoint.

*F.4 — Mid-response, write phase:*
- [ ] Client disconnects while the server is mid-write of a large response body (e.g. `/status`
      with a long error history) → `awrite()`/`drain()` hits the wrapped timeout or an immediate
      `OSError` (broken pipe/`ECONNRESET`), handled the same defensive way as every other
      wrapper-level failure — exercises `SPECIFICATION.md` A.5's flagged `Response.write()` gap
      directly, not just noting it exists.
- [ ] A route handler's return value fails JSON serialization (raw bytes, `NaN`/`Infinity` float,
      an accidentally-circular structure) → caught, logged with enough detail to identify the
      offending endpoint/module, answered with the consolidated error shape instead of a bare
      crash.
- [ ] Worst-case `/status` response size (longest configured error history across every module) →
      measure `gc.mem_free()` before/after under the Unix port; confirm building the full response
      dict before serialization doesn't spike memory unacceptably on a constrained device.

*F.5 — After response / close:*
- [ ] Normal close: counter decrements exactly once, connection task actually exits (never a
      zombie task invisible to `start_and_check_tasks()`).
- [ ] **Open design question**: does Microdot/our wrapper support HTTP keep-alive (multiple
      requests over one TCP connection)? If yes, the per-call timeout needs to reset **per request**,
      not just live for the connection's full lifetime — this changes the wrapper's shape and isn't
      addressed by the current design sketch. Needs checking against current Microdot/MicroPython
      `asyncio` docs (per CLAUDE.md's standing doc-currency instruction) before Step 2's
      implementation starts, not assumed either way.
- [ ] Double-close paths (our own `finally` plus any cleanup Microdot itself already does) don't
      raise or double-decrement the open-connection counter.

*F.6 — Concurrency / whole-server restart:*
- [ ] N simultaneous wedged connections crossing the restart threshold → restart fires exactly
      once, not repeatedly/thrashing.
- [ ] **Open design question**: what happens to a legitimate, healthy, mid-flight request when a
      restart is triggered by other wedged connections? BACKLOG's sketch only specifies
      `server.close()` (stops new accepts) — whether in-flight connection tasks are left to finish
      on their own or forcibly torn down needs verifying against real `asyncio.Server`/
      `StreamWriter` semantics, not assumed; write the test once that's confirmed, don't guess the
      expected behavior first.
- [ ] Pathological repeated rewedging (a broken/hostile client immediately reconnecting and
      rewedging right after each restart) doesn't thrash into a restart loop that starves the
      watchdog or floods logs/FRAM — confirm this either self-limits via the existing
      `_TASK_FAIL_MAX` escalation or needs its own secondary backoff (design decision, not just a
      test — flag if the current sketch doesn't already cover it).
- [ ] The secondary "harder timeout" (force-cancel the outer server task if `close()`/
      `wait_closed()` itself doesn't return within a further grace period) — force this path
      explicitly via a fake `wait_closed()` that hangs, don't rely on it happening to be exercised
      by another test.

*F.7 — Adversarial/malformed-input shapes* (LAN-only device, but cheap defensive discipline):
- [ ] Extremely long URL path/query string.
- [ ] Unknown path → confirmed `404` handler, shaped response, not a bare crash.
- [ ] Wrong HTTP method on a known path → confirmed `405` handler.
- [ ] Path-traversal-looking or trailing-garbage segments on a known route.
- [ ] Dedicated Slowloris-shaped simulation (many connections each trickling single bytes) to
      confirm the open-count/threshold-restart backstop actually engages within a bounded time —
      the concrete test for the open question flagged in F.2.

*F.8 — Server startup edge cases:*
- [ ] `asyncio.start_server()` failing to bind (e.g. port already in use from an unclean previous
      instance, `OSError(EADDRINUSE)`) — confirm whether `start_and_check_tasks()`'s existing
      retry/escalation treats this the same as any other task failure, and whether that's actually
      the right behavior for a bind failure specifically (a bind failure won't fix itself by
      retrying immediately the way a transient wedge might).
- [ ] Webserver task starting before the WiFi interface has actually associated — confirm whether
      `bind()`/`start_server()` on rp2 succeeds regardless of link state (likely yes, socket layer
      doesn't require an active association to bind) or needs to wait — verify against real
      MicroPython socket behavior, don't assume.

*F.9 — Supervisor integration / soak (capstone tests for this whole section):*
- [ ] Webserver task actually dying (post-restart) is picked up and restarted by
      `start_and_check_tasks()` through the real, unmocked supervisor path.
- [ ] Repeated webserver-task failures reach `_TASK_FAIL_MAX` and escalate to the existing
      watchdog-starve fallback exactly like any other supervised task — no special-casing.
- [ ] The soak test already specified in BACKLOG.md's design sketch step 5: 100+ start/wedge/
      reclaim/restart cycles under the Unix port, `gc.mem_free()` flat throughout — the pass/fail
      bar this whole section builds toward.

**G. Open design questions this action list surfaced** (genuinely new, not previously decided —
listed together here for visibility, in addition to being inline above; these are fair game for
Step 2's own 10-question round, not something to silently resolve while writing tests):
1. Per-call timeout vs. per-request wall-clock cap — is the open-connection-count backstop alone
   considered sufficient against a Slowloris-shaped slow-trickle client, or does the wrapper need
   an additional overall-request timeout?
2. What does MicroPython's `asyncio.StreamReader.readexactly()` actually raise on an early/clean
   peer close mid-body (not a timeout) — same handling path as the already-specified
   `TimeoutError`/`OSError` case, or a distinct one that needs its own catch?
3. Does Microdot support HTTP keep-alive today? If so, per-connection vs. per-request timeout
   scope needs revisiting before implementation, not after.
4. What happens to legitimate in-flight connections when a whole-server restart is triggered by
   other, unrelated wedged connections — finish naturally, or torn down?
5. Does repeated rewedge-immediately-after-restart need its own backoff/escalation, or does the
   existing `_TASK_FAIL_MAX` path already cover it structurally?
6. Bind failure (`EADDRINUSE`) and pre-network-up startup — does the existing task-retry behavior
   actually suit these two cases, or do they need distinct handling?

### Step 3 — Digital-twin hardware simulator

**Goal**: a new module, sitting at the same `machine`-module raw-bus-transaction mocking boundary
`tests/machine.py` already establishes for unit tests (not modified, not reused, not a higher-level
driver stand-in), but built for a different purpose: real-time-firing `Timer`s and sensible
in-range random simulated sensor values, so Step 5 can run the whole assembled prototype under the
Unix port and see it behave like it's actually attached to hardware, not just satisfy a hand-driven
test double.

**Known findings to carry in**:

- `tests/machine.py`'s `Timer` fake only fires on manual `.trigger()` — deliberately, since it's
  scoped to deterministic unit tests. The digital twin needs its own `Timer` that actually fires on
  a wall-clock schedule (e.g. backed by a real thread or asyncio-driven scheduler under the Unix
  port), which is exactly why it can't just be `tests/machine.py` with one method changed — it's a
  different fake with different goals, hence the owner's explicit "separate, new module" framing.
- Per-sensor value ranges must come from `datasheets/` (SGP40, SCD30, BMP3xx PDFs) — read them
  directly for realistic operating ranges, don't rely on general training-data familiarity with
  these parts (CLAUDE.md's standing datasheet rule).
- Bus wiring stays untouched (owner-confirmed) — the twin only needs to answer the same raw
  I2C/SPI transactions `tests/machine.py` already answers for these three sensors, just with
  randomized-but-plausible bytes instead of hand-scripted fixture values, and on a live timer
  instead of manual stepping.

**Doc links**: `tests/machine.py` (read-only reference for the transaction shapes to match — grep
each `_Sgp40Sensor`/`_Scd30Sensor`/`_Bmp3xxSensor`-equivalent fixture already in the file for the
exact byte-level protocol each chip expects), `datasheets/` (SGP40/SCD30/BMP3xx PDFs — read first
for any register-map or value-range claim), BACKLOG.md's "Owner requirement for the final wiring
stage" entry (the origin of this whole requirement).

**Criteria for this step to finish**: new module built at a location outside both `src/` and
`tests/` (see "Where the new code actually lives" above); drives all three sensors' real I2C/SPI
transaction shapes with real-time-firing timers; produces values that stay in each datasheet's
documented sensible range; fully unit-tested (deterministic tests of the twin's own transaction
responses, not flaky wall-clock-timing assertions); does not touch `tests/machine.py` at all.

**What Step 5 needs from this step**: a documented, minimal way to swap the twin in for a Unix-port
run (most likely `MICROPYPATH`/`sys.path` ordering, matching how `tests/machine.py` is already
picked up transparently by existing tests) — `src/sensortask_wozi.py` itself should need zero
twin-awareness, no `if` branch anywhere distinguishing real hardware from simulated.

### Step 4 — Website placeholder scaffold

**Goal**: the full mechanical structure for serving the config/status website — gzip → freezefs
(`--on-import mount`) → frozen Python module → Microdot static-route serving — wired end to end
with **stub placeholder content only** ("Hello world"-shaped), not the real site. Real website
content is explicitly out of scope for this whole effort.

**Known findings to carry in**:

- `ext/freezefs/` is already vendored this session (freezefs 2.4, unmodified, MIT-licensed,
  committed to this branch). Current CLI:
  `python -m freezefs <infolder> <outfile.py> --on-import mount --target /<mount> [--overwrite always]`
  — **do not pass `--compress`**: it switches to on-device `deflate`-module decompression, which is
  incompatible with this project's existing approach (pre-gzip the files by hand, serve them with
  Microdot's `send_file(..., compressed=True, file_extension='.gz')`, which only sets the
  `Content-Encoding` header and never decompresses on-device). Mixing the two would mean double
  encoding or a broken `Content-Encoding` claim.
- The legacy `build-wozi.sh` pipeline (`cp` → `gzip -9` → `freezefs` → assemble into the firmware
  build) is the structural reference, even though its exact freezefs invocation
  (`python3 -m freezefs -s html frozen_html.py`) is stale against freezefs 2.4's current CLI (no
  `-s` flag anymore) — follow the pipeline's *shape*, not its literal command line.
- `html_raw/wozi/index.html` (and its sibling config pages) is the real site's actual content —
  useful as a reference for what fields/routes the real site eventually needs, but **not** what
  gets built this step; the stub replaces it with placeholder content that exercises the same
  pipeline.
- `improved-quality/sensortask-wozi.py` currently has `import frozen_html` at the top with no
  backing module — this step is what finally gives that import something real to resolve to (in
  `src/sensortask_wozi.py`'s equivalent import, not by editing the reference file).

**Doc links**: `build-wozi.sh` (pipeline shape), `ext/freezefs/archive.py` (current CLI/behavior —
read directly rather than trusting the stale legacy script), `ext/freezefs/ffsmount.py` (what
actually runs on-device, ~1KB RAM per the freezefs README), `html_raw/wozi/` (reference content,
not to be built for real).

**Criteria for this step to finish**: a placeholder `html_raw`-equivalent stub folder, a build step
that gzips it and runs it through `freezefs --on-import mount` (no `--compress`), a frozen module
importable under both the real build and the Unix port, and Step 2's static-route extension point
actually serving it (verify at least one stub route returns the right bytes with the right
`Content-Encoding` header); unit/integration-tested under the Unix port.

### Step 5 — Full Unix-port integration

**Goal**: assemble Steps 1-4's output into one working `src/sensortask_wozi.py` prototype, run it
end to end under the real MicroPython Unix-port interpreter with Step 3's digital twin standing in
for physical hardware, and verify it as close to real-target behavior as this project's tooling
allows without actual silicon — this is the concrete fulfillment of BACKLOG.md's "Owner requirement
for the final wiring stage" entry.

**Criteria for this step to finish**: a full boot-to-steady-state run under `scripts/test.sh`'s
interpreter (or an equivalent dedicated integration entry point, if the digital twin's
`MICROPYPATH` wiring needs to stay separate from the plain unit-test set — Step 3/5's own sessions
settle that) with no unhandled exceptions, the task supervisor never escalating to watchdog-starve
under normal simulated conditions, every REST endpoint from Step 2 reachable and returning
correctly-shaped data sourced from the twin's simulated readings, the Step 4 website stub served
correctly, and a soak run (matching Step 2's own soak-test bar) showing stable memory over time;
integration-level tests added following `tests/test_setter_microdot_integration.py`'s existing
pattern of exercising real dispatch without a real socket.

## Out of scope for all five steps

- Real website content (stub only, see Step 4).
- The future per-variant build-script generator itself (only its constraints are honored, per
  "Generator-readiness constraint" above).
- The other three deployed variants (arzi/neu×3) — this prototype is `wozi` only.
- Real-hardware build genericization and physical-hardware verification — comes after all five
  steps merge back and the large audit closes, not a branch of its own inside this scheme.
- Editing `improved-quality/sensortask-wozi.py`, `ext/microdot.py`, or `tests/machine.py`.
